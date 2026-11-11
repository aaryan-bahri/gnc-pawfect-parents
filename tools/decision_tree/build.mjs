// Builds the player decision tree (Levels 1 and 2) from the game's own text in src/content.js.
//   node tools/decision_tree/build.mjs
// Writes docs/decision_tree/pawfect_parents_decision_tree.{html,png,pdf}. The PNG and PDF are rendered by headless Chrome/Edge
// from the same page (static mode), so all three always match the game text.
import { readFileSync, writeFileSync, mkdirSync, existsSync } from 'node:fs';
import { execFileSync } from 'node:child_process';
import { fileURLToPath, pathToFileURL } from 'node:url';
import path from 'node:path';
import { LEVEL1, LEVEL2, CUTSCENES, fill, DOG_NAMES } from '../../src/content.js';

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
  { id: 'LO4', short: 'LO4 Health checks', text: 'Check basic health signs (teeth, ears, coat, nails) and link each one to the right care' },
  { id: 'LO5', short: 'LO5 Needs and budget', text: 'Buy what a pet actually needs within a budget and a time limit' },
  { id: 'CTX', short: 'Context / empathy', text: 'Story, naming the dog and caring for it: motivation rather than a taught fact' },
];

// ---------------------------------------------------------------- node helpers
const say = (who, text, cls) => ({ who, text: f(text), cls });
const parent = t => say('Parent', t, 'parent');
const vet = t => say('Vet', t, 'vet');
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

// ---------------------------------------------------------------- Level 1, Task 1: Snack Time
const S = LEVEL1.snack, P = LEVEL1.potty;
const snackRounds = S.rounds.map((r, i) => dec(`Round ${i + 1} of 3: ${r.safe.label} or ${r.unsafe.label}`, {
  sub: 'The two foods sit on wooden boards; which side each is on is random.',
  lo: ['LO1'],
  kids: [
    act(`Pick ${r.safe.label}`, [good('Safe pick', {
      dog: 'The puppy walks to its bowl, sniffs, eats, then wags (happy chime).',
      meter: '+20', lo: ['LO1'],
      cards: [card('good', DOGCARD, r.safe.fact)],
      lines: i < 2 ? [] : [parent(S.done)],
      note: i < 2 ? `Next: round ${i + 2}. Parent: \u201C${f(S.next[i])}\u201D` : 'That was the last round: Potty Training starts.',
    })]),
    act(`Pick ${r.unsafe.label}`, [bad('Unsafe pick', {
      dog: 'The puppy sniffs, refuses, and shows a tummy-ache thought bubble. The dog never eats the unsafe food.',
      meter: '\u22125', lo: ['LO1'],
      cards: [card('bad', DOGCARD, r.unsafe.fact)],
      lines: [parent(S.wrongParent)],
      note: `The parent puts it up in the high cupboard (safe storage). The same pair comes back with the sides swapped. Parent: \u201C${f(S.again)}\u201D. If the same wrong food is picked again, the card is not shown twice.`,
    })]),
  ],
}));

const snack = {
  id: 'snack', title: 'Level 1, Task 1: Snack Time', nav: 'L1 Snack Time', lo: ['LO1'],
  desc: 'Good food or bad food. Three rounds, each a safe food against an unsafe one. A right pick is rewarded and explained; a wrong pick is a gentle nudge with a safety fact, never a punishment.',
  roots: [dec('Start of the task', {
    sub: 'The puppy sits by its bowl with a bowl thought bubble. A yellow arrow points at the kitchen counter. Meter drain: 0.25 per second.',
    lines: [parent(S.intro)], lo: ['LO1'],
    kids: [
      act('Tap the counter', [dec('Counter close-up: three rounds', { sub: 'The player must get all three rounds right to finish.', lo: ['LO1'], kids: snackRounds })]),
      act('Do nothing for 15 seconds', [info('Idle hint', { lines: [hint('Parent', S.hint)], lo: ['LO1'] })]),
    ],
  })],
};

