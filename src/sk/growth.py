# -*- coding: utf-8 -*-
"""养成服务层（需求 4/5/6/7）：角色解锁、武器强化、技能/被动升级。

设计原则
--------
- **纯函数 + 显式提交**：`can_*` 只判断不写档，`do_*` 才扣费。
  这样客厅 UI 可以先"预演"（显示差多少钱/什么材料），再由玩家确认。
- **单一事实来源**：所有消耗计算都委托给 `gamedata`，
  UI 与逻辑不会各算一套。
- **失败必带回执**：所有 `do_*` 返回 `(是否成功, 提示文案)`，
  客厅直接把这个文案丢进 toast，不必自己拼错误信息。
"""
from . import gamedata as GD

# 永久天赋词条的等级上限（局内三选一可叠加 3 层，这里是局外永久强化）
TALENT_MAX_LV = 5

# ================================================================ 角色


def char_list(prof):
    """给客厅用的角色列表。

    每项：{key,name,desc,perk,hp,spd,energy,starter,owned,cur,afford,
           unlock_text,reason}
    prof 为 None（无存档环境，如无头测试）时退化为"只有初始角色"。
    """
    prof = prof or {}
    owned = list(prof.get('chars') or ['scout'])
    cur = prof.get('char') or 'scout'
    out = []
    for k in GD.CHAR_ORDER:
        c = GD.char(k)
        is_owned = k in owned
        if is_owned:
            ok, reason = True, ''
        elif not prof:
            ok, reason = False, '尚无存档'
        else:
            ok, reason = GD.can_unlock(prof, k)
        out.append({
            'key': k,
            'name': c['name'],
            'desc': c['desc'],
            'perk': c['perk'],
            'hp': c['hp'],
            'spd': c['spd'],
            'energy': c['energy'],
            'starter': c['starter'],
            'starter_name': GD_weapon_name(c['starter']),
            'owned': is_owned,
            'cur': (k == cur),
            'afford': ok,
            'unlock_text': GD.unlock_text(k, prof),
            'reason': reason,
        })
    return out


def GD_weapon_name(wkey):
    try:
        from . import weapon as W
        return W.get(wkey).name
    except Exception:
        return wkey


def select_char(prof, key):
    """切换当前角色。未解锁则返回失败。"""
    if prof is None:
        return False, '无存档'
    if key not in (prof.get('chars') or []):
        return False, '尚未解锁该角色'
    prof['char'] = key
    c = GD.char(key)
    prof['weapon'] = c['starter']
    return True, '已换上「%s」' % c['name']


def buy_char(prof, key):
    """解锁角色（扣金币/钻石/材料）。"""
    if prof is None:
        return False, '无存档'
    if key in (prof.get('chars') or []):
        return False, '该角色已解锁'
    ok, reason = GD.can_unlock(prof, key)
    if not ok:
        return False, reason
    GD.do_unlock(prof, key)
    c = GD.char(key)
    return True, '解锁角色「%s」' % c['name']


# ================================================================ 武器培养


def weapon_lv(prof, wkey):
    return max(int(((prof or {}).get('weapon_quality_levels') or {}).get(wkey, 0) or 0),
               int(((prof or {}).get('weapons') or {}).get(wkey, 0) or 0))


def weapon_info(prof, wkey):
    """单把武器的养成状态（供工坊列表）。"""
    from . import weapon as W
    spec = W.get(wkey)
    lv = weapon_lv(prof, wkey)
    q = W.quality_of(wkey)
    qs = GD.quality_of(q)
    nxt = None
    plan = ((prof or {}).get('blueprints') or {}).get(wkey)
    craft = plan == q and wkey not in ((prof or {}).get('weapon_qualities') or {})
    cost = GD.upgrade_cost(plan, 0) if craft else (
        GD.upgrade_cost(q, lv) if GD.quality_rank(q) > 2 else GD.upgrade_cost_simple(lv))
    return {
        'key': wkey,
        'name': spec.name,
        'desc': spec.desc,
        'lv': lv,
        'quality': q,
        'quality_name': qs['name'],
        'quality_color': qs['color'],
        'mul': qs['mul'] * (1.0 + 0.10 * lv),
        'next_quality_at': nxt,
        'cost': cost,
        'craft': craft,
        'maxed': not craft and (lv >= GD.max_level(q) if GD.quality_rank(q) > 2 else lv >= 8),
    }


