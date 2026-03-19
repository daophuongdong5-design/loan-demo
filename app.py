import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(layout="wide")
st.title("AI Loan Approval Decision Engine")

# ================================
# LOAD DATA
# ================================

@st.cache_data
def load_internal():
    df = pd.read_csv("Internal_mock_data_20k.csv", dtype={"national_id": str})
    df["national_id"] = df["national_id"].astype(str).str.strip()
    return df

@st.cache_data
def load_cic():
    df = pd.read_csv("CIC_mock_data_100k.csv", dtype={"national_id": str})
    df["national_id"] = df["national_id"].astype(str).str.strip()
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

if national_id:

    national_id = national_id.strip()

    internal_match = internal_df[internal_df["national_id"] == national_id]
    cic_match = cic_df[cic_df["national_id"] == national_id]

    if not internal_match.empty:
        internal = internal_match.iloc[0]

    if not cic_match.empty:
        cic = cic_match.iloc[0]

    if internal is None and cic is None:
        st.error("Customer not found in BOTH datasets")
    else:
        st.success("Customer Found")

# ================================
# PROFILE (fallback từ CIC/Internal)
# ================================

# ================================
# CUSTOMER PROFILE (AUTO-FILL)
# ================================

if internal is not None or cic is not None:

    st.header("Customer Profile")

    # ======================
    # LẤY DATA (PRIORITY)
    # ======================

    full_name = None
    dob = None
    nationality = "Vietnam"  # default

    # Ưu tiên INTERNAL
    if internal is not None:

        full_name = internal.get("full_name", "Unknown")
        dob = pd.to_datetime(internal.get("dob", "1990-01-01"))
        nationality = internal.get("nationality", "Vietnam")

    # fallback CIC nếu thiếu
    elif cic is not None:

        full_name = cic.get("full_name", "Unknown")
        dob = pd.to_datetime(cic.get("dob", "1990-01-01"))
        nationality = cic.get("nationality", "Vietnam")

    # ======================
    # TÍNH AGE
    # ======================

    age = datetime.now().year - dob.year if dob is not None else 30

    # ======================
    # CUSTOMER TYPE
    # ======================

    customer_type = "ETB" if internal is not None else "NTB"

    # ======================
    # UI
    # ======================

    col1, col2 = st.columns(2)

    with col1:
        st.text_input("Full Name", value=full_name, disabled=True)
        st.text_input("Nationality", value=nationality, disabled=True)

    with col2:
        st.text_input("Customer Type", value=customer_type, disabled=True)
        st.text_input("DOB", value=str(dob.date()), disabled=True)

    st.write("Age:", age)

# ================================
# INPUT
# ================================

if internal is not None or cic is not None:

    st.header("Loan Input")

    monthly_income = st.number_input("Monthly Income", 0.0)
    monthly_expenses = st.number_input("Monthly Expenses", 0.0)
    loan_amount = st.number_input("Loan Amount", 0.0)

    run = st.button("Run Decision Engine")

# ================================
# ENGINE
# ================================

if (internal is not None or cic is not None) and run:

    st.header("Decision Engine Output")

    # CIC SAFE
    credit_score = cic.get("credit_score", None) if cic is not None else None
    max_dpd30 = cic.get("max_dpd30", cic.get("dpd_30", 0)) if cic is not None else 0
    existing_debt = cic.get(
        "existing_debt_obligations",
        cic.get("existing_debt", 0)
    ) if cic is not None else 0

    blacklist = internal.get("is_blacklisted", 0) if internal is not None else 0

    # =============================
    # LAYER 1
    # =============================

    st.subheader("Layer 1")

    if age < 18 or age > 65:
        st.error(f"Age = {age} → ❌ Reject")
        st.stop()
    else:
        st.success(f"Age = {age} → ✅ Pass")

    # =============================
    # LAYER 2
    # =============================

    st.subheader("Layer 2")

    if blacklist == 1:
        st.error("Blacklist = 1 → ❌ Reject")
        st.stop()
    else:
        st.success("Blacklist = 0 → ✅ Pass")

    # =============================
    # LAYER 3
    # =============================

    st.subheader("Layer 3")

    if max_dpd30 == 1:
        st.error(f"DPD30 = {max_dpd30} → ❌ Reject")
        st.stop()
    else:
        st.success(f"DPD30 = {max_dpd30} → ✅ Pass")

    if credit_score is None or credit_score <= 430:
        st.error(f"CIC Score = {credit_score} → ❌ Reject (low score)")
        st.stop()
    else:
        st.success(f"CIC Score = {credit_score} → ✅ Pass")

    # =============================
    # LAYER 4 (DTI_1)
    # =============================

    st.subheader("Layer 4")

    if monthly_income < 500:
        st.error(f"Income = {monthly_income} → ❌ Reject (<500)")
        st.stop()
    else:
        st.success(f"Income = {monthly_income} → ✅ Pass")

    dti_1 = existing_debt / monthly_income if monthly_income > 0 else 0

    st.write(f"DTI_1 = {round(dti_1,2)}")

    if dti_1 >= 0.5:
        st.error(f"DTI_1 = {round(dti_1,2)} → ❌ Reject")
        st.stop()
    else:
        st.success(f"DTI_1 = {round(dti_1,2)} → ✅ Pass")

    # ML
    prob = min(0.95, (credit_score / 850) + (0.5 - dti_1))

    st.write(f"ML Prob = {round(prob,2)}")

    if prob <= 0.7:
        st.error(f"ML Prob = {round(prob,2)} → ❌ Reject")
        st.stop()
    else:
        st.success(f"ML Prob = {round(prob,2)} → ✅ Pass")

    # =============================
    # FINAL (DTI_2)
    # =============================

    st.header("Final Decision")

    new_debt = 0.05 * loan_amount
    dti_2 = (existing_debt + new_debt) / monthly_income

    st.write(f"DTI_2 = {round(dti_2,2)}")

    approved_limit = (0.5 * monthly_income - existing_debt) / 0.05

    if loan_amount <= approved_limit:
        decision = "Approve"
        final_amount = loan_amount

    elif loan_amount <= approved_limit * 1.5:
        decision = "Partial Approve"
        final_amount = approved_limit

    else:
        decision = "Manual Review"
        final_amount = approved_limit

    st.success(f"{decision}")

    st.write(f"Approved Amount = {round(final_amount,2)}")
