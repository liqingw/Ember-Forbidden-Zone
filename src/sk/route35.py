"""3.5 optional survey route. Selection reads the completed map and uses no RNG."""
from collections import deque

from . import settings as S

ROUTE = {'id': 'mine_survey_02', 'scene': 'd_mine', 'stage_idx': 1,
         'reward': {'crystal': 2}}
ORDER = ('N', 'S', 'W', 'E')


def choose_room(dungeon):
    if dungeon.scene_key != ROUTE['scene'] or dungeon.stage_idx != ROUTE['stage_idx']:
        return None
    rooms = dungeon.rooms
    start, goal = dungeon.start_key, dungeon.goal_key

    def walk(source, blocked=None, forbidden=None):
        queue = deque([source])
        parent = {source: None}
        while queue:
            key = queue.popleft()
            room = rooms[key]
            for direction in ORDER:
                if direction not in room.doors:
                    continue
                delta = S.DIR_VEC[direction]
                nxt = (key[0] + delta[0], key[1] + delta[1])
                if nxt in rooms and nxt != blocked and nxt != forbidden and nxt not in parent:
                    parent[nxt] = key
                    queue.append(nxt)
        return parent

    parent = walk(start)
    if goal not in parent:
        return None
    path = set()
    key = goal
    while key is not None:
        path.add(key)
        key = parent[key]
    branch = walk(start, forbidden=goal)
    candidates = []
    for key, room in rooms.items():
        if (room.kind != 'normal' or key in path or key not in branch or
                goal not in walk(start, blocked=key)):
            continue
        degree = sum(1 for direction in ORDER if direction in room.doors)
        distance = min(abs(key[0] - p[0]) + abs(key[1] - p[1]) for p in path)
        candidates.append((0 if degree == 1 else 1, distance, key[0], key[1], key))
    return min(candidates)[-1] if candidates else None


def next_door(dungeon, source, target):
    if source == target:
        return None
    queue = deque([(source, None)])
    seen = {source}
    while queue:
        key, first = queue.popleft()
        room = dungeon.rooms.get(key)
        if room is None:
            continue
        for direction in ORDER:
            if direction not in room.doors:
                continue
            dx, dy = S.DIR_VEC[direction]
            nxt = (key[0] + dx, key[1] + dy)
            if nxt == dungeon.goal_key or nxt in seen or nxt not in dungeon.rooms:
                continue
            if nxt == target:
                return first or direction
            seen.add(nxt)
            queue.append((nxt, first or direction))
    return None
