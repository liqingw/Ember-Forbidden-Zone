# -*- coding: utf-8 -*-
"""HUD 与所有界面绘制"""
import math

import pygame

from . import settings as S
from . import utils as U
from . import weapon as W
from . import gamedata as GD

HEART_FULL = ((226, 62, 74), (255, 138, 146))
HEART_EMPTY = (62, 52, 62)


def dim(surf, a=170, color=(0, 0, 0)):
    o = pygame.Surface((S.VIEW_W, S.VIEW_H), pygame.SRCALPHA)
    o.fill((color[0], color[1], color[2], a))
    surf.blit(o, (0, 0))


def draw_route_choice(surf, game):
    dim(surf, 205, (6, 8, 12))
    U.panel(surf, (108, 47, 424, 270), (25, 27, 36, 245), (243, 184, 91), 8)
    font = game.assets.font
    lines = [
        ('旧厂勘测记录 · 第 2 关', 20, (243, 184, 91), 128, 59),
        ('检修工单 02：隔离区阀门已关闭。', 12, (220, 220, 224), 128, 89),
        ('沿警示线进入，取样后撤离。', 12, (220, 220, 224), 128, 107),
        ('常规通行 · 直接前往目标房', 15, (237, 243, 236), 142, 145),
        ('高危勘测 · 额外战斗 1 间 / 3 波', 15, (243, 184, 91), 142, 196),
        ('绕路可能消耗生命与能量；可在出口放弃。', 11, (200, 204, 210), 142, 235),
    ]
    claimed = 'mine_survey_02' in (game.profile or {}).get('route_first_rewards', [])
    lines.append(('首奖已领取；保留原房掉落' if claimed else
                  '首次完成并通关：污染结晶 ×2', 11, (182, 229, 198), 142, 256))
    for value, size, color, x, y in lines:
        U.text_shadow(font(size), surf, value, color, x, y)
    for i, y in enumerate((137, 188)):
        pygame.draw.rect(surf, (243, 184, 91) if game.route_index == i else (85, 88, 101),
                         (130, y, 380, 43), 2, border_radius=5)
    U.text_shadow(font(11), surf, '↑↓ 选择  Enter 确认  Esc 常规通行',
                  (170, 178, 185), 156, 283)


def draw_collection_popup(surf, game):
    """短暂覆盖战斗画面的收藏高光卡，不中断存档与战斗计时。"""
    popup = getattr(game, 'collection_popup', None)
    if not popup:
        return
    from . import codex as CX
    key = popup['key']
    entry = CX.COLLECTS.get(key)
    if not entry:
        return
    a = game.assets
    gold = entry[1] == 'superb'
    col = (255, 220, 118) if gold else (140, 235, 250)
    alpha = min(1.0, popup['t'] * 2.6, (popup['life'] - popup['t']) * 5)
    veil = pygame.Surface((S.VIEW_W, S.VIEW_H), pygame.SRCALPHA)
    veil.fill((5, 7, 19, int(140 * max(0, alpha))))
    surf.blit(veil, (0, 0))
    x, y, w, h = 157, 100, 326, 146
    U.panel(surf, (x, y, w, h), (18, 22, 39, 245), col, 10, 2)
    pygame.draw.line(surf, col, (x + 16, y + 12), (x + w - 16, y + 12), 2)
    icon = a.scaled('collect_' + key, 70, 70)
    surf.blit(icon, (x + 19, y + 39))
    U.text_shadow(a.font(11), surf, '珍藏发现 · ' + ('极品' if gold else '普通'),
                  col, x + 106, y + 28)
    U.text_shadow(a.font(19), surf, entry[0], (255, 247, 222), x + 106, y + 50)
    U.text_shadow(a.font(10), surf, _fit_text(a.font(10), entry[2], w - 125),
                  (189, 204, 225), x + 106, y + 87)
    U.text_shadow(a.font(10), surf, '已收录图鉴 · 已保存到展示台',
                  col, x + 106, y + 112)


