# -*- coding: utf-8 -*-
"""子弹 / 投射物 / 爆炸"""
import math

import pygame

from . import settings as S
from . import utils as U


def weapon_impact(game, enemy, vfx, damage, x, y):
    """2.0: elemental weapon behaviors shared by ranged and melee attacks."""
    if not enemy.alive or getattr(enemy, 'invuln', False):
        return
    if vfx == 'rad_star':
        enemy.dot_t = max(getattr(enemy, 'dot_t', 0.0), 1.8)
        enemy.dot_dps = max(getattr(enemy, 'dot_dps', 0.0), damage * .24)
        game.fx.burst(enemy.x, enemy.y, (255, 242, 175), n=8, speed=92,
                      life=.35, size=3)
    elif vfx == 'rad_nova':
        for other in game.enemies:
            if other is not enemy and other.alive and \
                    (other.x - enemy.x) ** 2 + (other.y - enemy.y) ** 2 < 76 ** 2:
                other.take_damage(max(1.0, damage * .18), game, enemy.x, enemy.y)
        game.fx.ring(enemy.x, enemy.y, 6, 76, .28, (255, 237, 181), 3)
    elif vfx == 'rad_chrono' and not getattr(enemy, 'is_boss', False):
        if getattr(enemy, 'slow_t', 0.0) <= 0:
            enemy._slow_base_speed = enemy.speed
            enemy.speed *= .45
        enemy.slow_t = max(getattr(enemy, 'slow_t', 0.0), 2.2)
        game.fx.ring(enemy.x, enemy.y, 3, enemy.radius + 16, .35,
                     (174, 238, 255), 2)
    elif vfx == 'rad_life':
        pl = game.player
        now = float(getattr(game, 'time', 0.0))
        if now >= float(getattr(pl, '_rad_heal_at', -1.0)) and pl.hp < pl.max_hp:
            pl.hp = min(pl.max_hp, pl.hp + .45)
            pl._rad_heal_at = now + .55
            game.fx.text(pl.x, pl.y - 28, '+生命', (188, 255, 182),
                         game.assets.font(11), .55)
        game.fx.burst(enemy.x, enemy.y, (188, 255, 182), n=5,
                      speed=64, life=.28, size=2)
    elif vfx == 'rad_prism':
        near = sorted((other for other in game.enemies if other is not enemy
                       and other.alive and (other.x - enemy.x) ** 2 +
                       (other.y - enemy.y) ** 2 < 142 ** 2),
                      key=lambda other: (other.x - enemy.x) ** 2 +
                      (other.y - enemy.y) ** 2)
        for other in near[:2]:
            other.take_damage(max(1.0, damage * .24), game, enemy.x, enemy.y)
            game.fx.burst(other.x, other.y, (229, 187, 255), n=5,
                          speed=80, life=.22, size=2)
    elif vfx == 'rad_orbit':
        for other in game.enemies:
            if other is enemy or not other.alive or getattr(other, 'is_boss', False):
                continue
            dx, dy = enemy.x - other.x, enemy.y - other.y
            distance = math.hypot(dx, dy)
            if 12 < distance < 135:
                other.kx += dx / distance * 110
                other.ky += dy / distance * 110
        game.fx.ring(enemy.x, enemy.y, 7, 70, .35, (181, 204, 255), 2)
    elif vfx.startswith('v30_'):
        seed = sum(map(ord, vfx))
        color = ((seed * 7) % 128 + 110, (seed * 11) % 128 + 110,
                 (seed * 13) % 128 + 110)
        game.fx.burst(enemy.x, enemy.y, color, n=4 + seed % 5,
                      speed=65 + seed % 50, life=.22 + seed % 3 * .05,
                      size=2 + seed % 2)
    elif vfx == 'frost' and not getattr(enemy, 'is_boss', False):
        if getattr(enemy, 'slow_t', 0.0) <= 0:
            enemy._slow_base_speed = enemy.speed
            enemy.speed *= 0.62
        enemy.slow_t = max(getattr(enemy, 'slow_t', 0.0), 1.3)
        game.fx.ring(enemy.x, enemy.y, 3, enemy.radius + 9, .25,
                     (136, 226, 255), 2)
    elif vfx in ('acid', 'flame', 'ember', 'sun'):
        enemy.dot_t = max(getattr(enemy, 'dot_t', 0.0), 2.0)
        enemy.dot_dps = max(getattr(enemy, 'dot_dps', 0.0), damage * .17)
        game.fx.burst(enemy.x, enemy.y, (160, 243, 103) if vfx == 'acid'
                      else (255, 142, 73), n=3, speed=45, life=.28, size=2)
    elif vfx in ('arc', 'volt', 'coil'):
        other = min((e for e in game.enemies if e is not enemy and e.alive and
                     (e.x - enemy.x) ** 2 + (e.y - enemy.y) ** 2 < 120 ** 2),
                    key=lambda e: (e.x - enemy.x) ** 2 + (e.y - enemy.y) ** 2,
                    default=None)
        if other is not None:
            other.take_damage(max(1.0, damage * .28), game, enemy.x, enemy.y)
            game.fx.burst(other.x, other.y, (112, 236, 255), n=4,
                          speed=70, life=.2, size=2)
    elif vfx == 'gravity':
        for other in game.enemies:
            if other is enemy or not other.alive or getattr(other, 'is_boss', False):
                continue
            dx, dy = x - other.x, y - other.y
            dist = math.hypot(dx, dy)
            if 12 < dist < 110:
                other.kx += dx / dist * 65
                other.ky += dy / dist * 65


