#!/usr/bin/env python3
# -*- coding: utf-8 -*-


# Built-in
import os


# Local
from .common import NormalizePath
from .module import Module
from .symlang.parser import AddressConversionMap
from .symlang.reader import TokenReader


class Target:
    def __init__(self):
        self.isAbstract = False

        self.addrMap = None
        self.baseRpx = None

        self.remove_Modules = []
        self.remove_Defines = []

        self.add_Modules = {}
        self.add_Defines = {}

        self.extendsName = None
        self.base = None

    @staticmethod
    def fromObj(obj, name, proj, error=print):
        target_field_name = "Target %r" % name
        modulesBaseDir = proj.modulesBaseDir
        normalize_path = NormalizePath

        ### Selected Options Sanity Check ###
        # print("%s Selected Options Sanity Check" % target_field_name)

        available_options = (
            "Abstract",
            "AddrMap",
            "BaseRpx",
            "Remove/Modules",
            "Add/Modules",
            "Remove/Defines",
            "Add/Defines",
            "Extends"
        )

        available_options_error_msg = "Unrecognized option in %s: %s" % (target_field_name, "%r")

        for k in obj:
            if k not in available_options:
                error(available_options_error_msg % k)
                return None

        ### Target Initialization ###
        # print("%s Target Initialization" % target_field_name)

        target = Target()
        default_name = name

        ### Abstract Determiner Reader ###

        if "Abstract" in obj:
            abstract = obj["Abstract"]
            if not isinstance(abstract, bool):
                error("In %s, expected \"Abstract\" to be a boolean" % target_field_name)
                return None

            target.isAbstract = abstract

        ### Extending Target Name Reading ###

        if "Extends" in obj:
            extends_name = proj.processString("%s Extending Target Name" % target_field_name, obj["Extends"], error=error)
            if extends_name is None:
                return None

            target.extendsName = extends_name
            default_name = extends_name

        ### Address Conversion Map Reading ###
        # print("%s Address Conversion Map Reading" % target_field_name)

        addr_map_name = None

        if "AddrMap" not in obj:
            addr_map_name = default_name

        else:
            addr_map = proj.readString(obj, "AddrMap", "%s Address Conversion Map Name" % target_field_name, 0x01020304, True, error=error)
            if addr_map is None:
                return None

            if addr_map != 0x01020304:
                addr_map_name = addr_map

        if addr_map_name is not None:
            addr_map_path = normalize_path(os.path.join(proj.path, "maps/%s.convmap" % addr_map_name))
            if not os.path.isfile(addr_map_path):
                error("In %s,\n"
                      "Address conversion map file not found: %r\n"
                      "Path resolved to: %r" % (target_field_name, addr_map_name, addr_map_path))
                return None

            reader = TokenReader()
            reader.openFile(addr_map_path)

            try:
                is_valid, text_addr, data_addr, statements = AddressConversionMap.start(reader)
                if not is_valid:
                    line, col = reader.indexToCoordinates(reader.file_str, reader.nextToken.srcPosAt)
                    error("In file: %s\n"
                          "At line %d, column %d: syntax error" % (addr_map_path, line, col))
                    return None

                try:
                    target.addrMap = AddressConversionMap.resolve(reader, text_addr, data_addr, statements)

                except Exception as e:
                    error("In file: %s\n"
                          "%s" % (addr_map_path, e))
                    return None

            finally:
                reader.closeFile()

        ### Base RPX Filename Reading ###
        # print("%s Base RPX Filename Reading" % target_field_name)

        if "BaseRpx" not in obj:
            target.baseRpx = default_name

        else:
            base_rpx = proj.readString(obj, "BaseRpx", "%s Base RPX Filename" % target_field_name, 0x01020304, True, error=error)
            if base_rpx is None:
                return None

            if base_rpx != 0x01020304:
                target.baseRpx = base_rpx

        ### Modules Removal List Reading ###
        # print("%s Modules Removal List Reading" % target_field_name)

        if "Remove/Modules" in obj:
            modules_names = obj["Remove/Modules"]
            if modules_names is not None:
                if not isinstance(modules_names, list):
                    error("In %s, expected \"Remove/Modules\" to be a list of strings" % target_field_name)
                    return None

                modules_names_set = set()
                remove_modules_field_name = "%s \"Remove/Modules\"" % target_field_name

                for filename in modules_names:
                    filename = proj.processString(remove_modules_field_name, filename, error=error)
                    if filename is None:
                        return None

                    file_path = filename + ".yaml"
                    if not os.path.isabs(file_path):
                        file_path = os.path.join(modulesBaseDir, file_path)

                    modules_names_set.add(normalize_path(file_path))

                target.remove_Modules = tuple(modules_names_set)

        ### Modules Addition List Reading ###
        # print("%s Modules Addition List Reading" % target_field_name)

        if "Add/Modules" in obj:
            modules_names = obj["Add/Modules"]
            if modules_names is not None:
                if not isinstance(modules_names, list):
                    error("In %s, expected \"Add/Modules\" to be a list of strings" % target_field_name)
                    return None

                modules_names_set = set()
                add_modules_field_name = "%s \"Add/Modules\"" % target_field_name

                for filename in modules_names:
                    filename = proj.processString(add_modules_field_name, filename, error=error)
                    if filename is None:
                        return None

                    file_path = filename + ".yaml"
                    if not os.path.isabs(file_path):
                        file_path = os.path.join(modulesBaseDir, file_path)

                    modules_names_set.add(normalize_path(file_path))

                for file_path in modules_names_set:
                    if file_path in target.remove_Modules:
                        error("In %s, trying to add module that needs to be removed within the same target: %s" % (target_field_name, file_path))
                        return None

                modules = {}

                for file_path in modules_names_set:
                    if file_path in proj.fileCache:
                        module = proj.fileCache[file_path]

                    else:
                        module = Module.fromYaml(file_path, proj, error)
                        if module is None:
                            return None

                        proj.fileCache[file_path] = module

                    modules[file_path] = module

                target.add_Modules = modules

        ### Defines Removal List Reading ###
        # print("%s Defines Removal List Reading" % target_field_name)

        if "Remove/Defines" in obj:
            defines = obj["Remove/Defines"]
            if defines is not None:
                if not isinstance(defines, list):
                    error("In %s, expected \"Remove/Defines\" to be a list of strings" % target_field_name)
                    return None

                is_str = lambda s: isinstance(s, str)
                is_non_null_str = lambda s: s and is_str(s)
                is_valid_key = lambda k: is_non_null_str(k) and k.isidentifier()

                defines_set = set()
                remove_key_error_msg = "In %s, invalid key in \"Remove/Defines\": %s" % (target_field_name, "%r")

                for k in defines:
                    if not is_valid_key(k):
                        error(remove_key_error_msg % k)
                        return None

                    defines_set.add(k)

                target.remove_Defines = tuple(defines_set)

        ### Defines Addition List Reading ###
        # print("%s Defines Addition List Reading" % target_field_name)

        if "Add/Defines" in obj:
            defines = obj["Add/Defines"]
            if defines is not None:
                if not isinstance(defines, dict):
                    error("In %s, expected \"Add/Defines\" to be a key-value mapping" % target_field_name)
                    return None

                is_str = lambda s: isinstance(s, str)
                is_non_null_str = lambda s: s and is_str(s)
                is_valid_key = lambda k: is_non_null_str(k) and k.isidentifier()

                new_defines = {}
                add_key_error_msg = "In %s, invalid key in \"Add/Defines\": %s" % (target_field_name, "%r")
                add_value_field_name = "\"Add/Defines\" for key %s in %s" % ("%r", target_field_name)

                for k, v in defines.items():
                    if not is_valid_key(k):
                        error(add_key_error_msg % k)
                        return None

                    if v is not None:
                        v = proj.processString(add_value_field_name % k, v, error=error)
                        if v is None:
                            return None

                    new_defines[k] = v

                target.add_Defines = new_defines

        ### Success ###
        # print("%s Success" % target_field_name)

        return target
