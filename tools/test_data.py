# -*- coding: utf-8 -*-
"""防卡死 + 存档 + 数据层单元测试（T13-T20）

这些测试不依赖 pygame 显示，专测纯逻辑层。
"""
import os
import random
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, 'src'))

from sk import save as SV          # noqa: E402
from sk import gamedata as G       # noqa: E402
from sk import chapter as C        # noqa: E402
from sk import chapter as CH       # noqa: E402  （旧测试用 CH 别名）
from sk import codex as CX         # noqa: E402
from sk import progress as PR      # noqa: E402

TMPDIR = os.path.join(ROOT, '_tmp')
os.makedirs(TMPDIR, exist_ok=True)

FAILED = []
PASSED = [0]


def check(cond, msg):
    if cond:
        PASSED[0] += 1
    else:
        FAILED.append(msg)
        print('   [FAIL] ' + msg)


def section(t):
    print('\n=== ' + t + ' ===')


# ---------------------------------------------------------------- T13 存档槽位
def t13_save_slots():
    section('T13 存档：3 槽位 / 建档 / 覆盖 / 原子写')
    p = os.path.join(tempfile.mkdtemp(prefix='t13_', dir=TMPDIR), '_t13.json')

    st = SV.SaveStore(path=p)
    check(st.slots() == [None, None, None], 'T13 初始 3 个空槽')
    check(st.free_slot() == 0, 'T13 首个空槽是 0')

    st.create(0, '甲')
    st.create(1, '乙')
    st.create(2, '丙')
    check(st.free_slot() is None, 'T13 三槽占满后没有空槽')

    # 覆盖第 2 槽
    st.create(1, '乙改')
    check(st.get(1)['name'] == '乙改', 'T13 可覆盖指定槽位')

    # 落盘 + 重载
    st2 = SV.SaveStore(path=p)
    check(st2.get(0)['name'] == '甲', 'T13 重新加载后槽 0 数据仍在')
    check(st2.get(1)['name'] == '乙改', 'T13 重新加载后覆盖结果保留')
    check(st2.get(2)['name'] == '丙', 'T13 重新加载后槽 2 数据仍在')

    # 删除
    st2.delete(1)
    check(st2.get(1) is None, 'T13 可删除槽位')
    check(st2.free_slot() == 1, 'T13 删除后该槽重新可用')

    # 新档默认值完备（需求 4/5/6/9/10 的字段都要在）
    p0 = SV.new_profile(0, 'x')
    for k in ('coins', 'diamonds', 'materials', 'chars', 'weapons',
              'codex', 'collects', 'showcase', 'settings', 'run'):
        check(k in p0, f'T13 新档包含字段 {k}')
    check(set(p0['settings']) >= {'music', 'sfx', 'shake', 'joystick',
                                  'joy_sens'},
          'T13 设置含音乐/音效/震动/摇杆')

    # 旧档迁移：缺字段应补齐且不丢已有值
    old = {'id': 0, 'name': '旧', 'coins': 999}
    mig = SV._migrate(old)
    check(mig['coins'] == 999, 'T13 迁移不覆盖已有值')
    check('diamonds' in mig, 'T13 迁移补齐缺失字段')
    return p


# ---------------------------------------------------------------- T14 武器品质
def t14_weapon_quality():
    section('T14 武器：7 档品质 / 培养消耗 / 满级')
    check(len(G.QUALITY_ORDER) == 7, 'T14 共 7 档品质')
    # 品质越高，伤害倍率越高
    muls = [G.quality_of(q)['mul'] for q in G.QUALITY_ORDER]
    check(all(b > a for a, b in zip(muls, muls[1:])), 'T14 品质倍率严格递增')
    # 品质越高，升级越贵
    costs = [G.upgrade_cost(q, 0)[0] for q in G.QUALITY_ORDER]
    check(all(b > a for a, b in zip(costs, costs[1:])), 'T14 升级金币严格递增')
    # 满级边界
    for q in G.QUALITY_ORDER:
        mx = G.max_level(q)
        check(G.upgrade_cost(q, mx) is None, f'T14 {q} 满级后无升级消耗')
        check(G.is_max(q, mx), f'T14 {q} 满级判定正确')
        check(not G.is_max(q, mx - 1), f'T14 {q} 未满级判定正确')
        check('perk' in G.quality_of(q), f'T14 {q} 有满级额外效果说明')
    # 每一级材料表都要够长
    ok = True
    for q in G.QUALITY_ORDER:
        spec = G.quality_of(q)
        for k, arr in spec['mats'].items():
            if len(arr) != spec['max_lv']:
                ok = False
    check(ok, 'T14 每档材料消耗表长度与满级匹配')


