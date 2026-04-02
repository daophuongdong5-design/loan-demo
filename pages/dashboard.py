from sqlalchemy import create_engine
import streamlit as st
import pandas as pd
import plotly.express as px
import os

engine = create_engine('sqlite:///loan_database.db')

def load_data():
    try:
        # Dùng câu lệnh SQL thật để kéo dữ liệu lên Dashboard
        df = pd.read_sql("SELECT * FROM decision_log", con=engine)
        # Tự động tạo cột Timestamp rỗng nếu database cũ chưa có (tránh lỗi)
        if 'Timestamp' not in df.columns:
            df['Timestamp'] = ""
        return df
    except:
        return pd.DataFrame()

st.set_page_config(page_title="Risk Alerts Dashboard", layout="wide")

# ==========================================
# CẤU HÌNH GIAO DIỆN (Mô phỏng Dark Theme & CSS)
# ==========================================
st.markdown("""
    <style>
    .metric-card {
        background-color: #1e1e2d;
        border-radius: 10px;
        padding: 20px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
        text-align: center;
    }
    .metric-title { color: #a0a5b1; font-size: 14px; margin-bottom: 5px; }
    .metric-value { color: #ffffff; font-size: 28px; font-weight: bold; }
    .metric-sub { font-size: 16px; font-weight: bold; }
    .sub-red { color: #ff4b4b; }
    .sub-yellow { color: #faca2b; }
    </style>
""", unsafe_allow_html=True)

st.title("Lending Risk Alerts Dashboard")

# ==========================================
# ADMIN PANEL: XÓA DỮ LIỆU (CHỈ HIỂN THỊ Ở SIDEBAR)
# ==========================================
with st.sidebar.expander("🛠️ Admin Panel", expanded=False):
    st.markdown("Khu vực dành riêng cho người thuyết trình.")
    # Ô nhập mật khẩu (dùng type="password" để ẩn ký tự)
    admin_pass = st.text_input("Mật khẩu Admin:", type="password", key="clear_data_pass")
    
    # Nút xóa chỉ bật lên khi nhập đúng pass (ví dụ: pass là "demo123")
    if st.button("🗑️ Xóa toàn bộ dữ liệu", disabled=(admin_pass != "demo123")):
        try:
            # Ngắt kết nối cũ (nếu có) và xóa hẳn file database
            if os.path.exists("loan_database.db"):
                os.remove("loan_database.db")
            st.success("Đã làm sạch toàn bộ dữ liệu hệ thống!")
            # Tải lại trang để dashboard cập nhật giao diện trống
            st.rerun()
        except Exception as e:
            st.error(f"Không thể xóa dữ liệu lúc này. Lỗi: {e}")

# ==========================================
# 1. ĐỌC DỮ LIỆU LOG
# ==========================================


df = load_data()

# Nút Refresh thủ công (Thêm nút này để bạn click làm mới trang nếu cần)
if st.button("🔄 LÀM MỚI DASHBOARD"):
    st.rerun()

if df.empty:
    st.warning("Chưa có dữ liệu log hoặc file log đang trống. Vui lòng quay lại tab 'App' và chạy Decision Engine.")
    st.stop()

# ==========================================
# 2. XỬ LÝ LOGIC ÁP DỤNG CÁC RULE TỪ EXCEL
# ==========================================
def determine_alert_and_severity(row):
    reason = str(row.get('Reject Reason', '')).lower()
    
    # Xử lý an toàn cho các cột số
    try:
        dti_2 = float(row.get('DTI_2', 0)) if pd.notna(row.get('DTI_2')) else 0
    except: dti_2 = 0
        
    try:
        ml_prob = float(row.get('ML probability', 1.0)) if pd.notna(row.get('ML probability')) else 1.0
    except: ml_prob = 1.0
        
    try:
        credit_score = float(row.get('Credit Score', 999)) if pd.notna(row.get('Credit Score')) else 999
    except: credit_score = 999

    alert_type = "Normal"
    
    # 1. Map High Risk (Ưu tiên kiểm tra trước)
    if "blacklist" in reason or "blacklisted" in reason:
        alert_type = "High Risk"
    elif "dpd" in reason:
        alert_type = "High Risk"
    elif 0 < credit_score <= 430 or "low cic score" in reason:
        alert_type = "High Risk"
    elif "dti_1" in reason:
        alert_type = "High Risk"
    elif ml_prob < 0.5:
        alert_type = "High Risk"
    elif dti_2 > 0.5:
        alert_type = "High Risk"
        
    # 2. Map Borderline
    elif 0.36 < dti_2 <= 0.5:
        alert_type = "Borderline"
    elif 0.5 <= ml_prob <= 0.7:
        alert_type = "Borderline"
        
    # 3. Map Policy Issue
    elif "age" in reason:
        alert_type = "Policy Issue"
    elif "nationality" in reason:
        alert_type = "Policy Issue"
    elif "income" in reason:
        alert_type = "Policy Issue"
    elif "missing" in reason or "null" in reason:
        alert_type = "Policy Issue"
        
    # Map Severity tương ứng
    severity_map = {
        "High Risk": "Critical",
        "Borderline": "High",
        "Policy Issue": "Medium",
        "Normal": "Low"
    }
    
    return pd.Series([alert_type, severity_map[alert_type]])

# Apply logic vào DataFrame
df[['Alert Type', 'Severity']] = df.apply(determine_alert_and_severity, axis=1)

# ==========================================
# 3. SECTION 1: METRICS & HEADER CONTROLS
# ==========================================
col_title, col_slider = st.columns([3, 1])
with col_slider:
    threshold = st.slider("False Positive Threshold (ML Prob)", 0.0, 1.0, 0.65, 0.05)

