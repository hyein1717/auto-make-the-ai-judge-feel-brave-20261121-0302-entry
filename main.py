"""Make the AI judge feel brave — a slow, steady text.

The program builds one short text (1-280 Unicode code points) and writes it
to /output/entry.txt. The text is assembled from three quiet sentences — a
scene, a small steady action, a lingering thought — chosen from a few hundred
hand-written combinations by a heuristic scorer, so the result is
deterministic and the same on every run.

Design, from the judge's brief (most important first):
  1. Relax: slow the reading down, steady the reader. Long vowels, commas,
     unhurried clauses; nothing rushed, nothing loud.
  2. Courage from the text itself, never from being told: no imperatives,
     no "you can", no "breathe", no "be brave". A scene that *shows* a
     steady hand is braver than a sentence that orders one.
  3. Craft: rhythm and pacing that slow the reader; plain, concrete, gentle
     words; nothing that could be cut.
  4. Linger: an image the reader can return to after the last line.
  5. Freshness: its own voice and images, no stock wellness phrases, no
     AI cliches (tapestry, whispering winds, echoes, symphony).

Standard library only. No network, no input, no randomness.
"""

import os

MAX_CHARS = 280
TARGET_LOW = 238
TARGET_HIGH = 266

CONFIG = {
    "max_chars": MAX_CHARS,
    "target_low": TARGET_LOW,
    "target_high": TARGET_HIGH,
    "slow_words": ("slow", "slowly", "unhurried", "still", "steady",
                   "one", "then", "again", "low", "soft", "warm"),
    "sensory_words": ("rain", "steam", "kettle", "tea", "fire", "pine",
                      "gold", "wool", "snow", "sea", "lamp", "clock",
                      "bread", "wood", "glass", "river", "dusk", "sun"),
}

# Sentence 1 — the scene. Quiet, concrete, evening.
OPENINGS = [
    "Late rain on the tin roof, slow as a held breath.",
    "Snow settles on the fence post, one flake, then another.",
    "The old lighthouse keeper climbs the stairs one at a time, palm flat on the cool rail.",
    "Evening comes down over the harbour like a grey blanket being shaken out.",
    "In the back room, the clock ticks the same note it has ticked for forty years.",
    "Dusk pools in the corners of the workshop, and the sawdust smells of pine.",
    "The river moves past the mill wheel at the pace of someone with nowhere to be.",
    "Low sun lays long bars of gold across the kitchen floor.",
    "The first stars come out over the allotments, one by one, like lamps being lit.",
    "Rain draws thin lines down the window, and the room behind it glows amber.",
]

# Sentence 2 — a small, steady action. Nothing heroic; a hand that knows its work.
MIDDLES = [
    "Someone sets the kettle down without hurrying, and the steam rises in one unbroken thread.",
    "He pours his tea, sits down, and lets the dark do what the dark does.",
    "The dog sighs in her sleep, and the fire ticks softly in the grate.",
    "She folds the last of the laundry, square corners, slow hands, and stacks it by the door.",
    "The lamp turns whether or not anyone is watching, and the sea keeps its own slow time.",
    "He wipes the workbench clean, hangs the tools in their places, and closes the door on the day.",
    "A cat kneads the blanket once, twice, then settles, warm and certain of the spot.",
    "The kettle sings low, the cup warms her hands, and the window fogs at the edges.",
    "He butters the bread, sets the plate down square on the table, and eats without haste.",
    "She winds the clock, listens for the catch, and nods when it holds.",
]

# Sentence 3 — the lingering thought. An image to return to.
CLOSINGS = [
    "Nothing here needs fixing tonight.",
    "Morning will come when it comes; for now the house holds still, and still is enough.",
    "The dark outside can wait; the light inside is enough, and it is staying.",
    "What is done is done, and what is left can wait until the light comes back.",
    "The night is long, but the room is warm, and warm is a kind of answer.",
    "No hurry lives here now, only the tick of the clock, keeping its promise.",
    "Tomorrow can have its turn. Tonight belongs to the lamplight and the rain.",
    "And the quiet, once noticed, stays: a small room inside the noise, with the door left open.",
    "The lamp stays lit. That is the whole of it, and it is plenty.",
    "Somewhere a kettle cools, a page waits, and the world keeps turning, gently.",
]

