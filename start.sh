#!/usr/bin/env bash
# Personal Data Warehouse — 백엔드 + 프론트엔드 동시 실행 스크립트
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# .env 파일 복사 안내
if [ ! -f .env ]; then
  echo "⚠️  .env 파일이 없습니다. .env.example 을 복사하여 API 키를 입력하세요:"
  echo "   cp .env.example .env && nano .env"
  exit 1
fi

echo "🚀 백엔드 시작 (http://localhost:8000) ..."
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

sleep 2

echo "🎨 프론트엔드 시작 (http://localhost:8501) ..."
streamlit run frontend/app.py --server.port 8501 &
FRONTEND_PID=$!

echo ""
echo "✅ 실행 중!"
echo "   백엔드  API: http://localhost:8000/docs"
echo "   프론트엔드:  http://localhost:8501"
echo ""
echo "종료하려면 Ctrl+C 를 누르세요."

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; echo '종료됨'" EXIT INT TERM
wait
