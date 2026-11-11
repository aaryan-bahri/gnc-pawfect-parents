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
             mouth='closed', ear=(0, 0), body_dy=0, pose='stand', tuck=False):
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
    # blush
    c.put(exx - 1, eyy + 3, 'N')
    # mouth
    my = int(sy + sry) - 1
    if mouth == 'open':
        c.rect(int(sx) - 1, my, 3, 1, 'k')
        c.rect(int(sx), my + 1, 2, 2, 'N')
    elif mouth == 'eat':
        c.rect(int(sx) - 1, my, 3, 1, 'k')
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
    c = Canvas(16, 16)
    (ICONS.get(name) or ICONS_L2[name])(c)
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
           'B': ['110', '101', '110', '101', '110'], 'S': ['011', '100', '010', '001', '110']}


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


def draw_panel_car():
    """Panel 1: the drive home. Visible area is y 15..146 (letterbox bars cover the rest)."""
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
    puppy_head(c, 137, 101)                                               # puppy peeking out
    c.pattern(136, 90, ['.R.R.', 'RRRRR', '.RRR.', '..R..'])              # heart above the box
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
        for name in CLOSEUPS:
            out[f'assets/screens/closeup_{name}_{coat}.png'] = ([draw_closeup(name)], cols, {'section': 'bg', 'anim': name})
        for name, fn in (('clinic', draw_panel_clinic), ('vaccine', draw_panel_vaccine)):
            out[f'assets/screens/panel_{name}_{coat}.png'] = ([fn()], cols, {'section': 'bg', 'anim': name})
    notes = {'vet': 'Health check skill / task card', 'toothbrush': 'Shopping list: dog toothbrush', 'toothpaste': 'Shopping list: dog toothpaste',
             'flea': 'Shopping list: flea treatment (dog)', 'clippers': 'Shopping list: nail clippers', 'ear': 'Shopping list: ear cleaner (dog)'}
    for name in ICONS_L2:
        out[f'assets/ui/icon_{name}.png'] = ([icon(name)], None, {'section': 'Icons', 'anim': name, 'note': notes[name]})
    out['assets/ui/spot_ring.png'] = (spot_frames(), None, {'section': 'Check-up UI', 'anim': 'spot ring', 'note': 'Blinks over each spot to check'})
    PS = 'Shopping list paper (pieces)'
    out['assets/ui/paper_top.png'] = ([paper_top()], None, {'section': PS, 'anim': 'top', 'note': 'Binding strip. The title is text'})
    out['assets/ui/paper_row.png'] = ([paper_row()], None, {'section': PS, 'anim': 'ruled line', 'note': 'Repeated, one per item'})
    out['assets/ui/paper_bottom.png'] = ([paper_bottom()], None, {'section': PS, 'anim': 'bottom', 'note': 'Closes the page'})
    out['assets/ui/list_box.png'] = ([list_box(False)], None, {'section': PS, 'anim': 'tick box', 'note': 'Empty, in front of each item'})
    out['assets/ui/list_tick.png'] = ([list_box(True)], None, {'section': PS, 'anim': 'ticked box', 'note': 'When bought (store)'})
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


# ---------------------------------------------------------------- group 7: Level 2, the pet store
# 24x24 shelf items (shown at 2x). kind: need (vet) / need (parent) / want / look-alike (the wrong pick).
def _tube(c, band, stripes, cap):
    c.rect(1, 9, 3, 10, 'E'); c.rect(4, 9, 14, 10, 'W'); c.rect(4, 17, 14, 2, 'E')
    c.rect(7, 9, 8, 10, band)
    for sx, col in stripes:
        c.rect(sx, 9, 1, 10, col)
    c.rect(18, 11, 5, 6, cap); c.rect(18, 15, 5, 2, 'r' if cap == 'R' else 's')


def _box(c, body, shade, lid):
    c.rect(5, 2, 14, 20, body); c.rect(5, 19, 14, 3, shade); c.rect(5, 2, 14, 4, lid); c.rect(16, 6, 3, 13, shade)


def _bottle(c, body, shade, cap, label):
    c.rect(6, 7, 12, 15, body); c.rect(6, 19, 12, 3, shade); c.rect(8, 3, 8, 4, cap); c.rect(8, 6, 8, 1, 'K')
    c.rect(8, 11, 8, 7, label)


