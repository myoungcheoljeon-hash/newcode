import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID", "")
    NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET", "")
    TARGET_CAFE_ID = os.getenv("TARGET_CAFE_ID", "")
    # Chrome CDP 포트 (기존 브라우저 연결용)
    CHROME_CDP_PORT = os.getenv("CHROME_CDP_PORT", "9222")

settings = Settings()
