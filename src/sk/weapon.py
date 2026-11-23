# -*- coding: utf-8 -*-
"""武器数据与开火逻辑。

需求 6（1.4 强化版）
--------------------
原版只有 6 把"基础型号"，品质提升只是把 dmg 乘一个倍率 —— 太单调。
1.4 起参考《元气骑士》的武器设计：

  1. **11 把基础型号**（白色基准），近战 / 远程都有：
       远程：学徒手枪、蜂鸟冲锋枪、蒸汽霰弹枪、幽蓝激光枪、
             脆脆火箭筒、金色传说炮、钉刺弩、霰流喷射器、磁轨狙击
       近战：废铁砍刀、等离子长刃
     每把有独立的弹道/节奏/手感，而不是同一把枪换个数字。

  2. **品质不再只是数值倍率**，而是逐级"加机制"
     （见 gamedata.QUALITIES 的 `mods` 字段 + `apply_quality`）：

       白  普通    基准
       绿  精良    +射速 / +弹速
       蓝  稀有    +1 发（散射/连发）/ 大幅弹速
       紫  史诗    +1 穿透
       金  传说    击杀迸射（溅射小弹）
       红  赤红    弹跳 / 分裂（命中后溅射到附近敌人）
       璀璨 璀璨    追猎（子弹带轻微跟踪）+ 全属性提升

     这样"往上升一级"玩家能明显感觉到**玩法**变了，而不只是数字变大。

  3. **近战武器**（`melee=True`）不发射子弹，而是在身前挥出扇形斩击：
     一次伤害覆盖扇形范围内的所有敌人，射程短但伤害高、不耗能。
     品质提升对近战意味着：斩击范围变大、附加穿透连击、高等级带剑气。

贴图：像素素材表里只有 6 格武器图，所以新武器用**程序化派生贴图**
（复用现有 wpn_*.png + 调色/形变），在 assets.py 里生成，不依赖新素材。
"""
import math
from dataclasses import dataclass

from .bullet import Bullet, weapon_impact


@dataclass(frozen=True)
class WeaponSpec:
    key: str
    name: str
    desc: str
    dmg: float          # 单发伤害
    cd: float           # 射击间隔（秒）
    speed: float        # 弹速 px/s
    count: int          # 单次弹丸数
    spread: float       # 总散射角（度）
    cost: float         # 单次耗能
    bullet: str         # 子弹贴图 key
    bsize: int = 14     # 子弹绘制尺寸
    pierce: int = 0     # 可穿透敌人数
    aoe: float = 0.0    # 爆炸半径（>0 表示爆炸弹）
    life: float = 1.25  # 存活秒数
    shake: float = 0.8
    sound: str = 'shoot'
    kick: float = 0.0   # 后坐力推玩家
    color: tuple = (255, 214, 120)
    price: int = 40
    # ---- 1.4 新增：机制字段 ----
    melee: bool = False     # 近战（挥砍）而非射击
    reach: float = 46.0     # 近战斩击半径
    arc: float = 100.0      # 近战斩击扇形角度（度）
    sprite: str = ''        # 专属贴图 key（空则用 key 推导 wpn_<key>）
    tier: int = 0           # 掉落池分层基准（越大越后期）
    vfx: str = 'spark'       # 2.0 专属战斗视觉语言


FISTS = WeaponSpec('fists', '手刀', '能量耗尽时的应急攻击', 2.0, 0.65,
                   0.0, 1, 0.0, 0.0, 'b_bullet', melee=True,
                   reach=82.0, arc=105.0, color=(190, 195, 205))

WEAPONS = {
    # ============================================================ 远程
    'pistol': WeaponSpec(
        'pistol', '学徒手枪', '不耗能的万能开局枪', 7, 0.26, 430, 1, 2.0, 0.0,
        'b_bullet', 13, 0, 0.0, 1.3, 0.7, 'shoot', 0.0, (255, 214, 120), 0,
        tier=0),
    'smg': WeaponSpec(
        'smg', '蜂鸟冲锋枪', '射速极快，耗能轻微', 4, 0.095, 470, 1, 7.0, 1.2,
        'b_bolt', 14, 0, 0.0, 1.15, 0.7, 'shoot', 0.0, (120, 232, 240), 45,
        tier=0),
    'shotgun': WeaponSpec(
        'shotgun', '蒸汽霰弹枪', '近距离一枪糊脸', 4, 0.72, 380, 6, 20.0, 3.0,
        'b_bullet', 12, 0, 0.0, 0.62, 2.4, 'shoot_heavy', 26.0,
        (255, 186, 96), 55, tier=0),
    'laser': WeaponSpec(
        'laser', '幽蓝激光枪', '高速穿透，指哪打哪', 10, 0.17, 940, 1, 0.6, 2.6,
        'b_laser', 18, 3, 0.0, 0.85, 0.6, 'laser', 0.0, (255, 96, 120), 65,
        tier=1),
    'rocket': WeaponSpec(
        'rocket', '脆脆火箭筒', '大范围爆炸重炮，可摧毁掩体', 24, 1.05, 300, 1, 1.5, 5.0,
        'b_rocket', 16, 0, 46.0, 1.6, 3.4, 'shoot_heavy', 34.0,
        (200, 220, 200), 80, tier=2),
    'cannon': WeaponSpec(
        'cannon', '金色传说炮', '三连高伤，稀有的传说武器', 15, 0.34, 540, 3, 7.0, 3.6,
        'b_plasma', 16, 0, 0.0, 1.25, 1.5, 'shoot_heavy', 6.0,
        (255, 226, 96), 110, tier=2),

    # ---- 1.4 新增 5 把（需求 6：白色基础型号 ≥ 10）----
    'crossbow': WeaponSpec(
        'crossbow', '钉刺弩', '单发高伤，弹道笔直且穿透 1 个敌人',
        18, 0.58, 620, 1, 1.0, 1.6, 'b_bolt', 18, 1, 0.0, 1.4, 1.4,
        'shoot', 14.0, (214, 232, 160), 70, sprite='wpn_laser', tier=1),
    'flamer': WeaponSpec(
        'flamer', '霰流喷射器', '近程高速散射，贴脸输出极高但射程短',
        3, 0.075, 300, 1, 16.0, 0.55, 'b_hex', 11, 0, 0.0, 0.42, 0.5,
        'shoot', 0.0, (255, 140, 70), 62, sprite='wpn_smg', tier=1),
    'railgun': WeaponSpec(
        'railgun', '磁轨狙击', '蓄力一击，穿透整条直线，耗能高',
        38, 1.35, 1250, 1, 0.0, 6.5, 'b_laser', 20, 6, 0.0, 1.05, 3.8,
        'laser', 40.0, (150, 220, 255), 120, sprite='wpn_cannon', tier=2),

    # ---- 1.4 新增：近战（需求 6：近战 & 远程都要有）----
    'blade': WeaponSpec(
        'blade', '废铁砍刀', '近战武器。身前扇形横扫，不耗能，伤害集中',
        16, 0.42, 0, 1, 0.0, 0.0, 'b_bullet', 14, 0, 0.0, 0.0, 1.2,
        'shoot_heavy', 0.0, (220, 226, 232), 85,
        melee=True, reach=48.0, arc=100.0, sprite='wpn_shotgun', tier=1),
    'plasma_blade': WeaponSpec(
        'plasma_blade', '等离子长刃', '近战武器。范围更大的等离子斩，附带击退',
        26, 0.62, 0, 1, 0.0, 0.0, 'b_plasma', 16, 2, 0.0, 0.0, 2.2,
        'laser', 0.0, (180, 240, 255), 130,
        melee=True, reach=62.0, arc=128.0, sprite='wpn_laser', tier=2),
}

