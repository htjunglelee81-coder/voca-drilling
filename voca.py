import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import re
import json
import os

# 1. 페이지 설정 및 스타일
st.set_page_config(page_title="Voca Master Pro", layout="wide")

st.markdown("""
    <style>
    .voca-header { background-color: #f8f9fa; padding: 10px; border-radius: 5px; border-left: 5px solid #007bff; margin-bottom: 20px; }
    .blank-input { background-color: #e8f5e9 !important; border: 1px solid #c8e6c9 !important; color: #2e7d32 !important; font-weight: bold; }
    .correct { color: #28a745; font-weight: bold; }
    .wrong { color: #dc3545; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# 2. 데이터 관리 및 저장 로직
DATA_PATH = "voca_projects.json"

def load_all_data():
    if os.path.exists(DATA_PATH):
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_all_data(data):
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

if 'voca_db' not in st.session_state:
    st.session_state.voca_db = load_all_data()

# 3. 사이드바 - 프로젝트 생성 및 선택
with st.sidebar:
    st.title("📂 Project Manager")
    
    # 프로젝트 생성 섹션
    with st.expander("➕ 새 프로젝트 생성"):
        p_name = st.text_input("프로젝트 이름")
        start_date = st.date_input("시작일", datetime.now())
        end_date = st.date_input("종료일", datetime.now() + timedelta(days=6))
        
        raw_voca_data = st.text_area("어휘 데이터 입력 (단어|뜻|예문1|예문2...)", 
                                     placeholder="apple|사과|I like apple.\nbanana|바나나|This is a banana.",
                                     height=150)
        
        if st.button("프로젝트 생성"):
            if p_name and raw_voca_data:
                lines = [l.strip() for l in raw_voca_data.split('\n') if l.strip()]
                total_days = (end_date - start_date).days + 1
                base_cnt = len(lines) // total_days
                
                # 날짜별 배분 로직 (나머지는 마지막 날에 추가)
                project_data = {}
                for i in range(total_days):
                    current_day = (start_date + timedelta(days=i)).strftime("%Y-%m-%d")
                    start_idx = i * base_cnt
                    # 마지막 날이면 끝까지 다 가져옴
                    end_idx = (i + 1) * base_cnt if i < total_days - 1 else len(lines)
                    
                    day_voca = []
                    for line in lines[start_idx:end_idx]:
                        parts = line.split('|')
                        word = parts[0].strip()
                        meaning = parts[1].strip()
                        sentences = [s.strip() for s in parts[2:]]
                        day_voca.append({
                            "word": word, "meaning": meaning, 
                            "sentences": sentences, "solved": False
                        })
                    project_data[current_day] = day_voca
                
                st.session_state.voca_db[p_name] = project_data
                save_all_data(st.session_state.voca_db)
                st.success(f"'{p_name}' 생성 완료!")
                st.rerun()

    st.write("---")
    
    # 프로젝트 선택
    projects = list(st.session_state.voca_db.keys())
    selected_p = st.selectbox("학습할 프로젝트 선택", ["선택하세요"] + projects)

# 4. 메인 학습 화면
if selected_p != "선택하세요":
    st.title(f"📖 {selected_p}")
    p_data = st.session_state.voca_db[selected_p]
    
    # 날짜 선택기
    selected_date = st.selectbox("학습 날짜 선택", list(p_data.keys()))
    current_day_voca = p_data[selected_date]
    
    # 학습 옵션
    col_opt1, col_opt2, col_opt3 = st.columns([2, 2, 6])
    hide_word = col_opt1.checkbox("영단어 가리기")
    hide_mean = col_opt2.checkbox("뜻 가리기")
    
    # 정렬 기능
    sort_uncompleted = st.checkbox("미완료 어휘 상단 정렬")
    display_voca = sorted(current_day_voca, key=lambda x: x['solved']) if sort_uncompleted else current_day_voca

    # 상단 정답률 표시
    correct_cnt = sum(1 for v in current_day_voca if v.get('temp_correct', False))
    total_cnt = len(current_day_voca)
    st.markdown(f"**정답률: {correct_cnt/total_cnt*100:.1f}% ({correct_cnt}/{total_cnt})**")

    # 어휘 테이블 생성
    st.write("---")
    
    for idx, voca in enumerate(display_voca):
        v_idx = current_day_voca.index(voca) # 원본 인덱스 유지
        c1, c2, c3, c4 = st.columns([2.5, 3, 3, 1.5])
        
        # 1. 영단어 칸
        with c1:
            if hide_word:
                u_word = st.text_input("단어 입력", key=f"w_in_{selected_date}_{v_idx}", label_visibility="collapsed")
                if u_word:
                    if u_word.lower() == voca['word'].lower():
                        st.markdown(f"<span class='correct'>✓ {voca['word']}</span>", unsafe_allow_html=True)
                        current_day_voca[v_idx]['temp_correct'] = True
                    else:
                        st.markdown(f"<span class='wrong'>✗</span>", unsafe_allow_html=True)
            else:
                st.write(f"**{voca['word']}**")

        # 2. 뜻 칸
        with c2:
            if hide_mean:
                u_mean = st.text_input("뜻 입력", key=f"m_in_{selected_date}_{v_idx}", label_visibility="collapsed")
                if u_mean and u_mean in voca['meaning']:
                    st.markdown(f"<span class='correct'>✓ {voca['meaning']}</span>", unsafe_allow_html=True)
            else:
                st.write(voca['meaning'])

        # 3. 문장 연습 버튼
        with c3:
            if st.button(f"📝 예문 ({len(voca['sentences'])})", key=f"btn_s_{v_idx}"):
                st.session_state.active_voca = voca
                st.session_state.show_popup = True

        # 4. 완료 체크
        with c4:
            is_done = st.checkbox("완료", value=voca['solved'], key=f"chk_{selected_date}_{v_idx}")
            if is_done != voca['solved']:
                current_day_voca[v_idx]['solved'] = is_done
                save_all_data(st.session_state.voca_db)
                st.rerun()

    # 예문 연습 영역 (팝업 대신 하단 레이어 혹은 Expander 활용)
    if 'active_voca' in st.session_state and st.session_state.show_popup:
        st.write("---")
        v = st.session_state.active_voca
        st.subheader(f"🔍 '{v['word']}' 문장 연습")
        
        hide_target = st.checkbox("문장 내 핵심 어휘 가리기")
        
        for s_idx, sentence in enumerate(v['sentences']):
            sc1, sc2 = st.columns([8, 2])
            with sc1:
                if hide_target:
                    # 대소문자 무시하고 단어 위치 찾기
                    pattern = re.compile(re.escape(v['word']), re.IGNORECASE)
                    # 빈칸으로 치환 (연한 초록색 강조 효과는 텍스트 입력창으로 구현)
                    display_s = pattern.sub("__________", sentence)
                    st.write(f"{s_idx+1}. {display_s}")
                    u_s_in = st.text_input("빈칸 채우기", key=f"s_in_{v['word']}_{s_idx}", label_visibility="collapsed")
                    if u_s_in.lower() == v['word'].lower():
                        st.success("Correct!")
                else:
                    st.info(f"{s_idx+1}. {sentence}")
            
        if st.button("닫기"):
            st.session_state.show_popup = False
            st.rerun()

else:
    st.info("왼쪽 사이드바에서 프로젝트를 생성하거나 선택해주세요.")