# -*- coding: utf-8 -*-
"""游戏主控：状态机 / 输入 / 更新 / 渲染"""
import math
import os
import random
import time

import pygame

from . import assets as assets_mod
from . import audio as audio_mod
from . import chapter as C
from . import codex as CX
from . import enemy as enemy_mod
from . import gamedata as GD
from . import hud
from . import progress as PR
from . import save as save_mod
from . import settings as S
from . import utils as U
from . import weapon as W
from .dungeon import Dungeon, SCENE_SPAWN
from .basketball import Basketball
from .enemy import Boss
from .fx import FX
from .pickup import Pickup
from .player import Player

SAVE_NAME = '.soulknight_lite.json'      # 旧版存档名（仅用于迁移提示）


def _boot_pygame(headless=False):
    """手动初始化 pygame 子系统，**绝不用 pygame.init()**。

    [!][!] 血泪教训（"桌面端双击没反应"的根因）：
    `pygame.init()` 会顺手初始化 **joystick** 子系统。Windows 上 SDL 枚举
    手柄 / HID 设备时，如果某个设备（虚拟手柄、蓝牙残留设备、带异常 HID
    描述符的 RGB 外设、某些主板的 XInput 垫片）响应缓慢，枚举会一直阻塞
    到超时。本机实测 `joystick.init()` 单独耗时 **60.2 秒**！
    而 `pygame.init()` 发生在**建窗口之前** —— 于是双击 exe 后 60 秒内
    什么都不发生，没有窗口、没有报错，用户只会以为"打不开"。

    更隐蔽的是：`--selfcheck` 用的是 SDL dummy 驱动，joystick 初始化
    是 no-op，所以自检永远 PASS，完全掩盖了这个 bug。

    结论：我们自己按需 init —— display / font / mixer 三个就够，
    joystick 直接跳过（本项目是键鼠游戏，本来也不需要手柄）。
    """
    # 先设环境变量，挡住 HIDAPI 那套设备枚举（双保险）
    os.environ.setdefault('SDL_JOYSTICK_HIDAPI', '0')
    os.environ.setdefault('SDL_JOYSTICK_ALLOW_BACKGROUND_EVENTS', '0')

    try:
        pygame.display.init()
    except Exception:
        pass
    if not pygame.font.get_init():
        try:
            pygame.font.init()
        except Exception:
            pass
    # mixer 单独 init：任何一步出问题都只降级掉音频，不能拖垮启动
    try:
        pygame.mixer.pre_init(44100, -16, 2, 512)
        pygame.mixer.init()
    except Exception:
        try:
            pygame.mixer.init()
        except Exception:
            pass
    # 明确不碰 joystick：
    #   pygame.joystick.init()   <- 就是这行让我们在启动时卡 60 秒
    if headless:
        # 无头环境下把显示也标成已初始化，避免上层误判
        pass


