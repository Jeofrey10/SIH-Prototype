"""Command line interface for AICTE Complaint Dashboard."""
from __future__ import annotations

import argparse
import sys

from app.db.session import SessionLocal
from app.jobs.overdue_scan import run_overdue_scan
from app.seed.generator import run_seed
from app.services.users import create_user


def main() -> None:
    parser = argparse.ArgumentParser(description="AICTE Complaint Dashboard CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Seed command
    seed_parser = subparsers.add_parser("seed", help="Seed database with synthetic data")
    seed_parser.add_argument(
        "--reset",
        action="store_true",
        help="Reset existing data before seeding (prohibited in production)",
    )

    # Overdue scan command
    subparsers.add_parser("overdue-scan", help="Run overdue complaints detection scan")

    # Create admin command
    admin_parser = subparsers.add_parser("create-admin", help="Create an administrator user")
    admin_parser.add_argument("email", help="Administrator email")
    admin_parser.add_argument("password", help="Administrator password")
    admin_parser.add_argument("full_name", help="Administrator full name")

    args = parser.parse_args()

    db = SessionLocal()
    try:
        if args.command == "seed":
            results = run_seed(db, reset=args.reset)
            print("Seed complete:", results)

        elif args.command == "overdue-scan":
            results = run_overdue_scan(db)
            db.commit()
            print("Overdue scan complete:", results)

        elif args.command == "create-admin":
            from app.models import User
            # System pseudo-actor for bootstrap
            system_actor = User(email="system@aicte-internal.gov", role="SYSTEM_ADMIN")
            user = create_user(
                db,
                data={
                    "email": args.email,
                    "password": args.password,
                    "full_name": args.full_name,
                    "role": "SYSTEM_ADMIN",
                },
                actor=system_actor,
            )
            db.commit()
            print(f"Created admin user {user.email} (ID: {user.id})")

    except Exception as exc:
        db.rollback()
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
