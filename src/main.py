#!/usr/bin/env python3
# -*- coding: utf-8 -*-


from clpc import Project
from json import dumps as json_dumps
import os


def NormalizePath(path):
    return os.path.normcase(os.path.normpath(path))


def printModule(name, module, base_indent_level):
    indent_level = base_indent_level

    def print_indent(*args, **kargs):
        nonlocal indent_level
        print("  " * indent_level, end='')
        print(*args, **kargs)

    print_indent(name)

    indent_level += 1

    strings = (
        "\"C\" Files:",
        "\"C++\" Files:",
        "\"Assembly\" Files:",
    )

    for i, files in enumerate(module.files):
        if not files:
            continue

        print_indent(strings[i])

        indent_level += 1

        for file_path in files:
            print_indent(file_path)

        indent_level -= 1

    indent_level -= 1


def main():
    def error(*args, **kargs):
        print("While trying to parse project, encountered the following error:\n")
        print(*args, **kargs)

    file_path = input("Enter project.yaml path: ")
    proj = Project.fromYaml(file_path, error=error)
    if proj is None:
        return

    print()
    print("Project Name:", repr(proj.name))
    print("Project Path:", NormalizePath(proj.path))

    if proj.variables:
        print("Project Variables:")
        for item in proj.variables:
            print("  %s: %r" % item)

    print("Modules Base Directory:", NormalizePath(proj.modulesBaseDir))
    if proj.srcBaseDir:
        print("Sources Base Directory:", NormalizePath(proj.srcBaseDir))

    if proj.includeDirs:
        print("Include Directories:")
        for item in sorted(proj.includeDirs):
            print("  %s" % item)

    print("RPX Files Directory:", proj.rpxDir)

    print("Default Build Options:", json_dumps(proj.defaultBuildOptions, sort_keys=True, indent=2))

    print("Project Defines:", json_dumps(proj.defines, sort_keys=True, indent=2))

    if proj.modules:
        print("Project Modules:")
        for name, module in sorted(proj.modules.items(), key=lambda item: item[0]):
            printModule(name, module, 1)

    if proj.templates:
        print("Project Templates:")
        for name, template in sorted(proj.templates.items(), key=lambda item: item[0]):
            print("  %s" % name)

    if proj.targets:
        print("Project Targets:")
        for name, target in sorted(proj.targets.items(), key=lambda item: item[0]):
            print("  %s" % name)


if __name__ == "__main__":
    main()
