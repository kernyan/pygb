#! /usr/bin/env python3

import os
from pathlib import Path
from typing import Dict, List
from enum import Enum
import struct

from utils import GBFile
from decode import Decoder, OTYPE, Registers, Flags, FlagOp
from array import array

DEBUG = os.getenv("DEBUG", False)

ROM_FILE = Path(__file__).resolve().parents[1] / 'blue.gb'

BRANCH_OP = {
    OTYPE.JR, OTYPE.JP, OTYPE.CALL, OTYPE.RET
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

class MArea(Enum):
    INT      =  0x0    #     0 -  100     
    ROM      =  0x100  #   100 -  150     
    PROG     =  0x150  #   150 - 8000     
    VRAM_BK  =  0x8000 #  8000 - 9800     
    VRAM_BG1 =  0x9800 #  9800 - 9C00     
    VRAM_BG2 =  0x9C00 #  9C00 - A000     
    EXT      =  0xA000 #  A000 - C000     
    WORK     =  0xC000 #  C000 - E000     
    OAM      =  0xFE00 #  FE00 - FEA0     
    PORT     =  0xFF00 #  FF00 - FF80     
    STACK    =  0xFF80 #  FF80 - FFFE          


class Memory:
    def __init__(self):
        self.mmap = array('B', [0]*(64*1024))


class CPU:
    def __init__(self, rom: bytes, entry: int):
        self.rom = rom
        self.PC = entry
        self.decoder = Decoder(self.rom)
        self.regs = {r.name: 0 for r in Registers}
        self.regs[Registers.SP] = 0xFFFE
        self.flags = {f.name: False for f in Flags}
        self.mem = Memory()
    
    def fetch_and_decode(self):
        self.opcode = self.decoder(self.PC)

    def update_flags(self, flag_op: FlagOp):
        for f, v in flag_op.flags_to_set.items():
            self.flags[f] = v
    
    def offset(self, operand, section: MArea):
        if isinstance(operand, Registers):
            v = operand
            n = f'{operand.name}(0x{self.val(operand):X})'
        else:
            addr = section.value + self.val(operand)
            v = self.mem.mmap[addr]
            n = f'(0x{addr:X}(0x{v:X}))'
        return v, n

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
                if isinstance(self.opcode.o2, Registers):
                    print(f' {rname(self.opcode.o1)} {rname(self.opcode.o2)}(0x{o2:X})')
                else:
                    print(f' {rname(self.opcode.o1)} 0x{o2:X}')
                len = 2 if self.opcode.o1 in R16 else 1
                self.assign(self.opcode.o1, o2, len)
                return
            case OTYPE.LDH:
                v1, n1 = self.offset(self.opcode.o1, MArea.PORT)
                v2, n2 = self.offset(self.opcode.o2, MArea.PORT)
                print(f' {n1} {n2}')
                self.assign(v1, self.val(v2))
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
                    offset = self.signed(self.opcode.o2)
                    self.PC += offset if self.check_flags(self.opcode.o1) else self.opcode.length
                else:
                    print(f' 0x{self.opcode.o1:X}')
                    offset = self.signed(self.val(self.opcode.o1))
                    self.PC += offset
                return
            case OTYPE.XOR:
                print(f' {self.opcode.o1.name if is_reg(self.opcode.o1) else self.opcode.o1}')
                self.regs[Registers.A] ^= self.regs[self.opcode.o1]
                self.flags[Flags.Z] = self.regs[self.opcode.o1] == 0
                return
            case OTYPE.DI:
                print()
                return
            case OTYPE.CALL:
                print(f' 0x{self.opcode.o1:X}')
                self.push(self.PC + self.opcode.length, len = 2)
                self.PC = self.opcode.o1
                return
            case OTYPE.RES:
                print(f' {self.opcode.o1} {rname(self.opcode.o2)}(0x{self.val(self.opcode.o2):X})')
                self.regs[self.opcode.o2] &= ~(1 << self.opcode.o1)
                return
            case OTYPE.AND:
                print(f' A(0x{self.A:X}) 0x{self.val(self.opcode.o1):X}')
                self.regs[Registers.A] &= self.val(self.opcode.o1)
                self.flags[Flags.Z] = self.regs[Registers.A] == 0
                return
            case OTYPE.RET:
                addr = self.pop(self.PC, len = 2)
                print(f' 0x{addr:X}')
                self.PC = addr
                return
            case OTYPE.INC:
                print(f' {rname(self.opcode.o1)}(0x{self.val(self.opcode.o1):X})')
                if self.opcode.o1 in R16:
                    self.assign(self.opcode.o1, self.val(self.opcode.o1) + 1, len=2)
                else:
                    raise RuntimeError(f"Need to update flags for INC {self.opcode.o1}")
                return
            case OTYPE.DEC:
                print(f' {rname(self.opcode.o1)}(0x{self.val(self.opcode.o1):X})')
                if self.opcode.o1 in R16:
                    self.assign(self.opcode.o1, self.val(self.opcode.o1) - 1, len=2)
                else:
                    raise RuntimeError(f"Need to update flags for DEC {self.opcode.o1}")
                return
            case OTYPE.OR:
                print(f" {rname(self.opcode.o1)}(0x{self.val(self.opcode.o1)})")
                self.regs[Registers.A] |= self.val(self.opcode.o1)
                return
            case OTYPE.PUSH:
                print(f' {rname(self.opcode.o1)}(0x{getattr(self,self.opcode.o1):X})')
                self.push(getattr(self, self.opcode.o1), len = 2)
                return
            case _:
                raise RuntimeError(f"Unhandled opcode {self.opcode.mne}")

    def signed(self, val) -> int:
        return struct.unpack('b', int.to_bytes(val))[0]

    def check_flags(self, operand) -> bool:
        if operand in [Flags.NC, Flags.NZ, Flags.NH]:
            return self.flags[operand[-1]] == 0
        else:
            return self.flags[operand]

    def assign(self, operand, value, len=1):
        if operand in R16 and len != 2:
            raise RuntimeError(f"2 byte registers {operand} assigned with single byte {value}")
        if operand == Registers.BC:
            b = value.to_bytes(len, "little")
            self.regs[Registers.C] = b[0]
            self.regs[Registers.B] = b[1]
        elif operand == Registers.HL:
            b = value.to_bytes(len, "little")
            self.regs[Registers.L] = b[0]
            self.regs[Registers.H] = b[1]
        elif operand == Registers.HLa:
            assert len == 1, f'Assigning to address must be single byte, but {len}'
            self.mem.mmap[self.HL] = value
        elif isinstance(operand, Registers):
            self.regs[operand] = value
        else:
            if len > 1:
                self.mem.mmap[operand:operand+len] = array('B', value.to_bytes(2, 'little'))
            else:
                self.mem.mmap[operand] = value

    def push(self, value, len=1):
        self.regs[Registers.SP] -= len
        self.assign(self.SP, value, len)

    def pop(self, value, len=1):
        v = int.from_bytes(self.mem.mmap[self.SP:self.SP+len], 'little')
        self.regs[Registers.SP] += len
        return v

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
    @property
    def SP(self):
        return self.regs[Registers.SP]
    @property
    def HL(self):
        return (self.regs[Registers.H] & 0xFF) << 8 | (self.regs[Registers.L] & 0xFF)
    @property
    def BC(self):
        return (self.regs[Registers.B] & 0xFF) << 8 | (self.regs[Registers.C] & 0xFF)
    @property
    def DE(self):
        return (self.regs[Registers.D] & 0xFF) << 8 | (self.regs[Registers.E] & 0xFF)

    def val(self, reg_or_imm):
        if is_reg(reg_or_imm):
            return getattr(self, reg_or_imm.name)
        return reg_or_imm

    def step(self):
        self.fetch_and_decode()
        self.execute()

if __name__ == '__main__':
    gbfile = GBFile(ROM_FILE)
    cpu = CPU(gbfile.ROM, gbfile.entry_point)
    while True:
        cpu.step()