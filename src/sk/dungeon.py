# -*- coding: utf-8 -*-
"""地牢生成：随机游走布局 + 房间类型分配 + 刷怪/掉落计划"""
from collections import deque

from . import settings as S
from . import utils as U
from . import weapon as W
from . import hazard as H
from .room import Room

DIRS4 = ((1, 0), (-1, 0), (0, 1), (0, -1))

# ---------------------------------------------------------------- 刷怪表
# 需求 8：**每个场景的怪不同**。
#
# 旧版按 floor(1/2/3) 选怪，导致 7 个场景刷的其实是同一批怪 ——
# 这是"换皮不换肉"。现在改成按 scene_key 取表，floor 只影响数量与强度。
#
# 表结构：scene_key -> (小怪权重表, 精英权重表)
# 权重表里的 key 与 codex.ENEMY_CODEX 完全一致。
SCENE_SPAWN = {
    'crust':    ([('slime', 0.34), ('slug', 0.27), ('crawler', 0.19), ('scatter_raider', 0.20)],
                 [('slime_big', 0.46), ('slug_big', 0.30),
                  ('crawler_big', 0.24)]),
    'sewer':    ([('slug', 0.30), ('drone', 0.27), ('leech', 0.21), ('rifle_raider', 0.22)],
                 [('drone_big', 0.46), ('slug_big', 0.28),
                  ('leech_big', 0.26)]),
    'facility': ([('drone', 0.29), ('bomber', 0.27), ('turret', 0.24), ('beam_raider', 0.20)],
                 [('bomber_big', 0.44), ('drone_big', 0.30),
                  ('turret_big', 0.26)]),
    'core':     ([('spore', 0.28), ('wraith', 0.29), ('frostbite', 0.25), ('beam_raider', 0.18)],
                 [('wraith_big', 0.40), ('spore_big', 0.32),
                  ('spore_big_m', 0.28)]),
    'd_mine':   ([('rockworm', 0.30), ('minebot', 0.27), ('slug', 0.23), ('scatter_raider', 0.20)],
                 [('slime_big_m', 0.40), ('bomber_big', 0.32),
                  ('rockworm_big', 0.28)]),
    'd_lab':    ([('frostbite', 0.27), ('spore', 0.27), ('wraith', 0.24), ('rifle_raider', 0.22)],
                 [('spore_big', 0.40), ('wraith_big', 0.32),
                  ('frostbite_big', 0.28)]),
    'd_gift':   ([('purifier', 0.5), ('sprite', 0.5)],
                 [('guardian_big', 1.0)]),
}

# 场景 -> boss key（第 3 关小 boss / 第 5 关大 boss 用同一个 key，
# 由 enemy.Boss.setup_scene 按 stage_idx 决定是否强化）
# 场景 -> boss key（第 3 关小 boss / 第 5 关大 boss 用同一个 key，
# 由 enemy.Boss.setup_scene 按 stage_idx 决定是否强化）
# core 是终局场景，小 boss / 大 boss 用两个不同 key（协议残片 -> 污染原点本体）。
SCENE_BOSS = {
    'crust': 'warlord', 'sewer': 'swarmqueen', 'facility': 'mech',
    'core': 'origin', 'd_mine': 'foreman', 'd_lab': 'specimen',
    'd_gift': 'guardian',
}
# 小 Boss（第 3 关，stage_idx=2）专用 key；缺省时复用 SCENE_BOSS。
SCENE_MINIBOSS = {
    'crust': 'crust_sentinel', 'sewer': 'sewer_serpent',
    'facility': 'facility_smelter', 'core': 'protocol',
    'd_mine': 'mine_excavator', 'd_lab': 'lab_cryowarden',
    'd_gift': 'gift_bloom',
}

# 兜底：没有 scene_key 时（无头测试等）退化成通用表
SPAWN_TABLE = {
    1: [('slime', 0.72), ('bomber', 0.28)],
    2: [('slime', 0.44), ('bomber', 0.24), ('drone', 0.32)],
    3: [('slime', 0.28), ('bomber', 0.26), ('drone', 0.46)],
}
ELITE_CHANCE = {1: 0.08, 2: 0.13, 3: 0.18}
SCENE_ELITE_CHANCE = {
    'crust': 0.08, 'sewer': 0.12, 'facility': 0.16, 'core': 0.20,
    'd_mine': 0.14, 'd_gift': 0.12, 'd_lab': 0.18,
}
SCENE_CHEST_BIAS = {
    'crust': 0.00, 'sewer': 0.15, 'facility': 0.30, 'core': 0.45,
    'd_mine': 0.20, 'd_gift': 0.30, 'd_lab': 0.35,
}
# Number of enemies in EACH wave, rather than the whole room.
ENEMY_COUNT = {1: (5, 6), 2: (5, 7), 3: (6, 8)}


