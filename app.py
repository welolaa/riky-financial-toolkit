import streamlit as st
import pandas as pd

# ตั้งค่าหน้าเพจ
st.set_page_config(page_title="Rik's Financial Toolkit", layout="centered")

st.title("🚀 Rik's Debt Simulator")
st.markdown("ระบบจำลองการปลดหนี้ฉบับ Ultimate Combo")

# เมนูด้านข้างสำหรับปรับตัวเลข
st.sidebar.header("⚙️ ปรับแต่งแผนการเงิน")
loan_amount = st.sidebar.number_input("ยอดหนี้ตั้งต้น (บาท)", value=1322000, step=10000)
interest_rate = st.sidebar.number_input("ดอกเบี้ยเฉลี่ย (% ต่อปี)", value=3.5, step=0.1) / 100
initial_pay = st.sidebar.number_input("ยอดผ่อนปีแรก (บาท/เดือน)", value=10000, step=500)
step_up = st.sidebar.number_input("ยอดผ่อนเพิ่มขึ้น (บาท/ปี)", value=1000, step=500)
bonus_pay = st.sidebar.number_input("โปะโบนัสปลายปี (บาท)", value=10000, step=1000)

# ตัวแปรสำหรับคำนวณ
balance = loan_amount
months = 0
total_interest = 0
current_pay = initial_pay
history = []

# ลูปคำนวณลดต้นลดดอกแบบรายเดือน
while balance > 0 and months < 360: # ป้องกันลูปเกิน 30 ปี
    months += 1
    
    # ปรับยอดผ่อนสเต็ปอัปทุกๆ การขึ้นปีใหม่ (เดือนที่ 13, 25, 37...)
    if months > 1 and (months - 1) % 12 == 0:
        current_pay += step_up
        
    # คำนวณดอกเบี้ยรายเดือน
    interest_month = balance * (interest_rate / 12)
    total_interest += interest_month
    
    # คำนวณเงินต้นที่ลดลง
    principal_paid = current_pay - interest_month
    
    # โปะโบนัสเพิ่มทุกๆ สิ้นปี (เดือนที่ 12, 24, 36...)
    if months % 12 == 0:
        principal_paid += bonus_pay
        
    # หักลบเงินต้นคงเหลือ
    balance -= principal_paid
    
    if balance < 0:
        balance = 0
        
    # บันทึกข้อมูลเพื่อพล็อตกราฟ
    history.append({
        "Month": months,
        "Balance": balance,
        "Monthly_Pay": current_pay
    })

# สรุปผลลัพธ์
years_to_payoff = months / 12
st.subheader("🎯 สรุปผลลัพธ์แผนนี้")
col1, col2 = st.columns(2)
col1.metric("ใช้เวลาผ่อนจบ", f"{years_to_payoff:.1f} ปี", f"{months} เดือน")
col2.metric("เสียดอกเบี้ยรวมให้แบงก์", f"{total_interest:,.0f} บาท")

# สร้าง DataFrame และพล็อตกราฟเงินต้นคงเหลือ
df = pd.DataFrame(history)
st.subheader("📉 กราฟจำลองยอดหนี้คงเหลือ")
st.line_chart(df.set_index("Month")["Balance"])

st.markdown("---")
st.caption("พัฒนาด้วย Python & Streamlit")