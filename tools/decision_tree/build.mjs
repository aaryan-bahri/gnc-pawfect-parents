// Builds the player decision tree (Levels 1 to 3) from the game's own text in src/content.js.
//   node tools/decision_tree/build.mjs
// Writes docs/decision_tree/pawfect_parents_decision_tree.{html,png,pdf}. The PNG and PDF are rendered by headless Chrome/Edge
// from the same page (static mode), so all three always match the game text.
import { readFileSync, writeFileSync, mkdirSync, existsSync } from 'node:fs';
import { execFileSync } from 'node:child_process';
import { fileURLToPath, pathToFileURL } from 'node:url';
import path from 'node:path';
import { LEVEL1, LEVEL2, LEVEL3, CUTSCENES, fill, DOG_NAMES } from '../../src/content.js';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const OUT = path.resolve(HERE, '../../docs/decision_tree');
const BASE = 'pawfect_parents_decision_tree';
const NAME = 'Biscuit';
const f = s => fill(s, NAME);

// ---------------------------------------------------------------- learning objectives (GAME_DESIGN.md section 1.2)
const LOS = [
  { id: 'LO1', short: 'LO1 Safe foods', text: 'Tell safe foods from toxic ones, and explain why some human foods are dangerous' },
  { id: 'LO2', short: 'LO2 Potty cues and spot', text: 'Recognise potty cues and choose a good toilet spot' },
  { id: 'LO3', short: 'LO3 Positive reinforcement', text: 'Use positive reinforcement instead of punishment' },
  { id: 'LO4', short: 'LO4 Health and grooming', text: 'Check basic health signs (teeth, ears, coat, nails), spot the wrong products, and link each one to the right care' },
  { id: 'LO6', short: 'LO6 Tiredness and heat', text: 'Spot tiredness and overheating during exercise and respond to it' },
  { id: 'LO7', short: 'LO7 Safe greetings', text: 'Handle a stranger meeting the dog safely, including reading the dog’s stress signals' },
  { id: 'CTX', short: 'Context / empathy', text: 'Story, naming the dog and caring for it: motivation rather than a taught fact' },
];

// ---------------------------------------------------------------- node helpers
const say = (who, text, cls) => ({ who, text: f(text), cls });
const parent = t => say('Parent', t, 'parent');
const vet = t => say('Vet', t, 'vet');
const sam = t => say('Sam', t, 'parent');
const hint = (who, t) => say(`${who} (idle hint)`, t, 'hint');
const card = (kind, title, text) => ({ kind, title, text: f(text) });
const good = (t, o = {}) => ({ t: 'outcome', tone: 'good', title: t, ...o });
const bad = (t, o = {}) => ({ t: 'outcome', tone: 'bad', title: t, ...o });
const info = (t, o = {}) => ({ t: 'outcome', tone: 'info', title: t, ...o });
const neutral = (t, o = {}) => ({ t: 'outcome', tone: 'neutral', title: t, ...o });
const act = (t, kids, o = {}) => ({ t: 'action', title: t, kids, ...o });
const dec = (t, o = {}) => ({ t: 'decision', title: t, ...o });
const scene = (t, o = {}) => ({ t: 'scene', title: t, ...o });
const rule = (t, o = {}) => ({ t: 'system', title: t, ...o });
const DOGCARD = 'Did you know?';
const beats = key => CUTSCENES[key].map(b => b.card ? say('Time card', b.card, 'hint') : say(b.face === 'vet' ? 'Vet' : b.face === null ? 'Story' : 'Parent', b.text, b.face === 'vet' ? 'vet' : 'parent'));
const DEMO = 'The first time, a ghost-hand demo shows the move; the ? button replays it.';

