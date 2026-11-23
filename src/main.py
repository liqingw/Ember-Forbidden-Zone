# -*- coding: utf-8 -*-
"""
陆面过程模拟 Soul Knight Lite —— 程序入口

用法：
    python main.py                 # 正常启动
    python main.py --headless      # 无窗口（自动化测试用，配合 SDL_VIDEODRIVER=dummy）
    python main.py --seed=12345    # 固定随机种子（可复现）
    python main.py --scale=3       # 3 倍窗口
"""
import os
import sys
import time
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def _parse_argv(argv):
    opt = {'headless': False, 'seed': None, 'scale': None, 'noaudio': False,
           'selfcheck': False}
    for a in argv[1:]:
        if a == '--headless':
            opt['headless'] = True
        elif a == '--selfcheck':
            opt['selfcheck'] = True
        elif a == '--noaudio':
            opt['noaudio'] = True
        elif a.startswith('--seed='):
            try:
                opt['seed'] = int(a.split('=', 1)[1])
            except ValueError:
                pass
        elif a.startswith('--scale='):
            try:
                opt['scale'] = max(1, int(a.split('=', 1)[1]))
            except ValueError:
                pass
    return opt


def _selfcheck():
    """打包后自检：验证 exe 能正常加载资源、跑逻辑、出画面。
    结果同时打印并写入 exe 同目录的 selfcheck.log。"""
    import math
    import time
    import traceback

    if getattr(sys, 'frozen', False):
        base = os.path.dirname(os.path.abspath(sys.executable))
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    logp = os.path.join(base, 'selfcheck.log')
    L = []
    code = 0
    t0 = time.time()
    try:
        from sk.game import Game
        t0 = time.time()
        g = Game(headless=True, seed=1234, enable_audio=True)
        init_s = time.time() - t0
        L.append(f'frozen={getattr(sys, "frozen", False)}')
        L.append(f'assets_root={g.assets.root}')
        L.append(f'missing_assets={g.assets.missing}')
        L.append(f'placeholder_keys={sorted(g.assets.placeholder_keys)}')
        L.append(f'font={g.assets._font_path}')
        L.append(f'audio_source={g.audio.source} enabled={g.audio.enabled} '
                 f'sounds={len(g.audio.sounds)}')
        L.append(f'init_seconds={init_s:.2f}')
        g.start_run()
        for i in range(1500):
            g.step(1 / 60.0, {'mx': math.cos(i * 0.05), 'my': math.sin(i * 0.04),
                              'aim': i * 0.06, 'shoot': True,
                              'dash': i % 97 == 0, 'slow': False})
        L.append(f'frames=1500 state={g.state} floor={g.floor} kills={g.kills} '
                 f'coins={g.coins} hp={g.player.hp:.0f} enemies={len(g.enemies)}')
        g._present()
        L.append('present=ok')
        # 关键场景渲染
        for st in ('title', 'help', 'paused', 'gameover', 'victory', 'levelclear'):
            g.state = st
            g.draw()
        L.append('screens=ok')
        problems = []
        if g.assets.missing:
            problems.append(f'素材缺失 {g.assets.missing}')
        if g.assets.placeholder_keys:
            problems.append(f'占位图 {sorted(g.assets.placeholder_keys)}')
        if g.assets._font_path is None:
            problems.append('字体未加载')
        L.append('RESULT=' + ('FAIL ' + '; '.join(problems) if problems else 'PASS'))
        code = 1 if problems else 0
    except Exception:
        L.append('EXCEPTION:\n' + traceback.format_exc())
        L.append('RESULT=FAIL')
        code = 2
    txt = '\n'.join(L)
    try:
        print(txt)
    except Exception:
        pass
    try:
        with open(logp, 'w', encoding='utf-8') as f:
            f.write(txt + '\n')
    except Exception:
        pass
    return code


def _ver():
    try:
        from sk import settings as _S
        return _S.VERSION
    except Exception:
        return '?'


def _log_dir():
    """启动日志目录：优先 exe 同目录（用户看得见），不可写就退到临时目录。"""
    if getattr(sys, 'frozen', False):
        base = os.path.dirname(os.path.abspath(sys.executable))
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    for cand in (base, os.environ.get('TEMP') or '/tmp'):
        try:
            if cand and os.access(cand, os.W_OK):
                return cand
        except Exception:
            continue
    return None


def _boot_log(msg, reset=False):
    """把启动进度写进 boot.log。

    这是"双击没反应"类问题的唯一现场证据 —— 窗口都没出来的时候，
    用户唯一能拿到的信息就是这个文件。
    """
    d = _log_dir()
    if not d:
        return
    p = os.path.join(d, 'boot.log')
    try:
        mode = 'w' if reset else 'a'
        with open(p, mode, encoding='utf-8') as f:
            f.write('[%s] %s\n' % (time.strftime('%H:%M:%S'), msg))
            f.flush()
            # 关键：进程被强杀时缓冲区可能丢数据，必须 fsync 到盘
            try:
                os.fsync(f.fileno())
            except Exception:
                pass
    except Exception:
        pass


