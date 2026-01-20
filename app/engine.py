import asyncio
import json
import re
from playwright.async_api import async_playwright, Page, BrowserContext
from sqlmodel import Session, select
from app.models import Account, Task, Log
from app.database import engine as db_engine
from app.config import settings  # 파일 상단으로 이동

class AutomationEngine:
    def __init__(self, headless=False):
        self.headless = headless
        self.playwright = None
        self.browser = None  # CDP 연결 시 사용
        self.context = None

    async def get_browser_context(self):
        """
        브라우저 컨텍스트 가져오기
        1. 기존 컨텍스트가 있으면 재사용
        2. CDP로 기존 크롬 브라우저에 연결 시도
        3. 실패 시 새 브라우저 창 생성
        """
        if self.context:
            try:
                # 기존 컨텍스트가 유효한지 확인
                _ = self.context.pages 
                return self.context
            except Exception:
                print("Context deemed disconnected, restarting...")
                self.browser = None
                self.context = None

        # 1단계: CDP로 기존 크롬 브라우저에 연결 시도
        cdp_port = settings.CHROME_CDP_PORT
        print(f"[DEBUG] CDP Port from settings: '{cdp_port}'")
        
        # CDP 포트가 설정되지 않았으면 건너뛰기
        if cdp_port and cdp_port.strip():
            cdp_url = f"http://localhost:{cdp_port}"
            
            try:
                print(f"🔗 Attempting to connect to existing Chrome via CDP: {cdp_url}")
                self.playwright = await async_playwright().start()
                
                # CDP 엔드포인트로 연결
                self.browser = await self.playwright.chromium.connect_over_cdp(cdp_url)
                
                # 기본 컨텍스트 가져오기 (CDP는 항상 기본 컨텍스트가 있음)
                if self.browser.contexts:
                    self.context = self.browser.contexts[0]
                else:
                    # 만약 컨텍스트가 없다면 에러 발생 (CDP에서는 거의 없는 경우)
                    raise Exception("No default context found in CDP browser")
                
                print("✅ Successfully connected to existing Chrome browser!")
                print(f"📑 Current tabs: {len(self.context.pages)}")
                return self.context
                
            except Exception as e:
                print(f"⚠️ CDP connection failed: {e}")
                print("📌 Falling back to launching new browser window...")
        else:
            print("ℹ️ CDP port not configured, using default browser launch mode...")
            
        # 2단계: CDP 비활성화 또는 실패 시 기존 방식(새 창) 사용
        import os
        user_data_dir = os.path.abspath("./user_data")
        
        print(f"[DEBUG] Starting playwright...")
        self.playwright = await async_playwright().start()
        print(f"[DEBUG] Playwright started successfully")
        
        print(f"🚀 Launching persistent context: {user_data_dir}")
        self.context = await self.playwright.chromium.launch_persistent_context(
            user_data_dir,
            headless=self.headless,
            # channel="chrome", # REMOVED: Causing crashes on some systems
            args=[
                "--disable-web-security",
                "--no-sandbox",
                "--disable-blink-features=AutomationControlled"
            ],
            viewport={"width": 1280, "height": 800}
        )
        print(f"[DEBUG] Browser context created successfully")
        return self.context

    async def open_dashboard(self, url="http://127.0.0.1:8000"):
        try:
            context = await self.get_browser_context()
            page = context.pages[0] if context.pages else await context.new_page()
            await page.goto(url)
            await page.bring_to_front()
        except Exception as e:
            print(f"Error opening dashboard: {e}")
            self.browser = None
            self.context = None # Force reset on error
            
    async def run_task(self, task_id: int):
        print(f"[DEBUG] run_task called with task_id: {task_id}")
        try:
            print(f"[DEBUG] Getting browser context...")
            context = await self.get_browser_context()
            print(f"[DEBUG] Browser context obtained: {context}")
            try:
                page = context.pages[0] if context.pages else await context.new_page()
                print(f"[DEBUG] Page obtained: {page.url if hasattr(page, 'url') else 'new page'}")
            except Exception:
                # Retry once if new_page fails (zombie context)
                print("Zombie context detected in run_task, Retrying...")
                self.browser = None
                self.context = None
                context = await self.get_browser_context()
                page = context.pages[0] if context.pages else await context.new_page()
        except Exception as e:
            print(f"Critical Browser Error: {e}")
            import traceback
            traceback.print_exc()  # 전체 스택 트레이스 출력
            self.browser = None
            self.context = None
            return # Let background task fail gracefully
            
        """
        Executes a pull-up task:
        1. Reuse existing window if available
        2. Write New Post
        """
        with Session(db_engine) as session:
            task = session.get(Task, task_id)
            if not task:
                print(f"Task {task_id} not found")
                return

            account = task.account
            if not account:
                self._log(session, task_id, "FAILED", "Account not found")
                return

            # Use Persistent/Shared Context
            context = await self.get_browser_context()
            if context:
                # FAILSAFE: Inject cookies from DB if available
                # This ensures login persists even if browser profile is cleared/buggy
                if account.cookies_json and len(account.cookies_json) > 10:
                    try:
                        cookies = json.loads(account.cookies_json)
                        # Ensure secure flag is handled if running local http
                        await context.add_cookies(cookies)
                        self._log(session, task_id, "INFO", "Restored login session from saved datebase cookies.")
                    except Exception as e:
                        print(f"Cookie restore warning: {e}")

                # Use the first open page or create new one
                page = context.pages[0] if context.pages else await context.new_page()
                try:
                    await page.bring_to_front()
                except: pass
                
                try:
                    # 1. Ensure Login
                    await page.goto("https://www.naver.com")
                    await page.wait_for_load_state("domcontentloaded")
                    
                    # Check for login button (means we are NOT logged in)
                    # Naver main page usually has a login button with class .gnb_btn_login or id #gnb_login_button
                    login_btn = page.locator(".gnb_btn_login, #gnb_login_button, #account .link_login").first
                    if await login_btn.count() > 0 and await login_btn.is_visible():
                        self._log(session, task_id, "WAITING", "Not logged in. Redirecting to login page...")
                        await page.goto("https://nid.naver.com/nidlogin.login")
                        
                        # Wait for user to login (Poll for success)
                        self._log(session, task_id, "WAITING", "Please login! Waiting for main page redirect...")
                        
                        for _ in range(120): # 2 mins max
                            if "nid.naver.com" not in page.url and "naver.com" in page.url:
                                self._log(session, task_id, "INFO", "Login detected!")
                                break
                            await asyncio.sleep(1)
                            
                        # Double check
                        if "nid.naver.com" in page.url:
                             self._log(session, task_id, "FAILED", "Login timeout.")
                             return 
                        
                        # LOGIN SUCCESS: Capture and Save Cookies
                        try:
                            # Update account cookies in DB for robustness
                            current_cookies = await context.cookies()
                            account.cookies_json = json.dumps(current_cookies)
                            session.add(account)
                            session.commit()
                            self._log(session, task_id, "INFO", "Login successful! Session saved to database.")
                        except Exception as e:
                             print(f"Failed to save cookies: {e}")
                    
                    target_url = task.cafe_url
                    
                    # Force PC Version for reliable automation
                    # Convert: https://cafe.naver.com/f-e/cafes/31621061/menus/1...
                    # To: https://cafe.naver.com/ArticleList.nhn?search.clubid=31621061&search.menuid=1
                    mobile_match = re.search(r"cafe\.naver\.com/f-e/cafes/(\d+)/menus/(\d+)", target_url)
                    if mobile_match:
                        club_id = mobile_match.group(1)
                        menu_id = mobile_match.group(2)
                        target_url = f"https://cafe.naver.com/ArticleList.nhn?search.clubid={club_id}&search.menuid={menu_id}"
                        self._log(session, task_id, "INFO", f"Converted Mobile URL to PC URL for stability: {target_url}")
                    
                    # 1.5 Navigate to Board (New Logic)
                    if task.board_name and task.board_name.lower() != "default":
                         self._log(session, task_id, "RUNNING", f"Navigating to board: {task.board_name}")
                         try:
                             # Try to find the menu in the main page (left sidebar usually)
                             menu = page.locator(f"a:has-text('{task.board_name}')").first
                             if await menu.count() > 0:
                                 await menu.click()
                                 await page.wait_for_timeout(2000) 
                             else:
                                 self._log(session, task_id, "WARNING", f"Board '{task.board_name}' not found. Staying on main page.")
                         except Exception as e:
                             self._log(session, task_id, "WARNING", f"Error navigating to board: {str(e)}")

                    # 2. Find OLD Post (to be deleted later)
                    old_post_url = None
                    if not task.board_name:
                        await page.goto(target_url)
                    
                    # 2. Find Write Button & Click
                    # Checks for both legacy and modern with a retry/wait loop for manual login
                    
                    write_btn = None
                    main_frame = None
                    
                    # Try for up to 60 seconds (user can login manually)
                    self._log(session, task_id, "WAITING", "Looking for 'Write' button... (Login manually if needed)")
                    
                    for i in range(30): # Increased wait to 90s
                        try:
                            # 0. Check if we are on the wrong page (Main Naver instead of Cafe)
                            current_url = page.url
                            # Allow being on login page without forcing redirect
                            if "cafe.naver.com" not in current_url and "nid.naver.com" not in current_url and "login" not in current_url:
                                # We are likely on the login success page or main naver page
                                # If we see user info or just generic "Login", assumption is we are logged in or need to move
                                # Force move to target URL to stop waiting on the wrong page
                                self._log(session, task_id, "INFO", f"Not on Cafe page ({current_url}). forcing navigation to board...")
                                await page.goto(target_url)
                                await asyncio.sleep(2)
                            
                            # 1. Check Legacy Iframe
                            iframe_element = await page.query_selector("#cafe_main")
                            if iframe_element:
                                main_frame = page.frame_locator("#cafe_main")
                                write_btn = await main_frame.get_by_text("글쓰기").first.is_visible()
                                if write_btn:
                                    write_btn = main_frame.get_by_text("글쓰기").first
                                    break
                            
                            # 2. Check Modern/Mobile DOM
                            # List of potential write button selectors (Prioritize accurate ones)
                            write_selectors = [
                                page.locator("#cafe-info-data .btn_cafe_writing").first, # Sidebar (Most reliable)
                                page.locator("#write-btn").first,
                                page.locator(".btn_writing").first,
                                page.locator("a[href*='TitleIn.nhn']").first, # Legacy write link
                                page.locator("a:has-text('글쓰기')").first,
                                page.locator("button:has-text('글쓰기')").first
                            ] 
                            
                            # Removed dangerous generic get_by_text("글쓰기") that matches popups/memos
                            
                            for sel in write_selectors:
                                if await sel.count() > 0 and await sel.is_visible():
                                    write_btn = sel
                                    break
                                    
                            if write_btn:
                                break
                                
                        except Exception:
                            pass
                        
                        await asyncio.sleep(3)
                        
                    if not write_btn:
                        await page.screenshot(path="debug_write_btn_fail.png")
                        self._log(session, task_id, "FAILED", "Could not find 'Write' button. Screenshot saved. (Check login/permissions)")
                        return
                        
                    # 3. Write New Post (Handle New Tab)
                    self._log(session, task_id, "RUNNING", "Found write button, clicking...")
                    
                    editor_page = None
                    try:
                        # Naver SmartEditor usually opens in a new tab/popup
                        async with context.expect_page() as new_page_info:
                            await write_btn.click(timeout=5000)
                        
                        editor_page = await new_page_info.value
                        await editor_page.wait_for_load_state()
                        self._log(session, task_id, "RUNNING", "Switched to Editor Tab")
                        
                    except Exception as e:
                        self._log(session, task_id, "WARNING", f"New tab detection failed: {e}. Checking open pages...")
                        # Fallback: Check if a new page exists in context.pages
                        if len(context.pages) > 1:
                             editor_page = context.pages[-1]
                             self._log(session, task_id, "RUNNING", f"Selected last open tab: {editor_page.url}")
                        else:
                             editor_page = page
                             self._log(session, task_id, "WARNING", "No new tab found, using current page.")

                    # Wait for Editor (SmartEditor One or 2.0)
                    self._log(session, task_id, "RUNNING", "Waiting for editor to load...")
                    
                    try:
                        target_page = editor_page
                        await target_page.wait_for_load_state("domcontentloaded")
                        
                        # Debug: Log frames
                        frames = target_page.frames
                        self._log(session, task_id, "DEBUG", f"Found {len(frames)} frames.")
                        
                        # 1. Handle TITLE Input
                        title_found = False
                        self._log(session, task_id, "RUNNING", "Attempting to type title...")
                        
                        # A. Playwright Locators
                        title_candidates = [
                            target_page.locator("textarea[placeholder*='제목']"), 
                            target_page.locator("input[placeholder*='제목']"),
                            target_page.get_by_placeholder("제목을 입력해 주세요"),
                            target_page.locator(".textarea_input"),
                            target_page.locator("#subject")
                        ]
                        
                        for locator in title_candidates:
                            if await locator.count() > 0 and await locator.first.is_visible():
                                try:
                                    await target_page.keyboard.press("Escape") 
                                except: pass
                                await locator.first.click(force=True)
                                await asyncio.sleep(0.5)
                                await locator.first.fill(task.title or task.name)
                                self._log(session, task_id, "RUNNING", "Typed Title successfully")
                                title_found = True
                                break
                        
                        # B. JS Fallback (Force Value)
                        if not title_found:
                            self._log(session, task_id, "WARNING", "Standard title typing failed. Trying JS injection...")
                            try:
                                js_success = await target_page.evaluate("""(text) => {
                                    const el = document.querySelector('textarea[placeholder*="제목"], input[placeholder*="제목"], .textarea_input');
                                    if (el) {
                                        el.value = text;
                                        el.dispatchEvent(new Event('input', { bubbles: true }));
                                        return true;
                                    }
                                    return false;
                                }""", task.title or task.name)
                                if js_success:
                                    title_found = True
                                    self._log(session, task_id, "INFO", "Typed Title via JS")
                            except Exception as e:
                                self._log(session, task_id, "WARNING", f"JS Title failed: {e}")

                        # C. Frame Fallback
                        if not title_found:
                            for f in frames:
                                try:
                                    f_loc = f.locator("textarea[placeholder*='제목'], input[placeholder*='제목']")
                                    if await f_loc.count() > 0:
                                        await f_loc.first.fill(task.title or task.name)
                                        title_found = True
                                        self._log(session, task_id, "RUNNING", "Typed Title in frame")
                                        break
                                except: pass

                        await asyncio.sleep(1.0) 

                        # 2. Handle CONTENT Input
                        content_found = False
                        self._log(session, task_id, "RUNNING", "Attempting to type content...")
                        
                        # A. Playwright Locators (SE One / ContentEditable)
                        se_content = target_page.locator(".se-main-container .se-content, .se-text-paragraph, [contenteditable='true']").first
                        
                        if await se_content.count() > 0:
                             await se_content.click(force=True)
                             await asyncio.sleep(0.5)
                             await target_page.keyboard.type(task.content_html or "Automated Post Content")
                             self._log(session, task_id, "RUNNING", "Typed Content")
                             content_found = True
                        
                        # B. JS Fallback for Content (InnerHTML / TextContent)
                        if not content_found:
                             self._log(session, task_id, "WARNING", "Standard content typing failed. Trying JS injection...")
                             try:
                                 js_valid = await target_page.evaluate("""(html) => {
                                     const el = document.querySelector('.se-main-container .se-content, [contenteditable="true"], body.se2_input_area');
                                     if (el) {
                                         el.focus();
                                         el.innerHTML = html; # Direct HTML injection usually works for editors
                                         el.dispatchEvent(new Event('input', { bubbles: true })); 
                                         return true;
                                     }
                                     return false;
                                 }""", task.content_html or "Automated Post Content")
                                 
                                 if js_valid:
                                     content_found = True
                                     self._log(session, task_id, "INFO", "Typed Content via JS")
                             except Exception as e:
                                 self._log(session, task_id, "WARNING", f"JS Content failed: {e}")

                        # C. Frame Fallback
                        if not content_found:
                             for f in frames:
                                 try:
                                     body = f.locator("body[contenteditable='true']")
                                     if await body.count() > 0:
                                         await body.click()
                                         await asyncio.sleep(0.5)
                                         await target_page.keyboard.type(task.content_html or "Automated Post Content")
                                         content_found = True
                                         break
                                 except: pass
                        
                        await asyncio.sleep(1.0)

                        if not content_found and title_found:
                             # Last resort: Tab from title
                             await target_page.keyboard.press("Tab")
                             await target_page.keyboard.type(task.content_html or "Automated Post Content")

                        # 3. Click SUBMIT "등록"
                        # Look for Green button at top right
                        submit_candidates = [
                            target_page.locator("button.btn_register").first, # Standard SE One
                            target_page.locator("a.btn_register").first, 
                            target_page.locator("button:has-text('등록')").first,
                            target_page.locator("#btn_submit") # Legacy
                        ]
                        
                        submit_btn = None
                        for btn in submit_candidates:
                            if await btn.count() > 0 and await btn.is_visible():
                                submit_btn = btn
                                break
                                
                        if submit_btn:
                            self._log(session, task_id, "RUNNING", "Found Submit button. Clicking...")
                            await asyncio.sleep(1.0)
                            await submit_btn.click(force=True)
                            self._log(session, task_id, "SUCCESS", "Clicked 'Register'. Post should be live!")
                        else:
                            self._log(session, task_id, "WARNING", "Submit button ('등록') not found.")
                            await target_page.screenshot(path="debug_submit_fail.png")

                        # Wait long enough for user to see the posted result
                        await asyncio.sleep(15)

                    except Exception as e:
                        # Dump HTML for debugging
                        try:
                            with open("debug_editor.html", "w", encoding="utf-8") as f:
                                f.write(await target_page.content())
                        except: pass
                        
                        await target_page.screenshot(path="debug_editor_fail.png")
                        self._log(session, task_id, "FAILED", f"Editor failed. HTML dumped. Error: {str(e)}")
                        await asyncio.sleep(60)

                    # 4. Old Post Deletion (Placeholder)
                    # Implementation of delete logic...
                    
                except Exception as e:
                    self._log(session, task_id, "FAILED", f"Error during execution: {str(e)}")
                    # Wait on general error too
                    await asyncio.sleep(10)
                finally:
                    # Do NOT close context provided by get_browser_context
                    # We want to keep it open for the user
                    pass

    def _log(self, session, task_id, status, message):
        log = Log(task_id=task_id, status=status, message=message)
        session.add(log)
        session.commit()

actions = AutomationEngine()
