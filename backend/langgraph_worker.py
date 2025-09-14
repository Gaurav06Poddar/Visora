import os
import cv2
import base64
import time
import threading
import shutil
from datetime import datetime
from .langgraph_builder import langgraph
from .models import Analyzer

def run_analyzer_task(analyzer: Analyzer):
    analyzer_id = analyzer.id
    stream_url = analyzer.stream_url
    schema_fields = analyzer.schema_fields

    base_path = f"analyzers/{analyzer_id}"
    MINUTES_FOLDER = os.path.join(base_path, "minutes")
    PROCESSED_FOLDER = os.path.join(base_path, "processed")
    os.makedirs(MINUTES_FOLDER, exist_ok=True)
    os.makedirs(PROCESSED_FOLDER, exist_ok=True)

    def capture_video():
        cap = cv2.VideoCapture(stream_url)
        if not cap.isOpened():
            print(f"[ERROR] Unable to open stream for analyzer {analyzer_id}")
            return

        fps = int(cap.get(cv2.CAP_PROP_FPS)) or 25
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')

        while True:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = os.path.join(MINUTES_FOLDER, f"{timestamp}.mp4")
            out = cv2.VideoWriter(filename, fourcc, fps, (width, height))

            frame_count = 0
            while frame_count < fps * 15:
                ret, frame = cap.read()
                if not ret:
                    print("[ERROR] Frame capture failed. Reinitializing...")
                    cap.release()
                    time.sleep(3)
                    cap = cv2.VideoCapture(stream_url)
                    break
                out.write(frame)
                frame_count += 1

            out.release()
            print(f"[CAPTURED] Saved: {filename}")
            time.sleep(1)

    def process_videos():
        while True:
            videos = [f for f in os.listdir(MINUTES_FOLDER) if f.endswith(".mp4")]
            if not videos:
                time.sleep(5)
                continue

            videos.sort()
            next_video = videos[0]
            video_path = os.path.join(MINUTES_FOLDER, next_video)

            try:
                with open(video_path, "rb") as f:
                    video_data = base64.b64encode(f.read()).decode("utf-8")

                context = {
                    "analyzer_id": analyzer_id,
                    "expected_fields": schema_fields,
                    "video_data": video_data,
                    "report": {}
                }

                langgraph.invoke(context)
                shutil.move(video_path, os.path.join(PROCESSED_FOLDER, next_video))
                print(f"[PROCESSED ✅] {next_video}")
            except Exception as e:
                print(f"[ERROR] Processing {next_video}: {e}")
                time.sleep(5)

    threading.Thread(target=capture_video, daemon=True).start()
    threading.Thread(target=process_videos, daemon=True).start()

    print(f"[✅ STARTED] Analyzer {analyzer_id} ({analyzer.name}) is running.")