def explode(game, x, y, radius, dmg, hurt_player=True, color=(255, 168, 72),
            bomber=False):
    """范围伤害 + 特效。统一入口，避免各处重复实现导致行为不一致。
    带递归深度保护：连环爆炸（炸弹机器人互相引爆）不会无限递归。

    bomber=True 表示这是"自爆囊/爆破工头"的爆炸——命中玩家时会计入
    副本准入条件里的"被自爆波及"次数（需求）。
    """
    if radius <= 0:
        return
    game.fx.ring(x, y, radius * 0.25, radius * 1.05, 0.34, color, 3)
    game.fx.burst(x, y, color, n=20, speed=radius * 4.2, life=0.42, size=4,
                  drag=2.6, shape='circle')
    game.fx.burst(x, y, (250, 240, 200), n=10, speed=radius * 3.0,
                  life=0.26, size=3, drag=3.4, shape='circle')
    game.fx.smoke(x, y, n=8)
    game.audio.play('explode')
    game.fx.add_shake(min(9.0, radius * 0.20))
    game.fx.add_flash(0.16, color)

    depth = getattr(game, '_explode_depth', 0)
    if depth >= 4:
        return
    game._explode_depth = depth + 1
    try:
        for e in list(game.enemies):
            if not e.alive:
                continue
            d = U.dist(x, y, e.x, e.y)
            if d < radius + e.radius:
                f = 1.0 - 0.55 * (d / max(1.0, radius + e.radius))
                e.take_damage(dmg * f, game, x, y)
        for p in list(game.props):
            if p.alive and U.dist(x, y, p.x, p.y) < radius + p.radius:
                p.take_damage(dmg, game, x, y)
        # 掩体（需求 3）：只有爆炸能摧毁，普通子弹打不动
        if game.room is not None:
            for cv in list(game.room.covers):
                if cv.alive and U.dist(x, y, cv.x, cv.y) < radius + cv.radius:
                    cv.take_damage(dmg * 1.6, game, x, y)
        if hurt_player and game.player.alive:
            d = U.dist(x, y, game.player.x, game.player.y)
            if d < radius + game.player.radius:
                if game.player.take_damage(max(1.0, dmg * 0.28), game, x, y):
                    if bomber and hasattr(game, 'on_bomber_hit'):
                        game.on_bomber_hit(None)
    finally:
        game._explode_depth = depth


