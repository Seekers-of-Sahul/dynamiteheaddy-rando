"""Dynamite Headdy (Mega Drive / Genesis) for Archipelago."""
from typing import Any, ClassVar

import settings
from BaseClasses import ItemClassification, Region, Tutorial
from worlds.AutoWorld import WebWorld, World

from .client import HeaddyClient  # noqa: F401  (registers the BizHawk client)
from .data import BASKETBALL_STAGES, BONUS_POINTS, GAME, STAGES
from .items import DIGITS, FILLER, HeaddyItem, item_name_groups, item_name_to_id, item_table, unlock_name
from .locations import (BASKETBALL_WINS, SECRET_BOSS, HeaddyLocation, clear_name, location_name_groups,
                        location_name_to_id, location_table)
from .options import Goal, HeaddyOptions
from .rom import JP_MD5, US_MD5, write_patch


class HeaddySettings(settings.Group):
    class RomFile(settings.UserFilePath):
        """File name of the Dynamite Headdy (USA, Europe) ROM"""
        description = "Dynamite Headdy (USA, Europe) ROM File"
        copy_to = "Dynamite Headdy (USA, Europe).md"
        md5s = [US_MD5]

    class JPRomFile(settings.OptionalUserFilePath):
        """File name of the Dynamite Headdy (Japan) ROM. Only needed for the jp_balance and
        jp_palettes options; if it's missing you'll be asked for it when patching."""
        description = "Dynamite Headdy (Japan) ROM File"
        copy_to = "Dynamite Headdy (Japan).md"
        md5s = [JP_MD5]

    rom_file: RomFile = RomFile(RomFile.copy_to)
    jp_rom_file: JPRomFile = JPRomFile(JPRomFile.copy_to)


class HeaddyWeb(WebWorld):
    theme = "partyTime"
    tutorials = [Tutorial(
        "Multiworld Setup Guide",
        "How to play Dynamite Headdy with Archipelago using BizHawk.",
        "English", "setup_en.md", "setup/en", ["mariodiazdecerio"],
    )]


class HeaddyWorld(World):
    """
    Dynamite Headdy: a puppet with a detachable head fights his way through a theatre of stages,
    swapping heads from Headcases. Stages are unlocked by items from the multiworld, and every act
    clear, Secret Bonus Point and basketball win is a check.
    """
    game = GAME
    web = HeaddyWeb()
    settings: ClassVar[HeaddySettings]
    options_dataclass = HeaddyOptions
    options: HeaddyOptions
    item_name_to_id = item_name_to_id
    location_name_to_id = location_name_to_id
    item_name_groups = item_name_groups
    location_name_groups = location_name_groups

    starting_stage_bit: int = 1
    code: list[int]

    def generate_early(self) -> None:
        self.starting_stage_bit = self.options.starting_stage.value
        self.code = [self.random.randint(0, 9) for _ in range(4)]

    @property
    def starting_stage(self) -> str:
        return next(name for bit, name, _ in STAGES if bit == self.starting_stage_bit)

    # ------------------------------------------------------------------ regions and rules
    def create_regions(self) -> None:
        p = self.player
        menu = Region("Menu", p, self.multiworld)
        self.multiworld.regions.append(menu)
        regions = {}
        for _, stage, _ in STAGES:
            r = Region(stage, p, self.multiworld)
            regions[stage] = r
            self.multiworld.regions.append(r)
            menu.connect(r, f"To {stage}", lambda state, s=stage: state.has(unlock_name(s), p))
        for name, (code, region) in location_table.items():
            if region in regions:
                regions[region].locations.append(HeaddyLocation(p, name, code, regions[region]))

        # Basketball: win k needs k different basketball stages reachable.
        bball = Region("Basketball", p, self.multiworld)
        self.multiworld.regions.append(bball)
        menu.connect(bball, "To Basketball")
        for k, name in enumerate(BASKETBALL_WINS, 1):
            loc = HeaddyLocation(p, name, location_name_to_id[name], bball)
            loc.access_rule = (lambda state, k=k: sum(state.has(unlock_name(s), p)
                                                      for s in BASKETBALL_STAGES) >= k)
            bball.locations.append(loc)

        # The secret door comes after the credits: beat 9-3 with all four code digits.
        door = Region("Secret Door", p, self.multiworld)
        self.multiworld.regions.append(door)
        regions["9-3"].connect(door, "Credits",
                               lambda state: state.has_all(DIGITS, p))
        door.locations.append(HeaddyLocation(p, SECRET_BOSS, location_name_to_id[SECRET_BOSS], door))

        # Goal event
        goal = self.options.goal.value
        victory_region = door if goal == Goal.option_secret_boss else regions["9-3"]
        victory = HeaddyLocation(p, "Victory", None, victory_region)
        victory.place_locked_item(HeaddyItem("Victory", ItemClassification.progression, None, p))
        if goal == Goal.option_bonus_points:
            need = self.options.required_bonus_points.value
            acts = [act for _, act, _ in BONUS_POINTS]
            victory.access_rule = (lambda state: sum(state.has(unlock_name(a), p) for a in acts) >= need)
        victory_region.locations.append(victory)
        self.multiworld.completion_condition[p] = lambda state: state.has("Victory", p)

    # ------------------------------------------------------------------ items
    def create_item(self, name: str) -> HeaddyItem:
        data = item_table[name]
        return HeaddyItem(name, data.classification, data.code, self.player)

    def get_filler_item_name(self) -> str:
        return self.random.choices(list(FILLER), weights=list(FILLER.values()))[0]

    def create_items(self) -> None:
        start = unlock_name(self.starting_stage)
        self.multiworld.push_precollected(self.create_item(start))
        pool = [self.create_item(unlock_name(s)) for _, s, _ in STAGES if unlock_name(s) != start]
        pool += [self.create_item(d) for d in DIGITS]
        n_locations = len(location_table)
        while len(pool) < n_locations:
            pool.append(self.create_item(self.get_filler_item_name()))
        self.multiworld.itempool += pool

    # ------------------------------------------------------------------ output
    def generate_output(self, output_directory: str) -> None:
        write_patch(self, output_directory)

    def fill_slot_data(self) -> dict[str, Any]:
        return {
            "goal": self.options.goal.value,
            "required_bonus_points": self.options.required_bonus_points.value,
            "code": self.code,
            "starting_stage_bit": self.starting_stage_bit,
        }