# ---------------------------------------------------------------- T15 角色
def t15_characters():
    section('T15 角色：8 个 / 解锁条件 / 初始武器唯一')
    check(len(G.CHAR_ORDER) == 8, 'T15 共 8 个角色（含 2 个收集解锁角色）')
    starters = [G.char(k)['starter'] for k in G.CHAR_ORDER]
    check(len(set(starters)) == len(starters), 'T15 各角色初始武器不重复')
    check(G.char('scout')['unlock'] is None, 'T15 初始角色无需解锁')

    kinds = {}
    for k in G.CHAR_ORDER[1:]:
        u = G.char(k)['unlock']
        kinds[u[0]] = kinds.get(u[0], 0) + 1
    check(kinds.get('coin', 0) == 3, 'T15 三个金币解锁的角色')
    check(kinds.get('diamond', 0) == 1, 'T15 一个钻石解锁的角色')
    check(kinds.get('craft', 0) == 1, 'T15 一个材料合成角色')

    # 资源不足时不可解锁
    prof = {'coins': 0, 'diamonds': 0, 'materials': {}, 'chars': ['scout']}
    for k in G.CHAR_ORDER[1:]:
        okc, _ = G.can_unlock(prof, k)
        check(not okc, f'T15 空档案不能解锁 {G.char(k)["name"]}')

    # 资源充足时可解锁并正确扣费
    prof2 = {'coins': 5000, 'diamonds': 200, 'materials': {},
             'chars': ['scout']}
    G.do_unlock(prof2, 'engineer')
    check('engineer' in prof2['chars'], 'T15 金币解锁成功')
    check(prof2['coins'] == 5000 - 800, 'T15 金币正确扣除')
    G.do_unlock(prof2, 'ghost')
    check(prof2['diamonds'] == 200 - 120, 'T15 钻石正确扣除')

    # 合成角色
    prof3 = {'coins': 1200, 'diamonds': 0, 'chars': ['scout'],
             'materials': {'relic': 5, 'core': 9, 'prism': 3}}
    okc, why = G.can_unlock(prof3, 'prime')
    check(okc, f'T15 材料充足可合成协议行者（{why}）')
    G.do_unlock(prof3, 'prime')
    check(prof3['materials'].get('relic', 0) == 2, 'T15 合成正确扣材料 relic')
    check(prof3['materials'].get('core', 0) == 3, 'T15 合成正确扣材料 core')

    # 材料不足
    prof4 = {'coins': 1200, 'diamonds': 0, 'chars': ['scout'],
             'materials': {'relic': 1}}
    okc, why = G.can_unlock(prof4, 'prime')
    check(not okc and '材料不足' in why, 'T15 材料不足时给出原因')


# ---------------------------------------------------------------- T16 宝箱
def t16_chests():
    section('T16 宝箱：5 类 × 2 档 / 概率 / 掉落')
    check(len(G.CHEST_ORDER) == 5, 'T16 共 5 类宝箱')
    kinds = set()
    for k in G.CHEST_ORDER:
        for t in ('normal', 'superb'):
            check(t in G.CHESTS[k], f'T16 {k} 有 {t} 档')
            kinds.add((k, t))
    check(len(kinds) == 10, 'T16 共 10 种宝箱组合')

    rng = random.Random(7)
    from collections import Counter
    c = Counter()
    for _ in range(8000):
        c[G.roll_chest(rng, 0.0)] += 1
    total = sum(c.values())
    # 普通箱应远多于极品箱
    normal = sum(v for (k, t), v in c.items() if t == 'normal')
    superb = sum(v for (k, t), v in c.items() if t == 'superb')
    check(normal > superb * 1.5, 'T16 普通箱明显多于极品箱')
    # 收集箱必须极其稀有（需求 9：极小概率）
    collect = sum(v for (k, t), v in c.items() if k == 'collect')
    rate = collect / float(total)
    check(rate < 0.05, f'T16 收集箱概率极低（{rate*100:.2f}%）')
    # 所有组合都应能被抽到
    check(len(c) == 10, f'T16 所有 10 种组合均可达（实际 {len(c)}）')

    # 开箱产出结构
    for k in G.CHEST_ORDER:
        for t in ('normal', 'superb'):
            loot = G.chest_loot(random.Random(3), k, t, 3)
            check(isinstance(loot, dict), f'T16 {k}/{t} 开箱返回 dict')
    # 货币箱给钱
    loot = G.chest_loot(random.Random(1), 'coin', 'superb', 1)
    check(loot['coins'] > 0, 'T16 极品货币箱给金币')
    # 医疗箱回血
    loot = G.chest_loot(random.Random(1), 'heal', 'normal', 1)
    check(loot['heal'] > 0, 'T16 医疗箱给回血')
    # 材料箱给材料
    loot = G.chest_loot(random.Random(1), 'material', 'superb', 1)
    check(sum(loot['mats'].values()) > 0, 'T16 极品材料箱给材料')


