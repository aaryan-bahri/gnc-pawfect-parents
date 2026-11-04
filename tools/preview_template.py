"""Builds the approval-artifact HTML for an asset group (see CLAUDE.md rule 3)."""
import base64
from html import escape

FRAME_MS = {'idle': 260, 'sit': 600, 'sad': 700, 'cower': 300, 'talk': 160, 'refuse': 300, 'pee': 400,
            'glow marker': 450}
NOTES = {
    'idle': 'Default standing loop, blinks', 'walk': 'Leading the puppy around the room',
    'sit': 'Waiting for food / praise', 'wag': 'Right answer, praise, treat',
    'sniff': 'Sniffing food before deciding', 'circle': 'Potty cue: sniff + turn in place',
    'pee': 'On the pad (or the floor)', 'eat': 'Eating safe food from the bowl',
    'refuse': 'Turns away from unsafe food', 'sad': 'Meter empty / retry screen',
    'cower': 'After being scolded', 'talk': 'Speaking in cutscenes', }
GROUP_INFO = {
    1: ('Palette &amp; Dog', 'Every sprite below is the exact PNG the game will load, scaled up with crisp pixels.', set()),
    2: ('Living Room &amp; Food',
        'Revision 3: the onion is now a pink red onion, and the chicken is a whole roast chicken. Revision 2 put the plant on '
        'the floor, removed the dog bed and glow marker, and gave Snack Time its own kitchen-counter close-up with large, detailed foods. The room mock-up shows the bowl (with kibble), the pad by the '
        'garden door, and a puddle on the rug. The three pad spots are by the door, on the rug, and by the bowl. '
        'Individual sprites are below.', set('EDdOoVvTt')),
    3: ('UI Kit',
        'Two mock-ups show the kit in place: the HUD and the parent speaking at the start of Snack Time, then a fact card after a wrong '
        'pick on the counter. The yellow arrow is the pointer cue that replaces the glow. Text is Pixelify Sans. Bubbles, cards and buttons '
        'are nine-slice sprites, so they stretch to fit any text without blurring. Individual parts are below.', set()),
    4: ('Screens',
        'Revision 2: the opening cutscene now has four illustrated panels (the drive home, arriving at the porch, the PUPPY JOBS chart '
        'on the fridge, and the new supplies), each exported in all three coat colours because the puppy appears in every one. '
        "The parent's face in the text bar is now a 2x crop, so it matches every other pixel. Also new: the logo, the title room, the album "
        'page, the polaroid, paw-print progress, and the retry spotlight. The loading puppy and the growth and retry screens reuse approved sprites.', set()),
    5: ('On-screen Keyboard &amp; Rotate Screen',
        'Two things for phones and tablets. First, the dog setup screen with an on-screen keyboard, so a name can be typed without a '
        'physical keyboard (it is built from the approved cream buttons and cards, and a real keyboard still works on a computer). '
        'Second, a screen that asks players to turn a phone sideways, since the game is wide. Only the small turn-your-phone icon is new art.', set()),
}


def uri_of(png):
    return 'data:image/png;base64,' + base64.b64encode(png).decode()


