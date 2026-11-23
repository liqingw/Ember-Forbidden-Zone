# -*- coding: utf-8 -*-
"""图鉴、收集品、天赋、提示词条（需求 8 / 9 / 15 / 1.1-2）。"""

# ================================================================ 图鉴
# 每个条目的首次出现会弹"新发现"提示（需求 15）。
CODEX_CATS = {
    'enemy': '怪物',
    'weapon': '武器',
    'material': '材料',
    'collect': '收集品',
}

# 怪物图鉴：key -> (名称, 所属场景, 类别, 简介)
#
# 规模约定（需求 8）：7 个主题场景 × 5 种 = 35，再加 2 种隐藏奖励怪 = 37。
# 每个场景的 5 种 = 3 小怪 + 1 精英 + 1 Boss（第 3 关小 Boss / 第 5 关大 Boss
# 共用同一 key，由 enemy.Boss.setup_scene 按关卡强化）。
# 类别取值：small / elite / boss / bigboss / rare
ENEMY_CODEX = {
    'scatter_raider': ('散弹掠夺者', '地表残骸 / 矿井', 'small', '手持霰铳，射出宽角慢速弹幕。'),
    'beam_raider': ('缓束哨兵', '机械坟场 / 原点', 'small', '单条极慢激光，封锁走位。'),
    'rifle_raider': ('精确射手', '下水道 / 冷库', 'small', '高速单发，提前看清准星。'),
    # ---------------- 地表残骸 crust（3 小怪 + 1 精英 + 1 Boss）
    'slime':      ('污染黏液', '地表残骸', 'small', '最基础的污染体，会朝你缓慢蠕动。'),
    'slug':       ('腐壳虫', '地表残骸', 'small', '外壳很硬，先对准再贴地冲锋，撞墙会僵住。'),
    'crawler':    ('碎骨爬行体', '地表残骸', 'small', '趴在地上快速爬行，偶尔弹跳扑咬。'),
    'slime_big':  ('黏液母体', '地表残骸', 'elite', '更大更硬，分裂时注意包夹。'),
    'warlord':    ('残骸军阀', '地表残骸', 'boss', '挥舞废铁的重装体，冲撞后有僵直可言。'),

    # ---------------- 腐化下水道 sewer
    'drone':      ('游荡机', '腐化下水道', 'small', '失控的巡检机，会绕着你要害打。'),
    'leech':      ('吸血水蛭', '腐化下水道', 'small', '贴住你会持续抽血，别让它缠上身。'),
    'drone_big':  ('重装巡弋', '腐化下水道', 'elite', '护盾会周期性重启，抓住空档。'),
    'swarmqueen': ('虫群女王', '腐化下水道', 'boss', '产卵型首领，别让场面积累。'),

    # ---------------- 机械坟场 facility
    'bomber':     ('自爆囊', '机械坟场', 'small', '靠近就膨胀，别让它贴脸。'),
    'turret':     ('废弃炮台', '机械坟场', 'small', '固定不动，但火力覆盖整条通道。'),
    'bomber_big': ('爆破工头', '机械坟场', 'elite', '一次性放出整圈炸弹，先清场再打。'),
    'mech':       ('坟场机枢', '机械坟场', 'boss', '三段变形，每段换一种弹幕。'),

    # ---------------- 污染原点 core
    'spore':      ('孢殖体', '污染原点', 'small', '死亡会留下毒雾，别站在它死的地方。'),
    'wraith':     ('污染幽影', '污染原点', 'small', '半透明，会瞬移到你背后，注意转身。'),
    'wraith_big': ('幽影督军', '污染原点', 'elite', '瞬移更频繁，弹道预判比它本体更准。'),
    'protocol':   ('协议残片', '污染原点', 'boss', '旧世界防御程序，攻击非常有规律。'),
    'origin':     ('污染原点·本体', '污染原点', 'bigboss', '一切开始的地方。终局。'),

    # ---------------- 废弃矿井 d_mine（副本）
    'rockworm':   ('岩噬虫', '废弃矿井', 'small', '在岩壁间钻行，从背后冒出来突袭。'),
    'minebot':    ('雷区机兵', '废弃矿井', 'small', '边走边布雷，走位要留意脚下。'),
    'slime_big_m':('矿脉黏液体', '废弃矿井', 'elite', '吃了矿物变得格外坚硬，钝击无效。'),
    'foreman':    ('矿井监工', '废弃矿井', 'boss', '在狭窄处很危险，拉开距离打。'),

    # ---------------- 实验冷库 d_lab（副本）
    'frostbite':  ('霜蚀体', '实验冷库', 'small', '命中会附带减速，别被叠满。'),
    'spore_big':  ('孢殖母巢', '实验冷库', 'elite', '持续召唤小孢殖体，速杀。'),
    'specimen':   ('冷库标本', '实验冷库', 'boss', '冻住的东西动了。别被逼到角落。'),

    # ---------------- 净土庭园 d_gift（奖励副本）
    'purifier':   ('净土傀儡', '净土庭园', 'small', '看守圣地的空壳，动作缓慢但很痛。'),
    'sprite':     ('微光灵', '净土庭园', 'small', '会闪避子弹的灵体，打它得预判。'),
    'guardian':   ('净土守卫', '净土庭园', 'boss', '把守着最后一片净土的门。'),

    # ---------------- 隐藏奖励怪（全场景极小概率，需求 8）
    'mimic':      ('拟态宝箱', '任意', 'rare', '伪装成宝箱。靠近才现形，打它掉好东西。'),
    'wanderer':   ('拾荒旅人', '任意', 'rare', '不主动攻击。它身上有红色与璀璨的图纸。'),
    'lucky_treasure': ('幸运宝藏怪', '任意', 'rare', '携带钻石、稀有材料与珍品武器的金色怪物。'),

    # ---------------- 第二梯队精英（后期场景刷新，需求 8：难度逐级递增）
    'crawler_big':  ('碎骨领主', '地表残骸', 'elite', '冲锋落点会留下骨刺，别站在圈里。'),
    'leech_big':    ('血蛭母体', '腐化下水道', 'elite', '一次吸附多个目标，必须先打断。'),
    'turret_big':   ('重炮平台', '机械坟场', 'elite', '三连发覆盖全场，靠掩体推进。'),
    'rockworm_big': ('岩噬母虫', '废弃矿井', 'elite', '钻地后整片地面都在震，抬头看。'),
    'frostbite_big':('霜蚀主宰', '实验冷库', 'elite', '光环持续减速，近身等于自杀。'),
    'guardian_big': ('净土裁决者', '净土庭园', 'elite', '会封锁你的退路，速战速决。'),
    'spore_big_m':  ('孢殖祖巢', '污染原点', 'elite', '毒雾覆盖半场，只能边跑边打。'),
    'crust_sentinel': ('熔渣哨兵', '地表残骸', 'boss', '第三关的废钢守门者，挥出扇形碎铁。'),
    'sewer_serpent': ('污水管蛇', '腐化下水道', 'boss', '盘绕水渠的污染巨蛇，擅长突进。'),
    'facility_smelter': ('熔炉看守', '机械坟场', 'boss', '旧熔炉的活动炉心，会释放热浪。'),
    'mine_excavator': ('地脉掘进机', '废弃矿井', 'boss', '钻地机械失控后成为矿道守卫。'),
    'lab_cryowarden': ('零号冻卫', '实验冷库', 'boss', '冷库第一批实验体，周围持续结霜。'),
    'gift_bloom': ('晶花园丁', '净土庭园', 'boss', '晶体与藤蔓构成的净土守护者。'),
}
ENEMY_ORDER = list(ENEMY_CODEX.keys())

