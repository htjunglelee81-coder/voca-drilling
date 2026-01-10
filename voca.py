import streamlit as st
from docx import Document
import re
import json
import os
from datetime import datetime, timedelta

st.set_page_config(page_title="Voca Master Pro", layout="wide")

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

# --- [인지적 파서] 단어와 다음 단어 사이를 모두 긁어옴 ---
def parse_docx_logic(file):
    doc = Document(file)
    data = []
    current_item = None

    for para in doc.paragraphs:
        text = para.text.strip()
        if not text: continue

        # 1. 단어 판별 (영문 위주, 짧음)
        if re.match(r'^[a-zA-Z\s\-]+$', text) and len(text.split()) <= 3:
            if current_item: data.append(current_item)
            current_item = {"word": text, "meaning": "", "sentences": [], "solved": False}
        
        # 2. 뜻 판별
        elif "Korean:" in text:
            if current_item:
                current_item["meaning"] = text.replace("Korean:", "").strip()
        
        # 3. 나머지는 무조건 현재 단어의 예문으로 간주 (숫자 여부 상관없음)
        else:
            if current_item:
                clean_s = re.sub(r'^\d+[\.\)]', '', text).strip()
                current_item["sentences"].append(clean_s)

    if current_item: data.append(current_item)
    return data

# --- 사이드바 ---
with st.sidebar:
    st.title("📂 Manager")
    if st.button("➕ 새 프로젝트"):
        st.session_state.view = "create"; st.rerun()
    st.write("---")
    for p_name in list(st.session_state.vdb.keys()):
        c1, c2 = st.columns([4, 1])
        if c1.button(f"📖 {p_name}", key=f"p_{p_name}"):
            st.session_state.selected_p = p_name
            st.session_state.view = "study"
            st.session_state.drill_word = None
            st.rerun()
        if c2.button("🗑️", key=f"d_{p_name}"):
            del st.session_state.vdb[p_name]
            save_db(st.session_state.vdb); st.rerun()

# --- 화면 로직 ---
if st.session_state.view == "list":
    st.title("학습 목록")
    if not st.session_state.vdb: st.info("새 프로젝트를 생성하세요.")
    else:
        for p in st.session_state.vdb.keys():
            if st.button(f"'{p}' 입장"):
                st.session_state.selected_p = p; st.session_state.view = "study"; st.rerun()

elif st.session_state.view == "create":
    st.title("🛠 프로젝트 생성")
    tab1, tab2 = st.tabs(["파일 업로드", "직접 입력"])
    with st.form("c_form"):
        p_name = st.text_input("이름")
        dist = st.selectbox("배분", ["총 일수", "하루 개수"])
        val = st.number_input("값", min_value=1, value=5)
        up = st.file_uploader("Word", type=['docx']) if tab1 else None
        if st.form_submit_button("생성"):
            raw = parse_docx_logic(up) if up else []
            if p_name and raw:
                days = val if dist == "총 일수" else (len(raw)//val + 1)
                chunk = (len(raw)//days) + 1
                p_db = {}
                for i in range(int(days)):
                    d_key = (datetime.now() + timedelta(days=i)).strftime("%Y-%m-%d")
                    p_db[d_key] = raw[i*chunk : (i+1)*chunk]
                st.session_state.vdb[p_name] = p_db
                save_db(st.session_state.vdb); st.session_state.view = "list"; st.rerun()

elif st.session_state.view == "study":
    p_name = st.session_state.selected_p
    day_voca = st.session_state.vdb[p_name][st.selectbox("날짜", list(st.session_state.vdb[p_name].keys()))]
    
    h_w, h_m = st.checkbox("단어 가리기"), st.checkbox("뜻 가리기")
    
    for v in day_voca:
        r = st.columns([2, 3, 2, 1])
        # 단어 가리기 로직
        if h_w:
            if r[0].text_input("w", key=f"w_{v['word']}", label_visibility="collapsed").lower() == v['word'].lower():
                r[0].success(v['word'])
        else: r[0].write(v['word'])
        
        # 뜻 가리기 로직 (정답일 때만 출력)
        if h_m:
            u_m = r[1].text_input("m", key=f"m_{v['word']}", label_visibility="collapsed")
            if u_m and u_m in v['meaning']: r[1].success(v['meaning'])
        else: r[1].write(v['meaning'])
        
        if r[2].button(f"📝 문장({len(v['sentences'])})", key=f"b_{v['word']}"):
            st.session_state.drill_word = v['word']
        
        if st.session_state.drill_word == v['word']:
            st.info(f"🔍 {v['word']} 연습")
            for si, sent in enumerate(v['sentences']):
                masked = re.compile(re.escape(v['word']), re.IGNORECASE).sub("____", sent)
                st.write(f"{si+1}. {masked}")
                if st.text_input("답", key=f"a_{v['word']}_{si}", label_visibility="collapsed").lower() == v['word'].lower():
                    st.success("OK")
            if st.button("닫기"): st.session_state.drill_word = None; st.rerun()