// ---------------------------------------------------------------- Level 1, Task 1: Snack Time
const S = LEVEL1.snack, P = LEVEL1.potty;
const snackRounds = S.rounds.map((r, i) => dec(`Round ${i + 1} of 3: ${r.safe.label} or ${r.unsafe.label}`, {
  sub: 'The two foods sit on wooden boards; which side each is on is random. Hovering a food outlines it.',
  lo: ['LO1'],
  kids: [
    act(`Pick ${r.safe.label}`, [good('Safe pick', {
      dog: 'The puppy walks to its bowl, sniffs, eats, then wags and a heart floats up.',
      meter: '+20', lo: ['LO1'],
      cards: [card('good', DOGCARD, r.safe.fact)],
      lines: i < 2 ? [parent(S.next[i])] : [parent(S.done)],
      note: i < 2 ? `Next: round ${i + 2}.` : 'Last round: the “Later that afternoon” cutscene, then Potty Training.',
    })]),
    act(`Pick ${r.unsafe.label}`, [bad('Unsafe pick', {
      dog: 'The puppy sniffs, refuses, and shows a tummy-ache thought bubble. The dog never eats the unsafe food.',
      meter: '−5', lo: ['LO1'],
      cards: [card('bad', DOGCARD, r.unsafe.fact)],
      lines: [parent(S.wrongParent), parent(S.again)],
      note: 'The parent puts it up in the high cupboard (safe storage). The same pair comes back with the sides swapped. A card is never shown twice.',
    })]),
  ],
}));

const snack = {
  id: 'snack', title: 'Level 1, Task 1: Snack Time', nav: 'L1 Snack Time', lo: ['LO1'],
  desc: 'Good food or bad food. Three rounds, each a safe food against an unsafe one. A right pick is rewarded and explained; a wrong pick is a gentle nudge with a safety fact, never a punishment.',
  roots: [dec('Start of the task', {
    sub: `Every line is in a dialogue box that blocks the game until OK. ${DEMO} A yellow arrow points at the counter. Meter drain: 0.25 per second.`,
    lines: [parent(S.intro)], lo: ['LO1'],
    kids: [
      act('Tap the counter', [dec('Counter close-up: three rounds', { sub: 'The first time, a demo shows tapping a food. All three rounds must be right to finish.', lo: ['LO1'], kids: snackRounds })]),
      act('Do nothing for 15 seconds', [info('Idle hint', { lines: [hint('Parent', S.hint)], lo: ['LO1'] })]),
    ],
  })],
};

// ---------------------------------------------------------------- Level 1, Task 2: Potty Training
const A = P.accident;
const accidentKids = A.choices.map(c => act(c.label, [(c.delta > 0 ? good : bad)(c.id === 'scold' ? 'Scolded' : 'Calm clean-up', {
  dog: c.id === 'scold' ? 'The puppy cowers.' : 'The puddle fades away.', meter: (c.delta > 0 ? '+' : '−') + Math.abs(c.delta), lo: ['LO3'],
  cards: [card(c.delta > 0 ? 'good' : 'bad', DOGCARD, c.fact)],
})]));
const spotName = { door: 'the quiet corner by the garden door', middle: 'the middle of the room (the rug)', bowl: 'next to the food bowl' };
const padSpots = P.spots.map(s => act(`Drop the pad ${spotName[s.id]}`, [s.correct
  ? good('Best spot', { meter: '+20', lo: ['LO2'], cards: [card('good', DOGCARD, s.fact)], note: 'Part B starts.' })
  : bad('Poor spot', { meter: '−5', lo: ['LO2'], cards: [card('bad', DOGCARD, s.fact)], note: 'The pad slides back and the player tries again.' })]));
padSpots.push(act('Drop the pad away from all three spots', [neutral('Pad slides back', { note: 'No message and no change to the meter.' })]));
padSpots.push(act('Do nothing for 15 seconds', [info('Idle hint', { lines: [hint('Parent', P.hintPad)], lo: ['LO2'] })]));

