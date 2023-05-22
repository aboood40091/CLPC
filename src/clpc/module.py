#!/usr/bin/env python3
# -*- coding: utf-8 -*-


# Built-in
import glob
import os


# Local
from .common import IsValidFilename
from .common import NormalizePath
from .hook import BranchHook
from .hook import FuncPtrHook
from .hook import NOPHook
from .hook import PatchHook
from .hook import ReturnHook


# External
import yaml


class Module:
    def __init__(self, path):
        if not os.path.isabs(path):
            path = os.path.abspath(path)

        self.path = path

        self.files = ([], [], [])
        self.hooks = []

    def readFileList(self, obj, key, idx, module_field_name, proj, error=print):
        files_new = self.files[idx]
        files_new.clear()

        if key not in obj:
            return True

        files = obj[key]
        if files is None:
            return True

        field_name = "\"%s\" Files List" % key

        if not isinstance(files, list):
            error("In %s, expected %s to be a list of strings" % (module_field_name, field_name))
            return False

        field_name_full = "%s in %s" % (field_name, module_field_name)
        srcBaseDir = proj.srcBaseDir if proj.srcBaseDir is not None else self.path

        files_set = set()
        normalize_path = NormalizePath
        join_path = os.path.join
        is_file = os.path.isfile
        i_glob = glob.iglob
        is_valid_filename = IsValidFilename

        for file_path in files:
            base_file_path = file_path

            file_path = proj.processString(field_name_full, file_path, error=error)
            if file_path is None:
                return False

            if not os.path.isabs(file_path):
                file_path = join_path(srcBaseDir, file_path)

            file_path = normalize_path(file_path)
            dir_path, filename = os.path.split(file_path)

            if filename.startswith("*."):
                if len(filename) == 2 or not is_valid_filename(filename[1:]):
                    error("In %s, folder scan path contains an invalid extension: %r" % (field_name_full, base_file_path))
                    return False

                scan_path = join_path(dir_path, '*' + filename)
                scan_files = (scan_file_path for scan_file_path in i_glob(scan_path, recursive=True) if is_file(scan_file_path))
                for scan_file_path in scan_files:
                    files_set.add(normalize_path(scan_file_path))

            elif filename.startswith("**."):
                if len(filename) == 3 or not is_valid_filename(filename[2:]):
                    error("In %s, folder recursive scan path contains an invalid extension: %r" % (field_name_full, base_file_path))
                    return False

                scan_path = join_path(dir_path, "**", filename)
                scan_files = (scan_file_path for scan_file_path in i_glob(scan_path, recursive=True) if is_file(scan_file_path))
                for scan_file_path in scan_files:
                    files_set.add(normalize_path(scan_file_path))

            else:
                if not is_file(file_path):
                    error("In %s,\n"
                          "File not found: %r\n"
                          "Path resolved to: %r" % (field_name_full, base_file_path, file_path))
                    return False

                files_set.add(file_path)

        files_new.extend(files_set)

        # for file_path in files_new:
        #     print(file_path)

        return True

    @staticmethod
    def fromYaml(file_path, proj, error=print):
        ### File Loading ###
        # print("Module File Loading:", file_path)

        if not os.path.isfile(file_path):
            error("File does not exist: %r" % file_path)
            return None

        with open(file_path, encoding="utf8") as inf:
            obj = yaml.safe_load(inf)

        if not isinstance(obj, dict):
            error("Unexpected file format for file: %r" % file_path)
            return None

        path, name = os.path.split(file_path)
        if not os.path.isabs(path):
            path = os.path.abspath(path)

        name = os.path.splitext(name)[0]
        module_field_name = "Module %r" % name

        ### Selected Options Sanity Check ###
        # print("%s Selected Options Sanity Check" % module_field_name)

        available_options = (
            "Files",
            "Hooks"
        )

        available_options_error_msg = "Unrecognized option in %s: %s" % (module_field_name, "%r")

        for k in obj:
            if k not in available_options:
                error(available_options_error_msg % k)
                return None

        ### Module Initialization ###
        # print("%s Module Initialization" % module_field_name)

        module = Module(path)

        ### Files List Reading ###
        # print("%s Files List Reading" % module_field_name)

        if "Files" in obj:
            file_lists = obj["Files"]
            if file_lists is not None:
                if not isinstance(file_lists, dict):
                    error("In %s, expected \"Files\" to be a key-value mapping" % module_field_name)
                    return None

                ### Files List Selected Options Sanity Check ###
                # print("%s Files List Selected Options Sanity Check" % module_field_name)

                files_available_options = (
                    "C",
                    "C++",
                    "Assembly"
                )

                files_available_options_error_msg = "Unrecognized option in \"Files\" in %s: %s" % (module_field_name, "%r")

                for k in file_lists:
                    if k not in files_available_options:
                        error(files_available_options_error_msg % k)
                        return None

                ### C Files List Reading ###
                # print("%s C Files List Reading" % module_field_name)

                if not module.readFileList(file_lists, "C",         0, module_field_name, proj, error):
                    return None

                ### C++ Files List Reading ###
                # print("%s C++ Files List Reading" % module_field_name)

                if not module.readFileList(file_lists, "C++",       1, module_field_name, proj, error):
                    return None

                ### Assembly Files List Reading ###
                # print("%s Assembly Files List Reading" % module_field_name)

                if not module.readFileList(file_lists, "Assembly",  2, module_field_name, proj, error):
                    return None

        ### Hooks List Reading ###
        # print("%s Hooks List Reading" % module_field_name)

        if "Hooks" in obj:
            hooks = obj["Hooks"]
            if hooks is not None:
                hooks_error_msg = "In %s, expected \"Hooks\" to be a list of key-value mappings" % module_field_name
                if not isinstance(hooks, list):
                    error(hooks_error_msg)
                    return None

                hooks_new = []
                hook_type_field_name = "%s Hook Type" % module_field_name
                hook_type_error_msg = "%s is invalid" % hook_type_field_name

                for hook_obj in hooks:
                    if not isinstance(hook_obj, dict):
                        error(hooks_error_msg)
                        return None

                    type_ = proj.readString(hook_obj, "type", hook_type_field_name, error=error)
                    if type_ is None:
                        return None

                    if type_ == "patch":
                        hook = PatchHook.fromObj(hook_obj, module_field_name, proj, error)
                        if hook is None:
                            return None

                    elif type_ == "nop":
                        hook = NOPHook.fromObj(hook_obj, module_field_name, proj, error)
                        if hook is None:
                            return None

                    elif type_ == "return":
                        hook = ReturnHook.fromObj(hook_obj, module_field_name, proj, error)
                        if hook is None:
                            return None

                    elif type_ == "branch":
                        hook = BranchHook.fromObj(hook_obj, module_field_name, proj, error)
                        if hook is None:
                            return None

                    elif type_ == "funcptr":
                        hook = FuncPtrHook.fromObj(hook_obj, module_field_name, proj, error)
                        if hook is None:
                            return None

                    else:
                        error(hook_type_error_msg)
                        return None

                    hooks_new.append(hook)

                module.hooks = hooks_new

        ### Success ###
        # print("%s Success" % module_field_name)

        return module
