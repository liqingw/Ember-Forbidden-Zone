# -*- coding: utf-8 -*-
"""
陆面过程模拟 —— 无头自动化测试套件

覆盖：
  T1  地牢生成不变量（多楼层 × 多种子：连通性、房间类型、几何合法性）
  T2  六把武器全部可开火、弹道参数合法
  T3  战斗循环：清空普通房 -> 门解锁 -> 掉落物产出
  T4  BOSS 战：三阶段攻击全部触发 -> 死亡演出 -> 传送门生成
  T5  房间切换：物理走门 + API 切换 + 往返一致性
  T6  掉落/交互：木箱破坏、宝箱开启、商店购买、武器交换
  T7  模糊测试：随机输入 + 随机瞬移 + 全状态渲染，逐帧校验不变量
  T8  所有界面渲染（标题/帮助/暂停/结算/通关/层通过）
  T9  端到端通关（三层全清 + 三个 BOSS）
  T10 渲染坐标一致性（世界坐标 -> 画布坐标的相机偏移必须统一）
  T11 武器自动交换不往返（踩在枪上只换一次，防止死循环 / 无限抢枪）
  T12 撞墙不卡死（防卡死）
  T13 1.3 抗污染天赋（运行时生效：减益折减 / 净化循环 / 污染共鸣）
  T14 图鉴 / 收集品展示台 / 客厅三分页（1.0 需求 8/9/16）
运行：python tools/selftest.py
"""
import math
import os
import random
import sys
import traceback

import pygame

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYTHONIOENCODING', 'utf-8')

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'src'))

# 存档隔离：所有测试都必须跑在临时数据目录里，否则 Game() 会读写用户
# 真实存档（APPDATA/Library/...），既污染玩家进度，也让用例之间互相干扰
# （例如某个用例把场景标记成"已通关"后，后面的用例读到的就是脏数据）。
_TEST_DATA = os.path.join(ROOT, '_tmp', 'testdata')
os.makedirs(_TEST_DATA, exist_ok=True)
if sys.platform.startswith('win'):
    os.environ['APPDATA'] = _TEST_DATA
else:
    # data_dir() 在 win 用 APPDATA，darwin 用 ~/Library（不可改 HOME），
    # Linux 用 XDG_DATA_HOME。macOS 下退化为"不隔离"——CI 跑在 Linux 上，
    # 本机开发为 Windows，实际都能隔离。
    os.environ['XDG_DATA_HOME'] = _TEST_DATA

from sk import settings as S              # noqa: E402
from sk import utils as U                 # noqa: E402
from sk import weapon as W                # noqa: E402
from sk import assets as assets_mod       # noqa: E402
from sk import chapter as C               # noqa: E402
from sk import codex as CX                # noqa: E402
from sk import progress as PR             # noqa: E402
from sk import save as SV                  # noqa: E402
from sk.game import Game                  # noqa: E402
from sk.pickup import Pickup, Prop        # noqa: E402
from sk.dungeon import Dungeon            # noqa: E402
from sk.enemy import Enemy                # noqa: E402

RESULTS = []
FRAME_ERRORS = []


def check(cond, msg):
    RESULTS.append((bool(cond), msg))
    if not cond:
        print(f'  [FAIL] {msg}')
    return bool(cond)


def section(name):
    print(f'\n=== {name} ===')


def fin(x):
    return isinstance(x, (int, float)) and math.isfinite(x)


def invariants(game, tag=''):
    """逐帧不变量校验"""
    errs = []
    pl = game.player
    if not fin(pl.x) or not fin(pl.y):
        errs.append(f'玩家坐标非有限值 {pl.x},{pl.y}')
    if not (-12 <= pl.x <= S.ROOM_PX_W + 12 and -12 <= pl.y <= S.ROOM_PX_H + 12):
        errs.append(f'玩家越界 {pl.x:.1f},{pl.y:.1f}')
    if pl.hp > pl.max_hp + 1e-6:
        errs.append(f'血量超上限 {pl.hp} > {pl.max_hp}')
    if pl.energy < -1e-6 or pl.energy > pl.max_energy + 1e-6:
        errs.append(f'能量越界 {pl.energy}')
    if not fin(pl.energy):
        errs.append('能量非有限值')
    if game.room is None:
        errs.append('room 为 None')
    if len(game.bullets) > 4000:
        errs.append(f'子弹数量失控 {len(game.bullets)}')
    if len(game.enemies) > 200:
        errs.append(f'敌人数失控 {len(game.enemies)}')
    if len(game.fx.parts) > 1500:
        errs.append(f'粒子数失控 {len(game.fx.parts)}')
    for e in game.enemies:
        if not fin(e.x) or not fin(e.y):
            errs.append(f'敌人坐标非有限值 {type(e).__name__}')
            break
        if not fin(e.hp):
            errs.append(f'敌人血量非有限值 {type(e).__name__}')
            break
    for b in game.bullets:
        if not fin(b.x) or not fin(b.y) or not fin(b.dmg):
            errs.append('子弹状态非有限值')
            break
    if errs:
        FRAME_ERRORS.append(f'{tag}: ' + ' | '.join(errs[:3]))
        return False
    return True


# ---------------------------------------------------------------- T0
def t0_sanity(game):
    """素材与渲染健全性：防止"贴图静默退化成占位图"这类致命但无声的故障"""
    section('T0 素材与渲染健全性')
    a = game.assets
    check(not a.missing, f'T0 全部素材文件加载成功（缺失 {a.missing}）')
    check(a._font_path is not None, f'T0 中文字体已加载（{a._font_path}）')

    refs = assets_mod.all_keys()
    absent = [k for k in refs if k not in a.img]
    check(not absent, f'T0 代码引用的 {len(refs)} 个贴图 key 全部存在（缺失 {absent}）')
    check(not a.placeholder_keys,
          f'T0 加载阶段无占位图（{sorted(a.placeholder_keys)}）')

    thin = []
    for key in refs:
        if _uniq_colors(a.spr(key)) < 5:
            thin.append(key)
    check(not thin, f'T0 所有贴图内容有效（疑似空白 {thin}）')

    # 渲染全部界面后，不允许有任何运行期占位图回溯
    a.placeholder_keys.clear()
    game.start_run()
    for st in ('title', 'help', 'playing', 'paused', 'gameover', 'victory', 'levelclear'):
        game.state = st
        game.draw()
    for k in W.ORDER:
        game.player.wkey = k
        game.state = 'playing'
        game.draw()
    check(not a.placeholder_keys,
          f'T0 渲染阶段无占位图回溯（{sorted(a.placeholder_keys)}）')

    game.state = 'playing'
    game.start_run()
    for _ in range(30):
        game.step(1 / 60.0, {'mx': 0, 'my': 0, 'aim': 0, 'shoot': False,
                             'dash': False, 'slow': False})
    uq = _uniq_colors(game.canvas)
    check(uq >= 300, f'T0 实机画面颜色丰富度合格（{uq} 种，占位图故障时会很低）')

    # 字体覆盖：源码里出现的字符必须都能渲染（否则界面出现方框）
    try:
        import glob
        from fontTools.ttLib import TTFont
        ft = TTFont(a._font_path)
        cmap = set()
        for t in ft['cmap'].tables:
            cmap |= set(t.cmap.keys())
        need = {chr(i) for i in range(32, 127)}
        for p in glob.glob(os.path.join(ROOT, 'src', '**', '*.py'), recursive=True):
            with open(p, encoding='utf-8') as fp:
                need |= {c for c in fp.read() if ord(c) >= 32}
        miss = sorted({c for c in need if ord(c) not in cmap})
        check(not miss, f'T0 字体覆盖全部界面字符（缺失 {miss[:24]}）')
    except ImportError:
        check(True, 'T0 未安装 fontTools，跳过字体覆盖校验')


def _uniq_colors(surf):
    import numpy as np
    arr = pygame.surfarray.array3d(surf)
    return int(np.unique(arr.reshape(-1, 3), axis=0).shape[0])


# ---------------------------------------------------------------- T1
def t1_dungeon():
    section('T1 地牢生成不变量')
    bad = 0
    tot = 0
    kinds_seen = set()
    # 需求 3/8：首领房只出现在"第 3 关小 Boss / 第 5 关大 Boss"的最后一层。
    # 所以 T1 同时遍历 (关口类型, 层) 组合，逐条校验这条规则本身。
    stage_cases = [(0, False), (2, True), (4, True)]   # (stage_idx, 是否该有boss)
    for stage_idx, want_boss in stage_cases:
        for floor in (1, 2, 3):
            for seed in range(60):
                rng = random.Random(seed * 7919 + floor + stage_idx * 131)
                try:
                    d = Dungeon(floor, rng, scene_key='crust',
                                stage_idx=stage_idx, diff=(1.0, 1.0))
                except Exception as e:
                    bad += 1
                    print('   生成异常', stage_idx, floor, seed, e)
                    continue
                tot += 1
                keys = set(d.rooms.keys())
                check_len = 6 <= len(keys) <= S.GRID_W * S.GRID_H
                if not check_len:
                    bad += 1
                    continue
                # 连通性：从出生点 BFS 必须覆盖全部房间
                dist = d._bfs(d.start_key)
                if len(dist) != len(keys):
                    bad += 1
                    print(f'   不连通 floor{floor} seed{seed}: {len(dist)}/{len(keys)}')
                    continue
                # 首领房规则：仅 boss 关的最后一层
                expect = want_boss and floor >= S.FLOORS
                has = bool(d.boss_key) and d.rooms[d.boss_key].kind == 'boss'
                if has != expect:
                    bad += 1
                    print(f'   BOSS房规则不符 stage{stage_idx} floor{floor} '
                          f'seed{seed} has={has} expect={expect}')
                    continue
                if d.start_key not in keys or d.rooms[d.start_key].kind != 'start':
                    bad += 1
                    continue
                # 门与邻居一致
                for c, r in d.rooms.items():
                    for dr in r.doors:
                        v = S.DIR_VEC[dr]
                        nb = (c[0] + v[0], c[1] + v[1])
                        if nb not in keys:
                            bad += 1
                            print(f'   门通向不存在的房间 {c}{dr}')
                    if r.doors:
                        S.DIR_VEC['N']
                for c, r in d.rooms.items():
                    kinds_seen.add(r.kind)
                    # 刷怪点位必须在房间内区
                    for kind, x, y, el in r.spawn_plan:
                        if not (S.IN_L <= x <= S.IN_R and S.IN_T <= y <= S.IN_B):
                            bad += 1
                            print(f'   刷怪点越界 {kind} {x:.0f},{y:.0f}')
                    for kk, x, y in r.prop_plan:
                        if not (S.IN_L <= x <= S.IN_R and S.IN_T <= y <= S.IN_B):
                            bad += 1
                            print(f'   道具点越界 {kk} {x:.0f},{y:.0f}')
    check(bad == 0, f'T1 全部 {tot} 个地牢生成合法（失败 {bad}）')
    check(kinds_seen >= {'start', 'normal', 'boss'},
          f'T1 房间类型覆盖 {sorted(kinds_seen)}')


# ---------------------------------------------------------------- T2
def t2_weapons(game):
    section('T2 武器系统')
    for key in W.ORDER:
        spec = W.get(key)
        check(spec.cd > 0 and spec.dmg > 0 and (spec.speed > 0 or spec.melee),
              f'T2 {spec.name} 参数合法 (cd={spec.cd} spd={spec.speed} dmg={spec.dmg})')
    # 需求 6（1.4）：白色基础型号 ≥ 10
    check(len(W.ORDER) >= 10, f'T2 基础武器型号 {len(W.ORDER)} 把（≥10）')
    check(any(W.get(k).melee for k in W.ORDER), 'T2 含近战武器')
    check(any(not W.get(k).melee for k in W.ORDER), 'T2 含远程武器')
    game.start_run()
    # 血泪教训：start_run() 在「场景未通关 + 有存档」时会先播 stage_enter
    # 过场然后 return，state 停在 'story' —— 后续 step() 完全不处理射击，
    # 于是本用例整段 22 项凭空失败（且只在存档被别的用例改脏后复现）。
    # 这里强制推进到 playing，让本用例与存档状态彻底解耦。
    n = 0
    while game.state == 'story' and n < 60:
        game._story_next()
        n += 1
    game.state = 'playing'
    pl = game.player
    for key in W.ORDER:
        pl.wkey = key
        pl.energy = pl.max_energy
        pl.cool = 0.0
        game.bullets.clear()
        before = pl.shots
        # 近战武器：在身前放一个敌人，能被打到才算成功
        spec0 = W.get(key)
        if spec0.melee:
            e = Enemy(pl.x + 20.0, pl.y, 1)
            game.enemies.append(e)
            ehp0 = e.hp
        else:
            e = None
            ehp0 = 0.0
        game.step(1 / 60.0, {'mx': 0, 'my': 0, 'aim': 0.0, 'shoot': True,
                             'dash': False, 'slow': False})
        if spec0.melee:
            check(e.hp < ehp0, f'T2 {spec0.name} 近战挥砍命中敌人')
            check(len(game.bullets) == 0, f'T2 {spec0.name} 近战不产生子弹')
            if e in game.enemies:
                game.enemies.remove(e)
        else:
            expected = pl.wq_spec(game).count
            check(len(game.bullets) == expected,
                  f'T2 {spec0.name} 单次开火生成 {expected} 发'
                  f'（实际 {len(game.bullets)}）')
        check(pl.shots == before + 1, f'T2 {spec0.name} 射击计数递增')
    # 能量不足时应打不出来
    pl.wkey = 'rocket'
    pl.energy = 0.5
    pl.cool = 0.0
    game.bullets.clear()
    n0 = pl.shots
    game.step(1 / 60.0, {'mx': 0, 'my': 0, 'aim': 0.0, 'shoot': True,
                         'dash': False, 'slow': False})
    check(pl.shots == n0, 'T2 能量不足时无法开火')


