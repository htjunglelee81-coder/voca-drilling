import streamlit as st
from docx import Document
import re

st.set_page_config(page_title="Voca Simple Table", layout="wide")

# --- 1. 워드 파일 파싱 엔진 (가장 중요) ---
def parse_voca_file(file):
    doc = Document(file)
    data = []
    current_entry = None

    for para in doc.paragraphs:
        text = para.text.strip()
        if not text: continue

        # 규칙 A: 'Korean:'이 포함된 줄은 현재 단어의 '뜻'
        if "Korean:" in text:
            if current_entry:
                current_entry["meaning"] = text.replace("Korean:", "").strip()
        
        # 규칙 B: 숫자로 시작하는 줄은 현재 단어의 '예문'
        elif re.match(r'^\d+[\.\)]', text):
            if current_entry:
                current_entry["sentences"].append(text)
        
        # 규칙 C: 영문자로만 시작하고 짧은 줄은 '새 단어' (가장 우선순위 낮음)
        elif re.match(r'^[a-zA-Z\s\-]+$', text) and len(text.split()) <= 4:
            if current_entry:
                data.append(current_entry)
            current_entry = {"word": text, "meaning": "뜻 없음", "sentences": []}
        
        # 규칙 D: 그 외 숫자로 시작하지 않지만 긴 문장들도 예문으로 간주 (advocacy 대응)
        elif len(text.split()) > 4 and current_entry:
            if not text.startswith("Korean:"):
                current_entry["sentences"].append(text)

    if current_entry: data.append(current_entry)
    return data

# --- 2. 앱 UI 시작 ---
st.title("📄 단어장 테이블 생성기")

uploaded_file = st.file_uploader("워드 파일을 업로드하세요 (.docx)", type="docx")

if uploaded_file:
    # 데이터 추출
    if 'voca_list' not in st.session_state:
        st.session_state.voca_list = parse_voca_file(uploaded_file)
    
    voca_list = st.session_state.voca_list

    # 상단 컨트롤러
    c1, c2 = st.columns(2)
    hide_word = c1.checkbox("영어 어휘 숨기기")
    hide_meaning = c2.checkbox("한국어 의미 숨기기")

    st.write("---")

    # 테이블 헤더
    h1, h2, h3 = st.columns([2, 3, 2])
    h1.subheader("영단어")
    h2.subheader("의미")
    h3.subheader("예문")

    # 테이블 본문
    for idx, item in enumerate(voca_list):
        row = st.container()
        with row:
            col1, col2, col3 = st.columns([2, 3, 2])
            
            # 영단어 열
            if hide_word:
                ans_w = col1.text_input("단어 입력", key=f"w_{idx}", label_visibility="collapsed")
                if ans_w.lower() == item['word'].lower():
                    col1.success(f"정답: {item['word']}")
            else:
                col1.write(f"### {item['word']}")

            # 의미 열
            if hide_meaning:
                ans_m = col2.text_input("뜻 입력", key=f"m_{idx}", label_visibility="collapsed")
                # 입력이 있을 때만 정답 확인
                if ans_m and (ans_m in item['meaning']):
                    col2.info(f"정답: {item['meaning']}")
            else:
                col2.write(item['meaning'])

            # 예문 보기 버튼
            if col3.button(f"📖 예문 보기 ({len(item['sentences'])})", key=f"btn_{idx}"):
                if f"show_{idx}" not in st.session_state:
                    st.session_state[f"show_{idx}"] = True
                else:
                    st.session_state[f"show_{idx}"] = not st.session_state[f"show_{idx}"]

            # 예문 리스트 출력 (클릭 시 하단에 펼쳐짐)
            if st.session_state.get(f"show_{idx}", False):
                st.markdown("---")
                st.write(f"🔍 **{item['word']}** 의 예문 리스트")
                for s_idx, sent in enumerate(item['sentences']):
                    # 단어 부분 빈칸 처리
                    masked_sent = re.compile(re.escape(item['word']), re.IGNORECASE).sub("________", sent)
                    sc1, sc2 = st.columns([5, 1])
                    sc1.write(f"{s_idx+1}. {masked_sent}")
                    ans_s = sc2.text_input("입력", key=f"ans_{idx}_{s_idx}", label_visibility="collapsed")
                    if ans_s.lower() == item['word'].lower():
                        sc2.success("OK")
                st.markdown("---")

else:
    st.warning("워드 파일을 업로드하면 테이블이 생성됩니다.")
