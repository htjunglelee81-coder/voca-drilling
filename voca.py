import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import re
import json
import os
from docx import Document

# --- 페이지 설정 ---
st.set_page_config(page_title="Voca Master Pro", layout="wide")

# --- 스타일 정의 ---
st.markdown("""
    <style>
    .main-title { font-size: 2.5rem; font-weight: bold; color: #1E3A8A; margin-bottom: 20px; }
    .project-card { background-color: #F3F4F6; padding: 20px; border-radius: 10px; margin-bottom: 10px; cursor: pointer; border: 1px solid #E5E7EB; }
    .correct { color: #10B981; font-weight: bold; }
    .stTextArea textarea { height: 100px; }
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

# 세션 상태 초기화
if 'vdb' not in st.session_state: st.session_state.vdb = load_db()
if 'view' not in st.session_state: st.session_state.view = "list" # list, create, study
if 'selected_project' not in st.session_state: st.session_state.selected_project = None

# --- 워드 파싱 함수 ---
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
            current = {"word": text, "meaning": "", "sentences": []}
    if current: data.append(current)
    return data

# --- 사이드바 (내비게이션) ---
with st.sidebar:
    st.title("📚 학습 메뉴")
    if st.button("➕ 새 프로젝트 만들기", use_container_width=True):
        st.session_state.view = "create"
        st.rerun()
    
    st.write("---")
    st.subheader("📁 내 프로젝트 목록")
    if not st.session_state.vdb:
        st.write("생성된 프로젝트가 없습니다.")
    for p_name in st.session_state.vdb.keys():
        if st.button(f"📖 {p_name}", key=f"nav_{p_name}", use_container_width=True):
            st.session_state.selected_project = p_name
            st.session_state.view = "study"
            st.rerun()

# --- 메인 화면 로직 ---

# 1. 프로젝트 리스트 화면 (초기 화면)
if st.session_state.view == "list":
    st.markdown("<div class='main-title'>나의 프로젝트 리스트</div>", unsafe_allow_html=True)
    if not st.session_state.vdb:
        st.info("아직 프로젝트가 없습니다. 왼쪽 상단의 '새 프로젝트 만들기'를 클릭하세요!")
    else:
        for p_name in st.session_state.vdb.keys():
            with st.container():
                st.markdown(f"<div class='project-card'><h3>{p_name}</h3></div>", unsafe_allow_html=True)
                if st.button("학습 시작", key=f"start_{p_name}"):
                    st.session_state.selected_project = p_name
                    st.session_state.view = "study"
                    st.rerun()

# 2. 프로젝트 생성 화면
elif st.session_state.view == "create":
    st.markdown("<div class='main-title'>새 프로젝트 생성</div>", unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        method = st.radio("입력 방식 선택", ["파일 업로드", "직접 입력"], horizontal=True)
    
    with st.form("project_form"):
        p_name_input = st.text_input("프로젝트 제목 입력")
        
        # 일정 배분 옵션
        st.write("📅 일정 배분 설정")
        d_col1, d_col2, d_col3 = st.columns(3)
        dist_mode = d_col1.selectbox("배분 기준", ["총 일수 직접 입력", "캘린더(시작/종료) 선택", "1일 분량 입력"])
        
        start_date = datetime.now()
        days_to_set = 7
        per_day_limit = 10
        
        if dist_mode == "총 일수 직접 입력":
            days_to_set = d_col2.number_input("목표 일수(일)", min_value=1, value=7)
        elif dist_mode == "캘린더(시작/종료) 선택":
            s_d = d_col2.date_input("시작일", datetime.now())
            e_d = d_col3.date_input("종료일", datetime.now() + timedelta(days=6))
            days_to_set = (e_d - s_d).days + 1
            start_date = s_d
        else:
            start_date = d_col2.date_input("학습 시작일", datetime.now())
            per_day_limit = d_col3.number_input("하루 어휘량", min_value=1, value=10)

        final_data = []
        if method == "파일 업로드":
            f_type = st.selectbox("파일 종류", ["docx (워드)", "csv", "xlsx"])
            uploaded_file = st.file_uploader(f"파일 선택 ({f_type})")
            if uploaded_file and f_type == "docx (워드)":
                parsed = parse_word_file(uploaded_file)
                # 미리보기 형태만 저장 (폼 제출 시 처리)
                final_data = parsed
        else:
            st.write("어휘 및 예문 직접 입력")
            # 텍스트 에디터 방식으로 변경 (멀티라인 예문 지원)
            raw_input = st.text_area("형식: 단어|뜻|예문1 (줄바꿈) 예문2\n(한 줄에 한 단어씩 입력하세요)", 
                                     placeholder="apple|사과|I like apple.\nIt is red.\nbanana|바나나|Banana is long.")

        if st.form_submit_button("🚀 프로젝트 생성 완료"):
            # 데이터 가공
            process_list = []
            if method == "파일 업로드" and final_data:
                process_list = final_data
            elif method == "직접 입력" and raw_input:
                lines = raw_input.split('\n')
                curr = None
                for line in lines:
                    if '|' in line:
                        if curr: process_list.append(curr)
                        parts = line.split('|')
                        curr = {"word": parts[0].strip(), "meaning": parts[1].strip(), "sentences": [parts[2].strip()] if len(parts)>2 else []}
                    elif curr and line.strip():
                        curr["sentences"].append(line.strip())
                if curr: process_list.append(curr)

            if p_name_input and process_list:
                # 날짜 배분
                total = len(process_list)
                if dist_mode == "1일 분량 입력":
                    days_to_set = (total // per_day_limit) + (1 if total % per_day_limit > 0 else 0)
                
                base = total // days_to_set
                project_days = {}
                for i in range(days_to_set):
                    d_str = (start_date + timedelta(days=i)).strftime("%Y-%m-%d")
                    s_idx, e_idx = i * base, (i+1) * base if i < days_to_set-1 else total
                    project_days[d_str] = process_list[s_idx:e_idx]
                
                # 저장 및 이동
                st.session_state.vdb[p_name_input] = project_days
                save_db(st.session_state.vdb)
                st.session_state.view = "list"
                st.success("프로젝트가 생성되었습니다!")
                st.rerun()

# 3. 프로젝트 학습 화면
elif st.session_state.view == "study":
    p_name = st.session_state.selected_project
    p_data = st.session_state.vdb[p_name]
    
    st.markdown(f"<div class='main-title'>📖 {p_name} 학습</div>", unsafe_allow_html=True)
    
    sel_date = st.selectbox("학습 날짜 선택", list(p_data.keys()))
    day_voca = p_data[sel_date]
    
    # 상단 옵션
    o1, o2, o3 = st.columns(3)
    h_w = o1.checkbox("단어 가리기")
    h_m = o2.checkbox("뜻 가리기")
    sort_un = o3.checkbox("미완료 어휘 상단 정렬")

    display_list = sorted(day_voca, key=lambda x: x.get('solved', False)) if sort_un else day_voca

    # 테이블 구현
    st.write("---")
    header = st.columns([2, 3, 2, 1])
    header[0].write("**영문 어휘**")
    header[1].write("**한국어 의미**")
    header[2].write("**문장 연습**")
    header[3].write("**완료**")
    
    for idx, v in enumerate(display_list):
        r = st.columns([2, 3, 2, 1])
        # 어휘
        if h_w:
            ans_w = r[0].text_input("입력", key=f"w_{idx}", label_visibility="collapsed")
            if ans_w.lower() == v['word'].lower(): r[0].markdown(f"<span class='correct'>{v['word']}</span>", unsafe_allow_html=True)
        else: r[0].write(v['word'])
        # 의미
        if h_m:
            ans_m = r[1].text_input("입력", key=f"m_{idx}", label_visibility="collapsed")
            if ans_m in v['meaning']: r[1].markdown(f"<span class='correct'>{v['meaning']}</span>", unsafe_allow_html=True)
        else: r[1].write(v['meaning'])
        # 예문 버튼
        if r[2].button("📝 문장 연습", key=f"btn_{idx}"):
            st.session_state.active_word = v
        # 완료
        v['solved'] = r[3].checkbox("", value=v.get('solved', False), key=f"chk_{idx}")

    # 예문 연습 영역 (클릭 시 하단 표시)
    if 'active_word' in st.session_state:
        st.write("---")
        aw = st.session_state.active_word
        st.subheader(f"🔍 '{aw['word']}' 문장 드릴링")
        hide_target = st.checkbox("문장 내 단어 가리기", value=True)
        for si, s in enumerate(aw['sentences']):
            if hide_target:
                pattern = re.compile(re.escape(aw['word']), re.IGNORECASE)
                masked = pattern.sub("__________", s)
                st.write(f"{si+1}. {masked}")
                user_in = st.text_input("단어 입력", key=f"si_{si}", label_visibility="collapsed")
                if user_in.lower() == aw['word'].lower(): st.success("Correct!")
            else: st.info(f"{si+1}. {s}")
        if st.button("닫기"):
            del st.session_state.active_word
            st.rerun()
