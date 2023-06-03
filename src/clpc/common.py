#!/usr/bin/env python3
# -*- coding: utf-8 -*-


import os
import pathlib
import re
import struct


TOOL_VERSION    = "0"

WUAPPS_VERSION_MIN      = (3, 0)
WUAPPS_VERSION_MIN_STR  = '.'.join(map(str, WUAPPS_VERSION_MIN))

WUAPPS_VERSION_MAX      = (3, 0)
WUAPPS_VERSION_MAX_STR  = '.'.join(map(str, WUAPPS_VERSION_MAX))

WUAPPS_VERSION      = WUAPPS_VERSION_MAX
WUAPPS_VERSION_STR  = WUAPPS_VERSION_MAX_STR


def align(x, y):
    return ((x - 1) | (y - 1)) + 1


STRUCT_U8   = struct.Struct(">B")
STRUCT_U16  = struct.Struct(">H")
STRUCT_U32  = struct.Struct(">I")
STRUCT_U64  = struct.Struct(">Q")
STRUCT_S8   = struct.Struct(">b")
STRUCT_S16  = struct.Struct(">h")
STRUCT_S32  = struct.Struct(">i")
STRUCT_S64  = struct.Struct(">q")
STRUCT_F32  = struct.Struct(">f")
STRUCT_F64  = struct.Struct(">d")

PACK_U8     = STRUCT_U8.pack
PACK_U16    = STRUCT_U16.pack
PACK_U32    = STRUCT_U32.pack
PACK_U64    = STRUCT_U64.pack
PACK_S8     = STRUCT_S8.pack
PACK_S16    = STRUCT_S16.pack
PACK_S32    = STRUCT_S32.pack
PACK_S64    = STRUCT_S64.pack
PACK_F32    = STRUCT_F32.pack
PACK_F64    = STRUCT_F64.pack


FILENAME_SEARCH_RE_OBJ = re.compile(r'[^A-Za-z0-9_\-.,+\(\)\ ]')


def IsValidFilename(s):
    # https://stackoverflow.com/a/8686943
    return not (s and
                isinstance(s, str) and
                FILENAME_SEARCH_RE_OBJ.search(s) and
                not s.startswith('-') and
                not s.endswith('.'))


def NormalizePath(path):
    return pathlib.Path(os.path.normcase(os.path.normpath(path))).resolve()
