# -*- coding: utf-8 -*-
"""游戏数据层：货币、材料、武器品质与培养、角色、宝箱分级。

这里只放**纯数据 + 纯函数**，不依赖 pygame，方便被存档/界面/测试共用。
"""
import random

# ================================================================ 货币
CURRENCY = {
    'coin': ('金币', 'common', '随处可见的通用货币，用来买角色和强化'),
    'diamond': ('钻石', 'rare', '稀有货币，只在深层与首领身上出现'),
}

# 持有上限（1.3 需求 3：金币需要一个回收/封顶口，超出后不再增加）
#
# 取值依据（见 tools/econ_probe.py）：
#   · 单周目主线首通 ≈ 24140 金；打通两个副本再 +19660
#   · 当前全部可消费项 ≈ 角色 5000 + 奖励副本 6500 + 武器培养（白满 1900 起）
#   · 顶级武器（璀璨升满）单把就要 100 万+，所以上限不能太低，
#     否则"攒钱升好枪"这条长线被掐断
# 璀璨武器后期单次强化可超过十万，封顶必须高于完整培养成本。
COIN_CAP = 9999999
DIAMOND_CAP = 9999


def clamp_coin(v):
    """把金币夹到 [0, COIN_CAP]。"""
    return max(0, min(COIN_CAP, int(v)))


def clamp_diamond(v):
    return max(0, min(DIAMOND_CAP, int(v)))


def add_coin(cur, gain):
    """加金币并封顶，返回 (新值, 实际入账)。"""
    cur = int(cur) if cur else 0
    if gain <= 0:
        return clamp_coin(cur), 0
    v = clamp_coin(cur + int(gain))
    return v, max(0, v - clamp_coin(cur))

# ================================================================ 材料
# tier: 1 常见 / 2 少见 / 3 稀有 / 4 极稀有
MATERIALS = {
    'scrap':    ('废铁', 1, '污染物里捡到的金属碎片，最基础的强化料'),
    'fiber':    ('纤维束', 1, '韧性极佳的合成纤维，常见于低级容器'),
    'circuit':  ('电路板', 2, '还能用的控制核心，精英怪身上常有'),
    'crystal':  ('污染结晶', 2, '凝固的污染能量，触碰有轻微刺痛'),
    'alloy':    ('合金锭', 3, '高强度合金，只有首领级才掉落'),
    'core':     ('协议核心', 3, '旧世界的智能核心，武器进化的关键'),
    'prism':    ('棱镜晶核', 4, '折射污染的奇异结晶，璀璨级强化的必需品'),
    'relic':    ('遗物碎片', 4, '不明文明的残片，据说能拼出什么东西'),
}
MAT_ORDER = ['scrap', 'fiber', 'circuit', 'crystal', 'alloy', 'core',
             'prism', 'relic']


def mat_name(k):
    return MATERIALS.get(k, (k, 1, ''))[0]


def mat_tier(k):
    return MATERIALS.get(k, (k, 1, ''))[1]


