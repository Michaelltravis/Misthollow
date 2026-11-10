#!/usr/bin/env python3
"""The first zone's rooms and creatures said in the world's voice (docs/world/WORLD_SPINE.md, pillar 6:
"one voice: plain, a little grave, never winking at the player").

Zone 186 came from a stock area that joked about itself ("couldn't they hire someone to clean this
place? What will the newbies think?"). It is the first place a new hero fights, so it is the first
place the world should sound like itself: an old watch-house of the lantern-bearers at the city's
edge, half given back to the damp, where the Temple still sends the newly woken to find their feet.
The mist gets into its lower passages; what it has touched down there has forgotten its name.

Every room keeps its exits, flags and creatures, and every creature its numbers. Names that spoke
of "newbies" are changed too (ROOM_NAMES, MOB_NAMES, thing_text): the owner kept the renames.

    python3 tools/world/proving_halls_text.py            # rewrites world/zones/zone_186.json in place
    python3 tools/world/proving_halls_text.py --check    # fails if a room or creature is not covered
"""
import json
import os
import sys

PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'world', 'zones', 'zone_186.json')

ROOMS = {
    18600: "An arch of old city stone stands open here, a lantern bracket rusting on either side of it. This was a watch-house of the lantern-bearers once; the Temple still sends the newly woken here to find their feet. The way in is north. Behind you the smoke and noise of the city go on as they always have.",
    18601: "The passage opens into a long corridor of dressed stone. Something moves further in, though the sound comes from no one direction. The corridor runs east; the entrance is back to the south.",
    18602: "The hallway runs on, east and west. Damp has got into the mortar here and a grey bloom covers the lower courses of the wall. There is movement behind the door to the south, and more of it somewhere to the east.",
    18603: "Two passages meet here. North and east the light is better, as if lamps were still kept there; the hallway to the south is darker. Doors close off the north and the east, and a plain passage leads back west.",
    18604: "A narrow passage, bare of any ornament but swept clean. It ends to the south at a small oak door, and something is moving on the other side of it.",
    18605: "A pit, dark and wet underfoot, the air close. Whatever the watch kept down here, something else has it now, and it is watching you from the corner. The only way out is back up.",
    18606: "A small square room, the kind a watch-sergeant might have slept in. Its present tenant looks up, startled to have company. There are doors to the north and the east, and a hatch in the floor.",
    18607: "More of the hallway, running north and south with a low ceiling. A door stands in the west wall.",
    18608: "Open ground at last, and clean air: a strip of rough grass under the watch-house wall, with the wide fields beyond it. The passage back inside is to the east.",
    18609: "The hallway ends here. To the west daylight shows through an open archway onto the fields; to the east the passage runs back the way you came.",
    18610: "The hallway runs east and west. To the west it grows brighter, and the air moves a little.",
    18611: "The passage turns here, west and north, and the floor is thick with what the damp has brought down from the walls. A door stands in the east wall.",
    18612: "Bottles and flasks crowd every shelf and half the floor, most of them empty, some of them not. Whoever works here works carefully: the walls are covered in formulae in a small exact hand. There are doors to the north and west, and a stair down.",
    18620: "A corner like the others, but for a red glow that comes up the passage from the south. The passage also runs east.",
    18621: "A long east-west passage meets a corridor leading south. The air is clearer here, as though a way out were not far off.",
    18622: "The passage turns here, south and west. Green-grey mould has covered the walls for some way now, and there are things moving in the dark that keep just out of your light.",
    18623: "Plain grey brick, greened over with mould. You can hear things moving in every direction, and none of it sounds like footsteps. The passage runs east and south.",
    18624: "The passage turns south here, and west. It would be easy to lose your bearings in these turnings; the watch cut marks at the corners once, and the mould has taken most of them.",
    18625: "The passage opens into a wide oval room with a floor worn smooth by drilling feet. Nothing is kept here now. Ways lead east and south.",
    18626: "A long, narrow passage running east and west. The walls are wet and furred with mould, and the air is bad: the mist has been in here, and not long ago.",
    18627: "A narrow east-west passage crosses a wider one running north and south. The air is dank and carries the smell of rot from somewhere below.",
    18628: "Little more than a crossing of two passages, north and west. A thin draught comes down from the north, and it does not smell clean.",
    18629: "The red light comes from the floor: a round opening, and through it, as if seen from a great height, a dirt road running across a field in evening light. It is not a painting. The air above it is warm. Passages lead east and north.",
    18630: "The north-south passage gives off a branch to the west. A red glow comes from that way, and a faint warm draught with it.",
    18631: "The passage is so narrow here that your shoulders brush both walls, and the mould comes away on your sleeves. It clings more than it should. Ways lead east, north and south.",
    18632: "The stair comes up into cold and dark. This is the old part of the watch-house, the part the damp took first, and there are things moving in it that do not sound as if they would welcome you. Passages lead north, south and west; the stair goes on up.",
    18633: "Another turning, east and north. More mould, more small sounds in the dark, and a thin draught from the north.",
    18634: "Three passages meet: north, south and west. It is cold here and everything is greened over, and you find you would rather be anywhere else.",
    18635: "Something has died in here, and not recently. From the sounds in the passages around you, something else is still very much alive. Ways lead east and north.",
    18636: "The east-west passage gives off a branch to the south. The smell of death is everywhere; only the mould seems to thrive on it.",
    18637: "The passage turns north here, and west. There is something ahead to the north. You cannot tell what, and you are not sure you want to.",
    18638: "The walls fall away on either side and you are suddenly standing in open dark, your light reaching nothing. A large room, how large you cannot say. You can be come at from any side here. The ways you know of are east and north.",
    18639: "Your light catches the east wall: words scratched into the stone, and a crude picture beside them. They are names, dozens of them, cut by people who meant to be remembered. West, the room runs on beyond your light. Ways lead north and west.",
    18640: "The passage enters a small room. Against the north wall stands a statue of a lantern-bearer, finely made, one arm raised to hold a light that is no longer there. Ways lead east and south.",
    18641: "Banners hang along this passage, their colours still good, and between them painted panels of the watches that trained here. Someone has kept this part up. The hallway runs east and west.",
    18642: "The hall opens into a wide room under a high dome. A stair climbs to a balcony open to the sky. The room continues south, and a hallway leaves to the west.",
    18643: "A balcony curving round the outside of the dome. From its northern end you can see across the wide fields to where the land goes grey: on a clear day that is haze, and on other days it is not. The balcony runs south; a stair goes down.",
    18644: "A clean, well-kept hallway, the floor inlaid with a lantern in pale stone. After the passages to the south it is like stepping into another building. A door leads south; the hallway runs north.",
    18645: "A balcony curving round the outside of the dome. From its southern end you look down on Garathorm: the roofs, the Temple, and at dusk the lanterns being lit one street at a time. The balcony runs north; a stair goes down.",
    18646: "A clean, well-kept hallway, the floor inlaid with a lantern in pale stone. After the passage to the west it is like stepping into another building. A door leads west; the hallway runs east.",
    18647: "The hall opens into a wide room under a high dome. A stair climbs to a balcony open to the sky. The room continues north; ways also lead south and west.",
}

