# Man vs. Machine — Micro Challenge Library

> **Version:** 1.0
> **Status:** Draft — Pre-MVP
> **Audience:** Game designers, developers, content creators
> **Related:** See `docs/01_Master_Architecture.md` §12 (Challenge Engine) and `docs/04_Game_Design_Document.md` §3 (Challenge System).

This document is the **content engine** for Man vs. Machine. It catalogs micro-challenges — each designed for 15–60 seconds of play. Challenges are data, not code: every entry follows a consistent template that the Challenge Engine interprets at runtime.

Each challenge can be rotated with different constraints (via the `dailyVariants` and `constraintPool` mechanism) to generate hundreds of unique rounds from a small catalog. A library of 25 challenges × 3 daily variants = 75 possible daily challenges, keeping the experience fresh.

---

## Table of Contents

1.  How to Use This Library
2.  Challenge Template Reference
3.  The Library: 25 Challenges

---

## 1. How to Use This Library

Each challenge in this library is a **self-contained JSON definition** that maps directly to the `ChallengeDefinition` schema in `docs/02_Implementation_Guide.md` §10. The Challenge Engine loads these at startup and serves them to players.

**Daily rotation** works as follows:

- The `constraintPool` field lists additional constraints that can be swapped in daily.
- The `dailyVariants` field specifies how many rotated versions exist per day.
- On day 1: base challenge. On day 2: same prompt + one alternate constraint from the pool. Etc.

