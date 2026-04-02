import streamlit as st
import pandas as pd
import plotly.express as px
import os
from sqlalchemy import create_engine

# Kết nối database
engine = create_engine('sqlite:///loan_database.db')

st.set_page_config(page_title="Risk Alerts Dashboard", layout="wide")

# ==========================================
# CẤU HÌNH GIAO DIỆN (CSS Dark Theme)
# ==========================================
st.markdown("""
    <style>
    .metric-card {
        background-color: #2b2b3d;
        border-radius: 10px;
        padding: 15px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
        text-align: left;
        border: 1px solid #3d3d5c;
    }
    .metric-title { color: #a0a5b1; font-size: 14px; margin-bottom: 5px; display: flex; align-items: center; gap: 8px;}
    .metric-value { color: #ffffff; font-size: 26px; font-weight: bold; }
    .sub-red { color: #ff4b4b; }
    .sub-yellow { color: #faca2b; }
    
    /* Thu gọn padding của các cột Streamlit */
    div[data-testid="column"] { padding: 0 10px; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# ADMIN PANEL (SIDEBAR)
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
def load_data():
    try:
        df = pd.read_sql("SELECT * FROM decision_log", con=engine)
        
        # FIX LỖI PYARROW: Ép kiểu dữ liệu rõ ràng để Streamlit không bị crash
        if not df.empty:
            # 1. Ép tất cả các cột văn bản về chuẩn String
            text_cols = ['Customer', 'National ID', 'Model decision', 'Rule Decision', 'Final Decision', 'Reject Reason']
            for col in text_cols:
                if col in df.columns:
                    # Chuyển đổi sang string và xử lý các giá trị None/NaN thành chuỗi rỗng
                    df[col] = df[col].fillna("").astype(str)
            
            # 2. Ép cột số liệu về chuẩn Float (số thực), nếu rỗng thì mặc định là 0.0
            if 'DTI_2' in df.columns:
                df['DTI_2'] = pd.to_numeric(df['DTI_2'], errors='coerce').fillna(0.0)
                
        return df
    except Exception as e:
        return pd.DataFrame()

df = load_data()

# ==========================================
# 2. XỬ LÝ LOGIC RULE 
# ==========================================
def determine_alert_and_severity(row):
    reason = str(row.get('Reject Reason', '')).lower()
    
    try: dti_2 = float(row.get('DTI_2', 0)) if pd.notna(row.get('DTI_2')) else 0
    except: dti_2 = 0
        
    try: ml_prob = float(row.get('ML probability', 1.0)) if pd.notna(row.get('ML probability')) else 1.0
    except: ml_prob = 1.0
        
    try: credit_score = float(row.get('Credit Score', 999)) if pd.notna(row.get('Credit Score')) else 999
    except: credit_score = 999

    alert_type = "Normal"
    
    if "blacklist" in reason or "dpd" in reason or (0 < credit_score <= 430) or "low cic" in reason or "dti_1" in reason or ml_prob < 0.7 or dti_2 > 0.5:
        alert_type = "High Risk"
    elif 0.36 < dti_2 <= 0.5:
        alert_type = "Borderline"
    elif "age" in reason or "nationality" in reason or "income" in reason or "missing" in reason:
        alert_type = "Policy Issue"
        
    severity_map = {
        "High Risk": "Critical",
        "Borderline": "High",
        "Policy Issue": "Medium",
        "Normal": "Low"
    }
    
    return pd.Series([alert_type, severity_map[alert_type]])

df[['Alert Type', 'Severity']] = df.apply(determine_alert_and_severity, axis=1)

# Tính toán các chỉ số KPI
total_apps = len(df)
total_alerts = len(df[df['Alert Type'] != 'Normal'])

# Đổi KPI từ % Reject thành % High Risk cho giống hình
high_risk_count = len(df[df['Alert Type'] == 'High Risk'])
pct_high_risk = (high_risk_count / total_apps * 100) if total_apps > 0 else 0

false_positive_df = df[(df['Model decision'] == 'Approve') & ((df['Rule Decision'] == 'Reject') | (df['Final Decision'] == 'Reject'))]
fp_count = len(false_positive_df)
pct_false_positive = (fp_count / total_apps * 100) if total_apps > 0 else 0

# ==========================================
# 3. HEADER METRICS (Top Row)
# ==========================================
m1, m2, m3, m4 = st.columns(4)

m1.markdown(f"""
<div class="metric-card">
    <div class="metric-title">📑 Total Applications</div>
    <div class="metric-value">{total_apps:,}</div>
</div>
""", unsafe_allow_html=True)

m2.markdown(f"""
<div class="metric-card">
    <div class="metric-title">🔔 Total Alerts</div>
    <div class="metric-value">{total_alerts:,}</div>
</div>
""", unsafe_allow_html=True)

m3.markdown(f"""
<div class="metric-card">
    <div class="metric-title">⚠️ % High Risk</div>
    <div class="metric-value"><span class="sub-red">{pct_high_risk:.1f}%</span></div>
</div>
""", unsafe_allow_html=True)

m4.markdown(f"""
<div class="metric-card">
    <div class="metric-title">⚠️ % False Positives</div>
    <div class="metric-value"><span class="sub-yellow">{pct_false_positive:.1f}%</span></div>
</div>
""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ==========================================
# 4. CHIA CỘT CHÍNH (Trái 65% - Phải 35%)
# ==========================================
col_left, col_right = st.columns([6.5, 3.5])

# --- CỘT TRÁI: BẢNG RISK ALERTS ---
with col_left:
    st.subheader("Risk Alerts")
    
    # Rút gọn cột hiển thị cho giống UI Design
    display_cols = ['Customer', 'DTI_2', 'Alert Type', 'Severity', 'Final Decision']
    
    def style_dataframe(row):
        colors = [''] * len(row)
        alert = row['Alert Type']
        if alert == 'High Risk': bg_color = 'background-color: rgba(239, 85, 59, 0.2); color: #EF553B;'
        elif alert == 'Borderline': bg_color = 'background-color: rgba(254, 203, 82, 0.2); color: #FECB52;'
        elif alert == 'Policy Issue': bg_color = 'background-color: rgba(99, 110, 250, 0.2); color: #636EFA;'
        else: bg_color = 'color: #00CC96;' 
        
        try:
            colors[row.index.get_loc('Alert Type')] = bg_color
            colors[row.index.get_loc('Severity')] = bg_color
        except: pass
        return colors

    st.dataframe(
        df[display_cols].style.apply(style_dataframe, axis=1).format({"DTI_2": "{:.2f}"}),
        use_container_width=True,
        hide_index=True,
        height=550
    )

# --- CỘT PHẢI: BIỂU ĐỒ & BẢNG FALSE POSITIVE ---
with col_right:
    # 1. Biểu đồ Pie
    st.subheader("Alert Severities")
    alert_counts = df['Alert Type'].value_counts().reset_index()
    alert_counts.columns = ['Alert Type', 'Count']
    
    color_discrete_map = {
        'High Risk': '#EF553B',
        'Borderline': '#FECB52',
        'Policy Issue': '#636EFA',
        'Normal': '#00CC96'
    }
    
    fig = px.pie(
        alert_counts, values='Count', names='Alert Type', hole=0.5, 
        color='Alert Type', color_discrete_map=color_discrete_map
    )
    fig.update_layout(
        margin=dict(t=0, b=10, l=0, r=0),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="white"),
        legend=dict(orientation="v", yanchor="middle", y=0.5, xanchor="left", x=1.0)
    )
    st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("<br>", unsafe_allow_html=True)

    # 2. Bảng False Positive (Rút gọn giống hình)
    st.subheader("False Positive Monitoring")
    
    fp_display_cols = ['Customer', 'Model decision', 'Rule Decision', 'Final Decision']
    
    if not false_positive_df.empty:
        st.dataframe(
            false_positive_df[fp_display_cols],
            use_container_width=True,
            hide_index=True,
            height=250
        )
    else:
        st.info("Chưa có hồ sơ False Positive.")
