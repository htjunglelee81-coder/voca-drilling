import streamlit as st
from docx import Document
import re
from gtts import gTTS
import base64
from io import BytesIO
import urllib.request
import os

st.set_page_config(page_title="Voca Master Pro", layout="wide")

# --- ⚙️ 설정: 서버 파일명 ---
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
                m_part = text.replace("Korean:", "").split("answer:")[0].strip()
                current_entry["meaning"] = m_part
        else:
            if current_entry:
                clean_s = re.sub(r'^\d+[\.\)]', '', text).strip()
                current_entry["sentences"].append(clean_s)
    if current_entry: data.append(current_entry)
    return data

# --- UI 레이아웃 ---
st.title("📚 보카 드릴링 마스터")

# 1. 파일 소스 결정 (서버 파일 우선 감지)
source_file = None
if os.path.exists(SERVER_FILE):
    source_file = SERVER_FILE
    st.success(f"✅ 서버 파일 '{SERVER_FILE}' 로드 완료. (학생 배포 모드)")
    if st.button("다른 파일 직접 업로드하기 (선생님 테스트)"):
        st.session_state.clear()
        if os.path.exists(SERVER_FILE): os.rename(SERVER_FILE, "backup.docx")
        st.rerun()
else:
    source_file = st.file_uploader("학습할 워드 파일을 업로드하세요", type="docx")

# 2. 데이터 처리
if source_file:
    if 'vdb' not in st.session_state:
        st.session_state.vdb = parse_docx(source_file)
    
    # --- 🛠️ 학습 설정 (여기에 모든 핵심 옵션 복구) ---
    with st.sidebar:
        st.header("⚙️ 학습 옵션")
        h_word = st.checkbox("영단어 가리기", value=True)
        h_mean = st.checkbox("한국어 뜻 가리기")
        show_trans = st.checkbox("문장 한국어 해석 보기", value=True)
        st.divider()
        if st.button("진행 상태 초기화"):
            st.session_state.clear()
            st.rerun()

    st.write("---")

    # 3. 메인 학습 테이블 로직
    for idx, item in enumerate(st.session_state.vdb):
        word = item['word']
        row = st.columns([2, 3, 2])
        
        # --- 영단어 입력 칸 및 피드백 ---
        if h_word:
            u_w = row[0].text_input(f"W_{idx}", key=f"w_{idx}", label_visibility="collapsed", placeholder="단어 입력")
            is_w_correct = u_w.lower().strip() == word.lower().strip()
            w_bg = "#d1fae5" if is_w_correct else ("#fee2e2" if u_w else "white")
            w_br = "#10B981" if is_w_correct else ("#EF4444" if u_w else "#ddd")
            row[0].markdown(f'<div style="background-color:{w_bg}; border:2px solid {w_br}; padding:8px; border-radius:5px; text-align:center; font-weight:bold; min-height:42px;">{word if is_w_correct else " "}</div>', unsafe_allow_html=True)
        else:
            row[0].subheader(word)

        # --- 한국어 뜻 입력 칸 및 피드백 ---
        if h_mean:
            u_m = row[1].text_input(f"M_{idx}", key=f"m_{idx}", label_visibility="collapsed", placeholder="뜻 입력")
            is_m_correct = u_m.strip() in item['meaning'] and u_m.strip() != ""
            m_bg = "#d1fae5" if is_m_correct else ("#fee2e2" if u_m else "white")
            m_br = "#10B981" if is_m_correct else ("#EF4444" if u_m else "#ddd")
            row[1].markdown(f'<div style="background-color:{m_bg}; border:2px solid {m_br}; padding:8px; border-radius:5px; min-height:42px;">{item["meaning"] if is_m_correct else " "}</div>', unsafe_allow_html=True)
        else:
            row[1].write(item['meaning'])

        # --- 예문 버튼 ---
        if row[2].button(f"📝 예문 ({len(item['sentences'])})", key=f"btn_{idx}", use_container_width=True):
            st.session_state[f"show_{idx}"] = not st.session_state.get(f"show_{idx}", False)

        # --- 예문 연습 섹션 (해석 보이기/숨기기 완벽 반영) ---
        if st.session_state.get(f"show_{idx}", False):
            st.markdown(f'<div style="background-color:#f8fafc; padding:20px; border-radius:10px; border:1px solid #e2e8f0; margin-bottom:20px;"><strong>🔍 {word} Sentence Drill</strong>', unsafe_allow_html=True)
            for s_idx, sent in enumerate(item['sentences']):
                sc1, sc2, sc3 = st.columns([5, 2, 0.5])
                
                # 마스킹 처리된 문장
                masked = re.compile(re.escape(word), re.IGNORECASE).sub("________", sent)
                sc1.write(f"**{s_idx+1}.** {masked}")
                
                # [핵심] 문장별 자동 해석 (사이드바 옵션에 연동)
                if show_trans:
                    trans_text = get_translation(sent)
                    sc1.markdown(f"<small style='color:#1e40af;'>해석: {trans_text}</small>", unsafe_allow_html=True)

                # 문장 내 단어 입력 및 색상 피드백
                u_s = sc2.text_input(f"S_{idx}_{s_idx}", key=f"s_{idx}_{s_idx}", label_visibility="collapsed", placeholder="정답")
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
