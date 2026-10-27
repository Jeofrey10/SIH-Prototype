"""Deterministic synthetic seed data generator."""
from __future__ import annotations

import logging
import random
from datetime import date, datetime, timedelta, timezone
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core import security
from app.core.config import get_settings
from app.models import (
    AuditLog, Bureau, CaseAssignment, Complaint, ComplaintNote,
    ComplaintRelation, Institution, Notification, StatusHistory, User
)
from app.services.audit import write_audit
from app.services.complaints import PRIORITY_DAYS
from app.services.notifications import notify_users
from app.services.relations.normalizer import get_keywords
from app.services.relations.scorer import ALGORITHM_VERSION, calculate_relation_score

logger = logging.getLogger(__name__)

SEED_RANDOM = 20260101

STATES = ["Tamil Nadu", "Maharashtra", "Karnataka", "Delhi", "Uttar Pradesh", "Gujarat", "Kerala", "Telangana"]
INSTITUTION_TYPES = ["ENGINEERING", "MANAGEMENT", "PHARMACY", "ARCHITECTURE", "POLYTECHNIC"]
CATEGORIES = [
    "FEES_REFUND",
    "INFRASTRUCTURE",
    "FACULTY_ISSUES",
    "STUDENT_WELFARE",
    "ADMISSION_IRREGULARITY",
    "ACADEMIC_MISCONDUCT",
]
PRIORITIES = ["CRITICAL", "HIGH", "MEDIUM", "LOW"]
SOURCE_CHANNELS = ["PORTAL", "EMAIL", "LETTER", "PHONE", "OTHER"]
COMPLAINANT_TYPES = ["STUDENT", "FACULTY", "PARENT", "STAKEHOLDER", "OTHER"]


