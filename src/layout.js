// Card layout: sizes a fact card from the *measured* height of its wrapped text, so text can never
// run into the button. Pure function (no Phaser), shared by the game and tools/layout_check.html.
// All numbers are 640x360 canvas pixels; art is drawn at 2x, so heights snap to even numbers.

export const CARD = {
  width: 340,       // fixed card width
  pad: 16,          // inner padding, all sides
  titleH: 32,       // icon (16 art px x 2) + title row
  gap: 10,          // between title, body and button
  buttonW: 80,
  buttonH: 28,      // 14 art px x 2
  minH: 120,
  maxH: 340,        // a card must fit on the 360px canvas
};

export const bodyWrapWidth = (c = CARD) => c.width - 2 * c.pad;

export function cardLayout(bodyH, c = CARD) {
  const titleY = c.pad;
  const bodyY = titleY + c.titleH + c.gap;
  const buttonY = bodyY + Math.ceil(bodyH) + c.gap;
  let h = buttonY + c.buttonH + c.pad;
  h = Math.max(c.minH, h + (h % 2));                       // even height = whole art pixels
  return { h, titleY, bodyY, buttonY, fits: h <= c.maxH };
}

// The blocking dialogue box across the bottom of the screen (asset group 8). Text wraps at `wrap` and must fit `maxH`
// (4 lines at 18px); tools/layout_check.html measures every line against it.
export const DIALOG = { x: 8, y: 238, w: 624, h: 114, textX: 140, textY: 252, wrap: 360, size: 18, maxH: 94,
  plateX: 136, plateY: 226, plateW: 92, okX: 520, okY: 306, okW: 96, okH: 32 };
