def decision_engine(customer_type,
                    credit_score,
                    dti2,
                    loan_amount,
                    monthly_income,
                    existing_debt):

    # --- DTI > 50% ---
    if dti2 > 0.50:
        return "Reject", None

    # --- DTI <= 36% ---
    if dti2 <= 0.36:
        if credit_score is not None:
            if credit_score >= 431:
                return "Approve", loan_amount
        else:  # credit_score is None
            if customer_type == "ETB":
                return "Approve", loan_amount
            return "Manual Review", None

    # --- 36% < DTI <= 50% ---
    if dti2 <= 0.50:
        if credit_score is not None:
            if credit_score >= 570:
                return "Approve", loan_amount
            if 431 <= credit_score <= 569:
                return "Manual Review", None
        else:  # credit_score is None
            if customer_type == "ETB":
                limit = (0.36 * monthly_income - existing_debt) / 0.1
                # Đảm bảo số tiền duyệt không vượt quá số tiền xin vay
                final_limit = round(limit, -6)
                approved_limit = min(final_limit, loan_amount)
                return "Partial Approve", approved_limit
            return "Manual Review", None

    return "Reject", None
