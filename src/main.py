#!/usr/bin/env python3
# -*- coding: utf-8 -*-


from clpc.common import align
from clpc.common import PACK_U16
from clpc.common import PACK_U32
from clpc import Project
from clpc.symlang.addrConv import PlatformType
from clpc.elf import ELF, readString as elf_readString
import glob
import os
import struct
import subprocess
import zlib


# Change the following (use / instead of \)
GHS_PATH = "D:/Greenhills/ghs/multi5327"
wiiurpxtool = "D:/NSMBU RE/v1.3.0/code/wiiurpxtool.exe"


GPJ_TEMPLATE = """#!gbuild
primaryTarget=ppc_cos_ndebug.tgt
[Project]
\t-object_dir="%s"
\t--no_commons
\t-cpu=espresso
\t-sda=none
\t-MD
\t-Dcafe"""

LD_TEMPLATE = """
MEMORY
{
    codearea : origin = 0x%08X, length = 0x%08X
    dataarea : origin = 0x%08X, length = 0x%08X
}

OPTION("-append")

SECTIONS
{
 // .syscall    ALIGN(0x0020)   :   > codearea
    .text       ALIGN(0x%04X)   :   > codearea

    .rodata     ALIGN(0x%04X)   :   > dataarea
    .data       ALIGN(0x%04X)   :   > dataarea
 // .module_id  ALIGN(0x0020)   :   > dataarea
    .bss        ALIGN(0x%04X)   :   > dataarea
}
"""

MAP_TEMPLATE = """
SECTIONS {

%s

}
"""


