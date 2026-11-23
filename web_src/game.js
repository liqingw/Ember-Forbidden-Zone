/* =========================================================================
 * 最后一片净土 · 网页版 —— 单文件 Canvas 2D 实现
 *
 * 模块划分与 Python / pygame 版一一对应，逻辑逐条对齐：
 *   settings.py -> 常量区        utils.py  -> 工具 / 碰撞区
 *   audio.py    -> Sfx（WebAudio 现场合成，不依赖外部音频文件）
 *   fx.py       -> 特效区        weapon.py -> 武器表
 *   bullet.py   -> 子弹 / 爆炸    pickup.py -> 掉落物 / 可破坏道具
 *   player.py   -> 玩家          enemy.py  -> 敌人 / BOSS
 *   room.py     -> 房间          dungeon.py-> 地牢生成
 *   hud.py      -> HUD 与界面     game.py   -> 主控状态机
 * ========================================================================= */
(function () {
    'use strict';

    // 数据层（由 tools/gen_data_js.py 从 Python 侧 src/sk/*.py 自动导出）
    // Python 版与网页版共用同一份数据源，改数据请改 Python 再重跑生成脚本。
    var D = window.__DATA__;
    if (!D) {
        throw new Error('缺少数据层 window.__DATA__（请先运行 tools/gen_data_js.py）');
    }

    // ==================================================================== 常量
    // ---- 显示
    var VIEW_W = 640, VIEW_H = 360;
    var TILE = 32;
    var FPS = 60;
    var MAX_DT = 1.0 / 30.0;

    // ---- 房间几何（含一圈外墙）
    var ROOM_COLS = 17, ROOM_ROWS = 11;
    var ROOM_PX_W = ROOM_COLS * TILE, ROOM_PX_H = ROOM_ROWS * TILE;
    var CAM_OFF = [Math.floor((VIEW_W - ROOM_PX_W) / 2),
                   Math.floor((VIEW_H - ROOM_PX_H) / 2)];
    var ROOM_CX = ROOM_PX_W / 2, ROOM_CY = ROOM_PX_H / 2;
    var IN_L = TILE, IN_T = TILE;
    var IN_R = (ROOM_COLS - 1) * TILE, IN_B = (ROOM_ROWS - 1) * TILE;

    var DOOR_TILE = { N: [8, 0], S: [8, ROOM_ROWS - 1], W: [0, 5], E: [ROOM_COLS - 1, 5] };
    var OPPOSITE = { N: 'S', S: 'N', W: 'E', E: 'W' };
    var DIR_VEC = { N: [0, -1], S: [0, 1], W: [-1, 0], E: [1, 0] };
    var DIR_LIST = ['N', 'S', 'W', 'E'];

    var ENTRY_FROM = {
        N: [ROOM_CX, TILE + TILE / 2],
        S: [ROOM_CX, (ROOM_ROWS - 2) * TILE + TILE / 2],
        W: [TILE + TILE / 2, ROOM_CY],
        E: [(ROOM_COLS - 2) * TILE + TILE / 2, ROOM_CY]
    };

    // ---- 玩家
    var P_MAX_HP = 12;
    var P_MAX_ENERGY = 200.0;
    var P_SPEED = 168.0;
    var P_RADIUS = 11.0;
    var P_IFRAME = 0.85;
    var P_DASH_SPEED = 540.0;
    var P_DASH_TIME = 0.16;
    var P_DASH_CD = 0.80;
    var P_ENERGY_REGEN = 0.0;
    var STUCK_SECONDS = 1.6;   // 有输入却连续零位移超过该秒数 -> 自动脱困

    // ---- 需求 20：打击停顿（hit-stop）与受击击退（与 Python settings 同源）
    var HITSTOP_HIT = 0.020;    // 普通命中
    var HITSTOP_KILL = 0.045;   // 击杀
    var HITSTOP_BOSS = 0.070;   // 打中首领
    var HITSTOP_HURT = 0.055;   // 玩家受击
    var HITSTOP_MAX = 0.11;     // 单次上限，防叠加成"卡住"
    var HITSTOP_SCALE = 0.35;   // 停顿期间世界时间的推进比例
    var HITSTOP_COOLDOWN = 0.09;// 两次打击顿之间的最小间隔（防连续刷新）
    var P_KNOCK_BASE = 150.0;   // 基础击退速度（px/s）
    var P_KNOCK_PER_DMG = 22.0; // 每点伤害追加
    var P_KNOCK_MAX = 330.0;    // 上限
    var P_KNOCK_TIME = 0.18;    // 击退持续时间

    // ---- 敌人
    var E_HP_BAR_W = 26;

    // ---- 楼层
    var FLOORS = 1;
    var GRID_W = 5, GRID_H = 5;

    // ---- 配色
    var C_BG = [18, 17, 24];
    var C_PANEL = [30, 28, 40];
    var C_PANEL_HI = [46, 43, 62];
    var C_TEXT = [232, 230, 240];
    var C_TEXT_DIM = [150, 146, 168];
    var C_GOLD = [255, 206, 74];
    var C_DIA = [140, 230, 255];
    var C_HP = [226, 62, 74];
    var C_ENERGY = [74, 200, 232];
    var C_ACCENT = [120, 220, 180];
    var C_WARN = [255, 138, 66];
    var C_BOSS = [198, 84, 220];
    var C_WHITE = [255, 255, 255];

    var ROOM_COLOR = {
        start: [108, 196, 255], normal: [150, 146, 168], treasure: [255, 206, 74],
        heal: [226, 62, 74], shop: [120, 220, 180], drink: [230, 153, 110], boss: [198, 84, 220],
        cleared: [96, 108, 96]
    };

    var KIND_LABEL = {
        start: '出生房', normal: '战斗房', treasure: '宝箱房',
        heal: '治疗房', shop: '商店房', drink: '饮料房', boss: 'BOSS 房'
    };

    var TAU = Math.PI * 2;
    var SAVE_KEY = 'soulknight_lite_save';
    // 网页版存档（与 Python src/sk/save.py 同构）：localStorage 里的 3 槽仓库
    var SAVE_STORE_KEY = 'last_clean_land_save_v2';
    var SAVE_BACKUP_KEY = 'last_clean_land_save_v2_bak';
    var SAVE_VERSION = 5;
    var MAX_SLOTS = 3;

    // ==================================================================== 工具
    function clamp(v, a, b) { return v < a ? a : (v > b ? b : v); }
    function lerp(a, b, t) { return a + (b - a) * t; }
    function dist(ax, ay, bx, by) { return Math.hypot(bx - ax, by - ay); }
    function angLerp(a, b, t) {
        var d = (b - a + Math.PI) % TAU - Math.PI;
        if (d < -Math.PI) { d += TAU; }
        return a + d * t;
    }
    function fin(v) { return typeof v === 'number' && isFinite(v); }
    function nowMs() { return (typeof performance !== 'undefined' ? performance.now() : Date.now()); }

    // 需求 11：手机震动。仅当设置开启且设备支持 navigator.vibrate 时生效。
    // 桌面/无该 API 的环境安静跳过，不影响任何逻辑。
    function vibrate(game, ms) {
        try {
            var st = (game && game.setting) ? game.setting : null;
            if (!st || !st.vibrate) { return false; }
            if (typeof navigator === 'undefined' || !navigator.vibrate) { return false; }
            navigator.vibrate(ms);
            return true;
        } catch (e) { return false; }
    }

    // ---- 圆形 vs 瓦片碰撞（最近点法）
    function circleSolid(cx, cy, r, solid) {
        var x0 = Math.floor((cx - r) / TILE), x1 = Math.floor((cx + r) / TILE);
        var y0 = Math.floor((cy - r) / TILE), y1 = Math.floor((cy + r) / TILE);
        var rr = r * r;
        for (var ty = y0; ty <= y1; ty++) {
            for (var tx = x0; tx <= x1; tx++) {
                if (!solid(tx, ty)) { continue; }
                var nx = clamp(cx, tx * TILE, tx * TILE + TILE);
                var ny = clamp(cy, ty * TILE, ty * TILE + TILE);
                var dx = cx - nx, dy = cy - ny;
                if (dx * dx + dy * dy < rr) { return true; }
            }
        }
        return false;
    }

    // ---- 沿单轴移动，遇阻用二分法逼近最大可移动距离
    // 注意：二分法成立的前提是"起点不在障碍里"。若起点本身已在障碍内
    // （被传送/击退推进墙里），test(cur+mid) 会恒为 true，hi 一路收缩到 0，
    // 位移永远是 0 —— 表现为永久卡死。因此先做起点脱困判断。
    function slide(cur, delta, test) {
        if (delta === 0.0) { return cur; }
        if (test(cur)) {
            // 起点已陷入障碍：放弃二分，直接尝试整段位移，能挪多少算多少
            return cur + delta;
        }
        if (!test(cur + delta)) { return cur + delta; }
        var lo = 0.0, hi = delta;
        for (var i = 0; i < 7; i++) {
            var mid = (lo + hi) * 0.5;
            if (test(cur + mid)) { hi = mid; } else { lo = mid; }
        }
        return cur + lo;
    }

    function collideTest(x, y, r, solid, blockers) {
        if (solid && circleSolid(x, y, r, solid)) { return true; }
        if (blockers) {
            for (var i = 0; i < blockers.length; i++) {
                var b = blockers[i];
                var rr = r + b[2], dx = x - b[0], dy = y - b[1];
                if (dx * dx + dy * dy < rr * rr) { return true; }
            }
        }
        return false;
    }

    function moveCircle(x, y, r, dx, dy, solid, blockers) {
        x = slide(x, dx, function (nx) { return collideTest(nx, y, r, solid, blockers); });
        y = slide(y, dy, function (ny) { return collideTest(x, ny, r, solid, blockers); });
        return [x, y];
    }

    // ---- 脱困：螺旋搜索最近的空位（与 Python utils.find_free_spot 对齐）
    function findFreeSpot(x, y, r, solid, blockers, maxR, step) {
        if (!collideTest(x, y, r, solid, blockers)) { return [x, y]; }
        if (step === undefined || step === null) { step = TILE * 0.5; }
        if (maxR === undefined || maxR === null) { maxR = TILE * 5; }
        for (var radius = step; radius <= maxR; radius += step) {
            var ring = Math.max(8, Math.floor(16 * radius / step));
            for (var i = 0; i < ring; i++) {
                var a = 2.0 * Math.PI * i / ring;
                var nx = x + Math.cos(a) * radius;
                var ny = y + Math.sin(a) * radius;
                if (!collideTest(nx, ny, r, solid, blockers)) { return [nx, ny]; }
            }
        }
        return null;
    }

    function unstick(x, y, r, solid, blockers, fallback) {
        var spot = findFreeSpot(x, y, r, solid, blockers, null, null);
        if (spot !== null) { return spot; }
        if (fallback) {
            var fx = fallback[0], fy = fallback[1];
            var s2 = findFreeSpot(fx, fy, r, solid, blockers, TILE * 8, null);
            if (s2 !== null) { return s2; }
            return [fx, fy];
        }
        return [x, y];
    }

    // ==================================================================== RNG
    // 确定性 PRNG（mulberry32），接口对齐 Python random.Random
    function makeRng(seed) {
        var s = (seed === null || seed === undefined)
            ? ((Date.now() ^ (Math.random() * 0xffffffff)) >>> 0) : (seed >>> 0);
        var api = {};
        api.random = function () {
            s = (s + 0x6D2B79F5) >>> 0;
            var t = s;
            t = Math.imul(t ^ (t >>> 15), t | 1);
            t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
            return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
        };
        api.uniform = function (a, b) { return a + (b - a) * api.random(); };
        api.randint = function (a, b) { return a + Math.floor(api.random() * (b - a + 1)); };
        api.choice = function (arr) { return arr[Math.floor(api.random() * arr.length)]; };
        api.chance = function (p) { return api.random() < p; };
        return api;
    }

    // ==================================================================== 画布
    var cv = document.getElementById('cv');
    var ctx = cv.getContext('2d');
    var FONT_STACK = '"Microsoft YaHei","MSYH","PingFang SC","Noto Sans SC",' +
                     '"Source Han Sans SC","WenQuanYi Micro Hei",sans-serif';

    function cssColor(c, a) {
        if (a === undefined || a === null) { return 'rgb(' + c[0] + ',' + c[1] + ',' + c[2] + ')'; }
        return 'rgba(' + c[0] + ',' + c[1] + ',' + c[2] + ',' + a + ')';
    }
    function setFont(size, bold) {
        ctx.font = (bold ? 'bold ' : '') + size + 'px ' + FONT_STACK;
    }
    function textWidth(s, size, bold) { setFont(size, bold); return ctx.measureText(s).width; }

    function rrect(x, y, w, h, r) {
        r = Math.min(r, Math.abs(w) / 2, Math.abs(h) / 2);
        ctx.beginPath();
        ctx.moveTo(x + r, y);
        ctx.lineTo(x + w - r, y);
        ctx.quadraticCurveTo(x + w, y, x + w, y + r);
        ctx.lineTo(x + w, y + h - r);
        ctx.quadraticCurveTo(x + w, y + h, x + w - r, y + h);
        ctx.lineTo(x + r, y + h);
        ctx.quadraticCurveTo(x, y + h, x, y + h - r);
        ctx.lineTo(x, y + r);
        ctx.quadraticCurveTo(x, y, x + r, y);
        ctx.closePath();
    }

    function fillRect(c, x, y, w, h) { ctx.fillStyle = cssColor(c); ctx.fillRect(x, y, w, h); }
    function panel(x, y, w, h, fill, border, radius, lw) {
        rrect(x, y, w, h, radius === undefined ? 6 : radius);
        ctx.fillStyle = cssColor(fill, fill.length > 3 ? fill[3] / 255 : 1);
        ctx.fill();
        if (lw !== 0) {
            ctx.lineWidth = lw || 2;
            ctx.strokeStyle = cssColor(border);
            ctx.stroke();
        }
    }
    function bar(x, y, w, h, ratio, fg, bg, border) {
        ratio = clamp(ratio, 0, 1);
        rrect(x, y, w, h, 3);
        ctx.fillStyle = cssColor(bg || [40, 38, 52]);
        ctx.fill();
        var fw = Math.floor(w * ratio);
        if (fw > 0) {
            rrect(x, y, fw, h, 3);
            ctx.fillStyle = cssColor(fg);
            ctx.fill();
        }
        if (border) {
            rrect(x, y, w, h, 3);
            ctx.lineWidth = 1;
            ctx.strokeStyle = cssColor(border);
            ctx.stroke();
        }
    }
    // 带描边阴影的文字（对应 utils.text_shadow）
    function txt(s, size, color, x, y, anchor, bold) {
        setFont(size, bold);
        var w = ctx.measureText(s).width;
        var X = x, Y = y;
        if (anchor === 'midtop' || anchor === 'midbottom') { X = x - w / 2; }
        else if (anchor === 'topright') { X = x - w; }
        if (anchor === 'midbottom' || anchor === 'bottomleft' || anchor === 'bottomright') {
            Y = y - size;
        }
        ctx.fillStyle = 'rgba(0,0,0,0.78)';
        ctx.fillText(s, X + 1, Y + 1);
        ctx.fillText(s, X + 2, Y);
        ctx.fillText(s, X, Y + 2);
        ctx.fillStyle = cssColor(color);
        ctx.fillText(s, X, Y);
        return w;
    }
    function dim(a, color) {
        color = color || [0, 0, 0];
        ctx.fillStyle = cssColor(color, a / 255);
        ctx.fillRect(0, 0, VIEW_W, VIEW_H);
    }
    // 测量文字宽度（不绘制）
    function measure(s, size, bold) {
        setFont(size, bold);
        return ctx.measureText(s).width;
    }

    // ---- 软阴影（缓存）
    var _shadowCache = {};
    function shadowSprite(w, h) {
        var k = w + ',' + h;
        if (_shadowCache[k]) { return _shadowCache[k]; }
        var c = document.createElement('canvas');
        c.width = w; c.height = h;
        var g = c.getContext('2d');
        g.save();
        g.translate(w / 2, h / 2);
        g.scale(1, h / w);
        var grd = g.createRadialGradient(0, 0, 0, 0, 0, w / 2);
        grd.addColorStop(0.00, 'rgba(0,0,0,0.62)');
        grd.addColorStop(0.55, 'rgba(0,0,0,0.30)');
        grd.addColorStop(0.85, 'rgba(0,0,0,0.10)');
        grd.addColorStop(1.00, 'rgba(0,0,0,0.00)');
        g.fillStyle = grd;
        g.beginPath();
        g.arc(0, 0, w / 2, 0, TAU);
        g.fill();
        g.restore();
        _shadowCache[k] = c;
        return c;
    }
    function drawShadow(cx, cy, rx, ry, alpha) {
        ry = (ry === undefined || ry === null) ? rx * 0.5 : ry;
        var w = Math.max(4, Math.round(rx * 2)), h = Math.max(3, Math.round(ry * 2));
        var s = shadowSprite(w, h);
        ctx.save();
        ctx.globalAlpha = (alpha === undefined ? 255 : alpha) / 255;
        ctx.imageSmoothingEnabled = true;
        ctx.drawImage(s, Math.round(cx - w / 2), Math.round(cy - h / 2));
        ctx.restore();
    }

    // ==================================================================== 存档
    // 与 Python src/sk/save.py 一一对应：3 槽仓库 + 个人 ID + 原子写 + 备份。
    // 落盘位置换成 localStorage；其余字段结构 / 迁移逻辑保持完全一致，
    // 这样两端存档字段名相同，测试断言可以共用一套。
    function defaultSettings() {
        return {
            music: false, sfx: true, shake: false,
            vibrate: !!(window.__TOUCH__ && window.__TOUCH__.enabled), // 手机端震动
            joystick: 'float',         // fixed / float（需求 14）
            joy_sens: 1.0,
            aim_sens: 1.0,
            aim_assist: true,
            button_scale: 1.0,
            button_opacity: 0.8,
            show_fps: false,
            ui_scale: 1.0,
            auto_fire: false
        };
    }

    function newProfile(pid, name) {
        return {
            version: SAVE_VERSION,
            id: pid,
            name: (name && String(name).replace(/^\s+|\s+$/g, '')) ||
                  ('漂泊者' + (pid + 1)),
            created: Date.now() / 1000.0,
            played: 0.0,
            updated: Date.now() / 1000.0,
            coins: 0,
            diamonds: 0,
            materials: {},
            route_first_rewards: [],
            chars: ['scout'],
            char: 'scout',
            weapons: { pistol: 0 },
            weapon: 'pistol',
            skills: {},
            passives: {},
            codex: { enemy: [], weapon: [], material: [], collect: [] },
            collects: [],
            showcase: [null, null, null, null, null, null],
            talent_unlocked: [],
            talent_levels: {},
            scene_prog: {},
            best_scene_prog: {},
            main_done: false,
            chapter: 0,
            stage: 0,
            visited_scenes: [],
            cleared_scenes: [],
            scene_best: {},
            blueprints: {},
            weapon_qualities: {},
            weapon_quality_levels: {},
            unlocked_dungeons: [],
            bonus_unlocked: false,
            story_seen: [],
            tips_seen: [],
            run: null,
            run_checkpoint: null,
            stats: { kills: 0, deaths: 0, runs: 0, best_chapter: 0,
                     boss_kills: 0, items: 0, chests: 0, play_seconds: 0.0 },
            settings: defaultSettings()
        };
    }

    // 旧档升级：补齐缺失字段，不丢已有数据（与 Python save._migrate 对齐）
    function migrateProfile(p) {
        if (!p || typeof p !== 'object') { return p; }
        var oldVersion = Number(p.version || 0);
        var base = newProfile(p.id === undefined ? 0 : p.id, p.name || '');
        for (var k in base) {
            if (!Object.prototype.hasOwnProperty.call(base, k)) { continue; }
            var v = base[k];
            if (p[k] === undefined || p[k] === null) {
                p[k] = v;
            } else if (v && typeof v === 'object' && !Array.isArray(v) &&
                       p[k] && typeof p[k] === 'object' && !Array.isArray(p[k])) {
                for (var kk in v) {
                    if (Object.prototype.hasOwnProperty.call(v, kk) &&
                        p[k][kk] === undefined) {
                        p[k][kk] = v[kk];
                    }
                }
            }
        }
        p.version = SAVE_VERSION;
        if (oldVersion < 4) {
            var oldCp = p.run_checkpoint;
            if (oldCp && Number(oldCp.floor || 1) > 1) {
                p.coins = D.clampCoin(Number(p.coins || 0) + Number(oldCp.coins || 0));
                p.run_checkpoint = null;
            }
            if (p.run) { p.run.floors = 1; }
        }
        var progress = p.scene_prog || {}, active = p.run;
        var unfinished = !!(active && active.scene &&
            Number(progress[active.scene] || 0) <= Number(active.stage_idx || 0));
        if (!unfinished && D.MAIN.every(function (key) {
            return Number(progress[key] || 0) >= D.STAGES_PER_SCENE;
        }) && D.resetCycle) {
            p.main_done = true;
            D.resetCycle(p);
        }
        if (D.syncCollectCharacters) { D.syncCollectCharacters(p); }
        return p;
    }

    function saveScore(p) {
        if (!p || typeof p !== 'object') { return [-1]; }
        var stages = Object.assign({}, p.best_scene_prog || {}), count = 0;
        Object.keys(p.scene_prog || {}).forEach(function (key) {
            stages[key] = Math.max(Number(stages[key] || 0), Number(p.scene_prog[key] || 0));
        });
        Object.keys(stages).forEach(function (key) { count += Math.max(0, Number(stages[key]) || 0); });
        return [p.main_done ? 1 : 0, count, (p.cleared_scenes || []).length,
            (p.unlocked_dungeons || []).length,
            (new Set(p.collects || [])).size,
            Number((p.stats || {}).best_chapter || 0),
            Number(p.played || 0), Number(p.updated || 0), Number(p.created || 0)];
    }
    function moreAdvanced(a, b) {
        var aa = saveScore(a), bb = saveScore(b);
        for (var i = 0; i < Math.max(aa.length, bb.length); i++) {
            if ((aa[i] || 0) > (bb[i] || 0)) { return a; }
            if ((aa[i] || 0) < (bb[i] || 0)) { return b; }
        }
        return a;
    }
    function mergeRouteClaims(winner, other) {
        if (!winner || !other || winner.id !== other.id ||
                winner.created !== other.created) { return false; }
        var claims = Array.isArray(winner.route_first_rewards) ?
            winner.route_first_rewards.slice() : [];
        var added = false;
        (Array.isArray(other.route_first_rewards) ? other.route_first_rewards : [])
            .forEach(function (claim) {
                if (typeof claim === 'string' && claims.indexOf(claim) < 0) {
                    claims.push(claim); added = true;
                }
            });
        if (added) { winner.route_first_rewards = claims; }
        return added;
    }

    var SaveStore = {
        data: { version: SAVE_VERSION, slots: [null, null, null], last: null },

        _store: function () {
            try {
                if (typeof window !== 'undefined' && window.localStorage) {
                    return window.localStorage;
                }
            } catch (e) { /* 隐私模式等 */ }
            return null;
        },
        load: function () {
            var ls = this._store();
            if (!ls) { return false; }
            var keys = [SAVE_STORE_KEY, SAVE_BACKUP_KEY,
                'last_clean_land_save_native', 'last_clean_land_save_native_bak',
                'last_clean_land_save_v1', 'last_clean_land_save_v1_bak'];
            var chosen = [null, null, null], found = false, last = null, imported = false;
            for (var i = 0; i < keys.length; i++) {
                try {
                    var raw = ls.getItem(keys[i]);
                    if (!raw && window.__NATIVE_SAVE__) {
                        if (keys[i] === 'last_clean_land_save_native') {
                            raw = window.__NATIVE_SAVE__.loaded[0];
                        } else if (keys[i] === 'last_clean_land_save_native_bak') {
                            raw = window.__NATIVE_SAVE__.loaded[1];
                        }
                    }
                    if (!raw) { continue; }
                    var d = JSON.parse(raw);
                    if (!d || !Array.isArray(d.slots)) { continue; }
                    found = true;
                    if (last === null && d.last !== undefined) { last = d.last; }
                    for (var j = 0; j < Math.min(MAX_SLOTS, d.slots.length); j++) {
                        var slot = d.slots[j];
                        if (!slot || typeof slot !== 'object') { continue; }
                        var previous = chosen[j];
                        if (moreAdvanced(previous, slot) === slot) {
                            chosen[j] = Object.assign({}, slot);
                            if (keys[i] !== SAVE_STORE_KEY) { imported = true; }
                        }
                        if (mergeRouteClaims(chosen[j],
                                chosen[j] === previous ? slot : previous)) {
                            imported = true;
                        }
                    }
                } catch (e) { continue; }   // 主档坏了就试备份
            }
            if (found) {
                this.data = {version: SAVE_VERSION,
                    slots: chosen.map(function (slot) { return slot ? migrateProfile(slot) : null; }),
                    last: last};
                if (imported || (window.__NATIVE_SAVE__ && window.__NATIVE_SAVE__.enabled)) {
                    this.save();
                }
                return true;
            }
            this.data = { version: SAVE_VERSION, slots: [null, null, null], last: null };
            return false;
        },
        save: function () {
            var ls = this._store();
            if (!ls) { return; }
            try {
                // 替换前先把现有档备份一份（与 Python _atomic_write 一致）
                var old = ls.getItem(SAVE_STORE_KEY);
                if (old) { ls.setItem(SAVE_BACKUP_KEY, old); }
                ls.setItem(SAVE_STORE_KEY, JSON.stringify(this.data));
                if (window.__NATIVE_SAVE__ && window.__NATIVE_SAVE__.enabled) {
                    window.__NATIVE_SAVE__.save(ls.getItem(SAVE_STORE_KEY),
                        ls.getItem(SAVE_BACKUP_KEY));
                }
            } catch (e) { /* 存档失败绝不能拖垮游戏 */ }
        },
        slots: function () {
            var s = this.data.slots || [];
            var out = s.slice();
            while (out.length < MAX_SLOTS) { out.push(null); }
            return out.slice(0, MAX_SLOTS);
        },
        get: function (idx) {
            var s = this.data.slots || [];
            if (idx >= 0 && idx < s.length) { return s[idx]; }
            return null;
        },
        freeSlot: function () {
            var s = this.slots();
            for (var i = 0; i < s.length; i++) { if (s[i] === null) { return i; } }
            return null;
        },
        create: function (idx, name) {
            var p = newProfile(idx, name);
            this.data.slots[idx] = p;
            this.data.last = p.id;
            this.save();
            return p;
        },
        remove: function (idx) {
            this.data.slots[idx] = null;
            if (this.data.last === idx) { this.data.last = null; }
            this.save();
        },
        setCurrent: function (idx) {
            this.data.last = idx;
            this.save();
        },
        current: function () {
            var i = this.data.last;
            if (typeof i === 'number') {
                var p = this.get(i);
                if (p !== null && p !== undefined) { return p; }
            }
            return null;
        },
        flush: function (profile) {
            if (!profile || typeof profile !== 'object') { return; }
            var idx = profile.id;
            var slots = this.data.slots;
            if (typeof idx === 'number' && idx >= 0 && idx < slots.length) {
                slots[idx] = profile;
                this.data.last = idx;
            }
            this.save();
        }
    };

    // ==================================================================== 素材
    // 全部贴图以 base64 内嵌（见文件尾部的 __ASSETS__），加载失败则生成占位图
    var IMG_MANIFEST = {
        player: 'spr_player.png', slime: 'spr_enemy_slime.png',
        bomber: 'spr_enemy_bomber.png', drone: 'spr_enemy_drone.png',
        boss: 'spr_boss.png',
        crate: 'spr_crate.png', barrel: 'spr_barrel.png', coin: 'spr_coin.png',
        diamond: 'spr_diamond.png',
        cover_pillar: 'spr_cover_pillar.png', cover_block: 'spr_cover_block.png',
        heart: 'spr_heart.png', energy: 'spr_energy.png', key: 'spr_key.png',
        chest: 'spr_chest.png', potion: 'spr_potion.png',
        potion_health: 'spr_potion_health.png', potion_energy: 'spr_potion_energy.png',
        drink_nectar: 'spr_drink_nectar.png', drink_dew: 'spr_drink_dew.png',
        drink_soda: 'spr_drink_soda.png', drink_tea: 'spr_drink_tea.png',
        basketball: 'spr_basketball.png',
        wpn_pistol: 'wpn_pistol.png', wpn_shotgun: 'wpn_shotgun.png',
        wpn_smg: 'wpn_smg.png', wpn_laser: 'wpn_laser.png',
        wpn_rocket: 'wpn_rocket.png', wpn_cannon: 'wpn_cannon.png',
        // 1.4 新增武器：复用现有底图（素材表只有 6 格）
        wpn_crossbow: 'wpn_laser.png', wpn_flamer: 'wpn_smg.png',
        wpn_railgun: 'wpn_cannon.png', wpn_blade: 'wpn_shotgun.png',
        wpn_plasma_blade: 'wpn_laser.png',
        b_bullet: 'bul_bullet.png', b_bolt: 'bul_bolt.png', b_plasma: 'bul_plasma.png',
        b_laser: 'bul_laser.png', b_rocket: 'bul_rocket.png', b_hex: 'bul_hex.png',
        tile_floor: 'tile_floor.png', tile_floor_alt: 'tile_floor_alt.png',
        tile_wall: 'tile_wall.png', tile_wall_top: 'tile_wall_top.png',
        tile_door: 'tile_door.png',
        bg_title: 'bg_title.png'
    };
    // 2.0：从共用数据表加载独立贴图，避免网页版回退到复用素材。
    (D.WPN_ORDER || []).forEach(function (key) {
        IMG_MANIFEST['wpn_' + key] = 'wpn_' + key + '.png';
    });
    (D.CHAR_ORDER || []).forEach(function (key) {
        IMG_MANIFEST['player_' + key] = 'spr_player_' + key + '.png';
    });
    (D.MAT_ORDER || []).forEach(function (key) {
        IMG_MANIFEST['material_' + key] = 'spr_material_' + key + '.png';
    });
    (D.ENEMY_ORDER || []).forEach(function (key) {
        IMG_MANIFEST['enemy_' + key] = 'spr_enemy_' + key + '.png';
    });
    (D.COLLECT_ORDER || []).forEach(function (key) {
        IMG_MANIFEST['collect_' + key] = 'spr_collect_' + key + '.png';
    });
    Object.keys(D.CHESTS || {}).forEach(function (key) {
        ['normal', 'superb'].forEach(function (tier) {
            IMG_MANIFEST['chest_' + key + '_' + tier] = 'spr_chest_' + key + '_' + tier + '.png';
        });
    });
    ['spike', 'poison', 'shock', 'slow', 'flame'].forEach(function (key) {
        IMG_MANIFEST['trap_' + key] = 'spr_trap_' + key + '.png';
    });
    ['crust', 'sewer', 'facility', 'core', 'd_mine', 'd_lab', 'd_gift'].forEach(function (scene) {
        ['floor', 'floor_alt', 'wall', 'wall_top'].forEach(function (part) {
            IMG_MANIFEST['tile_' + part + '_' + scene] = 'tile_' + part + '_' + scene + '.png';
        });
    });
    var PLACEHOLDER_COLOR = {
        player: [96, 200, 220], slime: [120, 220, 110], bomber: [220, 96, 80],
        drone: [170, 120, 230], boss: [210, 90, 220]
    };
    var IMG = {};

    function makePlaceholder(size, color) {
        var c = document.createElement('canvas');
        c.width = size[0]; c.height = size[1];
        var g = c.getContext('2d');
        var r = Math.min(size[0], size[1]) / 2;
        g.beginPath();
        g.arc(size[0] / 2, size[1] / 2, r, 0, TAU);
        g.fillStyle = cssColor(color);
        g.fill();
        g.lineWidth = 2;
        g.strokeStyle = 'rgb(20,20,26)';
        g.stroke();
        g.strokeStyle = '#fff';
        g.beginPath();
        g.moveTo(size[0] / 2 - r / 2, size[1] / 2);
        g.lineTo(size[0] / 2 + r / 2, size[1] / 2);
        g.moveTo(size[0] / 2, size[1] / 2 - r / 2);
        g.lineTo(size[0] / 2, size[1] / 2 + r / 2);
        g.stroke();
        return c;
    }

    // 加载全部贴图；返回 Promise
    function loadAssets() {
        var raw = (typeof window !== 'undefined' && window.__ASSETS__) || {};
        var names = [];
        for (var k in IMG_MANIFEST) {
            if (IMG_MANIFEST.hasOwnProperty(k)) { names.push(IMG_MANIFEST[k]); }
        }
        var jobs = names.map(function (fn) {
            return new Promise(function (resolve) {
                var key = null;
                for (var k2 in IMG_MANIFEST) {
                    if (IMG_MANIFEST[k2] === fn) { key = k2; }
                }
                var data = raw[fn];
                if (!data) {
                    IMG[key] = makePlaceholder([32, 32], [200, 80, 80]);
                    resolve();
                    return;
                }
                var im = new Image();
                im.onload = function () { IMG[key] = im; resolve(); };
                im.onerror = function () {
                    IMG[key] = makePlaceholder([32, 32], PLACEHOLDER_COLOR[key] || [140, 140, 160]);
                    resolve();
                };
                im.src = 'data:image/png;base64,' + data;
            });
        });
        return Promise.all(jobs);
    }

    // ---- 绘制贴图：中心定位 / 翻转 / 旋转 / 整体透明度
    function blit(key, cx, cy, w, h, opt) {
        var img = IMG[key];
        if (!img) { return; }
        opt = opt || {};
        ctx.save();
        ctx.imageSmoothingEnabled = false;
        ctx.globalAlpha = (opt.alpha === undefined ? 255 : opt.alpha) / 255;
        if (opt.ang !== undefined) {
            ctx.translate(cx, cy);
            ctx.rotate(opt.ang);
            ctx.drawImage(img, -w / 2, -h / 2, w, h);
        } else if (opt.flip) {
            ctx.translate(cx, cy);
            ctx.scale(-1, 1);
            ctx.drawImage(img, -w / 2, -h / 2, w, h);
        } else {
            ctx.drawImage(img, Math.round(cx - w / 2), Math.round(cy - h / 2), w, h);
        }
        ctx.restore();
    }

    // ---- 场景染色（需求 8）：同一张贴图按场景着色，做出"不同怪"的观感。
    // 结果按 (key,w,h,tint) 缓存，避免每帧新建 canvas。
    var _tintCache = {};
    function _tintCanvas(key, w, h, tint, amount) {
        var ck = key + '|' + w + '|' + h + '|' + tint[0] + ',' +
            tint[1] + ',' + tint[2] + '|' + amount.toFixed(2);
        var hit = _tintCache[ck];
        if (hit) { return hit; }
        var img = IMG[key];
        if (!img) { return null; }
        var cv = document.createElement('canvas');
        cv.width = Math.max(1, w); cv.height = Math.max(1, h);
        var g = cv.getContext('2d');
        g.imageSmoothingEnabled = false;
        g.drawImage(img, 0, 0, w, h);
        g.globalCompositeOperation = 'multiply';
        g.fillStyle = 'rgb(' + tint[0] + ',' + tint[1] + ',' + tint[2] + ')';
        g.fillRect(0, 0, w, h);
        g.globalCompositeOperation = 'destination-in';
        g.drawImage(img, 0, 0, w, h);
        g.globalCompositeOperation = 'source-over';
        // 按 amount 与原图混合
        var out = document.createElement('canvas');
        out.width = Math.max(1, w); out.height = Math.max(1, h);
        var g2 = out.getContext('2d');
        g2.imageSmoothingEnabled = false;
        g2.drawImage(img, 0, 0, w, h);
        g2.globalAlpha = amount;
        g2.drawImage(cv, 0, 0, w, h);
        _tintCache[ck] = out;
        return out;
    }

    function blitTint(key, cx, cy, w, h, tint, amount, opt) {
        opt = opt || {};
        var cv = _tintCanvas(key, w, h, tint, amount === undefined ? 0.66 : amount);
        if (!cv) { return blit(key, cx, cy, w, h, opt); }
        ctx.save();
        ctx.imageSmoothingEnabled = false;
        ctx.globalAlpha = (opt.alpha === undefined ? 255 : opt.alpha) / 255;
        if (opt.flip) {
            ctx.translate(cx, cy);
            ctx.scale(-1, 1);
            ctx.drawImage(cv, -w / 2, -h / 2, w, h);
        } else {
            ctx.drawImage(cv, Math.round(cx - w / 2), Math.round(cy - h / 2), w, h);
        }
        ctx.restore();
    }

    // ---- 叠加白色高光（对应 pygame BLEND_RGBA_ADD 的受伤闪白）
    var _tintCv = null;    function blitTintAdd(key, cx, cy, w, h, alpha, flip) {
        var img = IMG[key];
        if (!img || alpha <= 0.004) { return; }
        if (!_tintCv) { _tintCv = document.createElement('canvas'); }
        var t = _tintCv;
        if (t.width < w || t.height < h) {
            t.width = Math.max(t.width, w); t.height = Math.max(t.height, h);
        }
        var g = t.getContext('2d');
        g.setTransform(1, 0, 0, 1, 0, 0);
        g.clearRect(0, 0, t.width, t.height);
        if (flip) {
            g.save(); g.translate(w, 0); g.scale(-1, 1);
            g.drawImage(img, 0, 0, w, h);
            g.restore();
        } else {
            g.drawImage(img, 0, 0, w, h);
        }
        g.globalCompositeOperation = 'source-in';
        g.fillStyle = 'rgba(255,255,255,' + clamp(alpha, 0, 1) + ')';
        g.fillRect(0, 0, w, h);
        g.globalCompositeOperation = 'source-over';
        ctx.save();
        ctx.imageSmoothingEnabled = false;
        ctx.globalCompositeOperation = 'lighter';
        ctx.drawImage(t, 0, 0, w, h, Math.round(cx - w / 2), Math.round(cy - h / 2), w, h);
        ctx.restore();
    }

    // ==================================================================== 音效
    // WebAudio 现场合成，参数对齐 audio.py 的 synth() 表
    var Sfx = (function () {
        var actx = null;
        var master = null;
        var enabled = true;
        var live = 0;

        function ensure() {
            if (actx) { return actx; }
            var AC = window.AudioContext || window.webkitAudioContext;
            if (!AC) { enabled = false; return null; }
            try {
                actx = new AC();
                master = actx.createGain();
                master.gain.value = 0.5;
                master.connect(actx.destination);
            } catch (e) { actx = null; enabled = false; }
            return actx;
        }
        function unlock() {
            ensure();
            if (actx && actx.state === 'suspended') { actx.resume(); }
        }

        function tone(freq, dur, wave, vol, sweep, delay) {
            if (!enabled || !ensure()) { return; }
            if (live > 28) { return; }
            var t0 = actx.currentTime + (delay || 0);
            var osc = actx.createOscillator();
            var g = actx.createGain();
            osc.type = wave || 'square';
            osc.frequency.setValueAtTime(freq, t0);
            if (sweep && sweep !== 1.0) {
                osc.frequency.exponentialRampToValueAtTime(
                    Math.max(20, freq * sweep), t0 + dur);
            }
            g.gain.setValueAtTime(0.0001, t0);
            g.gain.exponentialRampToValueAtTime(Math.max(0.0002, vol), t0 + 0.008);
            g.gain.exponentialRampToValueAtTime(0.0001, t0 + dur);
            osc.connect(g); g.connect(master);
            osc.start(t0); osc.stop(t0 + dur + 0.02);
            live++;
            osc.onended = function () { live--; };
        }

        function noise(dur, vol, lp, delay) {
            if (!enabled || !ensure()) { return; }
            if (live > 28) { return; }
            var n = Math.max(8, Math.floor(actx.sampleRate * dur));
            var buf = actx.createBuffer(1, n, actx.sampleRate);
            var d = buf.getChannelData(0);
            for (var i = 0; i < n; i++) { d[i] = Math.random() * 2 - 1; }
            var src = actx.createBufferSource();
            src.buffer = buf;
            var g = actx.createGain();
            var t0 = actx.currentTime + (delay || 0);
            g.gain.setValueAtTime(vol, t0);
            g.gain.exponentialRampToValueAtTime(0.0001, t0 + dur);
            var node = src;
            if (lp && lp < 1) {
                var f = actx.createBiquadFilter();
                f.type = 'lowpass';
                f.frequency.value = Math.max(200, lp * actx.sampleRate * 0.06);
                src.connect(f); node = f;
            }
            node.connect(g); g.connect(master);
            src.start(t0);
            live++;
            src.onended = function () { live--; };
        }

        var TABLE = {
            shoot: function () { tone(880, 0.07, 'square', 0.34, 0.45); noise(0.07, 0.16, 0.9); },
            shoot_heavy: function () { tone(220, 0.16, 'sawtooth', 0.42, 0.4); noise(0.10, 0.25, 0.5); },
            laser: function () { tone(1500, 0.12, 'triangle', 0.34, 0.25); },
            rad_star: function () { tone(1290, .20, 'triangle', .42, .68); tone(1935, .12, 'sine', .22, 1.5); },
            rad_nova: function () { tone(360, .31, 'sawtooth', .42, .48); noise(.26, .42, .22); },
            rad_chrono: function () { tone(720, .24, 'triangle', .42, .35); tone(1440, .15, 'sine', .2, .7); },
            rad_life: function () { tone(520, .13, 'sine', .38, 1.6); tone(780, .21, 'triangle', .25, 1.3); },
            rad_prism: function () { tone(1680, .19, 'square', .35, .72); tone(2240, .10, 'triangle', .25, 1.2); },
            rad_orbit: function () { tone(180, .28, 'sawtooth', .38, 1.45); tone(90, .33, 'sine', .25, .6); },
            hit: function () { noise(0.07, 0.42, 0.6); },
            hurt: function () { tone(180, 0.20, 'sawtooth', 0.42, 0.5); noise(0.10, 0.30, 0.5); },
            explode: function () { noise(0.45, 0.85, 0.16); tone(70, 0.40, 'sine', 0.5, 0.6); },
            enemy_die: function () { tone(420, 0.22, 'square', 0.32, 0.35); noise(0.14, 0.35, 0.4); },
            boss_die: function () { noise(0.90, 0.90, 0.12); tone(90, 0.90, 'sawtooth', 0.5, 0.4); },
            coin: function () { tone(1180, 0.06, 'square', 0.30); tone(1760, 0.09, 'square', 0.24, 1, 0.03); },
            heart: function () { tone(660, 0.10, 'triangle', 0.34); tone(990, 0.16, 'triangle', 0.30, 1, 0.04); },
            energy: function () { tone(1320, 0.14, 'triangle', 0.30, 1.9); },
            door: function () { tone(150, 0.30, 'sawtooth', 0.34, 1.9); noise(0.30, 0.12, 0.8); },
            lock: function () { tone(120, 0.18, 'square', 0.34, 1.7); },
            dash: function () { tone(520, 0.13, 'triangle', 0.26, 2.6); },
            pickup: function () { tone(880, 0.07, 'square', 0.28); tone(1320, 0.11, 'square', 0.24, 1, 0.03); },
            ui: function () { tone(760, 0.05, 'square', 0.26); },
            ui_big: function () { tone(600, 0.09, 'square', 0.30); tone(900, 0.14, 'square', 0.26, 1, 0.04); },
            no_energy: function () { tone(150, 0.07, 'square', 0.30); },
            buy: function () {
                tone(700, 0.08, 'square', 0.30);
                tone(1050, 0.12, 'square', 0.26, 1, 0.05);
                tone(1400, 0.18, 'triangle', 0.22, 1, 0.10);
            },
            break: function () { noise(0.16, 0.50, 0.55); tone(320, 0.10, 'square', 0.22, 0.6); },
            level_up: function () {
                tone(523, 0.12, 'square', 0.30);
                tone(659, 0.12, 'square', 0.30, 1, 0.10);
                tone(784, 0.26, 'square', 0.30, 1, 0.20);
            },
            game_over: function () { tone(300, 0.50, 'triangle', 0.40, 0.35); tone(200, 0.70, 'sawtooth', 0.30, 0.3, 0.05); },
            victory: function () {
                tone(659, 0.14, 'square', 0.30);
                tone(784, 0.14, 'square', 0.30, 1, 0.12);
                tone(988, 0.34, 'square', 0.32, 1, 0.24);
            }
        };

        return {
            unlock: unlock,
            get enabled() { return enabled; },
            set enabled(v) { enabled = !!v; },
            play: function (name) {
                if (!enabled || !ensure()) { return; }
                if (name === 'man_what_can_i_say') {
                    var wav = window.__ASSETS__ && window.__ASSETS__['sfx/man_what_can_i_say.wav'];
                    if (wav) {
                        try { new Audio('data:audio/wav;base64,' + wav).play(); } catch (e0) { /* 音效降级 */ }
                    }
                    return;
                }
                var f = TABLE[name];
                if (!f) { return; }
                try { f(); } catch (e) { /* 音效失败绝不影响游戏 */ }
            },
            toggle: function () { enabled = !enabled; return enabled; }
        };
    })();

    // ---- 需求 11：程序合成的循环 BGM（与 Python audio.Music 对齐）
    // 纯 WebAudio 现场合成，不依赖任何外部音频文件；默认**关闭**。
    // 曲目按场景深度分 4 档（mood 0..3），越深越低沉紧张，与"污染入侵"呼应。
    var Music = (function () {
        var SCALE = [0, 2, 3, 5, 7, 8, 10, 12];   // 小调音阶（半音偏移）
        var BASE = 220.0;                          // A3
        // mood -> 音符序列（半音偏移）
        var SEQS = [
            [0, 4, 7, 4, 0, 4, 7, 9],          // 平和
            [0, 3, 7, 3, 0, 3, 8, 7],          // 微忧
            [0, 3, 5, 3, -1, 3, 5, 7],         // 紧张
            [-5, -1, 2, -1, -5, -1, 2, 3]      // 压抑
        ];
        var BEAT = 0.42;

        var actx = null, master = null;
        var enabled = false;
        var cur = null;          // 当前 mood（null = 没在播）
        var timer = null;
        var next_t = 0.0;
        var step = 0;
        var live = 0;

        function ensure() {
            if (actx) { return actx; }
            var AC = window.AudioContext || window.webkitAudioContext;
            if (!AC) { return null; }
            try {
                actx = new AC();
                master = actx.createGain();
                master.gain.value = 0.28;
                master.connect(actx.destination);
            } catch (e) { actx = null; }
            return actx;
        }
        function note(semi, dur, vol, wave, at) {
            if (!actx || live > 24) { return; }
            var f = BASE * Math.pow(2.0, semi / 12.0);
            var osc = actx.createOscillator();
            var g = actx.createGain();
            osc.type = wave || 'triangle';
            osc.frequency.setValueAtTime(f, at);
            g.gain.setValueAtTime(0.0001, at);
            g.gain.exponentialRampToValueAtTime(Math.max(0.0002, vol), at + 0.02);
            g.gain.exponentialRampToValueAtTime(0.0001, at + dur);
            osc.connect(g); g.connect(master);
            osc.start(at); osc.stop(at + dur + 0.02);
            live++;
            osc.onended = function () { live--; };
        }
        // 定时器推进音符序列（等价于 Python 的"整段波形循环"）
        function tick() {
            if (!actx || cur === null) { return; }
            var now = actx.currentTime;
            while (next_t < now + 0.5) {
                var seq = SEQS[clamp(cur, 0, SEQS.length - 1)];
                var s = seq[step % seq.length];
                note(s, BEAT * 0.92, 0.34, 'triangle', next_t);
                if (step % 2 === 0) {
                    note(s - 12, BEAT * 2.0, 0.22, 'sine', next_t);
                }
                next_t += BEAT;
                step++;
            }
        }
        function stop() {
            if (timer) { clearInterval(timer); timer = null; }
            cur = null;
            step = 0;
        }
        return {
            get enabled() { return enabled; },
            get mood() { return cur; },
            set_enabled: function (on, mood) {
                enabled = !!on;
                if (!enabled) { stop(); return; }
                if (!ensure()) { enabled = false; return; }
                if (actx && actx.state === 'suspended') { actx.resume(); }
                this.play(mood === undefined ? 0 : mood, true);
            },
            play: function (mood, force) {
                if (!enabled) { return false; }
                if (!ensure()) { return false; }
                mood = clamp(Math.trunc(mood || 0), 0, SEQS.length - 1);
                if (cur === mood && !force) { return true; }
                stop();
                cur = mood;
                step = 0;
                next_t = actx.currentTime + 0.05;
                if (actx.state === 'suspended') { actx.resume(); }
                timer = setInterval(tick, 120);
                tick();
                return true;
            }
        };
    })();

    // ==================================================================== 特效
    function Particle(x, y, vx, vy, life, color, size, drag, grav, shape, fade) {
        this.x = x; this.y = y; this.vx = vx; this.vy = vy;
        this.life = life; this.max_life = life;
        this.color = color; this.size = size;
        this.drag = drag === undefined ? 2.4 : drag;
        this.grav = grav || 0.0;
        this.shape = shape || 'square';
        this.fade = fade === undefined ? true : fade;
    }
    Particle.prototype.update = function (dt) {
        var k = Math.max(0.0, 1.0 - this.drag * dt);
        this.vx *= k; this.vy *= k;
        this.vy += this.grav * dt;
        this.x += this.vx * dt; this.y += this.vy * dt;
        this.life -= dt;
        return this.life > 0;
    };
    Particle.prototype.draw = function (cam) {
        var t = this.life / this.max_life;
        var a = 255.0 * (this.fade ? t : 1.0);
        var s = Math.max(1, Math.floor(this.size * (0.35 + 0.65 * t)));
        if (a <= 4) { return; }
        var x = this.x + cam[0], y = this.y + cam[1];
        ctx.fillStyle = cssColor(this.color, a / 255);
        if (this.shape === 'circle') {
            ctx.beginPath();
            ctx.arc(Math.round(x), Math.round(y), s, 0, TAU);
            ctx.fill();
        } else {
            ctx.fillRect(Math.round(x - s / 2), Math.round(y - s / 2), s, s);
        }
    };

    function Ring(x, y, r0, r1, life, color, width) {
        this.x = x; this.y = y; this.r0 = r0; this.r1 = r1;
        this.life = life; this.max_life = life;
        this.color = color; this.width = width === undefined ? 2 : width;
    }
    Ring.prototype.update = function (dt) { this.life -= dt; return this.life > 0; };
    Ring.prototype.draw = function (cam) {
        var t = 1.0 - this.life / this.max_life;
        var r = lerp(this.r0, this.r1, t);
        var a = 220.0 * (1.0 - t);
        if (r < 1 || a <= 4) { return; }
        ctx.beginPath();
        ctx.arc(Math.round(this.x + cam[0]), Math.round(this.y + cam[1]), r, 0, TAU);
        ctx.lineWidth = Math.max(1, this.width * (1 - t) + 1);
        ctx.strokeStyle = cssColor(this.color, a / 255);
        ctx.stroke();
    };

    function FloatText(x, y, s, color, size, life, vy) {
        this.x = x; this.y = y; this.text = s; this.color = color;
        this.size = size;
        this.life = life; this.max_life = life;
        this.vy = vy === undefined ? -34.0 : vy;
    }
    FloatText.prototype.update = function (dt) {
        this.y += this.vy * dt;
        this.vy *= Math.max(0.0, 1.0 - 2.2 * dt);
        this.life -= dt;
        return this.life > 0;
    };
    FloatText.prototype.draw = function (cam) {
        var t = this.life / this.max_life;
        var a = Math.min(1.0, t * 2.2);
        setFont(this.size);
        var w = ctx.measureText(this.text).width;
        var x = this.x + cam[0] - w / 2, y = this.y + cam[1];
        ctx.globalAlpha = a * 0.7;
        ctx.fillStyle = '#000';
        ctx.fillText(this.text, Math.round(x + 1), Math.round(y + 1));
        ctx.globalAlpha = a;
        ctx.fillStyle = cssColor(this.color);
        ctx.fillText(this.text, Math.round(x), Math.round(y));
        ctx.globalAlpha = 1;
    };

    function FX() {
        this.parts = []; this.rings = []; this.texts = [];
        this.shake = 0.0; this.shake_x = 0.0; this.shake_y = 0.0;
        this.flash = 0.0; this.flash_color = [255, 255, 255];
        this._rng = makeRng(20240923);
    }
    FX.prototype.burst = function (x, y, color, n, speed, life, size,
                                   spread, base_ang, drag, grav, shape) {
        n = n || 8; speed = speed === undefined ? 110.0 : speed;
        life = life === undefined ? 0.4 : life; size = size === undefined ? 3 : size;
        spread = spread === undefined ? TAU : spread;
        base_ang = base_ang || 0.0;
        drag = drag === undefined ? 2.6 : drag;
        grav = grav || 0.0;
        shape = shape || 'square';
        for (var i = 0; i < Math.max(0, n); i++) {
            var a = base_ang + this._rng.uniform(-spread / 2, spread / 2);
            var sp = speed * this._rng.uniform(0.35, 1.25);
            this.parts.push(new Particle(x, y, Math.cos(a) * sp, Math.sin(a) * sp,
                life * this._rng.uniform(0.7, 1.3), color, size, drag, grav, shape));
        }
        if (this.parts.length > 900) { this.parts.splice(0, this.parts.length - 900); }
    };
    FX.prototype.sparks = function (x, y, color, n, ang) {
        this.burst(x, y, color, n === undefined ? 6 : n, 150, 0.26, 2,
            1.1, ang || 0.0, 4.0);
    };
    FX.prototype.smoke = function (x, y, n, color) {
        this.burst(x, y, color || [96, 92, 104], n === undefined ? 5 : n, 42, 0.6, 4,
            TAU, 0, 2.0, -22.0, 'circle');
    };
    FX.prototype.blood = function (x, y, color, n, ang) {
        this.burst(x, y, color, n === undefined ? 7 : n, 125, 0.45, 3,
            (ang === undefined || ang === null) ? TAU : 1.4,
            ang || 0.0, 3.2, 180.0, 'circle');
    };
    FX.prototype.ring = function (x, y, r0, r1, life, color, width) {
        this.rings.push(new Ring(x, y, r0, r1, life, color, width));
    };
    // 需求 6：近战扇形挥砍特效（沿扇形铺开的小粒子模拟刀光）
    FX.prototype.arcSwing = function (x, y, ang, reach, arcDeg, color) {
        var n = Math.max(8, Math.trunc(reach * 0.32));
        var half = Math.max(10.0, arcDeg) * 0.5 * Math.PI / 180.0;
        for (var i = 0; i < n; i++) {
            var t = (i / (n - 1)) * 2.0 - 1.0;
            var a = ang + t * half;
            var r = reach * (0.72 + 0.28 * this._rng.random());
            this.parts.push(new Particle(
                x + Math.cos(a) * r, y + Math.sin(a) * r,
                Math.cos(a) * 40.0, Math.sin(a) * 40.0,
                0.20, color, 3, 6.0, 0.0, 'square'));
        }
        if (this.parts.length > 900) {
            this.parts.splice(0, this.parts.length - 900);
        }
    };
    FX.prototype.text = function (x, y, s, color, size, life) {
        if (this.texts.length > 60) { this.texts.splice(0, this.texts.length - 60); }
        this.texts.push(new FloatText(x, y, s, color, size, life === undefined ? 0.8 : life));
    };
    FX.prototype.add_shake = function (mag) { this.shake = Math.min(14.0, this.shake + mag); };
    FX.prototype.add_flash = function (a, color) {
        this.flash = Math.max(this.flash, a);
        this.flash_color = color || [255, 255, 255];
    };
    FX.prototype.clear = function () {
        this.parts.length = 0; this.rings.length = 0; this.texts.length = 0;
        this.shake = 0; this.shake_x = 0; this.shake_y = 0; this.flash = 0;
    };
    FX.prototype.update = function (dt) {
        var i, out = [];
        for (i = 0; i < this.parts.length; i++) {
            if (this.parts[i].update(dt)) { out.push(this.parts[i]); }
        }
        this.parts = out; out = [];
        for (i = 0; i < this.rings.length; i++) {
            if (this.rings[i].update(dt)) { out.push(this.rings[i]); }
        }
        this.rings = out; out = [];
        for (i = 0; i < this.texts.length; i++) {
            if (this.texts[i].update(dt)) { out.push(this.texts[i]); }
        }
        this.texts = out;
        if (this.shake > 0.01) {
            this.shake = Math.max(0.0, this.shake - 42.0 * dt);
            var m = this.shake;
            this.shake_x = this._rng.uniform(-m, m);
            this.shake_y = this._rng.uniform(-m, m);
        } else {
            this.shake = 0; this.shake_x = 0; this.shake_y = 0;
        }
        this.flash = Math.max(0.0, this.flash - dt * 3.4);
    };
    FX.prototype.draw_under = function (cam) {
        for (var i = 0; i < this.rings.length; i++) { this.rings[i].draw(cam); }
    };
    FX.prototype.draw_over = function (cam) {
        for (var i = 0; i < this.parts.length; i++) { this.parts[i].draw(cam); }
        for (var j = 0; j < this.texts.length; j++) { this.texts[j].draw(cam); }
    };

    // ==================================================================== 武器
    var WEAPONS = {
        pistol: {
            key: 'pistol', name: '学徒手枪', desc: '不耗能的万能开局枪',
            dmg: 7, cd: 0.26, speed: 430, count: 1, spread: 2.0, cost: 0.0,
            bullet: 'b_bullet', bsize: 13, pierce: 0, aoe: 0.0, life: 1.3,
            shake: 0.7, sound: 'shoot', kick: 0.0, color: [255, 214, 120], price: 0
        },
        smg: {
            key: 'smg', name: '蜂鸟冲锋枪', desc: '射速极快，耗能轻微',
            dmg: 4, cd: 0.095, speed: 470, count: 1, spread: 7.0, cost: 1.2,
            bullet: 'b_bolt', bsize: 14, pierce: 0, aoe: 0.0, life: 1.15,
            shake: 0.7, sound: 'shoot', kick: 0.0, color: [120, 232, 240], price: 45
        },
        shotgun: {
            key: 'shotgun', name: '蒸汽霰弹枪', desc: '近距离一枪糊脸',
            dmg: 4, cd: 0.72, speed: 380, count: 6, spread: 20.0, cost: 3.0,
            bullet: 'b_bullet', bsize: 12, pierce: 0, aoe: 0.0, life: 0.62,
            shake: 2.4, sound: 'shoot_heavy', kick: 26.0, color: [255, 186, 96], price: 55
        },
        laser: {
            key: 'laser', name: '幽蓝激光枪', desc: '高速穿透，指哪打哪',
            dmg: 10, cd: 0.17, speed: 940, count: 1, spread: 0.6, cost: 2.6,
            bullet: 'b_laser', bsize: 18, pierce: 3, aoe: 0.0, life: 0.85,
            shake: 0.6, sound: 'laser', kick: 0.0, color: [255, 96, 120], price: 65
        },
        rocket: {
            key: 'rocket', name: '脆脆火箭筒', desc: '大范围爆炸重炮，可摧毁掩体',
            dmg: 24, cd: 1.05, speed: 300, count: 1, spread: 1.5, cost: 5.0,
            bullet: 'b_rocket', bsize: 16, pierce: 0, aoe: 46.0, life: 1.6,
            shake: 3.4, sound: 'shoot_heavy', kick: 34.0, color: [200, 220, 200], price: 80
        },
        cannon: {
            key: 'cannon', name: '金色传说炮', desc: '三连高伤，稀有的传说武器',
            dmg: 15, cd: 0.34, speed: 540, count: 3, spread: 7.0, cost: 3.6,
            bullet: 'b_plasma', bsize: 16, pierce: 0, aoe: 0.0, life: 1.25,
            shake: 1.5, sound: 'shoot_heavy', kick: 6.0, color: [255, 226, 96], price: 110
        }
    };
    // 武器规格由 Python 数据层导出，避免网页版遗失近战与后期武器。
    WEAPONS = D.WEAPONS || WEAPONS;
    var WPN_ORDER = D.WPN_ORDER || Object.keys(WEAPONS);
    var DROP_POOL = {
        1: D.QUALITY_POOL.white.concat(D.QUALITY_POOL.green.slice(0, 5)),
        2: D.QUALITY_POOL.green.concat(D.QUALITY_POOL.blue.slice(0, 7),
            D.QUALITY_POOL.white.slice(0, 5)),
        3: D.QUALITY_POOL.blue.concat(D.QUALITY_POOL.purple,
            D.QUALITY_POOL.gold.slice(0, 2))
    };
    var BOSS_EXCLUSIVE_KEYS = (function () {
        var map = {}, sbw = D.SCENE_BOSS_WEAPONS || {};
        for (var sc in sbw) {
            if (!sbw.hasOwnProperty(sc)) { continue; }
            var row = sbw[sc] || {};
            for (var rk in row) {
                if (row.hasOwnProperty(rk) && row[rk]) { map[row[rk]] = true; }
            }
        }
        return map;
    })();
    var SHOP_QUALITY_WEIGHTS = {
        crust:    [['white', 55], ['green', 35], ['blue', 10]],
        sewer:    [['white', 20], ['green', 45], ['blue', 27], ['purple', 8]],
        facility: [['green', 20], ['blue', 42], ['purple', 30], ['gold', 8]],
        core:     [['blue', 25], ['purple', 45], ['gold', 24], ['red', 6]],
        d_mine:   [['white', 10], ['green', 30], ['blue', 40], ['purple', 17], ['gold', 3]],
        d_gift:   [['green', 20], ['blue', 40], ['purple', 30], ['gold', 10]],
        d_lab:    [['green', 10], ['blue', 32], ['purple', 40], ['gold', 15], ['red', 3]]
    };
    var ELITE_QUALITY_WEIGHTS = {
        crust:    [['white', 55], ['green', 33], ['blue', 12]],
        sewer:    [['white', 25], ['green', 45], ['blue', 24], ['purple', 6]],
        facility: [['green', 25], ['blue', 45], ['purple', 25], ['gold', 5]],
        core:     [['blue', 30], ['purple', 48], ['gold', 19], ['red', 3]],
        d_mine:   [['white', 15], ['green', 35], ['blue', 35], ['purple', 13], ['gold', 2]],
        d_gift:   [['green', 25], ['blue', 40], ['purple', 28], ['gold', 7]],
        d_lab:    [['green', 15], ['blue', 35], ['purple', 38], ['gold', 10], ['red', 2]]
    };
    var CHEST_QUALITY_WEIGHTS = {
        normal: {
            crust:    [['white', 45], ['green', 40], ['blue', 15]],
            sewer:    [['white', 15], ['green', 45], ['blue', 30], ['purple', 10]],
            facility: [['green', 15], ['blue', 45], ['purple', 32], ['gold', 8]],
            core:     [['blue', 20], ['purple', 50], ['gold', 25], ['red', 5]],
            d_mine:   [['white', 10], ['green', 28], ['blue', 42], ['purple', 17], ['gold', 3]],
            d_gift:   [['green', 15], ['blue', 40], ['purple', 33], ['gold', 12]],
            d_lab:    [['green', 10], ['blue', 30], ['purple', 42], ['gold', 15], ['red', 3]]
        },
        superb: {
            crust:    [['green', 40], ['blue', 45], ['purple', 15]],
            sewer:    [['blue', 45], ['purple', 45], ['gold', 10]],
            facility: [['blue', 20], ['purple', 52], ['gold', 24], ['red', 4]],
            core:     [['purple', 35], ['gold', 47], ['red', 18]],
            d_mine:   [['blue', 40], ['purple', 45], ['gold', 15]],
            d_gift:   [['blue', 25], ['purple', 50], ['gold', 22], ['red', 3]],
            d_lab:    [['blue', 15], ['purple', 45], ['gold', 32], ['red', 8]]
        }
    };
    function rollNonBossWeapons(rng, weights, count) {
        var total = 0, i;
        for (i = 0; i < weights.length; i++) { total += weights[i][1]; }
        function pickQuality() {
            var r = rng.random() * total, acc = 0, j;
            for (j = 0; j < weights.length; j++) {
                acc += weights[j][1];
                if (r <= acc) { return weights[j][0]; }
            }
            return weights[weights.length - 1][0];
        }
        var picked = [], n = Math.max(1, count || 1);
        for (i = 0; i < n; i++) {
            var q = pickQuality();
            var basePool = (D.QUALITY_POOL && D.QUALITY_POOL[q]) || D.QUALITY_POOL.white;
            var pool = basePool.filter(function (k) {
                return !BOSS_EXCLUSIVE_KEYS[k] && picked.indexOf(k) < 0;
            });
            if (!pool.length) {
                pool = basePool.filter(function (k) { return picked.indexOf(k) < 0; });
            }
            if (!pool.length) { pool = basePool.slice(); }
            picked.push(rng.choice(pool));
        }
        return picked;
    }
    function rollShopWeapons(rng, sceneKey, count) {
        var weights = SHOP_QUALITY_WEIGHTS[sceneKey] || SHOP_QUALITY_WEIGHTS.crust;
        return rollNonBossWeapons(rng, weights, count);
    }
    function rollEliteWeapon(rng, sceneKey) {
        var weights = ELITE_QUALITY_WEIGHTS[sceneKey] || ELITE_QUALITY_WEIGHTS.crust;
        var key = rollNonBossWeapons(rng, weights, 1)[0];
        var q = (D.WEAPON_QUALITY && D.WEAPON_QUALITY[key]) || 'white';
        return [key, q];
    }
    function rollChestWeapon(rng, sceneKey, tier) {
        var tbl = CHEST_QUALITY_WEIGHTS[tier] || CHEST_QUALITY_WEIGHTS.normal;
        var weights = tbl[sceneKey] || tbl.crust;
        var key = rollNonBossWeapons(rng, weights, 1)[0];
        var q = (D.WEAPON_QUALITY && D.WEAPON_QUALITY[key]) || 'white';
        return [key, q];
    }
    function wget(key) { return WEAPONS[key] || WEAPONS.pistol; }

    function weaponFlash(game, spec, x, y, ang, melee) {
        var seed = 0, i;
        for (i = 0; i < spec.key.length; i++) { seed += spec.key.charCodeAt(i); }
        var n = 2 + seed % 4;
        if (melee) {
            game.fx.burst(x, y, spec.color, n + 2, 90 + seed % 50,
                0.22, 2 + seed % 2, (spec.arc || 100) * Math.PI / 180,
                ang, 4);
            if (['sun', 'plasma', 'hammer', 'axe'].indexOf(spec.vfx) >= 0) {
                game.fx.ring(x, y, 7, Math.max(30, spec.reach * 0.72),
                    0.22, spec.color, 2 + seed % 2);
            }
            return;
        }
        game.fx.burst(x, y, spec.color, n, 68 + seed % 62,
            0.12 + (seed % 3) * 0.025, 2 + seed % 3,
            0.35 + spec.spread * 0.018, ang, 6);
        if (spec.aoe || ['nova', 'pulse', 'arc', 'prism', 'gravity', 'void'].indexOf(spec.vfx) >= 0) {
            game.fx.ring(x, y, 2, 12 + Math.min(15, spec.dmg * 0.4),
                0.15, spec.color, 1 + seed % 2);
        }
    }

    // ==================================================================== 子弹
    function explode(game, x, y, radius, dmg, hurt_player, color, bomber) {
        if (radius <= 0) { return; }
        color = color || [255, 168, 72];
        game.fx.ring(x, y, radius * 0.25, radius * 1.05, 0.34, color, 3);
        game.fx.burst(x, y, color, 20, radius * 4.2, 0.42, 4, TAU, 0, 2.6, 0, 'circle');
        game.fx.burst(x, y, [250, 240, 200], 10, radius * 3.0, 0.26, 3, TAU, 0, 3.4, 0, 'circle');
        game.fx.smoke(x, y, 8);
        Sfx.play('explode');
        game.fx.add_shake(Math.min(9.0, radius * 0.20));
        game.fx.add_flash(0.16, color);
        vibrate(game, 24);

        // 递归深度保护：连环爆炸（炸弹机器人互相引爆）不会无限递归
        var depth = game._explode_depth || 0;
        if (depth >= 4) { return; }
        game._explode_depth = depth + 1;
        try {
            var i, d, f;
            for (i = 0; i < game.enemies.length; i++) {
                var e = game.enemies[i];
                if (!e.alive) { continue; }
                d = dist(x, y, e.x, e.y);
                if (d < radius + e.radius) {
                    f = 1.0 - 0.55 * (d / Math.max(1.0, radius + e.radius));
                    e.take_damage(dmg * f, game, x, y);
                }
            }
            for (i = 0; i < game.props.length; i++) {
                var p = game.props[i];
                if (p.alive && dist(x, y, p.x, p.y) < radius + p.radius) {
                    p.take_damage(dmg, game, x, y);
                }
            }
            // 掩体（需求 3）：只有爆炸能摧毁，普通子弹打不动
            if (game.room) {
                for (i = 0; i < game.room.covers.length; i++) {
                    var cv = game.room.covers[i];
                    if (cv.alive && dist(x, y, cv.x, cv.y) < radius + cv.radius) {
                        cv.take_damage(dmg * 1.6, game, x, y);
                    }
                }
            }
            if (hurt_player && game.player.alive) {
                d = dist(x, y, game.player.x, game.player.y);
                if (d < radius + game.player.radius) {
                    if (game.player.take_damage(Math.max(1.0, dmg * 0.28), game, x, y)) {
                        if (bomber && game.on_bomber_hit) { game.on_bomber_hit(); }
                    }
                }
            }
        } finally {
            game._explode_depth = depth;
        }
    }

    function Bullet(x, y, ang, speed, dmg, friendly, img, size, radius, pierce, aoe, life, color, hit_shake) {
        this.x = x; this.y = y; this.ang = ang;
        this.vx = Math.cos(ang) * speed; this.vy = Math.sin(ang) * speed;
        this.dmg = dmg; this.friendly = friendly; this.img = img;
        this.size = size; this.radius = radius; this.pierce = pierce;
        this.aoe = aoe; this.life = life; this.color = color;
        this.alive = true; this.hits = []; this.hit_shake = hit_shake;
        this.exploded = false; this.trail = 0.0;
        // 需求 6（1.4）：品质机制 {'burst':n,'split':n,'homing':rad/s}
        this.mech = null;
        this.vfx = 'spark';
    }
    Bullet.prototype.kill = function (game, impact) {
        if (!this.alive) { return; }
        this.alive = false;
        if (this.aoe > 0 && !this.exploded) {
            this.exploded = true;
            explode(game, this.x, this.y, this.aoe, this.dmg, !this.friendly);
        } else if (impact) {
            game.fx.sparks(this.x, this.y, this.color, 4, this.ang);
            game.fx.burst(this.x, this.y, this.color, 3, 70, 0.2, 2, TAU, 0, 4.0);
        }
    };
    Bullet.prototype.update = function (game, dt) {
        if (!this.alive) { return; }
        this.life -= dt;
        if (this.life <= 0) { this.kill(game, false); return; }
        // 需求 6（璀璨级）：追猎弹道 —— 轻微转向最近敌人
        var homing = (this.mech && this.mech.homing) ? this.mech.homing : 0;
        if (homing > 0 && this.friendly && game.enemies.length) {
            var tgt = null, best = 1e18;
            for (var ti = 0; ti < game.enemies.length; ti++) {
                var te = game.enemies[ti];
                if (!te.alive) { continue; }
                var td = (te.x - this.x) * (te.x - this.x) +
                         (te.y - this.y) * (te.y - this.y);
                if (td < best) { best = td; tgt = te; }
            }
            if (tgt) {
                var want = Math.atan2(tgt.y - this.y, tgt.x - this.x);
                var da = (want - this.ang + Math.PI) % TAU - Math.PI;
                var step = Math.max(-homing * dt, Math.min(homing * dt, da));
                this.ang += step;
                var spd = Math.sqrt(this.vx * this.vx + this.vy * this.vy);
                this.vx = Math.cos(this.ang) * spd;
                this.vy = Math.sin(this.ang) * spd;
            }
        }
        var nx = this.x + this.vx * dt, ny = this.y + this.vy * dt;
        if (nx < -24 || nx > ROOM_PX_W + 24 || ny < -24 || ny > ROOM_PX_H + 24) {
            this.kill(game, false); return;
        }
        if (circleSolid(nx, ny, this.radius * 0.7, game.room.solid)) {
            this.kill(game, true); return;
        }
        // 掩体挡子弹（需求 3：掩体可掩护；但不能被普通子弹打坏）
        if (game.room) {
            var cvs = game.room.covers;
            for (var ci = 0; ci < cvs.length; ci++) {
                var cv = cvs[ci];
                if (!cv.alive) { continue; }
                var crr = this.radius + cv.radius;
                var cdx = nx - cv.x, cdy = ny - cv.y;
                if (cdx * cdx + cdy * cdy < crr * crr) {
                    game.fx.sparks(nx, ny, [196, 192, 178], 4, this.ang + Math.PI);
                    this.kill(game, false);
                    return;
                }
            }
        }
        this.x = nx; this.y = ny;
        this.trail -= dt;
        if (this.trail <= 0 && this.aoe <= 0) {
            this.trail = 0.045;
            game.fx.burst(this.x, this.y, this.color, 1, 18, 0.16, 2, TAU, 0, 4.0);
        }
        if (this.friendly) {
            this.hitEnemies(game);
            if (this.alive) { this.hitProps(game); }
        } else {
            this.hitPlayer(game);
        }
    };
    Bullet.prototype._seen = function (o) { return this.hits.indexOf(o) >= 0; };
    Bullet.prototype.hitEnemies = function (game) {
        for (var i = 0; i < game.enemies.length; i++) {
            var e = game.enemies[i];
            if (!e.alive || this._seen(e)) { continue; }
            var rr = this.radius + e.radius;
            var dx = this.x - e.x, dy = this.y - e.y;
            if (dx * dx + dy * dy < rr * rr) {
                this.hits.push(e);
                game.fx.sparks(this.x, this.y, this.color, 5, this.ang + Math.PI);
                var hp0 = e.hp;
                e.take_damage(this.dmg, game, this.x, this.y);
                weaponImpact(game, e, this.vfx, this.dmg, this.x, this.y);
                if (this.friendly && this.aoe <= 0 && game.run_stats &&
                        (game.run_stats.flags || []).indexOf('aoe_bullet') >= 0) {
                    explode(game, this.x, this.y, 44.0, Math.max(1.0, this.dmg * 0.45),
                        false, [255, 160, 80]);
                }
                var killed = (hp0 > 0 && e.hp <= 0);
                this._spawnSplit(game);
                if (killed) { this._spawnBurst(game); }
                if (this.pierce > 0) { this.pierce--; this.dmg *= 0.86; }
                else { this.kill(game, true); return; }
            }
        }
    };
    // 需求 6：命中分裂（红/璀璨级）—— 向附近敌人溅射
    Bullet.prototype._spawnSplit = function (game) {
        var n = (this.mech && this.mech.split) ? this.mech.split : 0;
        if (n <= 0 || !this.friendly) { return; }
        var cands = [];
        for (var i = 0; i < game.enemies.length; i++) {
            var e = game.enemies[i];
            if (!e.alive || this._seen(e)) { continue; }
            var d = Math.sqrt((e.x - this.x) * (e.x - this.x) +
                              (e.y - this.y) * (e.y - this.y));
            if (d < 150.0) { cands.push([d, e]); }
        }
        if (!cands.length) { return; }
        cands.sort(function (p, q) { return p[0] - q[0]; });
        for (var j = 0; j < Math.min(n, cands.length); j++) {
            var te = cands[j][1];
            var a = Math.atan2(te.y - this.y, te.x - this.x);
            var b = new Bullet(this.x, this.y, a, 460, this.dmg * 0.55, true,
                this.img, this.size, this.radius, 0, 0.0, 0.7, this.color,
                this.hit_shake * 0.6);
            game.bullets.push(b);
        }
    };
    // 需求 6：击杀迸射（金/红/璀璨级）—— 击杀点四周散射小弹
    Bullet.prototype._spawnBurst = function (game) {
        var n = (this.mech && this.mech.burst) ? this.mech.burst : 0;
        if (n <= 0 || !this.friendly) { return; }
        for (var i = 0; i < n; i++) {
            var a = this.ang + (i - (n - 1) * 0.5) * 0.7;
            var b = new Bullet(this.x, this.y, a, 380, this.dmg * 0.40, true,
                this.img, Math.max(8, this.size - 4),
                Math.max(2.5, this.radius * 0.7), 0, 0.0, 0.5, this.color,
                this.hit_shake * 0.5);
            game.bullets.push(b);
        }
    };
    Bullet.prototype.hitProps = function (game) {
        for (var i = 0; i < game.props.length; i++) {
            var p = game.props[i];
            if (!p.alive || this._seen(p)) { continue; }
            var rr = this.radius + p.radius;
            var dx = this.x - p.x, dy = this.y - p.y;
            if (dx * dx + dy * dy < rr * rr) {
                this.hits.push(p);
                p.take_damage(this.dmg, game, this.x, this.y);
                game.fx.sparks(this.x, this.y, [210, 180, 120], 4, this.ang + Math.PI);
                if (this.pierce > 0) { this.pierce--; }
                else { this.kill(game, true); return; }
            }
        }
    };
    Bullet.prototype.hitPlayer = function (game) {
        var pl = game.player;
        if (!pl.alive || this._seen(pl)) { return; }
        var rr = this.radius + pl.radius;
        var dx = this.x - pl.x, dy = this.y - pl.y;
        if (dx * dx + dy * dy < rr * rr) {
            this.hits.push(pl);
            pl.take_damage(this.dmg, game, this.x, this.y);
            this.kill(game, true);
        }
    };
    Bullet.prototype.draw = function (cam) {
        if (!this.alive) { return; }
        blit(this.img, this.x + cam[0], this.y + cam[1], this.size, this.size,
            { ang: this.ang });
    };

    // 需求 6：从规格反查品质机制（与 Python weapon.spec_mech 同源）
    function specMech(spec) {
        var base = (D.WEAPONS || {})[spec.key];
        if (!base) { return null; }
        var mech = null;
        var dc = Math.trunc(spec.count) - Math.trunc(base.count);
        var dp = Math.trunc(spec.pierce) - Math.trunc(base.pierce);
        var qs = ['white', 'green', 'blue', 'purple', 'gold', 'red', 'radiant'];
        for (var i = 0; i < qs.length; i++) {
            var mm = D.qualityMech(qs[i]);
            var needE = mm.extra || 0, needP = mm.pierce || 0;
            if (dc >= needE && dp >= needP) { mech = mm; }
        }
        return mech;
    }
    function weaponImpact(game, enemy, vfx, damage, x, y) {
        if (!enemy.alive || enemy.invuln) { return; }
        if (vfx === 'rad_star') {
            enemy.dot_t = Math.max(enemy.dot_t || 0, 1.8);
            enemy.dot_dps = Math.max(enemy.dot_dps || 0, damage * .24);
            game.fx.burst(enemy.x,enemy.y,[255,242,175],8,92,.35,3);
        } else if (vfx === 'rad_nova') {
            game.enemies.forEach(function (other) {
                if (other !== enemy && other.alive && dist(other.x,other.y,enemy.x,enemy.y)<76) {
                    other.take_damage(Math.max(1,damage*.18),game,enemy.x,enemy.y);
                }
            });
            game.fx.ring(enemy.x,enemy.y,6,76,.28,[255,237,181],3);
        } else if (vfx === 'rad_chrono' && !enemy.is_boss) {
            if (!(enemy.slow_t>0)) { enemy._slow_base_speed=enemy.speed; enemy.speed*=.45; }
            enemy.slow_t=Math.max(enemy.slow_t||0,2.2);
            game.fx.ring(enemy.x,enemy.y,3,enemy.radius+16,.35,[174,238,255],2);
        } else if (vfx === 'rad_life') {
            var pl=game.player, now=Number(game.time||0);
            if (now>=Number(pl._rad_heal_at||-1) && pl.hp<pl.max_hp) {
                pl.hp=Math.min(pl.max_hp,pl.hp+.45);pl._rad_heal_at=now+.55;
                game.fx.text(pl.x,pl.y-28,'+生命',[188,255,182],11,.55);
            }
            game.fx.burst(enemy.x,enemy.y,[188,255,182],5,64,.28,2);
        } else if (vfx === 'rad_prism') {
            game.enemies.filter(function(other){return other!==enemy&&other.alive&&dist(other.x,other.y,enemy.x,enemy.y)<142;})
                .sort(function(a,b){return dist(a.x,a.y,enemy.x,enemy.y)-dist(b.x,b.y,enemy.x,enemy.y);})
                .slice(0,2).forEach(function(other){
                    other.take_damage(Math.max(1,damage*.24),game,enemy.x,enemy.y);
                    game.fx.burst(other.x,other.y,[229,187,255],5,80,.22,2);
                });
        } else if (vfx === 'rad_orbit') {
            game.enemies.forEach(function(other){
                if(other===enemy||!other.alive||other.is_boss)return;
                var dx=enemy.x-other.x,dy=enemy.y-other.y,dd=Math.hypot(dx,dy);
                if(dd>12&&dd<135){other.kx+=dx/dd*110;other.ky+=dy/dd*110;}
            });
            game.fx.ring(enemy.x,enemy.y,7,70,.35,[181,204,255],2);
        } else if (vfx && vfx.indexOf('v30_')===0) {
            var seed=0;for(var s=0;s<vfx.length;s++)seed+=vfx.charCodeAt(s);
            game.fx.burst(enemy.x,enemy.y,[(seed*7)%128+110,(seed*11)%128+110,(seed*13)%128+110],
                4+seed%5,65+seed%50,.22+seed%3*.05,2+seed%2);
        } else if (vfx === 'frost' && !enemy.is_boss) {
            if (!(enemy.slow_t > 0)) {
                enemy._slow_base_speed = enemy.speed;
                enemy.speed *= 0.62;
            }
            enemy.slow_t = Math.max(enemy.slow_t || 0, 1.3);
            game.fx.ring(enemy.x, enemy.y, 3, enemy.radius + 9,
                0.25, [136,226,255], 2);
        } else if (['acid','flame','ember','sun'].indexOf(vfx) >= 0) {
            enemy.dot_t = Math.max(enemy.dot_t || 0, 2.0);
            enemy.dot_dps = Math.max(enemy.dot_dps || 0, damage * 0.17);
            game.fx.burst(enemy.x, enemy.y,
                vfx === 'acid' ? [160,243,103] : [255,142,73], 3,45,0.28,2);
        } else if (['arc','volt','coil'].indexOf(vfx) >= 0) {
            var other = null, best = 120 * 120;
            for (var i = 0; i < game.enemies.length; i++) {
                var e = game.enemies[i];
                if (e === enemy || !e.alive) { continue; }
                var d = (e.x-enemy.x)*(e.x-enemy.x)+(e.y-enemy.y)*(e.y-enemy.y);
                if (d < best) { other=e; best=d; }
            }
            if (other) {
                other.take_damage(Math.max(1,damage*0.28),game,enemy.x,enemy.y);
                game.fx.burst(other.x,other.y,[112,236,255],4,70,0.2,2);
            }
        } else if (vfx === 'gravity') {
            for (var j=0;j<game.enemies.length;j++) {
                var target=game.enemies[j];
                if (target===enemy || !target.alive || target.is_boss) { continue; }
                var dx=x-target.x, dy=y-target.y, dd=Math.hypot(dx,dy);
                if (dd>12 && dd<110) { target.kx+=dx/dd*65;target.ky+=dy/dd*65; }
            }
        }
    }

    function fire(game, spec, x, y, ang, friendly, dmg_mul) {
        dmg_mul = dmg_mul === undefined ? 1.0 : dmg_mul;
        var n = Math.max(1, spec.count);
        var spread = spec.spread * Math.PI / 180.0;
        // 1.1 天赋「贯穿」：额外穿透（只对玩家生效）
        var pierceExtra = 0;
        if (friendly) {
            if (game.run_stats) { pierceExtra += (game.run_stats.pierce || 0); }
            pierceExtra += (game.char_pierce_bonus || 0);
            if (game.player && game.player.wq(game) === 'purple') {
                var pq = (D.QUALITIES || {}).purple || {};
                if (game.player.wlevel(game) >= (pq.max_lv || 6)) { pierceExtra += 1; }
            }
        }
        var mech = friendly ? specMech(spec) : null;
        var made = 0;
        for (var i = 0; i < n; i++) {
            var a;
            if (n === 1) {
                a = (spread > 0 && game && game.rng)
                    ? (ang + game.rng.uniform(-spread * 0.5, spread * 0.5))
                    : ang;
            }
            else { a = ang + ((i / (n - 1)) - 0.5) * spread; }
            var b = new Bullet(
                x, y, a, spec.speed, spec.dmg * dmg_mul, friendly,
                spec.bullet, spec.bsize, Math.max(3.0, spec.bsize * 0.34),
                spec.pierce + pierceExtra, spec.aoe, spec.life, spec.color,
                spec.shake);
            if (mech) { b.mech = mech; }
            b.vfx = spec.vfx || 'spark';
            game.bullets.push(b);
            made++;
        }
        return made;
    }

    // 需求 6：近战挥砍 —— 身前扇形内所有敌人受创（与 Python melee_swing 同源）
    function meleeSwing(game, spec, x, y, ang, dmg_mul) {
        dmg_mul = dmg_mul === undefined ? 1.0 : dmg_mul;
        var half = Math.max(10.0, spec.arc) * 0.5 * Math.PI / 180.0;
        var reach = Math.max(82.0, spec.reach);
        var dmg = spec.dmg * dmg_mul;
        var hits = 0;
        for (var i = 0; i < game.enemies.length; i++) {
            var e = game.enemies[i];
            if (!e.alive) { continue; }
            var d = Math.sqrt((e.x - x) * (e.x - x) + (e.y - y) * (e.y - y));
            if (d > reach + e.radius) { continue; }
            var ea = Math.atan2(e.y - y, e.x - x);
            var da = Math.abs(Math.atan2(Math.sin(ea - ang), Math.cos(ea - ang)));
            if (da <= half) {
                e.take_damage(dmg, game, x, y);
                weaponImpact(game, e, spec.vfx, dmg, x, y);
                if (e.kx !== undefined) {
                    e.kx += Math.cos(ea) * 120.0;
                    e.ky += Math.sin(ea) * 120.0;
                }
                hits++;
            }
        }
        for (var pi = 0; pi < game.props.length; pi++) {
            var p = game.props[pi];
            if (!p.alive) { continue; }
            var pa = Math.atan2(p.y - y, p.x - x);
            var pd = Math.abs(Math.atan2(Math.sin(pa - ang), Math.cos(pa - ang)));
            if (dist(p.x, p.y, x, y) <= reach + p.radius && pd <= half) {
                p.take_damage(dmg, game, x, y);
                hits++;
            }
        }
        for (var bi = 0; bi < game.bullets.length; bi++) {
            var b = game.bullets[bi];
            if (!b.alive || b.friendly) { continue; }
            var ba = Math.atan2(b.y - y, b.x - x);
            var bd = Math.abs(Math.atan2(Math.sin(ba - ang), Math.cos(ba - ang)));
            if (dist(b.x, b.y, x, y) <= reach + b.radius && bd <= half) {
                b.alive = false;
                game.fx.sparks(b.x, b.y, spec.color, 5, ang);
                hits++;
            }
        }
        game.fx.arcSwing(x, y, ang, reach, spec.arc, spec.color);
        return hits;
    }

    // ==================================================================== 掉落
    var MAGNET_KINDS = ['coin', 'diamond', 'heart', 'energy', 'key', 'collect',
        'material'];
    var MAGNET_R = 74.0, MAGNET_SPEED = 250.0, TOUCH_PAD = 9.0, PROMPT_R = 34.0;

    function Basketball(x, y) {
        this.x = x; this.y = y; this.alive = true; this.life = 3;
        this.hits = 0; this.hit_ids = []; this.radius = 11; this.spin = 0;
        this.dmg = 24;
    }
    Basketball.prototype.update = function (game, dt) {
        if (!this.alive) { return; }
        this.life -= dt;
        if (this.life <= 0) { this.alive = false; return; }
        var targets = game.enemies.filter(function (e) {
            return e.alive && !e.invuln && this.hit_ids.indexOf(e) < 0;
        }, this);
        if (!targets.length) { this.alive = false; return; }
        targets.sort(function (a, b) {
            return dist(this.x, this.y, a.x, a.y) - dist(this.x, this.y, b.x, b.y);
        }.bind(this));
        var target = targets[0], dx = target.x - this.x, dy = target.y - this.y;
        var d = Math.hypot(dx, dy), step = Math.min(d, 390 * dt);
        if (d > 0) { this.x += dx / d * step; this.y += dy / d * step; }
        this.spin += dt * 9;
        if (d - step <= this.radius + target.radius) {
            this.hit_ids.push(target); this.hits++;
            game._basket_chain = true;
            try {
                var hitDmg = (game.rng && game.rng.random() < 0.08) ? 81 : this.dmg;
                target.take_damage(hitDmg, game);
            } finally { game._basket_chain = false; }
            game.fx.burst(this.x, this.y, [246, 151, 53], 10, 135, .32, 3);
            Sfx.play('hit');
            if (this.hits >= 2) { this.alive = false; }
        }
    };
    Basketball.prototype.draw = function (cam) {
        if (!this.alive) { return; }
        var x = Math.round(this.x + cam[0]), y = Math.round(this.y + cam[1]);
        blit('basketball', x, y, 24, 24);
    };

    function Pickup(x, y, kind, value, wkey, price, ckey, ctier, quality) {
        this.x = x; this.y = y; this.kind = kind;
        this.value = value === undefined ? 1 : value;
        this.wkey = wkey || null;
        this.quality = (kind === 'weapon' || kind === 'shop_weapon') && wkey
            ? (D.WEAPON_QUALITY || {})[wkey] || 'white' : (quality || 'white');
        this.ckey = ckey || null;  // 收集品 key / 宝箱类别（需求 7、9）
        this.ctier = ctier || 'normal';   // 宝箱档位：normal 一般 / superb 极品
        this.price = price || 0;
        this.alive = true; this.bob = 0.0;
        this.phase = (x * 0.07 + y * 0.11) % TAU;
        this.radius = 9.0;
        this.life = -1.0;
        this.spawn_t = 0.0;
        // 武器自动交换用"沿触发"（进入半径那一刻才换一次），
        // 防止在玩家脚下反复换枪导致死循环，见 swapWeapon 注释。
        this.was_inside = false;
    }
    Pickup.prototype.sprite = function () {
        var m = {
            coin: 'coin', diamond: 'diamond',
            heart: 'heart', energy: 'energy', key: 'key',
            collect: 'collect_' + (this.ckey || 'gear_cog'),
            material: 'material_' + (this.ckey || 'scrap'),
            chest: 'chest_' + (this.ckey || 'coin') + '_' + this.ctier,
            shop_heart: 'heart',
            shop_hp_potion: 'potion_health',
            shop_energy_potion: 'potion_energy',
            drink: 'drink_' + (this.ckey || 'nectar'),
            weapon: D.spriteKey(this.wkey || 'pistol'),
            shop_weapon: D.spriteKey(this.wkey || 'pistol')
        };
        return m[this.kind] || 'coin';
    };
    Pickup.prototype.isInteract = function () {
        return this.kind === 'chest' || this.kind === 'shop_weapon' ||
            this.kind === 'shop_heart' || this.kind === 'shop_hp_potion' ||
            this.kind === 'shop_energy_potion' || this.kind === 'drink' ||
            this.kind === 'weapon';
    };
    Pickup.prototype.update = function (game, dt) {
        if (!this.alive) { return; }
        this.bob += dt; this.spawn_t += dt;
        if (this.life > 0) {
            this.life -= dt;
            if (this.life <= 0) { this.alive = false; return; }
        }
        var pl = game.player;
        if (!pl.alive) { return; }
        if (MAGNET_KINDS.indexOf(this.kind) >= 0 && this.spawn_t > 0.18) {
            if (game.run_stats && (game.run_stats.flags || []).indexOf('auto_collect') >= 0) {
                this.collect(game);
                return;
            }
            var d = dist(this.x, this.y, pl.x, pl.y);
            // 1.1 天赋「引力场」：拾取范围加成
            var mr = MAGNET_R;
            mr *= (1.0 + ((game.run_stats && game.run_stats.magnet_mul) || 0.0) +
                (game.char_magnet_mul || 0.0));
            if (d < mr) {
                if (d < pl.radius + TOUCH_PAD) { this.collect(game); return; }
                var k = MAGNET_SPEED * dt / Math.max(1.0, d);
                this.x += (pl.x - this.x) * k;
                this.y += (pl.y - this.y) * k;
            }
        }
    };
    Pickup.prototype.collect = function (game) {
        this.alive = false;
        var pl = game.player;
        if (this.kind === 'coin') {
            // 1.3：金币持有上限，超出部分不再增加
            var r = D.addCoin(game.coins, this.value);
            game.coins = r[0];
            if (r[1] <= 0) {
                game.fx.text(this.x, this.y - 10, '已满', C_WARN, 11, 0.8);
                return;
            }
            Sfx.play('coin');
            game.fx.sparks(this.x, this.y, C_GOLD, 4, 0);
        } else if (this.kind === 'diamond') {
            // 需求 4：钻石难得——只在首领/深层出现
            var before = parseInt(game.diamonds || 0, 10) || 0;
            game.diamonds = D.clampDiamond(before + this.value);
            var got = game.diamonds - before;
            game.run_diamonds = (game.run_diamonds || 0) + got;
            Sfx.play('pickup');
            game.fx.text(this.x, this.y - 10, '+' + got + '钻', C_DIA, 11, 0.9);
            game.fx.burst(this.x, this.y, C_DIA, 14, 150, 0.6, 3, TAU, 0, 2.6, 0, 'circle');
        } else if (this.kind === 'key') {
            var rk = D.addCoin(game.coins, this.value);
            game.coins = rk[0];
            if (rk[1] <= 0) { return; }
            Sfx.play('pickup');
            game.fx.text(this.x, this.y - 10, '+' + rk[1] + '金', C_GOLD, 11, 0.9);
            game.fx.burst(this.x, this.y, C_GOLD, 12, 140, 0.5, 3, TAU, 0, 2.6, 0, 'circle');
        } else if (this.kind === 'heart') {
            pl.hp = Math.min(pl.max_hp, pl.hp + this.value);
            Sfx.play('heart');
            game.fx.text(this.x, this.y - 10, '+' + this.value + 'HP', C_HP, 11, 0.9);
            game.fx.burst(this.x, this.y, C_HP, 12, 130, 0.5, 3, TAU, 0, 2.6, 0, 'circle');
        } else if (this.kind === 'energy') {
            pl.energy = Math.min(pl.max_energy, pl.energy + this.value);
            Sfx.play('energy');
            game.fx.text(this.x, this.y - 10, '+' + Math.trunc(this.value) + 'EN', C_ENERGY, 11, 0.9);
            game.fx.burst(this.x, this.y, C_ENERGY, 10, 130, 0.45, 3, TAU, 0, 2.6, 0, 'circle');
        } else if (this.kind === 'material') {
            // 需求 7：宝箱开出的材料进背包（退出时并入存档）
            var mkey = this.ckey || 'scrap';
            var mn = Math.max(1, Math.trunc(this.value || 1));
            game.mats[mkey] = Math.trunc(game.mats[mkey] || 0) + mn;
            Sfx.play('pickup');
            var mv = D.MATERIALS[mkey];
            var mname = mv ? mv[0] : mkey;
            game.fx.text(this.x, this.y - 10, mname + ' +' + mn, [170, 240, 200], 11, 0.95);
            game.fx.burst(this.x, this.y, [140, 230, 190], 10, 130, 0.5, 3, TAU, 0, 2.6, 0, 'circle');
            try { game.discover('material', mkey); } catch (e2) { /* 忽略 */ }
        } else if (this.kind === 'collect') {
            // 需求 9：收集品 -> 记图鉴 + 自动上展示台
            var ck = this.ckey || 'relic_gear';
            var first = false;
            try { first = game.collect_got(ck); } catch (e) { first = false; }
            Sfx.play('ui_big');
            var cv = D.COLLECTS[ck];
            var cname = cv ? cv[0] : ck;
            var ccol = (cv && cv[1] === 'superb') ? C_GOLD : [170, 200, 230];
            game.fx.text(this.x, this.y - 12, cname, [255, 236, 170], 12, 1.3);
            if (first) {
                game.fx.text(this.x, this.y - 28, '新收藏！', ccol, 11, 1.4);
                game.toast('收录收藏品', cname, ccol);
            }
            game.fx.burst(this.x, this.y, ccol, 16, 160, 0.6, 3, TAU, 0, 2.6, 0, 'circle');
            game.fx.ring(this.x, this.y, ccol);
            game.collection_popup = { key: ck, t: 2.3, life: 2.3 };
        }
        // 拾取立即落盘，死亡或异常关闭后货币、材料与收集品仍在档中。
        game._write_save();
    };
    Pickup.prototype.swapWeapon = function (game) {
        var pl = game.player, old = pl.wkey;
        var oldQ = D.qualityForWeapon(old);
        if (!pl.wkey2) {
            if (this.wkey === old) { return; }
            pl.wkey2 = this.wkey;
            pl.wqual2 = this.quality;
            this.alive = false;
            Sfx.play('pickup');
            game.discover('weapon', this.wkey);
            if (game.profile) {
                var qualities = game.profile.weapon_qualities || (game.profile.weapon_qualities = {});
                qualities[this.wkey] = this.quality;
                game._write_save();
            }
            game.toast('第二武器已解锁', mobileUI() ? '点击「换」切换' : '按 Q 切换',
                [180, 220, 255]);
            return;
        }
        if (this.wkey === old) {
            return;
        }
        pl.wkey = this.wkey;
        pl.wqual = this.quality;
        this.alive = false;
        Sfx.play('pickup');
        var spec = wget(this.wkey);
        game.fx.text(this.x, this.y - 12, spec.name,
            ((D.QUALITIES || {})[this.quality] || {}).color || C_WHITE, 12, 1.2);
        game.fx.burst(this.x, this.y, spec.color, 14, 150, 0.5, 3, TAU, 0, 2.6, 0, 'circle');
        // 旧武器掉在原地，可换回。
        // 必须标记 was_inside=true：否则这把新枪会在"玩家脚下"被立刻再次触发交换，
        // 于是 A->B->A->B…… 无限往返，每次还 push 一个新 Pickup 进正在被遍历的
        // 同一数组 —— 表现为游戏卡死 + 内存爆掉（实测可涨到 4GB）。
        // 标记后必须"先走出去、再走回来"才会再换，既修掉死循环也更符合手感。
        var dropped = new Pickup(this.x, this.y, 'weapon', 1, old,
            0, null, 'normal', oldQ);
        dropped.was_inside = true;
        game.pickups.push(dropped);
        try { game.discover('weapon', this.wkey); } catch (e2) { /* 忽略 */ }
        if (game.profile) {
            var owned = game.profile.weapon_qualities || (game.profile.weapon_qualities = {});
            owned[this.wkey] = this.quality;
            game.profile.weapon = this.wkey;
            game._write_save();
        }
    };
    Pickup.prototype.canInteract = function (pl) {
        return this.alive && this.isInteract() && dist(this.x, this.y, pl.x, pl.y) < PROMPT_R;
    };
    // 需求 7：宝箱分 5 类 × 2 档，提示/确认里带上具体名字
    Pickup.prototype.chestName = function () {
        try {
            var c = (D.CHESTS || {})[this.ckey || 'coin'] || {};
            var t = c[this.ctier] || c.normal || {};
            return t.name || '宝箱';
        } catch (e) { return '宝箱'; }
    };
    Pickup.prototype.promptText = function () {
        var action = mobileUI() ? '交互  ' : 'E  ';
        if (this.kind === 'chest') { return action + '开启' + this.chestName(); }
        if (this.kind === 'weapon') {
            var q = (D.QUALITIES || {})[this.quality] || {};
            var qm = parseFloat(q.mul) || 1.0;
            var qs = D.applyQuality ? D.applyQuality(this.wkey, this.quality, qm) : null;
            var ws = qs || wget(this.wkey);
            var wdmg = Math.max(1, Math.round(ws.dmg || 1));
            var wcnt = ws.count || 1;
            var wspd = (1.0 / Math.max(0.01, ws.cd || 0.25)).toFixed(1);
            var wcrit = Math.round((0.08 + ((window.__GAME__ && window.__GAME__.char_crit_bonus) || 0)) * 100);
            var wtag = ' [伤' + (wcnt > 1 ? (wdmg + '×' + wcnt) : wdmg) + ' 速' + wspd + '/s 暴' + Math.min(65, wcrit) + '%]';
            return action + '拾取' + (q.name || '白色') + '·' + wget(this.wkey).name + wtag;
        }
        if (this.kind === 'shop_weapon') {
            var sq = (D.QUALITIES || {})[this.quality] || {};
            var sqm = parseFloat(sq.mul) || 1.0;
            var sqs = D.applyQuality ? D.applyQuality(this.wkey, this.quality, sqm) : null;
            var sw = wget(this.wkey);
            var sdmg = Math.max(1, Math.round((sqs ? sqs.dmg : sw.dmg) || 1));
            var scnt = (sqs ? sqs.count : sw.count) || 1;
            var sspd = (1.0 / Math.max(0.01, (sqs ? sqs.cd : sw.cd) || 0.25)).toFixed(1);
            var scrit = Math.round((0.08 + ((window.__GAME__ && window.__GAME__.char_crit_bonus) || 0)) * 100);
            var stag = ' [伤' + (scnt > 1 ? (sdmg + '×' + scnt) : sdmg) + ' 速' + sspd + '/s 暴' + Math.min(65, scrit) + '%]';
            return action + this.price + '金 ' + (sq.name || '普通') + '·' + sw.name + '：' + sw.desc + stag;
        }
        if (this.kind === 'drink') {
            var names = { nectar: '琼浆玉液', dew: '杨枝甘露', soda: '沙氏汽水', tea: '劳大冰红茶' };
            var effects = { nectar: '生命上限 +25%', dew: '每秒回1蓝',
                soda: '攻速 +12%', tea: '击杀发射固伤篮球' };
            return action + this.price + '金 ' + names[this.ckey] + '·' + effects[this.ckey];
        }
        if (this.kind === 'shop_hp_potion' || this.kind === 'shop_energy_potion') {
            return action + this.price + '金 ' +
                (this.kind === 'shop_hp_potion' ? '血瓶：回复 6 点生命' : '蓝瓶：回复 80 点蓝量');
        }
        if (['shop_weapon', 'shop_heart', 'shop_hp_potion', 'shop_energy_potion', 'drink'].indexOf(this.kind) >= 0) {
            return action + this.price + '金  购买';
        }
        return '';
    };
    Pickup.prototype.interact = function (game) {
        var pl = game.player;
        if (this.kind === 'chest') {
            this.alive = false;
            var ckey = this.ckey || 'coin';
            var cs = ((D.CHESTS || {})[ckey] || {})[this.ctier] ||
                (((D.CHESTS || {}).coin || {}).normal) || {};
            var col = cs.color || C_GOLD;
            Sfx.play('ui_big');
            game.fx.burst(this.x, this.y, col, 26, 190, 0.7, 4, TAU, 0, 2.6, 0, 'circle');
            game.fx.ring(this.x, this.y, 6, 54, 0.42, col, 3);
            game.fx.text(this.x, this.y - 30, cs.name || '宝箱', col, 12, 1.1);
            // 需求 7：开箱结算走 D.chestLoot（5 类 × 2 档）
            var loot = D.chestLoot(game.rng, ckey, this.ctier, game.floor);
            for (var ci = 0; ci < (loot.coins || 0); ci++) {
                var ca = game.rng.uniform(0, TAU), cd = game.rng.uniform(12, 30);
                game.pickups.push(new Pickup(this.x + Math.cos(ca) * cd,
                    this.y + Math.sin(ca) * cd, 'coin', 1));
            }
            for (var di = 0; di < (loot.diamonds || 0); di++) {
                var da = game.rng.uniform(0, TAU), dd = game.rng.uniform(14, 26);
                game.pickups.push(new Pickup(this.x + Math.cos(da) * dd,
                    this.y + Math.sin(da) * dd, 'diamond', 1));
            }
            for (var hi = 0; hi < (loot.heal || 0); hi++) {
                var ha = game.rng.uniform(0, TAU), hd = game.rng.uniform(14, 26);
                game.pickups.push(new Pickup(this.x + Math.cos(ha) * hd,
                    this.y + Math.sin(ha) * hd, 'heart', 1));
            }
            if (loot.energy) {
                game.pickups.push(new Pickup(this.x, this.y - 22, 'energy', loot.energy));
            }
            var mk;
            for (mk in (loot.mats || {})) {
                if (!Object.prototype.hasOwnProperty.call(loot.mats, mk)) { continue; }
                // 材料直接进背包：宝箱已二次确认，无需再捡一遍
                var mnum = Math.max(0, Math.trunc(loot.mats[mk]));
                if (mnum <= 0) { continue; }
                game.mats[mk] = Math.trunc(game.mats[mk] || 0) + mnum;
                var ma = game.rng.uniform(0, TAU), md = game.rng.uniform(14, 26);
                var mmv = D.MATERIALS[mk];
                game.fx.text(this.x + Math.cos(ma) * md,
                    this.y + Math.sin(ma) * md - 12,
                    (mmv ? mmv[0] : mk) + ' +' + mnum, [170, 240, 200], 11, 1.0);
                try { game.discover('material', mk); } catch (e3) { /* 忽略 */ }
            }
            // 武器箱（或任意箱的武器掉落）掉一把武器
            if (ckey === 'weapon' || loot.quality) {
                var csc = (game.level_state || {}).scene;
                var cw = rollChestWeapon(game.rng, csc, this.ctier);
                game.pickups.push(new Pickup(this.x, this.y - 16, 'weapon', 1,
                    cw[0], 0, null, 'normal', cw[1]));
            }
            // 收集箱：开收集品；其余箱 35% 概率附带
            if (ckey === 'collect' || game.rng.random() < 0.08) {
                var tier = (this.ctier === 'superb' || game.rng.random() < 0.22)
                    ? 'superb' : 'common';
                var ck = D.rollCollect(game.rng, tier);
                var pc = new Pickup(this.x, this.y - 26, 'collect', 1);
                pc.ckey = ck;
                game.pickups.push(pc);
            }
            return true;
        }
        if (this.kind === 'shop_weapon') {
            if (game.coins < this.price) {
                Sfx.play('no_energy');
                game.fx.text(pl.x, pl.y - 22, '金币不足', C_WARN, 12, 0.9);
                return false;
            }
            game.coins -= this.price;
            Sfx.play('buy');
            var old = pl.wkey;
            var oldQ = D.qualityForWeapon(old);
            this.alive = false;
            if (!pl.wkey2) {
                pl.wkey2 = this.wkey; pl.wqual2 = this.quality;
            } else {
                pl.wkey = this.wkey; pl.wqual = this.quality;
                game.pickups.push(new Pickup(this.x, this.y, 'weapon', 1, old,
                    0, null, 'normal', oldQ));
            }
            game.discover('weapon', this.wkey);
            if (game.profile) {
                var shopOwned = game.profile.weapon_qualities || (game.profile.weapon_qualities = {});
                shopOwned[this.wkey] = this.quality;
                if (pl.wkey === this.wkey) { game.profile.weapon = this.wkey; }
                game._write_save();
            }
            game.fx.text(pl.x, pl.y - 22, '购买成功', C_ACCENT, 12, 1.0);
            return true;
        }
        if (this.kind === 'shop_heart') {
            if (pl.hp >= pl.max_hp) {
                Sfx.play('no_energy');
                game.fx.text(pl.x, pl.y - 22, '血量已满', C_WARN, 12, 0.9);
                return false;
            }
            if (game.coins < this.price) {
                Sfx.play('no_energy');
                game.fx.text(pl.x, pl.y - 22, '金币不足', C_WARN, 12, 0.9);
                return false;
            }
            game.coins -= this.price;
            pl.hp = Math.min(pl.max_hp, pl.hp + 2);
            Sfx.play('buy');
            game.fx.text(pl.x, pl.y - 22, '+2 HP', C_HP, 12, 1.0);
            this.alive = false;
            return true;
        }
        if (this.kind === 'shop_hp_potion' || this.kind === 'shop_energy_potion' ||
            this.kind === 'drink') {
            if (game.coins < this.price) { Sfx.play('no_energy'); return false; }
            if (this.kind === 'shop_hp_potion' && pl.hp >= pl.max_hp) { return false; }
            if (this.kind === 'shop_energy_potion' && pl.energy >= pl.max_energy) { return false; }
            game.drink_buffs = game.drink_buffs || {};
            game.coins -= this.price;
            if (this.kind === 'shop_hp_potion') { pl.hp = Math.min(pl.max_hp, pl.hp + 6); }
            else if (this.kind === 'shop_energy_potion') {
                pl.energy = Math.min(pl.max_energy, pl.energy + 80);
            } else {
                var previous = Number(game.drink_buffs[this.ckey] || 0);
                game.drink_buffs[this.ckey] = previous + 1;
                if (this.ckey === 'nectar') {
                    var increase = pl.max_hp * 0.25 / (1 + 0.25 * previous);
                    pl.max_hp += increase;
                    pl.hp = Math.min(pl.max_hp, pl.hp + increase);
                }
            }
            Sfx.play('buy');
            game.fx.text(pl.x, pl.y - 22, this.kind === 'drink' ?
                ({ nectar: '琼浆玉液', dew: '杨枝甘露', soda: '沙氏汽水', tea: '劳大冰红茶' }[this.ckey] || '饮料') :
                '补给已使用', C_ACCENT, 12, 1.0);
            return true;
        }
        if (this.kind === 'weapon') { this.swapWeapon(game); return true; }
        return false;
    };
    Pickup.prototype.draw = function (cam) {
        if (!this.alive) { return; }
        var size = (this.kind === 'coin' || this.kind === 'diamond' ||
            this.kind === 'heart' ||
            this.kind === 'energy' || this.kind === 'key') ? 22 : 26;
        if (this.kind === 'collect') { size = 26; }
        if (this.kind === 'weapon' || this.kind === 'shop_weapon') { size = 28; }
        var off = Math.sin(this.bob * 3.0 + this.phase) * 2.2;
        var x = this.x + cam[0], y = this.y + cam[1];
        if (this.kind === 'weapon' || this.kind === 'shop_weapon') {
            var rarityColor = ((D.QUALITIES || {})[this.quality] || {}).color || [240, 240, 240];
            ctx.beginPath();
            ctx.arc(Math.round(x), Math.round(y + off), 20, 0, TAU);
            ctx.strokeStyle = cssColor(rarityColor, 1);
            ctx.lineWidth = 2;
            ctx.stroke();
        }
        if (this.kind !== 'chest') {
            drawShadow(x, y + 8, size * 0.36, size * 0.18, 120);
        } else {
            // 需求 7：宝箱按「类别 × 档位」着色，一眼区分 5 类，极品更亮
            var cs = ((D.CHESTS || {})[this.ckey || 'coin'] || {})[this.ctier] || {};
            var cc = cs.color || [255, 206, 74];
            ctx.beginPath();
            ctx.arc(Math.round(x), Math.round(y + off), (size + 13) / 2, 0, TAU);
            ctx.fillStyle = cssColor(cc, (this.ctier === 'superb' ? 96 : 54) / 255);
            ctx.fill();
            if (this.ctier === 'superb') {
                ctx.beginPath();
                ctx.arc(Math.round(x), Math.round(y + off), size * 0.52, 0, TAU);
                ctx.strokeStyle = cssColor(cc, 1.0);
                ctx.lineWidth = 2;
                ctx.stroke();
            }
        }
        var glowMap = {
            coin: [255, 210, 90], diamond: [140, 230, 255],
            key: [255, 210, 90], energy: [110, 220, 255],
            heart: [255, 90, 100], shop_heart: [255, 90, 100],
            collect: [255, 236, 170]
        };
        if (glowMap[this.kind]) {
            var c = glowMap[this.kind];
            ctx.beginPath();
            ctx.arc(Math.round(x), Math.round(y + off), (size + 8) / 2, 0, TAU);
            ctx.fillStyle = cssColor(c, 46 / 255);
            ctx.fill();
        }
        blit(this.sprite(), x, y + off, size, size);
        if (['shop_weapon', 'shop_heart', 'shop_hp_potion', 'shop_energy_potion', 'drink'].indexOf(this.kind) >= 0) {
            txt(this.price + '金', 11, C_GOLD, x, y + 16 + off, 'midtop');
        }
    };

    function Prop(x, y, kind) {
        this.x = x; this.y = y; this.kind = kind || 'crate';
        this.alive = true;
        this.max_hp = this.kind === 'crate' ? 1.0 : 2.0;
        this.hp = this.max_hp;
        this.radius = 12.0;
        this.hit_flash = 0.0;
        this.shake = 0.0;
    }
    Prop.prototype.take_damage = function (dmg, game) {
        if (!this.alive) { return; }
        this.hp -= dmg;
        this.hit_flash = 0.14;
        this.shake = 3.0;
        if (this.hp <= 0) { this.alive = false; this._break(game); }
    };
    Prop.prototype._break = function (game) {
        var col = this.kind === 'crate' ? [168, 128, 74] : [150, 96, 84];
        Sfx.play('break');
        game.fx.burst(this.x, this.y, col, 16, 150, 0.5, 4, TAU, 0, 2.4, 210.0);
        game.fx.burst(this.x, this.y, [206, 178, 128], 6, 90, 0.35, 3, TAU, 0, 3.0);
        game.fx.ring(this.x, this.y, 4, 30, 0.26, [222, 202, 156], 2);
        game.fx.add_shake(1.6);
        var r = game.rng.random();
        if (r < 0.55) {
            var n = game.rng.randint(1, 3);
            for (var i = 0; i < n; i++) {
                var a = game.rng.uniform(0, TAU), d = game.rng.uniform(6, 20);
                game.pickups.push(new Pickup(this.x + Math.cos(a) * d,
                    this.y + Math.sin(a) * d, 'coin', 1));
            }
        } else if (r < 0.70) {
            game.pickups.push(new Pickup(this.x, this.y, 'energy', 18));
        } else if (r < 0.76) {
            game.pickups.push(new Pickup(this.x, this.y, 'heart', 2));
        }
    };
    Prop.prototype.update = function (game, dt) {
        this.hit_flash = Math.max(0.0, this.hit_flash - dt);
        if (this.shake > 0) { this.shake = Math.max(0.0, this.shake - 30.0 * dt); }
    };
    Prop.prototype.draw = function (cam, game) {
        if (!this.alive) { return; }
        var size = 26;
        var sx = this.shake ? Math.sin(this.shake * 3.4) * (this.shake / 3.0) * 1.6 : 0.0;
        var x = this.x + cam[0] + sx, y = this.y + cam[1];
        drawShadow(x, y + 9, 12, 6, 130);
        blit(this.kind, x, y, size, size);
        if (this.hit_flash > 0) {
            blitTintAdd(this.kind, x, y, size, size, (this.hit_flash / 0.14) * 0.6, false);
            if (game) { /* 与 pygame 版一致：叠加白色高光 */ }
        }
    };

    // ==================================================================== 场景交互物
    // 需求 3：陷阱 / 掩体 / 奖励洞穴（与 Python hazard.py 逐条对齐）
    var TRAP_SPEC = {
        spike: { name: '地刺', color: [196, 196, 210], dmg: 3,
            period: 1.6, active: 0.7, radius: 13, w: 34 },
        poison: { name: '毒池', color: [128, 214, 96], dmg: 1.4,
            period: 0.55, active: 0.5, radius: 17, w: 26, slow: 0.55 },
        shock: { name: '电场', color: [120, 200, 255], dmg: 2.4,
            period: 2.1, active: 0.45, radius: 16, w: 16 },
        slow: { name: '泥沼', color: [140, 122, 88], dmg: 0.0,
            period: 99.0, active: 99.0, radius: 18, w: 18, slow: 0.48 },
        flame: { name: '喷焰口', color: [255, 146, 66], dmg: 3.6,
            period: 2.4, active: 0.9, radius: 14, w: 12 }
    };

    function SpeedStrip(x, y) { this.x = x; this.y = y; }
    SpeedStrip.prototype.contains = function (x, y) {
        return Math.abs(x - this.x) <= 22 && Math.abs(y - this.y) <= 15;
    };
    SpeedStrip.prototype.draw = function (cam) {
        var x = this.x + cam[0], y = this.y + cam[1];
        var color = this.color;
        fillRect([23, 29, 33], x - 24, y - 17, 48, 34);
        ctx.strokeStyle = cssColor(color); ctx.lineWidth = 2;
        ctx.strokeRect(x - 24, y - 17, 48, 34);
        for (var offset = -12; offset <= 12; offset += 12) {
            var dir = this.speed_mul > 1 ? 1 : -1;
            ctx.beginPath(); ctx.moveTo(x + offset - 4 * dir, y - 7);
            ctx.lineTo(x + offset + 4 * dir, y);
            ctx.lineTo(x + offset - 4 * dir, y + 7); ctx.stroke();
        }
    };
    function SpeedUpStrip(x, y) { SpeedStrip.call(this, x, y); }
    SpeedUpStrip.prototype = Object.create(SpeedStrip.prototype);
    SpeedUpStrip.prototype.speed_mul = 1.5;
    SpeedUpStrip.prototype.color = [80, 230, 165];
    function SlowDownStrip(x, y) { SpeedStrip.call(this, x, y); }
    SlowDownStrip.prototype = Object.create(SpeedStrip.prototype);
    SlowDownStrip.prototype.speed_mul = 0.55;
    SlowDownStrip.prototype.color = [245, 170, 75];

    function planSpeedStrips(rng, hazards) {
        var out = [], occupied = (hazards.traps || []).map(function (v) { return [v[1], v[2]]; });
        (hazards.covers || []).forEach(function (v) { occupied.push([v[1], v[2]]); });
        (hazards.caves || []).forEach(function (v) { occupied.push([v[1], v[2]]); });
        ['up', 'down'].forEach(function (kind) {
            for (var i = 0; i < 30; i++) {
                var x = rng.uniform(IN_L + 50, IN_R - 50);
                var y = rng.uniform(IN_T + 50, IN_B - 50);
                if (dist(x, y, ROOM_CX, ROOM_CY) < 72) { continue; }
                if (Object.keys(ENTRY_FROM).some(function (key) {
                    return dist(x, y, ENTRY_FROM[key][0], ENTRY_FROM[key][1]) < 72;
                })) { continue; }
                if (occupied.some(function (p) { return dist(x, y, p[0], p[1]) < 65; })) { continue; }
                occupied.push([x, y]); out.push([kind, x, y]); break;
            }
        });
        return out;
    }

    function Trap(x, y, kind, phase) {
        this.x = x; this.y = y;
        this.kind = kind || 'spike';
        this.spec = TRAP_SPEC[this.kind] || TRAP_SPEC.spike;
        this.radius = this.spec.radius;
        this.phase = phase || 0.0;
        this.t = phase || 0.0;
        this.alive = true;
        this._was_hit = false;
        this.flash = 0.0;
    }
    Trap.prototype.isActive = function () {
        var p = this.spec.period;
        if (p <= 0) { return true; }
        var c = this.t % p;
        if (c > this.spec.active) { return false; }
        if (c < this.spec.active * 0.22) { return false; }   // 预警窗口
        return true;
    };
    Trap.prototype.isWarning = function () {
        var p = this.spec.period;
        if (p <= 0) { return false; }
        var c = this.t % p;
        return c > 0 && c <= this.spec.active * 0.22;
    };
    Trap.prototype.update = function (game, dt) {
        this.t += dt;
        if (this.flash > 0) { this.flash = Math.max(0.0, this.flash - dt * 3.0); }
        var pl = game.player;
        if (game.run_stats && (game.run_stats.flags || []).indexOf('trap_ward') >= 0) {
            this._was_hit = false;
            return;
        }
        if (!pl.alive || pl.iframes > 0) { this._was_hit = false; return; }
        var d = dist(this.x, this.y, pl.x, pl.y);
        if (d > this.radius + pl.radius) { this._was_hit = false; return; }
        if (this.isActive()) {
            if (this.kind === 'slow') { pl.slow_until = 0.12; return; }
            if (!this._was_hit) {
                this._was_hit = true;
                this.flash = 1.0;
                pl.take_damage(this.spec.dmg, game, this.x, this.y);
                game.on_trap_hit(this);   // 需求：副本准入条件追踪
                var k = 130.0, a = Math.atan2(pl.y - this.y, pl.x - this.x);
                pl.x += Math.cos(a) * k * 0.06;
                pl.y += Math.sin(a) * k * 0.06;
            }
        } else {
            this._was_hit = false;
            if (this.kind === 'slow') { pl.slow_until = 0.12; }
        }
    };
    Trap.prototype.drawUnder = function (cam) {
        var x = this.x + cam[0], y = this.y + cam[1], r = Math.round(this.radius);
        var on = this.isActive(), warn = this.isWarning(), col = this.spec.color;
        blit('trap_' + this.kind, x, y, 32, 32);
        if (this.kind === 'poison' || this.kind === 'slow') {
            var a = on ? 96 : 60;
            for (var i = 0; i < 3; i++) {
                var rr = r * (0.7 + 0.12 * i), al = a * (1 - i * 0.22);
                ctx.beginPath();
                ctx.arc(Math.round(x), Math.round(y), rr, 0, TAU);
                ctx.fillStyle = cssColor(col, al / 255);
                ctx.fill();
            }
            if (warn) {
                ctx.beginPath();
                ctx.arc(Math.round(x), Math.round(y), r + 3, 0, TAU);
                ctx.lineWidth = 2;
                ctx.strokeStyle = 'rgba(255,240,180,0.275)';
                ctx.stroke();
            }
            return;
        }
        ctx.beginPath();
        ctx.arc(Math.round(x), Math.round(y), r, 0, TAU);
        ctx.fillStyle = 'rgba(24,22,30,0.588)';
        ctx.fill();
        ctx.lineWidth = 2;
        ctx.strokeStyle = 'rgba(60,56,74,0.784)';
        ctx.stroke();
    };
    Trap.prototype.drawOver = function (cam) {
        var x = this.x + cam[0], y = this.y + cam[1], r = Math.round(this.radius);
        var on = this.isActive(), warn = this.isWarning(), col = this.spec.color;
        var i, a, px, py;

        if (this.kind === 'spike') {
            var n = 5, up = on ? 8 : 2;
            for (i = 0; i < n; i++) {
                a = TAU * i / n + this.t * 0.4;
                px = x + Math.cos(a) * r * 0.62;
                py = y + Math.sin(a) * r * 0.62;
                ctx.beginPath();
                ctx.moveTo(px - 3, py + (on ? up : 3));
                ctx.lineTo(px + 3, py + (on ? up : 3));
                ctx.lineTo(px, py - 5 - (on ? up : 3));
                ctx.closePath();
                ctx.fillStyle = cssColor(on ? col : [110, 108, 120]);
                ctx.fill();
            }
        } else if (this.kind === 'shock') {
            if (on) {
                for (i = 0; i < 4; i++) {
                    a = this.t * 3.0 + i * 1.57;
                    ctx.beginPath();
                    ctx.moveTo(x, y);
                    ctx.lineTo(x + Math.cos(a) * r * 0.7, y + Math.sin(a) * r * 0.7);
                    ctx.lineWidth = 2;
                    ctx.strokeStyle = 'rgba(200,240,255,0.824)';
                    ctx.stroke();
                }
                ctx.beginPath();
                ctx.arc(x, y, Math.round(r * 0.55), 0, TAU);
                ctx.fillStyle = 'rgba(170,220,255,0.588)';
                ctx.fill();
            }
        } else if (this.kind === 'flame') {
            if (on) {
                var tt = (this.t % this.spec.period) / this.spec.active;
                var hh = r * (1.2 + 1.1 * Math.min(1.0, tt));
                for (i = 0; i < 3; i++) {
                    var rr2 = r * (0.85 - i * 0.2), al2 = 180 - i * 50;
                    ctx.beginPath();
                    ctx.ellipse(x, y + r - hh / 2, rr2, hh / 2, 0, 0, TAU);
                    ctx.fillStyle = cssColor([255, 150 + i * 30, 60], al2 / 255);
                    ctx.fill();
                }
            }
        }
        if (warn && this.kind !== 'spike') {
            ctx.beginPath();
            ctx.arc(x, y, r + 2, 0, TAU);
            ctx.lineWidth = 2;
            ctx.strokeStyle = 'rgba(255,236,170,0.353)';
            ctx.stroke();
        }
    };

    // ---- 掩体：实心，挡人挡子弹，爆炸可摧毁
    function Cover(x, y, kind, hp) {
        this.x = x; this.y = y; this.kind = kind || 'pillar';
        this.alive = true;
        this.max_hp = hp === undefined ? 6.0 : hp;
        this.hp = this.max_hp;
        this.radius = 15.0;
        this.hit_flash = 0.0;
        this.shake = 0.0;
    }
    Cover.prototype.take_damage = function (dmg, game) {
        if (!this.alive) { return; }
        this.hp -= dmg;
        this.hit_flash = 0.12;
        this.shake = 3.2;
        game.fx.burst(this.x, this.y, [168, 164, 150], 5, 70, 0.28, 3, TAU, 0, 3.0);
        if (this.hp <= 0) { this.alive = false; this._break(game); }
    };
    Cover.prototype._break = function (game) {
        Sfx.play('break');
        game.fx.burst(this.x, this.y, [150, 146, 138], 22, 170, 0.55, 5, TAU, 0, 2.2, 230.0);
        game.fx.ring(this.x, this.y, 6, 40, 0.3, [198, 194, 182], 3);
        game.fx.add_shake(3.4);
    };
    Cover.prototype.update = function (game, dt) {
        this.hit_flash = Math.max(0.0, this.hit_flash - dt);
        if (this.shake > 0) { this.shake = Math.max(0.0, this.shake - 26.0 * dt); }
    };
    Cover.prototype.draw = function (cam) {
        if (!this.alive) { return; }
        var size = 34;
        var sx = this.shake ? Math.sin(this.shake * 3.6) * (this.shake / 3.2) * 1.8 : 0.0;
        var x = this.x + cam[0] + sx, y = this.y + cam[1];
        drawShadow(x, y + 12, 15, 7, 150);
        var key = this.kind === 'pillar' ? 'cover_pillar' : 'cover_block';
        blit(key, x, y, size, size);
        if (this.hit_flash > 0) {
            blitTintAdd(key, x, y, size, size, (this.hit_flash / 0.12) * 0.63, false);
        }
        if (this.hp < this.max_hp - 0.01) {
            var w = 22, rr = Math.max(0.0, this.hp / this.max_hp);
            ctx.fillStyle = 'rgb(40,38,50)';
            ctx.fillRect(Math.round(x - w / 2), Math.round(y - size / 2 - 6), w, 3);
            ctx.fillStyle = 'rgb(200,190,150)';
            ctx.fillRect(Math.round(x - w / 2), Math.round(y - size / 2 - 6),
                Math.round(w * rr), 3);
        }
    };

    // ---- 奖励洞穴
    function Cave(x, y, loot_kind) {
        this.x = x; this.y = y;
        this.loot_kind = loot_kind || 'coin';
        this.alive = true;
        this.opened = false;
        this.t = 0.0;
        this.radius = 20.0;
    }
    Cave.prototype.update = function (game, dt) {
        this.t += dt;
        if (this.opened || !this.alive) { return; }
        var pl = game.player;
        if (!pl.alive) { return; }
        if (dist(this.x, this.y, pl.x, pl.y) < this.radius + pl.radius) {
            this.opened = true;
            this.alive = false;
            this._pop(game);
        }
    };
    Cave.prototype._pop = function (game) {
        var k = this.loot_kind, rng = game.rng, i, a, d;
        if (k === 'coin') {
            var n = rng.randint(3, 6);
            for (i = 0; i < n; i++) {
                a = rng.uniform(0, TAU); d = rng.uniform(8, 30);
                game.pickups.push(new Pickup(this.x + Math.cos(a) * d,
                    this.y + Math.sin(a) * d, 'coin', 1));
            }
        } else if (k === 'material') {
            var pool = ['scrap', 'fiber', 'circuit', 'crystal'];
            game.grant_material(rng.choice(pool), rng.randint(1, 2));
        } else if (k === 'heal') {
            game.pickups.push(new Pickup(this.x, this.y, 'heart', 3));
            game.pickups.push(new Pickup(this.x + 18, this.y, 'energy', 40));
        }
        Sfx.play('level_up');
        game.fx.ring(this.x, this.y, 6, 46, 0.4, [255, 226, 150], 3);
        game.fx.burst(this.x, this.y, [255, 220, 140], 18, 140, 0.5, 4, TAU, 0, 2.6);
        game.toast('发现奖励洞穴', '拿到了藏在这里的东西', [255, 226, 150]);
    };
    Cave.prototype.draw = function (cam) {
        if (!this.alive) { return; }
        var x = this.x + cam[0], y = this.y + cam[1], r = Math.round(this.radius);
        ctx.beginPath();
        ctx.arc(x, y, r, 0, TAU);
        ctx.fillStyle = 'rgba(18,16,24,0.824)';
        ctx.fill();
        ctx.lineWidth = 2;
        ctx.strokeStyle = 'rgba(196,168,110,0.745)';
        ctx.stroke();
        var pulse = 0.5 + 0.5 * Math.sin(this.t * 3.0);
        ctx.beginPath();
        ctx.arc(x, y, Math.round(r * 0.5), 0, TAU);
        ctx.fillStyle = cssColor([255, 226, 150], (60 + 70 * pulse) / 255);
        ctx.fill();
    };

    function inTrap(x, y, traps) {
        for (var i = 0; i < traps.length; i++) {
            if (dist(x, y, traps[i].x, traps[i].y) < traps[i].radius + 8) {
                return true;
            }
        }
        return false;
    }

    // 为某场景的一关规划场景交互物（对应 hazard.plan_scene）
    var TRAP_BY_SCENE = {
        crust: ['spike', 'flame'], sewer: ['poison', 'slow'],
        facility: ['shock', 'spike'], core: ['shock', 'flame'],
        d_mine: ['spike', 'slow'], d_lab: ['shock', 'poison'], d_gift: ['slow']
    };
    var SCENE_KEYS = ['crust', 'sewer', 'facility', 'core',
                      'd_mine', 'd_lab', 'd_gift'];
    function planScene(rng, sceneKey, stageIdx, diff) {
        var qmul = diff[0], smul = diff[1];
        var out = { traps: [], covers: [], caves: [] };
        var pool = TRAP_BY_SCENE[sceneKey] || ['spike'];
        var nTrap = sceneKey === 'd_gift' ? 0
            : Math.round(rng.randint(1, 3) * qmul);
        var nCover = Math.round(rng.randint(1, 3) * qmul);
        var nCave = rng.random() < (sceneKey !== 'd_gift' ? 0.34 : 0.85) ? 1 : 0;

        var avoid = [], kk;
        for (kk in ENTRY_FROM) {
            if (ENTRY_FROM.hasOwnProperty(kk)) {
                avoid.push([ENTRY_FROM[kk][0], ENTRY_FROM[kk][1], 84.0]);
            }
        }
        avoid.push([ROOM_CX, ROOM_CY, 52.0]);
        var occupied = [];

        function sample(minD) {
            for (var t = 0; t < 50; t++) {
                var x = rng.uniform(IN_L + 34, IN_R - 34);
                var y = rng.uniform(IN_T + 34, IN_B - 34);
                var bad = false, i;
                for (i = 0; i < occupied.length; i++) {
                    if (dist(x, y, occupied[i][0], occupied[i][1]) < minD) { bad = true; break; }
                }
                if (bad) { continue; }
                for (i = 0; i < avoid.length; i++) {
                    if (dist(x, y, avoid[i][0], avoid[i][1]) < avoid[i][2]) { bad = true; break; }
                }
                if (bad) { continue; }
                return [x, y];
            }
            return null;
        }

        var i, p;
        for (i = 0; i < nTrap; i++) {
            p = sample(44.0);
            if (!p) { break; }
            occupied.push(p);
            out.traps.push([rng.choice(pool), p[0], p[1], rng.uniform(0.0, 1.4)]);
        }
        for (i = 0; i < nCover; i++) {
            p = sample(50.0);
            if (!p) { break; }
            occupied.push(p);
            out.covers.push([rng.random() < 0.6 ? 'pillar' : 'block',
                p[0], p[1], 6.0 * smul]);
        }
        if (nCave) {
            p = sample(52.0);
            if (p) {
                occupied.push(p);
                out.caves.push([rng.choice(['coin', 'coin', 'material', 'heal']),
                    p[0], p[1]]);
            }
        }
        return out;
    }

    // ==================================================================== 玩家
    function Player(x, y) {
        this.x = x; this.y = y;
        this.radius = P_RADIUS;
        this.max_hp = P_MAX_HP;
        this.hp = P_MAX_HP;
        this.max_energy = P_MAX_ENERGY;
        this.energy = P_MAX_ENERGY;
        this.alive = true;
        this.wkey = 'pistol';
        this.wqual = 'white';
        this.wkey2 = null;
        this.wqual2 = 'white';
        this.cool = 0.0;
        this.cool2 = 0.0;
        this.iframes = 0.0;
        this.dash_t = 0.0;
        this.dash_cd = 0.0;
        this.dash_dx = 0.0; this.dash_dy = 0.0;
        this.aim = 0.0;
        this.walk = 0.0;
        this.recoil = 0.0;
        this.muzzle = 0.0;
        this.hit_flash = 0.0;
        this.moving = false;
        this.shots = 0;
        this.hit_taken = 0;
        this.dmg_taken = 0.0;
        // 需求 20：受击击退状态
        this.knock_t = 0.0;
        this.knock_dx = 0.0;
        this.knock_dy = 0.0;
        this.shield_charges = 0;
    }
    Player.prototype.spec = function () { return wget(this.wkey); };
    Player.prototype.switchWeapon = function () {
        if (!this.wkey2) { return false; }
        var key = this.wkey, quality = this.wqual, oldCool = this.cool || 0.0;
        this.wkey = this.wkey2; this.wqual = this.wqual2;
        this.wkey2 = key; this.wqual2 = quality;
        this.cool = Math.max(this.cool2 || 0.0, 0.12);
        this.cool2 = oldCool;
        return true;
    };
    Player.prototype.heal = function (n) { this.hp = Math.min(this.max_hp, this.hp + n); };
    // 需求 20：按伤害来源把玩家推开（与 Python apply_knockback 同源）
    Player.prototype.applyKnockback = function (game, sx, sy, dmg) {
        var ux, uy;
        if (sx === undefined || sx === null || sy === undefined || sy === null) {
            var a0 = this.aim + Math.PI;
            ux = Math.cos(a0); uy = Math.sin(a0);
        } else {
            var d = Math.sqrt((this.x - sx) * (this.x - sx) +
                              (this.y - sy) * (this.y - sy));
            if (d < 1e-3) {
                var a1 = this.aim + Math.PI;
                ux = Math.cos(a1); uy = Math.sin(a1);
            } else {
                ux = (this.x - sx) / d; uy = (this.y - sy) / d;
            }
        }
        var strength = Math.min(P_KNOCK_MAX,
                                P_KNOCK_BASE + (parseFloat(dmg) || 0) * P_KNOCK_PER_DMG);
        this.knock_t = P_KNOCK_TIME;
        this.knock_dx = ux * strength;
        this.knock_dy = uy * strength;
    };
    // 需求 5：当前武器在本存档里的强化等级（与 Python 端 Player.wlevel 同源）
    Player.prototype.wlevel = function (game) {
        var prof = game && game.profile;
        if (!prof) { return 0; }
        return Math.max(Math.trunc((prof.weapon_quality_levels || {})[this.wkey] || 0),
                        Math.trunc((prof.weapons || {})[this.wkey] || 0));
    };
    // 需求 6：武器成长后的品质（白 -> 绿 -> 蓝，封顶蓝色）
    Player.prototype.wq = function (game) {
        return (D.WEAPON_QUALITY || {})[this.wkey] || 'white';
    };
    // 需求 5：武器强化带来的伤害倍率（品质 mul × 每级 +6%）
    Player.prototype.wmul = function (game) {
        var lv = this.wlevel(game);
        var qs = D.QUALITIES || {};
        var qk = this.wq(game);
        var q = qs[qk] || qs.white || {};
        var base = parseFloat(q.mul);
        if (isNaN(base)) { base = 1.0; }
        var perk = (D.QUALITY_ORDER || []).indexOf(qk) > 2 &&
            lv >= (q.max_lv || 99) ? 1.15 : 1.0;
        return base * (1.0 + 0.10 * lv) * perk;
    };
    // 需求 6（1.4）：当前武器叠上品质机制后的实际规格（伤害倍率由 wmul 统一计算，不重复相乘）
    Player.prototype.wqSpec = function (game) {
        var q = this.wq(game);
        var s = D.applyQuality(this.wkey, q, 1.0) || wget(this.wkey);
        if (q === 'blue' || q === 'radiant') {
            var qObj = (D.QUALITIES || {})[q] || {};
            if (this.wlevel(game) >= (qObj.max_lv || 99)) {
                var copy = {};
                for (var sk in s) {
                    if (Object.prototype.hasOwnProperty.call(s, sk)) { copy[sk] = s[sk]; }
                }
                copy.speed = (copy.speed || 0) * 1.15;
                return copy;
            }
        }
        return s;
    };

    Player.prototype.update = function (game, dt, inp) {
        if (!this.alive) { return; }
        this.cool = Math.max(0.0, this.cool - dt);
        this.cool2 = Math.max(0.0, this.cool2 - dt);
        this.dash_cd = Math.max(0.0, this.dash_cd - dt);
        this.iframes = Math.max(0.0, this.iframes - dt);
        this.recoil = Math.max(0.0, this.recoil - dt * 6.0);
        this.muzzle = Math.max(0.0, this.muzzle - dt);
        this.hit_flash = Math.max(0.0, this.hit_flash - dt);
        this.knock_t = Math.max(0.0, this.knock_t - dt);

        if (inp.aim !== undefined) { this.aim = inp.aim; }
        var spec = this.spec();
        var hpRegen = (game && game.run_stats) ? (game.run_stats.hp_regen || 0.0) : 0.0;
        var regenRate = (game && game.char_regen_rate) ? game.char_regen_rate : 0.0;
        if (regenRate > 0 && game && game.room) {
            var anyAlive = false;
            if (!game.room.cleared && game.enemies) {
                for (var ri = 0; ri < game.enemies.length; ri++) {
                    if (game.enemies[ri].alive) { anyAlive = true; break; }
                }
            }
            if (game.room.cleared || !anyAlive) { hpRegen += regenRate; }
        }
        if (hpRegen > 0 && this.hp < this.max_hp) {
            this.hp = Math.min(this.max_hp, this.hp + hpRegen * dt);
        }

        // ---- 冲刺
        if (inp.dash && this.dash_t <= 0 && this.dash_cd <= 0) {
            var mx = inp.mx || 0.0, my = inp.my || 0.0;
            if (mx || my) {
                var l = Math.hypot(mx, my);
                this.dash_dx = mx / l; this.dash_dy = my / l;
            } else {
                this.dash_dx = Math.cos(this.aim); this.dash_dy = Math.sin(this.aim);
            }
            this.dash_t = P_DASH_TIME;
            this.phase_origin = [this.x, this.y];
            var charKey = (game.profile && game.profile.char) || game.char_key || 'scout';
            var dashMul = (game && game.run_stats) ? (game.run_stats.dash_cd_mul || 0.0) : 0.0;
            this.dash_cd = P_DASH_CD * (charKey === 'ghost' ? 0.75 : 1.0) * Math.max(0.25, 1.0 + dashMul);
            this.iframes = Math.max(this.iframes, P_DASH_TIME + 0.12);
            Sfx.play('dash');
            game.fx.burst(this.x, this.y, [170, 230, 255], 10, 110, 0.3, 3, TAU, 0, 3.0, 0, 'circle');
        }

        var sol = game.room.solid;
        var blk = game.room.blockers();
        var phaseStep = game.run_stats && (game.run_stats.flags || []).indexOf('phase_step') >= 0;
        var phaseActive = phaseStep && this.dash_t > 0;
        var dx, dy;

        if (this.dash_t > 0) {
            this.dash_t -= dt;
            dx = this.dash_dx * P_DASH_SPEED * dt;
            dy = this.dash_dy * P_DASH_SPEED * dt;
            this.moving = true;
            if (game.rng.random() < 0.75) {
                game.fx.burst(this.x, this.y, [140, 200, 240], 1, 14, 0.24, 3, TAU, 0, 3.0, 0, 'circle');
            }
        } else {
            var mmx = inp.mx || 0.0, mmy = inp.my || 0.0;
            var ll = Math.hypot(mmx, mmy);
            if (ll > 1.0) { mmx = mmx / ll; mmy = mmy / ll; }
            // 需求：污染渐近减益——移速随污染浓度下降
            var ps = game.pollution_spd === undefined ? 1.0 : game.pollution_spd;
            // 1.1 天赋：移速加成
            if (game.run_stats) { ps *= (1.0 + (game.run_stats.speed_mul || 0.0)); }
            // 需求 6：角色基础速度（由 game._applyLoadout 写入）
            ps *= (game.char_spd_mul === undefined || game.char_spd_mul === null)
                ? 1.0 : game.char_spd_mul;
            var stripMul = 1.0;
            var strips = game.room.speed_strips || [];
            for (var si = 0; si < strips.length; si++) {
                if (strips[si].contains(this.x, this.y)) { stripMul = strips[si].speed_mul; break; }
            }
            var ds = P_SPEED * ps * stripMul * (inp.slow ? 0.72 : 1.0);
            dx = mmx * ds * dt; dy = mmy * ds * dt;
            this.moving = ll > 0.01;
        }

        // 后坐力位移
        dx += Math.cos(this.aim + Math.PI) * this.recoil * dt * 5.0;
        dy += Math.sin(this.aim + Math.PI) * this.recoil * dt * 5.0;

        // 需求 20：受击击退位移（指数衰减，比常规移动更"硬"）
        if (this.knock_t > 0) {
            var kk = this.knock_t / Math.max(1e-6, P_KNOCK_TIME);
            dx += this.knock_dx * kk * dt;
            dy += this.knock_dy * kk * dt;
        }

        var pos = moveCircle(this.x, this.y, this.radius, dx, dy,
            phaseActive ? null : sol, phaseActive ? [] : blk);
        this.x = clamp(pos[0], -4.0, ROOM_PX_W + 4.0);
        this.y = clamp(pos[1], -4.0, ROOM_PX_H + 4.0);
        if (phaseActive && this.dash_t <= 0 &&
                collideTest(this.x, this.y, this.radius, sol, blk)) {
            var landing = findFreeSpot(this.x, this.y, this.radius, sol, blk);
            if (landing) { this.x = landing[0]; this.y = landing[1]; }
            else if (this.phase_origin) {
                this.x = this.phase_origin[0]; this.y = this.phase_origin[1];
            }
        }

        if (this.moving) { this.walk += dt; }

        // ---- 能量恢复（需求：污染渐近减益——回能速率下降）
        var preg = game.pollution_regen === undefined ? 1.0 : game.pollution_regen;
        // Energy is restored by pickups only.

        // ---- 射击
        if (inp.shoot && this.cool <= 0) {
            if (this.energy > 0 && this.energy + 1e-6 >= spec.cost) {
                this.fire(game, spec);
            } else {
                var fists = { key: 'fists', dmg: 2, cd: 0.65, cost: 0,
                    melee: true, reach: 82, arc: 105, color: [190, 195, 205], vfx: 'spark' };
                meleeSwing(game, fists, this.x, this.y, this.aim, 1 + this.dmgBonus(game));
                weaponFlash(game, fists, this.x, this.y, this.aim, true);
                Sfx.play('shoot_heavy');
                this.cool = fists.cd / this.attackSpeedMul(game, false);
            }
        }
    };

    Player.prototype.dmgBonus = function (game) {
        var b = (game && game.char_power_mul) ? game.char_power_mul : 0.0;
        if (game.run_stats) { b += (game.run_stats.dmg_mul || 0.0); }
        b += (game.purDmgMul ? game.purDmgMul() : 0.0);
        return b;
    };
    Player.prototype.attackSpeedMul = function (game, includeQuality) {
        var qk = this.wq(game);
        var base = (includeQuality !== false) ? Number((D.qualityMech(qk) || {}).rate || 1.0) : 1.0;
        if (includeQuality !== false && (qk === 'white' || qk === 'radiant')) {
            var qObj = (D.QUALITIES || {})[qk] || {};
            if (this.wlevel(game) >= (qObj.max_lv || 99)) { base += 0.08; }
        }
        var soda = Number((game && game.drink_buffs && game.drink_buffs.soda) || 0);
        var rateMul = Number((game && game.run_stats && game.run_stats.rate_mul) || 0);
        return Math.max(0.1, base + 0.12 * soda + rateMul);
    };
    Player.prototype.critChance = function (game) {
        var c = 0.08 + ((game && game.char_crit_bonus) ? game.char_crit_bonus : 0.0);
        if (game && game.run_stats) { c += (game.run_stats.crit || 0.0); }
        var wq = this.wq(game);
        if (wq === 'green' || wq === 'radiant') {
            var q = (D.QUALITIES || {})[wq];
            if (q && this.wlevel(game) >= (q.max_lv || 99)) { c += 0.06; }
        }
        return Math.min(0.65, c);
    };
    Player.prototype.fire = function (game, spec) {
        var qspec = this.wqSpec(game);      // 叠上品质机制后的规格
        this.cool = spec.cd / this.attackSpeedMul(game);
        this.energy = Math.max(0.0, this.energy - spec.cost);
        var a = this.aim;
        var dmul = (1.0 + this.dmgBonus(game)) * this.wmul(game);
        // 需求 6：近战 vs 远程
        if (qspec.melee) {
            var hits = meleeSwing(game, qspec, this.x, this.y, a, dmul);
            var mDouble = Number((D.qualityMech(this.wq(game)) || {}).melee_double || 0);
            if (mDouble > 0 && game.rng && game.rng.random() < mDouble) {
                hits += meleeSwing(game, qspec, this.x, this.y, a + 0.14, dmul);
                game.fx.text(this.x, this.y - 26, '连斩', [255, 226, 130], 10, 0.45);
            }
            if (hits > 0) { game.add_hitstop(HITSTOP_KILL); }
            Sfx.play('shoot_heavy');
            game.fx.add_shake(1.6);
            weaponFlash(game, qspec, this.x, this.y, a, true);
            this.shots++;
            return;
        }
        var mx = this.x + Math.cos(a) * 14.0;
        var my = this.y + Math.sin(a) * 14.0;
        fire(game, qspec, mx, my, a, true, dmul);
        this.shots++;
        this.muzzle = 0.07;
        this.recoil = Math.min(9.0, qspec.kick * 0.22);
        Sfx.play(qspec.sound);
        if (qspec.kick > 0) {
            this.x -= Math.cos(a) * qspec.kick * 0.012;
            this.y -= Math.sin(a) * qspec.kick * 0.012;
        }
        game.fx.add_shake(qspec.shake * 0.35);
        weaponFlash(game, qspec, mx, my, a, false);
    };

    Player.prototype.take_damage = function (dmg, game, sx, sy) {
        if (!this.alive || this.iframes > 0) { return false; }
        var guardMul = (game && game.char_guard_mul) ? game.char_guard_mul : 1.0;
        if ((this.shield_charges || 0) > 0) {
            this.shield_charges--;
            this.iframes = P_IFRAME * guardMul;
            Sfx.play('dash');
            game.fx.ring(this.x, this.y, 10, 36, 0.35, [120, 210, 255], 3);
            game.fx.text(this.x, this.y - 26, '护盾抵挡', [140, 220, 255], 12, 0.85);
            return false;
        }
        this.hit_taken++;
        this.dmg_taken += dmg;
        this.hp -= dmg;
        this.iframes = P_IFRAME * guardMul;
        this.hit_flash = 0.22;
        // 需求 20：受击击退 —— 从伤害来源方向被推开
        this.applyKnockback(game, sx, sy, dmg);
        Sfx.play('hurt');
        game.fx.add_shake(4.2);
        game.fx.add_flash(0.22, [255, 60, 70]);
        game.fx.blood(this.x, this.y, [226, 62, 74], 9, null);
        game.fx.text(this.x, this.y - 26, '-' + Math.round(dmg), C_HP, 13, 0.8);
        // 天赋「反伤甲」+ 局外被动「荆棘」：受击时向最近敌人反弹伤害
        var thornsRatio = ((game && game.run_stats && (game.run_stats.flags || []).indexOf('thorns') >= 0) ? 0.40 : 0.0) +
            ((game && game.char_thorns_ratio) ? game.char_thorns_ratio : 0.0);
        if (dmg > 0 && thornsRatio > 0 && game && game.enemies && game.enemies.length) {
            var ax = (sx !== undefined && sx !== null) ? sx : this.x;
            var ay = (sy !== undefined && sy !== null) ? sy : this.y;
            var bestE = null, bestD = 1e18;
            for (var ti = 0; ti < game.enemies.length; ti++) {
                var te = game.enemies[ti];
                if (!te.alive || te.invuln) { continue; }
                var td = (te.x - ax) * (te.x - ax) + (te.y - ay) * (te.y - ay);
                if (td < bestD) { bestD = td; bestE = te; }
            }
            if (bestE) {
                var reflected = Math.max(1.0, Math.round(dmg * thornsRatio * 100) / 100);
                bestE.take_damage(reflected, game);
            }
        }
        // 需求 20：受击硬直（hit-stop）+ 需求 11：手机震动
        game.add_hitstop(HITSTOP_HURT);
        vibrate(game, 28);
        if (this.hp <= 0) { this.hp = 0.0; this.die(game); }
        return true;
    };

    Player.prototype.die = function (game) {
        if (!this.alive) { return; }
        this.alive = false;
        Sfx.play('game_over');
        game.fx.burst(this.x, this.y, [226, 62, 74], 30, 190, 0.9, 5, TAU, 0, 1.8, 0, 'circle');
        game.fx.burst(this.x, this.y, [255, 220, 200], 16, 130, 0.6, 4, TAU, 0, 2.4);
        game.fx.ring(this.x, this.y, 6, 78, 0.6, [255, 120, 120], 3);
        game.fx.add_shake(11.0);
        game.fx.add_flash(0.4, [255, 40, 50]);
        game.onPlayerDied();
    };

    Player.prototype.draw = function (cam, game) {
        if (!this.alive) { return; }
        var x = this.x + cam[0], y = this.y + cam[1];
        // 无敌帧闪烁：半透明而非完全消失，避免玩家找不到自己
        var fade = (this.iframes > 0 && this.dash_t <= 0 &&
            Math.floor(this.iframes * 22) % 2 === 0);
        drawShadow(x, y + 12, 13, 6, 150);
        var bob = this.moving ? -Math.abs(Math.sin(this.walk * 11.0)) * 2.0 : 0.0;
        var size = 46;
        var flip = Math.cos(this.aim) < 0;
        var cy = y + bob - 4;
        var artKey = 'player_' + ((game.profile && game.profile.char) || 'scout');
        blit(IMG[artKey] ? artKey : 'player', x, cy, size, size,
            { flip: flip, alpha: fade ? 105 : 255 });
        // 枪口火焰
        if (this.muzzle > 0) {
            var t = this.muzzle / 0.07;
            var a = this.aim;
            var mx = x + Math.cos(a) * 20.0;
            var my = y + Math.sin(a) * 20.0 - 4;
            var r = 4 + 7 * t;
            ctx.beginPath();
            ctx.arc(Math.round(mx), Math.round(my), r, 0, TAU);
            ctx.fillStyle = cssColor([255, 236, 170], 0.82 * t);
            ctx.fill();
            ctx.beginPath();
            ctx.arc(Math.round(mx), Math.round(my), Math.max(1, r / 2), 0, TAU);
            ctx.fillStyle = cssColor([255, 255, 255], 0.9 * t);
            ctx.fill();
        }
        // 受伤闪白
        if (this.hit_flash > 0) {
            blitTintAdd(IMG[artKey] ? artKey : 'player', x, cy, size, size,
                (this.hit_flash / 0.22) * 0.62, flip);
        }
        // 瞄准指示
        if (game && game.show_aim) {
            var a2 = this.aim;
            var ex = x + Math.cos(a2) * 30.0;
            var ey = y + Math.sin(a2) * 30.0 - 4;
            ctx.fillStyle = 'rgba(255,255,255,0.28)';
            for (var k = 1; k <= 3; k++) {
                var tt = k / 4.0;
                ctx.fillRect(Math.round(lerp(x, ex, tt)) - 1,
                    Math.round(lerp(y - 4, ey, tt)) - 1, 2, 2);
            }
        }
        if ((this.shield_charges || 0) > 0) {
            ctx.beginPath();
            ctx.arc(Math.round(x), Math.round(y - 2), 20, 0, TAU);
            ctx.lineWidth = 2;
            ctx.strokeStyle = 'rgb(120,210,255)';
            ctx.stroke();
        }
    };

    // ==================================================================== 敌人
    function Enemy(x, y, floor, elite) {
        this.x = x; this.y = y;
        this.floor = floor;
        this.elite = !!elite;
        this.kind = 'enemy';
        this.spr_key = 'slime';
        this.spr_size = 40;
        this.radius = 13.0;
        this.body_color = [120, 220, 110];
        this.max_hp = 22.0;
        this.hp = this.max_hp;
        this.speed = 56.0;
        this.contact_dmg = 2.0;
        this.touch_cd = 0.0;
        this.alive = true;
        this.hit_flash = 0.0;
        this.kx = 0.0; this.ky = 0.0;
        this.t = 0.0;
        this.anim = 0.0;
        this.facing = 1;
        this.invuln = false;
        this.bullet_dmg = 2.0;
        this.dmg_mul = 1.0;
        this.slow_t = 0.0;
        this._slow_base_speed = null;
        this.dot_t = 0.0;
        this.dot_dps = 0.0;
        this.draw_off_y = 0.0;
        this.squash = 1.0;
        this.is_boss = false;
        if (this.elite) {
            this.max_hp = this.max_hp * 2.4 + 6;
            this.hp = this.max_hp;
            this.radius *= 1.18;
            this.spr_size = Math.floor(this.spr_size * 1.22);
        }
    }
    Enemy.prototype.hp_ratio = function () {
        return Math.max(0.0, Math.min(1.0, this.hp / Math.max(1e-6, this.max_hp)));
    };
    Enemy.prototype.applyDmgMul = function (mul) {
        mul = Number(mul || 1.0);
        if (Math.abs(mul - 1.0) <= 0.001) { return; }
        this.dmg_mul = mul;
        this.contact_dmg = Math.round(this.contact_dmg * mul * 100) / 100;
        this.bullet_dmg = Math.round(this.bullet_dmg * mul * 100) / 100;
        if (typeof this.explode_dmg === 'number') {
            this.explode_dmg = Math.round(this.explode_dmg * mul * 100) / 100;
        }
        if (typeof this.cloud_dmg === 'number') {
            this.cloud_dmg = Math.round(this.cloud_dmg * mul * 100) / 100;
        }
        if (typeof this.charge_dmg === 'number') {
            this.charge_dmg = Math.round(this.charge_dmg * mul * 100) / 100;
        }
    };
    Enemy.prototype.dist_to_player = function (game) {
        return dist(this.x, this.y, game.player.x, game.player.y);
    };
    Enemy.prototype._apply_knock = function (game, dt) {
        if (Math.abs(this.kx) > 1 || Math.abs(this.ky) > 1) {
            moveCircle(this.x, this.y, this.radius, this.kx * dt, this.ky * dt,
                game.room.solid);
        }
        var k = Math.max(0.0, 1.0 - 9.0 * dt);
        this.kx *= k; this.ky *= k;
    };
    Enemy.prototype._clamp_room = function (pad) {
        pad = pad === undefined ? 2.0 : pad;
        this.x = clamp(this.x, pad, ROOM_PX_W - pad);
        this.y = clamp(this.y, pad, ROOM_PX_H - pad);
    };
    Enemy.prototype._touch_player = function (game, dmg) {
        if (this.touch_cd > 0 || !this.alive) { return; }
        var pl = game.player;
        if (!pl.alive) { return; }
        var rr = this.radius + pl.radius;
        var dx = this.x - pl.x, dy = this.y - pl.y;
        if (dx * dx + dy * dy < rr * rr) {
            if (pl.take_damage(dmg, game)) {
                this.touch_cd = 0.6;
                var a = Math.atan2(pl.y - this.y, pl.x - this.x);
                pl.x += Math.cos(a) * 9.0;
                pl.y += Math.sin(a) * 9.0;
            }
        }
    };
    Enemy.prototype._shoot = function (game, ang, speed, dmg, img, size, spread, count, life) {
        if (!this.alive) { return 0; }
        var cnt = 0, i;
        for (i = 0; i < game.bullets.length; i++) {
            if (!game.bullets[i].friendly) { cnt++; }
        }
        if (cnt > 190) { return 0; }
        var made = 0;
        var n = Math.max(1, count || 1);
        for (i = 0; i < n; i++) {
            var a = n <= 1 ? ang : ang + ((i / (n - 1)) - 0.5) * spread;
            game.bullets.push(new Bullet(
                this.x + Math.cos(a) * (this.radius + 5),
                this.y + Math.sin(a) * (this.radius + 5),
                a, speed || 175.0, dmg || 2.0, false,
                img || 'b_hex', size || 14, Math.max(3.0, (size || 14) * 0.33),
                0, 0.0, life || 1.6, [196, 120, 240], 0.6));
            made++;
        }
        return made;
    };
    Enemy.prototype.take_damage = function (dmg, game, sx, sy) {
        if (!this.alive || this.invuln) { return; }
        dmg = Math.max(1.0, dmg);
        var fromPlayer = (sx !== undefined && sx !== null && game && game.player && game.rng);
        var isCrit = fromPlayer && (game.rng.random() < game.player.critChance(game));
        if (isCrit) { dmg *= 1.50; }
        if (this.is_boss) {
            dmg = Math.min(dmg, Math.max(1.0, this.max_hp * 0.15));
        } else if (this.elite) {
            dmg = Math.min(dmg, Math.max(1.0, this.max_hp * 0.75));
        }
        this.hp -= dmg;
        this.hit_flash = 0.13;
        if (sx !== undefined && sx !== null) {
            var a = Math.atan2(this.y - sy, this.x - sx);
            var f = Math.min(190.0, 40.0 + dmg * 3.4);
            if (!this.elite) {
                this.kx += Math.cos(a) * f; this.ky += Math.sin(a) * f;
            } else {
                this.kx += Math.cos(a) * f * 0.45; this.ky += Math.sin(a) * f * 0.45;
            }
        }
        game.fx.sparks(this.x, this.y, isCrit ? [255, 214, 96] : this.body_color,
            isCrit ? 8 : 5, Math.atan2(this.y - (sy || 0), this.x - (sx || 0)));
        if (isCrit) {
            game.fx.ring(this.x, this.y, 4, 22, 0.22, [255, 214, 96], 2);
            vibrate(game, 14);
        }
        var jx = (game && game.rng) ? game.rng.uniform(-7, 7) : 0;
        if (isCrit) {
            game.fx.text(this.x + jx, this.y - this.radius - 13,
                Math.round(dmg) + '!', [255, 224, 96], 15, 0.68);
        } else if (dmg >= 1) {
            game.fx.text(this.x + jx, this.y - this.radius - 10,
                String(Math.round(dmg)), [245, 240, 225], 11, 0.45);
        }
        if (this.hp <= 0) {
            // 需求 20：击杀的停顿比普通命中更重
            game.add_hitstop(HITSTOP_KILL);
            this.die(game);
        } else {
            // 需求 20：命中停顿 —— 让每一发都有"打得进去"的手感
            game.add_hitstop(HITSTOP_HIT);
            Sfx.play('hit');
        }
    };
    Enemy.prototype.die = function (game) {
        if (!this.alive) { return; }
        this.alive = false;
        Sfx.play('enemy_die');
        var col = this.body_color;
        game.fx.burst(this.x, this.y, col, 16, 165, 0.5, 4, TAU, 0, 2.2, 0, 'circle');
        game.fx.burst(this.x, this.y, [250, 245, 230], 7, 105, 0.32, 3, TAU, 0, 3.0);
        game.fx.ring(this.x, this.y, 4, 30, 0.3, col, 2);
        game.fx.add_shake(1.5);
        game.onEnemyKilled(this);
    };
    Enemy.prototype.draw = function (cam) {
        if (!this.alive) { return; }
        var x = this.x + cam[0], y = this.y + cam[1];
        var size = this.spr_size, off = this.draw_off_y || 0.0;
        drawShadow(x, y + size * 0.30, size * 0.31, size * 0.15, 140);
        if (this.elite) {
            ctx.beginPath();
            ctx.arc(Math.round(x), Math.round(y + off), (size + 12) / 2, 0, TAU);
            ctx.lineWidth = 3;
            ctx.strokeStyle = cssColor([255, 190, 70], 0.24);
            ctx.stroke();
        }
        var flip = this.facing < 0;
        var sq = this.squash === undefined ? 1.0 : this.squash;
        var dw = size, dh = size;
        var dy = y + off;
        if (Math.abs(sq - 1.0) > 0.01) {
            dh = Math.max(2, Math.floor(size * sq));
            dy = y + size * (1 - sq) * 0.4 + off;
        }
        if (this.tint && !this.is_boss) {
            // 需求 8：场景染色 —— 同一张贴图变出不同怪
            blitTint(this.spr_key, x, dy, dw, dh, this.tint, 0.66, { flip: flip });
        } else {
            blit(this.spr_key, x, dy, dw, dh, { flip: flip });
        }
        if (this.hit_flash > 0) {
            blitTintAdd(this.spr_key, x, dy, dw, dh, (this.hit_flash / 0.13) * 0.69, flip);
        }
        if (this.hp < this.max_hp - 0.01 && !this.is_boss) {
            var w = E_HP_BAR_W;
            var bx = Math.round(x - w / 2), by = Math.round(y - size * 0.52 - 8);
            fillRect([18, 16, 24], bx - 1, by - 1, w + 2, 5);
            fillRect([60, 40, 46], bx, by, w, 3);
            var fw = Math.floor(w * this.hp_ratio());
            if (fw > 0) { fillRect([226, 72, 84], bx, by, fw, 3); }
        }
    };
    Enemy.prototype.update = function (game, dt) {
        this.t += dt;
        if (this.slow_t > 0) {
            this.slow_t = Math.max(0, this.slow_t - dt);
            if (this.slow_t === 0 && this._slow_base_speed !== null) {
                this.speed = this._slow_base_speed;
                this._slow_base_speed = null;
            }
        }
        if (this.dot_t > 0 && this.alive && !this.invuln) {
            var tick = Math.min(dt, this.dot_t);
            this.dot_t = Math.max(0, this.dot_t - dt);
            this.hp -= this.dot_dps * tick;
            if (this.hp <= 0) { this.die(game); }
            if (this.dot_t === 0) { this.dot_dps = 0; }
        }
        this.touch_cd = Math.max(0.0, this.touch_cd - dt);
        this.hit_flash = Math.max(0.0, this.hit_flash - dt);
        this._apply_knock(game, dt);
    };

    // ---- 史莱姆
    function Slime(x, y, floor, elite) {
        Enemy.call(this, x, y, floor, elite);
        this.kind = 'slime'; this.spr_key = 'slime'; this.spr_size = 40;
        this.radius = 13.0; this.body_color = [124, 214, 106];
        this.max_hp = (21 + 8 * (floor - 1)) * (elite ? 2.4 : 1.0) * (1 + (elite ? 0.6 : 0));
        if (this.elite) { this.spr_size = Math.floor(40 * 1.22); this.radius = 13.0 * 1.18; }
        this.hp = this.max_hp;
        this.speed = 58.0 + 7.0 * (floor - 1);
        this.contact_dmg = 2.0;
        this.hop = 0.0;
        this.squash = 1.0;
        this.draw_off_y = 0.0;
    }
    Slime.prototype = Object.create(Enemy.prototype);
    Slime.prototype.constructor = Slime;
    Slime.prototype.update = function (game, dt) {
        Enemy.prototype.update.call(this, game, dt);
        var pl = game.player;
        this.facing = pl.x < this.x ? -1 : 1;
        this.anim += dt;
        this.hop = (this.hop + dt) % 0.95;
        var mv;
        if (this.hop < 0.5) {
            var k = this.hop / 0.5;
            this.squash = 1.0 - 0.16 * Math.sin(k * Math.PI);
            this.draw_off_y = 0.0;
            mv = 0.0;
        } else {
            var k2 = (this.hop - 0.5) / 0.45;
            this.squash = 1.0 + 0.14 * Math.sin(k2 * Math.PI);
            this.draw_off_y = -Math.sin(k2 * Math.PI) * 11.0;
            mv = this.speed * 2.35;
        }
        if (mv > 0) {
            var a = Math.atan2(pl.y - this.y, pl.x - this.x);
            var p = moveCircle(this.x, this.y, this.radius,
                Math.cos(a) * mv * dt, Math.sin(a) * mv * dt, game.room.solid);
            this.x = p[0]; this.y = p[1];
        }
        this._clamp_room();
        this._touch_player(game, this.contact_dmg);
    };

    // ---- 炸弹机器人
    function Bomber(x, y, floor, elite) {
        Enemy.call(this, x, y, floor, elite);
        this.kind = 'bomber'; this.spr_key = 'bomber'; this.spr_size = 40;
        this.radius = 12.0; this.body_color = [198, 92, 64];
        this.max_hp = (30 + 10 * (floor - 1)) * (elite ? 2.4 : 1.0);
        if (this.elite) { this.spr_size = Math.floor(40 * 1.22); this.radius = 12.0 * 1.18; }
        this.hp = this.max_hp;
        this.speed = 76.0 + 9.0 * (floor - 1);
        this.contact_dmg = 0.0;
        this.fuse = -1.0;
        this.boom_done = false;
        this.explode_r = 60.0 + 6.0 * (floor - 1);
        this.explode_dmg = 6.0 + 1.5 * (floor - 1);
        this.squash = 1.0;
    }
    Bomber.prototype = Object.create(Enemy.prototype);
    Bomber.prototype.constructor = Bomber;
    Bomber.prototype.update = function (game, dt) {
        Enemy.prototype.update.call(this, game, dt);
        var pl = game.player;
        if (!pl.alive) { return; }
        this.facing = pl.x < this.x ? -1 : 1;
        var d = this.dist_to_player(game);
        if (this.fuse >= 0) {
            this.fuse -= dt;
            this.squash = 1.0 + 0.2 * Math.abs(Math.sin(this.t * 26.0));
            if (this.fuse <= 0) { this._detonate(game, this.explode_r, this.explode_dmg); }
            return;
        }
        if (d < 48.0) {
            this.fuse = 0.85;
            Sfx.play('lock');
            game.fx.ring(this.x, this.y, 8, 34, 0.4, [255, 120, 80], 2);
            return;
        }
        var a = Math.atan2(pl.y - this.y, pl.x - this.x) + Math.sin(this.t * 7.0) * 0.35;
        var p = moveCircle(this.x, this.y, this.radius,
            Math.cos(a) * this.speed * dt, Math.sin(a) * this.speed * dt, game.room.solid);
        this.x = p[0]; this.y = p[1];
        this._clamp_room();
        if (this.t % 0.16 < dt) {
            game.fx.burst(this.x, this.y, [90, 88, 96], 1, 12, 0.3, 3, TAU, 0, 2.0, 0, 'circle');
        }
    };
    Bomber.prototype._detonate = function (game, radius, dmg) {
        if (this.boom_done) { return; }
        this.boom_done = true;
        this.alive = false;
        explode(game, this.x, this.y, radius, dmg, true, [255, 150, 70], true);
        game.onEnemyKilled(this);
    };
    Bomber.prototype.die = function (game) {
        if (!this.alive) { return; }
        if (!this.boom_done) {
            this.boom_done = true;
            this.alive = false;
            explode(game, this.x, this.y, this.explode_r * 0.78,
                this.explode_dmg * 0.55, true, [255, 150, 70], true);
            game.onEnemyKilled(this);
            return;
        }
        Enemy.prototype.die.call(this, game);
    };

    // ---- 无人机
    function Drone(x, y, floor, elite) {
        Enemy.call(this, x, y, floor, elite);
        this.kind = 'drone'; this.spr_key = 'drone'; this.spr_size = 40;
        this.radius = 13.0; this.body_color = [168, 124, 224];
        this.max_hp = (33 + 11 * (floor - 1)) * (elite ? 2.4 : 1.0);
        if (this.elite) { this.spr_size = Math.floor(40 * 1.22); this.radius = 13.0 * 1.18; }
        this.hp = this.max_hp;
        this.speed = 66.0 + 7.0 * (floor - 1);
        this.contact_dmg = 1.0;
        this.shoot_cd = 0.9 + (x * 0.013) % 0.8;
        this.strafe = (Math.floor(x + y) % 2 === 0) ? 1.0 : -1.0;
        this.prefer = 132.0;
        this.volley = 1 + Math.min(2, floor - 1);
        this.draw_off_y = -8.0;
        this.burst_left = 0;
        this.burst_t = 0.0;
    }
    Drone.prototype = Object.create(Enemy.prototype);
    Drone.prototype.constructor = Drone;
    Drone.prototype.update = function (game, dt) {
        Enemy.prototype.update.call(this, game, dt);
        var pl = game.player;
        if (!pl.alive) { return; }
        this.facing = pl.x < this.x ? -1 : 1;
        this.draw_off_y = -8.0 + Math.sin(this.t * 3.2) * 2.4;
        var d = this.dist_to_player(game);
        var a = Math.atan2(pl.y - this.y, pl.x - this.x);
        var mv;
        if (d < this.prefer - 34) { mv = -this.speed * 0.9; }
        else if (d > this.prefer + 34) { mv = this.speed; }
        else { mv = this.speed * 0.18; }
        var px = Math.cos(a + Math.PI / 2) * this.speed * 0.62 * this.strafe;
        var py = Math.sin(a + Math.PI / 2) * this.speed * 0.62 * this.strafe;
        var vx = Math.cos(a) * mv + px, vy = Math.sin(a) * mv + py;
        var p = moveCircle(this.x, this.y, this.radius, vx * dt, vy * dt, game.room.solid);
        this.x = p[0]; this.y = p[1];
        this._clamp_room();
        if (this.x < IN_L + 6 || this.x > IN_R - 6 ||
            this.y < IN_T + 6 || this.y > IN_B - 6) { this.strafe *= -1.0; }
        if (this.t % 1.7 < dt) { this.strafe *= -1.0; }

        if (this.burst_left > 0) {
            this.burst_t -= dt;
            if (this.burst_t <= 0) {
                this.burst_t = 0.16;
                this.burst_left--;
                this._shoot(game, a + game.rng.uniform(-0.07, 0.07),
                    196.0 + 12.0 * this.floor, this.bullet_dmg, 'b_hex', 14, 0.0, 1, 1.8);
            }
        } else {
            this.shoot_cd -= dt;
            if (this.shoot_cd <= 0 && d < 300) {
                this.shoot_cd = Math.max(0.9, 2.0 - 0.22 * this.floor);
                this.burst_left = this.volley;
                this.burst_t = 0.0;
            }
        }
        this._touch_player(game, this.contact_dmg);
    };

    // ---- 腐壳虫（需求 8）：蓄力 -> 直线冲锋 -> 撞墙僵直
    function Slug(x, y, floor, elite) {
        Enemy.call(this, x, y, floor, elite);
        this.kind = 'slug'; this.spr_key = 'slime'; this.spr_size = 42;
        this.radius = 14.0; this.body_color = [150, 132, 92];
        this.max_hp = (36 + 12 * (floor - 1)) * (elite ? 2.4 : 1.0);
        if (this.elite) { this.spr_size = Math.floor(42 * 1.22); this.radius = 14.0 * 1.18; }
        this.hp = this.max_hp;
        this.speed = 62.0 + 8.0 * (floor - 1);
        this.contact_dmg = 2.0;
        this.tint = [176, 156, 104];
        this.state = 'aim';
        this.st = (x * 0.017) % 0.6;
        this.dir = 0.0;
        this.squash = 1.0;
    }
    Slug.prototype = Object.create(Enemy.prototype);
    Slug.prototype.constructor = Slug;
    Slug.prototype.update = function (game, dt) {
        Enemy.prototype.update.call(this, game, dt);
        var pl = game.player;
        if (!pl.alive) { return; }
        this.facing = pl.x < this.x ? -1 : 1;
        this.st += dt;
        if (this.state === 'aim') {
            this.squash = 1.0 - 0.14 * Math.sin(this.st / 0.62 * Math.PI);
            var ta = Math.atan2(pl.y - this.y, pl.x - this.x);
            this.dir = this.st > 0.1 ? angLerp(this.dir, ta, 4.0 * dt) : ta;
            if (this.st >= 0.62) {
                this.state = 'dash'; this.st = 0.0;
                Sfx.play('lock', 0.4);
                game.fx.sparks(this.x, this.y, this.body_color, 6, this.dir + Math.PI);
            }
        } else {
            var sp = this.speed * 3.5;
            var ox = this.x, oy = this.y;
            var p = moveCircle(this.x, this.y, this.radius,
                Math.cos(this.dir) * sp * dt, Math.sin(this.dir) * sp * dt,
                game.room.solid);
            this.x = p[0]; this.y = p[1];
            var moved = dist(ox, oy, this.x, this.y);
            if (moved < sp * dt * 0.35 || this.st > 0.55) {
                this.state = 'aim'; this.st = -0.45;
                game.fx.ring(this.x, this.y, 3, 22, 0.28, this.body_color, 2);
            }
            this.squash = 1.05;
            if (this.t % 0.05 < dt) {
                game.fx.burst(this.x, this.y, this.body_color, 2, 40, 0.24, 3, 2.4, 'circle');
            }
        }
        this._clamp_room();
        this._touch_player(game, this.contact_dmg);
    };

    // ---- 孢殖体（需求 8）：死亡留下毒雾
    function SporeBug(x, y, floor, elite) {
        Enemy.call(this, x, y, floor, elite);
        this.kind = 'spore'; this.spr_key = 'bomber'; this.spr_size = 42;
        this.radius = 14.0; this.body_color = [140, 196, 96];
        this.max_hp = (41 + 14 * (floor - 1)) * (elite ? 2.4 : 1.0);
        if (this.elite) { this.spr_size = Math.floor(42 * 1.22); this.radius = 14.0 * 1.18; }
        this.hp = this.max_hp;
        this.speed = 34.0 + 4.0 * (floor - 1);
        this.contact_dmg = 1.5;
        this.tint = [150, 210, 110];
        this.squash = 1.0;
        this.draw_off_y = 0.0;
        this.cloud_r = 46.0 + 4.0 * (floor - 1);
        this.cloud_dmg = 1.4;
    }
    SporeBug.prototype = Object.create(Enemy.prototype);
    SporeBug.prototype.constructor = SporeBug;
    SporeBug.prototype.update = function (game, dt) {
        Enemy.prototype.update.call(this, game, dt);
        var pl = game.player;
        if (!pl.alive) { return; }
        this.facing = pl.x < this.x ? -1 : 1;
        this.draw_off_y = Math.sin(this.t * 2.1) * 4.0;
        var a = Math.atan2(pl.y - this.y, pl.x - this.x);
        var d = this.dist_to_player(game);
        var mv = d > 96 ? this.speed : -this.speed * 0.5;
        var p = moveCircle(this.x, this.y, this.radius,
            Math.cos(a) * mv * dt, Math.sin(a) * mv * dt, game.room.solid);
        this.x = p[0]; this.y = p[1];
        this._clamp_room();
        if (this.t % 0.5 < dt) {
            game.fx.burst(this.x, this.y, this.tint, 1, 10, 0.5, 3, 1.6, 'circle');
        }
        this._touch_player(game, this.contact_dmg);
    };
    SporeBug.prototype.die = function (game) {
        if (!this.alive) { return; }
        Enemy.prototype.die.call(this, game);
        try {
            if (game.room && game.room.clouds) {
                game.room.clouds.push(new PoisonCloud(this.x, this.y,
                    this.cloud_r, 4.2, this.tint, this.cloud_dmg));
            }
        } catch (err) { /* 忽略 */ }
    };

    // ---- 污染幽影（需求 8）：瞬移到背后 + 预判弹
    function Wraith(x, y, floor, elite) {
        Enemy.call(this, x, y, floor, elite);
        this.kind = 'wraith'; this.spr_key = 'drone'; this.spr_size = 42;
        this.radius = 13.0; this.body_color = [150, 120, 220];
        this.max_hp = (38 + 12 * (floor - 1)) * (elite ? 2.4 : 1.0);
        if (this.elite) { this.spr_size = Math.floor(42 * 1.22); this.radius = 13.0 * 1.18; }
        this.hp = this.max_hp;
        this.speed = 58.0 + 6.0 * (floor - 1);
        this.contact_dmg = 1.5;
        this.tint = [168, 140, 240];
        this.blink_cd = 2.4 + (x * 0.011) % 1.6;
        this.shoot_cd = 1.4;
    }
    Wraith.prototype = Object.create(Enemy.prototype);
    Wraith.prototype.constructor = Wraith;
    Wraith.prototype.update = function (game, dt) {
        Enemy.prototype.update.call(this, game, dt);
        var pl = game.player;
        if (!pl.alive) { return; }
        this.facing = pl.x < this.x ? -1 : 1;
        var d = this.dist_to_player(game);
        var a = Math.atan2(pl.y - this.y, pl.x - this.x);
        this.blink_cd -= dt;
        if (this.blink_cd <= 0 && d > 60) {
            var back = Math.atan2(this.y - pl.y, this.x - pl.x);
            var bx = clamp(pl.x + Math.cos(back) * 62, IN_L + 22, IN_R - 22);
            var by = clamp(pl.y + Math.sin(back) * 62, IN_T + 22, IN_B - 22);
            game.fx.burst(this.x, this.y, this.tint, 12, 120, 0.4, 4, 2.2, 'circle');
            game.fx.ring(this.x, this.y, 4, 30, 0.3, this.tint, 2);
            this.x = bx; this.y = by;
            game.fx.ring(this.x, this.y, 4, 30, 0.3, this.tint, 2);
            this.blink_cd = 2.6 + game.rng.uniform(-0.6, 1.0);
            this.shoot_cd = Math.min(this.shoot_cd, 0.28);
        } else {
            var mv = d > 110 ? this.speed : this.speed * 0.25;
            var sgn = (Math.floor(this.t) % 2) ? 1 : -1;
            var px = Math.cos(a + Math.PI / 2) * this.speed * 0.4 * sgn;
            var py = Math.sin(a + Math.PI / 2) * this.speed * 0.4 * sgn;
            var p = moveCircle(this.x, this.y, this.radius,
                (Math.cos(a) * mv + px) * dt, (Math.sin(a) * mv + py) * dt,
                game.room.solid);
            this.x = p[0]; this.y = p[1];
        }
        this._clamp_room();
        this.shoot_cd -= dt;
        if (this.shoot_cd <= 0 && d < 280) {
            this.shoot_cd = Math.max(1.05, 1.9 - 0.14 * this.floor);
            var lead = 0.28;
            var tx = pl.x + (pl.vx || 0) * lead;
            var ty = pl.y + (pl.vy || 0) * lead;
            this._shoot(game, Math.atan2(ty - this.y, tx - this.x),
                214.0, this.bullet_dmg, 13, 0, 1, 1.7);
        }
        this._touch_player(game, this.contact_dmg);
    };

    // ---- 拟态宝箱（需求 8）：伪装成宝箱，靠近才现形
    function Mimic(x, y, floor, elite) {
        Enemy.call(this, x, y, floor, elite);
        this.kind = 'mimic'; this.spr_key = 'chest'; this.spr_size = 40;
        this.radius = 15.0; this.body_color = [222, 178, 90];
        this.max_hp = 122.0 + 35.0 * (floor - 1);
        this.hp = this.max_hp;
        this.speed = 92.0;
        this.contact_dmg = 2.0;
        this.tint = [240, 200, 110];
        this.awake = false;
        this.squash = 1.0;
        this.is_rare = true;
    }
    Mimic.prototype = Object.create(Enemy.prototype);
    Mimic.prototype.constructor = Mimic;
    Mimic.prototype.update = function (game, dt) {
        Enemy.prototype.update.call(this, game, dt);
        var pl = game.player;
        if (!pl.alive) { return; }
        var d = this.dist_to_player(game);
        if (!this.awake) {
            if (d < 74.0) {
                this.awake = true;
                Sfx.play('ui_big', 0.8);
                game.fx.ring(this.x, this.y, 6, 46, 0.4, [255, 210, 120], 3);
                game.fx.add_shake(2.5);
                if (game.discover) { game.discover('enemy', 'mimic'); }
            }
            return;
        }
        this.facing = pl.x < this.x ? -1 : 1;
        var a = Math.atan2(pl.y - this.y, pl.x - this.x);
        var p = moveCircle(this.x, this.y, this.radius,
            Math.cos(a) * this.speed * dt, Math.sin(a) * this.speed * dt,
            game.room.solid);
        this.x = p[0]; this.y = p[1];
        this._clamp_room();
        this.squash = 1.0 + Math.sin(this.t * 9.0) * 0.06;
        this._touch_player(game, this.contact_dmg);
    };

    // ---- 拾荒旅人（需求 8）：不主动攻击，被打才逃
    function Wanderer(x, y, floor, elite) {
        Enemy.call(this, x, y, floor, elite);
        this.kind = 'wanderer'; this.spr_key = 'slime'; this.spr_size = 40;
        this.radius = 12.0; this.body_color = [230, 210, 130];
        this.max_hp = 62.0 + 19.0 * (floor - 1);
        this.hp = this.max_hp;
        this.speed = 78.0;
        this.contact_dmg = 0.0;
        this.tint = [250, 226, 140];
        this.flee = false;
        this.hop = 0.0;
        this.squash = 1.0;
        this.is_rare = true;
    }
    Wanderer.prototype = Object.create(Enemy.prototype);
    Wanderer.prototype.constructor = Wanderer;
    Wanderer.prototype.update = function (game, dt) {
        Enemy.prototype.update.call(this, game, dt);
        var pl = game.player;
        if (!pl.alive) { return; }
        this.facing = pl.x < this.x ? -1 : 1;
        var d = this.dist_to_player(game);
        if (!this.flee && d < 90) {
            this.flee = true;
            if (game.discover) { game.discover('enemy', 'wanderer'); }
        }
        this.hop = (this.hop + dt) % 0.8;
        this.squash = 1.0 + 0.08 * Math.sin(this.hop / 0.8 * Math.PI * 2);
        if (this.flee || d < 120) {
            var a = Math.atan2(this.y - pl.y, this.x - pl.x);
            var sgn = (Math.floor(this.t * 2) % 2) ? 1 : -1;
            var tang = a + Math.PI / 2 * sgn;
            var mx = Math.cos(a) * 0.65 + Math.cos(tang) * 0.55;
            var my = Math.sin(a) * 0.65 + Math.sin(tang) * 0.55;
            var n = Math.sqrt(mx * mx + my * my) || 1.0;
            var p = moveCircle(this.x, this.y, this.radius,
                mx / n * this.speed * dt, my / n * this.speed * dt,
                game.room.solid);
            this.x = p[0]; this.y = p[1];
        }
        this._clamp_room();
    };
    Wanderer.prototype.take_damage = function (dmg, game, sx, sy) {
        this.flee = true;
        Enemy.prototype.take_damage.call(this, dmg, game, sx, sy);
    };

    function LuckyTreasure(x, y, floor, elite) {
        Enemy.call(this, x, y, floor, elite);
        this.kind='lucky_treasure';this.spr_key='lucky_treasure';
        this.spr_size=48;this.radius=15;this.body_color=[255,215,93];
        this.max_hp=70;this.hp=70;this.speed=64;this.contact_dmg=0;
        this.squash=1;
    }
    LuckyTreasure.prototype=Object.create(Enemy.prototype);
    LuckyTreasure.prototype.constructor=LuckyTreasure;
    LuckyTreasure.prototype.update=function(game,dt){
        Enemy.prototype.update.call(this,game,dt);
        if(!game.player.alive)return;
        this.facing=game.player.x<this.x?-1:1;
        var a=Math.atan2(game.player.y-this.y,game.player.x-this.x);
        if(this.dist_to_player(game)>58){
            var p=moveCircle(this.x,this.y,this.radius,Math.cos(a)*this.speed*dt,
                Math.sin(a)*this.speed*dt,game.room.solid);
            this.x=p[0];this.y=p[1];
        }
        this._clamp_room();this.squash=1+.06*Math.sin(this.t*12);
    };

    // ---- 动态毒雾（需求 8）
    function PoisonCloud(x, y, radius, life, color, dmg) {
        this.x = x; this.y = y; this.radius = radius;
        this.life = life; this.max_life = life;
        this.color = color; this.dmg = dmg;
        this.t = 0.0; this.alive = true; this._tick = 0.0;
    }
    PoisonCloud.prototype.fade = function () {
        return Math.max(0, Math.min(1, 1 - this.life / this.max_life));
    };
    PoisonCloud.prototype.update = function (game, dt) {
        if (!this.alive) { return false; }
        this.t += dt; this.life -= dt;
        if (this.life <= 0) { this.alive = false; return false; }
        var pl = game.player;
        if (pl && pl.alive &&
            dist(this.x, this.y, pl.x, pl.y) < this.radius + pl.radius) {
            this._tick -= dt;
            if (this._tick <= 0) {
                this._tick = 0.5;
                pl.take_damage(this.dmg, game, this.x, this.y);
            }
        }
        return true;
    };

    var SCENE_BOSS_HP_MUL = {
        crust: 1.00, sewer: 1.35, facility: 1.75, core: 2.20,
        d_mine: 1.50, d_lab: 1.95, d_gift: 1.55
    };
    var SCENE_MOB_HP_MUL = {
        crust: 1.00, sewer: 1.25, facility: 1.50, core: 1.80,
        d_mine: 1.35, d_lab: 1.65, d_gift: 1.40
    };
    var SCENE_DMG_MUL = {
        crust: 1.00, sewer: 1.20, facility: 1.40, core: 1.60,
        d_mine: 1.30, d_lab: 1.50, d_gift: 1.35
    };
    var BOSS_SKIN = {
        'crust':    { name: '残骸军阀', title: 'WARLORD', tint: [198, 150, 96], color: [198, 150, 96], scale: 0.94, codex: 'warlord', big_mul: 1.25 },
        'sewer':    { name: '虫群女王', title: 'SWARM QUEEN', tint: [150, 210, 120], color: [150, 210, 120], scale: 0.98, codex: 'swarmqueen', big_mul: 1.25 },
        'facility': { name: '坟场机枢', title: 'MECH CORE', tint: [170, 190, 220], color: [170, 190, 220], scale: 1.0, codex: 'mech', big_mul: 1.25 },
        'core':     { name: '污染原点·本体', title: 'THE ORIGIN', tint: [222, 110, 230], color: [222, 110, 230], scale: 1.14, codex: 'origin', big_mul: 1.40 },
        'd_mine':   { name: '矿井监工', title: 'FOREMAN', tint: [196, 168, 120], color: [196, 168, 120], scale: 1.0, codex: 'foreman', big_mul: 1.25 },
        'd_lab':    { name: '冷库标本', title: 'SPECIMEN', tint: [150, 220, 235], color: [150, 220, 235], scale: 1.05, codex: 'specimen', big_mul: 1.25 },
        'd_gift':   { name: '净土守卫', title: 'GUARDIAN', tint: [255, 226, 150], color: [255, 226, 150], scale: 1.0, codex: 'guardian', big_mul: 1.25 }
    };
    var BOSS_SKIN_KEYS = { boss: true };
    var MINI_BOSS_NAMES = {
        crust: '熔渣哨兵', sewer: '污水管蛇', facility: '熔炉看守',
        core: '协议残片', d_mine: '地脉掘进机',
        d_lab: '零号冻卫', d_gift: '晶花园丁'
    };
    (function () {
        for (var k in BOSS_SKIN) {
            if (BOSS_SKIN.hasOwnProperty(k) && BOSS_SKIN[k].codex) {
                BOSS_SKIN_KEYS[BOSS_SKIN[k].codex] = true;
            }
        }
        for (var scene in MINI_BOSS_NAMES) {
            if (MINI_BOSS_NAMES.hasOwnProperty(scene)) {
                var mk = {
                    crust: 'crust_sentinel', sewer: 'sewer_serpent',
                    facility: 'facility_smelter', core: 'protocol',
                    d_mine: 'mine_excavator', d_lab: 'lab_cryowarden',
                    d_gift: 'gift_bloom'
                }[scene];
                BOSS_SKIN_KEYS[mk] = true;
            }
        }
    })();

    // ---- BOSS
    var ATK_P1 = [['ring', 3], ['spread', 3], ['charge', 2], ['summon', 1]];
    var ATK_P2 = [['ring', 3], ['spread', 3], ['charge', 3], ['summon', 2], ['sweep', 2]];
    var ATK_P3 = [['ring', 4], ['spread', 3], ['charge', 4], ['summon', 2], ['sweep', 4]];

    function Boss(x, y, floor, elite) {
        Enemy.call(this, x, y, floor, elite);
        this.kind = 'boss'; this.spr_key = 'boss'; this.spr_size = 96;
        this.radius = 32.0; this.body_color = [198, 84, 220];
        this.is_boss = true;
        this.elite = false;      // BOSS 不吃精英加成（与 Python 版一致）
        this.max_hp = 520.0 * (1.0 + 0.85 * (floor - 1));
        this.hp = this.max_hp;
        this.speed = 44.0 + 6.0 * (floor - 1);
        this.contact_dmg = 3.0;
        this.charge_dmg = 4.0;
        this.state = 'intro';
        this.st = 0.0;
        this.volley = 0;
        this.volley_t = 0.0;
        this.charge_dir = 0.0;
        this.death_t = 0.0;
        this.squash = 1.0;
        this.invuln = true;
    }
    Boss.prototype = Object.create(Enemy.prototype);
    Boss.prototype.constructor = Boss;
    // 需求 8：按场景给 Boss 换外观/名号/体型
    Boss.prototype.setup_scene = function (sceneKey, stageIdx) {
        var spec = BOSS_SKIN[sceneKey];
        if (!spec) { return; }
        this.tint = spec.tint;
        var mini = stageIdx === 2;
        this.boss_name = mini ? MINI_BOSS_NAMES[sceneKey] : spec.name;
        this.boss_title = mini ? 'WARDEN' : (spec.title || '');
        var scale = spec.scale || 1.0;
        if (Math.abs(scale - 1.0) > 0.001) {
            this.spr_size = Math.floor(this.spr_size * scale);
            this.radius *= scale;
        }
        this.body_color = spec.color || this.body_color;
        this.skey = mini ? SCENE_MINIBOSS[sceneKey] : spec.codex;
        if (this.skey && IMG_MANIFEST['enemy_' + this.skey]) {
            this.spr_key = 'enemy_' + this.skey;
            this.tint = null;
        }
        var sceneMul = SCENE_BOSS_HP_MUL[sceneKey] || 1.0;
        if (Math.abs(sceneMul - 1.0) > 0.001) {
            this.max_hp = Math.round(this.max_hp * sceneMul);
            this.hp = this.max_hp;
        }
        this.applyDmgMul(SCENE_DMG_MUL[sceneKey] || 1.0);
        if (stageIdx >= 4) {
            this.max_hp = Math.round(this.max_hp * (spec.big_mul || 1.25));
            this.hp = this.max_hp;
            this.radius *= 1.08;
            this.spr_size = Math.floor(this.spr_size * 1.08);
        }
    };
    Boss.prototype._pick_attack = function (game) {
        var r = this.hp_ratio();
        var table = r > 0.66 ? ATK_P1 : (r > 0.33 ? ATK_P2 : ATK_P3);
        var total = 0, i;
        for (i = 0; i < table.length; i++) { total += table[i][1]; }
        var pick = game.rng.uniform(0, total), acc = 0.0;
        for (i = 0; i < table.length; i++) {
            acc += table[i][1];
            if (pick <= acc) { return table[i][0]; }
        }
        return 'ring';
    };
    Boss.prototype._set_state = function (game, st) {
        this.state = st;
        this.st = 0.0;
        this.volley = 0;
        if (st === 'ring') { this.volley = 3; this.volley_t = 0.0; }
        else if (st === 'spread') { this.volley = 4; this.volley_t = 0.0; }
        else if (st === 'sweep') { this.volley = 3; this.volley_t = 0.0; }
        else if (st === 'charge') {
            var pl = game.player;
            this.charge_dir = Math.atan2(pl.y - this.y, pl.x - this.x);
            Sfx.play('lock');
            game.fx.ring(this.x, this.y, 10, 60, 0.5, [255, 90, 90], 3);
        } else if (st === 'summon') { this.volley = 0; }
    };
    Boss.prototype.update = function (game, dt) {
        Enemy.prototype.update.call(this, game, dt);
        this.st += dt;
        var pl = game.player;

        if (this.state === 'dying') {
            this.death_t += dt;
            this.invuln = true;
            if (Math.floor(this.death_t * 14) !== Math.floor((this.death_t - dt) * 14)) {
                game.fx.burst(this.x + game.rng.uniform(-40, 40),
                    this.y + game.rng.uniform(-40, 40), [255, 170, 90],
                    14, 160, 0.6, 5, TAU, 0, 2.0, 0, 'circle');
                game.fx.ring(this.x + game.rng.uniform(-30, 30),
                    this.y + game.rng.uniform(-30, 30), 4, 46, 0.35, [255, 200, 120], 2);
                game.fx.add_shake(4.0);
                Sfx.play('explode');
            }
            if (this.death_t > 1.5) {
                this.alive = false;
                game.fx.burst(this.x, this.y, [255, 230, 180], 46, 300, 1.1, 6, TAU, 0, 1.4, 0, 'circle');
                game.fx.ring(this.x, this.y, 8, 190, 0.9, [255, 220, 160], 6);
                game.fx.add_shake(15.0);
                game.fx.add_flash(0.55, [255, 220, 160]);
                Sfx.play('boss_die');
                game.onEnemyKilled(this);
                game.onBossDefeated();
            }
            return;
        }
        if (!pl.alive) { this.state = 'idle'; this.squash = 1.0; return; }

        this.facing = pl.x < this.x ? -1 : 1;
        this.squash = 1.0;
        var d = this.dist_to_player(game);
        var to_pl = Math.atan2(pl.y - this.y, pl.x - this.x);

        // ---- intro
        if (this.state === 'intro') {
            this.invuln = true;
            if (this.st < 0.9) {
                if (this.st % 0.2 < dt) {
                    game.fx.ring(this.x, this.y, 20, 110, 0.5, [230, 110, 250], 3);
                    game.fx.burst(this.x, this.y, [230, 120, 250], 10, 130, 0.5, 4, TAU, 0, 2.6, 0, 'circle');
                }
            } else {
                this.invuln = false;
                this._set_state(game, 'idle');
            }
            return;
        }

        // ---- idle
        if (this.state === 'idle') {
            this.squash = 1.0 + Math.sin(this.st * 4.0) * 0.02;
            var mv = d > 90 ? this.speed * 0.55 : -this.speed * 0.35;
            var p = moveCircle(this.x, this.y, this.radius,
                Math.cos(to_pl) * mv * dt, Math.sin(to_pl) * mv * dt, game.room.solid);
            this.x = p[0]; this.y = p[1];
            this._clamp_room(40);
            if (this.st > 0.75) { this._set_state(game, this._pick_attack(game)); }
            return;
        }

        // ---- 环形弹幕
        if (this.state === 'ring') {
            if (this.volley > 0) {
                this.volley_t -= dt;
                if (this.volley_t <= 0) {
                    this.volley_t = 0.30;
                    this.volley--;
                    var n = 13 + 3 * Math.min(3, this.floor);
                    var base = this.st * 1.7 + this.volley * 0.22;
                    for (var i = 0; i < n; i++) {
                        this._shoot(game, base + i * (TAU / n),
                            150.0 + 12.0 * this.floor, this.bullet_dmg, 'b_hex', 14, 0, 1, 2.2);
                    }
                    Sfx.play('shoot_heavy');
                    game.fx.ring(this.x, this.y, 20, 56, 0.26, [226, 130, 250], 2);
                }
            } else if (this.st > 1.2) { this._set_state(game, 'idle'); }
            return;
        }

        // ---- 扇形连射
        if (this.state === 'spread') {
            if (this.volley > 0) {
                this.volley_t -= dt;
                if (this.volley_t <= 0) {
                    this.volley_t = 0.24;
                    this.volley--;
                    this._shoot(game, to_pl, 228.0, this.bullet_dmg, 'b_hex', 15,
                        34 * Math.PI / 180, 5, 2.0);
                    Sfx.play('shoot');
                    game.fx.add_shake(1.2);
                }
            } else if (this.st > 1.15) { this._set_state(game, 'idle'); }
            return;
        }

        // ---- 冲锋
        if (this.state === 'charge') {
            if (this.st < 0.55) {
                this.squash = 1.0 - 0.2 * Math.sin(this.st / 0.55 * Math.PI);
                this.charge_dir = angLerp(this.charge_dir, to_pl, 3.0 * dt);
                if (this.st % 0.09 < dt) {
                    game.fx.sparks(this.x, this.y, [255, 120, 90], 4, this.charge_dir + Math.PI);
                }
            } else if (this.st < 1.15) {
                var sp = 330.0 + 25.0 * this.floor;
                var p2 = moveCircle(this.x, this.y, this.radius,
                    Math.cos(this.charge_dir) * sp * dt,
                    Math.sin(this.charge_dir) * sp * dt, game.room.solid);
                this.x = p2[0]; this.y = p2[1];
                this._clamp_room(34);
                if (this.st % 0.05 < dt) {
                    game.fx.burst(this.x, this.y, [255, 150, 90], 3, 60, 0.3, 4, TAU, 0, 2.4, 0, 'circle');
                    game.fx.add_shake(1.0);
                }
                if (dist(this.x, this.y, pl.x, pl.y) < this.radius + pl.radius + 4) {
                    pl.take_damage(this.charge_dmg, game, this.x, this.y);
                }
            } else { this._set_state(game, 'idle'); }
            return;
        }

        // ---- 召唤
        if (this.state === 'summon') {
            if (this.volley === 0) {
                this.volley = 1;
                var sumSc = (game.level_state || {}).scene;
                var k = (this.floor >= 2 || sumSc === 'facility' || sumSc === 'core' || sumSc === 'd_lab') ? 3 : 2;
                for (var j = 0; j < k; j++) {
                    var a = game.rng.uniform(0, TAU), rr = game.rng.uniform(70, 130);
                    var sx = clamp(this.x + Math.cos(a) * rr, IN_L + 24, IN_R - 24);
                    var sy = clamp(this.y + Math.sin(a) * rr, IN_T + 24, IN_B - 24);
                    game.fx.ring(sx, sy, 4, 44, 0.45, [200, 120, 250], 3);
                    game.fx.burst(sx, sy, [200, 130, 250], 12, 120, 0.5, 4, TAU, 0, 2.6, 0, 'circle');
                    game.spawnMinion(sx, sy, this.floor);
                }
                Sfx.play('ui_big');
                game.fx.add_shake(3.0);
            } else if (this.st > 0.95) { this._set_state(game, 'idle'); }
            return;
        }

        // ---- 扫射
        if (this.state === 'sweep') {
            if (this.volley > 0) {
                this.volley_t -= dt;
                if (this.volley_t <= 0) {
                    this.volley_t = 0.26;
                    this.volley--;
                    var base2 = to_pl - 30 * Math.PI / 180 + (2 - this.volley) * (22 * Math.PI / 180);
                    for (var m = 0; m < 7; m++) {
                        this._shoot(game, base2 + (m - 3) * (7.5 * Math.PI / 180),
                            265.0, this.bullet_dmg, 'b_hex', 13, 0, 1, 1.9);
                    }
                    Sfx.play('shoot');
                    game.fx.add_shake(1.4);
                }
            } else if (this.st > 1.3) { this._set_state(game, 'idle'); }
            return;
        }

        this._set_state(game, 'idle');
    };
    // ---- 受伤 / 死亡（intro 与 dying 阶段免疫伤害）
    Boss.prototype.take_damage = function (dmg, game, sx, sy) {
        if (this.state === 'intro' || this.state === 'dying') { return; }
        Enemy.prototype.take_damage.call(this, dmg, game, sx, sy);
    };
    Boss.prototype.die = function (game) {
        if (!this.alive || this.state === 'dying') { return; }
        this.state = 'dying';
        this.death_t = 0.0;
        this.invuln = true;
        this.kx = 0.0;
        this.ky = 0.0;
        Sfx.play('boss_die');
        game.fx.add_shake(10.0);
        game.fx.add_flash(0.35, [255, 200, 140]);
    };

    Boss.prototype.draw = function (cam) {
        if (!this.alive) { return; }
        var x = this.x + cam[0], y = this.y + cam[1];
        var size = this.spr_size;
        drawShadow(x, y + size * 0.30, size * 0.34, size * 0.15, 170);
        var flip = this.facing < 0;
        var sq = this.squash;
        var dw = size, dh = size, dy = y;
        if (Math.abs(sq - 1.0) > 0.01) {
            dh = Math.max(2, Math.floor(size * sq));
            dy = y + size * (1 - sq) * 0.4;
        }
        if (this.tint) {
            blitTint('boss', x, dy, dw, dh, this.tint, 0.62, { flip: flip });
        } else {
            blit('boss', x, dy, dw, dh, { flip: flip });
        }
        if (this.hit_flash > 0) {
            blitTintAdd('boss', x, dy, dw, dh, (this.hit_flash / 0.13) * 0.667, flip);
        }
        // 冲锋前的预警射线
        if (this.state === 'charge' && this.st < 0.55) {
            var t = this.st / 0.55, ln = 150;
            ctx.save();
            ctx.globalAlpha = 0.47 * (1 - t) + 0.157;
            ctx.strokeStyle = 'rgb(255,90,80)';
            ctx.lineWidth = 4;
            ctx.beginPath();
            ctx.moveTo(x, y);
            ctx.lineTo(x + Math.cos(this.charge_dir) * ln, y + Math.sin(this.charge_dir) * ln);
            ctx.stroke();
            ctx.restore();
        }
    };

    function RangedRaider(x, y, floor, elite, mode) {
        Enemy.call(this, x, y, floor, elite);
        var configs = {
            scatter: { key: 'scatter_raider', color: [223, 161, 112],
                speed: 170, count: 5, spread: 0.85, img: 'b_bullet', size: 11,
                cd: 2.2, prefer: 165 },
            beam: { key: 'beam_raider', color: [174, 132, 239],
                speed: 105, count: 1, spread: 0, img: 'b_laser', size: 18,
                cd: 2.8, prefer: 210 },
            rifle: { key: 'rifle_raider', color: [139, 218, 224],
                speed: 420, count: 1, spread: 0, img: 'b_bolt', size: 12,
                cd: 1.65, prefer: 205 }
        };
        var c = configs[mode] || configs.scatter;
        this.kind = c.key; this.spr_key = 'enemy_' + c.key;
        this.spr_size = 42; this.radius = 13;
        this.body_color = c.color;
        this.max_hp = (30 + floor * 8) * (elite ? 2.4 : 1);
        this.hp = this.max_hp;
        this.speed = 51 + floor * 4; this.contact_dmg = 1;
        this.shot_speed = c.speed; this.shot_count = c.count;
        this.shot_spread = c.spread; this.shot_img = c.img;
        this.shot_size = c.size; this.shot_cd = c.cd;
        this.prefer = c.prefer;
        this.shoot_cd = c.cd * (0.5 + (x % 17) / 34);
    }
    RangedRaider.prototype = Object.create(Enemy.prototype);
    RangedRaider.prototype.constructor = RangedRaider;
    RangedRaider.prototype.update = function (game, dt) {
        Enemy.prototype.update.call(this, game, dt);
        var pl = game.player;
        if (!pl.alive) { return; }
        this.facing = pl.x < this.x ? -1 : 1;
        var d = this.dist_to_player(game);
        var a = Math.atan2(pl.y - this.y, pl.x - this.x);
        var mv = this.speed * (d > this.prefer + 25 ? 1 :
            (d < this.prefer - 25 ? -0.65 : 0));
        var pos = moveCircle(this.x, this.y, this.radius,
            Math.cos(a) * mv * dt, Math.sin(a) * mv * dt, game.room.solid);
        this.x = pos[0]; this.y = pos[1];
        this.shoot_cd -= dt;
        if (this.shoot_cd <= 0 && d < 390) {
            this.shoot_cd = this.shot_cd;
            this._shoot(game, a, this.shot_speed, this.bullet_dmg,
                this.shot_img, this.shot_size, this.shot_spread,
                this.shot_count, this.shot_speed < 150 ? 3.5 : 2.4);
            game.fx.ring(this.x, this.y, 2, 18, 0.18, this.body_color, 2);
        }
        this._touch_player(game, this.contact_dmg);
    };
    function ScatterRaider(x, y, floor, elite) { RangedRaider.call(this, x, y, floor, elite, 'scatter'); }
    ScatterRaider.prototype = Object.create(RangedRaider.prototype);
    function BeamRaider(x, y, floor, elite) { RangedRaider.call(this, x, y, floor, elite, 'beam'); }
    BeamRaider.prototype = Object.create(RangedRaider.prototype);
    function RifleRaider(x, y, floor, elite) { RangedRaider.call(this, x, y, floor, elite, 'rifle'); }
    RifleRaider.prototype = Object.create(RangedRaider.prototype);
    var ENEMY_TYPES = { slime: Slime, bomber: Bomber, drone: Drone,
        mimic: Mimic, wanderer: Wanderer, lucky_treasure: LuckyTreasure,
        scatter_raider: ScatterRaider, beam_raider: BeamRaider,
        rifle_raider: RifleRaider };
    // 需求 8：场景变体 -> [基础类, tint, 数值微调]（与 Python enemy.VARIANT_OF 同源）
    var VARIANT_OF = {
        'crawler':       ['slime',  [186, 138, 96],  { speed_mul: 1.28, hp_mul: 0.82 }],
        'leech':         ['wraith', [196, 76, 96],   { speed_mul: 1.12, hp_mul: 0.9 }],
        'turret':        ['drone',  [198, 186, 160], { speed_mul: 0.16, hp_mul: 1.25, range_mul: 1.5 }],
        'rockworm':      ['slug',   [168, 142, 118], { speed_mul: 1.1, hp_mul: 1.15 }],
        'minebot':       ['bomber', [176, 176, 190], { hp_mul: 1.2 }],
        'frostbite':     ['spore',  [150, 220, 240], { speed_mul: 0.9 }],
        'purifier':      ['slug',   [230, 226, 210], { speed_mul: 0.82, hp_mul: 1.4 }],
        'sprite':        ['wraith', [250, 240, 180], { speed_mul: 1.2, hp_mul: 0.85 }],
        'slime_big_m':   ['slime',  [176, 156, 108], { hp_mul: 1.35 }],
        'spore_big_m':   ['spore',  [128, 200, 96],  { hp_mul: 1.3 }],
        'crawler_big':   ['slime',  [206, 148, 96],  { hp_mul: 1.2 }],
        'leech_big':     ['wraith', [216, 66, 92],   { hp_mul: 1.2 }],
        'turret_big':    ['drone',  [216, 200, 168], { hp_mul: 1.3, range_mul: 1.5 }],
        'rockworm_big':  ['slug',   [188, 156, 124], { hp_mul: 1.3 }],
        'frostbite_big': ['spore',  [170, 232, 250], { hp_mul: 1.25 }],
        'guardian_big':  ['slug',   [250, 246, 226], { hp_mul: 1.5 }]
    };
    var ELITE_BASE = {};
    (function () {
        for (var k in ENEMY_TYPES) {
            if (ENEMY_TYPES.hasOwnProperty(k)) { ELITE_BASE[k + '_big'] = k; }
        }
    })();

    function baseKindW(kind) {
        if (ENEMY_TYPES[kind]) { return kind; }
        if (VARIANT_OF[kind]) { return VARIANT_OF[kind][0]; }
        if (ELITE_BASE[kind]) { return ELITE_BASE[kind]; }
        if (kind && kind.slice(-4) === '_big') {
            var s = kind.slice(0, -4);
            if (VARIANT_OF[s]) { return VARIANT_OF[s][0]; }
            if (ENEMY_TYPES[s]) { return s; }
        }
        return 'slime';
    }

    function codexHasW(k) {
        return !!(D.ENEMY_CODEX && D.ENEMY_CODEX[k]);
    }

    function makeEnemy(kind, x, y, floor, elite) {
        var bk = baseKindW(kind);
        var isElite = !!elite || (kind && kind.slice(-4) === '_big');
        var C = ENEMY_TYPES[bk] || Slime;
        var e = new C(x, y, floor, isElite);
        // 场景变体：染色 + 数值
        var v = VARIANT_OF[kind];
        if (v) {
            try {
                e.tint = v[1];
                var tw = v[2] || {};
                if (tw.speed_mul) { e.speed *= tw.speed_mul; }
                if (tw.hp_mul) { e.max_hp *= tw.hp_mul; e.hp = e.max_hp; }
                if (tw.range_mul && e.prefer !== undefined) { e.prefer *= tw.range_mul; }
            } catch (err) { /* 忽略 */ }
        }
        // 图鉴标记（需求 8）
        try {
            e.skey = codexHasW(kind) ? kind : bk;
            if (isElite && !codexHasW(kind)) {
                var big = bk + '_big';
                e.skey = codexHasW(big) ? big : bk;
            }
            if (e.skey && IMG_MANIFEST['enemy_' + e.skey] && !(e instanceof Boss)) {
                e.spr_key = 'enemy_' + e.skey;
                e.tint = null;
            }
        } catch (err) { /* 忽略 */ }
        return e;
    }

    // ==================================================================== 房间
    var T_FLOOR = 0, T_WALL = 1, T_DOOR = 2;

    function Room(gx, gy, kind, doors, rng, floor) {
        var self = this;
        this.gx = gx; this.gy = gy; this.kind = kind;
        this.doors = doors.slice();
        this.open_doors = doors.slice();
        this.floor = floor; this.rng = rng;
        this.visited = false;
        this.cleared = (kind === 'start' || kind === 'treasure' ||
            kind === 'heal' || kind === 'shop' || kind === 'drink');
        this.enemies_spawned = false;
        this.loot_taken = false;
        this.spawn_plan = []; this.wave_plans = []; this.wave_index = 0;
        this.pickup_plan = []; this.prop_plan = [];
        this.hazard_plan = null;     // planScene() 的产物，进房间时物化
        this.props = []; this.pickups = [];
        this.traps = []; this.covers = []; this.caves = []; this.speed_strips = [];
        this.clouds = [];        // 动态毒雾（需求 8）
        this.portal = null; this.portal_t = 0.0;
        this._props_built = false;
        this._hazards_built = false;
        this._bg = null;

        this.tiles = [];
        var tx, ty;
        for (ty = 0; ty < ROOM_ROWS; ty++) {
            var row = [];
            for (tx = 0; tx < ROOM_COLS; tx++) { row.push(T_FLOOR); }
            this.tiles.push(row);
        }
        this.door_dir_at = {};
        for (var i = 0; i < this.doors.length; i++) {
            var d = this.doors[i], dtc = DOOR_TILE[d];
            for (var off = -1; off <= 1; off++) {
                var wx = dtc[0] + ((d === 'N' || d === 'S') ? off : 0);
                var wy = dtc[1] + ((d === 'W' || d === 'E') ? off : 0);
                this.door_dir_at[wx + ',' + wy] = d;
            }
        }
        for (ty = 0; ty < ROOM_ROWS; ty++) {
            for (tx = 0; tx < ROOM_COLS; tx++) {
                var border = (tx === 0 || ty === 0 ||
                    tx === ROOM_COLS - 1 || ty === ROOM_ROWS - 1);
                if (!border) { this.tiles[ty][tx] = T_FLOOR; }
                else if (this.door_dir_at[tx + ',' + ty]) { this.tiles[ty][tx] = T_DOOR; }
                else { this.tiles[ty][tx] = T_WALL; }
            }
        }

        // solid 以闭包形式暴露：会被直接传给碰撞函数，不能依赖 this 绑定
        this.solid = function (tx2, ty2) {
            var t;
            if (tx2 >= 0 && tx2 < ROOM_COLS && ty2 >= 0 && ty2 < ROOM_ROWS) {
                t = self.tiles[ty2][tx2];
            } else {
                t = T_WALL;
            }
            if (t === T_WALL) { return true; }
            if (t === T_DOOR) {
                var dd = self.door_dir_at[tx2 + ',' + ty2];
                return self.open_doors.indexOf(dd) < 0;
            }
            return false;
        };
    }
    Room.prototype.tile = function (tx, ty) {
        if (tx >= 0 && tx < ROOM_COLS && ty >= 0 && ty < ROOM_ROWS) {
            return this.tiles[ty][tx];
        }
        return T_WALL;
    };
    // 圆形阻挡物：可破坏道具 + 掩体（需求 3）
    Room.prototype.blockers = function () {
        var out = [], i;
        for (i = 0; i < this.props.length; i++) {
            var p = this.props[i];
            if (p.alive) { out.push([p.x, p.y, p.radius]); }
        }
        for (i = 0; i < this.covers.length; i++) {
            var c = this.covers[i];
            if (c.alive) { out.push([c.x, c.y, c.radius]); }
        }
        return out;
    };
    // 供子弹/爆炸统一施加伤害的地形物件
    Room.prototype.hazards = function () {
        var out = [];
        for (var i = 0; i < this.covers.length; i++) {
            if (this.covers[i].alive) { out.push(this.covers[i]); }
        }
        return out;
    };
    // 把 hazard_plan 物化成 Trap / Cover / Cave（需求 3）
    // props、掩体、陷阱三者共用一份占位表，保证互不重叠；
    // 掩体额外做一次落点校验：若正好压在门格/入口上会被拉偏，避免堵死通道。
    Room.prototype.build_hazards = function () {
        if (this._hazards_built) { return; }
        this._hazards_built = true;
        var plan = this.hazard_plan, i;
        if (!plan) { return; }
        for (i = 0; i < plan.traps.length; i++) {
            var tp = plan.traps[i];
            this.traps.push(new Trap(tp[1], tp[2], tp[0], tp[3]));
        }
        for (i = 0; i < (plan.strips || []).length; i++) {
            var st = plan.strips[i];
            this.speed_strips.push(st[0] === 'up' ?
                new SpeedUpStrip(st[1], st[2]) : new SlowDownStrip(st[1], st[2]));
        }
        for (i = 0; i < plan.covers.length; i++) {
            var cv = plan.covers[i];
            var f = unstick(cv[1], cv[2], 15.0, this.solid, null,
                [ROOM_CX, ROOM_CY]);
            this.covers.push(new Cover(f[0], f[1], cv[0], cv[3]));
        }
        for (i = 0; i < plan.caves.length; i++) {
            var ca = plan.caves[i];
            this.caves.push(new Cave(ca[1], ca[2], ca[0]));
        }
    };
    Room.prototype.update_hazards = function (game, dt) {
        var i;
        for (i = 0; i < this.traps.length; i++) {
            if (this.traps[i].alive) { this.traps[i].update(game, dt); }
        }
        for (i = 0; i < this.covers.length; i++) {
            if (this.covers[i].alive) { this.covers[i].update(game, dt); }
        }
        for (i = 0; i < this.caves.length; i++) {
            if (this.caves[i].alive) { this.caves[i].update(game, dt); }
        }
        // 动态毒雾（需求 8）：逐帧结算 + 过期回收
        if (this.clouds) {
            var keep = [];
            for (i = 0; i < this.clouds.length; i++) {
                var cl = this.clouds[i];
                if (typeof cl.update === 'function') {
                    if (cl.update(game, dt)) { keep.push(cl); }
                } else { keep.push(cl); }
            }
            this.clouds = keep;
        }
    };
    // 地面层：陷阱底盘、洞穴、毒雾
    Room.prototype.draw_hazards_under = function (cam) {
        var i;
        for (i = 0; i < this.speed_strips.length; i++) { this.speed_strips[i].draw(cam); }
        for (i = 0; i < this.caves.length; i++) {
            if (this.caves[i].alive) { this.caves[i].draw(cam); }
        }
        for (i = 0; i < this.traps.length; i++) {
            if (this.traps[i].alive) { this.traps[i].drawUnder(cam); }
        }
        if (this.clouds) {
            for (i = 0; i < this.clouds.length; i++) {
                this._drawCloud(this.clouds[i], cam);
            }
        }
    };
    Room.prototype._drawCloud = function (cl, cam) {
        var x = cl.x + cam[0], y = cl.y + cam[1];
        var r = cl.radius, fade = cl.fade ? cl.fade() : 0;
        var alpha = 120 * (1 - fade) + 24;
        ctx.save();
        var layers = [[1.0, 0.55], [0.72, 0.75], [0.44, 1.0]];
        for (var i = 0; i < layers.length; i++) {
            var wob = 1.0 + Math.sin(cl.t * 2.2 + i * 1.7) * 0.06;
            ctx.beginPath();
            ctx.arc(Math.round(x), Math.round(y),
                Math.max(2, r * layers[i][0] * wob), 0, TAU);
            ctx.fillStyle = cssColor(cl.color, alpha * layers[i][1] / 255);
            ctx.fill();
        }
        ctx.restore();
    };
    // 角色层之上：地刺/电场/喷焰
    Room.prototype.draw_hazards_over = function (cam) {
        for (var i = 0; i < this.traps.length; i++) {
            if (this.traps[i].alive) { this.traps[i].drawOver(cam); }
        }
    };
    Room.prototype.refresh_doors = function (locked) {
        this.open_doors = locked ? [] : this.doors.slice();
    };
    Room.prototype.label = function () { return KIND_LABEL[this.kind] || this.kind; };
    Room.prototype.build_props = function () {
        if (this._props_built) { return; }
        this._props_built = true;
        for (var i = 0; i < this.prop_plan.length; i++) {
            var k = this.prop_plan[i];
            this.props.push(new Prop(k[1], k[2], k[0]));
        }
    };
    Room.prototype.build_pickups = function () {
        for (var i = 0; i < this.pickup_plan.length; i++) {
            var kw = this.pickup_plan[i];
            this.pickups.push(new Pickup(kw.x, kw.y, kw.kind, kw.value, kw.wkey,
                kw.price, kw.ckey, kw.ctier));
        }
        this.pickup_plan = [];
    };
    function drawThemeDecor(g, scene, gx, gy, floor) {
        var colors = {
            crust: [[75,219,234],[213,94,215]], sewer: [[113,231,151],[203,239,91]],
            facility: [[91,210,250],[255,169,88]], core: [[246,88,148],[255,180,93]],
            d_mine: [[255,192,102],[255,229,129]], d_lab: [[143,219,255],[210,249,255]],
            d_gift: [[104,249,211],[249,219,124]]
        };
        if (!colors[scene]) { return; }
        var seed = floor * 743 + gx * 197 + gy * 389, i, x, y, c;
        for (i = 0; i < scene.length; i++) { seed += scene.charCodeAt(i) * 991; }
        function rnd() { seed = (Math.imul(seed, 1664525) + 1013904223) | 0;
                         return (seed >>> 0) / 4294967296; }
        g.save();
        for (i = 0; i < 23; i++) {
            x = 45 + Math.floor(rnd() * (ROOM_PX_W - 90));
            y = 47 + Math.floor(rnd() * (ROOM_PX_H - 94));
            if (Math.abs(x - ROOM_CX) < 44 && Math.abs(y - ROOM_CY) < 38) { continue; }
            c = colors[scene][i % 4 === 0 ? 1 : 0];
            if (i % 5 === 0) {
                var glow = g.createRadialGradient(x, y, 0, x, y, 18);
                glow.addColorStop(0, cssColor(c, 0.17));
                glow.addColorStop(1, cssColor(c, 0));
                g.fillStyle = glow;g.fillRect(x - 18, y - 18, 36, 36);
            }
            g.strokeStyle = cssColor(c, .55);
            g.fillStyle = cssColor(c, .52);
            g.lineWidth = 2;
            if (scene === 'crust' || scene === 'd_mine') {
                g.beginPath();g.moveTo(x - 5,y + 7);g.lineTo(x,y - 10);
                g.lineTo(x + 5,y + 6);g.closePath();g.fill();
                g.strokeStyle=cssColor(colors[scene][1],.6);
                g.beginPath();g.moveTo(x,y - 8);g.lineTo(x + 2,y + 4);g.stroke();
            } else if (scene === 'sewer') {
                g.beginPath();g.ellipse(x,y,12,5,0,0,TAU);g.fill();
                g.fillStyle=cssColor(colors[scene][1],.72);g.fillRect(x + 4,y - 2,3,3);
            } else if (scene === 'facility') {
                g.beginPath();g.moveTo(x - 12,y);g.lineTo(x + 8,y);
                g.lineTo(x + 8,y + 8);g.stroke();
                g.fillStyle=cssColor(colors[scene][1],.75);g.fillRect(x + 6,y + 6,5,4);
            } else if (scene === 'core' || scene === 'd_lab') {
                g.beginPath();g.moveTo(x - 11,y - 7);g.lineTo(x,y);
                g.lineTo(x + 10,y + 8);g.stroke();
                g.fillStyle=cssColor(colors[scene][1],.7);g.fillRect(x - 2,y - 2,4,4);
            } else {
                g.beginPath();g.moveTo(x,y + 8);g.lineTo(x,y - 6);g.stroke();
                g.beginPath();g.ellipse(x - 4,y - 5,5,3,-.3,0,TAU);g.fill();
                g.fillStyle=cssColor(colors[scene][1],.7);
                g.beginPath();g.ellipse(x + 4,y - 7,5,3,.3,0,TAU);g.fill();
            }
        }
        g.restore();
    }
    // 背景烘焙：主题地块 + 跨砖块环境细节 + 门洞 + 内投影。
    Room.prototype.bg = function () {
        if (this._bg) { return this._bg; }
        var c = document.createElement('canvas');
        c.width = ROOM_PX_W; c.height = ROOM_PX_H;
        var g = c.getContext('2d');
        g.imageSmoothingEnabled = false;
        g.fillStyle = 'rgb(14,13,18)';
        g.fillRect(0, 0, ROOM_PX_W, ROOM_PX_H);
        for (var ty = 0; ty < ROOM_ROWS; ty++) {
            for (var tx = 0; tx < ROOM_COLS; tx++) {
                var t = this.tiles[ty][tx];
                var px = tx * TILE, py = ty * TILE;
                var h = (tx * 7 + ty * 13) % 5;
                var key = null;
                var suffix = IMG['tile_floor_' + this.scene_key] ? '_' + this.scene_key : '';
                if (t === T_FLOOR) { key = (h === 0 ? 'tile_floor_alt' : 'tile_floor') + suffix; }
                else if (t === T_DOOR) { key = 'tile_floor' + suffix; }
                else { key = (ty === 0 ? 'tile_wall_top' : 'tile_wall') + suffix; }
                if (IMG[key]) { g.drawImage(IMG[key], px, py, TILE, TILE); }
                if (t === T_DOOR) {
                    g.fillStyle = 'rgba(0,0,0,0.463)';
                    g.fillRect(px, py, TILE, TILE);
                }
                if (h >= 3 && t !== T_WALL) {
                    g.fillStyle = 'rgba(0,0,0,' + ((16 + 8 * (h - 3)) / 255) + ')';
                    g.fillRect(px, py, TILE, TILE);
                }
            }
        }
        var palette = (D.CHAPTER_STORY || {})[this.scene_key || ''];
        if (palette && palette.tint) {
            g.fillStyle = cssColor(palette.tint, 22 / 255);
            g.fillRect(0, 0, ROOM_PX_W, ROOM_PX_H);
        }
        for (ty = 1; ty < ROOM_ROWS - 1; ty++) {
            for (tx = 1; tx < ROOM_COLS - 1; tx++) {
                if (this.tiles[ty][tx] !== T_FLOOR) { continue; }
                h = (tx * 37 + ty * 53 + this.gx * 11 + this.gy * 19) % 13;
                px = tx * TILE; py = ty * TILE;
                if (h === 0) {
                    g.strokeStyle = 'rgb(82,78,92)'; g.lineWidth = 1;
                    g.beginPath(); g.moveTo(px + 7, py + 8);
                    g.lineTo(px + 17, py + 14); g.lineTo(px + 22, py + 24);
                    g.stroke();
                } else if (h === 1) {
                    g.fillStyle = 'rgb(102,98,108)';
                    g.fillRect(px + 11, py + 21, 2, 2);
                }
            }
        }
        drawThemeDecor(g, this.scene_key, this.gx, this.gy, this.floor);
        for (var i = 0; i < 6; i++) {
            var a = 58 * Math.pow(1 - i / 6.0, 1.5);
            if (a <= 1) { continue; }
            g.fillStyle = 'rgba(0,0,0,' + (a / 255) + ')';
            g.fillRect(TILE, TILE + i, ROOM_PX_W - 2 * TILE, 1);
            g.fillRect(TILE, ROOM_PX_H - TILE - 1 - i, ROOM_PX_W - 2 * TILE, 1);
        }
        this._bg = c;
        return c;
    };
    Room.prototype.draw_bg = function (cam) {
        ctx.save();
        ctx.imageSmoothingEnabled = false;
        ctx.drawImage(this.bg(), Math.trunc(cam[0]), Math.trunc(cam[1]));
        ctx.restore();
    };
    Room.prototype.draw_doors = function (cam) {
        var ds = this.doors.slice().sort();
        for (var i = 0; i < ds.length; i++) {
            var d = ds[i], dtc = DOOR_TILE[d];
            var px = dtc[0] * TILE + cam[0], py = dtc[1] * TILE + cam[1];
            for (var off of [-1, 1]) {
                var sx = px + ((d === 'N' || d === 'S') ? off * TILE : 0);
                var sy = py + ((d === 'W' || d === 'E') ? off * TILE : 0);
                if (this.open_doors.indexOf(d) >= 0) {
                    ctx.fillStyle = 'rgb(9,10,18)'; ctx.fillRect(sx, sy, TILE, TILE);
                } else {
                    blit('tile_door', sx + TILE / 2, sy + TILE / 2, TILE, TILE);
                }
            }
            if (this.open_doors.indexOf(d) >= 0) {
                // 开启：明暗门洞 + 地面箭头，明确"可通行"
                ctx.fillStyle = 'rgba(6,6,10,0.647)';
                ctx.fillRect(px, py, TILE, TILE);
                var pts;
                if (d === 'N') { pts = [[10, 20], [22, 20], [16, 9]]; }
                else if (d === 'S') { pts = [[10, 12], [22, 12], [16, 23]]; }
                else if (d === 'W') { pts = [[20, 10], [20, 22], [9, 16]]; }
                else { pts = [[12, 10], [12, 22], [23, 16]]; }
                ctx.beginPath();
                ctx.moveTo(px + pts[0][0], py + pts[0][1]);
                ctx.lineTo(px + pts[1][0], py + pts[1][1]);
                ctx.lineTo(px + pts[2][0], py + pts[2][1]);
                ctx.closePath();
                ctx.fillStyle = 'rgba(150,240,200,0.353)';
                ctx.fill();
            } else {
                blit('tile_door', px + TILE / 2, py + TILE / 2, TILE, TILE);
                var pulse = 0.55 + 0.45 * Math.sin(nowMs() / 130.0);
                ctx.fillStyle = 'rgba(255,96,96,' + ((150 + 90 * pulse) / 255) + ')';
                if (d === 'N' || d === 'S') {
                    ctx.fillRect(px + 3, py + 14, TILE - 6, 4);
                } else {
                    ctx.fillRect(px + 14, py + 3, 4, TILE - 6);
                }
            }
        }
    };
    Room.prototype.draw_portal = function (cam, t) {
        if (this.portal === null) { return; }
        var x = this.portal[0] + cam[0], y = this.portal[1] + cam[1];
        var r = 30, i;
        for (i = 0; i < 4; i++) {
            var rr = r * (0.45 + 0.18 * i), a = 60 - i * 10;
            ctx.beginPath();
            ctx.arc(Math.round(x), Math.round(y), rr, 0, TAU);
            ctx.fillStyle = cssColor([150, 110, 255], a / 255);
            ctx.fill();
        }
        for (i = 0; i < 3; i++) {
            var ang = t * (2.4 + i * 0.7) + i * 2.1;
            ctx.beginPath();
            ctx.arc(Math.round(x + Math.cos(ang) * r * 0.78),
                Math.round(y + Math.sin(ang) * r * 0.78),
                Math.max(1, 4 - Math.floor(i / 2)), 0, TAU);
            ctx.fillStyle = cssColor([220, 200, 255], 190 / 255);
            ctx.fill();
        }
        ctx.beginPath();
        ctx.arc(Math.round(x), Math.round(y), Math.max(1, r * 0.30), 0, TAU);
        ctx.lineWidth = 2;
        ctx.strokeStyle = cssColor([196, 160, 255], 220 / 255);
        ctx.stroke();
        drawShadow(x, y + 24, 22, 9, 140);
    };
    Room.prototype.update_portal = function (dt) { this.portal_t += dt; };

    // ==================================================================== 地牢
    var SPAWN_TABLE = {
        1: [['slime', 0.72], ['bomber', 0.28]],
        2: [['slime', 0.44], ['bomber', 0.24], ['drone', 0.32]],
        3: [['slime', 0.28], ['bomber', 0.26], ['drone', 0.46]]
    };
    // 需求 8：每个场景的怪不同（与 Python 版 dungeon.SCENE_SPAWN 同源）
    var SCENE_SPAWN = {
        'crust':    [[['slime', 0.34], ['slug', 0.27], ['crawler', 0.19], ['scatter_raider', 0.20]],
                     [['slime_big', 0.46], ['slug_big', 0.30], ['crawler_big', 0.24]]],
        'sewer':    [[['slug', 0.30], ['drone', 0.27], ['leech', 0.21], ['rifle_raider', 0.22]],
                     [['drone_big', 0.46], ['slug_big', 0.28], ['leech_big', 0.26]]],
        'facility': [[['drone', 0.29], ['bomber', 0.27], ['turret', 0.24], ['beam_raider', 0.20]],
                     [['bomber_big', 0.44], ['drone_big', 0.30], ['turret_big', 0.26]]],
        'core':     [[['spore', 0.28], ['wraith', 0.29], ['frostbite', 0.25], ['beam_raider', 0.18]],
                     [['wraith_big', 0.40], ['spore_big', 0.32], ['spore_big_m', 0.28]]],
        'd_mine':   [[['rockworm', 0.30], ['minebot', 0.27], ['slug', 0.23], ['scatter_raider', 0.20]],
                     [['slime_big_m', 0.40], ['bomber_big', 0.32], ['rockworm_big', 0.28]]],
        'd_lab':    [[['frostbite', 0.27], ['spore', 0.27], ['wraith', 0.24], ['rifle_raider', 0.22]],
                     [['spore_big', 0.40], ['wraith_big', 0.32], ['frostbite_big', 0.28]]],
        'd_gift':   [[['purifier', 0.5], ['sprite', 0.5]], [['guardian_big', 1.0]]]
    };
    var SCENE_BOSS = {
        'crust': 'warlord', 'sewer': 'swarmqueen', 'facility': 'mech',
        'core': 'origin', 'd_mine': 'foreman', 'd_lab': 'specimen',
        'd_gift': 'guardian'
    };
    var SCENE_MINIBOSS = {
        'crust': 'crust_sentinel', 'sewer': 'sewer_serpent',
        'facility': 'facility_smelter', 'core': 'protocol',
        'd_mine': 'mine_excavator', 'd_lab': 'lab_cryowarden',
        'd_gift': 'gift_bloom'
    };
    var ELITE_CHANCE = { 1: 0.08, 2: 0.13, 3: 0.18 };
    var SCENE_ELITE_CHANCE = {
        crust: 0.08, sewer: 0.12, facility: 0.16, core: 0.20,
        d_mine: 0.14, d_gift: 0.12, d_lab: 0.18
    };
    var SCENE_CHEST_BIAS = {
        crust: 0.00, sewer: 0.15, facility: 0.30, core: 0.45,
        d_mine: 0.20, d_gift: 0.30, d_lab: 0.35
    };
    // Count per wave, not per room.
    var ENEMY_COUNT = { 1: [5, 6], 2: [5, 7], 3: [6, 8] };
    var GRID_TARGET = { 1: 8, 2: 9, 3: 10 };
    var DIRS4 = [[1, 0], [-1, 0], [0, 1], [0, -1]];
    var STAGES_PER_SCENE_W = 5;

    function stageKindW(stageIdx) {
        if (stageIdx === 2) { return 'miniboss'; }
        if (stageIdx === 4) { return 'boss'; }
        return 'normal';
    }
    function hasBossFloor(d) {
        var k = stageKindW(d.stage_idx);
        return (k === 'miniboss' || k === 'boss') && d.floor >= FLOORS;
    }
    function bossKindW(d) {
        if (!hasBossFloor(d)) { return null; }
        var k = stageKindW(d.stage_idx);
        if (k === 'miniboss') {
            return SCENE_MINIBOSS[d.scene_key] || SCENE_BOSS[d.scene_key];
        }
        return SCENE_BOSS[d.scene_key];
    }
    function spawnTablesW(d) {
        var spec = SCENE_SPAWN[d.scene_key];
        if (spec && spec[0]) { return spec; }
        return [SPAWN_TABLE[d.floor], []];
    }

    function weighted(rng, table) {
        var total = 0, i;
        for (i = 0; i < table.length; i++) { total += table[i][1]; }
        var p = rng.uniform(0, total), acc = 0.0;
        for (i = 0; i < table.length; i++) {
            acc += table[i][1];
            if (p <= acc) { return table[i][0]; }
        }
        return table[table.length - 1][0];
    }

    function Dungeon(floor, rng, sceneKey, stageIdx, diff, drinkStage, luckBonus) {
        this.floor = Math.max(1, Math.min(FLOORS, Math.floor(floor)));
        this.rng = rng;
        this.scene_key = (sceneKey === undefined) ? null : sceneKey;
        this.stage_idx = Math.floor(stageIdx || 0);
        this.diff = diff || [1.0, 1.0];
        this.drink_stage = !!drinkStage;
        this.luck_bonus = Number(luckBonus || 0);
        this.gw = GRID_W; this.gh = GRID_H;
        this.rooms = {};
        this.start_key = null;
        this.boss_key = null;
        this.goal_key = null;      // 本层目标房：清空后开传送门
        this._generate();
    }
    Dungeon.prototype._idx = function (gx, gy) {
        if (gx < 0 || gy < 0 || gx >= GRID_W || gy >= GRID_H) { return -1; }
        return gy * GRID_W + gx;
    };
    Dungeon.prototype.room = function (gx, gy) {
        var k = this._idx(gx, gy);
        return k < 0 ? null : (this.rooms[k] || null);
    };
    Dungeon.prototype._bfs = function (src) {
        var dm = {};
        var sk = this._idx(src[0], src[1]);
        dm[sk] = 0;
        var q = [src.slice()];
        while (q.length) {
            var c = q.shift();
            var ck = this._idx(c[0], c[1]);
            var r = this.rooms[ck];
            if (!r) { continue; }
            for (var i = 0; i < r.doors.length; i++) {
                var dv = DIR_VEC[r.doors[i]];
                var nk = this._idx(c[0] + dv[0], c[1] + dv[1]);
                if (this.rooms[nk] && dm[nk] === undefined) {
                    dm[nk] = dm[ck] + 1;
                    q.push([c[0] + dv[0], c[1] + dv[1]]);
                }
            }
        }
        return dm;
    };
    Dungeon.prototype.chooseSurveyRoom = function () {
        if (this.scene_key !== 'd_mine' || this.stage_idx !== 1) { return null; }
        var self = this, start = this.start_key, goal = this.goal_key;
        function id(p) { return p[1] * GRID_W + p[0]; }
        function walk(source, blocked, forbidden) {
            var queue = [source], parent = {};
            parent[id(source)] = null;
            while (queue.length) {
                var at = queue.shift(), room = self.room(at[0], at[1]);
                for (var i = 0; i < DIR_LIST.length; i++) {
                    var dir = DIR_LIST[i];
                    if (room.doors.indexOf(dir) < 0) { continue; }
                    var delta = DIR_VEC[dir], next = [at[0] + delta[0], at[1] + delta[1]];
                    if (!self.room(next[0], next[1]) ||
                        (blocked && id(next) === id(blocked)) ||
                        (forbidden && id(next) === id(forbidden)) ||
                        Object.prototype.hasOwnProperty.call(parent, id(next))) { continue; }
                    parent[id(next)] = at;
                    queue.push(next);
                }
            }
            return parent;
        }
        var parent = walk(start), path = {}, key = goal;
        if (!Object.prototype.hasOwnProperty.call(parent, id(goal))) { return null; }
        while (key) { path[id(key)] = key; key = parent[id(key)]; }
        var branch = walk(start, null, goal), candidates = [];
        Object.keys(this.rooms).forEach(function (k) {
            var r = self.rooms[k], at = [r.gx, r.gy];
            if (r.kind !== 'normal' || path[k] ||
                !Object.prototype.hasOwnProperty.call(branch, k) ||
                !Object.prototype.hasOwnProperty.call(walk(start, at), id(goal))) { return; }
            var distance = Math.min.apply(null, Object.keys(path).map(function (p) {
                return Math.abs(at[0] - path[p][0]) + Math.abs(at[1] - path[p][1]);
            }));
            candidates.push([r.doors.length === 1 ? 0 : 1, distance, r.gx, r.gy]);
        });
        candidates.sort(function (a, b) {
            for (var i = 0; i < 4; i++) { if (a[i] !== b[i]) { return a[i] - b[i]; } }
            return 0;
        });
        return candidates.length ? [candidates[0][2], candidates[0][3]] : null;
    };
    Dungeon.prototype.surveyNextDoor = function (source, target) {
        if (!target || (source[0] === target[0] && source[1] === target[1])) { return null; }
        var queue = [[source, null]], seen = {}, self = this;
        seen[source[1] * GRID_W + source[0]] = true;
        while (queue.length) {
            var item = queue.shift(), at = item[0], first = item[1];
            var room = self.room(at[0], at[1]);
            for (var i = 0; i < DIR_LIST.length; i++) {
                var dir = DIR_LIST[i];
                if (room.doors.indexOf(dir) < 0) { continue; }
                var delta = DIR_VEC[dir], next = [at[0] + delta[0], at[1] + delta[1]];
                var key = next[1] * GRID_W + next[0];
                if (!self.room(next[0], next[1]) || seen[key] ||
                    (next[0] === self.goal_key[0] && next[1] === self.goal_key[1])) { continue; }
                if (next[0] === target[0] && next[1] === target[1]) { return first || dir; }
                seen[key] = true; queue.push([next, first || dir]);
            }
        }
        return null;
    };
    Dungeon.prototype._sample_pos = function (occupied, min_d, avoid) {
        for (var tries = 0; tries < 200; tries++) {
            var x = this.rng.uniform(IN_L + 30, IN_R - 30);
            var y = this.rng.uniform(IN_T + 30, IN_B - 30);
            var bad = false, i;
            for (i = 0; i < occupied.length; i++) {
                if (dist(x, y, occupied[i][0], occupied[i][1]) < min_d) { bad = true; break; }
            }
            if (bad) { continue; }
            for (i = 0; i < avoid.length; i++) {
                if (dist(x, y, avoid[i][0], avoid[i][1]) < avoid[i][2]) { bad = true; break; }
            }
            if (bad) { continue; }
            return [x, y];
        }
        return null;
    };
    Dungeon.prototype._generate = function () {
        var rng = this.rng;
        var cx = Math.floor(this.gw / 2), cy = Math.floor(this.gh / 2);
        var start = [cx, cy];
        var target = Math.min(GRID_TARGET[this.floor], this.gw * this.gh - 1);

        // 随机游走铺房间（保证连通：每一步只走向相邻格）
        var cells = {};
        cells[this._idx(cx, cy)] = true;
        var cur = [cx, cy], steps = 0, n = 1;
        while (n < target && steps < 600) {
            steps++;
            var d = rng.choice(DIRS4);
            var nx = cur[0] + d[0], ny = cur[1] + d[1];
            if (nx >= 0 && nx < this.gw && ny >= 0 && ny < this.gh) {
                cur = [nx, ny];
                var nk = this._idx(nx, ny);
                if (!cells[nk]) { cells[nk] = true; n++; }
            }
        }

        var keys = Object.keys(cells).map(Number);
        var door_map = {}, i, j;
        for (i = 0; i < keys.length; i++) {
            var k = keys[i], gx = k % GRID_W, gy = Math.floor(k / GRID_W);
            var s = [];
            for (j = 0; j < DIR_LIST.length; j++) {
                var dd = DIR_LIST[j], v = DIR_VEC[dd];
                if (cells[this._idx(gx + v[0], gy + v[1])]) { s.push(dd); }
            }
            door_map[k] = s;
        }
        for (i = 0; i < keys.length; i++) {
            var kk = keys[i];
            this.rooms[kk] = new Room(kk % GRID_W, Math.floor(kk / GRID_W),
                'normal', door_map[kk], rng, this.floor);
            this.rooms[kk].scene_key = this.scene_key;
        }

        var sk = this._idx(start[0], start[1]);
        this.start_key = [start[0], start[1]];
        this.rooms[sk].kind = 'start';
        this.rooms[sk].cleared = true;

        // BOSS 房 = 离出生点最远的房间
        var dm = this._bfs(start);
        function cmpFar(a, b) {
            var da = dm[a] || 0, db = dm[b] || 0;
            if (db !== da) { return db - da; }
            var ax = a % GRID_W, bx = b % GRID_W;
            if (ax !== bx) { return ax - bx; }
            return Math.floor(a / GRID_W) - Math.floor(b / GRID_W);
        }
        var order = keys.slice().sort(cmpFar);
        var bossIdx = order.length ? order[0] : sk;
        if (bossIdx === sk) {
            var others = keys.filter(function (x) { return x !== sk; });
            bossIdx = others.length ? others[0] : sk;
        }
        // 需求 3/8：只有第 3 关（小 Boss）/ 第 5 关（大 Boss）的最后一层才有首领房
        this.is_boss_floor = hasBossFloor(this);
        // goal_key = 本层目标房：清空后开传送门。
        //   首领层 -> 首领房（走 onBossDefeated）
        //   普通层 -> 最远房（由房间清空判定开传送门）
        // 血泪教训：此前普通层 boss_key = null，导致"打光所有房间
        // 也永远没有传送门"，玩家被困在同一层（与 Python 侧同源 bug）。
        this.goal_key = [bossIdx % GRID_W, Math.floor(bossIdx / GRID_W)];
        if (this.is_boss_floor) {
            this.boss_key = [bossIdx % GRID_W, Math.floor(bossIdx / GRID_W)];
            this.rooms[bossIdx].kind = 'boss';
            this.rooms[bossIdx].cleared = false;
        } else {
            this.boss_key = null;
        }

        // 特殊房按离出生点的距离就近分配
        var rest = keys.filter(function (x) { return x !== sk && x !== bossIdx; });
        rest.sort(function (a, b) {
            var da = dm[a] === undefined ? 99 : dm[a];
            var db = dm[b] === undefined ? 99 : dm[b];
            if (da !== db) { return da - db; }
            var ax = a % GRID_W, bx = b % GRID_W;
            if (ax !== bx) { return ax - bx; }
            return Math.floor(a / GRID_W) - Math.floor(b / GRID_W);
        });
        var specials = ['treasure', 'shop', 'heal'];
        if (this.drink_stage) { specials.push('drink'); }
        for (i = 0; i < rest.length; i++) {
            if (i < specials.length) {
                this.rooms[rest[i]].kind = specials[i];
                this.rooms[rest[i]].cleared = true;
            }
        }
        for (i = 0; i < keys.length; i++) { this._plan_room(this.rooms[keys[i]]); }
    };
    Dungeon.prototype._plan_room = function (r) {
        var rng = this.rng, f = this.floor, i;
        var avoid = [];
        for (var kk in ENTRY_FROM) {
            if (ENTRY_FROM.hasOwnProperty(kk)) {
                var e = ENTRY_FROM[kk];
                avoid.push([e[0], e[1], 96.0]);
            }
        }
        // 中心区域也不要堆怪，给玩家反应空间
        avoid.push([ROOM_CX, ROOM_CY, 46.0]);
        var occupied = [];

        if (r.kind === 'normal' || r.kind === 'boss') {
            r.wave_plans = [[], [], []];
            var tbls = spawnTablesW(this);
            var smallTbl = tbls[0], eliteTbl = tbls[1] || [];
            var bossPos = [ROOM_CX, IN_T + 92];
            for (var waveIndex = 0; waveIndex < 3; waveIndex++) {
                var waveOccupied = [];
                var bossWave = r.kind === 'boss' && waveIndex === 2;
                var waveCount = rng.randint(ENEMY_COUNT[f][0], ENEMY_COUNT[f][1]) - (bossWave ? 1 : 0);
                var waveAvoid = bossWave ? avoid.concat([[bossPos[0], bossPos[1], 62.0]]) : avoid;
                for (i = 0; i < waveCount; i++) {
                    var pos = this._sample_pos(waveOccupied, 42.0, waveAvoid);
                    if (!pos) { throw new Error('Unable to place a complete combat wave'); }
                    waveOccupied.push(pos);
                    occupied.push(pos);
                    var eliteP = (SCENE_ELITE_CHANCE[this.scene_key] !== undefined)
                        ? SCENE_ELITE_CHANCE[this.scene_key] : ELITE_CHANCE[f];
                    var elite = rng.random() < eliteP;
                    var table = elite && eliteTbl.length ? eliteTbl : smallTbl;
                    var spawn = [weighted(rng, table), pos[0], pos[1], elite];
                    r.wave_plans[waveIndex].push(spawn);
                    r.spawn_plan.push(spawn);
                }
                if (bossWave) {
                    var bkey = bossKindW(this) || SCENE_BOSS[this.scene_key] || 'boss';
                    var bossSpawn = [bkey, bossPos[0], bossPos[1], false];
                    r.wave_plans[waveIndex].push(bossSpawn);
                    r.spawn_plan.push(bossSpawn);
                }
            }
            // 隐藏奖励怪（需求 8）
            if (r.kind === 'normal' && this.scene_key !== 'd_gift') {
                var roll = rng.random();
                if (roll < 0.035) {
                    var p2 = this._sample_pos(r.wave_plans[0].map(function (sp) { return [sp[1], sp[2]]; }), 42.0, avoid);
                    if (p2) {
                        occupied.push(p2);
                        var mimicSpawn = ['mimic', p2[0], p2[1], false];
                        r.spawn_plan.push(mimicSpawn);
                        r.wave_plans[0].push(mimicSpawn);
                        r.rare_mob = 'mimic';
                    }
                } else if (roll < 0.055) {
                    var p3 = this._sample_pos(r.wave_plans[0].map(function (sp) { return [sp[1], sp[2]]; }), 42.0, avoid);
                    if (p3) {
                        occupied.push(p3);
                        var wandererSpawn = ['wanderer', p3[0], p3[1], false];
                        r.spawn_plan.push(wandererSpawn);
                        r.wave_plans[0].push(wandererSpawn);
                        r.rare_mob = 'wanderer';
                    }
                } else if (roll < 0.085) {
                    var p4=this._sample_pos(r.wave_plans[0].map(function(sp){return [sp[1],sp[2]];}),42.0,avoid);
                    if(p4){
                        var luckySpawn=['lucky_treasure',p4[0],p4[1],false];
                        r.spawn_plan.push(luckySpawn);r.wave_plans[0].push(luckySpawn);
                        r.rare_mob='lucky_treasure';
                    }
                }
            }
        }

        if (r.kind === 'boss') {
            // Boss and guards were added to the third wave above.
        } else if (r.kind === 'treasure') {
            // 需求 7：宝箱分 5 类 × 2 档，越深越容易出极品
            var cbias = 0.10 * Math.max(0, f - 1) +
                (SCENE_CHEST_BIAS[this.scene_key] || 0.0) +
                (this.luck_bonus || 0);
            var cpick = D.rollChest(rng, cbias);
            r.pickup_plan.push({
                x: ROOM_CX, y: ROOM_CY, kind: 'chest',
                ckey: cpick[0], ctier: cpick[1]
            });
        } else if (r.kind === 'heal') {
            r.pickup_plan.push({ x: ROOM_CX - 34, y: ROOM_CY, kind: 'heart', value: 2 });
            r.pickup_plan.push({ x: ROOM_CX + 34, y: ROOM_CY, kind: 'heart', value: 2 });
            r.pickup_plan.push({ x: ROOM_CX, y: ROOM_CY + 48, kind: 'energy', value: 40 });
        } else if (r.kind === 'shop') {
            var shopKeys = rollShopWeapons(rng, this.scene_key, 2);
            var key = shopKeys[0], key2 = shopKeys[1];
            r.pickup_plan.push({ x: ROOM_CX - 66, y: ROOM_CY - 28,
                kind: 'shop_weapon', wkey: key, price: wget(key).price + 20 });
            r.pickup_plan.push({ x: ROOM_CX + 66, y: ROOM_CY - 28,
                kind: 'shop_weapon', wkey: key2, price: wget(key2).price + 20 });
            r.pickup_plan.push({ x: ROOM_CX - 66, y: ROOM_CY + 42,
                kind: 'shop_hp_potion', price: 45 });
            r.pickup_plan.push({ x: ROOM_CX + 66, y: ROOM_CY + 42,
                kind: 'shop_energy_potion', price: 35 });
        } else if (r.kind === 'drink') {
            [['nectar', -76, -32, 180], ['dew', 76, -32, 140],
                ['soda', -76, 48, 160], ['tea', 76, 48, 180]].forEach(function (item) {
                r.pickup_plan.push({ x: ROOM_CX + item[1], y: ROOM_CY + item[2],
                    kind: 'drink', ckey: item[0], price: item[3] });
            });
        }

        // 可破坏道具：远离门、远离房间中心，绝不堵路
        var prop_avoid = avoid.concat([[ROOM_CX, ROOM_CY, 74.0]]);
        r.pickup_plan.forEach(function (p) { prop_avoid.push([p.x, p.y, 42]); });
        var nprops = r.kind === 'boss' ? 2 : rng.randint(0, r.kind === 'normal' ? 3 : 2);
        for (i = 0; i < nprops; i++) {
            var p = this._sample_pos(occupied, 46.0, prop_avoid);
            if (!p) { break; }
            occupied.push(p);
            r.prop_plan.push([r.kind !== 'normal' && r.kind !== 'boss' ? 'crate' :
                (rng.random() < 0.62 ? 'crate' : 'barrel'), p[0], p[1]]);
        }

        // ---- 需求 3：陷阱 / 掩体 / 奖励洞穴
        if (this.scene_key !== null && (r.kind === 'normal' || r.kind === 'boss')) {
            r.hazard_plan = planScene(rng, this.scene_key, this.stage_idx, this.diff);
            r.hazard_plan.strips = planSpeedStrips(rng, r.hazard_plan);
            // 掩体占位纳入 occupied，避免与箱子叠在一起
            for (i = 0; i < r.hazard_plan.covers.length; i++) {
                occupied.push([r.hazard_plan.covers[i][1], r.hazard_plan.covers[i][2]]);
            }
        }
    };
    Dungeon.prototype.map_cells = function () {
        return Object.keys(this.rooms).map(Number).sort(function (a, b) {
            var ay = Math.floor(a / GRID_W), by = Math.floor(b / GRID_W);
            if (ay !== by) { return ay - by; }
            return (a % GRID_W) - (b % GRID_W);
        });
    };

    // ==================================================================== HUD
    var CHAR_SKILLS = {
        scout: {name:'地形脉冲', cd:12, color:[104,222,245], radius:105, desc:'回复48能量，并释放双层侦查脉冲'},
        engineer: {name:'过载电圈', cd:15, color:[255,185,94], radius:112, desc:'回复35能量，电圈击伤近处怪物'},
        ranger: {name:'猎手齐射', cd:13, color:[155,245,132], radius:190, desc:'向瞄准方向挥出远距离扇形箭雨'},
        medic: {name:'紧急救护', cd:18, color:[255,132,172], radius:92, desc:'回复6生命，短暂免疫伤害'},
        ghost: {name:'虚影闪避', cd:16, color:[188,143,255], radius:80, desc:'获得2.5秒无敌并重置冲刺'},
        prime: {name:'协议震荡', cd:19, color:[255,226,132], radius:145, desc:'回复20能量，释放强力范围震荡'},
        archivist: {name:'索引锁定', cd:14, color:[126,214,255], radius:245, desc:'回复30能量，锁定最近目标攻击'},
        seedkeeper: {name:'生命花环', cd:17, color:[163,235,125], radius:110, desc:'回复4生命，花环击伤近处怪物'}
    };
    function mobileUI() { return !!(window.__TOUCH__ && window.__TOUCH__.enabled); }
    var HEART_FULL = [[226, 62, 74], [255, 138, 146]];
    var HEART_EMPTY = [62, 52, 62];

    function drawHeart(x, y, state, size) {
        size = size || 13;
        var r = size;
        function shape(col) {
            ctx.fillStyle = cssColor(col);
            ctx.beginPath();
            ctx.arc(x + r / 3, y + r / 3, r / 3 + 1, 0, TAU);
            ctx.fill();
            ctx.beginPath();
            ctx.arc(x + 2 * r / 3, y + r / 3, r / 3 + 1, 0, TAU);
            ctx.fill();
            ctx.beginPath();
            ctx.moveTo(x, y + r / 2);
            ctx.lineTo(x + r, y + r / 2);
            ctx.lineTo(x + r / 2, y + r);
            ctx.closePath();
            ctx.fill();
        }
        shape(HEART_EMPTY);
        if (state > 0) {
            if (state === 1) {
                ctx.save();
                ctx.beginPath();
                ctx.moveTo(x, y);
                ctx.lineTo(x + r / 2 + 1, y);
                ctx.lineTo(x + r / 2 + 1, y + r + 2);
                ctx.lineTo(x, y + r + 2);
                ctx.closePath();
                ctx.clip();
            }
            shape(HEART_FULL[0]);
            if (state === 1) { ctx.restore(); }
            ctx.beginPath();
            ctx.arc(x + r / 3, y + r / 3, Math.max(1, r / 8), 0, TAU);
            ctx.fillStyle = cssColor(HEART_FULL[1]);
            ctx.fill();
        }
    }

    // 需求：污染渐近减益指示器（左下角武器面板下方）
    function drawPollution(game) {
        var p = game.pollution;
        if (!p) { return; }
        // 1.3：显示抗性折减后的实际值
        var pur = game._pur ||
            [p.hp_cut, p.spd, p.regen, p.drain];
        var lines = [];
        if (pur[0] > 0) { lines.push('生命-' + pur[0]); }
        if (pur[1] < 0.999) {
            lines.push('移速-' + Math.round((1.0 - pur[1]) * 100) + '%');
        }
        if (pur[2] < 0.999) {
            lines.push('回能-' + Math.round((1.0 - pur[2]) * 100) + '%');
        }
        if (pur[3] > 0) { lines.push('侵蚀' + pur[3].toFixed(2) + '/s'); }
        if (!lines.length) { return; }
        var x = 10, y = mobileUI() ? 104 : VIEW_H - 74, w = 176;
        var resist = 0.0;
        if (p.drain > 0) {
            resist = 1.0 - (pur[3] / p.drain);
        } else if (p.hp_cut > 0) {
            resist = 1.0 - (pur[0] / p.hp_cut);
        }
        resist = Math.max(0.0, Math.min(1.0, resist));
        // 抗性徽标（1.3）：堆了抗污染才显示
        if (resist > 0.01) {
            var badge = '抗' + Math.round(resist * 100) + '%';
            panel(x + 19, y - 12, measure(badge, 10) + 6, 11,
                  [22, 46, 40, 220], [120, 230, 190], 3);
            txt(badge, 10, [140, 240, 200], x + 22, y - 11);
        }
        panel(x, y, w, 18, [34, 16, 26, 200], [150, 60, 84], 4);
        var col = p.pct >= 60 ? [255, 150, 170] : [240, 180, 120];
        txt('污染 ' + p.pct + '%', 10, col, x + 5, y + 3);
        txt(lines.join(' '), 10, [222, 176, 190], x + w - 5, y + 3, 'right');
        bar(x + 2, y + 15, w - 4, 2, Math.min(1.0, p.pct / 100.0),
            [226, 90, 120], [44, 22, 30]);
    }

    function drawMinimap(game) {
        var dg = game.dungeon;
        var cell = 10, gap = 2;
        var w = dg.gw * (cell + gap) + 8;
        var h = dg.gh * (cell + gap) + 20;
        var x0 = VIEW_W - w - 8, y0 = mobileUI() ? 74 : VIEW_H - h - 8;
        panel(x0, y0, w, h, [20, 19, 28, 215], C_PANEL_HI, 5);
        txt('地图', 10, C_TEXT_DIM, x0 + 5, y0 + 4);
        var cur = [game.room.gx, game.room.gy];
        for (var key in dg.rooms) {
            if (!dg.rooms.hasOwnProperty(key)) { continue; }
            var idx = Number(key);
            var gx = idx % GRID_W, gy = Math.floor(idx / GRID_W);
            var r = dg.rooms[key];
            var visible = r.visited, near = false;
            if (!visible) {
                for (var j = 0; j < DIR_LIST.length; j++) {
                    var v = DIR_VEC[DIR_LIST[j]];
                    var nb = dg.room(gx + v[0], gy + v[1]);
                    if (nb && nb.visited) { near = true; break; }
                }
            }
            if (!(visible || near)) { continue; }
            var cx = x0 + 4 + gx * (cell + gap);
            var cy = y0 + 16 + gy * (cell + gap);
            var col;
            if (r.kind === 'start') { col = ROOM_COLOR.start; }
            else if (r.cleared || r.kind === 'treasure' || r.kind === 'heal' || r.kind === 'shop' || r.kind === 'drink') {
                col = ROOM_COLOR[r.kind] || ROOM_COLOR.cleared;
                if (r.kind === 'normal') { col = ROOM_COLOR.cleared; }
            } else {
                col = ROOM_COLOR[r.kind] || ROOM_COLOR.normal;
            }
            if (!visible) { col = [58, 56, 70]; }
            ctx.fillStyle = cssColor(col);
            rrect(cx, cy, cell, cell, 2);
            ctx.fill();
            if (game.route_state === 'survey' && game.route_room &&
                game.route_room[0] === gx && game.route_room[1] === gy && (visible || near)) {
                ctx.strokeStyle = game.route_sealed ? '#b6e5c6' : '#f3b85b';
                ctx.lineWidth = 2;
                ctx.strokeRect(cx - 2, cy - 2, cell + 4, cell + 4);
                if (game.route_sealed) { txt('✓', 12, [182, 229, 198], cx, cy - 2); }
            }
            if (visible && (r.kind === 'boss' || r.kind === 'treasure' || r.kind === 'shop' || r.kind === 'drink')) {
                var oc = r.kind === 'boss' ? [255, 220, 255] :
                    (r.kind === 'treasure' ? [255, 240, 180] :
                    (r.kind === 'drink' ? [255, 214, 170] : [200, 255, 220]));
                ctx.strokeStyle = cssColor(oc);
                ctx.lineWidth = 1;
                rrect(cx, cy, cell, cell, 2);
                ctx.stroke();
            }
            if (visible && r.portal !== null) {
                ctx.beginPath();
                ctx.arc(cx + cell / 2, cy + cell / 2, 7, 0, TAU);
                ctx.strokeStyle = 'rgb(112,62,190)'; ctx.lineWidth = 2; ctx.stroke();
                ctx.beginPath();
                ctx.arc(cx + cell / 2, cy + cell / 2, 4, 0, TAU);
                ctx.strokeStyle = 'rgb(250,213,255)'; ctx.lineWidth = 2; ctx.stroke();
                ctx.fillStyle = 'rgb(255,255,255)';
                ctx.fillRect(cx + 5, cy + 5, 1, 1);
            }
            // 已探明但锁着的房间打叉
            if (visible && !r.cleared && (r.kind === 'normal' || r.kind === 'boss')) {
                ctx.strokeStyle = 'rgb(10,10,14)';
                ctx.lineWidth = 1;
                ctx.beginPath();
                ctx.moveTo(cx + 1, cy + 1);
                ctx.lineTo(cx + cell - 1, cy + cell - 1);
                ctx.moveTo(cx + cell - 1, cy + 1);
                ctx.lineTo(cx + 1, cy + cell - 1);
                ctx.stroke();
            }
        }
        var blink = Math.floor(nowMs() / 260) % 2 === 0;
        var pcx = x0 + 4 + cur[0] * (cell + gap);
        var pcy = y0 + 16 + cur[1] * (cell + gap);
        ctx.strokeStyle = blink ? 'rgb(255,255,255)' : 'rgb(170,170,190)';
        ctx.lineWidth = 1;
        rrect(pcx - 1, pcy - 1, cell + 2, cell + 2, 2);
        ctx.stroke();
    }

    function drawBossBar(game) {
        var b = game.boss;
        if (!b || !b.alive || b.state === 'intro') { return; }
        var w = 270, h = 10;
        var x = 184, y = 23;
        panel(x - 6, 4, w + 12, h + 24, [18, 14, 24, 225], [150, 90, 180], 6);
        txt(b.boss_name || '首领', 12, C_BOSS, x + 2, 6);
        ctx.fillStyle = cssColor([48, 30, 50]);
        rrect(x, y, w, h, 3);
        ctx.fill();
        var fw = Math.floor(w * b.hp_ratio());
        if (fw > 0) {
            ctx.fillStyle = cssColor([198, 84, 220]);
            rrect(x, y, fw, h, 3);
            ctx.fill();
            ctx.fillStyle = cssColor([255, 170, 250]);
            rrect(x, y, fw, 3, 2);
            ctx.fill();
        }
        var seps = [0.33, 0.66];
        for (var i = 0; i < seps.length; i++) {
            ctx.fillStyle = 'rgb(22,16,26)';
            ctx.fillRect(Math.round(x + w * seps[i]), y, 1, h);
        }
        ctx.strokeStyle = cssColor([90, 60, 110]);
        ctx.lineWidth = 1;
        rrect(x, y, w, h, 3);
        ctx.stroke();
        var hpTxt = Math.max(0, Math.floor(b.hp)) + ' / ' + Math.floor(b.max_hp);
        txt(hpTxt, 10, C_TEXT_DIM, x + w - textWidth(hpTxt, 10) - 2, 7);
    }

    function drawPrompt(game) {
        var p = game.prompt;
        if (!p) { return; }
        var s = p.promptText();
        if (!s) { return; }
        var w = textWidth(s, 12) + 20;
        var x = VIEW_W / 2 - w / 2, y = VIEW_H - 84;
        // 避开左下武器面板（176 宽 + 10 边距）
        if (x < 10 + 176 + 8) { x = 10 + 176 + 8; }
        if (x + w > VIEW_W - 8) { x = Math.max(8, VIEW_W - 8 - w); }
        var col = (p.kind === 'weapon' || p.kind === 'shop_weapon')
            ? (((D.QUALITIES || {})[p.quality] || {}).color || C_TEXT) : C_TEXT;
        panel(x, y, w, 24, [24, 22, 32, 235], col, 5);
        txt(s, 12, col, x + 10, y + 5);
    }

    function drawRouteChoice(game) {
        dim(205, [6, 8, 12]);
        panel(108, 47, 424, 270, [25, 27, 36, 245], [243, 184, 91], 8);
        txt('旧厂勘测记录 · 第 2 关', 20, [243, 184, 91], 128, 59);
        txt('检修工单 02：隔离区阀门已关闭。', 12, C_TEXT, 128, 89);
        txt('沿警示线进入，取样后撤离。', 12, C_TEXT, 128, 107);
        var rows = [137, 188];
        for (var i = 0; i < 2; i++) {
            ctx.strokeStyle = i === game.route_index ? '#f3b85b' : '#555865';
            ctx.lineWidth = 2; ctx.strokeRect(130, rows[i], 380, 43);
        }
        txt('常规通行 · 直接前往目标房', 15, C_TEXT, 142, 145);
        txt('高危勘测 · 额外战斗 1 间 / 3 波', 15, [243, 184, 91], 142, 196);
        txt('绕路可能消耗生命与能量；可在出口放弃。', 11, C_TEXT_DIM, 142, 235);
        var claimed = (game.profile && game.profile.route_first_rewards || []).indexOf('mine_survey_02') >= 0;
        txt(claimed ? '首奖已领取；保留原房掉落' : '首次完成并通关：污染结晶 ×2',
            11, [182, 229, 198], 142, 256);
        txt(mobileUI() ? '点选路线；返回默认常规通行' : '↑↓ 选择  Enter 确认  Esc 常规通行',
            11, C_TEXT_DIM, 156, 283);
    }
    function drawHUD(game) {
        var pl = game.player, i;
        // ---------------- 左上：红心 + 能量
        // 能量条宽度随红心数量伸缩，数字紧跟条尾；避免像原来那样写死 x=164
        // 在红心多 / 能量三位数时顶到中间的场景横幅上。
        var hp = Math.max(0, Math.ceil(pl.hp - 1e-6));
        var total = Math.max(1, Math.ceil(pl.max_hp / 2));
        var ebarW = 120;
        var hudW = 160;
        panel(5, 4, hudW, 38, [16, 15, 24, 185], [64, 60, 86], 5, 1);
        if (total <= 8) {
            for (i = 0; i < total; i++) {
                var state = hp >= (i + 1) * 2 ? 2 : (hp === i * 2 + 1 ? 1 : 0);
                drawHeart(10 + i * 15, 8, state);
            }
        } else {
            drawHeart(10, 8, hp > 0 ? 2 : 0);
            bar(28, 10, 92, 10, pl.hp / Math.max(1.0, pl.max_hp),
                [226, 62, 74], [48, 22, 28], [120, 48, 56]);
            txt(hp + '/' + Math.ceil(pl.max_hp), 11, [255, 226, 226], 124, 9);
        }
        bar(10, 28, ebarW, 8, pl.energy / Math.max(1.0, pl.max_energy),
            C_ENERGY, [26, 34, 44], [60, 90, 110]);
        txt(String(Math.floor(pl.energy)), 11, C_ENERGY, 10 + ebarW + 5, 26);

        // ---------------- 右上：金币 / 层数 / 击杀（全部右对齐）
        var rgt = VIEW_W - (mobileUI() ? 62 : 10);
        var coinTxt = String(game.coins);
        var cw = textWidth(coinTxt, 16);
        blit('coin', rgt - cw - 22 + 9, 6 + 9, 18, 18);
        txt(coinTxt, 16, C_GOLD, rgt - cw, 6);
        var lvTxt = '第 ' + (Math.floor((game.level_state || {}).stage_idx || 0) + 1) + ' / 5 关';
        txt(lvTxt, 12, C_TEXT_DIM, rgt - textWidth(lvTxt, 12), 30);
        var kTxt = '击杀 ' + game.kills;
        txt(kTxt, 12, C_TEXT_DIM, rgt - textWidth(kTxt, 12), 46);
        if ((game.combo_count || 0) >= 2 && (game.combo_t || 0) > 0) {
            var cLabel = game.combo_count >= 8 ? ('×' + game.combo_count + ' 势不可挡') : ('×' + game.combo_count + ' 连杀');
            var cCol = game.combo_count >= 8 ? [255, 138, 90] : [255, 224, 96];
            var ctw = textWidth(cLabel, 12) + 12;
            ctx.save();
            ctx.globalAlpha = Math.min(1.0, game.combo_t / 0.6);
            panel(rgt - ctw, 64, ctw, 18, [26, 20, 32, 210], cCol, 4, 1);
            txt(cLabel, 12, cCol, rgt - ctw + 6, 66);
            ctx.restore();
        }

        // ---------------- 左下：武器面板
        var px = 10, py = mobileUI() ? 54 : VIEW_H - 56;
        var wQual = pl.wq ? pl.wq(game) : 'white';
        var qColor = ((D.QUALITIES || {})[wQual] || {}).color || C_PANEL_HI;
        panel(px, py, 232, 48, [26, 24, 34, 220], qColor, 6);
        var spec = pl.spec();
        var qspec = pl.wqSpec ? pl.wqSpec(game) : spec;
        var dmul = (1.0 + (pl.dmgBonus ? pl.dmgBonus(game) : 0.0)) * (pl.wmul ? pl.wmul(game) : 1.0);
        var dmgVal = Math.max(1, Math.round((qspec.dmg || spec.dmg || 1) * dmul));
        var dmgTxt = (qspec.count || 1) > 1 ? ('伤 ' + dmgVal + '×' + qspec.count) : ('伤 ' + dmgVal);
        var spdMul = pl.attackSpeedMul ? pl.attackSpeedMul(game) : 1.0;
        var aps = spdMul / Math.max(0.01, spec.cd || 0.25);
        var spdTxt = '速 ' + aps.toFixed(1) + '/s';
        var critPct = Math.round((pl.critChance ? pl.critChance(game) : 0.08) * 100);
        var critTxt = '暴 ' + critPct + '%';
        blit(D.spriteKey(spec.key), px + 6 + 15, py + 8 + 15, 30, 30);
        txt(spec.name, 12, C_TEXT, px + 42, py + 4);
        var cost = spec.cost <= 0 ? '不耗能' : '耗 ' + Math.floor(spec.cost);
        var costW = textWidth(cost, 10);
        txt(cost, 10, spec.cost <= 0 ? C_TEXT_DIM : C_ENERGY, px + 226 - costW, py + 5);
        txt(dmgTxt, 10, [255, 196, 120], px + 42, py + 23);
        var dw = textWidth(dmgTxt, 10);
        txt(spdTxt, 10, [120, 224, 245], px + 42 + dw + 7, py + 23);
        var sw = textWidth(spdTxt, 10);
        txt(critTxt, 10, [255, 224, 96], px + 42 + dw + sw + 14, py + 23);
        if (pl.wkey2) {
            txt((mobileUI() ? '换：' : 'Q 换：') + wget(pl.wkey2).name,
                11, [175, 215, 235], px + 240, py + 15);
        }
        if (game.fire_cool > 0) {
            bar(px + 6, py + 41, 220, 3,
                1.0 - game.fire_cool / Math.max(0.01, spec.cd), C_ACCENT, [40, 38, 52]);
        }
        var skill = CHAR_SKILLS[game.char_key] || CHAR_SKILLS.scout;
        txt((mobileUI() ? '技 ' : 'X ') + skill.name + '  ' +
            (game.char_skill_cd <= 0 ? '可用' : game.char_skill_cd.toFixed(1) + 's'),
            11, game.char_skill_cd <= 0 ? skill.color : C_TEXT_DIM,
            mobileUI() ? 10 : 240, mobileUI() ? 129 : VIEW_H - 34);

        // ---------------- 需求：污染渐近减益指示
        drawPollution(game);

        drawMinimap(game);
        if (game.route_state === 'survey') {
            txt(game.route_sealed ? '✓ 样本已封存' : '▨ 高危勘测', 11,
                game.route_sealed ? [182, 229, 198] : [243, 184, 91],
                VIEW_W - 170, 65);
        }
        drawBossBar(game);
        drawPrompt(game);

        // ---------------- 房间名横幅
        // y=44 是"场景名"、y=62 是"房间名"，两行错开；
        // 右上角资源占 0..58，所以横幅必须落在 58 以下才不打架。
        if (game.banner_t > 0) {
            var t = Math.min(1.0, game.banner_t / 1.6);
            ctx.globalAlpha = Math.min(1.0, t * 2.2);
            panel(VIEW_W / 2 - 160, 58, 320, 28, [14, 13, 22, 195], [88, 82, 120], 4, 1);
            txt(game.banner_text, 20, C_TEXT, VIEW_W / 2, 62, 'midtop');
            ctx.globalAlpha = 1;
        }

        // ---------------- 新手操作提示
        if (game.hint_t > 0 && game.floor === 1) {
            ctx.globalAlpha = Math.min(1.0, game.hint_t) * (190 / 255);
            txt(mobileUI() ? '左侧摇杆移动   右侧触点瞄准   射 / 冲 / 交互 / 换 / 技 / 暂停' :
                'WASD 移动   鼠标瞄准   左键射击   Shift 冲刺   E 交互   X 技能   ESC 暂停',
                11, C_TEXT_DIM, (192 + VIEW_W - 8) / 2, VIEW_H - 20, 'midtop');
            ctx.globalAlpha = 1;
        }
        // 局内关卡提示：进关后前几秒显示一次场景 / 小关 / 房间进度
        if (game.hint_t > 9.0 && game.level_state && game.level_state.scene) {
            var lsc = game.level_state;
            var sinfo = D.sceneInfo(lsc.scene);
            var sline = (sinfo.name || lsc.scene) + '  ·  ' +
                D.sceneStageName(Math.floor(lsc.stage_idx || 0)) +
                '  ·  房间 ' + game.floor + '/' + FLOORS;
            ctx.globalAlpha = Math.min(1.0, (game.hint_t - 9.0) / 3.0) * (200 / 255);
            txt(sline, 12, [245, 232, 180], VIEW_W / 2, 44, 'midtop');
            ctx.globalAlpha = 1;
        }
    }

    function drawFlash(game) {
        if (game.fx.flash > 0.01) {
            var c = game.fx.flash_color;
            ctx.fillStyle = cssColor(c, Math.min(200, game.fx.flash * 420) / 255);
            ctx.fillRect(0, 0, VIEW_W, VIEW_H);
        }
    }
    function drawTransition(game) {
        if (game.trans_fade > 0) {
            var t = game.trans_fade / 0.30;
            ctx.fillStyle = 'rgba(8,7,12,' + (Math.min(255, 235 * t) / 255) + ')';
            ctx.fillRect(0, 0, VIEW_W, VIEW_H);
        }
    }

    // ---- 界面：标题 / 帮助 / 暂停 / 结算 / 通关 / 退出
    function drawTitle(game) {
        blit('bg_title', VIEW_W / 2, VIEW_H / 2, VIEW_W, VIEW_H);
        dim(66, [6, 6, 12]);
        var t = nowMs() / 1000.0;
        var bob = Math.sin(t * 1.8) * 3;
        txt('余烬禁区', 40, [255, 226, 150], VIEW_W / 2, 44 + bob, 'midtop');
        txt('ASHEN EXCLUSION ZONE   ·   v4.0', 13, [200, 150, 240],
            VIEW_W / 2, 92 + bob, 'midtop');
        var items = game.menu_items;
        for (var i = 0; i < items.length; i++) {
            var sel = (i === game.menu_index);
            var y = 168 + i * 34;
            var size = sel ? 18 : 16;
            var col = sel ? [255, 236, 170] : [176, 172, 196];
            var w = textWidth(items[i][0], size);
            var x = VIEW_W / 2 - w / 2;
            if (sel) {
                ctx.fillStyle = cssColor([120, 90, 200], 70 / 255);
                ctx.fillRect(x - 20, y - 5, w + 40, 28);
                txt('▶', size, [255, 210, 120], x - 22, y - 2);
            }
            txt(items[i][0], size, col, x, y - 2);
        }
        txt(mobileUI() ? '点击菜单项继续' : '↑↓ 选择    Enter 确认    鼠标点击亦可',
            11, [140, 136, 160],
            VIEW_W / 2, VIEW_H - 26, 'midtop');
        if (game.best_floor > 0) {
            txt('最佳记录：第 ' + game.best_floor + ' 层   最高击杀 ' + game.best_kills,
                11, [150, 210, 180], VIEW_W / 2, VIEW_H - 44, 'midtop');
        }
        // 需求 18：右下角更新日志入口
        var lbl = '更新日志 v4.0';
        var bw = textWidth(lbl, 11) + 18;
        var bx = VIEW_W - 12 - bw, by = VIEW_H - 30;
        ctx.fillStyle = cssColor([28, 24, 36], 210 / 255);
        ctx.fillRect(bx, by, bw, 20);
        ctx.strokeStyle = cssColor([110, 100, 140], 1.0);
        ctx.lineWidth = 1;
        ctx.strokeRect(bx, by, bw, 20);
        txt(lbl, 11, [200, 190, 230], bx + 9, by + 3);
    }

    // 需求 12/15：设置项 = [显示名, 设置键, 类型]
    var JOY_MODES = ['float', 'fixed'];
    var JOY_MODE_CN = { float: '浮动', fixed: '固定' };
    function settingRows(game) {
        var st = game.setting || {};
        return [[
            ['程序合成音乐', 'music', 'bool'],
            ['打击音效', 'sfx', 'bool'],
            ['屏幕震动', 'shake', 'bool'],
            ['受击震动（手机端）', 'vibrate', 'bool'],
            ['摇杆模式', 'joystick', 'mode'],
            ['摇杆灵敏度', 'joy_sens', 'num'],
            ['攻击摇杆灵敏度（手机）', 'aim_sens', 'num'],
            ['辅助瞄准（手机）', 'aim_assist', 'bool'],
            ['按键大小', 'button_scale', 'num'],
            ['按键透明度', 'button_opacity', 'num'],
            ['显示帧率', 'show_fps', 'bool']
        ], st];
    }
    function settingValueText(key, typ, st) {
        if (typ === 'bool') { return st[key] ? '开' : '关'; }
        if (typ === 'mode') { return JOY_MODE_CN[st[key] || 'float'] || '浮动'; }
        if (typ === 'num') {
            var v = parseFloat(st[key]);
            return isNaN(v) ? '1.0' : v.toFixed(1);
        }
        return String(st[key] === undefined ? '' : st[key]);
    }

    function drawHelp(game) {
        dim(205, [6, 6, 12]);
        txt('操作说明 / 设置', 22, C_TEXT, VIEW_W / 2, 12, 'midtop');
        var lines = mobileUI() ? [
            ['左侧摇杆', '八方向移动'],
            ['右侧攻击摇杆', '拖动瞄准，按住连续攻击'],
            ['辅助瞄准', '可在设置中开启，靠近目标时微调'],
            ['冲', '短暂冲刺与闪避'],
            ['交互', '开箱、购买、进入传送门'],
            ['换 / 技', '切换武器 / 使用角色技能'],
            ['暂停', '打开暂停菜单'],
            ['点击设置', '直接调整对应选项']
        ] : [
            ['W A S D  /  方向键', '八方向移动'],
            ['鼠标移动', '瞄准（角色朝鼠标方向）'],
            ['鼠标左键 / 空格', '射击（可长按连射）'],
            ['Shift / 右键', '冲刺翻滚（短无敌）'],
            ['E / F', '交互（开宝箱、买东西、换武器）'],
            ['X / 技', '角色专属技能'],
            ['ESC / P', '暂停 / 返回'],
            ['F11', '全屏切换'],
            ['M', '静音切换']
        ];
        var y = 44, i;
        for (i = 0; i < lines.length; i++) {
            txt(lines[i][0], 12, [255, 226, 150], 30, y);
            txt(lines[i][1], 12, C_TEXT_DIM, 196, y);
            y += 20;
        }
        if (window.__NATIVE_SAVE__ && window.__NATIVE_SAVE__.error) {
            txt('原生存档异常，请导出备份', 11, [255, 130, 100], 30, 264);
        }
        // ---- 右侧：可交互设置（↑↓ 选择，Enter/←→ 调整）
        var sr = settingRows(game);
        var rows = sr[0], st = sr[1];
        var sel = ((game.setting_index || 0) % rows.length + rows.length) % rows.length;
        var x0 = 372;
        txt('设 置', 13, [255, 236, 170], x0, 44);
        for (i = 0; i < rows.length; i++) {
            var on = (i === sel), yy = 70 + i * 21;
            var col = on ? [255, 236, 170] : [176, 172, 196];
            if (on) {
                ctx.fillStyle = cssColor([120, 90, 200], 70 / 255);
                ctx.fillRect(x0 - 6, yy - 3, 236, 19);
            }
            txt((on ? '> ' : '  ') + rows[i][0], 12, col, x0, yy);
            var val = settingValueText(rows[i][1], rows[i][2], st);
            var vcol = (val === '开') ? [150, 230, 180]
                : (val === '关' ? [170, 150, 150] : [176, 172, 196]);
            txt(val, 12, vcol, x0 + 172, yy);
        }
        ctx.fillStyle = cssColor([54, 46, 78], 0.95);
        ctx.fillRect(372, 313, 108, 24);
        ctx.fillRect(492, 313, 108, 24);
        txt('导出存档', 12, [255, 236, 170], 426, 317, 'midtop');
        txt('导入存档', 12, [255, 236, 170], 546, 317, 'midtop');
        txt(mobileUI() ? '点击右侧设置进行调整，点击空白处返回' :
            '↑↓ 选择   Enter / ←→ 调整   ESC 返回',
            11, [140, 136, 160], VIEW_W / 2, VIEW_H - 14, 'midtop');
    }

    // 更新日志内容（需求 18）：与 Python 侧 hud._changelog_lines 一致
    function changelogLines() {
        return [
            ['h', 'v4.0 战斗重构 · 手机操控与数值平衡'],
            ['', '· 手机端双摇杆重做：落指相对拖动瞄准、默认扇形辅助瞄准与锁敌圈'],
            ['', '· 手机端新增右上角一键全屏按钮，支持隐藏地址栏并自动尝试横屏'],
            ['', '· 武器全界面显示伤害、实时攻速与暴击率；新增暴击、连杀与单发散布'],
            ['', '· 取消品质伤倍率，协议连星升璀璨、终端贯枪降传说任第4章专属金武'],
            ['', '· 史诗及以上近战新增 30% 概率额外挥砍（连斩），关闭玩家爆炸自伤'],
            ['', '· 上线 7 场景/副本阶梯血量，Boss 单次受击上限 15%，优化经济与回能'],
            ['', '· 品质射速收缓至 1.0~1.30，与沙氏汽水（+12%）及快速击发（+12%）统一加算'],
            ['', '· 饮品与篮球重做：血量 +25%、回蓝 1/s，篮球改 24 固伤（8% 概率 81 伤）'],
            ['', '· 第 1~4 章怪物与 Boss 伤害按 1.0× → 1.2× → 1.4× → 1.6× 阶梯递增'],
            ['', '· 修通全部 21 个局内天赋与客厅永久天赋触发，精英/宝箱/商店按章掉好枪'],
            ['', '· 接通护盾/荆棘/自愈/磁力局外词条与全部 7 档武器满级专属效果'],
            ['', '· 修复 Boss 血条遮挡角色血条、传送门旁捡武器误进门及多项底层 Bug'],
            ['h', 'v3.5 旧厂勘测记录'],
            ['t', '机械坟场第 2 关可选择高危勘测支路，首次成功获得污染结晶。'],
            ['h', 'v3.3.3 手机战斗界面与双摇杆'],
            ['t', '手机状态与地图避开按键；后台自动暂停，攻击摇杆可调灵敏度。'],
            ['', '· 手机可选辅助瞄准最近怪物'],
            ['h', 'v3.3.2 原生存档与性能监测'],
            ['t', '手机原生存档自动迁移，设置中可显示帧率。'],
            ['h', 'v3.3.1 存档备份与手机操控设置'],
            ['t', '加入存档导入导出、按键尺寸与透明度调节。'],
            ['h', 'v3.2 多端同步与手机触控'],
            ['', '· 手机 16:9 画面自适应，按键与菜单点击优化'],
            ['', '· 电脑与手机分别显示对应操作提示'],
            ['h', 'v3.1 生命系统与角色技能'],
            ['', '· 血包仅恢复生命；受伤的红心留在原位并变灰'],
            ['', '· 八名角色各有专属主动技能，按 X 或技键施放'],
            ['h', 'v3.0.1 已有存档重开修复'],
            ['', '· 客厅加入「从第一关开新局」按钮，保留永久通关记录'],
            ['', '· 旧三层断点迁移为单层关卡，断点收益结算到金库'],
            ['h', 'v3.0 重开旅程 · 珍品物资'],
            ['', '· 每关一张地图，战斗房保留三波刷怪'],
            ['', '· 通关记录保留，结算后从第一关重新开始'],
            ['', '· 新增 30 把常规武器与 5 把隐藏璀璨武器'],
            ['', '· 幸运宝藏怪可掉落珍品，升级界面显示材料需求'],
            ['', '· 更新场景、角色、怪物和武器像素贴图'],
            ['h', 'v2.6 续关存档 · 新角色与结算'],
            ['', '· 传送门房间小地图环形标记，拓宽房门通道'],
            ['', '· 档案员与守种人随收集品进度解锁，可查看进度'],
            ['', '· 旧档择优导入，本层起点续关，支持立即结算'],
            ['', '· 饮料可重复饮用叠加，调整宝箱概率与伤害'],
            ['h', 'v2.5 武器库 · 远程敌人与天赋'],
            ['', '· 69 种独立武器固定品质，拾取与商店显示品质颜色'],
            ['', '· 近战可破箱、斩弹；新增三类远程怪物'],
            ['', '· 调整金币与收藏品掉率；新增免疫陷阱等天赋'],
            ['h', 'v2.4 每轮怪物增量 · 精英突袭'],
            ['', '· 战斗房三轮刷新，每轮至少五只怪物'],
            ['', '· 各轮可能出现精英怪；首领在第三轮登场'],
            ['h', 'v2.3 三轮战斗 · 饮料房'],
            ['', '· 战斗房分三轮刷新，清空后出现奖励宝箱'],
            ['', '· 每主题随机两关有饮料房，四种付费饮料带来独立效果'],
            ['', '· 商店增至四槽；新增独立血瓶、蓝瓶和五把近战武器'],
            ['', '· 蓝量翻倍、武器耗蓝降低；特殊房只保留可击碎箱子'],
            ['h', 'v2.2 双武器 · 战斗节奏'],
            ['', '· 修复第三关后重复开始；局内金币与局外金库分离'],
            ['', '· 双武器切换、耗能后手刀、近战安全距离'],
            ['', '· 战斗音效默认开启；能量靠拾取恢复'],
            ['', '· 陷阱仅在战斗房；新增独立加速带与减速带'],
            ['h', 'v2.1 收藏高光 · 七域双首领'],
            ['', '· 50 种独立武器；常规品质到红色，璀璨隐藏'],
            ['', '· 七个主题各五关，小首领和大首领造型分离'],
            ['', '· 首领概率掉落各主题金色与红色专属武器'],
            ['', '· 收集品专属图标和拾取高光播报，展示台同步更新'],
            ['', '· 图鉴显示已发现武器与怪物的基础属性'],
            ['', '· 换武器需按交互键二次确认；宝箱、陷阱重绘'],
            ['h', 'v2.0 霓虹污染 · 全面重绘'],
            ['', '· 七个场景拥有独立地砖、墙面与霓虹环境纹理'],
            ['', '· 六名角色与 37 种图鉴怪物拥有专属像素造型'],
            ['', '· 武器增至 32 种：独立贴图、弹道节奏与彩色战斗特效'],
            ['', '· 冰霜减速、腐蚀灼烧、电弧连锁与引力牵引加入战斗'],
            ['', '· 修复掉落物与传送门重叠时无法前进的问题'],
            ['', '· 全新城市夜景主视觉；保留旧存档与线性关卡进度'],
            ['h', 'v1.0 余烬禁区 · 污染入侵与生存'],
            ['', '· 主线按顺序推进，副本达标后进入；奖励副本使用游戏金币购入'],
            ['', '· 修复传送门、即时存档和网页版武器缺失；首领后提供天赋三选一'],
            ['h', 'v1.4.4 修复普通关卡清空后没有传送门（卡关）'],
            ['s', '—— 修复'],
            ['', '· 修复「普通关卡打完后给了钥匙却没有传送门」：此前只有首领房'],
            ['', '  才会生成传送门，普通层清空房间只解锁房门'],
            ['', '· 而传送门是通往下一层的唯一出口 —— 于是普通层玩家清光所有'],
            ['', '  房间后仍被永久困在同一层（软锁死）'],
            ['', '· 现在每层都会记录一个"目标房"（初始点最远的那间），清空它'],
            ['', '  即出现传送门，与首领层的规则保持一致'],
            ['h', 'v1.4.3 修复 PC 端键盘完全没有反应'],
            ['s', '—— 修复'],
            ['', '· 修复「人物钉死、键盘操控完全无反应」：个别机器/窗口管理器下'],
            ['', '  窗口会被判定为未聚焦，导致整张键盘状态表恒为"没按"'],
            ['', '· 现在同时用按键事件累积一份"按住的键"，与键盘状态表取并集，'],
            ['', '  只要按键事件能到达，角色就能动 —— 从根上绕开焦点问题'],
            ['', '· 窗口失焦时清空按键集合，避免"松了手角色还在自己走"'],
            ['s', '—— 诊断'],
            ['', '· 首次收到移动输入会写进 boot.log，便于定位"输入没到"还是"走不动"'],
            ['h', 'v1.4.2 网页端全面对齐 + 移动手感修复'],
            ['s', '—— 修复'],
            ['', '· 修复打击停顿把玩家也一起冻住：连续命中时"几乎无法移动"'],
            ['', '· 现在只冻结世界（敌人/子弹/陷阱），玩家移动与瞄准始终用真实时间'],
            ['', '· 打击停顿加入冷却，避免高射速下世界被永久拖慢'],
            ['s', '—— 网页端对齐（此前与本地版内容不一致）'],
            ['', '· 补齐完整存档系统：3 个存档槽 + 个人 ID + 自动保存'],
            ['', '· 补齐选档界面：开始游戏 → 选档 / 新建 / 删除（含二次确认）'],
            ['', '· 补齐分档设置：音乐 / 音效 / 震动 / 摇杆设置随档保存'],
            ['', '· 补齐进度持久化：场景进度、图鉴、收集品、展示台、货币、材料'],
            ['', '· 补齐程序合成 BGM（默认关闭，曲目随场景深度分 4 档）'],
            ['', '· 断点续玩：从存档里的关卡断点继续，而不是每次都从第 1 关开始'],
            ['h', 'v1.4.1 修复选档后无法进入游戏'],
            ['s', '—— 修复'],
            ['', '· 修复「开始游戏 → 选择存档 → 按 Enter 后又退回主菜单」的死循环'],
            ['', '· 现在选中存档（或新建存档）后会直接进入客厅，可立即出击'],
            ['h', 'v1.4  机制化品质 · 自检优化'],
            ['s', '—— 武器（需求 6 强化）'],
            ['', '· 基础型号 6 → 11 把：新增钉刺弩 / 霰流喷射器 / 磁轨狙击 / 废铁砍刀 / 等离子长刃'],
            ['', '· 新增近战武器类别：身前扇形横扫，不耗能，命中即击退'],
            ['', '· 品质升级改为「机制变化」而非单纯加数值：'],
            ['', '  绿=射速弹速｜蓝=弹丸+1｜紫=穿透+1｜金=击杀迸射｜红=命中分裂｜璀璨=追猎弹道'],
            ['', '· 近战武器随品质提升斩击范围与扇形角度'],
            ['s', '—— 战斗手感'],
            ['', '· 网页端补齐「打击停顿（hit-stop）」与「受击击退」，与 PC 端一致'],
            ['', '· 命中 / 击杀 / 受击均有不同强度的定帧，打击更有分量'],
            ['s', '—— 修复与其它'],
            ['', '· 网页端补齐暂停菜单「脱离卡死」（复位并存盘，可断点续玩）'],
            ['', '· 手机端震动真正生效（设置开启后受击触发 navigator.vibrate）'],
            ['', '· 版本号统一为 v1.4'],
            ['h', 'v1.0  「最后一片净土」'],
            ['s', '—— 全新起点'],
            ['', '· 游戏更名：《陆面过程模拟》→《最后一片净土》'],
            ['', '· 剧情重写：围绕「污染入侵 - 生存」的完整叙事'],
            ['s', '—— 流程'],
            ['', '· 关卡改为线性推进，必须 1→2→3→4 依次通关，不能跳关'],
            ['', '· 每个场景 5 关：第 3 关小首领、第 5 关大首领'],
            ['', '· 击败首领后进入传送门，触发天赋三选一'],
            ['s', '—— 养成'],
            ['', '· 货币（金币/钻石）+ 材料收集系统'],
            ['', '· 6 名角色：3 名金币解锁、1 名钻石解锁、1 名材料合成'],
            ['', '· 武器 7 级品质：白/绿/蓝/紫/金/红/璀璨，满级附加特效'],
            ['', '· 宝箱 5 类 × 2 档：货币 / 医疗 / 材料 / 武器 / 收集'],
            ['', '· 图鉴系统：37 种怪物，每场景小怪/精英/首领各不相同'],
            ['', '· 收集品 + 个人展示台'],
            ['s', '—— 存档'],
            ['', '· 个人 ID、最多 3 个存档槽、新建需覆盖选择'],
            ['', '· 一切行为自动保存，异常退出也不丢进度'],
            ['', '· 新增「脱离卡死」：卡住时一键复位并存盘退出'],
            ['s', '—— 战斗'],
            ['', '· 陷阱、掩体、奖励洞穴等场景机关'],
            ['', '· 打击停顿 + 受击击退'],
            ['', '· 防卡死机制与碰撞优化'],
            ['s', '—— 表现'],
            ['', '· 程序合成音乐 / 打击特效 / 震动（默认关闭，可在设置开启）'],
            ['', '· 手机端透明摇杆：固定 / 浮动双模式 + 灵敏度调节'],
            ['', '· 局内提示：新怪、新材料、新武器、首领出现均有简介'],
            ['', '· 传送门 / 开箱 / 购买需二次确认']
        ];
    }

    function drawChangelog(game) {
        blit('bg_title', VIEW_W / 2, VIEW_H / 2, VIEW_W, VIEW_H);
        dim(214, [6, 6, 12]);
        panel(30, 20, VIEW_W - 60, VIEW_H - 40, [18, 16, 24, 238],
            [96, 86, 128], 6, 1);
        txt('更 新 日 志', 20, [255, 226, 150], VIEW_W / 2, 28, 'midtop');
        txt('当前版本 v4.0   ·   《余烬禁区》', 11, [170, 200, 230],
            VIEW_W / 2, 54, 'midtop');
        var lines = changelogLines();
        var sc = Math.trunc(game.log_scroll || 0);
        var y = 78, bottom = VIEW_H - 48, i;
        for (i = sc; i < lines.length; i++) {
            if (y > bottom) { break; }
            var kind = lines[i][0], t = lines[i][1];
            if (kind === 'h') { txt(t, 14, [255, 216, 120], 52, y); y += 22; }
            else if (kind === 's') { txt(t, 12, [160, 210, 190], 60, y); y += 18; }
            else { txt(t, 12, [206, 202, 224], 68, y); y += 17; }
        }
        // 滚动条
        var total = lines.length;
        if (total > 0) {
            var vis = Math.max(1, Math.floor((bottom - 78) / 17));
            if (total > vis) {
                var bar_h = Math.max(12, Math.floor((bottom - 78) * vis / total));
                var bar_y = 78 + Math.floor((bottom - 78 - bar_h) * sc /
                    Math.max(1, total - vis));
                ctx.fillStyle = cssColor([70, 62, 92], 200 / 255);
                ctx.fillRect(VIEW_W - 42, 78, 3, bottom - 78);
                ctx.fillStyle = cssColor([180, 170, 210], 1.0);
                ctx.fillRect(VIEW_W - 42, bar_y, 3, bar_h);
            }
        }
        txt(mobileUI() ? '上下滑动浏览，点击返回' : '↑↓ 滚动    ESC / Enter 返回',
            11, [140, 136, 160],
            VIEW_W / 2, VIEW_H - 34, 'midtop');
    }

    // 需求 10：存档槽界面（3 槽 + 新建 / 覆盖覆盖确认 / 删除）
    // 与 Python hud.draw_slots 布局一致。
    function drawSlots(game) {
        blit('bg_title', VIEW_W / 2, VIEW_H / 2, VIEW_W, VIEW_H);
        dim(200, [6, 6, 12]);
        var st = game.state;
        panel(30, 20, VIEW_W - 60, VIEW_H - 40, [18, 16, 24, 238],
            [96, 86, 128], 6, 1);
        var title = st === 'slot_create' ? '创建新存档'
                  : (st === 'slot_confirm' ? '确认删除存档' : '选择存档');
        txt(title, 21, [255, 226, 150], VIEW_W / 2, 28, 'midtop');
        txt('一台设备最多 3 个存档', 11, [150, 146, 172], VIEW_W / 2, 54, 'midtop');

        if (st === 'slot_create') {
            var idx = Math.trunc(game.slot_pending || 0);
            txt('存档 ' + (idx + 1) + '  ·  输入名字（字母/数字，12 字内）',
                13, [206, 202, 224], VIEW_W / 2, 92, 'midtop');
            var buf = game.name_buf || '';
            var caret = (Math.floor(nowMs() / 500) % 2 === 0) ? '_' : ' ';
            panel(VIEW_W / 2 - 110, 120, 220, 30, [34, 30, 44, 235], [170, 150, 220], 4, 2);
            txt(buf + caret, 15, [255, 240, 190], VIEW_W / 2, 126, 'midtop');
            txt('留空则用默认名「漂泊者' + (idx + 1) + '」', 11, [140, 136, 160],
                VIEW_W / 2, 162, 'midtop');
            txt(mobileUI() ? '点击确认或返回' : 'Enter 确认    ESC 返回',
                11, [140, 136, 160],
                VIEW_W / 2, VIEW_H - 40, 'midtop');
            return;
        }
        if (st === 'slot_confirm') {
            var idx2 = Math.trunc(game.slot_pending || 0);
            txt('真的要删除「存档 ' + (idx2 + 1) + '」吗？', 14, [255, 170, 150],
                VIEW_W / 2, 110, 'midtop');
            txt('该操作不可恢复（进度、货币、收集品都会消失）', 11, [206, 180, 180],
                VIEW_W / 2, 136, 'midtop');
            txt(mobileUI() ? '点击左侧确认删除，右侧取消' :
                'Enter / Y  确认删除        ESC / N  取消', 12, [255, 226, 150],
                VIEW_W / 2, 176, 'midtop');
            return;
        }
        // slots 列表
        var slots = game.slot_list();
        var sel = Math.trunc(game.slot_index || 0);
        for (var i = 0; i < slots.length; i++) {
            var y = 84 + i * 52;
            var on = (i === sel);
            var s = slots[i];
            panel(60, y, VIEW_W - 120, 44,
                on ? [44, 38, 56, 235] : [26, 23, 34, 210],
                on ? [200, 170, 240] : [58, 52, 74], 5, on ? 2 : 1);
            txt('存档 ' + (i + 1), 12, on ? [255, 216, 120] : [170, 166, 190], 70, y + 5);
            if (s === null || s === undefined) {
                txt(mobileUI() ? '— 空 —  （点击创建）' : '— 空 —  （Enter 创建）',
                    12, [120, 116, 140], 150, y + 12);
                continue;
            }
            var target = game._nextTarget(s);
            var scn = (D.sceneInfo(target.scene) || {}).name || target.scene;
            var stg = Math.trunc(target.stage_idx || 0) + 1;
            txt(s.name || '?', 13, [235, 230, 250], 150, y + 5);
            txt(scn + ' · 第 ' + stg + ' 关   金币 ' + Math.trunc(s.coins || 0) +
                '   钻石 ' + Math.trunc(s.diamonds || 0),
                11, [180, 190, 220], 150, y + 24);
            txt('击杀 ' + Math.trunc((s.stats || {}).kills || 0), 10,
                [150, 146, 172], VIEW_W - 76, y + 24, 'topright');
        }
        txt(mobileUI() ? '点击存档进入 / 创建，点击底部返回' :
            '↑↓ 选择    Enter 进入 / 创建    D 删除    ESC 返回',
            11, [140, 136, 160], VIEW_W / 2, VIEW_H - 36, 'midtop');
    }

    // ============================================================ 客厅 / 关卡地图
    // 1.0 需求 16：主菜单 -> 客厅（二级界面）-> 选场景出发。
    // 与 Python 侧 hud.draw_lobby 保持一致：左侧场景卡片，右侧详情 + 机制卡。
    var LOBBY_CARD_H = 30, LOBBY_GAP = 3, LOBBY_LX = 16, LOBBY_LW = 226;

    function fitText(s, size, maxW, bold) {
        if (textWidth(s, size, bold) <= maxW) { return s; }
        s = s.replace(/\s+$/, '');
        while (s.length && textWidth(s + '…', size, bold) > maxW) {
            s = s.slice(0, -1);
        }
        return s ? (s + '…') : '';
    }

    function lobbyMark(prof, key) {
        var progress = prof ? ((prof.scene_prog || {})[key] || 0) : 0;
        var recorded = !!(prof && (prof.cleared_scenes || []).indexOf(key) >= 0);
        if (key === D.BONUS) {
            if (!prof || !prof.bonus_unlocked) { return ['未购', [226, 160, 120]]; }
            if (progress >= D.STAGES_PER_SCENE) {
                return ['√ 通关', [150, 240, 190]];
            }
            if (recorded) { return ['再战', [255, 226, 150]]; }
            return ['可进入', [255, 226, 150]];
        }
        if (Object.prototype.hasOwnProperty.call(D.DUNGEONS, key)) {
            var unl = (prof && (prof.unlocked_dungeons || []).indexOf(key) >= 0);
            if (!unl) { return ['未解锁', [226, 140, 120]]; }
            if (progress >= D.STAGES_PER_SCENE) {
                return ['√ 通关', [150, 240, 190]];
            }
            if (recorded) { return ['再战', [200, 220, 150]]; }
            return ['可进入', [200, 220, 150]];
        }
        if (progress >= D.STAGES_PER_SCENE) {
            return ['√ 通关', [150, 240, 190]];
        }
        if (recorded) { return ['再战', [255, 226, 150]]; }
        return ['主线', [150, 200, 230]];
    }

    function drawDungeonBind(x, y, w, maxH, dkey) {
        var cards = D.dungeonBindCards(dkey);
        var tip = D.dungeonTip(dkey);
        if (!cards.length && !tip) { return 0; }
        var used = 0, i, c, ry, isEnemy, accent, tag, desc;
        for (i = 0; i < cards.length; i++) {
            if (used + 26 > maxH) { break; }
            c = cards[i]; ry = y + used;
            isEnemy = (c.kind === 'enemy');
            accent = isEnemy ? [226, 140, 120] : [140, 220, 160];
            panel(x, ry, w, 24, [26, 22, 30, 210], accent, 4, 1);
            tag = isEnemy ? '怪' : '陷阱';
            panel(x + 3, ry + 5, 22, 13, [40, 30, 36, 230], accent, 3, 1);
            txt(tag, 10, accent, x + 7, ry + 6);
            txt(c.name, 11, C_TEXT, x + 29, ry + 3);
            desc = fitText(c.desc, 10, w - 36);
            txt(desc, 10, C_TEXT_DIM, x + 29, ry + 14);
            used += 26;
        }
        if (tip && used + 16 <= maxH) {
            txt(fitText('战术：' + tip, 10, w - 4), 10, [200, 200, 150],
                x + 2, y + used + 1);
            used += 14;
        }
        return used + 5;
    }

    function drawLobbyDetail(game, key, x, y, w) {
        var prof = game.profile;
        var info = D.scene_info ? D.scene_info(key) : (D.CHAPTER_STORY[key] || {});
        var isDun = Object.prototype.hasOwnProperty.call(D.DUNGEONS, key);
        var isBonus = (key === D.BONUS);
        var yy = y, ent, i, k;

        txt(info.name, 16, [255, 236, 170], x, yy - 2);
        txt(info.sub || '', 10, [140, 136, 166], x, yy + 17);
        yy += 34;

        ent = info.enter || [];
        for (k = 0; k < Math.min(2, ent.length); k++) {
            txt(fitText(ent[k], 10, w), 10, [170, 176, 200], x, yy);
            yy += 13;
        }

        // ---- 污染警告
        var pw = null;
        try { pw = (D.pollutionLines ? D.pollutionLines(key, 0) : null); } catch (e) { pw = null; }
        if (pw && pw.length) {
            var p = D.pollution(key, 0);
            var head = '污染浓度 ' + p.pct + '%';
            var det = pw.join(' · ');
            var warn = fitText(head + '  ·  ' + det, 10, w + 12);
            panel(x, yy, w + 12, 15, [46, 30, 34, 190], [226, 130, 120], 3, 1);
            txt(warn, 10, [240, 170, 160], x + 5, yy + 3);
            yy += 20;
        }

        if (isDun && prof) {
            var res = D.dungeonProgress(prof, key);
            var items = res[0], ok = res[1], ctext = res[2], hint = res[3];
            txt('解锁条件', 11, [200, 220, 150], x, yy); yy += 15;
            txt(fitText(ctext, 10, w), 10, [200, 196, 214], x + 2, yy); yy += 13;
            for (i = 0; i < items.length; i++) {
                var done = items[i][3];
                var col = done ? [150, 240, 190] : [226, 150, 140];
                txt(done ? '√' : '·', 10, col, x + 2, yy);
                txt(fitText(items[i][0] + '  ' + items[i][1] + ' / ' + items[i][2],
                    10, w - 16), 10, col, x + 14, yy);
                yy += 13;
            }
            if (game.lobby_expand && !ok && hint) {
                txt(fitText('提示：' + hint, 10, w), 10, [220, 200, 150], x + 2, yy);
                yy += 13;
            }
            if (game.lobby_expand) {
                txt('— 场景机制 —', 10, [170, 160, 200], x, yy); yy += 13;
                yy += drawDungeonBind(x, yy, w + 12, Math.max(0, VIEW_H - 30 - yy), key);
            } else {
                txt(mobileUI() ? '（点击查看场景机制卡）' : '（按 E 查看场景机制卡）',
                    10, [140, 136, 166], x + 2, yy);
                yy += 13;
            }
        } else if (isBonus && prof) {
            var price = D.bonusPrice();
            var unl = !!prof.bonus_unlocked;
            if (unl) {
                panel(x, yy, w + 12, 18, [28, 40, 32, 200], [150, 240, 190], 3, 1);
                txt('已购买 · 可自由进入', 11, [150, 240, 190], x + 6, yy + 3);
            } else {
                var av = false;
                try { av = D.bonusUnlockable(prof); } catch (e) { av = false; }
                var miss = D.bonusMissing(prof);
                var col2 = (miss[0] <= 0 && miss[1] <= 0) ? [255, 216, 120] : [226, 150, 140];
                panel(x, yy, w + 12, 18, [42, 36, 26, 200], col2, 3, 1);
                txt(price + ' 金币', 11, col2, x + 6, yy + 3);
                var t2;
                if (!av) {
                    t2 = '需先通关「' + (D.CHAPTER_STORY[D.MAIN[D.MAIN.length - 1]] || {}).name + '」';
                } else if (miss[0] > 0 || miss[1] > 0) {
                    t2 = '还差 ' + miss[0] + ' 金币' + (miss[1] ? (' ' + miss[1] + ' 钻石') : '');
                } else {
                    t2 = '资金充足，可购买';
                }
                txt(fitText(t2, 10, w), 10, col2, x + 6, yy + 22);
                yy += 30;
            }
        }
        if (prof && (prof.cleared_scenes || []).indexOf(key) >= 0) {
            txt('√ 已通关该场景', 10, [150, 240, 190], x, yy + 2);
        }
    }

    // ---- 分页 2：图鉴（需求 8/15）
    function codexTotal(cat) {
        if (cat === 'enemy') { return Object.keys(D.ENEMY_CODEX).length; }
        if (cat === 'weapon') { return Object.keys(D.WEAPON_CODEX || {}).length; }
        if (cat === 'material') { return Object.keys(D.MATERIAL_CODEX || {}).length; }
        if (cat === 'collect') { return Object.keys(D.COLLECTS).length; }
        return 0;
    }
    function codexItems(game, cat) {
        var out = [], k, v, i;
        if (cat === 'enemy') {
            for (i = 0; i < D.ENEMY_ORDER.length; i++) {
                k = D.ENEMY_ORDER[i]; v = D.ENEMY_CODEX[k];
                out.push([k, v[0], v[1], false]);
            }
        } else if (cat === 'collect') {
            for (i = 0; i < D.COLLECT_ORDER.length; i++) {
                k = D.COLLECT_ORDER[i]; v = D.COLLECTS[k];
                out.push([k, v[0], v[1] === 'superb' ? '精品' : '普通', false]);
            }
        } else if (cat === 'weapon') {
            var wt = D.WEAPON_CODEX || {};
            for (k in wt) {
                if (Object.prototype.hasOwnProperty.call(wt, k)) {
                    out.push([k, wt[k][0], '武器', false]);
                }
            }
        } else if (cat === 'material') {
            var mt = D.MATERIAL_CODEX || {};
            for (k in mt) {
                if (Object.prototype.hasOwnProperty.call(mt, k)) {
                    out.push([k, mt[k][0], '材料', false]);
                }
            }
        }
        return out;
    }
    function codexDesc(cat, key) {
        var v;
        if (cat === 'enemy') {
            v = D.ENEMY_CODEX[key];
            if (!v) { return ''; }
            var es = (D.ENEMY_STATS || {})[key] || {};
            return '基础生命 ' + (es.hp || '?') + ' · 移速 ' + (es.speed || '?') +
                ' · 接触伤害 ' + (es.contact || '0') + '\n生命随关卡提高。' + v[3];
        }
        if (cat === 'collect') { v = D.COLLECTS[key]; return v ? v[2] : ''; }
        if (cat === 'weapon') {
            v = (D.WEAPON_CODEX || {})[key];
            if (!v) { return ''; }
            var w = (D.WEAPONS || {})[key] || {};
            var mode = w.melee ? '近战 · 范围 ' + w.reach + ' · 扇角 ' + w.arc + '°' :
                '远攻 · 弹丸 ' + w.count + ' · 弹速 ' + w.speed;
            return '基础伤害 ' + w.dmg + ' · 间隔 ' + Number(w.cd).toFixed(2) +
                '秒\n' + mode + '\n' + v[v.length - 1];
        }
        if (cat === 'material') { v = (D.MATERIAL_CODEX || {})[key]; return v ? v[v.length - 1] : ''; }
        return '';
    }
    function drawLobbyCodex(game) {
        var prof = game.profile || {};
        var cats = ['enemy', 'weapon', 'material', 'collect'];
        var ci = ((game.codex_cat || 0) % cats.length + cats.length) % cats.length;
        var cat = cats[ci];
        var seen = ((prof.codex || {})[cat] || []);
        var x = 16, i, k, cnt, tot, on, w;
        for (i = 0; i < cats.length; i++) {
            k = cats[i];
            var label = (D.CODEX_CATS && D.CODEX_CATS[k]) || k;
            cnt = (((prof.codex || {})[k]) || []).length;
            tot = codexTotal(k);
            on = (i === ci);
            var head = label + ' ' + cnt + '/' + tot;
            w = textWidth(head, 10) + 16;
            panel(x, 60, w, 17, on ? [60, 48, 84, 235] : [28, 25, 36, 190],
                on ? [200, 170, 240] : [58, 52, 74], 4, 1);
            txt(head, 10, on ? [255, 240, 190] : [150, 146, 172], x + w / 2, 63, 'midtop');
            x += w + 5;
        }

        var items = codexItems(game, cat);
        var lx = 16, lw = 250, ly = 84;
        // 列表必须止步于页码（VIEW_H-46）之上，否则 "1 / 2" 会糊在最后一行
        var per = Math.max(1, ((VIEW_H - 52 - ly) / 15) | 0);
        var maxpage = items.length ? Math.floor((items.length - 1) / per) : 0;
        var page = Math.max(0, Math.min(game.codex_page || 0, maxpage));
        game.codex_page = page;
        var start = page * per;
        var sel = Math.max(0, Math.min(game.codex_index || 0,
            Math.max(0, items.length - 1)));
        game.codex_index = sel;
        for (i = 0; i < per; i++) {
            var idx = start + i;
            if (idx >= items.length) { break; }
            var it = items[idx];
            var got = seen.indexOf(it[0]) >= 0;
            var isOn = (idx === sel);
            if (isOn) {
                panel(lx, ly - 1, lw, 14, [60, 50, 84, 230], [190, 160, 240], 3, 1);
            }
            var col = got ? [230, 224, 200] : [110, 106, 128];
            txt(fitText(got ? it[1] : '？？？', 11, 150), 11, col, lx + 4, ly);
            if (got) {
                txt(fitText(it[2], 9, 84), 9, [150, 146, 172], lx + lw - 88, ly + 2);
            }
            ly += 15;
        }
        txt((page + 1) + ' / ' + (maxpage + 1), 10, [140, 136, 160], lx, VIEW_H - 46);

        // 右侧详情
        var rx = lx + lw + 12, rw = VIEW_W - 16 - rx, ry = 84;
        if (sel >= 0 && sel < items.length) {
            var cur = items[sel];
            var ok = seen.indexOf(cur[0]) >= 0;
            if (!ok) {
                txt('？？？', 15, [120, 116, 140], rx, ry);
                txt('尚未发现', 11, [150, 146, 172], rx, ry + 22);
                txt(fitText('在关卡里遇到它，就会自动收录。', 10, rw), 10,
                    [130, 126, 150], rx, ry + 40);
            } else {
                txt(cur[1], 16, [255, 236, 170], rx, ry);
                if (cat === 'weapon' || cat === 'enemy') {
                    blit((cat === 'weapon' ? 'wpn_' : 'enemy_') + cur[0],
                        rx + rw - 24, ry + 24, 44, 44);
                }
                var yy = ry + 22;
                if (cur[2]) {
                    txt(cur[2], 10, [170, 176, 200], rx, yy); yy += 16;
                }
                var desc = codexDesc(cat, cur[0]);
                var line = '';
                for (var ci2 = 0; ci2 < desc.length; ci2++) {
                    var ch = desc.charAt(ci2);
                    if (textWidth(line + ch, 11) > rw || ch === '\n') {
                        txt(line, 11, [206, 210, 228], rx, yy); yy += 16;
                        line = (ch === '\n') ? '' : ch;
                    } else { line += ch; }
                }
                if (line) { txt(line, 11, [206, 210, 228], rx, yy); }
            }
        }
    }

    function drawCollectionPopup(game) {
        var p = game.collection_popup;
        if (!p || !D.COLLECTS[p.key]) { return; }
        var entry = D.COLLECTS[p.key];
        var col = entry[1] === 'superb' ? [255, 220, 118] : [140, 235, 250];
        var alpha = Math.max(0, Math.min(1, p.t * 2.6, (p.life - p.t) * 5));
        ctx.fillStyle = cssColor([5, 7, 19], (140 * alpha) / 255);
        ctx.fillRect(0, 0, VIEW_W, VIEW_H);
        panel(157, 100, 326, 146, [18, 22, 39, 245], col, 10, 2);
        ctx.strokeStyle = cssColor(col); ctx.lineWidth = 2;
        ctx.beginPath(); ctx.moveTo(173, 112); ctx.lineTo(467, 112); ctx.stroke();
        blit('collect_' + p.key, 211, 174, 70, 70);
        txt('珍藏发现 · ' + (entry[1] === 'superb' ? '极品' : '普通'),
            11, col, 263, 128);
        txt(entry[0], 19, [255, 247, 222], 263, 150);
        txt(fitText(entry[2], 10, 190), 10, [189, 204, 225], 263, 187);
        txt('已收录图鉴 · 已保存到展示台', 10, col, 263, 212);
    }

    // ---- 分页 3：收集品展示台（需求 9）
    function drawLobbyShowcase(game) {
        var prof = game.profile || {};
        var sc = prof.showcase || [null, null, null, null, null, null];
        var full = [];
        for (var j = 0; j < 6; j++) {
            full.push((j < sc.length) ? sc[j] : null);
        }
        var sel = ((game.showcase_index || 0) % 6 + 6) % 6;
        txt('收集品展示台', 12, [255, 236, 170], VIEW_W / 2, 60, 'midtop');
        var gx = 60, gy = 84, cw = 168, ch = 96, i;
        for (i = 0; i < 6; i++) {
            var col = i % 3, row = (i / 3) | 0;
            var x = gx + col * (cw + 12), y = gy + row * (ch + 12);
            var on = (i === sel), got = (full[i] !== null && full[i] !== undefined);
            panel(x, y, cw, ch, got ? [48, 40, 60, 235] : [26, 23, 32, 200],
                on ? [230, 200, 130] : (got ? [120, 110, 150] : [56, 50, 70]),
                5, on ? 2 : 1);
            txt('#' + (i + 1), 9, [140, 136, 160], x + 6, y + 5);
            if (got) {
                var v = D.COLLECTS[full[i]];
                var name = v ? v[0] : full[i];
                var tier = v ? v[1] : 'common';
                var tcol = (tier === 'superb') ? [255, 216, 120] : [170, 200, 230];
                blit('collect_' + full[i], x + cw / 2, y + 37, 42, 42);
                var nm2 = fitText(name, 12, cw - 16);
                txt(nm2, 12, [255, 240, 190],
                    x + cw / 2 - textWidth(nm2, 12) / 2, y + 62);
                var tag = (tier === 'superb') ? '精品' : '普通';
                txt(tag, 9, tcol, x + cw / 2 - textWidth(tag, 9) / 2, y + 80);
            } else {
                txt('空位', 11, [110, 106, 128], x + cw / 2, y + ch / 2 - 8, 'midtop');
            }
        }
        if (full[sel] !== null && full[sel] !== undefined) {
            var v2 = D.COLLECTS[full[sel]];
            var desc = v2 ? v2[2] : '';
            txt(fitText(desc, 10, VIEW_W - 60), 10, [196, 200, 220],
                VIEW_W / 2, VIEW_H - 46, 'midtop');
        } else {
            txt('在关卡里搜刮，凑齐属于你的收藏。', 10, [140, 136, 166],
                VIEW_W / 2, VIEW_H - 46, 'midtop');
        }
    }

    function drawLobby(game) {
        var prof = game.profile || {};
        dim(226, [6, 6, 12]);
        // 面板从 y=26 起，给顶部标题（y=2..24）留出干净的一条，
        // 避免标题压住面板描边（与 Python 端保持一致的排版约定）。
        panel(6, 26, VIEW_W - 12, VIEW_H - 54, [18, 16, 24, 216], [78, 70, 104], 5, 1);
        txt('客 厅 · 关卡地图', 19, [255, 226, 150], VIEW_W / 2, 2, 'midtop');

        // TAB 分页条（下移到面板内部，不再和标题抢同一行）
        var tab = ((game.lobby_tab || 0) % 4 + 4) % 4;
        var tabs = [['准备', 0], ['养成', 1], ['图鉴', 2], ['展示台', 3]];
        var tx = VIEW_W / 2 - 124, i;
        for (i = 0; i < tabs.length; i++) {
            var on2 = (tabs[i][1] === tab);
            var w2 = textWidth(tabs[i][0], 11) + 20;
            panel(tx, 30, w2, 17, on2 ? [60, 48, 84, 235] : [28, 25, 36, 190],
                on2 ? [200, 170, 240] : [60, 54, 76], 4, 1);
            txt(tabs[i][0], 11, on2 ? [255, 240, 190] : [150, 146, 172],
                tx + w2 / 2, 33, 'midtop');
            tx += w2 + 5;
        }

        txt('金币 ' + (prof.coins || 0) + '/' + D.COIN_CAP, 11, [255, 216, 120], 16, 32);
        txt('钻石 ' + (prof.diamonds || 0) + '/' + D.DIAMOND_CAP, 11, C_DIA, 16, 46);
        var chKey = game.char_key || prof.char || 'scout';
        var chName = (D.CHARACTERS && D.CHARACTERS[chKey]) ? D.CHARACTERS[chKey].name : chKey;
        txt((prof.name || '记录员 021') + '  ·  ' + chName, 11, [190, 200, 230],
            VIEW_W - 16, 32, 'topright');
        var hint = mobileUI() ? '点击上方分页与条目操作' : (tab === 0) ? '↑↓ 选关   E/Enter 详情'
            : ((tab === 1) ? '←→ 换子页   ↑↓ 选条目   Enter 购买/强化'
                : ((tab === 2) ? '←→ 切换分类   ↑↓ 翻页' : '←→ 换格子   E 取出'));
        txt(hint, 10, [150, 146, 172], VIEW_W - 16, 46, 'topright');

        if (tab === 1) {
            drawLobbyGrowth(game);
        } else if (tab === 2) {
            drawLobbyCodex(game);
        } else if (tab === 3) {
            drawLobbyShowcase(game);
        } else {
            var order = game._lobbyOrder();
            var n = order.length;
            var sel = ((game.lobby_index % n) + n) % n;
            var ly = 60, key, info, tint, isDun, isBonus, bg, tag, tcol, m;
            for (i = 0; i < n; i++) {
                if (ly + LOBBY_CARD_H > VIEW_H - 32) { break; }
                key = order[i];
                var on = (i === sel);
                info = D.CHAPTER_STORY[key] || { name: key };
                tint = info.tint || [140, 140, 140];
                isDun = Object.prototype.hasOwnProperty.call(D.DUNGEONS, key);
                isBonus = (key === D.BONUS);
                bg = on ? [44, 38, 56, 235] : [26, 23, 34, 200];
                panel(LOBBY_LX, ly, LOBBY_LW, LOBBY_CARD_H, bg,
                    on ? tint : [56, 50, 70], 4, on ? 2 : 1);
                if (on) { panel(LOBBY_LX, ly, 3, LOBBY_CARD_H, tint, tint, 0, 0); }
                tag = (D.MAIN.indexOf(key) >= 0) ? '主' : (isBonus ? '奖' : '副');
                tcol = isBonus ? [255, 226, 150] : (isDun ? [200, 160, 250] : [150, 200, 230]);
                panel(LOBBY_LX + 7, ly + 9, 17, 15, [18, 16, 24, 230], tcol, 3, 1);
                txt(tag, 10, tcol, LOBBY_LX + 10, ly + 10);
                txt('' + (i + 1), 11, [150, 146, 172], LOBBY_LX + 28, ly + 4);
                txt(fitText(info.name, 13, 120), 13,
                    on ? [255, 240, 190] : [210, 205, 226], LOBBY_LX + 28, ly + 15);
                m = lobbyMark(prof, key);
                txt(m[0], 10, m[1], LOBBY_LX + LOBBY_LW - 10 - textWidth(m[0], 10), ly + 11);
                ly += LOBBY_CARD_H + LOBBY_GAP;
            }
            var rx = LOBBY_LX + LOBBY_LW + 10;
            drawLobbyDetail(game, order[sel], rx, 56, VIEW_W - 16 - rx);
            panel(LOBBY_LX, VIEW_H - 51, 142, 21, [46, 39, 57, 235], [200, 170, 240], 4, 1);
            txt(mobileUI() ? '从第一关开新局' : '从第一关开新局  R',
                10, [255, 230, 170], LOBBY_LX + 8, VIEW_H - 46);
        }

        var tip;
        if (mobileUI()) {
            tip = tab === 0 ? '点击关卡卡片出发，点击底部按钮开新局' :
                '点击页签与条目，重复点击可确认操作';
        } else if (tab === 0) {
            tip = game.lobby_expand ? 'ESC/E 收起    Enter 出发    TAB 切换分页'
                : 'ESC 返回主菜单   E 查看详情   TAB 切换分页   Enter 出发';
        } else if (tab === 1) {
            tip = 'ESC 返回主菜单   ←→ 换子页   Enter 购买 / 强化装备';
        } else if (tab === 2) {
            tip = 'ESC 返回主菜单   ←→ 切换分类   TAB 切换分页';
        } else {
            tip = 'ESC 返回主菜单   ←→ 换格子   TAB 切换分页';
        }
        txt(tip, 11, [150, 146, 172], VIEW_W / 2, VIEW_H - 18, 'midtop');
    }

    // ============================================================ 养成分页
    var GROWTH_SUBS = ['角色', '武器', '技能 / 被动', '天赋'];

    function drawLobbyGrowth(game) {
        var prof = game.profile || {};
        var sub = ((game.growth_sub || 0) % 4 + 4) % 4;
        var rows = game._growthRows();
        var i, x, y, w, on, col;

        // 子页签
        x = 20;
        for (i = 0; i < GROWTH_SUBS.length; i++) {
            on = (i === sub);
            w = textWidth(GROWTH_SUBS[i], 11) + 18;
            panel(x, 58, w, 16, on ? [60, 48, 84, 235] : [26, 23, 34, 190],
                on ? [200, 170, 240] : [56, 50, 70], 4, 1);
            txt(GROWTH_SUBS[i], 11, on ? [255, 240, 190] : [150, 146, 172],
                x + w / 2, 60, 'midtop');
            x += w + 5;
        }
        if (!rows.length) {
            txt('（暂无内容）', 12, [140, 136, 166], VIEW_W / 2, VIEW_H / 2, 'midtop');
            return;
        }

        // 左栏列表
        var lx = 16, lw = 200, ly = 82, ih = 26;
        var visible = Math.max(1, ((VIEW_H - 60 - ly) / ih) | 0);
        var sel = (((game.growth_index || 0) % rows.length) + rows.length) % rows.length;
        var first = Math.max(0, Math.min(sel - (visible >> 1), Math.max(0, rows.length - visible)));
        for (i = 0; i < visible; i++) {
            var idx = first + i;
            if (idx >= rows.length) { break; }
            var r = rows[idx];
            on = (idx === sel);
            y = ly + i * ih;
            panel(lx, y, lw, ih - 2, on ? [52, 44, 68, 240] : [26, 23, 34, 190],
                on ? [200, 170, 240] : [56, 50, 70], 4, on ? 2 : 1);
            if (on) { panel(lx, y, 3, ih - 2, [200, 170, 240], [200, 170, 240], 0, 0); }
            growthRowLeft(r, sub, lx, y, lw, on);
        }

        // 右栏详情
        var rx = lx + lw + 10;
        growthDetail(game, rows[sel], sub, rx, 82, VIEW_W - 16 - rx);

        // 底部材料条
        var mats = D.materialSummary(prof);
        y = VIEW_H - 40;
        txt('材料', 10, [150, 146, 172], 16, y);
        x = 52;
        if (!mats.length) {
            txt('（空）', 10, [110, 106, 128], x, y);
        } else {
            for (i = 0; i < mats.length && i < 8; i++) {
                var sx = mats[i][1] + ' ' + mats[i][3];
                var sw = textWidth(sx, 10);
                if (x + sw > VIEW_W - 16) { break; }
                col = ({ '1': [170, 200, 230], '2': [150, 230, 190],
                         '3': [200, 170, 250] })[String(mats[i][2])] || [170, 200, 230];
                txt(sx, 10, col, x, y);
                x += sw + 12;
            }
        }
    }

    function growthRowLeft(r, sub, x, y, w, on) {
        var tag = '', tcol = [150, 146, 172], icon = '·';
        if (sub === 0) {
            icon = '人';
            if (r.cur) { tag = '出战'; tcol = [150, 240, 190]; }
            else if (r.owned) { tag = '已解锁'; tcol = [200, 220, 250]; }
            else if (r.afford) { tag = '可解锁'; tcol = [170, 240, 170]; }
            else { tag = '不足'; tcol = [226, 140, 120]; }
        } else if (sub === 1) {
            icon = '枪';
            tag = 'Lv.' + r.lv + ' ' + r.quality_name;
            tcol = r.quality_color || [200, 200, 220];
        } else if (sub === 2) {
            icon = r.is_passive ? '被' : '技';
            tag = 'Lv.' + r.lv + '/' + r.max;
            tcol = (r.lv >= r.max) ? [150, 240, 190] : [200, 220, 250];
        } else {
            icon = '星';
            tag = 'Lv.' + r.lv + '/' + r.max;
            tcol = r.color || [200, 200, 220];
        }
        txt(icon, 11, on ? [255, 226, 150] : [140, 132, 170], x + 7, y + 4);
        txt(fitText(r.name, 11, w - 70), 11, on ? [255, 240, 190] : [196, 192, 214],
            x + 24, y + 4);
        txt(tag, 9, tcol, x + w - 8 - textWidth(tag, 9), y + 6);
    }

    function growthDetail(game, r, sub, x, y, w) {
        var prof = game.profile || {};
        var rows = [], c, k, i, yy;
        function addMaterials(cost) {
            var needs=(cost && cost[1]) || {}, keys=Object.keys(needs);
            if(!keys.length){rows.push(['材料','无']);return;}
            keys.forEach(function(key){
                rows.push([(D.MATERIALS[key]||[key])[0],
                    '需 '+needs[key]+' · 持有 '+Number((prof.materials||{})[key]||0)]);
            });
        }
        if (sub === 0) {
            rows.push(['解锁', r.unlock_text]);
            rows.push(['生命', String(r.hp)]);
            rows.push(['速度', r.spd.toFixed(0)]);
            rows.push(['能量', r.energy.toFixed(0)]);
            rows.push(['初始武器', r.starter_name]);
            rows.push(['特性', r.perk]);
            var skillInfo = CHAR_SKILLS[r.key] || CHAR_SKILLS.scout;
            rows.push(['主动技能', skillInfo.name + ' · ' + skillInfo.cd + 's冷却']);
            rows.push(['技能效果', skillInfo.desc]);
        } else if (sub === 1) {
            var qObj = (D.QUALITIES || {})[r.quality] || {};
            var qSpec = D.applyQuality ? D.applyQuality(r.key, r.quality, 1.0) : wget(r.key);
            var pBonus = 1.0 + 0.04 * Math.trunc(((prof.skills || {}).power) || 0);
            var qPerk = (D.QUALITY_ORDER || []).indexOf(r.quality) > 2 &&
                r.lv >= (qObj.max_lv || 99) ? 1.15 : 1.0;
            var realDmg = Math.max(1, Math.round((qSpec.dmg || 1) * r.mul * qPerk * pBonus));
            var cnt = qSpec.count || 1;
            var dmgStr = cnt > 1 ? (realDmg + '×' + cnt) : String(realDmg);
            var cRate = 0.08 + 0.04 * Math.trunc(((prof.passives || {}).crit) || 0);
            if ((r.quality === 'green' || r.quality === 'radiant') && r.lv >= (qObj.max_lv || 99)) { cRate += 0.06; }
            cRate = Math.min(0.65, cRate);
            var spdRate = Number((D.qualityMech(r.quality) || {}).rate || 1.0);
            if ((r.quality === 'white' || r.quality === 'radiant') && r.lv >= (qObj.max_lv || 99)) { spdRate += 0.08; }
            rows.push(['强化等级', 'Lv.' + r.lv]);
            rows.push(['当前品质', r.quality_name + '（伤害 ×' + r.mul.toFixed(2) + '）']);
            rows.push(['武器伤害', dmgStr]);
            rows.push(['攻击速度', (spdRate / Math.max(0.01, (wget(r.key).cd || 0.25))).toFixed(1) + ' 次/秒']);
            rows.push(['暴击率', Math.round(cRate * 100) + '%（暴击 1.5×）']);
            rows.push(['下个品质', r.next_quality_at === null ? '已达上限'
                : ('强化到 Lv.' + r.next_quality_at)]);
            rows.push(['金币', r.cost ? String(r.cost[0]) : '已达上限']);
            addMaterials(r.cost);
        } else if (sub === 2) {
            rows.push(['说明', r.desc]);
            rows.push(['等级', 'Lv.' + r.lv + ' / ' + r.max]);
            if (r.cost) {
                rows.push(['金币', String(r.cost[0])]);
                addMaterials(r.cost);
            } else { rows.push(['状态', '已满级']); }
        } else {
            rows.push(['说明', r.desc]);
            rows.push(['等级', 'Lv.' + r.lv + ' / ' + r.max]);
            c = D.talentUpgradeCost(prof, r.key);
            rows.push(['金币', String(c[0])]);
            addMaterials(c);
        }

        var h = 34 + rows.length * 15;
        panel(x, y, w, h, [30, 26, 40, 230], [110, 96, 140], 4, 1);
        txt(r.name, 12, [255, 236, 170], x + 8, y + 4);
        yy = y + 22;
        for (i = 0; i < rows.length; i++) {
            txt(rows[i][0], 10, [150, 146, 172], x + 8, yy);
            txt(fitText(String(rows[i][1]), 10, w - 78), 10, [216, 214, 232], x + 70, yy);
            yy += 15;
        }
        // 操作提示
        var act, ok = true, reason = '';
        if (sub === 0) {
            if (r.cur) { act = '已装备'; }
            else if (r.owned) { act = mobileUI() ? '点击左侧已选角色进行切换' : 'Enter 换上该角色'; }
            else if (r.afford) { act = (mobileUI() ? '点击解锁（' : 'Enter 解锁（') + r.unlock_text + '）'; }
            else { act = r.reason || '条件不足'; ok = false; }
        } else if (sub === 1) {
            act = r.maxed ? '已达上限' : ((mobileUI() ? '点击强化（金币 ' : 'Enter 强化（金币 ') + r.cost[0] + '）');
        } else if (sub === 2) {
            act = r.cost ? ((mobileUI() ? '点击升级（金币 ' : 'Enter 升级（金币 ') + r.cost[0] + '）') : '已满级';
        } else {
            act = mobileUI() ? '点击升级（永久强化）' : 'Enter 升级（永久强化）';
        }
        if (sub === 0 && !r.owned) { ok = r.afford; reason = r.reason; }
        txt(ok ? act : (reason || '条件不足'), 10,
            ok ? [170, 240, 190] : [226, 150, 150], x + 8, y + h + 8);
    }

    // ================================================================ 过场
    var STORY_PAGE_MAX = 3;
    function drawStory(game) {
        var tint = game.story_tint || [140, 140, 140];
        var base = [Math.max(6, (tint[0] / 8) | 0), Math.max(6, (tint[1] / 8) | 0),
                    Math.max(8, (tint[2] / 8) | 0)];
        fillRect(base, 0, 0, VIEW_W, VIEW_H);
        dim(120, base);
        var t = game.story_t;
        txt(game.story_title || '', 15, [255, 236, 170], 30, 26);
        ctx.strokeStyle = cssColor(tint);
        ctx.lineWidth = 2;
        ctx.beginPath(); ctx.moveTo(30, 48); ctx.lineTo(VIEW_W - 30, 48); ctx.stroke();

        var lines = game.story_lines, page = game.story_page || 0;
        var y = 74, i;
        for (i = 0; i < lines.length; i++) {
            var appear = Math.max(0.0, Math.min(1.0, (t - i * 0.34) / 0.30));
            if (appear <= 0.01) { continue; }
            var col = (i === page) ? [245, 240, 214] : [200, 204, 224];
            if (i === page) { fillRect(tint, 18, y - 2, 3, 20); }
            txt(lines[i], 14, col, 30, y);
            y += 30;
        }
        var n = Math.max(1, lines.length);
        txt(Math.min(page + 1, n) + ' / ' + n, 10, [150, 146, 172],
            VIEW_W - 30, 30, 'topright');
        if (t > 0.6) {
            var hint;
            if (page + 1 < n) { hint = mobileUI() ? '点击画面继续' : '按任意键继续'; }
            else if (game.pending_after && game.pending_after[0] === 'scene_clear') {
                hint = mobileUI() ? '点击画面前往下一场景' : '按任意键前往下一场景';
            } else { hint = mobileUI() ? '点击画面出发' : '按任意键出发'; }
            var pulse = 150 + Math.round(70 * (0.5 + 0.5 * Math.sin(t * 4)));
            txt(hint, 11, [pulse, pulse - 20, 140], VIEW_W / 2, VIEW_H - 30, 'midtop');
        }
        txt(mobileUI() ? '点击继续' : 'ESC 跳过', 10,
            [120, 116, 140], VIEW_W - 30, VIEW_H - 32, 'topright');
    }

    // ================================================================ 天赋三选一
    function drawTalent(game) {
        dim(205, [6, 6, 12]);
        txt('天 赋 觉 醒', 24, [255, 236, 170], VIEW_W / 2, 26, 'midtop');
        txt('在污染里活下来的东西，会慢慢改变你。', 11, [170, 176, 200],
            VIEW_W / 2, 58, 'midtop');

        var picks = game.pending_talents || [];
        // 与 Python 端保持一致的防御：候选表为空时不要越界取 picks[0]
        if (!picks.length) {
            txt('天赋加载中…', 14, [220, 216, 240],
                VIEW_W / 2, VIEW_H / 2 - 10, 'midtop');
            txt(mobileUI() ? '点击继续' : '按 Enter 继续', 11, [150, 146, 172],
                VIEW_W / 2, VIEW_H - 22, 'midtop');
            return;
        }
        var n = picks.length;
        var sel = ((game.talent_pick || 0) % n + n) % n;
        var cw = 132, ch = 154, gap = 14, i;
        var total = n * cw + (n - 1) * gap;
        var x0 = VIEW_W / 2 - total / 2, cy = 96;
        for (i = 0; i < n; i++) {
            var on = (i === sel);
            var x = x0 + i * (cw + gap);
            var y = cy + (on ? 0 : 6);
            var h = ch - (on ? 0 : 12);
            var spec = D.TALENTS[picks[i]] || {};
            var col = spec.color || [200, 200, 220];
            panel(x, y, cw, h, on ? [40, 34, 52, 242] : [24, 21, 30, 210],
                on ? col : [58, 52, 74], 6, on ? 3 : 1);
            if (on) { panel(x, y, cw, 4, col, col, 0, 0); }
            // 菱形图标
            var cx2 = x + cw / 2, cy2 = y + 44;
            ctx.beginPath();
            ctx.moveTo(cx2, cy2 - 17); ctx.lineTo(cx2 + 15, cy2);
            ctx.lineTo(cx2, cy2 + 17); ctx.lineTo(cx2 - 15, cy2);
            ctx.closePath();
            ctx.fillStyle = cssColor(col); ctx.fill();
            ctx.strokeStyle = cssColor([26, 22, 34]); ctx.lineWidth = 2; ctx.stroke();
            var nm = spec.name || picks[i];
            txt(nm, 15, on ? [255, 240, 190] : [216, 212, 234], x + cw / 2, y + 66, 'midtop');
            // 描述换行
            var desc = spec.desc || '';
            var line = '', yy = y + 88;
            for (var ci = 0; ci < desc.length; ci++) {
                var ch2 = desc.charAt(ci);
                if (textWidth(line + ch2, 10) > cw - 18) {
                    txt(line, 10, [200, 204, 224], x + 9, yy); yy += 14;
                    line = ch2;
                } else { line += ch2; }
            }
            if (line) { txt(line, 10, [200, 204, 224], x + 9, yy); }
            // 已叠加次数
            var cnt = 0;
            for (var j = 0; j < game.talents_owned.length; j++) {
                if (game.talents_owned[j] === picks[i]) { cnt++; }
            }
            if (cnt) {
                var tag = '已叠加 ×' + cnt;
                txt(tag, 9, col, x + cw / 2 - textWidth(tag, 9) / 2, y + h - 18);
            }
        }
        txt(mobileUI() ? '点击一张天赋卡确认' : '←→ 选择    Enter 确认',
            11, [150, 146, 172],
            VIEW_W / 2, VIEW_H - 22, 'midtop');
    }

    function drawPause(game) {
        dim(175, [6, 6, 12]);
        txt('暂 停', 30, C_TEXT, VIEW_W / 2, 84, 'midtop');
        var items = game.pause_items;
        for (var i = 0; i < items.length; i++) {
            var sel = (i === game.pause_index);
            var y = 122 + i * 30;
            var size = sel ? 17 : 15;
            var col = sel ? [255, 236, 170] : [176, 172, 196];
            var w = textWidth(items[i][0], size);
            if (sel) {
                ctx.fillStyle = cssColor([120, 90, 200], 70 / 255);
                ctx.fillRect(VIEW_W / 2 - w / 2 - 18, y - 5, w + 36, 26);
            }
            txt(items[i][0], size, col, VIEW_W / 2 - w / 2, y - 2);
        }
        txt(mobileUI() ? '点击菜单项操作' :
            '↑↓ 选择   Enter 确认   ESC 继续游戏', 11, [140, 136, 160],
            VIEW_W / 2, VIEW_H - 26, 'midtop');
    }

    function drawMenuList(items, base, step, index) {
        for (var i = 0; i < items.length; i++) {
            var sel = (i === index);
            var y = base + i * step;
            var size = sel ? 16 : 14;
            var col = sel ? [255, 236, 170] : [176, 172, 196];
            var w = textWidth(items[i][0], size);
            if (sel) {
                ctx.fillStyle = cssColor([120, 90, 200], 70 / 255);
                ctx.fillRect(VIEW_W / 2 - w / 2 - 18, y - 4, w + 36, 24);
            }
            txt(items[i][0], size, col, VIEW_W / 2 - w / 2, y - 2);
        }
    }

    var OVER_ROWS_TOP = { gameover: 108, victory: 122 };
    var OVER_ROW_STEP = { gameover: 26, victory: 24 };
    var OVER_MENU_GAP = { gameover: 14, victory: 12 };
    var OVER_MENU_STEP = { gameover: 30, victory: 28 };
    function overMenuBase(st) {
        return OVER_ROWS_TOP[st] + 5 * OVER_ROW_STEP[st] + OVER_MENU_GAP[st];
    }

    function drawGameOver(game) {
        dim(200, [10, 4, 8]);
        txt('你 倒 下 了', 34, [226, 72, 84], VIEW_W / 2, 46, 'midtop');
        var rows = [
            ['抵达层数', '第 ' + game.floor + ' 层'],
            ['累计击杀', String(game.kills)],
            ['拾取金币', String(game.coins)],
            ['射击次数', String(game.player.shots)],
            ['承受伤害', String(Math.floor(game.player.dmg_taken))]
        ];
        var y = OVER_ROWS_TOP.gameover;
        for (var i = 0; i < rows.length; i++) {
            txt(rows[i][0], 14, C_TEXT_DIM, 216, y);
            txt(rows[i][1], 14, C_TEXT, 384, y);
            y += OVER_ROW_STEP.gameover;
        }
        drawMenuList(game.over_items, overMenuBase('gameover'), OVER_MENU_STEP.gameover,
            game.over_index);
    }

    function drawLevelClear(game) {
        dim(190, [6, 8, 12]);
        txt('第 ' + game.floor + ' 层  通过！', 30, [150, 240, 190],
            VIEW_W / 2, 76, 'midtop');
        txt('当前金币 ' + game.coins + '    累计击杀 ' + game.kills, 14, C_TEXT_DIM,
            VIEW_W / 2, 122, 'midtop');
        txt('生命与能量已部分恢复，武器保留', 14, [255, 226, 150],
            VIEW_W / 2, 150, 'midtop');
        txt(mobileUI() ? '点击进入下一关' : '按 Enter 进入下一关',
            16, C_TEXT, VIEW_W / 2, 208, 'midtop');
        txt(mobileUI() ? '点击此处立即结算并返回主菜单' :
            '按 S 立即结算并返回主菜单',
            13, [255, 226, 150], VIEW_W / 2, 239, 'midtop');
    }

    function drawVictory(game) {
        dim(190, [8, 6, 14]);
        var t = nowMs() / 1000.0;
        txt('通 关 ！！！', 34, [255, 226, 120], VIEW_W / 2,
            40 + Math.sin(t * 3) * 2, 'midtop');
        txt('你净化了污染核心，地表重归宁静', 14, [170, 240, 200],
            VIEW_W / 2, 88, 'midtop');
        var rows = [
            ['最终层数', FLOORS + ' 层全通'],
            ['累计击杀', String(game.kills)],
            ['拾取金币', String(game.coins)],
            ['射击次数', String(game.player.shots)],
            ['剩余生命', Math.floor(game.player.hp) + ' / ' + Math.floor(game.player.max_hp)],
            ['总用时', Math.floor(game.total_time / 60) + ' 分 ' +
                Math.floor(game.total_time % 60) + ' 秒']
        ];
        var y = OVER_ROWS_TOP.victory;
        for (var i = 0; i < rows.length; i++) {
            txt(rows[i][0], 14, C_TEXT_DIM, 216, y);
            txt(rows[i][1], 14, C_TEXT, 384, y);
            y += OVER_ROW_STEP.victory;
        }
        drawMenuList(game.over_items, overMenuBase('victory'), OVER_MENU_STEP.victory,
            game.over_index);
    }

    function drawQuit() {
        dim(230, [6, 6, 12]);
        txt('感谢游玩！', 28, [255, 226, 150], VIEW_W / 2, 112, 'midtop');
        txt('网页版直接关闭浏览器标签页即可退出', 14, C_TEXT_DIM,
            VIEW_W / 2, 158, 'midtop');
        txt(mobileUI() ? '点击返回主菜单' : '按 Enter / ESC 返回主菜单',
            13, [150, 210, 180],
            VIEW_W / 2, 196, 'midtop');
    }

    // ==================================================================== 主控
    function Game(seed, enableAudio) {
        this.seed = (seed === undefined || seed === null) ? null : seed;
        this.rng = makeRng(this.seed);
        this.mouse_canvas = [VIEW_W / 2, VIEW_H / 2];
        this.show_aim = true;
        this.cam = [CAM_OFF[0], CAM_OFF[1]];

        this.state = 'title';
        this.running = true;
        this.time = 0.0;
        this.total_time = 0.0;
        this.trans_fade = 0.0;
        this.banner_t = 0.0;
        this.banner_text = '';
        this.collection_popup = null;
        this.hint_t = 0.0;
        this.fire_cool = 0.0;
        this.prompt = null;
        this.hitstop = 0.0;    // 需求 20：打击停顿剩余秒数
        this._hitstop_cd = 0.0; // 打击停顿冷却（防连续刷新）
        this.boss = null;
        this.coins = 0;
        this.kills = 0;
        this.combo_count = 0;
        this.combo_t = 0.0;
        this.floor = 1;
        this._explode_depth = 0;
        this.inp = null;

        this.best_floor = 0;
        this.best_kills = 0;
        this.setting = defaultSettings();
        this.setting_index = 0;
        // 需求 10：3 槽存档仓库 + 个人 ID（与 Python save.py 同构）
        this.profile = null;
        this.slot_index = 0;
        this.slot_pending = 0;
        this.name_buf = '';
        this.store = SaveStore;
        this._load_save();

        // ---- 局外资源 / 提示（需求 4、15）
        this.diamonds = 0;
        this.mats = {};
        this.toasts = [];          // [{title, sub, color, t, life}]
        this.level_state = null;   // 关卡进度（章节/场景/小关），由 progress 层填充

        // ---- 1.1 天赋 / 过场（需求 1.1-2、17）
        this.talents_owned = [];   // 本局已选天赋（可叠加）
        this.run_stats = null;     // 天赋累计出的数值加成
        this.pending_talents = null;   // 三选一候选
        this.talent_pick = 0;
        this._pending_story = null;    // 三选一结束后要接的过场
        this.transition_lock = 0.0;    // 过场刚结束的输入锁（防误触立刻推进）
        this.story_scene = null;
        this.story_lines = [];
        this.story_t = 0.0;
        this.pending_after = null;     // 过场结束后要执行的动作
        this.run_kills = 0;
        this.run_deaths = 0;
        this.new_codex = [];           // 本次新解锁的图鉴条目

        this.dungeon = null;
        this.room = null;
        this.player = new Player(ROOM_CX, ROOM_CY);
        this.enemies = [];
        this.bullets = [];
        this.fx = new FX();

        this.menu_items = [
            ['开始游戏', 'new'],
            ['操作说明', 'help'],
            ['音效：' + (Sfx.enabled ? '开' : '关'), 'audio'],
            ['退出游戏', 'quit']
        ];
        this.pause_items = [
            ['继续游戏', 'resume'],
            ['脱离卡死', 'unstuck'],
            ['立即结算', 'settle'],
            ['重新开始', 'restart'],
            ['返回主菜单', 'title'],
            ['退出游戏', 'quit']
        ];
        this.over_items = [
            ['重新开始', 'restart'],
            ['返回主菜单', 'title'],
            ['退出游戏', 'quit']
        ];
        this.menu_index = 0;
        this.pause_index = 0;
        this.over_index = 0;
        // 客厅 / 关卡地图（1.0 需求 16）
        this.lobby_index = 0;
        this.lobby_expand = false;
        this.lobby_tab = 0;            // 0 关卡 / 1 图鉴 / 2 展示台
        this.codex_cat = 0;            // 图鉴分类
        this.codex_index = 0;          // 图鉴条目选中
        this.codex_page = 0;           // 图鉴分页
        this.showcase_index = 0;       // 展示台格子
        this.char_key = null;
        this.char_skill_cd = 0;
        if (enableAudio === false) { Sfx.enabled = false; }
    }

    // ---- 设置读写（需求 12/15）
    Game.prototype._applyAudioSettings = function () {
        var st = this.setting || {};
        Sfx.enabled = !!st.sfx;
        // 需求 11：音乐开关 + 按当前场景深度取情绪档
        try {
            Music.set_enabled(!!st.music, this.music_mood());
        } catch (e) { /* 浏览器不支持时静默降级 */ }
    };
    // 按当前场景在全部场景中的深浅给 BGM 一个情绪档（0..3）
    Game.prototype.music_mood = function () {
        try {
            var ls = this.level_state || {};
            var sc = ls.scene;
            if (!sc) { return 0; }
            var all = D.allScenes();
            var idx = all.indexOf(sc);
            if (idx < 0) { return 0; }
            var n = Math.max(1, all.length - 1);
            return Math.round(idx / n * 3);
        } catch (e) { return 0; }
    };
    Game.prototype.toggle_setting = function (name) {
        if (!this.setting || !Object.prototype.hasOwnProperty.call(this.setting, name)) {
            return;
        }
        this.setting[name] = !this.setting[name];
        this._applyAudioSettings();
        this.save_settings();
        Sfx.play('ui');
        return this.setting[name];
    };
    Game.prototype.set_setting = function (name, val) {
        this.setting[name] = val;
        this._applyAudioSettings();
        this.save_settings();
        return val;
    };

    // ---- 客厅 / 关卡地图
    Game.prototype._lobbyOrder = function () { return D.allScenes(); };
    Game.prototype._nextTarget = function (prof) {
        if (!prof) { return { scene: D.MAIN[0], stage_idx: 0 }; }
        var progress = prof.scene_prog || {}, run = prof.run;
        if (run && run.scene &&
            (progress[run.scene] || 0) <= (run.stage_idx || 0)) {
            return { scene: run.scene, stage_idx: run.stage_idx || 0 };
        }
        if (D.resetCycle && D.MAIN.every(function (key) {
            return Number(progress[key] || 0) >= D.STAGES_PER_SCENE;
        })) {
            prof.main_done = true;
            D.resetCycle(prof);
            progress = prof.scene_prog;
        }
        for (var i = 0; i < D.MAIN.length; i++) {
            var key = D.MAIN[i];
            if ((progress[key] || 0) < D.STAGES_PER_SCENE) {
                return { scene: key, stage_idx: progress[key] || 0 };
            }
        }
        return { scene: prof.bonus_unlocked ? D.BONUS : null, stage_idx: 0 };
    };
    Game.prototype._lobbyMove = function (d) {
        var n = this._lobbyOrder().length;
        if (n <= 0) { return; }
        this.lobby_index = (this.lobby_index + d % n + n) % n;
        this.lobby_expand = false;
    };
    Game.prototype._lobbyCanEnter = function (key, prof) {
        if (!prof) { return [key === D.MAIN[0], '只能从第一关开始']; }
        var target = this._nextTarget(prof);
        if (key === D.BONUS) {
            if (!prof.bonus_unlocked) {
                if (!D.bonusUnlockable(prof)) {
                    var lastN = (D.CHAPTER_STORY[D.MAIN[D.MAIN.length - 1]] || {}).name;
                    return [false, '需先通关「' + lastN + '」'];
                }
                if (!D.canBuyBonus(prof)) {
                    var miss = D.bonusMissing(prof), parts = [];
                    if (miss[0]) { parts.push(miss[0] + ' 金币'); }
                    if (miss[1]) { parts.push(miss[1] + ' 钻石'); }
                    return [false, '还差 ' + parts.join('、')];
                }
                return [false, '按两次出发键，使用游戏内金币购买'];
            }
            return [true, ''];
        }
        if (Object.prototype.hasOwnProperty.call(D.DUNGEONS, key)) {
            if ((prof.unlocked_dungeons || []).indexOf(key) < 0) {
                var res = D.dungeonProgress(prof, key);
                return [false, (res[3] || '解锁条件未达成')];
            }
            // 支线单独从客厅进入，继续该副本自己的下一关；主线进度不回退。
            return [true, ''];
        }
        return [target.scene === key, '主线只能依次推进，不能选关'];
    };
    Game.prototype._lobbyGo = function () {
        var order = this._lobbyOrder();
        if (!order.length) { return; }
        var sel = ((this.lobby_index % order.length) + order.length) % order.length;
        var key = order[sel];
        if (key === D.BONUS && this.profile && !this.profile.bonus_unlocked &&
            D.bonusUnlockable(this.profile) && D.canBuyBonus(this.profile)) {
            if (this._pending_bonus) {
                this._pending_bonus = false;
                if (D.buyBonus(this.profile)) {
                    this.coins = this.profile.coins;
                    this.diamonds = this.profile.diamonds;
                    this._write_save();
                    this.toast('已购入奖励副本', '再次按出发键进入馈赠之地', [255, 226, 150]);
                }
            } else {
                this._pending_bonus = true;
                this.toast('确认购买奖励副本', '再按一次出发键，支付 ' + D.bonusPrice() + ' 游戏金币', [255, 226, 150]);
            }
            return;
        }
        this._pending_bonus = false;
        var r = this._lobbyCanEnter(key, this.profile);
        if (!r[0]) {
            Sfx.play('ui');
            this.toast('无法进入', r[1], [226, 160, 120]);
            return;
        }
        Sfx.play('ui_big');
        var target = this._nextTarget(this.profile);
        var side = Object.prototype.hasOwnProperty.call(D.DUNGEONS, key);
        var stage = (side || key === D.BONUS) ? ((this.profile.scene_prog || {})[key] || 0)
            : (target.stage_idx || 0);
        this.start_run(key, stage);
    };
    Game.prototype._startNewCycle = function () {
        if (!this.profile) { return; }
        if (!this._pending_new_cycle || Date.now() - this._pending_new_cycle > 5000) {
            this._pending_new_cycle = Date.now();
            this.toast('从第一关开新局', '5 秒内再次点击或按 R 确认，当前断点收益会结算', [255, 226, 150]);
            return;
        }
        this._pending_new_cycle = 0;
        var cp = this.profile.run_checkpoint || {};
        this.profile.coins = D.clampCoin(Number(this.profile.coins || 0) + Number(cp.coins || 0));
        D.resetCycle(this.profile);
        this._write_save();
        this.start_run(D.MAIN[0], 0);
    };
    Game.prototype._enterLobby = function () {
        this._pending_new_cycle = 0;
        var order = this._lobbyOrder();
        this.lobby_expand = false;
        var target = this._nextTarget(this.profile);
        var idx = Math.max(0, order.indexOf(target.scene || D.BONUS));
        this.lobby_index = Math.max(0, Math.min(idx, Math.max(0, order.length - 1)));
        this.state = 'lobby';
    };
    Game.prototype._keydownSettings = function (key) {
        var sr = settingRows(this);
        var rows = sr[0];
        var n = Math.max(1, rows.length);
        var idx = ((this.setting_index || 0) % n + n) % n;
        if (key === 'w' || key === 'up') {
            this.setting_index = (idx - 1 + n) % n; Sfx.play('ui'); return;
        }
        if (key === 's' || key === 'down') {
            this.setting_index = (idx + 1) % n; Sfx.play('ui'); return;
        }
        if (key !== 'enter' && key !== ' ' && key !== 'a' && key !== 'left' &&
            key !== 'd' && key !== 'right') { return; }
        var row = rows[idx];
        var back = (key === 'a' || key === 'left');
        var k = row[1], typ = row[2];
        if (typ === 'bool') {
            this.toggle_setting(k);
        } else if (typ === 'mode') {
            var modes = JOY_MODES;
            var cur = this.setting[k] || modes[0];
            var mi = modes.indexOf(cur); if (mi < 0) { mi = 0; }
            mi = back ? (mi - 1 + modes.length) % modes.length
                      : (mi + 1) % modes.length;
            this.set_setting(k, modes[mi]);
            Sfx.play('ui');
        } else if (typ === 'num') {
            var v = parseFloat(this.setting[k]);
            if (isNaN(v)) { v = 1.0; }
            v += (back ? -0.1 : 0.1);
            var low = k === 'button_opacity' ? 0.3 :
                      (k === 'button_scale' ? 0.7 : 0.4);
            var high = k === 'button_opacity' ? 1.0 :
                       (k === 'button_scale' ? 1.4 : 2.0);
            v = Math.max(low, Math.min(high, Math.round(v * 10) / 10));
            this.set_setting(k, v);
            Sfx.play('ui');
        }
    };
    Game.prototype._keydownLobby = function (key) {
        if ((this.lobby_tab || 0) === 0 && key === 'r') { this._startNewCycle(); return; }
        if (key === 'tab') {
            this.lobby_tab = ((this.lobby_tab || 0) + 1) % 4;
            this.lobby_expand = false;
            Sfx.play('ui');
            return;
        }
        var tab = ((this.lobby_tab || 0) % 4 + 4) % 4;
        if (tab === 1) { this._keydownGrowth(key); return; }
        if (tab === 2) { this._keydownCodex(key); return; }
        if (tab === 3) { this._keydownShowcase(key); return; }
        if (key === 'arrowup' || key === 'w') { this._lobbyMove(-1); Sfx.play('ui'); }
        else if (key === 'arrowdown' || key === 's') { this._lobbyMove(1); Sfx.play('ui'); }
        else if (key === 'arrowleft') { this._lobbyMove(-5); Sfx.play('ui'); }
        else if (key === 'arrowright') { this._lobbyMove(5); Sfx.play('ui'); }
        else if (key === 'e' || key === 'f') { this.lobby_expand = !this.lobby_expand; Sfx.play('ui'); }
        else if (key === 'enter' || key === ' ') { this._lobbyGo(); }
        else if (key === 'escape') { this.state = 'title'; this.menu_index = 0; Sfx.play('ui'); }
    };

    // ---- 需求 10：存档槽界面（slots / slot_create / slot_confirm）
    // 与 Python game._keydown_slots 对齐。关键：选档后必须直接进客厅，
    // 退回 title 会形成"选了档又回到菜单"的死循环（曾出过该 bug）。
    Game.prototype._key_char = function (key) {
        if (!key || key.length !== 1) { return ''; }
        if (/^[a-z0-9]$/.test(key)) { return key; }
        return '';
    };
    Game.prototype._keydownSlots = function (key) {
        var st = this.state;
        if (st === 'slot_create') {
            if (key === 'backspace') {
                this.name_buf = (this.name_buf || '').slice(0, -1);
            } else if (key === 'escape') {
                this.state = 'slots';
                Sfx.play('ui');
            } else if (key === 'enter') {
                var nm = (this.name_buf || '').replace(/^\s+|\s+$/g, '') ||
                         ('漂泊者' + (Math.trunc(this.slot_pending || 0) + 1));
                this.create_profile(Math.trunc(this.slot_pending || 0), nm);
                this._enterLobby();
                Sfx.play('ui_big');
            } else {
                var ch = this._key_char(key);
                if (ch && (this.name_buf || '').length < 12) {
                    this.name_buf = (this.name_buf || '') + ch;
                    Sfx.play('ui');
                }
            }
            return;
        }
        if (st === 'slot_confirm') {
            if (key === 'enter' || key === 'y') {
                this.delete_profile(Math.trunc(this.slot_pending || 0));
                this.state = 'slots';
                this.slot_index = 0;
            } else if (key === 'escape' || key === 'n') {
                this.state = 'slots';
            }
            Sfx.play('ui');
            return;
        }
        // slots
        var slots = this.slot_list();
        var n = Math.max(1, slots.length);
        var idx = ((this.slot_index || 0) % n + n) % n;
        if (key === 'up' || key === 'w') {
            this.slot_index = (idx - 1 + n) % n;
            Sfx.play('ui');
        } else if (key === 'down' || key === 's') {
            this.slot_index = (idx + 1) % n;
            Sfx.play('ui');
        } else if (key === 'enter' || key === ' ') {
            if (slots[idx] === null) {
                this.slot_pending = idx;
                this.name_buf = '';
                this.state = 'slot_create';
                Sfx.play('ui_big');
            } else {
                this.select_profile(idx);
                // 选中存档后直接进客厅开玩（关键：不能退回 title，否则死循环）
                this._enterLobby();
                Sfx.play('ui_big');
            }
        } else if (key === 'd' || key === 'delete') {
            if (slots[idx] !== null) {
                this.slot_pending = idx;
                this.state = 'slot_confirm';
                Sfx.play('ui');
            }
        } else if (key === 'escape') {
            this.state = 'title';
            this.menu_index = 0;
            Sfx.play('ui');
        }
    };
    Game.prototype._slotMouse = function (pos) {
        var p = pos ? [pos[0], pos[1]] : this.mouse_canvas;
        var st = this.state;
        if (st === 'slot_create') {
            // 输入框 + 确认/取消按钮
            if (p[1] >= 118 && p[1] <= 152 &&
                p[0] >= VIEW_W / 2 - 110 && p[0] <= VIEW_W / 2 + 110) {
                this._keydownSlots('enter');
                return true;
            }
            if (p[1] >= VIEW_H - 46 && p[1] <= VIEW_H - 26) {
                this._keydownSlots('escape');
                return true;
            }
            return false;
        }
        if (st === 'slot_confirm') {
            if (p[1] >= 168 && p[1] <= 196) {
                if (p[0] < VIEW_W / 2) { this._keydownSlots('enter'); }
                else { this._keydownSlots('escape'); }
                return true;
            }
            return false;
        }
        // slots 列表
        var slots = this.slot_list();
        var top = 84, step = 52;
        for (var i = 0; i < slots.length; i++) {
            var y = top + i * step;
            if (p[1] >= y && p[1] <= y + 44 && p[0] >= 60 && p[0] <= VIEW_W - 60) {
                this.slot_index = i;
                Sfx.play('ui');
                if (slots[i] === null) {
                    this.slot_pending = i;
                    this.name_buf = '';
                    this.state = 'slot_create';
                } else {
                    this.select_profile(i);
                    this._enterLobby();
                }
                return true;
            }
        }
        if (p[1] >= VIEW_H - 44 && p[1] <= VIEW_H - 24) {
            this.state = 'title';
            this.menu_index = 0;
            Sfx.play('ui');
            return true;
        }
        return false;
    };

    // ---- 养成分页（需求 4/5/6/7）
    Game.prototype._growthRows = function () {
        var prof = this.profile;
        var sub = ((this.growth_sub || 0) % 4 + 4) % 4;
        if (sub === 0) { return D.charList(prof); }
        if (sub === 1) { return D.weaponList(prof); }
        if (sub === 2) {
            var rows = D.skillList ? D.skillList(prof) : [];
            for (var i = 0; i < rows.length; i++) { rows[i].is_passive = false; }
            var pr = D.passiveList ? D.passiveList(prof) : [];
            for (var j = 0; j < pr.length; j++) { pr[j].is_passive = true; }
            return rows.concat(pr);
        }
        return D.talentList ? D.talentList(prof) : [];
    };
    Game.prototype._keydownGrowth = function (key) {
        var nsub = 4;
        if (key === 'arrowleft' || key === 'a') {
            this.growth_sub = ((this.growth_sub || 0) - 1 + nsub) % nsub;
            this.growth_index = 0; Sfx.play('ui');
        } else if (key === 'arrowright' || key === 'd') {
            this.growth_sub = ((this.growth_sub || 0) + 1) % nsub;
            this.growth_index = 0; Sfx.play('ui');
        } else if (key === 'arrowup' || key === 'w') {
            this.growth_index = Math.max(0, (this.growth_index || 0) - 1); Sfx.play('ui');
        } else if (key === 'arrowdown' || key === 's') {
            var rows = this._growthRows();
            var mx = Math.max(0, rows.length - 1);
            this.growth_index = Math.min(mx, (this.growth_index || 0) + 1); Sfx.play('ui');
        } else if (key === 'enter' || key === ' ') {
            this._growthConfirm();
        } else if (key === 'escape') {
            this.state = 'title'; Sfx.play('ui');
        }
    };
    Game.prototype._growthConfirm = function () {
        var prof = this.profile;
        if (!prof) { Sfx.play('no_energy'); return; }
        var sub = ((this.growth_sub || 0) % 4 + 4) % 4;
        var rows = this._growthRows();
        if (!rows.length) { return; }
        var i = ((this.growth_index || 0) % rows.length + rows.length) % rows.length;
        var row = rows[i], key = row.key, res;
        if (sub === 0 && !row.owned && D.CHARACTERS[key] &&
            D.CHARACTERS[key].unlock[0] === 'collect') {
            this.toast(row.name + '解锁进度', D.unlockText(key, prof), [170, 230, 255], 3.0);
            return;
        }
        if (!(sub === 0 && row.owned)) {
            var pending = this._pending_growth;
            if (!pending || pending.sub !== sub || pending.key !== key ||
                Date.now() - pending.time > 5000) {
                this._pending_growth = {sub: sub, key: key, time: Date.now()};
                this.toast('确认' + (row.craft ? '合成' : '购买/强化'),
                    '再按一次确认，消耗所需游戏货币与材料', [255, 226, 150]);
                return;
            }
        }
        this._pending_growth = null;
        if (sub === 0) {
            if (!row.owned) { res = D.buyChar(prof, key); }
            else if (key !== prof.char) { res = D.selectChar(prof, key); }
            else { res = [false, '「' + row.name + '」已在出战']; }
        } else if (sub === 1) {
            res = D.upgradeWeapon(prof, key);
        } else if (sub === 2) {
            res = row.is_passive ? D.upgradePassive(prof, key) : D.upgradeSkill(prof, key);
        } else {
            res = D.upgradeTalent ? D.upgradeTalent(prof, key) : [false, '暂不可用'];
        }
        this._growthAfter(res[0], res[1]);
    };
    Game.prototype._growthAfter = function (ok, msg) {
        Sfx.play(ok ? 'ui_big' : 'no_energy');
        if (msg) {
            this.toast(msg, '', ok ? [200, 240, 200] : [240, 190, 190], 3.0);
        }
        if (ok) { try { this._write_save(); } catch (e) { /* 忽略 */ } }
    };
    Game.prototype._openGrowth = function (sub) {
        this.lobby_tab = 1;
        this.growth_sub = ((sub || 0) % 4 + 4) % 4;
        this.growth_index = 0;
        Sfx.play('ui');
    };
    // ---- 图鉴分页按键
    Game.prototype._keydownCodex = function (key) {
        var cats = 4;
        var per = Math.max(1, ((VIEW_H - 110) / 15) | 0);
        var items = codexItems(this, ['enemy', 'weapon', 'material', 'collect'][this.codex_cat % cats]);
        var maxpage = items.length ? Math.floor((items.length - 1) / per) : 0;
        if (key === 'arrowleft' || key === 'a') {
            this.codex_cat = ((this.codex_cat - 1) % cats + cats) % cats;
            this.codex_index = 0; this.codex_page = 0; Sfx.play('ui');
        } else if (key === 'arrowright' || key === 'd') {
            this.codex_cat = (this.codex_cat + 1) % cats;
            this.codex_index = 0; this.codex_page = 0; Sfx.play('ui');
        } else if (key === 'arrowup' || key === 'w') {
            this._codexSyncPage();
            if (this.codex_index > 0) { this.codex_index--; }
            this._codexSyncPage(); Sfx.play('ui');
        } else if (key === 'arrowdown' || key === 's') {
            this._codexSyncPage();
            if (this.codex_index < items.length - 1) { this.codex_index++; }
            this._codexSyncPage(); Sfx.play('ui');
        } else if (key === 'q') {
            this.codex_page = Math.max(0, this.codex_page - 1);
            this.codex_index = this.codex_page * per; Sfx.play('ui');
        } else if (key === 'e') {
            this.codex_page = Math.min(maxpage, this.codex_page + 1);
            this.codex_index = this.codex_page * per; Sfx.play('ui');
        } else if (key === 'escape') {
            this.state = 'title'; this.menu_index = 0; Sfx.play('ui');
        }
    };
    Game.prototype._codexSyncPage = function () {
        var per = Math.max(1, ((VIEW_H - 110) / 15) | 0);
        var items = codexItems(this, ['enemy', 'weapon', 'material', 'collect'][this.codex_cat % 4]);
        var maxpage = items.length ? Math.floor((items.length - 1) / per) : 0;
        var idx = Math.max(0, Math.min(this.codex_index, Math.max(0, items.length - 1)));
        this.codex_index = idx;
        this.codex_page = Math.max(0, Math.min(maxpage, Math.floor(idx / per)));
    };
    // ---- 展示台分页按键
    Game.prototype._keydownShowcase = function (key) {
        if (key === 'arrowleft' || key === 'a') {
            this.showcase_index = ((this.showcase_index - 1) % 6 + 6) % 6; Sfx.play('ui');
        } else if (key === 'arrowright' || key === 'd') {
            this.showcase_index = (this.showcase_index + 1) % 6; Sfx.play('ui');
        } else if (key === 'arrowup' || key === 'w') {
            this.showcase_index = (this.showcase_index + 3) % 6; Sfx.play('ui');
        } else if (key === 'arrowdown' || key === 's') {
            this.showcase_index = (this.showcase_index + 3) % 6; Sfx.play('ui');
        } else if (key === 'e' || key === 'f') {
            this.showcase_toggle();
        } else if (key === 'escape') {
            this.state = 'title'; this.menu_index = 0; Sfx.play('ui');
        }
    };
    Game.prototype.showcase_toggle = function () {
        var prof = this.profile;
        if (!prof) { return false; }
        if (!prof.showcase) { prof.showcase = [null, null, null, null, null, null]; }
        var i = ((this.showcase_index || 0) % 6 + 6) % 6;
        var cur = prof.showcase[i];
        if (cur) {
            // 取出 -> 放回收藏袋
            if (!prof.collects) { prof.collects = []; }
            if (prof.collects.indexOf(cur) < 0) { prof.collects.push(cur); }
            prof.showcase[i] = null;
            Sfx.play('ui');
            this.toast('已取出', (D.COLLECTS[cur] ? D.COLLECTS[cur][0] : cur), [200, 200, 220]);
        } else {
            // 从收藏袋放一件进来
            var bag = [], j;
            for (j = 0; j < (prof.collects || []).length; j++) {
                if (prof.showcase.indexOf(prof.collects[j]) < 0) {
                    bag.push(prof.collects[j]);
                }
            }
            if (!bag.length) {
                Sfx.play('no_energy');
                this.toast('没有更多收藏品', '', [226, 160, 120]);
                return false;
            }
            prof.showcase[i] = bag[0];
            Sfx.play('ui_big');
            this.toast('已摆放', (D.COLLECTS[bag[0]] ? D.COLLECTS[bag[0]][0] : bag[0]),
                [255, 236, 170]);
        }
        this._write_save();
        return true;
    };
    Game.prototype._mouseLobby = function (pos) {
        var p = pos ? [pos[0], pos[1]] : this.mouse_canvas;
        var tab = ((this.lobby_tab || 0) % 4 + 4) % 4;
        var i;
        // TAB 分页条点击
        if (p[1] >= 30 && p[1] <= 47) {
            var tx = VIEW_W / 2 - 124;
            var labels = ['准备', '养成', '图鉴', '展示台'];
            for (i = 0; i < labels.length; i++) {
                var tw = textWidth(labels[i], 11) + 20;
                if (p[0] >= tx && p[0] <= tx + tw) {
                    if (this.lobby_tab !== i) {
                        this.lobby_tab = i; this.lobby_expand = false;
                    }
                    return true;
                }
                tx += tw + 5;
            }
        }
        if (tab === 1) {
            var gx = 20, subs = ['角色', '武器', '技能 / 被动', '天赋'];
            if (p[1] >= 58 && p[1] <= 74) {
                for (i = 0; i < subs.length; i++) {
                    var sw = textWidth(subs[i], 11) + 18;
                    if (p[0] >= gx && p[0] <= gx + sw) {
                        this.growth_sub = i; this.growth_index = 0;
                        return true;
                    }
                    gx += sw + 5;
                }
            }
            if (p[0] >= 16 && p[0] <= 216 && p[1] >= 82) {
                var rows = this._growthRows();
                var visible = Math.max(1, ((VIEW_H - 60 - 82) / 26) | 0);
                var sel = Math.max(0, Math.min(this.growth_index || 0, rows.length - 1));
                var first = Math.max(0, Math.min(sel - (visible >> 1),
                    Math.max(0, rows.length - visible)));
                var row = Math.floor((p[1] - 82) / 26);
                var idx = first + row;
                if (row >= 0 && row < visible && idx < rows.length) {
                    if (this.growth_index === idx) { this._keydownGrowth('enter'); }
                    else { this.growth_index = idx; }
                    return true;
                }
            }
            return false;
        }
        if (tab === 2) {
            // 分类标签
            var cats = ['enemy', 'weapon', 'material', 'collect'];
            var x = 16;
            for (i = 0; i < cats.length; i++) {
                var cnt = (((this.profile || {}).codex || {})[cats[i]] || []).length;
                var head = ((D.CODEX_CATS && D.CODEX_CATS[cats[i]]) || cats[i])
                    + ' ' + cnt + '/' + codexTotal(cats[i]);
                var w = textWidth(head, 10) + 16;
                if (p[0] >= x && p[0] <= x + w && p[1] >= 56 && p[1] <= 73) {
                    this.codex_cat = i; this.codex_index = 0; this.codex_page = 0;
                    return true;
                }
                x += w + 5;
            }
            // 条目列表
            if (p[0] >= 16 && p[0] <= 266) {
                var per = Math.max(1, ((VIEW_H - 110) / 15) | 0);
                var items = codexItems(this, cats[((this.codex_cat || 0) % 4 + 4) % 4]);
                var start = (this.codex_page || 0) * per;
                for (i = 0; i < per; i++) {
                    var yy = 80 + i * 15;
                    if (p[1] >= yy - 1 && p[1] <= yy + 13 && start + i < items.length) {
                        this.codex_index = start + i;
                        return true;
                    }
                }
            }
            return false;
        }
        if (tab === 3) {
            // 3x2 网格
            var gx = 60, gy = 84, cw = 168, ch = 96;
            for (i = 0; i < 6; i++) {
                var col = i % 3, row = (i / 3) | 0;
                var gxx = gx + col * (cw + 12), gyy = gy + row * (ch + 12);
                if (p[0] >= gxx && p[0] <= gxx + cw &&
                    p[1] >= gyy && p[1] <= gyy + ch) {
                    if (this.showcase_index === i) { this.showcase_toggle(); }
                    else { this.showcase_index = i; }
                    return true;
                }
            }
            return false;
        }
        // 分页 0：关卡卡片
        if (p[0] < LOBBY_LX || p[0] > LOBBY_LX + LOBBY_LW) { return false; }
        var y = 56, order = this._lobbyOrder();
        for (i = 0; i < order.length; i++) {
            if (p[1] >= y && p[1] <= y + LOBBY_CARD_H) {
                if (this.lobby_index !== i) {
                    this.lobby_index = i;
                    this.lobby_expand = false;
                }
                return true;
            }
            y += LOBBY_CARD_H + LOBBY_GAP;
            if (y > VIEW_H - 28) { break; }
        }
        return false;
    };
    Object.defineProperty(Game.prototype, 'props', {
        get: function () { return this.room ? this.room.props : []; }
    });
    Object.defineProperty(Game.prototype, 'pickups', {
        get: function () { return this.room ? this.room.pickups : []; }
    });
    Object.defineProperty(Game.prototype, 'total_damage', {
        get: function () { return this.player.dmg_taken; }
    });

    // ---- 存档（等价于 Python 版写到用户目录的 JSON）
    Game.prototype._load_save = function () {
        // 需求 10：优先从 3 槽仓库取"上次玩的档"；没有则留空（等玩家选槽）
        try {
            SaveStore.load();
        } catch (e) { /* 隐私模式等场景下静默忽略 */ }
        this.profile = null;
        try {
            this.profile = SaveStore.current();
        } catch (e) { this.profile = null; }
        if (this.profile) {
            var st = this.profile.stats || {};
            this.best_floor = Math.trunc(st.best_chapter || 0);
            this.best_kills = Math.trunc(st.kills || 0);
            this._load_settings_from_profile();
        } else {
            this.best_floor = 0;
            this.best_kills = 0;
            // 无档时仍兼容旧版单文件存档里的设置（升级迁移的兜底）
            try {
                var raw = window.localStorage.getItem(SAVE_KEY);
                if (raw) {
                    var d = JSON.parse(raw);
                    if (d && d.setting && typeof d.setting === 'object') {
                        for (var k in d.setting) {
                            if (Object.prototype.hasOwnProperty.call(d.setting, k)) {
                                this.setting[k] = d.setting[k];
                            }
                        }
                    }
                }
            } catch (e2) { /* 忽略 */ }
        }
        this._applyAudioSettings();
    };
    // 从存档读设置（每档独立）
    Game.prototype._load_settings_from_profile = function () {
        var prof = this.profile;
        if (!prof || typeof prof !== 'object') { return; }
        var s = prof.settings;
        if (s && typeof s === 'object') {
            for (var k in s) {
                if (Object.prototype.hasOwnProperty.call(s, k)) {
                    this.setting[k] = s[k];
                }
            }
            if (!prof.v22_sfx_migrated && !s.sfx && !s.music && !s.shake && !s.vibrate) {
                this.setting.sfx = true;
                prof.v22_sfx_migrated = true;
                prof.settings.sfx = true;
            }
            if (!prof.v35_aim_assist_migrated && window.__TOUCH__ && window.__TOUCH__.enabled) {
                this.setting.aim_assist = true;
                prof.v35_aim_assist_migrated = true;
                prof.settings.aim_assist = true;
            }
        }
        this._applyAudioSettings();
    };
    // 把设置写回存档
    Game.prototype.save_settings = function () {
        if (!this.profile || typeof this.profile !== 'object') { return; }
        this.profile.settings = {};
        for (var k in this.setting) {
            if (Object.prototype.hasOwnProperty.call(this.setting, k)) {
                this.profile.settings[k] = this.setting[k];
            }
        }
        this._write_save();
    };
    Game.prototype._write_save = function () {
        try {
            var f = this.floor ? Math.trunc(this.floor) : 0;
            this.best_floor = Math.max(this.best_floor, f);
            this.best_kills = Math.max(this.best_kills, Math.trunc(this.kills || 0));
        } catch (e) { /* 忽略 */ }
        if (!this.profile) {
            // 无档环境（无头测试 / 未建档）只更新内存最佳记录，保持单调
            try {
                window.localStorage.setItem(SAVE_KEY, JSON.stringify({
                    best_floor: this.best_floor, best_kills: this.best_kills,
                    setting: this.setting || {}
                }));
            } catch (e2) { /* 忽略 */ }
            return;
        }
        try {
            var st = this.profile.stats || (this.profile.stats = {});
            st.kills = Math.max(Math.trunc(st.kills || 0), Math.trunc(this.kills || 0));
            st.best_chapter = Math.max(Math.trunc(st.best_chapter || 0),
                                       Math.trunc(f));
            // 需求 4：货币与材料在退出/过场时结算进档
            if (this.level_state && this.state !== 'lobby') {
                this.profile.diamonds = D.clampDiamond(this.diamonds || 0);
            }
            if (this.mats) {
                var pm = this.profile.materials || (this.profile.materials = {});
                for (var k2 in this.mats) {
                    if (Object.prototype.hasOwnProperty.call(this.mats, k2)) {
                        pm[k2] = Math.trunc(pm[k2] || 0) + Math.trunc(this.mats[k2] || 0);
                    }
                }
                this.mats = {};
            }
            this.profile.updated = Date.now() / 1000.0;
            SaveStore.flush(this.profile);
        } catch (e3) { /* 存档失败绝不能拖垮游戏 */ }
    };

    // ---- 档位管理（需求 10：个人 ID / 3 槽 / 覆盖确认 / 删除）
    Game.prototype.slot_list = function () {
        try { return SaveStore.slots(); } catch (e) { return [null, null, null]; }
    };
    Game.prototype.has_profile = function () { return this.profile !== null; };
    Game.prototype.create_profile = function (idx, name) {
        this.profile = SaveStore.create(idx, name || '');
        this.best_floor = 0; this.best_kills = 0;
        this.coins = 0; this.diamonds = 0; this.level_state = null;
        this.setting = defaultSettings();
        this._load_settings_from_profile();
        return true;
    };
    Game.prototype.select_profile = function (idx) {
        var p = SaveStore.get(idx);
        if (!p) { return false; }
        SaveStore.setCurrent(idx);
        this.profile = p;
        this.coins = p.coins || 0;
        this.diamonds = p.diamonds || 0;
        this.level_state = null;
        var st = p.stats || {};
        this.best_floor = Math.trunc(st.best_chapter || 0);
        this.best_kills = Math.trunc(st.kills || 0);
        this._load_settings_from_profile();
        return true;
    };
    Game.prototype.delete_profile = function (idx) {
        SaveStore.remove(idx);
        if (this.profile && this.profile.id === idx) { this.profile = null; }
        return true;
    };
    Game.prototype.save_now = function () { this._write_save(); };
    Game.prototype.backup_snapshot = function () {
        this._write_save();
        return JSON.stringify({format: 'ashen-save-3', version: 1,
            slots: SaveStore.slots(), last: SaveStore.data.last});
    };
    Game.prototype.import_backup = function (raw) {
        if (typeof raw !== 'string' || raw.length > 4 * 1024 * 1024) { return false; }
        var data;
        try { data = JSON.parse(raw); } catch (e) { return false; }
        if (!data || data.format !== 'ashen-save-3' || !Array.isArray(data.slots)
                || data.slots.length > MAX_SLOTS) { return false; }
        var count = 0, slots = SaveStore.slots();
        for (var i = 0; i < data.slots.length; i++) {
            var incoming = data.slots[i];
            if (!incoming || typeof incoming !== 'object' || Array.isArray(incoming)) { continue; }
            incoming = migrateProfile(incoming);
            incoming.id = i;
            var previous = slots[i];
            var merged = moreAdvanced(previous, incoming);
            if (merged === incoming) { slots[i] = incoming; count++; }
            if (mergeRouteClaims(slots[i], merged === incoming ? previous : incoming)) {
                count++;
            }
        }
        if (!count) { return false; }
        SaveStore.data.slots = slots;
        if (SaveStore.data.last === null && typeof data.last === 'number' &&
                slots[data.last]) { SaveStore.data.last = data.last; }
        SaveStore.save();
        if (this.profile && slots[this.profile.id]) {
            this.select_profile(this.profile.id);
        }
        return true;
    };
    Game.prototype.export_backup = function () {
        var raw = this.backup_snapshot();
        var file = new File([raw], '余烬禁区-存档.json', {type: 'application/json'});
        if (navigator.canShare && navigator.share && navigator.canShare({files: [file]})) {
            navigator.share({files: [file], title: '余烬禁区存档'}).catch(function () {});
            return;
        }
        if (window.Capacitor && window.Capacitor.isNativePlatform &&
                window.Capacitor.isNativePlatform()) {
            if (navigator.clipboard && navigator.clipboard.writeText) {
                navigator.clipboard.writeText(raw).then(function () {
                    window.alert('存档内容已复制，可粘贴保存为文本文件。');
                }).catch(function () { window.alert('此设备不支持分享存档。'); });
            } else { window.alert('此设备不支持分享存档。'); }
            return;
        }
        var url = URL.createObjectURL(file), a = document.createElement('a');
        a.href = url; a.download = file.name; document.body.appendChild(a);
        a.click(); a.remove();
        window.setTimeout(function () { URL.revokeObjectURL(url); }, 30000);
    };
    Game.prototype.choose_backup = function () {
        var self = this, input = document.createElement('input');
        input.type = 'file'; input.accept = '.json,application/json';
        input.onchange = function () {
            var file = input.files && input.files[0];
            if (!file || file.size > 4 * 1024 * 1024) {
                window.alert('存档文件为空或超过 4 MB。'); return;
            }
            var reader = new FileReader();
            reader.onload = function () {
                window.alert(self.import_backup(String(reader.result || '')) ?
                    '存档已导入；已有更高进度的档位会保留。' : '存档格式无效或没有更高进度。');
            };
            reader.readAsText(file);
        };
        input.click();
    };
    Game.prototype._bankRunCoins = function () {
        if (!this.profile || this._coins_banked) { return; }
        this.profile.coins = D.clampCoin((this.profile.coins || 0) + (this.coins || 0));
        this.profile.run_checkpoint = null;
        if (D.resetCycle) { D.resetCycle(this.profile); }
        this._coins_banked = true;
        this._write_save();
    };
    Game.prototype.settle_run = function () {
        this._bankRunCoins();
        this._write_save();
        this.state = 'title';
        this.menu_index = 0;
    };

    // ---- 局内提示与资源发放（需求 4、15）
    Game.prototype.toast = function (title, sub, color, life) {
        // 同标题只刷新计时，避免刷屏
        color = color || C_TEXT;
        sub = sub || '';
        life = life || 2.4;
        for (var i = 0; i < this.toasts.length; i++) {
            var t = this.toasts[i];
            if (t.title === title) {
                t.t = 0.0; t.life = life;
                if (sub) { t.sub = sub; }
                return;
            }
        }
        this.toasts.push({ title: title, sub: sub, color: color, t: 0.0, life: life });
        if (this.toasts.length > 4) { this.toasts.shift(); }
    };
    Game.prototype.grant_material = function (key, n) {
        n = n === undefined ? 1 : n;
        if (n <= 0 || !key) { return 0; }
        this.mats[key] = (this.mats[key] || 0) + Math.floor(n);
        try { this.discover('material', key); } catch (e) { /* 忽略 */ }
        var name = D.MATERIALS[key] ? D.MATERIALS[key][0] : key;
        this.fx.text(this.player.x, this.player.y - 30,
            '+' + Math.floor(n) + ' ' + name, [198, 220, 255], 1.1);
        this._write_save();
        return Math.floor(n);
    };
    Game.prototype.grant_diamond = function (n) {
        n = n === undefined ? 1 : n;
        if (n <= 0) { return 0; }
        this.diamonds += Math.floor(n);
        this.fx.text(this.player.x, this.player.y - 30,
            '+' + Math.floor(n) + ' 钻石', [150, 232, 255], 1.1);
        return Math.floor(n);
    };

    // ---- 图鉴（需求 8/15）：enemy / weapon / material / collect
    Game.prototype.discover = function (cat, key, silent) {
        if (!key) { return false; }
        var prof = this.profile;
        if (!prof) {
            var hit = false, i;
            for (i = 0; i < this.new_codex.length; i++) {
                if (this.new_codex[i][0] === cat && this.new_codex[i][1] === key) {
                    hit = true; break;
                }
            }
            if (!hit) { this.new_codex.push([cat, key]); return true; }
            return false;
        }
        if (!prof.codex) { prof.codex = {}; }
        if (!prof.codex[cat]) { prof.codex[cat] = []; }
        var lst = prof.codex[cat];
        if (lst.indexOf(key) >= 0) { return false; }
        lst.push(key);
        if (!silent) { this._codexToast(cat, key); }
        return true;
    };
    Game.prototype._codexInfo = function (cat, key) {
        try {
            if (cat === 'enemy') { return D.ENEMY_CODEX[key]; }
            if (cat === 'collect') { return D.COLLECTS[key]; }
            if (cat === 'material') { return D.MATERIALS ? D.MATERIALS[key] : null; }
            if (cat === 'weapon') { return D.WEAPON_CODEX ? D.WEAPON_CODEX[key] : null; }
        } catch (e) { /* 忽略 */ }
        return null;
    };
    Game.prototype._codexToast = function (cat, key) {
        var info = this._codexInfo(cat, key);
        var name = key, desc = '';
        if (info) {
            if (Array.isArray(info)) {
                name = info.length > 0 ? info[0] : key;
                desc = info.length > 2 ? info[info.length - 1] : '';
            } else if (typeof info === 'object') {
                name = info.name || key;
                desc = info.desc || '';
            }
        }
        var tag = (D.CODEX_CATS && D.CODEX_CATS[cat]) || '图鉴';
        this.toast('新' + tag + '：' + name, desc, [170, 230, 255], 3.0);
        this.new_codex.push([cat, key]);
    };
    Game.prototype.collect_got = function (key) {
        if (!key) { return false; }
        var prof = this.profile;
        this.discover('collect', key);
        if (!prof) { return true; }
        if (!prof.collects) { prof.collects = []; }
        var first = (prof.collects.indexOf(key) < 0);
        if (first) {
            prof.collects.push(key);
            var unlocked = D.syncCollectCharacters ? D.syncCollectCharacters(prof) : [];
            for (var u = 0; u < unlocked.length; u++) {
                var hero = D.CHARACTERS[unlocked[u]];
                this.toast('新角色解锁：' + hero.name, '可在客厅角色页选择', [255, 226, 150], 3.5);
            }
            if (!prof.showcase) { prof.showcase = [null, null, null, null, null, null]; }
            for (var i = 0; i < prof.showcase.length; i++) {
                if (prof.showcase[i] === null || prof.showcase[i] === undefined) {
                    prof.showcase[i] = key; break;
                }
            }
            this._write_save();
        }
        return first;
    };

    // ---- 流程
    // scene 为 undefined 时用进度层已存的断点；都没有则从第一主线场景第 1 关开始
    Game.prototype.start_run = function (scene, stageIdx) {
        var pendingCp = this.profile && this.profile.run_checkpoint;
        this.rng = makeRng(this.seed);
        this.player = new Player(ROOM_CX, ROOM_CY);
        this.char_skill_cd = 0;
        this.drink_stages = {};
        (D.allScenes ? D.allScenes() : ['crust', 'sewer', 'facility', 'core', 'd_mine', 'd_lab', 'd_gift']).forEach(function (sceneKey) {
            var a, b, pid = this.profile && this.profile.id;
            if (pid !== undefined && pid !== null) {
                var created = Math.floor(Number(this.profile.created || 0) * 1000);
                var raw = String(pid) + '|' + created + '|' + sceneKey, h = 2166136261;
                for (var j = 0; j < raw.length; j++) {
                    h = Math.imul(h ^ raw.charCodeAt(j), 16777619) >>> 0;
                }
                a = h % 5; b = Math.floor(h / 5) % 4;
            } else {
                a = this.rng.randint(0, 4); b = this.rng.randint(0, 3);
            }
            if (b >= a) { b++; }
            this.drink_stages[sceneKey] = [a, b];
        }, this);
        this.drink_buffs = {};
        this.coins = 0;
        this._coins_banked = false;
        this.kills = 0;
        this.combo_count = 0;
        this.combo_t = 0.0;
        this.total_time = 0.0;
        this._explode_depth = 0;
        this.hint_t = 13.0;
        this.diamonds = this.profile ? (this.profile.diamonds || 0) : 0;
        this.mats = {};
        this.toasts = [];
        this.run_kills = 0;
        this.run_deaths = 0;
        // 需求：副本准入条件追踪 + 污染减益
        this.run_trap_hits = 0;
        this.run_bomber_hits = 0;
        this.run_items = 0;
        this.run_low_hp = false;
        this._drain_acc = 0.0;
        this.pollution = null;
        this.pollution_spd = 1.0;
        this.pollution_regen = 1.0;
        this.pollution_drain = 0.0;
        this._pur = null;
        this._purge_t = 0.0;
        this._stage_done = false;
        // 1.1 天赋 / 过场
        this.talents_owned = [];
        this.run_stats = null;
        this.pending_talents = null;
        this.talent_pick = 0;
        this._pending_story = null;
        this.transition_lock = 0.0;
        this.story_scene = null;
        this.story_lines = [];
        this.story_t = 0.0;
        this.pending_after = null;
        // 图鉴
        this.new_codex = [];
        // 防卡死状态
        this._stuck_t = 0.0;
        this._stuck_rescues = 0;
        this._last_pos = null;
        this._last_mx = 0.0;
        this._last_my = 0.0;
        this.level_state = this._resolveLevelState(scene, stageIdx);
        this.route_state = 'none'; this.route_room = null;
        this.route_sealed = false; this.route_index = 0;
        this.story_scene = null;
        this.story_lines = [];
        this.story_t = 0.0;
        this.story_page = 0;
        this.pending_after = null;
        this.transition_lock = 0.0;
        this._applyLoadout();
        var ls = this.level_state || {};
        if (pendingCp && pendingCp.scene === ls.scene &&
            Math.trunc(pendingCp.stage_idx || 0) === Math.trunc(ls.stage_idx || 0)) {
            this._start_floor(Math.max(1, Math.min(FLOORS, Math.trunc(pendingCp.floor || 1))),
                pendingCp.seed, false);
            this._restoreFloorCheckpoint(pendingCp);
            if (this.route_state !== 'pending') { this.state = 'playing'; }
            return;
        }
        this._startFloorWithStory();
    };
    // 需求 6/7：把存档里的角色、武器、技能/被动等级应用进本局
    Game.prototype._applyLoadout = function () {
        var prof = this.profile || {};
        var pl = this.player;
        if (!pl) { return; }
        var ckey = prof.char || this.char_key || 'scout';
        this.char_key = ckey;
        var c = null;
        try { c = D.CHARACTERS[ckey]; } catch (e) { c = null; }
        if (!c) { c = { hp: P_MAX_HP, spd: 1.0, energy: P_MAX_ENERGY, starter: 'pistol' }; }
        var sk = prof.skills || {}, pv = prof.passives || {};
        var hp = Math.trunc(c.hp || P_MAX_HP);
        var spd = parseFloat(c.spd) || 1.0;
        var energy = parseFloat(c.energy) || P_MAX_ENERGY;
        hp += Math.trunc(sk.vital || 0);
        spd *= (1.0 + 0.03 * Math.trunc(sk.haste || 0));
        energy *= (1.0 + 0.08 * Math.trunc(sk.focus || 0));
        this.char_power_mul = 0.04 * Math.trunc(sk.power || 0);
        this.char_fortune_mul = 1.0 + 0.10 * Math.trunc(sk.fortune || 0);
        this.char_guard_mul = 1.0 + 0.08 * Math.trunc(sk.guard || 0);
        this.char_thorns_ratio = 0.15 * Math.trunc(pv.thorns || 0);
        this.char_regen_rate = 0.25 * Math.trunc(pv.regen || 0);
        this.char_magnet_mul = 0.20 * Math.trunc(pv.magnet || 0);
        this.char_crit_bonus = 0.04 * Math.trunc(pv.crit || 0);
        this.char_pierce_bonus = Math.trunc(pv.pierce || 0);
        pl.max_hp = Math.max(1, hp);
        pl.hp = pl.max_hp;
        pl.max_energy = Math.max(20.0, energy);
        pl.energy = pl.max_energy;
        this._loadout_hp = pl.max_hp;
        this._loadout_energy = pl.max_energy;
        this.char_spd_mul = spd / P_SPEED;
        var wkey = prof.weapon || c.starter || 'pistol';
        var pool = {};
        try { pool = D.WEAPONS || {}; } catch (e2) { pool = {}; }
        if (!pool[wkey]) { wkey = c.starter || 'pistol'; }
        pl.wkey = wkey;
        pl.wqual = D.qualityForWeapon(wkey);
        this.recomputeTalents();
    };
    // 决定这一局从哪个场景的哪一关开始（与 Python progress 层对齐）
    Game.prototype._resolveLevelState = function (scene, stageIdx) {
        // 与 Python Game._resolve_level_state 对齐：
        //   无档 -> 第一主线场景兜底
        //   指定场景 -> 写进档的 run（含 start_scene / next_stage）
        //   未指定 -> 用档里已有的断点；没有断点则从第一关起
        var prof = this.profile;
        var order = D.sceneOrder(prof || {});
        if (!prof) {
            if (!scene) { scene = order[0]; }
            var i0 = order.indexOf(scene);
            if (i0 < 0) { i0 = 0; scene = order[0]; }
            return {
                scene: scene, scene_idx: i0, stage_idx: Math.floor(stageIdx || 0),
                diff: D.difficulty(i0, Math.floor(stageIdx || 0)),
                kind: D.stageKind(Math.floor(stageIdx || 0)), floors: 3
            };
        }
        if (scene !== undefined && scene !== null) {
            if (order.indexOf(scene) < 0) { scene = order[0]; }
            D.startScene(prof, scene);
            if (stageIdx) { D.nextStage(prof, scene, Math.floor(stageIdx)); }
            if (prof.run) { return prof.run; }
        }
        if (prof.run) { return prof.run; }
        // 档里没有断点 -> 从第一关开始
        D.startScene(prof, order[0]);
        return prof.run;
    };
    Game.prototype._start_floor = function (floor, floorSeed, capture) {
        this.floor = floor;
        this.floor_seed = (floorSeed !== undefined && floorSeed !== null) ?
            (Number(floorSeed) >>> 0) : (this.rng.randint(0, 4294967295) >>> 0);
        this.rng = makeRng(this.floor_seed);
        // 关卡进度（场景/小关/难度）由 progress 层写入 level_state
        var scene = null, stageIdx = 0, diff = [1.0, 1.0];
        var ls = this.level_state;
        if (ls && typeof ls === 'object') {
            if (ls.scene !== undefined) { scene = ls.scene; }
            stageIdx = Math.floor(ls.stage_idx || 0);
            if (ls.diff) { diff = ls.diff; }
        }
        if (floor <= 1) { this._resetStageTrackers(); }
        // 需求 11：换场景时同步 BGM 情绪档
        try { Music.play(this.music_mood()); } catch (e) { /* 忽略 */ }
        var drinkStage = (this.drink_stages || {})[scene] || [];
        var luckB = (this.run_stats && this.run_stats.luck) || 0.0;
        this.dungeon = new Dungeon(floor, this.rng, scene, stageIdx, diff,
            drinkStage.indexOf(stageIdx) >= 0, luckB);
        this.route_room = this.dungeon.chooseSurveyRoom();
        this.route_state = this.route_room ? 'pending' : 'none';
        this.route_sealed = false; this.route_index = 0;
        this.bullets = [];
        this.enemies = [];
        this.boss = null;
        this.fx.clear();
        var key = this.dungeon.start_key;
        this.room = null;
        this.enter_room(key[0], key[1], null, true);
        this.player.x = ROOM_CX;
        this.player.y = ROOM_CY;
        // 需求：污染渐近减益（每个场景重新计算一次基准）
        this._applyPollution(scene, stageIdx);
        this.player.hp = Math.min(this.player.max_hp, this.player.hp + 3);
        this.player.energy = this.player.max_energy;
        this.player.iframes = Math.max(this.player.iframes, 1.0);
        this.player.shield_charges = (this.run_stats &&
            (this.run_stats.flags || []).indexOf('shield') >= 0) ? 1 : 0;
        this.state = this.route_state === 'pending' ? 'route_choice' : 'playing';
        if (capture !== false) { this._captureFloorCheckpoint(); }
    };
    Game.prototype._captureFloorCheckpoint = function () {
        if (!this.profile) { return; }
        var pl = this.player, ls = this.level_state || {}, fields =
            ['hp', 'energy', 'wkey', 'wqual', 'wkey2', 'wqual2'];
        var player = {};
        for (var i = 0; i < fields.length; i++) { player[fields[i]] = pl[fields[i]]; }
        this.profile.run_checkpoint = {
            scene: ls.scene, stage_idx: Math.trunc(ls.stage_idx || 0),
            floor: this.floor, seed: this.floor_seed, coins: this.coins,
            diamonds: this.diamonds, player: player,
            drinks: Object.assign({}, this.drink_buffs || {}),
            talents: (this.talents_owned || []).slice(),
            run_stats: this.run_stats ? JSON.parse(JSON.stringify(this.run_stats)) : null,
            kills: this.kills, run_kills: this.run_kills, run_items: this.run_items,
            total_time: this.total_time, run_deaths: this.run_deaths,
            run_trap_hits: this.run_trap_hits, run_bomber_hits: this.run_bomber_hits,
            run_low_hp: this.run_low_hp, run_diamonds: this.run_diamonds || 0
            ,route_id: this.route_room ? 'mine_survey_02' : null,
            route_room: this.route_room && this.route_room.slice(),
            route_state: this.route_state
        };
        this._write_save();
    };
    Game.prototype._restoreFloorCheckpoint = function (cp) {
        if (cp.route_id === 'mine_survey_02' && this.route_room && cp.route_room &&
            cp.route_room[0] === this.route_room[0] && cp.route_room[1] === this.route_room[1] &&
            (cp.route_state === 'normal' || cp.route_state === 'survey')) {
            this.route_state = cp.route_state;
            this.state = 'playing';
        }
        var pl = this.player;
        this.coins = Math.trunc(cp.coins || 0);
        this.diamonds = Math.trunc(cp.diamonds === undefined ? this.diamonds : cp.diamonds);
        this.drink_buffs = Object.assign({}, cp.drinks || {});
        this.talents_owned = (cp.talents || []).slice();
        this.recomputeTalents();
        this.kills = Math.trunc(cp.kills || 0);
        this.run_kills = Math.trunc(cp.run_kills || 0);
        this.run_items = Math.trunc(cp.run_items || 0);
        this.total_time = Number(cp.total_time || 0);
        this.run_deaths = Math.trunc(cp.run_deaths || 0);
        this.run_trap_hits = Math.trunc(cp.run_trap_hits || 0);
        this.run_bomber_hits = Math.trunc(cp.run_bomber_hits || 0);
        this.run_low_hp = !!cp.run_low_hp;
        this.run_diamonds = Math.trunc(cp.run_diamonds || 0);
        var ls = this.level_state || {};
        this._applyPollution(ls.scene, Math.trunc(ls.stage_idx || 0));
        var saved = cp.player || {};
        ['hp', 'energy', 'wkey', 'wqual', 'wkey2', 'wqual2'].forEach(function (key) {
            if (saved[key] !== undefined) { pl[key] = saved[key]; }
        });
        pl.hp = Math.max(1, Math.min(pl.hp, pl.max_hp));
        pl.energy = Math.max(0, Math.min(pl.energy, pl.max_energy));
        pl.shield_charges = (this.run_stats &&
            (this.run_stats.flags || []).indexOf('shield') >= 0) ? 1 : 0;
    };
    Game.prototype._chooseRoute = function (index) {
        if (this.route_state !== 'pending') { return; }
        this.route_index = index;
        this.route_state = index === 1 ? 'survey' : 'normal';
        this.state = 'playing';
        if (index === 1) {
            this.toast('勘测已启用', '清空标记支路后从出口撤离', [243, 184, 91], 2);
            Sfx.play('lock');
        }
        this._captureFloorCheckpoint();
    };
    // _start_floor 的过场包装：首次进入某场景时先播进场过场
    Game.prototype._startFloorWithStory = function () {
        this._start_floor(1);
        var ls = this.level_state || {};
        var sc = ls.scene, si = Math.floor(ls.stage_idx || 0);
        if (sc && si === 0 && this.profile) {
            var first = (this.profile.cleared_scenes || []).indexOf(sc) < 0;
            if (first) {
                this._startStory('stage_enter', sc, 0, ['enter', null]);
                return;
            }
        }
        if (this.route_state !== 'pending') { this.state = 'playing'; }
    };
    // 把当前场景的污染减益写进玩家属性 + 弹警告
    Game.prototype._applyPollution = function (scene, stageIdx) {
        this.pollution = scene ? D.pollution(scene, stageIdx) : null;
        var pl = this.player;
        var extraHp = 0, extraEnergy = 0.0;
        var baseHp = this._loadout_hp || P_MAX_HP;
        var baseEnergy = this._loadout_energy || P_MAX_ENERGY;
        var hpMult = 1.0 + 0.25 * ((this.drink_buffs && this.drink_buffs.nectar) || 0);
        if (this.run_stats) {
            extraHp = this.run_stats.max_hp || 0;
            extraEnergy = this.run_stats.max_energy || 0;
        }
        var p = this.pollution;
        if (!p) {
            pl.max_hp = (baseHp + extraHp) * hpMult;
            pl.max_energy = baseEnergy + extraEnergy;
            pl.hp = Math.min(pl.hp, pl.max_hp);
            pl.energy = Math.min(pl.energy, pl.max_energy);
            this._pur = [0, 1.0, 1.0, 0.0];
            this.pollution_spd = 1.0;
            this.pollution_regen = 1.0;
            this.pollution_drain = 0.0;
            return;
        }
        // 1.3：抗污染天赋在这里生效 —— 所有减益先过一遍抗性
        var pur = (typeof D.purTintAmount === 'function')
            ? D.purTintAmount(p, this.run_stats)
            : [p.hp_cut, p.spd, p.regen, p.drain];
        this._pur = pur;
        pl.max_hp = Math.max(1, baseHp + extraHp - (pur[0] | 0)) * hpMult;
        pl.max_energy = Math.max(20.0, baseEnergy + extraEnergy);
        pl.hp = Math.min(pl.hp, pl.max_hp);
        this.pollution_spd = pur[1];
        this.pollution_regen = pur[2];
        this.pollution_drain = pur[3];
        if (pur[0] > 0 || pur[1] < 0.999 || pur[3] > 0) {
            var lines = D.pollutionLines(scene, stageIdx);
            var title = '污染浓度 ' + p.pct + '%';
            if (p.drain > 0 && pur[3] < p.drain) {
                title += '（抗性 -' +
                    Math.round((1.0 - pur[3] / p.drain) * 100) + '%）';
            }
            this.toast(title, lines.join(' · '), [236, 128, 150]);
        }
    };
    // 每秒扣血（污染侵蚀）
    Game.prototype._updatePollution = function (dt) {
        var pl = this.player;
        var drain = this.pollution_drain || 0.0;
        if (drain <= 0 || !pl.alive) { this._drain_acc = 0.0; return; }
        this._drain_acc = (this._drain_acc || 0.0) + drain * dt;
        // 1.3「净化循环」：每 PUR_PURGE_INTERVAL 秒清一次累积
        if (typeof D.hasPurPurge === 'function' && D.hasPurPurge(this.run_stats)) {
            this._purge_t = (this._purge_t || 0.0) + dt;
            if (this._purge_t >= D.PUR_PURGE_INTERVAL) {
                this._purge_t -= D.PUR_PURGE_INTERVAL;
                this._drain_acc = 0.0;
                this.fx.text(pl.x, pl.y - 30, '净化', [120, 250, 210], 11, 0.9);
                return;
            }
        }
        if (this._drain_acc >= 1.0) {
            var n = Math.floor(this._drain_acc);
            this._drain_acc -= n;
            pl.hp -= n;
            this.fx.text(pl.x, pl.y - 26, '-' + n + ' 侵蚀', [196, 90, 120], 11, 0.8);
            if (pl.hp <= 0) { pl.hp = 0.0; pl.die(this); }
        }
    };
    // 1.3「污染共鸣」：浓度转化的伤害加成
    Game.prototype.purDmgMul = function () {
        if (typeof D.purWardBonus !== 'function') { return 0.0; }
        return D.purWardBonus(this.pollution, this.run_stats);
    };
    Game.prototype._resetStageTrackers = function () {
        this.run_kills = 0;
        this.run_deaths = 0;
        this.run_trap_hits = 0;
        this.run_bomber_hits = 0;
        this.run_items = 0;
        this.run_low_hp = false;
        this._drain_acc = 0.0;
        this._stage_done = false;
    };
    Game.prototype.on_trap_hit = function () {
        this.run_trap_hits = (this.run_trap_hits || 0) + 1;
    };
    Game.prototype.on_bomber_hit = function () {
        this.run_bomber_hits = (this.run_bomber_hits || 0) + 1;
    };
    Game.prototype._sceneStats = function () {
        return {
            kills: this.run_kills | 0,
            items: this.run_items | 0,
            deaths: this.run_deaths | 0,
            trap_hits: this.run_trap_hits | 0,
            bomber_hits: this.run_bomber_hits | 0,
            no_death: (this.run_deaths | 0) === 0,
            low_hp: !!this.run_low_hp
        };
    };
    // 一关打完：写入成绩 + 检查副本解锁
    Game.prototype._finishStage = function () {
        if (this._stage_done) { return; }
        this._stage_done = true;
        var ls = this.level_state || {};
        if (!ls.scene) { return; }
        if (this.player.alive && this.player.hp <= 3.0) { this.run_low_hp = true; }
        // 无存档（无头测试 / 未建档）时不写成绩，只更新内存计数
        if (this.profile && typeof D.mergeSceneBest === 'function') {
            D.mergeSceneBest(this.profile, ls.scene, this._sceneStats());
        }
        if (this.profile && this.route_state === 'survey' && this.route_sealed) {
            var claimed = this.profile.route_first_rewards ||
                (this.profile.route_first_rewards = []);
            if (claimed.indexOf('mine_survey_02') < 0) {
                var mats = this.profile.materials || (this.profile.materials = {});
                mats.crystal = Math.trunc(mats.crystal || 0) + 2;
                claimed.push('mine_survey_02');
                this.toast('首次勘测完成 · 污染结晶 ×2',
                    '回执 02：局部隔离有效', [182, 229, 198], 3);
            } else { this.toast('勘测完成 · 首奖已领取', '', [182, 229, 198], 2); }
        }
    };
    Game.prototype.enter_room = function (gx, gy, entry_door, first) {
        var r = this.dungeon.room(gx, gy);
        if (!r) { return false; }
        var old = this.room;
        // 未清空就离开 -> 下次进来重刷
        if (old && !old.cleared && old !== r) { old.enemies_spawned = false; }
        this.room = r;
        r.visited = true;
        r.build_props();
        r.build_pickups();
        r.build_hazards();   // 需求 3：陷阱 / 掩体 / 奖励洞穴

        this.enemies = [];
        this.bullets = [];
        this.boss = null;
        if (!r.cleared && !r.enemies_spawned) {
            this._spawn_room(r);
            r.enemies_spawned = true;
        }
        r.refresh_doors(!r.cleared && this.enemies.length > 0);

        if (entry_door !== null && entry_door !== undefined) {
            var e = ENTRY_FROM[entry_door];
            // 落点校验：掩体/障碍可能正好生成在门口格上，把玩家塞进墙。
            // 一旦圆心落在实心瓦片内，普通滑动移动会失效（详见 slide 注释）。
            var safe = unstick(e[0], e[1], this.player.radius, r.solid, null,
                               [ROOM_CX, ROOM_CY]);
            this.player.x = safe[0];
            this.player.y = safe[1];
        }
        this._ensurePlayerFree();
        this.trans_fade = first ? 0.0 : 0.30;
        this.banner_text = r.label();
        this.banner_t = first ? 0.0 : 1.6;
        this.prompt = null;
        this.fx.clear();
        // 需求 15：首领出场的专属提示（名号 + 一句简介），与 Python 版一致
        if (r.kind === 'boss' && this.boss) {
            this._boss_intro(this.boss);
        }
        return true;
    };
    // 首领出场提示（需求 15）：横幅 + 图鉴收录 + 音效
    Game.prototype._boss_intro = function (b) {
        var name = (b && b.boss_name) || '首领';
        var title = (b && b.boss_title) || '';
        var label = title ? (title + '  ' + name) : name;
        this.banner_text = label;
        this.banner_t = 3.2;
        try { this.discover('enemy', b ? b.skey : null); } catch (e) { /* 忽略 */ }
        var kind = 'boss';
        try {
            var si = Math.floor(((this.level_state || {}).stage_idx) || 0);
            kind = (D.stageKind ? D.stageKind(si) : 'boss');
        } catch (e) { /* 忽略 */ }
        var tag = (kind === 'miniboss') ? '小首领' : '首领';
        var info = null;
        try { info = D.ENEMY_CODEX[b ? b.skey : null]; } catch (e) { info = null; }
        var desc = (info && info.length > 3) ? info[3] : '';
        this.toast(tag + '登场：' + name, desc, [255, 170, 190], 3.6);
    };
    // 每帧兜底：玩家若落在实心瓦片内，就近拉出来（防卡死最后一道防线）
    Game.prototype._ensurePlayerFree = function () {
        if (!this.room || !this.player.alive) { return; }
        var pl = this.player;
        var blk = this.room.blockers ? this.room.blockers() : null;
        if (collideTest(pl.x, pl.y, pl.radius, this.room.solid, blk)) {
            var s = unstick(pl.x, pl.y, pl.radius, this.room.solid, blk,
                            [ROOM_CX, ROOM_CY]);
            pl.x = s[0];
            pl.y = s[1];
            this._stuck_rescues = (this._stuck_rescues || 0) + 1;
        }
    };

    // 连续"有输入却零位移"超过阈值 -> 自动脱困
    Game.prototype._checkStuck = function (dt) {
        var pl = this.player;
        if (this.state !== 'playing' || !pl.alive) {
            this._stuck_t = 0.0;
            this._last_pos = null;
            return;
        }
        var wantMove = (this._last_mx || this._last_my);
        if (!wantMove) {
            this._stuck_t = 0.0;
            this._last_pos = [pl.x, pl.y];
            return;
        }
        if (!this._last_pos) { this._last_pos = [pl.x, pl.y]; return; }
        var moved = Math.hypot(pl.x - this._last_pos[0], pl.y - this._last_pos[1]);
        if (moved < 0.05) { this._stuck_t += dt; } else { this._stuck_t = 0.0; }
        this._last_pos = [pl.x, pl.y];
        if (this._stuck_t >= STUCK_SECONDS) {
            var blk = this.room.blockers ? this.room.blockers() : null;
            var s = unstick(pl.x, pl.y, pl.radius, this.room.solid, blk,
                            [ROOM_CX, ROOM_CY]);
            pl.x = s[0];
            pl.y = s[1];
            this._stuck_rescues = (this._stuck_rescues || 0) + 1;
            this._stuck_t = 0.0;
            // assets/audio 在某些精简运行环境下可能未注入（如部分测试路径），
            // 脱困本身必须成功，提示效果允许缺失。
            if (this.assets && this.assets.font) {
                this.fx.text(pl.x, pl.y - 30, '已脱困', C_PANEL_HI,
                             this.assets.font(12), 1.2);
            }
            if (this.audio && this.audio.play) { this.audio.play('dash'); }
        }
    };

    Game.prototype._spawn_room = function (r) {
        var plan = r.wave_plans.length ? r.wave_plans[r.wave_index] : r.spawn_plan;
        for (var i = 0; i < plan.length; i++) {
            var sp = plan[i];
            var kind = sp[0], x = sp[1], y = sp[2], elite = sp[3];
            // 需求 8：首领 key 是场景专属的（warlord / swarmqueen / ...）
            if (BOSS_SKIN_KEYS[kind] || kind === 'boss') {
                var b = new Boss(x, y, this.floor, false);
                var ls = this.level_state || {};
                if (b.setup_scene) { b.setup_scene(ls.scene, ls.stage_idx || 0); }
                this.enemies.push(b);
                this.boss = b;
            } else {
                var em = makeEnemy(kind, x, y, this.floor, elite);
                var mobSc = (this.level_state || {}).scene;
                var mobMul = SCENE_MOB_HP_MUL[mobSc] || 1.0;
                if (Math.abs(mobMul - 1.0) > 0.001) {
                    em.max_hp = Math.round(em.max_hp * mobMul);
                    em.hp = em.max_hp;
                }
                em.applyDmgMul(SCENE_DMG_MUL[mobSc] || 1.0);
                this.enemies.push(em);
            }
        }
    };
    Game.prototype.spawnMinion = function (x, y, floor) {
        var mobSc = (this.level_state || {}).scene;
        var kinds = (floor >= 2 || (mobSc && mobSc !== 'crust')) ? ['slime', 'drone'] : ['slime'];
        var k = this.rng.choice(kinds);
        var em = makeEnemy(k, x, y, floor, false);
        var mobMul = SCENE_MOB_HP_MUL[mobSc] || 1.0;
        if (Math.abs(mobMul - 1.0) > 0.001) {
            em.max_hp = Math.round(em.max_hp * mobMul);
            em.hp = em.max_hp;
        }
        em.applyDmgMul(SCENE_DMG_MUL[mobSc] || 1.0);
        this.enemies.push(em);
        if (this.room && this.room.cleared && this.room.kind === 'boss') {
            this.room.cleared = false;
            this.room.enemies_spawned = true;
        }
    };
    Game.prototype.rollWeaponKey = function () {
        var pool = DROP_POOL[this.floor] || ['pistol'];
        return this.rng.choice(pool);
    };
    Game.prototype.awardRareWeapon = function (quality, x, y, directChance, forcedKey) {
        var pool = (D.QUALITY_POOL || {})[quality] || WPN_ORDER;
        var key = forcedKey || this.rng.choice(pool);
        quality = D.qualityForWeapon(key);
        if (this.profile) {
            var plans = this.profile.blueprints || (this.profile.blueprints = {});
            var order = D.QUALITY_ORDER || [];
            if (order.indexOf(quality) > order.indexOf(plans[key] || 'white')) {
                plans[key] = quality;
            }
            this._write_save();
        }
        var qs = (D.QUALITIES || {})[quality] || {};
        this.toast('获得' + (qs.name || quality) + '图纸', wget(key).name,
            qs.color || [255, 226, 150]);
        if (this.rng.random() < directChance) {
            this.pickups.push(new Pickup(x, y, 'weapon', 1, key,
                0, null, 'normal', quality));
        }
    };

    // ---- 回调
    // 需求 4：单枚金币面值随关卡深度递增（与 chapter.coin_value 同源）
    Game.prototype.coinValue = function () {
        var ls = this.level_state || {};
        var si = (typeof D.sceneIndexOf === 'function')
            ? D.sceneIndexOf(ls.scene) : 0;
        var v = D.coinValue(si, ls.stage_idx || 0);
        return Math.round(v * (this.char_fortune_mul || 1.0));
    };
    Game.prototype.onEnemyKilled = function (e) {
        this.kills++;
        this.run_kills = (this.run_kills || 0) + 1;
        this.combo_count = (this.combo_count || 0) + 1;
        this.combo_t = 2.8;
        if (this.player && this.player.alive) {
            var eGain = e.elite ? 2.5 : 1;
            if (this.player.wq(this) === 'red') {
                var rq = (D.QUALITIES || {}).red || {};
                if (this.player.wlevel(this) >= (rq.max_lv || 8)) { eGain *= 1.30; }
            }
            this.player.energy = Math.min(this.player.max_energy,
                this.player.energy + eGain);
            if (this.run_stats && (this.run_stats.flags || []).indexOf('lifesteal') >= 0 &&
                    this.rng.random() < 0.12) {
                this.player.hp = Math.min(this.player.max_hp, this.player.hp + 1.0);
                this.fx.text(this.player.x, this.player.y - 24, '+1', [130, 235, 140], 12, 0.7);
            }
        }
        vibrate(this, e.is_boss ? 42 : (e.elite ? 24 : 16));
        if (this.drink_buffs && this.drink_buffs.tea && !this._basket_chain) {
            Sfx.play('man_what_can_i_say');
            for (var ball = 0; ball < this.drink_buffs.tea; ball++) {
                this.bullets.push(new Basketball(e.x, e.y));
            }
        }
        try { this.discover('enemy', e.skey); } catch (e2) { /* 忽略 */ }
        if (e.kind === 'lucky_treasure') {
            var luckyRng=this.rng, luckyCoin=this.coinValue();
            for(var ci=0;ci<5;ci++){
                var ca=ci*TAU/5;
                this.pickups.push(new Pickup(e.x+Math.cos(ca)*18,e.y+Math.sin(ca)*18,
                    'coin',luckyCoin*3));
            }
            for(var di=0, dn=luckyRng.randint(2,3);di<dn;di++){
                this.pickups.push(new Pickup(e.x+di*13-12,e.y+22,'diamond',1));
            }
            var mats=[luckyRng.choice(['alloy','core']),luckyRng.choice(['prism','relic'])];
            for(var mi=0;mi<mats.length;mi++){
                this.pickups.push(new Pickup(e.x+luckyRng.uniform(-28,28),
                    e.y+luckyRng.uniform(-28,28),'material',luckyRng.randint(1,2),
                    null,0,mats[mi]));
            }
            if(luckyRng.random()<.40){this.awardRareWeapon(luckyRng.random()<.16?'red':'gold',e.x,e.y-27,1);}
            if(luckyRng.random()<.10){this.pickups.push(new Pickup(e.x,e.y-20,
                'collect',1,null,0,luckyRng.choice(D.COLLECT_ORDER)));}
            this.toast('幸运宝藏怪','发现珍品物资',[255,232,142]);
            return;
        }
        if (e.is_rare) {
            this.awardRareWeapon('red',
                e.x, e.y, 0.15);
        }
        if (e.is_boss) { return; }
        var luckB = (this.run_stats && this.run_stats.luck) || 0.0;
        if (e.elite && this.rng.random() < Math.min(0.10, 0.005 * (1.0 + luckB))) {
            this.awardRareWeapon('gold', e.x, e.y, 1.0);
        }
        var rng = this.rng, i;
        var cv = this.coinValue();
        var n = (rng.random() < 0.25 ? 2 : 1) + (e.elite ? 1 : 0);
        var face = Math.round(cv * (e.elite ? D.COIN_ELITE_MUL : 1.0));
        // 不合并成更少的大币：掉落实体数会影响玩家走位与命中
        // （与 Python 侧同理，见 game.py on_enemy_killed 注释）
        for (i = 0; i < n; i++) {
            var a = rng.uniform(0, TAU), d = rng.uniform(6, 26);
            this.pickups.push(new Pickup(e.x + Math.cos(a) * d,
                e.y + Math.sin(a) * d, 'coin', face));
        }
        if (e.elite) {
            this.pickups.push(new Pickup(e.x + 8, e.y - 6, 'material', 1,
                null, 0, rng.choice(['scrap', 'fiber', 'circuit'])));
        } else if (rng.random() < 0.12) {
            this.pickups.push(new Pickup(e.x + 6, e.y, 'material', 1,
                null, 0, rng.choice(['scrap', 'fiber'])));
        }
        if (rng.random() < 0.22 + (e.elite ? 0.12 : 0.0)) {
            this.pickups.push(new Pickup(e.x, e.y, 'energy', 18));
        }
        if (rng.random() < 0.09 + (e.elite ? 0.08 : 0.0)) {
            this.pickups.push(new Pickup(e.x, e.y, 'heart', 2));
        }
        if (rng.random() < 0.018) {
            this.pickups.push(new Pickup(e.x, e.y, 'key', 15));
        }
        if (e.elite && rng.random() < Math.min(0.85, 0.34 * (1.0 + 0.5 * luckB))) {
            var esc = (this.level_state || {}).scene;
            var ew = rollEliteWeapon(rng, esc);
            this.pickups.push(new Pickup(e.x, e.y, 'weapon', 1,
                ew[0], 0, null, 'normal', ew[1]));
        }
    };
    // 若刚清空的房间是本层"目标房"，开一道通往下一层的传送门。
    // 普通层没有首领，此前没有任何出口（与 Python 侧 _maybe_open_portal 对齐）。
    Game.prototype._maybeOpenPortal = function () {
        var r = this.room, d = this.dungeon;
        if (!r || !d || r.portal) { return; }
        if (d.is_boss_floor && !r.boss_defeated) { return; }
        var gk = d.goal_key;
        if (!gk || gk[0] !== r.gx || gk[1] !== r.gy) { return; }
        r.portal = [ROOM_CX, ROOM_CY];
        r.portal_t = 0.0;
        this.banner_text = '目标房已清空！进入传送门前往下一关';
        this.banner_t = 2.6;
        Sfx.play('level_up');
    };
    Game.prototype.onBossDefeated = function () {
        var r = this.room;
        this.boss = null;
        if (!r) { return; }
        r.boss_defeated = true;
        r.cleared = false;
        r.enemies_spawned = true;
        var stage = Math.trunc((this.level_state || {}).stage_idx || 0);
        var scene = (this.level_state || {}).scene;
        var exclusive = (D.SCENE_BOSS_WEAPONS || {})[scene] || {};
        if (D.stageKind(stage) === 'boss') {
            if (exclusive.red && this.rng.random() < 0.30) {
                this.awardRareWeapon('red', ROOM_CX - 42, ROOM_CY - 66, 1.0, exclusive.red);
            }
            this.awardRareWeapon('red', ROOM_CX, ROOM_CY - 62, 1.0);
            if (this.rng.random() < 0.012) {
                this.awardRareWeapon('radiant', ROOM_CX + 22, ROOM_CY - 62, 1.0);
            }
        } else {
            if (exclusive.gold && this.rng.random() < 0.42) {
                this.awardRareWeapon('gold', ROOM_CX - 42, ROOM_CY - 66, 1.0, exclusive.gold);
            }
            this.awardRareWeapon('gold', ROOM_CX, ROOM_CY - 62, 1.0);
            if (this.rng.random() < 0.02) {
                this.awardRareWeapon('red', ROOM_CX + 22, ROOM_CY - 62, 1.0);
            }
            if (this.rng.random() < 0.006) {
                this.awardRareWeapon('radiant', ROOM_CX + 42, ROOM_CY - 62, 1.0);
            }
        }
        var rng = this.rng, i, a;
        var bossFace = Math.round(this.coinValue() * D.COIN_BOSS_MUL);
        for (i = 0; i < 12; i++) {
            a = rng.uniform(0, TAU);
            var d = rng.uniform(20, 120);
            var x = clamp(ROOM_CX + Math.cos(a) * d, IN_L + 20, IN_R - 20);
            var y = clamp(ROOM_CY + Math.sin(a) * d, IN_T + 20, IN_B - 20);
            this.pickups.push(new Pickup(x, y, 'coin', bossFace));
        }
        // 大 Boss 必掉 5 枚钻石，小 Boss 必掉 2 枚
        var diaN = D.stageKind(stage) === 'boss' ? 5 : 2;
        for (i = 0; i < diaN; i++) {
            a = rng.uniform(0, TAU);
            this.pickups.push(new Pickup(ROOM_CX + Math.cos(a) * 64,
                ROOM_CY + Math.sin(a) * 64, 'diamond', 1));
        }
        for (i = 0; i < 3; i++) {
            a = rng.uniform(0, TAU);
            this.pickups.push(new Pickup(ROOM_CX + Math.cos(a) * 54,
                ROOM_CY + Math.sin(a) * 54, 'heart', 2));
        }
        for (i = 0; i < 2; i++) {
            a = rng.uniform(0, TAU);
            this.pickups.push(new Pickup(ROOM_CX + Math.cos(a) * 76,
                ROOM_CY + Math.sin(a) * 76, 'energy', 40));
        }
        this.banner_text = 'BOSS 已击败！清空随从后进入传送门';
        this.banner_t = 2.6;
        Sfx.play('level_up');
    };
    Game.prototype.onPlayerDied = function () {
        this._bankRunCoins();
        this._write_save();
        this.state = 'gameover';
        this.over_index = 0;
    };
    Game.prototype._next_floor = function () {
        // 需求：本关结束 -> 汇总成绩（副本准入条件靠它累积）
        if (this.floor < FLOORS) {
            this.state = 'levelclear';
            Sfx.play('level_up');
            return;
        }
        this._finishStage();
        var prof = this.profile;
        if (!prof) {
            this._write_save();
            this.state = 'victory';
            this.over_index = 0;
            Sfx.play('victory');
            return;
        }
        // level_state 是 prof.run 的副本，推进前回写，否则 advance 读到旧关卡号
        var ls = this.level_state || {};
        if (ls.scene !== undefined && ls.scene !== null) {
            try { D.nextStage(prof, ls.scene, Math.floor(ls.stage_idx || 0)); }
            catch (e) { /* 忽略，退化到 advance 的当前值 */ }
        }
        var res = D.advance(prof);
        var kind = res[0], payload = res[1];
        prof.scene_prog = prof.scene_prog || {};
        if (ls.scene) {
            prof.scene_prog[ls.scene] = Math.max(prof.scene_prog[ls.scene] || 0,
                Math.floor(ls.stage_idx || 0) + 1);
        }
        if (kind === 'scene_clear') { D.scanUnlocks(prof); }
        this._write_save();
        if (kind === 'next') {
            var sc = payload.scene, si = Math.floor(payload.stage_idx || 0);
            D.nextStage(prof, sc, si);
            this.level_state = Object.assign({}, prof.run);
            // 仅第三关小 Boss 和第五关大 Boss 的传送门提供天赋。
            if (D.stageKind(si - 1) === 'miniboss' && this.startTalentPick(3)) {
                this._pending_story = ['stage_enter', sc, si, ['enter', null]];
                return;
            }
            this._startStory('stage_enter', sc, si, ['enter', null]);
            return;
        }
        if (kind === 'game_clear') {
            this._bankRunCoins();
            if (this.startTalentPick(3)) {
                this._pending_story = ['scene_clear', ls.scene, 0,
                    ['game_clear', null]];
                return;
            }
            this._write_save();
            this.state = 'victory';
            this.over_index = 0;
            Sfx.play('victory');
            return;
        }
        if (this.startTalentPick(3)) {
            this._pending_story = ['scene_clear', payload.scene, 0,
                ['scene_clear', { finale: !!payload.finale }]];
            return;
        }
        this._startStory('scene_clear', payload.scene, 0,
                         ['scene_clear', { finale: !!payload.finale }]);
    };

    // ---- 天赋三选一（1.1 需求 2，与 Python recompute_talents 对齐）
    Game.prototype.recomputeTalents = function () {
        var st = {
            max_hp: 0, max_energy: 0.0, speed_mul: 0.0, spd_mul: 0.0,
            dmg_mul: 0.0, fire_mul: 0.0, rate_mul: 0.0, magnet_mul: 0.0,
            hp_regen: 0.0, crit: 0.0, dash_cd_mul: 0.0,
            luck: 0.0, pierce: 0, pur_resist: 0.0,
            flags: [], talents: []
        };
        var perm = (this.profile && this.profile.talent_levels) || {};
        for (var tk in perm) {
            if (!Object.prototype.hasOwnProperty.call(perm, tk)) { continue; }
            var tlv = Math.trunc(perm[tk] || 0);
            if (tlv <= 0) { continue; }
            var pspec = D.TALENTS[tk];
            if (!pspec) { continue; }
            if (pspec.kind === 'stat') {
                var pnm = pspec.stat;
                if (Object.prototype.hasOwnProperty.call(st, pnm)) {
                    st[pnm] = st[pnm] + (pspec.val || 0) * tlv;
                }
            } else if (pspec.flag) {
                if (st.flags.indexOf(pspec.flag) < 0) { st.flags.push(pspec.flag); }
            }
        }
        for (var i = 0; i < this.talents_owned.length; i++) {
            var k = this.talents_owned[i];
            var spec = D.TALENTS[k];
            if (!spec) { continue; }
            st.talents.push(k);
            if (spec.kind === 'stat') {
                var nm = spec.stat;
                if (Object.prototype.hasOwnProperty.call(st, nm)) {
                    st[nm] = st[nm] + (spec.val || 0);
                }
            } else if (spec.flag) {
                if (st.flags.indexOf(spec.flag) < 0) { st.flags.push(spec.flag); }
            }
        }
        st.speed_mul = st.spd_mul || 0.0;
        st.pur_resist = Math.max(0, Math.min(D.PUR_RESIST_CAP, st.pur_resist || 0));
        this.run_stats = st;
        return st;
    };
    Game.prototype.startTalentPick = function (n) {
        n = n || 3;
        var picks;
        try { picks = D.rollTalents(this.rng, this.talents_owned.slice(), n); }
        catch (e) { picks = D.TALENT_ORDER.slice(0, n); }
        if (!picks || !picks.length) { return false; }
        this.pending_talents = picks;
        this.talent_pick = 0;
        this.state = 'talent';
        return true;
    };
    Game.prototype._talentMove = function (d) {
        if (!this.pending_talents) { return; }
        var n = this.pending_talents.length;
        this.talent_pick = ((this.talent_pick + d) % n + n) % n;
        Sfx.play('ui');
    };
    Game.prototype._talentConfirm = function () {
        if (!this.pending_talents) { this.state = 'playing'; return; }
        var i = this.talent_pick % this.pending_talents.length;
        var k = this.pending_talents[i];
        this.talents_owned.push(k);
        this.recomputeTalents();
        var spec = D.TALENTS[k] || {};
        this.pending_talents = null;
        Sfx.play('ui_big');
        this.toast('习得天赋：' + (spec.name || k), spec.desc || '',
            spec.color || [255, 236, 170], 3.4);
        try {
            var ls = this.level_state || {};
            this._applyPollution(ls.scene, Math.floor(ls.stage_idx || 0));
        } catch (e) { /* 忽略 */ }
        if (k === 'hp_up') { this.player.hp = this.player.max_hp; }
        else if (k === 'shield') {
            this.player.shield_charges = Math.max(1, this.player.shield_charges || 0);
        }
        this.state = 'playing';
        var pend = this._pending_story;
        if (pend) {
            this._pending_story = null;
            try { this._startStory(pend[0], pend[1], pend[2], pend[3]); }
            catch (e2) { /* 忽略 */ }
        }
    };
    Game.prototype._keydownTalent = function (key) {
        if (key === 'arrowleft' || key === 'a') { this._talentMove(-1); }
        else if (key === 'arrowright' || key === 'd') { this._talentMove(1); }
        else if (key === 'enter' || key === ' ') { this._talentConfirm(); }
    };

    // ---- 过场（与 Python _start_story/_advance_pending 对齐）
    Game.prototype._startStory = function (phase, sceneKey, stageIdx, after) {
        var t = this._storyText(phase, sceneKey, stageIdx);
        var lines = t[0], title = t[1], tint = t[2];
        if (!lines || !lines.length) {
            this.pending_after = after;
            this._advancePending();
            return;
        }
        this.story_scene = sceneKey;
        this.story_phase = phase;
        this.story_lines = lines;
        this.story_title = title;
        this.story_tint = tint;
        this.story_t = 0.0;
        this.story_page = 0;
        this.pending_after = after;
        this.state = 'story';
        Sfx.play('ui_big');
    };
    Game.prototype._storyText = function (phase, sceneKey, stageIdx) {
        var info = D.sceneInfo(sceneKey);
        var tint = info.tint || [140, 140, 140];
        var name = info.name || sceneKey;
        if (phase === 'scene_clear') {
            return [(info.clear || []).slice(),
                    '「' + name + '」 已清理', tint];
        }
        var si = Math.floor(stageIdx || 0);
        if (si === 0) {
            return [(info.enter || []).slice(), '「' + name + '」 进入', tint];
        }
        var kind = D.stageKind(si);
        var sub = D.sceneStageName(si);
        var lines = [name + ' · ' + sub];
        if (kind === 'miniboss') {
            lines.push('前方有精英与小型 Boss，整理好弹药。');
        } else if (kind === 'boss') {
            lines.push('本场景的最终关。污染读数最高，注意脚下。');
        } else {
            lines.push('继续向下，别在同一个陷阱上栽两次。');
        }
        var pl = D.pollutionLines(sceneKey, si);
        if (pl && pl.length) { lines.push('污染浓度 ' + D.pollution(sceneKey, si).pct + '%  ·  ' + pl.join(' · ')); }
        return [lines, name + ' · 第 ' + (si + 1) + ' 关', tint];
    };
    Game.prototype._advancePending = function () {
        var act = this.pending_after;
        this.pending_after = null;
        if (!act) { this.state = 'playing'; return; }
        var kind = act[0], data = act[1];
        if (kind === 'enter') {
            this._startRunScene(this.level_state);
        } else if (kind === 'game_clear') {
            this._bankRunCoins();
            this._write_save();
            this.state = 'victory';
            this.over_index = 0;
            Sfx.play('victory');
        } else if (kind === 'scene_clear') {
            var prof = this.profile, scene = this.story_scene;
            if (data && data.finale) {
                this._bankRunCoins();
                this._write_save();
                this.state = 'lobby';
                this.lobby_expand = false;
                this.toast('主线已通关', '客厅里可以购买奖励副本「馈赠之地」了',
                           [255, 226, 150], 4.0);
                return;
            }
            var target = this._nextTarget(prof);
            var nxt = target.scene;
            if (!nxt) { this._bankRunCoins(); this._write_save(); this.state = 'lobby'; return; }
            D.nextStage(prof, nxt, target.stage_idx || 0);
            this._startRunScene(prof.run);
        } else {
            this.state = 'playing';
        }
    };
    Game.prototype._startRunScene = function (levelState) {
        this.level_state = levelState;
        this._stage_done = false;
        this.transition_lock = 0.35;
        this._start_floor(1);
        if (this.route_state !== 'pending') { this.state = 'playing'; }
    };
    Game.prototype._storyNext = function () {
        if (this.transition_lock > 0) { this.transition_lock = 0.0; }
        if (this.story_page + 1 < this.story_lines.length) {
            this.story_page += 1;
            this.story_t = 0.0;
            Sfx.play('ui');
        } else {
            this._advancePending();
            Sfx.play('ui_big');
        }
    };
    Game.prototype._storySkip = function () { this._advancePending(); };

    // ---- 输入
    Game.prototype.read_input = function () {
        if (this.inp) { return this.inp; }
        var k = Input.keys;
        var mx = 0, my = 0;
        if (k.a || k.arrowleft) { mx--; }
        if (k.d || k.arrowright) { mx++; }
        if (k.w || k.arrowup) { my--; }
        if (k.s || k.arrowdown) { my++; }
        var shoot = Input.mouse.left || !!k[' '];
        var dash = Input.mouse.right || !!k.shift;
        var slow = !!k.control;
        var wmx = this.mouse_canvas[0], wmy = this.mouse_canvas[1];
        // 手机端：双摇杆移动与攻击，辅助瞄准仅在手机输入时生效。
        var T = window.__TOUCH__;
        if (T && T.enabled) {
            if (Math.abs(T.mx) > 0.06 || Math.abs(T.my) > 0.06) {
                mx = T.mx; my = T.my;
            }
            if (T.shoot) { shoot = true; }
            if (T.dash) { dash = true; T.dash = false; }
            if (T.act) { T.act = false; this.request_interact(); }
            if (T.swap) { T.swap = false; this.player.switchWeapon(); }
            if (T.skill) { T.skill = false; this.activateCharSkill(); }
            if (T.aim) { wmx = T.aim[0]; wmy = T.aim[1]; }
        }
        var world = [wmx - this.cam[0], wmy - this.cam[1]];
        var aim = Math.atan2(world[1] - this.player.y, world[0] - this.player.x);
        this._mobile_lock = null;
        if (T && T.enabled) {
            var targets = [];
            var maxRange2 = 460 * 460;
            for (var ti = 0; ti < this.enemies.length; ti++) {
                var te = this.enemies[ti];
                if (te && te.alive && !te.invuln) { targets.push(te); }
            }
            if (this.boss && this.boss.alive && !this.boss.invuln) {
                targets.push(this.boss);
            }
            if (T.aimVector) {
                var targetAngle = Math.atan2(T.aimVector[1], T.aimVector[0]);
                if (typeof T.aimAngle !== 'number') { T.aimAngle = targetAngle; }
                var delta = Math.atan2(Math.sin(targetAngle - T.aimAngle),
                                       Math.cos(targetAngle - T.aimAngle));
                var sensitivity = Math.max(0.4, Math.min(2.0, Number(this.setting.aim_sens) || 1));
                T.aimAngle += delta * Math.min(1, 0.65 * sensitivity);
                aim = T.aimAngle;
                if (this.setting.aim_assist) {
                    var bestTarget = null, bestScore = 1e9, bestDelta = 0;
                    for (var bi = 0; bi < targets.length; bi++) {
                        var be = targets[bi];
                        var bdx = be.x - this.player.x, bdy = be.y - this.player.y;
                        var bd2 = bdx * bdx + bdy * bdy;
                        if (bd2 > maxRange2) { continue; }
                        var bang = Math.atan2(bdy, bdx);
                        var ad = Math.atan2(Math.sin(bang - aim), Math.cos(bang - aim));
                        if (Math.abs(ad) <= 0.49) { // ±28° 扇形磁吸范围
                            var score = Math.abs(ad) + (Math.sqrt(bd2) / 460) * 0.18;
                            if (score < bestScore) {
                                bestScore = score;
                                bestTarget = be;
                                bestDelta = ad;
                            }
                        }
                    }
                    if (bestTarget) {
                        this._mobile_lock = bestTarget;
                        aim += bestDelta * 0.85;
                    }
                }
            } else if (!T.aim) {
                var nearest = null, nearestD2 = maxRange2;
                if (this.setting.aim_assist) {
                    for (var ai = 0; ai < targets.length; ai++) {
                        var ae = targets[ai];
                        var adx = ae.x - this.player.x, ady = ae.y - this.player.y;
                        var ad2 = adx * adx + ady * ady;
                        if (ad2 < nearestD2) { nearest = ae; nearestD2 = ad2; }
                    }
                }
                if (nearest) {
                    this._mobile_lock = nearest;
                    aim = Math.atan2(nearest.y - this.player.y, nearest.x - this.player.x);
                    T.aimAngle = aim;
                } else {
                    if (typeof T.aimAngle === 'number') {
                        aim = T.aimAngle;
                    }
                    if (Math.abs(mx) > 0.1 || Math.abs(my) > 0.1) {
                        var moveAngle = Math.atan2(my, mx);
                        aim = angLerp(aim, moveAngle, 0.25);
                        T.aimAngle = aim;
                    }
                }
            }
        }
        if (mx > 1) { mx = 1; } else if (mx < -1) { mx = -1; }
        if (my > 1) { my = 1; } else if (my < -1) { my = -1; }
        return { mx: mx, my: my, aim: aim, shoot: shoot, dash: dash, slow: slow };
    };
    Game.prototype.unlockAudio = function () { Sfx.unlock(); };
    Game.prototype._findInteractTarget = function () {
        if (this.state !== 'playing' || !this.room || !this.player) { return null; }
        var pl = this.player, best = null, bd = 1e9, i;
        for (i = 0; i < this.pickups.length; i++) {
            var p = this.pickups[i];
            if (p.canInteract(pl)) {
                var d = dist(p.x, p.y, pl.x, pl.y);
                if (d < bd) { best = p; bd = d; }
            }
        }
        if (this.room.portal) {
            var portalD = dist(pl.x, pl.y, this.room.portal[0], this.room.portal[1]);
            if (portalD < 24 && (!best || portalD < 4 || portalD + 6 < bd)) {
                return this.room.portal;
            }
        }
        return best;
    };
    Game.prototype.getTouchHudState = function () {
        var pl = this.player;
        var charKey = (this.profile && this.profile.char) || this.char_key || 'scout';
        var skill = CHAR_SKILLS[charKey] || CHAR_SKILLS.scout;
        var dashMax = P_DASH_CD * (charKey === 'ghost' ? 0.75 : 1.0);
        var target = this._findInteractTarget();
        var interactLabel = null, interactConfirm = false;
        if (target) {
            var now = Date.now(), pending = this._pending_interact;
            if (pending && pending.target === target && pending.room === this.room &&
                pending.expires >= now) {
                interactConfirm = true;
                interactLabel = '确认';
            } else if (this.room && target === this.room.portal) {
                interactLabel = '进门';
            } else if (target.kind === 'chest') {
                interactLabel = '开箱';
            } else if (target.kind === 'weapon') {
                interactLabel = '捡枪';
            } else if (target.kind && target.kind.indexOf('shop_') === 0) {
                interactLabel = '购买';
            } else if (target.kind === 'drink') {
                interactLabel = '饮用';
            } else {
                interactLabel = '交互';
            }
        }
        return {
            dashCd: pl ? Math.max(0, pl.dash_cd || 0) : 0,
            dashMax: dashMax,
            skillCd: Math.max(0, this.char_skill_cd || 0),
            skillMax: skill ? skill.cd : 1,
            hasSecondWeapon: !!(pl && pl.wkey2),
            interactLabel: interactLabel,
            interactConfirm: interactConfirm,
            routeOpen: this.state === 'route_choice'
        };
    };
    Game.prototype.request_interact = function () {
        if (this.state !== 'playing' || !this.room) { return false; }
        var best = this._findInteractTarget();
        if (best && best === this.room.portal) {
            if (!this._confirmInteract(this.room.portal)) { return true; }
            this._next_floor();
            return true;
        }
        if (best) {
            if (best.kind === 'chest' || best.kind === 'shop_weapon' ||
                best.kind === 'shop_heart' || best.kind === 'shop_hp_potion' ||
                best.kind === 'shop_energy_potion' || best.kind === 'drink' ||
                best.kind === 'weapon') {
                if (!this._confirmInteract(best)) { return true; }
            }
            var acted = best.interact(this);
            this._write_save();
            return acted;
        }
        this._pending_interact = null;
        return false;
    };
    Game.prototype._confirmInteract = function (target) {
        var now = Date.now(), pending = this._pending_interact;
        if (pending && pending.target === target && pending.room === this.room &&
            pending.expires >= now) {
            this._pending_interact = null;
            return true;
        }
        this._pending_interact = { target: target, room: this.room,
                                   expires: now + 5000 };
        var label = target === this.room.portal ?
            (this.route_state === 'survey' && !this.route_sealed ?
             '离开本关将放弃勘测' : '进入传送门') :
            (target.promptText ? target.promptText() : '确认操作');
        this.toast('请确认：' + label,
            mobileUI() ? '五秒内再点一次「交互」执行' : '五秒内再按一次 E/F 执行',
            [255, 226, 150], 3.0);
        return false;
    };
    Game.prototype._menu_pick = function (action) {
        Sfx.play('ui_big');
        if (action === 'new') {
            // 需求 10：先选存档槽（3 槽 + 覆盖确认），再进客厅
            this.state = 'slots';
            this.slot_index = 0;
            // 光标默认停在"已有档"上，方便继续玩
            var slots = this.slot_list();
            for (var i = 0; i < slots.length; i++) {
                if (slots[i] !== null) { this.slot_index = i; break; }
            }
        }
        else if (action === 'help') { this.state = 'help'; }
        else if (action === 'audio') {
            Sfx.toggle();
            this.menu_items[2][0] = '音效：' + (Sfx.enabled ? '开' : '关');
        } else if (action === 'quit') { this._write_save(); this.state = 'quit'; }
        else if (action === 'resume') { this.state = 'playing'; }
        else if (action === 'unstuck') { this.doUnstuck(); }
        else if (action === 'restart') { this._bankRunCoins(); this.start_run(); }
        else if (action === 'settle') { this.settle_run(); }
        else if (action === 'title') { this._write_save(); this.state = 'title'; this.menu_index = 0; }
        else if (action === 'lobby') { this._write_save(); this._enterLobby(); }
    };
    // 需求 7：脱离卡死 —— 复位玩家 -> 存盘 -> 回主菜单（进度已保存，可断点续玩）
    Game.prototype.doUnstuck = function () {
        try {
            if (this.room) {
                this.player.x = ROOM_CX; this.player.y = ROOM_CY;
                this.player.knock_t = 0.0;
                this.player.iframes = Math.max(this.player.iframes, 1.2);
            }
            this._stuck_rescues = (this._stuck_rescues || 0) + 1;
        } catch (e) { /* 忽略 */ }
        this._write_save();
        this.state = 'title';
        this.menu_index = 0;
        try { this.toast('已脱离卡死', '进度已自动保存，下次可从断点继续', [140, 230, 190], 3.5); }
        catch (e) { /* 忽略 */ }
    };
    // 需求 18：标题右下角更新日志按钮命中检测
    Game.prototype._title_changelog_hit = function (pos) {
        var lbl = '更新日志 v4.0';
        var bw = textWidth(lbl, 11) + 18;
        var bx = VIEW_W - 12 - bw, by = VIEW_H - 30;
        var px = pos ? pos[0] : 0, py = pos ? pos[1] : 0;
        return px >= bx && px <= bx + bw && py >= by && py <= by + 20;
    };
    Game.prototype.menu_hit = function (cy) {
        var st = this.state, items, base, step, name;
        if (st === 'title') {
            items = this.menu_items; base = 168; step = 34; name = 'menu_index';
        } else if (st === 'paused') {
            items = this.pause_items; base = 122; step = 30; name = 'pause_index';
        } else if (st === 'gameover' || st === 'victory') {
            items = this.over_items;
            base = overMenuBase(st);
            step = OVER_MENU_STEP[st];
            name = 'over_index';
        } else { return -1; }
        for (var i = 0; i < items.length; i++) {
            var y = base + i * step;
            if (cy >= y - 6 && cy <= y + 26) {
                this[name] = i;
                return i;
            }
        }
        return -1;
    };
    Game.prototype.activateCharSkill = function () {
        var key = this.char_key || 'scout', skill = CHAR_SKILLS[key] || CHAR_SKILLS.scout;
        if (this.state !== 'playing' || this.char_skill_cd > 0) { return false; }
        var pl = this.player, enemies = this.enemies.filter(function (e) { return e.alive; });
        this.char_skill_cd = skill.cd;
        this.fx.ring(pl.x, pl.y, 5, skill.radius, .4, skill.color, 3);
        this.fx.burst(pl.x, pl.y, skill.color, 20, 155, .48, 4);
        this.fx.text(pl.x, pl.y - 35, skill.name, skill.color, 12, 1.0);
        this.fx.add_shake(2.6);
        vibrate(this, 22);
        Sfx.play('ui_big');
        if (key === 'scout') { this.fx.ring(pl.x, pl.y, 12, skill.radius * .7, .28, skill.color, 1); }
        else if (key === 'engineer') { this.fx.burst(pl.x, pl.y, skill.color, 26, 210, .27, 2); }
        else if (key === 'ranger') { this.fx.arcSwing(pl.x, pl.y, pl.aim, skill.radius * .72, 48, skill.color); }
        else if (key === 'medic') { this.fx.burst(pl.x, pl.y, skill.color, 18, 75, .8, 5, TAU, 0, 2.6, 0, 'circle'); }
        else if (key === 'ghost') { this.fx.burst(pl.x, pl.y, skill.color, 20, 42, .6, 4, TAU, 0, 2.6, -22, 'circle'); }
        else if (key === 'prime') { this.fx.ring(pl.x, pl.y, 20, skill.radius * 1.2, .5, skill.color, 5); }
        else if (key === 'archivist') { this.fx.burst(pl.x, pl.y, skill.color, 12, 50, .65, 2); }
        else if (key === 'seedkeeper') { this.fx.burst(pl.x, pl.y, skill.color, 26, 100, .75, 3, TAU, 0, 2.6, 0, 'circle'); }
        if (key === 'scout') { pl.energy = Math.min(pl.max_energy, pl.energy + 48); }
        else if (key === 'medic') { pl.heal(6); pl.iframes = Math.max(pl.iframes, 1.4); }
        else if (key === 'ghost') { pl.iframes = Math.max(pl.iframes, 2.5); pl.dash_cd = 0; }
        else if (key === 'seedkeeper') { pl.heal(4); }
        else if (key === 'engineer') { pl.energy = Math.min(pl.max_energy, pl.energy + 35); }
        else if (key === 'prime') { pl.energy = Math.min(pl.max_energy, pl.energy + 20); }
        else if (key === 'archivist') { pl.energy = Math.min(pl.max_energy, pl.energy + 30); }
        var skillMul = 1.0 + (pl.dmgBonus ? pl.dmgBonus(this) : 0.0);
        if (key === 'engineer' || key === 'prime' || key === 'seedkeeper') {
            var baseDmg = key === 'engineer' ? 17 : key === 'prime' ? 32 : 11;
            var dmg = Math.round(baseDmg * skillMul * 100) / 100;
            enemies.forEach(function (e) {
                if (Math.hypot(e.x - pl.x, e.y - pl.y) <= skill.radius) {
                    e.take_damage(dmg, this, pl.x, pl.y);
                    this.fx.burst(e.x, e.y, skill.color, 8, 100, .3, 3);
                }
            }, this);
        } else if (key === 'ranger') {
            var rDmg = Math.round(27 * skillMul * 100) / 100;
            enemies.forEach(function (e) {
                var dx = e.x - pl.x, dy = e.y - pl.y;
                var da = (Math.atan2(dy, dx) - pl.aim + Math.PI + 2 * Math.PI) % (2 * Math.PI) - Math.PI;
                if (Math.hypot(dx, dy) <= skill.radius && Math.abs(da) < .42) {
                    e.take_damage(rDmg, this, pl.x, pl.y);
                    this.fx.burst(e.x, e.y, skill.color, 8, 100, .3, 3);
                }
            }, this);
        } else if (key === 'archivist' && enemies.length) {
            enemies.sort(function (a, b) {
                return Math.hypot(a.x - pl.x, a.y - pl.y) - Math.hypot(b.x - pl.x, b.y - pl.y);
            });
            var target = enemies[0];
            if (Math.hypot(target.x - pl.x, target.y - pl.y) <= skill.radius) {
                target.take_damage(Math.round(24 * skillMul * 100) / 100, this, pl.x, pl.y);
                this.fx.ring(target.x, target.y, 4, 30, .35, skill.color, 2);
            }
        }
        return true;
    };
    Game.prototype._keydown = function (key) {
        var st = this.state, n;
        if (this.collection_popup) { this.collection_popup = null; return; }
        if (st === 'route_choice') {
            if (key === 'arrowup' || key === 'arrowdown' || key === 'w' || key === 's') {
                this.route_index = 1 - this.route_index; Sfx.play('ui');
            } else if (key === 'enter' || key === ' ') { this._chooseRoute(this.route_index); }
            else if (key === 'escape' || key === 'p') { this._chooseRoute(0); }
            return;
        }
        if (key === 'f11') { toggleFullscreen(); return; }
        if (key === 'm') {
            Sfx.toggle();
            this.menu_items[2][0] = '音效：' + (Sfx.enabled ? '开' : '关');
            return;
        }
        if (st === 'title') {
            if (key === 'arrowup' || key === 'w') {
                n = this.menu_items.length;
                this.menu_index = (this.menu_index + n - 1) % n;
                Sfx.play('ui');
            } else if (key === 'arrowdown' || key === 's') {
                this.menu_index = (this.menu_index + 1) % this.menu_items.length;
                Sfx.play('ui');
            } else if (key === 'enter' || key === ' ') {
                this._menu_pick(this.menu_items[this.menu_index][1]);
            }
        } else if (st === 'help') {
            if (key === 'escape' || key === 'p') {
                this.state = 'title';
                Sfx.play('ui');
            } else {
                this._keydownSettings(key);
            }
        } else if (st === 'changelog') {
            if (key === 'escape' || key === 'enter' || key === ' ' || key === 'p') {
                this.state = 'title';
                Sfx.play('ui');
            } else if (key === 'arrowdown' || key === 's') {
                this.log_scroll = (this.log_scroll || 0) + 1;
            } else if (key === 'arrowup' || key === 'w') {
                this.log_scroll = Math.max(0, (this.log_scroll || 0) - 1);
            }
        } else if (st === 'playing') {
            if (key === 'escape' || key === 'p') {
                this.state = 'paused';
                this.pause_index = 0;
                Sfx.play('ui');
            } else if (key === 'e' || key === 'f') { this.request_interact(); }
            else if (key === 'q') { if (this.player.switchWeapon()) { Sfx.play('pickup'); } }
            else if (key === 'x') { this.activateCharSkill(); }
            else if (key === 'v') { this.show_aim = !this.show_aim; }
        } else if (st === 'paused') {
            if (key === 'arrowup' || key === 'w') {
                n = this.pause_items.length;
                this.pause_index = (this.pause_index + n - 1) % n;
                Sfx.play('ui');
            } else if (key === 'arrowdown' || key === 's') {
                this.pause_index = (this.pause_index + 1) % this.pause_items.length;
                Sfx.play('ui');
            } else if (key === 'enter' || key === ' ') {
                this._menu_pick(this.pause_items[this.pause_index][1]);
            } else if (key === 'escape' || key === 'p') {
                this.state = 'playing';
                Sfx.play('ui');
            }
        } else if (st === 'levelclear') {
            if (key === 's') { this.settle_run(); }
            else if (key === 'enter' || key === ' ' || key === 'escape') {
                this._start_floor(this.floor + 1);
            }
        } else if (st === 'gameover' || st === 'victory') {
            if (key === 'arrowup' || key === 'w') {
                n = this.over_items.length;
                this.over_index = (this.over_index + n - 1) % n;
                Sfx.play('ui');
            } else if (key === 'arrowdown' || key === 's') {
                this.over_index = (this.over_index + 1) % this.over_items.length;
                Sfx.play('ui');
            } else if (key === 'enter' || key === ' ') {
                this._menu_pick(this.over_items[this.over_index][1]);
            }
        } else if (st === 'quit') {
            if (key === 'enter' || key === 'escape' || key === ' ') {
                this.state = 'title';
                this.menu_index = 0;
                Sfx.play('ui');
            }
        } else if (st === 'lobby') {
            this._keydownLobby(key);
        } else if (st === 'slots' || st === 'slot_create' || st === 'slot_confirm') {
            this._keydownSlots(key);
        } else if (st === 'talent') {
            this._keydownTalent(key);
        } else if (st === 'story') {
            if (key === 'escape') { this._storySkip(); }
            else { this._storyNext(); }
        }
    };
    Game.prototype._click = function () {
        var st = this.state;
        if (st === 'route_choice') {
            var p = this.mouse_canvas;
            if (p[0] >= 120 && p[0] <= 520 && p[1] >= 110 && p[1] <= 260) {
                this._chooseRoute(p[1] >= 181 ? 1 : 0);
            }
            return;
        }
        if (st === 'title') {
            // 需求 18：右下角更新日志按钮优先命中
            if (this._title_changelog_hit(this.mouse_canvas)) {
                this.state = 'changelog';
                this.log_scroll = 0;
                Sfx.play('ui');
                return;
            }
            if (this.menu_hit(this.mouse_canvas[1]) >= 0) {
                this._menu_pick(this.menu_items[this.menu_index][1]);
            }
        } else if (st === 'paused') {
            if (this.menu_hit(this.mouse_canvas[1]) >= 0) {
                this._menu_pick(this.pause_items[this.pause_index][1]);
            }
        } else if (st === 'gameover' || st === 'victory') {
            if (this.menu_hit(this.mouse_canvas[1]) >= 0) {
                this._menu_pick(this.over_items[this.over_index][1]);
            }
        } else if (st === 'levelclear') {
            if (this.mouse_canvas[1] >= 234) { this.settle_run(); }
            else { this._start_floor(this.floor + 1); }
        } else if (st === 'help') {
            var pos = this.mouse_canvas;
            if (pos[1] >= 313 && pos[1] <= 337) {
                if (pos[0] >= 372 && pos[0] <= 480) {
                    this.export_backup(); return;
                }
                if (pos[0] >= 492 && pos[0] <= 600) {
                    this.choose_backup(); return;
                }
            }
            if (pos[0] >= 372 && pos[1] >= 70 && pos[1] < 70 + settingRows(this)[0].length * 21) {
                var row = Math.floor((pos[1] - 70) / 21);
                if (row >= 0 && row < settingRows(this)[0].length) {
                    this.setting_index = row;
                    this._keydownSettings('enter');
                    return;
                }
            }
            this.state = 'title';
        } else if (st === 'quit' || st === 'changelog') {
            this.state = 'title';
        } else if (st === 'talent') {
            var picks = this.pending_talents || [];
            var cw = 132, gap = 14, total = picks.length * cw + (picks.length - 1) * gap;
            var x0 = VIEW_W / 2 - total / 2;
            for (var i = 0; i < picks.length; i++) {
                var cx = x0 + i * (cw + gap);
                if (this.mouse_canvas[0] >= cx && this.mouse_canvas[0] <= cx + cw &&
                    this.mouse_canvas[1] >= 96 && this.mouse_canvas[1] <= 250) {
                    this.talent_pick = i;
                    this._talentConfirm();
                    return;
                }
            }
        } else if (st === 'slots' || st === 'slot_create' || st === 'slot_confirm') {
            this._slotMouse(this.mouse_canvas);
        } else if (st === 'lobby') {
            if ((this.lobby_tab || 0) === 0 && this.mouse_canvas[0] >= LOBBY_LX &&
                this.mouse_canvas[0] <= LOBBY_LX + 142 &&
                this.mouse_canvas[1] >= VIEW_H - 51 && this.mouse_canvas[1] <= VIEW_H - 30) {
                this._startNewCycle();
                return;
            }
            var hit = this._mouseLobby(this.mouse_canvas);
            // 只有"关卡"分页点到卡片才立刻出发；图鉴/展示台分页点击仅做选中
            var tabNow = ((this.lobby_tab || 0) % 4 + 4) % 4;
            if (hit && tabNow === 0) { this._lobbyGo(); }
        } else if (st === 'story') {
            this._storyNext();
        }
    };

    // ---- 更新
    Game.prototype.update = function (dt) {
        this.time += dt;
        if (this.time > 1e8) { this.time = 0.0; }
        // 需求 20：打击停顿期间，**世界**时间几乎不推进（敌人/子弹/陷阱定住），
        // 但玩家移动与瞄准永远按真实 dt 走（与 Python 端一致）。
        // 曾把 wdt 作用到玩家身上，导致高射速（每帧都命中）时
        //    世界速度被永久锁死在 6%，玩家几乎无法移动。
        var wdt = dt;
        if (this.hitstop > 0) {
            this.hitstop = Math.max(0.0, this.hitstop - dt);
            wdt = dt * HITSTOP_SCALE;
        }
        if ((this._hitstop_cd || 0.0) > 0) {
            this._hitstop_cd = Math.max(0.0, this._hitstop_cd - dt);
        }
        var st = this.state;
        if (this.room) { this.room.update_portal(dt); }
        if (st === 'playing') {
            this.total_time += dt;
            this._update_playing(dt, wdt);
        } else if (st === 'gameover' || st === 'victory' || st === 'levelclear') {
            this.fx.update(dt);
            this._update_camera();
        } else if (st === 'title' || st === 'help' || st === 'paused' ||
                   st === 'lobby' || st === 'talent' || st === 'changelog' ||
                   st === 'slots' || st === 'slot_create' || st === 'slot_confirm') {
            this.fx.update(dt);
            this._update_camera();
        } else if (st === 'story') {
            this.story_t += dt;
            if (this.transition_lock > 0) {
                this.transition_lock = Math.max(0, this.transition_lock - dt);
            }
            this.fx.update(dt);
            this._update_camera();
        }
    };
    // 需求 20：请求一次打击停顿；多次请求取最大值并夹到上限。
    // 冷却 HITSTOP_COOLDOWN：两次触发至少间隔这么久，防止"每帧都命中"时
    // 世界时间被永久压低（= 又顿又粘）。
    Game.prototype.add_hitstop = function (sec) {
        if ((this._hitstop_cd || 0.0) > 0) { return; }
        var v = Math.min(HITSTOP_MAX, Math.max(parseFloat(sec) || 0.0,
                                               this.hitstop || 0.0));
        this.hitstop = v;
        this._hitstop_cd = HITSTOP_COOLDOWN;
    };
    Game.prototype._update_camera = function () {
        var sx = this.fx.shake > 0 ? this.fx.shake_x : 0.0;
        var sy = this.fx.shake > 0 ? this.fx.shake_y : 0.0;
        this.cam = [CAM_OFF[0] + sx, CAM_OFF[1] + sy];
    };
    Game.prototype._update_playing = function (dt, wdt) {
        // dt = 真实时间（玩家移动/瞄准/计时）；wdt = 世界时间（受打击停顿缩放）。
        // 玩家操作永不受 hitstop 影响，否则高射速时会"粘住"无法移动。
        if (wdt === undefined || wdt === null) { wdt = dt; }
        if (!this.room || !this.player.alive) {
            this.fx.update(dt);
            this._update_camera();
            return;
        }
        var inp = this.read_input();
        var pl = this.player, i;
        this.char_skill_cd = Math.max(0, this.char_skill_cd - dt);
        if ((this.combo_t || 0) > 0) {
            this.combo_t = Math.max(0, this.combo_t - dt);
            if (this.combo_t <= 0) { this.combo_count = 0; }
        }
        // ---- 玩家：始终用真实 dt
        pl.update(this, dt, inp);
        if (this.drink_buffs && this.drink_buffs.dew) {
            pl.energy = Math.min(pl.max_energy,
                pl.energy + 1 * this.drink_buffs.dew * dt);
        }
        // 需求：污染渐近减益（持续侵蚀）
        this._updatePollution(dt);
        // 防卡死：每帧兜底 + 连续零位移检测
        this._last_mx = inp.mx || 0.0;
        this._last_my = inp.my || 0.0;
        this._ensurePlayerFree();
        this._checkStuck(dt);
        this.fire_cool = pl.cool;
        // ---- 世界：用 wdt
        for (i = 0; i < this.enemies.length; i++) {
            if (this.enemies[i].alive) { this.enemies[i].update(this, wdt); }
        }
        for (i = 0; i < this.bullets.length; i++) {
            if (this.bullets[i].alive) { this.bullets[i].update(this, wdt); }
        }
        // 用快照遍历：掉落物在 update 里可能往同一个数组里 push（例如换枪时掉旧枪），
        // 直接在活数组上遍历会被新元素"续命"，形成无限循环。
        var pk = this.pickups.slice();
        for (i = 0; i < pk.length; i++) {
            if (pk[i].alive) { pk[i].update(this, wdt); }
        }
        var pr = this.props.slice();
        for (i = 0; i < pr.length; i++) {
            pr[i].update(this, wdt);
        }
        this.room.update_hazards(this, wdt);   // 需求 3：陷阱 / 掩体 / 洞穴
        this.fx.update(dt);
        this._update_camera();

        // ---- 清理死亡实体
        this.bullets = this.bullets.filter(function (b) { return b.alive; });
        this.enemies = this.enemies.filter(function (e) { return e.alive; });
        this.room.props = this.room.props.filter(function (p) { return p.alive; });
        this.room.pickups = this.room.pickups.filter(function (p) { return p.alive; });
        this.room.traps = this.room.traps.filter(function (t) { return t.alive; });
        this.room.covers = this.room.covers.filter(function (c) { return c.alive; });
        if (this.boss && !this.boss.alive) { this.boss = null; }

        // ---- 计时器
        if (this.banner_t > 0) { this.banner_t = Math.max(0.0, this.banner_t - dt); }
        if (this.collection_popup) {
            this.collection_popup.t -= dt;
            if (this.collection_popup.t <= 0) { this.collection_popup = null; }
        }
        if (this.hint_t > 0) { this.hint_t = Math.max(0.0, this.hint_t - dt); }
        if (this.trans_fade > 0) { this.trans_fade = Math.max(0.0, this.trans_fade - dt); }
        for (i = 0; i < this.toasts.length; i++) { this.toasts[i].t += dt; }
        this.toasts = this.toasts.filter(function (t) { return t.t < t.life; });

        // ---- 房间清空判定
        var anyAlive = false;
        for (i = 0; i < this.enemies.length; i++) {
            if (this.enemies[i].alive) { anyAlive = true; break; }
        }
        if (this.room.enemies_spawned && !this.room.cleared && !anyAlive) {
            if (this.room.wave_plans.length && this.room.wave_index + 1 < this.room.wave_plans.length) {
                this.room.wave_index++;
                this._spawn_room(this.room);
                this.room.refresh_doors(true);
                this.banner_text = '第 ' + (this.room.wave_index + 1) + '/3 轮来袭';
                this.banner_t = 1.4;
                Sfx.play('lock');
            } else {
                this.room.cleared = true;
                this.room.refresh_doors(false);
                if (this.room.kind === 'normal' || this.room.kind === 'boss') {
                    var scBias = SCENE_CHEST_BIAS[(this.level_state || {}).scene] || 0.0;
                    var luckB = (this.run_stats && this.run_stats.luck) || 0.0;
                    var cpick = D.rollChest(this.rng, .10 * (this.floor - 1) + scBias + luckB);
                    this.pickups.push(new Pickup(ROOM_CX - 74, ROOM_CY + 45,
                        'chest', 1, null, 0, cpick[0], cpick[1]));
                }
                this.banner_text = '三轮已清空 · 奖励宝箱出现';
                this.banner_t = 1.7;
                Sfx.play('door');
                if (this.route_state === 'survey' && this.route_room &&
                    this.route_room[0] === this.room.gx && this.route_room[1] === this.room.gy) {
                    this.route_sealed = true;
                    this.toast('样本已封存 · 前往出口',
                        '阀门关闭后，监测读数短时下降。执行人栏已损毁。',
                        [182, 229, 198], 2.4);
                    Sfx.play('lock');
                }
                this._maybeOpenPortal();
            }
        }

        // ---- 交互提示（与 _findInteractTarget 同源，防止提示与实际交互不一致）
        var interTarget = this._findInteractTarget();
        if (interTarget && this.room.portal && interTarget === this.room.portal) {
            this.prompt = { promptText: function () {
                return mobileUI() ? '交互  确认进入传送门' : 'E/F  确认进入传送门';
            } };
        } else {
            this.prompt = interTarget;
        }

        // ---- 房间切换（穿过已开启的门）
        if (this.trans_fade <= 0.001) {
            for (i = 0; i < this.room.open_doors.length; i++) {
                var dr = this.room.open_doors[i];
                var ok = false;
                if (dr === 'N') {
                    ok = pl.y < TILE * 0.55 && Math.abs(pl.x - ROOM_CX) < 43;
                } else if (dr === 'S') {
                    ok = pl.y > ROOM_PX_H - TILE * 0.55 && Math.abs(pl.x - ROOM_CX) < 43;
                } else if (dr === 'W') {
                    ok = pl.x < TILE * 0.55 && Math.abs(pl.y - ROOM_CY) < 43;
                } else {
                    ok = pl.x > ROOM_PX_W - TILE * 0.55 && Math.abs(pl.y - ROOM_CY) < 43;
                }
                if (ok) {
                    var v = DIR_VEC[dr];
                    if (this.enter_room(this.room.gx + v[0], this.room.gy + v[1],
                        OPPOSITE[dr], false)) {
                        Sfx.play('door');
                    }
                    break;
                }
            }
        }
    };

    // ---- 渲染
    Game.prototype._draw_world = function () {
        var cam = this.cam;
        var i, ent;
        this.room.draw_bg(cam);
        if (this.room.portal) { this.room.draw_portal(cam, this.room.portal_t); }
        this.fx.draw_under(cam);
        this.room.draw_hazards_under(cam);   // 需求 3：洞穴 + 陷阱底盘

        // 按 y 排序，保证前后遮挡正确
        var entries = [];
        for (i = 0; i < this.room.props.length; i++) {
            if (this.room.props[i].alive) {
                entries.push([this.room.props[i].y, 0, this.room.props[i]]);
            }
        }
        for (i = 0; i < this.room.covers.length; i++) {
            if (this.room.covers[i].alive) {
                entries.push([this.room.covers[i].y, 0, this.room.covers[i]]);
            }
        }
        for (i = 0; i < this.room.pickups.length; i++) {
            if (this.room.pickups[i].alive) {
                entries.push([this.room.pickups[i].y, 1, this.room.pickups[i]]);
            }
        }
        for (i = 0; i < this.enemies.length; i++) {
            if (this.enemies[i].alive) {
                entries.push([this.enemies[i].y, 2, this.enemies[i]]);
            }
        }
        if (this.player.alive) { entries.push([this.player.y, 3, this.player]); }
        entries.sort(function (a, b) {
            if (a[0] !== b[0]) { return a[0] - b[0]; }
            return a[1] - b[1];
        });
        for (i = 0; i < entries.length; i++) {
            ent = entries[i];
            if (ent[1] === 3) { ent[2].draw(cam, this); }
            else { ent[2].draw(cam); }
        }
        this.room.draw_doors(cam);
        if (this.route_state === 'survey' && !this.route_sealed && this.route_room) {
            var next = this.dungeon.surveyNextDoor([this.room.gx, this.room.gy], this.route_room);
            if (next) {
                var sx = next === 'W' ? 15 : (next === 'E' ? ROOM_PX_W - 15 : ROOM_CX);
                var sy = next === 'N' ? 21 : (next === 'S' ? ROOM_PX_H - 21 : ROOM_CY);
                sx += cam[0]; sy += cam[1];
                ctx.fillStyle = '#25252d'; ctx.fillRect(sx - 13, sy - 8, 26, 16);
                ctx.strokeStyle = '#f3b85b'; ctx.lineWidth = 2;
                ctx.strokeRect(sx - 13, sy - 8, 26, 16);
                ctx.beginPath();
                for (var stripe = -9; stripe <= 9; stripe += 7) {
                    ctx.moveTo(sx + stripe, sy - 6);
                    ctx.lineTo(sx + stripe + 5, sy + 6);
                }
                ctx.stroke();
            }
        }
        for (i = 0; i < this.bullets.length; i++) { this.bullets[i].draw(cam); }
        this.room.draw_hazards_over(cam);    // 需求 3：地刺 / 电场 / 喷焰
        this.fx.draw_over(cam);
        if (window.__TOUCH__ && window.__TOUCH__.enabled && this.player && this.player.alive) {
            var px = this.player.x + cam[0], py = this.player.y + cam[1];
            var pa = this.player.aim || 0;
            var ca = Math.cos(pa), sa = Math.sin(pa);
            var lk = this._mobile_lock && this._mobile_lock.alive ? this._mobile_lock : null;
            ctx.save();
            ctx.strokeStyle = lk ? 'rgba(255,206,110,0.44)' : 'rgba(110,230,255,0.30)';
            ctx.lineWidth = 1.5;
            ctx.beginPath();
            for (var ds = 16; ds <= 48; ds += 12) {
                ctx.moveTo(px + ca * ds, py + sa * ds);
                ctx.lineTo(px + ca * (ds + 7), py + sa * (ds + 7));
            }
            ctx.stroke();
            if (lk) {
                var lx = lk.x + cam[0], ly = lk.y + cam[1];
                var lr = (lk.radius || 14) + 5 + Math.sin(Date.now() * 0.008) * 1.5;
                ctx.strokeStyle = 'rgba(255,118,88,0.90)';
                ctx.lineWidth = 1.5;
                ctx.beginPath();
                ctx.arc(lx, ly, lr, 0, TAU);
                ctx.moveTo(lx - lr - 3, ly); ctx.lineTo(lx - lr + 3, ly);
                ctx.moveTo(lx + lr - 3, ly); ctx.lineTo(lx + lr + 3, ly);
                ctx.moveTo(lx, ly - lr - 3); ctx.lineTo(lx, ly - lr + 3);
                ctx.moveTo(lx, ly + lr - 3); ctx.lineTo(lx, ly + lr + 3);
                ctx.stroke();
            }
            ctx.restore();
        }
    };
    Game.prototype._draw_crosshair = function () {
        if (window.__TOUCH__ && window.__TOUCH__.enabled) { return; }
        var x = this.mouse_canvas[0], y = this.mouse_canvas[1];
        if (!(x >= 0 && x <= VIEW_W && y >= 0 && y <= VIEW_H)) { return; }
        ctx.save();
        ctx.strokeStyle = 'rgba(255,255,255,0.65)';
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.arc(Math.round(x), Math.round(y), 6, 0, TAU);
        ctx.stroke();
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(x, y - 9); ctx.lineTo(x, y - 5);
        ctx.moveTo(x, y + 5); ctx.lineTo(x, y + 9);
        ctx.moveTo(x - 9, y); ctx.lineTo(x - 5, y);
        ctx.moveTo(x + 5, y); ctx.lineTo(x + 9, y);
        ctx.stroke();
        ctx.restore();
    };
    Game.prototype.draw = function () {
        ctx.setTransform(1, 0, 0, 1, 0, 0);
        ctx.textAlign = 'left';
        ctx.textBaseline = 'top';
        ctx.imageSmoothingEnabled = false;
        var st = this.state;
        ctx.clearRect(0, 0, VIEW_W, VIEW_H);
        if (st === 'title') {
            drawTitle(this);
        } else if (st === 'help') {
            drawTitle(this);
            drawHelp(this);
        } else if (st === 'changelog') {
            drawChangelog(this);
        } else if (st === 'slots' || st === 'slot_create' || st === 'slot_confirm') {
            drawSlots(this);
        } else if (st === 'quit') {
            if (this.room) { this._draw_world(); drawHUD(this); }
            drawQuit();
        } else if (st === 'paused') {
            if (this.room) { this._draw_world(); drawHUD(this); }
            drawPause(this);
        } else if (st === 'gameover') {
            if (this.room) { this._draw_world(); }
            drawGameOver(this);
        } else if (st === 'victory') {
            if (this.room) { this._draw_world(); }
            drawVictory(this);
        } else if (st === 'levelclear') {
            if (this.room) { this._draw_world(); }
            drawLevelClear(this);
        } else if (st === 'lobby') {
            drawLobby(this);
        } else if (st === 'talent') {
            drawTalent(this);
        } else if (st === 'story') {
            drawStory(this);
        } else if (st === 'route_choice') {
            this._draw_world();
            drawRouteChoice(this);
        } else {
            fillRect(C_BG, 0, 0, VIEW_W, VIEW_H);
            this._draw_world();
            drawHUD(this);
            drawFlash(this);
            drawTransition(this);
            drawCollectionPopup(this);
            if (!this.collection_popup) { this._draw_crosshair(); }
        }
    };
    Game.prototype.step = function (dt, actions) {
        if (actions !== undefined) { this.inp = actions; }
        this.update(dt);
        this.draw();
        return this.state;
    };

    // ==================================================================== 输入层
    var Input = {
        keys: {},
        mouse: { left: false, right: false }
    };

    var KEYMAP = {
        ArrowLeft: 'arrowleft', ArrowRight: 'arrowright',
        ArrowUp: 'arrowup', ArrowDown: 'arrowdown',
        Enter: 'enter', Escape: 'escape', ' ': ' ', Shift: 'shift',
        Control: 'control', F11: 'f11', Tab: 'tab',
        Backspace: 'backspace', Delete: 'delete'
    };
    function keyName(e) {
        if (KEYMAP[e.key] !== undefined) { return KEYMAP[e.key]; }
        return String(e.key || '').toLowerCase();
    }

    var game = null;

    function toggleFullscreen() {
        try {
            if (!document.fullscreenElement) {
                if (document.documentElement.requestFullscreen) {
                    document.documentElement.requestFullscreen();
                }
            } else if (document.exitFullscreen) {
                document.exitFullscreen();
            }
        } catch (e) { /* 用户拒绝或浏览器不支持时忽略 */ }
    }

    function attachInput() {
        window.addEventListener('keydown', function (e) {
            Sfx.unlock();
            var k = keyName(e);
            if (k === ' ' || k === 'arrowup' || k === 'arrowdown' ||
                k === 'arrowleft' || k === 'arrowright') {
                if (game && game.state !== 'playing') { e.preventDefault(); }
            }
            // 建档输入框里 Backspace 会触发浏览器后退，必须拦掉
            if (k === 'backspace' && game && game.state === 'slot_create') {
                e.preventDefault();
            }
            if (k === 'f11') { e.preventDefault(); }
            if (e.repeat) { return; }
            Input.keys[k] = true;
            if (game) { game._keydown(k); }
        });
        window.addEventListener('keyup', function (e) {
            Input.keys[keyName(e)] = false;
        });
        window.addEventListener('blur', function () {
            Input.keys = {};
            Input.mouse.left = false;
            Input.mouse.right = false;
        });

        function syncMouse(e) {
            var r = cv.getBoundingClientRect();
            if (!game || !r.width || !r.height) { return; }
            game.mouse_canvas = [
                (e.clientX - r.left) / r.width * VIEW_W,
                (e.clientY - r.top) / r.height * VIEW_H
            ];
        }
        cv.addEventListener('mousemove', function (e) {
            syncMouse(e);
            if (game && game.state !== 'playing') {
                game.menu_hit(game.mouse_canvas[1]);
            }
        });
        cv.addEventListener('mousedown', function (e) {
            if (window.__TOUCH__ && window.__TOUCH__.enabled && e.sourceCapabilities &&
                e.sourceCapabilities.firesTouchEvents) { e.preventDefault(); return; }
            Sfx.unlock();
            syncMouse(e);
            if (e.button === 0) { Input.mouse.left = true; }
            if (e.button === 2) { Input.mouse.right = true; }
            if (game && game.state !== 'playing') { game._click(); }
            e.preventDefault();
        });
        window.addEventListener('mouseup', function (e) {
            if (e.button === 0) { Input.mouse.left = false; }
            if (e.button === 2) { Input.mouse.right = false; }
        });
        cv.addEventListener('contextmenu', function (e) { e.preventDefault(); });
    }

    function resize() {
        var mobile = !!(window.__TOUCH__ && window.__TOUCH__.enabled);
        var wrap = document.getElementById('wrap');
        var style = window.getComputedStyle ? window.getComputedStyle(wrap) : {};
        var safeW = (parseFloat(style.paddingLeft) || 0) + (parseFloat(style.paddingRight) || 0);
        var safeH = (parseFloat(style.paddingTop) || 0) + (parseFloat(style.paddingBottom) || 0);
        var availW = Math.max(200, window.innerWidth - (mobile ? safeW : 24));
        var availH = Math.max(120, window.innerHeight - (mobile ? safeH : 76));
        var s = Math.min(availW / VIEW_W, availH / VIEW_H);
        // 电脑端维持像素倍率；手机端连续缩放以填满 16:9 可用区域。
        if (!mobile) {
            s = s >= 2 ? Math.floor(s) : (s >= 1 ? Math.floor(s * 2) / 2 : Math.max(0.4, s));
        }
        cv.style.width = Math.round(VIEW_W * s) + 'px';
        cv.style.height = Math.round(VIEW_H * s) + 'px';
    }

    // ==================================================================== 启动
    var _last = 0;
    var fpsStart = 0, fpsFrames = 0, fpsValue = 0;
    function frame(now) {
        var dt = (now - _last) / 1000.0;
        _last = now;
        if (!fin(dt) || dt < 0) { dt = 0; }
        if (dt > MAX_DT) { dt = MAX_DT; }
        if (game) {
            game.update(dt);
            game.draw();
        }
        fpsFrames++;
        if (!fpsStart) { fpsStart = now; }
        if (now - fpsStart >= 1000) {
            fpsValue = Math.round(fpsFrames * 1000 / (now - fpsStart));
            fpsFrames = 0; fpsStart = now;
        }
        var perf = document.getElementById('perf');
        if (perf) {
            perf.style.display = game && game.setting.show_fps ? 'block' : 'none';
            if (perf.style.display === 'block') { perf.textContent = fpsValue + ' FPS'; }
        }
        if (window.__TOUCH__ && window.__TOUCH__.syncControls) {
            window.__TOUCH__.syncControls();
        }
        window.requestAnimationFrame(frame);
    }

    function boot() {
        var loading = document.getElementById('loading');
        loadAssets().then(function () {
            return window.__NATIVE_SAVE__ ? window.__NATIVE_SAVE__.ready : null;
        }).then(function () {
            game = new Game(null, true);
            window.__GAME__ = game;
            function pauseForBackground() {
                if (!game) { return; }
                if (game.state === 'playing') {
                    game.state = 'paused';
                    game.pause_index = 0;
                }
                Input.keys = {};
                Input.mouse.left = Input.mouse.right = false;
                if (window.__TOUCH__ && window.__TOUCH__.reset) { window.__TOUCH__.reset(); }
                if (game.profile) { game._write_save(); }
            }
            window.addEventListener('blur', pauseForBackground);
            window.addEventListener('pagehide', pauseForBackground);
            document.addEventListener('visibilitychange', function () {
                if (document.hidden) { pauseForBackground(); }
            });
            document.addEventListener('freeze', pauseForBackground);
            window.__VIEW__ = { W: VIEW_W, H: VIEW_H, CAM: CAM_OFF };
            // 暴露内部构造器，供自动化测试 / 控制台调试使用
            window.__INTERNALS__ = {
                Game: Game, Dungeon: Dungeon, Room: Room, Pickup: Pickup,
                Basketball: Basketball,
                Enemy: Enemy, Player: Player, Prop: Prop, makeEnemy: makeEnemy,
                Weapon: WEAPONS, WPN_ORDER: WPN_ORDER,
                makeRng: makeRng,
                // 碰撞/脱困工具（供 W12 防卡死测试）
                circleSolid: circleSolid, collideTest: collideTest,
                moveCircle: moveCircle, findFreeSpot: findFreeSpot,
                unstick: unstick, ENTRY_FROM: ENTRY_FROM,
                // 场景交互物（供 W13 测试）
                Trap: Trap, Cover: Cover, Cave: Cave, Bullet: Bullet,
                TRAP_SPEC: TRAP_SPEC, TRAP_BY_SCENE: TRAP_BY_SCENE,
                planScene: planScene, inTrap: inTrap, SCENE_KEYS: SCENE_KEYS,
                // 污染减益（供 W14 测试）
                explode: explode,
                // 需求 6：品质机制与近战（供 W21/W22 测试）
                specMech: specMech, meleeSwing: meleeSwing,
                settings: {
                    VIEW_W: VIEW_W, VIEW_H: VIEW_H, FLOORS: FLOORS,
                    GRID_W: GRID_W, GRID_H: GRID_H, TILE: TILE,
                    ROOM_COLS: ROOM_COLS, ROOM_ROWS: ROOM_ROWS,
                    ROOM_CX: ROOM_CX, ROOM_CY: ROOM_CY,
                    ROOM_PX_W: ROOM_PX_W, ROOM_PX_H: ROOM_PX_H, CAM_OFF: CAM_OFF,
                    STUCK_SECONDS: STUCK_SECONDS,
                    HITSTOP_MAX: HITSTOP_MAX, P_KNOCK_TIME: P_KNOCK_TIME
                }
            };
            window.__DUNGEON__ = Dungeon;
            window.__MUSIC__ = Music;
            // 需求 10：暴露存档仓库，供自动化测试清档 / 造档
            window.__SAVE__ = SaveStore;
            window.__SAVE_KEYS__ = { main: SAVE_STORE_KEY, backup: SAVE_BACKUP_KEY };
            window.__newProfile__ = newProfile;
            // 需求（输入健壮性）：暴露 Input 供 W24 输入路径回归测试
            window.__INPUT__ = { Input: Input, keyName: keyName };
            if (loading) { loading.style.display = 'none'; }
            attachInput();
            resize();
            window.addEventListener('resize', resize);
            _last = nowMs();
            window.requestAnimationFrame(frame);
        });
    }

    if (document.readyState === 'complete' || document.readyState === 'interactive') {
        setTimeout(boot, 0);
    } else {
        window.addEventListener('DOMContentLoaded', boot);
    }
})();