# ---------------------------------------------------------------- T17 章节
def t17_chapter():
    section('T17 章节：35 关 / 难度递增 / 副本条件')
    check(len(CH.MAIN) == 4, 'T17 4 个主线场景')
    check(len(CH.DUNGEONS) == 2, 'T17 2 个副本场景')
    check(CH.total_stages() == 35, 'T17 主线+副本共 35 关')
    check(CH.STAGES_PER_SCENE == 5, 'T17 每场景 5 关')
    # 主题场景总数：4 主线 + 2 副本 + 1 奖励 = 7
    check(len(CH.MAIN) + len(CH.DUNGEONS) + 1 == 7, 'T17 共 7 个主题场景')

    # 每个场景 1~4 关普通、第 3 关小 boss、第 5 关大 boss
    for i in range(5):
        k = CH.stage_kind(i)
        if i == 2:
            check(k == 'miniboss', 'T17 第 3 关是小 Boss')
        elif i == 4:
            check(k == 'boss', 'T17 第 5 关是大 Boss')
        else:
            check(k == 'normal', f'T17 第 {i+1} 关是普通关')

    # 难度随场景与关内序号递增（全局单调）
    ok = True
    prev = (0, 0)
    for si in range(7):
        for st in range(5):
            cur = CH.difficulty(si, st)
            if cur[0] <= prev[0] or cur[1] <= prev[1]:
                ok = False
            prev = cur
    check(ok, 'T17 难度随场景/关卡严格递增')

    # 剧情文本齐全
    for sc in list(CH.MAIN) + list(CH.DUNGEONS) + [CH.BONUS]:
        info = CH.scene_info(sc)
        check(info['name'] != sc, f'T17 {sc} 有中文场景名')
        check(len(info['enter']) > 0, f'T17 {sc} 有进场剧情')
        check(len(info['clear']) > 0, f'T17 {sc} 有通关剧情')
    check(len(CH.INTRO) >= 5, 'T17 有开场叙事')

    # 副本解锁顺序（必须先解锁才出现在顺序里）
    prof = {'unlocked_dungeons': [], 'cleared_scenes': []}
    order0 = CH.scene_order(prof)
    check(order0 == CH.MAIN, 'T17 未解锁副本时顺序等于主线')
    prof['unlocked_dungeons'] = ['d_mine']
    check('d_mine' in CH.scene_order(prof), 'T17 解锁后副本出现在顺序中')

    # 副本条件判定
    dk = 'd_mine'
    prof2 = {'cleared_scenes': ['sewer'], 'unlocked_dungeons': []}
    check(not CH.check_dungeon_unlock(prof2, dk, {'kills': 10, 'cleared': True}),
          'T17 击杀不足时副本不解锁')
    check(not CH.check_dungeon_unlock(
              prof2, dk, {'kills': 95, 'cleared': True, 'trap_hits': 12}),
          'T17 击杀达标但踩陷阱过多时副本不解锁')
    check(CH.check_dungeon_unlock(
              prof2, dk, {'kills': 95, 'cleared': True, 'trap_hits': 2}),
          'T17 满足全部条件时矿井解锁')
    prof3 = {'cleared_scenes': [], 'unlocked_dungeons': []}
    check(not CH.check_dungeon_unlock(prof3, dk, {'kills': 999, 'cleared': True}),
          'T17 未通关前置场景时副本不解锁')

    # 条件自洽性：所有条件引用的键都必须是"该前置场景真实存在的东西"
    for dkey, dinfo in CH.DUNGEONS.items():
        cond_keys = set(dinfo['cond'].keys())
        check(cond_keys <= {'kills', 'cleared', 'no_death', 'low_hp',
                            'trap_hits', 'bomber_hits'},
              f'T17 {dkey} 条件键合法（{sorted(cond_keys)}）')
        check(bool(dinfo.get('cond_text')) and bool(dinfo.get('hint')),
              f'T17 {dkey} 同时有正式条件文案与提示')
        # 条件里提到的怪必须真的在该前置场景的怪池里
        after = dinfo['after']
        scene_mobs = set(CH.SCENE_MOBS[after]['small']) | \
            set(CH.SCENE_MOBS[after]['elite'])
        if 'bomber_hits' in cond_keys:
            check(bool(scene_mobs & {'bomber', 'bomber_big'}),
                  f'T17 {dkey} 要求躲避自爆，但前置场景没有自爆类怪')

    # 条件难度：击杀门槛必须明显高于"顺手通关"的水平
    for dkey, dinfo in CH.DUNGEONS.items():
        k = dinfo['cond'].get('kills', 0)
        check(k >= 90, f'T17 {dkey} 击杀门槛有挑战性（{k}）')

    # 奖励副本条件（改为金币支付）
    p = {'cleared_scenes': ['crust'], 'bonus_unlocked': False}
    check(not CH.bonus_unlockable(p), 'T17 未通关最终场景时奖励副本不可解锁')
    p['cleared_scenes'] = ['crust', 'core']
    check(CH.bonus_unlockable(p), 'T17 通关最终场景后奖励副本可解锁')
    p['bonus_unlocked'] = True
    check(not CH.bonus_unlockable(p), 'T17 已解锁后不再重复解锁')


