"""Create a compact sprite contact sheet for visual review."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.sk import weapon, gamedata, codex  # noqa: E402

groups = [
    ('50 WEAPONS', [(k, f'wpn_{k}.png') for k in weapon.ORDER]),
    ('6 HEROES', [(k, f'spr_player_{k}.png') for k in gamedata.CHAR_ORDER]),
    ('43 MONSTERS', [(k, f'spr_enemy_{k}.png') for k in codex.ENEMY_ORDER]),
    ('10 COLLECTIBLES', [(k, f'spr_collect_{k}.png') for k in codex.COLLECT_ORDER]),
    ('10 CHESTS', [(f'{k}_{t}', f'spr_chest_{k}_{t}.png')
                   for k in gamedata.CHESTS for t in ('normal', 'superb')]),
    ('5 TRAPS', [(k, f'spr_trap_{k}.png') for k in
                 ('spike', 'poison', 'shock', 'slow', 'flame')]),
]
cell_w, cell_h, cols = 112, 92, 8
height = sum(34 + ((len(items) + cols - 1) // cols) * cell_h for _, items in groups)
out = Image.new('RGB', (cell_w * cols, height), (13, 17, 31))
d = ImageDraw.Draw(out)
y = 0
for title, items in groups:
    d.rectangle((0, y, out.width, y + 28), fill=(30, 39, 66))
    d.text((12, y + 7), title, fill=(195, 234, 249))
    y += 34
    for n, (name, filename) in enumerate(items):
        x = (n % cols) * cell_w
        yy = y + (n // cols) * cell_h
        d.rectangle((x + 4, yy + 3, x + cell_w - 4, yy + cell_h - 4),
                    fill=(27, 31, 48), outline=(54, 73, 99))
        with Image.open(ROOT / 'assets' / filename) as src:
            pic = src.convert('RGBA')
            pic.thumbnail((56, 56), Image.Resampling.NEAREST)
            out.paste(pic, (x + (cell_w - pic.width) // 2, yy + 7), pic)
        d.text((x + 5, yy + 66), name[:17], fill=(186, 190, 209))
    y += ((len(items) + cols - 1) // cols) * cell_h
dest = ROOT.parent / '版本2.1' / '预览-图鉴.png'
dest.parent.mkdir(parents=True, exist_ok=True)
out.save(dest, optimize=True)
print(dest)
