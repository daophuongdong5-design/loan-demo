def run_rules(customer):

    results = []

    # -------- Layer 1 ----------
    if customer["age"] < 18 or customer["age"] > 65:
        results.append(("Layer1 Age Check","Reject"))
        return results

    if customer["nationality"] != "VN":
        results.append(("Layer1 Nationality","Reject"))
        return results

    results.append(("Layer1","Pass"))


    # -------- Layer 2 ----------
    if customer["is_blacklist"] == 1:
        results.append(("Layer2 Blacklist","Reject"))
        return results

    results.append(("Layer2","Pass"))


    # -------- Layer 3 ----------
    if customer["max_dpd"] > 30:
        results.append(("Layer3 DPD","Reject"))
        return results

    if customer["credit_score"] <= 430:
        results.append(("Layer3 Credit Score","Reject"))
        return results

    results.append(("Layer3","Pass"))


    # -------- Layer 4 ----------
    if customer["monthly_income"] < 500:
        results.append(("Layer4 Income","Reject"))
        return results

    dti = customer["existing_debt"] / customer["monthly_income"]

    if dti >= 0.5:
        results.append(("Layer4 DTI","Reject"))
        return results

    results.append(("Layer4","Pass"))

    return results
