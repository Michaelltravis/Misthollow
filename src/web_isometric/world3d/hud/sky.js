// The sky dial over the minimap (the owner: "the sun up, sun down messages could be made into an
// icon in the UI"). The sun crosses a half-arc by day, the moon (in its phase) by night; beside it
// the weather over your zone, the season and how warm it is. The server sends the clock and the
// sky when they turn (web_hud.py world_tick) and with every map payload; the old lines ("The sun
// rises...") still come, dimmed in the log. No imports: the pure parts are tested in Node.

export const DAY_START = 6, DAY_END = 20;

// where the sun or the moon stands on the arc: t 0 (rising, left) .. 1 (setting, right)
export function skyBody(hour) {
  const h = ((Number(hour) || 0) % 24 + 24) % 24;
  if (h >= DAY_START && h < DAY_END) return { body: 'sun', t: (h - DAY_START) / (DAY_END - DAY_START) };
  const night = 24 - (DAY_END - DAY_START);
  return { body: 'moon', t: ((h - DAY_END + 24) % 24) / night };
}

// the weather's icon (icons.js PICTO / glyphs.js DRAW names); a clear night shows the moon
export function weatherGlyph(w, night = false) {
  if (!w || !w.sky) return null;
  const p = w.precipitation;
  if (p === 'snow' || p === 'sleet' || w.sky === 'snowy') return 'snow';
  return { clear: night ? 'moon' : 'sun', partly_cloudy: 'cloud', overcast: 'cloud', rainy: 'rain', stormy: 'bolt', foggy: 'smoke' }[w.sky] || 'cloud';
}

// how warm it feels, from degrees Fahrenheit
export function tempBand(f) {
  if (f == null || Number.isNaN(Number(f))) return '';
  const t = Number(f);
  return t <= 25 ? 'frigid' : t <= 45 ? 'cold' : t <= 72 ? 'mild' : t <= 90 ? 'warm' : 'hot';
}

// the moon's phase (0 new .. 0.5 full .. 1 new) in words
export function moonName(phase) {
  const p = ((Number(phase) || 0) % 1 + 1) % 1;
  const names = ['New moon', 'Waxing crescent', 'First quarter', 'Waxing gibbous', 'Full moon', 'Waning gibbous', 'Last quarter', 'Waning crescent'];
  return names[Math.round(p * 8) % 8];
}

// the moon's lit side as an SVG path in a circle of radius r at (0,0): phase 0..1
export function moonPath(phase, r = 6) {
  const p = ((Number(phase) || 0) % 1 + 1) % 1;
  const k = Math.cos(p * 2 * Math.PI);            // 1 new, -1 full: the terminator's bulge
  const waxing = p < 0.5;
  const outer = waxing ? 1 : 0;                  // which half is lit: the right while waxing
  const rx = Math.abs(k) * r;
  const inner = (k > 0) === waxing ? 0 : 1;
  return `M0,${-r} A${r},${r} 0 0 ${outer} 0,${r} A${rx.toFixed(2)},${r} 0 0 ${inner} 0,${-r}Z`;
}

// a point on the dial's arc (width w, height h, from the bottom centre)
export function arcPoint(t, w = 64, h = 26) {
  const a = Math.PI * (1 - Math.max(0, Math.min(1, t)));
  return { x: w / 2 + Math.cos(a) * (w / 2 - 6), y: h - Math.sin(a) * (h - 6) };
}

const PERIOD = { night: 'Night', dawn: 'Dawn', morning: 'Morning', afternoon: 'Afternoon', dusk: 'Dusk', evening: 'Evening' };

// the dial itself, in `el` (the minimap's head): icon(name) gives an image URL (icons.js uiIcon)
export function createSkyDial(el, icon) {
  if (!el) return { set() {} };
  el.classList.add('sky-dial');
  el.innerHTML = `
    <svg class="sky-arc" viewBox="0 0 64 28" width="64" height="28" aria-hidden="true">
      <path class="sky-track" d="M6,26 A26,20 0 0 1 58,26" />
      <line class="sky-horizon" x1="2" y1="26.5" x2="62" y2="26.5" />
      <g class="sky-body"><circle class="sky-sun" r="5" /><g class="sky-moon"><circle class="sky-moon-dark" r="5" /><path class="sky-moon-lit" /></g></g>
    </svg>
    <span class="sky-read"><b class="sky-hour"></b><i class="sky-season"></i></span>
    <span class="sky-weather"><img alt=""><em class="sky-temp"></em></span>`;
  const body = el.querySelector('.sky-body'), lit = el.querySelector('.sky-moon-lit');
  const img = el.querySelector('.sky-weather img');
  let last = { time: null, weather: null }, indoors = false;
  function draw() {
    const t = last.time, w = last.weather;
    if (!t || t.hour == null) { el.classList.add('hidden'); return; }
    el.classList.remove('hidden');
    const b = skyBody(t.hour), at = arcPoint(b.t, 64, 26);
    body.setAttribute('transform', `translate(${at.x.toFixed(1)},${at.y.toFixed(1)})`);
    el.dataset.body = b.body;
    el.dataset.period = t.period || '';
    if (b.body === 'moon') lit.setAttribute('d', moonPath(t.moon, 5));
    el.querySelector('.sky-hour').textContent = `${String(t.hour).padStart(2, '0')}:00`;
    el.querySelector('.sky-season').textContent = t.season || '';
    const g = weatherGlyph(w, b.body === 'moon');
    const wx = el.querySelector('.sky-weather');
    wx.classList.toggle('hidden', !g);
    wx.classList.toggle('indoors', indoors);
    if (g && icon) img.src = icon(g);
    const band = w ? tempBand(w.temperature) : '';
    const temp = el.querySelector('.sky-temp');
    temp.textContent = w && w.temperature != null ? `${Math.round(w.temperature)}°` : '';
    temp.dataset.band = band;
    const lines = [
      `${PERIOD[t.period] || ''} · ${String(t.hour).padStart(2, '0')}:00`,
      [t.month_name, t.season, t.year ? `year ${t.year}` : ''].filter(Boolean).join(' · '),
      b.body === 'moon' ? moonName(t.moon) : '',
      w && w.desc ? (indoors ? `Outside: ${w.desc}` : w.desc) : '',
      w && w.temperature != null ? `${Math.round(w.temperature)}°F, ${band}${w.wind ? ` · wind ${w.wind} mph` : ''}` : '',
    ];
    el.title = lines.filter(Boolean).join('\n');
  }
  return {
    // the clock and the sky: either may come alone (a world_tick carries both, a map payload too)
    set(time, weather) {
      if (time) last.time = time;
      if (weather) last.weather = weather;
      draw();
    },
    // under a roof the weather is greyed out (it is still there, outside)
    setIndoors(v) { if (!!v !== indoors) { indoors = !!v; draw(); } },
  };
}
