#!/usr/bin/env python3
# -*- coding: utf-8 -*-


from enum import IntEnum


class TokenType(IntEnum):
    UNKNOWN         = -2
    EOF             = -1
    IDENTIFIER      =  0
    HEX_LITERAL     =  1
    STATEMENT_END   =  2
    ASSIGN          =  3
    COMMENT_NOMATCH =  4


def readIdentifier(c, file):
    value_l = [c]
    c = file.read(1)
    while c.isalnum() or c in ('_', '.'):
        value_l.append(c)
        c = file.read(1)

    value = ''.join(value_l)
    pos_after = file.tell() - len(c)

    return (value, TokenType.IDENTIFIER, pos_after)


def readHexLiteral(c, file):
    assert c == '0'

    start_pos = file.tell()
    unknown_ret = ('0', TokenType.UNKNOWN, start_pos)

    c = file.read(1)
    if c != 'x':
        return unknown_ret

    hex_digits = "0123456789ABCDEFabcdef"
    is_hex_digit = lambda c: c in hex_digits

    c = file.read(1)
    if not is_hex_digit(c):
        return unknown_ret

    value_l = ["0x", c]
    c = file.read(1)
    while is_hex_digit(c):
        value_l.append(c)
        c = file.read(1)

    value = ''.join(value_l)
    pos_after = file.tell() - len(c)

    return (value, TokenType.HEX_LITERAL, pos_after)


class Token:
    def __init__(self, other=None):
        if other is not None:
            self.set(other)

        else:
            self.initialize()

    def initialize(self):
        self.value          = '\\0'
        self.type           = TokenType.EOF
        self.srcPosAt       = -1
        self.srcPosAfter    = -1

    def set(self, other):
        self.value          = other.value
        self.type           = other.type
        self.srcPosAt       = other.srcPosAt
        self.srcPosAfter    = other.srcPosAfter

    def consumeWhitespaceAndComments(self, file):
        c = file.read(1)
        while c.isspace():
            c = file.read(1)

        pos = file.tell()

        while c == '/':
            c = file.read(1)
            if c == '/':
                c = file.read(1)
                while c and c != '\n':
                    c = file.read(1)

                if c == '\n':
                    c = file.read(1)

            elif c == '*':
                while True:
                    c = file.read(1)
                    if c == '*':
                        c = file.read(1)
                        if c == '/':
                            c = file.read(1)
                            break

                    if not c:
                        self.value = "/* ..."
                        self.type = TokenType.COMMENT_NOMATCH
                        self.srcPosAt = pos - 1  # len('/') == 1
                        self.srcPosAfter = -1
                        return None

            else:
                file.seek(pos)
                c = '/'
                break

            while c.isspace():
                c = file.read(1)

            pos = file.tell()

        return c, pos

    def read(self, file):
        ret = self.consumeWhitespaceAndComments(file)
        if ret is None:
            return

        c, pos = ret
        if not c:
            self.initialize()
            return

        self.srcPosAt = pos - 1  # len(c) == 1

        if c.isalpha() or c == '_':
            self.value, self.type, self.srcPosAfter = readIdentifier(c, file)

        elif c == '0':
            self.value, self.type, self.srcPosAfter = readHexLiteral(c, file)

        elif c == ';':
            self.value = ';'
            self.type = TokenType.STATEMENT_END
            self.srcPosAfter = pos

        elif c == '=':
            self.value = '='
            self.type = TokenType.ASSIGN
            self.srcPosAfter = pos

        else:
            self.value = c
            self.type = TokenType.UNKNOWN
            self.srcPosAfter = pos
