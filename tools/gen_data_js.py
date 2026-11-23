# -*- coding: utf-8 -*-
"""把 Python 数据层导出成网页版可直接用的 web_src/data.js。

目的：Python 与网页版**共用同一份数据源**，避免两边手工同步导致漂移。

导出内容（全部只读，不含逻辑）：
  - gamedata: CURRENCY / MATERIALS / QUALITIES / QUALITY_ORDER /
              CHARACTERS / SKILLS / PASSIVES / CHESTS
  - chapter : CHAPTER_STORY / INTRO / MAIN / DUNGEONS / BONUS /
              BONUS_PRICE / STAGES_PER_SCENE / SCENE_MOBS / DIFF_*
  - codex   : CODEX_CATS / ENEMY_CODEX / ENEMY_ORDER / SCENE_ENEMIES /
              COLLECTS / COLLECT_ORDER / TALENTS / TALENT_ORDER

用法：
    python tools/gen_data_js.py
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from src.sk import gamedata as G      # noqa: E402
from src.sk import chapter as C       # noqa: E402
from src.sk import codex as X         # noqa: E402
from src.sk import hazard as H        # noqa: E402
from src.sk import weapon as W        # noqa: E402

OUT = os.path.join(ROOT, 'web_src', 'data.js')


def norm(o):
    """tuple -> list；dataclass -> dict；保持 dict 键序稳定。"""
    if isinstance(o, dict):
        return {str(k): norm(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [norm(v) for v in o]
    if isinstance(o, (set, frozenset)):
        return sorted(norm(v) for v in o)
    if hasattr(o, '__dataclass_fields__'):
        return {k: norm(getattr(o, k)) for k in o.__dataclass_fields__}
    return o


def dump(name, obj):
    s = json.dumps(norm(obj), ensure_ascii=False, indent=2, sort_keys=False)
    s = s.replace('\n', '\n    ')
    return '    var %s = %s;\n' % (name, s)


HEADER = '''/* eslint-disable */
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
'''


def attach(name):
    return '    D.%s = %s;\n' % (name, name)


# 货币上限在 main() 里注入 FOOTER（值来自 gamedata.py，避免两处手改）
FOOTER = '''
    /* ---- 纯函数：与 Python 侧逻辑保持一致 ---- */

    // 货币持有上限（1.3 需求 3：超出后不再增加）
    // 值由 tools/gen_data_js.py 从 gamedata.py 注入，勿手改
    D.COIN_CAP = __COIN_CAP__;
    D.DIAMOND_CAP = __DIAMOND_CAP__;
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
'''


def main():
    blocks = []
    blocks.append('    /* ---- gamedata.py ---- */')
    for n in ('CURRENCY', 'MATERIALS', 'MAT_ORDER', 'QUALITIES', 'QUALITY_ORDER',
              'QUALITY_MECH_DESC', 'CHARACTERS', 'CHAR_ORDER', 'SKILLS', 'PASSIVES',
              'CHESTS', 'CHEST_ORDER'):
        blocks.append(dump(n, getattr(G, n)))
        blocks.append(attach(n))
    blocks.append('    /* ---- weapon.py（武器表 + 顺序，供养成面板列出全部武器） ---- */')
    for n in ('WEAPONS', 'ORDER', 'QUALITY_POOL', 'SCENE_BOSS_WEAPONS'):
        jsname = 'WPN_ORDER' if n == 'ORDER' else n
        blocks.append(dump(jsname, getattr(W, n)))
        blocks.append(attach(jsname))
    blocks.append(dump('WEAPON_QUALITY', W.QUALITY_BY_KEY))
    blocks.append(attach('WEAPON_QUALITY'))
    blocks.append('    /* ---- weapon.py（品质机制，需求 6：1.4 机制化品质）---- */')
    blocks.append(dump('QUALITY_MECH', W.QUALITY_MECH))
    blocks.append(attach('QUALITY_MECH'))
    blocks.append('    /* ---- chapter.py ---- */')
    for n in ('INTRO', 'CHAPTER_STORY', 'MAIN', 'DUNGEONS', 'BONUS',
              'BONUS_PRICE', 'BONUS_PRICE_DIA', 'STAGES_PER_SCENE',
              'SCENE_MOBS', 'POLLUTION', 'POLLUTION_STAGE_SPAN',
              'COIN_BASE', 'COIN_STEP', 'COIN_ELITE_MUL', 'COIN_BOSS_MUL'):
        obj = getattr(C, n, None)
        if obj is None:
            continue
        blocks.append(dump(n, obj))
        blocks.append(attach(n))
    blocks.append('    /* ---- codex.py ---- */')
    for n in ('CODEX_CATS', 'ENEMY_CODEX', 'ENEMY_ORDER', 'SCENE_ENEMIES',
              'COLLECTS', 'COLLECT_ORDER', 'WEAPON_CODEX', 'MATERIAL_CODEX',
              'TALENTS', 'TALENT_ORDER'):
        blocks.append(dump(n, getattr(X, n)))
        blocks.append(attach(n))
    blocks.append(dump('ENEMY_STATS', {k: X.enemy_stats(k) for k in X.ENEMY_ORDER}))
    blocks.append(attach('ENEMY_STATS'))
    blocks.append('    /* ---- hazard.py（陷阱正式名，供叙事绑定卡用） ---- */')
    blocks.append(dump('TRAP_SPEC', H.TRAP_SPEC))
    blocks.append(attach('TRAP_SPEC'))

    footer = (FOOTER.replace('__COIN_CAP__', str(int(G.COIN_CAP)))
                    .replace('__DIAMOND_CAP__', str(int(G.DIAMOND_CAP))))
    body = HEADER + '\n'.join(blocks) + footer
    with open(OUT, 'w', encoding='utf-8', newline='\n') as f:
        f.write(body)
    kb = os.path.getsize(OUT) / 1024.0
    print('已生成 %s（%.1f KB）' % (os.path.relpath(OUT, ROOT), kb))
    return 0


if __name__ == '__main__':
    sys.exit(main())
