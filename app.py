from flask import Flask, render_template, request
import numpy as np
import joblib
from scipy.special import expit
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
from datetime import datetime
import os


app = Flask(__name__)

# Load trained SVM pipeline
model = joblib.load("svm_loan_approval_pipeline.pkl")

FEATURE_ORDER = [
    'Gender',
    'Married',
    'Dependents',
    'Education',
    'Self_Employed',
    'ApplicantIncome',
    'CoapplicantIncome',
    'LoanAmount',
    'Loan_Amount_Term',
    'Credit_History',
    'Property_Area'
]


@app.route("/")
def home():
    return render_template("index.html")


@app.route('/predict', methods=['POST'])
def predict():
    try:
        input_data = [float(request.form[f]) for f in FEATURE_ORDER]
        X = np.array(input_data).reshape(1, -1)

        prediction = model.predict(X)[0]
        decision_score = model.decision_function(X)
        probability = expit(decision_score)[0] * 100

        if probability >= 70:
            risk = "LOW RISK 🟢"
        elif probability >= 40:
            risk = "MEDIUM RISK 🟠"
        else:
            risk = "HIGH RISK 🔴"

        result = "Loan Approved ✅" if prediction == 1 else "Loan Rejected ❌"

        # ---------------- Explainable AI Reasons ----------------
        reasons = []

        if X[0][9] == 0:
            reasons.append("Poor credit history reduces approval chances.")

        total_income = X[0][5] + X[0][6]
        if total_income > 0:
            loan_to_income_ratio = X[0][7] / total_income
            if loan_to_income_ratio > 0.4:
                reasons.append("High loan amount compared to income.")

        if X[0][2] >= 3:
            reasons.append("Higher number of dependents increases financial burden.")

        if X[0][4] == 1:
            reasons.append("Self-employment can be considered higher risk.")

        if not reasons:
            reasons.append("Strong financial and credit profile.")

        if prediction == 1:
            reasons.insert(0, "Good credit profile supports loan approval.")

        # 🔹 STEP 3: Build report data and generate PDF
        report_data = {
            "Decision": result,
            "Approval Probability": f"{probability:.2f}%",
            "Risk Level": risk,
            "Reasons": reasons
        }

        pdf_path = generate_pdf(report_data)

        # ✅ Updated render_template call
        return render_template(
            "index.html",
            prediction_text=result,
            probability_text=f"Approval Probability: {probability:.2f}%",
            risk_text=risk,
            reasons=reasons,
            pdf_available=True,
            pdf_path=pdf_path
        )

    except Exception as e:
        return render_template(
            "index.html",
            prediction_text="Error occurred!",
            probability_text=str(e),
            risk_text="",
            reasons=[],
            pdf_available=False
        )

    except Exception as e:
        return render_template(
            "index.html",
            prediction_text="Error occurred!",
            probability_text=str(e),
            risk_text="",
            reasons=[]
        )

def generate_pdf(report_data):
    filename = "Loan_Assessment_Report.pdf"
    filepath = os.path.join("static", filename)

    doc = SimpleDocTemplate(filepath, pagesize=A4)
    styles = getSampleStyleSheet()
    content = []

    content.append(Paragraph("<b>AI Loan Assessment Report</b>", styles['Title']))
    content.append(Spacer(1, 12))

    content.append(Paragraph(f"<b>Date:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles['Normal']))
    content.append(Spacer(1, 12))

    for key, value in report_data.items():
        content.append(Paragraph(f"<b>{key}:</b> {value}", styles['Normal']))
        content.append(Spacer(1, 8))

    content.append(Spacer(1, 12))
    content.append(Paragraph("<b>AI Decision Insights:</b>", styles['Heading2']))

    for reason in report_data["Reasons"]:
        content.append(Paragraph(f"- {reason}", styles['Normal']))

    doc.build(content)
    return filepath

if __name__ == "__main__":
    app.run(debug=True)
