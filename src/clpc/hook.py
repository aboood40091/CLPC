#!/usr/bin/env python3
# -*- coding: utf-8 -*-


from enum import auto as enum_auto
from enum import IntEnum
from enum import IntFlag
import struct


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


class BasicHook:
    available_options = (
        "type",
        "addr"
    )

    def __init__(self):
        self.address = [0x00000000]
        self.dataCache = None

    def getData(self, *_):
        raise NotImplementedError

    @staticmethod
    def checkObj(obj, hook_field_name, available_options, error=print):
        if "addr" not in obj:
            error("%s Address not specified" % hook_field_name)
            return False

        available_options += BasicHook.available_options
        available_options_error_msg = "Unrecognized option in %s: %s" % (hook_field_name, "%r")

        for k in obj:
            if k not in available_options:
                error(available_options_error_msg % k)
                return False

        return True

    def baseFromObj(self, obj, hook_field_name, error=print):
        is_valid_addr = lambda v: isinstance(v, int) and 0 <= v <= 0xFFFFFFFF
        is_valid_addr_lst = lambda lst: isinstance(lst, list) and lst and all(is_valid_addr(v) for v in lst)

        address = obj["addr"]
        if is_valid_addr(address):
            address = [address]
        elif not is_valid_addr_lst(address):
            error("In %s, expected address to be a(n / list of) unsigned 32-bit integer(s), received: %r" % (hook_field_name, address))
            return False

        self.address = address
        return True


