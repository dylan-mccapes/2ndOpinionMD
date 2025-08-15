"""make_user_fields_optional

Revision ID: 755e5f98fff6
Revises: 001
Create Date: 2025-08-15 21:35:14.694167

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '755e5f98fff6'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("users", "full_name", nullable=True)
    op.alter_column("users", "birthdate", nullable=True)
    op.alter_column("users", "last_login", nullable=True)
    op.alter_column("users", "verification_token", nullable=True)
    op.alter_column("users", "verification_token_expires", nullable=True)
    op.alter_column("users", "password_reset_token", nullable=True)
    op.alter_column("users", "password_reset_token_expires", nullable=True)
    op.alter_column("users", "locked_until", nullable=True)

    op.alter_column("users", "subscription_tier", server_default="free", existing_nullable=False)
    op.alter_column("users", "failed_login_attempts", server_default="0", existing_nullable=False)
    op.alter_column("users", "is_verified", server_default="false", existing_nullable=False)


def downgrade() -> None:
    op.alter_column("users", "subscription_tier", server_default=None, existing_nullable=False)
    op.alter_column("users", "failed_login_attempts", server_default=None, existing_nullable=False)
    op.alter_column("users", "is_verified", server_default=None, existing_nullable=False)
    
    op.alter_column("users", "full_name", nullable=False)
    op.alter_column("users", "birthdate", nullable=False)
    op.alter_column("users", "last_login", nullable=False)
    op.alter_column("users", "verification_token", nullable=False)
    op.alter_column("users", "verification_token_expires", nullable=False)
    op.alter_column("users", "password_reset_token", nullable=False)
    op.alter_column("users", "password_reset_token_expires", nullable=False)
    op.alter_column("users", "locked_until", nullable=False)
