import os

from deforestwatch.db.base import SessionLocal
from deforestwatch.db.models import Subscriber


def seed() -> int:
    email = os.environ.get("TEAM_EMAIL")
    if not email:
        raise RuntimeError("TEAM_EMAIL must be set before subscriber seeding")
    with SessionLocal.begin() as session:
        if session.query(Subscriber).filter_by(email=email).first():
            return 0
        session.add(Subscriber(name="DeforestWatch team", email=email, role="admin"))
    return 1


if __name__ == "__main__":
    print(f"seeded {seed()} subscribers")
