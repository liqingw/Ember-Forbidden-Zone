# -*- coding: utf-8 -*-
"""确认 joystick.init() 就是那 60 秒，并验证 --no-joystick / 环境变量能否绕开。

真凶：pygame.init() 会自动初始化 joystick 子系统。Windows 上 SDL 枚举
HID / 手柄设备时，若有设备驱动响应缓慢（虚拟手柄、蓝牙残留设备、
某些 RGB 外设的 HID 描述符异常），枚举会阻塞到超时 —— 实测 60.2 秒。
这期间**窗口还没建**，用户看到的就是"双击之后什么都没发生"。
"""
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'src'))


def timed(tag, fn):
    t = time.time()
    try:
        r = fn()
        print('[%8.3fs] %-36s -> %r' % (time.time() - t, tag, r), flush=True)
    except Exception as e:
        print('[%8.3fs] %-36s !! %s: %s'
              % (time.time() - t, tag, type(e).__name__, e), flush=True)


def run(label):
    print('\n======== %s ========' % label, flush=True)
    import pygame
    t = time.time()
    pygame.init()
    print('[%8.3fs] pygame.init() 总计' % (time.time() - t), flush=True)
    print('    joystick.get_init =', pygame.joystick.get_init(), flush=True)
    print('    display.get_init  =', pygame.display.get_init(), flush=True)
    print('    mixer.get_init    =', pygame.mixer.get_init(), flush=True)
    print('    font.get_init     =', pygame.font.get_init(), flush=True)
    t = time.time()
    n = pygame.joystick.get_count()
    print('[%8.3fs] joystick.get_count() = %d' % (time.time() - t, n), flush=True)
    for i in range(n):
        try:
            j = pygame.joystick.Joystick(i)
            print('    手柄 %d: %s  axes=%d buttons=%d'
                  % (i, j.get_name(), j.get_numaxes(), j.get_numbuttons()),
                  flush=True)
        except Exception as e:
            print('    手柄 %d: 打开失败 %s' % (i, e), flush=True)
    try:
        pygame.mixer.quit()
        pygame.quit()
    except Exception:
        pass


if __name__ == '__main__':
    # 1) 裸跑：确认 60 秒
    run('A. 裸 pygame.init()（预期 ~60s）')

    # 2) SDL_JOYSTICK_DEVICE / 禁用 HIDAPI
    os.environ['SDL_JOYSTICK_HIDAPI'] = '0'
    for k in ('SDL_JOYSTICK_HIDAPI_XBOX', 'SDL_JOYSTICK_HIDAPI_PS4',
              'SDL_JOYSTICK_HIDAPI_PS5', 'SDL_JOYSTICK_HIDAPI_SWITCH',
              'SDL_JOYSTICK_HIDAPI_GAMECUBE'):
        os.environ[k] = '0'
    run('B. 关掉 HIDAPI + 各主机 HIDAPI（预期仍慢/变快？）')

    # 3) 完全禁用 joystick 子系统
    os.environ['SDL_JOYSTICK_ALLOW_BACKGROUND_EVENTS'] = '0'
    import pygame
    pygame.quit()
    print('\n======== C. 绕过 pygame.init()，手动只初始化需要的子系统 ========',
          flush=True)
    t = time.time()
    pygame.display.init()
    pygame.font.init()
    rc = pygame.mixer.init()
    print('[%8.3fs] display+font+mixer 手动 init 完成 mixer_rc=%r'
          % (time.time() - t, rc), flush=True)
    print('    joystick.get_init =', pygame.joystick.get_init(), flush=True)
    t = time.time()
    win = pygame.display.set_mode((640, 360))
    print('[%8.3fs] set_mode 完成 %s' % (time.time() - t, win.get_size()),
          flush=True)
    for _ in range(3):
        pygame.event.pump()
        win.fill((10, 9, 16))
        pygame.display.flip()
        pygame.time.wait(80)
    print('    渲染 3 帧 OK', flush=True)
    pygame.quit()
    print('\n结论：C 路径可用 -> 用"手动子系统初始化"替代 pygame.init()',
          flush=True)
