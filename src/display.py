#! /usr/bin/env python3

from pathlib import Path

import json
import struct

import numpy as np
from numpy.typing import NDArray
import matplotlib.pyplot as plt

OAM_SIZE = 0xA0 # 40 of 4 bytes
OAM_ENTRY_SIZE = 4

VRAM_SIZE = 8192
TILE_WIDTH = 8
TILE_HEIGHT = 8
COLOR_CHANNEL = 2 # 0 is white, 1 is light gray, 2 is dark gray, and 3 is black.
TILE_SIZE = TILE_WIDTH * TILE_HEIGHT * COLOR_CHANNEL // 8


FRAMES = Path(__file__).parent.resolve() / "input"
RENDERED_OUTPUT = Path(__file__).parent.resolve() / "output"

if not RENDERED_OUTPUT.is_dir():
    RENDERED_OUTPUT.mkdir(parents=True, exist_ok=True)

def make_vram(json_dat):
    o = [json_dat[f'VRAM0_{i}'] for i in range(VRAM_SIZE)]
    vram = struct.pack(f'{VRAM_SIZE}B', *o)
    return vram

def make_oam(json_dat):
    o = [json_dat[f'OAM_{i}'] for i in range(OAM_SIZE)]
    dat = struct.pack(f'{OAM_SIZE}B', *o)
    return dat

# Function to convert a single tile's data to an 8x8 pixel array
def tile_to_pixels(tile_data: bytes) -> NDArray:
    '''
    tile is 8x8 pixel for 2 bits color channel = 128 bits = 16 bytes
     ===================
     |     7  6  ... 0 |
     | 0   L  L        |
     | 1   H  H        |
     | ...             |
     | 15              |
     ===================

      0b{HL} from byte 0 bit 7, byte 1 bit 7 goes to row 0, col 0 for the 8x8 pixel
      0b{HL} from byte 0 bit 6, byte 1 bit 6 goes to row 0, col 1 for the 8x8 pixel

      0b{HL} from byte 2 bit 7, byte 3 bit 7 goes to row 1, col 0 for the 8x8 pixel

    Output is
      8x8 np array with range 0-3
    '''
    pixels = np.zeros((TILE_WIDTH, TILE_HEIGHT), dtype=np.uint8)
    for row in range(TILE_HEIGHT):
        byte1 = tile_data[row * 2]
        byte2 = tile_data[row * 2 + 1]
        for col in range(TILE_HEIGHT):
            color_idx = ((byte1 >> (7 - col)) & 1) | (((byte2 >> (7 - col)) & 1) << 1)
            pixels[row, col] = color_idx
    return pixels


# Function to convert VRAM data to an image
def vram_to_image(vram_data: bytes) -> NDArray:
    '''
    8K / 16 = 512 tile
    display as 32 x 16 tiles
    '''
    TILE_ROW_COUNT = 32
    TILE_COL_COUNT = 16
    image = np.zeros((TILE_ROW_COUNT * 8, TILE_COL_COUNT * 8), dtype=np.uint8)
    for tile_index in range(0, len(vram_data) // TILE_SIZE):
        tile_data = vram_data[tile_index * TILE_SIZE:tile_index * TILE_SIZE + TILE_SIZE]
        tile_col = (tile_index % 16) * 8
        tile_row = (tile_index // 32) * 8
        print(tile_row, tile_col)
        image[tile_row:tile_row+8, tile_col:tile_col+8] = tile_to_pixels(tile_data)
    return image

def save_tiles_as_png(vram_data, fname):
    image_data = vram_to_image(vram_data)
    plt.imshow(image_data, cmap='gray', vmin=0, vmax=1<<COLOR_CHANNEL - 1)
    plt.axis('off')
    plt.savefig(fname)


def oam_to_image(oam_data, vram_data):
    '''
    OAM is 160 bytes, 40*4 bytes
    Each OAM 4 byte entry identifies a tile index and start pixel position
    '''
    image = np.zeros((256, 256), dtype=np.uint8)
    for i in range(0, len(oam_data), OAM_ENTRY_SIZE):
        row = oam_data[i]             # Row position (+ 8 pixels)
        col = oam_data[i + 1]         # Col position (+ 8 pixels)
        tile_index = oam_data[i + 2]  # Tile Number
        flags = oam_data[i + 3]       # Flags (e.g., priority, flip, color palette)
        tile_data = vram_data[tile_index * 16:tile_index * 16 + 16]
        sprite_tile = tile_to_pixels(tile_data)
        image[row:row+8, col:col+8] = sprite_tile
    return image

# Generate and save the image
def render_oam(oam_data, sprite_vram_section, fname):
    image_data = oam_to_image(oam_data, sprite_vram_section)
    plt.imshow(image_data, cmap='gray', vmin=0, vmax=3)
    plt.axis('off')
    plt.savefig(fname)


if __name__ == '__main__':
    frames = list(FRAMES.glob("*.json")) # assume VRAM coming from json as list of single bytes
    frames = sorted(frames, key=lambda x: int(x.stem.split('_')[1]))[0:1]
    for frame in frames:
        frame_idx = int(frame.stem.split('_')[1])
        print(frame.name)
        with open(frame, 'r') as f:
            json_dat = json.load(f)
        vram = make_vram(json_dat)
        oam = make_oam(json_dat)

        fname = RENDERED_OUTPUT /  f'tiles_{frame_idx}.png'
        save_tiles_as_png(vram, fname)

        fname = RENDERED_OUTPUT /  f'oam_{frame_idx}.png'
        render_oam(oam, vram, fname)