// ---------------------------------------------------------------- Level 1, Task 2: Potty Training
const spotName = { door: 'the quiet corner by the garden door', middle: 'the middle of the room (the rug)', bowl: 'next to the food bowl' };
const padSpots = P.spots.map(s => act(`Drop the pad ${spotName[s.id]}`, [s.correct
  ? good('Best spot', { meter: '+20', lo: ['LO2'], cards: [card('good', DOGCARD, s.fact)], note: 'Part B starts.' })
  : bad('Poor spot', { meter: '\u22125', lo: ['LO2'], cards: [card('bad', DOGCARD, s.fact)], note: 'The pad slides back and the player tries again. If the same wrong spot is chosen again, the card is not repeated.' })]));
padSpots.push(act('Drop the pad away from all three spots', [neutral('Pad slides back', { note: 'No message and no change to the meter.' })]));
padSpots.push(act('Do nothing for 15 seconds', [info('Idle hint', { lines: [hint('Parent', P.hintPad)], lo: ['LO2'] })]));

const R = P.reward;
const partB = dec('Part B: read the signs and lead the puppy (two successes needed)', {
  sub: 'The puppy wanders for a few seconds, then sniffs the floor and circles. A thought bubble shows a droplet. The treat sits on the counter.',
  lines: [parent(P.introLead)], lo: ['LO2', 'LO3'],
  kids: [
    dec('The puppy sniffs and circles (12 second window)', {
      sub: 'The explanation appears the moment the signs start, whatever the player is doing. A yellow arrow points at the treat.',
      lines: [parent(P.cue), say('Parent, second time', P.cueAgain, 'parent')], lo: ['LO2'],
      kids: [
        act('Drag the treat and keep holding it so the puppy follows it onto the pad', [
          neutral('The puppy goes potty on the pad', {
            dog: 'It follows the treat, reaches the pad, pees for a moment, then wags with a treat thought bubble.',
            lines: [parent(R.prompt)], lo: ['LO2'],
            kids: [dec('Reward right away', { sub: 'A yellow arrow points at the puppy.', lo: ['LO3'], kids: [
              act('Drop the treat on the puppy', [good('Reward given', {
                dog: 'The puppy eats, wags, and a heart floats up.', meter: '+20', lo: ['LO3'],
                cards: [card('good', R.title, R.fact)],
                note: `The card is shown the first time only. The second time the parent says: \u201C${f(R.again)}\u201D`,
              })]),
              act('Wait 15 seconds', [info('Idle hint', { lines: [hint('Parent', R.prompt)], lo: ['LO3'] })]),
            ] })],
          }),
        ]),
        act('Let go of the treat too early', [neutral('The treat jumps back to the counter', { dog: 'The puppy keeps circling and waits.', note: 'No message. The 12 second timer keeps running.', lo: ['LO2'] })]),
        act('Do nothing for 15 seconds', [info('Idle hint', { lines: [hint('Parent', P.hintLead)], lo: ['LO2'] })]),
        act('Run out of time (12 seconds), or never reach the pad', [bad('An accident on the floor', {
          dog: 'The puppy pees on the floor and a small puddle appears.', lo: ['LO3'],
          lines: [parent(P.tooLate.question)],
          kids: P.tooLate.choices.map(c => act(c.label, [(c.delta > 0 ? good : bad)(c.id === 'scold' ? 'Scolded' : 'Calm clean-up', {
            dog: c.id === 'scold' ? 'The puppy cowers.' : 'The puddle fades away.', meter: (c.delta > 0 ? '+' : '\u2212') + Math.abs(c.delta), lo: ['LO3'],
            cards: [card(c.delta > 0 ? 'good' : 'bad', DOGCARD, c.fact)],
            note: 'The sniffing and circling starts again.',
          })])),
        })]),
      ],
    }),
  ],
});

const potty = {
  id: 'potty', title: 'Level 1, Task 2: Potty Training', nav: 'L1 Potty Training', lo: ['LO2', 'LO3'],
  desc: 'Place the pad, then read the puppy\u2019s signs and lead it with a treat, and reward it right away. This is where positive reinforcement is taught, and where scolding is shown not to work.',
  roots: [
    dec('Part A: place the pad', {
      sub: 'Three yellow arrows point at the possible spots. The pad can be dragged.', lines: [parent(P.introPad)], lo: ['LO2'], kids: padSpots,
    }),
    partB,
    good('Task complete (two successes)', {
      lines: [parent(P.done)], cards: [card('info', DOGCARD, P.tip)], lo: ['LO2'],
      note: 'The meter fills and the Day 1 album page appears.',
    }),
  ],
};

