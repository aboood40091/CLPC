#!/usr/bin/env python3
# -*- coding: utf-8 -*-


from .token import Token
from .token import TokenType


def start(reader):
    syms = []

    while True:
        is_valid, sym = statement(reader)
        if not is_valid:
            break

        syms.append(sym)

    return reader.nextToken.type == TokenType.EOF, dict(syms)


def statement(reader):
    if reader.nextToken.type == TokenType.IDENTIFIER and reader.lookAhead.type == TokenType.ASSIGN:
        memo = reader.saveNextToken()

        a = Token(reader.nextToken)

        reader.readNextToken()  # Consume identifier
        reader.readNextToken()  # Consume '='

        if (reader.nextToken.type == TokenType.IDENTIFIER or reader.nextToken.type == TokenType.HEX_LITERAL) and reader.lookAhead.type == TokenType.STATEMENT_END:
            b = Token(reader.nextToken)

            reader.readNextToken()  # Consume identifier or hex_literal
            reader.readNextToken()  # Consume ';'

            return True, (a, b)

        reader.restoreNextToken(memo)

    return False, None


def resolve(reader, syms):
    syms_resolved = {}

    assert isinstance(syms, dict)
    syms_keys = tuple(k.value for k in syms)

    for k, v in syms.items():
        # assert k.type == TokenType.IDENTIFIER

        if k.type == TokenType.IDENTIFIER:
            # assert v.type in (TokenType.IDENTIFIER, TokenType.HEX_LITERAL)

            if v.type == TokenType.IDENTIFIER:
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