const R = P.reward;
const partB = dec('Part B: read the signs and lead the puppy (two successes needed)', {
  sub: 'The puppy wanders for a few seconds, then sniffs the floor and circles. A thought bubble shows a droplet. The treat sits on the counter.',
  lines: [parent(P.introLead)], lo: ['LO2', 'LO3'],
  kids: [
    dec('The puppy sniffs and circles (12 seconds, counted from OK)', {
      sub: `The explanation appears the moment the signs start; the clock starts when it is closed. ${DEMO} A yellow arrow points at the treat.`,
      lines: [parent(P.cue), say('Parent, second time', P.cueAgain, 'parent')], lo: ['LO2'],
      kids: [
        act('Drag the treat and keep holding it so the puppy follows it onto the pad', [
          neutral('The puppy goes potty on the pad', {
            dog: 'It follows the treat, reaches the pad, pees for a moment, then wags with a treat thought bubble.',
            lines: [parent(R.prompt)], lo: ['LO2'],
            kids: [dec('Reward right away', { sub: 'A demo shows dropping the treat on the puppy (first time). The puppy lights up while the treat is over it.', lo: ['LO3'], kids: [
              act('Drop the treat on the puppy', [good('Reward given', {
                dog: 'The puppy eats, wags, and a heart floats up.', meter: '+20', lo: ['LO3'],
                cards: [card('good', R.title, R.fact)],
                note: `The card is shown the first time only. The second time the parent says: “${f(R.again)}”`,
              })]),
              act('Wait 15 seconds', [info('Idle hint', { lines: [hint('Parent', R.prompt)], lo: ['LO3'] })]),
            ] })],
          }),
        ]),
        act('Let go of the treat too early', [neutral('The treat jumps back to the counter', { dog: 'The puppy keeps circling and waits.', note: 'No message. The timer keeps running.', lo: ['LO2'] })]),
        act('Run out of time, or never reach the pad', [bad('Another accident', { dog: 'The puppy pees where it stands.', lines: [parent(A.question)], lo: ['LO3'], kids: accidentKids })]),
      ],
    }),
  ],
});

const potty = {
  id: 'potty', title: 'Level 1, Task 2: Potty Training', nav: 'L1 Potty Training', lo: ['LO2', 'LO3'],
  desc: 'It starts with an accident: the puppy pees on the rug before the player can act. Then place the pad, read the signs, lead the puppy with a treat and reward it right away.',
  roots: [
    scene('“Later that afternoon” cutscene', { lines: beats('afternoon'), lo: ['CTX', 'LO2'] }),
    dec('The accident (no input: the puppy sniffs, circles and pees on the rug)', { lines: [parent(A.question)], lo: ['LO3'], kids: accidentKids }),
    dec('Part A: place the pad', {
      sub: `${DEMO} Three yellow arrows point at the possible spots. The pad lights up when hovered.`, lines: [parent(A.after), parent(P.introPad)], lo: ['LO2'], kids: padSpots,
    }),
    partB,
    good('Task complete (two successes)', {
      lines: [parent(P.done)], cards: [card('info', DOGCARD, P.tip)], lo: ['LO2'],
      note: 'The “That night” cutscene, then the Day 1 album page.',
    }),
  ],
};

