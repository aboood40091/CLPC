#!/usr/bin/env python3
# -*- coding: utf-8 -*-


from enum import IntEnum


class TokenType(IntEnum):
    UNKNOWN                 = -2
    EOF                     = -1
    IDENTIFIER              =  0
    HEX_LITERAL             =  1
    STATEMENT_END           =  2
    ASSIGN                  =  3
    COMMENT_NOMATCH         =  4
    HEX_LITERAL_NOPREFIX    =  5    # Strictly with characters from the range A-Fa-f
    DECIMAL_LITERAL         =  6
    MINUS                   =  7
    PLUS                    =  8
    COLON                   =  9
    PLATFORM                = 10
    EXTENDS                 = 11
    EMULATOR                = 12
    CONSOLE                 = 13
    TEXT_ADDR               = 14
    DATA_ADDR               = 15

    def isPossiblyIdentifier(self):
        return self in (
            TokenType.IDENTIFIER,
            # TokenType.PLATFORM,           # This starts with "." so cannot possibly be identifier
            TokenType.EXTENDS,
            TokenType.EMULATOR,
            TokenType.CONSOLE,
            TokenType.TEXT_ADDR,
            TokenType.DATA_ADDR,
            TokenType.HEX_LITERAL_NOPREFIX  # Possible if value did not start with digit
        )

    def isPossiblyUnprefixedHexLiteral(self):
        return self in (
            TokenType.DECIMAL_LITERAL,
            TokenType.HEX_LITERAL_NOPREFIX
        )

    def isPossiblyIntegerLiteral(self):
        return self in (
            TokenType.HEX_LITERAL,
            TokenType.DECIMAL_LITERAL,
            TokenType.HEX_LITERAL_NOPREFIX
        )

    def __str__(self):
        if self == TokenType.HEX_LITERAL_NOPREFIX:
            return "TokenType.(IDENTIFIER or DECIMAL_LITERAL or HEX_LITERAL_NOPREFIX)"

        else:
            return super().__str__()

    def isSign(self):
        return self in (
            TokenType.MINUS,
            TokenType.PLUS
        )

    def isPlatformTarget(self):
        return self in (
            TokenType.EMULATOR,
            TokenType.CONSOLE
        )


def matchWord(file, word):
    while word:
        c = word[0]
        word = word[1:]
        if file.read(1) != c:
            return None

    pos_after = file.tell()

    c = file.read(1)
    if c.isalpha():  # Matched partial word
        return None

    return pos_after


def readKeyword(c, file, start_pos):
    keywords = (
        (".platform",   TokenType.PLATFORM),
        ("extends",     TokenType.EXTENDS),
        ("Emulator",    TokenType.EMULATOR),
        ("Console",     TokenType.CONSOLE),
        ("TextAddr",    TokenType.TEXT_ADDR),
        ("DataAddr",    TokenType.DATA_ADDR)
    )

    for keyword, type_ in keywords:
        if keyword.startswith(c):
            pos_after = matchWord(file, keyword[1:])
            if pos_after is not None:
                return (keyword, type_, pos_after)

            file.seek(start_pos)

    return None


def readUnprefixedHexLiteral(c, file, started_with_0x):
    hex_digits = "0123456789ABCDEFabcdef"
    is_hex_digit = lambda c: c in hex_digits

    if not is_hex_digit(c):
        return None

    digits = "0123456789"
    is_digit_c = lambda c: c in digits

    starts_with_digit = is_digit_c(c)

    value_l = [c]
    c = file.read(1)
    while True:
        if is_hex_digit(c):
            value_l.append(c)
            c = file.read(1)

        elif c.isalpha() or c in ('_', '.'):
            if starts_with_digit or started_with_0x:
                break

            else:
                return None  # Identifier maybe

        else:
            break

    value = ''.join(value_l)
    pos_after = file.tell() - len(c)

    return (value, TokenType.HEX_LITERAL_NOPREFIX, pos_after)


def readIdentifier(c, file, start_pos):
    ret = readKeyword(c, file, start_pos)
    if ret is not None:
        return ret

    file.seek(start_pos)

    ret = readUnprefixedHexLiteral(c, file, False)
    if ret is not None:
        return ret

    file.seek(start_pos)

    if not (c.isalpha() or c == '_'):
        return None

    value_l = [c]
    c = file.read(1)
    while c.isalnum() or c in ('_', '.'):
        value_l.append(c)
        c = file.read(1)

    value = ''.join(value_l)
    pos_after = file.tell() - len(c)

    return (value, TokenType.IDENTIFIER, pos_after)


def readDecimalLiteral(c, file, start_pos):
    ret = readUnprefixedHexLiteral(c, file, False)
    if ret is not None:
        return ret

    file.seek(start_pos)

    digits = "0123456789"
    is_digit_c = lambda c: c in digits

    if not is_digit_c(c):
        return None

    value_l = [c]
    c = file.read(1)
    while is_digit_c(c):
        value_l.append(c)
        c = file.read(1)

    if value_l[0] == '0' and len(set(value_l)) != 1:
        return None

    value = ''.join(value_l)
    pos_after = file.tell() - len(c)

    return (value, TokenType.INT_LITERAL, pos_after)


def readHexLiteral(c, file):
    if c != '0':
        return None

    c = file.read(1)
    if c != 'x':
        return None

    c = file.read(1)
    ret = readUnprefixedHexLiteral(c, file, True)
    if ret is None:
        return None

    value, _, pos_after = ret
    value = "0x" + value

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

    def isIdentifier(self):
        if not self.type.isPossiblyIdentifier():
            return False

        return self.type == TokenType.IDENTIFIER or self.value.isidentifier()

    def isIntegerLiteral(self):
        if not self.type.isPossiblyIntegerLiteral():
            return False

        if self.type == TokenType.HEX_LITERAL_NOPREFIX:
            digits = "0123456789"
            is_digit_c = lambda c: c in digits
            is_digit = lambda s: s and all(is_digit_c(c) for c in s)
            return is_digit(self.value)

        return True

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

        ret = readHexLiteral(c, file)
        if ret is None:
            file.seek(pos)
            ret = readIdentifier(c, file, pos)
            if ret is None:
                file.seek(pos)
                ret = readDecimalLiteral(c, file, pos)
                if ret is None:
                    file.seek(pos)

        if ret is not None:
            self.value, self.type, self.srcPosAfter = ret

        elif c == ';':
            self.value = ';'
            self.type = TokenType.STATEMENT_END
            self.srcPosAfter = pos

        elif c == '=':
            self.value = '='
            self.type = TokenType.ASSIGN
            self.srcPosAfter = pos

        elif c == '-':
            self.value = '-'
            self.type = TokenType.MINUS
            self.srcPosAfter = pos

        elif c == '+':
            self.value = '+'
            self.type = TokenType.PLUS
            self.srcPosAfter = pos

        elif c == ':':
            self.value = ':'
            self.type = TokenType.COLON
            self.srcPosAfter = pos

        else:
            self.value = c
            self.type = TokenType.UNKNOWN
            self.srcPosAfter = pos
