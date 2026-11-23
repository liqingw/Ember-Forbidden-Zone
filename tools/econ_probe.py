# -*- coding: utf-8 -*-
"""经济曲线实测探针。

用途：验证"金币易得"是否成立 —— 玩家首通主线能不能买得起
奖励副本 + 角色解锁，而不必把同一关反复刷。

对照 game.on_enemy_killed / on_boss_defeated 的真实掉落模型：
  · 每关敌人 n ≈ 14（含精英 2）
  · 小怪掉 1~3 枚（均值 2），面值 = coin_value(scene, stage)
  · 精英 +2 枚，面值 ×COIN_ELITE_MUL
  · 第 3 / 5 关各有一次首领爆 26 枚 × 面值 × COIN_BOSS_MUL
  · 每关约 3 个宝箱，均值 110 金
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from src.sk import chapter as C                                # noqa: E402
from src.sk import gamedata as G                               # noqa: E402

N_SMALL, N_ELITE = 12, 2
BOX_PER_STAGE, BOX_AVG = 3, 110


def stage_coin(scene_key, stage_idx):
    si = C.scene_index_of(scene_key)
    cv = C.coin_value(si, stage_idx)
    g = N_SMALL * 2 * cv + N_ELITE * 4 * cv * C.COIN_ELITE_MUL
    if C.stage_kind(stage_idx) in ('miniboss', 'boss'):
        g += 26 * cv * C.COIN_BOSS_MUL
    return g + BOX_PER_STAGE * BOX_AVG


def scene_coin(scene_key):
    return sum(stage_coin(scene_key, st)
               for st in range(C.STAGES_PER_SCENE))


def main():
    print('=' * 62)
    print(' 金币经济曲线实测')
    print('=' * 62)
    print('\n[单枚面值]')
    for si, s in enumerate(C.all_scenes()):
        vals = [C.coin_value(si, st) for st in range(C.STAGES_PER_SCENE)]
        print('  %-9s %s' % (s, vals))

    print('\n[场景金币产出]')
    total = 0
    for s in C.MAIN:
        v = scene_coin(s)
        total += v
        print('  %-9s %6d 金（累计 %6d）' % (s, v, total))
    main_total = total

    print('\n[副本产出]')
    dtotal = 0
    for s in list(C.DUNGEONS.keys()) + [C.BONUS]:
        v = scene_coin(s)
        dtotal += v
        print('  %-9s %6d 金' % (s, v))

    print('\n[收支平衡]')
    char_cost = sum(c['unlock'][1] for c in G.CHARACTERS.values()
                    if c['unlock'] and c['unlock'][0] == 'coin')
    print('  两个副本首通      : %6d 金' % (dtotal - scene_coin(C.BONUS)))
    print('  主线 4 场景首通   : %6d 金' % main_total)
    print('  ─────────────────────────────')
    print('  首通总产出        : %6d 金' % (main_total + dtotal -
                                          scene_coin(C.BONUS)))
    print('  奖励副本定价      : %6d 金  (占首通 %d%%)'
          % (C.BONUS_PRICE, round(C.BONUS_PRICE / main_total * 100)))
    print('  3 个金币角色      : %6d 金' % char_cost)
    print('  白品质武器升满    : %6d 金' % sum(G.QUALITIES['white']['up']))
    both = C.BONUS_PRICE + char_cost
    print('  奖励副本 + 3 角色 : %6d 金' % both)
    print('  => 首通主线后 %s 全部买下' %
          ('可以' if main_total >= both else
           '还差 %d 金' % (both - main_total)))
    print('\n  注：33 个角色/武器/材料上限远高于单周目产出，')
    print('      多周目刷取是设计内的长期目标，不是卡点。')
    print('=' * 62)
    return 0


if __name__ == '__main__':
    sys.exit(main())
