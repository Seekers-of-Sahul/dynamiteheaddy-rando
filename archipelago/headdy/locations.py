from BaseClasses import Location

from .data import BASE_ID, BONUS_POINTS, GAME, PICKUP_SPOTS, STAGES


class HeaddyLocation(Location):
    game = GAME


def clear_name(stage: str) -> str:
    return f"{stage} Clear"


def pickup_name(act: str, n: int) -> str:
    return f"{act} Pickup {n}"


BASKETBALL_WINS = [f"Basketball Win {i}" for i in range(1, 5)]
PICKUP_LOCATIONS = [pickup_name(act, n) for act, _, n, _ in PICKUP_SPOTS]
SECRET_BOSS = "Secret Boss"

# name -> (id, region)
location_table: dict[str, tuple[int, str]] = {}
for bit, stage, _ in STAGES:
    location_table[clear_name(stage)] = (BASE_ID + bit, stage)
for name, act, bit in BONUS_POINTS:
    location_table[name] = (BASE_ID + 0x100 + bit, act)
for i, name in enumerate(BASKETBALL_WINS):
    location_table[name] = (BASE_ID + 0x200 + i, "Basketball")
location_table[SECRET_BOSS] = (BASE_ID + 0x300, "Secret Door")
for i, (act, _, n, _) in enumerate(PICKUP_SPOTS):
    location_table[pickup_name(act, n)] = (BASE_ID + 0x400 + i, act)

location_name_to_id = {name: code for name, (code, _) in location_table.items()}
location_name_groups = {
    "Act Clears": {clear_name(s) for _, s, _ in STAGES},
    "Bonus Points": {name for name, _, _ in BONUS_POINTS},
    "Basketball": set(BASKETBALL_WINS),
    "Pickups": set(PICKUP_LOCATIONS),
}
