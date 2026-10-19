# Cover Tracks (thieves and assassins)

The owner: "A cool thief and assassin skill would be something that covers tracks when sneaking
and performing stealth activities."

`cover tracks` (or `cover_tracks`, or its button on the bar in /play), learnt at level 7 by
thieves and assassins (`mastery.py`), practised by use like any skill. Not mid-fight; 45 s
between uses (`stealth.py`).

- **At once**: whatever is hunting you (a hunter, a tracker, anything holding a grudge) and is
  not in sight of you loses your trail. The better your skill and the higher you are over it,
  the surer (`stealth.lose_odds`: 25% to 95%). You hear it ("Somewhere behind you, something
  loses your trail"); where it stands, it "sniffs at the ground and casts about".
- **For a few minutes after** (20 ticks + half your level, about 2-5 minutes; the
  `tracks_covered` flag):
  - a hunter that picks up the hunt again may lose the trail at each step (`mobs.hunting_ai`);
  - creatures across the open land notice you only from half as far (`reach.noticed`);
    sneaking, they do not notice you at all, as before;
  - a creature you flee or escape from leaves you alone twice as long (`reach.lost`);
  - a theft is easier: no trace gives you away (steal +10);
  - in /play you leave no footprints in snow and sand, only a faint brush of dust at the heel,
    and a little dust settles about your feet.

Best used with sneak: sneak, cover your tracks, and nothing follows.

Checks: `python3 tests/test_stealth.py`.
