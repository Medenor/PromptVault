# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""add_authentication_fields_to_users

Revision ID: da013146c222
Revises: 7182f1f03364
Create Date: 2025-12-02 17:18:18.377157

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'da013146c222'
down_revision: Union[str, Sequence[str], None] = '7182f1f03364'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    dialect = bind.dialect.name

    # Create password_reset_tokens table if it doesn't exist
    inspector = sa.inspect(bind)

    if 'password_reset_tokens' not in inspector.get_table_names():
        op.create_table('password_reset_tokens',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('token', sa.String(length=255), nullable=False),
        sa.Column('is_used', sa.Boolean(), server_default=sa.false(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_password_reset_tokens_user_id_users'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_password_reset_tokens'))
            )
        op.create_index(op.f('ix_password_reset_tokens_expires_at'), 'password_reset_tokens', ['expires_at'], unique=False)
        op.create_index(op.f('ix_password_reset_tokens_is_used'), 'password_reset_tokens', ['is_used'], unique=False)
        op.create_index(op.f('ix_password_reset_tokens_token'), 'password_reset_tokens', ['token'], unique=True)
        op.create_index(op.f('ix_password_reset_tokens_user_id'), 'password_reset_tokens', ['user_id'], unique=False)
        op.create_index('ix_password_reset_tokens_user_used', 'password_reset_tokens', ['user_id', 'is_used'], unique=False)

    if 'user_sessions' not in inspector.get_table_names():
        op.create_table('user_sessions',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('family_id', sa.String(length=36), nullable=False),
        sa.Column('refresh_token_jti', sa.String(length=36), nullable=False),
        sa.Column('device_info', sa.String(length=500), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('is_revoked', sa.Boolean(), server_default=sa.false(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
        sa.Column('last_used_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_user_sessions_user_id_users'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_user_sessions'))
            )
        op.create_index(op.f('ix_user_sessions_expires_at'), 'user_sessions', ['expires_at'], unique=False)
        op.create_index(op.f('ix_user_sessions_family_id'), 'user_sessions', ['family_id'], unique=True)
        op.create_index(op.f('ix_user_sessions_is_revoked'), 'user_sessions', ['is_revoked'], unique=False)
        op.create_index(op.f('ix_user_sessions_refresh_token_jti'), 'user_sessions', ['refresh_token_jti'], unique=True)
        op.create_index('ix_user_sessions_user_active', 'user_sessions', ['user_id', 'is_revoked'], unique=False)
        op.create_index(op.f('ix_user_sessions_user_id'), 'user_sessions', ['user_id'], unique=False)

    # Handle constraint drop for prompt_versions (PostgreSQL only — these
    # tables/constraints only exist on pre-existing Postgres deployments at
    # this point in the chain; a fresh SQLite install has neither yet).
    if dialect != 'sqlite':
        # Drop dependent foreign key constraints first
        op.execute('ALTER TABLE prompt_versions DROP CONSTRAINT IF EXISTS fk_prompt_versions_parent_version_id_prompt_versions CASCADE')
        op.execute('ALTER TABLE prompt_branches DROP CONSTRAINT IF EXISTS fk_prompt_branches_current_version_id_prompt_versions CASCADE')
        # Now drop the unique constraint and create index instead
        op.execute('ALTER TABLE prompt_versions DROP CONSTRAINT IF EXISTS uq_version_id CASCADE')
        op.execute('CREATE UNIQUE INDEX IF NOT EXISTS ix_prompt_versions_version_id ON prompt_versions(version_id)   ')

    # Update existing NULL emails before making email NOT NULL
    # Set a placeholder email for system/service accounts
    op.execute(
        """
        UPDATE users
        SET email = username || '@system.local'
        WHERE email IS NULL OR email = ''
        """
    )

    if dialect == 'sqlite':
        with op.batch_alter_table('users') as batch_op:
            batch_op.add_column(sa.Column('password_hash', sa.String(length=255), nullable=True))
            batch_op.add_column(sa.Column('email_verified', sa.Boolean(), server_default=sa.false(), nullable=True))
            batch_op.add_column(sa.Column('is_active', sa.Boolean(), server_default=sa.true(), nullable=True))
            batch_op.add_column(sa.Column('last_login', sa.DateTime(timezone=True), nullable=True))
            batch_op.add_column(sa.Column('failed_login_attempts', sa.Integer(), server_default='0', nullable=True))
            batch_op.add_column(sa.Column('locked_until', sa.DateTime(timezone=True), nullable=True))
            batch_op.add_column(sa.Column('password_changed_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True))
            batch_op.add_column(sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True))
            batch_op.alter_column('email', existing_type=sa.String(length=255), nullable=False)

        op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
        op.create_index(op.f('ix_users_is_active'), 'users', ['is_active'], unique=False)
        op.create_index(op.f('ix_users_email_verified'), 'users', ['email_verified'], unique=False)
    else:
        # Add authentication fields to users table using raw SQL for PostgreSQL
        op.execute('ALTER TABLE users ADD COLUMN IF NOT EXISTS password_hash VARCHAR(255)')
        op.execute('ALTER TABLE users ADD COLUMN IF NOT EXISTS email_verified BOOLEAN DEFAULT false')
        op.execute('ALTER TABLE users ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT true')
        op.execute('ALTER TABLE users ADD COLUMN IF NOT EXISTS last_login TIMESTAMP WITH TIME ZONE')
        op.execute('ALTER TABLE users ADD COLUMN IF NOT EXISTS failed_login_attempts INTEGER DEFAULT 0')
        op.execute('ALTER TABLE users ADD COLUMN IF NOT EXISTS locked_until TIMESTAMP WITH TIME ZONE')
        op.execute('ALTER TABLE users ADD COLUMN IF NOT EXISTS password_changed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP')
        op.execute('ALTER TABLE users ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP')

        # Alter email column to be not nullable and add indexes
        op.execute('ALTER TABLE users ALTER COLUMN email SET NOT NULL')
        op.execute('CREATE UNIQUE INDEX IF NOT EXISTS ix_users_email ON users(email)')
        op.execute('CREATE INDEX IF NOT EXISTS ix_users_is_active ON users(is_active)')
        op.execute('CREATE INDEX IF NOT EXISTS ix_users_email_verified ON users(email_verified)')


def downgrade() -> None:
    """Downgrade schema."""
    dialect = op.get_bind().dialect.name

    if dialect == 'sqlite':
        op.drop_index(op.f('ix_users_email_verified'), table_name='users')
        op.drop_index(op.f('ix_users_is_active'), table_name='users')
        op.drop_index(op.f('ix_users_email'), table_name='users')

        with op.batch_alter_table('users') as batch_op:
            batch_op.alter_column('email', existing_type=sa.String(length=255), nullable=True)
            batch_op.drop_column('updated_at')
            batch_op.drop_column('password_changed_at')
            batch_op.drop_column('locked_until')
            batch_op.drop_column('failed_login_attempts')
            batch_op.drop_column('last_login')
            batch_op.drop_column('is_active')
            batch_op.drop_column('email_verified')
            batch_op.drop_column('password_hash')
    else:
        # Drop authentication fields from users table using raw SQL
        op.execute('ALTER TABLE users DROP INDEX IF EXISTS ix_users_email_verified')
        op.execute('ALTER TABLE users DROP INDEX IF EXISTS ix_users_is_active')
        op.execute('ALTER TABLE users DROP INDEX IF EXISTS ix_users_email')

        op.execute('ALTER TABLE users ALTER COLUMN email DROP NOT NULL')

        op.execute('ALTER TABLE users DROP COLUMN IF EXISTS updated_at')
        op.execute('ALTER TABLE users DROP COLUMN IF EXISTS password_changed_at')
        op.execute('ALTER TABLE users DROP COLUMN IF EXISTS locked_until')
        op.execute('ALTER TABLE users DROP COLUMN IF EXISTS failed_login_attempts')
        op.execute('ALTER TABLE users DROP COLUMN IF EXISTS last_login')
        op.execute('ALTER TABLE users DROP COLUMN IF EXISTS is_active')
        op.execute('ALTER TABLE users DROP COLUMN IF EXISTS email_verified')
        op.execute('ALTER TABLE users DROP COLUMN IF EXISTS password_hash')

        # Handle constraint recreation for prompt_versions
        op.execute('ALTER TABLE prompt_versions DROP CONSTRAINT IF EXISTS fk_prompt_versions_parent_version_id_prompt_versions CASCADE')
        op.execute('ALTER TABLE prompt_branches DROP CONSTRAINT IF EXISTS fk_prompt_branches_current_version_id_prompt_versions CASCADE')
        op.execute('DROP INDEX IF EXISTS ix_prompt_versions_version_id CASCADE')
        op.execute('ALTER TABLE prompt_versions ADD CONSTRAINT uq_version_id UNIQUE (version_id)')

    op.drop_index(op.f('ix_user_sessions_user_id'), table_name='user_sessions')
    op.drop_index('ix_user_sessions_user_active', table_name='user_sessions')
    op.drop_index(op.f('ix_user_sessions_refresh_token_jti'), table_name='user_sessions')
    op.drop_index(op.f('ix_user_sessions_is_revoked'), table_name='user_sessions')
    op.drop_index(op.f('ix_user_sessions_family_id'), table_name='user_sessions')
    op.drop_index(op.f('ix_user_sessions_expires_at'), table_name='user_sessions')
    op.drop_table('user_sessions')
    op.drop_index('ix_password_reset_tokens_user_used', table_name='password_reset_tokens')
    op.drop_index(op.f('ix_password_reset_tokens_user_id'), table_name='password_reset_tokens')
    op.drop_index(op.f('ix_password_reset_tokens_token'), table_name='password_reset_tokens')
    op.drop_index(op.f('ix_password_reset_tokens_is_used'), table_name='password_reset_tokens')
    op.drop_index(op.f('ix_password_reset_tokens_expires_at'), table_name='password_reset_tokens')
    op.drop_table('password_reset_tokens')
