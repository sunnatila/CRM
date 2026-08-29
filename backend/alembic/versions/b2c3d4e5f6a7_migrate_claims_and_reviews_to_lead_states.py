"""migrate claims and reviews into lead_states

Folds the v1 state (company_claims + company_reviews.locked) into the v2 five-status
model. Nothing is deleted: company_claims, claim_requests, permission_requests and
company_reviews.locked all stay exactly as they were, so a downgrade puts the old
system back untouched.

Mapping (PRD 2026-08-20 section 10):
  both review fields locked  -> approved
  one review field locked    -> waiting  + system note
  claim status 'active'      -> in_progress, same operator
  claim status 'deferred'    -> waiting  + the operator's own defer reason as the
                                handover note (a system note when they gave none)
  everything else            -> no row at all, which reads as 'new'

A claim wins over a review-derived status: an operator actively holding a company
is a stronger signal than a half-filled review row.

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-08-20 14:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()

    # --- 1. Reviews: how many fields did each company get filled? -------------
    # locked=true is v1's "this field is done" marker. A company with both
    # website and lms locked was fully reviewed; one locked field means the
    # operator got halfway and stopped.
    review_rows = conn.execute(sa.text("""
        SELECT company_id, COUNT(*) FILTER (WHERE locked) AS locked_count,
               MAX(filled_by_id) AS filled_by_id, MAX(filled_at) AS filled_at
          FROM company_reviews
         GROUP BY company_id
    """)).mappings().all()

    states: dict[int, dict] = {}
    for row in review_rows:
        locked_count = row["locked_count"] or 0
        if locked_count >= 2:
            states[row["company_id"]] = {
                "status": "approved",
                "assigned_to_id": None,
                "last_actor_id": row["filled_by_id"],
                "last_activity_at": row["filled_at"],
                "note": "Migratsiya — v1 da to'liq to'ldirilgan yozuv.",
            }
        elif locked_count == 1:
            states[row["company_id"]] = {
                "status": "waiting",
                "assigned_to_id": None,
                "last_actor_id": row["filled_by_id"],
                "last_activity_at": row["filled_at"],
                "note": "Migratsiya — v1 da faqat bitta maydon to'ldirilgan. Qolgan maydonni tekshirish kerak.",
            }

    # --- 2. Claims override reviews ------------------------------------------
    # Ordered by id so that if a company somehow carries more than one open claim
    # (v1 allowed the row to linger), the newest one wins.
    claim_rows = conn.execute(sa.text("""
        SELECT company_id, operator_id, status, claimed_at
          FROM company_claims
         WHERE status IN ('active', 'deferred')
         ORDER BY id
    """)).mappings().all()

    # Reasons live on claim_requests, not on the claim itself: the operator's
    # stated "why" for a defer is the closest v1 thing to a handover note.
    reason_rows = conn.execute(sa.text("""
        SELECT cc.company_id, cr.reason
          FROM claim_requests cr
          JOIN company_claims cc ON cc.id = cr.claim_id
         WHERE cr.reason IS NOT NULL AND cr.reason <> ''
         ORDER BY cr.id
    """)).mappings().all()
    reason_by_company = {r["company_id"]: r["reason"] for r in reason_rows}

    now = conn.execute(sa.text("SELECT now()")).scalar()

    for row in claim_rows:
        company_id = row["company_id"]
        if row["status"] == "active":
            states[company_id] = {
                "status": "in_progress",
                "assigned_to_id": row["operator_id"],
                "last_actor_id": row["operator_id"],
                # Reset the inactivity clock to the migration moment rather than
                # the original claim time -- otherwise every migrated claim is
                # instantly past the 4-hour auto-release window and the operator
                # loses their work the second they log in.
                "last_activity_at": now,
                "assigned_at": row["claimed_at"],
                "note": "Migratsiya — v1 da faol ish sifatida band qilingan.",
            }
        else:  # deferred
            reason = reason_by_company.get(company_id)
            states[company_id] = {
                "status": "waiting",
                "assigned_to_id": None,
                "last_actor_id": row["operator_id"],
                "last_activity_at": row["claimed_at"],
                "note": (
                    f"Migratsiya — v1 da kechiktirilgan. Operatorning izohi: {reason}"
                    if reason
                    else "Migratsiya — v1 da kechiktirilgan, izoh qoldirilmagan. Qayerda to'xtaganini tekshirish kerak."
                ),
            }

    if not states:
        return

    # --- 3. Write ------------------------------------------------------------
    # Only companies that still exist -- a review or claim row pointing at a
    # deleted company would break the FK.
    live_ids = {
        r[0]
        for r in conn.execute(
            sa.text("SELECT id FROM companies WHERE id = ANY(:ids)"), {"ids": list(states)}
        ).all()
    }

    for company_id, state in states.items():
        if company_id not in live_ids:
            continue
        conn.execute(
            sa.text("""
                INSERT INTO lead_states (company_id, status, assigned_to_id, assigned_at,
                                         last_activity_at, last_actor_id, created_at, updated_at)
                VALUES (:company_id, :status, :assigned_to_id, :assigned_at,
                        :last_activity_at, :last_actor_id, now(), now())
                ON CONFLICT (company_id) DO NOTHING
            """),
            {
                "company_id": company_id,
                "status": state["status"],
                "assigned_to_id": state["assigned_to_id"],
                "assigned_at": state.get("assigned_at"),
                "last_activity_at": state["last_activity_at"],
                "last_actor_id": state["last_actor_id"],
            },
        )
        # actor_id NULL marks this as the system's doing, so the timeline reads
        # "Tizim" rather than crediting an operator who never wrote it.
        conn.execute(
            sa.text("""
                INSERT INTO lead_events (company_id, actor_id, type, from_status, to_status, note, created_at)
                VALUES (:company_id, NULL, 'migration', NULL, :to_status, :note, now())
            """),
            {"company_id": company_id, "to_status": state["status"], "note": state["note"]},
        )


def downgrade() -> None:
    # Only the rows this migration wrote. Anything created by the running v2 app
    # afterwards is left alone -- a downgrade should undo the migration, not wipe
    # work operators have done since.
    conn = op.get_bind()
    conn.execute(sa.text("""
        DELETE FROM lead_events
         WHERE type = 'migration'
    """))
    conn.execute(sa.text("""
        DELETE FROM lead_states ls
         WHERE NOT EXISTS (
                   SELECT 1 FROM lead_events le
                    WHERE le.company_id = ls.company_id
               )
    """))