# ---------------------------------------------------------------- T17b 污染减益
def t17b_pollution():
    section('T17b 污染渐近减益：浓度递增 / 减益单调加深')
    # 主线污染浓度必须随场景深度递增
    pcts = [CH.POLLUTION[s]['pct'] for s in CH.MAIN]
    check(all(b > a for a, b in zip(pcts, pcts[1:])),
          f'T17b 主线污染浓度递增（{pcts}）')
    check(CH.POLLUTION[CH.BONUS]['pct'] == 0,
          'T17b 奖励副本无污染（浓度 0）')

    # 同一场景内，关卡越深减益越重
    for sc in list(CH.MAIN) + list(CH.DUNGEONS):
        prev = None
        for st in range(CH.STAGES_PER_SCENE):
            p = CH.pollution(sc, st)
            if prev is not None:
                check(p['hp_cut'] >= prev['hp_cut'] and
                      p['spd'] <= prev['spd'] + 1e-9 and
                      p['drain'] >= prev['drain'] - 1e-9,
                      f'T17b {sc} 第 {st+1} 关减益不轻于上一关')
            prev = p

    # 污染最深处必须真的有明显减益（不能是"名义上的"）
    deep = CH.pollution('core', 4)
    check(deep['hp_cut'] >= 3, f'T17b 污染原点生命上限削减明显（{deep["hp_cut"]}）')
    check(deep['spd'] <= 0.92, f'T17b 污染原点移速明显下降（{deep["spd"]}）')
    check(deep['drain'] > 0, 'T17b 污染原点有持续侵蚀')
    check(len(CH.pollution_lines('core', 4)) >= 3,
          'T17b 污染文案包含多条减益')

    # 无污染场景不应产生任何减益
    check(CH.pollution_lines(CH.BONUS, 4) == [], 'T17b 奖励副本无减益文案')
    g0 = CH.pollution('crust', 0)
    check(g0['hp_cut'] == 0 and g0['spd'] == 1.0 and g0['drain'] == 0.0,
          'T17b 地表第 1 关无减益')

    # 警告文案
    w = CH.pollution_warning('sewer', 0)
    check(w is not None and '21%' in w[0], f'T17b 下水道警告含浓度读数（{w}）')
    check(CH.pollution_warning(CH.BONUS, 2) is None,
          'T17b 无减益场景不产生警告')


# ---------------------------------------------------------------- T18 图鉴
def t18_codex():
    section('T18 图鉴 / 收集品 / 怪物分配')
    check(len(CX.ENEMY_CODEX) >= 18, f'T18 怪物图鉴丰富（{len(CX.ENEMY_CODEX)} 条）')
    # 每个场景的怪都必须在图鉴里
    bad = []
    for sc, m in CX.SCENE_ENEMIES.items():
        for k in list(m['small']) + list(m['elite']) + \
                 ([m['boss']] if m['boss'] else []):
            if k not in CX.ENEMY_CODEX:
                bad.append((sc, k))
    check(not bad, f'T18 场景引用的怪物都在图鉴中（缺失 {bad}）')

    # 各场景的怪必须不同（需求 8：每个场景小怪/精英/boss 不同）
    seen = {}
    for sc in CH.MAIN:
        m = CX.SCENE_ENEMIES[sc]
        sig = (tuple(sorted(m['small'])), tuple(sorted(m['elite'])), m['boss'])
        check(sig not in seen, f'T18 {CH.scene_label(sc)} 的怪池与前面场景不同')
        seen[sig] = sc

    # 隐藏奖励怪：两种，掉高级图纸
    rare = [k for k, v in CX.ENEMY_CODEX.items() if v[2] == 'rare']
    check(len(rare) == 2, f'T18 恰有 2 种隐藏奖励怪（{rare}）')

    # 收集品
    check(len(CX.COLLECTS) >= 8, f'T18 收集品数量充足（{len(CX.COLLECTS)}）')
    check(len(CX.collect_pool('superb')) > 0, 'T18 有极品收集品')
    rng = random.Random(5)
    c = CX.roll_collect(rng, 'superb')
    check(CX.COLLECTS[c][1] == 'superb', 'T18 抽极品收集品只出极品')

    # 提示文案
    n, d = CX.enemy_intro('origin')
    check(n and d, 'T18 怪物有名称+简介提示')
    n, d = CX.material_intro('core')
    check(n and d, 'T18 材料有名称+简介提示')
    n, d = CX.collect_intro('music_box')
    check(n and d, 'T18 收集品有名称+简介提示')


# ---------------------------------------------------------------- T19 天赋
def t19_talents():
    section('T19 天赋：三选一 / 叠加 / 生效')
    check(len(CX.TALENTS) >= 12, f'T19 天赋池充足（{len(CX.TALENTS)}）')
    rng = random.Random(11)
    for _ in range(20):
        ks = CX.roll_talents(rng, [], 3)
        check(len(ks) == 3, 'T19 每次抽 3 个天赋')
        check(len(set(ks)) == 3, 'T19 三个天赋不重复')

    # 同一天赋最多叠 3 层
    ks = CX.roll_talents(rng, ['dmg_up'] * 3, 3)
    check('dmg_up' not in ks, 'T19 叠满 3 层后不再出现')

    # 生效
    s = CX.new_run_stats()
    CX.apply_talent(s, 'dmg_up')
    CX.apply_talent(s, 'dmg_up')
    check(abs(s['dmg_mul'] - 0.30) < 1e-6, 'T19 数值天赋可叠加')
    CX.apply_talent(s, 'hp_up')
    check(s['max_hp'] == 2, 'T19 上限类天赋生效')
    CX.apply_talent(s, 'thorns')
    check('thorns' in s['flags'], 'T19 标记类天赋生效')
    CX.apply_talent(s, 'dash_up')
    check(abs(s['dash_cd_mul'] + 0.30) < 1e-6, 'T19 减益型（冷却）天赋生效')
    # 基础暴击存在
    check(s['crit'] > 0, 'T19 基础暴击率非零')


