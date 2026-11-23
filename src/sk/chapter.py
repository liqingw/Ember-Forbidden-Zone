# -*- coding: utf-8 -*-
"""章节 / 关卡 / 剧情。

结构（对应需求 2）
------------------
  5 个主线场景 × 5 关 = 25 关
  2 个副本场景 × 5 关 = 10 关
  1 个奖励副本        = 收尾
  --------------------------  合计 35 关 + 1 收尾

每个场景 5 关的难度曲线固定为：
  第 1~2 关：小怪
  第 3 关   ：小怪 + 精英 + **小 Boss**
  第 4 关   ：小怪 + 精英（难点）
  第 5 关   ：小怪 + 精英 + **大 Boss**
副本解锁：2 个副本各自需要在前一场景达成某类条件。
奖励副本：最后一个主线场景结束时付费解锁。
"""
import random

# ================================================================ 剧情
# 核心叙事：污染入侵 -> 生存。用"日志残片"的形式在关卡开场/通关时播放。
#
# 需求 2：叙事要成体系，所以按"三幕"结构铺开：
#   第一幕（地表残骸 / 腐化下水道）—— 发现：污染不是天灾，是从地底涌上来的
#   第二幕（机械坟场 / 污染原点）  —— 对抗：有人在改造污染，也有人在改造人
#   第三幕（副本 / 馈赠之地）      —— 抉择：活下去，还是把干净的地方留下来
# 每幕的叙事都在入场、中场、通关三个节点给出，串起来是一条完整的故事线。
INTRO = [
    '第 7 号避难所，记录员编号 021。',
    '污染已经越过第三道防线。地表的土壤在变色，',
    '空气里飘着不会落下的灰。',
    '我们叫它「陆面过程」——',
    '一场从地底开始、正在改写整颗星球的入侵。',
    '协议还在运行。我是最后一批执行者之一。',
    '',
    '我不指望能彻底清掉它。',
    '我只想在被改写之前，',
    '替所有人记住——净土长什么样子。',
    '任务：向下。找到污染源。在它改写一切之前。',
]

# 每幕的标题（过场用）
ACT_TITLE = {
    'crust': '第一幕 · 发现',
    'sewer': '第一幕 · 发现',
    'facility': '第二幕 · 对抗',
    'core': '第二幕 · 对抗',
    'd_mine': '支线 · 回声',
    'd_lab': '支线 · 源头',
    'd_gift': '终幕 · 净土',
}

