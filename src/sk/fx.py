# -*- coding: utf-8 -*-
"""特效：粒子 / 冲击环 / 飘字 / 屏幕震动 / 命中闪白"""
import math
import random

import pygame

from . import settings as S
from . import utils as U


class Particle:
    __slots__ = ('x', 'y', 'vx', 'vy', 'life', 'max_life', 'color',
                 'size', 'drag', 'grav', 'shape', 'fade')

    def __init__(self, x, y, vx, vy, life, color, size=3,
                 drag=2.4, grav=0.0, shape='square', fade=True):
        self.x, self.y = x, y
        self.vx, self.vy = vx, vy
        self.life = self.max_life = life
        self.color = color
        self.size = size
        self.drag = drag
        self.grav = grav
        self.shape = shape
        self.fade = fade

    def update(self, dt):
        k = max(0.0, 1.0 - self.drag * dt)
        self.vx *= k
        self.vy *= k
        self.vy += self.grav * dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.life -= dt
        return self.life > 0

    def draw(self, surf, cam=(0.0, 0.0)):
        t = self.life / self.max_life
        a = int(255 * (t if self.fade else 1.0))
        s = max(1, int(self.size * (0.35 + 0.65 * t)))
        if a <= 4:
            return
        col = (self.color[0], self.color[1], self.color[2], a)
        x, y = self.x + cam[0], self.y + cam[1]
        if self.shape == 'circle':
            tmp = U.scratch_surf(s * 2, s * 2)
            pygame.draw.circle(tmp, col, (s, s), s)
            surf.blit(tmp, (int(x - s), int(y - s)))
        else:
            tmp = U.scratch_surf(s, s)
            tmp.fill(col)
            surf.blit(tmp, (int(x - s / 2), int(y - s / 2)))


