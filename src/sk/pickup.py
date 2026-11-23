# -*- coding: utf-8 -*-
"""掉落物 / 可交互物 / 可破坏道具"""
import math

import pygame

from . import gamedata as GD
from . import settings as S
from . import utils as U
from . import weapon as W

MAGNET_KINDS = ('coin', 'diamond', 'heart', 'energy', 'key', 'collect',
                'material')
MAGNET_R = 74.0
MAGNET_SPEED = 250.0
TOUCH_PAD = 9.0

PROMPT_R = 34.0
DRINK_NAMES = {'nectar': '琼浆玉液', 'dew': '杨枝甘露',
               'soda': '沙氏汽水', 'tea': '劳大冰红茶'}
DRINK_EFFECTS = {'nectar': '生命上限 +25%', 'dew': '每秒恢复 1 点蓝量',
                 'soda': '攻击速度 +12%', 'tea': '击杀发射固伤篮球'}


class Pickup:
    def __init__(self, x, y, kind, value=1, wkey=None, price=0,
                 ckey=None, ctier='normal', quality='white'):
        self.x, self.y = float(x), float(y)
        self.kind = kind                 # coin/diamond/heart/energy/key/weapon/chest/shop_weapon/shop_heart/collect
        self.value = value
        self.wkey = wkey
        self.quality = W.quality_of(wkey) if kind in ('weapon', 'shop_weapon') and wkey else quality
        self.price = price
        self.ckey = ckey                 # collect 收集品 key / chest 宝箱类别（需求 7、9）
        self.ctier = ctier               # chest 档位：normal 一般 / superb 极品
        self.alive = True
        self.bob = 0.0
        self.phase = (x * 0.07 + y * 0.11) % (math.pi * 2)
        self.radius = 9.0
        self.life = -1.0                 # 负值 = 永不过期
        self.spawn_t = 0.0
        # 武器自动交换用"沿触发"：只在玩家"刚进入"拾取半径那一刻换一次。
        # 若用每帧电平触发，换枪时掉在脚下的旧枪会被立刻再次触发交换，
        # 于是 A->B->A->B…… 无限往返（每帧新建一个 Pickup + 特效）。
        self.was_inside = False

    # -------------------------------------------------- 外观
    @property
    def sprite(self):
        return {
            'coin': 'coin', 'diamond': 'diamond',
            'heart': 'heart', 'energy': 'energy', 'key': 'key',
            'chest': 'chest_' + (self.ckey or 'coin') + '_' + self.ctier,
            'shop_heart': 'heart',
            'shop_hp_potion': 'potion_health',
            'shop_energy_potion': 'potion_energy',
            'drink': 'drink_' + (self.ckey or 'nectar'),
            'weapon': W.sprite_key(self.wkey or 'pistol'),
            'shop_weapon': W.sprite_key(self.wkey or 'pistol'),
            'collect': 'collect_' + (self.ckey or 'gear_cog'),
            'material': 'material_' + (self.ckey or 'scrap'),
        }.get(self.kind, 'coin')

    @property
    def is_interact(self):
        return self.kind in ('chest', 'shop_weapon', 'shop_heart',
                             'shop_hp_potion', 'shop_energy_potion', 'drink', 'weapon')

    # -------------------------------------------------- 更新
    def update(self, game, dt):
        if not self.alive:
            return
        self.bob += dt
        self.spawn_t += dt
        if self.life > 0:
            self.life -= dt
            if self.life <= 0:
                self.alive = False
                return

        pl = game.player
        if not pl.alive:
            return

        if self.kind in MAGNET_KINDS and self.spawn_t > 0.18:
            if 'auto_collect' in (getattr(game, 'run_stats', None) or {}).get('flags', ()):
                self._collect(game)
                return
            d = U.dist(self.x, self.y, pl.x, pl.y)
            # 1.1 天赋「引力场」：拾取范围 +50%
            mr = MAGNET_R
            try:
                _st = getattr(game, 'run_stats', None) or {}
                mr *= (1.0 + float(_st.get('magnet_mul', 0.0) or 0.0)
                       + float(getattr(game, 'char_magnet_mul', 0.0) or 0.0))
            except Exception:
                pass
            if d < mr:
                if d < pl.radius + TOUCH_PAD:
                    self._collect(game)
                    return
                k = MAGNET_SPEED * dt / max(1.0, d)
                self.x += (pl.x - self.x) * k
                self.y += (pl.y - self.y) * k

        # 武器只在玩家主动二次确认后交换，路过掉落物不会改变装备。

    def _collect(self, game):
        self.alive = False
        pl = game.player
        if self.kind == 'coin':
            # 1.3：金币持有上限，超出部分不再增加（避免无限膨胀）
            game.coins, got = GD.add_coin(game.coins, self.value)
            if got <= 0:
                game.fx.text(self.x, self.y - 10, '已满', S.C_WARN,
                             game.assets.font(11), 0.8)
                return
            game.audio.play('coin', 0.7)
            game.fx.sparks(self.x, self.y, S.C_GOLD, n=4)
        elif self.kind == 'diamond':
            # 需求 4：钻石难得——只在首领/深层出现，用于稀有角色与璀璨强化
            before = int(getattr(game, 'diamonds', 0) or 0)
            game.diamonds = GD.clamp_diamond(before + self.value)
            got = game.diamonds - before
            if hasattr(game, 'run_diamonds'):
                game.run_diamonds += got
            game.audio.play('pickup')
            game.fx.text(self.x, self.y - 10, f'+{got}钻', S.C_DIA,
                         game.assets.font(11), 0.9)
            game.fx.burst(self.x, self.y, S.C_DIA, n=14, speed=150,
                          life=0.6, size=3, shape='circle')
        elif self.kind == 'key':
            game.coins, got = GD.add_coin(game.coins, self.value)
            if got <= 0:
                return
            game.audio.play('pickup')
            game.fx.text(self.x, self.y - 10, f'+{got}金', S.C_GOLD,
                         game.assets.font(11), 0.9)
            game.fx.burst(self.x, self.y, S.C_GOLD, n=12, speed=140,
                          life=0.5, size=3, shape='circle')
        elif self.kind == 'heart':
            pl.hp = min(pl.max_hp, pl.hp + self.value)
            game.audio.play('heart')
            game.fx.text(self.x, self.y - 10, f'+{self.value}HP', S.C_HP,
                         game.assets.font(11), 0.9)
            game.fx.burst(self.x, self.y, S.C_HP, n=12, speed=130,
                          life=0.5, size=3, shape='circle')
        elif self.kind == 'energy':
            pl.energy = min(pl.max_energy, pl.energy + self.value)
            game.audio.play('energy')
            game.fx.text(self.x, self.y - 10, f'+{int(self.value)}EN', S.C_ENERGY,
                         game.assets.font(11), 0.9)
            game.fx.burst(self.x, self.y, S.C_ENERGY, n=10, speed=130,
                          life=0.45, size=3, shape='circle')
        elif self.kind == 'material':
            # 需求 7：宝箱开出的材料，直接进背包（与 run 结算同步）
            key = self.ckey or 'scrap'
            n = max(1, int(self.value or 1))
            bag = getattr(game, 'mats', None)
            if bag is not None:
                bag[key] = int(bag.get(key, 0) or 0) + n
            runbag = getattr(game, 'run_mats', None)
            if runbag is not None:
                runbag[key] = int(runbag.get(key, 0) or 0) + n
            game.audio.play('pickup')
            mname = (GD.MATERIALS.get(key) or (key,))[0]
            game.fx.text(self.x, self.y - 10, mname + f' +{n}', (170, 240, 200),
                         game.assets.font(11), 0.95)
            game.fx.burst(self.x, self.y, (140, 230, 190), n=10, speed=130,
                          life=0.5, size=3, shape='circle')
            try:
                game.discover('material', key)
            except Exception:
                pass

        elif self.kind == 'collect':
            # 需求 9：收集品 -> 图鉴 + 展示台
            key = self.ckey
            first = False
            try:
                first = game.collect_got(key)
            except Exception:
                first = False
            game.audio.play('ui_big')
            from . import codex as CX
            name = (CX.COLLECTS.get(key) or (key,))[0]
            game.fx.text(self.x, self.y - 12, name, (255, 236, 170),
                         game.assets.font(12), 1.3)
            game.fx.burst(self.x, self.y, (255, 226, 150), n=18, speed=160,
                          life=0.6, size=3, shape='circle')
            game.fx.ring(self.x, self.y, 5, 40, 0.4, (255, 226, 150), 2)
            game.collection_popup = {'key': key, 't': 2.3, 'life': 2.3}

        # 拾取物即时落盘；死亡结算与异常退出不再决定资源是否保留。
        game._write_save()

    def _swap_weapon(self, game):
        pl = game.player
        old = pl.wkey
        old_q = W.quality_of(old)
        if pl.wkey2 is None:
            if self.wkey == old:
                return False
            pl.wkey2 = self.wkey
            pl.wqual2 = self.quality
            self.alive = False
            game.audio.play('pickup')
            game.discover('weapon', self.wkey)
            if game.profile is not None:
                owned = game.profile.setdefault('weapon_qualities', {})
                owned[self.wkey] = self.quality
                game._write_save()
            game.toast('第二武器已解锁', '按 Q 切换武器', (180, 220, 255))
            return True
        if self.wkey == old:
            return False
        pl.wkey = self.wkey
        pl.wqual = self.quality
        self.alive = False
        game.audio.play('pickup')
        spec = W.get(self.wkey)
        # 需求 15：图鉴收录（第一次拿到这把武器）
        try:
            game.discover('weapon', self.wkey)
        except Exception:
            pass
        if game.profile is not None:
            owned = game.profile.setdefault('weapon_qualities', {})
            owned[self.wkey] = self.quality
            game.profile['weapon'] = self.wkey
            game._write_save()
        game.fx.text(self.x, self.y - 12, spec.name, GD.quality_of(self.quality)['color'],
                     game.assets.font(12), 1.2)
        game.fx.burst(self.x, self.y, spec.color, n=14, speed=150,
                      life=0.5, size=3, shape='circle')
        # 旧武器掉在原地，可换回。
        # 必须标记 was_inside=True：玩家此刻正踩在这把新枪上，若不标记就会
        # 下一帧立刻换回去，A->B->A->B 无限往返。标记后需"先走出去再走回来"。
        dropped = Pickup(self.x, self.y, 'weapon', wkey=old, quality=old_q)
        dropped.was_inside = True
        game.pickups.append(dropped)
        return True

    # -------------------------------------------------- 交互（按 E）
    def can_interact(self, pl):
        return self.alive and self.is_interact and \
            U.dist(self.x, self.y, pl.x, pl.y) < PROMPT_R

    def prompt_text(self):
        if self.kind == 'chest':
            return 'E  开启%s' % self._chest_name()
        if self.kind == 'weapon':
            qspec_obj = GD.quality_of(self.quality)
            qm = float(qspec_obj.get('mul', 1.0))
            ws = W.apply_quality(W.get(self.wkey), self.quality, qm)
            wdmg = max(1, int(round(ws.dmg)))
            wspd = 1.0 / max(0.01, float(ws.cd or 0.25))
            wtag = f' [伤{wdmg}×{ws.count} 速{wspd:.1f}/s 暴8%]' if ws.count > 1 else f' [伤{wdmg} 速{wspd:.1f}/s 暴8%]'
            return 'E  拾取%s·%s%s' % (
                qspec_obj['name'], W.get(self.wkey).name, wtag)
        if self.kind == 'shop_weapon':
            spec = W.get(self.wkey)
            qspec_obj = GD.quality_of(self.quality)
            qm = float(qspec_obj.get('mul', 1.0))
            ws = W.apply_quality(spec, self.quality, qm)
            wdmg = max(1, int(round(ws.dmg)))
            wspd = 1.0 / max(0.01, float(ws.cd or 0.25))
            wtag = f' [伤{wdmg}×{ws.count} 速{wspd:.1f}/s 暴8%]' if ws.count > 1 else f' [伤{wdmg} 速{wspd:.1f}/s 暴8%]'
            return f'E  {self.price}金 {qspec_obj["name"]}·{spec.name}：{spec.desc}{wtag}'
        if self.kind == 'drink':
            return f'E  {self.price}金 {DRINK_NAMES.get(self.ckey, "饮料")}·{DRINK_EFFECTS.get(self.ckey, "")}'
        if self.kind in ('shop_hp_potion', 'shop_energy_potion'):
            name = '血瓶' if self.kind == 'shop_hp_potion' else '蓝瓶'
            effect = '回复 6 点生命' if self.kind == 'shop_hp_potion' else '回复 80 点蓝量'
            return f'E  {self.price}金 {name}：{effect}'
        if self.kind in ('shop_weapon', 'shop_heart', 'shop_hp_potion',
                         'shop_energy_potion', 'drink'):
            return f'E  {self.price}金  购买'
        return ''

    def _chest_name(self):
        """需求 7：宝箱分 5 类 × 2 档，提示里带上具体名字。"""
        try:
            return GD.CHESTS.get(self.ckey or 'coin', {}).get(
                self.ctier, {}).get('name', '宝箱')
        except Exception:
            return '宝箱'

    # -------------------------------------------------- 需求 18：二次确认
    @property
    def needs_confirm(self):
        """这些操作会花掉资源 / 不可逆，故需要二次按键。"""
        return self.kind in ('chest', 'shop_weapon', 'shop_heart',
                             'shop_hp_potion', 'shop_energy_potion', 'drink', 'weapon')

    def confirm_text(self):
        """返回 (标题, 副标题)。标题为空表示不需要确认。"""
        if self.kind == 'chest':
            return ('开启%s' % self._chest_name(),
                    '再按一次确认开启（箱内物品随机）')
        if self.kind == 'shop_weapon':
            return ('购买武器 %s' % W.get(self.wkey).name,
                    '花费 %d 金币，再按一次确认' % self.price)
        if self.kind == 'shop_heart':
            return ('购买治疗', '花费 %d 金币回复 2 点生命，再按一次确认'
                    % self.price)
        if self.kind in ('shop_hp_potion', 'shop_energy_potion'):
            name = '血瓶' if self.kind == 'shop_hp_potion' else '蓝瓶'
            effect = '回复 6 点生命' if self.kind == 'shop_hp_potion' else '回复 80 点蓝量'
            return (f'购买{name}', f'花费 {self.price} 金币，{effect}；再按一次确认')
        if self.kind == 'drink':
            return (f'饮用{DRINK_NAMES.get(self.ckey, "饮料")}',
                    f'花费 {self.price} 金币，{DRINK_EFFECTS.get(self.ckey, "")}；再按一次确认')
        if self.kind == 'weapon':
            return ('拾取武器：%s' % W.get(self.wkey).name,
                    '空栏位将装入第二把；否则替换当前武器。再按一次确认')
        return ('', '')

    def interact(self, game):
        pl = game.player
        if self.kind == 'chest':
            from . import codex as CX
            self.alive = False
            game.audio.play('ui_big')
            ckey = self.ckey or 'coin'
            spec = GD.CHESTS.get(ckey, GD.CHESTS['coin']).get(
                self.ctier, GD.CHESTS['coin']['normal'])
            col = spec.get('color', S.C_GOLD)
            game.fx.burst(self.x, self.y, col, n=26, speed=190,
                          life=0.7, size=4, shape='circle')
            game.fx.ring(self.x, self.y, 6, 54, 0.42, col, 3)
            game.fx.text(self.x, self.y - 30, spec.get('name', '宝箱'), col,
                         game.assets.font(12), 1.1)
            # 需求 7：开箱结算走 gamedata.chest_loot（一般/极品两档）
            loot = GD.chest_loot(game.rng, ckey, self.ctier, game.floor)

            if loot.get('coins'):
                n = loot['coins']
                for _ in range(n):
                    a = game.rng.uniform(0, math.tau)
                    d = game.rng.uniform(12, 30)
                    game.pickups.append(Pickup(self.x + math.cos(a) * d,
                                               self.y + math.sin(a) * d, 'coin', 1))
            for _ in range(int(loot.get('diamonds') or 0)):
                a = game.rng.uniform(0, math.tau)
                d = game.rng.uniform(14, 26)
                game.pickups.append(Pickup(self.x + math.cos(a) * d,
                                           self.y + math.sin(a) * d, 'diamond', 1))
            for _ in range(int(loot.get('heal') or 0)):
                a = game.rng.uniform(0, math.tau)
                d = game.rng.uniform(14, 26)
                game.pickups.append(Pickup(self.x + math.cos(a) * d,
                                           self.y + math.sin(a) * d, 'heart', 1))
            if loot.get('energy'):
                game.pickups.append(Pickup(self.x, self.y - 22, 'energy',
                                           int(loot['energy'])))
            for mkey, mn in (loot.get('mats') or {}).items():
                # 材料直接进背包：宝箱已二次确认，无需再捡一遍
                mnum = max(0, int(mn))
                if mnum <= 0:
                    continue
                bag = getattr(game, 'mats', None)
                if bag is not None:
                    bag[mkey] = int(bag.get(mkey, 0) or 0) + mnum
                a = game.rng.uniform(0, math.tau)
                d = game.rng.uniform(14, 26)
                mname = (GD.MATERIALS.get(mkey) or (mkey,))[0]
                game.fx.text(self.x + math.cos(a) * d,
                             self.y + math.sin(a) * d - 12,
                             mname + f' +{mnum}', (170, 240, 200),
                             game.assets.font(11), 1.0)
                try:
                    game.discover('material', mkey)
                except Exception:
                    pass

            # 武器箱：按档位决定品质上限，掉一把武器
            if ckey == 'weapon' or loot.get('quality'):
                sc = (getattr(game, 'level_state', None) or {}).get('scene')
                key, quality = W.roll_chest_weapon(game.rng, sc, self.ctier)
                game.pickups.append(Pickup(self.x, self.y - 16, 'weapon',
                                           wkey=key, quality=quality))

            # 收集箱：开出收集品（可放到展示台）
            if ckey == 'collect' or game.rng.random() < 0.08:
                ctier = 'superb' if (self.ctier == 'superb'
                                     or game.rng.random() < 0.22) else 'common'
                ck = CX.roll_collect(game.rng, ctier)
                pc = Pickup(self.x, self.y - 26, 'collect', 1)
                pc.ckey = ck
                game.pickups.append(pc)
            return True

        if self.kind == 'shop_weapon':
            if game.coins < self.price:
                game.audio.play('no_energy')
                game.fx.text(pl.x, pl.y - 22, '金币不足', S.C_WARN,
                             game.assets.font(12), 0.9)
                return False
            game.coins -= self.price
            game.audio.play('buy')
            old = pl.wkey
            old_q = W.quality_of(old)
            self.alive = False
            if pl.wkey2 is None:
                pl.wkey2, pl.wqual2 = self.wkey, self.quality
            else:
                pl.wkey, pl.wqual = self.wkey, self.quality
                game.pickups.append(Pickup(self.x, self.y, 'weapon',
                                           wkey=old, quality=old_q))
            game.discover('weapon', self.wkey)
            if game.profile is not None:
                game.profile.setdefault('weapon_qualities', {})[self.wkey] = self.quality
                if pl.wkey == self.wkey:
                    game.profile['weapon'] = self.wkey
                game._write_save()
            game.fx.text(pl.x, pl.y - 22, '购买成功', S.C_ACCENT,
                         game.assets.font(12), 1.0)
            return True

        if self.kind == 'shop_heart':
            if pl.hp >= pl.max_hp:
                game.audio.play('no_energy')
                game.fx.text(pl.x, pl.y - 22, '血量已满', S.C_WARN,
                             game.assets.font(12), 0.9)
                return False
            if game.coins < self.price:
                game.audio.play('no_energy')
                game.fx.text(pl.x, pl.y - 22, '金币不足', S.C_WARN,
                             game.assets.font(12), 0.9)
                return False
            game.coins -= self.price
            pl.hp = min(pl.max_hp, pl.hp + 2)
            game.audio.play('buy')
            game.fx.text(pl.x, pl.y - 22, '+2 HP', S.C_HP,
                         game.assets.font(12), 1.0)
            self.alive = False
            return True

        if self.kind in ('shop_hp_potion', 'shop_energy_potion', 'drink'):
            if game.coins < self.price:
                game.audio.play('no_energy')
                game.fx.text(pl.x, pl.y - 22, '金币不足', S.C_WARN,
                             game.assets.font(12), 0.9)
                return False
            if self.kind == 'shop_hp_potion' and pl.hp >= pl.max_hp:
                return False
            if self.kind == 'shop_energy_potion' and pl.energy >= pl.max_energy:
                return False
            game.coins -= self.price
            if self.kind == 'shop_hp_potion':
                pl.hp = min(pl.max_hp, pl.hp + 6)
            elif self.kind == 'shop_energy_potion':
                pl.energy = min(pl.max_energy, pl.energy + 80)
            else:
                previous = game.drink_buffs.get(self.ckey, 0)
                game.drink_buffs[self.ckey] = previous + 1
                if self.ckey == 'nectar':
                    increase = pl.max_hp * 0.25 / (1 + 0.25 * previous)
                    pl.max_hp += increase
                    pl.hp = min(pl.max_hp, pl.hp + increase)
            game.audio.play('buy')
            game.fx.text(pl.x, pl.y - 22,
                         DRINK_NAMES.get(self.ckey, '补给已使用') if self.kind == 'drink' else '补给已使用',
                         S.C_ACCENT, game.assets.font(12), 1.0)
            return True

        if self.kind == 'weapon':
            self._swap_weapon(game)
            return True
        return False

    # -------------------------------------------------- 绘制
    def draw(self, surf, cam, assets):
        if not self.alive:
            return
        size = 22 if self.kind in ('coin', 'diamond', 'heart', 'energy',
                                   'key', 'collect') else 26
        if self.kind in ('weapon', 'shop_weapon'):
            size = 28
        key = self.sprite
        img = assets.scaled(key, size, size)
        off = math.sin(self.bob * 3.0 + self.phase) * 2.2
        x, y = self.x + cam[0], self.y + cam[1]
        if self.kind in ('weapon', 'shop_weapon'):
            qc = GD.quality_of(self.quality)['color']
            pygame.draw.circle(surf, qc, (int(x), int(y + off)), 20, 2)
        if self.kind not in ('chest',):
            U.draw_shadow(surf, x, y + 8, size * 0.36, size * 0.18, 120)
        # 需求 7：宝箱按「类别 × 档位」着色 —— 一眼区分 5 类，极品更亮
        if self.kind == 'chest':
            try:
                spec = GD.CHESTS.get(self.ckey or 'coin', {}).get(
                    self.ctier, {})
                cc = spec.get('color', (255, 206, 74))
                glow = pygame.Surface((size + 16, size + 16), pygame.SRCALPHA)
                alpha = 96 if self.ctier == 'superb' else 54
                pygame.draw.circle(glow, (cc[0], cc[1], cc[2], alpha),
                                   ((size + 16) // 2, (size + 16) // 2),
                                   (size + 13) // 2)
                surf.blit(glow, (int(x - (size + 16) / 2),
                                 int(y - (size + 16) / 2 + off)))
                if self.ctier == 'superb':
                    pygame.draw.circle(surf, cc, (int(x), int(y + off)),
                                       int(size * 0.52), 2)
            except Exception:
                pass
        if self.kind in ('coin', 'diamond', 'key', 'energy', 'heart',
                         'shop_heart', 'collect'):
            glow = pygame.Surface((size + 10, size + 10), pygame.SRCALPHA)
            c = {'coin': (255, 210, 90), 'diamond': (140, 230, 255),
                 'key': (255, 210, 90),
                 'energy': (110, 220, 255), 'heart': (255, 90, 100),
                 'shop_heart': (255, 90, 100), 'collect': (255, 226, 150)}[self.kind]
            pygame.draw.circle(glow, (c[0], c[1], c[2], 46),
                               ((size + 10) // 2, (size + 10) // 2), (size + 8) // 2)
            surf.blit(glow, (int(x - (size + 10) / 2), int(y - (size + 10) / 2 + off)))
        surf.blit(img, (int(x - size / 2), int(y - size / 2 + off)))

        # 价格 / 可交互提示
        if self.kind in ('shop_weapon', 'shop_heart', 'shop_hp_potion',
                         'shop_energy_potion', 'drink'):
            f = assets.font(11)
            label = f'{self.price}金'
            col = S.C_GOLD if True else S.C_WARN
            surf.blit(f.render(label, True, (0, 0, 0)),
                      (int(x - f.size(label)[0] / 2) + 1, int(y + 16 + off) + 1))
            surf.blit(f.render(label, True, col),
                      (int(x - f.size(label)[0] / 2), int(y + 16 + off)))


class Prop:
    """可破坏的木箱 / 油桶（挡路、挡子弹）"""

    def __init__(self, x, y, kind='crate'):
        self.x, self.y = float(x), float(y)
        self.kind = kind
        self.alive = True
        self.max_hp = 1.0 if kind == 'crate' else 2.0
        self.hp = self.max_hp
        self.radius = 12.0
        self.hit_flash = 0.0
        self.shake = 0.0

    def take_damage(self, dmg, game, sx=None, sy=None):
        if not self.alive:
            return
        self.hp -= dmg
        self.hit_flash = 0.14
        self.shake = 3.0
        if self.hp <= 0:
            self.alive = False
            self._break(game)

    def _break(self, game):
        col = (168, 128, 74) if self.kind == 'crate' else (150, 96, 84)
        game.audio.play('break')
        game.fx.burst(self.x, self.y, col, n=16, speed=150, life=0.5,
                      size=4, drag=2.4, grav=210.0)
        game.fx.burst(self.x, self.y, (206, 178, 128), n=6, speed=90,
                      life=0.35, size=3, drag=3.0)
        game.fx.ring(self.x, self.y, 4, 30, 0.26, (222, 202, 156), 2)
        game.fx.add_shake(1.6)
        r = game.rng.random()
        if r < 0.55:
            for _ in range(game.rng.randint(1, 3)):
                a = game.rng.uniform(0, math.tau)
                d = game.rng.uniform(6, 20)
                game.pickups.append(Pickup(self.x + math.cos(a) * d,
                                           self.y + math.sin(a) * d, 'coin', 1))
        elif r < 0.70:
            game.pickups.append(Pickup(self.x, self.y, 'energy', 18))
        elif r < 0.76:
            game.pickups.append(Pickup(self.x, self.y, 'heart', 2))

    def update(self, game, dt):
        self.hit_flash = max(0.0, self.hit_flash - dt)
        if self.shake > 0:
            self.shake = max(0.0, self.shake - 30.0 * dt)

    def draw(self, surf, cam, assets):
        if not self.alive:
            return
        size = 26
        img = assets.scaled(self.kind, size, size)
        sx = math.sin(self.shake * 3.4) * (self.shake / 3.0) * 1.6 if self.shake else 0.0
        x, y = self.x + cam[0] + sx, self.y + cam[1]
        U.draw_shadow(surf, x, y + 9, 12, 6, 130)
        surf.blit(img, (int(x - size / 2), int(y - size / 2)))
        if self.hit_flash > 0:
            fl = img.copy()
            fl.fill((255, 220, 180, int(210 * (self.hit_flash / 0.14))),
                    special_flags=pygame.BLEND_RGBA_MULT)
            white = pygame.Surface(img.get_size(), pygame.SRCALPHA)
            white.fill((255, 255, 255, int(150 * (self.hit_flash / 0.14))))
            tmp = img.copy()
            tmp.blit(white, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
            surf.blit(tmp, (int(x - size / 2), int(y - size / 2)))