def _new_weapon(key, name, desc, dmg, cd, speed, count, spread, cost,
                bullet, color, price, tier=1, *, pierce=0, aoe=0,
                melee=False, reach=46, arc=100, vfx='spark'):
    """2.0 独立武器目录：每把都有唯一图标、色彩和战斗节奏。"""
    return WeaponSpec(key, name, desc, dmg, cd, speed, count, spread, cost,
                      bullet, 15, pierce, aoe, 1.35 if not melee else 0,
                      0.7 + dmg / 28, 'laser' if bullet == 'b_laser' else
                      ('shoot_heavy' if dmg >= 18 else 'shoot'),
                      min(38, dmg * 0.7), color, price, melee, reach, arc,
                      '', tier, vfx)


_V2 = [
    ('pulse_pistol', '脉冲手枪', '三色脉冲，弹道稳定', 9, .32, 540, 1, 0, 1.0, 'b_plasma', (90, 245, 255), 65, 0, 0, 0, False, 0, 0, 'pulse'),
    ('arc_smg', '电弧蜂群', '高速电弧短点射', 5, .11, 550, 2, 10, 1.8, 'b_hex', (132, 204, 255), 90, 1, 0, 0, False, 0, 0, 'arc'),
    ('crystal_shotgun', '棱晶散射器', '晶片广角散射', 6, .86, 420, 7, 27, 3.5, 'b_bolt', (168, 118, 255), 105, 1, 0, 0, False, 0, 0, 'shard'),
    ('ion_carbine', '离子卡宾', '轻量穿透离子束', 12, .29, 720, 1, 1, 2.0, 'b_laser', (105, 238, 226), 110, 1, 1, 0, False, 0, 0, 'ion'),
    ('burst_rifle', '破晓三连', '三发短促连击', 7, .39, 660, 3, 4, 2.2, 'b_bullet', (255, 188, 105), 100, 1, 0, 0, False, 0, 0, 'burst'),
    ('needle_rifle', '毒针步枪', '高精度细针', 13, .42, 760, 1, 0, 1.5, 'b_bolt', (148, 232, 115), 100, 1, 2, 0, False, 0, 0, 'needle'),
    ('frost_pistol', '霜凝短铳', '冷光速射', 8, .21, 480, 1, 3, 1.5, 'b_hex', (140, 217, 255), 95, 1, 0, 0, False, 0, 0, 'frost'),
    ('corrosion_sprayer', '腐蚀喷射器', '短程锥形喷射', 4, .13, 330, 3, 22, 1.2, 'b_plasma', (160, 240, 96), 105, 1, 0, 0, False, 0, 0, 'acid'),
    ('coil_cannon', '线圈裂变炮', '高压重弹，带爆炸', 25, 1.1, 520, 1, 0, 5.0, 'b_rocket', (255, 103, 171), 150, 2, 0, 34, False, 0, 0, 'coil'),
    ('sonic_blaster', '共振震荡炮', '宽扇形音浪', 7, .7, 450, 5, 34, 3.5, 'b_hex', (255, 206, 116), 125, 2, 0, 0, False, 0, 0, 'wave'),
    ('prism_laser', '虹棱长枪', '双束穿透激光', 15, .55, 960, 2, 2, 4.2, 'b_laser', (220, 132, 255), 155, 2, 3, 0, False, 0, 0, 'prism'),
    ('gravity_launcher', '引力井', '缓慢重弹，命中爆裂', 27, 1.32, 320, 1, 0, 5.8, 'b_rocket', (148, 115, 245), 165, 2, 0, 58, False, 0, 0, 'gravity'),
    ('ember_mortar', '余烬迫击', '燃烧核心范围打击', 22, 1.0, 350, 2, 6, 5.0, 'b_rocket', (255, 124, 75), 155, 2, 0, 45, False, 0, 0, 'ember'),
    ('volt_crossbow', '雷鸣连弩', '电磁连弩', 16, .48, 690, 2, 5, 2.7, 'b_bolt', (115, 242, 248), 135, 2, 1, 0, False, 0, 0, 'volt'),
    ('scatter_bow', '月影星弓', '三箭抛射', 10, .62, 620, 3, 13, 1.8, 'b_bolt', (198, 180, 255), 120, 1, 1, 0, False, 0, 0, 'moon'),
    ('void_revolver', '虚空左轮', '高伤缓射穿透弹', 26, .9, 850, 1, 0, 3.0, 'b_hex', (219, 94, 255), 170, 2, 3, 0, False, 0, 0, 'void'),
    ('plasma_axe', '等离子战斧', '重型弧形劈砍', 29, .72, 0, 1, 0, 0, 'b_plasma', (105, 238, 235), 165, 2, 0, 0, True, 66, 126, 'axe'),
    ('twin_daggers', '双生影刃', '高速近身双斩', 13, .23, 0, 1, 0, 0, 'b_hex', (215, 145, 255), 120, 1, 0, 0, True, 43, 112, 'twin'),
    ('shock_hammer', '震地重锤', '广范围雷击挥砸', 36, 1.05, 0, 1, 0, 0, 'b_hex', (255, 210, 98), 175, 2, 0, 0, True, 58, 150, 'hammer'),
    ('crystal_spear', '晶脊长矛', '长射程窄角刺击', 23, .54, 0, 1, 0, 0, 'b_bolt', (170, 250, 255), 155, 2, 2, 0, True, 88, 55, 'spear'),
    ('sunblade', '日冕光刃', '高能宽角剑气', 31, .68, 0, 1, 0, 0, 'b_laser', (255, 221, 131), 190, 2, 2, 0, True, 70, 140, 'sun'),
]
for row in _V2:
    key, name, desc, dmg, cd, speed, count, spread, cost, bullet, color, price, tier, pierce, aoe, melee, reach, arc, vfx = row
    WEAPONS[key] = _new_weapon(key, name, desc, dmg, cd, speed, count, spread,
                               cost, bullet, color, price, tier, pierce=pierce,
                               aoe=aoe, melee=melee, reach=reach, arc=arc,
                               vfx=vfx)

