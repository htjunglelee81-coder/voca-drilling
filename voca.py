import streamlit as st
from docx import Document
import re
from gtts import gTTS
import base64
from io import BytesIO
import urllib.request
import os

st.set_page_config(page_title="Voca Master Pro", layout="wide")

# --- ⚙️ 설정: 서버용 기본 파일명 ---
SERVER_FILE = "voca.docx" 

# --- 🔊 핵심 엔진 (번역 및 음성) ---
@st.cache_data
def get_translation(text):
    try:
        url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=en&tl=ko&dt=t&q={urllib.parse.quote(text)}"
        res = urllib.request.urlopen(url).read().decode('utf-8')
        return res.split('"')[1]
    except: return "해석을 불러올 수 없습니다."

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

# --- 메인 타이틀 ---
st.title("📚 스마트 보카 드릴링")

# 1. 파일 결정 로직
source_file = None
if os.path.exists(SERVER_FILE):
    source_file = SERVER_FILE
    st.info(f"📢 배포된 콘텐츠({SERVER_FILE})로 학습을 시작합니다.")
else:
    source_file = st.file_uploader("학습할 워드 파일을 업로드하세요", type="docx")

if source_file:
    if 'vdb' not in st.session_state:
        st.session_state.vdb = parse_docx(source_file)
    
    # --- 🛠️ [복구] 상단 학습 옵션 레이아웃 ---
    st.markdown("### ⚙️ 학습 옵션")
    opt_col1, opt_col2, opt_col3 = st.columns(3)
    h_word = opt_col1.checkbox("영어 어휘 가리기", value=True)
    h_mean = opt_col2.checkbox("한국어 의미 가리기")
    show_trans = opt_col3.checkbox("문장별 한국어 해석 보기", value=True)
    st.write("---")

    # 2. 메인 학습 리스트
    for idx, item in enumerate(st.session_state.vdb):
        word = item['word']
        row = st.columns([2, 3, 2])
        
        # [단어 입력 및 피드백]
        if h_word:
            u_w = row[0].text_input("", key=f"w_{idx}", label_visibility="collapsed", placeholder="영단어 입력")
            is_w = u_w.lower().strip() == word.lower().strip()
            w_bg = "#d1fae5" if is_w else ("#fee2e2" if u_w else "white")
            w_br = "#10B981" if is_w else ("#EF4444" if u_w else "#ddd")
            row[0].markdown(f'<div style="background-color:{w_bg}; border:2px solid {w_br}; padding:8px; border-radius:5px; text-align:center; font-weight:bold; min-height:42px;">{word if is_w else " "}</div>', unsafe_allow_html=True)
        else:
            row[0].subheader(word)

        # [뜻 입력 및 피드백]
        if h_mean:
            u_m = row[1].text_input("", key=f"m_{idx}", label_visibility="collapsed", placeholder="한국어 뜻 입력")
            is_m = u_m.strip() in item['meaning'] and u_m.strip() != ""
            m_bg = "#d1fae5" if is_m else ("#fee2e2" if u_m else "white")
            m_br = "#10B981" if is_m else ("#EF4444" if u_m else "#ddd")
            row[1].markdown(f'<div style="background-color:{m_bg}; border:2px solid {m_br}; padding:8px; border-radius:5px; min-height:42px;">{item["meaning"] if is_m else " "}</div>', unsafe_allow_html=True)
        else:
            row[1].write(item['meaning'])

        # [예문 버튼]
        if row[2].button(f"📝 문장 연습 ({len(item['sentences'])})", key=f"btn_{idx}", use_container_width=True):
            st.session_state[f"show_{idx}"] = not st.session_state.get(f"show_{idx}", False)

        # [문장 연습 섹션]
        if st.session_state.get(f"show_{idx}", False):
            st.markdown(f'<div style="background-color:#f9fafb; padding:20px; border-radius:10px; border:1px solid #eee; margin-top:10px; margin-bottom:20px;">', unsafe_allow_html=True)
            for s_idx, sent in enumerate(item['sentences']):
                sc1, sc2, sc3 = st.columns([5, 2, 0.5])
                
                masked = re.compile(re.escape(word), re.IGNORECASE).sub("________", sent)
                sc1.write(f"**{s_idx+1}.** {masked}")
                
                # 상단 show_trans 옵션에 따른 자동 번역 표시
                if show_trans:
                    t_val = get_translation(sent)
                    sc1.markdown(f"<small style='color:#0369a1;'>해석: {t_val}</small>", unsafe_allow_html=True)

                # 문장 내 단어 입력 피드백
                u_s = sc2.text_input("", key=f"s_{idx}_{s_idx}", label_visibility="collapsed", placeholder="단어")
                is_s = u_s.lower().strip() == word.lower().strip()
                s_bg = "#d1fae5" if is_s else ("#fee2e2" if u_s else "white")
                s_br = "#10B981" if is_s else ("#EF4444" if u_s else "#ddd")
                sc2.markdown(f'<div style="background-color:{s_bg}; border:2px solid {s_br}; padding:5px; border-radius:5px; text-align:center; min-height:35px;">{word if is_s else " "}</div>', unsafe_allow_html=True)
                
                if sc3.button("🔊", key=f"sp_{idx}_{s_idx}"):
                    audio = speak(sent)
                    if audio:
                        b64 = base64.b64encode(audio.getvalue()).decode()
                        st.markdown(f'<audio autoplay="true" src="data:audio/mp3;base64,{b64}">', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
