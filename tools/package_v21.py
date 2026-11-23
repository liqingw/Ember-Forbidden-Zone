"""Build the 2.1 Web, Windows and mobile PWA delivery folders and ZIPs."""
from pathlib import Path
from shutil import copy2
from zipfile import ZipFile, ZIP_DEFLATED
import json

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT.parent
OUT = WORK / '版本2.1'
HTML = ROOT / 'web' / 'index.html'
EXE = WORK / '版本2.1构建' / 'attempt3' / 'dist' / 'AshenZone.exe'


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
        raise SystemExit('请先生成 2.1 网页版与 Windows exe')
    web, mobile, windows = (OUT / key for key in ('Web', 'Mobile', 'Windows'))
    for folder in (web, mobile, windows):
        folder.mkdir(parents=True, exist_ok=True)
    copy2(HTML, web / '余烬禁区-2.1.html')
    copy2(HTML, mobile / 'index.html')
    copy2(EXE, windows / 'AshenZone.exe')

    manifest = {
        'name': '余烬禁区 2.1', 'short_name': '余烬禁区',
        'description': '俯视角霓虹像素生存游戏，七个主题、三十五关、五十种武器。',
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
    sw = """const CACHE = 'ashen-zone-v2.1';
const FILES = ['./', './index.html', './manifest.webmanifest',
  './icon-192.png', './icon-512.png', './favicon.ico'];
self.addEventListener('install', event => {
  event.waitUntil(caches.open(CACHE).then(cache => cache.addAll(FILES))
    .then(() => self.skipWaiting()));
});
self.addEventListener('activate', event => {
  event.waitUntil(self.clients.claim());
});
self.addEventListener('fetch', event => {
  if (event.request.method !== 'GET') return;
  event.respondWith(caches.open(CACHE).then(cache =>
    cache.match(event.request).then(hit => hit || fetch(event.request)
      .catch(() => cache.match('./index.html')))));
});
"""
    write(mobile / 'sw.js', sw)
    copy2(ROOT / 'assets' / 'icon.ico', mobile / 'favicon.ico')
    with Image.open(ROOT / 'assets' / 'bg_title.png') as title:
        side = min(title.size)
        left = (title.width - side) // 2
        top = (title.height - side) // 2
        icon = title.crop((left, top, left + side, top + side)).convert('RGB')
        for size in (192, 512):
            icon.resize((size, size), Image.Resampling.NEAREST).save(
                mobile / f'icon-{size}.png', optimize=True)

    write(web / '使用说明.md',
          '# 余烬禁区 2.1 · 网页版\n\n双击 `余烬禁区-2.1.html` 离线游玩。'
          '存档保存在浏览器本地；升级时请使用同一浏览器与来源。\n')
    write(windows / '使用说明.md',
          '# 余烬禁区 2.1 · Windows\n\n双击 `AshenZone.exe` 运行。'
          '原有桌面存档继续读取；一台设备最多三个存档。\n')
    write(mobile / '使用说明.md',
          '# 余烬禁区 2.1 · 手机端 PWA\n\n将整个 Mobile 文件夹放到 HTTPS 网站，'
          '手机浏览器打开 `index.html` 并安装到主屏幕。首次安装需要联网，'
          '之后可离线。建议横屏；摇杆可选固定或浮动并调灵敏度。\n\n'
          '这是 PWA 网站源文件，不是 APK 或 IPA。\n')
    write(OUT / '交付说明.md',
          '# 余烬禁区 2.1\n\nWeb：单 HTML 离线网页；Windows：独立 exe；'
          'Mobile：可安装 PWA，首次访问需 HTTPS 或 localhost。\n\n'
          '2.1 保留现有存档结构，不会自动跨设备同步。'
          '常规武器品质白到红，璀璨仍为隐藏档。所有消费均为游戏内货币。\n')
    for key, name in (
        ('Web', '余烬禁区-2.1-网页版.zip'),
        ('Windows', '余烬禁区-2.1-Windows版.zip'),
        ('Mobile', '余烬禁区-2.1-手机版PWA.zip'),
    ):
        zip_folder(OUT / key, WORK / name)
    print('2.1 三端目录与压缩包已写入：', WORK)


if __name__ == '__main__':
    main()