// ---------------------------------------------------------------- Level 2, Task 1: Spot the Difference
const SP = LEVEL2.spot, B = LEVEL2.bath;
const diffKids = Object.entries(SP.diffs).map(([id, d]) => act(`Tap the ${SP.names[d.part]}, then the difference in the close-up`, [good(`Found: ${id}`, {
  meter: '+15', lo: ['LO4'], cards: [card('good', 'Found it!', d.fact)],
  note: 'Circled in both close-ups and in the big picture. The counter in the task card goes up.',
})]));
diffKids.push(...Object.entries(SP.decoys).map(([id, line]) => act(`Tap the ${SP.names[id]} (a decoy)`, [neutral('They are the same', { lines: [vet(line)], lo: ['LO4'], note: 'No change to the meter. Back closes the close-up.' })])));
diffKids.push(act('Tap the wrong place in a close-up', [bad('A miss', { meter: '−5 (once per close-up)', lines: [vet(SP.miss), vet(SP.missAgain)], lo: ['LO4'] })]));
diffKids.push(act('Do nothing for 25 seconds', [info('Idle hint', { lines: [hint('Vet', SP.hint.replace('{part}', 'paws'))], lo: ['LO4'], note: 'Names a part that is still unfound.' })]));
const spotTask = {
  id: 'spot', title: 'Level 2, Task 1: Spot the Difference', nav: 'L2 Spot the Difference', lo: ['LO4'],
  desc: 'Two framed pictures: a healthy dog with the right products, and your dog with the grooming bag from home. Hovering a part lights it up in both. Tapping opens both close-ups side by side. Eight differences, three decoys.',
  roots: [
    scene('Level 2 intro cutscene', { lines: beats('l2_intro'), lo: ['CTX', 'LO4'] }),
    dec('Start of the task', { sub: `${DEMO} Meter drain: 0.35 per second.`, lines: [vet(SP.intro)], lo: ['LO4'], kids: diffKids }),
    good('All eight found', { lines: [vet(SP.done)], note: 'The vaccine cutscene, then “That evening”, then Bath Time.', lo: ['LO4'], kids: [scene('Vaccine cutscene', { lines: beats('vaccine'), lo: ['LO4'] })] }),
  ],
};

// ---------------------------------------------------------------- Level 2, Task 2: Bath Time
const bathKids = B.order.map(id => { const it = B.items[id]; return act(`Drag the ${it.name} onto the ${it.part}`, [good('Right place', {
  meter: '+15', lo: ['LO4'], lines: [parent(it.line)],
  note: it.issue ? `The ${it.issue} problem disappears from the dog.` : id === 'shampoo' ? 'Then rub back and forth until the foam is full (a demo shows how).' : 'Then rub the dog dry.',
})]); });
bathKids.push(act('Drop an item on the wrong part', [bad('Wrong part', { meter: '−5', lines: [parent(B.wrong.replace('{item}', 'dog toothbrush').replace('{part}', 'teeth'))], lo: ['LO4'] })]));
bathKids.push(act('Use something too early', [neutral('Not yet', { lines: Object.entries(B.notYet).map(([, l]) => parent(l)), note: 'Teeth, nails and ears on the mat; shampoo in the tub; then the towel; flea drops last, once dry.' })]));
const bathTask = {
  id: 'bath', title: 'Level 2, Task 2: Bath Time', nav: 'L2 Bath Time', lo: ['LO4'],
  desc: 'Each care item is dragged from the shelf onto the right part of the dog; the dog’s problems disappear one by one. The part under the item lights up.',
  roots: [dec('Start of the task', { sub: DEMO, lines: [parent(B.intro)], lo: ['LO4'], kids: bathKids }),
    good('Task complete', { lines: [parent(B.tub), parent(B.scrubbed), parent(B.dried), parent(B.done)], note: 'The Check-up Day album page.', lo: ['LO4'] })],
};

