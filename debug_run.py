import asyncio
from sqlmodel import Session, select, create_engine
from app.models import Account, Task
from app.engine import AutomationEngine

# Setup DB
engine = create_engine('sqlite:///database.db')

async def main():
    print("--- DEBUG RUN START ---")
    
    with Session(engine) as session:
        # 1. Get Default Account (ID 1)
        account = session.get(Account, 1)
        if not account:
            print("ERROR: Account ID 1 not found!")
            return

        print(f"Checking Account: {account.nickname} ({account.naver_id})")
        
        # 2. Verify Session
        auto_engine = AutomationEngine(headless=True)
        print("Verifying Login Session...")
        is_valid = await auto_engine.verify_session(account)
        
        if is_valid:
            print("✅ Session is VALID. Logged in.")
        else:
            print("❌ Session is INVALID or Logged Out.")
            print("Please fallback to 'Connect Account' in the dashboard.")
            # For debugging, we might want to try running anyway to see the screenshot?
            # But the user asked to find errors.
            return

        # 3. Run Task
        task = session.exec(select(Task).where(Task.account_id == account.id)).first()
        if not task:
            print("ERROR: No task found for this account.")
            return

        print(f"Running Task: {task.name} (Board: {task.board_name})")
        
        # Run in HEADED mode so user can see
        auto_engine.headless = False 
        await auto_engine.run_task(task.id)
        print("--- DEBUG RUN COMPLETE ---")

if __name__ == "__main__":
    asyncio.run(main())