def _weighted(rng, table):
    total = sum(w for _, w in table)
    p = rng.uniform(0, total)
    acc = 0.0
    for k, w in table:
        acc += w
        if p <= acc:
            return k
    return table[-1][0]


class Dungeon:
    def __init__(self, floor, rng, scene_key=None, stage_idx=0, diff=(1.0, 1.0), drink_stage=False, luck_bonus=0.0):
        self.floor = max(1, min(S.FLOORS, int(floor)))
        self.rng = rng
        self.scene_key = scene_key
        self.stage_idx = int(stage_idx)
        self.diff = diff
        self.drink_stage = bool(drink_stage)
        self.luck_bonus = float(luck_bonus or 0.0)
        self.gw, self.gh = S.GRID_W, S.GRID_H
        self.rooms = {}
        self.start_key = None
        self.boss_key = None
        self.is_boss_floor = False   # 本层是否含首领房（第3关/第5关的最后一层）
        self.goal_key = None         # 本层目标房：清空后开传送门
        self._generate()

    # -------------------------------------------------- 工具
    def room(self, gx, gy):
        return self.rooms.get((int(gx), int(gy)))

    def _bfs(self, src):
        dist = {src: 0}
        q = deque([src])
        while q:
            c = q.popleft()
            r = self.rooms.get(c)
            if r is None:
                continue
            for d in r.doors:
                dv = S.DIR_VEC[d]
                n = (c[0] + dv[0], c[1] + dv[1])
                if n in self.rooms and n not in dist:
                    dist[n] = dist[c] + 1
                    q.append(n)
        return dist

    def _has_boss_floor(self):
        """本层要不要放首领房。

        需求 3 / 8：第 3 关末尾小 Boss、第 5 关末尾大 Boss —— 且只在
        **该关的最后一层**（floor == FLOORS）。普通关的三层都是战斗房。
        """
        try:
            from . import chapter as C
            kind = C.stage_kind(self.stage_idx)
        except Exception:
            kind = 'normal'
        return kind in ('miniboss', 'boss') and self.floor >= S.FLOORS

    def boss_kind(self):
        """本层首领的 key（小 Boss 与 大 Boss 可不同）。"""
        if not self.is_boss_floor:
            return None
        try:
            from . import chapter as C
            k = C.stage_kind(self.stage_idx)
        except Exception:
            k = 'boss'
        if k == 'miniboss':
            return SCENE_MINIBOSS.get(self.scene_key) or SCENE_BOSS.get(
                self.scene_key)
        return SCENE_BOSS.get(self.scene_key)

    def _spawn_tables(self):
        """返回 (小怪权重表, 精英权重表)。

        需求 8：优先用场景专属表；没有 scene_key（无头测试）或表缺失时
        退回按 floor 的通用表，保证任何调用路径都不会拿不到怪。
        """
        spec = SCENE_SPAWN.get(self.scene_key)
        if spec:
            small, elite = spec
            if small:
                return (small, elite)
        return (SPAWN_TABLE[self.floor], [])

    def _sample_pos(self, occupied, min_d, avoid, tries=200):
        for _ in range(tries):
            x = self.rng.uniform(S.IN_L + 30, S.IN_R - 30)
            y = self.rng.uniform(S.IN_T + 30, S.IN_B - 30)
            if any(U.dist(x, y, ox, oy) < min_d for ox, oy in occupied):
                continue
            if any(U.dist(x, y, ax, ay) < ad for ax, ay, ad in avoid):
                continue
            return x, y
        return None

    # -------------------------------------------------- 生成
    def _generate(self):
        rng = self.rng
        cx, cy = self.gw // 2, self.gh // 2
        start = (cx, cy)
        target = {1: 8, 2: 9, 3: 10}[self.floor]
        target = min(target, self.gw * self.gh - 1)

        cells = {start}
        cur = start
        steps = 0
        while len(cells) < target and steps < 600:
            steps += 1
            dx, dy = rng.choice(DIRS4)
            nx, ny = cur[0] + dx, cur[1] + dy
            if 0 <= nx < self.gw and 0 <= ny < self.gh:
                cur = (nx, ny)
                cells.add(cur)

        # 方向 -> 门
        door_map = {c: set() for c in cells}
        for (gx, gy) in cells:
            for d, (vx, vy) in S.DIR_VEC.items():
                if (gx + vx, gy + vy) in cells:
                    door_map[(gx, gy)].add(d)

        # 房间对象
        for c in cells:
            self.rooms[c] = Room(c[0], c[1], 'normal', door_map[c], rng, self.floor)
            self.rooms[c].scene_key = self.scene_key

        self.start_key = start
        self.rooms[start].kind = 'start'
        self.rooms[start].cleared = True

        dist = self._bfs(start)
        far = sorted(dist.keys(), key=lambda k: (-dist[k], k[0], k[1]))
        boss_key = far[0] if far else start
        if boss_key == start:
            others = [k for k in cells if k != start]
            boss_key = others[0] if others else start

        # 需求 3 / 8：**只有第 3 关（小 Boss）与第 5 关（大 Boss）的最后一层**
        # 才保留首领房。普通关的"最远房"降级为普通战斗房，避免每层都撞 Boss。
        self.is_boss_floor = self._has_boss_floor()
        # goal_key = 本层的"目标房"：清空它会开出通往下一层的传送门。
        #   · 首领层 -> 首领房（由 on_boss_defeated 开传送门）
        #   · 普通层 -> 最远的那间战斗房（由 _update_playing 的房间清空判定开传送门）
        # 血泪教训：此前普通层 boss_key 直接置 None，结果"打光所有房间
        # 也永远没有传送门"——玩家被永久困在同一层（用户报的
        # "普通关卡结束后给了钥匙却没有传送门"）。
        self.goal_key = boss_key
        if self.is_boss_floor:
            self.boss_key = boss_key
            self.rooms[boss_key].kind = 'boss'
            self.rooms[boss_key].cleared = False
        else:
            # 不设首领房，但保留 boss_key 供小地图/逻辑引用（指向最远房）
            self.boss_key = None

        # 特殊房（按离出生点的距离就近分配）
        rest = sorted([k for k in cells if k not in (start, boss_key)],
                      key=lambda k: (dist.get(k, 99), k[0], k[1]))
        specials = ['treasure', 'shop', 'heal']
        if self.drink_stage:
            specials.append('drink')
        for i, k in enumerate(rest):
            if i < len(specials):
                self.rooms[k].kind = specials[i]
                self.rooms[k].cleared = True

        for k, r in self.rooms.items():
            self._plan_room(r)

    # -------------------------------------------------- 单房间内容计划
    def _plan_room(self, r):
        rng = self.rng
        f = self.floor
        avoid = [(p[0], p[1], 96.0) for p in S.ENTRY_FROM.values()]
        # 中心区域也不要堆怪，给玩家反应空间
        avoid.append((S.ROOM_CX, S.ROOM_CY, 46.0))
        occupied = []

        if r.kind in ('normal', 'boss'):
            r.wave_plans = [[], [], []]
            small_tbl, elite_tbl = self._spawn_tables()
            boss_pos = (S.ROOM_CX, S.IN_T + 92)
            for wave_index in range(3):
                wave_occupied = []
                is_boss_wave = r.kind == 'boss' and wave_index == 2
                count = rng.randint(*ENEMY_COUNT[f]) - int(is_boss_wave)
                wave_avoid = avoid + ([(boss_pos[0], boss_pos[1], 62.0)]
                                      if is_boss_wave else [])
                for _ in range(count):
                    pos = self._sample_pos(wave_occupied, 42.0, wave_avoid)
                    if pos is None:
                        raise RuntimeError('Unable to place a complete combat wave')
                    wave_occupied.append(pos)
                    occupied.append(pos)
                    elite_p = SCENE_ELITE_CHANCE.get(self.scene_key, ELITE_CHANCE[f])
                    elite = rng.random() < elite_p
                    table = elite_tbl if elite and elite_tbl else small_tbl
                    spawn = (_weighted(rng, table), pos[0], pos[1], elite)
                    r.wave_plans[wave_index].append(spawn)
                    r.spawn_plan.append(spawn)
                if is_boss_wave:
                    bkey = self.boss_kind() or SCENE_BOSS.get(self.scene_key) or 'boss'
                    spawn = (bkey, boss_pos[0], boss_pos[1], False)
                    r.wave_plans[wave_index].append(spawn)
                    r.spawn_plan.append(spawn)

        # 隐藏奖励怪（需求 8）：极小概率把某个普通房换成奖励怪。
        # 拟态宝箱伪装成宝箱；拾荒旅人不主动攻击但可掉红色图纸。
        if r.kind == 'normal' and self.scene_key != 'd_gift':
            roll = rng.random()
            if roll < 0.035:
                pos = self._sample_pos([(sp[1], sp[2]) for sp in r.wave_plans[0]],
                                       42.0, avoid)
                if pos is not None:
                    occupied.append(pos)
                    spawn = ('mimic', pos[0], pos[1], False)
                    r.spawn_plan.append(spawn)
                    r.wave_plans[0].append(spawn)
                    r.rare_mob = 'mimic'
            elif roll < 0.055:
                pos = self._sample_pos([(sp[1], sp[2]) for sp in r.wave_plans[0]],
                                       42.0, avoid)
                if pos is not None:
                    occupied.append(pos)
                    spawn = ('wanderer', pos[0], pos[1], False)
                    r.spawn_plan.append(spawn)
                    r.wave_plans[0].append(spawn)
                    r.rare_mob = 'wanderer'
            elif roll < 0.085:
                pos = self._sample_pos([(sp[1], sp[2]) for sp in r.wave_plans[0]],
                                       42.0, avoid)
                if pos is not None:
                    spawn = ('lucky_treasure', pos[0], pos[1], False)
                    r.spawn_plan.append(spawn)
                    r.wave_plans[0].append(spawn)
                    r.rare_mob = 'lucky_treasure'

        if r.kind == 'boss':
            pass  # Boss and guards are planned in the third wave above.

        elif r.kind == 'treasure':
            # 需求 7：宝箱分 5 类 × 2 档，越深越容易出极品
            from . import gamedata as GD
            bias = (0.10 * max(0, (f - 1))
                    + SCENE_CHEST_BIAS.get(self.scene_key, 0.0)
                    + float(getattr(self, 'luck_bonus', 0.0) or 0.0))
            ckey, ctier = GD.roll_chest(rng, floor_bias=bias)
            r.pickup_plan.append(dict(x=S.ROOM_CX, y=S.ROOM_CY, kind='chest',
                                      ckey=ckey, ctier=ctier))

        elif r.kind == 'heal':
            r.pickup_plan.append(dict(x=S.ROOM_CX - 34, y=S.ROOM_CY, kind='heart', value=2))
            r.pickup_plan.append(dict(x=S.ROOM_CX + 34, y=S.ROOM_CY, kind='heart', value=2))
            r.pickup_plan.append(dict(x=S.ROOM_CX, y=S.ROOM_CY + 48, kind='energy', value=40))

        elif r.kind == 'shop':
            keys = W.roll_shop_weapons(rng, self.scene_key, 2)
            for x, key in zip((S.ROOM_CX - 66, S.ROOM_CX + 66), keys):
                r.pickup_plan.append(dict(x=x, y=S.ROOM_CY - 28, kind='shop_weapon',
                                          wkey=key, price=W.get(key).price + 20))
            r.pickup_plan.append(dict(x=S.ROOM_CX - 66, y=S.ROOM_CY + 42,
                                      kind='shop_hp_potion', price=45))
            r.pickup_plan.append(dict(x=S.ROOM_CX + 66, y=S.ROOM_CY + 42,
                                      kind='shop_energy_potion', price=35))

        elif r.kind == 'drink':
            for x, y, key, price in ((S.ROOM_CX-76, S.ROOM_CY-32, 'nectar', 180),
                                     (S.ROOM_CX+76, S.ROOM_CY-32, 'dew', 140),
                                     (S.ROOM_CX-76, S.ROOM_CY+48, 'soda', 160),
                                     (S.ROOM_CX+76, S.ROOM_CY+48, 'tea', 180)):
                r.pickup_plan.append(dict(x=x, y=y, kind='drink', ckey=key, price=price))

        # 可破坏道具：远离门、远离房间中心，绝不堵路
        prop_avoid = avoid + [(S.ROOM_CX, S.ROOM_CY, 74.0)]
        prop_avoid += [(p['x'], p['y'], 42.0) for p in r.pickup_plan]
        nprops = 2 if r.kind == 'boss' else rng.randint(0, 3)
        if r.kind not in ('normal', 'boss'):
            nprops = rng.randint(0, 2)
        for _ in range(nprops):
            pos = self._sample_pos(occupied, 46.0, prop_avoid)
            if pos is None:
                break
            occupied.append(pos)
            r.prop_plan.append(('crate' if r.kind not in ('normal', 'boss') or rng.random() < 0.62 else 'barrel',
                                pos[0], pos[1]))

        # ---- 需求 3：陷阱 / 掩体 / 奖励洞穴
        if self.scene_key is not None and r.kind in ('normal', 'boss'):
            r.hazard_plan = H.plan_scene(rng, self.scene_key, self.stage_idx,
                                         self.diff)
            r.hazard_plan['strips'] = H.plan_speed_strips(rng, r.hazard_plan)
            # 掩体占位纳入 occupied，避免与箱子叠在一起
            for _k, hx, hy, _hp in r.hazard_plan.get('covers', ()):
                occupied.append((hx, hy))

    # -------------------------------------------------- 小地图用
    def map_cells(self):
        return sorted(self.rooms.keys(), key=lambda k: (k[1], k[0]))
