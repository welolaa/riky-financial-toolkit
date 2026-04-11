import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# --- 1. ตั้งค่าหน้าเว็บหลัก ---
st.set_page_config(page_title="Rik's Finance App", layout="wide", page_icon="💡")

# --- 2. ระบบหลังบ้าน: ฟังก์ชันเชื่อมต่อ Google Sheets ---
@st.cache_resource # ให้ระบบจำการเชื่อมต่อไว้ จะได้ไม่หน่วงเวลาเปลี่ยนหน้า
def init_connection():
    try:
        # ดึงกุญแจลับจาก Streamlit Secrets
        key_dict = st.secrets["gcp_service_account"]
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        creds = Credentials.from_service_account_info(key_dict, scopes=scopes)
        client = gspread.authorize(creds)
        
        # ⚠️ สำคัญ: เปลี่ยนชื่อ "Rik_Financial_App" ให้ตรงกับชื่อไฟล์ Google Sheets ของคุณริก
        sheet = client.open("Rik_Financial_App") 
        return sheet
    except Exception as e:
        st.error(f"❌ เชื่อมต่อ Google Sheets ไม่สำเร็จ กรุณาเช็กชื่อไฟล์หรือการตั้งค่า Secrets: {e}")
        return None

sheet = init_connection()

# --- ฟังก์ชันช่วยสร้าง Worksheet อัตโนมัติถ้ายังไม่มี ---
def get_worksheet(sheet_name, headers):
    if sheet:
        try:
            ws = sheet.worksheet(sheet_name)
        except gspread.exceptions.WorksheetNotFound:
            # ถ้าหาไม่เจอ ให้สร้างชีตใหม่และพิมพ์หัวตารางให้เลย
            ws = sheet.add_worksheet(title=sheet_name, rows="100", cols="20")
            ws.append_row(headers)
        return ws
    return None

# --- 3. สร้างระบบแถบเมนู (Tabs) ---
tab1, tab2, tab3, tab4 = st.tabs([
    "💸 บันทึกรายจ่าย (วิก/เดือน)", 
    "🏢 วางแผนปลดหนี้", 
    "🚗 Grab & LPG", 
    "🖨️ ต้นทุน Maker"
])