// ---------------------------------------------------------------- Level 3: the walk, Fetch, meeting Sam
const Wk = LEVEL3.walk, F = LEVEL3.fetch, G = LEVEL3.greet;
const walkTask = {
  id: 'walk', title: 'Level 3: the walk to the park', nav: 'L3 Walk', lo: ['LO3'],
  desc: 'Hold to walk, let go to stop. Three distractions (a squirrel, a dropped sandwich, a cat). Not a graded task: it introduces leash manners.',
  roots: [scene('Level 3 intro cutscene', { lines: beats('l3_intro'), lo: ['CTX'] }),
    dec('Walking (hold anywhere)', { sub: `${DEMO} Meter drain: 0.45 per second. No pointer cues and no timed hints in Level 3.`, lines: [parent(Wk.intro)], lo: ['LO3'], kids: [
      act('Let go when the dog lunges', [good('Good stop', { meter: '+10', dog: 'The dog sits and the leash goes loose.', lines: [parent(Wk.stopped)], lo: ['LO3'] })]),
      act('Keep holding while it pulls', [bad('Dragged ahead', { meter: '−5', cards: [card('bad', Wk.pulled.title, Wk.pulled.fact)], lines: [parent(Wk.pulledAgain)], lo: ['LO3'] })]),
    ] }),
    good('At the park gate', { lines: [parent(Wk.done), ...beats('park')], lo: ['CTX'] })],
};
const fetchTask = {
  id: 'fetch', title: 'Level 3, Task 1: Fetch & Exercise', nav: 'L3 Fetch', lo: ['LO6'],
  desc: `Drag the ball back and let go to throw. After ${F.tiredAfter} fetches the dog pants and slows down; nothing on screen points this out.`,
  roots: [dec('Playing fetch', { sub: DEMO, lines: [parent(F.intro)], lo: ['LO6'], kids: [
    act('Throw the ball', [good('A fetch', { meter: '+10', dog: 'The dog runs, brings the ball back and drops it. From the fourth fetch it pants; the fifth is slow.', lo: ['LO6'] })]),
    act('Keep throwing while it pants', [bad('The dog flops down', { meter: '−5', dog: 'It lies down instead of fetching, with a hot thought bubble.', cards: [card('bad', F.flop.title, F.flop.fact)], lines: [parent(F.flopLine)], note: 'A demo shows the rest response.', lo: ['LO6'] })]),
    act('Tap the shady tree (once tired)', [good('Rest in the shade', { meter: '+15', lines: [parent(F.shade)], lo: ['LO6'] })]),
    act('Drag the water bowl to the dog (once tired)', [good('A drink', { meter: '+15', lines: [parent(F.water)], lo: ['LO6'] })]),
    act('Shade or water before it is tired', [neutral('Not yet', { lines: [parent(F.tooSoon)] })]),
  ] }),
  good('Rested and watered', { cards: [card('info', F.tip.title, F.tip.fact)], lines: [parent(F.done)], note: 'The “A little later” card, then Sam arrives.', lo: ['LO6'] })],
};
const S2 = G.step2;
const greetTask = {
  id: 'greet', title: 'Level 3, Task 2: Meeting a new friend', nav: 'L3 New friend', lo: ['LO7'],
  desc: 'Sam asks to pet the dog. Three steps; in one of two random variants the dog shows stress signals (whale eye, lip licking, yawning, tucked tail) and the right answer changes.',
  roots: [dec('Step 1: Sam runs over', { lines: [sam(G.hello), parent(G.step1.question)], lo: ['LO7'], kids: [
      act(G.step1.choices[0].label, [bad('Too fast', { meter: '−5', dog: 'The dog gets nervous.', cards: [card('bad', DOGCARD, G.step1.bad)], lines: [parent(G.step1.again)], lo: ['LO7'] })]),
      act(G.step1.choices[1].label, [good('A calm approach', { meter: '+15', cards: [card('good', DOGCARD, G.step1.good)], lines: [sam(G.step1.samSlow)], lo: ['LO7'] })]),
    ] }),
    dec('Step 2: read the dog (calm variant: a loose wag)', { lines: [parent(S2.question)], sub: 'The question sits top-left so the dog stays in view.', lo: ['LO7'], kids: [
      act(f(S2.choices[0].label), [bad('Too soon', { meter: '−5', cards: [card('bad', DOGCARD, S2.calm.pet)], lo: ['LO7'] })]),
      act(f(S2.choices[1].label), [good('A sniff hello', { meter: '+15', lines: [sam(S2.samSniff)], cards: [card('good', DOGCARD, S2.calm.sniff)], lo: ['LO7'] })]),
      act(f(S2.choices[2].label), [neutral('No is always OK, but look again', { lines: [parent(S2.calm.space)], lo: ['LO7'] })]),
    ] }),
    dec('Step 2: read the dog (stressed variant)', { lines: [parent(S2.question)], lo: ['LO7'], kids: [
      act(f(S2.choices[0].label), [bad('Not now', { meter: '−5', cards: [card('bad', DOGCARD, S2.stressed.pet)], lo: ['LO7'] })]),
      act(f(S2.choices[1].label), [bad('Not even a sniff', { meter: '−5', cards: [card('bad', DOGCARD, S2.stressed.sniff)], lo: ['LO7'] })]),
      act(f(S2.choices[2].label), [good('Space', { meter: '+15', cards: [card('good', f(S2.stressed.title), S2.stressed.space)], lines: [sam(S2.samBye)], lo: ['LO7'] })]),
    ] }),
    dec('Step 3 (calm variant): drag Sam’s hand onto the dog', { sub: `${DEMO} The part under the hand lights up.`, lines: [parent(G.step3.prompt)], lo: ['LO7'], kids: [
      act('Over the head', [bad('The dog ducks', { meter: '−5', cards: [card('bad', DOGCARD, G.step3.head)], lines: [parent(G.step3.headAgain)], lo: ['LO7'] })]),
      act('Side of the neck or chest', [good('A happy dog', { meter: '+15', cards: [card('good', DOGCARD, G.step3.chest)], lines: [sam(G.step3.samHappy)], lo: ['LO7'] })]),
    ] }),
    good('Both sides of the lesson', { cards: [card('info', G.both.title, G.both.fact)], note: 'Then “That evening”, the Park Day album page and the finale.', lo: ['LO7'] })],
};