class Bullet:
    __slots__ = ('x', 'y', 'vx', 'vy', 'ang', 'dmg', 'friendly', 'img', 'size',
                 'radius', 'pierce', 'aoe', 'life', 'color', 'alive', 'hits',
                 'hit_shake', 'exploded', 'trail', 'mech', 'dmg_mul', 'vfx')

    def __init__(self, x, y, ang, speed, dmg, friendly=True, img='b_bullet',
                 size=14, radius=5.0, pierce=0, aoe=0.0, life=1.3,
                 color=(255, 214, 120), hit_shake=0.8):
        self.x, self.y = float(x), float(y)
        self.ang = float(ang)
        self.vx = math.cos(ang) * speed
        self.vy = math.sin(ang) * speed
        self.dmg = float(dmg)
        self.friendly = bool(friendly)
        self.img = img
        self.size = int(size)
        self.radius = float(radius)
        self.pierce = int(pierce)
        self.aoe = float(aoe)
        self.life = float(life)
        self.color = color
        self.alive = True
        self.hits = set()
        self.hit_shake = hit_shake
        self.exploded = False
        self.trail = 0.0
        # 需求 6（1.4）：品质机制。{'burst':n,'split':n,'homing':rad/s}
        self.mech = {}
        # 分裂/迸射出的子弹出膛时继承的伤害倍率（默认 1.0）
        self.dmg_mul = 1.0
        self.vfx = 'spark'

    # -------------------------------------------------- 生命周期
    def kill(self, game, impact=True):
        if not self.alive:
            return
        self.alive = False
        if self.aoe > 0 and not self.exploded:
            self.exploded = True
            explode(game, self.x, self.y, self.aoe, self.dmg,
                    hurt_player=(not self.friendly))
        elif impact:
            game.fx.sparks(self.x, self.y, self.color, n=4, ang=self.ang)
            game.fx.burst(self.x, self.y, self.color, n=3, speed=70,
                          life=0.2, size=2, drag=4.0)

    # -------------------------------------------------- 更新
    def update(self, game, dt):
        if not self.alive:
            return
        self.life -= dt
        if self.life <= 0:
            self.kill(game, impact=False)
            return

        # 需求 6（1.4 璀璨级机制）：追猎弹道 —— 轻微转向最近的敌人
        homing = float(self.mech.get('homing', 0.0)) if self.mech else 0.0
        if homing > 0 and self.friendly and game.enemies:
            tgt = None
            best = 1e18
            for e in game.enemies:
                if not e.alive:
                    continue
                d = (e.x - self.x) ** 2 + (e.y - self.y) ** 2
                if d < best:
                    best, tgt = d, e
            if tgt is not None:
                want = math.atan2(tgt.y - self.y, tgt.x - self.x)
                da = (want - self.ang + math.pi) % math.tau - math.pi
                step = max(-homing * dt, min(homing * dt, da))
                self.ang += step
                spd = math.hypot(self.vx, self.vy)
                self.vx = math.cos(self.ang) * spd
                self.vy = math.sin(self.ang) * spd

        nx = self.x + self.vx * dt
        ny = self.y + self.vy * dt

        # 房间外
        if (nx < -24 or nx > S.ROOM_PX_W + 24 or
                ny < -24 or ny > S.ROOM_PX_H + 24):
            self.kill(game, impact=False)
            return

        # 墙体
        if U.circle_solid(nx, ny, self.radius * 0.7, game.room.solid):
            self.kill(game, impact=True)
            return

        # 掩体挡子弹（需求 3：掩体可掩护；但不能被普通子弹打坏）
        if game.room is not None:
            for cv in game.room.covers:
                if not cv.alive:
                    continue
                rr = self.radius + cv.radius
                if (nx - cv.x) ** 2 + (ny - cv.y) ** 2 < rr * rr:
                    game.fx.sparks(nx, ny, (196, 192, 178), n=4,
                                   ang=self.ang + math.pi)
                    self.kill(game, impact=False)
                    return

        self.x, self.y = nx, ny

        # 拖尾
        self.trail -= dt
        if self.trail <= 0 and self.aoe <= 0:
            self.trail = 0.045
            game.fx.burst(self.x, self.y, self.color, n=1, speed=18,
                          life=0.16, size=2, drag=4.0)

        # 命中判定
        if self.friendly:
            self._hit_enemies(game)
            if self.alive:
                self._hit_props(game)
        else:
            self._hit_player(game)

    def _hit_enemies(self, game):
        for e in list(game.enemies):
            if not e.alive or id(e) in self.hits:
                continue
            rr = self.radius + e.radius
            if (self.x - e.x) ** 2 + (self.y - e.y) ** 2 < rr * rr:
                self.hits.add(id(e))
                game.fx.sparks(self.x, self.y, self.color, n=5,
                               ang=self.ang + math.pi)
                hp_before = getattr(e, 'hp', 1.0)
                e.take_damage(self.dmg, game, self.x, self.y)
                weapon_impact(game, e, self.vfx, self.dmg, self.x, self.y)
                flags = (getattr(game, 'run_stats', None) or {}).get('flags') or ()
                if self.aoe <= 0 and 'aoe_bullet' in flags:
                    explode(game, self.x, self.y, 44.0, max(1.0, self.dmg * 0.45),
                            hurt_player=False, color=(255, 160, 80))
                killed = (hp_before > 0 and getattr(e, 'hp', 1.0) <= 0)
                # 需求 6：命中分裂（红/璀璨级）—— 命中后向附近敌人溅射
                self._spawn_split(game)
                if killed:
                    # 需求 6：击杀迸射（金/红/璀璨级）
                    self._spawn_burst(game)
                if self.pierce > 0:
                    self.pierce -= 1
                    self.dmg *= 0.86
                else:
                    self.kill(game, impact=True)
                    return

    def _spawn_split(self, game):
        """命中分裂：向附近敌人各射出一发小弹（继承 55% 伤害）。"""
        n = int(self.mech.get('split', 0)) if self.mech else 0
        if n <= 0 or not self.friendly:
            return
        cands = []
        for e in game.enemies:
            if not e.alive or id(e) in self.hits:
                continue
            d = math.hypot(e.x - self.x, e.y - self.y)
            if d < 150.0:
                cands.append((d, e))
        if not cands:
            return
        cands.sort(key=lambda t: t[0])
        for _d, e in cands[:n]:
            a = math.atan2(e.y - self.y, e.x - self.x)
            b = Bullet(self.x, self.y, a, 460, self.dmg * 0.55,
                       friendly=True, img=self.img, size=self.size,
                       radius=self.radius, pierce=0, aoe=0.0, life=0.7,
                       color=self.color, hit_shake=self.hit_shake * 0.6)
            game.bullets.append(b)

    def _spawn_burst(self, game):
        """击杀迸射：在击杀点向四周散射若干小弹（继承 40% 伤害）。"""
        n = int(self.mech.get('burst', 0)) if self.mech else 0
        if n <= 0 or not self.friendly:
            return
        for i in range(n):
            a = self.ang + (i - (n - 1) * 0.5) * 0.7
            b = Bullet(self.x, self.y, a, 380, self.dmg * 0.40,
                       friendly=True, img=self.img, size=max(8, self.size - 4),
                       radius=max(2.5, self.radius * 0.7), pierce=0, aoe=0.0,
                       life=0.5, color=self.color,
                       hit_shake=self.hit_shake * 0.5)
            game.bullets.append(b)

    def _hit_props(self, game):
        for p in list(game.props):
            if not p.alive or id(p) in self.hits:
                continue
            rr = self.radius + p.radius
            if (self.x - p.x) ** 2 + (self.y - p.y) ** 2 < rr * rr:
                self.hits.add(id(p))
                p.take_damage(self.dmg, game, self.x, self.y)
                game.fx.sparks(self.x, self.y, (210, 180, 120), n=4, ang=self.ang + math.pi)
                if self.pierce > 0:
                    self.pierce -= 1
                else:
                    self.kill(game, impact=True)
                    return

    def _hit_player(self, game):
        pl = game.player
        if not pl.alive or id(pl) in self.hits:
            return
        rr = self.radius + pl.radius
        if (self.x - pl.x) ** 2 + (self.y - pl.y) ** 2 < rr * rr:
            self.hits.add(id(pl))
            pl.take_damage(self.dmg, game, self.x, self.y)
            self.kill(game, impact=True)

    # -------------------------------------------------- 绘制
    def draw(self, surf, cam, assets):
        if not self.alive:
            return
        x, y = self.x + cam[0], self.y + cam[1]
        deg = -math.degrees(self.ang)
        if self.aoe > 0:
            img = assets.rot(self.img, self.size, self.size, deg)
        else:
            img = assets.rot(self.img, self.size, self.size, deg)
        surf.blit(img, (int(x - img.get_width() / 2), int(y - img.get_height() / 2)))
