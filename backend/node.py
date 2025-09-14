import os
import json
import base64
from datetime import datetime
from typing import Dict, Any
from langchain_core.messages import HumanMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_google_genai import ChatGoogleGenerativeAI
import re
import os

GEMINI_API_KEY = os.getenv("GOOGLE_API_KEY")


# --- Setup required folders ---
os.makedirs("reports", exist_ok=True)
os.makedirs("summaries", exist_ok=True)

# --- Prompt Generator ---
def generate_prompt(schema_fields: list[str]) -> str:
    return (
        f"You are analyzing CCTV footage from a factory.\n"
        f"The video contains observable activity.\n"
        f"Based on the provided schema fields below:\n\n"
        f"{json.dumps(schema_fields, indent=2)}\n\n"
        f"Your task is to return a JSON dictionary mapping each field to an appropriate value.\n"
        f"If something is not visible, respond with 'N/A'.\n"
        f"Only return the dictionary, nothing else."
    )

# --- Identify Node: extract info from video using Gemini ---
def identify_node(state: Dict[str, Any]) -> Dict[str, Any]:
    video_data = state["video_data"]
    schema_fields = state["expected_fields"]

    llm = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash",
        google_api_key=GEMINI_API_KEY,
        temperature=0
    )

    prompt = generate_prompt(schema_fields)
    message = HumanMessage(
        content=[
            {"type": "text", "text": prompt},
            {"type": "media", "data": video_data, "mime_type": "video/mp4"}
        ]
    )

    try:
        result = llm.invoke([message])
        content = result.content.strip().strip("```").lstrip("json").strip()
        parsed = json.loads(content) if content.startswith("{") else eval(content)
    except Exception as e:
        parsed = {"error": "Failed to parse LLM response", "raw": str(result.content), "exception": str(e)}

    state["report"] = parsed
    return state

# --- Check Node: validate fields ---
def check_node(state: dict, config: dict = None) -> dict:
    report = state.get("report", {})
    expected_fields = state.get("expected_fields", [])

    missing_fields = [
        field for field in expected_fields
        if field not in report or str(report[field]).strip().upper() in ["N/A", "", "NONE"]
    ]

    if missing_fields:
        print(f"[CHECK ❌] Missing: {missing_fields}")
        return {"report_valid": False, "missing_fields": missing_fields}
    else:
        print("[CHECK ✅] All fields present.")
        return {"report_valid": True, "validated_report": report}

# --- Publish Node: save minute report ---
def publish_node(state: dict, config: dict = None) -> dict:
    report = state["report"]
    analyzer_id = state["analyzer_id"]  # <-- Add this to your GraphState and make sure it's passed
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H-%M-%S")

    folder_path = os.path.join("analyzers", str(analyzer_id), "reports", date_str)
    os.makedirs(folder_path, exist_ok=True)

    filename = f"minute_{time_str}.json"
    file_path = os.path.join(folder_path, filename)

    with open(file_path, "w") as f:
        json.dump(report, f, indent=2)

    print(f"[PUBLISH ✅] Saved: {file_path}")
    return {"published": True}


# --- Concat Node: generate hourly and daily summaries ---

