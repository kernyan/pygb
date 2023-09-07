#! /usr/bin/env python3

import json
from typing import Dict, Any
from enum import Enum
from pprint import pprint as pp
from pprint import pformat

from pathlib import Path

OPCODE_DATA = Path(__file__).resolve().parent / 'opcodes.json'

class Flags(str, Enum):
    Z = 'Z' # zero
    N = 'N' # subtract
    H = 'H' # half carry
    C = 'C' # carry
    INTRP = 'INTRP' # interrupt


class BranchMnemonics(str):
    Z = 'Z' # zero
    N = 'N' # subtract
    H = 'H' # half carry
    C = 'C' # carry

    NZ = 'NZ' # not zero
    NH = 'NH' # not half carry
    NC = 'NC' # not carry


def parse_flag(flags: list[str]) -> dict[str, bool]:

    flags_to_set = {} # {Flags.Z: True/False} to set/clear

    lookup = { 0: Flags.Z, 1: Flags.N, 2: Flags.H, 3: Flags.C }

    for idx, status in enumerate(flags):
        match status:
            case '0':
                flags_to_set[lookup[idx]] = False
            case '1':
                flags_to_set[lookup[idx]] = True
            case '-':
                pass
            case _:
                raise RuntimeError(f"Unexpected flag status {status}")

    return flags_to_set


class FlagOp:
    def __init__(self, flags: list[str]):
        self.flags_to_set = parse_flag(flags)


class Registers(str, Enum):
    A = 'A'
    B = 'B'
    C = 'C'
    D = 'D'
    E = 'E'
    F = 'F'
    H = 'H'
    L = 'L'

    SP = 'SP'


class OperandMnemonic(str, Enum):
    A = 'A'
    B = 'B'
    C = 'C'
    D = 'D'
    E = 'E'
    F = 'F'
    H = 'H'
    L = 'L'

    Ca = '(C)'

    BC = 'BC' # union of B and C
    DE = 'DE' # union of D and E
    HL = 'HL' # union of H and L
    SP = 'SP' # stack pointer

    BCa = '(BC)'
    DEa = '(DE)'
    HLa = '(HL)'

    HLp = '(HL+)'
    HLs = '(HL-)'

    # immediates
    r8 = 'r8'
    a8a = '(a8)'
    a16a = '(a16)'
    d8a = '(d8)'
    d16a = '(d16)'


class IMM:
    """
    converts operand mnemonic of type imm into value (i.e. 1 or 2 byte value to be loaded from ROM)
    """
    def __init__(self, operand: str):
        # d8     8 bit data
        # d16   16 bit data
        # r8     8 bit relative address
        # (a8)   8 bit absolute address
        # (a16) 16 bit absolute address

        self.value = None
        if operand[0] in ['a', 'd', 'r'] and int(operand[1:]) in [8, 16]:
            self.dtype = operand[0]
            self.size = int(operand[1:]) // 8
            assert self.size in [1,2], f"imm must be either 1, or 2 bytes, but got {operand}"
        elif operand[0] == '(' and operand[-1] == ')':
            self.dtype = operand[1]
            self.size = int(operand[2:-1]) // 8
            assert self.size in [1,2], f"imm must be either 1, or 2 bytes, but got {operand}"
        else:
            try:
                self.value = int(operand, 16)
            except Exception as e:
                raise RuntimeError(f"{operand} is not an imm. {e}")

    def resolve(self, ROM: bytes, PC: int):
        """
        load imm value from ROM, either 1, or 2 bytes ahead of PC
        """
        if self.value is not None: # if not None, means is imm literal
            self.value = int.from_bytes(ROM[PC+1:PC+self.size+1], 'little')


