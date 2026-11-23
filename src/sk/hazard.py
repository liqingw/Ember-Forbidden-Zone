# -*- coding: utf-8 -*-
"""场景交互物：陷阱、掩体、奖励洞穴（需求 3）。

与 Prop（木箱/油桶）的区别
--------------------------
Prop 是"可破坏"的临时物件；这里的三类是**地形级**元素：
  * Trap   陷阱 —— 周期性伤害 / 减速 / 击退，不挡路
  * Cover  掩体 —— 实心，挡人挡子弹，但可被爆炸摧毁
  * Cave   奖励洞穴 —— 藏宝的小凹室，走近自动开启

全部纯逻辑 + 自带绘制，不依赖 Room 之外的模块。
"""
import math

import pygame

from . import settings as S
from . import utils as U
from .pickup import Pickup

_trap_under_cache = {}

# ================================================================ 陷阱
# kind: spike 地刺 / poison 毒池 / shock 电击 / slow 泥沼 / flame 喷焰
TRAP_SPEC = {
    'spike':  {'name': '地刺', 'color': (196, 196, 210), 'dmg': 3,
               'period': 1.6, 'active': 0.7, 'radius': 13, 'w': 34},
    'poison': {'name': '毒池', 'color': (128, 214, 96), 'dmg': 1.4,
               'period': 0.55, 'active': 0.5, 'radius': 17, 'w': 26,
               'slow': 0.55},
    'shock':  {'name': '电场', 'color': (120, 200, 255), 'dmg': 2.4,
               'period': 2.1, 'active': 0.45, 'radius': 16, 'w': 16},
    'slow':   {'name': '泥沼', 'color': (140, 122, 88), 'dmg': 0.0,
               'period': 99.0, 'active': 99.0, 'radius': 18, 'w': 18,
               'slow': 0.48},
    'flame':  {'name': '喷焰口', 'color': (255, 146, 66), 'dmg': 3.6,
               'period': 2.4, 'active': 0.9, 'radius': 14, 'w': 12},
}
TRAP_ORDER = ['spike', 'poison', 'shock', 'slow', 'flame']


class SpeedStrip:
    speed_mul = 1.0
    color = (255, 255, 255)
    name = ''

    def __init__(self, x, y):
        self.x, self.y = float(x), float(y)
        self.radius = 23.0

    def contains(self, x, y):
        return abs(x - self.x) <= 22 and abs(y - self.y) <= 15

    def draw(self, surf, cam):
        x, y = int(self.x + cam[0]), int(self.y + cam[1])
        pygame.draw.rect(surf, self.color, (x - 24, y - 17, 48, 34), 2)
        direction = 1 if self.speed_mul > 1 else -1
        for offset in (-12, 0, 12):
            pygame.draw.lines(surf, self.color, False,
                [(x + offset - 4 * direction, y - 7),
                 (x + offset + 4 * direction, y),
                 (x + offset - 4 * direction, y + 7)], 2)


class SpeedUpStrip(SpeedStrip):
    speed_mul = 1.5
    color = (80, 230, 165)
    name = '加速带'


class SlowDownStrip(SpeedStrip):
    speed_mul = 0.55
    color = (245, 170, 75)
    name = '减速带'


def plan_speed_strips(rng, hazards):
    """One independently modelled strip of each kind in combat rooms."""
    out = []
    occupied = [(x, y) for _, x, y, _ in hazards.get('traps', ())]
    occupied += [(x, y) for _, x, y, _ in hazards.get('covers', ())]
    occupied += [(x, y) for _, x, y in hazards.get('caves', ())]
    for kind in ('up', 'down'):
        for _ in range(30):
            x = rng.uniform(S.IN_L + 50, S.IN_R - 50)
            y = rng.uniform(S.IN_T + 50, S.IN_B - 50)
            if U.dist(x, y, S.ROOM_CX, S.ROOM_CY) < 72:
                continue
            if any(U.dist(x, y, ex, ey) < 72 for ex, ey in S.ENTRY_FROM.values()):
                continue
            if any(U.dist(x, y, a, b) < 65 for a, b in occupied):
                continue
            occupied.append((x, y))
            out.append((kind, x, y))
            break
    return out


