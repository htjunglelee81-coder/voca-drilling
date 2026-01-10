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

# --- [핵심] 고성능 워드 파서 ---
def parse_word_file_v2(file):
    doc = Document(file)
    data = []
    current_entry = None
    
    for para in doc.paragraphs:
        text = para.text.strip()
        if not text: continue
        
        # 1. 예문인 경우 (숫자로 시작하는 패턴: 1. 2) 20) 등)
        if re.match(r'^\d+[\.\)]', text):
            if current_entry:
                clean_sent = re.sub(r'^\d+[\.\)]', '', text).strip()
                current_entry["sentences"].append(clean_sent)
        
        # 2. 뜻 정보인 경우 (Korean: 단어가 포함된 경우)
        elif "Korean:" in text:
            if current_entry:
                # 'Korean: 뜻 answer: 정답' 형태에서 뜻만 추출
                meaning_match = re.search(r"Korean:\s*(.*?)(?:\s*answer:|$)", text)
                if meaning_match:
                    current_entry["meaning"] = meaning_match.group(1).strip()
        
        # 3. 새로운 단어인 경우 (영문자로 시작하고 짧은 줄)
        elif re.match(r'^[a-zA-Z\s\-]+$', text) and len(text.split()) <= 3:
            if current_entry:
                data.append(current_entry)
            current_entry = {"word": text, "meaning": "", "sentences": [], "solved": False}
            
    if current_entry:
        data.append(current_entry)
    return data

# --- 사이드바 및 내비게이션 (이전과 동일) ---
with st.sidebar:
    st.title("📂 Voca Manager")
    if st.button("➕ 새 프로젝트 만들기", use_container_width=True):
        st.session_state.view = "create"
        st.rerun()
    st.write("---")
    for p_name in list(st.session_state.vdb.keys()):
        if st.button(f"📖 {p_name}", key=f"nav_{p_name}", use_container_width=True):
            st.session_state.selected_project = p_name
            st.session_state.view = "study"
            st.session_state.active_word_info = None
            st.rerun()

# --- 메인 로직: 생성 및 학습 ---
if st.session_state.view == "list":
    st.title("나의 프로젝트")
    for p_name in st.session_state.vdb.keys():
        if st.button(f"'{p_name}' 학습 시작", key=f"list_{p_name}"):
            st.session_state.selected_project = p_name
            st.session_state.view = "study"
            st.rerun()

elif st.session_state.view == "create":
    st.title("🛠 프로젝트 생성")
    with st.form("create_form"):
        p_name = st.text_input("프로젝트 이름")
        f = st.file_uploader("day15.docx 파일을 올려주세요", type=['docx'])
        d_col1, d_col2 = st.columns(2)
        start_d = d_col1.date_input("시작일", datetime.now().date())
        days = d_col2.number_input("목표 일수", min_value=1, value=1)
        
        if st.form_submit_button("🚀 프로젝트 생성"):
            if f and p_name:
                raw_data = parse_word_file_v2(f)
                # 날짜 배분 (생략되지 않게 전체 데이터 넣기)
                st.session_state.vdb[p_name] = {start_d.strftime("%Y-%m-%d"): raw_data}
                save_db(st.session_state.vdb)
                st.session_state.view = "list"
                st.rerun()

elif st.session_state.view == "study":
    p_name = st.session_state.selected_project
    p_data = st.session_state.vdb[p_name]
    sel_date = st.selectbox("날짜 선택", list(p_data.keys()))
    day_voca = p_data[sel_date]

    # 학습 테이블
    for idx, v in enumerate(day_voca):
        cols = st.columns([2, 3, 2, 1])
        cols[0].write(f"**{v['word']}**")
        cols[1].write(v['meaning'])
        if cols[2].button("📝 문장 연습", key=f"btn_{v['word']}"):
            st.session_state.active_word_info = v
        v['solved'] = cols[3].checkbox("완료", value=v.get('solved', False), key=f"chk_{v['word']}")

    # [수정 확인] 문장 드릴링 섹션
    if st.session_state.active_word_info:
        aw = st.session_state.active_word_info
        st.write("---")
        st.subheader(f"🔍 '{aw['word']}' 문장 드릴링 (총 {len(aw['sentences'])}개)")
        
        if not aw['sentences']:
            st.warning("데이터 파싱 오류: 예문을 찾지 못했습니다. 파일 양식을 확인해주세요.")
        else:
            for si, sent in enumerate(aw['sentences']):
                # 대소문자 무시하고 빈칸 치환
                pattern = re.compile(re.escape(aw['word']), re.IGNORECASE)
                masked = pattern.sub("__________", sent)
                
                st.info(f"Sentence {si+1}: {masked}")
                ans = st.text_input("단어 입력", key=f"drill_{aw['word']}_{si}")
                if ans.lower() == aw['word'].lower():
                    st.success("Correct!")
        
        if st.button("닫기"):
            st.session_state.active_word_info = None
            st.rerun()
