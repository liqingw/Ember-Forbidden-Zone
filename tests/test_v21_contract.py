"""2.1 cross-platform data and interaction contract."""
import unittest

from src.sk import chapter, codex, dungeon, weapon
from src.sk.pickup import Pickup


class V21Contract(unittest.TestCase):
    def test_fifty_distinct_weapons_and_rarity_curve(self):
        self.assertGreaterEqual(len(weapon.ORDER), 50)
        self.assertEqual(len(set(weapon.ORDER)), len(weapon.ORDER))
        self.assertGreaterEqual(sum(weapon.WEAPONS[k].melee for k in weapon.ORDER), 12)
        sizes = [len(weapon.QUALITY_POOL[q]) for q in
                 ('white', 'green', 'blue', 'purple', 'gold', 'red')]
        self.assertTrue(all(a > b for a, b in zip(sizes, sizes[1:])), sizes)
        self.assertGreaterEqual(sizes[-1], 7)

    def test_two_bosses_per_theme(self):
        for scene in chapter.CHAPTER_STORY:
            self.assertEqual(chapter.STAGES_PER_SCENE, 5)
            self.assertEqual(chapter.stage_kind(2), 'miniboss')
            self.assertEqual(chapter.stage_kind(4), 'boss')
            mini = dungeon.SCENE_MINIBOSS[scene]
            big = dungeon.SCENE_BOSS[scene]
            self.assertNotEqual(mini, big)
            self.assertIn(mini, codex.ENEMY_CODEX)
            self.assertIn(big, codex.ENEMY_CODEX)

    def test_weapon_requires_interaction(self):
        self.assertTrue(Pickup(0, 0, 'weapon', wkey='blade').is_interact)


if __name__ == '__main__':
    unittest.main()