# 每关（5 关 · 0..4）的中场叙事节拍 —— 让"一场景 5 关"有连续的剧情推进，
# 而不是只在进场景时讲一次。需求 2：叙事要贯穿全程。
STAGE_BEATS = {
    'crust': [
        ['地表还没死透——瓦砾缝里有一株草。',
         '我把它记进日志：目标之外，仍有活物。'],
        ['灰越来越厚，能见度不到二十米。',
         '风里有金属味。这里不适合久留。'],
        ['前方读数异常——有人在这里建过哨点。',
         '哨点已经废弃，但门还锁着。'],
        ['哨点深处有动静。',
         '不是风。是"生长"。'],
        ['这一段挖到底了。',
         '顺着通风井往下，才是真正的入口。'],
    ],
    'sewer': [
        ['第二层，废弃管网。',
         '墙面上长着不该长在这的东西。'],
        ['水流在变慢——被什么堵住了。',
         '堵住它的东西，还在动。'],
        ['管道交汇处有巢。',
         '别惊动它，先清干净通道。'],
        ['巢的母体就在后面。',
         '它产卵的速度，比我清理的速度快。'],
        ['管网贯通。',
         '我在这里第一次看见它们「生长」的样子——',
         '它们不是在蔓延，是在进食。'],
    ],
    'facility': [
        ['第三层，旧工业区。',
         '机械残骸堆成山，有些还在动。'],
        ['有人在改造这里的设备。',
         '改造得很有目的性——不像逃难的人干的。'],
        ['检测到人工信号源。',
         '它在发一种我听不懂的编码，但节奏很稳。'],
        ['信号源的核心被加固过。',
         '他们知道我会来。'],
        ['这里有人在改造污染。',
         '不止我一个还活着——',
         '但他们显然不打算让我继续往下走。'],
    ],
    'core': [
        ['第四层。这里就是源头。',
         '地表的一切，都是从这一间开始的。'],
        ['浓度已经高到仪器读不出来了。',
         '肺在烧，视线在晃。快点。'],
        ['沿途全是"完成品"——',
         '被污染改写过、但仍然站着的旧执行者。'],
        ['协议本体在等我。',
         '它说：你也是可以被改写的。'],
        ['源头封住了。',
         '地表的浓度读数在下降——真的在下降。',
         '我完成了任务。虽然，可能只有我一个人知道。'],
    ],
    'd_mine': [
        ['副本：废弃矿井。',
         '支线信号源，偏离主路线。'],
        ['矿道比外面的年代更久。',
         '这里的污染是"老"的——不活跃，但更稠密。'],
        ['有人把机器埋在这里。',
         '埋得很深，像是在藏什么。'],
        ['监工还在。',
         '它已经不算活物了，但还在执行"看守"这个指令。'],
        ['矿井勘探完成。',
         '带出来的东西，足够让我再往下走很久。'],
    ],
    'd_lab': [
        ['副本：实验冷库。',
         '低温让污染结晶了——',
         '也让那些标本保持着死亡那一刻的姿势。'],
        ['标本编号从 001 排到 400 多。',
         '最早的几个，是自愿的。'],
        ['冷库深处有完整的实验记录。',
         '写记录的人，一开始是想救人。'],
        ['标本们醒了。',
         '别被逼到角落——那里没有第二个出口。'],
        ['冷库数据已提取。',
         '终于知道协议是谁写的了。'],
    ],
    'd_gift': [
        ['奖励副本：馈赠之地。',
         '协议最后的善意。'],
        ['这里没有敌人会主动追你',
         '——只要你手脚够快。'],
        ['箱子里装的是"还没被污染过"的东西。',
         '种子、水、一小段录音。'],
        ['把能带的都带走。',
         '这里的东西，比金币值钱。'],
        ['馈赠已收取。',
         '地表的天，第一次亮了。'],
    ],
}


# 每个场景的过场文本（进场 / 通关）
CHAPTER_STORY = {
    'crust': {
        'name': '地表残骸', 'sub': 'THE SCORCHED CRUST',
        'enter': ['第一层，地表。', '城市只剩下骨架，风把灰吹成墙。',
                  '记录：污染浓度 3%。还在可控范围。'],
        'clear': ['地表段清理完毕。', '但探测仪指向更深处——'
                  '污染不是从天上来的，是从地底涌上来的。'],
        'tint': (150, 132, 108),
    },
    'sewer': {
        'name': '腐化下水道', 'sub': 'THE ROTWAYS',
        'enter': ['第二层，废弃管网。', '墙面上长着不该长在这的东西。',
                  '记录：污染浓度 21%。样本开始有活性。'],
        'clear': ['管网贯通。', '我在这里第一次看见它们「生长」的样子。',
                  '它们不是在蔓延，是在进食。'],
        'tint': (96, 130, 96),
    },
    'facility': {
        'name': '机械坟场', 'sub': 'THE MACHINE GRAVEYARD',
        'enter': ['第三层，旧工业区。', '机械残骸堆成山，有些还在动。',
                  '记录：污染浓度 48%。检测到人工信号源。'],
        'clear': ['这里有人在改造污染。', '不止我一个还活着——'
                  '但他们显然不打算让我继续往下走。'],
        'tint': (110, 116, 138),
    },
    'core': {
        'name': '污染原点', 'sub': 'THE ORIGIN',
        'enter': ['第四层。这里就是源头。', '地表的一切，都是从这一间开始的。',
                  '记录：污染浓度 96%。协议提示：已无撤退路线。'],
        'clear': ['源头封住了。', '地表的浓度读数在下降——真的在下降。',
                  '我完成了任务。虽然，可能只有我一个人知道。'],
        'tint': (170, 80, 96),
    },
    # ---- 副本 ----
    'd_mine': {
        'name': '废弃矿井', 'sub': 'THE ABANDONED SHAFT',
        'enter': ['副本：废弃矿井。', '支线信号源，偏离主路线。',
                  '这里的东西比主线更古老。'],
        'clear': ['矿井勘探完成。', '带出来的东西，足够让我再往下走很久。'],
        'tint': (140, 120, 90),
    },
    'd_lab': {
        'name': '实验冷库', 'sub': 'THE COLD LAB',
        'enter': ['副本：实验冷库。', '低温让污染结晶了——',
                  '也让那些标本保持着死亡那一刻的姿势。'],
        'clear': ['冷库数据已提取。', '终于知道协议是谁写的了。'],
        'tint': (110, 150, 170),
    },
    'd_gift': {
        'name': '馈赠之地', 'sub': 'THE GIFT',
        'enter': ['奖励副本：馈赠之地。', '协议最后的善意。',
                  '这里没有敌人会主动追你——只要你手脚够快。'],
        'clear': ['馈赠已收取。', '地表的天，第一次亮了。'],
        'tint': (200, 180, 120),
    },
}

