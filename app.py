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
st.sidebar.title(f"👤 {current_user}")
if st.sidebar.button("Log out"):
    st.session_state['user'] = None
    st.rerun()

# --- 3. เชื่อมต่อ Google Services ---
@st.cache_resource
def init_services():
    try:
        key_dict = st.secrets["gcp_service_account"]
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(key_dict, scopes=scopes)
        sheet_client = gspread.authorize(creds)
        drive_service = build('drive', 'v3', credentials=creds)
        sh = sheet_client.open("Rik_Financial_App") # แก้ให้ตรงกับชื่อไฟล์จริง
        return sh, drive_service
    except Exception as e:
        st.error(f"การเชื่อมต่อผิดพลาด: {e}")
        return None, None

sh, drive_service = init_services()

# --- 4. ฟังก์ชันจัดการโฟลเดอร์ Drive ---
def get_or_create_folder(folder_name, parent_id=None):
    query = f"name = '{folder_name}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
    if parent_id: query += f" and '{parent_id}' in parents"
    results = drive_service.files().list(q=query, fields="files(id)").execute()
    items = results.get('files', [])
    if not items:
        file_metadata = {'name': folder_name, 'mimeType': 'application/vnd.google-apps.folder', 'parents': [parent_id] if parent_id else []}
        folder = drive_service.files().create(body=file_metadata, fields='id').execute()
        return folder.get('id')
    return items[0].get('id')

# --- 5. จัดการ Worksheet ---
def get_ws(name, headers):
    try: return sh.worksheet(name)
    except:
        ws = sh.add_worksheet(title=name, rows="100", cols="10")
        ws.append_row(headers)
        return ws

ws_fixed = get_ws("Fixed_Expenses", ["User", "Item", "Amount", "Current", "Total", "Type", "Status", "Slip_Link"])
ws_daily = get_ws("Daily_Records", ["User", "Date", "Type", "Item", "Amount", "Slip_Link", "Note"])

# ==========================================
# ส่วนการแสดงผล
# ==========================================
st.header(f"💰 ระบบบันทึกรายจ่าย ({current_user})")

tab1, tab2 = st.tabs(["📝 บันทึกใหม่/จ่ายหนี้", "📅 ประวัติและตรวจสอบสลิป"])

with tab1:
    col_input, col_pay = st.columns(2)
    
    with col_input:
        st.subheader("บันทึกรายวัน/รายรับ")
        with st.form("daily_form", clear_on_submit=True):
            d_date = st.date_input("วันที่", datetime.today())
            d_type = st.selectbox("ประเภท", ["รายรับ", "รายจ่ายทั่วไป"])
            d_item = st.text_input("รายการ")
            d_amt = st.number_input("จำนวนเงิน", min_value=0.0)
            d_note = st.text_input("Note")
            d_file = st.file_uploader("แนบสลิป", type=['png', 'jpg', 'jpeg'])
            if st.form_submit_button("บันทึก"):
                slip_url = ""
                if d_file:
                    main_id = get_or_create_folder("Rik_Finance_Receipts")
                    sub_id = get_or_create_folder(d_item, parent_id=main_id)
                    media = MediaIoBaseUpload(io.BytesIO(d_file.read()), mimetype='image/png')
                    file = drive_service.files().create(body={'name': f"{d_date}_{d_item}.png", 'parents': [sub_id]}, media_body=media, fields='webViewLink').execute()
                    slip_url = file.get('webViewLink')
                ws_daily.append_row([current_user, str(d_date), d_type, d_item, d_amt, slip_url, d_note])
                st.success("บันทึกสำเร็จ!")

    with col_pay:
        st.subheader("ชำระรายจ่ายฟิกซ์/หนี้")
        df_fixed = pd.DataFrame(ws_fixed.get_all_records())
        if not df_fixed.empty:
            my_fixed = df_fixed[df_fixed['User'] == current_user]
            unpaid = my_fixed[my_fixed['Status'] != 'จ่ายแล้ว']
            if not unpaid.empty:
                selected_item = st.selectbox("เลือกรายการที่จะจ่าย", unpaid['Item'])
                p_file = st.file_uploader(f"อัปโหลดสลิปสำหรับ: {selected_item}", type=['png', 'jpg', 'jpeg'])
                if st.button("ยืนยันการจ่าย"):
                    # Logic: อัปเดตลิงก์สลิปและสถานะใน Sheets
                    st.info("ระบบกำลังอัปโหลดและอัปเดตสถานะ...")
            else:
                st.write("✅ จ่ายครบทุกรายการแล้ว!")

with tab2:
    st.subheader("ตรวจสอบข้อมูลรายเดือน")
    view_month = st.selectbox("เลือกเดือน", ["มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน", "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม"], index=datetime.today().month-1)
    
    records = pd.DataFrame(ws_daily.get_all_records())
    if not records.empty:
        # กรองข้อมูลตาม User
        user_records = records[records['User'] == current_user]
        
        # แสดงตารางพร้อมปุ่มดูสลิป
        for i, row in user_records.iterrows():
            with st.container():
                c1, c2, c3, c4 = st.columns([2, 2, 2, 1])
                c1.write(f"**{row['Date']}**")
                c2.write(row['Item'])
                c3.write(f"{row['Amount']:,.2f} บาท")
                if row['Slip_Link']:
                    c4.link_button("📄 ดูสลิป", row['Slip_Link'])
                else:
                    c4.write("➖")
                st.divider()
