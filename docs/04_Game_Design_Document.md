# Man vs. Machine — Game Design Document (GDD)

> **Version:** 1.0
> **Status:** Draft — Sprint 0 (Pre-MVP)
> **Audience:** Game designers, developers, AI coding agents, product stakeholders
> **Related:** See `docs/01_Master_Architecture.md` for architecture and `docs/05_Micro_Challenge_Library.md` for challenge templates.

---

## Table of Contents

1.  Overview
    - 1.1 Core Concept
    - 1.2 The Bluff Mode
    - 1.3 Interaction Type Framework
2.  Core Gameplay Loop
    - 2.1 Round State Machine
    - 2.2 Match Flow Diagram
3.  Challenge System
    - 3.1 Micro-Challenge Philosophy
    - 3.2 Challenge Object Model
    - 3.3 Constraint Engine
    - 3.4 Challenge Categories (Interaction Types)
    - 3.5 Difficulty & Rotation
4.  AI Framework
    - 4.1 AI as the Opponent
    - 4.2 AI Prompt Design
    - 4.3 AI Fairness Rules
    - 4.4 AI "Humanity" Scoring
5.  Voting & Judging
    - 5.1 Anonymous Presentation
    - 5.2 Voting Criteria
    - 5.3 Reveal System
6.  Scoring & Progression
    - 6.1 Individual Round Scoring
    - 6.2 Player Rating (ELO-style)
    - 6.3 Streaks & Consistency
    - 6.4 Leaderboards
7.  Matchmaking & Sessions
    - 7.1 Single-Player vs. Solo Queue
    - 7.2 Multiplayer Rounds
8.  Player Psychology & Retention
    - 8.1 The Wordle Loop
    - 8.2 Daily & Weekly Challenges
    - 8.3 Streak Motivation
9.  Visual & Audio Direction
    - 9.1 Aesthetic
    - 9.2 UI Animation Principles
    - 9.3 Sound Design
10. Accessibility
11. Monetization & Economy
    - 11.1 Cosmetic Economy
    - 11.2 Battle Pass (Future)
12. Social Features
    - 12.1 Replay Sharing
    - 12.2 Community Challenges (Future)
13. Tournament & Competitive (Future)
14. Balancing Philosophy
15. Key Metrics

---

## 1. Overview

### 1.1 Core Concept

**Man vs. Machine** is a micro-challenge game where humans and AI compete side-by-side on the same prompt, and the player's task is to identify which answer came from the machine.

The game is **not** about AI being "better" than humans. It is about **human motivation vs. AI effort** — an AI has infinite patience and can spend minutes polishing an answer; a human has 15–60 seconds before they think, "good enough." The game exploits this asymmetry through **social deduction**: given two anonymous entries, the player must guess which one the AI wrote.

Each round takes **15–60 seconds** from prompt to reveal. The core mode (Bluff) is designed to be played in 2–3 minute sessions, like Wordle or GeoGuessr.

### 1.2 The Bluff Mode

This is the **default and core game mode**. Every round works as follows:

1.  A challenge is presented (e.g., "Invent a product nobody needs. Maximum 6 words.")
2.  The human player submits an answer within the time limit.
3.  The AI generates its own answer to the same prompt.
4.  Both answers are presented anonymously — labeled "Entry A" and "Entry B".
5.  The player votes: is **A** the AI, or is **B** the AI?
6.  The entries are revealed: **A = Human, B = AI** (or vice versa).
7.  The player scores points if they guessed correctly.

**The meta-game**: Over time, the system tracks whether players consistently misattribute high-quality answers to AI (the "AI is obviously better" bias) or low-effort answers to humans (the "humans are sloppy" bias). These biases become part of the player's profile and feed into matchmaking and challenge selection.

### 1.3 Interaction Type Framework

Instead of organizing challenges by subject matter (Writing, Art, Programming), the game is organized by **interaction type** — what the player *does*:

| Type | Description | Examples | Input |
|------|-------------|----------|-------|
| **Quick Text** | Text-based creativity under tight constraints | Slogan, product name, comeback, caption, one-liner | Text input |
| **Bluff** | Guess which entry is AI (core meta-mode) | Wraps any Quick Text challenge | Multiple choice / click |
| **Visual** | Simple visual creation or recognition | Tiny sketch, color palette, shape arrangement | Canvas / click |
| **Build** | Arrange or assemble objects | Block arrangement, simple engineering | Drag / drop |
| **Explain** | Explain a concept simply | ELI5, one-sentence analogy | Text input |
| **Strategy** | Tactical decision-making | Choose best move, rank items | Click / drag |

