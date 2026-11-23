# -*- coding: utf-8 -*-
"""关卡推进层（需求 2 / 10 / 17）。

把 `chapter.py` 的场景定义 + `save.py` 的存档串成一条可玩的推进线：

    选场景 -> 逐关推进(5 关) -> 场景通关 -> 检查副本解锁 -> 选下一个场景

设计要点
--------
- **单一事实来源**：进度只存在 `profile` 里（chapter / stage / 已通关场景 /
  已解锁副本 / bonus_unlocked），局内状态从它派生，不反向依赖。
- **场景推进与"关"解耦**：`level_state` 是喂给 Game 的字典，
  含 scene / scene_idx / stage_idx / diff / kind / intro。
- **只读查询 + 显式提交**：`plan_*` 只算不写；`commit_*` 才落存档。
  这样异常退出时存档不会被推到"半关"状态。
"""
from . import chapter as C
from . import codex as X

# ================================================================ 关卡状态


def level_state(prof):
    """当前存档指向的关卡 -> 喂给 Game._start_floor 的字典。

    返回 None 表示"还没有开始任何关卡"（需要先在客厅选场景）。
    """
    if prof.get('run') is None:
        return None
    return dict(prof['run'])


def make_run(scene_key, stage_idx, order):
    """构造一个关卡进度字典。

    order 是 scene_order(prof) 的下标，用来算难度（保证全局单调递增）。
    """
    diff = C.difficulty(order, stage_idx)
    return {
        'scene': scene_key,
        'scene_idx': int(order),
        'stage_idx': int(stage_idx),
        'diff': (float(diff[0]), float(diff[1])),
        'kind': C.stage_kind(stage_idx),
        'intro': C.stage_intro(scene_key, stage_idx),
        'floors': 1,
    }


def start_scene(prof, scene_key):
    """从某场景第 1 关开始（会写入 prof['run']）。"""
    order = _order_index(prof, scene_key)
    if order is None:
        return False
    prof['run'] = make_run(scene_key, 0, order)
    prof['chapter'] = order
    prof['stage'] = 0
    _mark_visited(prof, scene_key)
    return True


def advance(prof):
    """通关一关。返回 ('next'|'scene_clear'|'game_clear', payload)。

    不进下一关的 `run` 写入由调用方决定（需要在过场界面之后调
    `start_scene` 或 `next_stage`），保证"过场能被打断而不丢进度"。
    """
    run = prof.get('run')
    if run is None:
        return 'next', None
    scene = run['scene']
    st = int(run['stage_idx'])
    # 线性推进：无条件把本关记为已通关（不依赖调用方是否记得调 next_stage）
    bump_scene_prog(prof, scene, st)
    if st + 1 < C.STAGES_PER_SCENE:
        return 'next', {'scene': scene, 'stage_idx': st + 1}
    # 场景最后一关通关
    _mark_cleared(prof, scene)
    if scene == C.BONUS:
        prof['run'] = None
        prof['main_done'] = True
        return 'game_clear', {'scene': scene}
    if scene == C.MAIN[-1]:
        prof['main_done'] = True
        return 'scene_clear', {'scene': scene, 'finale': True}
    return 'scene_clear', {'scene': scene}


def next_stage(prof, scene_key, stage_idx):
    order = _order_index(prof, scene_key)
    if order is None:
        return False
    prof['run'] = make_run(scene_key, stage_idx, order)
    prof['chapter'] = order
    prof['stage'] = int(stage_idx)
    _mark_visited(prof, scene_key)
    return True


def clear_run(prof):
    """把 run 清掉（回客厅）。"""
    prof['run'] = None


def reset_cycle(prof):
    """Start a new playthrough while preserving permanent clear records."""
    history = prof.setdefault('best_scene_prog', {})
    for scene, stages in (prof.get('scene_prog') or {}).items():
        history[scene] = max(int(history.get(scene, 0)), int(stages or 0))
    prof['scene_prog'] = {}
    prof['run'] = None
    prof['run_checkpoint'] = None
    prof['chapter'] = 0
    prof['stage'] = 0


# ================================================================ 解锁


def _order_index(prof, scene_key):
    """场景在**展示顺序**里的下标（用于难度插值与展示排序）。

    展示顺序固定为 MAIN + DUNGEONS + BONUS，与是否解锁无关 ——
    这样难度曲线不会因为玩家解锁/未解锁副本而漂移。
    """
    try:
        return scene_order(prof).index(scene_key)
    except ValueError:
        return None


def scene_order(prof):
    """**展示顺序**：7 个主题场景全部列出（含未解锁的，UI 显示锁）。

    1.4 起这是"地图展示顺序"，不再是"可进入顺序" —— 玩家不能在里挑，
    只能按 next_target() 推进。保留此函数是为了让客厅/地图能画全貌。
    """
    return list(C.MAIN) + list(C.DUNGEONS.keys()) + [C.BONUS]


