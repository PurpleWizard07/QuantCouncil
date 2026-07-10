"""Risk evaluation snapshots: add metrics_snapshot and policy_snapshot.

Phase 4: the rule-based risk engine's ``evaluate()`` records a verbatim copy
of the metrics dict it was evaluated against (``metrics_snapshot``) and the
``RiskPolicy`` it was evaluated under (``policy_snapshot``), so any
historical ``risk_evaluations`` row can be interpreted and reproduced without
needing to reconstruct either from other tables. Both columns are nullable
JSON, matching ``app.db.models.RiskEvaluation``.

Revision ID: 853ec0ddce66
Revises: 356085dfc427
Create Date: 2026-07-07

"""
from __future__ import annotations


from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '853ec0ddce66'
down_revision = '356085dfc427'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("risk_evaluations", sa.Column("metrics_snapshot", sa.JSON(), nullable=True))
    op.add_column("risk_evaluations", sa.Column("policy_snapshot", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("risk_evaluations", "policy_snapshot")
    op.drop_column("risk_evaluations", "metrics_snapshot")
