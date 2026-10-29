#!/usr/bin/env python3
"""Dynamite Headdy (USA, Europe) randomizer.

One file, no dependencies, so it can also run in a web page (e.g. Pyodide):
    rom_out, spoiler = randomize(rom_in_bytes, {'seed': 1234, 'palettes': 'hue'})
OPTIONS below lists every option with its default, choices and a description,
so a page can build its form from it.

Command line:
    python3 headdy_rando.py in.bin out.bin --seed 1234 --palettes hue
    python3 headdy_rando.py --help

Features
  Headcases   randomizes the heads each Headcase cycles through (logic keeps
              every stage beatable and, by default, every bonus point reachable)
  Palettes    jp_palettes: use the 8 palettes the US version recoloured
              palettes: recolour every stage at runtime (hue / chaos)
  Enemies     enemy_damage: contact damage per object type ($001244 + type + 2,
              read every time Headdy is hit at $0109F2)
              (No enemy HP option yet: most enemies have flag bit 3 set and die
              in one hit without reading HP, see $010C36.)

How the palette shuffle works
  The game keeps its 64 colours in RAM at $FFB300 and DMAs them to the VDP
  every VBlank ($011BA0). The patch replaces that DMA with a loop that sends
  each colour through a lookup table picked by the current stage, so
  everything is recoloured consistently: stage palettes, boss flashes,
  palette cycling and fades. Menus and the title stay vanilla. Palette line 2
  (Headdy, enemies, Headcases) can be left untouched.

ROM space used (all $FF padding in the original):
  $0CDB00-$0CDCFF  palette code + stage table
  $1A1000-$1A1FFF  JP balance data (6-1 spawn list, level layouts, helper)
  $0CE000-$0CFFFF, $1A2000-$1A3FFF  palette lookup tables (4 per 4 KB block)
  ($1A0900-$1A1FFF is left free for ap_hub_patch.py)
"""
import argparse, colorsys, hashlib, random, struct, sys

US_SHA1 = 'e843decdff262791b1237f1545f5b17c56712d5f'
CHECK_END = 0x060002

OPTIONS = {
    'seed':          {'default': None, 'type': 'int',
                      'desc': 'Random seed (blank = random).'},
    'headcases':     {'default': 'safe', 'choices': ['off', 'safe', 'chaos'],
                      'desc': 'Headcase contents. safe: every Headcase keeps one of its '
                              'original heads; chaos: only the logic is guaranteed.'},
    'bonus_logic':   {'default': True, 'type': 'bool',
                      'desc': 'Guarantee the heads needed for Secret Bonus Points.'},
    'headtrip':      {'default': True, 'type': 'bool',
                      'desc': 'Allow Head Trip (a huge, heavy head that makes you slow and easy to stomp) in Headcases.'},
    'boss_bomb':     {'default': True, 'type': 'bool',
                      'desc': 'Keep Bomb Head available at the act 7 boss.'},
    'flying_heads':  {'default': False, 'type': 'bool',
                      'desc': 'Allow Rocket, Air and Feather Head in normal Headcases. They '
                              'time out like other heads and A drops them. Outside act 6 their '
                              'shots are drawn as stars and fireballs.'},
    'jp_balance':    {'default': False, 'type': 'bool',
                      'desc': 'Japanese difficulty: 2 starting continues, a continue every '
                              '10 tokens, JP enemy damage/HP, JP 1-1 boss, Stair Wars, act 7, '
                              '8-5 and 9-3 bosses, JP 6-1 waves and the 3-1/6-2/6-4 layouts.'},
    'jp_palettes':   {'default': False, 'type': 'bool',
                      'desc': 'Restore the Japanese colours of the 8 palettes the US '
                              'version changed.'},
    'palettes':      {'default': 'off', 'choices': ['off', 'safe', 'hue', 'chaos'],
                      'desc': 'Recolour each stage. safe: gentle shifts and warm/cool/muted '
                              'moods that keep every colour as bright as before; hue: any hue '
                              'rotation; chaos: swap and invert colour channels.'},
    'palette_sprites': {'default': False, 'type': 'bool',
                      'desc': 'Also recolour Headdy, enemies and Headcases '
                              '(palette line 2).'},
    'enemy_damage':  {'default': 'off', 'choices': ['off', 'random', 'half', 'double'],
                      'desc': 'Contact damage to Headdy (health is 32, most hits take 2). '
                              'random: each object type x0.5-x2.'},
}


# ---------------------------------------------------------------- helpers

def w16(rom, a):
    return rom[a] << 8 | rom[a + 1]


def l32(rom, a):
    return struct.unpack('>I', rom[a:a + 4])[0]


def put16(rom, a, v):
    rom[a], rom[a + 1] = (v >> 8) & 0xFF, v & 0xFF


def fix_checksum(rom):
    s = 0
    for i in range(0x200, CHECK_END, 2):
        s = (s + w16(rom, i)) & 0xFFFF
    put16(rom, 0x18E, s)
    return s


def claim(rom, start, size, what):
    if any(b != 0xFF for b in rom[start:start + size]):
        raise ValueError('ROM space $%06X-$%06X for %s is not empty '
                         '(already randomized?)' % (start, start + size - 1, what))


# Stage IDs ($FFE8AA) in stage-select order (list at $006786).
ACTS = [('1-1', 0x00), ('2-1', 0x0C), ('2-2', 0x02), ('2-3', 0x06), ('3-1', 0x10),
        ('3-2', 0x12), ('3-3', 0x32), ('3-4', 0x14), ('4-1', 0x04), ('4-2', 0x16),
        ('4-3', 0x18), ('4-4', 0x34), ('5-1', 0x36), ('5-2', 0x1A), ('5-3', 0x1C),
        ('5-4', 0x1E), ('6-1', 0x50), ('6-2', 0x52), ('6-3', 0x54), ('6-4', 0x56),
        ('7', 0x20), ('8-1', 0x22), ('8-2', 0x24), ('8-3', 0x26), ('8-4', 0x28),
        ('8-5', 0x2A), ('9-1', 0x2C), ('9-2', 0x2E), ('9-3', 0x30)]
SUBAREAS = {0x08: 0x0C, 0x0A: 0x0C, 0x0E: 0x0C}     # 2-1 tutorial rooms follow 2-1
EXTRA_STAGES = {0x3C: 'opening', 0x38: 'secret boss', 0x44: 'basketball',
                0x46: 'basketball', 0x4C: 'secret door room'}
STAGE_NAMES = dict((s, n) for n, s in ACTS)
STAGE_NAMES.update({0x3C: 'opening', 0x08: 'Headcase tutorial'})


# ---------------------------------------------------------------- Headcases

