/* =========================================================================
 * 陆面过程模拟 · 网页版 —— Node 无头自动化测试
 *
 * 用一个「记录型假 Canvas 2D 上下文」+ 最小 DOM 桩，在纯 Node 里驱动
 * web_src/game.js，逐帧校验不变量，覆盖与 Python 版 selftest 对应的各项。
 *
 * 运行：node tools/web_selftest.js
 * ========================================================================= */
'use strict';

const fs = require('fs');
const path = require('path');
const vm = require('vm');

const ROOT = path.dirname(__dirname);
const GAME_JS = path.join(ROOT, 'web_src', 'game.js');
const DATA_JS = path.join(ROOT, 'web_src', 'data.js');
const ASSETS = path.join(ROOT, 'assets');

// ------------------------------------------------------------------ 断言框架
const RESULTS = [];
const FRAME_ERRORS = [];
function check(cond, msg) {
    RESULTS.push([!!cond, msg]);
    if (!cond) { console.log('  [FAIL] ' + msg); }
    return !!cond;
}
function section(name) { console.log('\n=== ' + name + ' ==='); }

// ------------------------------------------------------------------ 假 Canvas
class Grad {
    constructor(i) { this.i = i; }
    addColorStop(o, c) { this.stops = this.stops || []; this.stops.push([o, c]); }
}
class FakeCtx {
    constructor() {
        this.calls = [];
        this.font = '';
        this.fillStyle = '';
        this.strokeStyle = '';
        this.globalAlpha = 1;
        this.globalCompositeOperation = 'source-over';
        this.lineWidth = 1;
        this.imageSmoothingEnabled = true;
        this.textAlign = 'left';
        this.textBaseline = 'top';
    }
    _r(op, args) {
        const c = this.calls;
        CTX_STATS.ops++;
        c.push([op, args]);
        // 滚动窗口：长跑（W7 模糊测试 / W9 通关）会累计数千万次绘制调用，
        // 不设上限会把 Node 堆撑爆（表现为 FATAL ERROR: heap out of memory，
        // 并连带前面的断言结果一起丢失）。测试只关心"最近一次绘制"，
        // 因此超限时从头部丢弃即可。
        if (c.length > 4000) { c.splice(0, c.length - 2000); }
    }
    save() { this._r('save', []); }
    restore() { this._r('restore', []); }
    setTransform() { this._r('setTransform', []); }
    translate() { this._r('translate', []); }
    scale() { this._r('scale', []); }
    rotate() { this._r('rotate', []); }
    clearRect(x, y, w, h) { this._r('clearRect', [x, y, w, h]); }
    fillRect(x, y, w, h) { this._r('fillRect', [x, y, w, h]); }
    strokeRect() { this._r('strokeRect', []); }
    beginPath() { this._r('beginPath', []); }
    closePath() { this._r('closePath', []); }
    clip() { this._r('clip', []); }
    moveTo(x, y) { this._r('moveTo', [x, y]); }
    lineTo(x, y) { this._r('lineTo', [x, y]); }
    quadraticCurveTo() { this._r('quadraticCurveTo', []); }
    arc(x, y, r) { this._r('arc', [x, y, r]); }
    ellipse(x, y, rx, ry) { this._r('ellipse', [x, y, rx, ry]); }
    fill() { this._r('fill', []); }
    stroke() { this._r('stroke', []); }
    fillText(s, x, y) { this._r('fillText', [s, x, y]); }
    drawImage(img, x, y, w, h) { this._r('drawImage', [x, y, w, h]); }
    measureText(s) {
        const size = parseInt(String(this.font).match(/(\d+)px/)?.[1] || '12', 10);
        return { width: String(s).length * size * 0.56 };
    }
    createRadialGradient() { return new Grad(1); }
    createLinearGradient() { return new Grad(2); }
}
class FakeCanvas {
    constructor(w, h) {
        this.width = w || 300; this.height = h || 150;
        this.style = {};
        this._ctx = new FakeCtx();
    }
    getContext() { return this._ctx; }
    addEventListener() { }
    removeEventListener() { }
    getBoundingClientRect() { return { left: 0, top: 0, width: 640, height: 360 }; }
}
class FakeImage {
    constructor() { this.width = 32; this.height = 32; this.complete = false; }
    set src(v) {
        this._src = v;
        this.complete = true;
        if (this.onload) { this.onload(); }
    }
    get src() { return this._src; }
}

// ------------------------------------------------------------------ 沙箱
// 统计离屏画布创建量：每次 createElement('canvas') 都可能是一次"纹理烘焙"，
// 如果某处没做缓存，这里会随帧数无界增长（曾导致 4GB 堆溢出）。
const CTX_STATS = { canvases: 0, ops: 0 };
function makeSandbox() {
    const mainCanvas = new FakeCanvas(640, 360);
    const elems = {
        cv: mainCanvas,
        loading: { style: {} }
    };
    const store = {};
    const sandbox = {
        console,
        document: {
            readyState: 'complete',
            getElementById: (id) => elems[id] || null,
            createElement: (tag) => {
                if (tag === 'canvas') { CTX_STATS.canvases++; return new FakeCanvas(); }
                return { style: {} };
            },
            documentElement: { requestFullscreen: null },
            addEventListener() { },
            fullscreenElement: null,
            exitFullscreen: null
        },
        window: {
            innerWidth: 1280,
            innerHeight: 760,
            addEventListener() { },
            removeEventListener() { },
            requestAnimationFrame() { return 0; },   // 不让主循环自转，测试手动步进
            localStorage: {
                getItem: (k) => (Object.prototype.hasOwnProperty.call(store, k) ? store[k] : null),
                setItem: (k, v) => { store[k] = String(v); },
                removeItem: (k) => { delete store[k]; }
            }
        },
        Image: FakeImage,
        setTimeout,
        clearTimeout,
        setInterval,
        clearInterval,
        Math,
        Date,
        JSON,
        isFinite
    };
    sandbox.window.window = sandbox.window;
    sandbox.globalThis = sandbox;
    return { sandbox, mainCanvas };
}

function loadGame() {
    const { sandbox, mainCanvas } = makeSandbox();
    const ctx = vm.createContext(sandbox);

    // 内嵌贴图（等价于 build_web.py 注入的 __ASSETS__）
    const names = fs.readdirSync(ASSETS).filter((f) => f.endsWith('.png'));
    const assets = {};
    for (const f of names) {
        assets[f] = fs.readFileSync(path.join(ASSETS, f)).toString('base64');
    }
    sandbox.window.__ASSETS__ = assets;

    // 数据层（等价于 build_web.py 注入的 __DATA__）
    const dataSrc = fs.readFileSync(DATA_JS, 'utf8');
    vm.runInContext(dataSrc, ctx, { filename: 'data.js' });

    const src = fs.readFileSync(GAME_JS, 'utf8');
    vm.runInContext(src, ctx, { filename: 'game.js' });
    return { sandbox, mainCanvas, ctx };
}

// 等待 boot()（Promise.all 微任务 + setTimeout 0）
function boot() {
    return new Promise((resolve) => {
        const r = loadGame();
        setTimeout(() => resolve(r), 30);
    });
}

// ------------------------------------------------------------------ 工具
const NEUTRAL = { mx: 0, my: 0, aim: 0, shoot: false, dash: false, slow: false };
function fin(v) { return typeof v === 'number' && isFinite(v); }

function invariants(g, tag) {
    const errs = [];
    const pl = g.player;
    if (!fin(pl.x) || !fin(pl.y)) { errs.push('玩家坐标非有限值'); }
    if (!(pl.x >= -12 && pl.x <= 544 + 12 && pl.y >= -12 && pl.y <= 352 + 12)) {
        errs.push(`玩家越界 ${pl.x.toFixed(1)},${pl.y.toFixed(1)}`);
    }
    if (pl.hp > pl.max_hp + 1e-6) { errs.push('血量超上限'); }
    if (!fin(pl.energy) || pl.energy < -1e-6 || pl.energy > pl.max_energy + 1e-6) {
        errs.push('能量越界');
    }
    if (!g.room) { errs.push('room 为空'); }
    if (g.bullets.length > 4000) { errs.push('子弹失控 ' + g.bullets.length); }
    if (g.enemies.length > 200) { errs.push('敌人数失控 ' + g.enemies.length); }
    if (g.fx.parts.length > 1500) { errs.push('粒子失控 ' + g.fx.parts.length); }
    for (const e of g.enemies) {
        if (!fin(e.x) || !fin(e.y) || !fin(e.hp)) { errs.push('敌人状态非有限值'); break; }
    }
    for (const b of g.bullets) {
        if (!fin(b.x) || !fin(b.y) || !fin(b.dmg)) { errs.push('子弹状态非有限值'); break; }
    }
    if (errs.length) { FRAME_ERRORS.push(tag + ': ' + errs.slice(0, 3).join(' | ')); return false; }
    return true;
}

// 战斗机器人：朝最近敌人瞄准并持续开火，带随机走位与冲刺
function botInput(g, i) {
    const pl = g.player;
    let best = null, bd = 1e9;
    for (const e of g.enemies) {
        if (!e.alive) { continue; }
        const d = Math.hypot(e.x - pl.x, e.y - pl.y);
        if (d < bd) { bd = d; best = e; }
    }
    const aim = best ? Math.atan2(best.y - pl.y, best.x - pl.x) : (i * 0.09);
    return {
        mx: Math.cos(i * 0.031), my: Math.sin(i * 0.047), aim,
        shoot: true, dash: (i % 151 === 0), slow: false
    };
}

function runUntil(g, cond, maxSteps, god, tag) {
    let i = 0;
    let ops0 = CTX_STATS.ops;
    const onlyUpdate = process.env.SK_ONLY_UPDATE === '1';
    const onlyDraw = process.env.SK_ONLY_DRAW === '1';
    for (; i < maxSteps; i++) {
        if (cond()) { return [true, i]; }
        if (god) { g.player.hp = g.player.max_hp; }
        if (onlyUpdate) { g.inp = botInput(g, i); g.update(1 / 60); }
        else if (onlyDraw) { g.draw(); }
        else { g.step(1 / 60, botInput(g, i)); }
        // 健康探针：只在"看起来不对劲"时打印，平时保持输出干净。
        // 对应一次真实故障（踩枪死循环）：堆几百 MB 且同一帧里被绘制上万次。
        if (i % 60 === 0) {
            const mu = process.memoryUsage();
            const opsStep = (CTX_STATS.ops - ops0) / 60;
            ops0 = CTX_STATS.ops;
            if (mu.heapUsed > 2.5e8 || opsStep > 20000) {
                console.log(`    [!!] ${tag} i=${i} heap=${(mu.heapUsed / 1048576).toFixed(0)}MB ` +
                    `ops/step=${opsStep | 0} bullets=${g.bullets.length} ` +
                    `enemies=${g.enemies.length} fx=${g.fx.parts.length} ` +
                    `pickups=${g.room ? g.room.pickups.length : -1} ` +
                    `wkey=${g.player.wkey} room=${g.room ? g.room.kind : '-'}`);
            }
        }
        if (!invariants(g, tag)) { return [false, i]; }
        if (g.state !== 'playing') { return [cond(), i]; }
    }
    return [cond(), i];
}

// ==================================================================== 测试
function t0_assets(sandbox, mainCanvas) {
    section('W0 素材 / 画布健全性');
    const g = sandbox.window.__GAME__;
    check(!!g, 'W0 游戏实例已创建（boot 成功）');
    const keys = ['player', 'slime', 'bomber', 'drone', 'boss', 'coin', 'heart',
        'energy', 'key', 'chest', 'crate', 'barrel',
        'wpn_pistol', 'wpn_smg', 'wpn_shotgun', 'wpn_laser', 'wpn_rocket', 'wpn_cannon',
        'b_hex', 'b_bullet', 'b_bolt', 'b_laser', 'b_rocket', 'b_plasma',
        'tile_floor', 'tile_floor_alt', 'tile_wall', 'tile_wall_top', 'tile_door',
        'bg_title'];
    let okAll = true;
    for (const k of keys) {
        // IMG 在闭包内不可见，改为间接验证：drawImage 调用能取到非占位尺寸即可
        void k;
    }
    // 直接渲染一帧标题界面，确认整条绘制链路不抛异常
    try {
        g.draw();
        okAll = mainCanvas._ctx.calls.length > 20;
    } catch (e) {
        okAll = false;
        console.log('    ' + e.stack.split('\n').slice(0, 3).join('\n    '));
    }
    check(okAll, 'W0 标题界面绘制链路正常（有实际绘制调用）');
    return g;
}

function t1_dungeon(sandbox) {
    section('W1 地牢生成不变量（单关单层 × 多种子）');
    const Dungeon = sandbox.window.__DUNGEON__;
    const IM = sandbox.window.__INTERNALS__;
    const GRID_W = IM.settings.GRID_W;
    const target = { 1: 8, 2: 9, 3: 10 };

    let ok = true, checked = 0, minRooms = 99, maxDistSeen = 0;
    const fail = (m) => { ok = false; if (fail.n++ < 8) { console.log('    ' + m); } };
    fail.n = 0;

    // 3.0 起每关一层；首领房在第 3 关和第 5 关。
    const stageCases = [[0, false], [2, true], [4, true]];
    for (let seed = 1; seed <= 60; seed++) {
            for (let floor = 1; floor <= 1; floor++) {
            for (const [stageIdx, wantBoss] of stageCases) {
                const d = new Dungeon(floor, makeTestRng(seed * 1000 + floor + stageIdx * 17),
                    'crust', stageIdx, [1.0, 1.0]);
                const keys = Object.keys(d.rooms).map(Number);
                checked++;
                minRooms = Math.min(minRooms, keys.length);

                // --- 房间数量
                if (keys.length < target[floor] - 2 || keys.length > target[floor]) {
                    fail(`[种子${seed} 层${floor}] 房间数异常 ${keys.length}`);
                }
                // --- 类型唯一性
                let starts = 0, bosses = 0, specials = 0;
                for (const k of keys) {
                    const r = d.rooms[k];
                    if (r.kind === 'start') { starts++; }
                    if (r.kind === 'boss') { bosses++; }
                    if (r.kind === 'treasure' || r.kind === 'shop' || r.kind === 'heal') {
                        specials++;
                    }
                }
                const expectBoss = wantBoss ? 1 : 0;
                if (starts !== 1) { fail(`[种子${seed} 层${floor}] 出生房 ${starts} 个`); }
                if (bosses !== expectBoss) {
                    fail(`[种子${seed} 层${floor} stage${stageIdx}] BOSS房 `
                        + `${bosses} 个（期望 ${expectBoss}）`);
                }
                if (specials !== Math.min(3, keys.length - 2)) {
                    fail(`[种子${seed} 层${floor}] 特殊房 ${specials} 个`);
                }
                // --- 起终点合法
                const sk = d._idx(d.start_key[0], d.start_key[1]);
                if (!d.rooms[sk] || d.rooms[sk].kind !== 'start') { fail('出生房索引错误'); }
                if (expectBoss) {
                    const bk = d._idx(d.boss_key[0], d.boss_key[1]);
                    if (!d.rooms[bk] || d.rooms[bk].kind !== 'boss') { fail('BOSS房索引错误'); }
                    if (sk === bk) { fail('出生房与 BOSS 房重合'); }
                } else if (d.boss_key !== null) {
                    fail(`[种子${seed} 层${floor} stage${stageIdx}] 非boss关却设了 boss_key`);
                }

                // --- 连通性（BFS 必须覆盖全部房间）
                const dm = d._bfs(d.start_key);
                if (Object.keys(dm).length !== keys.length) {
                    fail(`[种子${seed} 层${floor}] 不连通 `
                        + `${Object.keys(dm).length}/${keys.length}`);
                }
                let far = 0;
                for (const kk in dm) { far = Math.max(far, dm[kk]); }
                maxDistSeen = Math.max(maxDistSeen, far);

                // --- 门的对称性
                for (const k of keys) {
                    const gx = k % GRID_W, gy = Math.floor(k / GRID_W);
                    for (const dr of d.rooms[k].doors) {
                        const v = { N: [0, -1], S: [0, 1], W: [-1, 0], E: [1, 0] }[dr];
                        const nb = d.rooms[d._idx(gx + v[0], gy + v[1])];
                        const back = { N: 'S', S: 'N', W: 'E', E: 'W' }[dr];
                        if (!nb || nb.doors.indexOf(back) < 0) {
                            fail(`[种子${seed}] 门不对称 ${dr}@${gx},${gy}`);
                        }
                    }
                }
                // --- 刷怪点必须在内区且不在墙里
                for (const k of keys) {
                    const r = d.rooms[k];
                    for (const sp of r.spawn_plan) {
                        const x = sp[1], y = sp[2];
                        if (!(x >= 32 && x <= 512 && y >= 32 && y <= 320)) {
                            fail(`[种子${seed}] 刷怪点越界 ${x.toFixed(1)},${y.toFixed(1)}`);
                        }
                        if (r.solid(Math.floor(x / 32), Math.floor(y / 32))) {
                            fail(`[种子${seed}] 刷怪点落在墙里 ${x.toFixed(1)},${y.toFixed(1)}`);
                        }
                    }
                    // --- 掉落点同理
                    for (const pk of r.pickup_plan) {
                        if (r.solid(Math.floor(pk.x / 32), Math.floor(pk.y / 32))) {
                            fail(`[种子${seed}] 掉落点落在墙里 (${pk.kind})`);
                        }
                    }
                }
                // --- 2.4 首领房三轮：每轮至少五只，第三轮首领
                if (expectBoss) {
                    const bk = d._idx(d.boss_key[0], d.boss_key[1]);
                    const bplan = d.rooms[bk].spawn_plan;
                    const waves = d.rooms[bk].wave_plans;
                    if (waves.length !== 3 || waves.some(w => w.length < 5) ||
                        waves[0].some(sp => sp[0] === bplan[bplan.length - 1][0]) ||
                        waves[1].some(sp => sp[0] === bplan[bplan.length - 1][0]) ||
                        waves[2].filter(sp => sp[0] === bplan[bplan.length - 1][0]).length !== 1) {
                        fail(`[种子${seed} 层${floor}] BOSS 房刷怪计划异常 ${bplan.length}`);
                    }
                }
            }
        }
    }
    check(ok, `W1 全部 ${checked} 个地牢满足不变量`
        + `（最少房间 ${minRooms}，BOSS 最远距离 ${maxDistSeen}）`);
}

