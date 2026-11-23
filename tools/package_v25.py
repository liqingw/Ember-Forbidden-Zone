"""Build the 2.5 Web, Windows and mobile PWA delivery folders and ZIPs."""
from pathlib import Path
from shutil import copy2
from zipfile import ZipFile, ZIP_DEFLATED
import json

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT.parent
OUT = WORK / '版本2.5'
HTML = ROOT / 'web' / 'index.html'
EXE = WORK / '版本2.5构建' / 'ship_dist' / 'AshenZone.exe'


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
        raise SystemExit('请先生成 2.5 网页版与 Windows exe')
    web, mobile, windows = (OUT / key for key in ('Web', 'Mobile', 'Windows'))
    for folder in (web, mobile, windows):
        folder.mkdir(parents=True, exist_ok=True)
    copy2(HTML, web / '余烬禁区-2.5.html')
    copy2(HTML, mobile / 'index.html')
    copy2(EXE, windows / 'AshenZone.exe')

    manifest = {
        'name': '余烬禁区 2.5', 'short_name': '余烬禁区',
        'description': '俯视角霓虹像素生存游戏，七个主题、三十五关、六十九种武器。',
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
    sw = """const CACHE = 'ashen-zone-v2.5';
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
          '# 余烬禁区 2.5 · 网页版\n\n双击 `余烬禁区-2.5.html` 离线游玩。'
          '存档保存在浏览器本地；升级时请使用同一浏览器与来源。\n')
    write(windows / '使用说明.md',
          '# 余烬禁区 2.5 · Windows\n\n双击 `AshenZone.exe` 运行。'
          '原有桌面存档继续读取；一台设备最多三个存档。\n')
    write(mobile / '使用说明.md',
          '# 余烬禁区 2.5 · 手机端 PWA\n\n将整个 Mobile 文件夹放到 HTTPS 网站，'
          '手机浏览器打开 `index.html` 并安装到主屏幕。首次安装需要联网，'
          '之后可离线。建议横屏；摇杆可选固定或浮动并调灵敏度。\n\n'
          '这是 PWA 网站源文件，不是 APK 或 IPA。\n')
    write(OUT / '交付说明.md',
          '# 余烬禁区 2.5\n\nWeb：单 HTML 离线网页；Windows：独立 exe；'
          'Mobile：可安装 PWA，首次访问需 HTTPS 或 localhost。\n\n'
          '2.5 保留现有存档结构，不会自动跨设备同步。'
          '常规武器品质白到红，璀璨仍为隐藏档。所有消费均为游戏内货币。\n\n'
          '2.5：近战可击碎箱子和斩断敌方子弹。新增霰弹、激光、单发三类远程敌人，'
          '弹幕范围与速度各异。武器总数 69 把，其中远程 39 把、近战 30 把；'
          '每种武器对应唯一固定品质，拾取与商店提示显示品质颜色。'
          '降低局内金币与收藏品掉率，新增免疫陷阱、穿过地形、自动收集天赋。\n\n'
          '2.4：战斗房每轮至少刷新 5 只怪物，各轮可能出现精英怪；'
          '首领房前两轮刷新随从，第三轮刷新首领及随从。'
          '三轮全部清空后才生成奖励宝箱并开放出口。\n\n'
          '2.3：战斗房分三轮刷新。'
          '特殊房没有陷阱、掩体、洞穴和加减速带，仅可能有可击碎的箱子，'
          '箱子有概率掉蓝色能量球。角色基础蓝量翻倍，武器耗蓝约降低 30%。'
          '每个主题随机两关各有一间饮料房：琼浆玉液使生命上限翻倍，'
          '杨枝甘露每秒回 5 蓝，沙氏汽水使攻速翻倍，劳大冰红茶使击杀时播放'
          '“man what can i say”并发射篮球。篮球最多击杀两名怪物，不伤玩家。'
          '商店有两把武器及独立血瓶、蓝瓶；新增五把独立近战武器，总数 55 把。'
          '高品质武器掉率小幅提高。饮料和消耗品使用局内金币购买，增益仅本局有效。\n')
    for key, name in (
        ('Web', '余烬禁区-2.5-网页版.zip'),
        ('Windows', '余烬禁区-2.5-Windows版.zip'),
        ('Mobile', '余烬禁区-2.5-手机版PWA.zip'),
    ):
        zip_folder(OUT / key, WORK / name)
    print('2.5 三端目录与压缩包已写入：', WORK)


if __name__ == '__main__':
    main()

