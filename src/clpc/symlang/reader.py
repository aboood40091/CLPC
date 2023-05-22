#!/usr/bin/env python3
# -*- coding: utf-8 -*-


from .token import Token


class TokenReader:
    def __init__(self):
        self.initialize()

    def initialize(self):
        self.nextToken = Token()
        self.lookAhead = Token()

        self.file = None
        self.file_str = ''

    def openFile(self, path):
        if self.file:
            self.file.close()

        self.initialize()

        self.file = open(path, newline='')
        self.file_str = self.file.read()

        # print("Reading the following source file:")
        # print()
        # print(self.file_str)
        # print()

        self.file.seek(0)
        self.lookAhead.read(self.file)

        self.readNextToken()

    def closeFile(self):
        self.file.close()
        self.initialize()

    def saveNextToken(self):
        return Token(self.nextToken), Token(self.lookAhead)

    def restoreNextToken(self, memo):
        self.nextToken.set(memo[0])
        self.lookAhead.set(memo[1])

    @staticmethod
    def indexToCoordinates(s, index):
        """
        Returns (line, col) of `index` in `s`.
        """

        assert index >= -1

        s_len = len(s)
        if not s_len:
            return 1, 1

        if index == -1 or index + 1 >= s_len:
            sp = s.splitlines(keepends=True)

        else:
            sp = s[:index + 1].splitlines(keepends=True)

        line, col = len(sp), len(sp[-1])
        if index == -1 or index >= s_len:
            if any(s.endswith(line_boundary) for line_boundary in (
                '\r\n',
                '\n',
                '\r',
                '\x0b',
                '\x0c',
                '\x1c',
                '\x1d',
                '\x1e',
                '\x85',
                '\u2028',
                '\u2029'
            )):
                line += 1
                col = 1
            else:
                col += 1

        return line, col

    def readNextToken(self):
        assert self.file is not None

        self.nextToken.set(self.lookAhead)

        # line, col = self.indexToCoordinates(self.file_str, self.nextToken.srcPosAt)
        # print("Next Token is: %s, type: %s, position: %d (line %d, column %d)" % (self.nextToken.value, str(self.nextToken.type)[10:], self.nextToken.srcPosAt, line, col))

        if self.nextToken.srcPosAfter != -1:
            self.file.seek(self.nextToken.srcPosAfter)
            self.lookAhead.read(self.file)
