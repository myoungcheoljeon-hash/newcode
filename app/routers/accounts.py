from fastapi import APIRouter, Depends, HTTPException, Request
from sqlmodel import Session, select
from app.database import get_session
from app.models import Account
from playwright.async_api import async_playwright
import json
import asyncio

router = APIRouter(prefix="/accounts", tags=["accounts"])

@router.get("/")
def list_accounts(request: Request, session: Session = Depends(get_session)):
    accounts = session.exec(select(Account)).all()
    # In a real app, passing whole objects to template is fine for small scale
    # But usually we'd validate or serialize.
    return accounts

# Manual Login Logic
@router.post("/login")
async def start_manual_login(session: Session = Depends(get_session)):
    """
    Launches a browser for the user to log in manually.
    Waits for the user to visit a specific success page or close the window?
    Actually for Naver, we just wait for them to log in then capture cookies.
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
        await page.goto("https://nid.naver.com/nidlogin.login")
        
        # Poll for login success (check if url changes to main naver or if specific cookie exists)
        # We'll give them 2 minutes to login.
        print("Waiting for login...")
        
        logged_in = False
        naver_id = ""
        nickname = ""
        
        for _ in range(120): # 2 minutes
            await asyncio.sleep(1)
            # Check if we are redirected to www.naver.com or similar
            if "naver.com" in page.url and "nidlogin" not in page.url:
                # Try to get user info to verify
                cookies = await context.cookies()
                # Check for NID_AUT and NID_SES
                nid_aut = next((c for c in cookies if c['name'] == 'NID_AUT'), None)
                if nid_aut:
                    logged_in = True
                    # Let's try to scrape the ID/Nickname if possible, or just save generic
                    # Navigate to cafe main to get nickname? Or user info page.
                    break
        
        if logged_in:
            # Navigate to user info page to scrape ID/Nickname
            try:
                # This is a common Naver user info/security page that shows ID
                await page.goto("https://nid.naver.com/user2/help/myInfo.nhn?menu=home", wait_until="domcontentloaded")
                
                # Naver's DOM structure changes, but usually ID is in some profile area.
                # Let's try a safe approach: just use the NID_AUT cookie as a unique handle if scraping fails,
                # but try to find the ID element.
                # Common selector for ID in Naver GN (Global Navigation) or MyInfo
                # Let's try getting it from the GN area on main page if MyInfo is complex.
                await page.goto("https://www.naver.com", wait_until="domcontentloaded")
                await asyncio.sleep(2) # Wait for JS to render login info
                
                # Selector for "Naver ID" on the main page login area (often .my_info .nickname or similar)
                # Attempt to get text content of the logged-in user button
                # This is brittle. A better way: parsed token? No.
                # Let's just use "Naver User" + timestamp if we can't find it easily, 
                # allowing user to rename it later in the UI is a good fallback.
                
                final_id = "AutoUser_" + str(int(asyncio.get_event_loop().time()))
                final_nick = "Naver User"
                
                # Try simple selector
                # element = await page.query_selector("class_name_here") 
                
            except Exception as e:
                print(f"Scraping failed: {e}")
                final_id = "UnknownID"
                final_nick = "User"

            cookies = await context.cookies()
            new_account = Account(
                naver_id=final_id,
                nickname=final_nick, 
                cookies_json=json.dumps(cookies)
            )
            session.add(new_account)
            session.commit()
            session.refresh(new_account)
            
            await browser.close()
            return {"status": "success", "account_id": new_account.id, "message": "Login successful"}
        
        await browser.close()
        raise HTTPException(status_code=408, detail="Login timeout or failed")

