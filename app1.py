import streamlit as st
from supabase import create_client, Client
import requests
import base64
import uuid
import streamlit.components.v1 as components

# ==========================================
# 1. 설정 (Secrets에서 안전하게 가져오기)
# ==========================================

# [Supabase 설정]
# (이것도 Secrets에 넣으셨다면 st.secrets["SUPABASE_URL"]로 바꾸셔도 됩니다)
SUPABASE_URL = "https://lrnutmjafqqlzopxswsa.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImxybnV0bWphZnFxbHpvcHhzd3NhIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjMwMTU4NDIsImV4cCI6MjA3ODU5MTg0Mn0.JJJtqAKfYSzlSky0gYNKbQJF_j0YUPYf2jquyInnvpk"

# [토스페이먼츠 설정 - 핵심 변경 부분!]
try:
    # 1. Streamlit Secrets(금고)에서 키를 꺼내옵니다.
    TOSS_CLIENT_KEY = st.secrets["TOSS_CLIENT_KEY"]
    TOSS_SECRET_KEY = st.secrets["TOSS_SECRET_KEY"]
except FileNotFoundError:
    # 로컬에서 secrets.toml 파일이 없을 경우를 대비한 안내
    st.error("Secrets 파일을 찾을 수 없습니다. .streamlit/secrets.toml을 확인해주세요.")
    st.stop()
except KeyError:
    # 키 이름이 틀렸을 경우 안내
    st.error("Secrets에 'TOSS_CLIENT_KEY' 또는 'TOSS_SECRET_KEY'가 없습니다.")
    st.stop()

# 결제 금액 설정
PAYMENT_AMOUNT = 50000

# ==========================================
# 2. 기능 함수 모음
# ==========================================

# Supabase 연결 초기화
@st.cache_resource
def init_supabase():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = init_supabase()

# 토스 결제 승인 요청 (서버 검증)
def confirm_payment(payment_key, order_id, amount):
    # 시크릿 키가 입력되지 않았거나 기본값인 경우 (테스트용 가짜 승인)
    if "YOUR_SECRET_KEY" in TOSS_SECRET_KEY:
         return {"success": True, "data": {"status": "DONE"}}
         
    try:
        # 시크릿 키를 Base64로 인코딩
        secret_key_encoded = base64.b64encode(f"{TOSS_SECRET_KEY}:".encode()).decode()
        headers = {
            "Authorization": f"Basic {secret_key_encoded}",
            "Content-Type": "application/json"
        }
        data = {
            "paymentKey": payment_key,
            "orderId": order_id,
            "amount": amount
        }
        # 토스 서버에 승인 요청
        res = requests.post("https://api.tosspayments.com/v1/payments/confirm", headers=headers, json=data)
        
        if res.status_code == 200:
            return {"success": True, "data": res.json()}
        else:
            return {"success": False, "error": res.json()}
    except Exception as e:
        return {"success": False, "error": str(e)}

# Supabase에 예약 정보 저장
def save_reservation(name, phone, date, memo, payment_key, order_id, amount):
    data = {
        "name": name,
        "phone": phone,
        "date": str(date),
        "memo": memo,
        "payment_key": payment_key,
        "order_id": order_id,
        "amount": amount,
        "payment_status": "PAID" # 결제 완료 상태
    }
    try:
        supabase.table("reservations").insert(data).execute()
        return True
    except Exception as e:
        return str(e)

# ==========================================
# 3. 메인 화면 로직 시작
# ==========================================

st.set_page_config(page_title="심리상담 예약", layout="wide")
st.title("🏥 심리상담 예약 시스템")

# 세션 상태 초기화 (새로고침 되어도 데이터 유지)
if 'pending_payment' not in st.session_state:
    st.session_state.pending_payment = {}

# ------------------------------------------
# [STEP 1] 결제 성공 후 돌아왔는지 확인
# ------------------------------------------
query_params = st.query_params
payment_status = query_params.get("payment")

