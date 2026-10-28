import hashlib
import json
import os
from typing import TYPE_CHECKING

import Utils
from settings import get_settings
from worlds.Files import APPatchExtension, APProcedurePatch

from .data import GAME, ROM_MARKER, ROM_MARKER_ADDR, ROM_NAME_ADDR

if TYPE_CHECKING:
    from . import HeaddyWorld

US_MD5 = "d11ec9b230e88403cd75ef186a884c97"   # Dynamite Headdy (USA, Europe)
JP_MD5 = "cdb36911439289d3453060f58682057c"   # Dynamite Headdy (Japan), only for the JP options


class HeaddyPatchExtension(APPatchExtension):
    game = GAME

    @staticmethod
    def headdy_build(caller: APProcedurePatch, rom: bytes, settings_file: str) -> bytes:
        """Run the randomizer and the hub patch (Archipelago mode) on the player's ROM."""
        from . import ap_hub_patch, headdy_rando
        cfg = json.loads(caller.get_file(settings_file).decode())
        r = cfg["randomizer"]
        jp = get_jp_rom_bytes() if r["jp_balance"] or r["jp_palettes"] else None
        out, _spoiler = headdy_rando.randomize(rom, r, jp)
        out = bytearray(out)
        ap_hub_patch.apply(out, cfg["unlock_mask"], ap=True)     # also fixes the checksum
        out[ROM_MARKER_ADDR:ROM_MARKER_ADDR + 16] = ROM_MARKER.ljust(16, b"\0")
        name = cfg["player_name"].encode("utf-8")[:63]
        out[ROM_NAME_ADDR:ROM_NAME_ADDR + 64] = name.ljust(64, b"\0")
        return bytes(out)


class HeaddyProcedurePatch(APProcedurePatch):
    hash = US_MD5
    game = GAME
    patch_file_ending = ".apheaddy"
    result_file_ending = ".md"
    procedure = [("headdy_build", ["settings.json"])]

    @classmethod
    def get_source_data(cls) -> bytes:
        return get_base_rom_bytes()


def get_base_rom_bytes() -> bytes:
    file_name = get_settings()["headdy_options"]["rom_file"]
    if not os.path.exists(file_name):
        file_name = Utils.user_path(file_name)
    with open(file_name, "rb") as f:
        data = f.read()
    if hashlib.md5(data).hexdigest() != US_MD5:
        raise Exception("That ROM is not Dynamite Headdy (USA, Europe). "
                        "Get the right version (MD5 %s)." % US_MD5)
    return data


def get_jp_rom_bytes() -> bytes:
    """The Japanese ROM, for the JP options. Asks for it (and keeps a copy) if it isn't set up."""
    file_name = get_settings()["headdy_options"]["jp_rom_file"]
    path = file_name if os.path.exists(file_name) else Utils.user_path(file_name)
    if not os.path.exists(path):
        picked = Utils.open_filename("Choose the Dynamite Headdy (Japan) ROM (needed for the JP options)",
                                     (("Mega Drive ROM", (".md", ".bin", ".gen")),))
        if not picked:
            raise Exception("This seed uses JP balance or JP palettes, which need the Dynamite Headdy "
                            "(Japan) ROM. Set headdy_options.jp_rom_file in host.yaml.")
        with open(picked, "rb") as f:
            data = f.read()
        if hashlib.md5(data).hexdigest() == JP_MD5:
            with open(Utils.user_path("Dynamite Headdy (Japan).md"), "wb") as f:
                f.write(data)        # found automatically next time
    else:
        with open(path, "rb") as f:
            data = f.read()
    if hashlib.md5(data).hexdigest() != JP_MD5:
        raise Exception("That ROM is not Dynamite Headdy (Japan) (MD5 %s)." % JP_MD5)
    return data


def write_patch(world: "HeaddyWorld", output_directory: str) -> None:
    o = world.options
    randomizer = {
        "seed": world.random.randrange(1 << 31),
        "headcases": ["off", "safe", "chaos"][o.headcases.value],
        "bonus_logic": True,          # the AP logic assumes every bonus point is reachable
        "headtrip": bool(o.head_trip.value),
        "boss_bomb": bool(o.boss_bomb.value),
        "flying_heads": bool(o.flying_heads.value),
        "jp_balance": bool(o.jp_balance.value),
        "jp_palettes": bool(o.jp_palettes.value),
        "palettes": ["off", "safe", "hue", "chaos"][o.palettes.value],
        "palette_sprites": bool(o.palette_sprites.value),
        "enemy_damage": ["off", "random", "half", "double"][o.enemy_damage.value],
    }
    cfg = {
        "randomizer": randomizer,
        "unlock_mask": 1 << world.starting_stage_bit,
        "player_name": world.player_name,
    }
    patch = HeaddyProcedurePatch(player=world.player, player_name=world.player_name)
    patch.write_file("settings.json", json.dumps(cfg).encode())
    patch.write(os.path.join(output_directory,
                             f"{world.multiworld.get_out_file_name_base(world.player)}{patch.patch_file_ending}"))
