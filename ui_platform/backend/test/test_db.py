import sqlalchemy
from sqlalchemy import create_engine, text

# Update with your actual credentials
DB_URL = "postgresql://johnsmith:welcome1@localhost:5432/context_platform"

def check_postgres_health():
    engine = create_engine(DB_URL)
    
    print("--- 1. Testing Connection ---")
    try:
        with engine.connect() as conn:
            # Check version
            version = conn.execute(text("SELECT version();")).fetchone()
            print(f"Connected to: {version[0]}")
            
            print("\n--- 2. Checking PL/pgSQL Extension ---")
            # Check if plpgsql is installed and what its load path is
            ext_info = conn.execute(text("""
                SELECT extname, extversion 
                FROM pg_extension 
                WHERE extname = 'plpgsql';
            """)).fetchone()
            
            if ext_info:
                print(f"Extension '{ext_info[0]}' found (Version: {ext_info[1]})")
            else:
                print("Extension 'plpgsql' is NOT registered in this database.")

            print("\n--- 3. Testing Procedural Execution ---")
            # This forces the engine to load the .dylib file
            test_fn = conn.execute(text("""
                DO $$ 
                BEGIN 
                    RAISE NOTICE 'Procedural logic is working!'; 
                END $$;
            """))
            print("Success! The .dylib file was loaded and executed correctly.")

    except sqlalchemy.exc.OperationalError as e:
        if "plpgsql" in str(e):
            print("\n[CRITICAL] Still cannot find plpgsql.dylib.")
            print("The server is running, but the library file is missing or pathing is wrong.")
        else:
            print(f"\nConnection Error: {e}")
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")

if __name__ == "__main__":
    check_postgres_health()
