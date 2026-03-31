import streamlit as st
import pandas as pd
import joblib
from datetime import datetime

st.set_page_config(layout="wide")
st.title("AI Loan Approval Decision Engine")

# ================================
# LOAD DATA
# ================================

@st.cache_data
def load_internal():
    # Sử dụng try-except phòng trường hợp file chưa tồn tại ở môi trường test
    try:
        df = pd.read_csv("Internal_mock_data_20k.csv", dtype={"national_id": str})
        df["national_id"] = df["national_id"].astype(str).str.strip()
    except:
        df = pd.DataFrame(columns=["national_id", "full_name", "dob", "nationality", "is_blacklisted"])
    return df

@st.cache_data
def load_cic():
    try:
        df = pd.read_csv("CIC_mock_data_100k.csv", dtype={"national_id": str})
        df["national_id"] = df["national_id"].astype(str).str.strip()
    except:
        df = pd.DataFrame(columns=["national_id", "full_name", "dob", "nationality", "credit_score", "max_dpd30", "existing_debt_obligations"])
    return df

internal_df = load_internal()
cic_df = load_cic()

# ================================
# LOOKUP
# ================================

st.header("Customer Lookup")

national_id = st.text_input("Enter National ID")

internal = None
cic = None
user_found = False

if national_id:
    national_id = national_id.strip()

    internal_match = internal_df[internal_df["national_id"] == national_id]
    cic_match = cic_df[cic_df["national_id"] == national_id]

    if not internal_match.empty:
        internal = internal_match.iloc[0]

    if not cic_match.empty:
        cic = cic_match.iloc[0]

    if internal is None and cic is None:
        st.warning("Customer not found in datasets. Please enter information manually.")
        user_found = False
    else:
        st.success("Customer Found in DB")
        user_found = True

# Luôn hiển thị phần Profile dù có hay không để người dùng nhập tay nếu cần
st.header("Customer Profile")

# ======================
# DATA (PRIORITY / MANUAL)
# ======================

if user_found:
    # Lấy data từ DB, ưu tiên Internal
    full_name_val = internal.get("full_name") if internal is not None else cic.get("full_name", "Unknown")
    
    # Xử lý ngày sinh an toàn
    raw_dob = internal.get("dob") if internal is not None else cic.get("dob", "1990-01-01")
    dob_val = pd.to_datetime(raw_dob)
    
    nationality_val = internal.get("nationality") if internal is not None else cic.get("nationality", "Vietnam")
    
    customer_type = "ETB" if internal is not None else "NTB"
    is_disabled = True
else:
    # Cho phép nhập tay
    full_name_val = ""
    dob_val = datetime(1990, 1, 1)
    nationality_val = "Vietnam"
    customer_type = "NTB"
    is_disabled = False

# ======================
# UI PROFILE
# ======================

col1, col2 = st.columns(2)

with col1:
    full_name = st.text_input("Full Name", value=full_name_val, disabled=is_disabled)
    nationality = st.text_input("Nationality", value=nationality_val, disabled=is_disabled)

with col2:
    st.text_input("Customer Type", value=customer_type, disabled=True)
    if is_disabled:
        st.text_input("DOB", value=str(dob_val.date()), disabled=True)
        dob = dob_val
    else:
        dob_input = st.date_input("DOB", value=dob_val.date(), min_value=datetime(1900, 1, 1).date(), max_value=datetime.now().date())
        dob = pd.to_datetime(dob_input)

# TÍNH AGE
age = datetime.now().year - dob.year if dob is not None else 30
st.write("Age:", age)

# ================================
# INPUT LOAN & EMPLOYMENT
# ================================

st.header("Loan & Employment Input")

col3, col4 = st.columns(2)
with col3:
    monthly_income = st.number_input("Monthly Income", 0.0)
    monthly_expenses = st.number_input("Monthly Expenses", 0.0)
    loan_amount = st.number_input("Loan Amount", 0.0)
with col4:
    employment_years = st.number_input("Employment Years", 0.0, step=0.5, help="Biến phục vụ ML")
    employment_status = st.selectbox("Employment Status", ["Employed", "Self-Employed", "Business Owner", "Freelancer", "Unemployed", "Student"])

run = st.button("Run Decision Engine")

# ================================
# ENGINE
# ================================

