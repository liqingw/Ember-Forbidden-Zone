# -*- coding: utf-8 -*-
"""数学 / 碰撞 / 绘制小工具"""
import logging
import math
import pygame

from . import settings as S

TILE = S.TILE


# ------------------------------------------------------------ 基础数学
def clamp(v, a, b):
    return a if v < a else (b if v > b else v)


def lerp(a, b, t):
    return a + (b - a) * t


def dist(ax, ay, bx, by):
    return math.hypot(bx - ax, by - ay)


def dist2(ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    return dx * dx + dy * dy


def ang_of(dx, dy):
    return math.atan2(dy, dx)


def vec_from_ang(a, length=1.0):
    return math.cos(a) * length, math.sin(a) * length


def ang_lerp(a, b, t):
    """角度插值（走最短弧）"""
    d = (b - a + math.pi) % (2 * math.pi) - math.pi
    return a + d * t


def approach(cur, target, step):
    if cur < target:
        return min(cur + step, target)
    return max(cur - step, target)


# ------------------------------------------------------------ 圆形 vs 瓦片碰撞
def circle_solid(cx, cy, r, solid):
    """圆是否与任何实心瓦片相交（最近点法）"""
    x0 = int(math.floor((cx - r) / TILE))
    x1 = int(math.floor((cx + r) / TILE))
    y0 = int(math.floor((cy - r) / TILE))
    y1 = int(math.floor((cy + r) / TILE))
    rr = r * r
    for ty in range(y0, y1 + 1):
        for tx in range(x0, x1 + 1):
            if not solid(tx, ty):
                continue
            nx = clamp(cx, tx * TILE, tx * TILE + TILE)
            ny = clamp(cy, ty * TILE, ty * TILE + TILE)
            if (cx - nx) ** 2 + (cy - ny) ** 2 < rr:
                return True
    return False


def _slide(cur, delta, test):
    """沿单轴移动 delta，遇阻用二分法逼近可移动的最大距离。

    注意：二分法成立的前提是"起点不在障碍里"。若起点本身已在障碍内
    （例如被传送/击退推进了墙里），test(cur+mid) 会恒为 True，hi 一路
    收缩到 0，位移永远是 0 —— 表现为**永久卡死**。
    因此这里先做一次"起点脱困"：若起点已经碰撞，直接沿该方向尝试
    整体位移（不做二分），让玩家有机会自己挤出去。
    """
    if delta == 0.0:
        return cur
    if test(cur):
        # 起点已陷入障碍：放弃二分，直接尝试整段位移，能挪多少算多少
        return cur + delta
    if not test(cur + delta):
        return cur + delta
    lo, hi = 0.0, delta
    for _ in range(7):
        mid = (lo + hi) * 0.5
        if test(cur + mid):
            hi = mid
        else:
            lo = mid
    return cur + lo


def circle_move(x, y, r, dx, dy, solid):
    """分轴滑动移动，返回 (x, y)"""
    x = _slide(x, dx, lambda nx: circle_solid(nx, y, r, solid))
    y = _slide(y, dy, lambda ny: circle_solid(x, ny, r, solid))
    return x, y


def collide_test(x, y, r, solid, blockers=None):
    """圆是否撞到实心瓦片 或 任何圆形阻挡物 blockers=[(x,y,r), ...]"""
    if solid is not None and circle_solid(x, y, r, solid):
        return True
    if blockers:
        for b in blockers:
            bx, by, br = b[0], b[1], b[2]
            rr = r + br
            if (x - bx) ** 2 + (y - by) ** 2 < rr * rr:
                return True
    return False


def move_circle(x, y, r, dx, dy, solid, blockers=None):
    """分轴滑动移动（同时考虑瓦片与圆形阻挡物）"""
    x = _slide(x, dx, lambda nx: collide_test(nx, y, r, solid, blockers))
    y = _slide(y, dy, lambda nx: collide_test(x, nx, r, solid, blockers))
    return x, y


# ------------------------------------------------------------ 脱困
def find_free_spot(x, y, r, solid, blockers=None, max_r=None, step=None):
    """从 (x,y) 出发向外螺旋搜索一个不碰撞的落点。

    用于：传送/进门落点、存档恢复、击退推出界外——这些情况都可能把
    实体放进墙里，而一旦圆心落在实心瓦片内，普通滑动移动会失效
    （见 _slide 注释）。返回 (nx, ny)；在 max_r 内找不到则返回 None。
    搜索是确定性的（固定 16 向 + 半径递增），不依赖随机数。
    """
    if not collide_test(x, y, r, solid, blockers):
        return x, y
    if step is None:
        step = TILE * 0.5
    if max_r is None:
        max_r = TILE * 5
    radius = step
    while radius <= max_r:
        ring = max(8, int(16 * radius / step))
        for i in range(ring):
            a = 2.0 * math.pi * i / ring
            nx = x + math.cos(a) * radius
            ny = y + math.sin(a) * radius
            if not collide_test(nx, ny, r, solid, blockers):
                return nx, ny
        radius += step
    return None


def unstick(x, y, r, solid, blockers=None, fallback=None):
    """把可能卡在障碍里的实体拉出来，返回 (x, y)。

    优先就近螺旋找空位；找不到再退回 fallback（通常是房间中心）。
    这是"防卡死"的最后一道防线，保证任何情况下实体都不会被永久锁死。
    """
    spot = find_free_spot(x, y, r, solid, blockers)
    if spot is not None:
        return spot
    if fallback is not None:
        fx, fy = fallback
        spot = find_free_spot(fx, fy, r, solid, blockers, max_r=TILE * 8)
        if spot is not None:
            return spot
        return fx, fy
    return x, y


# ------------------------------------------------------------ 绘制辅助
_shadow_cache = {}
_shadow_alpha_cache = {}
_scratch_cache = {}
_flash_white_cache = {}
_flash_tmp_cache = {}
_logger = logging.getLogger('sk')
if not _logger.handlers:
    _logger.addHandler(logging.NullHandler())
_logged_exc_keys = set()


def log_exc(tag, exc, detail=''):
    """记录去重后的异常警告，绝不向调用方抛出异常。"""
    try:
        key = (tag, type(exc).__name__, str(detail))
        if key in _logged_exc_keys:
            return
        if len(_logged_exc_keys) >= 256:
            _logged_exc_keys.clear()
        _logged_exc_keys.add(key)
        _logger.warning('[%s] %s (%s: %s)', tag, detail, type(exc).__name__, exc)
    except Exception:
        pass


def shadow_surf(w, h):
    """缓存的软阴影（椭圆，中心浓边缘淡）"""
    key = (w, h)
    s = _shadow_cache.get(key)
    if s is None:
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        steps = max(3, h // 2)
        for i in range(steps, 0, -1):
            t = i / steps
            a = int(120 * (1.0 - t) ** 1.6) + 8
            rw, rh = int(w * t), int(h * t)
            if rw < 2 or rh < 2:
                continue
            pygame.draw.ellipse(s, (0, 0, 0, a),
                                ((w - rw) // 2, (h - rh) // 2, rw, rh))
        _shadow_cache[key] = s
    return s


def draw_shadow(surf, cx, cy, rx, ry=None, alpha=255):
    ry = rx * 0.5 if ry is None else ry
    w, h = max(4, int(rx * 2)), max(3, int(ry * 2))
    a = int(clamp(alpha, 0, 255))
    if a < 255:
        key = (w, h, a)
        s = _shadow_alpha_cache.get(key)
        if s is None:
            if len(_shadow_alpha_cache) >= 128:
                _shadow_alpha_cache.clear()
            s = shadow_surf(w, h).copy()
            s.set_alpha(a)
            _shadow_alpha_cache[key] = s
    else:
        s = shadow_surf(w, h)
    surf.blit(s, (int(cx - w / 2), int(cy - h / 2)))


def scratch_surf(w, h):
    """按尺寸复用临时 SRCALPHA 画布（每次返回前清空，禁止跨帧持有或同尺寸嵌套使用）。"""
    w = max(1, int(w))
    h = max(1, int(h))
    key = (w, h)
    s = _scratch_cache.get(key)
    if s is None:
        if len(_scratch_cache) >= 64:
            _scratch_cache.clear()
        s = pygame.Surface(key, pygame.SRCALPHA)
        _scratch_cache[key] = s
    else:
        s.fill((0, 0, 0, 0))
    return s


def blit_hit_flash(surf, img, dest, alpha):
    """使用缓存画布绘制受击闪白叠加，避免每帧分配 SRCALPHA Surface。"""
    a = int(clamp(alpha, 0, 255))
    size = img.get_size()
    white = _flash_white_cache.get(size)
    if white is None:
        if len(_flash_white_cache) >= 32:
            _flash_white_cache.clear()
        white = pygame.Surface(size, pygame.SRCALPHA)
        _flash_white_cache[size] = white
    white.fill((255, 255, 255, a))

    tmp = _flash_tmp_cache.get(size)
    if tmp is None:
        if len(_flash_tmp_cache) >= 32:
            _flash_tmp_cache.clear()
        tmp = pygame.Surface(size, pygame.SRCALPHA)
        _flash_tmp_cache[size] = tmp
    else:
        tmp.fill((0, 0, 0, 0))
    tmp.blit(img, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
    tmp.blit(white, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
    surf.blit(tmp, dest)


def blit_center(surf, img, x, y, off_y=0.0):
    surf.blit(img, (int(x - img.get_width() / 2),
                    int(y - img.get_height() / 2 + off_y)))


def blit_rot(surf, img, x, y, deg, scale=1.0):
    """旋转绘制（角度为数学角，逆时针为正）"""
    if scale != 1.0:
        img = pygame.transform.scale(
            img, (max(1, int(img.get_width() * scale)),
                  max(1, int(img.get_height() * scale))))
    out = pygame.transform.rotate(img, -deg)
    surf.blit(out, (int(x - out.get_width() / 2), int(y - out.get_height() / 2)))


def text_shadow(font, surf, s, color, x, y, anchor='topleft', shadow=(0, 0, 0, 190)):
    a = font.render(s, True, shadow)
    b = font.render(s, True, color)
    r = b.get_rect(**{anchor: (x, y)})
    for dx, dy in ((1, 1), (2, 0), (0, 2)):
        surf.blit(a, (r.x + dx, r.y + dy))
    surf.blit(b, r)
    return r


def panel(surf, rect, fill=S.C_PANEL, border=S.C_PANEL_HI, radius=6, width=2):
    pygame.draw.rect(surf, fill, rect, border_radius=radius)
    if width > 0:
        pygame.draw.rect(surf, border, rect, width=width, border_radius=radius)


def bar(surf, rect, ratio, fg, bg=(40, 38, 52), border=None, radius=3):
    ratio = clamp(ratio, 0.0, 1.0)
    pygame.draw.rect(surf, bg, rect, border_radius=radius)
    w = int(rect[2] * ratio)
    if w > 0:
        pygame.draw.rect(surf, fg, (rect[0], rect[1], w, rect[3]), border_radius=radius)
    if border:
        pygame.draw.rect(surf, border, rect, width=1, border_radius=radius)