def parse_operand_mne(mne: OperandMnemonic):
    """
    interprets z80 operand 1, or 2 into
    - either imm, if so, load it from ROM
    - register/register pairs, and if so whether to dereference, and post inc/dec them
    """

    high = None
    low = None
    offset = None
    imm = None
    post = None
    deref = False

    match len(mne):
        case 1:
            low = mne
        case 2:
            low = mne[1]
            high = mne[0]
        case 3:
            assert mne == '(C)', f"C reg is the only single byte register expected to be dereferenced: {mne}"
            low = mne[1]
            deref = True
        case 4:
            assert mne[0] == '('
            assert mne[3] == ')'
            if mne[1] == 'r': # imm type
                imm = IMM(mne)
            else:
                high = mne[1]
                low = mne[2]
                deref = True
        case 5:
            assert mne[0] == '('
            assert mne[4] == ')'
            if mne[1] in ('a', 'd'): # imm type
                imm = IMM(mne) 
            else:
                high = mne[1]
                low = mne[2]
                post = mne[3]
                deref = True
        case 7:
            assert mne[0] == '('
            assert mne[6] == ')'
            assert mne[3] == '+'
            high = mne[1]
            low = mne[2]
            offset = IMM(mne[4:6]) # e.g. r8
            deref = True
        case _:
            raise RuntimeError(f'Unexpected {mne} encountered')

    return high, low, offset, imm, post, deref


class Operand:
    """
    converts json operand into representation of either
    1. imm, or
    2. registers (or deference addr, and if should post inc/dec)
    """
    def __init__(self, mne: OperandMnemonic):
        high, low, offset, imm, post, deref = parse_operand_mne(mne)
        self.high = Registers(high) if high else None
        self.low = Registers(low) if low else None
        self.offset = offset
        self.imm = imm
        self.post = post
        self.deref = deref

        if self.imm:
            self.type = "imm"
        else:
            assert self.low, f"Operand should be of register type {self.low}"
            self.type = "reg"

    @staticmethod
    def from_imm(value: int):
        op = Operand(OperandMnemonic('r8'))
        op.high = None
        op.low = None
        op.imm = IMM(hex(value))
        op.post = None
        op.deref = False
        return op

#R16 = [Registers.BC, Registers.HL, Registers.SP]

# 34 Opcode Types
class OTYPE(str, Enum):
    NOP = 'NOP'
    JP = 'JP'
    LD = 'LD'
    CP = 'CP'
    JR = 'JR'
    XOR = 'XOR'
    DI = 'DI' # disable interrupt
    LDH = 'LDH' # load into high mem 0xFF(xx)
    CALL = 'CALL'
    AND = 'AND'
    RET = 'RET'
    INC = 'INC'
    DEC = 'DEC'
    OR = 'OR'
    PUSH = 'PUSH'

    # extended
    RES = 'RES' # reset

    # unimplemented
    ADC = 'ADC'
    ADD = 'ADD'
    CCF = 'CCF'
    CPL = 'CPL'
    DAA = 'DAA'
    EI = 'EI'
    HALT = 'HALT'
    POP = 'POP'
    PREF = 'PREFI'
    RETI = 'RETI'
    RLA = 'RLA'
    RLCA = 'RLCA'
    RRA = 'RRA'
    RRCA = 'RRCA'
    RST = 'RST'
    SBC = 'SBC'
    SCF = 'SCF'
    STOP = 'STOP'
    SUB = 'SUB'