# 2.1：每个主题的一把金色首领武器和一把红色核心武器，另有四把常规型号。
# 图像由 generate_v2_art.py 按 key 的结构语言独立绘制。
_V21 = [
    ('crust_glaive', '焦土戟', '裂开的合金戟刃，扫出炽热碎屑', 31, .67, 0, 1, 0, 0, 'b_hex', (255, 151, 83), 230, 2, 1, 0, True, 75, 130, 'ember'),
    ('sewer_harpoon', '腐潮鱼叉', '长距离穿刺并释放腐蚀', 28, .73, 0, 1, 0, 0, 'b_bolt', (91, 224, 166), 230, 2, 2, 0, True, 98, 48, 'acid'),
    ('facility_saw', '机枢圆锯', '高速旋刃，贴身连斩', 21, .25, 0, 1, 0, 0, 'b_hex', (255, 198, 82), 240, 2, 0, 0, True, 53, 116, 'coil'),
    ('core_repeater', '协议连星', '连续放出污染光束', 16, .16, 880, 2, 5, 3, 'b_laser', (224, 111, 245), 245, 2, 2, 0, False, 0, 0, 'void'),
    ('mine_drill', '矿脉穿刺钻', '钨钢螺旋头穿过护甲', 34, .82, 0, 1, 0, 0, 'b_bolt', (241, 179, 90), 235, 2, 3, 0, True, 79, 62, 'rail'),
    ('lab_cryo_staff', '冷库凝霜杖', '冻结触碰目标并向前放出冰晶', 27, .58, 0, 1, 0, 0, 'b_hex', (144, 230, 255), 245, 2, 1, 0, True, 71, 125, 'frost'),
    ('gift_starbow', '净土星弓', '收束的星光连射', 17, .47, 770, 4, 18, 3, 'b_bolt', (255, 232, 140), 245, 2, 2, 0, False, 0, 0, 'sun'),
    ('crust_ruinblade', '毁灭断刃', '残骸军阀遗留的赤色断刃', 46, .81, 0, 1, 0, 0, 'b_plasma', (255, 68, 83), 400, 2, 2, 0, True, 77, 140, 'ember'),
    ('sewer_abyssfang', '深渊双牙', '虫群女王的分叉毒牙', 35, .32, 0, 1, 0, 0, 'b_hex', (248, 75, 112), 410, 2, 1, 0, True, 56, 125, 'acid'),
    ('facility_overdrive', '超载矩阵炮', '机枢核心驱动的灼热重炮', 40, 1.03, 520, 3, 12, 7, 'b_rocket', (250, 75, 88), 450, 2, 1, 48, False, 0, 0, 'coil'),
    ('core_nihility', '虚无裁断', '污染原点凝成的赤红判决', 54, 1.12, 0, 1, 0, 0, 'b_laser', (255, 55, 155), 500, 2, 3, 0, True, 102, 138, 'void'),
    ('mine_faultaxe', '断层巨斧', '矿井监工的裂地重斧', 55, 1.17, 0, 1, 0, 0, 'b_hex', (255, 88, 84), 440, 2, 1, 0, True, 82, 155, 'axe'),
    ('lab_zerobeam', '绝对零度炮', '冷库实验的赤红冻结射线', 39, .74, 860, 2, 1, 6, 'b_laser', (249, 91, 135), 460, 2, 4, 0, False, 0, 0, 'frost'),
    ('gift_dawnkeeper', '晨曦守护剑', '净土守卫的最后誓言', 49, .68, 0, 1, 0, 0, 'b_plasma', (255, 104, 93), 475, 2, 2, 0, True, 85, 150, 'sun'),
    ('trench_blade', '堑壕直刀', '简洁可靠的近战直刀', 18, .39, 0, 1, 0, 0, 'b_bullet', (184, 209, 238), 100, 1, 0, 0, True, 59, 95, 'rust'),
    ('moss_whip', '苔链鞭', '柔性链刃覆盖宽广扇区', 17, .34, 0, 1, 0, 0, 'b_hex', (120, 237, 140), 118, 1, 0, 0, True, 73, 168, 'acid'),
    ('mirror_shield', '镜面盾刃', '近身撞击时反射棱光', 24, .61, 0, 1, 0, 0, 'b_plasma', (170, 200, 255), 125, 1, 0, 0, True, 48, 175, 'prism'),
    ('meteor_pike', '陨铁骑枪', '窄角远距突刺', 30, .57, 0, 1, 0, 0, 'b_bolt', (255, 172, 132), 130, 1, 2, 0, True, 105, 44, 'rail'),
]
for row in _V21:
    key, name, desc, dmg, cd, speed, count, spread, cost, bullet, color, price, tier, pierce, aoe, melee, reach, arc, vfx = row
    WEAPONS[key] = _new_weapon(key, name, desc, dmg, cd, speed, count, spread,
                               cost, bullet, color, price, tier, pierce=pierce,
                               aoe=aoe, melee=melee, reach=reach, arc=arc,
                               vfx=vfx)

