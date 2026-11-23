# -*- coding: utf-8 -*-
"""音效。

优先加载 assets/sfx/*.wav（构建期预渲染，运行时零依赖）；
若 WAV 缺失且运行环境有 numpy，则现场合成兜底；
再不行就静默无声 —— 任何失败都不会影响游戏运行。
"""
import logging
import math
import os

import pygame

_logger = logging.getLogger('sk.audio')
if not _logger.handlers:
    _logger.addHandler(logging.NullHandler())
_logged_audio_exc = set()


def _log_audio_exc(tag, exc, detail=''):
    try:
        key = (tag, type(exc).__name__, str(detail))
        if key in _logged_audio_exc:
            return
        if len(_logged_audio_exc) >= 128:
            _logged_audio_exc.clear()
        _logged_audio_exc.add(key)
        _logger.warning('[%s] %s (%s: %s)', tag, detail, type(exc).__name__, exc)
    except Exception:
        pass

RATE = 44100

SFX_NAMES = [
    'shoot', 'shoot_heavy', 'laser', 'hit', 'hurt', 'explode', 'enemy_die',
    'boss_die', 'coin', 'heart', 'energy', 'door', 'lock', 'dash', 'pickup',
    'ui', 'ui_big', 'no_energy', 'buy', 'break', 'level_up', 'game_over',
    'victory', 'man_what_can_i_say',
    'rad_star', 'rad_nova', 'rad_chrono', 'rad_life', 'rad_prism', 'rad_orbit',
]

_OK = True
try:
    import numpy as np
except Exception:                                    # pragma: no cover
    np = None
    _OK = False


# ------------------------------------------------------------ 波形合成
def _env(n, attack=0.01, decay=1.0, p=2.0):
    t = np.linspace(0.0, 1.0, n, endpoint=False)
    a = np.clip(t / max(1e-4, attack), 0.0, 1.0)
    return a * ((1.0 - t) ** p) * decay


def _osc(freq, n, wave='square', sweep=1.0):
    t = np.arange(n) / RATE
    if sweep != 1.0:
        k = freq * (sweep ** (t * 8.0))
        phase = 2 * math.pi * np.cumsum(k) / RATE
    else:
        phase = 2 * math.pi * freq * t
    if wave == 'square':
        return np.sign(np.sin(phase))
    if wave == 'saw':
        return 2.0 * ((phase / (2 * math.pi)) % 1.0) - 1.0
    if wave == 'tri':
        return 2.0 * np.abs(2.0 * ((phase / (2 * math.pi)) % 1.0) - 1.0) - 1.0
    return np.sin(phase)


def _noise(n, seed=0):
    return np.random.RandomState(seed).uniform(-1.0, 1.0, n)


def _mix(*parts):
    n = max(len(p) for p in parts)
    out = np.zeros(n, np.float32)
    for p in parts:
        out[:len(p)] += np.asarray(p, np.float32)
    m = float(np.max(np.abs(out))) or 1.0
    return out / m


def _tone(freq, dur, wave='square', vol=0.5, sweep=1.0, p=2.0, attack=0.01):
    n = max(8, int(RATE * dur))
    return (_osc(freq, n, wave, sweep) * _env(n, attack, vol, p)).astype(np.float32)


def _bang(dur, vol=0.6, lp=0.35, seed=1, p=2.4):
    n = max(8, int(RATE * dur))
    x = _noise(n, seed)
    a = int(max(1, n * lp))
    if a > 1:
        x = np.convolve(x, np.ones(a, np.float32) / a, mode='same')
    return (x * _env(n, 0.002, vol, p)).astype(np.float32)


def _short(dur, amp=0.16):
    n = int(RATE * dur)
    return _noise(n, 3)[:n] * amp


