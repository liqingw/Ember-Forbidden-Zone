"""Eight character specific active skills. X activates; cooldown is per run."""
import math

SKILLS = {
    'scout': ('地形脉冲', 12, (104, 222, 245), 105),
    'engineer': ('过载电圈', 15, (255, 185, 94), 112),
    'ranger': ('猎手齐射', 13, (155, 245, 132), 190),
    'medic': ('紧急救护', 18, (255, 132, 172), 92),
    'ghost': ('虚影闪避', 16, (188, 143, 255), 80),
    'prime': ('协议震荡', 19, (255, 226, 132), 145),
    'archivist': ('索引锁定', 14, (126, 214, 255), 245),
    'seedkeeper': ('生命花环', 17, (163, 235, 125), 110),
}
DETAILS = {
    'scout': '回复48能量，并释放双层侦查脉冲',
    'engineer': '回复35能量，电圈击伤近处怪物',
    'ranger': '向瞄准方向挥出远距离扇形箭雨',
    'medic': '回复6生命，短暂免疫伤害',
    'ghost': '获得2.5秒无敌并重置冲刺',
    'prime': '回复20能量，释放强力范围震荡',
    'archivist': '回复30能量，锁定最近目标攻击',
    'seedkeeper': '回复4生命，花环击伤近处怪物',
}


def activate(game):
    key = getattr(game, 'char_key', 'scout')
    name, cd, color, radius = SKILLS.get(key, SKILLS['scout'])
    if game.state != 'playing' or getattr(game, 'char_skill_cd', 0) > 0:
        return False
    pl = game.player
    game.char_skill_cd = float(cd)
    game.fx.ring(pl.x, pl.y, 5, radius, .4, color, 3)
    game.fx.burst(pl.x, pl.y, color, 20, 155, .48, 4)
    game.fx.text(pl.x, pl.y - 35, name, color, game.assets.font(12), 1.0)
    game.audio.play('ui_big')
    if key == 'scout':
        game.fx.ring(pl.x, pl.y, 12, radius * .7, .28, color, 1)
    elif key == 'engineer':
        game.fx.burst(pl.x, pl.y, color, 26, 210, .27, 2, shape='square')
    elif key == 'ranger':
        game.fx.arc_if_any(pl.x, pl.y, pl.aim, radius * .72, 48, color)
    elif key == 'medic':
        game.fx.burst(pl.x, pl.y, color, 18, 75, .8, 5, shape='circle')
    elif key == 'ghost':
        game.fx.smoke(pl.x, pl.y, 20, color)
    elif key == 'prime':
        game.fx.ring(pl.x, pl.y, 20, radius * 1.2, .5, color, 5)
    elif key == 'archivist':
        game.fx.burst(pl.x, pl.y, color, 12, 50, .65, 2, shape='square')
    elif key == 'seedkeeper':
        game.fx.burst(pl.x, pl.y, color, 26, 100, .75, 3, shape='circle')

    if key == 'scout':
        pl.energy = min(pl.max_energy, pl.energy + 48)
    elif key == 'medic':
        pl.heal(6)
        pl.iframes = max(pl.iframes, 1.4)
    elif key == 'ghost':
        pl.iframes = max(pl.iframes, 2.5)
        pl.dash_cd = 0
    elif key == 'seedkeeper':
        pl.heal(4)
    elif key == 'engineer':
        pl.energy = min(pl.max_energy, pl.energy + 35)
    elif key == 'prime':
        pl.energy = min(pl.max_energy, pl.energy + 20)
    elif key == 'archivist':
        pl.energy = min(pl.max_energy, pl.energy + 30)

    enemies = [e for e in getattr(game, 'enemies', ()) if e.alive]
    skill_mul = 1.0 + float(pl.dmg_bonus(game))
    if key in ('engineer', 'prime', 'seedkeeper'):
        base_dmg = {'engineer': 17, 'prime': 32, 'seedkeeper': 11}[key]
        damage = round(base_dmg * skill_mul, 2)
        for enemy in enemies:
            if math.hypot(enemy.x - pl.x, enemy.y - pl.y) <= radius:
                enemy.take_damage(damage, game, pl.x, pl.y)
                game.fx.burst(enemy.x, enemy.y, color, 8, 100, .3, 3)
    elif key == 'ranger':
        damage = round(27 * skill_mul, 2)
        for enemy in enemies:
            dx, dy = enemy.x - pl.x, enemy.y - pl.y
            if math.hypot(dx, dy) <= radius and abs((math.atan2(dy, dx) - pl.aim + math.pi) % math.tau - math.pi) < .42:
                enemy.take_damage(damage, game, pl.x, pl.y)
                game.fx.burst(enemy.x, enemy.y, color, 8, 100, .3, 3)
    elif key == 'archivist' and enemies:
        target = min(enemies, key=lambda e: math.hypot(e.x - pl.x, e.y - pl.y))
        if math.hypot(target.x - pl.x, target.y - pl.y) <= radius:
            target.take_damage(round(24 * skill_mul, 2), game, pl.x, pl.y)
            game.fx.ring(target.x, target.y, 4, 30, .35, color, 2)
    return True
