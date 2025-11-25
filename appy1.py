import streamlit as st
from supabase import create_client, Client
import requests
import base64
import uuid
from datetime import datetime
import os

# --- 1. 설정 ---
url: str = "https://lrnutmjafqqlzopxswsa.supabase.co"
key: str = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImxybnV0bWphZnFxbHpvcHhzd3NhIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjMwMTU4NDIsImV4cCI6MjA3ODU5MTg0Mn0.JJJtqAKfYSzlSky0gYNKbQJF_j0YUPYf2jquyInnvpk"
supabase: Client = create_client(url, key)

# --- 토스페이먼츠 설정 ---
# 환경 변수 또는 secrets에서 토스페이먼츠 키 가져오기
def get_toss_secret_key():
    """토스페이먼츠 시크릿 키 가져오기"""
    key = os.getenv("TOSS_SECRET_KEY", "")
    if not key and hasattr(st, 'secrets'):
        try:
            if isinstance(st.secrets, dict):
                key = st.secrets.get("TOSS_SECRET_KEY", "")
            else:
                key = getattr(st.secrets, "TOSS_SECRET_KEY", "")
        except:
            pass
    return key if key else "test_sk_..."

def get_toss_client_key():
    """토스페이먼츠 클라이언트 키 가져오기"""
    key = os.getenv("TOSS_CLIENT_KEY", "")
    if not key and hasattr(st, 'secrets'):
        try:
            if isinstance(st.secrets, dict):
                key = st.secrets.get("TOSS_CLIENT_KEY", "")
            else:
                key = getattr(st.secrets, "TOSS_CLIENT_KEY", "")
        except:
            pass
    return key if key else "test_ck_..."

TOSS_SECRET_KEY = get_toss_secret_key()
TOSS_CLIENT_KEY = get_toss_client_key()

# 기본 결제 금액 (원)
DEFAULT_PAYMENT_AMOUNT = 50000

# --- 토스페이먼츠 API 함수 ---
def get_toss_auth_header():
    """토스페이먼츠 API 인증 헤더 생성"""
    secret_key_encoded = base64.b64encode(f"{TOSS_SECRET_KEY}:".encode()).decode()
    return {"Authorization": f"Basic {secret_key_encoded}"}

def request_payment(order_id, amount, order_name, customer_name):
    """토스페이먼츠 결제 요청 (결제위젯 URL 생성)"""
    try:
        # 결제 요청 API 호출
        headers = get_toss_auth_header()
        headers["Content-Type"] = "application/json"
        
        # 결제 요청 데이터
        data = {
            "amount": amount,
            "orderId": order_id,
            "orderName": order_name,
            "customerName": customer_name,
            "successUrl": f"https://your-domain.com/success?orderId={order_id}",
            "failUrl": f"https://your-domain.com/fail?orderId={order_id}"
        }
        
        # 실제로는 결제위젯을 사용하지만, 여기서는 간단한 시뮬레이션
        # 실제 환경에서는 결제위젯 JavaScript를 사용해야 함
        return {"success": True, "paymentKey": f"test_payment_{order_id}", "orderId": order_id}
    except Exception as e:
        return {"success": False, "error": str(e)}

def confirm_payment(payment_key, order_id, amount):
    """토스페이먼츠 결제 승인"""
    # 테스트 모드 확인 (시크릿 키가 test_로 시작하면 테스트 모드)
    is_test_mode = TOSS_SECRET_KEY.startswith("test_") or TOSS_SECRET_KEY == "test_sk_..."
    
    if is_test_mode:
        # 테스트 모드: 실제 API 호출 없이 시뮬레이션
        return {
            "success": True, 
            "data": {
                "status": "DONE",
                "paymentKey": payment_key,
                "orderId": order_id,
                "totalAmount": amount,
                "approvedAt": datetime.now().isoformat()
            }
        }
    
    # 실제 운영 모드: 토스페이먼츠 API 호출
    try:
        headers = get_toss_auth_header()
        headers["Content-Type"] = "application/json"
        
        data = {
            "paymentKey": payment_key,
            "orderId": order_id,
            "amount": amount
        }
        
        response = requests.post(
            "https://api.tosspayments.com/v1/payments/confirm",
            headers=headers,
            json=data,
            timeout=10
        )
        
        if response.status_code == 200:
            return {"success": True, "data": response.json()}
        else:
            error_data = response.json() if response.text else {"code": "UNKNOWN_ERROR", "message": str(response.status_code)}
            return {"success": False, "error": error_data}
    except requests.exceptions.RequestException as e:
        # 네트워크 오류 등
        return {"success": False, "error": {"code": "NETWORK_ERROR", "message": f"API 호출 실패: {str(e)}"}}
    except Exception as e:
        # 기타 오류
        return {"success": False, "error": {"code": "UNKNOWN_ERROR", "message": str(e)}}

