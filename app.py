import streamlit as st
import pandas as pd
import joblib
import json

st.set_page_config(page_title="AI Credit Approval", layout="wide")

st.title("AI Loan Approval Decision System")

# -------------------------------------------------
# LOAD MODEL + CONFIG
# -------------------------------------------------

model = joblib.load("credit_model.pkl")

with open("model_features.json") as f:
    features = json.load(f)

with open("mapping.json") as f:
    mapping = json.load(f)

# -------------------------------------------------
# SIDEBAR INPUT
# -------------------------------------------------

st.sidebar.header("Customer Profile")

age = st.sidebar.slider("Age",18,70,30)

gender = st.sidebar.selectbox("Gender", list(mapping["gender"].keys()))

employment_years = st.sidebar.slider("Employment Years",0,20,5)

employment_status = st.sidebar.selectbox(
    "Employment Status",
    list(mapping["employment_status"].keys())
)

monthly_income = st.sidebar.number_input("Monthly Income",1000,20000,5000)

monthly_expenses = st.sidebar.number_input("Monthly Expenses",0,10000,2000)

credit_history_years = st.sidebar.slider("Credit History Years",0,20,5)

past_default = st.sidebar.selectbox(
    "Past Default",
    list(mapping["past_default"].keys())
)

residence_type = st.sidebar.selectbox(
    "Residence Type",
    list(mapping["residence_type"].keys())
)

loan_amount = st.sidebar.number_input("Loan Amount",1000,50000,10000)

education = st.sidebar.selectbox(
    "Education",
    list(mapping["education"].keys())
)

loan_intent = st.sidebar.selectbox(
    "Loan Purpose",
    list(mapping["loan_intent"].keys())
)

interest_rate = st.sidebar.slider("Interest Rate",1.0,20.0,10.0)

credit_score = st.sidebar.slider("Credit Score",300,850,650)

existing_debt = st.sidebar.number_input("Existing Monthly Debt",0,5000,500)

max_dpd = st.sidebar.number_input("Max Days Past Due",0,120,0)

is_blacklist = st.sidebar.selectbox("Blacklist",["no","yes"])

customer_type = st.sidebar.selectbox("Customer Type",["NTB","ETB"])

# -------------------------------------------------
# RULE ENGINE
# -------------------------------------------------

def run_rules():

    rules = []

    # Layer 1 Age
    if age < 18 or age > 65:
        rules.append(("Layer 1 - Age Policy","Reject"))
        return rules
    else:
        rules.append(("Layer 1 - Age Policy","Pass"))

    # Layer 2 blacklist
    if is_blacklist == "yes":
        rules.append(("Layer 2 - Blacklist","Reject"))
        return rules
    else:
        rules.append(("Layer 2 - Blacklist","Pass"))

    # Layer 3 credit behavior
    if max_dpd > 30:
        rules.append(("Layer 3 - Delinquency Check","Reject"))
        return rules

    if credit_score <= 430:
        rules.append(("Layer 3 - Credit Score","Reject"))
        return rules

    rules.append(("Layer 3 - Credit Behavior","Pass"))

    # Layer 4 affordability
    if monthly_income < 500:
        rules.append(("Layer 4 - Income Check","Reject"))
        return rules

    dti = existing_debt / monthly_income

    if dti >= 0.5:
        rules.append(("Layer 4 - DTI","Reject"))
        return rules

    rules.append(("Layer 4 - Affordability","Pass"))

    return rules

# -------------------------------------------------
# DECISION MATRIX
# -------------------------------------------------

def decision_engine(prob, credit_score, dti):

    if prob >= 0.7:

        if credit_score >= 570 and dti <= 0.5:
            return "Approve"

        if 431 <= credit_score <= 569 and dti <= 0.36:
            return "Approve"

        if 431 <= credit_score <= 569 and dti <= 0.5:
            return "Partial Approve"

    if prob >= 0.5:
        return "Manual Review"

    return "Reject"

# -------------------------------------------------
# RUN SYSTEM
# -------------------------------------------------

if st.button("Run Loan Decision"):

    st.header("1️⃣ Rule Engine")

    rules = run_rules()

    stop = False

    for r in rules:

        if r[1] == "Pass":
            st.success(r[0] + " PASS")

        else:
            st.error(r[0] + " FAIL")
            stop = True

    if stop:
        st.error("Application Rejected by Policy Rules")
        st.stop()

    # -------------------------------------------------
    # FEATURE ENGINEERING
    # -------------------------------------------------

    loan_percent_income = loan_amount / monthly_income

    expense_to_income = monthly_expenses / monthly_income

    disposable_income = monthly_income - monthly_expenses

    loan_to_disposable_income = loan_amount / disposable_income

    data = {
        "age": age,
        "gender": mapping["gender"][gender],
        "employment_years": employment_years,
        "employment_status": mapping["employment_status"][employment_status],
        "monthly_income": monthly_income,
        "monthly_expenses": monthly_expenses,
        "credit_history_years": credit_history_years,
        "past_default": mapping["past_default"][past_default],
        "residence_type": mapping["residence_type"][residence_type],
        "loan_amount": loan_amount,
        "education": mapping["education"][education],
        "loan_intent": mapping["loan_intent"][loan_intent],
        "interest_rate": interest_rate,
        "loan_percent_income": loan_percent_income,
        "credit_score": credit_score,
        "expense_to_income": expense_to_income,
        "disposable_income": disposable_income,
        "loan_to_disposable_income": loan_to_disposable_income
    }

    df = pd.DataFrame([data])
    df = df[features]

    # -------------------------------------------------
    # ML PREDICTION
    # -------------------------------------------------

    prob = model.predict_proba(df)[0][1]

    dti = existing_debt / monthly_income

    st.header("2️⃣ Machine Learning Risk Scoring")

    col1,col2,col3 = st.columns(3)

    col1.metric("ML Approval Probability", round(prob,2))
    col2.metric("Debt To Income", round(dti,2))
    col3.metric("Credit Score", credit_score)

    # -------------------------------------------------
    # FINAL DECISION
    # -------------------------------------------------

    result = decision_engine(prob, credit_score, dti)

    st.header("3️⃣ Final Decision")

    if result == "Approve":
        st.success("APPROVED")

    elif result == "Partial Approve":
        st.warning("PARTIAL APPROVAL")

    elif result == "Manual Review":
        st.info("MANUAL REVIEW REQUIRED")

    else:
        st.error("REJECTED")

    # -------------------------------------------------
    # AI EXPLANATION
    # -------------------------------------------------

    st.header("4️⃣ AI Decision Explanation")

    reasons = []

    if prob < 0.5:
        reasons.append("ML model predicts HIGH default risk")

    if credit_score < 500:
        reasons.append("Low credit score increases risk")

    if dti > 0.5:
        reasons.append("Debt-to-Income ratio is too high")

    if loan_percent_income > 0.5:
        reasons.append("Loan amount too large relative to income")

    if expense_to_income > 0.7:
        reasons.append("Customer expenses consume most income")

    if len(reasons) == 0:
        st.write("Risk indicators within acceptable range")

    else:
        for r in reasons:
            st.write("•", r)

    # -------------------------------------------------
    # DEBUG DATA
    # -------------------------------------------------

    with st.expander("View Model Input Features"):
        st.dataframe(df)
