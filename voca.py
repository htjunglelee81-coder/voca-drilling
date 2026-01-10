import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import re
import json
import os

try:
    from docx import Document
except ImportError:
    st.error("라이브러리 미설치: pip install python-docx 를 실행하세요.")

# --- 페이지 설정 ---
st.set_page_config(page_title="Voca Master Pro", layout="wide")

# --- 스타일 ---
st.markdown("""
    <style>
    .correct-text { color: #10B981; font-weight: bold; margin-top: 5px; }
    .drill-container { background-color: #f0f4f8; padding: 25px; border-radius: 15px; border: 2px solid #1E3A8A; margin-top: 30px; }
    .sentence-card { background: white; padding: 15px; border-radius: 10px; margin-bottom: 15px; border-left: 5px solid #1E3A8A; }
    </style>
    """, unsafe_allow_html=True)

# --- 데이터 관리 ---
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

# --- [개선] day15.docx 전용 파서 ---
def parse_day15_docx(file):
    doc = Document(file)
    data = []
    current_entry = None
    
    for para in doc.paragraphs:
        text = para.text.strip()
        if not text: continue
        
        # 패턴 1: 예문 (숫자로 시작)
        if re.match(r'^\d+[\.\)]', text):
            if current_entry:
                clean_sent = re.sub(r'^\d+[\.\)]', '', text).strip()
                current_entry["sentences"].append(clean_sent)
        
        # 패턴 2: 뜻 (Korean: 포함)
        elif "Korean:" in text:
            if current_entry:
                m = re.search(r"Korean:\s*(.*?)(?:\s*answer:|$)", text)
                current_entry["meaning"] = m.group(1).strip() if m else text.replace("Korean:", "").strip()
        
        # 패턴 3: 단어 (영문자만 있고 짧음)
        elif re.match(r'^[a-zA-Z\s\-]+$', text) and len(text.split()) <= 3:
            if current_entry: data.append(current_entry)
            current_entry = {"word": text, "meaning": "뜻 없음", "sentences": [], "solved": False}
            
    if current_entry: data.append(current_entry)
    return data

# --- 사이드바 ---
with st.sidebar:
    st.title("📂 Voca Master")
    if st.button("➕ 새 프로젝트 만들기", use_container_width=True):
        st.session_state.view = "create"
        st.session_state.active_word_info = None
        st.rerun()
    st.write("---")
    st.subheader("📁 프로젝트 목록")
    for p_name in list(st.session_state.vdb.keys()):
        if st.button(f"📖 {p_name}", key=f"nav_{p_name}", use_container_width=True):
            st.session_state.selected_project = p_name
            st.session_state.view = "study"
            st.session_state.active_word_info = None
            st.rerun()

# --- 1. 메인 목록 ---
if st.session_state.view == "list":
    st.title("나의 학습 보드")
    if not st.session_state.vdb:
        st.info("왼쪽 메뉴에서 프로젝트를 먼저 생성해 주세요.")
    else:
        for p_name in st.session_state.vdb.keys():
            with st.container():
                st.markdown(f"### {p_name}")
                if st.button("이 프로젝트 학습하기", key=f"main_{p_name}"):
                    st.session_state.selected_project = p_name
                    st.session_state.view = "study"
                    st.rerun()

# --- 2. 생성 화면 (배분 로직 포함) ---
elif st.session_state.view == "create":
    st.title("🛠 새 프로젝트 생성")
    with st.form("create_voca_form"):
        p_title = st.text_input("프로젝트 이름 (예: Day 15 학습)")
        uploaded_docx = st.file_uploader("워드 파일 업로드", type=['docx'])
        
        col_d1, col_d2 = st.columns(2)
        start_date = col_d1.date_input("학습 시작일", datetime.now().date())
        days_count = col_d2.number_input("목표 일수(데이터 분할용)", min_value=1, value=1)
        
        if st.form_submit_button("🚀 생성 및 자동 배분"):
            if p_title and uploaded_docx:
                parsed_data = parse_day15_docx(uploaded_docx)
                # 날짜별 배분
                chunk_size = len(parsed_data) // days_count
                if chunk_size == 0: chunk_size = len(parsed_data)
                
                project_data = {}
                for i in range(days_count):
                    d_str = (start_date + timedelta(days=i)).strftime("%Y-%m-%d")
                    start_idx = i * chunk_size
                    end_idx = (i+1) * chunk_size if i < days_count - 1 else len(parsed_data)
                    project_data[d_str] = parsed_data[start_idx:end_idx]
                
                st.session_state.vdb[p_title] = project_data
                save_db(st.session_state.vdb)
                st.session_state.view = "list"
                st.rerun()

