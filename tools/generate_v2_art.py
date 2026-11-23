"""Generate original, deterministic neon pixel art for Ashen Zone 2.0.

The title painting is generated separately with image_gen and kept in
assets_raw/ashen_zone_v2_title.png. All gameplay sprites are authored as
small pixel grids here so their silhouettes, alpha and filenames are exact.
"""
from __future__ import annotations

import colorsys
import hashlib
import random
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.sk import weapon as W, gamedata as G, codex as X  # noqa: E402

ASSETS = ROOT / 'assets'
RAW = ROOT / 'assets_raw'
SCENES = {
    'crust': ((31, 29, 50), (53, 49, 75), (74, 219, 231), (216, 81, 194)),
    'sewer': ((25, 41, 38), (40, 67, 61), (93, 223, 158), (157, 255, 98)),
    'facility': ((39, 39, 55), (69, 68, 86), (101, 202, 255), (252, 164, 89)),
    'core': ((49, 24, 49), (89, 41, 69), (239, 96, 147), (255, 181, 108)),
    'd_mine': ((45, 36, 43), (82, 64, 67), (254, 179, 96), (255, 220, 123)),
    'd_lab': ((27, 42, 61), (47, 76, 97), (126, 219, 251), (190, 251, 255)),
    'd_gift': ((20, 49, 56), (34, 84, 85), (111, 251, 220), (251, 222, 130)),
}


def mix(a, b, f):
    return tuple(max(0, min(255, round(a[i] * (1 - f) + b[i] * f))) for i in range(3))


def rng(key):
    return random.Random(int.from_bytes(hashlib.sha256(key.encode()).digest()[:8], 'big'))


def ensure_palette(im):
    """给低色数像素图加入细小高光点，避免移动端低对比背景里消失。"""
    colors = {p[:3] for p in im.get_flattened_data()}
    if len(colors) < 5:
        d = ImageDraw.Draw(im)
        w = im.width
        for i, col in enumerate(((244, 249, 255), (126, 170, 235),
                                 (255, 211, 132), (93, 227, 194))):
            d.point((w - 7 + i, 3 + (i % 2)), fill=col)
    return im


def polish_sprite(im, rim=(10, 12, 22, 235)):
    """为角色/怪物像素图补绘 1px 轮廓描边与上缘微高光，提升暗背景立体感。"""
    w, h = im.size
    src = im.load()
    out = im.copy()
    dst = out.load()
    for y in range(h):
        for x in range(w):
            r, g, b, a = src[x, y]
            if a >= 140:
                if y > 0 and src[x, y - 1][3] < 40:
                    dst[x, y] = (min(255, r + 14), min(255, g + 14), min(255, b + 16), a)
            elif a < 20:
                for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
                    if 0 <= nx < w and 0 <= ny < h and src[nx, ny][3] >= 140:
                        dst[x, y] = rim
                        break
    return out


def tile(scene, kind):
    base, metal, glow, hot = SCENES[scene]
    r = rng(scene + kind)
    im = Image.new('RGB', (32, 32), base)
    d = ImageDraw.Draw(im)
    if kind in ('floor', 'floor_alt'):
        for y in range(0, 32, 4):
            for x in range(0, 32, 4):
                c = mix(base, metal, r.uniform(.02, .4))
                d.rectangle((x, y, x + 3, y + 3), fill=c)
        d.rectangle((1, 1, 30, 30), outline=mix(base, metal, .28), width=1)
        d.line((2, 2, 28, 2), fill=mix(base, glow, .08))
        d.line((2, 29, 28, 29), fill=mix(base, (0, 0, 0), .28))
        d.line((2, 3, 2, 27), fill=mix(metal, glow, .18))
        for _ in range(11):
            x, y = r.randrange(3, 29), r.randrange(4, 28)
            c = mix(metal, glow if r.random() < .22 else base, r.uniform(.12, .55))
            d.rectangle((x, y, x + r.randrange(1, 4), y + r.randrange(1, 3)), fill=c)
        if kind == 'floor_alt':
            d.line((5, 19, 11, 13, 19, 16, 27, 7), fill=mix(metal, glow, .55), width=1)
            d.line((12, 13, 17, 8, 20, 8), fill=hot, width=1)
            d.rectangle((13, 17, 17, 20), fill=mix(base, glow, .65))
        else:
            d.line((8, 9, 15, 9, 15, 12), fill=mix(glow, base, .35), width=1)
            d.line((25, 24, 21, 24, 21, 21), fill=mix(hot, base, .43), width=1)
        # 每个主题有一眼可认的地面笔触，不依赖统一砖面换色。
        if kind == 'floor_alt' and scene == 'crust':
            d.line((0, 26, 8, 20, 15, 23, 22, 14, 31, 17), fill=hot, width=2)
        elif kind == 'floor_alt' and scene == 'sewer':
            d.arc((3, 4, 28, 30), 20, 260, fill=glow, width=2)
            d.ellipse((18, 19, 27, 25), outline=hot, width=2)
        elif kind == 'floor_alt' and scene == 'facility':
            d.line((3, 16, 12, 16, 12, 7, 26, 7), fill=glow, width=2)
            d.rectangle((23, 5, 28, 10), fill=hot)
        elif kind == 'floor_alt' and scene == 'core':
            d.line((16, 0, 12, 9, 21, 15, 11, 24, 14, 31), fill=hot, width=3)
        elif kind == 'floor_alt' and scene == 'd_mine':
            for x, y in ((5, 8), (25, 20), (13, 27)):
                d.polygon((x, y - 3, x + 4, y, x, y + 5, x - 3, y), fill=glow)
        elif kind == 'floor_alt' and scene == 'd_lab':
            d.line((16, 3, 16, 28), fill=glow, width=2)
            d.line((4, 16, 28, 16), fill=glow, width=2)
            for x, y in ((8, 8), (24, 24)): d.line((x - 3, y - 3, x + 3, y + 3), fill=hot)
        elif kind == 'floor_alt' and scene == 'd_gift':
            d.arc((3, 4, 28, 30), 40, 320, fill=glow, width=2)
            d.line((16, 16, 13, 5), fill=hot, width=2)
            d.ellipse((10, 3, 16, 9), fill=glow)
    else:
        d.rectangle((0, 0, 31, 31), fill=mix(base, (0, 0, 0), .26))
        d.rectangle((2, 3, 29, 29), fill=metal, outline=mix(metal, glow, .34))
        d.rectangle((5, 6, 26, 26), fill=mix(base, metal, .35))
        d.line((3, 29, 28, 29), fill=mix(glow, base, .23), width=2)
        d.line((3, 30, 28, 30), fill=mix(glow, base, .60))
        d.rectangle((7, 8, 10, 11), fill=hot)
        d.rectangle((22, 8, 25, 11), fill=glow)
        d.line((7, 16, 25, 16), fill=mix(glow, base, .45))
        d.line((15, 16, 15, 27), fill=mix(glow, base, .65))
        if kind == 'wall_top':
            d.rectangle((0, 0, 31, 6), fill=mix(metal, glow, .22))
            d.line((0, 6, 31, 6), fill=glow, width=1)
            d.rectangle((14, 0, 17, 4), fill=hot)
        for _ in range(6):
            x, y = r.randrange(5, 27), r.randrange(8, 28)
            d.point((x, y), fill=mix(glow, base, r.uniform(.3, .7)))
    return im


