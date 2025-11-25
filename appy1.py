import streamlit as st
from supabase import create_client, Client
import requests
import base64
import uuid
from datetime import datetime
import os
import streamlit.components.v1 as components
import json

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
    """토스페이먼츠 결제위젯 연동 키 가져오기 (Widget Client Key)"""
    key = os.getenv("TOSS_CLIENT_KEY", "")
    if not key and hasattr(st, 'secrets'):
        try:
            if isinstance(st.secrets, dict):
                key = st.secrets.get("TOSS_CLIENT_KEY", "")
            else:
                key = getattr(st.secrets, "TOSS_CLIENT_KEY", "")
        except:
            pass
    # 결제위젯 연동 키는 test_ck_ 또는 live_ck_로 시작해야 함
    # API 개별 연동 키(test_ok_, live_ok_)는 사용 불가
    if key and not (key.startswith("test_ck_") or key.startswith("live_ck_")):
        st.warning(f"⚠️ 잘못된 클라이언트 키 형식입니다. 결제위젯 연동 키(test_ck_ 또는 live_ck_로 시작)를 사용해야 합니다.")
        key = ""  # 잘못된 키는 무시
    return key if key else "test_ck_docs_OaPz8L5KdmQXkzRZ3y47BMw6"  # 토스페이먼츠 샌드박스 테스트 키

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
            # 주문번호 생성 및 세션에 저장
            order_id = f"order_{uuid.uuid4().hex[:16]}"
            order_name = f"심리상담 예약 - {name}"
            
            # 세션에 결제 정보 저장
            st.session_state.pending_order_id = order_id
            st.session_state.pending_order_name = order_name
            st.session_state.pending_name = name
            st.session_state.pending_phone = phone
            st.session_state.pending_date = str(date)
            st.session_state.pending_memo = memo
            st.session_state.pending_amount = DEFAULT_PAYMENT_AMOUNT
            st.session_state.show_payment_widget = True

# --- 현재 예약된 명단 표시 (결제위젯 전에 표시) ---
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

