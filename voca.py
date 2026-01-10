import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import re
import json
import os

try:
    from docx import Document
except ImportError:
    st.error("라이브러리 미설치: pip install python-docx")

# --- 설정 ---
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

# --- [정밀] 워드 파서 (day15.docx 예문 20개 추출용) ---
def parse_docx_final(file):
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
        # 3. 새로운 단어 (영문자 위주 짧은 줄)
        elif re.match(r'^[a-zA-Z\s\-]+$', text) and len(text.split()) <= 4:
            if current_entry: data.append(current_entry)
            current_entry = {"word": text, "meaning": "뜻 없음", "sentences": [], "solved": False}
            
    if current_entry: data.append(current_entry)
    return data

# --- 사이드바 (프로젝트 리스트 및 확실한 삭제 버튼) ---
with st.sidebar:
    st.title("📚 Voca Master")
    if st.button("➕ 새 프로젝트 만들기", use_container_width=True):
        st.session_state.view = "create"; st.rerun()
    st.write("---")
    st.subheader("📁 내 프로젝트")
    for p_name in list(st.session_state.vdb.keys()):
        # 삭제 버튼이 잘 보이도록 컬럼 비율 조정
        side_col1, side_col2 = st.columns([5, 1])
        if side_col1.button(f"📖 {p_name}", key=f"s_{p_name}", use_container_width=True):
            st.session_state.selected_p = p_name
            st.session_state.view = "study"
            st.session_state.active_word_info = None
            st.rerun()
        if side_col2.button("🗑️", key=f"del_{p_name}"):
            del st.session_state.vdb[p_name]
            save_db(st.session_state.vdb)
            st.rerun()

# --- 1. 메인 목록 ---
if st.session_state.view == "list":
    st.title("나의 학습 보드")
    if not st.session_state.vdb:
        st.info("왼쪽 사이드바의 '새 프로젝트 만들기'를 눌러주세요.")
    else:
        for p_name in st.session_state.vdb.keys():
            st.success(f"**{p_name}** 프로젝트가 활성화 되어 있습니다.")

