import streamlit as st
import pandas as pd
import joblib
from datetime import datetime, timedelta, timezone
import os
import json
from sqlalchemy import create_engine

# Tự động tạo một database local dạng file
engine = create_engine('sqlite:///loan_database.db')

st.set_page_config(layout="wide")
st.title("AI Loan Approval Decision Engine")

# ================================
# KHỞI TẠO SESSION STATE (GIỮ DỮ LIỆU)
# ================================
if 'saved_nat_id' not in st.session_state: st.session_state['saved_nat_id'] = ""
if 'saved_income' not in st.session_state: st.session_state['saved_income'] = 0.0
if 'saved_expense' not in st.session_state: st.session_state['saved_expense'] = 0.0
if 'saved_loan' not in st.session_state: st.session_state['saved_loan'] = 0.0
if 'saved_emp_years' not in st.session_state: st.session_state['saved_emp_years'] = 0.0
if 'saved_emp_status' not in st.session_state: st.session_state['saved_emp_status'] = "Employed"

# ================================
# LOAD DATA
# ================================
@st.cache_data
def load_internal():
    try:
        df = pd.read_csv("Internal_mock_data_20k.csv", dtype={"national_id": str})
        df["national_id"] = df["national_id"].astype(str).str.strip()
    except:
        df = pd.DataFrame(columns=["national_id", "full_name", "dob", "nationality", "is_blacklisted", "past_default", "interest_rate"])
    return df

@st.cache_data
def load_cic():
    try:
        df = pd.read_csv("CIC_mock_data_100k.csv", dtype={"national_id": str})
        df["national_id"] = df["national_id"].astype(str).str.strip()
    except:
        df = pd.DataFrame(columns=["national_id", "full_name", "dob", "nationality", "credit_score", "max_dpd", "existing_debt_obligations", "credit_history_years"])
    return df

internal_df = load_internal()
cic_df = load_cic()

# ================================
# LOOKUP
# ================================
st.header("Customer Lookup")

national_id = st.text_input("Enter National ID (Bắt buộc, 11 ký tự)", key="saved_nat_id", max_chars=11)

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

st.header("Customer Profile")

# ======================
# DATA (PRIORITY / MANUAL)
# ======================
if user_found:
    full_name_val = internal.get("full_name") if internal is not None else cic.get("full_name", "Unknown")
    raw_dob = internal.get("dob") if internal is not None else cic.get("dob", "1990-01-01")
    dob_val = pd.to_datetime(raw_dob, errors='coerce')
    if pd.isna(dob_val): dob_val = datetime(1990, 1, 1)
    nationality_val = "Vietnam" 
    customer_type = "ETB" if internal is not None else "NTB"
    is_disabled = True
else:
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
    nationality = st.text_input("Nationality", value=nationality_val, disabled=True)

with col2:
    st.text_input("Customer Type", value=customer_type, disabled=True)
    if is_disabled:
        st.text_input("DOB", value=str(dob_val.date()), disabled=True)
        dob = dob_val
    else:
        dob_input = st.date_input("DOB", value=dob_val.date(), min_value=datetime(1900, 1, 1).date(), max_value=datetime.now().date())
        dob = pd.to_datetime(dob_input)

age = datetime.now().year - dob.year if dob is not None else 30
st.write("Age:", age)

# ================================
# INPUT LOAN & EMPLOYMENT
# ================================
st.header("Loan & Employment Input")

col3, col4 = st.columns(2)
with col3:
    monthly_income = st.number_input("Monthly Income", key="saved_income")
    monthly_expenses = st.number_input("Monthly Expenses", key="saved_expense")
    loan_amount = st.number_input("Loan Amount", key="saved_loan")
with col4:
    employment_years = st.number_input("Employment Years", step=0.5, key="saved_emp_years")
    status_options = ["Full time", "Part time", "Self employed", "Unemployed"]
    default_index = status_options.index(st.session_state['saved_emp_status']) if st.session_state['saved_emp_status'] in status_options else 0
    employment_status = st.selectbox("Employment Status", options=status_options, index=default_index, key="saved_emp_status")