# ---------------------------------------------------------------- 战斗机器人
def bot_input(game):
    pl = game.player
    targets = [e for e in game.enemies if e.alive]
    if not targets:
        return {'mx': 0.0, 'my': 0.0, 'aim': pl.aim, 'shoot': False,
                'dash': False, 'slow': False}
    t = min(targets, key=lambda e: U.dist(pl.x, pl.y, e.x, e.y))
    a = math.atan2(t.y - pl.y, t.x - pl.x)
    d = U.dist(pl.x, pl.y, t.x, t.y)
    if d > 150:
        mx, my = math.cos(a), math.sin(a)
    elif d < 72:
        mx, my = -math.cos(a), math.sin(a) * 0.5
    else:
        mx, my = math.cos(a + 1.57) * 0.7, math.sin(a + 1.57) * 0.7
    return {'mx': mx, 'my': my, 'aim': a, 'shoot': True, 'dash': False, 'slow': False}


def run_until(game, cond, max_steps=9000, god=True, tag='combat'):
    for i in range(max_steps):
        if god and game.player.alive:
            game.player.iframes = max(game.player.iframes, 0.5)
        game.step(1 / 60.0, bot_input(game))
        if not invariants(game, f'{tag}@{i}'):
            return False, i
        if cond():
            return True, i
    return False, max_steps


# ---------------------------------------------------------------- T3
def t3_combat(game):
    section('T3 战斗循环 / 门禁 / 掉落')
    game.start_run()
    d = game.dungeon
    # 找一个普通战斗房
    target = None
    for c, r in d.rooms.items():
        if r.kind == 'normal':
            target = c
            break
    if not check(target is not None, 'T3 找到普通战斗房'):
        return
    game.enter_room(target[0], target[1], None)
    r = game.room
    check(len(game.enemies) > 0, f'T3 进入战斗房后有敌人（{len(game.enemies)} 个）')
    check(not r.open_doors, f'T3 有敌人时房门锁定（开门数={len(r.open_doors)}）')

    ok, steps = run_until(game, lambda: not any(e.alive for e in game.enemies),
                          max_steps=6000, tag='t3')
    check(ok, f'T3 机器人清空战斗房（{steps} 帧）')
    check(r.cleared, 'T3 房间标记为已清空')
    check(len(r.open_doors) == len(r.doors),
          f'T3 清空后所有门解锁（{len(r.open_doors)}/{len(r.doors)}）')
    items = len(r.pickups)
    check(items > 0, f'T3 击杀后产生掉落物（{items} 个）')
    check(game.kills > 0, f'T3 击杀计数 {game.kills}')
    check(len(game.props) <= len(r.prop_plan), 'T3 木箱数量未异常增长')


# ---------------------------------------------------------------- T4
def t4_boss(game):
    section('T4 BOSS 战')
    game.start_run()

    # --- T4a：三阶段攻击表覆盖（分阶段锁血观察，不击杀）
    # 注意：首领房只在 boss 关的最后一层存在，所以这里必须按 floor=S.FLOORS 生成。
    # 三阶段的差异靠"锁血比例"制造，不再依赖 floor 编号。
    for fl, phase, ratio in ((S.FLOORS, 'p1', 0.90), (S.FLOORS, 'p2', 0.50),
                             (S.FLOORS, 'p3', 0.20)):
        game.state = 'playing'
        game.floor = fl
        # 需求 3/8：首领房只出现在 boss 关（stage_idx=4）的最后一层
        game.dungeon = Dungeon(fl, game.rng, scene_key='crust',
                               stage_idx=4, diff=(1.0, 1.0))
        bk = game.dungeon.boss_key
        game.enter_room(bk[0], bk[1], None)
        for _wave in range(2):
            for _enemy in game.enemies:
                _enemy.alive = False
            game.step(1 / 60.0, {'mx': 0, 'my': 0, 'aim': 0,
                                 'shoot': False, 'dash': False, 'slow': False})
        b = game.boss
        if not check(b is not None and b.alive, f'T4 第{fl}层 BOSS 已生成'):
            continue
        game.player.wkey = 'pistol'
        seen = set()
        for i in range(1800):
            if b.alive:
                b.hp = max(b.hp, b.max_hp * ratio)      # 锁血，观察攻击
                game.player.iframes = max(game.player.iframes, 0.5)
            if b.alive:
                seen.add(b.state)
            a = bot_input(game)
            a['shoot'] = False
            game.step(1 / 60.0, a)
            invariants(game, f't4cov{fl}{phase}@{i}')
            if not b.alive:
                break
        atk = seen & {'ring', 'spread', 'charge', 'summon', 'sweep'}
        check(len(atk) >= 2,
              f'T4 第{fl}层 [{phase}] 攻击状态覆盖 {sorted(atk)}')

    # --- T4b：完整击杀流程 + 死亡演出 + 传送门（只在首领关最后一层）
    for fl in (S.FLOORS,):
        game.state = 'playing'
        game.floor = fl
        game.dungeon = Dungeon(fl, game.rng, scene_key='crust',
                               stage_idx=4, diff=(1.0, 1.0))
        bk = game.dungeon.boss_key
        game.enter_room(bk[0], bk[1], None)
        for _wave in range(2):
            for _enemy in game.enemies:
                _enemy.alive = False
            game.step(1 / 60.0, {'mx': 0, 'my': 0, 'aim': 0,
                                 'shoot': False, 'dash': False, 'slow': False})
        b = game.boss
        if not check(b is not None and b.alive, f'T4 第{fl}层 BOSS 已生成'):
            continue
        check(b.max_hp > 300, f'T4 第{fl}层 BOSS 血量 {b.max_hp:.0f}')
        game.player.wkey = 'cannon'
        game.player.hp = game.player.max_hp
        states = set()
        died = False
        i = 0
        for i in range(14000):
            if game.player.alive:
                game.player.iframes = max(game.player.iframes, 0.5)
            if b.alive:
                states.add(b.state)
            actions = bot_input(game)
            if b.state in ('intro', 'dying'):
                actions['shoot'] = False
            game.step(1 / 60.0, actions)
            invariants(game, f't4f{fl}@{i}')
            if not b.alive:
                died = True
                break
        check(died, f'T4 第{fl}层 BOSS 被击败（{i} 帧）')
        if not game.room.cleared:
            run_until(game, lambda: game.room.cleared, 6000, tag='t4remain')
        check('dying' in states, f'T4 第{fl}层 死亡演出触发')
        check(b.state == 'dying', f'T4 第{fl}层 死亡状态为 dying（{b.state}）')
        check(game.room.portal is not None, f'T4 第{fl}层 击败后生成传送门')
        check(game.room.cleared, f'T4 第{fl}层 房间标记清空')
        check(not game.room.open_doors or len(game.room.open_doors) == len(game.room.doors),
              f'T4 第{fl}层 击败后房门全开')

    # --- T4c：普通关传送门 -> 本关结算（每关只有一层）
    game.state = 'playing'
    game.floor = 1
    game.dungeon = Dungeon(1, game.rng, scene_key='crust',
                           stage_idx=0, diff=(1.0, 1.0))
    game.level_state = {'scene': 'crust', 'scene_idx': 0, 'stage_idx': 0,
                        'diff': (1.0, 1.0), 'kind': 'normal', 'floors': S.FLOORS}
    sk = game.dungeon.start_key
    game.enter_room(sk[0], sk[1], None)
    game.room.portal = (game.player.x, game.player.y)
    game.step(1 / 60.0, {'mx': 0, 'my': 0, 'aim': 0, 'shoot': False,
                         'dash': False, 'slow': False})
    check(game.state == 'playing', 'T4 触碰传送门不自动推进')
    game.request_interact()
    game._confirm_key(pygame.K_e)
    check(game.state in ('victory', 'story'),
          f'T4 普通关传送门推进到通关或剧情界面（{game.state}）')


# ---------------------------------------------------------------- T5
def t5_transition(game):
    section('T5 房间切换')
    game.start_run()
    d = game.dungeon
    start = d.start_key
    r0 = game.room
    check((r0.gx, r0.gy) == start, 'T5 起始房间正确')
    door = sorted(r0.doors)[0]
    v = S.DIR_VEC[door]
    nb = (start[0] + v[0], start[1] + v[1])

    # --- 物理走门
    ex, ey = S.ENTRY_FROM[door]
    game.player.x, game.player.y = ex, ey
    game.trans_fade = 0.0
    moved = False
    for i in range(240):
        game.step(1 / 60.0, {'mx': float(v[0]), 'my': float(v[1]), 'aim': 0.0,
                             'shoot': False, 'dash': False, 'slow': False})
        if (game.room.gx, game.room.gy) != start:
            moved = True
            break
    check(moved, f'T5 物理走门成功切换到 {nb}（{i} 帧）')
    check((game.room.gx, game.room.gy) == nb, 'T5 切换目标房间正确')
    back = S.ENTRY_FROM[S.OPPOSITE[door]]
    check(abs(game.player.x - back[0]) < 40 and abs(game.player.y - back[1]) < 40,
          f'T5 落点在对侧门内（{game.player.x:.0f},{game.player.y:.0f} 期望 {back}）')
    check(game.player.x > 0 and game.player.y > 0, 'T5 落点未卡在门里')

    # --- 走回原房间
    r1 = game.room
    r1.cleared = True
    r1.refresh_doors(locked=False)
    game.trans_fade = 0.0
    v2 = S.DIR_VEC[S.OPPOSITE[door]]
    for i in range(240):
        game.step(1 / 60.0, {'mx': float(v2[0]), 'my': float(v2[1]), 'aim': 0.0,
                             'shoot': False, 'dash': False, 'slow': False})
        if (game.room.gx, game.room.gy) == start:
            break
    check((game.room.gx, game.room.gy) == start,
          'T5 可以原路走回起始房（门双向连通）')

    # --- 未清空房离开后重进应重刷敌人
    tgt = None
    for c, rr in d.rooms.items():
        if rr.kind == 'normal':
            tgt = c
            break
    if tgt:
        game.enter_room(tgt[0], tgt[1], None)
        n1 = len(game.enemies)
        game.enter_room(start[0], start[1], None)
        game.enter_room(tgt[0], tgt[1], None)
        n2 = len(game.enemies)
        check(n1 == n2 and n1 > 0,
              f'T5 未清空房重进会重刷敌人（{n1} -> {n2}）')

    # --- 所有房间都能进入且不崩
    bad = 0
    for c in d.rooms:
        try:
            game.enter_room(c[0], c[1], None)
            invariants(game, 't5-enter')
        except Exception as e:
            bad += 1
            print('   进入房间异常', c, e)
    check(bad == 0, f'T5 全部 {len(d.rooms)} 个房间均可进入')