# 场景 -> 怪物分配（4 主线 + 2 副本 + 1 奖励副本，共 7 个场景）
# 与 dungeon.SCENE_SPAWN / SCENE_BOSS 保持同源。
SCENE_ENEMIES = {
    'crust':    {'small': ['slime', 'slug', 'crawler', 'scatter_raider'],
                 'elite': ['slime_big'],           'boss': 'warlord'},
    'sewer':    {'small': ['slug', 'drone', 'leech', 'rifle_raider'],
                 'elite': ['drone_big'],           'boss': 'swarmqueen'},
    'facility': {'small': ['drone', 'bomber', 'turret', 'beam_raider'],
                 'elite': ['bomber_big'],          'boss': 'mech'},
    'core':     {'small': ['spore', 'wraith', 'frostbite', 'beam_raider'],
                 'elite': ['wraith_big'],          'boss': 'origin'},
    'd_mine':   {'small': ['rockworm', 'minebot', 'slug', 'scatter_raider'],
                 'elite': ['slime_big_m'],         'boss': 'foreman'},
    'd_lab':    {'small': ['frostbite', 'spore', 'wraith', 'rifle_raider'],
                 'elite': ['spore_big'],           'boss': 'specimen'},
    'd_gift':   {'small': ['purifier', 'sprite'], 'elite': [],
                 'boss': 'guardian'},
}
SCENE_MINIBOSS_CODEX = {
    'crust': 'crust_sentinel', 'sewer': 'sewer_serpent',
    'facility': 'facility_smelter', 'core': 'protocol',
    'd_mine': 'mine_excavator', 'd_lab': 'lab_cryowarden',
    'd_gift': 'gift_bloom',
}


