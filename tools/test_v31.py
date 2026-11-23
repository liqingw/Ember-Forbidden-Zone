"""Focused 3.1 health and character skill regression checks."""
import os
import sys
from pathlib import Path

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
ROOT = Path(__file__).resolve().parents[1]
os.environ['APPDATA'] = str(ROOT / '_tmp' / 'test_v31')
sys.path.insert(0, str(ROOT / 'src'))

from sk import character_skills as CS
from sk.game import Game
from sk.pickup import Pickup
from sk.hud import _heart, HEART_EMPTY, HEART_FULL
import pygame


def main():
    game = Game(headless=True, seed=31, enable_audio=False)
    game.profile = None
    game.start_run(scene='crust', stage_idx=0)
    game.state = 'playing'
    pl = game.player
    cap = pl.max_hp
    pl.hp = cap
    Pickup(pl.x, pl.y, 'heart', 2)._collect(game)
    assert pl.max_hp == cap and pl.hp == cap, 'full-health pickup changed cap'
    pl.hp = max(1, cap - 4)
    Pickup(pl.x, pl.y, 'heart', 2)._collect(game)
    assert pl.max_hp == cap and pl.hp == min(cap, max(1, cap - 4) + 2)
    game._apply_pollution(None, 0)
    assert pl.max_hp == cap and pl.hp <= cap, 'room recalculation changed health'

    game._restore_floor_checkpoint({
        'player': {'hp': 999, 'max_hp': 999, 'energy': 999,
                   'max_energy': 999},
        'drinks': {}, 'run_stats': {},
    })
    assert pl.max_hp == cap and pl.hp == cap, 'legacy checkpoint restored bad cap'
    assert pl.energy <= pl.max_energy, 'legacy checkpoint restored bad energy cap'

    canvas = pygame.Surface((20, 20), pygame.SRCALPHA)
    _heart(canvas, 0, 0, 1)
    assert tuple(canvas.get_at((10, 4)))[:3] == tuple(HEART_EMPTY), 'half heart missing gray side'
    canvas.fill((0, 0, 0, 0))
    _heart(canvas, 0, 0, 2)
    assert tuple(canvas.get_at((10, 4)))[:3] == tuple(HEART_FULL[0]), 'full heart not red'

    class Target:
        def __init__(self):
            self.x, self.y = pl.x + 50, pl.y
            self.hp = 100
            self.alive = True

        def take_damage(self, damage, *_):
            self.hp -= damage

    for key in CS.SKILLS:
        game.char_key = key
        game.char_skill_cd = 0
        target = Target()
        game.enemies = [target]
        pl.aim = 0
        pl.hp = max(1, cap - 4)
        pl.energy = 0
        pl.iframes = 0
        assert CS.activate(game), key
        assert game.char_skill_cd == CS.SKILLS[key][1], key
        assert not CS.activate(game), key + ' bypassed cooldown'
        if key in ('scout', 'engineer', 'prime', 'archivist'):
            assert pl.energy > 0, key + ' did not restore energy'
        if key in ('engineer', 'ranger', 'prime', 'archivist', 'seedkeeper'):
            assert target.hp < 100, key + ' did not damage target'
        if key in ('medic', 'seedkeeper'):
            assert pl.hp > max(1, cap - 4), key + ' did not heal'
        if key == 'ghost':
            assert pl.iframes >= 2.5, 'ghost did not grant invulnerability'
    print('3.1 health and eight character skill checks passed')


if __name__ == '__main__':
    main()
