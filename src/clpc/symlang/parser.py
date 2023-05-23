#!/usr/bin/env python3
# -*- coding: utf-8 -*-


from .token import Token
from .token import TokenType


class SymbolMap:
    @classmethod
    def start(cls, reader):
        syms = []

        while True:
            is_valid, sym = cls.statement(reader)
            if not is_valid:
                break

            syms.append(sym)

        return reader.nextToken.type == TokenType.EOF, dict(syms)

    @staticmethod
    def statement(reader):
        if reader.nextToken.isIdentifier() and reader.lookAhead.type == TokenType.ASSIGN:
            memo = reader.saveNextToken()

            a = Token(reader.nextToken)

            reader.readNextToken()  # Consume identifier
            reader.readNextToken()  # Consume '='

            if (reader.nextToken.isIdentifier() or reader.nextToken.type == TokenType.HEX_LITERAL) and reader.lookAhead.type == TokenType.STATEMENT_END:
                b = Token(reader.nextToken)

                reader.readNextToken()  # Consume identifier or hex_literal
                reader.readNextToken()  # Consume ';'

                return True, (a, b)

            reader.restoreNextToken(memo)

        return False, None


class AddressConversionMap:
    @classmethod
    def start(cls, reader):
        data_addr = None

        is_valid, text_addr = cls.text_addr_statement(reader)
        if is_valid:
            is_valid, data_addr = cls.data_addr_statement(reader)
            if not is_valid:
                return False, None, None, {}

        assert ((text_addr is     None and data_addr is     None) or
                (text_addr is not None and data_addr is not None))

        statements = []

        while True:
            is_valid, offs = cls.statement(reader)
            if not is_valid:
                break

            statements.append(offs)

        return reader.nextToken.type == TokenType.EOF, text_addr, data_addr, tuple(statements)

    @staticmethod
    def text_addr_statement(reader):
        if reader.nextToken.type == TokenType.TEXT_ADDR and reader.lookAhead.type == TokenType.ASSIGN:
            memo = reader.saveNextToken()

            reader.readNextToken()  # Consume 'TextAddr'
            reader.readNextToken()  # Consume '='

            if reader.nextToken.type == TokenType.HEX_LITERAL and reader.lookAhead.type == TokenType.STATEMENT_END:
                addr = Token(reader.nextToken)

                reader.readNextToken()  # Consume hex_literal
                reader.readNextToken()  # Consume ';'

                return True, addr

            reader.restoreNextToken(memo)

        return False, None

    @staticmethod
    def data_addr_statement(reader):
        if reader.nextToken.type == TokenType.DATA_ADDR and reader.lookAhead.type == TokenType.ASSIGN:
            memo = reader.saveNextToken()

            reader.readNextToken()  # Consume 'DataAddr'
            reader.readNextToken()  # Consume '='

            if reader.nextToken.type == TokenType.HEX_LITERAL and reader.lookAhead.type == TokenType.STATEMENT_END:
                addr = Token(reader.nextToken)

                reader.readNextToken()  # Consume hex_literal
                reader.readNextToken()  # Consume ';'

                return True, addr

            reader.restoreNextToken(memo)

        return False, None

    @classmethod
    def statement(cls, reader):
        is_valid, value = cls.range_offset(reader)
        if is_valid:
            return True, value

        return cls.platform_directive(reader)

    @staticmethod
    def range_offset(reader):
        if reader.nextToken.type.isPossiblyUnprefixedHexLiteral() and reader.lookAhead.type == TokenType.MINUS:
            memo = reader.saveNextToken()

            a = Token(reader.nextToken)

            reader.readNextToken()  # Consume hex_literal_no_prefix
            reader.readNextToken()  # Consume '-'

            if reader.nextToken.type.isPossiblyUnprefixedHexLiteral() and reader.lookAhead.type == TokenType.COLON:
                b = Token(reader.nextToken)

                reader.readNextToken()  # Consume hex_literal_no_prefix
                reader.readNextToken()  # Consume ':'

                if reader.nextToken.type.isSign() and reader.lookAhead.isIntegerLiteral():
                    c = Token(reader.nextToken)
                    d = Token(reader.nextToken)

                    reader.readNextToken()  # Consume sign
                    reader.readNextToken()  # Consume integer_literal

                    if reader.nextToken.type == TokenType.STATEMENT_END:
                        reader.readNextToken()  # Consume ';'
                        return True, ((a, b), (c, d))

            reader.restoreNextToken(memo)

        return False, None

    @classmethod
    def platform_directive(cls, reader):
        if reader.nextToken.type == TokenType.PLATFORM:
            memo = reader.saveNextToken()

            reader.readNextToken()  # Consume '.platform'

            platform = None
            extends = None

            is_valid, platform = cls.platform(reader)
            if is_valid:
                if reader.nextToken.type == TokenType.EXTENDS:
                    reader.readNextToken()  # Consume 'extends'
                    is_valid, extends = cls.platform(reader)

            if is_valid:
                return True, (platform, extends)

            reader.restoreNextToken(memo)

        return False, None

    @staticmethod
    def platform(reader):
        if reader.nextToken.type.isPlatformTarget():
            memo = reader.saveNextToken()

            a = Token(reader.nextToken)
            b = None

            reader.readNextToken()  # Consume 'Emulator' or 'Console'

            is_valid = True

            if reader.nextToken.type == TokenType.ASSIGN:
                reader.readNextToken()  # Consume '='
                is_valid = reader.nextToken.isIdentifier()
                if is_valid:
                    b = Token(reader.nextToken)
                    reader.readNextToken()  # Consume identifier

            if is_valid:
                return True, (a, b)

            reader.restoreNextToken(memo)

        return False, None


def resolveSymbols(reader, syms):
    syms_resolved = {}

    assert isinstance(syms, dict)
    syms_keys = tuple(k.value for k in syms)

    for k, v in syms.items():
        # assert k.isIdentifier()

        if k.isIdentifier():
            # assert v.isIdentifier() or v.type == TokenType.HEX_LITERAL

            if v.isIdentifier():
                # assert v.value in syms_resolved

                if v.value in syms_resolved:
                    syms_resolved[k.value] = syms_resolved[v.value]

                else:
                    line, col = reader.indexToCoordinates(reader.file_str, v.srcPosAt)
                    msg = "referenced before assignment" if v.value in syms_keys else "not defined"
                    raise NameError("At line %d, column %d: %r is %s" % (line, col, v.value, msg))

            elif v.type == TokenType.HEX_LITERAL:
                v_int = int(v.value, 16)

                # assert 0 <= v_int <= 0xFFFFFFFF

                if 0 <= v_int <= 0xFFFFFFFF:
                    syms_resolved[k.value] = v_int

                else:
                    line, col = reader.indexToCoordinates(reader.file_str, v.srcPosAt)
                    raise ValueError("At line %d, column %d: expected value to be in range [0, 0xFFFFFFFF], received: %s" % (line, col, v.value))

            else:
                line, col = reader.indexToCoordinates(reader.file_str, v.srcPosAt)
                raise TypeError("Unrecognized token at line %d, column %d: %r" % (line, col, v.value))

        else:
            line, col = reader.indexToCoordinates(reader.file_str, k.srcPosAt)
            raise TypeError("Unrecognized token at line %d, column %d: %r" % (line, col, k.value))

    return syms_resolved
