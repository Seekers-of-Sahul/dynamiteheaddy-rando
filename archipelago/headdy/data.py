"""Game data for the Dynamite Headdy apworld: stages, bonus points, RAM addresses."""

GAME = "Dynamite Headdy"
BASE_ID = 0x48440000

# Stage-select entries (bit n of the hub's unlock / cleared masks), with stage IDs.
STAGES = [
    (1, "1-1", 0x00), (2, "2-1", 0x0C), (3, "2-2", 0x02), (4, "2-3", 0x06),
    (5, "3-1", 0x10), (6, "3-2", 0x12), (7, "3-3", 0x32), (8, "3-4", 0x14),
    (9, "4-1", 0x04), (10, "4-2", 0x16), (11, "4-3", 0x18), (12, "4-4", 0x34),
    (13, "5-1", 0x36), (14, "5-2", 0x1A), (15, "5-3", 0x1C), (16, "5-4", 0x1E),
    (17, "6-1", 0x50), (18, "6-2", 0x52), (19, "6-3", 0x54), (20, "6-4", 0x56),
    (21, "7", 0x20), (22, "8-1", 0x22), (23, "8-2", 0x24), (24, "8-3", 0x26),
    (25, "8-4", 0x28), (26, "8-5", 0x2A), (27, "9-1", 0x2C), (28, "9-2", 0x2E),
    (29, "9-3", 0x30),
]
STAGE_BIT = {name: bit for bit, name, _ in STAGES}
SECRET_BOSS_BIT = 30

# Stages with a Liberty Head (a basketball game).
BASKETBALL_STAGES = ["2-2", "3-3", "4-2", "5-1", "7", "8-3"]

# Secret Bonus Points: (location name, act, bit recorded by the hub patch).
BONUS_POINTS = [
    ("1-1 Bonus Point", "1-1", 0),
    ("2-1 Bonus Point (Headcase Tutorial)", "2-1", 7),
    ("2-1 Bonus Point (Hangman Tutorial)", "2-1", 40),
    ("2-1 Bonus Point (Beau Tutorial)", "2-1", 41),
    ("2-2 Bonus Point 1", "2-2", 1),
    ("2-2 Bonus Point 2", "2-2", 13),
    ("2-2 Bonus Point 3", "2-2", 10),
    ("2-2 Bonus Point 4", "2-2", 42),
    ("2-3 Bonus Point", "2-3", 2),
    ("3-1 Bonus Point", "3-1", 11),
    ("3-2 Bonus Point", "3-2", 12),
    ("3-3 Bonus Point", "3-3", 39),
    ("3-4 Bonus Point", "3-4", 14),
    ("4-1 Bonus Point 1", "4-1", 15),
    ("4-1 Bonus Point 2", "4-1", 3),
    ("4-1 Bonus Point 3", "4-1", 16),
    ("4-2 Bonus Point", "4-2", 17),
    ("4-3 Bonus Point 1", "4-3", 18),
    ("4-3 Bonus Point 2", "4-3", 43),
    ("4-4 Bonus Point", "4-4", 19),
    ("5-2 Bonus Point", "5-2", 21),
    ("5-3 Bonus Point", "5-3", 22),
    ("5-4 Bonus Point", "5-4", 23),
    ("6-1 Bonus Point (Bino Head)", "6-1", 35),
    ("6-1 Bonus Point", "6-1", 36),
    ("6-4 Bonus Point", "6-4", 37),
    ("7 Bonus Point 1", "7", 25),
    ("7 Bonus Point 2", "7", 4),
    ("7 Bonus Point 3", "7", 26),
    ("8-1 Bonus Point", "8-1", 27),
    ("8-2 Bonus Point", "8-2", 28),
    ("8-3 Bonus Point 1", "8-3", 29),
    ("8-3 Bonus Point 2", "8-3", 6),
    ("8-4 Bonus Point", "8-4", 30),
    ("8-5 Bonus Point", "8-5", 5),
    ("9-1 Bonus Point 1", "9-1", 31),
    ("9-1 Bonus Point 2", "9-1", 38),
    ("9-2 Bonus Point", "9-2", 33),
    ("9-3 Bonus Point", "9-3", 34),
]

# Hub-patch RAM (68K RAM domain offsets; the game sees them at $FFxxxx).
RAM_BB_STAGES = 0xFFE2      # byte: basketball stages won
RAM_UNLOCK = 0xFFE4         # long: unlocked stage-select entries
RAM_CLEARED = 0xFFE8        # long: cleared entries; bit 30 = secret boss
RAM_MAGIC = 0xFFF0          # word: 'AP' once the hub has initialised its variables
RAM_HUBFLAG = 0xFFEE        # byte: just started a stage; $FFEF = stage select redraw countdown
RAM_BONUS = 0xFFF2          # 6 bytes: bonus point bits 0-47
RAM_DIGITS_BACKUP = 0xFFF8  # word: 4 nibbles, $F = unknown
RAM_ITEMS = 0xFFFC          # word: received items already applied (consumables)
RAM_HUB_BLOCK = 0xFFE0      # read $FFE0-$FFFF in one go
RAM_GAME_DIGITS = 0xE9C4    # 4 words, $FFFF = unknown
RAM_LIVES = 0xE8EC          # word
RAM_CONTINUES = 0xE93C      # word
RAM_HEALTH = 0xD200         # word, $20 = full
RAM_MODE = 0xE802           # word, $20 = playing
RAM_STAGE = 0xE8AA          # word
RAM_HEADDY_STATE = 0xE600   # word: Headdy's routine; 8 = dying
RAM_TRAP = 0xFFE0           # byte: trap for the hub patch (1 Mean Bean, 2 Head Trip); it clears it
RAM_DEATH_REQ = 0xFFFE      # byte: set to 1 to make Headdy die (DeathLink, hub patch)
DYING = 8

# ROM marker written by the patch (outside the checksummed area).
ROM_MARKER_ADDR = 0x1D5E00
ROM_MARKER = b"HEADDYAP1"
ROM_NAME_ADDR = 0x1D5E10    # player name, 64 bytes, zero padded