def run_seed(db: Session, reset: bool = False) -> dict[str, int]:
    """Populate database with deterministic synthetic data."""
    settings = get_settings()

    if reset:
        if settings.app_env.lower() == "production":
            raise RuntimeError("Reset is prohibited in production environment")
        logger.info("Resetting existing database data...")
        # Clear existing rows in dependency order
        db.execute(text("DELETE FROM complaint_relations"))
        db.execute(text("DELETE FROM complaint_notes"))
        db.execute(text("DELETE FROM status_history"))
        db.execute(text("DELETE FROM case_assignments"))
        db.execute(text("DELETE FROM notifications"))
        db.execute(text("DELETE FROM complaints"))
        db.execute(text("DELETE FROM audit_logs"))
        db.execute(text("DELETE FROM users"))
        db.execute(text("DELETE FROM institutions"))
        db.execute(text("DELETE FROM bureaus"))
        db.commit()
    else:
        # Check if already seeded
        existing_inst = db.query(Institution).first()
        if existing_inst:
            logger.info("Database is already seeded. Use --reset to re-seed.")
            return {"status": "already_seeded"}

    random.seed(SEED_RANDOM)
    now = datetime.now(timezone.utc)
    today = now.date()

    demo_pw = settings.demo_password or "Demo@12345"
    pw_hash = security.hash_password(demo_pw)

    # 1. Bureaus
    b_rb = db.query(Bureau).filter_by(code="RB").first()
    if not b_rb:
        b_rb = Bureau(code="RB", name="Regulation Bureau", description="Regulatory compliance and standards", is_active=True)
        db.add(b_rb)
    b_pgrc = db.query(Bureau).filter_by(code="PGRC").first()
    if not b_pgrc:
        b_pgrc = Bureau(code="PGRC", name="Public Grievance Redressal Cell", description="Student and faculty grievance redressal", is_active=True)
        db.add(b_pgrc)
    db.flush()

    # 2. Demo Users & Official Quick-Fill Accounts
    users_data = [
        ("admin@aicte-demo.example", "System Administrator", "SYSTEM_ADMIN", None, "Administrator", pw_hash),
        ("supervisor@aicte-demo.example", "Senior Grievance Supervisor", "SUPERVISOR", None, "Director (Monitoring)", pw_hash),
        ("rb.official1@aicte-demo.example", "Ramesh Babu (RB)", "RB_OFFICIAL", b_rb.id, "Assistant Director", pw_hash),
        ("rb.official2@aicte-demo.example", "Priya Sharma (RB)", "RB_OFFICIAL", b_rb.id, "Section Officer", pw_hash),
        ("pgrc.official1@aicte-demo.example", "Anil Kumar (PGRC)", "PGRC_OFFICIAL", b_pgrc.id, "Assistant Director", pw_hash),
        ("pgrc.official2@aicte-demo.example", "Sunita Verma (PGRC)", "PGRC_OFFICIAL", b_pgrc.id, "Grievance Officer", pw_hash),
        # Frontend Quick-Fill and E2E Acceptance accounts:
        ("admin@aicte.gov.in", "System Administrator", "SYSTEM_ADMIN", None, "Administrator", security.hash_password("Admin@123")),
        ("supervisor@aicte.gov.in", "Senior Grievance Supervisor", "SUPERVISOR", None, "Director (Monitoring)", security.hash_password("Supervisor@123")),
        ("rb.official@aicte.gov.in", "RB Official", "RB_OFFICIAL", b_rb.id, "Assistant Director", security.hash_password("Official@123")),
        ("pgrc.official@aicte.gov.in", "PGRC Official", "PGRC_OFFICIAL", b_pgrc.id, "Grievance Officer", security.hash_password("Official@123")),
    ]

    user_map = {}
    for email, name, role, bureau_id, designation, user_pw_hash in users_data:
        existing_u = db.query(User).filter(User.email == email).first()
        if existing_u:
            user_map[email] = existing_u
            continue
        u = User(
            email=email,
            password_hash=user_pw_hash,
            full_name=name,
            role=role,
            bureau_id=bureau_id,
            designation=designation,
            is_active=True,
            created_at=now - timedelta(days=60),
            updated_at=now - timedelta(days=60),
        )
        db.add(u)
        user_map[email] = u

    db.flush()

    # 3. Mandatory Institution (SYN-TN-0001)
    inst_meridian = Institution(
        code="SYN-TN-0001",
        name="Meridian Institute of Engineering and Technology",
        name_normalized="meridian institute of engineering and technology",
        institution_type="ENGINEERING",
        state="Tamil Nadu",
        district="Chennai",
        city="Chennai",
        address="100 Technology Highway, Chennai, Tamil Nadu",
        email="contact@meridian-demo.example",
        phone="044-23456789",
        is_active=True,
        created_at=now - timedelta(days=120),
        updated_at=now - timedelta(days=120),
    )
    db.add(inst_meridian)

    # 24 other institutions
    institutions = [inst_meridian]
    for i in range(2, 26):
        st = STATES[i % len(STATES)]
        itype = INSTITUTION_TYPES[i % len(INSTITUTION_TYPES)]
        code = f"SYN-{st[:2].upper()}-{i:04d}"
        inst = Institution(
            code=code,
            name=f"Synthetix {itype.title()} College of {st} ({i})",
            name_normalized=f"synthetix {itype.lower()} college of {st.lower()} ({i})",
            institution_type=itype,
            state=st,
            district=f"District {i}",
            city=f"City {i}",
            address=f"Campus Plot {i}, Academic Zone, {st}",
            email=f"info@{code.lower()}.example",
            phone=f"011-987654{i:02d}",
            is_active=True,
            created_at=now - timedelta(days=100 + i),
            updated_at=now - timedelta(days=100 + i),
        )
        db.add(inst)
        institutions.append(inst)

    db.flush()

    # 4. Mandatory Scenario Fixtures for SYN-TN-0001
    # Complaint (a): PRIMARY RB, owner rb.official1, UNDER_REVIEW, FEES_REFUND, HIGH, received 3 days ago, target received + 15
    rec_a = today - timedelta(days=3)
    target_a = rec_a + timedelta(days=15)
    title_a = "Fee refund not processed after admission cancellation"
    desc_a = (
        "Student reports that the institution has not refunded tuition and hostel fees after "
        "cancellation of admission within the permitted period. Multiple written requests to the "
        "accounts office have received no response."
    )
    kw_a = get_keywords(f"{title_a} {desc_a}")

    comp_a = Complaint(
        reference_number=f"CMP-{rec_a.strftime('%Y%m%d')}-0001",
        institution_id=inst_meridian.id,
        category="FEES_REFUND",
        priority="HIGH",
        status="UNDER_REVIEW",
        source_channel="PORTAL",
        complainant_type="STUDENT",
        complainant_name="Karthik R",
        complainant_contact="karthik.r@example.com",
        incident_reference="MER-ADM-2026-089",
        incident_date=rec_a - timedelta(days=5),
        received_date=rec_a,
        target_date=target_a,
        title=title_a,
        description=desc_a,
        keywords=kw_a,
        primary_bureau_id=b_rb.id,
        owner_user_id=user_map["rb.official1@aicte-demo.example"].id,
        participating_bureau_codes=[],
        created_by=user_map["rb.official1@aicte-demo.example"].id,
        created_at=datetime.combine(rec_a, datetime.min.time(), tzinfo=timezone.utc),
        updated_at=datetime.combine(rec_a, datetime.min.time(), tzinfo=timezone.utc),
        version=2,
    )
    db.add(comp_a)
    db.flush()

    # Assignment & History for (a)
    assign_a = CaseAssignment(
        complaint_id=comp_a.id,
        bureau_id=b_rb.id,
        role_in_case="PRIMARY",
        assigned_user_id=user_map["rb.official1@aicte-demo.example"].id,
        assigned_by=user_map["rb.official1@aicte-demo.example"].id,
        assigned_at=comp_a.created_at,
        is_active=True,
    )
    db.add(assign_a)

    hist_a1 = StatusHistory(
        complaint_id=comp_a.id,
        from_status=None,
        to_status="REGISTERED",
        changed_by=user_map["rb.official1@aicte-demo.example"].id,
        changed_at=comp_a.created_at,
        remark="Initial registration",
    )
    hist_a2 = StatusHistory(
        complaint_id=comp_a.id,
        from_status="REGISTERED",
        to_status="UNDER_REVIEW",
        changed_by=user_map["rb.official1@aicte-demo.example"].id,
        changed_at=comp_a.created_at + timedelta(hours=2),
        remark="Initial scrutiny completed, case admitted for review",
    )
    db.add_all([hist_a1, hist_a2])

    # Complaint (b): PRIMARY RB, owner rb.official2, ACTION_INITIATED, INFRASTRUCTURE, MEDIUM, received 40 days ago, target 10 days in PAST (overdue)
    rec_b = today - timedelta(days=40)
    target_b = today - timedelta(days=10)
    title_b = "Laboratory equipment shortage in computer science department"
    desc_b = (
        "Shortage of functional computers and licensed software in computer science laboratory. "
        "Students are forced to share workstations during practical sessions and examinations."
    )
    kw_b = get_keywords(f"{title_b} {desc_b}")

    comp_b = Complaint(
        reference_number=f"CMP-{rec_b.strftime('%Y%m%d')}-0001",
        institution_id=inst_meridian.id,
        category="INFRASTRUCTURE",
        priority="MEDIUM",
        status="ACTION_INITIATED",
        source_channel="LETTER",
        complainant_type="FACULTY",
        complainant_name="Prof. Sundaram",
        complainant_contact="prof.sundaram@example.com",
        incident_date=rec_b - timedelta(days=10),
        received_date=rec_b,
        target_date=target_b,
        title=title_b,
        description=desc_b,
        keywords=kw_b,
        primary_bureau_id=b_rb.id,
        owner_user_id=user_map["rb.official2@aicte-demo.example"].id,
        participating_bureau_codes=[],
        created_by=user_map["rb.official2@aicte-demo.example"].id,
        created_at=datetime.combine(rec_b, datetime.min.time(), tzinfo=timezone.utc),
        updated_at=datetime.combine(rec_b + timedelta(days=15), datetime.min.time(), tzinfo=timezone.utc),
        version=2,
    )
    db.add(comp_b)
    db.flush()

    assign_b = CaseAssignment(
        complaint_id=comp_b.id,
        bureau_id=b_rb.id,
        role_in_case="PRIMARY",
        assigned_user_id=user_map["rb.official2@aicte-demo.example"].id,
        assigned_by=user_map["rb.official2@aicte-demo.example"].id,
        assigned_at=comp_b.created_at,
        is_active=True,
    )
    db.add(assign_b)

    hist_b1 = StatusHistory(
        complaint_id=comp_b.id,
        from_status=None,
        to_status="REGISTERED",
        changed_by=user_map["rb.official2@aicte-demo.example"].id,
        changed_at=comp_b.created_at,
        remark="Registered from physical grievance letter",
    )
    hist_b2 = StatusHistory(
        complaint_id=comp_b.id,
        from_status="REGISTERED",
        to_status="UNDER_REVIEW",
        changed_by=user_map["rb.official2@aicte-demo.example"].id,
        changed_at=comp_b.created_at + timedelta(days=5),
        remark="Assigned for verification",
    )
    hist_b3 = StatusHistory(
        complaint_id=comp_b.id,
        from_status="UNDER_REVIEW",
        to_status="ACTION_INITIATED",
        changed_by=user_map["rb.official2@aicte-demo.example"].id,
        changed_at=comp_b.created_at + timedelta(days=15),
        remark="Explanation letter issued to the college management",
    )
    db.add_all([hist_b1, hist_b2, hist_b3])

    # 5. Populate remaining ~118 complaints across the 25 institutions
    all_complaints = [comp_a, comp_b]
    officials_list = [
        user_map["rb.official1@aicte-demo.example"],
        user_map["rb.official2@aicte-demo.example"],
        user_map["pgrc.official1@aicte-demo.example"],
        user_map["pgrc.official2@aicte-demo.example"],
    ]

    # Pre-define complaint templates with keywords for realistic relation matches
    templates = [
        ("FEES_REFUND", "Tuition fee refund not granted after withdrawing admission", "Complainant cancelled seat within counseling period but management is not refunding original fee payment."),
        ("FEES_REFUND", "Excess capitation fee collected and withheld", "Institution charged additional capitation fee and security deposit that is not being refunded."),
        ("INFRASTRUCTURE", "Inadequate library textbooks and digital journal access", "Library lacks required volumes for accredited branches and no internet access in labs."),
        ("FACULTY_ISSUES", "Severe shortage of qualified professors in mechanical department", "Classes are constantly cancelled due to lack of regular faculty and ad-hoc teachers leaving."),
        ("FACULTY_ISSUES", "Faculty salary delayed by four months without notice", "Staff and faculty have not received approved salary increments and monthly payments are delayed."),
        ("STUDENT_WELFARE", "Ragging incident reported in first year hostel campus", "Senior students subjected freshers to ragging inside hostel premises without anti-ragging squad intervention."),
        ("ADMISSION_IRREGULARITY", "Admission given beyond approved sanctioned intake capacity", "Management admitted additional candidates exceeding the official AICTE approved intake seats."),
        ("ACADEMIC_MISCONDUCT", "Forged faculty experience certificates submitted for approval", "Institution submitted fake certificates and unverified documents during affiliation inspection."),
    ]

    complaint_idx = 2
    for inst in institutions:
        # Determine number of cases for this institution (between 3 and 7)
        num_cases = 3 if inst.code == "SYN-TN-0001" else random.randint(3, 7)
        for c_num in range(num_cases):
            cat, base_title, base_desc = random.choice(templates)
            prio = random.choice(PRIORITIES)
            channel = random.choice(SOURCE_CHANNELS)
            ctype = random.choice(COMPLAINANT_TYPES)

            # Age of complaint
            # Ensure >= 15 overdue cases
            is_overdue_sample = complaint_idx % 6 == 0
            if is_overdue_sample:
                rec_days = random.randint(35, 75)
                rec_d = today - timedelta(days=rec_days)
                targ_d = today - timedelta(days=random.randint(5, 20))
                stat = random.choice(["UNDER_REVIEW", "ACTION_INITIATED", "PENDING_INFORMATION"])
            else:
                rec_days = random.randint(2, 60)
                rec_d = today - timedelta(days=rec_days)
                targ_d = rec_d + timedelta(days=PRIORITY_DAYS.get(prio, 30))
                stat = random.choice(["REGISTERED", "UNDER_REVIEW", "ACTION_INITIATED", "RESOLVED", "CLOSED"])

            off = officials_list[complaint_idx % len(officials_list)]
            prim_bureau_id = off.bureau_id

            comp_title = f"{base_title} [Ref {inst.code}-{c_num}]"
            comp_desc = f"{base_desc} Institution: {inst.name}. Reported via {channel}."
            kw = get_keywords(f"{comp_title} {comp_desc}")

            res_summary = "Issue was examined and institution management complied with AICTE directives." if stat in ("RESOLVED", "CLOSED") else None
            resolved_at = datetime.combine(rec_d + timedelta(days=15), datetime.min.time(), tzinfo=timezone.utc) if stat in ("RESOLVED", "CLOSED") else None
            closed_at = datetime.combine(rec_d + timedelta(days=20), datetime.min.time(), tzinfo=timezone.utc) if stat == "CLOSED" else None

            # Participating bureau
            part_codes = []
            if complaint_idx % 4 == 0:
                other_code = "PGRC" if off.bureau_id == b_rb.id else "RB"
                part_codes.append(other_code)

            c_obj = Complaint(
                reference_number=f"CMP-{rec_d.strftime('%Y%m%d')}-{complaint_idx:04d}",
                institution_id=inst.id,
                category=cat,
                priority=prio,
                status=stat,
                source_channel=channel,
                complainant_type=ctype,
                complainant_name=f"Complainant {complaint_idx}",
                complainant_contact=f"citizen{complaint_idx}@example.com",
                received_date=rec_d,
                target_date=targ_d,
                title=comp_title,
                description=comp_desc,
                keywords=kw,
                primary_bureau_id=prim_bureau_id,
                owner_user_id=off.id,
                participating_bureau_codes=part_codes,
                resolution_summary=res_summary,
                resolved_at=resolved_at,
                closed_at=closed_at,
                created_by=off.id,
                created_at=datetime.combine(rec_d, datetime.min.time(), tzinfo=timezone.utc),
                updated_at=datetime.combine(rec_d + timedelta(days=2), datetime.min.time(), tzinfo=timezone.utc),
                version=1,
            )
            db.add(c_obj)
            all_complaints.append(c_obj)
            complaint_idx += 1

    db.flush()

    # Create CaseAssignments and StatusHistory for each generated complaint
    for c in all_complaints[2:]:  # skip a and b which already have them
        assign = CaseAssignment(
            complaint_id=c.id,
            bureau_id=c.primary_bureau_id,
            role_in_case="PRIMARY",
            assigned_user_id=c.owner_user_id,
            assigned_by=user_map["supervisor@aicte-demo.example"].id,
            assigned_at=c.created_at,
            is_active=True,
        )
        db.add(assign)

        hist = StatusHistory(
            complaint_id=c.id,
            from_status=None,
            to_status=c.status,
            changed_by=c.created_by,
            changed_at=c.created_at,
            remark="Initial registration during setup",
        )
        db.add(hist)

        # If participating bureau was set, add assignment
        for pcode in c.participating_bureau_codes or []:
            pbureau = b_pgrc if pcode == "PGRC" else b_rb
            p_assign = CaseAssignment(
                complaint_id=c.id,
                bureau_id=pbureau.id,
                role_in_case="PARTICIPATING",
                assigned_by=user_map["supervisor@aicte-demo.example"].id,
                assigned_at=c.created_at + timedelta(days=1),
                reason="Multi-bureau coordination required",
                is_active=True,
            )
            db.add(p_assign)

    db.flush()

    # 6. Generate Relations using real calculate_relation_score:
    # Need >= 5 SUGGESTED, >= 4 CONFIRMED, >= 3 DISMISSED
    # Group complaints by institution
    by_inst = {}
    for c in all_complaints:
        if c.id in (comp_a.id, comp_b.id):
            continue  # do not add relations for a and b before scenario runs!
        by_inst.setdefault(c.institution_id, []).append(c)

    suggested_count = 0
    confirmed_count = 0
    dismissed_count = 0

    for i_id, c_list in by_inst.items():
        if len(c_list) < 2:
            continue
        for idx in range(len(c_list) - 1):
            c1 = c_list[idx]
            c2 = c_list[idx + 1]
            c1_dict = {
                "category": c1.category, "title": c1.title, "description": c1.description,
                "incident_reference": c1.incident_reference, "incident_date": c1.incident_date,
                "received_date": c1.received_date, "primary_bureau_code": c1.primary_bureau.code if c1.primary_bureau else None,
            }
            c2_dict = {
                "category": c2.category, "title": c2.title, "description": c2.description,
                "incident_reference": c2.incident_reference, "incident_date": c2.incident_date,
                "received_date": c2.received_date, "primary_bureau_code": c2.primary_bureau.code if c2.primary_bureau else None,
            }

            res = calculate_relation_score(c1_dict, c2_dict)
            if res["is_suggested"]:
                a_id = min(c1.id, c2.id)
                b_id = max(c1.id, c2.id)

                # Determine target status
                if confirmed_count < 5:
                    status = "CONFIRMED"
                    rel_type = "RELATED_ISSUE"
                    confirmed_count += 1
                elif dismissed_count < 4:
                    status = "DISMISSED"
                    rel_type = None
                    dismissed_count += 1
                elif suggested_count < 7:
                    status = "SUGGESTED"
                    rel_type = None
                    suggested_count += 1
                else:
                    break

                rel = ComplaintRelation(
                    complaint_a_id=a_id,
                    complaint_b_id=b_id,
                    status=status,
                    relation_type=rel_type,
                    score=res["score"],
                    confidence=res["confidence"],
                    explanation=res,
                    algorithm_version=ALGORITHM_VERSION,
                    detected_from_complaint_id=c1.id,
                    detected_at=c1.created_at,
                    reviewed_by=user_map["supervisor@aicte-demo.example"].id if status != "SUGGESTED" else None,
                    reviewed_at=now - timedelta(days=2) if status != "SUGGESTED" else None,
                    review_note="Verified during synthetic seed generation" if status != "SUGGESTED" else None,
                )
                db.add(rel)

    db.flush()

    # 7. Add notes on ~40 complaints
    for idx, c in enumerate(all_complaints[:40]):
        author = officials_list[idx % len(officials_list)]
        note = ComplaintNote(
            complaint_id=c.id,
            author_id=author.id,
            bureau_id=author.bureau_id,
            note_type="ACTION_NOTE" if idx % 2 == 0 else "COORDINATION_NOTE",
            body=f"Review note #{idx + 1}: Contacted institution coordinator regarding compliance verification.",
            created_at=c.created_at + timedelta(days=1),
        )
        db.add(note)

    # 8. Add notifications for users
    for off in officials_list:
        notif = Notification(
            user_id=off.id,
            type="COMPLAINT_ASSIGNED",
            title="System Initialization",
            message="Welcome to the AICTE Integrated Complaint Dashboard.",
            is_read=False,
            created_at=now - timedelta(days=1),
        )
        db.add(notif)

    # 9. Audit log for SEED_RUN
    write_audit(
        db,
        actor_user_id=user_map["admin@aicte-demo.example"].id,
        actor_email="admin@aicte-demo.example",
        actor_role="SYSTEM_ADMIN",
        action="SEED_RUN",
        entity_type="SYSTEM",
        entity_id="SEED",
        after_state={
            "institutions_count": len(institutions),
            "complaints_count": len(all_complaints),
            "confirmed_relations": confirmed_count,
            "dismissed_relations": dismissed_count,
            "suggested_relations": suggested_count,
        },
    )

    db.commit()

    logger.info(
        "Seeding completed successfully: %d institutions, %d complaints, %d confirmed, %d dismissed, %d suggested relations",
        len(institutions),
        len(all_complaints),
        confirmed_count,
        dismissed_count,
        suggested_count,
    )

    return {
        "institutions": len(institutions),
        "complaints": len(all_complaints),
        "confirmed_relations": confirmed_count,
        "dismissed_relations": dismissed_count,
        "suggested_relations": suggested_count,
    }