// ---------------------------------------------------------------- Start, level select, albums and growth
const setup = {
  id: 'setup', title: 'Start: level select, the story and the dog', nav: 'Start and setup', lo: ['CTX'],
  desc: 'Title, then a cork-board level select (every level is open). Level 1’s story names the puppy halfway through; Levels 2 and 3 ask for a dog first if none was adopted yet.',
  roots: [dec('Level select', { lo: ['CTX'], kids: [
    act('Level 1', [scene('The story so far', { lines: beats('l1_intro'), lo: ['CTX'], kids: [dec('Dog setup', {
      sub: 'Three coat swatches, a name with an on-screen keyboard, Random and Adopt!', lo: ['CTX'], kids: [
        act('Tap Random', [neutral('A random name', { note: `One of ${DOG_NAMES.length}: ${DOG_NAMES.join(', ')}.` })]),
        act('Tap Adopt!', [scene('Bringing the puppy home', { lines: beats('l1_home'), lo: ['CTX', 'LO1', 'LO2'] })]),
      ] })] })]),
    act('Level 2 or 3', [neutral('The level’s own intro cutscene', { note: 'Dog setup first if no dog was adopted yet.' })]),
    act('Change dog', [neutral('Dog setup, then back to the level select')]),
  ] })],
};

const milestones = {
  id: 'albums', title: 'Album pages, growth and the finale', nav: 'Albums and growth', lo: ['LO1', 'LO2', 'LO4', 'LO6', 'LO7'],
  desc: 'After each level the player sees what they learned on a photo-album page, then the dog grows up. A “Pawfect!” stamp appears when the whole level had no wrong answer.',
  roots: [
    scene('After Level 1: “' + LEVEL1.album.title + '”', { sub: 'You learned: ' + LEVEL1.album.skills.map(s => s.label).join(' and ') + '.', lo: ['LO1', 'LO2'],
      kids: [scene('Growth: puppy to young dog', { lines: beats('growth1'), lo: ['CTX'] })] }),
    scene('After Level 2: “' + LEVEL2.album.title + '”', { sub: 'You learned: ' + LEVEL2.album.skills.map(s => s.label).join(' and ') + '.', lo: ['LO4'],
      kids: [scene('Growth: young dog to adult', { lines: beats('growth2'), lo: ['CTX'] })] }),
    scene('After Level 3: “' + LEVEL3.album.title + '”', { sub: 'You learned: ' + LEVEL3.album.skills.map(s => s.label).join(' and ') + '.', lo: ['LO6', 'LO7'],
      kids: [scene('Finale: “You’re a Pawfect Parent!”', { lines: beats('l3_end'), note: 'An album spread with a photo from each level, then Level select or Back to title.', lo: ['CTX'] })] }),
  ],
};

