from sqlalchemy import create_engine
import streamlit as st
import pandas as pd
import plotly.express as px
import os

engine = create_engine('sqlite:///loan_database.db')

def load_data():
    try:
        df = pd.read_sql("SELECT * FROM decision_log", con=engine)
        
        # Đảm bảo các cột mới tồn tại để tránh lỗi nếu DB cũ chưa cập nhật
        required_cols = ['Timestamp', 'Monthly Expenses', 'Employment Years', 'Employment Status']
        for col in required_cols:
            if col not in df.columns:
                df[col] = ""

        # Ép kiểu dữ liệu để tránh lỗi PyArrow
        if not df.empty:
            text_cols = ['Timestamp', 'Customer', 'National ID', 'Employment Status', 'Final Decision', 'Reject Reason']
            for col in text_cols:
                if col in df.columns:
                    df[col] = df[col].fillna("").astype(str)
        return df
    except:
        return pd.DataFrame()

st.set_page_config(page_title="Risk Alerts Dashboard", layout="wide")

# ==========================================
# CẤU HÌNH GIAO DIỆN
# ==========================================
st.markdown("""
    <style>
    .metric-card {
        background-color: #ffffff;
        border-radius: 10px;
        padding: 20px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        text-align: center;
        border: 2px solid #000000; /* THÊM VIỀN MÀU ĐEN */
    }
    .metric-title { color: #000000; font-size: 16px; margin-bottom: 5px; font-weight: bold; text-transform: uppercase; }
    .metric-value { color: #000000; font-size: 32px; font-weight: bold; }
    .sub-red { color: #ff4b4b; }
    .sub-yellow { color: #faca2b; }
    </style>
""", unsafe_allow_html=True)

st.title("Lending Risk Alerts Dashboard")

# ==========================================
# ADMIN PANEL
# ==========================================
with st.sidebar.expander("🛠️ Admin Panel", expanded=False):
    st.markdown("Khu vực dành riêng cho người thuyết trình.")
    admin_pass = st.text_input("Mật khẩu Admin:", type="password", key="clear_data_pass")
    if st.button("🗑️ Xóa toàn bộ dữ liệu", disabled=(admin_pass != "demo123")):
        try:
            if os.path.exists("loan_database.db"):
                os.remove("loan_database.db")
            st.success("Đã làm sạch toàn bộ dữ liệu hệ thống!")
            st.rerun()
        except Exception as e:
            st.error(f"Lỗi: {e}")

# ==========================================
# 1. ĐỌC DỮ LIỆU
# ==========================================
df = load_data()

if st.button("🔄 REFRESH DASHBOARD"):
    st.rerun()

if df.empty:
    st.warning("Chưa có dữ liệu log. Vui lòng chạy Decision Engine ở tab App.")
    st.stop()

# ==========================================
# 2. XỬ LÝ LOGIC ALERTS
# ==========================================
def determine_alert_and_severity(row):
    reason = str(row.get('Reject Reason', '')).lower()
    final_decision = str(row.get('Final Decision', '')) # Thêm dòng này để lấy kết quả cuối cùng
    
    try: dti_2 = float(row.get('DTI_2', 0)) if pd.notna(row.get('DTI_2')) else 0
    except: dti_2 = 0
    try: ml_prob = float(row.get('ML probability', 1.0)) if pd.notna(row.get('ML probability')) else 1.0
    except: ml_prob = 1.0
    try: credit_score = float(row.get('Credit Score', 999)) if pd.notna(row.get('Credit Score')) else 999
    except: credit_score = 999

    alert_type = "Normal"
    
    # Chỉ áp dụng các logic cảnh báo rủi ro nếu hồ sơ KHÔNG được Approve
    if "Approve" not in final_decision:
        if "blacklist" in reason or "dpd" in reason or (0 < credit_score < 500) or "low cic" in reason or "dti_1" in reason or ml_prob < 0.6 or dti_2 > 0.6:
            alert_type = "High Risk"
        elif 0.4 < dti_2 <= 0.6:
            alert_type = "Borderline"
        elif "age" in reason or "nationality" in reason or "income" in reason:
            alert_type = "Policy Issue"
            
    severity_map = {"High Risk": "Critical", "Borderline": "High", "Policy Issue": "Medium", "Normal": "Low"}
    return pd.Series([alert_type, severity_map[alert_type]])
    
df[['Alert Type', 'Severity']] = df.apply(determine_alert_and_severity, axis=1)

# KPI Calculations
total_apps = len(df)
total_alerts = len(df[df['Alert Type'] != 'Normal'])
pct_rejected = (len(df[df['Final Decision'] == 'Reject']) / total_apps * 100) if total_apps > 0 else 0
false_positive_df = df[(df['Model decision'] == 'Approve') & (df['Rule Decision'] == 'Reject')]
pct_false_positive = (len(false_positive_df) / total_apps * 100) if total_apps > 0 else 0

