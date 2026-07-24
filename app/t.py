# Create a standalone script fix_updated_at.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
import asyncio
from sqlalchemy import text
from app.core.database import AsyncSessionLocal

async def fix_updated_at():
    async with AsyncSessionLocal() as session:
        # Get all tables from your metadata
        from app.models.base import BaseModel
        
        for table in BaseModel.metadata.tables.keys():
            try:
                # Add default and update null values
                await session.execute(text(f"""
                    ALTER TABLE {table} ALTER COLUMN updated_at SET DEFAULT NOW();
                    UPDATE {table} SET updated_at = NOW() WHERE updated_at IS NULL;
                    ALTER TABLE {table} ALTER COLUMN updated_at SET NOT NULL;
                """))
                print(f"Fixed table: {table}")
            except Exception as e:
                print(f"Error fixing {table}: {e}")
        
        await session.commit()

if __name__ == "__main__":
    asyncio.run(fix_updated_at())