BANNED = (
    "tapestry", "whisper", "echo", "symphony", "breathe", "breathwork",
    "brave", "courage", "fear", "worry", "anxiety", "relax", "calm down",
    "you can", "you will", "just ", "remember to", "take a deep",
    "mindful", "wellness", "journey", "embrace", "let go",
)

SLOW_PUNCT = (",", ";", ":")


def _words(text):
    return [w.strip(".,;:!?").lower() for w in text.split()]


def score(text):
    """Heuristic quality score for one assembled candidate."""
    n = len(text)
    if n < 1 or n > MAX_CHARS:
        return -10000
    s = 0.0
    # Length: full marks only inside the 238-266 target band (85-95% of max),
    # steep fall-off outside it, so the winner always lands in the band.
    if TARGET_LOW <= n <= TARGET_HIGH:
        s += 40.0
    elif n > TARGET_HIGH:
        s += 40.0 - (n - TARGET_HIGH) * 1.5
    elif n >= 200:
        s += 40.0 - (TARGET_LOW - n) * 1.5
    else:
        s += max(0.0, n * 0.15)
    low = text.lower()
    for bad in BANNED:
        if bad in low:
            s -= 60.0
    # Slow pacing: commas and semicolons stretch the reading out.
    s += min(12.0, sum(text.count(p) for p in SLOW_PUNCT) * 2.0)
    # Concrete sensory words anchor the scene.
    words = _words(text)
    seen = set()
    for w in words:
        if w in CONFIG["sensory_words"] and w not in seen:
            s += 3.0
            seen.add(w)
    for w in words:
        if w in CONFIG["slow_words"]:
            s += 1.5
    # Variety: repeated content words are flab.
    if len(words) != len(set(words)):
        s -= 4.0 * (len(words) - len(set(words)))
    # Three sentences, each carrying its own weight.
    sentences = [p for p in text.split(". ") if p.strip()]
    if len(sentences) == 3:
        s += 8.0
    # A closing that lands on a concrete image, not an abstraction.
    tail = text.rsplit(".", 1)[0].lower()
    if any(w in tail for w in ("lamp", "light", "rain", "room", "clock", "door", "kettle")):
        s += 6.0
    # Prefer no word longer than 12 letters: plain words, none that could be cut.
    if max((len(w) for w in words), default=0) <= 12:
        s += 4.0
    return s


def build_best():
    """Try every opening x middle x closing combination; keep the best."""
    best_text = None
    best_score = None
    for opening in OPENINGS:
        for middle in MIDDLES:
            for closing in CLOSINGS:
                text = " ".join((opening, middle, closing))
                if len(text) > MAX_CHARS:
                    continue
                sc = score(text)
                if best_score is None or sc > best_score or (
                    sc == best_score and text < best_text
                ):
                    best_text, best_score = text, sc
    return best_text, best_score


FALLBACK = (
    "Late rain on the tin roof, slow as a held breath. "
    "Someone sets the kettle down without hurrying, and the steam rises "
    "in one unbroken thread. Nothing here needs fixing tonight."
)


def get_safe_fallback_text():
    """A short, valid text, used only if the generator ever fails."""
    return FALLBACK[:MAX_CHARS]


def main():
    try:
        text, _score = build_best()
        if not text or not text.strip():
            raise ValueError("no candidate")
    except Exception:
        text = get_safe_fallback_text()
    # Absolute character lock: never exceed the limit, whatever the scorer did.
    text = text[:MAX_CHARS]
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "entry.txt")
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


if __name__ == "__main__":
    main()
