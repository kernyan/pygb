#! /usr/bin/env python3

import os
from pathlib import Path
from typing import Dict
from dataclasses import dataclass

from utils import GBFile
from decode import Decoder, OTYPE, Registers

DEBUG = os.getenv("DEBUG", False)

ROM_FILE = Path(__file__).resolve().parents[1] / 'blue.gb'

class CPU:
    def __init__(self, rom: Dict[str, bytes], entry: bytes):
        self.rom = rom
        self.PC = entry
        self.opcode = None
        self.decoder = Decoder(self.rom)
        self.regs = {r.name: 0 for r in Registers}
    
    def fetch_and_decode(self):
        self.opcode = self.decoder(self.PC)

    def execute(self):
        self.PC += self.opcode.length # will be overwritten by branch/jump
        match self.opcode.mne:
            case OTYPE.NOP:
                return
            case OTYPE.JP:
                self.PC = self.opcode.nn
                return
            case OTYPE.LD:
                if isinstance(self.o2, Registers):
                    self.regs[self.o1.name] = self.regs[self.o2.name]
                else:
                    self.regs[self.o1.name] = self.o2
                return
            #case OTYPE.CP:
            #    #if self.A > 
            #    return
            case _:
                raise RuntimeError(f"Unhandled opcode {self.opcode.mne}")

    def step(self):
        self.fetch_and_decode()
        self.execute()

if __name__ == '__main__':
    gbfile = GBFile(ROM_FILE)
    cpu = CPU(gbfile.ROM, gbfile.entry_point)
    while True:
        cpu.step()