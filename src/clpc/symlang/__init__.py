#!/usr/bin/env python3
# -*- coding: utf-8 -*-


# Common:
#
# hex_literal           '0x' hex_literal_no_prefix
#
# hex_literal_no_prefix { HEX_DIGIT }+
#
# identifier            nondigit { (nondigit | DIGIT | '.') }*
#
# nondigit              ALPHA_CHARACTER | '_'


# Symbol map:
#
# start         { statement }* EOF
#
# statement     identifier '=' (identifier | hex_literal) ';'
#
# hex_literal   '0x' { HEX_DIGIT }+


# Address offsets map:
#
# start                 [ text_addr_statement data_addr_statement ] { statement }* EOF
#
# text_addr_statement   'TextAddr' '=' hex_literal ';'
#
# data_addr_statement   'DataAddr' '=' hex_literal ';'
#
# statement             range_offset | platform_directive
#
# range_offset          hex_literal_no_prefix '-' hex_literal_no_prefix ':' sign integer_literal ';'
#
# sign                  '+' | '-'
#
# integer_literal       decimal_literal | hex_literal
#
# decimal_literal       { '0' }+ | NONZERO_DIGIT { DIGIT }*
#
# platform_directive    '.platform' platform [ 'extends' platform ]
#
# platform              ('Emulator' | 'Console') [ '=' identifier ]


from . import parser
from . import reader
from . import token


__all__ = [
    "parser",
    "reader",
    "token"
]
