# Dynamite Headdy

## What does randomization do to this game?

The stage select becomes a hub. You start with one stage unlocked; every other stage is unlocked by an
item from the multiworld. When you clear an act you go back to the hub. For the stage under the cursor,
the hub shows whether it's cleared, how many of its Secret Bonus Points you have and, with pickupsanity,
how many of its pickups you've collected. Headcase contents, colours,
enemy damage and the Japanese balance can also be changed with options.

## What is the goal?

By default, beat the secret boss behind the door after the credits. You need all four Secret Code
Digits (items) to open the door; the hub shows the digits you have. Other goals: beat 9-3, or collect a
number of Secret Bonus Points and beat 9-3.

## Which locations are checks?

- Clearing each of the 29 acts
- Each of the 39 Secret Bonus Points
- Winning basketball games 1 to 4 (Liberty Head disappears after the 4th win, as in the original)
- Beating the secret boss
- With `pickupsanity`: every jelly bean, 500-point item and 1-up placed in the stages (86 of them;
  Head Hunter drops don't count). Each one is named after its act and its order from the start of the
  act, e.g. "2-2 Pickup 3". Keep the client connected while you play: a pickup collected while it isn't
  is sent the next time you collect it.

## What items are there?

- Stage unlocks for every act
- Secret Code Digits 1-4 (basketball wins no longer give digits)
- Extra lives, continues and health refills
- Traps, if `trap_percentage` is above 0: **Mean Bean Trap** (lose 16 health, never below 2) and
  **Head Trip Trap** (Head Trip goes on your head for its usual time). Traps wait while the game is
  paused, while you're dying, and in the stage select, tutorial rooms and basketball; a Head Trip Trap
  also waits in act 6 and while you wear Ticker, Liberty Head, Pin, Bomb or a flying head.

## Does it support DeathLink?

Yes, with the `death_link` option. When Headdy dies, everyone else with DeathLink dies too, and when
they die, so does Headdy. A death that arrives while you are in the stage select, a tutorial room or a
basketball game is ignored; one that arrives while the game is paused happens when you unpause.

## What does another world's item look like in Dynamite Headdy?

Nothing changes on screen: the check is sent when you clear the act, take the bonus point or win the game.
