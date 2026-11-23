# -*- coding: utf-8 -*-
"""玩家角色"""
import math

import pygame

from . import settings as S
from . import utils as U
from . import weapon as W


class Player:
    def __init__(self, x, y):
        self.x, self.y = float(x), float(y)
        self.radius = S.P_RADIUS
        self.max_hp = S.P_MAX_HP
        self.hp = float(self.max_hp)
        self.max_energy = S.P_MAX_ENERGY
        self.energy = S.P_MAX_ENERGY
        self.alive = True
        self.wkey = 'pistol'
        self.wqual = 'white'
        self.wkey2 = None
        self.wqual2 = 'white'
        self.cool = 0.0
        self.cool2 = 0.0
        self.iframes = 0.0
        self.dash_t = 0.0
        self.dash_cd = 0.0
        self.dash_dx = 0.0
        self.dash_dy = 0.0
        self.aim = 0.0
        self.walk = 0.0
        self.recoil = 0.0
        self.muzzle = 0.0
        self.hit_flash = 0.0
        self.moving = False
        self.shots = 0
        self.hit_taken = 0
        self.dmg_taken = 0.0
        # ---- 需求 20：受击击退。knock_t 是"击退位移的剩余时间"，
        # 击退期间玩家的常规移动被压到 30%，营造"被推开"的失控感。
        self.knock_t = 0.0
        self.knock_dx = 0.0
        self.knock_dy = 0.0
        self.shield_charges = 0

    # -------------------------------------------------- 属性
    @property
    def spec(self):
        return W.get(self.wkey)

    def wlevel(self, game):
        """当前武器在**本存档**里的强化等级（需求 5：武器培养）。

        局内换枪只改 wkey，强化等级始终跟随存档 —— 这样玩家在客厅
        砸的金币/材料，进关卡立刻能感知到。
        """
        prof = getattr(game, 'profile', None)
        if not prof:
            return 0
        from . import gamedata as GD
        return max(int((prof.get('weapon_quality_levels') or {}).get(self.wkey, 0) or 0),
                   int((prof.get('weapons') or {}).get(self.wkey, 0) or 0))

    def wq(self, game):
        """当前武器型号对应的固定品质。"""
        from . import gamedata as GD
        return W.quality_of(self.wkey)

    def wq_spec(self, game):
        """当前武器叠上**品质机制**后的实际规格（伤害倍率由 wmul 统一乘一次，不重复相乘）。"""
        from dataclasses import replace as _replace
        from . import gamedata as GD
        base = W.get(self.wkey)
        q = self.wq(game)
        try:
            s = W.apply_quality(base, q, 1.0)
        except Exception:
            s = base
        if q in ('blue', 'radiant') and self.wlevel(game) >= GD.max_level(q):
            s = _replace(s, speed=s.speed * 1.15)
        return s

    def wmul(self, game):
        """武器强化带来的伤害倍率（品质 mul × 每级 +10%）。"""
        from . import gamedata as GD
        lv = self.wlevel(game)
        q = self.wq(game)
        base = float(GD.quality_of(q).get('mul', 1.0))
        # 每级额外 +10%，满级再叠品质自带 perk（perk 的效果在 gamedata 里另有描述）
        max_bonus = 1.15 if GD.quality_rank(q) > 2 and lv >= GD.max_level(q) else 1.0
        return base * (1.0 + 0.10 * lv) * max_bonus

    def heal(self, n):
        self.hp = min(self.max_hp, self.hp + n)

    def switch_weapon(self):
        if self.wkey2 is None:
            return False
        old_cool = float(getattr(self, 'cool', 0.0) or 0.0)
        self.wkey, self.wkey2 = self.wkey2, self.wkey
        self.wqual, self.wqual2 = self.wqual2, self.wqual
        self.cool = max(float(getattr(self, 'cool2', 0.0) or 0.0), 0.12)
        self.cool2 = old_cool
        return True

    # -------------------------------------------------- 更新
    def update(self, game, dt, inp):
        if not self.alive:
            return
        self.cool = max(0.0, self.cool - dt)
        self.cool2 = max(0.0, float(getattr(self, 'cool2', 0.0)) - dt)
        self.dash_cd = max(0.0, self.dash_cd - dt)
        self.iframes = max(0.0, self.iframes - dt)
        self.recoil = max(0.0, self.recoil - dt * 6.0)
        self.muzzle = max(0.0, self.muzzle - dt)
        self.hit_flash = max(0.0, self.hit_flash - dt)
        self.knock_t = max(0.0, self.knock_t - dt)

        self.aim = float(inp.get('aim', self.aim))
        spec = self.spec
        hp_regen = float((getattr(game, 'run_stats', None) or {}).get('hp_regen', 0.0) or 0.0)
        regen_rate = float(getattr(game, 'char_regen_rate', 0.0) or 0.0)
        if regen_rate > 0 and getattr(game, 'room', None) is not None:
            if game.room.cleared or not any(e.alive for e in getattr(game, 'enemies', ())):
                hp_regen += regen_rate
        if hp_regen > 0 and self.hp < self.max_hp:
            self.hp = min(self.max_hp, self.hp + hp_regen * dt)

        # ---- 冲刺
        if inp.get('dash') and self.dash_t <= 0 and self.dash_cd <= 0:
            mx, my = inp.get('mx', 0.0), inp.get('my', 0.0)
            if mx or my:
                l = math.hypot(mx, my)
                self.dash_dx, self.dash_dy = mx / l, my / l
            else:
                self.dash_dx, self.dash_dy = math.cos(self.aim), math.sin(self.aim)
            self.dash_t = S.P_DASH_TIME
            self.phase_origin = (self.x, self.y)
            char_key = (getattr(game, 'profile', None) or {}).get('char') or getattr(game, 'char_key', 'scout')
            dash_mul = float((getattr(game, 'run_stats', None) or {}).get('dash_cd_mul', 0.0) or 0.0)
            self.dash_cd = S.P_DASH_CD * (0.75 if char_key == 'ghost' else 1.0) * max(0.25, 1.0 + dash_mul)
            self.iframes = max(self.iframes, S.P_DASH_TIME + 0.12)
            game.audio.play('dash')
            game.fx.burst(self.x, self.y, (170, 230, 255), n=10, speed=110,
                          life=0.3, size=3, drag=3.0, shape='circle')

        sol = game.room.solid
        blk = game.room.blockers()
        phase_step = 'phase_step' in (getattr(game, 'run_stats', None) or {}).get('flags', ())
        phase_active = phase_step and self.dash_t > 0

        if self.dash_t > 0:
            self.dash_t -= dt
            dx = self.dash_dx * S.P_DASH_SPEED * dt
            dy = self.dash_dy * S.P_DASH_SPEED * dt
            self.moving = True
            if game.rng.random() < 0.75:
                game.fx.burst(self.x, self.y, (140, 200, 240), n=1, speed=14,
                              life=0.24, size=3, drag=3.0, shape='circle')
        else:
            mx, my = float(inp.get('mx', 0.0)), float(inp.get('my', 0.0))
            l = math.hypot(mx, my)
            if l > 1.0:
                mx, my = mx / l, my / l
            # 需求：污染渐近减益——移速随污染浓度下降
            ps = float(getattr(game, 'pollution_spd', 1.0))
            # 需求 6：角色基础速度（由 game._apply_loadout 写入）
            ps *= float(getattr(game, 'char_spd_mul', 1.0) or 1.0)
            # 1.1 天赋：移速加成（speed_mul）
            try:
                _st = getattr(game, 'run_stats', None) or {}
                ps *= (1.0 + float(_st.get('speed_mul', 0.0) or 0.0))
            except Exception:
                pass
            strip_mul = 1.0
            for strip in getattr(game.room, 'speed_strips', ()):
                if strip.contains(self.x, self.y):
                    strip_mul = strip.speed_mul
                    break
            ds = S.P_SPEED * ps * strip_mul * (0.72 if inp.get('slow') else 1.0)
            dx, dy = mx * ds * dt, my * ds * dt
            self.moving = (l > 0.01)

        # 后坐力位移
        dx += math.cos(self.aim + math.pi) * self.recoil * dt * 5.0
        dy += math.sin(self.aim + math.pi) * self.recoil * dt * 5.0

        # 需求 20：受击击退位移（指数衰减，比常规移动更"硬"）
        if self.knock_t > 0:
            k = self.knock_t / max(1e-6, S.P_KNOCK_TIME)
            dx += self.knock_dx * k * dt
            dy += self.knock_dy * k * dt

        self.x, self.y = U.move_circle(self.x, self.y, self.radius, dx, dy,
                                       None if phase_active else sol,
                                       [] if phase_active else blk)
        self.x = U.clamp(self.x, -4.0, S.ROOM_PX_W + 4.0)
        self.y = U.clamp(self.y, -4.0, S.ROOM_PX_H + 4.0)
        if phase_active and self.dash_t <= 0 and U.collide_test(
                self.x, self.y, self.radius, sol, blk):
            spot = U.find_free_spot(self.x, self.y, self.radius, sol, blk)
            if spot is not None:
                self.x, self.y = spot
            else:
                self.x, self.y = self.phase_origin

        if self.moving:
            self.walk += dt

        # ---- 能量恢复（需求：污染渐近减益——回能速率下降）
        # Energy comes from pickups; it does not refill passively.

        # ---- 攻击（需求 6：远程射击 / 近战挥砍）
        if inp.get('shoot') and self.cool <= 0:
            if self.energy > 0 and (spec.cost <= 0 or self.energy + 1e-6 >= spec.cost):
                self._fire(game, spec)
            else:
                fist = W.FISTS
                hits = W.melee_swing(game, fist, self.x, self.y, self.aim,
                                     1.0 + self.dmg_bonus(game))
                W.weapon_flash(game, fist, self.x, self.y, self.aim, melee=True)
                game.audio.play('shoot_heavy', 0.35)
                self.cool = fist.cd / self.attack_speed_mul(game, include_quality=False)

    def dmg_bonus(self, game):
        """本局伤害加成（局外火力强化 + 天赋 dmg_mul + 1.3 污染共鸣）。"""
        b = float(getattr(game, 'char_power_mul', 0.0) or 0.0)
        st = getattr(game, 'run_stats', None)
        if isinstance(st, dict):
            b += float(st.get('dmg_mul', 0.0) or 0.0)
        b += float(getattr(game, 'pur_dmg_mul', 0.0) or 0.0)
        return b

    def attack_speed_mul(self, game, include_quality=True):
        """本局攻速倍率加算池（品质射速 + 满级词条 + 沙氏汽水 +12%/瓶 + 快速击发 +12%/层）。"""
        from . import gamedata as GD
        q = self.wq(game)
        base = float(W.quality_mech(q).get('rate', 1.0)) if include_quality else 1.0
        if include_quality and q in ('white', 'radiant') and self.wlevel(game) >= GD.max_level(q):
            base += 0.08
        soda = int(getattr(game, 'drink_buffs', {}).get('soda', 0) or 0)
        st = getattr(game, 'run_stats', None)
        rate_mul = float(st.get('rate_mul', 0.0) or 0.0) if isinstance(st, dict) else 0.0
        return max(0.1, base + 0.12 * soda + rate_mul)

    def crit_chance(self, game):
        """当前暴击率（基础 8% + 局外致命被动 + 天赋精密瞄具 + 绿/璀璨满级加成，上限 65%）。"""
        from . import gamedata as GD
        c = 0.08 + float(getattr(game, 'char_crit_bonus', 0.0) or 0.0)
        st = getattr(game, 'run_stats', None)
        if isinstance(st, dict):
            c += float(st.get('crit', 0.0) or 0.0)
        wq = self.wq(game)
        if wq in ('green', 'radiant') and self.wlevel(game) >= GD.max_level(wq):
            c += 0.06
        return min(0.65, c)

    def _fire(self, game, spec):
        """一次攻击。近战走 W.melee_swing，远程走 W.fire（需求 6）。"""
        qspec = self.wq_spec(game)          # 叠上品质机制后的规格
        self.cool = spec.cd / self.attack_speed_mul(game)
        self.energy = max(0.0, self.energy - spec.cost)
        a = self.aim
        # 天赋伤害加成（含 1.3「污染共鸣」）+ 武器培养倍率
        dmul = (1.0 + self.dmg_bonus(game)) * self.wmul(game)

        if qspec.melee:
            # 近战：身前扇形横扫，命中所有范围内的敌人
            hits = W.melee_swing(game, qspec, self.x, self.y, a, dmul)
            m_double = float(W.quality_mech(self.wq(game)).get('melee_double', 0.0))
            if (m_double > 0.0 and getattr(game, 'rng', None) is not None
                    and game.rng.random() < m_double):
                hits += W.melee_swing(game, qspec, self.x, self.y, a + 0.14, dmul)
                game.fx.text(self.x, self.y - 26, '连斩', (255, 226, 130),
                             game.assets.font(10), 0.45)
            if hits > 0 and hasattr(game, 'add_hitstop'):
                game.add_hitstop(S.HITSTOP_KILL)
            game.audio.play('shoot_heavy', 0.7)
            game.fx.add_shake(1.6)
            W.weapon_flash(game, qspec, self.x, self.y, a, melee=True)
            self.shots += 1
            return

        mx = self.x + math.cos(a) * 14.0
        my = self.y + math.sin(a) * 14.0
        W.fire(game, qspec, mx, my, a, friendly=True, dmg_mul=dmul)
        self.shots += 1
        self.muzzle = 0.07
        self.recoil = min(9.0, qspec.kick * 0.22)
        game.audio.play(qspec.sound, 0.85)
        if qspec.kick > 0:
            self.x -= math.cos(a) * qspec.kick * 0.012
            self.y -= math.sin(a) * qspec.kick * 0.012
        game.fx.add_shake(qspec.shake * 0.35)
        # 枪口火焰
        W.weapon_flash(game, qspec, mx, my, a)

    # -------------------------------------------------- 受伤
    def take_damage(self, dmg, game, sx=None, sy=None):
        if not self.alive or self.iframes > 0:
            return False
        guard_mul = float(getattr(game, 'char_guard_mul', 1.0) or 1.0)
        if int(getattr(self, 'shield_charges', 0) or 0) > 0:
            self.shield_charges -= 1
            self.iframes = S.P_IFRAME * guard_mul
            game.audio.play('dash')
            game.fx.ring(self.x, self.y, 10, 36, 0.35, (120, 210, 255), 3)
            game.fx.text(self.x, self.y - 26, '护盾抵挡', (140, 220, 255),
                         game.assets.font(12), 0.85)
            return False
        self.hit_taken += 1
        self.dmg_taken += float(dmg)
        self.hp -= float(dmg)
        self.iframes = S.P_IFRAME * guard_mul
        self.hit_flash = 0.22
        # 需求 20：受击击退 —— 从伤害来源方向被推开
        self.apply_knockback(game, sx, sy, dmg)
        game.audio.play('hurt')
        game.fx.add_shake(4.2)
        game.fx.add_flash(0.22, (255, 60, 70))
        game.fx.blood(self.x, self.y, (226, 62, 74), n=9)
        game.fx.text(self.x, self.y - 26, f'-{int(round(dmg))}', S.C_HP,
                     game.assets.font(13), 0.8)
        # 天赋「反伤甲」+ 局外被动「荆棘」：受击时向最近敌人反弹伤害
        flags = (getattr(game, 'run_stats', None) or {}).get('flags') or ()
        thorns_ratio = (0.40 if 'thorns' in flags else 0.0) + float(getattr(game, 'char_thorns_ratio', 0.0) or 0.0)
        if thorns_ratio > 0 and float(dmg) > 0 and getattr(game, 'enemies', None):
            ax = float(sx) if sx is not None else self.x
            ay = float(sy) if sy is not None else self.y
            cands = [e for e in game.enemies if e.alive and not getattr(e, 'invuln', False)]
            if cands:
                target = min(cands, key=lambda e: (e.x - ax) ** 2 + (e.y - ay) ** 2)
                reflected = max(1.0, round(float(dmg) * thorns_ratio, 2))
                target.take_damage(reflected, game)
        # 需求 20：受击硬直（hit-stop）—— 短暂定住，让打击有分量
        if hasattr(game, 'add_hitstop'):
            game.add_hitstop(S.HITSTOP_HURT)
        if self.hp <= 0:
            self.hp = 0.0
            self.die(game)
        return True

    def apply_knockback(self, game, sx=None, sy=None, dmg=1.0):
        """按来源坐标把玩家推开（需求 20）。

        sx/sy 是伤害来源的世界坐标；缺省时退化为"沿当前瞄准反方向"。
        击退强度与伤害成正比，但有上限，避免高伤一击把玩家推出房间。
        """
        try:
            if sx is None or sy is None:
                a = self.aim + math.pi
                ux, uy = math.cos(a), math.sin(a)
            else:
                d = math.hypot(self.x - float(sx), self.y - float(sy))
                if d < 1e-3:
                    a = self.aim + math.pi
                    ux, uy = math.cos(a), math.sin(a)
                else:
                    ux = (self.x - float(sx)) / d
                    uy = (self.y - float(sy)) / d
            strength = min(S.P_KNOCK_MAX,
                           S.P_KNOCK_BASE + float(dmg) * S.P_KNOCK_PER_DMG)
            self.knock_t = S.P_KNOCK_TIME
            self.knock_dx = ux * strength
            self.knock_dy = uy * strength
        except Exception:
            pass

    def die(self, game):
        if not self.alive:
            return
        self.alive = False
        game.audio.play('game_over')
        game.fx.burst(self.x, self.y, (226, 62, 74), n=30, speed=190,
                      life=0.9, size=5, drag=1.8, shape='circle')
        game.fx.burst(self.x, self.y, (255, 220, 200), n=16, speed=130,
                      life=0.6, size=4, drag=2.4)
        game.fx.ring(self.x, self.y, 6, 78, 0.6, (255, 120, 120), 3)
        game.fx.add_shake(11.0)
        game.fx.add_flash(0.4, (255, 40, 50))
        game.on_player_died()

    # -------------------------------------------------- 绘制
    def draw(self, surf, cam, assets, game=None):
        if not self.alive:
            return
        x, y = self.x + cam[0], self.y + cam[1]

        # 无敌帧闪烁：用半透明代替"完全消失"，避免玩家找不到自己
        fade = (self.iframes > 0 and self.dash_t <= 0
                and int(self.iframes * 22) % 2 == 0)

        U.draw_shadow(surf, x, y + 12, 13, 6, 150)

        bob = -abs(math.sin(self.walk * 11.0)) * 2.0 if self.moving else 0.0
        size = 46
        # 朝向：瞄准方向偏左则水平翻转
        flip = math.cos(self.aim) < 0
        char_key = ((game.profile or {}).get('char', 'scout') if game else 'scout')
        art_key = 'player_' + char_key if 'player_' + char_key in assets.img else 'player'
        img = assets.flipped(art_key, size, size) if flip else assets.scaled(art_key, size, size)
        if fade:
            img = img.copy()
            img.set_alpha(105)
        surf.blit(img, (int(x - size / 2), int(y - size / 2 + bob - 4)))

        # 枪口火焰
        if self.muzzle > 0:
            t = self.muzzle / 0.07
            a = self.aim
            mx = x + math.cos(a) * 20.0
            my = y + math.sin(a) * 20.0 - 4
            r = int(4 + 7 * t)
            gl = pygame.Surface((r * 4, r * 4), pygame.SRCALPHA)
            pygame.draw.circle(gl, (255, 236, 170, int(210 * t)), (r * 2, r * 2), r)
            pygame.draw.circle(gl, (255, 255, 255, int(230 * t)), (r * 2, r * 2), max(1, r // 2))
            surf.blit(gl, (int(mx - r * 2), int(my - r * 2)))

        # 受伤闪白
        if self.hit_flash > 0:
            t = self.hit_flash / 0.22
            white = pygame.Surface((size, size), pygame.SRCALPHA)
            white.fill((255, 255, 255, int(160 * t)))
            tmp = img.copy()
            tmp.blit(white, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
            surf.blit(tmp, (int(x - size / 2), int(y - size / 2 + bob - 4)))

        # 瞄准指示（细线 + 端点）
        if game is not None and game.show_aim:
            a = self.aim
            ex = x + math.cos(a) * 30.0
            ey = y + math.sin(a) * 30.0 - 4
            ln = pygame.Surface((4, 4), pygame.SRCALPHA)
            ln.fill((255, 255, 255, 70))
            for k in range(1, 4):
                t = k / 4.0
                surf.blit(ln, (int(U.lerp(x, ex, t)) - 2, int(U.lerp(y - 4, ey, t)) - 2))
        if int(getattr(self, 'shield_charges', 0) or 0) > 0:
            pygame.draw.circle(surf, (120, 210, 255), (int(x), int(y - 2)), 20, 2)
