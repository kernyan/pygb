#! /usr/bin/env python3

import json
from typing import Dict, Any
from enum import Enum

from pathlib import Path

OPCODE_DATA = Path(__file__).resolve().parent / 'opcodes.json'

class Registers(str, Enum):
    A = 'A'
    B = 'B'
    C = 'C'
    D = 'D'
    E = 'E'
    F = 'F'
    H = 'H'
    L = 'L'

class OTYPE(str, Enum):
    NOP = 'NOP'
    JP = 'JP'
    LD = 'LD'
    CP = 'CP'

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
        self.nn = None
        self.o1 = None
        self.o2 = None
        print(self.mne)
        match self.mne:
            case OTYPE.NOP:
                return
            case OTYPE.JP:
                self.nn = int.from_bytes(ROM[PC+1:PC+3], 'little')
                return
            case OTYPE.LD:
                self.o1 = reg_or_imm(json['operand1'])
                self.o2 = reg_or_imm(json['operand2'])
                return
            case OTYPE.CP:
                self.o1 = reg_or_imm(json['operand1'])
                return
            case _:
                raise RuntimeError(f'Unhandled decode {self.mne}')

class Decoder:
    def __init__(self, ROM):
        with open(OPCODE_DATA, 'r') as f:
            self.raw = json.load(f)
        self.reg_op = self.raw['unprefixed']
        self.ext_op = self.raw['cbprefixed']
        self.ROM = ROM

    def summary(self):
        for k, v in self.reg_op.items():
            o = f"{k} {v['length']} {v['mnemonic']:8} {v['addr']} {v['group']:12}"
            if 'operand1' in v:
                o += f" {v['operand1']:4} "
            if 'operand2' in v:
                o += f" {v['operand2']:4}"
            print(o)
    
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
