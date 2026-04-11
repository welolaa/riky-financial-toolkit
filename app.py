import streamlit as st
import pandas as pd

st.set_page_config(page_title="Rik's Financial Command Center", layout="wide")

# สร้าง Tabs สำหรับฟังก์ชันต่างๆ
tab1, tab2, tab3 = st.tabs(["📊 ระบบจัดการหนี้", "🚗 คำนวณ Grab & LPG", "🛠️ ต้นทุนธุรกิจ Maker"])

# --- Tab 1: ระบบจัดการหนี้ (Multi-Debt Manager) ---
with tab1:
    st.header("🏢 ระบบจัดการหนี้รายตัว")
    st.info("ระบุชื่อหนี้ อัตราดอกเบี้ย และยอดผ่อนต่อเดือน เพื่อดูวันปลดหนี้")

    if 'debts' not in st.session_state:
        st.session_state.debts = [
            {"name": "บ้านออมสิน (รวมกู้เพิ่ม)", "balance": 1322000, "rate": 3.5, "pay": 10000}
        ]

    # ฟอร์มเพิ่มหนี้ใหม่
    with st.expander("➕ เพิ่มรายการหนี้ใหม่ (บัตร/แอป/ยืมคน)"):
        with st.form("add_debt_form"):
            new_name = st.text_input("ชื่อหนี้ (เช่น บัตรเครดิต A / หนี้เพื่อน)")
            new_bal = st.number_input("ยอดหนี้คงเหลือ (บาท)", min_value=0, value=10000)
            new_rate = st.number_input("ดอกเบี้ย (% ต่อปี)", min_value=0.0, value=15.0)
            new_pay = st.number_input("ยอดผ่อนต่อเดือน (บาท)", min_value=1, value=1000)
            if st.form_submit_button("บันทึกรายการหนี้"):
                st.session_state.debts.append({"name": new_name, "balance": new_bal, "rate": new_rate, "pay": new_pay})
                st.rerun()

    # แสดงรายการและคำนวณ
    if st.session_state.debts:
        total_interest_all = 0
        for i, debt in enumerate(st.session_state.debts):
            with st.container():
                st.subheader(f"🔹 {debt['name']}")
                
                # ตรรกะคำนวณรายตัว
                bal = debt['balance']
                rate = debt['rate'] / 100 / 12
                pay = debt['pay']
                m = 0
                
                while bal > 0 and m < 360:
                    m += 1
                    int_m = bal * rate
                    bal = bal + int_m - pay
                    if int_m >= pay: # กรณีผ่อนไม่พอดอกเบี้ย
                        st.error(f"⚠️ ยอดผ่อนของ {debt['name']} น้อยกว่าดอกเบี้ย! หนี้จะไม่มีวันหมด")
                        break
                
                col1, col2, col3 = st.columns(3)
                col1.metric("ยอดหนี้", f"{debt['balance']:,.0f} ฿")
                col2.metric("ดอกเบี้ย", f"{debt['rate']}%")
                col3.metric("เวลาที่ใช้จบหนี้", f"{m} เดือน" if bal <= 0 else "N/A")
                
                if st.button(f"🗑️ ลบรายการ {debt['name']}", key=f"del_{i}"):
                    st.session_state.debts.pop(i)
                    st.rerun()
                st.divider()

# --- Tab 2: Grab & LPG Tracker ---
with tab2:
    st.header("⛽ คำนวณกำไร Grab & ค่าแก๊ส")
    col_g1, col_g2 = st.columns(2)
    with col_g1:
        revenue = st.number_input("รายได้รวมวันนี้ (บาท)", min_value=0, value=1000)
        distance = st.number_input("ระยะทางที่วิ่งรวม (กม.)", min_value=1, value=150)
    with col_g2:
        lpg_price = st.number_input("ราคา LPG (บาท/ลิตร)", value=15.5)
        consumption = st.number_input("อัตรากินแก๊สรถ (กม./ลิตร)", value=13.0)
    
    gas_cost = (distance / consumption) * lpg_price
    net_profit = revenue - gas_cost
    
    st.subheader(f"💰 กำไรสุทธิวันนี้: {net_profit:,.2f} บาท")
    st.write(f"📊 ต้นทุนค่าแก๊สเฉลี่ย: {gas_cost/distance:.2f} บาท/กม.")

# --- Tab 3: ต้นทุนธุรกิจ Maker ---
with tab3:
    st.header("🖨️ คำนวณราคาขายงาน Maker")
    m_col1, m_col2 = st.columns(2)
    with m_col1:
        weight = st.number_input("น้ำหนักชิ้นงาน (กรัม)", value=100)
        filament_price = st.number_input("ราคาฟิลาเมนต์ (บาท/กก.)", value=500)
    with m_col2:
        print_time = st.number_input("เวลาที่ใช้พิมพ์ (ชม.)", value=5)
        elec_hour = st.number_input("ค่าไฟ+ค่าเสื่อมเครื่อง (บาท/ชม.)", value=10)
    
    material_cost = (weight / 1000) * filament_price
    total_cost = material_cost + (print_time * elec_hour)
    
    st.subheader(f"🧾 ต้นทุนรวม: {total_cost:,.2f} บาท")
    profit_margin = st.slider("กำไรที่ต้องการ (%)", 0, 300, 100)
    st.success(f"💵 ราคาขายแนะนำ: {total_cost * (1 + profit_margin/100):,.0f} บาท")