def _heart(surf, x, y, state, size=13):
    """state: 2=满, 1=半, 0=空"""
    r = size
    for col, width in ((HEART_EMPTY, r + 2),
                       (HEART_FULL[0], r + 2 if state == 2 else r // 2 + 1 if state == 1 else 0)):
        if width <= 0:
            continue
        layer = pygame.Surface((r + 2, r + 2), pygame.SRCALPHA)
        pygame.draw.circle(layer, col, (r // 3, r // 3), r // 3 + 1)
        pygame.draw.circle(layer, col, (2 * r // 3, r // 3), r // 3 + 1)
        pygame.draw.polygon(layer, col, [(0, r // 2), (r, r // 2), (r // 2, r)])
        surf.blit(layer, (x, y), area=pygame.Rect(0, 0, width, r + 2))
    if state > 0:
        pygame.draw.circle(surf, HEART_FULL[1], (x + r // 3, y + r // 3), max(1, r // 8))


def draw_hud(surf, game):
    a = game.assets
    pl = game.player
    f11 = a.font(11)
    f12 = a.font(12)
    f16 = a.font(16)

    # ---------------- 左上：红心 + 能量
    # 排版说明：红心按 16px 步进排；满血 10 颗 = 154px 宽。
    # 能量条紧跟红心下方，数字右对齐到条尾留 6px 余量（原来写死在 164，
    # 一旦红心变多/能量到三位数就会顶到中间的场景横幅）。
    hp = max(0, int(math.ceil(pl.hp - 1e-6)))
    total_hearts = max(1, math.ceil(pl.max_hp / 2))
    if total_hearts <= 8:
        for i in range(total_hearts):
            state = 2 if hp >= (i + 1) * 2 else (1 if hp == i * 2 + 1 else 0)
            _heart(surf, 10 + i * 15, 8, state)
    else:
        _heart(surf, 10, 8, 2 if hp > 0 else 0)
        U.bar(surf, (28, 10, 92, 10), pl.hp / max(1.0, pl.max_hp),
              HEART_FULL[0], (48, 22, 28), (120, 48, 56))
        U.text_shadow(f11, surf, f'{hp}/{int(math.ceil(pl.max_hp))}',
                      (255, 226, 226), 124, 9)
    # 能量条与左上血条统一收紧在 x=165 以内，绝不与上方 Boss 血条重叠
    ebar_w = 120
    U.bar(surf, (10, 28, ebar_w, 8), pl.energy / max(1.0, pl.max_energy),
          S.C_ENERGY, (26, 34, 44), (60, 90, 110))
    etxt = f11.render(f'{int(pl.energy)}', True, S.C_ENERGY)
    surf.blit(etxt, (10 + ebar_w + 5, 26))

    # ---------------- 右上：金币 / 层数 / 击杀
    # 原来固定用 VIEW_W-92 当左边界，金币四位数时数字会往右顶出屏幕；
    # 现在改成"右对齐"布局：所有元素贴着右边 10px 依次左排。
    rx = S.VIEW_W - 10
    coin = a.scaled('coin', 18, 18)
    cnum = f16.render(str(game.coins), True, S.C_GOLD)
    csh = f16.render(str(game.coins), True, (0, 0, 0))
    cnx = rx - cnum.get_width()          # 金额右对齐
    surf.blit(coin, (cnx - 22, 6))
    surf.blit(csh, (cnx + 1, 7))
    surf.blit(cnum, (cnx, 6))
    # 层数 / 击杀：右对齐，逐行下移 16px
    for txt, yy in ((f'第 {int((game.level_state or {}).get("stage_idx", 0)) + 1} / 5 关', 30),
                    (f'击杀 {game.kills}', 46)):
        img = f12.render(txt, True, S.C_TEXT_DIM)
        sh = f12.render(txt, True, (0, 0, 0))
        x = rx - img.get_width()
        surf.blit(sh, (x + 1, yy + 1))
        surf.blit(img, (x, yy))

    # ---------------- 左下：武器
    px, py = 10, S.VIEW_H - 56
    wq = pl.wq(game)
    qcol = GD.quality_of(wq).get('color', S.C_PANEL_HI)
    U.panel(surf, (px, py, 232, 48), (26, 24, 34, 220), qcol, 6)
    spec = pl.spec
    qspec = pl.wq_spec(game)
    dmul = (1.0 + pl.dmg_bonus(game)) * pl.wmul(game)
    dmg_val = max(1, int(round(qspec.dmg * dmul)))
    dmg_txt = f'伤 {dmg_val}×{qspec.count}' if qspec.count > 1 else f'伤 {dmg_val}'
    aps = pl.attack_speed_mul(game) / max(0.01, float(getattr(spec, 'cd', 0.25) or 0.25))
    spd_txt = f'速 {aps:.1f}/s'
    crit_txt = f'暴 {int(round(pl.crit_chance(game) * 100))}%'
    wi = a.scaled(W.sprite_key(spec.key), 30, 30)
    surf.blit(wi, (px + 6, py + 8))
    U.text_shadow(f12, surf, spec.name, S.C_TEXT, px + 42, py + 4)
    f10 = a.font(10)
    cost = '不耗能' if spec.cost <= 0 else f'耗 {int(spec.cost)}'
    cc = S.C_TEXT_DIM if spec.cost <= 0 else S.C_ENERGY
    cw = f10.render(cost, True, cc).get_width()
    U.text_shadow(f10, surf, cost, cc, px + 226 - cw, py + 5)
    U.text_shadow(f10, surf, dmg_txt, (255, 196, 120), px + 42, py + 23)
    dw = f10.render(dmg_txt, True, (255, 196, 120)).get_width()
    U.text_shadow(f10, surf, spd_txt, (120, 224, 245), px + 42 + dw + 7, py + 23)
    sw = f10.render(spd_txt, True, (120, 224, 245)).get_width()
    U.text_shadow(f10, surf, crit_txt, (255, 224, 96), px + 42 + dw + sw + 14, py + 23)
    if pl.wkey2:
        U.text_shadow(f11, surf, 'Q 换：' + W.get(pl.wkey2).name,
                      (175, 215, 235), px + 240, py + 15)
    if game.fire_cool > 0:
        U.bar(surf, (px + 6, py + 41, 220, 3), 1.0 - game.fire_cool / max(0.01, spec.cd),
              S.C_ACCENT, (40, 38, 52))
    from .character_skills import SKILLS
    skill_name, _, skill_color, _ = SKILLS.get(game.char_key, SKILLS['scout'])
    skill_status = ('可用' if game.char_skill_cd <= 0 else f'{game.char_skill_cd:.1f}s')
    U.text_shadow(f11, surf, 'X ' + skill_name + '  ' + skill_status,
                  skill_color if game.char_skill_cd <= 0 else S.C_TEXT_DIM,
                  240, S.VIEW_H - 34)

    # ---------------- 需求：污染渐近减益指示
    draw_pollution(surf, game)

    # ---------------- 右下：小地图
    draw_minimap(surf, game)

    # ---------------- BOSS 血条
    draw_boss_bar(surf, game)

    # ---------------- 交互提示
    draw_prompt(surf, game)

    # ---------------- 房间名横幅
    # 摆放约定：y=54 是"房间名"，y=40 是"场景名"。
    # 左上角红心+能量占 0..40px，右上角资源占 0..58px，
    # 所以横幅必须落在 58px 以下才不会互相压 —— 原来 y=54/40 会和右上角打架。
    if game.banner_t > 0:
        t = min(1.0, game.banner_t / 1.6)
        al = int(255 * min(1.0, t * 2.2))
        f = a.font(20)
        img = f.render(game.banner_text, True, S.C_TEXT)
        img.set_alpha(al)
        sh = f.render(game.banner_text, True, (0, 0, 0))
        sh.set_alpha(int(al * 0.8))
        x = S.VIEW_W // 2 - img.get_width() // 2
        y = 62
        surf.blit(sh, (x + 2, y + 2))
        surf.blit(img, (x, y))

    # ---------------- 新手操作提示 + 局内关卡提示
    if game.hint_t > 0 and game.floor == 1:
        al = int(190 * min(1.0, game.hint_t))
        f = a.font(11)
        s = 'WASD 移动   左键射击   Shift 冲刺   E 交互   Q 换武器   X 技能   ESC 暂停'
        img = f.render(s, True, S.C_TEXT_DIM)
        img.set_alpha(al)
        # 底部提示要与左下武器面板（宽 176）错开，居中在剩余空间里
        cx = (192 + S.VIEW_W - 8) // 2
        surf.blit(img, (cx - img.get_width() // 2, S.VIEW_H - 20))

    # 关卡横幅下方的场景/小关提示（进关后前几秒显示一次）
    # 放在 y=44，和 y=62 的房间名分开成两行，不再叠字。
    if game.hint_t > 9.0 and getattr(game, 'level_state', None):
        ls = game.level_state or {}
        sc = ls.get('scene')
        if sc:
            si = int(ls.get('stage_idx', 0))
            try:
                from . import chapter as _C
                nm = _C.scene_info(sc).get('name', sc)
                sub = _C.scene_stage_name(si)
            except Exception:
                nm, sub = sc, '第 %d 关' % (si + 1)
            line = '%s  ·  %s  ·  房间 %d/%d' % (
                nm, sub, int(game.floor), int(S.FLOORS))
            al2 = int(200 * min(1.0, (game.hint_t - 9.0) / 3.0))
            im2 = a.font(12).render(line, True, (245, 232, 180))
            im2.set_alpha(al2)
            surf.blit(im2, (S.VIEW_W // 2 - im2.get_width() // 2, 44))

    if S.DEBUG:
        f = a.font(11)
        surf.blit(f.render(f'FPS {int(game.clock.get_fps())}  E{len(game.enemies)} '
                           f'B{len(game.bullets)} P{len(game.fx.parts)}',
                           True, (140, 255, 140)), (S.VIEW_W // 2 - 90, 6))


def draw_pollution(surf, game):
    """需求：污染渐近减益指示器。

    显示在左下角武器面板下方：一个细长的浓度条 + 减益摘要。
    1.3：显示的是**抗性折减后**的实际值，并带一个抗性徽标，
    让玩家一眼看出"我堆的抗污染天赋有没有生效"。
    没有减益时（如奖励副本）完全不画，保持界面干净。
    """
    p = getattr(game, 'pollution', None)
    if not p:
        return
    # 抗性调整后的实际值（_pur 是 game 在进关时算好的）
    pur = getattr(game, '_pur', None)
    if pur is None:
        hp_cut, spd, regen, drain = (p['hp_cut'], p['spd'], p['regen'],
                                     p['drain'])
    else:
        hp_cut, spd, regen, drain = pur
    lines = []
    if hp_cut > 0:
        lines.append('生命-%d' % int(hp_cut))
    if spd < 0.999:
        lines.append('移速-%d%%' % int(round((1.0 - spd) * 100)))
    if regen < 0.999:
        lines.append('回能-%d%%' % int(round((1.0 - regen) * 100)))
    if drain > 0:
        lines.append('侵蚀%.2f/s' % drain)
    if not lines:
        return
    a = game.assets
    f10 = a.font(10)
    # 纵向堆叠约定（从下往上）：
    #   VIEW_H-52 .. VIEW_H-10  武器面板（hud 里画）
    #   VIEW_H-74 .. VIEW_H-56  污染条
    #   VIEW_H-88 ..            抗性徽标（浮在污染条上方 12px）
    # 三个块各留 6px 间隙，保证 640x360 下不会叠字。
    x, y = 10, S.VIEW_H - 74
    w = 176
    # 抗性百分比（用侵蚀的折减比例作为代表值；无侵蚀时用 hp_cut 比）
    resist = 0.0
    base = float(p.get('drain', 0.0) or 0.0)
    if base > 0:
        resist = 1.0 - (float(drain) / base)
    elif p.get('hp_cut', 0) > 0:
        resist = 1.0 - (float(hp_cut) / float(p['hp_cut']))
    resist = max(0.0, min(1.0, resist))
    U.panel(surf, (x, y, w, 18), (34, 16, 26, 200), (150, 60, 84), 4)
    surf.blit(a.scaled('coin', 12, 12), (x + 4, y + 3))
    col = (255, 150, 170) if p['pct'] >= 60 else (240, 180, 120)
    surf.blit(f10.render('污染 %d%%' % p['pct'], True, col), (x + 19, y + 3))
    txt = ' '.join(lines)
    img = f10.render(txt, True, (222, 176, 190))
    surf.blit(img, (x + w - img.get_width() - 5, y + 3))
    # 抗性徽标（1.3）：堆了抗污染才显示
    if resist > 0.01:
        badge = '抗%d%%' % int(round(resist * 100))
        bw = f10.size(badge)[0] + 6
        U.panel(surf, (x + 19, y - 12, bw, 11), (22, 46, 40, 220),
                (120, 230, 190), 3)
        surf.blit(f10.render(badge, True, (140, 240, 200)),
                  (x + 22, y - 11))
    # 浓度条
    U.bar(surf, (x + 2, y + 15, w - 4, 2), min(1.0, p['pct'] / 100.0),
          (226, 90, 120), (44, 22, 30))


def draw_minimap(surf, game):
    a = game.assets
    dg = game.dungeon
    cell, gap = 10, 2
    w = dg.gw * (cell + gap) + 8
    h = dg.gh * (cell + gap) + 20
    x0, y0 = S.VIEW_W - w - 8, S.VIEW_H - h - 8
    U.panel(surf, (x0, y0, w, h), (20, 19, 28, 215), S.C_PANEL_HI, 5)
    surf.blit(a.font(10).render('地图', True, S.C_TEXT_DIM), (x0 + 5, y0 + 4))

    cur = (game.room.gx, game.room.gy)
    for (gx, gy) in dg.rooms:
        r = dg.rooms[(gx, gy)]
        visible = r.visited
        near = False
        if not visible:
            for d in S.DIR_VEC.values():
                nb = dg.room(gx + d[0], gy + d[1])
                if nb is not None and nb.visited:
                    near = True
                    break
        if not (visible or near):
            continue
        cx = x0 + 4 + gx * (cell + gap)
        cy = y0 + 16 + gy * (cell + gap)
        if r.kind == 'start':
            col = S.ROOM_COLOR['start']
        elif r.cleared or r.kind in ('treasure', 'heal', 'shop', 'drink'):
            col = S.ROOM_COLOR.get(r.kind, S.ROOM_COLOR['cleared'])
            if r.kind == 'normal':
                col = S.ROOM_COLOR['cleared']
        else:
            col = S.ROOM_COLOR.get(r.kind, S.ROOM_COLOR['normal'])
        if not visible:
            col = (58, 56, 70)
        pygame.draw.rect(surf, col, (cx, cy, cell, cell), border_radius=2)
        if (getattr(game, 'route_state', None) == 'survey' and
                getattr(game, 'route_room', None) == (gx, gy) and
                (visible or near)):
            marker = (182, 229, 198) if game.route_sealed else (243, 184, 91)
            pygame.draw.rect(surf, marker, (cx - 2, cy - 2, cell + 4, cell + 4), 2)
            if game.route_sealed:
                pygame.draw.line(surf, marker, (cx + 2, cy + 5), (cx + 4, cy + 8), 2)
                pygame.draw.line(surf, marker, (cx + 4, cy + 8), (cx + 9, cy + 2), 2)
        if r.kind == 'boss' and visible:
            pygame.draw.rect(surf, (255, 220, 255), (cx, cy, cell, cell), 1, border_radius=2)
        if r.kind == 'treasure' and visible:
            pygame.draw.rect(surf, (255, 240, 180), (cx, cy, cell, cell), 1, border_radius=2)
        if r.kind == 'shop' and visible:
            pygame.draw.rect(surf, (200, 255, 220), (cx, cy, cell, cell), 1, border_radius=2)
        if r.kind == 'drink' and visible:
            pygame.draw.rect(surf, (255, 214, 170), (cx, cy, cell, cell), 1, border_radius=2)
        if visible and r.portal is not None:
            center = (cx + cell // 2, cy + cell // 2)
            pygame.draw.circle(surf, (112, 62, 190), center, 7, 2)
            pygame.draw.circle(surf, (250, 213, 255), center, 4, 2)
            pygame.draw.circle(surf, (255, 255, 255), center, 1)
        # 已探明但锁着的房间打叉
        if visible and not r.cleared and r.kind in ('normal', 'boss'):
            pygame.draw.line(surf, (10, 10, 14), (cx + 1, cy + 1),
                             (cx + cell - 1, cy + cell - 1), 1)
            pygame.draw.line(surf, (10, 10, 14), (cx + cell - 1, cy + 1),
                             (cx + 1, cy + cell - 1), 1)
    # 当前房间闪烁描边
    blink = (pygame.time.get_ticks() // 260) % 2 == 0
    cx = x0 + 4 + cur[0] * (cell + gap)
    cy = y0 + 16 + cur[1] * (cell + gap)
    pygame.draw.rect(surf, (255, 255, 255) if blink else (170, 170, 190),
                     (cx - 1, cy - 1, cell + 2, cell + 2), 1, border_radius=2)


def draw_boss_bar(surf, game):
    b = game.boss
    if b is None or not b.alive or b.state in ('intro',):
        return
    a = game.assets
    w, h = 270, 10
    x = 184
    y = 23
    U.panel(surf, (x - 6, 4, w + 12, h + 24), (18, 14, 24, 225), (150, 90, 180), 6)
    bname = getattr(b, 'boss_name', None) or '首领'
    U.text_shadow(a.font(12), surf, bname, S.C_BOSS, x + 2, 6)
    pygame.draw.rect(surf, (48, 30, 50), (x, y, w, h), border_radius=3)
    fw = int(w * b.hp_ratio)
    if fw > 0:
        pygame.draw.rect(surf, (198, 84, 220), (x, y, fw, h), border_radius=3)
        pygame.draw.rect(surf, (255, 170, 250), (x, y, fw, 3), border_radius=2)
    # 阶段分隔线
    for t in (0.33, 0.66):
        pygame.draw.line(surf, (22, 16, 26), (x + int(w * t), y),
                         (x + int(w * t), y + h), 1)
    pygame.draw.rect(surf, (90, 60, 110), (x, y, w, h), 1, border_radius=3)
    f10 = a.font(10)
    hp_txt = f'{int(max(0, b.hp))} / {int(b.max_hp)}'
    hp_w = f10.render(hp_txt, True, S.C_TEXT_DIM).get_width()
    U.text_shadow(f10, surf, hp_txt, S.C_TEXT_DIM, x + w - hp_w - 2, 7)


def draw_prompt(surf, game):
    p = game.prompt
    if not p:
        return
    a = game.assets
    f = a.font(12)
    txt = p.prompt_text()
    if not txt:
        return
    col = GD.quality_of(p.quality)['color'] if p.kind in ('weapon', 'shop_weapon') else S.C_TEXT
    img = f.render(txt, True, col)
    w = img.get_width() + 20
    x = S.VIEW_W // 2 - w // 2
    # 放在底部提示行上方，且避开左下武器面板（176 宽）
    y = S.VIEW_H - 84
    # 若提示框左边缘侵入了武器面板区域，整体右移让开
    if x < 10 + 176 + 8:
        x = 10 + 176 + 8
    if x + w > S.VIEW_W - 8:
        x = max(8, S.VIEW_W - 8 - w)
    U.panel(surf, (x, y, w, 24), (24, 22, 32, 235), col, 5)
    surf.blit(img, (x + 10, y + 5))


# ==================================================================== 界面
def draw_title(surf, game):
    a = game.assets
    bg = a.scaled('bg_title', S.VIEW_W, S.VIEW_H)
    surf.blit(bg, (0, 0))
    dim(surf, 66, (6, 6, 12))

    t = pygame.time.get_ticks() / 1000.0
    bob = math.sin(t * 1.8) * 3

    f_big = a.font(40)
    U.text_shadow(f_big, surf, S.GAME_TITLE, (255, 226, 150),
                  S.VIEW_W // 2, 44 + bob, anchor='midtop')
    U.text_shadow(a.font(13), surf, S.GAME_SUB + '   ·   v' + S.VERSION,
                  (200, 150, 240), S.VIEW_W // 2, 92 + bob, anchor='midtop')

    items = game.menu_items
    for i, (label, _) in enumerate(items):
        sel = (i == game.menu_index)
        y = 168 + i * 34
        f = a.font(18 if sel else 16)
        col = (255, 236, 170) if sel else (176, 172, 196)
        w = f.size(label)[0]
        x = S.VIEW_W // 2 - w // 2
        if sel:
            hl = pygame.Surface((w + 40, 28), pygame.SRCALPHA)
            hl.fill((120, 90, 200, 70))
            surf.blit(hl, (x - 20, y - 5))
            U.text_shadow(f, surf, '▶', (255, 210, 120), x - 22, y - 2)
        U.text_shadow(f, surf, label, col, x, y - 2)

    U.text_shadow(a.font(11), surf, '↑↓ 选择    Enter 确认    鼠标点击亦可',
                  (140, 136, 160), S.VIEW_W // 2, S.VIEW_H - 26, anchor='midtop')
    if game.best_floor > 0:
        U.text_shadow(a.font(11), surf, f'最佳记录：第 {game.best_floor} 层   最高击杀 {game.best_kills}',
                      (150, 210, 180), S.VIEW_W // 2, S.VIEW_H - 44, anchor='midtop')

    # 需求 17：右下角更新日志入口，可点开查看更新详情
    _changelog_button(surf, game)


def _changelog_button(surf, game):
    """标题画面右下角的"更新日志"按钮（需求 17）。"""
    a = game.assets
    label = '更新日志 v' + S.VERSION
    w = a.font(11).size(label)[0] + 18
    bx = S.VIEW_W - 12 - w
    by = S.VIEW_H - 30
    U.panel(surf, (bx, by, w, 20), (28, 24, 36, 210), (110, 100, 140), 4, 1)
    U.text_shadow(a.font(11), surf, label, (200, 190, 230), bx + 9, by + 3)


def draw_changelog(surf, game):
    """更新日志面板（需求 17：标题右下角点开）。"""
    a = game.assets
    surf.blit(a.scaled('bg_title', S.VIEW_W, S.VIEW_H), (0, 0))
    dim(surf, 214, (6, 6, 12))
    U.panel(surf, (30, 20, S.VIEW_W - 60, S.VIEW_H - 40),
            (18, 16, 24, 238), (96, 86, 128), 6, 1)
    U.text_shadow(a.font(20), surf, '更 新 日 志', (255, 226, 150),
                  S.VIEW_W // 2, 28, anchor='midtop')
    U.text_shadow(a.font(11), surf, '当前版本 v' + S.VERSION +
                  '   ·   《' + S.GAME_TITLE + '》',
                  (170, 200, 230), S.VIEW_W // 2, 54, anchor='midtop')

    lines = _changelog_lines()
    sc = int(getattr(game, 'log_scroll', 0))
    y = 78
    bottom = S.VIEW_H - 48
    for i, (kind, txt) in enumerate(lines):
        if i < sc:
            continue
        if y > bottom:
            break
        if kind == 'h':
            U.text_shadow(a.font(14), surf, txt, (255, 216, 120), 52, y)
            y += 22
        elif kind == 's':
            U.text_shadow(a.font(12), surf, txt, (160, 210, 190), 60, y)
            y += 18
        else:
            U.text_shadow(a.font(12), surf, txt, (206, 202, 224), 68, y)
            y += 17
    # 滚动条
    total = len(lines)
    if total > 0:
        vis = max(1, (bottom - 78) // 17)
        if total > vis:
            bar_h = max(12, int((bottom - 78) * vis / float(total)))
            bar_y = 78 + int((bottom - 78 - bar_h) * sc / float(max(1, total - vis)))
            pygame.draw.rect(surf, (70, 62, 92, 200),
                             (S.VIEW_W - 42, 78, 3, bottom - 78), 2)
            pygame.draw.rect(surf, (180, 170, 210),
                             (S.VIEW_W - 42, bar_y, 3, bar_h), 0)
    U.text_shadow(a.font(11), surf, '↑↓ 滚动    ESC / Enter 返回',
                  (140, 136, 160), S.VIEW_W // 2, S.VIEW_H - 34, anchor='midtop')


def _changelog_lines():
    """更新日志内容：按版本倒序。用 (类型, 文本) 表达层级。"""
    return [
        ('h', 'v4.0 战斗重构 · 手机操控与数值平衡'),
        ('', '· 手机端双摇杆重做：落指相对拖动瞄准、默认扇形辅助瞄准与锁敌圈'),
        ('', '· 手机端新增右上角一键全屏按钮，支持隐藏地址栏并自动尝试横屏'),
        ('', '· 武器全界面显示伤害、实时攻速与暴击率；新增暴击、连杀与单发散布'),
        ('', '· 取消品质伤倍率，协议连星升璀璨、终端贯枪降传说任第4章专属金武'),
        ('', '· 史诗及以上近战新增 30% 概率额外挥砍（连斩），关闭玩家爆炸自伤'),
        ('', '· 上线 7 场景/副本阶梯血量，Boss 单次受击上限 15%，优化经济与回能'),
        ('', '· 品质射速收缓至 1.0~1.30，与沙氏汽水（+12%）及快速击发（+12%）统一加算'),
        ('', '· 饮品与篮球重做：血量 +25%、回蓝 1/s，篮球改 24 固伤（8% 概率 81 伤）'),
        ('', '· 第 1~4 章怪物与 Boss 伤害按 1.0× → 1.2× → 1.4× → 1.6× 阶梯递增'),
        ('', '· 修通全部 21 个局内天赋与客厅永久天赋触发，精英/宝箱/商店按章掉好枪'),
        ('', '· 接通护盾/荆棘/自愈/磁力局外词条与全部 7 档武器满级专属效果'),
        ('', '· 修复 Boss 血条遮挡角色血条、传送门旁捡武器误进门及多项底层 Bug'),
        ('h', 'v3.5 旧厂勘测记录'),
        ('', '· 机械坟场第 2 关可选高危勘测支路，首次通关获得污染结晶'),
        ('h', 'v3.3.3 手机战斗界面与双摇杆'),
        ('', '· 手机状态与地图避开按键，后台自动暂停'),
        ('', '· 攻击摇杆可调灵敏度，并可选择辅助瞄准'),
        ('h', 'v3.3.2 原生存档与性能监测'),
        ('', '· 手机原生存档持久化，并加入可选帧率显示'),
        ('h', 'v3.3.1 稳定性与存档备份'),
        ('', '· 网页及手机加入存档导入导出与触控按键设置'),
        ('h', 'v3.2 多端同步与手机触控'),
        ('', '· 手机画面保持 16:9 并按屏幕最大可用区域缩放'),
        ('', '· 手机按键及菜单点击优化，电脑与手机分别显示操作提示'),
        ('h', 'v3.1 生命系统与角色技能'),
        ('', '· 血包仅恢复生命；受伤的红心留在原位并变灰'),
        ('', '· 八名角色各有专属主动技能，按 X 施放'),
        ('h', 'v3.0.1 已有存档重开修复'),
        ('', '· 客厅加入「从第一关开新局」，永久通关记录仍保留'),
        ('', '· 旧三层断点迁移为单层关卡，断点收益归入金库'),
        ('h', 'v3.0 重开旅程 · 珍品物资'),
        ('', '· 每关一张地图，战斗房保留三波刷怪'),
        ('', '· 通关记录保留，结算后从第一关重新开始'),
        ('', '· 新增 30 把常规武器与 5 把隐藏璀璨武器'),
        ('', '· 幸运宝藏怪可掉落珍品，升级界面显示材料需求'),
        ('', '· 更新场景、角色、怪物和武器像素贴图'),
        ('h', 'v2.6 续关存档 · 新角色与结算'),
        ('', '· 传送门房间小地图环形标记，拓宽房门通道'),
        ('', '· 档案员与守种人随收集品进度解锁，可查看进度'),
        ('', '· 旧档择优导入，本层起点续关，支持立即结算'),
        ('', '· 饮料可重复饮用叠加，调整宝箱概率与伤害'),
        ('h', 'v2.5 武器库 · 远程敌人与天赋'),
        ('', '· 69 种独立武器固定品质，拾取与商店显示品质颜色'),
        ('', '· 近战可破箱、斩弹；新增三类远程怪物'),
        ('', '· 调整金币与收藏品掉率；新增免疫陷阱等天赋'),
        ('h', 'v2.4 每轮怪物增量 · 精英突袭'),
        ('', '· 战斗房三轮刷新，每轮至少五只怪物'),
        ('', '· 各轮可能出现精英怪；首领在第三轮登场'),
        ('h', 'v2.3 三轮战斗 · 饮料房'),
        ('', '· 战斗房分三轮刷新，清空后出现奖励宝箱'),
        ('', '· 每主题随机两关有饮料房，四种付费饮料带来独立效果'),
        ('', '· 商店增至四槽；新增独立血瓶、蓝瓶和五把近战武器'),
        ('', '· 蓝量翻倍、武器耗蓝降低；特殊房只保留可击碎箱子'),
        ('h', 'v2.2 双武器 · 战斗节奏'),
        ('', '· 修复第三关后重复开始；局内金币与局外金库分离'),
        ('', '· 双武器切换、耗能后手刀、近战安全距离'),
        ('', '· 战斗音效默认开启；能量靠拾取恢复'),
        ('', '· 陷阱仅在战斗房；新增独立加速带与减速带'),
        ('h', 'v2.1 收藏高光 · 七域双首领'),
        ('', '· 50 种独立武器；常规品质到红色，璀璨隐藏'),
        ('', '· 七个主题各五关，小首领和大首领造型分离'),
        ('', '· 首领概率掉落各主题金色与红色专属武器'),
        ('', '· 收集品专属图标和拾取高光播报，展示台同步更新'),
        ('', '· 图鉴显示已发现武器与怪物的基础属性'),
        ('', '· 换武器需按交互键二次确认；宝箱、陷阱重绘'),
        ('h', 'v2.0 霓虹污染 · 全面重绘'),
        ('', '· 七个场景拥有独立的地砖、墙面与霓虹环境纹理'),
        ('', '· 六名角色与 37 种图鉴怪物拥有专属像素造型'),
        ('', '· 武器增至 32 种：独立贴图、弹道节奏与彩色战斗特效'),
        ('', '· 冰霜减速、腐蚀灼烧、电弧连锁与引力牵引加入战斗'),
        ('', '· 修复掉落物与传送门重叠时无法前进的问题'),
        ('', '· 全新城市夜景主视觉；保留旧存档与线性关卡进度'),
        ('h', 'v1.0 余烬禁区 · 污染入侵与生存'),
        ('', '· 主线顺序推进，达标副本可进入；奖励副本用游戏金币购入'),
        ('', '· 修复传送门、即时存档和网页版武器；首领后天赋三选一'),
        ('h', 'v1.4.4 修复普通关卡清空后没有传送门（卡关）'),
        ('s', '—— 修复'),
        ('', '· 修复「普通关卡打完后给了钥匙却没有传送门」：此前只有首领房'),
        ('', '  才会生成传送门，普通层清空房间只解锁房门'),
        ('', '· 而传送门是通往下一层的唯一出口 —— 于是普通层玩家清光所有'),
        ('', '  房间后仍被永久困在同一层（软锁死）'),
        ('', '· 现在每层都会记录一个"目标房"（初始点最远的那间），清空它'),
        ('', '  即出现传送门，与首领层的规则保持一致'),
        ('h', 'v1.4.3 修复 PC 端键盘完全没有反应'),
        ('s', '—— 修复'),
        ('', '· 修复「人物钉死、键盘操控完全无反应」：个别机器/窗口管理器下'),
        ('', '  窗口会被判定为未聚焦，导致整张键盘状态表恒为"没按"'),
        ('', '· 现在同时用按键事件累积一份"按住的键"，与键盘状态表取并集，'),
        ('', '  只要按键事件能到达，角色就能动 —— 从根上绕开焦点问题'),
        ('', '· 窗口失焦时清空按键集合，避免"松了手角色还在自己走"'),
        ('s', '—— 诊断'),
        ('', '· 首次收到移动输入会写进 boot.log，便于定位"输入没到"还是"走不动"'),
        ('h', 'v1.4.2 网页端全面对齐 + 移动手感修复'),
        ('s', '—— 修复'),
        ('', '· 修复打击停顿把玩家也一起冻住：连续命中时"几乎无法移动"'),
        ('', '· 现在只冻结世界（敌人/子弹/陷阱），玩家移动与瞄准始终用真实时间'),
        ('', '· 打击停顿加入冷却，避免高射速下世界被永久拖慢'),
        ('s', '—— 网页端对齐（此前与本地版内容不一致）'),
        ('', '· 补齐完整存档系统：3 个存档槽 + 个人 ID + 自动保存'),
        ('', '· 补齐选档界面：开始游戏 → 选档 / 新建 / 删除（含二次确认）'),
        ('', '· 补齐分档设置：音乐 / 音效 / 震动 / 摇杆设置随档保存'),
        ('', '· 补齐进度持久化：场景进度、图鉴、收集品、展示台、货币、材料'),
        ('', '· 补齐程序合成 BGM（默认关闭，曲目随场景深度分 4 档）'),
        ('', '· 断点续玩：从存档里的关卡断点继续，而不是每次都从第 1 关开始'),
        ('h', 'v1.4.1 修复选档后无法进入游戏'),
        ('s', '—— 修复'),
        ('', '· 修复「开始游戏 → 选择存档 → 按 Enter 后又退回主菜单」的死循环'),
        ('', '· 现在选中存档（或新建存档）后会直接进入客厅，可立即出击'),
        ('h', 'v1.4  机制化品质 · 自检优化'),
        ('s', '—— 武器（需求 6 强化）'),
        ('', '· 基础型号 6 → 11 把：新增钉刺弩 / 霰流喷射器 / 磁轨狙击 / 废铁砍刀 / 等离子长刃'),
        ('', '· 新增近战武器类别：身前扇形横扫，不耗能，命中即击退'),
        ('', '· 品质升级改为「机制变化」而非单纯加数值：'),
        ('', '  绿=射速弹速｜蓝=弹丸+1｜紫=穿透+1｜金=击杀迸射｜红=命中分裂｜璀璨=追猎弹道'),
        ('', '· 近战武器随品质提升斩击范围与扇形角度'),
        ('s', '—— 战斗手感'),
        ('', '· 网页端补齐「打击停顿（hit-stop）」与「受击击退」，与 PC 端一致'),
        ('', '· 命中 / 击杀 / 受击均有不同强度的定帧，打击更有分量'),
        ('s', '—— 修复与其它'),
        ('', '· 网页端补齐暂停菜单「脱离卡死」（复位并存盘，可断点续玩）'),
        ('', '· 手机端震动真正生效（设置开启后受击触发 navigator.vibrate）'),
        ('', '· 版本号统一为 v1.4'),
        ('h', 'v1.0  「最后一片净土」'),
        ('s', '—— 全新起点'),
        ('', '· 游戏更名：《陆面过程模拟》→《最后一片净土》'),
        ('', '· 剧情重写：围绕「污染入侵 - 生存」的完整叙事'),
        ('s', '—— 流程'),
        ('', '· 关卡改为线性推进，必须 1→2→3→4 依次通关，不能跳关'),
        ('', '· 每个场景 5 关：第 3 关小首领、第 5 关大首领'),
        ('', '· 击败首领后进入传送门，触发天赋三选一'),
        ('s', '—— 养成'),
        ('', '· 货币（金币/钻石）+ 材料收集系统'),
        ('', '· 6 名角色：3 名金币解锁、1 名钻石解锁、1 名材料合成'),
        ('', '· 武器 7 级品质：白/绿/蓝/紫/金/红/璀璨，满级附加特效'),
        ('', '· 宝箱 5 类 × 2 档：货币 / 医疗 / 材料 / 武器 / 收集'),
        ('', '· 图鉴系统：37 种怪物，每场景小怪/精英/首领各不相同'),
        ('', '· 收集品 + 个人展示台'),
        ('s', '—— 存档'),
        ('', '· 个人 ID、最多 3 个存档槽、新建需覆盖选择'),
        ('', '· 一切行为自动保存，异常退出也不丢进度'),
        ('', '· 新增「脱离卡死」：卡住时一键复位并存盘退出'),
        ('s', '—— 战斗'),
        ('', '· 陷阱、掩体、奖励洞穴等场景机关'),
        ('', '· 打击停顿 + 受击击退'),
        ('', '· 防卡死机制与碰撞优化'),
        ('s', '—— 表现'),
        ('', '· 程序合成音乐 / 打击特效 / 震动（默认关闭，可在设置开启）'),
        ('', '· 手机端透明摇杆：固定 / 浮动双模式 + 灵敏度调节'),
        ('', '· 局内提示：新怪、新材料、新武器、首领出现均有简介'),
        ('', '· 传送门 / 开箱 / 购买需二次确认'),
    ]


def draw_slots(surf, game):
    """存档槽界面（需求 10）：3 个槽位 + 新建 / 覆盖 / 删除。"""
    a = game.assets
    surf.blit(a.scaled('bg_title', S.VIEW_W, S.VIEW_H), (0, 0))
    dim(surf, 200, (6, 6, 12))
    st = game.state
    U.panel(surf, (30, 20, S.VIEW_W - 60, S.VIEW_H - 40),
            (18, 16, 24, 238), (96, 86, 128), 6, 1)

    title = {'slot_create': '创建新存档',
             'slot_confirm': '确认删除存档'}.get(st, '选择存档')
    U.text_shadow(a.font(21), surf, title, (255, 226, 150),
                  S.VIEW_W // 2, 28, anchor='midtop')
    U.text_shadow(a.font(11), surf, '一台设备最多 3 个存档',
                  (150, 146, 172), S.VIEW_W // 2, 54, anchor='midtop')

    if st == 'slot_create':
        idx = int(getattr(game, 'slot_pending', 0))
        U.text_shadow(a.font(13), surf, '存档 %d  ·  输入名字（字母/数字，12 字内）'
                      % (idx + 1), (206, 202, 224), S.VIEW_W // 2, 92,
                      anchor='midtop')
        buf = (getattr(game, 'name_buf', '') or '')
        caret = '_' if (pygame.time.get_ticks() // 500) % 2 == 0 else ' '
        U.panel(surf, (S.VIEW_W // 2 - 110, 120, 220, 30),
                (34, 30, 44, 235), (170, 150, 220), 4, 2)
        U.text_shadow(a.font(15), surf, buf + caret, (255, 240, 190),
                      S.VIEW_W // 2, 126, anchor='midtop')
        U.text_shadow(a.font(11), surf, '留空则用默认名「漂泊者%d」' % (idx + 1),
                      (140, 136, 160), S.VIEW_W // 2, 162, anchor='midtop')
        U.text_shadow(a.font(11), surf, 'Enter 确认    ESC 返回',
                      (140, 136, 160), S.VIEW_W // 2, S.VIEW_H - 40,
                      anchor='midtop')
        return

    if st == 'slot_confirm':
        idx = int(getattr(game, 'slot_pending', 0))
        U.text_shadow(a.font(14), surf, '真的要删除「存档 %d」吗？' % (idx + 1),
                      (255, 170, 150), S.VIEW_W // 2, 110, anchor='midtop')
        U.text_shadow(a.font(11), surf, '该操作不可恢复（进度、货币、收集品都会消失）',
                      (206, 180, 180), S.VIEW_W // 2, 136, anchor='midtop')
        U.text_shadow(a.font(12), surf, 'Enter / Y  确认删除        ESC / N  取消',
                      (255, 226, 150), S.VIEW_W // 2, 176, anchor='midtop')
        return

    # slots 列表
    slots = game.slot_list()
    sel = int(getattr(game, 'slot_index', 0))
    for i in range(len(slots)):
        y = 84 + i * 52
        on = (i == sel)
        s = slots[i]
        bg = (44, 38, 56, 235) if on else (26, 23, 34, 210)
        U.panel(surf, (60, y, S.VIEW_W - 120, 44), bg,
                (200, 170, 240) if on else (58, 52, 74), 5, 2 if on else 1)
        U.text_shadow(a.font(12), surf, '存档 %d' % (i + 1),
                      (255, 216, 120) if on else (170, 166, 190), 70, y + 5)
        if s is None:
            U.text_shadow(a.font(12), surf, '— 空 —  （Enter 创建）',
                          (120, 116, 140), 150, y + 12)
            continue
        nm = s.get('name', '?')
        stt = s.get('stats') or {}
        # 需求 1：线性推进后，进度读 scene_prog 而不是"最高层"
        from . import progress as _PR
        from . import chapter as _C
        target = _PR.next_target(s)
        scn = _C.scene_label(target.get('scene', _C.MAIN[0]))
        stg = int(target.get('stage_idx', 0)) + 1
        U.text_shadow(a.font(13), surf, nm, (235, 230, 250), 150, y + 5)
        U.text_shadow(a.font(11), surf,
                      '%s · 第 %d 关   金币 %d   钻石 %d'
                      % (scn, stg, int(s.get('coins', 0)),
                         int(s.get('diamonds', 0))),
                      (180, 190, 220), 150, y + 24)
        U.text_shadow(a.font(10), surf,
                      '击杀 %d' % int(stt.get('kills', 0)),
                      (150, 146, 172), S.VIEW_W - 76, y + 24, anchor='topright')
    U.text_shadow(a.font(11), surf,
                  '↑↓ 选择    Enter 进入 / 创建    D 删除    ESC 返回',
                  (140, 136, 160), S.VIEW_W // 2, S.VIEW_H - 36, anchor='midtop')


def draw_confirm(surf, game):
    """需求 18：二次确认浮层。"""
    cp = getattr(game, 'confirm_prompt', None)
    if not cp:
        return
    a = game.assets
    dim(surf, 150, (0, 0, 0))
    w, h = 340, 96
    x = (S.VIEW_W - w) // 2
    y = (S.VIEW_H - h) // 2
    t = float(getattr(game, 'confirm_t', 0.0))
    pop = min(1.0, t / 0.12)
    h2 = int(h * (0.7 + 0.3 * pop))
    y2 = y + (h - h2) // 2
    U.panel(surf, (x, y2, w, h2), (24, 20, 32, 245), (255, 214, 130), 6, 2)
    U.text_shadow(a.font(15), surf, cp.get('title', ''), (255, 232, 160),
                  S.VIEW_W // 2, y2 + 12, anchor='midtop')
    U.text_shadow(a.font(11), surf, cp.get('sub', ''), (208, 204, 226),
                  S.VIEW_W // 2, y2 + 38, anchor='midtop')
    U.text_shadow(a.font(11), surf, 'Enter / E  确认        ESC  取消',
                  (160, 210, 190), S.VIEW_W // 2, y2 + 62, anchor='midtop')


def _setting_rows(game):
    """需求 12/15：设置项 = (显示名, 设置键, 类型)。
    类型 bool 直接切换；mode 在候选值间循环；num 调数值。
    """
    st = getattr(game, 'setting', {}) or {}
    rows = [
        ('程序合成音乐', 'music', 'bool'),
        ('打击音效', 'sfx', 'bool'),
        ('屏幕震动', 'shake', 'bool'),
        ('受击震动（手机端）', 'vibrate', 'bool'),
        ('摇杆模式', 'joystick', 'mode'),
        ('摇杆灵敏度', 'joy_sens', 'num'),
    ]
    return rows, st


_JOY_MODES = ('float', 'fixed')
_JOY_MODE_CN = {'float': '浮动', 'fixed': '固定'}


def _setting_value_text(key, typ, st):
    if typ == 'bool':
        return '开' if st.get(key) else '关'
    if typ == 'mode':
        return _JOY_MODE_CN.get(st.get(key, 'float'), '浮动')
    if typ == 'num':
        try:
            return '%.1f' % float(st.get(key, 1.0))
        except Exception:
            return '1.0'
    return str(st.get(key, ''))


def draw_help(surf, game):
    """需求 12/15/18：操作说明 + 可交互设置（音乐/音效/震动/摇杆）。"""
    a = game.assets
    dim(surf, 205, (6, 6, 12))
    U.text_shadow(a.font(22), surf, '操作说明 / 设置', S.C_TEXT,
                  S.VIEW_W // 2, 12, anchor='midtop')
    lines = [
        ('W A S D  /  方向键', '八方向移动'),
        ('鼠标移动', '瞄准（角色朝鼠标方向）'),
        ('鼠标左键 / 空格', '射击（可长按连射）'),
        ('Shift / 右键', '冲刺翻滚（短无敌）'),
        ('E / F', '交互（开宝箱、买东西、换武器）'),
        ('X', '角色专属技能'),
        ('ESC / P', '暂停 / 返回'),
        ('F11', '全屏切换'),
        ('M', '静音切换'),
    ]
    y = 44
    for k, v in lines:
        U.text_shadow(a.font(12), surf, k, (255, 226, 150), 30, y)
        U.text_shadow(a.font(12), surf, v, S.C_TEXT_DIM, 196, y)
        y += 20

    # ---- 右侧：可交互设置（↑↓ 选择，Enter/←→ 调整）
    rows, st = _setting_rows(game)
    sel = int(getattr(game, 'setting_index', 0)) % max(1, len(rows))
    x0 = 372
    U.text_shadow(a.font(13), surf, '设 置', (255, 236, 170), x0, 44)
    for i, (label, key, typ) in enumerate(rows):
        on = (i == sel)
        yy = 70 + i * 26
        col = (255, 236, 170) if on else (176, 172, 196)
        if on:
            hl = pygame.Surface((236, 22), pygame.SRCALPHA)
            hl.fill((120, 90, 200, 70))
            surf.blit(hl, (x0 - 6, yy - 3))
        U.text_shadow(a.font(12), surf, ('▶ ' if on else '  ') + label,
                      col, x0, yy)
        val = _setting_value_text(key, typ, st)
        vcol = (150, 230, 180) if val in ('开',) else (176, 172, 196)
        if typ == 'bool' and val == '关':
            vcol = (170, 150, 150)
        U.text_shadow(a.font(12), surf, val, vcol, x0 + 62, yy)

    U.text_shadow(a.font(11), surf,
                  '↑↓ 选择   Enter / ←→ 调整   ESC 返回',
                  (140, 136, 160), S.VIEW_W // 2, S.VIEW_H - 22,
                  anchor='midtop')


def draw_pause(surf, game):
    a = game.assets
    dim(surf, 175, (6, 6, 12))
    U.text_shadow(a.font(30), surf, '暂 停', S.C_TEXT,
                  S.VIEW_W // 2, 84, anchor='midtop')
    items = game.pause_items
    for i, (label, _) in enumerate(items):
        sel = (i == game.pause_index)
        y = 122 + i * 30
        f = a.font(17 if sel else 15)
        col = (255, 236, 170) if sel else (176, 172, 196)
        w = f.size(label)[0]
        if sel:
            hl = pygame.Surface((w + 36, 26), pygame.SRCALPHA)
            hl.fill((120, 90, 200, 70))
            surf.blit(hl, (S.VIEW_W // 2 - w // 2 - 18, y - 5))
        U.text_shadow(f, surf, label, col, S.VIEW_W // 2 - w // 2, y - 2)
    U.text_shadow(a.font(11), surf, '↑↓ 选择   Enter 确认   ESC 继续游戏',
                  (140, 136, 160), S.VIEW_W // 2, S.VIEW_H - 26, anchor='midtop')


def draw_gameover(surf, game):
    a = game.assets
    dim(surf, 200, (10, 4, 8))
    U.text_shadow(a.font(34), surf, '你 倒 下 了', (226, 72, 84),
                  S.VIEW_W // 2, 46, anchor='midtop')
    rows = [
        ('抵达层数', f'第 {game.floor} 层'),
        ('累计击杀', str(game.kills)),
        ('拾取金币', str(game.coins)),
        ('射击次数', str(game.player.shots)),
        ('承受伤害', f'{int(game.total_damage)}'),
    ]
    y = 108
    for k, v in rows:
        U.text_shadow(a.font(14), surf, k, S.C_TEXT_DIM, 216, y)
        U.text_shadow(a.font(14), surf, v, S.C_TEXT, 384, y)
        y += 26
    items = game.over_items
    for i, (label, _) in enumerate(items):
        sel = (i == game.over_index)
        y2 = y + 14 + i * 30
        f = a.font(16 if sel else 14)
        col = (255, 236, 170) if sel else (176, 172, 196)
        w = f.size(label)[0]
        if sel:
            hl = pygame.Surface((w + 36, 24), pygame.SRCALPHA)
            hl.fill((120, 90, 200, 70))
            surf.blit(hl, (S.VIEW_W // 2 - w // 2 - 18, y2 - 4))
        U.text_shadow(f, surf, label, col, S.VIEW_W // 2 - w // 2, y2 - 2)


def draw_levelclear(surf, game):
    a = game.assets
    dim(surf, 190, (6, 8, 12))
    U.text_shadow(a.font(30), surf, f'第 {game.floor} 层  通过！', (150, 240, 190),
                  S.VIEW_W // 2, 76, anchor='midtop')
    U.text_shadow(a.font(14), surf,
                  f'当前金币 {game.coins}    累计击杀 {game.kills}',
                  S.C_TEXT_DIM, S.VIEW_W // 2, 122, anchor='midtop')
    U.text_shadow(a.font(14), surf,
                  '生命与能量已部分恢复，武器保留',
                  (255, 226, 150), S.VIEW_W // 2, 150, anchor='midtop')
    U.text_shadow(a.font(16), surf, '按 Enter 进入下一关',
                  S.C_TEXT, S.VIEW_W // 2, 208, anchor='midtop')
    U.text_shadow(a.font(12), surf, '按 S 立即结算收益并返回主界面',
                  (255, 226, 150), S.VIEW_W // 2, 242, anchor='midtop')


def draw_victory(surf, game):
    a = game.assets
    dim(surf, 190, (8, 6, 14))
    t = pygame.time.get_ticks() / 1000.0
    U.text_shadow(a.font(34), surf, '通 关 ！！！', (255, 226, 120),
                  S.VIEW_W // 2, 40 + math.sin(t * 3) * 2, anchor='midtop')
    U.text_shadow(a.font(14), surf, '你净化了污染核心，地表重归宁静',
                  (170, 240, 200), S.VIEW_W // 2, 88, anchor='midtop')
    rows = [
        ('最终层数', f'{S.FLOORS} 层全通'),
        ('累计击杀', str(game.kills)),
        ('拾取金币', str(game.coins)),
        ('射击次数', str(game.player.shots)),
        ('剩余生命', f'{int(game.player.hp)} / {int(game.player.max_hp)}'),
        ('总用时', f'{int(game.total_time // 60)} 分 {int(game.total_time % 60)} 秒'),
    ]
    y = 122
    for k, v in rows:
        U.text_shadow(a.font(14), surf, k, S.C_TEXT_DIM, 216, y)
        U.text_shadow(a.font(14), surf, v, S.C_TEXT, 384, y)
        y += 24
    items = game.over_items
    for i, (label, _) in enumerate(items):
        sel = (i == game.over_index)
        y2 = y + 12 + i * 28
        f = a.font(16 if sel else 14)
        col = (255, 236, 170) if sel else (176, 172, 196)
        w = f.size(label)[0]
        if sel:
            hl = pygame.Surface((w + 36, 24), pygame.SRCALPHA)
            hl.fill((120, 90, 200, 70))
            surf.blit(hl, (S.VIEW_W // 2 - w // 2 - 18, y2 - 4))
        U.text_shadow(f, surf, label, col, S.VIEW_W // 2 - w // 2, y2 - 2)


def draw_flash(surf, game):
    if game.fx.flash > 0.01:
        o = pygame.Surface((S.VIEW_W, S.VIEW_H), pygame.SRCALPHA)
        c = game.fx.flash_color
        o.fill((c[0], c[1], c[2], int(min(200, game.fx.flash * 420))))
        surf.blit(o, (0, 0))


def draw_transition(surf, game):
    if game.trans_fade > 0:
        t = game.trans_fade / 0.30
        o = pygame.Surface((S.VIEW_W, S.VIEW_H), pygame.SRCALPHA)
        o.fill((8, 7, 12, int(min(255, 235 * t))))
        surf.blit(o, (0, 0))


# ================================================================ 副本机制卡
# 1.3 需求 2：副本条件不再是干巴巴的数字，而是绑定到前置场景里真实存在的
# 怪物/陷阱上。这个函数供客厅的"关卡地图"调用，把条件展开成可读的卡片。
def draw_dungeon_bind(surf, game, dkey, x, y, w, max_h=120):
    """绘制某个副本的"场景叙事绑定"区块。

    返回实际占用的高度。没有绑定数据时返回 0（不占位）。
    版式：
      [机制卡]  腐壳虫 —— 下水道的基础单位，数量极多…
      [机制卡]  毒池   —— 站上去持续掉血，是"踩中陷阱"的主力
      —— 战术：想少踩陷阱，贴着墙走。
    """
    try:
        from . import chapter as C
    except Exception:
        return 0
    cards = C.dungeon_bind_cards(dkey)
    tip = C.dungeon_tip(dkey)
    if not cards and not tip:
        return 0
    a = game.assets
    f10 = a.font(10)
    f11 = a.font(11)
    used = 0
    pad = 5
    for c in cards:
        if used + 26 > max_h:
            break
        ry = y + used
        is_enemy = (c['kind'] == 'enemy')
        accent = (226, 140, 120) if is_enemy else (140, 220, 160)
        U.panel(surf, (x, ry, w, 24), (26, 22, 30, 210), accent, 4, 1)
        tag = '怪' if is_enemy else '陷阱'
        # 标签徽章
        U.panel(surf, (x + 3, ry + 5, 22, 13), (40, 30, 36, 230),
                accent, 3, 1)
        surf.blit(f10.render(tag, True, accent), (x + 7, ry + 6))
        surf.blit(f11.render(c['name'], True, S.C_TEXT), (x + 29, ry + 3))
        # 说明（单行截断，避免溢出）
        desc = c['desc']
        while desc and f10.size(desc)[0] > w - 36:
            desc = desc[:-1]
        if desc != c['desc']:
            desc = desc[:-1] + '…'
        surf.blit(f10.render(desc, True, S.C_TEXT_DIM), (x + 29, ry + 14))
        used += 26
    if tip and used + 16 <= max_h:
        ty = y + used + 1
        words = '战术：' + tip
        while words and f10.size(words)[0] > w - 4:
            words = words[:-1]
        if words != '战术：' + tip:
            words = words[:-1] + '…'
        surf.blit(f10.render(words, True, (200, 200, 150)), (x + 2, ty))
        used += 14
    return used + pad


# ================================================================ 客厅（1.0 需求 16）
# 客厅是"主菜单 -> 开始游戏"之间的二级界面（需求 16：战斗准备）。
# 1.4 起客厅**不再让玩家选关**（需求 1：线性锁死），而是：
#   · 左栏：战斗准备菜单（出击 / 角色 / 武器 / 天赋 / 图鉴 / 展示台 / 更新日志）
#   · 右栏：当前"下一站"的详情卡 + 全 7 场景的进度地图（纯展示）
LOBBY_CARD_H = 34
LOBBY_GAP = 5
LOBBY_PREP_Y = 76          # 准备菜单起始 y
LOBBY_PREP_H = 22          # 每项高度
LOBBY_PREP_GAP = 3


def _fit_text(font, s, max_w):
    """按像素宽度截断字符串，末尾加省略号。"""
    if font.size(s)[0] <= max_w:
        return s
    s = s.rstrip()
    while s and font.size(s + '…')[0] > max_w:
        s = s[:-1]
    return (s + '…') if s else ''


def _arrow(surf, font, x, y, left=True):
    """在 (x, y) 画一个小三角，用作"还有内容可展开"的指示。"""
    d = 5
    if left:
        pts = [(x + d, y), (x + d, y + 2 * d), (x, y + d)]
    else:
        pts = [(x, y), (x, y + 2 * d), (x + d, y + d)]
    pygame.draw.polygon(surf, (210, 200, 160), pts)


def draw_lobby(surf, game):
    """战斗准备界面（需求 16）+ 进度地图 + 养成。

    四个分页（TAB 切换）：
      [0] 准备  —— 战斗准备菜单 + 下一站详情 + 全场景进度
      [1] 养成  —— 角色 / 武器 / 技能被动 / 天赋（需求 4/5/6/7）
      [2] 图鉴  —— 怪物 / 武器 / 材料 / 收集品 四类，已发现的显示详情
      [3] 展示台—— 6 个格子，摆放已获得的收集品（需求 9）
    """
    from . import progress as PR
    from . import chapter as C

    a = game.assets
    prof = game.profile
    dim(surf, 226, (6, 6, 12))
    U.panel(surf, (6, 26, S.VIEW_W - 12, S.VIEW_H - 54), (18, 16, 24, 216),
            (78, 70, 104), 5, 1)

    tab = int(getattr(game, 'lobby_tab', 0)) % 4
    U.text_shadow(a.font(19), surf, '净 土 营 地', (255, 226, 150),
                  S.VIEW_W // 2, 2, anchor='midtop')
    tabs = [('准备', 0), ('养成', 1), ('图鉴', 2), ('展示台', 3)]
    tx = S.VIEW_W // 2 - 124
    for label, i in tabs:
        on = (i == tab)
        w = a.font(11).size(label)[0] + 20
        U.panel(surf, (tx, 30, w, 17),
                (60, 48, 84, 235) if on else (28, 25, 36, 190),
                (200, 170, 240) if on else (60, 54, 76), 4, 1)
        U.text_shadow(a.font(11), surf, label,
                      (255, 240, 190) if on else (150, 146, 172),
                      tx + w // 2, 33, anchor='midtop')
        tx += w + 5

    # ---------------- 顶部资源条
    coins = int((prof or {}).get('coins', 0))
    dias = int((prof or {}).get('diamonds', 0))
    from . import gamedata as _GD
    U.text_shadow(a.font(11), surf,
                  '金币 %d/%d' % (coins, _GD.COIN_CAP), (255, 216, 120), 16, 32)
    U.text_shadow(a.font(11), surf,
                  '钻石 %d/%d' % (dias, _GD.DIAMOND_CAP), S.C_DIA, 16, 46)
    char = (getattr(game, 'char_key', None)
            or (prof or {}).get('char') or 'scout')
    try:
        cn = _GD.char(char)['name']
    except Exception:
        cn = char
    nm = (prof or {}).get('name', '漂泊者')
    U.text_shadow(a.font(11), surf, '%s  ·  %s' % (nm, cn),
                  (190, 200, 230), S.VIEW_W - 16, 32, anchor='topright')
    if tab == 0:
        hint = '↑↓ 选项目   Enter 确认   TAB 分页'
    elif tab == 1:
        hint = '←→ 换子页   ↑↓ 选条目   Enter 购买/强化'
    elif tab == 2:
        hint = '←→ 切换分类   ↑↓ 翻页'
    else:
        hint = '←→ 换格子   E 取出'
    U.text_shadow(a.font(10), surf, hint, (150, 146, 172),
                  S.VIEW_W - 16, 46, anchor='topright')

    if tab == 0:
        _lobby_tab_levels(surf, game, PR, C)
    elif tab == 1:
        _lobby_tab_growth(surf, game)
    elif tab == 2:
        _lobby_tab_codex(surf, game, C)
    else:
        _lobby_tab_showcase(surf, game)

    if tab == 0:
        tip = 'ESC 返回主菜单   TAB 切换分页   ↑↓ 选择   Enter 确认'
    elif tab == 1:
        tip = 'ESC 返回主菜单   ←→ 换子页   Enter 购买 / 强化装备'
    elif tab == 2:
        tip = 'ESC 返回主菜单   ←→ 切换分类   TAB 切换分页'
    else:
        tip = 'ESC 返回主菜单   ←→ 换格子   TAB 切换分页'
    U.text_shadow(a.font(11), surf, tip, (150, 146, 172),
                  S.VIEW_W // 2, S.VIEW_H - 18, anchor='midtop')
    return int(getattr(game, 'lobby_index', 0))


# ================================================================ 养成分页
_GROWTH_SUBS = ['角色', '武器', '技能 / 被动', '天赋']


def _lobby_tab_growth(surf, game):
    """分页 2：养成（角色 / 武器 / 技能被动 / 天赋）。"""
    a = game.assets
    prof = game.profile
    sub = int(getattr(game, 'growth_sub', 0)) % 4
    sel = int(getattr(game, 'growth_index', 0))

    # ---------------- 子页签
    sx = 20
    for i, label in enumerate(_GROWTH_SUBS):
        on = (i == sub)
        w = a.font(11).size(label)[0] + 18
        U.panel(surf, (sx, 58, w, 16),
                (60, 48, 84, 235) if on else (26, 23, 34, 190),
                (200, 170, 240) if on else (56, 50, 70), 4, 1)
        U.text_shadow(a.font(11), surf, label,
                      (255, 240, 190) if on else (150, 146, 172),
                      sx + w // 2, 60, anchor='midtop')
        sx += w + 5

    rows = game._growth_rows()
    if not rows:
        U.text_shadow(a.font(12), surf, '（暂无内容）', (140, 136, 166),
                      S.VIEW_W // 2, S.VIEW_H // 2, anchor='midtop')
        return

    # ---------------- 左栏：条目列表
    lx, lw = 16, 200
    ly = 82
    ih = 26
    visible = max(1, (S.VIEW_H - 60 - ly) // ih)
    sel = sel % len(rows)
    first = max(0, min(sel - visible // 2, max(0, len(rows) - visible)))
    for vi in range(visible):
        i = first + vi
        if i >= len(rows):
            break
        r = rows[i]
        on = (i == sel)
        y = ly + vi * ih
        U.panel(surf, (lx, y, lw, ih - 2),
                (52, 44, 68, 240) if on else (26, 23, 34, 190),
                (200, 170, 240) if on else (56, 50, 70), 4, 2 if on else 1)
        if on:
            U.panel(surf, (lx, y, 3, ih - 2), (200, 170, 240),
                    (200, 170, 240), 0, 0)
        _growth_row_left(surf, a, game, sub, r, lx, y, lw, on)

    # ---------------- 右栏：详情
    rx = lx + lw + 10
    rw = S.VIEW_W - 16 - rx
    _growth_detail(surf, a, game, sub, rows[sel], rx, 82, rw)

    # ---------------- 底部：材料背包
    _growth_mats_bar(surf, a, game)


def _growth_row_left(surf, a, game, sub, r, x, y, w, on):
    """列表行：图标 + 名称 + 右侧状态。"""
    name = r.get('name', r.get('key', '?'))
    col = (255, 240, 190) if on else (196, 192, 214)
    if sub == 0:
        # 角色：拥有 / 装备中 / 可买（绿色）/ 买不起（灰）
        tag, tcol = '', (150, 146, 172)
        if r.get('cur'):
            tag, tcol = '出战', (150, 240, 190)
        elif r.get('owned'):
            tag, tcol = '已解锁', (200, 220, 250)
        elif r.get('afford'):
            tag, tcol = '可解锁', (170, 240, 170)
        else:
            tag, tcol = '不足', (226, 140, 120)
        icon = '人'
    elif sub == 1:
        # 武器：Lv + 品质名（用品质色）
        tag = 'Lv.%d %s' % (int(r.get('lv', 0)), r.get('quality_name', ''))
        tcol = r.get('quality_color', (200, 200, 220))
        icon = '枪'
    elif sub == 2:
        mx = int(r.get('max', 1))
        tag = 'Lv.%d/%d' % (int(r.get('lv', 0)), mx)
        tcol = ((150, 240, 190) if int(r.get('lv', 0)) >= mx
                else (200, 220, 250))
        icon = '技' if not r.get('is_passive') else '被'
    else:
        tag = 'Lv.%d/%d' % (int(r.get('lv', 0)), int(r.get('max', 5)))
        tcol = (r.get('color') or (200, 200, 220))
        icon = '星'
    surf.blit(a.font(11).render(icon, True, (255, 226, 150) if on
                                else (140, 132, 170)), (x + 7, y + 4))
    nm = _fit_text(a.font(11), name, w - 70)
    surf.blit(a.font(11).render(nm, True, col), (x + 24, y + 4))
    tw = a.font(9).size(tag)[0]
    surf.blit(a.font(9).render(tag, True, tcol), (x + w - 8 - tw, y + 6))


def _growth_detail(surf, a, game, sub, r, x, y, w):
    """右栏详情卡：属性 / 花费 / 操作提示。"""
    from . import gamedata as GD
    prof = game.profile
    rows = []
    def add_materials(cost):
        mats = (cost or (0, {}))[1] or {}
        if not mats:
            rows.append(('材料', '无'))
        else:
            owned = (prof or {}).get('materials') or {}
            for key, amount in mats.items():
                rows.append((GD.mat_name(key), '需 %d · 持有 %d' %
                             (amount, int(owned.get(key, 0)))))
    if sub == 0:
        from .character_skills import SKILLS, DETAILS
        skey = r.get('key', 'scout')
        skill_name, skill_cd, _, _ = SKILLS.get(skey, SKILLS['scout'])
        rows.append(('解锁', r.get('unlock_text', '')))
        rows.append(('生命', str(r.get('hp', '-'))))
        rows.append(('速度', '%.0f' % float(r.get('spd', 0))))
        rows.append(('能量', '%.0f' % float(r.get('energy', 0))))
        rows.append(('初始武器', r.get('starter_name', '')))
        rows.append(('特性', r.get('perk', '')))
        rows.append(('主动技能', '%s · %ds冷却' % (skill_name, skill_cd)))
        rows.append(('技能效果', DETAILS.get(skey, DETAILS['scout'])))
    elif sub == 1:
        wk = r.get('key', 'pistol')
        wq = r.get('quality', 'white')
        wlv = int(r.get('lv', 0))
        try:
            qspec = W.apply_quality(W.get(wk), wq, 1.0)
        except Exception:
            qspec = W.get(wk)
        sk_p = (prof or {}).get('skills') or {}
        pv_p = (prof or {}).get('passives') or {}
        p_bonus = 1.0 + 0.04 * int(sk_p.get('power', 0))
        q_perk = 1.15 if GD.quality_rank(wq) > 2 and wlv >= GD.max_level(wq) else 1.0
        real_dmg = max(1, int(round(qspec.dmg * float(r.get('mul', 1.0)) * q_perk * p_bonus)))
        dmg_str = f'{real_dmg}×{qspec.count}' if qspec.count > 1 else str(real_dmg)
        c_rate = 0.08 + 0.04 * int(pv_p.get('crit', 0))
        if wq in ('green', 'radiant') and wlv >= GD.max_level(wq):
            c_rate += 0.06
        c_pct = int(round(min(0.65, c_rate) * 100))
        spd_rate = float(W.quality_mech(wq).get('rate', 1.0))
        if wq in ('white', 'radiant') and wlv >= GD.max_level(wq):
            spd_rate += 0.08
        rows.append(('强化等级', 'Lv.%d' % wlv))
        rows.append(('当前品质', '%s（伤害 ×%.2f）'
                     % (r.get('quality_name', ''), float(r.get('mul', 1.0)))))
        rows.append(('武器伤害', dmg_str))
        rows.append(('攻击速度', f'{spd_rate / max(0.01, float(getattr(W.get(wk), "cd", 0.25) or 0.25)):.1f} 次/秒'))
        rows.append(('暴击率', f'{c_pct}%（暴击 1.5×）'))
        nxt = r.get('next_quality_at')
        rows.append(('下个品质', ('强化到 Lv.%d' % nxt) if nxt else '已达上限'))
        c = r.get('cost') or (0, {})
        rows.append(('金币', '%d' % c[0]))
        add_materials(c)
    elif sub == 2:
        rows.append(('说明', r.get('desc', '')))
        rows.append(('等级', 'Lv.%d / %d' % (int(r.get('lv', 0)),
                                             int(r.get('max', 1)))))
        c = r.get('cost')
        if c:
            rows.append(('金币', '%d' % c[0]))
            add_materials(c)
        else:
            rows.append(('状态', '已满级'))
    else:
        rows.append(('说明', r.get('desc', '')))
        rows.append(('等级', 'Lv.%d / %d' % (int(r.get('lv', 0)),
                                             int(r.get('max', 5)))))
        if prof is not None:
            from . import growth as GR
            c = GR.talent_upgrade_cost(prof, r.get('key'))
            rows.append(('金币', '%d' % c[0]))
            add_materials(c)

    h = 34 + len(rows) * 15
    U.panel(surf, (x, y, w, h), (30, 26, 40, 230), (110, 96, 140), 4, 1)
    U.text_shadow(a.font(12), surf, r.get('name', ''),
                  (255, 236, 170), x + 8, y + 4)
    yy = y + 22
    for k, v in rows:
        U.text_shadow(a.font(10), surf, k, (150, 146, 172), x + 8, yy)
        U.text_shadow(a.font(10), surf, _fit_text(a.font(10), str(v), w - 78),
                      (216, 214, 232), x + 70, yy)
        yy += 15

    # 操作提示
    tipy = y + h + 8
    act = ''
    if sub == 0:
        if r.get('cur'):
            act = '已装备'
        elif r.get('owned'):
            act = 'Enter 换上该角色'
        elif r.get('afford'):
            act = 'Enter 解锁（%s）' % r.get('unlock_text', '')
        else:
            act = r.get('reason', '条件不足')
    elif sub == 1:
        act = ('Enter 强化（金币 %d）' % (r.get('cost') or (0,))[0]
               if (r.get('cost') or (0,))[0] else '已达上限')
    elif sub == 2:
        act = ('Enter 升级（金币 %d）' % (r.get('cost') or (0,))[0]
               if r.get('cost') else '已满级')
    else:
        act = 'Enter 升级（永久强化）'
    ok, reason = True, ''
    if prof is not None and sub == 0 and not r.get('owned'):
        ok, reason = r.get('afford'), r.get('reason', '')
    U.text_shadow(a.font(10), surf,
                  act if ok else (reason or '条件不足'),
                  (170, 240, 190) if ok else (226, 150, 150), x + 8, tipy)


def _growth_mats_bar(surf, a, game):
    """底部材料背包条。"""
    from . import growth as GR
    from . import gamedata as GD
    prof = game.profile
    rows = GR.material_summary(prof)
    y = S.VIEW_H - 40
    U.text_shadow(a.font(10), surf, '材料', (150, 146, 172), 16, y)
    x = 52
    if not rows:
        U.text_shadow(a.font(10), surf, '（空）', (110, 106, 128), x, y)
        return
    for key, name, tier, n in rows[:8]:
        txt = '%s %d' % (name, n)
        tw = a.font(10).size(txt)[0]
        if x + tw > S.VIEW_W - 16:
            break
        col = {'1': (170, 200, 230), '2': (150, 230, 190),
               '3': (200, 170, 250)}.get(str(tier), (170, 200, 230))
        surf.blit(a.font(10).render(txt, True, col), (x, y))
        x += tw + 12


def _lobby_tab_levels(surf, game, PR, C):
    """分页 1：战斗准备菜单（左）+ 下一站详情与进度地图（右）。"""
    a = game.assets
    prof = game.profile
    sel = int(getattr(game, 'lobby_index', 0))
    items = game._lobby_prep_items()

    # ---------------- 左栏：准备菜单
    lx, lw = 16, 148
    ly = LOBBY_PREP_Y
    for i, (act, label) in enumerate(items):
        on = (i == sel)
        y = ly + i * (LOBBY_PREP_H + LOBBY_PREP_GAP)
        bg = (52, 44, 68, 240) if on else (26, 23, 34, 200)
        U.panel(surf, (lx, y, lw, LOBBY_PREP_H), bg,
                (200, 170, 240) if on else (56, 50, 70), 4, 2 if on else 1)
        if on:
            U.panel(surf, (lx, y, 3, LOBBY_PREP_H),
                    (200, 170, 240), (200, 170, 240), 0, 0)
        col = (255, 240, 190) if on else (196, 192, 214)
        icon = {'enter': '▶', 'new_cycle': '新', 'char': '人', 'weapon': '枪', 'talent': '星',
                'codex': '鉴', 'showcase': '台', 'log': '志'}.get(act, '·')
        surf.blit(a.font(12).render(icon, True,
                                    (255, 226, 150) if on else (140, 132, 170)),
                  (lx + 9, y + 4))
        surf.blit(a.font(12).render(label, True, col), (lx + 28, y + 4))
        # 右侧角标：显示状态摘要
        extra = ''
        if act == 'enter':
            extra = '出发'
        elif act == 'char':
            extra = _GDc(prof).get('char_name', '')
        elif act == 'weapon':
            extra = _GDc(prof).get('weapon_name', '')
        if extra:
            ew = a.font(10).size(extra)[0]
            surf.blit(a.font(10).render(extra, True, (150, 180, 220)),
                      (lx + lw - 8 - ew, y + 6))

    # 左栏底部：玩家统计
    st = (prof or {}).get('stats') or {}
    U.text_shadow(a.font(10), surf,
                  '击杀 %d   首领 %d' % (int(st.get('kills', 0)),
                                         int(st.get('boss_kills', 0))),
                  (150, 146, 172), lx, ly + len(items) * (LOBBY_PREP_H + 3) + 6)

    # ---------------- 右栏：下一站 + 进度地图
    rx = lx + lw + 10
    rw = S.VIEW_W - 16 - rx
    _lobby_next_card(surf, game, rx, LOBBY_PREP_Y, rw, PR, C)
    _lobby_progress_map(surf, game, rx, LOBBY_PREP_Y + 62, rw, PR, C)


def _GDc(prof):
    """给准备菜单用的角色/武器名摘要。"""
    from . import gamedata as G
    out = {'char_name': '', 'weapon_name': ''}
    try:
        ck = (prof or {}).get('char') or 'scout'
        out['char_name'] = G.char(ck)['name']
    except Exception:
        pass
    try:
        from . import weapon as W
        wk = (prof or {}).get('weapon') or 'pistol'
        out['weapon_name'] = W.get(wk).name
    except Exception:
        pass
    return out


def _lobby_next_card(surf, game, x, y, w, PR, C):
    """右栏上：**下一站**（线性推进下唯一可进入的关卡）。"""
    a = game.assets
    prof = game.profile
    tgt = game._lobby_target() if prof else {'scene': C.MAIN[0], 'stage_idx': 0}
    sc = tgt.get('scene')
    U.panel(surf, (x, y, w, 56), (30, 26, 40, 230), (110, 96, 140), 4, 1)
    U.text_shadow(a.font(10), surf, '下 一 站', (150, 146, 172), x + 8, y + 3)
    if sc is None:
        U.text_shadow(a.font(14), surf, '主线已通关',
                      (255, 226, 150), x + 8, y + 16)
        U.text_shadow(a.font(10), surf,
                      '购买奖励副本后可继续（客厅内）',
                      (200, 190, 220), x + 8, y + 36)
        return
    si = int(tgt.get('stage_idx', 0))
    info = C.scene_info(sc)
    kind = C.stage_kind(si)
    ktag = {'miniboss': ' · 精英首领', 'boss': ' · 污染核心'}.get(kind, '')
    U.text_shadow(a.font(14), surf,
                  '%s · 第 %d 关%s' % (info['name'], si + 1, ktag),
                  (255, 240, 190), x + 8, y + 15)
    # 污染读数
    p = PR.pollution(sc, si) if hasattr(PR, 'pollution') else None
    line = ''
    if p:
        line = '污染浓度 %d%%' % int(p.get('pct', 0))
    dots = ''
    for i in range(C.STAGES_PER_SCENE):
        done = (PR.scene_prog(prof, sc) > i) if prof else False
        dots += '●' if done else ('◉' if i == si else '○')
    U.text_shadow(a.font(10), surf, '%s   进度 %s' % (line, dots),
                  (190, 200, 230), x + 8, y + 36)


def _lobby_progress_map(surf, game, x, y, w, PR, C):
    """右栏下：全 7 场景的进度地图（纯展示，不可点入 —— 需求 1 锁死选关）。"""
    a = game.assets
    prof = game.profile
    U.text_shadow(a.font(10), surf, '进 度 地 图', (150, 146, 172), x, y)
    ly = y + 14
    for i, key in enumerate(PR.scene_order(prof or {})):
        info = C.scene_info(key)
        unlocked = PR.is_scene_unlocked(prof, key) if prof else (i == 0)
        prog = PR.scene_prog(prof, key) if prof else 0
        cleared = prog >= C.STAGES_PER_SCENE
        recorded = PR.is_scene_cleared(prof, key) if prof else False
        is_bonus = (key == C.BONUS)
        is_dun = key in C.DUNGEONS
        tint = info.get('tint', (140, 140, 140))
        if not unlocked:
            bg, bd, tc = (20, 18, 26, 200), (48, 44, 58), (96, 92, 108)
        elif cleared:
            bg, bd, tc = (26, 34, 30, 220), (96, 130, 100), (150, 200, 160)
        else:
            bg, bd, tc = (30, 26, 40, 230), tint, (225, 220, 240)
        U.panel(surf, (x, ly, w, 20), bg, bd, 3, 1)
        tag = '主' if key in C.MAIN else ('奖' if is_bonus else '副')
        tcol = (255, 226, 150) if is_bonus else (
            (200, 160, 250) if is_dun else (150, 200, 230))
        if not unlocked:
            tcol = (110, 106, 122)
        U.panel(surf, (x + 4, ly + 4, 15, 13), (18, 16, 24, 230), tcol, 3, 1)
        surf.blit(a.font(9).render(tag, True, tcol), (x + 6, ly + 5))
        surf.blit(a.font(11).render(_fit_text(a.font(11), info['name'], 92),
                                    True, tc), (x + 24, ly + 3))
        # 右侧：锁 / 进度 / 通关
        if not unlocked:
            mark, mcol = '锁定', (110, 106, 122)
        elif cleared:
            mark, mcol = '已通关', (150, 200, 160)
        elif recorded:
            mark, mcol = '再战 %d/%d' % (prog, C.STAGES_PER_SCENE), (255, 216, 120)
        else:
            mark, mcol = '%d/%d' % (prog, C.STAGES_PER_SCENE), (255, 216, 120)
        mw = a.font(10).size(mark)[0]
        surf.blit(a.font(10).render(mark, True, mcol), (x + w - 8 - mw, ly + 4))
        ly += 22


def _lobby_tab_codex(surf, game, C):
    """分页 2：图鉴。四类条目列表，已发现的显示详情。"""
    from . import codex as CX
    a = game.assets
    prof = game.profile
    cats = ['enemy', 'weapon', 'material', 'collect']
    ci = int(getattr(game, 'codex_cat', 0)) % len(cats)
    cat = cats[ci]
    seen = set()
    if prof:
        seen = set((prof.get('codex') or {}).get(cat, []) or [])

    # 分类标签
    x = 16
    for i, k in enumerate(cats):
        label = CX.CODEX_CATS.get(k, k)
        cnt = len((prof or {}).get('codex', {}).get(k, []) or [])
        tot = _codex_total(k, CX)
        on = (i == ci)
        w = a.font(10).size('%s %d/%d' % (label, cnt, tot))[0] + 16
        U.panel(surf, (x, 60, w, 17),
                (60, 48, 84, 235) if on else (28, 25, 36, 190),
                (200, 170, 240) if on else (58, 52, 74), 4, 1)
        U.text_shadow(a.font(10), surf, '%s %d/%d' % (label, cnt, tot),
                      (255, 240, 190) if on else (150, 146, 172),
                      x + w // 2, 63, anchor='midtop')
        x += w + 5

    items = _codex_items(cat, CX)
    # 左列条目
    lx, lw = 16, 250
    ly = 84
    # 行高 15。底部占用：页码在 VIEW_H-46（高 12），提示在 VIEW_H-18。
    # 列表必须止步于 VIEW_H-52，否则会和页码叠在一起 —— 这就是
    # 原来 "1 / 2" 糊在最后一行上的原因。
    per = max(1, (S.VIEW_H - 52 - ly) // 15)
    page = int(getattr(game, 'codex_page', 0))
    maxpage = max(0, (len(items) - 1) // per) if items else 0
    page = max(0, min(page, maxpage))
    start = page * per
    sel = int(getattr(game, 'codex_index', 0))
    sel = max(0, min(sel, max(0, len(items) - 1)))
    for j in range(per):
        idx = start + j
        if idx >= len(items):
            break
        key, name, sub, _ = items[idx]
        got = key in seen
        on = (idx == sel)
        if on:
            U.panel(surf, (lx, ly - 1, lw, 14), (60, 50, 84, 230),
                    (190, 160, 240), 3, 1)
        col = (230, 224, 200) if got else (110, 106, 128)
        nm = name if got else '？？？'
        surf.blit(a.font(11).render(_fit_text(a.font(11), nm, 150), True, col),
                  (lx + 4, ly))
        if got:
            surf.blit(a.font(9).render(_fit_text(a.font(9), sub, 84), True,
                                       (150, 146, 172)), (lx + lw - 88, ly + 2))
        ly += 15
    # 页码：挪进面板内部（原来是 VIEW_H-40，正好压在面板下边缘上）
    U.text_shadow(a.font(10), surf, '%d / %d' % (page + 1, maxpage + 1),
                  (140, 136, 160), lx, S.VIEW_H - 46)

    # 右侧详情
    rx = lx + lw + 12
    rw = S.VIEW_W - 16 - rx
    ry = 84
    if 0 <= sel < len(items):
        key, name, sub, _ = items[sel]
        got = key in seen
        if not got:
            U.text_shadow(a.font(15), surf, '？？？', (120, 116, 140), rx, ry)
            U.text_shadow(a.font(11), surf, '尚未发现',
                          (150, 146, 172), rx, ry + 22)
            U.text_shadow(a.font(10), surf,
                          _fit_text(a.font(10),
                                    '在关卡里遇到它，就会自动收录。', rw),
                          (130, 126, 150), rx, ry + 40)
        else:
            U.text_shadow(a.font(16), surf, name, (255, 236, 170), rx, ry)
            if cat == 'weapon':
                surf.blit(a.scaled(W.sprite_key(key), 44, 44),
                          (rx + rw - 48, ry + 2))
            elif cat == 'enemy':
                surf.blit(a.scaled('enemy_' + key, 44, 44),
                          (rx + rw - 48, ry + 2))
            yy = ry + 22
            if sub:
                U.text_shadow(a.font(10), surf, sub, (170, 176, 200), rx, yy)
                yy += 16
            desc = _codex_desc(cat, key, CX)
            f10 = a.font(11)
            # 简易换行
            line = ''
            for ch in desc:
                if f10.size(line + ch)[0] > rw or ch == '\n':
                    surf.blit(f10.render(line, True, (206, 210, 228)), (rx, yy))
                    yy += 16
                    line = '' if ch == '\n' else ch
                else:
                    line += ch
            if line:
                surf.blit(f10.render(line, True, (206, 210, 228)), (rx, yy))


def _codex_total(cat, CX):
    return {
        'enemy': len(CX.ENEMY_CODEX),
        'weapon': len(getattr(CX, 'WEAPON_CODEX', {})),
        'material': len(getattr(CX, 'MATERIAL_CODEX', {})),
        'collect': len(CX.COLLECTS),
    }.get(cat, 0)


def _codex_items(cat, CX):
    """-> [(key, name, sub, got_bool)]（不含 got 判定，由调用方填）。"""
    try:
        from . import gamedata as GD
    except Exception:
        GD = None
    out = []
    if cat == 'enemy':
        for k in CX.ENEMY_ORDER:
            v = CX.ENEMY_CODEX[k]
            out.append([k, v[0], v[1], False])
    elif cat == 'collect':
        for k in CX.COLLECT_ORDER:
            v = CX.COLLECTS[k]
            out.append([k, v[0], '精品' if v[1] == 'superb' else '普通', False])
    elif cat == 'weapon':
        table = getattr(CX, 'WEAPON_CODEX', None) or {}
        for k, v in table.items():
            out.append([k, v[0] if isinstance(v, (list, tuple)) else str(v),
                        '武器', False])
    elif cat == 'material':
        table = getattr(CX, 'MATERIAL_CODEX', None) or {}
        for k, v in table.items():
            out.append([k, v[0] if isinstance(v, (list, tuple)) else str(v),
                        '材料', False])
    return out


def _codex_desc(cat, key, CX):
    if cat == 'enemy':
        v = CX.ENEMY_CODEX.get(key)
        if not v:
            return ''
        st = CX.enemy_stats(key)
        line = '基础生命 %s · 移速 %s · 接触伤害 %s\n' % (
            st.get('hp', '?'), st.get('speed', '?'), st.get('contact', '?'))
        return line + '生命随关卡提高。' + v[3]
    if cat == 'collect':
        v = CX.COLLECTS.get(key)
        return v[2] if v else ''
    if cat == 'weapon':
        v = (getattr(CX, 'WEAPON_CODEX', {}) or {}).get(key)
        if not v:
            return ''
        spec = W.get(key)
        line = ('近战 · 范围 %.0f · 扇角 %.0f°' % (spec.reach, spec.arc)
                if spec.melee else '远攻 · 弹丸 %d · 弹速 %.0f' %
                (spec.count, spec.speed))
        return ('基础伤害 %.0f · 间隔 %.2f秒\n%s\n%s'
                % (spec.dmg, spec.cd, line, v[-1]))
    if cat == 'material':
        v = (getattr(CX, 'MATERIAL_CODEX', {}) or {}).get(key)
        return v[-1] if v else ''
    return ''


def _lobby_tab_showcase(surf, game):
    """分页 3：收集品展示台。6 个格子，摆放已获得的工艺品。"""
    from . import codex as CX
    a = game.assets
    prof = game.profile
    sc = list((prof or {}).get('showcase', [None] * 6))
    while len(sc) < 6:
        sc.append(None)
    sel = int(getattr(game, 'showcase_index', 0)) % 6

    U.text_shadow(a.font(12), surf, '收集品展示台',
                  (255, 236, 170), S.VIEW_W // 2, 60, anchor='midtop')
    # 3 x 2 网格：从 y=84 起，每格 96 高 + 12 间距 = 2 行共 204 -> 到 y=288
    # 底部 288..(VIEW_H-46)=314 留给描述行，不再和格子重叠
    gx, gy = 60, 84
    cw, ch = 168, 96
    for i in range(6):
        col = i % 3
        row = i // 3
        x = gx + col * (cw + 12)
        y = gy + row * (ch + 12)
        on = (i == sel)
        got = sc[i] is not None
        U.panel(surf, (x, y, cw, ch),
                (48, 40, 60, 235) if got else (26, 23, 32, 200),
                (230, 200, 130) if on else (
                    (120, 110, 150) if got else (56, 50, 70)),
                5, 2 if on else 1)
        # 格子编号
        surf.blit(a.font(9).render('#%d' % (i + 1), True, (140, 136, 160)),
                  (x + 6, y + 5))
        if got:
            v = CX.COLLECTS.get(sc[i])
            name = v[0] if v else sc[i]
            tier = v[1] if v else 'common'
            tcol = (255, 216, 120) if tier == 'superb' else (170, 200, 230)
            icon = a.scaled('collect_' + sc[i], 42, 42)
            surf.blit(icon, (x + (cw - 42) // 2, y + 16))
            surf.blit(a.font(12).render(_fit_text(a.font(12), name, cw - 16),
                                        True, (255, 240, 190)),
                      (x + cw // 2 - a.font(12).size(
                          _fit_text(a.font(12), name, cw - 16))[0] // 2, y + 62))
            tag = '精品' if tier == 'superb' else '普通'
            surf.blit(a.font(9).render(tag, True, tcol),
                      (x + cw // 2 - a.font(9).size(tag)[0] // 2, y + 80))
        else:
            U.text_shadow(a.font(11), surf, '空位', (110, 106, 128),
                          x + cw // 2, y + ch // 2 - 8, anchor='midtop')

    # 底部：当前格子详情
    if sc[sel] is not None:
        v = CX.COLLECTS.get(sc[sel])
        desc = v[2] if v else ''
        U.text_shadow(a.font(10), surf,
                      _fit_text(a.font(10), desc, S.VIEW_W - 60),
                      (196, 200, 220), S.VIEW_W // 2, S.VIEW_H - 46,
                      anchor='midtop')
    else:
        U.text_shadow(a.font(10), surf, '在关卡里搜刮，凑齐属于你的收藏。',
                      (140, 136, 166), S.VIEW_W // 2, S.VIEW_H - 46,
                      anchor='midtop')


def _lobby_mark(prof, key, PR, C):
    """卡右侧的状态标记：(文字, 颜色)。"""
    progress = PR.scene_prog(prof, key) if prof else 0
    recorded = PR.is_scene_cleared(prof, key) if prof else False
    if key == C.BONUS:
        if not prof or not prof.get('bonus_unlocked'):
            return ('未购', (226, 160, 120))
        if progress >= C.STAGES_PER_SCENE:
            return ('√ 通关', (150, 240, 190))
        if recorded:
            return ('再战', (255, 226, 150))
        return ('可进入', (255, 226, 150))
    if key in C.DUNGEONS:
        unlocked = bool(prof and key in prof.get('unlocked_dungeons', []))
        if not unlocked:
            return ('未解锁', (226, 140, 120))
        if progress >= C.STAGES_PER_SCENE:
            return ('√ 通关', (150, 240, 190))
        if recorded:
            return ('再战', (200, 220, 150))
        return ('可进入', (200, 220, 150))
    # 主线
    if progress >= C.STAGES_PER_SCENE:
        return ('√ 通关', (150, 240, 190))
    if recorded:
        return ('再战', (255, 226, 150))
    return ('主线', (150, 200, 230))


def _lobby_detail(surf, game, key, x, y, w, expanded, PR, C):
    """右侧详情面板：过场摘要 + 污染 + （副本）条件与机制卡。"""
    a = game.assets
    prof = game.profile
    info = C.scene_info(key)
    is_dun = key in C.DUNGEONS
    is_bonus = (key == C.BONUS)

    # 标题
    U.text_shadow(a.font(16), surf, info['name'], (255, 236, 170), x, y - 2)
    U.text_shadow(a.font(10), surf, info.get('sub', ''), (140, 136, 166),
                  x, y + 17)
    yy = y + 34

    # 处境描述（进场台词，取前两行）
    f10 = a.font(10)
    for line in info.get('enter', [])[:2]:
        surf.blit(f10.render(_fit_text(f10, line, w), True, (170, 176, 200)),
                  (x, yy))
        yy += 13

    # ---- 污染警告
    try:
        w1 = PR.pollution_warning(key, 0)
    except Exception:
        w1 = None
    if w1:
        head, det = (w1 if isinstance(w1, (tuple, list)) and len(w1) == 2
                     else (str(w1), ''))
        warn = _fit_text(f10, ('%s  ·  %s' % (head, det)) if det else head,
                         w + 12)
        U.panel(surf, (x, yy, w + 12, 15), (46, 30, 34, 190),
                (226, 130, 120), 3, 1)
        surf.blit(f10.render(warn, True, (240, 170, 160)), (x + 5, yy + 3))
        yy += 20

    # ---- 副本：条件清单
    if is_dun and prof:
        items, ok, ctext, hint = PR.dungeon_progress(prof, key)
        U.text_shadow(a.font(11), surf, '解锁条件', (200, 220, 150), x, yy)
        yy += 15
        surf.blit(f10.render(_fit_text(f10, ctext, w), True, (200, 196, 214)),
                  (x + 2, yy))
        yy += 13
        for lab, cur, tgt, done in items:
            col = (150, 240, 190) if done else (226, 150, 140)
            surf.blit(f10.render('√' if done else '·', True, col), (x + 2, yy))
            surf.blit(f10.render(_fit_text(f10, '%s  %s / %s' % (lab, cur, tgt),
                                           w - 16), True, col), (x + 14, yy))
            yy += 13
        if expanded and not ok and hint:
            surf.blit(f10.render(_fit_text(f10, '提示：' + hint, w),
                                 True, (220, 200, 150)), (x + 2, yy))
            yy += 13
        if expanded:
            surf.blit(f10.render('— 场景机制 —', True, (170, 160, 200)),
                      (x, yy))
            yy += 13
            used = draw_dungeon_bind(surf, game, key, x, yy, w + 12,
                                     max_h=max(0, S.VIEW_H - 30 - yy))
            yy += used
        else:
            surf.blit(f10.render('（按 E 查看场景机制卡）', True, (140, 136, 166)),
                      (x + 2, yy))
            yy += 13

    # ---- 奖励副本：报价
    elif is_bonus and prof:
        price = PR.bonus_price(prof)
        unlocked = bool(prof.get('bonus_unlocked'))
        coins = int(prof.get('coins', 0))
        if unlocked:
            U.panel(surf, (x, yy, w + 12, 18), (28, 40, 32, 200),
                    (150, 240, 190), 3, 1)
            surf.blit(a.font(11).render('已购买 · 可自由进入', True,
                                        (150, 240, 190)), (x + 6, yy + 3))
        else:
            av = False
            try:
                av = PR.bonus_available(prof)
            except Exception:
                pass
            mc, md = PR.bonus_missing(prof)
            col = (255, 216, 120) if (mc <= 0 and md <= 0) else (226, 150, 140)
            U.panel(surf, (x, yy, w + 12, 18), (42, 36, 26, 200), col, 3, 1)
            surf.blit(a.font(11).render('%d 金币' % price, True, col),
                      (x + 6, yy + 3))
            if not av:
                txt = '需先通关「%s」' % C.scene_label(C.MAIN[-1])
            elif mc > 0 or md > 0:
                txt = '还差 %d 金币' % mc + (' %d 钻石' % md if md else '')
            else:
                txt = '资金充足，可购买'
            surf.blit(f10.render(_fit_text(f10, txt, w), True, col),
                      (x + 6, yy + 22))
            yy += 30

    # ---- 已通关标记
    if prof and PR.is_scene_cleared(prof, key):
        U.text_shadow(a.font(10), surf, '√ 已通关该场景', (150, 240, 190),
                      x, yy + 2)


# ================================================================ 过场
# 需求 1：剧情叙事（污染入侵 -> 生存）。过场用"日志残片"式的排版：
# 左侧一条竖线 + 逐行淡入的文本，底部提示按键继续。
STORY_PAGE_MAX = 3      # 每页最多几行


def draw_talent(surf, game):
    """天赋三选一（1.1 需求 2）。state == 'talent' 时调用。

    三张卡片横排：名称 + 描述 + 品色边框，选中卡放大并高亮。
    """
    from . import codex as CX
    a = game.assets
    dim(surf, 205, (6, 6, 12))
    U.text_shadow(a.font(24), surf, '天 赋 觉 醒', (255, 236, 170),
                  S.VIEW_W // 2, 26, anchor='midtop')
    U.text_shadow(a.font(11), surf, '在污染里活下来的东西，会慢慢改变你。',
                  (170, 176, 200), S.VIEW_W // 2, 58, anchor='midtop')

    picks = game.pending_talents or []
    # [!] 防御：state=='talent' 但候选表是空的（异常退出后残留状态、
    #    或测试直接切 state）时，len(picks)==0，下面 range(n) 会拿 picks[0] 越界。
    #    这里直接兜底成空列表渲染一个"占位卡"，绝不抛异常。
    if not picks:
        U.text_shadow(a.font(14), surf, '天赋加载中…', (220, 216, 240),
                      S.VIEW_W // 2, S.VIEW_H // 2 - 10, anchor='midtop')
        U.text_shadow(a.font(11), surf, '按 Enter 继续',
                      (150, 146, 172), S.VIEW_W // 2, S.VIEW_H - 26,
                      anchor='midtop')
        return
    n = len(picks)
    sel = int(getattr(game, 'talent_pick', 0)) % n
    cw, ch = 132, 154
    gap = 14
    total = n * cw + (n - 1) * gap
    x0 = S.VIEW_W // 2 - total // 2
    cy = 96
    for i in range(n):
        on = (i == sel)
        x = x0 + i * (cw + gap)
        y = cy + (0 if on else 6)
        h = ch - (0 if on else 12)
        spec = CX.TALENTS.get(picks[i], {})
        col = spec.get('color', (200, 200, 220))
        U.panel(surf, (x, y, cw, h),
                (40, 34, 52, 242) if on else (24, 21, 30, 210),
                col if on else (58, 52, 74), 6, 3 if on else 1)
        if on:
            U.panel(surf, (x, y, cw, 4), col, col, 0, 0)
        # 图标：一颗菱形
        cx2, cy2 = x + cw // 2, y + 44
        pygame.draw.polygon(surf, col, [
            (cx2, cy2 - 17), (cx2 + 15, cy2), (cx2, cy2 + 17),
            (cx2 - 15, cy2)])
        pygame.draw.polygon(surf, (26, 22, 34), [
            (cx2, cy2 - 17), (cx2 + 15, cy2), (cx2, cy2 + 17),
            (cx2 - 15, cy2)], 2)
        nm = spec.get('name', picks[i])
        U.text_shadow(a.font(15), surf, nm, (255, 240, 190) if on else (216, 212, 234),
                      x + cw // 2, y + 66, anchor='midtop')
        # 描述换行
        desc = spec.get('desc', '')
        f10 = a.font(10)
        line = ''
        yy = y + 88
        for ch2 in desc:
            if f10.size(line + ch2)[0] > cw - 18:
                surf.blit(f10.render(line, True, (200, 204, 224)),
                          (x + 9, yy))
                yy += 14
                line = ch2
            else:
                line += ch2
        if line:
            surf.blit(f10.render(line, True, (200, 204, 224)), (x + 9, yy))
        # 已选次数
        cnt = list(game.talents_owned).count(picks[i])
        if cnt:
            tag = '已叠加 ×%d' % cnt
            surf.blit(a.font(9).render(tag, True, col),
                      (x + cw // 2 - a.font(9).size(tag)[0] // 2, y + h - 18))

    U.text_shadow(a.font(11), surf, '←→ 选择    Enter 确认',
                  (150, 146, 172), S.VIEW_W // 2, S.VIEW_H - 22, anchor='midtop')


def draw_story(surf, game):
    """过场画面。game.state == 'story' 时调用。"""
    a = game.assets
    tint = getattr(game, 'story_tint', (140, 140, 140))
    # 底色：场景色调压暗，避免纯黑导致"像崩溃"
    base = (max(6, tint[0] // 8), max(6, tint[1] // 8), max(8, tint[2] // 8))
    surf.fill(base)
    o = pygame.Surface((S.VIEW_W, S.VIEW_H), pygame.SRCALPHA)
    o.fill((base[0], base[1], base[2], 120))
    surf.blit(o, (0, 0))

    t = game.story_t
    # 顶部标题 + 进度条式的色带
    head = getattr(game, 'story_title', '')
    U.text_shadow(a.font(15), surf, head, (255, 236, 170), 30, 26)
    pygame.draw.line(surf, tint, (30, 48), (S.VIEW_W - 30, 48), 2)

    # 台词逐行淡入
    lines = game.story_lines
    page = int(getattr(game, 'story_page', 0))
    y = 74
    for i, line in enumerate(lines):
        appear = max(0.0, min(1.0, (t - i * 0.34) / 0.30))
        if appear <= 0.01:
            continue
        col = (200, 204, 224)
        if i == page:
            col = (245, 240, 214)      # 当前行高亮
        # 用 alpha 做淡入
        img = a.font(14).render(line, True, col)
        if appear < 1.0:
            img = img.copy()
            img.set_alpha(int(255 * appear))
        # 左侧短竖线（当前行）
        if i == page:
            pygame.draw.rect(surf, tint, (18, y - 2, 3, 20), border_radius=2)
        surf.blit(img, (30, y))
        y += 30

    # 页码 + 底部提示
    n = max(1, len(lines))
    U.text_shadow(a.font(10), surf, '%d / %d' % (min(page + 1, n), n),
                  (150, 146, 172), S.VIEW_W - 30, 30, anchor='topright')
    if t > 0.6:
        hint = ('按任意键继续' if page + 1 < n else
                ('按任意键前往下一场景' if game.pending_after and
                 game.pending_after[0] == 'scene_clear' else
                 '按任意键出发'))
        pulse = 150 + int(70 * (0.5 + 0.5 * math.sin(t * 4)))
        U.text_shadow(a.font(11), surf, hint, (pulse, pulse - 20, 140),
                      S.VIEW_W // 2, S.VIEW_H - 30, anchor='midtop')
    # 跳过提示
    U.text_shadow(a.font(10), surf, 'ESC 跳过', (120, 116, 140),
                  S.VIEW_W - 30, S.VIEW_H - 32, anchor='topright')