# ================================================================ 场景定义
# theme: 场景 id；order: 出现在选关界面的顺序
# enemy/small/elite/boss: 该场景的怪池（在 enemy.py 里注册）
# unlock: None 主线 / ('dungeon_done', 场景) 各副本条件
# stages: 固定 5
# 4 个主线场景（35 关 = 4 主线 + 2 副本 + 1 奖励副本，共 7 个主题场景）
MAIN = ['crust', 'sewer', 'facility', 'core']

# ---------------------------------------------------------------- 副本准入
# 设计原则（需求：条件必须与前置关卡的具体内容逻辑自洽，且要有点难度）
#   1. 条件只能引用**前置场景真实存在的东西**：
#      · 该场景独有的怪（SCENE_MOBS / codex.SCENE_ENEMIES）
#      · 该场景独有的陷阱（hazard.plan_scene 里的 TRAP_BY_SCENE）
#      · 该场景本身的机制（自爆囊在近距离才会引爆；幽影会瞬移等）
#   2. 条件必须"打得到但不容易顺手完成"，所以给两条以上互相牵制的指标：
#      · 一条"量"（击杀某种怪 / 累计伤害）
#      · 一条"质"（不踩某种陷阱 / 不被某类攻击命中 / 低血量通关）
#   3. 条件全部用可累计的历史最好成绩判定（`scene_best`），
#      所以玩家可以在同一场景里分多次刷，越打越接近——不会"一次性赌博"。
#
# 每类条件的可追踪字段（都在 profile['scene_best'][scene] 下）：
#   kills        该场景历史最高单局击杀
#   trap_hits    该场景历史最低被陷阱命中次数（越小越好）
#   bomber_hits  被"自爆囊/爆破工头"炸到的次数（越小越好）
#   no_death     是否曾在单局内零死亡（布尔，一次达成即永久保留）
#   cleared      是否通关过该场景
#   low_hp       是否曾在残血（≤3 点生命）状态下通关该场景
#
# ---------------------------------------------------------------- 场景叙事绑定
# （1.3 需求 2）光有数字条件还是"干巴巴的"——玩家看到"踩毒池 ≤4 次"
# 会想"毒池是什么？我为什么要躲它？"。
# 所以每条条件都绑定到**前置场景里真实存在的对象**，UI 可展开成一张
# "机制卡"：图标 + 名称 + 图鉴说明 + 在哪儿遇到。
#
# bind 的结构：
#   {'enemies': [(key, 说明)], 'traps': [(key, 说明)], 'tip': '一句话战术'}
# 其中 enemy key 对应 codex.ENEMY_CODEX，trap key 对应 hazard 的陷阱类型。
DUNGEONS = {
    'd_mine': {
        'after': 'sewer',
        'cond': {'cleared': True, 'kills': 90, 'trap_hits': 4},
        'cond_text': '在「腐化下水道」通关一次，'
                     '单局击杀 ≥ 90 个敌人，且踩中的毒池/泥沼 ≤ 4 次',
        'hint': '下水道的怪以「腐壳虫 + 游荡机」为主，'
                '毒池与泥沼是本层唯一的地面机关——踩多了扣血又减速。'
                '想开废弃矿井，得先证明你能在这层横着走。',
        # ---- 叙事绑定（1.3）
        'bind': {
            'enemies': [
                ('slug', '腐壳虫——下水道的基础单位，数量极多。'
                         '击杀门槛 90 主要靠它堆'),
                ('drone', '游荡机——会贴脸自爆前摇，边打边退才安全'),
            ],
            'traps': [
                ('poison', '毒池——站上去持续掉血，是"踩中陷阱"计数的主力'),
                ('slow', '泥沼——大幅减速，被围住时最致命'),
            ],
            'tip': '想少踩陷阱：贴着墙走，毒池和泥沼从不长在墙角。',
        },
    },
    'd_lab': {
        'after': 'facility',
        'cond': {'cleared': True, 'kills': 140, 'bomber_hits': 2,
                 'low_hp': True},
        'cond_text': '在「机械坟场」通关一次，单局击杀 ≥ 140 个敌人、'
                     '被自爆囊炸到 ≤ 2 次，且曾残血（≤3 点生命）通关',
        'hint': '机械坟场的威胁全在「自爆囊」和「爆破工头」——'
                '它们贴脸才会引爆，被炸两次以上说明你一直在被近身。'
                '冷库的门只认真正的老手：既要清得干净，也要活得够险。',
        # ---- 叙事绑定（1.3）
        'bind': {
            'enemies': [
                ('bomber', '自爆囊——距离 <60 时开始闪烁，'
                           '约 1.2 秒后原地爆炸。被炸到就计数'),
                ('bomber_big', '爆破工头——自爆囊的精英版，'
                               '爆炸半径更大，但它自己也会被炸伤'),
                ('mech', '区域首领「机械领主」——第 5 关必打，'
                         '残血通关通常发生在这场'),
            ],
            'traps': [
                ('shock', '电弧栅栏——机械坟场的地面机关，'
                          '踩中会短暂麻痹（更容易被自爆囊贴上）'),
                ('spike', '地刺——固定伤害，好躲但别在混战里踩'),
            ],
            'tip': '躲自爆囊的关键：听到"滴"声立刻反向冲刺，'
                   '不要原地绕圈。残血通关建议留一发冲刺。',
        },
    },
}
BONUS = 'd_gift'
# 奖励副本以**金币**为主要支付手段（需求：金币易得，钻石只做点缀）
#
# 定价依据（实测经济曲线，见 tools/econ_probe.py）：
#   全程 35 关首通金币 ≈ 5100（击杀掉币 + 宝箱）
#   首通角色解锁 800+1600+2600 = 5000
#   => 若奖励副本定价 12000，玩家必须"通关后重刷 2 遍以上"才够，
#      而重刷时角色/武器已经买完，收益感极低 —— 经济通缩。
#   改为 6500：通关 + 顺手刷 1 个副本即可达成，
#   且玩家能在"买角色"和"买奖励副本"之间做真实取舍。
BONUS_PRICE = 6500       # 金币
BONUS_PRICE_DIA = 0      # 不额外要钻石
STAGES_PER_SCENE = 5

