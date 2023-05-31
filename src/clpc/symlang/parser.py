#!/usr/bin/env python3
# -*- coding: utf-8 -*-


from .addrConv import AddressConvert
from .addrConv import AddressConvertCafeLoader
from .addrConv import AddressConvertEmulator
from .addrConv import PlatformType
from .token import Token
from .token import TokenType


def resolveU32Literal(v, reader):
    if v.type == TokenType.HEX_LITERAL:
        v_int = int(v.value, 16)

    elif v.type.isPossiblyIntegerLiteral():
        v_int = int(v.value)

    else:
        line, col = reader.indexToCoordinates(reader.file_str, v.srcPosAt)
        raise TypeError("Unrecognized token at line %d, column %d: %r" % (line, col, v.value))

    # assert 0 <= v_int <= 0xFFFFFFFF

    if not (0 <= v_int <= 0xFFFFFFFF):
        line, col = reader.indexToCoordinates(reader.file_str, v.srcPosAt)
        raise ValueError("At line %d, column %d: expected value to be in range [0, 0xFFFFFFFF], received: %s" % (line, col, v.value))

    return v_int


def resolveU32HexNoPrefix(v, reader):
    if v.type.isPossiblyUnprefixedHexLiteral():
        v_int = int(v.value, 16)

    else:
        line, col = reader.indexToCoordinates(reader.file_str, v.srcPosAt)
        raise TypeError("Unrecognized token at line %d, column %d: %r" % (line, col, v.value))

    # assert 0 <= v_int <= 0xFFFFFFFF

    if not (0 <= v_int <= 0xFFFFFFFF):
        line, col = reader.indexToCoordinates(reader.file_str, v.srcPosAt)
        raise ValueError("At line %d, column %d: expected value to be in range [0, 0xFFFFFFFF], received: %s" % (line, col, v.value))

    return v_int


class SymbolMap:
    @staticmethod
    def resolve(reader, syms):
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

                else:
                    syms_resolved[k.value] = resolveU32Literal(v, reader)

            else:
                line, col = reader.indexToCoordinates(reader.file_str, k.srcPosAt)
                raise TypeError("Unrecognized token at line %d, column %d: %r" % (line, col, k.value))

        return syms_resolved

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
    @staticmethod
    def resolve(reader, text_addr, data_addr, statements):
        text_addr_resolved = None if text_addr is None else resolveU32Literal(text_addr, reader)
        data_addr_resolved = None if data_addr is None else resolveU32Literal(data_addr, reader)

        platform_type_type = PlatformType

        platforms = {
            platform_type_type.Base: AddressConvert(),
            platform_type_type.Emulator: None,
            platform_type_type.CafeLoader: None
        }
        current_platform = platform_type_type.Base

        for statement in statements:
            (a, b), cd = statement

            # assert a.type.isPlatformTarget() or a.type.isPossiblyUnprefixedHexLiteral()

            if a.type.isPlatformTarget():
                if a.type == TokenType.EMULATOR:
                    # assert b is None

                    if b is not None:
                        line, col = reader.indexToCoordinates(reader.file_str, b.srcPosAt)
                        raise ValueError("At line %d, column %d, unexpected platform kind: %r" % (line, col, b.value))

                    current_platform = platform_type_type.Emulator
                    current_platform_type = AddressConvertEmulator

                else:  # if a.type == TokenType.CONSOLE
                    # assert b.value in ("cfl", "cafeloader", "CafeLoader")

                    if b.value not in ("cfl", "cafeloader", "CafeLoader"):
                        line, col = reader.indexToCoordinates(reader.file_str, b.srcPosAt)
                        raise ValueError("At line %d, column %d, unexpected platform kind: %r" % (line, col, b.value))

                    current_platform = platform_type_type.CafeLoader
                    current_platform_type = AddressConvertCafeLoader

                # assert platforms[current_platform] is None

                if platforms[current_platform] is not None:
                    line, col = reader.indexToCoordinates(reader.file_str, a.srcPosAt)
                    raise ValueError("At line %d, column %d, platform is redefined" % (line, col))

                extend_platform = platform_type_type.Base
                if cd is not None:
                    c, d = cd

                    # assert c.type.isPlatformTarget()

                    if c.type == TokenType.EMULATOR:
                        # assert d is None

                        if d is not None:
                            line, col = reader.indexToCoordinates(reader.file_str, d.srcPosAt)
                            raise ValueError("At line %d, column %d, unexpected platform kind: %r" % (line, col, d.value))

                        extend_platform = platform_type_type.Emulator

                    elif c.type == TokenType.CONSOLE:
                        # assert d.value in ("cfl", "cafeloader", "CafeLoader")

                        if d.value not in ("cfl", "cafeloader", "CafeLoader"):
                            line, col = reader.indexToCoordinates(reader.file_str, d.srcPosAt)
                            raise ValueError("At line %d, column %d, unexpected platform kind: %r" % (line, col, d.value))

                        extend_platform = platform_type_type.CafeLoader

                    else:
                        line, col = reader.indexToCoordinates(reader.file_str, c.srcPosAt)
                        raise TypeError("Unrecognized token at line %d, column %d: %r" % (line, col, c.value))

                    # assert platforms[extend_platform] is not None

                    if platforms[extend_platform] is None:
                        line, col = reader.indexToCoordinates(reader.file_str, c.srcPosAt)
                        raise ValueError("At line %d, column %d, base platform is not yet defined" % (line, col))

                platforms[current_platform] = current_platform_type(platforms[extend_platform])

            elif a.type.isPossiblyUnprefixedHexLiteral():
                # assert b.type.isPossiblyUnprefixedHexLiteral()

                if not b.type.isPossiblyUnprefixedHexLiteral():
                    line, col = reader.indexToCoordinates(reader.file_str, b.srcPosAt)
                    raise TypeError("Unrecognized token at line %d, column %d: %r" % (line, col, b.value))

                # assert cd
                c, d = cd

                # assert c.type.isSign()

                if not c.type.isSign():
                    line, col = reader.indexToCoordinates(reader.file_str, c.srcPosAt)
                    raise TypeError("Unrecognized token at line %d, column %d: %r" % (line, col, c.value))

                # assert d.isIntegerLiteral()

                if not d.isIntegerLiteral():
                    line, col = reader.indexToCoordinates(reader.file_str, d.srcPosAt)
                    raise TypeError("Unrecognized token at line %d, column %d: %r" % (line, col, d.value))

                platforms[current_platform].ranges[range(
                    resolveU32HexNoPrefix(a, reader),
                    resolveU32HexNoPrefix(b, reader)
                )] = resolveU32Literal(d, reader) * (-1 if c.type == TokenType.MINUS else 1)

            else:
                line, col = reader.indexToCoordinates(reader.file_str, a.srcPosAt)
                raise TypeError("Unrecognized token at line %d, column %d: %r" % (line, col, a.value))

        base_platform = platforms[platform_type_type.Base]
        for platform, platform_type in (platform_type_type.Emulator, AddressConvertEmulator), (platform_type_type.CafeLoader, AddressConvertCafeLoader):
            if platforms[platform] is None:
                platforms[platform] = platform_type(base_platform)

        return text_addr_resolved, data_addr_resolved, platforms

    @classmethod
    def start(cls, reader):
        data_addr = None

        is_valid, text_addr = cls.text_addr_statement(reader)
        if is_valid:
            is_valid, data_addr = cls.data_addr_statement(reader)
            if not is_valid:
                return False, None, None, None

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
                    d = Token(reader.lookAhead)

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
