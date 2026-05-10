"""File upload and download API."""

import shutil
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import FileResponse

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from video2robot.config import DATA_DIR

router = APIRouter()


@router.post("/upload/{project_name}")
async def upload_video(project_name: str, file: UploadFile = File(...)):
    """Upload a video file to a project."""
    project_dir = DATA_DIR / project_name
    
    if not project_dir.exists():
        project_dir.mkdir(parents=True, exist_ok=True)
    
    # Validate file type
    if not file.filename.lower().endswith((".mp4", ".mov", ".avi", ".webm")):
        raise HTTPException(status_code=400, detail="Invalid file type. Supported: mp4, mov, avi, webm")
    
    video_path = project_dir / "original.mp4"
    
    # Save file
    with open(video_path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    
    size_mb = video_path.stat().st_size / (1024 * 1024)
    
    return {
        "status": "uploaded",
        "project": project_name,
        "filename": "original.mp4",
        "size_mb": round(size_mb, 2),
    }


@router.get("/video/{project_name}")
async def get_video(project_name: str):
    """Get the video file for a project."""
    video_path = DATA_DIR / project_name / "original.mp4"
    
    if not video_path.exists():
        raise HTTPException(status_code=404, detail="Video not found")
    
    return FileResponse(
        video_path,
        media_type="video/mp4",
        filename=f"{project_name}.mp4",
    )


@router.get("/robot-motion/{project_name}")
async def get_robot_motion(project_name: str, track: int = 1, twist: bool = False):
    """Get robot motion data as JSON."""
    project_dir = DATA_DIR / project_name
    
    if not project_dir.exists():
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Find motion file
    suffix = "_twist" if twist else ""
    if track == 1:
        motion_path = project_dir / f"robot_motion{suffix}.pkl"
        if not motion_path.exists():
            motion_path = project_dir / f"robot_motion_track_1{suffix}.pkl"
    else:
        motion_path = project_dir / f"robot_motion_track_{track}{suffix}.pkl"
    
    if not motion_path.exists():
        raise HTTPException(status_code=404, detail="Robot motion not found")
    
    import pickle
    import numpy as np
    
    with open(motion_path, "rb") as f:
        motion = pickle.load(f)
    
    # Convert numpy arrays to lists for JSON
    def to_json_serializable(obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, dict):
            return {k: to_json_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [to_json_serializable(v) for v in obj]
        else:
            return obj
    
    return to_json_serializable(motion)


@router.get("/download/{project_name}/{filename}")
async def download_file(project_name: str, filename: str):
    """Download any file from a project."""
    file_path = DATA_DIR / project_name / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    # Security: prevent path traversal
    if ".." in filename or filename.startswith("/"):
        raise HTTPException(status_code=400, detail="Invalid filename")
    
    return FileResponse(file_path, filename=filename)
