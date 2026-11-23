# -*- coding: utf-8 -*-
"""敌人与 Boss"""
import itertools
import math

import pygame

from . import settings as S
from . import utils as U
from .bullet import Bullet, explode
from .pickup import Pickup

_uid = itertools.count(1)
_elite_aura_cache = {}


def _elite_aura(size):
    """按贴图尺寸缓存精英怪光环，避免每帧新建 SRCALPHA Surface。"""
    s = _elite_aura_cache.get(size)
    if s is None:
        if len(_elite_aura_cache) >= 32:
            _elite_aura_cache.clear()
        dim = size + 16
        s = pygame.Surface((dim, dim), pygame.SRCALPHA)
        pygame.draw.circle(s, (255, 190, 70, 60),
                           (dim // 2, dim // 2), (size + 12) // 2, 3)
        _elite_aura_cache[size] = s
    return s


def _enemy_bullet_count(game):
    n = 0
    for b in game.bullets:
        if not b.friendly:
            n += 1
    return n


# ==================================================================== 基类
class Enemy:
    kind = 'enemy'
    spr_key = 'slime'
    spr_size = 40
    radius = 13.0
    body_color = (120, 220, 110)

    def __init__(self, x, y, floor=1, elite=False):
        self.uid = next(_uid)
        self.x, self.y = float(x), float(y)
        self.floor = int(floor)
        self.elite = bool(elite)
        self.max_hp = 22.0
        self.hp = self.max_hp
        self.speed = 56.0
        self.contact_dmg = 2.0
        self.touch_cd = 0.0
        self.alive = True
        self.hit_flash = 0.0
        self.kx = self.ky = 0.0
        self.t = 0.0
        self.anim = 0.0
        self.facing = 1
        self.invuln = False
        self.bullet_dmg = 2.0
        self.dmg_mul = 1.0
        self.slow_t = 0.0
        self._slow_base_speed = None
        self.dot_t = 0.0
        self.dot_dps = 0.0
        if self.elite:
            self.max_hp = self.max_hp * 2.4 + 6
            self.hp = self.max_hp
            self.radius *= 1.18
            self.spr_size = int(self.spr_size * 1.22)

    # -------------------------------------------------- 通用
    @property
    def hp_ratio(self):
        return max(0.0, min(1.0, self.hp / max(1e-6, self.max_hp)))

    def apply_dmg_mul(self, mul):
        """按章节或场景倍率同步放大怪物各来源伤害。"""
        mul = float(mul or 1.0)
        if abs(mul - 1.0) <= 0.001:
            return
        self.dmg_mul = mul
        self.contact_dmg = round(self.contact_dmg * mul, 2)
        self.bullet_dmg = round(self.bullet_dmg * mul, 2)
        if hasattr(self, 'explode_dmg'):
            self.explode_dmg = round(self.explode_dmg * mul, 2)
        if hasattr(self, 'cloud_dmg'):
            self.cloud_dmg = round(self.cloud_dmg * mul, 2)
        if hasattr(self, 'charge_dmg'):
            self.charge_dmg = round(self.charge_dmg * mul, 2)

    def dist_to_player(self, game):
        return U.dist(self.x, self.y, game.player.x, game.player.y)

    def _apply_knock(self, game, dt):
        if abs(self.kx) > 1 or abs(self.ky) > 1:
            nx = self.x + self.kx * dt
            ny = self.y + self.ky * dt
            self.x, self.y = U.move_circle(self.x, self.y, self.radius,
                                           nx - self.x, ny - self.y, game.room.solid)
        k = max(0.0, 1.0 - 9.0 * dt)
        self.kx *= k
        self.ky *= k

    def _clamp_room(self, pad=2.0):
        self.x = U.clamp(self.x, pad, S.ROOM_PX_W - pad)
        self.y = U.clamp(self.y, pad, S.ROOM_PX_H - pad)

    def _touch_player(self, game, dmg):
        if self.touch_cd > 0 or not self.alive:
            return
        pl = game.player
        if not pl.alive:
            return
        rr = self.radius + pl.radius
        if (self.x - pl.x) ** 2 + (self.y - pl.y) ** 2 < rr * rr:
            if pl.take_damage(dmg, game, self.x, self.y):
                self.touch_cd = 0.6
                a = math.atan2(pl.y - self.y, pl.x - self.x)
                pl.x += math.cos(a) * 9.0
                pl.y += math.sin(a) * 9.0

    def _shoot(self, game, ang, speed=175.0, dmg=2.0, img='b_hex',
               size=14, spread=0.0, count=1, life=1.6):
        if not self.alive:
            return 0
        if _enemy_bullet_count(game) > 190:
            return 0
        made = 0
        for i in range(max(1, int(count))):
            a = ang if count <= 1 else ang + ((i / (count - 1)) - 0.5) * spread
            game.bullets.append(Bullet(
                x=self.x + math.cos(a) * (self.radius + 5),
                y=self.y + math.sin(a) * (self.radius + 5),
                ang=a, speed=speed, dmg=dmg, friendly=False,
                img=img, size=size, radius=max(3.0, size * 0.33),
                life=life, color=(196, 120, 240), hit_shake=0.6))
            made += 1
        return made

    # -------------------------------------------------- 受伤 / 死亡
    def take_damage(self, dmg, game, sx=None, sy=None):
        if not self.alive or self.invuln:
            return
        dmg = max(1.0, float(dmg))
        pl = getattr(game, 'player', None)
        rng = getattr(game, 'rng', None)
        is_crit = (sx is not None and pl is not None and rng is not None
                   and hasattr(pl, 'crit_chance')
                   and rng.random() < pl.crit_chance(game))
        if is_crit:
            dmg *= 1.50
        if getattr(self, 'is_boss', False):
            dmg = min(dmg, max(1.0, self.max_hp * 0.15))
        elif self.elite:
            dmg = min(dmg, max(1.0, self.max_hp * 0.75))
        self.hp -= dmg
        self.hit_flash = 0.13
        if sx is not None:
            a = math.atan2(self.y - sy, self.x - sx)
            f = min(190.0, 40.0 + dmg * 3.4)
            if not self.elite:
                self.kx += math.cos(a) * f
                self.ky += math.sin(a) * f
            else:
                self.kx += math.cos(a) * f * 0.45
                self.ky += math.sin(a) * f * 0.45
        game.fx.sparks(self.x, self.y,
                       (255, 214, 96) if is_crit else self.body_color,
                       n=8 if is_crit else 5,
                       ang=(math.atan2(self.y - (sy or 0), self.x - (sx or 0))))
        if is_crit:
            game.fx.ring(self.x, self.y, 4, 22, 0.22, (255, 214, 96), 2)
        jx = rng.uniform(-7.0, 7.0) if rng is not None else 0.0
        if is_crit:
            game.fx.text(self.x + jx, self.y - self.radius - 13,
                         f'{int(round(dmg))}!', (255, 224, 96),
                         game.assets.font(15), 0.68)
        elif dmg >= 1.0:
            game.fx.text(self.x + jx, self.y - self.radius - 10,
                         str(int(round(dmg))), (245, 240, 225),
                         game.assets.font(11), 0.45)
        if self.hp <= 0:
            # 需求 20：击杀的停顿比普通命中更重
            if hasattr(game, 'add_hitstop'):
                game.add_hitstop(S.HITSTOP_KILL)
            self.die(game)
        else:
            # 需求 20：命中停顿 —— 让每一发都有"打得进去"的手感
            if hasattr(game, 'add_hitstop'):
                game.add_hitstop(S.HITSTOP_HIT)
            game.audio.play('hit', 0.45)

    def die(self, game):
        if not self.alive:
            return
        self.alive = False
        game.audio.play('enemy_die', 0.8)
        col = self.body_color
        game.fx.burst(self.x, self.y, col, n=16, speed=165, life=0.5,
                      size=4, drag=2.2, shape='circle')
        game.fx.burst(self.x, self.y, (250, 245, 230), n=7, speed=105,
                      life=0.32, size=3, drag=3.0)
        game.fx.ring(self.x, self.y, 4, 30, 0.3, col, 2)
        game.fx.add_shake(1.5)
        game.on_enemy_killed(self)

    # -------------------------------------------------- 绘制
    def draw(self, surf, cam, assets):
        if not self.alive:
            return
        x, y = self.x + cam[0], self.y + cam[1]
        size = self.spr_size
        off = getattr(self, 'draw_off_y', 0.0)
        U.draw_shadow(surf, x, y + size * 0.30, size * 0.31, size * 0.15, 140)

        if self.elite:
            surf.blit(_elite_aura(size),
                      (int(x - (size + 16) / 2), int(y - (size + 16) / 2 + off)))

        flip = self.facing < 0
        tint = getattr(self, 'tint', None)
        if tint is not None and hasattr(assets, 'tinted'):
            # 需求 8：同一张贴图按场景染色，做出"不同怪"的观感
            base = assets.tinted(self.spr_key, size, size, tint, 0.66)
            img = pygame.transform.flip(base, True, False) if flip else base
        else:
            img = (assets.flipped(self.spr_key, size, size) if flip
                   else assets.scaled(self.spr_key, size, size))
        sq = getattr(self, 'squash', 1.0)
        if abs(sq - 1.0) > 0.01:
            img = pygame.transform.scale(img, (size, max(2, int(size * sq))))
        surf.blit(img, (int(x - img.get_width() / 2),
                        int(y - img.get_height() / 2 + size * (1 - sq) * 0.4 + off)))

        if self.hit_flash > 0:
            t = self.hit_flash / 0.13
            U.blit_hit_flash(surf, img,
                             (int(x - img.get_width() / 2),
                              int(y - img.get_height() / 2 + size * (1 - sq) * 0.4 + off)),
                             int(175 * t))

        # 小血条
        if self.hp < self.max_hp - 0.01 and not getattr(self, 'is_boss', False):
            w = S.E_HP_BAR_W
            bx, by = int(x - w / 2), int(y - size * 0.52 - 8)
            pygame.draw.rect(surf, (18, 16, 24), (bx - 1, by - 1, w + 2, 5))
            pygame.draw.rect(surf, (60, 40, 46), (bx, by, w, 3))
            fw = int(w * self.hp_ratio)
            if fw > 0:
                pygame.draw.rect(surf, (226, 72, 84), (bx, by, fw, 3))

    def update(self, game, dt):
        self.t += dt
        if self.slow_t > 0:
            self.slow_t = max(0.0, self.slow_t - dt)
            if self.slow_t == 0 and self._slow_base_speed is not None:
                self.speed = self._slow_base_speed
                self._slow_base_speed = None
        if self.dot_t > 0 and self.alive and not self.invuln:
            tick = min(dt, self.dot_t)
            self.dot_t = max(0.0, self.dot_t - dt)
            self.hp -= self.dot_dps * tick
            if self.hp <= 0:
                self.die(game)
            if self.dot_t == 0:
                self.dot_dps = 0.0
        self.touch_cd = max(0.0, self.touch_cd - dt)
        self.hit_flash = max(0.0, self.hit_flash - dt)
        self._apply_knock(game, dt)


# ==================================================================== 史莱姆
class Slime(Enemy):
    kind = 'slime'
    spr_key = 'slime'
    spr_size = 40
    radius = 13.0
    body_color = (124, 214, 106)

    def __init__(self, x, y, floor=1, elite=False):
        super().__init__(x, y, floor, elite)
        self.max_hp = (21 + 8 * (floor - 1)) * (2.4 if elite else 1.0) * (1 + (0.6 if elite else 0))
        self.hp = self.max_hp
        self.speed = 58.0 + 7.0 * (floor - 1)
        self.contact_dmg = 2.0
        self.hop = self.t % 0.95
        self.squash = 1.0
        self.draw_off_y = 0.0

    def update(self, game, dt):
        super().update(game, dt)
        pl = game.player
        self.facing = -1 if pl.x < self.x else 1
        self.anim += dt

        # 跳跃循环：0~0.5 蓄力，0.5~0.95 起跳
        self.hop = (self.hop + dt) % 0.95
        if self.hop < 0.5:
            k = self.hop / 0.5
            self.squash = 1.0 - 0.16 * math.sin(k * math.pi)
            self.draw_off_y = 0.0
            mv = 0.0
        else:
            k = (self.hop - 0.5) / 0.45
            self.squash = 1.0 + 0.14 * math.sin(k * math.pi)
            self.draw_off_y = -math.sin(k * math.pi) * 11.0
            mv = self.speed * 2.35

        if mv > 0:
            a = math.atan2(pl.y - self.y, pl.x - self.x)
            self.x, self.y = U.move_circle(self.x, self.y, self.radius,
                                           math.cos(a) * mv * dt,
                                           math.sin(a) * mv * dt, game.room.solid)
        self._clamp_room()
        self._touch_player(game, self.contact_dmg)


# ==================================================================== 炸弹机器人
class Bomber(Enemy):
    kind = 'bomber'
    spr_key = 'bomber'
    spr_size = 40
    radius = 12.0
    body_color = (198, 92, 64)

    def __init__(self, x, y, floor=1, elite=False):
        super().__init__(x, y, floor, elite)
        self.max_hp = (30 + 10 * (floor - 1)) * (2.4 if elite else 1.0)
        self.hp = self.max_hp
        self.speed = 76.0 + 9.0 * (floor - 1)
        self.contact_dmg = 0.0
        self.fuse = -1.0
        self.boom_done = False
        self.explode_r = 60.0 + 6.0 * (floor - 1)
        self.explode_dmg = 6.0 + 1.5 * (floor - 1)
        self.squash = 1.0

    def update(self, game, dt):
        super().update(game, dt)
        pl = game.player
        if not pl.alive:
            return
        self.facing = -1 if pl.x < self.x else 1
        d = self.dist_to_player(game)

        if self.fuse >= 0:
            self.fuse -= dt
            self.squash = 1.0 + 0.2 * abs(math.sin(self.t * 26.0))
            if self.fuse <= 0:
                self._detonate(game, self.explode_r, self.explode_dmg)
            return

        if d < 48.0:
            self.fuse = 0.85
            game.audio.play('lock')
            game.fx.ring(self.x, self.y, 8, 34, 0.4, (255, 120, 80), 2)
            return

        a = math.atan2(pl.y - self.y, pl.x - self.x)
        wob = math.sin(self.t * 7.0) * 0.35
        a += wob
        self.x, self.y = U.move_circle(self.x, self.y, self.radius,
                                       math.cos(a) * self.speed * dt,
                                       math.sin(a) * self.speed * dt, game.room.solid)
        self._clamp_room()
        if self.t % 0.16 < dt:
            game.fx.burst(self.x, self.y, (90, 88, 96), n=1, speed=12,
                          life=0.3, size=3, drag=2.0, shape='circle')

    def _detonate(self, game, radius, dmg):
        if self.boom_done:
            return
        self.boom_done = True
        self.alive = False
        explode(game, self.x, self.y, radius, dmg, hurt_player=True,
                color=(255, 150, 70), bomber=True)
        game.on_enemy_killed(self)

    def die(self, game):
        if not self.alive:
            return
        if not self.boom_done:
            self.boom_done = True
            self.alive = False
            explode(game, self.x, self.y, self.explode_r * 0.78,
                    self.explode_dmg * 0.55, hurt_player=True,
                    color=(255, 150, 70), bomber=True)
            game.on_enemy_killed(self)
            return
        super().die(game)


# ==================================================================== 无人机
class Drone(Enemy):
    kind = 'drone'
    spr_key = 'drone'
    spr_size = 40
    radius = 13.0
    body_color = (168, 124, 224)

    def __init__(self, x, y, floor=1, elite=False):
        super().__init__(x, y, floor, elite)
        self.max_hp = (33 + 11 * (floor - 1)) * (2.4 if elite else 1.0)
        self.hp = self.max_hp
        self.speed = 66.0 + 7.0 * (floor - 1)
        self.contact_dmg = 1.0
        self.shoot_cd = 0.9 + (x * 0.013) % 0.8
        self.strafe = 1.0 if (int(x + y) % 2 == 0) else -1.0
        self.prefer = 132.0
        self.volley = 1 + min(2, floor - 1)
        self.draw_off_y = -8.0
        self.burst_left = 0
        self.burst_t = 0.0

    def update(self, game, dt):
        super().update(game, dt)
        pl = game.player
        if not pl.alive:
            return
        self.facing = -1 if pl.x < self.x else 1
        self.draw_off_y = -8.0 + math.sin(self.t * 3.2) * 2.4
        d = self.dist_to_player(game)
        a = math.atan2(pl.y - self.y, pl.x - self.x)

        # 维持距离 + 侧移
        if d < self.prefer - 34:
            mv = -self.speed * 0.9
        elif d > self.prefer + 34:
            mv = self.speed
        else:
            mv = self.speed * 0.18
        px = math.cos(a + math.pi / 2) * self.speed * 0.62 * self.strafe
        py = math.sin(a + math.pi / 2) * self.speed * 0.62 * self.strafe
        vx = math.cos(a) * mv + px
        vy = math.sin(a) * mv + py
        self.x, self.y = U.move_circle(self.x, self.y, self.radius, vx * dt, vy * dt,
                                       game.room.solid)
        self._clamp_room()
        if self.x < S.IN_L + 6 or self.x > S.IN_R - 6 or \
           self.y < S.IN_T + 6 or self.y > S.IN_B - 6:
            self.strafe *= -1.0
        if self.t % 1.7 < dt:
            self.strafe *= -1.0

        # 射击（可多连发）
        if self.burst_left > 0:
            self.burst_t -= dt
            if self.burst_t <= 0:
                self.burst_t = 0.16
                self.burst_left -= 1
                self._shoot(game, a + game.rng.uniform(-0.07, 0.07),
                            speed=196.0 + 12.0 * self.floor,
                            dmg=self.bullet_dmg, spread=0.0, count=1, life=1.8)
        else:
            self.shoot_cd -= dt
            if self.shoot_cd <= 0 and d < 300:
                self.shoot_cd = max(0.9, 2.0 - 0.22 * self.floor)
                self.burst_left = self.volley
                self.burst_t = 0.0

        self._touch_player(game, self.contact_dmg)


# ==================================================================== 腐壳虫
class Slug(Enemy):
    """贴地冲锋：先蓄力对准，再高速直线冲刺，撞墙会短暂僵直。

    与 Slime 的区别：Slime 是"追"，Slug 是"撞"。玩家必须学会横向闪避，
    而不是简单后退 —— 这给浅层关就带来"读招"的操作空间。
    """
    kind = 'slug'
    spr_key = 'slime'          # 复用贴图 + 场景染色
    spr_size = 42
    radius = 14.0
    body_color = (150, 132, 92)

    def __init__(self, x, y, floor=1, elite=False):
        super().__init__(x, y, floor, elite)
        self.max_hp = (36 + 12 * (floor - 1)) * (2.4 if elite else 1.0)
        self.hp = self.max_hp
        self.speed = 62.0 + 8.0 * (floor - 1)
        self.contact_dmg = 2.0
        self.tint = (176, 156, 104)
        self.state = 'aim'
        self.st = 0.0 + (x * 0.017) % 0.6
        self.dir = 0.0
        self.squash = 1.0

    def update(self, game, dt):
        super().update(game, dt)
        pl = game.player
        if not pl.alive:
            return
        self.facing = -1 if pl.x < self.x else 1
        self.st += dt
        if self.state == 'aim':
            self.squash = 1.0 - 0.14 * math.sin(self.st / 0.62 * math.pi)
            self.dir = U.ang_lerp(self.dir, math.atan2(pl.y - self.y, pl.x - self.x),
                                  4.0 * dt) if self.st > 0.1 else math.atan2(
                                      pl.y - self.y, pl.x - self.x)
            if self.st >= 0.62:
                self.state = 'dash'
                self.st = 0.0
                game.audio.play('lock', 0.4)
                game.fx.sparks(self.x, self.y, self.body_color, n=6,
                               ang=self.dir + math.pi)
        else:
            sp = self.speed * 3.5
            nx = self.x + math.cos(self.dir) * sp * dt
            ny = self.y + math.sin(self.dir) * sp * dt
            ox, oy = self.x, self.y
            self.x, self.y = U.move_circle(self.x, self.y, self.radius,
                                           nx - self.x, ny - self.y, game.room.solid)
            # 撞墙或超时 -> 僵直
            moved = U.dist(ox, oy, self.x, self.y)
            if moved < sp * dt * 0.35 or self.st > 0.55:
                self.state = 'aim'
                self.st = -0.45          # 僵直惩罚（负数即等待）
                game.fx.ring(self.x, self.y, 3, 22, 0.28, self.body_color, 2)
            self.squash = 1.05
            if self.st % 0.05 < dt:
                game.fx.burst(self.x, self.y, self.body_color, n=2, speed=40,
                              life=0.24, size=3, drag=2.4, shape='circle')
        self._clamp_room()
        self._touch_player(game, self.contact_dmg)


# ==================================================================== 孢殖体
class SporeBug(Enemy):
    """缓慢漂浮，死亡时留下一片毒雾，站在里面持续掉血。

    设计意图：惩罚"站桩输出"。玩家清完一片后必须挪窝，
    否则会被自己制造的战场反噬。
    """
    kind = 'spore'
    spr_key = 'bomber'         # 复用贴图 + 场景染色
    spr_size = 42
    radius = 14.0
    body_color = (140, 196, 96)

    def __init__(self, x, y, floor=1, elite=False):
        super().__init__(x, y, floor, elite)
        self.max_hp = (41 + 14 * (floor - 1)) * (2.4 if elite else 1.0)
        self.hp = self.max_hp
        self.speed = 34.0 + 4.0 * (floor - 1)
        self.contact_dmg = 1.5
        self.tint = (150, 210, 110)
        self.squash = 1.0
        self.draw_off_y = 0.0
        self.cloud_r = 46.0 + 4.0 * (floor - 1)
        self.cloud_life = 4.2
        self.cloud_dmg = 1.4

    def update(self, game, dt):
        super().update(game, dt)
        pl = game.player
        if not pl.alive:
            return
        self.facing = -1 if pl.x < self.x else 1
        self.draw_off_y = math.sin(self.t * 2.1) * 4.0
        a = math.atan2(pl.y - self.y, pl.x - self.x)
        # 保持中距离漂移，不贴脸
        d = self.dist_to_player(game)
        mv = self.speed if d > 96 else -self.speed * 0.5
        self.x, self.y = U.move_circle(self.x, self.y, self.radius,
                                       math.cos(a) * mv * dt,
                                       math.sin(a) * mv * dt, game.room.solid)
        self._clamp_room()
        if self.t % 0.5 < dt:
            game.fx.burst(self.x, self.y, self.tint, n=1, speed=10,
                          life=0.5, size=3, drag=1.6, shape='circle')
        self._touch_player(game, self.contact_dmg)

    def die(self, game):
        if not self.alive:
            return
        super().die(game)
        # 留下一片毒雾（需求 3：场景机关之外的"动态危险区"）
        try:
            from . import hazard as _H
            _H.spawn_cloud(game, self.x, self.y, self.cloud_r,
                           self.cloud_life, self.tint, dmg=self.cloud_dmg)
        except Exception:
            pass


# ==================================================================== 污染幽影
class Wraith(Enemy):
    """会间歇瞬移到玩家背后，并发射预判弹。

    设计意图：逼迫玩家"回头"，打断一味向前推进的节奏。
    """
    kind = 'wraith'
    spr_key = 'drone'          # 复用贴图 + 场景染色
    spr_size = 42
    radius = 13.0
    body_color = (150, 120, 220)

    def __init__(self, x, y, floor=1, elite=False):
        super().__init__(x, y, floor, elite)
        self.max_hp = (38 + 12 * (floor - 1)) * (2.4 if elite else 1.0)
        self.hp = self.max_hp
        self.speed = 58.0 + 6.0 * (floor - 1)
        self.contact_dmg = 1.5
        self.tint = (168, 140, 240)
        self.blink_cd = 2.4 + (x * 0.011) % 1.6
        self.shoot_cd = 1.4
        self.alpha = 190

    def update(self, game, dt):
        super().update(game, dt)
        pl = game.player
        if not pl.alive:
            return
        self.facing = -1 if pl.x < self.x else 1
        d = self.dist_to_player(game)
        a = math.atan2(pl.y - self.y, pl.x - self.x)

        self.blink_cd -= dt
        if self.blink_cd <= 0 and d > 60:
            # 瞬移到玩家背后 60px 处
            back = math.atan2(self.y - pl.y, self.x - pl.x)
            bx = U.clamp(pl.x + math.cos(back) * 62, S.IN_L + 22, S.IN_R - 22)
            by = U.clamp(pl.y + math.sin(back) * 62, S.IN_T + 22, S.IN_B - 22)
            game.fx.burst(self.x, self.y, self.tint, n=12, speed=120,
                          life=0.4, size=4, drag=2.2, shape='circle')
            game.fx.ring(self.x, self.y, 4, 30, 0.3, self.tint, 2)
            self.x, self.y = bx, by
            game.fx.ring(self.x, self.y, 4, 30, 0.3, self.tint, 2)
            self.blink_cd = 2.6 + game.rng.uniform(-0.6, 1.0)
            self.shoot_cd = min(self.shoot_cd, 0.28)
        else:
            mv = self.speed if d > 110 else self.speed * 0.25
            px = math.cos(a + math.pi / 2) * self.speed * 0.4
            py = math.sin(a + math.pi / 2) * self.speed * 0.4
            self.x, self.y = U.move_circle(
                self.x, self.y, self.radius,
                (math.cos(a) * mv + px * (1 if int(self.t) % 2 else -1)) * dt,
                (math.sin(a) * mv + py * (1 if int(self.t) % 2 else -1)) * dt,
                game.room.solid)
        self._clamp_room()
        # 预判弹：朝玩家当前速度方向提前量
        self.shoot_cd -= dt
        if self.shoot_cd <= 0 and d < 280:
            self.shoot_cd = max(1.05, 1.9 - 0.14 * self.floor)
            lead = 0.28
            tx = pl.x + getattr(pl, 'vx', 0.0) * lead
            ty = pl.y + getattr(pl, 'vy', 0.0) * lead
            self._shoot(game, math.atan2(ty - self.y, tx - self.x),
                        speed=214.0, dmg=self.bullet_dmg, size=13, life=1.7)
        self._touch_player(game, self.contact_dmg)


# ==================================================================== 拟态宝箱
class Mimic(Enemy):
    """隐藏奖励怪：伪装成宝箱，靠近才现形（需求 8）。

    击杀必掉紫色以上图纸/武器 —— 是"值得冒险"的正反馈。
    """
    kind = 'mimic'
    spr_key = 'chest'
    spr_size = 40
    radius = 15.0
    body_color = (222, 178, 90)
    is_rare = True

    def __init__(self, x, y, floor=1, elite=False):
        super().__init__(x, y, floor, elite)
        self.max_hp = 122.0 + 35.0 * (floor - 1)
        self.hp = self.max_hp
        self.speed = 92.0
        self.contact_dmg = 2.0
        self.tint = (240, 200, 110)
        self.awake = False
        self.squash = 1.0

    def update(self, game, dt):
        super().update(game, dt)
        pl = game.player
        if not pl.alive:
            return
        d = self.dist_to_player(game)
        if not self.awake:
            if d < 74.0:
                self.awake = True
                game.audio.play('ui_big', 0.8)
                game.fx.ring(self.x, self.y, 6, 46, 0.4, (255, 210, 120), 3)
                game.fx.add_shake(2.5)
                # 需求 15：现形时给一句提示
                try:
                    game.discover('enemy', 'mimic')
                except Exception:
                    pass
            return
        self.facing = -1 if pl.x < self.x else 1
        a = math.atan2(pl.y - self.y, pl.x - self.x)
        self.x, self.y = U.move_circle(self.x, self.y, self.radius,
                                       math.cos(a) * self.speed * dt,
                                       math.sin(a) * self.speed * dt, game.room.solid)
        self._clamp_room()
        self.squash = 1.0 + math.sin(self.t * 9.0) * 0.06
        self._touch_player(game, self.contact_dmg)


# ==================================================================== 拾荒旅人
class Wanderer(Enemy):
    """隐藏奖励怪：不主动攻击，被打了才逃，击杀掉红色/璀璨图纸（需求 8）。

    设计意图：给玩家一个"要不要出手"的抉择 —— 它不威胁你，
    但打它要花时间，而收益极高。这比"又一只必须杀的怪"有趣得多。
    """
    kind = 'wanderer'
    spr_key = 'slime'
    spr_size = 40
    radius = 12.0
    body_color = (230, 210, 130)
    is_rare = True

    def __init__(self, x, y, floor=1, elite=False):
        super().__init__(x, y, floor, elite)
        self.max_hp = 62.0 + 19.0 * (floor - 1)
        self.hp = self.max_hp
        self.speed = 78.0
        self.contact_dmg = 0.0          # 不主动造成伤害
        self.tint = (250, 226, 140)
        self.flee = False
        self.hop = 0.0
        self.squash = 1.0

    def update(self, game, dt):
        super().update(game, dt)
        pl = game.player
        if not pl.alive:
            return
        self.facing = -1 if pl.x < self.x else 1
        d = self.dist_to_player(game)
        # 没被打就原地小跳；被打了（flee）就绕着场地跑
        if not self.flee and d < 90:
            self.flee = True
            try:
                game.discover('enemy', 'wanderer')
            except Exception:
                pass
        self.hop = (self.hop + dt) % 0.8
        self.squash = 1.0 + 0.08 * math.sin(self.hop / 0.8 * math.tau)
        if self.flee or d < 120:
            a = math.atan2(self.y - pl.y, self.x - pl.x)
            # 沿墙跑：把朝向掺一点切向，避免撞墙卡住
            tang = a + math.pi / 2 * (1 if int(self.t * 2) % 2 else -1)
            mx = math.cos(a) * 0.65 + math.cos(tang) * 0.55
            my = math.sin(a) * 0.65 + math.sin(tang) * 0.55
            n = math.hypot(mx, my) or 1.0
            self.x, self.y = U.move_circle(
                self.x, self.y, self.radius,
                mx / n * self.speed * dt, my / n * self.speed * dt,
                game.room.solid)
        self._clamp_room()

    def take_damage(self, dmg, game, sx=None, sy=None):
        self.flee = True
        super().take_damage(dmg, game, sx, sy)


class LuckyTreasure(Enemy):
    """Rare golden creature that carries a mixed cache of valuable supplies."""
    kind = 'lucky_treasure'
    spr_key = 'lucky_treasure'
    spr_size = 48
    radius = 15.0
    body_color = (255, 215, 93)

    def __init__(self, x, y, floor=1, elite=False):
        super().__init__(x, y, floor, elite)
        self.max_hp = 70.0
        self.hp = self.max_hp
        self.speed = 64.0
        self.contact_dmg = 0.0
        self.squash = 1.0

    def update(self, game, dt):
        super().update(game, dt)
        if not game.player.alive:
            return
        self.facing = -1 if game.player.x < self.x else 1
        direction = math.atan2(game.player.y - self.y, game.player.x - self.x)
        distance = self.dist_to_player(game)
        if distance > 58:
            self.x, self.y = U.move_circle(
                self.x, self.y, self.radius,
                math.cos(direction) * self.speed * dt,
                math.sin(direction) * self.speed * dt, game.room.solid)
        self._clamp_room()
        self.squash = 1.0 + .06 * math.sin(self.t * 12)


# ==================================================================== BOSS
class Boss(Enemy):
    kind = 'boss'
    spr_key = 'boss'
    spr_size = 96
    radius = 32.0
    body_color = (198, 84, 220)
    is_boss = True

    ATK_P1 = [('ring', 3), ('spread', 3), ('charge', 2), ('summon', 1)]
    ATK_P2 = [('ring', 3), ('spread', 3), ('charge', 3), ('summon', 2), ('sweep', 2)]
    ATK_P3 = [('ring', 4), ('spread', 3), ('charge', 4), ('summon', 2), ('sweep', 4)]

    def __init__(self, x, y, floor=1, elite=False):
        super().__init__(x, y, floor, elite)
        self.max_hp = 520.0 * (1.0 + 0.85 * (floor - 1))
        self.hp = self.max_hp
        self.speed = 44.0 + 6.0 * (floor - 1)
        self.contact_dmg = 3.0
        self.charge_dmg = 4.0
        self.state = 'intro'
        self.st = 0.0
        self.volley = 0
        self.volley_t = 0.0
        self.charge_dir = 0.0
        self.death_t = 0.0
        self.squash = 1.0
        self.invuln = True

    def setup_scene(self, scene_key, stage_idx=0):
        """按场景给 Boss 换外观与名号（需求 8）。

        同一套 AI（多阶段弹幕）通过 tint/体型/称号差异化，
        让"每个场景的 Boss 不同"在观感上成立，而不必为 7 个 Boss
        各写一套状态机（那是后期迭代的活）。
        """
        mini = stage_idx == 2
        spec = BOSS_SKIN.get(scene_key)
        if not spec:
            return
        self.tint = spec.get('tint')
        self.boss_name = (MINIBOSS_NAMES.get(scene_key, '小首领')
                          if mini else spec.get('name', '首领'))
        self.boss_title = 'WARDEN' if mini else spec.get('title', '')
        scale = float(spec.get('scale', 1.0))
        if abs(scale - 1.0) > 0.001:
            self.spr_size = int(self.spr_size * scale)
            self.radius *= scale
        self.body_color = spec.get('color', self.body_color)
        # 名字里的 skey：让图鉴收录到正确的 Boss 条目
        self.skey = (MINIBOSS_KEYS.get(scene_key) if mini else spec.get('codex'))
        if self.skey in _CODEX_KEYS:
            self.spr_key = 'enemy_' + self.skey
            self.tint = None  # 专属贴图已含主题配色
        scene_mul = float(SCENE_BOSS_HP_MUL.get(scene_key, 1.0))
        if abs(scene_mul - 1.0) > 0.001:
            self.max_hp = float(round(self.max_hp * scene_mul))
            self.hp = self.max_hp
        self.apply_dmg_mul(SCENE_DMG_MUL.get(scene_key, 1.0))
        # 大 Boss（第 5 关）额外强化
        if stage_idx >= 4:
            self.max_hp = float(round(self.max_hp * float(spec.get('big_mul', 1.25))))
            self.hp = self.max_hp
            self.radius *= 1.08
            self.spr_size = int(self.spr_size * 1.08)

    # ------------------------------------------------ 辅助
    def _pick_attack(self, game):
        r = self.hp_ratio
        table = self.ATK_P1 if r > 0.66 else (self.ATK_P2 if r > 0.33 else self.ATK_P3)
        total = sum(w for _, w in table)
        pick = game.rng.uniform(0, total)
        acc = 0.0
        for name, w in table:
            acc += w
            if pick <= acc:
                return name
        return 'ring'

    def _set_state(self, game, st):
        self.state = st
        self.st = 0.0
        self.volley = 0
        if st == 'ring':
            self.volley, self.volley_t = 3, 0.0
        elif st == 'spread':
            self.volley, self.volley_t = 4, 0.0
        elif st == 'sweep':
            self.volley, self.volley_t = 3, 0.0
        elif st == 'charge':
            pl = game.player
            self.charge_dir = math.atan2(pl.y - self.y, pl.x - self.x)
            game.audio.play('lock')
            game.fx.ring(self.x, self.y, 10, 60, 0.5, (255, 90, 90), 3)
        elif st == 'summon':
            self.volley = 0

    # ------------------------------------------------ 更新
    def update(self, game, dt):
        super().update(game, dt)
        self.st += dt
        pl = game.player

        if self.state == 'dying':
            self.death_t += dt
            self.invuln = True
            if int(self.death_t * 14) != int((self.death_t - dt) * 14):
                game.fx.burst(self.x + game.rng.uniform(-40, 40),
                              self.y + game.rng.uniform(-40, 40),
                              (255, 170, 90), n=14, speed=160, life=0.6,
                              size=5, drag=2.0, shape='circle')
                game.fx.ring(self.x + game.rng.uniform(-30, 30),
                             self.y + game.rng.uniform(-30, 30), 4, 46, 0.35,
                             (255, 200, 120), 2)
                game.fx.add_shake(4.0)
                game.audio.play('explode', 0.5)
            if self.death_t > 1.5:
                self.alive = False
                game.fx.burst(self.x, self.y, (255, 230, 180), n=46, speed=300,
                              life=1.1, size=6, drag=1.4, shape='circle')
                game.fx.ring(self.x, self.y, 8, 190, 0.9, (255, 220, 160), 6)
                game.fx.add_shake(15.0)
                game.fx.add_flash(0.55, (255, 220, 160))
                game.audio.play('boss_die')
                game.on_enemy_killed(self)
                game.on_boss_defeated()
            return

        if not pl.alive:
            self.state = 'idle'
            self.squash = 1.0
            return

        self.facing = -1 if pl.x < self.x else 1
        self.squash = 1.0
        d = self.dist_to_player(game)
        to_pl = math.atan2(pl.y - self.y, pl.x - self.x)

        # ---------------- intro
        if self.state == 'intro':
            self.invuln = True
            if self.st < 0.9:
                if self.st % 0.2 < dt:
                    game.fx.ring(self.x, self.y, 20, 110, 0.5, (230, 110, 250), 3)
                    game.fx.burst(self.x, self.y, (230, 120, 250), n=10,
                                  speed=130, life=0.5, size=4, shape='circle')
            else:
                self.invuln = False
                self._set_state(game, 'idle')
            return

        # ---------------- idle
        if self.state == 'idle':
            self.squash = 1.0 + math.sin(self.st * 4.0) * 0.02
            mv = self.speed * 0.55 if d > 90 else -self.speed * 0.35
            self.x, self.y = U.move_circle(self.x, self.y, self.radius,
                                           math.cos(to_pl) * mv * dt,
                                           math.sin(to_pl) * mv * dt, game.room.solid)
            self._clamp_room(40)
            if self.st > 0.75:
                self._set_state(game, self._pick_attack(game))
            return

        # ---------------- 环形弹幕
        if self.state == 'ring':
            if self.volley > 0:
                self.volley_t -= dt
                if self.volley_t <= 0:
                    self.volley_t = 0.30
                    self.volley -= 1
                    n = 13 + 3 * min(3, self.floor)
                    base = self.st * 1.7 + self.volley * 0.22
                    for i in range(n):
                        a = base + i * (math.tau / n)
                        self._shoot(game, a, speed=150.0 + 12.0 * self.floor,
                                    dmg=self.bullet_dmg, size=14, life=2.2)
                    game.audio.play('shoot_heavy', 0.6)
                    game.fx.ring(self.x, self.y, 20, 56, 0.26, (226, 130, 250), 2)
            elif self.st > 1.2:
                self._set_state(game, 'idle')
            return

        # ---------------- 扇形连射
        if self.state == 'spread':
            if self.volley > 0:
                self.volley_t -= dt
                if self.volley_t <= 0:
                    self.volley_t = 0.24
                    self.volley -= 1
                    self._shoot(game, to_pl, speed=228.0, dmg=self.bullet_dmg, size=15,
                                spread=math.radians(34), count=5, life=2.0)
                    game.audio.play('shoot', 0.7)
                    game.fx.add_shake(1.2)
            elif self.st > 1.15:
                self._set_state(game, 'idle')
            return

        # ---------------- 冲锋
        if self.state == 'charge':
            if self.st < 0.55:
                self.squash = 1.0 - 0.2 * math.sin(self.st / 0.55 * math.pi)
                self.charge_dir = U.ang_lerp(self.charge_dir, to_pl, 3.0 * dt)
                if self.st % 0.09 < dt:
                    game.fx.sparks(self.x, self.y, (255, 120, 90), n=4,
                                   ang=self.charge_dir + math.pi)
            elif self.st < 1.15:
                sp = 330.0 + 25.0 * self.floor
                self.x, self.y = U.move_circle(
                    self.x, self.y, self.radius,
                    math.cos(self.charge_dir) * sp * dt,
                    math.sin(self.charge_dir) * sp * dt, game.room.solid)
                self._clamp_room(34)
                if self.st % 0.05 < dt:
                    game.fx.burst(self.x, self.y, (255, 150, 90), n=3,
                                  speed=60, life=0.3, size=4, drag=2.4, shape='circle')
                    game.fx.add_shake(1.0)
                # 冲锋撞击
                pl2 = game.player
                if U.dist(self.x, self.y, pl2.x, pl2.y) < self.radius + pl2.radius + 4:
                    pl2.take_damage(self.charge_dmg, game, self.x, self.y)
            else:
                self._set_state(game, 'idle')
            return

        # ---------------- 召唤
        if self.state == 'summon':
            if self.volley == 0:
                self.volley = 1
                sc = (getattr(game, 'level_state', None) or {}).get('scene')
                k = 3 if (self.floor >= 2 or sc in ('facility', 'core', 'd_lab')) else 2
                for _ in range(k):
                    a = game.rng.uniform(0, math.tau)
                    rr = game.rng.uniform(70, 130)
                    sx = U.clamp(self.x + math.cos(a) * rr, S.IN_L + 24, S.IN_R - 24)
                    sy = U.clamp(self.y + math.sin(a) * rr, S.IN_T + 24, S.IN_B - 24)
                    game.fx.ring(sx, sy, 4, 44, 0.45, (200, 120, 250), 3)
                    game.fx.burst(sx, sy, (200, 130, 250), n=12, speed=120,
                                  life=0.5, size=4, shape='circle')
                    game.spawn_minion(sx, sy, self.floor)
                game.audio.play('ui_big', 0.7)
                game.fx.add_shake(3.0)
            elif self.st > 0.95:
                self._set_state(game, 'idle')
            return

        # ---------------- 扫射
        if self.state == 'sweep':
            if self.volley > 0:
                self.volley_t -= dt
                if self.volley_t <= 0:
                    self.volley_t = 0.26
                    self.volley -= 1
                    base = to_pl - math.radians(30) + (2 - self.volley) * math.radians(22)
                    for i in range(7):
                        self._shoot(game, base + (i - 3) * math.radians(7.5),
                                    speed=265.0, dmg=self.bullet_dmg, size=13, life=1.9)
                    game.audio.play('shoot', 0.75)
                    game.fx.add_shake(1.4)
            elif self.st > 1.3:
                self._set_state(game, 'idle')
            return

        self._set_state(game, 'idle')

    # ------------------------------------------------ 受伤 / 死亡
    def take_damage(self, dmg, game, sx=None, sy=None):
        if self.state in ('intro', 'dying'):
            return
        super().take_damage(dmg, game, sx, sy)

    def die(self, game):
        if not self.alive or self.state == 'dying':
            return
        self.state = 'dying'
        self.death_t = 0.0
        self.invuln = True
        self.kx = self.ky = 0.0
        game.audio.play('boss_die')
        game.fx.add_shake(10.0)
        game.fx.add_flash(0.35, (255, 200, 140))

    def draw(self, surf, cam, assets):
        if not self.alive:
            return
        x, y = self.x + cam[0], self.y + cam[1]
        size = self.spr_size
        U.draw_shadow(surf, x, y + size * 0.30, size * 0.34, size * 0.15, 170)
        flip = self.facing < 0
        tint = getattr(self, 'tint', None)
        if tint is not None and hasattr(assets, 'tinted'):
            img = assets.tinted(self.spr_key, size, size, tint, 0.62)
            if flip:
                img = pygame.transform.flip(img, True, False)
        else:
            img = (assets.flipped(self.spr_key, size, size) if flip
                   else assets.scaled(self.spr_key, size, size))
        sq = self.squash
        if abs(sq - 1.0) > 0.01:
            img = pygame.transform.scale(img, (size, max(2, int(size * sq))))
        surf.blit(img, (int(x - img.get_width() / 2),
                        int(y - img.get_height() / 2 + size * (1 - sq) * 0.4)))
        if self.hit_flash > 0:
            t = self.hit_flash / 0.13
            U.blit_hit_flash(surf, img,
                             (int(x - img.get_width() / 2),
                              int(y - img.get_height() / 2 + size * (1 - sq) * 0.4)),
                             int(170 * t))
        if self.state == 'charge' and self.st < 0.55:
            t = self.st / 0.55
            ln = 150
            ex = x + math.cos(self.charge_dir) * ln
            ey = y + math.sin(self.charge_dir) * ln
            pad = 6
            ox = int(min(x, ex)) - pad
            oy = int(min(y, ey)) - pad
            bw = max(1, int(max(x, ex)) - ox + pad)
            bh = max(1, int(max(y, ey)) - oy + pad)
            s = U.scratch_surf(bw, bh)
            pygame.draw.line(s, (255, 90, 80, int(120 * (1 - t) + 40)),
                             (x - ox, y - oy), (ex - ox, ey - oy), 4)
            surf.blit(s, (ox, oy))


class RangedRaider(Enemy):
    """Armed enemy with a weapon-specific projectile pattern and speed."""

    kind = 'scatter_raider'
    spr_key = 'enemy_scatter_raider'
    spr_size = 42
    radius = 13.0
    body_color = (223, 161, 112)
    shot_speed = 170.0
    shot_count = 5
    shot_spread = 0.85
    shot_img = 'b_bullet'
    shot_size = 11
    shot_cd = 2.2
    prefer = 165.0

    def __init__(self, x, y, floor=1, elite=False):
        super().__init__(x, y, floor, elite)
        self.max_hp = (30 + floor * 8) * (2.4 if elite else 1.0)
        self.hp = self.max_hp
        self.speed = 51 + floor * 4
        self.contact_dmg = 1.0
        self.shoot_cd = self.shot_cd * (0.5 + (x % 17) / 34)

    def update(self, game, dt):
        super().update(game, dt)
        pl = game.player
        if not pl.alive:
            return
        self.facing = -1 if pl.x < self.x else 1
        d = self.dist_to_player(game)
        a = math.atan2(pl.y - self.y, pl.x - self.x)
        mv = self.speed * (1 if d > self.prefer + 25 else
                           (-0.65 if d < self.prefer - 25 else 0))
        self.x, self.y = U.move_circle(self.x, self.y, self.radius,
                                       math.cos(a) * mv * dt,
                                       math.sin(a) * mv * dt, game.room.solid)
        self.shoot_cd -= dt
        if self.shoot_cd <= 0 and d < 390:
            self.shoot_cd = self.shot_cd
            self._shoot(game, a, speed=self.shot_speed, dmg=self.bullet_dmg,
                        img=self.shot_img, size=self.shot_size,
                        spread=self.shot_spread, count=self.shot_count,
                        life=3.5 if self.shot_speed < 150 else 2.4)
            game.fx.ring(self.x, self.y, 2, 18, .18, self.body_color, 2)
        self._touch_player(game, self.contact_dmg)


class BeamRaider(RangedRaider):
    kind = 'beam_raider'
    spr_key = 'enemy_beam_raider'
    body_color = (174, 132, 239)
    shot_speed = 105.0
    shot_count = 1
    shot_spread = 0.0
    shot_img = 'b_laser'
    shot_size = 18
    shot_cd = 2.8
    prefer = 210.0


class RifleRaider(RangedRaider):
    kind = 'rifle_raider'
    spr_key = 'enemy_rifle_raider'
    body_color = (139, 218, 224)
    shot_speed = 420.0
    shot_count = 1
    shot_spread = 0.0
    shot_img = 'b_bolt'
    shot_size = 12
    shot_cd = 1.65
    prefer = 205.0


ENEMY_TYPES = {
    'slime': Slime,
    'bomber': Bomber,
    'drone': Drone,
    'slug': Slug,
    'spore': SporeBug,
    'wraith': Wraith,
    'mimic': Mimic,
    'wanderer': Wanderer,
    'lucky_treasure': LuckyTreasure,
    'scatter_raider': RangedRaider,
    'beam_raider': BeamRaider,
    'rifle_raider': RifleRaider,
}

# ---------------------------------------------------------------- Boss 皮肤
# 需求 8：每个场景的 Boss 不同（外观 + 名号 + 体型 + 强度）。
# codex 字段指向 ENEMY_CODEX 的 key，保证图鉴收录到正确的条目。
SCENE_BOSS_HP_MUL = {
    'crust': 1.00, 'sewer': 1.35, 'facility': 1.75, 'core': 2.20,
    'd_mine': 1.50, 'd_lab': 1.95, 'd_gift': 1.55,
}
SCENE_MOB_HP_MUL = {
    'crust': 1.00, 'sewer': 1.25, 'facility': 1.50, 'core': 1.80,
    'd_mine': 1.35, 'd_lab': 1.65, 'd_gift': 1.40,
}
SCENE_DMG_MUL = {
    'crust': 1.00, 'sewer': 1.20, 'facility': 1.40, 'core': 1.60,
    'd_mine': 1.30, 'd_lab': 1.50, 'd_gift': 1.35,
}

BOSS_SKIN = {
    'crust':    {'name': '残骸军阀', 'title': 'WARLORD',
                 'tint': (198, 150, 96), 'color': (198, 150, 96),
                 'scale': 0.94, 'codex': 'warlord', 'big_mul': 1.25},
    'sewer':    {'name': '虫群女王', 'title': 'SWARM QUEEN',
                 'tint': (150, 210, 120), 'color': (150, 210, 120),
                 'scale': 0.98, 'codex': 'swarmqueen', 'big_mul': 1.25},
    'facility': {'name': '坟场机枢', 'title': 'MECH CORE',
                 'tint': (170, 190, 220), 'color': (170, 190, 220),
                 'scale': 1.0, 'codex': 'mech', 'big_mul': 1.25},
    'core':     {'name': '污染原点·本体', 'title': 'THE ORIGIN',
                 'tint': (222, 110, 230), 'color': (222, 110, 230),
                 'scale': 1.14, 'codex': 'origin', 'big_mul': 1.40},
    'd_mine':   {'name': '矿井监工', 'title': 'FOREMAN',
                 'tint': (196, 168, 120), 'color': (196, 168, 120),
                 'scale': 1.0, 'codex': 'foreman', 'big_mul': 1.25},
    'd_lab':    {'name': '冷库标本', 'title': 'SPECIMEN',
                 'tint': (150, 220, 235), 'color': (150, 220, 235),
                 'scale': 1.05, 'codex': 'specimen', 'big_mul': 1.25},
    'd_gift':   {'name': '净土守卫', 'title': 'GUARDIAN',
                 'tint': (255, 226, 150), 'color': (255, 226, 150),
                 'scale': 1.0, 'codex': 'guardian', 'big_mul': 1.25},
}
MINIBOSS_KEYS = {
    'crust': 'crust_sentinel', 'sewer': 'sewer_serpent',
    'facility': 'facility_smelter', 'core': 'protocol',
    'd_mine': 'mine_excavator', 'd_lab': 'lab_cryowarden',
    'd_gift': 'gift_bloom',
}
MINIBOSS_NAMES = {
    'crust': '熔渣哨兵', 'sewer': '污水管蛇',
    'facility': '熔炉看守', 'core': '协议残片',
    'd_mine': '地脉掘进机', 'd_lab': '零号冻卫',
    'd_gift': '晶花园丁',
}

# 哪些 spawn_plan key 代表"首领"（game._spawn_room 据此分流）。
BOSS_SKIN_KEYS = set()
for _s in BOSS_SKIN.values():
    if _s.get('codex'):
        BOSS_SKIN_KEYS.add(_s['codex'])
BOSS_SKIN_KEYS.update(MINIBOSS_KEYS.values())
# 兼容字面 'boss'（旧存档/无头测试路径）
BOSS_SKIN_KEYS.add('boss')

# 精英版 key -> 普通版 key（"slime_big" -> "slime"）。
# 精英不是独立类，而是普通类 + elite=True —— 血量/体型在基类里放大，
# 行为完全一致，保证"精英 = 更强的同类"这一直觉成立。
ELITE_BASE = {}
for _k in list(ENEMY_TYPES.keys()):
    ELITE_BASE[_k + '_big'] = _k

# 场景专属小怪 -> (基础类, tint, 覆盖参数)。
# 需求 8 要"每场景怪不同"，但为 15 种小怪各写一套 AI 既不现实也没必要 ——
# 差异化体现在：行为骨架（复用 5 个基础类）+ 场景染色 + 数值微调。
# 玩家实际感知到的是"下水道的虫和矿井的虫手感不一样"，这就够了。
VARIANT_OF = {
    # crust：快而脆的爬行体（复用 Slime 的跳跃骨架，跑得更急）
    'crawler':  ('slime', (186, 138, 96), {'speed_mul': 1.28, 'hp_mul': 0.82}),
    # sewer：吸血水蛭（复用 Wraith 的贴身骨架，更快更黏）
    'leech':    ('wraith', (196, 76, 96), {'speed_mul': 1.12, 'hp_mul': 0.9}),
    # facility：固定炮台（复用 Drone 的射击骨架，射程更远、移动几乎为零）
    'turret':   ('drone', (198, 186, 160), {'speed_mul': 0.16, 'hp_mul': 1.25,
                                            'range_mul': 1.5}),
    # d_mine：岩噬虫（复用 Slug 的冲锋骨架，转向更笨但冲得更狠）
    'rockworm': ('slug', (168, 142, 118), {'speed_mul': 1.1, 'hp_mul': 1.15}),
    # d_mine：雷区机兵（复用 Bomber 的布雷骨架，更耐打）
    'minebot':  ('bomber', (176, 176, 190), {'hp_mul': 1.2}),
    # core / d_lab：霜蚀体（复用 SporeBug 的毒雾骨架，冷色调）
    'frostbite': ('spore', (150, 220, 240), {'speed_mul': 0.9}),
    # d_gift：净土傀儡（复用 Slug 的冲锋骨架，但更慢更硬）
    'purifier': ('slug', (230, 226, 210), {'speed_mul': 0.82, 'hp_mul': 1.4}),
    # d_gift：微光灵（复用 Wraith 的瞬移骨架，更快更飘）
    'sprite':   ('wraith', (250, 240, 180), {'speed_mul': 1.2, 'hp_mul': 0.85}),
    # d_mine 精英：矿脉黏液体
    'slime_big_m': ('slime', (176, 156, 108), {'hp_mul': 1.35}),
    # core 精英：孢殖祖巢（毒雾更大）
    'spore_big_m': ('spore', (128, 200, 96), {'hp_mul': 1.3}),
    # 第二梯队精英：复用对应变体的染色 + 略微加硬
    'crawler_big':   ('slime', (206, 148, 96), {'hp_mul': 1.2}),
    'leech_big':     ('wraith', (216, 66, 92), {'hp_mul': 1.2}),
    'turret_big':    ('drone', (216, 200, 168), {'hp_mul': 1.3,
                                                 'range_mul': 1.5}),
    'rockworm_big':  ('slug', (188, 156, 124), {'hp_mul': 1.3}),
    'frostbite_big': ('spore', (170, 232, 250), {'hp_mul': 1.25}),
    'guardian_big':  ('slug', (250, 246, 226), {'hp_mul': 1.5}),
}


def base_kind(kind):
    """把各种 key 归一化成可实例化的基础类名。

    'slug_big' -> 'slug'；'crawler' -> 'slime'；'crawler_big' -> 'slime'；
    未知 -> 'slime'。三级顺序：真实类 -> 变体 -> 精英后缀 -> 兜底。
    """
    if kind in ENEMY_TYPES:
        return kind
    if kind in VARIANT_OF:
        return VARIANT_OF[kind][0]
    if kind in ELITE_BASE:
        return ELITE_BASE[kind]
    # 'crawler_big' / 'turret_big' 这类"变体的精英版"：先剥后缀再看变体表
    if kind.endswith('_big'):
        stripped = kind[:-4]
        if stripped in VARIANT_OF:
            return VARIANT_OF[stripped][0]
        if stripped in ENEMY_TYPES:
            return stripped
    return 'slime'


def make(kind, x, y, floor=1, elite=False):
    """按图鉴 key 造怪。

    需求 8：每个场景的怪不同。kind 直接就是 codex.ENEMY_CODEX 的 key
    （如 'slug' / 'crawler' / 'spore_big'），这里的职责只是把它映射到真实类，
    并把"场景变体"的染色与数值微调施加上去。
    任何未知 key 一律退化成 Slime，保证永不崩溃。
    """
    bk = base_kind(kind)
    is_elite = bool(elite) or kind.endswith('_big')
    cls = ENEMY_TYPES.get(bk, Slime)
    e = cls(x, y, floor, is_elite)
    # 场景变体：染色 + 数值微调
    var = VARIANT_OF.get(kind)
    if var:
        _base, tint, tweak = var
        try:
            e.tint = tint
            if tweak.get('speed_mul'):
                e.speed *= tweak['speed_mul']
            if tweak.get('hp_mul'):
                e.max_hp *= tweak['hp_mul']
                e.hp = e.max_hp
            if tweak.get('range_mul') and isinstance(e, Drone):
                e.prefer *= tweak['range_mul']
        except Exception:
            pass
    # 图鉴用：记录该实例对应的怪物 key（与 ENEMY_CODEX 对齐）
    try:
        e.skey = kind if kind in _CODEX_KEYS else bk
        if is_elite and kind not in _CODEX_KEYS:
            big = bk + '_big'
            e.skey = big if big in _CODEX_KEYS else bk
        if e.skey in _CODEX_KEYS and not isinstance(e, Boss):
            e.spr_key = 'enemy_' + e.skey
            e.tint = None  # 不再用一张底图染色冒充不同怪物
    except Exception:
        pass
    return e


def _codex_keys():
    try:
        from . import codex as _CX
        return set(_CX.ENEMY_CODEX.keys())
    except Exception:
        return set()


_CODEX_KEYS = _codex_keys()
