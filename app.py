import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="AI Loan Approval Demo", layout="wide")

st.title("AI Loan Approval Decision Engine")

# =====================================================
# LOAD DATA
# =====================================================

@st.cache_data
def load_customer():

    df = pd.read_excel("data-test.xlsx", dtype={"national_id": str})
    df["national_id"] = df["national_id"].astype(str).str.strip()

    return df


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


customer_df = load_customer()
internal_df = load_internal()
cic_df = load_cic()

# =====================================================
# CUSTOMER LOOKUP
# =====================================================

st.header("Customer Lookup")

national_id = st.text_input("Enter National ID")

customer = None
internal = None
cic = None

if national_id:

    national_id = national_id.strip()

    customer_match = customer_df[customer_df["national_id"] == national_id]

    if not customer_match.empty:
        customer = customer_match.iloc[0]

    internal_match = internal_df[internal_df["national_id"] == national_id]

    if not internal_match.empty:
        internal = internal_match.iloc[0]

    cic_match = cic_df[cic_df["national_id"] == national_id]

    if not cic_match.empty:
        cic = cic_match.iloc[0]

    if customer is None:

        st.error("Customer not found in dataset")

    else:

        st.success("Customer Found")

# =====================================================
# CUSTOMER PROFILE
# =====================================================

if customer is not None:

    st.header("Customer Profile")

    dob = pd.to_datetime(customer["dob"])
    age = datetime.now().year - dob.year

    nationality = customer["nationality"]

    if internal is not None:
        customer_type = "ETB"
    else:
        customer_type = "NTB"

    col1, col2 = st.columns(2)

    with col1:

        st.text_input("Full Name", customer["full_name"], disabled=True)
        st.text_input("Nationality", nationality, disabled=True)

    with col2:

        st.text_input("Customer Type", customer_type, disabled=True)
        st.text_input("DOB", str(dob.date()), disabled=True)

    st.write("Age:", age)

# =====================================================
# LOAN INPUT
# =====================================================

if customer is not None:

    st.header("Loan Application Input")

    col1, col2 = st.columns(2)

    with col1:

        monthly_income = st.number_input("Monthly Income", 0.0)
        monthly_expenses = st.number_input("Monthly Expenses", 0.0)
        employment_years = st.number_input("Employment Years", 0)

    with col2:

        employment_status = st.selectbox(
            "Employment Status",
            ["Full-time", "Part-time", "Self-employed", "Unemployed"]
        )

        loan_amount = st.number_input("Requested Loan Amount", 0.0)

    run_check = st.button("Check Loan Approval")

# =====================================================
# DECISION ENGINE
# =====================================================

if customer is not None and run_check:

    st.header("AI Rule Engine")

    # CIC SAFE READ

    credit_score = None
    max_dpd30 = 0
    existing_debt = 0

    if cic is not None:

        credit_score = cic.get("credit_score", None)

        max_dpd30 = cic.get(
            "max_dpd30",
            cic.get("dpd_30", 0)
        )

        existing_debt = cic.get(
            "existing_debt_obligations",
            cic.get("existing_debt", 0)
        )

    # =================================================
    # LAYER 1
    # =================================================

    st.subheader("Layer 1 – Knock-out Rules")

    if age < 18 or age > 65:

        st.error("Reject: Age outside 18-65")

        st.stop()

    if nationality.lower() != "vietnam":

        st.error("Reject: Unsupported nationality")

        st.stop()

    st.success("Layer 1 Passed")

    # =================================================
    # LAYER 2
    # =================================================

    st.subheader("Layer 2 – Internal Data")

    is_blacklisted = 0

    if internal is not None:

        is_blacklisted = internal.get("is_blacklisted", 0)

    st.write("Customer Type:", customer_type)

    if is_blacklisted == 1:

        st.error("Reject: Customer in Internal Blacklist")

        st.stop()

    st.success("Layer 2 Passed")

    # =================================================
    # LAYER 3
    # =================================================

    st.subheader("Layer 3 – CIC Rules")

    if max_dpd30 == 1:

        st.error("Reject: Bad CIC repayment history")

        st.stop()

    if credit_score is None or credit_score <= 430:

        st.error("Reject: Low credit score")

        st.stop()

    st.success("Layer 3 Passed")

    # =================================================
    # LAYER 4
    # =================================================

    st.subheader("Layer 4 – Capacity Rules")

    if monthly_income < 500:

        st.error("Reject: Monthly income below minimum")

        st.stop()

    new_debt = 0.05 * loan_amount

    dti2 = (existing_debt + new_debt) / monthly_income

    st.write("DTI2:", round(dti2, 2))

    if dti2 >= 0.5:

        st.error("Reject: Debt-to-Income too high")

        st.stop()

    approve_prob = min(0.95, (credit_score / 850) + (0.5 - dti2))

    st.write("ML Approval Probability:", round(approve_prob, 2))

    if approve_prob <= 0.7:

        st.error("Reject: ML risk score too low")

        st.stop()

    st.success("Layer 4 Passed")

    # =================================================
    # FINAL DECISION
    # =================================================

    st.header("Final Decision")

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

    st.write("Decision:", decision)

    st.write("Approved Loan Amount:", round(final_amount, 2))
