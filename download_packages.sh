#!/usr/bin/env bash
# [인터넷 연결된 PC에서 실행]
# 모든 의존성을 packages/ 폴더에 다운로드합니다.
# 완료 후 아래 파일을 폐쇄망 서버로 전송하세요:
#   packages/ 폴더 전체, requirements.txt, setup_offline.sh
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "패키지 다운로드 시작..."
mkdir -p packages
pip download -r requirements.txt -d packages/

echo ""
echo "완료. 폐쇄망 서버로 전송할 항목:"
echo "  packages/        ($(ls packages/ | wc -l)개 파일)"
echo "  requirements.txt"
echo "  setup_offline.sh"
echo ""
echo "전송 후 서버에서: bash setup_offline.sh"