// ---------------------------------------------------------------- Level 2, Task 1: Help the Vet
const V = LEVEL2.vet, SH = LEVEL2.shop, ITEMS = SH.items;
const nm = id => ITEMS[id].name;
const spotKids = V.spots.map(s => act(`Tap ${s.label} (the ring on the dog or the label)`, [good(`Close-up: ${s.label.toLowerCase()}`, {
  dog: 'A magnifying-glass close-up opens. The meter is paused while it is open.',
  lines: [vet(s.say)], lo: ['LO4'],
  note: `${s.items.map(nm).join(' and ')} fly onto the shopping list.${s.id === 'teeth' ? ' The pointer arrow is only on this first spot.' : ''}`,
})]));

const vetTask = {
  id: 'vet', title: 'Level 2, Task 1: Help the Vet', nav: 'L2 Help the Vet', lo: ['LO4'],
  desc: 'Four health checks, in any order. Each finding is explained by the vet and becomes an item on the shopping list. The player can also calm the nervous dog.',
  roots: [
    scene('Level 2 intro cutscene', { lines: CUTSCENES.level2.map(p => parent(p.text)), lo: ['CTX', 'LO4', 'LO5'], note: 'The parent sets the plan: a check-up, then shopping for what the vet says is needed.' }),
    dec('Start of the task', {
      sub: 'A sky-blue clinic. The dog is on the exam table with its ears back and tail tucked. Four spots glow. Meter drain: 0.35 per second.',
      lines: [vet(V.intro)], lo: ['LO4'],
      kids: [
        ...spotKids,
        act('Tap the dog (once between checks)', [good('A calming pat', {
          dog: 'The dog wags and a heart floats up.', meter: '+5', lo: ['CTX'],
          lines: [vet(V.patDone)], note: `After the first check the vet reminds the player: \u201C${f(V.pat)}\u201D. Only one pat counts per gap between checks. This introduces reading a dog\u2019s stress, which comes back in Level 3.`,
        })]),
        act('Do nothing for 25 seconds', [info('Idle hint', { lines: [hint('Vet', V.hint)], lo: ['LO4'] })]),
        act('Finish all four checks', [good('Check-up complete', {
          lines: [vet(V.done)], lo: ['LO4'],
          note: 'The shopping list now has five items: Dog toothbrush, Dog toothpaste, Flea treatment (dog), Nail clippers and Ear cleaner (dog).',
          kids: [scene('Vaccine cutscene', { lines: [say('Vet', CUTSCENES.vaccine[0].text, 'vet')], lo: ['LO4'], note: 'A vaccine is a story beat, not an item to buy: only a vet can give one.' })],
        })]),
      ],
    }),
  ],
};

// ---------------------------------------------------------------- Level 2, Task 2: Pet Store Run
const byKind = (kind, from) => Object.entries(ITEMS).filter(([, v]) => v.kind === kind && (!from || v.from === from));
const listNames = ids => ids.map(([, v]) => v.name).join(', ');
const parentNeeds = byKind('need', 'parent'), vetNeeds = byKind('need', 'vet'), wants = byKind('want'), wrongs = byKind('wrong');
const aisleText = SH.aisles.map(a => `${a.name}: ${a.rows.flat().map(nm).join(', ')}`).join('. ');

