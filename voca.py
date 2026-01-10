import streamlit as st
from docx import Document
import re
import json
import os
from datetime import datetime, timedelta

# --- 페이지 설정 ---
st.set_page_config(page_title="Voca Master Pro", layout="wide")

# --- 스타일 (뜻 가리기 시 정답 글자색 등) ---
st.markdown("""
    <style>
    .ans-correct { color: #10B981; font-weight: bold; margin-top: 5px; }
    .drill-box { background-color: #f8fafc; padding: 20px; border: 2px solid #1e40af; border-radius: 10px; margin: 15px 0; }
    .sentence-card { background: white; padding: 10px; border-radius: 5px; margin-bottom: 8px; border-left: 5px solid #1e40af; box-shadow: 1px 1px 3px rgba(0,0,0,0.1); }
    </style>
    """, unsafe_allow_html=True)

# --- DB 로직 ---
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
if 'drill_word' not in st.session_state: st.session_state.drill_word = None

# --- [정밀 파서] day15.docx 구조 100% 대응 ---
def parse_docx_final(file):
    doc = Document(file)
    words_list = []
    current_item = None

    for para in doc.paragraphs:
        text = para.text.strip()
        if not text: continue

        # 1. 예문인 경우 (숫자로 시작)
        if re.match(r'^\d+[\.\)]', text):
            if current_item:
                clean_s = re.sub(r'^\d+[\.\)]', '', text).strip()
                current_item["sentences"].append(clean_s)
        
        # 2. 뜻인 경우 (Korean: 포함)
        elif "Korean:" in text:
            if current_item:
                meaning_part = text.split("Korean:")[1].split("answer:")[0].strip()
                current_item["meaning"] = meaning_part
        
        # 3. 새로운 단어인 경우 (영문자로만 구성됨)
        elif re.match(r'^[a-zA-Z\s\-]+$', text) and len(text.split()) <= 4:
            if current_item:
                words_list.append(current_item)
            current_item = {"word": text, "meaning": "", "sentences": [], "solved": False}

    if current_item: words_list.append(current_item)
    return words_list

# --- 사이드바 ---
with st.sidebar:
    st.title("📂 Voca Master")
    if st.button("➕ 새 프로젝트 만들기", use_container_width=True):
        st.session_state.view = "create"; st.rerun()
    st.write("---")
    for p_name in list(st.session_state.vdb.keys()):
        col_p, col_d = st.columns([4, 1])
        if col_p.button(f"📖 {p_name}", key=f"p_{p_name}", use_container_width=True):
            st.session_state.selected_p = p_name
            st.session_state.view = "study"
            st.session_state.drill_word = None
            st.rerun()
        if col_d.button("🗑️", key=f"d_{p_name}"):
            del st.session_state.vdb[p_name]
            save_db(st.session_state.vdb); st.rerun()

# --- 1. 목록 화면 ---
if st.session_state.view == "list":
    st.title("학습 목록")
    if not st.session_state.vdb: st.info("새 프로젝트를 생성해주세요.")
    else:
        for p in st.session_state.vdb.keys():
            if st.button(f"'{p}' 시작하기"):
                st.session_state.selected_p = p; st.session_state.view = "study"; st.rerun()