NAMES = {
    0x020: 'Slammer', 0x040: 'Super', 0x060: 'Ticker', 0x080: 'Spike',
    0x0A0: 'War', 0x0C0: 'Liberty', 0x0E0: 'Empty', 0x100: 'Pin',
    0x120: 'Bomb', 0x140: 'Vacuum', 0x160: 'Pig', 0x1A0: 'Head Trip',
    0x1C0: 'Sleepy', 0x1E0: 'Lotsa', 0x200: 'Protector', 0x220: 'Rocket',
    0x240: 'Air', 0x260: 'Feather',
}
SLAMMER, SPIKE, PIN, PROTECTOR, BOMB, LIBERTY = 0x020, 0x080, 0x100, 0x200, 0x120, 0x0C0
TICKER = 0x060
POOL = [0x020, 0x040, 0x060, 0x080, 0x0A0, 0x0E0, 0x100, 0x120, 0x140,
        0x160, 0x1A0, 0x1C0, 0x1E0, 0x200]
PROGRESSION = {
    4:  [(SPIKE, PIN)],   # 2-2, 4th Headcase
    28: [(SLAMMER,)],     # 4-2, 3rd Headcase
    34: [(SPIKE, PIN)],   # 8-1 / 8-2
    10: [(SPIKE,)],       # 8-3, floating around the miniboss
}
BONUS = {
    4:  [(SPIKE,)],       # 2-2, 4th
    28: [(SLAMMER,)],     # 4-2 hammer blocks
    29: [(SLAMMER,)],
    30: [(SLAMMER,)],
    34: [(SPIKE,)],       # 8-1 (Pin can't reach the bonus point)
    39: [(SLAMMER,)],     # 9-1
    41: [(SLAMMER,)],
}
# Stages where flying heads must not appear (play-testing): 4-1 (the camera
# scrolls on its own at the end and Headdy is lost), 4-3 (same when carried into
# 4-4), 5-1 (breaks completely), 8-2. Every set used by a Headcase there is kept
# free of them. They never count for the requirements above: they can't break
# Spike's wooden boards (2-2, 8-3) or fit Pin's paths.
FLY_BANNED_STAGES = {0x04: '4-1', 0x18: '4-3', 0x36: '5-1', 0x24: '8-2'}
# Heads that break a particular Headcase.
# Set 10, the 8-3 miniboss Headcase, circles the miniboss. Ticker stops time for the
# Headcase but not the boss, so it falls out of step and vanishes after the fight.
SET_BANS = {10: {TICKER}}
RUNTIME_USERS = {
    **{k: ['2-3 boss (random 14-29)'] for k in range(14, 30)},
    14: ['3-2 switching Headcase', '2-3 boss (random 14-29)'],
    15: ['3-2 switching Headcase', '2-3 boss (random 14-29)'],
    16: ['5-3 switching Headcase', '2-3 boss (random 14-29)'],
    17: ['5-3 switching Headcase', '2-3 boss (random 14-29)'],
    38: ['act 7 boss'], 40: ['act 7 boss'],
}
SET_TABLE, NUM_SETS = 0x01D222, 46
STAGE_TABLE, HEADCASE_TYPE = 0x059C4A, 0x018


def find_headcases(rom):
    """[(stage, x, entry_addr)] for every type-$018 placement entry."""
    ptrs = sorted({l32(rom, STAGE_TABLE + s * 2) for s in range(0, 0x80, 2)
                   if 0x60000 <= l32(rom, STAGE_TABLE + s * 2) < 0x200000})
    found, seen = [], set()
    for s in range(0, 0x80, 2):
        p = l32(rom, STAGE_TABLE + s * 2)
        if not 0x60000 <= p < 0x200000:
            continue
        nxt = [t for t in ptrs if t > p]
        lim = nxt[0] if nxt else p + 1024
        a, col = p, 0
        while a < lim:
            q = l32(rom, a)
            if not 0x60000 <= q < 0x200000:
                break
            e = q
            while rom[e] != 0 and e < q + 8 * 400:
                if w16(rom, e + 6) == HEADCASE_TYPE and e not in seen:
                    seen.add(e)
                    found.append((s, col * 256 + rom[e], e))
                e += 8
            a += 4
            col += 1
    return found


def read_set(rom, k):
    return [h for h in (w16(rom, SET_TABLE + 6 * k + 2 * i) for i in range(3)) if h]


def nm(h):
    return NAMES.get(h, '$%03X' % h)


FLYING = [0x220, 0x240, 0x260]
FLY_FIX = 0x1A1F00            # free space for the flying-head wrapper
FLY_TIMER = 0x400             # same as most heads


def patch_flying_heads(rom):
    """Flying heads picked from a Headcase outside 6-1 get the normal head timer.

    Their pickup routines ($01155E/$011572/$01157A) clear the timer $E8D8, and
    the per-frame head code at $015B58 skips both the timeout and the cancel
    button while it is zero. The wrappers call the original routine, then set
    the timer unless the stage is 6-1 ($50), whose flight must not be cancelled.
    The drop routine ($015B9E) already returns Headdy from flying to normal.
    The 6-x flying icons call the routines directly ($0111F8) and stay as they are.
    Also clears flying heads on death / stage change outside 6-2..6-4 (see below).
    """
    claim(rom, FLY_FIX, 0x80, 'flying-head fix')
    c, entries = bytearray(), {}
    for head, orig in ((0x220, 0x01155E), (0x240, 0x011572), (0x260, 0x01157A)):
        entries[head] = FLY_FIX + len(c)
        c += struct.pack('>HIHI', 0x4EB9, orig, 0x4EF9, 0)     # jsr orig / jmp common
    common = FLY_FIX + len(c)
    for head in entries:
        struct.pack_into('>I', c, entries[head] - FLY_FIX + 8, common)
    c += bytes.fromhex('0c780050e8aa6706')                  # cmpi.w #$50,$E8AA / beq.s +6
    c += struct.pack('>HHH', 0x31FC, FLY_TIMER, 0xE8D8)      # move.w #timer,$E8D8
    c += bytes.fromhex('4e75')                              # rts
    # Stage load / respawn ($007EB2) keeps a flying head (for 6-2..6-4) unless the
    # stage is 5-4, 6-1 or 7. Keep it only in 6-2..6-4; clear it everywhere else.
    keep = FLY_FIX + len(c)
    c += bytes.fromhex('0c780052e8aa' '6514'               # cmpi.w #$52,$E8AA / bcs.s clear
                       '0c780056e8aa' '620c'               # cmpi.w #$56,$E8AA / bhi.s clear
                       '0c780260ee0a')                     # cmpi.w #$260,$EE0A (replaced insn)
    c += struct.pack('>HI', 0x4EF9, 0x007EB8)               # jmp $007EB8 (beq on these flags)
    c += struct.pack('>HI', 0x4EF9, 0x007F14)               # clear: jmp $007F14 (normal reset)
    if bytes(rom[0x007EB2:0x007EB8]) != bytes.fromhex('0c780260ee0a'):
        raise ValueError('stage-load head code at $007EB2 is not the original')
    rom[0x007EB2:0x007EB8] = struct.pack('>HI', 0x4EF9, keep)
    rom[FLY_FIX:FLY_FIX + len(c)] = c
    for head, a in entries.items():
        t = 0x011312 + (head >> 3)
        if struct.unpack('>I', rom[t:t + 4])[0] not in (0x01155E, 0x011572, 0x01157A):
            raise ValueError('head handler table at $%06X is not the original' % t)
        rom[t:t + 4] = struct.pack('>I', a)
    patch_flying_shots(rom)
    return ['== Flying heads allowed in Headcases: A drops them, they time out after '
            '%d frames (except in 6-1), and they are cleared on death and stage change '
            '(except between 6-2 and 6-4). Never in %s. Outside act 6 their shots use '
            'the star and fireball sprites.' % (FLY_TIMER, ', '.join(FLY_BANNED_STAGES.values()))]


