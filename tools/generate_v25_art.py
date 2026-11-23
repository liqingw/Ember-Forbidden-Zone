"""Generate only the new 2.5 weapon and armed-enemy models."""
from pathlib import Path
from PIL import Image, ImageDraw

from generate_v2_art import weapon_icon
from src.sk import weapon as W

ASSETS = Path(__file__).resolve().parents[1] / 'assets'


def armed_enemy(mode, color):
    im = Image.new('RGBA', (48, 48))
    d = ImageDraw.Draw(im)
    dark = (20, 23, 37)
    steel = (85, 98, 119)
    pale = tuple(min(255, v + 72) for v in color)
    d.ellipse((9, 5, 37, 34), fill=dark, outline=color, width=3)
    d.polygon((12, 25, 35, 25, 41, 42, 6, 42), fill=steel, outline=dark)
    d.rectangle((14, 14, 22, 18), fill=pale)
    d.rectangle((26, 14, 34, 18), fill=pale)
    d.rectangle((8, 38, 17, 46), fill=dark, outline=color)
    d.rectangle((30, 38, 39, 46), fill=dark, outline=color)
    if mode == 'scatter_raider':
        for y in (24, 28, 32):
            d.rectangle((28, y, 47, y + 3), fill=color, outline=dark)
        d.rectangle((25, 25, 29, 36), fill=pale)
    elif mode == 'beam_raider':
        d.polygon((29, 23, 46, 18, 47, 37, 29, 34), fill=dark, outline=color)
        d.ellipse((37, 24, 45, 32), fill=pale)
        d.line((22, 6, 24, 1, 28, 7), fill=color, width=3)
    else:
        d.rectangle((26, 26, 46, 31), fill=dark, outline=color)
        d.rectangle((34, 22, 38, 27), fill=pale)
        d.line((42, 23, 47, 23), fill=pale, width=2)
    return im


def main():
    for row in W._V25:
        key = row[0]
        weapon_icon(key, W.get(key)).save(ASSETS / f'wpn_{key}.png', optimize=True)
    for key, color in (
        ('scatter_raider', (223, 161, 112)),
        ('beam_raider', (174, 132, 239)),
        ('rifle_raider', (139, 218, 224)),
    ):
        armed_enemy(key, color).save(ASSETS / f'spr_enemy_{key}.png', optimize=True)
    print('2.5 art: 14 weapon models and 3 armed enemy models')


if __name__ == '__main__':
    main()
