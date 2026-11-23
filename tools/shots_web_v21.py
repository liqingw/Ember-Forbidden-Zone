# -*- coding: utf-8 -*-
"""用无头 Chrome 给网页版导出场景截图（用于人工核对画面与手册配图）。

原理：把 web/index.html 复制一份，在 </body> 前注入一小段"场景脚本"，
它按 URL 的 #shot=xxx 把游戏推进到指定场景后冻结（把 update 换成空函数），
再由 Chrome 的 --screenshot 截屏。

用法：python tools/shots_web.py
输出：_tmp/webshots/*.png
"""
import io
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'web', 'index.html')
OUT = os.path.join(ROOT, '_tmp', 'webshots-v21-final')

CHROME_CANDIDATES = [
    r'C:\Program Files\Google\Chrome\Application\chrome.exe',
    r'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe',
    r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',
    r'C:\Program Files\Microsoft\Edge\Application\msedge.exe',
]

# ---------------------------------------------------------------- 注入脚本
INJECT = r'''
<script>
(function () {
  function bot(g, i) {
    var pl = g.player, best = null, bd = 1e9;
    for (var k = 0; k < g.enemies.length; k++) {
      var e = g.enemies[k];
      if (!e.alive) { continue; }
      var d = Math.hypot(e.x - pl.x, e.y - pl.y);
      if (d < bd) { bd = d; best = e; }
    }
    var aim = best ? Math.atan2(best.y - pl.y, best.x - pl.x) : i * 0.09;
    return { mx: Math.cos(i * 0.031), my: Math.sin(i * 0.047), aim: aim,
             shoot: true, dash: (i % 151 === 0), slow: false };
  }
  function run(g, n, god) {
    for (var i = 0; i < n; i++) {
      if (god) { g.player.hp = g.player.max_hp; }
      g.step(1 / 60, bot(g, i));
    }
  }
  function roomOfKind(g, kind) {
    var ks = Object.keys(g.dungeon.rooms).map(Number);
    for (var i = 0; i < ks.length; i++) {
      if (g.dungeon.rooms[ks[i]].kind === kind) {
        return [ks[i] % 5, Math.floor(ks[i] / 5)];
      }
    }
    return null;
  }
  function setup(g, shot) {
    var I = window.__INTERNALS__;
    g.seed = 4242;
    g.start_run();
    if (shot === 'title') { g.state = 'title'; return; }
    if (shot === 'help') { g.state = 'help'; return; }
    if (shot === 'play') {
      var r0 = roomOfKind(g, 'normal');
      g.enter_room(r0[0], r0[1], null, false);
      run(g, 150, true);
      return;
    }
    if (shot === 'cleared') {
      var r1 = roomOfKind(g, 'normal');
      g.enter_room(r1[0], r1[1], null, false);
      run(g, 900, true);
      return;
    }
    if (shot === 'treasure') {
      var r2 = roomOfKind(g, 'treasure');
      g.enter_room(r2[0], r2[1], null, false);
      g.player.x = 272; g.player.y = 176 + 46;
      run(g, 90, true);
      g.request_interact();
      run(g, 40, true);
      return;
    }
    if (shot === 'shop') {
      var r3 = roomOfKind(g, 'shop');
      g.enter_room(r3[0], r3[1], null, false);
      g.coins = 260;
      g.player.x = 272 - 52 + 30; g.player.y = 176;
      g.step(1 / 60, { mx: 0, my: 0, aim: 0, shoot: false, dash: false, slow: false });
      return;
    }
    if (shot === 'prop') {
      var r4 = null, ks = Object.keys(g.dungeon.rooms).map(Number), i;
      for (i = 0; i < ks.length; i++) {
        if (g.dungeon.rooms[ks[i]].prop_plan.length) { r4 = ks[i]; break; }
      }
      g.enter_room(r4 % 5, Math.floor(r4 / 5), null, false);
      g.player.x = g.props[0].x; g.player.y = g.props[0].y + 30;
      run(g, 30, true);
      return;
    }
    if (shot === 'boss') {
      g.floor = 2;
      g._start_floor(2);
      var bk = g.dungeon.boss_key;
      g.enter_room(bk[0], bk[1], null, false);
      run(g, 320, true);
      return;
    }
    if (shot === 'levelclear') {
      g.floor = 1;
      g._start_floor(1);
      var b2 = g.dungeon.boss_key;
      g.enter_room(b2[0], b2[1], null, false);
      run(g, 4000, true);
      if (g.room.portal) { g.player.x = g.room.portal[0]; g.player.y = g.room.portal[1]; }
      g.step(1 / 60, { mx: 0, my: 0, aim: 0, shoot: false, dash: false, slow: false });
      return;
    }
    if (shot === 'gameover') {
      run(g, 60, true);
      g.player.iframes = 0;
      g.player.take_damage(999, g, 0, 0);
      g.state = 'gameover';
      return;
    }
    if (shot === 'victory') {
      g.kills = 87; g.coins = 412; g.total_time = 254;
      g.player.shots = 1204;
      run(g, 60, true);
      g.state = 'victory';
      return;
    }
  }

  var tries = 0;
  (function wait() {
    var g = window.__GAME__;
    if (!g) { if (tries++ < 200) { setTimeout(wait, 25); } return; }
    var m = /shot=([a-z]+)/.exec(location.hash || '');
    var shot = m ? m[1] : 'title';
    try {
      setup(g, shot);
      g.draw();
      g.update = function () { };   // 冻结画面
      g.inp = null;
      document.title = 'SHOT-OK:' + shot;
    } catch (e) {
      document.title = 'SHOT-FAIL:' + shot + ':' + e.message;
      if (window.console) { console.error(e); }
    }
  })();
})();
</script>
'''


