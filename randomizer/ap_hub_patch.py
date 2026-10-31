#!/usr/bin/env python3
"""Dynamite Headdy (USA, Europe) - stage-select hub patch (Archipelago groundwork).

What it does:
  1. Pressing Start on the title screen always opens the stage select
     (the menu the RE3T-C6W6 Game Genie code unlocks).
  2. Stages can be locked. Left/Right skips locked entries and Start does
     nothing on a locked one. The unlock mask is a long word in RAM.
  3. When an act is finished and the game would load the NEXT stage of the
     stage-select list, it marks the act as cleared and returns to the title
     instead. Press Start there to get back to the stage select.
     Retries of the same stage, sub-areas (tutorial rooms, minigames) and the
     ending are not affected.
  4. Every Secret Bonus Point collected sets its own bit in RAM, so a client
     can tell exactly which ones were taken. The game's bonus routine at
     $00A610 is entered with d0 = 2 x bonus ID; its first instruction is
     replaced by TRAP #15, whose vector (unused, pointed at reset) now leads
     to a handler that does the original work and sets the bit.
  5. Under the stage number, the stage select shows the stage under the cursor:
     "CLEAR" / "NOT CLEAR", "BONUS n OF m" (its Secret Bonus Points) and, when the
     Archipelago client says pickupsanity is on, "PICKUPS nn OF mm"; then the code
     digits and "nn OF 39 SBPS" (bits set in the bonus mask; SBP_TOTAL = 39).
  6. Basketball progress persists: the title screen no longer wipes the
     secret-door digits ($FFE9C4-CA) and basketball stages ($FFE9B0), and a
     copy is kept in the reset-proof area and restored when a stage is started
     from the hub (soft reset clears game RAM). The hub shows "CODE 37--".
     Only WON games' stages are kept: the game marks a stage done when you
     enter its basketball game, so a failed game's Liberty Head returns the
     next time that stage is started from the hub.

RAM used (unused by the game; this area survives soft resets):
  $FFFFE4.l  unlock mask   bit n = stage select entry n (0-29) is selectable
  $FFFFE8.l  cleared mask  bit n = entry n's act was finished (n 1-29; 9-3 = bit 29
                           is set when the game moves on to the ending);
                           bit 30 = secret boss beaten (leaving stage $38)
  $FFFFEC.w  stage started from the hub (stage ID)
  $FFFFEE.b  1 = a stage was just started from the hub
  $FFFFEF.b  frames until the stage select redraws the stage number
  $FFFFF0.w  $4150 ('AP') once the variables are initialised
  $FFFFF2-F9 bonus mask    bit n of byte n/8 = Secret Bonus Point n taken
             (n = bonus ID 0-39, or 40+ for points that share an ID, see BONUS_REMAP)
  $FFFFE2.b  basketball stages WON (restored into $FFE9B0)
  $FFFFE3.b  stage loaded last time
  $FFFFF8.w  backup of the 4 secret-door digits, one nibble each, $F = unknown
  $FFFFFA.b  slot of the object that gave the last bonus point
  $FFFFFB.b  game ID of the last bonus point
  $FFFFFE.b  Archipelago DeathLink: the client sets it to 1 to make Headdy die
  $FFFFE0.b  Archipelago trap: the client sets it (1 Mean Bean, 2 Head Trip), the hub
             clears it once the trap has happened
On first use every entry except 0-1 is unlocked (standalone play). 0-1 (the
opening) is never selectable.
An Archipelago client would overwrite it with the stages the player owns.

Stage select entries (n: act, stage ID):
   0 opening $3C   1 1-1 $00   2 2-1 $0C   3 2-2 $02   4 2-3 $06
   5 3-1 $10       6 3-2 $12   7 3-3 $32   8 3-4 $14   9 4-1 $04
  10 4-2 $16      11 4-3 $18  12 4-4 $34  13 5-1 $36  14 5-2 $1A
  15 5-3 $1C      16 5-4 $1E  17 6-1 $50  18 6-2 $52  19 6-3 $54
  20 6-4 $56      21 7   $20  22 8-1 $22  23 8-2 $24  24 8-3 $26
  25 8-4 $28      26 8-5 $2A  27 9-1 $2C  28 9-2 $2E  29 9-3 $30

usage: python3 ap_hub_patch.py in.bin out.bin [--start-locked]
  --start-locked  first use unlocks only 1-1 instead of everything
"""
import hashlib, struct, sys

US_SHA1 = 'e843decdff262791b1237f1545f5b17c56712d5f'
CODE_BASE = 0x1A0900          # free space ($FF fill) outside the checksum area

# RAM (absolute short addresses, sign-extended to $FFFFxxxx)
UNLOCK, CLEARED, HUBSTAGE, HUBFLAG, MAGIC, REDRAW = 0xFFE4, 0xFFE8, 0xFFEC, 0xFFEE, 0xFFF0, 0xFFEF
BONUS = 0xFFF2                # 8 bytes, $FFF2-$FFF9
LAST_SLOT, LAST_ID = 0xFFFA, 0xFFFB   # last bonus award (for logging tools)
BB_STAGES = 0xFFE2            # backup of $FFE9B0 (basketball stages done)
LASTSTAGE = 0xFFE3            # stage loaded last time (to spot leaving the secret boss)
STAGE_9_3 = 0x30              # last act; it's followed by the ending (credits, door room $4C)
SECRET_BOSS, CONTINUE = 0x38, 0x3A     # secret boss stage (no lives lost there); continue stage
BIT_9_3, BIT_SECRET = 29, 30           # bits in the cleared mask
ITEMS_RECEIVED = 0xFFFC       # word: items the AP client has applied (survives soft reset)
DEATH_REQ = 0xFFFE            # byte: set by the AP client to kill Headdy (DeathLink)
TRAP_REQ = 0xFFE0             # byte: trap from the AP client (1 Mean Bean, 2 Head Trip)
MODE_TABLE = 0x0004C2         # game mode handlers (long each, mode = offset)
PLAY_MODE, PLAY_HANDLER = 0x20, 0x0144D8
KILL = 0x010B0E               # the game's own "Headdy dies" routine (pits call it too)
HEAD_RESET = 0x011366         # Headcase pickup, step 1: reset the head's settings
HEAD_SETUP = 0x011312         # Headcase pickup, step 2: setup routine per head (long, head/8)
NO_DEATH_STAGES = (0x08, 0x0A, 0x44)   # tutorial rooms and basketball: no dying there
HEAD_TRIP = 0x1A0
# A Head Trip trap waits while Headdy wears one of these: Ticker (time stop), Liberty
# (basketball), Empty, Pin (lasts until dropped some other way, like the flying heads),
# Bomb (act 7 boss) and the flying heads; and in act 6 (flying).
TRAP_WAIT_HEADS = (0x060, 0x0C0, 0x0E0, 0x100, 0x120, 0x220, 0x240, 0x260)
TRAP_WAIT_STAGES = NO_DEATH_STAGES + (0x50, 0x52, 0x54, 0x56)
BB_DIGITS = 0xFFF8            # backup of the 4 secret digits, one nibble each ($F = unknown)
E8F6 = 0xE8F6                 # bonus points taken in the current scene (game's own)
E8AA, E8C4, E80A, E80B, E806, E8FE = 0xE8AA, 0xE8C4, 0xE80A, 0xE80B, 0xE806, 0xE8FE
STAGE_LIST = 0x006786
SOUND = 0x0118B6
TO_TITLE = 0x0146F0
DEMO_RET = 0x013150           # return address when the title's idle timer starts the demo
DEMO_MODE = 0x28              # game mode while the demo's stage loads
SS_INIT = 0x013428            # original stage select setup (ends with rts)
SS_REDRAW = 0x01359C          # draws the stage number for the cursor (ends with rts)
TEXT_DRAW = 0x01232C          # queue a text block (a0) for drawing; returns a2 = end of queued line
TEXT_ERASE = 0x01231C         # queue the same block as blanks
SBP_TOTAL = 39                # total shown on the stage select ("12 OF 39 SBPS")
INFO_ROW = 0x509E             # screen address: 2 rows under the stage number
SBP_ROW = INFO_ROW + 6 * 0x80                 # total bonus points, 6 rows down
CODE_ROW = INFO_ROW + 4 * 0x80 + 4            # code digits, 4 rows down (2 cells right)
# Stage info for the entry under the cursor, every other row like the game's own lines:
#   row 0: "NOT CLEAR" / "CLEAR" and "BONUS n OF m"; row 2: "PICKUPS nn OF mm" (only when the
#   Archipelago client has set PU_FLAG, i.e. pickupsanity; the client keeps PICKUP_MASK)
INFO_BASE = 0x1A1800          # free space (after the JP layouts, before the flying-head fix)
PICKUP_MASK = 0xFF90          # 12 bytes: bit i (byte i/8, bit i%8) = pickup check i done
PU_FLAG = 0xFF9C              # byte: 1 = show the pickups line
# ($FF80-$FFB7 is untouched by the game, and soft resets only clear RAM up to $FFFEFF)
STAGE_NUMBERS = ['1-1', '2-1', '2-2', '2-3', '3-1', '3-2', '3-3', '3-4', '4-1', '4-2', '4-3',
                 '4-4', '5-1', '5-2', '5-3', '5-4', '6-1', '6-2', '6-3', '6-4', '7', '8-1',
                 '8-2', '8-3', '8-4', '8-5', '9-1', '9-2', '9-3']   # entries 1-29