# ---------------------------------------------------------------- T19b 经济曲线
def t19b_economy():
    print('\n=== T19b 经济曲线：金币面值递增 / 定价可达 ===')
    # 面值必须随全局关卡序号严格递增
    vals = []
    for si in range(7):
        for st in range(CH.STAGES_PER_SCENE):
            vals.append(CH.coin_value(si, st))
    check(all(b >= a for a, b in zip(vals, vals[1:])),
          f'T19b 金币面值单调不减（首 {vals[0]} 末 {vals[-1]}）')
    check(vals[-1] > vals[0], 'T19b 金币面值确实随深度增长')
    check(CH.coin_value(0, 0) == 2, 'T19b 第一关面值符合 2.5 经济')
    check(CH.coin_value(6, 4) >= 9, 'T19b 最深关面值随进度增长')

    # 精英 / 首领倍率
    check(CH.COIN_ELITE_MUL >= 1.5, 'T19b 精英掉币有明显加成')
    check(CH.COIN_BOSS_MUL >= 3.0, 'T19b 首领掉币远高于杂兵')

    # 副本金币定价必须落在"可达成"区间。
    # 预算模型对齐 game.on_enemy_killed / on_boss_defeated 的真实掉落：
    #   · 三层合计多个战斗房，每房三轮；保守按每关 120 普通怪、10 精英算
    #   · 普通怪平均 0.5 枚，精英平均 1.5 枚
    #   · 第 3 / 第 5 关首领爆 12 枚
    #   · 货币箱更少，按每关 4 箱、均值 20 金保守估计
    N_SMALL, N_ELITE = 120, 10
    BOX_PER_STAGE, BOX_AVG = 4, 20
    budget = 0
    for si in range(len(CH.MAIN)):
        for st in range(CH.STAGES_PER_SCENE):
            cv = CH.coin_value(si, st)
            g = (N_SMALL * 0.5 * cv
                 + N_ELITE * 1.5 * cv * CH.COIN_ELITE_MUL)
            if CH.stage_kind(st) in ('miniboss', 'boss'):
                g += 12 * cv * CH.COIN_BOSS_MUL
            budget += g + BOX_PER_STAGE * BOX_AVG
    check(budget > CH.BONUS_PRICE,
          f'T19b 主线首通预算({budget}) 足以覆盖奖励副本定价'
          f'({CH.BONUS_PRICE})')
    # 但不该廉价到"随手就买"——仍要占首通产出的可观份额
    check(CH.BONUS_PRICE >= budget * 0.15,
          f'T19b 奖励副本仍有取舍成本（≥ 首通产出 15%，'
          f'当前 {round(CH.BONUS_PRICE / budget * 100)}%）')
    # 且不能贵到"必须重刷"——首通产出还应够买下 3 个金币角色
    char_cost = sum(c['unlock'][1] for c in G.CHARACTERS.values()
                    if c['unlock'] and c['unlock'][0] == 'coin')
    check(budget >= CH.BONUS_PRICE + char_cost * 0.5,
          f'T19b 首通产出({budget}) 能同时支撑奖励副本('
          f'{CH.BONUS_PRICE}) 与部分角色解锁({char_cost})')

    # 4 个主线场景都能算出面值（scene_index_of 不越界）
    for s in CH.MAIN:
        si = CH.scene_index_of(s)
        check(0 <= si < 7, f'T19b {s} 场景下标合法（{si}）')
        check(CH.coin_value(si, 4) >= CH.coin_value(si, 0),
              f'T19b {s} 关内面值递增')


