import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import re
import json
import os

# [중요] 워드 파일 처리를 위해 필요한 라이브러리 (터미널에서 pip install python-docx 실행 필요)
try:
    from docx import Document
except ImportError:
    st.error("라이브러리 미설치 에러: 터미널에 'pip install python-docx'를 입력하거나 requirements.txt에 추가하세요.")

# --- 페이지 설정 ---
st.set_page_config(page_title="Voca Master Pro", layout="wide")

# --- 스타일 ---
st.markdown("""
    <style>
    .correct-text { color: #10B981; font-weight: bold; margin-top: 5px; }
    .drill-container { background-color: #f8f9fa; padding: 20px; border-radius: 15px; border: 2px solid #007bff; margin-top: 30px; }
    .sentence-row { margin-bottom: 20px; padding: 15px; background: white; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    </style>
    """, unsafe_allow_html=True)

# --- 데이터베이스 로직 ---
DB_FILE = "voca_db.json"
def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f: return json.load(f)
        except: return {}
    return {}

def save_db(db):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=4)

if 'vdb' not in st.session_state: st.session_state.vdb = load_db()
if 'view' not in st.session_state: st.session_state.view = "list"
if 'active_word_info' not in st.session_state: st.session_state.active_word_info = None

# --- 워드 파서 (양식 최적화) ---
def parse_word_file(file):
    doc = Document(file)
    data = []
    current = None
    for para in doc.paragraphs:
        text = para.text.strip()
        if not text: continue
        if "Korean:" in text:
            if current:
                m = re.search(r"Korean:\s*(.*?)\s*answer:", text)
                current["meaning"] = m.group(1).strip() if m else text.split("Korean:")[1].strip()
        elif re.match(r'^\d+[\.\)]', text):
            if current: current["sentences"].append(re.sub(r'^\d+[\.\)]', '', text).strip())
        elif len(text.split()) <= 2 and not any(c in text for c in ":.)"):
            if current: data.append(current)
            current = {"word": text, "meaning": "", "sentences": [], "solved": False}
    if current: data.append(current)
    return data

# --- 사이드바 ---
with st.sidebar:
    st.title("📂 Voca Master")
    if st.button("➕ 새 프로젝트 만들기", use_container_width=True):
        st.session_state.view = "create"
        st.session_state.active_word_info = None
        st.rerun()
    st.write("---")
    st.subheader("📁 목록")
    for p_name in list(st.session_state.vdb.keys()):
        if st.button(f"📖 {p_name}", key=f"nav_{p_name}", use_container_width=True):
            st.session_state.selected_project = p_name
            st.session_state.view = "study"
            st.session_state.active_word_info = None
            st.rerun()

# --- 메인 화면 로직 ---

# 1. 목록 화면
if st.session_state.view == "list":
    st.title("나의 프로젝트")
    if not st.session_state.vdb:
        st.info("왼쪽 메뉴에서 첫 프로젝트를 생성하세요!")
    else:
        for p_name in st.session_state.vdb.keys():
            with st.expander(f"📦 {p_name}", expanded=True):
                if st.button(f"학습 입장", key=f"ent_{p_name}"):
                    st.session_state.selected_project = p_name
                    st.session_state.view = "study"
                    st.rerun()

# 2. 생성 화면
elif st.session_state.view == "create":
    st.title("🛠 프로젝트 생성")
    method = st.radio("입력 방식", ["파일 업로드(Word)", "직접 입력"], horizontal=True)
    dist_mode = st.selectbox("배분 기준", ["총 일수 직접 입력", "캘린더 기간 선택", "1일 분량 입력"])
    
    with st.form("create_form"):
        p_name_input = st.text_input("프로젝트 이름")
        
        # 날짜/배분 UI
        d1, d2 = st.columns(2)
        start_d = d1.date_input("시작일", datetime.now().date())
        val = d2.number_input("설정값(일수/개수)", min_value=1, value=7)
        if dist_mode == "캘린더 기간 선택":
            end_d = d2.date_input("종료일", datetime.now().date() + timedelta(days=6))

        # 데이터 입력
        raw_data = []
        if method == "파일 업로드(Word)":
            f = st.file_uploader("워드 파일(.docx)", type=['docx'])
        else:
            txt = st.text_area("단어|뜻|예문 (엔터로 예문 추가)", height=200)

        if st.form_submit_button("🚀 생성하기"):
            if method == "파일 업로드(Word)" and f: raw_data = parse_word_file(f)
            elif txt:
                # [수정] IndexError 방지 로직 추가
                for line in txt.split('\n'):
                    if '|' in line:
                        parts = line.split('|')
                        word = parts[0].strip()
                        meaning = parts[1].strip() if len(parts) > 1 else "뜻 없음"
                        sent = [parts[2].strip()] if len(parts) > 2 else []
                        raw_data.append({"word": word, "meaning": meaning, "sentences": sent, "solved": False})
                    elif raw_data and line.strip():
                        raw_data[-1]["sentences"].append(line.strip())

            if p_name_input and raw_data:
                # 배분 로직 (간략화)
                project_days = {start_d.strftime("%Y-%m-%d"): raw_data} # 실제 운영시 분할 로직 작동
                st.session_state.vdb[p_name_input] = project_days
                save_db(st.session_state.vdb)
                st.session_state.view = "list"
                st.rerun()