def _item_toothbrush(c):
    c.rect(1, 15, 14, 4, 'M'); c.rect(1, 18, 14, 1, 'm'); c.rect(4, 16, 3, 2, 'R')
    c.rect(15, 15, 7, 4, 'W'); c.rect(15, 18, 7, 1, 'E'); c.rect(15, 10, 7, 5, 'S')
    for x in (16, 18, 20):
        c.put(x, 10, 'w'); c.put(x + 1, 12, 's')


def _item_toothpaste(c):
    _tube(c, 'Y', (), 'R'); c.pattern(8, 12, ['K...K', 'KKKKK', 'K...K'])               # a bone on the tube: made for dogs


def _item_toothpaste_human(c):
    _tube(c, 'S', ((9, 'M'), (11, 'M'), (13, 'M')), 'S')


def _item_flea(c):
    _box(c, 'M', 'm', 'W'); c.pattern(8, 9, ['K.K.K.K', '.......', '..KKK..', '.KKKKK.', '..KKK..']); c.pattern(10, 16, ['.S.', 'SwS', '.S.'])


def _item_flea_cat(c):
    _box(c, 'L', 'l', 'W'); c.pattern(8, 9, ['K.....K', 'KK...KK', 'KKKKKKK', 'K.K.K.K', 'KKKKKKK', '.KKKKK.']); c.pattern(10, 17, ['.S.', 'SwS', '.S.'])


def _item_ear(c):
    c.ellipse(12, 4, 3.4, 3.2, 'R', light='N'); c.rect(9, 7, 6, 3, 'W'); c.rect(7, 10, 10, 12, 'L'); c.rect(7, 19, 10, 3, 'l')
    c.rect(8, 13, 8, 5, 'W'); c.pattern(10, 14, ['.S.', 'SwS', '.S.'])


def _item_clippers(c):
    line(c, 5, 18, 19, 8, 'S', 3); line(c, 5, 6, 19, 15, 'W', 3)
    ring_blob(c, 5, 18, 'R'); ring_blob(c, 5, 6, 'R'); c.rect(11, 11, 2, 2, 'K')


def _item_brush(c):
    c.rect(1, 15, 11, 5, 'D'); c.rect(1, 19, 11, 1, 'd')
    c.rect(11, 9, 11, 11, 'P'); c.rect(11, 18, 11, 2, 'p')
    for x in range(12, 22, 2):
        for y in (10, 13, 16):
            c.put(x, y, 'K')


def _item_shampoo_dog(c):
    _bottle(c, 'M', 'm', 'Y', 'W'); c.pattern(10, 13, ['R.R.R', '.....', '.RRR.', 'RRRRR', '.RRR.'][:5])


def _item_shampoo_human(c):
    _bottle(c, 'P', 'p', 'R', 'W'); c.pattern(10, 13, ['.N.N.', 'NNNNN', '.NYN.', 'NNNNN', '.N.N.'])


def _item_chew(c):
    c.rect(5, 10, 14, 5, 'R'); c.rect(5, 14, 14, 1, 'r'); c.rect(7, 11, 4, 1, 'N')
    for x, y in ((5, 9), (5, 16), (19, 9), (19, 16)):
        c.ellipse(x, y, 2.6, 2.6, 'R', shade='r')


def _item_ball_squeak(c):
    c.ellipse(12, 14, 9, 9, 'Y', shade='y', light='w'); c.rect(4, 13, 17, 2, 'R'); c.rect(11, 12, 3, 4, 'R')
    c.put(12, 13, 'K'); c.pattern(7, 8, ['w', 'w'])


def _item_ball_tiny(c):
    c.ellipse(12, 19, 3.4, 3.4, 'R', shade='r'); c.put(11, 18, 'w')


def _item_tag(c):
    ring_blob(c, 12, 4, 'S'); c.ellipse(12, 15, 8, 7, 'Y', shade='y'); c.rect(8, 13, 8, 1, 'K'); c.rect(9, 16, 6, 1, 'K')
    c.pattern(11, 18, ['R.R', 'RRR', '.R.'])


