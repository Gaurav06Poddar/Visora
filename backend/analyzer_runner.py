import threading
from .langgraph_worker import run_analyzer_task

def start_analyzer_runner(analyzer):
    thread = threading.Thread(target=run_analyzer_task, args=(analyzer,), daemon=True)
    thread.start()