def render(n, group, palette, coats, sheet_png, scene=None, root=None):
    title, intro, new_keys = GROUP_INFO[n]
    sections, coat_names = {}, []
    for path, (frames, extra, meta) in group.items():
        uri = uri_of(sheet_png(frames, extra))
        if meta['section'] != 'bg':
            sections.setdefault(meta['section'], []).append((path, frames, meta, uri))
        if meta.get('coat') and meta['coat'] not in coat_names:
            coat_names.append(meta['coat'])

    def sprite(frames, meta, uri):
        f = frames[0]
        scale = 6 if f.w <= 32 else 4
        ms = FRAME_MS.get(meta['anim'], 150)
        coat = meta.get('coat')
        hide = ' hidden' if coat and coat != coat_names[0] else ''
        note = meta.get('note') or NOTES.get(meta['anim'], '')
        strip = ''.join(
            f'<span class="fr" style="--fw:{f.w}px;--fh:{f.h}px;background-image:url({uri});'
            f'background-position:-{i * f.w * 3}px 0;background-size:{f.w * len(frames) * 3}px {f.h * 3}px"></span>'
            for i in range(len(frames))) if len(frames) > 1 else ''
        return (f'<figure class="cell"{f" data-coat={coat!r}" if coat else ""}{hide}>'
                f'<div class="stage"><div class="spr" style="--w:{f.w * scale}px;--h:{f.h * scale}px;'
                f'--n:{len(frames)};--dur:{ms * len(frames)}ms;background-image:url({uri})"></div></div>'
                f'<figcaption><b>{escape(meta["anim"])}</b> <span class="dim">{len(frames)}f · {f.w}×{f.h}</span>'
                f'<br><span class="note{" " + note if note in ("safe", "unsafe") else ""}">{escape(note)}</span>'
                f'{f"<span class=strip>{strip}</span>" if strip else ""}</figcaption></figure>')

    scene_html = ''
    for stitle, (ww, wh), items in scene or []:
        layers = []
        for item in items:
            if item[0] == '@text':                # ('@text', x, y, w, text, size, colour, align): Pixelify Sans
                _, x, y, tw, text, size, col, align = item
                layers.append(f'<div class="txt" style="left:{x * 100 / ww}%;top:{y * 100 / wh}%;width:{tw * 100 / ww}%;'
                              f'font-size:{size * 100 / ww}cqw;color:{col};text-align:{align}">{escape(text)}</div>')
                continue
            if item[0] == '@rect':                # ('@rect', x, y, w, h, css colour): letterbox bars, dim overlay
                _, x, y, rw, rh, col = item
                layers.append(f'<div class="layer" style="left:{x * 100 / ww}%;top:{y * 100 / wh}%;width:{rw * 100 / ww}%;'
                              f'height:{rh * 100 / wh}%;background:{col}"></div>')
                continue
            if item[0] == '@canvas':              # ('@canvas', canvas, x, y, scale): drawn in memory
                _, cv, x, y, sc = item
                data, fw = sheet_png([cv]), cv.w
            else:                                 # (path, x, y[, scale]): exported sheet on disk
                path, x, y, sc = (item + (1,))[:4]
                data = (root / path).read_bytes()
                fw = next((fr[0].w for p2, (fr, _, _) in group.items() if p2 == path), None)
            w, h = int.from_bytes(data[16:20], 'big'), int.from_bytes(data[20:24], 'big')
            if fw is None:                        # sheet from an earlier group: assume square frames
                fw = h if w % h == 0 else w
            nfr = w // fw
            layers.append(f'<div class="layer" style="left:{x * 100 / ww}%;top:{y * 100 / wh}%;width:{fw * sc * 100 / ww}%;'
                          f'aspect-ratio:{fw}/{h};background-image:url({uri_of(data)});background-size:{nfr * 100}% 100%"></div>')
        portrait = wh > ww
        note = ('A phone held upright. This screen covers the game until the phone is turned sideways.' if portrait else
                'All pixel art (world and UI) is shown at 2×, so every pixel is the same size. Text is drawn at full screen resolution.'
                if ww == 640 else f'Drawn at {ww}×{wh} and shown at 2× in the 640×360 game.')
        wrap_style = ' style="max-width:320px"' if portrait else ''
        scene_html += (f'<section><h2>Mock-up: {escape(stitle)}</h2><div class="scene-wrap"{wrap_style}>'
                       f'<div class="scene" style="aspect-ratio:{ww}/{wh}">{"".join(layers)}</div></div>'
                       f'<p class="dim">{note}</p></section>')

    swatches = ''.join(f'<li{" class=new" if k in new_keys else ""}><span style="background:{v}"></span>'
                       f'<code>{k}</code> {v}{" <em>new</em>" if k in new_keys else ""}</li>' for k, v in palette.items())
    coat_bar = ''
    if coat_names:
        coat_bar = '<section><div class="bar"><b>Coat colour</b>' + ''.join(
            f'<button type="button" id="coat-{c}" class="coatbtn" data-c="{c}" aria-pressed="{str(i == 0).lower()}">'
            f'<span style="background:{coats[c]["A"]}"></span><span style="background:{coats[c]["B"]}"></span>'
            f'<span style="background:{coats[c]["C"]}"></span>{c}</button>'
            for i, c in enumerate(coat_names)) + '</div></section>'
    body = ''.join(f'<section><h2>{escape(name)}</h2><div class="grid">'
                   + ''.join(sprite(fr, m, u) for _, fr, m, u in items) + '</div></section>'
                   for name, items in sections.items())

    return f'''<title>Pawfect Parents Art: Group {n}</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Pixelify+Sans:wght@400;600&family=Atkinson+Hyperlegible:wght@400;700&display=swap">
<style>
/* Layout: a cosy sticker-book sheet. Sprites sit on little floor "stages" in a wrapping grid. Single deliberate cream look. */
:root {{ --paper:#FFF4E0; --card:#FFFDF7; --ink:#5A3E36; --dim:#8a6f66; --floor:#F6DDB0; --mint:#B8E0C2; --coral:#E8746A; --sage:#6FA07E;
  --display:"Pixelify Sans",ui-monospace,monospace; --body:"Atkinson Hyperlegible",system-ui,sans-serif; color-scheme:light }}
body {{ background:var(--paper); color:var(--ink); font-family:var(--body); font-size:15px; line-height:1.5;
  padding-left:max(16px,env(safe-area-inset-left,0px)); padding-right:max(16px,env(safe-area-inset-right,0px)); padding-block:24px 48px }}
main {{ max-width:1100px; margin:0 auto; display:flex; flex-direction:column; gap:32px }}
h1,h2 {{ font-family:var(--display); font-weight:600; text-wrap:balance; margin:0 }}
h1 {{ font-size:2.2rem; line-height:1.1 }} h2 {{ font-size:1.4rem; margin-bottom:12px }}
header p {{ max-width:65ch; margin:8px 0 0 }}
.dim,.note {{ color:var(--dim) }} .note {{ font-size:13px }}
.note.safe {{ color:var(--sage); font-weight:700 }} .note.unsafe {{ color:var(--coral); font-weight:700 }}
.bar {{ display:flex; flex-wrap:wrap; gap:8px; align-items:center }}
.bar > b {{ font-family:var(--display); font-size:1.05rem; margin-right:4px }}
.coatbtn {{ font:inherit; color:var(--ink); background:var(--card); border:2px solid var(--ink); padding:6px 12px 6px 8px;
  display:inline-flex; gap:3px; align-items:center; cursor:pointer; text-transform:capitalize; box-shadow:3px 3px 0 var(--ink) }}
.coatbtn span {{ width:12px; height:16px; display:inline-block; outline:1px solid var(--ink) }}
.coatbtn span:last-of-type {{ margin-right:6px }}
.coatbtn[aria-pressed="true"] {{ background:var(--mint) }}
.coatbtn:focus-visible {{ outline:3px solid var(--coral); outline-offset:2px }}
.scene-wrap {{ border:2px solid var(--ink); box-shadow:4px 4px 0 var(--ink); max-width:100% }}
.scene {{ position:relative; width:100%; overflow:hidden; container-type:inline-size }}
.layer {{ position:absolute; background-repeat:no-repeat; background-position:0 0; image-rendering:pixelated }}
.txt {{ position:absolute; font-family:var(--display); line-height:1.15; text-wrap:pretty }}
.grid {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(230px,1fr)); gap:16px }}
.cell {{ margin:0; background:var(--card); border:2px solid var(--ink); display:flex; flex-direction:column }}
.stage {{ height:290px; display:flex; align-items:flex-end; justify-content:center;
  background:linear-gradient(var(--card) 78%, var(--floor) 78%); border-bottom:2px solid var(--ink) }}
.spr {{ width:var(--w); height:var(--h); background-repeat:no-repeat;
  background-size:calc(var(--w) * var(--n)) var(--h); image-rendering:pixelated; margin-bottom:12px;
  animation:play var(--dur) steps(var(--n)) infinite }}
@keyframes play {{ from {{ background-position:0 0 }} to {{ background-position:calc(var(--w) * var(--n) * -1) 0 }} }}
@media (prefers-reduced-motion: reduce) {{ .spr {{ animation:none }} }}
figcaption {{ padding:10px 12px; min-width:0 }}
.strip {{ display:flex; flex-wrap:wrap; gap:4px; margin-top:8px }}
.fr {{ width:calc(var(--fw) * 3); height:calc(var(--fh) * 3); background-repeat:no-repeat; image-rendering:pixelated;
  outline:1px dashed #d9c4ae; display:inline-block }}
.pal {{ list-style:none; padding:0; margin:0; display:grid; grid-template-columns:repeat(auto-fill,minmax(150px,1fr)); gap:6px 12px;
  font-size:13px; font-variant-numeric:tabular-nums }}
.pal li {{ display:flex; gap:8px; align-items:center }}
.pal li.new {{ font-weight:700 }} .pal em {{ color:var(--coral); font-style:normal }}
.pal span {{ width:22px; height:22px; outline:2px solid var(--ink); flex:none }}
code {{ font-family:var(--display) }}
</style>
<main>
<header>
  <h1>Asset group {n}: {title}</h1>
  <p>{intro} Reply with <b>approve</b> or list the changes you want.</p>
</header>
{coat_bar}
{scene_html}
{body}
<section><h2>Palette</h2><ul class="pal">{swatches}</ul></section>
</main>
<script>
document.querySelectorAll('.coatbtn').forEach(b => b.addEventListener('click', () => {{
  document.querySelectorAll('.coatbtn').forEach(x => x.setAttribute('aria-pressed', String(x === b)));
  document.querySelectorAll('[data-coat]').forEach(el => {{ el.hidden = el.dataset.coat !== b.dataset.c; }});
}}));
</script>
'''
