import os
from typing import Any

import gradio as gr
import requests


API_URL = os.getenv("PREDICT_API_URL", "http://fastapi:8000/predict")
HEALTH_URL = os.getenv("HEALTH_API_URL", "http://fastapi:8000/health")


def _predict(
    age: int,
    gender: str,
    tenure: int,
    usage_frequency: int,
    support_calls: int,
    payment_delay: int,
    subscription_type: str,
    contract_length: str,
    total_spend: float,
    last_interaction: int,
) -> tuple[str, float, str]:
    payload: dict[str, Any] = {
        "Age": int(age),
        "Gender": gender,
        "Tenure": int(tenure),
        "Usage_Frequency": int(usage_frequency),
        "Support_Calls": int(support_calls),
        "Payment_Delay": int(payment_delay),
        "Subscription_Type": subscription_type,
        "Contract_Length": contract_length,
        "Total_Spend": float(total_spend),
        "Last_Interaction": int(last_interaction),
    }

    response = requests.post(API_URL, json=payload, timeout=30)
    response.raise_for_status()
    data = response.json()

    prediction = int(data.get("churn_prediction", 0))
    label = "Churn" if prediction == 1 else "No Churn"
    probability = float(data.get("churn_probability", 0.0))
    model_uri = str(data.get("model_uri", "unknown"))
    return label, probability, model_uri


def _health() -> str:
    try:
        response = requests.get(HEALTH_URL, timeout=15)
        response.raise_for_status()
        return str(response.json())
    except Exception as exc:
        return f"Health check failed: {exc}"


with gr.Blocks(title="Churn Prediction - Gradio") as demo:
    gr.Markdown("# Customer Churn Prediction (Gradio)")
    gr.Markdown("Chon thong tin khach hang, bam Predict de du doan churn tu model production.")

    with gr.Row():
        with gr.Column():
            age = gr.Slider(minimum=18, maximum=100, value=35, step=1, label="Age")
            gender = gr.Dropdown(choices=["Male", "Female"], value="Male", label="Gender")
            tenure = gr.Number(value=12, precision=0, label="Tenure")
            usage_frequency = gr.Number(value=10, precision=0, label="Usage Frequency")
            support_calls = gr.Number(value=1, precision=0, label="Support Calls")

        with gr.Column():
            payment_delay = gr.Number(value=0, precision=0, label="Payment Delay")
            subscription_type = gr.Dropdown(
                choices=["Basic", "Standard", "Premium"],
                value="Standard",
                label="Subscription Type",
            )
            contract_length = gr.Dropdown(
                choices=["Monthly", "Quarterly", "Annual"],
                value="Monthly",
                label="Contract Length",
            )
            total_spend = gr.Number(value=250.0, precision=2, label="Total Spend")
            last_interaction = gr.Number(value=7, precision=0, label="Last Interaction")

    with gr.Row():
        predict_btn = gr.Button("Predict", variant="primary")
        health_btn = gr.Button("Check API Health")

    with gr.Row():
        churn_label = gr.Textbox(label="Prediction")
        churn_probability = gr.Number(label="Churn Probability")
        model_uri = gr.Textbox(label="Model URI")

    health_output = gr.Textbox(label="API Health")

    predict_btn.click(
        fn=_predict,
        inputs=[
            age,
            gender,
            tenure,
            usage_frequency,
            support_calls,
            payment_delay,
            subscription_type,
            contract_length,
            total_spend,
            last_interaction,
        ],
        outputs=[churn_label, churn_probability, model_uri],
    )

    health_btn.click(fn=_health, inputs=[], outputs=[health_output])


if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860)