def buildProject(proj, target_name, platform_type, error=print):
    platform_names = {
        PlatformType.Emulator: "Emulator",
        PlatformType.CafeLoader: "CafeLoader"
    }

    if platform_type not in platform_names:
        error("Unrecognized platform target: %r" % platform_type)
        return False

    platform_name = platform_names[platform_type]

    proj_name = proj.name

    print("\n*** Building %r from %r for platform %r ***\n" % (target_name, proj_name, platform_name))

    if target_name not in proj.targets:
        error("Invalid target: %r", target_name)
        return False

    target = proj.targets[target_name]
    if target.isAbstract:
        error("Invalid target: %r", target_name)
        return False

    bases = [target]
    base = target.base
    while base is not None:
        bases.append(base)
        base = base.base

    modules = dict(proj.modules)
    build_options = list(proj.buildOptions)

    target_field_name = "Target %r" % target_name

    for base in reversed(bases):
        for module_name in base.remove_Modules:
            if module_name in modules:
                del modules[module_name]

        for module_name, module in base.add_Modules.items():
            if module_name in modules:
                error("In %s, trying to add module from base %r that already exists in chain:\n"
                      "%s" % (target_field_name, base.name, module_name))
                return False

            modules[module_name] = module

        for option in base.remove_BuildOptions:
            if option in build_options:
                build_options.remove(option)

        for option in base.add_BuildOptions:
            if option in build_options:
                error("In %s, trying to add build option from base %r that already exists in chain:\n"
                      "%s" % (target_field_name, base.name, option))
                return False

            build_options.append(option)

    path = proj.path

    temp_path = os.path.join(path, "temp")
    if not os.path.isdir(temp_path):
        os.mkdir(temp_path)
        assert os.path.isdir(temp_path)

    platform_temp_path = os.path.join(temp_path, platform_name)
    if not os.path.isdir(platform_temp_path):
        os.mkdir(platform_temp_path)
        assert os.path.isdir(platform_temp_path)

    proj_temp_path = os.path.join(platform_temp_path, proj_name)
    if not os.path.isdir(proj_temp_path):
        os.mkdir(proj_temp_path)
        assert os.path.isdir(proj_temp_path)

    target_temp_path = os.path.join(proj_temp_path, target_name)
    if not os.path.isdir(target_temp_path):
        os.mkdir(target_temp_path)
        assert os.path.isdir(target_temp_path)

    obj_path = os.path.join(target_temp_path, "obj")
    if not os.path.isdir(obj_path):
        os.mkdir(obj_path)
        assert os.path.isdir(obj_path)

    out_path = os.path.join(path, "out")
    if not os.path.isdir(out_path):
        os.mkdir(out_path)
        assert os.path.isdir(out_path)

    platform_out_path = os.path.join(out_path, platform_name)
    if not os.path.isdir(platform_out_path):
        os.mkdir(platform_out_path)
        assert os.path.isdir(platform_out_path)

    proj_out_path = os.path.join(platform_out_path, proj_name)
    if not os.path.isdir(proj_out_path):
        os.mkdir(proj_out_path)
        assert os.path.isdir(proj_out_path)

    if platform_type == PlatformType.CafeLoader:
        target_out_path = os.path.join(proj_out_path, target_name)
        if not os.path.isdir(target_out_path):
            os.mkdir(target_out_path)
            assert os.path.isdir(target_out_path)

    text_align      = proj.minAlign[".text"]
    rodata_align    = proj.minAlign[".rodata"]
    data_align      = proj.minAlign[".data"]
    bss_align       = proj.minAlign[".bss"]

    for module in modules.values():
        text_align      = max(module.align[".text"],    text_align)
        rodata_align    = max(module.align[".rodata"],  rodata_align)
        data_align      = max(module.align[".data"],    data_align)
        bss_align       = max(module.align[".bss"],     bss_align)

    is_pow_2 = lambda x: x > 0 and (x & (x - 1) == 0)
    assert is_pow_2(text_align)
    assert is_pow_2(rodata_align)
    assert is_pow_2(data_align)
    assert is_pow_2(bss_align)

    text_align_all = text_align
    data_align_all = max(rodata_align, data_align, bss_align)

    addrconv = target.addrMap

    if platform_type == PlatformType.CafeLoader:
        if addrconv is None:
            error("In %s, building for CafeLoader Console target, but Address Conversion Map file is not specified" % target_field_name)
            return None

        if None in addrconv:
            error("In %s, building for CafeLoader Console target requires specifying TextAddr and DataAddr in Address Conversion Map" % target_field_name)
            return None

        base_text_addr, base_data_addr, platforms = addrconv
        base_data_addr += 4  # Account for WHBLogPrintf address

    elif platform_type == PlatformType.Emulator:
        if addrconv is not None:
            platforms = addrconv[2]

        rpx_dir_path = proj.rpxDir
        assert rpx_dir_path is not None

        base_rpx_filename = target.baseRpxName
        if base_rpx_filename is None:
            error("In %s, building for Emulator target, but RPX file is not specified" % target_field_name)
            return False

        base_rpx_path = os.path.join(rpx_dir_path, "%s.rpx" % base_rpx_filename)
        if not os.path.isfile(base_rpx_path):
            error("In %s, building for Emulator target, but RPX file does not exist:\n"
                  "%s" % (target_field_name, base_rpx_path))
            return False

        base_elf_path = os.path.join(rpx_dir_path, "%s.elf" % base_rpx_filename)

        print("Decompressing RPX...")
        if not os.path.isfile(base_elf_path):
            DETACHED_PROCESS = 0x00000008
            subprocess.call("\"%s\" -d \"%s\" \"%s\"" % (wiiurpxtool, base_rpx_path, base_elf_path), creationflags=DETACHED_PROCESS)

            assert os.path.isfile(base_elf_path)

        print("Loading ELF...\n")
        base_elf = ELF(base_elf_path)

        rpl_fileinfo = base_elf.secHeadEnts.pop()
        if rpl_fileinfo.type != 0x80000004:
            error("In %s, could not find SHT_RPL_FILEINFO in RPX file:\n"
                  "%s" % (target_field_name, base_rpx_path))
            return False

        rpl_fileinfo_data = rpl_fileinfo.data
        if len(rpl_fileinfo_data) < 0x14:
            error("In %s, SHT_RPL_FILEINFO data is malformed (unexpected end of data) in RPX file:\n"
                  "%s" % (target_field_name, base_rpx_path))
            return False

        magic = struct.unpack_from(">I", rpl_fileinfo_data)[0]
        if magic != 0xCAFE0402:
            error("In %s, SHT_RPL_FILEINFO data is malformed (invalid magic) in RPX file:\n"
                  "%s" % (target_field_name, base_rpx_path))
            return False

        rpl_crcs = base_elf.secHeadEnts.pop()
        if rpl_crcs.type != 0x80000003:
            error("In %s, could not find SHT_RPL_CRCS in RPX file:\n"
                  "%s" % (target_field_name, base_rpx_path))
            return False

        base_text_end = max(entry.vAddr + entry.size_ for entry in base_elf.secHeadEnts if 0x02000000 <= entry.vAddr < 0x10000000)
        base_data_end = max(entry.vAddr + entry.size_ for entry in base_elf.secHeadEnts if 0x10000000 <= entry.vAddr < 0xC0000000)
        base_dyna_end = max(entry.vAddr + entry.size_ for entry in base_elf.secHeadEnts if 0xC0000000 <= entry.vAddr < 0xC8000000)

        base_text_addr  = base_text_end
        base_data_addr  = base_data_end
        syms_addr       = base_dyna_end

    f_align = align
    text_addr = f_align(base_text_addr, text_align_all)
    data_addr = f_align(base_data_addr, data_align_all)

    if platform_type == PlatformType.CafeLoader:
        pack_u32 = PACK_U32

        addrdata = pack_u32(text_addr) + pack_u32(data_addr)

        addr_out_path = os.path.join(target_out_path, "Addr.bin")
        with open(addr_out_path, "wb") as outf:
            outf.write(addrdata)

    gpj_str_lst = [
        GPJ_TEMPLATE % obj_path.replace('\\', '/'),
        "\t-DPLATFORM_IS_EMULATOR=%d" % int(platform_type == PlatformType.Emulator),
        "\t-DPLATFORM_IS_CONSOLE=%d" % int(platform_type != PlatformType.Emulator),
        "\t-DPLATFORM_IS_CONSOLE_CAFELOADER=%d" % int(platform_type == PlatformType.CafeLoader),
        "\t-DTEXT_ADDR=0x%08X" % text_addr,
        "\t-DDATA_ADDR=0x%08X" % data_addr,
    ]

    gpj_str_lst.extend(
        ("\t%s=%s" % (option, value)) if value is not None
        else ('\t' + option)
        for option, value in proj.defaultBuildOptions.items()
    )

    gpj_str_lst.extend(
        ("\t-I\"%s\"" % str(dir_path).replace('\\', '/'))
        for dir_path in proj.includeDirs
    )

    gpj_str_lst.extend(build_options)

    for module in modules.values():
        gpj_str_lst.extend([("%s [C]"           % str(file_path).replace('\\', '/')) for file_path in module.files[0]])
        gpj_str_lst.extend([("%s [C++]"         % str(file_path).replace('\\', '/')) for file_path in module.files[1]])
        gpj_str_lst.extend([("%s [Assembly]"    % str(file_path).replace('\\', '/')) for file_path in module.files[2]])

    gpj_str_lst.append('')
    gpj_str = '\n'.join(gpj_str_lst)

    gpj_path = os.path.join(target_temp_path, "%s.gpj" % proj_name)
    with open(gpj_path, 'w', encoding="utf8") as outf:
        outf.write(gpj_str)

    cmd = "\"%s\" -top \"%s\"" % (os.path.join(GHS_PATH, "gbuild"), gpj_path)
    error_code = subprocess.call(cmd)
    if error_code:
        error("Build failed!!\n"
              "Error code: %i" % error_code)
        return False

    obj_files = glob.glob(os.path.join(obj_path, "*.o"))

    print("\nLinking...")

    ### Remove type 11 relocations ###

    for fname in obj_files:
        obj = ELF(fname)

        for entry in obj.secHeadEnts:
            if entry.type != 4 or not entry.relocations:
                continue

            remove_indices = [i for i, rel in enumerate(entry.relocations) if (rel.info & 0xFF) == 0x0B]
            for i in reversed(remove_indices):
                del entry.relocations[i]

        with open(fname, "wb") as outf:
            outf.write(obj.saveRel())

    ##################################

    if platform_type != PlatformType.CafeLoader and addrconv is None:
        f_addrconv_resolve = None
        symbols = dict(proj.symbols)

    else:
        f_addrconv_resolve = platforms[platform_type].resolve
        symbols = dict((symbol, f_addrconv_resolve(address)) for symbol, address in proj.symbols.items())

    symbol_map_str = MAP_TEMPLATE % (
        '\n'.join(
            ("\t%s = 0x%08X;" % item) for item in symbols.items()
        )
    )

    symbol_map_path = os.path.join(target_temp_path, "%s.x" % proj_name)
    with open(symbol_map_path, 'w', encoding="utf8") as outf:
        outf.write(symbol_map_str)

    proj_ld_str = LD_TEMPLATE % (
        text_addr, 0x10000000 - text_addr,
        data_addr, 0xC0000000 - data_addr,
        text_align,
        rodata_align,
        data_align,
        bss_align
    )

    proj_ld_path = os.path.join(target_temp_path, "%s.ld" % proj_name)
    with open(proj_ld_path, 'w', encoding="utf8") as outf:
        outf.write(proj_ld_str)

    proj_obj_path = os.path.join(target_temp_path, "%s.o" % proj_name)

    cmd_lst = [
        "\"%s\"" % os.path.join(GHS_PATH, "elxr"),
        "-T \"%s\"" % symbol_map_path,
        "-T \"%s\"" % proj_ld_path,
        "-o \"%s\"" % proj_obj_path
    ]
    cmd_lst.extend(map(lambda s: "\"%s\"" % s, obj_files))

    cmd = ' '.join(cmd_lst)
    error_code = subprocess.call(cmd)
    if error_code:
        error("Link Failed!!\n"
              "Error code: %i" % error_code)
        return False

    print("\nLoading hax ELF...")
    proj_obj = ELF(proj_obj_path)

    text    = proj_obj.getSectionByName(".text")
    rodata  = proj_obj.getSectionByName(".rodata")
    data    = proj_obj.getSectionByName(".data")

    assert text is not None

    if platform_type == PlatformType.Emulator:
        bss = proj_obj.getSectionByName(".bss")

        rela_text = proj_obj.getSectionByName(".rela.text")
        rela_rodata = proj_obj.getSectionByName(".rela.rodata")
        rela_data = proj_obj.getSectionByName(".rela.data")

    elif platform_type == PlatformType.CafeLoader:
        code_path = os.path.join(target_out_path, "Code.bin")
        with open(code_path, "wb") as outf:
            outf.write(text.data)

    data_end = 0
    if rodata is not None:
        data_end = max(data_end, rodata.vAddr + rodata.size_)
    if data is not None:
        data_end = max(data_end, data.vAddr + data.size_)

    if platform_type == PlatformType.Emulator:
        if bss is not None:
            data_end = max(data_end, bss.vAddr + bss.size_)

    elif platform_type == PlatformType.CafeLoader:
        if data_end > 0:
            data_size = data_end - data_addr
            data_buf = bytearray(data_size)

            for data_entry in rodata, data:
                if data_entry is not None:
                    data_offset = data_entry.vAddr - data_addr
                    data_buf[data_offset:data_offset + data_entry.size_] = data_entry.data

            data_path = os.path.join(target_out_path, "Data.bin")
            with open(data_path, "wb") as outf:
                outf.write(data_buf)

    symtab  = proj_obj.getSectionByName(".symtab")
    strtab  = proj_obj.getSectionByName(".strtab")

    if symtab is not None and strtab is not None:
        # https://docs.oracle.com/cd/E23824_01/html/819-0690/chapter6-79797.html

        assert symtab.entSize == 0x10
        symtab_data = symtab.data
        symtab_data_len = len(symtab_data)
        assert symtab_data_len % 0x10 == 0

        endian = proj_obj.header.endian
        elf32_sym_struct = struct.Struct("%sIIIBBh" % endian)
        elf32_sym_struct_unpack_from = elf32_sym_struct.unpack_from

        section_headers = proj_obj.secHeadEnts
        section_headers_count = len(section_headers)
        strtab_data = strtab.data

        for pos in range(0, symtab_data_len, 0x10):
            st_name, st_value, st_size, st_info, st_other, st_shndx = elf32_sym_struct_unpack_from(symtab_data, pos)
            if st_name == 0 or \
               st_info >> 4 != 1 or \
               st_other != 0x00000000 or \
               st_shndx <= 0 or \
               st_shndx >= section_headers_count or \
               section_headers[st_shndx].name != ".text":
                continue

            name = elf_readString(strtab_data, st_name)
            if name not in symbols:
                symbols[name] = st_value

            else:
                assert symbols[name] == st_value

    if platform_type == PlatformType.Emulator:
        # sh_str_base = len(base_elf.shStrTable.data)

        text.nameIdx = 0  # sh_str_base; base_elf.shStrTable.data += b".textHaxx\0"; sh_str_base += 10
        base_elf.secHeadEnts.append(text)
        text.flags = base_elf.getSectionByName(".text").flags

        if rela_text:
            rela_text.nameIdx = 0  # sh_str_base; base_elf.shStrTable.data += b".rela.textHaxx\0"; sh_str_base += 15
            base_elf.secHeadEnts.append(rela_text)
            rela_text.flags = base_elf.getSectionByName(".rela.text").flags

        if rodata:
            rodata.nameIdx = 0  # sh_str_base; base_elf.shStrTable.data += b".rodataHaxx\0"; sh_str_base += 12
            base_elf.secHeadEnts.append(rodata)
            rodata.flags = base_elf.getSectionByName(".rodata").flags

        if rela_rodata:
            rela_rodata.nameIdx = 0  # sh_str_base; base_elf.shStrTable.data += b".rela.rodataHaxx\0"; sh_str_base += 17
            base_elf.secHeadEnts.append(rela_rodata)
            rela_rodata.flags = base_elf.getSectionByName(".rela.rodata").flags

        if data:
            data.nameIdx = 0  # sh_str_base; base_elf.shStrTable.data += b".dataHaxx\0"; sh_str_base += 10
            base_elf.secHeadEnts.append(data)
            data.flags = base_elf.getSectionByName(".data").flags

        if rela_data:
            rela_data.nameIdx = 0  # sh_str_base; base_elf.shStrTable.data += b".rela.dataHaxx\0"; sh_str_base += 15
            base_elf.secHeadEnts.append(rela_data)
            rela_data.flags = base_elf.getSectionByName(".rela.data").flags

        if bss:
            bss.nameIdx = 0  # sh_str_base; base_elf.shStrTable.data += b".bssHaxx\0"; sh_str_base += 9
            base_elf.secHeadEnts.append(bss)
            bss.flags = base_elf.getSectionByName(".bss").flags

        symtab_index = -1

        if symtab:
            symtab.nameIdx = 0  # sh_str_base; base_elf.shStrTable.data += b".symtabHaxx\0"; sh_str_base += 12
            symtab_index = len(base_elf.secHeadEnts)
            base_elf.secHeadEnts.append(symtab)
            symtab.flags = base_elf.getSectionByName(".symtab").flags

            syms_addr = f_align(syms_addr, symtab.addrAlign)
            symtab.vAddr = syms_addr
            syms_addr += len(symtab.data)

        if strtab:
            strtab.nameIdx = 0  # sh_str_base; base_elf.shStrTable.data += b".strtabHaxx\0"; sh_str_base += 12
            base_elf.secHeadEnts.append(strtab)
            strtab.flags = base_elf.getSectionByName(".strtab").flags

            syms_addr = f_align(syms_addr, strtab.addrAlign)
            strtab.vAddr = syms_addr
            syms_addr += len(strtab.data)

        base_elf.secHeadEnts.append(rpl_crcs)
        base_elf.secHeadEnts.append(rpl_fileinfo)

        text_end = text.vAddr + text.size_

        data_end = 0
        if rodata is not None:
            data_end = max(data_end, rodata.vAddr + rodata.size_)
        if data is not None:
            data_end = max(data_end, data.vAddr + data.size_)
        if bss is not None:
            data_end = max(data_end, bss.vAddr + bss.size_)

        dyna_end = syms_addr

        rpl_fileinfo_data[4:8]       = struct.pack(">I", text_end - 0x02000000)

        if data_end > 0:
            assert data_end > base_data_end
            rpl_fileinfo_data[12:16] = struct.pack(">I", data_end - 0x10000000)

        if dyna_end > base_dyna_end:
            rpl_fileinfo_data[20:24] = struct.pack(">I", dyna_end - 0xC0000000)
            rpl_fileinfo_data[76:80] = b'\0\0\0\0'

        if rela_text:
            if symtab_index != -1:
                rela_text.link = symtab_index

            rela_text.info = base_elf.secHeadEnts.index(text)

            for rela in rela_text.relocations:
                if rela.offset < text.vAddr:
                    rela.offset += text.vAddr

        if rodata and rela_rodata:
            if symtab_index != -1:
                rela_rodata.link = symtab_index

            rela_rodata.info = base_elf.secHeadEnts.index(rodata)

            for rela in rela_rodata.relocations:
                if rela.offset < rodata.vAddr:
                    rela.offset += rodata.vAddr

        if data and rela_data:
            if symtab_index != -1:
                rela_data.link = symtab_index

            rela_data.info = base_elf.secHeadEnts.index(data)

            for rela in rela_data.relocations:
                if rela.offset < data.vAddr:
                    rela.offset += data.vAddr

        if symtab and strtab:
            symtab.link = base_elf.secHeadEnts.index(strtab)

        base_text   = base_elf.getSectionByName(".text")
        base_rodata = base_elf.getSectionByName(".rodata")
        base_data   = base_elf.getSectionByName(".data")
        base_bss    = base_elf.getSectionByName(".bss")

        base_rela_text      = base_elf.getSectionByName(".rela.text")
        base_rela_rodata    = base_elf.getSectionByName(".rela.rodata")
        base_rela_data      = base_elf.getSectionByName(".rela.data")

        entry_ranges = tuple(
            (range(entry.vAddr, entry.vAddr + entry.size_), entry, entry_rela)
            for entry, entry_rela in zip(
                (base_text,         base_rodata,        base_data,      base_bss),
                (base_rela_text,    base_rela_rodata,   base_rela_data, None),
            )
            if entry is not None
        )

        print("Applying patches...")

        for module in modules.values():
            for hook in module.hooks:
                for address in hook.address:
                    if f_addrconv_resolve is not None:
                        try:
                            address = f_addrconv_resolve(address)
                        except Exception as e:
                            error(e)
                            return False

                    try:
                        data = hook.getData(address, symbols)
                    except Exception as e:
                        error(e)
                        return False

                    data_len = len(data)

                    end_address = address + data_len

                    for entry_range, entry, entry_rela in entry_ranges:
                        if address in entry_range:
                            break

                    else:
                        print("Patch at unknown region.")
                        print("Skipping patch at address: 0x%08X" % address)
                        continue

                    if entry is base_bss:
                        print("Patching .bss is not possible.")
                        print("Skipping patch at address: 0x%08X" % address)
                        continue

                    if end_address > entry.vAddr + entry.size_:
                        print("Patch exceeds section range.")
                        print("Skipping patch at address: 0x%08X" % address)
                        continue

                    if entry_rela is not None:
                        patch_range = range(address, end_address)

                        remove_indices = []

                        for i, rel in enumerate(entry_rela.relocations):
                            if rel.offset in patch_range:
                                # print("Found relocation at address: 0x%08X, removing..." % rel.offset)
                                remove_indices.append(i)

                        for i in reversed(remove_indices):
                            del entry_rela.relocations[i]

                    offset = address - entry.vAddr
                    entry.data[offset:offset + data_len] = data
                    # print("Patched %d byte(s) at address: 0x%08X" % (data_len, address))

        z_crc32 = zlib.crc32
        rpl_crcs.data = b''.join((struct.pack(">I", (z_crc32(section.data) & 0xFFFFFFFF)) if section.type not in (8, 0x80000003) and section.data else b'\0\0\0\0') for section in base_elf.secHeadEnts)

        # TODO(aboood40091): Strip filename symbols
        # TODO(aboood40091): Strip "/DISCARD/" and ".comment" sections

        elf_path = os.path.join(proj_out_path, "%s.elf" % target_name)
        rpx_path = os.path.join(proj_out_path, "%s.rpx" % target_name)

        print("Saving ELF...")
        buf = base_elf.save()
        with open(elf_path, "wb") as outf:
            outf.write(buf)

        print("Compressing RPX...")
        DETACHED_PROCESS = 0x00000008
        subprocess.call("\"%s\" -c \"%s\" \"%s\"" % (wiiurpxtool, elf_path, rpx_path), creationflags=DETACHED_PROCESS)

    elif platform_type == PlatformType.CafeLoader:
        print("Building patches...")

        pack_u16 = PACK_U16

        patch_count = sum(len(hook.address) for module in modules.values() for hook in module.hooks)
        patch_buf = bytearray(pack_u16(patch_count))

        for module in modules.values():
            for hook in module.hooks:
                for address in hook.address:
                    try:
                        address = f_addrconv_resolve(address)
                    except Exception as e:
                        error(e)
                        return False

                    try:
                        data = hook.getData(address, symbols)
                    except Exception as e:
                        error(e)
                        return False

                    data_len = len(data)

                    patch_buf += pack_u16(data_len)
                    patch_buf += pack_u32(address)
                    patch_buf += data

                    # print("Patched %d byte(s) at address: 0x%08X" % (data_len, address))

        patches_path = os.path.join(target_out_path, "Patches.hax")
        with open(patches_path, "wb") as outf:
            outf.write(patch_buf)

    return True


def main():
    if not os.path.isfile(os.path.join(GHS_PATH, "gbuild.exe")):
        print("Could not locate MULTI Green Hills Software! Did you set its path?")
        return

    def error(*args, **kargs):
        print("While trying to parse project, encountered the following error:\n")
        print(*args, **kargs)

    file_path = input("Enter project.yaml path: ")
    if not file_path:
        return

    proj = Project.fromYaml(file_path, error)
    if proj is None:
        return

    platform_types = (PlatformType.Emulator, PlatformType.CafeLoader)

    for target_name, target in proj.targets.items():
        if target.isAbstract:
            continue

        for platform_type in platform_types:
            if not buildProject(proj, target_name, platform_type, error):
                return

            print()
            print('=' * 50)


if __name__ == "__main__":
    main()
