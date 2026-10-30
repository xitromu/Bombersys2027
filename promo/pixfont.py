"""Растровый шрифт игровых автоматов: читает системные .fon Windows (CGA 8×8, кириллица в кодировке 866).

Формат .fon — исполняемый файл NE с ресурсами RT_FONT; внутри каждого — заголовок FNT и столбцы байтов на знак.
"""

from __future__ import annotations

import struct
from pathlib import Path

import numpy as np

RT_FONT = 0x8008


def fon_resources(data: bytes) -> list[bytes]:
    ne = struct.unpack_from("<I", data, 0x3C)[0]
    if data[ne:ne + 2] != b"NE":
        raise ValueError("не файл NE")
    table = ne + struct.unpack_from("<H", data, ne + 0x24)[0]
    shift = struct.unpack_from("<H", data, table)[0]
    at = table + 2
    fonts = []
    while True:
        kind = struct.unpack_from("<H", data, at)[0]
        if kind == 0:
            return fonts
        count = struct.unpack_from("<H", data, at + 2)[0]
        at += 8
        for _ in range(count):
            offset, length = struct.unpack_from("<HH", data, at)
            if kind == RT_FONT:
                fonts.append(data[offset << shift:(offset << shift) + (length << shift)])
            at += 12


class PixFont:
    def __init__(self, path: str | Path, encoding: str = "cp866"):
        fnt = fon_resources(Path(path).read_bytes())[0]
        version = struct.unpack_from("<H", fnt, 0)[0]
        self.height = struct.unpack_from("<H", fnt, 88)[0]
        first, last = fnt[95], fnt[96]
        self.encoding = encoding
        self.glyphs: dict[int, np.ndarray] = {}
        entry, size = (148, 6) if version == 0x300 else (118, 4)
        for code in range(first, last + 1):
            at = entry + (code - first) * size
            width = struct.unpack_from("<H", fnt, at)[0]
            offset = struct.unpack_from("<I" if version == 0x300 else "<H", fnt, at + 2)[0]
            columns = (width + 7) // 8
            bits = np.zeros((self.height, width), dtype=bool)
            for column in range(columns):
                for row in range(self.height):
                    byte = fnt[offset + column * self.height + row]
                    for bit in range(8):
                        x = column * 8 + bit
                        if x < width and byte & (0x80 >> bit):
                            bits[row, x] = True
            self.glyphs[code] = bits

    def mask(self, text: str, spacing: int = 0) -> np.ndarray:
        """Строка → логический массив (высота шрифта × сумма ширин)."""
        parts = []
        for byte in text.encode(self.encoding, "replace"):
            parts.append(self.glyphs.get(byte, self.glyphs[ord("?")]))
            if spacing:
                parts.append(np.zeros((self.height, spacing), dtype=bool))
        return np.hstack(parts)