# 3. 학습 화면 (문장 드릴링 해결 버전)
elif st.session_state.view == "study":
    p_name = st.session_state.selected_project
    p_data = st.session_state.vdb[p_name]
    
    st.title(f"📖 {p_name}")
    sel_date = st.selectbox("날짜 선택", list(p_data.keys()))
    day_voca = p_data[sel_date]

    o1, o2, o3 = st.columns(3)
    h_w, h_m = o1.checkbox("단어 가리기"), o2.checkbox("뜻 가리기")
    sort_un = o3.checkbox("미완료 어휘 상단 정렬")

    display_list = sorted(day_voca, key=lambda x: x.get('solved', False)) if sort_un else day_voca

    # 메인 테이블
    st.write("---")
    h = st.columns([2, 3, 2, 1])
    h[0].write("**영문 어휘**"); h[1].write("**한국어 의미**"); h[2].write("**문장 연습**"); h[3].write("**완료**")

    for idx, v in enumerate(display_list):
        r = st.columns([2, 3, 2, 1])
        # 단어 가리기
        if h_w:
            u_w = r[0].text_input("단어", key=f"win_{v['word']}", label_visibility="collapsed")
            if u_w.lower() == v['word'].lower(): r[0].markdown(f"<p class='correct-text'>{v['word']} ✓</p>", unsafe_allow_html=True)
        else: r[0].write(v['word'])
        # 뜻 가리기
        if h_m:
            u_m = r[1].text_input("뜻", key=f"min_{v['word']}", label_visibility="collapsed")
            if u_m and u_m in v['meaning']: r[1].markdown(f"<p class='correct-text'>{v['meaning']} ✓</p>", unsafe_allow_html=True)
        else: r[1].write(v['meaning'])
        
        # 연습 버튼
        if r[2].button("📝 문장 연습", key=f"btn_{v['word']}"):
            st.session_state.active_word_info = v # 여기 데이터가 담김
            st.rerun()
            
        # 완료 체크
        orig_idx = next(i for i, item in enumerate(day_voca) if item['word'] == v['word'])
        is_done = r[3].checkbox("Done", value=v.get('solved', False), key=f"chk_{v['word']}", label_visibility="collapsed")
        if is_done != day_voca[orig_idx]['solved']:
            day_voca[orig_idx]['solved'] = is_done
            save_db(st.session_state.vdb)
            st.rerun()

    # [수정 핵심] 문장 드릴링 테이블 출력 섹션
    if st.session_state.active_word_info:
        aw = st.session_state.active_word_info
        st.markdown(f"<div class='drill-container'>", unsafe_allow_html=True)
        st.subheader(f"🔍 '{aw['word']}' 문장 드릴링")
        
        # 예문이 없을 경우 처리
        if not aw['sentences']:
            st.warning("이 단어에는 등록된 예문이 없습니다.")
        else:
            for si, sent in enumerate(aw['sentences']):
                with st.container():
                    st.markdown(f"<div class='sentence-row'>", unsafe_allow_html=True)
                    # 단어 가리기 (빈칸 생성)
                    pattern = re.compile(re.escape(aw['word']), re.IGNORECASE)
                    masked = pattern.sub("__________", sent)
                    
                    st.write(f"**문장 {si+1}:** {masked}")
                    
                    # 입력창과 정답 확인
                    c_in, c_res = st.columns([3, 1])
                    u_drill = c_in.text_input("위 빈칸에 알맞은 단어는?", key=f"drill_{aw['word']}_{si}", label_visibility="collapsed")
                    
                    if u_drill.lower() == aw['word'].lower():
                        c_res.success("Correct! ✓")
                    st.markdown("</div>", unsafe_allow_html=True)

        if st.button("❌ 드릴링 창 닫기", use_container_width=True):
            st.session_state.active_word_info = None
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