# Flying-head shots outside act 6.
# The shots (object types $6D8 Rocket, $6F4 Rocket trail, $6DC Air, $6E0 Feather)
# draw tiles $3B0-$3BA, which only act 6 loads; other stages keep their own
# graphics there, so the shots come out garbled. Video memory is nearly full in
# most stages, so instead of loading the real art, shots spawned outside act 6
# get their own animation scripts that draw the star ($34E) and fireball ($34F),
# which every stage has loaded. Act 6 keeps the real graphics.
#
# Objects get their script when spawned ($00095A: move.l $19E4(a3),-$2400(a6),
# a3 = type). A script step is: flags byte, duration byte, word offset (from the
# word itself) to a sprite piece; duration 0 jumps by the offset. A piece is:
# size byte ((w-1)<<2 | h-1), count byte, attribute word (palette 2 + tile), y, x.
FLY_SHOT = 0x1D6000           # free space (after the Archipelago marker and name)
SCRIPT_TABLE = 0x0019E4       # animation script per object type
SPAWN_SCRIPT = 0x00095A
STAR, FIREBALL = 0x34E, 0x34F
SHOT_SCRIPTS = {              # type: [(duration, tile)], looping
    0x6D8: [(1, FIREBALL)],                 # Rocket's beam
    0x6F4: [(1, FIREBALL), (1, STAR)],      # Rocket's glow / spark
    0x6DC: [(2, FIREBALL)],                 # Air's ball
    0x6E0: [(8, STAR), (8, FIREBALL)],      # Feather's shot
}


def patch_flying_shots(rom):
    claim(rom, FLY_SHOT, 0x100, 'flying-head shots')
    if bytes(rom[SPAWN_SCRIPT:SPAWN_SCRIPT + 6]) != bytes.fromhex('2d6b19e4dc00'):
        raise ValueError('object spawn code at $%06X is not the original' % SPAWN_SCRIPT)
    c = bytearray()
    # Code: run the original instruction, then for shot types outside stages
    # $50-$56 (act 6) replace the script with ours.
    c += bytes.fromhex('2d6b19e4dc00')              # move.l $19E4(a3),-$2400(a6)
    c += bytes.fromhex('b6fc06d8' '6528'            # cmpa.w #$6D8,a3 / bcs.s done
                       'b6fc06f4' '6222'            # cmpa.w #$6F4,a3 / bhi.s done
                       '0c780050e8aa' '6508'        # cmpi.w #$50,$E8AA / bcs.s alt
                       '0c780056e8aa' '6312'        # cmpi.w #$56,$E8AA / bls.s done
                       '2f08')                      # alt: move.l a0,-(sp)
    table_ref = len(c) + 2
    c += bytes.fromhex('41f900000000'               # lea table-$6D8,a0
                       '2070b000'                   # movea.l 0(a0,a3.w),a0
                       '2d48dc00'                   # move.l a0,-$2400(a6)
                       '205f'                       # movea.l (sp)+,a0
                       '4e75')                      # done: rts
    done = len(c) - 2
    assert (c[11], c[17], c[25], c[33]) == (done - 12, done - 18, 34 - 26, done - 34), 'branch offsets'
    # Sprite pieces, one per tile used.
    pieces = {}
    for t in sorted({t for steps in SHOT_SCRIPTS.values() for _, t in steps}):
        pieces[t] = FLY_SHOT + len(c)
        c += struct.pack('>BBHbb', 0, 1, 0x4000 | t, -4, -4)
    # Scripts
    scripts = {}
    for typ, steps in SHOT_SCRIPTS.items():
        scripts[typ] = start = FLY_SHOT + len(c)
        for dur, t in steps:
            here = FLY_SHOT + len(c) + 2
            c += struct.pack('>BBh', 0, dur, pieces[t] - here)
        here = FLY_SHOT + len(c) + 2
        c += struct.pack('>BBh', 0, 0, start - here)            # loop
    # Table indexed by type - $6D8 (types without a script of ours keep the original)
    if len(c) % 2:
        c.append(0)
    table = FLY_SHOT + len(c)
    for typ in range(0x6D8, 0x6F8, 4):
        orig = struct.unpack('>I', rom[SCRIPT_TABLE + typ:SCRIPT_TABLE + typ + 4])[0]
        c += struct.pack('>I', scripts.get(typ, orig))
    struct.pack_into('>I', c, table_ref, table - 0x6D8)
    assert len(c) <= 0x100
    rom[FLY_SHOT:FLY_SHOT + len(c)] = c
    rom[SPAWN_SCRIPT:SPAWN_SCRIPT + 6] = struct.pack('>HI', 0x4EB9, FLY_SHOT)


def randomize_headcases(rom, rng, o):
    pool = [h for h in POOL if o['headtrip'] or h != 0x1A0]
    if o['flying_heads']:
        pool += FLYING
    users = {}
    for st, x, e in find_headcases(rom):
        k = rom[e + 5] & 0x7F
        users.setdefault(k, []).append('%s (X=%d)' % (STAGE_NAMES.get(st, '$%02X' % st), x))
    for k, u in RUNTIME_USERS.items():
        users.setdefault(k, []).extend(u)
    fixed = {44}                  # the 6-1 Headcase that starts the flight
    no_fly = {rom[e + 5] & 0x7F for st, x, e in find_headcases(rom) if st in FLY_BANNED_STAGES}
    log = ['== Headcases (%s, bonus logic %s, head trip %s, act 7 bomb %s)' % (
        o['headcases'], 'on' if o['bonus_logic'] else 'off',
        'on' if o['headtrip'] else 'off',
        'kept' if o['boss_bomb'] else 'not kept')]
    for k in range(NUM_SETS):
        old = read_set(rom, k)
        if k in fixed or not old:
            continue
        reqs = [(r, 'P') for r in PROGRESSION.get(k, [])]
        if o['bonus_logic']:
            reqs += [(r, 'B') for r in BONUS.get(k, [])]
        reqs = [r for r, kind in reqs]
        if k == 38 and o['boss_bomb']:
            reqs.append((BOMB,))
        heads = [LIBERTY] if LIBERTY in old else []
        for opts in reqs:
            if not any(h in heads for h in opts):
                heads.append(rng.choice(opts))
        if o['headcases'] == 'safe':
            keep = [h for h in old if h != LIBERTY and h not in heads]
            if keep and len(heads) < len(old):
                heads.append(rng.choice(keep))
        size = max(len(old), len(heads))
        set_pool = [h for h in pool if not (k in no_fly and h in FLYING)
                    and h not in SET_BANS.get(k, ())]
        while len(heads) < size:
            h = rng.choice(set_pool)
            if h not in heads:
                heads.append(h)
        rng.shuffle(heads)
        if LIBERTY in heads:
            # Liberty must stay last: when it has to be skipped the Headcase
            # restarts from the first head, so Liberty first hangs the game.
            heads.remove(LIBERTY)
            heads.append(LIBERTY)
        for i, h in enumerate(heads + [0] * (3 - len(heads))):
            put16(rom, SET_TABLE + 6 * k + 2 * i, h)
        log.append('set %2d  %-28s -> %-28s used by: %s' % (
            k, ', '.join(map(nm, old)), ', '.join(map(nm, heads)),
            '; '.join(users.get(k, ['nothing known']))))
    return log


