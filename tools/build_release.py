# -*- coding: utf-8 -*-
"""
一键发布构建：素材 -> 字体子集 -> 音效 -> 自动化测试 -> 图标 -> exe -> 自检

用法：
    python tools/build_release.py            # 完整流程
    python tools/build_release.py --skip-test  # 跳过测试（调试用）

产物：
    dist/最后一片净土.exe
"""
import os
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PY = sys.executable
DIST = os.path.join(ROOT, 'dist')
BUILD = os.path.join(ROOT, 'build')
TRASH = os.path.join(ROOT, '_tmp', '_trash')
APP_NAME_ASCII = 'LastCleanLand'
APP_NAME_CN = '最后一片净土'
ICON = os.path.join(ROOT, 'assets', 'icon.ico')


def nuke(path, label):
    """安全清理：改名挪进 _tmp/_trash，不做递归删除（避免触发沙箱批量删除阈值）。"""
    if not os.path.exists(path):
        return
    os.makedirs(TRASH, exist_ok=True)
    dst = os.path.join(TRASH, '%s_%d' % (label, int(time.time())))
    i = 0
    while os.path.exists(dst):
        i += 1
        dst = os.path.join(TRASH, '%s_%d_%d' % (label, int(time.time()), i))
    os.rename(path, dst)
    print('  [nuke] %s -> %s' % (path, dst))

env = dict(os.environ)
env['PYTHONIOENCODING'] = 'utf-8'
env['SDL_VIDEODRIVER'] = 'dummy'
env['SDL_AUDIODRIVER'] = 'dummy'


def run(title, args, cwd=ROOT, check=True):
    print(f'\n──────── {title} ────────')
    t = time.time()
    p = subprocess.run(args, cwd=cwd, env=env,
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    out = p.stdout.decode('utf-8', 'replace')
    tail = '\n'.join(out.strip().splitlines()[-14:])
    print(tail)
    print(f'  [exit={p.returncode}  {time.time() - t:.1f}s]')
    if check and p.returncode != 0:
        print(f'!! 步骤失败：{title}')
        sys.exit(p.returncode)
    return p.returncode, out


def make_icon():
    print('\n──────── 生成图标 ────────')
    from PIL import Image, ImageDraw
    src = os.path.join(ROOT, 'assets', 'spr_player.png')
    base = Image.open(src).convert('RGBA')
    side = 256
    canvas = Image.new('RGBA', (side, side), (0, 0, 0, 0))
    d = ImageDraw.Draw(canvas)
    d.ellipse((2, 2, side - 2, side - 2), fill=(30, 28, 42, 255),
              outline=(150, 110, 220, 255), width=6)
    inner = base.resize((int(side * 0.82), int(side * 0.82)), Image.NEAREST)
    canvas.alpha_composite(inner, ((side - inner.width) // 2,
                                   (side - inner.height) // 2 + 6))
    canvas.save(ICON, sizes=[(256, 256), (128, 128), (64, 64), (48, 48),
                             (32, 32), (16, 16)])
    print('  ->', ICON, os.path.getsize(ICON) // 1024, 'KB')


def build_exe():
    print('\n──────── PyInstaller 打包 ────────')
    nuke(DIST, 'dist')
    nuke(BUILD, 'build')
    args = [
        PY, '-m', 'PyInstaller', '--noconfirm',
        '--onefile', '--noconsole',
        '--name', APP_NAME_ASCII,
        '--icon', ICON,
        '--add-data', f'assets{os.pathsep}assets',
        '--paths', os.path.join(ROOT, 'src'),
        '--workpath', BUILD,
        '--specpath', ROOT,
        '--exclude-module', 'numpy',
        '--exclude-module', 'scipy',
        '--exclude-module', 'matplotlib',
        '--exclude-module', 'PIL',
        '--exclude-module', 'Pillow',
        '--exclude-module', 'tkinter',
        '--exclude-module', 'unittest',
        '--exclude-module', 'pydoc',
        '--exclude-module', 'fontTools',
        '--exclude-module', 'pandas',
        '--exclude-module', 'setuptools',
        '--distpath', DIST,
        os.path.join(ROOT, 'src', 'main.py'),
    ]
    t = time.time()
    p = subprocess.run(args, cwd=ROOT, env=env,
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    out = p.stdout.decode('utf-8', 'replace')
    print('\n'.join(out.strip().splitlines()[-10:]))
    print(f'  [exit={p.returncode}  {time.time() - t:.1f}s]')
    if p.returncode != 0:
        sys.exit(p.returncode)
    exe = os.path.join(DIST, APP_NAME_ASCII + '.exe')
    if not os.path.isfile(exe):
        print('!! 未找到生成的 exe')
        sys.exit(1)
    print(f'  产物 {exe}  {os.path.getsize(exe) / 1024 / 1024:.1f} MB')
    return exe


def selfcheck(exe):
    print('\n──────── 打包后 exe 自检 ────────')
    logp = os.path.join(DIST, 'selfcheck.log')
    if os.path.isfile(logp):
        os.remove(logp)
    e2 = dict(env)
    p = subprocess.run([exe, '--selfcheck'], cwd=DIST, env=e2,
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                       timeout=300)
    out = p.stdout.decode('utf-8', 'replace')
    if out.strip():
        print(out.strip())
    if os.path.isfile(logp):
        with open(logp, encoding='utf-8') as f:
            txt = f.read()
        print('--- selfcheck.log ---')
        print(txt.strip())
        if 'RESULT=PASS' not in txt:
            print('!! exe 自检未通过')
            sys.exit(1)
    else:
        print('!! 未生成 selfcheck.log（exit=%s）' % p.returncode)
        sys.exit(1)
    print('\n  exe 自检通过')


def main():
    skip_test = '--skip-test' in sys.argv
    run('1/5 重建素材', [PY, 'tools/build_assets.py'])
    run('2/5 字体子集化', [PY, 'tools/make_font.py'])
    run('3/5 预渲染音效', [PY, 'tools/make_sfx.py'])
    if not skip_test:
        run('4/5 自动化测试', [PY, 'tools/selftest.py'])
    else:
        print('\n──────── 4/5 自动化测试（已跳过）────────')
    make_icon()
    exe = build_exe()
    selfcheck(exe)
    print('\n全部完成 ->', exe)


if __name__ == '__main__':
    main()
