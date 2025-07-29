"""Initial migration

Revision ID: 001
Revises: 
Create Date: 2025-07-16

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # op.execute('CREATE EXTENSION IF NOT EXISTS vector')
    
    op.create_table('users',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('full_name', sa.String(), nullable=False),
        sa.Column('hashed_password', sa.String(), nullable=False),
        sa.Column('birthdate', sa.DateTime(), nullable=True),
        sa.Column('subscription_tier', sa.String(), server_default='basic', nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.Column('last_login', sa.DateTime(), nullable=True),
        sa.Column('is_verified', sa.Boolean(), server_default='false', nullable=True),
        sa.Column('verification_token', sa.String(), nullable=True),
        sa.Column('verification_token_expires', sa.DateTime(), nullable=True),
        sa.Column('failed_login_attempts', sa.Integer(), server_default='0', nullable=True),
        sa.Column('locked_until', sa.DateTime(), nullable=True),
        sa.Column('password_reset_token', sa.String(), nullable=True),
        sa.Column('password_reset_token_expires', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    
    op.create_table('journal_entries',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('date', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.Column('symptoms', sa.JSON(), nullable=True),
        sa.Column('environmental_factors', sa.JSON(), nullable=True),
        sa.Column('stress_level', sa.Integer(), nullable=True),
        sa.Column('diet_notes', sa.Text(), nullable=True),
        sa.Column('sleep_quality', sa.Integer(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('analysis', sa.Text(), nullable=True),
        sa.Column('pattern_observations', sa.Text(), nullable=True),
        sa.Column('ai_analysis', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    op.create_table('medical_knowledge',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('content_type', sa.String(), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('icd10_code', sa.String(), nullable=True),
        sa.Column('meta_data', sa.JSON(), nullable=True),
        sa.Column('embedding', Vector(1536), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    op.execute(
        'CREATE INDEX medical_knowledge_embedding_idx ON medical_knowledge USING ivfflat (embedding vector_l2_ops) WITH (lists = 100)'
    )


def downgrade() -> None:
    op.drop_table('medical_knowledge')
    op.drop_table('journal_entries')
    op.drop_table('users')