# 2.3 五把独立近战型号，分别进入白/绿/蓝/紫/金品质池。
_V23_MELEE = [
    ('scrap_saber', '荒原短刀', '轻快宽角斩击', 16, .38, 0, 1, 0, 0, 'b_bullet', (205, 218, 225), 90, 0, 0, 0, True, 86, 112, 'rust'),
    ('vine_sickle', '蔓生镰', '腐蚀刃使目标持续受伤', 21, .46, 0, 1, 0, 0, 'b_hex', (132, 237, 150), 125, 1, 0, 0, True, 94, 136, 'acid'),
    ('glacier_fang', '冰牙剑', '冰刃降低目标移动速度', 26, .55, 0, 1, 0, 0, 'b_laser', (120, 212, 255), 165, 1, 0, 0, True, 98, 114, 'frost'),
    ('thunder_axe', '雷暴斧', '命中向附近敌人传递电弧', 33, .74, 0, 1, 0, 0, 'b_hex', (194, 150, 255), 210, 2, 0, 0, True, 102, 142, 'arc'),
    ('solar_cleaver', '曜金巨刃', '炽热斩击灼烧敌人', 42, .88, 0, 1, 0, 0, 'b_plasma', (255, 206, 92), 270, 2, 0, 0, True, 110, 155, 'sun'),
]
for row in _V23_MELEE:
    key, name, desc, dmg, cd, speed, count, spread, cost, bullet, color, price, tier, pierce, aoe, melee, reach, arc, vfx = row
    WEAPONS[key] = _new_weapon(key, name, desc, dmg, cd, speed, count, spread,
                               cost, bullet, color, price, tier, pierce=pierce,
                               aoe=aoe, melee=melee, reach=reach, arc=arc, vfx=vfx)

# 2.5: each new model has its own silhouette, firing rhythm and impact effect.
_V25 = [
    ('dust_revolver', '尘暴左轮', '精确单发，高速金属弹', 13, .44, 850, 1, 0, 1.2, 'b_bullet', (218, 191, 139), 95, 0, 0, 0, False, 0, 0, 'brass'),
    ('reed_carbine', '苇叶卡宾', '轻量短点射', 8, .31, 700, 2, 4, 1.6, 'b_bolt', (128, 218, 146), 110, 1, 0, 0, False, 0, 0, 'needle'),
    ('ash_shotgun', '灰烬霰铳', '宽角慢速散弹', 7, .83, 260, 7, 38, 2.9, 'b_bullet', (222, 155, 112), 130, 1, 0, 0, False, 0, 0, 'blast'),
    ('tide_sprayer', '潮汐喷枪', '扇面水晶碎片', 5, .48, 300, 5, 32, 2.0, 'b_plasma', (104, 203, 218), 135, 1, 0, 0, False, 0, 0, 'shard'),
    ('frost_repeater', '霜环连发枪', '冰晶连射使目标减速', 10, .24, 540, 2, 5, 2.2, 'b_hex', (119, 213, 248), 175, 2, 0, 0, False, 0, 0, 'frost'),
    ('echo_blaster', '回声震荡器', '缓速音波扩散', 8, .58, 340, 4, 22, 2.5, 'b_hex', (182, 164, 245), 185, 2, 0, 0, False, 0, 0, 'wave'),
    ('singularity_rifle', '奇点射线枪', '极慢单束激光穿透', 28, .88, 115, 1, 0, 4.0, 'b_laser', (208, 143, 251), 290, 2, 3, 0, False, 0, 0, 'gravity'),
    ('aurora_cannon', '极光聚能炮', '高能单束爆裂激光', 35, 1.0, 165, 1, 0, 5.0, 'b_laser', (255, 224, 118), 360, 2, 3, 40, False, 0, 0, 'prism'),
    ('starfall_bow', '璀璨星落弓', '追猎星矢', 33, .65, 650, 1, 0, 4.3, 'b_bolt', (255, 244, 182), 520, 2, 2, 0, False, 0, 0, 'sun'),
    ('quartz_rifle', '石英步枪', '快速单发穿晶弹', 16, .36, 900, 1, 0, 1.8, 'b_bolt', (184, 215, 246), 155, 1, 1, 0, False, 0, 0, 'shard'),
    ('ember_knife', '余火短匕', '短促扇形火花', 20, .33, 0, 1, 0, 0, 'b_bullet', (252, 145, 99), 115, 0, 0, 0, True, 88, 105, 'ember'),
    ('tidal_spear', '潮汐长矛', '远距离精准突刺', 25, .51, 0, 1, 0, 0, 'b_bolt', (110, 216, 226), 165, 1, 1, 0, True, 112, 65, 'ion'),
    ('obsidian_axe', '黑曜战斧', '沉重弧形劈砍', 37, .83, 0, 1, 0, 0, 'b_hex', (163, 126, 222), 225, 2, 0, 0, True, 103, 145, 'void'),
    ('lumen_whip', '流明光鞭', '大范围柔性光刃', 26, .46, 0, 1, 0, 0, 'b_laser', (246, 226, 135), 240, 2, 1, 0, True, 120, 170, 'sun'),
]
for row in _V25:
    key, name, desc, dmg, cd, speed, count, spread, cost, bullet, color, price, tier, pierce, aoe, melee, reach, arc, vfx = row
    WEAPONS[key] = _new_weapon(key, name, desc, dmg, cd, speed, count, spread,
                               cost, bullet, color, price, tier, pierce=pierce,
                               aoe=aoe, melee=melee, reach=reach, arc=arc, vfx=vfx)

