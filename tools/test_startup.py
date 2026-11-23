# -*- coding: utf-8 -*-
"""启动路径回归测试：保证"双击能出画面"这件事不再悄悄坏掉。

背景（为什么需要这个文件）：
    原来的 `--selfcheck` 用 SDL **dummy** 驱动跑，把视频/音频/手柄全部跳过，
    于是一个"真实启动要卡 60 秒"的致命 bug 长期被掩盖 —— 自检永远 PASS。
    本文件专门验证"真实启动路径"，分两档：

      A 档（纯静态，永远可跑）：boot 模块的导入完整性与日志写入
      B 档（真实驱动，可能需要窗口）：用真 SDL 驱动跑完整启动管线

运行：
    python tools/test_startup.py          # A 档 + B 档（B 档会短暂开窗口）
    python tools/test_startup.py --no-win # 只跑 A 档（CI / 无显示环境）
"""
import ast
import glob
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'src'))

PASS = []
FAIL = []


def check(ok, label):
    (PASS if ok else FAIL).append(label)
    print(('   OK  ' if ok else '   XX  ') + label)
    return ok


def _strip_comments_and_docstrings(src):
    """去掉注释与 docstring，只留可执行代码。

    必要性：我们在注释/docstring 里写了大量"pygame.init() 会卡 60 秒"的
    说明文字，如果按纯文本匹配，这些解释本身会被误判成真的调用了。
    """
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef,
                             ast.ClassDef, ast.Module)):
            if (node.body and isinstance(node.body[0], ast.Expr)
                    and isinstance(node.body[0].value, ast.Constant)
                    and isinstance(node.body[0].value.value, str)):
                node.body[0].value.value = ''    # 清空 docstring
    return ast.unparse(tree)


# ============================================================ A 档：静态
def a_static():
    print('\n=== A 启动路径静态检查 ===')

    # A1 关键陷阱：main.py 里若用了模块级 time 却没在顶层 import，
    #    _boot_log 会静默抛 NameError 并被 except 吃掉 —— 日志永远 0 字节。
    src = open(os.path.join(ROOT, 'src', 'main.py'), encoding='utf-8').read()
    tree = ast.parse(src)
    top_imports = set()
    for node in tree.body:
        if isinstance(node, ast.Import):
            for a in node.names:
                top_imports.add((a.asname or a.name).split('.')[0])
        elif isinstance(node, ast.ImportFrom):
            for a in node.names:
                top_imports.add(a.asname or a.name)
    check('time' in top_imports,
          'A1 main.py 顶层 import time（否则 _boot_log 静默失效）')
    check('os' in top_imports, 'A2 main.py 顶层 import os')
    check('traceback' in top_imports, 'A3 main.py 顶层 import traceback')

    # A4 绝不能再调用 pygame.init()（会连带初始化 joystick，本机要卡 60s）
    bad = []
    for p in glob.glob(os.path.join(ROOT, 'src', '**', '*.py'), recursive=True):
        try:
            code = _strip_comments_and_docstrings(
                open(p, encoding='utf-8').read())
        except Exception:
            continue
        if 'pygame.init()' in code:
            bad.append(os.path.relpath(p, ROOT))
    check(not bad,
          'A4 src/ 内不存在 pygame.init() 调用（%s）' % (bad or '无'))

    # A5/A6 _boot_pygame 存在，且绝不初始化 joystick
    from sk.game import _boot_pygame
    check(callable(_boot_pygame), 'A5 _boot_pygame 可调用')
    gcode = _strip_comments_and_docstrings(
        open(os.path.join(ROOT, 'src', 'sk', 'game.py'),
             encoding='utf-8').read())
    body = gcode.split('def _boot_pygame')[1].split('\ndef ')[0]
    check('joystick.init' not in body,
          'A6 _boot_pygame 里没有 joystick.init 调用')
    check('display.init' in body and 'font.init' in body,
          'A7 _boot_pygame 里确实初始化了 display 与 font')

    # A8 启动日志必须真的写得进去
    import main as M
    d = M._log_dir()
    check(bool(d), 'A8 _log_dir() 返回可写目录（%s）' % d)
    if d:
        p = os.path.join(d, 'boot.log')
        M._boot_log('__regression_probe__', reset=True)
        txt = open(p, encoding='utf-8').read()
        check('__regression_probe__' in txt,
              'A9 boot.log 实际写入成功（%d 字节）' % os.path.getsize(p))

    # A10 异常必须能被 crash 处理看到
    try:
        raise ValueError('probe')
    except Exception:
        import traceback as tb
        check('ValueError' in tb.format_exc(), 'A10 traceback 可捕获异常详情')