def concat_node(state: dict, config: dict = None) -> dict:
    analyzer_id = state["analyzer_id"]
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")

    root = "analyzers"
    reports_dir = os.path.join(root, str(analyzer_id), "reports", date_str)
    summaries_dir = os.path.join(root, str(analyzer_id), "summaries", date_str)
    os.makedirs(summaries_dir, exist_ok=True)

    llm = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash",
        google_api_key=GEMINI_API_KEY,
        temperature=0
    )

    minute_files = sorted([
        f for f in os.listdir(reports_dir) if f.startswith("minute_") and f.endswith(".json")
    ])
    n = len(minute_files)
    output = {}

    # Hourly Summary
    if n and n % 6 == 0:
        last_60 = minute_files[-2:]
        data = [json.load(open(os.path.join(reports_dir, f))) for f in last_60]
        prompt = f"""You are an analytics assistant. Here's 6 JSON reports each collected for a 10 minute long interval for one hour:  
        {json.dumps(data, indent=2)} 
        Based on the reports provided, your task is to return a JSON dictionary mapping each of the following schema fields to appropriate data (Make sure that the data is only text): overview, notable_events_and_patterns and anomolies.
        Only return the dictionary, nothing else.
        """
        summary_str = (llm | StrOutputParser()).invoke(prompt)
        print(summary_str)  # Optional: for debugging
        cleaned = re.sub(r"^```(?:json)?\n", "", summary_str.strip())
        cleaned = re.sub(r"\n```$", "", cleaned)

        # Safely parse to dict
        try:
            summary_json = json.loads(cleaned)
        except Exception as e:
            print("[ERROR] Failed to parse LLM summary output:", e)
            summary_json = {"error": "Malformed summary", "raw": summary_str}

        idx = len([f for f in os.listdir(summaries_dir) if f.startswith("hourly_")]) + 1
        path = os.path.join(summaries_dir, f"hourly_{idx:02d}.json")
        with open(path, "w") as f:
            json.dump(summary_json, f, indent=2)
        print(f"[HOURLY ✅] Saved {path}")
        output["hourly_summary_file"] = os.path.basename(path)

    # Daily Summary
    if n and n % 12 == 0:
        data = [json.load(open(os.path.join(reports_dir, f))) for f in minute_files]
        prompt = f"""You are an intelligence analyst. Below is a full day of JSON reports:  
        {json.dumps(data, indent=2)} 
        Based on the reports provided, your task is to return a JSON dictionary mapping each of the following schema fields to appropriate data (Make sure that the data is only text): full_day_summary, issues and trends_and_recommendations.
        Only return the dictionary, nothing else.
        """
        summary_str = (llm | StrOutputParser()).invoke(prompt)
        cleaned = re.sub(r"^```(?:json)?\n", "", summary_str.strip())
        cleaned = re.sub(r"\n```$", "", cleaned)

        # Safely parse to dict
        try:
            summary_json = json.loads(cleaned)
        except Exception as e:
            print("[ERROR] Failed to parse LLM summary output:", e)
            summary_json = {"error": "Malformed summary", "raw": summary_str}

        path = os.path.join(summaries_dir, "daily_summary.json")
        with open(path, "w") as f:
            json.dump(summary_json, f, indent=2)
        print(f"[DAILY ✅] Saved {path}")
        output["daily_summary_file"] = os.path.basename(path)

    return output


'''
def concat_node(state: dict, config: dict = None) -> dict:
    analyzer_id = state["analyzer_id"]
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")

    root = "analyzers"
    reports_dir = os.path.join(root, str(analyzer_id), "reports", date_str)
    summaries_dir = os.path.join(root, str(analyzer_id), "summaries", date_str)
    os.makedirs(summaries_dir, exist_ok=True)

    llm = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash",
        google_api_key=GEMINI_API_KEY,
        temperature=0
    )

    minute_files = sorted([
        f for f in os.listdir(reports_dir) if f.startswith("minute_") and f.endswith(".json")
    ])
    n = len(minute_files)
    output = {}

    # Hourly Summary
    if n and n % 2 == 0:
        last_60 = minute_files[-2:]
        data = [json.load(open(os.path.join(reports_dir, f))) for f in last_60]
        prompt = f"""You are an analytics assistant. Here's 2 JSON reports each collected for 30 minutes for one hour: 
        {json.dumps(data, indent=2)} 
        Based on the reports provided, your task is to return a JSON dictionary mapping each of the following schema fields to appropriate data (Make sure that the data is only text): overview, notable_events_and_patterns and anomolies.
        Only return the dictionary, nothing else.
        """
        summary_str = (llm | StrOutputParser()).invoke(prompt)
        print(summary_str)
        
        try:
            summary_json = json.loads(summary_str)
        except json.JSONDecodeError:
            print("[ERROR ❌] Gemini did not return valid JSON for hourly summary.")
            return output
        
        idx = len([f for f in os.listdir(summaries_dir) if f.startswith("hourly_")]) + 1
        path = os.path.join(summaries_dir, f"hourly_{idx:02d}.json")
        with open(path, "w") as f:
            json.dump(summary_json, f, indent=2)
        print(f"[HOURLY ✅] Saved {path}")
        output["hourly_summary_file"] = os.path.basename(path)

    # Daily Summary
    if n == 6:
        data = [json.load(open(os.path.join(reports_dir, f))) for f in minute_files]
        prompt = f"""
You are an intelligence analyst. Below is a full day of six hour - by - six hour JSON reports: 
{json.dumps(data, indent=2)}
ONLY return a valid JSON object with:
- "day_summary": A full-day summary
- "issues": Any issues detected
- "trends_and_recommendations": Key trends and recommendations
In writing the full day summary, any issues detected and key trends and recommendations make sure that you only use valid text, don't use lists or any other objects.
"""
        summary_str = (llm | StrOutputParser()).invoke(prompt)

        try:
            summary_json = json.loads(summary_str)
        except json.JSONDecodeError:
            print("[ERROR ❌] Gemini did not return valid JSON for daily summary.")
            return output

        path = os.path.join(summaries_dir, "daily_summary.json")
        with open(path, "w") as f:
            json.dump(summary_json, f, indent=2)
        print(f"[DAILY ✅] Saved {path}")
        output["daily_summary_file"] = os.path.basename(path)

    return output

'''

