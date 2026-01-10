import streamlit as st
from docx import Document
import re
from gtts import gTTS
import base64
from io import BytesIO

# 페이지 설정
st.set_page_config(page_title="Voca Trainer", layout="wide")

# --- 🔊 음성 출력 함수 ---
def speak(text):
    try:
        tts = gTTS(text=text, lang='en')
        fp = BytesIO()
        tts.write_to_fp(fp)
        return fp
    except:
        return None

# --- 🔍 워드 파일 읽기 엔진 ---
def parse_docx(file):
    doc = Document(file)
    data = []
    current_entry = None
    
    for para in doc.paragraphs:
        text = para.text.strip()
        if not text: continue
        
        # 단어 인식 (영문 위주)
        if re.match(r'^[a-zA-Z\s\-]+$', text) and len(text.split()) <= 4:
            if current_entry:
                data.append(current_entry)
            current_entry = {"word": text, "meaning": "뜻 정보 없음", "sentences": []}
        # 뜻 인식
        elif "Korean:" in text:
            if current_entry:
                # 'answer:' 이후의 내용은 가림
                m_part = text.split("Korean:")[1].split("answer:")[0].strip()
                current_entry["meaning"] = m_part
        # 예문 인식
        else:
            if current_entry and not text.startswith("Korean:"):
                clean_s = re.sub(r'^\d+[\.\)]', '', text).strip()
                current_entry["sentences"].append(clean_s)
                
    if current_entry:
        data.append(current_entry)
    return data

# --- UI 부분 ---
st.title("📚 보카 드릴링 시스템")

uploaded_file = st.file_uploader("워드 파일(.docx)을 업로드하세요", type="docx")

if uploaded_file:
    if 'words' not in st.session_state:
        st.session_state.words = parse_docx(uploaded_file)
    
    words_data = st.session_state.words
    
    # 상단 옵션
    c1, c2 = st.columns(2)
    hide_word = c1.checkbox("영어 어휘 가리기")
    hide_mean = c2.checkbox("한국어 의미 가리기")

    st.write("---")

    # 단어 리스트 출력
    for idx, item in enumerate(words_data):
        target_word = item['word']
        col1, col2, col3 = st.columns([2, 3, 1])
        
        # 1. 영단어 입력 칸
        if hide_word:
            u_input = col1.text_input("단어 입력", key=f"word_{idx}", label_visibility="collapsed", placeholder="영단어")
            is_correct = u_input.lower().strip() == target_word.lower().strip()
            # 정답이면 초록색, 오답이면 빨간색 배경
            bg = "#d1fae5" if is_correct else ("#fee2e2" if u_input else "white")
            br = "#10B981" if is_correct else ("#EF4444" if u_input else "#ddd")
            col1.markdown(f'<div style="background-color:{bg}; border:2px solid {br}; padding:8px; border-radius:5px; text-align:center; font-weight:bold;">{target_word if is_correct else " "}</div>', unsafe_allow_html=True)
        else:
            col1.markdown(f"### {target_word}")

        # 2. 한국어 뜻 칸
        if hide_mean:
            m_input = col2.text_input("뜻 입력", key=f"mean_{idx}", label_visibility="collapsed", placeholder="뜻 입력")
            is_m_correct = m_input.strip() in item['meaning'] and m_input.strip() != ""
            m_bg = "#d1fae5" if is_m_correct else ("#fee2e2" if m_input else "white")
            m_br = "#10B981" if is_m_correct else ("#EF4444" if m_input else "#ddd")
            col2.markdown(f'<div style="background-color:{m_bg}; border:2px solid {m_br}; padding:8px; border-radius:5px;">{item["meaning"] if is_m_correct else " "}</div>', unsafe_allow_html=True)
        else:
            col2.write(item['meaning'])

        # 3. 예문 보기 버튼
        if col3.button(f"문장 ({len(item['sentences'])})", key=f"btn_{idx}", use_container_width=True):
            st.session_state[f"show_{idx}"] = not st.session_state.get(f"show_{idx}", False)

        # --- 예문 상세 (클릭 시 나타남) ---
        if st.session_state.get(f"show_{idx}", False):
            st.info(f"💡 {target_word} 문장 연습")
            for s_idx, sent in enumerate(item['sentences']):
                sc1, sc2, sc3 = st.columns([5, 2, 0.5])
                
                # 문장 마스킹
                masked_sent = re.compile(re.escape(target_word), re.IGNORECASE).sub("________", sent)
                sc1.write(f"{s_idx+1}. {masked_sent}")
                
                # 문장 내 정답 입력 (색상 변화 반영)
                s_input = sc2.text_input("답", key=f"sent_{idx}_{s_idx}", label_visibility="collapsed", placeholder="입력")
                s_is_correct = s_input.lower().strip() == target_word.lower().strip()
                s_bg = "#d1fae5" if s_is_correct else ("#fee2e2" if s_input else "white")
                s_br = "#10B981" if s_is_correct else ("#EF4444" if s_input else "#ddd")
                sc2.markdown(f'<div style="background-color:{s_bg}; border:2px solid {s_br}; padding:5px; border-radius:5px; text-align:center;">{target_word if s_is_correct else " "}</div>', unsafe_allow_html=True)
                
                # 듣기 버튼
                if sc3.button("🔊", key=f"sp_{idx}_{s_idx}"):
                    audio_fp = speak(sent)
                    if audio_fp:
                        b64 = base64.b64encode(audio_fp.getvalue()).decode()
                        st.markdown(f'<audio autoplay="true" src="data:audio/mp3;base64,{b64}">', unsafe_allow_html=True)
            st.write("---")

else:
    st.info("워드 파일을 업로드하면 학습이 시작됩니다.")