# 每个场景的怪物池。字段会在 enemy.py 里对应真实怪物。
SCENE_MOBS = {
    'crust': {'small': ['slime', 'slug'], 'elite': ['slime_big'],
              'boss': 'warlord', 'bigboss': 'warlord'},
    'sewer': {'small': ['slug', 'drone'], 'elite': ['drone_big'],
              'boss': 'swarmqueen', 'bigboss': 'swarmqueen'},
    'facility': {'small': ['drone', 'bomber'], 'elite': ['bomber_big'],
                 'boss': 'mech', 'bigboss': 'mech'},
    'core': {'small': ['spore', 'wraith'], 'elite': ['wraith_big'],
             'boss': 'protocol', 'bigboss': 'origin'},
    'd_mine': {'small': ['slug', 'bomber'], 'elite': ['slime_big'],
               'boss': 'foreman', 'bigboss': 'foreman'},
    'd_lab': {'small': ['wraith', 'drone'], 'elite': ['wraith_big'],
              'boss': 'specimen', 'bigboss': 'specimen'},
    'd_gift': {'small': ['slime', 'slug'], 'elite': [], 'boss': None,
               'bigboss': None},
}

# ================================================================ 经济曲线
# 金币"易得"（需求 4）——所以要保证**单局内产出能支撑解锁与培养**，
# 而不是让玩家为了买一个角色反复刷同一关。
#
# 掉落设计（双端同构）：
#   · 小怪：掉 1~3 枚，每枚面值 = coin_value(scene, stage_idx)
#   · 精英：额外 +2 枚，且面值 ×2
#   · 小 Boss（第 3 关）：固定爆 26 枚高面值金币
#   · 大 Boss（第 5 关）：固定爆 26 枚高面值金币 + 2 枚钻石
#   · 宝箱：coin 箱是主力（normal 30~70 / superb 90~180），另有海量材料
#
# coin_value 随**全局关卡序号**递增（与 difficulty 同源），
# 保证"越深越富"，避免后期还在捡 1 金币。
COIN_BASE = 2.0
COIN_STEP = 0.40
COIN_ELITE_MUL = 1.8
COIN_BOSS_MUL = 3.5


