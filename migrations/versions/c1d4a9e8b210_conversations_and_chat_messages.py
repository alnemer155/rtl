"""conversations and chat messages

Revision ID: c1d4a9e8b210
Revises: 0aadba10d73e
Create Date: 2026-09-11
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = 'c1d4a9e8b210'
down_revision: str | None = '0aadba10d73e'
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.create_table('conversations',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('title', sa.String(length=300), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('chat_messages',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('conversation_id', sa.String(length=36), nullable=False),
    sa.Column('role', sa.String(length=12), nullable=False),
    sa.Column('content', sa.Text(), nullable=False),
    sa.Column('citations_json', sa.JSON(), nullable=False),
    sa.Column('route_json', sa.JSON(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['conversation_id'], ['conversations.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('chat_messages', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_chat_messages_conversation_id'), ['conversation_id'], unique=False)


def downgrade() -> None:
    with op.batch_alter_table('chat_messages', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_chat_messages_conversation_id'))

    op.drop_table('chat_messages')
    op.drop_table('conversations')