class PatchHook(BasicHook):
    class Encoding(IntEnum):
        Shift_JIS   = enum_auto()
        UTF_8       = enum_auto()
        UCS_2       = enum_auto()

        @staticmethod
        def fromString(string):
            self_type = PatchHook.Encoding

            conv = {
                "Shift-JIS":    self_type.Shift_JIS,
                "ShiftJIS":     self_type.Shift_JIS,
                "shift-jis":    self_type.Shift_JIS,
                "shiftjis":     self_type.Shift_JIS,

                "UTF-8":        self_type.UTF_8,
                "UTF8":         self_type.UTF_8,
                "utf-8":        self_type.UTF_8,
                "utf8":         self_type.UTF_8,

                "UCS-2":        self_type.UCS_2,
                "UCS2":         self_type.UCS_2,
                "ucs-2":        self_type.UCS_2,
                "ucs2":         self_type.UCS_2
            }

            if string in conv:
                return conv[string]

            raise ValueError("Invalid encoding string %r" % string)

        def asEncodingStr(self):
            self_type = PatchHook.Encoding

            if self == self_type.UTF_8:
                return "utf-8"

            if self == self_type.UCS_2:
                return "utf-16be"

            return "shiftjis"

    class Type(IntFlag):
        Raw     = 0x0000

        U8      = 0x0001
        U16     = 0x0002
        U32     = 0x0004
        U64     = 0x0008

        S8      = 0x0010
        S16     = 0x0020
        S32     = 0x0040
        S64     = 0x0080

        F32     = 0x0100
        F64     = 0x0200

        Char    = 0x0400
        String  = 0x0800

        WChar   = 0x1000
        WString = 0x2000

        Array   = 0x4000

        def allowedEncodings(self):
            self_type = PatchHook.Type
            encd_type = PatchHook.Encoding

            conv = {
                self_type.String:   (encd_type.Shift_JIS, encd_type.UTF_8),

                self_type.WChar:    (encd_type.Shift_JIS, encd_type.UCS_2),
                self_type.WString:  (encd_type.Shift_JIS, encd_type.UCS_2)
            }

            type_no_array = self & ~self_type.Array
            if type_no_array in conv:
                return conv[type_no_array]

            return tuple()

        def defaultEncoding(self):
            self_type = PatchHook.Type
            encd_type = PatchHook.Encoding

            conv = {
                self_type.String:   encd_type.Shift_JIS,

                self_type.WChar:    encd_type.Shift_JIS,
                self_type.WString:  encd_type.Shift_JIS
            }

            type_no_array = self & ~self_type.Array
            if type_no_array in conv:
                return conv[type_no_array]

            return None

        @staticmethod
        def fromString(string):
            self_type = PatchHook.Type

            conv = {
                "raw":          self_type.Raw,

                "u8":           self_type.U8,
                "uchar":        self_type.U8,
                "u16":          self_type.U16,
                "ushort":       self_type.U16,
                "u32":          self_type.U32,
                "uint":         self_type.U32,
                "u64":          self_type.U64,
                "ulonglong":    self_type.U64,

                "s8":           self_type.S8,
                "schar":        self_type.S8,
                "s16":          self_type.S16,
                "short":        self_type.S16,
                "s32":          self_type.S32,
                "int":          self_type.S32,
                "s64":          self_type.S64,
                "longlong":     self_type.S64,

                "f32":          self_type.F32,
                "float":        self_type.F32,
                "f64":          self_type.F64,
                "double":       self_type.F64,

                "char":         self_type.Char,
                "string":       self_type.String,

                "wchar":        self_type.WChar,
                "wstring":      self_type.WString,

                "u8[]":         self_type.U8        | self_type.Array,
                "uchar[]":      self_type.U8        | self_type.Array,
                "u16[]":        self_type.U16       | self_type.Array,
                "ushort[]":     self_type.U16       | self_type.Array,
                "u32[]":        self_type.U32       | self_type.Array,
                "uint[]":       self_type.U32       | self_type.Array,
                "u64[]":        self_type.U64       | self_type.Array,
                "ulonglong[]":  self_type.U64       | self_type.Array,

                "s8[]":         self_type.S8        | self_type.Array,
                "schar[]":      self_type.S8        | self_type.Array,
                "s16[]":        self_type.S16       | self_type.Array,
                "short[]":      self_type.S16       | self_type.Array,
                "s32[]":        self_type.S32       | self_type.Array,
                "int[]":        self_type.S32       | self_type.Array,
                "s64[]":        self_type.S64       | self_type.Array,
                "longlong[]":   self_type.S64       | self_type.Array,

                "f32[]":        self_type.F32       | self_type.Array,
                "float[]":      self_type.F32       | self_type.Array,
                "f64[]":        self_type.F64       | self_type.Array,
                "double[]":     self_type.F64       | self_type.Array,

                "char[]":       self_type.Char      | self_type.Array,
                "string[]":     self_type.String    | self_type.Array,

                "wchar[]":      self_type.WChar     | self_type.Array,
                "wstring[]":    self_type.WString   | self_type.Array
            }

            if string in conv:
                return conv[string]

            raise ValueError("Invalid type string %r" % string)

    def __init__(self):
        super().__init__()

        self.data = None
        self.type = PatchHook.Type.Raw
        self.encoding = None

    def getData(self, *_):
        if self.dataCache is not None:
            return self.dataCache

        patch_type_type = PatchHook.Type

        type_ = self.type
        data = self.data

        if type_ == patch_type_type.Raw:
            data_buf = bytearray.fromhex(data)

        else:
            encode = {
                patch_type_type.U8:         PACK_U8,
                patch_type_type.U16:        PACK_U16,
                patch_type_type.U32:        PACK_U32,
                patch_type_type.U64:        PACK_U64,
                patch_type_type.S8:         PACK_S8,
                patch_type_type.S16:        PACK_S16,
                patch_type_type.S32:        PACK_S32,
                patch_type_type.S64:        PACK_S64,
                patch_type_type.F32:        PACK_F32,
                patch_type_type.F64:        PACK_F64,
                patch_type_type.Char:       lambda v: bytes((ord(v),)),
                patch_type_type.String:     lambda v: v,
                patch_type_type.WChar:      lambda v: v,
                patch_type_type.WString:    lambda v: v
            }[type_]

            alignment = {
                patch_type_type.U8:         1,
                patch_type_type.U16:        2,
                patch_type_type.U32:        4,
                patch_type_type.U64:        8,
                patch_type_type.S8:         1,
                patch_type_type.S16:        2,
                patch_type_type.S32:        4,
                patch_type_type.S64:        8,
                patch_type_type.F32:        4,
                patch_type_type.F64:        8,
                patch_type_type.Char:       1,
                patch_type_type.String:     4,
                patch_type_type.WChar:      2,
                patch_type_type.WString:    4
            }[type_]

            align = lambda x, y: ((x - 1) | (y - 1)) + 1

            data_buf = bytearray()
            for v in data:
                current_pos = len(data_buf)
                pad_size = align(current_pos, alignment) - current_pos
                data_buf += b'\0' * pad_size
                data_buf += encode(v)

            # print(type_, data, data_buf)

        self.dataCache = data_buf
        return data_buf

    @staticmethod
    def fromObj(obj, module_field_name, proj, error=print):
        hook_field_name = "%s Patch Hook" % module_field_name

        ### Selected Options Sanity Check ###
        # print("%s Selected Options Sanity Check" % hook_field_name)

        if not BasicHook.checkObj(
            obj,
            hook_field_name,
            ("data", "datatype", "encoding"),
            error=error
        ):
            return None

        ### Hook Initialization ###

        hook = PatchHook()

        ### Read Base Options ###

        if not hook.baseFromObj(obj, hook_field_name, error):
            return None

        ### Check Mandatory Variable-Type Attributes ###

        if "data" not in obj:
            error("%s Data not specified" % hook_field_name)
            return None

        ### Data Type Reading ###

        datatype = proj.readString(obj, "datatype", "%s Data Type" % hook_field_name, 0x01020304, error=error)
        if datatype is None:
            return None

        patch_type_type = PatchHook.Type

        if datatype == 0x01020304:
            type_ = patch_type_type.Raw

        else:
            try:
                type_ = patch_type_type.fromString(datatype)
            except ValueError as e:
                error("%s: %s" % (hook_field_name, e))
                return None

        type_no_array = patch_type_type(type_ & ~patch_type_type.Array)
        hook.type = type_no_array

        ### Data Reading ###

        if type_ == patch_type_type.Raw:
            data = proj.processString("%s Data" % hook_field_name, obj["data"], error=error)
            if data is None:
                return None

            data_str = ''.join(data.split())

            hex_digits = "0123456789ABCDEFabcdef"
            is_hex_digit = lambda c: c in hex_digits
            is_hex_str = lambda s: s and len(s) % 2 == 0 and all(is_hex_digit(c) for c in s)

            if not is_hex_str(data_str):
                error("In %s, expected \"data\" to be a valid hex string of even length, received: %r" % (hook_field_name, data))
                return None

            hook.data = data_str

        else:
            alignment = {
                patch_type_type.U8:         1,
                patch_type_type.U16:        2,
                patch_type_type.U32:        4,
                patch_type_type.U64:        8,
                patch_type_type.S8:         1,
                patch_type_type.S16:        2,
                patch_type_type.S32:        4,
                patch_type_type.S64:        8,
                patch_type_type.F32:        4,
                patch_type_type.F64:        8,
                patch_type_type.Char:       1,
                patch_type_type.String:     4,
                patch_type_type.WChar:      2,
                patch_type_type.WString:    4
            }[type_no_array]

            for address in hook.address:
                if address & (alignment - 1) != 0:
                    error("In %s, expected value in \"addr\" [0x%08X] to be aligned by %d" % (hook_field_name, address, alignment))
                    return None

            if type_ & patch_type_type.Array:
                data = obj["data"]
                if not isinstance(data, list) or not data:
                    error("In %s, expected \"data\" to be a list of values" % hook_field_name)
                    return None

            else:
                data = [obj["data"]]

            check = {
                patch_type_type.U8:         lambda v: isinstance(v, int) and 0 <= v <= 0xFF,
                patch_type_type.U16:        lambda v: isinstance(v, int) and 0 <= v <= 0xFFFF,
                patch_type_type.U32:        lambda v: isinstance(v, int) and 0 <= v <= 0xFFFFFFFF,
                patch_type_type.U64:        lambda v: isinstance(v, int) and 0 <= v <= 0xFFFFFFFFFFFFFFFF,
                patch_type_type.S8:         lambda v: isinstance(v, int) and -0x80 <= v <= 0x7F,
                patch_type_type.S16:        lambda v: isinstance(v, int) and -0x8000 <= v <= 0x7FFF,
                patch_type_type.S32:        lambda v: isinstance(v, int) and -0x80000000 <= v <= 0x7FFFFFFF,
                patch_type_type.S64:        lambda v: isinstance(v, int) and -0x8000000000000000 <= v <= 0x7FFFFFFFFFFFFFFF,
                patch_type_type.F32:        lambda v: isinstance(v, float),
                patch_type_type.F64:        lambda v: isinstance(v, float),
                patch_type_type.Char:       lambda v: (isinstance(v, str) and len(v) == 1 and v.isascii()) or v is None,
                patch_type_type.String:     lambda v: v and isinstance(v, str),  # Encoding checks happen later
                patch_type_type.WChar:      lambda v: v and isinstance(v, str),  # ^^^
                patch_type_type.WString:    lambda v: v and isinstance(v, str)   # ^^^
            }

            error_msgs = {
                patch_type_type.U8:         "In %s, expected data to be an integer in the range [%d, %d], received: %s" % (hook_field_name, 0, 0xFF, "%r"),
                patch_type_type.U16:        "In %s, expected data to be an integer in the range [%d, %d], received: %s" % (hook_field_name, 0, 0xFFFF, "%r"),
                patch_type_type.U32:        "In %s, expected data to be an integer in the range [%d, %d], received: %s" % (hook_field_name, 0, 0xFFFFFFFF, "%r"),
                patch_type_type.U64:        "In %s, expected data to be an integer in the range [%d, %d], received: %s" % (hook_field_name, 0, 0xFFFFFFFFFFFFFFFF, "%r"),
                patch_type_type.S8:         "In %s, expected data to be an integer in the range [%d, %d], received: %s" % (hook_field_name, -0x80, 0x7F, "%r"),
                patch_type_type.S16:        "In %s, expected data to be an integer in the range [%d, %d], received: %s" % (hook_field_name, -0x8000, 0x7FFF, "%r"),
                patch_type_type.S32:        "In %s, expected data to be an integer in the range [%d, %d], received: %s" % (hook_field_name, -0x80000000, 0x7FFFFFFF, "%r"),
                patch_type_type.S64:        "In %s, expected data to be an integer in the range [%d, %d], received: %s" % (hook_field_name, -0x8000000000000000, 0x7FFFFFFFFFFFFFFF, "%r"),
                patch_type_type.F32:        "In %s, expected data to be a floating-point number, received: %s" % (hook_field_name, "%r"),
                patch_type_type.F64:        "In %s, expected data to be a floating-point number, received: %s" % (hook_field_name, "%r"),
                patch_type_type.Char:       "In %s, expected data to be an ASCII character, received: %s" % (hook_field_name, "%r"),
                patch_type_type.String:     "In %s, expected data to be a non-empty string, received: %s" % (hook_field_name, "%r"),
                patch_type_type.WChar:      "In %s, expected data to be a non-empty string, received: %s" % (hook_field_name, "%r"),
                patch_type_type.WString:    "In %s, expected data to be a non-empty string, received: %s" % (hook_field_name, "%r")
            }

            f_check = check[type_no_array]
            data_error_msg = error_msgs[type_no_array]

            for v in data:
                if not f_check(v):
                    error(data_error_msg % v)
                    return None

            hook.data = data

        ### Encoding Reading ###

        encoding_s = proj.readString(obj, "encoding", "%s Encoding" % hook_field_name, 0x01020304, error=error)
        if encoding_s is None:
            return None

        if encoding_s == 0x01020304:
            encoding = type_.defaultEncoding()

        else:
            try:
                encoding = PatchHook.Encoding.fromString(encoding_s)
            except ValueError as e:
                error("%s: %s" % (hook_field_name, e))
                return None

            if encoding not in type_.allowedEncodings():
                error("%s Unexpected Encoding: %r" % (hook_field_name, encoding_s))
                return None

        hook.encoding = encoding

        ### Encode Strings ###

        if encoding is not None:
            encoding_str = encoding.asEncodingStr()

            try:
                if type_no_array == patch_type_type.String:
                    hook.data = [(s + '\0').encode(encoding_str) for s in hook.data]

                else:
                    def encode_wide_char(c, encoding_str):
                        c_encoded = c.encode(encoding_str)
                        if len(c_encoded) > 2:
                            raise UnicodeEncodeError

                        return c_encoded.rjust(2, b'\0')

                    if type_no_array == patch_type_type.WChar:
                        hook.data = [encode_wide_char(c, encoding_str) for c in hook.data]

                    elif type_no_array == patch_type_type.WString:
                        hook.data = [b''.join(encode_wide_char(c, encoding_str) for c in (s + '\0')) for s in hook.data]

                    else:
                        raise UnicodeEncodeError

            except UnicodeEncodeError:
                error("In %s, failed to encode strings" % hook_field_name)
                return None

        ### Success ###

        return hook