'''

def concat_node(state: dict, config: dict = None) -> dict:
    analyzer_id = state["analyzer_id"]
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")

    root = "analyzers"
    reports_dir = os.path.join(root, str(analyzer_id), "reports", date_str)
    summaries_dir = os.path.join(root, str(analyzer_id), "summaries", date_str)
    os.makedirs(summaries_dir, exist_ok=True)

    llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",
            google_api_key=GEMINI_API_KEY,
            temperature=0
        )

    minute_files = sorted([
        f for f in os.listdir(reports_dir) if f.startswith("minute_") and f.endswith(".json")
    ])
    n = len(minute_files)
    output = {}

    # Hourly Summary
    if n and n % 10 == 0:
        last_60 = minute_files[-10:]
        data = [json.load(open(os.path.join(reports_dir, f))) for f in last_60]
        prompt = f"""You are an analytics assistant. Here's a list of 10 JSON reports collected for 6 minutes each for one hour:
        {json.dumps(data, indent=2)} 
        ONLY return a valid JSON object with:
        - "overview": a brief overview
        - "notable_events": key events or patterns
        - "anomalies": Any anomalies or operational issues
        """
        summary = (llm | StrOutputParser()).invoke(prompt)

        idx = len([f for f in os.listdir(summaries_dir) if f.startswith("hourly_")]) + 1
        path = os.path.join(summaries_dir, f"hourly_{idx:02d}.json")
        with open(path, "w") as f: f.write(summary)
        print(f"[HOURLY ✅] Saved {path}")
        output["hourly_summary_file"] = os.path.basename(path)

    # Daily Summary
    if n == 20:
        data = [json.load(open(os.path.join(reports_dir, f))) for f in minute_files]
        prompt = f"""
        You are a intelligence analyst. Below is a full day of six minute - by - six minute JSON reports:
        {json.dumps(data, indent=2)}
        ONLY return a valid JSON object with:
        - "day_summary": A full-day summary
        - "issues": Any issues detected
        - "trends_and_recommendations": Key trends and recommendations
        """
        summary = (llm | StrOutputParser()).invoke(prompt)
        path = os.path.join(summaries_dir, "daily_summary.json")
        with open(path, "w") as f: f.write(summary)
        print(f"[DAILY ✅] Saved {path}")
        output["daily_summary_file"] = os.path.basename(path)

    return output


def concat_node(state: dict, config: dict = None) -> dict:
    analyzer_id = state["analyzer_id"]
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")

    folder_path = os.path.join("analyzers", str(analyzer_id), "reports", date_str)
    summary_path = os.path.join("analyzers", str(analyzer_id), "summaries", date_str)
    os.makedirs(summary_path, exist_ok=True)

    llm = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash",
        google_api_key=GEMINI_API_KEY,
        temperature=0
    )

    minute_reports = [
        os.path.join(folder_path, f)
        for f in os.listdir(folder_path)
        if f.startswith("minute_") and f.endswith(".json")
    ]
    minute_reports.sort()
    output = {}

    # --- Hourly Summary ---
    if len(minute_reports) % 60 == 0:
        hourly_data = []
        for f in minute_reports[-60:]:
            with open(f, "r") as rf:
                hourly_data.append(json.load(rf))

        prompt = f"""
        You are an analytics assistant. Here's a list of 60 JSON reports collected each minute for one hour:
        {json.dumps(hourly_data, indent=2)}

        Generate a JSON summary with:
        - Brief overview
        - Notable events or patterns
        - Any anomalies or operational issues
        """
        summary = (llm | StrOutputParser()).invoke(prompt)
        index = len([f for f in os.listdir(summary_path) if f.startswith("hourly_")]) + 1
        hourly_file = os.path.join(summary_path, f"hourly_{index:02d}.txt")
        with open(hourly_file, "w") as f:
            f.write(summary)
        print(f"[HOURLY ✅] {hourly_file}")
        output["hourly_summary"] = summary

    # --- Daily Summary ---
    if len(minute_reports) == 1440:
        daily_data = []
        for f in minute_reports:
            with open(f, "r") as rf:
                daily_data.append(json.load(rf))

        prompt = f"""
        You are a factory intelligence analyst. Below is a full day of minute-by-minute JSON reports:
        {json.dumps(daily_data, indent=2)}

        Generate a JSON summary that includes:
        - A full-day summary
        - Any issues detected
        - Key trends and recommendations
        """
        summary = (llm | StrOutputParser()).invoke(prompt)
        with open(os.path.join(summary_path, "daily_summary.txt"), "w") as f:
            f.write(summary)
        print("[DAILY ✅] Saved daily_summary.txt")
        output["daily_summary"] = summary

    return output
'''