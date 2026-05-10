"""Prompt templates for video generation.

This module provides a standardized base prompt optimized for robot retargeting,
ensuring consistent full-body motion capture style videos.

Usage:
    from video2robot.video.prompts import build_prompt

    action = '''Action sequence:
    The subject stands upright in a neutral posture for one second.
    Initiates walking forward at a normal human pace.
    Takes four consecutive steps forward.
    Comes to a balanced stop.'''

    final_prompt = build_prompt(action)
"""

# Base prompt optimized for robot motion retargeting
# This prompt ensures:
# - Full body always visible (head to feet)
# - Tight-fitting clothing (no loose garments that obscure body)
# - Static camera (easier pose estimation)
# - Plain environment (reduce visual noise)
# - Physically realistic motion (better retargeting quality)
BASE_PROMPT = """Full-body shot of a single adult humanoid subject, with the entire body visible from head to feet at all times.

The subject is wearing tight-fitting motion capture style clothing: a short-sleeve shirt and slim athletic pants.
No coat, no jacket, no robe, no cloak, no skirt, no loose clothing, no accessories.

Static camera, eye-level, neutral perspective.
The subject remains fully inside the frame throughout the entire video.

The scene takes place in a realistic indoor room environment.
The room has clearly visible walls, floor, and corners.
The boundary between the floor and the walls is clearly visible.
The floor plane is clearly defined and fully visible.
The background is NOT a seamless white backdrop, NOT a studio cyclorama, and NOT an infinite background.

The room resembles a simple laboratory, motion analysis room, or empty interior space.
Surfaces are plain but spatially well-defined.

Even, neutral indoor lighting with no dramatic shadows or highlights.
No cinematic effects.

Motion is biomechanically accurate and physically realistic.
Natural human joint limits, correct center-of-mass movement, realistic balance, gravity, inertia, and ground contact.
No exaggerated motion, no stylized animation.

No camera movement, no cuts, no slow motion, no motion blur.
"""

def build_prompt(action: str) -> str:
    """Build final prompt by combining BASE_PROMPT with action description.

    Args:
        action: Action sequence description. Should describe step-by-step
                movements, e.g.:
                "Action sequence:
                The subject stands upright for one second.
                Shifts weight forward.
                Takes three steps forward.
                Stops in a balanced position."

    Returns:
        Full prompt string: BASE_PROMPT + "\\n\\n" + action
    """
    return f"{BASE_PROMPT}\n\n{action}"
