import streamlit as st
from docx import Document
import re
from gtts import gTTS
import base64
from io import BytesIO
from deep_translator import GoogleTranslator

st.set_page_config(page_title="Voca Auto System", layout="wide")

# --- 🔊 핵심 엔진: 음성 및 실시간 번역 ---
def speak(text):
    try:
        tts = gTTS(text=text, lang='en')
        fp = BytesIO()
        tts.write_to_fp(fp)
        return fp
    except: return None

def get_translation(text):
    try:
        # 어떤 문장이 들어와도 실시간으로 번역
        return GoogleTranslator(source='en', target='ko').translate(text)
    except:
        return "번역 서비스를 일시적으로 사용할 수 없습니다."

# --- 🔍 파싱 엔진: 파일 내 모든 데이터를 객체화 ---
def parse_voca_file(file):
    doc = Document(file)
    data = []
    current_entry = None
    
    for para in doc.paragraphs:
        text = para.text.strip()
        if not text: continue
        
        # 단어 패턴 인식 (대소문자 영문)
        if re.match(r'^[a-zA-Z\s\-]+$', text) and len(text.split()) <= 4:
            if current_entry: data.append(current_entry)
            current_entry = {"word": text, "meaning": "", "sentences": []}
        # 뜻 패턴 인식
        elif "Korean:" in text:
            if current_entry:
                current_entry["meaning"] = text.replace("Korean:", "").split("answer:")[0].strip()
        # 예문 패턴 인식 (숫자 무관하게 현재 단어 하위로 수집)
        else:
            if current_entry and not text.startswith("Korean:"):
                clean_s = re.sub(r'^\d+[\.\)]', '', text).strip()
                current_entry["sentences"].append(clean_s)
    
    if current_entry: data.append(current_entry)
    return data

# --- UI 레이아웃 ---
st.title("📂 스마트 보카 트레이너")
uploaded_file = st.file_uploader("파일을 업로드하면 즉시 학습 테이블이 생성됩니다.", type="docx")

if uploaded_file:
    # 세션 상태에 데이터 보관 (매번 파싱하지 않도록)
    if 'vdb' not in st.session_state or st.sidebar.button("새 파일 적용"):
        st.session_state.vdb = parse_voca_file(uploaded_file)
        # 이전 번역 기록 초기화
        for key in list(st.session_state.keys()):
            if key.startswith("trans_"): del st.session_state[key]
    
    c1, c2 = st.columns(2)
    h_word = c1.checkbox("영어 어휘 숨기기")
    h_mean = c2.checkbox("한국어 의미 숨기기")

    st.write("---")

    for idx, item in enumerate(st.session_state.vdb):
        word = item['word']
        row = st.columns([2, 3, 2])
        
        # 1. 영단어 (가리기 모드)
        if h_word:
            u_w = row[0].text_input("", key=f"w_{idx}", placeholder="단어 입력")
            is_correct = u_w.lower().strip() == word.lower().strip()
            bg = "#d1fae5" if is_correct else ("#fee2e2" if u_w else "white")
            br = "#10B981" if is_correct else ("#EF4444" if u_w else "#ddd")
            row[0].markdown(f'<div style="background-color:{bg}; border:2px solid {br}; padding:8px; border-radius:5px; text-align:center; font-weight:bold; min-height:42px;">{word if is_correct else " "}</div>', unsafe_allow_html=True)
        else:
            row[0].subheader(word)

        # 2. 한국어 뜻 (가리기 모드)
        if h_mean:
            u_m = row[1].text_input("", key=f"m_{idx}", placeholder="뜻 입력")
            is_m_correct = u_m and (u_m.strip() in item['meaning'])
            m_bg = "#d1fae5" if is_m_correct else ("#fee2e2" if u_m else "white")
            m_br = "#10B981" if is_m_correct else ("#EF4444" if u_m else "#ddd")
            row[1].markdown(f'<div style="background-color:{m_bg}; border:2px solid {m_br}; padding:8px; border-radius:5px; min-height:42px;">{item["meaning"] if is_m_correct else " "}</div>', unsafe_allow_html=True)
        else:
            row[1].write(item['meaning'])

        # 3. 예문 연습 버튼
        if row[2].button(f"📖 문장 ({len(item['sentences'])})", key=f"btn_{idx}", use_container_width=True):
            st.session_state[f"show_{idx}"] = not st.session_state.get(f"show_{idx}", False)

        # --- 예문 드릴링 섹션 ---
        if st.session_state.get(f"show_{idx}", False):
            st.markdown('<div style="background-color:#fcfcfc; padding:15px; border-radius:10px; border:1px solid #eee;">', unsafe_allow_html=True)
            for s_idx, sent in enumerate(item['sentences']):
                sc1, sc2, sc3 = st.columns([5, 2, 0.5])
                
                # 실시간 번역 및 세션 저장
                t_key = f"trans_{idx}_{s_idx}"
                if t_key not in st.session_state:
                    st.session_state[t_key] = get_translation(sent)
                
                masked = re.compile(re.escape(word), re.IGNORECASE).sub("________", sent)
                sc1.write(f"**{s_idx+1}.** {masked}")
                sc1.markdown(f"<small style='color:#555;'>해석: {st.session_state[t_key]}</small>", unsafe_allow_html=True)

                # 단어 입력 피드백 (칸 색상 변화)
                u_s = sc2.text_input("", key=f"s_{idx}_{s_idx}", placeholder="정답 입력")
                s_correct = u_s.lower().strip() == word.lower().strip()
                s_bg = "#d1fae5" if s_correct else ("#fee2e2" if u_s else "white")
                s_br = "#10B981" if s_correct else ("#EF4444" if u_s else "#ddd")
                sc2.markdown(f'<div style="background-color:{s_bg}; border:2px solid {s_br}; padding:5px; border-radius:5px; text-align:center; min-height:35px;">{word if s_correct else " "}</div>', unsafe_allow_html=True)
                
                # 듣기 버튼
                if sc3.button("🔊", key=f"sp_{idx}_{s_idx}"):
                    audio = speak(sent)
                    if audio:
                        b64 = base64.b64encode(audio.getvalue()).decode()
                        st.markdown(f'<audio autoplay="true" src="data:audio/mp3;base64,{b64}">', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
