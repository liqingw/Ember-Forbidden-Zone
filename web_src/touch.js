/* Mobile controls for the shared 16:9 game canvas. */
(function () {
    'use strict';

    var TOUCH = window.__TOUCH__ = {
        enabled: false, mx: 0, my: 0, aim: null, aimVector: null, aimAngle: null,
        shoot: false, dash: false, act: false, swap: false, skill: false,
        syncControls: function () {}, reset: function () {}
    };
    function mobileDevice() {
        if (window.Capacitor && typeof window.Capacitor.isNativePlatform === 'function'
                && window.Capacitor.isNativePlatform()) { return true; }
        if (window.matchMedia) { return window.matchMedia('(pointer: coarse)').matches; }
        return (navigator.maxTouchPoints || 0) > 0;
    }
    function ready(fn) {
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', fn);
        } else { fn(); }
    }
    ready(function () {
        if (!mobileDevice()) { return; }
        var stage = document.getElementById('stage');
        var canvas = document.getElementById('cv');
        if (!stage || !canvas) { return; }
        TOUCH.enabled = true;
        document.body.classList.add('mobile-mode');

        function game() { return window.__GAME__; }
        function toView(x, y) {
            var r = canvas.getBoundingClientRect();
            return [(x - r.left) * canvas.width / r.width,
                    (y - r.top) * canvas.height / r.height];
        }
        function unlock() {
            var g = game();
            if (g && g.unlockAudio) { g.unlockAudio(); }
        }

        var DEADZONE = 0.14;
        var base = document.createElement('div');
        var knob = document.createElement('div');
        base.id = 'stick-base';
        knob.id = 'stick-knob';
        base.style.display = knob.style.display = 'none';
        document.body.appendChild(base);
        document.body.appendChild(knob);
        var stickId = null, aimId = null, centerX = 0, centerY = 0, radius = 58;
        function hideStick() {
            stickId = null; TOUCH.mx = 0; TOUCH.my = 0;
            base.style.display = knob.style.display = 'none';
        }
        function startStick(e) {
            var g = game(), fixed = g && g.setting && g.setting.joystick === 'fixed';
            var r = canvas.getBoundingClientRect();
            var anchorX = r.left + Math.min(96, r.width * .18);
            var anchorY = r.bottom - Math.min(100, r.height * .28);
            centerX = fixed ? anchorX : e.clientX;
            centerY = fixed ? anchorY : e.clientY;
            stickId = e.pointerId;
            base.style.display = knob.style.display = 'block';
            base.style.left = knob.style.left = centerX + 'px';
            base.style.top = knob.style.top = centerY + 'px';
            moveStick(e);
        }
        function moveStick(e) {
            if (e.pointerId !== stickId) { return; }
            var g = game(), fixed = g && g.setting && g.setting.joystick === 'fixed';
            var dx = e.clientX - centerX, dy = e.clientY - centerY;
            var len = Math.hypot(dx, dy);
            if (!fixed && len > radius * 1.45) {
                var pull = len - radius * 1.45;
                var ux = dx / len, uy = dy / len;
                var r = canvas.getBoundingClientRect();
                centerX = Math.max(r.left + 20, Math.min(r.left + r.width * 0.48, centerX + ux * pull));
                centerY = Math.max(r.top + 20, Math.min(r.bottom - 20, centerY + uy * pull));
                base.style.left = centerX + 'px';
                base.style.top = centerY + 'px';
                dx = e.clientX - centerX; dy = e.clientY - centerY;
                len = Math.hypot(dx, dy);
            }
            var clamped = len > radius ? radius : len;
            var scale = len > 0 ? clamped / len : 0;
            var norm = clamped / radius;
            if (norm <= DEADZONE) {
                TOUCH.mx = 0; TOUCH.my = 0;
            } else {
                var mapped = (norm - DEADZONE) / (1 - DEADZONE);
                var sens = Number((g && g.setting && g.setting.joy_sens) || 1);
                if (!isFinite(sens) || sens <= 0) { sens = 1; }
                var outLen = Math.min(1, mapped * sens);
                TOUCH.mx = (dx / len) * outLen;
                TOUCH.my = (dy / len) * outLen;
            }
            knob.style.left = (centerX + dx * scale) + 'px';
            knob.style.top = (centerY + dy * scale) + 'px';
        }
        stage.addEventListener('pointerdown', function (e) {
            if (e.pointerType === 'mouse') { return; }
            unlock();
            var g = game();
            if (!g) { return; }
            var p = toView(e.clientX, e.clientY);
            if (g.collection_popup) {
                g._keydown('enter');
            } else if (g.state !== 'playing') {
                g.mouse_canvas = p;
                g._click();
            } else {
                var r = canvas.getBoundingClientRect();
                if (e.clientX < r.left + r.width * .52 && stickId === null) {
                    startStick(e);
                    stage.setPointerCapture(e.pointerId);
                } else if (fireId === null && aimId === null) {
                    aimId = e.pointerId;
                    TOUCH.aim = p;
                    TOUCH.aimVector = null;
                    stage.setPointerCapture(e.pointerId);
                }
            }
            e.preventDefault();
        });
        stage.addEventListener('pointermove', function (e) {
            if (e.pointerType === 'mouse') { return; }
            if (e.pointerId === stickId) { moveStick(e); }
            else if (e.pointerId === aimId && game() && game().state === 'playing') {
                TOUCH.aim = toView(e.clientX, e.clientY);
            }
            e.preventDefault();
        });
        function endPointer(e) {
            if (e.pointerId === stickId) { hideStick(); }
            if (e.pointerId === aimId) { aimId = null; TOUCH.aim = null; }
            e.preventDefault();
        }
        stage.addEventListener('pointerup', endPointer);
        stage.addEventListener('pointercancel', endPointer);

        var buttons = [], fire = null, fireKnob = null;
        var fireId = null, fireOriginX = 0, fireOriginY = 0;

        TOUCH.reset = function () {
            hideStick();
            aimId = null; TOUCH.aim = null;
            TOUCH.shoot = false;
            TOUCH.dash = TOUCH.act = TOUCH.swap = TOUCH.skill = false;
            TOUCH.aimVector = null;
            if (fire) { fire.classList.remove('hit'); }
            if (fireKnob) { fireKnob.style.transform = 'translate(-50%, -50%)'; }
            fireId = null;
            fireOriginX = fireOriginY = 0;
        };
        window.addEventListener('blur', TOUCH.reset);

        function button(id, label, action, release, withCd) {
            var el = document.createElement('div');
            el.id = id;
            var lbl = document.createElement('span');
            lbl.className = 'btn-lbl';
            lbl.textContent = label;
            el.appendChild(lbl);
            if (withCd) {
                var mask = document.createElement('div');
                mask.className = 'cd-mask';
                var cdTxt = document.createElement('span');
                cdTxt.className = 'cd-text';
                el.appendChild(mask);
                el.appendChild(cdTxt);
                el._cdMask = mask;
                el._cdText = cdTxt;
            }
            el._lbl = lbl;
            stage.appendChild(el);
            buttons.push(el);
            el.addEventListener('pointerdown', function (e) {
                var current = game();
                if (!current || current.state !== 'playing') {
                    TOUCH.syncControls();
                    return; // 让本次触点继续冒泡，交给菜单处理。
                }
                unlock();
                el.classList.add('hit');
                if (el.setPointerCapture) { el.setPointerCapture(e.pointerId); }
                action();
                e.preventDefault(); e.stopPropagation();
            });
            function up(e) {
                el.classList.remove('hit');
                if (release) { release(); }
                e.preventDefault(); e.stopPropagation();
            }
            el.addEventListener('pointerup', up);
            el.addEventListener('pointercancel', up);
            return el;
        }
        fire = document.createElement('div');
        fire.id = 'btn-fire';
        var fireLbl = document.createElement('span');
        fireLbl.className = 'btn-lbl';
        fireLbl.textContent = '攻';
        fire.appendChild(fireLbl);
        fireKnob = document.createElement('div');
        fireKnob.id = 'fire-knob';
        fire.appendChild(fireKnob);
        stage.appendChild(fire);
        buttons.push(fire);

        function moveFire(e) {
            if (e.pointerId !== fireId) { return; }
            var rect = fire.getBoundingClientRect();
            var odx = e.clientX - fireOriginX, ody = e.clientY - fireOriginY;
            var dragDist = Math.hypot(odx, ody);
            var maxR = rect.width * 0.36;
            var scale = Math.min(1, maxR / Math.max(1, dragDist));
            fireKnob.style.transform = 'translate(calc(-50% + ' + (odx * scale) + 'px), calc(-50% + ' + (ody * scale) + 'px))';
            if (dragDist >= 10) {
                TOUCH.aimVector = [odx / dragDist, ody / dragDist];
            } else {
                TOUCH.aimVector = null;
            }
        }
        fire.addEventListener('pointerdown', function (e) {
            var g = game();
            if (!g || g.state !== 'playing') { TOUCH.syncControls(); return; }
            unlock();
            fireId = e.pointerId;
            fireOriginX = e.clientX;
            fireOriginY = e.clientY;
            TOUCH.shoot = true;
            TOUCH.aim = null;
            aimId = null;
            TOUCH.aimVector = null;
            if (typeof TOUCH.aimAngle !== 'number' && g.player) {
                TOUCH.aimAngle = g.player.aim;
            }
            fire.classList.add('hit');
            if (fire.setPointerCapture) { fire.setPointerCapture(e.pointerId); }
            moveFire(e);
            e.preventDefault(); e.stopPropagation();
        });
        fire.addEventListener('pointermove', function (e) {
            moveFire(e); e.preventDefault(); e.stopPropagation();
        });
        function endFire(e) {
            if (e.pointerId !== fireId) { return; }
            fireId = null;
            fireOriginX = fireOriginY = 0;
            TOUCH.shoot = false;
            TOUCH.aimVector = null;
            fire.classList.remove('hit');
            fireKnob.style.transform = 'translate(-50%, -50%)';
            e.preventDefault(); e.stopPropagation();
        }
        fire.addEventListener('pointerup', endFire);
        fire.addEventListener('pointercancel', endFire);

        var btnDash = button('btn-dash', '冲', function () { TOUCH.dash = true; }, null, true);
        var btnAct = button('btn-act', '交互', function () { TOUCH.act = true; });
        var btnSwap = button('btn-swap', '换', function () { TOUCH.swap = true; });
        var btnSkill = button('btn-skill', '技', function () { TOUCH.skill = true; }, null, true);
        button('btn-menu', '暂停', function () {
            var g = game();
            if (g) { g._keydown('escape'); }
        });

        // 手机端一键全屏按钮：在标题/大厅/局内均可用，帮助浏览器隐藏地址栏并尝试横屏。
        (function setupMobileFullscreen() {
            var isNative = !!(window.Capacitor && typeof window.Capacitor.isNativePlatform === 'function'
                && window.Capacitor.isNativePlatform());
            var isPwa = !!(window.navigator.standalone || (window.matchMedia &&
                (window.matchMedia('(display-mode: fullscreen)').matches ||
                 window.matchMedia('(display-mode: standalone)').matches)));
            var docEl = document.documentElement || {};
            var reqFs = docEl.requestFullscreen || docEl.webkitRequestFullscreen;
            if (isNative || isPwa || typeof reqFs !== 'function') { return; }

            var btnFs = document.createElement('div');
            btnFs.id = 'btn-fs';
            btnFs.style.display = 'flex';
            var fsLbl = document.createElement('span');
            fsLbl.className = 'btn-lbl';
            fsLbl.textContent = '全屏';
            btnFs.appendChild(fsLbl);
            stage.appendChild(btnFs);

            function inFs() {
                return !!(document.fullscreenElement || document.webkitFullscreenElement);
            }
            function syncFsBtn() {
                var active = inFs();
                fsLbl.textContent = active ? '退出' : '全屏';
                btnFs.classList.toggle('is-fs', active);
                window.dispatchEvent(new Event('resize'));
                setTimeout(function () { window.dispatchEvent(new Event('resize')); }, 120);
            }
            function lockLandscape() {
                try {
                    if (screen.orientation && typeof screen.orientation.lock === 'function') {
                        var lp = screen.orientation.lock('landscape');
                        if (lp && typeof lp.catch === 'function') { lp.catch(function () {}); }
                    }
                } catch (_err) { /* ignore */ }
            }
            function toggleFullscreen() {
                if (inFs()) {
                    var exitFs = document.exitFullscreen || document.webkitExitFullscreen;
                    if (typeof exitFs === 'function') {
                        try {
                            var ep = exitFs.call(document);
                            if (ep && typeof ep.catch === 'function') { ep.catch(function () {}); }
                        } catch (_err) { /* ignore */ }
                    }
                    return;
                }
                var ret = null;
                try {
                    ret = reqFs.call(docEl, { navigationUI: 'hide' });
                } catch (_err) {
                    try { ret = reqFs.call(docEl); } catch (_err2) { ret = null; }
                }
                if (ret && typeof ret.then === 'function') {
                    ret.then(function () { lockLandscape(); syncFsBtn(); }).catch(function () {});
                } else {
                    lockLandscape();
                }
            }

            btnFs.addEventListener('pointerdown', function (e) {
                btnFs.classList.add('hit');
                e.stopPropagation();
            });
            function clearFsHit(e) {
                btnFs.classList.remove('hit');
                e.stopPropagation();
            }
            btnFs.addEventListener('pointerup', clearFsHit);
            btnFs.addEventListener('pointercancel', clearFsHit);
            btnFs.addEventListener('click', function (e) {
                e.preventDefault();
                e.stopPropagation();
                unlock();
                toggleFullscreen();
            });
            document.addEventListener('fullscreenchange', syncFsBtn);
            document.addEventListener('webkitfullscreenchange', syncFsBtn);
            syncFsBtn();
        })();

        var lastSnap = {
            show: null, scale: null, opacity: null,
            dashTxt: null, dashPct: null,
            skillTxt: null, skillPct: null,
            swapDim: null, actLabel: null, actConfirm: null
        };
        function applyCd(btn, cd, maxCd, keyTxt, keyPct) {
            var active = cd > 0.05 && maxCd > 0;
            var txt = active ? (cd >= 10 ? String(Math.ceil(cd)) : cd.toFixed(1)) : '';
            var pct = active ? Math.min(100, Math.max(0, Math.round(cd / maxCd * 100))) : 0;
            if (lastSnap[keyTxt] !== txt) {
                lastSnap[keyTxt] = txt;
                btn._cdText.textContent = txt;
                btn.classList.toggle('cooling', active);
            }
            if (lastSnap[keyPct] !== pct) {
                lastSnap[keyPct] = pct;
                btn._cdMask.style.height = pct + '%';
            }
        }
        TOUCH.syncControls = function () {
            var g = game();
            var hud = (g && g.getTouchHudState) ? g.getTouchHudState() : null;
            var playing = !!g && g.state === 'playing' && !(hud && hud.routeOpen);
            var settings = g && g.setting || {};
            var scale = Math.max(0.7, Math.min(1.4,
                Number(settings.button_scale) || 1));
            var opacity = Math.max(0.3, Math.min(1,
                Number(settings.button_opacity) || 0.8));
            if (lastSnap.show !== playing || lastSnap.scale !== scale || lastSnap.opacity !== opacity) {
                lastSnap.show = playing;
                lastSnap.scale = scale;
                lastSnap.opacity = opacity;
                for (var i = 0; i < buttons.length; i++) {
                    buttons[i].style.display = playing ? 'flex' : 'none';
                    buttons[i].style.transform = 'scale(' + scale + ')';
                    buttons[i].style.opacity = String(opacity);
                }
            }
            if (!playing) {
                TOUCH.reset();
                return;
            }
            if (hud) {
                applyCd(btnDash, hud.dashCd, hud.dashMax, 'dashTxt', 'dashPct');
                applyCd(btnSkill, hud.skillCd, hud.skillMax, 'skillTxt', 'skillPct');
                var swapDim = !hud.hasSecondWeapon;
                if (lastSnap.swapDim !== swapDim) {
                    lastSnap.swapDim = swapDim;
                    btnSwap.classList.toggle('dimmed', swapDim);
                }
                if (lastSnap.actLabel !== hud.interactLabel || lastSnap.actConfirm !== hud.interactConfirm) {
                    lastSnap.actLabel = hud.interactLabel;
                    lastSnap.actConfirm = hud.interactConfirm;
                    var hasAct = !!hud.interactLabel;
                    btnAct._lbl.textContent = hud.interactLabel || '交互';
                    btnAct.classList.toggle('idle', !hasAct);
                    btnAct.classList.toggle('ready', hasAct && !hud.interactConfirm);
                    btnAct.classList.toggle('confirm', !!hud.interactConfirm);
                }
            }
        };
        TOUCH.syncControls();
        window.dispatchEvent(new Event('resize'));
        document.addEventListener('gesturestart', function (e) { e.preventDefault(); });
    });
})();
