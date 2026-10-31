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

# Pickupsanity: every jelly bean, 500-point item and 1-up the stages place.
# (act, stage ID, number in the act by position, the placement's saved ID). When Headdy
# touches one, the game sets $FFA800 + saved ID (cleared when a stage loads); the client
# reads those flags for the current stage. Types can change (pickup shuffle), spots don't.
PICKUP_SPOTS = [
    ("2-2", 0x02, 1, 0x10),   # X=336, 500 points
    ("2-2", 0x02, 2, 0x16),   # X=720, 500 points
    ("2-2", 0x02, 3, 0x1C),   # X=1200, 500 points
    ("2-2", 0x02, 4, 0x23),   # X=1408, 1-up
    ("2-2", 0x02, 5, 0x25),   # X=1476, 500 points
    ("2-2", 0x02, 6, 0x2B),   # X=1912, 500 points
    ("2-2", 0x02, 7, 0x2E),   # X=2128, jelly bean
    ("2-2", 0x02, 8, 0x2F),   # X=2240, jelly bean
    ("2-2", 0x02, 9, 0x36),   # X=2760, 500 points
    ("2-2", 0x02, 10, 0x39),   # X=2952, 500 points
    ("2-2", 0x02, 11, 0x3E),   # X=3200, 500 points
    ("2-2", 0x02, 12, 0x40),   # X=3232, 500 points
    ("2-2", 0x02, 13, 0x41),   # X=3312, 500 points
    ("2-2", 0x02, 14, 0x46),   # X=3755, jelly bean
    ("2-2", 0x02, 15, 0x48),   # X=3792, 500 points
    ("2-2", 0x02, 16, 0x4D),   # X=3956, 500 points
    ("2-2", 0x02, 17, 0x50),   # X=4144, 500 points
    ("2-2", 0x02, 18, 0x51),   # X=4168, 500 points
    ("3-1", 0x10, 1, 0x14),   # X=1136, jelly bean
    ("3-1", 0x10, 2, 0x17),   # X=1424, 500 points
    ("3-1", 0x10, 3, 0x19),   # X=1520, 500 points
    ("3-1", 0x10, 4, 0x1D),   # X=2032, 1-up
    ("3-1", 0x10, 5, 0x1E),   # X=2032, jelly bean
    ("4-1", 0x04, 1, 0x3D),   # X=2256, 500 points
    ("4-1", 0x04, 2, 0x3E),   # X=2256, 500 points
    ("4-1", 0x04, 3, 0x49),   # X=2801, 500 points
    ("4-1", 0x04, 4, 0x4A),   # X=2817, jelly bean
    ("4-1", 0x04, 5, 0x4B),   # X=2833, 500 points
    ("4-1", 0x04, 6, 0x5D),   # X=3585, 1-up
    ("4-1", 0x04, 7, 0x63),   # X=4304, 500 points
    ("4-1", 0x04, 8, 0x64),   # X=4304, 500 points
    ("4-1", 0x04, 9, 0x68),   # X=4592, 500 points
    ("4-1", 0x04, 10, 0x76),   # X=5040, 500 points
    ("4-1", 0x04, 11, 0x77),   # X=5056, 500 points
    ("4-1", 0x04, 12, 0x78),   # X=5072, 500 points
    ("4-1", 0x04, 13, 0x7C),   # X=5392, 500 points
    ("4-1", 0x04, 14, 0x8A),   # X=5904, 500 points
    ("4-1", 0x04, 15, 0x8D),   # X=6016, jelly bean
    ("4-1", 0x04, 16, 0x8E),   # X=6048, 500 points
    ("4-1", 0x04, 17, 0x92),   # X=6248, 500 points
    ("4-2", 0x16, 1, 0x11),   # X=624, jelly bean
    ("4-2", 0x16, 2, 0x15),   # X=912, 500 points
    ("4-2", 0x16, 3, 0x2C),   # X=1504, 500 points
    ("4-2", 0x16, 4, 0x2D),   # X=1504, 500 points
    ("4-2", 0x16, 5, 0x42),   # X=2240, 1-up
    ("4-2", 0x16, 6, 0x44),   # X=2320, 500 points
    ("4-2", 0x16, 7, 0x45),   # X=2368, 500 points
    ("4-3", 0x18, 1, 0x16),   # X=672, 500 points
    ("4-3", 0x18, 2, 0x17),   # X=672, 500 points
    ("4-3", 0x18, 3, 0x2C),   # X=1584, 500 points
    ("4-3", 0x18, 4, 0x2D),   # X=1584, 500 points
    ("4-3", 0x18, 5, 0x2E),   # X=1584, 500 points
    ("5-3", 0x1C, 1, 0x10),   # X=400, jelly bean
    ("6-2", 0x52, 1, 0x21),   # X=2496, jelly bean
    ("6-3", 0x54, 1, 0x5E),   # X=14600, jelly bean
    ("8-1", 0x22, 1, 0x80),   # X=464, 500 points
    ("8-1", 0x22, 2, 0x81),   # X=1136, 500 points
    ("8-1", 0x22, 3, 0x82),   # X=1664, 500 points
    ("8-1", 0x22, 4, 0x83),   # X=2608, 500 points
    ("8-1", 0x22, 5, 0x84),   # X=2640, 500 points
    ("8-1", 0x22, 6, 0x85),   # X=2672, 500 points
    ("8-1", 0x22, 7, 0x86),   # X=2704, jelly bean
    ("8-3", 0x26, 1, 0x10),   # X=272, jelly bean
    ("8-3", 0x26, 2, 0x11),   # X=272, jelly bean
    ("8-3", 0x26, 3, 0x26),   # X=624, 500 points
    ("8-3", 0x26, 4, 0x2F),   # X=832, 1-up
    ("8-3", 0x26, 5, 0x33),   # X=976, 500 points
    ("8-3", 0x26, 6, 0x34),   # X=1008, jelly bean
    ("8-3", 0x26, 7, 0x41),   # X=1168, 500 points
    ("8-3", 0x26, 8, 0x42),   # X=1168, 500 points
    ("8-3", 0x26, 9, 0x43),   # X=1200, 500 points
    ("8-3", 0x26, 10, 0x44),   # X=1200, 500 points
    ("8-3", 0x26, 11, 0x45),   # X=1344, 1-up
    ("8-3", 0x26, 12, 0x60),   # X=2224, 500 points
    ("8-3", 0x26, 13, 0x61),   # X=2224, jelly bean
    ("8-3", 0x26, 14, 0x62),   # X=2256, jelly bean
    ("8-3", 0x26, 15, 0x63),   # X=2256, 500 points
    ("8-3", 0x26, 16, 0x64),   # X=2256, 500 points
    ("9-1", 0x2C, 1, 0x10),   # X=952, 1-up
    ("9-1", 0x2C, 2, 0x11),   # X=952, 1-up
    ("9-1", 0x2C, 3, 0x1E),   # X=1415, 500 points
    ("9-1", 0x2C, 4, 0x1F),   # X=1543, 500 points
    ("9-1", 0x2C, 5, 0x20),   # X=1735, 500 points
    ("9-1", 0x2C, 6, 0x21),   # X=1863, 500 points
    ("9-1", 0x2C, 7, 0x22),   # X=1991, 500 points
    ("9-2", 0x2E, 1, 0x13),   # X=736, jelly bean
]
RAM_PICKUP_MASK = 0xFF90    # 12 bytes for the hub's stage info: bit i = pickup check i done
RAM_PU_FLAG = 0xFF9C        # byte: 1 = the hub shows the pickups line (pickupsanity)
RAM_COLLECTED = 0xA800      # 256 bytes: $FF = the object with that saved ID was collected
RAM_STAGE_ID = 0xE8AA       # word: current stage ID

# ROM marker written by the patch (outside the checksummed area).
ROM_MARKER_ADDR = 0x1D5E00
ROM_MARKER = b"HEADDYAP1"
ROM_NAME_ADDR = 0x1D5E10    # player name, 64 bytes, zero padded
