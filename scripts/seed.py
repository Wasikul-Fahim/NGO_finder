"""Idempotent demo data. Run from repo root: `.venv/bin/python scripts/seed.py`.

Passwords come from SEED_PASSWORD (local demo default below). Never use this in production.
"""
import os
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from sqlalchemy import select

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models import (
    NGO,
    Beneficiary,
    Campaign,
    CampaignStatus,
    Event,
    Opportunity,
    Role,
    User,
    VerificationStatus,
    Volunteer,
)

PASSWORD = os.environ.get("SEED_PASSWORD", "Demo12345")

USERS = [
    ("admin@example.com", "Platform Admin", Role.PLATFORM_ADMIN, "Dhaka"),
    ("ngo@example.com", "Shobuj Foundation Admin", Role.NGO_ADMIN, "Dhaka"),
    ("volunteer1@example.com", "Ayesha Rahman", Role.VOLUNTEER, "Dhaka"),
    ("volunteer2@example.com", "Tanvir Hossain", Role.VOLUNTEER, "Sylhet"),
    ("donor1@example.com", "Nusrat Jahan", Role.DONOR, "Dhaka"),
    ("beneficiary1@example.com", "Rahim Uddin", Role.BENEFICIARY, "Sylhet"),
]


def get_or_create_user(db, email, name, role, location) -> User:
    user = db.scalar(select(User).where(User.email == email))
    if user is None:
        user = User(
            email=email, name=name, role=role, location=location,
            password_hash=hash_password(PASSWORD), is_active=True, is_verified=True,
        )
        db.add(user)
        db.flush()
    return user


def main() -> None:
    today = date.today()
    with SessionLocal() as db:
        users = {u[0]: get_or_create_user(db, *u) for u in USERS}

        profiles = {
            "volunteer1@example.com": (["Teaching", "First Aid"], ["Education"], ["SAT", "SUN"]),
            "volunteer2@example.com": (["Logistics", "Driving"], ["Disaster Relief"], ["FRI", "SAT"]),
        }
        for email, (skills, interests, days) in profiles.items():
            uid = users[email].id
            if not db.scalar(select(Volunteer.id).where(Volunteer.user_id == uid)):
                db.add(Volunteer(user_id=uid, skills=skills, interests=interests, availability=days))
        users["volunteer1@example.com"].location = "Dhaka, Dhaka"
        users["volunteer2@example.com"].location = "Sylhet, Sylhet"
        ben = users["beneficiary1@example.com"]
        if not db.scalar(select(Beneficiary.id).where(Beneficiary.user_id == ben.id)):
            db.add(Beneficiary(user_id=ben.id, name=ben.name, location=ben.location))

        admin = users["ngo@example.com"]
        ngo = db.scalar(select(NGO).where(NGO.user_id == admin.id))
        if ngo is None:
            ngo = NGO(
                user_id=admin.id, ngo_name="Shobuj Foundation",
                description="Education and community development across Bangladesh.",
                address="Mirpur, Dhaka", contact="info@shobuj.test",
                verification_status=VerificationStatus.VERIFIED,
            )
            db.add(ngo)
            db.flush()

        samples = [
            ("Sylhet Flood Relief", "Sylhet", CampaignStatus.ACTIVE, -10, 20, 50),
            ("Back to School 2026", "Dhaka", CampaignStatus.ACTIVE, -5, 60, 30),
            ("Clean Water Drive (draft)", "Kurigram", CampaignStatus.DRAFT, 15, 90, 15),
        ]
        for title, location, status, start, end, vols in samples:
            campaign = db.scalar(select(Campaign).where(Campaign.ngo_id == ngo.id, Campaign.title == title))
            if campaign is None:
                campaign = Campaign(
                    ngo_id=ngo.id, title=title, location=location, status=status,
                    description=f"{title} organised by {ngo.ngo_name}.",
                    start_date=today + timedelta(days=start), end_date=today + timedelta(days=end),
                    required_volunteers=vols,
                    required_resources=[{"name": "Volunteers' kits", "quantity": vols * 2, "unit": "pcs"}],
                )
                db.add(campaign)
                db.flush()
            if not db.scalar(select(Event.id).where(Event.campaign_id == campaign.id)):
                db.add(Event(
                    campaign_id=campaign.id, event_name=f"{title}: kickoff",
                    event_date=campaign.start_date + timedelta(days=max(0, start * -1 + 1)) if start < 0
                    else campaign.start_date,
                    location=location, description="Orientation and first distribution.",
                ))
        opportunities = [
            ("Community Learning Facilitator", "Dhaka, Dhaka", ["Teaching"], ["Education"], ["SAT", "SUN"]),
            ("Flood Relief Logistics Driver", "Sylhet, Sylhet", ["Driving", "Logistics"], ["Disaster Relief"], ["FRI", "SAT"]),
            ("First Aid Camp Volunteer", "Gazipur, Dhaka", ["First Aid"], ["Health"], ["SUN"]),
        ]
        for title, location, skills, interests, days in opportunities:
            if not db.scalar(select(Opportunity.id).where(Opportunity.ngo_id == ngo.id, Opportunity.title == title)):
                db.add(Opportunity(
                    ngo_id=ngo.id, title=title, location=location, required_skills=skills,
                    interests=interests, availability=days, description=f"{title} with {ngo.ngo_name}.",
                ))
        db.commit()
    print("Seeded. Log in with any seeded email and password:", PASSWORD)


if __name__ == "__main__":
    main()