def scene_enemy_names(scene_key):
    """某场景的怪名列表（给过场/提示展示用，需求 15）。"""
    spec = SCENE_ENEMIES.get(scene_key)
    if not spec:
        return []
    out = []
    for grp in ('small', 'elite'):
        for k in spec.get(grp, ()):
            v = ENEMY_CODEX.get(k)
            if v:
                out.append((k, v[0], v[3]))
    b = spec.get('boss')
    if b and b in ENEMY_CODEX:
        v = ENEMY_CODEX[b]
        out.append((b, v[0], v[3]))
    return out

# ================================================================ 收集品
# 工艺品：放在个人展示台（需求 9）。品级 common / superb
COLLECTS = {
    'gear_cog':     ('锈蚀齿轮', 'common', '旧机械里拆出来的，还带着一点温度。'),
    'glass_shard':  ('污染玻片', 'common', '凝固的污染在玻璃里长成了花纹。'),
    'doll_rabbit':  ('缝补布偶', 'common', '针脚歪歪扭扭，是谁留下的？'),
    'ledger':       ('半本账簿', 'common', '字迹被水泡烂了，只剩几个数字。'),
    'coin_pressed': ('压平的硬币', 'common', '被碾压成薄片，上面的头像看不清了。'),
    'ring_copper':  ('铜环', 'superb', '内圈刻着一行小字：「等我回来」。'),
    'seed_pod':     ('未萌发的种荚', 'superb', '据说只要土还能用，它就能活。'),
    'music_box':    ('八音盒', 'superb', '上紧发条，它还能唱完前半段旋律。'),
    'photo':        ('褪色照片', 'superb', '四个人站在阳光里。没有人穿防护服。'),
    'core_fragment':('协议残页', 'superb', '写协议的人，也许就在这张纸上。'),
}
COLLECT_ORDER = list(COLLECTS.keys())


def collect_pool(tier):
    return [k for k, v in COLLECTS.items() if v[1] == tier]


def roll_collect(rng, tier='common'):
    pool = collect_pool(tier) or collect_pool('common')
    return rng.choice(pool)