# ================================================================ 武器品质
# 参考主流分级：白 -> 绿 -> 蓝 -> 紫 -> 金 -> 红 -> 璀璨
# 颜色用于 UI，mul 是该档位的伤害/属性总倍率，满级额外效果各有不同。
QUALITIES = {
    'white':   {'name': '普通', 'color': (222, 222, 230), 'mul': 1.00, 'star': 1,
                'max_lv': 3,  'up': (260, 480, 760),
                'mats': {'scrap': (2, 4, 6)},
                'perk': '满级：射速 +8%'},
    'green':   {'name': '精良', 'color': (110, 220, 120), 'mul': 1.00, 'star': 2,
                'max_lv': 4,  'up': (500, 900, 1400, 2000),
                'mats': {'scrap': (3, 5, 8, 12), 'fiber': (1, 2, 4, 6)},
                'perk': '满级：暴击率 +6%'},
    'blue':    {'name': '稀有', 'color': (110, 170, 250), 'mul': 1.00, 'star': 3,
                'max_lv': 5,  'up': (900, 1500, 2200, 3100, 4200),
                'mats': {'scrap': (4, 7, 10, 14, 18), 'circuit': (1, 2, 3, 5, 7)},
                'perk': '满级：弹速 +15%'},
    'purple':  {'name': '史诗', 'color': (186, 120, 250), 'mul': 1.00, 'star': 4,
                'max_lv': 6,  'up': (1600, 2500, 3600, 4900, 6500, 8400),
                'mats': {'circuit': (3, 5, 8, 11, 15, 20),
                         'crystal': (2, 3, 5, 8, 11, 15)},
                'perk': '满级：附带 1 次穿透'},
    'gold':    {'name': '传说', 'color': (255, 206, 74), 'mul': 1.00, 'star': 5,
                'max_lv': 7,  'up': (2800, 4200, 5800, 7800, 10200, 13000, 16200),
                'mats': {'crystal': (4, 6, 9, 13, 18, 24, 32),
                         'alloy': (1, 2, 3, 5, 7, 10, 14)},
                'perk': '满级：伤害 +15%，弹匣感更强'},
    'red':     {'name': '赤红', 'color': (240, 80, 84), 'mul': 1.00, 'star': 6,
                'max_lv': 8,  'up': (4500, 6500, 8800, 11500, 14600,
                                     18200, 22400, 27500),
                'mats': {'alloy': (3, 5, 8, 12, 17, 23, 30, 40),
                         'core': (1, 2, 3, 5, 7, 10, 14, 19)},
                'perk': '满级：击杀回能 +30%'},
    'radiant': {'name': '璀璨', 'color': (120, 255, 226), 'mul': 1.00, 'star': 7,
                'max_lv': 9,  'up': (7000, 10000, 13500, 17500, 22000,
                                     27500, 34000, 41500, 50000),
                'mats': {'core': (2, 4, 6, 9, 13, 18, 24, 31, 40),
                         'prism': (1, 2, 3, 5, 7, 10, 13, 17, 22)},
                'perk': '满级：全属性提升，附带追猎弹幕'},
}

QUALITY_ORDER = ['white', 'green', 'blue', 'purple', 'gold', 'red', 'radiant']

# 需求 6（1.4）：品质升级 = **机制变化**，不只是数字。
# 这张表是"每提升一级新增了哪些机制"的人类可读说明，与
# weapon.QUALITY_MECH 一一对应（那边是给代码用的数值）。
# UI（客厅强化预览 / 图鉴）直接展示这里的文案。
QUALITY_MECH_DESC = {
    'white':   '基准：无附加机制',
    'green':   '射速 +5%，弹速 +8%',
    'blue':    '弹丸 +1（散射/连发），射速 +10%，弹速 +15%',
    'purple':  '穿透 +1，射速 +15%，弹速 +22%，近战 30% 额外挥砍一次',
    'gold':    '击杀迸射：击杀时向四周溅射弹片',
    'red':     '命中分裂：命中后在敌人间弹跳',
    'radiant': '追猎弹道：子弹自动转向敌人 + 全属性大幅提升',
}


def quality_of(q):
    return QUALITIES.get(q, QUALITIES['white'])


def quality_rank(q):
    try:
        return QUALITY_ORDER.index(q)
    except ValueError:
        return 0


def max_level(q):
    return quality_of(q)['max_lv']


def upgrade_cost(q, lv):
    """把品质 q 的武器从 lv 升到 lv+1 需要 (金币, {材料: 数量})。
    lv 是当前等级（0 表示还没强化过）。"""
    spec = quality_of(q)
    ups = spec['up']
    if lv >= len(ups):
        return None
    coins = ups[lv]
    mats = {}
    for k, arr in spec['mats'].items():
        if lv < len(arr):
            mats[k] = arr[lv]
    return coins, mats


def is_max(q, lv):
    return lv >= max_level(q)


# -------------------------------------------------- 武器成长后的品质
# 需求 6：角色初始武器都是白色品质，随强化等级提升品质，**最高到蓝色**。
# 这里只描述"玩家自己培养的那把武器"的成长曲线；关卡里捡到的武器
# 仍然可以是更高品质（金/红/璀璨），那是掉落物本身的稀有度，两者不冲突。
_GROWTH_ORDER = ['white', 'green', 'blue']
# 达到各品质所需的强化等级
_GROWTH_AT = {'white': 0, 'green': 2, 'blue': 5}


