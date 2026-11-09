"""The regions of the world (docs/world/WORLD_SPINE.md): which of the nine a zone belongs to.

world/regions.json (written by tools/world/regions_ledger.py) lists each region's name, the line
a traveller reads on entering it, its level band and its zones. /play is told a zone's region with
its map (map_system.build_zonemap), and says it on the banner and the map.

    regions.of(30)  ->  {'id': 'vale', 'name': 'The Lantern Vale', 'line': '...', 'levels': [1, 10]}
    regions.of(12)  ->  None        (the God Rooms are in no region)
"""
import json
import logging
import os

logger = logging.getLogger('Misthollow.Regions')

PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'world', 'regions.json')
_by_zone = None


def load(path=None):
    """Read the regions afresh (None: the world's own file). A missing or broken file is no
    regions at all, and the game runs as it did before there were any."""
    global _by_zone
    _by_zone = {}
    try:
        with open(path or PATH, encoding='utf-8') as f:
            data = json.load(f)
    except (OSError, ValueError) as e:
        logger.warning(f'no regions: {e}')
        return _by_zone
    for r in data.get('regions') or []:
        try:
            pub = {'id': str(r['id']), 'name': str(r['name']), 'line': str(r.get('line') or ''),
                   'levels': [int(x) for x in (r.get('levels') or [])][:2]}
        except (KeyError, TypeError, ValueError):
            logger.warning(f'a region is malformed: {r!r:.80}')
            continue
        for z in r.get('zones') or []:
            try:
                z = int(z)
            except (TypeError, ValueError):
                continue
            if z in _by_zone:
                logger.warning(f'zone {z} is in two regions: {_by_zone[z]["id"]} and {pub["id"]} (the first stands)')
                continue
            _by_zone[z] = pub
    return _by_zone


def of(zone_num):
    """The region a zone is in (None: none)."""
    if _by_zone is None:
        load()
    try:
        return _by_zone.get(int(zone_num))
    except (TypeError, ValueError):
        return None