class Opcode:
    """
    converts opcode at PC location into
    length: size of opcode in bytes
    mne: op mnemonic
    o1: operand1
    o2: operand2
    flags: contains dict of flags_to_set
    branch_conditions: contains flags whose condition determines branching

    # only for convenience
    ROM: catridge text section
    PC: PC address
    json: full opcode json
    """
    def __init__(self, json: Dict[str, Any], ROM: bytes, PC: int):
        self.mne: OTYPE = OTYPE(json['mnemonic'])
        self.length: int = json['length']
        self.o1: Operand | None = None
        self.o2: Operand | None = None
        self.flags: FlagOp = FlagOp(json['flags'])
        self.branch_condition: BranchMnemonics | None = None
        self.ROM: bytes = ROM
        self.PC: int = PC
        self.json: dict[str, Any] = json

        match self.mne:
            case OTYPE.NOP:
                pass
            case OTYPE.JP:
                self.o1 = self.reg_or_imm(json['operand1'])
            case OTYPE.LD:
                self.o1 = self.reg_or_imm(json['operand1'])
                self.o2 = self.reg_or_imm(json['operand2'])
            case OTYPE.CP:
                self.o1 = self.reg_or_imm(json['operand1']) # if imm should read next byte
            case OTYPE.JR:
                if 'operand2' in json: # means is conditional jump on operand1 being True
                    self.branch_condition = BranchMnemonics(json['operand1'])
                    assert json['operand2'] == 'r8', f'Unexpected operand2 of JR. Is {json["operand2"]} instead of r8'
                    self.o2 = Operand.from_imm(ROM[PC+1])
                else:
                    self.o1 = Operand.from_imm(ROM[PC+1])
            case OTYPE.XOR:
                self.o1 = self.reg_or_imm(json['operand1'])
            case OTYPE.DI:
                self.flags.flags_to_set[Flags.INTRP] = False
            case OTYPE.LDH:
                self.o1 = self.reg_or_imm(json['operand1'])
                self.o2 = self.reg_or_imm(json['operand2'])
            case OTYPE.CALL:
                self.o1 = self.reg_or_imm(json['operand1'])
                if 'operand2' in json:
                    self.o2 = self.reg_or_imm(json['operand2'])
            case OTYPE.RES:
                self.o1 = self.reg_or_imm(json['operand1'])
                self.o2 = self.reg_or_imm(json['operand2'])
            case OTYPE.AND:
                self.o1 = self.reg_or_imm(json['operand1'])
            case OTYPE.RET:
                pass
            case OTYPE.INC:
                self.o1 = self.reg_or_imm(json['operand1'])
            case OTYPE.DEC:
                self.o1 = self.reg_or_imm(json['operand1'])
            case OTYPE.OR:
                self.o1 = self.reg_or_imm(json['operand1'])
            case OTYPE.PUSH:
                self.o1 = self.reg_or_imm(json['operand1'])
            case _:
                raise RuntimeError(f'Unhandled decode {self.mne} {pformat(self.json)}')

    def __repr__(self) -> str:
        o = dict(mne=self.mne,
                 length=self.length,
                 flags=self.flags,
                 o1=self.o1,
                 o2=self.o2)
        return pformat(o)

    def reg_or_imm(self, operand: str):
        """
        returns either register, or immediate/address
        """
        op_class = Operand(OperandMnemonic(operand))
        if isinstance(op_class.imm, IMM):
            op_class.imm.resolve(self.ROM, self.PC)
        if isinstance(op_class.offset, IMM):
            op_class.offset.resolve(self.ROM, self.PC)
        return op_class


class Decoder:
    def __init__(self, ROM):
        with open(OPCODE_DATA, 'r') as f:
            self.raw = json.load(f)
        self.reg_op = self.raw['unprefixed']
        self.ext_op = self.raw['cbprefixed']
        self.ROM = ROM

    def summary(self):
        mne = set()
        for k, v in self.reg_op.items():
            o = f"{k} {v['length']} {v['mnemonic']:8} {v['addr']} {v['group']:12}"
            mne.add(v['mnemonic'])
            if 'operand1' in v:
                o += f" {v['operand1']:4} "
            if 'operand2' in v:
                o += f" {v['operand2']:4}"
            print(o)
        pp(mne)
    
    def __call__(self, PC):
        opcode = self.ROM[PC]
        opcode = '0x' + f'{opcode:0>2X}'.lower()
        if opcode == '0xcb':
            opcode = '0x' + f'{self.ROM[PC+1]:0>2X}'.lower()
            return Opcode(self.ext_op[opcode], self.ROM, PC + 1)
        else:
            return Opcode(self.reg_op[opcode], self.ROM, PC)


if __name__ == '__main__':
    decoder = Decoder(None)
    decoder.summary()
