// All player-facing text and level data. Edit freely; no code changes needed.
// `icon` values name pixel-art icon sprites (asset groups 3, 6, 8, 11). Never put emoji in this file.
// `{name}` is replaced with the dog's name.

export const DOG_NAMES = ['Biscuit', 'Mochi', 'Pepper', 'Noodle', 'Waffles', 'Bean', 'Pip', 'Toffee', 'Maple', 'Scout'];

export const LOADING_TIPS = [
  'Dogs can smell up to 100,000 times better than people!',
  'Puppies sleep up to 18 hours a day.',
  'A wagging tail can mean lots of things. Watch the whole body!',
  'Dogs sweat a little through their paw pads.',
];

// The level select (asset group 8). `intro` is the cutscene that starts the level.
export const LEVELS = [
  { n: 1, title: 'First Day Home', sub: 'Puppy, 2 tasks', thumb: 'thumb_home', intro: 'l1_intro' },
  { n: 2, title: 'Check-up Day', sub: 'Young dog, 2 tasks', thumb: 'thumb_clinic', intro: 'l2_intro' },
  { n: 3, title: 'Park Day', sub: 'Adult dog, 2 tasks', thumb: 'thumb_park', intro: 'l3_intro' },
];

// The story (approved story flow + Level 3). A beat is a panel with a line (face: 'parent' by default, 'vet', or null for narration),
// a time card { card, icon }, or the growth panel.
export const CUTSCENES = {
  l1_intro: [
    { card: 'Saturday morning', icon: 'morning' },
    { panel: 'bedroom', text: "Wake up, sleepyhead! It's Puppy Day. We leave in five minutes!" },
    { panel: 'car_there', text: "We're off to the rescue centre. Lots of puppies there need a family." },
    { panel: 'rescue', face: null, text: "So many puppies! But one of them can't stop wagging at you." },
    { panel: 'chosen', text: 'Looks like this little one picked you. What will you call them?' },
  ],
  l1_home: [
    { panel: 'car', text: '{name} is a little nervous. Car rides are new and a bit scary for puppies.' },
    { panel: 'porch', text: 'Welcome home, {name}! Let them sniff around. Everything smells new.' },
    { panel: 'fridge', text: "Looking after {name} is your job now. Don't worry, I'll help at first." },
    { panel: 'supplies', text: "Puppies need the right food, a potty spot and lots of love. Let's start with lunch!" },
  ],
  afternoon: [
    { card: 'Later that afternoon', icon: 'afternoon' },
    { panel: 'afternoon', text: '{name} has had lunch and lots of play. Puppies often need to go potty after that...' },
    { panel: 'afternoon_sniff', face: null, text: 'Wait... why is {name} sniffing the rug like that?' },
  ],
  night: [
    { card: 'That night', icon: 'night' },
    { panel: 'night', text: 'What a first day! {name} learned so much, and so did you.' },
  ],
  growth1: [
    { card: 'Two months later', icon: 'later' },
    { panel: 'growth', text: "Look how much {name} has grown! You're doing a great job." },
  ],
  l2_intro: [
    { card: 'One morning', icon: 'morning' },
    { panel: 'scratching', text: "{name} keeps scratching. Let's take them to the vet for a check-up." },
    { panel: 'grooming_bag', text: "Bring {name}'s grooming bag too. The vet can check what we use at home." },
    { panel: 'clinic', text: 'Here we are! {name} is a little nervous. Stay close and keep calm.' },
    { panel: 'vet_chart', face: 'vet', text: "Hello, {name}! Let's compare you with a healthy dog, and check that grooming bag too." },
  ],
  vaccine: [
    { panel: 'vaccine', face: 'vet', text: '{name} was so brave! Vaccines protect against serious diseases, and only a vet can give them.' },
    { card: 'That evening', icon: 'evening' },
  ],
  growth2: [
    { card: 'A few months later', icon: 'later' },
    { panel: 'growth', stage: 'adult', text: "Look how big {name} is now! You're doing a great job." },
  ],
  l3_intro: [
    { card: 'One sunny morning', icon: 'morning' },
    { panel: 'leash', text: "{name} is all grown up and full of energy. Let's walk to the park!" },
  ],
  park: [
    { panel: 'park_gate', text: 'Here we are! Lots of room to run. Who wants to play fetch?' },
  ],
  l3_later: [
    { card: 'A little later', icon: 'afternoon' },
  ],
  l3_end: [
    { card: 'That evening', icon: 'evening' },
    { panel: 'evening_home', text: "What a day! {name} is all grown up, and so are you. You're a Pawfect Parent!" },
  ],
};

