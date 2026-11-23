# -*- coding: utf-8 -*-
"""
把所有程序化音效预渲染成 WAV，放到 assets/sfx/。
这样运行时不需要 numpy，exe 更小、启动更快。
用法：python tools/make_sfx.py
"""
import os
import sys
import wave

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'src'))

import numpy as np                       # noqa: E402
from sk import audio as A                # noqa: E402

OUT = os.path.join(ROOT, 'assets', 'sfx')


def main():
    if not A._OK:
        print('缺少 numpy，无法预渲染音效')
        return 1
    os.makedirs(OUT, exist_ok=True)
    total = 0
    for name in A.SFX_NAMES:
        mono = A.synth(name)
        if mono is None:
            print('  ! 未定义的音效', name)
            continue
        mono = np.clip(np.asarray(mono, np.float32), -1.0, 1.0)
        # 淡入淡出 3ms，消除爆音
        k = max(1, int(A.RATE * 0.003))
        if len(mono) > 2 * k:
            mono[:k] *= np.linspace(0, 1, k, dtype=np.float32)
            mono[-k:] *= np.linspace(1, 0, k, dtype=np.float32)
        pcm = (mono * 32767.0).astype('<i2').tobytes()
        p = os.path.join(OUT, name + '.wav')
        with wave.open(p, 'wb') as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(A.RATE)
            w.writeframes(pcm)
        kb = os.path.getsize(p) / 1024
        total += kb
        print(f'  {name:14s} {len(mono) / A.RATE * 1000:6.0f} ms  {kb:6.1f} KB')
    print(f'共 {len(A.SFX_NAMES)} 个音效，合计 {total:.0f} KB -> {OUT}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
