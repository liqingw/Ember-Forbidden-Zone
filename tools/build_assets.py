# -*- coding: utf-8 -*-
"""
素材加工流水线
把 AI 生成的原始大图，加工成游戏可直接使用的像素风小图：
  1) 去水印      strip_watermark
  2) 去背景      remove_bg      （边框连通域算法，保留内部同色区域）
  3) 自动裁边    autocrop
  4) 缩放+减色   fit / posterize （保留"像素风"质感）
  5) 切片        slice_items（单行素材表，连通域分割）
                 detect_grid_cells（规则网格 tile 表，投影法探测格线）
输出到 assets/，同时产出校验联络表 _tmp/verify_all.png
"""
import os
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

ROOT = r'C:/Users/ASUS/WorkBuddy/2026-09-23-20-23-24'
RAW = os.path.join(ROOT, 'assets_raw')
OUT = os.path.join(ROOT, 'assets')
TMP = os.path.join(ROOT, '_tmp')

LOG = []


def log(*a):
    s = ' '.join(str(x) for x in a)
    LOG.append(s)
    print(s, flush=True)


# ---------------------------------------------------------------- 基础工具
def load_rgb(p):
    return Image.open(p).convert('RGB')


def strip_watermark(im, frac_w=0.22, frac_h=0.10):
    """右下角水印：用左侧相邻区域镜像覆盖（对石墙/地砖这类纹理，观感自然）"""
    a = np.array(im.convert('RGB'))
    h, w, _ = a.shape
    bw = max(8, int(w * frac_w))
    bh = max(8, int(h * frac_h))
    y0, x0 = h - bh, w - bw
    src = a[y0:h, max(0, x0 - bw):x0]
    if src.shape[1] != bw:
        return im
    a[y0:h, x0:w] = src[:, ::-1, :]
    return Image.fromarray(a)


def remove_bg(im, tol=34):
    """边框连通域去背。支持纯色背景、棋盘格背景、白底、绿幕底。"""
    rgb = np.array(im.convert('RGB')).astype(np.int16)
    h, w, _ = rgb.shape

    border = np.concatenate([
        rgb[0:2].reshape(-1, 3), rgb[-2:].reshape(-1, 3),
        rgb[:, 0:2].reshape(-1, 3), rgb[:, -2:].reshape(-1, 3),
    ])
    q = border // 8
    keys, counts = np.unique(q, axis=0, return_counts=True)
    seeds = keys[np.argsort(-counts)[:3]] * 8 + 4

    dist = np.min(np.stack([np.abs(rgb - s).max(axis=2) for s in seeds]), axis=0)
    cand = dist <= tol
    mx, mn = rgb.max(axis=2), rgb.min(axis=2)
    cand |= ((mx - mn) < 14) & (mn > 193)          # 近中性且很亮（白/浅灰/棋盘格）

    lab, _ = ndimage.label(cand)
    bl = set(np.unique(lab[0, :])) | set(np.unique(lab[-1, :]))
    bl |= set(np.unique(lab[:, 0])) | set(np.unique(lab[:, -1]))
    bl.discard(0)
    bgmask = np.isin(lab, list(bl))

    alpha = np.where(bgmask, 0, 255).astype(np.uint8)
    if (alpha > 0).mean() < 0.02:
        log('    ! 去背异常(剩余<2%)，回退为不抠图')
        alpha = np.full((h, w), 255, np.uint8)
    return Image.fromarray(np.dstack([np.array(im.convert('RGB')), alpha]), 'RGBA')


def autocrop(im, thr=8):
    a = np.array(im)
    ys, xs = np.where(a[..., 3] > thr)
    if len(ys) == 0:
        return im
    return im.crop((int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1))


def posterize(im, colors=30):
    a = np.array(im)
    alpha = a[..., 3]
    q = Image.fromarray(a[..., :3]).quantize(
        colors=colors, method=Image.MEDIANCUT, dither=Image.NONE).convert('RGB')
    return Image.fromarray(np.dstack([np.array(q), alpha]), 'RGBA')


