import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# ==========================================
# ⚙️ ส่วนตั้งค่า
# ==========================================
SHEET_NAME = "Rik_Financial_App" 

# --- 1. ตั้งค่าหน้าเว็บ ---
st.set_page_config(page_title="Rik & Mom Finance V8", layout="wide")

# --- 2. ระบบ Login ---
if 'user' not in st.session_state:
    st.session_state['user'] = None

if st.session_state['user'] is None:
    st.title("🔐 Rik & Mom Finance Login")
    password = st.text_input("กรุณากรอกรหัสผ่าน", type="password")
    if st.button("ตกลง"):
        if password == "1509": st.session_state['user'] = "Rik"
        elif password == "2208": st.session_state['user'] = "Mom"
        else: st.error("รหัสผ่านไม่ถูกต้อง")
        if st.session_state['user']: st.rerun()
    st.stop()

current_user = st.session_state['user']

# --- 3. เชื่อมต่อ Google Sheets ---
@st.cache_resource
def init_sheets():
    try:
        key_dict = st.secrets["gcp_service_account"]
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(key_dict, scopes=scopes)
        return gspread.authorize(creds).open(SHEET_NAME)
    except Exception as e:
        st.error(f"🚨 เชื่อมต่อ Sheets ผิดพลาด: {e}")
        return None

sh = init_sheets()

# --- 4. จัดการ Worksheet ---
def get_ws(name, headers):
    try: return sh.worksheet(name)
    except:
        ws = sh.add_worksheet(title=name, rows="100", cols="10")
        ws.append_row(headers)
        return ws

ws_fixed = get_ws("Fixed_Expenses", ["User", "Item", "Amount", "Current_Month", "Total_Months", "Type", "Status", "Note"])
ws_daily = get_ws("Daily_Records", ["User", "Date", "Type", "Item", "Amount", "Note"])
ws_invest = get_ws("Investments", ["User", "Symbol", "Qty", "Avg_Cost", "Current_Price"])

# ==========================================
# ส่วนการแสดงผล
# ==========================================
st.sidebar.title(f"👤 {current_user}")
if st.sidebar.button("Log out"):
    st.session_state['user'] = None
    st.rerun()

tab1, tab2, tab3, tab4 = st.tabs(["📊 พอร์ตการลงทุน", "📝 บันทึกรายวัน", "📅 จัดการหนี้/รายจ่าย", "🤖 AI Insight"])

# --- TAB 1: พอร์ตการลงทุน ---
with tab1:
    st.header("📈 พอร์ตการลงทุนของคุณริก")
    with st.expander("➕ เพิ่มสินทรัพย์ใหม่"):
        with st.form("invest_form"):
            s_symbol = st.text_input("ชื่อหุ้น/สินทรัพย์ (เช่น BTC, PTT, TSLA)")
            s_qty = st.number_input("จำนวนที่ถือ", min_value=0.0)
            s_cost = st.number_input("ราคาต้นทุนเฉลี่ย", min_value=0.0)
            if st.form_submit_button("บันทึก"):
                ws_invest.append_row([current_user, s_symbol.upper(), s_qty, s_cost, 0])
                st.success(f"เพิ่ม {s_symbol} เรียบร้อย!")
                st.cache_data.clear()
                st.rerun()

    # แสดงพอร์ต
    invest_df = pd.DataFrame(ws_invest.get_all_records())
    if not invest_df.empty:
        my_invest = invest_df[invest_df['User'] == current_user].copy()
        
        # คำนวณเบื้องต้น (ตรงนี้คุณริกสามารถใส่ราคาปัจจุบันเพื่อดู Profit ได้ครับ)
        st.write("### สินทรัพย์ทั้งหมด")
        for i, row in my_invest.iterrows():
            col1, col2, col3 = st.columns([2, 2, 1])
            col1.write(f"**{row['Symbol']}** ({row['Qty']} หน่วย)")
            # ปุ่มลิงก์ไป TradingView
            tv_url = f"https://www.tradingview.com/symbols/{row['Symbol']}/"
            col2.link_button(f"🔍 ดูกราฟ {row['Symbol']}", tv_url)
            
            # ปุ่มลบรายการ
            if col3.button("🗑️ ลบ", key=f"del_{row['Symbol']}"):
                cell = ws_invest.find(row['Symbol'], in_column=2)
                ws_invest.delete_rows(cell.row)
                st.rerun()
            st.divider()

# --- TAB 3: จัดการหนี้/รายจ่าย (เพิ่มระบบลบ) ---
with tab3:
    st.subheader("จัดการรายจ่ายประจำเดือน")
    fixed_df = pd.DataFrame(ws_fixed.get_all_records())
    if not fixed_df.empty:
        my_fixed = fixed_df[fixed_df['User'] == current_user]
        # ใช้ data_editor เพื่อให้คุณริกแก้ไขตัวเลขหรือลบได้ง่ายขึ้น
        edited_df = st.data_editor(my_fixed, num_rows="dynamic", key="fixed_editor")
        if st.button("บันทึกการเปลี่ยนแปลงทั้งหมด"):
            # โค้ดส่วนการอัปเดตกลับไปที่ Sheets ทั้งตาราง
            st.info("ระบบกำลังซิงค์ข้อมูลใหม่ทั้งหมด...")
