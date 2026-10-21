# An open world (/play)

The owner: "I feel like the world should feel more open world like. Is this possible?"

The world underneath is a MUD's: rooms joined where an exit was written, each room a 24 x 15 m
cell on its zone's map. /play already draws a zone as one place; what still felt like boxes:

1. outdoor rooms side by side on the map joined only where an exit was written (corridors through a
   forest);
2. the land ending half a cell past a zone's edge rooms (darkness beyond);
3. draw distance (rooms past 3 cells hidden, for speed);
4. zone borders crossed with a fade and a load;
5. creatures living in rooms (they notice you, and wander, room by room).

| Phase | What | State |
|---|---|---|
| 1 | Open ground: side-by-side outdoor rooms join up; the land runs on past the edge | every zone (the God Rooms aside): 135 ways in 25 zones |
| 2 | See further: far rooms drawn cheaply, the haze further off, far hills, a lower camera | done |
| 3 | Seamless zone borders: the zones next door drawn past the border, walked into without a load | done |
| 4 | A living world: creatures see across the open land and come; herds roam together; wanderers use the openings | done |

## Phase 1: open ground (`src/wilds.py`)

In an opened zone (`wilds.WILD_ZONES`), two rooms side by side on the zone map
(`map_system.build_zonemap`) are joined both ways when both are open country (a land look:
forest, field, hills, desert, snow, swamp, stones, shore) and neither is flagged as walled
(death trap, private, immortal, tunnel, indoors). The joins are real exits (`'wild': True`), so
walking, followers, wandering creatures, reaching into the next room and pulls all follow them,
for telnet players too; the zone map gives them as `open`, and the 3D client draws the two rooms'
shared side as open country (roomgen.js).

Never a way the zone did not already have in another form: two rooms are joined only when one can
already walk from one to the other without passing a door (so a locked gate, its key and its
keeper keep their meaning: rites.py), and back again (a one-way drop stays one way). Water keeps
its banks (it needs a boat). Applied at world load after the room looks, before the tutorials'
routes.

The client (terrain.js `fillerLand`): in an opened zone the land skirt past an edge room reaches a
cell and a half out instead of half a cell, thinning into the fog.

Every zone is opened (`WILD_ZONES = None`), save those in `CLOSED_ZONES` (the God Rooms): 135
new joins in 25 zones (most zones' open country already joined itself, or they have none).

Checks: `python3 tests/test_polish.py` (the open ground section).

## Phase 2: see further (`world3d/far.js`)

Only the rooms round the hero are built in full (zone.js: within 2 rooms, drawn to 3). Past them
every room of the zone on the hero's level, within the quality's reach (low 6, med 8, high 10
rooms), is drawn as a tinted ground tile and a few shapes for what stands in it (tree crowns,
mounds, crags, roofs, water), all in a handful of instanced meshes (a few draw calls for the whole
zone); a room's stand-in shows only while the room itself is not built and drawn. Outdoors the
haze lies further off (`engine.farSight`: x1.25 / 1.45 / 1.65 by quality) and a ring of far hills
in the haze's colour stands round the hero. The camera may be dragged lower (pitch down to 14
degrees: orbit.js) to look out over the land.

### Past the edge: the country runs on (2026-10)

The owner, on the Sea of Storms: "ocean rooms that have no exit should just show more ocean on the
horizon or a land mass if there's a description of land in the distance ... forests, marshes etc
too". Before, a sea room's exitless sides were a bank of grass and rocks, a strip of water past
it, then the bare sky.

- **Open water to the edge** (roomgen.js `deep`, edges.js `landSides`): a water room's sides that
  are not land are drawn as water to its edge (still blocked: no boat leaves that way). A side is
  land when its way out leads onto land, the map's room there is dry land, or the room's words put
  the shore or a breakwater right there (a `near` vista); it keeps its bank, and the skirt past it
  is land.
- **Filler cells** (far.js `fillerPlan`, edges.js `fillKind`): every empty map cell within 4 rooms
  of the zone's rooms is drawn as the country nearest it: the sea as the room's own bed under the
  room's own water surface (one sea out to the haze), a forest as crowns, a marsh as marsh. Their
  shapes stand back where a built room's own land lies.
- **The sea's light** (engine.js `sea` mood): a blue-grey haze the far water fades into; at sea
  the far hills lie down into a horizon line.
- **Land in the distance** (room_vistas.py, vista.js): a room's words ("South lies the harbor to
  Timeless Island", "Close beyond the bergs looms the black headland of Cape Voogk") give a
  low-poly island, coast, cliffs, mountains, hills, forest or town where the view ends that way
  (the camera looks down from the south: some 22 m to either side, 34 m ahead); named with no
  side, off the sides with no way out. None where the zone's own rooms stand that way.

Checks: `python3 tests/test_room_vistas.py`, `node --test tests/web/edges.test.mjs`
(and roomlooks.test.mjs).

## Phase 3: seamless zone borders

On entering a zone the client fetches the maps of the zones next door (main.js `nextDoor`) and
draws each past the border where its way in says it lies (zone.js `addGhost`: the room a 'zone'
exit leads to sits in the cell beyond the exit's room), with the same stand-ins, never over the
zone's own ground. Crossing a compass-side border into a zone whose map is in hand is a step: no
dimming, no load, no flash (`hop.seamless`); the new zone is built round the hero at once.

## Phase 4: a living world

- An aggressive creature with no one to fight in its own room sees a hero with a position (/play)
  in a room joined to its own by an open way, within 16 m and not hiding (`reach.noticed`), runs
  in and attacks (`Mobile._charge_next_door`, `reach.bring`). Never from or into a peaceful room or
  one creatures keep out of; never a sentinel, a boss, a servant or a pet.
- A creature that wanders off may take up to three of its own kind idling with it
  (`Mobile._herd_follows`): herds and packs roam together.
- In /play a wanderer crossing to the next room walks through the opening between the two (the
  middle of their shared side), not through the wall (entities.js).
- A creature running in from next door (pulled, or charging at a hero it saw) snarls and kicks up
  dust as it sets off (entities.js `charging`, main.js `ents.onCharge`, the `growl` sound).

## Running away

- A creature a hero fled or escaped from leaves them alone for 30 s (`reach.lost`,
  `reach.FLEE_GRACE`): it does not spot them in the room next door and charge straight back.
- A hunter, tracker or boss chases only so far from where the chase began (`mobs.LEASH`: 3, 5 and
  6 rooms by open ways). Past that it gives up ("gives up the chase and turns back"), heals to
  full (no wearing it down by leading it about) and walks back to where it began.