# ==========================================
# TAB 1: บันทึกรายจ่าย (แบ่งวิก 15 วัน / รายเดือน)
# ==========================================
with tab1:
    st.header("💸 บันทึกและสรุปรายจ่าย")
    
    # เชื่อมต่อกับชีตชื่อ Expenses
    ws_expenses = get_worksheet("Expenses", ["Date", "Item", "Amount", "Category", "Period"])
    
    with st.expander("📝 ฟอร์มบันทึกรายจ่ายใหม่", expanded=True):
        with st.form("expense_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                e_date = st.date_input("วันที่", datetime.today())
                e_item = st.text_input("รายการ (เช่น ค่าอาหาร, ค่าบ้าน, ค่าเน็ต)")
                e_amount = st.number_input("จำนวนเงิน (บาท)", min_value=0.0, step=50.0)
            with col2:
                e_category = st.selectbox("หมวดหมู่", ["อาหาร", "เดินทาง", "ที่อยู่อาศัย/หนี้", "จิปาถะ", "ธุรกิจส่วนตัว"])
                
                # ตรรกะช่วยเลือกวิกอัตโนมัติตามวันที่ (วันที่ 1-15 คือวิก 1)
                day = e_date.day
                default_period = "วิก 1 (วันที่ 1-15)" if day <= 15 else "วิก 2 (วันที่ 16-31)"
                e_period = st.selectbox(
                    "รอบบิลรายจ่าย", 
                    ["วิก 1 (วันที่ 1-15)", "วิก 2 (วันที่ 16-31)", "รายจ่ายคงที่ (รายเดือน)"], 
                    index=0 if day <= 15 else 1
                )
            
            submit_expense = st.form_submit_button("💾 บันทึกลงฐานข้อมูล")
            
            if submit_expense:
                if ws_expenses and e_item:
                    ws_expenses.append_row([str(e_date), e_item, e_amount, e_category, e_period])
                    st.success(f"บันทึก '{e_item}' จำนวน {e_amount} บาท ลงระบบเรียบร้อย!")
                else:
                    st.warning("กรุณากรอกชื่อรายการ หรือตรวจสอบการเชื่อมต่อ")

    st.markdown("---")
    st.subheader("📊 สรุปกระแสเงินสด (Coming Soon)")
    st.info("เมื่อข้อมูลใน Google Sheets เริ่มเยอะขึ้น เราจะดึงข้อมูลมาทำกราฟสรุปแยกวิก 1 / วิก 2 ให้เห็นกระแสเงินสดชัดๆ ในอัปเดตเวอร์ชันหน้านะครับ!")

# ==========================================
# TAB 2: วางแผนปลดหนี้ (Ultimate Combo)
# ==========================================
with tab2:
    st.header("🏢 เครื่องจำลองการปลดหนี้")
    st.markdown("ระบบจำลองลดต้นลดดอก เมื่อใช้กลยุทธ์ **Step-up (เพิ่มยอดรายปี)** และ **โปะโบนัสสิ้นปี**")
    
    col_d1, col_d2 = st.columns(2)
    with col_d1:
        loan_amt = st.number_input("ยอดหนี้ตั้งต้น (บาท)", value=1322000, step=10000)
        interest_rate = st.number_input("ดอกเบี้ยเฉลี่ย (% ต่อปี)", value=3.5, step=0.1) / 100
    with col_d2:
        base_pay = st.number_input("ยอดผ่อนฐานปีแรก (บาท/เดือน)", value=10000, step=1000)
        step_up = st.number_input("เพิ่มยอดผ่อนทุกๆ ปี (บาท/ปี)", value=2000, step=1000)
        bonus_pay = st.number_input("โปะโบนัสปลายปี (บาท)", value=50000, step=5000)
        
    if st.button("🚀 คำนวณความเร็วปลดหนี้"):
        bal = loan_amt
        months = 0
        total_int = 0
        current_pay = base_pay
        
        while bal > 0 and months < 360: # ป้องกันลูปค้าง (30 ปี)
            months += 1
            
            # ขึ้นปีใหม่ (ทุกๆ 12 เดือน) อัดยอดผ่อนเพิ่ม
            if months > 1 and (months - 1) % 12 == 0:
                current_pay += step_up 
                
            int_m = bal * (interest_rate / 12)
            total_int += int_m
            principal_paid = current_pay - int_m
            
            # สิ้นปี อัดโบนัสโปะ
            if months % 12 == 0:
                principal_paid += bonus_pay 
                
            bal -= principal_paid
            
        st.success(f"🎉 โหดมาก! คุณจะปลดหนี้ก้อนนี้หมดเกลี้ยงในเวลาแค่ **{months/12:.1f} ปี** (หรือ {months} เดือน)")
        st.write(f"💸 เสียดอกเบี้ยรวมให้ธนาคารแค่: **{total_int:,.0f} บาท**")

# ==========================================
# TAB 3: Grab & LPG Tracker
# ==========================================
with tab3:
    st.header("🚗 บันทึกกำไรวิ่งรอบ & คุมต้นทุนแก๊ส LPG")
    
    # เชื่อมต่อกับชีตชื่อ Grab_LPG
    ws_grab = get_worksheet("Grab_LPG", ["Date", "Revenue", "Distance", "LPG_Cost", "Net_Profit", "Cost_Per_Km"])
    
    with st.form("grab_form", clear_on_submit=True):
        g_date = st.date_input("วันที่วิ่งงาน", datetime.today())
        col_g1, col_g2 = st.columns(2)
        with col_g1:
            g_revenue = st.number_input("รายได้ Grab วันนี้ (บาท)", min_value=0.0, value=1500.0)
            g_distance = st.number_input("ระยะทางที่ขับรวม (กม.)", min_value=1.0, value=150.0)
        with col_g2:
            lpg_price = st.number_input("ราคาแก๊ส LPG ปั๊ม PT (บาท/ลิตร)", value=15.5)
            lpg_km_l = st.number_input("อัตรากินแก๊สของรถ (กม./ลิตร)", value=13.0)
            
        g_submit = st.form_submit_button("คำนวณกำไร & บันทึก")
        
        if g_submit:
            lpg_cost = (g_distance / lpg_km_l) * lpg_price
            net_profit = g_revenue - lpg_cost
            cost_per_km = lpg_cost / g_distance
            
            st.success(f"💰 กำไรสุทธิเข้ากระเป๋าวันนี้: **{net_profit:,.0f} บาท**")
            
            # เช็กสุขภาพรถ
            if cost_per_km > 1.5:
                st.error(f"⚠️ ต้นทุนแก๊ส: {cost_per_km:.2f} บาท/กม. (เริ่มกินแก๊สผิดปกติ ควรเช็กระบบ)")
            else:
                st.info(f"✅ ต้นทุนแก๊สปกติ: **{cost_per_km:.2f} บาท/กม.**")
            
            if ws_grab:
                ws_grab.append_row([str(g_date), g_revenue, g_distance, lpg_cost, net_profit, cost_per_km])

# ==========================================
# TAB 4: ต้นทุนธุรกิจ Maker 
# ==========================================
with tab4:
    st.header("🖨️ คำนวณราคาขายงานผลิต (3D Print / Laser)")
    
    m_col1, m_col2 = st.columns(2)
    with m_col1:
        weight = st.number_input("น้ำหนักพลาสติกที่ใช้ (กรัม)", value=150.0)
        filament_price = st.number_input("ราคาพลาสติกม้วนละ (บาท/กก.)", value=500.0)
    with m_col2:
        print_time = st.number_input("เวลาที่เครื่องทำงาน (ชม.)", value=8.0)
        elec_hour = st.number_input("ค่าไฟ+ค่าสึกหรอเครื่อง (บาท/ชม.)", value=15.0)
    
    material_cost = (weight / 1000) * filament_price
    total_cost = material_cost + (print_time * elec_hour)
    
    st.write(f"🧾 **ต้นทุนที่แท้จริง:** {total_cost:,.0f} บาท")
    profit_margin = st.slider("มาร์จิ้นกำไรที่ต้องการ (%)", 0, 300, 100)
    
    final_price = total_cost * (1 + profit_margin/100)
    st.success(f"💵 **ราคาประเมินให้ลูกค้า:** {final_price:,.0f} บาท")
