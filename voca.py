import streamlit as st
from docx import Document
import re
from gtts import gTTS
import base64
from io import BytesIO
import urllib.request

st.set_page_config(page_title="Voca Share Pro", layout="wide")

# --- ⚙️ 설정: 공부할 파일 이름 지정 ---
# GitHub에 함께 올릴 워드 파일 이름을 여기에 적으세요.
DATA_FILE = "voca.docx" 

# --- 🔊 핵심 함수 (번역 및 음성) ---
@st.cache_data
def get_translation(text):
    try:
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

# --- 🔍 서버 내 파일 읽기 ---
@st.cache_data
def load_server_data(file_path):
    try:
        doc = Document(file_path)
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
    except Exception as e:
        st.error(f"파일을 찾을 수 없습니다: {e}")
        return []

# --- UI 레이아웃 ---
st.title("📖 오늘의 할당 학습")
st.info(f"현재 배포된 콘텐츠: {DATA_FILE}")

# 데이터 로드 (파일 업로드 없이 즉시 실행)
vdb = load_server_data(DATA_FILE)

if vdb:
    # 학습 옵션
    with st.sidebar:
        st.header("⚙️ 학습 설정")
        h_word = st.checkbox("영어 어휘 가리기")
        h_mean = st.checkbox("한국어 의미 가리기")
        show_trans = st.checkbox("문장 해석 보기", value=True)

    for idx, item in enumerate(vdb):
        word = item['word']
        row = st.columns([2, 3, 2])
        
        # 1. 단어/뜻 칸 (피드백 유지)
        if h_word:
            u_w = row[0].text_input("", key=f"w_{idx}", placeholder="단어")
            is_w = u_w.lower().strip() == word.lower().strip()
            row[0].markdown(f'<div style="background-color:{"#d1fae5" if is_w else "#fee2e2" if u_w else "white"}; border:2px solid {"#10B981" if is_w else "#EF4444" if u_w else "#ddd"}; padding:8px; border-radius:5px; text-align:center;">{word if is_w else " "}</div>', unsafe_allow_html=True)
        else:
            row[0].subheader(word)

        if h_mean:
            u_m = row[1].text_input("", key=f"m_{idx}", placeholder="뜻")
            is_m = u_m.strip() in item['meaning'] and u_m.strip() != ""
            row[1].markdown(f'<div style="background-color:{"#d1fae5" if is_m else "#fee2e2" if u_m else "white"}; border:2px solid {"#10B981" if is_m else "#EF4444" if u_m else "#ddd"}; padding:8px; border-radius:5px;">{item["meaning"] if is_m else " "}</div>', unsafe_allow_html=True)
        else:
            row[1].write(item['meaning'])

        if row[2].button(f"📝 문장 연습 ({len(item['sentences'])})", key=f"btn_{idx}", use_container_width=True):
            st.session_state[f"show_{idx}"] = not st.session_state.get(f"show_{idx}", False)

        # 2. 예문 섹션 (자동 번역 포함)
        if st.session_state.get(f"show_{idx}", False):
            st.markdown('<div style="background-color:#f8fafc; padding:15px; border-radius:10px; border:1px solid #e2e8f0; margin-bottom:20px;">', unsafe_allow_html=True)
            for s_idx, sent in enumerate(item['sentences']):
                sc1, sc2, sc3 = st.columns([5, 2, 0.5])
                
                trans = get_translation(sent) if show_trans else ""
                masked = re.compile(re.escape(word), re.IGNORECASE).sub("________", sent)
                
                sc1.write(f"**{s_idx+1}.** {masked}")
                if show_trans: sc1.markdown(f"<small style='color:#1e40af;'>해석: {trans}</small>", unsafe_allow_html=True)

                u_s = sc2.text_input("", key=f"s_{idx}_{s_idx}", placeholder="입력")
                is_s = u_s.lower().strip() == word.lower().strip()
                sc2.markdown(f'<div style="background-color:{"#d1fae5" if is_s else "#fee2e2" if u_s else "white"}; border:2px solid {"#10B981" if is_s else "#EF4444" if u_s else "#ddd"}; padding:5px; border-radius:5px; text-align:center;">{word if is_s else " "}</div>', unsafe_allow_html=True)
                
                if sc3.button("🔊", key=f"sp_{idx}_{s_idx}"):
                    audio = speak(sent)
                    if audio:
                        b64 = base64.b64encode(audio.getvalue()).decode()
                        st.markdown(f'<audio autoplay="true" src="data:audio/mp3;base64,{b64}">', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
