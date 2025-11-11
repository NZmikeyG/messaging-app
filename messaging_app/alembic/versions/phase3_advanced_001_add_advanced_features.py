"""Add advanced features tables

Revision ID: phase3_advanced_001
Revises: phase2_admin_001
Create Date: 2025-11-11 13:07:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'phase3_advanced_001'
down_revision = 'phase2_admin_001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'two_factor_auth',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('is_enabled', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('secret', sa.String(32), nullable=True),
        sa.Column('backup_codes', sa.String(), nullable=True),
        sa.Column('enabled_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id')
    )
    op.create_index('ix_two_factor_auth_user_id', 'two_factor_auth', ['user_id'])

    op.create_table(
        'device_sessions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('device_name', sa.String(255), nullable=False),
        sa.Column('device_type', sa.String(50), nullable=False),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.String(500), nullable=True),
        sa.Column('last_active', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_device_sessions_user_id', 'device_sessions', ['user_id'])
    op.create_index('ix_device_sessions_is_active', 'device_sessions', ['is_active'])

    op.create_table(
        'message_encryption',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('message_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('encrypted_content', sa.Text(), nullable=False),
        sa.Column('encryption_key_id', sa.String(100), nullable=False),
        sa.Column('algorithm', sa.String(50), nullable=False, server_default='AES-256-GCM'),
        sa.Column('iv', sa.String(100), nullable=False),
        sa.Column('tag', sa.String(100), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['message_id'], ['messages.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('message_id')
    )
    op.create_index('ix_message_encryption_message_id', 'message_encryption', ['message_id'])

    op.create_table(
        'user_activity',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('action', sa.String(100), nullable=False),
        sa.Column('target_type', sa.String(50), nullable=False),
        sa.Column('target_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_user_activity_user_id', 'user_activity', ['user_id'])
    op.create_index('ix_user_activity_action', 'user_activity', ['action'])
    op.create_index('ix_user_activity_created_at', 'user_activity', ['created_at'])

    op.create_table(
        'security_audit_log',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('event_type', sa.String(100), nullable=False),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.String(500), nullable=True),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('reason', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_security_audit_log_user_id', 'security_audit_log', ['user_id'])
    op.create_index('ix_security_audit_log_event_type', 'security_audit_log', ['event_type'])
    op.create_index('ix_security_audit_log_created_at', 'security_audit_log', ['created_at'])

    op.create_table(
        'search_index',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('indexed_type', sa.String(50), nullable=False),
        sa.Column('indexed_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('keywords', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_search_index_indexed_type', 'search_index', ['indexed_type'])
    op.create_index('ix_search_index_indexed_id', 'search_index', ['indexed_id'])


def downgrade() -> None:
    op.drop_index('ix_search_index_indexed_id')
    op.drop_index('ix_search_index_indexed_type')
    op.drop_table('search_index')
    
    op.drop_index('ix_security_audit_log_created_at')
    op.drop_index('ix_security_audit_log_event_type')
    op.drop_index('ix_security_audit_log_user_id')
    op.drop_table('security_audit_log')
    
    op.drop_index('ix_user_activity_created_at')
    op.drop_index('ix_user_activity_action')
    op.drop_index('ix_user_activity_user_id')
    op.drop_table('user_activity')
    
    op.drop_index('ix_message_encryption_message_id')
    op.drop_table('message_encryption')
    
    op.drop_index('ix_device_sessions_is_active')
    op.drop_index('ix_device_sessions_user_id')
    op.drop_table('device_sessions')
    
    op.drop_index('ix_two_factor_auth_user_id')
    op.drop_table('two_factor_auth')