# ---------------------------------------------------------------- T19c 1.3 新特性
def t19c_v13():
    print('\n=== T19c 1.3：抗污染天赋 / 叙事绑定 / 货币上限 ===')
    # ---- 抗污染天赋必须存在且语义正确
    for k in ('pur_resist', 'pur_purge', 'pur_ward'):
        check(k in CX.TALENTS, f'T19c 抗污染天赋 {k} 存在')
        check(CX.TALENTS[k].get('desc'), f'T19c {k} 有说明文案')
        check('color' in CX.TALENTS[k], f'T19c {k} 有配色')

    # 抗性天赋能累加，且被夹到上限
    s = CX.new_run_stats()
    check(s.get('pur_resist', None) == 0.0, 'T19c run_stats 含 pur_resist 初值')
    for _ in range(5):
        CX.apply_talent(s, 'pur_resist')
    check(abs(CX.pur_resist_of(s) - CX.PUR_RESIST_CAP) < 1e-6,
          f'T19c 抗性堆叠被夹到上限 {CX.PUR_RESIST_CAP}')

    # 半抗性：所有减益按比例折减
    pol = CH.pollution('core', 4)
    half = CX.new_run_stats()
    half['pur_resist'] = 0.5
    hc, sp, rg, dr = CX.pur_tint_amount(pol, half)
    check(hc == int(round(pol['hp_cut'] * 0.5)),
          f'T19c 生命削减减半（{pol["hp_cut"]} -> {hc}）')
    check(abs(dr - pol['drain'] * 0.5) < 1e-6,
          f'T19c 侵蚀减半（{pol["drain"]} -> {dr}）')
    check(sp > pol['spd'] and rg > pol['regen'],
          'T19c 移速/回能朝 1.0 收敛')
    check(sp < 1.0, 'T19c 半抗性不会让减益变成增益')

    # 无污染场景：无论抗性多少都是满值
    g0 = CX.pur_tint_amount(CH.pollution('d_gift', 0), half)
    check(g0 == (0, 1.0, 1.0, 0.0), 'T19c 无污染场景不受抗性影响')

    # 污染共鸣：无天赋=0，有天赋按浓度给伤害
    ward = CX.new_run_stats()
    check(CX.pur_ward_bonus(pol, ward) == 0.0, 'T19c 无共鸣天赋时无加成')
    CX.apply_talent(ward, 'pur_ward')
    b = CX.pur_ward_bonus(pol, ward)
    check(b > 0.0, f'T19c 共鸣在污染原点给伤害加成（+{b:.3f}）')
    shallow = CX.pur_ward_bonus(CH.pollution('crust', 0), ward)
    check(shallow < b, 'T19c 浅层共鸣收益更低（浓度越低越少）')

    # 净化循环 flag
    check(not CX.has_pur_purge(CX.new_run_stats()), 'T19c 默认没有净化循环')
    pg = CX.new_run_stats()
    CX.apply_talent(pg, 'pur_purge')
    check(CX.has_pur_purge(pg), 'T19c 点出净化循环后 flag 生效')

    # ---- 叙事绑定
    for dk in CH.DUNGEONS:
        b = CH.dungeon_bind(dk)
        check(b is not None, f'T19c {dk} 有叙事绑定数据')
        cards = CH.dungeon_bind_cards(dk)
        check(len(cards) >= 3, f'T19c {dk} 机制卡 ≥3 张（{len(cards)}）')
        check(bool(CH.dungeon_tip(dk) if hasattr(CH, 'dungeon_tip')
                  else b.get('tip')), f'T19c {dk} 有一句话战术提示')
        for c in cards:
            check(c['kind'] in ('enemy', 'trap'), f'T19c {dk} 卡片类型合法')
            check(c['name'] and c['name'] != c['key'],
                  f'T19c {dk} 卡片取到了正式名（{c["name"]}）')
            check(len(c['desc']) >= 8, f'T19c {dk} 卡片说明够具体')
    # 绑定对象必须真实存在于前置场景
    for dk, d in CH.DUNGEONS.items():
        after = d['after']
        sc = CX.SCENE_ENEMIES.get(after, {})
        pool = set(sc.get('small', []) + sc.get('elite', []) +
                   ([sc['boss']] if sc.get('boss') else []))
        for k, _ in d['bind'].get('enemies', []):
            check(k in pool,
                  f'T19c {dk} 绑定的怪 {k} 确实出现在 {after}')
        from sk import hazard as HZ
        traps = set(HZ.TRAP_BY_SCENE.get(after, []))
        for k, _ in d['bind'].get('traps', []):
            check(k in traps,
                  f'T19c {dk} 绑定的陷阱 {k} 确实出现在 {after}')

    # ---- 货币上限
    check(G.COIN_CAP > 0 and G.DIAMOND_CAP > 0, 'T19c 货币上限为正')
    check(G.COIN_CAP >= 50000,
          f'T19c 金币上限足够支撑多周目积累（{G.COIN_CAP}）')
    check(G.clamp_coin(0) == 0, 'T19c clamp 下界为 0')
    check(G.clamp_coin(-99) == 0, 'T19c 负数夹到 0')
    check(G.clamp_coin(G.COIN_CAP + 1) == G.COIN_CAP, 'T19c 超上限夹到上限')
    v, got = G.add_coin(G.COIN_CAP - 10, 50)
    check(v == G.COIN_CAP and got == 10, 'T19c 加币封顶且回报实际入账')
    v, got = G.add_coin(G.COIN_CAP, 100)
    check(v == G.COIN_CAP and got == 0, 'T19c 已满时入账为 0')
    v, got = G.add_coin(100, 0)
    check(v == 100 and got == 0, 'T19c 加 0 不变')
    check(G.clamp_diamond(999999) == G.DIAMOND_CAP, 'T19c 钻石同样封顶')

    # 单周目产出不会溢出上限（否则上限就是设计事故）
    budget = 0
    for si in range(len(CH.MAIN)):
        for st in range(CH.STAGES_PER_SCENE):
            cv = CH.coin_value(si, st)
            g2 = 12 * 2 * cv + 2 * 4 * cv * CH.COIN_ELITE_MUL
            if CH.stage_kind(st) in ('miniboss', 'boss'):
                g2 += 26 * cv * CH.COIN_BOSS_MUL
            budget += g2 + 3 * 110
    check(budget < G.COIN_CAP,
          f'T19c 单周目主线产出({budget}) 不溢出上限({G.COIN_CAP})')