class NOPHook(BasicHook):
    def __init__(self):
        super().__init__()

        self.count = 1

    def getData(self, *_):
        if self.dataCache is None:
            self.dataCache = b"\x60\x00\x00\x00" * self.count

        return self.dataCache

    @staticmethod
    def fromObj(obj, module_field_name, proj, error=print):
        hook_field_name = "%s NOP Hook" % module_field_name

        ### Selected Options Sanity Check ###
        # print("%s Selected Options Sanity Check" % hook_field_name)

        if not BasicHook.checkObj(
            obj,
            hook_field_name,
            ("count",),
            error=error
        ):
            return None

        ### Hook Initialization ###

        hook = NOPHook()

        ### Read Base Options ###

        if not hook.baseFromObj(obj, hook_field_name, error):
            return None

        ### Count Reading ###

        if "count" in obj:
            count = obj["count"]
            if not (isinstance(count, int) and count > 0):
                error("In %s, expected count to be positive non-zero integer, received: %r" % (hook_field_name, count))
                return None

            hook.count = count

        ### Success ###

        return hook


class ReturnHook(BasicHook):
    def getData(self, *_):
        return b"\x4E\x80\x00\x20"

    @staticmethod
    def fromObj(obj, module_field_name, proj, error=print):
        hook_field_name = "%s Return Hook" % module_field_name

        ### Selected Options Sanity Check ###
        # print("%s Selected Options Sanity Check" % hook_field_name)

        if not BasicHook.checkObj(
            obj,
            hook_field_name,
            tuple(),
            error=error
        ):
            return None

        ### Hook Initialization ###

        hook = ReturnHook()

        ### Read Base Options ###

        if not hook.baseFromObj(obj, hook_field_name, error):
            return None

        ### Success ###

        return hook