const itemKids = [
  act('Tap \u201CNot now\u201D', [neutral('The card closes', { note: 'Nothing changes.' })]),
  act(`Tap \u201CAdd\u201D on a vet need (${listNames(vetNeeds)})`, [good('A need from the vet', {
    dog: 'The item flies into the basket and its box on the paper list gets a tick.', meter: '+10', lo: ['LO5', 'LO4'],
    note: 'The +10 is given once per item, so taking an item out and back in cannot be farmed. No card: the vet already explained why at the clinic.',
  })]),
  act(`Tap \u201CAdd\u201D on a need the parent added (${listNames(parentNeeds)})`, [good('A need from the parent', {
    dog: 'The item flies into the basket and its box on the paper list gets a tick.', meter: '+10', lo: ['LO5'],
    cards: parentNeeds.map(([, v]) => card('good', `${v.name}: ${DOGCARD}`, v.fact)),
    note: 'One card per item, shown the first time that item is bought.',
  })]),
  act(`Tap \u201CAdd\u201D on a want (${listNames(wants)})`, [
    neutral('A want, with enough coins left for the needs', {
      meter: '', lo: ['LO5'], dog: 'The item goes in the basket. Wants are never wrong and give no points.',
      cards: [card('info', 'Looking good!', SH.wantFact)], note: 'The card is shown for the first want only.',
    }),
    bad('A want that would leave too little for the needs', {
      meter: '\u22125', lo: ['LO5'], dog: 'The item flies to the basket and straight back to the shelf. Nothing is charged.',
      cards: [card('bad', SH.nudge.title, SH.nudge.fact)],
      lines: [parent(SH.nudge.again)], note: 'The card is shown once. After that the parent says the short line instead.',
    }),
  ]),
  act(`Tap \u201CAdd\u201D on a look-alike (${listNames(wrongs)})`, [bad('The wrong item', {
    meter: '\u22125', lo: ['LO5', 'LO4'], dog: 'The item flies to the basket and straight back to the shelf. Nothing is charged.',
    cards: wrongs.map(([, v]) => card('bad', `${v.name}: ${SH.wrongTitle}`, v.fact)),
    lines: [parent(SH.wrongAgain)], note: 'One card per item, shown once. After that the parent says the short line instead.',
  })]),
  act('Tap \u201CAdd\u201D on something that costs more than the coins left', [neutral('Not enough coins', { lines: [parent(SH.tooMuch)], lo: ['LO5'], note: 'The card already warned \u201CNot enough coins\u201D in red.' })]),
];

const shopTask = {
  id: 'shop', title: 'Level 2, Task 2: Pet Store Run', nav: 'L2 Pet Store', lo: ['LO5', 'LO4'],
  desc: `Shopping with a budget of ${SH.budget} coins and a ticking meter. The nine needs cost ${vetNeeds.concat(parentNeeds).reduce((a, [, v]) => a + v.price, 0)} coins, so there is room for a want or two, but not for everything. Look-alike items test what the vet taught.`,
  roots: [
    dec('Start of the task', {
      sub: `A lavender store with four aisles. ${aisleText}. The meter is paused during the parent\u2019s introduction. Meter drain: 0.35 per second.`,
      lines: [parent(SH.intro), parent(SH.parent)], lo: ['LO5'],
      note: `The parent writes four more lines on the paper list (${parentNeeds.map(([, v]) => v.name).join(', ')}) and hands over ${SH.budget} coins. Tips from the parent hide after a few seconds so they never cover the shelves.`,
      kids: [
        act('Tap an arrow', [neutral('The shelves slide to the next aisle', { note: 'Health, Grooming, Play & Walk, Home & Style, then round again.' })]),
        act('Tap an item on a shelf', [dec('Item card: name, price, and the coins left after buying', { lo: ['LO5'], kids: itemKids })]),
        act('Tap the basket', [dec('Basket panel', { sub: 'Everything bought so far, and the total.', lo: ['LO5'], kids: [
          act('Tap an item in the basket', [neutral('Put it back', { dog: 'The coins are refunded and the tick on the list is removed.', lo: ['LO5'] })]),
          act('Tap \u201CKeep shopping\u201D', [neutral('The panel closes')]),
          act('Tap \u201CCheckout\u201D', [dec('Checkout', { lo: ['LO5', 'LO4'], kids: [
            act('Some needs are still not in the basket', [info('Not yet', { lines: [parent(SH.missing)], lo: ['LO5'] })]),
            act('All nine needs are in the basket', [good('The till: each item is explained, one by one', {
              dog: 'Each item appears on the counter and the parent says why it was bought. A tap moves on.', lo: ['LO5', 'LO4'],
              lines: [...vetNeeds.concat(parentNeeds).map(([, v]) => parent(v.why)), parent(SH.tillWant), parent(SH.tillDone)],
              note: 'The \u201Ca little extra\u201D line is only said for wants in the basket. The meter then fills and the \u201CCheck-up Day\u201D album page appears.',
            })]),
          ] })]),
        ] })]),
        act('Put every need in the basket', [info('Everything is on the list', { lines: [parent(SH.allDone)], lo: ['LO5'] })]),
        act('Do nothing for 25 seconds', [info('Idle hint', { lines: [hint('Parent', SH.hint)], lo: ['LO5'] })]),
      ],
    }),
  ],
};

