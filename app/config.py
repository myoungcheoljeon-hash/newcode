import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID", "")
    NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET", "")
    TARGET_CAFE_ID = os.getenv("TARGET_CAFE_ID", "")

settings = Settings()
