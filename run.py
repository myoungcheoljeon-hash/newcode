import sys
import asyncio
import uvicorn

if __name__ == "__main__":
    # Force ProactorEventLoop on Windows for Playwright compatibility
    if sys.platform.startswith("win"):
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    # Run Uvicorn
    # We import 'main:app' string style to allow reloading if needed, 
    # but for reliability let's just run it directly or use factory if possible.
    # To use reload, we must pass string, but policy must be set in the subprocess too.
    # Uvicorn with reload spawns subprocesses that might NOT inherit this policy if not careful.
    # Let's try running WITHOUT reload first to confirm it works.
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=False)
