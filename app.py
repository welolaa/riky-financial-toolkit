import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from googleapiclient.errors import HttpError
import io

# ==========================================
# ⚙️ ส่วนตั้งค่า (คุณริกแก้ 2 จุดนี้ให้ตรงครับ)
# ==========================================
SHEET_NAME = "Rik_Financial_App" 
DRIVE_FOLDER_ID = "1z6AK_cQKN5P1Ue9-BNR_2eUXa_teNX5j" # ก๊อปปี้จาก URL โฟลเดอร์ใน Drive

# --- 1. ตั้งค่าหน้าเว็บ ---
st.set_page_config(page_title="Rik & Mom Finance", layout="wide")

# --- 2. ระบบ Login ---
if 'user' not in st.session_state:
    st.session_state['user'] = None

if st.session_state['user'] is None:
    st.title("🔐 เข้าสู่ระบบ")
    password = st.text_input("กรุณากรอกรหัสผ่าน", type="password")
    if st.button("ตกลง"):
        if password == "1509": st.session_state['user'] = "Rik"
        elif password == "2208": st.session_state['user'] = "Mom"
        else: st.error("รหัสผ่านไม่ถูกต้อง")
        if st.session_state['user']: st.rerun()
    st.stop()

current_user = st.session_state['user']
st.sidebar.title(f"👤 ผู้ใช้: {current_user}")
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
        sh = sheet_client.open(SHEET_NAME) 
        return sh, drive_service
    except Exception as e:
        st.error(f"🚨 การเชื่อมต่อ Google ผิดพลาด: {e}")
        return None, None

sh, drive_service = init_services()

# --- 4. จัดการ Worksheet ---
def get_ws(name, headers):
    try: return sh.worksheet(name)
    except:
        ws = sh.add_worksheet(title=name, rows="100", cols="10")
        ws.append_row(headers)
        return ws

ws_fixed = get_ws("Fixed_Expenses", ["User", "Item", "Amount", "Current_Month", "Total_Months", "Type", "Status", "Slip_Link", "Note"])
ws_daily = get_ws("Daily_Records", ["User", "Date", "Type", "Item", "Amount", "Slip_Link", "Note"])

# ==========================================
# ส่วนการแสดงผลหลัก
# ==========================================
st.title(f"💰 Rik & Mom Financial System")

tab1, tab2, tab3 = st.tabs(["📝 บันทึกรายวัน", "⚙️ ตั้งค่ารายจ่ายประจำ", "📅 ติ๊กจ่าย & ตรวจสอบ"])

