import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import re
import json
import os
from docx import Document

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
            current = {"word": text, "meaning": "", "sentences": [], "solved": False}
    if current: data.append(current)
    return data

# --- 사이드바 ---
with st.sidebar:
    st.title("📚 학습 메뉴")
    if st.button("➕ 새 프로젝트 만들기", use_container_width=True):
        st.session_state.view = "create"
        st.rerun()
    st.write("---")
    st.subheader("📁 내 프로젝트 목록")
    for p_name in list(st.session_state.vdb.keys()):
        if st.button(f"📖 {p_name}", key=f"nav_{p_name}", use_container_width=True):
            st.session_state.selected_project = p_name
            st.session_state.view = "study"
            st.session_state.active_word_info = None
            st.rerun()

# --- 메인 로직 ---

# 1. 리스트 화면
if st.session_state.view == "list":
    st.title("나의 프로젝트 리스트")
    if not st.session_state.vdb:
        st.info("왼쪽 상단의 '새 프로젝트 만들기'를 클릭하여 시작하세요.")
    else:
        cols = st.columns(3)
        for idx, p_name in enumerate(st.session_state.vdb.keys()):
            with cols[idx % 3]:
                st.info(f"### {p_name}")
                if st.button("학습 시작", key=f"main_{p_name}"):
                    st.session_state.selected_project = p_name
                    st.session_state.view = "study"
                    st.rerun()

