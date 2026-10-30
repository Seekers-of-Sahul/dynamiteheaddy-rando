from dataclasses import dataclass

from .data import STAGES
from Options import Choice, DeathLink, DefaultOnToggle, PerGameCommonOptions, Range, Toggle


class Goal(Choice):
    """
    What you need to do to finish.
    secret_boss: beat the secret boss behind the door after the credits (needs all 4 Secret Code Digits).
    final_boss: beat 9-3.
    bonus_points: collect the required number of Secret Bonus Points, then beat 9-3.
    """
    display_name = "Goal"
    option_secret_boss = 0
    option_final_boss = 1
    option_bonus_points = 2
    default = 0


class RequiredBonusPoints(Range):
    """Secret Bonus Points needed for the bonus_points goal (out of 39)."""
    display_name = "Required Bonus Points"
    range_start = 1
    range_end = 39
    default = 20


class StartingStage(Choice):
    """The stage that is unlocked from the start (random picks any of them). The others are items."""
    display_name = "Starting Stage"
    for _bit, _name, _ in STAGES:
        locals()["option_act_" + _name.replace("-", "_")] = _bit
    del _bit, _name, _
    default = 1


class Headcases(Choice):
    """
    Randomize the heads inside Headcases. The heads needed to finish each stage and to reach its
    Secret Bonus Points are always guaranteed in that stage.
    safe: every Headcase keeps one of its original heads. chaos: anything goes.
    """
    display_name = "Headcases"
    option_off = 0
    option_safe = 1
    option_chaos = 2
    default = 1


class HeadTrip(DefaultOnToggle):
    """
    Allow Head Trip in shuffled Headcases. It's a head to avoid: your head becomes so big and heavy
    that it's hard to move around, and enemies easily stomp on you.
    """
    display_name = "Head Trip"


class FlyingHeads(Toggle):
    """
    Allow Rocket, Air and Feather Head in shuffled Headcases. Press A to drop them; they time out
    like other heads. Never placed in 4-1, 4-3, 5-1, 8-1 or 8-2. Outside act 6 their shots
    are drawn as stars and fireballs.
    """
    display_name = "Flying Heads"


class HeadHunter(Toggle):
    """
    Add Head Hunter (an unused head) to shuffled Headcases. It attacks like the normal head, and
    defeated enemies sometimes drop a pickup while you wear it (never bosses).
    """
    display_name = "Head Hunter"


class BossBomb(DefaultOnToggle):
    """Keep Bomb Head available at the act 7 boss."""
    display_name = "Act 7 Boss Bomb Head"


class PickupShuffle(Choice):
    """
    off: vanilla pickups. shuffle: jelly beans, 500-point items and 1-ups swap places.
    randomized: every spot gets a random pickup (45% bean, 45% 500 points, 10% 1-up).
    500-point items only appear in stages that have them.
    """
    display_name = "Pickup Shuffle"
    option_off = 0
    option_shuffle = 1
    option_randomized = 2
    default = 0


class NewPickups(Toggle):
    """
    Turn some jelly beans into new pickups. Upside-down bean: takes half your health (never below 1).
    Powerup beans give 15 seconds of double jump, power (double head damage, bigger head
    hitbox) or heavy (half damage, no knockback).
    """
    display_name = "New Pickups"


class JPBalance(Toggle):
    """
    Japanese difficulty: 2 starting continues, a continue every 10 tokens, the JP 1-1 boss, Stair Wars
    pattern, act 7 / 8-5 / 9-3 boss HP, JP 6-1 waves and the 3-1 (extra Headcase), 6-2 and 6-4 layouts.
    Needs the Dynamite Headdy (Japan) ROM when patching.
    """
    display_name = "JP Balance"


class JPPalettes(Toggle):
    """Restore the Japanese colours of the 8 palettes the US version changed. Needs the Japan ROM when patching."""
    display_name = "JP Palettes"


class Palettes(Choice):
    """
    Recolour each stage.
    safe: gentle shifts and warm/cool/dusk/muted moods that keep every colour's brightness.
    hue: any hue rotation. chaos: swapped and inverted colour channels.
    """
    display_name = "Palettes"
    option_off = 0
    option_safe = 1
    option_hue = 2
    option_chaos = 3
    default = 0


class PaletteSprites(Toggle):
    """Also recolour Headdy, enemies and Headcases."""
    display_name = "Recolour Sprites"


class EnemyDamage(Choice):
    """Contact damage to Headdy. shuffled: each enemy type x0.5 to x2."""
    display_name = "Enemy Damage"
    option_vanilla = 0
    option_shuffled = 1
    option_half = 2
    option_double = 3
    default = 0


class TrapPercentage(Range):
    """How many of the filler items (extra lives, continues, health refills) are traps instead, in percent."""
    display_name = "Trap Percentage"
    range_start = 0
    range_end = 100
    default = 0


class MeanBeanTrapWeight(Range):
    """How likely a trap is a Mean Bean Trap: you lose 16 health (half the maximum), but never go below 2."""
    display_name = "Mean Bean Trap Weight"
    range_start = 0
    range_end = 10
    default = 1


class HeadTripTrapWeight(Range):
    """
    How likely a trap is a Head Trip Trap: Head Trip goes on your head for its usual time. It waits while you
    wear a head you need (Ticker, Liberty Head, Bomb, flying heads) and in act 6.
    """
    display_name = "Head Trip Trap Weight"
    range_start = 0
    range_end = 10
    default = 1


@dataclass
class HeaddyOptions(PerGameCommonOptions):
    goal: Goal
    required_bonus_points: RequiredBonusPoints
    starting_stage: StartingStage
    headcases: Headcases
    head_trip: HeadTrip
    flying_heads: FlyingHeads
    boss_bomb: BossBomb
    head_hunter: HeadHunter
    jp_balance: JPBalance
    jp_palettes: JPPalettes
    palettes: Palettes
    palette_sprites: PaletteSprites
    enemy_damage: EnemyDamage
    pickup_shuffle: PickupShuffle
    new_pickups: NewPickups
    trap_percentage: TrapPercentage
    mean_bean_trap_weight: MeanBeanTrapWeight
    head_trip_trap_weight: HeadTripTrapWeight
    death_link: DeathLink
