// All player-facing text and Level 1 data. Edit freely; no code changes needed.
// `icon` values name pixel-art icon sprites (asset group 3). Never put emoji in this file.
// `{name}` is replaced with the dog's name.

export const DOG_NAMES = ['Biscuit', 'Mochi', 'Pepper', 'Noodle', 'Waffles', 'Bean', 'Pip', 'Toffee', 'Maple', 'Scout'];

export const LOADING_TIPS = [
  'Dogs can smell up to 100,000 times better than people!',
  'Puppies sleep up to 18 hours a day.',
  'A wagging tail can mean lots of things. Watch the whole body!',
  'Dogs sweat a little through their paw pads.',
];

export const CUTSCENES = {
  opening: [
    { panel: 'car', text: "We're bringing home a new puppy today!" },
    { panel: 'porch', text: 'Welcome home, {name}! Everything smells new.' },
    { panel: 'fridge', text: "Taking care of {name} is your job now. Don't worry, I'll help at first." },
    { panel: 'supplies', text: "Puppies need the right food, and they need to learn where to go potty. Let's start there!" },
  ],
  growth1: [
    { panel: 'growth', text: "Look how much {name} has grown! You're doing a great job." },
  ],
  growth2: [
    { panel: 'growth', stage: 'adult', text: "Look how big {name} is now! You're doing a great job." },
  ],
  level2: [
    { panel: 'clinic', text: "Time for {name}'s first check-up! Afterwards we'll buy whatever the vet says {name} needs." },
  ],
  vaccine: [
    { panel: 'vaccine', face: 'vet', text: '{name} was so brave! Vaccines protect against serious diseases, and only a vet can give them.' },
  ],
};