# Tính toán các chỉ số
total_apps = len(df)
total_alerts = len(df[df['Alert Type'] != 'Normal'])

low_approval_count = len(df[df['ML probability'] < threshold])
pct_low_approval = (low_approval_count / total_apps * 100) if total_apps > 0 else 0

rejected_count = len(df[df['Final Decision'] == 'Reject'])
pct_rejected = (rejected_count / total_apps * 100) if total_apps > 0 else 0

# False Positive: ML Approve (prob >= threshold) nhưng Rule Reject (Final hoặc Rule decision)
# Giả định: ML model decision = Approve, nhưng Final Decision = Reject
false_positive_df = df[(df['Model decision'] == 'Approve') & (df['Rule Decision'] == 'Reject')]
fp_count = len(false_positive_df)
pct_false_positive = (fp_count / total_apps * 100) if total_apps > 0 else 0

# Render các thẻ KPIs (Dùng HTML để giống giao diện dark theme)
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
    <div class="metric-title">⚠️ % Rejected (Final)</div>
    <div class="metric-value"><span class="sub-red">{pct_rejected:.1f}%</span></div>
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
# 4. LAYOUT CHÍNH: CHIA 2 CỘT (Trái 65% - Phải 35%)
# ==========================================
col_left, col_right = st.columns([6.5, 3.5])

# --- CỘT TRÁI: SECTION 2 - I. ALERTS TABLE ---
with col_left:
    st.subheader("Risk Alerts Table")
    
    # Filter Controls cho bảng
    f1, f2, f3 = st.columns(3)
    filter_alert = f1.selectbox("Alert Type", ["All"] + list(df['Alert Type'].unique()))
    filter_severity = f2.selectbox("Severity", ["All"] + list(df['Severity'].unique()))
    filter_decision = f3.selectbox("Final Decision", ["All"] + list(df['Final Decision'].unique()))
    
    # Áp dụng filter
    filtered_df = df.copy()
    if filter_alert != "All": filtered_df = filtered_df[filtered_df['Alert Type'] == filter_alert]
    if filter_severity != "All": filtered_df = filtered_df[filtered_df['Severity'] == filter_severity]
    if filter_decision != "All": filtered_df = filtered_df[filtered_df['Final Decision'] == filter_decision]
    
    # Chọn các cột cần hiển thị theo Excel (Đã thêm Timestamp lên đầu tiên)
    display_cols = ['Timestamp', 'National ID', 'Customer', 'DTI_2', 'ML probability', 'Alert Type', 'Severity', 'Final Decision', 'Reject Reason']
    
    # Đổi màu chữ cho DataFrame bằng Pandas Styling
    def style_dataframe(row):
        colors = [''] * len(row)
        alert = row['Alert Type']
        if alert == 'High Risk': bg_color = 'background-color: rgba(255, 75, 75, 0.2); color: #ff4b4b;'
        elif alert == 'Borderline': bg_color = 'background-color: rgba(250, 202, 43, 0.2); color: #faca2b;'
        elif alert == 'Policy Issue': bg_color = 'background-color: rgba(0, 191, 255, 0.2); color: #00bfff;'
        else: bg_color = 'color: #90ee90;' # Normal
        
        # Áp dụng màu cho cột Alert Type và Severity
        try:
            alert_idx = row.index.get_loc('Alert Type')
            sev_idx = row.index.get_loc('Severity')
            colors[alert_idx] = bg_color
            colors[sev_idx] = bg_color
        except: pass
        return colors

    st.dataframe(
        filtered_df[display_cols].style.apply(style_dataframe, axis=1),
        use_container_width=True,
        hide_index=True,
        height=550
    )

# --- CỘT PHẢI: SECTION 2.II & SECTION 3 ---
with col_right:
    # --- SECTION 2.II: PIE CHART ---
    st.subheader("Alert Severities Distribution")
    alert_counts = df['Alert Type'].value_counts().reset_index()
    alert_counts.columns = ['Alert Type', 'Count']
    
    # Map màu cứng để biểu đồ luôn chuẩn màu ý nghĩa
    color_discrete_map = {
        'High Risk': '#EF553B',    # Đỏ
        'Borderline': '#FECB52',   # Vàng
        'Policy Issue': '#636EFA', # Xanh dương
        'Normal': '#00CC96'        # Xanh lá
    }
    
    fig = px.pie(
        alert_counts, 
        values='Count', 
        names='Alert Type', 
        hole=0.4, # Tạo Donut chart cho hiện đại giống hình
        color='Alert Type',
        color_discrete_map=color_discrete_map
    )
    fig.update_layout(
        margin=dict(t=10, b=10, l=10, r=10),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="white"),
        legend=dict(orientation="v", yanchor="top", y=1, xanchor="left", x=1.0)
    )
    st.plotly_chart(fig, use_container_width=True)
    
    # --- SECTION 3: FALSE POSITIVE MONITOR ---
    st.subheader("False Positive Monitoring")
    st.markdown("<span style='font-size:14px; color:#a0a5b1;'>Model APPROVE but Rule REJECT</span>", unsafe_allow_html=True)
    
    # (Đã thêm Timestamp lên đầu tiên)
    fp_display_cols = ['Timestamp', 'National ID', 'Customer', 'ML probability', 'Model decision', 'Rule Decision', 'Final Decision']
    
    if not false_positive_df.empty:
        st.dataframe(
            false_positive_df[fp_display_cols],
            use_container_width=True,
            hide_index=True,
            height=250
        )
    else:
        st.info("Chưa có hồ sơ False Positive nào được ghi nhận.")