def synth(name):
    """合成单个音效，返回 float32 单声道波形；无 numpy 时返回 None"""
    if not _OK:
        return None
    table = {
        'shoot':       lambda: _mix(_tone(880, 0.07, 'square', 0.34, sweep=0.45, p=3.0),
                                    _short(0.07)),
        'shoot_heavy': lambda: _mix(_tone(220, 0.16, 'saw', 0.42, sweep=0.4, p=2.2),
                                    _bang(0.1, 0.25, 0.5, 5)),
        'laser':       lambda: _tone(1500, 0.12, 'tri', 0.34, sweep=0.25, p=2.6),
        'hit':         lambda: _bang(0.07, 0.42, 0.6, 7, p=3.0),
        'hurt':        lambda: _mix(_tone(180, 0.20, 'saw', 0.42, sweep=0.5, p=1.8),
                                    _bang(0.1, 0.3, 0.5, 11)),
        'explode':     lambda: _mix(_bang(0.45, 0.85, 0.16, 13, p=1.8),
                                    _tone(70, 0.4, 'sine', 0.5, sweep=0.6, p=1.5)),
        'enemy_die':   lambda: _mix(_tone(420, 0.22, 'square', 0.32, sweep=0.35, p=2.0),
                                    _bang(0.14, 0.35, 0.4, 17)),
        'boss_die':    lambda: _mix(_bang(0.9, 0.9, 0.12, 19, p=1.4),
                                    _tone(90, 0.9, 'saw', 0.5, sweep=0.4, p=1.2)),
        'coin':        lambda: _mix(_tone(1180, 0.06, 'square', 0.3, p=3.0),
                                    _tone(1760, 0.09, 'square', 0.24, p=3.2)),
        'heart':       lambda: _mix(_tone(660, 0.1, 'tri', 0.34, p=2.4),
                                    _tone(990, 0.16, 'tri', 0.3, p=2.0)),
        'energy':      lambda: _tone(1320, 0.14, 'tri', 0.3, sweep=1.9, p=2.4),
        'door':        lambda: _mix(_tone(150, 0.3, 'saw', 0.34, sweep=1.9, p=1.6),
                                    _short(0.3, 0.12)),
        'lock':        lambda: _tone(120, 0.18, 'square', 0.34, sweep=1.7, p=2.0),
        'dash':        lambda: _tone(520, 0.13, 'tri', 0.26, sweep=2.6, p=2.8),
        'pickup':      lambda: _mix(_tone(880, 0.07, 'square', 0.28, p=3.0),
                                    _tone(1320, 0.11, 'square', 0.24, p=2.8)),
        'ui':          lambda: _tone(760, 0.05, 'square', 0.26, p=3.4),
        'ui_big':      lambda: _mix(_tone(600, 0.09, 'square', 0.3, p=2.6),
                                    _tone(900, 0.14, 'square', 0.26, p=2.4)),
        'no_energy':   lambda: _tone(150, 0.07, 'square', 0.3, p=3.4),
        'buy':         lambda: _mix(_tone(700, 0.08, 'square', 0.3, p=2.8),
                                    _tone(1050, 0.12, 'square', 0.26, p=2.6),
                                    _tone(1400, 0.18, 'tri', 0.22, p=2.2)),
        'break':       lambda: _mix(_bang(0.16, 0.5, 0.55, 29, p=2.4),
                                    _tone(320, 0.1, 'square', 0.22, sweep=0.6, p=2.6)),
        'level_up':    lambda: _mix(_tone(523, 0.12, 'square', 0.3, p=2.6),
                                    _tone(659, 0.12, 'square', 0.3, p=2.6),
                                    _tone(784, 0.26, 'square', 0.3, p=2.0)),
        'game_over':   lambda: _mix(_tone(300, 0.5, 'tri', 0.4, sweep=0.35, p=1.3),
                                    _tone(200, 0.7, 'saw', 0.3, sweep=0.3, p=1.1)),
        'victory':     lambda: _mix(_tone(659, 0.14, 'square', 0.3, p=2.4),
                                    _tone(784, 0.14, 'square', 0.3, p=2.4),
                                    _tone(988, 0.34, 'square', 0.32, p=1.8)),
        'rad_star':    lambda: _mix(_tone(1290, .20, 'tri', .42, sweep=.68),
                                    _tone(1935, .12, 'sine', .22, sweep=1.5)),
        'rad_nova':    lambda: _mix(_tone(360, .31, 'saw', .42, sweep=.48),
                                    _bang(.26, .42, .22, 61)),
        'rad_chrono':  lambda: _mix(_tone(720, .24, 'tri', .42, sweep=.35),
                                    _tone(1440, .15, 'sine', .2, sweep=.7)),
        'rad_life':    lambda: _mix(_tone(520, .13, 'sine', .38, sweep=1.6),
                                    _tone(780, .21, 'tri', .25, sweep=1.3)),
        'rad_prism':   lambda: _mix(_tone(1680, .19, 'square', .35, sweep=.72),
                                    _tone(2240, .10, 'tri', .25, sweep=1.2)),
        'rad_orbit':   lambda: _mix(_tone(180, .28, 'saw', .38, sweep=1.45),
                                    _tone(90, .33, 'sine', .25, sweep=.6)),
    }
    fn = table.get(name)
    if fn is None:
        return None
    try:
        return np.asarray(fn(), np.float32)
    except Exception:
        return None


