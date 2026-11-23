/* eslint-disable */
/* =======================================================================
 * 陆面过程模拟 · 数据层（自动生成，请勿手改）
 *
 *   由 tools/gen_data_js.py 从 src/sk/{gamedata,chapter,codex}.py 导出。
 *   改数据请改 Python 侧，然后重跑：
 *       python tools/gen_data_js.py
 *
 *   这样 Python 版与网页版共用同一份数据源，不会漂移。
 * ======================================================================= */
(function () {
    'use strict';

    var D = {};
    /* ---- gamedata.py ---- */
    var CURRENCY = {
      "coin": [
        "金币",
        "common",
        "随处可见的通用货币，用来买角色和强化"
      ],
      "diamond": [
        "钻石",
        "rare",
        "稀有货币，只在深层与首领身上出现"
      ]
    };

    D.CURRENCY = CURRENCY;

    var MATERIALS = {
      "scrap": [
        "废铁",
        1,
        "污染物里捡到的金属碎片，最基础的强化料"
      ],
      "fiber": [
        "纤维束",
        1,
        "韧性极佳的合成纤维，常见于低级容器"
      ],
      "circuit": [
        "电路板",
        2,
        "还能用的控制核心，精英怪身上常有"
      ],
      "crystal": [
        "污染结晶",
        2,
        "凝固的污染能量，触碰有轻微刺痛"
      ],
      "alloy": [
        "合金锭",
        3,
        "高强度合金，只有首领级才掉落"
      ],
      "core": [
        "协议核心",
        3,
        "旧世界的智能核心，武器进化的关键"
      ],
      "prism": [
        "棱镜晶核",
        4,
        "折射污染的奇异结晶，璀璨级强化的必需品"
      ],
      "relic": [
        "遗物碎片",
        4,
        "不明文明的残片，据说能拼出什么东西"
      ]
    };

    D.MATERIALS = MATERIALS;

    var MAT_ORDER = [
      "scrap",
      "fiber",
      "circuit",
      "crystal",
      "alloy",
      "core",
      "prism",
      "relic"
    ];

    D.MAT_ORDER = MAT_ORDER;

    var QUALITIES = {
      "white": {
        "name": "普通",
        "color": [
          222,
          222,
          230
        ],
        "mul": 1.0,
        "star": 1,
        "max_lv": 3,
        "up": [
          260,
          480,
          760
        ],
        "mats": {
          "scrap": [
            2,
            4,
            6
          ]
        },
        "perk": "满级：射速 +8%"
      },
      "green": {
        "name": "精良",
        "color": [
          110,
          220,
          120
        ],
        "mul": 1.0,
        "star": 2,
        "max_lv": 4,
        "up": [
          500,
          900,
          1400,
          2000
        ],
        "mats": {
          "scrap": [
            3,
            5,
            8,
            12
          ],
          "fiber": [
            1,
            2,
            4,
            6
          ]
        },
        "perk": "满级：暴击率 +6%"
      },
      "blue": {
        "name": "稀有",
        "color": [
          110,
          170,
          250
        ],
        "mul": 1.0,
        "star": 3,
        "max_lv": 5,
        "up": [
          900,
          1500,
          2200,
          3100,
          4200
        ],
        "mats": {
          "scrap": [
            4,
            7,
            10,
            14,
            18
          ],
          "circuit": [
            1,
            2,
            3,
            5,
            7
          ]
        },
        "perk": "满级：弹速 +15%"
      },
      "purple": {
        "name": "史诗",
        "color": [
          186,
          120,
          250
        ],
        "mul": 1.0,
        "star": 4,
        "max_lv": 6,
        "up": [
          1600,
          2500,
          3600,
          4900,
          6500,
          8400
        ],
        "mats": {
          "circuit": [
            3,
            5,
            8,
            11,
            15,
            20
          ],
          "crystal": [
            2,
            3,
            5,
            8,
            11,
            15
          ]
        },
        "perk": "满级：附带 1 次穿透"
      },
      "gold": {
        "name": "传说",
        "color": [
          255,
          206,
          74
        ],
        "mul": 1.0,
        "star": 5,
        "max_lv": 7,
        "up": [
          2800,
          4200,
          5800,
          7800,
          10200,
          13000,
          16200
        ],
        "mats": {
          "crystal": [
            4,
            6,
            9,
            13,
            18,
            24,
            32
          ],
          "alloy": [
            1,
            2,
            3,
            5,
            7,
            10,
            14
          ]
        },
        "perk": "满级：伤害 +15%，弹匣感更强"
      },
      "red": {
        "name": "赤红",
        "color": [
          240,
          80,
          84
        ],
        "mul": 1.0,
        "star": 6,
        "max_lv": 8,
        "up": [
          4500,
          6500,
          8800,
          11500,
          14600,
          18200,
          22400,
          27500
        ],
        "mats": {
          "alloy": [
            3,
            5,
            8,
            12,
            17,
            23,
            30,
            40
          ],
          "core": [
            1,
            2,
            3,
            5,
            7,
            10,
            14,
            19
          ]
        },
        "perk": "满级：击杀回能 +30%"
      },
      "radiant": {
        "name": "璀璨",
        "color": [
          120,
          255,
          226
        ],
        "mul": 1.0,
        "star": 7,
        "max_lv": 9,
        "up": [
          7000,
          10000,
          13500,
          17500,
          22000,
          27500,
          34000,
          41500,
          50000
        ],
        "mats": {
          "core": [
            2,
            4,
            6,
            9,
            13,
            18,
            24,
            31,
            40
          ],
          "prism": [
            1,
            2,
            3,
            5,
            7,
            10,
            13,
            17,
            22
          ]
        },
        "perk": "满级：全属性提升，附带追猎弹幕"
      }
    };

    D.QUALITIES = QUALITIES;

    var QUALITY_ORDER = [
      "white",
      "green",
      "blue",
      "purple",
      "gold",
      "red",
      "radiant"
    ];

    D.QUALITY_ORDER = QUALITY_ORDER;

    var QUALITY_MECH_DESC = {
      "white": "基准：无附加机制",
      "green": "射速 +5%，弹速 +8%",
      "blue": "弹丸 +1（散射/连发），射速 +10%，弹速 +15%",
      "purple": "穿透 +1，射速 +15%，弹速 +22%，近战 30% 额外挥砍一次",
      "gold": "击杀迸射：击杀时向四周溅射弹片",
      "red": "命中分裂：命中后在敌人间弹跳",
      "radiant": "追猎弹道：子弹自动转向敌人 + 全属性大幅提升"
    };

    D.QUALITY_MECH_DESC = QUALITY_MECH_DESC;

    var CHARACTERS = {
      "scout": {
        "key": "scout",
        "name": "测绘员",
        "desc": "初始角色。漂泊在地表的记录者，靠一把旧手枪活到今天。",
        "unlock": null,
        "starter": "pistol",
        "hp": 12,
        "spd": 168.0,
        "energy": 200.0,
        "perk": "无特殊能力"
      },
      "engineer": {
        "key": "engineer",
        "name": "工程师",
        "desc": "背着自制工具的修理工，擅长把废料变成武器。",
        "unlock": [
          "coin",
          600,
          {
            "scrap": 6
          }
        ],
        "starter": "smg",
        "hp": 12,
        "spd": 164.0,
        "energy": 220.0,
        "perk": "能量上限 +10%"
      },
      "ranger": {
        "key": "ranger",
        "name": "游猎者",
        "desc": "在污染区独自狩猎的枪手，枪法快而准。",
        "unlock": [
          "coin",
          1200,
          {
            "circuit": 5
          }
        ],
        "starter": "shotgun",
        "hp": 11,
        "spd": 178.0,
        "energy": 200.0,
        "perk": "移动速度 +6%"
      },
      "medic": {
        "key": "medic",
        "name": "战地医师",
        "desc": "在废墟间救人的医师，比谁都清楚怎么活下去。",
        "unlock": [
          "coin",
          1800,
          {
            "crystal": 5
          }
        ],
        "starter": "laser",
        "hp": 15,
        "spd": 162.0,
        "energy": 200.0,
        "perk": "生命上限 +3"
      },
      "ghost": {
        "key": "ghost",
        "name": "潜行者",
        "desc": "没人见过真面目。传说他能穿过污染而不被侵蚀。",
        "unlock": [
          "diamond",
          45,
          {
            "crystal": 3
          }
        ],
        "starter": "rocket",
        "hp": 11,
        "spd": 186.0,
        "energy": 240.0,
        "perk": "冲刺冷却 -25%"
      },
      "prime": {
        "key": "prime",
        "name": "协议行者",
        "desc": "用遗物碎片拼合出的存在。据说是旧世界的最后协议。",
        "unlock": [
          "craft",
          {
            "relic": 2,
            "core": 4,
            "prism": 2
          },
          1000
        ],
        "starter": "cannon",
        "hp": 14,
        "spd": 172.0,
        "energy": 260.0,
        "perk": "全属性均衡，初始武器更强"
      },
      "archivist": {
        "key": "archivist",
        "name": "档案员",
        "desc": "追索散落在禁区的旧物，以记录拼回失落的世界。",
        "unlock": [
          "collect",
          3
        ],
        "starter": "quartz_rifle",
        "hp": 10,
        "spd": 176.0,
        "energy": 260.0,
        "perk": "高能量上限，擅长远程调查"
      },
      "seedkeeper": {
        "key": "seedkeeper",
        "name": "守种人",
        "desc": "携带最后的种子，在废墟中保护微弱的生机。",
        "unlock": [
          "collect",
          7
        ],
        "starter": "tidal_spear",
        "hp": 17,
        "spd": 156.0,
        "energy": 230.0,
        "perk": "高生命上限，擅长近距离守护"
      }
    };

    D.CHARACTERS = CHARACTERS;

    var CHAR_ORDER = [
      "scout",
      "engineer",
      "ranger",
      "medic",
      "ghost",
      "prime",
      "archivist",
      "seedkeeper"
    ];

    D.CHAR_ORDER = CHAR_ORDER;

    var SKILLS = {
      "power": [
        "火力强化",
        "所有武器伤害 +4%/级",
        6
      ],
      "haste": [
        "迅捷",
        "移动速度 +3%/级",
        6
      ],
      "vital": [
        "强健",
        "生命上限 +1/级",
        5
      ],
      "focus": [
        "专注",
        "能量上限 +8/级",
        5
      ],
      "guard": [
        "护盾",
        "受伤后无敌时间 +8%/级",
        4
      ],
      "fortune": [
        "幸运",
        "掉落金币 +10%/级",
        5
      ]
    };

    D.SKILLS = SKILLS;

    var PASSIVES = {
      "thorns": [
        "荆棘",
        "接触敌人时反弹伤害",
        4
      ],
      "regen": [
        "自愈",
        "脱离战斗后缓慢回血",
        5
      ],
      "magnet": [
        "磁力",
        "拾取范围扩大",
        4
      ],
      "pierce": [
        "穿透",
        "子弹额外穿透 +1/级",
        3
      ],
      "crit": [
        "致命",
        "暴击率 +4%/级",
        5
      ]
    };

    D.PASSIVES = PASSIVES;

    var CHESTS = {
      "coin": {
        "normal": {
          "name": "货币箱",
          "color": [
            255,
            206,
            74
          ],
          "coin": [
            14,
            28
          ],
          "dia": 0,
          "w": 30
        },
        "superb": {
          "name": "贵重货币箱",
          "color": [
            255,
            232,
            140
          ],
          "coin": [
            38,
            68
          ],
          "dia": 1,
          "w": 10
        }
      },
      "heal": {
        "normal": {
          "name": "医疗箱",
          "color": [
            226,
            62,
            74
          ],
          "heal": [
            3,
            5
          ],
          "w": 26
        },
        "superb": {
          "name": "急救箱",
          "color": [
            255,
            130,
            140
          ],
          "heal": [
            7,
            12
          ],
          "energy": 60,
          "w": 8
        }
      },
      "material": {
        "normal": {
          "name": "材料箱",
          "color": [
            120,
            220,
            180
          ],
          "mat_tier": [
            1,
            2
          ],
          "mat_n": [
            2,
            4
          ],
          "w": 22
        },
        "superb": {
          "name": "稀有材料箱",
          "color": [
            170,
            255,
            210
          ],
          "mat_tier": [
            2,
            3
          ],
          "mat_n": [
            3,
            6
          ],
          "w": 6
        }
      },
      "weapon": {
        "normal": {
          "name": "武器箱",
          "color": [
            140,
            180,
            250
          ],
          "q_max": 2,
          "w": 18
        },
        "superb": {
          "name": "极品武器箱",
          "color": [
            200,
            160,
            255
          ],
          "q_max": 3,
          "w": 4
        }
      },
      "collect": {
        "normal": {
          "name": "工艺品箱",
          "color": [
            210,
            180,
            140
          ],
          "collect": "common",
          "w": 0.8
        },
        "superb": {
          "name": "珍藏工艺品箱",
          "color": [
            255,
            230,
            190
          ],
          "collect": "superb",
          "w": 0.1
        }
      }
    };

    D.CHESTS = CHESTS;

    var CHEST_ORDER = [
      "coin",
      "heal",
      "material",
      "weapon",
      "collect"
    ];

    D.CHEST_ORDER = CHEST_ORDER;

    /* ---- weapon.py（武器表 + 顺序，供养成面板列出全部武器） ---- */
    var WEAPONS = {
      "pistol": {
        "key": "pistol",
        "name": "学徒手枪",
        "desc": "不耗能的万能开局枪",
        "dmg": 7.56,
        "cd": 0.26,
        "speed": 430,
        "count": 1,
        "spread": 2.0,
        "cost": 0.0,
        "bullet": "b_bullet",
        "bsize": 13,
        "pierce": 0,
        "aoe": 0.0,
        "life": 1.3,
        "shake": 0.7,
        "sound": "shoot",
        "kick": 0.0,
        "color": [
          255,
          214,
          120
        ],
        "price": 0,
        "melee": false,
        "reach": 46.0,
        "arc": 100.0,
        "sprite": "",
        "tier": 0,
        "vfx": "brass"
      },
      "smg": {
        "key": "smg",
        "name": "蜂鸟冲锋枪",
        "desc": "射速极快，耗能轻微",
        "dmg": 4.32,
        "cd": 0.095,
        "speed": 470,
        "count": 1,
        "spread": 7.0,
        "cost": 0.84,
        "bullet": "b_bolt",
        "bsize": 14,
        "pierce": 0,
        "aoe": 0.0,
        "life": 1.15,
        "shake": 0.7,
        "sound": "shoot",
        "kick": 0.0,
        "color": [
          120,
          232,
          240
        ],
        "price": 45,
        "melee": false,
        "reach": 46.0,
        "arc": 100.0,
        "sprite": "",
        "tier": 0,
        "vfx": "cyan"
      },
      "shotgun": {
        "key": "shotgun",
        "name": "蒸汽霰弹枪",
        "desc": "近距离一枪糊脸",
        "dmg": 4.32,
        "cd": 0.72,
        "speed": 380,
        "count": 6,
        "spread": 20.0,
        "cost": 2.1,
        "bullet": "b_bullet",
        "bsize": 12,
        "pierce": 0,
        "aoe": 0.0,
        "life": 0.62,
        "shake": 2.4,
        "sound": "shoot_heavy",
        "kick": 26.0,
        "color": [
          255,
          186,
          96
        ],
        "price": 55,
        "melee": false,
        "reach": 46.0,
        "arc": 100.0,
        "sprite": "",
        "tier": 0,
        "vfx": "blast"
      },
      "laser": {
        "key": "laser",
        "name": "幽蓝激光枪",
        "desc": "高速穿透，指哪打哪",
        "dmg": 10.8,
        "cd": 0.17,
        "speed": 940,
        "count": 1,
        "spread": 0.6,
        "cost": 1.82,
        "bullet": "b_laser",
        "bsize": 18,
        "pierce": 3,
        "aoe": 0.0,
        "life": 0.85,
        "shake": 0.6,
        "sound": "laser",
        "kick": 0.0,
        "color": [
          255,
          96,
          120
        ],
        "price": 65,
        "melee": false,
        "reach": 46.0,
        "arc": 100.0,
        "sprite": "",
        "tier": 1,
        "vfx": "laser"
      },
      "rocket": {
        "key": "rocket",
        "name": "脆脆火箭筒",
        "desc": "大范围爆炸重炮，可摧毁掩体",
        "dmg": 25.92,
        "cd": 1.05,
        "speed": 300,
        "count": 1,
        "spread": 1.5,
        "cost": 3.5,
        "bullet": "b_rocket",
        "bsize": 16,
        "pierce": 0,
        "aoe": 46.0,
        "life": 1.6,
        "shake": 3.4,
        "sound": "shoot_heavy",
        "kick": 34.0,
        "color": [
          200,
          220,
          200
        ],
        "price": 80,
        "melee": false,
        "reach": 46.0,
        "arc": 100.0,
        "sprite": "",
        "tier": 2,
        "vfx": "rocket"
      },
      "cannon": {
        "key": "cannon",
        "name": "金色传说炮",
        "desc": "三连高伤，稀有的传说武器",
        "dmg": 16.2,
        "cd": 0.34,
        "speed": 540,
        "count": 3,
        "spread": 7.0,
        "cost": 2.52,
        "bullet": "b_plasma",
        "bsize": 16,
        "pierce": 0,
        "aoe": 0.0,
        "life": 1.25,
        "shake": 1.5,
        "sound": "shoot_heavy",
        "kick": 6.0,
        "color": [
          255,
          226,
          96
        ],
        "price": 110,
        "melee": false,
        "reach": 46.0,
        "arc": 100.0,
        "sprite": "",
        "tier": 2,
        "vfx": "nova"
      },
      "crossbow": {
        "key": "crossbow",
        "name": "钉刺弩",
        "desc": "单发高伤，弹道笔直且穿透 1 个敌人",
        "dmg": 19.44,
        "cd": 0.58,
        "speed": 620,
        "count": 1,
        "spread": 1.0,
        "cost": 1.12,
        "bullet": "b_bolt",
        "bsize": 18,
        "pierce": 1,
        "aoe": 0.0,
        "life": 1.4,
        "shake": 1.4,
        "sound": "shoot",
        "kick": 14.0,
        "color": [
          214,
          232,
          160
        ],
        "price": 70,
        "melee": false,
        "reach": 46.0,
        "arc": 100.0,
        "sprite": "",
        "tier": 1,
        "vfx": "arrow"
      },
      "flamer": {
        "key": "flamer",
        "name": "霰流喷射器",
        "desc": "近程高速散射，贴脸输出极高但射程短",
        "dmg": 3.24,
        "cd": 0.075,
        "speed": 300,
        "count": 1,
        "spread": 16.0,
        "cost": 0.39,
        "bullet": "b_hex",
        "bsize": 11,
        "pierce": 0,
        "aoe": 0.0,
        "life": 0.42,
        "shake": 0.5,
        "sound": "shoot",
        "kick": 0.0,
        "color": [
          255,
          140,
          70
        ],
        "price": 62,
        "melee": false,
        "reach": 46.0,
        "arc": 100.0,
        "sprite": "",
        "tier": 1,
        "vfx": "flame"
      },
      "railgun": {
        "key": "railgun",
        "name": "磁轨狙击",
        "desc": "蓄力一击，穿透整条直线，耗能高",
        "dmg": 34.56,
        "cd": 1.35,
        "speed": 1250,
        "count": 1,
        "spread": 0.0,
        "cost": 4.55,
        "bullet": "b_laser",
        "bsize": 20,
        "pierce": 6,
        "aoe": 0.0,
        "life": 1.05,
        "shake": 3.8,
        "sound": "laser",
        "kick": 40.0,
        "color": [
          150,
          220,
          255
        ],
        "price": 120,
        "melee": false,
        "reach": 46.0,
        "arc": 100.0,
        "sprite": "",
        "tier": 2,
        "vfx": "rail"
      },
      "blade": {
        "key": "blade",
        "name": "废铁砍刀",
        "desc": "近战武器。身前扇形横扫，不耗能，伤害集中",
        "dmg": 17.28,
        "cd": 0.42,
        "speed": 0,
        "count": 1,
        "spread": 0.0,
        "cost": 0.0,
        "bullet": "b_bullet",
        "bsize": 14,
        "pierce": 0,
        "aoe": 0.0,
        "life": 0.0,
        "shake": 1.2,
        "sound": "shoot_heavy",
        "kick": 0.0,
        "color": [
          220,
          226,
          232
        ],
        "price": 85,
        "melee": true,
        "reach": 82.0,
        "arc": 100.0,
        "sprite": "",
        "tier": 1,
        "vfx": "rust"
      },
      "plasma_blade": {
        "key": "plasma_blade",
        "name": "等离子长刃",
        "desc": "近战武器。范围更大的等离子斩，附带击退",
        "dmg": 28.08,
        "cd": 0.62,
        "speed": 0,
        "count": 1,
        "spread": 0.0,
        "cost": 0.0,
        "bullet": "b_plasma",
        "bsize": 16,
        "pierce": 2,
        "aoe": 0.0,
        "life": 0.0,
        "shake": 2.2,
        "sound": "laser",
        "kick": 0.0,
        "color": [
          180,
          240,
          255
        ],
        "price": 130,
        "melee": true,
        "reach": 82.0,
        "arc": 128.0,
        "sprite": "",
        "tier": 2,
        "vfx": "plasma"
      },
      "pulse_pistol": {
        "key": "pulse_pistol",
        "name": "脉冲手枪",
        "desc": "三色脉冲，弹道稳定",
        "dmg": 9.72,
        "cd": 0.32,
        "speed": 540,
        "count": 1,
        "spread": 0,
        "cost": 0.7,
        "bullet": "b_plasma",
        "bsize": 15,
        "pierce": 0,
        "aoe": 0,
        "life": 1.35,
        "shake": 1.0214285714285714,
        "sound": "shoot",
        "kick": 6.3,
        "color": [
          90,
          245,
          255
        ],
        "price": 65,
        "melee": false,
        "reach": 0,
        "arc": 0,
        "sprite": "",
        "tier": 0,
        "vfx": "pulse"
      },
      "arc_smg": {
        "key": "arc_smg",
        "name": "电弧蜂群",
        "desc": "高速电弧短点射",
        "dmg": 5.4,
        "cd": 0.11,
        "speed": 550,
        "count": 2,
        "spread": 10,
        "cost": 1.26,
        "bullet": "b_hex",
        "bsize": 15,
        "pierce": 0,
        "aoe": 0,
        "life": 1.35,
        "shake": 0.8785714285714286,
        "sound": "shoot",
        "kick": 3.5,
        "color": [
          132,
          204,
          255
        ],
        "price": 90,
        "melee": false,
        "reach": 0,
        "arc": 0,
        "sprite": "",
        "tier": 1,
        "vfx": "arc"
      },
      "crystal_shotgun": {
        "key": "crystal_shotgun",
        "name": "棱晶散射器",
        "desc": "晶片广角散射",
        "dmg": 6.48,
        "cd": 0.86,
        "speed": 420,
        "count": 7,
        "spread": 27,
        "cost": 2.45,
        "bullet": "b_bolt",
        "bsize": 15,
        "pierce": 0,
        "aoe": 0,
        "life": 1.35,
        "shake": 0.9142857142857143,
        "sound": "shoot",
        "kick": 4.199999999999999,
        "color": [
          168,
          118,
          255
        ],
        "price": 105,
        "melee": false,
        "reach": 0,
        "arc": 0,
        "sprite": "",
        "tier": 1,
        "vfx": "shard"
      },
      "ion_carbine": {
        "key": "ion_carbine",
        "name": "离子卡宾",
        "desc": "轻量穿透离子束",
        "dmg": 12.96,
        "cd": 0.29,
        "speed": 720,
        "count": 1,
        "spread": 1,
        "cost": 1.4,
        "bullet": "b_laser",
        "bsize": 15,
        "pierce": 1,
        "aoe": 0,
        "life": 1.35,
        "shake": 1.1285714285714286,
        "sound": "laser",
        "kick": 8.399999999999999,
        "color": [
          105,
          238,
          226
        ],
        "price": 110,
        "melee": false,
        "reach": 0,
        "arc": 0,
        "sprite": "",
        "tier": 1,
        "vfx": "ion"
      },
      "burst_rifle": {
        "key": "burst_rifle",
        "name": "破晓三连",
        "desc": "三发短促连击",
        "dmg": 7.56,
        "cd": 0.39,
        "speed": 660,
        "count": 3,
        "spread": 4,
        "cost": 1.54,
        "bullet": "b_bullet",
        "bsize": 15,
        "pierce": 0,
        "aoe": 0,
        "life": 1.35,
        "shake": 0.95,
        "sound": "shoot",
        "kick": 4.8999999999999995,
        "color": [
          255,
          188,
          105
        ],
        "price": 100,
        "melee": false,
        "reach": 0,
        "arc": 0,
        "sprite": "",
        "tier": 1,
        "vfx": "burst"
      },
      "needle_rifle": {
        "key": "needle_rifle",
        "name": "毒针步枪",
        "desc": "高精度细针",
        "dmg": 14.04,
        "cd": 0.42,
        "speed": 760,
        "count": 1,
        "spread": 0,
        "cost": 1.05,
        "bullet": "b_bolt",
        "bsize": 15,
        "pierce": 2,
        "aoe": 0,
        "life": 1.35,
        "shake": 1.1642857142857141,
        "sound": "shoot",
        "kick": 9.1,
        "color": [
          148,
          232,
          115
        ],
        "price": 100,
        "melee": false,
        "reach": 0,
        "arc": 0,
        "sprite": "",
        "tier": 1,
        "vfx": "needle"
      },
      "frost_pistol": {
        "key": "frost_pistol",
        "name": "霜凝短铳",
        "desc": "冷光速射",
        "dmg": 8.64,
        "cd": 0.21,
        "speed": 480,
        "count": 1,
        "spread": 3,
        "cost": 1.05,
        "bullet": "b_hex",
        "bsize": 15,
        "pierce": 0,
        "aoe": 0,
        "life": 1.35,
        "shake": 0.9857142857142857,
        "sound": "shoot",
        "kick": 5.6,
        "color": [
          140,
          217,
          255
        ],
        "price": 95,
        "melee": false,
        "reach": 0,
        "arc": 0,
        "sprite": "",
        "tier": 1,
        "vfx": "frost"
      },
      "corrosion_sprayer": {
        "key": "corrosion_sprayer",
        "name": "腐蚀喷射器",
        "desc": "短程锥形喷射",
        "dmg": 4.32,
        "cd": 0.13,
        "speed": 330,
        "count": 3,
        "spread": 22,
        "cost": 0.84,
        "bullet": "b_plasma",
        "bsize": 15,
        "pierce": 0,
        "aoe": 0,
        "life": 1.35,
        "shake": 0.8428571428571427,
        "sound": "shoot",
        "kick": 2.8,
        "color": [
          160,
          240,
          96
        ],
        "price": 105,
        "melee": false,
        "reach": 0,
        "arc": 0,
        "sprite": "",
        "tier": 1,
        "vfx": "acid"
      },
      "coil_cannon": {
        "key": "coil_cannon",
        "name": "线圈裂变炮",
        "desc": "高压重弹，带爆炸",
        "dmg": 27.0,
        "cd": 1.1,
        "speed": 520,
        "count": 1,
        "spread": 0,
        "cost": 3.5,
        "bullet": "b_rocket",
        "bsize": 15,
        "pierce": 0,
        "aoe": 34,
        "life": 1.35,
        "shake": 1.592857142857143,
        "sound": "shoot_heavy",
        "kick": 17.5,
        "color": [
          255,
          103,
          171
        ],
        "price": 150,
        "melee": false,
        "reach": 0,
        "arc": 0,
        "sprite": "",
        "tier": 2,
        "vfx": "coil"
      },
      "sonic_blaster": {
        "key": "sonic_blaster",
        "name": "共振震荡炮",
        "desc": "宽扇形音浪",
        "dmg": 7.56,
        "cd": 0.7,
        "speed": 450,
        "count": 5,
        "spread": 34,
        "cost": 2.45,
        "bullet": "b_hex",
        "bsize": 15,
        "pierce": 0,
        "aoe": 0,
        "life": 1.35,
        "shake": 0.95,
        "sound": "shoot",
        "kick": 4.8999999999999995,
        "color": [
          255,
          206,
          116
        ],
        "price": 125,
        "melee": false,
        "reach": 0,
        "arc": 0,
        "sprite": "",
        "tier": 2,
        "vfx": "wave"
      },
      "prism_laser": {
        "key": "prism_laser",
        "name": "虹棱长枪",
        "desc": "双束穿透激光",
        "dmg": 16.2,
        "cd": 0.55,
        "speed": 960,
        "count": 2,
        "spread": 2,
        "cost": 2.94,
        "bullet": "b_laser",
        "bsize": 15,
        "pierce": 3,
        "aoe": 0,
        "life": 1.35,
        "shake": 1.2357142857142858,
        "sound": "laser",
        "kick": 10.5,
        "color": [
          220,
          132,
          255
        ],
        "price": 155,
        "melee": false,
        "reach": 0,
        "arc": 0,
        "sprite": "",
        "tier": 2,
        "vfx": "prism"
      },
      "gravity_launcher": {
        "key": "gravity_launcher",
        "name": "引力井",
        "desc": "缓慢重弹，命中爆裂",
        "dmg": 29.16,
        "cd": 1.32,
        "speed": 320,
        "count": 1,
        "spread": 0,
        "cost": 4.06,
        "bullet": "b_rocket",
        "bsize": 15,
        "pierce": 0,
        "aoe": 58,
        "life": 1.35,
        "shake": 1.6642857142857141,
        "sound": "shoot_heavy",
        "kick": 18.9,
        "color": [
          148,
          115,
          245
        ],
        "price": 165,
        "melee": false,
        "reach": 0,
        "arc": 0,
        "sprite": "",
        "tier": 2,
        "vfx": "gravity"
      },
      "ember_mortar": {
        "key": "ember_mortar",
        "name": "余烬迫击",
        "desc": "燃烧核心范围打击",
        "dmg": 23.76,
        "cd": 1.0,
        "speed": 350,
        "count": 2,
        "spread": 6,
        "cost": 3.5,
        "bullet": "b_rocket",
        "bsize": 15,
        "pierce": 0,
        "aoe": 45,
        "life": 1.35,
        "shake": 1.4857142857142858,
        "sound": "shoot_heavy",
        "kick": 15.399999999999999,
        "color": [
          255,
          124,
          75
        ],
        "price": 155,
        "melee": false,
        "reach": 0,
        "arc": 0,
        "sprite": "",
        "tier": 2,
        "vfx": "ember"
      },
      "volt_crossbow": {
        "key": "volt_crossbow",
        "name": "雷鸣连弩",
        "desc": "电磁连弩",
        "dmg": 17.28,
        "cd": 0.48,
        "speed": 690,
        "count": 2,
        "spread": 5,
        "cost": 1.89,
        "bullet": "b_bolt",
        "bsize": 15,
        "pierce": 1,
        "aoe": 0,
        "life": 1.35,
        "shake": 1.2714285714285714,
        "sound": "shoot",
        "kick": 11.2,
        "color": [
          115,
          242,
          248
        ],
        "price": 135,
        "melee": false,
        "reach": 0,
        "arc": 0,
        "sprite": "",
        "tier": 2,
        "vfx": "volt"
      },
      "scatter_bow": {
        "key": "scatter_bow",
        "name": "月影星弓",
        "desc": "三箭抛射",
        "dmg": 10.8,
        "cd": 0.62,
        "speed": 620,
        "count": 3,
        "spread": 13,
        "cost": 1.26,
        "bullet": "b_bolt",
        "bsize": 15,
        "pierce": 1,
        "aoe": 0,
        "life": 1.35,
        "shake": 1.0571428571428572,
        "sound": "shoot",
        "kick": 7.0,
        "color": [
          198,
          180,
          255
        ],
        "price": 120,
        "melee": false,
        "reach": 0,
        "arc": 0,
        "sprite": "",
        "tier": 1,
        "vfx": "moon"
      },
      "void_revolver": {
        "key": "void_revolver",
        "name": "虚空左轮",
        "desc": "高伤缓射穿透弹",
        "dmg": 28.08,
        "cd": 0.9,
        "speed": 850,
        "count": 1,
        "spread": 0,
        "cost": 2.1,
        "bullet": "b_hex",
        "bsize": 15,
        "pierce": 3,
        "aoe": 0,
        "life": 1.35,
        "shake": 1.6285714285714286,
        "sound": "shoot_heavy",
        "kick": 18.2,
        "color": [
          219,
          94,
          255
        ],
        "price": 170,
        "melee": false,
        "reach": 0,
        "arc": 0,
        "sprite": "",
        "tier": 2,
        "vfx": "void"
      },
      "plasma_axe": {
        "key": "plasma_axe",
        "name": "等离子战斧",
        "desc": "重型弧形劈砍",
        "dmg": 31.32,
        "cd": 0.72,
        "speed": 0,
        "count": 1,
        "spread": 0,
        "cost": 0,
        "bullet": "b_plasma",
        "bsize": 15,
        "pierce": 0,
        "aoe": 0,
        "life": 0,
        "shake": 1.7357142857142858,
        "sound": "shoot_heavy",
        "kick": 20.299999999999997,
        "color": [
          105,
          238,
          235
        ],
        "price": 165,
        "melee": true,
        "reach": 82.0,
        "arc": 126,
        "sprite": "",
        "tier": 2,
        "vfx": "axe"
      },
      "twin_daggers": {
        "key": "twin_daggers",
        "name": "双生影刃",
        "desc": "高速近身双斩",
        "dmg": 14.04,
        "cd": 0.23,
        "speed": 0,
        "count": 1,
        "spread": 0,
        "cost": 0,
        "bullet": "b_hex",
        "bsize": 15,
        "pierce": 0,
        "aoe": 0,
        "life": 0,
        "shake": 1.1642857142857141,
        "sound": "shoot",
        "kick": 9.1,
        "color": [
          215,
          145,
          255
        ],
        "price": 120,
        "melee": true,
        "reach": 82.0,
        "arc": 112,
        "sprite": "",
        "tier": 1,
        "vfx": "twin"
      },
      "shock_hammer": {
        "key": "shock_hammer",
        "name": "震地重锤",
        "desc": "广范围雷击挥砸",
        "dmg": 33.48,
        "cd": 1.05,
        "speed": 0,
        "count": 1,
        "spread": 0,
        "cost": 0,
        "bullet": "b_hex",
        "bsize": 15,
        "pierce": 0,
        "aoe": 0,
        "life": 0,
        "shake": 1.9857142857142858,
        "sound": "shoot_heavy",
        "kick": 25.2,
        "color": [
          255,
          210,
          98
        ],
        "price": 175,
        "melee": true,
        "reach": 82.0,
        "arc": 150,
        "sprite": "",
        "tier": 2,
        "vfx": "hammer"
      },
      "crystal_spear": {
        "key": "crystal_spear",
        "name": "晶脊长矛",
        "desc": "长射程窄角刺击",
        "dmg": 24.84,
        "cd": 0.54,
        "speed": 0,
        "count": 1,
        "spread": 0,
        "cost": 0,
        "bullet": "b_bolt",
        "bsize": 15,
        "pierce": 2,
        "aoe": 0,
        "life": 0,
        "shake": 1.5214285714285714,
        "sound": "shoot_heavy",
        "kick": 16.099999999999998,
        "color": [
          170,
          250,
          255
        ],
        "price": 155,
        "melee": true,
        "reach": 88,
        "arc": 55,
        "sprite": "",
        "tier": 2,
        "vfx": "spear"
      },
      "sunblade": {
        "key": "sunblade",
        "name": "日冕光刃",
        "desc": "高能宽角剑气",
        "dmg": 33.48,
        "cd": 0.68,
        "speed": 0,
        "count": 1,
        "spread": 0,
        "cost": 0,
        "bullet": "b_laser",
        "bsize": 15,
        "pierce": 2,
        "aoe": 0,
        "life": 0,
        "shake": 1.8071428571428572,
        "sound": "laser",
        "kick": 21.7,
        "color": [
          255,
          221,
          131
        ],
        "price": 190,
        "melee": true,
        "reach": 82.0,
        "arc": 140,
        "sprite": "",
        "tier": 2,
        "vfx": "sun"
      },
      "crust_glaive": {
        "key": "crust_glaive",
        "name": "焦土戟",
        "desc": "裂开的合金戟刃，扫出炽热碎屑",
        "dmg": 33.48,
        "cd": 0.55,
        "speed": 0,
        "count": 1,
        "spread": 0,
        "cost": 0,
        "bullet": "b_hex",
        "bsize": 15,
        "pierce": 1,
        "aoe": 0,
        "life": 0,
        "shake": 1.8071428571428572,
        "sound": "shoot_heavy",
        "kick": 21.7,
        "color": [
          255,
          151,
          83
        ],
        "price": 230,
        "melee": true,
        "reach": 82.0,
        "arc": 130,
        "sprite": "",
        "tier": 2,
        "vfx": "ember"
      },
      "sewer_harpoon": {
        "key": "sewer_harpoon",
        "name": "腐潮鱼叉",
        "desc": "长距离穿刺并释放腐蚀",
        "dmg": 30.24,
        "cd": 0.52,
        "speed": 0,
        "count": 1,
        "spread": 0,
        "cost": 0,
        "bullet": "b_bolt",
        "bsize": 15,
        "pierce": 2,
        "aoe": 0,
        "life": 0,
        "shake": 1.7,
        "sound": "shoot_heavy",
        "kick": 19.599999999999998,
        "color": [
          91,
          224,
          166
        ],
        "price": 230,
        "melee": true,
        "reach": 98,
        "arc": 48,
        "sprite": "",
        "tier": 2,
        "vfx": "acid"
      },
      "facility_saw": {
        "key": "facility_saw",
        "name": "机枢圆锯",
        "desc": "高速旋刃，贴身连斩",
        "dmg": 22.68,
        "cd": 0.25,
        "speed": 0,
        "count": 1,
        "spread": 0,
        "cost": 0,
        "bullet": "b_hex",
        "bsize": 15,
        "pierce": 0,
        "aoe": 0,
        "life": 0,
        "shake": 1.45,
        "sound": "shoot_heavy",
        "kick": 14.7,
        "color": [
          255,
          198,
          82
        ],
        "price": 240,
        "melee": true,
        "reach": 82.0,
        "arc": 116,
        "sprite": "",
        "tier": 2,
        "vfx": "coil"
      },
      "core_repeater": {
        "key": "core_repeater",
        "name": "协议连星",
        "desc": "连续放出污染光束",
        "dmg": 17.28,
        "cd": 0.16,
        "speed": 880,
        "count": 2,
        "spread": 5,
        "cost": 2.1,
        "bullet": "b_laser",
        "bsize": 15,
        "pierce": 2,
        "aoe": 0,
        "life": 1.35,
        "shake": 1.2714285714285714,
        "sound": "laser",
        "kick": 11.2,
        "color": [
          224,
          111,
          245
        ],
        "price": 245,
        "melee": false,
        "reach": 0,
        "arc": 0,
        "sprite": "",
        "tier": 2,
        "vfx": "void"
      },
      "mine_drill": {
        "key": "mine_drill",
        "name": "矿脉穿刺钻",
        "desc": "钨钢螺旋头穿过护甲",
        "dmg": 36.72,
        "cd": 0.6,
        "speed": 0,
        "count": 1,
        "spread": 0,
        "cost": 0,
        "bullet": "b_bolt",
        "bsize": 15,
        "pierce": 3,
        "aoe": 0,
        "life": 0,
        "shake": 1.9142857142857141,
        "sound": "shoot_heavy",
        "kick": 23.799999999999997,
        "color": [
          241,
          179,
          90
        ],
        "price": 235,
        "melee": true,
        "reach": 82.0,
        "arc": 62,
        "sprite": "",
        "tier": 2,
        "vfx": "rail"
      },
      "lab_cryo_staff": {
        "key": "lab_cryo_staff",
        "name": "冷库凝霜杖",
        "desc": "冻结触碰目标并向前放出冰晶",
        "dmg": 29.16,
        "cd": 0.49,
        "speed": 0,
        "count": 1,
        "spread": 0,
        "cost": 0,
        "bullet": "b_hex",
        "bsize": 15,
        "pierce": 1,
        "aoe": 0,
        "life": 0,
        "shake": 1.6642857142857141,
        "sound": "shoot_heavy",
        "kick": 18.9,
        "color": [
          144,
          230,
          255
        ],
        "price": 245,
        "melee": true,
        "reach": 82.0,
        "arc": 125,
        "sprite": "",
        "tier": 2,
        "vfx": "frost"
      },
      "gift_starbow": {
        "key": "gift_starbow",
        "name": "净土星弓",
        "desc": "收束的星光连射",
        "dmg": 18.36,
        "cd": 0.47,
        "speed": 770,
        "count": 4,
        "spread": 18,
        "cost": 2.1,
        "bullet": "b_bolt",
        "bsize": 15,
        "pierce": 2,
        "aoe": 0,
        "life": 1.35,
        "shake": 1.307142857142857,
        "sound": "shoot",
        "kick": 11.899999999999999,
        "color": [
          255,
          232,
          140
        ],
        "price": 245,
        "melee": false,
        "reach": 0,
        "arc": 0,
        "sprite": "",
        "tier": 2,
        "vfx": "sun"
      },
      "crust_ruinblade": {
        "key": "crust_ruinblade",
        "name": "毁灭断刃",
        "desc": "残骸军阀遗留的赤色断刃",
        "dmg": 41.04,
        "cd": 0.6,
        "speed": 0,
        "count": 1,
        "spread": 0,
        "cost": 0,
        "bullet": "b_plasma",
        "bsize": 15,
        "pierce": 2,
        "aoe": 0,
        "life": 0,
        "shake": 2.3428571428571425,
        "sound": "shoot_heavy",
        "kick": 32.199999999999996,
        "color": [
          255,
          68,
          83
        ],
        "price": 400,
        "melee": true,
        "reach": 82.0,
        "arc": 140,
        "sprite": "",
        "tier": 2,
        "vfx": "ember"
      },
      "sewer_abyssfang": {
        "key": "sewer_abyssfang",
        "name": "深渊双牙",
        "desc": "虫群女王的分叉毒牙",
        "dmg": 37.8,
        "cd": 0.32,
        "speed": 0,
        "count": 1,
        "spread": 0,
        "cost": 0,
        "bullet": "b_hex",
        "bsize": 15,
        "pierce": 1,
        "aoe": 0,
        "life": 0,
        "shake": 1.95,
        "sound": "shoot_heavy",
        "kick": 24.5,
        "color": [
          248,
          75,
          112
        ],
        "price": 410,
        "melee": true,
        "reach": 82.0,
        "arc": 125,
        "sprite": "",
        "tier": 2,
        "vfx": "acid"
      },
      "facility_overdrive": {
        "key": "facility_overdrive",
        "name": "超载矩阵炮",
        "desc": "机枢核心驱动的灼热重炮",
        "dmg": 36.72,
        "cd": 1.03,
        "speed": 520,
        "count": 3,
        "spread": 12,
        "cost": 4.9,
        "bullet": "b_rocket",
        "bsize": 15,
        "pierce": 1,
        "aoe": 48,
        "life": 1.35,
        "shake": 2.1285714285714286,
        "sound": "shoot_heavy",
        "kick": 28.0,
        "color": [
          250,
          75,
          88
        ],
        "price": 450,
        "melee": false,
        "reach": 0,
        "arc": 0,
        "sprite": "",
        "tier": 2,
        "vfx": "coil"
      },
      "core_nihility": {
        "key": "core_nihility",
        "name": "虚无裁断",
        "desc": "污染原点凝成的赤红判决",
        "dmg": 45.36,
        "cd": 0.64,
        "speed": 0,
        "count": 1,
        "spread": 0,
        "cost": 0,
        "bullet": "b_laser",
        "bsize": 15,
        "pierce": 3,
        "aoe": 0,
        "life": 0,
        "shake": 2.6285714285714286,
        "sound": "laser",
        "kick": 37.8,
        "color": [
          255,
          55,
          155
        ],
        "price": 500,
        "melee": true,
        "reach": 102,
        "arc": 138,
        "sprite": "",
        "tier": 2,
        "vfx": "void"
      },
      "mine_faultaxe": {
        "key": "mine_faultaxe",
        "name": "断层巨斧",
        "desc": "矿井监工的裂地重斧",
        "dmg": 45.36,
        "cd": 0.68,
        "speed": 0,
        "count": 1,
        "spread": 0,
        "cost": 0,
        "bullet": "b_hex",
        "bsize": 15,
        "pierce": 1,
        "aoe": 0,
        "life": 0,
        "shake": 2.664285714285714,
        "sound": "shoot_heavy",
        "kick": 38,
        "color": [
          255,
          88,
          84
        ],
        "price": 440,
        "melee": true,
        "reach": 82,
        "arc": 155,
        "sprite": "",
        "tier": 2,
        "vfx": "axe"
      },
      "lab_zerobeam": {
        "key": "lab_zerobeam",
        "name": "绝对零度炮",
        "desc": "冷库实验的赤红冻结射线",
        "dmg": 35.64,
        "cd": 0.74,
        "speed": 860,
        "count": 2,
        "spread": 1,
        "cost": 4.2,
        "bullet": "b_laser",
        "bsize": 15,
        "pierce": 4,
        "aoe": 0,
        "life": 1.35,
        "shake": 2.0928571428571425,
        "sound": "laser",
        "kick": 27.299999999999997,
        "color": [
          249,
          91,
          135
        ],
        "price": 460,
        "melee": false,
        "reach": 0,
        "arc": 0,
        "sprite": "",
        "tier": 2,
        "vfx": "frost"
      },
      "gift_dawnkeeper": {
        "key": "gift_dawnkeeper",
        "name": "晨曦守护剑",
        "desc": "净土守卫的最后誓言",
        "dmg": 43.2,
        "cd": 0.6,
        "speed": 0,
        "count": 1,
        "spread": 0,
        "cost": 0,
        "bullet": "b_plasma",
        "bsize": 15,
        "pierce": 2,
        "aoe": 0,
        "life": 0,
        "shake": 2.45,
        "sound": "shoot_heavy",
        "kick": 34.3,
        "color": [
          255,
          104,
          93
        ],
        "price": 475,
        "melee": true,
        "reach": 85,
        "arc": 150,
        "sprite": "",
        "tier": 2,
        "vfx": "sun"
      },
      "trench_blade": {
        "key": "trench_blade",
        "name": "堑壕直刀",
        "desc": "简洁可靠的近战直刀",
        "dmg": 19.44,
        "cd": 0.39,
        "speed": 0,
        "count": 1,
        "spread": 0,
        "cost": 0,
        "bullet": "b_bullet",
        "bsize": 15,
        "pierce": 0,
        "aoe": 0,
        "life": 0,
        "shake": 1.342857142857143,
        "sound": "shoot_heavy",
        "kick": 12.6,
        "color": [
          184,
          209,
          238
        ],
        "price": 100,
        "melee": true,
        "reach": 82.0,
        "arc": 95,
        "sprite": "",
        "tier": 1,
        "vfx": "rust"
      },
      "moss_whip": {
        "key": "moss_whip",
        "name": "苔链鞭",
        "desc": "柔性链刃覆盖宽广扇区",
        "dmg": 18.36,
        "cd": 0.34,
        "speed": 0,
        "count": 1,
        "spread": 0,
        "cost": 0,
        "bullet": "b_hex",
        "bsize": 15,
        "pierce": 0,
        "aoe": 0,
        "life": 0,
        "shake": 1.307142857142857,
        "sound": "shoot",
        "kick": 11.899999999999999,
        "color": [
          120,
          237,
          140
        ],
        "price": 118,
        "melee": true,
        "reach": 82.0,
        "arc": 168,
        "sprite": "",
        "tier": 1,
        "vfx": "acid"
      },
      "mirror_shield": {
        "key": "mirror_shield",
        "name": "镜面盾刃",
        "desc": "近身撞击时反射棱光",
        "dmg": 25.92,
        "cd": 0.61,
        "speed": 0,
        "count": 1,
        "spread": 0,
        "cost": 0,
        "bullet": "b_plasma",
        "bsize": 15,
        "pierce": 0,
        "aoe": 0,
        "life": 0,
        "shake": 1.557142857142857,
        "sound": "shoot_heavy",
        "kick": 16.799999999999997,
        "color": [
          170,
          200,
          255
        ],
        "price": 125,
        "melee": true,
        "reach": 82.0,
        "arc": 175,
        "sprite": "",
        "tier": 1,
        "vfx": "prism"
      },
      "meteor_pike": {
        "key": "meteor_pike",
        "name": "陨铁骑枪",
        "desc": "窄角远距突刺",
        "dmg": 32.4,
        "cd": 0.57,
        "speed": 0,
        "count": 1,
        "spread": 0,
        "cost": 0,
        "bullet": "b_bolt",
        "bsize": 15,
        "pierce": 2,
        "aoe": 0,
        "life": 0,
        "shake": 1.7714285714285714,
        "sound": "shoot_heavy",
        "kick": 21.0,
        "color": [
          255,
          172,
          132
        ],
        "price": 130,
        "melee": true,
        "reach": 105,
        "arc": 44,
        "sprite": "",
        "tier": 1,
        "vfx": "rail"
      },
      "scrap_saber": {
        "key": "scrap_saber",
        "name": "荒原短刀",
        "desc": "轻快宽角斩击",
        "dmg": 17.28,
        "cd": 0.38,
        "speed": 0,
        "count": 1,
        "spread": 0,
        "cost": 0,
        "bullet": "b_bullet",
        "bsize": 15,
        "pierce": 0,
        "aoe": 0,
        "life": 0,
        "shake": 1.2714285714285714,
        "sound": "shoot",
        "kick": 11.2,
        "color": [
          205,
          218,
          225
        ],
        "price": 90,
        "melee": true,
        "reach": 86,
        "arc": 112,
        "sprite": "",
        "tier": 0,
        "vfx": "rust"
      },
      "vine_sickle": {
        "key": "vine_sickle",
        "name": "蔓生镰",
        "desc": "腐蚀刃使目标持续受伤",
        "dmg": 22.68,
        "cd": 0.46,
        "speed": 0,
        "count": 1,
        "spread": 0,
        "cost": 0,
        "bullet": "b_hex",
        "bsize": 15,
        "pierce": 0,
        "aoe": 0,
        "life": 0,
        "shake": 1.45,
        "sound": "shoot_heavy",
        "kick": 14.7,
        "color": [
          132,
          237,
          150
        ],
        "price": 125,
        "melee": true,
        "reach": 94,
        "arc": 136,
        "sprite": "",
        "tier": 1,
        "vfx": "acid"
      },
      "glacier_fang": {
        "key": "glacier_fang",
        "name": "冰牙剑",
        "desc": "冰刃降低目标移动速度",
        "dmg": 28.08,
        "cd": 0.55,
        "speed": 0,
        "count": 1,
        "spread": 0,
        "cost": 0,
        "bullet": "b_laser",
        "bsize": 15,
        "pierce": 0,
        "aoe": 0,
        "life": 0,
        "shake": 1.6285714285714286,
        "sound": "laser",
        "kick": 18.2,
        "color": [
          120,
          212,
          255
        ],
        "price": 165,
        "melee": true,
        "reach": 98,
        "arc": 114,
        "sprite": "",
        "tier": 1,
        "vfx": "frost"
      },
      "thunder_axe": {
        "key": "thunder_axe",
        "name": "雷暴斧",
        "desc": "命中向附近敌人传递电弧",
        "dmg": 35.64,
        "cd": 0.74,
        "speed": 0,
        "count": 1,
        "spread": 0,
        "cost": 0,
        "bullet": "b_hex",
        "bsize": 15,
        "pierce": 0,
        "aoe": 0,
        "life": 0,
        "shake": 1.8785714285714286,
        "sound": "shoot_heavy",
        "kick": 23.099999999999998,
        "color": [
          194,
          150,
          255
        ],
        "price": 210,
        "melee": true,
        "reach": 102,
        "arc": 142,
        "sprite": "",
        "tier": 2,
        "vfx": "arc"
      },
      "solar_cleaver": {
        "key": "solar_cleaver",
        "name": "曜金巨刃",
        "desc": "炽热斩击灼烧敌人",
        "dmg": 36.72,
        "cd": 0.58,
        "speed": 0,
        "count": 1,
        "spread": 0,
        "cost": 0,
        "bullet": "b_plasma",
        "bsize": 15,
        "pierce": 0,
        "aoe": 0,
        "life": 0,
        "shake": 2.2,
        "sound": "shoot_heavy",
        "kick": 29.4,
        "color": [
          255,
          206,
          92
        ],
        "price": 270,
        "melee": true,
        "reach": 110,
        "arc": 155,
        "sprite": "",
        "tier": 2,
        "vfx": "sun"
      },
      "dust_revolver": {
        "key": "dust_revolver",
        "name": "尘暴左轮",
        "desc": "精确单发，高速金属弹",
        "dmg": 14.04,
        "cd": 0.44,
        "speed": 850,
        "count": 1,
        "spread": 0,
        "cost": 0.84,
        "bullet": "b_bullet",
        "bsize": 15,
        "pierce": 0,
        "aoe": 0,
        "life": 1.35,
        "shake": 1.1642857142857141,
        "sound": "shoot",
        "kick": 9.1,
        "color": [
          218,
          191,
          139
        ],
        "price": 95,
        "melee": false,
        "reach": 0,
        "arc": 0,
        "sprite": "",
        "tier": 0,
        "vfx": "brass"
      },
      "reed_carbine": {
        "key": "reed_carbine",
        "name": "苇叶卡宾",
        "desc": "轻量短点射",
        "dmg": 8.64,
        "cd": 0.31,
        "speed": 700,
        "count": 2,
        "spread": 4,
        "cost": 1.12,
        "bullet": "b_bolt",
        "bsize": 15,
        "pierce": 0,
        "aoe": 0,
        "life": 1.35,
        "shake": 0.9857142857142857,
        "sound": "shoot",
        "kick": 5.6,
        "color": [
          128,
          218,
          146
        ],
        "price": 110,
        "melee": false,
        "reach": 0,
        "arc": 0,
        "sprite": "",
        "tier": 1,
        "vfx": "needle"
      },
      "ash_shotgun": {
        "key": "ash_shotgun",
        "name": "灰烬霰铳",
        "desc": "宽角慢速散弹",
        "dmg": 7.56,
        "cd": 0.83,
        "speed": 260,
        "count": 7,
        "spread": 38,
        "cost": 2.03,
        "bullet": "b_bullet",
        "bsize": 15,
        "pierce": 0,
        "aoe": 0,
        "life": 1.35,
        "shake": 0.95,
        "sound": "shoot",
        "kick": 4.8999999999999995,
        "color": [
          222,
          155,
          112
        ],
        "price": 130,
        "melee": false,
        "reach": 0,
        "arc": 0,
        "sprite": "",
        "tier": 1,
        "vfx": "blast"
      },
      "tide_sprayer": {
        "key": "tide_sprayer",
        "name": "潮汐喷枪",
        "desc": "扇面水晶碎片",
        "dmg": 5.4,
        "cd": 0.48,
        "speed": 300,
        "count": 5,
        "spread": 32,
        "cost": 1.4,
        "bullet": "b_plasma",
        "bsize": 15,
        "pierce": 0,
        "aoe": 0,
        "life": 1.35,
        "shake": 0.8785714285714286,
        "sound": "shoot",
        "kick": 3.5,
        "color": [
          104,
          203,
          218
        ],
        "price": 135,
        "melee": false,
        "reach": 0,
        "arc": 0,
        "sprite": "",
        "tier": 1,
        "vfx": "shard"
      },
      "frost_repeater": {
        "key": "frost_repeater",
        "name": "霜环连发枪",
        "desc": "冰晶连射使目标减速",
        "dmg": 10.8,
        "cd": 0.24,
        "speed": 540,
        "count": 2,
        "spread": 5,
        "cost": 1.54,
        "bullet": "b_hex",
        "bsize": 15,
        "pierce": 0,
        "aoe": 0,
        "life": 1.35,
        "shake": 1.0571428571428572,
        "sound": "shoot",
        "kick": 7.0,
        "color": [
          119,
          213,
          248
        ],
        "price": 175,
        "melee": false,
        "reach": 0,
        "arc": 0,
        "sprite": "",
        "tier": 2,
        "vfx": "frost"
      },
      "echo_blaster": {
        "key": "echo_blaster",
        "name": "回声震荡器",
        "desc": "缓速音波扩散",
        "dmg": 8.64,
        "cd": 0.58,
        "speed": 340,
        "count": 4,
        "spread": 22,
        "cost": 1.75,
        "bullet": "b_hex",
        "bsize": 15,
        "pierce": 0,
        "aoe": 0,
        "life": 1.35,
        "shake": 0.9857142857142857,
        "sound": "shoot",
        "kick": 5.6,
        "color": [
          182,
          164,
          245
        ],
        "price": 185,
        "melee": false,
        "reach": 0,
        "arc": 0,
        "sprite": "",
        "tier": 2,
        "vfx": "wave"
      },
      "singularity_rifle": {
        "key": "singularity_rifle",
        "name": "奇点射线枪",
        "desc": "极慢单束激光穿透",
        "dmg": 30.24,
        "cd": 0.88,
        "speed": 115,
        "count": 1,
        "spread": 0,
        "cost": 2.8,
        "bullet": "b_laser",
        "bsize": 15,
        "pierce": 3,
        "aoe": 0,
        "life": 1.35,
        "shake": 1.7,
        "sound": "laser",
        "kick": 19.599999999999998,
        "color": [
          208,
          143,
          251
        ],
        "price": 290,
        "melee": false,
        "reach": 0,
        "arc": 0,
        "sprite": "",
        "tier": 2,
        "vfx": "gravity"
      },
      "aurora_cannon": {
        "key": "aurora_cannon",
        "name": "极光聚能炮",
        "desc": "高能单束爆裂激光",
        "dmg": 37.8,
        "cd": 1.0,
        "speed": 165,
        "count": 1,
        "spread": 0,
        "cost": 3.5,
        "bullet": "b_laser",
        "bsize": 15,
        "pierce": 3,
        "aoe": 40,
        "life": 1.35,
        "shake": 1.95,
        "sound": "laser",
        "kick": 24.5,
        "color": [
          255,
          224,
          118
        ],
        "price": 360,
        "melee": false,
        "reach": 0,
        "arc": 0,
        "sprite": "",
        "tier": 2,
        "vfx": "prism"
      },
      "starfall_bow": {
        "key": "starfall_bow",
        "name": "璀璨星落弓",
        "desc": "追猎星矢",
        "dmg": 35.64,
        "cd": 0.65,
        "speed": 650,
        "count": 1,
        "spread": 0,
        "cost": 3.01,
        "bullet": "b_bolt",
        "bsize": 15,
        "pierce": 2,
        "aoe": 0,
        "life": 1.35,
        "shake": 1.8785714285714286,
        "sound": "rad_star",
        "kick": 23.099999999999998,
        "color": [
          255,
          244,
          182
        ],
        "price": 520,
        "melee": false,
        "reach": 0,
        "arc": 0,
        "sprite": "",
        "tier": 2,
        "vfx": "rad_star"
      },
      "quartz_rifle": {
        "key": "quartz_rifle",
        "name": "石英步枪",
        "desc": "快速单发穿晶弹",
        "dmg": 17.28,
        "cd": 0.36,
        "speed": 900,
        "count": 1,
        "spread": 0,
        "cost": 1.26,
        "bullet": "b_bolt",
        "bsize": 15,
        "pierce": 1,
        "aoe": 0,
        "life": 1.35,
        "shake": 1.2714285714285714,
        "sound": "shoot",
        "kick": 11.2,
        "color": [
          184,
          215,
          246
        ],
        "price": 155,
        "melee": false,
        "reach": 0,
        "arc": 0,
        "sprite": "",
        "tier": 1,
        "vfx": "shard"
      },
      "ember_knife": {
        "key": "ember_knife",
        "name": "余火短匕",
        "desc": "短促扇形火花",
        "dmg": 21.6,
        "cd": 0.33,
        "speed": 0,
        "count": 1,
        "spread": 0,
        "cost": 0,
        "bullet": "b_bullet",
        "bsize": 15,
        "pierce": 0,
        "aoe": 0,
        "life": 0,
        "shake": 1.4142857142857141,
        "sound": "shoot_heavy",
        "kick": 14.0,
        "color": [
          252,
          145,
          99
        ],
        "price": 115,
        "melee": true,
        "reach": 88,
        "arc": 105,
        "sprite": "",
        "tier": 0,
        "vfx": "ember"
      },
      "tidal_spear": {
        "key": "tidal_spear",
        "name": "潮汐长矛",
        "desc": "远距离精准突刺",
        "dmg": 27.0,
        "cd": 0.51,
        "speed": 0,
        "count": 1,
        "spread": 0,
        "cost": 0,
        "bullet": "b_bolt",
        "bsize": 15,
        "pierce": 1,
        "aoe": 0,
        "life": 0,
        "shake": 1.592857142857143,
        "sound": "shoot_heavy",
        "kick": 17.5,
        "color": [
          110,
          216,
          226
        ],
        "price": 165,
        "melee": true,
        "reach": 112,
        "arc": 65,
        "sprite": "",
        "tier": 1,
        "vfx": "ion"
      },
      "obsidian_axe": {
        "key": "obsidian_axe",
        "name": "黑曜战斧",
        "desc": "沉重弧形劈砍",
        "dmg": 34.56,
        "cd": 0.83,
        "speed": 0,
        "count": 1,
        "spread": 0,
        "cost": 0,
        "bullet": "b_hex",
        "bsize": 15,
        "pierce": 0,
        "aoe": 0,
        "life": 0,
        "shake": 2.0214285714285714,
        "sound": "shoot_heavy",
        "kick": 25.9,
        "color": [
          163,
          126,
          222
        ],
        "price": 225,
        "melee": true,
        "reach": 103,
        "arc": 145,
        "sprite": "",
        "tier": 2,
        "vfx": "void"
      },
      "lumen_whip": {
        "key": "lumen_whip",
        "name": "流明光鞭",
        "desc": "大范围柔性光刃",
        "dmg": 28.08,
        "cd": 0.46,
        "speed": 0,
        "count": 1,
        "spread": 0,
        "cost": 0,
        "bullet": "b_laser",
        "bsize": 15,
        "pierce": 1,
        "aoe": 0,
        "life": 0,
        "shake": 1.6285714285714286,
        "sound": "laser",
        "kick": 18.2,
        "color": [
          246,
          226,
          135
        ],
        "price": 240,
        "melee": true,
        "reach": 120,
        "arc": 170,
        "sprite": "",
        "tier": 2,
        "vfx": "sun"
      },
      "pebble_popper": {
        "key": "pebble_popper",
        "name": "砂砾手铳",
        "desc": "低耗能高速单发",
        "dmg": 10.8,
        "cd": 0.37,
        "speed": 670,
        "count": 1,
        "spread": 0,
        "cost": 0.7,
        "bullet": "b_bullet",
        "bsize": 15,
        "pierce": 0,
        "aoe": 0,
        "life": 1.35,
        "shake": 1.0571428571428572,
        "sound": "shoot",
        "kick": 7.0,
        "color": [
          218,
          190,
          146
        ],
        "price": 78,
        "melee": false,
        "reach": 0,
        "arc": 0,
        "sprite": "",
        "tier": 0,
        "vfx": "v30_pebble"
      },
      "scrap_crossbow": {
        "key": "scrap_crossbow",
        "name": "锈钉短弩",
        "desc": "锈钉精准穿刺",
        "dmg": 15.12,
        "cd": 0.52,
        "speed": 750,
        "count": 1,
        "spread": 0,
        "cost": 0.84,
        "bullet": "b_bolt",
        "bsize": 15,
        "pierce": 1,
        "aoe": 0,
        "life": 1.35,
        "shake": 1.2,
        "sound": "shoot",
        "kick": 9.799999999999999,
        "color": [
          174,
          195,
          184
        ],
        "price": 90,
        "melee": false,
        "reach": 0,
        "arc": 0,
        "sprite": "",
        "tier": 0,
        "vfx": "v30_scrap"
      },
      "flare_tube": {
        "key": "flare_tube",
        "name": "信号焰管",
        "desc": "慢速燃烧散弹",
        "dmg": 7.56,
        "cd": 0.7,
        "speed": 300,
        "count": 4,
        "spread": 30,
        "cost": 1.4,
        "bullet": "b_plasma",
        "bsize": 15,
        "pierce": 0,
        "aoe": 0,
        "life": 1.35,
        "shake": 0.95,
        "sound": "shoot",
        "kick": 4.8999999999999995,
        "color": [
          246,
          163,
          117
        ],
        "price": 96,
        "melee": false,
        "reach": 0,
        "arc": 0,
        "sprite": "",
        "tier": 0,
        "vfx": "ember"
      },
      "alloy_knife": {
        "key": "alloy_knife",
        "name": "薄钢折刀",
        "desc": "快速宽角斩",
        "dmg": 18.36,
        "cd": 0.34,
        "speed": 0,
        "count": 1,
        "spread": 0,
        "cost": 0,
        "bullet": "b_bullet",
        "bsize": 15,
        "pierce": 0,
        "aoe": 0,
        "life": 0,
        "shake": 1.307142857142857,
        "sound": "shoot",
        "kick": 11.899999999999999,
        "color": [
          195,
          210,
          230
        ],
        "price": 88,
        "melee": true,
        "reach": 92,
        "arc": 118,
        "sprite": "",
        "tier": 0,
        "vfx": "v30_alloy"
      },
      "survey_spear": {
        "key": "survey_spear",
        "name": "测绘长钎",
        "desc": "远距精准突刺",
        "dmg": 20.52,
        "cd": 0.51,
        "speed": 0,
        "count": 1,
        "spread": 0,
        "cost": 0,
        "bullet": "b_bolt",
        "bsize": 15,
        "pierce": 1,
        "aoe": 0,
        "life": 0,
        "shake": 1.3785714285714286,
        "sound": "shoot_heavy",
        "kick": 13.299999999999999,
        "color": [
          177,
          212,
          221
        ],
        "price": 104,
        "melee": true,
        "reach": 112,
        "arc": 58,
        "sprite": "",
        "tier": 0,
        "vfx": "v30_survey"
      },
      "ivy_repeater": {
        "key": "ivy_repeater",
        "name": "藤脉连弩",
        "desc": "双发腐蚀藤刺",
        "dmg": 10.8,
        "cd": 0.37,
        "speed": 620,
        "count": 2,
        "spread": 7,
        "cost": 1.26,
        "bullet": "b_bolt",
        "bsize": 15,
        "pierce": 0,
        "aoe": 0,
        "life": 1.35,
        "shake": 1.0571428571428572,
        "sound": "shoot",
        "kick": 7.0,
        "color": [
          132,
          224,
          148
        ],
        "price": 142,
        "melee": false,
        "reach": 0,
        "arc": 0,
        "sprite": "",
        "tier": 1,
        "vfx": "acid"
      },
      "current_shotgun": {
        "key": "current_shotgun",
        "name": "流电霰铳",
        "desc": "五枚电荷宽角散射",
        "dmg": 8.64,
        "cd": 0.71,
        "speed": 400,
        "count": 5,
        "spread": 26,
        "cost": 1.89,
        "bullet": "b_hex",
        "bsize": 15,
        "pierce": 0,
        "aoe": 0,
        "life": 1.35,
        "shake": 0.9857142857142857,
        "sound": "shoot",
        "kick": 5.6,
        "color": [
          102,
          233,
          212
        ],
        "price": 157,
        "melee": false,
        "reach": 0,
        "arc": 0,
        "sprite": "",
        "tier": 1,
        "vfx": "arc"
      },
      "spring_carbine": {
        "key": "spring_carbine",
        "name": "弹簧卡宾",
        "desc": "稳定的三点连射",
        "dmg": 9.72,
        "cd": 0.41,
        "speed": 780,
        "count": 3,
        "spread": 5,
        "cost": 1.47,
        "bullet": "b_bullet",
        "bsize": 15,
        "pierce": 0,
        "aoe": 0,
        "life": 1.35,
        "shake": 1.0214285714285714,
        "sound": "shoot",
        "kick": 6.3,
        "color": [
          179,
          227,
          114
        ],
        "price": 149,
        "melee": false,
        "reach": 0,
        "arc": 0,
        "sprite": "",
        "tier": 1,
        "vfx": "v30_spring"
      },
      "acid_cleaver": {
        "key": "acid_cleaver",
        "name": "腐叶砍斧",
        "desc": "宽角腐蚀重斩",
        "dmg": 25.92,
        "cd": 0.65,
        "speed": 0,
        "count": 1,
        "spread": 0,
        "cost": 0,
        "bullet": "b_hex",
        "bsize": 15,
        "pierce": 0,
        "aoe": 0,
        "life": 0,
        "shake": 1.557142857142857,
        "sound": "shoot_heavy",
        "kick": 16.799999999999997,
        "color": [
          132,
          238,
          124
        ],
        "price": 164,
        "melee": true,
        "reach": 100,
        "arc": 148,
        "sprite": "",
        "tier": 1,
        "vfx": "acid"
      },
      "cloud_staff": {
        "key": "cloud_staff",
        "name": "云絮法杖",
        "desc": "三枚漂移能量球",
        "dmg": 9.72,
        "cd": 0.55,
        "speed": 350,
        "count": 3,
        "spread": 18,
        "cost": 1.61,
        "bullet": "b_plasma",
        "bsize": 15,
        "pierce": 0,
        "aoe": 0,
        "life": 1.35,
        "shake": 1.0214285714285714,
        "sound": "shoot",
        "kick": 6.3,
        "color": [
          150,
          231,
          215
        ],
        "price": 156,
        "melee": false,
        "reach": 0,
        "arc": 0,
        "sprite": "",
        "tier": 1,
        "vfx": "v30_cloud"
      },
      "frost_lance": {
        "key": "frost_lance",
        "name": "寒潮穿枪",
        "desc": "冰晶穿透并减速",
        "dmg": 25.92,
        "cd": 0.58,
        "speed": 820,
        "count": 1,
        "spread": 0,
        "cost": 1.75,
        "bullet": "b_laser",
        "bsize": 15,
        "pierce": 2,
        "aoe": 0,
        "life": 1.35,
        "shake": 1.557142857142857,
        "sound": "laser",
        "kick": 16.799999999999997,
        "color": [
          131,
          219,
          255
        ],
        "price": 205,
        "melee": false,
        "reach": 0,
        "arc": 0,
        "sprite": "",
        "tier": 2,
        "vfx": "frost"
      },
      "echo_pulse": {
        "key": "echo_pulse",
        "name": "回声脉冲器",
        "desc": "音浪三连发",
        "dmg": 11.88,
        "cd": 0.44,
        "speed": 480,
        "count": 3,
        "spread": 14,
        "cost": 1.68,
        "bullet": "b_hex",
        "bsize": 15,
        "pierce": 0,
        "aoe": 0,
        "life": 1.35,
        "shake": 1.0928571428571427,
        "sound": "shoot",
        "kick": 7.699999999999999,
        "color": [
          176,
          174,
          249
        ],
        "price": 208,
        "melee": false,
        "reach": 0,
        "arc": 0,
        "sprite": "",
        "tier": 2,
        "vfx": "v30_echo"
      },
      "arc_lantern": {
        "key": "arc_lantern",
        "name": "雷弧灯笼",
        "desc": "电球在敌群连锁",
        "dmg": 16.2,
        "cd": 0.61,
        "speed": 410,
        "count": 2,
        "spread": 8,
        "cost": 2.1,
        "bullet": "b_plasma",
        "bsize": 15,
        "pierce": 0,
        "aoe": 0,
        "life": 1.35,
        "shake": 1.2357142857142858,
        "sound": "shoot",
        "kick": 10.5,
        "color": [
          124,
          232,
          252
        ],
        "price": 220,
        "melee": false,
        "reach": 0,
        "arc": 0,
        "sprite": "",
        "tier": 2,
        "vfx": "arc"
      },
      "glass_bow": {
        "key": "glass_bow",
        "name": "琉璃长弓",
        "desc": "四片玻璃箭穿甲",
        "dmg": 12.96,
        "cd": 0.56,
        "speed": 730,
        "count": 4,
        "spread": 12,
        "cost": 1.75,
        "bullet": "b_bolt",
        "bsize": 15,
        "pierce": 1,
        "aoe": 0,
        "life": 1.35,
        "shake": 1.1285714285714286,
        "sound": "shoot",
        "kick": 8.399999999999999,
        "color": [
          181,
          216,
          254
        ],
        "price": 211,
        "melee": false,
        "reach": 0,
        "arc": 0,
        "sprite": "",
        "tier": 2,
        "vfx": "v30_glass"
      },
      "gyro_blade": {
        "key": "gyro_blade",
        "name": "陀螺环刃",
        "desc": "近身圆弧双斩",
        "dmg": 29.16,
        "cd": 0.54,
        "speed": 0,
        "count": 1,
        "spread": 0,
        "cost": 0,
        "bullet": "b_hex",
        "bsize": 15,
        "pierce": 1,
        "aoe": 0,
        "life": 0,
        "shake": 1.6642857142857141,
        "sound": "shoot_heavy",
        "kick": 18.9,
        "color": [
          128,
          205,
          255
        ],
        "price": 225,
        "melee": true,
        "reach": 107,
        "arc": 172,
        "sprite": "",
        "tier": 2,
        "vfx": "v30_gyro"
      },
      "null_carbine": {
        "key": "null_carbine",
        "name": "零域卡宾",
        "desc": "高速精确穿透弹",
        "dmg": 31.32,
        "cd": 0.55,
        "speed": 900,
        "count": 1,
        "spread": 0,
        "cost": 2.24,
        "bullet": "b_hex",
        "bsize": 15,
        "pierce": 3,
        "aoe": 0,
        "life": 1.35,
        "shake": 1.7357142857142858,
        "sound": "shoot_heavy",
        "kick": 20.299999999999997,
        "color": [
          202,
          142,
          250
        ],
        "price": 292,
        "melee": false,
        "reach": 0,
        "arc": 0,
        "sprite": "",
        "tier": 2,
        "vfx": "void"
      },
      "prism_fan": {
        "key": "prism_fan",
        "name": "棱面散射仪",
        "desc": "七束棱光交叉",
        "dmg": 11.88,
        "cd": 0.72,
        "speed": 590,
        "count": 7,
        "spread": 32,
        "cost": 2.45,
        "bullet": "b_laser",
        "bsize": 15,
        "pierce": 1,
        "aoe": 0,
        "life": 1.35,
        "shake": 1.0928571428571427,
        "sound": "laser",
        "kick": 7.699999999999999,
        "color": [
          217,
          164,
          255
        ],
        "price": 305,
        "melee": false,
        "reach": 0,
        "arc": 0,
        "sprite": "",
        "tier": 2,
        "vfx": "prism"
      },
      "quake_hammer": {
        "key": "quake_hammer",
        "name": "震域重锤",
        "desc": "大范围震荡重击",
        "dmg": 39.96,
        "cd": 0.9,
        "speed": 0,
        "count": 1,
        "spread": 0,
        "cost": 0,
        "bullet": "b_hex",
        "bsize": 15,
        "pierce": 0,
        "aoe": 0,
        "life": 0,
        "shake": 2.0214285714285714,
        "sound": "shoot_heavy",
        "kick": 25.9,
        "color": [
          203,
          144,
          236
        ],
        "price": 318,
        "melee": true,
        "reach": 108,
        "arc": 164,
        "sprite": "",
        "tier": 2,
        "vfx": "v30_quake"
      },
      "phase_needle": {
        "key": "phase_needle",
        "name": "相位毒针",
        "desc": "高速连穿弹",
        "dmg": 24.84,
        "cd": 0.43,
        "speed": 970,
        "count": 1,
        "spread": 0,
        "cost": 2.31,
        "bullet": "b_bolt",
        "bsize": 15,
        "pierce": 4,
        "aoe": 0,
        "life": 1.35,
        "shake": 1.5214285714285714,
        "sound": "shoot_heavy",
        "kick": 16.099999999999998,
        "color": [
          174,
          150,
          255
        ],
        "price": 300,
        "melee": false,
        "reach": 0,
        "arc": 0,
        "sprite": "",
        "tier": 2,
        "vfx": "v30_phase"
      },
      "comet_scythe": {
        "key": "comet_scythe",
        "name": "彗尾镰",
        "desc": "长弧紫色切割",
        "dmg": 34.56,
        "cd": 0.62,
        "speed": 0,
        "count": 1,
        "spread": 0,
        "cost": 0,
        "bullet": "b_laser",
        "bsize": 15,
        "pierce": 1,
        "aoe": 0,
        "life": 0,
        "shake": 1.8428571428571427,
        "sound": "laser",
        "kick": 22.4,
        "color": [
          200,
          145,
          249
        ],
        "price": 324,
        "melee": true,
        "reach": 122,
        "arc": 170,
        "sprite": "",
        "tier": 2,
        "vfx": "v30_comet"
      },
      "solar_array": {
        "key": "solar_array",
        "name": "日珥阵列",
        "desc": "多束灼热日光",
        "dmg": 15.12,
        "cd": 0.48,
        "speed": 780,
        "count": 5,
        "spread": 15,
        "cost": 2.94,
        "bullet": "b_laser",
        "bsize": 15,
        "pierce": 2,
        "aoe": 0,
        "life": 1.35,
        "shake": 1.2,
        "sound": "laser",
        "kick": 9.799999999999999,
        "color": [
          255,
          217,
          114
        ],
        "price": 390,
        "melee": false,
        "reach": 0,
        "arc": 0,
        "sprite": "",
        "tier": 2,
        "vfx": "sun"
      },
      "thunder_crown": {
        "key": "thunder_crown",
        "name": "雷冠发射器",
        "desc": "四发连锁电弧",
        "dmg": 18.36,
        "cd": 0.52,
        "speed": 700,
        "count": 4,
        "spread": 13,
        "cost": 2.87,
        "bullet": "b_hex",
        "bsize": 15,
        "pierce": 1,
        "aoe": 0,
        "life": 1.35,
        "shake": 1.307142857142857,
        "sound": "shoot",
        "kick": 11.899999999999999,
        "color": [
          255,
          225,
          137
        ],
        "price": 405,
        "melee": false,
        "reach": 0,
        "arc": 0,
        "sprite": "",
        "tier": 2,
        "vfx": "arc"
      },
      "royal_blaster": {
        "key": "royal_blaster",
        "name": "王权聚能炮",
        "desc": "巨弹范围爆裂",
        "dmg": 41.04,
        "cd": 0.98,
        "speed": 480,
        "count": 1,
        "spread": 0,
        "cost": 3.57,
        "bullet": "b_rocket",
        "bsize": 15,
        "pierce": 0,
        "aoe": 47,
        "life": 1.35,
        "shake": 2.057142857142857,
        "sound": "shoot_heavy",
        "kick": 26.599999999999998,
        "color": [
          255,
          214,
          136
        ],
        "price": 420,
        "melee": false,
        "reach": 0,
        "arc": 0,
        "sprite": "",
        "tier": 2,
        "vfx": "v30_royal"
      },
      "gilded_halberd": {
        "key": "gilded_halberd",
        "name": "鎏金战戟",
        "desc": "大范围长柄横扫",
        "dmg": 42.12,
        "cd": 0.65,
        "speed": 0,
        "count": 1,
        "spread": 0,
        "cost": 0,
        "bullet": "b_bolt",
        "bsize": 15,
        "pierce": 2,
        "aoe": 0,
        "life": 0,
        "shake": 2.0928571428571425,
        "sound": "shoot_heavy",
        "kick": 27.299999999999997,
        "color": [
          255,
          223,
          145
        ],
        "price": 410,
        "melee": true,
        "reach": 121,
        "arc": 151,
        "sprite": "",
        "tier": 2,
        "vfx": "v30_gilded"
      },
      "ember_seraph": {
        "key": "ember_seraph",
        "name": "炽天使羽刃",
        "desc": "火羽迅速连斩",
        "dmg": 33.48,
        "cd": 0.43,
        "speed": 0,
        "count": 1,
        "spread": 0,
        "cost": 0,
        "bullet": "b_plasma",
        "bsize": 15,
        "pierce": 1,
        "aoe": 0,
        "life": 0,
        "shake": 1.8071428571428572,
        "sound": "shoot_heavy",
        "kick": 21.7,
        "color": [
          255,
          194,
          126
        ],
        "price": 428,
        "melee": true,
        "reach": 110,
        "arc": 160,
        "sprite": "",
        "tier": 2,
        "vfx": "ember"
      },
      "rupture_cannon": {
        "key": "rupture_cannon",
        "name": "裂界巨炮",
        "desc": "炮弹爆炸并分裂",
        "dmg": 45.36,
        "cd": 1.05,
        "speed": 520,
        "count": 1,
        "spread": 0,
        "cost": 4.41,
        "bullet": "b_rocket",
        "bsize": 15,
        "pierce": 1,
        "aoe": 58,
        "life": 1.35,
        "shake": 2.2,
        "sound": "shoot_heavy",
        "kick": 29.4,
        "color": [
          255,
          92,
          125
        ],
        "price": 540,
        "melee": false,
        "reach": 0,
        "arc": 0,
        "sprite": "",
        "tier": 2,
        "vfx": "v30_rupture"
      },
      "abyss_loom": {
        "key": "abyss_loom",
        "name": "深渊织机",
        "desc": "六线暗红束流",
        "dmg": 17.28,
        "cd": 0.57,
        "speed": 730,
        "count": 6,
        "spread": 23,
        "cost": 3.5,
        "bullet": "b_laser",
        "bsize": 15,
        "pierce": 3,
        "aoe": 0,
        "life": 1.35,
        "shake": 1.2714285714285714,
        "sound": "laser",
        "kick": 11.2,
        "color": [
          241,
          99,
          163
        ],
        "price": 530,
        "melee": false,
        "reach": 0,
        "arc": 0,
        "sprite": "",
        "tier": 2,
        "vfx": "v30_abyss"
      },
      "crimson_orbit": {
        "key": "crimson_orbit",
        "name": "绯红环炮",
        "desc": "旋转能量弹",
        "dmg": 36.72,
        "cd": 0.84,
        "speed": 330,
        "count": 2,
        "spread": 10,
        "cost": 3.78,
        "bullet": "b_plasma",
        "bsize": 15,
        "pierce": 2,
        "aoe": 29,
        "life": 1.35,
        "shake": 1.9142857142857141,
        "sound": "shoot_heavy",
        "kick": 23.799999999999997,
        "color": [
          255,
          108,
          145
        ],
        "price": 535,
        "melee": false,
        "reach": 0,
        "arc": 0,
        "sprite": "",
        "tier": 2,
        "vfx": "v30_crimson"
      },
      "bloodmoon_glaive": {
        "key": "bloodmoon_glaive",
        "name": "血月偃月刀",
        "desc": "血月远弧斩",
        "dmg": 45.36,
        "cd": 0.65,
        "speed": 0,
        "count": 1,
        "spread": 0,
        "cost": 0,
        "bullet": "b_hex",
        "bsize": 15,
        "pierce": 3,
        "aoe": 0,
        "life": 0,
        "shake": 2.2,
        "sound": "shoot_heavy",
        "kick": 29.4,
        "color": [
          250,
          75,
          111
        ],
        "price": 550,
        "melee": true,
        "reach": 130,
        "arc": 161,
        "sprite": "",
        "tier": 2,
        "vfx": "v30_bloodmoon"
      },
      "terminal_spear": {
        "key": "terminal_spear",
        "name": "终端贯枪",
        "desc": "极远距直线贯穿",
        "dmg": 45.36,
        "cd": 0.7,
        "speed": 0,
        "count": 1,
        "spread": 0,
        "cost": 0,
        "bullet": "b_laser",
        "bsize": 15,
        "pierce": 4,
        "aoe": 0,
        "life": 0,
        "shake": 2.2,
        "sound": "laser",
        "kick": 29.4,
        "color": [
          255,
          105,
          144
        ],
        "price": 560,
        "melee": true,
        "reach": 154,
        "arc": 51,
        "sprite": "",
        "tier": 2,
        "vfx": "v30_terminal"
      },
      "nova_requiem": {
        "key": "nova_requiem",
        "name": "星葬挽歌",
        "desc": "星核爆裂并扩散",
        "dmg": 46.44,
        "cd": 0.84,
        "speed": 570,
        "count": 2,
        "spread": 9,
        "cost": 4.2,
        "bullet": "b_rocket",
        "bsize": 15,
        "pierce": 3,
        "aoe": 48,
        "life": 1.35,
        "shake": 2.2357142857142858,
        "sound": "rad_nova",
        "kick": 30.099999999999998,
        "color": [
          255,
          238,
          185
        ],
        "price": 690,
        "melee": false,
        "reach": 0,
        "arc": 0,
        "sprite": "",
        "tier": 2,
        "vfx": "rad_nova"
      },
      "chrono_lance": {
        "key": "chrono_lance",
        "name": "时凝圣枪",
        "desc": "光矛令目标迟缓",
        "dmg": 44.28,
        "cd": 0.6,
        "speed": 900,
        "count": 1,
        "spread": 0,
        "cost": 3.78,
        "bullet": "b_laser",
        "bsize": 15,
        "pierce": 5,
        "aoe": 0,
        "life": 1.35,
        "shake": 2.164285714285714,
        "sound": "rad_chrono",
        "kick": 28.7,
        "color": [
          176,
          244,
          255
        ],
        "price": 690,
        "melee": false,
        "reach": 0,
        "arc": 0,
        "sprite": "",
        "tier": 2,
        "vfx": "rad_chrono"
      },
      "lifeweaver": {
        "key": "lifeweaver",
        "name": "生命织梭",
        "desc": "命中时回复生命",
        "dmg": 30.24,
        "cd": 0.42,
        "speed": 750,
        "count": 3,
        "spread": 12,
        "cost": 3.57,
        "bullet": "b_plasma",
        "bsize": 15,
        "pierce": 2,
        "aoe": 0,
        "life": 1.35,
        "shake": 1.7,
        "sound": "rad_life",
        "kick": 19.599999999999998,
        "color": [
          188,
          255,
          182
        ],
        "price": 700,
        "melee": false,
        "reach": 0,
        "arc": 0,
        "sprite": "",
        "tier": 2,
        "vfx": "rad_life"
      },
      "prism_ascendant": {
        "key": "prism_ascendant",
        "name": "万象棱镜",
        "desc": "光束连锁敌人",
        "dmg": 42.12,
        "cd": 0.63,
        "speed": 810,
        "count": 2,
        "spread": 7,
        "cost": 4.06,
        "bullet": "b_laser",
        "bsize": 15,
        "pierce": 4,
        "aoe": 0,
        "life": 1.35,
        "shake": 2.0928571428571425,
        "sound": "rad_prism",
        "kick": 27.299999999999997,
        "color": [
          228,
          184,
          255
        ],
        "price": 710,
        "melee": false,
        "reach": 0,
        "arc": 0,
        "sprite": "",
        "tier": 2,
        "vfx": "rad_prism"
      },
      "orbit_mirror": {
        "key": "orbit_mirror",
        "name": "引力镜环",
        "desc": "命中产生吸引场",
        "dmg": 43.2,
        "cd": 0.72,
        "speed": 500,
        "count": 2,
        "spread": 14,
        "cost": 3.99,
        "bullet": "b_hex",
        "bsize": 15,
        "pierce": 3,
        "aoe": 32,
        "life": 1.35,
        "shake": 2.1285714285714286,
        "sound": "rad_orbit",
        "kick": 28.0,
        "color": [
          185,
          205,
          255
        ],
        "price": 720,
        "melee": false,
        "reach": 0,
        "arc": 0,
        "sprite": "",
        "tier": 2,
        "vfx": "rad_orbit"
      }
    };

    D.WEAPONS = WEAPONS;

    var WPN_ORDER = [
      "pistol",
      "smg",
      "shotgun",
      "crossbow",
      "flamer",
      "blade",
      "laser",
      "cannon",
      "rocket",
      "railgun",
      "plasma_blade",
      "pulse_pistol",
      "arc_smg",
      "crystal_shotgun",
      "ion_carbine",
      "burst_rifle",
      "needle_rifle",
      "frost_pistol",
      "corrosion_sprayer",
      "coil_cannon",
      "sonic_blaster",
      "prism_laser",
      "gravity_launcher",
      "ember_mortar",
      "volt_crossbow",
      "scatter_bow",
      "void_revolver",
      "plasma_axe",
      "twin_daggers",
      "shock_hammer",
      "crystal_spear",
      "sunblade",
      "crust_glaive",
      "sewer_harpoon",
      "facility_saw",
      "core_repeater",
      "mine_drill",
      "lab_cryo_staff",
      "gift_starbow",
      "crust_ruinblade",
      "sewer_abyssfang",
      "facility_overdrive",
      "core_nihility",
      "mine_faultaxe",
      "lab_zerobeam",
      "gift_dawnkeeper",
      "trench_blade",
      "moss_whip",
      "mirror_shield",
      "meteor_pike",
      "scrap_saber",
      "vine_sickle",
      "glacier_fang",
      "thunder_axe",
      "solar_cleaver",
      "dust_revolver",
      "reed_carbine",
      "ash_shotgun",
      "tide_sprayer",
      "frost_repeater",
      "echo_blaster",
      "singularity_rifle",
      "aurora_cannon",
      "starfall_bow",
      "quartz_rifle",
      "ember_knife",
      "tidal_spear",
      "obsidian_axe",
      "lumen_whip",
      "pebble_popper",
      "scrap_crossbow",
      "flare_tube",
      "alloy_knife",
      "survey_spear",
      "ivy_repeater",
      "current_shotgun",
      "spring_carbine",
      "acid_cleaver",
      "cloud_staff",
      "frost_lance",
      "echo_pulse",
      "arc_lantern",
      "glass_bow",
      "gyro_blade",
      "null_carbine",
      "prism_fan",
      "quake_hammer",
      "phase_needle",
      "comet_scythe",
      "solar_array",
      "thunder_crown",
      "royal_blaster",
      "gilded_halberd",
      "ember_seraph",
      "rupture_cannon",
      "abyss_loom",
      "crimson_orbit",
      "bloodmoon_glaive",
      "terminal_spear",
      "nova_requiem",
      "chrono_lance",
      "lifeweaver",
      "prism_ascendant",
      "orbit_mirror"
    ];

    D.WPN_ORDER = WPN_ORDER;

    var QUALITY_POOL = {
      "white": [
        "pistol",
        "smg",
        "shotgun",
        "crossbow",
        "flamer",
        "blade",
        "pulse_pistol",
        "needle_rifle",
        "frost_pistol",
        "shock_hammer",
        "trench_blade",
        "mirror_shield",
        "scrap_saber",
        "dust_revolver",
        "obsidian_axe",
        "pebble_popper",
        "scrap_crossbow",
        "flare_tube",
        "alloy_knife",
        "survey_spear",
        "acid_cleaver"
      ],
      "green": [
        "crystal_shotgun",
        "ion_carbine",
        "burst_rifle",
        "scatter_bow",
        "plasma_axe",
        "twin_daggers",
        "crystal_spear",
        "moss_whip",
        "meteor_pike",
        "vine_sickle",
        "reed_carbine",
        "ash_shotgun",
        "tide_sprayer",
        "quartz_rifle",
        "ember_knife",
        "tidal_spear",
        "ivy_repeater",
        "current_shotgun",
        "cloud_staff"
      ],
      "blue": [
        "rocket",
        "plasma_blade",
        "coil_cannon",
        "sonic_blaster",
        "ember_mortar",
        "volt_crossbow",
        "void_revolver",
        "sunblade",
        "glacier_fang",
        "thunder_axe",
        "echo_blaster",
        "spring_carbine",
        "frost_lance",
        "echo_pulse",
        "arc_lantern",
        "gyro_blade",
        "quake_hammer"
      ],
      "purple": [
        "laser",
        "railgun",
        "arc_smg",
        "corrosion_sprayer",
        "prism_laser",
        "gravity_launcher",
        "frost_repeater",
        "singularity_rifle",
        "aurora_cannon",
        "lumen_whip",
        "glass_bow",
        "null_carbine",
        "prism_fan",
        "phase_needle",
        "comet_scythe"
      ],
      "gold": [
        "crust_glaive",
        "sewer_harpoon",
        "facility_saw",
        "terminal_spear",
        "mine_drill",
        "lab_cryo_staff",
        "gift_starbow",
        "cannon",
        "solar_cleaver",
        "solar_array",
        "thunder_crown",
        "royal_blaster",
        "gilded_halberd",
        "ember_seraph"
      ],
      "red": [
        "crust_ruinblade",
        "sewer_abyssfang",
        "facility_overdrive",
        "core_nihility",
        "mine_faultaxe",
        "lab_zerobeam",
        "gift_dawnkeeper",
        "rupture_cannon",
        "abyss_loom",
        "crimson_orbit",
        "bloodmoon_glaive"
      ],
      "radiant": [
        "starfall_bow",
        "core_repeater",
        "nova_requiem",
        "chrono_lance",
        "lifeweaver",
        "prism_ascendant",
        "orbit_mirror"
      ]
    };

    D.QUALITY_POOL = QUALITY_POOL;

    var SCENE_BOSS_WEAPONS = {
      "crust": {
        "gold": "crust_glaive",
        "red": "crust_ruinblade"
      },
      "sewer": {
        "gold": "sewer_harpoon",
        "red": "sewer_abyssfang"
      },
      "facility": {
        "gold": "facility_saw",
        "red": "facility_overdrive"
      },
      "core": {
        "gold": "terminal_spear",
        "red": "core_nihility"
      },
      "d_mine": {
        "gold": "mine_drill",
        "red": "mine_faultaxe"
      },
      "d_lab": {
        "gold": "lab_cryo_staff",
        "red": "lab_zerobeam"
      },
      "d_gift": {
        "gold": "gift_starbow",
        "red": "gift_dawnkeeper"
      }
    };

    D.SCENE_BOSS_WEAPONS = SCENE_BOSS_WEAPONS;

    var WEAPON_QUALITY = {
      "pistol": "white",
      "smg": "white",
      "shotgun": "white",
      "crossbow": "white",
      "flamer": "white",
      "blade": "white",
      "pulse_pistol": "white",
      "needle_rifle": "white",
      "frost_pistol": "white",
      "shock_hammer": "white",
      "trench_blade": "white",
      "mirror_shield": "white",
      "scrap_saber": "white",
      "dust_revolver": "white",
      "obsidian_axe": "white",
      "pebble_popper": "white",
      "scrap_crossbow": "white",
      "flare_tube": "white",
      "alloy_knife": "white",
      "survey_spear": "white",
      "acid_cleaver": "white",
      "crystal_shotgun": "green",
      "ion_carbine": "green",
      "burst_rifle": "green",
      "scatter_bow": "green",
      "plasma_axe": "green",
      "twin_daggers": "green",
      "crystal_spear": "green",
      "moss_whip": "green",
      "meteor_pike": "green",
      "vine_sickle": "green",
      "reed_carbine": "green",
      "ash_shotgun": "green",
      "tide_sprayer": "green",
      "quartz_rifle": "green",
      "ember_knife": "green",
      "tidal_spear": "green",
      "ivy_repeater": "green",
      "current_shotgun": "green",
      "cloud_staff": "green",
      "rocket": "blue",
      "plasma_blade": "blue",
      "coil_cannon": "blue",
      "sonic_blaster": "blue",
      "ember_mortar": "blue",
      "volt_crossbow": "blue",
      "void_revolver": "blue",
      "sunblade": "blue",
      "glacier_fang": "blue",
      "thunder_axe": "blue",
      "echo_blaster": "blue",
      "spring_carbine": "blue",
      "frost_lance": "blue",
      "echo_pulse": "blue",
      "arc_lantern": "blue",
      "gyro_blade": "blue",
      "quake_hammer": "blue",
      "laser": "purple",
      "railgun": "purple",
      "arc_smg": "purple",
      "corrosion_sprayer": "purple",
      "prism_laser": "purple",
      "gravity_launcher": "purple",
      "frost_repeater": "purple",
      "singularity_rifle": "purple",
      "aurora_cannon": "purple",
      "lumen_whip": "purple",
      "glass_bow": "purple",
      "null_carbine": "purple",
      "prism_fan": "purple",
      "phase_needle": "purple",
      "comet_scythe": "purple",
      "crust_glaive": "gold",
      "sewer_harpoon": "gold",
      "facility_saw": "gold",
      "terminal_spear": "gold",
      "mine_drill": "gold",
      "lab_cryo_staff": "gold",
      "gift_starbow": "gold",
      "cannon": "gold",
      "solar_cleaver": "gold",
      "solar_array": "gold",
      "thunder_crown": "gold",
      "royal_blaster": "gold",
      "gilded_halberd": "gold",
      "ember_seraph": "gold",
      "crust_ruinblade": "red",
      "sewer_abyssfang": "red",
      "facility_overdrive": "red",
      "core_nihility": "red",
      "mine_faultaxe": "red",
      "lab_zerobeam": "red",
      "gift_dawnkeeper": "red",
      "rupture_cannon": "red",
      "abyss_loom": "red",
      "crimson_orbit": "red",
      "bloodmoon_glaive": "red",
      "starfall_bow": "radiant",
      "core_repeater": "radiant",
      "nova_requiem": "radiant",
      "chrono_lance": "radiant",
      "lifeweaver": "radiant",
      "prism_ascendant": "radiant",
      "orbit_mirror": "radiant"
    };

    D.WEAPON_QUALITY = WEAPON_QUALITY;

    /* ---- weapon.py（品质机制，需求 6：1.4 机制化品质）---- */
    var QUALITY_MECH = {
      "white": {},
      "green": {
        "rate": 1.05,
        "bspd": 1.08
      },
      "blue": {
        "rate": 1.1,
        "bspd": 1.15,
        "extra": 1
      },
      "purple": {
        "rate": 1.15,
        "bspd": 1.22,
        "extra": 1,
        "pierce": 1,
        "melee_double": 0.3
      },
      "gold": {
        "rate": 1.2,
        "bspd": 1.3,
        "extra": 1,
        "pierce": 1,
        "burst": 2,
        "melee_double": 0.3
      },
      "red": {
        "rate": 1.25,
        "bspd": 1.35,
        "extra": 1,
        "pierce": 2,
        "burst": 2,
        "split": 2,
        "melee_double": 0.3
      },
      "radiant": {
        "rate": 1.3,
        "bspd": 1.42,
        "extra": 2,
        "pierce": 2,
        "burst": 3,
        "split": 3,
        "homing": 2.4,
        "melee_double": 0.3
      }
    };

    D.QUALITY_MECH = QUALITY_MECH;

    /* ---- chapter.py ---- */
    var INTRO = [
      "第 7 号避难所，记录员编号 021。",
      "污染已经越过第三道防线。地表的土壤在变色，",
      "空气里飘着不会落下的灰。",
      "我们叫它「陆面过程」——",
      "一场从地底开始、正在改写整颗星球的入侵。",
      "协议还在运行。我是最后一批执行者之一。",
      "",
      "我不指望能彻底清掉它。",
      "我只想在被改写之前，",
      "替所有人记住——净土长什么样子。",
      "任务：向下。找到污染源。在它改写一切之前。"
    ];

    D.INTRO = INTRO;

    var CHAPTER_STORY = {
      "crust": {
        "name": "地表残骸",
        "sub": "THE SCORCHED CRUST",
        "enter": [
          "第一层，地表。",
          "城市只剩下骨架，风把灰吹成墙。",
          "记录：污染浓度 3%。还在可控范围。"
        ],
        "clear": [
          "地表段清理完毕。",
          "但探测仪指向更深处——污染不是从天上来的，是从地底涌上来的。"
        ],
        "tint": [
          150,
          132,
          108
        ]
      },
      "sewer": {
        "name": "腐化下水道",
        "sub": "THE ROTWAYS",
        "enter": [
          "第二层，废弃管网。",
          "墙面上长着不该长在这的东西。",
          "记录：污染浓度 21%。样本开始有活性。"
        ],
        "clear": [
          "管网贯通。",
          "我在这里第一次看见它们「生长」的样子。",
          "它们不是在蔓延，是在进食。"
        ],
        "tint": [
          96,
          130,
          96
        ]
      },
      "facility": {
        "name": "机械坟场",
        "sub": "THE MACHINE GRAVEYARD",
        "enter": [
          "第三层，旧工业区。",
          "机械残骸堆成山，有些还在动。",
          "记录：污染浓度 48%。检测到人工信号源。"
        ],
        "clear": [
          "这里有人在改造污染。",
          "不止我一个还活着——但他们显然不打算让我继续往下走。"
        ],
        "tint": [
          110,
          116,
          138
        ]
      },
      "core": {
        "name": "污染原点",
        "sub": "THE ORIGIN",
        "enter": [
          "第四层。这里就是源头。",
          "地表的一切，都是从这一间开始的。",
          "记录：污染浓度 96%。协议提示：已无撤退路线。"
        ],
        "clear": [
          "源头封住了。",
          "地表的浓度读数在下降——真的在下降。",
          "我完成了任务。虽然，可能只有我一个人知道。"
        ],
        "tint": [
          170,
          80,
          96
        ]
      },
      "d_mine": {
        "name": "废弃矿井",
        "sub": "THE ABANDONED SHAFT",
        "enter": [
          "副本：废弃矿井。",
          "支线信号源，偏离主路线。",
          "这里的东西比主线更古老。"
        ],
        "clear": [
          "矿井勘探完成。",
          "带出来的东西，足够让我再往下走很久。"
        ],
        "tint": [
          140,
          120,
          90
        ]
      },
      "d_lab": {
        "name": "实验冷库",
        "sub": "THE COLD LAB",
        "enter": [
          "副本：实验冷库。",
          "低温让污染结晶了——",
          "也让那些标本保持着死亡那一刻的姿势。"
        ],
        "clear": [
          "冷库数据已提取。",
          "终于知道协议是谁写的了。"
        ],
        "tint": [
          110,
          150,
          170
        ]
      },
      "d_gift": {
        "name": "馈赠之地",
        "sub": "THE GIFT",
        "enter": [
          "奖励副本：馈赠之地。",
          "协议最后的善意。",
          "这里没有敌人会主动追你——只要你手脚够快。"
        ],
        "clear": [
          "馈赠已收取。",
          "地表的天，第一次亮了。"
        ],
        "tint": [
          200,
          180,
          120
        ]
      }
    };

    D.CHAPTER_STORY = CHAPTER_STORY;

    var MAIN = [
      "crust",
      "sewer",
      "facility",
      "core"
    ];

    D.MAIN = MAIN;

    var DUNGEONS = {
      "d_mine": {
        "after": "sewer",
        "cond": {
          "cleared": true,
          "kills": 90,
          "trap_hits": 4
        },
        "cond_text": "在「腐化下水道」通关一次，单局击杀 ≥ 90 个敌人，且踩中的毒池/泥沼 ≤ 4 次",
        "hint": "下水道的怪以「腐壳虫 + 游荡机」为主，毒池与泥沼是本层唯一的地面机关——踩多了扣血又减速。想开废弃矿井，得先证明你能在这层横着走。",
        "bind": {
          "enemies": [
            [
              "slug",
              "腐壳虫——下水道的基础单位，数量极多。击杀门槛 90 主要靠它堆"
            ],
            [
              "drone",
              "游荡机——会贴脸自爆前摇，边打边退才安全"
            ]
          ],
          "traps": [
            [
              "poison",
              "毒池——站上去持续掉血，是\"踩中陷阱\"计数的主力"
            ],
            [
              "slow",
              "泥沼——大幅减速，被围住时最致命"
            ]
          ],
          "tip": "想少踩陷阱：贴着墙走，毒池和泥沼从不长在墙角。"
        }
      },
      "d_lab": {
        "after": "facility",
        "cond": {
          "cleared": true,
          "kills": 140,
          "bomber_hits": 2,
          "low_hp": true
        },
        "cond_text": "在「机械坟场」通关一次，单局击杀 ≥ 140 个敌人、被自爆囊炸到 ≤ 2 次，且曾残血（≤3 点生命）通关",
        "hint": "机械坟场的威胁全在「自爆囊」和「爆破工头」——它们贴脸才会引爆，被炸两次以上说明你一直在被近身。冷库的门只认真正的老手：既要清得干净，也要活得够险。",
        "bind": {
          "enemies": [
            [
              "bomber",
              "自爆囊——距离 <60 时开始闪烁，约 1.2 秒后原地爆炸。被炸到就计数"
            ],
            [
              "bomber_big",
              "爆破工头——自爆囊的精英版，爆炸半径更大，但它自己也会被炸伤"
            ],
            [
              "mech",
              "区域首领「机械领主」——第 5 关必打，残血通关通常发生在这场"
            ]
          ],
          "traps": [
            [
              "shock",
              "电弧栅栏——机械坟场的地面机关，踩中会短暂麻痹（更容易被自爆囊贴上）"
            ],
            [
              "spike",
              "地刺——固定伤害，好躲但别在混战里踩"
            ]
          ],
          "tip": "躲自爆囊的关键：听到\"滴\"声立刻反向冲刺，不要原地绕圈。残血通关建议留一发冲刺。"
        }
      }
    };

    D.DUNGEONS = DUNGEONS;

    var BONUS = "d_gift";

    D.BONUS = BONUS;

    var BONUS_PRICE = 6500;

    D.BONUS_PRICE = BONUS_PRICE;

    var BONUS_PRICE_DIA = 0;

    D.BONUS_PRICE_DIA = BONUS_PRICE_DIA;

    var STAGES_PER_SCENE = 5;

    D.STAGES_PER_SCENE = STAGES_PER_SCENE;

    var SCENE_MOBS = {
      "crust": {
        "small": [
          "slime",
          "slug"
        ],
        "elite": [
          "slime_big"
        ],
        "boss": "warlord",
        "bigboss": "warlord"
      },
      "sewer": {
        "small": [
          "slug",
          "drone"
        ],
        "elite": [
          "drone_big"
        ],
        "boss": "swarmqueen",
        "bigboss": "swarmqueen"
      },
      "facility": {
        "small": [
          "drone",
          "bomber"
        ],
        "elite": [
          "bomber_big"
        ],
        "boss": "mech",
        "bigboss": "mech"
      },
      "core": {
        "small": [
          "spore",
          "wraith"
        ],
        "elite": [
          "wraith_big"
        ],
        "boss": "protocol",
        "bigboss": "origin"
      },
      "d_mine": {
        "small": [
          "slug",
          "bomber"
        ],
        "elite": [
          "slime_big"
        ],
        "boss": "foreman",
        "bigboss": "foreman"
      },
      "d_lab": {
        "small": [
          "wraith",
          "drone"
        ],
        "elite": [
          "wraith_big"
        ],
        "boss": "specimen",
        "bigboss": "specimen"
      },
      "d_gift": {
        "small": [
          "slime",
          "slug"
        ],
        "elite": [],
        "boss": null,
        "bigboss": null
      }
    };

    D.SCENE_MOBS = SCENE_MOBS;

    var POLLUTION = {
      "crust": {
        "pct": 3,
        "hp_cut": 0,
        "spd": 1.0,
        "regen": 1.0,
        "drain": 0.0,
        "tint": [
          150,
          132,
          108
        ],
        "desc": "空气里的灰还没落到皮肤上。"
      },
      "sewer": {
        "pct": 21,
        "hp_cut": 1,
        "spd": 0.97,
        "regen": 0.95,
        "drain": 0.0,
        "tint": [
          96,
          130,
          96
        ],
        "desc": "样本有活性。你会觉得比平时慢一点。"
      },
      "facility": {
        "pct": 48,
        "hp_cut": 2,
        "spd": 0.93,
        "regen": 0.88,
        "drain": 0.05,
        "tint": [
          110,
          116,
          138
        ],
        "desc": "污染开始改写机械。持续侵蚀生效。"
      },
      "core": {
        "pct": 96,
        "hp_cut": 4,
        "spd": 0.88,
        "regen": 0.78,
        "drain": 0.14,
        "tint": [
          170,
          80,
          96
        ],
        "desc": "这里就是源头。协议提示：已无撤退路线。"
      },
      "d_mine": {
        "pct": 30,
        "hp_cut": 1,
        "spd": 0.96,
        "regen": 0.93,
        "drain": 0.02,
        "tint": [
          140,
          120,
          90
        ],
        "desc": "支线信号源。矿井深处的空气更稠。"
      },
      "d_lab": {
        "pct": 60,
        "hp_cut": 3,
        "spd": 0.91,
        "regen": 0.84,
        "drain": 0.08,
        "tint": [
          110,
          150,
          170
        ],
        "desc": "低温压住了污染，但结晶会割伤你。"
      },
      "d_gift": {
        "pct": 0,
        "hp_cut": 0,
        "spd": 1.0,
        "regen": 1.0,
        "drain": 0.0,
        "tint": [
          200,
          180,
          120
        ],
        "desc": "协议最后的善意。这里的空气是干净的。"
      }
    };

    D.POLLUTION = POLLUTION;

    var POLLUTION_STAGE_SPAN = 0.4;

    D.POLLUTION_STAGE_SPAN = POLLUTION_STAGE_SPAN;

    var COIN_BASE = 2.0;

    D.COIN_BASE = COIN_BASE;

    var COIN_STEP = 0.4;

    D.COIN_STEP = COIN_STEP;

    var COIN_ELITE_MUL = 1.8;

    D.COIN_ELITE_MUL = COIN_ELITE_MUL;

    var COIN_BOSS_MUL = 3.5;

    D.COIN_BOSS_MUL = COIN_BOSS_MUL;

    /* ---- codex.py ---- */
    var CODEX_CATS = {
      "enemy": "怪物",
      "weapon": "武器",
      "material": "材料",
      "collect": "收集品"
    };

    D.CODEX_CATS = CODEX_CATS;

    var ENEMY_CODEX = {
      "scatter_raider": [
        "散弹掠夺者",
        "地表残骸 / 矿井",
        "small",
        "手持霰铳，射出宽角慢速弹幕。"
      ],
      "beam_raider": [
        "缓束哨兵",
        "机械坟场 / 原点",
        "small",
        "单条极慢激光，封锁走位。"
      ],
      "rifle_raider": [
        "精确射手",
        "下水道 / 冷库",
        "small",
        "高速单发，提前看清准星。"
      ],
      "slime": [
        "污染黏液",
        "地表残骸",
        "small",
        "最基础的污染体，会朝你缓慢蠕动。"
      ],
      "slug": [
        "腐壳虫",
        "地表残骸",
        "small",
        "外壳很硬，先对准再贴地冲锋，撞墙会僵住。"
      ],
      "crawler": [
        "碎骨爬行体",
        "地表残骸",
        "small",
        "趴在地上快速爬行，偶尔弹跳扑咬。"
      ],
      "slime_big": [
        "黏液母体",
        "地表残骸",
        "elite",
        "更大更硬，分裂时注意包夹。"
      ],
      "warlord": [
        "残骸军阀",
        "地表残骸",
        "boss",
        "挥舞废铁的重装体，冲撞后有僵直可言。"
      ],
      "drone": [
        "游荡机",
        "腐化下水道",
        "small",
        "失控的巡检机，会绕着你要害打。"
      ],
      "leech": [
        "吸血水蛭",
        "腐化下水道",
        "small",
        "贴住你会持续抽血，别让它缠上身。"
      ],
      "drone_big": [
        "重装巡弋",
        "腐化下水道",
        "elite",
        "护盾会周期性重启，抓住空档。"
      ],
      "swarmqueen": [
        "虫群女王",
        "腐化下水道",
        "boss",
        "产卵型首领，别让场面积累。"
      ],
      "bomber": [
        "自爆囊",
        "机械坟场",
        "small",
        "靠近就膨胀，别让它贴脸。"
      ],
      "turret": [
        "废弃炮台",
        "机械坟场",
        "small",
        "固定不动，但火力覆盖整条通道。"
      ],
      "bomber_big": [
        "爆破工头",
        "机械坟场",
        "elite",
        "一次性放出整圈炸弹，先清场再打。"
      ],
      "mech": [
        "坟场机枢",
        "机械坟场",
        "boss",
        "三段变形，每段换一种弹幕。"
      ],
      "spore": [
        "孢殖体",
        "污染原点",
        "small",
        "死亡会留下毒雾，别站在它死的地方。"
      ],
      "wraith": [
        "污染幽影",
        "污染原点",
        "small",
        "半透明，会瞬移到你背后，注意转身。"
      ],
      "wraith_big": [
        "幽影督军",
        "污染原点",
        "elite",
        "瞬移更频繁，弹道预判比它本体更准。"
      ],
      "protocol": [
        "协议残片",
        "污染原点",
        "boss",
        "旧世界防御程序，攻击非常有规律。"
      ],
      "origin": [
        "污染原点·本体",
        "污染原点",
        "bigboss",
        "一切开始的地方。终局。"
      ],
      "rockworm": [
        "岩噬虫",
        "废弃矿井",
        "small",
        "在岩壁间钻行，从背后冒出来突袭。"
      ],
      "minebot": [
        "雷区机兵",
        "废弃矿井",
        "small",
        "边走边布雷，走位要留意脚下。"
      ],
      "slime_big_m": [
        "矿脉黏液体",
        "废弃矿井",
        "elite",
        "吃了矿物变得格外坚硬，钝击无效。"
      ],
      "foreman": [
        "矿井监工",
        "废弃矿井",
        "boss",
        "在狭窄处很危险，拉开距离打。"
      ],
      "frostbite": [
        "霜蚀体",
        "实验冷库",
        "small",
        "命中会附带减速，别被叠满。"
      ],
      "spore_big": [
        "孢殖母巢",
        "实验冷库",
        "elite",
        "持续召唤小孢殖体，速杀。"
      ],
      "specimen": [
        "冷库标本",
        "实验冷库",
        "boss",
        "冻住的东西动了。别被逼到角落。"
      ],
      "purifier": [
        "净土傀儡",
        "净土庭园",
        "small",
        "看守圣地的空壳，动作缓慢但很痛。"
      ],
      "sprite": [
        "微光灵",
        "净土庭园",
        "small",
        "会闪避子弹的灵体，打它得预判。"
      ],
      "guardian": [
        "净土守卫",
        "净土庭园",
        "boss",
        "把守着最后一片净土的门。"
      ],
      "mimic": [
        "拟态宝箱",
        "任意",
        "rare",
        "伪装成宝箱。靠近才现形，打它掉好东西。"
      ],
      "wanderer": [
        "拾荒旅人",
        "任意",
        "rare",
        "不主动攻击。它身上有红色与璀璨的图纸。"
      ],
      "lucky_treasure": [
        "幸运宝藏怪",
        "任意",
        "rare",
        "携带钻石、稀有材料与珍品武器的金色怪物。"
      ],
      "crawler_big": [
        "碎骨领主",
        "地表残骸",
        "elite",
        "冲锋落点会留下骨刺，别站在圈里。"
      ],
      "leech_big": [
        "血蛭母体",
        "腐化下水道",
        "elite",
        "一次吸附多个目标，必须先打断。"
      ],
      "turret_big": [
        "重炮平台",
        "机械坟场",
        "elite",
        "三连发覆盖全场，靠掩体推进。"
      ],
      "rockworm_big": [
        "岩噬母虫",
        "废弃矿井",
        "elite",
        "钻地后整片地面都在震，抬头看。"
      ],
      "frostbite_big": [
        "霜蚀主宰",
        "实验冷库",
        "elite",
        "光环持续减速，近身等于自杀。"
      ],
      "guardian_big": [
        "净土裁决者",
        "净土庭园",
        "elite",
        "会封锁你的退路，速战速决。"
      ],
      "spore_big_m": [
        "孢殖祖巢",
        "污染原点",
        "elite",
        "毒雾覆盖半场，只能边跑边打。"
      ],
      "crust_sentinel": [
        "熔渣哨兵",
        "地表残骸",
        "boss",
        "第三关的废钢守门者，挥出扇形碎铁。"
      ],
      "sewer_serpent": [
        "污水管蛇",
        "腐化下水道",
        "boss",
        "盘绕水渠的污染巨蛇，擅长突进。"
      ],
      "facility_smelter": [
        "熔炉看守",
        "机械坟场",
        "boss",
        "旧熔炉的活动炉心，会释放热浪。"
      ],
      "mine_excavator": [
        "地脉掘进机",
        "废弃矿井",
        "boss",
        "钻地机械失控后成为矿道守卫。"
      ],
      "lab_cryowarden": [
        "零号冻卫",
        "实验冷库",
        "boss",
        "冷库第一批实验体，周围持续结霜。"
      ],
      "gift_bloom": [
        "晶花园丁",
        "净土庭园",
        "boss",
        "晶体与藤蔓构成的净土守护者。"
      ]
    };

    D.ENEMY_CODEX = ENEMY_CODEX;

    var ENEMY_ORDER = [
      "scatter_raider",
      "beam_raider",
      "rifle_raider",
      "slime",
      "slug",
      "crawler",
      "slime_big",
      "warlord",
      "drone",
      "leech",
      "drone_big",
      "swarmqueen",
      "bomber",
      "turret",
      "bomber_big",
      "mech",
      "spore",
      "wraith",
      "wraith_big",
      "protocol",
      "origin",
      "rockworm",
      "minebot",
      "slime_big_m",
      "foreman",
      "frostbite",
      "spore_big",
      "specimen",
      "purifier",
      "sprite",
      "guardian",
      "mimic",
      "wanderer",
      "lucky_treasure",
      "crawler_big",
      "leech_big",
      "turret_big",
      "rockworm_big",
      "frostbite_big",
      "guardian_big",
      "spore_big_m",
      "crust_sentinel",
      "sewer_serpent",
      "facility_smelter",
      "mine_excavator",
      "lab_cryowarden",
      "gift_bloom"
    ];

    D.ENEMY_ORDER = ENEMY_ORDER;

    var SCENE_ENEMIES = {
      "crust": {
        "small": [
          "slime",
          "slug",
          "crawler",
          "scatter_raider"
        ],
        "elite": [
          "slime_big"
        ],
        "boss": "warlord"
      },
      "sewer": {
        "small": [
          "slug",
          "drone",
          "leech",
          "rifle_raider"
        ],
        "elite": [
          "drone_big"
        ],
        "boss": "swarmqueen"
      },
      "facility": {
        "small": [
          "drone",
          "bomber",
          "turret",
          "beam_raider"
        ],
        "elite": [
          "bomber_big"
        ],
        "boss": "mech"
      },
      "core": {
        "small": [
          "spore",
          "wraith",
          "frostbite",
          "beam_raider"
        ],
        "elite": [
          "wraith_big"
        ],
        "boss": "origin"
      },
      "d_mine": {
        "small": [
          "rockworm",
          "minebot",
          "slug",
          "scatter_raider"
        ],
        "elite": [
          "slime_big_m"
        ],
        "boss": "foreman"
      },
      "d_lab": {
        "small": [
          "frostbite",
          "spore",
          "wraith",
          "rifle_raider"
        ],
        "elite": [
          "spore_big"
        ],
        "boss": "specimen"
      },
      "d_gift": {
        "small": [
          "purifier",
          "sprite"
        ],
        "elite": [],
        "boss": "guardian"
      }
    };

    D.SCENE_ENEMIES = SCENE_ENEMIES;

    var COLLECTS = {
      "gear_cog": [
        "锈蚀齿轮",
        "common",
        "旧机械里拆出来的，还带着一点温度。"
      ],
      "glass_shard": [
        "污染玻片",
        "common",
        "凝固的污染在玻璃里长成了花纹。"
      ],
      "doll_rabbit": [
        "缝补布偶",
        "common",
        "针脚歪歪扭扭，是谁留下的？"
      ],
      "ledger": [
        "半本账簿",
        "common",
        "字迹被水泡烂了，只剩几个数字。"
      ],
      "coin_pressed": [
        "压平的硬币",
        "common",
        "被碾压成薄片，上面的头像看不清了。"
      ],
      "ring_copper": [
        "铜环",
        "superb",
        "内圈刻着一行小字：「等我回来」。"
      ],
      "seed_pod": [
        "未萌发的种荚",
        "superb",
        "据说只要土还能用，它就能活。"
      ],
      "music_box": [
        "八音盒",
        "superb",
        "上紧发条，它还能唱完前半段旋律。"
      ],
      "photo": [
        "褪色照片",
        "superb",
        "四个人站在阳光里。没有人穿防护服。"
      ],
      "core_fragment": [
        "协议残页",
        "superb",
        "写协议的人，也许就在这张纸上。"
      ]
    };

    D.COLLECTS = COLLECTS;

    var COLLECT_ORDER = [
      "gear_cog",
      "glass_shard",
      "doll_rabbit",
      "ledger",
      "coin_pressed",
      "ring_copper",
      "seed_pod",
      "music_box",
      "photo",
      "core_fragment"
    ];

    D.COLLECT_ORDER = COLLECT_ORDER;

    var WEAPON_CODEX = {
      "pistol": [
        "学徒手枪",
        "不耗能的万能开局枪（伤 8 · 攻速 3.8/秒）"
      ],
      "smg": [
        "蜂鸟冲锋枪",
        "射速极快，耗能轻微（伤 4 · 攻速 10.5/秒）"
      ],
      "shotgun": [
        "蒸汽霰弹枪",
        "近距离一枪糊脸（伤 4×6 · 攻速 1.4/秒）"
      ],
      "crossbow": [
        "钉刺弩",
        "单发高伤，弹道笔直且穿透 1 个敌人（伤 19 · 攻速 1.7/秒）"
      ],
      "flamer": [
        "霰流喷射器",
        "近程高速散射，贴脸输出极高但射程短（伤 3 · 攻速 13.3/秒）"
      ],
      "blade": [
        "废铁砍刀",
        "近战武器。身前扇形横扫，不耗能，伤害集中（伤 17 · 攻速 2.4/秒）"
      ],
      "laser": [
        "幽蓝激光枪",
        "高速穿透，指哪打哪（伤 11 · 攻速 5.9/秒）"
      ],
      "cannon": [
        "金色传说炮",
        "三连高伤，稀有的传说武器（伤 16×3 · 攻速 2.9/秒）"
      ],
      "rocket": [
        "脆脆火箭筒",
        "大范围爆炸重炮，可摧毁掩体（伤 26 · 攻速 1.0/秒）"
      ],
      "railgun": [
        "磁轨狙击",
        "蓄力一击，穿透整条直线，耗能高（伤 35 · 攻速 0.7/秒）"
      ],
      "plasma_blade": [
        "等离子长刃",
        "近战武器。范围更大的等离子斩，附带击退（伤 28 · 攻速 1.6/秒）"
      ],
      "pulse_pistol": [
        "脉冲手枪",
        "三色脉冲，弹道稳定（伤 10 · 攻速 3.1/秒）"
      ],
      "arc_smg": [
        "电弧蜂群",
        "高速电弧短点射（伤 5×2 · 攻速 9.1/秒）"
      ],
      "crystal_shotgun": [
        "棱晶散射器",
        "晶片广角散射（伤 6×7 · 攻速 1.2/秒）"
      ],
      "ion_carbine": [
        "离子卡宾",
        "轻量穿透离子束（伤 13 · 攻速 3.4/秒）"
      ],
      "burst_rifle": [
        "破晓三连",
        "三发短促连击（伤 8×3 · 攻速 2.6/秒）"
      ],
      "needle_rifle": [
        "毒针步枪",
        "高精度细针（伤 14 · 攻速 2.4/秒）"
      ],
      "frost_pistol": [
        "霜凝短铳",
        "冷光速射（伤 9 · 攻速 4.8/秒）"
      ],
      "corrosion_sprayer": [
        "腐蚀喷射器",
        "短程锥形喷射（伤 4×3 · 攻速 7.7/秒）"
      ],
      "coil_cannon": [
        "线圈裂变炮",
        "高压重弹，带爆炸（伤 27 · 攻速 0.9/秒）"
      ],
      "sonic_blaster": [
        "共振震荡炮",
        "宽扇形音浪（伤 8×5 · 攻速 1.4/秒）"
      ],
      "prism_laser": [
        "虹棱长枪",
        "双束穿透激光（伤 16×2 · 攻速 1.8/秒）"
      ],
      "gravity_launcher": [
        "引力井",
        "缓慢重弹，命中爆裂（伤 29 · 攻速 0.8/秒）"
      ],
      "ember_mortar": [
        "余烬迫击",
        "燃烧核心范围打击（伤 24×2 · 攻速 1.0/秒）"
      ],
      "volt_crossbow": [
        "雷鸣连弩",
        "电磁连弩（伤 17×2 · 攻速 2.1/秒）"
      ],
      "scatter_bow": [
        "月影星弓",
        "三箭抛射（伤 11×3 · 攻速 1.6/秒）"
      ],
      "void_revolver": [
        "虚空左轮",
        "高伤缓射穿透弹（伤 28 · 攻速 1.1/秒）"
      ],
      "plasma_axe": [
        "等离子战斧",
        "重型弧形劈砍（伤 31 · 攻速 1.4/秒）"
      ],
      "twin_daggers": [
        "双生影刃",
        "高速近身双斩（伤 14 · 攻速 4.3/秒）"
      ],
      "shock_hammer": [
        "震地重锤",
        "广范围雷击挥砸（伤 33 · 攻速 1.0/秒）"
      ],
      "crystal_spear": [
        "晶脊长矛",
        "长射程窄角刺击（伤 25 · 攻速 1.9/秒）"
      ],
      "sunblade": [
        "日冕光刃",
        "高能宽角剑气（伤 33 · 攻速 1.5/秒）"
      ],
      "crust_glaive": [
        "焦土戟",
        "裂开的合金戟刃，扫出炽热碎屑（伤 33 · 攻速 1.8/秒）"
      ],
      "sewer_harpoon": [
        "腐潮鱼叉",
        "长距离穿刺并释放腐蚀（伤 30 · 攻速 1.9/秒）"
      ],
      "facility_saw": [
        "机枢圆锯",
        "高速旋刃，贴身连斩（伤 23 · 攻速 4.0/秒）"
      ],
      "core_repeater": [
        "协议连星",
        "连续放出污染光束（伤 17×2 · 攻速 6.2/秒）"
      ],
      "mine_drill": [
        "矿脉穿刺钻",
        "钨钢螺旋头穿过护甲（伤 37 · 攻速 1.7/秒）"
      ],
      "lab_cryo_staff": [
        "冷库凝霜杖",
        "冻结触碰目标并向前放出冰晶（伤 29 · 攻速 2.0/秒）"
      ],
      "gift_starbow": [
        "净土星弓",
        "收束的星光连射（伤 18×4 · 攻速 2.1/秒）"
      ],
      "crust_ruinblade": [
        "毁灭断刃",
        "残骸军阀遗留的赤色断刃（伤 41 · 攻速 1.7/秒）"
      ],
      "sewer_abyssfang": [
        "深渊双牙",
        "虫群女王的分叉毒牙（伤 38 · 攻速 3.1/秒）"
      ],
      "facility_overdrive": [
        "超载矩阵炮",
        "机枢核心驱动的灼热重炮（伤 37×3 · 攻速 1.0/秒）"
      ],
      "core_nihility": [
        "虚无裁断",
        "污染原点凝成的赤红判决（伤 45 · 攻速 1.6/秒）"
      ],
      "mine_faultaxe": [
        "断层巨斧",
        "矿井监工的裂地重斧（伤 45 · 攻速 1.5/秒）"
      ],
      "lab_zerobeam": [
        "绝对零度炮",
        "冷库实验的赤红冻结射线（伤 36×2 · 攻速 1.4/秒）"
      ],
      "gift_dawnkeeper": [
        "晨曦守护剑",
        "净土守卫的最后誓言（伤 43 · 攻速 1.7/秒）"
      ],
      "trench_blade": [
        "堑壕直刀",
        "简洁可靠的近战直刀（伤 19 · 攻速 2.6/秒）"
      ],
      "moss_whip": [
        "苔链鞭",
        "柔性链刃覆盖宽广扇区（伤 18 · 攻速 2.9/秒）"
      ],
      "mirror_shield": [
        "镜面盾刃",
        "近身撞击时反射棱光（伤 26 · 攻速 1.6/秒）"
      ],
      "meteor_pike": [
        "陨铁骑枪",
        "窄角远距突刺（伤 32 · 攻速 1.8/秒）"
      ],
      "scrap_saber": [
        "荒原短刀",
        "轻快宽角斩击（伤 17 · 攻速 2.6/秒）"
      ],
      "vine_sickle": [
        "蔓生镰",
        "腐蚀刃使目标持续受伤（伤 23 · 攻速 2.2/秒）"
      ],
      "glacier_fang": [
        "冰牙剑",
        "冰刃降低目标移动速度（伤 28 · 攻速 1.8/秒）"
      ],
      "thunder_axe": [
        "雷暴斧",
        "命中向附近敌人传递电弧（伤 36 · 攻速 1.4/秒）"
      ],
      "solar_cleaver": [
        "曜金巨刃",
        "炽热斩击灼烧敌人（伤 37 · 攻速 1.7/秒）"
      ],
      "dust_revolver": [
        "尘暴左轮",
        "精确单发，高速金属弹（伤 14 · 攻速 2.3/秒）"
      ],
      "reed_carbine": [
        "苇叶卡宾",
        "轻量短点射（伤 9×2 · 攻速 3.2/秒）"
      ],
      "ash_shotgun": [
        "灰烬霰铳",
        "宽角慢速散弹（伤 8×7 · 攻速 1.2/秒）"
      ],
      "tide_sprayer": [
        "潮汐喷枪",
        "扇面水晶碎片（伤 5×5 · 攻速 2.1/秒）"
      ],
      "frost_repeater": [
        "霜环连发枪",
        "冰晶连射使目标减速（伤 11×2 · 攻速 4.2/秒）"
      ],
      "echo_blaster": [
        "回声震荡器",
        "缓速音波扩散（伤 9×4 · 攻速 1.7/秒）"
      ],
      "singularity_rifle": [
        "奇点射线枪",
        "极慢单束激光穿透（伤 30 · 攻速 1.1/秒）"
      ],
      "aurora_cannon": [
        "极光聚能炮",
        "高能单束爆裂激光（伤 38 · 攻速 1.0/秒）"
      ],
      "starfall_bow": [
        "璀璨星落弓",
        "追猎星矢（伤 36 · 攻速 1.5/秒）"
      ],
      "quartz_rifle": [
        "石英步枪",
        "快速单发穿晶弹（伤 17 · 攻速 2.8/秒）"
      ],
      "ember_knife": [
        "余火短匕",
        "短促扇形火花（伤 22 · 攻速 3.0/秒）"
      ],
      "tidal_spear": [
        "潮汐长矛",
        "远距离精准突刺（伤 27 · 攻速 2.0/秒）"
      ],
      "obsidian_axe": [
        "黑曜战斧",
        "沉重弧形劈砍（伤 35 · 攻速 1.2/秒）"
      ],
      "lumen_whip": [
        "流明光鞭",
        "大范围柔性光刃（伤 28 · 攻速 2.2/秒）"
      ],
      "pebble_popper": [
        "砂砾手铳",
        "低耗能高速单发（伤 11 · 攻速 2.7/秒）"
      ],
      "scrap_crossbow": [
        "锈钉短弩",
        "锈钉精准穿刺（伤 15 · 攻速 1.9/秒）"
      ],
      "flare_tube": [
        "信号焰管",
        "慢速燃烧散弹（伤 8×4 · 攻速 1.4/秒）"
      ],
      "alloy_knife": [
        "薄钢折刀",
        "快速宽角斩（伤 18 · 攻速 2.9/秒）"
      ],
      "survey_spear": [
        "测绘长钎",
        "远距精准突刺（伤 21 · 攻速 2.0/秒）"
      ],
      "ivy_repeater": [
        "藤脉连弩",
        "双发腐蚀藤刺（伤 11×2 · 攻速 2.7/秒）"
      ],
      "current_shotgun": [
        "流电霰铳",
        "五枚电荷宽角散射（伤 9×5 · 攻速 1.4/秒）"
      ],
      "spring_carbine": [
        "弹簧卡宾",
        "稳定的三点连射（伤 10×3 · 攻速 2.4/秒）"
      ],
      "acid_cleaver": [
        "腐叶砍斧",
        "宽角腐蚀重斩（伤 26 · 攻速 1.5/秒）"
      ],
      "cloud_staff": [
        "云絮法杖",
        "三枚漂移能量球（伤 10×3 · 攻速 1.8/秒）"
      ],
      "frost_lance": [
        "寒潮穿枪",
        "冰晶穿透并减速（伤 26 · 攻速 1.7/秒）"
      ],
      "echo_pulse": [
        "回声脉冲器",
        "音浪三连发（伤 12×3 · 攻速 2.3/秒）"
      ],
      "arc_lantern": [
        "雷弧灯笼",
        "电球在敌群连锁（伤 16×2 · 攻速 1.6/秒）"
      ],
      "glass_bow": [
        "琉璃长弓",
        "四片玻璃箭穿甲（伤 13×4 · 攻速 1.8/秒）"
      ],
      "gyro_blade": [
        "陀螺环刃",
        "近身圆弧双斩（伤 29 · 攻速 1.9/秒）"
      ],
      "null_carbine": [
        "零域卡宾",
        "高速精确穿透弹（伤 31 · 攻速 1.8/秒）"
      ],
      "prism_fan": [
        "棱面散射仪",
        "七束棱光交叉（伤 12×7 · 攻速 1.4/秒）"
      ],
      "quake_hammer": [
        "震域重锤",
        "大范围震荡重击（伤 40 · 攻速 1.1/秒）"
      ],
      "phase_needle": [
        "相位毒针",
        "高速连穿弹（伤 25 · 攻速 2.3/秒）"
      ],
      "comet_scythe": [
        "彗尾镰",
        "长弧紫色切割（伤 35 · 攻速 1.6/秒）"
      ],
      "solar_array": [
        "日珥阵列",
        "多束灼热日光（伤 15×5 · 攻速 2.1/秒）"
      ],
      "thunder_crown": [
        "雷冠发射器",
        "四发连锁电弧（伤 18×4 · 攻速 1.9/秒）"
      ],
      "royal_blaster": [
        "王权聚能炮",
        "巨弹范围爆裂（伤 41 · 攻速 1.0/秒）"
      ],
      "gilded_halberd": [
        "鎏金战戟",
        "大范围长柄横扫（伤 42 · 攻速 1.5/秒）"
      ],
      "ember_seraph": [
        "炽天使羽刃",
        "火羽迅速连斩（伤 33 · 攻速 2.3/秒）"
      ],
      "rupture_cannon": [
        "裂界巨炮",
        "炮弹爆炸并分裂（伤 45 · 攻速 1.0/秒）"
      ],
      "abyss_loom": [
        "深渊织机",
        "六线暗红束流（伤 17×6 · 攻速 1.8/秒）"
      ],
      "crimson_orbit": [
        "绯红环炮",
        "旋转能量弹（伤 37×2 · 攻速 1.2/秒）"
      ],
      "bloodmoon_glaive": [
        "血月偃月刀",
        "血月远弧斩（伤 45 · 攻速 1.5/秒）"
      ],
      "terminal_spear": [
        "终端贯枪",
        "极远距直线贯穿（伤 45 · 攻速 1.4/秒）"
      ],
      "nova_requiem": [
        "星葬挽歌",
        "星核爆裂并扩散（伤 46×2 · 攻速 1.2/秒）"
      ],
      "chrono_lance": [
        "时凝圣枪",
        "光矛令目标迟缓（伤 44 · 攻速 1.7/秒）"
      ],
      "lifeweaver": [
        "生命织梭",
        "命中时回复生命（伤 30×3 · 攻速 2.4/秒）"
      ],
      "prism_ascendant": [
        "万象棱镜",
        "光束连锁敌人（伤 42×2 · 攻速 1.6/秒）"
      ],
      "orbit_mirror": [
        "引力镜环",
        "命中产生吸引场（伤 43×2 · 攻速 1.4/秒）"
      ]
    };

    D.WEAPON_CODEX = WEAPON_CODEX;

    var MATERIAL_CODEX = {
      "scrap": [
        "废铁",
        "污染物里捡到的金属碎片，最基础的强化料"
      ],
      "fiber": [
        "纤维束",
        "韧性极佳的合成纤维，常见于低级容器"
      ],
      "circuit": [
        "电路板",
        "还能用的控制核心，精英怪身上常有"
      ],
      "crystal": [
        "污染结晶",
        "凝固的污染能量，触碰有轻微刺痛"
      ],
      "alloy": [
        "合金锭",
        "高强度合金，只有首领级才掉落"
      ],
      "core": [
        "协议核心",
        "旧世界的智能核心，武器进化的关键"
      ],
      "prism": [
        "棱镜晶核",
        "折射污染的奇异结晶，璀璨级强化的必需品"
      ],
      "relic": [
        "遗物碎片",
        "不明文明的残片，据说能拼出什么东西"
      ]
    };

    D.MATERIAL_CODEX = MATERIAL_CODEX;

    var TALENTS = {
      "dmg_up": {
        "name": "锐化弹头",
        "desc": "伤害 +15%",
        "kind": "stat",
        "stat": "dmg_mul",
        "val": 0.15,
        "color": [
          255,
          140,
          120
        ]
      },
      "rate_up": {
        "name": "快速击发",
        "desc": "射速 +12%",
        "kind": "stat",
        "stat": "rate_mul",
        "val": 0.12,
        "color": [
          255,
          210,
          120
        ]
      },
      "hp_up": {
        "name": "强化体魄",
        "desc": "生命上限 +2 并回满",
        "kind": "stat",
        "stat": "max_hp",
        "val": 2,
        "color": [
          226,
          90,
          100
        ]
      },
      "spd_up": {
        "name": "轻装",
        "desc": "移动速度 +10%",
        "kind": "stat",
        "stat": "spd_mul",
        "val": 0.1,
        "color": [
          120,
          220,
          240
        ]
      },
      "energy_up": {
        "name": "能量扩容",
        "desc": "能量上限 +25",
        "kind": "stat",
        "stat": "max_energy",
        "val": 25,
        "color": [
          100,
          180,
          255
        ]
      },
      "regen_up": {
        "name": "再生协议",
        "desc": "每秒回血 +0.4",
        "kind": "stat",
        "stat": "hp_regen",
        "val": 0.4,
        "color": [
          140,
          240,
          160
        ]
      },
      "crit_up": {
        "name": "精密瞄具",
        "desc": "暴击率 +12%",
        "kind": "stat",
        "stat": "crit",
        "val": 0.12,
        "color": [
          255,
          180,
          90
        ]
      },
      "dash_up": {
        "name": "疾风步",
        "desc": "冲刺冷却 -30%",
        "kind": "stat",
        "stat": "dash_cd_mul",
        "val": -0.3,
        "color": [
          180,
          200,
          255
        ]
      },
      "magnet_up": {
        "name": "引力场",
        "desc": "拾取范围 +50%",
        "kind": "stat",
        "stat": "magnet_mul",
        "val": 0.5,
        "color": [
          200,
          220,
          140
        ]
      },
      "luck_up": {
        "name": "幸运星",
        "desc": "掉落与宝箱品质提升",
        "kind": "stat",
        "stat": "luck",
        "val": 0.35,
        "color": [
          255,
          230,
          140
        ]
      },
      "pierce_add": {
        "name": "贯穿",
        "desc": "子弹额外穿透 +1",
        "kind": "stat",
        "stat": "pierce",
        "val": 1,
        "color": [
          200,
          140,
          255
        ]
      },
      "thorns": {
        "name": "反伤甲",
        "desc": "受击时反弹 40% 伤害",
        "kind": "flag",
        "flag": "thorns",
        "color": [
          180,
          180,
          200
        ]
      },
      "lifesteal": {
        "name": "汲取",
        "desc": "击杀时有 12% 概率回血",
        "kind": "flag",
        "flag": "lifesteal",
        "color": [
          226,
          100,
          130
        ]
      },
      "aoe_bullet": {
        "name": "崩解弹",
        "desc": "子弹命中时产生小范围爆炸",
        "kind": "flag",
        "flag": "aoe_bullet",
        "color": [
          255,
          160,
          80
        ]
      },
      "shield": {
        "name": "应急护盾",
        "desc": "每层开始获得 1 次免伤",
        "kind": "flag",
        "flag": "shield",
        "color": [
          120,
          200,
          255
        ]
      },
      "pur_resist": {
        "name": "滤芯装甲",
        "desc": "污染侵蚀与减益整体 -25%",
        "kind": "stat",
        "stat": "pur_resist",
        "val": 0.25,
        "color": [
          140,
          230,
          190
        ]
      },
      "pur_purge": {
        "name": "净化循环",
        "desc": "每 6 秒自动清除一次侵蚀累积",
        "kind": "flag",
        "flag": "pur_purge",
        "color": [
          120,
          250,
          210
        ]
      },
      "pur_ward": {
        "name": "污染共鸣",
        "desc": "污染浓度每 10%，伤害 +3%",
        "kind": "flag",
        "flag": "pur_ward",
        "color": [
          200,
          160,
          250
        ]
      },
      "trap_ward": {
        "name": "无害通行",
        "desc": "免疫所有陷阱伤害与减速",
        "kind": "flag",
        "flag": "trap_ward",
        "color": [
          117,
          244,
          198
        ]
      },
      "phase_step": {
        "name": "相位步",
        "desc": "冲刺时穿过墙体与掩体",
        "kind": "flag",
        "flag": "phase_step",
        "color": [
          195,
          153,
          250
        ]
      },
      "auto_collect": {
        "name": "自动拾荒",
        "desc": "自动收集房间内的金币与补给",
        "kind": "flag",
        "flag": "auto_collect",
        "color": [
          247,
          220,
          114
        ]
      }
    };

    D.TALENTS = TALENTS;

    var TALENT_ORDER = [
      "dmg_up",
      "rate_up",
      "hp_up",
      "spd_up",
      "energy_up",
      "regen_up",
      "crit_up",
      "dash_up",
      "magnet_up",
      "luck_up",
      "pierce_add",
      "thorns",
      "lifesteal",
      "aoe_bullet",
      "shield",
      "pur_resist",
      "pur_purge",
      "pur_ward",
      "trap_ward",
      "phase_step",
      "auto_collect"
    ];

    D.TALENT_ORDER = TALENT_ORDER;

    var ENEMY_STATS = {
      "scatter_raider": {
        "hp": 38,
        "speed": 55,
        "contact": 1.0,
        "type": "small"
      },
      "beam_raider": {
        "hp": 38,
        "speed": 55,
        "contact": 1.0,
        "type": "small"
      },
      "rifle_raider": {
        "hp": 38,
        "speed": 55,
        "contact": 1.0,
        "type": "small"
      },
      "slime": {
        "hp": 21,
        "speed": 58,
        "contact": 2.0,
        "type": "small"
      },
      "slug": {
        "hp": 36,
        "speed": 62,
        "contact": 2.0,
        "type": "small"
      },
      "crawler": {
        "hp": 17,
        "speed": 74,
        "contact": 2.0,
        "type": "small"
      },
      "slime_big": {
        "hp": 81,
        "speed": 58,
        "contact": 2.0,
        "type": "elite"
      },
      "warlord": {
        "hp": 650,
        "speed": 44,
        "contact": 3.0,
        "type": "boss"
      },
      "drone": {
        "hp": 33,
        "speed": 66,
        "contact": 1.0,
        "type": "small"
      },
      "leech": {
        "hp": 34,
        "speed": 65,
        "contact": 1.5,
        "type": "small"
      },
      "drone_big": {
        "hp": 79,
        "speed": 66,
        "contact": 1.0,
        "type": "elite"
      },
      "swarmqueen": {
        "hp": 878,
        "speed": 44,
        "contact": 3.6,
        "type": "boss"
      },
      "bomber": {
        "hp": 30,
        "speed": 76,
        "contact": 0.0,
        "type": "small"
      },
      "turret": {
        "hp": 41,
        "speed": 11,
        "contact": 1.0,
        "type": "small"
      },
      "bomber_big": {
        "hp": 72,
        "speed": 76,
        "contact": 0.0,
        "type": "elite"
      },
      "mech": {
        "hp": 1138,
        "speed": 44,
        "contact": 4.2,
        "type": "boss"
      },
      "spore": {
        "hp": 41,
        "speed": 34,
        "contact": 1.5,
        "type": "small"
      },
      "wraith": {
        "hp": 38,
        "speed": 58,
        "contact": 1.5,
        "type": "small"
      },
      "wraith_big": {
        "hp": 91,
        "speed": 58,
        "contact": 1.5,
        "type": "elite"
      },
      "protocol": {
        "hp": 1144,
        "speed": 44,
        "contact": 4.8,
        "type": "boss"
      },
      "origin": {
        "hp": 1602,
        "speed": 44,
        "contact": 4.8,
        "type": "bigboss"
      },
      "rockworm": {
        "hp": 41,
        "speed": 68,
        "contact": 2.0,
        "type": "small"
      },
      "minebot": {
        "hp": 36,
        "speed": 76,
        "contact": 0.0,
        "type": "small"
      },
      "slime_big_m": {
        "hp": 109,
        "speed": 58,
        "contact": 2.0,
        "type": "elite"
      },
      "foreman": {
        "hp": 975,
        "speed": 44,
        "contact": 3.9,
        "type": "boss"
      },
      "frostbite": {
        "hp": 41,
        "speed": 31,
        "contact": 1.5,
        "type": "small"
      },
      "spore_big": {
        "hp": 98,
        "speed": 34,
        "contact": 1.5,
        "type": "elite"
      },
      "specimen": {
        "hp": 1268,
        "speed": 44,
        "contact": 4.5,
        "type": "boss"
      },
      "purifier": {
        "hp": 50,
        "speed": 51,
        "contact": 2.0,
        "type": "small"
      },
      "sprite": {
        "hp": 32,
        "speed": 70,
        "contact": 1.5,
        "type": "small"
      },
      "guardian": {
        "hp": 1008,
        "speed": 44,
        "contact": 4.0,
        "type": "boss"
      },
      "mimic": {
        "hp": 122,
        "speed": 92,
        "contact": 2.0,
        "type": "rare"
      },
      "wanderer": {
        "hp": 62,
        "speed": 78,
        "contact": 0.0,
        "type": "rare"
      },
      "lucky_treasure": {
        "hp": 70,
        "speed": 64,
        "contact": 0.0,
        "type": "rare"
      },
      "crawler_big": {
        "hp": 97,
        "speed": 58,
        "contact": 2.0,
        "type": "elite"
      },
      "leech_big": {
        "hp": 109,
        "speed": 58,
        "contact": 1.5,
        "type": "elite"
      },
      "turret_big": {
        "hp": 103,
        "speed": 66,
        "contact": 1.0,
        "type": "elite"
      },
      "rockworm_big": {
        "hp": 112,
        "speed": 62,
        "contact": 2.0,
        "type": "elite"
      },
      "frostbite_big": {
        "hp": 123,
        "speed": 34,
        "contact": 1.5,
        "type": "elite"
      },
      "guardian_big": {
        "hp": 130,
        "speed": 62,
        "contact": 2.0,
        "type": "elite"
      },
      "spore_big_m": {
        "hp": 128,
        "speed": 34,
        "contact": 1.5,
        "type": "elite"
      },
      "crust_sentinel": {
        "hp": 520,
        "speed": 44,
        "contact": 3.0,
        "type": "boss"
      },
      "sewer_serpent": {
        "hp": 702,
        "speed": 44,
        "contact": 3.6,
        "type": "boss"
      },
      "facility_smelter": {
        "hp": 910,
        "speed": 44,
        "contact": 4.2,
        "type": "boss"
      },
      "mine_excavator": {
        "hp": 780,
        "speed": 44,
        "contact": 3.9,
        "type": "boss"
      },
      "lab_cryowarden": {
        "hp": 1014,
        "speed": 44,
        "contact": 4.5,
        "type": "boss"
      },
      "gift_bloom": {
        "hp": 806,
        "speed": 44,
        "contact": 4.0,
        "type": "boss"
      }
    };

    D.ENEMY_STATS = ENEMY_STATS;

    /* ---- hazard.py（陷阱正式名，供叙事绑定卡用） ---- */
    var TRAP_SPEC = {
      "spike": {
        "name": "地刺",
        "color": [
          196,
          196,
          210
        ],
        "dmg": 3,
        "period": 1.6,
        "active": 0.7,
        "radius": 13,
        "w": 34
      },
      "poison": {
        "name": "毒池",
        "color": [
          128,
          214,
          96
        ],
        "dmg": 1.4,
        "period": 0.55,
        "active": 0.5,
        "radius": 17,
        "w": 26,
        "slow": 0.55
      },
      "shock": {
        "name": "电场",
        "color": [
          120,
          200,
          255
        ],
        "dmg": 2.4,
        "period": 2.1,
        "active": 0.45,
        "radius": 16,
        "w": 16
      },
      "slow": {
        "name": "泥沼",
        "color": [
          140,
          122,
          88
        ],
        "dmg": 0.0,
        "period": 99.0,
        "active": 99.0,
        "radius": 18,
        "w": 18,
        "slow": 0.48
      },
      "flame": {
        "name": "喷焰口",
        "color": [
          255,
          146,
          66
        ],
        "dmg": 3.6,
        "period": 2.4,
        "active": 0.9,
        "radius": 14,
        "w": 12
      }
    };

    D.TRAP_SPEC = TRAP_SPEC;

    /* ---- 纯函数：与 Python 侧逻辑保持一致 ---- */

    // 货币持有上限（1.3 需求 3：超出后不再增加）
    // 值由 tools/gen_data_js.py 从 gamedata.py 注入，勿手改
    D.COIN_CAP = 9999999;
    D.DIAMOND_CAP = 9999;
    D.clampCoin = function (v) {
        return Math.max(0, Math.min(D.COIN_CAP, Math.trunc(v) || 0));
    };
    D.clampDiamond = function (v) {
        return Math.max(0, Math.min(D.DIAMOND_CAP, Math.trunc(v) || 0));
    };
    // 加金币并封顶 -> [新值, 实际入账]
    D.addCoin = function (cur, gain) {
        cur = D.clampCoin(cur || 0);
        gain = Math.trunc(gain) || 0;
        if (gain <= 0) { return [cur, 0]; }
        var v = D.clampCoin(cur + gain);
        return [v, v - cur];
    };

    // 武器品质升级花费 -> [金币, {材料: 数量}] 或 null（已满级）
    D.upgradeCost = function (q, lv) {
        var qq = D.QUALITIES[q];
        if (!qq || lv >= qq.max_lv) { return null; }
        var coins = qq.up[lv];
        var mats = {};
        var keys = Object.keys(qq.mats);
        for (var i = 0; i < keys.length; i++) {
            mats[keys[i]] = qq.mats[keys[i]][lv];
        }
        return [coins, mats];
    };
    D.isMax = function (q, lv) {
        var qq = D.QUALITIES[q];
        return !qq || lv >= qq.max_lv;
    };

    // 解锁条件判定 -> [ok, 文案]
    D.collectProgress = function (prof, key) {
        var c = D.CHARACTERS[key], u = c && c.unlock;
        var need = u && u[0] === 'collect' ? Number(u[1]) : 0;
        var valid = D.COLLECT_ORDER || [], seen = {}, have = 0;
        for (var i = 0; i < ((prof && prof.collects) || []).length; i++) {
            var item = prof.collects[i];
            if (valid.indexOf(item) >= 0 && !seen[item]) { seen[item] = true; have++; }
        }
        return [have, need];
    };
    D.syncCollectCharacters = function (prof) {
        var added = [], order = D.CHAR_ORDER || [];
        prof.chars = prof.chars || ['scout'];
        for (var i = 0; i < order.length; i++) {
            var key = order[i], c = D.CHARACTERS[key], u = c && c.unlock;
            if (u && u[0] === 'collect' && prof.chars.indexOf(key) < 0 &&
                    D.collectProgress(prof, key)[0] >= Number(u[1])) {
                prof.chars.push(key); added.push(key);
            }
        }
        return added;
    };
    D.unlockText = function (key, prof) {
        var c = D.CHARACTERS[key];
        if (!c) { return ''; }
        var u = c.unlock;
        if (u === null || u === undefined) { return '初始角色'; }
        if (u[0] === 'collect') {
            var progress = D.collectProgress(prof, key);
            return '收集品 ' + progress[0] + '/' + progress[1] + '（点击查看）';
        }
        var need = u[0] === 'craft' ? u[1] : u[2];
        var parts = [], ks = Object.keys(need);
        for (var i = 0; i < ks.length; i++) {
            var m = D.MATERIALS[ks[i]];
            parts.push((m ? m[0] : ks[i]) + ' ×' + need[ks[i]]);
        }
        var base = u[0] === 'coin' ? u[1] + ' 金币' :
            (u[0] === 'diamond' ? u[1] + ' 钻石' : u[2] + ' 金币');
        return base + ' + ' + parts.join('  ');
    };
    D.canUnlock = function (prof, key) {
        var c = D.CHARACTERS[key];
        if (!c) { return [false, '角色不存在']; }
        if ((prof.chars || []).indexOf(key) >= 0) { return [false, '已解锁']; }
        var u = c.unlock;
        if (u === null || u === undefined) { return [true, '']; }
        if (u[0] === 'collect') {
            var progress = D.collectProgress(prof, key);
            return [progress[0] >= progress[1],
                '收集品进度 ' + progress[0] + '/' + progress[1]];
        }
        if (u[0] === 'coin') {
            if ((prof.coins || 0) < u[1]) {
                return [false, '还差 ' + (u[1] - (prof.coins || 0)) + ' 金币'];
            }
        }
        if (u[0] === 'diamond') {
            if ((prof.diamonds || 0) < u[1]) {
                return [false, '还差 ' + (u[1] - (prof.diamonds || 0)) + ' 钻石'];
            }
        }
        if (u[0] === 'craft' && (prof.coins || 0) < u[2]) {
            return [false, '还差 ' + (u[2] - (prof.coins || 0)) + ' 金币'];
        }
        var need = u[0] === 'craft' ? u[1] : u[2], have = prof.materials || {};
        for (var k in need) {
            if (Object.prototype.hasOwnProperty.call(need, k)) {
                if ((have[k] || 0) < need[k]) {
                    var mm = D.MATERIALS[k];
                    return [false, '还差 ' + (need[k] - (have[k] || 0)) + ' ' +
                            (mm ? mm[0] : k)];
                }
            }
        }
        return [true, ''];
    };
    D.doUnlock = function (prof, key) {
        var r = D.canUnlock(prof, key);
        if (!r[0]) { return false; }
        var u = D.CHARACTERS[key].unlock;
        if (u && u[0] === 'collect') {
            return D.syncCollectCharacters(prof).indexOf(key) >= 0 ||
                (prof.chars || []).indexOf(key) >= 0;
        }
        if (u) {
            if (u[0] === 'coin') { prof.coins -= u[1]; }
            else if (u[0] === 'diamond') { prof.diamonds -= u[1]; }
            else { prof.coins -= u[2]; }
            var need = u[0] === 'craft' ? u[1] : u[2];
            for (var k in need) {
                if (Object.prototype.hasOwnProperty.call(need, k)) {
                    prof.materials[k] = (prof.materials[k] || 0) - need[k];
                }
            }
        }
        prof.chars = prof.chars || [];
        prof.chars.push(key);
        return true;
    };

    // 技能 / 被动表是三元组 [名称, 描述, 满级]，这里统一取字段
    function _skillMeta(k) {
        var s = D.SKILLS[k];
        if (!s) { return null; }
        return { key: k, name: s[0], desc: s[1], max_lv: Math.trunc(s[2]) };
    }
    function _passiveMeta(k) {
        var p = D.PASSIVES[k];
        if (!p) { return null; }
        return { key: k, name: p[0], desc: p[1], max_lv: Math.trunc(p[2]) };
    }
    // 技能 / 被动升级花费（与 Python gamedata.skill_cost / passive_cost 同源）
    D.skillCost = function (key, lv) {
        var s = _skillMeta(key);
        if (!s || lv >= s.max_lv) { return null; }
        var base = 240 + lv * 220;
        if (lv < 2) {
            return [base, { scrap: 2 + lv, fiber: 1 + lv }];
        }
        return [base,
                { circuit: 1 + Math.floor((lv - 2) / 2), crystal: 1 + Math.floor((lv - 2) / 3) }];
    };
    D.passiveCost = function (key, lv) {
        var p = _passiveMeta(key);
        if (!p || lv >= p.max_lv) { return null; }
        var base = 360 + lv * 280;
        if (lv < 2) {
            return [base, { circuit: 1 + lv, crystal: 1 + lv }];
        }
        return [base,
                { alloy: 1 + Math.floor((lv - 2) / 2), core: 1 + Math.floor((lv - 2) / 3) }];
    };

    // 难度：全局严格单调递增（按全局关卡序号插值）
    D.difficulty = function (sceneIdx, stageIdx, perScene) {
        perScene = perScene || D.STAGES_PER_SCENE;
        var g = sceneIdx * perScene + stageIdx;
        return [1.0 + g * 0.045, 1.0 + g * 0.062];
    };
    // 第 3 关小 Boss / 第 5 关大 Boss
    D.stageKind = function (stageIdx) {
        if (stageIdx === 2) { return 'miniboss'; }
        if (stageIdx === 4) { return 'boss'; }
        return 'normal';
    };
    D.totalStages = function () {
        return (D.MAIN.length + Object.keys(D.DUNGEONS).length + 1) *
               D.STAGES_PER_SCENE;
    };
    D.allScenes = function () {
        var out = D.MAIN.slice();
        for (var k in D.DUNGEONS) {
            if (Object.prototype.hasOwnProperty.call(D.DUNGEONS, k)) { out.push(k); }
        }
        out.push(D.BONUS);
        return out;
    };
    D.sceneOrder = function (prof) {
        var out = D.MAIN.slice();
        var dks = Object.keys(D.DUNGEONS);
        for (var i = 0; i < dks.length; i++) {
            // 副本解锁后插到它前置场景的**后面**（与 Python 侧一致）
            if ((prof.unlocked_dungeons || []).indexOf(dks[i]) >= 0) {
                var after = D.DUNGEONS[dks[i]].after;
                var at = out.indexOf(after);
                if (at < 0) { out.push(dks[i]); } else { out.splice(at + 1, 0, dks[i]); }
            }
        }
        if (prof.bonus_unlocked) { out.push(D.BONUS); }
        return out;
    };

    // ---- 场景推进（与 progress.advance / next_stage / start_scene 对齐）
    // 返回 ['next'|'scene_clear'|'game_clear', payload]
    D.advance = function (prof) {
        var run = prof.run;
        if (!run) { return ['next', null]; }
        var scene = run.scene, st = Math.floor(run.stage_idx || 0);
        if (st + 1 < D.STAGES_PER_SCENE) {
            return ['next', { scene: scene, stage_idx: st + 1 }];
        }
        if ((prof.cleared_scenes || []).indexOf(scene) < 0) {
            prof.cleared_scenes = (prof.cleared_scenes || []).concat([scene]);
        }
        if (scene === D.BONUS) {
            prof.run = null;
            prof.main_done = true;
            return ['game_clear', { scene: scene }];
        }
        if (scene === D.MAIN[D.MAIN.length - 1]) {
            prof.main_done = true;
            return ['scene_clear', { scene: scene, finale: true }];
        }
        return ['scene_clear', { scene: scene }];
    };
    D.resetCycle = function (prof) {
        var best = prof.best_scene_prog || (prof.best_scene_prog = {});
        var current = prof.scene_prog || {};
        Object.keys(current).forEach(function (key) {
            best[key] = Math.max(Number(best[key] || 0), Number(current[key] || 0));
        });
        prof.scene_prog = {};
        prof.run = null;
        prof.run_checkpoint = null;
        prof.chapter = 0;
        prof.stage = 0;
    };
    D.nextStage = function (prof, sceneKey, stageIdx) {
        var order = D.sceneOrder(prof);
        var idx = order.indexOf(sceneKey);
        if (idx < 0) { return false; }
        prof.run = {
            scene: sceneKey, scene_idx: idx, stage_idx: Math.floor(stageIdx),
            diff: D.difficulty(idx, Math.floor(stageIdx)),
            kind: D.stageKind(Math.floor(stageIdx)),
            intro: D.sceneStageName(Math.floor(stageIdx)), floors: 1
        };
        prof.chapter = idx;
        prof.stage = Math.floor(stageIdx);
        if ((prof.visited_scenes || []).indexOf(sceneKey) < 0) {
            prof.visited_scenes = (prof.visited_scenes || []).concat([sceneKey]);
        }
        return true;
    };
    D.startScene = function (prof, sceneKey) {
        return D.nextStage(prof, sceneKey, 0);
    };
    D.sceneStageName = function (stageIdx) {
        var k = D.stageKind(stageIdx);
        if (k === 'miniboss') { return '第 ' + (stageIdx + 1) + ' 关 · 精英哨点'; }
        if (k === 'boss') { return '第 ' + (stageIdx + 1) + ' 关 · 底层核心'; }
        return '第 ' + (stageIdx + 1) + ' 关';
    };
    D.sceneInfo = function (key) {
        return D.CHAPTER_STORY[key] || { name: key, sub: String(key).toUpperCase(),
                                         enter: [], clear: [], tint: [140, 140, 140] };
    };
    // 奖励副本：金币支付（需求）
    D.bonusUnlockable = function (prof) {
        return !prof.bonus_unlocked &&
            (prof.cleared_scenes || []).indexOf(D.MAIN[D.MAIN.length - 1]) >= 0;
    };
    D.bonusPrice = function () { return D.BONUS_PRICE; };
    D.bonusFunds = function (prof) {
        return [prof.coins || 0, prof.diamonds || 0,
                D.BONUS_PRICE, D.BONUS_PRICE_DIA || 0];
    };
    D.canBuyBonus = function (prof, want) {
        var f = D.bonusFunds(prof);
        var moneyOk = f[0] >= f[2] && f[1] >= f[3];
        if (!want) { return moneyOk; }
        return D.bonusUnlockable(prof) && moneyOk;
    };
    D.bonusMissing = function (prof) {
        var f = D.bonusFunds(prof);
        return [Math.max(0, f[2] - f[0]), Math.max(0, f[3] - f[1])];
    };
    D.buyBonus = function (prof) {
        if (!D.canBuyBonus(prof, true)) { return false; }
        var f = D.bonusFunds(prof);
        if (f[2]) { prof.coins = f[0] - f[2]; }
        if (f[3]) { prof.diamonds = f[1] - f[3]; }
        prof.bonus_unlocked = true;
        return true;
    };

    // ---- 经济曲线（与 chapter.coin_value 对齐）
    // 单枚金币面值随全局关卡序号递增
    D.coinValue = function (sceneIdx, stageIdx, perScene) {
        perScene = perScene || D.STAGES_PER_SCENE;
        var g = Math.max(0, sceneIdx) * perScene + Math.max(0, stageIdx);
        return Math.round(D.COIN_BASE + g * D.COIN_STEP);
    };
    D.sceneIndexOf = function (sceneKey) {
        var all = D.allScenes();
        var i = all.indexOf(sceneKey);
        return i < 0 ? 0 : i;
    };
    // 一关的金币掉落预算（击杀 + 首领），供 UI/平衡展示
    D.stageCoinBudget = function (sceneKey, stageIdx) {
        var si = D.sceneIndexOf(sceneKey);
        var cv = D.coinValue(si, stageIdx);
        return { face: cv, elite: Math.round(cv * D.COIN_ELITE_MUL),
                 boss: Math.round(cv * D.COIN_BOSS_MUL) };
    };

    // ---- 污染渐近减益（与 chapter.pollution 对齐）
    D.pollution = function (sceneKey, stageIdx) {
        var base = D.POLLUTION[sceneKey] || D.POLLUTION[D.MAIN[0]];
        var per = D.STAGES_PER_SCENE;
        var st = Math.max(0, Math.min(per - 1, Math.floor(stageIdx || 0)));
        var span = D.POLLUTION_STAGE_SPAN || 0;
        var k = per > 1 ? (st / (per - 1)) * span : 0;
        return {
            pct: base.pct, stage: st,
            hp_cut: Math.floor(base.hp_cut + Math.round(k * base.hp_cut)),
            spd: Math.round(base.spd * (1.0 - k * (1.0 - base.spd)) * 10000) / 10000,
            regen: Math.round(base.regen * (1.0 - k * (1.0 - base.regen)) * 10000) / 10000,
            drain: Math.round(base.drain * (1.0 + k) * 10000) / 10000,
            tint: base.tint, desc: base.desc
        };
    };
    D.pollutionLines = function (sceneKey, stageIdx) {
        var p = D.pollution(sceneKey, stageIdx), out = [];
        if (p.hp_cut > 0) { out.push('生命上限 -' + p.hp_cut); }
        if (p.spd < 0.999) {
            out.push('移速 -' + Math.round((1.0 - p.spd) * 100) + '%');
        }
        if (p.regen < 0.999) {
            out.push('回能 -' + Math.round((1.0 - p.regen) * 100) + '%');
        }
        if (p.drain > 0) { out.push('每秒侵蚀 -' + p.drain.toFixed(2)); }
        return out;
    };

    // ---- 副本准入条件（与 chapter._cond_met 对齐）
    D.condMet = function (cond, best, cleared) {
        best = best || {};
        var ok = true;
        if (cond.kills > 0) { ok = ok && ((best.kills || 0) >= cond.kills); }
        if (cond.cleared) { ok = ok && !!cleared; }
        if (cond.no_death) { ok = ok && !!best.no_death; }
        if (cond.low_hp) { ok = ok && !!best.low_hp; }
        if (cond.trap_hits !== undefined) {
            ok = ok && (best.trap_hits === undefined ||
                        best.trap_hits === null ||
                        best.trap_hits <= cond.trap_hits);
        }
        if (cond.bomber_hits !== undefined) {
            ok = ok && (best.bomber_hits === undefined ||
                        best.bomber_hits === null ||
                        best.bomber_hits <= cond.bomber_hits);
        }
        return ok;
    };
    D.dungeonProgress = function (prof, dkey) {
        var d = D.DUNGEONS[dkey];
        if (!d) { return [[], false, '', '']; }
        var cond = d.cond, after = d.after;
        var sb = (prof.scene_best || {})[after] || {};
        var cleared = (prof.cleared_scenes || []).indexOf(after) >= 0;
        var items = [];
        if (cond.cleared) {
            items.push(['通关「' + (D.CHAPTER_STORY[after] || {}).name + '」',
                cleared ? '已通关' : '未通关', '需通关', cleared]);
        }
        if (cond.kills > 0) {
            var ck = sb.kills || 0;
            items.push(['单局击杀', '' + ck, '' + cond.kills, ck >= cond.kills]);
        }
        if (cond.trap_hits !== undefined) {
            var tv = sb.trap_hits;
            items.push(['踩中陷阱',
                (tv === undefined || tv === null) ? '未记录' : (tv + ' 次'),
                '≤ ' + cond.trap_hits + ' 次',
                (tv === undefined || tv === null) ? true : (tv <= cond.trap_hits)]);
        }
        if (cond.bomber_hits !== undefined) {
            var bv = sb.bomber_hits;
            items.push(['被自爆波及',
                (bv === undefined || bv === null) ? '未记录' : (bv + ' 次'),
                '≤ ' + cond.bomber_hits + ' 次',
                (bv === undefined || bv === null) ? true : (bv <= cond.bomber_hits)]);
        }
        if (cond.no_death) {
            items.push(['零死亡通关', sb.no_death ? '已达成' : '未达成', '需达成',
                        !!sb.no_death]);
        }
        if (cond.low_hp) {
            items.push(['残血通关', sb.low_hp ? '已达成' : '未达成', '需达成',
                        !!sb.low_hp]);
        }
        return [items, D.condMet(cond, sb, cleared), d.cond_text, d.hint || ''];
    };
    // 场景最好成绩合并（只增不减 / 越小越好取最小）
    D.mergeSceneBest = function (prof, sceneKey, stats) {
        prof.scene_best = prof.scene_best || {};
        var cur = prof.scene_best[sceneKey] ||
            { kills: 0, no_death: false, items: 0, deaths: 0 };
        var up = ['kills', 'items', 'bosses'];
        for (var i = 0; i < up.length; i++) {
            var k = up[i];
            if (stats[k] !== undefined) {
                cur[k] = Math.max(cur[k] || 0, stats[k] | 0);
            }
        }
        cur.kills = cur.kills || 0;
        if (stats.no_death) { cur.no_death = true; }
        if (stats.low_hp) { cur.low_hp = true; }
        if (stats.cleared_once) { cur.cleared_once = true; }
        var down = ['trap_hits', 'bomber_hits'];
        for (var j = 0; j < down.length; j++) {
            var kk = down[j];
            if (stats[kk] !== undefined && stats[kk] !== null) {
                var v = stats[kk] | 0;
                cur[kk] = (cur[kk] === undefined || cur[kk] === null)
                    ? v : Math.min(cur[kk], v);
            }
        }
        if (stats.deaths !== undefined) {
            var dv = stats.deaths | 0;
            cur.deaths = (cur.deaths === undefined || cur.deaths === null)
                ? dv : Math.min(cur.deaths, dv);
        }
        if (cur.items === undefined) { cur.items = 0; }
        prof.scene_best[sceneKey] = cur;
        return cur;
    };
    D.scanUnlocks = function (prof) {
        var out = [], keys = Object.keys(D.DUNGEONS), i;
        prof.unlocked_dungeons = prof.unlocked_dungeons || [];
        for (i = 0; i < keys.length; i++) {
            var k = keys[i];
            if (prof.unlocked_dungeons.indexOf(k) >= 0) { continue; }
            var r = D.dungeonProgress(prof, k);
            if (!r[1]) { continue; }
            // 前置场景必须先通关
            if ((prof.cleared_scenes || [])
                    .indexOf(D.DUNGEONS[k].after) < 0) { continue; }
            prof.unlocked_dungeons.push(k);
            out.push(k);
        }
        return out;
    };

    // 收集品抽选
    D.collectPool = function (tier) {
        var out = [];
        for (var k in D.COLLECTS) {
            if (Object.prototype.hasOwnProperty.call(D.COLLECTS, k)) {
                if (D.COLLECTS[k][1] === tier) { out.push(k); }
            }
        }
        return out;
    };
    D.rollCollect = function (rng, tier) {
        var pool = D.collectPool(tier || 'common');
        if (!pool.length) { pool = D.collectPool('common'); }
        return rng.choice(pool);
    };

    // 天赋：抽三选一 / 效果应用 / 初始 stats
    D.rollTalents = function (rng, owned, n) {
        n = n || 3;
        var cnt = {};
        for (var i = 0; i < owned.length; i++) {
            cnt[owned[i]] = (cnt[owned[i]] || 0) + 1;
        }
        var pool = [];
        for (var j = 0; j < D.TALENT_ORDER.length; j++) {
            var k = D.TALENT_ORDER[j];
            if ((cnt[k] || 0) < 3) { pool.push(k); }
        }
        if (pool.length < n) { pool = D.TALENT_ORDER.slice(); }
        // Fisher-Yates 取前 n 个
        for (var m = pool.length - 1; m > 0; m--) {
            var r = rng.randint(0, m);
            var tmp = pool[m]; pool[m] = pool[r]; pool[r] = tmp;
        }
        return pool.slice(0, Math.min(n, pool.length));
    };
    D.applyTalent = function (stats, key) {
        var t = D.TALENTS[key];
        if (!t) { return false; }
        if (t.kind === 'stat') {
            if (t.stat === 'max_hp' || t.stat === 'max_energy' ||
                t.stat === 'pierce') {
                stats[t.stat] = (stats[t.stat] || 0) + t.val;
            } else {
                stats[t.stat] = (stats[t.stat] || 0.0) + t.val;
            }
        } else {
            stats.flags = stats.flags || [];
            if (stats.flags.indexOf(t.flag) < 0) { stats.flags.push(t.flag); }
        }
        return true;
    };
    D.newRunStats = function () {
        return {
            dmg_mul: 0.0, rate_mul: 0.0, spd_mul: 0.0, magnet_mul: 0.0,
            crit: 0.05, hp_regen: 0.0, luck: 0.0, dash_cd_mul: 0.0,
            max_hp: 0, max_energy: 0, pierce: 0,
            pur_resist: 0.0,
            flags: [], talents: []
        };
    };

    // ---- 场景叙事绑定（1.3 需求 2：让副本条件挂到真实机制上）
    // DUNGEONS 里已含 bind 字段，这里提供拍平函数。
    // 陷阱正式名从 HAZARD_TRAP_SPEC 查（由下方导出）。
    D.dungeonBind = function (dkey) {
        var d = D.DUNGEONS[dkey];
        return d ? (d.bind || null) : null;
    };
    D.dungeonBindCards = function (dkey) {
        var b = D.dungeonBind(dkey);
        if (!b) { return []; }
        var out = [], i, k, desc, v, spec;
        for (i = 0; i < (b.enemies || []).length; i++) {
            k = b.enemies[i][0]; desc = b.enemies[i][1];
            v = D.ENEMY_CODEX[k];
            out.push({ kind: 'enemy', key: k, name: v ? v[0] : k, desc: desc });
        }
        for (i = 0; i < (b.traps || []).length; i++) {
            k = b.traps[i][0]; desc = b.traps[i][1];
            spec = D.TRAP_SPEC ? D.TRAP_SPEC[k] : null;
            out.push({ kind: 'trap', key: k,
                       name: spec ? spec.name : k, desc: desc });
        }
        return out;
    };
    D.dungeonTip = function (dkey) {
        var b = D.dungeonBind(dkey);
        return (b && b.tip) ? b.tip : '';
    };

    // ---- 抗污染（1.3 需求：与 codex.py 对齐）
    D.PUR_RESIST_CAP = 0.85;
    D.PUR_WARD_PER = 3.0;
    D.PUR_PURGE_INTERVAL = 6.0;
    D.purResistOf = function (stats) {
        if (!stats) { return 0.0; }
        var v = parseFloat(stats.pur_resist || 0) || 0;
        return Math.max(0.0, Math.min(D.PUR_RESIST_CAP, v));
    };
    // 返回 [hp_cut, spd, regen, drain]（已按抗性折减）
    D.purTintAmount = function (pollution, stats) {
        if (!pollution) { return [0, 1.0, 1.0, 0.0]; }
        var r = D.purResistOf(stats);
        return [
            Math.round(pollution.hp_cut * (1.0 - r)),
            Math.round((1.0 - (1.0 - pollution.spd) * (1.0 - r)) * 10000) / 10000,
            Math.round((1.0 - (1.0 - pollution.regen) * (1.0 - r)) * 10000) / 10000,
            Math.round(pollution.drain * (1.0 - r) * 10000) / 10000
        ];
    };
    D.purWardBonus = function (pollution, stats) {
        if (!stats || !pollution) { return 0.0; }
        if ((stats.flags || []).indexOf('pur_ward') < 0) { return 0.0; }
        return (parseFloat(pollution.pct || 0) / 10.0) * (D.PUR_WARD_PER / 100.0);
    };
    D.hasPurPurge = function (stats) {
        return !!(stats && (stats.flags || []).indexOf('pur_purge') >= 0);
    };

    // 局内提示词条（需求 15）
    D.enemyIntro = function (key) {
        var v = D.ENEMY_CODEX[key];
        return v ? [v[0], v[3]] : null;
    };
    D.materialIntro = function (key) {
        var v = D.MATERIALS[key];
        return v ? [v[0], v[2]] : null;
    };
    D.collectIntro = function (key) {
        var v = D.COLLECTS[key];
        if (!v) { return null; }
        return [v[0] + '（' + (v[1] === 'superb' ? '珍品' : '工艺品') + '）', v[2]];
    };

    // ============================================================ 养成（需求 4/5/6/7）
    // 与 Python 侧 growth.py + gamedata.quality_for_weapon / upgrade_cost_simple 同源。
    var GROWTH_ORDER = ['white', 'green', 'blue'];
    var GROWTH_AT = { white: 0, green: 2, blue: 5 };
    D.WEAPON_LV_MAX = 8;

    // 2.5: every model has a single immutable rarity.
    D.qualityForWeapon = function (wkey, lv) {
        return (D.WEAPON_QUALITY || {})[wkey] || 'white';
    };
    D.nextGrowthAt = function (lv) {
        lv = Math.max(0, Math.trunc(lv) || 0);
        for (var i = 0; i < GROWTH_ORDER.length; i++) {
            if (lv < GROWTH_AT[GROWTH_ORDER[i]]) { return GROWTH_AT[GROWTH_ORDER[i]]; }
        }
        return null;
    };
    // 白->蓝这条线的强化开销：线性，不卡材料
    D.upgradeCostSimple = function (lv) {
        lv = Math.max(0, Math.trunc(lv) || 0);
        var mats = { scrap: 2 + lv, fiber: Math.floor(lv / 2) + 1 };
        if (lv >= 4) { mats.circuit = lv - 3; }
        return [260 + lv * 220, mats];
    };
    D.weaponLv = function (prof, wkey) {
        return Math.max(Math.trunc(((prof || {}).weapon_quality_levels || {})[wkey] || 0),
                        Math.trunc(((prof || {}).weapons || {})[wkey] || 0));
    };

    // ---- 需求 6（1.4）：品质机制。与 Python weapon.apply_quality 同源 ----
    var QUALITY_RANK_JS = { white: 0, green: 1, blue: 2, purple: 3, gold: 4,
                            red: 5, radiant: 6 };
    D.spriteKey = function (wkey) {
        return 'wpn_' + wkey;
    };
    D.qualityMech = function (q) {
        return (D.QUALITY_MECH || {})[q] || {};
    };
    // 把品质机制叠到武器规格上，返回一份新规格（不改原表）
    D.applyQuality = function (wkey, q, mul) {
        var base = D.WEAPONS ? D.WEAPONS[wkey] : null;
        if (!base) { return null; }
        var m = D.qualityMech(q);
        var rank = QUALITY_RANK_JS[q] || 0;
        var spec = {};
        for (var k in base) {
            if (Object.prototype.hasOwnProperty.call(base, k)) { spec[k] = base[k]; }
        }
        spec.dmg = base.dmg * (mul === undefined ? 1.0 : mul);
        spec.cd = base.cd / Math.max(0.05, (m.rate || 1.0));
        spec.speed = base.speed * (m.bspd || 1.0);
        spec.count = base.count + (base.melee ? 0 : (m.extra || 0));
        spec.spread = base.spread + (base.melee ? 0.0 : (m.extra ? 4.0 : 0.0));
        spec.pierce = base.pierce + (m.pierce || 0);
        // 近战专属：范围/扇形随品质变大
        spec.reach = (base.reach || 46.0) * (m.reach || 1.0) * (1.0 + 0.08 * rank);
        spec.arc = (base.arc || 100.0) * (m.arc || 1.0) * (1.0 + 0.06 * rank);
        return spec;
    };
    D.qualityMechSummary = function (q) {
        var m = D.qualityMech(q);
        var out = [];
        if (m.rate) { out.push('射速 +' + Math.round((m.rate - 1) * 100) + '%'); }
        if (m.bspd) { out.push('弹速 +' + Math.round((m.bspd - 1) * 100) + '%'); }
        if (m.extra) { out.push('弹丸 +' + m.extra); }
        if (m.pierce) { out.push('穿透 +' + m.pierce); }
        if (m.burst) { out.push('击杀迸射'); }
        if (m.split) { out.push('命中分裂'); }
        if (m.homing) { out.push('追猎弹道'); }
        return out.length ? out.join(' · ') : '基准性能';
    };

    D.weaponInfo = function (prof, wkey) {
        var spec = D.WEAPONS ? D.WEAPONS[wkey] : null;
        var lv = D.weaponLv(prof, wkey);
        var q = D.qualityForWeapon(wkey, lv);
        var qs = D.QUALITIES[q] || D.QUALITIES.white;
        var plan = (((prof || {}).blueprints) || {})[wkey];
        var craft = plan === q && !Object.prototype.hasOwnProperty.call(
            ((prof || {}).weapon_qualities) || {}, wkey);
        var cost = craft ? D.upgradeCost(plan, 0) :
            (D.QUALITY_ORDER.indexOf(q) > 2 ? D.upgradeCost(q, lv) : D.upgradeCostSimple(lv));
        return {
            key: wkey,
            name: spec ? spec.name : wkey,
            desc: spec ? spec.desc : '',
            melee: !!(spec && spec.melee),
            lv: lv, quality: q, quality_name: qs.name, quality_color: qs.color,
            mul: qs.mul * (1.0 + 0.10 * lv),
            mech: D.qualityMechSummary(q),
            mech_desc: (D.QUALITY_MECH_DESC || {})[q] || '',
            next_quality_at: null,
            cost: cost, craft: craft,
            maxed: !craft && (D.QUALITY_ORDER.indexOf(q) > 2 ? lv >= qs.max_lv :
                lv >= D.WEAPON_LV_MAX)
        };
    };
    D.weaponList = function (prof) {
        var out = [], order = D.WPN_ORDER || Object.keys(D.WEAPONS || {});
        for (var i = 0; i < order.length; i++) { out.push(D.weaponInfo(prof, order[i])); }
        return out;
    };
    // -> [ok, 原因, 金币, 材料需求]
    D.canUpgrade = function (prof, wkey) {
        if (!prof) { return [false, '无存档', 0, {}]; }
        var info = D.weaponInfo(prof, wkey);
        if (info.maxed) { return [false, '已强化到上限', 0, {}]; }
        var c = info.cost, coins = c[0], mats = c[1];
        if ((prof.coins || 0) < coins) {
            return [false, '金币不足（还差 ' + (coins - (prof.coins || 0)) + '）',
                    coins, mats];
        }
        var pm = prof.materials || {}, lack = [];
        for (var k in mats) {
            if (Object.prototype.hasOwnProperty.call(mats, k)) {
                if ((pm[k] || 0) < mats[k]) {
                    var m = D.MATERIALS[k];
                    lack.push((m ? m[0] : k) + '×' + (mats[k] - (pm[k] || 0)));
                }
            }
        }
        if (lack.length) { return [false, '材料不足（缺 ' + lack.join('、') + '）', coins, mats]; }
        return [true, '', coins, mats];
    };
    D.upgradeWeapon = function (prof, wkey) {
        var r = D.canUpgrade(prof, wkey);
        if (!r[0]) { return [false, r[1]]; }
        var coins = r[2], mats = r[3];
        prof.coins = (prof.coins || 0) - coins;
        prof.materials = prof.materials || {};
        for (var k in mats) {
            if (Object.prototype.hasOwnProperty.call(mats, k)) {
                prof.materials[k] = (prof.materials[k] || 0) - mats[k];
                if (prof.materials[k] <= 0) { delete prof.materials[k]; }
            }
        }
        var spec = D.WEAPONS ? D.WEAPONS[wkey] : null;
        var name = spec ? spec.name : wkey;
        var info = D.weaponInfo(prof, wkey);
        if (info.craft) {
            var quality = prof.blueprints[wkey];
            prof.weapon_qualities = prof.weapon_qualities || {};
            prof.weapon_quality_levels = prof.weapon_quality_levels || {};
            prof.weapon_qualities[wkey] = quality;
            prof.weapon_quality_levels[wkey] = 0;
            prof.weapon = wkey;
            return [true, '合成并装备「' + (D.QUALITIES[quality] || {}).name + '·' + name + '」'];
        }
        var high = D.QUALITY_ORDER.indexOf(info.quality) > 2;
        var levels = high ? (prof.weapon_quality_levels || (prof.weapon_quality_levels = {}))
            : (prof.weapons || (prof.weapons = {}));
        var lv = (levels[wkey] || 0) + 1;
        levels[wkey] = lv;
        var qn = (D.QUALITIES[D.qualityForWeapon(wkey, lv)] || {}).name || '';
        if (lv === 5) { return [true, '「' + name + '」强化至 Lv.' + lv + '，品质提升为「' + qn + '」']; }
        return [true, '「' + name + '」强化至 Lv.' + lv];
    };

    // 角色列表
    D.charList = function (prof) {
        prof = prof || {};
        var owned = prof.chars || ['scout'], cur = prof.char || 'scout';
        var out = [], order = D.CHAR_ORDER || Object.keys(D.CHARACTERS || {});
        for (var i = 0; i < order.length; i++) {
            var k = order[i], c = D.CHARACTERS[k];
            var isOwned = owned.indexOf(k) >= 0;
            var ok = true, reason = '';
            if (!isOwned) {
                if (!prof.chars && !prof.coins) { ok = false; reason = '尚无存档'; }
                else { var r = D.canUnlock(prof, k); ok = r[0]; reason = r[1]; }
            }
            var st = D.WEAPONS ? D.WEAPONS[c.starter] : null;
            out.push({
                key: k, name: c.name, desc: c.desc, perk: c.perk,
                hp: c.hp, spd: c.spd, energy: c.energy,
                starter: c.starter, starter_name: st ? st.name : c.starter,
                owned: isOwned, cur: (k === cur), afford: ok,
                unlock_text: D.unlockText(k, prof), reason: reason
            });
        }
        return out;
    };
    D.selectChar = function (prof, key) {
        if (!prof) { return [false, '无存档']; }
        if ((prof.chars || []).indexOf(key) < 0) { return [false, '尚未解锁该角色']; }
        prof.char = key;
        prof.weapon = D.CHARACTERS[key].starter;
        return [true, '已换上「' + (D.CHARACTERS[key] ? D.CHARACTERS[key].name : key) + '」'];
    };
    D.buyChar = function (prof, key) {
        if (!prof) { return [false, '无存档']; }
        if ((prof.chars || []).indexOf(key) >= 0) { return [false, '该角色已解锁']; }
        if (!D.doUnlock(prof, key)) {
            return [false, (D.canUnlock(prof, key) || [false, '条件不足'])[1]];
        }
        return [true, '解锁角色「' + (D.CHARACTERS[key] ? D.CHARACTERS[key].name : key) + '」'];
    };
    D.TALENT_MAX_LV = 5;

    // 技能 / 被动列表与升级
    D.skillList = function (prof) {
        var lv = (prof || {}).skills || {}, out = [];
        var order = D.SKILL_ORDER || Object.keys(D.SKILLS || {});
        for (var i = 0; i < order.length; i++) {
            var k = order[i], s = _skillMeta(k);
            if (!s) { continue; }
            var cur = Math.trunc(lv[k] || 0);
            out.push({ key: k, name: s.name, desc: s.desc, lv: cur, max: s.max_lv,
                       cost: (cur < s.max_lv ? D.skillCost(k, cur) : null) });
        }
        return out;
    };
    D.passiveList = function (prof) {
        var lv = (prof || {}).passives || {}, out = [];
        var order = D.PASSIVE_ORDER || Object.keys(D.PASSIVES || {});
        for (var i = 0; i < order.length; i++) {
            var k = order[i], p = _passiveMeta(k);
            if (!p) { continue; }
            var cur = Math.trunc(lv[k] || 0);
            out.push({ key: k, name: p.name, desc: p.desc, lv: cur, max: p.max_lv,
                       cost: (cur < p.max_lv ? D.passiveCost(k, cur) : null) });
        }
        return out;
    };
    D._canPay = function (prof, coins, mats) {
        if (!prof) { return [false, '无存档']; }
        if ((prof.coins || 0) < coins) {
            return [false, '金币不足（还差 ' + (coins - (prof.coins || 0)) + '）'];
        }
        var pm = prof.materials || {}, lack = [];
        for (var k in mats) {
            if (Object.prototype.hasOwnProperty.call(mats, k)) {
                if ((pm[k] || 0) < mats[k]) {
                    var m = D.MATERIALS[k];
                    lack.push((m ? m[0] : k) + '×' + (mats[k] - (pm[k] || 0)));
                }
            }
        }
        if (lack.length) { return [false, '材料不足（缺 ' + lack.join('、') + '）']; }
        return [true, ''];
    };
    D._pay = function (prof, coins, mats) {
        prof.coins = (prof.coins || 0) - coins;
        prof.materials = prof.materials || {};
        for (var k in mats) {
            if (Object.prototype.hasOwnProperty.call(mats, k)) {
                prof.materials[k] = (prof.materials[k] || 0) - mats[k];
                if (prof.materials[k] <= 0) { delete prof.materials[k]; }
            }
        }
    };
    D.upgradeSkill = function (prof, key) {
        var s = _skillMeta(key);
        if (!s) { return [false, '无此技能']; }
        prof.skills = prof.skills || {};
        var lv = Math.trunc(prof.skills[key] || 0);
        if (lv >= s.max_lv) { return [false, '「' + s.name + '」已满级']; }
        var c = D.skillCost(key, lv);
        var chk = D._canPay(prof, c[0], c[1] || {});
        if (!chk[0]) { return [false, chk[1]]; }
        D._pay(prof, c[0], c[1] || {});
        prof.skills[key] = lv + 1;
        return [true, '「' + s.name + '」提升至 Lv.' + (lv + 1)];
    };
    D.upgradePassive = function (prof, key) {
        var p = _passiveMeta(key);
        if (!p) { return [false, '无此被动']; }
        prof.passives = prof.passives || {};
        var lv = Math.trunc(prof.passives[key] || 0);
        if (lv >= p.max_lv) { return [false, '「' + p.name + '」已满级']; }
        var c = D.passiveCost(key, lv);
        var chk = D._canPay(prof, c[0], c[1] || {});
        if (!chk[0]) { return [false, chk[1]]; }
        D._pay(prof, c[0], c[1] || {});
        prof.passives[key] = lv + 1;
        return [true, '「' + p.name + '」提升至 Lv.' + (lv + 1)];
    };

    // 永久天赋（与局内三选一共用 TALENTS 表）
    D.talentList = function (prof) {
        var lv = (prof || {}).talent_levels || {}, out = [], order = D.TALENT_ORDER || [];
        for (var i = 0; i < order.length; i++) {
            var k = order[i], t = D.TALENTS[k];
            out.push({ key: k, name: t.name, desc: t.desc, color: t.color,
                       lv: Math.trunc(lv[k] || 0), max: D.TALENT_MAX_LV });
        }
        return out;
    };
    D.talentUpgradeCost = function (prof, key) {
        var lv = Math.trunc((((prof || {}).talent_levels || {})[key]) || 0);
        return [500 + lv * 600, { crystal: 1 + Math.floor(lv / 2) }];
    };
    D.upgradeTalent = function (prof, key) {
        var t = D.TALENTS[key];
        if (!t) { return [false, '无此天赋']; }
        prof.talent_levels = prof.talent_levels || {};
        var lv = Math.trunc(prof.talent_levels[key] || 0);
        if (lv >= D.TALENT_MAX_LV) { return [false, '「' + t.name + '」已满级']; }
        var c = D.talentUpgradeCost(prof, key);
        var chk = D._canPay(prof, c[0], c[1] || {});
        if (!chk[0]) { return [false, chk[1]]; }
        D._pay(prof, c[0], c[1] || {});
        prof.talent_levels[key] = lv + 1;
        return [true, '「' + t.name + '」提升至 Lv.' + (lv + 1)];
    };
    D.materialSummary = function (prof) {
        var pm = (prof || {}).materials || {}, out = [];
        var order = D.MAT_ORDER || Object.keys(D.MATERIALS || {});
        for (var i = 0; i < order.length; i++) {
            var k = order[i], n = Math.trunc(pm[k] || 0);
            if (n > 0) {
                var m = D.MATERIALS[k];
                out.push([k, m ? m[0] : k, m ? m[1] : 1, n]);
            }
        }
        return out;
    };

    // ---- 宝箱分级（需求 7）：与 Python gamedata.roll_chest / chest_loot 同源
    D.CHEST_ORDER = D.CHEST_ORDER || ['coin', 'heal', 'material', 'weapon',
                                      'collect'];
    D.rollChest = function (rng, floorBias, luck) {
        floorBias = floorBias || 0.0; luck = luck || 1.0;
        var pool = [], k, t, spec, w, i;
        var keys = ['coin', 'heal', 'material', 'weapon', 'collect'];
        for (i = 0; i < keys.length; i++) {
            k = keys[i];
            var tiers = ['normal', 'superb'];
            for (var j = 0; j < tiers.length; j++) {
                t = tiers[j];
                spec = (D.CHESTS[k] || {})[t];
                if (!spec) { continue; }
                w = (spec.w || 1) * luck;
                if (t === 'superb') { w *= (0.55 + floorBias * 0.4); }
                pool.push([k, t, w]);
            }
        }
        var total = 0.0;
        for (i = 0; i < pool.length; i++) { total += pool[i][2]; }
        var r = rng.random() * total, acc = 0.0;
        for (i = 0; i < pool.length; i++) {
            acc += pool[i][2];
            if (r <= acc) { return [pool[i][0], pool[i][1]]; }
        }
        return ['coin', 'normal'];
    };
    D.chestLoot = function (rng, kind, tier, floor) {
        var spec = ((D.CHESTS || {})[kind] || {})[tier] || {};
        var out = { coins: 0, diamonds: 0, heal: 0, energy: 0, mats: {},
                    quality: null };
        if (kind === 'coin') {
            var cr = spec.coin || [30, 70];
            out.coins = rng.randint(cr[0], cr[1]);
            out.diamonds = (spec.dia || 0) * rng.randint(1, 2);
        } else if (kind === 'heal') {
            var hr = spec.heal || [3, 5];
            out.heal = rng.randint(hr[0], hr[1]);
            out.energy = spec.energy || 0;
        } else if (kind === 'material') {
            var tr = spec.mat_tier || [1, 2];
            var nr = spec.mat_n || [1, 2];
            var order = D.MAT_ORDER || Object.keys(D.MATERIALS || {});
            var pool2 = [];
            for (var q = 0; q < order.length; q++) {
                var mm = D.MATERIALS[order[q]];
                var tv = mm ? Math.trunc(mm[1]) : 1;
                if (tv >= tr[0] && tv <= tr[1]) { pool2.push(order[q]); }
            }
            if (pool2.length) {
                var cnt = rng.randint(nr[0], nr[1]);
                for (var z = 0; z < cnt; z++) {
                    var kk = rng.choice(pool2);
                    out.mats[kk] = (out.mats[kk] || 0) + 1;
                }
            }
        } else if (kind === 'weapon') {
            var qo = D.QUALITY_ORDER || ['white', 'green', 'blue'];
            var qi = Math.min(spec.q_max === undefined ? 2 : spec.q_max,
                              qo.length - 1);
            out.quality = qo[Math.max(0, qi)];
        }
        return out;
    };

    window.__DATA__ = D;
})();
