@echo off
REM ========================================
REM Hanyang Smart Auto Bot - Daily Auto
REM 매일 아침 08:00 실행: 스크래핑 + Drive 업로드 + WhatsApp 알림
REM ========================================

cd /d "D:\AI _coding_project_all\hanyang_smart_auto_bot"

REM 가상환경이 있으면 활성화
if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
)

python scrapers/daily_auto.py >> data\logs\daily_auto.log 2>&1

echo [%date% %time%] Daily auto completed >> data\logs\daily_auto.log
