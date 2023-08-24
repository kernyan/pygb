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

class Registers(str, Enum):
    A = 'A'
    B = 'B'
    C = 'C'
    D = 'D'
    E = 'E'
    F = 'F'
    H = 'H'
    L = 'L'

# 34 Opcode Types
class OTYPE(str, Enum):
    NOP = 'NOP'
    JP = 'JP'
    LD = 'LD'
    CP = 'CP'
    JR = 'JR'
    XOR = 'XOR'

    # unimplemented
    ADC = 'ADC'
    ADD = 'ADD'
    AND = 'AND'
    CALL = 'CALL'
    CCF = 'CCF'
    CPL = 'CPL'
    DAA = 'DAA'
    DEC = 'DEC'
    DI = 'DI'
    EI = 'EI'
    HALT = 'HALT'
    INC = 'INC'
    OR = 'OR'
    POP = 'POP'
    PREF = 'PREFI'
    PUSH = 'PUSH'
    RET = 'RET'
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


def reg_or_imm(operand: str):
    try:
        out = Registers(operand)
    except:
        out = int(operand, 16)
    return out

class Opcode:
    def __init__(self, json: Dict[str, Any], ROM: bytes, PC):
        self.mne = OTYPE(json['mnemonic'])
        self.length = json['length']
        self.n = None
        self.o1 = None
        self.o2 = None
        self.flags = json['flags']
        match self.mne:
            case OTYPE.NOP:
                return
            case OTYPE.JP:
                self.n = int.from_bytes(ROM[PC+1:PC+3], 'little')
                return
            case OTYPE.LD:
                self.o1 = reg_or_imm(json['operand1'])
                match json['operand2']:
                    case 'd8':
                        self.o2 = ROM[PC+1]
                    case _:
                        raise RuntimeError(f'Unhandled load {json}')
                return
            case OTYPE.CP:
                self.o1 = reg_or_imm(json['operand1']) # if imm should read next byte
                return
            case OTYPE.JR:
                if 'operand2' in json:
                    self.o1 = Flags(json['operand1'])
                    assert json['operand2'] == 'r8', f'Unexpected operand2 of JR. Is {json["operand2"]} instead of r8'
                    self.o2 = ROM[PC+1]
                else:
                    self.o1 = ROM[PC+1]
                return
            case OTYPE.XOR:
                self.o1 = reg_or_imm(json['operand1'])
                return
            case _:
                raise RuntimeError(f'Unhandled decode {self.mne}')

    def __repr__(self) -> str:
        o = dict(mne=self.mne,
                 length=self.length,
                 nn=self.nn,
                 o1=self.o1,
                 o2=self.o2)
        return pformat(o)


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
        if opcode == '0xCB':
            raise RuntimeError('Extended CB unhandled')
        else:
            return Opcode(self.reg_op[opcode], self.ROM, PC)


if __name__ == '__main__':
    decoder = Decoder(None)
    decoder.summary()
