"""Gera os ícones PNG do app (fundo verde-petróleo com um visto branco), sem dependências.

Uso: python ferramentas/icones.py
"""
import math, struct, zlib
from pathlib import Path

PASTA = Path(__file__).resolve().parent.parent / "icones"
FUNDO, TINTA = (0x0F, 0x6B, 0x64), (0xFF, 0xFF, 0xFF)
VISTO = [(0.28, 0.53), (0.43, 0.68), (0.73, 0.37)]  # mesmo desenho do icone.svg (viewBox 0..100)
ESP = 0.085


def dist_seg(px, py, a, b):
    (ax, ay), (bx, by) = a, b
    dx, dy = bx - ax, by - ay
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
    return math.hypot(px - ax - t * dx, py - ay - t * dy)


def png(n):
    linhas = []
    amostras = 4  # supersampling para suavizar a borda
    for y in range(n):
        linha = bytearray([0])
        for x in range(n):
            cob = 0
            for sy in range(amostras):
                for sx in range(amostras):
                    px, py = (x + (sx + .5) / amostras) / n, (y + (sy + .5) / amostras) / n
                    d = min(dist_seg(px, py, VISTO[0], VISTO[1]), dist_seg(px, py, VISTO[1], VISTO[2]))
                    cob += d <= ESP / 2
            f = cob / amostras ** 2
            linha += bytes(round(FUNDO[k] * (1 - f) + TINTA[k] * f) for k in range(3))
        linhas.append(bytes(linha))
    raw = zlib.compress(b"".join(linhas), 9)
    chunk = lambda t, d: struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", n, n, 8, 2, 0, 0, 0)) + chunk(b"IDAT", raw) + chunk(b"IEND", b"")


if __name__ == "__main__":
    PASTA.mkdir(exist_ok=True)
    for n in (180, 192, 512):
        (PASTA / f"icone-{n}.png").write_bytes(png(n))
        print(f"icone-{n}.png")