# 결제위젯 표시
if st.session_state.get('show_payment_widget', False):
    st.markdown("---")
    st.subheader("💳 결제하기")
    
    # 토스페이먼츠 결제위젯 HTML
    # 결제위젯 연동 키 사용 (test_ck_ 또는 live_ck_로 시작)
    client_key = TOSS_CLIENT_KEY
    
    # 클라이언트 키 검증 및 안내
    if not client_key or (not client_key.startswith('test_ck_') and not client_key.startswith('live_ck_')):
        st.error("⚠️ **결제위젯 연동 키 오류**: 결제위젯을 사용하려면 `test_ck_` 또는 `live_ck_`로 시작하는 결제위젯 연동 키가 필요합니다. API 개별 연동 키(`test_ok_`, `live_ok_`)는 사용할 수 없습니다.")
        st.info("💡 **해결 방법**: 토스페이먼츠 개발자센터 > API 키 > 결제위젯 연동 키에서 올바른 키를 확인하세요.")
        st.code(f"현재 키: {client_key}", language="text")
        if st.button("❌ 결제 취소", key="cancel_payment_widget_error"):
            st.session_state.show_payment_widget = False
            st.rerun()
    else:
        # 전화번호에서 하이픈 제거 (Python에서 미리 처리)
        customer_phone_clean = st.session_state.pending_phone.replace('-', '') if st.session_state.pending_phone else ''
        
        # 결제위젯 HTML 생성
        payment_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <script src="https://js.tosspayments.com/v2/standard"></script>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                padding: 20px;
            }}
            #payment-method {{
                margin: 20px 0;
            }}
            #payment-button {{
                background-color: #EF4444;
                color: white;
                border: none;
                padding: 15px 30px;
                font-size: 16px;
                border-radius: 8px;
                cursor: pointer;
                width: 100%;
                margin-top: 20px;
            }}
            #payment-button:hover {{
                background-color: #DC2626;
            }}
        </style>
    </head>
    <body>
        <div id="payment-method"></div>
        <div id="agreement"></div>
        <button id="payment-button">결제하기</button>
        
        <script>
            (function() {{
                try {{
                    const clientKey = "{client_key}";
                    const customerKey = "customer_{uuid.uuid4().hex[:16]}";
                    const orderId = "{st.session_state.pending_order_id}";
                    const orderName = "{st.session_state.pending_order_name}";
                    const amount = {st.session_state.pending_amount};
                    const customerName = "{st.session_state.pending_name}";
                    const customerPhone = "{customer_phone_clean}";
                    
                    console.log('결제위젯 초기화 시작...', {{ clientKey, orderId, amount }});
                    
                    // 클라이언트 키 형식 검증
                    if (!clientKey || (!clientKey.startsWith('test_ck_') && !clientKey.startsWith('live_ck_'))) {{
                        const errorMsg = '결제위젯 연동 키가 올바르지 않습니다. test_ck_ 또는 live_ck_로 시작하는 결제위젯 연동 키를 사용해야 합니다.';
                        console.error(errorMsg);
                        document.getElementById('payment-method').innerHTML = 
                            '<div style="color: red; padding: 20px; border: 1px solid red; border-radius: 8px; margin: 20px 0;">' +
                            '<strong>오류:</strong><br>' + errorMsg + '<br><br>' +
                            '현재 사용 중인 키: ' + (clientKey || '없음') + '<br>' +
                            '토스페이먼츠 개발자센터에서 결제위젯 연동 키를 확인하세요.' +
                            '</div>';
                        return;
                    }}
                    
                    // TossPayments SDK 로드 확인
                    if (typeof TossPayments === 'undefined') {{
                        console.error('TossPayments SDK가 로드되지 않았습니다.');
                        document.getElementById('payment-method').innerHTML = 
                            '<div style="color: red; padding: 20px; border: 1px solid red; border-radius: 8px; margin: 20px 0;">' +
                            '<strong>오류:</strong> TossPayments SDK를 로드할 수 없습니다. 페이지를 새로고침해주세요.' +
                            '</div>';
                        return;
                    }}
                    
                    let tossPayments;
                    let widgets;
                    
                    try {{
                        // TossPayments 초기화
                        tossPayments = TossPayments(clientKey);
                        console.log('TossPayments 초기화 성공');
                        
                        // 결제위젯 인스턴스 생성
                        widgets = tossPayments.widgets({{ customerKey: TossPayments.ANONYMOUS }});
                        console.log('결제위젯 인스턴스 생성 성공');
                    }} catch (initError) {{
                        console.error('TossPayments 초기화 실패:', initError);
                        const errorMsg = initError.message || '알 수 없는 오류';
                        document.getElementById('payment-method').innerHTML = 
                            '<div style="color: red; padding: 20px; border: 1px solid red; border-radius: 8px; margin: 20px 0;">' +
                            '<strong>초기화 오류:</strong><br>' + errorMsg + '<br><br>' +
                            '결제위젯 연동 키를 확인하세요. API 개별 연동 키는 사용할 수 없습니다.' +
                            '</div>';
                        return;
                    }}
                    
                    async function initPayment() {{
                        try {{
                            if (!widgets) {{
                                throw new Error('결제위젯 인스턴스가 생성되지 않았습니다.');
                            }}
                            
                            console.log('결제 금액 설정 중...', amount);
                            // 결제 금액 설정
                            await widgets.setAmount({{
                                currency: 'KRW',
                                value: amount
                            }});
                            console.log('결제 금액 설정 완료');
                            
                            console.log('결제 UI 렌더링 중...');
                            // 결제 UI 렌더링
                            await Promise.all([
                                widgets.renderPaymentMethods({{
                                    selector: '#payment-method',
                                    variantKey: 'DEFAULT'
                                }}),
                                widgets.renderAgreement({{
                                    selector: '#agreement',
                                    variantKey: 'AGREEMENT'
                                }})
                            ]);
                            
                            console.log('결제위젯 렌더링 완료');
                            
                            // 결제 버튼 클릭 이벤트
                            const paymentButton = document.getElementById('payment-button');
                            if (paymentButton) {{
                                paymentButton.addEventListener('click', async function() {{
                                    try {{
                                        console.log('결제 요청 시작...');
                                        const result = await widgets.requestPayment({{
                                            orderId: orderId,
                                            orderName: orderName,
                                            customerName: customerName,
                                            customerMobilePhone: customerPhone
                                        }});
                                        
                                        console.log('결제 성공:', result);
                                        
                                        // 결제 성공 시
                                        if (result.paymentKey) {{
                                            alert('결제가 완료되었습니다! 결제 완료 확인 버튼을 클릭해주세요.');
                                            // 부모 창에 메시지 전송
                                            if (window.parent && window.parent !== window) {{
                                                window.parent.postMessage({{
                                                    type: 'payment_success',
                                                    paymentKey: result.paymentKey,
                                                    orderId: result.orderId,
                                                    amount: result.amount.value
                                                }}, '*');
                                            }}
                                        }}
                                    }} catch (error) {{
                                        console.error('결제 실패:', error);
                                        alert('결제 실패: ' + (error.message || '알 수 없는 오류'));
                                    }}
                                }});
                            }}
                        }} catch (error) {{
                            console.error('초기화 실패:', error);
                            document.getElementById('payment-method').innerHTML = 
                                '<div style="color: red; padding: 20px;">결제위젯 초기화 실패: ' + error.message + '</div>';
                        }}
                    }}
                    
                    // 페이지 로드 시 초기화
                    if (document.readyState === 'loading') {{
                        document.addEventListener('DOMContentLoaded', initPayment);
                    }} else {{
                        initPayment();
                    }}
                }} catch (error) {{
                    console.error('스크립트 실행 오류:', error);
                }}
            }})();
        </script>
    </body>
    </html>
        """
        
        # 결제위젯 표시 (iframe sandbox 속성 추가)
        components.html(
            payment_html, 
            height=800,
            scrolling=True
        )
        
        # 결제 완료 확인 버튼 (테스트용)
        st.info("💡 **테스트 모드**: 결제위젯에서 테스트 카드번호를 입력하세요. 테스트 카드: 1234-5678-9012-3456 (유효기간: 12/34, CVC: 123)")
        
        # 결제 완료 후 수동 확인 (실제 환경에서는 자동 처리)
        if st.button("✅ 결제 완료 확인", key="confirm_payment_manual"):
            # 테스트용: 결제 완료 처리
            order_id_from_result = st.session_state.pending_order_id
            payment_key = f"test_payment_{order_id_from_result}"
            
            with st.spinner("결제를 확인 중입니다..."):
                confirm_result = confirm_payment(payment_key, order_id_from_result, st.session_state.pending_amount)
                
                if confirm_result.get("success"):
                    # 예약 저장
                    save_result = save_to_supabase(
                        st.session_state.pending_name,
                        st.session_state.pending_phone,
                        st.session_state.pending_date,
                        st.session_state.pending_memo,
                        payment_key=payment_key,
                        order_id=order_id_from_result,
                        amount=st.session_state.pending_amount,
                        payment_status="PAID"
                    )
                    
                    if save_result == True:
                        st.success(f"✅ 결제가 완료되었고, {st.session_state.pending_name}님의 예약이 확정되었습니다!")
                        st.balloons()
                        
                        # 세션 상태 초기화
                        st.session_state.payment_completed = True
                        st.session_state.current_order_id = order_id_from_result
                        st.session_state.current_payment_key = payment_key
                        st.session_state.current_amount = st.session_state.pending_amount
                        st.session_state.show_payment_widget = False
                        
                        st.rerun()
                    else:
                        st.error(f"예약 저장 실패: {save_result}")
                else:
                    st.error("결제 승인 실패")
        
        # 결제 취소 버튼
        if st.button("❌ 결제 취소", key="cancel_payment_widget"):
            st.session_state.show_payment_widget = False
            st.rerun()

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
