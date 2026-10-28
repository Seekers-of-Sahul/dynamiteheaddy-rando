"""BizHawk client for Dynamite Headdy (Genesis Plus GX core).

Every loop it reads the hub patch's variables ($FFFFE0-$FFFFFF), sends newly
checked locations, and writes what the multiworld has given the player:
  - stage unlocks -> the unlock mask (rebuilt from all items every time)
  - code digits   -> the game's digit cells and the hub's reset-proof backup
  - filler        -> applied once each, counted at $FFFFFC so a soft reset or
                     reconnect doesn't hand them out twice
"""
import logging
from typing import TYPE_CHECKING

from NetUtils import ClientStatus
from worlds._bizhawk import read, write
from worlds._bizhawk.client import BizHawkClient

from .data import (BONUS_POINTS, GAME, RAM_BB_STAGES, RAM_BONUS, RAM_CLEARED, RAM_CONTINUES, RAM_DIGITS_BACKUP,
                   RAM_GAME_DIGITS, RAM_HEALTH, RAM_HUB_BLOCK, RAM_HUBFLAG, RAM_ITEMS, RAM_LIVES, RAM_MAGIC, RAM_MODE,
                   RAM_UNLOCK, ROM_MARKER, ROM_MARKER_ADDR, ROM_NAME_ADDR, SECRET_BOSS_BIT, STAGES)

if TYPE_CHECKING:
    from worlds._bizhawk.context import BizHawkClientContext

logger = logging.getLogger("Client")

RAM = "68K RAM"
ROM = "MD CART"
MODE_PLAYING = 0x20


def _swap(b: bytes) -> bytes:
    """Swap each pair of bytes (for a byte-swapped memory domain)."""
    b = bytearray(b)
    b[0::2], b[1::2] = b[1::2], b[0::2]
    return bytes(b)


