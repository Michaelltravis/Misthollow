// The few helpers the shared scripts (shared/roomgen.js, parser.js) expect from the retired
// Phaser client's sprites.js / scene.js. Classic script, loaded before them.
(() => {
  const MH = window.MH = window.MH || {};
  // the 3D client asks for its zone's rooms plus the occupants of every room near the hero
  MH.mapMode = 'near';
  // real-time combat (action_combat.py), on unless Settings turned it off
  MH.combatMode = (() => { try { return localStorage.getItem('mh3d_combat') === 'rounds' ? null : 'action'; } catch (_) { return 'action'; } })();
  MH.mulberry32 = MH.mulberry32 || function (seed) {
    let a = seed >>> 0;
    return function () {
      a |= 0; a = (a + 0x6D2B79F5) | 0;
      let t = Math.imul(a ^ (a >>> 15), 1 | a);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  };
  // sectors, and the looks the server gives rooms (room_looks.py: a cave that was typed 'inside')
  const THEMES = ['inside', 'city', 'dungeon', 'cave', 'forest', 'field', 'hills', 'mountain', 'desert',
    'swamp', 'water_swim', 'water_noswim', 'underwater', 'flying', 'default',
    'mine', 'crypt', 'sewer', 'snow', 'shore', 'volcanic', 'web', 'castle', 'necropolis', 'stones', 'village', 'camp', 'garden', 'ruins', 'terrace', 'ice_cave', 'lava_cave', 'drow'];
  MH.themeForSector = MH.themeForSector || (s => THEMES.includes(s) ? s : 'default');
  MH.hashStr = MH.hashStr || function (s) {
    let h = 2166136261;
    for (const ch of String(s)) h = Math.imul(h ^ ch.charCodeAt(0), 16777619);
    return h >>> 0;
  };
  // the word the MUD matches a creature by ("the old grey wolf" -> "wolf")
  MH.mobKeyword = MH.mobKeyword || function (name) {
    const words = String(name || '').toLowerCase().replace(/[^a-z' ]/g, '').split(/\s+/)
      .filter(w => w && !['a', 'an', 'the', 'some', 'of'].includes(w));
    return words[words.length - 1] || 'mob';
  };
})();