# ---------------------------------------------------------------- palettes

PAL_TABLE_US, PAL_TABLE_JP = 0x003196, 0x003186    # 32 bytes per palette, index 1-138
JP_CHANGED = [13, 22, 26, 55, 57, 65, 87, 131]     # palettes the US version recoloured

PAL_HOOK = 0x011BA0           # VBlank: set up the CRAM DMA from $FFB300 ...
PAL_HOOK_END = 0x011BC6       # ... up to here
PAL_CODE = 0x0CDB00
LUT_BLOCKS = [0x0CE000, 0x0CF000, 0x1A2000, 0x1A3000]
LUT_SLOTS = [b + off for b in LUT_BLOCKS for off in (0x000, 0x010, 0x100, 0x110)]
MODE_LOADING, MODE_PLAYING = 0x1C, 0x20


def apply_jp_palettes(rom, jp_rom):
    """Copy the JP colours of the palettes the US version changed (from the JP ROM)."""
    for i in JP_CHANGED:
        rom[PAL_TABLE_US + 32 * i:PAL_TABLE_US + 32 * i + 32] = \
            jp_rom[PAL_TABLE_JP + 32 * i:PAL_TABLE_JP + 32 * i + 32]


def lut_hue(rng):
    """Rotate the hue by a random amount; keep brightness and saturation."""
    shift = rng.uniform(0.12, 0.88)
    sat = rng.uniform(0.85, 1.15)
    def f(r, g, b):
        h, s, v = colorsys.rgb_to_hsv(r / 7, g / 7, b / 7)
        r2, g2, b2 = colorsys.hsv_to_rgb((h + shift) % 1.0, min(1.0, s * sat), v)
        return [min(7, int(round(c * 7))) for c in (r2, g2, b2)]
    return f, 'hue %+d deg' % round(shift * 360 if shift <= 0.5 else (shift - 1) * 360)


def _luma(r, g, b):
    return 0.299 * r + 0.587 * g + 0.114 * b


def _keep_luma(rgb, y0):
    """Nudge an RGB triple (0-1) back to luminance y0, then clamp."""
    r, g, b = rgb
    for _ in range(4):
        d = y0 - _luma(r, g, b)
        if abs(d) < 1e-3:
            break
        r, g, b = (min(1.0, max(0.0, c + d)) for c in (r, g, b))
    return r, g, b


SAFE_MOODS = [
    # (description, hue shift range in turns, saturation x, tint hue, tint amount)
    ('shift', (0.05, 0.125), 1.0, None, 0.0),
    ('shift', (-0.125, -0.05), 1.0, None, 0.0),
    ('warm', (-0.03, 0.03), 0.95, 0.08, 0.25),      # towards orange
    ('cool', (-0.03, 0.03), 0.95, 0.60, 0.25),      # towards blue
    ('dusk', (-0.08, -0.02), 0.85, 0.80, 0.20),     # towards purple
    ('muted', (-0.05, 0.05), 0.55, None, 0.0),
]


def lut_safe(rng):
    """Gentle recolour: small hue shift or a mood tint, perceived brightness kept.

    Every colour keeps its luminance (0.299R + 0.587G + 0.114B), so light and
    dark stay where they were and the stage reads the same. Greys stay grey.
    """
    name, (lo, hi), sat, tint, amt = rng.choice(SAFE_MOODS)
    shift = rng.uniform(lo, hi)
    def f(r, g, b):
        r0, g0, b0 = r / 7, g / 7, b / 7
        y0 = _luma(r0, g0, b0)
        h, s, v = colorsys.rgb_to_hsv(r0, g0, b0)
        if s < 0.05:
            return [r, g, b]
        rgb = colorsys.hsv_to_rgb((h + shift) % 1.0, min(1.0, s * sat), v)
        if tint is not None:
            t = colorsys.hsv_to_rgb(tint, 0.6, 1.0)
            rgb = tuple(c * (1 - amt) + c * tc * amt * 1.6 for c, tc in zip(rgb, t))
        rgb = _keep_luma(rgb, y0)
        return [min(7, max(0, int(round(c * 7)))) for c in rgb]
    deg = round(shift * 360)
    return f, '%s %+d deg' % (name, deg)


def lut_chaos(rng):
    """Swap colour channels and invert some of them."""
    perms = [(0, 1, 2), (0, 2, 1), (1, 0, 2), (1, 2, 0), (2, 0, 1), (2, 1, 0)]
    while True:
        perm = rng.choice(perms)
        inv = [rng.random() < 0.3 for _ in range(3)]
        if perm != (0, 1, 2) or any(inv):
            break
    def f(r, g, b):
        src = (r, g, b)
        return [7 - src[perm[i]] if inv[i] else src[perm[i]] for i in range(3)]
    desc = 'channels %s%s' % (''.join('RGB'[p] for p in perm),
                              ', invert ' + ''.join('RGB'[i] for i in range(3) if inv[i])
                              if any(inv) else '')
    return f, desc


def write_lut(rom, base, f):
    # A Genesis colour is 0000BBB0GGG00RRR0; the table is indexed by
    # (colour & $0EEE), so four tables interleave in one 4 KB block.
    for b in range(8):
        for g in range(8):
            for r in range(8):
                r2, g2, b2 = f(r, g, b)
                put16(rom, base + (b << 9 | g << 5 | r << 1), b2 << 9 | g2 << 5 | r2 << 1)