# --- TAB 1: บันทึกรายวัน ---
with tab1:
    st.subheader("บันทึกรายรับ-รายจ่ายทั่วไป")
    with st.form("daily_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            d_date = st.date_input("วันที่", datetime.today())
            d_type = st.selectbox("ประเภท", ["รายรับ", "รายจ่ายทั่วไป"])
            d_item = st.text_input("ชื่อรายการ")
        with col2:
            d_amt = st.number_input("จำนวนเงิน (บาท)", min_value=0.0)
            d_file = st.file_uploader("แนบสลิป (ถ้ามี)", type=['png', 'jpg', 'jpeg'])
        d_note = st.text_input("บันทึกเพิ่มเติม")
        
        if st.form_submit_button("บันทึกลงระบบ"):
            slip_url = ""
            if d_file:
                try:
                    file_name = f"{d_date}_{d_item}.png"
                    media = MediaIoBaseUpload(io.BytesIO(d_file.read()), mimetype=d_file.type)
                    file = drive_service.files().create(body={'name': file_name, 'parents': [DRIVE_FOLDER_ID]}, media_body=media, fields='webViewLink').execute()
                    slip_url = file.get('webViewLink')
                except Exception as e:
                    st.error(f"🚨 อัปโหลดสลิปไม่สำเร็จ: {e}")
            
            ws_daily.append_row([current_user, str(d_date), d_type, d_item, d_amt, slip_url, d_note])
            st.success("บันทึกเรียบร้อย!")

# --- TAB 2: ตั้งค่ารายจ่ายประจำ ---
with tab2:
    st.subheader("เพิ่มรายการรายจ่ายประจำเดือน / หนี้")
    with st.form("fixed_form", clear_on_submit=True):
        f_item = st.text_input("ชื่อรายการ (เช่น ค่าบ้าน, ค่าเน็ต)")
        f_amt = st.number_input("ยอดจ่ายต่อเดือน", min_value=0.0)
        f_type = st.radio("ประเภท", ["รายจ่ายประจำ", "หนี้สิน (มีงวดผ่อน)"])
        f_total = st.number_input("จำนวนงวดทั้งหมด (ถ้ามี)", min_value=0, value=0)
        
        if st.form_submit_button("เพิ่มรายการ"):
            ws_fixed.append_row([current_user, f_item, f_amt, 0, f_total, f_type, "ยังไม่จ่าย", "", ""])
            st.success("เพิ่มรายการสำเร็จ!")
            st.cache_data.clear()

# --- TAB 3: ติ๊กจ่ายเงิน ---
with tab3:
    st.subheader("รายการที่ต้องจัดการเดือนนี้")
    fixed_data = pd.DataFrame(ws_fixed.get_all_records())
    
    if not fixed_data.empty:
        my_fixed = fixed_data[fixed_data['User'] == current_user]
        st.dataframe(my_fixed[['Item', 'Amount', 'Current_Month', 'Total_Months', 'Status']])
        
        st.divider()
        unpaid = my_fixed[my_fixed['Status'] != 'จ่ายแล้ว']['Item'].tolist()
        
        if unpaid:
            pay_item = st.selectbox("เลือกรายการที่จะจ่าย", unpaid)
            pay_file = st.file_uploader(f"แนบสลิปสำหรับ {pay_item} (ข้ามได้)", type=['png', 'jpg', 'jpeg'])
            
            if st.button(f"✅ ยืนยันการจ่าย {pay_item}"):
                with st.spinner("กำลังอัปเดตระบบ..."):
                    slip_url = ""
                    # 1. จัดการไฟล์ใน Drive (ถ้ามี)
                    if pay_file:
                        try:
                            t_str = datetime.today().strftime('%Y-%m-%d')
                            f_name = f"{t_str}_{pay_item}.png"
                            media = MediaIoBaseUpload(io.BytesIO(pay_file.read()), mimetype=pay_file.type)
                            up_file = drive_service.files().create(body={'name': f_name, 'parents': [DRIVE_FOLDER_ID]}, media_body=media, fields='webViewLink').execute()
                            slip_url = up_file.get('webViewLink')
                        except HttpError as he:
                            st.error(f"🚨 Google Drive Error: {he.content.decode('utf-8')}")
                            st.stop()
                    
                    # 2. อัปเดต Google Sheets
                    try:
                        cell = ws_fixed.find(pay_item, in_column=2)
                        if cell:
                            r = cell.row
                            curr = int(ws_fixed.cell(r, 4).value or 0)
                            tot = int(ws_fixed.cell(r, 5).value or 0)
                            
                            new_curr = curr + 1
                            ws_fixed.update_cell(r, 4, new_curr) # อัปเดตงวด
                            ws_fixed.update_cell(r, 7, "จ่ายแล้ว") # อัปเดตสถานะ
                            if slip_url: ws_fixed.update_cell(r, 8, slip_url) # บันทึกลิงก์
                            
                            st.success(f"บันทึกการจ่าย '{pay_item}' งวดที่ {new_curr} สำเร็จ!")
                            if tot > 0 and new_curr >= tot:
                                st.balloons()
                                st.success("🎉 ปิดยอดหนี้รายการนี้เรียบร้อย!")
                            
                            st.cache_data.clear()
                            st.rerun()
                    except Exception as ex:
                        st.error(f"🚨 อัปเดต Sheets ผิดพลาด: {ex}")
        else:
            st.success("จ่ายครบหมดแล้วสำหรับเดือนนี้! ✨")