# Bonus point bits recorded for each act (the client's BONUS_POINTS, by act)
ACT_BONUS_BITS = {'1-1': [0], '2-1': [7, 40, 41], '2-2': [1, 13, 10, 42], '2-3': [2], '3-1': [11],
                  '3-2': [12], '3-3': [39], '3-4': [14], '4-1': [15, 3, 16], '4-2': [17],
                  '4-3': [18, 43], '4-4': [19], '5-2': [21], '5-3': [22], '5-4': [23],
                  '6-1': [35, 36], '6-4': [37], '7': [25, 4, 26], '8-1': [27], '8-2': [28],
                  '8-3': [29, 6], '8-4': [30], '8-5': [5], '9-1': [31, 38], '9-2': [33], '9-3': [34]}
# Pickup checks of each act: (first index, count) in the client's PICKUP_SPOTS order
ACT_PICKUPS = {'2-2': (0, 18), '3-1': (18, 5), '4-1': (23, 17), '4-2': (40, 7), '4-3': (47, 5),
               '5-3': (52, 1), '6-2': (53, 1), '6-3': (54, 1), '8-1': (55, 7), '8-3': (62, 16),
               '9-1': (78, 7), '9-2': (85, 1)}

# Bonus points that share an ID with another one get their own bit.
# (stage ID, bonus ID, object slot or -1 for any, bit to record)
ANY = -1
BONUS_REMAP = [
    # 2-1's three tutorial doors lead to $08 (Headcase), $0A (Hangman) and
    # $0E (Beau). Each room sets its own bit in $FFE918, then all three award
    # ID 7 from the same routine ($02460C).
    (0x0A, 7, ANY, 40),       # Hangman tutorial
    (0x0E, 7, ANY, 41),       # Beau tutorial
    # 2-2: two neighbouring enemies run the same code and both award ID 10
    # (types $078 at X=3144 and $070 at X=3168). The second one's point comes
    # from object slot $60 (seen in play); the first keeps bit 10.
    (0x02, 10, 0x60, 42),
    # 4-3: two objects award ID 18, from slots $9C (keeps bit 18) and $A0.
    (0x18, 18, 0xA0, 43),
]


def text_bytes(txt):
    out = bytearray()
    for ch in txt:
        if ch == ' ':
            out.append(0xC0)
        elif ch.isdigit():
            out.append(0xC1 + int(ch))
        elif ch == '-':
            out.append(0xE5)
        else:
            out.append(0xCB + ord(ch) - ord('A'))
    return bytes(out)


class Asm:
    """Tiny assembler: raw words, labels and branches with fixups."""
    def __init__(self, base):
        self.base, self.code, self.labels, self.fix = base, bytearray(), {}, []

    def here(self):
        return self.base + len(self.code)

    def label(self, name):
        self.labels[name] = self.here()

    def w(self, *words):
        for x in words:
            self.code += struct.pack('>H', x & 0xFFFF)

    def l(self, x):
        self.code += struct.pack('>I', x & 0xFFFFFFFF)

    def br(self, op, name):          # 16-bit displacement branch: Bcc.w / BSR.w / DBcc
        self.w(op)
        self.fix.append((len(self.code), name))
        self.w(0)

    def done(self):
        for off, name in self.fix:
            disp = self.labels[name] - (self.base + off)
            assert -0x8000 <= disp < 0x8000
            self.code[off:off + 2] = struct.pack('>h', disp)
        return bytes(self.code)


def text_block(addr, txt):
    b = struct.pack('>HH', addr, 0x4600) + text_bytes(txt) + b'\xFF'
    return b + (b'\xFF' if len(b) % 2 else b'')