# 2. 생성 화면
elif st.session_state.view == "create":
    st.title("🛠 새 프로젝트 생성")
    
    # Form 밖에서 옵션을 먼저 선택하게 하여 UI를 즉시 갱신
    method = st.radio("입력 방식 선택", ["파일 업로드(Word)", "직접 입력"], horizontal=True)
    dist_mode = st.selectbox("배분 기준 설정", ["총 일수 직접 입력", "캘린더 기간 선택", "1일 분량 입력"])
    
    with st.form("create_project_form"):
        p_name_input = st.text_input("프로젝트 제목")
        
        # [수정] 배분 기준에 따른 동적 입력창
        start_date = datetime.now().date()
        target_days = 1
        per_day_count = 10
        
        d_col1, d_col2 = st.columns(2)
        if dist_mode == "총 일수 직접 입력":
            start_date = d_col1.date_input("학습 시작일", datetime.now().date())
            target_days = d_col2.number_input("목표 일수(일)", min_value=1, value=7)
        elif dist_mode == "캘린더 기간 선택":
            s_date = d_col1.date_input("시작일", datetime.now().date())
            e_date = d_col2.date_input("종료일", datetime.now().date() + timedelta(days=6))
            start_date = s_date
            target_days = (e_date - s_date).days + 1
        else: # 1일 분량 입력
            start_date = d_col1.date_input("학습 시작일", datetime.now().date())
            per_day_count = d_col2.number_input("하루 학습 어휘 수", min_value=1, value=20)

        # 데이터 입력
        raw_data = []
        if method == "파일 업로드(Word)":
            f = st.file_uploader("워드 파일 선택", type=['docx'])
            # 폼 제출 시 처리를 위해 세션이나 변수에 담음
        else:
            txt_input = st.text_area("단어|뜻|예문 형식 (엔터로 예문 추가)", height=250, 
                                     placeholder="apple|사과|I like apple.\nIt is red.\nbanana|바나나|Banana is yellow.")

        submit = st.form_submit_button("🚀 프로젝트 생성 및 어휘 배분")
        
        if submit:
            # 1. 데이터 파싱
            if method == "파일 업로드(Word)" and f:
                raw_data = parse_word_file(f)
            elif method == "직접 입력" and txt_input:
                lines = txt_input.split('\n')
                curr = None
                for l in lines:
                    if '|' in l:
                        if curr: raw_data.append(curr)
                        p = l.split('|')
                        curr = {"word": p[0].strip(), "meaning": p[1].strip(), "sentences": [p[2].strip()] if len(p)>2 else [], "solved": False}
                    elif curr and l.strip(): curr["sentences"].append(l.strip())
                if curr: raw_data.append(curr)

            if not p_name_input:
                st.error("프로젝트 이름을 입력해주세요.")
            elif not raw_data:
                st.error("입력된 어휘 데이터가 없습니다.")
            else:
                # 2. 날짜 배분 로직
                total_v = len(raw_data)
                if dist_mode == "1일 분량 입력":
                    target_days = (total_v // per_day_count) + (1 if total_v % per_day_count > 0 else 0)
                
                if target_days < 1: target_days = 1
                
                base_cnt = total_v // target_days
                project_days = {}
                
                for i in range(target_days):
                    current_d_str = (start_date + timedelta(days=i)).strftime("%Y-%m-%d")
                    start_idx = i * base_cnt
                    # 마지막 날에 나머지 몰아넣기
                    end_idx = (i + 1) * base_cnt if i < target_days - 1 else total_v
                    project_days[current_d_str] = raw_data[start_idx:end_idx]
                
                # 3. 저장 및 리다이렉트
                st.session_state.vdb[p_name_input] = project_days
                save_db(st.session_state.vdb)
                st.session_state.view = "list"
                st.rerun()

# 3. 학습 화면 (수정 완료 버전)
elif st.session_state.view == "study":
    p_name = st.session_state.selected_project
    p_data = st.session_state.vdb[p_name]
    
    st.title(f"📖 {p_name}")
    c1, c2 = st.columns([2, 1])
    sel_date = c1.selectbox("날짜 선택", list(p_data.keys()))
    if c2.button("🏠 목록으로", use_container_width=True):
        st.session_state.view = "list"
        st.rerun()

    day_voca = p_data[sel_date]
    
    # 학습 도구 옵션
    o1, o2, o3 = st.columns(3)
    hide_w = o1.checkbox("단어 가리기")
    hide_m = o2.checkbox("뜻 가리기")
    sort_un = o3.checkbox("미완료 어휘 상단 정렬")

    display_list = sorted(day_voca, key=lambda x: x.get('solved', False)) if sort_un else day_voca

    st.write("---")
    # 테이블 헤더
    h = st.columns([2, 3, 2, 1])
    h[0].write("**영문 어휘**"); h[1].write("**한국어 의미**"); h[2].write("**문장 연습**"); h[3].write("**완료**")

    for idx, v in enumerate(display_list):
        # 고유 키 생성을 위해 원본 인덱스 확인
        orig_idx = next(i for i, item in enumerate(day_voca) if item['word'] == v['word'])
        r = st.columns([2, 3, 2, 1])
        
        # 어휘 열
        if hide_w:
            u_w = r[0].text_input("단어입력", key=f"w_in_{v['word']}", label_visibility="collapsed")
            if u_w.lower() == v['word'].lower():
                r[0].markdown(f"<span style='color:#10B981; font-weight:bold;'>{v['word']} ✓</span>", unsafe_allow_html=True)
        else: r[0].write(f"**{v['word']}**")
        
        # 의미 열
        if hide_m:
            u_m = r[1].text_input("뜻입력", key=f"m_in_{v['word']}", label_visibility="collapsed")
            if u_m and u_m in v['meaning']:
                r[1].markdown(f"<span style='color:#10B981; font-weight:bold;'>{v['meaning']} ✓</span>", unsafe_allow_html=True)
        else: r[1].write(v['meaning'])
        
        # 문장 연습 버튼
        if r[2].button("📝 연습", key=f"btn_{v['word']}"):
            st.session_state.active_word_info = v
            st.rerun()
            
        # 완료 체크 (정렬 오류 해결)
        is_done = r[3].checkbox("Done", value=v.get('solved', False), key=f"chk_{v['word']}", label_visibility="collapsed")
        if is_done != day_voca[orig_idx].get('solved'):
            day_voca[orig_idx]['solved'] = is_done
            save_db(st.session_state.vdb)
            st.rerun()

    # 문장 드릴링 섹션
    if st.session_state.active_word_info:
        aw = st.session_state.active_word_info
        st.write("---")
        st.subheader(f"🔍 '{aw['word']}' 문장 드릴링")
        for si, sent in enumerate(aw['sentences']):
            pattern = re.compile(re.escape(aw['word']), re.IGNORECASE)
            masked = pattern.sub("__________", sent)
            st.info(f"문장 {si+1}: {masked}")
            u_drill = st.text_input("단어 입력", key=f"drill_{aw['word']}_{si}")
            if u_drill.lower() == aw['word'].lower():
                st.success("정답입니다! ✓")
        if st.button("닫기"):
            st.session_state.active_word_info = None
            st.rerun()
