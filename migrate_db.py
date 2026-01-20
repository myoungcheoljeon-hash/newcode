import sqlite3
import os

db_path = "database.db"

if os.path.exists(db_path):
    print(f"Migrating {db_path}...")
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    try:
        # Check if column exists
        cur.execute("SELECT title FROM task LIMIT 1")
    except:
        # Column likely missing, add it
        try:
            cur.execute("ALTER TABLE task ADD COLUMN title VARCHAR")
            print("Added 'title' column to 'task' table.")
        except Exception as e:
            print(f"Migration error: {e}")
    finally:
        con.commit()
        con.close()
        print("Migration complete.")
else:
    print("No database found to migrate.")
