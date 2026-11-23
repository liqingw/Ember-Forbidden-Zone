"""Create the three local 1.0 delivery bundles without touching old releases."""
from pathlib import Path
from shutil import copy2
from zipfile import ZipFile, ZIP_DEFLATED
import json

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT.parent / '版本1.0'
HTML = ROOT / 'web' / 'index.html'
EXE = OUT / 'Windows' / 'AshenZone.exe'


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
        raise SystemExit('网页版或 Windows 可执行文件尚未生成')
    web = OUT / 'Web'
    mobile = OUT / 'Mobile'
    web.mkdir(parents=True, exist_ok=True)
    mobile.mkdir(parents=True, exist_ok=True)
    copy2(HTML, web / '余烬禁区.html')
    copy2(HTML, mobile / 'index.html')

    manifest = {
        'name': '余烬禁区', 'short_name': '余烬禁区',
        'description': '污染入侵与生存：七个主题场景、三十五关。',
        'start_url': './index.html', 'scope': './', 'display': 'fullscreen',
        'orientation': 'landscape', 'background_color': '#0a0910',
        'theme_color': '#0a0910',
        'icons': [
            {'src': f'./icon-{size}.png', 'sizes': f'{size}x{size}',
             'type': 'image/png', 'purpose': 'any maskable'}
            for size in (192, 512)
        ],
    }
    write(mobile / 'manifest.webmanifest',
          json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    sw = """const CACHE = 'ashen-zone-v1.0';
const FILES = ['./', './index.html', './manifest.webmanifest',
  './icon-192.png', './icon-512.png'];
self.addEventListener('install', event => {
  event.waitUntil(caches.open(CACHE).then(cache => cache.addAll(FILES))
    .then(() => self.skipWaiting()));
});
self.addEventListener('activate', event => {
  event.waitUntil(caches.keys().then(keys => Promise.all(
    keys.filter(key => key !== CACHE).map(key => caches.delete(key))
  )).then(() => self.clients.claim()));
});
self.addEventListener('fetch', event => {
  if (event.request.method !== 'GET') return;
  event.respondWith(caches.match(event.request).then(hit =>
    hit || fetch(event.request).catch(() => caches.match('./index.html'))));
});
"""
    write(mobile / 'sw.js', sw)
    icon = ROOT / 'assets' / 'icon.ico'
    with Image.open(icon) as image:
        for size in (192, 512):
            image.convert('RGBA').resize((size, size), Image.Resampling.LANCZOS).save(
                mobile / f'icon-{size}.png')

    write(web / '使用说明.md',
          '# 余烬禁区 1.0 · 网页版\n\n双击“余烬禁区.html”即可在电脑浏览器离线游玩。'
          '存档保存在该浏览器本地，请勿清理站点数据。\n')
    write(OUT / 'Windows' / '使用说明.md',
          '# 余烬禁区 1.0 · Windows\n\n双击 AshenZone.exe 运行。'
          '第一次进入请创建个人 ID；最多三个存档。\n')
    write(mobile / '使用说明.md',
          '# 余烬禁区 1.0 · 手机端 PWA\n\n将本文件夹完整放到 HTTPS 网站，'
          '用手机浏览器打开 index.html 后添加到主屏幕。安装后可离线游玩。'
          'Android Chrome 使用“安装应用”，iOS Safari 使用“添加到主屏幕”。'
          '横屏操作；摇杆可在设置中选固定或浮动并调整灵敏度。\n\n'
          '此压缩包是 PWA 源包，不是可直接侧载的 APK 或 IPA。\n')
    write(OUT / '交付说明.md',
          '# 余烬禁区 1.0\n\n- Web：电脑浏览器单文件版。\n'
          '- Windows：桌面 exe。\n- Mobile：可安装的网页应用 PWA。\n\n'
          '三个版本为各自本地存档，不会自动跨设备同步。\n')
    for folder, target in (
        ('Web', '余烬禁区-1.0-网页版.zip'),
        ('Windows', '余烬禁区-1.0-Windows版.zip'),
        ('Mobile', '余烬禁区-1.0-手机版PWA.zip'),
    ):
        zip_folder(OUT / folder, OUT.parent / target)
    print('已生成三端交付目录与三个压缩包：', OUT.parent)


if __name__ == '__main__':
    main()
