"""Offline pixel-art authoring for Pawfect Parents.

Sprites are drawn into small pixel grids (palette keys), outlined, and exported
as PNG sprite sheets into assets/. The game only ever loads the PNGs.

  python tools/sprites.py              export every group
  python tools/sprites.py --group 1    export group 1 + write tools/preview/group1.html
  python tools/sprites.py --check      validate grids/palette, export nothing
"""
import base64, math, struct, sys, zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------- palette
# GAME_DESIGN.md §4.2 plus shades. 'A','B','C' are the dog coat slots (base, shade, light).
PALETTE = {
    'K': '#5A3E36',  # cocoa outline
    'k': '#3E2A24',  # deep cocoa: eyes, nose
    'w': '#FFFFFF',  # eye glint
    'W': '#FFF4E0',  # cream
    'Y': '#FFE08A',  # butter
    'y': '#F2C55C',  # butter shade
    'P': '#FFC3A0',  # peach
    'p': '#E89F7C',  # peach shade
    'M': '#B8E0C2',  # mint
    'm': '#8DBF9A',  # sage
    'G': '#6FA07E',  # deep sage
    'S': '#BFE3F2',  # sky
    's': '#8FC3DB',  # sky shade
    'L': '#D7C4EC',  # lavender
    'l': '#B39DD6',  # lavender shade
    'R': '#E8746A',  # coral
    'r': '#C95A52',  # coral shade
    'N': '#F4A7A0',  # pink: blush, tongue
    'H': '#6B4535',  # hair
    'h': '#4E3227',  # hair shade
    'F': '#E8B68E',  # skin
    'f': '#C98F66',  # skin shade
    # added in group 2 (room + food)
    'E': '#F7E6CB',  # cream shade: wallpaper pattern, plate rims
    'D': '#D9A877',  # wood
    'd': '#B9855A',  # wood shade
    'O': '#F29A5B',  # carrot orange
    'o': '#D97B3E',  # orange shade
    'V': '#9B7BC4',  # grape
    'v': '#76589E',  # grape shade
    'T': '#E9C994',  # cooked chicken / golden fry
    't': '#C99A62',  # chicken shade
}
COATS = {
    'cream':     {'A': '#F6DDB0', 'B': '#E2BE85', 'C': '#FFF1D6'},
    'caramel':   {'A': '#E0A060', 'B': '#C07C40', 'C': '#F2C48C'},
    'chocolate': {'A': '#9A6448', 'B': '#7A4A34', 'C': '#C08E70'},
}


def rgba(hexcol):
    h = hexcol.lstrip('#')
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), 255)


# ---------------------------------------------------------------- canvas
class Canvas:
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.px = [[None] * w for _ in range(h)]

    def put(self, x, y, c):
        x, y = int(x), int(y)
        if 0 <= x < self.w and 0 <= y < self.h:
            self.px[y][x] = c

    def get(self, x, y):
        if 0 <= x < self.w and 0 <= y < self.h:
            return self.px[y][x]
        return None

    def rect(self, x, y, w, h, c):
        for yy in range(int(y), int(y + h)):
            for xx in range(int(x), int(x + w)):
                self.put(xx, yy, c)

    def ellipse(self, cx, cy, rx, ry, c, shade=None, light=None):
        """Filled ellipse; bottom 35% gets `shade`, a top-left cap gets `light`."""
        for y in range(int(cy - ry) - 1, int(cy + ry) + 2):
            for x in range(int(cx - rx) - 1, int(cx + rx) + 2):
                nx, ny = (x + 0.5 - cx) / rx, (y + 0.5 - cy) / ry
                if nx * nx + ny * ny <= 1.0:
                    col = c
                    if shade and ny > 0.45:
                        col = shade
                    elif light and ny < -0.45 and nx < 0.35:
                        col = light
                    self.put(x, y, col)

    def recolor_filled(self, x, y, w, h, c):
        for yy in range(y, y + h):
            for xx in range(x, x + w):
                if self.get(xx, yy):
                    self.put(xx, yy, c)

    def pattern(self, x, y, rows):
        """Stamp a hand-drawn grid; '.' is transparent."""
        for j, row in enumerate(rows):
            for i, ch in enumerate(row):
                if ch != '.':
                    self.put(x + i, y + j, ch)

    def outline(self, c='K'):
        add = []
        for y in range(self.h):
            for x in range(self.w):
                if self.px[y][x] is None and any(
                        self.get(x + dx, y + dy) not in (None,)
                        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                    add.append((x, y))
        for x, y in add:
            self.px[y][x] = c
        return self

    def flipped(self):
        out = Canvas(self.w, self.h)
        out.px = [row[::-1] for row in self.px]
        return out


# ---------------------------------------------------------------- PNG
def png_bytes(rows_rgba, w, h):
    raw = b''.join(b'\x00' + b''.join(struct.pack('4B', *p) for p in row) for row in rows_rgba)

    def chunk(tag, data):
        return struct.pack('>I', len(data)) + tag + data + struct.pack('>I', zlib.crc32(tag + data) & 0xffffffff)
    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 6, 0, 0, 0))
            + chunk(b'IDAT', zlib.compress(raw, 9)) + chunk(b'IEND', b''))


def sheet_png(frames, extra=None):
    """Lay frames left-to-right; resolve palette keys (+ coat slots) to RGBA."""
    pal = {k: rgba(v) for k, v in PALETTE.items()}
    if extra:
        pal.update({k: rgba(v) for k, v in extra.items()})
    fw, fh = frames[0].w, frames[0].h
    rows = []
    for y in range(fh):
        row = []
        for f in frames:
            for x in range(fw):
                k = f.px[y][x]
                row.append(pal[k] if k else (0, 0, 0, 0))
        rows.append(row)
    return png_bytes(rows, fw * len(frames), fh)


# ---------------------------------------------------------------- dog
PUPPY = dict(w=32, h=32, body=(13, 21, 8, 5), head=(21, 13, 6), snout=(26, 16.5, 3.2, 2.2),
             ear=(17, 13, 2.2, 4.2), legs_back=(7, 10), legs_front=(16, 19), leg_top=23, ground=30,
             tail=(6, 18), tail_len=6, collar_x=16)
YOUNG = dict(w=40, h=40, body=(16, 26, 11, 6), head=(28, 15, 6.5), snout=(34, 18.5, 4, 2.5),
             ear=(23.5, 15, 2.4, 5), legs_back=(8, 12), legs_front=(21, 25), leg_top=28, ground=38,
             tail=(6, 22), tail_len=8, collar_x=22)


def draw_dog(d, *, legs=(0, 0, 0, 0), lift=(0, 0, 0, 0), tail=45, head=(0, 0), eyes='open',
             mouth='closed', ear=(0, 0), body_dy=0, pose='stand', tuck=False, ball=False):
    c = Canvas(d['w'], d['h'])
    bx, by, brx, bry = d['body']
    g = d['ground']

    # tail (behind body): chain of 2x2 blocks bending upward at the tip
    tx, ty = d['tail']
    ty += body_dy
    if pose == 'lie':
        tx, ty = int(bx - brx + 2), g - 5                       # tail grows from the rump, resting on the ground
    if pose == 'sit':
        tx, ty = tx + 3, g - 1
    a = math.radians(tail)
    for i in range(0 if tuck else d['tail_len']):
        t = i / max(1, d['tail_len'] - 1)
        ang = a + 0.5 * t * (1 if tail >= 0 else -1)
        px = tx - i * math.cos(ang) * 0.9
        py = ty - i * math.sin(ang) * 0.9
        c.rect(round(px) - 1, round(py) - 1, 2, 2, 'A' if i < d['tail_len'] - 1 else 'C')

    # legs: far legs in shade, near legs in base, white socks
    def leg(x, lifted, col):
        top = d['leg_top'] + body_dy
        bottom = g - lifted
        c.rect(x, top, 3, bottom - top, col)
        c.rect(x, bottom - 1, 3, 2, 'C')

    lb, lf = d['legs_back'], d['legs_front']
    if pose == 'sit':
        u = d['w'] / 32
        c.ellipse(lb[1] + 2, g - 4 * u, 6 * u, 5 * u, 'A', shade='B')   # folded haunch
        c.rect(lb[1] + 3, g - 1, int(5 * u), 2, 'C')                    # back paw
        for i, x in enumerate(lf):
            leg(x + legs[2 + i], 0, 'B' if i == 0 else 'A')
    elif pose == 'lie':
        c.rect(lf[1] + 1, g - 2, 8, 3, 'A')                         # front paws stretched out
        c.rect(lf[1] + 7, g - 2, 3, 3, 'C')
        c.ellipse(lb[0] + 3, g - 2, 4, 2.5, 'B')
    else:
        for i, x in enumerate(lb):
            leg(x + legs[i], lift[i], 'B' if i == 0 else 'A')
        for i, x in enumerate(lf):
            leg(x + legs[2 + i], lift[2 + i], 'B' if i == 0 else 'A')

    # body
    if pose == 'sit':                                             # upright chest + back sloping down to the haunch, no hump
        u = d['w'] / 32
        cxs = d['head'][0] - 5 * u
        c.ellipse((cxs + lb[1] + 2) / 2, g - 9 * u, 7 * u, 8 * u, 'A', shade='B')
        c.ellipse(cxs, g - 10 * u, 5.5 * u, 9 * u, 'A', shade='B', light='C')
    elif pose == 'lie':
        c.ellipse(bx, g - 3, brx + 1, 3.6, 'A', shade='B', light='C')
    else:
        c.ellipse(bx, by + body_dy, brx, bry, 'A', shade='B', light='C')

    if tuck:                                                      # tail curled down between the back legs
        x0, y0 = int(bx - brx + 1), int(by + body_dy + bry - 3)
        path = [(0, 0), (1, 2), (3, 4), (5, 5), (7, 5), (9, 4)]
        for dx, dy in path:
            c.rect(x0 + dx - 1, y0 + dy - 1, 4, 4, 'K')
        for i, (dx, dy) in enumerate(path):
            c.rect(x0 + dx, y0 + dy, 2, 2, 'C')

    # head group
    hx, hy, hr = d['head']
    hx += head[0]
    hy += head[1] + body_dy
    sx, sy, srx, sry = d['snout']
    sx += head[0]
    sy += head[1] + body_dy
    c.ellipse(hx, hy, hr, hr, 'A', shade=None, light='C')
    c.ellipse(sx, sy, srx, sry, 'C')
    # collar band where head meets body
    cx = d['collar_x'] + head[0] // 2
    cy0 = int(hy + hr * 0.55)
    c.recolor_filled(cx, cy0, 2, 3, 'R')
    c.put(cx + 1, cy0 + 3, 'Y')                                   # tag
    # ear (floppy, darker), drawn over head
    ex, ey, erx, ery = d['ear']
    c.ellipse(ex + head[0] + ear[0], ey + head[1] + body_dy + ear[1], erx, ery, 'B')
    # nose
    nx, ny = int(sx + srx) - 1, int(sy - sry) + 1
    c.rect(nx - 1, ny, 2, 2, 'k')
    # eye
    exx, eyy = int(hx + 1), int(hy - 1)
    if eyes == 'open':
        c.rect(exx, eyy, 2, 2, 'k')
        c.put(exx + 1, eyy, 'w')
    elif eyes == 'happy':
        c.put(exx - 1, eyy + 1, 'k'); c.put(exx, eyy, 'k'); c.put(exx + 1, eyy, 'k'); c.put(exx + 2, eyy + 1, 'k')
    elif eyes == 'closed':
        c.rect(exx, eyy + 1, 2, 1, 'k')
    elif eyes == 'sad':
        c.rect(exx, eyy + 1, 2, 1, 'k'); c.put(exx + 1, eyy, 'k'); c.put(exx - 1, eyy - 1, 'B')
    elif eyes == 'squint':
        c.put(exx, eyy, 'k'); c.put(exx + 1, eyy + 1, 'k'); c.put(exx, eyy + 2, 'k')
    elif eyes == 'whale':                                         # stress: the white of the eye shows, the eye looks back
        c.rect(exx - 1, eyy, 3, 2, 'w'); c.rect(exx - 1, eyy, 1, 2, 'k')
    # blush
    c.put(exx - 1, eyy + 3, 'N')
    # mouth
    my = int(sy + sry) - 1
    if mouth == 'open':
        c.rect(int(sx) - 1, my, 3, 1, 'k')
        c.rect(int(sx), my + 1, 2, 2, 'N')
    elif mouth == 'eat':
        c.rect(int(sx) - 1, my, 3, 1, 'k')
    elif mouth == 'pant':                                         # hot and tired: a long tongue hanging out
        c.rect(int(sx) - 1, my, 4, 1, 'k')
        c.rect(int(sx), my + 1, 2, 4, 'N'); c.rect(int(sx) + 1, my + 1, 1, 4, 'p')
    elif mouth == 'yawn':                                         # stress yawn: a wide-open mouth
        c.rect(int(sx) - 2, my - 1, 5, 3, 'k'); c.rect(int(sx) - 1, my + 1, 3, 1, 'N')
    elif mouth == 'lick':                                         # stress lip-lick: the tongue flicks up over the nose
        c.rect(int(sx) - 1, my, 3, 1, 'k')
        c.rect(nx - 2, ny + 2, 2, 2, 'N')
    if ball:                                                      # a tennis ball held in the mouth
        bx0, by0 = int(sx + srx * 0.4), my
        c.ellipse(bx0, by0 + 1, 2.6, 2.6, 'Y', shade='y'); c.put(bx0 - 1, by0, 'w'); c.put(bx0 + 1, by0 + 2, 'M')
    return c.outline()


def puppy_anims(d=PUPPY):
    D = lambda **kw: draw_dog(d, **kw)
    A = {}
    A['idle'] = [D(tail=45), D(tail=50), D(tail=50, eyes='closed'), D(tail=45)]
    A['walk'] = [D(legs=(1, -1, -1, 1), lift=(0, 1, 1, 0), tail=40),
                 D(legs=(0, 0, 0, 0), tail=45, body_dy=-1),
                 D(legs=(-1, 1, 1, -1), lift=(1, 0, 0, 1), tail=40),
                 D(legs=(0, 0, 0, 0), tail=45, body_dy=-1)]
    A['sit'] = [D(pose='sit', tail=15), D(pose='sit', tail=25, eyes='closed')]
    A['wag'] = [D(tail=t, eyes='happy', mouth='open') for t in (55, 85, 110, 85)]
    A['sniff'] = [D(head=(2, 6), tail=30, ear=(0, 1)), D(head=(2, 7), tail=35, ear=(0, 1))]
    A['circle'] = [D(head=(2, 6), tail=60, legs=(1, -1, -1, 1), lift=(0, 1, 1, 0)),
                   D(head=(2, 6), tail=60, body_dy=-1),
                   D(head=(2, 6), tail=60, legs=(1, -1, -1, 1), lift=(0, 1, 1, 0)).flipped(),
                   D(head=(2, 6), tail=60, body_dy=-1).flipped()]
    A['pee'] = [D(legs=(1, 0, 0, 0), body_dy=2, tail=20, eyes='closed'),
                D(legs=(1, 0, 0, 0), body_dy=2, tail=25, eyes='closed')]
    A['eat'] = [D(head=(3, 7), tail=60, eyes='closed', mouth='eat'), D(head=(3, 8), tail=75, eyes='closed')]
    A['refuse'] = [D(head=(-2, -1), tail=10, eyes='squint'), D(head=(-3, -1), tail=5, eyes='squint')]
    A['sad'] = [D(pose='lie', head=(1, 8), tail=-15, eyes='sad', ear=(0, 2)),
                D(pose='lie', head=(1, 8), tail=-15, eyes='closed', ear=(0, 2))]
    A['cower'] = [D(body_dy=3, head=(-1, 3), tuck=True, eyes='sad', ear=(-1, 2)),
                  D(body_dy=3, head=(-1, 4), tuck=True, eyes='sad', ear=(-1, 2))]
    return A


def young_anims():
    D = lambda **kw: draw_dog(YOUNG, **kw)
    return {'idle': [D(tail=45), D(tail=50), D(tail=50, eyes='closed'), D(tail=45)],
            'wag': [D(tail=t, eyes='happy', mouth='open') for t in (55, 85, 110, 85)]}


# ---------------------------------------------------------------- parent
def draw_parent(mouth='closed', blink=False):
    c = Canvas(48, 48)
    c.ellipse(24, 47, 17, 10, 'P', shade='p')            # shoulders / sweater
    c.rect(19, 36, 10, 3, 'W')                           # shirt collar
    c.rect(21, 30, 6, 7, 'f')                            # neck
    c.ellipse(24, 21, 10, 11, 'F')                       # face
    c.ellipse(24, 13, 11, 7, 'H', light=None)            # hair top
    c.rect(13, 13, 3, 11, 'H')                           # side hair L
    c.rect(32, 13, 3, 11, 'H')                           # side hair R
    c.pattern(16, 14, ['HHHHHH..HHHHHHH',               # fringe with a side part
                       'HHHH......HHHH.',
                       'HH...........H.'])
    c.rect(14, 22, 2, 2, 'h')
    c.rect(32, 22, 2, 2, 'h')
    # eyes
    if blink:
        c.rect(19, 21, 3, 1, 'k'); c.rect(27, 21, 3, 1, 'k')
    else:
        c.rect(19, 20, 2, 3, 'k'); c.put(20, 20, 'w')
        c.rect(28, 20, 2, 3, 'k'); c.put(29, 20, 'w')
    c.rect(17, 25, 2, 1, 'N'); c.rect(30, 25, 2, 1, 'N')  # blush
    if mouth == 'open':
        c.pattern(22, 26, ['kkkk', 'kNNk', '.kk.'])
    else:
        c.pattern(22, 26, ['k..k', '.kk.'])
    c.put(24, 24, 'f')                                    # nose hint
    return c.outline()


def parent_frames():
    return {'talk': [draw_parent('closed'), draw_parent('open'), draw_parent('closed'), draw_parent('open')],
            'idle': [draw_parent(), draw_parent(), draw_parent(blink=True), draw_parent()]}


# ---------------------------------------------------------------- groups
def group1():
    """Returns {relative_path: (frames, extra_palette, meta)}."""
    out = {}
    pup = puppy_anims()
    yng = young_anims()
    for coat, cols in COATS.items():
        for name, frames in pup.items():
            out[f'assets/sprites/puppy_{coat}_{name}.png'] = (frames, cols, {'coat': coat, 'anim': name, 'section': 'Puppy (Level 1)'})
        for name, frames in yng.items():
            out[f'assets/sprites/young_{coat}_{name}.png'] = (frames, cols, {'coat': coat, 'anim': name, 'section': 'Young dog (growth cutscene)'})
    for name, frames in parent_frames().items():
        out[f'assets/sprites/parent_{name}.png'] = (frames, None, {'anim': name, 'section': 'Parent (cutscenes and tips)'})
    return out


# ---------------------------------------------------------------- group 2: living room
# The world layer (rooms, dog, props) is authored at 320x180 and shown at 2x inside the
# 640x360 canvas; UI is drawn at full 640x360. This keeps the dog readable for kids.
FLOOR_Y = 140                                                    # top of the floor band
GROUND_Y = 165                                                   # where paws land
SPOTS = {'door': 36, 'middle': 170, 'bowl': 246}                 # pee-pad spot centres (x)


def box(c, x, y, w, h, fill, border='K'):
    c.rect(x, y, w, h, border)
    c.rect(x + 1, y + 1, w - 2, h - 2, fill)


def ring(c, cx, cy, rx, ry, keys, col='K'):
    """Outline the outer edge of a blob made of `keys` (collect first, then paint)."""
    edge = [(x, y) for y in range(int(cy - ry) - 1, int(cy + ry) + 2) for x in range(int(cx - rx) - 1, int(cx + rx) + 2)
            if c.get(x, y) in keys and any(c.get(x + dx, y + dy) not in keys for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))]
    for x, y in edge:
        c.put(x, y, col)


