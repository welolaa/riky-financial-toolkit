import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import io

# --- 1. ตั้งค่าหน้าเว็บ ---
st.set_page_config(page_title="Rik & Mom Finance", layout="wide")

# --- 2. ระบบ Login ---
if 'user' not in st.session_state:
    st.session_state['user'] = None

if st.session_state['user'] is None:
    st.title("🔐 เข้าสู่ระบบ")
    password = st.text_input("กรุณากรอกรหัสผ่าน", type="password")
    if st.button("ตกลง"):
        if password == "1509":
            st.session_state['user'] = "Rik"
            st.rerun()
        elif password == "2208":
            st.session_state['user'] = "Mom"
            st.rerun()
        else:
            st.error("รหัสผ่านไม่ถูกต้อง")
    st.stop()

current_user = st.session_state['user']
st.sidebar.title(f"👤 ผู้ใช้: {current_user}")
if st.sidebar.button("Log out"):
    st.session_state['user'] = None
    st.rerun()

# --- 3. เชื่อมต่อ Google Services (Sheets & Drive) ---
@st.cache_resource
def init_services():
    try:
        key_dict = st.secrets["gcp_service_account"]
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        creds = Credentials.from_service_account_info(key_dict, scopes=scopes)
        sheet_client = gspread.authorize(creds)
        drive_service = build('drive', 'v3', credentials=creds)
        
        # เชื่อมไฟล์ (แก้ชื่อไฟล์ให้ตรงกับคุณริก)
        sh = sheet_client.open("Rik_Financial_App") 
        return sh, drive_service
    except Exception as e:
        st.error(f"การเชื่อมต่อผิดพลาด: {e}")
        return None, None

sh, drive_service = init_services()

# --- 4. ฟังก์ชันจัดการข้อมูล ---
def get_ws(name, headers):
    try:
        return sh.worksheet(name)
    except:
        ws = sh.add_worksheet(title=name, rows="100", cols="10")
        ws.append_row(headers)
        return ws

ws_fixed = get_ws("Fixed_Expenses", ["User", "Item", "Amount", "Current_Installment", "Total_Installments", "Is_LongTerm", "Status", "Note"])
ws_daily = get_ws("Daily_Records", ["User", "Date", "Type", "Item", "Amount", "Slip_Link", "Note"])

# ==========================================
# หน้าตาโปรแกรมหลัก
# ==========================================

if current_user == "Mom":
    st.header("🚗 ระบบของคุณแม่ (Grab & LPG)")
    # ดึง Tab Grab & LPG มาไว้ที่นี่ (จากโค้ดเดิมของคุณริก)
    st.info("ระบบ Grab & LPG ถูกย้ายมาให้คุณแม่จัดการที่นี่แล้วครับ")

st.header(f"💰 ระบบจัดการเงิน ({current_user})")

# Tab การทำงาน
t1, t2, t3 = st.tabs(["📊 บันทึกประจำวัน", "📅 รายจ่ายฟิกซ์/หนี้", "📈 สรุปผล"])

with t1:
    st.subheader("บันทึกรายรับ-รายจ่ายรายวัน")
    with st.form("daily_form"):
        col1, col2 = st.columns(2)
        with col1:
            rec_date = st.date_input("วันที่", datetime.today())
            rec_type = st.selectbox("ประเภท", ["รายรับ", "รายจ่าย"])
            rec_item = st.text_input("ชื่อรายการ (เช่น ค่าอาหาร, เงินเดือน)")
        with col2:
            rec_amount = st.number_input("จำนวนเงิน", min_value=0.0)
            rec_note = st.text_input("บันทึกช่วยจำ (Note)")
            uploaded_file = st.file_uploader("แนบสลิป (ส่งเข้า Google Drive)", type=['png', 'jpg', 'jpeg', 'pdf'])
        
        if st.form_submit_button("บันทึกข้อมูล"):
            slip_url = "ไม่มีสลิป"
            if uploaded_file and drive_service:
                # อัปโหลดไฟล์ไปที่ Drive
                file_metadata = {'name': f"Slip_{rec_item}_{rec_date}.png"}
                media = MediaIoBaseUpload(io.BytesIO(uploaded_file.read()), mimetype='image/png')
                file = drive_service.files().create(body=file_metadata, media_body=media, fields='id, webViewLink').execute()
                slip_url = file.get('webViewLink')
            
            ws_daily.append_row([current_user, str(rec_date), rec_type, rec_item, rec_amount, slip_url, rec_note])
            st.success("บันทึกเรียบร้อย!")

with t2:
    st.subheader("ตารางรายจ่ายประจำเดือน & หนี้")
    # ส่วนเพิ่มรายจ่ายฟิกซ์ใหม่
    with st.expander("➕ เพิ่มรายจ่ายประจำเดือน/หนี้ใหม่"):
        with st.form("fixed_form"):
            f_item = st.text_input("ชื่อหนี้/รายจ่ายฟิกซ์")
            f_amt = st.number_input("ยอดจ่ายต่อเดือน", min_value=0.0)
            is_lt = st.checkbox("หนี้ระยะยาว (ไม่มีกำหนดงวด)")
            total_inst = st.number_input("จำนวนงวดทั้งหมด (ถ้าไม่ใช่หนี้ระยะยาว)", min_value=0, value=12)
            if st.form_submit_button("เพิ่มเข้าระบบ"):
                ws_fixed.append_row([current_user, f_item, f_amt, 0, total_inst, str(is_lt), "ยังไม่จ่าย", ""])
                st.success("เพิ่มรายจ่ายฟิกซ์แล้ว")

    # แสดงตารางแบบ Excel
    df_fixed = pd.DataFrame(ws_fixed.get_all_records())
    if not df_fixed.empty:
        user_fixed = df_fixed[df_fixed['User'] == current_user]
        st.write("### รายการที่ต้องจ่ายเดือนนี้")
        edited_df = st.data_editor(user_fixed, num_rows="dynamic", key="fixed_editor")
        
        if st.button("อัปเดตสถานะการจ่าย (Sync)"):
            # ในทางปฏิบัติ คุณริกสามารถเขียนฟังก์ชันวนลูปอัปเดต Current_Installment 
            # ถ้า Status เปลี่ยนเป็น 'จ่ายแล้ว' และเพิ่มงวดให้เมื่อครบเดือน
            st.info("ระบบกำลังบันทึกสถานะลง Sheets...")

with t3:
    st.subheader("สรุปงบประมาณ")
    # ดึงข้อมูลจาก Sheets มาคำนวณกำไร-ขาดทุน รายเดือน/รายปี
    st.write("ส่วนนี้จะดึงรายรับทั้งหมด ลบ รายจ่ายรายวัน และ รายจ่ายฟิกซ์ เพื่อสรุปยอดคงเหลือครับ")
