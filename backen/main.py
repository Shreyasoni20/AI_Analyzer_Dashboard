from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from langdetect import detect
import pandas as pd

app = FastAPI()

# -----------------------------
# Enable CORS
# -----------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------
# Load Dataset
# -----------------------------

df = pd.read_csv("Customer_Behaviour.csv")

class Prompt(BaseModel):
    prompt: str


# =============================
# AI DASHBOARD GENERATION
# =============================

@app.post("/generate")
def generate_dashboard(data: Prompt):

    prompt = data.prompt.lower()

    try:
        language = detect(prompt)
    except:
        language = "en"

    charts = []
    insight = ""

    # Internet Usage Chart
    if "internet" in prompt:

        internet_data = df.groupby("daily_internet_hours")[
            "avg_online_spend"
        ].mean().reset_index()

        charts.append({
            "id": "1",
            "title": "Internet Usage vs Online Spending",
            "type": "line",
            "data": [
                {
                    "name": str(row["daily_internet_hours"]),
                    "value": float(row["avg_online_spend"])
                }
                for _, row in internet_data.iterrows()
            ]
        })

        insight = "Higher internet usage often leads to more online spending."


    # City Tier Spending
    elif "city" in prompt:

        city_data = df.groupby("city_tier")[
            "avg_online_spend"
        ].mean().reset_index()

        charts.append({
            "id": "2",
            "title": "Spending by City Tier",
            "type": "bar",
            "data": [
                {
                    "name": str(row["city_tier"]),
                    "value": float(row["avg_online_spend"])
                }
                for _, row in city_data.iterrows()
            ]
        })

        insight = "Customers from higher city tiers spend more."


    # Shopping Preference Pie Chart
    elif "shopping" in prompt or "preference" in prompt:

        pref_data = df["shopping_preference"].value_counts().reset_index()
        pref_data.columns = ["shopping_preference", "count"]

        charts.append({
            "id": "3",
            "title": "Shopping Preference Distribution",
            "type": "pie",
            "data": [
                {
                    "name": row["shopping_preference"],
                    "value": int(row["count"])
                }
                for _, row in pref_data.iterrows()
            ]
        })

        insight = "This pie chart shows customer shopping preferences."


    # Default Chart
    else:

        charts.append({
            "id": "4",
            "title": "Online vs Store Spending",
            "type": "bar",
            "data": [
                {"name": "Online", "value": float(df["avg_online_spend"].mean())},
                {"name": "Store", "value": float(df["avg_store_spend"].mean())}
            ]
        })

        insight = "Comparison of online vs store spending."

    return {
        "language": language,
        "insight": insight,
        "charts": charts
    }


# =============================
# EXECUTIVE DASHBOARD KPIs
# =============================

@app.get("/kpis")
def get_kpis():

    total_online = df["avg_online_spend"].sum()
    total_store = df["avg_store_spend"].sum()

    total_revenue = total_online + total_store

    avg_orders = df["monthly_online_orders"].mean()

    return_freq = df["return_frequency"].mean()

    efficiency = 100 - (return_freq * 10)

    return {
        "revenue": round(total_revenue, 2),
        "orders": round(avg_orders, 2),
        "returns": round(return_freq, 2),
        "efficiency": round(efficiency, 2)
    }


# =============================
# SALES DASHBOARD KPIs
# =============================

@app.get("/sales-kpis")
def sales_kpis():

    total_revenue = df["avg_online_spend"].sum() + df["avg_store_spend"].sum()

    avg_deal_size = df["avg_online_spend"].mean()

    conversion_rate = (
        df["monthly_online_orders"].sum() /
        (df["monthly_online_orders"].sum() + df["monthly_store_visits"].sum())
    ) * 100

    pipeline_velocity = avg_deal_size * 8

    win_rate = 100 - (df["return_frequency"].mean() * 10)

    open_deals = int(df["monthly_online_orders"].sum())

    return {
        "total_revenue": round(total_revenue, 2),
        "avg_deal_size": round(avg_deal_size, 2),
        "conversion_rate": round(conversion_rate, 2),
        "pipeline_velocity": round(pipeline_velocity, 2),
        "win_rate": round(win_rate, 2),
        "open_deals": open_deals
    }