# what a room, a creature or a thing is called, where the old name spoke of "newbies" (the owner kept
# the renames, 9 November). A creature's `name` is the word a player types to find it.
ROOM_NAMES = {18600: 'The Arch Of The Proving Halls'}
MOB_NAMES = {
    18602: ('shambler', 'the shambler'),
    18604: ('guard', 'the watch-house guard'),
    18605: ('alchemist', 'the watch-house alchemist'),
    18607: ('novice', 'the mist-taken novice'),
    18609: ('minotaur', 'the massive minotaur'),
    18611: ('novice', 'the boastful novice'),
    18612: ('novice', 'the lost-looking novice'),
    18613: ('novice', 'the talkative novice'),
    18614: ('novice', 'the wandering novice'),
    18615: ('novice', 'the steady novice'),
}


def thing_text(text):
    """A thing's words without "newbie": "a shiny newbie sword" -> "a novice's shiny sword"."""
    import re
    if not isinstance(text, str):
        return text
    text = re.sub(r"\b([Aa]n?|[Ss]ome) ((?:[\w-]+ ){0,2})newbie (\w)", lambda m: f"{'A' if m.group(1)[0].isupper() else 'a'} novice's {m.group(2)}{m.group(3)}"
                  if m.group(1).lower() in ('a', 'an') else f"{m.group(1)} novice's {m.group(2)}{m.group(3)}", text)
    return re.sub(r"\bnewbie\b", "novice's", re.sub(r"\bNewbie\b", "Novice's", text))


