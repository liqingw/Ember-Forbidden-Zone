# -*- coding: utf-8 -*-
"""资源加载。任何缺失资源都会生成本地占位图，保证游戏永不因素材问题崩溃。"""
import logging
import os

import pygame

from . import settings as S

_logger = logging.getLogger('sk.assets')
if not _logger.handlers:
    _logger.addHandler(logging.NullHandler())
_logged_assets_exc = set()


def _log_asset_exc(tag, exc, detail=''):
    try:
        key = (tag, type(exc).__name__, str(detail))
        if key in _logged_assets_exc:
            return
        if len(_logged_assets_exc) >= 128:
            _logged_assets_exc.clear()
        _logged_assets_exc.add(key)
        _logger.warning('[%s] %s (%s: %s)', tag, detail, type(exc).__name__, exc)
    except Exception:
        pass

# key -> (文件名, 期望尺寸)
IMG_MANIFEST = {
    'player':        ('spr_player.png',           (48, 48)),
    'slime':         ('spr_enemy_slime.png',      (44, 44)),
    'bomber':        ('spr_enemy_bomber.png',     (44, 44)),
    'drone':         ('spr_enemy_drone.png',      (44, 44)),
    'boss':          ('spr_boss.png',             (104, 104)),

    'crate':         ('spr_crate.png',            (24, 24)),
    'barrel':        ('spr_barrel.png',           (24, 24)),
    'cover_pillar':  ('spr_cover_pillar.png',     (34, 34)),
    'cover_block':   ('spr_cover_block.png',      (34, 34)),
    'coin':          ('spr_coin.png',             (24, 24)),
    'diamond':       ('spr_diamond.png',          (24, 24)),
    'heart':         ('spr_heart.png',            (24, 24)),
    'energy':        ('spr_energy.png',           (24, 24)),
    'key':           ('spr_key.png',              (24, 24)),
    'chest':         ('spr_chest.png',            (24, 24)),
    'potion':        ('spr_potion.png',           (24, 24)),
    'potion_health': ('spr_potion_health.png',    (32, 32)),
    'potion_energy': ('spr_potion_energy.png',    (32, 32)),
    'basketball':    ('spr_basketball.png',       (32, 32)),
    'drink_nectar':  ('spr_drink_nectar.png',     (32, 32)),
    'drink_dew':     ('spr_drink_dew.png',        (32, 32)),
    'drink_soda':    ('spr_drink_soda.png',       (32, 32)),
    'drink_tea':     ('spr_drink_tea.png',        (32, 32)),

    'wpn_pistol':    ('wpn_pistol.png',           (32, 32)),
    'wpn_shotgun':   ('wpn_shotgun.png',          (32, 32)),
    'wpn_smg':       ('wpn_smg.png',              (32, 32)),
    'wpn_laser':     ('wpn_laser.png',            (32, 32)),
    'wpn_rocket':    ('wpn_rocket.png',           (32, 32)),
    'wpn_cannon':    ('wpn_cannon.png',           (32, 32)),

    # ---- 1.4 新增武器（需求 6）：素材表只有 6 格，所以新武器复用底图 ----
    # 用"同一张图 + 独立 key"的方式，让库里能查到；实际观感差异靠
    # 武器配色（spec.color）与子弹区分，像素风下足够辨识。
    'wpn_crossbow':  ('wpn_laser.png',            (32, 32)),
    'wpn_flamer':    ('wpn_smg.png',              (32, 32)),
    'wpn_railgun':   ('wpn_cannon.png',           (32, 32)),
    'wpn_blade':     ('wpn_shotgun.png',          (32, 32)),
    'wpn_plasma_blade': ('wpn_laser.png',         (32, 32)),

    'b_bullet':      ('bul_bullet.png',           (20, 20)),
    'b_bolt':        ('bul_bolt.png',             (20, 20)),
    'b_plasma':      ('bul_plasma.png',           (20, 20)),
    'b_laser':       ('bul_laser.png',            (20, 20)),
    'b_rocket':      ('bul_rocket.png',           (20, 20)),
    'b_hex':         ('bul_hex.png',              (20, 20)),

    'tile_floor':    ('tile_floor.png',           (32, 32)),
    'tile_floor_alt': ('tile_floor_alt.png',      (32, 32)),
    'tile_wall':     ('tile_wall.png',            (32, 32)),
    'tile_wall_top': ('tile_wall_top.png',        (32, 32)),
    'tile_door':     ('tile_door.png',            (32, 32)),

    'bg_title':      ('bg_title.png',             (640, 360)),
}