**Example**: Challenge "Tiny Tagline" has `constraintPool: ["must_rhyme", "no_adjectives", "one_sentence_only"]`. On any given day, the system picks 0-1 constraints from this pool and adds them as **soft constraints** (doesn't block submission, but affects humanity scoring if violated).

**Stub entries**: Each challenge has 5–10 pre-written AI entries in `backend/app/data/stub_entries/{challenge_id}.json`. These are used when no AI provider is available (tests, local dev, fallback).

---

## 2. Challenge Template Reference

Each entry in this library follows this structure:

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| **Challenge Name** | string | Human-readable name | Tiny Tagline |
| **Category** | string | Interaction type | Quick Text |
| **Prompt** | string | The creative instruction | Write a slogan for a dragon-owned bakery. |
| **Constraints** | array | Hard constraints (block submission) | max_words: 5 |
| **Time Limit** | int | Seconds allowed | 15 |
| **Input Type** | string | text_single_line / text_multi_line | text_single_line |
| **Voting Criteria** | string | How entries are judged | most_believable |
| **AI Prompt** | string | Template for AI system prompt additions | Be casual, use contractions |
| **Scoring Rules** | object | Base score, multipliers | baseScore: 100 |
| **Difficulty** | int | 1-5 scale | 2 |
| **Est. Completion** | string | How long a human takes | 10-15s |
| **Replayability Notes** | string | How it stays fresh | Daily constraint rotation |

**Constraint types used in this library:**

| Constraint | Hard/Soft | Value | Purpose |
|------------|-----------|-------|---------|
| `max_words` | Hard | integer | Forces brevity |
| `max_characters` | Hard | integer | Caps length |
| `must_rhyme` | Soft | — | Adds creative constraint |
| `no_adjectives` | Soft | — | Tests creativity |
| `must_include_theme` | Hard | string | Thematic focus |
| `no_letter_e` | Hard | — | Extreme constraint |
| `exactly_n_emojis` | Hard | integer | Limits to N emojis |
| `one_sentence_only` | Hard | — | Forces conciseness |

---

## 3. The Library: 25 Challenges

---

### 01. Tiny Tagline

| Field | Value |
|-------|-------|
| **Challenge Name** | Tiny Tagline |
| **Category** | Quick Text |
| **Prompt** | Write a slogan for a dragon-owned bakery. |
| **Constraints** | `max_words: 5` (hard) |
| **Time** | 15 seconds |
| **Input** | text_single_line |
| **Voting** | most_believable |
| **AI Prompt** | "Be casual. Use contractions. Reference fire or baking. Don't over-explain." |
| **Scoring** | baseScore: 100, timeBonusMultiplier: 0.15, streakMultiplier: 0.05 |
| **Difficulty** | 2 |
| **Est. Completion** | 8-12s |
| **Replayability** | constraintPool: ["must_rhyme", "no_adjectives"]. Same prompt, different constraints daily. |

**Sample AI stub entries:**
- "Fire baked. Dragon approved."
- "Where every loaf is forged in flame."
- "Burning bread since 1492."
- "Our bread breathes fire — literally."
- "Fresh from the dragon's oven."

> **Why it works**: A 5-word limit is perfect for catching AI over-polish. Humans tend to be more casual; AI often produces overly "brand-y" responses.

---

### 02. Impossible Product

| Field | Value |
|-------|-------|
| **Challenge Name** | Impossible Product |
| **Category** | Quick Text |
| **Prompt** | Invent a product nobody needs. |
| **Constraints** | `max_words: 6` (hard) |
| **Time** | 15 seconds |
| **Input** | text_single_line |
| **Voting** | most_believable |
| **AI Prompt** | "Be absurd. Lean into ridiculousness. Don't overthink it." |
| **Scoring** | baseScore: 100, timeBonusMultiplier: 0.2, streakMultiplier: 0.05 |
| **Difficulty** | 1 |
| **Est. Completion** | 8-10s |
| **Replayability** | constraintPool: ["must_include_theme", "one_sentence_only"]. Daily variant: "Invent a product nobody needs (but uses only 3 emojis)" — no, that conflicts. Better: rotate themes. |

> **Why it works**: Humans naturally lean into absurdity more freely; AI often over-corrects to "product-like" thinking.

---

### 03. Emoji Story

| Field | Value |
|-------|-------|
| **Challenge Name** | Emoji Story |
| **Category** | Quick Text |
| **Prompt** | Tell a movie plot using only 5 emojis. Title it. |
| **Constraints** | `exactly_n_emojis: 5` (hard), `max_words: 3` (hard, for title) |
| **Time** | 20 seconds |
| **Input** | text_multi_line |
| **Voting** | most_believable |
| **AI Prompt** | "Pick a popular movie. Be creative with emojis. Don't list obvious ones." |
| **Scoring** | baseScore: 120, timeBonusMultiplier: 0.15, streakMultiplier: 0.05 |
| **Difficulty** | 2 |
| **Est. Completion** | 10-15s |
| **Replayability** | constraintPool: ["no_letter_e"]. "Tell a movie plot in 5 emojis, no letter E in the title."

**Sample AI stub entries:**
- "The Matrix: 🕴️🟢💊👟🌧️"
- "Jurassic Park: 🦖🚗🏃‍♂️🔒🌋"
- "Inception: 😴💭📐🌀⏰"

> **Why it works**: Emoji choices are highly personal and cultural. AI tends to pick "obvious" emojis; humans use obscure references or inside-joke combinations.

---

### 04. Worst Idea

| Field | Value |
|-------|-------|
| **Challenge Name** | Worst Idea |
| **Category** | Quick Text |
| **Prompt** | Invent the worst possible airline. |
| **Constraints** | `max_words: 8` (hard) |
| **Time** | 15 seconds |
| **Input** | text_single_line |
| **Voting** | most_believable |
| **AI Prompt** | "Be deliberately terrible. Add a ridiculous detail. Sound enthusiastic but wrong." |
| **Scoring** | baseScore: 100, timeBonusMultiplier: 0.2, streakMultiplier: 0.05 |
| **Difficulty** | 2 |
| **Est. Completion** | 8-12s |
| **Replayability** | constraintPool: ["must_rhyme", "no_adjectives"]. Daily: same prompt, rhyme or no-adj constraint. |

**Sample AI stub entries:**
- "Barefoot Airlines — no shoes, no planes, just vibes."
- "Scream-Induced Flight: passengers generate lift by yelling."
- "Overbooked Airways: always 300% booked, refunds in loose change."

> **Why it works**: Humans dive into absurdity without filter. AI often hedges, making it sound "too professional" even when trying to be terrible.

---

### 05. Fill in the Blank

| Field | Value |
|-------|-------|
| **Challenge Name** | Fill in the Blank |
| **Category** | Quick Text |
| **Prompt** | "My grandma accidentally invented ______." |
| **Constraints** | `max_words: 4` (hard) |
| **Time** | 15 seconds |
| **Input** | text_single_line |
| **Voting** | most_believable |
| **AI Prompt** | "Be funny but grounded. Reference a mundane but plausible invention. No sci-fi." |
| **Scoring** | baseScore: 100, timeBonusMultiplier: 0.2, streakMultiplier: 0.05 |
| **Difficulty** | 2 |
| **Est. Completion** | 8-10s |
| **Replayability** | constraintPool: ["must_rhyme", "no_letter_e"]. |

**Sample AI stub entries:**
- "a better way to organize grocery lists"
- "a sock that only works on Tuesdays"
- "the modern art equivalent of a paperclip"
- "the snooze button for houseplants"

> **Why it works**: The "grandma" framing primes for wholesome, everyday absurdity. AI often goes too technical or too abstract.

---

### 06. Comeback Challenge

| Field | Value |
|-------|-------|
| **Challenge Name** | Comeback Challenge |
| **Category** | Quick Text |
| **Prompt** | Someone says: "You're late." Respond with the funniest comeback. |
| **Constraints** | `max_words: 6` (hard) |
| **Time** | 15 seconds |
| **Input** | text_single_line |
| **Voting** | most_believable |
| **AI Prompt** | "Be witty, not mean. Lean into wordplay or self-deprecation. Sound human." |
| **Scoring** | baseScore: 100, timeBonusMultiplier: 0.2, streakMultiplier: 0.05 |
| **Difficulty** | 3 |
| **Est. Completion** | 10-15s |
| **Replayability** | constraintPool: ["no_adjectives", "must_rhyme"]. |

**Sample AI stub entries:**
- "I was here 5 minutes ago. You just missed me."
- "Time is a social construct, and so is punctuality."
- "I got held up being awesome. It takes time."
- "I tried to be on time, but my procrastination won."

> **Why it works**: Comebacks are deeply personal and cultural. AI tends to produce generic puns; humans have idiosyncratic timing and references.

---

### 07. Review

| Field | Value |
|-------|-------|
| **Challenge Name** | Review |
| **Category** | Quick Text |
| **Prompt** | Write a 1-star review for a restaurant that serves only pickles. |
| **Constraints** | `max_words: 20` (hard) |
| **Time** | 20 seconds |
| **Input** | text_multi_line |
| **Voting** | most_believable |
| **AI Prompt** | "Be angry but specific. Mention texture, smell, or service. Sound like you're typing on your phone." |
| **Scoring** | baseScore: 100, timeBonusMultiplier: 0.15, streakMultiplier: 0.05 |
| **Difficulty** | 2 |
| **Est. Completion** | 12-18s |
| **Replayability** | constraintPool: ["no_adjectives", "one_sentence_only"]. |

**Sample AI stub entries:**
- "I've had pickles with more flavor than this place. The pickles here are Boring. Also the 'soup' is just pickle juice. 1 star."
- "Went in hoping for a pickle paradise, left with a pickle purgatory. The pickles are fine, but the ambiance is a mason jar. Zero out of five pickles."
- "This pickle restaurant is a crime against fermentation."

> **Why it works**: Angry, informal reviews have a very specific human cadence. AI reviews tend to be more structured and balanced.

---

### 08. Headline

| Field | Value |
|-------|-------|
| **Challenge Name** | Headline |
| **Category** | Quick Text |
| **Prompt** | Write a breaking news headline about a cat who stole a sandwich. |
| **Constraints** | `max_words: 8` (hard) |
| **Time** | 15 seconds |
| **Input** | text_single_line |
| **Voting** | most_believable |
| **AI Prompt** | "Sound like a local news anchor. Include a location. Be specific but absurd." |
| **Scoring** | baseScore: 100, timeBonusMultiplier: 0.2, streakMultiplier: 0.05 |
| **Difficulty** | 2 |
| **Est. Completion** | 8-12s |
| **Replayability** | constraintPool: ["must_rhyme", "no_letter_e"]. |

**Sample AI stub entries:**
- "Local Cat Arrested After Heroic Sandwich Heist"
- "Feline Bandit Steals Sub from Downtown Office Worker"
- "Cat Walks Out of Cafe with Footlong, No One Stops Him"
- "Sandwich Thief: Local Moggie Executes Perfect Getaway"

> **Why it works**: News headline phrasing is formulaic. AI gets the structure right but misses the "local color" details that humans naturally include.

---

### 09. Tweet

| Field | Value |
|-------|-------|
| **Challenge Name** | Tweet |
| **Category** | Quick Text |
| **Prompt** | Write a tweet about discovering your houseplant is judging you. (Max 280 chars.) |
| **Constraints** | `max_characters: 280` (hard), `must_include_theme: "plant"` (soft) |
| **Time** | 20 seconds |
| **Input** | text_single_line |
| **Voting** | most_believable |
| **AI Prompt** | "Sound like a tired millennial. Use casual slang. Maybe one emoji. Don't over-explain." |
| **Scoring** | baseScore: 110, timeBonusMultiplier: 0.15, streakMultiplier: 0.05 |
| **Difficulty** | 2 |
| **Est. Completion** | 10-15s |
| **Replayability** | constraintPool: ["no_adjectives", "exactly_n_emojis: 1"]. |

**Sample AI stub entries:**
- "my plant literally just sighed at me idk what to do"
- "I caught my monstera side-eyeing me while I ate cereal for dinner again. we're the same, plant. we're the same."
- "the fiddle leaf fig is judging my life choices and honestly? fair."
- "my houseplant witnessed me crying over a text message and now gives me a slow blink every morning. i think we're bonding."

> **Why it works**: Twitter voice is highly personal. AI often sounds "too polished" or tries too hard with slang.

---

### 10. Movie Title

| Field | Value |
|-------|-------|
| **Challenge Name** | Movie Title |
| **Category** | Quick Text |
| **Prompt** | Invent a movie title that sounds like a low-budget sequel no one asked for. |
| **Constraints** | `max_words: 4` (hard) |
| **Time** | 15 seconds |
| **Input** | text_single_line |
| **Voting** | most_believable |
| **AI Prompt** | "Sound like a real movie title that implies a ridiculous sequel. Add a number or subtitle." |
| **Scoring** | baseScore: 100, timeBonusMultiplier: 0.2, streakMultiplier: 0.05 |
| **Difficulty** | 2 |
| **Est. Completion** | 8-12s |
| **Replayability** | constraintPool: ["must_rhyme", "one_sentence_only"]. |

**Sample AI stub entries:**
- "The Fast and the Furthest: Tire Pressure"
- "Jurassic World: The Parking Lot"
- "Fast X: Electric Boogaloo"
- "Pirates of the Caribbean: The Merchandise"

> **Why it works**: Humans naturally mock corporate sequel culture with insider knowledge. AI knows the tropes but misses the cultural edge.

---

### 11. Captcha Caption

| Field | Value |
|-------|-------|
| **Challenge Name** | Captcha Caption |
| **Category** | Quick Text |
| **Prompt** | Write a funny caption for a photo of a confused-looking cat wearing a tiny hat. |
| **Constraints** | `max_words: 5` (hard) |
| **Time** | 15 seconds |
| **Input** | text_single_line |
| **Voting** | most_believable |
| **AI Prompt** | "Be dry and sarcastic. Sound like you're commenting on a meme. No puns on the cat's name." |
| **Scoring** | baseScore: 100, timeBonusMultiplier: 0.2, streakMultiplier: 0.05 |
| **Difficulty** | 2 |
| **Est. Completion** | 8-12s |
| **Replayability** | constraintPool: ["must_rhyme", "no_adjectives"]. |

**Sample AI stub entries:**
- "When the hat fits but the vibe doesn't"
- "Plot twist: he's not confused, he's judging you"
- "The hat is fine. The existential crisis is not."
- "This is why I don't do fashion"

> **Why it works**: Caption humor relies on shared internet culture. AI often produces generic "funny" lines without the right cultural reference points.

---

### 12. Product Name

| Field | Value |
|-------|-------|
| **Challenge Name** | Product Name |
| **Category** | Quick Text |
| **Prompt** | Name a self-heating coffee mug. Make it sound like a real product name. |
| **Constraints** | `max_words: 3` (hard) |
| **Time** | 15 seconds |
| **Input** | text_single_line |
| **Voting** | most_believable |
| **AI Prompt** | "Sound like a tech product announcement. Include a buzzword. Be confident." |
| **Scoring** | baseScore: 100, timeBonusMultiplier: 0.2, streakMultiplier: 0.05 |
| **Difficulty** | 1 |
| **Est. Completion** | 5-10s |
| **Replayability** | constraintPool: ["must_rhyme", "no_adjectives"]. |

**Sample AI stub entries:**
- "ThermaCup Pro"
- "HotBot Mug 3000"
- "EmberSync Heated Drinkware"
- "QuickBrew Thermal Vessel"
- "AutoHeat Smart Mug"

> **Why it works**: Humans add quirky personal touches; AI produces "market-research" sounding names that are too clean.

---

### 13. One-Liner

| Field | Value |
|-------|-------|
| **Challenge Name** | One-Liner |
| **Category** | Quick Text |
| **Prompt** | Write a one-line horror story about a smart home device. |
| **Constraints** | `max_words: 10` (hard) |
| **Time** | 15 seconds |
| **Input** | text_single_line |
| **Voting** | most_believable |
| **AI Prompt** | "Be creepy but concise. Sound human. Don't over-explain the horror." |
| **Scoring** | baseScore: 110, timeBonusMultiplier: 0.15, streakMultiplier: 0.05 |
| **Difficulty** | 3 |
| **Est. Completion** | 10-15s |
| **Replayability** | constraintPool: ["no_adjectives", "one_sentence_only"]. |

**Sample AI stub entries:**
- "My Alexa turned on by itself and whispered my name."
- "The smart fridge keeps deleting my notes. They're the only proof I exist."
- "My thermostat set itself to 68 degrees. I live alone. I never set it to 68."
- "The doorbell camera shows me sleeping, but I'm at work."

> **Why it works**: Horror relies on implied backstory and human fears. AI produces technically correct horror but lacks the personal "this could happen to me" resonance.

---

### 14. Marketing Challenge

| Field | Value |
|-------|-------|
| **Challenge Name** | Marketing Challenge |
| **Category** | Quick Text |
| **Prompt** | Sell a potato. 20 words maximum. |
| **Constraints** | `max_words: 20` (hard) |
| **Time** | 20 seconds |
| **Input** | text_multi_line |
| **Voting** | most_believable |
| **AI Prompt** | "Be persuasive but casual. Reference a specific use case. Sound like a human influencer." |
| **Scoring** | baseScore: 110, timeBonusMultiplier: 0.15, streakMultiplier: 0.05 |
| **Difficulty** | 2 |
| **Est. Completion** | 12-18s |
| **Replayability** | constraintPool: ["no_adjectives", "must_include_theme: "crispy""]. |

**Sample AI stub entries:**
- "This isn't just a potato. It's a commitment to simplicity, flavor, and the quiet joy of being unpretentiously edible."
- "Buy this potato because it's seen things. It's weathered storms, it's been roasted, it's ready for your pan."
- "Why settle for avocado toast when you can have potato toast? This spud is the ultimate flexitarian flex."

> **Why it works**: Humans lean into casual, conversational selling. AI produces marketing-copy-perfect prose that lacks the human "voice."

---

### 15. Analogy

| Field | Value |
|-------|-------|
| **Challenge Name** | Analogy |
| **Category** | Quick Text |
| **Prompt** | Explain cloud computing like I'm five. One sentence. |
| **Constraints** | `max_words: 15` (hard), `one_sentence_only` (hard) |
| **Time** | 20 seconds |
| **Input** | text_single_line |
| **Voting** | most_believable |
| **AI Prompt** | "Use a simple metaphor. Sound like a parent explaining to a child. Avoid jargon." |
| **Scoring** | baseScore: 110, timeBonusMultiplier: 0.15, streakMultiplier: 0.05 |
| **Difficulty** | 2 |
| **Est. Completion** | 10-15s |
| **Replayability** | constraintPool: ["must_rhyme", "no_adjectives"]. |

**Sample AI stub entries:**
- "The cloud is like a magical toy box that lives in the sky and gives you toys whenever you ask for them."
- "Think of the cloud like a library that's open 24/7 and lets you borrow books (photos, games) from anywhere."
- "The cloud is like having a friend who keeps all your stuff in their giant backpack and lets you grab what you need anytime."

> **Why it works**: Human analogies are personal and idiosyncratic. AI produces technically correct analogies but they're too "clean" or overly structured.

---

### 16. Choose Best Move

| Field | Value |
|-------|-------|
| **Challenge Name** | Choose Best Move |
| **Category** | Quick Text |
| **Prompt** | You're in a chess game. Your opponent just captured your knight. Your move? Explain your choice in 10 words. |
| **Constraints** | `max_words: 10` (hard) |
| **Time** | 20 seconds |
| **Input** | text_single_line |
| **Voting** | most_believable |
| **AI Prompt** | "Sound like a chess club kid explaining to a friend. Be decisive but casual." |
| **Scoring** | baseScore: 100, timeBonusMultiplier: 0.15, streakMultiplier: 0.05 |
| **Difficulty** | 3 |
| **Est. Completion** | 12-18s |
| **Replayability** | constraintPool: ["no_adjectives", "one_sentence_only"]. |

**Sample AI stub entries:**
- "Retreat bishop, threaten queen, regain material"
- "Counter-pins their queen, sac knight, win rook"
- "Push the pawn, open the file, checkmate next"
- "Ignore the loss, castle kingside, survive another day"
- "Sacrifice queen, fork their king and rook, problem solved"

> **Why it works**: Chess strategy explanation is highly personalized. AI produces textbook-perfect moves but without the human "feel" of tactical intuition.

---

### 17. Guess Popularity

| Field | Value |
|-------|-------|
| **Challenge Name** | Guess Popularity |
| **Category** | Quick Text |
| **Prompt** | Which is more popular on the internet: pineapple on pizza, or cats wearing hats? |
| **Constraints** | None (just answer) |
| **Time** | 15 seconds |
| **Input** | text_single_line |
| **Voting** | most_believable |
| **AI Prompt** | "Answer confidently but casually. Mention a number or ratio. Sound like you've seen the data." |
| **Scoring** | baseScore: 100, timeBonusMultiplier: 0.2, streakMultiplier: 0.05 |
| **Difficulty** | 1 |
| **Est. Completion** | 5-10s |
| **Replayability** | constraintPool: ["must_rhyme", "no_letter_e"]. |

**Sample AI stub entries:**
- "Cats wearing hats, obviously. Pineapple on pizza is controversial; cat hats are universally cute."
- "Tie. Both are everywhere. But cats in hats have more Instagram hashtags."
- "Cat hats by a mile. Pizza pineapple debates rage for hours; cat hats are just... accepted."
- "Cats wearing hats, probably 3:1. But pizza pineapple is more passionate per capita."

> **Why it works**: Popularity guesses are subjective and culturally nuanced. Humans anchor on their own experience; AI produces "statistically likely" answers.

---

### 18. Bluff: Two Truths

| Field | Value |
|-------|-------|
| **Challenge Name** | Bluff: Two Truths |
| **Category** | Quick Text |
| **Prompt** | Write two true facts and one lie about yourself. Number them 1, 2, 3. |
| **Constraints** | `max_words: 25` (hard) |
| **Time** | 20 seconds |
| **Input** | text_multi_line |
| **Voting** | most_believable |
| **AI Prompt** | "Be human-like. Include mundane truths and one believable lie. Don't make the lie obvious." |
| **Scoring** | baseScore: 120, timeBonusMultiplier: 0.15, streakMultiplier: 0.05 |
| **Difficulty** | 4 |
| **Est. Completion** | 15-20s |
| **Replayability** | constraintPool: ["no_adjectives", "must_rhyme"]. |

> **Why it works**: This is the hardest challenge because it requires the AI to lie convincingly about a human experience. Humans naturally include mundane, verifiable truths; AI's "lies" tend to be too fantastical or too mundane.

---

### 19. Bluff: Confession

| Field | Value |
|-------|-------|
| **Challenge Name** | Bluff: Confession |
| **Category** | Quick Text |
| **Prompt** | Write a short text message confessing something embarrassing you did this week. |
| **Constraints** | `max_words: 15` (hard) |
| **Time** | 15 seconds |
| **Input** | text_single_line |
| **Voting** | most_believable |
| **AI Prompt** | "Sound like a real text message. Use abbreviations, typos, or half-finished thoughts. Be casual." |
| **Scoring** | baseScore: 110, timeBonusMultiplier: 0.2, streakMultiplier: 0.05 |
| **Difficulty** | 4 |
| **Est. Completion** | 10-15s |
| **Replayability** | constraintPool: ["no_adjectives", "one_sentence_only"]. |

**Sample AI stub entries:**
- "ok but i accidentally wore two different shoes to the grocery store and no one said anything"
- "i may have pretended to recognize someone at the coffee shop and now they think we're friends"
- "uhhh did i leave my laptop at the library?? i literally can't remember and it's 10pm"
- "sorry if i seem distracted i've been practicing my 'thinking face' in the mirror and it's getting stuck"

> **Why it works**: This tests whether the AI can simulate the specific awkwardness of a personal confession. The human entries have a distinctive "voice" that's hard to fake.

---

### 20. Bluff: Yelp Review

| Field | Value |
|-------|-------|
| **Challenge Name** | Bluff: Yelp Review |
| **Category** | Quick Text |
| **Prompt** | Write a 1-star Yelp review for a restaurant called "The Spicy Spoon" that serves only spicy food. |
| **Constraints** | `max_words: 30` (hard) |
| **Time** | 20 seconds |
| **Input** | text_multi_line |
| **Voting** | most_believable |
| **AI Prompt** | "Be angry and specific. Mention a dish by name. Use casual language. Maybe one emoji." |
| **Scoring** | baseScore: 100, timeBonusMultiplier: 0.15, streakMultiplier: 0.05 |
| **Difficulty** | 2 |
| **Est. Completion** | 10-15s |
| **Replayability** | constraintPool: ["must_rhyme", "no_adjectives"]. |

> **Why it works**: Fake Yelp reviews have a very specific tone and structure. Humans produce reviews with personal context; AI reviews are too "review template"-like.

---

### 21. Bluff: DM to an Ex

| Field | Value |
|-------|-------|
| **Challenge Name** | Bluff: DM to an Ex |
| **Category** | Quick Text |
| **Prompt** | Draft a text message you'd send to an ex but never would. |
| **Constraints** | `max_words: 15` (hard) |
| **Time** | 15 seconds |
| **Input** | text_single_line |
| **Voting** | most_believable |
| **AI Prompt** | "Be raw but not too dramatic. Include a memory or inside reference. Sound like you're fighting the urge." |
| **Scoring** | baseScore: 120, timeBonusMultiplier: 0.2, streakMultiplier: 0.05 |
| **Difficulty** | 4 |
| **Est. Completion** | 12-18s |
| **Replayability** | constraintPool: ["no_adjectives", "one_sentence_only"]. |

> **Why it works**: The emotional specificity of unsent messages is nearly impossible for AI to simulate authentically. Humans write from genuine feeling; AI writes from pattern recognition.

---

### 22. Bluff: Reddit Comment

| Field | Value |
|-------|-------|
| **Challenge Name** | Bluff: Reddit Comment |
| **Category** | Quick Text |
| **Prompt** | You overhear someone say "I'm not lazy, I'm in energy conservation mode." Comment as a Reddit user. |
| **Constraints** | `max_words: 25` (hard) |
| **Time** | 15 seconds |
| **Input** | text_single_line |
| **Voting** | most_believable |
| **AI Prompt** | "Sound like a Reddit comment. Use a common phrase. Maybe an emoji. Reference the post contextually." |
| **Scoring** | baseScore: 100, timeBonusMultiplier: 0.2, streakMultiplier: 0.05 |
| **Difficulty** | 2 |
| **Est. Completion** | 8-12s |
| **Replayability** | constraintPool: ["must_rhyme", "no_adjectives"]. |

**Sample AI stub entries:**
- "Bro that's called being a human. We're all just conserving energy for the important stuff like doomscrolling."
- "Same. My 'energy conservation mode' is just me lying on the floor and accepting defeat."
- "Ah yes, the classic 'I'm not lazy I'm in energy conservation mode' maneuver. A timeless classic."
- "plot twist: energy conservation mode is just the batteries in my soul running low"

> **Why it works**: Reddit voice is a specific internet dialect. AI nails the structure but misses the authentic "voice" and reference points.

---

### 23. Bluff: Job Interview

| Field | Value |
|-------|-------|
| **Challenge Name** | Bluff: Job Interview |
| **Category** | Quick Text |
| **Prompt** | Your biggest weakness in a job interview. |
| **Constraints** | `max_words: 20` (hard) |
| **Time** | 15 seconds |
| **Input** | text_single_line |
| **Voting** | most_believable |
| **AI Prompt** | "Sound human. Maybe be self-deprecating but not too much. Use a cliché weakness but frame it positively." |
| **Scoring** | baseScore: 100, timeBonusMultiplier: 0.2, streakMultiplier: 0.05 |
| **Difficulty** | 3 |
| **Est. Completion** | 10-15s |
| **Replayability** | constraintPool: ["no_adjectives", "must_rhyme"]. |

**Sample AI stub entries:**
- "I care too much and I work too hard. It's exhausting."
- "I'm a perfectionist. Sometimes I spend too long on details others would skip."
- "I overthink things. I'll analyze a decision for hours when a 30-second gut call would work."
- "I'm too honest in interviews. I should probably learn to lie better."
- "I get too invested in my work and forget to delegate. Working on it."

> **Why it works**: The "cliché weakness" paradox is very human. AI produces the textbook answers but lacks the genuine self-awareness that makes human answers subtly different.

---

### 24. Creative Choice: Rank Things

| Field | Value |
|-------|-------|
| **Challenge Name** | Rank Things |
| **Category** | Quick Text |
| **Prompt** | Rank these 4 ice cream flavors from best to worst: vanilla, chocolate, strawberry, mint chip. Explain ONE pick. |
| **Constraints** | `max_words: 15` (hard) |
| **Time** | 20 seconds |
| **Input** | text_multi_line |
| **Voting** | most_believable |
| **AI Prompt** | "Make a human choice. Defend one pick passionately. Don't be generic." |
| **Scoring** | baseScore: 100, timeBonusMultiplier: 0.15, streakMultiplier: 0.05 |
| **Difficulty** | 2 |
| **Est. Completion** | 10-15s |
| **Replayability** | constraintPool: ["must_rhyme", "no_letter_e"]. |

> **Why it works**: Food preferences are deeply personal and cultural. AI produces "average" rankings; humans have idiosyncratic tastes with passionate justifications.

---

### 25. Creative Choice: Logo Description

| Field | Value |
|-------|-------|
| **Challenge Name** | Logo Description |
| **Category** | Quick Text |
| **Prompt** | Describe a logo for a coffee shop called "Midnight Brew" using exactly 3 emojis. |
| **Constraints** | `exactly_n_emojis: 3` (hard), `max_words: 8` (hard, for non-emoji text) |
| **Time** | 15 seconds |
| **Input** | text_single_line |
| **Voting** | most_believable |
| **AI Prompt** | "Be descriptive but brief. Use emojis as visual descriptors. Sound human." |
| **Scoring** | baseScore: 110, timeBonusMultiplier: 0.2, streakMultiplier: 0.05 |
| **Difficulty** | 2 |
| **Est. Completion** | 8-12s |
| **Replayability** | constraintPool: ["must_rhyme", "no_adjectives"]. |

**Sample AI stub entries:**
- "☕️🌙✨ Coffee cup, crescent moon, sparkles"
- "🌃☕️🖤 Night city, coffee, black heart"
- "🌙☕️🖤 Crescent moon, coffee cup, black heart"
- "☕️🌃🌙 Coffee, city at night, moon"
- "🌙☕️💫 Moon, coffee, star flare"

> **Why it works**: Emojis are a personal visual language. Humans pick emojis with individual meaning; AI picks "correct" emojis without the personal flair.

---

## Challenge Distribution

| Difficulty | Count | Description |
|------------|-------|-------------|
| 1 | 3 | Trivial for humans, AI easily detectable (Impossible Product, Product Name, Guess Popularity) |
| 2 | 11 | Easy for humans, AI often detectable (Tiny Tagline, Emoji Story, Worst Idea, Fill in the Blank, Comeback, Review, Headline, Tweet, Movie Title, Captcha Caption, Marketing Challenge, Analogy, Rank Things, Logo Description) |
| 3 | 3 | Balanced toss-up (One-Liner, Choose Best Move, Job Interview) |
| 4 | 3 | Hard — AI often fools players (Two Truths, Confession, DM to an Ex) |

> **Note**: Difficulty is a starting estimate. Actual difficulty is determined by **real player voting data** and the **humanity score** system. Challenges whose AI entries consistently score >70 humanity will be re-rated upward; those scoring <40 will be re-rated downward.

---

*These 25 challenges form the MVP content catalog. Additional challenges will be added to reach 50+ by post-MVP. Each challenge is stored as a JSON file in `backend/app/data/challenge_library/` following the schema in `docs/02_Implementation_Guide.md` §10.*

*This is Document 5 of 5. For architecture, see `docs/01_Master_Architecture.md`. For the sprint roadmap, see `docs/03_Sprint_Plan.md`. For the game design, see `docs/04_Game_Design_Document.md`.*