SCENE_BOSS_WEAPONS = {
    scene: {'gold': gold, 'red': red}
    for scene, gold, red in (
        ('crust', 'crust_glaive', 'crust_ruinblade'),
        ('sewer', 'sewer_harpoon', 'sewer_abyssfang'),
        ('facility', 'facility_saw', 'facility_overdrive'),
        ('core', 'terminal_spear', 'core_nihility'),
        ('d_mine', 'mine_drill', 'mine_faultaxe'),
        ('d_lab', 'lab_cryo_staff', 'lab_zerobeam'),
        ('d_gift', 'gift_starbow', 'gift_dawnkeeper'),
    )
}

# 早期 11 把也获得专属视觉标记，旧存档的武器键保持不变。
from dataclasses import replace as _replace
for _key, _effect in {
    'pistol': 'brass', 'smg': 'cyan', 'shotgun': 'blast',
    'crossbow': 'arrow', 'flamer': 'flame', 'blade': 'rust',
    'laser': 'laser', 'cannon': 'nova', 'rocket': 'rocket',
    'railgun': 'rail', 'plasma_blade': 'plasma',
}.items():
    WEAPONS[_key] = _replace(WEAPONS[_key], sprite='', vfx=_effect)

from .v30_weapons import ROWS as _V30_ROWS
for _quality, _rows in _V30_ROWS.items():
    for _row in _rows:
        (_key, _name, _desc, _dmg, _cd, _speed, _count, _spread, _cost,
         _bullet, _color, _price, _tier, _pierce, _aoe, _melee,
         _reach, _arc, _vfx) = _row
        WEAPONS[_key] = _new_weapon(
            _key, _name, _desc, _dmg, _cd, _speed, _count, _spread,
            _cost, _bullet, _color, _price, _tier, pierce=_pierce,
            aoe=_aoe, melee=_melee, reach=_reach, arc=_arc, vfx=_vfx)
for _key, _trait in {
    'starfall_bow': 'rad_star', 'nova_requiem': 'rad_nova',
    'chrono_lance': 'rad_chrono', 'lifeweaver': 'rad_life',
    'prism_ascendant': 'rad_prism', 'orbit_mirror': 'rad_orbit',
}.items():
    WEAPONS[_key] = _replace(WEAPONS[_key], vfx=_trait, sound=_trait)

# 2.6: trim the strongest single-hit weapons before quality and upgrades apply.
for _key, _damage in {
    'mine_faultaxe': 42, 'core_nihility': 42,
    'gift_dawnkeeper': 40, 'crust_ruinblade': 38,
    'solar_cleaver': 34, 'facility_overdrive': 34,
    'lab_zerobeam': 33, 'railgun': 32,
    'obsidian_axe': 32, 'shock_hammer': 31,
}.items():
    WEAPONS[_key] = _replace(WEAPONS[_key], dmg=_damage)

# 4.0: speed up slow heavy gold/red melee swings so melee floor matches tier curve.
for _key, _cd in {
    'sewer_harpoon': 0.52,
    'mine_drill': 0.60,
    'solar_cleaver': 0.58,
    'terminal_spear': 0.70,
    'crust_glaive': 0.55,
    'lab_cryo_staff': 0.49,
    'gilded_halberd': 0.65,
    'mine_faultaxe': 0.68,
    'core_nihility': 0.64,
    'crust_ruinblade': 0.60,
    'bloodmoon_glaive': 0.65,
    'gift_dawnkeeper': 0.60,
}.items():
    WEAPONS[_key] = _replace(WEAPONS[_key], cd=_cd)

# Keep the listed reach, hit test, and visual arc consistent at a safe distance.
for _key, _spec in list(WEAPONS.items()):
    _spec = _replace(_spec, dmg=round(_spec.dmg * 1.08, 2))
    if _spec.cost > 0:
        _spec = _replace(_spec, cost=round(_spec.cost * .7, 2))
    if _spec.melee and _spec.reach < 82.0:
        _spec = _replace(_spec, reach=82.0)
    WEAPONS[_key] = _spec

ORDER = ['pistol', 'smg', 'shotgun', 'crossbow', 'flamer', 'blade',
         'laser', 'cannon', 'rocket', 'railgun', 'plasma_blade'] + [x[0] for x in _V2] + [x[0] for x in _V21] + [x[0] for x in _V23_MELEE] + [x[0] for x in _V25] + [x[0] for _rows in _V30_ROWS.values() for x in _rows]

# 全部武器型号顺序，用于图鉴和资源加载。
BASE_ORDER = list(ORDER)

# A model has exactly one immutable rarity; upgrade levels change strength only.
_FIXED_RARITY = {
    'radiant': ['starfall_bow', 'core_repeater'] + [row[0] for row in _V30_ROWS['radiant']],
    'red': [v['red'] for v in SCENE_BOSS_WEAPONS.values()] + [row[0] for row in _V30_ROWS['red'] if row[0] != 'terminal_spear'],
    'gold': [v['gold'] for v in SCENE_BOSS_WEAPONS.values()] + ['cannon', 'solar_cleaver'] + [row[0] for row in _V30_ROWS['gold']],
    'purple': [
        'laser', 'railgun', 'arc_smg', 'corrosion_sprayer', 'prism_laser',
        'gravity_launcher', 'frost_repeater', 'singularity_rifle',
        'aurora_cannon', 'lumen_whip', 'glass_bow', 'null_carbine',
        'prism_fan', 'phase_needle', 'comet_scythe',
    ],
    'blue': [
        'rocket', 'plasma_blade', 'coil_cannon', 'sonic_blaster',
        'ember_mortar', 'volt_crossbow', 'void_revolver', 'sunblade',
        'glacier_fang', 'thunder_axe', 'echo_blaster', 'spring_carbine',
        'frost_lance', 'echo_pulse', 'arc_lantern', 'gyro_blade',
        'quake_hammer',
    ],
    'green': [
        'crystal_shotgun', 'ion_carbine', 'burst_rifle', 'scatter_bow',
        'plasma_axe', 'twin_daggers', 'crystal_spear', 'moss_whip',
        'meteor_pike', 'vine_sickle', 'reed_carbine', 'ash_shotgun',
        'tide_sprayer', 'quartz_rifle', 'ember_knife', 'tidal_spear',
        'ivy_repeater', 'current_shotgun', 'cloud_staff',
    ],
}
_assigned = {key for keys in _FIXED_RARITY.values() for key in keys}
_FIXED_RARITY['white'] = [key for key in ORDER if key not in _assigned]
QUALITY_POOL = {q: list(_FIXED_RARITY[q]) for q in
                ('white', 'green', 'blue', 'purple', 'gold', 'red', 'radiant')}
