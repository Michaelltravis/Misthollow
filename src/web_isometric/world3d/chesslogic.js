// The Chessboard's squares (the 'chessboard' look, terrain-chess.js), without three.js: the
// minimap and the far view colour them too.

// a room's square: 'white', 'black' or null (the board's gate)
export function chessSquare(name) {
  const m = /\b(white|black)\s+square\b/i.exec(name || '');
  return m ? m[1].toLowerCase() : null;
}
// its colour on the minimap and from afar
export const SQUARE_FILL = { white: '#e6e2d8', black: '#2c2a32', gate: '#9e9a94' };