def visible_order(prof):
    """**玩家已解锁**的场景（用于地图高亮）。"""
    out = [k for k in C.MAIN if main_chain_unlocked(prof, k)]
    for k, d in C.DUNGEONS.items():
        if k in prof.get('unlocked_dungeons', []):
            try:
                out.insert(out.index(d['after']) + 1, k)
            except ValueError:
                out.append(k)
    if prof.get('bonus_unlocked'):
        out.append(C.BONUS)
    return out


# ---------------------------------------------------------------- 线性推进
# 需求 1：不允许选关，必须 1 -> 2 -> 3 -> 4 依次推进。
#
# 实现方式：给每个场景记一个"已通关到第几关"（scene_prog[scene] = 0..5），
# 再由它推导出**唯一允许进入的关卡**。客厅不再让玩家挑场景，只显示
# "下一站"以及锁定中/已通关的场景（纯展示，不可点入）。
#
# scene_prog 的推进规则：
#   · 某关通关后 prog = max(prog, stage_idx + 1)
#   · prog >= STAGES_PER_SCENE 视为该场景通关
#   · 主线场景必须**前一个场景通关**才解锁下一个
#   · 副本解锁后是"可选支线"，不阻塞主线，但一旦进入就必须打通
def scene_prog(prof, scene_key):
    """该场景已通关到第几关（0 = 一关没通）。"""
    return int((prof.get('scene_prog') or {}).get(scene_key, 0))


def set_scene_prog(prof, scene_key, v):
    sp = prof.setdefault('scene_prog', {})
    sp[scene_key] = max(0, min(int(C.STAGES_PER_SCENE), int(v)))
    return sp[scene_key]


def bump_scene_prog(prof, scene_key, stage_idx):
    """通关第 stage_idx 关（0 起）-> 进度至少推进到 stage_idx+1。"""
    return set_scene_prog(prof, scene_key, int(stage_idx) + 1)


def scene_stage_done(prof, scene_key, stage_idx):
    """该场景第 stage_idx 关是否已通关。"""
    return scene_prog(prof, scene_key) > int(stage_idx)


def is_scene_cleared(prof, scene_key):
    if scene_key in prof.get('cleared_scenes', []):
        return True
    return scene_prog(prof, scene_key) >= C.STAGES_PER_SCENE


def main_chain_unlocked(prof, scene_key):
    """主线场景是否已解锁（前一个主线场景必须通关）。

    MAIN 是 [crust, sewer, facility, core]，逐一串行。
    """
    if scene_key not in C.MAIN:
        return False
    i = C.MAIN.index(scene_key)
    if i == 0:
        return True
    return is_scene_cleared(prof, C.MAIN[i - 1])


def next_target(prof):
    """返回玩家**当前唯一应该去**的关卡：{'scene', 'stage_idx', 'locked'}。

    这是线性推进的单一事实来源 —— 客厅、开始游戏、断点续玩全用它。

    规则：
      1. 若存档里有未完成的 run（断点），直接用它。
      2. 否则按主线顺序找第一个"没通关"的场景：
         · 该场景没通关 -> 去它的下一关
         · 全部主线通关 -> 若无奖励副本则返回 bonus_pending（去客厅购买）
      3. 副本是支线：只有玩家主动进入才会出现在这里。
    """
    # 1) 断点优先（但已通关的断点要忽略，否则会卡在刚打完的那一关）
    run = prof.get('run')
    if isinstance(run, dict) and run.get('scene'):
        sc = run['scene']
        si = int(run.get('stage_idx', 0))
        if not scene_stage_done(prof, sc, si):
            return {'scene': sc, 'stage_idx': si,
                    'locked': False, 'resume': True}
        prof['run'] = None      # 陈旧断点：清掉，继续往下算
    # 旧版及异常中断的通关档可能仍保留全满进度。进入客厅时修复为新一轮。
    if all(scene_prog(prof, key) >= C.STAGES_PER_SCENE for key in C.MAIN):
        prof['main_done'] = True
        reset_cycle(prof)
    # 2) 主线推进
    for k in C.MAIN:
        if not main_chain_unlocked(prof, k):
            # 前一个主线没通关 —— 理论上不该走到这，回退到那个场景
            i = C.MAIN.index(k)
            prev = C.MAIN[max(0, i - 1)]
            pg = scene_prog(prof, prev)
            return {'scene': prev,
                    'stage_idx': min(pg, C.STAGES_PER_SCENE - 1),
                    'locked': False}
        pg = scene_prog(prof, k)
        if pg < C.STAGES_PER_SCENE:
            return {'scene': k, 'stage_idx': pg, 'locked': False}
    # 3) 主线全通
    return {'scene': None, 'stage_idx': 0, 'locked': False,
            'main_done': True,
            'bonus_available': bool(prof.get('bonus_unlocked'))
            or bonus_available(prof)}