def build_pal_code(table_addr, keep_mask):
    """VBlank colour transfer. Entered with a0 = $C00004 (VDP control)."""
    c = bytearray()
    def w(*ws):
        for x in ws:
            c.extend(struct.pack('>H', x & 0xFFFF))
    orig = len(c)
    # --- not in a stage: original DMA (the replaced instructions, verbatim)
    w(0x0C78, MODE_PLAYING, 0xE802)        # cmpi.w #$20,$E802.w
    w(0x6700, 0)                           # beq.w go        (fixed below)
    beq1 = len(c) - 2
    w(0x0C78, MODE_LOADING, 0xE802)        # cmpi.w #$1C,$E802.w
    w(0x6700, 0)                           # beq.w go
    beq2 = len(c) - 2
    dma = len(c)
    w(0x30BC, 0x8F02)                      # move.w #$8F02,(a0)
    w(0x20BC, 0x9340, 0x9400)              # move.l #$93409400,(a0)
    w(0x30BC, 0x9580)                      # move.w #$9580,(a0)
    w(0x30BC, 0x96D9)                      # move.w #$96D9,(a0)
    w(0x30BC, 0x977F)                      # move.w #$977F,(a0)
    w(0x21FC, 0xC000, 0x0080, 0xB6C0)      # move.l #$C0000080,$B6C0.w
    w(0x30B8, 0xB6C0)                      # move.w $B6C0.w,(a0)
    w(0x30B8, 0xB6C2)                      # move.w $B6C2.w,(a0)
    w(0x4EF9, PAL_HOOK_END >> 16, PAL_HOOK_END & 0xFFFF)   # jmp $011BC6
    # --- in a stage
    go = len(c)
    for at in (beq1, beq2):
        struct.pack_into('>h', c, at, go - at)
    w(0x48E7, 0xF070)                      # movem.l d0-d3/a1-a3,-(sp)
    w(0x7000)                              # moveq #0,d0
    w(0x1038, 0xE8AB)                      # move.b $E8AB.w,d0   (stage ID)
    w(0x0240, 0x007E)                      # andi.w #$7E,d0
    w(0xD040)                              # add.w d0,d0          (x4: long table)
    w(0x247C, table_addr >> 16, table_addr & 0xFFFF)  # movea.l #table,a2
    w(0x2472, 0x0000)                      # movea.l (a2,d0.w),a2
    w(0xB4FC, 0x0000)                      # cmpa.w #0,a2
    w(0x6600, 0)                           # bne.w xfer
    bne = len(c) - 2
    w(0x4CDF, 0x0E0F)                      # movem.l (sp)+,d0-d3/a1-a3
    w(0x6000, 0)                           # bra.w dma
    struct.pack_into('>h', c, len(c) - 2, dma - (len(c) - 2))
    xfer = len(c)
    struct.pack_into('>h', c, bne, xfer - bne)
    w(0x30BC, 0x8F02)                      # move.w #$8F02,(a0)   autoincrement 2
    w(0x20BC, 0xC000, 0x0000)              # move.l #$C0000000,(a0)  CRAM write @0
    w(0x47F9, 0x00C0, 0x0000)              # lea $C00000,a3
    w(0x43F8, 0xB300)                      # lea $FFB300.w,a1
    w(0x123C, keep_mask)                   # move.b #keep,d1
    w(0x7403)                              # moveq #3,d2
    line = len(c)
    w(0xE209)                              # lsr.b #1,d1
    w(0x6500, 0)                           # bcs.w raw
    bcs = len(c) - 2
    w(0x760F)                              # moveq #15,d3
    lut_loop = len(c)
    w(0x3019)                              # move.w (a1)+,d0
    w(0x0240, 0x0EEE)                      # andi.w #$0EEE,d0
    w(0x36B2, 0x0000)                      # move.w (a2,d0.w),(a3)
    w(0x51CB, lut_loop - (len(c) + 2))           # dbra d3,lut_loop
    w(0x6000, 0)                           # bra.w next
    bra_next = len(c) - 2
    raw = len(c)
    struct.pack_into('>h', c, bcs, raw - bcs)
    w(0x760F)                              # moveq #15,d3
    raw_loop = len(c)
    w(0x3699)                              # move.w (a1)+,(a3)
    w(0x51CB, raw_loop - (len(c) + 2))           # dbra d3,raw_loop
    nxt = len(c)
    struct.pack_into('>h', c, bra_next, nxt - bra_next)
    w(0x51CA, line - (len(c) + 2))               # dbra d2,line
    w(0x4CDF, 0x0E0F)                      # movem.l (sp)+,d0-d3/a1-a3
    w(0x4EF9, PAL_HOOK_END >> 16, PAL_HOOK_END & 0xFFFF)   # jmp $011BC6
    return bytes(c)