class Trap:
    """周期性生效的陷阱。phase 让同一房间的陷阱错开，避免同时爆发。

    active 状态下每帧对玩家做"圆 vs 圆"判定；命中后走沿触发（_was_hit），
    一次激活只结算一次伤害，避免每帧掉血造成瞬间暴毙。
    """

    def __init__(self, x, y, kind='spike', phase=0.0):
        self.x, self.y = float(x), float(y)
        self.kind = kind
        spec = TRAP_SPEC.get(kind, TRAP_SPEC['spike'])
        self.spec = spec
        self.radius = float(spec['radius'])
        self.phase = float(phase)
        self.t = phase
        self.alive = True
        self._was_hit = False        # 沿触发：同一次激活只结算一次
        self.flash = 0.0

    # ---- 是否处于激活（会造成伤害）状态
    @property
    def active(self):
        p = self.spec['period']
        if p <= 0:
            return True
        c = (self.t % p)
        if c > self.spec['active']:
            return False
        # 起爆瞬间的"预警"时间：前 22% 不结算伤害，给玩家反应窗口
        if c < self.spec['active'] * 0.22:
            return False
        return True

    @property
    def warning(self):
        """即将触发（预警亮起）。"""
        p = self.spec['period']
        if p <= 0:
            return False
        c = (self.t % p)
        return 0 < c <= self.spec['active'] * 0.22

    def update(self, game, dt):
        self.t += dt
        if self.flash > 0:
            self.flash = max(0.0, self.flash - dt * 3.0)

        if 'trap_ward' in (getattr(game, 'run_stats', None) or {}).get('flags', ()):
            self._was_hit = False
            return

        pl = game.player
        if not pl.alive or pl.iframes > 0:
            self._was_hit = False
            return
        d = U.dist(self.x, self.y, pl.x, pl.y)
        if d > self.radius + pl.radius:
            self._was_hit = False
            return

        if self.active:
            # 泥沼：只减速不掉血
            if self.kind == 'slow':
                pl.slow_until = 0.12
                return
            if not self._was_hit:
                self._was_hit = True
                self.flash = 1.0
                pl.take_damage(self.spec['dmg'], game, self.x, self.y)
                # 需求：副本准入条件需要统计"踩中陷阱次数"
                game.on_trap_hit(self)
                # 击退：从陷阱中心往外推
                k = 130.0
                a = math.atan2(pl.y - self.y, pl.x - self.x)
                pl.x += math.cos(a) * k * 0.06
                pl.y += math.sin(a) * k * 0.06
        else:
            self._was_hit = False
            if self.kind == 'slow':
                pl.slow_until = 0.12

    # ---- 绘制
    def draw_under(self, surf, cam, assets):
        """画在地面层（角色下方）。"""
        x, y = self.x + cam[0], self.y + cam[1]
        r = int(self.radius)
        on = self.active
        warn = self.warning
        col = self.spec['color']
        icon = assets.scaled('trap_' + self.kind, 32, 32)
        surf.blit(icon, (int(x - 16), int(y - 16)))

        if self.kind == 'poison' or self.kind == 'slow':
            # 地面色斑（按外观参数缓存）
            ckey = ('stain', r, bool(on), bool(warn), tuple(col))
            s = _trap_under_cache.get(ckey)
            if s is None:
                if len(_trap_under_cache) >= 128:
                    _trap_under_cache.clear()
                a = 96 if on else 60
                s = pygame.Surface((r * 3, r * 3), pygame.SRCALPHA)
                for i in range(3):
                    rr = int(r * (0.7 + 0.12 * i))
                    al = int(a * (1 - i * 0.22))
                    pygame.draw.circle(s, (col[0], col[1], col[2], al),
                                       (r * 3 // 2, r * 3 // 2), rr)
                if warn:
                    pygame.draw.circle(s, (255, 240, 180, 70),
                                       (r * 3 // 2, r * 3 // 2), r + 3, 2)
                _trap_under_cache[ckey] = s
            surf.blit(s, (int(x - r * 1.5), int(y - r * 1.5)))
            return

        # 其余：底盘（按半径缓存）
        bkey = ('base', r)
        base = _trap_under_cache.get(bkey)
        if base is None:
            if len(_trap_under_cache) >= 128:
                _trap_under_cache.clear()
            base = pygame.Surface((r * 3, r * 3), pygame.SRCALPHA)
            pygame.draw.circle(base, (24, 22, 30, 150), (r * 3 // 2, r * 3 // 2), r)
            pygame.draw.circle(base, (60, 56, 74, 200), (r * 3 // 2, r * 3 // 2), r, 2)
            _trap_under_cache[bkey] = base
        surf.blit(base, (int(x - r * 1.5), int(y - r * 1.5)))

    def draw_over(self, surf, cam, assets):
        """画在角色层之上（刺、电、火）。"""
        x, y = self.x + cam[0], self.y + cam[1]
        r = int(self.radius)
        on = self.active
        warn = self.warning
        col = self.spec['color']

        if self.kind == 'spike':
            g = U.scratch_surf(r * 3, r * 3)
            n = 5
            up = 8 if on else 2
            for i in range(n):
                a = 2 * math.pi * i / n + self.t * 0.4
                px = r * 1.5 + math.cos(a) * r * 0.62
                py = r * 1.5 + math.sin(a) * r * 0.62
                hgt = up if on else 3
                c = col if on else (110, 108, 120)
                pygame.draw.polygon(g, c, [(px - 3, py + hgt), (px + 3, py + hgt),
                                           (px, py - 5 - hgt)])
            if warn:
                pygame.draw.circle(g, (255, 236, 170, 90),
                                   (r * 3 // 2, r * 3 // 2), r + 2, 2)
            surf.blit(g, (int(x - r * 1.5), int(y - r * 1.5)))

        elif self.kind == 'shock':
            if on:
                g = U.scratch_surf(r * 3, r * 3)
                for i in range(4):
                    a0 = self.t * 3.0 + i * 1.57
                    px = r * 1.5 + math.cos(a0) * r * 0.7
                    py = r * 1.5 + math.sin(a0) * r * 0.7
                    pygame.draw.line(g, (200, 240, 255, 210),
                                     (r * 1.5, r * 1.5), (px, py), 2)
                pygame.draw.circle(g, (170, 220, 255, 150),
                                   (r * 3 // 2, r * 3 // 2), int(r * 0.55))
                surf.blit(g, (int(x - r * 1.5), int(y - r * 1.5)))
            elif warn:
                g = U.scratch_surf(r * 3, r * 3)
                pygame.draw.circle(g, (140, 200, 255, 110),
                                   (r * 3 // 2, r * 3 // 2), r + 2, 2)
                surf.blit(g, (int(x - r * 1.5), int(y - r * 1.5)))

        elif self.kind == 'flame':
            if on:
                t = (self.t % self.spec['period']) / self.spec['active']
                g = U.scratch_surf(r * 3, r * 4)
                hh = int(r * (1.2 + 1.1 * min(1.0, t)))
                for i in range(3):
                    rr = int(r * (0.85 - i * 0.2))
                    al = 180 - i * 50
                    pygame.draw.ellipse(
                        g, (255, 150 + i * 30, 60, al),
                        (r * 3 // 2 - rr, r * 2 - hh, rr * 2, hh))
                surf.blit(g, (int(x - r * 1.5), int(y - r * 2)))
            elif warn:
                g = U.scratch_surf(r * 3, r * 3)
                pygame.draw.circle(g, (255, 190, 120, 110),
                                   (r * 3 // 2, r * 3 // 2), r + 2, 2)
                surf.blit(g, (int(x - r * 1.5), int(y - r * 1.5)))


# ================================================================ 掩体
class Cover:
    """实心掩体：挡人、挡子弹，爆炸可摧毁。"""

    def __init__(self, x, y, kind='pillar', hp=6.0):
        self.x, self.y = float(x), float(y)
        self.kind = kind
        self.alive = True
        self.max_hp = float(hp)
        self.hp = float(hp)
        self.radius = 15.0
        self.hit_flash = 0.0
        self.shake = 0.0

    def blocks_bullet(self):
        return True

    def take_damage(self, dmg, game, sx=None, sy=None):
        if not self.alive:
            return
        self.hp -= dmg
        self.hit_flash = 0.12
        self.shake = 3.2
        game.fx.burst(self.x, self.y, (168, 164, 150), n=5, speed=70,
                      life=0.28, size=3, drag=3.0)
        if self.hp <= 0:
            self.alive = False
            self._break(game)

    def _break(self, game):
        game.audio.play('break')
        game.fx.burst(self.x, self.y, (150, 146, 138), n=22, speed=170,
                      life=0.55, size=5, drag=2.2, grav=230.0)
        game.fx.ring(self.x, self.y, 6, 40, 0.3, (198, 194, 182), 3)
        game.fx.add_shake(3.4)

    def update(self, game, dt):
        self.hit_flash = max(0.0, self.hit_flash - dt)
        if self.shake > 0:
            self.shake = max(0.0, self.shake - 26.0 * dt)

    def draw(self, surf, cam, assets):
        if not self.alive:
            return
        size = 34
        sx = math.sin(self.shake * 3.6) * (self.shake / 3.2) * 1.8 if self.shake else 0.0
        x, y = self.x + cam[0] + sx, self.y + cam[1]
        U.draw_shadow(surf, x, y + 12, 15, 7, 150)
        key = 'cover_pillar' if self.kind == 'pillar' else 'cover_block'
        img = assets.scaled(key, size, size)
        surf.blit(img, (int(x - size / 2), int(y - size / 2)))
        if self.hit_flash > 0:
            U.blit_hit_flash(surf, img, (int(x - size / 2), int(y - size / 2)),
                             int(160 * (self.hit_flash / 0.12)))
        # 血条（受损后显示）
        if self.hp < self.max_hp:
            w = 22
            r = max(0.0, self.hp / self.max_hp)
            pygame.draw.rect(surf, (40, 38, 50), (int(x - w / 2), int(y - size / 2 - 6), w, 3))
            pygame.draw.rect(surf, (200, 190, 150),
                             (int(x - w / 2), int(y - size / 2 - 6), int(w * r), 3))


# ================================================================ 奖励洞穴
class Cave:
    """藏宝小凹室：走近（或击败守卫）自动开启，掉落一份奖励。"""

    def __init__(self, x, y, loot_kind='coin', amount=40):
        self.x, self.y = float(x), float(y)
        self.loot_kind = loot_kind
        self.amount = amount
        self.alive = True
        self.opened = False
        self.t = 0.0
        self.life = -1.0
        self.radius = 20.0

    def update(self, game, dt):
        self.t += dt
        if self.opened or not self.alive:
            return
        pl = game.player
        if not pl.alive:
            return
        if U.dist(self.x, self.y, pl.x, pl.y) < self.radius + pl.radius:
            self.opened = True
            self.alive = False
            self._pop(game)

    def _pop(self, game):
        k = self.loot_kind
        rng = game.rng
        if k == 'coin':
            for _ in range(rng.randint(3, 6)):
                a = rng.uniform(0, math.tau)
                d = rng.uniform(8, 30)
                game.pickups.append(Pickup(self.x + math.cos(a) * d,
                                           self.y + math.sin(a) * d, 'coin', 1))
        elif k == 'material':
            game.grant_material(rng.choice(['scrap', 'fiber', 'circuit',
                                            'crystal']), rng.randint(1, 2))
        elif k == 'heal':
            game.pickups.append(Pickup(self.x, self.y, 'heart', 3))
            game.pickups.append(Pickup(self.x + 18, self.y, 'energy', 40))
        game.audio.play('level_up')
        game.fx.ring(self.x, self.y, 6, 46, 0.4, (255, 226, 150), 3)
        game.fx.burst(self.x, self.y, (255, 220, 140), n=18, speed=140,
                      life=0.5, size=4, drag=2.6)
        game.toast('发现奖励洞穴', '拿到了藏在这里的东西', (255, 226, 150))

    def draw(self, surf, cam, assets):
        if not self.alive:
            return
        x, y = self.x + cam[0], self.y + cam[1]
        r = int(self.radius)
        s = U.scratch_surf(r * 3, r * 3)
        pygame.draw.circle(s, (18, 16, 24, 210), (r * 3 // 2, r * 3 // 2), r)
        pygame.draw.circle(s, (196, 168, 110, 190), (r * 3 // 2, r * 3 // 2), r, 2)
        pulse = 0.5 + 0.5 * math.sin(self.t * 3.0)
        pygame.draw.circle(s, (255, 226, 150, int(60 + 70 * pulse)),
                           (r * 3 // 2, r * 3 // 2), int(r * 0.5))
        surf.blit(s, (int(x - r * 1.5), int(y - r * 1.5)))


# ================================================================ 动态毒雾
class PoisonCloud:
    """孢殖体死亡后残留的毒雾（需求 8）。

    与 Trap 的区别：Trap 是**关卡生成时就固定**的地形；毒雾是
    **战斗中动态产生**的，玩家自己的击杀会改变战场 —— 这让"清怪顺序"
    变成一种战术选择（先杀哪只会决定哪片区域被封）。
    """

    def __init__(self, x, y, radius=46.0, life=4.0, color=(150, 210, 110),
                 dmg=1.4):
        self.x, self.y = float(x), float(y)
        self.radius = float(radius)
        self.life = float(life)
        self.max_life = float(life)
        self.color = color
        self.dmg = float(dmg)
        self.t = 0.0
        self.alive = True
        self._tick = 0.0

    @property
    def fade(self):
        """0（刚生成）-> 1（消散）：用于绘制透明度。"""
        if self.max_life <= 0:
            return 1.0
        return max(0.0, min(1.0, 1.0 - self.life / self.max_life))

    def update(self, game, dt):
        """返回 False 表示已消散，可以回收。"""
        if not self.alive:
            return False
        self.t += dt
        self.life -= dt
        if self.life <= 0:
            self.alive = False
            return False
        pl = game.player
        if pl is not None and pl.alive:
            if U.dist(self.x, self.y, pl.x, pl.y) < self.radius + pl.radius:
                # 每 0.5 秒结算一次，避免逐帧掉血
                self._tick -= dt
                if self._tick <= 0:
                    self._tick = 0.5
                    pl.take_damage(self.dmg, game, self.x, self.y)
        return True

    def draw(self, surf, cam, assets):
        if not self.alive:
            return
        x, y = self.x + cam[0], self.y + cam[1]
        r = int(self.radius)
        fade = self.fade
        alpha = int(120 * (1.0 - fade) + 24)
        s = U.scratch_surf(r * 2 + 4, r * 2 + 4)
        cx = cy = r + 2
        # 三层同心圆模拟"雾团"
        for i, (rr, aa) in enumerate(((1.0, 0.55), (0.72, 0.75), (0.44, 1.0))):
            wob = 1.0 + math.sin(self.t * 2.2 + i * 1.7) * 0.06
            pygame.draw.circle(s, (self.color[0], self.color[1], self.color[2],
                                   int(alpha * aa)),
                               (cx, cy), max(2, int(r * rr * wob)))
        surf.blit(s, (int(x - cx), int(y - cy)))


def spawn_cloud(game, x, y, radius=46.0, life=4.0, color=(150, 210, 110),
                dmg=1.4):
    """往当前房间投放一片毒雾（供 enemy.SporeBug 等调用）。"""
    r = getattr(game, 'room', None)
    if r is None:
        return None
    cloud = PoisonCloud(x, y, radius, life, color, dmg)
    r.clouds.append(cloud)
    return cloud


# ================================================================ 生成
# 每个场景偏好的陷阱类型（需求 3：不同场景不同机关）
# 提到模块级：chapter.py 的场景叙事绑定要靠它校验"绑定的陷阱确实在这层出现"
TRAP_BY_SCENE = {
    'crust': ['spike', 'flame'],
    'sewer': ['poison', 'slow'],
    'facility': ['shock', 'spike'],
    'core': ['shock', 'flame'],
    'd_mine': ['spike', 'slow'],
    'd_lab': ['shock', 'poison'],
    'd_gift': ['slow'],
}


def plan_scene(rng, scene_key, stage_idx, diff):
    """为某个场景的一关规划陷阱/掩体/洞穴。

    返回 dict:
      {'traps': [(kind,x,y,phase)], 'covers': [(kind,x,y,hp)],
       'caves': [(loot,x,y)]}
    diff 是 chapter.difficulty 返回的 (数量倍率, 强度倍率)。
    """
    qmul, smul = diff
    out = {'traps': [], 'covers': [], 'caves': []}

    pool = TRAP_BY_SCENE.get(scene_key, ['spike'])

    # 奖励副本以"收集"为主，少陷阱
    n_trap = 0 if scene_key == 'd_gift' else int(round(rng.randint(1, 3) * qmul))
    n_cover = int(round(rng.randint(1, 3) * qmul))
    n_cave = 1 if rng.random() < (0.34 if scene_key != 'd_gift' else 0.85) else 0

    avoid = [(p[0], p[1], 84.0) for p in S.ENTRY_FROM.values()]
    avoid.append((S.ROOM_CX, S.ROOM_CY, 52.0))
    occupied = []

    def sample(min_d, tries=50):
        for _ in range(tries):
            x = rng.uniform(S.IN_L + 34, S.IN_R - 34)
            y = rng.uniform(S.IN_T + 34, S.IN_B - 34)
            if any(U.dist(x, y, ox, oy) < min_d for ox, oy in occupied):
                continue
            if any(U.dist(x, y, ax, ay) < ad for ax, ay, ad in avoid):
                continue
            return x, y
        return None

    for i in range(n_trap):
        p = sample(44.0)
        if p is None:
            break
        occupied.append(p)
        out['traps'].append((rng.choice(pool), p[0], p[1],
                             rng.uniform(0.0, 1.4)))

    for _ in range(n_cover):
        p = sample(50.0)
        if p is None:
            break
        occupied.append(p)
        out['covers'].append(('pillar' if rng.random() < 0.6 else 'block',
                              p[0], p[1], 6.0 * smul))

    if n_cave:
        p = sample(52.0)
        if p is not None:
            occupied.append(p)
            loot = rng.choice(['coin', 'coin', 'material', 'heal'])
            amt = 40 + int(20 * smul)
            out['caves'].append((loot, p[0], p[1]))

    return out


def in_trap(x, y, traps):
    """点是否被任意陷阱覆盖（用于避免把怪直接生成在陷阱上）。"""
    for t in traps:
        if U.dist(x, y, t.x, t.y) < t.radius + 8:
            return True
    return False
