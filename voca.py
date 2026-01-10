import streamlit as st
from docx import Document
import re
from gtts import gTTS
import base64
from io import BytesIO
import urllib.request
import os

st.set_page_config(page_title="Voca All-in-One", layout="wide")

# --- ⚙️ 설정: 서버용 기본 파일명 ---
SERVER_FILE = "voca.docx" 

# --- 🔊 핵심 엔진 (번역 및 음성) ---
@st.cache_data
def get_translation(text):
    try:
        # 라이브러리 없이 구글 API를 직접 호출하여 에러 방지
        url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=en&tl=ko&dt=t&q={urllib.parse.quote(text)}"
        res = urllib.request.urlopen(url).read().decode('utf-8')
        return res.split('"')[1]
    except: return "해석을 가져오는 중..."

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
        # 영문 단어 인식 (대소문자, 하이픈 포함)
        if re.match(r'^[a-zA-Z\s\-]+$', text) and len(text.split()) <= 4:
            if current_entry: data.append(current_entry)
            current_entry = {"word": text, "meaning": "", "sentences": []}
        elif "Korean:" in text:
            if current_entry:
                m_part = text.replace("Korean:", "").split("answer:")[0].strip()
                current_entry["meaning"] = m_part
        else:
            if current_entry:
                clean_s = re.sub(r'^\d+[\.\)]', '', text).strip()
                current_entry["sentences"].append(clean_s)
    if current_entry: data.append(current_entry)
    return data

# --- UI 메인 ---
st.title("📚 스마트 보카 시스템 (공유 & 업로드)")

# 1. 파일 결정 로직: 서버 파일이 있으면 먼저 로드, 없으면 업로드 위젯 표시
source_file = None

if os.path.exists(SERVER_FILE):
    source_file = SERVER_FILE
    st.success(f"📢 서버에 등록된 '{SERVER_FILE}' 파일을 불러왔습니다.")
    if st.button("내 파일 새로 업로드하기"):
        # 서버 파일 무시하고 업로드하고 싶을 때 세션 초기화
        st.session_state.clear()
        source_file = None
        st.rerun()
else:
    source_file = st.file_uploader("워드 파일(.docx)을 업로드해주세요", type="docx")

# 2. 데이터 처리 및 화면 구성
if source_file:
    # 세션 데이터 캐싱 (매번 파싱하지 않도록)
    if 'vdb' not in st.session_state:
        st.session_state.vdb = parse_docx(source_file)
    
    vdb = st.session_state.vdb
    
    # 설정 옵션
    with st.sidebar:
        st.header("⚙️ 학습 옵션")
        h_word = st.checkbox("영어 어휘 가리기")
        h_mean = st.checkbox("한국어 의미 가리기")
        show_trans = st.checkbox("문장 해석 자동 생성", value=True)

    st.write("---")

    for idx, item in enumerate(vdb):
        word = item['word']
        row = st.columns([2, 3, 2])
        
        # [단어/뜻 칸 - 피드백 색상 유지]
        if h_word:
            u_w = row[0].text_input("Word", key=f"w_{idx}", label_visibility="collapsed", placeholder="단어")
            is_w = u_w.lower().strip() == word.lower().strip()
            w_bg = "#d1fae5" if is_w else ("#fee2e2" if u_w else "white")
            w_br = "#10B981" if is_w else ("#EF4444" if u_w else "#ddd")
            row[0].markdown(f'<div style="background-color:{w_bg}; border:2px solid {w_br}; padding:8px; border-radius:5px; text-align:center; font-weight:bold;">{word if is_w else " "}</div>', unsafe_allow_html=True)
        else:
            row[0].subheader(word)

        if h_mean:
            u_m = row[1].text_input("Meaning", key=f"m_{idx}", label_visibility="collapsed", placeholder="뜻")
            is_m = u_m.strip() in item['meaning'] and u_m.strip() != ""
            m_bg = "#d1fae5" if is_m else ("#fee2e2" if u_m else "white")
            m_br = "#10B981" if is_m else ("#EF4444" if u_m else "#ddd")
            row[1].markdown(f'<div style="background-color:{m_bg}; border:2px solid {m_br}; padding:8px; border-radius:5px;">{item["meaning"] if is_m else " "}</div>', unsafe_allow_html=True)
        else:
            row[1].write(item['meaning'])

        # 예문 버튼
        if row[2].button(f"📝 문장 ({len(item['sentences'])})", key=f"btn_{idx}", use_container_width=True):
            st.session_state[f"show_{idx}"] = not st.session_state.get(f"show_{idx}", False)

        # [문장 연습 섹션 - 자동 번역 포함]
        if st.session_state.get(f"show_{idx}", False):
            st.markdown('<div style="background-color:#f9fafb; padding:15px; border-radius:10px; border:1px solid #eee; margin-bottom:15px;">', unsafe_allow_html=True)
            for s_idx, sent in enumerate(item['sentences']):
                sc1, sc2, sc3 = st.columns([5, 2, 0.5])
                
                # 자동 해석 표시
                trans = get_translation(sent) if show_trans else ""
                masked = re.compile(re.escape(word), re.IGNORECASE).sub("________", sent)
                
                sc1.write(f"**{s_idx+1}.** {masked}")
                if show_trans:
                    sc1.markdown(f"<small style='color:#0369a1;'>해석: {trans}</small>", unsafe_allow_html=True)

                # 문장 내 정답 입력 (색상 변화)
                u_s = sc2.text_input("답", key=f"s_{idx}_{s_idx}", label_visibility="collapsed", placeholder="정답")
                is_s = u_s.lower().strip() == word.lower().strip()
                s_bg = "#d1fae5" if is_s else ("#fee2e2" if u_s else "white")
                s_br = "#10B981" if is_s else ("#EF4444" if u_s else "#ddd")
                sc2.markdown(f'<div style="background-color:{s_bg}; border:2px solid {s_br}; padding:5px; border-radius:5px; text-align:center;">{word if is_s else " "}</div>', unsafe_allow_html=True)
                
                if sc3.button("🔊", key=f"sp_{idx}_{s_idx}"):
                    audio = speak(sent)
                    if audio:
                        b64 = base64.b64encode(audio.getvalue()).decode()
                        st.markdown(f'<audio autoplay="true" src="data:audio/mp3;base64,{b64}">', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
