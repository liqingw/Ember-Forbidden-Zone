# -*- coding: utf-8 -*-
"""启动探针：用**真实**视频驱动跑一遍启动管线，逐步打点日志。

为什么要它：
    `--selfcheck` 走的是 SDL dummy driver，绕过了一切真实窗口/显卡路径，
    所以"exe 能自检通过"根本不能证明"双击能出画面"。
    真实启动会碰到：SDL 视频驱动初始化、显卡/OpenGL 选择、音频设备打开、
    DPI 缩放、多显示器坐标……这些在 dummy 下全是 no-op。

用法：
    python tools/startup_probe.py              # 立刻建窗口，1 秒后自动退出
    python tools/startup_probe.py --hold=5     # 建窗口后停 5 秒
    python tools/startup_probe.py --no-window  # 跳过建窗口，只测初始化

产物：
    _tmp/startup_probe.log   每一步的耗时与异常
"""
import os
import sys
import time
import traceback

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'src'))

LOG = os.path.join(ROOT, '_tmp', 'startup_probe.log')
os.makedirs(os.path.dirname(LOG), exist_ok=True)


class Probe:
    def __init__(self):
        self.t0 = time.time()
        self.lines = []

    def mark(self, tag, extra=''):
        dt = time.time() - self.t0
        line = '[%7.3fs] %-34s %s' % (dt, tag, extra)
        self.lines.append(line)
        print(line, flush=True)

    def fail(self, tag, exc):
        self.mark(tag, '<<< 异常: %s: %s' % (type(exc).__name__, exc))
        self.lines.append(traceback.format_exc())

    def flush(self):
        try:
            with open(LOG, 'w', encoding='utf-8') as f:
                f.write('\n'.join(self.lines) + '\n')
        except Exception:
            pass


def main():
    hold = 1.0
    do_window = True
    for a in sys.argv[1:]:
        if a.startswith('--hold='):
            hold = float(a.split('=', 1)[1])
        elif a == '--no-window':
            do_window = False

    p = Probe()
    p.mark('probe:start', 'argv=%s' % (sys.argv[1:],))
    p.mark('probe:python', sys.version.split()[0])
    p.mark('probe:frozen', str(getattr(sys, 'frozen', False)))
    p.mark('probe:cwd', os.getcwd())
    p.mark('probe:sdl_video', os.environ.get('SDL_VIDEODRIVER', '(未设置)'))
    p.mark('probe:sdl_audio', os.environ.get('SDL_AUDIODRIVER', '(未设置)'))

    try:
        import pygame
        p.mark('import:pygame', pygame.version.ver)
    except Exception as e:
        p.fail('import:pygame', e)
        p.flush()
        return 2

    try:
        t = time.time()
        from sk.game import _boot_pygame
        _boot_pygame(False)
        p.mark('_boot_pygame(手动子系统)',
               '%.3fs video=%s audio=%s font=%s joy=%s' % (
                   time.time() - t, pygame.display.get_init(),
                   pygame.mixer.get_init() is not None,
                   pygame.font.get_init(),
                   pygame.joystick.get_init()))
    except Exception as e:
        p.fail('_boot_pygame', e)

    try:
        info = pygame.display.Info()
        p.mark('display.Info', 'driver=%s current=%dx%d desktop=%dx%d' % (
            pygame.display.get_driver(), info.current_w, info.current_h,
            info.current_w, info.current_h))
    except Exception as e:
        p.fail('display.Info', e)

    try:
        p.mark('display.list_modes',
               str(pygame.display.list_modes()[:4]) + ' ...')
    except Exception as e:
        p.fail('display.list_modes', e)

    if do_window:
        try:
            win = pygame.display.set_mode((640, 360))
            p.mark('set_mode(640x360)', 'ok size=%s flags=%s' % (
                win.get_size(), win.get_flags()))
        except Exception as e:
            p.fail('set_mode(640x360)', e)

    try:
        from sk.game import Game
        p.mark('import:Game', 'ok')
    except Exception as e:
        p.fail('import:Game', e)
        p.flush()
        return 2

    t = time.time()
    try:
        g = Game(headless=False, seed=1234, enable_audio=True, scale=2)
        p.mark('Game(headless=False)', '%.2fs  window=%s scale=%d' % (
            time.time() - t, g.window and g.window.get_size(), g.scale))
    except Exception as e:
        p.fail('Game(headless=False)', e)
        p.flush()
        return 2

    p.mark('assets', 'root=%s' % (g.assets.root,))
    p.mark('assets.missing', str(g.assets.missing))
    p.mark('assets.placeholder', str(sorted(g.assets.placeholder_keys)))
    p.mark('font', str(g.assets._font_path))
    p.mark('audio', 'source=%s enabled=%s sounds=%d' % (
        g.audio.source, g.audio.enabled, len(g.audio.sounds)))

    # 跑几帧 + 出画面，这是"双击没内容"最可能的失败点
    t = time.time()
    try:
        g.start_run()
        p.mark('start_run', 'state=%s' % g.state)
        for i in range(60):
            g.step(1.0 / 60.0, {'mx': 0.5, 'my': 0.0, 'aim': 0.3,
                                'shoot': True, 'dash': False, 'slow': False})
        p.mark('step x60', '%.2fs state=%s' % (time.time() - t, g.state))
    except Exception as e:
        p.fail('step x60', e)

    try:
        g.draw()
        g._present()
        p.mark('draw + _present', 'ok')
    except Exception as e:
        p.fail('draw + _present', e)

    try:
        for st in ('title', 'help', 'lobby', 'paused', 'gameover',
                   'victory', 'levelclear', 'talent', 'story'):
            g.state = st
            g.draw()
            g._present()
        p.mark('all screens', 'ok')
    except Exception as e:
        p.fail('all screens', e)

    # 主循环式泵事件：验证窗口消息队列真的在跑（"没响应"类问题在这里暴露）
    t = time.time()
    try:
        end = time.time() + max(0.2, hold)
        n = 0
        while time.time() < end:
            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    p.mark('event:pump', 'QUIT 收到（窗口被关闭）')
                    end = 0
                    break
            g.update(1.0 / 60.0)
            g.draw()
            g._present()
            pygame.display.set_caption('%s  v%s  [probe %d]' % (
                __import__('sk.settings', fromlist=['x']).GAME_TITLE,
                __import__('sk.settings', fromlist=['x']).VERSION, n))
            n += 1
            pygame.time.wait(16)
        p.mark('event pump', '%d 帧 / %.2fs  窗口存活=%s' % (
            n, time.time() - t, pygame.display.get_surface() is not None))
    except Exception as e:
        p.fail('event pump', e)

    try:
        pygame.mouse.set_visible(True)
    except Exception:
        pass
    try:
        pygame.display.set_caption('probe done - closing')
        pygame.display.quit()
        pygame.quit()
        p.mark('cleanup', 'ok')
    except Exception as e:
        p.fail('cleanup', e)

    p.mark('probe:end', '所有步骤走完，没有崩溃')
    p.flush()
    print('\n日志 ->', LOG)
    return 0


if __name__ == '__main__':
    sys.exit(main())
