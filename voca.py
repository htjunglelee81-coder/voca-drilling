import streamlit as st
from docx import Document
import re

# gTTS(Google Text-to-Speech) 라이브러리가 필요합니다: pip install gTTS
from gtts import gTTS
import base64
from io import BytesIO

st.set_page_config(page_title="Voca Simple Pro", layout="wide")

# --- 🔊 음성 합성 함수 ---
def speak(text):
    tts = gTTS(text=text, lang='en')
    fp = BytesIO()
    tts.write_to_fp(fp)
    return fp

# --- 🔍 파싱 엔진 (개선됨) ---
def parse_voca_file(file):
    doc = Document(file)
    data = []
    current_entry = None

    for para in doc.paragraphs:
        text = para.text.strip()
        if not text: continue

        # 1. 단어 판별
        if re.match(r'^[a-zA-Z\s\-]+$', text) and len(text.split()) <= 4:
            if current_entry: data.append(current_entry)
            current_entry = {"word": text, "meaning": "", "sentences": []}
        
        # 2. 뜻 판별 (answer: 문구 삭제)
        elif "Korean:" in text:
            if current_item := current_entry:
                m = text.split("Korean:")[1].split("answer:")[0].strip()
                current_item["meaning"] = m
        
        # 3. 예문 판별
        else:
            if current_entry and not text.startswith("Korean:"):
                # 숫자 제거
                clean_s = re.sub(r'^\d+[\.\)]', '', text).strip()
                current_entry["sentences"].append(clean_s)

    if current_entry: data.append(current_entry)
    return data

# --- UI ---
st.title("📚 스마트 단어장")

uploaded_file = st.file_uploader("워드 파일 업로드", type="docx")

if uploaded_file:
    if 'vdb' not in st.session_state:
        st.session_state.vdb = parse_voca_file(uploaded_file)
    
    vdb = st.session_state.vdb

    # 옵션
    c1, c2 = st.columns(2)
    h_w = c1.checkbox("영어 어휘 가리기")
    h_m = c2.checkbox("한국어 의미 가리기")

    st.write("---")

    for idx, item in enumerate(vdb):
        with st.container():
            col1, col2, col3 = st.columns([2, 3, 2])
            
            # 1. 단어 칸
            word = item['word']
            if h_w:
                u_w = col1.text_input("Word", key=f"w_{idx}", label_visibility="collapsed")
                is_correct = u_w.lower() == word.lower()
                bg_color = "#d1fae5" if is_correct else ("#fee2e2" if u_w else "white")
                text_color = "#065f46" if is_correct else "#991b1b"
                col1.markdown(f"""<div style="background-color:{bg_color}; padding:10px; border-radius:5px; color:{text_color}; font-weight:bold; border:1px solid {text_color if u_w else '#ddd'}">{word if is_correct else '입력 중...'}</div>""", unsafe_allow_html=True)
            else:
                col1.subheader(word)

            # 2. 의미 칸 (answer: 제거됨)
            if h_m:
                u_m = col2.text_input("Meaning", key=f"m_{idx}", label_visibility="collapsed")
                is_m_correct = u_m and (u_m in item['meaning'])
                m_bg = "#d1fae5" if is_m_correct else "white"
                col2.markdown(f"""<div style="background-color:{m_bg}; padding:10px; border-radius:5px; border:1px solid #ddd">{item['meaning'] if is_m_correct else '뜻을 맞춰보세요'}</div>""", unsafe_allow_html=True)
            else:
                col2.write(item['meaning'])

            # 3. 예문 버튼
            if col3.button(f"📝 예문 연습 ({len(item['sentences'])})", key=f"btn_{idx}"):
                st.session_state[f"show_{idx}"] = not st.session_state.get(f"show_{idx}", False)

            # --- 예문 상세 리스트 ---
            if st.session_state.get(f"show_{idx}", False):
                st.info(f"💡 {word} 문장 연습")
                for s_idx, sent in enumerate(item['sentences']):
                    sc1, sc2, sc3 = st.columns([5, 1, 1])
                    
                    # 문장 마스킹
                    masked = re.compile(re.escape(word), re.IGNORECASE).sub("________", sent)
                    sc1.write(f"{s_idx+1}. {masked}")
                    
                    # 실시간 입력 감지
                    u_s = sc2.text_input("답", key=f"s_{idx}_{s_idx}", label_visibility="collapsed")
                    s_correct = u_s.lower() == word.lower()
                    s_color = "#10B981" if s_correct else "#EF4444"
                    
                    if s_correct:
                        sc2.markdown(f"<span style='color:{s_color}; font-weight:bold;'>✓ OK</span>", unsafe_allow_html=True)
                    
                    # 듣기 기능
                    if sc3.button("🔊", key=f"sp_{idx}_{s_idx}"):
                        audio_fp = speak(sent)
                        audio_bytes = audio_fp.getvalue()
                        b64 = base64.b64encode(audio_bytes).decode()
                        md = f'<audio autoplay="true" src="data:audio/mp3;base64,{b64}">'
                        st.markdown(md, unsafe_allow_html=True)
                st.write("---")

else:
    st.info("단어장 파일을 업로드해 주세요.")
