"""2.3 独立武器、补给和饮料图标。仅写入对应新素材。"""
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'assets'


def blade(key, color):
    im = Image.new('RGBA', (32, 32))
    d = ImageDraw.Draw(im)
    dark = (21, 25, 37)
    steel = (91, 105, 128)
    light = tuple(min(255, int(v + (255 - v) * .65)) for v in color)
    if key == 'scrap_saber':
        d.line((5, 27, 15, 17), fill=steel, width=5)
        d.polygon((13, 18, 22, 4, 28, 3, 24, 14, 17, 21), fill=color, outline=dark)
        d.line((20, 8, 23, 15), fill=light, width=2)
    elif key == 'vine_sickle':
        d.line((7, 28, 20, 8), fill=steel, width=4)
        d.arc((8, 0, 31, 23), 225, 50, fill=color, width=5)
        d.arc((11, 2, 29, 20), 215, 40, fill=light, width=2)
        d.ellipse((4, 24, 9, 29), fill=color)
    elif key == 'glacier_fang':
        d.polygon((14, 27, 18, 27, 19, 13, 16, 4, 13, 15), fill=color, outline=dark)
        d.polygon((16, 3, 22, 12, 17, 10), fill=light)
        d.line((8, 20, 25, 20), fill=steel, width=3)
        d.line((16, 21, 16, 30), fill=steel, width=4)
    elif key == 'thunder_axe':
        d.line((6, 28, 23, 7), fill=steel, width=5)
        d.polygon((12, 8, 24, 3, 29, 8, 25, 19, 17, 20), fill=color, outline=dark)
        d.line((18, 10, 25, 11, 20, 17), fill=light, width=2)
    else:
        d.line((5, 29, 17, 17), fill=steel, width=6)
        d.polygon((13, 18, 17, 5, 29, 1, 25, 17, 18, 24), fill=color, outline=dark)
        d.polygon((22, 4, 27, 2, 24, 15, 20, 18), fill=light)
        d.ellipse((24, 3, 30, 9), outline=light, width=2)
    d.ellipse((5, 24, 10, 29), fill=dark, outline=light)
    return im


def bottle(color, symbol, shape='bottle'):
    im = Image.new('RGBA', (32, 32))
    d = ImageDraw.Draw(im)
    dark = (24, 27, 42)
    if shape == 'can':
        d.rounded_rectangle((8, 6, 24, 28), 3, fill=color, outline=dark, width=2)
        d.rectangle((9, 5, 23, 8), fill=(208, 219, 226), outline=dark)
        d.line((12, 12, 20, 20, 12, 20), fill=(255, 250, 210), width=2)
    else:
        d.rectangle((12, 2, 20, 8), fill=(219, 223, 230), outline=dark)
        d.rectangle((11, 8, 21, 11), fill=color, outline=dark)
        d.rounded_rectangle((6, 11, 26, 29), 5, fill=color, outline=dark, width=2)
        d.ellipse((10, 14, 22, 26), fill=(235, 241, 247), outline=dark)
        if symbol == '+':
            d.line((16, 16, 16, 24), fill=color, width=3)
            d.line((12, 20, 20, 20), fill=color, width=3)
        elif symbol == '~':
            d.arc((11, 17, 20, 24), 180, 360, fill=color, width=2)
            d.arc((11, 15, 20, 22), 0, 180, fill=color, width=2)
        else:
            d.text((12, 14), symbol, fill=color)
    return im


def basketball():
    im = Image.new('RGBA', (32, 32))
    d = ImageDraw.Draw(im)
    d.ellipse((3, 3, 29, 29), fill=(231, 123, 38), outline=(31, 26, 29), width=2)
    d.arc((6, 3, 26, 29), 55, 305, fill=(54, 34, 29), width=2)
    d.arc((3, 7, 29, 25), 215, 500, fill=(54, 34, 29), width=2)
    d.line((4, 16, 28, 16), fill=(54, 34, 29), width=2)
    d.arc((6, 6, 21, 21), 185, 280, fill=(255, 190, 95), width=2)
    return im


def main():
    colors = {
        'scrap_saber': (205, 218, 225), 'vine_sickle': (132, 237, 150),
        'glacier_fang': (120, 212, 255), 'thunder_axe': (194, 150, 255),
        'solar_cleaver': (255, 206, 92),
    }
    for key, col in colors.items():
        blade(key, col).save(OUT / f'wpn_{key}.png', optimize=True)
    for key, col, sym, shape in (
        ('potion_health', (229, 76, 95), '+', 'bottle'),
        ('potion_energy', (76, 176, 239), '~', 'bottle'),
        ('drink_nectar', (255, 208, 96), '★', 'bottle'),
        ('drink_dew', (133, 221, 252), '◇', 'bottle'),
        ('drink_soda', (150, 220, 133), 'S', 'can'),
        ('drink_tea', (181, 94, 61), 'T', 'can'),
    ):
        bottle(col, sym, shape).save(OUT / f'spr_{key}.png', optimize=True)
    basketball().save(OUT / 'spr_basketball.png', optimize=True)
    print('2.3 art: 5 melee weapons, 2 potions, 4 drinks, basketball')


if __name__ == '__main__':
    main()
