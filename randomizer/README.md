# Dynamite Headdy Randomizer

A randomizer and difficulty mod for **Dynamite Headdy (USA, Europe)** on the Mega Drive / Genesis.

It can:

- shuffle the heads inside Headcases, with logic so every stage stays beatable
- recolour every stage
- change enemy damage
- restore the easier Japanese balance

You need your own ROM. No ROM is included.

---

## What you need

- **Python 3.9 or newer.** On Windows, get it from [python.org](https://www.python.org/downloads/) and tick **"Add Python to PATH"** during setup. Nothing else needs installing.
- **The US/EU ROM**, `Dynamite Headdy (USA, Europe).md` or `.bin`. Its SHA-1 should be `e843decdff262791b1237f1545f5b17c56712d5f`. Another ROM may still work, but you'll get a warning.
- **Only for `--jp-balance` and `--jp-palettes`:** the **Japanese ROM**, `Dynamite Headdy (Japan)` (MD5 `cdb36911439289d3453060f58682057c`). The randomizer copies the JP code and data from it, so none of it is included here. Pass it with `--jp-rom`.

---

## Quick start (Windows cmd)

1. Put `headdy_rando.py` and your ROM in the same folder, for example `C:\headdy`.
2. Open **cmd** and go to that folder:
   ```
   cd C:\headdy
   ```
3. Run it:
   ```
   python headdy_rando.py "Dynamite Headdy (USA, Europe).md" rando.md
   ```

This makes two files:

- `rando.md`: the randomized ROM. Open it in any emulator (BizHawk, Genesis Plus GX, Kega Fusion…) or on a flash cart.
- `rando.md.spoiler.txt`: everything that changed, including the seed. Don't open it if you want surprises.

> If `python` isn't found, try `py` instead: `py headdy_rando.py ...`

---

## Choosing options

Add options after the two file names. Here's a full example:

```
python headdy_rando.py headdy.md out.md --seed 1234 --headcases chaos --palettes hue --jp-balance --jp-rom headdy_jp.md
```

To see every option in cmd, run:

```
python headdy_rando.py --help
```

### Seed

| Option | What it does |
| --- | --- |
| `--seed 1234` | Same seed + same options = same ROM, so you can race or share a seed. Leave it out for a random one, which is written at the top of the spoiler log. |

### Headcases

| Option | What it does |
| --- | --- |
| `--headcases safe` | **Default.** Every Headcase keeps at least one of its original heads. |
| `--headcases chaos` | Anything goes, but heads needed to finish a stage are still guaranteed. |
| `--headcases off` | Headcases stay vanilla. |
| `--no-bonus-logic` | Don't guarantee the heads needed for Secret Bonus Points. Some may become impossible. |
| `--no-headtrip` | Never put Head Trip (reversed controls) in a Headcase. |
| `--shuffle-3-2` | Also shuffle the switching Headcase in 3-2 (it changes contents during the stage). It's vanilla by default. |
| `--no-boss-bomb` | Don't guarantee Bomb Head at the act 7 boss. |
| `--flying-heads` | Allow Rocket, Air and Feather Head in normal Headcases (see below). |

The logic always guarantees:

- **2-2:** Spike or Pin in the 4th Headcase.
- **4-2:** Slammer in the 3rd Headcase.
- **8-1 / 8-2:** Spike or Pin.
- **8-3:** Spike at the miniboss.

Flying heads never count for these: they can't break Spike's wooden boards or fit through Pin's paths.

Bonus logic (on by default) adds:

- **Slammer:** for the bonus points in 4-2 and 9-1.
- **Spike:** at the 2-2 4th Headcase and in 8-1.

Liberty Head always stays in its sets, because it's how you reach the basketball minigames. The Headcase that gives you your first flying head in 6-1 is never changed.

**Flying heads (`--flying-heads`).** Without this option, flying heads never appear in normal stages. With it, they can show up in any shuffled Headcase, and you fly freely around the stage. They then work like the other heads:

- **A drops them**, back to normal Headdy.
- **They time out** after the same time as most heads.
- **They're cleared when you die or change stage.**

Flying heads are never placed in **4-1, 4-3, 5-1 or 8-2**, where they break the stage (the camera takes over, or the stage stops working). 8-1 shares its Headcase set with 8-2, so 8-1 doesn't get them either.

6-1 to 6-4 work exactly as before: 6-1's flying heads can't be dropped or time out, and you keep flying through deaths and from one 6-x stage to the next.

In act 7 the camera moves on its own when you reach the boss with a flying head. You get control back once the head runs out.

Known issues:

- **Garbled shots.** Outside 6-1 the shots look garbled, because their graphics are only loaded in 6-1. They still work.
- **Bino Head.** Feather Head has the game's usual 1-in-8 chance of turning into Bino Head when you pick it up, which gives a Secret Bonus Point.

### Colours

| Option | What it does |
| --- | --- |
| `--palettes safe` | **Recommended.** Each act gets a gentle recolour: a small hue shift (up to 45°) or a warm, cool, dusk or muted mood. Every colour keeps its brightness, so stages read exactly like the original. |
| `--palettes hue` | Each act gets its colours rotated. Brightness is kept, so stages stay readable. |
| `--palettes chaos` | Colour channels are swapped and inverted. Often garish, on purpose. |
| `--palette-sprites` | Also recolour Headdy, enemies and Headcases. Off by default so you can still recognise them. |
| `--jp-palettes` | Restore the Japanese colours of the 8 palettes the US version changed. Needs `--jp-rom`. |

Menus and title cards always keep their normal colours.

### Enemies

| Option | What it does |
| --- | --- |
| `--enemy-damage random` | Each enemy type hits for between half and double its normal damage. |
| `--enemy-damage half` / `double` | All contact damage halved or doubled. |

Headdy has 32 health, and most hits normally take 2.

### Japanese balance

| Option | What it does |
| --- | --- |
| `--jp-balance` | Plays like the easier Japanese release (details below). Needs `--jp-rom`. |
| `--jp-rom FILE` | The Japanese ROM, which the JP options copy their code and data from. Your US ROM is still the one being randomized. |

What `--jp-balance` changes:

- **Continues and tokens:** start with **2 continues** (US: 0), and get a continue every **10** tokens (US: 13).
- **1-1 boss:** slower attacks, and the energy balls do less damage.
- **Stair Wars:** fixed pattern (3 hooks, then an opening), and **4** hits instead of 8.
- **Act 7 real boss:** **9** hits (US: 17).
- **8-5 boss:** **33** hits but a bigger hitbox (US: 17).
- **9-3 boss:** **9** hits and slower attacks (US: 17).
- **6-1:** the JP enemy waves (1 shark instead of 5, plus the second Jayron wave) and the longer JP stage.
- **Layouts:** the **3-1 Headcase** the US version removed is back, along with the JP layouts of 6-2 and 6-4.
- **Smaller JP tweaks:** some enemy damage, speeds, timers and scores.

---

## Example setups

A casual randomizer:
```
python headdy_rando.py headdy.md casual.md --palettes safe --jp-balance --jp-rom headdy_jp.md
```

Hard mode:
```
python headdy_rando.py headdy.md hard.md --headcases chaos --enemy-damage double
```

Just the Japanese balance, nothing random:
```
python headdy_rando.py headdy.md jp.md --headcases off --jp-balance --jp-palettes --jp-rom headdy_jp.md
```

---

## Using it with the stage-select hub (optional)

`ap_hub_patch.py` turns the stage select into a hub, the groundwork for Archipelago:

- Each act returns to the stage select when you finish it.
- Secret Bonus Points are counted on the hub screen.
- The basketball code digits are remembered.

Always run the randomizer **first**, then the hub patch on its output:

```
python headdy_rando.py headdy.md rando.md --seed 1234 --palettes hue
python ap_hub_patch.py rando.md rando_hub.md
```

The hub patch will say the ROM is "not unmodified". That's expected.

---

## Troubleshooting

- **`python` is not recognized:** use `py` instead, or reinstall Python with "Add Python to PATH" ticked.
- **"not the known Dynamite Headdy (USA, Europe) ROM":** your ROM is a different version or a bad dump. The randomizer still runs, but things may break. The Japanese ROM can't be randomized; it's only used through `--jp-rom`.
- **"ROM space … is not empty (already randomized?)":** you fed it a ROM that was already randomized. Always start from the original ROM.
- **"JP balance and JP palettes need the Japanese ROM":** add `--jp-rom` with your Japanese ROM, or drop the JP options.
- **File names with spaces:** put them in quotes: `"Dynamite Headdy (USA, Europe).md"`.
- **Emulator says the checksum is wrong:** it shouldn't, because the randomizer fixes it. If it does, tell me which emulator.

---

## Reporting bugs

Please include:

- the **seed** and options (the first lines of the spoiler log)
- the act and what you were doing
- a save state if you can

A softlock with a specific head in a specific Headcase is the most useful kind of report.
