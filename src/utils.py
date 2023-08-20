#! /usr/bin/env python3

from enum import Enum, auto
from pathlib import Path

ROM_FILE = Path(__file__).resolve().parents[1] / 'blue.gb'

class SECTIONS(Enum):
    ENTRY = auto()
    LOGO = auto()
    TITLE = auto()
    CART = auto()
    ROM_SIZE = auto()
    RAM_SIZE = auto()


OFFSETS = {
    SECTIONS.LOGO.name: (0x104, 0x133),
    SECTIONS.TITLE.name: (0x134, 0x143),
    SECTIONS.CART.name: (0x147, 0x147),
    SECTIONS.ROM_SIZE.name: (0x148, 0x148),
    SECTIONS.RAM_SIZE.name: (0x149, 0x149),
}

ROM_SIZE_MAP = {
    0: 32 * 1024,
    1: 64 * 1024,
    5: 1024 * 1024
}

RAM_SIZE_MAP = {
    0: 0,
    1: 2 * 1024,
    3: 32 * 1024
}

def hexdump(dat):
    o = []
    for b in range(len(dat)):
        if b % 16 == 0:
            o.append(f'\n {b:0>4x} ')
        o.append(hex(dat[b])[-2:].upper() + ' ')
    return ''.join(o)

class GBFile:
    def __init__(self, rom_file: Path):
        with open(rom_file, 'rb') as f:
            self.ROM = f.read()
        
        sections = dict()
        for name, range in OFFSETS.items():
            start, end = range
            sections[name] = self.ROM[start:end+1]

        self.sections = sections
        self.entry_point = 0x100

if __name__ == '__main__':
    gbfile = GBFile(ROM_FILE)
    print('LOGO bitmap', hexdump(gbfile.sections['LOGO']))
    print('Title', gbfile.sections['TITLE'].decode())
    print('Cart', hex(gbfile.sections['CART'][0]))
    print('ROM Size', ROM_SIZE_MAP[gbfile.sections['ROM_SIZE'][0]])
    print('RAM Size', RAM_SIZE_MAP[gbfile.sections['RAM_SIZE'][0]])