def coin_value(scene_idx, stage_idx, per_scene=STAGES_PER_SCENE):
    """单枚金币的面值（按全局关卡序号递增）。"""
    g = max(0, scene_idx) * per_scene + max(0, stage_idx)
    return int(round(COIN_BASE + g * COIN_STEP))


def scene_index_of(scene_key):
    """场景在解锁顺序里的下标（crust=0 …）。用于经济/难度插值。"""
    try:
        return all_scenes().index(scene_key)
    except ValueError:
        return 0


# ================================================================ 污染减益
# 叙事依据：CHAPTER_STORY 里每个场景的"污染浓度"读数 3% / 21% / 48% / 96%。
# 污染是逐渐逼近的，所以**越往下走，角色受到的侵蚀越重**——这不是惩罚性
# 设计，而是让"推进"本身带代价：你越接近源头，越需要靠装备、天赋和操作
# 去抵消它。玩家可以在客厅里看到当前减益，提前规划。
#
# 每条减益字段：
#   hp_cut      最大生命减少量（整数，向上取整）
#   spd         移速倍率（<1 更慢）
#   regen       能量回复倍率（<1 更慢）
#   drain       每秒持续流血（污染侵蚀；0 = 不流）
#   name/desc   给玩家看的说明
POLLUTION = {
    'crust':    {'pct': 3,  'hp_cut': 0, 'spd': 1.00, 'regen': 1.00,
                 'drain': 0.0, 'tint': (150, 132, 108),
                 'desc': '空气里的灰还没落到皮肤上。'},
    'sewer':    {'pct': 21, 'hp_cut': 1, 'spd': 0.97, 'regen': 0.95,
                 'drain': 0.0, 'tint': (96, 130, 96),
                 'desc': '样本有活性。你会觉得比平时慢一点。'},
    'facility': {'pct': 48, 'hp_cut': 2, 'spd': 0.93, 'regen': 0.88,
                 'drain': 0.05, 'tint': (110, 116, 138),
                 'desc': '污染开始改写机械。持续侵蚀生效。'},
    'core':     {'pct': 96, 'hp_cut': 4, 'spd': 0.88, 'regen': 0.78,
                 'drain': 0.14, 'tint': (170, 80, 96),
                 'desc': '这里就是源头。协议提示：已无撤退路线。'},
    # ---- 副本：偏离主线，浓度按前后主线场景插值 ----
    'd_mine':   {'pct': 30, 'hp_cut': 1, 'spd': 0.96, 'regen': 0.93,
                 'drain': 0.02, 'tint': (140, 120, 90),
                 'desc': '支线信号源。矿井深处的空气更稠。'},
    'd_lab':    {'pct': 60, 'hp_cut': 3, 'spd': 0.91, 'regen': 0.84,
                 'drain': 0.08, 'tint': (110, 150, 170),
                 'desc': '低温压住了污染，但结晶会割伤你。'},
    'd_gift':   {'pct': 0,  'hp_cut': 0, 'spd': 1.00, 'regen': 1.00,
                 'drain': 0.0, 'tint': (200, 180, 120),
                 'desc': '协议最后的善意。这里的空气是干净的。'},
}
# 减益随关卡在场景内继续加深：第 1 关按表，第 5 关额外再走 40%
POLLUTION_STAGE_SPAN = 0.40