# ================================================================ 天赋
# 打完 Boss 进传送门后三选一（需求 1.1-2）
# kind: stat 直接改数值；flag 给特殊效果
TALENTS = {
    'dmg_up':    {'name': '锐化弹头', 'desc': '伤害 +15%', 'kind': 'stat',
                  'stat': 'dmg_mul', 'val': 0.15, 'color': (255, 140, 120)},
    'rate_up':   {'name': '快速击发', 'desc': '射速 +12%', 'kind': 'stat',
                  'stat': 'rate_mul', 'val': 0.12, 'color': (255, 210, 120)},
    'hp_up':     {'name': '强化体魄', 'desc': '生命上限 +2 并回满', 'kind': 'stat',
                  'stat': 'max_hp', 'val': 2, 'color': (226, 90, 100)},
    'spd_up':    {'name': '轻装', 'desc': '移动速度 +10%', 'kind': 'stat',
                  'stat': 'spd_mul', 'val': 0.10, 'color': (120, 220, 240)},
    'energy_up': {'name': '能量扩容', 'desc': '能量上限 +25', 'kind': 'stat',
                  'stat': 'max_energy', 'val': 25, 'color': (100, 180, 255)},
    'regen_up':  {'name': '再生协议', 'desc': '每秒回血 +0.4', 'kind': 'stat',
                  'stat': 'hp_regen', 'val': 0.4, 'color': (140, 240, 160)},
    'crit_up':   {'name': '精密瞄具', 'desc': '暴击率 +12%', 'kind': 'stat',
                  'stat': 'crit', 'val': 0.12, 'color': (255, 180, 90)},
    'dash_up':   {'name': '疾风步', 'desc': '冲刺冷却 -30%', 'kind': 'stat',
                  'stat': 'dash_cd_mul', 'val': -0.30, 'color': (180, 200, 255)},
    'magnet_up': {'name': '引力场', 'desc': '拾取范围 +50%', 'kind': 'stat',
                  'stat': 'magnet_mul', 'val': 0.50, 'color': (200, 220, 140)},
    'luck_up':   {'name': '幸运星', 'desc': '掉落与宝箱品质提升', 'kind': 'stat',
                  'stat': 'luck', 'val': 0.35, 'color': (255, 230, 140)},
    'pierce_add':{'name': '贯穿', 'desc': '子弹额外穿透 +1', 'kind': 'stat',
                  'stat': 'pierce', 'val': 1, 'color': (200, 140, 255)},
    'thorns':    {'name': '反伤甲', 'desc': '受击时反弹 40% 伤害', 'kind': 'flag',
                  'flag': 'thorns', 'color': (180, 180, 200)},
    'lifesteal': {'name': '汲取', 'desc': '击杀时有 12% 概率回血', 'kind': 'flag',
                  'flag': 'lifesteal', 'color': (226, 100, 130)},
    'aoe_bullet':{'name': '崩解弹', 'desc': '子弹命中时产生小范围爆炸', 'kind': 'flag',
                  'flag': 'aoe_bullet', 'color': (255, 160, 80)},
    'shield':    {'name': '应急护盾', 'desc': '每层开始获得 1 次免伤', 'kind': 'flag',
                  'flag': 'shield', 'color': (120, 200, 255)},
    # ---- 抗污染天赋（1.3 需求：让"推进"本身有对抗手段，而不是纯挨打）
    # 这三条是**乘算**叠加进 pur_resist（0~0.85 上限），逐帧作用于污染减益。
    # 设计意图：越接近源头（污染原点 96%），抗污染系越关键；
    # 在浅层（地表 3%）它们几乎无用，形成"环境越深、构筑越针对性"的取舍。
    'pur_resist':{'name': '滤芯装甲', 'desc': '污染侵蚀与减益整体 -25%',
                  'kind': 'stat', 'stat': 'pur_resist', 'val': 0.25,
                  'color': (140, 230, 190)},
    'pur_purge': {'name': '净化循环', 'desc': '每 6 秒自动清除一次侵蚀累积',
                  'kind': 'flag', 'flag': 'pur_purge', 'color': (120, 250, 210)},
    'pur_ward':  {'name': '污染共鸣', 'desc': '污染浓度每 10%，伤害 +3%',
                  'kind': 'flag', 'flag': 'pur_ward', 'color': (200, 160, 250)},
    'trap_ward': {'name': '无害通行', 'desc': '免疫所有陷阱伤害与减速',
                  'kind': 'flag', 'flag': 'trap_ward', 'color': (117, 244, 198)},
    'phase_step': {'name': '相位步', 'desc': '冲刺时穿过墙体与掩体',
                   'kind': 'flag', 'flag': 'phase_step', 'color': (195, 153, 250)},
    'auto_collect': {'name': '自动拾荒', 'desc': '自动收集房间内的金币与补给',
                     'kind': 'flag', 'flag': 'auto_collect', 'color': (247, 220, 114)},
}
TALENT_ORDER = list(TALENTS.keys())


