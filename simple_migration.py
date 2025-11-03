import asyncio
import asyncpg

async def make_columns_nullable():
    conn = await asyncpg.connect(
        host="localhost",
        port=5432,
        user="postgres", 
        password="postgres",
        database="edu_backend"
    )
    
    try:
        # Make date_of_birth nullable
        await conn.execute("ALTER TABLE school_authorities ALTER COLUMN date_of_birth DROP NOT NULL;")
        print("✓ Made date_of_birth nullable")
        
        # Make address nullable  
        await conn.execute("ALTER TABLE school_authorities ALTER COLUMN address DROP NOT NULL;")
        print("✓ Made address nullable")
        
        # Make joining_date nullable
        await conn.execute("ALTER TABLE school_authorities ALTER COLUMN joining_date DROP NOT NULL;")
        print("✓ Made joining_date nullable")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(make_columns_nullable())