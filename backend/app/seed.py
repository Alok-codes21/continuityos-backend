"""Optional demo data. Everything is labelled SYNTHETIC and goes through the same ingestion pipeline as real uploads.
Run:  python -m app.seed   (needs SEED_ADMIN_PASSWORD; there is no default password)"""
import os
import sys

from . import models as m
from .connectors.base import NormalizedRecord
from .connectors.manual_upload import ManualUploadConnector
from .db import SessionLocal, init_db
from .security import hash_password
from .services import graph, ingest

DOCS = {
    "SYNTHETIC architecture.md": "Priya Sharma owns payments-service.\nAnjali Jha owns auth-service.\npayments-service depends on auth-service.\n"
                                 "We decided to use PostgreSQL instead of MongoDB because transactions need strong consistency.\n"
                                 "We decided to adopt Redis for the payments-service cache.\nThe payments-service timeout is 30 seconds.\n",
    "SYNTHETIC runbook.md": "The payments-service timeout is 60 seconds.\nDeploys of billing-service are manual.\n",
}


def main():
    pw = os.getenv("SEED_ADMIN_PASSWORD")
    if not pw or len(pw) < 10:
        sys.exit("Set SEED_ADMIN_PASSWORD (10+ chars). No default password exists.")
    init_db()
    db = SessionLocal()
    email = os.getenv("SEED_ADMIN_EMAIL", "admin@demo.local")
    if db.query(m.User).filter_by(email=email).first():
        sys.exit("Seed already applied")
    u = m.User(email=email, name="Demo Admin", password_hash=hash_password(pw))
    org = m.Organisation(name="Demo Org (synthetic)", domain="demo.local")
    db.add_all([u, org]); db.flush()
    db.add(m.Membership(org_id=org.id, user_id=u.id, role="admin"))
    prj = m.Project(org_id=org.id, name="Demo project (synthetic)"); db.add(prj); db.flush()
    integ = m.Integration(org_id=org.id, connector="manual_upload", created_by=u.id); db.add(integ); db.flush()
    src = m.Source(project_id=prj.id, integration_id=integ.id, source_type="manual_upload", external_id="uploads", name="Synthetic uploads")
    db.add(src); db.flush()
    graph.ensure_person(db, prj.id, u.name)
    c = ManualUploadConnector()
    ingest.ingest_records(db, prj, src, [c.normalize_record({"filename": n, "text": t, "author": "Priya Sharma", "occurred_at": m.now()}) for n, t in DOCS.items()], actor=u)
    db.commit()
    print("Seeded synthetic demo. Login:", email)


if __name__ == "__main__":
    main()