# ============================================================ B 档：真实驱动
def b_real(no_window=False):
    print('\n=== B 真实驱动启动管线 ===')
    import pygame
    from sk.game import _boot_pygame, Game

    t = time.time()
    _boot_pygame(no_window)
    boot_s = time.time() - t
    check(boot_s < 8.0,
          'B1 _boot_pygame 耗时 %.2fs < 8s（joystick 未初始化）' % boot_s)
    check(not pygame.joystick.get_init(),
          'B2 joystick 子系统未被初始化')
    check(pygame.display.get_init(), 'B3 display 已初始化')
    check(pygame.font.get_init(), 'B4 font 已初始化')

    if no_window:
        print('   --  --no-win：跳过窗口相关检查')
        return

    t = time.time()
    win = pygame.display.set_mode((640, 360))
    check(win.get_size() == (640, 360), 'B5 set_mode 成功 640x360')
    check(time.time() - t < 5.0, 'B6 set_mode 耗时 %.2fs < 5s' % (time.time() - t))

    t = time.time()
    g = Game(headless=False, seed=1234, enable_audio=False, scale=1)
    check(g.window is not None, 'B7 Game 构造后存在真实窗口')
    check(time.time() - t < 6.0, 'B8 Game 构造 %.2fs < 6s' % (time.time() - t))

    # B9 全界面渲染不得抛异常 —— 覆盖"某个状态一进就崩"的情况
    g.start_run()
    errs = []
    for st in ('title', 'help', 'lobby', 'paused', 'gameover', 'victory',
               'levelclear', 'talent', 'story', 'playing'):
        try:
            g.state = st
            g.draw()
            g._present()
        except Exception as e:
            errs.append('%s:%s' % (st, e))
    check(not errs, 'B9 全部界面渲染无异常（%s）' % (errs or '无'))

    # B10 天赋空候选表不得越界（曾经的 IndexError）
    try:
        g.state = 'talent'
        g.pending_talents = None
        g.draw()
        check(True, 'B10 talent 状态空候选表可安全渲染')
    except Exception as e:
        check(False, 'B10 talent 空候选表渲染抛异常: %s' % e)

    # B11 事件泵存活（窗口真的在收消息）
    try:
        for _ in range(12):
            pygame.event.pump()
            g.update(1.0 / 60.0)
            g.draw()
            g._present()
            pygame.time.wait(16)
        check(True, 'B11 事件泵 + 渲染循环 12 帧无异常')
    except Exception as e:
        check(False, 'B11 事件泵异常: %s' % e)

    try:
        pygame.mouse.set_visible(True)
        pygame.display.quit()
        pygame.quit()
    except Exception:
        pass


def main():
    no_win = '--no-win' in sys.argv
    a_static()
    if not no_win:
        try:
            b_real(False)
        except Exception as e:
            import traceback
            traceback.print_exc()
            check(False, 'B 档真实驱动测试崩溃: %s' % e)
    else:
        print('\n(--no-win：跳过 B 档)')

    print('\n' + '=' * 62)
    if FAIL:
        print('失败项（%d）：' % len(FAIL))
        for f in FAIL:
            print('   x', f)
    print('结果：%d/%d 项通过' % (len(PASS), len(PASS) + len(FAIL)))
    print('=' * 62)
    return 1 if FAIL else 0


if __name__ == '__main__':
    sys.exit(main())