QUALITY_BY_KEY = {key: q for q, keys in QUALITY_POOL.items() for key in keys}
assert len(QUALITY_BY_KEY) == len(ORDER) == sum(map(len, QUALITY_POOL.values()))


def quality_of(key):
    return QUALITY_BY_KEY.get(key, 'white')


def roll_quality_key(rng, quality):
    return rng.choice(QUALITY_POOL.get(quality, QUALITY_POOL['white']))


def weapon_flash(game, spec, x, y, ang, melee=False):
    """成本受控的专属枪口/挥砍特效；颜色、宽度与节奏取自武器。"""
    seed = sum(ord(c) for c in spec.key)
    n = 2 + seed % 4
    if melee:
        game.fx.burst(x, y, spec.color, n=n + 2, speed=90 + seed % 50,
                      life=.22, size=2 + seed % 2, spread=spec.arc * math.pi / 180,
                      base_ang=ang, drag=4)
        if spec.vfx in ('sun', 'plasma', 'hammer', 'axe'):
            game.fx.ring(x, y, 7, max(30, spec.reach * .72), .22,
                         spec.color, 2 + seed % 2)
        return
    game.fx.burst(x, y, spec.color, n=n, speed=68 + seed % 62,
                  life=.12 + (seed % 3) * .025, size=2 + seed % 3,
                  spread=.35 + spec.spread * .018, base_ang=ang, drag=6)
    if spec.aoe or spec.vfx in ('nova', 'pulse', 'arc', 'prism', 'gravity', 'void'):
        game.fx.ring(x, y, 2, 12 + min(15, spec.dmg * .4), .15,
                     spec.color, 1 + seed % 2)

# 按掉落层次分层（tier 0 早期 / 1 中期 / 2 后期），越深越可能掉高级型号
# 需求 6：品质越高数量越少 —— 这里体现为"越深越强"，且高 tier 池更小。
DROP_POOL = {
    1: QUALITY_POOL['white'] + QUALITY_POOL['green'][:5],
    2: QUALITY_POOL['green'] + QUALITY_POOL['blue'][:7] + QUALITY_POOL['white'][:5],
    3: QUALITY_POOL['blue'] + QUALITY_POOL['purple'] + QUALITY_POOL['gold'][:2],
}

BOSS_EXCLUSIVE_KEYS = frozenset(
    k for v in SCENE_BOSS_WEAPONS.values() for k in v.values()
)

SHOP_QUALITY_WEIGHTS = {
    'crust':    (('white', 55), ('green', 35), ('blue', 10)),
    'sewer':    (('white', 20), ('green', 45), ('blue', 27), ('purple', 8)),
    'facility': (('green', 20), ('blue', 42), ('purple', 30), ('gold', 8)),
    'core':     (('blue', 25), ('purple', 45), ('gold', 24), ('red', 6)),
    'd_mine':   (('white', 10), ('green', 30), ('blue', 40), ('purple', 17), ('gold', 3)),
    'd_gift':   (('green', 20), ('blue', 40), ('purple', 30), ('gold', 10)),
    'd_lab':    (('green', 10), ('blue', 32), ('purple', 40), ('gold', 15), ('red', 3)),
}


ELITE_QUALITY_WEIGHTS = {
    'crust':    (('white', 55), ('green', 33), ('blue', 12)),
    'sewer':    (('white', 25), ('green', 45), ('blue', 24), ('purple', 6)),
    'facility': (('green', 25), ('blue', 45), ('purple', 25), ('gold', 5)),
    'core':     (('blue', 30), ('purple', 48), ('gold', 19), ('red', 3)),
    'd_mine':   (('white', 15), ('green', 35), ('blue', 35), ('purple', 13), ('gold', 2)),
    'd_gift':   (('green', 25), ('blue', 40), ('purple', 28), ('gold', 7)),
    'd_lab':    (('green', 15), ('blue', 35), ('purple', 38), ('gold', 10), ('red', 2)),
}

CHEST_QUALITY_WEIGHTS = {
    'normal': {
        'crust':    (('white', 45), ('green', 40), ('blue', 15)),
        'sewer':    (('white', 15), ('green', 45), ('blue', 30), ('purple', 10)),
        'facility': (('green', 15), ('blue', 45), ('purple', 32), ('gold', 8)),
        'core':     (('blue', 20), ('purple', 50), ('gold', 25), ('red', 5)),
        'd_mine':   (('white', 10), ('green', 28), ('blue', 42), ('purple', 17), ('gold', 3)),
        'd_gift':   (('green', 15), ('blue', 40), ('purple', 33), ('gold', 12)),
        'd_lab':    (('green', 10), ('blue', 30), ('purple', 42), ('gold', 15), ('red', 3)),
    },
    'superb': {
        'crust':    (('green', 40), ('blue', 45), ('purple', 15)),
        'sewer':    (('blue', 45), ('purple', 45), ('gold', 10)),
        'facility': (('blue', 20), ('purple', 52), ('gold', 24), ('red', 4)),
        'core':     (('purple', 35), ('gold', 47), ('red', 18)),
        'd_mine':   (('blue', 40), ('purple', 45), ('gold', 15)),
        'd_gift':   (('blue', 25), ('purple', 50), ('gold', 22), ('red', 3)),
        'd_lab':    (('blue', 15), ('purple', 45), ('gold', 32), ('red', 8)),
    },
}