def pollution(scene_key, stage_idx=0):
    """返回该场景某一关的污染减益（已按关卡深度插值）。

    结果 dict:
      {'pct','hp_cut','spd','regen','drain','tint','desc','stage'}
    """
    base = POLLUTION.get(scene_key)
    if base is None:
        base = POLLUTION.get(MAIN[0])
    k = 0.0
    if STAGES_PER_SCENE > 1:
        k = (max(0, min(STAGES_PER_SCENE - 1, int(stage_idx)))
             / float(STAGES_PER_SCENE - 1)) * POLLUTION_STAGE_SPAN
    return {
        'pct': base['pct'],
        'stage': int(stage_idx),
        'hp_cut': int(base['hp_cut'] + round(k * base['hp_cut'])),
        'spd': round(base['spd'] * (1.0 - k * (1.0 - base['spd'])), 4),
        'regen': round(base['regen'] * (1.0 - k * (1.0 - base['regen'])), 4),
        'drain': round(base['drain'] * (1.0 + k), 4),
        'tint': base['tint'],
        'desc': base['desc'],
    }


def pollution_lines(scene_key, stage_idx=0):
    """污染减益的展示文案（HUD/客厅用）。无减益时返回空列表。"""
    p = pollution(scene_key, stage_idx)
    out = []
    if p['hp_cut'] > 0:
        out.append('生命上限 -%d' % p['hp_cut'])
    if p['spd'] < 0.999:
        out.append('移速 -%d%%' % int(round((1.0 - p['spd']) * 100)))
    if p['regen'] < 0.999:
        out.append('回能 -%d%%' % int(round((1.0 - p['regen']) * 100)))
    if p['drain'] > 0:
        out.append('每秒侵蚀 -%.2f' % p['drain'])
    return out

# 难度系数：随场景序号与关内序号递增
# 全局单调递增：第 N 关（全局编号 1..35）一定比第 N-1 关难，
# 场景之间不允许出现回落，符合"难度逐级递增"的要求。
def difficulty(scene_idx, stage_idx, per_scene=STAGES_PER_SCENE):
    """返回 (敌人数量倍率, 敌人强度倍率)。

    scene_idx 是场景在解锁顺序中的下标，stage_idx 是场景内 0..4。
    用全局关卡序号统一插值，保证跨场景也严格单调。
    """
    g = scene_idx * per_scene + stage_idx      # 全局序号（0 起）
    return (1.0 + g * 0.045,
            1.0 + g * 0.062)


def stage_kind(stage_idx):
    """某一关的类型：'normal' / 'miniboss' / 'boss'"""
    if stage_idx == 2:
        return 'miniboss'
    if stage_idx == 4:
        return 'boss'
    return 'normal'


def scene_stage_name(stage_idx):
    """场景内小关的可读名（用于过场标题）。"""
    k = stage_kind(stage_idx)
    if k == 'miniboss':
        return '第 %d 关 · 精英哨点' % (stage_idx + 1)
    if k == 'boss':
        return '第 %d 关 · 底层核心' % (stage_idx + 1)
    return '第 %d 关' % (stage_idx + 1)


