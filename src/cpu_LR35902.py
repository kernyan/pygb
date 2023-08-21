#! /usr/bin/env python3

import os
from pathlib import Path
from typing import Dict
from dataclasses import dataclass

from utils import GBFile
from decode import Decoder, OTYPE, Registers, Flags

DEBUG = os.getenv("DEBUG", False)

ROM_FILE = Path(__file__).resolve().parents[1] / 'blue.gb'

def hf_carry(a:int, b:int) -> bool:
    a = a & 0x0f
    b = b & 0x0f
    return (a - b) < 0

class CPU:
    def __init__(self, rom: Dict[str, bytes], entry: bytes):
        self.rom = rom
        self.PC = entry
        self.opcode = None
        self.decoder = Decoder(self.rom)
        self.regs = {r.name: 0 for r in Registers}
        self.flags = {f.name: False for f in Flags}
    
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
                self.regs[self.o1] = self.val(self.opcode.o2)
                return
            case OTYPE.CP:
                comp = self.A - self.val(self.opcode.o1)
                if comp == 0:
                    self.flags[Flags.Z] = True
                self.flags[Flags.H] = hf_carry(self.A, self.val(self.opcode.o1))
                self.flags[Flags.N] = True
                self.flags[Flags.CY] = self.A < self.val(self.opcode.o1)
                return
            case OTYPE.JR:
                if isinstance(self.opcode.o1, Flags):
                    self.PC += (self.opcode.o2 - self.opcode.length) if self.flags[self.opcode.o1] else 0
                else:
                    self.PC += self.val(self.opcode.o1)
                return
            case _:
                raise RuntimeError(f"Unhandled opcode {self.opcode.mne}")

    @property
    def A(self):
        return self.regs[Registers.A.name]
    @property
    def B(self):
        return self.regs[Registers.B.name]
    @property
    def C(self):
        return self.regs[Registers.C.name]
    @property
    def D(self):
        return self.regs[Registers.D.name]
    @property
    def E(self):
        return self.regs[Registers.E.name]
    @property
    def F(self):
        return self.regs[Registers.F.name]

    def val(self, reg_or_imm):
        if isinstance(reg_or_imm, Registers):
            return self.regs[reg_or_imm.name]
        return reg_or_imm

    def step(self):
        self.fetch_and_decode()
        self.execute()

if __name__ == '__main__':
    gbfile = GBFile(ROM_FILE)
    cpu = CPU(gbfile.ROM, gbfile.entry_point)
    while True:
        cpu.step()