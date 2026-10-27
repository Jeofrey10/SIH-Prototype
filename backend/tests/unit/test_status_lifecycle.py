"""Unit tests for complaint status lifecycle transitions."""
from __future__ import annotations

import pytest

from app.services.complaints import VALID_STATUS_TRANSITIONS


def test_valid_transitions_exist():
    """Verify all valid transitions from Section 11."""
    assert "UNDER_REVIEW" in VALID_STATUS_TRANSITIONS["REGISTERED"]
    assert "ACTION_INITIATED" in VALID_STATUS_TRANSITIONS["UNDER_REVIEW"]
    assert "PENDING_INFORMATION" in VALID_STATUS_TRANSITIONS["UNDER_REVIEW"]
    assert "RESOLVED" in VALID_STATUS_TRANSITIONS["UNDER_REVIEW"]

    assert "UNDER_REVIEW" in VALID_STATUS_TRANSITIONS["ACTION_INITIATED"]
    assert "PENDING_INFORMATION" in VALID_STATUS_TRANSITIONS["ACTION_INITIATED"]
    assert "RESOLVED" in VALID_STATUS_TRANSITIONS["ACTION_INITIATED"]

    assert "UNDER_REVIEW" in VALID_STATUS_TRANSITIONS["PENDING_INFORMATION"]
    assert "ACTION_INITIATED" in VALID_STATUS_TRANSITIONS["PENDING_INFORMATION"]

    assert "CLOSED" in VALID_STATUS_TRANSITIONS["RESOLVED"]
    assert "REOPENED" in VALID_STATUS_TRANSITIONS["RESOLVED"]

    assert "REOPENED" in VALID_STATUS_TRANSITIONS["CLOSED"]

    assert "UNDER_REVIEW" in VALID_STATUS_TRANSITIONS["REOPENED"]
    assert "ACTION_INITIATED" in VALID_STATUS_TRANSITIONS["REOPENED"]
    assert "PENDING_INFORMATION" in VALID_STATUS_TRANSITIONS["REOPENED"]
    assert "RESOLVED" in VALID_STATUS_TRANSITIONS["REOPENED"]


def test_invalid_transitions_rejected():
    """Verify mandatory invalid transition examples from Section 11."""
    # 1. REGISTERED -> RESOLVED
    assert "RESOLVED" not in VALID_STATUS_TRANSITIONS.get("REGISTERED", set())

    # 2. REGISTERED -> CLOSED
    assert "CLOSED" not in VALID_STATUS_TRANSITIONS.get("REGISTERED", set())

    # 3. UNDER_REVIEW -> CLOSED
    assert "CLOSED" not in VALID_STATUS_TRANSITIONS.get("UNDER_REVIEW", set())

    # 4. CLOSED -> RESOLVED
    assert "RESOLVED" not in VALID_STATUS_TRANSITIONS.get("CLOSED", set())

    # 5. PENDING_INFORMATION -> RESOLVED
    assert "RESOLVED" not in VALID_STATUS_TRANSITIONS.get("PENDING_INFORMATION", set())

    # 6. Same status transitions
    for status, allowed in VALID_STATUS_TRANSITIONS.items():
        assert status not in allowed, f"Self-transition for {status} must be invalid"