class HeaddyClient(BizHawkClient):
    game = GAME
    system = "GEN"
    patch_suffix = ".apheaddy"

    def __init__(self) -> None:
        super().__init__()
        self.rom_swapped = False
        self.ram_swapped: bool | None = None
        self.sent: set[int] = set()
        self.goal_sent = False
        self.last_note = ""
        self.notify_set = False

    # ------------------------------------------------------------------ helpers
    async def read_rom(self, ctx: "BizHawkClientContext", addr: int, size: int) -> bytes:
        data = (await read(ctx.bizhawk_ctx, [(addr, size, ROM)]))[0]
        return _swap(data) if self.rom_swapped else data

    async def read_ram(self, ctx: "BizHawkClientContext", reads: list[tuple[int, int]]) -> list[bytes]:
        """Reads (even address, even size) blocks from 68K RAM in big-endian order."""
        out = await read(ctx.bizhawk_ctx, [(a, n, RAM) for a, n in reads])
        return [_swap(b) if self.ram_swapped else b for b in out]

    def ram_write(self, addr: int, data: bytes) -> tuple[int, list[int], str]:
        """A write of `data` (even address, even length) in the domain's byte order."""
        return addr, list(_swap(data) if self.ram_swapped else data), RAM

    # ------------------------------------------------------------------ BizHawkClient
    async def validate_rom(self, ctx: "BizHawkClientContext") -> bool:
        try:
            marker = (await read(ctx.bizhawk_ctx, [(ROM_MARKER_ADDR, 16, ROM)]))[0]
        except Exception:
            return False
        if marker.startswith(ROM_MARKER):
            self.rom_swapped = False
        elif _swap(marker).startswith(ROM_MARKER):
            self.rom_swapped = True
        else:
            return False
        ctx.game = self.game
        ctx.items_handling = 0b111       # all items come from the server, including our own
        ctx.want_slot_data = True
        ctx.watcher_timeout = 0.25
        self.ram_swapped = None
        self.sent = set()
        self.goal_sent = False
        self.notify_set = False
        return True

    async def set_auth(self, ctx: "BizHawkClientContext") -> None:
        name = await self.read_rom(ctx, ROM_NAME_ADDR, 64)
        ctx.auth = name.split(b"\0")[0].decode("utf-8", "replace")

    def note(self, key: str, msg: str) -> None:
        """Log a status message once (until the status changes)."""
        if self.last_note != key:
            self.last_note = key
            logger.info("Dynamite Headdy: " + msg)

    async def game_watcher(self, ctx: "BizHawkClientContext") -> None:
        try:
            await self._watch(ctx)
        except Exception as e:      # report instead of failing silently
            import traceback
            self.note("error " + repr(e), "client error, please report:\n" + traceback.format_exc())

    async def _watch(self, ctx: "BizHawkClientContext") -> None:
        if ctx.server is None or ctx.server.socket.closed:
            self.note("noserver", "not connected to the server yet.")
            return
        if ctx.slot_data is None:
            self.note("noslot", "connected, waiting for slot data from the server.")
            return

        # The hub's block $FFE0-$FFFF, plus game state.
        hub, digits, misc = await self.read_ram(ctx, [(RAM_HUB_BLOCK, 0x20), (RAM_GAME_DIGITS, 8), (RAM_MODE, 2)])
        if self.ram_swapped is None:
            magic = hub[RAM_MAGIC - RAM_HUB_BLOCK:RAM_MAGIC - RAM_HUB_BLOCK + 2]
            if magic == b"AP":
                self.ram_swapped = False
            elif magic == b"PA":
                self.ram_swapped = True
                hub, digits, misc = [_swap(b) for b in (hub, digits, misc)]
            else:
                self.note("nohub " + magic.hex(), "waiting for the stage-select hub (press Start on the title "
                          "screen). Hub RAM reads %s." % hub.hex())
                return
        if hub[RAM_MAGIC - RAM_HUB_BLOCK:RAM_MAGIC - RAM_HUB_BLOCK + 2] != b"AP":
            self.note("nohub2", "hub not set up (console reset?); waiting for the stage select.")
            return
        self.note("ok", "reading the game (RAM byte order %s)." % ("swapped" if self.ram_swapped else "normal"))

        def u8(a: int) -> int:
            return hub[a - RAM_HUB_BLOCK]

        def u16(a: int) -> int:
            return int.from_bytes(hub[a - RAM_HUB_BLOCK:a - RAM_HUB_BLOCK + 2], "big")

        def u32(a: int) -> int:
            return int.from_bytes(hub[a - RAM_HUB_BLOCK:a - RAM_HUB_BLOCK + 4], "big")

        from .items import DIGITS, item_name_to_id, unlock_name
        id_to_name = {v: k for k, v in item_name_to_id.items()}
        from .locations import BASKETBALL_WINS, SECRET_BOSS, clear_name

        # ---------------------------------------------------------- locations
        cleared = u32(RAM_CLEARED)
        bonus = sum(((hub[RAM_BONUS - RAM_HUB_BLOCK + i] >> b) & 1) << (8 * i + b) for i in range(6) for b in range(8))
        wins = bin(u8(RAM_BB_STAGES)).count("1")
        ids = self.location_ids(ctx)
        found = set()
        for bit, stage, _ in STAGES:
            if cleared >> bit & 1:
                found.add(ids[clear_name(stage)])
        if cleared >> SECRET_BOSS_BIT & 1:
            found.add(ids[SECRET_BOSS])
        for name, _, bit in BONUS_POINTS:
            if bonus >> bit & 1:
                found.add(ids[name])
        for k, name in enumerate(BASKETBALL_WINS, 1):
            if wins >= k:
                found.add(ids[name])
        new = (found - self.sent) & set(ctx.server_locations)
        if new:
            await ctx.send_msgs([{"cmd": "LocationChecks", "locations": sorted(new)}])
            self.sent |= new
            logger.info("Dynamite Headdy: sent %d check(s)." % len(new))

        # ---------------------------------------------------------- restore after a power-off
        # The server knows every location already checked; put those bits back so the hub's
        # counters and the cleared marks come back after the console RAM is wiped.
        # Which basketball stages were won is kept in the server's data storage.
        writes = []
        done = set(ctx.checked_locations)
        want_cleared = cleared
        for bit, stage, _ in STAGES:
            if ids[clear_name(stage)] in done:
                want_cleared |= 1 << bit
        if ids[SECRET_BOSS] in done:
            want_cleared |= 1 << SECRET_BOSS_BIT
        if want_cleared != cleared:
            writes.append(self.ram_write(RAM_CLEARED, want_cleared.to_bytes(4, "big")))
        want_bonus = bonus
        for name, _, bit in BONUS_POINTS:
            if ids[name] in done:
                want_bonus |= 1 << bit
        if want_bonus != bonus:
            raw = bytes((want_bonus >> (8 * i)) & 0xFF for i in range(6))
            writes.append(self.ram_write(RAM_BONUS, raw))
        key = "headdy_bb_%d_%d" % (ctx.team, ctx.slot)
        if not self.notify_set:
            ctx.set_notify(key)
            self.notify_set = True
        stored = ctx.stored_data.get(key) or 0
        bb = u8(RAM_BB_STAGES)
        if bb & ~stored:
            await ctx.send_msgs([{"cmd": "Set", "key": key, "default": 0, "want_reply": True,
                                  "operations": [{"operation": "or", "value": bb}]}])
        if key in ctx.stored_data and (bb | stored) != bb:
            writes.append(self.ram_write(RAM_BB_STAGES, bytes([bb | stored, u8(RAM_BB_STAGES + 1)])))
        restored = bool(writes)

        # ---------------------------------------------------------- items
        names = [id_to_name.get(i.item, "") for i in ctx.items_received]
        mask = 1 << ctx.slot_data["starting_stage_bit"]
        for bit, stage, _ in STAGES:
            if unlock_name(stage) in names:
                mask |= 1 << bit
        if u32(RAM_UNLOCK) != mask:
            writes.append(self.ram_write(RAM_UNLOCK, mask.to_bytes(4, "big")))

        code = ctx.slot_data["code"]
        backup = u16(RAM_DIGITS_BACKUP)
        new_backup = backup
        game_digits = bytearray(digits)
        for i, d in enumerate(DIGITS):
            if d in names:
                shift = 12 - 4 * i
                new_backup = (new_backup & ~(0xF << shift)) | (code[i] << shift)
                game_digits[2 * i:2 * i + 2] = code[i].to_bytes(2, "big")
        if new_backup != backup:
            writes.append(self.ram_write(RAM_DIGITS_BACKUP, new_backup.to_bytes(2, "big")))
        if bytes(game_digits) != digits:
            writes.append(self.ram_write(RAM_GAME_DIGITS, bytes(game_digits)))

        # Consumables: only while playing a stage, once each.
        applied = u16(RAM_ITEMS)
        mode = int.from_bytes(misc, "big")
        if mode == MODE_PLAYING and applied < len(names):
            lives, conts, health = await self.read_ram(ctx, [(RAM_LIVES, 2), (RAM_CONTINUES, 2), (RAM_HEALTH, 2)])
            lives, conts, health = (int.from_bytes(x, "big") for x in (lives, conts, health))
            for name in names[applied:]:
                if name == "Extra Life":
                    lives = min(99, lives + 1)
                elif name == "Continue":
                    conts = min(9, conts + 1)
                elif name == "Health Refill":
                    health = 0x20
            writes += [self.ram_write(RAM_LIVES, lives.to_bytes(2, "big")),
                       self.ram_write(RAM_CONTINUES, conts.to_bytes(2, "big")),
                       self.ram_write(RAM_HEALTH, health.to_bytes(2, "big")),
                       self.ram_write(RAM_ITEMS, len(names).to_bytes(2, "big"))]
        if restored or new_backup != backup:
            # The stage select drew its "nn OF 39 SBPS" / code lines before we got here:
            # ask the hub to redraw them (REDRAW = 3: stage number, SBP line, code line).
            writes.append(self.ram_write(RAM_HUBFLAG, bytes([u8(RAM_HUBFLAG), 3])))
        if writes:
            await write(ctx.bizhawk_ctx, writes)

        # ---------------------------------------------------------- goal
        if not self.goal_sent and not ctx.finished_game:
            goal = ctx.slot_data["goal"]
            done = False
            if goal == 0:
                done = bool(cleared >> SECRET_BOSS_BIT & 1)
            elif goal == 1:
                done = bool(cleared >> 29 & 1)
            else:
                taken = sum(bonus >> bit & 1 for _, _, bit in BONUS_POINTS)
                done = bool(cleared >> 29 & 1) and taken >= ctx.slot_data["required_bonus_points"]
            if done:
                await ctx.send_msgs([{"cmd": "StatusUpdate", "status": ClientStatus.CLIENT_GOAL}])
                ctx.finished_game = True
                self.goal_sent = True

    @staticmethod
    def location_ids(ctx: "BizHawkClientContext") -> dict[str, int]:
        from .locations import location_name_to_id
        return location_name_to_id