def randomize_palettes(rom, rng, o):
    log = ['== Palettes (%s, sprites %s)' % (
        o['palettes'], 'recoloured' if o['palette_sprites'] else 'vanilla')]
    expect = bytes.fromhex('30bc8f0220bc9340940030bc958030bc96d930bc977f'
                           '21fcc0000080b6c030b8b6c030b8b6c2')
    if bytes(rom[PAL_HOOK:PAL_HOOK_END]) != expect:
        raise ValueError('palette DMA at $%06X is not the original code' % PAL_HOOK)
    claim(rom, PAL_CODE, 0x500, 'palette code')
    for b in LUT_BLOCKS:
        claim(rom, b, 0x1000, 'palette tables')
    make = {'safe': lut_safe, 'hue': lut_hue, 'chaos': lut_chaos}[o['palettes']]
    luts = []
    for slot in LUT_SLOTS:
        f, desc = make(rng)
        write_lut(rom, slot, f)
        luts.append((slot, desc))
    # one table per act, no two acts in a row alike
    order = luts[:]
    rng.shuffle(order)
    table = [0] * 64                     # stage ID / 2 -> table address (0 = vanilla)
    per_stage = {}
    for i, (name, sid) in enumerate(ACTS):
        per_stage[sid] = order[i % len(order)]
    for sid, parent in SUBAREAS.items():
        per_stage[sid] = per_stage[parent]
    for sid in EXTRA_STAGES:
        per_stage[sid] = rng.choice(luts)
    for sid, (slot, desc) in per_stage.items():
        table[sid >> 1] = slot
    for name, sid in ACTS:
        log.append('%-4s %s' % (name, per_stage[sid][1]))
    for sid, name in EXTRA_STAGES.items():
        log.append('%-4s %s (%s)' % ('$%02X' % sid, per_stage[sid][1], name))
    table_addr = PAL_CODE + 0x100
    keep = 0 if o['palette_sprites'] else 0b0100
    code = build_pal_code(table_addr, keep)
    assert len(code) <= 0x100
    rom[PAL_CODE:PAL_CODE + len(code)] = code
    for i, t in enumerate(table):
        rom[table_addr + 4 * i:table_addr + 4 * i + 4] = struct.pack('>I', t)
    # hook: jmp PAL_CODE, then nops up to the end of the replaced code
    hook = struct.pack('>HI', 0x4EF9, PAL_CODE)
    hook += b'\x4e\x71' * ((PAL_HOOK_END - PAL_HOOK - len(hook)) // 2)
    rom[PAL_HOOK:PAL_HOOK_END] = hook
    return log


# ---------------------------------------------------------------- enemy stats

T1, T2, NUM_TYPES = 0x000AA4, 0x001244, 488    # per type (ID = 4 x n): 4 bytes each
# T1: flags.w, ?, HP     T2: hitbox w, hitbox h, contact damage, score


def randomize_stats(rom, rng, o):
    log = []
    if o['enemy_damage'] != 'off':
        log.append('== Enemy damage (%s)' % o['enemy_damage'])
        changed = 0
        for t in range(0, NUM_TYPES * 4, 4):
            d = rom[T2 + t + 2]
            if not 0 < d < 10:          # 0 = harmless, 10+ = special hazards
                continue
            if o['enemy_damage'] == 'half':
                n = max(1, d // 2)
            elif o['enemy_damage'] == 'double':
                n = d * 2
            else:
                n = max(1, min(16, int(round(d * rng.choice([0.5, 1, 1, 1.5, 2])))))
            if n != d:
                rom[T2 + t + 2] = n
                changed += 1
                if o['enemy_damage'] == 'random':
                    log.append('type $%03X  %d -> %d' % (t, d, n))
        log.append('%d object types changed' % changed)
    return log


# ---------------------------------------------------------------- JP balance

# JP code and data, as recipes (make_jp_recipes.py). No ROM bytes: copies from the JP ROM, plus our own bytes.
JP_BLOCKS = [
    (0x01E96E, [
        ('J', 0x01E6B2, 17),
        ('H', '3c008400c200d8015801a201d0025c'),
        ('J', 0x01E6D2, 22),
        ('H', '4a6ede026e001d06426ede02610002da'),
        ('J', 0x01E6FA, 24),
        ('H', '4a406d00002e56414a41'),
        ('J', 0x01E720, 43),
        ('H', 'f0'),
        ('J', 0x01E74C, 34),
        ('H', 'f2fe'),
        ('J', 0x01E770, 3),
        ('H', '0a'),
        ('J', 0x01E774, 19),
        ('H', '50'),
        ('J', 0x01E788, 30),
        ('H', '4a6ee50067001c4e'),
        ('J', 0x01E7B0, 13),
        ('H', '40'),
        ('J', 0x01E7BE, 120),
        ('H', 'a5f44a00'),
        ('J', 0x01E83C, 47),
        ('H', '22'),
        ('J', 0x01E86C, 57),
        ('H', 'e8'),
        ('J', 0x01D5D4, 8),
        ('H', '1b50'),
        ('J', 0x01E8B2, 13),
        ('H', '42'),
        ('J', 0x01E8C0, 70),
        ('J', 0x01DE96, 10),
        ('J', 0x01E910, 61),
        ('H', 'b4'),
        ('J', 0x01E94E, 13),
        ('H', 'a6'),
        ('J', 0x01E95C, 32),
        ('H', '9762'),
        ('J', 0x01E97E, 2),
        ('H', '974a'),
        ('J', 0x01E982, 2),
        ('H', '9732'),
        ('J', 0x01E986, 2),
        ('H', '971a001a9702'),
        ('J', 0x01E98E, 13),
        ('H', '66'),
        ('J', 0x01E99C, 13),
        ('H', '58'),
        ('J', 0x01E9AA, 32),
        ('H', '9702'),
        ('J', 0x01E9CC, 2),
        ('H', '971a'),
        ('J', 0x01E9D0, 2),
        ('H', '9732'),
        ('J', 0x01E9D4, 2),
        ('H', '974a'),
        ('J', 0x01E9D8, 2),
        ('H', '9762'),
        ('J', 0x01E9DC, 46),
        ('J', 0x00FBC6, 8),
    ]),
    (0x045C5E, [
        ('J', 0x045910, 66),
        ('H', 'eb38'),
        ('J', 0x045954, 84),
        ('H', 'a5f4'),
        ('J', 0x0459AA, 16),
        ('H', '0d50'),
        ('J', 0x0459BC, 16),
        ('H', '3ade'),
        ('J', 0x0459CE, 32),
        ('H', '3ae6'),
        ('J', 0x0459F0, 24),
        ('H', '3ade'),
        ('J', 0x045A0A, 28),
        ('H', '3b0a'),
        ('J', 0x045A28, 20),
        ('H', '3af2'),
        ('J', 0x045A3E, 44),
        ('H', '18b6'),
        ('J', 0x045A6C, 62),
        ('H', '3ad2'),
        ('J', 0x045AAC, 36),
        ('H', 'a5f4'),
        ('J', 0x045AD2, 16),
        ('H', '0d50'),
        ('J', 0x045AE4, 12),
        ('H', '3ae6'),
        ('J', 0x045AF2, 32),
        ('H', '3ade001b3ae6'),
        ('J', 0x045B18, 60),
        ('H', '3ade'),
        ('J', 0x045B56, 136),
        ('H', '57b4'),
        ('J', 0x045BE0, 6),
        ('H', '5a18'),
        ('J', 0x045BE8, 42),
        ('H', '58b4dc'),
        ('J', 0x045C15, 5),
        ('H', '59f4'),
        ('J', 0x045C1C, 118),
        ('H', '80a8'),
        ('J', 0x045C94, 2),
        ('H', '59f4'),
        ('J', 0x045C98, 2),
        ('H', '80e0'),
        ('J', 0x045C9C, 2),
        ('H', '5ac4'),
        ('J', 0x045CA0, 2),
        ('H', '58d4'),
        ('J', 0x045CA4, 2),
        ('H', '58b4'),
        ('J', 0x045CA8, 2),
        ('H', '5920'),
        ('J', 0x045CAC, 2),
        ('H', '5920'),
        ('J', 0x045CB0, 232),
        ('H', 'a5f4'),
        ('J', 0x045D9A, 12),
        ('H', '18b6'),
        ('J', 0x045DA8, 12),
        ('H', '0d50'),
        ('J', 0x045DB6, 66),
        ('H', '3c0a'),
        ('J', 0x045DFA, 20),
        ('H', '3c1e'),
        ('J', 0x045E10, 36),
        ('H', '3c02'),
        ('J', 0x045E36, 24),
        ('H', '3c2a'),
        ('J', 0x045E50, 32),
        ('H', '3c32'),
        ('J', 0x045E72, 2),
        ('H', '3c2a'),
        ('J', 0x045E76, 76),
        ('H', '3c2a'),
        ('J', 0x045EC4, 94),
        ('H', '3c46'),
        ('J', 0x045F24, 2),
        ('H', '3c3e'),
        ('J', 0x045F28, 24),
        ('J', 0x035852, 10),
        ('J', 0x045F4A, 40),
        ('H', '3c4e'),
        ('J', 0x045F74, 22),
        ('H', '3c66'),
        ('J', 0x045F8C, 10),
        ('J', 0x035852, 10),
        ('J', 0x045FA0, 24),
        ('J', 0x057BDE, 10),
        ('J', 0x057BDE, 10),
        ('J', 0x057BDE, 10),
        ('J', 0x057BDE, 10),
        ('J', 0x057BDE, 10),
        ('J', 0x057BDE, 10),
        ('J', 0x057BDE, 10),
        ('J', 0x057BDE, 10),
        ('J', 0x057BDE, 10),
        ('J', 0x057BDE, 10),
        ('J', 0x057BDE, 10),
        ('J', 0x057BDE, 10),
        ('J', 0x057BDE, 10),
        ('J', 0x057BDE, 10),
        ('J', 0x057BDE, 10),
        ('J', 0x057BDE, 10),
        ('J', 0x057BDE, 10),
        ('J', 0x057BDE, 10),
        ('J', 0x057BDE, 10),
        ('J', 0x057BDE, 10),
        ('J', 0x00FBC6, 8),
    ]),
    (0x1A1000, [
        ('J', 0x0CD442, 686),
        ('H', '001a12de001a12e0001a132a001a1374001a13b6001a1410001a1462001a149c001a14f6001a1530001a12de001a12de0000'),
        ('J', 0x0CB848, 642),
        ('H', '001a158e001a1590001a1602001a1604001a1606001a1608001a160a001a1614001a1616001a1620001a158e'),
        ('J', 0x0CBAF6, 2),
        ('J', 0x0CD6F0, 155),
        ('H', '1a1646001a1648001a164a001a166c001a167e001a1646'),
        ('J', 0x0621D4, 9),
        ('H', 'c8'),
        ('J', 0x0CDA8A, 60),
        ('H', '001a169c001a169c001a169e001a16f0001a169c'),
        ('J', 0x0CCEB2, 126),
        ('J', 0x00841C, 12),
        ('H', '4e75'),
    ]),
]
JP_HANDLERS = {0x504: 0x045C5E, 0x508: 0x045FFE, 0x50C: 0x046066, 0x79C: 0x046306}
JP_STAGE_LAYOUTS = {0x10: 0x1A12AE, 0x52: 0x1A1562, 0x56: 0x1A162A, 0x3A: 0x1A1688}
JP_LIST_6_1 = 0x1A1000
JP_CONTINUES_HELPER = 0x1A171A

JP_MD5 = 'cdb36911439289d3453060f58682057c'   # Dynamite Headdy (Japan)
JP_BLOCK_SHA1 = {0x01E96E: '150a5b4eaced76ef', 0x045C5E: 'e3009c6246174a85'}
HANDLERS = 0x0021D4              # code pointer per object type (long, type ID = offset)

# (US address, length, sha1 of the US bytes, JP value, what)
JP_PATCHES = [
    (0x0084C4, 10, '0373bf212baa', ('H', '4eb9001a171a4e714e71'), 'start with 2 continues (helper in free space)'),
    (0x020700, 2, 'eaba1526c0f4', ('J', 0x020448, 2), 'a continue every 10 tokens instead of 13'),
    (0x032C4E, 16, '28d30bc4b115', ('H', '526edf00026e0003df00661e4e714e71'), 'Stair Wars: fixed pattern (3 hooks, then an opening) instead of random'),
    (0x032DFD, 1, '8d883f1577ca', ('H', '04'), 'Stair Wars: 4 hits instead of 8'),
    (0x03A888, 2, 'a481f1a81cba', ('J', 0x03A566, 2), 'act 7 boss (second form): 9 hits instead of 17'),
    (0x000F93, 1, '511993d3c997', ('J', 0x000F97, 1), '9-3 boss: 9 hits instead of 17'),
    (0x00108F, 1, '511993d3c997', ('J', 0x001093, 1), '8-5 boss: 33 hits instead of 17'),
    (0x00182D, 1, '8d883f1577ca', ('J', 0x00182D, 1), '8-5 boss: hitbox 16 high instead of 8'),
    (0x00121B, 1, 'a9de501bd963', ('J', 0x00121F, 1), 'type $774 HP 140 instead of 134'),
    (0x000BD0, 2, '8bbf6f236fa1', ('J', 0x000BD4, 2), '1-1 boss energy balls: JP flags'),
    (0x001372, 1, 'a42c6cf1de3a', ('J', 0x001372, 1), '1-1 boss energy balls: damage 2 instead of 4'),
    (0x001696, 1, '1e32e3c36050', ('J', 0x001696, 1), '8-3 type $450: damage 8 instead of 12'),
    (0x0016A2, 1, '2d0134ed3b9d', ('J', 0x0016A2, 1), '8-3 type $45C: damage 2 instead of 6'),
    (0x0016C7, 1, 'bf8b4530d8d2', ('J', 0x0016C7, 1), 'score values (JP)'),
    (0x0016CB, 1, 'bf8b4530d8d2', ('J', 0x0016CB, 1), ''),
    (0x001747, 1, '5ba93c9db0cf', ('H', '03'), ''),
    (0x00182F, 1, '3ce0a1af90b6', ('J', 0x00182F, 1), ''),
    (0x001833, 1, '3ce0a1af90b6', ('J', 0x001833, 1), ''),
    (0x0018FF, 1, '8dc00598417d', ('J', 0x0018FF, 1), ''),
    (0x001907, 1, '8dc00598417d', ('J', 0x001907, 1), ''),
    (0x01D924, 2, 'b428cbaf48c7', ('H', '0060'), '1-1 boss: 96 frames between attacks instead of 64'),
    (0x01D940, 2, 'b428cbaf48c7', ('H', '0060'), ''),
    (0x01D970, 2, 'b428cbaf48c7', ('H', '0060'), ''),
    (0x01D98C, 2, 'b428cbaf48c7', ('H', '0060'), ''),
    (0x01D9A8, 2, 'b428cbaf48c7', ('H', '0060'), ''),
    (0x01D97A, 4, '90f2ef75f6eb', ('H', '4a78ee20'), '1-1 boss: waits for the event flag like JP'),
    (0x025A64, 4, '40b48b6cd230', ('H', '00018000'), 'homing object: 1.5 px/frame instead of 2'),
    (0x025A70, 4, 'ffa5207277b2', ('H', 'fffe8000'), ''),
    (0x025A86, 4, '40b48b6cd230', ('H', '00018000'), ''),
    (0x025A92, 4, 'ffa5207277b2', ('H', 'fffe8000'), ''),
    (0x03DF82, 2, 'd72d6bcdba5c', ('J', 0x03DC60, 2), 'timer step +1 instead of +4'),
    (0x0450F6, 2, 'f14919e3d5a9', ('J', 0x044DA8, 2), '9-3 boss: 96-frame interval instead of 60'),
    (0x05052E, 2, '8575c6036321', ('J', 0x050488, 2), 'flying enemy: 1 px steps instead of 2'),
    (0x050592, 2, '1844cc8a17e5', ('H', '536e'), ''),
    (0x0505AC, 2, '1844cc8a17e5', ('H', '536e'), ''),
    (0x0585F0, 2, 'a481f1a81cba', ('H', '0060'), 'wait timer 96 frames instead of 80'),
    (0x00F708, 4, '100e44df815d', ('H', '001a1000'), '6-1: JP enemy waves (1 shark, 2 Jayron waves)'),
    (0x00F720, 6, '2d4e0aa036e8', ('H', '0c7804a8e814'), '6-1: JP scroll trigger'),
    (0x00F74A, 2, '1a95536cfa43', ('H', '0900'), '6-1: JP stage length'),
    (0x05302A, 2, '4b69a33075f7', ('H', '0360'), '6-2: JP positions and speeds of 4 enemies'),
    (0x053052, 2, 'a08fd486bf5d', ('H', '04e0'), ''),
    (0x05307A, 2, 'a08fd486bf5d', ('H', '04e0'), ''),
    (0x05300E, 4, 'ffa5207277b2', ('H', 'ffff0000'), ''),
    (0x053036, 4, 'ffa5207277b2', ('H', 'ffff0000'), ''),
    (0x05305E, 4, 'ffa5207277b2', ('H', 'ffff0000'), ''),
    (0x053086, 4, 'ffa5207277b2', ('H', 'ffff0000'), ''),
    (0x00FBBA, 2, 'd7803a0f4d61', ('H', '0300'), '6-4: JP layout (objects 152 px further right)'),
    (0x053894, 2, '113af00f993b', ('J', 0x0537EC, 2), ''),
]


def jp_bytes(jp_rom, val):
    """A recipe value: ('J', JP address, length) copies from the JP ROM; ('H', hex) is our own."""
    return jp_rom[val[1]:val[1] + val[2]] if val[0] == 'J' else bytes.fromhex(val[1])


def check_jp_rom(jp_rom):
    if jp_rom is None:
        raise ValueError('JP balance and JP palettes need the Japanese ROM (Dynamite Headdy (Japan), '
                         'MD5 %s); pass it with --jp-rom' % JP_MD5)
    if hashlib.md5(bytes(jp_rom)).hexdigest() != JP_MD5:
        raise ValueError('the JP ROM is not Dynamite Headdy (Japan) (MD5 %s)' % JP_MD5)


def apply_jp_balance(rom, jp_rom):
    log = ['== JP balance']
    for a, ops in JP_BLOCKS:
        b = b''.join(jp_bytes(jp_rom, op) for op in ops)
        if a in JP_BLOCK_SHA1:
            if hashlib.sha1(bytes(rom[a:a + len(b)])).hexdigest()[:16] != JP_BLOCK_SHA1[a]:
                raise ValueError('code at $%06X is not the original US code' % a)
        else:
            claim(rom, a, len(b), 'JP balance data')
        rom[a:a + len(b)] = b
    for a, n, oldsum, val, what in JP_PATCHES:
        if hashlib.sha1(bytes(rom[a:a + n])).hexdigest()[:12] != oldsum:
            raise ValueError('unexpected bytes at $%06X (%s)' % (a, what or 'JP patch'))
        new = jp_bytes(jp_rom, val)
        rom[a:a + len(new)] = new
        if what:
            log.append(what)
    for t, h in JP_HANDLERS.items():
        rom[HANDLERS + t:HANDLERS + t + 4] = struct.pack('>I', h)
    log.append('1-1 boss energy balls and 9-3 objects $504/$508/$50C: JP code')
    for st, p in JP_STAGE_LAYOUTS.items():
        rom[STAGE_TABLE + st * 2:STAGE_TABLE + st * 2 + 4] = struct.pack('>I', p)
    log.append('JP object layouts for 3-1 (extra Headcase), 6-2, 6-4 and stage $3A')
    return log


# ---------------------------------------------------------------- main API

def normalize(opts):
    o = {k: v['default'] for k, v in OPTIONS.items()}
    for k, v in (opts or {}).items():
        if k not in OPTIONS:
            raise ValueError('unknown option %r' % k)
        if 'choices' in OPTIONS[k] and v not in OPTIONS[k]['choices']:
            raise ValueError('%s must be one of %s' % (k, OPTIONS[k]['choices']))
        o[k] = v
    if o['seed'] is None:
        o['seed'] = random.randrange(1 << 31)
    return o


def randomize(rom_in, opts=None, jp_rom=None):
    """Returns (randomized ROM bytes, spoiler log text)."""
    o = normalize(opts)
    rom = bytearray(rom_in)
    log = ['Dynamite Headdy randomizer - seed %d' % o['seed']]
    if hashlib.sha1(bytes(rom)).hexdigest() != US_SHA1:
        log.append('warning: not the known Dynamite Headdy (USA, Europe) ROM')
    # each feature gets its own random stream, so turning one feature on or
    # off doesn't change what the others do with the same seed
    def rng_for(name):
        return random.Random('%d:%s' % (o['seed'], name))
    if o['jp_balance'] or o['jp_palettes']:
        check_jp_rom(jp_rom)
    if o['jp_balance']:
        log += [''] + apply_jp_balance(rom, jp_rom)
    if o['headcases'] != 'off':
        if o['flying_heads']:
            log += [''] + patch_flying_heads(rom)
        log += [''] + randomize_headcases(rom, rng_for('headcases'), o)
    if o['jp_palettes']:
        apply_jp_palettes(rom, jp_rom)
        log += ['', '== JP palettes: %s' % ', '.join(map(str, JP_CHANGED))]
    if o['palettes'] != 'off':
        log += [''] + randomize_palettes(rom, rng_for('palettes'), o)
    if o['enemy_damage'] != 'off':
        log += [''] + randomize_stats(rom, rng_for('stats'), o)
    log += ['', 'checksum $%04X' % fix_checksum(rom)]
    return bytes(rom), '\n'.join(log) + '\n'


def main():
    ap = argparse.ArgumentParser(description='Dynamite Headdy (USA, Europe) randomizer')
    ap.add_argument('rom_in')
    ap.add_argument('rom_out')
    ap.add_argument('--jp-rom', help='Dynamite Headdy (Japan) ROM, needed for --jp-balance and --jp-palettes')
    for k, v in OPTIONS.items():
        flag = '--' + k.replace('_', '-')
        if v.get('type') == 'bool':
            ap.add_argument(flag, dest=k, action=argparse.BooleanOptionalAction,
                            default=v['default'], help=v['desc'])
        elif v.get('type') == 'int':
            ap.add_argument(flag, dest=k, type=int, default=v['default'], help=v['desc'])
        else:
            ap.add_argument(flag, dest=k, choices=v['choices'], default=v['default'],
                            help=v['desc'])
    args = ap.parse_args()
    opts = {k: getattr(args, k) for k in OPTIONS}
    jp = open(args.jp_rom, 'rb').read() if args.jp_rom else None
    rom, spoiler = randomize(open(args.rom_in, 'rb').read(), opts, jp)
    open(args.rom_out, 'wb').write(rom)
    open(args.rom_out + '.spoiler.txt', 'w').write(spoiler)
    print(spoiler.splitlines()[0] + ': wrote %s and %s.spoiler.txt' % (args.rom_out, args.rom_out))


if __name__ == '__main__':
    main()
