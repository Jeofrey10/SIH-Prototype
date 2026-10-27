"""Unit tests for duplicate and related complaint detection."""
from __future__ import annotations

from datetime import date
import pytest

from app.services.relations.normalizer import (
    DOMAIN_TERMS,
    STOPWORDS,
    cosine_similarity_sublinear_tf,
    get_keywords,
    jaccard_similarity,
    normalize_text,
    stem_word,
)
from app.services.relations.scorer import (
    ALGORITHM_VERSION,
    calculate_relation_score,
)


def test_stemmer_rules():
    """Test deterministic suffix stemmer."""
    # ies -> y
    assert stem_word("categories") == "category"
    assert stem_word("faculties") == "faculty"

    # sses -> ss
    assert stem_word("processes") == "process"

    # ing, ed, ment, ly, es, s with stem >= 4 chars
    assert stem_word("complaining") == "complain"
    assert stem_word("delayed") == "delay"
    assert stem_word("allotment") == "allot"
    assert stem_word("frequently") == "frequent"
    assert stem_word("colleges") == "colleg"
    assert stem_word("refunds") == "refund"

    # Too short stems (< 4 chars remaining) should NOT be stemmed
    assert stem_word("ring") == "ring"
    assert stem_word("beds") == "beds"
    assert stem_word("red") == "red"


def test_text_normalization():
    """Test text normalization and token extraction."""
    text = "The Institute of Engineering failed to refund the students' hostel fee 12345 in 2026!"
    tokens, token_set, counter = normalize_text(text)

    # Stopwords and domain stopwords should be removed: 'the', 'institute', 'of', 'to', 'students', 'in'
    assert "institute" not in token_set
    assert "students" not in token_set
    assert "the" not in token_set

    # Pure numbers dropped
    assert "12345" not in token_set
    assert "2026" not in token_set

    # Domain terms retained
    assert "refund" in token_set or "hostel" in token_set or "fee" in token_set


def test_jaccard_and_cosine_metrics():
    """Test similarity metrics with known vectors."""
    set1 = {"fee", "refund", "hostel"}
    set2 = {"fee", "refund", "tuition"}
    jaccard = jaccard_similarity(set1, set2)
    # intersection: 2 ('fee', 'refund'), union: 4 ('fee', 'refund', 'hostel', 'tuition') -> 2/4 = 0.5
    assert jaccard == 0.5

    # Empty sets
    assert jaccard_similarity(set(), set()) == 0.0

    _, _, c1 = normalize_text("fee refund tuition fee")
    _, _, c2 = normalize_text("fee refund hostel fee")
    cosine = cosine_similarity_sublinear_tf(c1, c2)
    assert 0.0 < cosine <= 1.0


def test_scorer_component_breakdown():
    """Test that relation scorer calculates exact component weights."""
    comp1 = {
        "category": "FEES_REFUND",
        "title": "Tuition fee refund not processed",
        "description": "Student withdrew admission within deadline but refund for tuition and hostel fees is not released.",
        "incident_reference": "REF-2026-001",
        "received_date": date(2026, 1, 10),
        "status": "UNDER_REVIEW",
        "primary_bureau_code": "RB",
    }
    comp2 = {
        "category": "FEES_REFUND",
        "title": "Hostel and tuition fee refund withheld",
        "description": "College accounts section refuses to refund fees after admission was cancelled.",
        "incident_reference": "REF-2026-001",
        "received_date": date(2026, 1, 12),
        "status": "REGISTERED",
        "primary_bureau_code": "PGRC",
    }

    res = calculate_relation_score(comp1, comp2)
    assert res["algorithm_version"] == ALGORITHM_VERSION
    assert res["category_match"] is True
    assert res["incident_reference_match"] is True
    assert res["date_gap_days"] == 2
    assert res["score"] >= 60
    assert res["confidence"] == "HIGH"
    assert res["is_suggested"] is True


def test_scorer_incident_reference_floor():
    """Incident reference match should floor score to at least 40 and yield suggestion."""
    comp1 = {
        "category": "INFRASTRUCTURE",
        "title": "Classroom projector broken",
        "description": "Projector in room 101 does not work.",
        "incident_reference": "INC-SHARED-999",
        "received_date": date(2026, 1, 1),
    }
    comp2 = {
        "category": "HARASSMENT",
        "title": "Verbal altercation in cafeteria",
        "description": "Staff was rude to student in dining hall.",
        "incident_reference": "inc-shared-999 ",  # case and whitespace test
        "received_date": date(2026, 6, 1),        # far away in time
    }

    res = calculate_relation_score(comp1, comp2)
    assert res["incident_reference_match"] is True
    assert res["score"] >= 40
    assert res["is_suggested"] is True


def test_scorer_negative_control():
    """Completely unrelated complaints should not be suggested."""
    comp1 = {
        "category": "INFRASTRUCTURE",
        "title": "Broken desks in room 302",
        "description": "Desks are damaged and need carpenter repair.",
        "received_date": date(2026, 1, 1),
    }
    comp2 = {
        "category": "ACADEMIC_INTEGRITY",
        "title": "Plagiarism in final year semester project submission",
        "description": "Submitted paper copy was downloaded directly from online repository.",
        "received_date": date(2026, 8, 1),
    }

    res = calculate_relation_score(comp1, comp2)
    assert res["category_match"] is False
    assert res["score"] < 40
    assert res["is_suggested"] is False