// ---------------------------------------------------------------- Game rules that apply to every task
const retries = [LEVEL1.retry.snack, LEVEL1.retry.potty, LEVEL2.retry.spot, LEVEL2.retry.bath, LEVEL3.retry.walk, LEVEL3.retry.fetch, LEVEL3.retry.greet];
const rules = {
  id: 'rules', title: 'Rules that apply everywhere: dialogue, demos, meter, hints, retry and pause', nav: 'Meter, hints, retry', lo: ['LO1', 'LO2', 'LO3', 'LO4', 'LO6', 'LO7'],
  desc: 'Dialogue boxes block the game until OK. Every new move gets a ghost-hand demo the first time (the ? button replays it). Things that can be tapped or dropped on light up under the pointer. Running out of meter never ends the game: the task restarts.',
  roots: [rule('Happiness meter', {
    sub: 'Starts each task at 80 of 100. Drains 0.25, 0.35 and 0.45 per second in Levels 1, 2 and 3. Paused while any dialogue, card, choice, demo or the pause menu is open.',
    kids: [
      act('The meter reaches 0', [bad('Retry screen', { dog: 'The scene greys out and the sad dog lies in a spotlight; Try again restarts that task only.', lines: retries.map(parent), lo: ['LO1', 'LO2', 'LO4', 'LO6', 'LO7'] })]),
      act('The player waits without progress', [info('Idle hints', { lines: [hint('Level 1, after 15 s', S.hint), hint('Level 1, after 15 s', P.hintPad), hint('Level 1, after 15 s', P.hintLead),
        hint('Level 2, after 25 s', SP.hint.replace('{part}', 'ears')), hint('Level 2, after 25 s', B.hint)], note: 'Level 3 has no timed hints: help comes only after a wrong action.' })]),
      act('The player taps the pause button', [dec('Pause menu', { kids: [act('Resume', [neutral('Back to the task')]), act('Sound on or off', [neutral('The sound is toggled')]),
        act('Level select', [neutral('Back to the cork board')]), act('Quit to title', [neutral('Back to the title screen')])] })]),
    ],
  })],
};

// ---------------------------------------------------------------- overview flow
const sections = [
  { id: 'overview', title: 'How a play-through flows', desc: 'Click a step to jump to its decision tree. Each tree reads from left to right: a decision point, what the player can do, and what the game says back, with the learning objective (LO) each answer serves.',
    flow: [
      { title: 'Title and level select', sub: 'Every level is open', lo: ['CTX'], go: 'setup' },
      { title: 'Story: Puppy Day', sub: 'Name the puppy at the rescue', lo: ['CTX'], go: 'setup' },
      { title: 'Level 1, Task 1: Snack Time', sub: 'Safe or unsafe food, 3 rounds', lo: ['LO1'], go: 'snack' },
      { title: 'Level 1, Task 2: Potty Training', sub: 'An accident, the pad, lead, reward', lo: ['LO2', 'LO3'], go: 'potty' },
      { title: 'Album and growth', sub: 'Puppy becomes a young dog', lo: ['LO1', 'LO2'], go: 'albums' },
      { title: 'Level 2, Task 1: Spot the Difference', sub: 'Eight differences at the vet', lo: ['LO4'], go: 'spot' },
      { title: 'Level 2, Task 2: Bath Time', sub: 'The right care on the right part', lo: ['LO4'], go: 'bath' },
      { title: 'Album and growth', sub: 'Young dog becomes an adult', lo: ['LO4'], go: 'albums' },
      { title: 'Level 3: the walk', sub: 'Stop when the dog pulls', lo: ['LO3'], go: 'walk' },
      { title: 'Level 3, Task 1: Fetch', sub: 'Notice the panting, rest, water', lo: ['LO6'], go: 'fetch' },
      { title: 'Level 3, Task 2: A new friend', sub: 'Read the dog, greet safely', lo: ['LO7'], go: 'greet' },
      { title: 'Album and finale', sub: 'You’re a Pawfect Parent!', lo: ['LO6', 'LO7'], go: 'albums' },
      { title: 'Rules in every task', sub: 'Dialogue, demos, meter, retry', lo: [], go: 'rules' },
    ] },
  setup, snack, potty, spotTask, bathTask, walkTask, fetchTask, greetTask, milestones, rules,
];