# Metric Cards
m1, m2, m3, m4 = st.columns(4)
m1.markdown(f'<div class="metric-card"><div class="metric-title">📑 TOTAL APPS</div><div class="metric-value">{total_apps}</div></div>', unsafe_allow_html=True)
m2.markdown(f'<div class="metric-card"><div class="metric-title">🔔 TOTAL ALERTS</div><div class="metric-value">{total_alerts}</div></div>', unsafe_allow_html=True)
m3.markdown(f'<div class="metric-card"><div class="metric-title">⚠️ % REJECTED</div><div class="metric-value"><span class="sub-red">{pct_rejected:.1f}%</span></div></div>', unsafe_allow_html=True)
m4.markdown(f'<div class="metric-card"><div class="metric-title">⚠️ % FALSE POSITIVES</div><div class="metric-value"><span class="sub-yellow">{pct_false_positive:.1f}%</span></div></div>', unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ==========================================
# 4. BẢNG DỮ LIỆU & BIỂU ĐỒ (ĐÃ ĐƯỢC BỐ TRÍ LẠI LAYOUT)
# ==========================================

# --- KHU VỰC 1: BẢNG RISK ALERTS (Trải dài toàn bộ màn hình để dễ theo dõi) ---
st.subheader("Risk Alerts Table")
f1, f2, f3 = st.columns(3)
filter_alert = f1.selectbox("Alert Type", ["All"] + list(df['Alert Type'].unique()))
filter_severity = f2.selectbox("Severity", ["All"] + list(df['Severity'].unique()))
filter_decision = f3.selectbox("Final Decision", ["All"] + list(df['Final Decision'].unique()))

filtered_df = df.copy()
if filter_alert != "All": filtered_df = filtered_df[filtered_df['Alert Type'] == filter_alert]
if filter_severity != "All": filtered_df = filtered_df[filtered_df['Severity'] == filter_severity]
if filter_decision != "All": filtered_df = filtered_df[filtered_df['Final Decision'] == filter_decision]

display_cols = [
    'Timestamp', 'National ID', 'Customer', 
    'Monthly Income', 'Monthly Expenses', 'Loan Amount', 
    'Employment Years', 'Employment Status', 
    'DTI_2', 'ML probability', 'Alert Type', 'Severity', 'Final Decision', 'Reject Reason'
]

def style_df(row):
    colors = [''] * len(row)
    if row['Alert Type'] == 'High Risk': bg = 'background-color: rgba(255, 75, 75, 0.1); color: #ff4b4b;'
    elif row['Alert Type'] == 'Borderline': bg = 'background-color: rgba(250, 202, 43, 0.1); color: #faca2b;'
    else: bg = ''
    try:
        colors[row.index.get_loc('Alert Type')] = bg
        colors[row.index.get_loc('Severity')] = bg
    except: pass
    return colors

st.dataframe(filtered_df[display_cols].style.apply(style_df, axis=1), use_container_width=True, hide_index=True)

st.markdown("<br>", unsafe_allow_html=True)

# --- KHU VỰC 2: PIE CHART VÀ FALSE POSITIVE ĐƯỢC ĐẨY XUỐNG DƯỚI ---
# Nới rộng cột trái một chút [4, 6] để có đủ không gian chứa 2 biểu đồ
col_bottom_left, col_bottom_right = st.columns([4, 6])

with col_bottom_left:
    # Chia làm 2 cột nhỏ cho 2 biểu đồ
    pie_col1, pie_col2 = st.columns(2)
    with pie_col1:
        st.subheader("Alert Types")
        fig1 = px.pie(df, names='Alert Type', hole=0.4, color='Alert Type',
                     color_discrete_map={'High Risk': '#ff4b4b', 'Borderline': '#faca2b', 'Policy Issue': '#00bfff', 'Normal': '#90ee90'})
        # Đổi font_color thành black cho hợp nền trắng, ẩn chú thích (legend) để biểu đồ to rõ hơn
        fig1.update_layout(showlegend=False, paper_bgcolor="rgba(0,0,0,0)", font_color="black", margin=dict(t=10, b=10, l=10, r=10))
        st.plotly_chart(fig1, use_container_width=True)
        
    with pie_col2:
        st.subheader("Severities")
        fig2 = px.pie(df, names='Severity', hole=0.4, color='Severity',
                     color_discrete_map={'Critical': '#ff4b4b', 'High': '#faca2b', 'Medium': '#00bfff', 'Low': '#90ee90'})
        fig2.update_layout(showlegend=False, paper_bgcolor="rgba(0,0,0,0)", font_color="black", margin=dict(t=10, b=10, l=10, r=10))
        st.plotly_chart(fig2, use_container_width=True)

with col_bottom_right:
    col_fp_title, col_fp_slider = st.columns([3, 2])
    with col_fp_title:
        st.subheader("False Positive Monitoring")
    with col_fp_slider:
        threshold = st.slider("False Positive Threshold (ML Prob)", 0.0, 1.0, 0.65, 0.05)

    # Tính toán lại False Positives và FPR dựa trên thanh trượt
    df['ML_prob_numeric'] = pd.to_numeric(df['ML probability'], errors='coerce').fillna(0)
    # Lọc: Rule thì từ chối (Reject) nhưng AI lại chấm điểm lớn hơn hoặc bằng thanh trượt
    dynamic_fp_df = df[(df['ML_prob_numeric'] >= threshold) & (df['Rule Decision'] == 'Reject')]
    
    current_fpr = (len(dynamic_fp_df) / total_apps * 100) if total_apps > 0 else 0
    
    # Hiển thị FPR giống trong hình
    st.markdown(f"**FPR: {current_fpr:.2f}%**")

    fp_cols = ['Timestamp', 'National ID', 'Customer', 'Monthly Income', 'Loan Amount', 'ML probability', 'Final Decision', 'Reject Reason']
    if not dynamic_fp_df.empty:
        st.dataframe(dynamic_fp_df[fp_cols], use_container_width=True, hide_index=True)
    else:
        st.info("No False Positives.")
