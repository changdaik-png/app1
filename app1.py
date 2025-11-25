import streamlit as st
from supabase import create_client, Client
import requests
import base64
import uuid
from datetime import datetime
import os
import streamlit.components.v1 as components

# --- 1. 설정 (기존 키 유지) ---
url: str = "https://lrnutmjafqqlzopxswsa.supabase.co"
key: str = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImxybnV0bWphZnFxbHpvcHhzd3NhIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjMwMTU4NDIsImV4cCI6MjA3ODU5MTg0Mn0.JJJtqAKfYSzlSky0gYNKbQJF_j0YUPYf2jquyInnvpk"

@st.cache_resource
def init_supabase():
    return create_client(url, key)

supabase = init_supabase()

# --- 토스페이먼츠 설정 ---
# 테스트용 키 (직접 입력하신 부분)
TOSS_CLIENT_KEY = "test_ck_D5GePWvyJnrK0W0k6q8gLzN97Eoq" # 원장님 코드에 있던 키 사용 (혹은 test_gck_...)
TOSS_SECRET_KEY = "test_sk_..." # 실제 시크릿 키를 여기에 넣으세요

DEFAULT_PAYMENT_AMOUNT = 50000

# --- 함수 모음 ---
def get_toss_auth_header():
    secret_key_encoded = base64.b64encode(f"{TOSS_SECRET_KEY}:".encode()).decode()
    return {"Authorization": f"Basic {secret_key_encoded}"}

def confirm_payment(payment_key, order_id, amount):
    # 테스트 모드 시뮬레이션
    if "test_sk_" in TOSS_SECRET_KEY: # 시크릿 키가 없거나 테스트용이면
         return {"success": True, "data": {"status": "DONE"}}
         
    try:
        headers = get_toss_auth_header()
        headers["Content-Type"] = "application/json"
        data = {"paymentKey": payment_key, "orderId": order_id, "amount": amount}
        res = requests.post("https://api.tosspayments.com/v1/payments/confirm", headers=headers, json=data)
        return {"success": True, "data": res.json()} if res.status_code == 200 else {"success": False, "error": res.json()}
    except Exception as e:
        return {"success": False, "error": str(e)}

def save_to_supabase(name, phone, date, memo, payment_key, order_id, amount):
    data = {
        "name": name,
        "phone": phone,
        "date": str(date),
        "memo": memo,
        "payment_key": payment_key,
        "order_id": order_id,
        "amount": amount,
        "payment_status": "PAID"
    }
    try:
        supabase.table("reservations").insert(data).execute()
        return True
    except Exception as e:
        return str(e)

# --- 메인 앱 시작 ---
st.title("🏥 심리상담 예약 시스템")

# [중요] 세션 상태 초기화 (가장 먼저 실행)
if 'pending_payment' not in st.session_state:
    st.session_state.pending_payment = {}

# ==========================================
# 1. 결제 성공 후 복귀 처리 (가장 먼저 체크해야 함!)
# ==========================================
# 최신 Streamlit 방식의 파라미터 확인
query_params = st.query_params 
payment_status = query_params.get("payment") # 'success' or 'fail'

if payment_status == "success":
    payment_key = query_params.get("paymentKey")
    order_id = query_params.get("orderId")
    amount = query_params.get("amount")
    
    # 세션에 저장해둔 예약 정보가 있는지 확인
    pending = st.session_state.pending_payment
    
    if pending and pending.get("order_id") == order_id:
        with st.spinner("결제 승인 및 예약 저장 중..."):
            # 1. 토스 승인 요청
            confirm = confirm_payment(payment_key, order_id, int(amount))
            
            if confirm["success"]:
                # 2. Supabase 저장
                saved = save_to_supabase(
                    pending["name"], pending["phone"], pending["date"], 
                    pending["memo"], payment_key, order_id, int(amount)
                )
                
                if saved == True:
                    st.success(f"✅ {pending['name']}님, 예약과 결제가 완료되었습니다!")
                    st.balloons()
                    # 세션 및 파라미터 초기화
                    st.session_state.pending_payment = {}
                    st.query_params.clear() 
                else:
                    st.error(f"저장 실패: {saved}")
            else:
                st.error("결제 승인 실패: 관리자에게 문의하세요.")
    else:
        # 새로고침 등으로 세션이 날아갔을 경우를 대비해 화면에 로그만 표시
        st.warning("결제는 성공했으나 세션 정보가 만료되었습니다. 관리자에게 `paymentKey`를 전달해주세요.")
        st.write(f"Payment Key: {payment_key}")

