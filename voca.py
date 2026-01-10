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

# --- 설정 및 스타일 ---
st.set_page_config(page_title="Voca Master Pro", layout="wide")
st.markdown("""
    <style>
    .drill-area { background-color: #f0f7ff; padding: 20px; border-radius: 10px; border: 2px solid #007bff; margin: 10px 0; }
    .sentence-row { background: white; padding: 10px; border-radius: 5px; margin-bottom: 5px; box-shadow: 1px 1px 3px rgba(0,0,0,0.1); }
    .correct-ans { color: #28a745; font-weight: bold; }
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
if 'editing_word' not in st.session_state: st.session_state.editing_word = None # 현재 연습 중인 단어 보관

# --- [초강력] 파서: 단어-뜻-예문 연결 보장 ---
def parse_docx_perfect(file):
    doc = Document(file)
    all_data = []
    curr = None
    
    for para in doc.paragraphs:
        t = para.text.strip()
        if not t: continue
        
        # 1. 숫자 예문 (예: 1. 2. 3.)
        if re.match(r'^\d+[\.\)]', t):
            if curr:
                curr["sentences"].append(re.sub(r'^\d+[\.\)]', '', t).strip())
        # 2. 뜻 (Korean:)
        elif "Korean:" in t:
            if curr:
                m = re.search(r"Korean:\s*(.*?)(?:\s*answer:|$)", t)
                curr["meaning"] = m.group(1).strip() if m else t.replace("Korean:", "").strip()
        # 3. 영문 단어 (새 단어 시작)
        elif re.match(r'^[a-zA-Z\s\-]+$', t) and len(t.split()) <= 4:
            if curr: all_data.append(curr)
            curr = {"word": t, "meaning": "뜻 없음", "sentences": [], "solved": False}
            
    if curr: all_data.append(curr)
    return all_data

# --- 사이드바 ---
with st.sidebar:
    st.title("📚 Voca Manager")
    if st.button("➕ 새 프로젝트 만들기"):
        st.session_state.view = "create"; st.rerun()
    st.write("---")
    for p_name in list(st.session_state.vdb.keys()):
        c1, c2 = st.columns([4, 1])
        if c1.button(f"📖 {p_name}", key=f"s_{p_name}"):
            st.session_state.selected_p = p_name
            st.session_state.view = "study"
            st.session_state.editing_word = None
            st.rerun()
        if c2.button("🗑️", key=f"d_{p_name}"):
            del st.session_state.vdb[p_name]
            save_db(st.session_state.vdb); st.rerun()

# --- 1. 목록 ---
if st.session_state.view == "list":
    st.title("학습 목록")
    if not st.session_state.vdb: st.info("사이드바에서 새 프로젝트를 생성하세요.")
    else:
        for p in st.session_state.vdb.keys():
            if st.button(f"'{p}' 학습 입장"):
                st.session_state.selected_p = p; st.session_state.view = "study"; st.rerun()

# --- 2. 생성 (모든 옵션 통합) ---
elif st.session_state.view == "create":
    st.title("🛠 프로젝트 생성")
    mode = st.radio("입력 방식", ["파일 업로드", "직접 입력"], horizontal=True)
    dist = st.selectbox("배분 방식", ["총 일수", "기간 선택", "하루 개수"])
    
    with st.form("c_form"):
        title = st.text_input("프로젝트 이름")
        c1, c2 = st.columns(2)
        s_date = c1.date_input("시작일")
        val = c2.number_input("설정값(일수/개수)", min_value=1, value=5)
        
        up = st.file_uploader("Word 파일", type=['docx']) if mode == "파일 업로드" else None
        txt = st.text_area("단어|뜻|예문") if mode == "직접 입력" else ""
        
        if st.form_submit_button("생성"):
            data = []
            if mode == "파일 업로드" and up: data = parse_docx_perfect(up)
            elif txt:
                # 직접 입력 파싱 (단어|뜻|예문)
                for l in txt.split('\n'):
                    if '|' in l:
                        p = l.split('|')
                        data.append({"word": p[0].strip(), "meaning": p[1].strip() if len(p)>1 else "", "sentences": [p[2].strip()] if len(p)>2 else [], "solved": False})
                    elif data and l.strip(): data[-1]["sentences"].append(l.strip())
            
            if title and data:
                # 배분 로직
                days = val if dist != "하루 개수" else (len(data)//val + 1)
                chunk = (len(data)//days) + 1
                p_db = {}
                for i in range(int(days)):
                    d_key = (s_date + timedelta(days=i)).strftime("%Y-%m-%d")
                    p_db[d_key] = data[i*chunk : (i+1)*chunk]
                    if not p_db[d_key]: break
                st.session_state.vdb[title] = p_db
                save_db(st.session_state.vdb); st.session_state.view = "list"; st.rerun()

# --- 3. 학습 (문장 연습 테이블 해결 핵심) ---
elif st.session_state.view == "study":
    p_name = st.session_state.selected_p
    p_data = st.session_state.vdb[p_name]
    sel_date = st.selectbox("날짜", list(p_data.keys()))
    day_voca = p_data[sel_date]

    # 옵션
    o1, o2, o3 = st.columns(3)
    hw, hm = o1.checkbox("단어 가리기"), o2.checkbox("뜻 가리기")
    sort_un = o3.checkbox("미완료 상단")

    display_list = sorted(day_voca, key=lambda x: x.get('solved', False)) if sort_un else day_voca

    st.write("---")
    for idx, v in enumerate(display_list):
        r = st.columns([2, 3, 2, 1])
        # 단어/뜻
        if hw:
            if r[0].text_input("w", key=f"w_{v['word']}", label_visibility="collapsed").lower() == v['word'].lower():
                r[0].markdown(f"<span class='correct-ans'>{v['word']} ✓</span>", unsafe_allow_html=True)
        else: r[0].write(f"**{v['word']}**")
        
        if hm:
            if r[1].text_input("m", key=f"m_{v['word']}", label_visibility="collapsed") in v['meaning']:
                r[1].markdown(f"<span class='correct-ans'>{v['meaning']} ✓</span>", unsafe_allow_html=True)
        else: r[1].write(v['meaning'])
        
        # [핵심] 문장 연습 버튼
        if r[2].button(f"📝 연습 ({len(v['sentences'])})", key=f"btn_{v['word']}"):
            st.session_state.editing_word = v['word'] # 현재 단어 저장
            
        # 완료
        orig_idx = next(i for i, item in enumerate(day_voca) if item['word'] == v['word'])
        v['solved'] = r[3].checkbox("V", value=v.get('solved', False), key=f"c_{v['word']}", label_visibility="collapsed")
        if v['solved'] != day_voca[orig_idx]['solved']:
            day_voca[orig_idx]['solved'] = v['solved']
            save_db(st.session_state.vdb); st.rerun()

        # [핵심] 클릭한 단어 바로 아래에 드릴링 테이블 생성
        if st.session_state.editing_word == v['word']:
            with st.container():
                st.markdown(f"<div class='drill-area'>", unsafe_allow_html=True)
                st.subheader(f"🔍 {v['word']} 문장 채우기")
                for si, sent in enumerate(v['sentences']):
                    st.markdown(f"<div class='sentence-row'>", unsafe_allow_html=True)
                    m_sent = re.compile(re.escape(v['word']), re.IGNORECASE).sub("__________", sent)
                    st.write(f"**{si+1}.** {m_sent}")
                    ans = st.text_input("정답 입력", key=f"ans_{v['word']}_{si}", label_visibility="collapsed")
                    if ans.lower() == v['word'].lower(): st.success("Correct!")
                    st.markdown("</div>", unsafe_allow_html=True)
                if st.button("닫기", key=f"close_{v['word']}"):
                    st.session_state.editing_word = None
                    st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)
