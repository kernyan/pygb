#! /usr/bin/env python3

import os
from pathlib import Path
from typing import Dict, List

from utils import GBFile
from decode import Decoder, OTYPE, Registers, Flags
from array import array

DEBUG = os.getenv("DEBUG", False)

ROM_FILE = Path(__file__).resolve().parents[1] / 'blue.gb'

BRANCH_OP = {
    OTYPE.JR, OTYPE.JP
}

def hf_carry(a:int, b:int) -> bool:
    a = a & 0x0f
    b = b & 0x0f
    return (a - b) < 0

def is_reg(operand) -> bool:
    return isinstance(operand, Registers)

def rname(operand):
    if isinstance(operand, Registers):
        operand = operand.name
    else:
        operand = f"({hex(operand)})"
    return operand

class Memory:
    def __init__(self):
        self.mmap = array('B', [0]*(64*1024))
        #     0 -  100     interrupt
        #   100 -  150     ROM
        #   150 - 8000     User rogram area
        #  8000 - 9800     (VRAM) Bank 0, 1
        #  9800 - 9C00     (VRAM) BG Display Data 1
        #  9C00 - A000     (VRAM) BG Display Data 2
        #  A000 - C000     External expansion working RAM
        #  C000 - E000     Unit working RAM
        #  FE00 - FEA0     OAM
        #  FF00 - FF80     Port/Control/Sound
        #  FF80 - FFFE     Stack

class CPU:
    def __init__(self, rom: Dict[str, bytes], entry: bytes):
        self.rom = rom
        self.PC = entry
        self.opcode = None
        self.decoder = Decoder(self.rom)
        self.regs = {r.name: 0 for r in Registers}
        self.flags = {f.name: False for f in Flags}
        self.mem = Memory()
    
    def fetch_and_decode(self):
        self.opcode = self.decoder(self.PC)

    def update_flags(self, flags_to_update: List[str]):
        for f, v in zip(Flags, flags_to_update):
            if v == '1':
                self.flags[f] = True
            elif v == '0':
                self.flags[f] = False

    def execute(self):
        print(f'0x{self.PC:X} {self.opcode.mne.name} {self.opcode.length} {self.opcode.flags}', end='')
        self.PC += 0 if self.opcode.mne in BRANCH_OP else self.opcode.length
        self.update_flags(self.opcode.flags)
        match self.opcode.mne:
            case OTYPE.NOP:
                print('')
                return
            case OTYPE.JP:
                print(f' 0x{self.opcode.o1:X}')
                self.PC = self.opcode.o1
                return
            case OTYPE.LD:
                o2 = self.val(self.opcode.o2)
                print(f' {rname(self.opcode.o1)} 0x{o2:X}')
                self.assign(self.opcode.o1, o2)
                return
            case OTYPE.CP:
                o1 = self.val(self.opcode.o1)
                print(f' 0x{o1:X}')
                comp = self.A - o1
                if comp == 0:
                    self.flags[Flags.Z] = True
                self.flags[Flags.H] = hf_carry(self.A, o1)
                self.flags[Flags.C] = self.A < o1
                return
            case OTYPE.JR:
                if isinstance(self.opcode.o1, Flags):
                    print(f' Z 0x{self.opcode.o2:X}')
                    self.PC += self.opcode.o2 if self.flags[self.opcode.o1] else self.opcode.length
                else:
                    print(f' 0x{self.opcode.o1:X}')
                    self.PC += self.val(self.opcode.o1)
                return
            case OTYPE.XOR:
                print(f' {self.opcode.o1.name if is_reg(self.opcode.o1) else self.opcode.o1}')
                self.regs[Registers.A] ^= self.regs[self.opcode.o1]
                self.flags[Flags.Z] = self.regs[self.opcode.o1] == 0
                return
            case _:
                raise RuntimeError(f"Unhandled opcode {self.opcode.mne}")

    def assign(self, operand, value, len=1):
        assert len==1, 'multi byte assign not yet implemented'
        if isinstance(operand, Registers):
            self.regs[operand] = value
        else:
            self.mem.mmap[operand] = value

    @property
    def A(self):
        return self.regs[Registers.A]
    @property
    def B(self):
        return self.regs[Registers.B]
    @property
    def C(self):
        return self.regs[Registers.C]
    @property
    def D(self):
        return self.regs[Registers.D]
    @property
    def E(self):
        return self.regs[Registers.E]
    @property
    def F(self):
        return self.regs[Registers.F]

    def val(self, reg_or_imm):
        if is_reg(reg_or_imm):
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