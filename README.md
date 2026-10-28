# Dynamite Headdy Randomizer

A randomizer, difficulty mod and [Archipelago](https://archipelago.gg) world for **Dynamite Headdy** (Mega Drive / Genesis, USA/Europe version).

- **Headcase shuffle** with logic, so every stage stays beatable and every Secret Bonus Point reachable.
- **Flying heads** (Rocket, Air, Feather) usable outside act 6 (you can press the A to drop them and they expire in time just like other heads.)
- **Palette shuffle:** safe, hue or chaos palettes.
- **Enemy damage:** shuffled, halved or doubled.
- **JP balance:** the easier Japanese release's continues, bosses, enemy waves and layouts, including the 3-1 Headcase the US version removed.
- **Stage-select hub** (optional patch, always on in Archipelago): every act is picked from the stage select, which counts your Secret Bonus Points and remembers the basketball code digits.
- **Archipelago:** stages are unlocked by items from the multiworld, and act clears, Secret Bonus Points and basketball wins are checks.

**No ROMs are included.** You need your own copy of Dynamite Headdy (USA, Europe). The JP options also need your own Dynamite Headdy (Japan) ROM, because they copy the Japanese code and data from it.

**[Mod your legal ROM on your browser →](https://seekers-of-sahul.github.io/dynamiteheaddy-rando/)** Pick your ROM and options, and download the randomized game. Nothing is uploaded.

## How do I download it?

| I want to… | Go to |
| --- | --- |
 | Make a randomized ROM to play on its own | the [web page](https://seekers-of-sahul.github.io/dynamiteheaddy-rando/), or [`randomizer/`](randomizer/README.md) from the command line |
| Play it in an Archipelago multiworld | [`archipelago/`](archipelago/README.md) |

The randomizer is one Python file with no dependencies:

```
python randomizer/headdy_rando.py "Dynamite Headdy (USA, Europe).md" rando.md --palettes safe
```

## ROM versions

| ROM | MD5 | Used for |
| --- | --- | --- |
| Dynamite Headdy (USA, Europe) | `d11ec9b230e88403cd75ef186a884c97` | everything |
| Dynamite Headdy (Japan) | `cdb36911439289d3453060f58682057c` | only the JP balance / JP palette options |

AI was consulted when coding the Python scripts, and it created the HTML page as well because I couldn't be bothered.

## License

The code in this repository is under the [MIT license](LICENSE). Dynamite Headdy is © Sega / Treasure; this project isn't affiliated with them.
