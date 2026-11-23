# -*- coding: utf-8 -*-
"""三端交付打包：把 PC(exe) / 网页版(HTML) / 手机版(PWA) 汇总到交付目录。

用法：
    python tools/deploy.py

产物目录结构：
    最后一片净土/
      PC版/最后一片净土.exe          双击即玩（Windows）
      PC版/使用手册.md
      网页版/最后一片净土.html       单文件，双击即可离线玩，也可发到网上
      网页版/README.md
      手机版/index.html              可作为 PWA 安装到手机桌面
      手机版/manifest.webmanifest
      手机版/sw.js
      手机版/README.md
      更新日志.md
"""
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DESKTOP = os.path.join(os.path.expanduser('~'), 'Desktop')
OUT = os.path.join(DESKTOP, 'AI授课', '演示', '最后一片净土')
WEB_HTML = os.path.join(ROOT, 'web', 'index.html')
EXE = os.path.join(ROOT, 'dist', 'LastCleanLand.exe')
ICON = os.path.join(ROOT, 'assets', 'icon.ico')
MANUAL = os.path.join(ROOT, 'docs', '使用手册.md')


def ensure(p):
    os.makedirs(p, exist_ok=True)
    return p


def copy(src, dst_dir, name=None):
    if not os.path.isfile(src):
        print('  [警告] 缺少', src)
        return None
    ensure(dst_dir)
    dst = os.path.join(dst_dir, name or os.path.basename(src))
    shutil.copy2(src, dst)
    print('  ->', os.path.relpath(dst, OUT),
          '%.1f KB' % (os.path.getsize(dst) / 1024))
    return dst


PWA_MANIFEST = '''{
  "name": "最后一片净土",
  "short_name": "最后净土",
  "description": "污染入侵下的生存 Roguelike：35 关、7 个主题场景、天赋构筑与收集品图鉴。",
  "start_url": "./index.html",
  "scope": "./",
  "display": "fullscreen",
  "orientation": "landscape",
  "background_color": "#0a0910",
  "theme_color": "#0a0910",
  "icons": [
    { "src": "./icon-192.png", "sizes": "192x192", "type": "image/png",
      "purpose": "any maskable" },
    { "src": "./icon-512.png", "sizes": "512x512", "type": "image/png",
      "purpose": "any maskable" }
  ]
}
'''

PWA_SW = '''/* 最后一片净土 · Service Worker —— 首次打开后即可离线游玩 */
var CACHE = 'last-clean-land-v1.4.4';
var FILES = ['./', './index.html', './manifest.webmanifest',
             './icon-192.png', './icon-512.png'];

self.addEventListener('install', function (e) {
    e.waitUntil(caches.open(CACHE).then(function (c) {
        return c.addAll(FILES).catch(function () { /* 缺图标也能装 */ });
    }).then(function () { return self.skipWaiting(); }));
});

self.addEventListener('activate', function (e) {
    e.waitUntil(caches.keys().then(function (ks) {
        return Promise.all(ks.map(function (k) {
            return k === CACHE ? null : caches.delete(k);
        }));
    }).then(function () { return self.clients.claim(); }));
});

self.addEventListener('fetch', function (e) {
    if (e.request.method !== 'GET') { return; }
    e.respondWith(
        caches.match(e.request).then(function (hit) {
            if (hit) { return hit; }
            return fetch(e.request).then(function (res) {
                var copy = res.clone();
                caches.open(CACHE).then(function (c) {
                    try { c.put(e.request, copy); } catch (err) { }
                });
                return res;
            }).catch(function () { return caches.match('./index.html'); });
        })
    );
});
'''

PWA_README = '''# 手机版（PWA）使用说明

## 一、怎么玩

1. 把整个 `手机版` 文件夹放到一个 **HTTPS 网址** 下（或本机起的 HTTP 服务）。
   PWA 安装要求 HTTPS（`localhost` 例外）。
2. 手机浏览器打开 `index.html`。
3. 建议先在浏览器里把手机**横屏**，然后：
   - **Android Chrome**：右上角菜单 →「添加到主屏幕」/「安装应用」
   - **iOS Safari**：底部分享 →「添加到主屏幕」
4. 装好后从桌面图标启动，即为全屏、无地址栏，且**断网也能玩**（Service Worker 已缓存全部资源）。

## 二、触控操作

| 操作 | 说明 |
| --- | --- |
| 左半屏按住拖动 | 半透明摇杆，控制移动方向与幅度 |
| 右半屏点/拖 | 朝该方向瞄准 |
| 右下「射」 | 按住持续开火 |
| 右下「冲」 | 冲刺 |
| 右下「E」 | 交互（开宝箱 / 买 / 进传送门） |

摇杆与按钮均为半透明，不遮挡画面。

## 三、常见问题

- **装了但没图标 / 打不开全屏**：确认是通过 https 访问的，且 `index.html`、
  `manifest.webmanifest`、`sw.js` 在同一目录。
- **想直接玩不想装**：直接浏览器打开 `index.html` 也能玩，只是没有全屏与离线。
- **想发给朋友**：把 `网页版/最后一片净土.html` 这一个文件发过去即可，
  对方双击就能玩，不需要任何环境。
'''