def roll_talents(rng, owned, n=3):
    """从天赋池抽 n 个不重复的（已拥有的可重复出现以叠加）。"""
    cnt = {}
    for k in owned:
        cnt[k] = cnt.get(k, 0) + 1
    pool = [k for k in TALENT_ORDER if cnt.get(k, 0) < 3]
    if len(pool) < n:
        pool = list(TALENT_ORDER)
    return rng.sample(pool, min(n, len(pool)))


def apply_talent(stats, key):
    """把天赋效果累加进一局的 stats 字典。"""
    t = TALENTS.get(key)
    if not t:
        return False
    if t['kind'] == 'stat':
        s = t['stat']
        if s in ('dmg_mul', 'rate_mul', 'spd_mul', 'magnet_mul', 'crit',
                 'hp_regen', 'luck', 'pur_resist'):
            stats[s] = stats.get(s, 0.0) + t['val']
        elif s == 'dash_cd_mul':
            stats[s] = stats.get(s, 0.0) + t['val']
        elif s in ('max_hp', 'max_energy', 'pierce'):
            stats[s] = stats.get(s, 0) + t['val']
    else:
        stats.setdefault('flags', set())
        stats['flags'].add(t['flag'])
    return True


def new_run_stats():
    """一局开始时的基础加成（角色的被动会写进来）。"""
    return {
        'dmg_mul': 0.0, 'rate_mul': 0.0, 'spd_mul': 0.0, 'magnet_mul': 0.0,
        'crit': 0.05, 'hp_regen': 0.0, 'luck': 0.0,
        'dash_cd_mul': 0.0,
        'max_hp': 0, 'max_energy': 0, 'pierce': 0,
        # 抗污染：0.0 = 完全不抗，0.85 = 减益只剩 15%（硬上限）
        'pur_resist': 0.0,
        'flags': set(),
        'talents': [],
    }


# ---------------------------------------------------------------- 抗污染计算
PUR_RESIST_CAP = 0.85      # 抗性上限：再堆也不会低于 15% 的减益
PUR_WARD_PER = 3.0         # 「污染共鸣」：浓度每 10%，伤害 +3%
PUR_PURGE_INTERVAL = 6.0   # 「净化循环」：每 6 秒清一次侵蚀累积


def pur_resist_of(stats):
    """从 run_stats 取抗污染系数，并夹到 [0, PUR_RESIST_CAP]。"""
    if not isinstance(stats, dict):
        return 0.0
    v = float(stats.get('pur_resist', 0.0) or 0.0)
    return max(0.0, min(PUR_RESIST_CAP, v))


def pur_tint_amount(pollution, stats):
    """返回 (hp_cut, spd, regen, drain) —— 已按抗污染减过的实际值。

    pollution 是 chapter.pollution() 的返回，stats 是本局加成。
    抗性是**线性减免**：resist=0.25 时，hp_cut 少 25%、drain 少 25%，
    而 spd/regen 是"朝 1.0 收敛 25%"。
    """
    if not pollution:
        return (0, 1.0, 1.0, 0.0)
    r = pur_resist_of(stats)
    hp_cut = int(round(pollution['hp_cut'] * (1.0 - r)))
    spd = 1.0 - (1.0 - float(pollution['spd'])) * (1.0 - r)
    regen = 1.0 - (1.0 - float(pollution['regen'])) * (1.0 - r)
    drain = float(pollution['drain']) * (1.0 - r)
    return (hp_cut, spd, regen, drain)


