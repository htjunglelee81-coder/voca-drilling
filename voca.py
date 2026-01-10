import streamlit as st
from docx import Document
import re
from gtts import gTTS
import base64
from io import BytesIO
import urllib.request
import os

st.set_page_config(page_title="Voca Master Pro", layout="wide")

# --- ⚙️ 설정: 서버 기본 파일명 ---
SERVER_FILE = "voca.docx" 

# --- 🔊 핵심 기능 (번역 및 음성) ---
@st.cache_data
def get_translation(text):
    try:
        url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=en&tl=ko&dt=t&q={urllib.parse.quote(text)}"
        res = urllib.request.urlopen(url).read().decode('utf-8')
        return res.split('"')[1]
    except: return "해석을 불러오는 중..."

def speak(text):
    try:
        tts = gTTS(text=text, lang='en')
        fp = BytesIO()
        tts.write_to_fp(fp)
        return fp
    except: return None

# --- 🔍 파싱 엔진 ---
def parse_docx(file):
    doc = Document(file)
    data = []
    current_entry = None
    for para in doc.paragraphs:
        text = para.text.strip()
        if not text: continue
        if re.match(r'^[a-zA-Z\s\-]+$', text) and len(text.split()) <= 4:
            if current_entry: data.append(current_entry)
            current_entry = {"word": text, "meaning": "", "sentences": []}
        elif "Korean:" in text:
            if current_entry:
                current_entry["meaning"] = text.replace("Korean:", "").split("answer:")[0].strip()
        else:
            if current_entry:
                clean_s = re.sub(r'^\d+[\.\)]', '', text).strip()
                current_entry["sentences"].append(clean_s)
    if current_entry: data.append(current_entry)
    return data

# --- UI 레이아웃 ---
st.title("📚 스마트 보카 트레이너 (공유 & 개인 겸용)")

# 1. 파일 소스 결정 (서버 파일 우선, 없으면 업로드 대기)
source_file = None

if os.path.exists(SERVER_FILE):
    source_file = SERVER_FILE
    st.success(f"📢 서버에 저장된 콘텐츠({SERVER_FILE})를 불러왔습니다.")
    if st.button("다른 파일 직접 업로드하기"):
        os.rename(SERVER_FILE, "temp_voca.docx") # 잠시 이름 변경하여 업로드창 유도
        st.rerun()
else:
    source_file = st.file_uploader("워드 파일(.docx)을 업로드해주세요", type="docx")

# 2. 데이터 처리
if source_file:
    # 세션에 데이터 저장 (중복 파싱 방지)
    if 'vdb' not in st.session_state or st.sidebar.button("데이터 새로고침"):
        st.session_state.vdb = parse_docx(source_file)
    
    vdb = st.session_state.vdb
    
    # ⚙️ 사이드바 옵션
    with st.sidebar:
        st.header("⚙️ 학습 옵션")
        h_word = st.checkbox("영어 어휘 가리기")
        h_mean = st.checkbox("한국어 의미 가리기