# 2.0 数据驱动的专属图集；旧键保留供旧存档与旧调用读取。
from . import weapon as _weapons, gamedata as _game_data, codex as _codex_data
for _key in _weapons.ORDER:
    IMG_MANIFEST['wpn_' + _key] = ('wpn_' + _key + '.png', (32, 32))
for _key in _game_data.CHAR_ORDER:
    IMG_MANIFEST['player_' + _key] = ('spr_player_' + _key + '.png', (48, 48))
for _key in _game_data.MAT_ORDER:
    IMG_MANIFEST['material_' + _key] = ('spr_material_' + _key + '.png', (24, 24))
for _key, _entry in _codex_data.ENEMY_CODEX.items():
    _size = (104, 104) if _entry[2] in ('boss', 'bigboss') else (44, 44)
    IMG_MANIFEST['enemy_' + _key] = ('spr_enemy_' + _key + '.png', _size)
for _key in _codex_data.COLLECTS:
    IMG_MANIFEST['collect_' + _key] = ('spr_collect_' + _key + '.png', (48, 48))
for _kind in _game_data.CHESTS:
    for _tier in ('normal', 'superb'):
        IMG_MANIFEST['chest_' + _kind + '_' + _tier] = (
            'spr_chest_' + _kind + '_' + _tier + '.png', (40, 36))
for _kind in ('spike', 'poison', 'shock', 'slow', 'flame'):
    IMG_MANIFEST['trap_' + _kind] = ('spr_trap_' + _kind + '.png', (42, 42))
for _scene in ('crust', 'sewer', 'facility', 'core', 'd_mine', 'd_lab', 'd_gift'):
    for _part in ('floor', 'floor_alt', 'wall', 'wall_top'):
        IMG_MANIFEST['tile_' + _part + '_' + _scene] = (
            'tile_' + _part + '_' + _scene + '.png', (32, 32))

# 缺图占位色（便于一眼看出是占位）
PLACEHOLDER_COLOR = {
    'player': (96, 200, 220), 'slime': (120, 220, 110), 'bomber': (220, 96, 80),
    'drone': (170, 120, 230), 'boss': (210, 90, 220),
}

# 供测试校验：游戏代码会引用到的全部贴图 key
def all_keys():
    from . import weapon as _W
    keys = set(IMG_MANIFEST.keys())
    for k in _W.ORDER:
        keys.add(_W.sprite_key(k))
    for spec in _W.WEAPONS.values():
        keys.add(spec.bullet)
    return sorted(keys)

FONT_CANDIDATES = [
    'font.ttf',
    '/Windows/Fonts/NotoSansSC-VF.ttf',
    '/Windows/Fonts/Noto Sans SC (TrueType).otf',
    '/Windows/Fonts/msyh.ttc',
    '/Windows/Fonts/simhei.ttf',
    '/System/Library/Fonts/PingFang.ttc',
    '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
]