# ---------------------------------------------------------------- T20 进度推进
def t20_progress():
    print('\n=== T20 关卡推进 / 副本解锁 / 奖励副本 ===')
    p = SV.new_profile(0, 'tester')

    # --- 展示顺序：1.4 起固定为 MAIN + DUNGEONS + BONUS（与解锁无关）
    check(PR.scene_order(p) == list(C.MAIN) + list(C.DUNGEONS.keys()) + [C.BONUS],
          'T20 展示顺序 = 4 主线 + 2 副本 + 奖励关')
    # 1.4：7 个主题场景（4 主线 + 2 副本 + 1 奖励），共 7×5=35 关
    check(len(C.all_scenes()) == 7, 'T20 场景总数 = 7（%s）' % C.all_scenes())
    check(C.STAGES_PER_SCENE == 5, 'T20 每场景 5 关（35 关）')
    # 初始已解锁场景只有主线第一站（需求 1：不允许选关，线性推进）
    check(PR.visible_order(p) == [C.MAIN[0]], 'T20 初始已解锁场景 = 主线第 1 站')
    check(PR.level_state(p) is None, 'T20 未选场景时 level_state 为 None')

    # --- 开始第一场景
    check(PR.start_scene(p, 'crust'), 'T20 可以开始 crust')
    ls = PR.level_state(p)
    check(ls['scene'] == 'crust' and ls['stage_idx'] == 0, 'T20 从第 1 关开始')
    check(ls['kind'] == 'normal', 'T20 第 1 关是普通关')
    check(abs(ls['diff'][0] - 1.0) < 1e-6, 'T20 第 1 关难度倍率为 1.0')

    # --- 场景内推进 5 关
    kinds = []
    for i in range(C.STAGES_PER_SCENE):
        PR.next_stage(p, 'crust', i)
        kinds.append(PR.level_state(p)['kind'])
    check(kinds == ['normal', 'normal', 'miniboss', 'normal', 'boss'],
          'T20 5 关类型 = 普通/普通/小Boss/普通/大Boss（%s）' % kinds)

    # --- 通关整个场景
    PR.next_stage(p, 'crust', 4)
    ev, _pl = PR.advance(p)
    check(ev == 'scene_clear', 'T20 打完第 5 关触发 scene_clear')
    check(PR.is_scene_cleared(p, 'crust'), 'T20 crust 已标记通关')

    # --- 场景间难度严格递增（全局单调）
    diffs = []
    order = list(C.MAIN)
    for si, sk in enumerate(order):
        for st in range(C.STAGES_PER_SCENE):
            diffs.append(C.difficulty(si, st)[0])
    mono = all(diffs[i] > diffs[i - 1] for i in range(1, len(diffs)))
    check(mono, 'T20 主线 20 关难度严格单调递增（%.2f -> %.2f）'
                % (diffs[0], diffs[-1]))

    # --- 副本解锁进度条（新的多条件打勾结构）
    items, ok, text, hint = PR.dungeon_progress(p, 'd_mine')
    check(not ok, 'T20 矿井条件尚未达成')
    check(len(items) >= 3, f'T20 矿井条件拆成多条可打勾项（{len(items)}）')
    check(any('腐化下水道' in it[0] or '通关' in it[0] for it in items),
          'T20 条件里包含前置场景通关项')
    check(all(len(it) == 4 for it in items), 'T20 每条进度项是 4 元组')
    check('腐化下水道' in text, 'T20 副本条件文案含前置场景名')
    check(bool(hint), 'T20 副本提供设计提示（hint）')

    # 只满足击杀，不满足陷阱上限 -> 仍不解锁
    PR.merge_scene_best(p, 'sewer', {'kills': 95, 'trap_hits': 12})
    PR._mark_cleared(p, 'sewer')
    check(PR.scan_unlocks(p) == [], 'T20 踩陷阱过多时矿井仍不解锁')

    # 补上陷阱上限 -> 解锁
    PR.merge_scene_best(p, 'sewer', {'kills': 95, 'trap_hits': 2})
    new = PR.scan_unlocks(p)
    check('d_mine' in new, 'T20 满足全部条件后矿井解锁（%s）' % new)
    check('d_mine' in PR.visible_order(p), 'T20 解锁后出现在已解锁场景里')
    # 插入位置：紧随 sewer 之后
    so = PR.visible_order(p)
    check(so.index('d_mine') == so.index('sewer') + 1,
          'T20 矿井插在下水道之后（%s）' % so)

    # merge_scene_best 语义：只增不减 / 越小越好取最小
    PR.merge_scene_best(p, 'sewer', {'kills': 10, 'trap_hits': 99})
    sb = p['scene_best']['sewer']
    check(sb['kills'] == 95, 'T20 击杀取历史最大（不被小值顶掉）')
    check(sb['trap_hits'] == 2, 'T20 陷阱命中取历史最小（不被大值顶掉）')

    # d_lab：击杀 + 被自爆波及上限 + 残血通关
    items, ok, _t, _h = PR.dungeon_progress(p, 'd_lab')
    check(not ok, 'T20 冷库条件尚未达成')
    PR.merge_scene_best(p, 'facility', {'kills': 150, 'bomber_hits': 1})
    PR._mark_cleared(p, 'facility')
    check(PR.scan_unlocks(p) == [], 'T20 差"残血通关"时冷库不解锁')
    PR.merge_scene_best(p, 'facility', {'kills': 150, 'bomber_hits': 1,
                                        'low_hp': True})
    check(PR.scan_unlocks(p) and 'd_lab' in p['unlocked_dungeons'],
          'T20 补上残血通关后冷库解锁')

    # --- 奖励副本：需打完 core，且以**金币**支付
    p2 = SV.new_profile(1, 'buyer')
    check(not PR.can_buy_bonus(p2, want=True), 'T20 未通关核心时不能买奖励副本')
    PR._mark_cleared(p2, C.MAIN[-1])
    check(PR.bonus_available(p2), 'T20 通关核心后奖励副本开放')
    check(PR.bonus_price(p2) == C.BONUS_PRICE, 'T20 售价等于配置值')
    check(C.BONUS_PRICE_DIA == 0, 'T20 奖励副本不额外收钻石')
    check(not PR.can_buy_bonus(p2, want=True), 'T20 金币不足时不能买')
    check(PR.bonus_missing(p2)[0] == C.BONUS_PRICE, 'T20 差额提示正确')
    p2['coins'] = C.BONUS_PRICE
    check(PR.can_buy_bonus(p2, want=True), 'T20 金币够时可以买')
    check(PR.buy_bonus(p2), 'T20 购买成功')
    check(p2['coins'] == 0, f'T20 购买后扣光金币（{p2["coins"]}）')
    check(p2['bonus_unlocked'], 'T20 bonus_unlocked 置位')
    check(C.BONUS in PR.visible_order(p2), 'T20 奖励副本进入已解锁场景')
    check(not PR.can_buy_bonus(p2, want=True), 'T20 不能重复购买')

    # --- 剧情接口
    name, sub, lines, tint = PR.scene_story('crust', 'enter')
    check(name == '地表残骸' and len(lines) == 3, 'T20 场景进场剧情可读')
    il = PR.intro_lines()
    check(len(il) == len(C.INTRO) and len(il) >= 7,
          'T20 开场叙事 %d 行（≥7）' % len(il))
    ni = PR.enemy_intro('slime')
    check(ni and '小怪' in ni[0], 'T20 怪物提示带类别标签（%s）' % (ni[0] if ni else ''))

    # --- 奖励副本单独成关：打完它应触发 game_clear
    PR.start_scene(p2, C.BONUS)
    PR.next_stage(p2, C.BONUS, 4)
    ev, pl = PR.advance(p2)
    check(ev == 'game_clear', 'T20 打完奖励副本触发 game_clear')
    check(p2['run'] is None, 'T20 game_clear 后清空 run（回客厅）')

    # --- 存档往返：进度字段不丢
    p2['run'] = None
    PR.merge_scene_best(p2, 'sewer', {'kills': 95, 'trap_hits': 3})
    progress_path = os.path.join(tempfile.mkdtemp(prefix='t20_', dir=TMPDIR), 'prog_test.json')
    s = SV.SaveStore(path=progress_path)
    s.data['slots'][0] = p2
    s.save()
    s2 = SV.SaveStore(path=progress_path)
    q = s2.get(0)
    check(q['bonus_unlocked'] is True, 'T20 存档往返保留 bonus_unlocked')
    check(q['unlocked_dungeons'] == p2['unlocked_dungeons'],
          'T20 存档往返保留副本解锁列表')
    check(q['scene_best'] == p2['scene_best'], 'T20 存档往返保留场景最好成绩')
    check(set(q.keys()) >= {'visited_scenes', 'cleared_scenes', 'story_seen'},
          'T20 新进度字段齐全')
    # 副本条件的追踪字段也要能往返
    check('trap_hits' in q['scene_best'].get('sewer', {}),
          'T20 存档往返保留陷阱命中统计')


# ---------------------------------------------------------------- 主流程
def main():
    print('=' * 62)
    print('数据层 / 存档 / 防卡死 单元测试')
    print('=' * 62)
    tmp = t13_save_slots()
    t14_weapon_quality()
    t15_characters()
    t16_chests()
    t17_chapter()
    t17b_pollution()
    t19b_economy()
    t19c_v13()
    t18_codex()
    t19_talents()
    t20_progress()

    # 清理
    for f in (tmp, tmp + '.tmp'):
        try:
            if os.path.isfile(f):
                os.remove(f)
        except Exception:
            pass

    print('\n' + '=' * 62)
    if FAILED:
        print(f'失败项（{len(FAILED)}）：')
        for m in FAILED:
            print('   x ' + m)
    print(f'结果：{PASSED[0]}/{PASSED[0] + len(FAILED)} 项通过')
    print('=' * 62)
    return 1 if FAILED else 0


if __name__ == '__main__':
    sys.exit(main())
