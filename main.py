import sys
import asyncio

# Force ProactorEventLoop on Windows for Playwright compatibility
if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from fastapi import FastAPI, Request, Form, Depends, BackgroundTasks, Response
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from contextlib import asynccontextmanager
from app.database import create_db_and_tables
from app.routers import accounts, tasks

@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield

app = FastAPI(lifespan=lifespan)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

app.include_router(accounts.router)
app.include_router(tasks.router)

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return Response(status_code=204)

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

if __name__ == "__main__":
    import uvicorn
    import os
    # Render에서는 PORT 환경 변수를 사용하고, 로컬에서는 8000 포트 사용
    port = int(os.environ.get("PORT", 8000))
    # 0.0.0.0으로 설정하여 외부 접근 허용 (Render 배포 필수)
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