if run:
    st.header("Decision Engine Output")

    # CIC / INTERNAL SAFE DEFAULTS (Nếu NTB nhập tay thì lấy default)
    credit_score = None
    max_dpd30 = 0
    existing_debt = 0
    blacklist = 0

    if user_found:
        credit_score = cic.get("credit_score", None) if cic is not None else None
        # Xử lý trường hợp pd.isna
        if pd.isna(credit_score):
            credit_score = None
            
        max_dpd30 = cic.get("max_dpd30", cic.get("dpd_30", 0)) if cic is not None else 0
        existing_debt = cic.get("existing_debt_obligations", cic.get("existing_debt", 0)) if cic is not None else 0
        blacklist = internal.get("is_blacklisted", 0) if internal is not None else 0

    # =============================
    # LAYER 1: Tuổi
    # =============================
    st.subheader("Layer 1: Age")
    if age < 18 or age > 65:
        st.error(f"Age = {age} → ❌ Reject")
        st.stop()
    else:
        st.success(f"Age = {age} → ✅ Pass")

    # =============================
    # LAYER 2: Blacklist
    # =============================
    st.subheader("Layer 2: Blacklist")
    if blacklist == 1:
        st.error("Blacklist = 1 → ❌ Reject")
        st.stop()
    else:
        st.success("Blacklist = 0 → ✅ Pass")

    # =============================
    # LAYER 3: DPD & CIC Score
    # =============================
    st.subheader("Layer 3: CIC & DPD")
    
    if max_dpd30 == 1:
        st.error(f"DPD30 = {max_dpd30} → ❌ Reject")
        st.stop()
    else:
        st.success(f"DPD30 = {max_dpd30} → ✅ Pass")

    if credit_score is None:
        st.warning("CIC Score = NULL → ⚠️ No data, check other conditions")
        # Không dùng st.stop() ở đây nữa
    elif credit_score <= 430:
        st.error(f"CIC Score = {credit_score} → ❌ Reject (low score)")
        st.stop()
    else:
        st.success(f"CIC Score = {credit_score} → ✅ Pass")

    # =============================
    # LAYER 4: DTI_1 & ML Model
    # =============================
    st.subheader("Layer 4: Income & DTI 1")

    if monthly_income < 500:
        st.error(f"Income = {monthly_income} → ❌ Reject (<500)")
        st.stop()
    else:
        st.success(f"Income = {monthly_income} → ✅ Pass")

    dti_1 = existing_debt / monthly_income if monthly_income > 0 else 1.0
    st.write(f"DTI_1 = {round(dti_1, 2)}")

    if dti_1 >= 0.5:
        st.error(f"DTI_1 = {round(dti_1, 2)} → ❌ Reject")
        st.stop()
    else:
        st.success(f"DTI_1 = {round(dti_1, 2)} → ✅ Pass")

    # --- ML Probability from trained model ---
    import joblib

    @st.cache_resource
    def load_credit_model():
        return joblib.load("credit_model.pkl")

    credit_model = load_credit_model()

    # Các biến có sẵn từ app
    cs_dummy = credit_score if credit_score is not None else 500
    credit_history_years = int(cic.get("credit_history_years", 0)) if user_found and cic is not None else 0
    past_default = int(internal.get("past_default", 0)) if user_found and internal is not None else 0

    # Nếu internal.csv có interest_rate thì lấy, không có thì default
    raw_interest_rate = internal.get("interest_rate", "18%") if user_found and internal is not None else "18%"
    interest_rate = float(str(raw_interest_rate).replace("%", ""))

    loan_percent_income = loan_amount / monthly_income if monthly_income > 0 else 0
    expense_to_income = monthly_expenses / monthly_income if monthly_income > 0 else 0
    disposable_income = monthly_income - monthly_expenses
    loan_to_disposable_income = loan_amount / disposable_income if disposable_income > 0 else 999

    # Categorical fields: phải map đúng theo lúc train
    gender_map = {"Male": 0, "Female": 1}
    employment_status_map = {
        "Employed": 0,
        "Self-Employed": 1,
        "Business Owner": 2,
        "Freelancer": 3,
        "Unemployed": 4,
        "Student": 5,
    }
    residence_type = 0   # default nếu UI chưa có input
    education = 0        # default nếu UI chưa có input
    loan_intent = 0      # default nếu UI chưa có input
    gender = 0           # default nếu UI chưa có input

    X = pd.DataFrame([{
        "age": age,
        "gender": gender,
        "employment_years": employment_years,
        "employment_status": employment_status_map.get(employment_status, 0),
        "monthly_income": monthly_income,
        "monthly_expenses": monthly_expenses,
        "credit_history_years": credit_history_years,
        "past_default": past_default,
        "residence_type": residence_type,
        "loan_amount": loan_amount,
        "education": education,
        "loan_intent": loan_intent,
        "interest_rate": interest_rate,
        "loan_percent_income": loan_percent_income,
        "credit_score": cs_dummy,
        "expense_to_income": expense_to_income,
        "disposable_income": disposable_income,
        "loan_to_disposable_income": loan_to_disposable_income,
    }])

    # Đảm bảo đúng thứ tự cột mà model đã train
    X = X[credit_model.feature_names_in_]

    prob = float(credit_model.predict_proba(X)[0, 1])

    st.write(f"ML Prob (Loan Status) = {round(prob, 2)}")

    if prob < 0.5:
        st.error(f"ML Prob = {round(prob, 2)} → ❌ Reject (< 0.5)")
        st.stop()
    else:
        st.success(f"ML Prob = {round(prob, 2)} → ✅ Pass")

    # =============================
    # FINAL: DTI_2 & DECISION MATRIX
    # =============================
    st.header("Final Decision")

    # Tính DTI 2: Khoản vay mong muốn chiếm bao nhiêu % thu nhập?
    # Theo rule, hạn mức duyệt = (50%*monthly_income - existing_debt)/10% -> Ước tính số tiền trả góp hàng tháng là 10% loan_amount
    new_debt = 0.10 * loan_amount 
    dti_2 = (existing_debt + new_debt) / monthly_income if monthly_income > 0 else 1.0

    st.write(f"DTI_2 = {round(dti_2 * 100, 2)}%")

    # Công thức hạn mức cho Partial Approve
    calc_limit = (0.50 * monthly_income - existing_debt) / 0.10
    if calc_limit < 0: 
        calc_limit = 0

    # Matrix Logic Variables
    decision = "Reject"
    final_amount = 0.0
    prob_tier = "0.7-1.0" if prob >= 0.7 else "0.5-0.7"
    cs = credit_score

    # IMPLEMENT DECISION MATRIX VER 2
    if customer_type == "NTB":
        if prob_tier == "0.7-1.0":
            if cs is not None and cs >= 570:
                if dti_2 <= 0.50:
                    decision, final_amount = "Approve", loan_amount
                else:
                    decision, final_amount = "Reject", 0 # DTI_2 vượt mốc 50%
            elif cs is None or (431 <= cs <= 569):
                if dti_2 <= 0.36:
                    decision, final_amount = "Approve", loan_amount
                else:
                    decision, final_amount = "Partial Approve", calc_limit
        elif prob_tier == "0.5-0.7":
            if cs is not None and cs >= 570:
                if dti_2 <= 0.36:
                    decision, final_amount = "Approve", loan_amount
                else:
                    decision, final_amount = "Partial Approve", calc_limit
            elif cs is None or (431 <= cs <= 569):
                if dti_2 <= 0.36:
                    decision, final_amount = "Manual Review", 0
                else:
                    decision, final_amount = "Reject", 0

    elif customer_type == "ETB":
        # ETB Red Notes Override
        if dti_2 > 0.50:
            decision, final_amount = "Reject", 0
        else:
            if prob_tier == "0.7-1.0":
                decision, final_amount = "Approve", loan_amount
            elif prob_tier == "0.5-0.7":
                decision, final_amount = "Manual Review", 0

    # Ràng buộc thêm: nếu Partial Approve mà calc_limit = 0 thì báo Reject
    if decision == "Partial Approve" and final_amount <= 0:
        decision = "Reject"
        final_amount = 0

    # RENDER KẾT QUẢ VỚI MÀU SẮC
    if decision == "Approve":
        st.success(f"🎉 Result: {decision}")
    elif decision == "Partial Approve":
        st.info(f"⚖️ Result: {decision}")
    elif decision == "Manual Review":
        st.warning(f"⚠️ Result: {decision}")
    else:
        st.error(f"❌ Result: {decision}")

    if decision in ["Approve", "Partial Approve"]:
        st.write(f"### 💰 Approved Amount = {round(final_amount, 2)}")