// ---------------------------------------------------------------- Setup, albums and growth
const setup = {
  id: 'setup', title: 'Start: dog setup and the opening cutscene', nav: 'Start and setup', lo: ['CTX', 'LO1', 'LO2'],
  desc: 'The player names and chooses their dog before anything is taught, so that they care what happens to it. Then a four-panel story sets up the first two skills.',
  roots: [dec('Dog setup screen', {
    sub: 'A puppy wagging on a rug, three coat swatches, a name field with an on-screen keyboard (a real keyboard works too), a Random button and Adopt!.',
    lo: ['CTX'],
    kids: [
      act('Tap a coat swatch (cream, caramel or chocolate)', [neutral('The puppy changes colour', { dog: 'The puppy wags in the new coat and a wag sound plays. The whole game uses this coat.', lo: ['CTX'] })]),
      act('Type a name (up to 10 letters)', [neutral('The name appears', { dog: 'The first key replaces the suggested name. The first letter is a capital, the rest are lowercase.', lo: ['CTX'] })]),
      act('Tap Random', [neutral('A random name', { note: `One of ${DOG_NAMES.length}: ${DOG_NAMES.join(', ')}.`, lo: ['CTX'] })]),
      act('Tap Adopt!', [scene('Opening cutscene (4 panels, tap to continue, Skip is available)', {
        lines: CUTSCENES.opening.map(p => parent(p.text)),
        note: 'Panels: the drive home, arriving at the porch, the PUPPY JOBS chart on the fridge, and the puppy\u2019s new things. If the name is empty, a random name is used. Level 1 starts next.',
        lo: ['CTX', 'LO1', 'LO2'],
      })]),
    ],
  })],
};

const milestones = {
  id: 'albums', title: 'Album pages and growth cutscenes', nav: 'Albums and growth', lo: ['LO1', 'LO2', 'LO4', 'LO5'],
  desc: 'After each level the player sees what they learned on a photo-album page, then the dog grows up. A \u201CPawfect!\u201D stamp appears when the whole level had no wrong answer.',
  roots: [
    scene('After Level 1: album page \u201C' + LEVEL1.album.title + '\u201D', {
      sub: 'You learned: ' + LEVEL1.album.skills.map(s => s.label).join(' and ') + '.', lo: ['LO1', 'LO2'],
      note: 'The skills are ticked one at a time. No wrong answers in the whole level gives the Pawfect! stamp; otherwise it says how many slips there were and that this is how we learn.',
      kids: [scene('Growth cutscene: puppy to young dog', { lines: [parent(CUTSCENES.growth1[0].text)], note: 'Leads to the Level 2 intro cutscene.', lo: ['CTX'] })],
    }),
    scene('After Level 2: album page \u201C' + LEVEL2.album.title + '\u201D', {
      sub: 'You learned: ' + LEVEL2.album.skills.map(s => s.label).join(' and ') + '.', lo: ['LO4', 'LO5'],
      note: 'Same rules as Level 1.',
      kids: [scene('Growth cutscene: young dog to adult', { lines: [parent(CUTSCENES.growth2[0].text)], note: 'Then the end card: \u201CThanks for playing!\u201D. Level 3 (the park) is not built yet.', lo: ['CTX'] })],
    }),
  ],
};