**MVP supports only Quick Text + Bluff** (which is really one mode: Quick Text challenge + anonymous voting). Visual, Build, Explain, and Strategy are post-MVP.

---

## 2. Core Gameplay Loop

### 2.1 Round State Machine

Each round is a deterministic state machine with real-time transitions:

```
IDLE
  │
  │  Prompt assigned + time started
  ▼
WRITING     ← player writes their answer (15–60s timer)
  │
  │  Timer expires OR player submits
  ▼
REVEAL_AI   ← AI generates answer
  │
  │  AI response received
  ▼
VOTING      ← both entries shown anonymously, player votes
  │
  │  Player submits vote
  ▼
SCORE       ← result revealed, points awarded, rating updated
  │
  │  Animation + stat update (~2s)
  ▼
RESULT      ← round complete, transition to next
```

**State details:**

- **IDLE → WRITING**: Triggered by prompt assignment. All clients receive the same prompt simultaneously.
- **WRITING → REVEAL_AI**: Two exit conditions: (a) player submits, or (b) timer expires. The player's submission time is recorded for scoring nuance (faster = minor bonus). If the timer expires, the player's answer is submitted automatically (may be empty).
- **REVEAL_AI → VOTING**: Triggered when the AI response is received. The AI response is fetched from the backend's AI service layer, which calls the configured provider API.
- **VOTING → SCORE**: Triggered by player vote.
- **SCORE → RESULT → IDLE**: Score is calculated, displayed, and after a brief animation the next round begins.

### 2.2 Match Flow Diagram

