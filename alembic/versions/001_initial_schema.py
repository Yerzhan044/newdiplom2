"""Initial migration: create all tables

Revision ID: 001
Revises:
Create Date: 2026-05-15

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Создание всех таблиц"""

    # Таблица users
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('country', sa.String(length=2), nullable=False),
        sa.Column('bank', sa.String(length=50), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)
    op.create_index(op.f('ix_users_name'), 'users', ['name'], unique=False)

    # Таблица accounts
    op.create_table(
        'accounts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('account_number', sa.String(length=34), nullable=False),
        sa.Column('currency', sa.String(length=3), nullable=False),
        sa.Column('balance', sa.Float(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('account_number'),
    )
    op.create_index(op.f('ix_accounts_id'), 'accounts', ['id'], unique=False)
    op.create_index(op.f('ix_accounts_user_id'), 'accounts', ['user_id'], unique=False)
    op.create_index(op.f('ix_accounts_account_number'), 'accounts', ['account_number'], unique=False)

    # Таблица transactions
    op.create_table(
        'transactions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('sender_id', sa.Integer(), nullable=False),
        sa.Column('receiver_id', sa.Integer(), nullable=False),
        sa.Column('account_id', sa.Integer(), nullable=False),
        sa.Column('amount', sa.Float(), nullable=False),
        sa.Column('currency', sa.String(length=3), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=True),
        sa.Column('description', sa.String(length=500), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('location', sa.String(length=100), nullable=True),
        sa.Column('device_id', sa.String(length=100), nullable=True),
        sa.Column('status', sa.Enum('approved', 'review', 'blocked', 'pending', name='transactionstatusenum'), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['sender_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['receiver_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['account_id'], ['accounts.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_transactions_id'), 'transactions', ['id'], unique=False)
    op.create_index(op.f('ix_transactions_sender_id'), 'transactions', ['sender_id'], unique=False)
    op.create_index(op.f('ix_transactions_receiver_id'), 'transactions', ['receiver_id'], unique=False)
    op.create_index(op.f('ix_transactions_account_id'), 'transactions', ['account_id'], unique=False)
    op.create_index(op.f('ix_transactions_timestamp'), 'transactions', ['timestamp'], unique=False)
    op.create_index(op.f('ix_transactions_status'), 'transactions', ['status'], unique=False)
    op.create_index(op.f('ix_transactions_created_at'), 'transactions', ['created_at'], unique=False)

    # Таблица fraud_scores
    op.create_table(
        'fraud_scores',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('transaction_id', sa.Integer(), nullable=False),
        sa.Column('xgboost_score', sa.Float(), nullable=True),
        sa.Column('random_forest_score', sa.Float(), nullable=True),
        sa.Column('lstm_score', sa.Float(), nullable=True),
        sa.Column('isolation_forest_score', sa.Float(), nullable=True),
        sa.Column('rule_engine_score', sa.Float(), nullable=True),
        sa.Column('final_score', sa.Float(), nullable=False),
        sa.Column('explanation', sa.String(length=1000), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['transaction_id'], ['transactions.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('transaction_id'),
    )
    op.create_index(op.f('ix_fraud_scores_id'), 'fraud_scores', ['id'], unique=False)
    op.create_index(op.f('ix_fraud_scores_transaction_id'), 'fraud_scores', ['transaction_id'], unique=False)
    op.create_index(op.f('ix_fraud_scores_created_at'), 'fraud_scores', ['created_at'], unique=False)

    # Таблица fraud_patterns
    op.create_table(
        'fraud_patterns',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('transaction_id', sa.Integer(), nullable=False),
        sa.Column('pattern_name', sa.String(length=100), nullable=False),
        sa.Column('pattern_description', sa.String(length=500), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=False),
        sa.Column('details', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['transaction_id'], ['transactions.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_fraud_patterns_id'), 'fraud_patterns', ['id'], unique=False)
    op.create_index(op.f('ix_fraud_patterns_transaction_id'), 'fraud_patterns', ['transaction_id'], unique=False)
    op.create_index(op.f('ix_fraud_patterns_pattern_name'), 'fraud_patterns', ['pattern_name'], unique=False)
    op.create_index(op.f('ix_fraud_patterns_created_at'), 'fraud_patterns', ['created_at'], unique=False)


def downgrade() -> None:
    """Удаление всех таблиц"""
    op.drop_index(op.f('ix_fraud_patterns_created_at'), table_name='fraud_patterns')
    op.drop_index(op.f('ix_fraud_patterns_pattern_name'), table_name='fraud_patterns')
    op.drop_index(op.f('ix_fraud_patterns_transaction_id'), table_name='fraud_patterns')
    op.drop_index(op.f('ix_fraud_patterns_id'), table_name='fraud_patterns')
    op.drop_table('fraud_patterns')

    op.drop_index(op.f('ix_fraud_scores_created_at'), table_name='fraud_scores')
    op.drop_index(op.f('ix_fraud_scores_transaction_id'), table_name='fraud_scores')
    op.drop_index(op.f('ix_fraud_scores_id'), table_name='fraud_scores')
    op.drop_table('fraud_scores')

    op.drop_index(op.f('ix_transactions_created_at'), table_name='transactions')
    op.drop_index(op.f('ix_transactions_status'), table_name='transactions')
    op.drop_index(op.f('ix_transactions_timestamp'), table_name='transactions')
    op.drop_index(op.f('ix_transactions_account_id'), table_name='transactions')
    op.drop_index(op.f('ix_transactions_receiver_id'), table_name='transactions')
    op.drop_index(op.f('ix_transactions_sender_id'), table_name='transactions')
    op.drop_index(op.f('ix_transactions_id'), table_name='transactions')
    op.drop_table('transactions')

    op.drop_index(op.f('ix_accounts_account_number'), table_name='accounts')
    op.drop_index(op.f('ix_accounts_user_id'), table_name='accounts')
    op.drop_index(op.f('ix_accounts_id'), table_name='accounts')
    op.drop_table('accounts')

    op.drop_index(op.f('ix_users_name'), table_name='users')
    op.drop_index(op.f('ix_users_id'), table_name='users')
    op.drop_table('users')
