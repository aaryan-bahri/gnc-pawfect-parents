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
    introLead: 'Now watch {name}. When they need to go, drag a treat from the counter and lead them to the pad!',
    hintLead: 'Sniffing and circling mean "I need to go!" Drag the treat from the counter and {name} will follow it to the pad.',
    cueWindowMs: 12000,
    successesNeeded: 2,
    reward: {
      title: 'Great job!',
      prompt: '{name} went on the pad! Reward them right away: drop the treat on {name}.',
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

export const fill = (s, name) => s.replaceAll('{name}', name);