# ------------------------------------------------------------ 运行期
class Audio:
    def __init__(self, enable=True, sfx_dir=None):
        self.enabled = False
        self.sounds = {}
        self.sfx_dir = sfx_dir
        self.source = 'off'
        if not enable:
            return
        try:
            if pygame.mixer.get_init() is None:
                pygame.mixer.init(frequency=RATE, size=-16, channels=2, buffer=512)
            self._build()
            self.enabled = bool(self.sounds)
        except Exception:
            self.enabled = False

    def _wav_path(self, name):
        if not self.sfx_dir:
            return None
        p = os.path.join(self.sfx_dir, name + '.wav')
        return p if os.path.isfile(p) else None

    def _to_sound(self, mono):
        try:
            ch = pygame.mixer.get_init()[2]
            arr = np.repeat(mono.reshape(-1, 1), 2, axis=1) if ch >= 2 else mono
            data = np.ascontiguousarray((np.clip(arr, -1, 1) * 32767).astype(np.int16))
            return pygame.sndarray.make_sound(data)
        except Exception:
            return None

    def _build(self):
        wav_ok = synth_ok = 0
        for name in SFX_NAMES:
            sd = None
            p = self._wav_path(name)
            if p:
                try:
                    sd = pygame.mixer.Sound(p)
                    wav_ok += 1
                except Exception as exc:
                    _log_audio_exc('audio.wav', exc, name)
                    sd = None
            if sd is None:
                mono = synth(name)
                if mono is not None:
                    sd = self._to_sound(mono)
                    if sd is not None:
                        synth_ok += 1
            if sd is not None:
                try:
                    sd.set_volume(0.55)
                except Exception:
                    pass
                self.sounds[name] = sd
        if wav_ok and not synth_ok:
            self.source = 'wav'
        elif synth_ok and not wav_ok:
            self.source = 'synth'
        elif wav_ok and synth_ok:
            self.source = 'wav+synth'
        else:
            self.source = 'off'

    def play(self, name, vol=1.0):
        if not self.enabled:
            return
        s = self.sounds.get(name)
        if s is None:
            return
        try:
            s.set_volume(0.55 * max(0.0, min(1.5, vol)))
            s.play()
        except Exception as exc:
            _log_audio_exc('audio.play', exc, name)

    def set_enabled(self, on):
        """显式开关音效（需求 11：默认关闭，玩家手动打开）。"""
        self.enabled = bool(on) and bool(self.sounds)
        return self.enabled

    def toggle(self):
        return self.set_enabled(not self.enabled)


