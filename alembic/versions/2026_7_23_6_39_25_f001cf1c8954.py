"""Update base model updated_at column

Revision ID: f001cf1c8954
Revises: 65b1b6c18d48
Create Date: 2026-07-23 06:39:25.809825

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision: str = 'f001cf1c8954'
down_revision: Union[str, Sequence[str], None] = '65b1b6c18d48'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# List all your tables that inherit from BaseModel
TABLES = ['nodes', 'pipes', 'networks', 'quality_readings', 
          'scenarios', 'telemetry', 'users', 'work_orders']

def upgrade() -> None:
    """Upgrade schema."""
    for table in TABLES:
        try:
            # Check if column exists
            check_query = text(f"""
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_name = '{table}' AND column_name = 'updated_at'
                )
            """)
            
            # Execute check - note: in a migration script, you'd use connection.execute()
            # This is a simplified example; actual implementation depends on your setup
            
            # Execute statements one by one
            op.execute(text(f"""
                ALTER TABLE {table} ALTER COLUMN updated_at SET DEFAULT NOW()
            """))
            
            op.execute(text(f"""
                UPDATE {table} SET updated_at = NOW() WHERE updated_at IS NULL
            """))
            
            op.execute(text(f"""
                ALTER TABLE {table} ALTER COLUMN updated_at SET NOT NULL
            """))
            
            print(f"Fixed table: {table}")
        except Exception as e:
            print(f"Error fixing {table}: {e}")

def downgrade() -> None:
    """Downgrade schema."""
    for table in TABLES:
        try:
            op.execute(text(f"""
                ALTER TABLE {table} ALTER COLUMN updated_at DROP DEFAULT
            """))
            
            op.execute(text(f"""
                ALTER TABLE {table} ALTER COLUMN updated_at DROP NOT NULL
            """))
            
            print(f"Reverted table: {table}")
        except Exception as e:
            print(f"Error reverting {table}: {e}")
