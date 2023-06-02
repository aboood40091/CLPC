#!/usr/bin/env python3
# -*- coding: utf-8 -*-


# Built-in
# from json import dumps as json_dumps
import os


# Local
from .common import IsValidFilename
from .common import NormalizePath
from .common import WUAPPS_VERSION_MAX, WUAPPS_VERSION_MAX_STR
from .common import WUAPPS_VERSION_MIN, WUAPPS_VERSION_MIN_STR
from .module import Module
from .symlang.parser import AddressConversionMap
from .symlang.parser import SymbolMap
from .symlang.reader import TokenReader
from .target import Target


# External
import yaml


class Project:
    def __init__(self, path):
        normalize_path = NormalizePath

        if not os.path.isabs(path):
            path = os.path.abspath(path)

        path = normalize_path(path)
        self.path = path

        self.name = None
        self.variables = []
        self.modulesBaseDir = path
        self.srcBaseDir = None
        self.includeDirs = [normalize_path(os.path.join(path, "include"))]
        self.rpxDir = normalize_path(os.path.join(path, "rpxs"))
        self.modules = {}
        self.buildOptions = []
        self.targets = {}
        self.symbols = {}

        self.defaultBuildOptions = {
            "-c99":                     None,
            "--g++":                    None,
            "--link_once_templates":    None,
            "--enable_noinline":        None,
            "--max_inlining":           None,
            "--no_exceptions":          None,
            "--no_rtti":                None,
            "--no_implicit_include":    None,
            "-no_ansi_alias":           None,
            "-only_explicit_reg_use":   None,
            "-kanji":                   "shiftjis",
            "-Ospeed":                  None,
            "-Onounroll":               None
        }

        self.minAlign = {
            ".text":    0x20,
            ".rodata":  0x20,
            ".data":    0x20,
            ".bss":     0x40
        }

        self.fileCache = {}

    def processVariables(self, s, error=print):
        variables = self.variables

        s_parts = s.split('$')
        s_new_parts = [s_parts[0]]

        for part in s_parts[1:]:
            for k, v in variables:
                if part.startswith(k):
                    part = v + part[len(k):]
                    break

            else:
                error("Unable to process variables in string: %r" % s)
                return None

            s_new_parts.append(part)

        return ''.join(s_new_parts)

    def readString(self, obj, key, field_name, default=None, allow_explicit_null=False, allow_empty=False, error=print):
        """
        Notes:
        * 'default' is None <-> Field is required.
        * 'default' == '' -> 'allow_empty' must be True.
        * 'allow_explicit_null' is True -> Field must be optional (i.e., 'default' must not be None).
        """

        assert not allow_explicit_null or default is not None
        assert default != '' or allow_empty

        if key not in obj:
            if default is None:
                error("%s not specified" % field_name)
                return None

            else:
                # print("return default")
                return default

        s = obj[key]
        if s is None:
            if allow_explicit_null:  # and default is not None: (This should be guaranteed at this stage)
                # print("return default (allow_explicit_null)")
                return default

            s_valid = False

        elif s == '':
            if allow_empty:
                # print("return \"\" (allow_empty)")
                return ''

            s_valid = False

        else:
            s_valid = isinstance(s, str)
            if s_valid:
                s = self.processVariables(s, error)
                if s is None:
                    # print("return None (processVariables)")
                    return None

                if s == '':
                    if allow_empty:
                        # print("return \"\" (allow_empty after processVariables)")
                        return ''

                    s_valid = False

        if not s_valid:
            error("%s is invalid" % field_name)
            return None

        # print(s)
        return s

    def processString(self, field_name, s, allow_empty=False, error=print):
        if s == '':
            if allow_empty:
                # print("return \"\" (allow_empty)")
                return ''

            s_valid = False

        else:
            s_valid = isinstance(s, str)
            if s_valid:
                s = self.processVariables(s, error)
                if s is None:
                    # print("return None (processVariables)")
                    return None

                if s == '':
                    if allow_empty:
                        # print("return \"\" (allow_empty after processVariables)")
                        return ''

                    s_valid = False

        if not s_valid:
            error("Invalid value in %s: %r" % (field_name, s))
            return None

        # print(s)
        return s

    @staticmethod
    def fromYaml(file_path, error=print):
        normalize_path = NormalizePath

        ### File Loading ###
        # print("Project File Loading")

        if not os.path.isfile(file_path):
            error("File does not exist: %r" % file_path)
            return None

        with open(file_path, encoding="utf8") as inf:
            obj = yaml.safe_load(inf)

        if not isinstance(obj, dict):
            error("Unexpected file format for file: %r" % file_path)
            return None

        path = os.path.dirname(file_path)
        if not os.path.isabs(path):
            path = os.path.abspath(path)

        path = normalize_path(path)

        ### Selected Options Sanity Check ###
        # print("Selected Options Sanity Check")

        available_options = (
            "WUAPPSVersion",
            "Name",
            "Variables",
            "ModulesBaseDir",
            "SourcesBaseDir",
            "IncludeDirs",
            "RpxDir",
            "ExcludeDefaultBuildOptions",
            "MinAlign",
            "Modules",
            "BuildOptions",
            "Targets"
        )

        for k in obj:
            if k not in available_options:
                error("Unrecognized option: %r" % k)
                return None

        ### Project Initialization ###
        # print("Project Initialization")

        proj = Project(path)

        ### Variables Reading ###
        # print("Variables Reading")

        if "Variables" in obj:
            variables = obj["Variables"]
            if variables is not None:
                if not isinstance(variables, dict):
                    error("Expected \"Variables\" to be a key-value mapping")
                    return None

                is_str = lambda s: isinstance(s, str)
                is_non_null_str = lambda s: s and is_str(s)
                is_valid_key = lambda k: is_non_null_str(k) and k.isidentifier()

                for k, v in variables.items():
                    if not is_valid_key(k):
                        error("Invalid key in \"Variables\": %r" % k)
                        return None

                    if not is_str(v):
                        error("Invalid value for key in \"Variables\": (%r, %r)" % (k, v))
                        return None

                proj.variables = tuple(sorted(variables.items(), key=lambda item: len(item[0]), reverse=True))

        ### Version Check ###
        # print("Version Check")

        version_str = proj.readString(obj, "WUAPPSVersion", "WUAPPS Version", error=error)
        if version_str is None:
            return None

        try:
            major, minor = map(int, version_str.split('.'))
        except ValueError:
            error("Unexpected WUAPPSVersion format: %r" % version_str)
            return None

        if major < WUAPPS_VERSION_MIN[0] or \
           minor < WUAPPS_VERSION_MIN[1] and major == WUAPPS_VERSION_MIN[0] or \
           major > WUAPPS_VERSION_MAX[0] or \
           minor > WUAPPS_VERSION_MAX[1] and major == WUAPPS_VERSION_MAX[0]:
            error("Version mismatch,\n"
                  "Specified version: %r,\n"
                  "Latest supported version: %r,\n"
                  "Minimum supported version: %r" % (version_str, WUAPPS_VERSION_MAX_STR, WUAPPS_VERSION_MIN_STR))
            return None

        ### Project Name Reading ###
        # print("Project Name Reading")

        name = proj.readString(obj, "Name", "Project Name", error=error)
        if name is None:
            return None

        proj.name = name

        ### Modules Base Directory Reading ###
        # print("Modules Base Directory Reading")

        modulesBaseDir = proj.readString(obj, "ModulesBaseDir", "Modules Base Directory", 0x01020304, error=error)
        if modulesBaseDir is None:
            return None

        if modulesBaseDir == 0x01020304:
            modulesBaseDir = path

        elif not os.path.isabs(modulesBaseDir):
            modulesBaseDir = os.path.join(path, modulesBaseDir)

        proj.modulesBaseDir = normalize_path(modulesBaseDir)

        ### Sources Base Directory Reading ###
        # print("Sources Base Directory Reading")

        srcBaseDir = proj.readString(obj, "SourcesBaseDir", "Sources Base Directory", 0x01020304, error=error)
        if srcBaseDir is None:
            return None

        if srcBaseDir != 0x01020304:
            if not os.path.isabs(srcBaseDir):
                srcBaseDir = os.path.join(path, srcBaseDir)

            proj.srcBaseDir = normalize_path(srcBaseDir)

        ### Include Directories List Reading ###
        # print("Include Directories List Reading")

        if "IncludeDirs" in obj:
            include_dirs = obj["IncludeDirs"]
            if include_dirs is not None:
                if not isinstance(include_dirs, list):
                    error("Expected \"IncludeDirs\" to be a list of strings")
                    return None

                include_dirs_set = []

                for include_dir in include_dirs:
                    include_dir = proj.processString("\"IncludeDirs\"", include_dir, error=error)
                    if include_dir is None:
                        return None

                    if not os.path.isabs(include_dir):
                        include_dir = os.path.join(path, include_dir)

                    include_dir = normalize_path(include_dir)
                    if include_dir not in include_dirs_set:
                        include_dirs_set.append(include_dir)

                proj.includeDirs = include_dirs_set

        ### RPX Files Directory Reading ###
        # print("RPX Files Directory Reading")

        rpxDir = proj.readString(obj, "RpxDir", "RPX Files Directory", 0x01020304, error=error)
        if rpxDir is None:
            return None

        if rpxDir != 0x01020304:
            if not os.path.isabs(rpxDir):
                rpxDir = os.path.join(path, rpxDir)

            proj.rpxDir = normalize_path(rpxDir)

        ### Excluded Default Build Options Reading ###
        # print("Excluded Default Build Options Reading")

        if "ExcludeDefaultBuildOptions" in obj:
            exclude = obj["ExcludeDefaultBuildOptions"]
            if isinstance(exclude, bool):
                if exclude:
                    proj.defaultBuildOptions = {}

            else:
                if not isinstance(exclude, list):
                    error("Expected \"ExcludeDefaultBuildOptions\" to be a list of strings")
                    return None

                exclude_set = []

                for option in exclude:
                    option = proj.processString("\"ExcludeDefaultBuildOptions\"", option, error=error)
                    if option is None:
                        return None

                    if option not in exclude_set:
                        exclude_set.append(option)

                build_options = proj.defaultBuildOptions

                for option in exclude_set:
                    if option not in build_options:
                        error("Unrecognized build option: %r" % option)
                        return None

                    del build_options[option]

        ### Minimum Align Reading ###
        # print("%s Minimum Align Reading" % module_field_name)

        if "MinAlign" in obj:
            align = obj["MinAlign"]
            if align is not None:
                if not isinstance(align, dict):
                    error("Expected \"MinAlign\" to be a key-value mapping")
                    return None

                is_positive_int = lambda v: isinstance(v, int) and v > 0
                is_pow_2 = lambda v: is_positive_int(v) and (v & (v - 1) == 0)
                is_valid_align = lambda v: is_pow_2(v) and v <= 0x2000

                proj_min_align = proj.minAlign

                for k, v in align.items():
                    if k not in proj_min_align:
                        error("In \"MinAlign\", unexpected key: %r" % k)
                        return None

                    if not is_valid_align(v):
                        error("In \"%s MinAlign\", expected value to be a power of 2 in range (0, 0x2000], received: %r" % (k, v))
                        return None

                    proj_min_align[k] = v

        ### Modules List Reading ###
        # print("Modules List Reading")

        if "Modules" in obj:
            modules_names = obj["Modules"]
            if modules_names is not None:
                if not isinstance(modules_names, list):
                    error("Expected \"Modules\" to be a list of strings")
                    return None

                modules_names_set = []

                for filename in modules_names:
                    filename = proj.processString("\"Modules\"", filename, error=error)
                    if filename is None:
                        return None

                    file_path = filename + ".yaml"
                    if not os.path.isabs(file_path):
                        file_path = os.path.join(modulesBaseDir, file_path)

                    file_path = normalize_path(file_path)
                    if file_path not in modules_names_set:
                        modules_names_set.append(file_path)

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

                proj.modules = modules

        ### Build Options List Reading ###
        # print("Build Options List Reading")

        if "BuildOptions" in obj:
            build_options = obj["BuildOptions"]
            if build_options is not None:
                if not isinstance(build_options, list):
                    error("Expected \"BuildOptions\" to be a list of strings")
                    return None

                new_build_options = []

                for option in build_options:
                    option = proj.processString("\"BuildOptions\"", option, error=error)
                    if option is None:
                        return None

                    option = option.strip()
                    if not option:
                        error("In \"BuildOptions\", option is empty string")
                        return None

                    if option in new_build_options:
                        error("In \"BuildOptions\", option has multiple occurrences: %r" % option)
                        return None

                    new_build_options.append('\t' + option)

                proj.buildOptions = new_build_options

        ### Targets List Reading ###
        # print("Targets List Reading")

        if "Targets" in obj:
            targets = obj["Targets"]
            if targets is not None:
                if not isinstance(targets, dict):
                    error("Expected \"Targets\" to be a key-value mapping")
                    return None

                is_str = lambda s: isinstance(s, str)
                is_non_null_str = lambda s: s and is_str(s)

                is_valid_filename = IsValidFilename

                targets_new = {}

                for target_name, target_obj in targets.items():
                    if not is_non_null_str(target_name):
                        error("Invalid Target name: %r" % target_name)
                        return None

                    if not is_valid_filename(target_name):
                        error("Target name is invalid (cannot be used as filename): %r" % target_name)
                        return None

                    target = Target.fromObj(target_obj, target_name, proj, error)
                    if target is None:
                        return None

                    targets_new[target_name] = target

                ### Target Bases List Creation ###

                for target_name, target in targets_new.items():
                    bases = target.bases
                    # assert not bases

                    for base_name in target.baseNames:
                        if base_name not in targets_new:
                            error("Target %r is trying to extend non-existent target %r" % (target_name, base_name))
                            return None

                        bases.append(targets_new[base_name])

                ### Target Bases List Join ###

                for target_name, target in targets_new.items():
                    bases = target.bases
                    if bases:
                        base = Target()
                        base.copy(bases[0])

                        target_field_name = "Target %r" % target_name

                        for other_base in bases[1:]:
                            if not base.join(other_base, target_field_name, error):
                                return None

                        # print("%s has base: %r" % (target_field_name, base.name))
                        target.base = base

                    # else:
                    #     assert not target.base

                ### Target Extension Cycle Detection ###

                cycles_resolved = []

                for target_name, target in targets_new.items():
                    current = target
                    bases = [current]
                    while current.base is not None:
                        base = current.base
                        if base in cycles_resolved:
                            break

                        if base in bases:
                            error("Detected cycle while trying to resolve bases for target: %r" % target_name)
                            return None

                        bases.append(base)
                        current = base

                    cycles_resolved.extend(bases)

                ## Target Address Conversion Map Reading ###

                for target_name, target in targets_new.items():
                    if target.isAbstract:
                        continue

                    addr_map_name = target.addrMapName
                    if addr_map_name == "@inherit":
                        target_field_name = "Target %r" % target_name

                        prev_base = target
                        base = target.base

                        while base is not None:
                            if base.addrMapName != "@inherit":
                                break

                            prev_base = base
                            base = base.base

                        else:
                            if target == prev_base:
                                error("In %s, \"AddrMap\" is set to inherit non-existing base" % target_field_name)
                            else:
                                error("While processing %s, in base(s) %r, \"AddrMap\" is set to inherit non-existing base" % (target_field_name, prev_base.name))

                            return None

                        addr_map_name = base.addrMapName
                        target.addrMapName = addr_map_name

                    if addr_map_name is not None:
                        addr_map_path = normalize_path(os.path.join(proj.path, "maps/%s.convmap" % addr_map_name))
                        if addr_map_path in proj.fileCache:
                            # print("Already cached: %s" % addr_map_path)
                            target.addrMap = proj.fileCache[addr_map_path]

                        elif os.path.isfile(addr_map_path):
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

                                else:
                                    proj.fileCache[addr_map_path] = target.addrMap

                            finally:
                                reader.closeFile()

                        else:
                            error("In %s,\n"
                                  "Address conversion map file not found: %r\n"
                                  "Path resolved to: %r" % (target_field_name, addr_map_name, addr_map_path))
                            return None

                ### Target Base RPX Filename Resolution ###

                for target_name, target in targets_new.items():
                    if target.baseRpxName == "@inherit":
                        target_field_name = "Target %r" % target_name

                        prev_base = target
                        base = target.base

                        while base is not None:
                            if base.baseRpxName != "@inherit":
                                break

                            prev_base = base
                            base = base.base

                        else:
                            if target == prev_base:
                                error("In %s, \"BaseRpx\" is set to inherit non-existing base" % target_field_name)
                            else:
                                error("While processing %s, in base %r, \"BaseRpx\" is set to inherit non-existing base" % (target_field_name, prev_base.name))

                            return None

                        target.baseRpxName = base.baseRpxName

                ### Targets List Reading Success ###

                proj.targets = targets_new

        ### Symbol Map Reading ###

        sym_map_path = normalize_path(os.path.join(path, "maps/main.map"))
        if sym_map_path in proj.fileCache:
            # print("Already cached: %s" % sym_map_path)
            proj.symbols = proj.fileCache[sym_map_path]

        elif os.path.isfile(sym_map_path):
            reader = TokenReader()
            reader.openFile(sym_map_path)

            try:
                is_valid, syms = SymbolMap.start(reader)
                if not is_valid:
                    line, col = reader.indexToCoordinates(reader.file_str, reader.nextToken.srcPosAt)
                    error("In file: %s\n"
                          "At line %d, column %d: syntax error" % (sym_map_path, line, col))
                    return None

                try:
                    proj.symbols = SymbolMap.resolve(reader, syms)

                except Exception as e:
                    error("In file: %s\n"
                          "%s" % (sym_map_path, e))
                    return None

                else:
                    proj.fileCache[sym_map_path] = proj.symbols
                    # print(json_dumps(proj.symbols, indent=2))

            finally:
                reader.closeFile()

        ### Success ###
        # print("Success")

        return proj
