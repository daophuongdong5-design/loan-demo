def decision_engine(customer_type,
                    loan_prob,
                    credit_score,
                    dti2,
                    loan_amount,
                    monthly_income,
                    existing_debt):

    # classify probability
    if loan_prob >= 0.7:
        loan_status = "high"
    elif loan_prob >= 0.5:
        loan_status = "medium"
    else:
        loan_status = "low"

    # ---------- NTB ----------
    if customer_type == "NTB":

        if loan_status == "high":

            if credit_score >= 570 and dti2 <= 0.50:
                return "Approve", loan_amount

            if 431 <= credit_score <= 569:

                if dti2 <= 0.36:
                    return "Approve", loan_amount

                if dti2 <= 0.50:
                    limit = (0.36 * monthly_income - existing_debt) / 0.05
                    return "Partial Approve", round(limit, -6)

            if credit_score is None:

                if dti2 <= 0.36:
                    return "Approve", loan_amount

                if dti2 <= 0.50:
                    limit = (0.36 * monthly_income - existing_debt) / 0.05
                    return "Partial Approve", round(limit, -6)

        if loan_status == "medium":

            if credit_score >= 570:

                if dti2 <= 0.36:
                    return "Approve", loan_amount

                if dti2 <= 0.50:
                    limit = (0.36 * monthly_income) / 0.05
                    return "Partial Approve", round(limit, -6)

            if 431 <= credit_score <= 569:

                if dti2 <= 0.36:
                    return "Manual Review", None

                return "Reject", None

            if credit_score is None:

                if dti2 <= 0.36:
                    return "Manual Review", None

                return "Reject", None

    # ---------- ETB ----------
    if customer_type == "ETB":

        if loan_status == "high":

            if credit_score >= 431 and dti2 <= 0.50:
                return "Approve", loan_amount

            if credit_score is None and dti2 <= 0.50:
                return "Approve", loan_amount

        if loan_status == "medium":
            return "Manual Review", None

    return "Reject", None