def weapon_icon(key, spec):
    if key in {row[0] for row in W._V21}:
        return weapon_icon_21(key, spec)
    r = rng(key)
    c = tuple(spec.color)
    dark, steel, pale = (18, 20, 34), (82, 92, 116), mix(c, (255, 255, 255), .65)
    im = Image.new('RGBA', (32, 32), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    shape = 'blade' if spec.melee else ('launcher' if spec.aoe else
              'longgun' if spec.speed > 700 or spec.pierce >= 2 else
              'scatter' if spec.count >= 3 else 'gun')
    # Each icon has a real silhouette with its own barrel, grip, vents and core.
    if shape == 'blade':
        if 'hammer' in key or 'axe' in key:
            d.polygon((4, 25, 9, 27, 20, 15, 17, 12), fill=steel, outline=dark)
            d.polygon((13, 9, 20, 3, 29, 12, 23, 20), fill=c, outline=dark)
            d.line((17, 10, 25, 13), fill=pale, width=2)
        elif 'spear' in key:
            d.line((4, 28, 25, 6), fill=steel, width=4)
            d.polygon((19, 9, 27, 1, 30, 3, 26, 13), fill=c, outline=dark)
        elif 'dagger' in key:
            for dx in (-5, 5):
                d.line((16 + dx, 27, 16 + dx, 9), fill=steel, width=4)
                d.polygon((13 + dx, 11, 16 + dx, 2, 19 + dx, 11), fill=c, outline=pale)
        else:
            d.line((6, 27, 16, 17), fill=steel, width=5)
            d.polygon((13, 19, 18, 4, 27, 2, 25, 11, 18, 23), fill=c, outline=dark)
            d.line((19, 8, 22, 17), fill=pale, width=2)
        d.ellipse((7, 21, 12, 26), fill=dark, outline=pale)
    else:
        length = 21 if shape == 'gun' else 25
        width = 5 if shape == 'gun' else (10 if shape == 'launcher' else 7)
        d.rounded_rectangle((3, 12, length, 12 + width), radius=2, fill=dark, outline=steel)
        d.rectangle((length - 1, 13, min(30, length + (4 if shape == 'launcher' else 7)),
                     11 + width), fill=mix(steel, c, .45), outline=dark)
        d.rectangle((8, 17, 12, 27), fill=steel, outline=dark)
        d.polygon((13, 19, 20, 19, 18, 24, 14, 24), fill=mix(c, dark, .44))
        if shape == 'scatter':
            for yy in (11, 14, 17):
                d.rectangle((22, yy, 29, yy + 1), fill=c)
        elif shape == 'launcher':
            d.ellipse((18, 9, 28, 21), fill=dark, outline=c, width=2)
            d.ellipse((22, 12, 26, 18), fill=pale)
        else:
            d.line((13, 11, length + 1, 11), fill=pale, width=1)
        if 'crossbow' in key or 'bow' in key:
            d.arc((18, 3, 30, 27), 80, 280, fill=pale, width=2)
            d.line((23, 4, 23, 26), fill=c, width=1)
        if 'rail' in key or 'prism' in key:
            d.line((17, 8, 28, 8), fill=c, width=2)
            d.point((28, 8), fill=pale)
    # Core, vents and tiny chromatic rivets are key-specific.
    for i in range(3):
        x = 9 + i * 3 + r.randrange(-1, 2)
        y = 12 + r.randrange(0, 4)
        d.rectangle((x, y, x + 1, y + 1), fill=(pale if i == 1 else c))
    signature = sum(ord(ch) for ch in key) % 6
    if not spec.melee:
        if signature == 0:
            d.ellipse((15, 5, 22, 12), outline=c, width=2)
        elif signature == 1:
            d.polygon((14, 6, 20, 8, 17, 11), fill=pale)
        elif signature == 2:
            d.rectangle((3, 8, 8, 12), fill=c, outline=dark)
        elif signature == 3:
            d.line((6, 6, 17, 6), fill=c, width=2)
        elif signature == 4:
            d.ellipse((4, 16, 9, 21), fill=c, outline=dark)
        else:
            d.line((12, 7, 12, 11), fill=pale, width=2)
            d.line((19, 7, 19, 11), fill=c, width=2)
    d.point((max(2, min(30, 4 + len(key) % 19)), 29), fill=c)
    return im


def weapon_icon_21(key, spec):
    """2.1 专属轮廓，不用旧模板的换色枪/剑。"""
    im = Image.new('RGBA', (32, 32), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    c = tuple(spec.color)
    pale = mix(c, (255, 255, 255), .65)
    dark = (14, 19, 34)
    steel = (97, 112, 139)
    if key in ('crust_glaive', 'lab_cryo_staff'):
        d.line((16, 29, 16, 5), fill=steel, width=3)
        if key == 'crust_glaive':
            d.arc((8, 1, 27, 19), 40, 250, fill=c, width=5)
            d.polygon((22, 2, 29, 7, 22, 12), fill=pale)
        else:
            d.polygon((16, 0, 25, 10, 16, 20, 7, 10), fill=c, outline=pale)
            d.line((6, 9, 26, 9), fill=pale, width=2)
    elif key in ('sewer_harpoon', 'meteor_pike'):
        d.line((3, 24, 25, 9), fill=steel, width=3)
        d.polygon((19, 10, 29, 1, 29, 11, 22, 16), fill=c, outline=pale)
        if key == 'sewer_harpoon':
            d.line((21, 6, 16, 1), fill=c, width=2)
            d.line((27, 13, 31, 18), fill=c, width=2)
        else:
            d.polygon((17, 15, 12, 13, 14, 20), fill=pale)
    elif key == 'facility_saw':
        d.ellipse((5, 3, 27, 25), fill=steel, outline=c, width=3)
        d.ellipse((12, 10, 20, 18), fill=dark, outline=pale, width=2)
        for x, y in ((2, 11), (26, 2), (27, 21), (8, 27)):
            d.polygon((x, y, x + 5, y + 1, x + 2, y + 6), fill=pale)
        d.rectangle((13, 24, 19, 31), fill=dark, outline=c)
    elif key in ('core_repeater', 'facility_overdrive', 'lab_zerobeam'):
        d.rectangle((3, 11, 23, 22), fill=dark, outline=steel, width=2)
        d.rectangle((20, 12, 30, 19), fill=c, outline=pale, width=2)
        d.line((7, 23, 5, 29), fill=steel, width=4)
        if key == 'core_repeater':
            for y in (5, 8, 24): d.line((9, y, 25, y), fill=c, width=2)
            d.ellipse((11, 12, 18, 19), fill=pale)
        elif key == 'facility_overdrive':
            for y in (2, 24): d.rectangle((9, y, 28, y + 5), fill=steel, outline=c)
            d.ellipse((20, 10, 31, 22), fill=dark, outline=pale, width=3)
        else:
            d.polygon((11, 2, 19, 2, 23, 11, 7, 11), fill=c, outline=pale)
            d.line((25, 3, 25, 27), fill=pale, width=2)
    elif key == 'mine_drill':
        d.rectangle((3, 12, 14, 24), fill=dark, outline=steel, width=2)
        d.polygon((13, 10, 29, 18, 13, 26), fill=c, outline=pale)
        for x in (16, 21, 26): d.line((x, 13, x - 2, 23), fill=dark, width=2)
    elif key == 'gift_starbow':
        d.arc((9, 0, 30, 31), 70, 285, fill=c, width=4)
        d.line((21, 2, 21, 29), fill=pale, width=1)
        d.line((2, 16, 29, 16), fill=steel, width=3)
        d.polygon((26, 11, 31, 16, 26, 21), fill=pale)
        for x, y in ((9, 5), (4, 27), (29, 3)): d.point((x, y), fill=pale)
    elif key == 'sewer_abyssfang':
        for x, tilt in ((8, -2), (23, 2)):
            d.polygon((x, 29, x - 3, 15, x + tilt, 1, x + 5, 14, x + 4, 25), fill=c, outline=pale)
            d.line((x - 5, 25, x + 5, 25), fill=steel, width=2)
    elif key == 'core_nihility':
        d.line((7, 29, 24, 6), fill=steel, width=4)
        d.arc((10, 0, 31, 25), 205, 25, fill=c, width=5)
        d.polygon((6, 3, 13, 4, 10, 12), fill=pale)
    elif key == 'mine_faultaxe':
        d.line((16, 30, 17, 4), fill=steel, width=4)
        for s in (-1, 1):
            d.polygon((17, 4, 17 + s * 12, 8, 17 + s * 14, 20,
                       17 + s * 5, 17), fill=c, outline=pale)
        d.rectangle((14, 24, 19, 29), fill=dark, outline=pale)
    elif key == 'gift_dawnkeeper':
        d.polygon((16, 1, 22, 7, 20, 22, 12, 22, 10, 7), fill=c, outline=pale)
        d.line((5, 22, 27, 22), fill=pale, width=3)
        d.line((16, 22, 16, 31), fill=steel, width=3)
        for s in (-1, 1): d.polygon((16 + s * 5, 21, 16 + s * 12, 13, 16 + s * 13, 23), fill=pale)
    elif key == 'moss_whip':
        d.arc((4, 2, 30, 26), 160, 450, fill=c, width=4)
        d.line((19, 22, 13, 31), fill=steel, width=4)
        for x, y in ((5, 12), (9, 4), (28, 7)): d.polygon((x, y, x + 5, y - 3, x + 3, y + 5), fill=pale)
    elif key == 'mirror_shield':
        d.polygon((16, 1, 30, 8, 27, 24, 16, 31, 5, 24, 2, 8), fill=steel, outline=pale)
        d.polygon((16, 6, 25, 11, 23, 21, 16, 26, 9, 21, 7, 11), fill=c, outline=dark)
        d.line((7, 12, 24, 12), fill=pale, width=2)
    else:  # 焦土断刃、堑壕直刀：不同刀身缺口和护手
        d.line((5, 28, 12, 21), fill=steel, width=5)
        d.polygon((10, 22, 23, 4, 30, 2, 26, 11, 14, 25), fill=c, outline=pale)
        d.line((7, 19, 18, 28), fill=dark, width=3)
        if key == 'crust_ruinblade':
            d.polygon((22, 5, 18, 8, 23, 11), fill=dark)
            d.polygon((16, 13, 13, 17, 18, 18), fill=dark)
        elif key == 'trench_blade':
            d.line((12, 22, 30, 4), fill=pale, width=2)
            d.line((8, 23, 23, 8), fill=steel, width=1)
    return ensure_palette(im)


def avatar(key):
    colors = {
        'scout': (75, 230, 240), 'engineer': (255, 181, 94),
        'ranger': (148, 243, 132), 'medic': (241, 116, 164),
        'ghost': (175, 130, 255), 'prime': (247, 224, 132),
        'archivist': (114, 214, 252), 'seedkeeper': (155, 226, 121),
    }
    c = colors[key]
    im = Image.new('RGBA', (48, 48), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    dark, armor, light = (16, 20, 34), mix(c, (75, 74, 103), .58), mix(c, (255, 255, 255), .55)
    d.ellipse((5, 8, 43, 44), fill=(5, 8, 20, 90))
    d.polygon((9, 24, 14, 19, 34, 19, 39, 24, 36, 39, 12, 39), fill=dark)
    d.rounded_rectangle((11, 22, 36, 39), 4, fill=armor, outline=dark, width=2)
    d.rectangle((18, 28, 29, 34), fill=mix(c, dark, .35), outline=light)
    d.rectangle((12, 18, 18, 31), fill=armor, outline=light)
    d.rectangle((30, 18, 36, 31), fill=armor, outline=light)
    d.polygon((16, 10, 21, 5, 29, 5, 34, 11, 33, 23, 15, 23), fill=armor, outline=dark)
    d.rectangle((17, 14, 32, 18), fill=dark, outline=light)
    d.rectangle((19, 15, 30, 17), fill=c)
    d.rectangle((23, 15, 25, 16), fill=(255, 255, 255))
    d.rectangle((17, 39, 22, 43), fill=armor, outline=dark)
    d.rectangle((26, 39, 31, 43), fill=armor, outline=dark)
    if key == 'engineer':
        d.rectangle((13, 2, 34, 6), fill=(255, 190, 91), outline=dark)
        d.rectangle((5, 23, 11, 35), fill=(87, 103, 119), outline=dark)
    elif key == 'ranger':
        d.polygon((8, 23, 15, 12, 14, 35, 4, 43), fill=mix(c, dark, .6))
    elif key == 'medic':
        d.rectangle((22, 27, 26, 36), fill=(255, 244, 245))
        d.rectangle((19, 30, 29, 33), fill=(255, 244, 245))
    elif key == 'ghost':
        d.polygon((11, 7, 24, 2, 38, 7, 41, 39, 36, 43, 33, 23, 15, 23), fill=mix(c, dark, .67), outline=c)
    elif key == 'prime':
        for x in (7, 39):
            d.polygon((x, 12, x - 3, 2, x + 2, 6), fill=light)
        d.ellipse((18, 26, 30, 38), outline=c, width=2)
    elif key == 'archivist':
        d.rectangle((3, 19, 13, 39), fill=(43, 72, 103), outline=light, width=2)
        d.line((6, 23, 10, 23), fill=c, width=2)
        d.line((6, 28, 10, 28), fill=c, width=2)
        d.arc((32, 4, 47, 18), 180, 350, fill=c, width=2)
        d.ellipse((35, 7, 44, 16), outline=light, width=2)
        d.line((39, 16, 45, 22), fill=light, width=2)
    elif key == 'seedkeeper':
        d.polygon((4, 23, 12, 17, 16, 38, 7, 42), fill=(55, 104, 67), outline=light)
        d.ellipse((35, 24, 46, 38), fill=(83, 146, 84), outline=c, width=2)
        d.line((40, 24, 40, 10), fill=light, width=2)
        d.polygon((40, 16, 34, 10, 40, 7), fill=c)
        d.polygon((40, 15, 46, 9, 42, 6), fill=light)
    else:
        d.rectangle((21, 2, 27, 6), fill=light)
    # 2.1 职业轮廓：头部、背包、肩甲和道具各有清晰身份。
    if key == 'scout':
        d.polygon((8, 18, 2, 12, 5, 30, 11, 33), fill=light, outline=dark)
        d.polygon((40, 18, 46, 12, 43, 30, 37, 33), fill=light, outline=dark)
        d.line((10, 6, 5, 2), fill=c, width=2)
    elif key == 'engineer':
        d.rectangle((36, 22, 45, 38), fill=dark, outline=c, width=2)
        d.ellipse((37, 26, 44, 33), outline=light, width=2)
        d.line((11, 24, 4, 24), fill=c, width=3)
    elif key == 'ranger':
        d.arc((3, 3, 21, 39), 65, 285, fill=light, width=2)
        d.line((11, 5, 11, 39), fill=c, width=1)
        d.polygon((36, 15, 46, 26, 39, 38), fill=dark, outline=c)
    elif key == 'medic':
        d.rounded_rectangle((34, 20, 45, 37), 2, fill=(234, 231, 235), outline=c)
        d.line((39, 23, 39, 34), fill=(225, 81, 119), width=2)
        d.line((36, 29, 43, 29), fill=(225, 81, 119), width=2)
        d.ellipse((17, 1, 31, 8), fill=dark, outline=light, width=2)
    elif key == 'ghost':
        d.polygon((6, 17, 1, 31, 9, 36, 13, 27), fill=dark, outline=light)
        d.polygon((42, 17, 47, 31, 39, 36, 35, 27), fill=dark, outline=light)
        d.line((20, 7, 29, 7), fill=c, width=2)
    elif key == 'prime':
        for px in (4, 40):
            d.polygon((px, 15, px + 4, 4, px + 8, 15), fill=light, outline=dark)
        d.arc((8, 18, 39, 45), 30, 150, fill=c, width=3)
    d.line((20, 6, 28, 6), fill=light, width=1)
    d.point((21, 15), fill=(255, 255, 255))
    return polish_sprite(im)


def enemy(key, category):
    seed = rng(key)
    h = (int.from_bytes(hashlib.sha256(key.encode()).digest()[:2], 'big') % 360) / 360
    c = tuple(round(v * 255) for v in colorsys.hsv_to_rgb(h, .62, .95))
    if key in ('slime', 'crawler', 'slug'): c = (134, 224, 132)
    if category in ('boss', 'bigboss'): c = mix(c, (232, 87, 204), .35)
    if category not in ('boss', 'bigboss'):
        return minion_icon(key, category, c)
    size = 104 if category in ('boss', 'bigboss') else 44
    im = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    cx, cy = size // 2, size // 2
    rr = size * (.36 if category in ('boss', 'bigboss') else .34)
    dark, metal, light = (19, 18, 34), mix(c, (53, 58, 75), .68), mix(c, (255, 255, 255), .53)
    form = seed.randrange(5)
    if form == 0:
        d.ellipse((cx - rr, cy - rr, cx + rr, cy + rr), fill=metal, outline=dark, width=3)
    elif form == 1:
        d.polygon((cx, cy - rr - 3, cx + rr, cy - rr // 3, cx + rr, cy + rr // 2,
                   cx, cy + rr + 2, cx - rr, cy + rr // 2, cx - rr, cy - rr // 3), fill=metal)
        d.line((cx, cy - rr - 3, cx + rr, cy - rr // 3, cx + rr, cy + rr // 2), fill=dark, width=3)
    elif form == 2:
        d.rounded_rectangle((cx - rr, cy - rr, cx + rr, cy + rr), 5, fill=metal, outline=dark, width=3)
    elif form == 3:
        d.polygon((cx, cy - rr - 3, cx + rr + 2, cy, cx, cy + rr + 3, cx - rr - 2, cy), fill=metal, outline=dark)
    else:
        d.ellipse((cx - rr, cy - rr, cx + rr, cy + rr), fill=mix(c, metal, .45), outline=dark, width=3)
    for side in (-1, 1):
        x = cx + side * rr
        d.polygon((x, cy - 4, x + side * rr * .55, cy - rr * .5,
                   x + side * rr * .65, cy + rr * .3, x, cy + 5), fill=metal, outline=dark)
        if category in ('boss', 'bigboss'):
            d.polygon((cx + side * rr * .48, cy - rr * .7,
                       cx + side * rr * .6, cy - rr * 1.4,
                       cx + side * rr * .78, cy - rr * .5), fill=c, outline=light)
    core = rr * (.52 if category in ('boss', 'bigboss') else .45)
    d.ellipse((cx - core, cy - core, cx + core, cy + core), fill=dark, outline=c, width=2)
    d.polygon((cx, cy - core + 2, cx + core * .7, cy,
               cx, cy + core - 2, cx - core * .7, cy), fill=c, outline=light)
    d.ellipse((cx - 2, cy - 2, cx + 2, cy + 2), fill=(255, 255, 255))
    for _ in range(6 if category in ('boss', 'bigboss') else 3):
        a = seed.uniform(0, 6.283)
        x = int(cx + rr * .7 * __import__('math').cos(a))
        y = int(cy + rr * .7 * __import__('math').sin(a))
        d.rectangle((x, y, x + 2, y + 2), fill=light)
    if category in ('boss', 'bigboss'):
        if key == 'warlord':
            d.polygon((8, 26, 21, 4, 34, 29), fill=metal, outline=c)
            d.polygon((size - 8, 26, size - 21, 4, size - 34, 29), fill=metal, outline=c)
            d.rectangle((cx - 18, cy - 24, cx + 18, cy - 15), fill=dark, outline=light, width=2)
        elif key == 'swarmqueen':
            for yy in (cy + 20, cy + 32, cy + 44):
                d.ellipse((cx - 22, yy - 8, cx + 22, yy + 8), fill=metal, outline=c, width=2)
            for xx in (11, 27, size - 27, size - 11):
                d.ellipse((xx - 4, cy + 21, xx + 4, cy + 29), fill=light, outline=dark)
        elif key == 'mech':
            for xx in (4, size - 28):
                d.rectangle((xx, cy - 16, xx + 24, cy + 10), fill=dark, outline=c, width=3)
                d.rectangle((xx + 4, cy - 9, xx + 20, cy - 3), fill=light)
            d.rectangle((cx - 15, 7, cx + 15, 17), fill=metal, outline=light)
        elif key in ('protocol', 'origin'):
            for side in (-1, 1):
                d.polygon((cx + side * 14, cy - 24,
                           cx + side * 36, cy - 50,
                           cx + side * 26, cy + 3), fill=c, outline=light)
                d.line((cx + side * 13, cy + 25, cx + side * 39, cy + 39), fill=c, width=4)
            d.polygon((cx, cy - 46, cx + 12, cy - 20, cx, cy - 27, cx - 12, cy - 20), fill=light)
        elif key == 'foreman':
            d.polygon((cx - 10, 3, cx + 10, 3, cx + 19, 21, cx, 34, cx - 19, 21), fill=metal, outline=light)
            d.polygon((cx - 8, 15, cx + 8, 15, cx, 37), fill=c)
            d.rectangle((6, cy + 9, 31, cy + 22), fill=dark, outline=c)
        elif key == 'specimen':
            d.rounded_rectangle((17, 4, size - 18, size - 7), 10,
                                outline=light, width=5)
            d.line((27, 12, 27, size - 15), fill=(205, 247, 255), width=2)
            d.line((size - 27, 12, size - 27, size - 15), fill=(205, 247, 255), width=2)
            d.polygon((cx, 4, cx + 17, 20, cx, 15, cx - 17, 20), fill=light)
        elif key == 'guardian':
            for side in (-1, 1):
                d.polygon((cx + side * 24, cy - 19,
                           cx + side * 48, cy - 41,
                           cx + side * 42, cy + 15,
                           cx + side * 24, cy + 30), fill=metal, outline=light)
                d.line((cx + side * 34, cy - 21, cx + side * 39, cy + 13), fill=c, width=4)
        elif key == 'crust_sentinel':
            d.rectangle((10, 12, 94, 24), fill=metal, outline=c, width=3)
            for xx in (13, 77): d.polygon((xx, 22, xx + 14, 22, xx + 7, 49), fill=light)
        elif key == 'sewer_serpent':
            for xx, yy in ((24, 78), (41, 82), (63, 79), (82, 66)):
                d.ellipse((xx - 10, yy - 8, xx + 10, yy + 8), fill=c, outline=dark, width=3)
            d.polygon((15, 46, 3, 34, 12, 64), fill=light)
        elif key == 'facility_smelter':
            d.rectangle((18, 12, 86, 92), outline=c, width=5)
            d.polygon((34, 9, 70, 9, 81, 30, 23, 30), fill=metal, outline=light)
            for xx in (12, 91): d.rectangle((xx - 8, 41, xx + 8, 69), fill=dark, outline=c, width=3)
        elif key == 'mine_excavator':
            d.polygon((52, 0, 78, 28, 52, 52, 26, 28), fill=metal, outline=light)
            d.line((52, 0, 52, 43), fill=c, width=6)
            for xx in (8, 77): d.ellipse((xx, 70, xx + 20, 96), fill=dark, outline=c, width=4)
        elif key == 'lab_cryowarden':
            for xx in (8, 82):
                d.polygon((xx, 78, xx + 8, 10, xx + 18, 78), fill=light, outline=c)
            d.rectangle((29, 0, 75, 20), fill=dark, outline=light, width=3)
            d.line((39, 5, 65, 5), fill=c, width=4)
        elif key == 'gift_bloom':
            for a in range(0, 360, 45):
                import math
                px = cx + 38 * math.cos(math.radians(a))
                py = cy + 38 * math.sin(math.radians(a))
                d.ellipse((px - 10, py - 17, px + 10, py + 17), fill=metal, outline=light, width=3)
            d.ellipse((cx - 17, cy - 17, cx + 17, cy + 17), fill=c, outline=light, width=3)
    return polish_sprite(im, rim=(18, 8, 28, 240))


def minion_icon(key, category, c):
    """按生物门类而非统一核心圆球绘制，精英拥有独立装甲轮廓。"""
    im = Image.new('RGBA', (44, 44), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    dark = (15, 20, 31)
    pale = mix(c, (255, 255, 255), .58)
    metal = mix(c, (58, 68, 88), .6)
    r = rng(key)
    if any(t in key for t in ('slime', 'spore', 'frostbite')):
        # 软体、孢子、冰壳分别有液滴、菌伞、晶簇的外形。
        if 'spore' in key:
            d.polygon((3, 20, 11, 8, 30, 5, 41, 21, 33, 26, 10, 25), fill=metal, outline=pale)
            d.rectangle((16, 24, 29, 40), fill=c, outline=dark, width=2)
            for x in (11, 20, 30): d.ellipse((x, 14, x + 4, 18), fill=pale)
        elif 'frost' in key:
            for i in range(6):
                a = i * 1.047
                import math
                x = 22 + 19 * math.cos(a); y = 22 + 19 * math.sin(a)
                d.polygon((22, 22, x - 3, y - 3, x, y, x + 3, y + 3), fill=c, outline=pale)
            d.ellipse((13, 13, 31, 31), fill=dark, outline=pale, width=3)
        else:
            d.polygon((4, 31, 8, 16, 17, 6, 29, 9, 37, 19, 40, 34, 29, 39, 12, 38), fill=c, outline=dark)
            d.ellipse((10, 20, 34, 36), fill=metal, outline=pale, width=2)
            for x in (14, 29): d.ellipse((x, 23, x + 4, 29), fill=dark)
    elif any(t in key for t in ('slug', 'crawler', 'rockworm', 'leech')):
        d.ellipse((5, 12, 39, 36), fill=metal, outline=dark, width=2)
        d.polygon((7, 21, 19, 5, 31, 10, 38, 28, 26, 37, 11, 34), fill=c, outline=pale)
        if 'leech' in key:
            d.ellipse((9, 20, 30, 37), fill=dark, outline=pale, width=2)
            for x in (12, 18, 24): d.polygon((x, 25, x + 3, 29, x, 33), fill=pale)
        elif 'rockworm' in key:
            for x in (9, 17, 25, 33): d.line((x, 13, x + 4, 34), fill=dark, width=2)
            d.polygon((30, 5, 43, 22, 31, 20), fill=pale)
        else:
            for x in (6, 16, 27, 36): d.line((x, 31, x - 3, 41), fill=c, width=3)
    elif any(t in key for t in ('drone', 'turret', 'minebot', 'purifier')):
        d.rectangle((9, 11, 35, 34), fill=metal, outline=pale, width=2)
        if 'turret' in key:
            d.rectangle((16, 1, 28, 20), fill=dark, outline=c, width=2)
            for x in (3, 35): d.rectangle((x, 24, x + 6, 37), fill=c)
        elif 'drone' in key:
            for x in (2, 34): d.ellipse((x, 14, x + 8, 28), fill=dark, outline=c, width=2)
            d.polygon((14, 8, 22, 2, 30, 8), fill=c)
        elif 'minebot' in key:
            d.polygon((22, 0, 30, 14, 14, 14), fill=c, outline=pale)
            for x in (7, 29): d.ellipse((x, 33, x + 8, 42), fill=dark, outline=c, width=2)
        else:
            d.arc((3, 1, 41, 40), 190, 350, fill=c, width=4)
            d.rectangle((17, 14, 27, 31), fill=pale)
        d.ellipse((17, 18, 27, 28), fill=dark, outline=c, width=2)
    elif any(t in key for t in ('wraith', 'sprite', 'wanderer')):
        d.polygon((22, 2, 36, 11, 40, 34, 32, 42, 22, 35, 12, 42, 4, 34, 8, 11), fill=metal, outline=c)
        d.polygon((10, 9, 22, 3, 34, 9, 29, 23, 15, 23), fill=dark, outline=pale)
        d.line((15, 19, 19, 19), fill=c, width=2)
        d.line((25, 19, 29, 19), fill=c, width=2)
        if key == 'wanderer': d.line((35, 12, 39, 42), fill=pale, width=3)
    elif key == 'mimic':
        d.rectangle((4, 10, 40, 37), fill=metal, outline=c, width=3)
        d.polygon((5, 17, 15, 24, 21, 18, 27, 24, 39, 17), fill=dark)
        for x in (10, 20, 30): d.polygon((x, 20, x + 4, 29, x + 8, 20), fill=pale)
        d.ellipse((17, 5, 27, 13), fill=c)
    else:  # 自爆囊等
        d.polygon((22, 3, 39, 17, 35, 36, 22, 42, 8, 35, 4, 17), fill=c, outline=dark)
        for a in range(0, 360, 90):
            import math
            x = 22 + 13 * math.cos(math.radians(a)); y = 22 + 13 * math.sin(math.radians(a))
            d.ellipse((x - 3, y - 3, x + 3, y + 3), fill=pale)
    # 同家族成员仍因器官与铆钉排列不同；精英加外露肩甲和冠刺。
    for _ in range(3):
        x, y = r.randrange(12, 33), r.randrange(14, 33)
        d.rectangle((x, y, x + 1, y + 1), fill=pale)
    if category == 'elite':
        for s in (-1, 1):
            d.polygon((22 + s * 13, 10, 22 + s * 18, 1,
                       22 + s * 20, 24), fill=metal, outline=pale)
        d.line((10, 38, 34, 38), fill=c, width=3)
    return polish_sprite(ensure_palette(im))


def collectible_icon(key, tier):
    """十件文物有独立形状；同品级仅共享边框光晕。"""
    im = Image.new('RGBA', (48, 48), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    c = (255, 221, 123) if tier == 'superb' else (126, 225, 237)
    d.ellipse((4, 4, 44, 44), outline=(*c, 105), width=2)
    if key == 'gear_cog':
        for x, y in ((20, 5), (20, 37), (5, 20), (37, 20)):
            d.rectangle((x, y, x + 7, y + 7), fill=c)
        d.ellipse((10, 10, 38, 38), fill=(77, 81, 99), outline=c, width=3)
        d.ellipse((20, 20, 28, 28), fill=(12, 17, 27))
    elif key == 'glass_shard':
        d.polygon((23, 2, 40, 16, 29, 42, 11, 33, 8, 11), fill=(59, 149, 166), outline=c)
        d.line((23, 3, 25, 34, 11, 33), fill=(220, 254, 255), width=2)
    elif key == 'doll_rabbit':
        d.ellipse((14, 15, 34, 36), fill=(177, 131, 153), outline=c, width=2)
        for x in (17, 27): d.ellipse((x, 4, x + 5, 23), fill=(209, 177, 192), outline=c)
        d.point((20, 24), fill=(8, 9, 22)); d.point((28, 24), fill=(8, 9, 22))
    elif key == 'ledger':
        d.polygon((8, 11, 22, 7, 40, 11, 38, 39, 23, 34, 9, 39), fill=(121, 86, 69), outline=c)
        d.line((23, 9, 23, 34), fill=c, width=2)
        for y in (17, 22, 27): d.line((13, y, 20, y), fill=(230, 215, 176))
    elif key == 'coin_pressed':
        d.ellipse((8, 14, 40, 34), fill=(181, 138, 72), outline=c, width=3)
        d.line((13, 24, 35, 24), fill=(245, 218, 157), width=2)
    elif key == 'ring_copper':
        d.ellipse((9, 9, 39, 39), outline=(177, 91, 59), width=7)
        d.ellipse((10, 10, 38, 38), outline=c, width=2)
        d.polygon((20, 3, 28, 3, 32, 11, 24, 17, 16, 11), fill=c)
    elif key == 'seed_pod':
        d.ellipse((14, 12, 34, 40), fill=(97, 151, 72), outline=c, width=3)
        d.line((24, 13, 24, 38), fill=(213, 251, 156), width=2)
        d.polygon((24, 16, 6, 8, 16, 25), fill=(116, 205, 95))
    elif key == 'music_box':
        d.rectangle((7, 19, 40, 38), fill=(90, 70, 119), outline=c, width=3)
        d.arc((16, 6, 34, 27), 180, 355, fill=c, width=3)
        for x in (14, 23, 32): d.line((x, 20, x, 32), fill=(230, 201, 150), width=2)
    elif key == 'photo':
        d.rectangle((8, 6, 40, 42), fill=(238, 218, 190), outline=c, width=2)
        d.polygon((12, 29, 22, 18, 29, 27, 36, 16, 36, 37, 12, 37), fill=(89, 123, 137))
        d.ellipse((15, 12, 21, 18), fill=(250, 241, 178))
    else:  # protocol page
        d.polygon((10, 4, 34, 7, 39, 39, 14, 43), fill=(88, 84, 123), outline=c)
        d.polygon((23, 12, 31, 21, 23, 31, 15, 21), fill=c)
    return ensure_palette(im)


def chest_icon(kind, tier):
    im = Image.new('RGBA', (40, 36), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    col = {'coin': (245, 192, 82), 'heal': (235, 95, 119),
           'material': (113, 220, 168), 'weapon': (136, 183, 255),
           'collect': (211, 139, 247)}[kind]
    bright = mix(col, (255, 255, 255), .55 if tier == 'superb' else .2)
    d.rectangle((3, 13, 36, 32), fill=(37, 39, 57), outline=bright, width=2)
    d.polygon((5, 14, 10, 5, 30, 5, 35, 14), fill=(54, 54, 77), outline=col)
    for x in (8, 30): d.rectangle((x, 12, x + 2, 31), fill=bright)
    if kind == 'coin': d.ellipse((14, 16, 25, 27), fill=col, outline=bright)
    elif kind == 'heal':
        d.rectangle((17, 16, 22, 28), fill=bright)
        d.rectangle((13, 20, 26, 24), fill=bright)
    elif kind == 'material': d.polygon((20, 15, 27, 21, 20, 28, 13, 21), fill=col, outline=bright)
    elif kind == 'weapon':
        d.line((13, 26, 26, 16), fill=bright, width=4)
        d.line((12, 19, 22, 29), fill=col, width=2)
    else: d.polygon((20, 14, 26, 20, 23, 28, 16, 28, 13, 20), fill=bright, outline=col)
    if tier == 'superb':
        for x, y in ((3, 2), (35, 3), (38, 22), (1, 23)):
            d.line((x - 2, y, x + 2, y), fill=bright)
            d.line((x, y - 2, x, y + 2), fill=bright)
    return ensure_palette(im)


def trap_icon(kind):
    im = Image.new('RGBA', (42, 42), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    if kind == 'spike':
        for x in (5, 16, 27): d.polygon((x, 34, x + 5, 5, x + 10, 34), fill=(188, 197, 218), outline=(73, 86, 104))
    elif kind == 'poison':
        d.ellipse((4, 19, 38, 36), fill=(48, 155, 83), outline=(177, 246, 90), width=3)
        for x, y in ((14, 22), (26, 27), (20, 13)): d.ellipse((x, y, x + 4, y + 4), fill=(208, 255, 126))
    elif kind == 'shock':
        d.ellipse((4, 4, 38, 38), outline=(111, 197, 255), width=3)
        d.polygon((24, 2, 13, 21, 23, 21, 17, 40, 32, 17, 23, 17), fill=(202, 245, 255))
    elif kind == 'slow':
        d.ellipse((3, 15, 39, 36), fill=(91, 71, 68), outline=(178, 135, 100), width=3)
        d.arc((8, 18, 30, 33), 0, 180, fill=(221, 179, 122), width=2)
    else:
        d.rectangle((9, 27, 33, 37), fill=(80, 71, 78), outline=(255, 149, 72), width=3)
        d.polygon((13, 28, 7, 16, 16, 19, 21, 3, 28, 19, 36, 11, 31, 28), fill=(255, 134, 68), outline=(255, 221, 115))
    return ensure_palette(im)


def main():
    ASSETS.mkdir(parents=True, exist_ok=True)
    title = RAW / 'ashen_zone_v2_title.png'
    if not title.is_file():
        raise SystemExit('Missing generated title artwork: ' + str(title))
    with Image.open(title) as source:
        source.convert('RGB').resize((640, 360), Image.Resampling.LANCZOS).save(ASSETS / 'bg_title.png', optimize=True)
    for scene in SCENES:
        for kind in ('floor', 'floor_alt', 'wall', 'wall_top'):
            tile(scene, kind).save(ASSETS / f'tile_{kind}_{scene}.png', optimize=True)
    for key in W.ORDER:
        weapon_icon(key, W.WEAPONS[key]).save(ASSETS / f'wpn_{key}.png', optimize=True)
    for key in G.CHAR_ORDER:
        avatar(key).save(ASSETS / f'spr_player_{key}.png', optimize=True)
    avatar('scout').save(ASSETS / 'spr_player.png', optimize=True)
    for key, record in X.ENEMY_CODEX.items():
        enemy(key, record[2]).save(ASSETS / f'spr_enemy_{key}.png', optimize=True)
    for key, record in X.COLLECTS.items():
        collectible_icon(key, record[1]).save(ASSETS / f'spr_collect_{key}.png', optimize=True)
    for kind in G.CHESTS:
        for tier in ('normal', 'superb'):
            chest_icon(kind, tier).save(ASSETS / f'spr_chest_{kind}_{tier}.png', optimize=True)
    for kind in ('spike', 'poison', 'shock', 'slow', 'flame'):
        trap_icon(kind).save(ASSETS / f'spr_trap_{kind}.png', optimize=True)
    for k in ('slime', 'bomber', 'drone'):
        enemy(k, 'small').save(ASSETS / f'spr_enemy_{k}.png', optimize=True)
    enemy('origin', 'bigboss').save(ASSETS / 'spr_boss.png', optimize=True)
    print('V2.1 art:', len(W.ORDER), 'weapons, 6 heroes,', len(X.ENEMY_CODEX),
          'enemies, 10 collectibles, 10 chests, 5 traps, 7 scenes, 1 title')


if __name__ == '__main__':
    main()
