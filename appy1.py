import streamlit as st
from supabase import create_client, Client

# --- 1. 설정 (아까 쓰신 그대로) ---
url: str = "https://lrnutmjafqqlzopxswsa.supabase.co"
key: str = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImxybnV0bWphZnFxbHpvcHhzd3NhIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjMwMTU4NDIsImV4cCI6MjA3ODU5MTg0Mn0.JJJtqAKfYSzlSky0gYNKbQJF_j0YUPYf2jquyInnvpk"
supabase: Client = create_client(url, key)

# --- 2. 예약 함수 (아까 만드신 엔진) ---
def save_to_supabase(name, phone, date, memo):
    data = {
        "name": name,
        "phone": phone,
        "date": str(date), # 날짜는 문자열로 변환
        "memo": memo,
        "status": "대기중"
    }
    try:
        supabase.table("reservations").insert(data).execute()
        return True
    except Exception as e:
        return str(e)

# --- 3. 화면 구성 (Streamlit) ---
st.title("🏥 심리상담 예약 시스템")
st.write("원장님, 테스트를 위해 예약 정보를 입력해주세요.")

# 입력 폼 만들기
with st.form("reservation_form"):
    col1, col2 = st.columns(2)
    with col1:
        name = st.text_input("신청자 이름", placeholder="예: 김철수")
    with col2:
        phone = st.text_input("연락처", placeholder="010-0000-0000")
    
    date = st.date_input("상담 희망 날짜")
    memo = st.text_area("상담 요청 내용 (선택사항)")
    
    # 제출 버튼
    submitted = st.form_submit_button("예약 등록하기")

    if submitted:
        if not name or not phone:
            st.error("이름과 연락처는 필수입니다!")
        else:
            # 로딩 표시
            with st.spinner("Supabase에 저장 중..."):
                result = save_to_supabase(name, phone, date, memo)
                
            if result == True:
                st.success(f"✅ {name}님 예약이 확정되었습니다!")
                st.balloons() # 성공 축하 풍선 효과 🎉
            else:
                st.error(f"저장 실패: {result}")