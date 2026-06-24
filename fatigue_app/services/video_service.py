"""
Video service for fatigue management system.

Handles video upload, storage, and placeholder analysis.
Full video analysis with OpenCV/MediaPipe will be implemented in Phase 2/3.
"""

import os
import uuid
from werkzeug.utils import secure_filename


ALLOWED_EXTENSIONS = {'mp4', 'mov', 'avi', 'webm', 'mkv'}


def allowed_file(filename):
    """Check if the file extension is allowed."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def save_video(file, upload_folder):
    """
    Save an uploaded video file to the specified folder.

    Args:
        file: Flask FileStorage object
        upload_folder: Absolute path to the upload directory

    Returns:
        str: Relative file path (from static folder) or None on failure
    """
    if file is None or file.filename == '':
        return None

    if not allowed_file(file.filename):
        return None

    # Generate a unique filename to avoid collisions
    ext = file.filename.rsplit('.', 1)[1].lower()
    unique_name = f"{uuid.uuid4().hex}.{ext}"
    filename = secure_filename(unique_name)
    filepath = os.path.join(upload_folder, filename)
    file.save(filepath)

    # Return path relative to the app's static folder
    return os.path.join('uploads', filename)


def analyze_video(filepath):
    """
    Placeholder for video analysis.
    In future phases, this will use OpenCV and MediaPipe to extract
    stride, pitch, joint angles, etc.

    Args:
        filepath: Path to the video file

    Returns:
        dict: Analysis result (empty dict in MVP)
    """
    # MVP: Return empty result
    return {}