def line_addr(row, n):
    """Screen address of an n-character line centred like the 13-character SBP line."""
    return INFO_ROW + row * 0x80 + 2 * ((13 - n) // 2)


def build_info():
    """Stage info lines for the entry under the cursor (code and tables at INFO_BASE)."""
    BEQ, BNE, BRA = 0x6700, 0x6600, 0x6000
    i = Asm(INFO_BASE)
    # info_clear: "NOT CLEAR" / "  CLEAR  " from the cleared mask
    i.label('info_clear')
    i.w(0x3038, E8C4)                           # move.w cursor,d0
    i.w(0xE248)                                 # lsr.w #1,d0      entry
    i.w(0x2238, CLEARED)                        # move.l CLEARED,d1
    i.w(0x0101)                                 # btst d0,d1
    i.br(BEQ, 'ic_not')
    i.w(0x41F9); i.l(0); i.label('ref_clear')   # lea txt_clear,a0
    i.br(BRA, 'ic_draw')
    i.label('ic_not')
    i.w(0x41F9); i.l(0); i.label('ref_notclear')
    i.label('ic_draw')
    i.w(0x4EF9); i.l(TEXT_DRAW)                 # jmp draw text
    # info_bonus: "BONUS n OF m" from the act's list of bonus bits
    i.label('info_bonus')
    i.w(0x3038, E8C4)                           # move.w cursor,d0 (entry*2)
    i.w(0x43F9); i.l(0); i.label('ref_bidx')    # lea bonus_index,a1
    i.w(0x3231, 0x0000)                         # move.w 0(a1,d0.w),d1
    i.w(0x43F9); i.l(0); i.label('ref_blist')   # lea bonus_lists,a1
    i.w(0xD2C1)                                 # adda.w d1,a1
    i.w(0x7400, 0x1419)                         # moveq #0,d2 / move.b (a1)+,d2   total
    i.br(BEQ, 'ib_blank')
    i.w(0x7600, 0x3802, 0x5344)                 # moveq #0,d3 / move.w d2,d4 / subq.w #1,d4
    i.w(0x41F8, BONUS)                          # lea BONUS,a0
    i.label('ib_loop')
    i.w(0x7200, 0x1219)                         # moveq #0,d1 / move.b (a1)+,d1
    i.w(0x3A01, 0xE64D)                         # move.w d1,d5 / lsr.w #3,d5
    i.w(0x0330, 0x5000)                         # btst d1,0(a0,d5.w)
    i.w(0x6702, 0x5243)                         # beq.s +2 / addq.w #1,d3
    i.br(0x51CC, 'ib_loop')                     # dbra d4,ib_loop
    i.w(0x48E7, 0x3000)                         # movem.l d2-d3,-(sp)
    i.w(0x41F9); i.l(0); i.label('ref_bonus')   # lea txt_bonus,a0
    i.w(0x4EB9); i.l(TEXT_DRAW)
    i.w(0x4CDF, 0x000C)                         # movem.l (sp)+,d2-d3
    i.w(0x0643, 0x46C1, 0x3543, (-12) & 0xFFFF) # taken: addi.w #$46C1,d3 / move.w d3,-12(a2)
    i.w(0x0642, 0x46C1, 0x3542, (-2) & 0xFFFF)  # total: addi.w #$46C1,d2 / move.w d2,-2(a2)
    i.w(0x4E75)
    i.label('ib_blank')
    i.w(0x41F9); i.l(0); i.label('ref_bblank')
    i.w(0x4EF9); i.l(TEXT_DRAW)
    # info_pickups: "PICKUPS nn OF mm" from PICKUP_MASK (only with PU_FLAG)
    i.label('info_pickups')
    i.w(0x4A38, PU_FLAG)                        # tst.b PU_FLAG
    i.br(BEQ, 'ip_blank')
    i.w(0x3038, E8C4)                           # move.w cursor,d0
    i.w(0x43F9); i.l(0); i.label('ref_pidx')    # lea pickup_index,a1
    i.w(0x3231, 0x0000)                         # move.w 0(a1,d0.w),d1   start<<8 | count
    i.w(0x7400, 0x1401)                         # moveq #0,d2 / move.b d1,d2   total
    i.br(BEQ, 'ip_blank')
    i.w(0xE049)                                 # lsr.w #8,d1   first index
    i.w(0x7600, 0x3802, 0x5344)                 # moveq #0,d3 / move.w d2,d4 / subq.w #1,d4
    i.w(0x41F8, PICKUP_MASK)                    # lea PICKUP_MASK,a0
    i.label('ip_loop')
    i.w(0x3A01, 0xE64D)                         # move.w d1,d5 / lsr.w #3,d5
    i.w(0x0330, 0x5000)                         # btst d1,0(a0,d5.w)
    i.w(0x6702, 0x5243)                         # beq.s +2 / addq.w #1,d3
    i.w(0x5241)                                 # addq.w #1,d1
    i.br(0x51CC, 'ip_loop')                     # dbra d4,ip_loop
    i.w(0x48E7, 0x3000)                         # movem.l d2-d3,-(sp)
    i.w(0x41F9); i.l(0); i.label('ref_pick')
    i.w(0x4EB9); i.l(TEXT_DRAW)
    i.w(0x4CDF, 0x000C)                         # movem.l (sp)+,d2-d3
    for reg, at in ((3, -16), (2, -4)):         # taken (cells 8-9), total (cells 14-15)
        i.w(0x80FC | (reg << 9), 0x000A)        # divu #10,dN
        i.w(0x0640 | reg, 0x46C1)               # addi.w #$46C1,dN   tens
        i.w(0x3540 | reg, at & 0xFFFF)          # move.w dN,at(a2)
        i.w(0x4840 | reg)                       # swap dN            ones
        i.w(0x0640 | reg, 0x46C1)
        i.w(0x3540 | reg, (at + 2) & 0xFFFF)
    i.w(0x4E75)
    i.label('ip_blank')
    i.w(0x41F9); i.l(0); i.label('ref_pblank')
    i.w(0x4EF9); i.l(TEXT_DRAW)
    # tables: per entry (word each, entries 0-29)
    i.label('bonus_index')
    lists = bytearray()
    for e in range(30):
        bits = ACT_BONUS_BITS.get(STAGE_NUMBERS[e - 1], []) if e else []
        i.w(len(lists))
        lists += bytes([len(bits)] + bits)
    i.label('pickup_index')
    for e in range(30):
        start, n = ACT_PICKUPS.get(STAGE_NUMBERS[e - 1], (0, 0)) if e else (0, 0)
        i.w(start << 8 | n)
    i.label('bonus_lists')
    i.code += lists + (b'\xFF' if len(lists) % 2 else b'')
    # row 0 holds "NOT CLEAR  BONUS 0 OF 0" (23 characters) as two blocks
    left = INFO_ROW + 2 * ((13 - 23) // 2)
    texts = {'txt_clear': (left, '  CLEAR  '), 'txt_notclear': (left, 'NOT CLEAR'),
             'txt_bonus': (left + 22, 'BONUS 0 OF 0'), 'txt_bblank': (left + 22, ' ' * 12),
             'txt_pickups': (line_addr(2, 16), 'PICKUPS 00 OF 00'),
             'txt_pblank': (line_addr(2, 16), ' ' * 16)}
    for name, (addr, txt) in texts.items():
        i.label(name)
        i.code += text_block(addr, txt)
    code = bytearray(i.done())
    for ref, target in (('ref_clear', 'txt_clear'), ('ref_notclear', 'txt_notclear'),
                        ('ref_bidx', 'bonus_index'), ('ref_blist', 'bonus_lists'),
                        ('ref_bonus', 'txt_bonus'), ('ref_bblank', 'txt_bblank'),
                        ('ref_pidx', 'pickup_index'), ('ref_pick', 'txt_pickups'),
                        ('ref_pblank', 'txt_pblank')):
        o = i.labels[ref] - INFO_BASE - 4
        code[o:o + 4] = struct.pack('>I', i.labels[target])
    return bytes(code), i.labels


INFO_CODE, INFO = build_info()


def build(ap=False):
    a = Asm(CODE_BASE)
    BEQ, BNE, BRA, BSR, BPL, BMI, DBRA_D1, DBRA_D2 = 0x6700, 0x6600, 0x6000, 0x6100, 0x6A00, 0x6B00, 0x51C9, 0x51CA

    # ensure_init: set up the variables once
    a.label('ensure_init')
    a.w(0x0C78, 0x4150, MAGIC)                  # cmpi.w #'AP',MAGIC
    a.br(BEQ, 'ei_ok')
    a.w(0x21FC); a.l(0); a.w(UNLOCK)            # move.l #mask,UNLOCK (patched below)
    a.label('default_mask_imm')
    a.w(0x42B8, CLEARED)                        # clr.l CLEARED
    a.w(0x4278, HUBSTAGE)                       # clr.w HUBSTAGE
    a.w(0x4238, HUBFLAG)                        # clr.b HUBFLAG
    a.w(0x42B8, BONUS)                          # clr.l BONUS
    a.w(0x4278, BONUS + 4)                      # clr.w BONUS+4 (bits 32-47)
    a.w(0x4238, BB_STAGES)                      # clr.b BB_STAGES
    a.w(0x4238, LASTSTAGE)                      # clr.b LASTSTAGE
    a.w(0x31FC, 0xFFFF, BB_DIGITS)              # move.w #$FFFF,BB_DIGITS (no digits yet)
    a.w(0x4278, ITEMS_RECEIVED)                 # clr.w ITEMS_RECEIVED (client's counter)
    a.w(0x4238, DEATH_REQ)                      # clr.b DEATH_REQ
    a.w(0x4238, TRAP_REQ)                       # clr.b TRAP_REQ
    a.w(0x31FC, 0x4150, MAGIC)                  # move.w #'AP',MAGIC
    a.label('ei_ok')
    a.w(0x4E75)                                 # rts

    # is_unlocked: d0 = entry*2 -> Z clear if unlocked (uses d1,d3)
    a.label('is_unlocked')
    a.w(0x3200)                                 # move.w d0,d1
    a.w(0xE249)                                 # lsr.w #1,d1
    a.w(0x2638, UNLOCK)                         # move.l UNLOCK,d3
    a.w(0x0283); a.l(0x3FFFFFFE)                # andi.l #$3FFFFFFE,d3 (0-1 never selectable)
    a.w(0x0303)                                 # btst d1,d3
    a.w(0x4E75)                                 # rts

    # ss_move: called after Left/Right moved the cursor; skip locked entries
    a.label('ss_move')
    a.br(BSR, 'ensure_init')
    a.w(0x3038, E8C4)                           # move.w cursor,d0
    a.w(0x741D)                                 # moveq #29,d2
    a.w(0x0838, 0x0002, E80A)                   # btst #2,held   (Left)
    a.br(BNE, 'mv_back')
    a.w(0x0838, 0x0002, E80B)                   # btst #2,pressed (Left)
    a.br(BNE, 'mv_back')
    a.label('mv_fwd')
    a.br(BSR, 'is_unlocked')
    a.br(BNE, 'mv_done')
    a.w(0x5440)                                 # addq.w #2,d0
    a.w(0x0C40, 0x003C)                         # cmpi.w #$3C,d0
    a.br(BNE, 'mv_f1')
    a.w(0x7000)                                 # moveq #0,d0
    a.label('mv_f1')
    a.br(DBRA_D2, 'mv_fwd')
    a.br(BRA, 'mv_done')
    a.label('mv_back')
    a.br(BSR, 'is_unlocked')
    a.br(BNE, 'mv_done')
    a.w(0x5540)                                 # subq.w #2,d0
    a.br(BPL, 'mv_b1')
    a.w(0x703A)                                 # moveq #$3A,d0
    a.label('mv_b1')
    a.br(DBRA_D2, 'mv_back')
    a.label('mv_done')
    a.w(0x31C0, E8C4)                           # move.w d0,cursor
    a.w(0x11FC, 0x0006, REDRAW)                 # move.b #6,REDRAW (this stage's info lines)
    a.w(0x103C, 0x00AD)                         # move.b #$AD,d0   (original code)
    a.w(0x4EF9); a.l(SOUND)                     # jmp sound        (its rts returns to the menu)

    # ss_start: Start pressed in the stage select
    a.label('ss_start')
    # The title's idle timer starts the demo through this same code ($01314C: bsr $0134CC,
    # return address $013150): do exactly what the original does then.
    a.w(0x0CAF); a.l(DEMO_RET); a.w(0x0004)     # cmpi.l #$13150,4(sp)
    a.br(BNE, 'st_menu')
    a.w(0x3038, E8C4)                           # move.w cursor,d0 (original code)
    a.w(0x41F9); a.l(STAGE_LIST)                # lea stage list,a0 (original code)
    a.w(0x4E75)                                 # rts
    a.label('st_menu')
    a.br(BSR, 'ensure_init')
    a.w(0x3038, E8C4)                           # move.w cursor,d0
    a.br(BSR, 'is_unlocked')
    a.br(BEQ, 'st_locked')
    a.w(0x11FC, 0x0001, HUBFLAG)                # move.b #1,HUBFLAG
    a.w(0x41F9); a.l(STAGE_LIST)                # lea stage list,a0 (original code)
    a.w(0x4E75)                                 # rts -> original code loads the stage
    a.label('st_locked')
    a.w(0x588F)                                 # addq.l #4,sp
    a.w(0x4E75)                                 # rts (= ignore Start this frame)

    # hub_stage_load: start of stage loading (mode $1C, step 0)
    a.label('hub_stage_load')
    a.w(0x0C78, DEMO_MODE, 0xE802)              # cmpi.w #$28,$E802 (loading the title demo)
    a.br(BEQ, 'hl_cont')                        #  -> not a real stage: leave it alone
    a.br(BSR, 'ensure_init')
    a.w(0x3038, 0xE8C2)                         # move.w $E8C2,d0  (the stage the loader will actually use)
    a.w(0x1838, LASTSTAGE)                      # move.b LASTSTAGE,d4  previous stage
    a.w(0x11C0, LASTSTAGE)                      # move.b d0,LASTSTAGE
    a.w(0x4A38, HUBFLAG)                        # tst.b HUBFLAG
    a.br(BEQ, 'hl_notfresh')
    a.w(0x4238, HUBFLAG)                        # clr.b HUBFLAG
    a.w(0x31C0, HUBSTAGE)                       # move.w d0,HUBSTAGE
    a.br(BSR, 'restore_bb')                     # basketball progress back into the game
    a.br(BRA, 'hl_cont')
    a.label('hl_notfresh')
    a.br(BSR, 'save_bb')                        # keep a copy of basketball progress
    a.w(0x3038, 0xE8C2)                         # move.w $E8C2,d0 (save_bb used d0)
    # 9-3 finished: 9-3 was started from the hub and the game moves on to
    # anything but a 9-3 retry or the continue screen (i.e. the ending).
    # Mark 9-3 cleared; the ending stages aren't menu stages, so play goes on.
    a.w(0x0C78, STAGE_9_3, HUBSTAGE)            # cmpi.w #$30,HUBSTAGE
    a.br(BNE, 'hl_n1')
    a.w(0x0C40, STAGE_9_3)                      # cmpi.w #$30,d0
    a.br(BEQ, 'hl_n1')
    a.w(0x0C40, CONTINUE)                       # cmpi.w #$3A,d0
    a.br(BEQ, 'hl_n1')
    a.w(0x2638, CLEARED)                        # move.l CLEARED,d3
    a.w(0x08C3, BIT_9_3)                        # bset #29,d3
    a.w(0x21C3, CLEARED)                        # move.l d3,CLEARED
    a.label('hl_n1')
    # leaving the secret boss stage = boss beaten (no lives are lost there, so
    # dying just reloads it)
    a.w(0x0C04, SECRET_BOSS)                    # cmpi.b #$38,d4  (previous stage)
    a.br(BNE, 'hl_n2')
    a.w(0x0C40, SECRET_BOSS)                    # cmpi.w #$38,d0
    a.br(BEQ, 'hl_n2')
    a.w(0x2638, CLEARED)                        # move.l CLEARED,d3
    a.w(0x08C3, BIT_SECRET)                     # bset #30,d3
    a.w(0x21C3, CLEARED)                        # move.l d3,CLEARED
    a.label('hl_n2')
    a.w(0xB078, HUBSTAGE)                       # cmp.w HUBSTAGE,d0
    a.br(BEQ, 'hl_cont')                        # retry of the same stage
    a.w(0x41F9); a.l(STAGE_LIST)                # lea list,a0
    a.w(0x721D)                                 # moveq #29,d1
    a.label('hl_scan')
    a.w(0xB058)                                 # cmp.w (a0)+,d0
    a.br(BEQ, 'hl_inmenu')
    a.br(DBRA_D1, 'hl_scan')
    a.br(BRA, 'hl_cont')                        # sub-area / ending: carry on
    a.label('hl_inmenu')
    a.w(0x3038, HUBSTAGE)                       # move.w HUBSTAGE,d0
    a.w(0x41F9); a.l(STAGE_LIST)                # lea list,a0
    a.w(0x721D)                                 # moveq #29,d1
    a.w(0x7400)                                 # moveq #0,d2
    a.label('hl_scan2')
    a.w(0xB058)                                 # cmp.w (a0)+,d0
    a.br(BEQ, 'hl_found')
    a.w(0x5242)                                 # addq.w #1,d2
    a.br(DBRA_D1, 'hl_scan2')
    a.br(BRA, 'hl_tohub')
    a.label('hl_found')
    a.w(0x2638, CLEARED)                        # move.l CLEARED,d3
    a.w(0x05C3)                                 # bset d2,d3
    a.w(0x21C3, CLEARED)                        # move.l d3,CLEARED
    a.label('hl_tohub')
    a.w(0x588F)                                 # addq.l #4,sp
    a.w(0x4EF9); a.l(TO_TITLE)                  # jmp to-title routine (ends with rts)
    a.label('hl_cont')
    a.w(0x31FC, 0x0001, E806)                   # move.w #1,$E806 (original code)
    a.w(0x4E75)                                 # rts

    # ss_enter: title Start -> stage select, cursor on the first unlocked entry
    a.label('ss_enter')
    a.br(BSR, 'ensure_init')
    a.w(0x4EB9); a.l(SS_INIT)                   # jsr original stage select init
    a.w(0x7000)                                 # moveq #0,d0
    a.w(0x741D)                                 # moveq #29,d2
    a.label('en_scan')
    a.br(BSR, 'is_unlocked')
    a.br(BNE, 'en_done')
    a.w(0x5440)                                 # addq.w #2,d0
    a.br(DBRA_D2, 'en_scan')
    a.w(0x7000)                                 # moveq #0,d0 (nothing unlocked)
    a.label('en_done')
    a.w(0x31C0, E8C4)                           # move.w d0,cursor
    a.w(0x11FC, 0x0006, REDRAW)                 # move.b #6,REDRAW (redraw in a few frames)
    a.w(0x4E75)                                 # rts

    # ss_frame: start of every stage select frame (replaces btst #4,$E80B)
    # REDRAW counts down: at 1 redraw the stage number, at 0 draw the SBP line
    a.label('ss_frame')
    a.w(0x4A38, REDRAW)                         # tst.b REDRAW
    a.br(BEQ, 'fr_x')
    a.w(0x5338, REDRAW)                         # subq.b #1,REDRAW
    a.br(BEQ, 'fr_code')
    a.w(0x0C38, 0x0001, REDRAW)                 # cmpi.b #1,REDRAW
    a.br(BEQ, 'fr_sbp')
    for n, routine in ((3, 'info_pickups'), (4, 'info_bonus'), (5, 'info_clear')):
        a.w(0x0C38, n, REDRAW)                  # cmpi.b #n,REDRAW
        a.br(BNE, 'fr_not%d' % n)
        a.w(0x4EB9); a.l(INFO[routine])         # jsr stage info line
        a.br(BRA, 'fr_x')
        a.label('fr_not%d' % n)
    a.w(0x0C38, 0x0002, REDRAW)                 # cmpi.b #2,REDRAW
    a.br(BNE, 'fr_x')
    a.w(0x4EB9); a.l(SS_REDRAW)                 # jsr redraw stage number
    a.br(BRA, 'fr_x')
    a.label('fr_sbp')
    a.br(BSR, 'draw_sbp')
    a.br(BRA, 'fr_x')
    a.label('fr_code')
    a.br(BSR, 'draw_code')
    a.label('fr_x')
    a.w(0x0838, 0x0004, E80B)                   # btst #4,$E80B (original; flags kept for caller)
    a.w(0x4E75)                                 # rts

    # draw_sbp: "nn OF 39 SBPS" with nn = bits set in the bonus mask
    a.label('draw_sbp')
    a.w(0x41F9); a.l(0)                         # lea sbp_text,a0 (patched below)
    a.label('sbp_text_ref')
    a.w(0x4EB9); a.l(TEXT_DRAW)                 # jsr draw text (a2 = end of line)
    a.w(0x7000)                                 # moveq #0,d0  count
    a.w(0x7200)                                 # moveq #0,d1  ID
    a.w(0x41F8, BONUS)                          # lea BONUS,a0
    a.label('sbp_loop')
    a.w(0x3401)                                 # move.w d1,d2
    a.w(0xE64A)                                 # lsr.w #3,d2
    a.w(0x0330, 0x2000)                         # btst d1,(a0,d2.w)
    a.br(BEQ, 'sbp_skip')
    a.w(0x5240)                                 # addq.w #1,d0
    a.label('sbp_skip')
    a.w(0x5241)                                 # addq.w #1,d1
    a.w(0x0C41, 0x0030)                         # cmpi.w #48,d1 (bits 48+ hold the digit backup)
    a.br(BNE, 'sbp_loop')
    a.w(0x80FC, 0x000A)                         # divu #10,d0
    n = SBP_TEXT_LEN = len('00 OF %d SBPS' % SBP_TOTAL)
    a.w(0x3200)                                 # move.w d0,d1      tens
    a.w(0x0641, 0x46C1)                         # addi.w #$46C1,d1
    a.w(0x3541, (-2 * n) & 0xFFFF)              # move.w d1,-2n(a2)
    a.w(0x4840)                                 # swap d0           ones
    a.w(0x0640, 0x46C1)                         # addi.w #$46C1,d0
    a.w(0x3540, (-2 * n + 2) & 0xFFFF)          # move.w d0,-2n+2(a2)
    a.w(0x4E75)                                 # rts

    # sbp_back: B pressed in the stage select -> also erase the SBP line
    a.label('sbp_back')
    a.w(0x41F9); a.l(0)                         # lea sbp_text,a0 (patched below)
    a.label('sbp_text_ref2')
    a.w(0x4EB9); a.l(TEXT_ERASE)                # jsr erase text
    a.w(0x41F9); a.l(0)                         # lea code_text,a0 (patched below)
    a.label('code_text_ref2')
    a.w(0x4EB9); a.l(TEXT_ERASE)                # jsr erase text
    for t in ('txt_notclear', 'txt_bonus', 'txt_pickups'):
        a.w(0x41F9); a.l(INFO[t])               # lea info line,a0
        a.w(0x4EB9); a.l(TEXT_ERASE)
    a.w(0x41F9); a.l(0x013BC2)                  # lea $013BC2,a0 (original lea)
    a.w(0x4E75)                                 # rts

    # draw_code: "CODE 37--" from the backed-up digits
    a.label('draw_code')
    a.w(0x41F9); a.l(0)                         # lea code_text,a0 (patched below)
    a.label('code_text_ref')
    a.w(0x4EB9); a.l(TEXT_DRAW)                 # jsr draw text (a2 = end of line)
    a.w(0x3238, BB_DIGITS)                      # move.w BB_DIGITS,d1
    a.w(0x45EA, 0xFFF8)                         # lea -8(a2),a2  (first of the 4 digit cells)
    a.w(0x7403)                                 # moveq #3,d2
    a.label('dc_loop')
    a.w(0xE959)                                 # rol.w #4,d1
    a.w(0x3001)                                 # move.w d1,d0
    a.w(0x0240, 0x000F)                         # andi.w #$F,d0
    a.w(0x0C40, 0x000F)                         # cmpi.w #$F,d0
    a.br(BNE, 'dc_dig')
    a.w(0x34FC, 0x46E5)                         # move.w #$46E5,(a2)+  '-'
    a.br(BRA, 'dc_next')
    a.label('dc_dig')
    a.w(0x0640, 0x46C1)                         # addi.w #$46C1,d0
    a.w(0x34C0)                                 # move.w d0,(a2)+
    a.label('dc_next')
    a.br(DBRA_D2, 'dc_loop')
    a.w(0x4E75)                                 # rts

    # save_bb: secret digits (game RAM) -> reset-proof backup.
    # Merges, never loses: a digit the game doesn't know (e.g. after a soft
    # reset) keeps the backed-up value. Stage bits are saved only on a win
    # (bb_won), so a FAILED game's Liberty Head comes back next time.
    a.label('save_bb')
    a.w(0x3638, BB_DIGITS)                      # move.w BB_DIGITS,d3  old digits
    a.w(0x41F8, 0xE9C4)                         # lea $E9C4,a0   4 digit words
    a.w(0x7200)                                 # moveq #0,d1
    a.w(0x7403)                                 # moveq #3,d2
    a.label('sb_loop')
    a.w(0xE949)                                 # lsl.w #4,d1
    a.w(0xE95B)                                 # rol.w #4,d3
    a.w(0x3018)                                 # move.w (a0)+,d0
    a.w(0x0C40, 0x0009)                         # cmpi.w #9,d0
    a.w(0x6306)                                 # bls.s +6      known in game
    a.w(0x3003)                                 # move.w d3,d0  else keep old nibble
    a.w(0x0240, 0x000F)                         # andi.w #$F,d0
    a.w(0x8200)                                 # or.b d0,d1
    a.br(DBRA_D2, 'sb_loop')
    a.w(0x31C1, BB_DIGITS)                      # move.w d1,BB_DIGITS
    a.w(0x4E75)                                 # rts

    # bb_won: basketball game WON (replaces addq.w #1,$E9B4 / addq.w #2,$D1D6
    # at $056D00). $E9B0 now holds the won stages plus this one: keep them.
    a.label('bb_won')
    a.w(0x5278, 0xE9B4)                         # addq.w #1,$E9B4 (original)
    a.w(0x5478, 0xD1D6)                         # addq.w #2,$D1D6 (original)
    a.w(0x3F00)                                 # move.w d0,-(sp)
    a.w(0x1038, 0xE9B0)                         # move.b $E9B0,d0
    a.w(0x8138, BB_STAGES)                      # or.b d0,BB_STAGES
    a.w(0x301F)                                 # move.w (sp)+,d0
    a.w(0x4E75)                                 # rts

    # restore_bb: backup -> game RAM ($E9B0 = won stages only, digits, games-won count)
    a.label('restore_bb')
    a.w(0x11F8, BB_STAGES, 0xE9B0)              # move.b BB_STAGES,$E9B0
    a.w(0x3238, BB_DIGITS)                      # move.w BB_DIGITS,d1
    a.w(0x41F8, 0xE9C4)                         # lea $E9C4,a0
    a.w(0x7600)                                 # moveq #0,d3   games won
    a.w(0x7800)                                 # moveq #0,d4   seen an unknown digit
    a.w(0x7403)                                 # moveq #3,d2
    a.label('rb_loop')
    a.w(0xE959)                                 # rol.w #4,d1
    a.w(0x3001)                                 # move.w d1,d0
    a.w(0x0240, 0x000F)                         # andi.w #$F,d0
    a.w(0x0C40, 0x000F)                         # cmpi.w #$F,d0
    a.br(BNE, 'rb_known')
    a.w(0x30FC, 0xFFFF)                         # move.w #$FFFF,(a0)+
    a.w(0x7801)                                 # moveq #1,d4
    a.br(BRA, 'rb_next')
    a.label('rb_known')
    a.w(0x30C0)                                 # move.w d0,(a0)+
    a.w(0x4A44)                                 # tst.w d4
    a.br(BNE, 'rb_next')
    a.w(0x5243)                                 # addq.w #1,d3
    a.label('rb_next')
    a.br(DBRA_D2, 'rb_loop')
    if ap:
        # AP: digits come from items, so the games-won count is the number of
        # basketball stages won (bits of BB_STAGES), not the number of digits.
        a.w(0x7600)                             # moveq #0,d3
        a.w(0x1038, BB_STAGES)                  # move.b BB_STAGES,d0
        a.w(0x7407)                             # moveq #7,d2
        a.label('pc_loop')
        a.w(0xE208)                             # lsr.b #1,d0
        a.w(0x6402)                             # bcc.s +2
        a.w(0x5243)                             # addq.w #1,d3
        a.br(DBRA_D2, 'pc_loop')
    a.w(0x31C3, 0xE9B4)                         # move.w d3,$E9B4
    a.w(0x4E75)                                 # rts

    a.label('code_text')
    a.w(CODE_ROW, 0x4600)
    a.code += text_bytes('CODE ----') + b'\xFF'
    if len(a.code) % 2:
        a.code += b'\xFF'

    a.label('sbp_text')
    a.w(SBP_ROW, 0x4600)
    a.code += text_bytes('00 OF %d SBPS' % SBP_TOTAL) + b'\xFF'
    if len(a.code) % 2:
        a.code += b'\xFF'

    # bonus_trap: TRAP #15 from $00A610, d0 = 2 x bonus ID, a6 = awarding object's slot
    # The bit recorded is the ID, unless (stage, ID, slot) is in BONUS_REMAP.
    # The last award's ID and slot are also stored for logging tools.
    a.label('bonus_trap')
    a.w(0x5278, E8F6)                           # addq.w #1,$E8F6 (original instruction)
    a.w(0x48E7, 0x7880)                         # movem.l d1-d4/a0,-(sp)
    a.w(0x3200)                                 # move.w d0,d1
    a.w(0xE249)                                 # lsr.w #1,d1        ID
    a.w(0x380E)                                 # move.w a6,d4       slot
    a.w(0x11C1, LAST_ID)                        # move.b d1,LAST_ID
    a.w(0x11C4, LAST_SLOT)                      # move.b d4,LAST_SLOT
    a.w(0x3638, E8AA)                           # move.w stage,d3
    a.w(0x41F9); a.l(0)                         # lea bonus_remap,a0 (patched below)
    a.label('remap_ref')
    a.label('bt_loop')
    a.w(0x3418)                                 # move.w (a0)+,d2    entry stage
    a.br(BMI, 'bt_set')                         # $FFFF = end of table
    a.w(0xB642)                                 # cmp.w d2,d3
    a.br(BNE, 'bt_skip3')
    a.w(0x3418)                                 # move.w (a0)+,d2    entry ID
    a.w(0xB242)                                 # cmp.w d2,d1
    a.br(BNE, 'bt_skip2')
    a.w(0x3418)                                 # move.w (a0)+,d2    entry slot
    a.w(0x0C42, 0xFFFF)                         # cmpi.w #-1,d2      any slot
    a.br(BEQ, 'bt_hit')
    a.w(0xB842)                                 # cmp.w d2,d4
    a.br(BNE, 'bt_skip1')
    a.label('bt_hit')
    a.w(0x3210)                                 # move.w (a0),d1     -> remapped bit
    a.br(BRA, 'bt_set')
    a.label('bt_skip3')
    a.w(0x5488)                                 # addq.l #2,a0
    a.label('bt_skip2')
    a.w(0x5488)                                 # addq.l #2,a0
    a.label('bt_skip1')
    a.w(0x5488)                                 # addq.l #2,a0
    a.br(BRA, 'bt_loop')
    a.label('bt_set')
    a.w(0x3401)                                 # move.w d1,d2
    a.w(0xE64A)                                 # lsr.w #3,d2        byte = bit/8
    a.w(0x41F8, BONUS)                          # lea BONUS,a0
    a.w(0x03F0, 0x2000)                         # bset d1,(a0,d2.w)  bit mod 8
    a.w(0x4CDF, 0x011E)                         # movem.l (sp)+,d1-d4/a0
    a.w(0x4E73)                                 # rte

    a.label('bonus_remap')
    assert all(bit < 48 for _, _, _, bit in BONUS_REMAP), 'bonus bits must be < 48'
    for stage, bid, slot, bit in BONUS_REMAP:
        a.w(stage, bid, slot & 0xFFFF, bit)
    a.w(0xFFFF)

    if ap:
        # dl_frame: runs first in every frame of play (mode $20). When the client
        # asks for a DeathLink death, call the game's death routine, unless the game
        # is paused (wait), Headdy is already dying, or deaths can't happen here.
        a.label('dl_frame')
        # Traps from the client. They wait while paused, while Headdy is dying, and
        # where they can't happen safely.
        a.w(0x4A38, TRAP_REQ)                   # tst.b TRAP_REQ
        a.br(BEQ, 'dl_death')
        a.w(0x4A78, 0xE806)                     # tst.w $E806 (paused)
        a.br(BNE, 'dl_death')
        a.w(0x0C78, 0x0008, 0xE600)             # cmpi.w #8,$E600 (dying)
        a.br(BEQ, 'dl_death')
        for st in NO_DEATH_STAGES:
            a.w(0x0C78, st, E8AA)
            a.br(BEQ, 'dl_death')
        a.w(0x0C38, 0x0001, TRAP_REQ)           # cmpi.b #1,TRAP_REQ
        a.br(BNE, 'tr_trip')
        # Mean Bean: lose 16 health (never below 2: health stays even), with the hit sound
        a.w(0x0478, 0x0010, 0xD200)             # subi.w #$10,$D200
        a.w(0x6E06)                             # bgt.s +6
        a.w(0x31FC, 0x0002, 0xD200)             # move.w #2,$D200
        a.w(0x48E7, 0xFFFE)                     # movem.l d0-d7/a0-a6,-(sp)
        a.w(0x103C, 0x0021)                     # move.b #$21,d0
        a.w(0x4EB9); a.l(SOUND)
        a.w(0x4CDF, 0x7FFF)
        a.br(BRA, 'tr_done')
        # Head Trip: put it on, as a Headcase would (only when Headdy stands, walks or
        # jumps with his head on, and not while he wears a head that has to stay)
        a.label('tr_trip')
        for st in TRAP_WAIT_STAGES[len(NO_DEATH_STAGES):]:
            a.w(0x0C78, st, E8AA)
            a.br(BEQ, 'dl_death')
        a.w(0x0C78, HEAD_TRIP, 0xEE0A)          # already wearing it: start its time again
        a.br(BNE, 'tr_new')
        a.w(0x31FC, 0x0400, 0xE8D8)             # move.w #$400,$E8D8
        a.br(BRA, 'tr_done')
        a.label('tr_new')
        for h in TRAP_WAIT_HEADS:
            a.w(0x0C78, h, 0xEE0A)
            a.br(BEQ, 'dl_death')
        a.w(0x4A78, 0xEE82)                     # tst.w $EE82 (time stopped)
        a.br(BNE, 'dl_death')
        a.w(0x4A78, 0xD106)                     # tst.w $D106 (head attached)
        a.br(BNE, 'dl_death')
        a.w(0x3038, 0xD102)                     # move.w $D102,d0
        a.w(0x0C40, 0x0008)                     # cmpi.w #8,d0 (stand 0, walk 4, air 8)
        a.br(0x6200, 'dl_death')                # bhi
        a.w(0x48E7, 0xFFFE)                     # movem.l d0-d7/a0-a6,-(sp)
        a.w(0x4EB9); a.l(HEAD_RESET)            # jsr $011366 (what a Headcase does first)
        a.w(0x3238, 0xEE0A)                     # move.w $EE0A,d1 (old head)
        a.w(0x31FC, HEAD_TRIP, 0xEE0A)          # move.w #$1A0,$EE0A
        a.w(0x2079); a.l(HEAD_SETUP + (HEAD_TRIP >> 3))   # movea.l (setup table + $34),a0
        a.w(0x4E90)                             # jsr (a0)
        a.w(0x31FC, 0x000A, 0xD106)             # move.w #$A,$D106 (head arriving)
        a.w(0x103C, 0x0023)                     # move.b #$23,d0 (Headcase sound)
        a.w(0x4EB9); a.l(SOUND)
        a.w(0x3038, 0xEE0C)                     # move.w $EE0C,d0
        a.w(0x4EB9); a.l(0x0194EA)              # head colours
        a.w(0x4EB9); a.l(0x0194B8)              # head object
        a.w(0x4CDF, 0x7FFF)
        a.label('tr_done')
        a.w(0x4238, TRAP_REQ)                   # clr.b TRAP_REQ
        a.label('dl_death')
        a.w(0x4A38, DEATH_REQ)                  # tst.b DEATH_REQ
        a.br(BEQ, 'dl_play')
        a.w(0x4A78, 0xE806)                     # tst.w $E806 (paused)
        a.br(BNE, 'dl_play')
        a.w(0x4238, DEATH_REQ)                  # clr.b DEATH_REQ
        a.w(0x0C78, 0x0008, 0xE600)             # cmpi.w #8,$E600 (already dying)
        a.br(BEQ, 'dl_play')
        for st in NO_DEATH_STAGES:
            a.w(0x0C78, st, E8AA)               # cmpi.w #stage,$E8AA
            a.br(BEQ, 'dl_play')
        a.w(0x48E7, 0xFFFE)                     # movem.l d0-d7/a0-a6,-(sp)
        a.w(0x4EB9); a.l(KILL)                  # jsr KILL
        a.w(0x4CDF, 0x7FFF)                     # movem.l (sp)+,d0-d7/a0-a6
        a.label('dl_play')
        a.w(0x4EF9); a.l(PLAY_HANDLER)          # jmp the play-mode handler
    return a


# (address, original bytes, replacement builder)
def hooks(L, ap=False):
    jsr = lambda t: bytes.fromhex('4EB9') + struct.pack('>I', t)
    h = [
        # title Start -> stage select init ($013428) instead of the cheat check
        (0x01335C, '6610 0838 0004', bytes.fromhex('4EF9') + struct.pack('>I', L['ss_enter'])),
        # Left/Right moved the cursor: move.b #$AD,d0 / jsr $118B6
        (0x013592, '103C 00AD 4EB9 0001 18B6', jsr(L['ss_move']) + bytes.fromhex('4E714E71')),
        # Start pressed: move.w $E8C4,d0 / lea $6786.l,a0
        (0x0134CC, '3038 E8C4 41F9 0000 6786', jsr(L['ss_start']) + bytes.fromhex('4E714E71')),
        # B pressed in the stage select: lea $13BC2(pc),a0 / nop
        (0x013506, '41FA 06BA 4E71', jsr(L['sbp_back'])),
        # title screen reset: moveq #-1,d0 / move.l d0,$E9C4 / move.l d0,$E9C8 / clr.l $E9B0
        # -> nops, so basketball digits and stages survive returning to the hub
        (0x0124EC, '70FF 21C0 E9C4 21C0 E9C8 42B8 E9B0', bytes.fromhex('4E71' * 7)),
        # basketball won: addq.w #1,$E9B4 / addq.w #2,$D1D6 -> jsr bb_won / nop
        (0x056D00, '5278 E9B4 5478 D1D6', jsr(L['bb_won']) + bytes.fromhex('4E71')),
        # stage select frame handler: btst #4,$E80B
        (0x013492, '0838 0004 E80B', jsr(L['ss_frame'])),
        # stage load step 0: move.w #1,$E806
        (0x007804, '31FC 0001 E806', jsr(L['hub_stage_load'])),
        # bonus point routine: addq.w #1,$E8F6 -> trap #15 / nop
        (0x00A610, '5278 E8F6', bytes.fromhex('4E4F4E71')),
        # TRAP #15 vector (unused, points at reset) -> bonus_trap
        (0x0000BC, '0000 0200', struct.pack('>I', L['bonus_trap'])),
    ]
    if ap:
        # basketball won: bsr store_digit ($056D5E) -> nops. Digits come from
        # Archipelago items; the win still counts towards the limit of 4.
        h.append((0x056CFC, '6100 0060', bytes.fromhex('4E714E71')))
        # play-mode handler pointer -> dl_frame (DeathLink)
        h.append((MODE_TABLE + PLAY_MODE, '0001 44D8', struct.pack('>I', L['dl_frame'])))
    return h


def apply(rom, unlock_mask=0x3FFFFFFE, ap=False):
    """Patch rom (bytearray) in place. Returns the labels of the new code.
    unlock_mask: entries unlocked the first time the hub starts (bit n = entry n).
    ap: Archipelago mode (basketball wins don't give digits; see hooks())."""
    a = build(ap)
    code = bytearray(a.done())
    imm = a.labels['default_mask_imm'] - CODE_BASE - 6   # the move.l immediate
    code[imm:imm + 4] = struct.pack('>I', unlock_mask)
    for ref, target in (('sbp_text_ref', 'sbp_text'), ('sbp_text_ref2', 'sbp_text'),
                        ('code_text_ref', 'code_text'), ('code_text_ref2', 'code_text'),
                        ('remap_ref', 'bonus_remap')):       # lea xxx,a0 operands
        o = a.labels[ref] - CODE_BASE - 4
        code[o:o + 4] = struct.pack('>I', a.labels[target])
    if any(b != 0xFF for b in rom[CODE_BASE:CODE_BASE + len(code)]):
        raise ValueError('free space at $%06X is not empty - already patched?' % CODE_BASE)
    if any(b != 0xFF for b in rom[INFO_BASE:INFO_BASE + len(INFO_CODE)]):
        raise ValueError('free space at $%06X is not empty - already patched?' % INFO_BASE)
    rom[CODE_BASE:CODE_BASE + len(code)] = code
    rom[INFO_BASE:INFO_BASE + len(INFO_CODE)] = INFO_CODE
    for addr, orig, new in hooks(a.labels, ap):
        o = bytes.fromhex(orig.replace(' ', ''))
        if rom[addr:addr + len(o)] != o:
            raise ValueError('unexpected bytes at $%06X - wrong ROM or already patched' % addr)
        assert len(new) <= len(o)
        rom[addr:addr + len(new)] = new
    s = 0
    for i in range(0x200, 0x60002, 2):
        s = (s + (rom[i] << 8 | rom[i + 1])) & 0xFFFF
    rom[0x18E], rom[0x18F] = s >> 8, s & 0xFF
    return a.labels, len(code), s


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    src, dst = sys.argv[1], sys.argv[2]
    mask = 0x00000002 if "--start-locked" in sys.argv else 0x3FFFFFFE
    rom = bytearray(open(src, 'rb').read())
    if hashlib.sha1(rom).hexdigest() != US_SHA1:
        print('warning: not the unmodified Dynamite Headdy (USA, Europe) ROM '
              '(fine if you applied the Headcase randomizer first)', file=sys.stderr)
    try:
        labels, n, s = apply(rom, mask, ap="--ap" in sys.argv)
    except ValueError as e:
        sys.exit(str(e))
    open(dst, 'wb').write(rom)
    print('hub patch applied: %d bytes of new code at $%06X, checksum $%04X' % (n, CODE_BASE, s))
    for k in ('ss_move', 'ss_start', 'hub_stage_load', 'bonus_trap'):
        print('  %-15s $%06X' % (k, labels[k]))


if __name__ == '__main__':
    main()
