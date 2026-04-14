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
        if password == "1509": st.session_state['user'] = "Rik"
        elif password == "2208": st.session_state['user'] = "Mom"
        else: st.error("รหัสผ่านไม่ถูกต้อง")
        if st.session_state['user']: st.rerun()
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
        sh = sheet_client.open("Rik_Financial_App") 
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

ws_fixed = get_ws("Fixed_Expenses", ["User", "Item", "Amount", "Current_Month", "Total_Months", "Type", "Status", "Note"])
ws_daily = get_ws("Daily_Records", ["User", "Date", "Type", "Item", "Amount", "Slip_Link", "Note"])

# ==========================================
# ส่วนการแสดงผล
# ==========================================
st.title(f"💰 Rik & Mom Financial System")

tab1, tab2, tab3 = st.tabs(["📝 บันทึกรายวัน/รายรับ", "⚙️ ตั้งค่ารายจ่ายประจำ/หนี้", "📅 ติ๊กจ่าย & ตรวจสอบสลิป"])

with tab1:
    st.subheader("บันทึกรายรับ-รายจ่ายทั่วไป")
    with st.form("daily_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            d_date = st.date_input("วันที่", datetime.today())
            d_type = st.selectbox("ประเภท", ["รายรับ", "รายจ่ายทั่วไป"])
            d_item = st.text_input("ชื่อรายการ (เช่น เติมแก๊ส, ซื้อของ)")
        with col2:
            d_amt = st.number_input("จำนวนเงิน (บาท)", min_value=0.0)
            d_file = st.file_uploader("แนบสลิป (ถ้ามี)", type=['png', 'jpg', 'jpeg'])
        
        d_note = st.text_input("บันทึกเพิ่มเติม")
        if st.form_submit_button("บันทึกลงระบบ"):
            slip_url = ""
            if d_file:
                main_id = get_or_create_folder("Rik_Finance_Receipts")
                sub_id = get_or_create_folder(d_item, parent_id=main_id)
                media = MediaIoBaseUpload(io.BytesIO(d_file.read()), mimetype='image/png')
                file = drive_service.files().create(body={'name': f"{d_date}_{d_item}.png", 'parents': [sub_id]}, media_body=media, fields='webViewLink').execute()
                slip_url = file.get('webViewLink')
            ws_daily.append_row([current_user, str(d_date), d_type, d_item, d_amt, slip_url, d_note])
            st.success("บันทึกเรียบร้อย!")

with tab2:
    st.subheader("เพิ่มรายการรายจ่ายประจำเดือน หรือ หนี้ระยะยาว")
    with st.form("fixed_setting_form", clear_on_submit=True):
        f_item = st.text_input("ชื่อรายการ (เช่น ค่าบ้าน, ค่ารถ, ค่าเน็ต)")
        f_amt = st.number_input("ยอดที่ต้องจ่ายต่อเดือน", min_value=0.0)
        f_type = st.radio("ประเภทรายการ", ["รายจ่ายประจำ (จ่ายตลอด)", "หนี้สิน (มีงวดผ่อน)"])
        f_total = 0
        if f_type == "หนี้สิน (มีงวดผ่อน)":
            f_total = st.number_input("จำนวนงวดทั้งหมด", min_value=1, value=12)
        
        if st.form_submit_button("บันทึกรายการประจำ"):
            ws_fixed.append_row([current_user, f_item, f_amt, 0, f_total, f_type, "ยังไม่จ่าย", ""])
            st.success(f"เพิ่มรายการ '{f_item}' เข้าสู่ระบบแล้ว")

with tab3:
    st.subheader("รายการที่ต้องจ่าย/ตรวจสอบเดือนนี้")
    
    # ดึงข้อมูลมาแสดงตารางติ๊กจ่าย
    fixed_data = pd.DataFrame(ws_fixed.get_all_records())
    if not fixed_data.empty:
        my_fixed = fixed_data[fixed_data['User'] == current_user]
        st.write("### ตารางรายจ่ายประจำเดือนของคุณ")
        st.dataframe(my_fixed[['Item', 'Amount', 'Current_Month', 'Total_Months', 'Type', 'Status']])
        
        st.divider()
        st.subheader("ยืนยันการจ่ายเงิน")
        unpaid_list = my_fixed[my_fixed['Status'] != 'จ่ายแล้ว']['Item'].tolist()
        
        if unpaid_list:
            # 1. เลือกรายการ
            pay_item = st.selectbox("เลือกรายการที่จะแจ้งจ่าย", unpaid_list)
            # 2. ช่องอัปโหลดสลิป (ไม่บังคับ)
            st.caption("อัปโหลดสลิป (ไม่บังคับ - ข้ามได้ถ้าจ่ายด้วยเงินสดหรือไม่ได้เซฟสลิปไว้)")
            pay_file = st.file_uploader(f"แนบสลิปสำหรับ {pay_item}", type=['png', 'jpg', 'jpeg'])
            
            # 3. ปุ่มกดจ่าย
            if st.button(f"✅ ยืนยันว่าจ่าย '{pay_item}' แล้ว"):
                with st.spinner("กำลังบันทึกข้อมูล..."):
                    # ----- ส่วนอัปโหลดสลิป (ถ้ามี) -----
                    slip_url = ""
                    if pay_file:
                        main_id = get_or_create_folder("Rik_Finance_Receipts")
                        # ตั้งชื่อไฟล์ให้ตรงกับหนี้ เพื่อง่ายต่อการค้นหา
                        today_str = datetime.today().strftime('%Y-%m-%d')
                        file_name = f"{today_str}_{pay_item}.png"
                        
                        media = MediaIoBaseUpload(io.BytesIO(pay_file.read()), mimetype='image/png')
                        file = drive_service.files().create(
                            body={'name': file_name, 'parents': [main_id]}, 
                            media_body=media, 
                            fields='webViewLink'
                        ).execute()
                        slip_url = file.get('webViewLink')

                    # ----- ส่วนอัปเดต Google Sheets -----
                    # หาบรรทัด (Row) ของรายการนี้ เพื่อไปอัปเดต
                    cell = ws_fixed.find(pay_item, in_column=2) # ค้นหาในคอลัมน์ Item (คอลัมน์ที่ 2)
                    if cell:
                        row_index = cell.row
                        
                        # ดึงค่าเก่ามาเพื่อคำนวณงวด
                        current_month = int(ws_fixed.cell(row_index, 4).value or 0)
                        total_months = int(ws_fixed.cell(row_index, 5).value or 0)
                        item_type = ws_fixed.cell(row_index, 6).value
                        
                        # บวกงวดเพิ่ม 1
                        new_current_month = current_month + 1
                        
                        # อัปเดตสถานะและงวด
                        ws_fixed.update_cell(row_index, 4, new_current_month)
                        ws_fixed.update_cell(row_index, 7, "จ่ายแล้ว")
                        
                        # ถ้ามีสลิป ก็อัปเดตลิงก์ลงไปด้วย (อยู่คอลัมน์ที่ 8 - ต้องเพิ่มหัวคอลัมน์ Slip_Link ไว้ด้วยนะ)
                        if slip_url:
                            ws_fixed.update_cell(row_index, 8, slip_url)

                        # เช็กเงื่อนไขปิดยอด
                        if item_type == "หนี้สิน (มีงวดผ่อน)" and new_current_month >= total_months:
                            st.balloons() # ฉลองปิดยอด!
                            st.success(f"🎉 ยินดีด้วย! คุณผ่อน '{pay_item}' ครบทุกงวดแล้ว!")
                        else:
                            st.success(f"บันทึกการจ่าย '{pay_item}' งวดที่ {new_current_month} เรียบร้อย!")
                        
                        st.rerun() # รีเฟรชหน้าเพื่ออัปเดตตาราง
                    else:
                        st.error("ไม่พบรายการนี้ในระบบ")
        else:
            st.success("คุณจ่ายครบทุกรายการของเดือนนี้แล้ว! ")

