"""add database indexes for query optimization

Revision ID: add_indexes_001
Revises: [previous_migration_id]
Create Date: 2025-11-10 21:40:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_indexes_001'
down_revision = None  # Replace with actual previous revision
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add indexes for better query performance
    op.create_index('ix_users_created_at', 'users', ['created_at'])
    op.create_index('ix_messages_channel_id', 'messages', ['channel_id'])
    op.create_index('ix_messages_user_id', 'messages', ['user_id'])
    op.create_index('ix_messages_created_at', 'messages', ['created_at'])
    op.create_index('ix_direct_messages_sender_id', 'direct_messages', ['sender_id'])
    op.create_index('ix_direct_messages_receiver_id', 'direct_messages', ['receiver_id'])
    op.create_index('ix_direct_messages_created_at', 'direct_messages', ['created_at'])
    op.create_index('ix_channels_created_at', 'channels', ['created_at'])


def downgrade() -> None:
    op.drop_index('ix_channels_created_at')
    op.drop_index('ix_direct_messages_created_at')
    op.drop_index('ix_direct_messages_receiver_id')
    op.drop_index('ix_direct_messages_sender_id')
    op.drop_index('ix_messages_created_at')
    op.drop_index('ix_messages_user_id')
    op.drop_index('ix_messages_channel_id')
    op.drop_index('ix_users_created_at')