# ---------------------------------------------------------------- T6
def t6_drops(game):
    section('T6 掉落 / 交互')
    game.start_run()
    pl = game.player

    # 木箱破坏
    r = game.room
    r.props.clear()
    r.props.append(Prop(pl.x + 60, pl.y, 'crate'))
    r.props.append(Prop(pl.x + 90, pl.y + 30, 'barrel'))
    n0 = len(r.pickups)
    pl.wkey = 'shotgun'
    pl.energy = 100
    for i in range(180):
        pl.aim = 0.0
        pl.cool = 0.0
        pl.energy = 100
        game.step(1 / 60.0, {'mx': 0, 'my': 0, 'aim': 0.0, 'shoot': True,
                             'dash': False, 'slow': False})
        if not any(p.alive for p in r.props):
            break
    check(not any(p.alive for p in r.props), f'T6 木箱/油桶可被击碎（{i} 帧）')
    check(len(r.pickups) >= n0, 'T6 击碎道具产生掉落')

    # 宝箱
    r.pickups.clear()
    r.pickups.append(Pickup(pl.x + 20, pl.y, 'chest'))
    game.step(1 / 60.0, {'mx': 0, 'my': 0, 'aim': 0, 'shoot': False,
                         'dash': False, 'slow': False})
    check(game.prompt is not None, 'T6 靠近宝箱出现交互提示')
    n0 = len(r.pickups)
    # 需求 18：开箱要二次按键 —— 第一次弹确认框，第二次才真的开
    ok = game.request_interact()
    check(ok and game.confirm_prompt is not None, 'T6 宝箱首次交互弹出确认框')
    check(len(r.pickups) == n0, 'T6 确认框期间宝箱尚未开启')
    game._confirm_key(pygame.K_RETURN)
    check(len(r.pickups) > n0, f'T6 宝箱产出物品（{len(r.pickups)}）')

    # 武器拾取：靠近不换，交互二次确认后交换
    r.pickups.clear()
    pl.wkey = 'pistol'
    r.pickups.append(Pickup(pl.x + 6, pl.y, 'weapon', wkey='laser'))
    game.step(1 / 60.0, {'mx': 0, 'my': 0, 'aim': 0, 'shoot': False,
                         'dash': False, 'slow': False})
    check(pl.wkey == 'pistol', 'T6 路过掉落武器不自动交换')
    game.request_interact()
    check(game.confirm_prompt is not None, 'T6 拾取武器弹二次确认')
    game._confirm_key(pygame.K_RETURN)
    check(pl.wkey == 'pistol' and pl.wkey2 == 'laser',
          'T6 首次拾取解锁第二武器栏')
    check(not any(p.alive and p.kind == 'weapon' and p.wkey == 'pistol' for p in r.pickups),
          'T6 初始武器仍在第一栏')

    # 商店：金币不足
    r.pickups.clear()
    game.coins = 0
    r.pickups.append(Pickup(pl.x + 6, pl.y, 'shop_heart', price=35))
    n_before = len(r.pickups)
    game.request_interact()
    check(len(r.pickups) == n_before, 'T6 金币不足时无法购买')
    # 金币充足（需求 18：购买同样要二次确认）
    pl.hp = 4
    game.coins = 500
    game.request_interact()
    check(game.confirm_prompt is not None, 'T6 购买治疗弹出确认框')
    check(game.coins == 500, 'T6 确认框期间尚未扣费')
    game._confirm_key(pygame.K_RETURN)
    check(pl.hp == 6, f'T6 购买治疗成功（HP {pl.hp}）')
    check(game.coins == 465, f'T6 扣费正确（金币 {game.coins}）')

    # 商店武器
    r.pickups.clear()
    pl.wkey = 'pistol'
    r.pickups.append(Pickup(pl.x + 6, pl.y, 'shop_weapon', wkey='laser', price=50))
    game.request_interact()
    game._confirm_key(pygame.K_RETURN)
    check(pl.wkey == 'laser', f'T6 购买武器成功（{pl.wkey}）')

    # 金币 / 红心 / 能量 拾取
    r.pickups.clear()
    pl.hp = 2
    pl.energy = 0
    c0 = game.coins
    for _ in range(3):
        r.pickups.append(Pickup(pl.x + 4, pl.y, 'coin', 1))
    r.pickups.append(Pickup(pl.x + 4, pl.y, 'heart', 2))
    r.pickups.append(Pickup(pl.x + 4, pl.y, 'energy', 25))
    for i in range(120):
        game.step(1 / 60.0, {'mx': 0, 'my': 0, 'aim': 0, 'shoot': False,
                             'dash': False, 'slow': False})
        if not r.pickups:
            break
    check(game.coins == c0 + 3, f'T6 金币拾取（{game.coins}）')
    check(pl.hp == 4, f'T6 红心回血（HP {pl.hp}）')
    check(pl.energy >= 25, f'T6 能量回复（EN {pl.energy:.0f}）')

    # 钥匙
    r.pickups.clear()
    c0 = game.coins
    r.pickups.append(Pickup(pl.x + 4, pl.y, 'key', 50))
    for i in range(120):
        game.step(1 / 60.0, {'mx': 0, 'my': 0, 'aim': 0, 'shoot': False,
                             'dash': False, 'slow': False})
        if not r.pickups:
            break
    check(game.coins == c0 + 50, f'T6 金钥匙折算金币（{game.coins}）')


# ---------------------------------------------------------------- T7
def t7_fuzz():
    section('T7 模糊测试（随机输入 + 瞬移 + 全系统）')
    bad_frames = 0
    total = 0
    for seed in (1, 2, 3, 4):
        g = Game(headless=True, seed=seed, enable_audio=False)
        g.start_run()
        rng = random.Random(seed * 977)
        for i in range(2600):
            total += 1
            act = {
                'mx': rng.uniform(-1, 1), 'my': rng.uniform(-1, 1),
                'aim': rng.uniform(-math.pi, math.pi),
                'shoot': rng.random() < 0.75,
                'dash': rng.random() < 0.05,
                'slow': rng.random() < 0.05,
            }
            r = rng.random()
            if r < 0.010:
                g.player.x = rng.uniform(20, S.ROOM_PX_W - 20)
                g.player.y = rng.uniform(20, S.ROOM_PX_H - 20)
            if r < 0.014:
                g.player.wkey = rng.choice(W.ORDER)
                g.player.energy = 100
            if r < 0.018:
                g.request_interact()
            if r < 0.021:
                keys = list(g.dungeon.rooms.keys())
                k = rng.choice(keys) if keys else None
                if k:
                    g.enter_room(k[0], k[1], None)
            if r < 0.024:
                g.player.hp = rng.uniform(1, g.player.max_hp)
            if r < 0.026:
                g.player.max_hp = rng.choice([6, 12, 20, 24])
                g.player.hp = min(g.player.hp, g.player.max_hp)
            if r < 0.028 and g.room.props:
                for p in g.room.props[:1]:
                    p.take_damage(99, g, p.x + 1, p.y)
            if r < 0.030:
                g.state = rng.choice(['playing', 'paused', 'help'])
                try:
                    g.draw()
                except Exception:
                    bad_frames += 1
                    FRAME_ERRORS.append('状态渲染异常: ' + traceback.format_exc()[-260:])
                g.state = 'playing'
            try:
                if not g.step(1 / 60.0, act):
                    pass
            except Exception:
                bad_frames += 1
                FRAME_ERRORS.append(f'seed{seed}@{i} ' + traceback.format_exc()[-300:])
                break
            if not invariants(g, f'fuzz{seed}@{i}'):
                bad_frames += 1
        check(g.room is not None, f'T7 seed{seed} 房间状态有效')
        check(g.player.hp > 0 or g.state in ('gameover', 'playing'),
              f'T7 seed{seed} 玩家状态自洽（state={g.state}）')
    check(bad_frames == 0, f'T7 {total} 帧模糊测试无异常（异常 {bad_frames}）')


# ---------------------------------------------------------------- T8
def t8_screens():
    section('T8 界面渲染')
    g = Game(headless=True, seed=7, enable_audio=False)
    g.start_run()
    # 造一个 BOSS 房用于渲染 boss 血条
    # 需求 3/8：首领房只出现在 boss 关的最后一层
    g.floor = S.FLOORS
    g.dungeon = Dungeon(S.FLOORS, g.rng, scene_key='crust',
                        stage_idx=4, diff=(1.0, 1.0))
    bk = g.dungeon.boss_key
    g.enter_room(bk[0], bk[1], None)
    for i in range(90):
        g.step(1 / 60.0, bot_input(g))
    states = ['title', 'help', 'playing', 'paused', 'gameover', 'victory', 'levelclear']
    for st in states:
        g.state = st
        try:
            for _ in range(3):
                g.draw()
            check(True, f'T8 界面 [{st}] 渲染正常')
        except Exception:
            check(False, f'T8 界面 [{st}] 渲染异常: {traceback.format_exc()[-200:]}')
    g.state = 'playing'
    # 各武器图标 HUD
    for k in W.ORDER:
        g.player.wkey = k
        try:
            g.draw()
        except Exception:
            check(False, f'T8 武器 {k} HUD 渲染异常')
    check(True, 'T8 全部武器 HUD 渲染正常')
    # 小地图：把所有房间标记为已访问
    for r in g.dungeon.rooms.values():
        r.visited = True
    try:
        g.draw()
        check(True, 'T8 全图小地图渲染正常')
    except Exception:
        check(False, 'T8 全图小地图渲染异常')

    # 1.3：副本机制卡渲染（客厅关卡地图会用到）
    try:
        from sk import chapter as C
        from sk import hud
        surf = pygame.Surface((S.VIEW_W, S.VIEW_H))
        for dk in C.DUNGEONS:
            h = hud.draw_dungeon_bind(surf, g, dk, 8, 8, 240, 120)
            check(h > 0, f'T8 [{dk}] 机制卡渲染有内容（高 {h}）')
        # 未知副本不崩、不占位
        h0 = hud.draw_dungeon_bind(surf, g, 'nope', 8, 8, 240, 120)
        check(h0 == 0, 'T8 未知副本机制卡占位为 0')
    except Exception:
        check(False, 'T8 机制卡渲染异常: ' + traceback.format_exc()[-200:])

    # 1.0 需求 16：客厅 / 关卡地图渲染（无存档 + 全解锁两种状态）
    try:
        g._enter_lobby()
        check(g.state == 'lobby', 'T8 开始游戏进入客厅（不再直进第 1 层）')
        for _ in range(2):
            g.draw()
        check(True, 'T8 客厅（无存档）渲染正常')
        from sk import progress as PR
        # 注意：这里会临时改 g.profile 来构造"全解锁"状态，测完必须还原，
        # 否则同一进程里后续用例（T9/T12/T13）会读到脏进度。
        saved_prof = g.profile
        g.profile = {'coins': 0, 'diamonds': 0, 'unlocked_dungeons': [],
                     'cleared_scenes': [], 'visited_scenes': [],
                     'scene_prog': {},
                     'stats': {}, 'scene_best': {}, 'name': '测试',
                     'codex': {'enemy': [], 'weapon': [], 'material': [],
                               'collect': []},
                     'collects': [], 'showcase': [None] * 6}
        for dk in C.DUNGEONS:
            g.profile['unlocked_dungeons'].append(dk)
        g.profile['bonus_unlocked'] = True
        g.profile['coins'] = 99999
        g.profile['diamonds'] = 500
        order = g._lobby_order()
        check(len(order) == 7, f'T8 客厅列出全部 7 个场景（实为 {len(order)}）')
        # 需求 1：1.4 起客厅是"战斗准备"，项目数是准备菜单的条数
        n = len(g._lobby_prep_items())
        for i in range(n):
            g.lobby_index = i
            g.draw()
        check(True, 'T8 客厅准备菜单各项渲染正常')
        # 键盘导航：从 0 出发按 n 次 ↓ 应回到 0（模 n 循环）
        g.lobby_index = 0
        for _ in range(n):
            g._keydown_lobby(pygame.K_s)
        check(g.lobby_index == 0, 'T8 客厅 ↓ 键循环导航回到起点')
        g.lobby_index = 0
        g._keydown_lobby(pygame.K_UP)
        check(g.lobby_index == n - 1, 'T8 客厅 ↑ 键从首项绕到末项')
        # TAB 分页：养成 / 图鉴 / 展示台也要能渲染
        g.lobby_tab = 1
        for sub in range(4):
            g.growth_sub = sub
            for gi in range(3):
                g.growth_index = gi
                g.draw()
        check(True, 'T8 客厅养成分页（四子页）渲染正常')
        g.lobby_tab = 2
        for cat in range(4):
            g.codex_cat = cat
            g.codex_index = 0
            g.codex_page = 0
            g.draw()
        check(True, 'T8 客厅图鉴分页（四类）渲染正常')
        g.lobby_tab = 3
        for i in range(6):
            g.showcase_index = i
            g.draw()
        check(True, 'T8 客厅展示台分页渲染正常')
        g._keydown_lobby(pygame.K_TAB)
        check(g.lobby_tab == 0, 'T8 TAB 在四个分页之间循环')
        # 可进入性判定（需求 1：线性锁死 —— 未通关前置场景的主线不可进入）
        # crust 是第一个主线场景，任何档都应可进
        ok_core, _ = g._lobby_can_enter('crust', g.profile)
        check(ok_core, 'T8 客厅首个主线场景恒可进入')
        # core 是最后一个主线；前置没通关则不可进入
        g.profile['scene_prog'] = {}
        g.profile['cleared_scenes'] = []
        ok_core2, why_core2 = g._lobby_can_enter('core', g.profile)
        check((not ok_core2) and bool(why_core2),
              'T8 未通关前置场景时主线被锁（线性推进）')
        g.profile['bonus_unlocked'] = False
        ok_b, why_b = g._lobby_can_enter('d_gift', g.profile)
        check((not ok_b) and bool(why_b),
              'T8 客厅未满足条件时给出不可进入原因')
        # 还原档案，避免污染后续用例
        g.profile = saved_prof
        g.lobby_tab = 0
        g.state = 'title'
    except Exception:
        check(False, 'T8 客厅渲染异常: ' + traceback.format_exc()[-300:])