def draw_room():
    c = Canvas(320, 180)
    # wall + wallpaper dots
    c.rect(0, 0, 320, FLOOR_Y, 'W')
    for y in range(8, FLOOR_Y - 10, 14):
        for x in range(6 + (7 if (y // 14) % 2 else 0), 320, 14):
            c.pattern(x - 1, y - 1, ['.E.', 'EEE', '.E.'])
    # baseboard
    c.rect(0, FLOOR_Y - 5, 320, 5, 'P'); c.rect(0, FLOOR_Y - 5, 320, 1, 'K'); c.rect(0, FLOOR_Y - 2, 320, 2, 'p')
    # floor planks
    c.rect(0, FLOOR_Y, 320, 40, 'D'); c.rect(0, FLOOR_Y, 320, 1, 'K'); c.rect(0, FLOOR_Y + 1, 320, 2, 'd')
    for i, y in enumerate(range(FLOOR_Y + 8, 180, 8)):
        c.rect(0, y, 320, 1, 'd')
        for x in range((i * 19) % 44, 320, 44):
            c.rect(x, y - 7, 1, 7, 'd')

    # garden door (left): glass top shows the garden
    box(c, 10, 46, 48, 94, 'D')
    box(c, 13, 49, 42, 91, 'D')
    box(c, 16, 52, 36, 42, 'S')
    c.rect(17, 80, 34, 13, 'm'); c.rect(17, 79, 34, 1, 'G')
    for fx in (20, 29, 41, 47):
        c.put(fx, 78, 'Y')
    c.rect(33, 52, 1, 42, 'K'); c.rect(16, 72, 36, 1, 'K')
    c.rect(18, 54, 5, 1, 'w'); c.rect(18, 55, 2, 1, 'w')
    box(c, 19, 100, 30, 34, 'd')
    c.rect(49, 97, 4, 2, 'Y'); c.rect(49, 97, 4, 1, 'K')

    # window with curtains
    box(c, 76, 34, 56, 48, 'W')
    box(c, 79, 37, 50, 42, 'S')
    c.ellipse(95, 49, 7, 3, 'W'); c.ellipse(101, 47, 5, 3, 'W'); c.ellipse(119, 64, 5, 2, 'W')
    c.rect(104, 37, 1, 42, 'K'); c.rect(79, 57, 50, 1, 'K')
    for cx0 in (72, 126):
        box(c, cx0, 30, 10, 58, 'M')
        for yy in range(33, 85, 6):
            c.rect(cx0 + 3, yy, 1, 4, 'm'); c.rect(cx0 + 6, yy + 2, 1, 4, 'm')
        c.rect(cx0 + 1, 60, 8, 2, 'R')
    c.rect(68, 28, 72, 2, 'd'); c.rect(68, 28, 72, 1, 'K')
    box(c, 73, 82, 62, 4, 'P')

    # picture frame with a paw print
    box(c, 160, 46, 26, 22, 'd'); box(c, 162, 48, 22, 18, 'Y')
    c.pattern(168, 51, ['K.K.K.', '......', '.KKK..', 'KKKKK.', '.KKK..'])

    # sofa
    box(c, 143, 88, 56, 36, 'P')
    for sx0 in (147, 171):
        box(c, sx0, 92, 24, 20, 'P'); c.rect(sx0 + 1, 107, 22, 4, 'p')
    box(c, 138, 107, 66, 23, 'P'); c.rect(139, 123, 64, 6, 'p')
    box(c, 135, 102, 10, 28, 'P'); box(c, 197, 102, 10, 28, 'P')
    c.rect(136, 103, 8, 1, 'W'); c.rect(198, 103, 8, 1, 'W')
    box(c, 140, 130, 3, 7, 'd'); box(c, 199, 130, 3, 7, 'd')

    # rug in the middle of the room
    c.ellipse(170, 161, 32, 7, 'L'); c.ellipse(170, 161, 25, 4.5, 'l'); c.ellipse(170, 161, 22, 3, 'L')
    ring(c, 170, 161, 32, 7, ('L', 'l'))

    # potted plant
    for lx, ly, rx, ry in ((205, 112, 5, 4), (225, 112, 5, 4), (208, 104, 4, 6), (222, 104, 4, 6),
                           (212, 98, 3.5, 9), (218, 98, 3.5, 9), (215, 108, 4, 11)):
        blob(c, lx, ly, rx, ry, 'm', 'G', light='M')
    ring(c, 215, 104, 13, 18, ('m', 'G', 'M'))
    box(c, 208, 123, 15, 16, 'R'); c.rect(209, 133, 13, 5, 'r'); box(c, 206, 120, 19, 4, 'R')
    c.rect(207, 139, 17, 1, 'd')                                        # contact shadow on the floor

    # kitchen: high cupboard, tiled backsplash, counter
    box(c, 228, 20, 84, 40, 'M')
    for dx in (230, 271):
        box(c, dx, 22, 39, 36, 'M'); box(c, dx + 3, 25, 33, 30, 'M'); c.rect(dx + 4, 26, 31, 1, 'w')
    c.rect(266, 51, 2, 3, 'Y'); c.rect(272, 51, 2, 3, 'Y')
    c.rect(228, 60, 84, 41, 'S')
    for y in range(65, 101, 5):
        c.rect(228, y, 84, 1, 's')
    for y in range(60, 101, 5):
        for x in range(228 + (5 if (y // 5) % 2 else 0), 312, 10):
            c.rect(x, y, 1, 5, 's')
    c.rect(228, 60, 1, 41, 'K'); c.rect(311, 60, 1, 41, 'K')
    box(c, 223, 101, 93, 5, 'E'); c.rect(224, 102, 91, 1, 'w')
    box(c, 226, 106, 88, 31, 'M')
    for dx in (228, 257, 286):
        box(c, dx, 108, 26, 27, 'M'); c.rect(dx + 1, 131, 24, 3, 'm'); c.rect(dx + 11, 111, 4, 2, 'Y')
    c.rect(226, 137, 88, 3, 'd')
    return c


def draw_bowl(contents=None):
    """Room-view food bowl, optionally filled with one of the six foods."""
    c = Canvas(22, 12)
    if contents == 'kibble':
        c.ellipse(11, 5, 8, 2.6, 'D')
        for x in range(5, 18, 3):
            c.put(x, 4 + x % 2, 'd')
    elif contents == 'carrot':
        for x in (5, 9, 13):
            c.rect(x, 1 + x % 3, 2, 5, 'O'); c.put(x + 1, 2 + x % 3, 'o')
    elif contents == 'chicken':
        for x in (6, 11, 16):
            blob(c, x, 4, 2, 2, 'W', 't'); c.put(x - 1, 2, 'T')
    elif contents == 'chocolate':
        c.rect(5, 2, 12, 4, 'H'); c.rect(9, 2, 1, 4, 'h'); c.rect(13, 2, 1, 4, 'h')
    elif contents == 'grapes':
        c.pattern(4, 1, ['...VV.VV....', '.VVwVVwVVV..', 'VwVVvVVvVwV.', 'VVvVVVvVVVv.'])
    elif contents == 'onion':
        for gx in (8, 14):
            blob(c, gx, 3, 3, 1.6, 'N', 'r'); c.put(gx, 3, 'W')
    c.ellipse(11, 5.5, 9, 1.8, 'r')                                     # inside of bowl
    if contents:
        c.recolor_filled(2, 5, 0, 0, 'r')
    c.rect(3, 6, 16, 5, 'R'); c.rect(4, 9, 14, 2, 'r')
    c.rect(2, 5, 18, 1, 'W')                                            # rim
    return c.outline()


def draw_prop(kind, frame=0):
    if kind == 'pad':
        c = Canvas(48, 10)
        for y in range(2, 8):                                           # slight perspective slant
            c.rect(3 + (7 - y) // 2, y, 42 - (7 - y), 1, 'W')
        for x in range(10, 40, 7):
            c.put(x, 4, 'S'); c.put(x + 3, 6, 'S')
        c.rect(4, 7, 40, 1, 'L')
        return c.outline()
    if kind == 'puddle':
        c = Canvas(26, 7)
        c.ellipse(13, 3.5, 11, 2.4, 'Y'); c.ellipse(9, 3, 3, 1, 'w')
        return c.outline('y')
    raise ValueError(kind)


# ---------------------------------------------------------------- group 2: counter close-up (Snack Time)
COUNTER_SLOTS = (110, 210)        # x centres of the two food choices on the close-up
COUNTER_TOP_Y = 134               # where the big foods' bottoms rest


def blob(c, cx, cy, rx, ry, fill, edge, shade=None, light=None):
    """Ellipse with its own edge colour, so overlapping pieces stay readable."""
    c.ellipse(cx, cy, rx + 1, ry + 1, edge)
    c.ellipse(cx, cy, rx, ry, fill, shade=shade, light=light)


def draw_counter():
    c = Canvas(320, 180)
    # upper cupboard bottoms
    c.rect(0, 0, 320, 18, 'M')
    for dx in (0, 80, 160, 240):
        box(c, dx + 2, -1, 76, 18, 'M'); c.rect(dx + 3, 14, 74, 2, 'm')
    c.rect(74, 8, 3, 6, 'Y'); c.rect(83, 8, 3, 6, 'Y'); c.rect(234, 8, 3, 6, 'Y'); c.rect(243, 8, 3, 6, 'Y')
    c.rect(0, 18, 320, 1, 'K')
    # subway-tile backsplash
    c.rect(0, 19, 320, 95, 'S')
    c.rect(0, 19, 320, 3, 's')                                          # shadow under cupboards
    for i, y in enumerate(range(22, 114, 10)):
        c.rect(0, y, 320, 1, 's')
        for x in range(10 if i % 2 else 0, 320, 20):
            c.rect(x, y, 1, 10, 's')
            c.put(x + 3, y + 2, 'w')
    # utensil rail with hanging tools (left)
    c.rect(14, 34, 64, 2, 'd'); c.rect(14, 34, 64, 1, 'K')
    for hx in (22, 40, 58, 72):
        c.rect(hx, 36, 1, 4, 'K')
    box(c, 20, 40, 5, 18, 'D'); box(c, 18, 56, 9, 12, 'W')             # spatula
    box(c, 39, 40, 3, 22, 'D'); blob(c, 40, 66, 4, 3, 'W', 'K')          # spoon
    box(c, 57, 40, 3, 12, 'D')                                           # whisk
    for wx in (54, 57, 60):
        c.rect(wx, 52, 1, 12, 'K')
    c.ellipse(58, 63, 4, 3, 'K'); c.ellipse(58, 62, 3, 2, 'S')
    box(c, 71, 40, 3, 16, 'r')                                           # ladle
    blob(c, 72, 59, 5, 3, 'R', 'K', shade='r')
    # countertop (seen slightly from above)
    c.rect(0, 114, 320, 1, 'K')
    c.rect(0, 115, 320, 27, 'E')
    for i in range(70):                                                  # speckles
        x, y = (i * 53) % 317 + 1, 117 + (i * 29) % 23
        c.put(x, y, 'W' if i % 3 else 'p')
    c.rect(0, 115, 320, 2, 'P')                                          # back edge shadow
    # wooden boards under each food choice
    for sx in COUNTER_SLOTS:
        box(c, sx - 36, 124, 72, 14, 'D'); c.rect(sx - 35, 134, 70, 3, 'd')
        for gy in (127, 130):
            c.rect(sx - 30 + (gy % 7), gy, 20, 1, 'd'); c.rect(sx + 6, gy + 1, 16, 1, 'd')
    # herb pot (right)
    for lx, ly, rx, ry in ((282, 98, 4, 8), (292, 94, 4, 10), (300, 99, 4, 7)):
        blob(c, lx, ly, rx, ry, 'm', 'G')
    box(c, 280, 106, 26, 22, 'R'); c.rect(281, 120, 24, 7, 'r'); box(c, 278, 104, 30, 5, 'R')
    # front edge + lower cabinets
    box(c, -1, 142, 322, 7, 'W'); c.rect(0, 147, 320, 1, 'E')
    c.rect(0, 149, 320, 31, 'M')
    for dx in (4, 84, 164, 244):
        box(c, dx, 152, 72, 30, 'M'); c.rect(dx + 1, 152, 70, 2, 'm')
        c.rect(dx + 26, 158, 20, 3, 'Y'); c.rect(dx + 26, 158, 20, 1, 'K')
    return c


def draw_food_big(kind):
    c = Canvas(48, 48)
    if kind == 'kibble':        # dog-food bag with a bone label and spilled kibble
        box(c, 9, 9, 30, 37, 'P'); c.rect(32, 10, 6, 35, 'p'); c.rect(10, 40, 28, 5, 'p')
        for x in range(9, 39):                                           # crimped top
            c.rect(x, 4 + (x % 2), 1, 5, 'p')
        c.rect(9, 9, 30, 1, 'K')
        blob(c, 23, 23, 9, 7, 'W', 'K')
        c.pattern(16, 21, ['DD........DD', 'DDDDDDDDDDDD', 'DD........DD'])
        c.rect(14, 33, 20, 3, 'R'); c.rect(14, 37, 14, 1, 'p')
        for kx, ky in ((4, 45), (7, 46), (41, 46), (44, 44)):
            c.rect(kx, ky, 2, 2, 'd'); c.put(kx, ky, 'D')
    elif kind == 'chocolate':    # half-unwrapped bar
        c.rect(3, 16, 24, 18, 'H')
        for x in (9, 15, 21):
            c.rect(x, 16, 1, 18, 'h')
        c.rect(3, 25, 24, 1, 'h')
        for x in (4, 10, 16, 22):
            c.rect(x, 17, 3, 1, 'f'); c.rect(x, 26, 3, 1, 'f')
        c.rect(25, 13, 20, 24, 'R'); c.rect(25, 31, 20, 6, 'r')
        box(c, 29, 18, 12, 9, 'Y')
        c.pattern(32, 20, ['.K.K.', 'KKKKK', '.KKK.', '..K..'])           # little heart logo
        for y in range(13, 37):                                          # foil edge
            c.put(24 + (y % 2), y, 'W'); c.put(23 + (y % 2), y, 'E')
    elif kind == 'carrot':       # carrot sticks in a striped cup
        for i, x in enumerate((13, 18, 23, 28, 32)):
            top = (6, 2, 5, 1, 7)[i]
            c.rect(x, top, 4, 30 - top, 'O'); c.rect(x + 3, top + 1, 1, 29 - top, 'o')
            for ry in range(top + 4, 28, 5):
                c.rect(x, ry, 2, 1, 'o')
            c.put(x, top, 'Y')
        box(c, 10, 26, 28, 20, 'S')
        for sy in (30, 36, 42):
            c.rect(11, sy, 26, 2, 'W')
        c.rect(32, 27, 5, 18, 's')
    elif kind == 'grapes':
        c.rect(23, 2, 2, 9, 'G'); blob(c, 32, 6, 6, 3, 'm', 'G'); c.rect(28, 6, 8, 1, 'G')
        for gx, gy in ((13, 14), (21, 13), (29, 14), (37, 15), (17, 21), (25, 20), (33, 21),
                       (15, 28), (23, 28), (31, 28), (19, 35), (27, 35), (23, 41)):
            blob(c, gx, gy, 4.2, 4.2, 'V', 'v', shade='v')
            c.rect(gx - 2, gy - 2, 2, 1, 'w'); c.put(gx - 2, gy - 1, 'L')
    elif kind == 'chicken':      # whole roast (rotisserie) chicken on a plate
        c.ellipse(24, 41, 22, 5, 'W'); c.ellipse(24, 40, 16, 3, 'E')
        for side in (-1, 1):                                            # drumsticks pointing up and out
            lx = 24 + side * 11
            blob(c, lx, 25, 4, 6, 'D', 'd', shade='d', light='T')
            c.rect(lx + side * 2 - 1, 14, 3, 6, 'W'); c.rect(lx + side * 2 - 2, 13, 5, 2, 'W')   # bone tip
            c.put(lx + side * 2, 19, 'E')
        blob(c, 24, 31, 15, 9, 'D', 'd', shade='d', light='T')          # roasted body
        blob(c, 9, 33, 3, 3, 'D', 'd'); blob(c, 39, 33, 3, 3, 'D', 'd')  # tucked wings
        for gx, gy in ((18, 26), (22, 25), (29, 27), (16, 30)):           # crispy-skin glints
            c.put(gx, gy, 'Y')
        for gx, gy in ((20, 33), (27, 34), (31, 31), (24, 37)):           # roast speckles
            c.put(gx, gy, 'd')
    elif kind == 'onion':        # red onion: a whole bulb and a cut half showing its rings
        blob(c, 17, 31, 11, 11, 'N', 'r', shade='R')
        c.rect(16, 15, 3, 6, 'R'); c.rect(17, 12, 1, 4, 'r')              # pointed top
        for dx in (-6, 0, 6):                                             # curved skin lines
            for yy in range(23, 41):
                bulge = round(dx * 0.35 * (1 - ((yy - 31) / 9) ** 2))
                c.put(17 + dx + bulge, yy, 'R')
        c.rect(11, 25, 2, 3, 'W'); c.put(11, 28, 'W')                      # glint
        for rx in (-2, 0, 2):                                             # roots
            c.put(17 + rx, 43, 'h')
        for r, col in ((9, 'r'), (8, 'N'), (6, 'W'), (5, 'N'), (3, 'W'), (2, 'N'), (1, 'W')):
            c.ellipse(36, 36, r, r * 0.8, col)
    return c.outline()


FOODS = ('kibble', 'chocolate', 'carrot', 'grapes', 'chicken', 'onion')


def group2():
    out = {'assets/bg/living_room.png': ([draw_room()], None, {'section': 'bg', 'anim': 'living room', 'place': (0, 0)})}
    out['assets/bg/counter_closeup.png'] = ([draw_counter()], None, {'section': 'bg', 'anim': 'counter close-up'})
    for f in FOODS:
        safe = f in ('kibble', 'carrot', 'chicken')
        out[f'assets/sprites/foodbig_{f}.png'] = ([draw_food_big(f)], None,
            {'section': 'Food, close-up (choosing on the counter)', 'anim': f, 'note': 'safe' if safe else 'unsafe'})
    out['assets/sprites/bowl_empty.png'] = ([draw_bowl()], None, {'section': 'Food bowl (room view)', 'anim': 'empty', 'note': 'By the counter'})
    for f in FOODS:
        out[f'assets/sprites/bowl_{f}.png'] = ([draw_bowl(f)], None,
            {'section': 'Food bowl (room view)', 'anim': f, 'note': 'After choosing ' + f})
    out['assets/sprites/prop_pad.png'] = ([draw_prop('pad')], None, {'section': 'Props', 'anim': 'pee pad', 'note': 'Dragged to a potty spot'})
    out['assets/sprites/prop_puddle.png'] = ([draw_prop('puddle')], None, {'section': 'Props', 'anim': 'puddle', 'note': 'Accident on the floor'})
    return out


# Preview mock-ups (top-left, world pixels 320x180). Level1.js uses the same numbers.
SCENES2 = [
    ('Living room', (320, 180), [
        ('assets/bg/living_room.png', 0, 0),
        ('assets/sprites/bowl_kibble.png', SPOTS['bowl'] - 11, GROUND_Y - 10),
        ('assets/sprites/prop_pad.png', SPOTS['door'] - 24, GROUND_Y - 7),
        ('assets/sprites/prop_puddle.png', SPOTS['middle'] - 13, GROUND_Y - 4),
        ('assets/sprites/puppy_caramel_wag.png', 262, GROUND_Y - 30),
    ]),
    ('Kitchen counter close-up (Snack Time)', (320, 180), [
        ('assets/bg/counter_closeup.png', 0, 0),
        ('assets/sprites/foodbig_carrot.png', COUNTER_SLOTS[0] - 24, COUNTER_TOP_Y - 48),
        ('assets/sprites/foodbig_grapes.png', COUNTER_SLOTS[1] - 24, COUNTER_TOP_Y - 48),
    ]),
]


# ---------------------------------------------------------------- group 3: UI kit
# UI art uses the same chunky pixel size as the world: authored small, shown at 2x.
# Only text (Pixelify Sans) renders at the full 640x360 resolution.

def shape(w, h, insets):
    """Mask of a rounded rectangle; insets[i] = how far row i (from top and bottom) is pulled in."""
    c = Canvas(w, h)
    for y in range(h):
        i = insets[y] if y < len(insets) else insets[h - 1 - y] if h - 1 - y < len(insets) else 0
        c.rect(i, y, w - 2 * i, 1, 'W')
    return c


def panel(w, h, fill='W', ring=None, lip=None, insets=(3, 1, 1)):
    """Rounded UI panel: cocoa border, optional coloured inner ring, optional bottom lip."""
    c = shape(w, h, insets)
    for y in range(h):
        for x in range(w):
            if c.px[y][x]:
                c.px[y][x] = fill
    if lip:
        for y in range(h - 3, h):
            for x in range(w):
                if c.px[y][x]:
                    c.px[y][x] = lip
    # border = any filled pixel touching outside
    border = [(x, y) for y in range(h) for x in range(w) if c.px[y][x] and any(
        c.get(x + dx, y + dy) is None for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))]
    for x, y in border:
        c.px[y][x] = 'K'
    if ring:
        inner = [(x, y) for y in range(h) for x in range(w) if c.px[y][x] not in (None, 'K') and any(
            c.get(x + dx, y + dy) == 'K' for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, -1), (1, -1), (-1, 1)))]
        for x, y in inner:
            c.px[y][x] = ring
    return c


def nine(src, w, h, k):
    """Stretch a nine-slice source to w x h (preview only; Phaser's NineSlice does this in game)."""
    out = Canvas(w, h)
    for y in range(h):
        sy = y if y < k else src.h - (h - y) if y >= h - k else k
        for x in range(w):
            sx = x if x < k else src.w - (w - x) if x >= w - k else k
            out.px[y][x] = src.px[sy][sx]
    return out


def scale2(c):
    out = Canvas(c.w * 2, c.h * 2)
    for y in range(c.h):
        for x in range(c.w):
            for d in ((0, 0), (1, 0), (0, 1), (1, 1)):
                out.px[y * 2 + d[1]][x * 2 + d[0]] = c.px[y][x]
    return out


def speech_bubble():
    c = panel(16, 16, 'W', lip=None)
    for y in (12, 13):
        for x in range(c.w):
            if c.px[y][x] == 'W':
                c.px[y][x] = 'E'
    return c


def thought_bubble():
    c = panel(16, 16, 'W', insets=(4, 2, 1, 1))
    for y in (12, 13):
        for x in range(c.w):
            if c.px[y][x] == 'W':
                c.px[y][x] = 'E'
    return c


def speech_tail():
    """Points left from the bubble towards the parent; its last column overlaps the bubble border."""
    c = Canvas(9, 7)
    c.pattern(0, 1, ['....WWWW', '..WWWWWW', 'WWWWWWWW', '..WWWWWW', '....WWWW'])
    c.outline()
    for y in range(c.h):
        if c.px[y][7] == 'W':
            c.px[y][8] = 'W'
    return c


def thought_tail():
    c = Canvas(12, 12)
    c.ellipse(4, 3, 3, 2.5, 'W'); c.ellipse(8, 8, 2, 1.6, 'W')
    return c.outline()


def button(fill, lip, hi):
    frames = []
    for state in ('normal', 'hover', 'down'):
        f = {'normal': fill, 'hover': hi, 'down': fill}[state]
        c = panel(16, 14, f, lip=None, insets=(2, 1))
        top = 1 if state == 'down' else 0
        for y in range(c.h):
            for x in range(c.w):
                if c.px[y][x] not in (None, 'K'):
                    if y >= c.h - (2 if state == 'down' else 4):
                        c.px[y][x] = lip
                    elif y == 1 + top:
                        c.px[y][x] = 'w' if state != 'down' else f
        frames.append(c)
    return frames


ICONS = {
    'bowl':     lambda c: (c.ellipse(8, 7, 6, 1.5, 'r'), c.rect(3, 7, 10, 5, 'R'), c.rect(4, 10, 8, 2, 'r'), c.rect(2, 6, 12, 1, 'W'),
                           c.ellipse(8, 5.5, 4, 1.6, 'D')),
    'question': lambda c: c.pattern(4, 1, ['.YYYYY.', 'YYyyyYY', 'YY...YY', '....YYY', '...YYy.', '..YYy..', '..YY...', '.......', '..YY...', '..YY...']),
    'tummy':    lambda c: c.pattern(2, 2, ['..mmmmmm..', '.mm....mm.', 'mm..mmm.mm', 'm..m...mm.', 'm..m.mmm..', 'm..m......',
                                           'mm..mmmm..', '.mm.....m.', '..mmmmmm..']),
    'heart':    lambda c: (c.pattern(2, 3, ['.RRR..RRR.', 'RRwRRRRRRR', 'RwRRRRRRRR', 'RRRRRRRRRR', '.RRRRRRRr.', '..RRRRRr..',
                                            '...RRRr...', '....Rr....'])),
    'treat':    lambda c: c.pattern(1, 5, ['.WW.......WW.', 'WWWWWWWWWWWWW', '.WEEEEEEEEEW.', 'WWWWWWWWWWWWW', '.WE.......WE.']),
    'clean':    lambda c: (box(c, 4, 6, 7, 8, 'S'), c.rect(5, 11, 5, 2, 's'), c.rect(5, 3, 5, 3, 'M'), c.rect(10, 3, 3, 2, 'M'),
                           c.put(13, 2, 'Y'), c.put(14, 4, 'Y'), c.put(13, 6, 'Y'), c.rect(6, 8, 3, 1, 'W')),
    'scold':    lambda c: c.pattern(1, 1, ['......R.......', '.R...RR...R...', '.RR.RRRR.RR...', '.RRRRWWRRRR...', '..RRRWWRRR....',
                                           'RRRRRWWRRRRRR.', '.RRRRWWRRRRR..', '..RRRRRRRRR...', '..RRRWWRRRRR..', '.RRRRWWRRRRRR.',
                                           '.RR.RRRR.RR...', '.R...RR...R...', '......R.......']),
    'droplet':  lambda c: c.pattern(4, 1, ['...Y...', '..YYY..', '..YYY..', '.YYYYY.', '.YwYYY.', 'YwYYYYY', 'YwYYYYY', 'YYYYYyY',
                                           'YYYYYyY', '.YYYyY.', '..yyy..']),
    'pad':      lambda c: (c.rect(1, 6, 14, 6, 'W'), c.put(4, 8, 'S'), c.put(8, 9, 'S'), c.put(12, 8, 'S'), c.rect(1, 11, 14, 1, 'L')),
    'bulb':     lambda c: (c.ellipse(8, 6, 5, 5, 'Y', shade='y'), c.rect(6, 10, 5, 2, 'Y'), c.rect(6, 12, 5, 2, 'S'), c.rect(7, 14, 3, 1, 's'),
                           c.rect(5, 3, 2, 2, 'w')),
    'check':    lambda c: c.pattern(1, 3, ['...........MM', '..........MMM', '.........MMM.', 'MM......MMM..', 'MMM....MMM...',
                                           '.MMM..MMM....', '..MMMMMM.....', '...MMMM......', '....MM.......']),
    'cross':    lambda c: c.pattern(2, 2, ['RR......RR', 'RRR....RRR', '.RRR..RRR.', '..RRRRRR..', '...RRRR...', '...RRRR...',
                                           '..RRRRRR..', '.RRR..RRR.', 'RRR....RRR', 'RR......RR']),
    'star':     lambda c: c.pattern(2, 1, ['.....Y.....', '.....Y.....', '....YYY....', 'YYYYYwYYYYY', '.YYYwYYYYY.', '..YYYYYYY..',
                                           '..YYYYYYY..', '.YYYY.YYYY.', '.YY.....YY.', 'Y.........Y']),
    'sound_on': lambda c: (c.pattern(1, 4, ['..WW', 'WWWW', 'WWWW', 'WWWW', '..WW']), c.pattern(5, 2, ['...W', '..WW', '.WWW', 'WWWW', 'WWWW',
                           'WWWW', '.WWW', '..WW', '...W'])),
    'sound_off': lambda c: (c.pattern(1, 4, ['..WW', 'WWWW', 'WWWW', 'WWWW', '..WW']), c.pattern(5, 2, ['...W', '..WW', '.WWW', 'WWWW', 'WWWW',
                            'WWWW', '.WWW', '..WW', '...W']), c.pattern(10, 4, ['R...R', '.R.R.', '..R..', '.R.R.', 'R...R'])),
    'pause':    lambda c: (c.rect(4, 3, 3, 10, 'W'), c.rect(9, 3, 3, 10, 'W')),
}


ICON_AFTER_OUTLINE = {      # thin line details that the outline pass would otherwise swallow
    'sound_on': lambda c: c.pattern(11, 4, ['K...', '.K.K', '.K.K', '.K.K', '.K.K', 'K...'][:6]),
}


def icon(name):
    if name in globals().get('ICONS11', {}):
        return icon11(name)
    c = Canvas(16, 16)
    (ICONS.get(name) or ICONS_L2.get(name) or ICONS8[name])(c)
    c.outline()
    if name in ICON_AFTER_OUTLINE:
        ICON_AFTER_OUTLINE[name](c)
    return c


def pointer_cue():
    frames = []
    for dy in (0, 1, 2, 1):
        c = Canvas(13, 17)
        c.pattern(1, 1 + dy, ['...YYYYY...', '...YYYYY...', '...YYYYY...', '...YYYYY...', 'YYYYYYYYYYY', '.YYYYYYYYy.',
                              '..YYYYYYy..', '...YYYYy...', '....YYy....', '.....y.....'])
        c.rect(4, 1 + dy, 1, 4, 'w')
        frames.append(c.outline())
    return frames


def paw_cursor():
    c = Canvas(16, 16)
    c.ellipse(8, 11, 4.5, 3.6, 'W', shade='E')
    for tx, ty in ((3, 6), (6, 3.5), (10, 3.5), (13, 6)):
        c.ellipse(tx, ty, 1.7, 2, 'W')
    return scale2(c.outline())          # CSS cursors are not scaled, so export at display size


def meter_parts():
    frame = panel(64, 8, 'E', insets=(1,))
    fills = {}
    for state, (f, s) in {'green': ('M', 'm'), 'yellow': ('Y', 'y'), 'red': ('R', 'r')}.items():
        c = Canvas(62, 6)
        c.rect(0, 0, 62, 6, f); c.rect(0, 4, 62, 2, s); c.rect(0, 1, 62, 1, 'w')
        fills[state] = c
    heart = Canvas(13, 12)
    heart.pattern(1, 1, ['.RRR.RRR.', 'RwRRRRRRR', 'RwRRRRRRR', 'RRRRRRRRr', '.RRRRRRr.', '..RRRRr..', '...RRr...', '....r....'])
    heart = heart.outline()
    return frame, fills, heart


FONT3x5 = {'P': ['111', '101', '111', '100', '100'], 'A': ['010', '101', '111', '101', '101'],
           'W': ['101', '101', '111', '111', '101'], 'F': ['111', '100', '110', '100', '100'],
           'E': ['111', '100', '110', '100', '111'], 'C': ['011', '100', '100', '100', '011'],
           'T': ['111', '010', '010', '010', '010'], '!': ['1', '1', '1', '0', '1'],
           'U': ['101', '101', '101', '101', '111'], 'Y': ['101', '101', '010', '010', '010'],
           'J': ['001', '001', '001', '101', '010'], 'O': ['010', '101', '101', '101', '010'],
           'B': ['110', '101', '110', '101', '110'], 'S': ['011', '100', '010', '001', '110'],
           'D': ['110', '101', '101', '101', '110'], 'R': ['110', '101', '110', '101', '101'],
           'M': ['10001', '11011', '10101', '10001', '10001'], 'H': ['101', '101', '111', '101', '101'],
           'L': ['100', '100', '100', '100', '111'], 'G': ['011', '100', '101', '101', '011'],
           'Z': ['111', '001', '010', '100', '111']}


def stamp():
    c = panel(52, 17, 'W', ring='R', insets=(2, 1))
    c.pattern(4, 5, ['.R.R.', 'R...R', '.RRR.', 'RRRRR', '.RRR.'])          # paw
    x = 11
    for ch in 'PAWFECT!':
        for j, row in enumerate(FONT3x5[ch]):
            for i, bit in enumerate(row):
                if bit == '1':
                    c.put(x + i, 6 + j, 'r')
        x += len(FONT3x5[ch][0]) + 1
    return c


def swatch(coat):
    c = Canvas(14, 14)
    c.ellipse(7, 7, 6, 6, 'A', shade='B', light='C')
    return c.outline()


def swatch_ring():
    c = Canvas(18, 18)
    for y in range(18):
        for x in range(18):
            r = ((x + 0.5 - 9) / 8.5) ** 2 + ((y + 0.5 - 9) / 8.5) ** 2
            if 0.62 <= r <= 1.0:
                c.put(x, y, 'Y')
    return c


def group3():
    out = {}
    U = 'assets/ui/'
    out[U + 'bubble_speech.png'] = ([speech_bubble()], None, {'section': 'Bubbles and cards (nine-slice: stretch to fit text)', 'anim': 'speech bubble', 'note': 'Parent speaks. Corners 5px'})
    out[U + 'bubble_speech_tail.png'] = ([speech_tail()], None, {'section': 'Bubbles and cards (nine-slice: stretch to fit text)', 'anim': 'speech tail', 'note': 'Points at the parent'})
    out[U + 'bubble_thought.png'] = ([thought_bubble()], None, {'section': 'Bubbles and cards (nine-slice: stretch to fit text)', 'anim': 'thought bubble', 'note': 'Dog thinks. Holds an icon'})
    out[U + 'bubble_thought_tail.png'] = ([thought_tail()], None, {'section': 'Bubbles and cards (nine-slice: stretch to fit text)', 'anim': 'thought tail', 'note': 'Little circles to the dog'})
    for name, ring, note in (('info', 'E', 'Task card, name field'), ('good', 'M', 'Did you know? (right choice)'), ('bad', 'R', 'Did you know? (unsafe / wrong)')):
        out[U + f'card_{name}.png'] = ([panel(18, 18, 'W', ring=ring)], None,
                                       {'section': 'Bubbles and cards (nine-slice: stretch to fit text)', 'anim': f'card {name}', 'note': note + '. Corners 6px'})
    out[U + 'button_mint.png'] = (button('M', 'm', 'Y'), None, {'section': 'Buttons (normal, hover, pressed)', 'anim': 'primary', 'note': 'OK, Adopt!, Try again'})
    out[U + 'button_cream.png'] = (button('W', 'E', 'Y'), None, {'section': 'Buttons (normal, hover, pressed)', 'anim': 'secondary', 'note': 'Choices, pause menu'})
    frame, fills, heart = meter_parts()
    out[U + 'meter_heart.png'] = ([heart], None, {'section': 'Happiness meter', 'anim': 'heart', 'note': 'Left of the bar'})
    out[U + 'meter_frame.png'] = ([frame], None, {'section': 'Happiness meter', 'anim': 'bar frame', 'note': 'Empty track'})
    for st, f in fills.items():
        out[U + f'meter_fill_{st}.png'] = ([f], None, {'section': 'Happiness meter', 'anim': f'fill {st}', 'note': {'green': 'Above 60', 'yellow': '30 to 60', 'red': 'Below 30 (pulses)'}[st]})
    out[U + 'cue_arrow.png'] = (pointer_cue(), None, {'section': 'Guidance and cursor', 'anim': 'pointer cue', 'note': 'Bobs over the dog or a target (Level 1 only)'})
    out[U + 'cursor_paw.png'] = ([paw_cursor()], None, {'section': 'Guidance and cursor', 'anim': 'paw cursor', 'note': 'Over anything clickable'})
    out[U + 'stamp_pawfect.png'] = ([stamp()], None, {'section': 'Guidance and cursor', 'anim': 'Pawfect! stamp', 'note': 'Album page, no wrong answers'})
    for coat, cols in COATS.items():
        out[U + f'swatch_{coat}.png'] = ([swatch(coat)], cols, {'section': 'Dog setup', 'anim': f'{coat} swatch', 'note': 'Coat choice'})
    out[U + 'swatch_ring.png'] = ([swatch_ring()], None, {'section': 'Dog setup', 'anim': 'selected ring', 'note': 'Around the chosen coat'})
    notes = {'bowl': 'Hungry / Safe foods skill', 'question': 'Curious / unsure', 'tummy': 'Tummy hurts', 'heart': 'Happy / praise later',
             'treat': 'Treat and praise', 'clean': 'Clean it up calmly', 'scold': 'Scold the puppy', 'droplet': 'Needs to go potty',
             'pad': 'Potty spot skill', 'bulb': 'Did you know?', 'check': 'Right', 'cross': 'Not safe', 'star': 'Bonus / sparkle',
             'sound_on': 'Sound on', 'sound_off': 'Sound off', 'pause': 'Pause'}
    for name in ICONS:
        out[U + f'icon_{name}.png'] = ([icon(name)], None, {'section': 'Icons (replace emoji everywhere)', 'anim': name, 'note': notes[name]})
    return out


def ui_mockups():
    """Two HUD mock-ups at 640x360. Art at 2x; text in Pixelify Sans on top."""
    sp, th, cg, cb, ci = speech_bubble(), thought_bubble(), panel(18, 18, 'W', ring='M'), panel(18, 18, 'W', ring='R'), panel(18, 18, 'W', ring='E')
    frame, fills, heart = meter_parts()
    bm, bc = button('M', 'm', 'Y')[0], button('W', 'E', 'Y')[0]
    green = Canvas(62, 6); green.px = [row[:44] + [None] * 18 for row in fills['green'].px]
    yellow = Canvas(62, 6); yellow.px = [row[:26] + [None] * 36 for row in fills['yellow'].px]
    hud = lambda fill, name: [
        ('@canvas', heart, 8, 8, 2), ('@canvas', frame, 36, 10, 2), ('@canvas', fill, 38, 12, 2),
        ('@text', 172, 9, 120, name, 16, '#5A3E36', 'left'),
        ('@canvas', nine(ci, 96, 16, 6), 402, 6, 2), ('@canvas', icon('bowl'), 410, 6, 2),
        ('@text', 446, 13, 140, 'Snack time  1 of 2', 14, '#5A3E36', 'left'),
        ('@canvas', nine(bc, 16, 16, 5), 604, 6, 2), ('@canvas', icon('pause'), 604, 6, 2)]
    room = [('assets/bg/living_room.png', 0, 0, 2)] + hud(green, 'Biscuit') + [
        ('assets/sprites/bowl_empty.png', (SPOTS['bowl'] - 11) * 2, (GROUND_Y - 10) * 2, 2),
        ('assets/sprites/puppy_cream_sit.png', 400, (GROUND_Y - 30) * 2, 2),
        ('@canvas', nine(th, 26, 24, 6), 410, 212, 2), ('@canvas', icon('bowl'), 415, 216, 2),
        ('@canvas', thought_tail(), 424, 258, 2),
        ('@canvas', pointer_cue()[0], 524, 136, 2),
        ('@canvas', nine(ci, 52, 50, 6), 2, 40, 2), ('assets/sprites/parent_talk.png', 6, 42, 2),
        ('@canvas', nine(sp, 210, 30, 5), 116, 58, 2), ('@canvas', speech_tail(), 100, 78, 2),
        ('@text', 134, 70, 390, "Biscuit's hungry! Pick something safe from the counter.", 16, '#5A3E36', 'left'),
    ]
    counter = [('assets/bg/counter_closeup.png', 0, 0, 2), ('assets/sprites/foodbig_kibble.png', (COUNTER_SLOTS[0] - 24) * 2, (COUNTER_TOP_Y - 48) * 2, 2),
               ('assets/sprites/foodbig_chocolate.png', (COUNTER_SLOTS[1] - 24) * 2, (COUNTER_TOP_Y - 48) * 2, 2)] + hud(yellow, 'Biscuit') + [
        ('@canvas', nine(ci, 50, 12, 6), (COUNTER_SLOTS[0] - 25) * 2, 290, 2),
        ('@text', (COUNTER_SLOTS[0] - 25) * 2, 296, 100, 'Puppy kibble', 13, '#5A3E36', 'center'),
        ('@canvas', nine(ci, 50, 12, 6), (COUNTER_SLOTS[1] - 25) * 2, 290, 2),
        ('@text', (COUNTER_SLOTS[1] - 25) * 2, 296, 100, 'Chocolate bar', 13, '#5A3E36', 'center'),
        # Same numbers as src/layout.js cardLayout() for this text (measured in Phaser: 3 lines -> h=158).
        ('@canvas', nine(cb, 170, 79, 6), 150, 101, 2), ('@canvas', icon('bulb'), 166, 117, 2),
        ('@text', 206, 123, 260, 'Did you know?', 18, '#C95A52', 'left'),
        ('@text', 166, 159, 308, "Chocolate contains theobromine, which dogs can't break down. Even a little can make them very sick.", 14, '#5A3E36', 'left'),
        ('@canvas', nine(bm, 40, 14, 5), 280, 215, 2), ('@text', 280, 220, 80, 'OK!', 15, '#5A3E36', 'center'),
    ]
    return [('HUD in the living room (Snack Time start)', (640, 360), room),
            ('Counter close-up with a fact card (wrong pick)', (640, 360), counter)]


# ---------------------------------------------------------------- group 4: screens
FONT5x7 = {
    'P': ['11110', '10001', '10001', '11110', '10000', '10000', '10000'],
    'A': ['01110', '10001', '10001', '11111', '10001', '10001', '10001'],
    'W': ['10001', '10001', '10001', '10101', '10101', '11011', '10001'],
    'F': ['11111', '10000', '10000', '11110', '10000', '10000', '10000'],
    'E': ['11111', '10000', '10000', '11110', '10000', '10000', '11111'],
    'C': ['01111', '10000', '10000', '10000', '10000', '10000', '01111'],
    'T': ['11111', '00100', '00100', '00100', '00100', '00100', '00100'],
    'R': ['11110', '10001', '10001', '11110', '10100', '10010', '10001'],
    'N': ['10001', '11001', '10101', '10011', '10001', '10001', '10001'],
    'S': ['01111', '10000', '10000', '01110', '00001', '00001', '11110'],
}


def logo():
    """'PAWFECT / PARENTS' in chunky 2x pixel letters: coral with a butter shine, cocoa outline, drop shadow."""
    c = Canvas(104, 40)
    for line, (word, fill, shade) in enumerate((('PAWFECT', 'R', 'r'), ('PARENTS', 'm', 'G'))):
        x0, y0 = 3 + line * 4, 3 + line * 18
        for i, ch in enumerate(word):
            for j, row in enumerate(FONT5x7[ch]):
                for k, bit in enumerate(row):
                    if bit == '1':
                        col = 'Y' if j == 0 else fill if j < 5 else shade
                        c.rect(x0 + i * 13 + k * 2, y0 + j * 2, 2, 2, col)
    c.outline()
    shadow = [(x + 1, y + 1) for y in range(c.h) for x in range(c.w) if c.px[y][x] == 'K']
    for x, y in shadow:                                                   # 1px cocoa drop shadow
        if c.get(x, y) is None:
            c.put(x, y, 'h')
    c.pattern(95, 30, ['.K.K.', 'K...K', '.KKK.', 'KKKKK', '.KKK.'])         # little paw after PARENTS
    return c


def wall_and_floor(c, floor_y):
    c.rect(0, 0, c.w, floor_y, 'W')
    for y in range(8, floor_y - 10, 14):
        for x in range(6 + (7 if (y // 14) % 2 else 0), c.w, 14):
            c.pattern(x - 1, y - 1, ['.E.', 'EEE', '.E.'])
    c.rect(0, floor_y - 5, c.w, 5, 'P'); c.rect(0, floor_y - 5, c.w, 1, 'K'); c.rect(0, floor_y - 2, c.w, 2, 'p')
    c.rect(0, floor_y, c.w, c.h - floor_y, 'D'); c.rect(0, floor_y, c.w, 1, 'K'); c.rect(0, floor_y + 1, c.w, 2, 'd')
    for i, y in enumerate(range(floor_y + 8, c.h, 8)):
        c.rect(0, y, c.w, 1, 'd')
        for x in range((i * 19) % 44, c.w, 44):
            c.rect(x, y - 7, 1, 7, 'd')


def draw_title_bg():
    c = Canvas(320, 180)
    wall_and_floor(c, 140)
    # bunting across the top
    for x in range(0, 320):
        c.put(x, 6 + round(3 * math.sin(math.pi * (x % 160) / 160)), 'K')
    for i, x in enumerate(range(4, 316, 16)):
        top = 7 + round(3 * math.sin(math.pi * (x % 160) / 160))
        col = 'RYMSL'[i % 5]
        for r in range(7):
            c.rect(x + r // 2, top + r, 9 - r, 1, col)
        c.put(x + 4, top + 7, col)
    # window (left) and plant (right)
    box(c, 22, 40, 64, 56, 'W'); box(c, 25, 43, 58, 50, 'S')
    c.ellipse(42, 58, 7, 3, 'W'); c.ellipse(49, 56, 5, 3, 'W')
    c.rect(53, 43, 1, 50, 'K'); c.rect(25, 67, 58, 1, 'K')
    for cx0 in (16, 80):
        box(c, cx0, 36, 10, 66, 'M')
        for yy in range(39, 98, 6):
            c.rect(cx0 + 3, yy, 1, 4, 'm'); c.rect(cx0 + 6, yy + 2, 1, 4, 'm')
        c.rect(cx0 + 1, 70, 8, 2, 'R')
    c.rect(12, 34, 84, 2, 'd'); c.rect(12, 34, 84, 1, 'K'); box(c, 19, 96, 70, 4, 'P')
    for lx, ly, rx, ry in ((276, 112, 5, 4), (296, 112, 5, 4), (279, 104, 4, 6), (293, 104, 4, 6),
                           (283, 98, 3.5, 9), (289, 98, 3.5, 9), (286, 108, 4, 11)):
        blob(c, lx, ly, rx, ry, 'm', 'G', light='M')
    ring(c, 286, 104, 13, 18, ('m', 'G', 'M'))
    box(c, 279, 123, 15, 16, 'R'); c.rect(280, 133, 13, 5, 'r'); box(c, 277, 120, 19, 4, 'R')
    # rug + big cushion in the middle (the puppy sits here)
    c.ellipse(160, 160, 70, 12, 'L'); c.ellipse(160, 160, 60, 8, 'l'); c.ellipse(160, 160, 56, 6, 'L')
    ring(c, 160, 160, 70, 12, ('L', 'l'))
    blob(c, 160, 154, 34, 9, 'R', 'K', shade='r', light='N')
    for tx in (140, 160, 180):
        c.put(tx, 153, 'r'); c.put(tx, 154, 'r')
    return c


def paw_print(filled):
    c = Canvas(11, 10)
    col = 'R' if filled else 'E'
    c.ellipse(5.5, 6.5, 3.2, 2.6, col)
    for tx, ty in ((2, 3), (4.5, 1.5), (6.5, 1.5), (9, 3)):
        c.ellipse(tx, ty, 1.1, 1.2, col)
    return c.outline()


def paste(dst, src, x, y):
    for j in range(src.h):
        for i in range(src.w):
            if src.px[j][i]:
                dst.put(x + i, y + j, src.px[j][i])


def crop(src, x, y, w, h):
    out = Canvas(w, h)
    out.px = [row[x:x + w] for row in src.px[y:y + h]]
    return out


def pixel_text(c, x, y, text, col):
    for ch in text:
        if ch == ' ':
            x += 2
            continue
        g = FONT3x5[ch]
        for j, row in enumerate(g):
            for i, bit in enumerate(row):
                if bit == '1':
                    c.put(x + i, y + j, col)
        x += len(g[0]) + 1


def puppy_head(c, x, y):
    """Tiny puppy head (coat slots) for windows, boxes and photos. (x, y) = head centre."""
    c.ellipse(x, y, 4, 3.6, 'A', light='C')
    c.ellipse(x + 3.5, y + 1.2, 2, 1.4, 'C')
    c.ellipse(x - 2.6, y + 0.5, 1.5, 3, 'B')
    c.put(x + 1, y - 1, 'k'); c.put(x + 5, y, 'k'); c.put(x, y + 2, 'N')


def house(c, x, w, h, base_y, wall, roof, door):
    top = base_y - h
    for i in range(9):                                                   # roof, flat-topped
        c.rect(x - 3 + i, top - i, w + 6 - 2 * i, 1, roof)
    ring(c, x + w / 2, top - 4, w / 2 + 4, 6, (roof,))
    box(c, x, top, w, h, wall)
    box(c, x + w // 2 - 3, base_y - 11, 7, 11, door); c.put(x + w // 2 + 2, base_y - 6, 'Y')
    for wx in (x + 3, x + w - 11):
        box(c, wx, top + 4, 8, 8, 'S'); c.rect(wx + 4, top + 4, 1, 8, 'K'); c.rect(wx, top + 8, 8, 1, 'K')
    box(c, x + w - 9, top - 12, 5, 7, 'r')                               # chimney


def draw_panel_car(puppy=True):
    """Panel 1: the drive home (puppy=False: the drive to the rescue centre, an empty box). Visible area is y 15..146."""
    c = Canvas(320, 180)
    c.rect(0, 0, 320, 110, 'S')
    blob(c, 290, 30, 10, 10, 'Y', 'y')                                   # sun
    for cx0, cy0 in ((50, 34), (180, 24), (250, 46)):
        c.ellipse(cx0, cy0, 14, 4.5, 'W'); c.ellipse(cx0 + 8, cy0 - 3, 9, 4.5, 'W')
    for bx, by in ((110, 30), (124, 36), (214, 40)):                     # birds
        c.pattern(bx, by, ['K...K', '.K.K.'])
    for hx, hy, hr in ((30, 92, 60), (160, 96, 80), (290, 90, 60)):      # hills
        c.ellipse(hx, hy, hr, 26, 'M', shade='m')
    for x, w, h, wall, roof, door in ((6, 38, 26, 'N', 'r', 'd'), (58, 44, 30, 'Y', 'd', 'R'), (116, 36, 24, 'L', 'l', 'M'),
                                      (166, 42, 28, 'W', 'R', 'S'), (222, 38, 26, 'M', 'G', 'R'), (276, 40, 30, 'P', 'r', 'd')):
        house(c, x, w, h, 100, wall, roof, door)
    for tx in (50, 108, 214, 268):                                       # trees between houses
        c.rect(tx - 1, 86, 3, 14, 'd'); blob(c, tx, 80, 6, 8, 'm', 'G', light='M')
    for fx in range(0, 320, 6):                                          # picket fence
        c.rect(fx, 93, 4, 11, 'W'); c.put(fx + 1, 92, 'W'); c.put(fx + 2, 92, 'W')
    ring(c, 160, 98, 170, 8, ('W',))
    c.rect(0, 97, 320, 2, 'W')
    c.rect(0, 104, 320, 6, 'E'); c.rect(0, 104, 320, 1, 'K')             # sidewalk
    for sx in range(10, 320, 22):
        c.rect(sx, 105, 1, 5, 'P')
    c.rect(266, 92, 2, 13, 'd'); box(c, 259, 84, 15, 9, 'S'); c.rect(260, 90, 13, 2, 's')   # mailbox
    c.rect(273, 80, 1, 7, 'K'); c.rect(274, 80, 4, 3, 'R')
    c.rect(0, 110, 320, 28, 'L'); c.rect(0, 110, 320, 1, 'K'); c.rect(0, 137, 320, 1, 'K')  # road
    for x in range(6, 320, 30):
        c.rect(x, 123, 14, 2, 'W')
    c.rect(0, 138, 320, 42, 'm')
    for x in range(3, 320, 7):                                            # grass + flowers along the verge
        c.put(x, 140 + (x * 5) % 6, 'G')
        if x % 4 == 0:
            c.put(x, 139 + (x * 3) % 5, 'NYW'[x % 3])
    # the car
    c.ellipse(165, 110, 45, 17, 'K'); c.ellipse(165, 110, 44, 16, 'P', shade='p')
    c.rect(121, 110, 89, 20, 'P'); c.rect(121, 124, 89, 6, 'p')
    c.rect(120, 110, 1, 21, 'K'); c.rect(210, 110, 1, 21, 'K'); c.rect(120, 130, 91, 1, 'K')
    box(c, 128, 96, 31, 15, 'S'); box(c, 162, 96, 30, 15, 'S')
    c.rect(130, 98, 6, 1, 'w'); c.rect(164, 98, 6, 1, 'w')
    c.rect(160, 112, 1, 17, 'p'); c.rect(150, 115, 5, 1, 'K'); c.rect(185, 115, 5, 1, 'K')     # door seam + handles
    box(c, 130, 104, 15, 7, 'D'); c.pattern(129, 102, ['DD...........DD', '.DD.........DD.'])   # box
    if puppy:
        puppy_head(c, 137, 101)                                           # puppy peeking out
        c.pattern(136, 90, ['.R.R.', 'RRRRR', '.RRR.', '..R..'])          # heart above the box
    else:
        c.rect(132, 101, 11, 3, 'L'); c.rect(133, 100, 6, 1, 'L'); c.rect(134, 102, 3, 1, 'l')   # a soft blanket, waiting
        c.pattern(147, 88, ['..Y..', '.YwY.', '..Y..'])                   # an excited sparkle by the kid
        c.rect(300, 66, 2, 38, 'd')                                       # sign: RESCUE ->
        box(c, 270, 56, 44, 13, 'W'); pixel_text(c, 274, 60, 'RESCUE', 'R')
        c.pattern(300, 60, ['.K..', '.KK.', 'KKKK', '.KK.', '.K..'][:5])
    c.ellipse(152, 103, 4, 4, 'F'); c.rect(148, 98, 9, 3, 'M'); c.rect(155, 100, 3, 1, 'M')   # kid in a cap
    c.put(154, 103, 'k'); c.put(155, 105, 'N')
    c.ellipse(181, 103, 4.5, 4.5, 'F'); c.ellipse(180, 99.5, 4.5, 2.5, 'H'); c.rect(176, 100, 2, 5, 'H')  # parent driving
    c.put(183, 103, 'k'); c.rect(188, 104, 3, 5, 'K')                       # steering wheel
    c.rect(208, 114, 3, 4, 'Y'); c.rect(118, 116, 3, 4, 'R')
    for wx in (140, 192):
        c.ellipse(wx, 131, 7.5, 7.5, 'K'); c.ellipse(wx, 131, 5.5, 5.5, 'h'); c.ellipse(wx, 131, 2.2, 2.2, 'E')
    for my in (114, 120, 126):
        c.rect(88, my, 20, 1, 'W'); c.rect(100, my + 3, 12, 1, 'W')
    return c


def draw_panel_porch():
    """Panel 2: arriving home, the puppy sniffs the doormat."""
    c = Canvas(320, 180)
    c.rect(0, 0, 320, 118, 'P')
    for y in range(12, 118, 6):
        c.rect(0, y, 320, 1, 'p')
    c.rect(0, 0, 320, 8, 'r'); c.rect(0, 8, 320, 1, 'K')                   # eave
    for wx in (26, 226):                                                    # windows + flower boxes
        box(c, wx, 34, 68, 50, 'W'); box(c, wx + 4, 38, 60, 42, 'S')
        c.rect(wx + 4, 38, 60, 6, 'M'); c.rect(wx + 4, 44, 60, 1, 'm')
        c.rect(wx + 34, 44, 1, 36, 'K'); c.rect(wx + 4, 62, 60, 1, 'K')
        c.rect(wx + 7, 47, 6, 1, 'w')
        box(c, wx - 2, 86, 72, 9, 'd')
        for fx in range(wx + 1, wx + 68, 4):
            c.put(fx, 85, 'm'); c.put(fx + 1, 84, 'NYL'[(fx // 4) % 3]); c.put(fx + 2, 85, 'G')
    box(c, 128, 32, 64, 87, 'W')                                            # door frame
    box(c, 133, 37, 54, 82, 'E')                                            # hallway inside
    c.rect(134, 100, 52, 18, 'D'); c.rect(134, 100, 52, 1, 'd')
    c.ellipse(160, 110, 18, 4, 'L')                                         # hall rug
    box(c, 165, 52, 12, 10, 'd'); box(c, 167, 54, 8, 6, 'Y')                # picture inside
    c.rect(134, 38, 12, 80, 'R'); c.rect(144, 38, 2, 80, 'r'); c.rect(134, 38, 12, 1, 'K')    # open door
    c.rect(141, 76, 2, 3, 'Y')
    box(c, 114, 48, 8, 11, 'Y'); c.rect(114, 46, 8, 3, 'K'); c.rect(116, 50, 4, 6, 'w')        # porch lamp
    box(c, 198, 46, 16, 11, 'W')
    c.pattern(201, 49, ['.K..KKK', 'KK....K', '.K..KKK', '.K..K..', 'KKK.KKK'])  # house number 12
    c.rect(0, 118, 320, 12, 'D'); c.rect(0, 118, 320, 1, 'K')               # porch floor
    for x in range(0, 320, 26):
        c.rect(x, 119, 1, 11, 'd')
    box(c, 92, 130, 136, 8, 'E'); box(c, 84, 138, 152, 9, 'E')               # steps
    c.rect(0, 130, 92, 50, 'm'); c.rect(228, 130, 92, 50, 'm')
    for bx in (30, 62, 258, 290):
        blob(c, bx, 134, 14, 8, 'm', 'G', light='M')
    box(c, 132, 121, 56, 7, 'R'); c.pattern(156, 122, ['W.W.W', '.WWW.', '.WWW.'])              # doormat
    for px0 in (66, 248):                                                    # potted plants on the porch
        box(c, px0, 106, 14, 12, 'R'); c.rect(px0 + 1, 113, 12, 4, 'r')
        blob(c, px0 + 4, 100, 4, 6, 'm', 'G'); blob(c, px0 + 10, 99, 4, 7, 'm', 'G')
    box(c, 204, 104, 28, 16, 'D'); c.rect(205, 112, 26, 1, 'd')               # the box
    c.pattern(202, 100, ['DDD......................DDD', '.DDD....................DDD.', '..DD....................DD..'])
    c.pattern(213, 107, ['.R.R.', 'RRRRR', '.RRR.', '..R..'])
    pup = puppy_anims()['sniff'][0]
    paste(c, pup, 146, 124 - 30)
    return c


def draw_panel_fridge():
    """Panel 3: the parent explains the rules. A chore chart on the fridge."""
    c = Canvas(320, 180)
    c.rect(0, 0, 320, 180, 'S')
    for y in range(0, 180, 8):
        c.rect(0, y, 320, 1, 's')
        for x in range(8 if (y // 8) % 2 else 0, 320, 16):
            c.rect(x, y, 1, 8, 's')
    box(c, 12, 18, 46, 46, 'W'); c.rect(13, 19, 44, 9, 'R')                 # calendar
    for j in range(4):
        for i in range(6):
            c.rect(16 + i * 7, 32 + j * 7, 3, 3, 'E')
    c.ellipse(32.5, 40.5, 4, 4, 'R'); c.ellipse(32.5, 40.5, 3, 3, 'W'); c.rect(31, 39, 3, 3, 'E')
    box(c, -1, 104, 70, 50, 'M'); box(c, -1, 98, 74, 7, 'E')                # counter
    c.rect(30, 112, 6, 2, 'Y')
    box(c, 270, 14, 60, 70, 'W'); box(c, 274, 18, 52, 62, 'S'); c.rect(274, 18, 52, 8, 'M')   # window
    box(c, 80, 4, 172, 160, 'W'); c.rect(236, 5, 15, 158, 'E')              # fridge
    c.rect(81, 54, 170, 1, 'K')
    box(c, 230, 20, 5, 26, 's'); box(c, 230, 64, 5, 40, 's')
    box(c, 98, 18, 48, 32, 'W'); c.rect(110, 16, 10, 4, 'Y'); c.rect(126, 16, 10, 4, 'Y')   # crayon drawing
    c.ellipse(108, 25, 3, 3, 'Y')
    c.pattern(114, 31, ['....OO.OO..', 'OOOOOOOOOO.', 'O.......OOO', 'OOOOOOOOO..', '.O.O..O.O..'])
    c.rect(100, 44, 44, 1, 'm')
    box(c, 186, 18, 32, 32, 'W'); box(c, 189, 21, 26, 21, 'S'); c.rect(190, 36, 24, 5, 'D')  # photo of the puppy
    puppy_head(c, 201, 32)
    blob(c, 202, 17, 2.5, 2.5, 'M', 'K')                                     # magnet
    box(c, 106, 62, 116, 82, 'W'); c.rect(107, 63, 114, 11, 'L')            # chore chart
    pixel_text(c, 140, 66, 'PUPPY JOBS', 'K')
    blob(c, 108, 63, 3, 3, 'Y', 'K'); blob(c, 220, 63, 3, 3, 'R', 'K')       # magnets
    for r, (name, done) in enumerate((('bowl', 3), ('pad', 1), ('heart', 2))):
        y = 78 + r * 22
        paste(c, icon(name), 110, y)
        for d in range(4):
            box(c, 134 + d * 21, y + 3, 11, 11, 'W')
            if d < done:
                c.pattern(135 + d * 21, y + 5, ['........m', '.......mm', 'm.....mm.', 'mm...mm..', '.mm.mm...', '..mmm....', '...m.....'])
        c.rect(110, y + 19, 108, 1, 'E')
    return c


def draw_panel_supplies():
    """Panel 4: the puppy's new things, ready to start."""
    c = Canvas(320, 180)
    wall_and_floor(c, 100)
    for i, x in enumerate(range(10, 312, 14)):                             # welcome bunting
        top = 21 + round(5 * math.sin(math.pi * x / 320))
        for r in range(6):
            c.rect(x + r // 2, top + r, 9 - r, 1, 'RYMSL'[i % 5])
    for x in range(0, 320):
        c.put(x, 20 + round(5 * math.sin(math.pi * x / 320)), 'K')
    c.rect(252, 46, 4, 3, 'K')                                              # wall hook with the new leash
    for y in range(49, 84):
        c.put(253 + round(4 * math.sin((y - 49) / 6)), y, 'R'); c.put(254 + round(4 * math.sin((y - 49) / 6)), y, 'R')
    blob(c, 255, 86, 3, 2, 'R', 'K'); c.put(255, 86, 'Y')
    for lx, ly, rx, ry in ((296, 74, 5, 4), (310, 74, 5, 4), (299, 66, 4, 6), (307, 66, 4, 6), (303, 70, 4, 11)):   # plant
        blob(c, lx, ly, rx, ry, 'm', 'G', light='M')
    box(c, 296, 84, 15, 16, 'R'); c.rect(297, 94, 13, 5, 'r'); box(c, 294, 81, 19, 4, 'R')
    box(c, 136, 34, 48, 36, 'd'); box(c, 139, 37, 42, 30, 'S')             # framed picture
    c.ellipse(160, 58, 14, 6, 'M'); c.ellipse(152, 45, 4, 3, 'Y')
    paste(c, draw_food_big('kibble'), 22, 134 - 48)
    box(c, 84, 124, 36, 12, 'R'); c.rect(85, 131, 34, 4, 'r'); c.rect(83, 122, 38, 3, 'W')    # big bowl
    c.ellipse(102, 122, 15, 2.5, 'D')
    for i in range(3):                                                       # stack of pads
        y = 128 - i * 4
        box(c, 220 + i, y, 50, 5, 'W'); c.put(230 + i * 3, y + 2, 'S'); c.put(250 - i * 2, y + 2, 'S')
    paste(c, icon('treat'), 194, 122)
    blob(c, 290, 128, 7, 7, 'R', 'K', light='N'); c.rect(284, 127, 13, 2, 'W')   # ball
    paste(c, puppy_anims()['sit'][0], 146, 134 - 30)
    paste(c, icon('heart'), 154, 82)
    return c


PANELS = {'car': draw_panel_car, 'porch': draw_panel_porch, 'fridge': draw_panel_fridge, 'supplies': draw_panel_supplies}


def draw_album_bg():
    c = Canvas(320, 180)
    c.rect(0, 0, 320, 180, 'D')
    for y in range(6, 180, 9):
        c.rect(0, y, 320, 1, 'd')
        for x in range((y * 13) % 60, 320, 60):
            c.rect(x, y - 8, 1, 8, 'd')
    for px0 in (22, 160):                                                   # page stacks
        box(c, px0, 16, 138, 154, 'E')
        box(c, px0 + (2 if px0 == 22 else -2), 13, 138, 154, 'W')
    c.rect(156, 13, 8, 154, 'E'); c.rect(159, 13, 2, 154, 'P')              # spine
    c.rect(282, 8, 8, 166, 'R'); c.rect(288, 8, 2, 166, 'r')                # ribbon bookmark
    c.pattern(282, 174, ['RRRRRRRR', 'RRR..RRR', 'RR....RR'])
    c.rect(282, 8, 8, 1, 'K')
    for dx, dy in ((34, 150), (140, 22), (182, 150), (262, 24)):            # doodles
        c.pattern(dx, dy, ['.N.N.', 'NNNNN', '.NNN.', '..N..'])
    return c


def polaroid():
    c = Canvas(64, 62)
    box(c, 0, 0, 64, 62, 'W'); c.rect(1, 58, 62, 3, 'E')
    box(c, 5, 5, 54, 44, 'S')
    c.rect(6, 36, 52, 12, 'D'); c.rect(6, 36, 52, 1, 'd')                   # floor inside the photo
    c.ellipse(20, 16, 6, 2.5, 'W')
    c.rect(24, 0, 16, 5, 'Y'); c.rect(24, 4, 16, 1, 'y')                    # tape
    return c


def spotlight():
    c = Canvas(84, 18)
    for y in range(18):
        for x in range(84):
            r = ((x + 0.5 - 42) / 41) ** 2 + ((y + 0.5 - 9) / 8.5) ** 2
            if r <= 0.6 or (r <= 1.0 and (x + y) % 2 == 0):
                c.put(x, y, 'W' if r <= 0.6 else 'E')
    return c


def group4():
    out, S4 = {}, 'Screens'
    out['assets/screens/logo.png'] = ([logo()], None, {'section': 'Title', 'anim': 'logo', 'note': 'Shown at the top of the title screen'})
    out['assets/screens/title_bg.png'] = ([draw_title_bg()], None, {'section': 'bg', 'anim': 'title'})
    for name, fn in PANELS.items():                                     # one sheet per coat (the puppy appears in each)
        art = fn()
        for coat, cols in COATS.items():
            out[f'assets/screens/panel_{name}_{coat}.png'] = ([art], cols, {'section': 'bg', 'anim': name})
    out['assets/screens/album_bg.png'] = ([draw_album_bg()], None, {'section': 'bg', 'anim': 'album'})
    out['assets/screens/polaroid.png'] = ([polaroid()], None, {'section': 'Album and retry', 'anim': 'polaroid', 'note': "The dog's photo goes inside"})
    out['assets/screens/spotlight.png'] = ([spotlight()], None, {'section': 'Album and retry', 'anim': 'spotlight', 'note': 'Under the sad dog on the retry screen'})
    out['assets/screens/paw_empty.png'] = ([paw_print(False)], None, {'section': 'Loading', 'anim': 'paw empty', 'note': 'Progress bar, not loaded yet'})
    out['assets/screens/paw_full.png'] = ([paw_print(True)], None, {'section': 'Loading', 'anim': 'paw full', 'note': 'Progress bar, loaded'})
    return out


def screen_mockups():
    cream = Canvas(320, 180); cream.rect(0, 0, 320, 180, 'W')
    bm, bc = button('M', 'm', 'Y')[0], button('W', 'E', 'Y')[0]
    sp, ci = speech_bubble(), panel(18, 18, 'W', ring='E')
    t = lambda x, y, w, s, size, col='#5A3E36', al='center': ('@text', x, y, w, s, size, col, al)
    title = [('assets/screens/title_bg.png', 0, 0, 2), ('assets/screens/logo.png', 216, 52, 2),
             ('assets/sprites/puppy_caramel_wag.png', 288, 244, 2),
             ('@canvas', nine(bm, 56, 16, 5), 264, 178, 2), t(264, 186, 112, 'Play', 18),
             ('@canvas', nine(bc, 16, 16, 5), 604, 8, 2), ('@canvas', icon('sound_on'), 604, 8, 2)]
    loading = [('@canvas', cream, 0, 0, 2), ('assets/sprites/puppy_caramel_circle.png', 288, 120, 2)] + \
              [('@canvas', paw_print(i < 5), 216 + i * 26, 210, 2) for i in range(8)] + \
              [t(120, 252, 400, 'Tip: Puppies sleep up to 18 hours a day.', 15, '#8a6f66')]
    head = crop(parent_frames()['talk'][1], 11, 5, 26, 26)           # parent's face for the text bar (setCrop in game)

    def panel_mock(name, line):
        return [(f'assets/screens/panel_{name}_caramel.png', 0, 0, 2), ('@rect', 0, 0, 640, 30, '#D7C4EC'),
                ('@rect', 0, 292, 640, 68, '#D7C4EC'), ('@canvas', nine(ci, 30, 30, 6), 8, 296, 2), ('@canvas', head, 12, 300, 2),
                ('@canvas', nine(sp, 270, 26, 5), 82, 302, 2), t(98, 312, 520, line, 16, '#5A3E36', 'left'),
                t(560, 8, 72, 'Skip', 13, '#5A3E36', 'right')]
    opening = [panel_mock('car', "We're bringing home a new puppy today!"),
               panel_mock('porch', 'Welcome home, Biscuit! Everything smells new.'),
               panel_mock('fridge', "Taking care of Biscuit is your job now. Don't worry, I'll help at first."),
               panel_mock('supplies', "Puppies need the right food, and they need to learn where to go potty. Let's start there!")]
    growth = [('assets/bg/living_room.png', 0, -60, 2), ('@rect', 0, 0, 640, 30, '#D7C4EC'), ('@rect', 0, 292, 640, 68, '#D7C4EC'),
              ('assets/sprites/puppy_caramel_sit.png', 210, 210, 2), ('assets/sprites/young_caramel_wag.png', 330, 196, 2),
              ('@canvas', icon('star'), 300, 190, 2), ('@canvas', icon('star'), 420, 172, 2), ('@canvas', icon('star'), 196, 186, 2),
              ('@canvas', nine(sp, 300, 26, 5), 20, 302, 2), t(36, 316, 560, "Look how much Biscuit has grown! You're doing a great job.", 16, '#5A3E36', 'left')]
    album = [('assets/screens/album_bg.png', 0, 0, 2), ('assets/screens/polaroid.png', 82, 62, 2),
             ('assets/sprites/puppy_caramel_wag.png', 116, 102, 2),
             t(54, 36, 210, 'Day 1', 24, '#5A3E36'), t(82, 186, 128, 'Biscuit', 16),
             t(340, 40, 230, 'You learned:', 18, '#5A3E36', 'left'),
             ('@canvas', icon('bowl'), 340, 84, 2), t(380, 92, 200, 'Safe foods', 16, '#5A3E36', 'left'), ('@canvas', icon('check'), 530, 84, 2),
             ('@canvas', icon('pad'), 340, 132, 2), t(380, 140, 200, 'Potty spot', 16, '#5A3E36', 'left'), ('@canvas', icon('check'), 530, 132, 2),
             ('@canvas', stamp(), 380, 196, 2),
             ('@canvas', nine(bm, 56, 16, 5), 380, 280, 2), t(380, 288, 112, 'Next', 18)]
    retry = [('assets/bg/living_room.png', 0, 0, 2), ('@rect', 0, 0, 640, 360, 'rgba(62,42,36,.55)'),
             ('assets/screens/spotlight.png', 236, 312, 2), ('assets/sprites/puppy_caramel_sad.png', 288, 270, 2),
             ('@canvas', nine(ci, 52, 50, 6), 70, 40, 2), ('assets/sprites/parent_idle.png', 74, 42, 2),
             ('@canvas', nine(sp, 170, 40, 5), 194, 54, 2), ('@canvas', speech_tail(), 178, 80, 2),
             t(212, 66, 310, "Biscuit got too hungry and sad. Remember: only dog-safe food. Let's try again!", 16, '#5A3E36', 'left'),
             ('@canvas', nine(bm, 64, 16, 5), 256, 160, 2), t(256, 168, 128, 'Try again', 18)]
    W = (640, 360)
    return [('Title screen', W, title), ('Loading', W, loading),
            ('Opening 1 of 4: the drive home', W, opening[0]), ('Opening 2 of 4: arriving home', W, opening[1]),
            ('Opening 3 of 4: the rules', W, opening[2]), ('Opening 4 of 4: time to start', W, opening[3]),
            ('Growth cutscene', W, growth), ('Album page (level complete)', W, album), ('Retry (meter ran out)', W, retry)]


# ---------------------------------------------------------------- group 5: on-screen keyboard + rotate screen
KEY_ROWS = ('QWERTYUIOP', 'ASDFGHJKL', 'ZXCVBNM')
KEY_W, KEY_H, KEY_GAP = 50, 30, 4          # canvas px (the art is drawn at 2x)


def draw_rotate_icon():
    """A phone turning from upright to sideways."""
    c = Canvas(52, 28)
    box(c, 2, 2, 14, 24, 'W'); box(c, 4, 5, 10, 16, 'S'); c.rect(7, 22, 4, 1, 'K')            # upright phone
    c.rect(20, 12, 9, 3, 'Y')
    c.pattern(28, 10, ['Y....', 'YY...', 'YYY..', 'YYYY.', 'YYY..', 'YY...', 'Y....'])         # arrow
    box(c, 33, 8, 18, 12, 'W'); box(c, 35, 10, 12, 8, 'S'); c.rect(49, 13, 1, 2, 'K')         # sideways phone
    c.pattern(39, 12, ['R.R', 'RRR', '.R.'])                                                    # a heart on its screen
    return c


def group5():
    return {'assets/ui/icon_rotate.png': ([draw_rotate_icon()], None,
            {'section': 'Rotate screen icon', 'anim': 'turn your phone', 'note': 'Shown on the rotate screen (portrait phones)'})}


def keyboard_mockups():
    bm, bc = button('M', 'm', 'Y'), button('W', 'E', 'Y')
    ci = panel(18, 18, 'W', ring='E')
    t = lambda x, y, w, s, size, col='#5A3E36', al='center': ('@text', x, y, w, s, size, col, al)
    kw, kh, pitch = KEY_W, KEY_H, KEY_H + KEY_GAP
    items = [('assets/screens/title_bg.png', 0, 0, 2), ('assets/sprites/puppy_caramel_wag.png', 288, 244, 2),
             t(0, 36, 640, 'Meet your new puppy!', 20),
             ('@canvas', nine(ci, 280, 96, 6), 40, 62, 2),                                   # card: y 62..254, puppy's head starts at 258
             t(64, 76, 60, 'Coat', 16, al='left')]
    for i, coat in enumerate(('cream', 'caramel', 'chocolate')):
        items.append((f'assets/ui/swatch_{coat}.png', 132 + i * 44, 70, 2))
    items.append(('assets/ui/swatch_ring.png', 132 + 44 - 4, 66, 2))
    items += [t(64, 118, 60, 'Name', 16, al='left'), ('@canvas', nine(ci, 80, 18, 6), 112, 108, 2), t(124, 117, 120, 'Mochi', 18, al='left'),
              ('@rect', 190, 116, 2, 20, '#5A3E36'),
              ('@canvas', nine(bc[0], 18, 18, 5), 278, 108, 2), ('@canvas', icon('star'), 280, 110, 2), t(320, 119, 80, 'Random', 13, '#8a6f66', 'left'),
              ('@canvas', nine(bm[0], 60, 18, 5), 440, 108, 2), t(440, 117, 120, 'Adopt!', 18)]
    # the keys: QWERTY rows, backspace at the end of the last row ("O" is shown pressed)
    for r, row in enumerate(KEY_ROWS):
        n = len(row)
        total = n * kw + (n - 1) * KEY_GAP + ((KEY_GAP + 2 * kw + KEY_GAP) if r == 2 else 0)
        x0, y = (640 - total) // 2, 152 + r * pitch
        for i, ch in enumerate(row):
            x, pressed = x0 + i * (kw + KEY_GAP), ch == 'O'
            items += [('@canvas', nine(bc[2 if pressed else 0], kw // 2, kh // 2, 5), x, y, 2), t(x, y + (8 if pressed else 6), kw, ch, 16)]
        if r == 2:
            x = x0 + n * (kw + KEY_GAP)
            items += [('@canvas', nine(bc[0], kw + KEY_GAP // 2, kh // 2, 5), x, y, 2), t(x, y + 7, 2 * kw + KEY_GAP, 'Del', 15)]
    rot = [('@rect', 0, 0, 320, 568, '#FFF4E0'), ('@canvas', draw_rotate_icon(), 56, 170, 4),
           t(30, 318, 260, 'Turn your phone sideways to play!', 22), t(30, 400, 260, 'Pawfect Parents is made for wide screens.', 14, '#8a6f66')]
    return [('Dog setup with the on-screen keyboard', (640, 360), items), ('Turn-your-phone screen', (320, 568), rot)]


# ---------------------------------------------------------------- group 6: Level 2, the vet clinic
# Characters first (young-dog poses, adult dog, vet), then icons, then the clinic scene, close-ups and cutscene panels.
ADULT = dict(w=48, h=48, body=(19, 31, 13, 7), head=(34, 18, 8), snout=(41, 22, 5, 3),
             ear=(28, 18, 3, 6), legs_back=(10, 14), legs_front=(25, 30), leg_top=34, ground=46,
             tail=(7, 26), tail_len=10, collar_x=26)


def young_anims_l2():
    D = lambda **kw: draw_dog(YOUNG, **kw)
    return {'sit': [D(pose='sit', tail=15), D(pose='sit', tail=25, eyes='closed')],
            # nervous on the exam table: ears back, tail tucked, a tiny tremble
            'nervous': [D(body_dy=2, head=(-1, 3), tuck=True, eyes='sad', ear=(-2, 2)),
                        D(body_dy=2, head=(-2, 3), tuck=True, eyes='sad', ear=(-2, 2))],
            'sad': [D(pose='lie', head=(1, 8), tail=-15, eyes='sad', ear=(0, 2)),
                    D(pose='lie', head=(1, 8), tail=-15, eyes='closed', ear=(0, 2))]}


def adult_anims():
    D = lambda **kw: draw_dog(ADULT, **kw)
    return {'idle': [D(tail=45), D(tail=50), D(tail=50, eyes='closed'), D(tail=45)],
            'wag': [D(tail=t, eyes='happy', mouth='open') for t in (55, 85, 110, 85)]}


def draw_vet(mouth='closed', blink=False):
    """Vet bust, same 48x48 framing as the parent so the face crop (11,5,26,26) works in cutscenes."""
    c = Canvas(48, 48)
    c.ellipse(24, 47, 17, 10, 'W', shade='E')            # white coat
    c.rect(18, 36, 12, 4, 'M')                           # mint scrubs under it
    c.rect(21, 30, 6, 7, 'f')                            # neck
    c.pattern(15, 38, ['l.........', 'l.........', 'l.........', '.l........', '..l.......', '...llll...'])   # stethoscope tube
    c.pattern(33, 38, ['.........l', '.........l', '.........l', '........l.', '.......l..', '...llll...'][:5])
    c.ellipse(24, 44, 2.5, 2.5, 'S'); c.put(24, 44, 'K')                                                    # chest piece
    c.ellipse(24, 21, 10, 11, 'F')                       # face
    c.ellipse(24, 12, 11, 7, 'T')                        # blond hair
    c.rect(13, 13, 3, 10, 'T'); c.rect(32, 13, 3, 10, 'T')
    c.pattern(15, 14, ['TTTTTTTTTTTTTTTTTT', 'TTTT..TTTTTT..TTTT', 'TT..............TT'])
    c.rect(13, 21, 2, 2, 't'); c.rect(33, 21, 2, 2, 't')
    for lx in (17, 26):                                   # round glasses
        c.pattern(lx, 18, ['.KKKK.', 'KWWWWK', 'KWWWWK', 'KWWWWK', 'KWWWWK', '.KKKK.'])
    c.rect(23, 20, 3, 1, 'K')
    if blink:
        c.rect(19, 21, 3, 1, 'k'); c.rect(27, 21, 3, 1, 'k')
    else:
        c.rect(19, 20, 2, 3, 'k'); c.put(20, 20, 'w')
        c.rect(28, 20, 2, 3, 'k'); c.put(29, 20, 'w')
    c.rect(16, 25, 2, 1, 'N'); c.rect(31, 25, 2, 1, 'N')
    if mouth == 'open':
        c.pattern(22, 26, ['kkkk', 'kNNk', '.kk.'])
    else:
        c.pattern(22, 26, ['k..k', '.kk.'])
    return c.outline()


def vet_frames():
    return {'talk': [draw_vet('closed'), draw_vet('open'), draw_vet('closed'), draw_vet('open')],
            'idle': [draw_vet(), draw_vet(), draw_vet(blink=True), draw_vet()]}


def draw_vet_body(blink=False):
    """Full-length vet, 36x82 (two spare rows on top so the hair gets an outline), facing left (towards the dog)."""
    c = Canvas(36, 80)
    c.rect(11, 62, 6, 13, 'l'); c.rect(19, 62, 6, 13, 'l')                        # scrub trousers
    c.rect(9, 74, 8, 4, 'R'); c.rect(19, 74, 8, 4, 'R'); c.rect(9, 76, 8, 2, 'r'); c.rect(19, 76, 8, 2, 'r')   # sneakers
    c.rect(15, 24, 6, 5, 'f')                                                      # neck
    c.ellipse(18, 33, 11, 6, 'W')                                                  # shoulders
    c.rect(8, 33, 20, 33, 'W'); c.rect(24, 33, 4, 33, 'E'); c.rect(8, 64, 20, 2, 'E')   # lab coat
    c.pattern(14, 28, ['MMMMMMMM', '.MMMMMM.', '..MMMM..'])                       # scrubs at the neck
    c.rect(17, 36, 2, 29, 'E')                                                     # coat opening
    box(c, 10, 52, 7, 6, 'E')                                                      # pocket
    c.rect(11, 49, 1, 4, 'R'); c.rect(14, 49, 1, 4, 'Y')                           # pens
    c.rect(4, 34, 5, 20, 'W'); c.rect(27, 34, 5, 22, 'E')                          # arms
    c.ellipse(6, 56, 2.4, 2.4, 'F'); c.ellipse(29, 58, 2.4, 2.4, 'F')              # hands
    box(c, 0, 46, 10, 14, 'D'); c.rect(1, 48, 8, 10, 'W'); c.rect(3, 44, 4, 3, 's')   # clipboard
    for ly in (50, 53, 56):
        c.rect(2, ly, 6, 1, 'S')
    c.ellipse(18, 13, 10, 11, 'F')                                                 # head
    c.ellipse(18, 6, 11, 6, 'T'); c.rect(8, 6, 3, 13, 'T'); c.rect(25, 6, 3, 13, 'T')
    c.pattern(9, 8, ['TTTTTTTTTTTTTTTTTT', 'TTT..TTTTTT..TTTTT'])
    for lx in (9, 16):                                                              # round glasses, looking left
        c.pattern(lx, 11, ['.KKKK.', 'KWWWWK', 'KWWWWK', 'KWWWWK', '.KKKK.'])
    c.put(15, 12, 'K')
    if blink:
        c.rect(10, 14, 3, 1, 'k'); c.rect(17, 14, 3, 1, 'k')
    else:
        c.rect(11, 13, 2, 2, 'k'); c.put(11, 13, 'w'); c.rect(17, 13, 2, 2, 'k'); c.put(17, 13, 'w')
    c.pattern(11, 19, ['k..k', '.kk.'])
    c.put(8, 16, 'f')
    c.rect(11, 17, 2, 1, 'N'); c.rect(21, 17, 2, 1, 'N')
    c.pattern(12, 29, ['l.......l', 'l.......l', 'l.......l', '.l.....l.', '.l.....l.', '..l...l..', '...lll...'])   # stethoscope
    c.ellipse(16, 41, 2.5, 2.5, 'S'); c.put(16, 41, 'K')
    out = Canvas(36, 82)
    paste(out, c, 0, 2)
    return out.outline()


def line(c, x0, y0, x1, y1, col, t=1):
    """Pixel line with a t x t brush."""
    n = max(abs(x1 - x0), abs(y1 - y0)) or 1
    for i in range(n + 1):
        c.rect(round(x0 + (x1 - x0) * i / n), round(y0 + (y1 - y0) * i / n), t, t, col)


def ring_blob(c, cx, cy, col):
    """A finger loop: a ring of `col` with a hole."""
    for y in range(cy - 3, cy + 4):
        for x in range(cx - 3, cx + 4):
            r = (x - cx) ** 2 + (y - cy) ** 2
            if 2 <= r <= 9:
                c.put(x, y, col)


ICONS_L2 = {
    'vet':        lambda c: (box(c, 2, 2, 12, 12, 'R'), c.rect(7, 4, 2, 8, 'W'), c.rect(4, 7, 8, 2, 'W'), c.rect(3, 12, 10, 1, 'r')),
    'toothbrush': lambda c: (c.rect(1, 9, 9, 3, 'M'), c.rect(1, 11, 9, 1, 'm'), c.rect(10, 8, 5, 4, 'W'),
                             c.rect(10, 4, 5, 4, 'S'), c.put(11, 4, 'w'), c.put(13, 4, 'w'), c.put(12, 6, 's'), c.put(14, 6, 's')),
    'toothpaste': lambda c: (c.rect(2, 5, 3, 7, 'E'), c.rect(5, 5, 8, 7, 'W'), c.rect(6, 7, 6, 3, 'S'), c.rect(5, 11, 8, 1, 'E'),
                             c.rect(13, 6, 2, 5, 'R'), c.put(8, 8, 'w')),
    'flea':       lambda c: (c.rect(5, 6, 7, 9, 'M'), c.rect(5, 13, 7, 2, 'm'), c.rect(6, 3, 5, 3, 'W'), c.rect(6, 1, 5, 2, 'R'),
                             c.rect(7, 8, 3, 3, 'W'), c.put(8, 9, 'k'), c.put(7, 8, 'k')),
    'clippers':   lambda c: (line(c, 4, 11, 13, 5, 'S', 2), line(c, 4, 5, 13, 10, 'W', 2),
                             ring_blob(c, 4, 11, 'R'), ring_blob(c, 4, 5, 'R'), c.put(8, 8, 'K'), c.put(9, 8, 'K')),
    'ear':        lambda c: (c.ellipse(8, 3.5, 2.8, 2.8, 'R', light='N'), c.rect(6, 5, 4, 2, 'W'), c.rect(5, 7, 6, 8, 'L'),
                             c.rect(5, 13, 6, 2, 'l'), c.rect(6, 9, 4, 3, 'W'), c.put(8, 10, 'S')),
}


def spot_ring(c, col):
    for y in range(10):
        for x in range(10):
            r = ((x + 0.5 - 5) / 4.6) ** 2 + ((y + 0.5 - 5) / 4.6) ** 2
            if 0.35 <= r <= 1.0:
                c.put(x, y, col)
    return c


def spot_frames():
    return [spot_ring(Canvas(10, 10), 'Y').outline(), spot_ring(Canvas(10, 10), 'W').outline()]


# ---- the clinic room
CLINIC = dict(table_x=150, table_top=124, ground=165, vet_x=252, dog_x=146)   # world px; mirrored by CLINIC in src/ui.js


def draw_clinic():
    c = Canvas(320, 180)
    c.rect(0, 0, 320, FLOOR_Y, 'S')
    for y in range(6, 98, 12):                                                   # soft wall dots
        for x in range(4 + (6 if (y // 12) % 2 else 0), 320, 12):
            c.put(x, y, 's')
    c.rect(0, 96, 320, 44, 'W')                                                  # wainscot
    c.rect(0, 96, 320, 1, 'K'); c.rect(0, 97, 320, 2, 's')
    for x in range(0, 320, 24):
        c.rect(x, 104, 1, 34, 'E')
    c.rect(0, FLOOR_Y - 4, 320, 4, 'E'); c.rect(0, FLOOR_Y - 4, 320, 1, 'K')    # baseboard
    c.rect(0, FLOOR_Y, 320, 40, 'W'); c.rect(0, FLOOR_Y, 320, 1, 'K')          # tiled floor
    for i, y in enumerate(range(FLOOR_Y, 180, 10)):
        c.rect(0, y, 320, 1, 'E')
        for x in range(10 if i % 2 else 0, 320, 20):
            c.rect(x, y, 1, 10, 'E')
    # window (left) looking out at a sunny garden
    box(c, 14, 28, 58, 50, 'W'); box(c, 18, 32, 50, 42, 'S')
    c.rect(18, 58, 50, 16, 'm'); c.rect(18, 58, 50, 1, 'G')
    c.ellipse(34, 44, 7, 3, 'W'); c.ellipse(41, 42, 5, 3, 'W'); blob(c, 56, 42, 5, 5, 'Y', 'y')
    c.rect(42, 32, 1, 42, 'K'); c.rect(18, 52, 50, 1, 'K')
    box(c, 10, 76, 66, 5, 'E')
    # wall cabinet with a first-aid cross (right)
    box(c, 226, 22, 84, 44, 'W')
    for dx in (229, 270):
        box(c, dx, 25, 38, 38, 'M'); c.rect(dx + 1, 26, 36, 1, 'w')
    box(c, 262, 36, 12, 12, 'R'); c.rect(267, 38, 2, 8, 'W'); c.rect(264, 41, 8, 2, 'W')
    # tooth poster and paw-print certificate
    box(c, 96, 22, 32, 42, 'L'); c.rect(97, 23, 30, 4, 'l')
    c.pattern(103, 32, ['..WW...WW..', '.WWWW.WWWW.', 'WWWWWWWWWWW', 'WWWWWWWWWWW', 'WWWWWWWWWWW', '.WWWWWWWWW.', '.WWW...WWW.',
                        '.WWW...WWW.', '..WW...WW..'])
    ring(c, 108.5, 36.5, 8, 7, ('W',))
    c.pattern(118, 30, ['.Y.', 'YwY', '.Y.']); c.pattern(98, 52, ['.Y.', 'YwY', '.Y.'])
    c.rect(100, 56, 24, 1, 'l'); c.rect(100, 59, 16, 1, 'l')
    box(c, 150, 28, 36, 28, 'd'); box(c, 153, 31, 30, 22, 'Y')
    c.pattern(162, 35, ['K.K.K.K', '.......', '..KKK..', '.KKKKK.', '..KKK..'])
    # supplies counter with a scale and a jar (far right, behind the vet)
    box(c, 214, 104, 100, 5, 'E'); c.rect(215, 105, 98, 1, 'w')
    box(c, 218, 109, 92, 31, 'M')
    for dx in (221, 255, 289):
        box(c, dx, 112, 28, 24, 'M'); c.rect(dx + 11, 117, 6, 2, 'Y')
    box(c, 296, 92, 12, 12, 'S'); c.rect(298, 94, 8, 3, 'W'); c.rect(300, 87, 4, 5, 'R')     # jar with a cap
    # exam table with a mint mat
    tx, tt = CLINIC['table_x'], CLINIC['table_top']
    for lx in (tx - 44, tx + 40):                                                  # legs
        box(c, lx, tt + 8, 5, 164 - tt - 8, 'S'); c.rect(lx + 3, tt + 9, 1, 164 - tt - 10, 's')
    box(c, tx - 44, 150, 93, 4, 'S')                                              # lower shelf
    box(c, tx - 50, tt, 105, 9, 'W'); c.rect(tx - 49, tt + 6, 103, 2, 'E')       # table slab
    box(c, tx - 40, tt - 5, 85, 7, 'M'); c.rect(tx - 39, tt - 4, 83, 1, 'w'); c.rect(tx - 39, tt, 83, 1, 'm')     # mat the dog stands on
    c.ellipse(tx, 167, 56, 3, 'E')                                                 # soft floor shadow
    return c


# ---- check-up close-ups: a magnifying glass over the spot being examined (coat slots A/B/C, so one sheet per coat)
LENS = (166, 124, 50)          # centre x, centre y, radius (world px). Leaves y<69 free for the vet's speech bubble


def thick_line(c, x0, y0, x1, y1, col, t):
    line(c, x0 - t // 2, y0 - t // 2, x1 - t // 2, y1 - t // 2, col, t)


def lens_scene(draw_inner):
    c = Canvas(320, 180)
    c.rect(0, 0, 320, 180, 'S')
    for y in range(6, 180, 12):
        for x in range(4 + (6 if (y // 12) % 2 else 0), 320, 12):
            c.put(x, y, 's')
    cx, cy, r = LENS
    inner = Canvas(320, 180)
    draw_inner(inner)
    thick_line(c, cx + 36, cy + 36, cx + 62, cy + 54, 'K', 9)                      # handle
    thick_line(c, cx + 36, cy + 36, cx + 62, cy + 54, 'D', 7)
    for y in range(180):
        for x in range(320):
            d2 = (x + 0.5 - cx) ** 2 + (y + 0.5 - cy) ** 2
            if d2 <= r * r:
                c.put(x, y, inner.get(x, y) or 'E')
            elif d2 <= (r + 4) ** 2:
                c.put(x, y, 'Y')
            if (r - 1) ** 2 <= d2 <= r * r or (r + 4) ** 2 <= d2 <= (r + 5) ** 2:
                c.put(x, y, 'K')
    c.pattern(cx - 38, cy - 40, ['wwww', 'w...', 'w...'])                           # glass glint
    return c


def inner_teeth(c):
    c.rect(100, 70, 120, 110, 'r')                                                  # inside of the mouth
    c.rect(100, 70, 120, 28, 'A'); c.rect(100, 92, 120, 6, 'B')                     # fur above the lip
    blob(c, 160, 82, 13, 7, 'k', 'K'); c.rect(154, 78, 5, 2, 'w')                   # nose
    c.rect(100, 98, 120, 9, 'N'); c.rect(100, 105, 120, 2, 'p')                      # upper gum
    for (x, w, h, tar) in ((114, 11, 24, 11), (128, 9, 15, 8), (139, 9, 14, 7), (150, 9, 15, 9),
                           (161, 9, 14, 6), (172, 9, 15, 8), (183, 9, 14, 7), (195, 11, 24, 12)):
        box(c, x, 106, w, h, 'W')                                                    # upper teeth
        c.rect(x + 1, 107, w - 2, tar, 'y')                                          # yellow-brown tartar from the gum down
        c.rect(x + 1, 106 + tar, w - 2, 1, 't')
        c.put(x + 2, 108, 't'); c.put(x + w - 3, 110 + tar // 2, 't')
    c.ellipse(160, 146, 28, 9, 'N', shade='p')                                       # tongue
    c.rect(160, 138, 1, 9, 'p')
    c.rect(100, 152, 120, 28, 'A'); c.rect(100, 152, 120, 3, 'B')                    # lower lip fur
    c.rect(100, 148, 120, 6, 'N')                                                    # lower gum
    for x in range(122, 200, 12):
        box(c, x, 138, 9, 11, 'W'); c.rect(x + 1, 144, 7, 4, 'y'); c.rect(x + 1, 144, 7, 1, 't')   # lower teeth


def inner_coat(c):
    c.rect(100, 70, 120, 110, 'A')
    for j, y in enumerate(range(72, 178, 7)):                                        # fur strokes
        for x in range(100 + (j % 3) * 3, 222, 11):
            c.pattern(x, y, ['B..', '.B.', '..B'] if (x + y) % 3 else ['..C', '.C.', 'C..'])
    for x, y in ((126, 98), (188, 150), (120, 146)):                                 # itchy red bumps
        c.pattern(x, y, ['.R.', 'RRR', '.R.'])
    for i in range(8):                                                               # hop trail
        c.put(126 + i * 4, 146 - i * 3 - (i * i) // 3, 'w')
    blob(c, 166, 110, 14, 10, 'h', 'K', light='H')                                   # the flea, big enough to see
    blob(c, 179, 104, 6, 6, 'h', 'K')
    c.put(181, 103, 'w'); c.put(182, 105, 'w')
    for lx, ly in ((154, 119), (160, 121), (168, 121), (175, 119)):                  # legs
        line(c, lx, ly, lx - 3, ly + 6, 'K', 2)
    c.pattern(184, 92, ['..KK', '.KK.', 'KK..']); c.pattern(188, 96, ['KK..', '.KK.', '..KK'])   # antennae
    for x, y in ((144, 96), (200, 128), (120, 124)):                                 # sparkle lines for the hop
        c.pattern(x, y, ['.w.', 'www', '.w.'])


def inner_paws(c):
    c.rect(100, 70, 120, 110, 'M')
    for x in range(100, 220, 16):
        c.rect(x, 70, 1, 110, 'm')
    blob(c, 160, 154, 26, 16, 'A', 'K', shade='B', light='C')                         # palm
    blob(c, 160, 157, 13, 7, 'N', 'K', shade='p')                                    # pad
    for tx, ty in ((131, 130), (150, 119), (170, 119), (189, 130)):                   # toes
        blob(c, tx, ty, 8, 10, 'A', 'K', shade='B', light='C')
    for nx, ny, lean in ((130, 120, -3), (149, 109, -1), (171, 109, 1), (190, 120, 3)):   # long nails, curling inwards
        for i in range(15):
            x = nx + (lean * (i * i)) // 70
            c.rect(x - 2, ny - i, 5, 1, 'K')
        for i in range(15):
            x = nx + (lean * (i * i)) // 70
            c.rect(x - 1, ny - i, 3, 1, 'W' if i % 5 else 'E')
    for x, y in ((111, 100), (206, 100), (160, 88)):                                  # "click click"
        c.pattern(x, y, ['K.K', '.K.', 'K.K'])


def inner_ears(c):
    c.rect(100, 70, 120, 110, 'E')
    blob(c, 160, 124, 36, 48, 'B', 'K', light='A')                                    # fluffy ear flap
    for x, y in ((127, 100), (129, 138), (192, 104), (194, 140)):                     # fur tufts on the rim
        c.rect(x, y, 3, 2, 'A')
    c.ellipse(161, 128, 27, 38, 'N', shade='p')                                      # clean pink inside
    c.ellipse(161, 130, 21, 31, 'P')
    for dy, rx, ry in ((0, 15, 24), (2, 10, 17)):                                     # soft ridges
        for a in range(0, 360, 6):
            c.put(round(161 + rx * math.cos(math.radians(a))), round(132 + ry * math.sin(math.radians(a))), 'p')
    c.ellipse(161, 140, 9, 11, 'y'); c.ellipse(161, 142, 6, 7, 't')                  # wax build-up round the canal
    c.ellipse(161, 143, 3, 4, 'k')
    for x, y, w in ((148, 124, 5), (172, 120, 4), (150, 150, 4), (174, 148, 5)):      # little flakes of wax
        c.rect(x, y, w, 2, 'y'); c.rect(x, y + 1, w, 1, 't')
    for x, y in ((116, 88), (204, 100)):
        c.pattern(x, y, ['.w.', 'www', '.w.'])


CLOSEUPS = {'teeth': inner_teeth, 'coat': inner_coat, 'paws': inner_paws, 'ears': inner_ears}


def draw_closeup(name):
    return lens_scene(CLOSEUPS[name])


# ---- cutscene panels: arriving at the clinic, and the vaccine
FONT5x7['V'] = ['10001', '10001', '10001', '10001', '10001', '01010', '00100']


def big_text(c, x, y, word, col, scale=2):
    for i, ch in enumerate(word):
        for j, row in enumerate(FONT5x7[ch]):
            for k, bit in enumerate(row):
                if bit == '1':
                    c.rect(x + i * (5 * scale + scale) + k * scale, y + j * scale, scale, scale, col)


def draw_panel_clinic():
    """Cutscene: arriving at the vet. Visible area is y 15..146."""
    c = Canvas(320, 180)
    c.rect(0, 0, 320, 110, 'S')
    blob(c, 40, 32, 10, 10, 'Y', 'y')
    for cx0, cy0 in ((120, 26), (250, 40)):
        c.ellipse(cx0, cy0, 14, 4.5, 'W'); c.ellipse(cx0 + 8, cy0 - 3, 9, 4.5, 'W')
    for hx, hy, hr in ((20, 100, 60), (300, 98, 62)):
        c.ellipse(hx, hy, hr, 24, 'M', shade='m')
    c.rect(0, 112, 320, 70, 'm')
    for x in range(3, 320, 7):
        c.put(x, 118 + (x * 5) % 9, 'G')
    c.rect(0, 120, 320, 26, 'E'); c.rect(0, 120, 320, 1, 'K')                       # pavement
    for sx in range(8, 320, 24):
        c.rect(sx, 121, 1, 25, 'P')
    c.rect(130, 120, 60, 10, 'P')                                                    # path to the door
    # the clinic
    box(c, 76, 52, 168, 68, 'W'); c.rect(77, 112, 166, 7, 'E')
    box(c, 70, 42, 180, 12, 'M'); c.rect(71, 50, 178, 3, 'm')                        # roof
    box(c, 122, 14, 76, 28, 'Y'); c.rect(123, 38, 74, 3, 'y')                        # sign board
    big_text(c, 134, 22, 'VET', 'R')
    c.pattern(180, 24, ['.K.K.K', '......', '.KKKK.', 'KKKKKK', '.KKKK.'])
    for wx in (88, 200):
        box(c, wx, 64, 32, 30, 'S'); c.rect(wx + 16, 64, 1, 30, 'K'); c.rect(wx, 79, 32, 1, 'K'); c.rect(wx + 3, 67, 6, 1, 'w')
        box(c, wx - 2, 94, 36, 7, 'd')
        for fx in range(wx, wx + 32, 4):
            c.put(fx, 93, 'm'); c.put(fx + 1, 92, 'NYL'[(fx // 4) % 3])
    box(c, 140, 70, 40, 50, 'S'); c.rect(160, 70, 1, 50, 'K'); c.rect(142, 73, 6, 1, 'w')
    c.pattern(147, 90, ['.K.K.K', '......', '.KKKK.', 'KKKKKK', '.KKKK.'])           # paw sticker on the glass
    c.pattern(166, 90, ['R.R.', 'RRRR', '.RR.'])
    # the young dog waits on the pavement, leash running off to the left
    dog = young_anims()['idle'][0]
    paste(c, dog, 38, 124 - 38)
    for x in range(0, 54):
        c.put(x, 105 + round(3 * math.sin(x / 7)), 'R'); c.put(x, 106 + round(3 * math.sin(x / 7)), 'R')
    c.pattern(56, 88, ['.R.R.', 'RRRRR', '.RRR.', '..R..'])
    return c


def draw_panel_vaccine():
    """Cutscene: the vaccine. The dog sits on the table with a heart bandage."""
    c = draw_clinic()
    tt = CLINIC['table_top']
    paste(c, young_anims_l2()['sit'][0], CLINIC['dog_x'] - 20, tt - 3 - 38)
    paste(c, draw_vet_body(), CLINIC['vet_x'] - 18, 86)
    c.pattern(CLINIC['dog_x'] - 4, tt - 20, ['.R.R.', 'RRRRR', '.RRR.', '..R..'])    # heart bandage
    for x, y in ((120, 84), (178, 96), (136, 70)):
        paste(c, icon('star'), x, y)
    return c


# ---- the shopping list on paper: a yellow pad built from a top, a repeatable ruled row and a bottom (cut to fit in the game)
PAPER_W = 96                        # art px (192 on the canvas)
PAPER_ROW = 10                      # art px per written line (20 on the canvas)


def _paper_sides(c, y0, y1):
    for y in range(y0, y1):
        c.put(0, y, 'K'); c.put(PAPER_W - 1, y, 'K')


def paper_top():
    c = Canvas(PAPER_W, 18)
    c.rect(0, 0, PAPER_W, 6, 'R'); c.rect(0, 5, PAPER_W, 1, 'r')                # coral binding strip
    c.rect(0, 6, PAPER_W, 12, 'Y')
    for x in (12, 46, 80):                                                        # wire loops
        c.rect(x, 1, 3, 7, 'K'); c.rect(x + 1, 2, 1, 4, 'w')
    c.rect(0, 0, PAPER_W, 1, 'K')
    c.rect(0, 17, PAPER_W, 1, 'y')
    _paper_sides(c, 0, 18)
    return c


def paper_row():
    c = Canvas(PAPER_W, PAPER_ROW)
    c.rect(0, 0, PAPER_W, PAPER_ROW, 'Y')
    c.rect(0, PAPER_ROW - 1, PAPER_W, 1, 'y')                                    # the ruled line
    c.rect(12, 0, 1, PAPER_ROW, 'R')                                              # red margin
    _paper_sides(c, 0, PAPER_ROW)
    return c


def paper_bottom():
    c = Canvas(PAPER_W, 4)
    c.rect(0, 0, PAPER_W, 3, 'Y'); c.rect(0, 2, PAPER_W, 1, 'y')
    c.rect(0, 3, PAPER_W, 1, 'K')
    _paper_sides(c, 0, 3)
    return c


def list_box(ticked):
    c = Canvas(7, 7)
    box(c, 0, 0, 7, 7, 'W')
    if ticked:
        c.pattern(1, 1, ['....G', '...G.', 'G.G..', '.G...', '.....'])
    return c


# ---- group 6 export + preview mock-ups
LIST_ITEMS = (('toothbrush', 'Dog toothbrush'), ('toothpaste', 'Dog toothpaste'), ('flea', 'Flea treatment (dog)'),
              ('clippers', 'Nail clippers'), ('ear', 'Ear cleaner (dog)'))


def group6():
    out = {}
    out['assets/bg/vet_clinic.png'] = ([draw_clinic()], None, {'section': 'bg', 'anim': 'vet clinic'})
    out['assets/sprites/vet_stand.png'] = ([draw_vet_body(), draw_vet_body(), draw_vet_body(True), draw_vet_body()], None,
                                           {'section': 'The vet', 'anim': 'idle', 'note': 'Stands beside the exam table (36x82)'})
    for name, frames in vet_frames().items():
        out[f'assets/sprites/vet_{name}.png'] = (frames, None, {'section': 'The vet', 'anim': name, 'note': 'Portrait, like the parent'})
    for coat, cols in COATS.items():
        for name, frames in young_anims_l2().items():
            out[f'assets/sprites/young_{coat}_{name}.png'] = (frames, cols, {'coat': coat, 'anim': name, 'section': 'Young dog (Level 2)'})
        for name, frames in adult_anims().items():
            out[f'assets/sprites/adult_{coat}_{name}.png'] = (frames, cols, {'coat': coat, 'anim': name, 'section': 'Adult dog (growth cutscene)'})
        for name, fn in (('clinic', draw_panel_clinic), ('vaccine', draw_panel_vaccine)):
            out[f'assets/screens/panel_{name}_{coat}.png'] = ([fn()], cols, {'section': 'bg', 'anim': name})
    out['assets/ui/icon_vet.png'] = ([icon('vet')], None, {'section': 'Icons', 'anim': 'vet', 'note': 'Health check skill'})
    # (the old check-up close-ups, spot ring, shopping-list paper and list icons were retired with the shop)
    return out


def l2_hud(fill_cols, name, task_icon, task_label):
    frame, fills, heart = meter_parts()
    fill = Canvas(62, 6); fill.px = [row[:fill_cols] + [None] * (62 - fill_cols) for row in fills['green'].px]
    ci, bc = panel(18, 18, 'W', ring='E'), button('W', 'E', 'Y')[0]
    return [('@canvas', heart, 8, 8, 2), ('@canvas', frame, 36, 10, 2), ('@canvas', fill, 38, 12, 2),
            ('@text', 172, 9, 120, name, 16, '#5A3E36', 'left'),
            ('@canvas', nine(ci, 96, 16, 6), 402, 6, 2), ('@canvas', icon(task_icon), 410, 6, 2),
            ('@text', 446, 13, 140, task_label, 14, '#5A3E36', 'left'),
            ('@canvas', nine(bc, 16, 16, 5), 604, 8, 2), ('@canvas', icon('pause'), 604, 8, 2)]


def vet_say(line, h=30):
    sp, ci = speech_bubble(), panel(18, 18, 'W', ring='E')
    return [('@canvas', nine(ci, 52, 50, 6), 2, 40, 2), ('assets/sprites/vet_talk.png', 6, 42, 2),
            ('@canvas', nine(sp, 210, h, 5), 116, 58, 2), ('@canvas', speech_tail(), 100, 78, 2),
            ('@text', 134, 70, 390, line, 16, '#5A3E36', 'left')]


def list_paper(x, y, found, ticked=0):
    """The shopping list as a sheet of paper at canvas (x, y). It grows one ruled line per item written, plus one blank line."""
    rows = min(found + 1, len(LIST_ITEMS))
    items = [('assets/ui/paper_top.png', x, y, 2), ('@text', x + 28, y + 14, 150, 'Shopping list', 14, '#5A3E36', 'left')]
    for i in range(rows):
        ry = y + 36 + i * PAPER_ROW * 2
        items.append(('assets/ui/paper_row.png', x, ry, 2))
        if i < found:
            items += [('assets/ui/list_tick.png' if i < ticked else 'assets/ui/list_box.png', x + 26, ry + 3, 2),
                      ('@text', x + 46, ry + 3, 150, LIST_ITEMS[i][1], 13, '#5A3E36', 'left')]
    items.append(('assets/ui/paper_bottom.png', x, y + 36 + rows * PAPER_ROW * 2, 2))
    return items


def l2_mockups():
    ci, bm = panel(18, 18, 'W', ring='E'), button('M', 'm', 'Y')[0]
    sp = speech_bubble()
    t = lambda x, y, w, s, size, col='#5A3E36', al='center': ('@text', x, y, w, s, size, col, al)
    W2 = (640, 360)
    pill = lambda x, y, w, label: [('@canvas', nine(ci, w // 2, 14, 6), x * 2, y * 2, 2), t(x * 2, y * 2 + 5, w, label, 13)]
    ring = lambda cx, cy: ('assets/ui/spot_ring.png', (cx - 5) * 2, (cy - 5) * 2, 2)
    table_top = CLINIC['table_top']
    PX, PY = 4, 206                                                            # the paper, bottom-left
    clinic = ([('assets/bg/vet_clinic.png', 0, 0, 2)] + l2_hud(44, 'Biscuit', 'vet', 'Check-up  1 of 2') + [
        ('assets/sprites/vet_stand.png', (CLINIC['vet_x'] - 18) * 2, 86 * 2, 2),
        ('assets/sprites/young_caramel_nervous.png', (CLINIC['dog_x'] - 20) * 2, (table_top - 3 - 39) * 2, 2),
        ring(165, 102), ring(148, 95), ring(138, 110), ring(150, 118)]
        + pill(172, 96, 52, 'Teeth') + pill(117, 88, 52, 'Ears') + pill(105, 109, 52, 'Coat') + pill(157, 112, 52, 'Paws')
        + [('@canvas', pointer_cue()[0], 165 * 2 - 13, 157, 2)]
        + vet_say("Hi! Let's check Biscuit from nose to tail. Tap each spot to look closer.") + list_paper(PX, PY, 0))
    scene = lambda name, line, found: ([(f'assets/screens/closeup_{name}_caramel.png', 0, 0, 2)] + l2_hud(44, 'Biscuit', 'vet', 'Check-up  1 of 2')
                                       + vet_say(line) + list_paper(PX, PY, found))
    teeth = scene('teeth', 'Yellow tartar on the teeth! Brushing a few times a week keeps teeth and gums healthy.', 2) \
        + [('@canvas', nine(bm, 56, 16, 5), 504, 296, 2), t(504, 304, 112, 'Next', 18)]
    coat = scene('coat', 'A flea! Fleas cause itching and can spread illness, so monthly prevention helps.', 3)
    paws = scene('paws', 'Long nails click on the floor. They hurt when walking, so trim them regularly.', 4)
    ears = scene('ears', 'A little wax in the ears. A gentle ear cleaner helps, and checking every week keeps them healthy.', 5)
    done = ([('assets/bg/vet_clinic.png', 0, 0, 2), ('@rect', 0, 0, 640, 360, 'rgba(62,42,36,.4)')] + list_paper(216, 24, 5)
            + [('@canvas', nine(bm, 80, 16, 5), 240, 192, 2), t(240, 200, 160, 'To the store!', 16)])

    def bar(name, face, line):
        return [(f'assets/screens/panel_{name}_caramel.png', 0, 0, 2), ('@rect', 0, 0, 640, 30, '#D7C4EC'), ('@rect', 0, 292, 640, 68, '#D7C4EC'),
                ('@canvas', nine(ci, 30, 30, 6), 8, 296, 2), ('@canvas', face, 12, 300, 2),
                ('@canvas', nine(sp, 270, 26, 5), 82, 302, 2), t(98, 312, 520, line, 16, '#5A3E36', 'left'), t(560, 8, 72, 'Skip', 13, '#5A3E36', 'right')]
    pface = crop(parent_frames()['talk'][1], 11, 5, 26, 26)
    vface = crop(vet_frames()['talk'][1], 11, 5, 26, 26)
    growth = [('assets/bg/living_room.png', 0, -60, 2), ('@rect', 0, 0, 640, 30, '#D7C4EC'), ('@rect', 0, 292, 640, 68, '#D7C4EC'),
              ('assets/sprites/young_caramel_sit.png', 210, 190, 2), ('assets/sprites/adult_caramel_wag.png', 330, 168, 2),
              ('@canvas', icon('star'), 300, 190, 2), ('@canvas', icon('star'), 440, 150, 2), ('@canvas', icon('star'), 196, 186, 2),
              ('@canvas', nine(sp, 300, 26, 5), 20, 302, 2), t(36, 316, 560, "Look how big Biscuit is now! You're doing a great job.", 16, '#5A3E36', 'left')]
    return [('The clinic: start of the check-up (arrow on the first spot only)', W2, clinic),
            ('Close-up: teeth (the list gets two items)', W2, teeth), ('Close-up: coat', W2, coat), ('Close-up: paws', W2, paws),
            ('Close-up: ears (a little wax, so ear cleaner joins the list)', W2, ears), ('The finished shopping list', W2, done),
            ('Cutscene: arriving at the clinic', W2, bar('clinic', pface, "Time for Biscuit's first check-up! Afterwards we'll buy whatever the vet says Biscuit needs.")),
            ('Cutscene: the vaccine (the vet speaks)', W2, bar('vaccine', vface, 'All done! Vaccines protect against serious diseases, and only a vet can give them.')),
            ('Growth cutscene: young dog to adult', W2, growth)]


# Group 7 (the pet store) was retired with the shop: Level 2 became spot the difference + bath time (groups 10, 11).


# ---------------------------------------------------------------- group 9: story panels (the kid and parent in full)
def kid(pose='stand', step=0):
    """The player's kid, 40x64, facing right. Poses: stand, worried, hug (arms drawn by the panel, over the puppy), pj (arms up,
    pyjamas, no cap), sit (on the floor, legs forward, laughing), leash (front arm forward holding a leash; step 0-3 walks)."""
    c = Canvas(40, 64)
    o = 4                                                                    # spare rows on top for raised arms
    pj, sit = pose == 'pj', pose == 'sit'
    shirt, shade = ('L', 'l') if pj else ('Y', 'y')
    if pj:
        c.ellipse(15, 9 + o, 9, 8, 'H')                                      # bed hair
    else:
        c.rect(6, 9 + o, 4, 8, 'H')                                          # hair under the cap
    c.ellipse(15, 13 + o, 8, 8, 'F')                                         # face
    if pj:
        c.rect(8, 4 + o, 14, 4, 'H'); c.rect(7, 8 + o, 3, 8, 'H'); c.pattern(16, 2 + o, ['.H.H', 'HH.H'])   # messy fringe
    else:
        c.ellipse(14, 7 + o, 9, 5, 'M'); c.rect(5, 7 + o, 18, 3, 'M'); c.rect(18, 9 + o, 9, 2, 'M'); c.rect(6, 10 + o, 17, 1, 'm')
        c.put(14, 2 + o, 'R')                                                # button on top of the cap
    c.rect(10, 13 + o, 2, 3, 'f')                                            # ear
    c.put(23, 15 + o, 'f')                                                   # nose
    happy = pose in ('hug', 'sit')
    if happy:
        c.pattern(18, 13 + o, ['.kk.', 'k..k'])                              # ^ eyes
        c.pattern(18, 18 + o, ['kkk', 'kNk', '.k.'])                         # open smile
    elif pose == 'worried':
        c.rect(19, 12 + o, 2, 3, 'k'); c.put(20, 12 + o, 'w'); c.pattern(18, 10 + o, ['..hh', 'hh..'])   # worried brow
        c.pattern(19, 19 + o, ['.k.', 'k.k'])
    elif pj:
        c.rect(18, 13 + o, 3, 1, 'k'); c.pattern(18, 18 + o, ['kkk', 'kNk', 'kkk'])   # sleepy eyes, a big yawn
    else:
        c.rect(19, 12 + o, 2, 3, 'k'); c.put(20, 12 + o, 'w'); c.pattern(19, 18 + o, ['k.k', '.k.'])
    c.rect(19, 17 + o, 2, 1, 'N')                                            # blush
    c.rect(13, 21 + o, 4, 3, 'f')                                            # neck
    c.ellipse(15, 27 + o, 9, 4, shirt); c.rect(6, 27 + o, 18, 14, shirt); c.rect(6, 38 + o, 18, 3, shade)
    if pj:
        for x in range(8, 24, 4):
            c.rect(x, 28 + o, 1, 12, shade)
    else:
        c.rect(6, 32 + o, 18, 2, 'R')                                        # stripe on the T-shirt
    if pj:                                                                   # stretching, arms up
        c.rect(3, 0, 4, 28 + o, shirt); c.rect(3, 0, 4, 3, 'F'); c.rect(23, 0, 4, 28 + o, shirt); c.rect(23, 0, 4, 3, 'F')
    elif pose == 'worried':                                                  # a hand by the mouth
        c.rect(3, 27 + o, 4, 4, shirt); c.rect(3, 31 + o, 4, 11, 'F')
        c.rect(23, 27 + o, 4, 4, shirt); c.rect(22, 21 + o, 4, 7, 'F')
    elif pose == 'leash':                                                    # front arm held out, the hand closed round the leash
        c.rect(3, 27 + o, 4, 4, shirt); c.rect(3 - (step == 1) + (step == 3), 31 + o, 4, 10, 'F')
        c.rect(23, 27 + o, 6, 4, shirt); c.rect(29, 28 + o, 5, 3, 'F'); c.rect(33, 27 + o, 3, 5, 'F')
    elif pose != 'hug':
        c.rect(3, 27 + o, 4, 4, shirt); c.rect(3, 31 + o, 4, 11, 'F')
        c.rect(23, 27 + o, 4, 4, shirt); c.rect(23, 31 + o, 4, 11, 'F')
    if pose == 'leash' and step in (1, 3):                                  # mid-stride: one leg forward, one back
        f, b = (3, -3) if step == 1 else (-3, 3)
        c.rect(8, 41 + o, 14, 3, 'S'); c.rect(8 + b, 44 + o, 6, 10, 'S'); c.rect(16 + f, 44 + o, 6, 10, 'S')
        c.rect(7 + b, 54 + o, 8, 3, 'R'); c.rect(16 + f, 54 + o, 9, 3, 'R'); c.rect(7 + b, 56 + o, 8, 1, 'W'); c.rect(16 + f, 56 + o, 9, 1, 'W')
    elif sit:                                                                  # legs out in front
        c.rect(8, 41 + o, 26, 6, 'S'); c.rect(8, 46 + o, 26, 1, 's'); c.rect(34, 38 + o, 3, 10, 'R'); c.rect(36, 38 + o, 1, 10, 'W')
    else:
        c.rect(8, 41 + o, 14, 3, 'S'); c.rect(8, 44 + o, 6, 10, 'S'); c.rect(16, 44 + o, 6, 10, 'S'); c.rect(12, 44 + o, 2, 10, 's')
        c.rect(7, 54 + o, 8, 3, 'R'); c.rect(16, 54 + o, 9, 3, 'R'); c.rect(7, 56 + o, 8, 1, 'W'); c.rect(16, 56 + o, 9, 1, 'W')
    return c.outline()


def kid_arms():
    """The cradling arm (sleeve, forearm and hand) that the held puppy sits on."""
    c = Canvas(30, 8)
    c.rect(1, 1, 6, 5, 'Y'); c.rect(7, 2, 18, 4, 'F'); c.rect(24, 1, 4, 5, 'F')
    return c.outline()


def kid_hand():
    c = Canvas(7, 7)
    c.rect(1, 1, 5, 4, 'F'); c.rect(1, 5, 2, 1, 'F')
    return c.outline()


PARENT_H = 66                                                                 # the parent's height (art px); the kid is 61


def parent_body(pose='stand'):
    """The parent full length, 28x66, facing right: a head taller than the kid. Matches the bust: brown hair, peach sweater.
    pose 'wave' raises the right arm."""
    c = Canvas(28, PARENT_H)
    c.rect(4, 6, 4, 13, 'H')                                                 # hair at the back
    c.ellipse(14, 11, 7, 8, 'F')
    c.ellipse(13, 6, 9, 5, 'H'); c.rect(10, 4, 10, 3, 'H'); c.rect(19, 6, 2, 3, 'H')
    c.rect(8, 11, 2, 3, 'f'); c.put(21, 12, 'f')
    c.rect(16, 9, 2, 3, 'k'); c.put(17, 9, 'w'); c.rect(16, 14, 2, 1, 'N'); c.pattern(15, 16, ['k..k', '.kk.'])
    c.rect(11, 18, 5, 3, 'f')
    c.ellipse(14, 24, 9, 4, 'P'); c.rect(5, 24, 18, 19, 'P'); c.rect(5, 40, 18, 3, 'p')
    c.pattern(10, 21, ['WWWWWWW', '.WWWWW.'])
    c.rect(2, 24, 4, 17, 'P'); c.rect(2, 41, 4, 3, 'F')
    if pose == 'wave':
        c.rect(22, 9, 4, 16, 'P'); c.rect(22, 6, 4, 3, 'F')
    else:
        c.rect(22, 24, 4, 17, 'P'); c.rect(22, 41, 4, 3, 'F')
    c.rect(7, 43, 6, 18, 'd'); c.rect(15, 43, 6, 18, 'd')
    c.rect(6, 61, 8, 3, 'h'); c.rect(15, 61, 8, 3, 'h')
    return c.outline()


def shift_up(c, dy):
    """Raise a scene by dy rows so its floor sits inside the visible band (the cutscene bars hide y<15 and y>146)."""
    out = Canvas(c.w, c.h)
    out.px = c.px[dy:] + [list(c.px[-1]) for _ in range(dy)]
    return out


def recolor(cv, mapping):
    out = Canvas(cv.w, cv.h)
    out.px = [[mapping.get(k, k) for k in row] for row in cv.px]
    return out


OTHER_PUPS = ({'A': 'W', 'B': 'E', 'C': 'w'}, {'A': 'H', 'B': 'h', 'C': 'D'})   # the rescue centre's other puppies: white, dark brown


def prod_toothpaste_human():
    c = Canvas(18, 8)
    c.rect(1, 2, 13, 4, 'W'); c.rect(3, 2, 2, 4, 'S'); c.rect(7, 2, 2, 4, 'M'); c.rect(11, 2, 2, 4, 'S'); c.rect(14, 3, 3, 2, 'R')
    return c.outline()


def prod_shampoo_human():
    c = Canvas(10, 17)
    c.rect(1, 4, 8, 12, 'N'); c.rect(3, 1, 4, 3, 'W'); c.rect(2, 7, 6, 5, 'W'); c.pattern(3, 8, ['.Y.', 'YRY', '.Y.']); c.rect(7, 4, 1, 12, 'p')
    return c.outline()


def prod_flea_cat():
    c = Canvas(13, 12)
    c.rect(1, 1, 11, 10, 'L'); c.rect(2, 3, 9, 6, 'W'); c.pattern(4, 3, ['k...k', 'kk.kk', 'kkkkk', '.kkk.'])
    return c.outline()


def prod_ball_tiny():
    c = Canvas(7, 7)
    c.ellipse(3.5, 3.5, 2.6, 2.6, 'Y', shade='y'); c.put(2, 2, 'w')
    return c.outline()


def floor_planks(c, y0, base='D', line='d'):
    c.rect(0, y0, c.w, c.h - y0, base); c.rect(0, y0, c.w, 1, 'K'); c.rect(0, y0 + 1, c.w, 2, line)
    for i, y in enumerate(range(y0 + 8, c.h, 8)):
        c.rect(0, y, c.w, 1, line)
        for x in range((i * 19) % 44, c.w, 44):
            c.rect(x, y - 7, 1, 7, line)


def bedroom(night=False):
    c = Canvas(320, 180)
    wall, stripe = ('l', 'V') if night else ('S', 's')            # sky blue by day, so the lavender pyjamas stand out
    c.rect(0, 0, 320, 128, wall)
    for x in range(6, 320, 14):
        c.rect(x, 0, 1, 124, stripe)
    c.rect(0, 123, 320, 5, 'W' if not night else 'E'); c.rect(0, 123, 320, 1, 'K')
    floor_planks(c, 128, 'D' if not night else 'd', 'd' if not night else 'h')
    box(c, 96, 28, 64, 52, 'W'); box(c, 100, 32, 56, 44, 'v' if night else 'S')   # window
    if night:
        c.ellipse(140, 46, 7, 7, 'Y'); c.ellipse(144, 43, 6, 6, 'v')
        for sx, sy in ((108, 40), (122, 58), (150, 66), (114, 68)):
            c.put(sx, sy, 'W')
    else:
        c.rect(100, 58, 56, 18, 'Y'); c.rect(100, 52, 56, 6, 'P')               # sunrise
        blob(c, 128, 70, 9, 9, 'O', 'o'); c.ellipse(128, 80, 40, 7, 'm')
        c.rect(100, 76, 56, 0, 'm')
    c.rect(127, 32, 2, 44, 'K'); c.rect(100, 53, 56, 1, 'K')
    for cx0 in (88, 160):                                                     # curtains
        box(c, cx0, 26, 10, 60, 'R'); c.rect(cx0 + 4, 28, 1, 56, 'r')
    c.rect(84, 24, 90, 3, 'd'); c.rect(84, 24, 90, 1, 'K')
    box(c, 182, 32, 42, 46, 'W'); c.rect(183, 33, 40, 9, 'R')                  # calendar: PUPPY DAY
    pixel_text(c, 186, 35, 'PUPPY DAY', 'W')
    for j in range(4):
        for i in range(5):
            c.rect(188 + i * 7, 46 + j * 7, 3, 3, 'E')
    for a in range(0, 360, 12):                                              # the circled day
        c.put(round(209 + 5 * math.cos(math.radians(a))), round(61 + 4 * math.sin(math.radians(a))), 'R')
    # the bed (left), pillow, blanket
    box(c, 6, 66, 10, 64, 'd'); box(c, 6, 100, 90, 30, 'D'); c.rect(7, 124, 88, 4, 'd')
    box(c, 16, 90, 26, 12, 'W')
    box(c, 92, 108, 30, 22, 'D'); c.rect(93, 114, 28, 1, 'd'); c.rect(105, 118, 4, 2, 'Y')   # nightstand
    if night:
        box(c, 100, 98, 12, 10, 'E'); c.rect(104, 92, 4, 6, 'd')                 # lamp, off
    else:
        blob(c, 107, 102, 6, 5, 'Y', 'K'); c.rect(103, 99, 1, 2, 'K'); c.rect(110, 99, 1, 2, 'K')   # alarm clock
        c.rect(107, 100, 1, 3, 'K'); c.rect(107, 102, 3, 1, 'K')
    # door (right)
    box(c, 248, 36, 50, 92, 'W')
    if night:
        box(c, 252, 40, 42, 88, 'D'); c.rect(286, 84, 3, 3, 'Y')
    else:
        box(c, 252, 40, 42, 88, 'E'); c.rect(253, 110, 40, 17, 'P'); c.rect(286, 40, 8, 88, 'D'); c.rect(286, 40, 1, 88, 'K')
    return c


def draw_panel_bedroom():
    """Saturday morning: the kid sits up in bed and stretches; PUPPY DAY is circled; the parent leans in at the door."""
    c = bedroom()
    paste(c, kid('pj'), 26, 52)
    box(c, 14, 99, 82, 25, 'M')                                               # blanket over the legs
    for x in range(20, 92, 8):
        c.pattern(x, 106, ['.Y.', 'YYY', '.Y.'])
    c.rect(15, 120, 80, 3, 'm')
    paste(c, parent_body('wave').flipped(), 259, 128 - PARENT_H)
    blob(c, 186, 136, 5, 5, 'R', 'K', light='N'); c.rect(181, 135, 11, 2, 'W')          # a ball on the floor
    c.pattern(56, 46, ['..Y..', '.YwY.', '..Y..']); c.pattern(84, 58, ['.Y.', 'YwY', '.Y.'])   # excitement
    return c


def draw_panel_car_there():
    return draw_panel_car(puppy=False)


def rescue_room(c):
    c.rect(0, 0, 320, 120, 'M')
    for y in range(8, 70, 14):
        for x in range(8 + (7 if (y // 14) % 2 else 0), 320, 14):
            c.pattern(x - 1, y - 1, ['.m.', 'mmm', '.m.'])
    c.rect(0, 70, 320, 50, 'm'); c.rect(0, 70, 320, 1, 'K'); c.rect(0, 71, 320, 2, 'M')
    c.rect(0, 120, 320, 60, 'E'); c.rect(0, 120, 320, 1, 'K')
    for i, y in enumerate(range(120, 180, 10)):
        c.rect(0, y, 320, 1, 'P')
        for x in range(12 if i % 2 else 0, 320, 24):
            c.rect(x, y, 1, 10, 'P')
    for hx, hy in ((30, 30), (290, 34), (60, 52), (260, 56)):                 # painted hearts
        c.pattern(hx, hy, ['.R.R.', 'RRRRR', '.RRR.', '..R..'])


def pen(c, x, w):
    box(c, x, 64, w, 58, 'W'); c.rect(x + 1, 110, w - 2, 11, 'T')              # kennel back + straw
    for px in range(x + 2, x + w - 2, 4):
        c.put(px, 112 + px % 3, 't')
    c.rect(x, 82, w, 2, 'K'); c.rect(x, 84, w, 1, 'E')                          # top rail
    for bx in range(x + 3, x + w - 1, 7):                                     # bars
        c.rect(bx, 84, 1, 38, 'K')


def draw_panel_rescue():
    """The rescue centre: two pups nap in their pens; yours is at the front, wagging."""
    c = Canvas(320, 180)
    rescue_room(c)
    pen(c, 22, 82); pen(c, 216, 82)
    sleepy = puppy_anims()['sad'][1]
    paste(c, recolor(sleepy, OTHER_PUPS[0]), 46, 120 - 30)
    paste(c, recolor(sleepy, OTHER_PUPS[1]), 244, 120 - 30)
    for zx in (70, 268):
        pixel_text(c, zx, 78, 'Z', 'l'); pixel_text(c, zx + 5, 72, 'Z', 'l')
    box(c, 112, 64, 96, 58, 'W'); c.rect(113, 110, 94, 11, 'T')               # middle pen, gate open
    box(c, 126, 46, 68, 14, 'Y'); pixel_text(c, 140, 50, 'ADOPT ME', 'K')
    for bx in range(198, 207, 7):
        c.rect(bx, 84, 1, 38, 'K')
    c.rect(198, 82, 10, 2, 'K')
    paste(c, puppy_anims()['wag'][2], 144, 138 - 30)
    c.pattern(156, 92, ['.R.R.', 'RRRRR', '.RRR.', '..R..'])
    for x, y in ((140, 104), (186, 102)):
        c.pattern(x, y, ['.w.', 'www', '.w.'])
    paste(c, kid('stand'), 68, 140 - 61)
    return c


def draw_panel_chosen():
    """The puppy has picked you: a big hug, and the parent smiles."""
    c = Canvas(320, 180)
    rescue_room(c)
    pen(c, 22, 82)
    paste(c, recolor(puppy_anims()['sad'][1], OTHER_PUPS[0]), 46, 120 - 30)
    paste(c, parent_body().flipped(), 200, 140 - PARENT_H)
    paste(c, kid('hug'), 126, 140 - 61)
    pup = draw_dog(PUPPY, pose='sit', tail=60, eyes='happy', mouth='open')      # sitting up, cradled on the kid's forearm
    paste(c, pup, 136, 120 - 30)
    paste(c, kid_arms(), 128, 117)
    paste(c, kid_hand(), 141, 103)                                             # the other hand on the puppy's back
    for hx, hy in ((150, 64), (176, 52), (132, 54)):
        c.pattern(hx, hy, ['.R.R.', 'RRRRR', '.RRR.', '..R..'])
    return c


def living_afternoon():
    c = draw_room()
    for y in range(140, 180):                                                 # warm patches of sun on the floor
        for x in range(320):
            u = x - (y - 140) * 0.8
            if (60 <= u < 84 or 96 <= u < 116) and c.px[y][x] in ('D', 'd'):
                c.px[y][x] = 'T' if c.px[y][x] == 'D' else 'D'
    for y in range(34, 140):                                                  # and through the window onto the wall
        for x in range(320):
            u = x - (y - 34) * 0.8
            if 140 <= u < 150 and c.px[y][x] in ('W', 'E'):
                c.px[y][x] = 'Y' if c.px[y][x] == 'W' else 'y'
    return c


def draw_panel_afternoon():
    """Later that afternoon: the puppy chases a ball across the rug, the kid laughs."""
    c = living_afternoon()
    paste(c, puppy_anims()['walk'][0], 140, 166 - 30)
    blob(c, 186, 146, 5, 5, 'R', 'K', light='N'); c.rect(181, 145, 11, 2, 'W')
    for i, (x, y) in enumerate(((176, 140), (170, 136), (165, 134))):           # the ball's bounce trail
        c.put(x, y, 'W')
    for my in (150, 156):
        c.rect(124, my, 10, 1, 'W')
    paste(c, kid('sit').flipped(), 226, 166 - 59)
    return shift_up(c, 26)


def draw_panel_afternoon_sniff():
    """The ball has rolled away, and the puppy has its nose down, sniffing the rug."""
    c = living_afternoon()
    blob(c, 234, 136, 5, 5, 'R', 'K', light='N'); c.rect(229, 135, 11, 2, 'W')
    paste(c, puppy_anims()['sniff'][0], 150, 166 - 30)
    paste(c, kid('sit').flipped(), 226, 166 - 59)
    paste(c, icon('question'), 240, 94)
    for x, y in ((146, 160), (186, 162)):                                    # sniff, sniff
        c.pattern(x, y, ['W.W', '.W.'])
    return shift_up(c, 26)


def draw_panel_night():
    """That night: the kid asleep, the puppy curled up in its basket by the bed, the moon in the window."""
    c = bedroom(night=True)
    box(c, 16, 90, 26, 12, 'W')
    c.ellipse(32, 92, 8, 7, 'F'); c.ellipse(29, 87, 8, 5, 'H'); c.rect(23, 87, 3, 8, 'H')   # sleeping head on the pillow
    c.rect(34, 92, 3, 1, 'k'); c.put(36, 95, 'N'); ring(c, 31, 91, 9, 8, ('F', 'H'))
    box(c, 14, 98, 82, 26, 'M'); c.rect(15, 120, 80, 3, 'm')
    for x in range(20, 92, 8):
        c.pattern(x, 106, ['.Y.', 'YYY', '.Y.'])
    pixel_text(c, 48, 76, 'Z', 'W'); pixel_text(c, 54, 70, 'Z', 'W'); pixel_text(c, 61, 63, 'Z', 'W')
    for y in range(128, 146):                                                 # moonlight on the floor
        for x in range(320):
            u = x - (y - 128) * 1.2
            if 150 <= u < 190:
                c.put(x, y, 'l')
    c.ellipse(152, 140, 26, 6, 'd'); c.ellipse(152, 138, 22, 4, 'D'); c.ellipse(152, 138, 18, 3, 'R')   # basket + cushion
    paste(c, puppy_anims()['sad'][1], 136, 140 - 30)
    pixel_text(c, 168, 112, 'Z', 'W'); pixel_text(c, 173, 106, 'Z', 'W')
    return c


def scratching_dog():
    """The young dog sitting, scratching behind its ear with a back paw."""
    dog = draw_dog(YOUNG, pose='sit', eyes='squint', head=(0, 1), tail=20)
    c = Canvas(40, 40)
    paste(c, dog, 0, 0)
    thick_line(c, 13, 33, 21, 17, 'K', 4)
    thick_line(c, 13, 33, 21, 17, 'B', 2)
    c.rect(19, 14, 4, 4, 'K'); c.rect(20, 15, 2, 2, 'C')
    return c


def draw_panel_scratching():
    """One morning: the young dog keeps scratching; the kid looks worried."""
    c = draw_room()
    paste(c, scratching_dog(), 136, 165 - 38)
    for x, y in ((164, 124), (170, 132), (160, 118)):                        # scratch-scratch lines
        c.rect(x, y, 4, 1, 'K')
    for x, y in ((150, 112), (176, 116)):                                     # tiny hopping specks
        c.put(x, y, 'k'); c.put(x + 1, y - 2, 'K')
    paste(c, kid('worried').flipped(), 206, 166 - 61)
    return shift_up(c, 26)


def bathroom(c):
    c.rect(0, 0, 320, 128, 'S')
    for y in range(0, 128, 8):
        c.rect(0, y, 320, 1, 's')
        for x in range(8 if (y // 8) % 2 else 0, 320, 16):
            c.rect(x, y, 1, 8, 's')
    c.rect(0, 128, 320, 52, 'W'); c.rect(0, 128, 320, 1, 'K')
    for y in range(128, 180, 9):
        for x in range(0 if (y // 9) % 2 else 9, 320, 18):
            c.rect(x, y, 9, 9, 'E')


def draw_panel_grooming_bag():
    """The parent packs the grooming bag from the bathroom: our own toothpaste and shampoo, cat flea drops, a tiny ball."""
    c = Canvas(320, 180)
    bathroom(c)
    box(c, 244, 18, 44, 34, 'W'); box(c, 248, 22, 36, 26, 'S'); c.rect(250, 24, 8, 1, 'w')   # mirror
    box(c, 214, 72, 82, 8, 'E'); box(c, 220, 80, 70, 48, 'W')                # counter + cabinet
    box(c, 222, 82, 32, 44, 'E'); c.rect(250, 102, 2, 4, 'Y')
    box(c, 256, 82, 32, 44, 'W'); c.rect(258, 102, 2, 4, 'Y')
    box(c, 0, 92, 40, 36, 'W'); c.rect(1, 96, 38, 4, 'E')                    # bathtub edge, left
    for bx, by in ((8, 88), (18, 84), (30, 88)):
        c.ellipse(bx, by, 4, 3, 'W'); c.put(bx - 1, by - 1, 'w')
    # the bag on the counter, the products going in
    c.pattern(222, 40, ['..KKKKKKKKKKKKKKKKKKKKKKKKKKKKK....', '.K.............................K...', 'K...............................K..'])
    paste(c, prod_shampoo_human(), 226, 38)                                    # going into the bag, sitting on the counter
    paste(c, prod_toothpaste_human(), 238, 46)
    box(c, 218, 52, 40, 21, 'R'); c.rect(219, 65, 38, 7, 'r')
    paste(c, prod_flea_cat(), 264, 60)
    paste(c, prod_ball_tiny(), 282, 65)
    paste(c, parent_body(), 186, 128 - PARENT_H)
    paste(c, young_anims_l2()['sit'][0], 60, 128 - 38)
    paste(c, icon('question'), 74, 70)
    return c


def draw_panel_vet_chart():
    """Inside the clinic: the vet holds up the HEALTHY DOG chart; the grooming bag waits by the table."""
    c = draw_clinic()
    tt = CLINIC['table_top']
    paste(c, young_anims_l2()['nervous'][0], CLINIC['dog_x'] - 20, tt - 3 - 39)
    box(c, 186, 40, 50, 62, 'W'); c.rect(187, 41, 48, 10, 'M')                 # the chart on an easel
    pixel_text(c, 191, 44, 'HEALTHY', 'K')
    paste(c, young_anims()['idle'][0], 191, 56)
    for x, y in ((190, 92), (226, 92)):
        c.pattern(x, y, ['...M', 'M.MM', '.MM.'])
    c.rect(196, 102, 3, 64, 'd'); c.rect(224, 102, 3, 64, 'd')
    paste(c, draw_vet_body(), CLINIC['vet_x'] - 18, 86)
    box(c, 54, 136, 30, 20, 'R'); c.rect(55, 150, 28, 5, 'r')                 # the grooming bag on the floor
    c.pattern(56, 128, ['..KKKKKKKKKKKKKKKKKKKKKK..', '.K......................K.', 'K........................K'])
    paste(c, prod_shampoo_human(), 60, 122); paste(c, prod_toothpaste_human(), 66, 131)
    return shift_up(c, 20)


STORY_PANELS = {'bedroom': draw_panel_bedroom, 'car_there': draw_panel_car_there, 'rescue': draw_panel_rescue, 'chosen': draw_panel_chosen,
                'afternoon': draw_panel_afternoon, 'afternoon_sniff': draw_panel_afternoon_sniff, 'night': draw_panel_night,
                'scratching': draw_panel_scratching, 'grooming_bag': draw_panel_grooming_bag, 'vet_chart': draw_panel_vet_chart}
STORY_LINES = {   # (who, line) as in the approved story flow; the preview shows each panel in its cutscene frame
    'bedroom': ('parent', "Wake up, sleepyhead! It's Puppy Day. We leave in five minutes!"),
    'car_there': ('parent', "We're off to the rescue centre. Lots of puppies there need a family."),
    'rescue': (None, "So many puppies! But one of them can't stop wagging at you."),
    'chosen': ('parent', 'Looks like this little one picked you. What will you call them?'),
    'afternoon': ('parent', 'Biscuit has had lunch and lots of play. Puppies often need to go potty after that...'),
    'afternoon_sniff': (None, 'Wait... why is Biscuit sniffing the rug like that?'),
    'night': ('parent', 'What a first day! Biscuit learned so much, and so did you.'),
    'scratching': ('parent', "Biscuit keeps scratching. Let's take them to the vet for a check-up."),
    'grooming_bag': ('parent', "Bring Biscuit's grooming bag too. The vet can check what we use at home."),
    'vet_chart': ('vet', "Hello, Biscuit! Let's compare you with a healthy dog, and check that grooming bag too."),
}


def group9():
    out = {}
    for name, fn in STORY_PANELS.items():
        art = fn()
        for coat, cols in COATS.items():
            out[f'assets/screens/panel_{name}_{coat}.png'] = ([art], cols, {'section': 'bg', 'anim': name})
    out['assets/sprites/kid_stand.png'] = ([kid('stand')], None, {'section': 'Characters (drawn into the panels)', 'anim': 'kid', 'note': 'Also: worried, hug, pyjamas, sitting'})
    out['assets/sprites/parent_body.png'] = ([parent_body()], None, {'section': 'Characters (drawn into the panels)', 'anim': 'parent', 'note': 'Full length, matches the portrait'})
    return out


def g9_mockups():
    ci, sp = panel(18, 18, 'W', ring='E'), speech_bubble()
    pface = crop(parent_frames()['talk'][1], 11, 5, 26, 26)
    vface = crop(vet_frames()['talk'][1], 11, 5, 26, 26)
    out = []
    for name, (who, line) in STORY_LINES.items():
        items = [(f'assets/screens/panel_{name}_caramel.png', 0, 0, 2), ('@rect', 0, 0, 640, 30, '#D7C4EC'), ('@rect', 0, 292, 640, 68, '#D7C4EC')]
        if who:
            items += [('@canvas', nine(ci, 30, 30, 6), 8, 296, 2), ('@canvas', pface if who == 'parent' else vface, 12, 300, 2)]
        x0 = 82 if who else 20
        items += [('@canvas', nine(sp, (622 - x0) // 2, 26, 5), x0, 302, 2), ('@text', x0 + 16, 312, 600 - x0, line, 16, INK, 'left'),
                  ('@text', 560, 8, 72, 'Skip', 13, INK, 'right')]
        out.append((f'{name} ({"the " + who if who else "story, no speaker"})', (640, 360), items))
    return out


# ---------------------------------------------------------------- group 10: Level 2, spot the difference + bath time
# One big young dog (76x62, feet on y=58) drawn healthy; the four problems the vet finds are separate layers on top
# (ISSUES). Spot the difference shows them all on "your" dog; bath time removes them one by one as each is cared for.
BIG_W, BIG_H, BIG_GROUND = 76, 62, 58
BIG_PAWS = ((19, 'B'), (26, 'A'), (51, 'B'), (58, 'A'))          # paw centre x, colour (far legs in shade)


def big_dog(eyes='open'):
    c = Canvas(BIG_W, BIG_H)
    for i, (x, y) in enumerate(((15, 27), (12, 24), (10, 21), (8, 18), (7, 15), (7, 12), (8, 9))):   # tail, up and happy
        c.rect(x - 2, y - 2, 4, 4, 'A' if i < 5 else 'C')
    for px, col in BIG_PAWS:                                                   # legs + white paws
        c.rect(px - 3, 36, 6, 18, col)
        c.ellipse(px + 1, 55.5, 4.5, 2.6, 'C')
    c.ellipse(34, 32, 22, 11, 'A', shade='B', light='C')                        # body
    c.ellipse(52, 34, 8, 10, 'A', shade='B')                                    # chest
    c.ellipse(58, 18, 11, 10, 'A', light='C')                                   # head
    c.ellipse(67, 23, 7.5, 5, 'C')                                              # snout
    c.ellipse(66, 30, 5, 2.2, 'C')                                              # lower jaw
    c.rect(62, 27, 10, 2, 'k'); c.rect(63, 27, 8, 1, 'W'); c.rect(65, 29, 4, 2, 'N')   # open mouth: teeth, tongue
    c.rect(72, 18, 3, 3, 'k'); c.put(72, 18, 'w')                               # nose
    if eyes == 'open':
        c.rect(60, 13, 3, 3, 'k'); c.put(61, 13, 'w')
    else:
        c.rect(60, 15, 3, 1, 'k')
    c.rect(60, 19, 2, 1, 'N')                                                   # blush
    c.ellipse(50, 19, 4.5, 9, 'B')                                              # floppy ear
    c.recolor_filled(45, 27, 4, 8, 'R'); c.rect(46, 35, 2, 2, 'Y')               # collar + tag
    return c.outline()


def issue(name):
    """One problem, as a layer drawn over big_dog() at the same position."""
    c = Canvas(BIG_W, BIG_H)
    if name == 'nails':                                                         # long nails poking out of every paw
        for px, _ in BIG_PAWS:
            c.rect(px + 5, 55, 3, 2, 'W'); c.rect(px + 7, 56, 2, 2, 'W')
        return c.outline()
    if name == 'ears':                                                          # brown wax round the ear opening
        c.ellipse(51, 24, 2.2, 2, 't'); c.put(49, 20, 'y'); c.put(52, 16, 't'); c.rect(48, 26, 2, 1, 'd'); c.put(53, 21, 'y')
    elif name == 'teeth':                                                       # yellow tartar
        c.rect(63, 27, 8, 1, 'y'); c.put(64, 27, 't'); c.put(67, 27, 't'); c.put(70, 27, 't')
    elif name == 'fleas':                                                       # fleas and itchy red spots on the back
        for x, y in ((26, 24), (36, 23), (31, 28), (42, 27), (20, 29)):
            c.pattern(x, y, ['k.k', '.k.'])
        for x, y in ((29, 26), (39, 26), (23, 27)):
            c.put(x, y, 'R')
    return c


ISSUES = ('nails', 'ears', 'teeth', 'fleas')


def dog_with(issues):
    c = big_dog()
    for n in issues:
        paste(c, issue(n), 0, 0)
    return c


def _in_region(part, x, y):
    e = lambda cx, cy, rx, ry: ((x + 0.5 - cx) / rx) ** 2 + ((y + 0.5 - cy) / ry) ** 2 <= 1
    return {'ears': lambda: e(50, 19, 6, 10.5), 'teeth': lambda: 59 <= x and 21 <= y <= 33, 'eyes': lambda: e(61, 14, 4.5, 4.5),
            'paws': lambda: y >= 49, 'coat': lambda: e(32, 30, 19, 9) and x >= 14, 'tail': lambda: x <= 15 and y <= 27,
            'neck': lambda: e(45, 24, 4, 5)}[part]()


BODY_PARTS = ('ears', 'teeth', 'eyes', 'paws', 'coat', 'tail')               # tappable in spot the difference
BATH_PARTS = ('teeth', 'paws', 'ears', 'coat', 'neck')                        # drop targets in bath time


def part_mask(part):
    """The part's shape (any colour, used for pixel-perfect taps), from the dog with every problem showing."""
    full, c = dog_with(ISSUES), Canvas(BIG_W, BIG_H)
    for y in range(BIG_H):
        for x in range(BIG_W):
            if full.px[y][x] and _in_region(part, x, y):
                c.px[y][x] = 'W'
    return c


def part_ring(part):
    """Hover highlight, drawn over the dog: a white line round the part with butter outside it, so it shows on every coat."""
    m, c = part_mask(part), Canvas(BIG_W, BIG_H)
    near = lambda g, x, y: any(g.get(x + dx, y + dy) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))
    for y in range(BIG_H):
        for x in range(BIG_W):
            if m.px[y][x] is None and near(m, x, y):
                c.px[y][x] = 'w'
    for y in range(BIG_H):
        for x in range(BIG_W):
            if m.px[y][x] is None and c.px[y][x] is None and near(c, x, y) and any(c.get(x + dx, y + dy) == 'w' for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                c.px[y][x] = 'Y'
    return c


# ---- the five products on each tray: [healthy kit, the bag from home]. The brush is the same in both (a decoy).
PAW4 = ['k..k', '.kk.', 'kkkk', '.kk.']


def tray_item(name, side):
    good = side == 'dog'
    if name == 'toothpaste':
        c = Canvas(24, 10)
        c.rect(1, 2, 16, 6, 'M' if good else 'W'); c.rect(1, 2, 2, 6, 'm' if good else 'E')
        if good:
            c.rect(5, 3, 9, 4, 'W'); c.pattern(8, 3, PAW4)
        else:
            for x in (5, 9, 13):
                c.rect(x, 2, 2, 6, 'S' if x != 9 else 'M')
        c.rect(17, 3, 5, 4, 'W' if good else 'R')
    elif name == 'shampoo':
        c = Canvas(14, 22)
        body, shade = ('S', 's') if good else ('N', 'p')
        c.rect(2, 6, 10, 15, body); c.rect(10, 6, 2, 15, shade); c.rect(4, 3, 6, 3, 'W'); c.rect(5, 1, 4, 2, 'M' if good else 'W')
        c.rect(3, 10, 7, 7, 'W')
        if good:
            c.pattern(4, 11, PAW4)
        else:
            c.pattern(4, 11, ['.Y.', 'YRY', '.Y.']); c.rect(5, 14, 1, 2, 'G')
    elif name == 'flea':
        c = Canvas(16, 16)
        body, shade = ('M', 'm') if good else ('L', 'l')
        c.rect(1, 2, 14, 13, body); c.rect(12, 2, 3, 13, shade); c.rect(3, 5, 9, 7, 'W')
        c.pattern(5, 6, ['k...k', 'kkkkk', 'kk.kk', '.kkk.'] if good else ['k...k', 'kk.kk', 'kkkkk', '.kkk.'])
        if good:
            c.put(5, 6, 'd'); c.put(9, 6, 'd')                                  # floppy ears (dog) vs pointy (cat)
    elif name == 'toy':
        if good:
            c = Canvas(18, 18)
            c.ellipse(9, 9, 7.5, 7.5, 'R', shade='r', light='N')
            for y in range(18):
                for x in range(18):
                    if ((x + 0.5 - 9) / 3) ** 2 + ((y + 0.5 - 9) / 3) ** 2 <= 1:
                        c.px[y][x] = None
        else:
            c = Canvas(8, 8)
            c.ellipse(4, 4, 2.6, 2.6, 'Y', shade='y'); c.put(3, 3, 'w')
    elif name == 'brush':
        c = Canvas(22, 10)
        c.rect(1, 4, 8, 3, 'D'); c.rect(9, 2, 11, 4, 'D'); c.rect(9, 5, 11, 1, 'd')
        for x in range(10, 20, 2):
            c.rect(x, 6, 1, 3, 'W')
    return c.outline()


TRAY = ('toothpaste', 'shampoo', 'flea', 'toy', 'brush')
DIFFS = ('nails', 'ears', 'teeth', 'fleas', 'toothpaste', 'shampoo', 'flea', 'toy')     # the 8 to find
# Spot-the-difference layout, world px. Mirrored by LEVEL2.spot in src/content.js.
SPOT = dict(frames=(6, 164), top=28, w=150, h=144, dog_dx=37, dog_feet=114, item_xs=(20, 46, 74, 102, 130), item_bottom=162)


def draw_spot_bg():
    """The clinic wall with two framed pictures (left: the healthy chart, right: your dog) on mats, each with a tray."""
    c = Canvas(320, 180)
    c.rect(0, 0, 320, 180, 'S')
    for y in range(6, 180, 12):
        for x in range(4 + (6 if (y // 12) % 2 else 0), 320, 12):
            c.put(x, y, 's')
    for fx in SPOT['frames']:
        box(c, fx, SPOT['top'], SPOT['w'], SPOT['h'], 'D'); c.rect(fx + 1, SPOT['top'] + 1, SPOT['w'] - 2, 1, 'w')
        box(c, fx + 4, SPOT['top'] + 4, SPOT['w'] - 8, SPOT['h'] - 8, 'W')
        box(c, fx + 45, SPOT['top'] + 1, 60, 14, 'Y'); c.rect(fx + 46, SPOT['top'] + 12, 58, 2, 'y')   # name plate (words drawn in game)
        f = SPOT['dog_feet']
        box(c, fx + 26, f - 2, 98, 6, 'M'); c.rect(fx + 27, f + 2, 96, 1, 'm')        # the mat the dog stands on
        box(c, fx + 8, 132, SPOT['w'] - 16, 34, 'E'); c.rect(fx + 9, 160, SPOT['w'] - 18, 5, 'P')   # tray
    return c


# ---- close-ups (120x110 each, shown side by side at 2x). Hit boxes (x, y, w, h) are mirrored in LEVEL2.spot.closeups.
CU_W, CU_H = 120, 110


def _cu(draw):
    big = Canvas(320, 180)
    draw(big)
    return crop(big, 100, 70, CU_W, CU_H)


def cu_teeth(tartar):
    def d(c):
        c.rect(100, 70, 120, 110, 'r')
        c.rect(100, 70, 120, 28, 'A'); c.rect(100, 92, 120, 6, 'B')
        blob(c, 160, 82, 13, 7, 'k', 'K'); c.rect(154, 78, 5, 2, 'w')
        c.rect(100, 98, 120, 9, 'N'); c.rect(100, 105, 120, 2, 'p')
        for (x, w, h, tar) in ((114, 11, 24, 11), (128, 9, 15, 8), (139, 9, 14, 7), (150, 9, 15, 9),
                               (161, 9, 14, 6), (172, 9, 15, 8), (183, 9, 14, 7), (195, 11, 24, 12)):
            box(c, x, 106, w, h, 'W')
            c.rect(x + 1, 107, 1, h - 3, 'w')
            if tartar:
                c.rect(x + 1, 107, w - 2, tar, 'y'); c.rect(x + 1, 106 + tar, w - 2, 1, 't')
                c.put(x + 2, 108, 't'); c.put(x + w - 3, 110 + tar // 2, 't')
        c.ellipse(160, 146, 28, 9, 'N', shade='p'); c.rect(160, 138, 1, 9, 'p')
        c.rect(100, 152, 120, 28, 'A'); c.rect(100, 152, 120, 3, 'B')
        c.rect(100, 148, 120, 6, 'N')
        for x in range(122, 200, 12):
            box(c, x, 138, 9, 11, 'W')
            if tartar:
                c.rect(x + 1, 144, 7, 4, 'y'); c.rect(x + 1, 144, 7, 1, 't')
    return _cu(d)


def cu_coat(fleas):
    def d(c):
        c.rect(100, 70, 120, 110, 'A')
        for j, y in enumerate(range(72, 178, 7)):
            for x in range(100 + (j % 3) * 3, 222, 11):
                c.pattern(x, y, ['B..', '.B.', '..B'] if (x + y) % 3 else ['..C', '.C.', 'C..'])
        if not fleas:
            for x, y in ((130, 96), (190, 140)):
                c.pattern(x, y, ['.w.', 'www', '.w.'])                           # a shiny, healthy coat
            return
        for x, y in ((126, 98), (188, 150), (120, 146)):
            c.pattern(x, y, ['.R.', 'RRR', '.R.'])
        for i in range(8):
            c.put(126 + i * 4, 146 - i * 3 - (i * i) // 3, 'w')
        blob(c, 166, 110, 14, 10, 'h', 'K', light='H'); blob(c, 179, 104, 6, 6, 'h', 'K')
        c.put(181, 103, 'w'); c.put(182, 105, 'w')
        for lx, ly in ((154, 119), (160, 121), (168, 121), (175, 119)):
            line(c, lx, ly, lx - 3, ly + 6, 'K', 2)
        c.pattern(184, 92, ['..KK', '.KK.', 'KK..']); c.pattern(188, 96, ['KK..', '.KK.', '..KK'])
    return _cu(d)


def cu_paws(long):
    def d(c):
        c.rect(100, 70, 120, 110, 'M')
        for x in range(100, 220, 16):
            c.rect(x, 70, 1, 110, 'm')
        blob(c, 160, 154, 26, 16, 'A', 'K', shade='B', light='C')
        blob(c, 160, 157, 13, 7, 'N', 'K', shade='p')
        for tx, ty in ((131, 130), (150, 119), (170, 119), (189, 130)):
            blob(c, tx, ty, 8, 10, 'A', 'K', shade='B', light='C')
        n = 15 if long else 5
        for nx, ny, lean in ((130, 120, -3), (149, 109, -1), (171, 109, 1), (190, 120, 3)):
            for i in range(n):
                x = nx + (lean * (i * i)) // 70
                c.rect(x - 2, ny - i, 5, 1, 'K')
            for i in range(n - 1):
                x = nx + (lean * (i * i)) // 70
                c.rect(x - 1, ny - i, 3, 1, 'W' if i % 5 else 'E')
        if long:
            for x, y in ((111, 100), (206, 100), (160, 88)):
                c.pattern(x, y, ['K.K', '.K.', 'K.K'])
    return _cu(d)


def cu_ears(wax):
    def d(c):
        c.rect(100, 70, 120, 110, 'E')
        blob(c, 160, 124, 36, 48, 'B', 'K', light='A')
        for x, y in ((127, 100), (129, 138), (192, 104), (194, 140)):
            c.rect(x, y, 3, 2, 'A')
        c.ellipse(161, 128, 27, 38, 'N', shade='p'); c.ellipse(161, 130, 21, 31, 'P')
        for dy, rx, ry in ((0, 15, 24), (2, 10, 17)):
            for a in range(0, 360, 6):
                c.put(round(161 + rx * math.cos(math.radians(a))), round(132 + ry * math.sin(math.radians(a))), 'p')
        if wax:
            c.ellipse(161, 140, 9, 11, 'y'); c.ellipse(161, 142, 6, 7, 't'); c.ellipse(161, 143, 3, 4, 'k')
            for x, y, w in ((148, 124, 5), (172, 120, 4), (150, 150, 4), (174, 148, 5)):
                c.rect(x, y, w, 2, 'y'); c.rect(x, y + 1, w, 1, 't')
        else:
            c.ellipse(161, 143, 3, 4, 'p')
            for x, y in ((116, 88), (204, 100)):
                c.pattern(x, y, ['.w.', 'www', '.w.'])
    return _cu(d)


def cu_eyes():
    def d(c):
        c.rect(100, 70, 120, 110, 'A')
        for j, y in enumerate(range(72, 178, 8)):
            for x in range(100 + (j % 2) * 5, 222, 10):
                c.pattern(x, y, ['B.', '.B'])
        c.ellipse(160, 126, 30, 24, 'W'); c.ellipse(160, 128, 20, 20, 'h'); c.ellipse(160, 128, 13, 13, 'k')
        c.rect(150, 116, 7, 6, 'w'); c.rect(167, 134, 3, 3, 'w')
        ring(c, 160, 126, 30, 24, ('W', 'h', 'k', 'w'))
        for x in range(134, 188, 6):                                               # lashes
            c.rect(x, 101 - abs(x - 160) // 6, 2, 3, 'K')
        c.ellipse(160, 160, 34, 3, 'B')
    return _cu(d)


def cu_tail():
    def d(c):
        c.rect(100, 70, 120, 110, 'M')
        for x in range(100, 220, 16):
            c.rect(x, 70, 1, 110, 'm')
        for i in range(9):                                                         # a big fluffy tail curling up
            cx, cy = 130 + i * 9, 170 - i * 10 + (i * i) // 2
            blob(c, cx, cy, 14 - i // 2, 12 - i // 2, 'A' if i < 7 else 'C', 'K', shade='B' if i < 7 else None)
        for x, y in ((140, 150), (160, 128), (178, 110)):
            c.pattern(x, y, ['B..', '.B.', '..B'])
    return _cu(d)


def _counter(c):
    c.rect(100, 70, 120, 110, 'W')
    for y in range(70, 180, 9):
        for x in range(100 if (y // 9) % 2 else 109, 220, 18):
            c.rect(x, y, 9, 9, 'E')


def cu_toothpaste(good):
    def d(c):
        _counter(c)
        c.rect(110, 104, 84, 34, 'K'); c.rect(111, 105, 82, 32, 'M' if good else 'W')
        for x in range(111, 117):
            c.rect(x, 105, 1, 32, 'm' if good else 'E')
        c.rect(193, 112, 14, 18, 'K'); c.rect(194, 113, 12, 16, 'W' if good else 'R')
        box(c, 124, 109, 58, 24, 'W')
        if good:
            big_text(c, 128, 114, 'DOG', 'K', 2); c.pattern(168, 115, ['k...k', '.kkk.', 'kkkkk', 'kkkkk', '.kkk.'])
        else:
            big_text(c, 127, 114, 'MINT', 'S', 2)
            for x in (116, 186):
                c.rect(x, 105, 3, 32, 'S')
    return _cu(d)


def cu_shampoo(good):
    def d(c):
        _counter(c)
        body, shade = ('S', 's') if good else ('N', 'p')
        c.rect(138, 76, 20, 8, 'K'); c.rect(139, 77, 18, 7, 'M' if good else 'W')       # cap
        c.rect(126, 84, 44, 88, 'K'); c.rect(127, 85, 42, 86, body); c.rect(160, 85, 9, 86, shade)
        box(c, 130, 104, 36, 44, 'W')
        if good:
            big_text(c, 131, 109, 'DOG', 'K', 2); c.pattern(140, 130, ['k...k', '.kkk.', 'kkkkk', 'kkkkk', '.kkk.'])
        else:
            big_text(c, 135, 109, 'HAIR', 'p', 1)
            c.pattern(141, 124, ['..YY..', '.YYYY.', 'YYRRYY', 'YYRRYY', '.YYYY.', '..YY..']); c.rect(143, 130, 2, 10, 'G')
    return _cu(d)


def cu_flea(good):
    def d(c):
        _counter(c)
        body, shade = ('M', 'm') if good else ('L', 'l')
        c.rect(112, 86, 92, 86, 'K'); c.rect(113, 87, 90, 84, body); c.rect(192, 87, 11, 84, shade)
        box(c, 122, 96, 62, 64, 'W')
        big_text(c, 135, 100, 'DOG' if good else 'CAT', 'K', 2)
        if good:                                                                   # floppy-eared dog head
            c.ellipse(153, 136, 13, 11, 'D'); c.ellipse(139, 134, 4, 9, 'd'); c.ellipse(167, 134, 4, 9, 'd')
            c.ellipse(153, 142, 6, 4, 'W'); c.rect(151, 139, 4, 3, 'k'); c.put(147, 132, 'k'); c.put(159, 132, 'k')
        else:                                                                      # pointy-eared cat head
            c.ellipse(153, 138, 13, 11, 'O')
            c.pattern(140, 120, ['O...........O', 'OO.........OO', 'OOO.......OOO', 'OOOO.....OOOO'])
            c.put(147, 135, 'k'); c.put(159, 135, 'k'); c.pattern(151, 140, ['kkk', '.k.'])
            for wy in (141, 144):
                c.rect(137, wy, 7, 1, 'K'); c.rect(163, wy, 7, 1, 'K')
    return _cu(d)


def cu_toy(good):
    """The toy next to the dog's muzzle, for size: a chew ring too big to swallow vs a ball that fits in the mouth."""
    def d(c):
        _counter(c)
        c.ellipse(212, 128, 26, 20, 'A', light='C'); c.ellipse(200, 140, 18, 9, 'C')      # the dog's muzzle, right
        c.rect(182, 128, 6, 5, 'k'); c.put(183, 128, 'w')
        c.rect(184, 146, 26, 3, 'k')                                                   # mouth line
        if good:
            blob(c, 140, 136, 26, 26, 'R', 'K', shade='r', light='N')
            c.ellipse(140, 136, 10, 10, 'W'); ring(c, 140, 136, 10, 10, ('W',))
        else:
            blob(c, 166, 146, 6, 6, 'Y', 'K', shade='y'); c.put(164, 143, 'w')
            for x, y in ((150, 132), (176, 128)):
                c.pattern(x, y, ['.R.', 'R.R', '.R.'])
    return _cu(d)


def cu_brush():
    def d(c):
        _counter(c)
        c.rect(110, 126, 44, 14, 'K'); c.rect(111, 127, 42, 12, 'D')
        c.rect(150, 112, 58, 26, 'K'); c.rect(151, 113, 56, 24, 'D'); c.rect(151, 132, 56, 5, 'd')
        for x in range(154, 206, 5):
            c.rect(x, 138, 2, 12, 'W'); c.rect(x, 149, 2, 1, 'E')
    return _cu(d)


CLOSEUPS10 = {   # part: (healthy, yours); the same function twice means "no difference" (a decoy)
    'teeth': (lambda: cu_teeth(False), lambda: cu_teeth(True)), 'coat': (lambda: cu_coat(False), lambda: cu_coat(True)),
    'paws': (lambda: cu_paws(False), lambda: cu_paws(True)), 'ears': (lambda: cu_ears(False), lambda: cu_ears(True)),
    'eyes': (cu_eyes, None), 'tail': (cu_tail, None),
    'toothpaste': (lambda: cu_toothpaste(True), lambda: cu_toothpaste(False)), 'shampoo': (lambda: cu_shampoo(True), lambda: cu_shampoo(False)),
    'flea': (lambda: cu_flea(True), lambda: cu_flea(False)), 'toy': (lambda: cu_toy(True), lambda: cu_toy(False)),
    'brush': (cu_brush, None),
}
CU_HITS = {'teeth': (12, 34, 96, 46), 'coat': (46, 24, 44, 34), 'paws': (20, 28, 80, 26), 'ears': (44, 52, 34, 34),
           'toothpaste': (22, 37, 62, 28), 'shampoo': (28, 32, 42, 48), 'flea': (20, 24, 66, 68), 'toy': (52, 60, 26, 26)}
COAT_PARTS = ('teeth', 'coat', 'paws', 'ears', 'eyes', 'tail', 'toy')   # the toy is held up to your dog's muzzle


# ---- bath time: the bathroom, the tub (its front is a layer over the dog), the shelf of care things, foam
BATH = dict(mat_x=172, mat_feet=130, tub_x=62, tub_feet=112, shelf_x=(270, 294), boards=(56, 94))   # mirrored in LEVEL2.bath


def draw_bath_bg():
    c = Canvas(320, 180)
    bathroom(c)
    c.rect(24, 22, 160, 2, 'E'); c.rect(24, 22, 160, 1, 'K')                     # curtain rail + bunched curtain (below the HUD)
    for x in range(26, 50, 4):
        c.rect(x, 24, 4, 56, 'M'); c.rect(x + 3, 24, 1, 56, 'm')
    c.rect(26, 79, 24, 1, 'K')
    c.rect(40, 70, 4, 22, 'E'); box(c, 36, 66, 14, 6, 'E'); c.rect(46, 72, 2, 3, 'S')   # tap
    box(c, 28, 92, 148, 10, 'W'); c.rect(29, 93, 146, 1, 'w')                     # tub rim (the front is its own layer)
    c.ellipse(102, 98, 70, 3, 'S')
    box(c, 166, 128, 86, 7, 'M')                                                  # bath mat
    for x in range(170, 250, 8):
        c.rect(x, 129, 2, 5, 'm')
    box(c, 262, 56, 52, 4, 'D'); box(c, 262, 94, 52, 4, 'D')                     # shelf boards
    c.rect(264, 60, 2, 6, 'd'); c.rect(310, 60, 2, 6, 'd'); c.rect(264, 98, 2, 6, 'd'); c.rect(310, 98, 2, 6, 'd')
    box(c, 200, 24, 40, 30, 'W'); box(c, 204, 28, 32, 22, 'S'); c.rect(206, 30, 8, 1, 'w')   # little mirror
    paste(c, rubber_duck(), 152, 84)
    return c


def rubber_duck():
    c = Canvas(14, 10)
    c.ellipse(6, 6, 5, 3, 'Y', shade='y'); c.ellipse(9, 3, 3, 2.5, 'Y'); c.rect(12, 3, 2, 1, 'O'); c.put(9, 2, 'k')
    return c.outline()


def draw_tub_front():
    c = Canvas(320, 180)
    box(c, 28, 100, 148, 32, 'W'); c.rect(29, 124, 146, 7, 'E'); c.rect(29, 101, 146, 1, 'w')
    for x in range(40, 170, 9):                                                  # bubbles floating on the water line
        c.ellipse(x, 100, 4, 2.5, 'W'); c.put(x - 1, 99, 'w')
    for fx in (36, 162):                                                         # claw feet
        box(c, fx, 131, 8, 6, 'Y'); c.rect(fx + 1, 135, 6, 1, 'y')
    return c


def care_item(name):
    if name == 'toothbrush':                                                    # dog toothbrush with a blob of dog toothpaste
        c = Canvas(26, 12)
        c.rect(1, 6, 15, 3, 'M'); c.rect(1, 8, 15, 1, 'm'); c.rect(15, 5, 8, 4, 'W')
        for x in range(16, 23, 2):
            c.rect(x, 3, 1, 2, 'S')
        c.ellipse(19, 2.5, 3, 1.5, 'M')
        return c.outline()
    if name == 'clippers':
        c = Canvas(20, 14)
        c.rect(1, 3, 9, 3, 'R'); c.rect(1, 8, 9, 3, 'R'); c.rect(9, 4, 4, 6, 'E'); c.rect(13, 5, 5, 4, 'E'); c.rect(14, 7, 4, 1, 'K')
        c.put(10, 7, 'K')
        return c.outline()
    if name == 'ear':                                                           # ear cleaner (dog)
        c = Canvas(12, 20)
        c.rect(2, 6, 8, 13, 'Y'); c.rect(8, 6, 2, 13, 'y'); c.rect(4, 2, 4, 4, 'W'); c.rect(5, 0, 2, 2, 'W')
        c.rect(3, 9, 6, 6, 'W'); c.pattern(4, 10, ['.dd.', 'd..d', 'd.d.', '.d..'])
        return c.outline()
    if name == 'towel':
        c = Canvas(24, 14)
        c.rect(1, 3, 22, 10, 'L'); c.rect(1, 1, 22, 3, 'L'); c.rect(1, 6, 22, 1, 'l'); c.rect(1, 10, 22, 2, 'l')
        for x in range(3, 22, 4):
            c.put(x, 12, 'W')
        return c.outline()
    return tray_item({'shampoo': 'shampoo', 'flea': 'flea'}[name], 'dog')


CARE = ('toothbrush', 'clippers', 'ear', 'shampoo', 'towel', 'flea')          # shelf order (top board: 3, bottom board: 3)


def foam_frames():
    out = []
    spots = [(22, 26), (32, 22), (42, 26), (28, 30), (38, 30), (48, 28), (18, 32), (52, 22), (34, 34), (44, 33), (24, 24), (56, 30)]
    for n in (4, 8, 12):
        c = Canvas(BIG_W, BIG_H)
        for i, (x, y) in enumerate(spots[:n]):
            r = 3 + (i % 3)
            c.ellipse(x, y, r, r - 0.5, 'W', shade='E'); c.put(x - 1, y - 2, 'w')
        out.append(c.outline('S'))
    return out


FONT5x7.update({
    'D': ['11110', '10001', '10001', '10001', '10001', '10001', '11110'], 'O': ['01110', '10001', '10001', '10001', '10001', '10001', '01110'],
    'G': ['01111', '10000', '10000', '10011', '10001', '10001', '01111'], 'M': ['10001', '11011', '10101', '10101', '10001', '10001', '10001'],
    'I': ['11111', '00100', '00100', '00100', '00100', '00100', '11111'], 'H': ['10001', '10001', '10001', '11111', '10001', '10001', '10001']})


def group10():
    out, S_, U = {}, 'assets/sprites/', 'assets/ui/'
    out['assets/bg/spot_bg.png'] = ([draw_spot_bg()], None, {'section': 'bg', 'anim': 'spot'})
    out['assets/bg/bath_bg.png'] = ([draw_bath_bg()], None, {'section': 'bg', 'anim': 'bath'})
    out['assets/bg/bath_tub_front.png'] = ([draw_tub_front()], None, {'section': 'bg', 'anim': 'tub front'})
    d = 'The big young dog (both tasks): healthy, plus one layer per problem'
    for coat, cols in COATS.items():
        out[S_ + f'big_{coat}.png'] = ([big_dog(), big_dog('closed')], cols, {'section': d, 'anim': 'healthy dog', 'coat': coat, 'note': 'Open eyes, then a happy blink'})
    for n in ISSUES:
        out[S_ + f'issue_{n}.png'] = ([issue(n)], None, {'section': d, 'anim': f'problem: {n}', 'note': 'Drawn over the dog until it is cared for'})
    out[S_ + 'foam.png'] = (foam_frames(), None, {'section': d, 'anim': 'shampoo foam', 'note': 'Grows as the player scrubs'})
    p = 'Tappable parts: the hover ring (the shape itself is used for taps)'
    for part in BODY_PARTS + ('neck',):
        out[S_ + f'part_{part}.png'] = ([part_mask(part)], None, {'section': 'bg', 'anim': part})
        out[S_ + f'ring_{part}.png'] = ([part_ring(part)], None, {'section': p, 'anim': part, 'note': 'Bath only' if part == 'neck' else 'Spot + bath' if part in BATH_PARTS else 'Spot only'})
    t = 'Tray products: the healthy kit (dog) vs the bag from home'
    for name in TRAY:
        for side in (('dog',) if name == 'brush' else ('dog', 'home')):
            out[S_ + f'tray_{name}_{side}.png'] = ([tray_item(name, side)], None, {'section': t, 'anim': f'{name} ({side})', 'note': 'Same in both (decoy)' if name == 'brush' else ''})
    cu = 'Close-ups (tap a part to compare both)'
    for part, (h, y) in CLOSEUPS10.items():
        for side, fn in (('healthy', h), ('yours', y)):
            if fn is None:
                continue
            if part in COAT_PARTS:
                art = fn()
                for coat, cols in COATS.items():
                    out[f'assets/screens/cu_{part}_{side}_{coat}.png'] = ([art], cols, {'section': 'bg', 'anim': part})
            else:
                out[f'assets/screens/cu_{part}_{side}.png'] = ([fn()], None, {'section': 'bg', 'anim': part})
    b = 'Bath time: the care things on the shelf'
    for name in CARE:
        if name not in ('shampoo', 'flea'):
            out[S_ + f'care_{name}.png'] = ([care_item(name)], None, {'section': b, 'anim': name, 'note': {'toothbrush': 'Dog toothbrush + dog toothpaste → teeth',
                'clippers': 'Nail clippers → paws', 'ear': 'Ear cleaner → ears', 'towel': 'Towel → rub dry'}[name]})
    out[U + 'icon_bath.png'] = ([icon('bath')], None, {'section': b, 'anim': 'bath icon', 'note': 'Album skill "Grooming", task card'})
    return out


def g10_mockups():
    caramel = COATS['caramel']
    ci, bm, bc = panel(18, 18, 'W', ring='E'), button('M', 'm', 'Y')[0], button('W', 'E', 'Y')[0]
    t = lambda x, y, w, s, size, col=INK, al='center': ('@text', x, y, w, s, size, col, al)
    W2 = (640, 360)

    def overview(found_teeth=True, hover='ears'):
        items = [('@canvas', draw_spot_bg(), 0, 0, 2)] + hud8(50, 'Biscuit', 'magnifier', f'Found {1 if found_teeth else 0} of 8')
        for side, fx in zip(('healthy', 'yours'), SPOT['frames']):
            dog = big_dog() if side == 'healthy' else dog_with(ISSUES)
            dx, dy = fx + SPOT['dog_dx'], SPOT['dog_feet'] - BIG_GROUND
            items += [('@canvas', dog, dx * 2, dy * 2, 2, caramel), ('@canvas', part_ring(hover), dx * 2, dy * 2, 2)]
            items.append(t((fx + 45) * 2, (SPOT['top'] + 3) * 2, 120, 'Healthy' if side == 'healthy' else 'Biscuit', 14))
            for name, ix in zip(TRAY, SPOT['item_xs']):
                cv = tray_item(name, 'dog' if side == 'healthy' or name == 'brush' else 'home')
                items.append(('@canvas', cv, (fx + ix) * 2 - cv.w, (SPOT['item_bottom'] - cv.h) * 2, 2))
            if found_teeth and side == 'yours':
                items.append(('@canvas', found_ring(20, 18), (dx + 58) * 2, (dy + 18) * 2, 2))
        return items + [('@canvas', paw_cursor(), (SPOT['frames'][1] + SPOT['dog_dx'] + 50) * 2 + 4, (SPOT['dog_feet'] - BIG_GROUND + 22) * 2, 1)]

    def closer(part, title_l='Healthy', found_hit=True):
        h, y = CLOSEUPS10[part]
        L, R = h(), (y or h)()
        items = overview(True, 'ears') + [('@rect', 0, 0, 640, 360, 'rgba(62,42,36,0.55)')]
        for cv, x, label in ((L, 64, title_l), (R, 336, 'Biscuit')):
            items += [('@canvas', nine(ci, 128, 132, 6), x - 8, 48, 2), t(x, 58, 240, label, 16),
                      ('@canvas', cv, x, 84, 2, caramel)]
        if found_hit and part in CU_HITS:
            hx, hy, hw, hh = CU_HITS[part]
            ring_cv = found_ring(hw + 6, hh + 6)
            items += [('@canvas', ring_cv, 336 + (hx - 3) * 2, 84 + (hy - 3) * 2, 2), ('@canvas', ring_cv, 64 + (hx - 3) * 2, 84 + (hy - 3) * 2, 2)]
        return items + [('@canvas', nine(bm, 50, 16, 5), 270, 316, 2), t(270, 322, 100, 'Back', 17)]

    def bath(on_mat=True, foam=None, done=()):
        items = [('@canvas', draw_bath_bg(), 0, 0, 2)]
        x, feet = (BATH['mat_x'], BATH['mat_feet']) if on_mat else (BATH['tub_x'], BATH['tub_feet'])
        items.append(('@canvas', dog_with([i for i in ISSUES if i not in done]), x * 2, (feet - BIG_GROUND) * 2, 2, caramel))
        if foam is not None:
            items.append(('@canvas', foam_frames()[foam], x * 2, (feet - BIG_GROUND) * 2, 2))
        items.append(('@canvas', draw_tub_front(), 0, 0, 2))
        for i, name in enumerate(CARE):
            cv = care_item(name)
            bx = BATH['shelf_x'][0] + (i % 3) * 16 - 4
            items.append(('@canvas', cv, bx * 2, (BATH['boards'][i // 3] - cv.h) * 2, 2))
        return items + hud8(40, 'Biscuit', 'bath', 'Bath time  2 of 2')

    start = bath() + [('@canvas', part_ring('teeth'), BATH['mat_x'] * 2, (BATH['mat_feet'] - BIG_GROUND) * 2, 2),
                      ('@canvas', care_item('toothbrush'), (BATH['mat_x'] + 78) * 2, (BATH['mat_feet'] - BIG_GROUND + 22) * 2, 2)]
    scrub = bath(False, 1, ('teeth', 'nails', 'ears')) + [('@canvas', hand_frames()[1], (BATH['tub_x'] + 34) * 2, (BATH['tub_feet'] - BIG_GROUND + 20) * 2, 2)]
    return [('Spot the difference: hovering the ears highlights them in both pictures (the tartar is already found)', W2, overview()),
            ('Closer look: paws (the long nails are found and circled in both)', W2, closer('paws')),
            ('Closer look: the toothpaste from home is for people', W2, closer('toothpaste')),
            ('Closer look: a decoy (the eyes are the same in both)', W2, closer('eyes', found_hit=False)),
            ('Bath time: dragging the dog toothbrush to the teeth (the drop target lights up)', W2, start),
            ('Bath time: in the tub, scrubbing in the shampoo (teeth, nails and ears done)', W2, scrub)]


# ---------------------------------------------------------------- group 8: blocking dialogue, demos, level select, time cards
INK = '#5A3E36'
ICONS8 = {
    'help':      lambda c: c.pattern(5, 3, ['.WWWW.', 'WW..WW', '....WW', '...WW.', '..WW..', '..WW..', '......', '..WW..', '..WW..']),
    'lock':      lambda c: (c.rect(5, 2, 6, 2, 'E'), c.rect(4, 3, 2, 5, 'E'), c.rect(10, 3, 2, 5, 'E'),
                            c.rect(3, 7, 10, 7, 'Y'), c.rect(3, 12, 10, 2, 'y'), c.rect(7, 9, 2, 3, 'K')),
    'magnifier': lambda c: (c.ellipse(6.5, 6.5, 4.6, 4.6, 'W'), c.ellipse(6.5, 6.5, 3.2, 3.2, 'S'), c.put(5, 4, 'w'), c.put(4, 5, 'w'),
                            [c.rect(10 + i, 10 + i, 2, 2, 'D') for i in range(4)]),
}


def hand_frames():
    """Ghost hand for demos: a pointing hand (fingertip at HAND_TIP), then the same hand pressing down."""
    rows = ['.....WW.........', '....WWWW........', '....WWWW........', '....WWWW........', '....WWWW........',
            '....WWWWWW.WW...', '....WWWWWWWWWWW.', '.WW.WWWWWWWWWWWW', 'WWWWWWWWWWWWWWWW', 'WWWWWWWWWWWWWWWW',
            '.WWWWWWWWWWWWWWW', '..WWWWWWWWWWWWW.', '..WWWWWWWWWWWWW.', '...WWWWWWWWWWW..', '...WWWWWWWWWWW..',
            '....WWWWWWWWW...', '....SSSSSSSSS...', '....SSSSSSSSS...']
    out = []
    for press in (False, True):
        c = Canvas(18, 22)
        c.pattern(1, 3 if press else 1, rows[2:] if press else rows)   # pressing: the body stays put, the finger shortens
        for y in range(c.h):                            # shade the right edge of every row
            xs = [x for x in range(c.w) if c.px[y][x] == 'W']
            if xs:
                c.px[y][xs[-1]] = 'E'
        for x, y in ((10, 8), (13, 8), (10, 9), (13, 9)):  # knuckle creases of the folded fingers
            c.put(x, y, 'E')
        out.append(c.outline())
    return out


HAND_TIP = (7, 1)                                       # fingertip pixel (art px) of the pointing frame


def tap_ring_frames():
    out = []
    for r in (3, 5, 7):
        c = Canvas(20, 20)
        for y in range(20):
            for x in range(20):
                if r - 0.8 <= math.hypot(x + 0.5 - 10, y + 0.5 - 10) <= r + 0.2:
                    c.put(x, y, 'Y')
        out.append(c.outline())
    return out


def demo_dot():
    c = Canvas(6, 6)
    c.pattern(1, 1, ['.YY.', 'YYYY', 'YYYY', '.YY.'])
    return c.outline()


def found_ring(w, h):
    """Coral pen circle (2 px, no outline so it reads as drawn on), round a difference once found."""
    c = Canvas(w, h)
    cx, cy, rx, ry = w / 2, h / 2, w / 2 - 1, h / 2 - 1
    for y in range(h):
        for x in range(w):
            d = ((x + 0.5 - cx) / rx) ** 2 + ((y + 0.5 - cy) / ry) ** 2
            di = ((x + 0.5 - cx) / (rx - 2)) ** 2 + ((y + 0.5 - cy) / (ry - 2)) ** 2
            if d <= 1 and di > 1:
                c.put(x, y, 'R')
    return c


def time_icon(kind):
    c = Canvas(32, 32)
    rays = lambda cx, cy, r, angles: [c.rect(round(cx + r * math.cos(math.radians(a))) - 1, round(cy + r * math.sin(math.radians(a))) - 1, 3, 3, 'Y')
                                     for a in angles]
    if kind == 'morning':
        rays(16, 16, 13, range(0, 360, 45))
        c.ellipse(16, 16, 8, 8, 'Y', shade='y'); c.rect(12, 11, 3, 2, 'w')
    elif kind == 'afternoon':
        rays(12, 12, 10, range(150, 330, 45))
        c.ellipse(12, 12, 6.5, 6.5, 'Y', shade='y'); c.rect(9, 8, 2, 2, 'w')
        c.ellipse(19, 21, 8, 5, 'W', shade='E'); c.ellipse(12, 23, 5, 3.6, 'W', shade='E'); c.ellipse(25, 23, 5, 3.4, 'W', shade='E')
    elif kind == 'evening':
        rays(16, 21, 13, range(195, 350, 36))
        c.ellipse(16, 21, 9, 9, 'O', shade='o'); c.rect(12, 15, 3, 2, 'Y')
        c.ellipse(16, 30, 16, 7, 'm', shade='G')
        for y in range(28, 32):                          # nothing below the hill
            for x in range(32):
                if c.px[y][x] in ('O', 'o', 'Y'):
                    c.px[y][x] = 'm'
    elif kind == 'night':
        c.ellipse(15, 17, 9, 9, 'Y', shade='y')
        for y in range(32):
            for x in range(32):
                if ((x + 0.5 - 20) / 7.5) ** 2 + ((y + 0.5 - 13) / 7.5) ** 2 <= 1:
                    c.px[y][x] = None
        c.pattern(23, 4, ['.w.', 'wYw', '.w.']); c.pattern(25, 22, ['.Y.', 'YYY', '.Y.']); c.put(28, 13, 'Y')
    elif kind == 'later':
        c.rect(5, 7, 22, 21, 'W'); c.rect(5, 7, 22, 5, 'R'); c.rect(5, 11, 22, 1, 'r'); c.rect(5, 26, 22, 2, 'E')
        c.rect(10, 4, 2, 5, 'E'); c.rect(20, 4, 2, 5, 'E')
        for y in (14, 18, 22):
            for x in (8, 12, 16, 20):
                c.rect(x, y, 2, 2, 'E')
        c.rect(23, 21, 4, 4, 'R'); c.rect(24, 22, 2, 2, 'W')    # the circled day
    return c.outline()


TIME_ICONS = ('morning', 'afternoon', 'evening', 'night', 'later')


def draw_timecard_bg():
    """Full-screen card between story beats ("Later that afternoon"). Icon sits above the banner; the words are drawn in game."""
    c = Canvas(320, 180)
    c.rect(0, 0, 320, 180, 'L')
    for y in range(8, 180, 18):
        for x in range(10 + (9 if (y // 18) % 2 else 0), 320, 18):
            c.put(x, y, 'l')
    for x, y in ((40, 30), (276, 40), (60, 140), (250, 150), (24, 96), (296, 110), (150, 22), (190, 158)):
        c.pattern(x - 1, y - 1, ['.W.', 'WWW', '.W.'])
    tail = Canvas(26, 28)
    for y in range(1, 27):
        notch = 7 - abs(y - 14) * 7 // 13
        tail.rect(1 + notch, y, 24 - notch, 1, 'P' if y < 22 else 'p')
    tail.outline()
    paste(c, tail, 44, 84); paste(c, tail.flipped(), 320 - 44 - 26, 84)
    box(c, 62, 78, 196, 28, 'W'); c.rect(63, 102, 194, 3, 'E'); c.rect(63, 79, 194, 1, 'w')
    return c


def draw_select_bg():
    """Level select: a cork board on the hallway wall; level cards are pinned to it in game."""
    c = Canvas(320, 180)
    c.rect(0, 0, 320, 180, 'W')
    for y in range(8, 180, 14):
        for x in range(6 + (7 if (y // 14) % 2 else 0), 320, 14):
            c.pattern(x - 1, y - 1, ['.E.', 'EEE', '.E.'])
    box(c, 8, 26, 304, 150, 'D'); c.rect(9, 27, 302, 1, 'w'); c.rect(9, 173, 302, 2, 'd')
    box(c, 12, 30, 296, 142, 'T')
    for i in range(420):                                 # cork speckles
        c.put(13 + (i * 37) % 294, 31 + (i * 53 + i // 7) % 140, 't')
    return c


def _frame(c):
    c.rect(0, 0, c.w, 1, 'K'); c.rect(0, c.h - 1, c.w, 1, 'K'); c.rect(0, 0, 1, c.h, 'K'); c.rect(c.w - 1, 0, 1, c.h, 'K')
    return c


def thumb_home():
    c = Canvas(80, 56)
    wall_and_floor(c, 40)
    box(c, 7, 7, 24, 20, 'W'); box(c, 9, 9, 20, 16, 'S'); c.rect(19, 9, 1, 16, 'K'); c.ellipse(14, 13, 3, 1.5, 'W')
    box(c, 47, 20, 28, 14, 'P'); box(c, 44, 28, 34, 11, 'P'); c.rect(45, 35, 32, 3, 'p')
    c.ellipse(36, 49, 18, 3.5, 'L'); c.ellipse(36, 49, 13, 2, 'l')
    paste(c, puppy_anims()['sit'][0], 20, 22)
    return _frame(c)


def thumb_clinic():
    c = Canvas(80, 56)
    c.rect(0, 0, 80, 44, 'S')
    for y in range(4, 40, 8):
        for x in range(3 + (4 if (y // 8) % 2 else 0), 80, 8):
            c.put(x, y, 's')
    c.rect(0, 44, 80, 12, 'W'); c.rect(0, 44, 80, 1, 'K'); c.rect(0, 50, 80, 1, 'E')
    box(c, 56, 6, 18, 22, 'Y'); c.rect(59, 10, 12, 1, 'K'); c.rect(59, 14, 9, 1, 'y'); c.rect(59, 18, 11, 1, 'y'); c.rect(59, 22, 8, 1, 'y')
    box(c, 14, 46, 4, 9, 'S'); box(c, 52, 46, 4, 9, 'S')
    box(c, 10, 40, 52, 7, 'W'); box(c, 14, 37, 44, 4, 'M')
    paste(c, young_anims_l2()['sit'][0], 16, -1)
    return _frame(c)


def thumb_park():
    """Level 3 is not built: a frosted park with the adult dog as a mystery silhouette."""
    c = Canvas(80, 56)
    c.rect(0, 0, 80, 56, 'S')
    blob(c, 66, 10, 5, 5, 'Y', 'y'); c.ellipse(36, 9, 7, 2.5, 'W'); c.ellipse(41, 7, 4, 2.5, 'W')
    c.ellipse(60, 44, 34, 12, 'M'); c.rect(0, 40, 80, 16, 'm')
    for x in range(2, 80, 5):
        c.put(x, 42 + (x * 3) % 5, 'G')
    c.ellipse(40, 52, 26, 3, 'E')
    box(c, 8, 20, 4, 22, 'd'); blob(c, 10, 16, 9, 8, 'm', 'G', light='M')
    dog = adult_anims()['idle'][0]
    for j in range(dog.h):
        for i in range(dog.w):
            if dog.px[j][i]:
                c.put(28 + i, 6 + j, 'l')
    for y in range(56):
        for x in range(80):
            if x % 2 == 0 and y % 2 == 0 and c.px[y][x] != 'l':
                c.px[y][x] = 'L'
    return _frame(c)


def pin():
    c = Canvas(8, 9)
    c.ellipse(4, 3.5, 3, 3, 'R', light='N'); c.rect(4, 6, 1, 2, 'E')
    return c.outline()


def hl(cv, col='Y'):
    """Preview only: the hover highlight the game draws (a 1 px butter outline round the sprite's shape)."""
    out = Canvas(cv.w + 2, cv.h + 2)
    paste(out, cv, 1, 1)
    for y in range(out.h):
        for x in range(out.w):
            if out.px[y][x] is None and any(out.get(x + dx, y + dy) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                out.px[y][x] = col
    return out


def group8():
    U, S = 'assets/ui/', 'assets/screens/'
    out = {}
    d = 'Dialogue box (blocks the game until OK)'
    out[U + 'dialog_panel.png'] = ([panel(24, 24, 'W', ring='P', lip='E')], None, {'section': d, 'anim': 'dialogue panel', 'note': 'Nine-slice, corners 7px. Bottom third of the screen'})
    out[U + 'portrait_frame.png'] = ([panel(50, 50, 'E', ring='W')], None, {'section': d, 'anim': 'portrait frame', 'note': 'Behind the parent or vet bust'})
    out[U + 'nameplate_parent.png'] = ([panel(12, 12, 'P', lip='p', insets=(2, 1))], None, {'section': d, 'anim': 'name plate: parent', 'note': 'Nine-slice, corners 4px'})
    out[U + 'nameplate_vet.png'] = ([panel(12, 12, 'S', lip='s', insets=(2, 1))], None, {'section': d, 'anim': 'name plate: vet', 'note': 'Nine-slice, corners 4px'})
    m = 'Demos and help'
    out[U + 'hand.png'] = (hand_frames(), None, {'section': m, 'anim': 'ghost hand', 'note': 'Point, then press. Plays taps and drags in demos'})
    out[U + 'tap_ring.png'] = (tap_ring_frames(), None, {'section': m, 'anim': 'tap ring', 'note': 'Ripples out where the hand taps'})
    out[U + 'demo_dot.png'] = ([demo_dot()], None, {'section': m, 'anim': 'path dot', 'note': 'Dotted path of a drag'})
    out[U + 'icon_help.png'] = ([icon('help')], None, {'section': m, 'anim': 'help', 'note': 'HUD button: replay the demo'})
    s = 'Level select'
    out[S + 'select_bg.png'] = ([draw_select_bg()], None, {'section': 'bg', 'anim': 'cork board'})
    out[U + 'level_card.png'] = ([panel(20, 20, 'W', lip='E')], None, {'section': s, 'anim': 'level card', 'note': 'Nine-slice, corners 6px'})
    out[U + 'pin.png'] = ([pin()], None, {'section': s, 'anim': 'push pin', 'note': 'Holds each card on the board'})
    out[U + 'tag_soon.png'] = ([panel(12, 12, 'Y', lip='y', insets=(2, 1))], None, {'section': s, 'anim': 'coming soon tag', 'note': 'Nine-slice, corners 4px'})
    out[U + 'icon_lock.png'] = ([icon('lock')], None, {'section': s, 'anim': 'lock', 'note': 'Level not built yet'})
    for coat, cols in COATS.items():
        out[S + f'thumb_home_{coat}.png'] = ([thumb_home()], cols, {'section': s, 'anim': 'Level 1 thumbnail', 'coat': coat, 'note': 'First Day Home'})
        out[S + f'thumb_clinic_{coat}.png'] = ([thumb_clinic()], cols, {'section': s, 'anim': 'Level 2 thumbnail', 'coat': coat, 'note': 'Check-up Day'})
    out[S + 'thumb_park.png'] = ([thumb_park()], None, {'section': s, 'anim': 'Level 3 thumbnail', 'note': 'Frosted: coming soon'})
    t = 'Time cards (a jump in time between story beats)'
    out[S + 'timecard_bg.png'] = ([draw_timecard_bg()], None, {'section': 'bg', 'anim': 'time card'})
    notes = {'morning': 'Saturday morning, One morning', 'afternoon': 'Later that afternoon', 'evening': 'That evening',
             'night': 'That night', 'later': 'Two months later, A few months later'}
    for k in TIME_ICONS:
        out[U + f'time_{k}.png'] = ([time_icon(k)], None, {'section': t, 'anim': k, 'note': notes[k]})
    f = 'Spot the difference (Level 2)'
    out[U + 'found_ring.png'] = ([found_ring(44, 38)], None, {'section': f, 'anim': 'found ring', 'note': 'Round a difference in a close-up'})
    out[U + 'found_ring_small.png'] = ([found_ring(20, 18)], None, {'section': f, 'anim': 'found ring (small)', 'note': 'Round a part in the big pictures'})
    out[U + 'icon_magnifier.png'] = ([icon('magnifier')], None, {'section': f, 'anim': 'magnifier', 'note': 'Found counter in the HUD'})
    return out


def hud8(fill_len, name, task_icon, task_label, state='green'):
    """The HUD with the new ? button (the task card moves left to make room)."""
    frame, fills, heart = meter_parts()
    fill = Canvas(62, 6); fill.px = [row[:fill_len] + [None] * (62 - fill_len) for row in fills[state].px]
    ci, bc = panel(18, 18, 'W', ring='E'), button('W', 'E', 'Y')[0]
    return [('@canvas', heart, 8, 8, 2), ('@canvas', frame, 36, 10, 2), ('@canvas', fill, 38, 12, 2),
            ('@text', 172, 9, 120, name, 16, INK, 'left'),
            ('@canvas', nine(ci, 96, 16, 6), 362, 6, 2), ('@canvas', icon(task_icon), 370, 6, 2),
            ('@text', 406, 13, 150, task_label, 14, INK, 'left'),
            ('@canvas', nine(bc, 16, 16, 5), 564, 6, 2), ('@canvas', icon('help'), 564, 6, 2),
            ('@canvas', nine(bc, 16, 16, 5), 604, 6, 2), ('@canvas', icon('pause'), 604, 6, 2)]


def g8_mockups():
    bm, bc = button('M', 'm', 'Y')[0], button('W', 'E', 'Y')[0]
    ci = panel(18, 18, 'W', ring='E')
    card, tag = panel(20, 20, 'W', lip='E'), panel(12, 12, 'Y', lip='y', insets=(2, 1))
    t = lambda x, y, w, s, size, col=INK, al='center': ('@text', x, y, w, s, size, col, al)
    W2 = (640, 360)

    sel = [('@canvas', draw_select_bg(), 0, 0, 2),
           ('@canvas', nine(bc, 40, 15, 5), 12, 10, 2), t(12, 15, 80, 'Back', 15),
           t(0, 13, 640, 'Choose a level', 22),
           ('@canvas', nine(bc, 70, 15, 5), 488, 10, 2), t(488, 15, 140, 'Change dog', 15)]
    cards = [('thumb_home', 'Level 1', 'First Day Home', 'Puppy · 2 tasks', False),
             ('thumb_clinic', 'Level 2', 'Check-up Day', 'Young dog · 2 tasks', False),
             ('thumb_park', 'Level 3', 'Park Day', '', True)]
    for i, (th, t1, t2, t3, locked) in enumerate(cards):
        x, y = 40 + i * 192, 72
        cv = nine(card, 88, 100, 6)
        sel.append(('@canvas', hl(cv) if i == 0 else cv, x - (2 if i == 0 else 0), y - (2 if i == 0 else 0), 2))
        sel.append(('@canvas', thumb_park(), x + 8, y + 8, 2) if locked else (f'assets/screens/{th}_caramel.png', x + 8, y + 8, 2))
        sel.append(('@canvas', pin(), x + 80, y - 6, 2))
        sel += [t(x, y + 128, 176, t1, 18), t(x, y + 150, 176, t2, 15)]
        if locked:
            sel += [('@canvas', icon('lock'), x + 72, y + 48, 2), ('@canvas', nine(tag, 50, 12, 4), x + 38, y + 170, 2),
                    t(x + 38, y + 174, 100, 'Coming soon', 13)]
        else:
            sel.append(t(x, y + 174, 176, t3, 12, '#8a6f66'))

    def room(task_icon, label):
        return [('assets/bg/living_room.png', 0, 0, 2), ('assets/sprites/bowl_empty.png', (SPOTS['bowl'] - 11) * 2, (GROUND_Y - 10) * 2, 2),
                ('assets/ui/icon_treat.png', 576, 180, 2)] + hud8(48, 'Biscuit', task_icon, label)

    dlg = room('pad', 'Potty time  2 of 2') + [
        ('assets/sprites/puppy_caramel_circle.png', 268, 270, 2),
        ('@rect', 0, 0, 640, 360, 'rgba(62,42,36,0.28)'),
        ('@canvas', nine(panel(24, 24, 'W', ring='P', lip='E'), 312, 57, 7), 8, 238, 2),
        ('@canvas', panel(50, 50, 'E', ring='W'), 22, 246, 2), ('assets/sprites/parent_talk.png', 24, 248, 2),
        ('@canvas', nine(panel(12, 12, 'P', lip='p', insets=(2, 1)), 46, 12, 4), 136, 226, 2), t(136, 230, 92, 'Parent', 14),
        t(140, 254, 360, 'Biscuit is sniffing and circling. That means "I need to go!" Drag the treat from the counter to lead them to the pad.', 18, INK, 'left'),
        ('@canvas', nine(bm, 48, 16, 5), 520, 306, 2), t(520, 312, 96, 'OK', 18)]

    hand = hand_frames()[0]
    pts = [((1 - u) ** 2 * 592 + 2 * (1 - u) * u * 330 + u ** 2 * 96, (1 - u) ** 2 * 196 + 2 * (1 - u) * u * 170 + u ** 2 * 300)
           for u in [i / 12 for i in range(13)]]
    hx, hy = pts[7]
    demo = room('pad', 'Potty time  2 of 2') + [
        ('@canvas', draw_prop('pad'), 24, 312, 2), ('assets/sprites/puppy_caramel_circle.png', 268, 270, 2),
        ('@rect', 0, 0, 640, 360, 'rgba(62,42,36,0.45)')]
    demo += [('@canvas', demo_dot(), round(x) - 6, round(y) - 6, 2) for i, (x, y) in enumerate(pts) if i not in (6, 7, 8)]
    demo += [('@canvas', icon('treat'), round(hx) - 16, round(hy) - 22, 2), ('@canvas', hand, round(hx) - HAND_TIP[0] * 2, round(hy) - HAND_TIP[1] * 2 - 4, 2),
             ('@canvas', nine(ci, 216, 22, 6), 104, 52, 2), ('@canvas', icon('bulb'), 114, 58, 2),
             t(152, 66, 360, 'Drag the treat. Biscuit follows it to the pad.', 16, INK, 'left'),
             ('@canvas', nine(bm, 56, 16, 5), 440, 296, 2), t(440, 302, 112, 'Got it!', 17)]

    kib = draw_food_big('kibble')
    hover = [('assets/bg/counter_closeup.png', 0, 0, 2),
             ('@canvas', hl(kib), (COUNTER_SLOTS[0] - 24) * 2 - 2, (COUNTER_TOP_Y - 48) * 2 - 2, 2),
             ('assets/sprites/foodbig_chocolate.png', (COUNTER_SLOTS[1] - 24) * 2, (COUNTER_TOP_Y - 48) * 2, 2)] + hud8(40, 'Biscuit', 'bowl', 'Snack time  1 of 2') + [
             ('@canvas', nine(ci, 64, 13, 6), (COUNTER_SLOTS[0] - 32) * 2, 290, 2), t((COUNTER_SLOTS[0] - 32) * 2, 296, 128, 'Puppy kibble', 14),
             ('@canvas', nine(ci, 64, 13, 6), (COUNTER_SLOTS[1] - 32) * 2, 290, 2), t((COUNTER_SLOTS[1] - 32) * 2, 296, 128, 'Chocolate bar', 14),
             ('@canvas', paw_cursor(), 232, 196, 1)]

    tc = [('@canvas', draw_timecard_bg(), 0, 0, 2), ('@canvas', time_icon('afternoon'), 288, 82, 2),
          t(0, 166, 640, 'Later that afternoon', 26), t(560, 6, 72, 'Skip', 13, INK, 'right'),
          t(400, 336, 214, 'click to continue', 11, '#8a6f66', 'right')]
    return [('Level select (all built levels open; the hovered card has the highlight)', W2, sel),
            ('Blocking dialogue: the scene is dimmed and nothing can be tapped until OK', W2, dlg),
            ('Demo: the ghost hand drags the treat along a dotted path (first time, or the ? button)', W2, demo),
            ('Hover highlight replaces the rings: a butter outline round whatever is under the pointer', W2, hover),
            ('Time card between story beats', W2, tc)]


ICONS8['bath'] = lambda c: (c.rect(2, 8, 12, 5, 'W'), c.rect(2, 11, 12, 2, 'E'), c.rect(3, 13, 2, 2, 'Y'), c.rect(11, 13, 2, 2, 'Y'),
                            c.ellipse(5, 6, 2, 2, 'S'), c.ellipse(9, 4, 2.5, 2.5, 'S'), c.put(9, 3, 'w'), c.ellipse(12, 6, 1.5, 1.5, 'S'))


# ---------------------------------------------------------------- group 11: Level 3 (the walk, the park, fetch, a new friend), the finale, extras
FONT3x5['K'] = ['101', '101', '110', '101', '101']
FONT3x5['N'] = ['101', '111', '111', '111', '101']
FONT5x7['K'] = ['10001', '10010', '10100', '11000', '10100', '10010', '10001']


def adult_anims_l3():
    """The adult dog's park poses (idle and wag are in group 6)."""
    D = lambda **kw: draw_dog(ADULT, **kw)
    step = lambda **kw: [D(legs=(1, -1, -1, 1), lift=(0, 1, 1, 0), **kw), D(body_dy=-1, **kw),
                         D(legs=(-1, 1, 1, -1), lift=(1, 0, 0, 1), **kw), D(body_dy=-1, **kw)]
    gallop = lambda **kw: [D(legs=(3, -2, 3, -2), lift=(2, 0, 0, 3), tail=70, head=(1, 0), body_dy=-1, **kw),
                           D(lift=(1, 1, 1, 1), tail=80, head=(1, -1), body_dy=-2, **kw),
                           D(legs=(-2, 3, -2, 3), lift=(0, 3, 2, 0), tail=70, head=(1, 0), body_dy=-1, **kw),
                           D(tail=75, head=(1, 0), **kw)]
    stress = dict(body_dy=2, tuck=True, ear=(-2, 2))
    return {
        'walk': step(tail=45), 'run': gallop(), 'carry': step(tail=60, ball=True),
        'tired': step(tail=15, mouth='pant', head=(0, 2)),                                   # slow, head low, panting
        'pant': [D(tail=15, mouth='pant', eyes='squint', body_dy=1, head=(0, 2)), D(tail=15, mouth='pant', eyes='closed', body_dy=2, head=(0, 2))],
        'flop': [D(pose='lie', head=(1, 8), tail=-15, eyes='closed', mouth='pant', ear=(0, 2)),
                 D(pose='lie', head=(1, 8), tail=-15, eyes='squint', mouth='pant', ear=(0, 2))],
        'rest': [D(pose='lie', head=(1, 8), tail=-5, eyes='closed', ear=(0, 2)), D(pose='lie', head=(1, 8), tail=5, eyes='closed', ear=(0, 2))],
        'drink': [D(head=(3, 9), tail=60, eyes='closed', mouth='eat'), D(head=(3, 10), tail=75, eyes='closed')],
        'sit': [D(pose='sit', tail=15), D(pose='sit', tail=25, eyes='closed')],
        'lunge': [D(legs=(2, 2, 4, 4), lift=(0, 0, 2, 3), head=(3, -2), tail=70, mouth='open', ear=(1, -1)),
                  D(legs=(2, 2, 4, 4), lift=(0, 0, 3, 2), head=(3, -1), tail=85, mouth='open', ear=(1, -1))],
        'sniff': [D(head=(2, 7), tail=30, ear=(0, 1)), D(head=(2, 8), tail=35, ear=(0, 1))],
        'nervous': [D(head=(-1, 3), eyes='sad', **stress), D(head=(-2, 3), eyes='sad', **stress)],
        'stress': [D(head=(-1, 2), eyes='whale', **stress), D(head=(-1, 2), eyes='whale', mouth='lick', **stress),
                   D(head=(-1, 2), eyes='whale', **stress), D(head=(-1, 1), eyes='closed', mouth='yawn', **stress)],
        'duck': [D(head=(-3, 4), eyes='squint', tail=10, ear=(-2, 2), body_dy=2), D(head=(-3, 5), eyes='squint', tail=5, ear=(-2, 2), body_dy=2)],
        'sad': [D(pose='lie', head=(1, 8), tail=-15, eyes='sad', ear=(0, 2)), D(pose='lie', head=(1, 8), tail=-15, eyes='closed', ear=(0, 2))],
    }


# ---- the walk to the park (a 960-wide street that scrolls; the kid holds the leash)
KID_H = 62                                                                    # kid sprites are cropped so the feet sit on the bottom
WALK = dict(w=960, ground=158, kid_x=56, hand=(35, -29), collar=(3, -25), slack=26, tight=38, gate=868,
            distractions=(('squirrel', 330, 140), ('sandwich', 560, 161), ('cat', 752, 105)))   # mirrored in LEVEL3.walk


def kid_walk_frames():
    return [crop(kid('leash', s), 0, 0, 40, KID_H) for s in range(4)]


def leash(tight):
    n = WALK['tight' if tight else 'slack']
    c = Canvas(n + 1, 12)
    for x in range(n + 1):
        t = x / n
        y = round(4 * t + (0 if tight else 6 * math.sin(math.pi * t)))
        c.put(x, y, 'R'); c.put(x, y + 1, 'r')
    return c


def tree(c, x, base, h=34, r=16):
    c.rect(x - 2, base - h, 5, h, 'd'); c.rect(x - 2, base - h, 1, h, 'K'); c.rect(x + 2, base - h, 1, h, 'K')
    blob(c, x, base - h - r // 2, r, r * 0.85, 'm', 'K', shade='G', light='M')


def lamp(c, x, base):
    c.rect(x, base - 52, 2, 52, 'K'); box(c, x - 3, base - 60, 8, 8, 'Y'); c.rect(x - 4, base - 61, 10, 2, 'K')
    c.rect(x - 2, base, 6, 2, 'K')


def picket(c, x0, x1, top, base):
    c.rect(x0, top + 5, x1 - x0, 4, 'K'); c.rect(x0, top + 6, x1 - x0, 2, 'W')
    c.rect(x0, top + 13, x1 - x0, 4, 'K'); c.rect(x0, top + 14, x1 - x0, 2, 'W')
    for x in range(x0, x1, 6):
        c.rect(x - 1, top, 6, base - top, 'K'); c.rect(x, top + 1, 4, base - top - 1, 'W')
        c.put(x - 1, top, None); c.put(x + 4, top, None)


def draw_street():
    """The walk: houses, gardens and a pavement, ending at the park gate. 960 wide; the game slides it left."""
    W_ = WALK['w']
    c = Canvas(W_, 180)
    c.rect(0, 0, W_, 132, 'S')
    for x, y in ((40, 20), (200, 30), (390, 16), (540, 34), (700, 22), (860, 28)):
        c.ellipse(x, y, 16, 5, 'W'); c.ellipse(x + 9, y - 3, 9, 5, 'W'); c.ellipse(x - 10, y + 1, 8, 4, 'W')
    walls, roofs = ('P', 'Y', 'M', 'L', 'E'), ('R', 'd', 'G', 'V', 'o')
    for i, x in enumerate(range(10, 760, 140)):
        house(c, x, 64, 44, 112, walls[i % 5], roofs[i % 5], ('d', 'R', 'S', 'D', 'G')[i % 5])
        tree(c, x + 104, 112, 30, 14)
    c.rect(0, 112, W_, 20, 'M')                                                   # front gardens
    for x in range(4, W_, 9):
        c.put(x, 116 + (x * 7) % 9, 'G'); c.put(x + 3, 122 + (x * 5) % 7, 'm')
    for x in range(14, 760, 140):
        picket(c, x, x + 100, 104, 132)
        for fx in range(x + 4, x + 96, 12):
            c.pattern(fx, 124, ['.R.', 'RYR', '.R.'] if (fx // 12) % 2 else ['.L.', 'LYL', '.L.'])
    c.rect(0, 132, W_, 8, 'm'); c.rect(0, 132, W_, 1, 'G')                      # grass verge
    c.rect(0, 140, W_, 26, 'W'); c.rect(0, 140, W_, 1, 'K')                       # pavement
    for x in range(0, W_, 24):
        c.rect(x, 141, 1, 25, 'E')
    c.rect(0, 153, W_, 1, 'E')
    c.rect(0, 166, W_, 3, 'P'); c.rect(0, 166, W_, 1, 'K'); c.rect(0, 168, W_, 1, 'p')   # kerb
    c.rect(0, 169, W_, 11, 'l')                                                   # road
    for x in range(8, W_, 32):
        c.rect(x, 175, 14, 2, 'W')
    for x in range(120, 760, 200):
        lamp(c, x, 140)
    # the park: hedge, gate pillars and an arch with the sign
    gx = WALK['gate']
    c.rect(gx - 60, 96, W_ - gx + 60, 36, 'm')
    for x in range(gx - 60, W_, 10):
        blob(c, x + 5, 98, 7, 6, 'm', 'K', shade='G', light='M')
    tree(c, gx - 30, 112, 44, 22)
    tree(c, gx + 120, 112, 40, 20)
    for px_ in (gx, gx + 70):
        box(c, px_, 72, 14, 68, 'R'); c.rect(px_ + 1, 73, 12, 3, 'N')
        for y in range(80, 138, 6):
            c.rect(px_ + 1, y, 12, 1, 'r')
        box(c, px_ - 2, 68, 18, 6, 'E')
    c.rect(gx + 14, 132, 56, 8, 'T'); c.rect(gx + 14, 132, 56, 1, 't')           # the path into the park
    for i in range(56):
        y = round(66 - 8 * math.sin(math.pi * i / 55))
        c.rect(gx + 14 + i, y, 1, 2, 'K')
    box(c, gx + 20, 44, 44, 14, 'Y'); big_text(c, gx + 23, 47, 'PARK', 'K', 1)
    c.rect(gx + 41, 58, 2, 3, 'K')
    return c


def squirrel_frames():
    """Sitting up with a nut, then flicking its big tail."""
    out = []
    for flick in (0, 1):
        c = Canvas(20, 18)
        for i, (x, y) in enumerate(((5, 15), (3, 12), (2, 9), (3, 6), (5, 4))):            # the bushy tail
            c.ellipse(x + flick * (i // 3), y - flick, 3, 3, 'o' if i % 2 else 'O')
        c.ellipse(11, 12, 4, 5, 'O', shade='o'); c.ellipse(14, 7, 3.5, 3, 'O'); c.rect(13, 3, 2, 2, 'O')
        c.put(15, 6, 'k'); c.put(17, 8, 'k'); c.rect(11, 13, 3, 2, 'W')
        c.rect(15, 10, 3, 3, 'd'); c.put(16, 10, 'D')                                       # the nut
        c.rect(9, 16, 3, 1, 'o'); c.rect(13, 16, 3, 1, 'o')
        out.append(c.outline())
    return out


def sandwich():
    c = Canvas(20, 10)
    c.rect(1, 6, 18, 3, 'T'); c.rect(1, 5, 18, 1, 'M'); c.rect(2, 4, 16, 1, 'R'); c.rect(1, 2, 18, 2, 'T')
    c.rect(2, 1, 16, 1, 't'); c.pattern(4, 4, ['Y...Y...Y.'])
    return c.outline()


def cat_frames():
    """A cat on the fence, its tail swishing."""
    out = []
    for swish in (0, 1):
        c = Canvas(22, 18)
        c.ellipse(9, 11, 6, 5, 'H', shade='h'); c.ellipse(15, 6, 4, 3.6, 'H')
        c.pattern(12, 1, ['H...H', 'HH.HH']); c.put(16, 5, 'Y'); c.put(18, 5, 'Y'); c.put(17, 7, 'N')
        for i in range(6):
            c.rect(3 - (i // 2 if swish else 0), 12 + (i // 2 if swish else i), 2, 2, 'H')
        c.rect(8, 15, 2, 2, 'W'); c.rect(12, 15, 2, 2, 'W')
        out.append(c.outline())
    return out


# ---- the park
PARK = dict(ground=152, kid_x=80, dog_x=124, ball=(146, 150), shade=(4, 138, 84, 24), rest_x=44, bowl=(262, 153),
            land=(168, 262), sam_x=200)                                           # mirrored in LEVEL3.park


def draw_park():
    c = Canvas(320, 180)
    c.rect(0, 0, 320, 100, 'S')
    for y in range(0, 40, 5):
        c.rect(0, y, 320, 1, 'S' if y % 10 else 's')
    for x, y in ((60, 26), (170, 16), (230, 36)):
        c.ellipse(x, y, 15, 5, 'W'); c.ellipse(x + 8, y - 3, 8, 5, 'W')
    for x in range(-10, 330, 26):                                                 # far trees
        blob(c, x, 88, 15, 12, 'G', 'K', light='m')
    c.rect(0, 96, 320, 84, 'm'); c.rect(0, 96, 320, 1, 'G')
    for x in range(3, 320, 7):
        c.put(x, 104 + (x * 13) % 56, 'G'); c.put(x + 2, 100 + (x * 7) % 60, 'M')
    for x, y, col in ((120, 120, 'R'), (200, 114, 'Y'), (236, 130, 'L'), (100, 108, 'Y'), (300, 112, 'R'), (176, 126, 'L')):
        c.pattern(x, y, ['.' + col + '.', col + 'Y' + col, '.' + col + '.'])
    box(c, 140, 102, 40, 4, 'D'); box(c, 140, 94, 40, 4, 'D'); c.rect(144, 106, 2, 6, 'K'); c.rect(174, 106, 2, 6, 'K')   # bench
    c.rect(0, 160, 320, 20, 'T'); c.rect(0, 160, 320, 1, 't')                      # the path
    for x in range(6, 320, 15):
        c.rect(x, 166 + x % 9, 3, 1, 't')
    c.ellipse(292, 44, 9, 9, 'Y', shade='y')                                      # the sun (below the HUD)
    for a in range(0, 360, 45):
        c.rect(round(292 + 14 * math.cos(math.radians(a))) - 1, round(44 + 14 * math.sin(math.radians(a))) - 1, 3, 3, 'Y')
    return c


def park_tree():
    c = Canvas(96, 122)
    c.rect(40, 50, 12, 70, 'd'); c.rect(43, 50, 3, 70, 'D'); c.rect(36, 114, 20, 6, 'd')
    for x, y, r in ((26, 40, 22), (66, 40, 22), (46, 24, 24), (20, 58, 14), (74, 60, 14), (46, 54, 20)):
        c.ellipse(x, y, r, r * 0.8, 'm', shade='G', light='M')
    for x, y in ((30, 30), (60, 22), (70, 46), (24, 52), (50, 40)):
        c.pattern(x, y, ['.G.', 'G.G'])
    return c.outline()


def park_shade():
    x, y, w, h = PARK['shade']
    c = Canvas(w, h)
    c.ellipse(w / 2, h / 2, w / 2, h / 2, 'G')
    for yy in range(h):
        for xx in range(w):
            if c.px[yy][xx] and (xx + yy) % 5 == 0:
                c.px[yy][xx] = 'm'
    return c


def fountain():
    c = Canvas(44, 52)
    box(c, 4, 34, 36, 16, 'E'); c.rect(5, 46, 34, 3, 'W'); c.rect(5, 35, 34, 1, 'w')
    c.ellipse(22, 36, 16, 3, 'S'); c.ellipse(22, 36, 11, 1.6, 's')
    box(c, 18, 16, 8, 20, 'E'); box(c, 12, 12, 20, 6, 'E')
    for x, y in ((22, 2), (18, 5), (26, 5), (15, 9), (29, 9)):
        c.rect(x - 1, y, 2, 4, 'S'); c.put(x, y, 'w')
    return c.outline()


def water_bowl(full):
    c = Canvas(22, 12)
    c.ellipse(11, 4, 9, 2.6, 'K'); c.rect(3, 4, 16, 6, 'S'); c.rect(4, 8, 14, 2, 's'); c.rect(2, 3, 18, 1, 'W')
    c.ellipse(11, 4, 7, 1.6, 'S' if full else 's')
    if full:
        c.put(8, 4, 'w'); c.put(13, 4, 'w')
    return c.outline()


def tennis_ball():
    c = Canvas(8, 8)
    c.ellipse(4, 4, 3, 3, 'Y', shade='y'); c.pattern(2, 2, ['M..', '.MM', '...']); c.put(3, 2, 'w')
    return c.outline()


def ball_shadow():
    c = Canvas(8, 3)
    c.ellipse(4, 1.5, 3.5, 1.2, 'G')
    return c


# ---- Sam, the child who wants to say hello (40x62, faces right; flipped in game to face the dog)
def sam(pose='stand', step=0):
    c = Canvas(40, 64)
    o = 4
    skin, shade, hair, shirt, sshade = 'd', 't', 'k', 'O', 'o'
    c.ellipse(9, 9 + o, 5, 5, hair); c.ellipse(21, 7 + o, 5, 5, hair)            # two puffs
    c.ellipse(15, 13 + o, 8, 8, skin)
    c.ellipse(15, 7 + o, 8, 4, hair); c.rect(8, 8 + o, 3, 6, hair)
    c.rect(10, 13 + o, 2, 3, shade); c.put(23, 15 + o, shade)
    if pose in ('run', 'wave'):
        c.pattern(18, 13 + o, ['.kk.', 'k..k']); c.pattern(18, 18 + o, ['kkk', 'kNk', '.k.'])
    else:
        c.rect(19, 12 + o, 2, 3, 'k'); c.put(20, 12 + o, 'w'); c.pattern(19, 18 + o, ['k.k', '.k.'])
    c.rect(19, 17 + o, 2, 1, 'N')
    c.rect(13, 21 + o, 4, 3, shade)
    c.ellipse(15, 27 + o, 9, 4, shirt); c.rect(6, 27 + o, 18, 14, shirt); c.rect(6, 38 + o, 18, 3, sshade)
    c.pattern(11, 31 + o, ['.W.W.', 'WWWWW', '.WWW.', '..W..'])                    # a heart on the T-shirt
    def back(dx=0):
        c.rect(3, 27 + o, 4, 4, shirt); c.rect(3 + dx, 31 + o, 4, 11, skin)
    if pose == 'run':
        back(-1 if step else 1)
        c.rect(23, 27 + o, 4, 4, shirt); c.rect(24 + (2 if step else -1), 31 + o, 4, 9, skin)
    elif pose == 'hand':                                                         # a hand held out low, for a sniff
        back(); c.rect(23, 27 + o, 4, 6, shirt); c.rect(25, 33 + o, 9, 4, skin); c.rect(33, 32 + o, 3, 3, skin)
    elif pose == 'pet':                                                          # reaching forward and down to the chest
        back(); c.rect(23, 27 + o, 5, 4, shirt); c.rect(27, 30 + o, 4, 4, skin); c.rect(30, 33 + o, 4, 4, skin); c.rect(33, 36 + o, 4, 3, skin)
    elif pose == 'wave':
        back(); c.rect(23, 9 + o, 4, 20, shirt); c.rect(23, 4 + o, 4, 5, skin)
    else:
        back(); c.rect(23, 27 + o, 4, 4, shirt); c.rect(23, 31 + o, 4, 11, skin)
    f, b = (3, -3) if (pose in ('run', 'walk') and step) else (0, 0)
    c.rect(8, 41 + o, 14, 3, 'G'); c.rect(8 + b, 44 + o, 6, 6, 'G'); c.rect(16 + f, 44 + o, 6, 6, 'G')
    c.rect(9 + b, 50 + o, 4, 4, skin); c.rect(17 + f, 50 + o, 4, 4, skin)
    c.rect(7 + b, 54 + o, 8, 3, 'W'); c.rect(16 + f, 54 + o, 9, 3, 'W'); c.rect(7 + b, 56 + o, 8, 1, 'S'); c.rect(16 + f, 56 + o, 9, 1, 'S')
    return crop(c.outline(), 0, 0, 40, KID_H)


SAM_POSES = {'run': 2, 'walk': 2, 'stand': 1, 'hand': 1, 'pet': 1, 'wave': 1}


def sam_frames():
    return {p: [sam(p, s) for s in range(n)] for p, n in SAM_POSES.items()}


def draw_sam_bust(mouth='closed', blink=False):
    """Sam's portrait for the dialogue box, framed like the parent's (48x48)."""
    c = Canvas(48, 48)
    c.ellipse(24, 47, 17, 10, 'O', shade='o'); c.pattern(21, 40, ['.W.W.', 'WWWWW', '.WWW.']); c.rect(21, 30, 6, 7, 't')
    c.ellipse(12, 12, 7, 7, 'k'); c.ellipse(36, 12, 7, 7, 'k')
    c.ellipse(24, 21, 10, 11, 'd')
    c.ellipse(24, 13, 11, 6, 'k'); c.rect(14, 13, 3, 8, 'k'); c.rect(31, 13, 3, 8, 'k')
    if blink:
        c.rect(19, 21, 3, 1, 'k'); c.rect(27, 21, 3, 1, 'k')
    else:
        c.rect(19, 20, 2, 3, 'k'); c.put(20, 20, 'w'); c.rect(28, 20, 2, 3, 'k'); c.put(29, 20, 'w')
    c.rect(17, 25, 2, 1, 'N'); c.rect(30, 25, 2, 1, 'N')
    c.pattern(22, 26, ['kkkk', 'kNNk', '.kk.'] if mouth == 'open' else ['k..k', '.kk.'])
    c.put(24, 24, 't')
    return c.outline()


def sam_bust_frames():
    return {'talk': [draw_sam_bust('closed'), draw_sam_bust('open'), draw_sam_bust('closed'), draw_sam_bust('open')],
            'idle': [draw_sam_bust(), draw_sam_bust(), draw_sam_bust(blink=True), draw_sam_bust()]}


def sam_hand():
    """Sam's hand, dragged onto the dog to choose where to pet."""
    c = Canvas(14, 10)
    c.rect(1, 3, 9, 5, 'd'); c.rect(9, 2, 4, 2, 'd'); c.rect(9, 4, 4, 1, 'd'); c.rect(9, 5, 4, 1, 'd'); c.rect(9, 6, 3, 1, 'd')
    c.rect(2, 3, 2, 1, 't'); c.put(9, 4, 't'); c.put(9, 6, 't')
    return c.outline()


# ---- where Sam can pet the adult dog: the top of the head vs the side of the neck and chest
def _adult_region(part, x, y):
    return {'head': lambda: y <= 15 and 26 <= x <= 44, 'chest': lambda: 22 <= x <= 37 and 21 <= y <= 36}[part]()


def adult_part(part, ring_it):
    base = adult_anims()['idle'][0]
    m = Canvas(48, 48)
    for y in range(48):
        for x in range(48):
            if base.px[y][x] and _adult_region(part, x, y):
                m.px[y][x] = 'W'
    if not ring_it:
        return m
    c = Canvas(48, 48)
    nb = ((1, 0), (-1, 0), (0, 1), (0, -1))
    for y in range(48):
        for x in range(48):
            if m.px[y][x] is None and any(m.get(x + dx, y + dy) for dx, dy in nb):
                c.px[y][x] = 'w'
    for y in range(48):
        for x in range(48):
            if m.px[y][x] is None and c.px[y][x] is None and any(c.get(x + dx, y + dy) == 'w' for dx, dy in nb):
                c.px[y][x] = 'Y'
    return c


# ---- icons for Level 3 (choices, thought bubbles, task cards, album)
def _rays(c, cx, cy, r):
    for a in range(0, 360, 60):
        c.rect(round(cx + r * math.cos(math.radians(a))) - 1, round(cy + r * math.sin(math.radians(a))) - 1, 2, 2, 'Y')


ICONS11 = {
    'ball':  lambda c: (c.ellipse(8, 8, 6, 6, 'Y', shade='y'), c.pattern(3, 4, ['M.....', '.MM...', '...MMM', '......', '......', 'MMM...']),
                        c.rect(5, 4, 2, 1, 'w')),
    'hot':   lambda c: (_rays(c, 7, 7, 7), c.ellipse(7, 7, 4.5, 4.5, 'Y', shade='y'), c.pattern(11, 8, ['.S.', '.S.', 'SSS', 'SwS', '.S.'])),
    'leash': lambda c: (c.ellipse(5, 5, 4, 4, 'R'), [c.rect(8 + i, 8 + i, 2, 2, 'R') for i in range(6)], c.rect(13, 12, 3, 3, 'Y')),
    'park':  lambda c: (c.rect(7, 9, 3, 6, 'd'), c.ellipse(8, 6, 6, 5, 'm', shade='G', light='M')),
    'water': lambda c: (c.ellipse(8, 9, 6, 1.6, 'S'), c.rect(3, 10, 11, 4, 'S'), c.rect(4, 13, 9, 1, 's'), c.rect(2, 9, 13, 1, 'W'),
                        c.pattern(7, 1, ['.S.', 'SSS', 'SwS', '.S.'])),
    'stop':  lambda c: c.pattern(3, 1, ['..F.F.F...', '..F.F.F.F.', '..F.F.F.F.', '..FFFFFFF.', 'F.FFFFFFF.', 'FFFFFFFFF.',
                                         '.FFFFFFFF.', '.FFFFFFFF.', '..FFFFFF..', '..FFFFFF..', '...FFFF...', '...ffff...']),
    'run':   lambda c: (c.pattern(1, 4, ['WWW...', '......', 'WWWW..', '......', '.WWW..']),
                        c.pattern(6, 5, ['...RRR..', '..RRRRR.', 'RRRRRRRR', 'RRRRRRRR', 'WWWWWWWW'])),
    'sniff': lambda c: (c.ellipse(10, 9, 4, 3, 'k'), c.put(9, 8, 'w'), c.put(8, 10, 'K'), c.put(11, 10, 'K'),
                        c.pattern(1, 4, ['W.....', '.W....', '......', 'W.W...', '......', '.W....', 'W.....'])),
    'space': lambda c: (c.pattern(0, 5, ['..W..........W..', '.WW..........WW.', 'WWWWW......WWWWW', '.WW..........WW.',
                                         '..W..........W..']), c.rect(7, 4, 2, 7, 'R')),
    'pet':   lambda c: (c.pattern(1, 7, ['...dddddd.....', '..dddddddddd..', '.ddddddddddddd', '.dddddddd.....', '..dddddd......']),
                        c.pattern(9, 1, ['RR.RR', 'RRRRR', '.RRR.', '..R..'])),
}


def icon11(name):
    c = Canvas(16, 16)
    ICONS11[name](c)
    if name == 'leash':                                                          # the handle's loop is open
        c.ellipse(5, 5, 2, 2, 'W')
        for y in range(16):
            for x in range(16):
                if c.px[y][x] == 'W':
                    c.px[y][x] = None
        c.outline()
        c.ellipse(5, 5, 1.2, 1.2, 'K')
        for y in range(16):
            for x in range(16):
                if c.px[y][x] == 'K' and ((x + 0.5 - 5) ** 2 + (y + 0.5 - 5) ** 2) < 2:
                    c.px[y][x] = None
        return c
    return c.outline()


# ---- Level 3 story panels (x 3 coats; the visible band is y 15..146)
def draw_panel_leash():
    """One sunny morning: the grown-up dog waits by the front door with its leash in its mouth."""
    c = Canvas(320, 180)
    wall_and_floor(c, 128)
    box(c, 196, 30, 60, 98, 'W'); box(c, 200, 34, 52, 94, 'R'); c.rect(201, 35, 50, 1, 'N')       # the front door
    box(c, 208, 42, 36, 22, 'S'); c.rect(226, 42, 1, 22, 'K'); c.rect(244, 84, 4, 4, 'Y')
    for x in range(172, 196, 6):                                                    # coat hooks + a hat
        c.rect(x, 50, 2, 4, 'd')
    blob(c, 180, 60, 8, 5, 'M', 'K'); c.rect(172, 62, 18, 2, 'M')
    box(c, 262, 108, 40, 20, 'D'); c.rect(263, 112, 38, 1, 'd')                     # shoe bench
    paste(c, adult_anims_l3()['sit'][0], 132, 128 - 48)
    for x, y in ((170, 102), (171, 105), (172, 108), (172, 111), (171, 114), (169, 117), (166, 119)):   # the leash hanging from its mouth
        c.rect(x, y, 2, 3, 'R')
    c.ellipse(164, 122, 4, 2.5, 'R'); c.ellipse(164, 122, 2, 1, 'W')
    for x, y in ((128, 92), (184, 84)):
        c.pattern(x, y, ['..Y..', '.YwY.', '..Y..'])
    paste(c, kid('stand'), 66, 128 - 61)
    paste(c, parent_body(), 22, 128 - PARENT_H)
    return c


def draw_panel_park_gate():
    """At the park gate: green grass, the sun out, the dog wagging at the end of a loose leash."""
    c = shift_up(crop(draw_street(), WALK['w'] - 320, 0, 320, 180), 14)
    kx, g = 40, WALK['ground'] - 14
    paste(c, crop(kid('leash', 0), 0, 0, 40, KID_H), kx, g - KID_H)
    paste(c, leash(False), kx + WALK['hand'][0], g + WALK['hand'][1])
    paste(c, adult_anims()['wag'][1], kx + WALK['hand'][0] + WALK['slack'] - WALK['collar'][0] - 24, g - 48)
    return c


def draw_panel_evening_home():
    """That evening: the tired, happy dog asleep on the rug; the kid on the sofa with the photo album."""
    c = draw_room()
    for y in range(37, 79):                                                         # an orange evening sky in the window
        for x in range(79, 129):
            if c.px[y][x] in ('S', 'W'):
                c.px[y][x] = 'O' if y < 58 else 'V'
    for y in range(52, 94):
        for x in range(16, 52):
            if c.px[y][x] == 'S':
                c.px[y][x] = 'O' if y < 72 else 'V'
    for y in range(0, 135):                                                         # warm lamplight dims the wall
        for x in range(320):
            if c.px[y][x] == 'W' and (x + y) % 2 == 0:
                c.px[y][x] = 'E'
    box(c, 112, 100, 6, 34, 'D'); box(c, 104, 86, 22, 16, 'Y'); c.rect(105, 98, 20, 3, 'y')   # a lamp by the sofa
    paste(c, adult_anims_l3()['rest'][0], 146, 166 - 48)
    pixel_text(c, 192, 132, 'Z', 'l'); pixel_text(c, 197, 126, 'Z', 'l')
    paste(c, kid('sit').flipped(), 152, 128 - 59)
    box(c, 146, 94, 18, 12, 'R'); c.rect(154, 94, 1, 12, 'r'); c.rect(147, 96, 6, 8, 'W'); c.rect(156, 96, 6, 8, 'W')   # the album
    return shift_up(c, 26)


L3_PANELS = {'leash': draw_panel_leash, 'park_gate': draw_panel_park_gate, 'evening_home': draw_panel_evening_home}
L3_LINES = {
    'leash': ('parent', "{name} is all grown up and full of energy. Let's walk to the park!"),
    'park_gate': ('parent', 'Here we are! Lots of room to run. Who wants to play fetch?'),
    'evening_home': ('parent', "What a day! {name} is all grown up, and so are you. You're a Pawfect Parent!"),
}


# ---- the finale (an album spread with a photo from each level) and the level-select park card, now open
def draw_finale_bg():
    c = Canvas(320, 180)
    c.rect(0, 0, 320, 180, 'D')
    for y in range(0, 180, 9):
        c.rect(0, y, 320, 1, 'd')
    box(c, 14, 22, 292, 150, 'W'); c.rect(159, 23, 2, 148, 'E'); c.rect(15, 165, 290, 6, 'E')
    for x0 in (18, 164):
        for y in range(38, 160, 10):
            c.rect(x0 + 4, y, 130, 1, 'E')
    for i, x in enumerate((30, 122, 214)):
        box(c, x, 54, 76, 86, 'W'); box(c, x + 6, 60, 64, 56, ('S', 'M', 'Y')[i]); c.rect(x + 7, 100, 62, 15, ('D', 'W', 'm')[i])
        for cx, cy in ((x, 54), (x + 70, 54), (x, 134), (x + 70, 134)):               # photo corners
            box(c, cx - 1, cy - 1, 8, 8, 'R')
    box(c, 54, 2, 212, 26, 'P'); c.rect(55, 24, 210, 3, 'p'); c.rect(55, 3, 210, 1, 'W')       # the banner (words in game)
    for x, y in ((24, 148), (292, 40), (300, 150), (118, 148), (206, 150)):
        c.pattern(x, y, ['.R.R.', 'RRRRR', '.RRR.', '..R..'])
    return c


def thumb_park_open():
    c = Canvas(80, 56)
    c.rect(0, 0, 80, 56, 'S')
    blob(c, 66, 10, 5, 5, 'Y', 'y'); c.ellipse(36, 9, 7, 2.5, 'W'); c.ellipse(41, 7, 4, 2.5, 'W')
    c.ellipse(60, 44, 34, 12, 'M'); c.rect(0, 40, 80, 16, 'm')
    for x in range(2, 80, 5):
        c.put(x, 42 + (x * 3) % 5, 'G')
    c.ellipse(40, 52, 26, 3, 'T')
    box(c, 8, 20, 4, 22, 'd'); blob(c, 10, 16, 9, 8, 'm', 'G', light='M')
    paste(c, adult_anims()['wag'][1], 26, 6)
    paste(c, tennis_ball(), 64, 44)
    return _frame(c)


def hover_frame():
    """Nine-slice hover highlight for places that are not sprites (the counter, a spot on the floor, the shade): butter outside, white in."""
    c = Canvas(10, 10)
    for y in range(10):
        for x in range(10):
            out_ = x in (0, 9) or y in (0, 9)
            in_ = x in (1, 8) or y in (1, 8)
            if out_ and not (x in (0, 9) and y in (0, 9)):
                c.px[y][x] = 'Y'
            elif in_ and not out_:
                c.px[y][x] = 'Y' if (x in (1, 8) and y in (1, 8)) else 'w'
    return c


def group11():
    out, S_, U, B, SC = {}, 'assets/sprites/', 'assets/ui/', 'assets/bg/', 'assets/screens/'
    a = 'The adult dog at the park'
    anims = adult_anims_l3()
    notes = {'walk': 'On the leash', 'run': 'Chasing the ball', 'carry': 'Bringing the ball back', 'tired': 'Slowing down, panting (a sign!)',
             'pant': 'Hot and tired: tongue out', 'flop': 'Too hot: flops down and will not move', 'rest': 'Resting in the shade',
             'drink': 'Drinking water', 'sit': 'Stopped and calm on the walk', 'lunge': 'Pulling at a squirrel',
             'sniff': 'Sniffing a new friend', 'nervous': 'Ears back, tail tucked: someone ran at them',
             'stress': 'Stress signals: whale eye, lip lick, yawn, tucked tail', 'duck': 'Ducks away from a hand over the head',
             'sad': 'Retry screen'}
    for coat, cols in COATS.items():
        for name, frames in anims.items():
            out[S_ + f'adult_{coat}_{name}.png'] = (frames, cols, {'section': a, 'anim': name, 'coat': coat, 'note': notes[name]})
    w = 'The walk to the park'
    out[B + 'street.png'] = ([draw_street()], None, {'section': 'bg', 'anim': 'street'})
    out[S_ + 'kid_walk.png'] = (kid_walk_frames(), None, {'section': w, 'anim': 'kid walking', 'note': 'Holding the leash'})
    out[S_ + 'leash_slack.png'] = ([leash(False)], None, {'section': w, 'anim': 'leash: loose', 'note': 'Walking nicely'})
    out[S_ + 'leash_tight.png'] = ([leash(True)], None, {'section': w, 'anim': 'leash: tight', 'note': 'The dog is pulling'})
    out[S_ + 'squirrel.png'] = (squirrel_frames(), None, {'section': w, 'anim': 'squirrel', 'note': 'Distraction 1'})
    out[S_ + 'sandwich.png'] = ([sandwich()], None, {'section': w, 'anim': 'dropped sandwich', 'note': 'Distraction 2'})
    out[S_ + 'cat.png'] = (cat_frames(), None, {'section': w, 'anim': 'cat on the fence', 'note': 'Distraction 3'})
    p = 'The park: fetch, rest and water'
    out[B + 'park.png'] = ([draw_park()], None, {'section': 'bg', 'anim': 'park'})
    out[S_ + 'park_tree.png'] = ([park_tree()], None, {'section': p, 'anim': 'shady tree', 'note': 'Tap it (or its shade) to rest'})
    out[S_ + 'park_shade.png'] = ([park_shade()], None, {'section': p, 'anim': 'shade', 'note': 'Under the tree'})
    out[S_ + 'fountain.png'] = ([fountain()], None, {'section': p, 'anim': 'water fountain'})
    out[S_ + 'water_bowl.png'] = ([water_bowl(False), water_bowl(True)], None, {'section': p, 'anim': 'water bowl', 'note': 'Empty, then full: drag it to the dog'})
    out[S_ + 'ball.png'] = ([tennis_ball()], None, {'section': p, 'anim': 'tennis ball', 'note': 'Drag back and let go to throw'})
    out[S_ + 'ball_shadow.png'] = ([ball_shadow()], None, {'section': p, 'anim': 'ball shadow'})
    out[S_ + 'kid_park.png'] = ([crop(kid('stand'), 0, 0, 40, KID_H)], None, {'section': p, 'anim': 'kid', 'note': 'Stands by during fetch'})
    s = 'Meeting a new friend: Sam'
    for name, frames in sam_frames().items():
        out[S_ + f'sam_{name}.png'] = (frames, None, {'section': s, 'anim': name})
    for name, frames in sam_bust_frames().items():
        out[S_ + f'sam_bust_{name}.png'] = (frames, None, {'section': s, 'anim': f'portrait: {name}'})
    out[S_ + 'sam_hand.png'] = ([sam_hand()], None, {'section': s, 'anim': "Sam's hand", 'note': 'Dragged onto the dog to pet'})
    out[U + 'nameplate_sam.png'] = ([panel(12, 12, 'O', lip='o', insets=(2, 1))], None, {'section': s, 'anim': 'name plate: Sam'})
    for part in ('head', 'chest'):
        out[S_ + f'adult_part_{part}.png'] = ([adult_part(part, False)], None, {'section': 'bg', 'anim': part})
        out[S_ + f'adult_ring_{part}.png'] = ([adult_part(part, True)], None, {'section': s, 'anim': f'hover: {part}',
                                                                                'note': 'Wrong: over the head' if part == 'head' else 'Right: side of the neck and chest'})
    i = 'Icons'
    for name in ICONS11:
        out[U + f'icon_{name}.png'] = ([icon11(name)], None, {'section': i, 'anim': name})
    for name, fn in L3_PANELS.items():
        art_ = fn()
        for coat, cols in COATS.items():
            out[SC + f'panel_{name}_{coat}.png'] = ([art_], cols, {'section': 'bg', 'anim': name})
    f = 'The finale and the level select'
    out[SC + 'finale_bg.png'] = ([draw_finale_bg()], None, {'section': 'bg', 'anim': 'finale'})
    for coat, cols in COATS.items():
        out[SC + f'thumb_park_{coat}.png'] = ([thumb_park_open()], cols, {'section': f, 'anim': 'Level 3 thumbnail', 'coat': coat, 'note': 'Open now'})
    e = 'Extras for Levels 1 and 2'
    out[U + 'hover_frame.png'] = ([hover_frame()], None, {'section': e, 'anim': 'hover frame', 'note': 'Nine-slice highlight for places (counter, floor spots)'})
    for part, (hx, hy, hw, hh) in CU_HITS.items():
        out[U + f'found_cu_{part}.png'] = ([found_ring(hw + 6, hh + 6)], None, {'section': e, 'anim': f'found: {part}', 'note': 'Circles the difference in a close-up'})
    return out


def g11_mockups():
    caramel = COATS['caramel']
    t = lambda x, y, w, s, size, col=INK, al='center': ('@text', x, y, w, s, size, col, al)
    W2 = (640, 360)
    A = adult_anims_l3()
    g = WALK['ground']
    street = draw_street()

    def walk(offset, dog_anim='walk', tight=False):
        items = [('@canvas', crop(street, offset, 0, 320, 180), 0, 0, 2)]
        for name, x, y in WALK['distractions']:
            cv = {'squirrel': squirrel_frames()[0], 'sandwich': sandwich(), 'cat': cat_frames()[0]}[name]
            if 0 <= x - offset < 320:
                items.append(('@canvas', cv, (x - offset - cv.w // 2) * 2, (y - cv.h) * 2, 2))
        kx = WALK['kid_x']
        n = WALK['tight' if tight else 'slack']
        items += [('@canvas', kid_walk_frames()[1], kx * 2, (g - KID_H) * 2, 2),
                  ('@canvas', leash(tight), (kx + WALK['hand'][0]) * 2, (g + WALK['hand'][1]) * 2, 2),
                  ('@canvas', A[dog_anim][0], (kx + WALK['hand'][0] + n - WALK['collar'][0] - 24) * 2, (g - 48) * 2, 2, caramel)]
        return items + hud8(52, 'Biscuit', 'leash', 'Walk to the park')

    def park():
        return [('@canvas', draw_park(), 0, 0, 2), ('@canvas', park_shade(), PARK['shade'][0] * 2, PARK['shade'][1] * 2, 2),
                ('@canvas', park_tree(), -4 * 2, (PARK['ground'] - 122) * 2, 2), ('@canvas', fountain(), 274 * 2, (PARK['ground'] + 2 - 52) * 2, 2),
                ('@canvas', water_bowl(True), (PARK['bowl'][0] - 11) * 2, (PARK['bowl'][1] - 12) * 2, 2),
                ('@canvas', crop(kid('stand'), 0, 0, 40, KID_H), PARK['kid_x'] * 2, (PARK['ground'] - KID_H) * 2, 2)]
    dog_at = lambda frame, x: ('@canvas', frame, (x - 24) * 2, (PARK['ground'] - 48) * 2, 2, caramel)
    arc = []
    for k in range(1, 10):
        u = k / 10
        x = PARK['ball'][0] + u * 90; y = PARK['ball'][1] - 4 - 112 * u * (1 - u)
        arc.append(('@canvas', demo_dot(), round(x * 2) - 6, round(y * 2) - 6, 2))
    fetch = park() + [dog_at(A['sit'][0], PARK['dog_x'])] + arc + [
        ('@canvas', tennis_ball(), (PARK['ball'][0] - 18) * 2, (PARK['ball'][1] - 8) * 2, 2),
        ('@canvas', hand_frames()[1], (PARK['ball'][0] - 22) * 2, (PARK['ball'][1] - 4) * 2, 2)] + hud8(46, 'Biscuit', 'ball', 'Fetch  1 of 2')
    tired = park() + [dog_at(A['pant'][0], 196), ('@canvas', tennis_ball(), 212 * 2, (PARK['ground'] - 8) * 2, 2)] + hud8(40, 'Biscuit', 'ball', 'Fetch  1 of 2')
    rest = park() + [dog_at(A['rest'][0], PARK['rest_x']), ('@canvas', water_bowl(True), (PARK['rest_x'] + 14) * 2, (PARK['ground'] - 12) * 2, 2)] + hud8(70, 'Biscuit', 'water', 'Fetch  1 of 2')
    sx, dx = PARK['sam_x'], PARK['dog_x'] + 30
    greet = park() + [dog_at(adult_anims()['wag'][1], dx), ('@canvas', adult_part('chest', True), (dx - 24) * 2, (PARK['ground'] - 48) * 2, 2),
                      ('@canvas', sam('stand').flipped(), sx * 2, (PARK['ground'] - KID_H) * 2, 2),
                      ('@canvas', sam_hand().flipped(), (dx + 4) * 2, (PARK['ground'] - 26) * 2, 2)] + hud8(60, 'Biscuit', 'pet', 'New friend  2 of 2')
    stressed = park() + [dog_at(A['stress'][1], dx), ('@canvas', sam('hand').flipped(), sx * 2, (PARK['ground'] - KID_H) * 2, 2)] + hud8(60, 'Biscuit', 'pet', 'New friend  2 of 2')
    fin = [('@canvas', draw_finale_bg(), 0, 0, 2), t(108, 14, 424, "You're a Pawfect Parent!", 24)]
    for i, (st, x) in enumerate((('assets/sprites/puppy_caramel_wag.png', 30), ('assets/sprites/young_caramel_wag.png', 122), ('assets/sprites/adult_caramel_wag.png', 214))):
        fw = (32, 40, 48)[i]
        fin.append((st, (x + 38 - fw // 2) * 2, (114 - fw) * 2, 2))
        fin.append(t(x * 2, 284, 152, ('Day 1', 'Check-up Day', 'Park Day')[i], 15))
    scenes = [('The walk: hold to walk; the leash is loose', W2, walk(0)),
              ('The walk: a squirrel! The dog lunges and the leash goes tight (let go to stop)', W2, walk(150, 'lunge', True)),
              ('The walk: the dog sits calmly once the player lets go', W2, walk(150, 'sit')),
              ('The walk ends at the park gate', W2, walk(640)),
              ('Fetch: drag the ball back and let go (the dots show where it will land)', W2, fetch),
              ('Fetch: after a few throws the dog pants and slows down (no UI cues: the player has to notice)', W2, tired),
              ('Rest: in the shade with a bowl of water', W2, rest),
              ('A new friend: Sam pets the side of the neck and chest (drag the hand; the target lights up)', W2, greet),
              ('A new friend, the other variant: stress signals (whale eye, lip lick); the right call is "Not today"', W2, stressed),
              ('The finale', W2, fin)]
    ci, sp = panel(18, 18, 'W', ring='E'), speech_bubble()
    pface = crop(parent_frames()['talk'][1], 11, 5, 26, 26)
    for name, (who, line) in L3_LINES.items():
        items = [('@canvas', L3_PANELS[name](), 0, 0, 2, caramel), ('@rect', 0, 0, 640, 30, '#D7C4EC'), ('@rect', 0, 292, 640, 68, '#D7C4EC'),
                 ('@canvas', nine(ci, 30, 30, 6), 8, 296, 2), ('@canvas', pface, 12, 300, 2),
                 ('@canvas', nine(sp, 270, 26, 5), 82, 302, 2), ('@text', 98, 312, 518, line.replace('{name}', 'Biscuit'), 16, INK, 'left')]
        scenes.append((f'Story panel: {name}', W2, items))
    return scenes


GROUPS = {1: group1, 2: group2, 3: group3, 4: group4, 5: group5, 6: group6, 8: group8, 9: group9, 10: group10, 11: group11}
SCENES = {2: SCENES2, 3: ui_mockups(), 4: screen_mockups(), 5: keyboard_mockups(), 6: l2_mockups(), 8: g8_mockups(), 9: g9_mockups(), 10: g10_mockups(), 11: g11_mockups()}


# ---------------------------------------------------------------- check / export / preview
def check(group):
    errors = []
    for path, (frames, extra, _) in group.items():
        keys = set(PALETTE) | set(extra or {})
        sizes = {(f.w, f.h) for f in frames}
        if len(sizes) != 1:
            errors.append(f'{path}: frames differ in size {sizes}')
        for i, f in enumerate(frames):
            if len(f.px) != f.h or any(len(r) != f.w for r in f.px):
                errors.append(f'{path}[{i}]: ragged grid')
            bad = {k for r in f.px for k in r if k and k not in keys}
            if bad:
                errors.append(f'{path}[{i}]: unknown palette keys {bad}')
            if not any(k for r in f.px for k in r):
                errors.append(f'{path}[{i}]: empty frame')
    return errors


def export(group):
    for path, (frames, extra, _) in group.items():
        p = ROOT / path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(sheet_png(frames, extra))


def preview(n, group):
    from preview_template import render  # tools/preview_template.py
    html = render(n, group, PALETTE, COATS, sheet_png, SCENES.get(n), ROOT)
    out = ROOT / 'tools' / 'preview' / f'group{n}.html'
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding='utf-8')
    return out


def main(argv):
    if '--check' in argv:
        errs = [e for g in GROUPS.values() for e in check(g())]
        print('\n'.join(errs) or f'ok: {len(GROUPS)} group(s) valid')
        return 1 if errs else 0
    ns = [int(argv[argv.index('--group') + 1])] if '--group' in argv else list(GROUPS)
    for n in ns:
        g = GROUPS[n]()
        errs = check(g)
        if errs:
            print('\n'.join(errs)); return 1
        export(g)
        print(f'group {n}: exported {len(g)} sheets')
        if '--group' in argv:
            print('preview:', preview(n, g))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
