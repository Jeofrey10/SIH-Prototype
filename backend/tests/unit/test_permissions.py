"""Unit tests for role-based access control and complaint authorization."""
from __future__ import annotations

import pytest

from app.core import permissions
from app.core.permissions import AccessContext, ComplaintContext


def test_rbac_access_level():
    """Supervisor and Admin always have FULL access; Officials have FULL only when participating."""
    complaint = ComplaintContext(
        complaint_id="c1",
        status="UNDER_REVIEW",
        primary_bureau_id="bureau-rb",
        owner_user_id="user-rb-1",
        participating_bureau_ids=[],
    )

    admin_access = AccessContext(user_id="u-admin", user_role="SYSTEM_ADMIN", user_bureau_id=None)
    supervisor_access = AccessContext(user_id="u-sup", user_role="SUPERVISOR", user_bureau_id=None)
    rb_official_access = AccessContext(user_id="u-rb", user_role="RB_OFFICIAL", user_bureau_id="bureau-rb")
    pgrc_official_access = AccessContext(user_id="u-pgrc", user_role="PGRC_OFFICIAL", user_bureau_id="bureau-pgrc")

    # Supervisor and Admin get FULL access
    assert permissions.get_access_level(admin_access, complaint) == "FULL"
    assert permissions.get_access_level(supervisor_access, complaint) == "FULL"

    # RB Official participates as primary -> FULL
    assert permissions.get_access_level(rb_official_access, complaint) == "FULL"

    # PGRC Official does NOT participate -> SUMMARY
    assert permissions.get_access_level(pgrc_official_access, complaint) == "SUMMARY"

    # When PGRC is added to participating bureaus -> PGRC Official gets FULL
    complaint.participating_bureau_ids = ["bureau-pgrc"]
    assert permissions.get_access_level(pgrc_official_access, complaint) == "FULL"


def test_official_cannot_change_status_without_participation():
    """Officials cannot change status of cases where their bureau does not participate."""
    complaint = ComplaintContext(
        complaint_id="c1",
        status="UNDER_REVIEW",
        primary_bureau_id="bureau-rb",
        owner_user_id="user-rb-1",
        participating_bureau_ids=[],
    )
    pgrc_official = AccessContext(user_id="u-pgrc", user_role="PGRC_OFFICIAL", user_bureau_id="bureau-pgrc")
    assert not permissions.user_participates(pgrc_official, complaint)


def test_supervisor_exclusive_actions():
    """Primary transfer, closing resolved cases, and reopening closed cases are restricted."""
    complaint_open = ComplaintContext(
        complaint_id="c1",
        status="UNDER_REVIEW",
        primary_bureau_id="bureau-rb",
        owner_user_id="user-rb-1",
    )
    rb_official = AccessContext(user_id="u-rb", user_role="RB_OFFICIAL", user_bureau_id="bureau-rb")
    supervisor = AccessContext(user_id="u-sup", user_role="SUPERVISOR", user_bureau_id=None)

    actions_official = permissions.compute_allowed_actions(rb_official, complaint_open)
    actions_sup = permissions.compute_allowed_actions(supervisor, complaint_open)

    assert actions_sup["can_transfer_primary"] is True
    assert actions_official["can_transfer_primary"] is False


def test_resolved_to_closed_supervisor_only():
    """Only supervisor can close a resolved case."""
    complaint_resolved = ComplaintContext(
        complaint_id="c1",
        status="RESOLVED",
        primary_bureau_id="bureau-rb",
        owner_user_id="user-rb-1",
    )
    rb_official = AccessContext(user_id="u-rb", user_role="RB_OFFICIAL", user_bureau_id="bureau-rb")
    supervisor = AccessContext(user_id="u-sup", user_role="SUPERVISOR", user_bureau_id=None)

    actions_official = permissions.compute_allowed_actions(rb_official, complaint_resolved)
    actions_sup = permissions.compute_allowed_actions(supervisor, complaint_resolved)

    assert "CLOSED" in actions_sup["allowed_status_transitions"]
    assert "CLOSED" not in actions_official["allowed_status_transitions"]
