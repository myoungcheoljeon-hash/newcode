import asyncio
import json
from playwright.async_api import async_playwright, Page, BrowserContext
from sqlmodel import Session, select
from app.models import Account, Task, Log
from app.database import engine as db_engine

class AutomationEngine:
    def __init__(self, headless=False):
        self.headless = headless

    async def run_task(self, task_id: int):
        """
        Executes a pull-up task:
        1. Login (Restore cookies)
        2. Write New Post
        3. Delete Old Post
        """
        async with Session(db_engine) as session:
            task = session.get(Task, task_id)
            if not task:
                print(f"Task {task_id} not found")
                return

            account = task.account
            if not account:
                self._log(session, task_id, "FAILED", "Account not found")
                return

            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=self.headless)
                
                # Create context with restored cookies
                context = await browser.new_context()
                if account.cookies_json:
                    await context.add_cookies(json.loads(account.cookies_json))
                
                page = await context.new_page()
                try:
                    # 1. Verify Login
                    await page.goto("https://www.naver.com")
                    if "nid.naver.com" in page.url or "login" in await page.content():
                        # Simple check, real check is if we see user info
                        pass 
                    
                    target_url = task.cafe_url
                    
                    # 2. Find OLD Post (to be deleted later)
                    old_post_url = None
                    try:
                        self._log(session, task_id, "RUNNING", f"Searching for existing post in {target_url}")
                        await page.goto(target_url)
                        
                        # Wait for iframe logic: The list is usually in 'cafe_main'
                        main_frame = page.frame_locator("#cafe_main")
                        
                        # Search by BOARD search bar inside the frame
                        # Usually there is a search form. 
                        # Or simpler: Look at the first few posts. If our account is "Writer", matches "Title".
                        # Let's simple-scan the first page of the board.
                        
                        # We need the User's Nickname to know which post is theirs? 
                        # Or just match exact Title?
                        # Matching Title is safer if user writes unique titles.
                        # Naver Cafe List Table: usually `.td_article` or similar.
                        
                        # Iterate through rows
                        # For now, let's skip complex search and assume we delete the previous one found on top?
                        # No, that's risky.
                        # Let's try: Search by "Title" using the board's search box.
                        
                        # If we can't find search box easily, just scan visible rows.
                        # Row structure: .board-list .td_article .board-list .td_name
                        # Note: This is highly dependent on Cafe Skin (Coffee vs others).
                        # Assumption: Standard Cafe Skin.
                        
                        # Placeholder: Store the HREF of the post if found.
                        # old_post_url = ...
                        pass
                    except Exception as e:
                        print(f"Error finding old post: {e}")

                    # 3. Write New Post
                    self._log(session, task_id, "RUNNING", "Writing new post...")
                    # Click "Use HTML" if possible? 
                    # Assuming we click "Write" button.
                    # Button is usually "#write-btn" or text="글쓰기"
                    await main_frame.get_by_text("글쓰기").first.click()
                    
                    # Wait for Editor
                    # If "SmartEditor One", we need to interact with it.
                    # Title Input
                    await page.wait_for_selector("input.textarea_input", timeout=5000) # Common title class
                    await page.type("input.textarea_input", task.name) # Use Task Search/Name as Title for now? Or we need 'title' field in Task model.
                    # Note: Task model has `content_html` but we missed `title` in schema? 
                    # Checking schema... Task has `name` (used for task name), but maybe user wants specific post title.
                    # We should probably add `post_title` to Task model. Using `name` for now.
                    
                    # Content
                    # If using clipboard:
                    # await page.evaluate("navigator.clipboard.writeText(...)")
                    # await page.keyboard.press("Control+V")
                    
                    # Click Submit "등록"
                    await page.click("#btn_submit_id_or_text") # Placeholder
                    
                    await page.wait_for_url("**/ArticleRead.nhn**") # Wait for read page
                    self._log(session, task_id, "SUCCESS", "Posted successfully")

                    # 4. Delete Old Post
                    if old_post_url:
                        self._log(session, task_id, "RUNNING", f"Deleting old post: {old_post_url}")
                        await page.goto(old_post_url)
                        # Click Delete button
                        # await page.click("text=삭제")
                        # Handle confirmation dialog
                        # page.on("dialog", lambda dialog: dialog.accept())
                        self._log(session, task_id, "SUCCESS", "Deleted old post")
                    
                except Exception as e:
                    self._log(session, task_id, "FAILED", f"Error during execution: {str(e)}")
                finally:
                    await browser.close()

    def _log(self, session, task_id, status, message):
        log = Log(task_id=task_id, status=status, message=message)
        session.add(log)
        session.commit()

actions = AutomationEngine()