def weapon_list(prof):
    """全部武器的养成状态（工坊面板）。"""
    from . import weapon as W
    return [weapon_info(prof, k) for k in W.ORDER]


def can_upgrade(prof, wkey):
    """返回 (是否可强化, 原因, 金币, 材料需求)。"""
    if prof is None:
        return False, '无存档', 0, {}
    info = weapon_info(prof, wkey)
    lv = info['lv']
    if info['maxed']:
        return False, '已强化到上限', 0, {}
    coins, mats = info['cost']
    have = int(prof.get('coins', 0))
    if have < coins:
        return False, '金币不足（还差 %d）' % (coins - have), coins, mats
    pm = prof.get('materials') or {}
    lack = ['%s×%d' % (GD.mat_name(k), v - pm.get(k, 0))
            for k, v in mats.items() if pm.get(k, 0) < v]
    if lack:
        return False, '材料不足（缺 %s）' % '、'.join(lack), coins, mats
    return True, '', coins, mats


def upgrade_weapon(prof, wkey):
    """强化武器一级。"""
    ok, reason, coins, mats = can_upgrade(prof, wkey)
    if not ok:
        return False, reason
    prof['coins'] = int(prof.get('coins', 0)) - coins
    pm = prof.setdefault('materials', {})
    for k, v in mats.items():
        pm[k] = pm.get(k, 0) - v
        if pm[k] <= 0:
            pm.pop(k, None)
    info = weapon_info(prof, wkey)
    from . import weapon as W
    name = W.get(wkey).name
    if info['craft']:
        q = prof['blueprints'][wkey]
        prof.setdefault('weapon_qualities', {})[wkey] = q
        prof.setdefault('weapon_quality_levels', {})[wkey] = 0
        prof['weapon'] = wkey
        return True, '合成并装备「%s·%s」' % (GD.quality_of(q)['name'], name)
    q = info['quality']
    ws = (prof.setdefault('weapon_quality_levels', {}) if GD.quality_rank(q) > 2
          else prof.setdefault('weapons', {}))
    lv = int(ws.get(wkey, 0)) + 1
    ws[wkey] = lv
    qn = GD.quality_of(q)['name']
    return True, '「%s」强化至 Lv.%d' % (name, lv)


# ================================================================ 技能 / 被动


def skill_list(prof):
    out = []
    lv_map = (prof or {}).get('skills') or {}
    for k, (name, desc, mx) in GD.SKILLS.items():
        lv = int(lv_map.get(k, 0))
        cost = GD.skill_cost(k, lv) if lv < mx else None
        out.append({'key': k, 'name': name, 'desc': desc, 'lv': lv,
                    'max': mx, 'cost': cost})
    return out


def passive_list(prof):
    out = []
    lv_map = (prof or {}).get('passives') or {}
    for k, (name, desc, mx) in GD.PASSIVES.items():
        lv = int(lv_map.get(k, 0))
        cost = GD.passive_cost(k, lv) if lv < mx else None
        out.append({'key': k, 'name': name, 'desc': desc, 'lv': lv,
                    'max': mx, 'cost': cost})
    return out


def _can_pay(prof, coins, mats):
    if prof is None:
        return False, '无存档'
    have = int(prof.get('coins', 0))
    if have < coins:
        return False, '金币不足（还差 %d）' % (coins - have)
    pm = prof.get('materials') or {}
    lack = ['%s×%d' % (GD.mat_name(k), v - pm.get(k, 0))
            for k, v in mats.items() if pm.get(k, 0) < v]
    if lack:
        return False, '材料不足（缺 %s）' % '、'.join(lack)
    return True, ''


