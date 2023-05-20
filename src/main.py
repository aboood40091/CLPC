#!/usr/bin/env python3
# -*- coding: utf-8 -*-


from clpc import Project
from json import dumps as json_dumps
import os


def NormalizePath(path):
    return os.path.normcase(os.path.normpath(path))


def main():
    file_path = input("Enter project.yaml path: ")
    proj = Project.fromYaml(file_path)
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

    print("Address Offsets Maps Extension:", proj.addrMapExt)

    print("Project Defines:", json_dumps(proj.defines, sort_keys=True, indent=2))

    if proj.modules:
        print("Project Modules:")
        for item in sorted(proj.modules.keys()):
            print("  %s" % item)

    if proj.templates:
        print("Project Templates:")
        for item in sorted(proj.templates.keys()):
            print("  %s" % item)

    if proj.targets:
        print("Project Targets:")
        for item in sorted(proj.targets.keys()):
            print("  %s" % item)


if __name__ == "__main__":
    main()