def scene_info(key):
    return CHAPTER_STORY.get(key, {'name': key, 'sub': key.upper(),
                                   'enter': [], 'clear': [],
                                   'tint': (140, 140, 140)})


def act_title(scene_key):
    """该场景属于第几幕（过场标题用，需求 2）。"""
    return ACT_TITLE.get(scene_key, '')


def stage_beat(scene_key, stage_idx):
    """某场景某关的叙事节拍（需求 2：让故事贯穿全程）。

    返回该关的台词列表；没有专门写节拍时，回退到"进场景台词"。
    """
    beats = STAGE_BEATS.get(scene_key)
    if not beats:
        return []
    i = max(0, min(len(beats) - 1, int(stage_idx)))
    return list(beats[i])


def scene_label(key):
    return scene_info(key)['name']


def total_stages():
    """全部关卡数：7 个主题场景 × 5 关 = 35。
    7 = 4 主线 + 2 副本 + 1 奖励副本。"""
    return (len(MAIN) + len(DUNGEONS) + 1) * STAGES_PER_SCENE


def all_scenes():
    """7 个主题场景的 key（顺序：主线 → 副本 → 奖励）。"""
    return list(MAIN) + list(DUNGEONS.keys()) + [BONUS]


# ================================================================ 进度推进
def scene_order(prof):
    """当前玩家可见的场景顺序（主线 + 已解锁副本）。"""
    out = list(MAIN)
    for k, d in DUNGEONS.items():
        if k in prof.get('unlocked_dungeons', []):
            out.insert(MAIN.index(d['after']) + 1, k)
    return out


def _cond_met(cond, best, cleared):
    """通用条件判定。best 是 profile['scene_best'][after] 的子集。

    所有条件都"与"关系；缺省字段视为不约束。
    可追踪字段（见 DUNGEONS 注释）：
      kills       累计击杀门槛（越大越好）
      trap_hits   踩陷阱次数上限（越小越好，0 表示未记录）
      bomber_hits 被自爆类炸到次数上限（越小越好）
      no_death    必须零死亡通关过
      low_hp      必须残血通关过（把"险胜"本身作为实力证明）
      cleared     必须通关过前置场景
    """
    ok = True
    if cond.get('kills', 0) > 0:
        ok = ok and (best.get('kills', 0) >= cond['kills'])
    if cond.get('cleared'):
        ok = ok and bool(cleared)
    if cond.get('no_death'):
        ok = ok and bool(best.get('no_death', False))
    if cond.get('low_hp'):
        ok = ok and bool(best.get('low_hp', False))
    # 上限类：没记录过（= 0 次）也算达成，避免新档永远无法满足
    if 'trap_hits' in cond:
        v = best.get('trap_hits')
        ok = ok and (v is None or v <= cond['trap_hits'])
    if 'bomber_hits' in cond:
        v = best.get('bomber_hits')
        ok = ok and (v is None or v <= cond['bomber_hits'])
    return ok


def check_dungeon_unlock(prof, dkey, run_stats):
    """检查副本解锁条件是否满足。

    run_stats 本次通关该场景的统计（可为 None，此时只看历史最好成绩）：
      {'kills':n, 'cleared':bool, 'no_death':bool, 'low_hp':bool,
       'trap_hits':n, 'bomber_hits':n}
    注意：条件里的"上限类"（trap_hits / bomber_hits）取**历史最好**成绩，
    所以本次成绩差不会把已经达成的记录顶掉。
    """
    d = DUNGEONS.get(dkey)
    if not d:
        return False
    after = d['after']
    # 必须先通关前置场景
    if after not in prof.get('cleared_scenes', []):
        return False
    best = (prof.get('scene_best') or {}).get(after) or {}
    if run_stats:
        # 本次成绩先并入一份临时副本，避免修改调用方的数据
        best = dict(best)
        best['kills'] = max(best.get('kills', 0), int(run_stats.get('kills', 0)))
        if run_stats.get('no_death'):
            best['no_death'] = True
        if run_stats.get('low_hp'):
            best['low_hp'] = True
        for k in ('trap_hits', 'bomber_hits'):
            if k in run_stats and run_stats[k] is not None:
                cur = best.get(k)
                best[k] = run_stats[k] if cur is None else min(cur, run_stats[k])
    return _cond_met(d['cond'], best, True)