run = st.button("Run Decision Engine")

# ================================
# ENGINE
# ================================
if run:
    if not national_id or len(national_id.strip()) != 11:
        st.error("❌ Lỗi: National ID là thông tin bắt buộc và phải có chính xác 11 ký tự. Vui lòng kiểm tra lại!")
        st.stop()

    st.header("Decision Engine Output")

    log_record = {
        "Timestamp": (datetime.now(timezone.utc) + timedelta(hours=7)).strftime("%Y-%m-%d %H:%M:%S"),
        "National ID": national_id,
        "Customer": full_name,
        "DOB": dob.strftime("%Y-%m-%d") if pd.notnull(dob) else "",
        "Customer Type": customer_type,
        "Monthly Income": monthly_income,
        "Monthly Expenses": monthly_expenses,    # Thêm mới
        "Loan Amount": loan_amount,
        "Employment Years": employment_years,    # Thêm mới
        "Employment Status": employment_status,  # Thêm mới
        "Credit Score": None,
        "DTI_2": None,
        "ML probability": None,
        "Model decision": None,
        "Rule Decision": "Pass", 
        "Final Decision": "Pending",
        "Reject Reason": "",
        "Limit": 0.0
    }

    def log_and_stop(reason, rule_dec="Reject", final_dec="Reject"):
        log_record["Reject Reason"] = reason
        log_record["Rule Decision"] = rule_dec
        log_record["Final Decision"] = final_dec
        
        df_log = pd.DataFrame([log_record])
        df_log.to_sql('decision_log', con=engine, if_exists='append', index=False)
        st.stop()

    credit_score = None
    max_dpd30 = 0
    existing_debt = 0
    blacklist = 0
    past_default = 0
    raw_interest_rate = "18%" 

    if user_found:
        if cic is not None and "credit_score" in cic:
            try:
                cs_val = float(cic["credit_score"])
                credit_score = None if pd.isna(cs_val) else cs_val
            except:
                credit_score = None

        if cic is not None:
            try: max_dpd30 = float(cic.get("max_dpd", cic.get("max_dpd30", 0)))
            except: max_dpd30 = 0
            
            try: existing_debt = float(cic.get("existing_debt_obligations", cic.get("existing_debt", 0)))
            except: existing_debt = 0
            
        if internal is not None:
            try: blacklist = int(internal.get("is_blacklisted", 0))
            except: blacklist = 0
            
            try: past_default = int(internal.get("past_default", 0))
            except: past_default = 0
            
    log_record["Credit Score"] = credit_score

    # =============================
    # LAYER 1: Tuổi
    # =============================
    st.subheader("Layer 1: Age")
    if age < 18 or age > 65:
        st.error(f"Age = {age} → ❌ Reject")
        log_and_stop(f"Age invalid ({age})")
    else:
        st.success(f"Age = {age} → ✅ Pass")

    # =============================
    # LAYER 2: Blacklist
    # =============================
    st.subheader("Layer 2: Blacklist")
    if blacklist == 1:
        st.error("Blacklist = 1 → ❌ Reject")
        log_and_stop("Customer is blacklisted")
    else:
        st.success("Blacklist = 0 → ✅ Pass")

    # =============================
    # LAYER 3: DPD & CIC Score
    # =============================
    st.subheader("Layer 3: CIC & DPD")
    
    if max_dpd30 == 1:
        st.error(f"DPD30 = {max_dpd30} → ❌ Reject")
        log_and_stop(f"Max DPD30 = {max_dpd30}")
    else:
        st.success(f"DPD30 = {max_dpd30} → ✅ Pass")

    if credit_score is None:
        st.warning("CIC Score = NULL → ⚠️ No data, check other conditions")
    elif credit_score <= 430:
        st.error(f"CIC Score = {credit_score} → ❌ Reject (low score)")
        log_and_stop(f"Low CIC Score ({credit_score})")
    else:
        st.success(f"CIC Score = {credit_score} → ✅ Pass")

    # =============================
    # LAYER 4: Capacity Rules
    # =============================
    st.subheader("Layer 4: Capacity Rules (Income, DTI 1 & ML)")

    # 4.1 Income
    if monthly_income < 500:
        st.error(f"Income = {monthly_income} → ❌ Reject (<500)")
        log_and_stop(f"Income too low ({monthly_income})")
    else:
        st.success(f"Income = {monthly_income} → ✅ Pass")

    # 4.2 DTI 1 (> 36% -> Reject)
    dti_1 = existing_debt / monthly_income if monthly_income > 0 else 1.0
    st.write(f"DTI_1 = {round(dti_1 * 100, 2)}%")

    if dti_1 > 0.36:
        st.error(f"DTI_1 = {round(dti_1 * 100, 2)}% → ❌ Reject (> 36%)")
        log_and_stop(f"DTI_1 too high ({round(dti_1 * 100, 2)}% > 36%)")
    else:
        st.success(f"DTI_1 = {round(dti_1 * 100, 2)}% → ✅ Pass")

    # 4.3 ML Probability (Tích hợp Data Mapping từ app-new.py)
    @st.cache_resource
    def load_credit_model():
        try:
            model = joblib.load("credit_model.pkl")
            with open("model_features.json") as f:
                MODEL_FEATURES = json.load(f)
            with open("mapping.json") as f:
                MAPPING = json.load(f)
            return model, MODEL_FEATURES, MAPPING
        except Exception as e:
            return None, None, None

    credit_model, MODEL_FEATURES, MAPPING = load_credit_model()
    
    if credit_model is None:
        st.warning("⚠️ No credit_model.pkl / json found. Using dummy probability 0.8")
        prob = 0.8
    else:
        if user_found and cic is not None:
            try: credit_history_years = int(cic.get("credit_history_years", 0))
            except: credit_history_years = 0
        else:
            credit_history_years = 0
        
        # -------- ENCODING --------
        employment_status_key = str(employment_status).strip().lower().replace(" ", "_")
        employment_status_val = MAPPING["employment_status"].get(employment_status_key, 0)

        loan_intent_val = MAPPING["loan_intent"]["personal"]
        education_val = MAPPING["education"]["bachelor"]
        residence_type_val = MAPPING["residence_type"]["rent"]
        gender_val = MAPPING["gender"]["male"]

        if pd.isna(past_default):
            past_default_key = "no" 
        else:
            past_default_key = "yes" if past_default == 1 else "no"
        past_default_val = MAPPING["past_default"][past_default_key]
        
        # -------- FEATURE ENGINEERING --------
        expense_to_income = monthly_expenses / monthly_income if monthly_income > 0 else 0
        disposable_income = monthly_income - monthly_expenses
        loan_percent_income = loan_amount / monthly_income if monthly_income > 0 else 0

        if disposable_income <= 0:
            loan_to_disposable_income = loan_amount
        else:
            loan_to_disposable_income = loan_amount / disposable_income

        try:
            interest_rate = float(str(raw_interest_rate).replace("%", ""))
        except:
            interest_rate = 18.0
        
        X = pd.DataFrame([{
            "age": age, 
            "gender": gender_val, 
            "employment_years": employment_years,
            "employment_status": employment_status_val,
            "monthly_income": monthly_income, 
            "monthly_expenses": monthly_expenses,
            "credit_history_years": credit_history_years, 
            "past_default": past_default_val,
            "residence_type": residence_type_val, 
            "loan_amount": loan_amount,
            "education": education_val, 
            "loan_intent": loan_intent_val,
            "interest_rate": interest_rate, 
            "loan_percent_income": loan_percent_income,
            "credit_score": 0 if credit_score is None else credit_score, 
            "expense_to_income": expense_to_income,
            "disposable_income": disposable_income, 
            "loan_to_disposable_income": loan_to_disposable_income,
        }])
        
        X = X[MODEL_FEATURES]
        
        # --- BẮT ĐẦU ĐOẠN THÊM MỚI ---
        with st.expander("🔍 Click để xem chi tiết Dữ liệu đầu vào của ML Model (X.T)"):
            st.dataframe(X.T, use_container_width=True) # Dùng st.dataframe đẹp hơn st.write
        # --- KẾT THÚC ĐOẠN THÊM MỚI ---

        proba = credit_model.predict_proba(X)[0]
        prob = float(proba[1])

    st.write(f"ML Prob (Loan Status) = {round(prob, 2)}")

    log_record["ML probability"] = round(prob, 4)
    # ML Approve chỉ khi prob >= 0.7
    log_record["Model decision"] = "Approve" if prob >= 0.7 else "Reject"

    # Rule 4.3: Xác suất < 0.7 là Reject
    if prob < 0.7:
        st.error(f"ML Prob = {round(prob, 2)} → ❌ Reject (< 0.7)")
        log_and_stop(f"ML Prob too low ({round(prob, 2)} < 0.7)", rule_dec="Pass")
    else:
        st.success(f"ML Prob = {round(prob, 2)} → ✅ Pass")

    # =============================
    # FINAL: DTI_2 & DECISION MATRIX
    # =============================
    st.header("Final Decision")

    new_debt = 0.10 * loan_amount 
    dti_2 = (existing_debt + new_debt) / monthly_income if monthly_income > 0 else 1.0

    st.write(f"DTI_2 = {round(dti_2 * 100, 2)}%")
    log_record["DTI_2"] = round(dti_2, 4)

    decision = "Reject"
    final_amount = 0.0

    # Inline Engine Logic (Giữ nguyên logic của decision_engine-new.py)
    if dti_2 > 0.50:
        decision, final_amount = "Reject", 0
    elif dti_2 <= 0.36:
        if credit_score is not None:
            if credit_score >= 431:
                decision, final_amount = "Approve", loan_amount
            else:
                decision, final_amount = "Reject", 0
        else:
            if customer_type == "ETB":
                decision, final_amount = "Approve", loan_amount
            else:
                decision, final_amount = "Manual Review", 0
    elif dti_2 <= 0.50:
        if credit_score is not None:
            if credit_score >= 570:
                decision, final_amount = "Approve", loan_amount
            elif 431 <= credit_score <= 569:
                decision, final_amount = "Manual Review", 0
            else:
                decision, final_amount = "Reject", 0
        else:
            if customer_type == "ETB":
                calc_limit = (0.36 * monthly_income - existing_debt) / 0.10
                if calc_limit < 0: calc_limit = 0
                calc_limit = round(calc_limit, -6)
                # Đảm bảo số tiền Partial Approve không lớn hơn tiền vay gốc
                approved_limit = min(calc_limit, loan_amount)
                decision, final_amount = "Partial Approve", approved_limit
            else:
                decision, final_amount = "Manual Review", 0

    # LƯU KẾT QUẢ CUỐI CÙNG VÀO LOG
    log_record["Final Decision"] = decision
    log_record["Limit"] = final_amount
    if decision == "Reject":
        log_record["Reject Reason"] = "Failed at Final Matrix / DTI_2"

    df_log = pd.DataFrame([log_record])
    df_log.to_sql('decision_log', con=engine, if_exists='append', index=False)

    # RENDER KẾT QUẢ
    if decision == "Approve":
        st.success(f"🎉 Result: {decision}")
    elif decision == "Partial Approve":
        st.info(f"⚖️ Result: {decision}")
    elif decision == "Manual Review":
        st.warning(f"⚠️ Result: {decision}")
    else:
        st.error(f"❌ Result: {decision}")

    if decision in ["Approve", "Partial Approve"]:
        st.write(f"### 💰 Approved Amount = {round(final_amount, 2):,}")