def _pay(prof, coins, mats):
    prof['coins'] = int(prof.get('coins', 0)) - coins
    pm = prof.setdefault('materials', {})
    for k, v in mats.items():
        pm[k] = pm.get(k, 0) - v
        if pm[k] <= 0:
            pm.pop(k, None)


def upgrade_skill(prof, key):
    table = GD.SKILLS.get(key)
    if not table:
        return False, '无此技能'
    name, _desc, mx = table
    lv_map = prof.setdefault('skills', {})
    lv = int(lv_map.get(key, 0))
    if lv >= mx:
        return False, '「%s」已满级' % name
    coins, mats = GD.skill_cost(key, lv)
    ok, reason = _can_pay(prof, coins, mats)
    if not ok:
        return False, reason
    _pay(prof, coins, mats)
    lv_map[key] = lv + 1
    return True, '「%s」提升至 Lv.%d' % (name, lv + 1)


def upgrade_passive(prof, key):
    table = GD.PASSIVES.get(key)
    if not table:
        return False, '无此被动'
    name, _desc, mx = table
    lv_map = prof.setdefault('passives', {})
    lv = int(lv_map.get(key, 0))
    if lv >= mx:
        return False, '「%s」已满级' % name
    coins, mats = GD.passive_cost(key, lv)
    ok, reason = _can_pay(prof, coins, mats)
    if not ok:
        return False, reason
    _pay(prof, coins, mats)
    lv_map[key] = lv + 1
    return True, '「%s」提升至 Lv.%d' % (name, lv + 1)


# ================================================================ 天赋（永久）


def talent_list(prof):
    """永久天赋词条（与局内三选一天赋共用 TALENTS 表，但这里是可升级的）。"""
    from . import codex as CX
    out = []
    lv_map = (prof or {}).get('talent_levels') or {}
    for key, spec in CX.TALENTS.items():
        out.append({
            'key': key,
            'name': spec.get('name', key),
            'desc': spec.get('desc', ''),
            'color': spec.get('color', (200, 200, 220)),
            'lv': int(lv_map.get(key, 0)),
            'max': TALENT_MAX_LV,
        })
    return out


def talent_upgrade_cost(prof, key):
    lv = int(((prof or {}).get('talent_levels') or {}).get(key, 0))
    return 500 + lv * 600, {'crystal': 1 + lv // 2}


def upgrade_talent(prof, key):
    from . import codex as CX
    spec = CX.TALENTS.get(key)
    if not spec:
        return False, '无此天赋'
    lv_map = prof.setdefault('talent_levels', {})
    lv = int(lv_map.get(key, 0))
    if lv >= TALENT_MAX_LV:
        return False, '「%s」已满级' % spec.get('name', key)
    coins, mats = talent_upgrade_cost(prof, key)
    ok, reason = _can_pay(prof, coins, mats)
    if not ok:
        return False, reason
    _pay(prof, coins, mats)
    lv_map[key] = lv + 1
    return True, '「%s」提升至 Lv.%d' % (spec.get('name', key), lv + 1)


# ================================================================ 存档整合


def sync_unlocked_weapons(prof):
    """保证 save 里 weapons 字典覆盖所有已知武器（缺失补 0）。"""
    if prof is None:
        return
    from . import weapon as W
    ws = prof.setdefault('weapons', {})
    for k in W.ORDER:
        ws.setdefault(k, 0)
    ws.setdefault('pistol', max(1, ws.get('pistol', 0)) - 0)


def material_summary(prof):
    """材料背包展示用：[(key, name, tier, count)]，按 tier 再按 key 排序。"""
    pm = (prof or {}).get('materials') or {}
    rows = []
    for k in GD.MAT_ORDER:
        n = int(pm.get(k, 0))
        if n > 0:
            rows.append((k, GD.mat_name(k), GD.mat_tier(k), n))
    for k, n in pm.items():
        if k not in GD.MAT_ORDER and n > 0:
            rows.append((k, GD.mat_name(k), GD.mat_tier(k), int(n)))
    return rows
