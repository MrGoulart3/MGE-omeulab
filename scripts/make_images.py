"""Gera as imagens derivadas: WebP, og.png (1200x630) e ícones (favicon, apple-touch, manifest).

Uso: python3 scripts/make_images.py   (requer Pillow e fontTools+brotli; usa as fontes de assets/fonts)
"""

from __future__ import annotations

import io
import json
import math
from pathlib import Path

from fontTools.ttLib import TTFont
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
NAVY, CREAM, OCRE, MUTED = "#16202c", "#f6f4ef", "#e8894a", "#b5bdc8"
CPK = {"C": "#9aa5b4", "H": "#f2f0ea", "N": "#3b6fd4", "O": "#d8452f", "S": "#e2b62a"}
RADII = {"H": 0.31, "C": 0.76, "N": 0.71, "O": 0.66, "S": 1.05}
VIS = {"H": 0.25, "C": 0.38, "N": 0.37, "O": 0.36, "S": 0.50}


def webp_versions() -> None:
    """WebP de cada JPEG; as fotos largas também ganham versão de 640 px."""
    for src in sorted(ASSETS.glob("*.jpg")):
        if src.stem == "lab_ic_2":  # não usada nas páginas
            continue
        image = Image.open(src).convert("RGB")
        quality = 82 if src.stem != "hdl_video" else 85
        image.save(ASSETS / (src.stem + ".webp"), "WEBP", quality=quality, method=6)
        if image.width >= 800:
            small = image.resize((640, round(image.height * 640 / image.width)), Image.LANCZOS)
            small.save(ASSETS / (src.stem + "-640.webp"), "WEBP", quality=quality, method=6)


def font_from_woff2(name: str, size: int, axes: list[float] | None = None) -> ImageFont.FreeTypeFont:
    """Carrega uma fonte WOFF2 do site no Pillow (via conversão em memória)."""
    font = TTFont(ASSETS / "fonts" / name)
    font.flavor = None
    buffer = io.BytesIO()
    font.save(buffer)
    buffer.seek(0)
    loaded = ImageFont.truetype(buffer, size)
    if axes:
        loaded.set_variation_by_axes(axes)
    return loaded


def draw_molecule(size: int) -> Image.Image:
    """Bola-e-bastão da dipirona (dados de src/dipirona.json), fundo transparente."""
    atoms = json.loads((ROOT / "src/dipirona.json").read_text())
    n = len(atoms)
    cx, cy, cz = (sum(a[i] for a in atoms) / n for i in (1, 2, 3))
    ry, rx = 0.9, -0.45
    points = []
    for element, x, y, z in atoms:
        x, y, z = x - cx, y - cy, z - cz
        x, z = x * math.cos(ry) + z * math.sin(ry), -x * math.sin(ry) + z * math.cos(ry)
        y, z = y * math.cos(rx) - z * math.sin(rx), y * math.sin(rx) + z * math.cos(rx)
        points.append((element, x, y, z))
    extent = max(math.hypot(x, y, z) for _, x, y, z in points)
    scale = size / (2.05 * extent)
    projected = []
    for element, x, y, z in points:
        f = 1 + z * 0.04
        projected.append((element, size / 2 + x * scale * f, size / 2 - y * scale * f, z, VIS[element] * scale * f))
    bonds = []
    for i in range(n):
        for j in range(i + 1, n):
            d = math.dist(points[i][1:], points[j][1:])
            if d < 1.18 * (RADII[points[i][0]] + RADII[points[j][0]]):
                bonds.append((i, j))
    items = [(q[3], 0, i) for i, q in enumerate(projected)]
    items += [((projected[i][3] + projected[j][3]) / 2 - 0.01, 1, (i, j)) for i, j in bonds]
    items.sort(key=lambda item: item[0])
    layer = Image.new("RGBA", (size * 2, size * 2), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    k = 2
    for _, kind, ref in items:
        if kind == 1:
            a, b = projected[ref[0]], projected[ref[1]]
            mx, my = (a[1] + b[1]) / 2, (a[2] + b[2]) / 2
            width = max(2, round(0.13 * scale * k))
            draw.line([(a[1] * k, a[2] * k), (mx * k, my * k)], fill=CPK[a[0]], width=width)
            draw.line([(mx * k, my * k), (b[1] * k, b[2] * k)], fill=CPK[b[0]], width=width)
        else:
            element, x, y, _, r = projected[ref]
            draw.ellipse([(x - r) * k, (y - r) * k, (x + r) * k, (y + r) * k], fill=CPK[element], outline="#10161e", width=2)
            draw.ellipse([(x - r * 0.55) * k, (y - r * 0.6) * k, (x - r * 0.1) * k, (y - r * 0.15) * k], fill=(255, 255, 255, 70))
    return layer.resize((size, size), Image.LANCZOS)


def og_image() -> None:
    """Imagem de compartilhamento 1200x630: nome, linha de atuação e a molécula do site."""
    image = Image.new("RGB", (1200, 630), NAVY)
    draw = ImageDraw.Draw(image)
    molecule = draw_molecule(560)
    image.paste(molecule, (610, 35), molecule)
    draw.rectangle([0, 0, 14, 630], fill=OCRE)
    mono = font_from_woff2("ibm-plex-mono-latin-600-normal.woff2", 28)
    title = font_from_woff2("fraunces-latin-opsz-normal.woff2", 92, [144, 640])
    sans = font_from_woff2("ibm-plex-sans-latin-400-normal.woff2", 33)
    draw.text((80, 96), "O MEU LABORATÓRIO", font=mono, fill=OCRE)
    draw.text((80, 160), "Mário Goulart", font=title, fill=CREAM)
    draw.text((80, 262), "Envall", font=title, fill=CREAM)
    draw.rectangle([80, 398, 200, 402], fill=OCRE)
    draw.text((80, 428), "Química computacional", font=sans, fill=MUTED)
    draw.text((80, 474), "Ciências farmacêuticas", font=sans, fill=MUTED)
    draw.text((80, 548), "omeulab.com", font=mono, fill=CREAM)
    image.save(ASSETS / "og.png", optimize=True)


def double_dagger(size: int) -> Image.Image:
    """Ícone: ‡ (símbolo de estado de transição) creme sobre azul-marinho, desenhado com formas."""
    scale = 4
    s = size * scale
    image = Image.new("RGB", (s, s), NAVY)
    draw = ImageDraw.Draw(image)
    stem = s * 0.095
    cx = s / 2
    top, bottom = s * 0.17, s * 0.83
    draw.rectangle([cx - stem / 2, top, cx + stem / 2, bottom], fill=CREAM)
    for y in (0.40, 0.62):
        draw.rectangle([s * 0.27, s * y - stem * 0.4, s * 0.73, s * y + stem * 0.4], fill=CREAM)
    return image.resize((size, size), Image.LANCZOS)


def icons() -> None:
    double_dagger(180).save(ASSETS / "apple-touch-icon.png", optimize=True)
    double_dagger(192).save(ASSETS / "icon-192.png", optimize=True)
    double_dagger(512).save(ASSETS / "icon-512.png", optimize=True)
    double_dagger(256).save(ROOT / "favicon.ico", sizes=[(16, 16), (32, 32), (48, 48)])


if __name__ == "__main__":
    webp_versions()
    og_image()
    icons()
    print("Imagens geradas em assets/ e favicon.ico na raiz.")
