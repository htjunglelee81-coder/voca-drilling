import streamlit as st
from docx import Document
import re
from gtts import gTTS
from googletrans import Translator # 자동 번역기 추가
import base64
from io import BytesIO

st.set_page_config(page_title="Voca AI Pro", layout="wide")

# 번역기 초기화
translator = Translator()

# --- 🔊 음성 합성 함수 ---
def speak(text):
    try:
        tts = gTTS(text=text, lang='en')
        fp = BytesIO()
        tts.write_to_fp(fp)
        return fp
    except: return None

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
            if current_entry and not text.startswith("Korean:"):
                clean_s = re.sub(r'^\d+[\.\)]', '', text).strip()
                current_entry["sentences"].append(clean_s)
    if current_entry: data.append(current_entry)
    return data

# --- UI 시작 ---
st.title("📚 AI 자동 번역 단어장")
uploaded_file = st.file_uploader("워드 파일 업로드", type="docx")

if uploaded_file:
    if 'vdb' not in st.session_state:
        st.session_state.vdb = parse_voca_file(uploaded_file)
    
    # 상단 옵션
    c1, c2 = st.columns(2)
    h_word = c1.checkbox("영어 어휘 가리기")
    h_mean = c2.checkbox("한국어 의미 가리기")

    st.write("---")

    for idx, item in enumerate(st.session_state.vdb):
        word = item['word']
        
        # 메인 테이블 행
        row_cols = st.columns([2, 3, 2])
        
        # 1. 영단어 칸
        if h_word:
            u_w = row_cols[0].text_input("Word", key=f"w_{idx}", label_visibility="collapsed", placeholder="단어 입력")
            is_correct = u_w.lower() == word.lower()
            color = "#d1fae5" if is_correct else ("#fee2e2" if u_w else "white")
            border = "#10B981" if is_correct else ("#EF4444" if u_w else "#ddd")
            row_cols[0].markdown(f'<div style="background-color:{color}; border:2px solid {border}; padding:10px; border-radius:5px; text-align:center; font-weight:bold; height:45px;">{word if is_correct else " "}</div>', unsafe_allow_html=True)
        else:
            row_cols[0].markdown(f"### {word}")

        # 2. 한국어 의미 칸
        if h_mean:
            u_m = row_cols[1].text_input("Meaning", key=f"m_{idx}", label_visibility="collapsed", placeholder="뜻 입력")
            is_m_correct = u_m and (u_m in item['meaning'])
            m_color = "#d1fae5" if is_m_correct else ("#fee2e2" if u_m else "white")
            m_border = "#10B981" if is_m_correct else ("#EF4444" if u_m else "#ddd")
            row_cols[1].markdown(f'<div style="background-color:{m_color}; border:2px solid {m_border}; padding:10px; border-radius:5px; height:45px;">{item["meaning"] if is_m_correct else " "}</div>', unsafe_allow_html=True)
        else:
            row_cols[1].write(item['meaning'])

        # 3. 예문 연습 버튼
        if row_cols[2].button(f"📝 문장 연습 ({len(item['sentences'])})", key=f"btn_{idx}", use_container_width=True):
            st.session_state[f"show_{idx}"] = not st.session_state.get(f"show_{idx}", False)

        # --- 예문 상세 연습 섹션 (자동 번역 포함) ---
        if st.session_state.get(f"show_{idx}", False):
            st.markdown(f'<div style="background-color:#f8fafc; padding:20px; border-radius:10px; border:1px solid #e2e8f0; margin:10px 0 30px 0;">', unsafe_allow_html=True)
            for s_idx, sent in enumerate(item['sentences']):
                sc1, sc2, sc3 = st.columns([5, 2, 0.5])
                
                # [자동 번역 로직] 세션에 저장하여 한 번만 번역하도록 처리
                trans_key = f"trans_{idx}_{s_idx}"
                if trans_key not in st.session_state:
                    try:
                        translated = translator.translate(sent, src='en', dest='ko').text
                        st.session_state[trans_key] = translated
                    except:
                        st.session_state[trans_key] = "번역 오류 (재시도 필요)"
                
                # 문장 출력 (마스킹 + 해석)
                masked = re.compile(re.escape(word), re.IGNORECASE).sub("________", sent)
                sc1.write(f"**{s_idx+1}.** {masked}")
                sc1.markdown(f"<small style='color:#64748b;'>해석: {st.session_state[trans_key]}</small>", unsafe_allow_html=True)

                # 단어 입력 칸 (정답 시 색상 변경)
                u_s = sc2.text_input("정답", key=f"s_{idx}_{s_idx}", label_visibility="collapsed", placeholder="영단어 입력")
                s_correct = u_s.lower() == word.lower()
                s_bg = "#d1fae5" if s_correct else ("#fee2e2" if u_s else "white")
                s_br = "#10B981" if s_correct else ("#EF4444" if u_s else "#ddd")
                sc2.markdown(f'<div style="background-color:{s_bg}; border:2px solid {s_br}; padding:5px; border-radius:5px; text-align:center; font-size:0.9rem; height:35px;">{word if s_correct else " "}</div>', unsafe_allow_html=True)
                
                # 듣기
                if sc3.button("🔊", key=f"sp_{idx}_{s_idx}"):
                    audio_fp = speak(sent)
                    if audio_fp:
                        b64 = base64.b64encode(audio_fp.getvalue()).decode()
                        st.markdown(f'<audio autoplay="true" src="data:audio/mp3;base64,{b64}">', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
