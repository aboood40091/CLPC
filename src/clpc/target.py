#!/usr/bin/env python3
# -*- coding: utf-8 -*-


# Built-in
import os


# Local
from .common import NormalizePath
from .module import Module


class Target:
    def __init__(self):
        self.name = None

        self.isAbstract = False

        self.baseNames = []
        self.bases = []
        self.base = None

        self.addrMapName = None
        self.addrMap = None

        self.baseRpxName = None

        self.remove_Modules = []
        self.remove_BuildOptions = []

        self.add_Modules = {}
        self.add_BuildOptions = []

    def __eq__(self, other):
        if isinstance(other, Target) and (other.name is not None or self.name is not None):
            return self.name == other.name

        return super().__eq__(other)

    def copy(self, other):
        self.name                   = other.name
        self.isAbstract             = other.isAbstract
        self.baseNames              = other.baseNames
        self.bases                  = other.bases
        self.base                   = other.base
        self.addrMapName            = other.addrMapName
        self.addrMap                = other.addrMap
        self.baseRpxName            = other.baseRpxName
        self.remove_Modules         = other.remove_Modules
        self.remove_BuildOptions    = other.remove_BuildOptions
        self.add_Modules            = other.add_Modules
        self.add_BuildOptions       = other.add_BuildOptions

    def join(self, other, target_field_name, error=print):
        self.isAbstract = True

        # We don't care about these
        self.baseNames = None
        self.bases = None
        self.addrMap = None

        if other.addrMapName != "@inherit":
            self.addrMapName = other.addrMapName

        if other.baseRpxName != "@inherit":
            self.baseRpxName = other.baseRpxName

        for module_name in other.remove_Modules:
            if module_name in self.add_Modules:
                del self.add_Modules[module_name]

            else:
                self.remove_Modules.append(module_name)

        for module_name, module in other.add_Modules.items():
            if module_name in self.add_Modules:
                error("In %s, trying to add module from base %r that already exists in base(s): %r,\n"
                      "%s" % (target_field_name, other.name, self.name, module_name))
                return False

            self.add_Modules[module_name] = module

        for option in other.remove_BuildOptions:
            if option in self.add_BuildOptions:
                self.add_BuildOptions.remove(option)

            else:
                self.remove_BuildOptions.append(option)

        for option in other.add_BuildOptions:
            if option in self.add_BuildOptions:
                error("In %s, trying to add build option from base %r that already exists in base(s): %r,\n"
                      "%s" % (target_field_name, other.name, self.name, option))
                return False

            self.add_BuildOptions.append(option)

        self.name = " ".join((self.name, "|", other.name))
        return True

    @staticmethod
    def fromObj(obj, name, proj, error=print):
        target_field_name = "Target %r" % name

        ### Target Initialization ###
        # print("%s Target Initialization" % target_field_name)

        target = Target()
        target.name = name

        if obj is None:
            target.addrMapName = name
            target.baseRpxName = name

            return target

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
            "Remove/BuildOptions",
            "Add/BuildOptions",
            "Extends"
        )

        available_options_error_msg = "Unrecognized option in %s: %s" % (target_field_name, "%r")

        for k in obj:
            if k not in available_options:
                error(available_options_error_msg % k)
                return None

        ### Abstract Determiner Reader ###

        if "Abstract" in obj:
            abstract = obj["Abstract"]
            if not isinstance(abstract, bool):
                error("In %s, expected \"Abstract\" to be a boolean" % target_field_name)
                return None

            target.isAbstract = abstract

        ### Base Target(s) Name Reading ###

        if "Extends" in obj:
            extends = obj["Extends"]
            if isinstance(extends, str):
                extends = [extends]

            elif not isinstance(extends, list) or not extends:
                error("In %s, expected \"Extends\" to be a string or list of strings" % target_field_name)
                return None

            extends_field_name = "%s Base Target(s) Name" % target_field_name

            base_names = []

            for base_name in extends:
                base_name = proj.processString(extends_field_name, base_name, error=error)
                if base_name is None:
                    return None

                base_names.append(base_name)

            target.baseNames = base_names

        ### Address Conversion Map Filename Reading ###
        # print("%s Address Conversion Map Filename Reading" % target_field_name)

        addr_map_name = None

        if "AddrMap" not in obj:
            addr_map_name = "@inherit" if target.baseNames else "@self"

        else:
            addr_map = proj.readString(obj, "AddrMap", "%s Address Conversion Map Filename" % target_field_name, 0x01020304, True, error=error)
            if addr_map is None:
                return None

            if addr_map != 0x01020304:
                addr_map_name = addr_map

        if addr_map_name is not None:
            if addr_map_name == "@self":
                addr_map_name = name

            target.addrMapName = addr_map_name

        ### Base RPX Filename Reading ###
        # print("%s Base RPX Filename Reading" % target_field_name)

        base_rpx_name = None

        if "BaseRpx" not in obj:
            base_rpx_name = "@inherit" if target.baseNames else "@self"

        else:
            base_rpx = proj.readString(obj, "BaseRpx", "%s Base RPX Filename" % target_field_name, 0x01020304, True, error=error)
            if base_rpx is None:
                return None

            if base_rpx != 0x01020304:
                base_rpx_name = base_rpx

        if base_rpx_name is not None:
            if base_rpx_name == "@self":
                base_rpx_name = name

            target.baseRpxName = base_rpx_name

        ### Modules Removal List Reading ###
        # print("%s Modules Removal List Reading" % target_field_name)

        if "Remove/Modules" in obj:
            modules_names = obj["Remove/Modules"]
            if modules_names is not None:
                if not isinstance(modules_names, list):
                    error("In %s, expected \"Remove/Modules\" to be a list of strings" % target_field_name)
                    return None

                modules_names_set = []
                remove_modules_field_name = "%s \"Remove/Modules\"" % target_field_name

                for filename in modules_names:
                    filename = proj.processString(remove_modules_field_name, filename, error=error)
                    if filename is None:
                        return None

                    file_path = filename + ".yaml"
                    if not os.path.isabs(file_path):
                        file_path = os.path.join(modulesBaseDir, file_path)

                    file_path = normalize_path(file_path)
                    if file_path not in modules_names_set:
                        modules_names_set.append(file_path)

                target.remove_Modules = modules_names_set

        ### Modules Addition List Reading ###
        # print("%s Modules Addition List Reading" % target_field_name)

        if "Add/Modules" in obj:
            modules_names = obj["Add/Modules"]
            if modules_names is not None:
                if not isinstance(modules_names, list):
                    error("In %s, expected \"Add/Modules\" to be a list of strings" % target_field_name)
                    return None

                modules_names_set = []
                add_modules_field_name = "%s \"Add/Modules\"" % target_field_name

                for filename in modules_names:
                    filename = proj.processString(add_modules_field_name, filename, error=error)
                    if filename is None:
                        return None

                    file_path = filename + ".yaml"
                    if not os.path.isabs(file_path):
                        file_path = os.path.join(modulesBaseDir, file_path)

                    file_path = normalize_path(file_path)
                    if file_path not in modules_names_set:
                        modules_names_set.append(file_path)

                for file_path in modules_names_set:
                    if file_path in target.remove_Modules:
                        error("In %s, trying to add module that needs to be removed within the same target: %s" % (target_field_name, file_path))
                        return None

                modules = {}

                for file_path in modules_names_set:
                    if file_path in proj.fileCache:
                        # print("Already cached: %s" % file_path)
                        module = proj.fileCache[file_path]

                    else:
                        module = Module.fromYaml(file_path, proj, error)
                        if module is None:
                            return None

                        proj.fileCache[file_path] = module

                    modules[file_path] = module

                target.add_Modules = modules

        ### Build Options Removal List Reading ###
        # print("%s Build Options Removal List Reading" % target_field_name)

        if "Remove/BuildOptions" in obj:
            build_options = obj["Remove/BuildOptions"]
            if build_options is not None:
                if not isinstance(build_options, list):
                    error("In %s, expected \"Remove/BuildOptions\" to be a list of strings" % target_field_name)
                    return None

                new_build_options = []
                remove_build_options_field_name = "%s \"Remove/BuildOptions\"" % target_field_name

                for option in build_options:
                    option = proj.processString(remove_build_options_field_name, option, error=error)
                    if option is None:
                        return None

                    option = option.strip()
                    if not option:
                        error("In %s, option is empty string" % remove_build_options_field_name)
                        return None

                    if option in new_build_options:
                        error("In %s, option has multiple occurrences: %r" % (remove_build_options_field_name, option))
                        return None

                    new_build_options.append('\t' + option)

                target.remove_BuildOptions = new_build_options

        ### Build Options Addition List Reading ###
        # print("%s Build Options Addition List Reading" % target_field_name)

        if "Add/BuildOptions" in obj:
            build_options = obj["Add/BuildOptions"]
            if build_options is not None:
                if not isinstance(build_options, list):
                    error("In %s, expected \"Add/BuildOptions\" to be a list of strings" % target_field_name)
                    return None

                new_build_options = []
                add_build_options_field_name = "%s \"Add/BuildOptions\"" % target_field_name

                for option in build_options:
                    option = proj.processString(add_build_options_field_name, option, error=error)
                    if option is None:
                        return None

                    option = option.strip()
                    if not option:
                        error("In %s, option is empty string" % add_build_options_field_name)
                        return None

                    if option in new_build_options:
                        error("In %s, option has multiple occurrences: %r" % (add_build_options_field_name, option))
                        return None

                    new_build_options.append('\t' + option)

                target.add_BuildOptions = new_build_options

        ### Success ###
        # print("%s Success" % target_field_name)

        return target
