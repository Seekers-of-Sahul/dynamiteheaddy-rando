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
| `--no-pickup-logic` | Don't guarantee the heads needed to reach pickups (Vacuum in sets 8 and 19 in 4-1, which pulls in pickups you can't reach otherwise, Slammer in every 4-2 Headcase and in set 31 in 4-3, and Pin in set 39, the top Headcase in 9-1). |
| `--no-headtrip` | Never put Head Trip in a Headcase. It's a head to avoid: your head becomes so big and heavy that it's hard to move around, and enemies easily stomp on you. |
| `--no-boss-bomb` | Don't guarantee Bomb Head at the act 7 boss. |
| `--flying-heads` | Allow Rocket, Air and Feather Head in normal Headcases (see below). |
| `--head-hunter` | Add **Head Hunter** to the shuffle: an unused head (goggles and a headset) with a recoloured Ticker symbol. It attacks like the normal head, and while you wear it defeated enemies sometimes drop a pickup where it stood: a jelly bean (7 in 16; with `--new-pickups`, a quarter of them upside-down and 3 in 16 powerup beans), a 500-point item (3 in 16, only in the stages that have them: 2-2, 4-1, 4-2, 4-3, 8-1, 8-3 and 9-1) or a 1-up (1 in 16). A drop can't be picked up for its first 24 frames, so the blow that defeats the enemy doesn't collect it. Bosses never drop anything. It never counts as a required head. |

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
Ticker Head is never put in the 8-3 miniboss Headcase: that Headcase circles the miniboss, and stopping time throws it out of step so it vanishes after the fight.

**Flying heads (`--flying-heads`).** Without this option, flying heads never appear in normal stages. With it, they can show up in any shuffled Headcase, and you fly freely around the stage. They then work like the other heads:

- **A drops them**, back to normal Headdy.
- **They time out** after the same time as most heads.
- **They're cleared when you die or change stage.**

Flying heads are never placed in **4-1, 4-3, 5-1 or 8-2**, where they break the stage (the camera takes over, or the stage stops working). 8-1 shares its Headcase set with 8-2, so 8-1 doesn't get them either.

6-1 to 6-4 work exactly as before: 6-1's flying heads can't be dropped or time out, and you keep flying through deaths and from one 6-x stage to the next.

In act 7 the camera moves on its own when you reach the boss with a flying head. You get control back once the head runs out.

Known issues:

- **Stand-in shots.** The real shot graphics are only loaded in act 6, and other stages have no room for them, so outside act 6 the shots are drawn as small stars and fireballs instead. In act 6 they look as usual.
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

### Stage order

| Option | What it does |
| --- | --- |
| `--stage-order` | Play the acts in a random order. 1-1 stays first and 9-3 last (the ending and the secret door still follow it). A flying head from act 6 is cleared when you leave act 6, so it can't follow you into another stage. The 2-1 tutorial rooms still return to 2-1, basketball returns to the stage you came from, and a continue puts you back on the act you were on. Each curtain names the stage you're about to play. End-of-scene tallies appear after the acts that originally ended a scene, wherever those land. Not used with the stage-select hub, which picks the next stage itself. |

### Pickups

| Option | What it does |
| --- | --- |
| `--pickups shuffle` | Jelly beans, 500-point items and 1-ups swap places. 500-point items stay in the stages that have them, because their graphics are only loaded there. |
| `--pickups random` | Every pickup spot gets a random pickup: 45% jelly bean, 45% 500 points, 10% 1-up (500-point items only in stages that have them). The totals change from seed to seed. |
| `--new-pickups` | About half of the jelly beans become new pickups. **Upside-down bean** (a quarter of the beans): takes half your health (16), but never below 1. **Powerup beans** (another quarter): don't heal; they give a 15-second powerup, shown by an icon beside the health spotlight that blinks in the last 3 seconds. A new powerup replaces the current one; dying or finishing the act ends it. **Double jump** (bean with a star): jump once more in the air. **Power** (bean with a fireball): the head does double damage and its hitbox is half as big again. **Heavy** (two beans): half damage and no knockback. With Head Hunter, its jelly bean drops can be any of these too. |

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
- **8-5 boss:** a bigger hitbox. (The JP boss also takes 33 hits instead of 17, but the US version shows boss health in the spotlight and can't handle that much, so it keeps the US amount.)
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
- The hub screen shows, for the stage under the cursor, whether it's cleared and how many of its Secret Bonus Points you have, plus the code digits and your total of Secret Bonus Points.
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
