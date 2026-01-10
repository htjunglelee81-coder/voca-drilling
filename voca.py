import streamlit as st
from docx import Document
import re
from gtts import gTTS
import base64
from io import BytesIO

st.set_page_config(page_title="Voca Pro", layout="wide")

# --- 🔊 음성 합성 함수 ---
def speak(text):
    tts = gTTS(text=text, lang='en')
    fp = BytesIO()
    tts.write_to_fp(fp)
    return fp

# --- 🔍 파싱 엔진: 예문과 해석을 정확히 분리 ---
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
        
        # 2. 뜻 판별
        elif "Korean:" in text:
            if current_entry:
                current_entry["meaning"] = text.replace("Korean:", "").split("answer:")[0].strip()
        
        # 3. 예문 및 해석 판별
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
    c1, c2, c3 = st.columns(3)
    h_w = c1.checkbox("영어 어휘 가리기")
    h_m = c2.checkbox("한국어 의미 가리기")
    h_t = c3.checkbox("문장 해석 항상 보기", value=True)

    st.write("---")

    for idx, item in enumerate(vdb):
        with st.container():
            col1, col2, col3 = st.columns([2, 3, 2])
            word = item['word']
            
            # 1. 영단어 입력 (실시간 색상 반영)
            if h_w:
                u_w = col1.text_input("단어를 입력하세요", key=f"w_{idx}", label_visibility="collapsed", placeholder="단어를 입력하세요")
                is_correct = u_w.lower() == word.lower()
                color = "#d1fae5" if is_correct else ("#fee2e2" if u_w else "white")
                border = "#10B981" if is_correct else ("#EF4444" if u_w else "#ddd")
                col1.markdown(f'<div style="background-color:{color}; border:2px solid {border}; padding:8px; border-radius:5px; text-align:center; font-weight:bold;">{word if is_correct else " "}</div>', unsafe_allow_html=True)
            else:
                col1.subheader(word)

            # 2. 의미 입력 (실시간 색상 반영)
            if h_m:
                u_m = col2.text_input("뜻을 입력하세요", key=f"m_{idx}", label_visibility="collapsed", placeholder="뜻을 입력하세요")
                is_m_correct = u_m and (u_m in item['meaning'])
                m_color = "#d1fae5" if is_m_correct else ("#fee2e2" if u_m else "white")
                m_border = "#10B981" if is_m_correct else ("#EF4444" if u_m else "#ddd")
                col2.markdown(f'<div style="background-color:{m_color}; border:2px solid {m_border}; padding:8px; border-radius:5px;">{item["meaning"] if is_m_correct else " "}</div>', unsafe_allow_html=True)
            else:
                col2.write(item['meaning'])

            # 3. 예문 연습 버튼
            if col3.button(f"📝 문장 연습 ({len(item['sentences'])})", key=f"btn_{idx}", use_container_width=True):
                st.session_state[f"show_{idx}"] = not st.session_state.get(f"show_{idx}", False)

            # --- 예문 상세 연습 섹션 ---
            if st.session_state.get(f"show_{idx}", False):
                st.markdown(f'<div style="background-color:#f9fafb; padding:20px; border-radius:10px; border:1px solid #eee; margin-bottom:20px;">', unsafe_allow_html=True)
                for s_idx, sent in enumerate(item['sentences']):
                    sc1, sc2, sc3 = st.columns([5, 2, 0.5])
                    
                    # 문장 마스킹 및 해석(해석이 따로 없으면 문장 자체 표시)
                    masked = re.compile(re.escape(word), re.IGNORECASE).sub("________", sent)
                    sc1.write(f"**{s_idx+1}.** {masked}")
                    if h_t:
                        sc1.caption("해석: (파일 내 해석이 포함된 경우 표시됩니다)") # 필요시 번역 API 연결 가능

                    # 문장 내 단어 입력 (정답 시 칸 색상 변경)
                    u_s = sc2.text_input("정답", key=f"s_{idx}_{s_idx}", label_visibility="collapsed", placeholder="단어 입력")
                    s_correct = u_s.lower() == word.lower()
                    s_bg = "#d1fae5" if s_correct else ("#fee2e2" if u_s else "white")
                    s_br = "#10B981" if s_correct else ("#EF4444" if u_s else "#ddd")
                    sc2.markdown(f'<div style="background-color:{s_bg}; border:2px solid {s_br}; padding:5px; border-radius:5px; text-align:center; font-size:0.9rem;">{word if s_correct else " "}</div>', unsafe_allow_html=True)
                    
                    # 듣기
                    if sc3.button("🔊", key=f"sp_{idx}_{s_idx}"):
                        audio_fp = speak(sent)
                        b64 = base64.b64encode(audio_fp.getvalue()).decode()
                        st.markdown(f'<audio autoplay="true" src="data:audio/mp3;base64,{b64}">', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