class BranchHook(BasicHook):
    class Type(IntEnum):
        Branch      = enum_auto()
        Branch_Link = enum_auto()

        @staticmethod
        def fromString(string):
            self_type = BranchHook.Type

            conv = {
                "b":    self_type.Branch,
                "bl":   self_type.Branch_Link,
            }

            if string in conv:
                return conv[string]

            raise ValueError("Invalid instruction type string %r" % string)

    def __init__(self):
        super().__init__()

        self.type = BranchHook.Type.Branch
        self.func = None

    def getData(self, address, symbols):
        func = self.func
        if func not in symbols:
            func = func.strip()
            if func not in symbols:
                raise KeyError("In Branch Hook, function symbol not found: %r" % self.func)

        func_address = symbols[func]

        key = (address << 32) | func_address
        if self.dataCache is None:
            self.dataCache = {}
        elif key in self.dataCache:
            return self.dataCache[key]

        offset = (func_address - address) & 0x03FFFFFC

        instruction = 0x48000000 | offset
        if self.type == BranchHook.Type.Branch_Link:
            instruction |= 1

        data_buf = PACK_U32(instruction)
        self.dataCache[key] = data_buf
        return data_buf

    @staticmethod
    def fromObj(obj, module_field_name, proj, error=print):
        hook_field_name = "%s Branch Hook" % module_field_name

        ### Selected Options Sanity Check ###
        # print("%s Selected Options Sanity Check" % hook_field_name)

        if not BasicHook.checkObj(
            obj,
            hook_field_name,
            ("instr", "func"),
            error=error
        ):
            return None

        ### Hook Initialization ###

        hook = BranchHook()

        ### Read Base Options ###

        if not hook.baseFromObj(obj, hook_field_name, error):
            return None

        ### Branch Type Reading ###

        instr = proj.readString(obj, "instr", "%s Instruction Type" % hook_field_name, error=error)
        if instr is None:
            return None

        try:
            type_ = BranchHook.Type.fromString(instr)
        except ValueError as e:
            error("%s: %s" % (hook_field_name, e))
            return None

        hook.type = type_

        ### Function Symbol Reading ###

        func = proj.readString(obj, "func", "%s Function Symbol" % hook_field_name, error=error)
        if func is None:
            return None

        hook.func = func

        ### Success ###

        return hook


