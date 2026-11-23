"""Deterministic original 3.0 pixel art for new weapons and refreshed world sprites."""
from __future__ import annotations

import hashlib
import math
from PIL import Image, ImageDraw

from generate_v2_art import ASSETS, SCENES, avatar, enemy, mix, rng, tile, weapon_icon
from src.sk import weapon as W, gamedata as G, codex as X
from src.sk.v30_weapons import ROWS


def weapon_30(key):
    spec = W.WEAPONS[key]
    im = weapon_icon(key, spec).resize((64, 64), Image.Resampling.NEAREST)
    d = ImageDraw.Draw(im)
    c = tuple(spec.color)
    light = mix(c, (255, 255, 255), .7)
    seed = int.from_bytes(hashlib.sha256(key.encode()).digest()[:4], 'big')
    # One key-specific crest on every model, plus visible rarity geometry.
    cx, cy = 31 + seed % 7 - 3, 29 + (seed // 7) % 7 - 3
    crest = seed % 5
    if crest == 0:
        d.polygon((cx, cy - 7, cx + 6, cy, cx, cy + 7, cx - 6, cy),
                  outline=light, fill=c)
    elif crest == 1:
        d.ellipse((cx - 6, cy - 6, cx + 6, cy + 6), outline=light, width=2)
        d.line((cx - 7, cy, cx + 7, cy), fill=c, width=2)
    elif crest == 2:
        d.polygon((cx - 7, cy + 5, cx, cy - 7, cx + 7, cy + 5),
                  fill=c, outline=light)
    elif crest == 3:
        for dx in (-4, 0, 4):
            d.line((cx + dx, cy - 6, cx + dx, cy + 5), fill=light, width=2)
    else:
        d.arc((cx - 7, cy - 7, cx + 7, cy + 7), 15, 310, fill=light, width=3)
        d.ellipse((cx - 2, cy - 2, cx + 2, cy + 2), fill=c)
    if W.quality_of(key) == 'radiant':
        for a in range(8):
            ang = a * math.tau / 8 + seed % 8 * .08
            x, y = 32 + math.cos(ang) * 25, 32 + math.sin(ang) * 25
            d.line((x, y, x + math.cos(ang) * 5, y + math.sin(ang) * 5),
                   fill=light, width=2)
    return im


def scene_tile(scene, part):
    im = tile(scene, part).resize((64, 64), Image.Resampling.NEAREST)
    d = ImageDraw.Draw(im)
    base, metal, glow, hot = SCENES[scene]
    rand = rng('v30/' + scene + '/' + part)
    # Extra texture stays beneath gameplay hazards and does not alter collision.
    for _ in range(12 if part.startswith('floor') else 6):
        x, y = rand.randrange(3, 60), rand.randrange(4, 59)
        color = mix(glow if rand.random() < .45 else hot, base, .58)
        d.line((x, y, x + rand.randrange(2, 7), y), fill=color, width=1)
    if part.startswith('floor'):
        d.rectangle((2, 2, 61, 61), outline=mix(metal, glow, .3))
        for x, y in ((8, 8), (55, 8), (8, 55), (55, 55)):
            d.rectangle((x, y, x + 2, y + 2), fill=glow)
        if scene == 'sewer':
            d.arc((10, 10, 54, 54), 25, 270, fill=glow, width=2)
        elif scene == 'd_mine':
            d.polygon((39, 36, 46, 24, 52, 39), fill=hot, outline=glow)
        elif scene == 'core':
            d.line((22, 4, 27, 19, 22, 31, 29, 42, 25, 59), fill=hot, width=2)
    else:
        d.line((8, 20, 56, 20), fill=glow, width=2)
        for x in (13, 48):
            d.ellipse((x - 3, 27, x + 3, 33), fill=hot, outline=glow)
    return im


def hero_30(key):
    im = avatar(key).resize((96, 96), Image.Resampling.NEAREST)
    d = ImageDraw.Draw(im)
    rand = rng('v30/hero/' + key)
    c = tuple(G.CHARACTERS[key].get('color', (160, 220, 230))) if isinstance(G.CHARACTERS[key], dict) else (160, 220, 230)
    # Armor seam, reflective visor and individual insignia.
    d.line((37, 29, 58, 29), fill=(245, 249, 255), width=2)
    d.line((28, 48, 36, 48), fill=c, width=2)
    d.line((60, 48, 68, 48), fill=c, width=2)
    for i in range(3):
        x = 43 + i * 4
        d.rectangle((x, 59, x + 2, 61), fill=c if rand.random() < .6 else (245, 249, 255))
    return im


def lucky_sprite():
    im = Image.new('RGBA', (88, 88))
    d = ImageDraw.Draw(im)
    d.ellipse((10, 17, 78, 78), fill=(42, 77, 75), outline=(24, 32, 46), width=4)
    d.polygon((19, 32, 34, 7, 44, 30, 55, 5, 69, 32),
              fill=(235, 182, 85), outline=(255, 236, 153))
    d.rounded_rectangle((20, 30, 68, 70), 8, fill=(91, 157, 115),
                        outline=(250, 216, 113), width=4)
    d.rectangle((26, 38, 62, 52), fill=(21, 35, 47), outline=(245, 222, 139), width=2)
    for x in (33, 54):
        d.ellipse((x - 4, 40, x + 4, 48), fill=(250, 244, 170))
    d.arc((31, 46, 57, 62), 5, 175, fill=(255, 227, 127), width=3)
    d.polygon((38, 54, 50, 54, 44, 68), fill=(253, 203, 82))
    for x, y in ((9, 27), (76, 23), (8, 65), (77, 64)):
        d.line((x - 4, y, x + 4, y), fill=(255, 244, 179), width=2)
        d.line((x, y - 4, x, y + 4), fill=(255, 244, 179), width=2)
    return im


def foe_30(key, category):
    if key == 'lucky_treasure':
        return lucky_sprite()
    base = enemy(key, category)
    boss = category in ('boss', 'bigboss')
    size = 208 if boss else 88
    im = base.resize((size, size), Image.Resampling.NEAREST)
    d = ImageDraw.Draw(im)
    rand = rng('v30/foe/' + key)
    color = (255, 221, 174) if boss else (190, 231, 255)
    for _ in range(6 if boss else 4):
        x, y = rand.randrange(size // 4, 3 * size // 4), rand.randrange(size // 4, 3 * size // 4)
        if im.getpixel((x, y))[3] > 0:
            d.line((x, y, x + 4, y), fill=color, width=1)
    return im


def material_icon(key):
    palette = {'scrap': (163, 178, 193), 'fiber': (143, 219, 141),
               'circuit': (101, 224, 212), 'crystal': (130, 190, 255),
               'alloy': (224, 185, 124), 'core': (236, 127, 164),
               'prism': (229, 185, 255), 'relic': (255, 229, 145)}
    c = palette[key]
    im = Image.new('RGBA', (48, 48))
    d = ImageDraw.Draw(im)
    seed = list(palette).index(key)
    if seed in (0, 4):
        d.polygon((8, 16, 24, 5, 40, 16, 40, 33, 24, 43, 8, 33), fill=c, outline=(255, 245, 215))
        for x in (16, 31): d.line((x, 15, x, 35), fill=(71, 81, 98), width=3)
    elif seed in (1, 2):
        for j in range(4):
            d.arc((5 + j * 3, 6 + j * 2, 40 - j * 2, 42 - j * 2), 20, 290, fill=c, width=3)
        d.ellipse((20, 20, 28, 28), fill=(244, 255, 219))
    else:
        d.polygon((24, 3, 39, 16, 35, 36, 24, 45, 10, 35, 7, 17), fill=c, outline=(248, 249, 255))
        d.line((24, 4, 24, 42), fill=(255, 255, 255), width=2)
        d.line((8, 17, 35, 35), fill=(255, 255, 255), width=2)
    d.point((20, 12), fill=(255, 255, 255))
    return im


def main():
    ASSETS.mkdir(parents=True, exist_ok=True)
    keys = [row[0] for group in ROWS.values() for row in group] + ['starfall_bow']
    for key in keys:
        weapon_30(key).save(ASSETS / f'wpn_{key}.png', optimize=True)
    for scene in SCENES:
        for part in ('floor', 'floor_alt', 'wall', 'wall_top'):
            scene_tile(scene, part).save(ASSETS / f'tile_{part}_{scene}.png', optimize=True)
    for key in G.CHAR_ORDER:
        hero_30(key).save(ASSETS / f'spr_player_{key}.png', optimize=True)
    hero_30('scout').save(ASSETS / 'spr_player.png', optimize=True)
    for key, record in X.ENEMY_CODEX.items():
        foe_30(key, record[2]).save(ASSETS / f'spr_enemy_{key}.png', optimize=True)
    for key in G.MAT_ORDER:
        material_icon(key).save(ASSETS / f'spr_material_{key}.png', optimize=True)
    print(f'3.0 art: {len(keys)} weapons, {len(SCENES)*4} tiles, '
          f'{len(G.CHAR_ORDER)} heroes, {len(X.ENEMY_CODEX)} enemies, {len(G.MAT_ORDER)} materials')


if __name__ == '__main__':
    main()