def _patch_list(prof, key):
    if key not in prof or not isinstance(prof[key], list):
        prof[key] = []
    return prof[key]


def _mark_visited(prof, scene_key):
    v = _patch_list(prof, 'visited_scenes')
    if scene_key not in v:
        v.append(scene_key)


def _mark_cleared(prof, scene_key):
    c = _patch_list(prof, 'cleared_scenes')
    if scene_key not in c:
        c.append(scene_key)
    st = prof.setdefault('stats', {})
    st['best_chapter'] = max(st.get('best_chapter', 0), prof.get('chapter', 0) + 1)


def is_scene_unlocked(prof, scene_key):
    """场景是否可进入。

    1.4 线性推进后语义变化：
      · 主线：必须前一个主线场景通关（不再是"恒解锁"）
      · 副本：unlocked_dungeons 里有才算
      · 奖励副本：bonus_unlocked
    """
    if scene_key in C.MAIN:
        return main_chain_unlocked(prof, scene_key)
    if scene_key == C.BONUS:
        return bool(prof.get('bonus_unlocked'))
    return scene_key in prof.get('unlocked_dungeons', [])


# -------------------------------------------------- 副本解锁


def dungeon_progress(prof, dkey):
    """返回 (进度列表, 是否达成, 条件文案, 提示)。

    进度列表每项：(标签, 当前值文案, 目标文案, 是否已满足)
    这样 UI 可以一条一条打勾，玩家知道还差什么。
    """
    d = C.DUNGEONS.get(dkey)
    if not d:
        return ([], False, '', '')
    cond = d['cond']
    after = d['after']
    best = (prof.get('scene_best') or {}).get(after) or {}
    cleared = is_scene_cleared(prof, after)
    items = []
    if cond.get('cleared'):
        items.append(('通关「%s」' % C.scene_label(after),
                      '已通关' if cleared else '未通关',
                      '需通关', cleared))
    if cond.get('kills', 0) > 0:
        cur = int(best.get('kills', 0))
        items.append(('单局击杀', '%d' % cur, '%d' % cond['kills'],
                      cur >= cond['kills']))
    if 'trap_hits' in cond:
        v = best.get('trap_hits')
        if v is None:
            items.append(('踩中陷阱', '未记录', '≤ %d 次' % cond['trap_hits'],
                          True))
        else:
            items.append(('踩中陷阱', '%d 次' % v,
                          '≤ %d 次' % cond['trap_hits'],
                          v <= cond['trap_hits']))
    if 'bomber_hits' in cond:
        v = best.get('bomber_hits')
        if v is None:
            items.append(('被自爆波及', '未记录',
                          '≤ %d 次' % cond['bomber_hits'], True))
        else:
            items.append(('被自爆波及', '%d 次' % v,
                          '≤ %d 次' % cond['bomber_hits'],
                          v <= cond['bomber_hits']))
    if cond.get('no_death'):
        v = bool(best.get('no_death', False))
        items.append(('零死亡通关', '已达成' if v else '未达成', '需达成', v))
    if cond.get('low_hp'):
        v = bool(best.get('low_hp', False))
        items.append(('残血通关', '已达成' if v else '未达成', '需达成', v))
    ok = C._cond_met(cond, best, cleared)
    return (items, ok, d['cond_text'], d.get('hint', ''))


def check_dungeon_unlock(prof, dkey, scene_stats=None):
    """判断副本能否解锁。scene_stats 是刚打完那个前置场景的成绩。"""
    d = C.DUNGEONS.get(dkey)
    if not d or dkey in prof.get('unlocked_dungeons', []):
        return False
    if scene_stats:
        merge_scene_best(prof, d['after'], scene_stats)
    _items, ok, _t, _h = dungeon_progress(prof, dkey)
    if not ok:
        return False
    lst = _patch_list(prof, 'unlocked_dungeons')
    lst.append(dkey)
    return True


# 只增不减（越大越好）的字段
_BEST_UP = ('kills', 'items', 'bosses')
# 只减不增（越小越好）的字段；None 表示"尚未记录"
_BEST_DOWN = ('trap_hits', 'bomber_hits')


