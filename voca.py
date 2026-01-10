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

# --- 스타일 정의 ---
st.markdown("""
    <style>
    .correct-text { color: #10B981; font-weight: bold; }
    .drill-section { background-color: #f8fafc; padding: 20px; border-radius: 10px; border: 2px solid #1e40af; margin-top: 20px; }
    .stButton button { width: 100%; }
    .project-card { padding: 15px; border-radius: 8px; background-color: #f1f5f9; margin-bottom: 10px; }
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

# --- [정밀] 워드 파서 ---
def parse_docx_refined(file):
    doc = Document(file)
    data = []
    current_entry = None
    
    for para in doc.paragraphs:
        text = para.text.strip()
        if not text: continue
        
        # 1. 예문 (숫자로 시작)
        if re.match(r'^\d+[\.\)]', text):
            if current_entry:
                clean_s = re.sub(r'^\d+[\.\)]', '', text).strip()
                current_entry["sentences"].append(clean_s)
        
        # 2. 뜻 (Korean: 포함)
        elif "Korean:" in text:
            if current_entry:
                m = re.search(r"Korean:\s*(.*?)(?:\s*answer:|$)", text)
                current_entry["meaning"] = m.group(1).strip() if m else text.replace("Korean:", "").strip()
        
        # 3. 단어 (영문 위주)
        elif re.match(r'^[a-zA-Z\s\-]+$', text) and len(text.split()) <= 4:
            if current_entry: data.append(current_entry)
            current_entry = {"word": text, "meaning": "뜻 없음", "sentences": [], "solved": False}
            
    if current_entry: data.append(current_entry)
    return data

# --- 사이드바 (프로젝트 리스트 & 삭제) ---
with st.sidebar:
    st.title("📂 Voca Master")
    if st.button("➕ 새 프로젝트 만들기", use_container_width=True):
        st.session_state.view = "create"; st.rerun()
    st.write("---")
    st.subheader("📋 내 프로젝트 목록")
    for p_name in list(st.session_state.vdb.keys()):
        c1, c2 = st.columns([4, 1])
        if c1.button(f"📖 {p_name}", key=f"side_{p_name}", use_container_width=True):
            st.session_state.selected_p = p_name
            st.session_state.view = "study"
            st.session_state.active_word_info = None
            st.rerun()
        if c2.button("🗑️", key=f"del_{p_name}"):
            del st.session_state.vdb[p_name]
            save_db(st.session_state.vdb)
            st.rerun()

# --- 1. 메인 목록 화면 ---
if st.session_state.view == "list":
    st.title("나의 학습 보드")
    if not st.session_state.vdb:
        st.info("왼쪽 메뉴에서 프로젝트를 생성해주세요.")
    else:
        for p_name in st.session_state.vdb.keys():
            with st.container():
                st.markdown(f"<div class='project-card'><h3>{p_name}</h3></div>", unsafe_allow_html=True)
                if st.button(f"학습 시작", key=f"main_{p_name}"):
                    st.session_state.selected_p = p_name
                    st.session_state.view = "study"
                    st.rerun()

# --- 2. 프로젝트 생성 (옵션 3종 완벽 복구) ---
elif st.session_state.view == "create":
    st.title("🛠 프로젝트 생성")
    
    # 옵션 선택 (Form 밖에서 즉시 갱신되도록 설정)
    dist_mode = st.selectbox("과제 배분 방식", ["총 일수 설정", "캘린더(시작/종료일) 선택", "1일 분량 설정"])
    
    with st.form("create_form"):
        p_name = st.text_input("프로젝트 제목")
        up_file = st.file_uploader("워드 파일(.docx) 업로드", type=['docx'])
        
        c1, c2 = st.columns(2)
        start_d = c1.date_input("학습 시작일", datetime.now().date())
        
        # [복구] 조건부 입력창
        days_to_set = 1
        per_day_count = 20
        if dist_mode == "총 일수 설정":
            days_to_set = c2.number_input("목표 일수(일)", min_value=1, value=5)
        elif dist_mode == "캘린더(시작/종료일) 선택":
            end_d = c2.date_input("종료일", start_d + timedelta(days=4))
            days_to_set = (end_d - start_d).days + 1
        else:
            per_day_count = c2.number_input("하루 학습 단어 수", min_value=1, value=20)

        if st.form_submit_button("🚀 프로젝트 생성"):
            if p_name and up_file:
                raw_data = parse_docx_refined(up_file)
                total = len(raw_data)
                
                # 배분 계산
                if dist_mode == "1일 분량 설정":
                    days_to_set = (total // per_day_count) + (1 if total % per_day_count > 0 else 0)
                
                chunk = (total // days_to_set) + (1 if total % days_to_set > 0 else 0)
                project_data = {}
                for i in range(days_to_set):
                    d_str = (start_d + timedelta(days=i)).strftime("%Y-%m-%d")
                    project_data[d_str] = raw_data[i*chunk : (i+1)*chunk]
                
                st.session_state.vdb[p_name] = project_data
                save_db(st.session_state.vdb)
                st.session_state.view = "list"; st.rerun()

# --- 3. 학습 화면 (가리기, 정렬, 드릴링 완벽 통합) ---
elif st.session_state.view == "study":
    p_name = st.session_state.selected_p
    p_data = st.session_state.vdb[p_name]
    
    st.title(f"📖 {p_name}")
    col_a, col_b = st.columns([3, 1])
    sel_date = col_a.selectbox("날짜 선택", list(p_data.keys()))
    if col_b.button("🏠 홈으로", use_container_width=True):
        st.session_state.view = "list"; st.rerun()

    day_voca = p_data[sel_date]
    
    # 옵션 바
    o1, o2, o3 = st.columns(3)
    hide_w = o1.checkbox("단어 가리기")
    hide_m = o2.checkbox("뜻 가리기")
    sort_un = o3.checkbox("미완료 어휘 상단 정렬")

    display_list = sorted(day_voca, key=lambda x: x.get('solved', False)) if sort_un else day_voca

    st.write("---")
    h = st.columns([2, 3, 2, 1])
    h[0].write("**영문 어휘**"); h[1].write("**한국어 의미**"); h[2].write("**문장 연습**"); h[3].write("**완료**")

    for idx, v in enumerate(display_list):
        r = st.columns([2, 3, 2, 1])
        # 단어
        if hide_w:
            in_w = r[0].text_input("w", key=f"win_{v['word']}", label_visibility="collapsed")
            if in_w.lower() == v['word'].lower(): r[0].markdown(f"<span class='correct-text'>{v['word']} ✓</span>", unsafe_allow_html=True)
        else: r[0].write(f"**{v['word']}**")
        # 뜻
        if hide_m:
            in_m = r[1].text_input("m", key=f"min_{v['word']}", label_visibility="collapsed")
            if in_m and in_m in v['meaning']: r[1].markdown(f"<span class='correct-text'>{v['meaning']} ✓</span>", unsafe_allow_html=True)
        else: r[1].write(v['meaning'])
        # 연습 버튼
        if r[2].button("📝 문장 연습", key=f"btn_{v['word']}"):
            st.session_state.active_word_info = v; st.rerun()
        # 완료 체크
        orig_idx = next(i for i, item in enumerate(day_voca) if item['word'] == v['word'])
        v['solved'] = r[3].checkbox("Done", value=v.get('solved', False), key=f"chk_{v['word']}", label_visibility="collapsed")
        if v['solved'] != day_voca[orig_idx]['solved']:
            day_voca[orig_idx]['solved'] = v['solved']
            save_db(st.session_state.vdb); st.rerun()

    # 문장 드릴링 섹션 (alley 예문 20개 출력 보장)
    if st.session_state.active_word_info:
        aw = st.session_state.active_word_info
        st.markdown(f"<div class='drill-section'>", unsafe_allow_html=True)
        st.subheader(f"🔍 '{aw['word']}' 문장 드릴링 (예문 {len(aw['sentences'])}개)")
        
        for si, sent in enumerate(aw['sentences']):
            pattern = re.compile(re.escape(aw['word']), re.IGNORECASE)
            masked = pattern.sub("__________", sent)
            st.write(f"**{si+1}.** {masked}")
            c_in, c_msg = st.columns([4, 1])
            ans = c_in.text_input("단어 입력", key=f"drill_{aw['word']}_{si}", label_visibility="collapsed")
            if ans.lower() == aw['word'].lower(): c_msg.success("Correct!")
            
        if st.button("❌ 연습 창 닫기", use_container_width=True):
            st.session_state.active_word_info = None; st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