class FuncPtrHook(BasicHook):
    def __init__(self):
        super().__init__()

        self.func = None

    def getData(self, _, symbols):
        func = self.func
        if func not in symbols:
            func = func.strip()
            if func not in symbols:
                raise KeyError("In Branch Hook, function symbol not found: %r" % self.func)

        func_address = symbols[func]

        key = func_address
        if self.dataCache is None:
            self.dataCache = {}
        elif key in self.dataCache:
            return self.dataCache[key]

        data_buf = PACK_U32(func_address)
        self.dataCache[key] = data_buf
        return data_buf

    @staticmethod
    def fromObj(obj, module_field_name, proj, error=print):
        hook_field_name = "%s Function Pointer Hook" % module_field_name

        ### Selected Options Sanity Check ###
        # print("%s Selected Options Sanity Check" % hook_field_name)

        if not BasicHook.checkObj(
            obj,
            hook_field_name,
            ("func",),
            error=error
        ):
            return None

        ### Hook Initialization ###

        hook = FuncPtrHook()

        ### Read Base Options ###

        if not hook.baseFromObj(obj, hook_field_name, error):
            return None

        ### Function Symbol Reading ###

        func = proj.readString(obj, "func", "%s Function Symbol" % hook_field_name, error=error)
        if func is None:
            return None

        hook.func = func

        ### Success ###

        return hook