// ---------------------------------------------------------------- Game rules that apply to every task
const rules = {
  id: 'rules', title: 'Rules that apply everywhere: meter, hints, retry and pause', nav: 'Meter, hints, retry', lo: ['LO1', 'LO2', 'LO3', 'LO4', 'LO5'],
  desc: 'The happiness meter is a soft timer and the feedback: right actions raise it, wrong actions only nudge it down. Help fades as the levels go on. Running out of meter never ends the game: the task restarts with a hint.',
  roots: [rule('Happiness meter', {
    sub: 'Starts each task at 80 of 100. Drains 0.25 per second in Level 1 and 0.35 per second in Level 2. It is paused while a card, a close-up, a choice or the pause menu is open, so reading never costs anything. Green above 60, yellow from 30 to 60, red below 30.',
    kids: [
      act('The meter reaches 0', [bad('Retry screen', {
        dog: 'The scene greys out, the sad dog lies in a spotlight, the parent explains what was needed, and a Try again button restarts that task only.',
        lo: ['LO1', 'LO2', 'LO4', 'LO5'],
        lines: [parent(LEVEL1.retry.snack), parent(LEVEL1.retry.potty), parent(LEVEL2.retry.vet), parent(LEVEL2.retry.shop)],
        note: 'In order: Snack Time, Potty Training, Help the Vet, Pet Store Run. A retry shows the hint straight away, and facts already seen are not shown again.',
      })]),
      act('The player waits without progress', [info('Idle hints', {
        lo: ['LO1', 'LO2', 'LO3', 'LO4', 'LO5'],
        lines: [hint('Level 1, after 15 s', S.hint), hint('Level 1, after 15 s', P.hintPad), hint('Level 1, after 15 s', P.hintLead),
          hint('Level 2, after 25 s', V.hint), hint('Level 2, after 25 s', SH.hint)],
        note: 'Level 1 shows pointer arrows on what matters. Level 2 has only one arrow, on the first spot at the vet. The hint timer restarts after every action and does not run while the meter is paused.',
      })]),
      act('The player taps the pause button', [dec('Pause menu', { kids: [
        act('Resume', [neutral('Back to the task', { note: 'Everything is frozen while paused, including the meter and timers.' })]),
        act('Sound on or off', [neutral('The sound is toggled')]),
        act('Quit to title', [neutral('Back to the title screen', { note: 'Progress in the current task is lost.' })]),
      ] })]),
    ],
  })],
};

// ---------------------------------------------------------------- overview flow
const sections = [
  { id: 'overview', title: 'How a play-through flows', desc: 'Click a step to jump to its decision tree. Each tree reads from left to right: a decision point, what the player can do, and what the game says back, with the learning objective (LO) each answer serves.',
    flow: [
      { title: 'Title and dog setup', sub: 'Name and colour the dog', lo: ['CTX'], go: 'setup' },
      { title: 'Opening cutscene', sub: 'The parent explains the jobs', lo: ['CTX', 'LO1', 'LO2'], go: 'setup' },
      { title: 'Level 1, Task 1: Snack Time', sub: 'Safe or unsafe food, 3 rounds', lo: ['LO1'], go: 'snack' },
      { title: 'Level 1, Task 2: Potty Training', sub: 'Place the pad, lead, reward', lo: ['LO2', 'LO3'], go: 'potty' },
      { title: 'Album and growth', sub: 'Puppy becomes a young dog', lo: ['LO1', 'LO2'], go: 'albums' },
      { title: 'Level 2, Task 1: Help the Vet', sub: 'Four checks build the list', lo: ['LO4'], go: 'vet' },
      { title: 'Level 2, Task 2: Pet Store Run', sub: 'Needs, wants and a budget', lo: ['LO5', 'LO4'], go: 'shop' },
      { title: 'Album and growth', sub: 'Young dog becomes an adult', lo: ['LO4', 'LO5'], go: 'albums' },
      { title: 'Rules in every task', sub: 'Meter, hints, retry, pause', lo: [], go: 'rules' },
    ] },
  setup, snack, potty, milestones, vetTask, shopTask, rules,
];

// ---------------------------------------------------------------- write the HTML
const count = n => 1 + (n.kids || []).reduce((a, k) => a + count(k), 0);
const total = sections.filter(s => s.roots).reduce((a, s) => a + s.roots.reduce((b, r) => b + count(r), 0), 0);
const data = {
  intro: 'Every action a player can take in Levels 1 and 2, what the game says or shows in reply, and the learning objective each reply serves. The dog is called ' + NAME + ' here; in the game it is the name the player chose. Built from the game\u2019s own text, so it matches what players see. Level 3 is not built yet and is not included.',
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
