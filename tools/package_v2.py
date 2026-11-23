"""Package Ashen Zone 2.0 for web, Windows and installable mobile PWA.

Creates only new 2.0 paths; existing 1.0 deliverables remain untouched.
"""
from pathlib import Path
from shutil import copy2
from zipfile import ZipFile, ZIP_DEFLATED
import json

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT.parent
OUT = WORK / '版本2.0'
HTML = ROOT / 'web' / 'index.html'
EXE = WORK / '版本2.0构建' / 'attempt4' / 'dist' / 'AshenZone.exe'


def write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')


def zip_folder(folder, target):
    with ZipFile(target, 'w', ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(folder.rglob('*')):
            if path.is_file():
                archive.write(path, path.relative_to(folder.parent))


def main():
    if not HTML.is_file() or not EXE.is_file():
        raise SystemExit('2.0 网页版或 Windows 可执行文件尚未生成')
    web, mobile, windows = (OUT / key for key in ('Web', 'Mobile', 'Windows'))
    for folder in (web, mobile, windows):
        folder.mkdir(parents=True, exist_ok=True)
    copy2(HTML, web / '余烬禁区-2.0.html')
    copy2(HTML, mobile / 'index.html')
    copy2(EXE, windows / 'AshenZone.exe')

    manifest = {
        'name': '余烬禁区 2.0', 'short_name': '余烬禁区',
        'description': '俯视角霓虹像素生存游戏：七大主题、三十五关、三十二种武器。',
        'start_url': './index.html', 'scope': './', 'display': 'fullscreen',
        'orientation': 'landscape', 'background_color': '#0b0c1b',
        'theme_color': '#11122b',
        'icons': [
            {'src': f'./icon-{size}.png', 'sizes': f'{size}x{size}',
             'type': 'image/png', 'purpose': 'any maskable'}
            for size in (192, 512)
        ],
    }
    write(mobile / 'manifest.webmanifest',
          json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    sw = """const CACHE = 'ashen-zone-v2.0';
const FILES = ['./', './index.html', './manifest.webmanifest',
  './icon-192.png', './icon-512.png'];
self.addEventListener('install', event => {
  event.waitUntil(caches.open(CACHE).then(cache => cache.addAll(FILES))
    .then(() => self.skipWaiting()));
});
self.addEventListener('activate', event => {
  event.waitUntil(self.clients.claim());
});
self.addEventListener('fetch', event => {
  if (event.request.method !== 'GET') return;
  event.respondWith(caches.match(event.request).then(hit =>
    hit || fetch(event.request).catch(() => caches.match('./index.html'))));
});
"""
    write(mobile / 'sw.js', sw)
    with Image.open(ROOT / 'assets' / 'icon.ico') as icon:
        for size in (192, 512):
            icon.convert('RGBA').resize((size, size), Image.Resampling.LANCZOS).save(
                mobile / f'icon-{size}.png')

    write(web / '使用说明.md',
          '# 余烬禁区 2.0 · 网页版\n\n双击 `余烬禁区-2.0.html` 离线游玩。'
          '存档保存在浏览器本地；升级时请使用同一浏览器与来源。\n')
    write(windows / '使用说明.md',
          '# 余烬禁区 2.0 · Windows\n\n双击 `AshenZone.exe` 运行。'
          '现有 1.0 桌面存档可继续读取；最多三个存档。\n')
    write(mobile / '使用说明.md',
          '# 余烬禁区 2.0 · 手机端 PWA\n\n解压后将整个 Mobile 文件夹放到 HTTPS 网站，'
          '手机浏览器打开 `index.html` 并安装到主屏幕。首次安装需要联网，之后可离线使用。'
          'Android Chrome 使用“安装应用”，iOS Safari 使用“添加到主屏幕”。'
          '建议横屏，摇杆可设固定或浮动并调灵敏度。\n\n'
          '此包是 PWA 网站源文件，不是 APK 或 IPA。\n')
    write(OUT / '交付说明.md',
          '# 余烬禁区 2.0\n\n- Web：单 HTML 离线网页。\n'
          '- Windows：独立 exe。\n- Mobile：可安装 PWA，需 HTTPS 或 localhost 首次访问。\n\n'
          '三个版本均为本地存档，不会自动跨设备同步；1.0 成品保留。'
          '2.0 保留存档数据结构，但旧网页版单文件从 file:// 打开时，'
          '更换文件路径或浏览器可能改变存档来源；升级前建议保留旧文件。\n')

    for key, name in (
        ('Web', '余烬禁区-2.0-网页版.zip'),
        ('Windows', '余烬禁区-2.0-Windows版.zip'),
        ('Mobile', '余烬禁区-2.0-手机版PWA.zip'),
    ):
        zip_folder(OUT / key, WORK / name)
    print('2.0 三端目录与压缩包已写入：', WORK)


if __name__ == '__main__':
    main()
