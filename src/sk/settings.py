# -*- coding: utf-8 -*-
"""最后一片净土 —— 全局常量与配置"""
import math

GAME_TITLE = '余烬禁区'
GAME_SUB = 'ASHEN EXCLUSION ZONE'
VERSION = '4.0'

# ---------------- 显示 ----------------
VIEW_W, VIEW_H = 640, 360           # 逻辑分辨率（所有绘制都在这块画布上）
TILE = 32
WIN_SCALE = 2                       # 默认窗口 = 逻辑 × 2 = 1280×720
FPS = 60
MAX_DT = 1.0 / 30.0                 # dt 上限，防卡顿穿墙

# ---------------- 房间几何 ----------------
ROOM_COLS, ROOM_ROWS = 17, 11       # 含一圈外墙
ROOM_PX_W, ROOM_PX_H = ROOM_COLS * TILE, ROOM_ROWS * TILE     # 544 × 352
CAM_OFF = ((VIEW_W - ROOM_PX_W) // 2, (VIEW_H - ROOM_PX_H) // 2)   # (48, 4)
ROOM_CX, ROOM_CY = ROOM_PX_W / 2, ROOM_PX_H / 2                    # 272, 176

# 内区像素范围（不含墙）
IN_L, IN_T = 1 * TILE, 1 * TILE                 # 32, 32
IN_R, IN_B = (ROOM_COLS - 1) * TILE, (ROOM_ROWS - 1) * TILE   # 512, 320

DOOR_TILE = {                        # 方向 -> 门所在格
    'N': (8, 0),
    'S': (8, ROOM_ROWS - 1),
    'W': (0, 5),
    'E': (ROOM_COLS - 1, 5),
}
OPPOSITE = {'N': 'S', 'S': 'N', 'W': 'E', 'E': 'W'}
DIR_VEC = {'N': (0, -1), 'S': (0, 1), 'W': (-1, 0), 'E': (1, 0)}

# 从某扇门进入房间时，玩家的落点（内区一格处，避免立刻二次触发换房）
ENTRY_FROM = {
    'N': (ROOM_CX, 1 * TILE + TILE / 2),                                   # (272, 48)
    'S': (ROOM_CX, (ROOM_ROWS - 2) * TILE + TILE / 2),                     # (272, 304)
    'W': (1 * TILE + TILE / 2, ROOM_CY),                                   # (48, 176)
    'E': ((ROOM_COLS - 2) * TILE + TILE / 2, ROOM_CY),                     # (496, 176)
}

# 触发换房的越界阈值（玩家中心越过门格中点即触发）
DOOR_TRIGGER = {
    'N': lambda p: p.y < TILE * 0.55 and abs(p.x - ROOM_CX) < 43,
    'S': lambda p: p.y > ROOM_PX_H - TILE * 0.55 and abs(p.x - ROOM_CX) < 43,
    'W': lambda p: p.x < TILE * 0.55 and abs(p.y - ROOM_CY) < 43,
    'E': lambda p: p.x > ROOM_PX_W - TILE * 0.55 and abs(p.y - ROOM_CY) < 43,
}

# ---------------- 玩家 ----------------
P_MAX_HP = 12
P_MAX_ENERGY = 200.0
P_SPEED = 168.0
P_RADIUS = 11.0
P_IFRAME = 0.85                     # 受伤无敌时间
P_DASH_SPEED = 540.0
P_DASH_TIME = 0.16
P_DASH_CD = 0.80
P_ENERGY_REGEN = 0.0

# 防卡死：有移动输入却连续零位移超过该秒数，则自动脱困
STUCK_SECONDS = 1.6

# ---------------- 需求 20：打击停顿 / 受击击退 ----------------
# 打击停顿（hit-stop）：命中瞬间把 dt 冻结一小会儿，打击感显著变强。
# 数值很小（秒），且只在"打中东西"时触发。**只冻结世界（敌人/子弹/陷阱），
# 玩家移动与瞄准永远按真实 dt 走** —— 见 game.update 的注释与血泪教训。
HITSTOP_HIT = 0.020         # 普通命中
HITSTOP_KILL = 0.045        # 击杀
HITSTOP_BOSS = 0.070        # 打中首领
HITSTOP_HURT = 0.055        # 玩家受击（比击杀更重，强调"被打了"）
HITSTOP_MAX = 0.11          # 单次上限，防叠加成"卡住"
# 停顿期间世界时间的推进比例。0.06 太狠（连续命中时世界几乎静止），
# 调到 0.35：仍有明显"卡肉"顿感，但世界不会停死。
HITSTOP_SCALE = 0.35
# 冷却：两次触发之间的最小间隔。防止"每帧都命中"时 hitstop 被无限刷新，
# 导致世界长时间停留在慢速 —— 这是"打群怪时又顿又粘"的元凶。
HITSTOP_COOLDOWN = 0.09

# 受击击退
P_KNOCK_BASE = 150.0        # 基础击退速度（px/s）
P_KNOCK_PER_DMG = 22.0      # 每点伤害追加
P_KNOCK_MAX = 330.0         # 上限，避免被一次推出房间
P_KNOCK_TIME = 0.18         # 击退持续时间

# ---------------- 敌人 ----------------
E_HP_BAR_W = 26

# ---------------- 楼层 ----------------
FLOORS = 1
GRID_W, GRID_H = 5, 5

# ---------------- 配色 ----------------
C_BG = (18, 17, 24)
C_PANEL = (30, 28, 40)
C_PANEL_HI = (46, 43, 62)
C_TEXT = (232, 230, 240)
C_TEXT_DIM = (150, 146, 168)
C_GOLD = (255, 206, 74)
C_DIA = (140, 230, 255)
C_HP = (226, 62, 74)
C_ENERGY = (74, 200, 232)
C_ACCENT = (120, 220, 180)
C_WARN = (255, 138, 66)
C_BOSS = (198, 84, 220)
C_SHADOW = (0, 0, 0, 90)
C_WHITE = (255, 255, 255)
C_BLACK = (0, 0, 0)

# 房间类型配色（小地图用）
ROOM_COLOR = {
    'start': (108, 196, 255),
    'normal': (150, 146, 168),
    'treasure': (255, 206, 74),
    'heal': (226, 62, 74),
    'shop': (120, 220, 180),
    'drink': (230, 153, 110),
    'boss': (198, 84, 220),
    'cleared': (96, 108, 96),
}

# ---------------- 调试 ----------------
DEBUG = False
