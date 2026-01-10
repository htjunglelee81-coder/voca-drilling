import streamlit as st
from docx import Document
import re
from gtts import gTTS
import base64
from io import BytesIO
from deep_translator import GoogleTranslator

st.set_page_config(page_title="Voca AI Ultimate", layout="wide")

# --- 🔊 음성 및 번역 함수 ---
def speak(text):
    try:
        tts = gTTS(text=text, lang='en')
        fp = BytesIO()
        tts.write_to_fp(fp)
        return fp
    except: return None

def get_translation(text):
    try:
        # 실시간으로 모든 문장을 한국어로 번역
        return GoogleTranslator(source='en', target='ko').translate(text)
    except:
        return "해석을 불러오는 중 오류가 발생했습니다."

# --- 🔍 파싱 엔진 ---
def parse_voca_file(file):
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

# --- UI ---
st.title("📚 전 문장 자동 해석 단어장")
uploaded_file = st.file_uploader("워드 파일을 업로드하세요", type="docx")

if uploaded_file:
    if 'vdb' not in st.session_state:
        st.session_state.vdb = parse_voca_file(uploaded_file)
    
    c1, c2 = st.columns(2)
    h_word = c1.checkbox("영어 어휘 가리기")
    h_mean = c2.checkbox("한국어 의미 가리기")

    st.write("---")

    for idx, item in enumerate(st.session_state.vdb):
        word = item['word']
        row = st.columns([2, 3, 2])
        
        # 1. 영단어 입력 (색상 피드백)
        if h_word:
            u_w = row[0].text_input("Word", key=f"w_{idx}", label_visibility="collapsed", placeholder="단어 입력")
            is_correct = u_w.lower() == word.lower()
            bg = "#d1fae5" if is_correct else ("#fee2e2" if u_w else "white")
            br = "#10B981" if is_correct else ("#EF4444" if u_w else "#ddd")
            row[0].markdown(f'<div style="background-color:{bg}; border:2px solid {br}; padding:10px; border-radius:5px; text-align:center; font-weight:bold;">{word if is_correct else " "}</div>', unsafe_allow_html=True)
        else:
            row[0].subheader(word)

        # 2. 한국어 의미 입력 (색상 피드백)
        if h_mean:
            u_m = row[1].text_input("Meaning", key=f"m_{idx}", label_visibility="collapsed", placeholder="뜻 입력")
            is_m_correct = u_m and (u_m in item['meaning'])
            m_bg = "#d1fae5" if is_m_correct else ("#fee2e2" if u_m else "white")
            m_br = "#10B981" if is_m_correct else ("#EF4444" if u_m else "#ddd")
            row[1].markdown(f'<div style="background-color:{m_bg}; border:2px solid {m_br}; padding:10px; border-radius:5px;">{item["meaning"] if is_m_correct else " "}</div>', unsafe_allow_html=True)
        else:
            row[1].write(item['meaning'])

        # 3. 예문 버튼
        if row[2].button(f"📝 문장 연습 ({len(item['sentences'])})", key=f"btn_{idx}", use_container_width=True):
            st.session_state[f"show_{idx}"] = not st.session_state.get(f"show_{idx}", False)

        # --- 예문 연습 및 실시간 전체 번역 ---
        if st.session_state.get(f"show_{idx}", False):
            st.markdown('<div style="background-color:#f8fafc; padding:15px; border-radius:10px; border:1px solid #e2e8f0;">', unsafe_allow_html=True)
            for s_idx, sent in enumerate(item['sentences']):
                sc1, sc2, sc3 = st.columns([5, 2, 0.5])
                
                # 모든 문장에 대해 세션 기반 실시간 번역
                t_key = f"t_{idx}_{s_idx}"
                if t_key not in st.session_state:
                    with st.spinner('해석 중...'):
                        st.session_state[t_key] = get_translation(sent)
                
                masked = re.compile(re.escape(word), re.IGNORECASE).sub("________", sent)
                sc1.write(f"**{s_idx+1}.** {masked}")
                sc1.markdown(f"<small style='color:#1e40af; font-weight:500;'>해석: {st.session_state[t_key]}</small>", unsafe_allow_html=True)

                # 예문 내 단어 입력 (색상 피드백)
                u_s = sc2.text_input("답", key=f"s_{idx}_{s_idx}", label_visibility="collapsed", placeholder="입력")
                s_correct = u_s.lower() == word.lower()
                s_bg = "#d1fae5" if s_correct else ("#fee2e2" if u_s else "white")
                s_br = "#10B981" if s_correct else ("#EF4444" if u_s else "#ddd")
                sc2.markdown(f'<div style="background-color:{s_bg}; border:2px solid {s_br}; padding:5px; border-radius:5px; text-align:center; min-height:35px;">{word if s_correct else " "}</div>', unsafe_allow_html=True)
                
                if sc3.button("🔊", key=f"sp_{idx}_{s_idx}"):
                    audio = speak(sent)
                    if audio:
                        b64 = base64.b64encode(audio.getvalue()).decode()
                        st.markdown(f'<audio autoplay="true" src="data:audio/mp3;base64,{b64}">', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