def find_chrome():
    for c in CHROME_CANDIDATES:
        if os.path.isfile(c):
            return c
    return None


def main():
    chrome = find_chrome()
    if not chrome:
        print('未找到 Chrome / Edge，跳过网页版截图')
        return 1
    if not os.path.isfile(SRC):
        print('未找到 web/index.html，请先运行 tools/build_web.py')
        return 1

    os.makedirs(OUT, exist_ok=True)
    html = io.open(SRC, encoding='utf-8').read()
    tmp_html = os.path.join(OUT, '_shot.html')
    io.open(tmp_html, 'w', encoding='utf-8', newline='\n').write(
        html.replace('</body>', INJECT + '\n</body>'))

    shots = ['title', 'help', 'play', 'cleared', 'treasure', 'shop', 'prop',
             'boss', 'levelclear', 'gameover', 'victory']
    url_base = 'file:///' + tmp_html.replace('\\', '/')
    ok = 0
    for s in shots:
        png = os.path.join(OUT, s + '.png')
        if os.path.isfile(png):
            raise FileExistsError('Screenshot already exists; use a fresh output directory: ' + png)
        cmd = [
            chrome, '--headless=new', '--disable-gpu', '--hide-scrollbars',
            '--window-size=1040,700', '--virtual-time-budget=9000',
            '--force-device-scale-factor=1',
            '--screenshot=' + png, url_base + '#shot=' + s,
        ]
        try:
            r = subprocess.run(cmd, capture_output=True, timeout=180)
            good = os.path.isfile(png) and os.path.getsize(png) > 2000
        except Exception as e:
            good = False
            print(f'  [{s}] 失败：{e}')
        if good:
            ok += 1
            print(f'  [OK] {s}.png  {os.path.getsize(png) // 1024} KB')
        else:
            print(f'  [FAIL] {s} (rc={getattr(r, "returncode", "?")}) '
                  f'{r.stderr[-300:] if hasattr(r, "stderr") else ""}')
    print(f'共导出 {ok}/{len(shots)} 张 -> {os.path.relpath(OUT, ROOT)}')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