# ================================================================ 音乐（需求 11）
class Music:
    """程序合成的循环 BGM。

    不依赖任何外部音频文件 —— 用音符序列现场合成为一段可无缝循环的
    波形，再用 pygame.Sound 循环播放（比 mixer.music 更适合内存波形）。

    默认**关闭**（需求 11），玩家在设置里打开才播。
    曲目按场景切换：越深处越低沉、越紧张（与叙事"污染入侵"呼应）。
    """

    # 小调音阶（半音偏移），让曲子天然带点压抑感
    SCALE = [0, 2, 3, 5, 7, 8, 10, 12]
    BASE = 220.0            # A3

    def __init__(self, enable=False):
        self.enabled = False
        self.sound = None
        self.cur = None
        self.vol = 0.28
        if not enable:
            return
        try:
            if pygame.mixer.get_init() is None:
                pygame.mixer.init(frequency=RATE, size=-16, channels=2,
                                  buffer=512)
            self.enabled = True
        except Exception:
            self.enabled = False

    def _note(self, semi, dur, vol=0.5, wave='tri'):
        f = self.BASE * (2.0 ** (semi / 12.0))
        return _tone(f, dur, wave, vol, p=1.6, attack=0.02)

    def build(self, mood=0):
        """按 mood(0..3) 合成一段 ~8 秒的循环。mood 越大越暗。"""
        if not _OK:
            return None
        try:
            import numpy as _np
            seqs = [
                [0, 4, 7, 4, 0, 4, 7, 9],          # 平和
                [0, 3, 7, 3, 0, 3, 8, 7],          # 微忧
                [0, 3, 5, 3, -1, 3, 5, 7],         # 紧张
                [-5, -1, 2, -1, -5, -1, 2, 3],     # 压抑
            ]
            seq = seqs[max(0, min(len(seqs) - 1, int(mood)))]
            parts = []
            beat = 0.42
            for i, s in enumerate(seq):
                parts.append(self._note(s, beat * 0.92, 0.34, 'tri'))
                # 低八度贝斯，每两拍一次
                if i % 2 == 0:
                    parts.append(self._note(s - 12, beat * 2.0, 0.22, 'sine'))
            # 拼成一整条
            total = int(sum(len(p) for p in parts) + RATE * 0.3)
            out = _np.zeros(total, _np.float32)
            cur = 0
            for p in parts:
                out[cur:cur + len(p)] += p
                cur += len(p)
            # 首尾交叉淡化，循环不爆音
            fade = int(RATE * 0.25)
            if total > fade * 2:
                for i in range(fade):
                    k = i / float(fade)
                    out[i] *= k
                    out[total - 1 - i] *= k
            m = float(_np.max(_np.abs(out))) or 1.0
            return (out / m * 0.9).astype(_np.float32)
        except Exception:
            return None

    def play(self, mood=0, force=False):
        if not self.enabled:
            return False
        if self.cur == mood and not force:
            return True
        try:
            if self.sound is not None:
                self.sound.stop()
            mono = self.build(mood)
            if mono is None:
                return False
            ch = pygame.mixer.get_init()[2]
            arr = mono.reshape(-1, 1)
            if ch >= 2:
                import numpy as _np
                arr = _np.repeat(arr, 2, axis=1)
            import numpy as _np
            data = _np.ascontiguousarray(
                (_np.clip(arr, -1, 1) * 32767).astype(_np.int16))
            self.sound = pygame.sndarray.make_sound(data)
            self.sound.set_volume(self.vol)
            self.sound.play(loops=-1)
            self.cur = mood
            return True
        except Exception:
            return False

    def stop(self):
        try:
            if self.sound is not None:
                self.sound.stop()
        except Exception:
            pass
        self.cur = None

    def set_enabled(self, on, mood=0):
        self.enabled = bool(on)
        if not self.enabled:
            self.stop()
        else:
            self.play(mood, force=True)
        return self.enabled


# ================================================================ 震动（需求 11）
class Vibrator:
    """震动模块。

    桌面端用 Windows 的 XInput（ctypes，无需额外依赖）——但大部分台式机
    没有手柄，所以这里**只做"接口存在 + 手机端 Web 端生效"**：
      · 桌面：尝试调用 SDL 的 joystick rumble（我们没 init joystick，
        所以基本是 no-op），失败即静默；
      · 网页/手机：由前端 game.js 调 navigator.vibrate() 实现。
    这样接口统一，桌面不会报错，手机上真能震。
    """

    def __init__(self, enable=False):
        self.enabled = bool(enable)
        self._warned = False

    def set_enabled(self, on):
        self.enabled = bool(on)
        return self.enabled

    def buzz(self, ms=60, strength=0.6):
        if not self.enabled:
            return False
        try:
            # 尝试通过已有的 SDL 手柄震动（多数机器上会安静失败）
            if not pygame.joystick.get_init():
                return False
            n = pygame.joystick.get_count()
            if n <= 0:
                return False
            js = pygame.joystick.Joystick(0)
            if not js.get_init():
                js.init()
            try:
                js.rumble(0.0, float(strength), int(ms))
            except Exception:
                try:
                    js.rumble(float(strength), float(strength), int(ms))
                except Exception:
                    return False
            return True
        except Exception:
            return False
