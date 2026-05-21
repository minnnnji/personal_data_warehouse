#!/usr/bin/env bash
# [폐쇄망 서버에서 실행]
# venv를 생성하고 오프라인으로 패키지를 설치합니다.
# 사전 조건: packages/ 폴더와 requirements.txt가 같은 디렉토리에 있어야 합니다.
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [ ! -d packages ]; then
  echo "오류: packages/ 폴더가 없습니다."
  echo "인터넷 연결된 PC에서 download_packages.sh 를 먼저 실행하고 전송하세요."
  exit 1
fi

if [ ! -f requirements.txt ]; then
  echo "오류: requirements.txt 파일이 없습니다."
  exit 1
fi

echo "가상 환경(venv) 생성 중..."
python3 -m venv venv

echo "가상 환경 활성화..."
source venv/bin/activate

echo "패키지 설치 중 (오프라인, 외부 네트워크 미사용)..."
pip install --no-index --find-links=packages/ -r requirements.txt

echo ""
echo "설치 완료!"
echo "앱 실행: bash start.sh"
