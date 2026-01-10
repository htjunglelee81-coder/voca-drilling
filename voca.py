import streamlit as st
from docx import Document
import re
from gtts import gTTS
import base64
from io import BytesIO

st.set_page_config(page_title="Voca AI Pro", layout="wide")

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

# --- 🤖 AI 가 미리 번역한 advocacy 예문 (오류 방지용) ---
ADVOCACY_TRANS = [
    "옹호 단체들은 사회 정의를 증진하는 데 중요한 역할을 합니다.",
    "그녀는 여성 권리 옹호로 잘 알려져 있었습니다.",
    "그 조직은 장애인을 위한 옹호를 제공하기 위해 결성되었습니다.",
    "그 상원의원은 환경 보호의 강력한 옹호자였습니다.",
    "표현의 자유 옹호는 민주주의의 초석입니다.",
    "그 그룹의 옹호 활동은 법 개정이라는 결과를 가져왔습니다.",
    "동물 권리 옹호는 최근 몇 년 동안 성장해 왔습니다.",
    "평화적인 시위 옹호는 변화를 위한 강력한 도구입니다.",
    "그녀는 정신 건강 문제에 대한 옹호를 평생의 과업으로 삼았습니다.",
    "저렴한 주택 공급을 위한 그들의 옹호는 많은 가족들을 도왔습니다.",
    "책임감 있는 총기 소유 옹호는 공공 안전을 위해 중요합니다.",
    "그 조직은 가정 폭력 피해자들을 위한 옹호를 제공합니다.",
    "그 NGO의 옹호 노력은 의료 서비스 접근성 개선으로 이어졌습니다.",
    "성소수자 권리 옹호는 최근 몇 년 동안 큰 진전을 이루었습니다.",
    "그 배우는 자신의 플랫폼을 기후 변화 행동을 옹호하는 데 사용합니다.",
    "교육 개혁을 위한 그 그룹의 옹호는 널리 퍼진 지지를 얻었습니다.",
    "형사 사법 개혁 옹호는 국가적인 문제가 되었습니다.",
    "그 조직은 난민과 이민자들을 위한 옹호를 제공합니다.",
    "공정한 노동 관행 옹호는 노동자 권리에 매우 중요합니다.",
    "인종 정의 옹호는 최근 사건들 이후 탄력을 받았습니다."
]

# --- UI 시작 ---
st.title("📚 스마트 AI 단어장 (해석 내장형)")
uploaded_file = st.file_uploader("워드 파일 업로드", type="docx")

if uploaded_file:
    if 'vdb' not in st.session_state:
        st.session_state.vdb = parse_voca_file(uploaded_file)
    
    c1, c2 = st.columns(2)
    h_word = c1.checkbox("영어 어휘 가리기")
    h_mean = c2.checkbox("한국어 의미 가리기")

    st.write("---")

    for idx, item in enumerate(st.session_state.vdb):
        word = item['word']
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

        # --- 예문 상세 연습 섹션 ---
        if st.session_state.get(f"show_{idx}", False):
            st.markdown(f'<div style="background-color:#f8fafc; padding:20px; border-radius:10px; border:1px solid #e2e8f0; margin:10px 0 30px 0;">', unsafe_allow_html=True)
            for s_idx, sent in enumerate(item['sentences']):
                sc1, sc2, sc3 = st.columns([5, 2, 0.5])
                
                # 해석 매칭 (advocacy는 내장 해석 사용, 나머지는 자동 텍스트)
                interpretation = ADVOCACY_TRANS[s_idx] if word.lower() == "advocacy" and s_idx < len(ADVOCACY_TRANS) else "자동 해석 준비 중..."
                
                masked = re.compile(re.escape(word), re.IGNORECASE).sub("________", sent)
                sc1.write(f"**{s_idx+1}.** {masked}")
                sc1.markdown(f"<small style='color:#1e40af;'>해석: {interpretation}</small>", unsafe_allow_html=True)

                # 단어 입력 칸 (정답 시 색상 변경)
                u_s = sc2.text_input("정답", key=f"s_{idx}_{s_idx}", label_visibility="collapsed", placeholder="단어 입력")
                s_correct = u_s.lower() == word.lower()
                s_bg = "#d1fae5" if s_correct else ("#fee2e2" if u_s else "white")
                s_br = "#10B981" if s_correct else ("#EF4444" if u_s else "#ddd")
                sc2.markdown(f'<div style="background-color:{s_bg}; border:2px solid {s_br}; padding:5px; border-radius:5px; text-align:center; font-size:0.9rem; height:35px;">{word if s_correct else " "}</div>', unsafe_allow_html=True)
                
                if sc3.button("🔊", key=f"sp_{idx}_{s_idx}"):
                    audio_fp = speak(sent)
                    if audio_fp:
                        b64 = base64.b64encode(audio_fp.getvalue()).decode()
                        st.markdown(f'<audio autoplay="true" src="data:audio/mp3;base64,{b64}">', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
