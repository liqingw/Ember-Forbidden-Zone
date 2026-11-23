# -*- coding: utf-8 -*-
"""
字体子集化：把 8MB+ 的中文全字库裁剪成只覆盖游戏实际用到的字符。
既大幅缩小 exe，又加快启动。生成 assets/font.ttf，并逐个校验字符覆盖。

用法：python tools/make_font.py
"""
import glob
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(ROOT, 'src')
OUT = os.path.join(ROOT, 'assets', 'font.ttf')

# 源字体候选（优先可自由分发的开源字体 Noto Sans SC，SIL OFL）
SOURCE_CANDIDATES = [
    r'C:/Windows/Fonts/Noto Sans SC (TrueType).otf',
    r'C:/Windows/Fonts/NotoSansSC-VF.ttf',
    r'C:/Windows/Fonts/simhei.ttf',
    r'C:/Windows/Fonts/msyh.ttc',
    '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
]

# 固定补充字符集（标点/符号/全角）
EXTRA = (
    ' 　！？。，、；：“”‘’（）《》【】〈〉—…·～￥%‰'
    '+-*/=<>×÷±→←↑↓★☆●○■□▲▼◆◇✓✗№°′″∞≈≠≤≥'
    '①②③④⑤⑥⑦⑧⑨⑩ⅠⅡⅢⅣⅤ'
)


def collect_chars():
    """need = 源码里真实出现的字符（必须全覆盖）；extra = 装饰性符号（允许缺失）"""
    need = set()
    for i in range(32, 127):
        need.add(chr(i))
    n_files = 0
    for p in glob.glob(os.path.join(SRC_DIR, '**', '*.py'), recursive=True):
        n_files += 1
        with open(p, encoding='utf-8') as f:
            for ch in f.read():
                if ord(ch) >= 32:
                    need.add(ch)
    extra = set(EXTRA)
    return need, extra, n_files


def pick_source():
    for c in SOURCE_CANDIDATES:
        if os.path.isfile(c):
            return c
    return None


def main():
    src = pick_source()
    if src is None:
        print('找不到可用源字体，跳过子集化')
        return 1
    need, extra, n_files = collect_chars()
    chars = need | extra
    text = ''.join(sorted(chars))
    print(f'扫描 {n_files} 个源文件：必需字符 {len(need)} 个，'
          f'装饰符号 {len(extra - need)} 个，合计 {len(chars)}')

    from fontTools import subset
    from fontTools.ttLib import TTFont

    args = [
        src,
        '--text=' + text,
        '--output-file=' + OUT,
        '--layout-features=',
        '--no-hinting',
        '--desubroutinize',
        '--drop-tables+=DSIG,GSUB,GPOS,GDEF',
        '--name-IDs=1,2,3,4,6',
        '--recalc-bounds',
    ]
    try:
        subset.main(args)
    except SystemExit:
        pass

    if not os.path.isfile(OUT):
        print('子集化失败：未生成输出')
        return 1

    # ---------- 校验：源码用到的字符必须全部覆盖 ----------
    f = TTFont(OUT)
    cmap = set()
    for t in f['cmap'].tables:
        cmap |= set(t.cmap.keys())
    missing = sorted({c for c in need if ord(c) not in cmap})
    absent_extra = sorted({c for c in extra if ord(c) not in cmap})
    src_kb = os.path.getsize(src) // 1024
    out_kb = os.path.getsize(OUT) // 1024
    print(f'源字体 {src_kb} KB  ->  子集 {out_kb} KB  '
          f'(压缩到 {out_kb / max(1, src_kb) * 100:.1f}%)')
    if absent_extra:
        print('提示：源字体不含这些装饰符号，已忽略：', ''.join(absent_extra))
    if missing:
        print('!! 必需字符缺失（会导致界面显示方框）：', ''.join(missing[:80]))
        return 2
    print(f'字符覆盖校验通过：源码用到的 {len(need)} 个字符全部存在')
    return 0


if __name__ == '__main__':
    sys.exit(main())
