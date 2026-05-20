"""
Personal Data Warehouse — Streamlit Frontend
백엔드(FastAPI)가 http://localhost:8000 에서 실행 중이어야 합니다.
"""

import io
import os

import pandas as pd
import requests
import streamlit as st

API = os.environ.get("DW_API_URL", "http://localhost:8000")

st.set_page_config(
    page_title="Personal Data Warehouse",
    page_icon="🏭",
    layout="wide",
)


# ──────────────────────────────────────────────────────────────────────────────
# 유틸리티
# ──────────────────────────────────────────────────────────────────────────────


def api_get(path: str, params: dict = None):
    try:
        r = requests.get(f"{API}{path}", params=params, timeout=30)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.ConnectionError:
        st.error("❌ 백엔드 서버에 연결할 수 없습니다. `uvicorn backend.main:app` 실행 여부를 확인하세요.")
        return None
    except Exception as e:
        st.error(f"API 오류: {e}")
        return None


def api_post(path: str, json_data: dict = None, files=None, timeout=60):
    try:
        if files:
            r = requests.post(f"{API}{path}", files=files, timeout=timeout)
        else:
            r = requests.post(f"{API}{path}", json=json_data, timeout=timeout)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.ConnectionError:
        st.error("❌ 백엔드 서버에 연결할 수 없습니다.")
        return None
    except Exception as e:
        try:
            detail = e.response.json().get("detail", str(e))
        except Exception:
            detail = str(e)
        st.error(f"오류: {detail}")
        return None


def api_delete(path: str):
    try:
        r = requests.delete(f"{API}{path}", timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"삭제 오류: {e}")
        return None


def format_tags(tags: list) -> str:
    return " ".join(f"`{t}`" for t in tags) if tags else "—"


