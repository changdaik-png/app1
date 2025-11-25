import streamlit as st
from supabase import create_client, Client
import requests
import base64
import uuid
import streamlit.components.v1 as components

# 1. 페이지 기본 설정 (가장 윗줄에 있어야 함)
st.set_page_config(page_title="심리상담 예약 시스템", layout="wide")

# ==========================================
# 2. 설정 및 키 값 불러오기 (안전장치 포함)
# ==========================================
try:
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
    TOSS_CLIENT_KEY = st.secrets["TOSS_CLIENT_KEY"]
    TOSS_SECRET_KEY = st.secrets["TOSS_SECRET_KEY"]
except Exception:
    st.error("🚨 설정을 찾을 수 없습니다!")
    st.warning("프로젝트 폴더 안에 .streamlit/secrets.toml 파일을 만들고 키 값을 넣어주세요.")
    st.stop()

# Supabase 연결
@st.cache_resource
def init_supabase():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

try:
    supabase = init_supabase()
except Exception as e:
    st.error(f"Supabase 연결 실패: {e}")
    st.stop()

# 상담료 설정
PAYMENT_AMOUNT = 50000

# ==========================================
# 3. 기능 함수 (결제 승인 & DB 저장)
# ==========================================

def confirm_payment(payment_key, order_id, amount):
    """토스 서버에 '진짜 결제됐냐'고 물어보는 함수"""
    # 시크릿 키 암호화 (Basic Auth)
    secret_key_encoded = base64.b64encode(f"{TOSS_SECRET_KEY}:".encode()).decode()
    headers = {
        "Authorization": f"Basic {secret_key_encoded}",
        "Content-Type": "application/json"
    }
    data = {"paymentKey": payment_key, "orderId": order_id, "amount": amount}
    
    try:
        res = requests.post("https://api.tosspayments.com/v1/payments/confirm", headers=headers, json=data)
        return {"success": True, "data": res.json()} if res.status_code == 200 else {"success": False, "error": res.json()}
    except Exception as e:
        return {"success": False, "error": str(e)}

def save_reservation(name, phone, date, memo, payment_key, order_id, amount):
    """결제 완료된 정보를 Supabase에 저장하는 함수"""
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

# ==========================================
# 4. 메인 화면 로직
# ==========================================

st.title("🏥 심리상담 예약 & 결제 시스템")

# (1) 세션 상태 초기화 (결제하고 돌아와도 정보 기억하기 위함)
if 'pending_payment' not in st.session_state:
    st.session_state.pending_payment = {}

# (2) 결제 성공 후 복귀 처리 (가장 먼저 실행)
query_params = st.query_params
payment_status = query_params.get("payment")

if payment_status == "success":
    payment_key = query_params.get("paymentKey")
    order_id = query_params.get("orderId")
    amount = query_params.get("amount")
    
    # 아까 저장해둔 예약자 정보 꺼내기
    pending = st.session_state.pending_payment
    
    # 정보가 일치하면 승인 및 저장 진행
    if pending and pending.get("order_id") == order_id:
        with st.spinner("결제 승인 중입니다... 잠시만 기다려주세요."):
            confirm = confirm_payment(payment_key, order_id, int(amount))
            
            if confirm["success"]:
                # DB 저장
                saved = save_reservation(
                    pending["name"], pending["phone"], pending["date"], 
                    pending["memo"], payment_key, order_id, int(amount)
                )
                
                if saved == True:
                    st.success(f"✅ {pending['name']}님, 예약이 확정되었습니다!")
                    st.balloons()
                    # 세션 및 URL 청소
                    st.session_state.pending_payment = {}
                    st.query_params.clear()
                else:
                    st.error(f"❌ 저장 실패: {saved}")
                    st.info("💡 힌트: Supabase에 'reservations' 테이블이 있는지 확인하세요.")
            else:
                st.error(f"❌ 결제 승인 실패: {confirm.get('error')}")
    else:
        st.warning("⚠️ 세션이 만료되었습니다. (결제는 성공했으나 예약 정보가 유실됨)")

elif payment_status == "fail":
    st.error("결제가 취소되었습니다.")
    st.query_params.clear()

# (3) 예약 정보 입력 폼
st.markdown("---")
st.subheader("📝 예약 신청")

with st.form("reservation_form"):
    col1, col2 = st.columns(2)
    name = col1.text_input("신청자 성함")
    phone = col2.text_input("연락처 (- 없이 입력)")
    
    date = st.date_input("희망 상담 날짜")
    memo = st.text_area("상담 요청 내용 (선택)")
    
    # 결제 버튼
    submit = st.form_submit_button(f"💳 {PAYMENT_AMOUNT:,}원 결제하기")

    if submit:
        if not name or not phone:
            st.error("성함과 연락처를 꼭 입력해주세요!")
        else:
            # 고유 주문번호 생성
            new_order_id = f"order_{uuid.uuid4().hex[:10]}"
            
            # 세션에 정보 임시 저장
            st.session_state.pending_payment = {
                "name": name, "phone": phone, "date": str(date), 
                "memo": memo, "order_id": new_order_id, "amount": PAYMENT_AMOUNT
            }
            
            # -------------------------------------------------------
            # [핵심] 토스 결제창 (높이 800px + 부모창 리다이렉트)
            # -------------------------------------------------------
            payment_html = f"""
            <html>
            <head>
              <script src="https://js.tosspayments.com/v1/payment"></script>
              <style>body {{ font-family: sans-serif; text-align: center; }}</style>
            </head>
            <body>
              <h3>결제창을 불러오고 있습니다...</h3>
              <script>
                var clientKey = '{TOSS_CLIENT_KEY}';
                var tossPayments = TossPayments(clientKey);
                
                // 현재 창의 부모(원래 Streamlit 페이지) 주소를 가져옴
                var currentUrl = window.parent.location.href.split('?')[0];

                tossPayments.requestPayment('카드', {{
                  amount: {PAYMENT_AMOUNT},
                  orderId: '{new_order_id}',
                  orderName: '심리상담 1회 예약',
                  customerName: '{name}',
                  successUrl: currentUrl + "?payment=success", 
                  failUrl: currentUrl + "?payment=fail",
                }})
                .catch(function (error) {{
                    if (error.code === 'USER_CANCEL') {{
                        // 취소 시 조용히 있음
                    }} else {{
                        alert(error.message);
                    }}
                }});
              </script>
            </body>
            </html>
            """
            # iframe 높이를 800으로 설정하여 결제창 잘림 방지
            components.html(payment_html, height=800, scrolling=True)

# (4) 관리자용 예약 명단 (하단 배치)
st.markdown("---")
st.subheader("📋 [관리자용] 실시간 예약 현황")

try:
    res = supabase.table("reservations").select("*").order("created_at", desc=True).execute()
    
    if res.data:
        # 데이터를 깔끔한 표나 카드로 보여주기
        for item in res.data:
            with st.expander(f"{item['date']} - {item['name']} ({item['payment_status']})"):
                st.write(f"📞 연락처: {item['phone']}")
                st.write(f"📝 메모: {item.get('memo', '-')}")
                st.write(f"💰 금액: {item.get('amount', 0):,}원")
                st.write(f"🔑 주문번호: {item['order_id']}")
                
                # 삭제 기능
                if st.button("내역 삭제", key=item['id']):
                    supabase.table("reservations").delete().eq("id", item['id']).execute()
                    st.rerun()
    else:
        st.info("아직 접수된 예약이 없습니다.")

except Exception as e:
    st.error("데이터를 불러오지 못했습니다.")
    st.code(str(e))