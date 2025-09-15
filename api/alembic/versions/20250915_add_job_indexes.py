"""
Add indexes on jobs table for performance

Revision ID: 20250915_add_job_indexes
Revises: 
Create Date: 2025-09-15
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20250915_add_job_indexes'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Create indexes if not exist (safe to run multiple times in most DBs)
    op.create_index('ix_jobs_status', 'jobs', ['status'], unique=False)
    op.create_index('ix_jobs_user_id', 'jobs', ['user_id'], unique=False)
    op.create_index('ix_jobs_created_at', 'jobs', ['created_at'], unique=False)
    op.create_index('ix_jobs_updated_at', 'jobs', ['updated_at'], unique=False)
    # Composite index for common listing by user and creation time
    op.create_index('ix_jobs_user_id_created_at', 'jobs', ['user_id', 'created_at'], unique=False)


def downgrade():
    op.drop_index('ix_jobs_user_id_created_at', table_name='jobs')
    op.drop_index('ix_jobs_updated_at', table_name='jobs')
    op.drop_index('ix_jobs_created_at', table_name='jobs')
    op.drop_index('ix_jobs_user_id', table_name='jobs')
    op.drop_index('ix_jobs_status', table_name='jobs')

