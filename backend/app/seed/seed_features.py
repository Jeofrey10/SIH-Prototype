"""Seed demo scenarios for the 5 new features: Handover, Waiting-On, Limbo, Threads, Explainer."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from app.db.session import SessionLocal
from app.models import (
    Bureau, CaseAssignment, Complaint, ComplaintNote,
    ComplaintRelation, Handover, IssueThread, StatusHistory,
    User, WaitingOnEntry
)


def seed_new_features():
    db = SessionLocal()
    now = datetime.now(timezone.utc)

    supervisor = db.query(User).filter(User.role == "SUPERVISOR").first()
    rb_official = db.query(User).filter(User.role == "RB_OFFICIAL").first()
    pgrc_official = db.query(User).filter(User.role == "PGRC_OFFICIAL").first()

    rb_bureau = db.query(Bureau).filter(Bureau.code == "RB").first()
    pgrc_bureau = db.query(Bureau).filter(Bureau.code == "PGRC").first()

    if not supervisor or not rb_bureau or not pgrc_bureau:
        print("Missing required users or bureaus for seeding features.")
        db.close()
        return

    print("Seeding Feature 1: Handover Contracts...")
    # Find 2 open complaints for in-transit handover
    open_complaints = (
        db.query(Complaint)
        .filter(Complaint.status.in_(("UNDER_REVIEW", "ACTION_INITIATED")))
        .limit(10)
        .all()
    )

    if len(open_complaints) >= 3:
        c_transit = open_complaints[0]
        # Clean previous handovers if any
        db.query(Handover).filter(Handover.complaint_id == c_transit.id).delete()
        h1 = Handover(
            complaint_id=c_transit.id,
            from_bureau_id=rb_bureau.id,
            to_bureau_id=pgrc_bureau.id,
            target_owner_id=pgrc_official.id if pgrc_official else None,
            initiated_by=supervisor.id,
            initiated_at=now - timedelta(days=2, hours=4),
            status="PENDING",
            context_summary="Transferring case following inter-bureau coordination meeting. Institution failed to provide tuition refund compliance logs across multiple notices. Requires immediate Grievance Redressal committee hearing.",
            key_findings="1. Complainant submitted fee receipts of Rs 1,12,000.\n2. College accounts section refused written acknowledgment.\n3. Institutional response overdue by 21 days.",
        )
        c_transit.handover_status = "IN_TRANSIT"
        c_transit.primary_bureau_id = rb_bureau.id
        db.add(h1)

        c_past = open_complaints[1]
        db.query(Handover).filter(Handover.complaint_id == c_past.id).delete()
        h2 = Handover(
            complaint_id=c_past.id,
            from_bureau_id=pgrc_bureau.id,
            to_bureau_id=rb_bureau.id,
            target_owner_id=rb_official.id if rb_official else None,
            initiated_by=supervisor.id,
            initiated_at=now - timedelta(days=10),
            responded_by=rb_official.id if rb_official else None,
            responded_at=now - timedelta(days=9),
            status="ACCEPTED",
            context_summary="Initial verification complete; transferred to Regional Bureau for on-site infrastructure inspection and laboratory equipment audit.",
            key_findings="Affidavit confirmed deficit in computer lab terminals.",
        )
        db.add(h2)

    print("Seeding Feature 2: Waiting-On Ledger...")
    # Add active waiting-on entries
    if len(open_complaints) >= 5:
        # Case 1: Waiting on institution with chaser
        c_wait1 = open_complaints[1]
        db.query(WaitingOnEntry).filter(WaitingOnEntry.complaint_id == c_wait1.id).delete()
        w1 = WaitingOnEntry(
            complaint_id=c_wait1.id,
            waiting_on_type="INSTITUTION_REPLY",
            waiting_on_party=c_wait1.institution.name if c_wait1.institution else "Engineering College",
            since=now - timedelta(days=16),
            chaser_user_id=rb_official.id if rb_official else None,
            is_resolved=False,
            notes="Issued 2nd reminder notice via registered portal post. Awaiting Registrar's counter-affidavit.",
            created_by=supervisor.id,
            created_at=now - timedelta(days=16),
        )
        db.add(w1)

        # Case 2: Waiting on Bureau Opinion
        c_wait2 = open_complaints[2]
        db.query(WaitingOnEntry).filter(WaitingOnEntry.complaint_id == c_wait2.id).delete()
        w2 = WaitingOnEntry(
            complaint_id=c_wait2.id,
            waiting_on_type="BUREAU_OPINION",
            waiting_on_party="AICTE Legal Cell",
            since=now - timedelta(days=5),
            chaser_user_id=pgrc_official.id if pgrc_official else None,
            is_resolved=False,
            notes="Referred for legal advisory on jurisdictional standing regarding state quota refund regulations.",
            created_by=pgrc_official.id if pgrc_official else supervisor.id,
            created_at=now - timedelta(days=5),
        )
        db.add(w2)

        # Case 3: Waiting with NO chaser assigned (triggers UNASSIGNED_CHASER limbo flag)
        c_wait3 = open_complaints[3]
        db.query(WaitingOnEntry).filter(WaitingOnEntry.complaint_id == c_wait3.id).delete()
        w3 = WaitingOnEntry(
            complaint_id=c_wait3.id,
            waiting_on_type="DOCUMENT_SUBMISSION",
            waiting_on_party="Complainant Guardian",
            since=now - timedelta(days=8),
            chaser_user_id=None,
            is_resolved=False,
            notes="Requested bank account statement showing debit deduction.",
            created_by=supervisor.id,
            created_at=now - timedelta(days=8),
        )
        db.add(w3)

    print("Seeding Feature 3: Limbo and Ping-Pong cases...")
    # Case with ping pong: simulate 3 bureau assignments
    if len(open_complaints) >= 6:
        c_ping = open_complaints[4]
        # Add past assignments
        db.add(CaseAssignment(
            complaint_id=c_ping.id,
            bureau_id=rb_bureau.id,
            role_in_case="PRIMARY",
            assigned_by=supervisor.id,
            assigned_at=now - timedelta(days=25),
            ended_at=now - timedelta(days=15),
            ended_by=supervisor.id,
            reason="Initial assignment",
            is_active=False,
        ))
        db.add(CaseAssignment(
            complaint_id=c_ping.id,
            bureau_id=pgrc_bureau.id,
            role_in_case="PRIMARY",
            assigned_by=supervisor.id,
            assigned_at=now - timedelta(days=15),
            ended_at=now - timedelta(days=5),
            ended_by=supervisor.id,
            reason="Transferred to grievance cell",
            is_active=False,
        ))

    print("Seeding Feature 4: Issue Threads...")
    # Find confirmed relations and create a consolidated thread
    confirmed_rels = (
        db.query(ComplaintRelation)
        .filter(ComplaintRelation.status == "CONFIRMED")
        .limit(3)
        .all()
    )

    if confirmed_rels:
        thread = IssueThread(
            title="Thread: Laboratory Fee Retainment & Denial of Refund",
            brief=(
                "Consolidated issue cluster covering 3 inter-related complaints against systematic fee retainment.\n"
                "Key findings: The institute withheld student laboratory caution deposits beyond the mandated 15-day refund window.\n"
                "Multiple batches impacted. Recommended joint show-cause notice from RB and PGRC."
            ),
            status="ACTIVE",
            created_at=now - timedelta(days=5),
            updated_at=now - timedelta(hours=3),
        )
        db.add(thread)
        db.flush()

        for r in confirmed_rels:
            r.thread_id = thread.id

    db.commit()
    print("Feature demo seed data committed successfully!")
    db.close()


if __name__ == "__main__":
    seed_new_features()