WEB_README = '''# 网页版使用说明

## 一、单机游玩

双击 `最后一片净土.html`，用浏览器打开即可。

- 完全自包含：贴图、数据、音效全部内嵌在这一个文件里
- 不联网、不需要本地服务器、不需要安装任何东西
- 也可以直接把这一个文件发给别人玩

## 二、操作

| 键位 | 功能 |
| --- | --- |
| WASD / 方向键 | 移动 |
| 鼠标 | 瞄准 |
| 鼠标左键 / 空格 | 射击（按住连射） |
| 鼠标右键 / Shift | 冲刺 |
| Ctrl | 缓步（精细走位） |
| E / F | 交互（宝箱、商店、传送门） |
| ESC | 暂停 |
| TAB | 客厅里切换分页（关卡 / 图鉴 / 展示台） |
| F11 | 全屏 |
| M | 静音开关 |

手机/平板打开会自动出现半透明摇杆与触控按钮。

## 三、发布到网上

把 `最后一片净土.html` 传到任意静态托管（GitHub Pages、Vercel、
对象存储等），或把 `手机版/` 整个目录传上去以获得 PWA 安装能力。

## 四、开发

网页版与 Python 版共用同一套逻辑与数据：

```bash
python tools/gen_data_js.py   # 从 src/sk/*.py 导出 web_src/data.js
python tools/build_web.py     # 打包成 web/index.html（单文件）
node tools/web_selftest.js    # 网页版无头自动化测试
```
'''


def pwa_icons():
    """从 icon.ico 生成 PWA 需要的 PNG 图标。"""
    out = []
    try:
        from PIL import Image
    except Exception:
        print('  [提示] 无 Pillow，跳过 PWA PNG 图标生成')
        return out
    if not os.path.isfile(ICON):
        return out
    im = Image.open(ICON).convert('RGBA')
    for side in (192, 512):
        p = os.path.join(OUT, '手机版', 'icon-%d.png' % side)
        im.resize((side, side), Image.LANCZOS).save(p)
        print('  ->', os.path.relpath(p, OUT),
              '%.1f KB' % (os.path.getsize(p) / 1024))
        out.append(p)
    return out


def main():
    if not os.path.isfile(WEB_HTML):
        raise SystemExit('缺少 web/index.html，请先运行 tools/build_web.py')
    if not os.path.isfile(EXE):
        raise SystemExit('缺少 dist/LastCleanLand.exe，请先运行 tools/build_release.py')

    print('交付目录 ->', OUT)
    # PC 版
    copy(EXE, os.path.join(OUT, 'PC版'), '最后一片净土.exe')
    copy(MANUAL, os.path.join(OUT, 'PC版'))
    copy(ICON, os.path.join(OUT, 'PC版'), 'icon.ico')

    # 网页版
    copy(WEB_HTML, os.path.join(OUT, '网页版'), '最后一片净土.html')
    with open(os.path.join(OUT, '网页版', 'README.md'), 'w',
              encoding='utf-8', newline='\n') as f:
        f.write(WEB_README)
    print('  ->', os.path.relpath(
        os.path.join(OUT, '网页版', 'README.md'), OUT))

    # 手机版（PWA）
    ensure(os.path.join(OUT, '手机版'))
    copy(WEB_HTML, os.path.join(OUT, '手机版'), 'index.html')
    with open(os.path.join(OUT, '手机版', 'manifest.webmanifest'), 'w',
              encoding='utf-8', newline='\n') as f:
        f.write(PWA_MANIFEST)
    with open(os.path.join(OUT, '手机版', 'sw.js'), 'w',
              encoding='utf-8', newline='\n') as f:
        f.write(PWA_SW)
    with open(os.path.join(OUT, '手机版', 'README.md'), 'w',
              encoding='utf-8', newline='\n') as f:
        f.write(PWA_README)
    print('  ->', os.path.relpath(os.path.join(OUT, '手机版'), OUT), '(manifest/sw)')
    pwa_icons()

    print('\n交付完成。')
    return 0


if __name__ == '__main__':
    sys.exit(main())