# --- 2. 생성 화면 (직접 입력 복구 및 모든 옵션 유지) ---
elif st.session_state.view == "create":
    st.title("🛠 프로젝트 생성")
    tab1, tab2 = st.tabs(["📄 파일 업로드", "⌨️ 직접 텍스트 입력"])
    
    with st.form("create_form"):
        p_name = st.text_input("프로젝트 이름")
        dist_mode = st.selectbox("배분 방식", ["총 일수", "기간 선택", "하루 개수"])
        c1, c2 = st.columns(2)
        start_d = c1.date_input("시작일")
        dist_val = c2.number_input("설정값(일수 또는 개수)", min_value=1, value=5)
        
        # 탭별 데이터 소스
        up_file = None
        if tab1: up_file = st.file_uploader("Word 파일(.docx)", type=['docx'])
        txt_data = tab2.text_area("단어|뜻|예문 (줄바꿈으로 예문 추가)")

        if st.form_submit_button("🚀 생성"):
            data = []
            if up_file: data = parse_docx_final(up_file)
            elif txt_data:
                for line in txt_data.split('\n'):
                    if '|' in line:
                        p = line.split('|')
                        data.append({"word": p[0].strip(), "meaning": p[1].strip(), "sentences": [p[2].strip()] if len(p)>2 else [], "solved": False})
                    elif data and line.strip(): data[-1]["sentences"].append(line.strip())
            
            if p_name and data:
                # 배분 로직
                days = dist_val if dist_mode != "하루 개수" else (len(data)//dist_val + 1)
                chunk = (len(data)//days) + 1
                new_db = {}
                for i in range(int(days)):
                    d_key = (start_d + timedelta(days=i)).strftime("%Y-%m-%d")
                    new_db[d_key] = data[i*chunk : (i+1)*chunk]
                    if not new_db[d_key]: break
                st.session_state.vdb[p_name] = new_db
                save_db(st.session_state.vdb); st.session_state.view = "list"; st.rerun()

# --- 3. 학습 화면 ---
elif st.session_state.view == "study":
    p_name = st.session_state.selected_p
    p_data = st.session_state.vdb[p_name]
    sel_date = st.selectbox("날짜 선택", list(p_data.keys()))
    day_voca = p_data[sel_date]

    o1, o2, o3 = st.columns(3)
    hide_w = o1.checkbox("단어 가리기")
    hide_m = o2.checkbox("뜻 가리기")
    sort_un = o3.checkbox("미완료 어휘 상단 정렬")

    display_list = sorted(day_voca, key=lambda x: x.get('solved', False)) if sort_un else day_voca

    st.write("---")
    header = st.columns([2, 3, 2, 1])
    header[0].write("**영문 어휘**"); header[1].write("**의미**"); header[2].write("**연습**"); header[3].write("**완료**")

    for idx, v in enumerate(display_list):
        r = st.columns([2, 3, 2, 1])
        # 단어
        if hide_w:
            user_w = r[0].text_input("w", key=f"win_{v['word']}", label_visibility="collapsed")
            if user_w.lower() == v['word'].lower(): r[0].markdown(f"<p class='ans-correct'>{v['word']} ✓</p>", unsafe_allow_html=True)
        else: r[0].write(f"**{v['word']}**")
        
        # 뜻 (오류 수정: 정답 입력 시에만 노출)
        if hide_m:
            user_m = r[1].text_input("m", key=f"min_{v['word']}", label_visibility="collapsed")
            if user_m and user_m in v['meaning']: r[1].markdown(f"<p class='ans-correct'>{v['meaning']} ✓</p>", unsafe_allow_html=True)
        else: r[1].write(v['meaning'])
        
        # 문장 연습 버튼 (옆에 예문 개수 표시하여 파싱 확인)
        if r[2].button(f"📝 연습 ({len(v['sentences'])})", key=f"btn_{v['word']}"):
            st.session_state.drill_word = v['word']
            
        # 완료 체크
        orig_idx = next(i for i, item in enumerate(day_voca) if item['word'] == v['word'])
        v['solved'] = r[3].checkbox("V", value=v.get('solved', False), key=f"chk_{v['word']}", label_visibility="collapsed")
        if v['solved'] != day_voca[orig_idx]['solved']:
            day_voca[orig_idx]['solved'] = v['solved']
            save_db(st.session_state.vdb); st.rerun()

        # [테이블 생성 로직] 해당 단어 바로 아래에 드릴링 섹션
        if st.session_state.drill_word == v['word']:
            with st.container():
                st.markdown(f"<div class='drill-box'>", unsafe_allow_html=True)
                st.subheader(f"🔍 '{v['word']}' 문장 드릴링")
                if not v['sentences']:
                    st.warning("이 단어는 예문이 없습니다.")
                else:
                    for si, sent in enumerate(v['sentences']):
                        st.markdown(f"<div class='sentence-card'>", unsafe_allow_html=True)
                        masked = re.compile(re.escape(v['word']), re.IGNORECASE).sub("__________", sent)
                        st.write(f"**{si+1}.** {masked}")
                        ans = st.text_input("정답", key=f"ans_{v['word']}_{si}", label_visibility="collapsed")
                        if ans.lower() == v['word'].lower(): st.success("Correct!")
                        st.markdown("</div>", unsafe_allow_html=True)
                if st.button("닫기", key=f"close_{v['word']}"):
                    st.session_state.drill_word = None; st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)