class Assets:
    def __init__(self, root=None):
        self.root = root or self._default_root()
        self.img = {}
        self._scaled = {}
        self._fonts = {}
        self._font_path = None
        self.missing = []
        self.placeholder_keys = set()
        self._load_images()
        self._find_font()

    # -------------------------------------------------- 路径
    @staticmethod
    def _default_root():
        here = os.path.dirname(os.path.abspath(__file__))
        cands = [
            os.path.join(os.path.dirname(os.path.dirname(here)), 'assets'),
            os.path.join(os.path.dirname(here), 'assets'),
            os.path.join(here, 'assets'),
            os.path.join(os.getcwd(), 'assets'),
        ]
        try:
            import sys
            base = getattr(sys, '_MEIPASS', None)
            if base:
                cands.insert(0, os.path.join(base, 'assets'))
        except Exception:
            pass
        for c in cands:
            if os.path.isdir(c):
                return c
        return cands[0]

    # -------------------------------------------------- 加载
    def _placeholder(self, size, color, letter='?'):
        w, h = size
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        r = min(w, h) // 2
        pygame.draw.circle(s, color, (w // 2, h // 2), r)
        pygame.draw.circle(s, (20, 20, 26), (w // 2, h // 2), r, 2)
        pygame.draw.line(s, (255, 255, 255), (w // 2 - r // 2, h // 2),
                         (w // 2 + r // 2, h // 2), 2)
        pygame.draw.line(s, (255, 255, 255), (w // 2, h // 2 - r // 2),
                         (w // 2, h // 2 + r // 2), 2)
        return s

    def _load_images(self):
        for key, (fn, size) in IMG_MANIFEST.items():
            path = os.path.join(self.root, fn)
            surf = None
            if os.path.isfile(path):
                try:
                    surf = pygame.image.load(path)
                except Exception as exc:
                    _log_asset_exc('assets.load', exc, fn)
                    surf = None
                if surf is not None:
                    try:
                        surf = surf.convert_alpha()
                    except Exception:
                        # 没有显示模式时 convert_alpha 会失败——退化为使用原始
                        # Surface，绝不能因此变成占位图（否则玩家看到一屏灰圈）
                        pass
            if surf is None:
                self.missing.append(fn)
                self.placeholder_keys.add(key)
                surf = self._placeholder(size, PLACEHOLDER_COLOR.get(key, (140, 140, 160)), key[0])
            if surf.get_size() != size:
                surf = pygame.transform.smoothscale(surf, size)
            self.img[key] = surf

    def _find_font(self):
        for c in FONT_CANDIDATES:
            p = c if os.path.isabs(c) else os.path.join(self.root, c)
            if os.path.isfile(p):
                self._font_path = p
                return
        self._font_path = None

    # -------------------------------------------------- 取用
    def spr(self, key):
        s = self.img.get(key)
        if s is None:
            self.placeholder_keys.add(key)
            return self._placeholder((32, 32), (200, 80, 80))
        return s

    def scaled(self, key, w, h=None):
        """按目标尺寸缓存缩放（NEAREST，保持像素感）"""
        h = w if h is None else h
        ck = (key, w, h)
        s = self._scaled.get(ck)
        if s is None:
            src = self.spr(key)
            s = pygame.transform.scale(src, (max(1, w), max(1, h)))
            self._scaled[ck] = s
        return s

    def rot(self, key, w, h, deg):
        ck = (key, w, h, int(deg) % 360)
        s = self._scaled.get(ck)
        if s is None:
            s = pygame.transform.rotate(self.scaled(key, w, h), deg)
            self._scaled[ck] = s
        return s

    def flipped(self, key, w, h):
        """水平翻转（缓存）"""
        ck = ('#flip', key, w, h)
        s = self._scaled.get(ck)
        if s is None:
            s = pygame.transform.flip(self.scaled(key, w, h), True, False)
            self._scaled[ck] = s
        return s

    def tinted(self, key, w, h, tint, amount=0.72):
        """给贴图整体染色（缓存）。

        需求 8：每个场景的怪要"看起来不一样"。与其为 30+ 种怪各画一张
        PNG（资源管线爆炸、包体膨胀），不如复用 6 张基础贴图 + 场景色相
        偏移 —— 玩家一眼能分辨，成本近乎为零。

        tint: (r,g,b) 目标色；amount 是混色强度（0=原图，1=纯 tint）。
        用 BLEND_MULT 先压暗，再按 amount 叠一层 tint，保留原始明暗层次。
        """
        amt = max(0.0, min(1.0, float(amount)))
        ck = ('#tint', key, w, h, tuple(tint), round(amt, 3))
        s = self._scaled.get(ck)
        if s is not None:
            return s
        base = self.scaled(key, w, h)
        src = base.copy()
        # 1) 乘法压色：让原图的亮部/暗部结构保留下来
        mul = pygame.Surface(src.get_size(), pygame.SRCALPHA)
        mul.fill((int(tint[0]), int(tint[1]), int(tint[2]), 255))
        src.blit(mul, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        # 2) 按 amount 与原图混合，避免变成纯色块
        src.set_alpha(int(255 * amt))
        s = base.copy()
        s.blit(src, (0, 0))
        self._scaled[ck] = s
        return s

    def shaded(self, key, w, h, mul=(255, 255, 255), add=None):
        """亮度/色相微调（缓存）。mul 为乘法通道，add 为可选叠加。"""
        ck = ('#shade', key, w, h, tuple(mul), tuple(add) if add else None)
        s = self._scaled.get(ck)
        if s is not None:
            return s
        s = self.scaled(key, w, h).copy()
        lay = pygame.Surface(s.get_size(), pygame.SRCALPHA)
        lay.fill((int(mul[0]), int(mul[1]), int(mul[2]), 255))
        s.blit(lay, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        if add:
            lay2 = pygame.Surface(s.get_size(), pygame.SRCALPHA)
            lay2.fill((int(add[0]), int(add[1]), int(add[2]), 0))
            s.blit(lay2, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
        self._scaled[ck] = s
        return s

    def font(self, size, bold=False):
        ck = (size, bold)
        f = self._fonts.get(ck)
        if f is None:
            try:
                if self._font_path:
                    f = pygame.font.Font(self._font_path, size)
                    f.set_bold(bold)
                else:
                    f = pygame.font.SysFont('microsoftyahei,simhei,arial', size, bold=bold)
            except Exception:
                f = pygame.font.Font(None, size)
            self._fonts[ck] = f
        return f
