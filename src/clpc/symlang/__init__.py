#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# start         { statement }* EOF
#
# statement     identifier '=' (identifier | hex_literal) ';'
#
# identifier    nondigit { (nondigit | DIGIT | '.') }*
#
# nondigit      ALPHA_CHARACTER | '_'
#
# hex_literal   '0x' { HEX_DIGIT }+


from . import parser
from . import reader
from . import token


__all__ = [
    "parser",
    "reader",
    "token"
]
