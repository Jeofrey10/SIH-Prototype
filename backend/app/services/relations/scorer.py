"""Scoring and candidate matching for related complaint detection."""
from __future__ import annotations

import math
from datetime import date
from typing import Any

from app.services.relations.normalizer import (
    DOMAIN_TERMS,
    cosine_similarity_sublinear_tf,
    get_keywords,
    jaccard_similarity,
    normalize_text,
    stem_word,
)

ALGORITHM_VERSION = "1.0"

# Stemmed domain terms for exact matching
STEMMED_DOMAIN_TERMS = frozenset(stem_word(t) for t in DOMAIN_TERMS)


def calculate_relation_score(
    complaint_a: dict[str, Any],
    complaint_b: dict[str, Any],
) -> dict[str, Any]:
    """
    Score relationship between two complaints.
    Returns:
    {
        "algorithm_version": "1.0",
        "score": int (0-100),
        "confidence": "HIGH" | "MEDIUM",
        "is_suggested": bool,
        "components": [
            {"name": str, "points": int, "max_points": int, "detail": str}
        ],
        "shared_keywords": list[str],
        "shared_domain_terms": list[str],
        "category_match": bool,
        "incident_reference_match": bool,
        "date_gap_days": int | None,
        "candidate_status": str,
        "candidate_primary_bureau": str | None,
    }
    """
    # 1. Category match: 25 if categories equal, else 0
    cat_a = (complaint_a.get("category") or "").strip().upper()
    cat_b = (complaint_b.get("category") or "").strip().upper()
    cat_match = bool(cat_a and cat_b and cat_a == cat_b)
    cat_points = 25 if cat_match else 0
    cat_detail = f"Categories match ({cat_a})" if cat_match else f"Different categories ({cat_a} vs {cat_b})"

    # 2. Text similarity
    text_a = f"{complaint_a.get('title', '')} {complaint_a.get('description', '')}"
    text_b = f"{complaint_b.get('title', '')} {complaint_b.get('description', '')}"

    tokens_a, set_a, counter_a = normalize_text(text_a)
    tokens_b, set_b, counter_b = normalize_text(text_b)

    jaccard = jaccard_similarity(set_a, set_b)
    cosine = cosine_similarity_sublinear_tf(counter_a, counter_b)
    text_sim_val = 0.5 * jaccard + 0.5 * cosine
    text_points = round(40 * text_sim_val)
    text_detail = (
        f"Jaccard={jaccard:.2f}, Cosine={cosine:.2f}, Composite={text_sim_val:.2f} -> {text_points}/40 pts"
    )

    # 3. Domain terms: 15 * min(1, shared_domain_terms / 3)
    shared_domain = sorted(list((set_a & set_b) & STEMMED_DOMAIN_TERMS))
    shared_domain_count = len(shared_domain)
    domain_points = round(15 * min(1.0, shared_domain_count / 3.0))
    domain_detail = (
        f"{shared_domain_count} shared domain terms: {', '.join(shared_domain[:5])}"
        if shared_domain else "No shared domain terms"
    )

    # 4. Incident reference: 10 if both non-empty and equal after trim+lowercase
    ref_a = (complaint_a.get("incident_reference") or "").strip().lower()
    ref_b = (complaint_b.get("incident_reference") or "").strip().lower()
    ref_match = bool(ref_a and ref_b and ref_a == ref_b)
    ref_points = 10 if ref_match else 0
    ref_detail = f"Matching incident reference: '{ref_a}'" if ref_match else "No matching incident reference"

    # 5. Date proximity: incident_date if both present, else received_date
    date_a = complaint_a.get("incident_date")
    date_b = complaint_b.get("incident_date")
    used_incident_date = True
    if not (date_a and date_b):
        date_a = complaint_a.get("received_date")
        date_b = complaint_b.get("received_date")
        used_incident_date = False

    date_gap_days: int | None = None
    date_points = 0
    date_detail = "Date unavailable"

    if date_a and date_b:
        if isinstance(date_a, str):
            date_a = date.fromisoformat(date_a)
        if isinstance(date_b, str):
            date_b = date.fromisoformat(date_b)
        date_gap_days = abs((date_a - date_b).days)
        if date_gap_days <= 7:
            date_points = 10
        elif date_gap_days <= 30:
            date_points = 6
        elif date_gap_days <= 90:
            date_points = 3
        else:
            date_points = 0
        date_source_str = "incident_date" if used_incident_date else "received_date"
        date_detail = f"Gap of {date_gap_days} days using {date_source_str} ({date_points}/10 pts)"

    # Total score calculation
    raw_score = cat_points + text_points + domain_points + ref_points + date_points

    # Floor at 40 if incident_reference match
    final_score = raw_score
    if ref_match and final_score < 40:
        final_score = 40

    final_score = max(0, min(100, final_score))

    # Shared keywords (top 10 shared tokens, sorted by combined frequency)
    shared_tokens = set_a & set_b
    shared_keywords = sorted(
        list(shared_tokens),
        key=lambda t: (-(counter_a.get(t, 0) + counter_b.get(t, 0)), t),
    )[:10]

    # Suggestion rules:
    # suggest when score >= 40 AND (category_match OR text_similarity points >= 12 OR incident_reference match).
    # An incident_reference match always yields a suggestion with score floored to 40.
    is_suggested = (final_score >= 40) and (cat_match or text_points >= 12 or ref_match)
    if ref_match:
        is_suggested = True

    confidence = "HIGH" if final_score >= 60 else "MEDIUM"

    candidate_status = complaint_b.get("status", "UNKNOWN")
    candidate_primary_bureau = complaint_b.get("primary_bureau_code") or complaint_b.get("primary_bureau")

    return {
        "algorithm_version": ALGORITHM_VERSION,
        "score": int(final_score),
        "confidence": confidence,
        "is_suggested": is_suggested,
        "components": [
            {"name": "category_match", "points": cat_points, "max_points": 25, "detail": cat_detail},
            {"name": "text_similarity", "points": text_points, "max_points": 40, "detail": text_detail},
            {"name": "domain_terms", "points": domain_points, "max_points": 15, "detail": domain_detail},
            {"name": "incident_reference", "points": ref_points, "max_points": 10, "detail": ref_detail},
            {"name": "date_proximity", "points": date_points, "max_points": 10, "detail": date_detail},
        ],
        "shared_keywords": shared_keywords,
        "shared_domain_terms": shared_domain,
        "category_match": cat_match,
        "incident_reference_match": ref_match,
        "date_gap_days": date_gap_days,
        "candidate_status": candidate_status,
        "candidate_primary_bureau": candidate_primary_bureau,
    }
