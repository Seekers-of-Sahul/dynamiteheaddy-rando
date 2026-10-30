from typing import NamedTuple

from BaseClasses import Item, ItemClassification

from .data import BASE_ID, GAME, STAGES


class HeaddyItem(Item):
    game = GAME


class ItemData(NamedTuple):
    code: int
    classification: ItemClassification


def unlock_name(stage: str) -> str:
    return f"{stage} Unlock"


DIGITS = [f"Secret Code Digit {i}" for i in range(1, 5)]
FILLER = {
    "Extra Life": 3,
    "Continue": 1,
    "Health Refill": 3,
}
TRAPS = {                      # name: value for the hub patch's trap byte ($FFFFE0)
    "Mean Bean Trap": 1,       # lose 16 health (never below 2)
    "Head Trip Trap": 2,       # Head Trip goes on for its usual time
}

item_table: dict[str, ItemData] = {}
for bit, stage, _ in STAGES:
    item_table[unlock_name(stage)] = ItemData(BASE_ID + bit, ItemClassification.progression)
for i, name in enumerate(DIGITS):
    item_table[name] = ItemData(BASE_ID + 0x40 + i, ItemClassification.progression)
for i, name in enumerate(FILLER):
    item_table[name] = ItemData(BASE_ID + 0x80 + i, ItemClassification.filler)
for i, name in enumerate(TRAPS):
    item_table[name] = ItemData(BASE_ID + 0xC0 + i, ItemClassification.trap)

item_name_to_id = {name: data.code for name, data in item_table.items()}
item_name_groups = {
    "Unlocks": {unlock_name(s) for _, s, _ in STAGES},
    "Code Digits": set(DIGITS),
    "Traps": set(TRAPS),
}