def _item_bags(c):
    c.ellipse(12, 14, 9, 8, 'M', shade='m'); c.ellipse(12, 14, 4, 3.5, 'E'); c.ellipse(12, 14, 1.5, 1.5, 'K')
    c.rect(14, 19, 7, 3, 'W'); c.rect(14, 21, 7, 1, 'E'); c.put(16, 20, 'S'); c.put(19, 20, 'S')


def _item_bandana(c):
    for r in range(15):
        half = int((14 - r) * 0.75) + 1
        c.rect(12 - half, 6 + r, 2 * half, 1, 'R')
    c.rect(2, 6, 20, 2, 'r')
    for x, y in ((6, 10), (11, 9), (16, 10), (9, 13), (14, 13), (12, 17)):
        c.put(x, y, 'W'); c.put(x + 1, y, 'W')


def _item_bow(c):
    for x in range(3, 10):
        h = (x - 2) * 0.9
        c.rect(x, int(13 - h), 1, int(2 * h) + 1, 'N')
        c.rect(23 - x, int(13 - h), 1, int(2 * h) + 1, 'N')
    c.rect(4, 12, 5, 1, 'R'); c.rect(15, 12, 5, 1, 'R')
    c.ellipse(12, 13, 2.8, 3.4, 'R', shade='r'); c.rect(10, 16, 2, 5, 'N'); c.rect(13, 16, 2, 5, 'N')


def _item_sweater(c):
    c.rect(6, 8, 12, 14, 'S'); c.rect(2, 9, 5, 9, 'S'); c.rect(17, 9, 5, 9, 'S')
    c.ellipse(12, 8, 3.5, 2, 'E'); c.rect(6, 12, 12, 2, 'W'); c.rect(6, 17, 12, 2, 'W')
    c.rect(2, 17, 5, 2, 'L'); c.rect(17, 17, 5, 2, 'L'); c.rect(6, 21, 12, 1, 'L'); c.rect(15, 9, 3, 13, 's')


def _item_collar(c):
    for y in range(24):
        for x in range(24):
            r = ((x + 0.5 - 12) / 10.5) ** 2 + ((y + 0.5 - 12) / 9) ** 2
            if 0.5 <= r <= 1.0:
                c.put(x, y, 'L' if y < 16 else 'l')
    for x, y in ((6, 6), (12, 3), (18, 6), (21, 12), (3, 12)):
        c.rect(x, y, 2, 2, 'Y'); c.put(x, y, 'w')
    c.ellipse(12, 21, 2.5, 2.5, 'Y')


def _item_bed(c):
    c.ellipse(12, 17, 11, 5.5, 'p'); c.ellipse(12, 16, 11, 5, 'P'); c.ellipse(12, 15, 8, 3, 'W'); c.ellipse(12, 15, 5, 1.6, 'E')
    c.pattern(10, 14, ['R.R', '.R.']); c.put(12, 17, 'p')


SHOP_ITEMS = {
    'toothbrush': (_item_toothbrush, 'Need (vet)'), 'toothpaste': (_item_toothpaste, 'Need (vet)'),
    'toothpaste_human': (_item_toothpaste_human, 'Look-alike: wrong pick'),
    'flea': (_item_flea, 'Need (vet)'), 'flea_cat': (_item_flea_cat, 'Look-alike: wrong pick'),
    'ear': (_item_ear, 'Need (vet)'), 'clippers': (_item_clippers, 'Need (vet)'),
    'brush': (_item_brush, 'Need (parent)'), 'shampoo_dog': (_item_shampoo_dog, 'Want'),
    'shampoo_human': (_item_shampoo_human, 'Look-alike: wrong pick'),
    'chew': (_item_chew, 'Need (parent)'), 'ball_squeak': (_item_ball_squeak, 'Want'),
    'ball_tiny': (_item_ball_tiny, 'Look-alike: too small'), 'tag': (_item_tag, 'Need (parent)'),
    'bags': (_item_bags, 'Need (parent)'), 'bandana': (_item_bandana, 'Want'), 'bow': (_item_bow, 'Want'),
    'sweater': (_item_sweater, 'Want'), 'collar': (_item_collar, 'Want'), 'bed': (_item_bed, 'Want'),
}