# a creature's line in the room (its name and numbers are not touched)
MOBS = {
    18601: "A big, heavy-jawed pit-beast stands here, sizing you up.",
    18602: "A shambling thing stands here, looking about as if it has forgotten what it came for.",
    18603: "A baby dragon, someone's pet got loose, is sniffing about here.",
    18604: "A guard of the watch-house is here, looking for the dragon that got out.",
    18605: "The alchemist is here, bent over something that has not worked yet.",
    18606: "A small crawling thing scuttles along the floor at your feet.",
    18607: "A gaunt figure in a novice's coat stands here. The mist has had this one: there is nobody behind the eyes.",
    18608: "A small imp-like thing, a quasit perhaps, is sneaking about here.",
    18609: "A massive minotaur stands here, considering what you will taste like.",
    18610: "A dark spectre keeps to the shadows here.",
    18611: "A novice is here, pleased with himself and eager to tell you why.",
    18612: "A novice is here, turning a map round and round.",
    18613: "A novice is here, talking, whether or not anyone is listening.",
    18614: "A novice is here, wandering with no clear idea of where.",
    18615: "A novice is here who looks as if he knows what he is about.",
}


def main():
    with open(PATH, encoding='utf-8') as f:
        raw = f.read()
    zone = json.loads(raw)
    rooms, mobs = zone['rooms'], zone['mobs']
    missing = [v for v in rooms if int(v) not in ROOMS] + [f'mob {v}' for v in mobs if int(v) not in MOBS]
    extra = [v for v in ROOMS if str(v) not in rooms] + [f'mob {v}' for v in MOBS if str(v) not in mobs]
    if missing or extra:
        print(f'not covered: {missing}; not in the zone: {extra}', file=sys.stderr)
        return 1
    if '--check' in sys.argv:
        print(f'ok: {len(ROOMS)} rooms, {len(MOBS)} creatures')
        return 0
    for v, text in ROOMS.items():
        rooms[str(v)]['description'] = text
    for v, text in MOBS.items():
        mobs[str(v)]['long_desc'] = text
    for v, name in ROOM_NAMES.items():
        rooms[str(v)]['name'] = name
    for v, (name, short) in MOB_NAMES.items():
        mobs[str(v)]['name'], mobs[str(v)]['short_desc'] = name, short
    for obj in (zone.get('objects') or {}).values():
        for k in ('short_desc', 'room_desc', 'long_desc', 'description'):
            if k in obj:
                obj[k] = thing_text(obj[k])
    # written the way the zone files are (one space a level, the letters as they are, a last
    # newline), so the change is its words alone; a file in another format is left as it is
    if json.dumps(json.loads(raw), indent=1, ensure_ascii=False) + '\n' != raw:
        print('the zone file is not in the usual format: not rewritten', file=sys.stderr)
        return 1
    with open(PATH, 'w', encoding='utf-8', newline='\n') as f:
        f.write(json.dumps(zone, indent=1, ensure_ascii=False) + '\n')
    print(f'rewrote {len(ROOMS)} rooms and {len(MOBS)} creatures')
    return 0


if __name__ == '__main__':
    sys.exit(main())