def bytes_to_human(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


def download_button(label: str, url: str, filename: str):
    try:
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        st.download_button(label, data=r.content, file_name=filename)
    except Exception as e:
        st.error(f"다운로드 실패: {e}")


# ──────────────────────────────────────────────────────────────────────────────
# 사이드바 필터
# ──────────────────────────────────────────────────────────────────────────────


def render_sidebar():
    st.sidebar.title("🏭 Data Warehouse")
    st.sidebar.markdown("---")
    st.sidebar.header("🔎 필터")

    cats = api_get("/meta/categories") or []
    projs = api_get("/meta/projects") or []
    tags = api_get("/meta/tags") or []

    sel_cat = st.sidebar.selectbox("카테고리", ["전체"] + cats)
    sel_proj = st.sidebar.selectbox("프로젝트", ["전체"] + projs)
    sel_tag = st.sidebar.selectbox("태그", ["전체"] + tags)

    st.sidebar.markdown("---")
    st.sidebar.caption("백엔드: " + API)

    return (
        None if sel_cat == "전체" else sel_cat,
        None if sel_proj == "전체" else sel_proj,
        None if sel_tag == "전체" else sel_tag,
    )


# ──────────────────────────────────────────────────────────────────────────────
# 탭 1: 파일 창고
# ──────────────────────────────────────────────────────────────────────────────


def render_warehouse(sel_cat, sel_proj, sel_tag):
    st.header("📁 파일 창고")

    params = {}
    if sel_cat:
        params["category"] = sel_cat
    if sel_proj:
        params["project"] = sel_proj
    if sel_tag:
        params["tag"] = sel_tag

    files = api_get("/files", params=params)
    if files is None:
        return
    if not files:
        st.info("저장된 파일이 없습니다. '파일 업로드' 탭에서 파일을 추가하세요.")
        return

    st.caption(f"총 {len(files)}개 파일")

    for f in files:
        fid = f["id"]
        with st.container(border=True):
            col_info, col_actions = st.columns([3, 1])

            with col_info:
                st.markdown(f"### 📄 {f['original_filename']}")
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("카테고리", f["category"] or "—")
                c2.metric("프로젝트", f["project_name"] or "—")
                c3.metric("행 × 열", f"{f['row_count']:,} × {f['col_count']}")
                c4.metric("크기", bytes_to_human(f["file_size"]))

                if f["description"]:
                    st.markdown(f"> {f['description']}")

                if f["tags"]:
                    st.markdown(f"**태그:** {format_tags(f['tags'])}")

                with st.expander("컬럼 정보"):
                    if f["columns_info"]:
                        col_df = pd.DataFrame(
                            [
                                {
                                    "컬럼명": c["name"],
                                    "타입": c["dtype"],
                                    "결측치": c["null_count"],
                                    "샘플값": ", ".join(c.get("sample_values", [])),
                                }
                                for c in f["columns_info"]
                            ]
                        )
                        st.dataframe(col_df, use_container_width=True, hide_index=True)

            with col_actions:
                st.caption(f"업로드: {f['upload_date'][:10]}")

                # 미리보기
                preview_key = f"preview_{fid}"
                if st.button("👁 미리보기", key=f"btn_preview_{fid}"):
                    st.session_state[preview_key] = not st.session_state.get(
                        preview_key, False
                    )

                # 다운로드
                fmt = st.selectbox(
                    "포맷",
                    ["csv", "xlsx", "pkl", "parquet"],
                    key=f"fmt_{fid}",
                    label_visibility="collapsed",
                )
                download_button(
                    "⬇ 다운로드",
                    f"{API}/files/{fid}/download?format={fmt}",
                    f"{f['original_filename'].rsplit('.', 1)[0]}.{fmt}",
                )

                # 삭제
                if st.button("🗑 삭제", key=f"btn_del_{fid}", type="secondary"):
                    st.session_state[f"confirm_del_{fid}"] = True

                if st.session_state.get(f"confirm_del_{fid}"):
                    st.warning("정말 삭제할까요?")
                    y, n = st.columns(2)
                    if y.button("예", key=f"yes_del_{fid}"):
                        result = api_delete(f"/files/{fid}")
                        if result:
                            st.success("삭제됨")
                            del st.session_state[f"confirm_del_{fid}"]
                            st.rerun()
                    if n.button("아니오", key=f"no_del_{fid}"):
                        del st.session_state[f"confirm_del_{fid}"]
                        st.rerun()

        # 미리보기 테이블 (카드 아래)
        if st.session_state.get(f"preview_{fid}"):
            with st.spinner("불러오는 중..."):
                pdata = api_get(f"/files/{fid}/preview", {"limit": 100})
            if pdata:
                st.caption(
                    f"전체 {pdata['total_rows']:,}행 중 {pdata['preview_rows']}행 표시"
                )
                st.dataframe(
                    pd.DataFrame(pdata["data"], columns=pdata["columns"]),
                    use_container_width=True,
                    height=300,
                )


# ──────────────────────────────────────────────────────────────────────────────
# 탭 2: 파일 업로드
# ──────────────────────────────────────────────────────────────────────────────


def render_upload():
    st.header("⬆️ 파일 업로드")

    # ── 업로드 폼 ──
    if "upload_result" not in st.session_state:
        uploaded = st.file_uploader(
            "파일을 선택하세요 (.csv, .pkl, .parquet, .xlsx, .xls, .json)",
            type=["csv", "pkl", "parquet", "xlsx", "xls", "json"],
        )
        if uploaded is not None:
            with st.spinner("🤖 LLM이 파일을 분석 중..."):
                result = api_post(
                    "/upload",
                    files={"file": (uploaded.name, uploaded.getvalue(), uploaded.type)},
                    timeout=120,
                )
            if result:
                st.session_state["upload_result"] = result
                st.rerun()

    # ── 메타데이터 확인·수정 폼 ──
    if "upload_result" in st.session_state:
        result = st.session_state["upload_result"]
        meta = result["metadata"]
        uncertain = result.get("uncertain", False)
        question = result.get("question_for_user")

        st.success(f"✅ '{meta['original_filename']}' 업로드 완료 — LLM 분석 결과를 확인·수정 후 저장하세요")

        if uncertain and question:
            st.warning(f"🤔 **LLM 질문:** {question}")
            user_answer = st.text_area("답변을 입력하세요 (선택사항)")
        else:
            user_answer = ""

        with st.form("confirm_form"):
            st.subheader("메타데이터 수정")

            c1, c2 = st.columns(2)
            category = c1.text_input("카테고리", value=meta.get("category", ""))
            project = c2.text_input("프로젝트명", value=meta.get("project_name", ""))

            description = st.text_area(
                "설명", value=meta.get("description", ""), height=100
            )
            tags_str = st.text_input(
                "태그 (쉼표 구분)",
                value=", ".join(meta.get("tags", [])),
            )

            st.subheader("파일 정보")
            fi1, fi2, fi3 = st.columns(3)
            fi1.metric("행 수", f"{meta['row_count']:,}")
            fi2.metric("열 수", meta["col_count"])
            fi3.metric("크기", bytes_to_human(meta["file_size"]))

            with st.expander("컬럼 미리보기"):
                if meta["columns_info"]:
                    st.dataframe(
                        pd.DataFrame(
                            [
                                {
                                    "컬럼명": c["name"],
                                    "타입": c["dtype"],
                                    "결측치": c["null_count"],
                                }
                                for c in meta["columns_info"]
                            ]
                        ),
                        hide_index=True,
                        use_container_width=True,
                    )

            submitted = st.form_submit_button("💾 저장 확정", type="primary")

        if submitted:
            tags_list = [t.strip() for t in tags_str.split(",") if t.strip()]
            confirm_data = {
                "file_id": meta["id"],
                "category": category,
                "description": description,
                "tags": tags_list,
                "project_name": project,
                "user_answer": user_answer,
            }
            with st.spinner("저장 중..."):
                r = api_post("/upload/confirm", json_data=confirm_data)
            if r and r.get("success"):
                st.success("✅ 저장 완료!")
                del st.session_state["upload_result"]
                st.rerun()

        if st.button("✖ 취소 (파일 폐기)"):
            del st.session_state["upload_result"]
            st.rerun()


# ──────────────────────────────────────────────────────────────────────────────
# 탭 3: 데이터 검색
# ──────────────────────────────────────────────────────────────────────────────


def render_search():
    st.header("🔍 데이터 검색")

    query = st.text_input(
        "자연어로 찾고 싶은 데이터를 입력하세요",
        placeholder="예) PR 공정 관련 불량률 데이터 뭐 있어?",
    )

    if st.button("검색", type="primary", disabled=not query):
        with st.spinner("🤖 LLM이 검색 중..."):
            result = api_post("/query", json_data={"query": query})
        if result:
            st.markdown("### 💬 답변")
            st.markdown(result["answer"])

            mentioned = set(result.get("mentioned_file_ids", []))
            related = [
                f for f in result.get("all_files", []) if f["id"] in mentioned
            ]

            if related:
                st.markdown(f"### 📌 관련 파일 ({len(related)}개)")
                for f in related:
                    with st.container(border=True):
                        ca, cb = st.columns([4, 1])
                        with ca:
                            st.markdown(f"**{f['original_filename']}**")
                            st.caption(
                                f"{f['category']} | {f['row_count']:,}행 × {f['col_count']}열 | {f['project_name'] or '—'}"
                            )
                            if f["description"]:
                                st.markdown(f"> {f['description']}")
                            if f["tags"]:
                                st.markdown(format_tags(f["tags"]))
                        with cb:
                            fmt = st.selectbox(
                                "포맷",
                                ["csv", "xlsx", "pkl"],
                                key=f"sfmt_{f['id']}",
                                label_visibility="collapsed",
                            )
                            download_button(
                                "⬇ 다운로드",
                                f"{API}/files/{f['id']}/download?format={fmt}",
                                f"{f['original_filename'].rsplit('.', 1)[0]}.{fmt}",
                            )


# ──────────────────────────────────────────────────────────────────────────────
# 탭 4: 데이터 결합
# ──────────────────────────────────────────────────────────────────────────────


def render_combine():
    st.header("🔗 데이터 결합")

    all_files = api_get("/files")
    if not all_files:
        st.info("파일이 없습니다. 먼저 파일을 업로드하세요.")
        return

    st.subheader("1️⃣ 결합할 파일 선택 (2개 이상)")
    selected_ids = []
    cols = st.columns(min(len(all_files), 3))
    for i, f in enumerate(all_files):
        with cols[i % 3]:
            checked = st.checkbox(
                f"**{f['original_filename']}**\n\n"
                f"{f['row_count']:,}행 × {f['col_count']}열 | {f['category']}",
                key=f"combine_chk_{f['id']}",
            )
            if checked:
                selected_ids.append(f["id"])

    if len(selected_ids) >= 2:
        selected_names = [
            f["original_filename"]
            for f in all_files
            if f["id"] in selected_ids
        ]
        st.info(f"선택됨: {', '.join(selected_names)}")

        st.subheader("2️⃣ 결합 명령 입력")
        command = st.text_area(
            "자연어로 명령을 입력하세요",
            placeholder=(
                "예) 두 파일을 세로로 합쳐줘\n"
                "예) lot_id 컬럼 기준으로 left join 해줘\n"
                "예) A파일의 date 컬럼과 B파일의 날짜 컬럼을 기준으로 inner join"
            ),
            height=100,
        )

        if st.button(
            "🤖 코드 생성", type="primary", disabled=not command.strip()
        ):
            with st.spinner("LLM이 pandas 코드를 생성 중..."):
                result = api_post(
                    "/combine",
                    json_data={"file_ids": selected_ids, "command": command},
                    timeout=120,
                )
            if result:
                st.session_state["combine_result"] = result

    # 결과 표시
    if "combine_result" in st.session_state:
        result = st.session_state["combine_result"]
        st.markdown("---")
        st.subheader("3️⃣ 생성된 코드 검토")
        st.code(result["generated_code"], language="python")
        st.caption(
            f"결과: {result['row_count']:,}행 × {result['col_count']}열"
        )

        st.subheader("4️⃣ 결과 미리보기")
        pdata = result["preview"]
        if pdata and pdata.get("data"):
            st.dataframe(
                pd.DataFrame(pdata["data"], columns=pdata["columns"]),
                use_container_width=True,
                height=300,
            )

        st.subheader("5️⃣ 결과 다운로드")
        dl_fmt = st.selectbox("다운로드 포맷", ["csv", "xlsx", "pkl", "parquet"])
        download_button(
            "⬇ 결과 다운로드",
            f"{API}/combine/{result['result_id']}/download?format={dl_fmt}",
            f"combined_result.{dl_fmt}",
        )

        if st.button("🔄 초기화"):
            del st.session_state["combine_result"]
            st.rerun()

    elif len(selected_ids) < 2:
        st.info("파일을 2개 이상 선택하면 결합 명령 입력창이 나타납니다.")


# ──────────────────────────────────────────────────────────────────────────────
# 메인
# ──────────────────────────────────────────────────────────────────────────────


def main():
    sel_cat, sel_proj, sel_tag = render_sidebar()

    tab1, tab2, tab3, tab4 = st.tabs(
        ["📁 파일 창고", "⬆️ 파일 업로드", "🔍 데이터 검색", "🔗 데이터 결합"]
    )

    with tab1:
        render_warehouse(sel_cat, sel_proj, sel_tag)

    with tab2:
        render_upload()

    with tab3:
        render_search()

    with tab4:
        render_combine()


if __name__ == "__main__":
    main()