export const LEVEL1 = {
  drainPerSec: 0.25,
  hintAfterMs: 15000,

  snack: {
    intro: "{name}'s hungry! Pick something safe from the counter.",
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
    next: ['{name} is hungry again! Which food is safe this time?', 'One more snack! Choose carefully.'],
    again: 'Look again at both foods. Which one is safe for {name}?',
    done: 'Great choices! {name} has a happy tummy.',
  },

  potty: {
    introPad: "Where should {name}'s potty pad go? Drag it to a good spot.",
    hintPad: 'Dogs like a quiet potty spot, away from where they eat and sleep.',
    spots: [
      { id: 'bowl',   correct: false, fact: "Dogs don't like to go potty near where they eat." },
      { id: 'middle', correct: false, fact: 'The middle of the room is busy and stressful, so the puppy may avoid it.' },
      { id: 'door',   correct: true,  fact: 'A quiet corner by the door makes it easier to move to outdoor potty later.' },
    ],
    introLead: "Now watch {name} closely. They'll show you when they need to go!",
    cue: '{name} is sniffing and circling. That means "I need to go!" Drag the treat from the counter to lead them to the pad.',
    cueAgain: '{name} is sniffing again! Lead them to the pad.',
    hintLead: 'Keep holding the treat, and walk slowly so {name} keeps following it.',
    cueWindowMs: 12000,
    successesNeeded: 2,
    reward: {
      title: 'Great job!',
      prompt: '{name} went on the pad! Reward them right away: drop the treat on {name}.',
      again: "{name} did it again, and you rewarded them right away. That's how puppies learn!",
      fact: "That's positive reinforcement! Rewarding good behavior right away is a great way to train a dog. {name} learns that using the pad means good things happen.",
    },
    tooLate: {
      question: 'Oops, an accident on the floor. What do you do?',
      choices: [
        { id: 'scold', icon: 'scold', label: 'Scold the puppy', delta: -5,
          fact: 'Scolding teaches puppies to hide when they go, not where to go.' },
        { id: 'clean', icon: 'clean', label: 'Clean it up calmly', delta: 10,
          fact: 'Clean accidents well. Leftover smell makes a puppy go there again.' },
      ],
    },
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

// Level 2 (GAME_DESIGN.md section 7). Positions are world pixels (320x180) and must match CLINIC in tools/sprites.py / src/ui.js.
const ITEMS = {
  // needs from the vet: explained in the clinic, so no fact card; `why` is said at the till
  toothbrush: { name: 'Dog toothbrush', price: 4, kind: 'need', from: 'vet', why: "The dog toothbrush is for the yellow tartar the vet found on {name}'s teeth." },
  toothpaste: { name: 'Dog toothpaste', price: 6, kind: 'need', from: 'vet', why: 'Dog toothpaste goes with it. Human toothpaste is not safe for dogs to swallow.' },
  flea:       { name: 'Flea treatment (dog)', price: 12, kind: 'need', from: 'vet', why: "The flea treatment is for the flea the vet found on {name}'s coat." },
  clippers:   { name: 'Nail clippers', price: 7, kind: 'need', from: 'vet', why: "The nail clippers are for {name}'s long nails." },
  ear:        { name: 'Ear cleaner (dog)', price: 7, kind: 'need', from: 'vet', why: "The ear cleaner is for the wax the vet saw in {name}'s ears." },
  // needs the parent adds: each gets a fact card the first time it is bought
  brush: { name: 'Brush', price: 5, kind: 'need', from: 'parent', why: "A brush keeps {name}'s coat clean and tangle-free.",
           fact: "Brushing keeps a dog's coat clean and tangle-free, and it spreads natural oils that make fur shiny." },
  tag:   { name: 'ID tag', price: 4, kind: 'need', from: 'parent', why: 'An ID tag helps {name} get home if they ever get lost.',
           fact: 'A tag with your phone number helps a lost dog get home fast.' },
  chew:  { name: 'Chew toy', price: 6, kind: 'need', from: 'parent', why: '{name} needs something safe to chew.',
           fact: "Chew toys give a dog something safe to chew. Pick one that is bigger than your dog's mouth, so it can't be swallowed." },
  bags:  { name: 'Poop bags', price: 3, kind: 'need', from: 'parent', why: 'Poop bags keep parks clean and healthy for everyone.',
           fact: 'Picking up after your dog keeps parks clean and healthy for everyone.' },
  // wants: never wrong, but they cost coins the needs may require
  shampoo_dog: { name: 'Dog shampoo', price: 6, kind: 'want' },
  ball_squeak: { name: 'Squeaky ball', price: 5, kind: 'want' },
  bandana:     { name: 'Bandana', price: 4, kind: 'want' },
  bow:         { name: 'Bow', price: 2, kind: 'want' },
  sweater:     { name: 'Sweater', price: 9, kind: 'want' },
  collar:      { name: 'Sparkly collar', price: 8, kind: 'want' },
  bed:         { name: 'Dog bed', price: 12, kind: 'want' },
  // look-alikes: the wrong pick (-5) and why
  toothpaste_human: { name: 'Human toothpaste', price: 4, kind: 'wrong',
                      fact: 'Human toothpaste often has xylitol or fluoride, which are unsafe for dogs to swallow.' },
  flea_cat:         { name: 'Flea treatment (cat)', price: 10, kind: 'wrong',
                      fact: 'Flea products are made for one species. Always match the label.' },
  shampoo_human:    { name: 'Human shampoo', price: 5, kind: 'wrong',
                      fact: "A dog's skin is different from ours, so use a shampoo made for dogs." },
  ball_tiny:        { name: 'Tiny ball', price: 2, kind: 'wrong',
                      fact: 'Toys that are small enough to swallow can make a dog choke. Choose one that is bigger than its mouth.' },
};

export const LEVEL2 = {
  drainPerSec: 0.35,
  hintAfterMs: 25000,
  items: Object.fromEntries(Object.entries(ITEMS).filter(([, v]) => v.kind === 'need').map(([k, v]) => [k, v.name])),   // label for each list line

  vet: {
    intro: "Let's check {name} from nose to tail. Tap each spot to look closer.",
    hint: 'Tap a glowing spot on {name}, or the label next to it. Teeth, coat, paws and ears all need a look.',
    pat: '{name} is a little nervous. Tap {name} for a calming pat!',
    patDone: '{name} feels calmer. Good job!',
    done: "That's everything! {name} was great. Next up: a vaccine.",
    spots: [
      { id: 'teeth', label: 'Teeth', ring: [165, 102], pill: [172, 96], items: ['toothbrush', 'toothpaste'],
        say: 'Yellow tartar on the teeth! Brushing a few times a week keeps teeth and gums healthy.' },
      { id: 'coat', label: 'Coat', ring: [138, 110], pill: [105, 109], items: ['flea'],
        say: 'A flea! Fleas cause itching and can spread illness, so monthly prevention helps.' },
      { id: 'paws', label: 'Paws', ring: [150, 118], pill: [157, 112], items: ['clippers'],
        say: 'Long nails click on the floor. They hurt when walking, so trim them regularly.' },
      { id: 'ears', label: 'Ears', ring: [148, 95], pill: [117, 88], items: ['ear'],
        say: 'A little wax in the ears. A gentle ear cleaner helps, and checking every week keeps them healthy.' },
    ],
  },

  shop: {
    budget: 60,
    items: ITEMS,
    vetNeeds: ['toothbrush', 'toothpaste', 'flea', 'clippers', 'ear'],        // already on the paper when the shop opens
    parentNeeds: ['brush', 'tag', 'chew', 'bags'],                              // the parent writes these on
    intro: "Now let's go shopping for everything the vet said {name} needs!",
    parent: 'Also pick up a brush, an ID tag, a chew toy and poop bags. Here are 60 coins. Needs first, then extras!',
    hint: 'Tap an item for its price. Use the arrows for more aisles, and the basket when you are done.',
    tooMuch: "That's more than we have left. Put something back in the basket first.",
    missing: "We're not done yet. Some things on the list still need a tick.",
    allDone: 'That is everything on the list! Tap the basket to check out.',
    nudge: {
      title: 'Needs come first!',
      again: 'Needs first! Keep enough coins for everything on the list.',
      fact: "If we buy that now, we won't have enough coins for everything on the list. Food, health and safety come before extras.",
    },
    wantFact: 'Style is fine if it is comfortable, fits well, and the dog can still see and move freely.',
    wrongTitle: 'Look at the label!',
    wrongAgain: "Check the label first. That one isn't made for dogs.",
    tillWant: 'A little extra for {name}, bought with the leftover coins.',
    tillDone: "That's everything on the list, and we stayed within our coins. Great shopping!",
    aisles: [
      { name: 'Health', rows: [['toothbrush', 'toothpaste', 'toothpaste_human'], ['flea', 'flea_cat', 'ear']] },
      { name: 'Grooming', rows: [['clippers', 'brush'], ['shampoo_dog', 'shampoo_human']] },
      { name: 'Play & Walk', rows: [['chew', 'ball_squeak', 'ball_tiny'], ['tag', 'bags']] },
      { name: 'Home & Style', rows: [['bandana', 'bow', 'sweater'], ['collar', 'bed']] },
    ],
  },

  retry: {
    vet: "{name} got too nervous. Gentle pats keep a dog calm, and a check-up goes best when you take your time. Let's try again!",
    shop: "The shopping took too long, and {name} is waiting at home. Let's try again, and check the list first!",
  },

  album: {
    title: 'Check-up Day',
    skills: [
      { icon: 'vet', label: 'Health check' },
      { icon: 'coin', label: 'Smart shopping' },
    ],
  },
};

export const fill = (s, name) => s.replaceAll('{name}', name);
