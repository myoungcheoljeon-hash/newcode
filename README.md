# 🚀 Naver Cafe Automation (네이버 카페 자동화 툴)

네이버 카페의 구버전 게시글을 삭제하고 새 글로 등록하여 상단에 노출시키는 **'끌올(Pull-up)' 자동화 프로그램**입니다.
다수의 계정과 게시판 작업을 효율적으로 관리할 수 있도록 설계되었습니다.

![Dashboard Preview](https://via.placeholder.com/800x400?text=Dashboard+Preview)  
*(스크린샷 이미지가 있다면 여기에 추가하세요)*

## ✨ 주요 기능

*   **🛡️ 안전한 로그인 (Manual Login Mode)**: 사용자가 직접 브라우저에서 로그인하면 세션을 안전하게 캡처하여 저장합니다. (캡차/보안 감지 회피)
*   **🤖 스마트한 자동화 (Auto Pull-up)**:
    1.  지정된 게시판으로 이동
    2.  이전에 작성한 동일한 글 검색
    3.  **새 글 작성** (상단 노출)
    4.  **기존 글 삭제** (중복 방지)
*   **📊 대시보드 UI**: 웹 기반의 깔끔한 인터페이스로 여러 계정과 작업을 한눈에 관리합니다.
*   **♾️ 멀티 계정 지원**: 네이버 계정을 무제한으로 등록하고 각기 다른 작업을 할당할 수 있습니다.

## 🛠️ 기술 스택 (Tech Stack)

*   **Backend**: Python 3.10+, FastAPI
*   **Automation**: Playwright (Browser Automation)
*   **Database**: SQLite (SQLModel)
*   **Frontend**: HTML5, CSS3 (Premium Dark Theme), Vanilla JS

## 📦 설치 및 실행 방법

이 프로젝트는 로컬 컴퓨터에서 실행됩니다.

### 1. 필수 프로그램 설치
*   [Python 3.10 이상](https://www.python.org/downloads/)
*   [Git](https://git-scm.com/)

### 2. 프로젝트 다운로드
```bash
git clone https://github.com/your-username/naver-cafe-automation.git
cd naver-cafe-automation
```

### 3. 가상환경 생성 및 패키지 설치
```bash
# 가상환경 생성
python -m venv venv

# 가상환경 활성화 (Windows)
./venv/Scripts/activate

# 필수 라이브러리 설치
pip install -r requirements.txt
playwright install chromium
```

### 4. 서버 실행
Windows 환경에서 Playwright 안정성을 위해 아래 명령어로 실행하세요.
```bash
python run.py
```
서버가 실행되면 브라우저에서 **[http://127.0.0.1:8000](http://127.0.0.1:8000)** 으로 접속하세요.

## 📖 사용 가이드

1.  **계정 연결 (Connect Account)**: 대시보드 상단의 'Connect Account'를 누르고 뜨는 창에서 네이버에 로그인합니다.
2.  **작업 생성 (Create Task)**: 'Tasks' 탭에서 글을 올릴 게시판 주소와 내용을 입력합니다.
3.  **실행 (Run)**: 'Run Now' 버튼을 누르면 브라우저가 열리며 자동으로 글쓰기 및 기존 글 삭제가 진행됩니다.

## ⚠️ 주의사항

*   이 프로그램은 사용자의 편의를 돕는 도구입니다. 과도한 자동화 사용은 네이버 운영 정책에 의해 제재될 수 있으므로 적절한 간격을 두고 사용하세요.
*   개인적인 용도로만 사용하시기 바랍니다.

---
Created by Automation Pro