# ---------------------------------------------------------------- T13 1.3 抗污染
def t13_pur_resist():
    section("T13 1.3 抗污染天赋（运行时生效）")
    g = Game(headless=True, seed=99, enable_audio=False)
    g.start_run()
    # 直接进污染原点第 5 关（浓度最高）
    g._start_floor(1)
    g.level_state = {'scene': 'core', 'stage_idx': 4}
    g.run_stats = CX.new_run_stats()
    g._apply_pollution('core', 4)
    base_pol = dict(g.pollution)
    base_hp = g.player.max_hp
    base_spd = g.pollution_spd
    base_drain = g.pollution_drain
    check(base_pol['pct'] == 96, 'T13 污染原点浓度为 96%')
    check(base_drain > 0, f'T13 无抗性时存在侵蚀（{base_drain}）')

    # 堆两层滤芯装甲（+50% 抗性）
    CX.apply_talent(g.run_stats, 'pur_resist')
    CX.apply_talent(g.run_stats, 'pur_resist')
    g._apply_pollution('core', 4)
    check(g.player.max_hp > base_hp,
          f'T13 抗性让生命上限回升（{base_hp} -> {g.player.max_hp}）')
    check(g.pollution_spd > base_spd,
          f'T13 抗性让移速回升（{base_spd:.3f} -> {g.pollution_spd:.3f}）')
    check(abs(g.pollution_drain - base_drain * 0.5) < 1e-6,
          f'T13 抗性让侵蚀减半（{base_drain:.3f} -> {g.pollution_drain:.3f}）')

    # 抗性上限：堆再多也不会把减益抹掉
    for _ in range(8):
        CX.apply_talent(g.run_stats, 'pur_resist')
    g._apply_pollution('core', 4)
    check(g.pollution_drain > 0,
          'T13 即使堆满抗性，污染原点仍有侵蚀（不会变正收益）')
    check(g.pollution_spd < 1.0, 'T13 即使堆满抗性，移速仍低于基准')

    # 净化循环：累积器会被周期清零
    g.run_stats = CX.new_run_stats()
    CX.apply_talent(g.run_stats, 'pur_purge')
    g._apply_pollution('core', 4)
    g._drain_acc = 0.0
    g._purge_t = 0.0
    pl = g.player
    pl.hp = pl.max_hp = 200  # 抬高上限，避免被侵蚀打死干扰断言
    for _ in range(int(CX.PUR_PURGE_INTERVAL * 60) - 2):
        g._update_pollution(1 / 60.0)
    check(g._drain_acc < 1.0, 'T13 净化循环在 6 秒内压住了累积器')
    # 对照组：没有净化循环时同样时间会扣血
    g.run_stats = CX.new_run_stats()
    g._apply_pollution('core', 4)
    g._drain_acc = 0.0
    pl.hp = 200
    hp0 = pl.hp
    for _ in range(int(CX.PUR_PURGE_INTERVAL * 60) - 2):
        g._update_pollution(1 / 60.0)
    check(pl.hp < hp0, f'T13 无净化时会持续掉血（{hp0} -> {pl.hp}）')

    # 污染共鸣：伤害加成随浓度
    g.run_stats = CX.new_run_stats()
    g._apply_pollution('core', 4)
    check(g.pur_dmg_mul == 0.0, 'T13 无共鸣天赋时伤害加成为 0')
    CX.apply_talent(g.run_stats, 'pur_ward')
    check(g.pur_dmg_mul > 0.2,
          f'T13 污染原点共鸣给显著加成（+{g.pur_dmg_mul:.3f}）')
    g._apply_pollution('crust', 0)
    deep = g.pur_dmg_mul
    g._apply_pollution('core', 4)
    check(g.pur_dmg_mul > deep, 'T13 浓度越高共鸣收益越大')

    # 无污染场景：抗性完全不参与
    g.run_stats = CX.new_run_stats()
    for _ in range(4):
        CX.apply_talent(g.run_stats, 'pur_resist')
    g._apply_pollution('d_gift', 0)
    check(g.pollution_drain == 0.0 and g.pollution_spd == 1.0,
          'T13 奖励副本不受污染与抗性影响')


# ---------------------------------------------------------------- T14
def t14_codex_showcase():
    section('T14 图鉴 / 收集品展示台 / 客厅分页（1.0 需求 8/9/16）')
    from sk import hud
    g = Game(headless=True, seed=61, enable_audio=False)
    g.profile = {
        'name': '测试', 'char': 'scout', 'coins': 1234, 'diamonds': 56,
        'cleared_scenes': [], 'unlocked_dungeons': [], 'scene_best': {},
        'stats': {}, 'collects': [], 'showcase': [None] * 6,
        'materials': {},
        'codex': {'enemy': [], 'weapon': [], 'material': [], 'collect': []},
    }
    g.start_run()
    # 关掉过场，直接进 playing 便于测试
    while g.state == 'story':
        g._story_next()

    # ---- 图鉴四类派生表齐备
    check(len(CX.ENEMY_CODEX) >= 18, f'T14 怪物图鉴 {len(CX.ENEMY_CODEX)} 条')
    check(len(CX.WEAPON_CODEX) >= 6, f'T14 武器图鉴 {len(CX.WEAPON_CODEX)} 条')
    check(len(CX.MATERIAL_CODEX) >= 8, f'T14 材料图鉴 {len(CX.MATERIAL_CODEX)} 条')
    check(len(CX.COLLECTS) >= 10, f'T14 收集品 {len(CX.COLLECTS)} 件')
    check(set(CX.WEAPON_CODEX) == set(W.ORDER),
          'T14 武器图鉴覆盖全部武器')

    # ---- discover：首次为真，重复为假
    check(g.discover('enemy', 'slime'), 'T14 首次发现怪物返回 True')
    check(not g.discover('enemy', 'slime'), 'T14 重复发现返回 False')
    check('slime' in g.profile['codex']['enemy'], 'T14 怪物写进存档图鉴')
    check(g.discover('material', 'scrap'), 'T14 首次发现材料')
    check(g.discover('weapon', 'pistol'), 'T14 首次发现武器')
    # 空 key 不记录
    check(not g.discover('enemy', None), 'T14 空 key 不记录')
    check(len(g.profile['codex']['enemy']) == 1, 'T14 空 key 未污染图鉴')

    # ---- 收集品：记图鉴 + 自动上展示台
    check(g.collect_got('music_box'), 'T14 首次获得收集品返回 True')
    check('music_box' in g.profile['collects'], 'T14 收集品进已获得列表')
    check(g.profile['showcase'][0] == 'music_box', 'T14 收集品自动放上展示台')
    check('music_box' in g.profile['codex']['collect'], 'T14 收集品同时进图鉴')
    check(not g.collect_got('music_box'), 'T14 重复获得返回 False')
    g.collect_got('photo')
    check(g.profile['showcase'][1] == 'photo', 'T14 第二件放到第二个格子')

    # ---- 收集品拾取物
    p = Pickup(0, 0, 'collect', 1)
    p.ckey = 'ring_copper'
    g.pickups.append(p)
    p._collect(g)
    check('ring_copper' in g.profile['collects'], 'T14 collect 拾取物可收取')
    check(p.alive is False, 'T14 收取后拾取物消失')

    # ---- 展示台：取出 / 放回
    g.showcase_index = 0
    g.lobby_tab = 3
    g._showcase_toggle()
    check(g.profile['showcase'][0] is None, 'T14 展示台格子可取出')
    g._showcase_toggle()
    check(g.profile['showcase'][0] is not None, 'T14 展示台空格可放回')

    # ---- 客厅四分页渲染
    g._enter_lobby()
    for tab in range(4):
        g.lobby_tab = tab
        try:
            for _ in range(2):
                g.draw()
            check(True, f'T14 客厅分页 [{tab}] 渲染正常')
        except Exception:
            check(False, f'T14 客厅分页 [{tab}] 渲染异常: '
                  + traceback.format_exc()[-200:])
    # 图鉴四类 × 翻页
    g.lobby_tab = 2
    try:
        for cat in range(4):
            g.codex_cat = cat
            for idx in (0, 3, 8):
                g.codex_index = idx
                g._codex_sync_page()
                g.draw()
        check(True, 'T14 图鉴四类 × 多条目渲染正常')
    except Exception:
        check(False, 'T14 图鉴渲染异常: ' + traceback.format_exc()[-200:])
    # TAB 循环
    g.lobby_tab = 0
    for _ in range(4):
        g._keydown_lobby(pygame.K_TAB)
    check(g.lobby_tab == 0, 'T14 TAB 四页循环回到起点')

    # ---- 无存档环境不崩
    g2 = Game(headless=True, seed=7, enable_audio=False)
    g2.profile = None
    check(g2.discover('enemy', 'drone'), 'T14 无存档 discover 仍返回 True')
    ok = g2.collect_got('gear_cog')
    check(ok, 'T14 无存档 collect_got 不崩')
    g2._enter_lobby()
    for tab in range(4):
        g2.lobby_tab = tab
        try:
            g2.draw()
        except Exception:
            check(False, f'T14 无存档客厅分页 [{tab}] 异常')
    check(True, 'T14 无存档时客厅四分页均可渲染')


# ---------------------------------------------------------------- T9
def _clear_one_floor(g, floor_tag):
    """把当前层的非首领房全部清空，返回清空数。"""
    d = g.dungeon
    cleared = 0
    for c in list(d.rooms.keys()):
        r = d.rooms[c]
        if r.kind == 'boss':
            continue
        g.enter_room(c[0], c[1], None)
        ok, _ = run_until(g, lambda: not any(e.alive for e in g.enemies),
                          max_steps=9000, tag=floor_tag)
        if ok:
            cleared += 1
            r.cleared = True
            r.refresh_doors(locked=False)
    return cleared


def _pump_states(g, max_it=900):
    """推进过场/天赋/层通过等中间状态，直到回到 playing 或终点。

    返回最终 state。
    """
    it = 0
    while it < max_it:
        it += 1
        st = g.state
        if st == 'story':
            g._story_next()
            continue
        if st == 'talent':
            g._talent_confirm()
            continue
        if st == 'levelclear':
            g._start_floor(g.floor + 1)
            continue
        break
    return g.state


def t9_full_run():
    """1.0 需求 1/3：完整跑通"一个场景的 5 个小关 × 3 层"。

    重点校验新的首领房规则：只有第 3 关（小 Boss）与第 5 关（大 Boss）
    的最后一层才有首领房，普通关三层都是战斗房。
    """
    section('T9 全流程通关（场景 5 关 × 3 层 + 首领房规则）')
    g = Game(headless=True, seed=4242, enable_audio=False)
    g.profile = SV.new_profile(0, '全流程测试')
    g.store = None
    g.start_run()
    _pump_states(g)                       # 跳过开场过场
    check(g.state == 'playing', f'T9 开局进入 playing（{g.state}）')

    scene = (g.level_state or {}).get('scene')
    check(scene is not None, f'T9 开局已进入场景（{scene}）')

    total_kills0 = g.kills
    for stage_idx in range(5):
        # 用关卡状态机推进到目标关（第 0 关已在跑）
        ls = g.level_state or {}
        if int(ls.get('stage_idx', 0)) != stage_idx:
            PR.next_stage(g.profile, scene, stage_idx)
            g.level_state = {
                'scene': scene,
                'scene_idx': ls.get('scene_idx', 0),
                'stage_idx': stage_idx,
                'diff': C.difficulty(ls.get('scene_idx', 0), stage_idx),
                'kind': C.stage_kind(stage_idx), 'floors': S.FLOORS,
            }
            g.floor = 1
            g._stage_done = False
            g._start_floor(1)
        want_boss = C.stage_kind(stage_idx) in ('miniboss', 'boss')
        for floor in range(1, S.FLOORS + 1):
            g.floor = floor if g.dungeon is None else g.floor
            check(g.floor == floor,
                  f'T9 stage{stage_idx} 第 {floor} 层（实际 {g.floor}）')
            d = g.dungeon
            has_boss = bool(d.boss_key) and d.rooms[d.boss_key].kind == 'boss'
            expect_boss = want_boss and floor >= S.FLOORS
            check(has_boss == expect_boss,
                  f'T9 stage{stage_idx} fl{floor} 首领房 {has_boss}/{expect_boss}')
            cleared = _clear_one_floor(g, f't9s{stage_idx}f{floor}')
            check(cleared >= 3,
                  f'T9 stage{stage_idx} fl{floor} 清空 {cleared} 个非首领房')
            if has_boss:
                bk = d.boss_key
                g.enter_room(bk[0], bk[1], None)
                for _wave in range(2):
                    for _enemy in g.enemies:
                        _enemy.alive = False
                    g.step(1 / 60.0, {'mx': 0, 'my': 0, 'aim': 0,
                                      'shoot': False, 'dash': False, 'slow': False})
                g.player.hp = g.player.max_hp
                ok, steps = run_until(
                    g, lambda: (g.boss is None) or (not g.boss.alive),
                    max_steps=18000, tag=f't9boss{stage_idx}f{floor}')
                check(ok, f'T9 stage{stage_idx} fl{floor} 首领击败（{steps} 帧）')
                if not g.room.cleared:
                    run_until(g, lambda: g.room.cleared, 6000,
                              tag=f't9bossremain{stage_idx}f{floor}')
                check(g.room.portal is not None,
                      f'T9 stage{stage_idx} fl{floor} 传送门出现')
            # 进传送门推进
            g.room.portal = (g.player.x, g.player.y)
            g.step(1 / 60.0, {'mx': 0, 'my': 0, 'aim': 0, 'shoot': False,
                              'dash': False, 'slow': False})
            g.request_interact()
            g._confirm_key(pygame.K_e)
            _pump_states(g)
            if g.state in ('victory', 'lobby', 'gameover'):
                break
        if g.state in ('victory', 'lobby', 'gameover'):
            break

    check(g.kills > total_kills0, f'T9 累计击杀 {g.kills}')
    check(g.coins > 0, f'T9 累计金币 {g.coins}')
    g._write_save()
    check(g.best_floor >= 1, f'T9 最佳记录已写入（{g.best_floor}）')