# --- 3. 학습 화면 (복구된 기능들) ---
elif st.session_state.view == "study":
    p_name = st.session_state.selected_project
    p_data = st.session_state.vdb[p_name]
    
    st.title(f"📖 {p_name}")
    sel_date = st.selectbox("학습 날짜", list(p_data.keys()))
    day_voca = p_data[sel_date]

    # [복구] 옵션 바
    opt1, opt2, opt3 = st.columns(3)
    hide_w = opt1.checkbox("단어 가리기")
    hide_m = opt2.checkbox("뜻 가리기")
    sort_un = opt3.checkbox("미완료 어휘 상단 정렬")

    display_list = sorted(day_voca, key=lambda x: x.get('solved', False)) if sort_un else day_voca

    # 메인 테이블 헤더
    st.write("---")
    header = st.columns([2, 3, 2, 1])
    header[0].write("**영문 어휘**"); header[1].write("**한국어 의미**"); header[2].write("**문장 연습**"); header[3].write("**완료**")

    for idx, v in enumerate(display_list):
        orig_idx = next(i for i, item in enumerate(day_voca) if item['word'] == v['word'])
        r = st.columns([2, 3, 2, 1])
        
        # [복구] 단어 가리기/입력
        with r[0]:
            if hide_w:
                u_w = st.text_input("w", key=f"win_{v['word']}", label_visibility="collapsed")
                if u_w.lower() == v['word'].lower(): st.markdown(f"<p class='correct-text'>{v['word']} ✓</p>", unsafe_allow_html=True)
            else: st.write(f"**{v['word']}**")
            
        # [복구] 뜻 가리기/입력
        with r[1]:
            if hide_m:
                u_m = st.text_input("m", key=f"min_{v['word']}", label_visibility="collapsed")
                if u_m and u_m in v['meaning']: st.markdown(f"<p class='correct-text'>{v['meaning']} ✓</p>", unsafe_allow_html=True)
            else: st.write(v['meaning'])
            
        # 문장 연습 버튼
        if r[2].button("📝 문장 연습", key=f"btn_{v['word']}"):
            st.session_state.active_word_info = v
            st.rerun()
            
        # [복구] 완료 체크박스 및 정렬 유지
        new_solved = r[3].checkbox("D", value=v.get('solved', False), key=f"chk_{v['word']}", label_visibility="collapsed")
        if new_solved != day_voca[orig_idx]['solved']:
            day_voca[orig_idx]['solved'] = new_solved
            save_db(st.session_state.vdb)
            st.rerun()

    # [복구 및 강화] 문장 드릴링 섹션
    if st.session_state.active_word_info:
        aw = st.session_state.active_word_info
        st.markdown(f"<div class='drill-container'>", unsafe_allow_html=True)
        st.subheader(f"🔍 '{aw['word']}' 문장 연습 (예문 {len(aw['sentences'])}개 발견)")
        
        if not aw['sentences']:
            st.warning("이 단어의 예문을 찾지 못했습니다. 파싱 로직을 확인하세요.")
        else:
            for si, sent in enumerate(aw['sentences']):
                st.markdown(f"<div class='sentence-card'>", unsafe_allow_html=True)
                # 해당 단어 빈칸 처리
                pattern = re.compile(re.escape(aw['word']), re.IGNORECASE)
                masked = pattern.sub("__________", sent)
                st.write(f"**{si+1}.** {masked}")
                
                c_in, c_msg = st.columns([4, 1])
                drill_ans = c_in.text_input("단어 입력", key=f"drill_{aw['word']}_{si}", label_visibility="collapsed")
                if drill_ans.lower() == aw['word'].lower():
                    c_msg.success("Correct!")
                st.markdown("</div>", unsafe_allow_html=True)

        if st.button("❌ 연습 창 닫기", use_container_width=True):
            st.session_state.active_word_info = None
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
