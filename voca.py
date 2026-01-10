import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import re
import json
import os

try:
    from docx import Document
except ImportError:
    st.error("라이브러리 미설치: 터미널에서 'pip install python-docx'를 실행하세요.")

# --- 1. 페이지 설정 및 디자인 ---
st.set_page_config(page_title="Voca Master Pro (Final)", layout="wide")
st.markdown("""
    <style>
    .correct-ans { color: #10B981; font-weight: bold; font-size: 1.1rem; }
    .drill-container { background-color: #f1f5f9; padding: 25px; border-radius: 15px; border: 2px solid #1e40af; margin-top: 25px; }
    .sentence-box { background: white; padding: 15px; border-radius: 10px; margin-bottom: 12px; border-left: 6px solid #1e40af; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .sidebar-project { display: flex; justify-content: space-between; align-items: center; margin-bottom: 5px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 데이터베이스 로직 ---
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

# --- 3. [개선] 워드 파서 로직 ---
def parse_voca_docx(file):
    doc = Document(file)
    data = []
    current_entry = None
    
    for para in doc.paragraphs:
        text = para.text.strip()
        if not text: continue
        
        # 문장 패턴 (숫자. 문장)
        if re.match(r'^\d+[\.\)]', text):
            if current_entry:
                clean_s = re.sub(r'^\d+[\.\)]', '', text).strip()
                current_entry["sentences"].append(clean_s)
        # 뜻 패턴
        elif "Korean:" in text:
            if current_entry:
                m = re.search(r"Korean:\s*(.*?)(?:\s*answer:|$)", text)
                current_entry["meaning"] = m.group(1).strip() if m else text.replace("Korean:", "").strip()
        # 단어 패턴 (알파벳 위주 짧은 줄)
        elif re.match(r'^[a-zA-Z\s\-]+$', text) and len(text.split()) <= 4:
            if current_entry: data.append(current_entry)
            current_entry = {"word": text, "meaning": "뜻 없음", "sentences": [], "solved": False}
            
    if current_entry: data.append(current_entry)
    return data

# --- 4. 사이드바 (프로젝트 관리 및 삭제) ---
with st.sidebar:
    st.title("📂 Voca Master")
    if st.button("➕ 새 프로젝트 만들기", use_container_width=True):
