# -*- coding: utf-8 -*-
"""进度存档：个人 ID、三个槽位、自动保存、异常退出保护。

设计要点
--------
* 一台设备最多 3 个存档槽（需求 10）。新建第 4 个时必须选择覆盖哪个。
* 玩家的一切行为都会自动保存（关键节点 + 定时兜底），异常退出也不丢。
* "脱离卡死"会先存盘再退出，下次可从该存档继续（需求 7）。
* 落盘位置随平台：
    Windows  %APPDATA%/陆面过程模拟/
    macOS    ~/Library/Application Support/陆面过程模拟/
    Linux    ~/.local/share/陆面过程模拟/
* 写入用"临时文件 + 原子替换"，避免写到一半断电导致存档损坏。
"""
import json
import logging
import os
import shutil
import sys
import time

_logger = logging.getLogger('sk.save')
if not _logger.handlers:
    _logger.addHandler(logging.NullHandler())
_logged_save_exc = set()


def _log_save_exc(tag, exc, detail=''):
    """记录去重后的存档读写异常，绝不中断游戏流程。"""
    try:
        key = (tag, type(exc).__name__, str(detail))
        if key in _logged_save_exc:
            return
        if len(_logged_save_exc) >= 128:
            _logged_save_exc.clear()
        _logged_save_exc.add(key)
        _logger.warning('[%s] %s (%s: %s)', tag, detail, type(exc).__name__, exc)
    except Exception:
        pass

APP_DIR_NAME = '最后一片净土'
SAVE_FILE = 'profiles.json'
BACKUP_FILE = 'profiles.bak.json'
MAX_SLOTS = 3
SAVE_VERSION = 5

# 旧版存档目录名（改名前的「陆面过程模拟」）——仅用于一次性迁移
LEGACY_DIR_NAMES = ['陆面过程模拟', 'SoulKnightLite']


# ---------------------------------------------------------------- 路径
def data_dir():
    """跨平台的数据目录（存档/设置都放这里）。"""
    if sys.platform.startswith('win'):
        base = os.environ.get('APPDATA') or os.path.expanduser('~')
    elif sys.platform == 'darwin':
        base = os.path.join(os.path.expanduser('~'), 'Library', 'Application Support')
    else:
        base = os.environ.get('XDG_DATA_HOME') or os.path.join(
            os.path.expanduser('~'), '.local', 'share')
    return os.path.join(base, APP_DIR_NAME)


def save_path():
    return os.path.join(data_dir(), SAVE_FILE)


def backup_path():
    return os.path.join(data_dir(), BACKUP_FILE)


def _legacy_paths():
    """旧版数据目录下的存档路径（用于一次性迁移）。"""
    out = []
    base = os.path.dirname(data_dir())
    for nm in LEGACY_DIR_NAMES:
        out.append(os.path.join(base, nm, SAVE_FILE))
        out.append(os.path.join(base, nm, BACKUP_FILE))
    return out


def migrate_legacy():
    """把旧版本目录里的存档搬过来（只在目标档不存在时）。

    需求 17 改了游戏名，数据目录随之改变 —— 老玩家不该因此丢档。
    -> 返回被迁入的路径，没迁移则返回 None。
    """
    dst = save_path()
    if os.path.isfile(dst):
        return None
    for src in _legacy_paths():
        try:
            if os.path.isfile(src):
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copy2(src, dst)
                return dst
        except Exception as exc:
            _log_save_exc('save.migrate', exc, src)
            continue
    return None