def cancel_payment(payment_key, cancel_reason="고객 요청"):
    """토스페이먼츠 결제 취소"""
    # 테스트 모드 확인
    is_test_mode = TOSS_SECRET_KEY.startswith("test_") or TOSS_SECRET_KEY == "test_sk_..."
    
    if is_test_mode:
        # 테스트 모드: 시뮬레이션
        return {
            "success": True, 
            "data": {
                "status": "CANCELED",
                "paymentKey": payment_key,
                "canceledAt": datetime.now().isoformat()
            }
        }
    
    # 실제 운영 모드: 토스페이먼츠 API 호출
    try:
        headers = get_toss_auth_header()
        headers["Content-Type"] = "application/json"
        
        data = {
            "cancelReason": cancel_reason
        }
        
        response = requests.post(
            f"https://api.tosspayments.com/v1/payments/{payment_key}/cancel",
            headers=headers,
            json=data,
            timeout=10
        )
        
        if response.status_code == 200:
            return {"success": True, "data": response.json()}
        else:
            error_data = response.json() if response.text else {"code": "UNKNOWN_ERROR", "message": str(response.status_code)}
            return {"success": False, "error": error_data}
    except requests.exceptions.RequestException as e:
        return {"success": False, "error": {"code": "NETWORK_ERROR", "message": f"API 호출 실패: {str(e)}"}}
    except Exception as e:
        return {"success": False, "error": {"code": "UNKNOWN_ERROR", "message": str(e)}}

# --- 예약 함수 (결제 정보 포함) ---
def save_to_supabase(name, phone, date, memo, payment_key=None, order_id=None, amount=None, payment_status="PENDING"):
    """예약 정보를 Supabase에 저장 (결제 정보 포함)"""
    data = {
        "name": name,
        "phone": phone,
        "date": str(date),
        "memo": memo,
        "payment_key": payment_key,
        "order_id": order_id,
        "amount": amount,
        "payment_status": payment_status
    }
    try:
        supabase.table("reservations").insert(data).execute()
        return True
    except Exception as e:
        return str(e)

def update_payment_status(reservation_id, payment_key, payment_status):
    """예약의 결제 상태 업데이트"""
    try:
        supabase.table("reservations").update({
            "payment_key": payment_key,
            "payment_status": payment_status
        }).eq("id", reservation_id).execute()
        return True
    except Exception as e:
        return str(e)

# --- 예약 목록 조회 함수 ---
def get_reservations():
    """Supabase에서 모든 예약 목록을 가져옵니다"""
    try:
        response = supabase.table("reservations").select("*").order("date", desc=False).order("created_at", desc=True).execute()
        return response.data if response.data else []
    except Exception as e:
        st.error(f"예약 목록 조회 실패: {str(e)}")
        return []

# --- 3. 화면 구성 (Streamlit) ---
st.title("🏥 심리상담 예약 시스템")
st.write("원장님, 테스트를 위해 예약 정보를 입력해주세요.")

# 테스트 모드 안내
is_test_mode = TOSS_SECRET_KEY.startswith("test_") or TOSS_SECRET_KEY == "test_sk_..."
if is_test_mode:
    st.info("ℹ️ **테스트 모드**: 실제 결제가 발생하지 않으며, 결제가 시뮬레이션됩니다. 운영 환경에서는 실제 토스페이먼츠 API 키를 설정하세요.")

# 세션 상태 초기화
if 'payment_completed' not in st.session_state:
    st.session_state.payment_completed = False
if 'current_order_id' not in st.session_state:
    st.session_state.current_order_id = None
if 'current_payment_key' not in st.session_state:
    st.session_state.current_payment_key = None
if 'current_amount' not in st.session_state:
    st.session_state.current_amount = None

# 입력 폼 만들기
with st.form("reservation_form"):
    col1, col2 = st.columns(2)
    with col1:
        name = st.text_input("신청자 이름", placeholder="예: 김철수")
    with col2:
        phone = st.text_input("연락처", placeholder="010-0000-0000")
    
    date = st.date_input("상담 희망 날짜")
    memo = st.text_area("상담 요청 내용 (선택사항)")
    
    # 결제 금액 표시
    st.markdown("---")
    st.markdown(f"### 💰 결제 금액: {DEFAULT_PAYMENT_AMOUNT:,}원")
    
    # 결제 버튼
    payment_submitted = st.form_submit_button("💳 결제하기", type="primary", use_container_width=True)

    if payment_submitted:
        if not name or not phone:
            st.error("이름과 연락처는 필수입니다!")
        else:
            # 주문번호 생성
            order_id = f"order_{uuid.uuid4().hex[:16]}"
            order_name = f"심리상담 예약 - {name}"
            
            # 결제 요청
            with st.spinner("결제를 진행 중입니다..."):
                payment_request = request_payment(order_id, DEFAULT_PAYMENT_AMOUNT, order_name, name)
                
                if payment_request.get("success"):
                    payment_key = payment_request.get("paymentKey")
                    
                    # 결제 승인 (검증 포함)
                    confirm_result = confirm_payment(payment_key, order_id, DEFAULT_PAYMENT_AMOUNT)
                    
                    if confirm_result.get("success"):
                        payment_data = confirm_result.get("data", {})
                        
                        # 결제 검증: 금액 확인
                        confirmed_amount = payment_data.get("totalAmount", DEFAULT_PAYMENT_AMOUNT)
                        if confirmed_amount == DEFAULT_PAYMENT_AMOUNT:
                            # 결제 완료 후 예약 저장
                            save_result = save_to_supabase(
                                name, phone, date, memo,
                                payment_key=payment_key,
                                order_id=order_id,
                                amount=DEFAULT_PAYMENT_AMOUNT,
                                payment_status="PAID"
                            )
                            
                            if save_result == True:
                                st.success(f"✅ 결제가 완료되었고, {name}님의 예약이 확정되었습니다!")
                                st.balloons()
                                
                                # 세션 상태 업데이트
                                st.session_state.payment_completed = True
                                st.session_state.current_order_id = order_id
                                st.session_state.current_payment_key = payment_key
                                st.session_state.current_amount = DEFAULT_PAYMENT_AMOUNT
                                
                                st.rerun()
                            else:
                                st.error(f"예약 저장 실패: {save_result}")
                        else:
                            st.error(f"❌ 결제 금액이 일치하지 않습니다. (요청: {DEFAULT_PAYMENT_AMOUNT:,}원, 승인: {confirmed_amount:,}원)")
                    else:
                        error_info = confirm_result.get('error', {})
                        error_code = error_info.get('code', 'UNKNOWN')
                        error_message = error_info.get('message', str(error_info))
                        st.error(f"❌ 결제 승인 실패: [{error_code}] {error_message}")
                else:
                    st.error(f"결제 요청 실패: {payment_request.get('error')}")

