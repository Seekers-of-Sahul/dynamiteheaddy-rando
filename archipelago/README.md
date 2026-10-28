# Dynamite Headdy for Archipelago

Requires Archipelago 0.6.8 or newer and BizHawk 2.10 or newer (tested with 2.11.1).

## How it plays

- You start with one stage unlocked (1-1 by default). Every other stage is an item.
- **Checks:** each act clear, each of the 39 Secret Bonus Points, the 4 basketball wins and the secret boss.
- **Items:** stage unlocks, the 4 secret code digits, and filler (Extra Life, Continue, Health Refill).
- **Goal** (pick one): beat the secret boss behind the door after the credits, beat 9-3, or collect a number of Secret Bonus Points and beat 9-3.
- Basketball wins no longer give code digits; the digits come from the multiworld instead.
- After a hard reset or closing the emulator, the client restores your bonus points, act clears and basketball progress from the server.

All the randomizer options (Headcases, flying heads, palettes, enemy damage, JP balance) are available as YAML options.

## Installing

1. Get `headdy.apworld` from the [Releases](../../releases) page, or build it yourself (below).
2. Put it in the `custom_worlds` folder of your Archipelago install (or double-click it).
3. Fill in a YAML: `Headdy_simple.yaml` has the common options with comments; `Dynamite Headdy.yaml` has every option.

The full setup guide (patching, BizHawk, connecting) is in [`headdy/docs/setup_en.md`](headdy/docs/setup_en.md).

## Building the apworld

```
python build_apworld.py
```

It writes `headdy.apworld` here. The world uses `headdy_rando.py` and `ap_hub_patch.py` from `../randomizer`, which the script copies in.

If you run Archipelago from source, you can instead copy the `headdy` folder into `worlds/`, along with those two files.
