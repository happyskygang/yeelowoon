"""FastAPI backend for drum2midi web service."""
import asyncio
import json
import os
import shutil
import tempfile
import uuid
import zipfile
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

# Configuration from environment
WORK_DIR = Path(os.getenv("WORK_DIR", "/tmp/drum2midi-jobs"))
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:8080").split(",")
MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", 50 * 1024 * 1024))  # 50MB default

# Ensure work directory exists
WORK_DIR.mkdir(parents=True, exist_ok=True)

# Process pool for CPU-bound work
executor = ProcessPoolExecutor(max_workers=2)

app = FastAPI(
    title="drum2midi API",
    description="Drum WAV separation and MIDI extraction API",
    version="0.2.0",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class JobStatus(BaseModel):
    """Job status response."""
    job_id: str
    status: str  # "pending", "processing", "completed", "failed"
    created_at: str
    completed_at: Optional[str] = None
    error: Optional[str] = None
    result: Optional[dict] = None


# In-memory job store (use Redis/DB for production)
jobs: dict[str, dict] = {}


def process_audio_sync(job_id: str, input_path: str, output_dir: str, options: dict) -> dict:
    """Synchronous audio processing (runs in process pool)."""
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))

    from engine.pipeline import process_drum_audio
    from engine.separation import SeparationConfig

    sep_config = SeparationConfig(
        method=options.get("sep_backend", "bandpass"),
        quality=options.get("sep_quality", "balanced"),
    )

    result = process_drum_audio(
        input_path=input_path,
        output_dir=output_dir,
        stems=options.get("stems", ["kick", "snare", "hihat"]),
        bpm=options.get("bpm", "auto"),
        quantize=options.get("quantize", 0.0),
        sep_config=sep_config,
    )

    return result


async def process_job(job_id: str, input_path: Path, options: dict):
    """Process a job asynchronously."""
    job_dir = WORK_DIR / job_id
    output_dir = job_dir / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        jobs[job_id]["status"] = "processing"

        # Run CPU-bound work in process pool
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            executor,
            process_audio_sync,
            job_id,
            str(input_path),
            str(output_dir),
            options,
        )

        # Create ZIP file
        zip_path = job_dir / "result.zip"
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            # Add stems
            stems_dir = output_dir / "stems"
            if stems_dir.exists():
                for stem_file in stems_dir.glob("*.wav"):
                    zf.write(stem_file, f"stems/{stem_file.name}")

            # Add MIDI
            midi_file = output_dir / "drums.mid"
            if midi_file.exists():
                zf.write(midi_file, "drums.mid")

            # Add report
            report_file = output_dir / "report.json"
            if report_file.exists():
                zf.write(report_file, "report.json")

        jobs[job_id]["status"] = "completed"
        jobs[job_id]["completed_at"] = datetime.utcnow().isoformat()
        jobs[job_id]["result"] = result

    except Exception as e:
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = str(e)
        jobs[job_id]["completed_at"] = datetime.utcnow().isoformat()


@app.get("/healthz")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "version": "0.2.0"}


@app.post("/api/jobs", response_model=JobStatus)
async def create_job(
    file: UploadFile = File(...),
    stems: str = Form("kick,snare,hihat"),
    bpm: str = Form("auto"),
    sep_backend: str = Form("bandpass"),
    sep_quality: str = Form("balanced"),
    quantize: float = Form(0.0),
):
    """Create a new processing job."""
    # Validate file type
    if not file.filename.lower().endswith((".wav", ".wave")):
        raise HTTPException(status_code=400, detail="Only WAV files are accepted")

    # Check file size
    file.file.seek(0, 2)
    size = file.file.tell()
    file.file.seek(0)

    if size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size is {MAX_FILE_SIZE // (1024*1024)}MB"
        )

    # Create job
    job_id = str(uuid.uuid4())
    job_dir = WORK_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    # Save uploaded file
    input_path = job_dir / "input.wav"
    with open(input_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # Parse options
    stems_list = [s.strip() for s in stems.split(",") if s.strip()]
    bpm_value = "auto" if bpm.lower() == "auto" else bpm

    options = {
        "stems": stems_list,
        "bpm": bpm_value,
        "sep_backend": sep_backend,
        "sep_quality": sep_quality,
        "quantize": quantize,
    }

    # Initialize job status
    jobs[job_id] = {
        "job_id": job_id,
        "status": "pending",
        "created_at": datetime.utcnow().isoformat(),
        "completed_at": None,
        "error": None,
        "result": None,
    }

    # Start processing in background
    asyncio.create_task(process_job(job_id, input_path, options))

    return JobStatus(**jobs[job_id])


@app.get("/api/jobs/{job_id}", response_model=JobStatus)
async def get_job(job_id: str):
    """Get job status."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    return JobStatus(**jobs[job_id])


@app.get("/api/jobs/{job_id}/download")
async def download_job(job_id: str):
    """Download job result as ZIP."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job = jobs[job_id]
    if job["status"] != "completed":
        raise HTTPException(status_code=400, detail=f"Job is {job['status']}, not completed")

    zip_path = WORK_DIR / job_id / "result.zip"
    if not zip_path.exists():
        raise HTTPException(status_code=404, detail="Result file not found")

    return FileResponse(
        zip_path,
        media_type="application/zip",
        filename=f"drum2midi-{job_id[:8]}.zip",
    )


@app.on_event("shutdown")
def shutdown_event():
    """Cleanup on shutdown."""
    executor.shutdown(wait=False)


if __name__ == "__main__":
    import uvicorn

    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8001"))

    uvicorn.run(app, host=host, port=port)