def shop_item(name):
    c = Canvas(24, 24)
    SHOP_ITEMS[name][0](c)
    return c.outline()


# ---- the store rooms (320x180 world)
STORE = dict(boards=(112, 156), unit=(120, 288))
STORE_AISLES = (('Health', (('toothbrush', 'toothpaste', 'toothpaste_human'), ('flea', 'flea_cat', 'ear'))),
                ('Grooming', (('clippers', 'brush'), ('shampoo_dog', 'shampoo_human'))),
                ('Play & Walk', (('chew', 'ball_squeak', 'ball_tiny'), ('tag', 'bags'))),
                ('Home & Style', (('bandana', 'bow', 'sweater'), ('collar', 'bed'))))


def store_room(c):
    c.rect(0, 0, 320, 140, 'L')
    for y in range(6, 130, 12):
        for x in range(4 + (6 if (y // 12) % 2 else 0), 320, 12):
            c.put(x, y, 'l')
    c.rect(0, 136, 320, 4, 'P'); c.rect(0, 136, 320, 1, 'K')
    c.rect(0, 140, 320, 40, 'E'); c.rect(0, 140, 320, 1, 'K')
    for i, y in enumerate(range(141, 180, 10)):
        for x in range(10 if i % 2 else 0, 320, 20):
            c.rect(x, y, 10, 10, 'W')


def draw_store():
    c = Canvas(320, 180)
    store_room(c)
    x0, x1 = STORE['unit']
    box(c, x0, 76, x1 - x0, 98, 'P'); c.rect(x0 + 1, 77, x1 - x0 - 2, 3, 'p')                      # back panel
    box(c, x0 - 3, 72, x1 - x0 + 6, 6, 'D'); c.rect(x0 - 2, 76, x1 - x0 + 4, 1, 'd')                # top cap
    for post in (x0, x1 - 4):
        box(c, post, 76, 4, 98, 'D')
    for bt in STORE['boards']:
        c.rect(x0 + 4, bt, x1 - x0 - 8, 3, 'D'); c.rect(x0 + 4, bt, x1 - x0 - 8, 1, 'K')           # board top
        box(c, x0 + 3, bt + 3, x1 - x0 - 6, 8, 'E'); c.rect(x0 + 4, bt + 4, x1 - x0 - 8, 1, 'w')   # board lip: the price goes here
        c.rect(x0 + 4, bt + 11, x1 - x0 - 8, 2, 'p')                                                # shadow under it
    box(c, x0, 168, x1 - x0, 6, 'd')                                                               # kick plate
    c.rect(144, 40, 1, 12, 'K'); c.rect(264, 40, 1, 12, 'K')                                       # sign strings
    box(c, 130, 50, 148, 22, 'W'); c.rect(131, 68, 146, 3, 'E')                                    # aisle sign (the name is text)
    return c


def draw_till():
    c = Canvas(320, 180)
    store_room(c)
    box(c, 214, 18, 90, 60, 'W'); box(c, 218, 22, 82, 52, 'S'); c.rect(258, 22, 1, 52, 'K'); c.rect(218, 48, 82, 1, 'K')   # window
    c.ellipse(236, 36, 8, 3, 'W'); blob(c, 282, 36, 6, 6, 'Y', 'y')
    box(c, 40, 112, 240, 8, 'E'); c.rect(41, 113, 238, 1, 'w')                                     # counter top (items stand on it)
    box(c, 44, 120, 232, 52, 'P'); c.rect(45, 121, 230, 2, 'p')
    for dx in (52, 124, 196):
        box(c, dx, 128, 64, 36, 'P'); c.rect(dx + 1, 128, 62, 2, 'p'); c.rect(dx + 26, 134, 12, 3, 'Y')
    box(c, 226, 86, 44, 26, 'S'); box(c, 230, 90, 20, 10, 'M'); c.rect(232, 92, 6, 1, 'w')        # till
    for kx in range(254, 266, 4):
        for ky in (90, 96):
            c.rect(kx, ky, 3, 3, 'W')
    box(c, 236, 104, 24, 6, 's')
    box(c, 62, 100, 16, 12, 'S'); c.rect(64, 96, 12, 4, 'R'); c.rect(66, 93, 8, 3, 'W')          # a jar of treats
    return c


# ---- UI bits
def coin_jar(level):
    """level 0..5: how much of the budget is left."""
    c = Canvas(12, 14)
    c.rect(2, 1, 8, 3, 'R'); c.rect(3, 2, 6, 1, 'r')                                             # lid with a slot
    c.rect(1, 4, 10, 9, 'S')
    pile = round(level * 1.6)
    if pile:
        c.rect(2, 12 - pile + 1, 8, pile, 'Y'); c.rect(2, 12 - pile + 1, 8, 1, 'w'); c.rect(2, 12, 8, 1, 'y')
        for i in range(pile // 2):
            c.put(3 + i * 3, 12 - pile + 3, 'y')
    c.rect(2, 5, 1, 4, 'w')
    return c.outline()


def draw_coin(size):
    c = Canvas(size, size)
    r = size / 2 - 1
    c.ellipse(size / 2, size / 2, r, r, 'Y', shade='y')
    if size >= 12:
        c.rect(size // 2 - 1, 5, 2, size - 10, 'y'); c.rect(4, 4, 2, 2, 'w')
    else:
        c.put(2, 2, 'w')
    return c.outline()


def draw_basket(items):
    c = Canvas(30, 24)
    if items:
        for x, y, col in ((6, 6, 'R'), (12, 3, 'Y'), (18, 6, 'M'), (9, 8, 'S'), (15, 8, 'N')):
            c.ellipse(x + 3, y + 3, 3.5, 3.5, col)
    c.rect(2, 10, 26, 2, 'd')
    c.rect(3, 12, 24, 10, 'D')
    for y in (14, 18):
        c.rect(3, y, 24, 1, 'd')
    for x in range(5, 27, 4):
        c.rect(x, 12, 1, 10, 'd')
    line(c, 3, 11, 8, 3, 'd', 1); line(c, 27, 11, 22, 3, 'd', 1); c.rect(8, 2, 14, 1, 'd')        # handle
    return c.outline()


def draw_arrow(direction):
    c = Canvas(12, 16)
    rows = ['....YY', '...YYY', '..YYYy', '.YYYYy', 'YYYYYy', 'YYYYYy', '.YYYYy', '..YYYy', '...YYy', '....Yy']
    c.pattern(2, 3, rows)
    c.rect(4, 4, 1, 2, 'w')
    return (c.flipped() if direction == 'right' else c).outline()


# ---- group 7 export
def group7():
    out = {}
    out['assets/bg/store_aisle.png'] = ([draw_store()], None, {'section': 'bg', 'anim': 'store aisle'})
    out['assets/bg/store_till.png'] = ([draw_till()], None, {'section': 'bg', 'anim': 'store till'})
    for name, (_, kind) in SHOP_ITEMS.items():
        out[f'assets/sprites/shop_{name}.png'] = ([shop_item(name)], None, {'section': 'Shelf items (24x24, shown at 2x)', 'anim': name.replace('_', ' '), 'note': kind})
    U = 'assets/ui/'
    out[U + 'coin_jar.png'] = ([coin_jar(k) for k in range(6)], None, {'section': 'Budget and basket', 'anim': 'coin jar', 'note': 'Six frames: the coins left in the budget'})
    out[U + 'coin_small.png'] = ([draw_coin(8)], None, {'section': 'Budget and basket', 'anim': 'coin (price)', 'note': 'Next to each price'})
    out[U + 'icon_coin.png'] = ([draw_coin(16)], None, {'section': 'Budget and basket', 'anim': 'coin icon', 'note': 'Smart shopping skill, task card'})
    out[U + 'basket.png'] = ([draw_basket(False), draw_basket(True)], None, {'section': 'Budget and basket', 'anim': 'basket', 'note': 'Empty, then with items'})
    out[U + 'arrow_left.png'] = ([draw_arrow('left')], None, {'section': 'Budget and basket', 'anim': 'aisle arrow left', 'note': 'Next to the aisle sign'})
    out[U + 'arrow_right.png'] = ([draw_arrow('right')], None, {'section': 'Budget and basket', 'anim': 'aisle arrow right', 'note': 'Next to the aisle sign'})
    return out


# ---- group 7 preview mock-ups
STORE_LIST = ('Dog toothbrush', 'Dog toothpaste', 'Flea treatment (dog)', 'Nail clippers', 'Ear cleaner (dog)',
              'Brush', 'ID tag', 'Chew toy', 'Poop bags')


def store_paper(x, y, labels, ticked=0):
    items = [('assets/ui/paper_top.png', x, y, 2), ('@text', x + 28, y + 14, 150, 'Shopping list', 14, '#5A3E36', 'left')]
    for i, lab in enumerate(labels):
        ry = y + 36 + i * PAPER_ROW * 2
        items += [('assets/ui/paper_row.png', x, ry, 2), ('assets/ui/list_tick.png' if i < ticked else 'assets/ui/list_box.png', x + 26, ry + 3, 2),
                  ('@text', x + 46, ry + 3, 150, lab, 13, '#5A3E36', 'left')]
    items.append(('assets/ui/paper_bottom.png', x, y + 36 + len(labels) * PAPER_ROW * 2, 2))
    return items


def store_hud(coins_left):
    """The level 2 HUD plus the coin jar card (between the name and the task card)."""
    ci = panel(18, 18, 'W', ring='E')
    items = l2_hud(44, 'Biscuit', 'toothbrush', 'Shopping  2 of 2')
    items += [('@canvas', nine(ci, 60, 16, 6), 282, 6, 2), ('assets/ui/coin_jar.png', 290, 8, 2),
              ('@text', 324, 12, 48, str(coins_left), 16, '#5A3E36', 'left')]
    return items


def aisle_items(aisle, taken=()):
    """Shelf sprites + price tags for one aisle, as mock-up layers."""
    prices = {'toothbrush': 4, 'toothpaste': 6, 'toothpaste_human': 4, 'flea': 12, 'flea_cat': 10, 'ear': 7, 'clippers': 7, 'brush': 5,
              'shampoo_dog': 6, 'shampoo_human': 5, 'chew': 6, 'ball_squeak': 5, 'ball_tiny': 2, 'tag': 4, 'bags': 3,
              'bandana': 4, 'bow': 3, 'sweater': 9, 'collar': 8, 'bed': 12}
    layers = []
    for row, ids in enumerate(STORE_AISLES[aisle][1]):
        xs = {3: (146, 204, 262), 2: (175, 233)}[len(ids)]
        for x, id_ in zip(xs, ids):
            bt = STORE['boards'][row]
            if id_ not in taken:
                layers.append((f'assets/sprites/shop_{id_}.png', (x - 12) * 2, (bt - 23) * 2, 2))
            layers += [('assets/ui/coin_small.png', (x - 11) * 2, (bt + 4) * 2, 2),
                       ('@text', (x - 1) * 2, (bt + 4) * 2 + 1, 40, str(prices[id_]), 13, '#5A3E36', 'left')]
    return layers


def store_mockups():
    ci, bm, bc = panel(18, 18, 'W', ring='E'), button('M', 'm', 'Y')[0], button('W', 'E', 'Y')[0]
    sp = speech_bubble()
    t = lambda x, y, w, s, size, col='#5A3E36', al='center': ('@text', x, y, w, s, size, col, al)
    W2 = (640, 360)

    def aisle(i, coins, taken=(), ticked=0, extra=()):
        sign = [t(284, 110, 248, STORE_AISLES[i][0], 16), ('@canvas', draw_arrow('left'), 266, 106, 2), ('@canvas', draw_arrow('right'), 550, 106, 2)]
        basket = [('assets/ui/basket.png', 578, 288, 2), t(590, 326, 36, f'{len(taken)}', 14)]
        return ([('assets/bg/store_aisle.png', 0, 0, 2)] + store_hud(coins) + sign + aisle_items(i, taken)
                + store_paper(4, 132, STORE_LIST, ticked) + basket + list(extra))
    health = aisle(0, 60)
    # tapping a shelf item: a small card with the name, the price and what the balance would be
    pick = aisle(0, 60, extra=[('@rect', 0, 0, 640, 360, 'rgba(62,42,36,.4)'), ('@canvas', nine(ci, 120, 82, 6), 200, 100, 2),
        t(216, 112, 208, 'Dog toothpaste', 18), ('assets/sprites/shop_toothpaste.png', 216, 142, 2), t(272, 144, 150, 'Costs 6 coins', 14, al='left'),
        t(272, 164, 150, 'After: 54 coins left', 14, '#6FA07E', 'left'),
        ('@canvas', nine(bm, 54, 16, 5), 214, 222, 2), t(214, 230, 108, 'Add', 16), ('@canvas', nine(bc, 46, 16, 5), 338, 222, 2), t(338, 231, 92, 'Not now', 13)])
    # after a few buys, in the Play & Walk aisle
    play = aisle(2, 31, taken=('tag', 'chew'), ticked=7)
    # the basket
    cells = [('toothbrush', 'toothpaste', 'flea', 'clippers', 'ear'), ('brush', 'tag', 'chew', 'bags', 'bandana')]
    basket = aisle(3, 22, taken=sum(cells, ()), ticked=9, extra=[('@rect', 0, 0, 640, 360, 'rgba(62,42,36,.45)'), ('@canvas', nine(ci, 170, 140, 6), 150, 60, 2),
        t(170, 74, 300, 'Your basket', 18, al='left')])
    for r, row in enumerate(cells):
        for k, id_ in enumerate(row):
            basket += [('assets/sprites/shop_%s.png' % id_, 174 + k * 58, 106 + r * 74, 2)]
    basket += [t(170, 262, 300, 'Total 49 of 60 coins. Tap an item to put it back.', 13, '#8a6f66', 'left'),
               ('@canvas', nine(bm, 56, 16, 5), 264, 282, 2), t(264, 290, 112, 'Checkout', 16)]
    # the till: the items are matched, one by one, to why they are on the list
    till = ([('assets/bg/store_till.png', 0, 0, 2)] + store_hud(11) + store_paper(4, 132, STORE_LIST, 4)
            + [('assets/sprites/shop_toothbrush.png', 300, 176, 2), ('assets/sprites/shop_toothpaste.png', 372, 176, 2),
               ('@canvas', nine(ci, 52, 50, 6), 2, 40, 2), ('assets/sprites/parent_talk.png', 6, 42, 2),
               ('@canvas', nine(sp, 210, 30, 5), 116, 58, 2), ('@canvas', speech_tail(), 100, 78, 2),
               t(134, 70, 390, "The toothbrush and toothpaste are for the yellow tartar the vet found on Biscuit's teeth.", 16, '#5A3E36', 'left')])
    # album page 2
    album = [('assets/screens/album_bg.png', 0, 0, 2), ('assets/screens/polaroid.png', 82, 62, 2), ('assets/sprites/young_caramel_wag.png', 106, 78, 2),
             t(54, 36, 210, 'Check-up Day', 24), t(82, 186, 128, 'Biscuit', 16), t(340, 40, 230, 'You learned:', 18, '#5A3E36', 'left'),
             ('@canvas', icon('vet'), 340, 84, 2), t(380, 92, 200, 'Health check', 16, '#5A3E36', 'left'), ('@canvas', icon('check'), 530, 84, 2),
             ('assets/ui/icon_coin.png', 340, 132, 2), t(380, 140, 200, 'Smart shopping', 16, '#5A3E36', 'left'), ('@canvas', icon('check'), 530, 132, 2),
             ('@canvas', stamp(), 380, 196, 2), ('@canvas', nine(bm, 56, 16, 5), 380, 280, 2), t(380, 288, 112, 'Next', 18)]
    return [('Aisle: Health (start of the shop, the coin jar is full)', W2, health), ('Tapping an item: name, price and what is left', W2, pick),
            ('Aisle: Play & Walk (some items bought, so their shelf spots are empty)', W2, play), ('The basket (tap an item to put it back)', W2, basket),
            ('The till: each item is matched to why it was bought', W2, till), ('Album page for Level 2', W2, album)]


GROUPS = {1: group1, 2: group2, 3: group3, 4: group4, 5: group5, 6: group6, 7: group7}
SCENES = {2: SCENES2, 3: ui_mockups(), 4: screen_mockups(), 5: keyboard_mockups(), 6: l2_mockups(), 7: store_mockups()}


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
