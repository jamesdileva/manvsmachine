"""Executable acceptance criteria for the challenge library data files (Sprint 5).

Validates every challenge definition against the §10.1 schema, the stub-entry
pools, and the v1.0 prompt template — the checks the sprint's manual testing
section calls for, run automatically.
"""

import json
import re
from pathlib import Path
from typing import Any

import pytest

DATA_DIR = Path(__file__).resolve().parents[1] / "app" / "data"
LIBRARY_DIR = DATA_DIR / "challenge_library"
STUB_DIR = DATA_DIR / "stub_entries"
PROMPTS_DIR = DATA_DIR / "ai_prompts"

ID_PATTERN = re.compile(r"^challenge_[a-z0-9]+_[0-9]+$")
VALID_CONSTRAINT_TYPES = {
    "max_words",
    "max_characters",
    "must_rhyme",
    "no_adjectives",
    "must_include_theme",
    "exactly_n_emojis",
    "no_letter_e",
    "one_sentence_only",
}
VALID_INPUT_TYPES = {"text_single_line", "text_multi_line"}

# The 25 challenge IDs, per docs/05_Micro_Challenge_Library.md (order = doc order).
EXPECTED_IDS = {
    "challenge_slogan_01",
    "challenge_impossible_02",
    "challenge_emoji_03",
    "challenge_worstidea_04",
    "challenge_blank_05",
    "challenge_comeback_06",
    "challenge_review_07",
    "challenge_headline_08",
    "challenge_tweet_09",
    "challenge_movie_10",
    "challenge_caption_11",
    "challenge_product_12",
    "challenge_oneliner_13",
    "challenge_marketing_14",
    "challenge_analogy_15",
    "challenge_bestmove_16",
    "challenge_popularity_17",
    "challenge_twotruths_18",
    "challenge_confession_19",
    "challenge_yelp_20",
    "challenge_dm_21",
    "challenge_reddit_22",
    "challenge_interview_23",
    "challenge_rank_24",
    "challenge_logo_25",
}

REQUIRED_KEYS = {
    "id",
    "name",
    "interactionType",
    "prompt",
    "constraints",
    "timeLimitSeconds",
    "inputType",
    "votingCriteria",
    "difficulty",
    "scoringRules",
    "aiPromptTemplateId",
    "replayability",
    "aiPromptGuidance",
}


def _load_all(directory: Path) -> dict[str, dict[str, Any]]:
    return {
        path.stem: json.loads(path.read_text(encoding="utf-8"))
        for path in sorted(directory.glob("*.json"))
    }


def test_library_contains_exactly_the_doc_05_catalog() -> None:
    challenges = _load_all(LIBRARY_DIR)
    assert set(challenges) == EXPECTED_IDS


@pytest.mark.parametrize("challenge_id", sorted(EXPECTED_IDS))
def test_challenge_matches_schema(challenge_id: str) -> None:
    data = json.loads((LIBRARY_DIR / f"{challenge_id}.json").read_text(encoding="utf-8"))

    assert set(REQUIRED_KEYS) <= set(data)
    assert data["id"] == challenge_id
    assert data["interactionType"] == "Quick Text"
    assert data["inputType"] in VALID_INPUT_TYPES
    assert data["votingCriteria"] == "most_believable"
    assert isinstance(data["difficulty"], int) and 1 <= data["difficulty"] <= 5
    assert isinstance(data["timeLimitSeconds"], int) and 10 <= data["timeLimitSeconds"] <= 120
    assert isinstance(data["prompt"], str) and data["prompt"].strip()
    assert isinstance(data["aiPromptGuidance"], str) and data["aiPromptGuidance"].strip()
    assert data["aiPromptTemplateId"] == "v1.0"

    scoring = data["scoringRules"]
    assert {"baseScore", "timeBonusMultiplier", "streakMultiplier"} <= set(scoring)
    assert scoring["baseScore"] > 0

    for constraint in data["constraints"]:
        assert constraint["type"] in VALID_CONSTRAINT_TYPES
        assert isinstance(constraint["isHard"], bool)
        if constraint["type"] in {"max_words", "max_characters", "exactly_n_emojis"}:
            assert isinstance(constraint.get("value"), int) and constraint["value"] > 0
        if constraint["type"] == "must_include_theme":
            assert isinstance(constraint.get("value"), str) and constraint["value"]

    replayability = data["replayability"]
    assert replayability["dailyVariants"] >= 1
    assert set(replayability["constraintPool"]) <= VALID_CONSTRAINT_TYPES


def test_stub_pools_cover_every_challenge_with_entries() -> None:
    pools = _load_all(STUB_DIR)
    assert set(pools) == EXPECTED_IDS  # one pool per challenge, none extra

    for pool_id, entries in pools.items():
        assert isinstance(entries, list) and len(entries) >= 5, pool_id
        assert all(isinstance(e, str) and e.strip() for e in entries), pool_id
        assert len(entries) == len(set(entries)), f"duplicate entries in {pool_id}"

    ten_plus = [pool_id for pool_id, entries in pools.items() if len(entries) >= 10]
    assert len(ten_plus) >= 5  # explicit acceptance criterion


def test_every_stub_pool_has_ten_entries() -> None:
    """Content spec: 10 entries per challenge, giving the StubProvider variety."""
    pools = _load_all(STUB_DIR)
    short = {pool_id: len(entries) for pool_id, entries in pools.items() if len(entries) != 10}
    assert not short, f"pools without exactly 10 entries: {short}"


def test_prompt_template_v1_is_well_formed() -> None:
    template = json.loads((PROMPTS_DIR / "v1.0.json").read_text(encoding="utf-8"))
    assert template["version"] == "v1.0"
    assert "{time_limit}" in template["system_prompt"]
    assert "{prompt}" in template["user_template"]
    assert "{constraints_formatted}" in template["user_template"]
    assert isinstance(template["instructions"], list) and template["instructions"]
    assert isinstance(template["humanity_guidance"], list) and template["humanity_guidance"]
