# -*- coding: utf-8 -*-
"""把网页版打包成「单文件 HTML」。

做法：
  web_src/shell.html  +  web_src/data.js  +  web_src/game.js
                      +  assets/*.png(base64)  ->  web/index.html

产物是**完全自包含**的单文件：双击即可离线游玩，不依赖网络、不依赖本地服务器、
不需要任何外部目录。贴图全部以 data URI 内嵌，音效用 WebAudio 现场合成。

用法：
    python tools/gen_data_js.py   # 先把 Python 数据层导出（改动数据后）
    python tools/build_web.py
"""
import base64
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHELL = os.path.join(ROOT, 'web_src', 'shell.html')
GAME_JS = os.path.join(ROOT, 'web_src', 'game.js')
DATA_JS = os.path.join(ROOT, 'web_src', 'data.js')
TOUCH_JS = os.path.join(ROOT, 'web_src', 'touch.js')
NATIVE_STORAGE_JS = os.path.join(ROOT, 'web_src', 'native_storage.js')
ASSETS = os.path.join(ROOT, 'assets')
OUT = os.path.join(ROOT, 'web', 'index.html')

# 需要内嵌的贴图（键名与 game.js 的 IMG_MANIFEST 一一对应）
WANTED = [
    'spr_player.png',
    'spr_enemy_slime.png', 'spr_enemy_bomber.png', 'spr_enemy_drone.png',
    'spr_boss.png',
    'spr_crate.png', 'spr_barrel.png', 'spr_coin.png', 'spr_diamond.png',
    'spr_heart.png',
    'spr_cover_pillar.png', 'spr_cover_block.png',
    'spr_energy.png', 'spr_key.png', 'spr_chest.png', 'spr_potion.png',
    'spr_potion_health.png', 'spr_potion_energy.png',
    'spr_drink_nectar.png', 'spr_drink_dew.png',
    'spr_drink_soda.png', 'spr_drink_tea.png', 'spr_basketball.png',
    'wpn_pistol.png', 'wpn_shotgun.png', 'wpn_smg.png',
    'wpn_laser.png', 'wpn_rocket.png', 'wpn_cannon.png',
    'bul_bullet.png', 'bul_bolt.png', 'bul_plasma.png',
    'bul_laser.png', 'bul_rocket.png', 'bul_hex.png',
    'tile_floor.png', 'tile_floor_alt.png',
    'tile_wall.png', 'tile_wall_top.png', 'tile_door.png',
    'bg_title.png',
    'sfx/man_what_can_i_say.wav',
]

# 2.0: gameplay assets follow the same Python tables exported to data.js.
sys.path.insert(0, ROOT)
from src.sk import weapon as _W, gamedata as _G, codex as _X  # noqa: E402
WANTED.extend('wpn_' + key + '.png' for key in _W.ORDER)
WANTED.extend('spr_player_' + key + '.png' for key in _G.CHAR_ORDER)
WANTED.extend('spr_material_' + key + '.png' for key in _G.MAT_ORDER)
WANTED.extend('spr_enemy_' + key + '.png' for key in _X.ENEMY_ORDER)
WANTED.extend('spr_collect_' + key + '.png' for key in _X.COLLECT_ORDER)
WANTED.extend('spr_chest_' + kind + '_' + tier + '.png'
              for kind in _G.CHESTS for tier in ('normal', 'superb'))
WANTED.extend('spr_trap_' + kind + '.png'
              for kind in ('spike', 'poison', 'shock', 'slow', 'flame'))
WANTED.extend('tile_' + part + '_' + scene + '.png'
              for scene in ('crust', 'sewer', 'facility', 'core', 'd_mine', 'd_lab', 'd_gift')
              for part in ('floor', 'floor_alt', 'wall', 'wall_top'))
WANTED = list(dict.fromkeys(WANTED))


def read(path, mode='r'):
    with open(path, mode, **({} if 'b' in mode else {'encoding': 'utf-8'})) as f:
        return f.read()


def build():
    missing = []
    entries = []
    for fn in WANTED:
        p = os.path.join(ASSETS, fn)
        if not os.path.isfile(p):
            missing.append(fn)
            continue
        with open(p, 'rb') as f:
            b64 = base64.b64encode(f.read()).decode('ascii')
        entries.append('"%s":"%s"' % (fn, b64))

    assets_js = 'window.__ASSETS__={' + ','.join(entries) + '};'
    game_js = read(GAME_JS, 'rb').decode('utf-8')
    shell = read(SHELL, 'rb').decode('utf-8')
    if not os.path.isfile(DATA_JS):
        raise SystemExit('缺少 web_src/data.js，请先运行 python tools/gen_data_js.py')
    data_js = read(DATA_JS, 'rb').decode('utf-8')
    touch_js = read(TOUCH_JS, 'rb').decode('utf-8') if os.path.isfile(TOUCH_JS) else ''
    native_storage_js = read(NATIVE_STORAGE_JS, 'rb').decode('utf-8')

    if '/*__ASSETS__*/' not in shell or '/*__GAME__*/' not in shell:
        raise SystemExit('shell.html 缺少 /*__ASSETS__*/ 或 /*__GAME__*/ 占位符')
    if '/*__DATA__*/' not in shell:
        raise SystemExit('shell.html 缺少 /*__DATA__*/ 占位符')
    if '/*__TOUCH__*/' not in shell:
        raise SystemExit('shell.html 缺少 /*__TOUCH__*/ 占位符')

    html = shell.replace('/*__ASSETS__*/', assets_js)
    html = html.replace('/*__DATA__*/', data_js)
    html = html.replace('/*__NATIVE_STORAGE__*/', native_storage_js)
    html = html.replace('/*__GAME__*/', game_js)
    html = html.replace('/*__TOUCH__*/', touch_js)

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', encoding='utf-8', newline='\n') as f:
        f.write(html)

    manifest_path = os.path.join(os.path.dirname(OUT), 'manifest.webmanifest')
    manifest = {
        'name': '余烬禁区',
        'short_name': '余烬禁区',
        'start_url': './index.html',
        'display': 'fullscreen',
        'orientation': 'landscape',
        'background_color': '#0a0910',
        'theme_color': '#0a0910',
    }
    with open(manifest_path, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    n = os.path.getsize(OUT)
    print(f'已生成 {os.path.relpath(OUT, ROOT)}')
    print(f'已生成 {os.path.relpath(manifest_path, ROOT)}')
    print(f'  内嵌贴图 {len(entries)}/{len(WANTED)} 张，'
          f'体积 {n / 1024:.0f} KB（{n / 1024 / 1024:.2f} MB）')
    if missing:
        print(f'  [警告] 缺失贴图：{missing}（游戏会用占位图继续运行）')
    # 粗校验：确认占位符都替换掉了
    for bad in ('/*__ASSETS__*/', '/*__GAME__*/', '/*__DATA__*/', '/*__TOUCH__*/'):
        if bad in html:
            print(f'  [错误] 占位符 {bad} 未被替换')
            return 1
    return 0


if __name__ == '__main__':
    sys.exit(build())