export const LEVEL1 = {
  drainPerSec: 0.25,
  hintAfterMs: 15000,
  outro: 'night',

  snack: {
    intro: "{name}'s hungry! Tap the kitchen counter to see what we have.",
    pick: 'Tap the food that is safe for {name}.',
    hint: 'Dogs need dog food or plain, simple foods. Sweets and some fruits are dangerous.',
    rounds: [
      { safe: { id: 'kibble', label: 'Puppy kibble',
                fact: 'Puppy kibble has everything a growing puppy needs.' },
        unsafe: { id: 'chocolate', label: 'Chocolate bar',
                  fact: "Chocolate contains theobromine, which dogs can't break down. Even a little can make them very sick." } },
      { safe: { id: 'carrot', label: 'Carrot sticks',
                fact: 'Carrots are a crunchy, healthy snack for dogs.' },
        unsafe: { id: 'grapes', label: 'Grapes',
                  fact: "Grapes and raisins can hurt a dog's kidneys, even in small amounts." } },
      { safe: { id: 'chicken', label: 'Cooked chicken',
                fact: 'Cooked chicken is a safe treat. Take the meat off the bone first, and skip the skin and seasoning.' },
        unsafe: { id: 'onion', label: 'Red onion',
                  fact: "Onions and garlic harm a dog's blood, whether cooked or raw." } },
    ],
    wrongParent: "Good thing {name} didn't eat it. I'll put that up high where they can't reach.",
    next: ['{name} is hungry again! Tap the counter. Which food is safe this time?', 'One more snack! Tap the counter and choose carefully.'],
    again: 'Look again at both foods. Which one is safe for {name}?',
    done: 'Great choices! {name} has a happy tummy. Time to play!',
  },

  potty: {
    accident: {
      question: 'Oh no, {name} had an accident on the rug! What do you do?',
      choices: [
        { id: 'scold', icon: 'scold', label: 'Scold the puppy', delta: -5,
          fact: 'Scolding teaches puppies to hide when they go, not where to go.' },
        { id: 'clean', icon: 'clean', label: 'Clean it up calmly', delta: 10,
          fact: 'Clean accidents well. Leftover smell makes a puppy go there again.' },
      ],
      after: "Accidents happen. Let's give {name} a proper potty spot.",
    },
    introPad: "Here's a potty pad. Drag it to a good spot for {name}.",
    hintPad: 'Dogs like a quiet potty spot, away from where they eat and sleep.',
    spots: [
      { id: 'bowl',   correct: false, fact: "Dogs don't like to go potty near where they eat." },
      { id: 'middle', correct: false, fact: 'The middle of the room is busy and stressful, so the puppy may avoid it.' },
      { id: 'door',   correct: true,  fact: 'A quiet corner by the door makes it easier to move to outdoor potty later.' },
    ],
    introLead: "Now watch {name} closely. Sniffing and circling mean they need to go!",
    cue: '{name} is sniffing and circling. That means "I need to go!" Drag the treat from the counter to lead them to the pad.',
    cueAgain: '{name} is sniffing again! Lead them to the pad.',
    hintLead: 'Keep holding the treat, and move it slowly so {name} keeps following it.',
    cueWindowMs: 12000,
    successesNeeded: 2,
    reward: {
      title: 'Great job!',
      prompt: '{name} went on the pad! Reward them right away: drop the treat on {name}.',
      again: "{name} did it again, and you rewarded them right away. That's how puppies learn!",
      fact: "That's positive reinforcement! Rewarding good behavior right away is a great way to train a dog. {name} learns that using the pad means good things happen.",
    },
    late: "Too late, {name} couldn't wait. Let's help next time.",
    tip: 'Puppies often need to go after waking up, eating, and playing.',
    done: '{name} is learning fast!',
  },

  retry: {
    snack: "{name} got too hungry and sad. Remember: only dog-safe food. Let's try again!",
    potty: "{name} needed help with potty time. Watch for sniffing and circling. Let's try again!",
  },

  album: {
    title: 'Day 1',
    skills: [
      { icon: 'bowl', label: 'Safe foods' },
      { icon: 'pad', label: 'Potty spot' },
    ],
  },
};