class Game:
    def __init__(self, headless=False, seed=None, enable_audio=True, scale=None):
        _boot_pygame(headless)
        self.headless = headless
        self.seed = seed
        self.rng = random.Random(seed)

        # 注意：必须先建立显示模式，否则 Surface.convert_alpha() 会失败，
        # 导致所有贴图静默退化为占位图。
        self.scale = int(scale or S.WIN_SCALE)
        self.fullscreen = False
        self.window = None
        self.canvas = pygame.Surface((S.VIEW_W, S.VIEW_H))
        self.view_off = (0, 0)
        self._set_mode(self.scale, False)
        # 隐藏系统光标：游戏自己画准星，系统箭头压在准星上会挡住瞄准点
        self._cursor_hidden = False
        if not headless:
            self._set_cursor_hidden(True)

        self.assets = assets_mod.Assets()
        # 战斗音效默认开启；音乐和震动仍由玩家单独设置。
        # 音效音源由 assets 目录构建期预渲染，运行时零依赖。
        self.audio = audio_mod.Audio(
            enable=enable_audio and not headless,
            sfx_dir=os.path.join(self.assets.root, 'sfx'))
        self.music = audio_mod.Music(enable=False)
        self.vibrator = audio_mod.Vibrator(enable=False)
        self.setting = {
            'music': False, 'sfx': True, 'shake': False, 'vibrate': False,
            'joystick': 'float', 'joy_sens': 1.0,
        }
        # 按玩家设置启动（settings 从存档里读，见 _load_save）
        self._apply_audio_settings()
        self.clock = pygame.time.Clock()

        self.cam = (S.CAM_OFF[0], S.CAM_OFF[1])
        self.mouse_canvas = (S.VIEW_W / 2, S.VIEW_H / 2)
        self.show_aim = True

        # ---- 运行时状态
        self.state = 'title'
        self.running = True
        self.time = 0.0
        self.total_time = 0.0
        self.trans_fade = 0.0
        self.banner_t = 0.0
        self.banner_text = ''
        self.collection_popup = None
        self.hint_t = 0.0
        self.fire_cool = 0.0
        self.prompt = None
        self.boss = None
        self.hitstop = 0.0          # 需求 20：打击停顿剩余秒数
        self._hitstop_cd = 0.0      # 打击停顿冷却（防连续刷新）
        self.coins = 0
        self.diamonds = 0
        self.run_diamonds = 0
        self.kills = 0
        self.combo_count = 0
        self.combo_t = 0.0
        self._explode_depth = 0
        self.inp_override = None
        self.auto_fire = False
        # ---- 事件驱动的"按下键集合"（需求 防卡死/输入健壮性）
        # 有些机器 / 窗口管理器下，SDL 认为窗口未聚焦，pygame.key.get_pressed()
        # 会整表返回 False，导致"键盘完全没反应、人物钉死"。
        # 但 KEYDOWN / KEYUP 事件仍然会照常投递到事件队列。
        # 所以这里同时维护一份"由事件累积出的按键集合"，read_input 取两者并集，
        # 从根上消除"窗口焦点丢失 = 无法移动"这一类问题。
        self._held_keys = set()
        # 记录最近一次收到键盘事件的时刻（诊断用）
        self._last_key_t = -1.0

        # ---- 局外资源 / 提示（需求 4、15）
        self.diamonds = 0
        self.mats = {}
        self.toasts = []          # [{'title','sub','color','t','life'}]
        self.level_state = None   # 关卡进度（章节/场景/小关），由 progress 层填充

        # ---- 1.1 天赋 / 过场（需求 1.1-2、17）
        self.talents_owned = []   # 本局已选天赋（可叠加）
        self.run_stats = None     # 天赋累计出的数值加成
        self.pending_talents = None   # 三选一候选
        self.talent_pick = 0
        self._pending_story = None    # 三选一结束后要接的过场
        self.transition_lock = 0.0    # 过场刚结束的输入锁（防误触立刻推进）
        self.story_scene = None       # 当前过场播放的场景
        self.story_lines = []
        self.story_t = 0.0
        self.story_phase = 'stage_enter'
        self.story_title = ''
        self.story_tint = (140, 140, 140)
        self.story_page = 0
        self.pending_after = None     # 过场结束后要执行的 ('next'|'scene_clear'|'game_clear')

        # ---- 局内计数（与累计 kills 区分：run_* 只统计本关）
        self.run_kills = 0
        self.run_deaths = 0
        # ---- 需求：副本准入条件追踪（本场景本局）
        self.run_trap_hits = 0
        self.run_bomber_hits = 0
        self.run_low_hp = False      # 是否曾残血（≤3）通关本场景
        self.run_items = 0
        self._drain_acc = 0.0
        self.pollution = None
        self._stage_done = False

        # ---- 图鉴 / 收集品（需求 8、9、15）
        self.new_codex = []       # 本次新解锁的图鉴条目，供弹提示
        self.floor_item_counts = None

        self.best_floor = 0
        self.best_kills = 0
        self.store = None
        self.profile = None
        self._load_save()

        # ---- 世界
        self.dungeon = None
        self.room = None
        self.player = Player(S.ROOM_CX, S.ROOM_CY)
        self.char_skill_cd = 0.0
        self.drink_stages = {}
        self.drink_buffs = {}
        self.enemies = []
        self.bullets = []
        self.fx = FX()

        # ---- 菜单
        self.menu_items = [
            ('开始游戏', 'new'),
            ('操作说明', 'help'),
            ('音效：开' if self.audio.enabled else '音效：关', 'audio'),
            ('退出游戏', 'quit'),
        ]
        self.pause_items = [
            ('继续游戏', 'resume'),
            ('脱离卡死', 'unstuck'),
            ('立即结算', 'settle'),
            ('重新开始', 'restart'),
            ('返回主菜单', 'title'),
            ('退出游戏', 'quit'),
        ]
        self.over_items = [
            ('重新开始', 'restart'),
            ('返回主菜单', 'title'),
            ('退出游戏', 'quit'),
        ]
        self.menu_index = 0
        self.pause_index = 0
        self.over_index = 0
        self.setting_index = 0   # 需求 12：设置面板选中项
        self.prev_state = 'title'

        # ---- 存档槽选择（需求 10：个人 ID / 3 槽 / 覆盖确认）
        self.slot_index = 0
        self.slot_mode = 'pick'     # pick | create | overwrite | confirm_del
        self.slot_pending = -1      # 正在处理的槽位
        self.name_buf = ''          # 新建档时输入的名字

        # ---- 更新日志面板（需求 17：标题右下角可点开）
        self.log_scroll = 0

        # ---- 二次确认（需求 18：传送门/购买/开箱需二次按键）
        self.confirm_prompt = None   # {'title','sub','key','on_ok'}
        self.confirm_t = 0.0

        # ---- 客厅 / 关卡地图（1.0 需求 16）
        self.lobby_index = 0        # 选中的场景下标（对应 PR.scene_order）
        self.lobby_expand = False   # 是否展开了副本机制卡
        self.lobby_tab = 0          # 0 准备 / 1 养成 / 2 图鉴 / 3 展示台
        self.growth_sub = 0         # 0 角色 / 1 武器 / 2 技能被动 / 3 天赋
        self.growth_index = 0
        self.codex_cat = 0          # 图鉴分类下标
        self.codex_index = 0        # 图鉴条目下标
        self.codex_page = 0
        self.showcase_index = 0     # 展示台格子下标
        self.char_key = 'scout'
        self._lobby_cards = []      # 缓存的场景卡片热区 [(key, top, bottom)]

    # ================================================================ 便捷属性
    @property
    def props(self):
        """当前房间的可破坏道具（供子弹/爆炸系统使用）"""
        return self.room.props if self.room is not None else []

    @property
    def pickups(self):
        """当前房间的掉落物（列表本身属于房间对象，跨房间自动持久化）"""
        return self.room.pickups if self.room is not None else []

    @property
    def total_damage(self):
        return self.player.dmg_taken

    # ================================================================ 窗口
    def _set_mode(self, scale, fullscreen):
        self.scale = max(1, int(scale))
        self.fullscreen = bool(fullscreen)
        try:
            if self.fullscreen:
                info = pygame.display.Info()
                sw, sh = max(640, info.current_w), max(360, info.current_h)
                sc = max(1, min(sw // S.VIEW_W, sh // S.VIEW_H))
                self.window = pygame.display.set_mode((sw, sh), pygame.FULLSCREEN)
                self.scale = sc
                self.view_off = ((sw - S.VIEW_W * sc) // 2, (sh - S.VIEW_H * sc) // 2)
            else:
                size = (S.VIEW_W * self.scale, S.VIEW_H * self.scale)
                self.window = pygame.display.set_mode(size)
                self.view_off = (0, 0)
        except Exception:
            self.window = pygame.Surface((S.VIEW_W * self.scale, S.VIEW_H * self.scale))
            self.view_off = (0, 0)
        try:
            pygame.display.set_caption(f'{S.GAME_TITLE}  v{S.VERSION}')
        except Exception:
            pass
        # set_mode() 会重置光标可见性，切窗口 / 切全屏后必须重新隐藏
        try:
            if getattr(self, '_cursor_hidden', False):
                pygame.mouse.set_visible(False)
        except Exception:
            pass

    def toggle_fullscreen(self):
        self._set_mode(self.scale, not self.fullscreen)

    def _set_cursor_hidden(self, hidden):
        """隐藏 / 恢复系统鼠标指针。

        [!] 必须容错：某些驱动 / 无头环境下 set_visible 会抛异常，
        不能让光标问题把整个游戏拖崩。
        """
        want = bool(hidden)
        if want == getattr(self, '_cursor_hidden', False):
            return
        try:
            pygame.mouse.set_visible(not want)
            self._cursor_hidden = want
        except Exception:
            self._cursor_hidden = False

    # ================================================================ 存档
    # 需求 10：个人 ID、三个槽位、自动保存、异常退出保护。
    # 旧版把 best_floor/best_kills 写在用户主目录的单个 JSON 里；
    # 现在换成 save.py 的存档仓库（跨平台数据目录 + 原子写 + 备份）。
    def _load_save(self):
        try:
            self.store = save_mod.store()
        except Exception:
            self.store = None
        self.profile = None
        try:
            if self.store is not None:
                self.profile = self.store.current()
        except Exception:
            self.profile = None
        if self.profile is not None:
            st = self.profile.get('stats') or {}
            self.best_floor = int(st.get('best_chapter', 0))
            self.best_kills = int(st.get('kills', 0))
            self._load_settings_from_profile()
        else:
            self.best_floor = 0
            self.best_kills = 0

    def _write_save(self):
        """把局外进度落盘。任何异常都不能拖垮游戏。

        没有存档（无头测试 / 未建档）时只更新内存里的最佳记录，
        这样"最佳记录"在无档环境下也保持单调，测试与 UI 都能读到。
        """
        try:
            f = int(self.floor) if getattr(self, 'floor', None) else 0
            self.best_floor = max(self.best_floor, f)
            self.best_kills = max(self.best_kills, int(self.kills))
        except Exception:
            pass
        if self.profile is None:
            return
        try:
            st = self.profile.setdefault('stats', {})
            st['kills'] = max(int(st.get('kills', 0)), int(self.kills))
            st['best_chapter'] = max(int(st.get('best_chapter', 0)),
                                     int(self.floor))
            # 需求 4：货币与材料在退出/过场时结算进档，避免只存在局内
            # 1.3：金币/钻石落档前先封顶
            if self.level_state is not None and self.state != 'lobby':
                self.profile['diamonds'] = GD.clamp_diamond(
                    getattr(self, 'diamonds', 0))
            if getattr(self, 'mats', None):
                pm = self.profile.setdefault('materials', {})
                for k, v in self.mats.items():
                    pm[k] = int(pm.get(k, 0)) + int(v)
                self.mats = {}
            self.profile['updated'] = time.time()
            if self.store is not None:
                self.store.flush(self.profile)
        except Exception:
            pass

    # -------------------------------------------------- 需求 11：音频/震动开关
    def _apply_audio_settings(self):
        """把当前 setting 字典落到 audio/music/vibrator 上。"""
        st = self.setting
        try:
            self.audio.set_enabled(bool(st.get('sfx')) and
                                   bool(self.audio.sounds))
        except Exception:
            pass
        try:
            self.music.set_enabled(bool(st.get('music')))
        except Exception:
            pass
        try:
            self.vibrator.set_enabled(bool(st.get('vibrate')))
        except Exception:
            pass

    def _load_settings_from_profile(self):
        """从存档读设置（每档独立）。"""
        prof = self.profile
        if not isinstance(prof, dict):
            return
        s = prof.get('settings')
        if isinstance(s, dict):
            for k, v in s.items():
                self.setting[k] = v
            if (not prof.get('v22_sfx_migrated') and
                    not s.get('sfx') and not s.get('music') and
                    not s.get('shake') and not s.get('vibrate')):
                self.setting['sfx'] = True
                prof['v22_sfx_migrated'] = True
                prof['settings']['sfx'] = True
        self._apply_audio_settings()

    def save_settings(self):
        """把设置写回存档。"""
        if not isinstance(self.profile, dict):
            return
        self.profile['settings'] = dict(self.setting)
        self._write_save()

    def toggle_setting(self, name):
        """切换一个布尔设置并落盘。"""
        if name not in self.setting:
            return
        self.setting[name] = not bool(self.setting[name])
        self._apply_audio_settings()
        self.save_settings()
        self.audio.play('ui')
        return self.setting[name]

    def set_setting(self, name, val):
        self.setting[name] = val
        self._apply_audio_settings()
        self.save_settings()
        return val

    def buzz(self, ms=60, strength=0.6):
        """触发一次震动（需求 11）。默认关闭时是 no-op。"""
        try:
            return self.vibrator.buzz(ms, strength)
        except Exception:
            return False

    def music_mood(self):
        """按当前场景深浅给 BGM 一个"情绪档"（0..3）。"""
        try:
            ls = self.level_state or {}
            sc = ls.get('scene')
            if not sc:
                return 0
            idx = C.all_scenes().index(sc)
            n = max(1, len(C.all_scenes()) - 1)
            return int(round(idx / float(n) * 3))
        except Exception:
            return 0

    # -------------------------------------------------- 档位管理（需求 10）
    def slot_list(self):
        """返回 3 个档位（None 表示空档）。"""
        if self.store is None:
            return [None, None, None]
        return self.store.slots()

    def has_profile(self):
        return self.profile is not None

    def create_profile(self, idx, name=''):
        if self.store is None:
            return False
        self.profile = self.store.create(idx, name)
        self.best_floor = self.best_kills = 0
        self.coins = self.diamonds = 0
        self.level_state = None
        # 新档的设置从默认值起（音效/音乐/震动默认关，需求 11）
        self._load_settings_from_profile()
        return True

    def select_profile(self, idx):
        p = self.store.get(idx) if self.store else None
        if p is None:
            return False
        self.store.set_current(idx)
        self.profile = p
        self.coins = int(p.get('coins', 0))
        self.diamonds = int(p.get('diamonds', 0))
        self.level_state = None
        st = p.get('stats') or {}
        self.best_floor = int(st.get('best_chapter', 0))
        self.best_kills = int(st.get('kills', 0))
        self._load_settings_from_profile()
        return True

    def delete_profile(self, idx):
        if self.store is None:
            return False
        self.store.delete(idx)
        if self.profile is not None and self.profile.get('id') == idx:
            self.profile = None
        return True

    def save_now(self):
        """显式存盘（需求 7：脱离卡死时先存后退出）。"""
        self._write_save()

    def _bank_run_coins(self):
        """Settle the remaining run purse once when the run ends."""
        if self.profile is None or getattr(self, '_coins_banked', True):
            return
        self.profile['coins'] = GD.clamp_coin(
            int(self.profile.get('coins', 0)) + int(self.coins))
        self.profile['run_checkpoint'] = None
        PR.reset_cycle(self.profile)
        self._coins_banked = True
        self._write_save()

    def settle_run(self):
        """Bank this run's remaining rewards and return to the main menu."""
        self._bank_run_coins()
        self._write_save()
        self.state = 'title'
        self.menu_index = 0

    # ================================================================ 流程
    def _drink_schedule(self):
        """一个存档内每主题固定抽两关，续玩时不会重新抽取。"""
        profile = self.profile or {}
        pid = profile.get('id')
        if pid is None:
            return {key: set(self.rng.sample(range(5), 2)) for key in SCENE_SPAWN}
        out = {}
        for key in SCENE_SPAWN:
            h = 2166136261
            seed = f'{pid}|{int(float(profile.get("created", 0) or 0) * 1000)}|{key}'
            for b in seed.encode('utf-8'):
                h = ((h ^ b) * 16777619) & 0xffffffff
            a = h % 5
            b = (h // 5) % 4
            if b >= a:
                b += 1
            out[key] = {a, b}
        return out

    def start_run(self, scene=None, stage_idx=0):
        """开始一局。

        scene 为 None 时用进度层里已存的断点（`profile['run']`）；
        都没有则从第一个主线场景的第 1 关开始——保证任何入口都能进得去。
        """
        pending_cp = (self.profile or {}).get('run_checkpoint')
        self.char_skill_cd = 0.0
        if self.seed is None:
            self.rng = random.Random()
        else:
            self.rng = random.Random(self.seed)
        self.player = Player(S.ROOM_CX, S.ROOM_CY)
        self.drink_stages = self._drink_schedule()
        self.drink_buffs = {}
        self.coins = 0
        self._coins_banked = False
        self.diamonds = int(self.profile.get('diamonds', 0)) if self.profile else 0
        self.run_diamonds = 0
        self.mats = {}
        self.toasts = []
        self.kills = 0
        self.combo_count = 0
        self.combo_t = 0.0
        self.run_kills = 0
        self.run_deaths = 0
        self.run_trap_hits = 0
        self.run_bomber_hits = 0
        self.run_low_hp = False
        self.run_items = 0
        self._drain_acc = 0.0
        self.pollution = None
        self._stage_done = False
        self._stage_done = False
        self.total_time = 0.0
        self._explode_depth = 0
        self.hint_t = 13.0
        self.hitstop = 0.0
        self.hitstop = 0.0
        self._hitstop_cd = 0.0
        self.run_stats = None
        self.pending_talents = None
        self.transition_lock = 0.0
        # 防卡死状态
        self._stuck_t = 0.0
        self._stuck_rescues = 0
        self._last_pos = None
        self._last_mx = 0.0
        self._last_my = 0.0

        # ---- 关卡进度（需求 2）
        self.level_state = self._resolve_level_state(scene, stage_idx)
        self.route_state = 'none'
        self.route_room = None
        self.route_sealed = False
        self.route_index = 0

        # ---- 需求 6：应用当前角色（属性 / 初始武器）与永久养成加成
        self._apply_loadout()

        # ---- 过场状态复位
        self.story_scene = None
        self.story_lines = []
        self.story_t = 0.0
        self.story_page = 0
        self.pending_after = None

        # 首次进入一个场景（第 1 关）时先播该场景的进场过场
        ls = self.level_state or {}
        sc = ls.get('scene')
        si = int(ls.get('stage_idx', 0))
        if (isinstance(pending_cp, dict) and pending_cp.get('scene') == sc
                and int(pending_cp.get('stage_idx', -1)) == si):
            floor = max(1, min(S.FLOORS, int(pending_cp.get('floor', 1))))
            self._start_floor(floor, floor_seed=pending_cp.get('seed'),
                              capture=False)
            self._restore_floor_checkpoint(pending_cp)
            if self.route_state != 'pending':
                self.state = 'playing'
            return
        self._start_floor(1)
        if sc and si == 0 and self.profile is not None:
            first = not PR.is_scene_cleared(self.profile, sc)
            if first:
                self._start_story('stage_enter', sc, 0, after=('enter', None))
                return
        if self.route_state != 'pending':
            self.state = 'playing'

    def _resolve_level_state(self, scene, stage_idx):
        """决定这一局从哪个场景的哪一关开始。"""
        prof = self.profile
        if prof is None:
            # 没有存档（无头测试/未建档）-> 用第一个主线场景兜底
            key = scene or PR.scene_order({})[0]
            order = PR.scene_order({}).index(key)
            return PR.make_run(key, int(stage_idx), order)
        if scene is not None:
            order = PR.scene_order(prof)
            if scene not in order:
                scene = order[0]
            PR.start_scene(prof, scene)
            if stage_idx:
                PR.next_stage(prof, scene, stage_idx)
            return PR.level_state(prof)
        ls = PR.level_state(prof)
        if ls is not None:
            return ls
        # 存档里没有断点 -> 从第一关开始
        key = PR.scene_order(prof)[0]
        PR.start_scene(prof, key)
        return PR.level_state(prof)

    def _start_floor(self, floor, floor_seed=None, capture=True):
        self.floor = int(floor)
        self.floor_seed = int(floor_seed) if floor_seed is not None else \
            self.rng.randrange(2 ** 32)
        self.rng = random.Random(self.floor_seed)
        # 需求 2/3：场景 key 与难度由进度层给出；缺省时退化为旧行为（无场景机关）
        scene = None
        stage_idx = 0
        diff = (1.0, 1.0)
        ls = self.level_state
        if isinstance(ls, dict):
            scene = ls.get('scene')
            stage_idx = int(ls.get('stage_idx', 0))
            diff = ls.get('diff', (1.0, 1.0))
        # 进入第 1 层 = 进入新一关 -> 重置本关统计
        if int(floor) <= 1:
            self._reset_stage_trackers()
        drink_stage = stage_idx in getattr(self, 'drink_stages', {}).get(scene, ())
        luck_b = float((getattr(self, 'run_stats', None) or {}).get('luck', 0.0) or 0.0)
        self.dungeon = Dungeon(self.floor, self.rng, scene_key=scene,
                               stage_idx=stage_idx, diff=diff,
                               drink_stage=drink_stage, luck_bonus=luck_b)
        from .route35 import choose_room
        self.route_room = choose_room(self.dungeon)
        self.route_state = 'pending' if self.route_room is not None else 'none'
        self.route_sealed = False
        self.route_index = 0
        self.bullets = []
        self.enemies = []
        self.boss = None
        self.fx.clear()
        key = self.dungeon.start_key
        self.room = None
        self.enter_room(key[0], key[1], None, first=True)
        self.player.x, self.player.y = S.ROOM_CX, S.ROOM_CY
        # 需求：污染渐近减益。基础数值在每个场景重新计算一次，
        # 这样"越往下走越难受"是稳定的，而不是逐帧抖动。
        self._apply_pollution(scene, stage_idx)
        self.player.hp = min(self.player.max_hp, self.player.hp + 3)
        self.player.energy = self.player.max_energy
        self.player.iframes = max(self.player.iframes, 1.0)
        flags = (getattr(self, 'run_stats', None) or {}).get('flags') or ()
        self.player.shield_charges = 1 if 'shield' in flags else 0
        self.state = 'route_choice' if self.route_state == 'pending' else 'playing'
        if capture:
            self._capture_floor_checkpoint()

    def _capture_floor_checkpoint(self):
        if self.profile is None:
            return
        pl = self.player
        ls = self.level_state or {}
        self.profile['run_checkpoint'] = {
            'scene': ls.get('scene'), 'stage_idx': int(ls.get('stage_idx', 0)),
            'floor': self.floor, 'seed': self.floor_seed,
            'coins': int(self.coins), 'diamonds': int(self.diamonds),
            'player': {k: getattr(pl, k) for k in
                       ('hp', 'energy', 'wkey', 'wqual', 'wkey2', 'wqual2')},
            'drinks': dict(self.drink_buffs),
            'talents': list(getattr(self, 'talents_owned', ()) or ()),
            'run_stats': dict(self.run_stats or {}),
            'kills': self.kills, 'run_kills': self.run_kills,
            'run_items': self.run_items, 'total_time': self.total_time,
            'run_deaths': self.run_deaths,
            'run_trap_hits': self.run_trap_hits,
            'run_bomber_hits': self.run_bomber_hits,
            'run_low_hp': self.run_low_hp,
            'run_diamonds': self.run_diamonds,
            'route_id': 'mine_survey_02' if self.route_room else None,
            'route_room': list(self.route_room) if self.route_room else None,
            'route_state': self.route_state,
        }
        self._write_save()

    def _restore_floor_checkpoint(self, cp):
        saved = cp.get('route_room')
        if (saved and self.route_room and list(self.route_room) == list(saved)
                and cp.get('route_id') == 'mine_survey_02'
                and cp.get('route_state') in ('normal', 'survey')):
            self.route_state = cp['route_state']
            self.state = 'playing'
        pl = self.player
        self.coins = int(cp.get('coins', 0))
        self.diamonds = int(cp.get('diamonds', self.diamonds))
        raw_drinks = cp.get('drinks') or {}
        self.drink_buffs = (dict(raw_drinks) if isinstance(raw_drinks, dict)
                            else {key: 1 for key in raw_drinks})
        self.talents_owned = list(cp.get('talents') or ())
        self.recompute_talents()
        self.kills = int(cp.get('kills', 0))
        self.run_kills = int(cp.get('run_kills', 0))
        self.run_items = int(cp.get('run_items', 0))
        self.total_time = float(cp.get('total_time', 0.0))
        self.run_deaths = int(cp.get('run_deaths', 0))
        self.run_trap_hits = int(cp.get('run_trap_hits', 0))
        self.run_bomber_hits = int(cp.get('run_bomber_hits', 0))
        self.run_low_hp = bool(cp.get('run_low_hp', False))
        self.run_diamonds = int(cp.get('run_diamonds', 0))
        ls = self.level_state or {}
        self._apply_pollution(ls.get('scene'), int(ls.get('stage_idx', 0)))
        for key, value in (cp.get('player') or {}).items():
            if key in ('hp', 'energy', 'wkey', 'wqual', 'wkey2', 'wqual2'):
                setattr(pl, key, value)
        pl.hp = max(1.0, min(float(pl.hp), float(pl.max_hp)))
        pl.energy = max(0.0, min(float(pl.energy), float(pl.max_energy)))
        flags = (getattr(self, 'run_stats', None) or {}).get('flags') or ()
        pl.shield_charges = 1 if 'shield' in flags else 0

    def _choose_route(self, index=0):
        if self.route_state != 'pending':
            return
        self.route_state = 'survey' if index == 1 else 'normal'
        self.route_index = index
        self.state = 'playing'
        if index == 1:
            self.toast('勘测已启用', '清空标记支路后从出口撤离', life=2.0)
            self.audio.play('lock')
        self._capture_floor_checkpoint()

    def _apply_pollution(self, scene, stage_idx):
        """把当前场景的污染减益写进玩家属性，并弹一条警告。

        减益是**相对基准值**计算的（每个场景重新推一次），
        所以天赋/装备的加成不会被反复叠加或抹掉。
        """
        self.pollution = PR.pollution(scene, stage_idx) if scene else None
        pl = self.player
        base_hp = getattr(self, '_loadout_hp', S.P_MAX_HP)
        base_energy = getattr(self, '_loadout_energy', S.P_MAX_ENERGY)
        # 天赋等带来的额外上限（max_hp_max_energy 增量在 run_stats 里）
        extra_hp = 0
        extra_energy = 0.0
        if isinstance(self.run_stats, dict):
            extra_hp = int(self.run_stats.get('max_hp', 0))
            extra_energy = float(self.run_stats.get('max_energy', 0))
        p = self.pollution
        if not p:
            pl.max_hp = (base_hp + extra_hp) * (1.0 + 0.25 * self.drink_buffs.get('nectar', 0))
            pl.max_energy = base_energy + extra_energy
            pl.hp = min(pl.hp, pl.max_hp)
            pl.energy = min(pl.energy, pl.max_energy)
            self._pur = (0, 1.0, 1.0, 0.0)
            return
        # 1.3：抗污染天赋在这里生效 —— 所有减益先过一遍抗性
        hp_cut, spd, regen, drain = CX.pur_tint_amount(p, self.run_stats)
        self._pur = (hp_cut, spd, regen, drain)
        pl.max_hp = max(1, base_hp + extra_hp - int(hp_cut)) * (1.0 + 0.25 * self.drink_buffs.get('nectar', 0))
        pl.max_energy = max(20.0, base_energy + extra_energy)
        pl.hp = min(pl.hp, pl.max_hp)
        # 警告提示（需求 15：局内文字提示）
        if hp_cut > 0 or spd < 0.999 or drain > 0:
            lines = PR.pollution_lines(scene, stage_idx)
            r = max(0.0, min(1.0, 1.0 - (drain / max(1e-6, float(p['drain'])))
                              )) if p['drain'] > 0 else 0.0
            title = '污染浓度 %d%%' % p['pct']
            if r > 0.01:
                title += '（抗性 -%d%%）' % int(round(r * 100))
            self.toast(title, ' · '.join(lines), (236, 128, 150))

    # ---- 污染减益的逐帧效果（持续侵蚀 + 移速/回能倍率）
    def _pur_val(self, idx, default):
        """取抗性调整后的污染值（未初始化时回退到原始 pollution）。"""
        pur = getattr(self, '_pur', None)
        if pur is None:
            p = getattr(self, 'pollution', None)
            if not p:
                return default
            if idx == 0:
                return p['hp_cut']
            if idx == 1:
                return float(p['spd'])
            if idx == 2:
                return float(p['regen'])
            return float(p['drain'])
        return pur[idx]

    @property
    def pollution_spd(self):
        return float(self._pur_val(1, 1.0))

    @property
    def pollution_regen(self):
        return float(self._pur_val(2, 1.0))

    @property
    def pollution_drain(self):
        return float(self._pur_val(3, 0.0))

    def _update_pollution(self, dt):
        """每秒扣血（污染侵蚀）。用累积器避免浮点误差丢帧。"""
        pl = self.player
        drain = self.pollution_drain
        if drain <= 0 or not pl.alive:
            self._drain_acc = 0.0
            return
        self._drain_acc = getattr(self, '_drain_acc', 0.0) + drain * dt
        # 1.3「净化循环」：每 PERIOD 秒把累积器清零一次（不清血量）
        if CX.has_pur_purge(self.run_stats):
            self._purge_t = getattr(self, '_purge_t', 0.0) + dt
            if self._purge_t >= CX.PUR_PURGE_INTERVAL:
                self._purge_t -= CX.PUR_PURGE_INTERVAL
                self._drain_acc = 0.0
                self.fx.text(pl.x, pl.y - 30, '净化', (120, 250, 210),
                             self.assets.font(11), 0.9)
                return
        if self._drain_acc >= 1.0:
            n = int(self._drain_acc)
            self._drain_acc -= n
            # 不触发无敌帧/闪烁，只做"环境侵蚀"
            pl.hp -= n
            self.fx.text(pl.x, pl.y - 26, '-%d 侵蚀' % n, (196, 90, 120),
                         self.assets.font(11), 0.8)
            if pl.hp <= 0:
                pl.hp = 0.0
                pl.die(self)

    @property
    def pur_dmg_mul(self):
        """1.3「污染共鸣」：浓度转化的伤害加成。"""
        return CX.pur_ward_bonus(getattr(self, 'pollution', None),
                                 self.run_stats)


    def enter_room(self, gx, gy, entry_door=None, first=False):
        r = self.dungeon.room(gx, gy)
        if r is None:
            return False
        old = self.room
        if old is not None and not old.cleared and old is not r:
            old.enemies_spawned = False        # 未清空就离开 -> 下次进来重刷
        self.room = r
        r.visited = True
        r.build_props()
        r.build_pickups()
        r.build_hazards()

        self.enemies = []
        self.bullets = []
        self.boss = None
        if not r.cleared and not r.enemies_spawned:
            self._spawn_room(r)
            r.enemies_spawned = True
        r.refresh_doors(locked=(not r.cleared and bool(self.enemies)))

        if entry_door is not None:
            ex, ey = S.ENTRY_FROM[entry_door]
            # 落点校验：掩体/障碍/陷阱可能正好生成在门口格上，把玩家塞进墙。
            # 一旦圆心落在实心瓦片内，普通滑动移动会失效（详见 utils._slide），
            # 所以进门时必须先找一个安全落点。
            self.player.x, self.player.y = U.unstick(
                ex, ey, self.player.radius, r.solid, fallback=(S.ROOM_CX, S.ROOM_CY))
        self._ensure_player_free()
        self.trans_fade = 0.0 if first else 0.30
        self.banner_text = r.label()
        self.banner_t = 0.0 if first else 1.6
        self.prompt = None
        self.fx.clear()
        # 需求 15：首领出场的专属提示（名号 + 一句简介）
        if r.kind == 'boss' and self.boss is not None:
            self._boss_intro(self.boss)
        return True

    def _boss_intro(self, b):
        """首领出场提示（需求 15）：横幅 + 图鉴收录 + 音效。"""
        name = getattr(b, 'boss_name', None) or '首领'
        title = getattr(b, 'boss_title', '')
        label = ('%s  %s' % (title, name)).strip() if title else name
        self.banner_text = label
        self.banner_t = 3.2
        try:
            self.discover('enemy', getattr(b, 'skey', None))
        except Exception:
            pass
        kind = 'miniboss'
        try:
            si = int((self.level_state or {}).get('stage_idx', 0))
            kind = C.stage_kind(si)
        except Exception:
            pass
        tag = '小首领' if kind == 'miniboss' else '首领'
        info = None
        try:
            info = CX.ENEMY_CODEX.get(getattr(b, 'skey', None))
        except Exception:
            info = None
        desc = info[3] if info else ''
        self.toast('%s登场：%s' % (tag, name), desc, (255, 170, 190), life=3.6)
        self.audio.play('ui_big')

    def _diag_input(self, inp):
        """把"第一次收到移动输入"记进 boot.log，用于远程排查"无法移动"。

        只记一次，开销可忽略；有无这一行能立刻区分
        "输入根本没到达" 还是 "输入到了但走不动"。
        """
        if getattr(self, '_diag_move_done', False):
            return
        try:
            if inp.get('mx') or inp.get('my'):
                self._diag_move_done = True
                import main as _m
                _m._boot_log('首次收到移动输入 mx=%s my=%s（键盘通路正常）'
                             % (inp.get('mx'), inp.get('my')))
        except Exception:
            self._diag_move_done = True

    def _ensure_player_free(self):
        """每帧兜底：若玩家落在实心瓦片内（被击退顶进墙、落点异常等），
        就近拉出来。这是"防卡死"的最后一道防线。"""
        if self.room is None or not self.player.alive:
            return
        pl = self.player
        if U.collide_test(pl.x, pl.y, pl.radius, self.room.solid,
                          self.room.blockers()):
            pl.x, pl.y = U.unstick(pl.x, pl.y, pl.radius, self.room.solid,
                                   self.room.blockers(),
                                   fallback=(S.ROOM_CX, S.ROOM_CY))
            self._stuck_rescues += 1

    def _check_stuck(self, dt):
        """连续多秒"有输入却零位移"则判定卡死，触发自动脱困。
        对应需求：角色一场卡死无法移动的修复 + 防卡死设计。"""
        pl = self.player
        if self.state != 'playing' or not pl.alive:
            self._stuck_t = 0.0
            self._last_pos = None
            return
        want_move = bool(self._last_mx or self._last_my)
        if not want_move:
            self._stuck_t = 0.0
            self._last_pos = (pl.x, pl.y)
            return
        if self._last_pos is None:
            self._last_pos = (pl.x, pl.y)
            return
        moved = U.dist(self._last_pos[0], self._last_pos[1], pl.x, pl.y)
        if moved < 0.05:
            self._stuck_t += dt
        else:
            self._stuck_t = 0.0
        self._last_pos = (pl.x, pl.y)
        if self._stuck_t >= S.STUCK_SECONDS:
            # 自动脱困（需求 7）：三级降级，逐级加狠
            #   1) 从障碍/墙体里拉出来（几何解）
            #   2) 若还在墙里，把玩家挪到房间中心
            #   3) 顺带清掉压在玩家身上的可破坏掩体（掩体是"软"阻塞，
            #      不清理的话下一帧又会把玩家挤住，形成"反复脱困"）
            self._stuck_rescues += 1
            try:
                self._free_from_covers(pl)
            except Exception:
                pass
            pl.x, pl.y = U.unstick(pl.x, pl.y, pl.radius, self.room.solid,
                                   self.room.blockers(),
                                   fallback=(S.ROOM_CX, S.ROOM_CY))
            # 经过 2 次自动脱困仍卡住 -> 直接送房间中心（最暴力但绝对有效）
            if self._stuck_rescues >= 2 or U.collide_test(
                    pl.x, pl.y, pl.radius, self.room.solid, self.room.blockers()):
                pl.x, pl.y = S.ROOM_CX, S.ROOM_CY
                pl.knock_t = 0.0
                self._stuck_rescues = 0
            self._stuck_t = 0.0
            self.fx.text(pl.x, pl.y - 30, '已脱困', S.C_PANEL_HI,
                         self.assets.font(12), 1.2)
            self.audio.play('dash')

    def _free_from_covers(self, pl):
        """把压在玩家身上的掩体推开（需求 7 的配套）。

        掩体是"实体阻塞"，如果玩家恰好生成/被击退到与掩体重叠的位置，
        常规移动会被完全锁死。这里直接销毁重叠的掩体，比"硬挤"更稳。
        """
        room = self.room
        if room is None:
            return
        covers = getattr(room, 'covers', None)
        if not covers:
            return
        keep = []
        for c in covers:
            try:
                cx, cy, cr = c[0], c[1], c[2] if len(c) > 2 else 14
            except Exception:
                keep.append(c)
                continue
            if U.dist(pl.x, pl.y, cx, cy) < pl.radius + float(cr) + 2:
                continue        # 丢掉这一块
            keep.append(c)
        room.covers = keep

    def _spawn_room(self, r):
        # Boss 的 key 现在是场景专属的（warlord / swarmqueen / ...），
        # 不再是字面 'boss'。用 BOSS_SKIN 判定哪些 key 是首领。
        plan = r.wave_plans[r.wave_index] if r.wave_plans else r.spawn_plan
        for kind, x, y, elite in plan:
            if kind in enemy_mod.BOSS_SKIN_KEYS:
                b = Boss(x, y, self.floor)
                # 需求 8：不同场景的 Boss 外观/名号不同
                sc = (self.level_state or {}).get('scene')
                si = int((self.level_state or {}).get('stage_idx', 0))
                try:
                    b.setup_scene(sc, si)
                except Exception:
                    pass
                self.enemies.append(b)
                self.boss = b
            else:
                em = enemy_mod.make(kind, x, y, self.floor, elite)
                sc = (self.level_state or {}).get('scene')
                mob_mul = float(enemy_mod.SCENE_MOB_HP_MUL.get(sc, 1.0))
                if abs(mob_mul - 1.0) > 0.001:
                    em.max_hp = float(round(em.max_hp * mob_mul))
                    em.hp = em.max_hp
                em.apply_dmg_mul(enemy_mod.SCENE_DMG_MUL.get(sc, 1.0))
                self.enemies.append(em)

    def spawn_minion(self, x, y, floor):
        sc = (self.level_state or {}).get('scene')
        kinds = ['slime', 'drone'] if (floor >= 2 or sc not in (None, 'crust')) else ['slime']
        k = self.rng.choice(kinds)
        em = enemy_mod.make(k, x, y, floor, False)
        mob_mul = float(enemy_mod.SCENE_MOB_HP_MUL.get(sc, 1.0))
        if abs(mob_mul - 1.0) > 0.001:
            em.max_hp = float(round(em.max_hp * mob_mul))
            em.hp = em.max_hp
        em.apply_dmg_mul(enemy_mod.SCENE_DMG_MUL.get(sc, 1.0))
        self.enemies.append(em)
        if self.room is not None and self.room.cleared and self.room.kind == 'boss':
            self.room.cleared = False
            self.room.enemies_spawned = True

    def roll_weapon_key(self):
        pool = W.DROP_POOL.get(self.floor, ['pistol'])
        return self.rng.choice(pool)

    def award_rare_weapon(self, quality, x, y, direct_chance=1.0, key=None):
        """Record a blueprint and optionally drop its usable weapon."""
        key = key or W.roll_quality_key(self.rng, quality)
        quality = W.quality_of(key)
        if self.profile is not None:
            plans = self.profile.setdefault('blueprints', {})
            if GD.quality_rank(quality) > GD.quality_rank(plans.get(key, 'white')):
                plans[key] = quality
            self._write_save()
        self.toast('获得%s图纸' % GD.quality_of(quality)['name'],
                   W.get(key).name, GD.quality_of(quality)['color'])
        if self.rng.random() < direct_chance:
            self.pickups.append(Pickup(x, y, 'weapon', wkey=key, quality=quality))

    # ================================================================ 图鉴
    def discover(self, cat, key, silent=False):
        """记录一次图鉴发现。首次发现返回 True 并弹提示（需求 15）。

        cat: 'enemy' / 'weapon' / 'material' / 'collect'
        """
        if not key:
            return False
        prof = self.profile
        if prof is None:
            # 无存档环境：只记在内存的 new_codex 里，方便测试断言
            if (cat, key) not in self.new_codex:
                self.new_codex.append((cat, key))
                return True
            return False
        cx = prof.setdefault('codex', {})
        lst = cx.setdefault(cat, [])
        if key in lst:
            return False
        lst.append(key)
        if not silent:
            self._codex_toast(cat, key)
        return True

    def _codex_toast(self, cat, key):
        """新发现的提示文案。"""
        info = None
        desc = ''
        try:
            if cat == 'enemy':
                info = CX.ENEMY_CODEX.get(key)
            elif cat == 'collect':
                info = CX.COLLECTS.get(key)
            elif cat == 'material':
                info = GD.MATERIALS.get(key) if hasattr(GD, 'MATERIALS') else None
            elif cat == 'weapon':
                info = W.WEAPONS.get(key) if hasattr(W, 'WEAPONS') else None
        except Exception:
            info = None
        if info:
            if isinstance(info, dict):
                name = info.get('name', key)
                desc = info.get('desc', '')
            elif isinstance(info, (list, tuple)):
                name = info[0] if len(info) > 0 else key
                desc = info[-1] if len(info) > 2 else ''
            else:
                # WeaponSpec 之类的对象
                name = getattr(info, 'name', None) or str(key)
                desc = getattr(info, 'desc', '') or ''
        else:
            name = key
        tag = CX.CODEX_CATS.get(cat, '图鉴')
        self.toast('新%s：%s' % (tag, name), desc, (170, 230, 255), life=3.0)
        self.new_codex.append((cat, key))

    def collect_got(self, key):
        """获得一件收集品 -> 记图鉴 + 存展示台（需求 9）。"""
        if not key:
            return False
        prof = self.profile
        self.discover('collect', key)
        if prof is None:
            return True
        lst = prof.setdefault('collects', [])
        first = key not in lst
        if first:
            lst.append(key)
            # 自动放到第一个空展示位
            sc = prof.setdefault('showcase', [None] * 6)
            for i in range(len(sc)):
                if sc[i] is None:
                    sc[i] = key
                    break
            for hero in GD.sync_collect_characters(prof):
                self.toast('新角色已解锁：%s' % GD.char(hero)['name'],
                           GD.unlock_text(hero, prof), (180, 245, 190), life=4.0)
            self._write_save()
        return first

    # ================================================================ 回调
    def toast(self, title, sub='', color=None, life=2.4):
        """局内文字提示（需求 15）。同标题只刷新计时，避免刷屏。"""
        color = color or S.C_TEXT
        for t in self.toasts:
            if t['title'] == title:
                t['t'] = 0.0
                t['life'] = life
                t['sub'] = sub or t['sub']
                return
        self.toasts.append({'title': title, 'sub': sub, 'color': color,
                            't': 0.0, 'life': life})
        if len(self.toasts) > 4:
            del self.toasts[0]

    def grant_material(self, key, n=1):
        """发放材料（需求 4）。返回实际到手数量。"""
        if n <= 0 or not key:
            return 0
        self.mats[key] = self.mats.get(key, 0) + int(n)
        from . import gamedata as GD
        name = GD.MATERIALS.get(key, (key,))[0]
        # 需求 15：图鉴收录（第一次拿到这种材料）
        try:
            self.discover('material', key)
        except Exception:
            pass
        self.fx.text(self.player.x, self.player.y - 30,
                     f'+{int(n)} {name}', (198, 220, 255),
                     self.assets.font(12), 1.1)
        self._write_save()
        return int(n)

    def grant_diamond(self, n=1):
        self.diamonds += int(n)
        self.fx.text(self.player.x, self.player.y - 30,
                     f'+{int(n)} 钻石', (170, 226, 255),
                     self.assets.font(12), 1.2)
        self._write_save()
        return int(n)

    def on_trap_hit(self, trap):
        """踩中陷阱（需求：副本准入条件追踪）。

        泥沼只减速不掉血，但同样算"踩中"，因为它就是那个场景的机关。
        """
        try:
            self.run_trap_hits += 1
        except Exception:
            pass

    def on_bomber_hit(self, enemy):
        """被自爆囊/爆破工头炸到（需求：副本准入条件追踪）。"""
        try:
            self.run_bomber_hits += 1
        except Exception:
            pass

    def _scene_stats(self):
        """汇总本场景本局的成绩，用于副本准入条件判定。"""
        cleared = False
        try:
            scene = (self.level_state or {}).get('scene')
            if scene and self.profile is not None:
                cleared = PR.is_scene_cleared(self.profile, scene)
        except Exception:
            cleared = False
        # 残血通关：完成时生命 ≤3 也算（这里在 advance 里再判定一次）
        return {
            'kills': int(self.run_kills),
            'items': int(self.run_items),
            'deaths': int(self.run_deaths),
            'trap_hits': int(self.run_trap_hits),
            'bomber_hits': int(self.run_bomber_hits),
            'no_death': (self.run_deaths == 0),
            'low_hp': bool(self.run_low_hp),
            'cleared': cleared,
        }

    def coin_value(self):
        """当前关单枚金币面值（需求 4：金币易得，但深度递增）。"""
        ls = self.level_state or {}
        v = C.coin_value(C.scene_index_of(ls.get('scene')),
                         ls.get('stage_idx', 0))
        return int(round(v * float(getattr(self, 'char_fortune_mul', 1.0) or 1.0)))

    def on_enemy_killed(self, e):
        self.kills += 1
        self.run_kills += 1
        self.combo_count = getattr(self, 'combo_count', 0) + 1
        self.combo_t = 2.8
        if getattr(self, 'player', None) and self.player.alive:
            e_gain = 2.5 if e.elite else 1.0
            if self.player.wq(self) == 'red' and self.player.wlevel(self) >= GD.max_level('red'):
                e_gain *= 1.30
            self.player.energy = min(self.player.max_energy,
                                     self.player.energy + e_gain)
            flags = (getattr(self, 'run_stats', None) or {}).get('flags') or ()
            if 'lifesteal' in flags and self.rng.random() < 0.12:
                self.player.hp = min(self.player.max_hp, self.player.hp + 1.0)
                self.fx.text(self.player.x, self.player.y - 24, '+1',
                             (130, 235, 140), self.assets.font(12), 0.7)
        if self.drink_buffs.get('tea', 0) and not getattr(self, '_basket_chain', False):
            self.audio.play('man_what_can_i_say')
            for _ in range(self.drink_buffs['tea']):
                self.bullets.append(Basketball(e.x, e.y))
        # 需求 15：图鉴收录（第一次见到就记，不限击杀）
        try:
            self.discover('enemy', getattr(e, 'skey', None))
        except Exception:
            pass
        if getattr(e, 'kind', '') == 'lucky_treasure':
            rng = self.rng
            cv = self.coin_value()
            for i in range(5):
                a = i * math.tau / 5
                self.pickups.append(Pickup(e.x + math.cos(a) * 18,
                                           e.y + math.sin(a) * 18, 'coin', cv * 3))
            for i in range(rng.randint(2, 3)):
                self.pickups.append(Pickup(e.x + i * 13 - 12, e.y + 22,
                                           'diamond', 1))
            for mat in (rng.choice(('alloy', 'core')),
                        rng.choice(('prism', 'relic'))):
                self.pickups.append(Pickup(e.x + rng.uniform(-28, 28),
                                           e.y + rng.uniform(-28, 28),
                                           'material', rng.randint(1, 2), ckey=mat))
            if rng.random() < .40:
                self.award_rare_weapon('red' if rng.random() < .16 else 'gold',
                                       e.x, e.y - 27, 1.0)
            if rng.random() < .10:
                self.pickups.append(Pickup(e.x, e.y - 20, 'collect',
                                           ckey=rng.choice(CX.COLLECT_ORDER)))
            self.toast('幸运宝藏怪', '发现珍品物资', (255, 232, 142))
            return
        if getattr(e, 'is_rare', False):
            self.award_rare_weapon('red', e.x, e.y, 0.15)
        if getattr(e, 'is_boss', False):
            return
        luck_b = float((getattr(self, 'run_stats', None) or {}).get('luck', 0.0) or 0.0)
        if e.elite and self.rng.random() < min(0.10, 0.005 * (1.0 + luck_b)):
            self.award_rare_weapon('gold', e.x, e.y, 1.0)
        rng = self.rng
        cv = self.coin_value()
        n = (2 if rng.random() < 0.25 else 1) + (1 if e.elite else 0)
        face = int(round(cv * (C.COIN_ELITE_MUL if e.elite else 1.0)))
        # 注意：不要在这里"合并成更少的大币"。
        # 掉落实体数量会影响玩家的磁力吸附轨迹，进而改变走位与命中，
        # 实测会让无头 Boss 战从"2179 帧击杀"恶化成"18000 帧打不死"。
        # 经济靠面值（face）放大即可，枚数保持与旧版一致。
        for _ in range(n):
            a = rng.uniform(0, math.tau)
            d = rng.uniform(6, 26)
            self.pickups.append(Pickup(e.x + math.cos(a) * d,
                                       e.y + math.sin(a) * d, 'coin', face))
        if e.elite:
            self.pickups.append(Pickup(e.x + 8, e.y - 6, 'material', 1,
                                       ckey=rng.choice(('scrap', 'fiber', 'circuit'))))
        elif rng.random() < 0.12:
            self.pickups.append(Pickup(e.x + 6, e.y, 'material', 1,
                                       ckey=rng.choice(('scrap', 'fiber'))))
        if rng.random() < 0.22 + (0.12 if e.elite else 0.0):
            self.pickups.append(Pickup(e.x, e.y, 'energy', 18))
        if rng.random() < 0.09 + (0.08 if e.elite else 0.0):
            self.pickups.append(Pickup(e.x, e.y, 'heart', 2))
        if rng.random() < 0.018:
            self.pickups.append(Pickup(e.x, e.y, 'key', 15))
        if e.elite and rng.random() < min(0.85, 0.34 * (1.0 + 0.5 * luck_b)):
            sc = (getattr(self, 'level_state', None) or {}).get('scene')
            wkey, quality = W.roll_elite_weapon(rng, sc)
            self.pickups.append(Pickup(e.x, e.y, 'weapon',
                                       wkey=wkey, quality=quality))

    def _maybe_open_portal(self):
        """若刚清空的房间是本层的"目标房"，就开一道通往下一层的传送门。

        普通层没有首领，此前没有任何出口 -> 玩家打光所有房间也出不去
        （用户报的"给了钥匙却没有传送门"）。目标房由 Dungeon.goal_key 指定：
          · 首领层 -> 首领房（走 on_boss_defeated，不在这里处理）
          · 普通层 -> 最远的那间战斗房
        """
        r = self.room
        d = self.dungeon
        if r is None or d is None or r.portal is not None:
            return
        if getattr(d, 'is_boss_floor', False) and not getattr(r, 'boss_defeated', False):
            return
        if getattr(d, 'goal_key', None) != (r.gx, r.gy):
            return
        r.portal = (S.ROOM_CX, S.ROOM_CY)
        r.portal_t = 0.0
        self.banner_text = '目标房已清空！进入传送门前往下一关'
        self.banner_t = 2.6
        self.audio.play('level_up')

    def on_boss_defeated(self):
        r = self.room
        self.boss = None
        if r is None:
            return
        r.boss_defeated = True
        r.cleared = False
        r.enemies_spawned = True
        stage = int((self.level_state or {}).get('stage_idx', 0))
        scene = (self.level_state or {}).get('scene')
        exclusive = W.SCENE_BOSS_WEAPONS.get(scene, {})
        if C.stage_kind(stage) == 'boss':
            if exclusive.get('red') and self.rng.random() < 0.30:
                self.award_rare_weapon('red', S.ROOM_CX - 42,
                                       S.ROOM_CY - 66, 1.0, exclusive['red'])
            self.award_rare_weapon('red', S.ROOM_CX, S.ROOM_CY - 62, 1.0)
            if self.rng.random() < 0.012:
                self.award_rare_weapon('radiant', S.ROOM_CX + 22,
                                       S.ROOM_CY - 62, 1.0)
        else:
            if exclusive.get('gold') and self.rng.random() < 0.42:
                self.award_rare_weapon('gold', S.ROOM_CX - 42,
                                       S.ROOM_CY - 66, 1.0, exclusive['gold'])
            self.award_rare_weapon('gold', S.ROOM_CX, S.ROOM_CY - 62, 1.0)
            if self.rng.random() < 0.02:
                self.award_rare_weapon('red', S.ROOM_CX + 22,
                                       S.ROOM_CY - 62, 1.0)
            if self.rng.random() < 0.006:
                self.award_rare_weapon('radiant', S.ROOM_CX + 42,
                                       S.ROOM_CY - 62, 1.0)
        rng = self.rng
        cv = self.coin_value()
        boss_face = int(round(cv * C.COIN_BOSS_MUL))
        for _ in range(12):
            a = rng.uniform(0, math.tau)
            d = rng.uniform(20, 120)
            x = U.clamp(S.ROOM_CX + math.cos(a) * d, S.IN_L + 20, S.IN_R - 20)
            y = U.clamp(S.ROOM_CY + math.sin(a) * d, S.IN_T + 20, S.IN_B - 20)
            self.pickups.append(Pickup(x, y, 'coin', boss_face))
        # 大 Boss 必掉 5 枚钻石，小 Boss 必掉 2 枚
        dia_n = 5 if C.stage_kind(stage) == 'boss' else 2
        for _ in range(dia_n):
            a = rng.uniform(0, math.tau)
            self.pickups.append(Pickup(S.ROOM_CX + math.cos(a) * 64,
                                       S.ROOM_CY + math.sin(a) * 64,
                                       'diamond', 1))
        for _ in range(3):
            a = rng.uniform(0, math.tau)
            self.pickups.append(Pickup(S.ROOM_CX + math.cos(a) * 54,
                                       S.ROOM_CY + math.sin(a) * 54, 'heart', 2))
        for _ in range(2):
            a = rng.uniform(0, math.tau)
            self.pickups.append(Pickup(S.ROOM_CX + math.cos(a) * 76,
                                       S.ROOM_CY + math.sin(a) * 76, 'energy', 40))
        self.banner_text = 'BOSS 已击败！清空随从后进入传送门'
        self.banner_t = 2.6
        self.audio.play('level_up')

    def on_player_died(self):
        self._bank_run_coins()
        self._write_save()
        self.state = 'gameover'
        self.over_index = 0

    def _next_floor(self):
        """打完当前房间后推进。

        分三层：
          · 同一关内还有房间（floor < FLOORS）-> levelclear，继续下一房间
          · 本关最后一间房 -> _finish_stage() 记成绩，然后让 progress 决定去向
              - 'next'        -> 同一场景的下一小关
              - 'scene_clear' -> 播放该场景的通关过场，再进下一场景（或通关）
              - 'game_clear'  -> 奖励副本收尾，直接 victory
        过场期间 state='story'，玩家按任意键继续（不丢进度）。
        """
        if self.floor < S.FLOORS:
            self.state = 'levelclear'
            self.audio.play('level_up')
            return
        self._finish_stage()

        prof = self.profile
        if prof is None:
            # 无存档（无头测试）-> 退化成旧的"3 层通关"行为
            self._write_save()
            self.state = 'victory'
            self.over_index = 0
            self.audio.play('victory')
            return

        # 关键：level_state 是 prof['run'] 的副本，推进前必须回写，
        # 否则 PR.advance 读到的还是旧关卡号（会一直返回 'next'）。
        ls = self.level_state or {}
        sc = ls.get('scene')
        si = int(ls.get('stage_idx', 0))
        if prof is not None and sc is not None:
            try:
                PR.next_stage(prof, sc, si)
            except Exception:
                pass

        kind, payload = PR.advance(prof)
        if kind == 'next':
            # 同场景下一小关（需求 19）：只有**刚打完 boss 关**才给天赋三选一。
            # 判断依据是"刚打完的这一关"是不是 boss 关，而不是"要进的那一关"。
            sc = payload.get('scene')
            si = int(payload.get('stage_idx', 0))
            PR.next_stage(prof, sc, si)
            self.level_state = PR.level_state(prof)
            just_cleared = si - 1        # 刚打完的关
            if just_cleared >= 0 and C.stage_kind(just_cleared) in (
                    'miniboss', 'boss'):
                if self.start_talent_pick(3):
                    self._pending_story = ('stage_enter', sc, si,
                                           ('enter', None))
                    return
            self._start_story('stage_enter', sc, si, after=('enter', None))
            return

        if kind == 'game_clear':
            self._bank_run_coins()
            if self.start_talent_pick(3):
                self._pending_story = ('scene_clear', ls.get('scene'), 0,
                                       ('game_clear', None))
                return
            self._write_save()
            self.state = 'victory'
            self.over_index = 0
            self.audio.play('victory')
            return

        # 每个场景的第五关大 Boss 也要在穿过传送门后获得一次天赋。
        sc = payload.get('scene')
        finale = bool(payload.get('finale'))
        if C.stage_kind(si) == 'boss' and self.start_talent_pick(3):
            self._pending_story = ('scene_clear', sc, 0,
                                   ('scene_clear', {'finale': finale}))
            return
        self._start_story('scene_clear', sc, 0,
                          after=('scene_clear', {'finale': finale}))

    # ================================================================ 过场
    def _start_story(self, phase, scene_key, stage_idx=0, after=None):
        """进入过场。phase: 'stage_enter' | 'scene_clear' | 'scene_enter'。"""
        lines, title, tint = self._story_text(phase, scene_key, stage_idx)
        if not lines:
            # 没有台词 -> 跳过过场，直接执行后置动作
            self.pending_after = after
            self._advance_pending()
            return
        self.story_scene = scene_key
        self.story_phase = phase
        self.story_lines = lines
        self.story_title = title
        self.story_tint = tint
        self.story_t = 0.0
        self.story_page = 0
        self.pending_after = after
        self.state = 'story'
        self.audio.play('ui_big')

    def _story_text(self, phase, scene_key, stage_idx):
        """-> (台词列表, 标题, 色调)。"""
        info = C.scene_info(scene_key)
        tint = info.get('tint', (140, 140, 140))
        name = info.get('name', scene_key)
        act = C.act_title(scene_key) if hasattr(C, 'act_title') else ''
        if phase == 'scene_clear':
            head = '「%s」 已清理' % name
            return (list(info.get('clear', [])), head, tint)

        # stage_enter：需求 2 —— 每一关都给叙事节拍，让故事贯穿全程；
        # 第 1 关额外带上该场景的"进场台词"和幕标题。
        si = int(stage_idx)
        if si == 0:
            lines = []
            if act:
                lines.append(act)
            lines.extend(list(info.get('enter', [])))
            return (lines, '「%s」 进入' % name, tint)
        kind = C.stage_kind(si) if hasattr(C, 'stage_kind') else 'normal'
        sub = C.scene_stage_name(si) if hasattr(C, 'scene_stage_name') \
            else '第 %d 关' % (si + 1)
        # 叙事节拍（需求 2）
        lines = []
        if act:
            lines.append(act)
        lines.append('%s · %s' % (name, sub))
        beats = C.stage_beat(scene_key, si) if hasattr(C, 'stage_beat') else []
        if beats:
            lines.extend(beats)
        elif kind == 'miniboss':
            lines.append('前方有精英与小型 Boss，整理好弹药。')
        elif kind == 'boss':
            lines.append('本场景的最终关。污染读数最高，注意脚下。')
        else:
            lines.append('继续向下，别在同一个陷阱上栽两次。')
        try:
            hint = PR.pollution_warning(scene_key, si)
            if hint:
                lines.append(hint)
        except Exception:
            pass
        return (lines, '%s · 第 %d 关' % (name, si + 1), tint)

    def _advance_pending(self):
        """执行过场结束后的动作。"""
        act = self.pending_after
        self.pending_after = None
        if act is None:
            self.state = 'playing'
            return
        kind, data = act
        if kind == 'enter':
            # 进入当前场景已经写进 level_state，直接开局
            self.start_run_scene(self.level_state)
        elif kind == 'game_clear':
            self._bank_run_coins()
            self._write_save()
            self.state = 'victory'
            self.over_index = 0
            self.audio.play('victory')
        elif kind == 'scene_clear':
            prof = self.profile
            scene = self.story_scene
            if data and data.get('finale'):
                self._bank_run_coins()
                # 主线最终场景通关 -> 提示去客厅买奖励副本
                self._write_save()
                self.state = 'lobby'
                self.lobby_expand = False
                self.toast('主线已通关',
                           '客厅里可以购买奖励副本「%s」了' % C.scene_label(C.BONUS),
                           (255, 226, 150), life=4.0)
                return
            # 1.4 线性推进：直接按 next_target 找下一个该打的场景，
            # 不再依赖"可见顺序"（副本不会被顺路吞掉）。
            nxt = None
            if prof is not None:
                tgt = PR.next_target(prof)
                nxt = tgt.get('scene')
                if nxt == scene:        # 防御：不该自己接自己
                    nxt = None
            if nxt is None:
                self._bank_run_coins()
                self._write_save()
                self.state = 'lobby'
                return
            if prof is not None:
                PR.start_scene(prof, nxt)
                self.level_state = PR.level_state(prof)
            self.start_run_scene(self.level_state)
        else:
            self.state = 'playing'

    def start_run_scene(self, level_state):
        """从过场恢复：按当前 level_state 打开第 1 层。"""
        self.level_state = level_state
        self._stage_done = False
        self.transition_lock = 0.35
        self._start_floor(1)
        self.state = 'playing'

    def _story_next(self):
        """过场推进：先翻页，翻完执行后置动作。"""
        if self.transition_lock > 0:
            # 输入锁还在（刚进过场，防误触）：在无头/无 update 的环境下
            # 也要能推进，所以这里直接把锁清掉，而不是干等。
            self.transition_lock = 0.0
        if self.story_page + 1 < len(self.story_lines):
            self.story_page += 1
            self.story_t = 0.0
            self.audio.play('ui')
        else:
            self._advance_pending()
            self.audio.play('ui_big')

    def _story_skip(self):
        """ESC 跳过整个过场（直接执行后置动作）。"""
        self._advance_pending()

    def _finish_stage(self):
        """一关打完：写入本关成绩 + 检查副本解锁 + 存档。

        只在"最后一层"调用一次（前两层只是同一关内的房间切换）。
        """
        if self._stage_done:
            return
        self._stage_done = True
        try:
            scene = (self.level_state or {}).get('scene')
            if scene is None:
                return
            si = int((self.level_state or {}).get('stage_idx', 0))
            # 残血通关：生命 ≤3 时算一次"险胜"
            try:
                if self.player.alive and self.player.hp <= 3.0:
                    self.run_low_hp = True
            except Exception:
                pass
            stats = self._scene_stats()
            if self.profile is not None:
                if self.route_state == 'survey' and self.route_sealed:
                    claimed = self.profile.setdefault('route_first_rewards', [])
                    if 'mine_survey_02' not in claimed:
                        self.profile.setdefault('materials', {})['crystal'] = (
                            int(self.profile.setdefault('materials', {}).get('crystal', 0)) + 2)
                        claimed.append('mine_survey_02')
                        self.toast('首次勘测完成 · 污染结晶 ×2',
                                   '回执 02：局部隔离有效', life=3.0)
                    else:
                        self.toast('勘测完成 · 首奖已领取', life=2.0)
                PR.merge_scene_best(self.profile, scene, stats)
                # 需求 1：线性推进 —— 本关通关立刻记进 scene_prog，
                # 这样即使玩家中途退出，下次也知道该从哪一关继续。
                PR.bump_scene_prog(self.profile, scene, si)
                # 只有"通关整场景（第 5 关）"才检查副本解锁条件
                if si >= PR.C.STAGES_PER_SCENE - 1:
                    new = PR.scan_unlocks(self.profile)
                    for k in new:
                        nm = PR.C.DUNGEONS.get(k, {}).get('name')
                        if nm is None:
                            nm = PR.scene_name(k)
                        self.toast('解锁新副本：%s' % nm,
                                   '客厅地图上已点亮（支线，可选）',
                                   (255, 226, 150), life=4.0)
                self._write_save()
        except Exception:
            pass

    def _reset_stage_trackers(self):
        """进入新的一关时重置"本关"计数（污染/关卡统计）。"""
        self.run_kills = 0
        self.run_deaths = 0

    # ============================================================ 天赋三选一
    def recompute_talents(self):
        """把已选天赋折算成 run_stats（数值加成 + flag 集合）。

        乘算项（如 pur_resist）逐件相加后受硬上限约束；
        加法项（max_hp / speed_mul …）直接累加。
        """
        st = {
            'max_hp': 0, 'max_energy': 0.0, 'speed_mul': 0.0, 'spd_mul': 0.0,
            'dmg_mul': 0.0, 'fire_mul': 0.0, 'rate_mul': 0.0, 'magnet_mul': 0.0,
            'hp_regen': 0.0, 'crit': 0.0, 'dash_cd_mul': 0.0,
            'luck': 0.0, 'pierce': 0, 'pur_resist': 0.0,
            'flags': [], 'talents': [],
        }
        # 先合入客厅已升级的永久天赋（不写进 talents_owned，保留局内三选一池独立）
        perm_lv = (getattr(self, 'profile', None) or {}).get('talent_levels') or {}
        for tk, tlv in perm_lv.items():
            lv = int(tlv or 0)
            if lv <= 0:
                continue
            spec = CX.TALENTS.get(tk)
            if not spec:
                continue
            if spec.get('kind') == 'stat':
                name = spec.get('stat')
                if name in st:
                    st[name] = st[name] + spec.get('val', 0) * lv
            else:
                fl = spec.get('flag')
                if fl and fl not in st['flags']:
                    st['flags'].append(fl)
        for k in self.talents_owned:
            spec = CX.TALENTS.get(k)
            if not spec:
                continue
            st['talents'].append(k)
            if spec.get('kind') == 'stat':
                name = spec.get('stat')
                if name in st:
                    st[name] = st[name] + spec.get('val', 0)
            else:
                fl = spec.get('flag')
                if fl and fl not in st['flags']:
                    st['flags'].append(fl)
        st['speed_mul'] = float(st.get('spd_mul', 0.0) or 0.0)
        # 抗污染走硬上限
        st['pur_resist'] = max(0.0, min(CX.PUR_RESIST_CAP,
                                        float(st['pur_resist'] or 0.0)))
        self.run_stats = st
        return st

    def start_talent_pick(self, n=3):
        """生成三选一候选（已选满 3 次的天赋不再出现）。"""
        owned = list(self.talents_owned)
        try:
            picks = CX.roll_talents(self.rng, owned, n)
        except Exception:
            picks = list(CX.TALENT_ORDER[:n])
        if not picks:
            return False
        self.pending_talents = picks
        self.talent_pick = 0
        self.state = 'talent'
        return True

    def _talent_move(self, d):
        if not self.pending_talents:
            return
        n = len(self.pending_talents)
        self.talent_pick = (int(self.talent_pick) + int(d)) % max(1, n)
        self.audio.play('ui')

    def _talent_confirm(self):
        if not self.pending_talents:
            self.state = 'playing'
            return
        i = int(self.talent_pick) % len(self.pending_talents)
        k = self.pending_talents[i]
        self.talents_owned.append(k)
        self.recompute_talents()
        spec = CX.TALENTS.get(k, {})
        nm = spec.get('name', k)
        self.pending_talents = None
        self.audio.play('ui_big')
        self.toast('习得天赋：%s' % nm, spec.get('desc', ''),
                   spec.get('color', (255, 236, 170)), life=3.4)
        # 把加成落到玩家身上（生命上限 / 污染减益立刻生效）
        try:
            ls = self.level_state or {}
            self._apply_pollution(ls.get('scene'),
                                  int(ls.get('stage_idx', 0)))
        except Exception:
            pass
        if k == 'hp_up':
            self.player.hp = float(self.player.max_hp)
        elif k == 'shield':
            self.player.shield_charges = max(
                1, int(getattr(self.player, 'shield_charges', 0) or 0))
        self.state = 'playing'
        # 若这次三选一是"关卡推进"触发的，选完继续走后续过场链路
        pend = getattr(self, '_pending_story', None)
        if pend:
            self._pending_story = None
            try:
                phase, sc, si, after = pend
                self._start_story(phase, sc, si, after=after)
            except Exception:
                pass
        self.run_trap_hits = 0
        self.run_bomber_hits = 0
        self.run_items = 0
        self.run_low_hp = False
        self._drain_acc = 0.0
        self._stage_done = False


    # ================================================================ 输入
    def _window_to_canvas(self, pos):
        ox, oy = self.view_off
        return ((pos[0] - ox) / max(1, self.scale), (pos[1] - oy) / max(1, self.scale))

    def read_input(self):
        if self.inp_override is not None:
            return dict(self.inp_override)
        try:
            keys = pygame.key.get_pressed()
            mp = pygame.mouse.get_pressed()
            mpos = pygame.mouse.get_pos()
        except Exception:
            keys, mp, mpos = None, (0, 0, 0), (S.VIEW_W // 2, S.VIEW_H // 2)

        # 事件累积出的按键集合（焦点丢失时 get_pressed() 会整表 False）。
        held = self._held_keys
        # ---- 防"幽灵按键"：若 get_pressed() 工作正常、且报告"全都没按"，
        # 而事件集合里还留着键，说明 KEYUP 丢了。连续多帧如此就清空，
        # 避免玩家松开手后角色继续走个不停。
        if keys is not None and held:
            try:
                any_pressed = any(keys[k] for k in held)
            except Exception:
                any_pressed = True
            if any_pressed:
                self._ghost_t = 0.0
            else:
                self._ghost_t = getattr(self, '_ghost_t', 0.0) + 1.0 / 60.0
                if self._ghost_t > 0.5:
                    held = set()
                    self._held_keys = held
                    self._ghost_t = 0.0

        def down(k):
            try:
                if keys is not None and keys[k]:
                    return True
            except Exception:
                pass
            return k in held

        mx = my = 0
        if keys is not None or held:
            if down(pygame.K_a) or down(pygame.K_LEFT):
                mx -= 1
            if down(pygame.K_d) or down(pygame.K_RIGHT):
                mx += 1
            if down(pygame.K_w) or down(pygame.K_UP):
                my -= 1
            if down(pygame.K_s) or down(pygame.K_DOWN):
                my += 1
            shoot = bool(mp[0]) or down(pygame.K_SPACE)
            dash = bool(mp[2]) or down(pygame.K_LSHIFT) or down(pygame.K_RSHIFT)
            slow = down(pygame.K_LCTRL) or down(pygame.K_RCTRL)
        else:
            shoot = dash = slow = False
        self.mouse_canvas = self._window_to_canvas(mpos)
        world = (self.mouse_canvas[0] - self.cam[0], self.mouse_canvas[1] - self.cam[1])
        aim = math.atan2(world[1] - self.player.y, world[0] - self.player.x)
        return {'mx': mx, 'my': my, 'aim': aim, 'shoot': shoot,
                'dash': dash, 'slow': slow}

    def _keydown(self, key):
        st = self.state
        if self.collection_popup is not None:
            self.collection_popup = None
            return
        # 需求 18：二次确认浮层优先吃掉所有输入
        if self.confirm_prompt is not None:
            self._confirm_key(key)
            return
        if key == pygame.K_F11:
            self.toggle_fullscreen()
            return
        if key == pygame.K_m:
            self.audio.set_enabled(not self.audio.enabled)
            self.menu_items[2] = ('音效：开' if self.audio.enabled else '音效：关', 'audio')
            return

        if st == 'title':
            if key in (pygame.K_UP, pygame.K_w):
                self.menu_index = (self.menu_index - 1) % len(self.menu_items)
                self.audio.play('ui')
            elif key in (pygame.K_DOWN, pygame.K_s):
                self.menu_index = (self.menu_index + 1) % len(self.menu_items)
                self.audio.play('ui')
            elif key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                self._menu_pick(self.menu_items[self.menu_index][1])
            elif key in (pygame.K_F1, pygame.K_l):
                self.state = 'changelog'
                self.log_scroll = 0
                self.audio.play('ui')
        elif st == 'changelog':
            if key in (pygame.K_UP, pygame.K_w):
                self.log_scroll = max(0, int(self.log_scroll) - 1)
            elif key in (pygame.K_DOWN, pygame.K_s):
                self.log_scroll = int(self.log_scroll) + 1
            elif key in (pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_KP_ENTER,
                         pygame.K_SPACE):
                self.state = 'title'
                self.audio.play('ui')
        elif st in ('slots', 'slot_create', 'slot_confirm'):
            self._keydown_slots(key)
        elif st == 'help':
            # 需求 12/15：设置面板 —— ↑↓ 选择，Enter/←→ 调整
            if key in (pygame.K_ESCAPE, pygame.K_p):
                self.state = 'title'
                self.audio.play('ui')
            else:
                self._keydown_settings(key)
        elif st == 'playing':
            if key in (pygame.K_ESCAPE, pygame.K_p):
                self.state = 'paused'
                self.pause_index = 0
                self.audio.play('ui')
            elif key in (pygame.K_e, pygame.K_f):
                self.request_interact()
            elif key == pygame.K_q:
                if self.player.switch_weapon():
                    self.audio.play('pickup')
            elif key == pygame.K_x:
                from . import character_skills
                character_skills.activate(self)
            elif key == pygame.K_v:
                self.show_aim = not self.show_aim
        elif st == 'route_choice':
            if key in (pygame.K_UP, pygame.K_DOWN, pygame.K_w, pygame.K_s):
                self.route_index = 1 - self.route_index
                self.audio.play('ui')
            elif key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                self._choose_route(self.route_index)
            elif key in (pygame.K_ESCAPE, pygame.K_p):
                self._choose_route(0)
        elif st == 'paused':
            if key in (pygame.K_UP, pygame.K_w):
                self.pause_index = (self.pause_index - 1) % len(self.pause_items)
                self.audio.play('ui')
            elif key in (pygame.K_DOWN, pygame.K_s):
                self.pause_index = (self.pause_index + 1) % len(self.pause_items)
                self.audio.play('ui')
            elif key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                self._menu_pick(self.pause_items[self.pause_index][1])
            elif key in (pygame.K_ESCAPE, pygame.K_p):
                self.state = 'playing'
                self.audio.play('ui')
        elif st == 'levelclear':
            if key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE,
                       pygame.K_ESCAPE):
                self._start_floor(self.floor + 1)
            elif key == pygame.K_s:
                self.settle_run()
        elif st in ('gameover', 'victory'):
            if key in (pygame.K_UP, pygame.K_w):
                self.over_index = (self.over_index - 1) % len(self.over_items)
                self.audio.play('ui')
            elif key in (pygame.K_DOWN, pygame.K_s):
                self.over_index = (self.over_index + 1) % len(self.over_items)
                self.audio.play('ui')
            elif key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                self._menu_pick(self.over_items[self.over_index][1])
        elif st == 'lobby':
            self._keydown_lobby(key)
        elif st == 'talent':
            if key in (pygame.K_LEFT, pygame.K_a):
                self._talent_move(-1)
            elif key in (pygame.K_RIGHT, pygame.K_d):
                self._talent_move(1)
            elif key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                self._talent_confirm()
        elif st == 'story':
            if key == pygame.K_ESCAPE:
                self._story_skip()
            else:
                self._story_next()

    # ================================================================ 客厅输入
    # 需求 1：1.4 起**不允许选关**。客厅退化成"战斗准备"界面：
    #   · 主区只显示"下一站"（唯一可进入的关卡）
    #   · 地图区展示全 7 场景的锁/通状态，纯展示不可点入
    #   · ←→ 切换页签，↑↓ 只在"准备面板"里选具体项目
    def _lobby_order(self):
        """客厅展示用的场景顺序（全部 7 个，含未解锁）。"""
        try:
            return list(PR.scene_order(self.profile or {}))
        except Exception:
            return list(C.MAIN)

    def _lobby_target(self):
        """当前唯一可进入的关卡（线性推进）。"""
        prof = self.profile
        if prof is None:
            return {'scene': C.MAIN[0], 'stage_idx': 0}
        try:
            return PR.next_target(prof)
        except Exception:
            return {'scene': C.MAIN[0], 'stage_idx': 0}

    def _lobby_move(self, d):
        """1.4：客厅不再"选场景"。↑↓ 改为在准备面板的项目间移动。"""
        items = self._lobby_prep_items()
        n = max(1, len(items))
        self.lobby_index = (int(self.lobby_index) + d) % n
        self.lobby_expand = False
        self.audio.play('ui')

    def _lobby_prep_items(self):
        """战斗准备面板的可选项（需求 16）。

        1.4 起「角色 / 武器 / 天赋」不再是占位提示，而是切到养成分页
        里对应的子页（需求 4/5/6）。
        """
        items = [
            ('enter', '出击'),
            ('new_cycle', '从第一关开新局'),
            ('char', '角色'),
            ('weapon', '武器'),
            ('talent', '天赋'),
            ('codex', '图鉴'),
            ('showcase', '展示台'),
            ('log', '更新日志'),
        ]
        prof = self.profile or {}
        for key in C.DUNGEONS:
            if key in prof.get('unlocked_dungeons', []) and PR.scene_prog(prof, key) < C.STAGES_PER_SCENE:
                items.insert(1, ('dungeon:' + key, C.scene_label(key)))
        if PR.bonus_available(prof) or prof.get('bonus_unlocked'):
            items.insert(1, ('bonus', '奖励副本'))
        return items

    def _keydown_settings(self, key):
        """需求 12/15：设置面板键盘操作。
        ↑↓ 选项；Enter / ←→ 调整；bool 直接切换，mode 循环，num 步进 0.1。
        """
        from . import hud as _hud
        rows, _st = _hud._setting_rows(self)
        n = max(1, len(rows))
        idx = int(getattr(self, 'setting_index', 0)) % n
        if key in (pygame.K_w, pygame.K_UP):
            self.setting_index = (idx - 1) % n
            self.audio.play('ui')
            return
        if key in (pygame.K_s, pygame.K_DOWN):
            self.setting_index = (idx + 1) % n
            self.audio.play('ui')
            return
        if key not in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE,
                       pygame.K_a, pygame.K_LEFT, pygame.K_d, pygame.K_RIGHT):
            return
        label, k, typ = rows[idx]
        back = key in (pygame.K_a, pygame.K_LEFT)
        if typ == 'bool':
            self.toggle_setting(k)
        elif typ == 'mode':
            modes = _hud._JOY_MODES
            cur = self.setting.get(k, modes[0])
            i = modes.index(cur) if cur in modes else 0
            i = (i - 1) % len(modes) if back else (i + 1) % len(modes)
            self.set_setting(k, modes[i])
            self.audio.play('ui')
        elif typ == 'num':
            try:
                v = float(self.setting.get(k, 1.0))
            except Exception:
                v = 1.0
            v += (-0.1 if back else 0.1)
            # 灵敏度区间 0.4 ~ 2.0
            v = max(0.4, min(2.0, round(v, 1)))
            self.set_setting(k, v)
            self.audio.play('ui')

    def _keydown_lobby(self, key):
        if key == pygame.K_TAB:
            self.lobby_tab = (int(self.lobby_tab) + 1) % 4
            self.lobby_expand = False
            self.audio.play('ui')
            return
        tab = int(getattr(self, 'lobby_tab', 0)) % 4
        if tab == 1:
            self._keydown_growth(key)
            return
        if tab == 2:
            self._keydown_codex(key)
            return
        if tab == 3:
            self._keydown_showcase(key)
            return
        if key in (pygame.K_UP, pygame.K_w):
            self._lobby_move(-1)
        elif key in (pygame.K_DOWN, pygame.K_s):
            self._lobby_move(1)
        elif key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
            self._lobby_go()
        elif key == pygame.K_ESCAPE:
            self.state = 'title'
            self.menu_index = 0
            self.audio.play('ui')

    # ---- 养成分页（需求 4/5/6/7） -------------------------------------
    def _keydown_growth(self, key):
        """养成分页：←→ 换子页（角色/武器/技能/天赋），↑↓ 选条目，Enter 购买或强化。"""
        nsub = 4
        if key in (pygame.K_LEFT, pygame.K_a):
            self.growth_sub = (int(getattr(self, 'growth_sub', 0)) - 1) % nsub
            self.growth_index = 0
            self.audio.play('ui')
        elif key in (pygame.K_RIGHT, pygame.K_d):
            self.growth_sub = (int(getattr(self, 'growth_sub', 0)) + 1) % nsub
            self.growth_index = 0
            self.audio.play('ui')
        elif key in (pygame.K_UP, pygame.K_w):
            self.growth_index = max(0, int(getattr(self, 'growth_index', 0)) - 1)
            self.audio.play('ui')
        elif key in (pygame.K_DOWN, pygame.K_s):
            self.growth_index = int(getattr(self, 'growth_index', 0)) + 1
            self.audio.play('ui')
        elif key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
            self._growth_confirm()
        elif key == pygame.K_ESCAPE:
            self.state = 'title'
            self.audio.play('ui')

    def _growth_rows(self):
        """当前子页的条目列表（供 UI 与键盘共用）。"""
        from . import growth as GR
        prof = self.profile
        sub = int(getattr(self, 'growth_sub', 0)) % 4
        if sub == 0:
            return GR.char_list(prof)
        if sub == 1:
            return GR.weapon_list(prof)
        if sub == 2:
            rows = GR.skill_list(prof)
            for r in rows:
                r['is_passive'] = False
            pr = GR.passive_list(prof)
            for r in pr:
                r['is_passive'] = True
            return rows + pr
        return GR.talent_list(prof)

    def _growth_confirm(self):
        """Enter：角色=选中/购买，武器/技能/天赋=强化。"""
        from . import growth as GR
        prof = self.profile
        if prof is None:
            self.audio.play('no_energy')
            return
        sub = int(getattr(self, 'growth_sub', 0)) % 4
        rows = self._growth_rows()
        if not rows:
            return
        i = int(getattr(self, 'growth_index', 0)) % len(rows)
        row = rows[i]
        key = row.get('key')
        if sub == 0:
            # 未拥有 -> 购买；已拥有且非当前 -> 换上；已装备 -> 提示
            if not row.get('owned'):
                if GD.char(key)['unlock'] and GD.char(key)['unlock'][0] == 'collect':
                    have, need = GD.collect_progress(prof, key)
                    self.toast('收集进度 %d/%d' % (have, need),
                               '获得不同收集品后自动解锁「%s」' % row.get('name', key),
                               (180, 225, 250), life=3.0)
                    return
                self.ask_confirm('解锁角色「%s」' % row.get('name', key),
                                 '将扣除货币和材料，再按 Enter 确认',
                                 pygame.K_RETURN,
                                 lambda: self._growth_after(*GR.buy_char(prof, key)))
                return
            elif key != prof.get('char'):
                ok, msg = GR.select_char(prof, key)
            else:
                ok, msg = False, '「%s」已在出战' % row.get('name', key)
            self._growth_after(ok, msg)
            return
        if sub == 1:
            cb = lambda: GR.upgrade_weapon(prof, key)
            title = '合成武器' if row.get('craft') else '强化武器'
        elif sub == 2:
            if row.get('is_passive'):
                cb = lambda: GR.upgrade_passive(prof, key)
            else:
                cb = lambda: GR.upgrade_skill(prof, key)
            title = '强化技能'
        else:
            cb = lambda: GR.upgrade_talent(prof, key)
            title = '强化天赋'
        self.ask_confirm(title, '将扣除金币和材料，再按 Enter 确认',
                         pygame.K_RETURN,
                         lambda: self._growth_after(*cb()))

    def _growth_after(self, ok, msg):
        self.audio.play('ui_big' if ok else 'no_energy')
        if msg:
            self.toast(msg, '', (200, 240, 200) if ok else (240, 190, 190), 3.0)
        if ok:
            try:
                self._write_save()
            except Exception:
                pass

    def _open_growth(self, sub):
        """从准备菜单跳进养成分页并定位到指定子页。"""
        self.lobby_tab = 1
        self.growth_sub = int(sub) % 4
        self.growth_index = 0
        self.audio.play('ui')

    def _keydown_codex(self, key):
        """图鉴分页：←→ 换分类，↑↓ 选条目，PgUp/PgDn 翻页。"""
        ncat = 4
        if key in (pygame.K_LEFT, pygame.K_a):
            self.codex_cat = (int(self.codex_cat) - 1) % ncat
            self.codex_index = 0
            self.codex_page = 0
            self.audio.play('ui')
        elif key in (pygame.K_RIGHT, pygame.K_d):
            self.codex_cat = (int(self.codex_cat) + 1) % ncat
            self.codex_index = 0
            self.codex_page = 0
            self.audio.play('ui')
        elif key in (pygame.K_UP, pygame.K_w):
            self.codex_index = max(0, int(self.codex_index) - 1)
            self._codex_sync_page()
            self.audio.play('ui')
        elif key in (pygame.K_DOWN, pygame.K_s):
            self.codex_index = int(self.codex_index) + 1
            self._codex_sync_page()
            self.audio.play('ui')
        elif key == pygame.K_ESCAPE:
            self.state = 'title'
            self.audio.play('ui')

    def _codex_sync_page(self):
        """保证选中项在可见页内。"""
        per = max(1, (S.VIEW_H - 110) // 15)
        self.codex_page = int(self.codex_index) // per

    def _keydown_showcase(self, key):
        if key in (pygame.K_LEFT, pygame.K_a):
            self.showcase_index = (int(self.showcase_index) - 1) % 6
            self.audio.play('ui')
        elif key in (pygame.K_RIGHT, pygame.K_d):
            self.showcase_index = (int(self.showcase_index) + 1) % 6
            self.audio.play('ui')
        elif key in (pygame.K_UP, pygame.K_w):
            self.showcase_index = (int(self.showcase_index) - 3) % 6
            self.audio.play('ui')
        elif key in (pygame.K_DOWN, pygame.K_s):
            self.showcase_index = (int(self.showcase_index) + 3) % 6
            self.audio.play('ui')
        elif key in (pygame.K_e, pygame.K_f):
            self._showcase_toggle()
            self.audio.play('ui')
        elif key == pygame.K_ESCAPE:
            self.state = 'title'
            self.audio.play('ui')

    def _showcase_toggle(self):
        """把选中格子里的收集品取出 / 放回。"""
        prof = self.profile
        if prof is None:
            return
        sc = prof.setdefault('showcase', [None] * 6)
        while len(sc) < 6:
            sc.append(None)
        i = int(self.showcase_index) % 6
        if sc[i] is not None:
            sc[i] = None
        else:
            # 从"已获得但没摆出来"的收集品里补一个
            own = list(prof.get('collects', []))
            placed = set(x for x in sc if x)
            for k in own:
                if k not in placed:
                    sc[i] = k
                    break
        self._write_save()

    def _lobby_go(self):
        """客厅主行动键。

        1.4 起不再"选中场景就进"——必须按 PR.next_target() 的唯一路径走。
        选到"出击"才真的出发，选到别的项则执行对应动作。
        """
        prof = self.profile
        items = self._lobby_prep_items()
        sel = int(self.lobby_index) % max(1, len(items))
        action = items[sel][0]
        if action == 'enter':
            self._lobby_enter_next()
        elif action == 'new_cycle':
            self.ask_confirm('从第一关开新局', '保留通关记录，并结算当前断点收益；再按 Enter 确认',
                             pygame.K_RETURN, self._start_new_cycle)
        elif action.startswith('dungeon:'):
            key = action.split(':', 1)[1]
            if key in (prof or {}).get('unlocked_dungeons', []):
                si = PR.scene_prog(prof, key)
                if si < C.STAGES_PER_SCENE:
                    self.start_run(scene=key, stage_idx=si)
        elif action == 'bonus':
            if prof and not prof.get('bonus_unlocked'):
                self.ask_confirm('购买奖励副本',
                                 '支付 %d 游戏金币，再按 Enter 确认' % C.BONUS_PRICE,
                                 pygame.K_RETURN, self._buy_bonus)
            elif prof and prof.get('bonus_unlocked'):
                si = PR.scene_prog(prof, C.BONUS)
                if si < C.STAGES_PER_SCENE:
                    self.start_run(scene=C.BONUS, stage_idx=si)
        elif action == 'codex':
            self.lobby_tab = 2
            self.audio.play('ui')
        elif action == 'showcase':
            self.lobby_tab = 3
            self.audio.play('ui')
        elif action == 'log':
            self.state = 'changelog'
            self.log_scroll = 0
            self.audio.play('ui')
        elif action == 'char':
            self._open_growth(0)
        elif action == 'weapon':
            self._open_growth(1)
        elif action == 'talent':
            self._open_growth(3)
        else:
            self.audio.play('ui')

    def _buy_bonus(self):
        if self.profile and PR.buy_bonus(self.profile):
            self.coins = self.profile['coins']
            self._write_save()
            self.toast('奖励副本已解锁', '再次确认可进入', (255, 226, 150))
        else:
            self.toast('无法购买', '请先通关主线并攒够游戏金币', (226, 160, 120))

    def _start_new_cycle(self):
        prof = self.profile
        if prof is None:
            return
        cp = prof.get('run_checkpoint') or {}
        prof['coins'] = GD.clamp_coin(int(prof.get('coins', 0)) + int(cp.get('coins', 0) or 0))
        PR.reset_cycle(prof)
        self._write_save()
        self.start_run(scene=C.MAIN[0], stage_idx=0)

    def _lobby_enter_next(self):
        """按线性推进进入唯一允许的关卡。"""
        prof = self.profile
        tgt = self._lobby_target()
        sc = tgt.get('scene')
        if sc is None:
            self.audio.play('ui')
            self.toast('主线已通关', '选择奖励副本「%s」购买或进入'
                       % C.scene_label(C.BONUS), (255, 226, 150), life=4.0)
            return
        # 主线未通关但奖励副本已买 -> 允许去奖励副本
        if tgt.get('main_done') and prof is not None \
                and prof.get('bonus_unlocked'):
            PR.start_scene(prof, C.BONUS)
            self.audio.play('ui_big')
            self.start_run(scene=C.BONUS, stage_idx=0)
            return
        self.audio.play('ui_big')
        self.start_run(scene=sc, stage_idx=int(tgt.get('stage_idx', 0)))

    def _lobby_can_enter(self, key, prof):
        """兼容旧接口：判断某场景当前是否可以进入。"""
        if prof is None:
            return True, ''
        if not PR.is_scene_unlocked(prof, key):
            if key == C.BONUS:
                return False, '需先通关「%s」并购入' % C.scene_label(C.MAIN[-1])
            if key in C.DUNGEONS:
                _it, _ok, _ct, hint = PR.dungeon_progress(prof, key)
                return False, (hint or '解锁条件未达成')
            return False, '需先通关前置场景'
        return True, ''

    def _menu_pick(self, action):
        self.audio.play('ui_big')
        if action == 'new':
            # 需求 10：先选存档槽（3 槽 + 覆盖确认），再进客厅
            if self.store is None:
                self._enter_lobby()
            else:
                self.state = 'slots'
                self.slot_index = 0
                # 光标默认停在"已有档"上，方便继续玩
                slots = self.slot_list()
                for i, s in enumerate(slots):
                    if s is not None:
                        self.slot_index = i
                        break
        elif action == 'help':
            self.state = 'help'
        elif action == 'audio':
            self.audio.enabled = not self.audio.enabled and bool(self.audio.sounds)
            self.menu_items[2] = ('音效：开' if self.audio.enabled else '音效：关', 'audio')
        elif action == 'quit':
            self._write_save()
            self.running = False
        elif action == 'resume':
            self.state = 'playing'
        elif action == 'unstuck':
            self._do_unstuck()
        elif action == 'restart':
            self._bank_run_coins()
            self.start_run()
        elif action == 'settle':
            self.settle_run()
        elif action == 'title':
            self._write_save()
            self.state = 'title'
            self.menu_index = 0
        elif action == 'lobby':
            self._write_save()
            self._enter_lobby()

    # ================================================== 需求 7：脱离卡死
    def _do_unstuck(self):
        """脱离卡死：把玩家挪到房间中心的安全位置，并存盘后退出。

        需求 7 原文要求"点击脱离卡死后自动保存当前状态并退出，下次开始
        可选择从该存档开始"。所以这里：把玩家位置复位 -> 存盘 -> 退到主菜单
        （不直接杀进程，让玩家还能看到存档已保存）。
        """
        try:
            if self.room is not None:
                self.player.x, self.player.y = S.ROOM_CX, S.ROOM_CY
                self.player.vx = self.player.vy = 0.0
                self.player.iframes = max(self.player.iframes, 1.2)
            self._stuck_rescues = int(getattr(self, '_stuck_rescues', 0)) + 1
        except Exception:
            pass
        self._write_save()
        self.state = 'title'
        self.menu_index = 0
        try:
            self.toast('已脱离卡死', '进度已自动保存，下次可从断点继续',
                       (140, 230, 190), life=3.5)
        except Exception:
            pass
        self.audio.play('ui_big')

    # ================================================== 需求 18：二次确认
    def ask_confirm(self, title, sub, key, on_ok):
        """弹一个二次确认框。玩家再按一次 key（或 Enter）才执行 on_ok。"""
        self.confirm_prompt = {'title': title, 'sub': sub,
                               'key': key, 'on_ok': on_ok}
        self.confirm_t = 0.0
        self.audio.play('ui')

    def _confirm_key(self, key):
        cp = self.confirm_prompt
        if cp is None:
            return
        if key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE,
                   pygame.K_e, pygame.K_f) or key == cp.get('key'):
            self.confirm_prompt = None
            cb = cp.get('on_ok')
            self.audio.play('ui_big')
            if callable(cb):
                try:
                    cb()
                except Exception:
                    pass
        elif key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
            self.confirm_prompt = None
            self.audio.play('ui')

    # ================================================== 需求 10：存档槽
    def _keydown_slots(self, key):
        st = self.state
        if st == 'slot_create':
            if key == pygame.K_BACKSPACE:
                self.name_buf = self.name_buf[:-1]
            elif key == pygame.K_ESCAPE:
                self.state = 'slots'
            elif key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                name = (self.name_buf or '').strip() or \
                    ('漂泊者%d' % (int(self.slot_pending) + 1))
                self.create_profile(int(self.slot_pending), name)
                # 新建档后直接进客厅（否则会退回主菜单形成死循环）
                self._enter_lobby()
                self.audio.play('ui_big')
            else:
                ch = self._key_char(key)
                if ch and len(self.name_buf) < 12:
                    self.name_buf += ch
            return
        if st == 'slot_confirm':
            if key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_y):
                self.delete_profile(int(self.slot_pending))
                self.state = 'slots'
                self.slot_index = 0
            elif key in (pygame.K_ESCAPE, pygame.K_n):
                self.state = 'slots'
            self.audio.play('ui')
            return
        # slots
        slots = self.slot_list()
        n = max(1, len(slots))
        if key in (pygame.K_UP, pygame.K_w):
            self.slot_index = (int(self.slot_index) - 1) % n
            self.audio.play('ui')
        elif key in (pygame.K_DOWN, pygame.K_s):
            self.slot_index = (int(self.slot_index) + 1) % n
            self.audio.play('ui')
        elif key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
            i = int(self.slot_index) % n
            if slots[i] is None:
                self.slot_pending = i
                self.name_buf = ''
                self.state = 'slot_create'
                self.audio.play('ui_big')
            else:
                self.select_profile(i)
                # 选中存档后直接进客厅开玩（关键：不能退回 title，否则死循环）
                self._enter_lobby()
                self.audio.play('ui_big')
        elif key == pygame.K_d:
            i = int(self.slot_index) % n
            if slots[i] is not None:
                self.slot_pending = i
                self.state = 'slot_confirm'
                self.audio.play('ui')
        elif key == pygame.K_ESCAPE:
            self.state = 'title'
            self.menu_index = 0
            self.audio.play('ui')

    def _apply_loadout(self):
        """需求 6/7：把存档里的角色、武器、技能/被动等级应用进本局。

        - 角色决定生命/速度/能量上限与初始武器
        - 技能/被动是**永久**等级，直接叠在角色基础值上
        - 武器强化不在这里算（在 Player.wmul 里按帧读取），
          因为局内会换枪，强化等级必须跟着 wkey 走。
        """
        from . import gamedata as GD
        prof = self.profile
        pl = self.player
        ckey = (prof or {}).get('char') or self.char_key or 'scout'
        self.char_key = ckey
        c = GD.char(ckey)

        hp = int(c['hp'])
        spd = float(c['spd'])
        energy = float(c['energy'])

        # 永久技能 / 被动加成
        sk = (prof or {}).get('skills') or {}
        pv = (prof or {}).get('passives') or {}
        hp += int(sk.get('vital', 0))
        spd *= (1.0 + 0.03 * int(sk.get('haste', 0)))
        energy *= (1.0 + 0.08 * int(sk.get('focus', 0)))
        self.char_power_mul = 0.04 * int(sk.get('power', 0))
        self.char_fortune_mul = 1.0 + 0.10 * int(sk.get('fortune', 0))
        self.char_guard_mul = 1.0 + 0.08 * int(sk.get('guard', 0))
        self.char_thorns_ratio = 0.15 * int(pv.get('thorns', 0))
        self.char_regen_rate = 0.25 * int(pv.get('regen', 0))
        self.char_magnet_mul = 0.20 * int(pv.get('magnet', 0))
        self.char_crit_bonus = 0.04 * int(pv.get('crit', 0))
        self.char_pierce_bonus = int(pv.get('pierce', 0))

        pl.max_hp = max(1, hp)
        pl.hp = float(pl.max_hp)
        pl.max_energy = max(20.0, energy)
        pl.energy = pl.max_energy
        self._loadout_hp = pl.max_hp
        self._loadout_energy = pl.max_energy
        # 速度基准保持全局默认，用 char_spd_mul 让移动跟随角色
        self.char_spd_mul = spd / float(S.P_SPEED)

        # 初始武器：优先用存档携带的那把（可能已强化），否则用角色初始枪
        wkey = (prof or {}).get('weapon') or c['starter']
        if wkey not in W.WEAPONS:
            wkey = c['starter']
        pl.wkey = wkey
        pl.wqual = W.quality_of(wkey)
        self.recompute_talents()

    @staticmethod
    def _key_char(key):
        """把 keycode 转成可输入字符（只支持 ASCII 字母数字，够用）。"""
        if pygame.K_a <= key <= pygame.K_z:
            return chr(ord('a') + (key - pygame.K_a))
        if pygame.K_0 <= key <= pygame.K_9:
            return chr(ord('0') + (key - pygame.K_0))
        return ''

    def _enter_lobby(self):
        """进入客厅（战斗准备二级界面）。

        1.4 起光标默认落在"出击"上 —— 因为客厅的主职是"准备下一战"，
        而不是"挑一个场景"。
        """
        self.lobby_expand = False
        self.lobby_index = 0
        self.lobby_tab = 0
        self.state = 'lobby'

    def _mouse_menu(self, pos):
        """菜单鼠标悬停 / 点击"""
        cy = self._window_to_canvas(pos)[1]
        st = self.state
        if st == 'title':
            items, base = self.menu_items, 168
            step, idx_name = 34, 'menu_index'
        elif st == 'paused':
            items, base = self.pause_items, 122
            step, idx_name = 30, 'pause_index'
        elif st in ('gameover', 'victory'):
            items, base = self.over_items, None
            step, idx_name = 30, 'over_index'
        elif st == 'lobby':
            return self._mouse_lobby(pos)
        else:
            return False
        if base is None:
            return False
        for i in range(len(items)):
            y = base + i * step
            if y - 6 <= cy <= y + 26:
                setattr(self, idx_name, i)
                return True
        return False

    def _mouse_lobby(self, pos):
        """客厅：鼠标悬停到准备面板某项上即选中它。"""
        mx, my = self._window_to_canvas(pos)
        top = hud.LOBBY_PREP_Y
        step = hud.LOBBY_PREP_H + hud.LOBBY_PREP_GAP
        n = len(self._lobby_prep_items())
        for i in range(n):
            y = top + i * step
            if y <= my <= y + hud.LOBBY_PREP_H:
                if self.lobby_index != i:
                    self.lobby_index = i
                    self.lobby_expand = False
                    self.audio.play('ui')
                return True
        return False

    def _events(self):
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                self.running = False
            elif e.type == pygame.KEYDOWN:
                # 事件驱动按键集合：即使 get_pressed() 因焦点问题全 False，
                # 这里也能拿到"确实按下了什么"。
                try:
                    self._held_keys.add(int(e.key))
                    self._last_key_t = self.time
                except Exception:
                    pass
                self._keydown(e.key)
            elif e.type == pygame.KEYUP:
                try:
                    self._held_keys.discard(int(e.key))
                except Exception:
                    pass
            elif e.type in (getattr(pygame, 'WINDOWFOCUSLOST', -1),
                            getattr(pygame, 'WINDOWMINIMIZED', -2)):
                # 失焦时按键的 KEYUP 往往收不到 -> 必须清空，
                # 否则玩家会"松了键还在自己走"。
                self._held_keys.clear()
            elif e.type == pygame.MOUSEMOTION:
                self._mouse_menu(e.pos)
            elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                # 需求 18：确认框打开时，点击 = 确认
                if self.confirm_prompt is not None:
                    self._confirm_key(pygame.K_RETURN)
                elif self.state == 'title' and self._mouse_menu(e.pos):
                    self._menu_pick(self.menu_items[self.menu_index][1])
                elif self.state == 'paused' and self._mouse_menu(e.pos):
                    self._menu_pick(self.pause_items[self.pause_index][1])
                elif self.state in ('gameover', 'victory') and self._mouse_menu(e.pos):
                    self._menu_pick(self.over_items[self.over_index][1])
                elif self.state == 'levelclear':
                    self._start_floor(self.floor + 1)
                elif self.state == 'help':
                    if not self._mouse_settings(e.pos):
                        self.state = 'title'
                elif self.state == 'changelog':
                    self.state = 'title'
                elif self.state in ('slots', 'slot_create', 'slot_confirm'):
                    self._slot_mouse(e.pos)
                elif self.state == 'lobby':
                    if self._mouse_lobby(e.pos):
                        self._lobby_go()
                elif self.state == 'story':
                    self._story_next()
                elif self.state == 'route_choice':
                    mx, my = self._window_to_canvas(e.pos)
                    if 120 <= mx <= 520 and 110 <= my <= 260:
                        self._choose_route(1 if my >= 181 else 0)

    def _mouse_settings(self, pos):
        """需求 12/15：设置面板鼠标命中。命中返回 True（不退出界面）。"""
        from . import hud as _hud
        mx, my = self._window_to_canvas(pos)
        rows, _st = _hud._setting_rows(self)
        x0 = 372
        for i, (_label, _k, _typ) in enumerate(rows):
            yy = 70 + i * 26
            if x0 - 8 <= mx <= x0 + 236 and yy - 4 <= my <= yy + 20:
                self.setting_index = i
                self._keydown_settings(pygame.K_RETURN)
                return True
        return False

    def _slot_mouse(self, pos):
        """存档槽界面：鼠标点选。"""
        mx, my = self._window_to_canvas(pos)
        if self.state == 'slots':
            top = 84
            step = 52
            for i in range(len(self.slot_list())):
                y = top + i * step
                if y <= my <= y + 44 and 60 <= mx <= S.VIEW_W - 60:
                    self.slot_index = i
                    self.audio.play('ui')
                    slots = self.slot_list()
                    if slots[i] is None:
                        self.slot_pending = i
                        self.name_buf = ''
                        self.state = 'slot_create'
                    else:
                        self.select_profile(i)
                        self._enter_lobby()
                    return True
        return False

    def _find_interact_target(self):
        """拾取物优先于传送门，避免在传送门旁捡武器误触进门；站到传送门中心或附近无更近物品时才选中传送门。"""
        if self.state != 'playing' or self.room is None or self.player is None:
            return None
        pl = self.player
        best, bd = None, 1e9
        for p in self.pickups:
            if p.can_interact(pl):
                d = U.dist(p.x, p.y, pl.x, pl.y)
                if d < bd:
                    best, bd = p, d
        if self.room.portal is not None:
            portal_d = U.dist(pl.x, pl.y, *self.room.portal)
            if portal_d < 24 and (best is None or portal_d < 4 or portal_d + 6 < bd):
                return 'portal'
        return best

    def request_interact(self):
        """外部/测试调用：请求一次交互。

        需求 18：传送门、宝箱、购买这些"不可逆/有代价"的操作需要**二次按键**
        确认 —— 第一次按弹出确认框（给玩家思考时间），再按一次才真的执行。
        武器交换也需要确认，避免路过掉落物时误换。
        """
        if self.state != 'playing' or self.room is None:
            return False
        if self.confirm_prompt is not None:
            return False
        target = self._find_interact_target()
        if target == 'portal':
            route_warning = (self.route_state == 'survey' and not self.route_sealed)
            if int(getattr(self, 'floor', 1)) >= S.FLOORS:
                self.ask_confirm('进入传送门', '离开本关将放弃勘测' if route_warning else '前往下一关，无法返回',
                                 pygame.K_e, self._next_floor)
            else:
                self.ask_confirm('进入下一间', '继续深入本层',
                                 pygame.K_e, self._next_floor)
            return True
        if target is not None:
            if getattr(target, 'needs_confirm', False):
                title, sub = target.confirm_text()
                if title:
                    self.ask_confirm(title, sub, pygame.K_e,
                                     lambda pk=target: pk.interact(self))
                    return True
            # 返回交互是否真的发生了（例如金币不足时购买会被拒绝）
            return bool(target.interact(self))
        return False

    # ================================================================ 更新
    def add_hitstop(self, sec):
        """请求一次打击停顿（需求 20）。

        命中/击杀/受击时把**世界** dt 冻结极短时间，打击感瞬间变"实"。
        多条保护：
          - 取最大值（不叠加）并夹到 HITSTOP_MAX；
          - 冷却 HITSTOP_COOLDOWN：两次触发之间至少间隔这么久，
            否则"每帧都命中"的高射速场景会把世界时间永久压低（= 又顿又粘）。
        """
        try:
            cd = float(getattr(self, '_hitstop_cd', 0.0) or 0.0)
            if cd > 0:
                return
            v = min(S.HITSTOP_MAX, max(float(sec), float(self.hitstop or 0.0)))
            self.hitstop = v
            self._hitstop_cd = float(S.HITSTOP_COOLDOWN)
        except Exception:
            pass

    def update(self, dt):
        # 需求 20：打击停顿期间，**世界**时间几乎不推进（敌人/子弹/陷阱定住），
        # 但**玩家移动与瞄准始终按真实 dt 走**。
        #
        # 血泪教训：曾把 wdt 作用到玩家身上，结果"每帧都有命中"
        # （高射速武器 / 多个敌人）时 hitstop 被无限刷新，
        # 世界速度被永久锁死在 HITSTOP_SCALE=6%，玩家几乎无法移动。
        # 打击感应该只冻结"被打中的那个世界"，绝不冻结玩家自己的操作。
        if self.hitstop > 0:
            self.hitstop = max(0.0, self.hitstop - dt)
            wdt = dt * S.HITSTOP_SCALE
        else:
            wdt = dt
        if getattr(self, '_hitstop_cd', 0.0) > 0:
            self._hitstop_cd = max(0.0, self._hitstop_cd - dt)
        self.time += dt
        if self.time > 1e8:
            self.time = 0.0
        st = self.state
        if st == 'playing':
            self.total_time += dt
            self._update_playing(dt, wdt)
        elif st in ('gameover', 'victory', 'levelclear'):
            self.fx.update(dt)
            self._update_camera()
        elif st == 'story':
            self.story_t += dt
            if self.transition_lock > 0:
                self.transition_lock = max(0.0, self.transition_lock - dt)
            self.fx.update(dt)
            self._update_camera()
        elif st in ('title', 'help', 'paused', 'lobby', 'talent', 'changelog',
                    'slots', 'slot_create', 'slot_confirm'):
            self.fx.update(dt)
            self._update_camera()
        # 二次确认弹窗的计时（用于淡入）
        if self.confirm_prompt is not None:
            self.confirm_t = getattr(self, 'confirm_t', 0.0) + dt

    def _update_camera(self):
        sx = self.fx.shake_x if self.fx.shake > 0 else 0.0
        sy = self.fx.shake_y if self.fx.shake > 0 else 0.0
        self.cam = (S.CAM_OFF[0] + sx, S.CAM_OFF[1] + sy)

    def _update_playing(self, dt, wdt=None):
        """dt = 真实时间（玩家移动/瞄准/计时用）；wdt = 世界时间（受打击停顿缩放）。

        玩家操作永不受 hitstop 影响，否则高射速时会"粘住"无法移动。
        """
        if wdt is None:
            wdt = dt
        if self.room is None or not self.player.alive:
            self.fx.update(dt)
            self._update_camera()
            return
        inp = self.read_input()
        pl = self.player
        self.char_skill_cd = max(0.0, self.char_skill_cd - dt)
        if getattr(self, 'combo_t', 0.0) > 0:
            self.combo_t = max(0.0, self.combo_t - dt)
            if self.combo_t <= 0.0:
                self.combo_count = 0
        # ---- 玩家：始终用真实 dt（打击停顿不冻结玩家手感）
        pl.update(self, dt, inp)
        if self.drink_buffs.get('dew', 0):
            pl.energy = min(pl.max_energy,
                            pl.energy + 1.0 * self.drink_buffs['dew'] * dt)
        self.fire_cool = pl.cool

        # ---- 需求：污染渐近减益（持续侵蚀）
        self._update_pollution(dt)

        # ---- 防卡死：每帧兜底 + 连续零位移检测
        self._last_mx = float(inp.get('mx', 0.0))
        self._last_my = float(inp.get('my', 0.0))
        self._diag_input(inp)
        self._ensure_player_free()
        self._check_stuck(dt)

        # ---- 世界：用 wdt（被打击停顿缩放）
        for e in list(self.enemies):
            if e.alive:
                e.update(self, wdt)

        for b in list(self.bullets):
            if b.alive:
                b.update(self, wdt)

        for p in list(self.pickups):
            if p.alive:
                p.update(self, wdt)

        for p in list(self.props):
            p.update(self, wdt)

        # ---- 场景交互物（需求 3：陷阱 / 掩体 / 洞穴）
        self.room.update_hazards(self, wdt)

        self.fx.update(dt)
        self._update_camera()

        # ---- 清理
        self.bullets = [b for b in self.bullets if b.alive]
        self.enemies = [e for e in self.enemies if e.alive]
        self.room.props = [p for p in self.room.props if p.alive]
        self.room.pickups = [p for p in self.room.pickups if p.alive]
        self.room.traps = [t for t in self.room.traps if t.alive]
        self.room.covers = [c for c in self.room.covers if c.alive]
        if self.boss is not None and not self.boss.alive:
            self.boss = None

        # ---- 关卡计时器
        if self.banner_t > 0:
            self.banner_t = max(0.0, self.banner_t - dt)
        if self.collection_popup:
            self.collection_popup['t'] -= dt
            if self.collection_popup['t'] <= 0:
                self.collection_popup = None
        if self.hint_t > 0:
            self.hint_t = max(0.0, self.hint_t - dt)
        if self.trans_fade > 0:
            self.trans_fade = max(0.0, self.trans_fade - dt)
        for _t in self.toasts:
            _t['t'] += dt
        self.toasts = [_t for _t in self.toasts if _t['t'] < _t['life']]

        # ---- 房间清空判定
        if (self.room.enemies_spawned and not self.room.cleared
                and not any(e.alive for e in self.enemies)):
            if self.room.wave_plans and self.room.wave_index + 1 < len(self.room.wave_plans):
                self.room.wave_index += 1
                self._spawn_room(self.room)
                self.room.refresh_doors(locked=True)
                self.banner_text = f'第 {self.room.wave_index + 1}/3 轮来袭'
                self.banner_t = 1.4
                self.audio.play('lock')
            else:
                self.room.cleared = True
                self.room.refresh_doors(locked=False)
                if self.room.kind in ('normal', 'boss'):
                    from .dungeon import SCENE_CHEST_BIAS
                    sc_bias = SCENE_CHEST_BIAS.get((self.level_state or {}).get('scene'), 0.0)
                    luck_b = float((getattr(self, 'run_stats', None) or {}).get('luck', 0.0) or 0.0)
                    ckey, ctier = GD.roll_chest(self.rng, floor_bias=.10 * (self.floor - 1) + sc_bias + luck_b)
                    self.pickups.append(Pickup(S.ROOM_CX - 74, S.ROOM_CY + 45,
                                               'chest', ckey=ckey, ctier=ctier))
                self.banner_text = '三轮已清空 · 奖励宝箱出现'
                self.banner_t = 1.7
                self.audio.play('door')
                if (self.route_state == 'survey' and self.route_room ==
                        (self.room.gx, self.room.gy)):
                    self.route_sealed = True
                    self.toast('样本已封存 · 前往出口',
                               '阀门关闭后，监测读数短时下降。执行人栏已损毁。',
                               life=2.4)
                    self.audio.play('lock')
                self._maybe_open_portal()

        # 传送门只展示可交互状态；必须由 request_interact 二次确认后推进。
        self.room.update_portal(dt)

        # ---- 交互提示（与 request_interact 共用同一目标判定）
        target = self._find_interact_target()
        self.prompt = None if (target is None or target == 'portal') else target

        # ---- 房间切换
        if self.trans_fade <= 0.001:
            for d in list(self.room.open_doors):
                if S.DOOR_TRIGGER[d](pl):
                    vx, vy = S.DIR_VEC[d]
                    if self.enter_room(self.room.gx + vx, self.room.gy + vy,
                                       S.OPPOSITE[d]):
                        self.audio.play('door')
                    break

    # ================================================================ 渲染
    def _draw_world(self):
        c = self.canvas
        a = self.assets
        cam = self.cam
        self.room.draw_bg(c, cam, a)
        if self.room.portal is not None:
            self.room.draw_portal(c, cam, a, self.room.portal_t)

        self.fx.draw_under(c, cam)

        # 陷阱底盘 / 洞穴（角色脚下）
        self.room.draw_hazards_under(c, cam, a)

        # 按 y 排序，保证前后遮挡正确
        entries = []
        for p in self.room.props:
            if p.alive:
                entries.append((p.y, 0, p))
        for cv in self.room.covers:
            if cv.alive:
                entries.append((cv.y, 0, cv))
        for p in self.room.pickups:
            if p.alive:
                entries.append((p.y, 1, p))
        for e in self.enemies:
            if e.alive:
                entries.append((e.y, 2, e))
        if self.player.alive:
            entries.append((self.player.y, 3, self.player))
        entries.sort(key=lambda it: (it[0], it[1]))

        for _, kind, obj in entries:
            if kind == 0:
                obj.draw(c, cam, a)
            elif kind == 1:
                obj.draw(c, cam, a)
            elif kind == 2:
                obj.draw(c, cam, a)
            else:
                obj.draw(c, cam, a, self)

        self.room.draw_doors(c, cam, a)
        if self.route_state == 'survey' and not self.route_sealed and self.route_room:
            from .route35 import next_door
            direction = next_door(self.dungeon, (self.room.gx, self.room.gy),
                                  self.route_room)
            if direction:
                x = 15 if direction == 'W' else (S.ROOM_PX_W - 15 if direction == 'E' else S.ROOM_CX)
                y = 21 if direction == 'N' else (S.ROOM_PX_H - 21 if direction == 'S' else S.ROOM_CY)
                x, y = int(x + cam[0]), int(y + cam[1])
                pygame.draw.rect(c, (37, 37, 45), (x - 13, y - 8, 26, 16))
                pygame.draw.rect(c, (243, 184, 91), (x - 13, y - 8, 26, 16), 2)
                for offset in (-9, -2, 5):
                    pygame.draw.line(c, (243, 184, 91),
                                     (x + offset, y - 6), (x + offset + 5, y + 6), 1)
        for b in self.bullets:
            b.draw(c, cam, a)
        # 角色层之上：地刺 / 电场 / 喷焰
        self.room.draw_hazards_over(c, cam, a)
        self.fx.draw_over(c, cam)

    def _draw_crosshair(self, surf, scale, off):
        """在**窗口坐标系**画准星。

        [!] 历史 bug：准星原本画在 640×360 的逻辑画布上，再被整体放大 2~3 倍，
        于是准星又糊又粗；同时系统箭头没隐藏，压在准星上面挡住瞄准点。
        现在改为直接画在缩放后的窗口 Surface 上（线条永远是 1px），
        并隐藏系统光标。
        """
        x, y = self.mouse_canvas
        if not (0 <= x <= S.VIEW_W and 0 <= y <= S.VIEW_H):
            return
        # 逻辑坐标 -> 窗口坐标
        px = int(x * scale + off[0])
        py = int(y * scale + off[1])
        if not (0 <= px <= surf.get_width() and 0 <= py <= surf.get_height()):
            return
        g = pygame.Surface((26, 26), pygame.SRCALPHA)
        cx = cy = 13
        col = (255, 255, 255, 175)
        dark = (10, 8, 16, 120)
        # 先描一圈暗边，保证在任何背景上都看得清
        pygame.draw.circle(g, dark, (cx, cy), 7, 3)
        pygame.draw.circle(g, col, (cx, cy), 6, 1)
        pygame.draw.line(g, dark, (cx, cy - 11), (cx, cy - 4), 3)
        pygame.draw.line(g, dark, (cx, cy + 4), (cx, cy + 11), 3)
        pygame.draw.line(g, dark, (cx - 11, cy), (cx - 4, cy), 3)
        pygame.draw.line(g, dark, (cx + 4, cy), (cx + 11, cy), 3)
        pygame.draw.line(g, col, (cx, cy - 10), (cx, cy - 5), 1)
        pygame.draw.line(g, col, (cx, cy + 5), (cx, cy + 10), 1)
        pygame.draw.line(g, col, (cx - 10, cy), (cx - 5, cy), 1)
        pygame.draw.line(g, col, (cx + 5, cy), (cx + 10, cy), 1)
        surf.blit(g, (px - 13, py - 13))

    def draw(self):
        c = self.canvas
        st = self.state
        if st == 'title':
            hud.draw_title(c, self)
        elif st in ('slots', 'slot_create', 'slot_confirm') or st == 'help':
            if st == 'help':
                hud.draw_title(c, self)
                hud.draw_help(c, self)
            else:
                hud.draw_slots(c, self)
        elif st == 'changelog':
            hud.draw_changelog(c, self)
        elif st == 'paused':
            if self.room is not None:
                self._draw_world()
                hud.draw_hud(c, self)
            hud.draw_pause(c, self)
        elif st == 'gameover':
            if self.room is not None:
                self._draw_world()
            hud.draw_gameover(c, self)
        elif st == 'victory':
            if self.room is not None:
                self._draw_world()
            hud.draw_victory(c, self)
        elif st == 'levelclear':
            if self.room is not None:
                self._draw_world()
            hud.draw_levelclear(c, self)
        elif st == 'lobby':
            hud.draw_lobby(c, self)
        elif st == 'route_choice':
            self._draw_world()
            hud.draw_route_choice(c, self)
        elif st == 'talent':
            hud.draw_talent(c, self)
        elif st == 'story':
            hud.draw_story(c, self)
        else:
            c.fill(S.C_BG)
            self._draw_world()
            hud.draw_hud(c, self)
            hud.draw_flash(c, self)
            hud.draw_transition(c, self)
            hud.draw_collection_popup(c, self)
        # 需求 18：二次确认浮层 —— 画在所有界面之上
        if st not in ('title', 'help', 'changelog', 'slots',
                      'slot_create', 'slot_confirm'):
            hud.draw_confirm(c, self)

    def _present(self):
        if self.window is None:
            return
        w, h = self.window.get_size()
        try:
            if self.scale == 1 and (w, h) == (S.VIEW_W, S.VIEW_H):
                self.window.blit(self.canvas, (0, 0))
            else:
                scaled = pygame.transform.scale(
                    self.canvas, (S.VIEW_W * self.scale, S.VIEW_H * self.scale))
                if self.fullscreen:
                    self.window.fill((0, 0, 0))
                self.window.blit(scaled, self.view_off)
            # 准星画在窗口层：不参与 640×360 -> 1280×720 的放大，线宽永远是 1px
            if not self.headless and self.show_aim and not self.collection_popup:
                try:
                    if pygame.mouse.get_focused():
                        self._draw_crosshair(self.window, self.scale, self.view_off)
                except Exception:
                    pass
            pygame.display.flip()
        except Exception:
            pass

    # ================================================================ 主循环
    def run(self):
        try:
            while self.running:
                dt = self.clock.tick(S.FPS) / 1000.0
                if dt > S.MAX_DT:
                    dt = S.MAX_DT
                self._events()
                self.update(dt)
                self.draw()
                self._present()
        finally:
            self._write_save()
            # 退出前把系统光标还给玩家，否则回到桌面会发现鼠标"不见了"
            try:
                pygame.mouse.set_visible(True)
            except Exception:
                pass
            pygame.quit()

    # 供自动化测试使用的单帧步进
    def step(self, dt=1.0 / 60.0, actions=None):
        if actions is not None:
            self.inp_override = actions
        self.update(dt)
        self.draw()
        return self.state
