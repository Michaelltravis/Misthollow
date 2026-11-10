// Misthollow: room vnum -> level layout. Two generators share this file:
//   generateRoom        - legacy side-view platformer chamber (?view=side)
//   generateRoomTopDown - Zelda-style top-down screen (the default view)
// Misthollow platformer: room vnum -> platforming chamber layout.
// Pure and deterministic: the same room always generates the same level.
// Side-view exit mapping:
//   east/west -> gaps in the right/left walls at floor level
//   north     -> background arched doorway (press W while overlapping)
//   south     -> foreground floor hatch (press S while overlapping)
//   up        -> ladder to an opening in the ceiling
//   down      -> grated trapdoor in the floor (press S on it)
(() => {
  const MH = window.MH = window.MH || {};
  const W = 60, H = 34, T = 16;

  const EMPTY = 0, SOLID = 1, PLAT = 2, LADDER = 3, WATER = 4;
  MH.CELL = { EMPTY, SOLID, PLAT, LADDER, WATER };

  function smoothHeightmap(rng, base, amp, step) {
    const hm = new Array(W);
    let y = base;
    for (let x = 0; x < W; x++) {
      if (x % step === 0 && x > 0) {
        y += Math.round((rng() - 0.5) * 2 * amp);
        y = Math.max(base - amp - 1, Math.min(base + 2, y));
      }
      hm[x] = y;
    }
    // flatten the outermost columns so wall exits line up with the floor
    for (let x = 0; x < 6; x++) { hm[x] = hm[6]; hm[W - 1 - x] = hm[W - 7]; }
    return hm;
  }

  MH.generateRoom = function generateRoom(roomData) {
    const vnum = Number(roomData.vnum) || 0;
    const sector = MH.themeForSector(roomData.sector || 'default');
    const rng = MH.mulberry32((vnum * 2654435761) >>> 0);
    const exits = roomData.exits || {};
    const has = dir => Object.prototype.hasOwnProperty.call(exits, dir);
    const flags = roomData.flags || [];

    const theme = sector;
    const grid = new Uint8Array(W * H);
    const at = (x, y) => grid[y * W + x];
    const set = (x, y, v) => { if (x >= 0 && x < W && y >= 0 && y < H) grid[y * W + x] = v; };

    // --- floor heightmap by terrain feel ---
    let base = 28, amp = 0, step = 6;
    if (sector === 'field' || sector === 'forest' || sector === 'swamp') { amp = 2; step = 7; }
    else if (sector === 'hills') { amp = 3; step = 6; }
    else if (sector === 'mountain') { amp = 4; step = 5; }
    const hm = smoothHeightmap(rng, base, amp, step);

    for (let x = 0; x < W; x++) {
      for (let y = hm[x]; y < H; y++) set(x, y, SOLID);
    }

    // --- water pool for watery sectors ---
    const isUnderwater = sector === 'underwater';
    let pool = null;
    if (!isUnderwater && (sector === 'water_swim' || sector === 'water_noswim' || sector === 'swamp')) {
      const px0 = 20 + Math.floor(rng() * 8);
      const px1 = px0 + 12 + Math.floor(rng() * 8);
      pool = { x0: px0, x1: px1 };
      for (let x = px0; x <= px1; x++) {
        const top = hm[x];
        for (let y = top; y < Math.min(H, top + 4); y++) set(x, y, WATER);
        for (let y = top + 4; y < H; y++) set(x, y, SOLID);
      }
    }
    if (isUnderwater) {
      for (let x = 0; x < W; x++) for (let y = 2; y < hm[x]; y++) if (at(x, y) === EMPTY) set(x, y, WATER);
    }

    // --- ceiling ---
    for (let x = 0; x < W; x++) { set(x, 0, SOLID); set(x, 1, SOLID); }

    // --- side walls with exit gaps ---
    const gapFor = x => {
      const fy = hm[x];
      return { y0: fy - 5, y1: fy - 1 };
    };
    const eastGap = has('east') ? gapFor(W - 3) : null;
    const westGap = has('west') ? gapFor(2) : null;
    for (let y = 2; y < H; y++) {
      if (!westGap || y < westGap.y0 || y > westGap.y1) { set(0, y, SOLID); set(1, y, SOLID); }
      if (!eastGap || y < eastGap.y0 || y > eastGap.y1) { set(W - 1, y, SOLID); set(W - 2, y, SOLID); }
    }
    // keep gap floors solid
    if (westGap) for (let x = 0; x < 2; x++) for (let y = hm[2]; y < H; y++) set(x, y, SOLID);
    if (eastGap) for (let x = W - 2; x < W; x++) for (let y = hm[W - 3]; y < H; y++) set(x, y, SOLID);

    // --- up exit: ladder + ceiling opening ---
    let ladder = null;
    if (has('up')) {
      const lx = 40 + Math.floor(rng() * 8);
      set(lx, 0, EMPTY); set(lx, 1, EMPTY); set(lx + 1, 0, EMPTY); set(lx + 1, 1, EMPTY);
      for (let y = 2; y < hm[lx]; y++) set(lx, y, LADDER);
      ladder = { x: lx, topY: 0, bottomY: hm[lx] - 1 };
    }

    // --- down exit: trapdoor in floor ---
    let trapdoor = null;
    if (has('down')) {
      let tx = 14 + Math.floor(rng() * 10);
      if (pool && tx >= pool.x0 - 2 && tx <= pool.x1 + 2) tx = pool.x1 + 4;
      trapdoor = { x: tx, y: hm[tx] };
    }

    // --- north / south background-foreground doors ---
    const doorAt = frac => {
      let dx = Math.floor(W * frac);
      if (pool && dx >= pool.x0 - 1 && dx <= pool.x1 + 1) dx = pool.x0 - 4;
      return { x: dx, y: hm[dx] };
    };
    const northDoor = has('north') ? doorAt(0.62) : null;
    const southDoor = has('south') ? doorAt(0.38) : null;

    // non-cardinal exits (gate/arch/portal/...) become shimmering portals
    const CARDINALS = ['north', 'south', 'east', 'west', 'up', 'down'];
    const portals = [];
    const portalNames = Object.keys(exits).filter(d => !CARDINALS.includes(d));
    portalNames.forEach((name, i) => {
      const spot = doorAt(0.25 + (i * 0.5) / Math.max(1, portalNames.length));
      // nudge off the cardinal doors
      let px = spot.x;
      if (southDoor && Math.abs(px - southDoor.x) < 4) px += 5;
      if (northDoor && Math.abs(px - northDoor.x) < 4) px -= 5;
      px = Math.max(5, Math.min(W - 6, px));
      portals.push({ name, x: px, y: hm[px] });
    });

    // --- one-way platforms in the air band ---
    const platforms = [];
    const nPlats = 2 + Math.floor(rng() * 3);
    for (let i = 0; i < nPlats; i++) {
      const pw = 4 + Math.floor(rng() * 5);
      const px = 6 + Math.floor(rng() * (W - 14 - pw));
      const py = 15 + Math.floor(rng() * 9);
      // skip if it would sit inside terrain or block the ladder column
      if (py >= hm[px] - 2 || py >= hm[px + pw] - 2) continue;
      if (ladder && px <= ladder.x + 1 && px + pw >= ladder.x - 1) continue;
      let clear = true;
      for (let x = px; x < px + pw; x++) if (at(x, py) !== EMPTY && at(x, py) !== WATER) { clear = false; break; }
      if (!clear) continue;
      for (let x = px; x < px + pw; x++) set(x, py, PLAT);
      platforms.push({ x: px, y: py, w: pw });
    }

    // --- props on the floor ---
    const props = [];
    const nProps = 2 + Math.floor(rng() * 4);
    for (let i = 0; i < nProps; i++) {
      let px = 5 + Math.floor(rng() * (W - 10));
      if (pool && px >= pool.x0 - 1 && px <= pool.x1 + 1) continue;
      if (northDoor && Math.abs(px - northDoor.x) < 3) continue;
      if (southDoor && Math.abs(px - southDoor.x) < 3) continue;
      if (trapdoor && Math.abs(px - trapdoor.x) < 3) continue;
      props.push({ idx: Math.floor(rng() * 3), x: px, y: hm[px] });
    }

    // --- deterministic spawn slots along the floor ---
    const spawnSlots = [];
    for (let i = 0; i < 8; i++) {
      let sx = 8 + Math.floor(((i + 0.5) / 8) * (W - 16));
      if (pool && sx >= pool.x0 && sx <= pool.x1) sx = pool.x0 - 2 - (i % 3);
      spawnSlots.push({ x: sx * T + T / 2, y: (hm[sx] - 1) * T });
    }

    // --- entry points: where the player appears arriving FROM a direction ---
    const floorPx = x => ({ x: x * T + T / 2, y: (hm[x] - 2) * T });
    const entries = {
      west: floorPx(4),                 // came in heading east? no: entered THROUGH west wall
      east: floorPx(W - 5),
      north: northDoor ? floorPx(northDoor.x) : floorPx(Math.floor(W / 2)),
      south: southDoor ? floorPx(southDoor.x) : floorPx(Math.floor(W / 2)),
      up: trapdoor ? floorPx(trapdoor.x) : floorPx(Math.floor(W / 2)),     // arrived going up => appear at trapdoor
      down: ladder ? floorPx(ladder.x) : floorPx(Math.floor(W / 2)),      // arrived going down => appear at ladder top area
      none: floorPx(Math.floor(W / 2)),
    };

    return {
      vnum, theme, sector, flags,
      description: roomData.description || '',
      gravestones: roomData.gravestones,   // server-shared memorials, if provided
      W, H, T,
      grid, hm,
      pool, isUnderwater,
      lowGravity: sector === 'flying',
      dark: flags.includes('dark'),
      peaceful: flags.includes('peaceful'),
      eastGap, westGap, ladder, trapdoor, northDoor, southDoor, portals,
      platforms, props, spawnSlots, entries,
      exits,
      pxW: W * T, pxH: H * T,
    };
  };
})();

