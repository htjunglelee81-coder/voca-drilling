import streamlit as st
from docx import Document
import re
from gtts import gTTS
from googletrans import Translator
import base64
from io import BytesIO

st.set_page_config(page_title="Voca System Pro", layout="wide")

# 번역기 및 음성 엔진 초기화
translator = Translator()

def get_translation(text):
    try:
        # 실시간 번역 시도
        return translator.translate(text, src='en', dest='ko').text
    except:
        return "해석을 불러올 수 없습니다 (재시도 필요)"

def speak(text):
    try:
        tts = gTTS(text=text, lang='en')
        fp = BytesIO()
        tts.write_to_fp(fp)
        return fp
    except: return None

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

# --- UI 시작 ---
st.title("📚 문장 자동 해석 보카 시스템")
uploaded_file = st.file_uploader("워드 파일 업로드", type="docx")

if uploaded_file:
    if 'vdb' not in st.session_state:
        st.session_state.vdb = parse_docx(uploaded_file)
    
    # 1. 상단 옵션 (요청하신 기능들)
    st.sidebar.header("⚙️ 학습 옵션")
    h_word = st.sidebar.checkbox("영어 어휘 가리기")
    h_mean = st.sidebar.checkbox("한국어 의미 가리기")
    show_trans = st.sidebar.checkbox("문장별 한국어 해석 보기", value=True) # 해석 보이기/가리기

    st.write("---")

    for idx, item in enumerate(st.session_state.vdb):
        word = item['word']
        row = st.columns([2, 3, 2])
        
        # [단어/뜻 입력 영역] - 초록색/빨간색 피드백 유지
        # 영단어
        if h_word:
            u_w = row[0].text_input("Word", key=f"w_{idx}", label_visibility="collapsed", placeholder="단어 입력")
            is_w_correct = u_w.lower().strip() == word.lower().strip()
            w_bg = "#d1fae5" if is_w_correct else ("#fee2e2" if u_w else "white")
            w_br = "#10B981" if is_w_correct else ("#EF4444" if u_w else "#ddd")
            row[0].markdown(f'<div style="background-color:{w_bg}; border:2px solid {w_br}; padding:8px; border-radius:5px; text-align:center; font-weight:bold;">{word if is_w_correct else " "}</div>', unsafe_allow_html=True)
        else:
            row[0].subheader(word)

        # 뜻
        if h_mean:
            u_m = row[1].text_input("Meaning", key=f"m_{idx}", label_visibility="collapsed", placeholder="뜻 입력")
            is_m_correct = u_m.strip() in item['meaning'] and u_m.strip() != ""
            m_bg = "#d1fae5" if is_m_correct else ("#fee2e2" if u_m else "white")
            m_br = "#10B981" if is_m_correct else ("#EF4444" if u_m else "#ddd")
            row[1].markdown(f'<div style="background-color:{m_bg}; border:2px solid {m_br}; padding:8px; border-radius:5px;">{item["meaning"] if is_m_correct else " "}</div>', unsafe_allow_html=True)
        else:
            row[1].write(item['meaning'])

        # 예문 버튼
        if row[2].button(f"📝 문장 ({len(item['sentences'])})", key=f"btn_{idx}", use_container_width=True):
            st.session_state[f"show_{idx}"] = not st.session_state.get(f"show_{idx}", False)

        # --- [문장 연습 섹션] ---
        if st.session_state.get(f"show_{idx}", False):
            st.markdown('<div style="background-color:#f9fafb; padding:15px; border-radius:10px; border:1px solid #eee; margin-bottom:10px;">', unsafe_allow_html=True)
            for s_idx, sent in enumerate(item['sentences']):
                sc1, sc2, sc3 = st.columns([5, 2, 0.5])
                
                # 자동 번역 로직
                t_key = f"t_{idx}_{s_idx}"
                if t_key not in st.session_state:
                    st.session_state[t_key] = get_translation(sent)
                
                masked = re.compile(re.escape(word), re.IGNORECASE).sub("________", sent)
                sc1.write(f"**{s_idx+1}.** {masked}")
                
                # [해석 보이기/가리기 적용]
                if show_trans:
                    sc1.markdown(f"<small style='color:#0369a1;'>해석: {st.session_state[t_key]}</small>", unsafe_allow_html=True)

                # 문장 내 단어 입력 (초록색/빨간색 변화)
                u_s = sc2.text_input("답", key=f"s_{idx}_{s_idx}", label_visibility="collapsed", placeholder="단어")
                is_s_correct = u_s.lower().strip() == word.lower().strip()
                s_bg = "#d1fae5" if is_s_correct else ("#fee2e2" if u_s else "white")
                s_br = "#10B981" if is_s_correct else ("#EF4444" if u_s else "#ddd")
                sc2.markdown(f'<div style="background-color:{s_bg}; border:2px solid {s_br}; padding:5px; border-radius:5px; text-align:center;">{word if is_s_correct else " "}</div>', unsafe_allow_html=True)
                
                if sc3.button("🔊", key=f"sp_{idx}_{s_idx}"):
                    audio = speak(sent)
                    if audio:
                        b64 = base64.b64encode(audio.getvalue()).decode()
                        st.markdown(f'<audio autoplay="true" src="data:audio/mp3;base64,{b64}">', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
