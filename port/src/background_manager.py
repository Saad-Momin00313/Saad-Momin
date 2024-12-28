import threading
import time
from datetime import datetime
from typing import Dict, Any, Callable
import queue

class BackgroundManager:
    def __init__(self):
        self._stop_event = threading.Event()
        self._tasks = {}
        self._task_results = {}
        self._task_queue = queue.Queue()
        self._worker_thread = threading.Thread(target=self._worker, daemon=True)
        self._worker_thread.start()
    
    def add_task(self, name: str, func: Callable, interval: int):
        """Add a task to be executed in the background"""
        self._tasks[name] = {
            'function': func,
            'interval': interval,
            'last_run': 0
        }
    
    def get_result(self, task_name: str) -> Dict[str, Any]:
        """Get the latest result for a task"""
        return self._task_results.get(task_name)
    
    def _worker(self):
        """Background worker that executes tasks"""
        while not self._stop_event.is_set():
            current_time = time.time()
            
            # Check each task
            for name, task in self._tasks.items():
                if current_time - task['last_run'] >= task['interval']:
                    try:
                        # Execute the task
                        result = task['function']()
                        self._task_results[name] = {
                            'result': result,
                            'timestamp': current_time,
                            'status': 'success'
                        }
                    except Exception as e:
                        self._task_results[name] = {
                            'result': None,
                            'timestamp': current_time,
                            'status': 'error',
                            'error': str(e)
                        }
                    finally:
                        task['last_run'] = current_time
            
            # Sleep for a short interval
            time.sleep(1)
    
    def stop(self):
        """Stop the background worker"""
        self._stop_event.set()
        self._worker_thread.join()
    
    def is_result_fresh(self, task_name: str, max_age: int) -> bool:
        """Check if a task result is fresh enough"""
        result = self._task_results.get(task_name)
        if not result:
            return False
        
        current_time = time.time()
        return current_time - result['timestamp'] <= max_age 