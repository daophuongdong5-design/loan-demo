import shap
import pandas as pd

def explain_prediction(model, X):

    explainer = shap.TreeExplainer(model)

    shap_values = explainer.shap_values(X)

    impact = pd.DataFrame({
        "feature": X.columns,
        "impact": shap_values[0]
    })

    impact = impact.sort_values("impact", key=abs, ascending=False)

    return impact.head(5)