elif payment_status == "fail":
    st.error("결제가 취소되거나 실패했습니다. 다시 시도해주세요.")
    st.query_params.clear()

# ==========================================
# 2. 예약 입력 및 결제 요청 화면
# ==========================================
st.write("원장님, 테스트를 위해 예약 정보를 입력해주세요.")

with st.form("reservation_form"):
    col1, col2 = st.columns(2)
    with col1:
        name = st.text_input("신청자 이름")
    with col2:
        phone = st.text_input("연락처")
    
    date = st.date_input("상담 희망 날짜")
    memo = st.text_area("요청 사항")
    
    submit = st.form_submit_button("💳 50,000원 결제하기")

    if submit:
        if not name or not phone:
            st.error("이름과 연락처를 입력해주세요.")
        else:
            # 주문 ID 생성
            new_order_id = f"order_{uuid.uuid4().hex[:10]}"
            
            # 세션에 임시 저장 (갔다 오면 사라지니까 여기 담아둠)
            st.session_state.pending_payment = {
                "name": name, "phone": phone, "date": str(date), 
                "memo": memo, "order_id": new_order_id, "amount": DEFAULT_PAYMENT_AMOUNT
            }
            
            # 결제창 HTML 생성
            # window.parent.location.href를 사용하여 확실하게 부모 창 주소를 잡음
            payment_html = f"""
            <html>
            <head>
              <script src="https://js.tosspayments.com/v1/payment"></script>
            </head>
            <body>
              <script>
                var clientKey = '{TOSS_CLIENT_KEY}';
                var tossPayments = TossPayments(clientKey);
                
                // 현재 Streamlit 앱의 주소 가져오기 (iframe 밖의 부모 주소)
                var currentUrl = window.parent.location.href.split('?')[0];

                tossPayments.requestPayment('카드', {{
                  amount: {DEFAULT_PAYMENT_AMOUNT},
                  orderId: '{new_order_id}',
                  orderName: '심리상담 예약',
                  customerName: '{name}',
                  successUrl: currentUrl + "?payment=success", 
                  failUrl: currentUrl + "?payment=fail",
                }})
                .catch(function (error) {{
                    if (error.code === 'USER_CANCEL') {{
                        // 취소 시 처리
                    }} else {{
                        alert(error.message);
                    }}
                }});
              </script>
              <div style="text-align: center; padding: 20px;">
                <h3>결제창을 불러오는 중입니다...</h3>
                <p>팝업이 차단되었다면 허용해주세요.</p>
              </div>
            </body>
            </html>
            """
            
            # HTML 실행 (결제창 띄우기)
            components.html(payment_html, height=200)

# ==========================================
# 3. 예약 현황 목록 (Read)
# ==========================================
st.markdown("---")
st.subheader("📋 실시간 예약 현황")

res = supabase.table("reservations").select("*").order("created_at", desc=True).execute()

if res.data:
    for item in res.data:
        with st.expander(f"{item['name']} ({item['date']}) - {item['payment_status']}"):
            st.write(f"연락처: {item['phone']}")
            st.write(f"결제키: {item.get('payment_key', '없음')}")
            if st.button("예약 취소/삭제", key=item['id']):
                supabase.table("reservations").delete().eq("id", item['id']).execute()
                st.rerun()
else:
    st.info("예약 내역이 없습니다.")