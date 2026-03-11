from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from langdetect import detect
import pandas as pd

app = FastAPI()

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load dataset
df = pd.read_csv("Customer_Behaviour.csv")


class Prompt(BaseModel):
    prompt: str


@app.post("/generate")
def generate_dashboard(data: Prompt):

    prompt = data.prompt.lower()

    try:
        language = detect(prompt)
    except:
        language = "en"

    charts = []
    insight = ""

    # ------------------------------------------------
    # INTERNET USAGE vs SPENDING  → LINE CHART
    # ------------------------------------------------
    if any(word in prompt for word in [
        "internet", "online", "इंटरनेट", "internetnutzung",
        "usage", "net", "web"
    ]):

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

        insight = "Higher internet usage often leads to higher online spending."


    # ------------------------------------------------
    # CITY TIER ANALYSIS → BAR CHART
    # ------------------------------------------------
    elif any(word in prompt for word in [
        "city", "tier", "शहर", "ciudad", "stadt"
    ]):

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

        insight = "Customers from different city tiers spend differently."


    # ------------------------------------------------
    # SHOPPING PREFERENCE → PIE CHART
    # ------------------------------------------------
    elif any(word in prompt for word in [
        "preference", "shopping", "खरीदारी",
        "achat", "einkauf"
    ]):

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

        insight = "This pie chart shows customer shopping preference."


    # ------------------------------------------------
    # GENDER SPENDING → BAR CHART
    # ------------------------------------------------
    elif any(word in prompt for word in [
        "gender", "male", "female"
    ]):

        gender_data = df.groupby("gender")[
            "avg_online_spend"
        ].mean().reset_index()

        charts.append({
            "id": "4",
            "title": "Average Spending by Gender",
            "type": "bar",
            "data": [
                {
                    "name": row["gender"],
                    "value": float(row["avg_online_spend"])
                }
                for _, row in gender_data.iterrows()
            ]
        })

        insight = "Average online spending comparison between genders."


    # ------------------------------------------------
    # DEFAULT CHART → BAR
    # ------------------------------------------------
    else:

        charts.append({
            "id": "5",
            "title": "Online vs Store Spending",
            "type": "bar",
            "data": [
                {"name": "Online", "value": float(df["avg_online_spend"].mean())},
                {"name": "Store", "value": float(df["avg_store_spend"].mean())}
            ]
        })

        insight = "Default comparison of online vs store spending."

    return {
        "language": language,
        "insight": insight,
        "charts": charts
    }
