"""Pipeline event layer: brokers pipeline events to the frontend over SSE.
"""

from __future__ import annotations

import json
import queue
import threading
import uuid

from insurance_verify.pipeline import run_pipeline


class EventBroker:
    """Holds a per-job event queue so the pipeline can stream to the frontend."""

    def __init__(self) -> None:
        self._queues: dict[str, queue.Queue] = {}
        self._images: dict[str, str] = {}
        self._started: set[str] = set()
        self._lock = threading.Lock()

    def create_job(self, image_path: str) -> str:
        """Create a job and return its id. The pipeline starts on subscribe."""
        job_id = uuid.uuid4().hex
        with self._lock:
            self._queues[job_id] = queue.Queue()
            self._images[job_id] = image_path
        return job_id

    def start(self, job_id: str) -> None:
        """Start the pipeline for a job (idempotent)."""
        with self._lock:
            if job_id in self._started:
                return
            self._started.add(job_id)
            image_path = self._images.get(job_id)
        if image_path is None:
            return

        def _run() -> None:
            try:
                summary = run_pipeline(image_path, emit=lambda e: self.emit(job_id, e))
                self.emit(
                    job_id,
                    {"step": "result", "status": "done", "detail": summary.model_dump_json()},
                )
            except Exception as exc:  # noqa: BLE001 - surface any failure to the client
                self.emit(job_id, {"step": "error", "status": "error", "detail": str(exc)})
            finally:
                self.emit(job_id, {"step": "end", "status": "done", "detail": ""})

        threading.Thread(target=_run, daemon=True).start()

    def emit(self, job_id: str, event: dict) -> None:
        with self._lock:
            q = self._queues.get(job_id)
        if q is not None:
            q.put(event)

    def subscribe(self, job_id: str) -> queue.Queue | None:
        with self._lock:
            return self._queues.get(job_id)

    def close(self, job_id: str) -> None:
        with self._lock:
            self._queues.pop(job_id, None)
            self._images.pop(job_id, None)


broker = EventBroker()


def start_verification(image_path: str) -> str:
    """Convenience: create a job and start the pipeline immediately (tests)."""
    job_id = broker.create_job(image_path)
    broker.start(job_id)
    return job_id


def sse_format(event: dict) -> str:
    """Format an event dict as an SSE frame."""
    return f"data: {json.dumps(event)}\n\n"
