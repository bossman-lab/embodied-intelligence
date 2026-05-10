#!/usr/bin/env python3
"""
Generate video using Seedance / Google Veo / OpenAI Sora

Usage:
    # With action (uses BASE_PROMPT template for robot retargeting)
    python scripts/generate_video.py --action "Action sequence:
    The subject stands upright for one second.
    Walks forward with four steps.
    Stops in a balanced position."

    # With raw prompt (no template)
    python scripts/generate_video.py --raw-prompt "A person dancing"

    # With Seedance
    python scripts/generate_video.py --model seedance --action "..."

    # With Sora
    python scripts/generate_video.py --model sora --action "..."

    # With Sora Pro (higher quality)
    python scripts/generate_video.py --model sora-pro --action "..."
"""

import argparse
import json
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from video2robot.utils import ensure_project_dir


def main():
    parser = argparse.ArgumentParser(
        description="Generate video using Seedance / Veo / Sora",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Model selection
    parser.add_argument("--model", "-m", default="seedance",
                        choices=["seedance", "veo", "sora", "sora-pro"],
                        help="Video generation model (default: seedance)")

    # Prompt options (mutually exclusive)
    prompt_group = parser.add_argument_group("Prompt options")
    prompt_input = prompt_group.add_mutually_exclusive_group(required=True)
    prompt_input.add_argument("--action", "-a",
                              help="Action sequence (uses BASE_PROMPT template for robot retargeting)")
    prompt_input.add_argument("--raw-prompt", "-p",
                              help="Raw prompt without BASE_PROMPT template")

    # Common arguments
    parser.add_argument("--name", "-n", help="Project folder name (default: video_XXX)")
    parser.add_argument("--duration", type=int, default=8,
                        help="Duration in seconds (Seedance: e.g. 8, Veo: 4-8, Sora: 4/8/12)")

    # Seedance/Veo arguments
    veo_group = parser.add_argument_group("Seedance/Veo options")
    veo_group.add_argument("--image", "-i", help="Input image for image-to-video (Veo only)")
    veo_group.add_argument("--veo-model", default="veo-3.1-fast-generate-preview",
                           help="Veo model: veo-3.1-generate-preview, veo-3.1-fast-generate-preview, "
                                "veo-3.0-generate-001, veo-3.0-fast-generate-001, veo-2.0-generate-001")
    veo_group.add_argument("--aspect-ratio", default="16:9", choices=["16:9", "9:16"],
                           help="Aspect ratio for Seedance/Veo")
    veo_group.add_argument("--seed", type=int, help="Random seed (Veo only)")
    veo_group.add_argument("--negative", "-neg", help="Negative prompt (Veo only)")
    veo_group.add_argument("--resolution", choices=["720p", "1080p"],
                           help="Resolution (Seedance/Veo)")
    veo_group.add_argument("--person", default="allow_all",
                           choices=["allow_all", "allow_adult", "dont_allow"],
                           help="Person generation (Veo only)")

    # Sora-specific arguments
    sora_group = parser.add_argument_group("Sora options")
    sora_group.add_argument("--size", default="1280x720",
                            choices=["720x1280", "1280x720", "1024x1792", "1792x1024"],
                            help="Video size for Sora (default: 1280x720 = 16:9 landscape)")

    args = parser.parse_args()

    # Build final prompt
    if args.action:
        from video2robot.video.prompts import build_prompt
        final_prompt = build_prompt(args.action)
        action_text = args.action
    else:
        final_prompt = args.raw_prompt
        action_text = None

    # Create project directory
    project_dir = ensure_project_dir(name=args.name)
    output_path = project_dir / "original.mp4"

    print(f"[Project] {project_dir}")

    # Determine provider and model_id from --model argument
    if args.model in ("sora", "sora-pro"):
        provider = "sora"
        sora_model_id = "sora-2-pro" if args.model == "sora-pro" else "sora-2"
    elif args.model == "seedance":
        provider = "seedance"
    else:
        provider = "veo"

    # Generate video based on provider
    if provider == "sora":
        from video2robot.video import SoraClient
        client = SoraClient(model_id=sora_model_id)
        client.generate(
            prompt=final_prompt,
            output_path=str(output_path),
            size=args.size,
            duration_seconds=args.duration,
        )
        # Save metadata
        metadata = {
            "created_at": datetime.now().isoformat(),
            "action": action_text,
            "prompt": final_prompt,
            "model": args.model,
            "provider": "sora",
            "sora": {
                "model_id": sora_model_id,
                "size": args.size,
                "duration_seconds": args.duration,
            },
        }
    elif provider == "seedance":
        from video2robot.video import SeedanceClient
        client = SeedanceClient()
        client.generate(
            prompt=final_prompt,
            output_path=str(output_path),
            aspect_ratio=args.aspect_ratio,
            resolution=args.resolution or "720p",
            duration_seconds=args.duration,
        )
        metadata = {
            "created_at": datetime.now().isoformat(),
            "action": action_text,
            "prompt": final_prompt,
            "model": args.model,
            "provider": "seedance",
            "seedance": {
                "aspect_ratio": args.aspect_ratio,
                "resolution": args.resolution or "720p",
                "duration_seconds": args.duration,
            },
        }
    else:
        from video2robot.video import VeoClient
        client = VeoClient(model_id=args.veo_model)
        client.generate(
            prompt=final_prompt,
            output_path=str(output_path),
            image_path=args.image,
            aspect_ratio=args.aspect_ratio,
            duration_seconds=args.duration,
            seed=args.seed,
            negative_prompt=args.negative,
            resolution=args.resolution,
            person_generation=args.person,
        )
        # Save metadata
        metadata = {
            "created_at": datetime.now().isoformat(),
            "action": action_text,
            "prompt": final_prompt,
            "model": args.model,
            "provider": "veo",
            "veo": {
                "model_id": args.veo_model,
                "aspect_ratio": args.aspect_ratio,
                "duration_seconds": args.duration,
                "seed": args.seed,
                "negative_prompt": args.negative,
                "resolution": args.resolution,
                "person_generation": args.person,
            },
        }

    with open(project_dir / "config.json", "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    print(f"\nDone!")
    print(f"  Project: {project_dir}")
    print(f"  Video:   {output_path}")
    print(f"  Config:  {project_dir / 'config.json'}")


if __name__ == "__main__":
    main()