// ---------------------------------------------------------------- write the HTML
const count = n => 1 + (n.kids || []).reduce((a, k) => a + count(k), 0);
const total = sections.filter(s => s.roots).reduce((a, s) => a + s.roots.reduce((b, r) => b + count(r), 0), 0);
const data = {
  intro: 'Every action a player can take in Levels 1 to 3, what the game says or shows in reply, and the learning objective each reply serves. The dog is called ' + NAME + ' here; in the game it is the name the player chose. Built from the game’s own text, so it matches what players see.',
  foot: `Generated ${new Date().toISOString().slice(0, 10)} by tools/decision_tree/build.mjs from src/content.js (${total} boxes). Learning objectives are defined in GAME_DESIGN.md section 1.2. Meter changes are in points on a 0 to 100 scale.`,
  los: LOS, sections,
};
const template = readFileSync(path.join(HERE, 'template.html'), 'utf8');
const json = JSON.stringify(data).replace(/</g, '\\u003c').replace(/\u2028|\u2029/g, '');
mkdirSync(OUT, { recursive: true });
const htmlPath = path.join(OUT, BASE + '.html');
writeFileSync(htmlPath, template.replace('/*DATA*/', () => json));
console.log(`html: ${htmlPath} (${total} boxes)`);

// ---------------------------------------------------------------- render PNG and PDF with headless Chrome / Edge
const browsers = ['C:/Program Files/Google/Chrome/Application/chrome.exe', 'C:/Program Files (x86)/Google/Chrome/Application/chrome.exe',
  'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe', 'C:/Program Files/Microsoft/Edge/Application/msedge.exe',
  '/usr/bin/google-chrome', '/usr/bin/chromium', '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'];
const exe = browsers.find(existsSync);
if (!exe || process.argv.includes('--html-only')) { console.log('skipped PNG and PDF (no Chrome or Edge found, or --html-only)'); process.exit(0); }
const url = q => pathToFileURL(htmlPath).href + q;
const run = args => execFileSync(exe, ['--headless=new', '--disable-gpu', '--hide-scrollbars', '--no-sandbox', '--allow-file-access-from-files',
  '--virtual-time-budget=10000', ...args], { encoding: 'utf8', maxBuffer: 1 << 28, stdio: ['ignore', 'pipe', 'pipe'] });

const dom = run(['--window-size=2400,1200', '--dump-dom', url('?static')]);
const m = dom.match(/<title>M:(\{.*?\})<\/title>/);
if (!m) { console.error('could not measure the page'); process.exit(1); }
const { w, h, total: pageH } = JSON.parse(m[1]);
console.log(`measured: width ${w}, tallest section ${h}, whole page ${pageH}`);
run([`--window-size=${w + 40},${pageH + 40}`, `--screenshot=${path.join(OUT, BASE + '.png')}`, url('?static')]);
console.log('png ok');
run([`--print-to-pdf=${path.join(OUT, BASE + '.pdf')}`, '--no-pdf-header-footer', url('?static&print')]);
console.log('pdf ok');