A typical session is 3 rounds (like Wordle's 6 guesses, but shorter rounds):

```
Session Start
  │
  ├─ Round 1: Challenge A (e.g., "Slogan")
  │     └─ Human writes → AI writes → Vote → Score
  │
  ├─ Round 2: Challenge B (e.g., "Product Name")
  │     └─ Human writes → AI writes → Vote → Score
  │
  └─ Round 3: Challenge C (e.g., "Caption")
        └─ Human writes → AI writes → Vote → Score

  │
  ▼
Session Summary: Accuracy %, Avg Humanity Score, ELO Change
  │
  ▼
Back to Home / Next Session
```

**Session length**: ~2–4 minutes for 3 rounds. Each round is ~30–60 seconds.

---

## 3. Challenge System

### 3.1 Micro-Challenge Philosophy

Every challenge is designed around the **30-second fun principle**. No open-ended creative tasks that take minutes. Instead:

- **15–60 seconds** to complete
- **One clear objective** (no ambiguity about what to do)
- **Immediate reveal** (no waiting for other players)
- **Immediate scoring** (no delayed gratification)

**Constraint-based design**: Every challenge is defined by a small set of parameters. The game engine treats these as data, not hardcoded logic:

| Parameter | Description | Example |
|-----------|-------------|---------|
| Prompt | The creative instruction | "Invent a product nobody needs." |
| Constraints | Text limits, word limits, style rules | "Maximum 6 words", "Must rhyme" |
| Time Limit | Seconds allowed | 20 |
| Input Type | What the player submits | Text (single-line or multi-line) |
| Voting Criteria | How entries are judged | Funniest, Most Creative, Most Believable |

### 3.2 Challenge Object Model

```json
{
  "id": "challenge_slogan_01",
  "name": "Tiny Tagline",
  "interactionType": "Quick Text",
  "prompt": "Write a slogan for a dragon-owned bakery.",
  "constraints": [
    {"type": "max_words", "value": 5},
    {"type": "must_include_theme", "value": "fire"}
  ],
  "timeLimitSeconds": 15,
  "inputType": "text_single_line",
  "votingCriteria": "most_memorable",
  "aiPromptTemplate": "You are a creative brand strategist. Write a slogan for a dragon-owned bakery. Maximum 5 words. The slogan must reference fire or flames.",
  "difficulty": 2,
  "scoringRules": {
    "baseScore": 100,
    "timeBonusMultiplier": 0.1,
    "streakMultiplier": 0.05
  },
  "replayability": {
    "dailyVariants": 3,
    "constraintPool": ["max_words", "must_rhyme", "no_adjectives", "must_include_theme"]
  }
}
```

Challenges are stored as JSON data, not hard-coded logic. The engine applies constraints at runtime. See `docs/05_Micro_Challenge_Library.md` for 20+ fully-specified examples.

### 3.3 Constraint Engine

Constraints are applied as middleware around the prompt. Each constraint type has a validator:

| Constraint Type | Validator Behavior |
|-----------------|-------------------|
| `max_words` | Rejects input with more than N words |
| `max_characters` | Rejects input exceeding N characters |
| `must_rhyme` | Post-submission check (soft constraint) |
| `no_adjectives` | Post-submission check (soft constraint) |
| `must_include_theme` | Must contain a keyword from a theme list |
| `exactly_n_emojis` | Must contain exactly N emojis |
| `no_letter_e` | Post-submission check (soft constraint) |

**Hard constraints** (max_words, max_characters) prevent submission. **Soft constraints** (must_rhyme, no_adjectives) are tracked but don't block — they affect scoring and the AI's humanity rating.

### 3.4 Challenge Categories (Interaction Types)

**MVP Categories:**

| Type | Count | Description |
|------|-------|-------------|
| **Quick Text** | ~12 | Slogans, product names, captions, comebacks, headlines |
| **Bluff** | 1 (meta-mode) | Wraps any Quick Text challenge — the core voting/decision mode |

**Post-MVP Categories** (documented in the architecture but not implemented):

| Type | Description |
|------|-------------|
| **Visual** | Tiny sketches, color palettes, shape arrangement, pattern finding |
| **Build** | Block arrangement, tower construction, domino sequences |
| **Explain** | ELI5 explanations, one-sentence summaries, analogies |
| **Strategy** | Best move selection, resource allocation, ranking tasks |

### 3.5 Difficulty & Rotation

**Difficulty** is a 1–5 scale:
- **1**: Trivially human (AI might overcomplicate)
- **2**: Easy for humans, easy to detect as AI
- **3**: Balanced — a real toss-up
- **4**: Hard to detect — AI mimics human flaws well
- **5**: AI-dominated (humans rarely guess correctly)

**Rotation**:
- **Daily Challenge**: One pre-selected challenge per day, same for all players
- **Challenge Pool**: Each session pulls from a pool of 20–30 challenges
- **Daily Variants**: Same challenge name, rotated constraints (e.g., "max 5 words" vs. "max 8 words" vs. "must rhyme")

---

## 4. AI Framework

### 4.1 AI as the Opponent

The AI is not an "opponent" to beat. It is a **collaborative entry** in the same challenge. The game's tension comes from:

1.  **Can the AI mimic human creativity under constraints?**
2.  **Can humans detect the AI's fingerprints?**

The AI is given the **exact same prompt and constraints** as the human. However, the AI has no time limit — it can spend however long it needs. This creates the fundamental asymmetry the game exploits.

### 4.2 AI Prompt Design

The AI prompt is constructed from the challenge template:

```
Prompt: {challenge.prompt}
Constraints: {challenge.constraints formatted as natural language}
Style: {challenge.aiPromptStyle} (e.g., "Match the style of a casual Twitter user", "Be deliberately imperfect")

Your response should appear as if written by a human under a {timeLimitSeconds} second time constraint.
Do NOT explicitly acknowledge that you are an AI.
Do NOT mention that you are responding to a prompt.
Do NOT add explanations or commentary. Just output the entry.
```

**Key design decisions:**
- The AI is instructed to be "deliberately imperfect" — to introduce human-like flaws (minor grammar issues, overly casual phrasing, off-topic tangents)
- The AI is NOT told to be "as good as possible" — that would make detection impossible and the game frustrating

### 4.3 AI Fairness Rules

1.  **Same prompt, same constraints**: The AI receives identical instructions to the human.
2.  **No meta-knowledge**: The AI does not know it is competing against a human.
3.  **Time asymmetry is intentional**: The AI has unlimited time; the human has 15–60 seconds. This is the core game mechanic, not a bug.
4.  **No system prompt leakage**: The AI's system prompt must never mention being an AI or the game's rules.
5.  **Provider abstraction**: The AI layer supports multiple providers (OpenAI, Anthropic, local models). The game logic does not depend on a specific provider's output format.

### 4.4 AI "Humanity" Scoring

When a player correctly identifies the AI entry, that entry is scored for **humanity** — how well it fooled (or failed to fool) the player:

- **If the player guessed correctly** (identified the AI entry): the AI entry gets a LOWER humanity score (it was detectable)
- **If the player guessed incorrectly** (thought their own entry was AI): the **human** entry gets a higher humanity score (the human entry was AI-like enough to fool the player into thinking it was the machine)

**Humanity Score** is a per-entry metric (0–100) that aggregates across all rounds:
- High humanity = the entry was convincing enough to be mistaken for the other party
- Low humanity = the entry was easily identifiable as AI (or as human)

This creates a **meta-scoring layer**: players can achieve high humanity scores by writing in a way that seems AI-generated (overly polished, "too perfect"), while the AI tries to write with human imperfections.

---

## 5. Voting & Judging

### 5.1 Anonymous Presentation

Entries are presented in a randomized order. The player sees:

```
Challenge: "Invent a product nobody needs."

Entry A: The Toaster Shower — a showerhead that also toasts bread.
Entry B: A self-stirring sock that you wear on your foot to stir soup while walking.

Which entry was written by the AI?
[A is AI]  [B is AI]
```

The human player cannot see:
- Which entry is their own
- Which entry is the AI's
- Any timestamps or metadata

### 5.2 Voting Criteria

The voting criteria are tied to the challenge type:

| Criteria | Description |
|----------|-------------|
| **Funniest** | Which entry is funnier? |
| **Most Creative** | Which entry is more creative/original? |
| **Most Believable** | Which entry seems like something a human would actually write? (used in Bluff mode) |
| **Best** | General quality judgment (used in community voting modes) |

In **Bluff mode** (MVP), the criterion is always "Most Believable" — the player guesses which is AI, implicitly judging believability.

### 5.3 Reveal System

After voting:

```
✓ Correct!

Your entry:  Entry A — The Toaster Shower
AI's entry:  Entry B — A self-stirring sock...

The AI wrote Entry B. You fooled 42% of players with your entry.
The AI's humanity score for this entry: 67/100
```

The reveal includes:
- Which entry was human, which was AI
- A brief explanation of why the AI's entry was detectable (if the player was correct)
- The player's updated humanity score for their entry
- The AI's updated humanity score for its entry

---

## 6. Scoring & Progression

### 6.1 Individual Round Scoring

| Action | Points |
|--------|--------|
| Correct guess (identified AI) | 100 |
| Wrong guess | 0 |
| Submit before time limit | +10 × (time remaining / time limit) (capped at +50) |
| Daily challenge completed | +50 bonus |
| 3-round accuracy streak (all correct) | +75 bonus |

### 6.2 Player Rating (ELO-style)

Players have a **Detection Rating** (1000 initial):

- Correct guess: rating increases by `K × (1 - expected)`
- Wrong guess: rating decreases by `K × (0 - expected)`
- `expected = 1 / (1 + 10^((AI_rating - player_rating) / 400))`
- `K = 32` for new players (< 50 rounds), `K = 16` thereafter

The AI also has a **Humanity Rating** per challenge type — how often its entries fool players. This feeds back into prompt engineering (higher-rated AI prompts are used more).

### 6.3 Streaks & Consistency

| Streak Type | Reward |
|-------------|--------|
| Correct guess streak (3+) | "Sharp Eye" badge |
| Daily challenge streak (7+) | "Devotee" title |
| Perfect session (3/3 correct) | "Psychic" badge |
| 100 rounds played | "Veteran" title |

### 6.4 Leaderboards

- **Daily**: Top accuracy for today's challenge
- **Weekly**: Top accuracy this week
- **All-time**: Highest Detection Rating
- **Streak**: Longest current correct-guess streak

---

## 7. Matchmaking & Sessions

### 7.1 Single-Player vs. Solo Queue

**MVP**: All rounds are **against the AI** (human vs AI entry). No real-time multiplayer. The "voting" is the player guessing which entry is AI.

**Post-MVP**: True multiplayer Bluff mode — two humans compete, and a third player votes. Or three entries (2 humans + 1 AI) and the player must find the AI.

### 7.2 Multiplayer Rounds

Post-MVP multiplayer:
- 3–6 players per match
- Each round: all players submit simultaneously, one entry is AI
- Players vote on which is AI
- Scoring based on accuracy + how many people were "fooled" by your entry

---

## 8. Player Psychology & Retention

### 8.1 The Wordle Loop

The game targets a **2–4 minute daily session**:

- Open the app
- Play today's daily challenge (3 rounds, ~2 min)
- See your score + humanity stats
- Share a result (e.g., "3/3 — I detected the AI every time!")
- Close the app

This is the **habit-forming loop**: quick, satisfying, shareable.

### 8.2 Daily & Weekly Challenges

- **Daily Challenge**: One pre-selected challenge, same for all players. Resets at midnight UTC.
- **Weekly Challenge**: A themed set (e.g., "All Movie Slogans Week") with 5 rounds.
- **Practice Mode**: Unlimited random challenges from the pool.

### 8.3 Streak Motivation

A visible streak counter on the home screen motivates daily returns. Breaking the streak is mildly penalized (lose 10% of current streak bonus, not a hard reset).

---

## 9. Visual & Audio Direction

### 9.1 Aesthetic

**Minimalist, fast-loading, no distractions**. The UI should fade into the background so the focus is on reading and comparing entries.

- Clean sans-serif typography (Inter or similar)
- High contrast for accessibility
- Subtle animations for state transitions (fade, slide)
- Color palette: dark mode default, light mode optional
- Accent colors: blue (trust), green (correct), red (incorrect)

### 9.2 UI Animation Principles

| Transition | Animation | Duration |
|------------|-----------|----------|
| Prompt appear | Fade in + slide up | 200ms |
| Timer urgency | Color shift (green → yellow → red) | 300ms |
| Entry reveal | Flip card animation | 400ms |
| Voting result | Scale + color pulse | 300ms |
| Progress bar | Smooth fill | Matches timer |

### 9.3 Sound Design

MVP sound effects (all subtle, toggleable):

| Event | Sound |
|-------|-------|
| Timer warning (10s left) | Soft pulse tone |
| Submit | Gentle "click" |
| Vote cast | Soft "chime" |
| Correct | Pleasant "ding" |
| Wrong | Subtle "thud" |
| Round transition | Whoosh |

No background music in MVP (distraction from the core loop). Post-MVP: ambient focus playlists.

---

## 10. Accessibility

| Feature | Implementation |
|---------|---------------|
| Colorblind mode | Text labels + patterns, not just color |
| Text scaling | CSS `em` units, user-adjustable |
| Keyboard navigation | Full tab order, Enter to submit |
| Reduced motion | `prefers-reduced-motion` media query |
| Screen reader | ARIA labels on all interactive elements |
| Contrast | WCAG AA minimum (4.5:1) |
| Dark mode | System preference detection |

---

## 11. Monetization & Economy

### 11.1 Cosmetic Economy (Future)

- **Titles**: Earned through achievements (e.g., "Dragon Whisperer" for 100 slogan challenges)
- **Entry Frames**: Cosmetic borders around your entries in reveal
- **Themes**: Alternative color schemes for the UI
- **Reaction Emotes**: During multiplayer voting, react to entries with emotes

All cosmetics are earned, not purchased. No pay-to-win, no paywall for core gameplay.

### 11.2 Battle Pass (Future)

A seasonal progression system with free and premium tracks. Premium track (~$5) unlocks additional cosmetics and early access to new challenge types.

### 11.3 No Monetization in MVP

The MVP is completely free. Monetization discussion is intentionally deferred to ensure the core game loop is solid first.

---

## 12. Social Features

### 12.1 Replay Sharing

After a round, players can share:
- A text summary ("I got 2/3 today — the AI's slogan was too polished, I should have known!")
- A shareable image card with the challenge, entries, and result
- Link to replay the exact round (entries anonymized, no personal data)

### 12.2 Community Challenges (Future)

Players can submit their own prompts/challenges for community review and potential addition to the library.

---

## 13. Tournament & Competitive (Future)

- **Ranked Mode**: ELO ladder with seasonal resets
- **Bracket Tournaments**: Weekly elimination brackets
- **Creator Tournaments**: Community-submitted challenges in a bracket format

Not in MVP. Documented for future expansion.

---

## 14. Balancing Philosophy

The game's balance hinges on a fundamental question: **Is the AI already better than us at creative micro-tasks?**

The answer depends on the challenge. For highly-constrained creative tasks (slogans, product names, captions), modern LLMs can produce genuinely clever answers. But they also exhibit telltale patterns:

- **Over-polished**: Responses are often too grammatically perfect
- **Cliché-heavy**: Relies on familiar tropes and patterns from training data
- **Lacks personal voice**: No idiosyncratic phrasing, no inside-joke references
- **Tries too hard**: When given a silly prompt, sometimes over-delivers with elaborate reasoning

The AI is explicitly instructed to introduce flaws to counteract these tendencies. The **humanity score** tracks how well this works.

**Balance is dynamic**: If AI humanity scores consistently above 80 (too good at fooling), prompts are adjusted to encourage more "human" flaws. If scores drop below 50 (too easy to detect), the AI is given more freedom to polish.

---

## 15. Key Metrics

| Metric | Target (MVP) |
|--------|-------------|
| Daily active users | 100 (post-launch) |
| Daily challenge completion rate | > 60% |
| Average session length | 2–4 minutes |
| 7-day retention | > 40% |
| Average rounds per session | 3 |
| AI detection accuracy (player) | ~65% (not too easy, not too hard) |
| AI humanity score (average) | ~60/100 (balanced) |
| Load time (web) | < 2 seconds |

---

*This is Document 4 of 5. For architecture, see `docs/01_Master_Architecture.md`. For implementation details, see `docs/02_Implementation_Guide.md`. For challenge definitions, see `docs/05_Micro_Challenge_Library.md`.*