// Level 2 (GAME_DESIGN.md section 7). Positions are world pixels (320x180) and mirror SPOT, CU_HITS and BATH in tools/sprites.py.
export const LEVEL2 = {
  drainPerSec: 0.35,
  hintAfterMs: 25000,

  spot: {
    layout: { frames: [6, 164], top: 28, w: 150, dogDx: 37, dogFeet: 114, bigGround: 58, itemXs: [20, 46, 74, 102, 130], itemBottom: 162 },
    bodyParts: ['ears', 'teeth', 'eyes', 'paws', 'coat', 'tail'],
    tray: ['toothpaste', 'shampoo', 'flea', 'toy', 'brush'],
    total: 8,
    intro: "On the left is a healthy dog. On the right is {name}, with the grooming bag from home. Tap anything to look closer. Can you find 8 differences?",
    closer: 'Compare the two. Tap the difference if you see one, or tap Back.',
    hint: "Look closely at {name}'s {part}.",
    miss: 'Look again: compare both pictures.',
    missAgain: 'Hmm, not there.',
    already: 'We already found that one!',
    done: "Great eyes! You found all 8. And now, one last thing for {name}: a vaccine.",
    // the 8 differences: what part (or tray product) shows it, where it is circled in the overview (world px from the dog / item),
    // the close-up hit box (close-up art px, 120x110), and what the vet says
    diffs: {
      nails: { part: 'paws', ring: [45, 46], hit: [20, 28, 80, 26],
               fact: "{name}'s nails are too long. Long nails hurt when a dog walks, so trim the tips regularly." },
      ears: { part: 'ears', ring: [40, 10], hit: [44, 52, 34, 34],
              fact: 'Brown wax in the ears! A gentle dog ear cleaner helps, and a weekly check keeps ears healthy.' },
      teeth: { part: 'teeth', ring: [58, 18], hit: [12, 34, 96, 46],
               fact: 'Yellow tartar on the teeth. Brushing a few times a week with dog toothpaste keeps teeth and gums healthy.' },
      fleas: { part: 'coat', ring: [21, 17], hit: [46, 24, 44, 34],
               fact: 'Fleas! They make dogs itch and can spread illness. Monthly flea prevention keeps them away.' },
      toothpaste: { part: 'toothpaste', hit: [22, 37, 62, 28],
                    fact: 'That toothpaste is for people. It often has xylitol or fluoride, which are unsafe for dogs to swallow.' },
      shampoo: { part: 'shampoo', hit: [28, 32, 42, 48],
                 fact: "That shampoo is for people. A dog's skin is different from ours, so use a shampoo made for dogs." },
      flea: { part: 'flea', hit: [20, 24, 66, 68],
              fact: 'Those flea drops are for cats! Flea products are made for one kind of animal, so always match the label.' },
      toy: { part: 'toy', hit: [52, 60, 26, 26],
             fact: 'That ball is small enough to swallow, and it could make a dog choke. Choose a toy bigger than its mouth.' },
    },
    decoys: { eyes: "{name}'s eyes look just like the healthy dog's: bright and clear!", tail: 'Both tails look the same. Fluffy and happy!',
              brush: 'Both brushes are the same. That brush is just right!' },
    names: { ears: 'ears', teeth: 'teeth', eyes: 'eyes', paws: 'paws', coat: 'coat', tail: 'tail', toothpaste: 'toothpaste',
             shampoo: 'shampoo', flea: 'flea drops', toy: 'toy', brush: 'brush' },
  },

  bath: {
    layout: { matX: 172, matFeet: 130, tubX: 62, tubFeet: 112, shelfX: 270, boards: [56, 94], bigGround: 58 },
    order: ['toothbrush', 'clippers', 'ear', 'shampoo', 'towel', 'flea'],
    intro: "Bath time! Drag each thing from the shelf onto the right part of {name}. Teeth, nails and ears come first.",
    hint: 'Drag something from the shelf onto {name}.',
    wrong: "Not there! The {item} is for {name}'s {part}.",
    notYet: {
      shampoo: 'Shampoo comes in the tub. Teeth, nails and ears first!',
      towel: 'The towel comes after the bath.',
      flea: 'Flea drops go on after the bath, once {name} is dry.',
      done: 'We already did that one!',
    },
    items: {
      toothbrush: { name: 'dog toothbrush', part: 'teeth', issue: 'teeth', line: 'Dog toothpaste, little circles... bye-bye, tartar!' },
      clippers: { name: 'nail clippers', part: 'paws', issue: 'nails', line: 'Just the tips, and never too short. Much better!' },
      ear: { name: 'ear cleaner', part: 'ears', issue: 'ears', line: 'A little cleaner, then a gentle wipe. Clean ears!' },
      shampoo: { name: 'dog shampoo', part: 'coat', line: 'Now scrub! Rub {name} back and forth to make lots of bubbles.' },
      towel: { name: 'towel', part: 'coat', line: 'Rub {name} dry with the towel.' },
      flea: { name: 'flea drops', part: 'neck', issue: 'fleas', line: "Flea drops go on the back of the neck, where {name} can't lick them off." },
    },
    tub: 'Teeth, nails and ears are done! Into the tub, {name}!',
    scrubbed: 'So many bubbles! A quick rinse, and out you get.',
    dried: 'Nice and dry! One last thing before {name} goes to play.',
    done: 'Dog shampoo, dog toothpaste, the right flea drops and a big chew toy. Now {name} has what they need!',
    rubNeeded: 1400,                                    // canvas px of rubbing to fill the foam or dry the coat
  },

  retry: {
    spot: "{name} got bored waiting. Compare the two pictures part by part. Let's try again!",
    bath: "{name} got cold and fed up. Drag each thing onto the right part of {name}. Let's try again!",
  },

  album: {
    title: 'Check-up Day',
    skills: [
      { icon: 'vet', label: 'Health check' },
      { icon: 'bath', label: 'Grooming' },
    ],
  },
};