def _show_splash(text='正在载入…'):
    """在 main() 最早期抢建一个极小的窗口，先给用户一个"我启动了"的信号。

    必要性：真实启动要初始化 SDL 视频 / 音频 / 加载贴图字体，
    在部分机器上（尤其接了一堆 USB 外设时）可能要好几秒。
    如果这段时间屏幕上什么都没有，用户就会以为双击无效 —— 这正是
    这次 "桌面版双击打不开" 的观感来源。所以：
        只要窗口先亮出来，"没反应" 的投诉就不会再出现。
    """
    try:
        import pygame
        pygame.display.init()
        scr = pygame.display.set_mode((520, 200))
        pygame.display.set_caption('陆面过程模拟')
        try:
            pygame.event.pump()
        except Exception:
            pass
        scr.fill((10, 9, 16))
        # 不依赖字体子集：这个阶段 font 可能还没 init，用几何图形画
        w, h = scr.get_size()
        pygame.draw.rect(scr, (36, 32, 48), (0, h - 34, w, 34))
        pygame.draw.rect(scr, (150, 110, 220), (0, h - 34, int(w * 0.35), 34))
        pygame.draw.circle(scr, (226, 62, 74), (w // 2, 74), 16)
        pygame.draw.circle(scr, (255, 138, 146), (w // 2 - 5, 69), 5)
        for i in range(3):
            pygame.draw.rect(scr, (150, 110, 220),
                             (w // 2 - 60 + i * 44, 118, 32, 6))
        try:
            pygame.display.flip()
        except Exception:
            pass
        return scr
    except Exception:
        return None


def _crash_dialog(title, detail):
    """崩溃时弹一个原生消息框，并把详情写进 boot.log。

    没有这个的话，`--noconsole` 打包出来的 exe 一崩就是"双击没反应"，
    用户完全拿不到任何线索。有了它至少能看到一句人话。
    """
    _boot_log('!!!! %s !!!!\n%s' % (title, detail))
    try:
        import ctypes
        d = _log_dir() or ''
        msg = ('%s\n\n详细信息已写入:\n%s\\boot.log\n\n%s'
               % (title, d, detail.strip().splitlines()[-1] if detail.strip()
                  else ''))
        ctypes.windll.user32.MessageBoxW(None, msg, '陆面过程模拟 · 启动失败',
                                         0x10)
    except Exception:
        pass


def main(argv=None):
    argv = list(sys.argv if argv is None else argv)
    opt = _parse_argv(argv)

    if opt['headless'] or opt['selfcheck']:
        os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
        os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')

    if opt['selfcheck']:
        return _selfcheck()

    _boot_log('---- 启动 v%s ----' % _ver(), reset=True)
    _boot_log('frozen=%s  argv=%s' % (getattr(sys, 'frozen', False), argv))
    _boot_log('python=%s' % sys.version.split()[0])

    # 有窗口的情况下，先把窗口亮出来
    if not opt['headless']:
        _show_splash()
        _boot_log('splash 已显示')

    import time as _time
    _t = _time.time()
    try:
        from sk.game import Game
    except Exception:
        _boot_log('!! import Game 失败\n' + traceback.format_exc())
        _crash_dialog('导入游戏模块失败', traceback.format_exc())
        return 3
    _boot_log('import Game 完成 %.3fs' % (_time.time() - _t))

    _t = _time.time()
    try:
        game = Game(headless=opt['headless'], seed=opt['seed'],
                    enable_audio=not opt['noaudio'], scale=opt['scale'])
    except Exception:
        _boot_log('!! Game 构造失败\n' + traceback.format_exc())
        _crash_dialog('初始化失败', traceback.format_exc())
        return 3
    _boot_log('Game 构造完成 %.3fs  window=%s scale=%s'
              % (_time.time() - _t,
                 getattr(game.window, 'get_size', lambda: None)(),
                 game.scale))
    _boot_log('assets.missing=%s placeholder=%s'
              % (game.assets.missing, sorted(game.assets.placeholder_keys)))

    if not opt['headless']:
        # 心跳：进入主循环后立刻记一笔，证明"窗口真的出来了、开始渲染了"。
        # 排查"双击没反应"时，boot.log 的最后一行的下一步就是卡住的地方。
        game._boot_heartbeat = lambda: _boot_log('已进入主循环，画面开始渲染')
        try:
            game.draw()
            game._present()
            _boot_log('首帧渲染完成，窗口应已可见')
        except Exception:
            _boot_log('!! 首帧渲染失败\n' + traceback.format_exc())

    if opt['headless']:
        # 无头模式：跑到玩家死亡或超时为止（供冒烟测试）
        steps = 0
        game.start_run()
        import math
        inps = {'mx': 1, 'my': 0, 'aim': 0.0, 'shoot': True, 'dash': False, 'slow': False}
        while game.running and steps < 7200:
            inps['aim'] = (steps * 0.07) % (2 * math.pi)
            inps['mx'] = math.cos(steps * 0.02)
            inps['my'] = math.sin(steps * 0.03)
            game.step(1.0 / 60.0, inps)
            steps += 1
        print(f'[headless] steps={steps} state={game.state} kills={game.kills} '
              f'coins={game.coins} floor={game.floor}')
        return 0

    try:
        hb = getattr(game, '_boot_heartbeat', None)
        if hb is not None:
            hb()
        game.run()
    except Exception:
        _crash_dialog('运行中发生错误', traceback.format_exc())
        return 3
    _boot_log('正常退出')
    return 0


if __name__ == '__main__':
    sys.exit(main())
