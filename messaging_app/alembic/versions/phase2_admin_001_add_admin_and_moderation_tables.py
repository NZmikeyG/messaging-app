"""Add admin and moderation tables

Revision ID: phase2_admin_001
Revises: ad941b9e5a53
Create Date: 2025-11-11 12:45:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'phase2_admin_001'
down_revision = 'ad941b9e5a53'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create user_roles table
    op.create_table(
        'user_roles',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('role', sa.String(20), nullable=False, server_default='member'),
        sa.Column('assigned_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('assigned_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['assigned_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id')
    )
    op.create_index('ix_user_roles_user_id', 'user_roles', ['user_id'])
    op.create_index('ix_user_roles_role', 'user_roles', ['role'])

    # Create channel_roles table
    op.create_table(
        'channel_roles',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('channel_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('role', sa.String(20), nullable=False, server_default='member'),
        sa.Column('assigned_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['channel_id'], ['channels.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_channel_roles_channel_id', 'channel_roles', ['channel_id'])
    op.create_index('ix_channel_roles_user_id', 'channel_roles', ['user_id'])

    # Create flagged_content table
    op.create_table(
        'flagged_content',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('message_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('reported_by', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('reason', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('reviewed_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(), nullable=True),
        sa.Column('action_taken', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['message_id'], ['messages.id'], ),
        sa.ForeignKeyConstraint(['reported_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['reviewed_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_flagged_content_message_id', 'flagged_content', ['message_id'])
    op.create_index('ix_flagged_content_status', 'flagged_content', ['status'])
    op.create_index('ix_flagged_content_created_at', 'flagged_content', ['created_at'])

    # Create user_suspensions table
    op.create_table(
        'user_suspensions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('suspended_by', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('suspended_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('suspended_until', sa.DateTime(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['suspended_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id')
    )
    op.create_index('ix_user_suspensions_user_id', 'user_suspensions', ['user_id'])
    op.create_index('ix_user_suspensions_is_active', 'user_suspensions', ['is_active'])

    # Create admin_actions table
    op.create_table(
        'admin_actions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('admin_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('action_type', sa.String(50), nullable=False),
        sa.Column('target_type', sa.String(50), nullable=False),
        sa.Column('target_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('details', sa.String(500), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['admin_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_admin_actions_admin_id', 'admin_actions', ['admin_id'])
    op.create_index('ix_admin_actions_action_type', 'admin_actions', ['action_type'])
    op.create_index('ix_admin_actions_created_at', 'admin_actions', ['created_at'])


def downgrade() -> None:
    op.drop_index('ix_admin_actions_created_at')
    op.drop_index('ix_admin_actions_action_type')
    op.drop_index('ix_admin_actions_admin_id')
    op.drop_table('admin_actions')
    
    op.drop_index('ix_user_suspensions_is_active')
    op.drop_index('ix_user_suspensions_user_id')
    op.drop_table('user_suspensions')
    
    op.drop_index('ix_flagged_content_created_at')
    op.drop_index('ix_flagged_content_status')
    op.drop_index('ix_flagged_content_message_id')
    op.drop_table('flagged_content')
    
    op.drop_index('ix_channel_roles_user_id')
    op.drop_index('ix_channel_roles_channel_id')
    op.drop_table('channel_roles')
    
    op.drop_index('ix_user_roles_role')
    op.drop_index('ix_user_roles_user_id')
    op.drop_table('user_roles')
