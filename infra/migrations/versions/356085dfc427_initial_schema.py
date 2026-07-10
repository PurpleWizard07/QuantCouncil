"""Initial schema: all ten QuantCouncil foundation tables.

Creates assets, ohlcv_daily, strategy_definitions, backtest_runs,
risk_evaluations, agent_decisions, paper_portfolios, paper_orders,
paper_positions, and trade_journal, exactly matching
``app.db.models.Base.metadata`` (verified by
apps/api/tests/test_migrations.py, which asserts schema equivalence with
``Base.metadata.create_all``). Generated via autogenerate against an empty
scratch SQLite database; the models use only portable types, so the emitted
operations are dialect-neutral (``BigInteger().with_variant(Integer,
"sqlite")`` renders per-dialect at execution time).

Downgrade drops all tables in FK-safe (reverse-dependency) order.

Revision ID: 356085dfc427
Revises:
Create Date: 2026-07-07

"""
from __future__ import annotations


from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '356085dfc427'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('assets',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('symbol', sa.String(length=32), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('exchange', sa.String(length=16), nullable=False),
    sa.Column('sector', sa.String(length=128), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_assets_symbol'), 'assets', ['symbol'], unique=True)
    op.create_table('paper_portfolios',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('starting_capital', sa.Numeric(precision=14, scale=2), nullable=False),
    sa.Column('cash', sa.Numeric(precision=14, scale=2), nullable=False),
    sa.Column('nav', sa.Numeric(precision=14, scale=2), nullable=False),
    sa.Column('peak_nav', sa.Numeric(precision=14, scale=2), nullable=True),
    sa.Column('risk_off', sa.Boolean(), nullable=False),
    sa.Column('settings', sa.JSON(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('strategy_definitions',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('status', sa.String(length=32), nullable=False),
    sa.Column('rules', sa.JSON(), nullable=False),
    sa.Column('universe', sa.JSON(), nullable=False),
    sa.Column('timeframe', sa.String(length=8), nullable=False),
    sa.Column('direction', sa.String(length=16), nullable=False),
    sa.Column('version', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_strategy_definitions_name'), 'strategy_definitions', ['name'], unique=False)
    op.create_index(op.f('ix_strategy_definitions_status'), 'strategy_definitions', ['status'], unique=False)
    op.create_table('backtest_runs',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('strategy_id', sa.Uuid(), nullable=False),
    sa.Column('start_date', sa.Date(), nullable=False),
    sa.Column('end_date', sa.Date(), nullable=False),
    sa.Column('initial_capital', sa.Numeric(precision=14, scale=2), nullable=False),
    sa.Column('params', sa.JSON(), nullable=False),
    sa.Column('metrics', sa.JSON(), nullable=True),
    sa.Column('equity_curve_path', sa.String(length=512), nullable=True),
    sa.Column('trades_path', sa.String(length=512), nullable=True),
    sa.Column('status', sa.String(length=16), nullable=False),
    sa.Column('error', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['strategy_id'], ['strategy_definitions.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_backtest_runs_status'), 'backtest_runs', ['status'], unique=False)
    op.create_index(op.f('ix_backtest_runs_strategy_id'), 'backtest_runs', ['strategy_id'], unique=False)
    op.create_table('ohlcv_daily',
    sa.Column('id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), autoincrement=True, nullable=False),
    sa.Column('asset_id', sa.Integer(), nullable=False),
    sa.Column('date', sa.Date(), nullable=False),
    sa.Column('open', sa.Numeric(precision=14, scale=4), nullable=False),
    sa.Column('high', sa.Numeric(precision=14, scale=4), nullable=False),
    sa.Column('low', sa.Numeric(precision=14, scale=4), nullable=False),
    sa.Column('close', sa.Numeric(precision=14, scale=4), nullable=False),
    sa.Column('volume', sa.BigInteger(), nullable=False),
    sa.Column('source', sa.String(length=32), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['asset_id'], ['assets.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('asset_id', 'date', name='uq_ohlcv_daily_asset_date')
    )
    op.create_index(op.f('ix_ohlcv_daily_asset_id'), 'ohlcv_daily', ['asset_id'], unique=False)
    op.create_index(op.f('ix_ohlcv_daily_date'), 'ohlcv_daily', ['date'], unique=False)
    op.create_table('paper_positions',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('portfolio_id', sa.Uuid(), nullable=False),
    sa.Column('asset_id', sa.Integer(), nullable=False),
    sa.Column('strategy_id', sa.Uuid(), nullable=True),
    sa.Column('quantity', sa.Integer(), nullable=False),
    sa.Column('avg_entry_price', sa.Numeric(precision=14, scale=4), nullable=False),
    sa.Column('stop_loss', sa.Numeric(precision=14, scale=4), nullable=False),
    sa.Column('status', sa.String(length=16), nullable=False),
    sa.Column('last_price', sa.Numeric(precision=14, scale=4), nullable=True),
    sa.Column('unrealized_pnl', sa.Numeric(precision=14, scale=2), nullable=True),
    sa.Column('realized_pnl', sa.Numeric(precision=14, scale=2), nullable=True),
    sa.Column('opened_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('closed_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['asset_id'], ['assets.id'], ),
    sa.ForeignKeyConstraint(['portfolio_id'], ['paper_portfolios.id'], ),
    sa.ForeignKeyConstraint(['strategy_id'], ['strategy_definitions.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_paper_positions_asset_id'), 'paper_positions', ['asset_id'], unique=False)
    op.create_index(op.f('ix_paper_positions_portfolio_id'), 'paper_positions', ['portfolio_id'], unique=False)
    op.create_index(op.f('ix_paper_positions_status'), 'paper_positions', ['status'], unique=False)
    op.create_index(op.f('ix_paper_positions_strategy_id'), 'paper_positions', ['strategy_id'], unique=False)
    op.create_table('agent_decisions',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('strategy_id', sa.Uuid(), nullable=True),
    sa.Column('backtest_run_id', sa.Uuid(), nullable=True),
    sa.Column('agent_role', sa.String(length=32), nullable=False),
    sa.Column('model', sa.String(length=128), nullable=True),
    sa.Column('input', sa.JSON(), nullable=False),
    sa.Column('output', sa.JSON(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['backtest_run_id'], ['backtest_runs.id'], ),
    sa.ForeignKeyConstraint(['strategy_id'], ['strategy_definitions.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_agent_decisions_agent_role'), 'agent_decisions', ['agent_role'], unique=False)
    op.create_index(op.f('ix_agent_decisions_backtest_run_id'), 'agent_decisions', ['backtest_run_id'], unique=False)
    op.create_index(op.f('ix_agent_decisions_strategy_id'), 'agent_decisions', ['strategy_id'], unique=False)
    op.create_table('risk_evaluations',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('backtest_run_id', sa.Uuid(), nullable=False),
    sa.Column('strategy_id', sa.Uuid(), nullable=False),
    sa.Column('decision', sa.String(length=16), nullable=False),
    sa.Column('approved', sa.Boolean(), nullable=False),
    sa.Column('risk_score', sa.Integer(), nullable=False),
    sa.Column('reasons', sa.JSON(), nullable=False),
    sa.Column('failed_rules', sa.JSON(), nullable=False),
    sa.Column('warnings', sa.JSON(), nullable=False),
    sa.Column('policy_version', sa.String(length=16), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['backtest_run_id'], ['backtest_runs.id'], ),
    sa.ForeignKeyConstraint(['strategy_id'], ['strategy_definitions.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_risk_evaluations_backtest_run_id'), 'risk_evaluations', ['backtest_run_id'], unique=False)
    op.create_index(op.f('ix_risk_evaluations_strategy_id'), 'risk_evaluations', ['strategy_id'], unique=False)
    op.create_table('paper_orders',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('portfolio_id', sa.Uuid(), nullable=False),
    sa.Column('asset_id', sa.Integer(), nullable=False),
    sa.Column('strategy_id', sa.Uuid(), nullable=True),
    sa.Column('backtest_run_id', sa.Uuid(), nullable=True),
    sa.Column('risk_evaluation_id', sa.Uuid(), nullable=True),
    sa.Column('side', sa.String(length=4), nullable=False),
    sa.Column('quantity', sa.Integer(), nullable=False),
    sa.Column('order_type', sa.String(length=16), nullable=False),
    sa.Column('status', sa.String(length=16), nullable=False),
    sa.Column('limit_price', sa.Numeric(precision=14, scale=4), nullable=True),
    sa.Column('fill_price', sa.Numeric(precision=14, scale=4), nullable=True),
    sa.Column('stop_loss', sa.Numeric(precision=14, scale=4), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('filled_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['asset_id'], ['assets.id'], ),
    sa.ForeignKeyConstraint(['backtest_run_id'], ['backtest_runs.id'], ),
    sa.ForeignKeyConstraint(['portfolio_id'], ['paper_portfolios.id'], ),
    sa.ForeignKeyConstraint(['risk_evaluation_id'], ['risk_evaluations.id'], ),
    sa.ForeignKeyConstraint(['strategy_id'], ['strategy_definitions.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_paper_orders_asset_id'), 'paper_orders', ['asset_id'], unique=False)
    op.create_index(op.f('ix_paper_orders_portfolio_id'), 'paper_orders', ['portfolio_id'], unique=False)
    op.create_index(op.f('ix_paper_orders_status'), 'paper_orders', ['status'], unique=False)
    op.create_index(op.f('ix_paper_orders_strategy_id'), 'paper_orders', ['strategy_id'], unique=False)
    op.create_table('trade_journal',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('portfolio_id', sa.Uuid(), nullable=False),
    sa.Column('order_id', sa.Uuid(), nullable=True),
    sa.Column('position_id', sa.Uuid(), nullable=True),
    sa.Column('strategy_id', sa.Uuid(), nullable=True),
    sa.Column('entry_type', sa.String(length=16), nullable=False),
    sa.Column('title', sa.String(length=255), nullable=False),
    sa.Column('body', sa.Text(), nullable=False),
    sa.Column('refs', sa.JSON(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['order_id'], ['paper_orders.id'], ),
    sa.ForeignKeyConstraint(['portfolio_id'], ['paper_portfolios.id'], ),
    sa.ForeignKeyConstraint(['position_id'], ['paper_positions.id'], ),
    sa.ForeignKeyConstraint(['strategy_id'], ['strategy_definitions.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_trade_journal_entry_type'), 'trade_journal', ['entry_type'], unique=False)
    op.create_index(op.f('ix_trade_journal_portfolio_id'), 'trade_journal', ['portfolio_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_trade_journal_portfolio_id'), table_name='trade_journal')
    op.drop_index(op.f('ix_trade_journal_entry_type'), table_name='trade_journal')
    op.drop_table('trade_journal')
    op.drop_index(op.f('ix_paper_orders_strategy_id'), table_name='paper_orders')
    op.drop_index(op.f('ix_paper_orders_status'), table_name='paper_orders')
    op.drop_index(op.f('ix_paper_orders_portfolio_id'), table_name='paper_orders')
    op.drop_index(op.f('ix_paper_orders_asset_id'), table_name='paper_orders')
    op.drop_table('paper_orders')
    op.drop_index(op.f('ix_risk_evaluations_strategy_id'), table_name='risk_evaluations')
    op.drop_index(op.f('ix_risk_evaluations_backtest_run_id'), table_name='risk_evaluations')
    op.drop_table('risk_evaluations')
    op.drop_index(op.f('ix_agent_decisions_strategy_id'), table_name='agent_decisions')
    op.drop_index(op.f('ix_agent_decisions_backtest_run_id'), table_name='agent_decisions')
    op.drop_index(op.f('ix_agent_decisions_agent_role'), table_name='agent_decisions')
    op.drop_table('agent_decisions')
    op.drop_index(op.f('ix_paper_positions_strategy_id'), table_name='paper_positions')
    op.drop_index(op.f('ix_paper_positions_status'), table_name='paper_positions')
    op.drop_index(op.f('ix_paper_positions_portfolio_id'), table_name='paper_positions')
    op.drop_index(op.f('ix_paper_positions_asset_id'), table_name='paper_positions')
    op.drop_table('paper_positions')
    op.drop_index(op.f('ix_ohlcv_daily_date'), table_name='ohlcv_daily')
    op.drop_index(op.f('ix_ohlcv_daily_asset_id'), table_name='ohlcv_daily')
    op.drop_table('ohlcv_daily')
    op.drop_index(op.f('ix_backtest_runs_strategy_id'), table_name='backtest_runs')
    op.drop_index(op.f('ix_backtest_runs_status'), table_name='backtest_runs')
    op.drop_table('backtest_runs')
    op.drop_index(op.f('ix_strategy_definitions_status'), table_name='strategy_definitions')
    op.drop_index(op.f('ix_strategy_definitions_name'), table_name='strategy_definitions')
    op.drop_table('strategy_definitions')
    op.drop_table('paper_portfolios')
    op.drop_index(op.f('ix_assets_symbol'), table_name='assets')
    op.drop_table('assets')
