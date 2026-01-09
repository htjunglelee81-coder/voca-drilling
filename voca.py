import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import re
import json
import os
from docx import Document
import io

# 1. 페이지 설정 및 데이터 관리 (생략 가능, 이전과 동일)
st.set_page_config(page_title="Voca Master Pro", layout="wide")

# [핵심] 워드 파일 파싱 함수 - 선생님의 이미지 양식 맞춤형
def parse_word_file_custom(file):
    doc = Document(file)
    extracted_data = []
    current_entry = None
    
    for para in doc.paragraphs:
        text = para.text.strip()
        if not text: continue
        
        # 1. 뜻 추출 (Korean: ... 감지)
        if "Korean:" in text:
            if current_entry:
                meaning_part = text.split("Korean:")[1].split("answer:")[0].strip()
                current_entry["meaning"] = meaning_part
        
        # 2. 예문 추출 (숫자. ... 감지)
        elif re.match(r'^\d+[\.\)]', text):
            if current_entry:
                clean_sent = re.sub(r'^\d+[\.\)]', '', text).strip()
                current_entry["sentences"].append(clean_sent)
        
        # 3. 새로운 단어 추출 (한 단어만 있고 특수기호가 없는 경우 단어로 인식)
        elif len(text.split()) == 1 and not any(c in text for c in ":.)"):
            if current_entry:
                extracted_data.append(current_entry)
            current_entry = {"word": text, "meaning": "", "sentences": []}
            
    if current_entry:
        extracted_data.append(current_entry)
    return extracted_data

# --- 메인 로직 시작 ---
DATA_PATH = "voca_projects.json"
def load_data():
    if os.path.exists(DATA_PATH):
        with open(DATA_PATH, "r", encoding="utf-8") as f: return json.load(f)
    return {}

if 'voca_db' not in st.session_state: st.session_state.voca_db = load_data()

# 사이드바 관리자 설정
with st.sidebar:
    st.title("📂 Project Manager")
    with st.expander("➕ 새 프로젝트 생성"):
        p_name = st.text_input("프로젝트 이름")
        
        # 날짜 설정 옵션 (요청사항 반영)
        date_opt = st.radio("일정 설정 방식", ["캘린더 기간 설정", "총 일수 설정", "하루 분량 설정"])
        start_date = st.date_input("시작일", datetime.now())
        
        total_days = 1
        v_per_day = 10
        if date_opt == "캘린더 기간 설정":
            end_date = st.date_input("종료일", datetime.now() + timedelta(days=6))
            total_days = (end_date - start_date).days + 1
        elif date_opt == "총 일수 설정":
            total_days = st.number_input("총 학습 일수", min_value=1, value=7)
        else:
            v_per_day = st.number_input("하루 어휘 분량", min_value=1, value=10)

        st.write("---")
        # 파일 업로드 (워드 파일 우선)
        uploaded_file = st.file_uploader("워드 자료 업로드 (.docx)", type=['docx'])
        
        if st.button("🚀 프로젝트 생성 및 자동 배정"):
            if p_name and uploaded_file:
                valid_voca = parse_word_file_custom(uploaded_file)
                
                if date_opt == "하루 분량 설정":
                    total_days = (len(valid_voca) // v_per_day) + (1 if len(valid_voca) % v_per_day > 0 else 0)
                
                base_cnt = len(valid_voca) // total_days
                project_data = {}
                
                for i in range(total_days):
                    d_str = (start_date + timedelta(days=i)).strftime("%Y-%m-%d")
                    s_idx = i * base_cnt
                    e_idx = (i + 1) * base_cnt if i < total_days - 1 else len(valid_voca)
                    
                    day_list = []
                    for v in valid_voca[s_idx:e_idx]:
                        day_list.append({"word": v['word'], "meaning": v['meaning'], "sentences": v['sentences'], "solved": False})
                    project_data[d_str] = day_list
                
                st.session_state.voca_db[p_name] = project_data
                with open(DATA_PATH, "w", encoding="utf-8") as f:
                    json.dump(st.session_state.voca_db, f, ensure_ascii=False, indent=4)
                st.success(f"{len(valid_voca)}개 단어 배정 완료!")
                st.rerun()

    st.write("---")
    projects = list(st.session_state.voca_db.keys())
    selected_p = st.selectbox("프로젝트 선택", ["선택하세요"] + projects)

# --- 학습 화면 (기존과 동일하되 디자인 보강) ---
if selected_p != "선택하세요":
    st.title(f"📖 {selected_p}")
    p_data = st.session_state.voca_db[selected_p]
    selected_date = st.selectbox("날짜 선택", list(p_data.keys()))
    
    # 미완료 어휘 정렬 및 테스트 기능 (기존 로직 유지)
    # ... (중략: 이전 코드와 동일한 테이블 및 예문 연습 로직)
