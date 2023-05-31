#!/usr/bin/env python3
# -*- coding: utf-8 -*-


from enum import IntEnum


class PlatformType(IntEnum):
    Base        = 0
    Emulator    = 1
    CafeLoader  = 2


class AddressConvert:
    def __init__(self):
        self.type = PlatformType.Base
        self.ranges = {}

    def addressOutOfRange(self, address):
        # raise IndexError("Address[0x%08X] out of range" % address)
        pass

    def resolve(self, address):
        for range_, offset in self.ranges.items():
            if address in range_:
                address += offset
                break

        else:
            self.addressOutOfRange(address)

        return address


class PlatformAddressConvert(AddressConvert):
    def __init__(self, platform_name, base):
        super().__init__()
        self.platformName = platform_name
        self.base = base

    def addressOutOfRange(self, address):
        raise IndexError("Address[0x%08X] out of range for %r platform" % (address, self.platformName))

    def resolve(self, address):
        return AddressConvert.resolve(self, self.base.resolve(address))


class AddressConvertEmulator(PlatformAddressConvert):
    def __init__(self, base):
        super().__init__("Emulator", base)
        self.type = PlatformType.Emulator


class AddressConvertCafeLoader(PlatformAddressConvert):
    def __init__(self, base):
        super().__init__("CafeLoader", base)
        self.type = PlatformType.CafeLoader
