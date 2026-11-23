# -*- coding: utf-8 -*-
"""找出 pygame.init() 里那 60 秒到底花在哪个子系统。"""
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
        print('[%8.3fs] %-30s -> %r' % (dt, tag, r), flush=True)
        return dt
    except Exception as e:
        dt = time.time() - t
        print('[%8.3fs] %-30s !! %s: %s' % (dt, tag, type(e).__name__, e),
              flush=True)
        return dt


print('=== 逐个单独 init（互相独立） ===', flush=True)
tick('display.init', pygame.display.init)
tick('font.init', pygame.font.init)
tick('joystick.init', pygame.joystick.init)
tick('mixer.init', pygame.mixer.init)
tick('scrap.init', getattr(pygame, 'scrap', pygame).init
     if hasattr(pygame, 'scrap') else (lambda: 'no scrap'))
tick('cdrom.init', getattr(pygame, 'cdrom', pygame).init
     if hasattr(pygame, 'cdrom') else (lambda: 'no cdrom'))
tick('time 模块可用', lambda: pygame.time.get_ticks())

pygame.quit()

print()
print('=== 关键：get_init 全量列表 ===', flush=True)
tick('display.get_init', pygame.display.get_init)
tick('font.get_init', pygame.font.get_init)

print()
print('=== 二分：pygame.init() 前先手动喂一部分 ===', flush=True)
t = time.time()
pygame.init()
print('[%8.3fs] 第一次 pygame.init()' % (time.time() - t), flush=True)
fmt = pygame.display.get_surface()
print('display.get_surface =', fmt, flush=True)

print()
print('=== 关键实验：只做 display.init + font.init，反复 3 次 ===', flush=True)
pygame.quit()
for k in range(3):
    pygame.quit()
    t = time.time()
    pygame.display.init()
    t1 = time.time() - t
    t = time.time()
    pygame.font.init()
    t2 = time.time() - t
    t = time.time()
    pygame.mixer.init()
    t3 = time.time() - t
    print('#%d  display=%.3fs  font=%.3fs  mixer=%.3fs' % (k, t1, t2, t3),
          flush=True)

print()
print('=== 关键实验：pygame.init() 第二次调用是否还慢 ===', flush=True)
pygame.quit()
t = time.time()
pygame.init()
print('[%8.3fs] 第二次 pygame.init()' % (time.time() - t), flush=True)

try:
    pygame.mixer.quit()
    pygame.quit()
except Exception:
    pass
print('done', flush=True)
