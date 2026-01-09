import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import re
import json
import os
from docx import Document
import io

# 1. 페이지 설정 및 디자인
st.set_page_config(page_title="Voca Master Pro", layout="wide")

st.markdown("""
    <style>
    .correct { color: #28a745; font-weight: bold; }
    .voca-row { padding: 10px; border-bottom: 1px solid #eee; }
    .stats-card { background-color: #f0f2f6; padding: 15px; border-radius: 10px; margin-bottom: 20px; border-left: 5px solid #007bff; }
    .stDataEditor { border: 1px solid #ddd; border-radius: 5px; }
    </style>
    """, unsafe_allow_html=True)

# 2. 핵심 함수: 워드 파서 (이미지 양식 맞춤)
def parse_word_file_custom(file):
    doc = Document(file)
    data = []
    current = None
    for para in doc.paragraphs:
        text = para.text.strip()
        if not text: continue
        # 뜻 추출
        if "Korean:" in text:
            if current:
                m = re.search(r"Korean:\s*(.*?)\s*answer:", text)
                current["meaning"] = m.group(1).strip() if m else text.split("Korean:")[1].strip()
        # 예문 추출
        elif re.match(r'^\d+[\.\)]', text):
            if current:
                current["sentences"].append(re.sub(r'^\d+[\.\)]', '', text).strip())
        # 단어 추출 (한두 단어이며 특수기호 없음)
        elif len(text.split()) <= 2 and not any(c in text for c in ":.)"):
            if current: data.append(current)
            current = {"word": text, "meaning": "", "sentences": []}
    if current: data.append(current)
    return data

# 3. 데이터 저장 및 로드
DB_FILE = "voca_db.json"
def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f: return json.load(f)
        except: return {}
    return {}

def save_db(db):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=4)

if 'vdb' not in st.session_state: st.session_state.vdb = load_db()
if 'editing_voca' not in st.session_state: st.session_state.editing_voca = []

# 4. 사이드바: 프로젝트 생성 (관리자/학생 공용)
with st.sidebar:
    st.title("📂 Voca Manager")
    with st.expander("✨ 새 프로젝트 만들기", expanded=not st.session_state.vdb):
        p_name = st.text_input("프로젝트 이름")
        input_method = st.radio("입력 방식", ["워드 파일 업로드", "직접 타이핑 입력"])
        
        if input_method == "워드 파일 업로드":
            up_file = st.file_uploader("워드 파일(.docx)", type=['docx'])
            if up_file and st.button("데이터 추출하기"):
                parsed = parse_word_file_custom(up_file)
                for d in parsed: d['sentences'] = "\n".join(d['sentences'])
                st.session_state.editing_voca = parsed
                st.success(f"{len(parsed)}개 단어 추출 완료!")

        st.write("---")
        date_opt = st.radio("일정 배분 방식", ["총 일수 설정", "하루 분량 설정", "캘린더 설정"])
        start_date = st.date_input("시작일", datetime.now())
        dist_val = st.number_input("설정값(일수/개수)", min_value=1, value=10)

# 5. 메인 화면 - 데이터 편집 및 학습
st.title("🚀 Voca Master Pro")

