#!/usr/bin/env python3
"""
Convert PKL files in data folder to JSONL format

Usage:
    python scripts/pkl_to_jsonl.py                          # All projects
    python scripts/pkl_to_jsonl.py --project data/video_001 # Single project
    python scripts/pkl_to_jsonl.py --output exports/        # Custom output dir
"""

import argparse
import json
import pickle
from pathlib import Path
import numpy as np


def numpy_to_python(obj):
    """Recursively convert numpy types to Python native types"""
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.bool_):
        return bool(obj)
    elif isinstance(obj, dict):
        return {k: numpy_to_python(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [numpy_to_python(item) for item in obj]
    elif isinstance(obj, bytes):
        return obj.decode('utf-8', errors='replace')
    else:
        return obj


def get_shape_info(obj, depth=0, max_depth=3):
    """Get shape/type information for summarizing data structure"""
    if depth > max_depth:
        return "..."
    
    if isinstance(obj, np.ndarray):
        return f"array{list(obj.shape)} ({obj.dtype})"
    elif isinstance(obj, (list, tuple)):
        if len(obj) == 0:
            return "[]"
        # Check if it's a nested array-like structure
        first = obj[0]
        if isinstance(first, (list, np.ndarray)):
            inner = get_shape_info(first, depth + 1, max_depth)
            return f"[{len(obj)}x {inner}]"
        elif isinstance(first, dict):
            return f"[{len(obj)} dicts]"
        else:
            return f"[{len(obj)} items]"
    elif isinstance(obj, dict):
        return {k: get_shape_info(v, depth + 1, max_depth) for k, v in obj.items()}
    elif isinstance(obj, str):
        if len(obj) > 50:
            return f"str({len(obj)} chars)"
        return f'"{obj}"'
    elif isinstance(obj, (int, float)):
        return obj
    elif obj is None:
        return None
    else:
        return type(obj).__name__


def create_summary(data, source_file: str):
    """Create a summary/metadata section for the JSON output"""
    from datetime import datetime
    
    summary = {
        "_meta": {
            "source_file": source_file,
            "converted_at": datetime.now().isoformat(),
            "format": "Converted from PKL to JSON",
        },
        "_schema": get_shape_info(data),
    }
    
    # Add top-level keys info
    if isinstance(data, dict):
        summary["_keys"] = list(data.keys())
    
    return summary


def pkl_to_jsonl(pkl_path: Path, output_path: Path, include_summary: bool = True):
    """Convert a single PKL file to JSON with optional summary header"""
    # Try pickle first, then joblib
    try:
        with open(pkl_path, 'rb') as f:
            data = pickle.load(f)
    except Exception:
        try:
            import joblib
            data = joblib.load(pkl_path)
        except ImportError:
            raise ImportError("Install joblib: pip install joblib")
    
    # Create output structure
    if include_summary:
        summary = create_summary(data, pkl_path.name)
        output_data = {
            **summary,
            "data": numpy_to_python(data),
        }
    else:
        output_data = numpy_to_python(data)
    
    # Write as JSON
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    return output_path


def process_project(project_dir: Path, output_dir: Path = None, include_summary: bool = True):
    """Process all PKL files in a project directory"""
    project_dir = Path(project_dir)
    
    if output_dir is None:
        output_dir = project_dir
    else:
        output_dir = Path(output_dir) / project_dir.name
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    pkl_files = list(project_dir.glob("*.pkl"))
    
    if not pkl_files:
        print(f"[{project_dir.name}] No PKL files found")
        return []
    
    converted = []
    for pkl_path in pkl_files:
        jsonl_name = pkl_path.stem + ".json"
        output_path = output_dir / jsonl_name
        
        try:
            pkl_to_jsonl(pkl_path, output_path, include_summary=include_summary)
            size_kb = output_path.stat().st_size / 1024
            print(f"  {pkl_path.name} → {jsonl_name} ({size_kb:.1f} KB)")
            converted.append(output_path)
        except Exception as e:
            print(f"  {pkl_path.name} → ERROR: {e}")
    
    return converted


def main():
    parser = argparse.ArgumentParser(description="Convert PKL files to JSON format")
    parser.add_argument("--project", "-p", help="Single project folder (e.g., data/video_001)")
    parser.add_argument("--output", "-o", help="Output directory (default: same as source)")
    parser.add_argument("--data-dir", default="data", help="Data directory (default: data)")
    parser.add_argument("--no-summary", action="store_true", help="Skip summary/metadata header")
    
    args = parser.parse_args()
    include_summary = not args.no_summary
    
    if args.project:
        # Single project
        project_dir = Path(args.project)
        if not project_dir.exists():
            parser.error(f"Project not found: {project_dir}")
        
        print(f"[{project_dir.name}]")
        process_project(project_dir, args.output, include_summary=include_summary)
    else:
        # All projects
        data_dir = Path(args.data_dir)
        if not data_dir.exists():
            parser.error(f"Data directory not found: {data_dir}")
        
        projects = sorted(data_dir.glob("video_*"))
        
        if not projects:
            print("No video_* projects found")
            return
        
        total_converted = 0
        for project in projects:
            print(f"[{project.name}]")
            converted = process_project(project, args.output, include_summary=include_summary)
            total_converted += len(converted)
        
        print(f"\n✅ Total: {total_converted} files converted")


if __name__ == "__main__":
    main()

