"""NAV snapshots: daily NAV/cash/drawdown/risk-off history (Phase 9).

The Daily Ops Loop's ``run_daily_cycle`` upserts one ``nav_snapshots`` row per
(portfolio, date) after each day's stop-loss sweep and mark-to-market, so the
API can serve a NAV/drawdown/risk-off history chart (``GET
/paper/portfolios/{id}/nav-history``) without replaying every order.
``uq_nav_snapshots_portfolio_date`` enforces at most one row per portfolio per
day; re-running the cycle for the same day updates that row in place (see
``app.db.repositories.upsert_nav_snapshot``).

Revision ID: 2810b70e4708
Revises: 853ec0ddce66
Create Date: 2026-07-10

"""
from __future__ import annotations


from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '2810b70e4708'
down_revision = '853ec0ddce66'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('nav_snapshots',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('portfolio_id', sa.Uuid(), nullable=False),
    sa.Column('date', sa.Date(), nullable=False),
    sa.Column('nav', sa.Numeric(precision=14, scale=2), nullable=False),
    sa.Column('cash', sa.Numeric(precision=14, scale=2), nullable=False),
    sa.Column('drawdown', sa.Numeric(precision=8, scale=6), nullable=True),
    sa.Column('risk_off', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['portfolio_id'], ['paper_portfolios.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('portfolio_id', 'date', name='uq_nav_snapshots_portfolio_date')
    )
    op.create_index(op.f('ix_nav_snapshots_portfolio_id'), 'nav_snapshots', ['portfolio_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_nav_snapshots_portfolio_id'), table_name='nav_snapshots')
    op.drop_table('nav_snapshots')
