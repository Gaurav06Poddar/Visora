import os
import json
from datetime import date
from typing import List

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from . import models, schemas, crud
from .database import engine, get_db
from .langgraph_worker import run_analyzer_task

# Initialize DB
models.Base.metadata.create_all(bind=engine)

# App
app = FastAPI()

# CORS config
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Replace with specific origin in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Folder paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ANALYZER_DIR = os.path.join(BASE_DIR, "..", "analyzers")
os.makedirs(ANALYZER_DIR, exist_ok=True)

# Mount static files
app.mount(
    "/analyzers",
    StaticFiles(directory=ANALYZER_DIR),
    name="analyzers"
)

# === API Endpoints ===

@app.get("/api/analyzers/", response_model=List[schemas.AnalyzerOut])
def get_analyzers(db: Session = Depends(get_db)):
    return crud.get_all_analyzers(db)

@app.post("/api/analyzers/", response_model=schemas.AnalyzerOut)
def create_analyzer(analyzer: schemas.AnalyzerCreate, db: Session = Depends(get_db)):
    db_analyzer = crud.create_analyzer(db, analyzer)

    # Create folder structure: analyzers/{id}/minutes, reports/{date}, summaries/{date}
    analyzer_path = os.path.join(ANALYZER_DIR, str(db_analyzer.id))
    os.makedirs(os.path.join(analyzer_path, "minutes"), exist_ok=True)
    os.makedirs(os.path.join(analyzer_path, "processed"), exist_ok=True)
    os.makedirs(os.path.join(analyzer_path, "reports", str(date.today())), exist_ok=True)
    os.makedirs(os.path.join(analyzer_path, "summaries", str(date.today())), exist_ok=True)

    # Start analyzer stream capture + processing
    run_analyzer_task(db_analyzer)

    return db_analyzer

@app.put("/api/analyzers/{analyzer_id}", response_model=schemas.AnalyzerOut)
def update_analyzer(analyzer_id: int, analyzer: schemas.AnalyzerCreate, db: Session = Depends(get_db)):
    return crud.update_analyzer(db, analyzer_id, analyzer)

@app.delete("/api/analyzers/{analyzer_id}")
def delete_analyzer(analyzer_id: int, db: Session = Depends(get_db)):
    crud.delete_analyzer(db, analyzer_id)
    return {"message": "Analyzer deleted"}

@app.get("/api/analyzers/{analyzer_id}/stream")
def get_stream_video(analyzer_id: int):
    minutes_dir = os.path.join(ANALYZER_DIR, str(analyzer_id), "minutes")
    video_files = sorted([
        f for f in os.listdir(minutes_dir)
        if f.endswith(".mp4")
    ], reverse=True)

    if not video_files:
        raise HTTPException(status_code=404, detail="No video found")

    latest_video_path = os.path.join(minutes_dir, video_files[0])
    return FileResponse(latest_video_path, media_type="video/mp4")

@app.get("/api/analyzers/{analyzer_id}/report-files")
def list_report_files(analyzer_id: int):
    report_dir = os.path.join(ANALYZER_DIR, str(analyzer_id), "reports", str(date.today()))
    if not os.path.exists(report_dir):
        return []
    return os.listdir(report_dir)

@app.get("/api/analyzers/{analyzer_id}/reports/{report_file}")
def get_report(analyzer_id: int, report_file: str):
    report_path = os.path.join(ANALYZER_DIR, str(analyzer_id), "reports", str(date.today()), report_file)
    if not os.path.exists(report_path):
        raise HTTPException(status_code=404, detail="Report not found")
    with open(report_path, "r") as f:
        return json.load(f)



@app.get("/api/analyzers/{id}/summary-files")
def list_summary_files(id: int):
    dir = f"analyzers/{id}/summaries/{date.today()}"
    return os.listdir(dir) if os.path.exists(dir) else []

@app.get("/api/analyzers/{id}/summaries/{file}")
def get_summary(id: int, file: str):
    path = f"analyzers/{id}/summaries/{date.today()}/{file}"
    if not os.path.exists(path):
        raise HTTPException(404, "Not found")
    with open(path, "r") as f:
        return json.load(f)

@app.get("/api/analyzers/{id}/summary-files")
def list_summary_files(id: int):
    dir = f"analyzers/{id}/summaries/{date.today()}"
    return os.listdir(dir) if os.path.exists(dir) else []


'''
@app.get("/api/analyzers/{analyzer_id}/summary-files")
def list_summary_files(analyzer_id: int):
    summary_path = os.path.join(ANALYZER_DIR, str(analyzer_id), "summaries", str(date.today()))
    if not os.path.exists(summary_path):
        return []

    files = []
    for root, _, filenames in os.walk(summary_path):
        for fname in filenames:
            if fname.endswith(".txt"):
                relative_path = os.path.relpath(os.path.join(root, fname), summary_path)
                files.append(relative_path.replace("\\", "/"))

    return files

@app.get("/api/analyzers/{analyzer_id}/summaries/{summary_file}")
def get_summary(analyzer_id: int, summary_file: str):
    summary_path = os.path.join(ANALYZER_DIR, str(analyzer_id), "summaries", str(date.today()), summary_file)
    if not os.path.exists(summary_path):
        raise HTTPException(status_code=404, detail="Summary not found")
    return FileResponse(summary_path, media_type="text/plain")
'''