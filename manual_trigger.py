import asyncio
from app.engine import AutomationEngine
from app.database import create_db_and_tables

async def main():
    print("Initializing Engine in Manual Mode...")
    engine = AutomationEngine(headless=False)
    # Task ID 1 is the default test task
    print("Running Task 1 directly...")
    await engine.run_task(1)
    print("Manual Trigger Complete.")

if __name__ == "__main__":
    asyncio.run(main())