def _roll_non_boss_weapons(rng, weights, count=1):
    """按权重抽取非 Boss 专属武器列表（排除重复与璀璨品质）。"""
    total = sum(w for _, w in weights)

    def _pick_quality():
        r = rng.random() * total
        acc = 0.0
        for q, w in weights:
            acc += w
            if r <= acc:
                return q
        return weights[-1][0]

    picked = []
    for _ in range(max(1, int(count))):
        q = _pick_quality()
        base_pool = QUALITY_POOL.get(q, QUALITY_POOL['white'])
        pool = [k for k in base_pool if k not in BOSS_EXCLUSIVE_KEYS and k not in picked]
        if not pool:
            pool = [k for k in base_pool if k not in picked]
        if not pool:
            pool = list(base_pool)
        picked.append(rng.choice(pool))
    return picked


def roll_shop_weapons(rng, scene_key=None, count=2):
    """按章节权重抽取商店在售武器（排除 Boss 专属武器且不重复）。"""
    weights = SHOP_QUALITY_WEIGHTS.get(scene_key) or SHOP_QUALITY_WEIGHTS['crust']
    return _roll_non_boss_weapons(rng, weights, count)


def roll_elite_weapon(rng, scene_key=None):
    """按章节权重抽取精英怪常规掉落武器，返回 (wkey, quality)。"""
    weights = ELITE_QUALITY_WEIGHTS.get(scene_key) or ELITE_QUALITY_WEIGHTS['crust']
    wkey = _roll_non_boss_weapons(rng, weights, 1)[0]
    return wkey, quality_of(wkey)


def roll_chest_weapon(rng, scene_key=None, tier='normal'):
    """按章节权重与宝箱档位抽取开箱武器，返回 (wkey, quality)。"""
    tbl = CHEST_QUALITY_WEIGHTS.get(tier) or CHEST_QUALITY_WEIGHTS['normal']
    weights = tbl.get(scene_key) or tbl['crust']
    wkey = _roll_non_boss_weapons(rng, weights, 1)[0]
    return wkey, quality_of(wkey)


def get(key):
    return WEAPONS.get(key) or WEAPONS['pistol']


def sprite_key(key):
    """2.0: 每种武器都使用对应的原创贴图。"""
    return 'wpn_' + key


# ================================================================ 品质机制
# 需求 6：品质提升是"机制变更"而不是单纯数值。这里把每一级的机制
# 加成集中定义，fire()/melee 都从这里取，保证两端同构、可测。
#
# 键含义：
#   rate    射速倍率（cd 除以它）
#   bspd    弹速倍率
#   extra   额外弹丸数（散射/连发）
#   pierce  额外穿透
#   burst   击杀迸射：击杀时产生的溅射弹数量
#   split   命中分裂：命中后向附近敌人溅射（=弹跳）
#   homing  追猎：子弹转向附近敌人的强度（rad/s）
#   reach   近战范围倍率
#   arc     近战扇形倍率
#   calm    近战附加"剑气"：挥砍时向前放出一发穿透弹
QUALITY_MECH = {
    'white':   {},
    'green':   {'rate': 1.05, 'bspd': 1.08},
    'blue':    {'rate': 1.10, 'bspd': 1.15, 'extra': 1},
    'purple':  {'rate': 1.15, 'bspd': 1.22, 'extra': 1, 'pierce': 1,
                'melee_double': 0.30},
    'gold':    {'rate': 1.20, 'bspd': 1.30, 'extra': 1, 'pierce': 1,
                'burst': 2, 'melee_double': 0.30},
    'red':     {'rate': 1.25, 'bspd': 1.35, 'extra': 1, 'pierce': 2,
                'burst': 2, 'split': 2, 'melee_double': 0.30},
    'radiant': {'rate': 1.30, 'bspd': 1.42, 'extra': 2, 'pierce': 2,
                'burst': 3, 'split': 3, 'homing': 2.4, 'melee_double': 0.30},
}

# 品质在成长序列里的下标（近战范围成长用）
QUALITY_RANK = {'white': 0, 'green': 1, 'blue': 2, 'purple': 3, 'gold': 4,
                'red': 5, 'radiant': 6}


def quality_mech(q):
    return QUALITY_MECH.get(q) or {}


def apply_quality(spec, q, mul=1.0):
    """把品质机制叠到武器规格上，返回一份新的 WeaponSpec。

    mul 是品质的**伤害倍率**（gamedata.QUALITIES[q]['mul']），
    机制部分来自 QUALITY_MECH。两者合起来才是"这一级的武器"。

    近战武器（spec.melee）额外吃近战专属机制：范围/扇形随品质变大，
    这是"近战越练越猛"的主要成长感来源。
    """
    m = quality_mech(q)
    rate = float(m.get('rate', 1.0))
    # 近战专属：品质越高，斩击范围与扇形越大（每级 +8% / +6%）
    rank = QUALITY_RANK.get(q, 0)
    reach_mul = float(m.get('reach', 1.0)) * (1.0 + 0.08 * rank)
    arc_mul = float(m.get('arc', 1.0)) * (1.0 + 0.06 * rank)
    return WeaponSpec(
        key=spec.key, name=spec.name, desc=spec.desc,
        dmg=spec.dmg * float(mul),
        cd=spec.cd / max(0.05, rate),
        speed=spec.speed * float(m.get('bspd', 1.0)),
        count=spec.count + (0 if spec.melee else int(m.get('extra', 0))),
        spread=spec.spread + (0.0 if spec.melee else (4.0 if m.get('extra') else 0.0)),
        cost=spec.cost, bullet=spec.bullet, bsize=spec.bsize,
        pierce=spec.pierce + int(m.get('pierce', 0)),
        aoe=spec.aoe, life=spec.life, shake=spec.shake, sound=spec.sound,
        kick=spec.kick, color=spec.color, price=spec.price,
        melee=spec.melee,
        reach=spec.reach * reach_mul,
        arc=spec.arc * arc_mul,
        sprite=spec.sprite, tier=spec.tier, vfx=spec.vfx,
    )