// Level 3 (GAME_DESIGN.md section 7). Positions mirror WALK and PARK in tools/sprites.py. No pointer cues and no timed hints here.
export const LEVEL3 = {
  drainPerSec: 0.45,
  hintAfterMs: null,
  outro: 'l3_end',

  walk: {
    layout: { width: 960, ground: 158, kidX: 56, hand: [35, -29], collar: [3, -25], slack: 26, tight: 38, gate: 868,
              distractions: [['squirrel', 330, 140], ['sandwich', 560, 161], ['cat', 752, 105]] },
    speed: 22,                                          // world px per second while holding
    intro: "Hold down anywhere to walk. If {name} pulls, let go and stop. We only walk when the leash is loose.",
    lunge: { squirrel: 'A squirrel!', sandwich: 'A dropped sandwich!', cat: 'A cat on the fence!' },
    pulled: { title: 'Stop when they pull', fact: 'If you keep walking when they pull, they learn that pulling works. Stop, and wait for a loose leash.' },
    stopped: 'Good stop! {name} sat down and the leash is loose. Hold to walk again.',
    pulledAgain: 'Let go when {name} pulls!',
    done: 'We made it to the park, and the leash stayed loose. Nice walking!',
  },

  fetch: {
    layout: { ground: 152, kidX: 80, dogX: 124, ball: [146, 150], shade: [4, 138, 84, 24], restX: 44, bowl: [262, 153], land: [168, 262] },
    tiredAfter: 4,                                      // fetches before the dog starts panting
    intro: 'Drag the ball back and let go to throw it. Keep an eye on {name} while you play!',
    tooSoon: '{name} still has lots of energy! Throw the ball a few more times.',
    shade: 'Good call! {name} was panting hard. A rest in the shade helps.',
    water: 'Fresh water helps {name} cool down.',
    needShade: 'Water helps! Now let {name} rest in the shade too.',
    needWater: '{name} is resting. Now bring some water from the fountain.',
    flop: { title: 'Time for a rest!', fact: 'Panting hard and lying down mean your dog needs rest, shade and water now.' },
    flopLine: '{name} is too hot to play. Tap the shady tree, then drag the water bowl to {name}.',
    tip: { title: 'Hot days', fact: "On hot days, walk in the morning or evening. Test the pavement with the back of your hand: if you can't hold it there for 7 seconds, it's too hot for paws." },
    done: '{name} is cool and happy again. Great job looking after them!',
  },

  greet: {
    samX: 200,
    hello: 'Can I pet your dog?!',
    step1: {
      question: 'Sam is running over! What do you say?',
      choices: [
        { id: 'come', icon: 'run', label: 'Sure, come here!', ok: false },
        { id: 'slow', icon: 'stop', label: 'Stop! Walk slowly, please.', ok: true },
      ],
      bad: 'Running at a dog can scare it. Ask people to walk up slowly and calmly.',
      good: 'Running at a dog can scare it, so a slow, calm walk is best.',
      again: "Let's ask Sam to try that again.",
      samSlow: "Okay! I'll walk slowly.",
    },
    step2: {
      question: 'Sam is here. Look at {name}. What should happen next?',
      choices: [
        { id: 'pet', icon: 'pet', label: 'Pet {name} right away', ok: false },
        { id: 'sniff', icon: 'sniff', label: 'Let {name} sniff your hand first', ok: true },
        { id: 'space', icon: 'space', label: 'Not today, {name} needs space', ok: false },
      ],
      calm: {
        pet: 'Petting right away can startle a dog. Let the dog sniff your hand first. A sniff is how dogs say hello.',
        sniff: 'A sniff is a dog\'s way of saying hello. {name} is wagging: that means "Nice to meet you!"',
        space: "It's always OK to say no, but look at {name}: a loose, wagging tail and a relaxed face. {name} is happy to say hello!",
      },
      stressed: {
        title: '{name} needs space',
        pet: "Look at {name}: licking lips, yawning, the whites of the eyes showing and a tucked tail. Those mean \"I'm uncomfortable\". Petting now could go wrong.",
        sniff: "Look at {name}: licking lips, yawning, the whites of the eyes showing and a tucked tail. Those mean \"I'm uncomfortable\". Not even a sniff right now.",
        space: "It's always OK to say no. Lip licking, yawning, whale eye and a tucked tail mean a dog is uncomfortable and needs space.",
      },
      samSniff: 'Hello, {name}! Here, sniff my hand.',
      samBye: 'Okay! Maybe next time. Bye, {name}!',
    },
    step3: {
      prompt: "Now drag Sam's hand onto {name}. Where do dogs like to be petted?",
      head: 'Many dogs don\'t like a hand coming over their head. The side of the neck or the chest is better.',
      chest: '{name} loves a scratch on the chest! Many dogs like that much more than a pat on the head.',
      headAgain: 'Not over the head! Try somewhere else.',
      samHappy: "{name} is so soft! Thank you!",
    },
    both: { title: 'Both sides!', fact: "When you meet a dog you don't know, ask the owner first, and let the dog sniff your hand." },
  },

  retry: {
    walk: "{name} pulled the whole way, and we ran out of time. Remember: stop when {name} pulls. Let's try again!",
    fetch: "{name} got too hot and tired. Watch for panting, slowing down and lying down, then rest in the shade with water. Let's try again!",
    greet: "{name} got overwhelmed. Read {name}'s body language and greet slowly. Let's try again!",
  },

  album: {
    title: 'Park Day',
    skills: [
      { icon: 'ball', label: 'Exercise safely' },
      { icon: 'pet', label: 'Safe greetings' },
    ],
  },
};

export const fill = (s, name) => s.replaceAll('{name}', name);