class Ring:
    __slots__ = ('x', 'y', 'r0', 'r1', 'life', 'max_life', 'color', 'width')

    def __init__(self, x, y, r0, r1, life, color, width=2):
        self.x, self.y = x, y
        self.r0, self.r1 = r0, r1
        self.life = self.max_life = life
        self.color = color
        self.width = width

    def update(self, dt):
        self.life -= dt
        return self.life > 0

    def draw(self, surf, cam=(0.0, 0.0)):
        t = 1.0 - self.life / self.max_life
        r = U.lerp(self.r0, self.r1, t)
        a = int(220 * (1.0 - t))
        if r < 1 or a <= 4:
            return
        size = int(r * 2) + 6
        tmp = U.scratch_surf(size, size)
        pygame.draw.circle(tmp, (self.color[0], self.color[1], self.color[2], a),
                           (size // 2, size // 2), int(r), max(1, int(self.width * (1 - t) + 1)))
        surf.blit(tmp, (int(self.x + cam[0] - size / 2),
                        int(self.y + cam[1] - size / 2)))


class FloatText:
    __slots__ = ('x', 'y', 'text', 'color', 'life', 'max_life', 'font', 'vy')

    def __init__(self, x, y, text, color, font, life=0.8, vy=-34.0):
        self.x, self.y = x, y
        self.text = text
        self.color = color
        self.font = font
        self.life = self.max_life = life
        self.vy = vy

    def update(self, dt):
        self.y += self.vy * dt
        self.vy *= max(0.0, 1.0 - 2.2 * dt)
        self.life -= dt
        return self.life > 0

    def draw(self, surf, cam=(0.0, 0.0)):
        t = self.life / self.max_life
        img = self.font.render(self.text, True, self.color)
        sh = self.font.render(self.text, True, (0, 0, 0))
        a = int(255 * min(1.0, t * 2.2))
        img.set_alpha(a)
        sh.set_alpha(int(a * 0.7))
        x, y = int(self.x + cam[0] - img.get_width() / 2), int(self.y + cam[1])
        surf.blit(sh, (x + 1, y + 1))
        surf.blit(img, (x, y))


class FX:
    """特效总控。坐标一律使用「房间局部像素坐标」。"""

    def __init__(self):
        self.parts = []
        self.rings = []
        self.texts = []
        self.shake = 0.0
        self.shake_x = 0.0
        self.shake_y = 0.0
        self.flash = 0.0
        self.flash_color = (255, 255, 255)
        self._rng = random.Random(20240923)

    # ------------------------------------------------ 生成
    def burst(self, x, y, color, n=8, speed=110.0, life=0.4, size=3,
              spread=math.tau, base_ang=0.0, drag=2.6, grav=0.0, shape='square'):
        for _ in range(max(0, n)):
            a = base_ang + self._rng.uniform(-spread / 2, spread / 2)
            sp = speed * self._rng.uniform(0.35, 1.25)
            self.parts.append(Particle(x, y,
                                       math.cos(a) * sp, math.sin(a) * sp,
                                       life * self._rng.uniform(0.7, 1.3),
                                       color, size, drag, grav, shape))
        if len(self.parts) > 900:
            del self.parts[:len(self.parts) - 900]

    def sparks(self, x, y, color, n=6, ang=0.0):
        self.burst(x, y, color, n=n, speed=150, life=0.26, size=2,
                   spread=1.1, base_ang=ang, drag=4.0)

    def smoke(self, x, y, n=5, color=(96, 92, 104)):
        self.burst(x, y, color, n=n, speed=42, life=0.6, size=4,
                   drag=2.0, grav=-22.0, shape='circle')

    def blood(self, x, y, color, n=7, ang=None):
        self.burst(x, y, color, n=n, speed=125, life=0.45, size=3,
                   spread=math.tau if ang is None else 1.4,
                   base_ang=ang or 0.0, drag=3.2, grav=180.0, shape='circle')

    def ring(self, x, y, r0, r1, life, color, width=2):
        self.rings.append(Ring(x, y, r0, r1, life, color, width))

    def arc_if_any(self, x, y, ang, reach, arc_deg, color):
        """近战扇形挥砍特效（需求 6：近战的视觉表现）。

        用一串沿扇形铺开的小粒子模拟"刀光"，比纯圆环更能读出方向。
        """
        n = max(8, int(reach * 0.32))
        half = math.radians(max(10.0, arc_deg) * 0.5)
        for i in range(n):
            t = (i / (n - 1)) * 2.0 - 1.0
            a = ang + t * half
            r = reach * (0.72 + 0.28 * self._rng.random())
            px = x + math.cos(a) * r
            py = y + math.sin(a) * r
            self.parts.append(Particle(
                px, py, math.cos(a) * 40.0, math.sin(a) * 40.0,
                0.20, color, 3, 6.0, 0.0, 'square'))
        if len(self.parts) > 900:
            del self.parts[:len(self.parts) - 900]

    def text(self, x, y, s, color, font, life=0.8):
        if len(self.texts) > 60:
            del self.texts[:len(self.texts) - 60]
        self.texts.append(FloatText(x, y, s, color, font, life))

    def add_shake(self, mag):
        self.shake = min(14.0, self.shake + mag)

    def add_flash(self, a, color=(255, 255, 255)):
        self.flash = max(self.flash, a)
        self.flash_color = color

    def clear(self):
        self.parts.clear()
        self.rings.clear()
        self.texts.clear()
        self.shake = 0.0
        self.shake_x = self.shake_y = 0.0
        self.flash = 0.0

    # ------------------------------------------------ 更新 / 绘制
    def update(self, dt):
        self.parts = [p for p in self.parts if p.update(dt)]
        self.rings = [r for r in self.rings if r.update(dt)]
        self.texts = [t for t in self.texts if t.update(dt)]
        if self.shake > 0.01:
            self.shake = max(0.0, self.shake - 42.0 * dt)
            m = self.shake
            self.shake_x = self._rng.uniform(-m, m)
            self.shake_y = self._rng.uniform(-m, m)
        else:
            self.shake = 0.0
            self.shake_x = self.shake_y = 0.0
        self.flash = max(0.0, self.flash - dt * 3.4)

    def draw_under(self, surf, cam=(0.0, 0.0)):
        for r in self.rings:
            r.draw(surf, cam)

    def draw_over(self, surf, cam=(0.0, 0.0)):
        for p in self.parts:
            p.draw(surf, cam)
        for t in self.texts:
            t.draw(surf, cam)
