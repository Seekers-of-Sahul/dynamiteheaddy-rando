# Dynamite Headdy Setup Guide

## Required software

- [Archipelago](https://github.com/ArchipelagoMW/Archipelago/releases) 0.6.8 or newer
- [BizHawk](https://tasvideos.org/BizHawk/ReleaseHistory) 2.10 or newer (tested target: 2.11.1)
- Your own **Dynamite Headdy (USA, Europe)** ROM (MD5 `d11ec9b230e88403cd75ef186a884c97`)
- Only if your options use `jp_balance` or `jp_palettes`: your own **Dynamite Headdy (Japan)** ROM
  (MD5 `cdb36911439289d3453060f58682057c`). The JP code and data are copied from it when patching.

## Installing

1. Put `headdy.apworld` in the `custom_worlds` folder of your Archipelago install
   (or double-click it to install).
2. The first time you patch, Archipelago asks for your Dynamite Headdy ROM. If the seed uses the JP
   options, it also asks for the Japanese ROM (or set `jp_rom_file` under `headdy_options` in `host.yaml`).

## Playing

1. Open your `.apheaddy` patch file with the Archipelago Launcher (or the BizHawk Client). It creates
   the patched ROM, opens BizHawk and the BizHawk Client.
2. In BizHawk, open Tools > Lua Console and load `connector_bizhawk_generic.lua` from the `data/lua`
   folder of your Archipelago install (the client may do this for you).
3. Connect the **BizHawk Client** to the server. This is a separate Archipelago window (with an address
   box and a Connect button), not BizHawk's Lua Console. If it didn't open, start it from the
   Archipelago Launcher ("BizHawk Client"). Its log shows "Running handler for Dynamite Headdy" and
   every check it sends.
4. Press Start on the title screen to open the stage-select hub. Left/Right picks a stage; locked
   stages are skipped. The screen shows your Secret Bonus Points and the code digits you have.

Use the Genesis Plus GX core (BizHawk's default for Genesis).