def dungeon_cond_lines(dkey):
    """返回该副本的全部条件条目 [(标签, 键, 目标值, 比较方向)]，供 UI 打勾。"""
    d = DUNGEONS.get(dkey)
    if not d:
        return []
    cond = d['cond']
    out = []
    if cond.get('cleared'):
        out.append(('通关前置场景', 'cleared', True, 'ge'))
    if cond.get('kills', 0) > 0:
        out.append(('单局击杀', 'kills', cond['kills'], 'ge'))
    if 'trap_hits' in cond:
        out.append(('踩中陷阱', 'trap_hits', cond['trap_hits'], 'le'))
    if 'bomber_hits' in cond:
        out.append(('被自爆波及', 'bomber_hits', cond['bomber_hits'], 'le'))
    if cond.get('no_death'):
        out.append(('零死亡通关', 'no_death', True, 'flag'))
    if cond.get('low_hp'):
        out.append(('残血通关', 'low_hp', True, 'flag'))
    return out


def bonus_unlockable(prof):
    """奖励副本是否已经可以向玩家报价（打完主线最终场景 + 还没买）。"""
    return (not prof.get('bonus_unlocked', False)
            and 'core' in prof.get('cleared_scenes', []))


def scene_key_of(scene_key):
    """场景 id -> 排他性强度（越小越浅）。用于排序/展示。"""
    order = all_scenes()
    try:
        return order.index(scene_key)
    except ValueError:
        return len(order)


# ================================================================ 场景叙事绑定
def dungeon_bind(dkey):
    """返回副本条件的"机制卡"数据，供 UI 展开（1.3 需求 2）。

    -> {'enemies': [(key, 说明), ...], 'traps': [(key, 说明), ...],
        'tip': '一句话战术'} 或 None
    """
    d = DUNGEONS.get(dkey)
    if not d:
        return None
    return d.get('bind')


def dungeon_tip(dkey):
    """副本的一句话战术提示（1.3 需求 2）。"""
    b = dungeon_bind(dkey)
    return (b or {}).get('tip', '')


def dungeon_bind_cards(dkey):
    """把 bind 拍平成 UI 可直接渲染的卡片列表。

    -> [{'kind':'enemy'|'trap', 'key':..., 'name':..., 'desc':...}, ...]
    name 优先取图鉴里的正式名，取不到则回退到 key。
    """
    b = dungeon_bind(dkey)
    if not b:
        return []
    from . import codex as _X
    from . import hazard as _H
    out = []
    for k, desc in b.get('enemies', []):
        v = _X.ENEMY_CODEX.get(k)
        out.append({'kind': 'enemy', 'key': k,
                    'name': v[0] if v else k, 'desc': desc})
    for k, desc in b.get('traps', []):
        spec = _H.TRAP_SPEC.get(k)
        out.append({'kind': 'trap', 'key': k,
                    'name': spec['name'] if spec else k, 'desc': desc})
    return out


# ================================================================ 提示文案
def stage_intro(scene, stage_idx):
    """进入某关时的横幅文案（需求 15：关卡提示）。"""
    k = stage_kind(stage_idx)
    name = scene_label(scene)
    if k == 'miniboss':
        return f'{name} · 第 {stage_idx + 1} 关  · 检测到精英首领'
    if k == 'boss':
        return f'{name} · 第 {stage_idx + 1} 关  · 污染核心反应'
    return f'{name} · 第 {stage_idx + 1} 关'


def pollution_warning(scene_key, stage_idx=0):
    """进关时的污染警告文案（含浓度读数），无减益时返回 None。"""
    p = pollution(scene_key, stage_idx)
    lines = pollution_lines(scene_key, stage_idx)
    if not lines:
        return None
    return ('污染浓度 %d%%' % p['pct'], ' · '.join(lines))
