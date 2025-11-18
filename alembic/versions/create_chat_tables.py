"""create chat tables

Revision ID: create_chat_tables
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = 'chat_001'
down_revision = 'dce8cb71ac3c'  # Latest notification system migration
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Create chat_rooms table
    op.create_table('chat_rooms',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('teacher_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('student_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, default=False),
        sa.ForeignKeyConstraint(['student_id'], ['students.id'], ),
        sa.ForeignKeyConstraint(['teacher_id'], ['teachers.id'], ),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for chat_rooms
    op.create_index('idx_chat_room_unique', 'chat_rooms', ['tenant_id', 'teacher_id', 'student_id'], unique=True)
    op.create_index(op.f('ix_chat_rooms_tenant_id'), 'chat_rooms', ['tenant_id'])
    op.create_index(op.f('ix_chat_rooms_teacher_id'), 'chat_rooms', ['teacher_id'])
    op.create_index(op.f('ix_chat_rooms_student_id'), 'chat_rooms', ['student_id'])
    
    # Create chat_messages table
    op.create_table('chat_messages',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('chat_room_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('sender_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('sender_type', sa.String(length=10), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('is_read', sa.Boolean(), nullable=False, default=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, default=False),
        sa.ForeignKeyConstraint(['chat_room_id'], ['chat_rooms.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for chat_messages
    op.create_index('idx_chat_message_room_time', 'chat_messages', ['chat_room_id', 'created_at'])
    op.create_index('idx_chat_message_unread', 'chat_messages', ['chat_room_id', 'is_read'])
    op.create_index(op.f('ix_chat_messages_chat_room_id'), 'chat_messages', ['chat_room_id'])
    op.create_index(op.f('ix_chat_messages_sender_id'), 'chat_messages', ['sender_id'])

def downgrade() -> None:
    # Drop chat_messages table and indexes
    op.drop_index(op.f('ix_chat_messages_sender_id'), table_name='chat_messages')
    op.drop_index(op.f('ix_chat_messages_chat_room_id'), table_name='chat_messages')
    op.drop_index('idx_chat_message_unread', table_name='chat_messages')
    op.drop_index('idx_chat_message_room_time', table_name='chat_messages')
    op.drop_table('chat_messages')
    
    # Drop chat_rooms table and indexes
    op.drop_index(op.f('ix_chat_rooms_student_id'), table_name='chat_rooms')
    op.drop_index(op.f('ix_chat_rooms_teacher_id'), table_name='chat_rooms')
    op.drop_index(op.f('ix_chat_rooms_tenant_id'), table_name='chat_rooms')
    op.drop_index('idx_chat_room_unique', table_name='chat_rooms')
    op.drop_table('chat_rooms')