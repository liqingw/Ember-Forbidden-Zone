import random
import json
import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from tempfile import TemporaryDirectory

from src.sk.dungeon import Dungeon
from src.sk.route35 import choose_room, next_door
from src.sk.game import Game
from src.sk import save


class Route35Test(unittest.TestCase):
    def test_fixed_graph_result_for_cross_platform_comparison(self):
        graph = {
            (2, 2): ('start', 'ES'), (3, 2): ('normal', 'WES'),
            (4, 2): ('normal', 'W'), (2, 3): ('normal', 'NE'),
            (3, 3): ('normal', 'WN'),
        }
        rooms = {key: SimpleNamespace(kind=kind, doors=doors)
                 for key, (kind, doors) in graph.items()}
        d = SimpleNamespace(scene_key='d_mine', stage_idx=1,
                            start_key=(2, 2), goal_key=(4, 2), rooms=rooms)
        self.assertEqual(choose_room(d), (2, 3))

    def test_candidate_is_optional_and_deterministic(self):
        found = 0
        for seed in range(100):
            d = Dungeon(1, random.Random(seed), 'd_mine', 1)
            key = choose_room(d)
            self.assertEqual(key, choose_room(d))
            if key:
                found += 1
                self.assertEqual(d.room(*key).kind, 'normal')
                self.assertIsNotNone(next_door(d, d.start_key, key))
            self.assertEqual(choose_room(Dungeon(1, random.Random(seed), 'sewer', 1)), None)
        self.assertGreaterEqual(found, 80)

    def test_choice_checkpoint_and_first_reward(self):
        with TemporaryDirectory() as tmp, patch.object(save, 'data_dir', return_value=tmp):
            g = Game(headless=True, seed=1, enable_audio=False)
            g.store = None
            g.profile = save.new_profile(0, 'route-test')
            g.level_state = {'scene': 'd_mine', 'stage_idx': 1, 'diff': (1.0, 1.0)}
            g._start_floor(1, floor_seed=0)
            self.assertEqual(g.state, 'route_choice')
            g._choose_route(1)
            cp = dict(g.profile['run_checkpoint'])
            self.assertEqual(cp['route_state'], 'survey')
            g._start_floor(1, floor_seed=0, capture=False)
            g._restore_floor_checkpoint(cp)
            self.assertEqual(g.route_state, 'survey')
            self.assertFalse(g.route_sealed)
            g._stage_done = False
            g.route_sealed = True
            g._finish_stage()
            self.assertEqual(g.profile['materials'].get('crystal'), 2)
            g._stage_done = False
            g._finish_stage()
            self.assertEqual(g.profile['materials'].get('crystal'), 2)

    def test_backup_merge_keeps_claim_for_same_profile_only(self):
        with TemporaryDirectory() as tmp:
            main = os.path.join(tmp, 'profiles.json')
            claimed = save.new_profile(0, 'route-test')
            claimed['route_first_rewards'] = ['mine_survey_02']
            advanced = dict(claimed)
            advanced['route_first_rewards'] = []
            advanced['played'] = 10.0
            with open(main, 'w', encoding='utf-8') as f:
                json.dump({'slots': [advanced], 'last': 0}, f)
            with open(os.path.join(tmp, 'profiles.bak.json'), 'w', encoding='utf-8') as f:
                json.dump({'slots': [claimed], 'last': 0}, f)
            store = save.SaveStore(path=main)
            self.assertEqual(store.data['slots'][0]['route_first_rewards'],
                             ['mine_survey_02'])
            self.assertEqual(store.data['slots'][0]['played'], 10.0)
            different = dict(claimed, created=claimed['created'] - 1)
            self.assertFalse(save.merge_route_claims(advanced, different))

    def test_regular_and_abandoned_route_give_no_survey_crystals(self):
        for route_state in ('normal', 'survey'):
            with self.subTest(route_state=route_state), TemporaryDirectory() as tmp, \
                    patch.object(save, 'data_dir', return_value=tmp):
                g = Game(headless=True, seed=1, enable_audio=False)
                g.store = None
                g.profile = save.new_profile(0, 'route-test')
                g.level_state = {'scene': 'd_mine', 'stage_idx': 1,
                                 'diff': (1.0, 1.0)}
                g._start_floor(1, floor_seed=0)
                g.route_state = route_state
                g.route_sealed = False
                g._finish_stage()
                self.assertEqual(g.profile['materials'].get('crystal', 0), 0)
                self.assertNotIn('mine_survey_02',
                                 g.profile['route_first_rewards'])


if __name__ == '__main__':
    unittest.main()