def pur_ward_bonus(pollution, stats):
    """「污染共鸣」：按当前污染浓度换算成额外伤害倍率。

    没有该天赋时返回 0。浓度 96% 时约 +29% 伤害，
    是对"越深越难"的正向补偿 —— 与抗污染系形成两套解法
    （硬抗 vs 借力）。
    """
    if not isinstance(stats, dict) or not pollution:
        return 0.0
    flags = stats.get('flags') or ()
    if 'pur_ward' not in flags:
        return 0.0
    pct = float(pollution.get('pct', 0) or 0)
    return (pct / 10.0) * (PUR_WARD_PER / 100.0)


def has_pur_purge(stats):
    return bool(isinstance(stats, dict)
                and 'pur_purge' in (stats.get('flags') or ()))


# ================================================================ 局内提示
# 需求 15：新怪物 / 新武器 / 新材料 / Boss 出现时弹简要介绍
def enemy_intro(key):
    v = ENEMY_CODEX.get(key)
    if not v:
        return None
    return f'{v[0]}', v[3]


def material_intro(key):
    from . import gamedata as G
    v = G.MATERIALS.get(key)
    if not v:
        return None
    return v[0], v[2]


def collect_intro(key):
    v = COLLECTS.get(key)
    if not v:
        return None
    return f'{v[0]}（{"珍品" if v[1] == "superb" else "工艺品"}）', v[2]


# ================================================================ 派生图鉴表
# 需求 8：图鉴要覆盖怪物 / 武器 / 材料 / 收集品四类。武器与材料的原始
# 数据在 weapon.py / gamedata.py，这里做一层"图鉴视图"（名称 + 一句简介），
# 避免在两个地方重复维护文案。
def _build_weapon_codex():
    out = {}
    try:
        from . import weapon as W
        for k in getattr(W, 'ORDER', []):
            spec = W.WEAPONS.get(k)
            if spec is None:
                continue
            name = getattr(spec, 'name', k)
            desc = getattr(spec, 'desc', '') or ''
            dmg_v = max(1, int(round(getattr(spec, 'dmg', 1))))
            cnt_v = int(getattr(spec, 'count', 1) or 1)
            dmg_s = f'{dmg_v}×{cnt_v}' if cnt_v > 1 else str(dmg_v)
            aps = 1.0 / max(0.01, float(getattr(spec, 'cd', 0.25) or 0.25))
            summary = f'伤 {dmg_s} · 攻速 {aps:.1f}/秒'
            out[k] = (name, f'{desc}（{summary}）' if desc else summary)
    except Exception:
        pass
    return out


def _build_material_codex():
    out = {}
    try:
        from . import gamedata as G
        for k in getattr(G, 'MAT_ORDER', []):
            v = G.MATERIALS.get(k)
            if v:
                out[k] = (v[0], v[2])
    except Exception:
        pass
    return out


WEAPON_CODEX = _build_weapon_codex()
MATERIAL_CODEX = _build_material_codex()


def enemy_stats(key):
    """图鉴中的基础战斗属性；实际生命值还会随关卡深度提高。"""
    from . import enemy as E
    if key not in ENEMY_CODEX:
        return {}
    category = ENEMY_CODEX[key][2]
    if category in ('boss', 'bigboss'):
        e = E.Boss(0, 0, 1)
        from . import chapter as C
        for scene, sk in SCENE_ENEMIES.items():
            if sk.get('boss') == key or SCENE_MINIBOSS_CODEX.get(scene) == key:
                e.setup_scene(scene, 2 if SCENE_MINIBOSS_CODEX.get(scene) == key else 4)
                break
    else:
        e = E.make(key, 0, 0, 1, category == 'elite')
    return {'hp': round(e.max_hp), 'speed': round(e.speed),
            'contact': round(e.contact_dmg, 1),
            'type': category}
