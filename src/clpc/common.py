#!/usr/bin/env python3
# -*- coding: utf-8 -*-


import os
import re


TOOL_VERSION    = "0"

WUAPPS_VERSION_MIN      = (3, 0)
WUAPPS_VERSION_MIN_STR  = '.'.join(map(str, WUAPPS_VERSION_MIN))

WUAPPS_VERSION_MAX      = (3, 0)
WUAPPS_VERSION_MAX_STR  = '.'.join(map(str, WUAPPS_VERSION_MAX))

WUAPPS_VERSION      = WUAPPS_VERSION_MAX
WUAPPS_VERSION_STR  = WUAPPS_VERSION_MAX_STR


FILENAME_SEARCH_RE_OBJ = re.compile(r'[^A-Za-z0-9_\-.,+\(\)]')


def IsValidFilename(s):
    # https://stackoverflow.com/a/8686943
    return not (s and
                isinstance(s, str) and
                FILENAME_SEARCH_RE_OBJ.search(s) and
                not s.startswith('-') and
                not s.endswith('.'))


def NormalizePath(path):
    return os.path.normcase(os.path.normpath(path))
