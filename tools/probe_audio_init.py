# -*- coding: utf-8 -*-
"""逐子系统计时 pygame.init()，找出启动慢在哪一步。

背景：真实启动探针发现 pygame.init() 耗时 60.7 秒，
而 --selfcheck（dummy 驱动）完全看不到这个，因为混音器/显示都被跳过了。
"""
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'src'))

import pygame  # noqa: E402


def tick(tag, fn):
    t = time.time()
    try:
        r = fn()
        dt = time.time() - t
        print('[%7.3fs] %-28s -> %s' % (dt, tag, r))
        return dt
    except Exception as e:
        dt = time.time() - t
        print('[%7.3fs] %-28s !! %s: %s' % (dt, tag, type(e).__name__, e))
        return dt


print('--- 逐子系统计时 ---')
tick('display.init', pygame.display.init)
tick('font.init', pygame.font.init)
tick('mixer.pre_init(default)', lambda: pygame.mixer.pre_init())
tick('mixer.init(default 44100/16/2)', pygame.mixer.init)
print('    mixer.get_init =', pygame.mixer.get_init())

# 再试一次：如果上面改了参数，这里测"冷启动"的实际代价
try:
    pygame.mixer.quit()
except Exception:
    pass
tick('mixer.quit', lambda: None)
for freq, size, ch, buf in ((44100, -16, 2, 512),
                            (22050, -16, 2, 512),
                            (44100, -16, 1, 1024)):
    try:
        pygame.mixer.quit()
    except Exception:
        pass
    print('    --- 参数 %s ---' % ((freq, size, ch, buf),))
    tick('  pre_init+init', lambda f=freq, s=size, c=ch,
         b=buf: (pygame.mixer.pre_init(f, s, c, b), pygame.mixer.init()))

print()
print('--- pygame.init 整体（重新来一遍） ---')
pygame.quit()
t = time.time()
pygame.init()
print('[%7.3fs] pygame.init 总计' % (time.time() - t))
print('mixer.get_init =', pygame.mixer.get_init())
try:
    pygame.mixer.quit()
    pygame.quit()
except Exception:
    pass
