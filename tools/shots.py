# -*- coding: utf-8 -*-
"""
从无头模式导出各场景实际画面，用于人工核验渲染效果。
输出到 _tmp/shots/*.png，并合成一张联络表 _tmp/shots/contact.png
"""
import math
import os
import sys

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'src'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))

import pygame                                        # noqa: E402
from sk import settings as S                          # noqa: E402
from sk import utils as U                             # noqa: E402
from sk import weapon as W                            # noqa: E402
from sk.game import Game                              # noqa: E402
from sk.dungeon import Dungeon                        # noqa: E402
from sk.pickup import Pickup, Prop                    # noqa: E402
from selftest import bot_input, run_until             # noqa: E402

OUT = os.path.join(ROOT, '_tmp', 'shots')
SCALE = 2
SHOTS = []


def shot(game, name):
    game.player.iframes = 0.0
    game.draw()
    img = pygame.transform.scale(game.canvas,
                                 (S.VIEW_W * SCALE, S.VIEW_H * SCALE))
    path = os.path.join(OUT, f'{len(SHOTS):02d}_{name}.png')
    pygame.image.save(img, path)
    SHOTS.append((name, path))
    print('  ->', os.path.basename(path))


def contact_sheet():
    from PIL import Image, ImageDraw
    th_w = S.VIEW_W * SCALE
    th_h = S.VIEW_H * SCALE
    cols = 2
    rows = (len(SHOTS) + cols - 1) // cols
    sw, sh = th_w // 2, th_h // 2
    canvas = Image.new('RGB', (cols * sw, rows * (sh + 18)), (24, 23, 30))
    d = ImageDraw.Draw(canvas)
    for i, (nm, p) in enumerate(SHOTS):
        im = Image.open(p).convert('RGB').resize((sw, sh), Image.LANCZOS)
        x, y = (i % cols) * sw, (i // cols) * (sh + 18)
        canvas.paste(im, (x, y + 18))
        d.text((x + 4, y + 4), f'{i}:{nm}', fill=(255, 220, 120))
    canvas.save(os.path.join(OUT, 'contact.png'))
    print('联络表 ->', os.path.join(OUT, 'contact.png'), canvas.size)


def main():
    os.makedirs(OUT, exist_ok=True)
    g = Game(headless=True, seed=2024, enable_audio=False)

    # 1) 标题
    g.state = 'title'
    g.best_floor, g.best_kills = 3, 142
    g.draw()
    shot(g, 'title')
    g.state = 'help'
    g.draw()
    shot(g, 'help')

    # 2) 出生房
    g.start_run()
    for _ in range(30):
        g.step(1 / 60.0, {'mx': 0, 'my': 0, 'aim': 0.6, 'shoot': False,
                          'dash': False, 'slow': False})
    shot(g, 'start_room')

    # 3) 战斗房（打到一半）
    d = g.dungeon
    tgt = None
    for c, r in d.rooms.items():
        if r.kind == 'normal':
            tgt = c
            break
    if tgt:
        g.enter_room(tgt[0], tgt[1], None)
        for i in range(150):
            g.player.iframes = 9
            g.step(1 / 60.0, bot_input(g))
        shot(g, 'combat')
        # 打碎木箱的瞬间
        if not g.room.props:
            g.room.props.append(Prop(g.player.x + 60, g.player.y - 30, 'crate'))
        g.player.wkey = 'shotgun'
        for i in range(26):
            g.player.iframes = 9
            g.player.cool = 0
            g.player.energy = 100
            a = bot_input(g)
            a['aim'] = math.atan2(-30, 60)
            g.step(1 / 60.0, a)
        shot(g, 'breaking_prop')

    # 4) BOSS 战
    g.state = 'playing'
    g.floor = 2
    g.dungeon = Dungeon(2, g.rng)
    bk = g.dungeon.boss_key
    g.enter_room(bk[0], bk[1], None)
    g.player.wkey = 'smg'
    got = False
    for i in range(4000):
        g.player.iframes = 9
        g.player.energy = 100
        b = g.boss
        if b is not None and b.state in ('ring', 'spread', 'sweep') and len(g.bullets) > 30:
            shot(g, 'boss_bullets')
            got = True
            break
        g.step(1 / 60.0, bot_input(g))
    if not got:
        shot(g, 'boss_bullets')
    # 移动到玩家附近再截一张
    for i in range(60):
        g.player.iframes = 9
        g.player.energy = 100
        g.step(1 / 60.0, bot_input(g))
    shot(g, 'boss_fight')

    # 5) 宝箱房 + 交互提示
    g.state = 'playing'
    g.floor = 1
    g.dungeon = Dungeon(1, g.rng)
    tk = None
    for c, r in g.dungeon.rooms.items():
        if r.kind == 'treasure':
            tk = c
            break
    if tk:
        g.enter_room(tk[0], tk[1], None)
        r = g.room
        r.pickups.clear()
        r.pickups.append(Pickup(g.player.x + 22, g.player.y, 'chest'))
        for _ in range(20):
            g.step(1 / 60.0, {'mx': 0, 'my': 0, 'aim': 0, 'shoot': False,
                              'dash': False, 'slow': False})
        shot(g, 'treasure_prompt')
        g.request_interact()
        for _ in range(12):
            g.step(1 / 60.0, {'mx': 0, 'my': 0, 'aim': 0, 'shoot': False,
                              'dash': False, 'slow': False})
        shot(g, 'chest_opened')

    # 6) 商店房
    g.state = 'playing'
    g.dungeon = Dungeon(1, g.rng)
    sk = None
    for c, r in g.dungeon.rooms.items():
        if r.kind == 'shop':
            sk = c
            break
    if sk:
        g.enter_room(sk[0], sk[1], None)
        g.coins = 260
        g.player.x, g.player.y = S.ROOM_CX - 30, S.ROOM_CY + 30
        for _ in range(20):
            g.step(1 / 60.0, {'mx': 0, 'my': 0, 'aim': -1.2, 'shoot': False,
                              'dash': False, 'slow': False})
        shot(g, 'shop')

    # 7) 暂停 / 结算 / 通关
    g.state = 'paused'
    g.draw()
    shot(g, 'paused')

    g.state = 'playing'
    g.kills, g.coins = 87, 342
    g.player.shots = 512
    g.player.dmg_taken = 26
    g.floor = 2
    g.state = 'gameover'
    g.draw()
    shot(g, 'gameover')

    g.floor = 3
    g.total_time = 428
    g.state = 'victory'
    g.draw()
    shot(g, 'victory')

    g.state = 'levelclear'
    g.draw()
    shot(g, 'levelclear')

    # 8) 1.x 新增界面：客厅三分页 / 展示台 / 天赋三选一 / 过场
    g.state = 'lobby'
    for tab in range(3):
        g.lobby_tab = tab
        g.draw()
        shot(g, 'lobby_tab%d' % tab)
    g.lobby_tab = 0
    g.lobby_expand = True
    g.draw()
    shot(g, 'lobby_expand')
    g.lobby_expand = False
    # 副本站位（条件清单最长的情况）
    try:
        from sk import progress as PR                      # noqa: E402
        order = PR.scene_order(g.profile)
        for i, k in enumerate(order):
            if k in ('dun_hive', 'dun_furnace'):
                g.lobby_index = i
                g.lobby_expand = True
                g.draw()
                shot(g, 'lobby_' + k)
        g.lobby_expand = False
    except Exception as e:
        print('  跳过副本页:', e)

    try:
        from sk import codex as CX                         # noqa: E402
        g.pending_talents = list(CX.TALENT_ORDER[:3])
        g.talent_pick = 0
        g.state = 'talent'
        g.draw()
        shot(g, 'talent')
    except Exception as e:
        print('  跳过天赋页:', e)

    g.story_lines = ['……这是今天的第三百七十四条观测记录。',
                     '地表的污染浓度又升了 3.7%。',
                     '我们还剩最后三台净化器。',
                     '如果这个月再补不上滤芯，就得放弃地面站。']
    g.story_page = 0
    g.story_t = 1.0
    g.story_title = '记录 · 第 1 天'
    g.story_phase = 'stage_enter'
    g.state = 'story'
    g.draw()
    shot(g, 'story')

    contact_sheet()
    print('共导出', len(SHOTS), '张')


if __name__ == '__main__':
    main()