# ---------------------------------------------------------------- 新档模板
def new_profile(pid, name):
    """一个全新的存档槽。所有字段都要有默认值，方便旧档向后兼容。"""
    return {
        'version': SAVE_VERSION,
        'id': pid,
        'name': name or ('漂泊者%d' % (pid + 1)),
        'created': time.time(),
        'played': 0.0,
        'updated': time.time(),
        # ---- 货币 ----
        'coins': 0,
        'diamonds': 0,
        # ---- 材料：key -> 数量 ----
        'materials': {},
        'route_first_rewards': [],
        # ---- 角色：已解锁的角色 key 列表 + 当前选中 ----
        'chars': ['scout'],
        'char': 'scout',
        # ---- 武器：已解锁 + 每把的强化等级 + 当前携带 ----
        'weapons': {'pistol': 0},
        'weapon': 'pistol',
        # ---- 技能 / 被动 强化等级 ----
        'skills': {},
        'passives': {},
        # ---- 图鉴：见过的怪物 / 武器 / 材料 / 收集品 ----
        'codex': {'enemy': [], 'weapon': [], 'material': [], 'collect': []},
        # ---- 收集品：已获得列表 + 展示台摆放 ----
        'collects': [],
        'showcase': [None, None, None, None, None, None],
        # ---- 天赋：临时（局内）不存，这里是永久解锁的 ----
        'talent_unlocked': [],
        # ---- 天赋词条：永久强化（客厅可升级）----
        'talent_levels': {},
        # ---- 场景/关卡进度（1.4：线性锁死，不可跳关）----
        'scene_prog': {},         # scene -> 已通关到第几关（0..5）
        'best_scene_prog': {},    # historical best, retained between playthroughs
        'main_done': False,       # 主线是否已通关
        'chapter': 0,             # 当前场景在可见顺序中的下标
        'stage': 0,               # 当前场景内进度（0..4）
        'visited_scenes': [],     # 去过的场景
        'cleared_scenes': [],     # 已通关的场景
        # 场景 -> 历史最好成绩，用于副本准入条件的"打勾"判定：
        #   kills        单局最高击杀（越大越好）
        #   items        单局最多拾取（越大越好）
        #   deaths       单局最少死亡（越小越好）
        #   trap_hits    单局最少踩中陷阱次数（越小越好）
        #   bomber_hits  单局最少被自爆波及次数（越小越好）
        #   no_death     是否零死亡通关过（布尔，一次达成永久保留）
        #   low_hp       是否残血（≤3 生命）通关过（布尔）
        'scene_best': {},
        'blueprints': {},       # 型号 -> 已发现的最高品质图纸
        'weapon_qualities': {}, # 型号 -> 已取得的最高品质武器
        'weapon_quality_levels': {},  # 高品质武器的独立强化等级
        'unlocked_dungeons': [],  # 已解锁的副本 id
        'bonus_unlocked': False,  # 奖励副本是否已付费解锁
        'story_seen': [],         # 已播放过的剧情片段 id
        'tips_seen': [],          # 已弹过的局内提示（新怪/材料/武器/收集品）
        # ---- 局内断点（供"异常退出后继续"）----
        'run': None,
        'run_checkpoint': None,  # 2.6: floor-entry resume snapshot
        # ---- 统计 ----
        'stats': {'kills': 0, 'deaths': 0, 'runs': 0, 'best_chapter': 0,
                  'boss_kills': 0, 'items': 0, 'chests': 0,
                  'play_seconds': 0.0},
        # ---- 设置（每档独立，手机/桌面可不同）----
        'settings': {
            'music': False, 'sfx': True, 'shake': False,
            'vibrate': False,           # 手机端震动（需求 11）
            'joystick': 'float',        # fixed / float（需求 14）
            'joy_sens': 1.0,            # 摇杆灵敏度
            'ui_scale': 1.0,
            'auto_fire': False,
        },
    }


def _migrate(p):
    """旧档升级：补齐缺失字段，不丢已有数据。"""
    old_version = int(p.get('version', 0) or 0)
    base = new_profile(p.get('id', 0), p.get('name', ''))
    for k, v in base.items():
        if k not in p:
            p[k] = v
        elif isinstance(v, dict) and isinstance(p.get(k), dict):
            for kk, vv in v.items():
                p[k].setdefault(kk, vv)
    p['version'] = SAVE_VERSION
    if old_version < 4:
        cp = p.get('run_checkpoint')
        if isinstance(cp, dict) and int(cp.get('floor', 1) or 1) > 1:
            from . import gamedata as GD
            p['coins'] = GD.clamp_coin(int(p.get('coins', 0)) + int(cp.get('coins', 0) or 0))
            p['run_checkpoint'] = None
        if isinstance(p.get('run'), dict):
            p['run']['floors'] = 1
    from . import chapter as C
    progress = p.get('scene_prog') or {}
    active = p.get('run')
    unfinished = isinstance(active, dict) and active.get('scene') and \
        int(progress.get(active['scene'], 0) or 0) <= int(active.get('stage_idx', 0) or 0)
    if not unfinished and all(
            int(progress.get(key, 0) or 0) >= C.STAGES_PER_SCENE for key in C.MAIN):
        p['main_done'] = True
        from . import progress as PR
        PR.reset_cycle(p)
    try:
        from . import gamedata as GD
        GD.sync_collect_characters(p)
    except Exception:
        pass
    return p


def _progress_score(p):
    """Compare complete profiles; stage progression outranks currency."""
    if not isinstance(p, dict):
        return (-1,)
    stages = dict(p.get('best_scene_prog') or {})
    for scene, count in (p.get('scene_prog') or {}).items():
        stages[scene] = max(int(stages.get(scene, 0)), int(count or 0))
    return (int(bool(p.get('main_done'))),
            sum(max(0, int(v or 0)) for v in stages.values()),
            len(p.get('cleared_scenes') or ()),
            len(p.get('unlocked_dungeons') or ()),
            len(set(p.get('collects') or ())),
            int((p.get('stats') or {}).get('best_chapter', 0) or 0),
            float(p.get('played', 0) or 0),
            float(p.get('updated', 0) or 0),
            float(p.get('created', 0) or 0))


