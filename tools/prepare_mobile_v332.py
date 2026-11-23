"""Build the common 3.3.2 web payload used by PWA, Android and iOS."""
from pathlib import Path
from shutil import copy2
import json
import subprocess
import sys

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
NATIVE = ROOT / 'mobile_native'
WWW = NATIVE / 'www'


def main():
    subprocess.run([sys.executable, str(ROOT / 'tools' / 'build_web.py')], check=True)
    WWW.mkdir(parents=True, exist_ok=True)
    copy2(ROOT / 'web' / 'index.html', WWW / 'index.html')
    copy2(ROOT / 'assets' / 'icon.ico', WWW / 'favicon.ico')
    manifest = {
        'name': '余烬禁区 3.3.2', 'short_name': '余烬禁区',
        'start_url': './index.html', 'scope': './', 'display': 'fullscreen',
        'orientation': 'landscape', 'background_color': '#0b0c1b',
        'theme_color': '#11122b',
        'icons': [
            {'src': f'./icon-{size}.png', 'sizes': f'{size}x{size}',
             'type': 'image/png', 'purpose': 'any maskable'}
            for size in (192, 512)
        ],
    }
    (WWW / 'manifest.webmanifest').write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    with Image.open(ROOT / 'assets' / 'bg_title.png') as title:
        side = min(title.size)
        left, top = (title.width - side) // 2, (title.height - side) // 2
        icon = title.crop((left, top, left + side, top + side)).convert('RGB')
        for size in (192, 512):
            icon.resize((size, size), Image.Resampling.NEAREST).save(
                WWW / f'icon-{size}.png', optimize=True)
        ios_icon = NATIVE / 'ios' / 'App' / 'App' / 'Assets.xcassets' / 'AppIcon.appiconset' / 'AppIcon-512@2x.png'
        if ios_icon.parent.is_dir():
            icon.resize((1024, 1024), Image.Resampling.NEAREST).save(ios_icon, optimize=True)
        android_res = NATIVE / 'android' / 'app' / 'src' / 'main' / 'res'
        for density, size in [('mdpi', 48), ('hdpi', 72), ('xhdpi', 96),
                              ('xxhdpi', 144), ('xxxhdpi', 192)]:
            folder = android_res / ('mipmap-' + density)
            if not folder.is_dir():
                continue
            square = icon.resize((size, size), Image.Resampling.NEAREST)
            square.save(folder / 'ic_launcher.png', optimize=True)
            round_icon = square.convert('RGBA')
            mask = Image.new('L', (size, size), 0)
            ImageDraw.Draw(mask).ellipse((0, 0, size - 1, size - 1), fill=255)
            round_icon.putalpha(mask)
            round_icon.save(folder / 'ic_launcher_round.png', optimize=True)
            foreground = Image.new('RGBA', (size * 2, size * 2), (0, 0, 0, 0))
            foreground.paste(square, (size // 2, size // 2))
            foreground.save(folder / 'ic_launcher_foreground.png', optimize=True)
    # 同步到已生成的原生工程；逐文件复制，不清空工程中的目录。
    native_web_dirs = [
        NATIVE / 'android' / 'app' / 'src' / 'main' / 'assets' / 'public',
        NATIVE / 'ios' / 'App' / 'App' / 'public',
    ]
    for target in native_web_dirs:
        if not target.is_dir():
            continue
        for source in WWW.rglob('*'):
            if source.is_file():
                dest = target / source.relative_to(WWW)
                dest.parent.mkdir(parents=True, exist_ok=True)
                copy2(source, dest)
    print('3.3.2 common mobile payload:', WWW)


if __name__ == '__main__':
    main()