# 결제 취소 섹션
if st.session_state.payment_completed and st.session_state.current_payment_key:
    st.markdown("---")
    st.warning("⚠️ 결제를 취소하시겠습니까?")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔄 결제 취소하기", use_container_width=True):
            with st.spinner("결제 취소 중..."):
                cancel_result = cancel_payment(st.session_state.current_payment_key, "고객 요청")
                
                if cancel_result.get("success"):
                    st.success("✅ 결제가 취소되었습니다.")
                    # 예약 삭제 또는 상태 업데이트
                    try:
                        supabase.table("reservations").delete().eq("order_id", st.session_state.current_order_id).execute()
                        st.session_state.payment_completed = False
                        st.session_state.current_order_id = None
                        st.session_state.current_payment_key = None
                        st.rerun()
                    except Exception as e:
                        st.error(f"예약 삭제 실패: {str(e)}")
                else:
                    st.error(f"결제 취소 실패: {cancel_result.get('error')}")

# --- 현재 예약된 명단 표시 ---
st.markdown("---")
st.subheader("📋 현재 예약된 명단")

# 예약 목록 가져오기
reservations = get_reservations()

if not reservations:
    st.info("📭 아직 예약된 내역이 없습니다.")
else:
    # 예약 목록을 카드 형태로 표시
    for idx, reservation in enumerate(reservations, 1):
        with st.container():
            col1, col2, col3, col4, col5 = st.columns([2, 2, 2, 1, 1])
            
            with col1:
                st.write(f"**{reservation.get('name', 'N/A')}**")
            
            with col2:
                st.write(f"📞 {reservation.get('phone', 'N/A')}")
            
            with col3:
                date_str = reservation.get('date', 'N/A')
                st.write(f"📅 {date_str}")
            
            # 결제 상태 표시
            payment_status = reservation.get('payment_status', 'N/A')
            payment_key = reservation.get('payment_key')
            amount = reservation.get('amount', 0)
            
            with col4:
                if payment_status == "PAID":
                    st.success("💰 결제완료")
                elif payment_status == "CANCELED":
                    st.error("❌ 취소됨")
                else:
                    st.warning("⏳ 대기중")
            
            with col5:
                # 결제 취소 버튼 (결제 완료된 경우만)
                if payment_status == "PAID" and payment_key:
                    if st.button("🗑️ 취소", key=f"cancel_{reservation.get('id', idx)}"):
                        with st.spinner("결제 취소 중..."):
                            cancel_result = cancel_payment(payment_key, "관리자 취소")
                            
                            if cancel_result.get("success"):
                                # 결제 상태 업데이트
                                update_payment_status(reservation.get('id'), payment_key, "CANCELED")
                                st.success("결제가 취소되었습니다!")
                                st.rerun()
                            else:
                                st.error(f"취소 실패: {cancel_result.get('error')}")
                else:
                    # 삭제 버튼 (결제가 안 된 경우)
                    if st.button("🗑️", key=f"delete_{reservation.get('id', idx)}"):
                        try:
                            supabase.table("reservations").delete().eq("id", reservation.get('id')).execute()
                            st.success("예약이 삭제되었습니다!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"삭제 실패: {str(e)}")
            
            # 결제 정보 표시
            if amount:
                st.caption(f"💳 결제 금액: {amount:,}원")
            
            # 메모가 있으면 표시
            memo = reservation.get('memo', '')
            if memo:
                st.caption(f"💬 {memo}")
            
            # 구분선
            if idx < len(reservations):
                st.markdown("---")