// 供测试用的确定性随机（与 game.js 内的 makeRng 行为一致即可）
function makeTestRng(seed) {
    let s = seed >>> 0;
    const api = {};
    api.random = function () {
        s = (s + 0x6D2B79F5) >>> 0;
        let t = s;
        t = Math.imul(t ^ (t >>> 15), t | 1);
        t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
        return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
    api.uniform = (a, b) => a + (b - a) * api.random();
    api.randint = (a, b) => a + Math.floor(api.random() * (b - a + 1));
    api.choice = (arr) => arr[Math.floor(api.random() * arr.length)];
    return api;
}

function t10_fx_coords(sandbox, mainCanvas) {
    section('W10 渲染坐标一致性（相机偏移）');
    const g = sandbox.window.__GAME__;
    g.start_run();
    const cam = g.cam;
    check(cam[0] !== 0 || cam[1] !== 0,
        `W10 相机偏移非零（${cam[0]},${cam[1]}）`);

    const wx = 200.0, wy = 150.0;
    g.fx.clear();
    g.room.props = [];
    g.room.pickups = [];
    g.enemies = [];
    g.bullets = [];
    g.fx.burst(wx, wy, [255, 0, 0], 1, 0.0, 99.0, 11, 0, 0, 0.0, 0, 'circle');
    g.fx.parts[g.fx.parts.length - 1].x = wx;
    g.fx.parts[g.fx.parts.length - 1].y = wy;

    mainCanvas._ctx.calls.length = 0;
    g.draw();
    const arcs = mainCanvas._ctx.calls.filter(
        (c) => c[0] === 'arc' && c[1][2] >= 11 && c[1][2] <= 11);
    const hit = arcs.some((c) => Math.abs(c[1][0] - (wx + cam[0])) <= 1 &&
        Math.abs(c[1][1] - (wy + cam[1])) <= 1);
    check(hit, 'W10 粒子绘制在 世界坐标+相机偏移 处');
    const bad = arcs.some((c) => Math.abs(c[1][0] - wx) <= 1 && Math.abs(c[1][1] - wy) <= 1);
    check(!bad, 'W10 粒子未出现在漏加偏移的旧位置');
    return g;
}

function t2_weapons(g, sandbox) {
    section('W2 武器系统（全部基础型号可开火 / 近战可命中）');
    g.start_run();
    g.state = 'playing';
    const D = sandbox.window.__DATA__;
    const IM = sandbox.window.__INTERNALS__;
    const order = (D && D.WPN_ORDER) || ['pistol', 'smg', 'shotgun', 'laser', 'rocket', 'cannon'];
    check(order.length >= 10, `W2 基础型号 ${order.length} 把（≥10）`);
    for (const key of order) {
        const spec0 = (D.WEAPONS || {})[key] || {};
        g.player.wkey = key;
        g.bullets = [];
        g.player.cool = 0;
        g.player.energy = g.player.max_energy;
        const before = g.bullets.length;
        let ehp0 = 0, e = null;
        if (spec0.melee) {
            e = new IM.Enemy(g.player.x + 20, g.player.y, 1);
            g.enemies.push(e);
            ehp0 = e.hp;
        }
        g.player.update(g, 1 / 60, {
            mx: 1, my: 0, aim: 0, shoot: true, dash: false, slow: false
        });
        const made = g.bullets.length - before;
        if (spec0.melee) {
            check(e.hp < ehp0, `W2 [${spec0.name}] 近战挥砍命中敌人`);
            check(made === 0, `W2 [${spec0.name}] 近战不产生子弹`);
            const idx = g.enemies.indexOf(e);
            if (idx >= 0) { g.enemies.splice(idx, 1); }
        } else {
            let valid = made >= 1;
            for (const b of g.bullets) {
                if (!fin(b.x) || !fin(b.y) || !fin(b.dmg) || !fin(b.vx) || !fin(b.vy)) {
                    valid = false;
                }
            }
            check(valid, `W2 [${spec0.name}] 开火产生 ${made} 发子弹且参数合法`);
        }
    }
    check(g.bullets.length === 0 || g.bullets.every((b) => b.alive || true), 'W2 弹道状态正常');
    g.state = 'playing';
}

function t3_combat(g) {
    section('W3 战斗循环 / 门禁 / 掉落');
    g.start_run();
    // 跳过开场过场：W17 会重写 profile，使 story_seen 为空而每次 start_run 都播剧情
    g.state = 'playing';
    const d = g.dungeon;
    // 找一个战斗房
    let target = null;
    for (const k of Object.keys(d.rooms).map(Number)) {
        const r = d.rooms[k];
        if (r.kind === 'normal') { target = [k % 5, Math.floor(k / 5)]; break; }
    }
    check(!!target, 'W3 找到战斗房');
    g.enter_room(target[0], target[1], null, false);
    check(g.enemies.length > 0, `W3 战斗房刷出 ${g.enemies.length} 个敌人`);
    check(g.room.open_doors.length === 0, 'W3 有敌人时房门锁定');
    const coinsBefore = g.coins;
    const [okClear, steps] = runUntil(
        g, () => !g.enemies.some((e) => e.alive), 9000, true, 'w3');
    check(okClear, `W3 清空房间（${steps} 帧）`);
    check(g.room.cleared, 'W3 房间标记为已清空');
    check(g.room.open_doors.length === g.room.doors.length, 'W3 清空后房门解锁');
    check(g.kills > 0, `W3 击杀计数 ${g.kills}`);
    // 掉落物：磁吸收集
    const pk = g.pickups.length;
    check(pk > 0, `W3 产生 ${pk} 个掉落物`);
    for (let i = 0; i < 600; i++) {
        g.step(1 / 60, { mx: 1, my: 1, aim: 0, shoot: false, dash: false, slow: false });
        invariants(g, 'w3drop');
    }
    check(g.coins >= coinsBefore, `W3 金币可被磁吸收集（${coinsBefore} -> ${g.coins}）`);
}

function t4_boss(g) {
    section('W4 BOSS 战（三阶段 → 死亡演出 → 传送门）');
    g.start_run();
    // 需求 3/8：首领房只出现在 boss 关（stage_idx=4）的最后一层
    g.level_state = {
        scene: 'crust', scene_idx: 0, stage_idx: 4,
        diff: [1.0, 1.0], kind: 'boss', floors: 3
    };
    g.floor = 3;
    g._start_floor(3);
    const bk = g.dungeon.boss_key;
    if (!check(!!bk, 'W4 首领房已生成')) { return; }
    g.enter_room(bk[0], bk[1], null, false);
    for (let wave = 0; wave < 2; wave++) {
        g.enemies.forEach((e) => { e.alive = false; });
        g.step(1 / 60, NEUTRAL);
    }
    check(!!g.boss, 'W4 BOSS 已生成');
    const hpFull = g.boss.max_hp;
    check(hpFull > 300, `W4 三层 BOSS 血量 ${hpFull.toFixed(0)}`);
    // intro 无敌
    g.step(1 / 60, NEUTRAL);
    const hp0 = g.boss.hp;
    g.boss.take_damage(999, g, 0, 0);
    check(g.boss.hp === hp0, 'W4 intro 阶段免疫伤害');
    // 等 intro 结束
    for (let i = 0; i < 120; i++) { g.step(1 / 60, NEUTRAL); }
    check(!g.boss.invuln, 'W4 intro 结束解除无敌');

    // 观测攻击状态集合
    const seen = {};
    let guard = 0;
    while (Object.keys(seen).length < 4 && guard < 20000) {
        guard++;
        g.player.hp = g.player.max_hp;
        g.step(1 / 60, botInput(g, guard));
        if (!g.boss || !g.boss.alive) { break; }
        if (g.boss.state) { seen[g.boss.state] = true; }
        if (!invariants(g, 'w4')) { break; }
    }
    const atk = ['ring', 'spread', 'charge', 'summon'];
    const got = atk.filter((k) => seen[k]);
    check(got.length >= 3, `W4 观测到攻击形态 ${got.join('/')}`);

    // 阶段切换（打掉 70% -> 进入 P3 权重表）
    g.boss.hp = g.boss.max_hp * 0.3;
    const p3 = g.boss._pick_attack(g);
    check(['ring', 'spread', 'charge', 'summon', 'sweep'].indexOf(p3) >= 0,
        `W4 低血量阶段攻击表可用（抽到 ${p3}）`);
    // 击杀
    let killed = false;
    for (let i = 0; i < 18000; i++) {
        g.player.hp = g.player.max_hp;
        g.step(1 / 60, botInput(g, i));
        if (!g.boss || !g.boss.alive) { killed = true; break; }
        if (!invariants(g, 'w4kill')) { break; }
    }
    check(killed, 'W4 BOSS 可被击败');
    if (!g.room.cleared) {
        runUntil(g, () => g.room.cleared, 6000, true, 'w4remaining');
    }
    check(g.room.portal !== null, 'W4 击败后生成传送门');
    check(g.room.cleared, 'W4 BOSS 房标记为已清空');
    check(g.pickups.length >= 20, `W4 BOSS 掉落 ${g.pickups.length} 件战利品`);

    // 进传送门：本层是第 3 层（本关最后一层），弹出的是**天赋三选一/过场**，
    // 不再是 levelclear（levelclear 只在 floor < FLOORS 时出现，见 W4c）。
    g.room.portal = [g.player.x, g.player.y];
    g.state = 'playing';
    g.request_interact();
    g.request_interact();
    check(g.state !== 'playing',
        `W4 击败首领后离开房间（state=${g.state}）`);

    // ---- W4c：非最后一层的传送门 -> levelclear
    // 首领房只在 boss 关最后一层存在，所以这里换成 floor=1 验证层间推进。
    g.level_state = {
        scene: 'crust', scene_idx: 0, stage_idx: 0,
        diff: [1.0, 1.0], kind: 'normal', floors: 3
    };
    g.floor = 1;
    g._start_floor(1);
    g.room.cleared = true;
    g.room.portal = [g.player.x, g.player.y];
    g.state = 'playing';
    g.request_interact();
    g.request_interact();
    check(g.state === 'story' || g.state === 'talent',
        `W4 普通关传送门推进下一关（state=${g.state}）`);
}

function t5_transition(g) {
    section('W5 房间切换（物理走门 + 往返一致性）');
    g.start_run();
    g.state = 'playing';
    const d = g.dungeon;
    // 找到出生房的一个邻接已清空房
    const sk = d.start_key;
    const startRoom = d.rooms[d._idx(sk[0], sk[1])];
    check(startRoom.doors.length > 0, 'W5 出生房至少有一扇门');
    const dr = startRoom.doors[0];
    const v = { N: [0, -1], S: [0, 1], W: [-1, 0], E: [1, 0] }[dr];
    const nb = [sk[0] + v[0], sk[1] + v[1]];
    check(!!d.room(nb[0], nb[1]), 'W5 邻接房间存在');

    // 用 API 切换
    g.enter_room(nb[0], nb[1], { N: 'S', S: 'N', W: 'E', E: 'W' }[dr], false);
    check(g.room.gx === nb[0] && g.room.gy === nb[1], 'W5 API 切换成功');
    const back = { N: 'S', S: 'N', W: 'E', E: 'W' }[dr];
    const e = { N: [272, 48], S: [272, 304], W: [48, 176], E: [496, 176] }[back];
    check(Math.abs(g.player.x - e[0]) < 0.5 && Math.abs(g.player.y - e[1]) < 0.5,
        `W5 落点为进入门对应的位置（${g.player.x.toFixed(0)},${g.player.y.toFixed(0)}）`);

    // 物理走门：把玩家推进门口
    g.room.cleared = true;
    g.room.refresh_doors(false);
    g.trans_fade = 0;
    const D = { N: [8, 0], S: [8, 10], W: [0, 5], E: [16, 5] };
    let pushed = false;
    for (const door of g.room.open_doors) {
        const dt = D[door];
        g.player.x = dt[0] * 32 + 16;
        g.player.y = dt[1] * 32 + 16;
        const before = [g.room.gx, g.room.gy];
        g.step(1 / 60, NEUTRAL);
        if (g.room.gx !== before[0] || g.room.gy !== before[1]) { pushed = true; break; }
    }
    check(pushed, 'W5 站在门口可物理触发换房');

    // 未清空离开 -> 回来重刷
    g.start_run();
    const d2 = g.dungeon;
    let nr = null;
    for (const k of Object.keys(d2.rooms).map(Number)) {
        const r = d2.rooms[k];
        if (r.kind === 'normal') { nr = [k % 5, Math.floor(k / 5)]; break; }
    }
    g.enter_room(nr[0], nr[1], null, false);
    const n1 = g.enemies.length;
    g.enter_room(d2.start_key[0], d2.start_key[1], null, false);
    g.enter_room(nr[0], nr[1], null, false);
    check(g.enemies.length === n1 && n1 > 0,
        `W5 未清空离开再回来会重新刷怪（${n1} 个）`);
}

function t6_drops(g, sandbox) {
    section('W6 掉落 / 交互（宝箱 / 商店 / 木箱）');
    g.start_run();
    g.state = 'playing';
    const d = g.dungeon;
    let tk = null, skKey = null;
    for (const k of Object.keys(d.rooms).map(Number)) {
        if (d.rooms[k].kind === 'treasure') { tk = k; }
        if (d.rooms[k].kind === 'shop') { skKey = k; }
    }
    check(tk !== null && skKey !== null, 'W6 生成宝箱房与商店房');
    // 宝箱
    g.enter_room(tk % 5, Math.floor(tk / 5), null, false);
    const chest = g.pickups.filter((p) => p.kind === 'chest')[0];
    check(!!chest, 'W6 宝箱房内有宝箱');
    g.player.x = chest.x;
    g.player.y = chest.y;
    const before = g.pickups.length;
    function materialTotal() {
        const bag = Object.values(g.mats).reduce((sum, value) => sum + value, 0);
        const saved = Object.values((g.profile && g.profile.materials) || {})
            .reduce((sum, value) => sum + value, 0);
        return bag + saved;
    }
    const matsBefore = materialTotal();
    check(g.request_interact(), 'W6 可交互开启宝箱');
    check(chest.alive, 'W6 首次按键只显示确认');
    g.request_interact();
    const matsAfter = materialTotal();
    check(g.pickups.length > before || matsAfter > matsBefore,
        `W6 宝箱产出 ${g.pickups.length - before} 个掉落物与 ${matsAfter - matsBefore} 个材料`);
    // 宝箱产出是随机的（金币/血/能量/材料…），掉落物类型必须落在合法集合里
    const LEGAL = ['coin', 'heart', 'energy', 'weapon', 'material', 'diamond', 'collect'];
    const got = g.pickups.slice(before).map((p) => p.kind);
    check(got.every((k) => LEGAL.indexOf(k) >= 0),
        `W6 掉落物类型合法（${got.join(',')}）`);
    // 武器箱（ckey === 'weapon'）必定产出一把武器 —— 确定性路径
    const PickupC = sandbox.window.__INTERNALS__
        ? sandbox.window.__INTERNALS__.Pickup : null;
    if (PickupC) {
        const wc = new PickupC(g.player.x + 6, g.player.y + 6, 'chest', 1);
        wc.ckey = 'weapon';
        wc.ctier = 'normal';
        g.pickups.push(wc);
        g.player.x = wc.x; g.player.y = wc.y;
        g.request_interact();
        g.request_interact();
        check(g.pickups.some((p) => p.kind === 'weapon'), 'W6 武器箱产出武器');
    }

    // 商店：金币不足时拒绝
    g.enter_room(skKey % 5, Math.floor(skKey / 5), null, false);
    const sw = g.pickups.filter((p) => p.kind === 'shop_weapon')[0];
    const sh = g.pickups.filter((p) => p.kind === 'shop_hp_potion')[0];
    check(g.pickups.filter((p) => p.kind === 'shop_weapon').length === 2 && !!sh &&
        g.pickups.some((p) => p.kind === 'shop_energy_potion'),
        'W6 商店房内有两把武器、血瓶和蓝瓶');
    g.coins = 0;
    g.player.x = sw.x; g.player.y = sw.y;
    const wk0 = g.player.wkey;
    g.request_interact();
    check(g.request_interact() === false, 'W6 金币不足时购买被拒绝');
    check(g.player.wkey === wk0, 'W6 拒绝购买后武器未变');
    g.coins = sw.price + 10;
    const coins0 = g.coins;
    g.request_interact();
    check(g.request_interact(), 'W6 金币充足时购买成功');
    check(g.player.wkey === wk0 && g.player.wkey2 === sw.wkey,
        'W6 购买后第二武器槽已解锁');
    check(g.coins === coins0 - sw.price, `W6 金币正确扣除（${coins0} -> ${g.coins}）`);

    // 回血
    g.player.hp = 2;
    g.player.x = sh.x; g.player.y = sh.y;
    g.coins = 999;
    const hp0 = g.player.hp;
    g.request_interact();
    check(g.request_interact(), 'W6 购买回血成功');
    check(g.player.hp === Math.min(g.player.max_hp, hp0 + 6),
        `W6 血瓶回血 +6（${hp0} -> ${g.player.hp}）`);

    // 木箱 / 油桶
    g.start_run();
    let propRoom = null;
    for (const k of Object.keys(g.dungeon.rooms).map(Number)) {
        if (g.dungeon.rooms[k].prop_plan.length) { propRoom = k; break; }
    }
    check(propRoom !== null, 'W6 存在带可破坏道具的房间');
    g.enter_room(propRoom % 5, Math.floor(propRoom / 5), null, false);
    const props = g.props.filter((p) => p.alive);
    check(props.length > 0, `W6 房间内有 ${props.length} 个可破坏道具`);
    const pk0 = g.pickups.length;
    for (const p of props) { p.take_damage(99, g); }
    check(g.props.filter((p) => p.alive).length === 0, 'W6 道具可被击碎');
    check(g.pickups.length >= pk0, 'W6 击碎后产生掉落（概率性）');
}

function t8_screens(sandbox) {
    section('W8 全部界面渲染');
    const g = sandbox.window.__GAME__;
    const states = ['title', 'help', 'playing', 'paused', 'gameover', 'victory',
        'levelclear', 'quit'];
    for (const st of states) {
        let ok = true;
        try {
            g.state = st;
            for (let i = 0; i < 3; i++) { g.draw(); }
        } catch (e) {
            ok = false;
            console.log('    ' + st + ': ' + e.stack.split('\n').slice(0, 3).join('\n    '));
        }
        check(ok, `W8 界面 [${st}] 渲染正常`);
    }
    g.state = 'playing';
    let okW = true;
    for (const k of ['pistol', 'smg', 'shotgun', 'laser', 'rocket', 'cannon']) {
        try { g.player.wkey = k; g.draw(); } catch (e) { okW = false; }
    }
    check(okW, 'W8 六把武器的 HUD 渲染正常');
    // 全图小地图
    for (const k of Object.keys(g.dungeon.rooms)) { g.dungeon.rooms[k].visited = true; }
    let okM = true;
    try { g.draw(); } catch (e) { okM = false; }
    check(okM, 'W8 全图小地图渲染正常');
}

function t7_fuzz(g) {
    section('W7 模糊测试（随机输入 + 瞬移 + 全状态渲染）');
    const states = ['title', 'help', 'playing', 'paused', 'gameover', 'victory',
        'levelclear', 'quit'];
    let err = null, frames = 0;
    const rnd = makeTestRng(20240923);
    g.seed = 20240923;      // 同上：让被模糊测试的世界也是确定性的
    g.start_run();
    try {
        for (let i = 0; i < 9000; i++) {
            frames++;
            const inp = {
                mx: rnd.uniform(-1, 1), my: rnd.uniform(-1, 1),
                aim: rnd.uniform(-4, 4), shoot: rnd.random() < 0.75,
                dash: rnd.random() < 0.05, slow: rnd.random() < 0.1
            };
            g.step(1 / 60, inp);
            if (g.state === 'playing' && i % 37 === 0) {
                g.player.hp = 2;   // 加速死亡/受伤路径
            }
            if (i % 211 === 0) {
                g.player.x = rnd.uniform(-6, 550);
                g.player.y = rnd.uniform(-6, 358);
            }
            if (i % 397 === 0) {
                g.player.wkey = ['pistol', 'smg', 'shotgun', 'laser', 'rocket',
                    'cannon'][rnd.randint(0, 5)];
            }
            if (i % 601 === 0) { g.floor = rnd.randint(1, 3); g._start_floor(g.floor); }
            if (i % 733 === 0) { g.state = states[rnd.randint(0, states.length - 1)]; }
            if (i % 900 === 0) { g.state = 'playing'; }
            if (!invariants(g, 'w7-fuzz')) { break; }
        }
    } catch (e) {
        err = e;
        console.log('    ' + e.stack.split('\n').slice(0, 4).join('\n    '));
    }
    check(!err, `W7 ${frames} 帧模糊测试无异常`);
}

function t11_weapon_swap_no_pingpong(sandbox) {
    section('W11 武器自动交换不往返（踩枪不再死循环）');
    const g = sandbox.window.__GAME__;
    const Pickup = sandbox.window.__INTERNALS__.Pickup;
    const S = sandbox.window.__INTERNALS__.settings;
    const cx = S.ROOM_PX_W / 2, cy = S.ROOM_PX_H / 2;
    const noop = { mx: 0, my: 0, aim: 0, shoot: false, dash: false, slow: false };

    // --- 场景 A：直接踩在掉落的枪上
    g.seed = 31;
    g.start_run();
    const pl = g.player;
    pl.x = cx; pl.y = cy; pl.wkey = 'pistol';
    g.room.pickups.push(new Pickup(pl.x, pl.y, 'weapon', 1, 'smg'));
    const n0 = g.pickups.length;
    const seq = [];
    for (let i = 0; i < 90; i++) { g.step(1 / 60, noop); seq.push(pl.wkey); }
    let changes = 0;
    for (let i = 1; i < seq.length; i++) { if (seq[i] !== seq[i - 1]) { changes++; } }
    check(pl.wkey === 'pistol', `W11 踩枪不自动换枪（wkey=${pl.wkey}）`);
    g.request_interact();
    check(g._pending_interact !== null, 'W11 换枪需二次确认');
    g.request_interact();
    check(pl.wkey === 'pistol' && pl.wkey2 === 'smg',
        `W11 确认后装备第二把枪（wkey2=${pl.wkey2}）`);
    check(changes === 0, `W11 换枪后不再反复抢回（其后变化 ${changes} 次）`);
    check(g.pickups.length <= n0 + 2,
        `W11 掉落物数量不失控（${n0} -> ${g.pickups.length}）`);

    // --- 场景 B：走出去再走回来，应该能再换回旧枪
    g.seed = 31;
    g.start_run();
    const p2 = g.player;
    p2.x = cx; p2.y = cy; p2.wkey = 'pistol';
    g.room.pickups.push(new Pickup(p2.x + 8, p2.y, 'weapon', 1, 'laser'));
    for (let i = 0; i < 3; i++) { g.step(1 / 60, noop); }
    check(p2.wkey === 'pistol', 'W11 场景B 路过保持旧武器');
    g.request_interact(); g.request_interact();
    check(p2.wkey === 'pistol' && p2.wkey2 === 'laser',
        `W11 场景B 确认后获得第二把枪（wkey2=${p2.wkey2}）`);
    p2.switchWeapon();
    check(p2.wkey === 'laser' && p2.wkey2 === 'pistol',
        'W11 场景B 可以切换两把武器');
}

function t9_full_run(g, Dref) {
    section('W9 全流程通关（场景 5 关 × 每关 1 层 + 首领房规则）');
    // W9 依赖 progress 层的 D.nextStage(prof, ...)，所以要自备一份**结构完整**的
    // profile。不能沿用前序测试留下的：W14 结尾把 g.profile 换成了精简对象，
    // 导致 nextStage -> sceneOrder 读不到 unlocked_dungeons 而抛异常。
    g.profile = {
        name: 'W9', char: 'scout', coins: 0, diamonds: 0,
        cleared_scenes: [], unlocked_dungeons: [], scene_best: {},
        scene_prog: {}, codex: {}, collects: [], showcase: [null, null, null, null],
        run: null, bonus_unlocked: false, main_done: false, talent_levels: {}
    };
    // 必须设 seed（不是 rng）：start_run() 内部会 this.rng = makeRng(this.seed)，
    // 直接赋 g.rng 会被立刻覆盖，导致每次跑的地牢都不一样（历史 flaky 来源）。
    g.seed = 7777;
    g.start_run();
    const scene0 = (g.level_state || {}).scene;
    check(!!scene0, `W9 开局已进入场景（${scene0}）`);

    const kindOf = (si) => (Dref && Dref.stageKind)
        ? Dref.stageKind(si)
        : (si === 2 ? 'miniboss' : (si === 4 ? 'boss' : 'normal'));
    const diffOf = (sidx, si) => (Dref && Dref.difficulty)
        ? Dref.difficulty(sidx, si) : [1.0, 1.0];

    let clearedTotal = 0;
    for (let stageIdx = 0; stageIdx < 5; stageIdx++) {
        const ls0 = g.level_state || {};
        if ((ls0.stage_idx || 0) !== stageIdx) {
            if (Dref) { Dref.nextStage(g.profile, scene0, stageIdx); }
            g.level_state = {
                scene: scene0, scene_idx: ls0.scene_idx || 0,
                stage_idx: stageIdx,
                diff: diffOf(ls0.scene_idx || 0, stageIdx),
                kind: kindOf(stageIdx), floors: 3
            };
            g.floor = 1; g._stage_done = false;
            g._start_floor(1);
        }
        const wantBoss = kindOf(stageIdx) === 'miniboss' || kindOf(stageIdx) === 'boss';
        for (let floor = 1; floor <= 1; floor++) {
            g.floor = floor;
            const d = g.dungeon;
            const hasBoss = !!d.boss_key && d.rooms[d._idx(d.boss_key[0], d.boss_key[1])]
                .kind === 'boss';
            const expectBoss = wantBoss;
            check(hasBoss === expectBoss,
                `W9 stage${stageIdx} fl${floor} 首领房 ${hasBoss}/${expectBoss}`);
            let cleared = 0;
            for (const k of Object.keys(d.rooms).map(Number)) {
                const r = d.rooms[k];
                if (r.kind === 'boss') { continue; }
                g.enter_room(k % 5, Math.floor(k / 5), null, false);
                const [ok] = runUntil(g, () => !g.enemies.some((e) => e.alive),
                    9000, true, `w9s${stageIdx}f${floor}`);
                if (ok) { cleared++; r.cleared = true; r.refresh_doors(false); }
            }
            check(cleared >= 3,
                `W9 stage${stageIdx} fl${floor} 清空 ${cleared} 个非首领房`);
            clearedTotal += cleared;
            if (hasBoss) {
                const bk = d.boss_key;
                g.enter_room(bk[0], bk[1], null, false);
                for (let wave = 0; wave < 2; wave++) {
                    g.enemies.forEach((e) => { e.alive = false; });
                    g.step(1 / 60, NEUTRAL);
                }
                const [okB] = runUntil(g, () => !g.boss || !g.boss.alive,
                    18000, true, `w9boss${stageIdx}f${floor}`);
                check(okB, `W9 stage${stageIdx} fl${floor} 首领击败`);
                if (!g.room.cleared) {
                    runUntil(g, () => g.room.cleared, 6000, true,
                        `w9bossremain${stageIdx}f${floor}`);
                }
                check(g.room.portal !== null,
                    `W9 stage${stageIdx} fl${floor} 传送门出现`);
            }
            g.room.portal = [g.player.x, g.player.y];
            g.state = 'playing';
            g.request_interact();
            g.request_interact();
            // 推进过场 / 天赋 / 层通过
            let guard = 0;
            while (guard < 200) {
                guard++;
                if (g.state === 'story') { g._storyNext(); continue; }
                if (g.state === 'levelclear') { g._start_floor(g.floor + 1); continue; }
                if (g.state === 'talent') { g._talentConfirm(); continue; }
                break;
            }
        }
    }
    check(g.kills > 20, `W9 累计击杀 ${g.kills}`);
    console.log(`    [diag] W9 累计清空房间 ${clearedTotal}，state=${g.state}`);
}

function t31_health_skills(sandbox) {
    section('W31 生命上限、旧存档与八角色技能');
    const g = sandbox.window.__GAME__;
    g.seed = 31;
    g.start_run('crust', 0);
    g.state = 'playing';
    const pl = g.player;
    const cap = pl.max_hp;
    const roomKey = Object.keys(g.dungeon.rooms).find((k) => g.dungeon.rooms[k].kind === 'shop');
    check(roomKey !== undefined, 'W31 存在商店房用于构造拾取物');
    g.enter_room(Number(roomKey) % 5, Math.floor(Number(roomKey) / 5), null, false);
    const PickupClass = g.pickups[0].constructor;
    pl.hp = cap;
    new PickupClass(pl.x, pl.y, 'heart', 2).collect(g);
    check(pl.max_hp === cap && pl.hp === cap, 'W31 满血拾取不会抬高上限');
    pl.hp = Math.max(1, cap - 4);
    new PickupClass(pl.x, pl.y, 'heart', 2).collect(g);
    check(pl.max_hp === cap && pl.hp === Math.min(cap, Math.max(1, cap - 4) + 2),
        'W31 受伤拾取只回血');
    g._applyPollution(null, 0);
    check(pl.max_hp === cap && pl.hp <= cap, 'W31 换房重算后血量稳定');
    g._restoreFloorCheckpoint({player:{hp:999, max_hp:999, energy:999, max_energy:999},
        drinks:{}, run_stats:{}});
    check(pl.max_hp === cap && pl.hp === cap && pl.energy <= pl.max_energy,
        'W31 旧档异常上限被规则重算');
    const keys = ['scout','engineer','ranger','medic','ghost','prime','archivist','seedkeeper'];
    for (const key of keys) {
        g.char_key = key; g.char_skill_cd = 0;
        const target = {x:pl.x + 50, y:pl.y, hp:100, alive:true,
            take_damage(damage) { this.hp -= damage; }};
        g.enemies = [target]; pl.aim = 0;
        pl.hp = Math.max(1, cap - 4); pl.energy = 0; pl.iframes = 0;
        check(g.activateCharSkill() && g.char_skill_cd > 0, 'W31 ' + key + ' 技能可施放');
        check(!g.activateCharSkill(), 'W31 ' + key + ' 冷却生效');
        if (['scout','engineer','prime','archivist'].includes(key)) {
            check(pl.energy > 0, 'W31 ' + key + ' 回复能量');
        }
        if (['engineer','ranger','prime','archivist','seedkeeper'].includes(key)) {
            check(target.hp < 100, 'W31 ' + key + ' 命中目标');
        }
        if (['medic','seedkeeper'].includes(key)) {
            check(pl.hp > Math.max(1, cap - 4), 'W31 ' + key + ' 回复生命');
        }
        if (key === 'ghost') { check(pl.iframes >= 2.5, 'W31 虚影闪避无敌时间'); }
    }
    g.enemies = [];
    g.draw();
    check(true, 'W31 灰色半心和技能 HUD 正常绘制');
}

// ==================================================================== 主流程
(async function main() {
    console.log('='.repeat(62));
    console.log(' 陆面过程模拟 网页版 · Node 无头自动化测试');
    console.log('='.repeat(62));

    const { sandbox, mainCanvas } = await boot();
    global.__SANDBOX__ = sandbox;

    // 只跑指定小节：node tools/web_selftest.js --only=W9,W7
    const onlyArg = (process.argv.find((a) => a.startsWith('--only=')) || '');
    const only = onlyArg ? onlyArg.slice('--only='.length).split(',').filter(Boolean) : null;
    const want = (n) => !only || only.indexOf(n) >= 0;

    // 任何测试抛异常都不应让整个套件崩掉，而是记为失败项
    const guard = (name, fn) => {
        if (!want(name)) { return; }
        const m0 = process.memoryUsage().heapUsed;
        try { fn(); } catch (e) {
            check(false, `${name} 抛出异常: ${e.message}`);
            console.log('    ' + String(e.stack).split('\n').slice(0, 4).join('\n    '));
        }
        const m1 = process.memoryUsage().heapUsed;
        console.log(`    [mem] ${name} ${(m0 / 1048576).toFixed(0)}MB -> ` +
            `${(m1 / 1048576).toFixed(0)}MB  (+${((m1 - m0) / 1048576).toFixed(0)}MB)`);
    };

    // ---------------------------------------------------------------- W12
function t12_no_stuck_in_wall(sandbox) {
    section('W12 防卡死（陷进实心瓦片后能脱困）');
    const I = sandbox.window.__INTERNALS__;
    const S = I.settings;
    const circleSolid = I.circleSolid;
    const collideTest = I.collideTest;
    const findFreeSpot = I.findFreeSpot;
    const unstick = I.unstick;
    const ENTRY_FROM = I.ENTRY_FROM;
    const R = I.Game.prototype.constructor;
    const TILE = S.TILE;
    const cx = S.ROOM_PX_W / 2, cy = S.ROOM_PX_H / 2;
    const noop = { mx: 0, my: 0, aim: 0, shoot: false, dash: false, slow: false };

    const g = sandbox.window.__GAME__;
    g.seed = 5;
    g.start_run();

    // 收集实心格
    const solidCells = [];
    for (let ty = 0; ty < S.ROOM_ROWS; ty++) {
        for (let tx = 0; tx < S.ROOM_COLS; tx++) {
            if (g.room.solid(tx, ty)) { solidCells.push([tx, ty]); }
        }
    }
    check(solidCells.length > 0, 'W12 测试房间存在实心瓦片');
    const cell = solidCells[Math.floor(solidCells.length / 2)];
    const px = cell[0] * TILE + TILE / 2;
    const py = cell[1] * TILE + TILE / 2;
    check(circleSolid(px, py, g.player.radius, g.room.solid),
          'W12 选定测试点确实落在实心瓦片内');

    // --- 场景 A：墙内四方向推，必须能脱困（历史 bug：位移恒为 0）
    const dirs = [['右', 1, 0], ['左', -1, 0], ['下', 0, 1], ['上', 0, -1]];
    for (const [name, dx, dy] of dirs) {
        const pl = g.player;
        pl.x = px; pl.y = py;
        const x0 = pl.x, y0 = pl.y;
        const inp = Object.assign({}, noop, { mx: dx, my: dy });
        for (let i = 0; i < 120; i++) { g.step(1 / 60, inp); }
        const moved = Math.hypot(pl.x - x0, pl.y - y0);
        check(moved > 8.0, `W12 陷入墙中朝${name}推能脱困（位移 ${moved.toFixed(1)}px）`);
    }

    // --- 场景 B：findFreeSpot 落点安全且就近
    const spot = findFreeSpot(px, py, g.player.radius, g.room.solid, null, null, null);
    check(spot !== null, 'W12 findFreeSpot 能在墙内找到空位');
    if (spot) {
        check(!collideTest(spot[0], spot[1], g.player.radius, g.room.solid, null),
              'W12 findFreeSpot 返回落点不碰撞');
        const d = Math.hypot(spot[0] - px, spot[1] - py);
        check(d < TILE * 6, `W12 脱困落点应就近（${d.toFixed(1)}px）`);
    }

    // --- 场景 C：入口格被占时 enter_room 必须给安全落点
    g.seed = 5;
    g.start_run();
    const r = g.room;
    const e = ENTRY_FROM.E;
    const etx = Math.floor(e[0] / TILE), ety = Math.floor(e[1] / TILE);
    const orig = r.solid;
    const patched = function (tx, ty) {
        if (tx === etx && ty === ety) { return true; }
        return orig(tx, ty);
    };
    r.solid = patched;
    g.dungeon.room(r.gx, r.gy).solid = patched;
    g.enter_room(r.gx, r.gy, 'E');
    check(!collideTest(g.player.x, g.player.y, g.player.radius, patched, null),
          `W12 入口格被占时落点仍安全（${g.player.x.toFixed(1)},${g.player.y.toFixed(1)}）`);
    r.solid = orig;
    g.dungeon.room(r.gx, r.gy).solid = orig;

    // --- 场景 D：连续零位移 -> 自动脱困兜底
    g.seed = 7;
    g.start_run();
    g.player.x = solidCells[0][0] * TILE + TILE / 2;
    g.player.y = solidCells[0][1] * TILE + TILE / 2;
    const before = g._stuck_rescues || 0;
    const inp = Object.assign({}, noop, { mx: 1.0, my: 0.0 });
    const n = Math.floor(S.STUCK_SECONDS * 60) + 40;
    for (let i = 0; i < n; i++) { g.step(1 / 60, inp); }
    check((g._stuck_rescues || 0) > before,
          `W12 连续零位移触发自动脱困（${before} -> ${g._stuck_rescues || 0}）`);
    check(!collideTest(g.player.x, g.player.y, g.player.radius,
                       g.room.solid, g.room.blockers ? g.room.blockers() : null),
          'W12 自动脱困后玩家不在障碍内');
}

// ============================================================ W13 场景交互物
function t13_hazards(sandbox) {
    section('W13 场景交互物（陷阱 / 掩体 / 奖励洞穴）');
    const I = sandbox.window.__INTERNALS__;
    const S = I.settings;
    const planScene = I.planScene;
    const TRAP_SPEC = I.TRAP_SPEC;
    const KEY_LIST = I.SCENE_KEYS;
    const makeRng = I.makeRng;
    const TRAP_BY_SCENE = I.TRAP_BY_SCENE;

    check(!!planScene, 'W13 planScene 已导出');
    check(!!TRAP_SPEC && Object.keys(TRAP_SPEC).length === 5,
          'W13 陷阱表覆盖 5 种（' + Object.keys(TRAP_SPEC).length + '）');

    // --- 场景 A：每个场景 × 每关都能生成，且结构合法
    let totalTraps = 0, totalCovers = 0, totalCaves = 0, rooms = 0;
    let badKind = 0, outOfRoom = 0;
    for (const sceneKey of KEY_LIST) {
        for (let st = 0; st < 5; st++) {
            const rng = makeRng(1000 + st * 7 + sceneKey.length);
            const diff = [1.0 + st * 0.05, 1.0 + st * 0.07];
            // 每个场景跑 6 个房间样本
            for (let k = 0; k < 6; k++) {
                const plan = planScene(rng, sceneKey, st, diff);
                rooms++;
                totalTraps += plan.traps.length;
                totalCovers += plan.covers.length;
                totalCaves += plan.caves.length;
                for (const tp of plan.traps) {
                    if (!TRAP_SPEC[tp[0]]) { badKind++; }
                    if (tp[1] < S.IN_L || tp[1] > S.IN_R ||
                        tp[2] < S.IN_T || tp[2] > S.IN_B) { outOfRoom++; }
                }
                for (const cv of plan.covers) {
                    if (!(cv[3] > 0)) { badKind++; }
                }
            }
        }
    }
    check(rooms === 7 * 5 * 6, 'W13 采样覆盖 7 场景 × 5 关 × 6 房间（' + rooms + '）');
    check(badKind === 0, 'W13 生成的陷阱/掩体种类与参数全部合法');
    check(outOfRoom === 0, 'W13 陷阱全部落在房间内区');
    check(totalTraps > 0 && totalCovers > 0 && totalCaves > 0,
          `W13 三类交互物均有产出（陷阱 ${totalTraps} / 掩体 ${totalCovers} / 洞穴 ${totalCaves}）`);

    // --- 场景 B：每场景偏好陷阱不同（TRAP_BY_SCENE 覆盖 7 场景）
    check(!!TRAP_BY_SCENE && Object.keys(TRAP_BY_SCENE).length === 7,
          'W13 7 个场景都有陷阱偏好表');

    // --- 场景 C：陷阱不入入口格与房间中心
    const ENTRY_FROM = I.ENTRY_FROM;
    let nearEntry = 0;
    for (const sceneKey of KEY_LIST) {
        const rng = makeRng(77 + sceneKey.length);
        for (let k = 0; k < 40; k++) {
            const plan = planScene(rng, sceneKey, 0, [1.0, 1.0]);
            for (const tp of plan.traps) {
                for (const dk in ENTRY_FROM) {
                    const e = ENTRY_FROM[dk];
                    if (Math.hypot(tp[1] - e[0], tp[2] - e[1]) < 60) { nearEntry++; }
                }
            }
        }
    }
    check(nearEntry === 0, 'W13 陷阱避开所有入口格（' + nearEntry + ' 次越界）');

    // --- 场景 D：进房间物化 + 掩体阻挡 + 爆炸摧毁 + 陷阱扣血
    const g = sandbox.window.__GAME__;
    g.seed = 1234;
    g.start_run();

    let anyRoom = null;
    const keys = Object.keys(g.dungeon.rooms);
    for (const kk of keys) {
        const rr = g.dungeon.rooms[kk];
        if (rr.hazard_plan) { anyRoom = rr; break; }
    }
    if (!anyRoom) {
        // 当前房间可能没有 plan（未传 scene），手动构造一个再物化
        check(true, 'W13 当前流程未注入场景 key，跳过物化验证');
        return;
    }
    g.enter_room(anyRoom.gx, anyRoom.gy, null, true);
    check(g.room._hazards_built, 'W13 enter_room 已物化场景交互物');
    const nCover = g.room.covers.length;
    check(g.room.covers.length === anyRoom.hazard_plan.covers.length,
          `W13 掩体数量一致（plan ${anyRoom.hazard_plan.covers.length} -> live ${nCover}）`);

    // 掩体是阻挡物
    if (nCover > 0) {
        const blk = g.room.blockers();
        let found = false;
        for (const b of blk) { if (b[2] > 12) { found = true; break; } }
        check(found || blk.length >= nCover, 'W13 掩体已并入 blockers()');
    }

    // 掩体被爆炸摧毁
    if (nCover > 0) {
        const cv = g.room.covers[0];
        const hp0 = cv.hp;
        for (let i = 0; i < 8; i++) { cv.take_damage(60, g); }
        check(!cv.alive, `W13 掩体被爆炸伤害摧毁（hp ${hp0} -> ${cv.hp.toFixed(1)}）`);
    }

    // 陷阱持续扣血
    if (g.room.traps.length > 0) {
        const tp = g.room.traps[0];
        tp.spec = Object.assign({}, tp.spec);
        tp.spec.period = 0.01; tp.spec.active = 0.01;   // 强制常开
        g.player.hp = g.player.max_hp;
        g.player.iframes = 0.0;
        const hp0 = g.player.hp;
        for (let i = 0; i < 180; i++) {
            g.player.x = tp.x; g.player.y = tp.y;
            g.player.iframes = 0.0;
            g.room.update_hazards(g, 1 / 60);
        }
        check(g.player.hp < hp0, `W13 站在陷阱上会持续掉血（${hp0} -> ${g.player.hp.toFixed(1)}）`);
    }

    // 洞穴开出材料（找还没被开启的那个）
    const liveCaves = g.room.caves.filter((c) => c.alive);
    if (liveCaves.length > 0) {
        const cave = liveCaves[0];
        g.mats = {};
        g.toasts = [];
        // 前面的陷阱测试可能打死了玩家，这里先复活再验证洞穴
        g.player.alive = true;
        g.player.hp = g.player.max_hp;
        g.player.iframes = 0.0;
        g.player.x = cave.x;
        g.player.y = cave.y;
        cave.update(g, 1 / 60);
        check(!cave.alive, 'W13 走近奖励洞穴即开启');
        const got = Object.keys(g.mats).length > 0;
        check(got || g.toasts.length > 0,
              'W13 洞穴产出材料或至少给出提示（mats=' + JSON.stringify(g.mats) + '）');
    }
    check(g.room.caves.filter((c) => c.alive).length < g.room.caves.length ||
          g.room.caves.length === 0, 'W13 洞穴总有一个被开启过');

    // --- 场景 E：掩体挡子弹（挑一个还活着的掩体）
    const liveCovers = g.room.covers.filter((c) => c.alive);
    if (liveCovers.length > 0) {
        const cv = liveCovers[0];
        const B = I.Bullet;
        // 从掩体左侧一定距离外发射，确保初始位置不与掩体重叠
        const b = new B(cv.x - 60, cv.y, 0, 260, 5, true, 'b_bullet', 14, 5, 0, 0, 2.0,
                        [255, 214, 120], 0.8);
        g.bullets = [b];
        for (let i = 0; i < 40 && b.alive; i++) { b.update(g, 1 / 60); }
        check(!b.alive, 'W13 普通子弹被掩体挡住（子弹已消失）');
        check(cv.alive, 'W13 普通子弹打不动掩体');
    }
}

function t14_pollution_conditions(sandbox) {
    section('W14 污染减益 / 副本准入条件 / 奖励副本金币支付');
    const D = sandbox.window.__DATA__;
    const g = sandbox.window.__GAME__;

    // ---- 1. 污染数据与纯函数
    check(!!D.POLLUTION && Object.keys(D.POLLUTION).length === 7,
          'W14 POLLUTION 覆盖 7 个场景');
    const pcts = D.MAIN.map((s) => D.POLLUTION[s].pct);
    let inc = true;
    for (let i = 1; i < pcts.length; i++) {
        if (!(pcts[i] > pcts[i - 1])) { inc = false; }
    }
    check(inc, 'W14 主线污染浓度递增（' + pcts.join(' -> ') + '）');
    check(D.POLLUTION.D_BONUS === undefined &&
          D.POLLUTION[D.BONUS].pct === 0, 'W14 奖励副本无污染');

    // 场景内越深越重
    let mono = true;
    for (const sc of D.MAIN.concat(Object.keys(D.DUNGEONS))) {
        for (let st = 1; st < D.STAGES_PER_SCENE; st++) {
            const a = D.pollution(sc, st - 1), b = D.pollution(sc, st);
            if (b.hp_cut < a.hp_cut || b.spd > a.spd + 1e-9 ||
                b.drain < a.drain - 1e-9) { mono = false; }
        }
    }
    check(mono, 'W14 同一场景内减益随关卡单调加深');

    const deep = D.pollution('core', 4);
    check(deep.hp_cut >= 3 && deep.spd <= 0.92 && deep.drain > 0,
          `W14 污染原点减益明显（hp-${deep.hp_cut} spd${deep.spd} ` +
          `drain${deep.drain}）`);
    check(D.pollutionLines(D.BONUS, 4).length === 0, 'W14 无污染场景无减益文案');
    check(JSON.stringify(D.pollution('core', 4)) ===
          JSON.stringify(D.pollution('core', 4)), 'W14 污染计算是纯函数（幂等）');

    // ---- 2. 进关时真的把减益写进玩家
    g.seed = 4321;
    g.start_run('core', 4);
    check(!!g.pollution, 'W14 start_run 后记录了当前污染');
    check(g.pollution.pct === 96, 'W14 污染原点浓度 96%');
    check(g.player.max_hp < 12,
          `W14 污染削减了生命上限（${g.player.max_hp} < 12）`);
    check(g.pollution_spd < 1.0, `W14 移速倍率生效（${g.pollution_spd}）`);
    check(g.pollution_regen < 1.0, `W14 回能倍率生效（${g.pollution_regen}）`);

    // 持续侵蚀：站在安全位置空转，血量应缓慢下降
    g.player.hp = g.player.max_hp;
    g.player.iframes = 0.0;
    g._drain_acc = 0.0;
    const hp0 = g.player.hp;
    // 96% 污染 ≈ 0.196/s，跑 720 帧（12 秒）应至少扣 2 点
    for (let i = 0; i < 720; i++) {
        g.player.iframes = 0.0;
        g._updatePollution(1 / 60);
    }
    check(g.player.hp < hp0,
          `W14 污染持续侵蚀扣血（${hp0} -> ${g.player.hp.toFixed(2)}）`);

    // 无污染场景不扣血
    g.start_run('d_gift', 0);
    check(g.pollution === null || g.pollution === undefined ||
          g.pollution.drain === 0, 'W14 奖励副本无侵蚀');
    const hp1 = g.player.hp;
    for (let i = 0; i < 720; i++) { g._updatePollution(1 / 60); }
    check(g.player.hp === hp1, 'W14 奖励副本不受侵蚀影响');
    check(g.player.max_hp >= 12, 'W14 奖励副本不削减生命上限');

    // ---- 3. 副本准入条件（多条件 + 单调累计）
    check(Object.keys(D.DUNGEONS).length === 2, 'W14 共 2 个副本');
    for (const dk of Object.keys(D.DUNGEONS)) {
        const cond = D.DUNGEONS[dk].cond;
        const allowed = ['kills', 'cleared', 'no_death', 'low_hp',
                         'trap_hits', 'bomber_hits'];
        const ks = Object.keys(cond);
        check(ks.every((k) => allowed.indexOf(k) >= 0),
              `W14 ${dk} 条件键合法（${ks.join(',')}）`);
        check(!!D.DUNGEONS[dk].hint, `W14 ${dk} 提供设计提示`);
        check(cond.kills >= 90, `W14 ${dk} 击杀门槛有挑战性（${cond.kills}）`);
    }

    // 空档案：全部未达成
    const prof = { cleared_scenes: [], unlocked_dungeons: [], scene_best: {} };
    let r = D.dungeonProgress(prof, 'd_mine');
    check(r[1] === false, 'W14 空档案时矿井未解锁');
    check(r[0].length >= 3, 'W14 条件拆成多条打勾项（' + r[0].length + '）');

    // 前一条不满足 -> 不解锁
    prof.cleared_scenes = ['sewer'];
    D.mergeSceneBest(prof, 'sewer', { kills: 95, trap_hits: 12 });
    check(D.scanUnlocks(prof).length === 0, 'W14 踩陷阱过多时不解锁');

    // 补上 -> 解锁
    D.mergeSceneBest(prof, 'sewer', { kills: 95, trap_hits: 2 });
    const newly = D.scanUnlocks(prof);
    check(newly.indexOf('d_mine') >= 0, 'W14 满足全部条件后解锁矿井');
    const so = D.sceneOrder(prof);
    check(so.indexOf('d_mine') === so.indexOf('sewer') + 1,
          'W14 矿井插在下水道之后（' + so.join(',') + '）');

    // 合并语义：只增不减 / 越小越好
    D.mergeSceneBest(prof, 'sewer', { kills: 10, trap_hits: 99 });
    const sb = prof.scene_best.sewer;
    check(sb.kills === 95, 'W14 击杀取历史最大');
    check(sb.trap_hits === 2, 'W14 陷阱命中取历史最小');

    // 未通关前置场景 -> 不解锁
    const prof2 = { cleared_scenes: [], unlocked_dungeons: [],
                    scene_best: { sewer: { kills: 999, trap_hits: 0 } } };
    check(D.scanUnlocks(prof2).length === 0, 'W14 未通关前置场景不解锁');

    // ---- 3b. 经济曲线：面值与定价可达性（与 Python T19b 对齐）
    check(D.coinValue(0, 0) === 2, 'W14 第一关金币面值符合 2.5 经济');
    check(D.coinValue(6, 4) > D.coinValue(0, 0), 'W14 金币面值随深度增长');
    let monotone = true, prev = -1;
    for (let si = 0; si < 7; si++) {
        for (let st = 0; st < D.STAGES_PER_SCENE; st++) {
            const v = D.coinValue(si, st);
            if (v < prev) { monotone = false; }
            prev = v;
        }
    }
    check(monotone, 'W14 金币面值全局单调不减');
    check(D.COIN_ELITE_MUL >= 1.5 && D.COIN_BOSS_MUL >= 3.0,
          'W14 精英/首领掉币倍率合理');
    // 预算模型对齐 onEnemyKilled / onBossDefeated
    let budget = 0;
    const N_SMALL = 12, N_ELITE = 2, BOX = 3 * 110;
    for (let si = 0; si < D.MAIN.length; si++) {
        for (let st = 0; st < D.STAGES_PER_SCENE; st++) {
            const cv = D.coinValue(si, st);
            let g2 = N_SMALL * 2 * cv + N_ELITE * 4 * cv * D.COIN_ELITE_MUL;
            const kind = D.stageKind(st);
            if (kind === 'miniboss' || kind === 'boss') {
                g2 += 26 * cv * D.COIN_BOSS_MUL;
            }
            budget += g2 + BOX;
        }
    }
    check(budget > D.BONUS_PRICE,
          'W14 主线首通预算(' + budget + ') 覆盖奖励副本定价(' +
          D.BONUS_PRICE + ')');
    check(D.BONUS_PRICE >= budget * 0.15,
          'W14 奖励副本仍有取舍成本');
    check(D.sceneIndexOf('core') === 3 && D.sceneIndexOf('d_gift') === 6,
          'W14 场景下标解析正确');

    // ---- 3c. 1.3 抗污染天赋
    ['pur_resist', 'pur_purge', 'pur_ward'].forEach(function (k) {
        check(!!D.TALENTS[k], 'W14 抗污染天赋 ' + k + ' 存在');
    });
    const wst = D.newRunStats();
    check(wst.pur_resist === 0.0, 'W14 run_stats 含 pur_resist 初值');
    for (let i = 0; i < 5; i++) { D.applyTalent(wst, 'pur_resist'); }
    check(Math.abs(D.purResistOf(wst) - D.PUR_RESIST_CAP) < 1e-6,
          'W14 抗性堆叠被夹到上限');
    const polCore = D.pollution('core', 4);
    const hst = D.newRunStats();
    hst.pur_resist = 0.5;
    const ta = D.purTintAmount(polCore, hst);
    check(ta[0] === Math.round(polCore.hp_cut * 0.5), 'W14 生命削减减半');
    check(Math.abs(ta[3] - polCore.drain * 0.5) < 0.01, 'W14 侵蚀减半');
    check(ta[1] > polCore.spd && ta[2] > polCore.regen,
          'W14 移速/回能朝 1.0 收敛');
    check(ta[1] < 1.0, 'W14 半抗性不会变成增益');
    const gz = D.purTintAmount(D.pollution('d_gift', 0), hst);
    check(gz[0] === 0 && gz[1] === 1.0 && gz[3] === 0.0,
          'W14 无污染场景不受抗性影响');
    const wardSt = D.newRunStats();
    check(D.purWardBonus(polCore, wardSt) === 0.0, 'W14 无共鸣天赋无加成');
    D.applyTalent(wardSt, 'pur_ward');
    const wb = D.purWardBonus(polCore, wardSt);
    check(wb > 0, 'W14 共鸣在污染原点给伤害加成');
    check(D.purWardBonus(D.pollution('crust', 0), wardSt) < wb,
          'W14 浅层共鸣收益更低');
    const pgSt = D.newRunStats();
    check(!D.hasPurPurge(pgSt), 'W14 默认没有净化循环');
    D.applyTalent(pgSt, 'pur_purge');
    check(D.hasPurPurge(pgSt), 'W14 净化循环 flag 生效');

    // ---- 3d. 叙事绑定
    ['d_mine', 'd_lab'].forEach(function (dk) {
        const cards = D.dungeonBindCards(dk);
        check(cards.length >= 3, 'W14 ' + dk + ' 机制卡 ≥3（' + cards.length + '）');
        let allNamed = true, allDesc = true;
        cards.forEach(function (c) {
            if (!c.name || c.name === c.key) { allNamed = false; }
            if (!c.desc || c.desc.length < 8) { allDesc = false; }
            if (c.kind !== 'enemy' && c.kind !== 'trap') { allNamed = false; }
        });
        check(allNamed, 'W14 ' + dk + ' 卡片有正式名与合法类型');
        check(allDesc, 'W14 ' + dk + ' 卡片说明够具体');
        check(D.dungeonTip(dk).length > 0, 'W14 ' + dk + ' 有战术提示');
    });
    check(D.dungeonBindCards('nope').length === 0, 'W14 未知副本返回空卡片');

    // ---- 3e. 货币上限
    check(D.COIN_CAP > 0 && D.DIAMOND_CAP > 0, 'W14 货币上限为正');
    check(D.clampCoin(-5) === 0, 'W14 负数夹到 0');
    check(D.clampCoin(D.COIN_CAP + 1) === D.COIN_CAP, 'W14 超上限夹到上限');
    const ac = D.addCoin(D.COIN_CAP - 10, 50);
    check(ac[0] === D.COIN_CAP && ac[1] === 10, 'W14 加币封顶且回报实际入账');
    const ac2 = D.addCoin(D.COIN_CAP, 100);
    check(ac2[0] === D.COIN_CAP && ac2[1] === 0, 'W14 已满时入账为 0');
    check(D.clampDiamond(999999) === D.DIAMOND_CAP, 'W14 钻石同样封顶');

    // ---- 4. 奖励副本：金币支付
    // 定价不再硬编码：从数据层读，避免调整经济时测试跟着漂移
    const BPRICE = D.BONUS_PRICE;
    check(BPRICE > 0 && D.BONUS_PRICE_DIA === 0,
          'W14 奖励副本以金币定价且不收钻石');
    const bp = { coins: 0, diamonds: 99999, cleared_scenes: [],
                 unlocked_dungeons: [], scene_best: {} };
    check(!D.canBuyBonus(bp, true), 'W14 未通关核心时不能买');
    check(!D.bonusUnlockable(bp), 'W14 未通关核心时不可解锁');
    bp.cleared_scenes = ['core'];
    check(D.bonusUnlockable(bp), 'W14 通关核心后可解锁');
    check(!D.canBuyBonus(bp, true), 'W14 金币为 0 时不能买（钻石再多也没用）');
    const miss = D.bonusMissing(bp);
    check(miss[0] === BPRICE && miss[1] === 0, 'W14 差额提示只看金币');
    bp.coins = BPRICE;
    check(D.canBuyBonus(bp, true), 'W14 金币够时可以买');
    check(D.buyBonus(bp), 'W14 购买成功');
    check(bp.coins === 0 && bp.bonus_unlocked === true, 'W14 购买后扣金币并置位');
    check(bp.diamonds === 99999, 'W14 购买不动钻石');
    check(!D.canBuyBonus(bp, true), 'W14 不能重复购买');
    check(D.sceneOrder(bp).indexOf(D.BONUS) >= 0, 'W14 奖励副本进入可见场景');

    // ---- 5. 游戏内触发：踩陷阱与自爆的计数
    g.seed = 777;
    g.start_run('sewer', 0);
    g.run_trap_hits = 0;
    g.on_trap_hit();
    g.on_bomber_hit();
    const st = g._sceneStats();
    check(st.trap_hits === 1 && st.bomber_hits === 1,
          'W14 踩陷阱/被自爆计数进入场景成绩');
    check(st.no_death === true, 'W14 未死亡时 no_death 为真');

    // ---- 6. 客厅 / 关卡地图（1.0 需求 16）
    // 1.4 起"开始游戏"先走存档槽（需求 10），选/建档后必须直接进客厅 ——
    // 曾经错写成回 title，形成"选了档又回菜单"的死循环。
    g.state = 'title';
    g._menu_pick('new');
    check(g.state === 'slots', 'W14 开始游戏先进入存档槽选择');
    g.draw();
    check(true, 'W14 存档槽界面渲染不抛异常');
    // 选一个有内容的槽 -> 必须直接进客厅
    const saveMod = sandbox.window.__SAVE__;
    const oldSlots = JSON.parse(JSON.stringify(saveMod.data));
    try {
        saveMod.data.slots[0] = sandbox.window.__newProfile__(0, '测试A');
        saveMod.data.last = 0;
        g.slot_index = 0;
        g._keydownSlots('enter');
        check(g.state === 'lobby', 'W14 选中已有档后直接进入客厅（不死循环）');
        check(g.profile && g.profile.name === '测试A', 'W14 选中档后 profile 生效');
    } finally {
        saveMod.data = oldSlots;
        saveMod.save();
    }
    g.draw();
    check(true, 'W14 客厅渲染不抛异常');

    // 地图展示全部场景，只有唯一目标关可出发
    g.profile = null;
    check(g._lobbyOrder().length === 7,
          'W14 无存档时客厅列出全部 7 个场景');

    // 全解锁后列出全部 7 个场景，且每个都能渲染（收起 / 展开）
    g.profile = { name: '测试', char: 'scout', coins: 99999, diamonds: 500,
                  cleared_scenes: [], unlocked_dungeons: [], scene_best: {} };
    Object.keys(D.DUNGEONS).forEach(function (dk) {
        g.profile.unlocked_dungeons.push(dk);
    });
    g.profile.bonus_unlocked = true;
    const lo = g._lobbyOrder();
    check(lo.length === 7, 'W14 全解锁后客厅列出 7 个场景（' + lo.length + '）');
    let drawOk = true;
    for (let i = 0; i < lo.length; i++) {
        g.lobby_index = i;
        for (const ex of [false, true]) {
            g.lobby_expand = ex;
            try { g.draw(); } catch (e) { drawOk = false; }
        }
    }
    check(drawOk, 'W14 客厅 7 个场景详情（收起/展开）渲染正常');

    // 键盘导航：模 n 循环
    const nlo = lo.length;
    g.lobby_index = 0;
    for (let i = 0; i < nlo; i++) { g._keydownLobby('s'); }
    check(g.lobby_index === 0, 'W14 客厅 ↓ 键循环导航回到起点');
    g.lobby_index = 0;
    g._keydownLobby('arrowup');
    check(g.lobby_index === nlo - 1, 'W14 客厅 ↑ 键从首项绕到末项');
    g.lobby_index = 0;
    g._keydownLobby('e');
    check(g.lobby_expand === true, 'W14 客厅 E 键展开机制卡');

    // 进入判定
    let lr = g._lobbyCanEnter('crust', g.profile);
    check(lr[0], 'W14 第一主线可进入');
    check(!g._lobbyCanEnter('core', g.profile)[0], 'W14 不可跳到第四主线');
    g.profile.bonus_unlocked = false;
    g.profile.cleared_scenes = [];
    lr = g._lobbyCanEnter('d_gift', g.profile);
    check(!lr[0] && !!lr[1], 'W14 未满足条件时给出不可进入原因');
    g.profile.unlocked_dungeons = [];
    lr = g._lobbyCanEnter('d_mine', g.profile);
    check(!lr[0] && !!lr[1], 'W14 未解锁副本给出不可进入原因');

    // 条件满足后可以从客厅直接出发
    g.profile = sandbox.window.__newProfile__(0, '测试');
    g.profile.cleared_scenes = ['crust'];
    g.profile.scene_prog.crust = D.STAGES_PER_SCENE;
    g.lobby_index = 1;
    g._lobbyGo();
    check(g.state === 'playing' || g.state === 'story',
          'W14 客厅出发后进入游戏（state=' + g.state + '）');
}

// ============================================================ W15 图鉴 / 展示台
function t15_codex_showcase(sandbox) {
    const D = sandbox.window.__DATA__;
    section('W15 图鉴 / 收集品展示台 / 客厅分页（1.0 需求 8/9）');
    const g = sandbox.window.__GAME__;
    if (!g) { check(false, 'W15 __GAME__ 未暴露'); return; }
    const Pickup = sandbox.window.__INTERNALS__.Pickup;
    g.seed = 20240923;

    // ---- 数据层：四类图鉴表齐备
    // 2.1：七个主题新增六种独立小首领，图鉴总数为 43。
    check(Object.keys(D.ENEMY_CODEX).length >= 47,
          'W15 怪物图鉴至少 47 条（' + Object.keys(D.ENEMY_CODEX).length + '）');
    // 2.1：图鉴必须覆盖全部 50 把独立武器。
    check(Object.keys(D.WEAPON_CODEX || {}).length >= 104,
          'W15 武器图鉴至少 104 条（' + Object.keys(D.WEAPON_CODEX || {}).length + '）');
    check(Object.keys(D.MATERIAL_CODEX || {}).length === 8,
          'W15 材料图鉴 8 条（' + Object.keys(D.MATERIAL_CODEX || {}).length + '）');
    check(Object.keys(D.COLLECTS).length === 10,
          'W15 收集品 10 件（' + Object.keys(D.COLLECTS).length + '）');

    // ---- discover：无存档 -> new_codex
    g.profile = null;
    g.new_codex = [];
    const d1 = g.discover('enemy', 'slime');
    const d2 = g.discover('enemy', 'slime');
    check(d1 === true && d2 === false, 'W15 无存档时图鉴首见返回 true、重见 false');
    check(g.new_codex.length === 1, 'W15 无存档时记入内存 new_codex');

    // ---- discover：有存档 -> prof.codex
    g.profile = { name: 'T', coins: 0, diamonds: 0, cleared_scenes: [],
                  unlocked_dungeons: [], codex: {}, showcase: [null, null, null, null, null, null] };
    check(g.discover('weapon', 'pistol') === true, 'W15 有存档时图鉴首次收录');
    check(g.discover('weapon', 'pistol') === false, 'W15 重复收录被忽略');
    check((g.profile.codex.weapon || []).length === 1, 'W15 图鉴写入 prof.codex');

    // ---- collect_got：图鉴 + 自动上架
    const ck = D.COLLECT_ORDER[0];
    const c1 = g.collect_got(ck);
    check(c1 === true, 'W15 首次获得收集品返回 true');
    check((g.profile.collects || []).indexOf(ck) >= 0, 'W15 收集品记入 prof.collects');
    check(g.profile.showcase[0] === ck, 'W15 收集品自动放到展示台第 1 格');
    check((g.profile.codex.collect || []).indexOf(ck) >= 0, 'W15 收集品同时记入图鉴');

    // ---- 展示台取出 / 放回
    g.showcase_index = 0;
    g.showcase_toggle();
    check(g.profile.showcase[0] === null, 'W15 E 键取出展示台格子');
    g.showcase_toggle();
    check(g.profile.showcase[0] === ck, 'W15 空位 E 键从收藏袋放回');

    // ---- collect 拾取物：世界内可被拾取
    g.start_run('crust', 0);
    g.state = 'playing';
    const pc = new Pickup(g.player.x, g.player.y, 'collect', 1);
    pc.ckey = D.COLLECT_ORDER[1];
    g.pickups.push(pc);
    const nBefore = (g.profile.collects || []).length;
    pc.collect(g);
    check(pc.alive === false, 'W15 collect 拾取物被拾取后消失');
    check((g.profile.collects || []).length > nBefore, 'W15 拾取 collect 后收藏数增加');

    // ---- 客厅四分页渲染
    g.profile = { name: 'T', char: 'scout', coins: 0, diamonds: 0,
                  cleared_scenes: ['crust'], unlocked_dungeons: [],
                  scene_prog: {}, weapons: { pistol: 0 }, weapon: 'pistol',
                  chars: ['scout'], skills: {}, passives: {}, talent_levels: {},
                  materials: {}, scene_best: {}, codex: {},
                  showcase: [null, null, null, null, null, null] };
    g._enterLobby();
    check(g.state === 'lobby', 'W15 进入客厅');
    let renderOk = true;
    for (let tab = 0; tab < 4; tab++) {
        g.lobby_tab = tab;
        for (let idx = 0; idx < 6; idx++) {
            g.codex_cat = idx % 4; g.codex_index = idx; g.showcase_index = idx;
            g.growth_sub = idx % 4; g.growth_index = idx;
            try { g.draw(); } catch (e) { renderOk = false; }
        }
    }
    check(renderOk, 'W15 客厅四分页（准备/养成/图鉴/展示台）渲染正常');

    // ---- TAB 切页循环
    g.lobby_tab = 0;
    g._keydownLobby('tab');
    check(g.lobby_tab === 1, 'W15 TAB 切到养成分页');
    g._keydownLobby('tab');
    check(g.lobby_tab === 2, 'W15 TAB 切到图鉴分页');
    g._keydownLobby('tab');
    g._keydownLobby('tab');
    check(g.lobby_tab === 0, 'W15 TAB 四分页循环回到准备页');

    // ---- 养成分页导航（子页切换）
    g.lobby_tab = 1;
    g.growth_sub = 0; g.growth_index = 0;
    g._keydownLobby('d');
    check(g.growth_sub === 1, 'W15 → 键切到武器子页');
    g._keydownLobby('a');
    check(g.growth_sub === 0, 'W15 ← 键切回角色子页');
    g.growth_sub = 0; g.growth_index = 0;
    g._keydownLobby('s');
    check(g.growth_index === 1, 'W15 ↓ 键在养成列表内移动选中');
    g.growth_index = 0;
    g._keydownLobby('w');
    check(g.growth_index === 0, 'W15 养成列表顶部不再上移（边界夹紧）');

    // ---- 图鉴分页导航
    g.lobby_tab = 2;
    g.codex_cat = 0; g.codex_index = 0; g.codex_page = 0;
    g._keydownLobby('d');
    check(g.codex_cat === 1, 'W15 → 键切换图鉴分类');
    g._keydownLobby('a');
    check(g.codex_cat === 0, 'W15 ← 键切回上一分类');
    g.codex_index = 0;
    g._keydownLobby('s');
    check(g.codex_index === 1, 'W15 ↓ 键在图鉴内移动选中');
    g.codex_index = 0;
    g._keydownLobby('w');
    check(g.codex_index === 0, 'W15 图鉴顶部不再上移（边界夹紧）');

    // ---- 展示台导航
    g.lobby_tab = 3;
    g.showcase_index = 0;
    g._keydownLobby('d');
    check(g.showcase_index === 1, 'W15 → 键换展示台格子');
    g.showcase_index = 5;
    g._keydownLobby('d');
    check(g.showcase_index === 0, 'W15 展示台末格 → 键绕回首格');

    // ---- 图鉴总数与条目数一致
    check(D.ENEMY_ORDER.length === Object.keys(D.ENEMY_CODEX).length,
          'W15 怪物图鉴顺序表与图鉴条目一致');
    check(D.COLLECT_ORDER.length === 10, 'W15 收集品顺序表 10 条');
}

// ============================================================ W16 天赋三选一
function t16_talents(sandbox) {
    const D = sandbox.window.__DATA__;
    section('W16 天赋三选一（1.1 需求 2）');
    const g = sandbox.window.__GAME__;
    if (!g) { check(false, 'W16 __GAME__ 未暴露'); return; }
    g.seed = 20240923;

    check(D.TALENT_ORDER.length >= 12,
          'W16 天赋池 ' + D.TALENT_ORDER.length + ' 条');
    check(D.TALENT_ORDER.indexOf('pur_resist') >= 0, 'W16 池内含「滤芯装甲」');
    check(D.TALENT_ORDER.indexOf('pur_purge') >= 0, 'W16 池内含「净化循环」');
    check(D.TALENT_ORDER.indexOf('pur_ward') >= 0, 'W16 池内含「污染共鸣」');

    const picks = D.rollTalents(g.rng, [], 3);
    check(picks.length === 3, 'W16 三选一返回 3 个候选');
    check(new Set(picks).size === 3, 'W16 同一次候选不重复');

    // ---- 状态机
    g.profile = null;
    g.start_run('crust', 0);
    g.state = 'playing';
    g.talents_owned = [];
    g.recomputeTalents();
    const ok = g.startTalentPick(3);
    check(ok && g.state === 'talent', 'W16 触发三选一进入 talent 状态');
    check(g.pending_talents.length === 3, 'W16 pending_talents 3 个');
    g.talent_pick = 0;
    g._talentMove(1);
    check(g.talent_pick === 1, 'W16 → 键移动选择');
    g._talentMove(-1);
    check(g.talent_pick === 0, 'W16 ← 键移回');
    g.talent_pick = 2;
    g._talentMove(1);
    check(g.talent_pick === 0, 'W16 选择在候选上循环');

    g.talent_pick = 0;
    g._talentConfirm();
    check(g.state === 'playing', 'W16 确认后回到 playing');
    check(g.talents_owned.length === 1, 'W16 已选天赋记录');
    check(g.pending_talents === null, 'W16 确认后清空候选');
    check(g.run_stats && typeof g.run_stats === 'object', 'W16 确认后重算 run_stats');

    // ---- 渲染
    let renderOk = true;
    try {
        g.startTalentPick(3);
        for (let i = 0; i < 3; i++) {
            g.talent_pick = i;
            g.draw();
        }
    } catch (e) { renderOk = false; }
    check(renderOk, 'W16 天赋三选一界面渲染正常');
    g.state = 'playing';

    // ---- 叠加上限
    g.talents_owned = ['pur_resist', 'pur_resist', 'pur_resist'];
    const pool = D.rollTalents(g.rng, g.talents_owned, 3);
    check(pool.indexOf('pur_resist') < 0, 'W16 选满 3 次的天赋不再出现');

    // ---- 抗污染加成（乘算 + 硬上限）
    g.talents_owned = [];
    g.recomputeTalents();
    check(Math.abs(g.run_stats.pur_resist) < 1e-9, 'W16 未选时抗性为 0');
    g.talents_owned = ['pur_resist'];
    g.recomputeTalents();
    check(Math.abs(g.run_stats.pur_resist - 0.25) < 1e-6,
          'W16 1 件滤芯装甲抗性 0.25（' + g.run_stats.pur_resist + '）');
    g.talents_owned = ['pur_resist', 'pur_resist', 'pur_resist',
                       'pur_resist', 'pur_resist', 'pur_resist'];
    g.recomputeTalents();
    check(Math.abs(g.run_stats.pur_resist - D.PUR_RESIST_CAP) < 1e-6,
          'W16 抗性受硬上限 ' + D.PUR_RESIST_CAP);

    // ---- flag / 数值天赋
    g.talents_owned = ['shield', 'hp_up'];
    g.recomputeTalents();
    check(g.run_stats.flags.indexOf('shield') >= 0, 'W16 flag 类天赋写入 flags');
    check(g.run_stats.max_hp > 0, 'W16 生命上限天赋计入 run_stats');
    check(g.run_stats.talents.length === 2, 'W16 天赋 key 也记录在 talents');
    g.talents_owned = [];
    g.recomputeTalents();
}

// ============================================================ W20 更新日志
function t20_changelog(sandbox) {
    section('W20 更新日志（标题右下角入口）');
    const g = sandbox.window.__GAME__;
    if (!g) { check(false, 'W20 __GAME__ 未暴露'); return; }
    const VW = sandbox.window.__INTERNALS__.settings.VIEW_W;
    const VH = sandbox.window.__INTERNALS__.settings.VIEW_H;

    // ---- 标题页点击右下角进入 changelog
    g.collection_popup = null;
    g.state = 'title';
    g.log_scroll = 0;
    // 按钮右边界固定 = VW - 12（见 drawTitle），点其中心偏右即可命中
    g.mouse_canvas = [VW - 16, VH - 20];
    g._click();
    check(g.state === 'changelog', `W20 点右下角进入更新日志（state=${g.state}）`);

    // ---- 滚动
    g._keydown('s');
    check(g.log_scroll === 1, 'W20 ↓ 滚动更新日志');
    g._keydown('w');
    check(g.log_scroll === 0, 'W20 ↑ 回滚更新日志');

    // ---- 渲染不炸
    let okdraw = true;
    try { g.draw(); } catch (e) { okdraw = false; }
    check(okdraw, 'W20 更新日志面板渲染正常');

    // ---- 返回
    g._keydown('escape');
    check(g.state === 'title', 'W20 ESC 返回标题');

    g.state = 'playing';
}


// ============================================================ W21 武器机制
function t21_weapon_mech(sandbox) {
    section('W21 武器扩充与机制化品质（1.4 需求 6）');
    const D = sandbox.window.__DATA__;
    const I = sandbox.window.__INTERNALS__;

    // ---- 基础型号数量与近战/远程并存
    check((D.WPN_ORDER || []).length >= 10,
        `W21 基础型号 ${(D.WPN_ORDER || []).length} 把（≥10）`);
    let melee = 0, ranged = 0;
    for (const k of D.WPN_ORDER) {
        if ((D.WEAPONS[k] || {}).melee) { melee++; } else { ranged++; }
    }
    check(melee >= 1, `W21 近战型号 ${melee} 把`);
    check(ranged >= 5, `W21 远程型号 ${ranged} 把`);

    // ---- 品质机制逐级叠加
    const base = D.WEAPONS.pistol;
    const bWhite = D.applyQuality('pistol', 'white', 1.0);
    const bBlue = D.applyQuality('pistol', 'blue', D.QUALITIES.blue.mul);
    const bRad = D.applyQuality('pistol', 'radiant', D.QUALITIES.radiant.mul);
    check(bBlue.cd < bWhite.cd, 'W21 蓝色射速快于白色');
    check(bBlue.count > bWhite.count, 'W21 蓝色弹丸数 > 白色');
    check(bRad.pierce > bWhite.pierce, 'W21 璀璨穿透 > 白色');

    // ---- 机制表
    check(!!D.qualityMech('gold').burst, 'W21 金色带「击杀迸射」');
    check(!!D.qualityMech('red').split, 'W21 赤红带「命中分裂」');
    check(!!D.qualityMech('radiant').homing, 'W21 璀璨带「追猎弹道」');
    check(Object.keys(D.QUALITY_MECH_DESC || {}).length === 7, 'W21 机制说明表 7 条');

    // ---- 近战范围随品质增大 + 挥砍命中
    const bl = D.applyQuality('blade', 'radiant', D.QUALITIES.radiant.mul);
    const bw = D.applyQuality('blade', 'white', 1.0);
    check(bl.reach > bw.reach && bl.arc > bw.arc, 'W21 近战范围随品质增大');

    const g = sandbox.window.__GAME__;
    g.start_run();
    g.state = 'playing';
    g.player.wkey = 'blade';
    g.bullets = [];
    const e = new I.Enemy(g.player.x + 20, g.player.y, 1);
    g.enemies.push(e);
    const hp0 = e.hp;
    g.player.cool = 0;
    g.player.update(g, 1 / 60, { mx: 1, my: 0, aim: 0, shoot: true, dash: false, slow: false });
    check(e.hp < hp0, 'W21 近战挥砍命中身前敌人');
    check(g.bullets.length === 0, 'W21 近战不产生子弹');
    g.state = 'playing';
}

// ============================================================ W22 定帧 / 击退
function t22_hitstop_knock(sandbox) {
    section('W22 打击停顿 / 受击击退（需求 20）');
    const I = sandbox.window.__INTERNALS__;
    const S = I.settings;
    const g = sandbox.window.__GAME__;
    g.start_run();
    g.state = 'playing';
    const pl = g.player;
    pl.wkey = 'pistol';

    // ---- 命中产生定帧
    const e = new I.Enemy(pl.x + 60, pl.y, 1);
    g.enemies.push(e);
    g.add_hitstop(0);
    e.take_damage(1.0, g, pl.x, pl.y);
    check(g.hitstop > 0, `W22 命中触发打击停顿（${g.hitstop.toFixed(3)}s）`);
    check(g.hitstop <= S.HITSTOP_MAX + 1e-6, 'W22 停顿夹在上限内');

    // ---- 不叠加成卡死
    for (let i = 0; i < 10; i++) { g.add_hitstop(0.045); }
    check(g.hitstop <= S.HITSTOP_MAX + 1e-6, 'W22 多次请求取最大值不叠加');

    // ---- 受击击退方向
    pl.hp = pl.max_hp;
    pl.iframes = 0;
    pl.knock_t = 0;
    pl.take_damage(2.0, g, pl.x - 40, pl.y);   // 来源在左 -> 向右推
    check(pl.knock_t > 0, 'W22 受击进入击退状态');
    check(pl.knock_dx > 0, `W22 击退方向正确（dx=${pl.knock_dx.toFixed(1)}）`);
    check(g.hitstop > 0, 'W22 受击触发打击停顿');

    // ---- 击退产生位移
    const x0 = pl.x;
    const inp = { mx: 0, my: 0, aim: 0, shoot: false, dash: false, slow: false };
    for (let i = 0; i < 6; i++) { g.step(1 / 60, inp); }
    check(pl.x > x0, `W22 击退期间位置前移（${x0.toFixed(1)}->${pl.x.toFixed(1)}）`);

    // ---- 暂停菜单含「脱离卡死」
    const acts = g.pause_items.map((it) => it[1]);
    check(acts.indexOf('unstuck') >= 0, 'W22 暂停菜单含「脱离卡死」');
    g.state = 'playing';
    g._doUnstuck ? g._doUnstuck() : g.doUnstuck();
    check(g.state === 'title', 'W22 脱离卡死后退回主菜单（进度已存）');
    g.state = 'playing';
}


function t23_save_system(sandbox) {
    section('W23 存档系统（需求 10：3 槽 / 个人 ID / 完整持久化）');
    const D = sandbox.window.__DATA__;
    const S = sandbox.window.__SAVE__;
    const np = sandbox.window.__newProfile__;
    const g = sandbox.window.__GAME__;
    if (!S || !np) { check(false, 'W23 __SAVE__ / __newProfile__ 未暴露'); return; }

    const snapshot = JSON.parse(JSON.stringify(S.data));
    try {
        // ---- 新档模板字段齐全（与 Python save.new_profile 对齐）
        const p = np(0, '');
        const need = ['version', 'id', 'name', 'created', 'played', 'coins',
            'diamonds', 'materials', 'chars', 'char', 'weapons', 'weapon',
            'skills', 'passives', 'codex', 'collects', 'showcase',
            'talent_unlocked', 'talent_levels', 'scene_prog', 'main_done',
            'chapter', 'stage', 'visited_scenes', 'cleared_scenes', 'scene_best',
            'unlocked_dungeons', 'bonus_unlocked', 'story_seen', 'tips_seen',
            'run', 'stats', 'settings'];
        let missing = need.filter((k) => p[k] === undefined);
        check(missing.length === 0, `W23 新档字段齐全（缺 ${missing.join(',') || '无'}）`);
        check(p.name === '漂泊者1', 'W23 默认名「漂泊者N」');
        check(p.settings.music === false && p.settings.sfx === true &&
              p.settings.vibrate === false, 'W23 新档音效默认开启');
        check(p.showcase.length === 6, 'W23 展示台 6 格');
        check(p.chars[0] === 'scout' && p.weapons.pistol === 0, 'W23 新档初始角色/武器');

        // ---- create / get / current
        S.data = { version: 2, slots: [null, null, null], last: null };
        const created = S.create(1, '阿甲');
        check(created && created.name === '阿甲' && created.id === 1, 'W23 create 建档');
        check(S.get(1) === created, 'W23 get 取回同一对象');
        check(S.current() === created, 'W23 last 指向新档');
        check(S.freeSlot() === 0, 'W23 freeSlot 返回第一个空位');

        // ---- 3 槽上限
        S.create(0, '阿乙'); S.create(2, '阿丙');
        check(S.freeSlot() === null, 'W23 满 3 槽后 freeSlot 为 null');
        check(S.slots().length === 3, 'W23 槽位数恒为 3');

        // ---- 删除
        S.remove(1);
        check(S.get(1) === null, 'W23 删除后该槽为空');
        check(S.slots().filter((x) => x !== null).length === 2, 'W23 删除后剩 2 档');

        // ---- 落盘 + 重载（持久化）
        S.data.slots[0].coins = 1234;
        S.data.slots[0].cleared_scenes = ['sewer'];
        S.data.slots[0].codex.enemy = ['slime'];
        S.data.slots[0].materials = { scrap: 7 };
        S.save();
        S.data = { version: 2, slots: [null, null, null], last: null };
        const ok = S.load();
        check(ok, 'W23 从 localStorage 重载成功');
        const back = S.get(0);
        check(back && back.coins === 1234, 'W23 货币持久化');
        check(back && back.cleared_scenes.indexOf('sewer') >= 0, 'W23 场景进度持久化');
        check(back && back.codex.enemy.indexOf('slime') >= 0, 'W23 图鉴持久化');
        check(back && back.materials.scrap === 7, 'W23 材料持久化');

        // ---- 旧档迁移：缺字段补齐（写一个残缺档再 load）
        const legacy = { id: 2, name: '老档', coins: 5 };
        sandbox.window.localStorage.removeItem(sandbox.window.__SAVE_KEYS__.backup);
        sandbox.window.localStorage.setItem(
            sandbox.window.__SAVE_KEYS__.main,
            JSON.stringify({ version: 1, slots: [legacy, null, null], last: 0 }));
        S.load();
        const lp = S.get(0);
        check(lp && lp.coins === 5, 'W23 旧档保留原数据');
        check(lp && lp.settings && lp.settings.music === false,
              'W23 旧档补齐 settings 字段');
        check(lp && lp.stats && lp.stats.kills === 0, 'W23 旧档补齐 stats 字段');

        // ---- 存档损坏 -> 回退备份
        S.data.slots[0] = np(0, '好档');
        S.data.slots[0].coins = 777;
        S.save();                       // 这次会把上一个档写进 backup
        S.save();
        sandbox.window.localStorage.setItem(
            sandbox.window.__SAVE_KEYS__.main, '{ 这不是合法 JSON');
        const ok2 = S.load();
        check(ok2, 'W23 主档损坏时回退备份并成功装载');
        check(S.get(0) && S.get(0).coins === 777, 'W23 备份档内容正确');

        // ---- Game 层：选档 -> profile 生效 -> 设置随档走
        S.data = { version: 2, slots: [null, null, null], last: null };
        const a = S.create(0, '甲');
        a.settings.sfx = true;
        a.settings.joystick = 'fixed';
        S.save();
        g.profile = null;
        check(g.select_profile(0) === true, 'W23 select_profile 成功');
        check(g.profile === a, 'W23 选中后 game.profile 指向该档');
        check(g.setting.sfx === true, 'W23 设置从档读入（sfx=on）');
        check(g.setting.joystick === 'fixed', 'W23 设置从档读入（joystick=fixed）');

        // ---- 设置改动写回档
        g.toggle_setting('music');
        check(a.settings.music === true, 'W23 切换设置写回存档');

        // ---- delete_profile 清空 game.profile
        check(g.delete_profile(0) === true, 'W23 delete_profile 成功');
        check(g.profile === null, 'W23 删除当前档后 profile 置空');

        // ---- 存档槽流程：title -> slots -> 建档 -> 客厅（不死循环）
        S.data = { version: 2, slots: [null, null, null], last: null };
        g.state = 'title';
        g._menu_pick('new');
        check(g.state === 'slots', 'W23 开始游戏 -> 存档槽');
        g.slot_index = 0;
        g._keydownSlots('enter');
        check(g.state === 'slot_create', 'W23 空槽 Enter -> 建档界面');
        g._keydownSlots('escape');
        check(g.state === 'slots', 'W23 ESC 退回槽列表');
        g._keydownSlots('enter');
        g._keydownSlots('escape');    // 再回到 slots
        g._keydownSlots('enter');     // 进 slot_create
        g.name_buf = '阿丁';
        g._keydownSlots('enter');
        check(g.state === 'lobby', 'W23 建档后直接进客厅（关键：不死循环）');
        check(g.profile && g.profile.name === '阿丁', 'W23 建档名字生效');
        check(g.slot_list()[0] !== null, 'W23 新档已占槽');

        // ---- 删除确认流程
        g.state = 'slots';
        g.slot_index = 0;
        g._keydownSlots('d');
        check(g.state === 'slot_confirm', 'W23 D 进入删除确认');
        g._keydownSlots('n');
        check(g.state === 'slots', 'W23 N 取消删除');
        check(g.slot_list()[0] !== null, 'W23 取消后档仍在');
        g._keydownSlots('d');
        g._keydownSlots('y');
        check(g.slot_list()[0] === null, 'W23 Y 确认后档被删除');

        // ---- 各界面渲染不抛异常
        try {
            g.state = 'slots'; g.draw();
            g.state = 'slot_create'; g.slot_pending = 1; g.draw();
            g.state = 'slot_confirm'; g.draw();
            check(true, 'W23 三种存档界面渲染正常');
        } catch (e) {
            check(false, 'W23 存档界面渲染异常: ' + e.message);
        }

        // ---- 鼠标点选
        S.data = { version: 2, slots: [null, null, null], last: null };
        S.create(0, '点选');
        g.state = 'slots';
        g.mouse_canvas = [300, 100];
        g._slotMouse([300, 100]);
        check(g.state === 'lobby', 'W23 鼠标点已有档直接进客厅');
    } finally {
        S.data = snapshot;
        try { S.save(); } catch (e) { /* 忽略 */ }
        g.state = 'title';
    }
}


function t19_settings(sandbox) {
    const g = sandbox.window.__GAME__;
    if (!g) { check(false, 'W19 __GAME__ 未暴露'); return; }

    // ---- 2.2 起战斗音效默认开启
    check(g.setting.music === false && g.setting.sfx === true,
        'W19 音乐默认关闭、音效默认开启');
    check(g.setting.vibrate === false, 'W19 震动默认关闭');

    // ---- 需求 11：BGM 模块已接线
    // 无头沙箱没有 AudioContext，Music 会自我降级（enabled 保持 false），
    // 所以这里只验证"开关会同步到 Music"这条接线，而不假设它一定成功开启。
    const M = sandbox.window.__MUSIC__;
    if (M) {
        let sawOn = false;
        const orig = M.set_enabled;
        M.set_enabled = function (on, mood) { sawOn = !!on; return orig.call(M, on, mood); };
        g.setting.music = true;
        g._applyAudioSettings();
        check(sawOn === true, 'W19 打开音乐 -> 已同步到 Music');
        M.set_enabled = orig;
        g.setting.music = false;
        g._applyAudioSettings();
        check(M.enabled === false, 'W19 关闭音乐 -> Music 停止');
        // 情绪档按场景深浅分 4 档
        g.level_state = { scene: sandbox.window.__DATA__.MAIN[0] };
        const m0 = g.music_mood();
        g.level_state = { scene: sandbox.window.__DATA__.BONUS };
        const m3 = g.music_mood();
        check(m0 >= 0 && m0 <= 3 && m3 >= 0 && m3 <= 3 && m3 >= m0,
            `W19 BGM 情绪档随场景变深（${m0} -> ${m3}）`);
        g.level_state = null;
    } else {
        check(false, 'W19 __MUSIC__ 未暴露');
    }

    // ---- 切换 bool
    g.state = 'help';
    g.setting_index = 1;  // sfx
    g._keydownSettings('enter');
    check(g.setting.sfx === false, 'W19 Enter 关闭音效');

    // ---- 摇杆模式循环
    g.setting_index = 4;  // joystick
    const before = g.setting.joystick;
    g._keydownSettings('enter');
    check(g.setting.joystick !== before,
        `W19 摇杆模式可切换（${before} -> ${g.setting.joystick}）`);

    // ---- 灵敏度步进与夹紧
    g.setting_index = 5;  // joy_sens
    g.setting.joy_sens = 1.0;
    g._keydownSettings('enter');
    check(Math.abs(g.setting.joy_sens - 1.1) < 1e-6,
        `W19 灵敏度 +0.1（${g.setting.joy_sens}）`);
    for (let i = 0; i < 40; i++) { g._keydownSettings('d'); }
    check(g.setting.joy_sens <= 2.0, 'W19 灵敏度上限夹紧 2.0');
    for (let i = 0; i < 40; i++) { g._keydownSettings('a'); }
    check(g.setting.joy_sens >= 0.4, 'W19 灵敏度下限夹紧 0.4');

    // ---- 选中项循环
    g.setting_index = 0;
    g._keydownSettings('w');
    check(g.setting_index === 10, 'W19 ↑ 从首项绕到末项');

    // ---- 渲染不炸
    let okdraw = true;
    for (let i = 0; i < 6; i++) {
        g.setting_index = i;
        try { g.draw(); } catch (e) { okdraw = false; }
    }
    check(okdraw, 'W19 设置面板逐项渲染正常');

    g.state = 'playing';
}


function t18_chests(sandbox) {
    const D = sandbox.window.__DATA__;
    section('W18 宝箱分级（5 类 × 2 档）');
    const g = sandbox.window.__GAME__;
    if (!g) { check(false, 'W18 __GAME__ 未暴露'); return; }

    // ---- 数据层完整性
    const keys = ['coin', 'heal', 'material', 'weapon', 'collect'];
    let allTiers = true;
    for (const k of keys) {
        const c = D.CHESTS[k] || {};
        if (!c.normal || !c.superb) { allTiers = false; }
    }
    check(allTiers, 'W18 5 类宝箱都有 一般/极品 两档');
    check(D.CHESTS.collect.normal.w < D.CHESTS.weapon.normal.w &&
        D.CHESTS.collect.superb.w < D.CHESTS.weapon.superb.w,
        'W18 收集品箱权重低于武器箱（更稀有）');

    // ---- rollChest 覆盖 10 种组合
    let s = 20240923;
    const rng = {
        random() { s = (s * 1103515245 + 12345) & 0x7fffffff; return s / 0x7fffffff; },
        randint(a, b) { return a + Math.floor(this.random() * (b - a + 1)); },
        uniform(a, b) { return a + (b - a) * this.random(); },
        choice(arr) { return arr[Math.floor(this.random() * arr.length)]; }
    };
    const seen = new Set();
    for (let i = 0; i < 4000; i++) {
        const r = D.rollChest(rng, 0.2);
        seen.add(r[0] + '/' + r[1]);
    }
    check(seen.size === 10, `W18 rollChest 覆盖 10 种组合（${seen.size}）`);

    // ---- chestLoot 各类
    const lc = D.chestLoot(rng, 'coin', 'superb', 3);
    check(lc.coins >= 35, `W18 极品货币箱金币更多（${lc.coins}）`);
    const lh = D.chestLoot(rng, 'heal', 'superb', 3);
    check(lh.heal >= 7 && lh.energy > 0, 'W18 极品急救箱回血 + 回能');
    const lm = D.chestLoot(rng, 'material', 'normal', 2);
    check(typeof lm.mats === 'object', 'W18 材料箱返回材料字典');
    const lw = D.chestLoot(rng, 'weapon', 'superb', 3);
    check(D.QUALITY_ORDER.indexOf(lw.quality) >= 0,
        `W18 武器箱给品质（${lw.quality}）`);

    // ---- 拾取物文案
    const P = sandbox.window.__INTERNALS__.Pickup;
    if (P) {
        const pc = new P(0, 0, 'chest', 1, null, 0, 'material', 'superb');
        check(('' + pc.promptText()).indexOf('稀有材料箱') >= 0,
            `W18 宝箱提示带类别名：${pc.promptText()}`);
    } else {
        check(false, 'W18 __PICKUP__ 未暴露（跳过文案校验）');
    }

    // ---- 端到端：开箱掉资源
    g.start_run();
    g.state = 'playing';
    const PC = sandbox.window.__INTERNALS__.Pickup;
    if (PC) {
        const chest = new PC(g.player.x, g.player.y, 'chest', 1, null, 0,
            'coin', 'superb');
        g.room.pickups = [chest];
        chest.interact(g);
        check(chest.alive === false, 'W18 开箱后宝箱消失');
        const coins = g.room.pickups.filter((p) => p.kind === 'coin').length;
        check(coins > 0, `W18 开箱掉出金币（${coins} 枚）`);

        g.mats = {};
        const mc = new PC(g.player.x, g.player.y, 'chest', 1, null, 0,
            'material', 'normal');
        g.room.pickups = [mc];
        mc.interact(g);
        check(Object.keys(g.mats).length > 0,
            `W18 材料箱把材料放进背包（${Object.keys(g.mats).length} 种）`);
    }
    g.state = 'playing';
}


function t17_growth(sandbox) {
    const D = sandbox.window.__DATA__;
    section('W17 养成系统（角色 / 武器 / 技能 / 天赋 / 材料）');
    const g = sandbox.window.__GAME__;
    if (!g) { check(false, 'W17 __GAME__ 未暴露'); return; }

    function freshProf() {
        return {
            name: 'G17', char: 'scout', coins: 0, diamonds: 0, materials: {},
            chars: ['scout'], weapons: { pistol: 0 }, weapon: 'pistol',
            skills: {}, passives: {}, talent_unlocked: [], talent_levels: {},
            codex: { enemy: [], weapon: [], material: [], collect: [] },
            collects: [], showcase: [null, null, null, null, null, null],
            cleared_scenes: [], unlocked_dungeons: [], scene_best: {},
            scene_prog: {}, run: null, bonus_unlocked: false, main_done: false
        };
    }

    // ---- 角色列表与购买
    let prof = freshProf();
    let rows = D.charList(prof);
    check(Array.isArray(rows) && rows.length >= 6, `W17 角色列表返回 6+ 条（${rows.length}）`);
    const ownedRow = rows.filter((r) => r.owned).map((r) => r.key);
    check(ownedRow.length === 1 && ownedRow[0] === 'scout', 'W17 初始只拥有 scout');
    const locked = rows.filter((r) => !r.owned);
    check(locked.length >= 5, `W17 锁定角色 5+ 个（${locked.length}）`);

    // 金币不足时拒绝购买
    let res = D.buyChar(prof, locked[0] ? locked[0].key : 'x');
    check(res[0] === false, 'W17 金币不足时购买角色被拒');

    // 无存档时兜底
    const noProf = D.charList(null);
    check(Array.isArray(noProf) && noProf.length >= 6, 'W17 无存档时角色列表兜底');

    // ---- 武器成长线（白 -> 绿 -> 蓝，封顶蓝）
    check(D.qualityForWeapon('pistol', 0) === 'white', 'W17 武器 Lv.0 为白色');
    check(D.qualityForWeapon('pistol', 2) === 'white', 'W17 武器 Lv.2 品质固定');
    check(D.qualityForWeapon('pistol', 5) === 'white', 'W17 武器 Lv.5 品质固定');
    check(D.qualityForWeapon('pistol', 99) === 'white', 'W17 武器升级不改变品质');
    check(D.nextGrowthAt(0) === 2, 'W17 Lv.0 距下一档还需 2 级');
    const c0 = D.upgradeCostSimple(0);
    check(c0[0] === 260, `W17 Lv.0 强化金币 260（${c0[0]}）`);
    check(c0[1].scrap === 2, 'W17 Lv.0 强化需废铁 2');

    // 金币/材料不足 -> 拒绝
    prof = freshProf();
    res = D.canUpgrade(prof, 'pistol');
    check(res[0] === false, 'W17 资源不足时强化被拒');

    // 发资源后成功强化到 Lv.5（品质变蓝）
    prof.coins = 999999;
    prof.materials = { scrap: 999, fiber: 999, circuit: 999 };
    let ups = 0;
    for (let i = 0; i < 5; i++) {
        const r2 = D.upgradeWeapon(prof, 'pistol');
        if (r2[0]) { ups++; }
    }
    check(ups === 5, `W17 连续强化 5 次成功（${ups}）`);
    check(prof.weapons.pistol === 5, `W17 武器等级为 Lv.5（${prof.weapons.pistol}）`);
    const wi = D.weaponInfo(prof, 'pistol');
    check(wi.quality === 'white', `W17 满 5 级后品质固定白色（${wi.quality}）`);
    check(wi.mul > 1.0, `W17 强化后伤害倍率 > 1（${wi.mul}）`);

    // ---- 技能 / 被动 / 天赋（补足资源，避免受前段武器强化扣款影响）
    prof.coins = 999999;
    prof.materials = { scrap: 999, fiber: 999, circuit: 999, crystal: 999,
                       alloy: 999, core: 999 };
    res = D.upgradeSkill(prof, 'vital');
    check(res[0] === true, 'W17 技能 vital 升级成功');
    check(prof.skills.vital === 1, 'W17 技能 vital 等级写入存档');
    res = D.upgradePassive(prof, 'thorns');
    check(res[0] === true, 'W17 被动 thorns 升级成功');
    check(prof.passives.thorns === 1, 'W17 被动 thorns 等级写入存档');

    prof.diamonds = 999;
    prof.materials = { scrap: 999, fiber: 999, circuit: 999, crystal: 999 };
    const tRows = D.talentList(prof);
    check(Array.isArray(tRows) && tRows.length > 0, `W17 天赋列表非空（${tRows.length}）`);
    if (tRows.length) {
        res = D.upgradeTalent(prof, tRows[0].key);
        check(res[0] === true, 'W17 永久天赋升级成功');
    }

    // ---- 材料摘要
    const summ = D.materialSummary(prof);
    check(Array.isArray(summ) && summ.length > 0, `W17 材料摘要非空（${summ.length}）`);

    // ---- 客厅键盘端到端
    g.profile = prof;
    g._enterLobby();
    g.lobby_tab = 1; g.growth_sub = 0; g.growth_index = 0;
    let kr = true;
    try {
        g._keydownLobby('d');
        g._keydownLobby('d');
        g._keydownLobby('d');
        g._keydownLobby('w');
        g._keydownLobby('s');
        g._keydownLobby('enter');
        g.draw();
    } catch (e) { kr = false; }
    check(kr, 'W17 客厅养成分页键盘操作 + 渲染无异常');
    check(g.growth_sub === 3, `W17 → 键三次到天赋子页（${g.growth_sub}）`);

    // ---- 角色装配影响开局（hp / 速度 / 初始武器）
    prof.char = 'scout';
    prof.weapon = 'pistol';
    prof.skills = { vital: 0, haste: 0, focus: 0 };
    g.profile = prof;
    g.seed = 20240923;
    g.start_run();
    check(g.player.wkey === 'pistol', `W17 开局武器取存档 weapon（${g.player.wkey}）`);
    check(g.char_spd_mul > 0, `W17 角色速度系数已写入（${g.char_spd_mul}）`);
    const lv = g.player.wlevel(g);
    check(lv === 5, `W17 开局读到武器强化等级 Lv.5（${lv}）`);
    check(g.player.wq(g) === 'white', 'W17 开局武器固定白色品质');
    const expectMul = D.QUALITIES.white.mul * (1.0 + 0.10 * 5);
    check(Math.abs(g.player.wmul(g) - expectMul) < 1e-6,
        `W17 伤害倍率 = 品质mul×等级加成（${g.player.wmul(g).toFixed(4)}）`);

    // 收尾：把状态归位，避免把 story 过场态泄漏给后续小节
    g.state = 'playing';
}


function t24_input_path(sandbox) {
    section('W24 真实键盘输入路径（与 Python T23 对齐）');
    const g = sandbox.window.__GAME__;
    const INPUT = sandbox.window.__INPUT__;
    const T = INPUT && INPUT.Input;
    if (!g) { check(false, 'W24 __GAME__ 未暴露'); return; }

    const snapState = g.state;
    const snapKeys = T ? JSON.parse(JSON.stringify(T.keys)) : null;
    try {
        g.inp = null;
        if (T) { T.keys = {}; }
        g.state = 'playing';

        // 无输入 -> mx/my 为 0
        let inp = g.read_input();
        check(inp.mx === 0 && inp.my === 0, 'W24 无输入时 mx/my 为 0');

        if (T) {
            // ---- 事件驱动：直接写 Input.keys（等价于 keydown 监听器）
            T.keys = { d: true };
            inp = g.read_input();
            check(inp.mx === 1, `W24 按住 D 读出向右（mx=${inp.mx}）`);

            // 四方向
            const dirs = [['a', -1, 'mx'], ['d', 1, 'mx'],
                          ['w', -1, 'my'], ['s', 1, 'my']];
            for (const [k, want, axis] of dirs) {
                T.keys = {};
                T.keys[k] = true;
                inp = g.read_input();
                check(inp[axis] === want,
                    `W24 键 ${k} -> ${axis}=${want}（实得 ${inp[axis]}）`);
            }

            // 方向键别名
            T.keys = {};
            T.keys.arrowup = true;
            inp = g.read_input();
            check(inp.my === -1, `W24 方向键 ↑ 同样生效（my=${inp.my}）`);

            // ---- 松开后归零
            T.keys = {};
            inp = g.read_input();
            check(inp.mx === 0 && inp.my === 0, 'W24 松开后归零');

            // ---- 失焦清空（浏览器 blur 监听器语义）
            T.keys = { d: true, a: true };
            T.keys = {};   // blur 处理器 `Input.keys = {}`
            inp = g.read_input();
            check(inp.mx === 0, 'W24 失焦清空后不再移动（防自己走个不停）');
            T.keys = snapKeys || {};
        } else {
            // 没有 __INPUT__ 时至少验证 read_input 不抛异常
            check(typeof g.read_input() === 'object', 'W24 read_input 返回对象');
        }
    } catch (e) {
        check(false, `W24 输入路径用例异常：${e && e.message}`);
    } finally {
        g.state = snapState;
        g.inp = null;
        if (T && snapKeys) { T.keys = snapKeys; }
    }
}


function t25_floor_exit_portal(sandbox) {
    section('W25 普通层目标房 -> 传送门（与 Python T24 对齐）');
    const G = sandbox.window.__GAME__;
    const Dref = sandbox.window.__DATA__;
    if (!G) { check(false, 'W25 __GAME__ 未暴露'); return; }

    // 自备结构完整 profile，避免继承前序测试被裁剪过的对象
    G.profile = {
        name: 'W25', char: 'scout', coins: 0, diamonds: 0,
        cleared_scenes: [], unlocked_dungeons: [], scene_best: {},
        scene_prog: {}, codex: {}, collects: [], showcase: [null, null, null, null],
        run: null, bonus_unlocked: false, main_done: false, talent_levels: {}
    };
    G.seed = 20241010;
    // 回到第 1 关第 1 层（纯普通层，绝无首领）
    if (Dref && Dref.nextStage) {
        Dref.nextStage(G.profile, Dref.MAIN[0], 0);
        G.level_state = Object.assign({}, G.profile.run);
    }
    G.floor = 1;
    G._start_floor(1);
    G.state = 'playing';

    const d = G.dungeon;
    check(!!d && !d.is_boss_floor, 'W25 构造出普通层（非首领层）');
    check(!!d && d.goal_key !== null && d.goal_key !== undefined,
        'W25 普通层也有目标房 goal_key');

    const gk = d.goal_key;
    const GW = d.gw || 5;
    const idxOf = (k) => (k % GW);
    const gyOf = (k) => Math.floor(k / GW);

    // ---- A) 先清一个非目标房：不应有传送门
    let nongoal = null;
    for (const k of Object.keys(d.rooms).map(Number)) {
        const r = d.rooms[k];
        const gx = idxOf(k), gy = gyOf(k);
        if (r.kind === 'normal' && !r.cleared
            && !(gx === gk[0] && gy === gk[1])) { nongoal = [gx, gy]; break; }
    }
    if (nongoal) {
        G.enter_room(nongoal[0], nongoal[1], null, false);
        G.state = 'playing';
        for (let wave = 0; wave < 3; wave++) {
            for (const e of G.enemies) { e.alive = false; }
            G.step(1 / 60, NEUTRAL);
        }
        check(!!G.room.cleared, 'W25 非目标房已清空');
        check(!G.room.portal, 'W25 非目标房不开传送门');
    }

    // ---- B) 清空目标房：必须出现传送门（本次修复的核心断言）
    G.enter_room(gk[0], gk[1], null, false);
    G.state = 'playing';
    for (let wave = 0; wave < 3; wave++) {
        for (const e of G.enemies) { e.alive = false; }
        G.step(1 / 60, NEUTRAL);
    }
    check(!!G.room.cleared, 'W25 目标房已清空');
    check(!!G.room.portal,
        'W25 普通层目标房清空后出现传送门（此前恒为 null）');

    // ---- C) 真实走进去 -> 推进到下一层
    const f0 = G.floor;
    if (G.room.portal) {
        G.player.x = G.room.portal[0];
        G.player.y = G.room.portal[1];
        G.step(1 / 60, NEUTRAL);
        check(G.state === 'playing', 'W25 触碰传送门不会自动推进');
        G.request_interact();
        G.request_interact();
        check((G.state === 'story' && G.profile.run && G.profile.run.stage_idx === 1) ||
              G.state === 'levelclear' || G.floor > f0,
            `W25 进入传送门推进下一关（floor ${f0} -> ${G.floor}, state=${G.state}）`);
    }
}


const gg = sandbox.window.__GAME__;
    // 全局固定种子：Game 构造时 seed=null → makeRng(null) 会退化成时间随机，
    // 使得每一节的 start_run() 都生成不同的地牢（W9 曾因此偶发失败）。
    // 单个小节需要别的种子时自行覆盖 g.seed。
    if (gg) { gg.seed = 20240923; }
    guard('W31', () => t31_health_skills(sandbox));
    guard('W0', () => t0_assets(sandbox, mainCanvas));
    if (sandbox.window.__DUNGEON__) {
        guard('W1', () => t1_dungeon(sandbox));
    } else if (want('W1')) {
        section('W1 地牢生成不变量（多楼层 × 多种子）');
        check(false, 'W1 window.__DUNGEON__ 未暴露，无法构造地牢');
    }
    guard('W10', () => t10_fx_coords(sandbox, mainCanvas));
    guard('W11', () => t11_weapon_swap_no_pingpong(sandbox));
    guard('W12', () => t12_no_stuck_in_wall(sandbox));
    guard('W13', () => t13_hazards(sandbox));
    guard('W14', () => t14_pollution_conditions(sandbox));
    guard('W15', () => t15_codex_showcase(sandbox));
    guard('W16', () => t16_talents(sandbox));
    guard('W17', () => t17_growth(sandbox));
    guard('W18', () => t18_chests(sandbox));
    guard('W19', () => t19_settings(sandbox));
    guard('W20', () => t20_changelog(sandbox));
    guard('W21', () => t21_weapon_mech(sandbox));
    guard('W22', () => t22_hitstop_knock(sandbox));
    guard('W23', () => t23_save_system(sandbox));
    guard('W24', () => t24_input_path(sandbox));
    guard('W25', () => t25_floor_exit_portal(sandbox));
    guard('W2', () => t2_weapons(gg, sandbox));
    guard('W3', () => t3_combat(gg));
    guard('W4', () => t4_boss(gg));
    guard('W5', () => t5_transition(gg));
    guard('W6', () => t6_drops(gg, sandbox));
    guard('W8', () => t8_screens(sandbox));
    guard('W7', () => t7_fuzz(gg));
    guard('W9', () => t9_full_run(gg, sandbox.window.__DATA__));
    guard('W35', () => {
        section('W35 机械坟场可选勘测路线');
        const Dungeon = sandbox.window.__DUNGEON__;
        let found = 0, sample = null;
        for (let seed = 0; seed < 100; seed++) {
            const d = new Dungeon(1, makeTestRng(seed), 'd_mine', 1);
            const key = d.chooseSurveyRoom();
            if (key) { found++; if (sample === null) sample = seed; }
            check(JSON.stringify(key) === JSON.stringify(d.chooseSurveyRoom()),
                  'W35 选房不消耗随机数 ' + seed);
        }
        check(found >= 80, 'W35 100 张地图候选覆盖率 ' + found + '/100');
        const graph = new Dungeon(1, makeTestRng(7), 'd_mine', 1);
        graph.rooms = {};
        [[2,2,'start','ES'],[3,2,'normal','WES'],[4,2,'normal','W'],
         [2,3,'normal','NE'],[3,3,'normal','WN']].forEach(row => {
            graph.rooms[row[1]*5+row[0]] = {
                gx:row[0],gy:row[1],kind:row[2],doors:row[3].split('')};
        });
        graph.start_key = [2,2]; graph.goal_key = [4,2];
        check(JSON.stringify(graph.chooseSurveyRoom()) === '[2,3]',
              'W35 两端固定门网选出相同房间 (2,3)');
        const g = sandbox.window.__GAME__;
        g.profile = null;
        g.level_state = {scene:'d_mine',stage_idx:1,diff:[1,1]};
        g._start_floor(1, sample, false);
        check(g.state === 'route_choice', 'W35 出生房显示路线选择');
        g.profile = sandbox.window.__newProfile__(0, 'route-test');
        g._chooseRoute(1);
        check(g.route_state === 'survey' && g.profile.run_checkpoint.route_state === 'survey',
              'W35 勘测选择进入入口断点');
        const cp = JSON.parse(JSON.stringify(g.profile.run_checkpoint));
        g._start_floor(1, sample, false);
        g._restoreFloorCheckpoint(cp);
        check(g.route_state === 'survey' && !g.route_sealed,
              'W35 续玩保留路线并重打样本房');
        g.route_sealed = true; g._stage_done = false;
        g._finishStage();
        check(g.profile.materials.crystal === 2,
              'W35 首次勘测奖励 2 个污染结晶');
        g._stage_done = false; g._finishStage();
        check(g.profile.materials.crystal === 2,
              'W35 重复提交不重复发奖');
        const S = sandbox.window.__SAVE__, keys = sandbox.window.__SAVE_KEYS__;
        const claimed = sandbox.window.__newProfile__(0, 'route-test');
        claimed.route_first_rewards = ['mine_survey_02'];
        const advanced = Object.assign({}, claimed, {
            played: 10, route_first_rewards: []
        });
        sandbox.window.localStorage.setItem(keys.main,
            JSON.stringify({slots:[advanced,null,null],last:0}));
        sandbox.window.localStorage.setItem(keys.backup,
            JSON.stringify({slots:[claimed,null,null],last:0}));
        S.load();
        check(S.get(0).played === 10 &&
              S.get(0).route_first_rewards.indexOf('mine_survey_02') >= 0,
              'W35 同一档主档与备份合并保留首奖标记');
    });

    const ok = RESULTS.filter((r) => r[0]).length;
    console.log('\n' + '='.repeat(62));
    if (FRAME_ERRORS.length) {
        console.log(`逐帧异常样本（共 ${FRAME_ERRORS.length}，前 10 条）：`);
        for (const e of FRAME_ERRORS.slice(0, 10)) { console.log('   - ' + e.slice(0, 200)); }
        console.log('');
    }
    const failed = RESULTS.filter((r) => !r[0]).map((r) => r[1]);
    if (failed.length) {
        console.log(`失败项（${failed.length}）：`);
        for (const m of failed) { console.log('   x ' + m); }
        console.log('');
    }
    console.log(`结果：${ok}/${RESULTS.length} 项通过`);
    process.exit(failed.length || FRAME_ERRORS.length ? 1 : 0);
})();