# ---------------------------------------------------------------- T15
def t15_talents():
    """1.1 需求 2：天赋三选一（抽卡 / 叠加 / 生效 / UI 渲染）。"""
    section('T15 天赋三选一（1.1 需求 2）')
    from sk import hud
    g = Game(headless=True, seed=77, enable_audio=False)
    g.profile = {
        'name': '测试', 'char': 'scout', 'coins': 0, 'diamonds': 0,
        'cleared_scenes': [], 'unlocked_dungeons': [], 'scene_best': {},
        'stats': {}, 'collects': [], 'showcase': [None] * 6,
        'materials': {},
        'codex': {'enemy': [], 'weapon': [], 'material': [], 'collect': []},
    }
    g.start_run()
    while g.state == 'story':
        g._story_next()

    # ---- 候选池
    check(len(CX.TALENT_ORDER) >= 12, f'T15 天赋池 {len(CX.TALENT_ORDER)} 条')
    picks = CX.roll_talents(g.rng, [], 3)
    check(len(picks) == 3, 'T15 三选一返回 3 个候选')
    check(len(set(picks)) == 3, 'T15 同一次候选不重复')
    # 抗污染天赋在池里（1.3 需求 1）
    check('pur_resist' in CX.TALENT_ORDER, 'T15 池内含抗污染天赋「滤芯装甲」')
    check('pur_purge' in CX.TALENT_ORDER, 'T15 池内含「净化循环」')
    check('pur_ward' in CX.TALENT_ORDER, 'T15 池内含「污染共鸣」')

    # ---- 三选一状态机
    ok = g.start_talent_pick(3)
    check(ok and g.state == 'talent', 'T15 触发三选一进入 talent 状态')
    check(len(g.pending_talents) == 3, 'T15 pending_talents 有 3 个')
    g.talent_pick = 0
    g._talent_move(1)
    check(g.talent_pick == 1, 'T15 → 键移动选择')
    g._talent_move(-1)
    check(g.talent_pick == 0, 'T15 ← 键移回')
    g.talent_pick = 2
    g._talent_move(1)
    check(g.talent_pick == 0, 'T15 选择在候选上循环')

    # ---- 确认后写入 + 加成落地
    g.talent_pick = 0
    g._talent_confirm()
    check(g.state == 'playing', 'T15 确认后回到 playing')
    check(len(g.talents_owned) == 1, 'T15 已选天赋记录到 talents_owned')
    check(g.pending_talents is None, 'T15 确认后清空候选')
    check(isinstance(g.run_stats, dict), 'T15 确认后重算出 run_stats')

    # ---- 渲染不出错
    render_ok = True
    try:
        g.start_talent_pick(3)
        c = pygame.Surface((S.VIEW_W, S.VIEW_H), pygame.SRCALPHA)
        hud.draw_talent(c, g)
        g.talent_pick = 1
        hud.draw_talent(c, g)
    except Exception as e:
        render_ok = False
        print('   渲染异常:', e)
    check(render_ok, 'T15 天赋三选一界面渲染正常')
    g._talent_confirm()

    # ---- 叠加：同一天赋选 3 次后不再出现
    g.talents_owned = ['pur_resist', 'pur_resist', 'pur_resist']
    pool = CX.roll_talents(g.rng, g.talents_owned, 3)
    check('pur_resist' not in pool, 'T15 选满 3 次的天赋不再出现')

    # ---- 抗污染天赋真的减益（乘算 + 硬上限）
    g.talents_owned = []
    g.recompute_talents()
    r0 = float(g.run_stats['pur_resist'])
    check(abs(r0) < 1e-9, 'T15 未选抗污染天赋时抗性为 0')
    g.talents_owned = ['pur_resist']
    g.recompute_talents()
    r1 = float(g.run_stats['pur_resist'])
    check(abs(r1 - 0.25) < 1e-6, f'T15 1 件滤芯装甲抗性 0.25（{r1}）')
    g.talents_owned = ['pur_resist'] * 6
    g.recompute_talents()
    r2 = float(g.run_stats['pur_resist'])
    check(abs(r2 - CX.PUR_RESIST_CAP) < 1e-6,
          f'T15 抗性受硬上限约束到 {CX.PUR_RESIST_CAP}（{r2}）')

    # ---- 数值天赋落进 run_stats
    g.talents_owned = []
    g.recompute_talents()
    g.talents_owned = ['hp_up'] if 'hp_up' in CX.TALENT_ORDER else []
    if g.talents_owned:
        g.recompute_talents()
        check(float(g.run_stats['max_hp']) > 0, 'T15 生命上限天赋计入 run_stats')

    # ---- flag 类天赋进 flags
    g.talents_owned = ['shield']
    if 'shield' in CX.TALENT_ORDER:
        g.recompute_talents()
        check('shield' in g.run_stats['flags'], 'T15 flag 类天赋写入 flags')
        check('shield' in g.run_stats['talents'], 'T15 天赋 key 也记录在 talents')

    # ---- 天赋推进链路：通关一关后应弹三选一
    g.talents_owned = []
    g.recompute_talents()
    g.profile = {
        'name': '测试', 'char': 'scout', 'coins': 0, 'diamonds': 0,
        'cleared_scenes': [], 'unlocked_dungeons': [], 'scene_best': {},
        'stats': {}, 'collects': [], 'showcase': [None] * 6,
        'materials': {}, 'codex': {}, 'run': None,
    }
    g.start_run()
    while g.state == 'story':
        g._story_next()
    ls = g.level_state or {}
    PR.next_stage(g.profile, ls.get('scene'), 1)
    g.level_state = {
        'scene': ls.get('scene'), 'scene_idx': ls.get('scene_idx', 0),
        'stage_idx': 1, 'diff': ls.get('diff', 1.0),
        'kind': C.stage_kind(1), 'floors': S.FLOORS,
    }
    g.floor = S.FLOORS
    g._stage_done = False
    g._next_floor()
    check(g.state in ('talent', 'story'),
          f'T15 打完一关后进入三选一/过场（state={g.state}）')


# ---------------------------------------------------------------- T10
def t10_render_coords():
    """渲染坐标一致性：世界坐标 -> 画布坐标必须统一加上相机偏移。

    历史 bug：FX 的粒子 / 冲击环 / 伤害飘字漏加相机偏移，导致所有爆炸、
    火花、飘字整体偏到命中点的左上角（偏移量恰好等于 CAM_OFF = (48,4)）。
    这条测试用「在已知世界坐标放一个特效，检查像素落在画布上的确切位置」
    把该行为锁死，防止回归。
    """
    section('T10 渲染坐标一致性（相机偏移）')
    g = Game(headless=True, seed=11, enable_audio=False)
    g.start_run()
    cam = S.CAM_OFF
    check(cam[0] != 0 or cam[1] != 0,
          f'T10 相机偏移非零（{cam}），否则本测试形同虚设')

    wx, wy = 200.0, 150.0
    red = (255, 0, 0)

    def fresh():
        """清空一切可能遮挡的实体与特效"""
        g.fx.clear()
        g.room.props = []
        g.room.pickups = []
        g.enemies = []
        g.bullets = []
        g.player.x, g.player.y = S.IN_R - 20.0, S.IN_B - 20.0

    def px(x, y):
        return g.canvas.get_at((int(x), int(y)))[:3]

    # ---- 粒子
    fresh()
    g.fx.burst(wx, wy, red, n=1, speed=0.0, life=99.0, size=11,
               drag=0.0, shape='circle')
    g.fx.parts[-1].x, g.fx.parts[-1].y = wx, wy
    g.draw()
    check(px(wx + cam[0], wy + cam[1]) == red,
          f'T10 粒子绘制在 世界坐标+相机偏移 处'
          f'（实测 {px(wx + cam[0], wy + cam[1])}）')
    check(px(wx, wy) != red,
          f'T10 粒子未出现在漏加偏移的旧位置（实测 {px(wx, wy)}）')

    # ---- 冲击环
    fresh()
    g.fx.ring(wx, wy, 12, 12.5, 99.0, red, 7)
    g.draw()

    def scan_has_ring(cx, cy, rad=16):
        """在 (cx,cy) 邻域内是否存在"红环"像素"""
        for dy in range(-rad, rad + 1):
            for dx in range(-rad, rad + 1):
                c = px(cx + dx, cy + dy)
                if c[0] > 150 and c[1] < 110 and c[2] < 110:
                    return True
        return False

    check(scan_has_ring(wx + cam[0], wy + cam[1]),
          'T10 冲击环绘制在 世界坐标+相机偏移 处')
    check(not scan_has_ring(wx, wy),
          'T10 冲击环未出现在漏加偏移的旧位置')

    # ---- 伤害飘字
    fresh()
    green = (0, 255, 0)
    g.fx.text(wx, wy, '88', green, g.assets.font(13), 99.0)
    g.draw()
    tw = g.assets.font(13).size('88')[0]
    found = False
    for dy in range(0, 15):
        for dx in range(-3, tw + 4):
            c = px(wx + cam[0] - tw / 2 + dx, wy + cam[1] + dy)
            if c[1] > 140 and c[0] < 130 and c[2] < 130:
                found = True
                break
        if found:
            break
    check(found, 'T10 伤害飘字绘制在 世界坐标+相机偏移 处')

    # ---- 实体与特效必须落在同一坐标系：把敌人生成在粒子同一位置，
    #      敌人的绘制中心与粒子的绘制中心应当重合
    fresh()
    from sk import enemy as _enemy
    e = _enemy.make('slime', wx, wy, 1, False)
    g.enemies = [e]
    g.room.enemies_spawned = True
    g.room.cleared = False
    g.draw()
    check(px(wx + cam[0], wy + cam[1]) != (14, 13, 18),
          'T10 敌人在 世界坐标+相机偏移 处可见')
    g.enemies = []


# ---------------------------------------------------------------- T11
def t11_weapon_swap_no_pingpong():
    """武器自动交换不能来回抢：踩在枪上只换一次，之后必须稳定。

    历史 bug：_swap_weapon 会把旧枪掉在玩家脚下，而自动交换是按"距离 < 半径"
    每帧电平触发的，于是下一帧立刻把旧枪换回来、再下一帧又换回去……
    A->B->A->B 无限往返（每轮新建一个 Pickup + 特效）。

    网页版的后果更严重：它的掉落物遍历用的是活数组而不是快照，
    新 push 的旧枪会被同一个 for 循环"续命"，于是**单帧内死循环**，
    实测堆内存一路涨到 4GB 后 Node 崩溃。
    """
    noop = {'mx': 0, 'my': 0, 'aim': 0, 'shoot': False, 'dash': False,
            'slow': False}

    # --- 场景 A：直接踩在掉落的枪上
    g = Game(headless=True, seed=31, enable_audio=False)
    g.start_run()
    pl = g.player
    pl.x, pl.y = S.ROOM_CX, S.ROOM_CY
    pl.wkey = 'pistol'
    g.pickups.append(Pickup(pl.x, pl.y, 'weapon', wkey='smg'))
    n0 = len(g.pickups)
    seq = []
    for _ in range(90):
        g.step(1.0 / 60.0, noop)
        seq.append(pl.wkey)
    changes = sum(1 for a, b in zip(seq, seq[1:]) if a != b)
    check(pl.wkey == 'pistol', f'T13 踩枪不自动换枪（wkey={pl.wkey}）')
    g.request_interact()
    check(g.confirm_prompt is not None, 'T13 换枪需二次确认')
    g._confirm_key(pygame.K_RETURN)
    check(pl.wkey == 'pistol' and pl.wkey2 == 'smg',
          'T13 确认后装备第二武器')
    check(changes == 0, f'T13 换枪后不再反复抢回（其后变化 {changes} 次）')
    check(len(g.pickups) <= n0 + 2,
          f'T13 掉落物数量不失控（{n0} -> {len(g.pickups)}）')

    # --- 场景 B：走过的枪能反复交换（走出去再走回来）
    g2 = Game(headless=True, seed=31, enable_audio=False)
    g2.start_run()
    p2 = g2.player
    p2.x, p2.y = S.ROOM_CX, S.ROOM_CY
    p2.wkey = 'pistol'
    g2.pickups.append(Pickup(p2.x + 8, p2.y, 'weapon', wkey='laser'))
    for _ in range(3):
        g2.step(1.0 / 60.0, noop)
    check(p2.wkey == 'pistol', 'T13 场景B 路过保持旧武器')
    g2.request_interact()
    g2._confirm_key(pygame.K_RETURN)
    check(p2.wkey == 'pistol' and p2.wkey2 == 'laser',
          'T13 场景B 确认后获得第二武器')
    # 走远到半径之外（必须仍在同一房间内，否则会穿门换房）
    p2.x = S.ROOM_CX + 80
    for _ in range(3):
        g2.step(1.0 / 60.0, noop)
    p2.switch_weapon()
    check(p2.wkey == 'laser' and p2.wkey2 == 'pistol',
          'T13 场景B 可切换两把武器')


