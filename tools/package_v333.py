"""Deliver the 3.3.3 web, desktop, PWA and native mobile projects."""
from pathlib import Path
from shutil import copy2
from zipfile import ZipFile, ZIP_DEFLATED
import json

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT.parent
OUT = WORK / '版本3.3.3'
NATIVE = ROOT / 'mobile_native'
WWW = NATIVE / 'www'
EXE = WORK / '版本3.3.3构建' / 'release_dist' / 'AshenZone.exe'
APK = NATIVE / 'android' / 'app' / 'build' / 'outputs' / 'apk' / 'debug' / 'app-debug.apk'


def write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')


def pack_folder(folder, target):
    with ZipFile(target, 'w', ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(folder.rglob('*')):
            if path.is_file():
                archive.write(path, path.relative_to(folder.parent))


def pack_native(target):
    excluded = {'node_modules', '.gradle', 'build', '.idea', 'DerivedData'}
    with ZipFile(target, 'w', ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(NATIVE.rglob('*')):
            rel = path.relative_to(NATIVE)
            if not path.is_file() or any(part in excluded for part in rel.parts):
                continue
            if path.name in ('local.properties', '.DS_Store'):
                continue
            archive.write(path, Path('MobileNative') / rel)
        archive.writestr('MobileNative/构建说明.md',
            '# 手机原生工程\n\n'
            '先在 MobileNative 目录执行 npm install，以恢复压缩包未包含的 node_modules。'
            'Android 使用 android 目录，iOS 使用 ios 目录。'
            '游戏内容来自原项目 游戏源码/web_src；每次修改后在原项目运行 '
            'python 游戏源码/tools/prepare_mobile_v333.py，逐文件同步到两端。'
            '本压缩包含当前版本的 www 和原生工程。\n')


def main():
    if not (WWW / 'index.html').is_file() or not EXE.is_file():
        raise SystemExit('先运行 prepare_mobile_v333.py 并构建 Windows exe')
    if not APK.is_file():
        raise SystemExit('未找到 3.3.3 Android APK，停止打包以免交付旧版本')
    with ZipFile(APK) as built:
        if built.read('assets/public/index.html') != (WWW / 'index.html').read_bytes():
            raise SystemExit('Android APK 的游戏资源与当前版本不一致')
    if (NATIVE / 'ios/App/App/public/index.html').read_bytes() != (WWW / 'index.html').read_bytes():
        raise SystemExit('iOS 工程的游戏资源与当前版本不一致')
    plugins = json.loads((NATIVE / 'android/app/src/main/assets/capacitor.plugins.json').read_text(encoding='utf-8'))
    if not any(item.get('pkg') == '@capacitor/preferences' for item in plugins):
        raise SystemExit('Android 原生存档插件未注册')
    if 'CapacitorPreferences' not in (NATIVE / 'ios/App/CapApp-SPM/Package.swift').read_text(encoding='utf-8'):
        raise SystemExit('iOS 原生存档插件未接入')
    web, windows, pwa, android, ios = (OUT / name for name in
        ('Web', 'Windows', 'Mobile-PWA', 'Android', 'iOS'))
    for folder in (web, windows, pwa, android, ios):
        folder.mkdir(parents=True, exist_ok=True)
    copy2(WWW / 'index.html', web / '余烬禁区-3.3.3.html')
    copy2(EXE, windows / 'AshenZone.exe')
    for source in WWW.iterdir():
        if source.is_file():
            copy2(source, pwa / source.name)
    sw = """const CACHE='ashen-zone-v3.3.3';
const FILES=['./','./index.html','./manifest.webmanifest','./icon-192.png','./icon-512.png','./favicon.ico'];
self.addEventListener('install',event=>event.waitUntil(caches.open(CACHE)
  .then(cache=>cache.addAll(FILES)).then(()=>self.skipWaiting())));
self.addEventListener('activate',event=>event.waitUntil(caches.keys()
  .then(keys=>Promise.all(keys.filter(key=>key.startsWith('ashen-zone-')&&key!==CACHE)
  .map(key=>caches.delete(key)))).then(()=>self.clients.claim())));
self.addEventListener('fetch',event=>{if(event.request.method!=='GET')return;
  event.respondWith(caches.open(CACHE).then(cache=>cache.match(event.request)
    .then(hit=>hit||fetch(event.request).catch(()=>cache.match('./index.html')))));});
"""
    write(pwa / 'sw.js', sw)
    write(web / '使用说明.md', '# 余烬禁区 3.3.3 网页版\n\n双击 HTML 离线游玩。\n')
    write(windows / '使用说明.md', '# 余烬禁区 3.3.3 Windows 版\n\n双击 AshenZone.exe 游玩。\n')
    write(pwa / '使用说明.md', '# 余烬禁区 3.3.3 手机 PWA\n\n放到 HTTPS 网站访问；横屏游玩。\n')
    if APK.is_file():
        copy2(APK, android / '余烬禁区-3.3.3-Android测试版.apk')
        write(android / '使用说明.md',
              '# Android 测试安装包\n\n这是 Gradle debug APK，可安装测试；正式发布需要保管专用签名密钥并构建 release 包。\n')
    else:
        write(android / '使用说明.md',
              '# Android 工程\n\n当前未生成 APK。使用 MobileNative/android 工程及 Android SDK 构建。\n')
    write(ios / '使用说明.md',
          '# iOS 工程\n\n本机没有 macOS/Xcode，当前未生成 IPA。请在 Mac 上打开 MobileNative/ios/App/App.xcodeproj，配置自己的开发者签名后构建与测试。\n')
    write(OUT / '交付说明.md',
          '# 余烬禁区 3.3.3\n\n'
          '## 使用\n\n'
          '- Android：安装 Android 目录中的 APK；这是测试签名包，正式发布需正式签名。\n'
          '- Windows：运行 Windows/AshenZone.exe。\n'
          '- Web：用浏览器打开 Web 中的 HTML。\n'
          '- 手机 PWA：把 Mobile-PWA 放在 HTTPS 网站，手机横屏访问。\n'
          '- iOS：提供 Xcode 工程；本机没有 Mac，尚未生成或测试 IPA。\n\n'
          '手机画面固定 16:9，并按可用屏幕最大尺寸缩放。手机与电脑分别显示相应操作提示。'
          '浏览器 PWA 与原生 App 的存档处于不同应用空间，安装 App 不会自动搬运浏览器存档。'
          '可在游戏操作说明中导出和导入 JSON 存档；导入时保留本机进度更高的档位。'
          '安卓 App 优先调用系统分享，若不支持则尝试复制存档文本。'
          '原生 App 启动时会对比旧 WebView 存档与原生持久存档，保留进度较高的档位；'
          '保存时同步写入原生 Preferences。建议继续定期手动导出备份。'
          '设置页可调整攻击摇杆灵敏度及开关手机辅助瞄准；切换后台会自动暂停。\n\n'
          '## 后续更新\n\n'
          '手机网页、PWA、Android、iOS 的游戏内容来自 游戏源码/web_src。'
          '每次修改后运行 python 游戏源码/tools/prepare_mobile_v333.py，'
          '同步资源到两个原生工程，再分别构建安装包。Windows 版需用 Python 项目单独构建。\n\n'
          '## 验证范围\n\n'
          '触屏浏览器自动化测试 21/21 通过；原生存档桥接单测通过；'
          'Windows 可执行文件自检通过；Android APK 已完成构建、包内资源和签名校验。'
          '3.3.2 与 3.3.3 测试 APK 的包名及签名相同，版本号已递增；'
          '实际覆盖安装尚未在设备上验证。'
          '尚未在实体手机运行 APK，iOS 工程尚未用 Xcode 编译。'
          '按当前五关、每关一层规则更新测试后，网页全量自测 591/591 通过。\n')
    copy2(ROOT / 'docs' / '3.3.3验证.md', OUT / '验证记录.md')
    for folder, filename in ((web, '余烬禁区-3.3.3-网页版.zip'),
                             (windows, '余烬禁区-3.3.3-Windows版.zip'),
                             (pwa, '余烬禁区-3.3.3-手机版PWA.zip')):
        pack_folder(folder, WORK / filename)
    if APK.is_file():
        pack_folder(android, WORK / '余烬禁区-3.3.3-Android测试版.zip')
    pack_native(WORK / '余烬禁区-3.3.3-Android-iOS原生工程.zip')
    print('3.3.3 packages written:', WORK)


if __name__ == '__main__':
    main()