def mech_summary(q):
    """给 UI 用的一句话机制说明（图鉴 / 强化预览）。"""
    m = quality_mech(q)
    if not m:
        return '基准性能'
    out = []
    if m.get('rate'):
        out.append('射速 +%d%%' % int(round((m['rate'] - 1) * 100)))
    if m.get('bspd'):
        out.append('弹速 +%d%%' % int(round((m['bspd'] - 1) * 100)))
    if m.get('extra'):
        out.append('弹丸 +%d' % int(m['extra']))
    if m.get('pierce'):
        out.append('穿透 +%d' % int(m['pierce']))
    if m.get('burst'):
        out.append('击杀迸射')
    if m.get('split'):
        out.append('命中分裂')
    if m.get('homing'):
        out.append('追猎弹道')
    if m.get('melee_double'):
        out.append('近战 %d%% 连斩' % int(round(m['melee_double'] * 100)))
    return ' · '.join(out)


# ================================================================ 开火
def _mech_bonus(game):
    """本局天赋带来的额外机制（贯穿）。只对玩家生效。"""
    extra = {}
    try:
        st = getattr(game, 'run_stats', None) or {}
        extra['pierce'] = int(st.get('pierce', 0) or 0)
    except Exception:
        pass
    return extra


def fire(game, spec, x, y, ang, friendly=True, dmg_mul=1.0):
    """按武器规格生成一组子弹，返回实际生成的子弹数。

    近战武器不走这里（见 `melee_hit`），由 player 调用。
    """
    n = max(1, int(spec.count))
    spread = math.radians(spec.spread)
    mb = _mech_bonus(game) if friendly else {}
    pierce_extra = int(mb.get('pierce', 0)) + (
        int(getattr(game, 'char_pierce_bonus', 0) or 0) if friendly else 0)
    if friendly and getattr(game, 'player', None) is not None:
        from . import gamedata as GD
        _pl = game.player
        if _pl.wq(game) == 'purple' and _pl.wlevel(game) >= GD.max_level('purple'):
            pierce_extra += 1
    mech = spec_mech(spec) if friendly else {}
    made = 0
    for i in range(n):
        if n == 1:
            a = (ang + game.rng.uniform(-spread * 0.5, spread * 0.5)
                 if spread > 0 and getattr(game, 'rng', None) is not None else ang)
        else:
            t = (i / (n - 1)) - 0.5
            a = ang + t * spread
        b = Bullet(
            x=x, y=y, ang=a, speed=spec.speed,
            dmg=spec.dmg * dmg_mul,
            friendly=friendly,
            img=spec.bullet, size=spec.bsize,
            radius=max(3.0, spec.bsize * 0.34),
            pierce=int(spec.pierce) + pierce_extra, aoe=spec.aoe, life=spec.life,
            color=spec.color, hit_shake=spec.shake,
        )
        # 机制：击杀迸射 / 命中分裂 / 追猎（挂到子弹上，命中/击杀时结算）
        if mech:
            b.mech = dict(mech)
        b.vfx = spec.vfx
        game.bullets.append(b)
        made += 1
    return made


def spec_mech(spec):
    """从 WeaponSpec 反查它属于哪一级品质机制（用于给子弹挂标记）。

    因为 apply_quality 产生的是普通 WeaponSpec，机制信息用"特征比对"反推：
    逐级比较 count/pierce 的增量，取**满足的最高级**机制。
    """
    base = WEAPONS.get(spec.key)
    if base is None:
        return {}
    mech = {}
    dc = int(spec.count) - int(base.count)
    dp = int(spec.pierce) - int(base.pierce)
    for q in ('white', 'green', 'blue', 'purple', 'gold', 'red', 'radiant'):
        mm = quality_mech(q)
        # 该级要求的机制门槛：extra 弹丸数 / pierce 穿透数
        need_e = int(mm.get('extra', 0))
        need_p = int(mm.get('pierce', 0))
        if dc >= need_e and dp >= need_p:
            mech = mm
    return mech


def melee_swing(game, spec, x, y, ang, dmg_mul=1.0):
    """近战挥砍：对身前扇形内所有敌人造成伤害。返回命中数。

    扇形判定用"距离 <= reach + 敌人半径"且"夹角 <= arc/2"。
    近战不产生子弹（除高等级"剑气"外），所以手感更"重"。
    """
    half = math.radians(max(10.0, spec.arc) * 0.5)
    reach = max(82.0, spec.reach)
    dmg = spec.dmg * float(dmg_mul)
    hits = 0
    for e in list(game.enemies):
        if not e.alive:
            continue
        d = math.hypot(e.x - x, e.y - y)
        if d > reach + e.radius:
            continue
        a = math.atan2(e.y - y, e.x - x)
        da = abs((a - ang + math.pi) % math.tau - math.pi)
        if da <= half:
            e.take_damage(dmg, game, x, y)
            weapon_impact(game, e, spec.vfx, dmg, x, y)
            # 近战自带击退（比子弹更明显）
            try:
                e.kx += math.cos(a) * 120.0
                e.ky += math.sin(a) * 120.0
            except Exception:
                pass
            hits += 1
    # The same blade arc also breaks room props and parries hostile shots.
    for p in list(game.props):
        if not p.alive:
            continue
        dx, dy = p.x - x, p.y - y
        if math.hypot(dx, dy) <= reach + p.radius and \
           abs((math.atan2(dy, dx) - ang + math.pi) % math.tau - math.pi) <= half:
            p.take_damage(dmg, game, x, y)
            hits += 1
    for b in list(game.bullets):
        if not b.alive or b.friendly:
            continue
        dx, dy = b.x - x, b.y - y
        if math.hypot(dx, dy) <= reach + b.radius and \
           abs((math.atan2(dy, dx) - ang + math.pi) % math.tau - math.pi) <= half:
            b.alive = False
            game.fx.sparks(b.x, b.y, spec.color, n=5, ang=ang)
            hits += 1
    # 特效：一道扇形挥砍的弧
    game.fx.arc_if_any(x, y, ang, reach, spec.arc, spec.color)
    return hits
