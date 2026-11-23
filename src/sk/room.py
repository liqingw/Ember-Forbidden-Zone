# -*- coding: utf-8 -*-
"""房间：地块、门、房间内实体容器、房间背景烘焙"""
import math
import random

import pygame

from . import settings as S
from . import utils as U
from . import chapter as C
from .pickup import Pickup, Prop
from . import hazard as H

T_FLOOR, T_WALL, T_DOOR = 0, 1, 2
KIND_LABEL = {
    'start': '出生房', 'normal': '战斗房', 'treasure': '宝箱房',
    'heal': '治疗房', 'shop': '商店房', 'drink': '饮料房', 'boss': 'BOSS 房',
}


class Room:
    def __init__(self, gx, gy, kind, doors, rng, floor):
        self.gx, self.gy = int(gx), int(gy)
        self.kind = kind
        self.doors = set(doors)
        self.open_doors = set(doors)
        self.floor = int(floor)
        self.rng = rng

        self.visited = False
        self.cleared = kind in ('start', 'treasure', 'heal', 'shop', 'drink')
        self.enemies_spawned = False
        self.loot_taken = False

        self.spawn_plan = []      # [(kind, x, y, elite), ...]
        self.wave_plans = []      # 三轮顺序刷新
        self.wave_index = 0
        self.pickup_plan = []     # [(pickup_kwargs), ...]
        self.prop_plan = []       # [(kind, x, y), ...]
        self.hazard_plan = None   # hazard.plan_scene() 的产物，进入房间时物化
        self.rare_mob = None      # 隐藏奖励怪 key（mimic / wanderer，需求 8）

        self.props = []
        self.pickups = []
        self.traps = []           # 需求 3：陷阱
        self.speed_strips = []
        self.covers = []          # 需求 3：掩体（实心，可被爆炸摧毁）
        self.caves = []           # 需求 3：奖励洞穴
        self.clouds = []          # 动态毒雾（孢殖体死亡留下，需求 8）
        self.portal = None
        self.portal_t = 0.0
        self._props_built = False
        self._hazards_built = False

        # ---- 地块
        self.tiles = [[T_FLOOR] * S.ROOM_COLS for _ in range(S.ROOM_ROWS)]
        self.door_dir_at = {}
        for d in self.doors:
            tx, ty = S.DOOR_TILE[d]
            for off in (-1, 0, 1):
                xy = (tx + off, ty) if d in ('N', 'S') else (tx, ty + off)
                self.door_dir_at[xy] = d
        for ty in range(S.ROOM_ROWS):
            for tx in range(S.ROOM_COLS):
                border = (tx == 0 or ty == 0 or
                          tx == S.ROOM_COLS - 1 or ty == S.ROOM_ROWS - 1)
                if not border:
                    self.tiles[ty][tx] = T_FLOOR
                elif (tx, ty) in self.door_dir_at:
                    self.tiles[ty][tx] = T_DOOR
                else:
                    self.tiles[ty][tx] = T_WALL

        self._bg = None

    # -------------------------------------------------- 查询
    def tile(self, tx, ty):
        if 0 <= tx < S.ROOM_COLS and 0 <= ty < S.ROOM_ROWS:
            return self.tiles[ty][tx]
        return T_WALL

    def solid(self, tx, ty):
        t = self.tile(tx, ty)
        if t == T_WALL:
            return True
        if t == T_DOOR:
            d = self.door_dir_at.get((tx, ty))
            return d not in self.open_doors
        return False

    def blockers(self):
        """圆形阻挡物：可破坏道具 + 掩体（需求 3）。"""
        out = [(p.x, p.y, p.radius) for p in self.props if p.alive]
        out.extend((c.x, c.y, c.radius) for c in self.covers if c.alive)
        return out

    def hazards(self):
        """供子弹/爆炸统一施加伤害的地形物件。"""
        return [c for c in self.covers if c.alive]

    @property
    def has_enemies(self):
        return self.kind == 'boss' or self.kind == 'normal'

    def refresh_doors(self, locked):
        self.open_doors = set() if locked else set(self.doors)

    def label(self):
        return KIND_LABEL.get(self.kind, self.kind)

    # -------------------------------------------------- 构建内容
    def build_props(self):
        if self._props_built:
            return
        self._props_built = True
        for kind, x, y in self.prop_plan:
            self.props.append(Prop(x, y, kind))

    def build_pickups(self):
        for kw in self.pickup_plan:
            self.pickups.append(Pickup(**kw))
        self.pickup_plan = []

    # -------------------------------------------------- 场景交互物（需求 3）
    def build_hazards(self):
        """把 hazard_plan 物化成 Trap / Cover / Cave。

        props（木箱油桶）、掩体、陷阱三者共用一份"占位表"，保证互不重叠；
        掩体额外做一次落点校验：若正好压在门格/入口上会被拉偏，避免堵死通道。
        """
        if self._hazards_built:
            return
        self._hazards_built = True
        plan = self.hazard_plan
        if not plan:
            return
        for kind, x, y, phase in plan.get('traps', ()):
            self.traps.append(H.Trap(x, y, kind, phase))
        for kind, x, y in plan.get('strips', ()):
            cls = H.SpeedUpStrip if kind == 'up' else H.SlowDownStrip
            self.speed_strips.append(cls(x, y))
        for kind, x, y, hp in plan.get('covers', ()):
            cx, cy = U.unstick(x, y, 15.0, self.solid, None,
                               fallback=(S.ROOM_CX, S.ROOM_CY))
            self.covers.append(H.Cover(cx, cy, kind, hp))
        for loot, x, y in plan.get('caves', ()):
            self.caves.append(H.Cave(x, y, loot))

    def update_hazards(self, game, dt):
        for t in self.traps:
            if t.alive:
                t.update(game, dt)
        for c in self.covers:
            if c.alive:
                c.update(game, dt)
        for cv in self.caves:
            if cv.alive:
                cv.update(game, dt)
        # 动态毒雾（需求 8）：逐帧结算 + 过期回收
        alive_clouds = []
        for cl in self.clouds:
            if cl.update(game, dt):
                alive_clouds.append(cl)
        self.clouds = alive_clouds

    def draw_hazards_under(self, surf, cam, assets):
        for strip in self.speed_strips:
            strip.draw(surf, cam)
        """地面层：陷阱底盘、洞穴、毒雾。"""
        for c in self.caves:
            if c.alive:
                c.draw(surf, cam, assets)
        for t in self.traps:
            if t.alive:
                t.draw_under(surf, cam, assets)
        for cl in self.clouds:
            cl.draw(surf, cam, assets)

    def draw_hazards_over(self, surf, cam, assets):
        """角色层之上：地刺/电场/喷焰。"""
        for t in self.traps:
            if t.alive:
                t.draw_over(surf, cam, assets)

    # -------------------------------------------------- 背景烘焙
    def bg(self, assets):
        if self._bg is not None:
            return self._bg
        surf = pygame.Surface((S.ROOM_PX_W, S.ROOM_PX_H)).convert()
        surf.fill((14, 13, 18))
        scene = getattr(self, 'scene_key', None)
        suffix = '_' + scene if scene in C.CHAPTER_STORY else ''
        floor_a = assets.scaled('tile_floor' + suffix, S.TILE, S.TILE)
        floor_b = assets.scaled('tile_floor_alt' + suffix, S.TILE, S.TILE)
        wall = assets.scaled('tile_wall' + suffix, S.TILE, S.TILE)
        wall_top = assets.scaled('tile_wall_top' + suffix, S.TILE, S.TILE)

        for ty in range(S.ROOM_ROWS):
            for tx in range(S.ROOM_COLS):
                t = self.tiles[ty][tx]
                px, py = tx * S.TILE, ty * S.TILE
                h = (tx * 7 + ty * 13) % 5
                if t == T_FLOOR:
                    surf.blit(floor_b if h == 0 else floor_a, (px, py))
                elif t == T_DOOR:
                    surf.blit(floor_a, (px, py))
                    dark = pygame.Surface((S.TILE, S.TILE), pygame.SRCALPHA)
                    dark.fill((0, 0, 0, 118))
                    surf.blit(dark, (px, py))
                else:
                    surf.blit(wall_top if ty == 0 else wall, (px, py))
                # 地砖明暗变化，避免大面积平铺的呆板感
                if h >= 3 and t != T_WALL:
                    sh = pygame.Surface((S.TILE, S.TILE), pygame.SRCALPHA)
                    sh.fill((0, 0, 0, 16 + 8 * (h - 3)))
                    surf.blit(sh, (px, py))
        # 每个主题场景各有环境色；只烘焙一次，避免逐帧分配贴图。
        scene = getattr(self, 'scene_key', None)
        if scene in C.CHAPTER_STORY:
            tint = C.scene_info(scene).get('tint', (140, 140, 140))
            wash = pygame.Surface((S.ROOM_PX_W, S.ROOM_PX_H), pygame.SRCALPHA)
            wash.fill((*tint[:3], 22))
            surf.blit(wash, (0, 0))
        # 地表裂纹与散落砂粒使用坐标哈希，房间往返时纹理保持稳定。
        for ty in range(1, S.ROOM_ROWS - 1):
            for tx in range(1, S.ROOM_COLS - 1):
                if self.tiles[ty][tx] != T_FLOOR:
                    continue
                h = (tx * 37 + ty * 53 + self.gx * 11 + self.gy * 19) % 13
                px, py = tx * S.TILE, ty * S.TILE
                if h == 0:
                    pygame.draw.line(surf, (82, 78, 92),
                                     (px + 7, py + 8), (px + 17, py + 14), 1)
                    pygame.draw.line(surf, (66, 64, 78),
                                     (px + 17, py + 14), (px + 22, py + 24), 1)
                elif h == 1:
                    pygame.draw.circle(surf, (102, 98, 108),
                                       (px + 11, py + 21), 1)
        self._draw_theme_decor(surf, scene)
        # 内区四周的内投影，增加纵深
        for i in range(6):
            a = int(58 * (1 - i / 6.0) ** 1.5)
            if a <= 1:
                continue
            band = pygame.Surface((S.ROOM_PX_W - 2 * S.TILE, 1), pygame.SRCALPHA)
            band.fill((0, 0, 0, a))
            surf.blit(band, (S.TILE, S.TILE + i))
            surf.blit(band, (S.TILE, S.ROOM_PX_H - S.TILE - 1 - i))
        self._bg = surf
        return surf

    def _draw_theme_decor(self, surf, scene):
        """每房间烘焙一次跨地砖细节；不影响碰撞与可读性。"""
        palettes = {
            'crust': ((75, 219, 234), (213, 94, 215)),
            'sewer': ((113, 231, 151), (203, 239, 91)),
            'facility': ((91, 210, 250), (255, 169, 88)),
            'core': ((246, 88, 148), (255, 180, 93)),
            'd_mine': ((255, 192, 102), (255, 229, 129)),
            'd_lab': ((143, 219, 255), (210, 249, 255)),
            'd_gift': ((104, 249, 211), (249, 219, 124)),
        }
        if scene not in palettes:
            return
        light, hot = palettes[scene]
        seed = (sum(ord(c) for c in scene) * 991 + self.gx * 197 +
                self.gy * 389 + self.floor * 743)
        rng = random.Random(seed)
        layer = pygame.Surface((S.ROOM_PX_W, S.ROOM_PX_H), pygame.SRCALPHA)
        for i in range(23):
            x, y = rng.randrange(45, S.ROOM_PX_W - 45), rng.randrange(47, S.ROOM_PX_H - 45)
            if abs(x - S.ROOM_CX) < 44 and abs(y - S.ROOM_CY) < 38:
                continue
            accent = light if i % 4 else hot
            if i % 5 == 0:
                pygame.draw.circle(layer, (*accent, 16), (x, y), 15)
                pygame.draw.circle(layer, (*accent, 29), (x, y), 9)
            if scene == 'crust':
                pygame.draw.polygon(layer, (*accent, 150),
                    [(x, y - 10), (x + 4, y + 2), (x - 2, y + 7)])
                pygame.draw.line(layer, (*hot, 95), (x + 4, y + 2), (x + 12, y + 6))
            elif scene == 'sewer':
                pygame.draw.ellipse(layer, (45, 169, 117, 64), (x - 12, y - 5, 14, 6))
                pygame.draw.arc(layer, (*light, 150), (x - 14, y - 8, 18, 8), 0, 3.1, 1)
                pygame.draw.circle(layer, (*hot, 160), (x + 5, y - 2), 2)
            elif scene == 'facility':
                pygame.draw.line(layer, (*light, 90), (x - 12, y), (x + 8, y), 2)
                pygame.draw.line(layer, (*light, 90), (x + 8, y), (x + 8, y + 8), 2)
                pygame.draw.rect(layer, (*hot, 170), (x + 6, y + 6, 5, 4))
            elif scene == 'core':
                pygame.draw.line(layer, (*light, 140), (x - 12, y - 7), (x, y), 2)
                pygame.draw.line(layer, (*hot, 155), (x, y), (x + 10, y + 8), 2)
                pygame.draw.circle(layer, (*hot, 170), (x, y), 3)
            elif scene == 'd_mine':
                pygame.draw.polygon(layer, (*accent, 150),
                    [(x - 6, y + 6), (x - 3, y - 6), (x + 4, y - 2), (x + 7, y + 7)])
                pygame.draw.line(layer, (*hot, 160), (x - 3, y - 5), (x + 2, y + 4), 1)
            elif scene == 'd_lab':
                pygame.draw.line(layer, (*light, 115), (x - 9, y), (x, y - 7), 1)
                pygame.draw.line(layer, (*light, 115), (x, y - 7), (x + 8, y + 6), 1)
                pygame.draw.line(layer, (*hot, 180), (x - 4, y - 3), (x + 5, y + 5), 1)
            else:
                pygame.draw.line(layer, (*light, 165), (x, y + 8), (x, y - 5), 2)
                pygame.draw.ellipse(layer, (*light, 125), (x - 7, y - 6, x, y))
                pygame.draw.ellipse(layer, (*hot, 170), (x, y - 7, x + 6, y - 1))
        surf.blit(layer, (0, 0))

    # -------------------------------------------------- 绘制
    def draw_bg(self, surf, cam, assets):
        surf.blit(self.bg(assets), cam)

    def draw_doors(self, surf, cam, assets):
        door_img = assets.scaled('tile_door', S.TILE, S.TILE)
        for d in sorted(self.doors):
            tx, ty = S.DOOR_TILE[d]
            px = tx * S.TILE + cam[0]
            py = ty * S.TILE + cam[1]
            for off in (-1, 1):
                sx = px + off * S.TILE if d in ('N', 'S') else px
                sy = py if d in ('N', 'S') else py + off * S.TILE
                if d in self.open_doors:
                    pygame.draw.rect(surf, (9, 10, 18),
                                     (sx, sy, S.TILE, S.TILE))
                else:
                    surf.blit(door_img, (sx, sy))
            if d in self.open_doors:
                # 开启：画一个明暗门洞 + 地面箭头，明确"可通行"
                hole = pygame.Surface((S.TILE, S.TILE), pygame.SRCALPHA)
                hole.fill((6, 6, 10, 165))
                surf.blit(hole, (px, py))
                g = pygame.Surface((S.TILE, S.TILE), pygame.SRCALPHA)
                c = (150, 240, 200, 90)
                if d == 'N':
                    pygame.draw.polygon(g, c, [(10, 20), (22, 20), (16, 9)])
                elif d == 'S':
                    pygame.draw.polygon(g, c, [(10, 12), (22, 12), (16, 23)])
                elif d == 'W':
                    pygame.draw.polygon(g, c, [(20, 10), (20, 22), (9, 16)])
                else:
                    pygame.draw.polygon(g, c, [(12, 10), (12, 22), (23, 16)])
                surf.blit(g, (px, py))
            else:
                surf.blit(door_img, (px, py))
                # 锁定警示条
                pulse = 0.55 + 0.45 * math.sin(pygame.time.get_ticks() / 130.0)
                bar = pygame.Surface((S.TILE - 6, 4), pygame.SRCALPHA)
                bar.fill((255, 96, 96, int(150 + 90 * pulse)))
                if d in ('N', 'S'):
                    surf.blit(bar, (px + 3, py + (14 if d == 'N' else 14)))
                else:
                    bar2 = pygame.Surface((4, S.TILE - 6), pygame.SRCALPHA)
                    bar2.fill((255, 96, 96, int(150 + 90 * pulse)))
                    surf.blit(bar2, (px + 14, py + 3))

    def draw_portal(self, surf, cam, assets, t):
        if self.portal is None:
            return
        x = self.portal[0] + cam[0]
        y = self.portal[1] + cam[1]
        r = 30
        gl = pygame.Surface((r * 4, r * 4), pygame.SRCALPHA)
        cx = cy = r * 2
        for i in range(4):
            rr = int(r * (0.45 + 0.18 * i))
            a = 60 - i * 10
            pygame.draw.circle(gl, (150, 110, 255, a), (cx, cy), rr)
        for i in range(3):
            ang = t * (2.4 + i * 0.7) + i * 2.1
            ex = cx + math.cos(ang) * r * 0.78
            ey = cy + math.sin(ang) * r * 0.78
            pygame.draw.circle(gl, (220, 200, 255, 190), (int(ex), int(ey)), 4 - i // 2)
        pygame.draw.circle(gl, (196, 160, 255, 220), (cx, cy), int(r * 0.30), 2)
        surf.blit(gl, (int(x - cx), int(y - cy)))
        U.draw_shadow(surf, x, y + 24, 22, 9, 140)

    def update_portal(self, dt):
        self.portal_t += dt
