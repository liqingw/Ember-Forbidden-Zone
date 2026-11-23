# -*- coding: utf-8 -*-
"""劳大冰红茶的篮球：独立投射物，首次命中后至多弹向另一只怪物。"""
import math
import pygame


class Basketball:
    def __init__(self, x, y):
        self.x, self.y = float(x), float(y)
        self.alive = True
        self.life = 3.0
        self.hits = 0
        self.hit_ids = set()
        self.radius = 11.0
        self.dmg = 24.0
        self.spin = 0.0

    def update(self, game, dt):
        if not self.alive:
            return
        self.life -= dt
        if self.life <= 0:
            self.alive = False
            return
        targets = [e for e in game.enemies if e.alive and not getattr(e, 'invuln', False) and id(e) not in self.hit_ids]
        if not targets:
            self.alive = False
            return
        target = min(targets, key=lambda e: (e.x-self.x)**2 + (e.y-self.y)**2)
        dx, dy = target.x-self.x, target.y-self.y
        d = math.hypot(dx, dy)
        step = min(d, 390.0 * dt)
        if d > 0:
            self.x += dx / d * step
            self.y += dy / d * step
        self.spin += dt * 9.0
        if d - step <= self.radius + target.radius:
            self.hit_ids.add(id(target))
            self.hits += 1
            game._basket_chain = True
            try:
                rng = getattr(game, 'rng', None)
                hit_dmg = 81.0 if (rng is not None and rng.random() < 0.08) else self.dmg
                target.take_damage(hit_dmg, game)
            finally:
                game._basket_chain = False
            game.fx.burst(self.x, self.y, (246, 151, 53), n=10,
                          speed=135, life=.32, size=3)
            game.audio.play('hit')
            if self.hits >= 2:
                self.alive = False

    def draw(self, surf, cam, assets):
        if not self.alive:
            return
        x, y = int(self.x+cam[0]), int(self.y+cam[1])
        surf.blit(assets.scaled('basketball', 24, 24), (x-12, y-12))