def merge_scene_best(prof, scene_key, stats):
    """把本次成绩并入该场景的历史最好成绩。

    数值型：击杀/道具 取最大；陷阱命中/被自爆波及 取最小；布尔型一旦为真
    就永久保留。这样"刷条件"是单调向前的，不会因为某次手滑把进度清零。
    """
    sb = prof.setdefault('scene_best', {})
    cur = sb.get(scene_key) or {'kills': 0, 'no_death': False, 'items': 0,
                                'deaths': 0}
    for k in _BEST_UP:
        if k in stats:
            cur[k] = max(cur.get(k, 0), int(stats.get(k, 0)))
    cur.setdefault('kills', 0)
    for k in ('no_death', 'low_hp', 'cleared_once'):
        if stats.get(k):
            cur[k] = True
    for k in _BEST_DOWN:
        if k in stats and stats[k] is not None:
            v = int(stats[k])
            old = cur.get(k)
            cur[k] = v if old is None else min(old, v)
    # deaths 取最小（越少越好）
    if 'deaths' in stats:
        v = int(stats.get('deaths', 0))
        old = cur.get('deaths')
        cur['deaths'] = v if old is None else min(old, v)
    if 'items' not in cur:
        cur['items'] = 0
    sb[scene_key] = cur
    return cur


def scan_unlocks(prof):
    """扫一遍所有副本，返回本次新解锁的 key 列表（用于弹提示）。"""
    new = []
    for k in C.DUNGEONS:
        if k in prof.get('unlocked_dungeons', []):
            continue
        if check_dungeon_unlock(prof, k):
            new.append(k)
    return new


# -------------------------------------------------- 奖励副本


def bonus_available(prof):
    """奖励副本是否已可购买（打完主线最终场景 + 尚未购买）。"""
    return (not prof.get('bonus_unlocked')
            and is_scene_cleared(prof, C.MAIN[-1]))


def bonus_price(prof):
    """奖励副本售价（金币）。"""
    return C.BONUS_PRICE


def bonus_funds(prof):
    """返回 (金币, 钻石, 需要金币, 需要钻石)。"""
    return (int(prof.get('coins', 0)), int(prof.get('diamonds', 0)),
            int(C.BONUS_PRICE), int(getattr(C, 'BONUS_PRICE_DIA', 0)))


def can_buy_bonus(prof, want=False):
    """能否购买奖励副本。want=True 时额外要求"确实可买"（未买过）。

    注意：默认只判断钱够不够，方便 UI 在"还没通关"时也能显示价格与差额。
    """
    c, d, need_c, need_d = bonus_funds(prof)
    money_ok = (c >= need_c and d >= need_d)
    if not want:
        return money_ok
    return bonus_available(prof) and money_ok


def bonus_missing(prof):
    """还差多少（用于 UI 提示）。返回 (差金币, 差钻石)。"""
    c, d, need_c, need_d = bonus_funds(prof)
    return (max(0, need_c - c), max(0, need_d - d))


def buy_bonus(prof):
    """用金币购买奖励副本。调用前应先用 can_buy_bonus(prof, want=True)。"""
    if not can_buy_bonus(prof, want=True):
        return False
    c, d, need_c, need_d = bonus_funds(prof)
    if need_c:
        prof['coins'] = c - need_c
    if need_d:
        prof['diamonds'] = d - need_d
    prof['bonus_unlocked'] = True
    return True


# ================================================================ 污染减益


def pollution(scene_key, stage_idx=0):
    return C.pollution(scene_key, stage_idx)


def pollution_lines(scene_key, stage_idx=0):
    return C.pollution_lines(scene_key, stage_idx)


def pollution_warning(scene_key, stage_idx=0):
    return C.pollution_warning(scene_key, stage_idx)


# ================================================================ 剧情


def intro_lines():
    return list(C.INTRO)


def scene_story(scene_key, phase):
    """phase: 'enter' / 'clear'。返回 (标题, 副标题, [文本行], tint)。"""
    info = C.scene_info(scene_key)
    lines = info.get(phase) or []
    return (info.get('name', scene_key), info.get('sub', ''),
            list(lines), info.get('tint', (140, 140, 140)))


def scene_name(scene_key):
    return C.scene_label(scene_key)


def scene_tint(scene_key):
    return C.scene_info(scene_key).get('tint', (140, 140, 140))


# ================================================================ 局内提示


def enemy_intro(key):
    """(标题, 副标题) 或 None。用于"首次遇到新怪"提示（需求 15）。"""
    v = X.ENEMY_CODEX.get(key)
    if not v:
        return None
    tag = {'small': '小怪', 'elite': '精英', 'boss': '首领',
           'bigboss': '污染核心', 'rare': '稀有'}.get(v[2], '敌人')
    return (f'新 {tag}：{v[0]}', v[3])


def material_intro(key):
    from . import gamedata as G
    v = G.MATERIALS.get(key)
    if not v:
        return None
    return (f'新材料：{v[0]}', v[2])


def collect_intro(key):
    v = X.COLLECTS.get(key)
    if not v:
        return None
    tier = '珍品' if v[1] == 'superb' else '工艺品'
    return (f'{tier}：{v[0]}', v[2])


def weapon_quality_intro(qkey):
    from . import gamedata as G
    v = G.QUALITIES.get(qkey)
    if not v:
        return None
    return (f'{v["name"]}品质武器', v.get('perk', '随强化等级提升威力'))