def fit(im, size, pad=0.05, colors=30):
    """等比缩放并居中放入 size×size 透明画布"""
    w, h = im.size
    inner = max(1, int(size * (1 - 2 * pad)))
    s = min(inner / w, inner / h)
    nw, nh = max(1, int(round(w * s))), max(1, int(round(h * s)))
    resample = Image.BOX if s < 1 else Image.LANCZOS
    r = im.resize((nw, nh), resample)
    canvas = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    canvas.paste(r, ((size - nw) // 2, (size - nh) // 2), r)
    return posterize(canvas, colors)


def slice_items(im, expected, min_area_frac=0.0018, merge_r_frac=0.0075):
    """单行素材表：连通域分割。merge_r_frac 控制"多部件合并"的膨胀半径。"""
    a = np.array(im.convert('RGBA'))
    mask = a[..., 3] > 8
    h, w = mask.shape
    r = max(1, int(w * merge_r_frac))
    mask_d = ndimage.binary_dilation(mask, structure=np.ones((2 * r + 1, 2 * r + 1), bool))
    lab, n = ndimage.label(mask_d)
    boxes = []
    for i in range(1, n + 1):
        sub = (lab == i) & mask
        if int(sub.sum()) < h * w * min_area_frac:
            continue
        ys, xs = np.where(sub)
        boxes.append((int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1))
    if len(boxes) != expected:
        log(f'    ! 连通域 {len(boxes)} != 预期 {expected}，按面积取前 {expected}')
        boxes = sorted(boxes, key=lambda b: -(b[2] - b[0]) * (b[3] - b[1]))[:expected]
    boxes.sort(key=lambda b: (b[0] + b[2]) / 2)
    return [(i, im.crop(b)) for i, b in enumerate(boxes)]


def detect_grid_cells(im, nx=4, ny=4, margin=0.06):
    """规则网格 tile 表：用行/列灰度标准差找"空白隔离带"，切出 nx×ny 格。
    找不到规则网格时回退为等分切割。"""
    g = np.array(im.convert('L')).astype(np.float32)
    h, w = g.shape

    def spans(std_vec, n_expect, L):
        thr = max(1.5, float(np.percentile(std_vec, 10)) * 1.8)
        is_bg = std_vec < thr
        min_run = max(2, L // 500)
        runs, i = [], 0
        while i < L:
            if is_bg[i]:
                j = i
                while j < L and is_bg[j]:
                    j += 1
                if j - i >= min_run:
                    runs.append((i, j))
                i = j
            else:
                i += 1
        out, prev = [], 0
        for a, b in runs:
            if a - prev > L // 25:
                out.append((prev, a))
            prev = b
        if L - prev > L // 25:
            out.append((prev, L))
        return out, thr

    cs, tc = spans(g.std(axis=0), nx, w)
    rs, tr = spans(g.std(axis=1), ny, h)
    log(f'    投影探测: 列带 {len(cs)} 行带 {len(rs)} (阈值 c={tc:.2f} r={tr:.2f})')
    if len(cs) != nx or len(rs) != ny:
        log('    ! 网格不规则，回退等分切割')
        cs = [(int(w * i / nx), int(w * (i + 1) / nx)) for i in range(nx)]
        rs = [(int(h * i / ny), int(h * (i + 1) / ny)) for i in range(ny)]
        margin = 0.10

    out = []
    k = 0
    for (y0, y1) in rs:
        for (x0, x1) in cs:
            bw, bh = x1 - x0, y1 - y0
            mx, my = int(bw * margin), int(bh * margin)
            out.append((k, im.crop((x0 + mx, y0 + my, x1 - mx, y1 - my))))
            k += 1
    return out


def verify_sheet(items, path, th=96, cols=8):
    n = len(items)
    rows = max(1, (n + cols - 1) // cols)
    cell = th + 20
    canvas = Image.new('RGBA', (cols * cell, rows * cell), (34, 34, 42, 255))
    d = ImageDraw.Draw(canvas)
    for i, (name, img) in enumerate(items):
        x, y = (i % cols) * cell, (i // cols) * cell
        thumb = img.convert('RGBA').copy()
        thumb.thumbnail((th - 6, th - 6), Image.NEAREST)
        bg = Image.new('RGBA', (th - 6, th - 6), (110, 110, 120, 255))
        bg.alpha_composite(thumb, ((th - 6 - thumb.width) // 2, (th - 6 - thumb.height) // 2))
        canvas.alpha_composite(bg, (x + 3, y + 17))
        d.text((x + 3, y + 4), f'{i}:{name[:13]}', fill=(255, 220, 120))
    canvas.convert('RGB').save(path)
    log('  校验表 ->', os.path.basename(path), f'({n} 项)')


# ---------------------------------------------------------------- 主流程
def main():
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(TMP, exist_ok=True)
    verify = []

    log('[1] 单体角色')
    lone = [
        ('player',       'Pixel_art_game_sprite__16_bit__2026-09-23T12-25-57.png', 48),
        ('enemy_slime',  'Pixel_art_game_sprite__16_bit__2026-09-23T12-25-56.png', 44),
        ('enemy_bomber', 'Pixel_art_game_sprite__16_bit__2026-09-23T12-25-55.png', 44),
        ('enemy_drone',  'boss/Pixel_art_game_sprite__16_bit__2026-09-23T12-29-50.png', 44),
        ('boss',         'boss/Pixel_art_game_sprite__16_bit__2026-09-23T12-29-49.png', 104),
    ]
    for name, rel, size in lone:
        p = os.path.join(RAW, rel)
        if not os.path.exists(p):
            log('   ! 缺失', rel)
            continue
        im = fit(autocrop(remove_bg(load_rgb(p))), size)
        im.save(os.path.join(OUT, f'spr_{name}.png'))
        log(f'  {name:14s} -> {size}x{size}')
        verify.append((name, im))

    log('[2] 道具 / 拾取物')
    props_raw = os.path.join(RAW, 'Pixel_art_game_asset_sheet__16_2026-09-23T12-26-19.png')
    if os.path.exists(props_raw):
        props = ['crate', 'barrel', 'coin', 'heart', 'energy', 'key', 'chest', 'potion']
        for i, sub in slice_items(remove_bg(load_rgb(props_raw)), len(props)):
            nm = props[i]
            s = fit(autocrop(sub), 24)
            s.save(os.path.join(OUT, f'spr_{nm}.png'))
            verify.append((nm, s))
            log(f'  {nm:14s} -> 24x24')

    log('[3] 武器')
    wpn_raw = os.path.join(RAW, 'Pixel_art_game_asset_sheet__16_2026-09-23T12-26-17.png')
    if os.path.exists(wpn_raw):
        wpns = ['pistol', 'shotgun', 'smg', 'laser', 'rocket', 'cannon']
        for i, sub in slice_items(remove_bg(load_rgb(wpn_raw)), len(wpns)):
            nm = wpns[i]
            s = fit(autocrop(sub), 32)
            s.save(os.path.join(OUT, f'wpn_{nm}.png'))
            verify.append((nm, s))
            log(f'  {nm:14s} -> 32x32')

    log('[4] 子弹')
    bul_raw = os.path.join(RAW, 'Pixel_art_game_asset_sheet__16_2026-09-23T12-26-46.png')
    if os.path.exists(bul_raw):
        buls = ['bullet', 'bolt', 'plasma', 'laser', 'rocket', 'hex']
        for i, sub in slice_items(remove_bg(load_rgb(bul_raw)), len(buls)):
            nm = buls[i]
            s = fit(autocrop(sub), 20, pad=0.02)
            s.save(os.path.join(OUT, f'bul_{nm}.png'))
            verify.append((nm, s))
            log(f'  {nm:14s} -> 20x20')

    log('[5] 地块')
    tile_raw = os.path.join(RAW, 'Pixel_art_top_down_dungeon_til_2026-09-23T12-25-59.png')
    if os.path.exists(tile_raw):
        cells = detect_grid_cells(load_rgb(tile_raw).convert('RGBA'), 4, 4)
        # 选格：0=浅灰砖(地板) 12=地板变体 4=深色苔石(墙) 8=带亮顶的墙 7=木门
        pick = {0: 'tile_floor', 12: 'tile_floor_alt', 4: 'tile_wall',
                8: 'tile_wall_top', 7: 'tile_door'}
        for i, sub in cells:
            s = sub.resize((32, 32), Image.BOX)
            s.save(os.path.join(TMP, f'tilecell_{i:02d}.png'))
            if i in pick:
                s.save(os.path.join(OUT, f'{pick[i]}.png'))
            verify.append((f'tile{i:02d}', s))
        log(f'  {len(cells)} 格；已选 {len(pick)} 格输出为 tile_*.png')

    log('[6] 标题背景')
    t_raw = os.path.join(RAW, 'Pixel_art_game_title_screen_ba_2026-09-23T12-26-17.png')
    if os.path.exists(t_raw):
        src = load_rgb(t_raw)
        w, h = src.size
        # 直接裁掉底部（水印所在区域）并取 16:9，避免镜像修补留下接缝
        ch = min(h, int(w * 9 / 16))
        im = src.crop((0, 0, w, ch)).resize((640, 360), Image.BOX)
        a = (np.array(im).astype(np.float32) * 0.72).astype(np.uint8)
        Image.fromarray(a).save(os.path.join(OUT, 'bg_title.png'))
        log(f'  bg_title.png -> 640x360 (裁 {(w,ch)} 去水印, 已压暗)')
        verify.append(('bg_title', im))

    log('[7] 钻石（需求 4：稀有货币，独立配色）')
    coin_p = os.path.join(OUT, 'spr_coin.png')
    if os.path.exists(coin_p):
        # 以金币为底稿做"冷色化 + 提亮"，得到一眼可辨的蓝色钻石，
        # 不改原始素材表（素材表里没有钻石格）。
        c = Image.open(coin_p).convert('RGBA')
        arr = np.array(c).astype(np.float32)
        r, g, b, al = arr[..., 0], arr[..., 1], arr[..., 2], arr[..., 3]
        lum = (r * 0.299 + g * 0.587 + b * 0.114)
        # 蓝色钻石：R 压到 0.45，G 抬到 1.05，B 抬到 1.25，整体提亮 1.15
        arr[..., 0] = np.clip(lum * 0.45 * 1.15, 0, 255)
        arr[..., 1] = np.clip(lum * 1.05 * 1.15, 0, 255)
        arr[..., 2] = np.clip(lum * 1.25 * 1.15, 0, 255)
        arr[..., 3] = al
        dia = Image.fromarray(arr.astype(np.uint8), 'RGBA')
        # 压成菱形轮廓（去四角），比圆形金币更像"宝石"
        w2, h2 = dia.size
        mask = Image.new('L', (w2, h2), 0)
        md = ImageDraw.Draw(mask)
        cx, cy = w2 / 2.0, h2 / 2.0
        md.polygon([(cx, 0.06 * h2), (0.94 * w2, cy),
                    (cx, 0.94 * h2), (0.06 * w2, cy)], fill=255)
        dia.putalpha(Image.composite(dia.getchannel('A'),
                                     Image.new('L', (w2, h2), 0), mask))
        dia.save(os.path.join(OUT, 'spr_diamond.png'))
        verify.append(('diamond', dia))
        log('  diamond.png    -> %dx%d (由 coin 冷色化+菱形蒙版派生)'
            % (w2, h2))
    else:
        log('  ! 缺少 spr_coin.png，跳过钻石派生')

    verify_sheet(verify, os.path.join(TMP, 'verify_all.png'), th=96, cols=8)
    with open(os.path.join(TMP, 'build_assets.log'), 'w', encoding='utf-8') as f:
        f.write('\n'.join(LOG))
    log('完成，输出目录:', OUT)


if __name__ == '__main__':
    main()