def quality_for_weapon(wkey, lv):
    """A weapon's rarity is fixed; upgrades only increase its level."""
    from . import weapon as W
    return W.quality_of(wkey)


def next_growth_at(lv):
    """还差多少级升到下一档品质；已封顶返回 None。"""
    lv = max(0, int(lv or 0))
    for k in _GROWTH_ORDER:
        if lv < _GROWTH_AT[k]:
            return _GROWTH_AT[k]
    return None


def upgrade_cost_simple(lv):
    """角色初始武器（白->蓝）的强化开销：金币 + 废铁系材料。

    比通用 upgrade_cost 更线性，因为这条线是"新手养成主轴"，
    不应该让玩家卡在材料上。
    """
    lv = max(0, int(lv or 0))
    coins = 260 + lv * 220
    mats = {'scrap': 2 + lv, 'fiber': (lv // 2) + 1}
    if lv >= 4:
        mats['circuit'] = lv - 3
    return coins, mats


# ================================================================ 角色
# unlock: ('coin', 数量) / ('diamond', 数量) / ('craft', {材料: 数量})
# starter: 初始武器 key（白品质起步）
def _c(key, name, desc, unlock, starter, hp, spd, energy, perk):
    return {'key': key, 'name': name, 'desc': desc, 'unlock': unlock,
            'starter': starter, 'hp': hp, 'spd': spd, 'energy': energy,
            'perk': perk}


CHARACTERS = {
    'scout': _c('scout', '测绘员', '初始角色。漂泊在地表的记录者，靠一把旧手枪活到今天。',
                None, 'pistol', 12, 168.0, 200.0, '无特殊能力'),
    'engineer': _c('engineer', '工程师', '背着自制工具的修理工，擅长把废料变成武器。',
                   ('coin', 600, {'scrap': 6}), 'smg', 12, 164.0, 220.0, '能量上限 +10%'),
    'ranger': _c('ranger', '游猎者', '在污染区独自狩猎的枪手，枪法快而准。',
                 ('coin', 1200, {'circuit': 5}), 'shotgun', 11, 178.0, 200.0, '移动速度 +6%'),
    'medic': _c('medic', '战地医师', '在废墟间救人的医师，比谁都清楚怎么活下去。',
                ('coin', 1800, {'crystal': 5}), 'laser', 15, 162.0, 200.0, '生命上限 +3'),
    'ghost': _c('ghost', '潜行者', '没人见过真面目。传说他能穿过污染而不被侵蚀。',
                ('diamond', 45, {'crystal': 3}), 'rocket', 11, 186.0, 240.0, '冲刺冷却 -25%'),
    'prime': _c('prime', '协议行者', '用遗物碎片拼合出的存在。据说是旧世界的最后协议。',
                ('craft', {'relic': 2, 'core': 4, 'prism': 2}, 1000),
                'cannon', 14, 172.0, 260.0, '全属性均衡，初始武器更强'),
    'archivist': _c('archivist', '档案员', '追索散落在禁区的旧物，以记录拼回失落的世界。',
                    ('collect', 3), 'quartz_rifle', 10, 176.0, 260.0,
                    '高能量上限，擅长远程调查'),
    'seedkeeper': _c('seedkeeper', '守种人', '携带最后的种子，在废墟中保护微弱的生机。',
                     ('collect', 7), 'tidal_spear', 17, 156.0, 230.0,
                     '高生命上限，擅长近距离守护'),
}
CHAR_ORDER = ['scout', 'engineer', 'ranger', 'medic', 'ghost', 'prime',
              'archivist', 'seedkeeper']


def collect_progress(prof, key):
    """Valid distinct collectibles held and the hero's requirement."""
    u = char(key)['unlock']
    need = int(u[1]) if u and u[0] == 'collect' else 0
    from . import codex as CX
    have = len(set((prof or {}).get('collects') or ()) & set(CX.COLLECT_ORDER))
    return have, need


def sync_collect_characters(prof):
    """Unlock eligible collection heroes in current and migrated profiles."""
    unlocked = []
    chars = prof.setdefault('chars', ['scout'])
    for key in CHAR_ORDER:
        u = char(key)['unlock']
        if u and u[0] == 'collect' and key not in chars:
            have, need = collect_progress(prof, key)
            if have >= need:
                chars.append(key)
                unlocked.append(key)
    return unlocked


def char(key):
    return CHARACTERS.get(key, CHARACTERS['scout'])


def unlock_text(key, prof=None):
    """角色的解锁条件，给人看的字符串。"""
    u = char(key)['unlock']
    if u is None:
        return '初始角色'
    kind, val = u[0], u[1]
    if kind == 'collect':
        have, need = collect_progress(prof, key)
        return '收集品 %d/%d（点击查看）' % (have, need)
    if kind == 'coin':
        return '金币 %d + %s' % (val, '、'.join(
            '%s×%d' % (mat_name(k), n) for k, n in u[2].items()))
    if kind == 'diamond':
        return '钻石 %d + %s' % (val, '、'.join(
            '%s×%d' % (mat_name(k), n) for k, n in u[2].items()))
    if kind == 'craft':
        return '合成：金币 %d + %s' % (u[2], '、'.join(
            '%s×%d' % (mat_name(k), v) for k, v in val.items()))
    return '未知'


def can_unlock(prof, key):
    """返回 (是否可解锁, 缺少说明)。"""
    u = char(key)['unlock']
    if u is None:
        return True, ''
    kind, val = u[0], u[1]
    if kind == 'collect':
        have, need = collect_progress(prof, key)
        return (have >= need, '收集品进度 %d/%d' % (have, need))
    if kind == 'coin':
        if prof.get('coins', 0) < val:
            return False, '金币不足（需 %d）' % val
    if kind == 'diamond':
        if prof.get('diamonds', 0) < val:
            return False, '钻石不足（需 %d）' % val
    if kind == 'craft' and prof.get('coins', 0) < u[2]:
        return False, '金币不足（需 %d）' % u[2]
    if kind not in ('coin', 'diamond', 'craft'):
        return False, '未知条件'
    need = val if kind == 'craft' else u[2]
    mats = prof.get('materials', {})
    lack = ['%s×%d' % (mat_name(k), v - mats.get(k, 0))
            for k, v in need.items() if mats.get(k, 0) < v]
    return (False, '材料不足（缺 %s）' % '、'.join(lack)) if lack else (True, '')


def do_unlock(prof, key):
    """扣费并解锁。调用前应先用 can_unlock 检查。"""
    u = char(key)['unlock']
    if u is None:
        return True
    kind, val = u[0], u[1]
    if kind == 'collect':
        return key in sync_collect_characters(prof) or key in prof.get('chars', ())
    if kind == 'coin':
        prof['coins'] = prof.get('coins', 0) - val
    elif kind == 'diamond':
        prof['diamonds'] = prof.get('diamonds', 0) - val
    elif kind == 'craft':
        prof['coins'] = prof.get('coins', 0) - u[2]
    mats = prof.setdefault('materials', {})
    for k, v in (val if kind == 'craft' else u[2]).items():
        mats[k] = mats.get(k, 0) - v
        if mats[k] <= 0:
            mats.pop(k, None)
    chars = prof.setdefault('chars', ['scout'])
    if key not in chars:
        chars.append(key)
    return True


# ================================================================ 技能 / 被动
SKILLS = {
    'power':   ('火力强化', '所有武器伤害 +4%/级', 6),
    'haste':   ('迅捷', '移动速度 +3%/级', 6),
    'vital':   ('强健', '生命上限 +1/级', 5),
    'focus':   ('专注', '能量上限 +8/级', 5),
    'guard':   ('护盾', '受伤后无敌时间 +8%/级', 4),
    'fortune': ('幸运', '掉落金币 +10%/级', 5),
}
PASSIVES = {
    'thorns':  ('荆棘', '接触敌人时反弹伤害', 4),
    'regen':   ('自愈', '脱离战斗后缓慢回血', 5),
    'magnet':  ('磁力', '拾取范围扩大', 4),
    'pierce':  ('穿透', '子弹额外穿透 +1/级', 3),
    'crit':    ('致命', '暴击率 +4%/级', 5),
}


def skill_cost(key, lv):
    """技能/被动从 lv 升到 lv+1 的 (金币, 材料)。"""
    base = 240 + lv * 220
    if lv < 2:
        return base, {'scrap': 2 + lv, 'fiber': 1 + lv}
    return base, {'circuit': 1 + (lv - 2) // 2, 'crystal': 1 + (lv - 2) // 3}


def passive_cost(key, lv):
    base = 360 + lv * 280
    if lv < 2:
        return base, {'circuit': 1 + lv, 'crystal': 1 + lv}
    return base, {'alloy': 1 + (lv - 2) // 2, 'core': 1 + (lv - 2) // 3}


# ================================================================ 宝箱分级
# kind: coin 货币 / heal 医疗 / material 材料 / weapon 武器 / collect 收集
# tier: normal 一般 / superb 极品
CHESTS = {
    'coin': {
        'normal': {'name': '货币箱', 'color': (255, 206, 74),
                   'coin': (14, 28), 'dia': 0, 'w': 30},
        'superb': {'name': '贵重货币箱', 'color': (255, 232, 140),
                   'coin': (38, 68), 'dia': 1, 'w': 10},
    },
    'heal': {
        'normal': {'name': '医疗箱', 'color': (226, 62, 74),
                   'heal': (3, 5), 'w': 26},
        'superb': {'name': '急救箱', 'color': (255, 130, 140),
                   'heal': (7, 12), 'energy': 60, 'w': 8},
    },
    'material': {
        'normal': {'name': '材料箱', 'color': (120, 220, 180),
                   'mat_tier': (1, 2), 'mat_n': (2, 4), 'w': 22},
        'superb': {'name': '稀有材料箱', 'color': (170, 255, 210),
                   'mat_tier': (2, 3), 'mat_n': (3, 6), 'w': 6},
    },
    'weapon': {
        'normal': {'name': '武器箱', 'color': (140, 180, 250),
                   'q_max': 2, 'w': 18},
        'superb': {'name': '极品武器箱', 'color': (200, 160, 255),
                   'q_max': 3, 'w': 4},
    },
    'collect': {
        'normal': {'name': '工艺品箱', 'color': (210, 180, 140),
                   'collect': 'common', 'w': 0.8},
        'superb': {'name': '珍藏工艺品箱', 'color': (255, 230, 190),
                   'collect': 'superb', 'w': 0.10},
    },
}
CHEST_ORDER = ['coin', 'heal', 'material', 'weapon', 'collect']


def roll_chest(rng, floor_bias=0.0, luck=1.0):
    """按权重抽一个宝箱，返回 (kind, tier)。
    floor_bias 越大越偏极品（深层更容易出好东西）。
    """
    pool = []
    for k in CHEST_ORDER:
        for t in ('normal', 'superb'):
            spec = CHESTS[k][t]
            w = spec.get('w', 1) * luck
            if t == 'superb':
                w *= (0.55 + floor_bias * 0.4)
            pool.append((k, t, w))
    total = sum(p[2] for p in pool)
    r = rng.random() * total
    acc = 0.0
    for k, t, w in pool:
        acc += w
        if r <= acc:
            return k, t
    return 'coin', 'normal'


def chest_loot(rng, kind, tier, floor):
    """开箱结算，返回一个 dict：
    {'coins':int,'diamonds':int,'heal':int,'energy':int,'mats':{k:n},'quality':str}
    """
    spec = CHESTS[kind][tier]
    out = {'coins': 0, 'diamonds': 0, 'heal': 0, 'energy': 0,
           'mats': {}, 'quality': None}
    if kind == 'coin':
        out['coins'] = rng.randint(*spec['coin'])
        out['diamonds'] = spec.get('dia', 0) * rng.randint(1, 2)
    elif kind == 'heal':
        out['heal'] = rng.randint(*spec['heal'])
        out['energy'] = spec.get('energy', 0)
    elif kind == 'material':
        lo, hi = spec['mat_tier']
        pool = [k for k in MAT_ORDER if lo <= mat_tier(k) <= hi]
        if pool:
            for _ in range(rng.randint(*spec['mat_n'])):
                key = rng.choice(pool)
                out['mats'][key] = out['mats'].get(key, 0) + 1
    elif kind == 'weapon':
        out['quality'] = QUALITY_ORDER[min(spec['q_max'],
                                           len(QUALITY_ORDER) - 1)]
    return out