if payment_status == "success":
    # URL에 있는 정보 가져오기
    payment_key = query_params.get("paymentKey")
    order_id = query_params.get("orderId")
    amount = query_params.get("amount")
    
    # 아까 입력한 예약자 정보 가져오기
    pending = st.session_state.pending_payment
    
    # 정보가 다 있으면 저장 진행
    if pending and pending.get("order_id") == order_id:
        with st.spinner("결제 승인 및 예약 저장 중입니다..."):
            # 1. 토스에 승인 요청
            confirm = confirm_payment(payment_key, order_id, int(amount))
            
            if confirm["success"]:
                # 2. Supabase에 저장
                saved = save_reservation(
                    pending["name"], pending["phone"], pending["date"], 
                    pending["memo"], payment_key, order_id, int(amount)
                )
                
                if saved == True:
                    st.success(f"✅ {pending['name']}님, 예약이 확정되었습니다!")
                    st.balloons()
                    # 저장 완료 후 정보 초기화
                    st.session_state.pending_payment = {}
                    st.query_params.clear()
                else:
                    st.error(f"데이터베이스 저장 실패: {saved}")
            else:
                st.error(f"결제 승인 실패: {confirm.get('error')}")
    else:
        st.warning("세션이 만료되었습니다. 결제는 성공했으나 예약 정보가 유실되었습니다.")

elif payment_status == "fail":
    st.error("결제가 취소되었거나 실패했습니다.")
    st.query_params.clear()

# ------------------------------------------
# [STEP 2] 예약 정보 입력 폼
# ------------------------------------------
st.write("원장님, 테스트를 위해 예약 정보를 입력해주세요.")

with st.form("reservation_form"):
    col1, col2 = st.columns(2)
    with col1:
        name = st.text_input("신청자 이름", placeholder="예: 김철수")
    with col2:
        phone = st.text_input("연락처", placeholder="010-0000-0000")
    
    date = st.date_input("상담 희망 날짜")
    memo = st.text_area("요청 사항 (선택)")
    
    # 결제 버튼
    submit = st.form_submit_button(f"💳 {PAYMENT_AMOUNT:,}원 결제하기")

    if submit:
        if not name or not phone:
            st.error("이름과 연락처를 꼭 입력해주세요!")
        else:
            # 고유 주문번호 생성
            new_order_id = f"order_{uuid.uuid4().hex[:10]}"
            
            # 1. 입력 정보를 세션에 임시 저장 (결제하고 돌아올 때 쓰려고)
            st.session_state.pending_payment = {
                "name": name, "phone": phone, "date": str(date), 
                "memo": memo, "order_id": new_order_id, "amount": PAYMENT_AMOUNT
            }
            
            # 2. 토스 결제창 HTML 생성 (높이를 키웠습니다!)
            payment_html = f"""
            <html>
            <head>
              <script src="https://js.tosspayments.com/v1/payment"></script>
              <style>
                body {{ font-family: sans-serif; text-align: center; padding-top: 20px; }}
              </style>
            </head>
            <body>
              <h3>결제창을 불러오고 있습니다...</h3>
              <script>
                var clientKey = '{TOSS_CLIENT_KEY}';
                var tossPayments = TossPayments(clientKey);
                
                // 현재 페이지 주소 (돌아올 곳)
                var currentUrl = window.parent.location.href.split('?')[0];

                tossPayments.requestPayment('카드', {{
                  amount: {PAYMENT_AMOUNT},
                  orderId: '{new_order_id}',
                  orderName: '심리상담 예약',
                  customerName: '{name}',
                  successUrl: currentUrl + "?payment=success", 
                  failUrl: currentUrl + "?payment=fail",
                }})
                .catch(function (error) {{
                    if (error.code === 'USER_CANCEL') {{
                        // 사용자가 취소함
                    }} else {{
                        alert(error.message);
                    }}
                }});
              </script>
            </body>
            </html>
            """
            
            # [핵심 수정] 높이를 800으로 설정하여 결제창이 잘리지 않게 함
            components.html(payment_html, height=800, scrolling=True)

# ------------------------------------------
# [STEP 3] 관리자용 예약 명단 확인
# ------------------------------------------
st.markdown("---")
st.subheader("📋 실시간 예약 현황 (Admin View)")

# 데이터 불러오기
try:
    res = supabase.table("reservations").select("*").order("created_at", desc=True).execute()
    
    if res.data:
        for item in res.data:
            with st.expander(f"[{item['payment_status']}] {item['name']} - {item['date']}"):
                st.write(f"📞 연락처: {item['phone']}")
                st.write(f"📝 메모: {item.get('memo', '없음')}")
                st.write(f"💰 결제금액: {item.get('amount', 0):,}원")
                st.write(f"🔑 주문번호: {item['order_id']}")
                
                # 삭제 버튼
                if st.button("예약 삭제", key=item['id']):
                    supabase.table("reservations").delete().eq("id", item['id']).execute()
                    st.rerun()
    else:
        st.info("아직 접수된 예약이 없습니다.")
except Exception as e:
    st.error(f"데이터를 불러오는 중 오류가 발생했습니다: {e}")