def more_advanced(a, b):
    """Return the more advanced whole profile; ties retain the first."""
    return a if _progress_score(a) >= _progress_score(b) else b


def merge_route_claims(winner, other):
    """Keep one-time claims when two snapshots belong to the same character."""
    if not isinstance(winner, dict) or not isinstance(other, dict):
        return False
    if (winner.get('id') != other.get('id') or
            winner.get('created') != other.get('created')):
        return False
    claims = list(winner.get('route_first_rewards') or [])
    added = False
    for claim in other.get('route_first_rewards') or []:
        if isinstance(claim, str) and claim not in claims:
            claims.append(claim)
            added = True
    if added:
        winner['route_first_rewards'] = claims
    return added


# ---------------------------------------------------------------- 读写
class SaveStore:
    """存档仓库：管理 3 个槽位的读写。"""

    def __init__(self, path=None, legacy_paths=None):
        self.path = path or save_path()
        self.backup = os.path.join(os.path.dirname(self.path), BACKUP_FILE)
        self.legacy_paths = list(legacy_paths) if legacy_paths is not None else \
            (_legacy_paths() if path is None else [])
        self.data = {'version': SAVE_VERSION, 'slots': [None] * MAX_SLOTS,
                     'last': None}
        self.load()

    # ---- 磁盘 ----
    def load(self):
        chosen = [None] * MAX_SLOTS
        found = False
        last = None
        imported = False
        for p in dict.fromkeys([self.path, self.backup] + self.legacy_paths):
            try:
                if not os.path.isfile(p):
                    continue
                with open(p, 'r', encoding='utf-8') as f:
                    d = json.load(f)
                if not isinstance(d, dict) or not isinstance(d.get('slots'), list):
                    continue
                found = True
                if last is None:
                    last = d.get('last')
                for i, slot in enumerate(d['slots'][:MAX_SLOTS]):
                    if not isinstance(slot, dict):
                        continue
                    previous = chosen[i]
                    winner = more_advanced(previous, slot)
                    if winner is slot:
                        chosen[i] = slot.copy()
                        if p != self.path:
                            imported = True
                    if merge_route_claims(chosen[i],
                                          previous if winner is slot else slot):
                        imported = True
            except Exception as exc:
                _log_save_exc('save.load', exc, p)
                continue
        if not found:
            return False
        self.data = {'version': SAVE_VERSION,
                     'slots': [(_migrate(s) if s is not None else None)
                               for s in chosen], 'last': last}
        if imported:
            self.save()
        return True

    def _atomic_write(self, path, obj):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = path + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(obj, f, ensure_ascii=False, separators=(',', ':'))
            f.flush()
            os.fsync(f.fileno())
        # 替换前先把现有档备份一份
        if os.path.isfile(path):
            try:
                shutil.copy2(path, self.backup)
            except Exception as exc:
                _log_save_exc('save.backup', exc, self.backup)
        os.replace(tmp, path)

    def save(self):
        try:
            self._atomic_write(self.path, self.data)
        except Exception as exc:
            _log_save_exc('save.write', exc, self.path)        # 存档失败绝不能拖垮游戏

    # ---- 槽位 ----
    def slots(self):
        return list(self.data.get('slots') or [None] * MAX_SLOTS)

    def get(self, idx):
        s = self.data.get('slots') or []
        if 0 <= idx < len(s):
            return s[idx]
        return None

    def free_slot(self):
        """返回第一个空槽下标；没有则返回 None。"""
        for i, s in enumerate(self.slots()):
            if s is None:
                return i
        return None

    def create(self, idx, name):
        """在指定槽位建档（会覆盖该槽已有内容）。"""
        s = new_profile(idx, name)
        self.data['slots'][idx] = s
        self.data['last'] = s['id']
        self.save()
        return s

    def delete(self, idx):
        self.data['slots'][idx] = None
        if self.data.get('last') == idx:
            self.data['last'] = None
        self.save()

    def set_current(self, idx):
        self.data['last'] = idx
        self.save()

    def current(self):
        i = self.data.get('last')
        if isinstance(i, int):
            p = self.get(i)
            if p is not None:
                return p
        return None

    def flush(self, profile):
        """把某个档写回它自己的槽位，并按需落盘。"""
        if not isinstance(profile, dict):
            return
        idx = profile.get('id')
        slots = self.data['slots']
        if isinstance(idx, int) and 0 <= idx < len(slots):
            slots[idx] = profile
            self.data['last'] = idx
        self.save()


# ---------------------------------------------------------------- 便捷函数
_default = None


def store():
    """进程内单例。"""
    global _default
    if _default is None:
        _default = SaveStore()
    return _default
