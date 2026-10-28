#!/usr/bin/env python3
"""Dynamite Headdy - flying-head test ROM.

Puts flying heads in EVERY Headcase so you can check where they cause trouble,
with the same A-to-drop / timeout patch as headdy_rando.py --flying-heads.

  python flying_test.py in.md out.md                  Rocket, Air and Feather in every Headcase
  python flying_test.py in.md out.md --head rocket    only one head (rocket, air, feather)
  python flying_test.py in.md out.md --no-liberty     also replace Liberty Head (no basketball)

Not changed: set 44 (the 6-1 Headcase, which starts the flight).
By default Liberty Head is kept, last in its set, so the basketball games
still work. The Headcases then cycle between flying heads and Liberty.

It writes out.md.headcases.txt: every Headcase, with its stage, position and
set, as a checklist. Sets used by several Headcases are listed together,
because blocking flying heads works per set.
"""
import argparse, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import headdy_rando as H

if not hasattr(H, 'patch_flying_heads'):
    sys.exit('Your headdy_rando.py is an older version. Get the latest one and put it '
             'in the same folder as flying_test.py.')

HEADS = {'rocket': 0x220, 'air': 0x240, 'feather': 0x260}


def main():
    ap = argparse.ArgumentParser(description='Flying heads in every Headcase (test ROM)')
    ap.add_argument('rom_in')
    ap.add_argument('rom_out')
    ap.add_argument('--head', choices=sorted(HEADS), help='use only this flying head')
    ap.add_argument('--no-liberty', action='store_true', help='replace Liberty Head too')
    args = ap.parse_args()

    rom = bytearray(open(args.rom_in, 'rb').read())
    heads = [HEADS[args.head]] if args.head else list(H.FLYING)
    H.patch_flying_heads(rom)

    users = {}
    for st, x, e in H.find_headcases(rom):
        k = rom[e + 5] & 0x7F
        users.setdefault(k, []).append('%s X=%d' % (H.STAGE_NAMES.get(st, '$%02X' % st), x))
    for k, u in H.RUNTIME_USERS.items():
        users.setdefault(k, []).extend(u)

    lines = ['Flying-head test ROM: %s in every Headcase (A drops them, they time out'
             ' like other heads)' % ', '.join(map(H.nm, heads)),
             'Liberty Head %s. Set 44 (6-1) unchanged.' % (
                 'replaced' if args.no_liberty else 'kept'), '',
             'set  original heads              -> now                         used by']
    for k in range(H.NUM_SETS):
        old = H.read_set(rom, k)
        if k == 44 or not old:
            continue
        size = len(old)
        keep_lib = H.LIBERTY in old and not args.no_liberty
        new = (heads * 3)[:size - 1 if keep_lib else size]
        if keep_lib:
            new = new + [H.LIBERTY]          # Liberty must stay last
        for i, h in enumerate(new + [0] * (3 - len(new))):
            H.put16(rom, H.SET_TABLE + 6 * k + 2 * i, h)
        lines.append('[ ] %2d  %-28s -> %-28s %s' % (
            k, ', '.join(map(H.nm, old)), ', '.join(map(H.nm, new)),
            '; '.join(users.get(k, ['(no Headcase uses it)']))))
    cs = H.fix_checksum(rom)
    open(args.rom_out, 'wb').write(rom)
    open(args.rom_out + '.headcases.txt', 'w').write('\n'.join(lines) + '\n\nchecksum $%04X\n' % cs)
    print('wrote %s and %s.headcases.txt' % (args.rom_out, args.rom_out))


if __name__ == '__main__':
    main()
