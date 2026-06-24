"""
Video analysis service for fatigue management system.

Handles video upload, storage, and motion analysis using OpenCV + MediaPipe.
Features: stride, pitch, joint angles, ground contact time, pelvic movement.
"""

import os
import json
import uuid
import math
from werkzeug.utils import secure_filename
from datetime import datetime

# Optional imports - gracefully degrade if not available
try:
    import cv2
    import numpy as np
    OPENCV_AVAILABLE = True
except ImportError:
    OPENCV_AVAILABLE = False

try:
    import mediapipe as mp
    MEDIAPIPE_AVAILABLE = True
except ImportError:
    MEDIAPIPE_AVAILABLE = False


ALLOWED_EXTENSIONS = {'mp4', 'mov', 'avi', 'webm', 'mkv'}

# Analysis configuration
ANALYSIS_CONFIG = {
    'real_world_distance_m': 30.0,   # Assumed real-world distance covered (m)
    'hip_height_ratio': 0.53,         # Hip height / body height (approx)
    'gravity': 9.81,                  # m/s²
}


def allowed_file(filename):
    """Check if the file extension is allowed."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def save_video(file, upload_folder):
    """Save an uploaded video file to the specified folder."""
    if file is None or file.filename == '':
        return None

    if not allowed_file(file.filename):
        return None

    ext = file.filename.rsplit('.', 1)[1].lower()
    unique_name = f"{uuid.uuid4().hex}.{ext}"
    filename = secure_filename(unique_name)
    filepath = os.path.join(upload_folder, filename)
    file.save(filepath)

    return os.path.join('uploads', filename)


# ============================================================
#  Pose Analysis Engine (OpenCV + MediaPipe)
# ============================================================

def analyze_video(filepath):
    """
    Analyze a running video to extract fatigue-related metrics.

    Args:
        filepath: Relative path to the video file (from static folder)

    Returns:
        dict: Analysis results with keys:
              stride_m, pitch_steps_per_sec, hip_angle_deg, knee_angle_deg,
              ground_contact_time_ms, pelvic_oscillation_px,
              running_score, status, error (if any)
    """
    if not OPENCV_AVAILABLE or not MEDIAPIPE_AVAILABLE:
        return _fallback_analysis(filepath)

    try:
        return _run_mediapipe_analysis(filepath)
    except Exception as e:
        return {
            'status': 'failed',
            'error': str(e),
            'stride_m': None,
            'pitch_steps_per_sec': None,
            'hip_angle_deg': None,
            'knee_angle_deg': None,
            'ground_contact_time_ms': None,
            'pelvic_oscillation_px': None,
            'running_score': 0.0,
        }


def _fallback_analysis(filepath):
    """Fallback analysis when OpenCV/MediaPipe are not available.
    Uses basic frame counting via file metadata (if possible).
    """
    result = {
        'status': 'partial',
        'error': 'OpenCVまたはMediaPipeがインストールされていません。'
                 'pip install opencv-python mediapipe numpy を実行してください。',
        'stride_m': None,
        'pitch_steps_per_sec': None,
        'hip_angle_deg': None,
        'knee_angle_deg': None,
        'ground_contact_time_ms': None,
        'pelvic_oscillation_px': None,
        'running_score': 0.0,
    }

    # Try to get basic video info even without OpenCV
    try:
        if OPENCV_AVAILABLE and hasattr(cv2, 'VideoCapture'):
            cap = cv2.VideoCapture(filepath)
            if cap.isOpened():
                fps = cap.get(cv2.CAP_PROP_FPS)
                frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                duration = frame_count / fps if fps > 0 else 0
                result['fps'] = round(fps, 1)
                result['frame_count'] = frame_count
                result['duration_sec'] = round(duration, 2)
                cap.release()
    except Exception:
        pass

    return result


def _run_mediapipe_analysis(filepath):
    """Core analysis using MediaPipe Pose for landmark detection."""
    mp_pose = mp.solutions.pose
    mp_drawing = mp.solutions.drawing_utils

    cap = cv2.VideoCapture(filepath)
    if not cap.isOpened():
        raise ValueError(f"動画ファイルを開けませんでした: {filepath}")

    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    duration_sec = total_frames / fps if fps > 0 else 0

    if fps <= 0 or total_frames <= 0:
        raise ValueError("動画のフレームレートまたはフレーム数が不正です。")

    # Tracking data across frames
    hip_angles = []          # Hip joint angles per frame
    knee_angles = []         # Knee joint angles per frame
    hip_y_positions = []     # Pelvis Y coordinates (for vertical oscillation)
    ankle_y_positions = []   # Ankle Y coordinates (for ground contact detection)
    left_knee_y = []         # Left knee Y (for stride/keypoint detection)

    # Landmark indices for MediaPipe Pose
    # https://google.github.io/mediapipe/solutions/pose.html
    LEFT_HIP = 23
    RIGHT_HIP = 24
    LEFT_KNEE = 25
    RIGHT_KNEE = 26
    LEFT_ANKLE = 27
    RIGHT_ANKLE = 28
    LEFT_SHOULDER = 11
    RIGHT_SHOULDER = 12

    with mp_pose.Pose(
        static_image_mode=False,
        model_complexity=1,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5
    ) as pose:
        frame_idx = 0

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            # Process every 2nd frame for performance (if fps >= 30)
            if fps < 30 or frame_idx % 2 == 0:
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                results = pose.process(frame_rgb)

                if results.pose_landmarks:
                    lm = results.pose_landmarks.landmark

                    # Convert normalized coordinates to pixel coordinates
                    def to_px(landmark):
                        return (landmark.x * width, landmark.y * height)

                    # Hip angle: angle between shoulder-hip-knee (left side)
                    l_shoulder = to_px(lm[LEFT_SHOULDER])
                    l_hip = to_px(lm[LEFT_HIP])
                    l_knee = to_px(lm[LEFT_KNEE])
                    l_ankle = to_px(lm[LEFT_ANKLE])

                    r_shoulder = to_px(lm[RIGHT_SHOULDER])
                    r_hip = to_px(lm[RIGHT_HIP])
                    r_knee = to_px(lm[RIGHT_KNEE])
                    r_ankle = to_px(lm[RIGHT_ANKLE])

                    # Calculate joint angles
                    l_hip_angle = _calculate_angle(l_shoulder, l_hip, l_knee)
                    r_hip_angle = _calculate_angle(r_shoulder, r_hip, r_knee)
                    l_knee_angle_val = _calculate_angle(l_hip, l_knee, l_ankle)
                    r_knee_angle_val = _calculate_angle(r_hip, r_knee, r_ankle)

                    avg_hip_angle = (l_hip_angle + r_hip_angle) / 2
                    avg_knee_angle = (l_knee_angle_val + r_knee_angle_val) / 2

                    hip_angles.append(avg_hip_angle)
                    knee_angles.append(avg_knee_angle)

                    # Pelvis Y position (midpoint of left/right hip)
                    pelvis_y = (l_hip[1] + r_hip[1]) / 2
                    hip_y_positions.append(pelvis_y)

                    # Ankle Y (minimum of left/right, lower = closer to ground)
                    ankle_y = min(l_ankle[1], r_ankle[1])
                    ankle_y_positions.append(ankle_y)

                    left_knee_y.append(l_knee[1])

            frame_idx += 1

    cap.release()

    processed_frames = len(hip_angles)
    if processed_frames < 3:
        return {
            'status': '解析済み',
            'error': '十分な姿勢データが検出できませんでした。全身が映った真横からの映像をお使いください。',
            'stride_m': None,
            'pitch_steps_per_sec': None,
            'hip_angle_deg': None,
            'knee_angle_deg': None,
            'ground_contact_time_ms': None,
            'pelvic_oscillation_px': None,
            'running_score': 0.0,
            'fps': round(fps, 1),
            'frame_count': total_frames,
            'duration_sec': round(duration_sec, 2),
            'processed_frames': processed_frames,
        }

    # ----- Extract metrics -----

    # 1. Average joint angles
    avg_hip = round(np.mean(hip_angles), 1)
    avg_knee = round(np.mean(knee_angles), 1)

    # 2. Pelvic oscillation (vertical)
    pelvic_osc = round(np.std(hip_y_positions), 1)

    # 3. Ground contact time estimation
    # Detect foot strike events: ankle Y near max (closest to ground)
    ankle_arr = np.array(ankle_y_positions)
    ankle_threshold = np.percentile(ankle_arr, 85)  # Top 15% Y values = ground contact
    contact_frames = np.sum(ankle_arr >= ankle_threshold)
    contact_ratio = contact_frames / len(ankle_arr) if len(ankle_arr) > 0 else 0
    frame_interval = 1.0 / fps
    ground_contact_ms = round(contact_ratio * frame_interval * 1000, 1)

    # 4. Stride estimation
    # Count step cycles from knee Y oscillation
    knee_arr = np.array(left_knee_y)
    if len(knee_arr) > 3:
        # Find zero-crossings of the detrended signal to count steps
        knee_detrended = knee_arr - np.mean(knee_arr)
        zero_crossings = np.sum(np.diff(np.signbit(knee_detrended)))
        step_count = max(1, zero_crossings // 2)
    else:
        step_count = 1

    stride_m = round(ANALYSIS_CONFIG['real_world_distance_m'] / step_count, 2)

    # 5. Pitch estimation
    pitch = round(step_count / duration_sec, 1) if duration_sec > 0 else 0

    # 6. Running score (relative to baseline, using population norms as proxy)
    # Baseline reference values
    baseline_stride = 2.2       # m (typical for sprinters)
    baseline_pitch = 4.0        # steps/sec
    baseline_hip_angle = 160.0  # degrees
    baseline_knee_angle = 150.0 # degrees

    stride_change = abs((baseline_stride - stride_m) / baseline_stride * 100) if stride_m else 0
    pitch_change = abs((baseline_pitch - pitch) / baseline_pitch * 100) if pitch else 0
    hip_change = abs((baseline_hip_angle - avg_hip) / baseline_hip_angle * 100) if avg_hip else 0
    knee_change = abs((baseline_knee_angle - avg_knee) / baseline_knee_angle * 100) if avg_knee else 0

    running_score = round(stride_change + pitch_change + hip_change + knee_change, 1)

    return {
        'status': '解析済み',
        'error': None,
        'stride_m': stride_m,
        'pitch_steps_per_sec': pitch,
        'hip_angle_deg': avg_hip,
        'knee_angle_deg': avg_knee,
        'ground_contact_time_ms': ground_contact_ms,
        'pelvic_oscillation_px': pelvic_osc,
        'running_score': running_score,
        'fps': round(fps, 1),
        'frame_count': total_frames,
        'duration_sec': round(duration_sec, 2),
        'processed_frames': processed_frames,
        'contact_ratio': round(contact_ratio, 3),
        'estimated_steps': step_count,
        # Baseline comparisons
        'stride_change_pct': round(stride_change, 1),
        'pitch_change_pct': round(pitch_change, 1),
        'hip_angle_change_pct': round(hip_change, 1),
        'knee_angle_change_pct': round(knee_change, 1),
    }


def _calculate_angle(a, b, c):
    """
    Calculate angle ABC (angle at point b) in degrees.

    Args:
        a: (x, y) of first point
        b: (x, y) of vertex point
        c: (x, y) of third point

    Returns:
        float: Angle in degrees
    """
    ba = (a[0] - b[0], a[1] - b[1])
    bc = (c[0] - b[0], c[1] - b[1])

    dot_product = ba[0] * bc[0] + ba[1] * bc[1]
    mag_ba = math.sqrt(ba[0]**2 + ba[1]**2)
    mag_bc = math.sqrt(bc[0]**2 + bc[1]**2)

    if mag_ba == 0 or mag_bc == 0:
        return 0.0

    cos_angle = max(-1.0, min(1.0, dot_product / (mag_ba * mag_bc)))
    angle_rad = math.acos(cos_angle)
    return math.degrees(angle_rad)