# [A] 데이터 편집 단계 (프로젝트 생성 전)
if input_method or st.session_state.editing_voca:
    st.subheader("1️⃣ 데이터 확인 및 편집")
    st.info("아래 테이블에서 단어, 뜻, 예문을 직접 수정하거나 추가할 수 있습니다.")
    
    initial_df = pd.DataFrame(st.session_state.editing_voca if st.session_state.editing_voca else [{"word":"", "meaning":"", "sentences":""}])
    
    edited_df = st.data_editor(
        initial_df,
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "word": st.column_config.TextColumn("어휘"),
            "meaning": st.column_config.TextColumn("의미"),
            "sentences": st.column_config.TextColumn("예문 (엔터로 구분)"),
        },
        key="voca_editor"
    )

    if st.button("✅ 이 내용으로 프로젝트 생성하기"):
        if not p_name: st.warning("프로젝트 이름을 입력해주세요.")
        else:
            final_list = edited_df.to_dict('records')
            valid_data = []
            for v in final_list:
                if v['word'].strip():
                    sents = [s.strip() for s in str(v['sentences']).split('\n') if s.strip()]
                    valid_data.append({"word": v['word'], "meaning": v['meaning'], "sentences": sents, "solved": False})
            
            # 배분 로직
            total = len(valid_data)
            if date_opt == "총 일수 설정": days = dist_val
            elif date_opt == "하루 분량 설정": days = (total // dist_val) + (1 if total % dist_val > 0 else 0)
            else: days = 7 # 캘린더 로직 간단화
            
            base = total // days
            project_days = {}
            for i in range(days):
                d_str = (start_date + timedelta(days=i)).strftime("%Y-%m-%d")
                s_idx, e_idx = i * base, (i + 1) * base if i < days - 1 else total
                project_days[d_str] = valid_data[s_idx:e_idx]
            
            st.session_state.vdb[p_name] = project_days
            save_db(st.session_state.vdb)
            st.session_state.editing_voca = []
            st.success(f"'{p_name}' 생성 완료! 아래에서 프로젝트를 선택해 학습하세요.")
            st.rerun()

st.write("---")

# [B] 학습 단계 (이미 생성된 프로젝트가 있을 때)
projects = list(st.session_state.vdb.keys())
if projects:
    st.subheader("2️⃣ 어휘 학습하기")
    c1, c2 = st.columns(2)
    sel_p = c1.selectbox("프로젝트 선택", ["선택하세요"] + projects)
    if sel_p != "선택하세요":
        p_data = st.session_state.vdb[sel_p]
        sel_date = c2.selectbox("날짜 선택", list(p_data.keys()))
        day_voca = p_data[sel_date]
        
        # 정답률 계산
        correct_num = sum(1 for v in day_voca if v.get('correct_mark', False))
        st.markdown(f"""<div class='stats-card'>
            <b>📊 오늘의 학습 현황</b><br>
            완성률: {correct_num/len(day_voca)*100:.1f}% ({correct_num}/{len(day_voca)} 완료)
            </div>""", unsafe_allow_html=True)

        opt1, opt2, opt3 = st.columns(3)
        h_w = opt1.checkbox("단어 가리기")
        h_m = opt2.checkbox("뜻 가리기")
        sort_m = opt3.checkbox("미완료 어휘 상단 정렬")

        display_voca = sorted(day_voca, key=lambda x: x['solved']) if sort_m else day_voca

        # 학습 테이블
        for idx, v in enumerate(display_voca):
            v_idx = day_voca.index(v)
            r1, r2, r3, r4 = st.columns([2, 3, 2, 1])
            with r1:
                if h_w:
                    in_w = st.text_input("단어", key=f"win_{sel_date}_{v_idx}", label_visibility="collapsed")
                    if in_w.lower() == v['word'].lower():
                        st.markdown(f"<span class='correct'>✓ {v['word']}</span>", unsafe_allow_html=True)
                        day_voca[v_idx]['correct_mark'] = True
                else: st.write(f"**{v['word']}**")
            with r2:
                if h_m:
                    in_m = st.text_input("뜻", key=f"min_{sel_date}_{v_idx}", label_visibility="collapsed")
                    if in_m and (in_m in v['meaning']): st.markdown(f"<span class='correct'>✓ {v['meaning']}</span>", unsafe_allow_html=True)
                else: st.write(v['meaning'])
            with r3:
                if st.button(f"📝 예문 ({len(v['sentences'])})", key=f"btn_{sel_date}_{v_idx}"):
                    st.session_state.active_v = v
            with r4:
                is_done = st.checkbox("완료", value=v['solved'], key=f"chk_{sel_date}_{v_idx}")
                if is_done != v['solved']:
                    day_voca[v_idx]['solved'] = is_done
                    save_db(st.session_state.vdb)
                    st.rerun()

        # 예문 학습 모달(하단 레이어)
        if 'active_v' in st.session_state:
            av = st.session_state.active_v
            st.markdown("---")
            st.subheader(f"🔍 {av['word']} 문장 연습")
            h_target = st.checkbox("문장 내 단어 가리기", value=True)
            for si, s in enumerate(av['sentences']):
                if h_target:
                    pattern = re.compile(re.escape(av['word']), re.IGNORECASE)
                    masked = pattern.sub("__________", s)
                    st.write(f"{si+1}. {masked}")
                    si_in = st.text_input("빈칸 정답", key=f"si_{si}", label_visibility="collapsed")
                    if si_in.lower() == av['word'].lower(): st.success("Correct!")
                else: st.info(f"{si+1}. {s}")
            if st.button("연습 창 닫기"):
                del st.session_state.active_v
                st.rerun()
else:
    st.warning("등록된 프로젝트가 없습니다. 사이드바에서 먼저 프로젝트를 생성해 주세요!")