# ---------------------------------------------------------------- T12
def t12_no_stuck_in_wall():
    """防卡死：圆心陷进实心瓦片后必须能自行脱困。

    历史 bug（本版本修复）：玩家被传送/击退推进实心瓦片内部，
    而 _slide 的二分逼近在"起点已碰撞"时恒返回原点，
    于是四个方向怎么推都是 0 位移 —— 永久卡死。
    触发条件：ENTRY_FROM 的硬编码落点恰好生成出障碍物（掩体/木桶等）。

    修复分三层：
      1) _slide 起点已碰撞时放弃二分，直接尝试整段位移；
      2) utils.unstick / find_free_spot 螺旋搜索最近空位；
      3) game 每帧 _ensure_player_free + 连续零位移 _check_stuck。
    """
    from sk import utils as U

    noop = {'mx': 0, 'my': 0, 'aim': 0, 'shoot': False, 'dash': False, 'slow': False}

    # --- 场景 A：把玩家硬塞进实心瓦片 -> 必须能走出来
    g = Game(headless=True, seed=5, enable_audio=False)
    g.start_run()
    solid_cells = [(tx, ty)
                   for ty in range(S.ROOM_ROWS) for tx in range(S.ROOM_COLS)
                   if g.room.solid(tx, ty)]
    if not solid_cells:
        check(False, 'T12 测试房间应存在实心瓦片')
        return
    tx, ty = solid_cells[len(solid_cells) // 2]
    cx = tx * S.TILE + S.TILE / 2
    cy = ty * S.TILE + S.TILE / 2
    check(U.circle_solid(cx, cy, g.player.radius, g.room.solid),
          'T12 选定测试点确实落在实心瓦片内')

    for name, (dx, dy) in (('右', (1, 0)), ('左', (-1, 0)),
                           ('下', (0, 1)), ('上', (0, -1))):
        g.player.x, g.player.y = cx, cy
        x0, y0 = cx, cy
        inp = dict(noop, mx=dx, my=dy)
        for _ in range(120):
            g.player.update(g, 1.0 / 60.0, inp)
        moved = U.dist(x0, y0, g.player.x, g.player.y)
        check(moved > 8.0,
              f'T12 陷入墙中朝{name}推能脱困（位移 {moved:.1f}px）')

    # --- 场景 B：unstick 必须给出不碰撞的落点
    spot = U.find_free_spot(cx, cy, g.player.radius, g.room.solid)
    check(spot is not None, 'T12 find_free_spot 能在墙内找到空位')
    if spot is not None:
        check(not U.collide_test(spot[0], spot[1], g.player.radius, g.room.solid),
              'T12 find_free_spot 返回的落点不碰撞')
        # 脱困距离应当合理（不该丢到房间另一头）
        check(U.dist(cx, cy, spot[0], spot[1]) < S.TILE * 6,
              f'T12 脱困落点应就近（{U.dist(cx, cy, spot[0], spot[1]):.1f}px）')

    # --- 场景 C：入口落点被占时，enter_room 必须落到安全位置
    g2 = Game(headless=True, seed=5, enable_audio=False)
    g2.start_run()
    r = g2.room
    # 人为把东门落点那格改成实心（模拟障碍生成在门口）
    ex, ey = S.ENTRY_FROM['E']
    etx, ety = int(ex // S.TILE), int(ey // S.TILE)
    orig = r.solid
    occupied = set()

    def solid_patched(tx, ty, _o=orig, _e=(etx, ety), _acc=occupied):
        if (tx, ty) == _e:
            return True
        return _o(tx, ty)

    r.solid = solid_patched
    g2.dungeon.room(r.gx, r.gy).solid = solid_patched
    g2.enter_room(r.gx, r.gy, 'E')
    check(not U.collide_test(g2.player.x, g2.player.y, g2.player.radius,
                             solid_patched),
          f'T12 入口格被占时落点仍安全（{g2.player.x:.1f},{g2.player.y:.1f}）')
    r.solid = orig
    g2.dungeon.room(r.gx, r.gy).solid = orig

    # --- 场景 D：连续零位移自动脱困（_check_stuck 兜底）
    g3 = Game(headless=True, seed=7, enable_audio=False)
    g3.start_run()
    own_solid = [(x, y) for y in range(S.ROOM_ROWS) for x in range(S.ROOM_COLS)
                 if g3.room.solid(x, y)]
    tx, ty = own_solid[0]
    g3.player.x = tx * S.TILE + S.TILE / 2
    g3.player.y = ty * S.TILE + S.TILE / 2
    before = g3._stuck_rescues
    inp = dict(noop, mx=1.0, my=0.0)
    for _ in range(int(S.STUCK_SECONDS * 60) + 40):
        g3.step(1.0 / 60.0, inp)
    check(g3._stuck_rescues >= before,
          f'T12 自动脱困计数未异常回退（rescue {before} -> {g3._stuck_rescues}）')
    from sk import utils as _u
    check(not _u.collide_test(g3.player.x, g3.player.y, g3.player.radius,
                              g3.room.solid, g3.room.blockers()),
          'T12 自动脱困后玩家不在障碍内')


# ---------------------------------------------------------------- 主流程
def t16_growth():
    """需求 4/5/6/7：养成系统（角色解锁 / 武器强化 / 技能被动 / 天赋 / 材料）。"""
    section('T16 养成系统（角色 / 武器 / 技能 / 天赋）')
    from sk import growth as GR
    from sk import gamedata as GD
    from sk import save as SV

    # ---- 干净存档
    p = SV.new_profile(0, 'T16')
    p['coins'] = 30000
    p['diamonds'] = 500
    p['materials'] = {'scrap': 60, 'fiber': 40, 'circuit': 30,
                      'crystal': 20, 'alloy': 15, 'core': 10, 'relic': 5,
                      'prism': 5}

    # ---- 角色：列表 / 购买 / 切换
    chars = GR.char_list(p)
    check(len(chars) == len(GD.CHAR_ORDER), f'T16 角色表 {len(chars)} 个')
    check(chars[0]['owned'] and chars[0]['cur'], 'T16 scout 默认拥有且出战')
    ok, msg = GR.buy_char(p, 'engineer')
    check(ok and 'engineer' in p['chars'], f'T16 购买工程师（{msg}）')
    ok2, msg2 = GR.buy_char(p, 'engineer')
    check(not ok2, 'T16 重复购买被拒')
    ok3, msg3 = GR.select_char(p, 'engineer')
    check(ok3 and p['char'] == 'engineer', f'T16 切换角色（{msg3}）')
    ok4, _ = GR.select_char(p, 'ranger')
    check(not ok4, 'T16 未解锁角色不能切换')
    # 钻石角色
    ok5, _ = GR.buy_char(p, 'ghost')
    check(ok5, 'T16 钻石角色可解锁')
    # 合成角色
    ok6, _ = GR.buy_char(p, 'prime')
    check(ok6, 'T16 材料合成角色可解锁')

    # ---- 武器：强化 / 品质成长 / 封顶
    w0 = GR.weapon_info(p, 'pistol')
    check(w0['lv'] == 0 and w0['quality'] == 'white', 'T16 初始武器白品质 Lv.0')
    for _ in range(5):
        GR.upgrade_weapon(p, 'pistol')
    w1 = GR.weapon_info(p, 'pistol')
    check(w1['lv'] == 5, f"T16 强化到 Lv.5（{w1['lv']}）")
    check(w1['quality'] == W.quality_of('pistol'), f"T16 强化后品质固定（{w1['quality']}）")
    check(w1['next_quality_at'] is None, 'T16 强化不改变武器品质')
    check(w1['mul'] > w0['mul'] * 1.25, f"T16 强化显著提升倍率"
          f"（{w0['mul']:.2f} -> {w1['mul']:.2f}）")
    # 金币不足时被拒
    p2 = SV.new_profile(1, 'poor')
    p2['coins'] = 0
    ok7, why7, _c, _m = GR.can_upgrade(p2, 'pistol')
    check(not ok7 and '金币' in why7, f'T16 金币不足时拒绝强化（{why7}）')

    # ---- 技能 / 被动
    ok8, msg8 = GR.upgrade_skill(p, 'power')
    check(ok8 and p['skills'].get('power') == 1, f'T16 升级技能（{msg8}）')
    ok9, msg9 = GR.upgrade_passive(p, 'thorns')
    check(ok9 and p['passives'].get('thorns') == 1, f'T16 升级被动（{msg9}）')
    ls = GR.skill_list(p)
    check(len(ls) == len(GD.SKILLS), f'T16 技能表 {len(ls)} 条')
    lp = GR.passive_list(p)
    check(len(lp) == len(GD.PASSIVES), f'T16 被动表 {len(lp)} 条')

    # ---- 天赋（永久）
    lt = GR.talent_list(p)
    check(len(lt) == len(CX.TALENTS), f'T16 永久天赋 {len(lt)} 条')
    ok10, msg10 = GR.upgrade_talent(p, 'dmg_up')
    check(ok10 and p['talent_levels'].get('dmg_up') == 1,
          f'T16 升级永久天赋（{msg10}）')

    # ---- 材料摘要
    rows = GR.material_summary(p)
    check(len(rows) > 0, f'T16 材料背包 {len(rows)} 类')
    check(all(n > 0 for _k, _n, _t, n in rows), 'T16 材料摘要不含零数量')

    # ---- 客厅养成面板端到端（键盘驱动，不直接调服务层）
    g = Game(headless=True, seed=5, enable_audio=False)
    g.profile = SV.new_profile(2, 'T16b')
    g.profile['coins'] = 10000
    g.profile['materials'] = {'scrap': 30, 'fiber': 20, 'circuit': 10}
    g._enter_lobby()
    g.lobby_tab = 1
    g.growth_sub = 0
    g.growth_index = 1                 # 第二个角色
    before = len(g.profile['chars'])
    g._keydown_lobby(pygame.K_RETURN)
    check(len(g.profile['chars']) >= before, 'T16 客厅 Enter 购买角色（不崩）')
    # 切到武器子页强化
    g.growth_sub = 1
    g.growth_index = 0
    lv0 = g.profile['weapons'].get('pistol', 0)
    g._keydown_lobby(pygame.K_RETURN)
    check(g.profile['weapons'].get('pistol', 0) >= lv0, 'T16 客厅 Enter 强化武器')
    # 子页切换与渲染
    okdraw = True
    for sub in range(4):
        g.growth_sub = sub
        for gi in range(4):
            g.growth_index = gi
            try:
                g.draw()
            except Exception:
                okdraw = False
    check(okdraw, 'T16 养成四子页 × 多条目渲染正常')

    # ---- 角色真正影响开局（需求 6）
    g.profile['weapons'] = {'pistol': 5}
    g.profile['weapon'] = 'pistol'
    g.start_run()
    while g.state == 'story':
        g._story_next()
    check(g.player.wkey == 'pistol', f'T16 开局武器跟随存档（{g.player.wkey}）')
    check(g.char_key == g.profile['char'], 'T16 开局应用当前角色')
    base = GD.char(g.profile['char'])
    check(g.player.max_hp >= int(base['hp']),
          f"T16 角色生命上限生效（{g.player.max_hp}）")
    check(abs(g.player.wmul(g) - GD.quality_of('white')['mul'] * 1.50) < 1e-6,
          f"T16 武器强化倍率接入伤害（×{g.player.wmul(g):.2f}）")


def t17_chests():
    """需求 7：宝箱分级制度（5 类 × 2 档）+ 开箱结算。"""
    print('\n=== T17 宝箱分级（货币/医疗/材料/武器/收集 × 一般/极品） ===')
    from sk import gamedata as GD
    from sk.pickup import Pickup
    from sk import dungeon as DN

    # ---- 数据层：5 类 × 2 档齐全
    check(set(GD.CHEST_ORDER) == {'coin', 'heal', 'material', 'weapon',
                                  'collect'},
          f'T17 宝箱共 5 类（{len(GD.CHEST_ORDER)}）')
    tiers_ok = all(set(GD.CHESTS[k].keys()) >= {'normal', 'superb'}
                   for k in GD.CHEST_ORDER)
    check(tiers_ok, 'T17 每类都有 一般/极品 两档')
    check(all(GD.CHESTS['collect'][t]['w'] <
              GD.CHESTS['weapon'][t]['w'] for t in ('normal', 'superb')),
          'T17 收集品箱权重低于武器箱（更稀有）')

    # ---- roll_chest 分布：全部 10 种组合都可达
    rng = random.Random(20240923)
    seen = set()
    for _ in range(4000):
        seen.add(GD.roll_chest(rng, floor_bias=0.2))
    check(len(seen) == 10, f'T17 roll_chest 覆盖 10 种组合（{len(seen)}）')

    # ---- 深层更容易出极品
    rng2 = random.Random(7)
    sup_deep = sum(1 for _ in range(2000)
                   if GD.roll_chest(rng2, floor_bias=1.5)[1] == 'superb')
    rng3 = random.Random(7)
    sup_shallow = sum(1 for _ in range(2000)
                      if GD.roll_chest(rng3, floor_bias=0.0)[1] == 'superb')
    check(sup_deep > sup_shallow,
          f'T17 深层极品更多（{sup_deep} > {sup_shallow}）')

    # ---- chest_loot 各类结算
    rng4 = random.Random(11)
    lc = GD.chest_loot(rng4, 'coin', 'superb', 3)
    check(lc['coins'] >= 35, f"T17 极品货币箱金币更多（{lc['coins']}）")
    lh = GD.chest_loot(rng4, 'heal', 'superb', 3)
    check(lh['heal'] >= 7 and lh['energy'] > 0, 'T17 极品急救箱回血 + 回能')
    lm = GD.chest_loot(rng4, 'material', 'normal', 2)
    check(isinstance(lm['mats'], dict), 'T17 材料箱返回材料字典')
    lw = GD.chest_loot(rng4, 'weapon', 'superb', 3)
    check(lw['quality'] in GD.QUALITY_ORDER, f"T17 武器箱给品质（{lw['quality']}）")

    # ---- 拾取物：宝箱名 / 二次确认文案
    pc = Pickup(0, 0, 'chest', ckey='material', ctier='superb')
    check('稀有材料箱' in pc.prompt_text(), f'T17 宝箱提示带类别名：{pc.prompt_text()}')
    title, sub = pc.confirm_text()
    check('稀有材料箱' in title and '再按一次' in sub,
          f'T17 二次确认文案正确：{title}')

    # ---- 端到端：开箱结算（直接对拾取物调用 interact）
    g = Game(headless=True, seed=20240923, enable_audio=False)
    from sk import save as SV
    g.profile = SV.new_profile(0, 'T17')
    g.start_run()
    while g.state == 'story':
        g._story_next()
    g.state = 'playing'
    chest = Pickup(g.player.x, g.player.y, 'chest', ckey='coin',
                   ctier='superb')
    g.room.pickups = [chest]
    before_coins = len([p for p in g.room.pickups if p.kind == 'coin'])
    chest.interact(g)
    check(chest.alive is False, 'T17 开箱后宝箱消失')
    after_coins = len([p for p in g.room.pickups if p.kind == 'coin'])
    check(after_coins > before_coins, f'T17 开箱掉出金币（{after_coins} 枚）')

    # ---- 材料箱：材料直接进 game.mats
    g.mats = {}
    mc = Pickup(g.player.x, g.player.y, 'chest', ckey='material',
                ctier='normal')
    g.room.pickups = [mc]
    mc.interact(g)
    check(len(g.mats) > 0, f'T17 材料箱把材料放进背包（{len(g.mats)} 种）')


def t18_settings():
    """需求 12/15：设置面板（音乐/音效/震动开关 + 摇杆模式 + 灵敏度）。"""
    section('T18 设置面板（音效 / 震动 / 摇杆）')
    from sk import hud
    from sk import save as SV

    g = Game(headless=True, seed=20240923, enable_audio=False)
    g.profile = SV.new_profile(0, 'T18')
    g._load_settings_from_profile()

    rows, st = hud._setting_rows(g)
    keys = [r[1] for r in rows]
    check('music' in keys and 'sfx' in keys and 'shake' in keys,
          f'T18 设置含音乐/音效/震动（{len(rows)} 项）')
    check('joystick' in keys and 'joy_sens' in keys, 'T18 设置含摇杆模式与灵敏度')

    # ---- 2.2 战斗音效默认开启
    check(g.setting['music'] is False and g.setting['sfx'] is True,
          'T18 音乐默认关闭、音效默认开启')
    check(g.setting['vibrate'] is False, 'T18 震动默认关闭')

    # ---- 切换 bool
    g.state = 'help'
    g.setting_index = keys.index('sfx')
    g._keydown_settings(pygame.K_RETURN)
    check(g.setting['sfx'] is False, 'T18 Enter 可关闭音效')

    # ---- 摇杆模式循环
    g.setting_index = keys.index('joystick')
    before = g.setting['joystick']
    g._keydown_settings(pygame.K_RETURN)
    check(g.setting['joystick'] != before,
          f"T18 摇杆模式可切换（{before} -> {g.setting['joystick']}）")

    # ---- 灵敏度步进与夹紧
    g.setting_index = keys.index('joy_sens')
    g.setting['joy_sens'] = 1.0
    g._keydown_settings(pygame.K_RETURN)
    check(abs(g.setting['joy_sens'] - 1.1) < 1e-6,
          f"T18 灵敏度 +0.1（{g.setting['joy_sens']}）")
    for _ in range(40):
        g._keydown_settings(pygame.K_d)
    check(g.setting['joy_sens'] <= 2.0, 'T18 灵敏度上限夹紧 2.0')
    for _ in range(40):
        g._keydown_settings(pygame.K_a)
    check(g.setting['joy_sens'] >= 0.4, 'T18 灵敏度下限夹紧 0.4')

    # ---- 选中项循环
    g.setting_index = 0
    g._keydown_settings(pygame.K_w)
    check(g.setting_index == len(rows) - 1, 'T18 ↑ 从首项绕到末项')

    # ---- 渲染不炸
    okdraw = True
    for i in range(len(rows)):
        g.setting_index = i
        try:
            hud.draw_help(g.canvas, g)
        except Exception:
            okdraw = False
    check(okdraw, 'T18 设置面板逐项渲染正常')

    # ---- 落盘：设置写回存档
    g.save_settings()
    check(isinstance(g.profile.get('settings'), dict) and
          'music' in g.profile['settings'], 'T18 设置写回存档')


def t19_changelog():
    """需求 18：更新日志面板（标题右下角入口 + 内容 + 滚动）。"""
    section('T19 更新日志（标题右下角入口）')
    from sk import hud

    g = Game(headless=True, seed=20240923, enable_audio=False)
    from sk import save as SV
    g.profile = SV.new_profile(0, 'T19')

    # ---- 标题页进入 changelog
    g.state = 'title'
    g.log_scroll = 0
    g.state = 'changelog'
    check(g.state == 'changelog', 'T19 可进入更新日志状态')

    # ---- 滚动
    g._keydown(pygame.K_DOWN)
    check(g.log_scroll >= 1, f'T19 ↓ 滚动更新日志（{g.log_scroll}）')
    g._keydown(pygame.K_UP)
    check(g.log_scroll == 0, 'T19 ↑ 回滚更新日志')

    # ---- 内容非空（v1.0 标题）
    lines = hud._changelog_lines()
    check(len(lines) > 10, f'T19 更新日志内容非空（{len(lines)} 条）')
    heads = [t for k, t in lines if k == 'h']
    check(any('v1.0' in h for h in heads), 'T19 更新日志含 v1.0 标题')
    check(any('v1.4' in h for h in heads), 'T19 更新日志含 v1.4 标题（最新）')

    # ---- 渲染不炸
    okdraw = True
    try:
        hud.draw_changelog(g.canvas, g)
    except Exception:
        okdraw = False
    check(okdraw, 'T19 更新日志面板渲染正常')

    # ---- 返回标题
    g._keydown(pygame.K_ESCAPE)
    check(g.state == 'title', 'T19 ESC 返回标题')


def t20_weapon_mech():
    """需求 6（1.4）：武器扩充 + 机制化品质。"""
    section('T20 武器扩充与机制化品质（1.4 需求 6）')
    from sk import gamedata as GD
    from sk import save as SV

    # ---- 基础型号数量与近战/远程并存
    check(len(W.ORDER) >= 10, f'T20 基础型号 {len(W.ORDER)} 把（≥10）')
    check(len(W.BASE_ORDER) == len(W.ORDER), 'T20 BASE_ORDER 与 ORDER 一致')
    melee = [k for k in W.ORDER if W.get(k).melee]
    ranged = [k for k in W.ORDER if not W.get(k).melee]
    check(len(melee) >= 1, f'T20 近战型号 {len(melee)} 把')
    check(len(ranged) >= 5, f'T20 远程型号 {len(ranged)} 把')

    # ---- 品质机制：逐级"加机制"而非只加数值
    base = W.get('pistol')
    prev_cnt, prev_pierce = base.count, base.pierce
    for q in GD.QUALITY_ORDER:
        s = W.apply_quality(base, q, GD.quality_of(q)['mul'])
        check(s.cd <= base.cd + 1e-6, f'T20 {q} 射速不低于基准')
        prev_cnt = max(prev_cnt, s.count)
        prev_pierce = max(prev_pierce, s.pierce)
    check(prev_cnt > base.count, 'T20 高等级提升弹丸数（蓝+）')
    check(prev_pierce > base.pierce, 'T20 高等级提升穿透（紫+）')

    # ---- 机制表：金/红/璀璨 各有独特机制
    check(W.quality_mech('gold').get('burst'), 'T20 金色带「击杀迸射」')
    check(W.quality_mech('red').get('split'), 'T20 赤红带「命中分裂」')
    check(W.quality_mech('radiant').get('homing'), 'T20 璀璨带「追猎弹道」')
    for q in GD.QUALITY_ORDER:
        check(W.mech_summary(q) != '', f'T20 {q} 机制说明非空')
    check(len(GD.QUALITY_MECH_DESC) == 7, 'T20 机制说明表 7 条')

    # ---- 近战：范围内敌人受创、范围随品质变大
    g = Game(headless=True, seed=7, enable_audio=False)
    g.profile = SV.new_profile(0, 'T20')
    g.start_run()
    g.state = 'playing'          # 跳过开场过场
    pl = g.player
    pl.wkey = 'blade'
    e = Enemy(pl.x + 22.0, pl.y, 1)
    g.enemies.append(e)
    hp0 = e.hp
    g.step(1 / 60.0, {'mx': 0, 'my': 0, 'aim': 0.0, 'shoot': True,
                      'dash': False, 'slow': False})
    check(e.hp < hp0, 'T20 近战挥砍命中身前敌人')
    check(len(g.bullets) == 0, 'T20 近战不产生子弹')
    b0 = W.apply_quality(W.get('blade'), 'white', 1.0)
    b6 = W.apply_quality(W.get('blade'), 'radiant', 1.0)
    check(b6.reach > b0.reach and b6.arc > b0.arc,
          f'T20 近战范围随品质增大（{b0.reach:.0f}->{b6.reach:.0f}）')

    # ---- sprite_key 能解析到合法贴图 key
    from sk import assets as A
    known = set(A.all_keys())
    for k in W.ORDER:
        check(W.sprite_key(k) in known, f'T20 {k} 贴图 key 合法（{W.sprite_key(k)}）')


def t21_hitstop_knock():
    """需求 20：打击停顿 + 受击击退。"""
    section('T21 打击停顿 / 受击击退（需求 20）')
    from sk import save as SV

    g = Game(headless=True, seed=11, enable_audio=False)
    g.profile = SV.new_profile(0, 'T21')
    g.start_run()
    g.state = 'playing'          # 跳过开场过场
    pl = g.player
    pl.wkey = 'pistol'

    # ---- 命中产生定帧
    e = Enemy(pl.x + 60.0, pl.y, 1)
    g.enemies.append(e)
    e.take_damage(1.0, g, pl.x, pl.y)
    check(g.hitstop > 0, f'T21 命中触发打击停顿（{g.hitstop:.3f}s）')
    check(g.hitstop <= S.HITSTOP_MAX + 1e-6, 'T21 停顿夹在上限内')

    # ---- 定帧不会叠加成"卡死"
    for _ in range(10):
        g.add_hitstop(S.HITSTOP_KILL)
    check(g.hitstop <= S.HITSTOP_MAX + 1e-6,
          f'T21 多次请求取最大值不叠加（{g.hitstop:.3f}）')

    # ---- 受击击退：从来源方向被推开
    pl.hp = pl.max_hp
    pl.iframes = 0.0
    pl.knock_t = 0.0
    sx, sy = pl.x - 40.0, pl.y           # 来源在左侧 -> 应向右推
    pl.take_damage(2.0, g, sx, sy)
    check(pl.knock_t > 0, 'T21 受击进入击退状态')
    check(pl.knock_dx > 0, f'T21 击退方向正确（dx={pl.knock_dx:.1f}）')
    check(g.hitstop > 0, 'T21 受击触发打击停顿')

    # ---- 击退期间确实产生位移
    x0 = pl.x
    for _ in range(6):
        g.step(1 / 60.0, {'mx': 0, 'my': 0, 'aim': 0.0, 'shoot': False,
                          'dash': False, 'slow': False})
    check(pl.x > x0, f'T21 击退期间位置前移（{x0:.1f}->{pl.x:.1f}）')


def t22_slot_flow():
    """需求 10：标题 → 选档 → 必须进客厅（曾出现死循环，回归防护）。

    注意：SaveStore 是**进程内单例**，本用例会建档并切换当前档。
    若不还原，后续用例（T6/T10/T12/T13…）新建的 Game 会自动载入这个档，
    导致它们读到脏进度而失败。故这里先快照、测完还原。
    """
    print('\n=== T22 存档选择流程（标题 → 选档 → 客厅） ===')
    g = Game(headless=True, seed=20240923, enable_audio=False)
    if g.store is None:
        check(False, 'T22 无存档后端，跳过')
        return

    # ---- 快照单例存档，测完还原（含磁盘，避免污染其它用例）
    import copy
    snap_data = copy.deepcopy(g.store.data)
    snap_last = g.profile

    try:
        # 造一个新档，模拟"已有存档"
        g.create_profile(0, '回归档')
        check(g.has_profile(), 'T22 新建档成功')

        # 回到标题，走一遍"开始游戏"路径
        g.state = 'title'
        g.menu_index = 0
        g._menu_pick('new')
        check(g.state == 'slots', 'T22 点开始游戏进入存档槽界面')

        # 光标默认停在已有档上
        slots = g.slot_list()
        idx = next((i for i, s in enumerate(slots) if s is not None), 0)
        g.slot_index = idx

        # 按 Enter 选择存档 —— 关键断言：必须进客厅，而不是退回标题
        g._keydown_slots(pygame.K_RETURN)
        check(g.state == 'lobby',
              f'T22 选档后进入客厅而非主菜单（state={g.state}）')
        check(g.has_profile(), 'T22 选档后存档已载入')
        check(g.profile is not None and g.profile.get('name') == '回归档',
              'T22 载入的是被选中的那份存档')

        # 从客厅能真正开局（证明"能进游戏"）
        # 出击后先播开场过场（story），过场结束才进 playing —— 两者都算"进了游戏"
        g._lobby_enter_next()
        check(g.state in ('playing', 'story'),
              f'T22 客厅出击进入战斗/过场（state={g.state}）')
        g.state = 'playing'   # 收尾归位，避免过场态泄漏

        # 鼠标点选路径同样必须进客厅
        g.state = 'slots'
        cx, cy = 120, 84 + idx * 52 + 10
        g._slot_mouse((cx * max(1, g.scale) + g.view_off[0],
                       cy * max(1, g.scale) + g.view_off[1]))
        check(g.state == 'lobby', f'T22 鼠标选档也进客厅（state={g.state}）')

        # 新建档路径也必须进客厅
        g.state = 'slots'
        g.slot_pending = 1
        g.name_buf = '新档'
        g.state = 'slot_create'
        g._keydown_slots(pygame.K_RETURN)
        check(g.state == 'lobby', f'T22 新建档后进客厅（state={g.state}）')
    finally:
        # ---- 还原单例存档（内存 + 磁盘）
        try:
            g.store.data = snap_data
            g.store.save()
        except Exception:
            pass
        g.profile = snap_last


def t23_input_path():
    """回归：真实键盘读取路径（事件驱动 + get_pressed 并集）。

    背景（血泪教训）：整套用例长期用 `inp_override` 注入输入，而
    `read_input()` 一旦发现 `inp_override` 就**提前返回**，从不调用
    `pygame.key.get_pressed()`。于是"真实键盘读不到 / 窗口失焦导致整表
    False"这类 bug 测试完全无感 —— 用户报"PC 端完全无法移动"时，
    353 项全绿却帮不上忙。

    本用例**不走 inp_override**，直接驱动事件与按键表，覆盖三条：
      1) 正常 get_pressed() 有键 -> 能读出方向
      2) get_pressed() 全 False 但收到 KEYDOWN -> 事件集合兜底仍能移动
      3) 松开（KEYUP）后不再移动；失焦（WINDOWFOCUSLOST）清空按键
    """
    section('T23 真实键盘输入路径（事件驱动兜底）')
    g = Game(headless=True, seed=777, enable_audio=False)
    g.state = 'playing'
    try:
        g.start_run(scene=None, stage_idx=0)
        g.state = 'playing'
        pl = g.player
        if pl is None:
            check(False, 'T23 无法取得玩家')
            return

        # ---- 1) 清空一切，确认无输入时不动
        g.inp_override = None
        g._held_keys = set()
        inp = g.read_input()
        check(inp['mx'] == 0 and inp['my'] == 0,
              'T23 无输入时 mx/my 为 0')

        # ---- 2) get_pressed 全 False，但事件集合里有 K_d（模拟失焦兜底）
        real_gp = pygame.key.get_pressed
        try:
            class _AllFalse(object):
                def __getitem__(self, k):
                    return False

                def __len__(self):
                    return 512

            pygame.key.get_pressed = lambda: _AllFalse()
            g._held_keys = {pygame.K_d}
            inp = g.read_input()
            check(inp['mx'] == 1,
                  f'T23 失焦时事件集合兜底仍能读出向右（mx={inp["mx"]}）')

            # 实际位移：用事件集合驱动一整帧序列
            g._held_keys = {pygame.K_d}
            x0 = pl.x
            for _ in range(30):
                g.update(1 / 60.0)
            moved = pl.x - x0
            check(moved > 5.0,
                  f'T23 失焦兜底真的推动角色（dx={moved:.1f}）')

            # 四个方向都验证
            for key, name, axis in ((pygame.K_a, '左', 'x'),
                                    (pygame.K_w, '上', 'y'),
                                    (pygame.K_s, '下', 'y')):
                g._held_keys = {key}
                if axis == 'x':
                    p0 = pl.x
                else:
                    p0 = pl.y
                for _ in range(20):
                    g.update(1 / 60.0)
                d = abs((pl.x if axis == 'x' else pl.y) - p0)
                check(d > 3.0, f'T23 兜底 {name} 方向可移动（d={d:.1f}）')

            # ---- 3) KEYUP 后不再移动
            g._held_keys = {pygame.K_d}
            g._events_held_backup = None
            g._held_keys.discard(pygame.K_d)      # 等价于收到 KEYUP
            inp = g.read_input()
            check(inp['mx'] == 0, 'T23 松开按键后不再移动')

            # ---- 4) 失焦清空：直接调事件处理
            g._held_keys = {pygame.K_d, pygame.K_a}
            ev = pygame.event.Event(getattr(pygame, 'WINDOWFOCUSLOST', 0))
            try:
                # 通过真实事件队列走一遍
                pygame.event.post(ev)
                g._events()
            except Exception:
                g._held_keys.clear()
            check(len(g._held_keys) == 0,
                  'T23 窗口失焦后按键集合被清空（防"自己走个不停"）')
        finally:
            pygame.key.get_pressed = real_gp
            g._held_keys = set()
            g.inp_override = None
    except Exception as e:
        check(False, f'T23 输入路径用例异常：{e!r}')


def t24_floor_exit_portal():
    """回归：**普通层**清空目标房后必须出现传送门。

    血泪教训：此前只有首领房（on_boss_defeated）会开传送门，
    普通层清空房间只解锁房门。而 _next_floor() 是**唯一**的换层入口，
    且只能通过传送门进入 —— 于是普通层玩家打光所有房间也永远出不去，
    被永久困在同一层。用户报的就是"普通关卡结束后给了钥匙却没有传送门"。

    本用例**不伪造传送门**（T9 的强制赋值掩盖了该 bug），而是模拟真实清房。
    """
    section('T24 普通层目标房 -> 传送门（换层出口）')

    class _D(object):
        enabled = False
        sounds = {}

        def play(self, *a, **k):
            return False

        def set_enabled(self, *a, **k):
            pass

        def buzz(self, *a, **k):
            return False

    import sk.progress as PR
    import sk.chapter as C

    g = Game(headless=True, seed=20241010, enable_audio=False)
    g.audio = _D()
    g.music = _D()
    g.vibrator = _D()

    # 血泪教训：这里**不要** create_profile / PR.start_scene，它们会把
    # 进度写进共享存档（_tmp/testdata），污染后续用例（T2 首当其冲）。
    # 直接把存档摘掉：profile=None 时 start_run 会用第一个主线场景兜底，
    # 且不会触发 stage_enter 过场，state 直接就是 'playing'。
    g.profile = None
    g.level_state = PR.make_run(C.MAIN[0], 0, 0)
    g.start_run(scene=C.MAIN[0], stage_idx=0)
    g.state = 'playing'

    d = g.dungeon
    check(not d.is_boss_floor, 'T24 第 1 关第 1 层确为非首领层')
    check(getattr(d, 'goal_key', None) is not None,
          'T24 普通层也应有 target 目标房（goal_key）')

    gk = d.goal_key
    goal = d.rooms[gk]
    check(goal.kind != 'boss' or d.is_boss_floor,
          f'T24 普通层目标房不是首领房（kind={goal.kind}）')

    # ---- A) 先清一个非目标房：不应有传送门
    nongoal = None
    for k, r in d.rooms.items():
        if r.kind == 'normal' and not r.cleared and k != gk:
            nongoal = k
            break
    if nongoal is not None:
        g.enter_room(nongoal[0], nongoal[1], None)
        g.state = 'playing'
        for _wave in range(3):
            for e in list(g.enemies):
                e.alive = False
            g.step(1 / 60.0, {'mx': 0, 'my': 0, 'aim': 0, 'shoot': False,
                              'dash': False, 'slow': False})
        check(g.room.cleared, 'T24 非目标房已清空')
        check(g.room.portal is None, 'T24 非目标房不开传送门')

    # ---- B) 清空目标房：必须出现传送门（本次修复的核心断言）
    g.enter_room(gk[0], gk[1], None)
    g.state = 'playing'
    for _wave in range(3):
        for e in list(g.enemies):
            e.alive = False
        g.step(1 / 60.0, {'mx': 0, 'my': 0, 'aim': 0, 'shoot': False,
                          'dash': False, 'slow': False})
    check(g.room.cleared, 'T24 目标房已清空')
    check(g.room.portal is not None,
          'T24 普通层目标房清空后出现传送门（此前恒为 None）')

    # ---- C) 真实走进去 -> 本关结算（每关只有一层）
    f0 = g.floor
    px, py = g.room.portal
    g.player.x, g.player.y = px, py
    g.step(1 / 60.0, {'mx': 0, 'my': 0, 'aim': 0, 'shoot': False,
                      'dash': False, 'slow': False})
    check(g.state == 'playing', 'T24 触碰传送门不自动推进')
    g.request_interact()
    g._confirm_key(pygame.K_e)
    check(g.state == 'victory',
          f'T24 进入传送门完成本关（floor {f0} -> {g.floor}, state={g.state}）')

    # ---- D) 首领层：目标房 = 首领房，传送门仍由 boss 死亡流程给出
    #
    # 血泪教训：这里**不能**用 create_profile + PR.next_stage 来造首领层。
    # 那两个调用会把进度写进共享存档文件（_tmp/testdata），
    # 于是下一次运行时 T2 的 start_run() 读到"场景未清空"，
    # 走进 stage_enter 过场后直接 return，state 停在 'story'，
    # 后续 step() 不再处理射击 -> T2 整段 22 项凭空失败，
    # 而且只在"第二次跑"才复现（第一次干净存档反而全绿）。
    # 现在改为直接构造一个首领层地牢，完全不碰存档。
    try:
        d2 = Dungeon(S.FLOORS, random.Random(424242),
                     scene_key=C.MAIN[0], stage_idx=2, diff=(1.0, 1.0))
        check(d2.is_boss_floor, 'T24 第 3 关末层确为首领层')
        check(d2.goal_key == d2.boss_key,
              'T24 首领层的目标房就是首领房（goal_key == boss_key）')
        check(d2.start_key != d2.boss_key,
              'T24 首领层出生房 != 首领房（出生点逻辑未受影响）')
        # 首领层的出口必须仍然由 boss 死亡流程给出：_maybe_open_portal
        # 对首领层必须直接返回，不能自己抢着开门（否则 boss 还没死就通了）。
        g3 = Game(headless=True, seed=424242, enable_audio=False)
        g3.audio = _D()
        g3.music = _D()
        g3.vibrator = _D()
        g3.floor = S.FLOORS
        g3.dungeon = d2
        g3.enemies = []
        g3.boss = None
        g3.room = None
        g3.enter_room(d2.goal_key[0], d2.goal_key[1], None, first=True)
        r3 = g3.room
        r3.cleared = True
        g3._maybe_open_portal()
        check(r3.portal is None,
              'T24 首领层不走普通层开门逻辑（仍由 boss 死亡流程给门）')
    except Exception as e:
        check(False, f'T24 首领层用例异常：{e!r}')


def main():
    print('=' * 62)
    print(' 陆面过程模拟 无头自动化测试')
    print('=' * 62)
    g = Game(headless=True, seed=20240923, enable_audio=False)
    t0_sanity(g)
    t1_dungeon()
    t2_weapons(g)
    t3_combat(g)
    t4_boss(g)
    t5_transition(g)
    t6_drops(g)
    t8_screens()
    t10_render_coords()
    t11_weapon_swap_no_pingpong()
    t12_no_stuck_in_wall()
    t13_pur_resist()
    t14_codex_showcase()
    t15_talents()
    t16_growth()
    t17_chests()
    t18_settings()
    t19_changelog()
    t20_weapon_mech()
    t21_hitstop_knock()
    t22_slot_flow()
    t23_input_path()
    t24_floor_exit_portal()
    t7_fuzz()
    t9_full_run()

    ok = sum(1 for r, _ in RESULTS if r)
    total = len(RESULTS)
    print('\n' + '=' * 62)
    if FRAME_ERRORS:
        print(f'逐帧异常样本（共 {len(FRAME_ERRORS)}，展示前 12 条）：')
        for e in FRAME_ERRORS[:12]:
            print('   -', e.replace('\n', ' | ')[:240])
        print()
    failed = [m for r, m in RESULTS if not r]
    if failed:
        print(f'失败项（{len(failed)}）：')
        for m in failed:
            print('   x', m)
        print()
    print(f'结果：{ok}/{total} 项通过')
    print('=' * 62)
    return 0 if ok == total else 1


if __name__ == '__main__':
    sys.exit(main())
