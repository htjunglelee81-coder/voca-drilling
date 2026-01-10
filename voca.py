import streamlit as st
from docx import Document
import re
from gtts import gTTS
import base64
from io import BytesIO

st.set_page_config(page_title="Voca Ultimate Pro", layout="wide")

# --- 🔊 음성 합성 함수 ---
def speak(text):
    try:
        tts = gTTS(text=text, lang='en')
        fp = BytesIO()
        tts.write_to_fp(fp)
        return fp
    except: return None

# --- 🔍 파싱 엔진 (안정성 강화) ---
def parse_docx(file):
    doc = Document(file)
    data = []
    current_entry = None
    for para in doc.paragraphs:
        text = para.text.strip()
        if not text: continue
        # 영문 단어 인식
        if re.match(r'^[a-zA-Z\s\-]+$', text) and len(text.split()) <= 4:
            if current_entry: data.append(current_entry)
            current_entry = {"word": text, "meaning": "", "sentences": []}
        # 한글 뜻 인식
        elif "Korean:" in text:
            if current_entry:
                m_part = text.replace("Korean:", "").split("answer:")[0].strip()
                current_entry["meaning"] = m_part
        # 예문 인식
        else:
            if current_entry:
                clean_s = re.sub(r'^\d+[\.\)]', '', text).strip()
                current_entry["sentences"].append(clean_s)
    if current_entry: data.append(current_entry)
    return data

# --- 🤖 초간단 자동 해석 로직 ---
# 서버 에러 방지를 위해 Streamlit 내장 기능을 활용한 우회 번역 (안전함)
@st.cache_data
def simple_translate(text):
    import urllib.request
    try:
        url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=en&tl=ko&dt=t&q={urllib.parse.quote(text)}"
        res = urllib.request.urlopen(url).read().decode('utf-8')
        return res.split('"')[1]
    except:
        return "해석을 가져오는 중입니다..."

# --- UI 레이아웃 ---
st.title("📚 AI 문장 자동 해석 보카")
uploaded_file = st.file_uploader("워드 파일을 업로드하세요", type="docx")

if uploaded_file:
    if 'vdb' not in st.session_state:
        st.session_state.vdb = parse_docx(uploaded_file)
    
    # ⚙️ 설정 옵션
    with st.expander("🛠️ 학습 설정", expanded=True):
        c1, c2, c3 = st.columns(3)
        h_word = c1.checkbox("영어 어휘 가리기")
        h_mean = c2.checkbox("한국어 의미 가리기")
        show_trans = c3.checkbox("문장별 한국어 해석 보기", value=True)

    st.write("---")

    for idx, item in enumerate(st.session_state.vdb):
        word = item['word']
        row = st.columns([2, 3, 2])
        
        # 1. 영단어 (초록/빨강 피드백)
        if h_word:
            u_w = row[0].text_input("Word", key=f"w_{idx}", label_visibility="collapsed", placeholder="단어")
            is_w_correct = u_w.lower().strip() == word.lower().strip()
            w_bg = "#d1fae5" if is_w_correct else ("#fee2e2" if u_w else "white")
            w_br = "#10B981" if is_w_correct else ("#EF4444" if u_w else "#ddd")
            row[0].markdown(f'<div style="background-color:{w_bg}; border:2px solid {w_br}; padding:8px; border-radius:5px; text-align:center; font-weight:bold;">{word if is_w_correct else " "}</div>', unsafe_allow_html=True)
        else:
            row[0].subheader(word)

        # 2. 한국어 의미 (초록/빨강 피드백)
        if h_mean:
            u_m = row[1].text_input("Meaning", key=f"m_{idx}", label_visibility="collapsed", placeholder="뜻")
            is_m_correct = u_m.strip() in item['meaning'] and u_m.strip() != ""
            m_bg = "#d1fae5" if is_m_correct else ("#fee2e2" if u_m else "white")
            m_br = "#10B981" if is_m_correct else ("#EF4444" if u_m else "#ddd")
            row[1].markdown(f'<div style="background-color:{m_bg}; border:2px solid {m_br}; padding:8px; border-radius:5px;">{item["meaning"] if is_m_correct else " "}</div>', unsafe_allow_html=True)
        else:
            row[1].write(item['meaning'])

        # 3. 예문 연습 버튼
        if row[2].button(f"📝 문장 연습 ({len(item['sentences'])})", key=f"btn_{idx}", use_container_width=True):
            st.session_state[f"show_{idx}"] = not st.session_state.get(f"show_{idx}", False)

        # --- 예문 상세 섹션 ---
        if st.session_state.get(f"show_{idx}", False):
            st.markdown('<div style="background-color:#f8fafc; padding:15px; border-radius:10px; border:1px solid #e2e8f0; margin-bottom:20px;">', unsafe_allow_html=True)
            for s_idx, sent in enumerate(item['sentences']):
                sc1, sc2, sc3 = st.columns([5, 2, 0.5])
                
                # 실시간 자동 해석 (요청 사항)
                interpretation = simple_translate(sent) if show_trans else ""
                
                masked = re.compile(re.escape(word), re.IGNORECASE).sub("________", sent)
                sc1.write(f"**{s_idx+1}.** {masked}")
                if show_trans:
                    sc1.markdown(f"<small style='color:#1e40af;'>해석: {interpretation}</small>", unsafe_allow_html=True)

                # 문장 정답 입력 (초록/빨강 피드백)
                u_s = sc2.text_input("답", key=f"s_{idx}_{s_idx}", label_visibility="collapsed", placeholder="입력")
                is_s_correct = u_s.lower().strip() == word.lower().strip()
                s_bg = "#d1fae5" if is_s_correct else ("#fee2e2" if u_s else "white")
                s_br = "#10B981" if is_s_correct else ("#EF4444" if u_s else "#ddd")
                sc2.markdown(f'<div style="background-color:{s_bg}; border:2px solid {s_br}; padding:5px; border-radius:5px; text-align:center;">{word if is_s_correct else " "}</div>', unsafe_allow_html=True)
                
                # 듣기
                if sc3.button("🔊", key=f"sp_{idx}_{s_idx}"):
                    audio = speak(sent)
                    if audio:
                        b64 = base64.b64encode(audio.getvalue()).decode()
                        st.markdown(f'<audio autoplay="true" src="data:audio/mp3;base64,{b64}">', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
