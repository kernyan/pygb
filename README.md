# pygb
Python GB Emulator

# TODO
* [ ] gb architecture
* [ ] loading rom
    - skip boot rom
    - executes and writes to VRAM
* [X] skipping PPU implementation, just render VRAM into image

# Progress
```
Given 8K VRAM, render all tiles, and render OAM
```

Show all tiles
![image](./src/output/tiles_5000001.png)

Show OAM constructed tiles
![image](./src/output/oam_5000001.png)

# Reference
- https://gekkio.fi/files/gb-docs/gbctr.pdf
- has 8KB RAM
- ~4.19 MHz
- data bus is 8 bit
- address is 16 bit (65536 addressable)
    - cartridge (gb ROM)
    - display
    - IO (gamepad, audio, LCD)
    - interrupt controls
- display
    - 160×144 pixels
    - 4 shades of grey (white, light grey, dark grey and black)
    - shared access to 8K VRAM with CPU
        - tile set, collection of 8x8 bitmaps
        - background layer is 256x256 (32x32 tile)
        - OAM decides which tile used as sprite, filled by DMA from ROM or RAM