// ===================== Zelda-style top-down generator =====================
// One MUD room = one screen. The four cardinal exits are gaps in the border
// ring; up/down are staircase tiles; named passages are portal tiles.
(() => {
  const MH = window.MH = window.MH || {};
  // a roomy tactical chamber: enough grid that the world reads as a space with
  // unit-sized actors (Aether Grid feel), not a cramped close-up.
  const W = 24, H = 15, T = 16;
  const FLOOR = 0, BLOCK = 1, WATER = 4;
  MH.TD = { W, H, T, FLOOR, BLOCK, WATER };

  function floodReachable(grid, sx, sy, swim = false) {
    const seen = new Uint8Array(W * H);
    const q = [[sx, sy]];
    seen[sy * W + sx] = 1;
    while (q.length) {
      const [x, y] = q.pop();
      for (const [dx, dy] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) {
        const nx = x + dx, ny = y + dy;
        if (nx < 0 || ny < 0 || nx >= W || ny >= H) continue;
        const i = ny * W + nx;
        if (seen[i] || grid[i] === BLOCK || (grid[i] === WATER && !swim)) continue;
        seen[i] = 1;
        q.push([nx, ny]);
      }
    }
    return seen;
  }

  // A zone whose theme is ENCLOSED (sewers, mines, crypts, drow tunnels...) is
  // underground whatever its rooms' old sector tags say: the stock sewer zones tag
  // most rooms forest/field/mountain/city, which grew canopy, deer and daylight in a
  // sewer (first real playtest). Outdoor sector themes are mapped to 'dungeon'.
  const OUTDOOR_THEMES = new Set(['forest', 'field', 'hills', 'mountain', 'city', 'default', 'desert']);
  MH.roomTheme = function roomTheme(roomData) {
    // the server's look comes first (room_looks.py: it read the room's words and its neighbours)
    const look = roomData.look && MH.themeForSector(roomData.look);
    if (look && look !== 'default') return look;
    const sector = MH.themeForSector(roomData.sector || 'default');
    const zk = MH.zoneThemeKey ? MH.zoneThemeKey(roomData.zone) : null;
    const zt = zk && MH.ZONE_THEMES ? MH.ZONE_THEMES[zk] : null;
    if (zt && zt.light && zt.light.enclosed && OUTDOOR_THEMES.has(sector)) return 'dungeon';
    return sector;
  };

  MH.generateRoomTopDown = function generateRoomTopDown(roomData) {
    const vnum = Number(roomData.vnum) || 0;
    const sector = MH.roomTheme(roomData);
    const rng = MH.mulberry32(((vnum * 2654435761) ^ 0x5eada) >>> 0);
    const exits = roomData.exits || {};
    const has = dir => Object.prototype.hasOwnProperty.call(exits, dir);
    const flags = roomData.flags || [];
    // a water room is open water you cross (in a boat, or swimming: the server says who may enter)
    const waterRoom = sector === 'water_swim' || sector === 'water_noswim';
    const swim = sector === 'underwater' || waterRoom;

    const grid = new Uint8Array(W * H); // FLOOR
    const at = (x, y) => grid[y * W + x];
    const set = (x, y, v) => { if (x >= 0 && y >= 0 && x < W && y < H) grid[y * W + x] = v; };

    // border ring with edge gaps where exits exist
    for (let x = 0; x < W; x++) { set(x, 0, BLOCK); set(x, H - 1, BLOCK); }
    for (let y = 0; y < H; y++) { set(0, y, BLOCK); set(W - 1, y, BLOCK); }
    const midX = Math.floor(W / 2), midY = Math.floor(H / 2);
    const gaps = {};
    // REBUILD phase 2 ("movement between rooms is clunky"): openings are WIDE — 7 tiles
    // on the long walls, 5 on the short ones — so leaving a room is walking on, not
    // threading a 3-tile door in the wall middle. Both sides of a shared wall use the
    // same centred span, so neighbours still line up.
    const GX = 3, GY = 2;
    if (has('north')) { gaps.north = { x0: midX - GX, x1: midX + GX }; for (let x = midX - GX; x <= midX + GX; x++) set(x, 0, FLOOR); }
    if (has('south')) { gaps.south = { x0: midX - GX, x1: midX + GX }; for (let x = midX - GX; x <= midX + GX; x++) set(x, H - 1, FLOOR); }
    if (has('west'))  { gaps.west  = { y0: midY - GY, y1: midY + GY }; for (let y = midY - GY; y <= midY + GY; y++) set(0, y, FLOOR); }
    if (has('east'))  { gaps.east  = { y0: midY - GY, y1: midY + GY }; for (let y = midY - GY; y <= midY + GY; y++) set(W - 1, y, FLOOR); }
    // Two outdoor rooms side by side that open onto each other (exit kind 'open', no door) share
    // their whole side: no ring and no treeline band between them, so the country runs on
    // (the client passes each exit's kind and the neighbour's look)
    const OUTDOOR_LOOKS = new Set(['forest', 'darkforest', 'web', 'field', 'hills', 'mountain', 'desert', 'snow', 'swamp', 'shore', 'volcanic', 'stones', 'village', 'camp', 'garden', 'ruins', 'terrace',
      'water_swim', 'water_noswim']);
    const WATERS = new Set(['water_swim', 'water_noswim']);
    const wide = {};
    for (const d of ['north', 'south', 'east', 'west']) {
      const e = exits[d];
      // (the Chessboard's squares, too: the board is one floor, its squares running into each other)
      const board = !!e && sector === 'chessboard' && e.nlook === 'chessboard';
      if (!e || e.kind !== 'open' || e.door || (!board && (!OUTDOOR_LOOKS.has(sector) || !OUTDOOR_LOOKS.has(MH.themeForSector(e.nlook || ''))))) continue;
      // water opens onto water; land onto land (a shore between them is the bank, below)
      if (WATERS.has(sector) !== WATERS.has(MH.themeForSector(e.nlook || ''))) continue;
      wide[d] = true;
      if (d === 'north' || d === 'south') {
        gaps[d] = { x0: 1, x1: W - 2 };
        for (let x = 1; x < W - 1; x++) set(x, d === 'north' ? 0 : H - 1, FLOOR);
      } else {
        gaps[d] = { y0: 1, y1: H - 2 };
        for (let y = 1; y < H - 1; y++) set(d === 'west' ? 0 : W - 1, y, FLOOR);
      }
    }
    // where two of the board's open sides meet, the corner opens too (else a stub of the ring
    // stands where four squares meet)
    if (sector === 'chessboard') {
      for (const [x, y, a, b] of [[0, 0, 'north', 'west'], [W - 1, 0, 'north', 'east'], [0, H - 1, 'south', 'west'], [W - 1, H - 1, 'south', 'east']]) {
        if (wide[a] && wide[b]) set(x, y, FLOOR);
      }
    }

    // ---- Phase 3: biome-shaped rooms ------------------------------------
    // Every room used to be the same rectangle. Now the border grows into the
    // room organically per biome (noise treelines in the wilds, cellular
    // caverns underground), and the prose can carve real terrain (a stream, a
    // pond). All shaped cells are tracked so connectivity failures revert.
    const organic = [];
    const midX0 = Math.floor(W / 2), midY0 = Math.floor(H / 2);
    // lanes + gap mouths stay clear so holding a direction always exits
    const laneSafe = (x, y) =>
      (((gaps.east || gaps.west) && Math.abs(y - midY0) <= GY)
        || ((gaps.north || gaps.south) && Math.abs(x - midX0) <= GX)
        || (gaps.north && y <= 3 && Math.abs(x - midX0) <= GX + 1)
        || (gaps.south && y >= H - 4 && Math.abs(x - midX0) <= GX + 1)
        || (gaps.west && x <= 3 && Math.abs(y - midY0) <= GY + 1)
        || (gaps.east && x >= W - 4 && Math.abs(y - midY0) <= GY + 1));
    const carve = (x, y, v) => {
      if (x < 1 || y < 1 || x >= W - 1 || y >= H - 1) return;
      if (laneSafe(x, y) || at(x, y) !== FLOOR) return;
      set(x, y, v);
      organic.push([x, y]);
    };
    const SHAPE = {
      forest: 3, darkforest: 3, web: 3, swamp: 3, hills: 2, field: 2, desert: 2, snow: 2, shore: 2, volcanic: 2, stones: 2, village: 2, camp: 2, garden: 2, ruins: 2,
      cave: 'cavern', mine: 'cavern', ice_cave: 'cavern', lava_cave: 'cavern', mountain: 'cavern', underground: 'cavern',
    }[sector];
    if (typeof SHAPE === 'number' && !swim) {
      // organic border: each side's thickness wanders 0..maxD like a treeline
      const maxD = SHAPE;
      const walk = () => { let d = 1 + Math.floor(rng() * maxD); return () => { d += Math.floor(rng() * 3) - 1; d = Math.max(0, Math.min(maxD, d)); return d; }; };
      const dn = walk(), ds = walk(), dw = walk(), de = walk();
      for (let x = 1; x < W - 1; x++) {
        const d1 = dn(); if (!wide.north) for (let y = 1; y <= d1; y++) carve(x, y, BLOCK);
        const d2 = ds(); if (!wide.south) for (let y = H - 2; y >= H - 1 - d2; y--) carve(x, y, BLOCK);
      }
      for (let y = 1; y < H - 1; y++) {
        const d1 = dw(); if (!wide.west) for (let x = 1; x <= d1; x++) carve(x, y, BLOCK);
        const d2 = de(); if (!wide.east) for (let x = W - 2; x >= W - 1 - d2; x--) carve(x, y, BLOCK);
      }
    } else if (SHAPE === 'cavern' && !swim) {
      // cellular-automata rubble: caves stop being tidy rectangles
      const tmp = new Uint8Array(W * H);
      for (let y = 2; y < H - 2; y++) for (let x = 2; x < W - 2; x++) {
        if (!laneSafe(x, y) && rng() < 0.24) tmp[y * W + x] = 1;
      }
      for (let pass = 0; pass < 2; pass++) {
        const nxt = new Uint8Array(tmp);
        for (let y = 2; y < H - 2; y++) for (let x = 2; x < W - 2; x++) {
          let n = 0;
          for (let dy = -1; dy <= 1; dy++) for (let dx = -1; dx <= 1; dx++) {
            if (!dx && !dy) continue;
            const xx = x + dx, yy = y + dy;
            if (xx < 1 || yy < 1 || xx >= W - 1 || yy >= H - 1 || tmp[yy * W + xx]) n++;
          }
          nxt[y * W + x] = n >= 5 ? 1 : (n <= 2 ? 0 : tmp[y * W + x]);
        }
        tmp.set(nxt);
      }
      for (let y = 2; y < H - 2; y++) for (let x = 2; x < W - 2; x++) {
        if (tmp[y * W + x]) carve(x, y, BLOCK);
      }
    }
    // prose-carved terrain: the description reshapes the ground
    const prose = `${roomData.name || ''} ${roomData.description || ''}`.toLowerCase();
    const proseFx = {
      mossy: /\bmoss|overgrown|ivy|vines?\b/.test(prose),
      snowy: /\bsnow|frozen|icy|frost\b/.test(prose),
    };
    if (sector === 'shore') {
      // the water's edge along a side with no way through (south first), wavy, a few tiles deep
      const side = ['south', 'north', 'east', 'west'].find(d => !gaps[d]) || 'south';
      let d = 2;
      const len = side === 'south' || side === 'north' ? W : H;
      // (over the shaped edge too: the sea comes right up to the room's side)
      const wet = (x, y) => { if (!laneSafe(x, y) && x > 0 && y > 0 && x < W - 1 && y < H - 1) { set(x, y, WATER); organic.push([x, y]); } };
      for (let i = 1; i < len - 1; i++) {
        d += Math.floor(rng() * 3) - 1; d = Math.max(3, Math.min(5, d));
        for (let k = 1; k <= d; k++) {
          if (side === 'south') wet(i, H - 1 - k);
          else if (side === 'north') wet(i, k);
          else if (side === 'east') wet(W - 1 - k, i);
          else wet(k, i);
        }
      }
    } else if (sector === 'swamp' && !swim) {
      // black pools among the reeds
      for (let p = 0; p < 3; p++) {
        const cx = 4 + Math.floor(rng() * (W - 8)), cy = 3 + Math.floor(rng() * (H - 6));
        const rx = 1.5 + rng() * 1.5, ry = 1 + rng();
        for (let y = cy - 2; y <= cy + 2; y++) for (let x = cx - 3; x <= cx + 3; x++) {
          if (Math.hypot((x - cx) / rx, (y - cy) / ry) <= 1) carve(x, y, WATER);
        }
      }
    } else if (sector === 'sewer') {
      // a straight channel of foul water the length of the room, with dry crossings where the
      // ways through cross it (a sewer is built: no winding)
      const y0 = 3 + Math.floor(rng() * 2);
      for (let x = 1; x < W - 1; x++) {
        if (Math.abs(x - midX0) <= GX) continue;
        carve(x, y0, WATER); carve(x, y0 + 1, WATER);
      }
    } else if (!swim && /\b(stream|river|brook|creek)\b/.test(prose)) {
      // a winding ribbon of water along one third of the room; lane crossings
      // stay dry and read as natural fords
      const vertical = rng() < 0.5;
      if (vertical) {
        let x = 4 + Math.floor(rng() * 3);
        for (let y = 1; y < H - 1; y++) {
          if (Math.abs(y - midY0) <= GY) continue;   // the ford: always crossable
          x += Math.floor(rng() * 3) - 1; x = Math.max(3, Math.min(8, x));
          carve(x, y, WATER); if (rng() < 0.6) carve(x + 1, y, WATER);
        }
      } else {
        let y = 3 + Math.floor(rng() * 2);
        for (let x = 1; x < W - 1; x++) {
          if (Math.abs(x - midX0) <= GX) continue;   // the ford: always crossable
          y += Math.floor(rng() * 3) - 1; y = Math.max(2, Math.min(5, y));
          carve(x, y, WATER); if (rng() < 0.6) carve(x, y + 1, WATER);
        }
      }
    } else if (!swim && sector !== 'water_noswim' && /\b(pond|pool|lake|spring)\b/.test(prose)) {
      const cx = midX0 + Math.floor(rng() * 6) - 3, cy = midY0 + Math.floor(rng() * 4) - 2;
      for (let y = cy - 2; y <= cy + 2; y++) for (let x = cx - 3; x <= cx + 3; x++) {
        const d = Math.hypot((x - cx) / 3.2, (y - cy) / 2.2);
        if (d <= 1) carve(x, y, WATER);
      }
    }

    // staircase / portal feature tiles
    const stairsUp = has('up') ? { x: W - 8, y: 4 } : null;
    const stairsDown = has('down') ? { x: 7, y: 4 } : null;
    const CARDINALS = ['north', 'south', 'east', 'west', 'up', 'down'];
    const portalNames = Object.keys(exits).filter(d => !CARDINALS.includes(d));
    const portals = portalNames.map((name, i) => ({
      name, x: 9 + ((i * 7) % (W - 18)), y: H - 5,
    }));

    // a water room is water from bank to bank: every open tile, and its ways out onto more water
    if (waterRoom) {
      for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) if (at(x, y) === FLOOR) set(x, y, WATER);
    }
    // and past its edge the sea runs on: the ring of a side that is not land (zone.js, edges.js
    // landSides) is drawn as water, not as a bank of rocks; still BLOCK, so no boat leaves that way
    const deep = [];
    if (waterRoom) {
      const land = roomData.land || {};
      for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
        if (at(x, y) !== BLOCK || (x > 0 && y > 0 && x < W - 1 && y < H - 1)) continue;
        const sides = [y === 0 && 'north', y === H - 1 && 'south', x === 0 && 'west', x === W - 1 && 'east'].filter(Boolean);
        if (!sides.some(s => land[s])) deep.push(y * W + x);
      }
    }

    // points of interest that must stay mutually reachable
    const pois = [];
    if (gaps.north) pois.push([midX, 1]);
    if (gaps.south) pois.push([midX, H - 2]);
    if (gaps.west) pois.push([1, midY]);
    if (gaps.east) pois.push([W - 2, midY]);
    if (stairsUp) pois.push([stairsUp.x, stairsUp.y]);
    if (stairsDown) pois.push([stairsDown.x, stairsDown.y]);
    portals.forEach(p => pois.push([p.x, p.y]));
    pois.push([midX, midY]);

    // entry tiles are POIs too: the player materializes there, so nothing
    // may block them and they must stay reachable
    const px = (x, y) => ({ x: x * T + T / 2, y: y * T + T / 2 });
    const entries = {
      north: px(midX, 1.6),
      south: px(midX, H - 2.6),
      west: px(1.6, midY),
      east: px(W - 2.6, midY),
      up: stairsDown ? px(stairsDown.x + 1.4, stairsDown.y) : px(midX, midY),
      down: stairsUp ? px(stairsUp.x - 1.4, stairsUp.y) : px(midX, midY),
      none: px(midX, midY),
    };
    for (const p of portals) entries[p.name] = px(midX, midY);
    for (const e of Object.values(entries)) {
      pois.push([Math.floor(e.x / T), Math.floor(e.y / T)]);
    }

    // clear a small disc around every POI the shaping/pond may have swallowed
    // (stairs, portals, entries must stay open and walkable)
    pois.forEach(([x, y]) => {
      for (let dy = -1; dy <= 1; dy++) {
        for (let dx = -1; dx <= 1; dx++) {
          const xx = x + dx, yy = y + dy;
          // (in a water room, open water is the way: only what blocks is cleared, to water)
          if (xx > 0 && yy > 0 && xx < W - 1 && yy < H - 1 && at(xx, yy) !== FLOOR && !(waterRoom && at(xx, yy) === WATER)) set(xx, yy, waterRoom ? WATER : FLOOR);
        }
      }
    });

    const allReachable = () => {
      const seen = floodReachable(grid, midX, midY, swim);
      return pois.every(([x, y]) => seen[y * W + x]);
    };
    if (!allReachable()) {
      // the biome shaping / stream / pond cut something off: revert it all
      for (const [x, y] of organic) set(x, y, FLOOR);
      for (let i = 0; i < grid.length; i++) if (grid[i] === WATER) grid[i] = FLOOR;
    }

    // ---- what the room's words say stands in it (room_features.py): standing stones, altars,
    // stakes, banners... each on open floor off the lanes, never on a way in or out; the big ones
    // block (kept only while every way through stays reachable), the small lie where they fall.
    // `edge` things stand by the walls, `centre` ones out in the open (a room's own centrepiece,
    // the altar of "The First Altar", nearest the middle) ----
    const FEAT = {
      standing_stone: [1, 1, 'edge', true], altar: [2, 1, 'centre', true], statue: [1, 1, 'centre', true], obelisk: [1, 1, 'centre', true],
      pillar: [1, 1, 'edge', true], piling: [1, 1, 'centre', true], well: [2, 2, 'centre', true], fountain: [2, 2, 'centre', true], brazier: [1, 1, 'centre', true],
      tent: [2, 2, 'edge', true], cage: [1, 1, 'edge', true], stake: [1, 1, 'edge', true], pole: [1, 1, 'edge', true],
      banner: [1, 1, 'edge', true], grave: [1, 1, 'edge', true], coffin: [1, 1, 'edge', true], drum: [1, 1, 'centre', true],
      throne: [1, 1, 'centre', true], table: [2, 1, 'centre', true], bench: [1, 1, 'edge', true], shelf: [1, 1, 'edge', true],
      bed: [1, 1, 'edge', true], chest: [1, 1, 'edge', true], barrel: [1, 1, 'edge', true], crate: [1, 1, 'edge', true],
      weapons: [1, 1, 'edge', true], fence: [1, 1, 'edge', true], dead_tree: [1, 1, 'scatter', true], torch: [1, 1, 'edge', true],
      lantern: [1, 1, 'edge', true], chains: [1, 1, 'edge', true], cairn: [1, 1, 'scatter', false], skull: [1, 1, 'scatter', false],
      bones: [1, 1, 'scatter', false], candle: [1, 1, 'scatter', false], rubble: [1, 1, 'scatter', false],
      mushroom: [1, 1, 'scatter', false], flowers: [1, 1, 'scatter', false], crystal: [1, 1, 'scatter', false],
      rug: [2, 2, 'centre', false], blood: [1, 1, 'scatter', false], ash: [1, 1, 'scatter', false], stake_holes: [1, 1, 'scatter', false],
      gate: [2, 1, 'edge', true], tree: [1, 1, 'scatter', true], reeds: [1, 1, 'scatter', false], roots: [1, 1, 'edge', false],
      boat: [2, 1, 'edge', true], mist: [1, 1, 'scatter', false], ice: [1, 1, 'scatter', true], flames: [1, 1, 'scatter', true],
      mirror: [1, 1, 'edge', true], bell: [1, 1, 'centre', true], waterfall: [2, 1, 'edge', true],
    };
    const features = [];
    // (none read from the words where you swim; on the seabed a set piece's, placed by hand: the
    // pilings under the dock, the bones in a lair)
    const featWanted = (roomData.features || []).filter(f => FEAT[f.k] && (!swim || (sector === 'underwater' && f.x != null && f.y != null)));
    if (featWanted.length) {
      const taken = new Set();
      const inLaneCell = (x, y) => ((gaps.east || gaps.west) && Math.abs(y - midY) <= 1) || ((gaps.north || gaps.south) && Math.abs(x - midX) <= 1);
      const nearPoiCell = (x, y) => pois.some(([px, py]) => Math.abs(x - px) <= 1 && Math.abs(y - py) <= 1);
      const nearWall = (x, y) => { for (let dy = -2; dy <= 2; dy++) for (let dx = -2; dx <= 2; dx++) if (at(x + dx, y + dy) === BLOCK) return true; return false; };
      const free = (x, y, w, h, block) => {
        for (let dy = -(block ? 1 : 0); dy < h + (block ? 1 : 0); dy++) for (let dx = -(block ? 1 : 0); dx < w + (block ? 1 : 0); dx++) {
          if (taken.has((y + dy) * W + x + dx)) return false;
        }
        for (let dy = 0; dy < h; dy++) for (let dx = 0; dx < w; dx++) {
          const cx = x + dx, cy = y + dy;
          if (cx < 2 || cy < 2 || cx > W - 3 || cy > H - 3 || at(cx, cy) !== FLOOR || inLaneCell(cx, cy) || nearPoiCell(cx, cy)) return false;
        }
        return true;
      };
      // a set piece (setpieces.py): its things where its maker put them, facing the room's middle
      // (thrones, altars, statues); kept only on open floor that keeps every way out reachable
      // (only what is really used stays clear: the entries of the ways this room has, its stairs
      // and portals, its middle; not the entry of a north wall with no way through it)
      const keepClear = [[midX, midY]];
      for (const d of ['north', 'south', 'west', 'east']) if (gaps[d]) keepClear.push([Math.floor(entries[d].x / T), Math.floor(entries[d].y / T)]);
      if (stairsUp) keepClear.push([stairsUp.x, stairsUp.y]);
      if (stairsDown) keepClear.push([stairsDown.x, stairsDown.y]);
      portals.forEach(p => keepClear.push([p.x, p.y]));
      const nearKept = (x, y) => keepClear.some(([px, py]) => Math.abs(x - px) <= 1 && Math.abs(y - py) <= 1);
      const keptReachable = () => { const seen = floodReachable(grid, midX, midY, swim); return keepClear.every(([x, y]) => seen[y * W + x]); };
      for (const f of featWanted.filter(f => f.x != null && f.y != null)) {
        const [w, h, , block] = FEAT[f.k];
        let ok = true;
        for (let dy = 0; dy < h && ok; dy++) for (let dx = 0; dx < w; dx++) {
          const cx = f.x + dx, cy = f.y + dy;
          if (cx < 1 || cy < 1 || cx > W - 2 || cy > H - 2 || at(cx, cy) !== FLOOR || nearKept(cx, cy) || taken.has(cy * W + cx)) { ok = false; break; }
        }
        if (!ok) continue;
        if (block) {
          for (let dy = 0; dy < h; dy++) for (let dx = 0; dx < w; dx++) set(f.x + dx, f.y + dy, BLOCK);
          if (!keptReachable()) { for (let dy = 0; dy < h; dy++) for (let dx = 0; dx < w; dx++) set(f.x + dx, f.y + dy, FLOOR); continue; }
        }
        for (let dy = 0; dy < h; dy++) for (let dx = 0; dx < w; dx++) taken.add((f.y + dy) * W + f.x + dx);
        const yaw = f.yaw != null ? f.yaw : Math.atan2(midX - (f.x + w / 2), midY - (f.y + h / 2));
        features.push({ k: f.k, x: f.x, y: f.y, w, h, c: f.c || null, main: !!f.main, i: 0, block, yaw, s: f.s || 1 });
      }
      for (const f of featWanted.filter(f => f.x == null || f.y == null)) {
        const [w, h, where0, block] = FEAT[f.k];
        const where = f.main ? 'main' : where0;
        const score = (x, y) => {
          const dc = Math.hypot(x + w / 2 - midX, y + h / 2 - midY);
          if (where === 'main') return Math.abs(dc - 3.5);
          if (where === 'centre') return Math.abs(dc - 4.5) + rng() * 2;
          // (and within the view of one standing in the middle: a room is wider than the camera
          // sees, and a thing by a far wall is lost off the edge or behind the rocks and trees)
          const far = Math.max(0, dc - 5.5) * 1.5;
          if (where === 'edge') return (nearWall(x, y) ? 0 : 4) + rng() * 3 + far;
          return rng() * 6 + far;
        };
        const cands = [];
        for (let y = 2; y < H - 2; y++) for (let x = 2; x < W - 2; x++) if (free(x, y, w, h, block)) cands.push([score(x, y), x, y]);
        cands.sort((a, b) => a[0] - b[0]);
        let placed = 0;
        for (const [, x, y] of cands) {
          if (placed >= (f.n || 1)) break;
          if (!free(x, y, w, h, block)) continue;
          if (block) {
            for (let dy = 0; dy < h; dy++) for (let dx = 0; dx < w; dx++) set(x + dx, y + dy, BLOCK);
            if (!allReachable()) { for (let dy = 0; dy < h; dy++) for (let dx = 0; dx < w; dx++) set(x + dx, y + dy, FLOOR); continue; }
          }
          for (let dy = 0; dy < h; dy++) for (let dx = 0; dx < w; dx++) taken.add((y + dy) * W + x + dx);
          features.push({ k: f.k, x, y, w, h, c: f.c || null, main: !!f.main && placed === 0, i: placed, block, yaw: Math.floor(rng() * 8) * Math.PI / 4, s: 0.85 + rng() * 0.3 });
          placed++;
        }
      }
    }

    // scattered obstacles, kept only when they don't break connectivity (fewer where the words
    // already furnish the room)
    const obstacles = [];
    // (none on the Chessboard: its squares are bare, the pieces are its creatures)
    const tries = sector === 'chessboard' ? 0 : features.length ? 2 : 8 + Math.floor(rng() * 8);
    for (let i = 0; i < tries; i++) {
      const big = rng() < 0.35;
      const ox = 2 + Math.floor(rng() * (W - 5));
      const oy = 2 + Math.floor(rng() * (H - 5));
      const cells = [];
      for (let dy = 0; dy < (big ? 2 : 1); dy++) {
        for (let dx = 0; dx < (big ? 2 : 1); dx++) cells.push([ox + dx, oy + dy]);
      }
      // skip near feature tiles and gap corridors
      const nearPoi = pois.some(([px, py]) => cells.some(([cx, cy]) => Math.abs(cx - px) <= 1 && Math.abs(cy - py) <= 1));
      // keep the straight lanes to each exit clear: holding a direction
      // key must always carry you from the center to the gap (Zelda feel)
      const inLane = cells.some(([cx, cy]) =>
        ((gaps.east || gaps.west) && Math.abs(cy - midY) <= 1) ||
        ((gaps.north || gaps.south) && Math.abs(cx - midX) <= 1));
      if (nearPoi || inLane || cells.some(([cx, cy]) => at(cx, cy) !== FLOOR)) continue;
      cells.forEach(([cx, cy]) => set(cx, cy, BLOCK));
      if (!allReachable()) {
        cells.forEach(([cx, cy]) => set(cx, cy, FLOOR));
        continue;
      }
      obstacles.push({ x: ox, y: oy, big, idx: Math.floor(rng() * 2) });
    }

    // deterministic spawn slots on reachable floor
    const seen = floodReachable(grid, midX, midY, swim);
    const spawnSlots = [];
    let guard = 0;
    while (spawnSlots.length < 8 && guard++ < 300) {
      const sx = 2 + Math.floor(rng() * (W - 4));
      const sy = 2 + Math.floor(rng() * (H - 4));
      if ((at(sx, sy) === FLOOR || (swim && at(sx, sy) === WATER)) && seen[sy * W + sx]) {
        spawnSlots.push({ x: sx * T + T / 2, y: sy * T + T / 2 });
      }
    }
    while (spawnSlots.length < 8) spawnSlots.push({ x: midX * T + T / 2, y: midY * T + T / 2 });

    // decorative props (non-blocking); zone themes get richer, named sets
    const zoneKey = MH.zoneThemeKey ? MH.zoneThemeKey(roomData.zone) : null;
    const zoneTheme = zoneKey && MH.ZONE_THEMES ? MH.ZONE_THEMES[zoneKey] : null;
    const props = [];
    const nProps = zoneTheme ? 5 + Math.floor(rng() * 5) : 3 + Math.floor(rng() * 3);
    for (let i = 0; i < nProps; i++) {
      const px = 2 + Math.floor(rng() * (W - 4));
      const py = 2 + Math.floor(rng() * (H - 4));
      if (at(px, py) === FLOOR && !pois.some(([qx, qy]) => Math.abs(qx - px) <= 1 && Math.abs(qy - py) <= 1)
          && !props.some(p => Math.abs(p.x - px) <= 1 && Math.abs(p.y - py) <= 1)) {
        const prop = { idx: Math.floor(rng() * 3), x: px, y: py };
        if (zoneTheme) {
          // first props lean on the theme's signature pieces, rest random
          const list = zoneTheme.props;
          prop.name = list[i < 2 ? i % list.length : Math.floor(rng() * list.length)];
          prop.scale = 0.8 + rng() * 0.4;
        }
        props.push(prop);
      }
    }

    // frozen terrain (elemental interplay): a frost spell froze this room's
    // water — the ice is WALKABLE, and the painter draws it as an ice sheet
    let icy = false, iceCells = null;
    if (roomData.env && roomData.env.frozen) {
      iceCells = [];
      for (let i = 0; i < grid.length; i++) {
        if (grid[i] === WATER) { grid[i] = FLOOR; iceCells.push(i); }
      }
      icy = iceCells.length > 0;
    }

    return {
      topdown: true,
      icy, iceCells,
      vnum, theme: sector, sector, flags, zoneKey,
      description: roomData.description || '',
      name: roomData.name || '',
      gravestones: roomData.gravestones,
      W, H, T, grid, gaps,
      stairsUp, stairsDown, portals, obstacles, props, spawnSlots, entries, wide, features,
      tone: roomData.tone || null,     // the zone's stone and light, from its rooms' words (zone_tone.py)
      setpiece: roomData.setpiece || null,   // a landmark's own light (setpieces.py)
      mossy: proseFx.mossy, snowy: proseFx.snowy,
      exits, swim, deep, land: roomData.land || {},
      dark: flags.includes('dark'),
      peaceful: flags.includes('peaceful'),
      pxW: W * T, pxH: H * T,
    };
  };
})();