# --- 2. 생성 화면 (직접 입력 탭 및 날짜 옵션 복구) ---
elif st.session_state.view == "create":
    st.title("🛠 새 프로젝트 생성")
    
    # 1. 배분 설정 (Form 외부)
    dist_mode = st.selectbox("어휘 배분 방식", ["총 일수 직접 입력", "캘린더(시작/종료일) 선택", "1일 학습량(개수) 지정"])
    
    with st.form("create_voca_form"):
        p_title = st.text_input("프로젝트 이름")
        
        c1, c2 = st.columns(2)
        start_date = c1.date_input("학습 시작일", datetime.now().date())
        
        target_days = 1
        v_per_day = 20
        if dist_mode == "총 일수 직접 입력":
            target_days = c2.number_input("목표 일수(일)", min_value=1, value=5)
        elif dist_mode == "캘린더(시작/종료일) 선택":
            end_date = c2.date_input("종료일", start_date + timedelta(days=6))
            target_days = (end_date - start_date).days + 1
        else:
            v_per_day = c2.number_input("하루 단어 개수", min_value=1, value=20)

        # 2. 입력 방식 선택
        st.write("---")
        input_method = st.radio("입력 방식 선택", ["Word 파일 업로드", "텍스트 직접 입력"], horizontal=True)
        
        up_file = None
        direct_text = ""
        if input_method == "Word 파일 업로드":
            up_file = st.file_uploader("day15.docx 등 업로드", type=['docx'])
        else:
            direct_text = st.text_area("단어|뜻|예문 (엔터로 예문 추가)", height=200)

        if st.form_submit_button("🚀 프로젝트 생성하기"):
            raw_voca = []
            if input_method == "Word 파일 업로드" and up_file:
                raw_voca = parse_docx_final(up_file)
            elif direct_text:
                # 직접 입력 파싱
                lines = direct_text.split('\n')
                curr = None
                for l in lines:
                    if '|' in l:
                        if curr: raw_voca.append(curr)
                        p = l.split('|')
                        curr = {"word": p[0].strip(), "meaning": p[1].strip() if len(p)>1 else "", "sentences": [p[2].strip()] if len(p)>2 else [], "solved": False}
                    elif curr and l.strip(): curr["sentences"].append(l.strip())
                if curr: raw_voca.append(curr)

            if p_title and raw_voca:
                total_v = len(raw_voca)
                if dist_mode == "1일 학습량(개수) 지정":
                    target_days = (total_v // v_per_day) + (1 if total_v % v_per_day > 0 else 0)
                
                chunk = max(1, (total_v // target_days) + (1 if total_v % target_days > 0 else 0))
                p_db = {}
                for i in range(target_days):
                    d_key = (start_date + timedelta(days=i)).strftime("%Y-%m-%d")
                    p_db[d_key] = raw_voca[i*chunk : (i+1)*chunk]
                
                st.session_state.vdb[p_title] = p_db
                save_db(st.session_state.vdb)
                st.session_state.view = "list"; st.rerun()

# --- 3. 학습 화면 ---
elif st.session_state.view == "study":
    p_name = st.session_state.selected_p
    p_data = st.session_state.vdb[p_name]
    
    st.title(f"📖 {p_name}")
    col_sel, col_btn = st.columns([3, 1])
    sel_date = col_sel.selectbox("날짜 선택", list(p_data.keys()))
    if col_btn.button("🏠 홈으로", use_container_width=True):
        st.session_state.view = "list"; st.rerun()

    day_voca = p_data[sel_date]
    o1, o2, o3 = st.columns(3)
    hide_w, hide_m = o1.checkbox("단어 가리기"), o2.checkbox("뜻 가리기")
    sort_un = o3.checkbox("미완료 어휘 상단 정렬")

    display_list = sorted(day_voca, key=lambda x: x.get('solved', False)) if sort_un else day_voca

    st.write("---")
    h = st.columns([2, 3, 2, 1])
    h[0].write("**영문 어휘**"); h[1].write("**한국어 의미**"); h[2].write("**연습**"); h[3].write("**완료**")

    for idx, v in enumerate(display_list):
        r = st.columns([2, 3, 2, 1])
        # 단어/뜻 가리기 입력창
        if hide_w:
            if r[0].text_input("w", key=f"w_{v['word']}", label_visibility="collapsed").lower() == v['word'].lower():
                r[0].success(f"{v['word']} ✓")
        else: r[0].write(f"**{v['word']}**")
        
        if hide_m:
            if r[1].text_input("m", key=f"m_{v['word']}", label_visibility="collapsed") in v['meaning']:
                r[1].success(f"{v['meaning']} ✓")
        else: r[1].write(v['meaning'])
        
        if r[2].button("📝 문장", key=f"btn_{v['word']}"):
            st.session_state.active_word_info = v; st.rerun()
            
        orig_idx = next(i for i, item in enumerate(day_voca) if item['word'] == v['word'])
        v['solved'] = r[3].checkbox("V", value=v.get('solved', False), key=f"chk_{v['word']}", label_visibility="collapsed")
        if v['solved'] != day_voca[orig_idx]['solved']:
            day_voca[orig_idx]['solved'] = v['solved']
            save_db(st.session_state.vdb); st.rerun()

    # 문장 연습 (이 부분에서 alley 예문 20개가 나와야 함)
    if st.session_state.active_word_info:
        aw = st.session_state.active_word_info
        st.write("---")
        st.subheader(f"🔍 '{aw['word']}' 문장 드릴링 (총 {len(aw['sentences'])}개)")
        if not aw['sentences']:
            st.warning("예문을 불러오지 못했습니다. 파싱 로직을 점검하세요.")
        else:
            for si, sent in enumerate(aw['sentences']):
                pattern = re.compile(re.escape(aw['word']), re.IGNORECASE)
                masked = pattern.sub("__________", sent)
                st.info(f"{si+1}. {masked}")
                if st.text_input("답", key=f"dr_{aw['word']}_{si}", label_visibility="collapsed").lower() == aw['word'].lower():
                    st.success("Correct!")
        if st.button("❌ 닫기"):
            st.session_state.active_word_info = None; st.rerun()
