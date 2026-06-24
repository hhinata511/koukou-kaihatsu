import os
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from models import db, TrainingRecord, VideoRecord
from services.video_service import save_video, analyze_video, allowed_file

analysis_bp = Blueprint('analysis', __name__)


@analysis_bp.route('/analysis/<int:record_id>')
def analysis_detail(record_id):
    """Display analysis results for a specific record."""
    record = TrainingRecord.query.get_or_404(record_id)
    videos = VideoRecord.query.filter_by(training_record_id=record_id).all()
    return render_template('analysis.html', record=record, videos=videos)


@analysis_bp.route('/video/upload', methods=['POST'])
def video_upload():
    """Upload a video file associated with a training record."""
    record_id = request.form.get('record_id', '')

    if not record_id:
        flash('記録IDが指定されていません。', 'error')
        return redirect(url_for('records.record_list'))

    record = TrainingRecord.query.get(int(record_id))

    if record is None:
        flash('指定された記録が見つかりません。', 'error')
        return redirect(url_for('records.record_list'))

    if 'video_file' not in request.files:
        flash('動画ファイルが選択されていません。', 'error')
        return redirect(url_for('analysis.analysis_detail', record_id=record.id))

    file = request.files['video_file']
    video_type = request.form.get('video_type', 'running')

    if file.filename == '':
        flash('動画ファイルが選択されていません。', 'error')
        return redirect(url_for('analysis.analysis_detail', record_id=record.id))

    if not allowed_file(file.filename):
        flash('許可されていないファイル形式です。mp4, mov, avi, webm, mkv を利用してください。', 'error')
        return redirect(url_for('analysis.analysis_detail', record_id=record.id))

    upload_folder = current_app.config['UPLOAD_FOLDER']
    file_path = save_video(file, upload_folder)

    if file_path is None:
        flash('動画の保存に失敗しました。', 'error')
        return redirect(url_for('analysis.analysis_detail', record_id=record.id))

    video_record = VideoRecord(
        training_record_id=record.id,
        video_type=video_type,
        file_path=file_path,
        analysis_status='未解析',
        analysis_result_json='{}',
    )

    db.session.add(video_record)
    db.session.commit()

    flash('動画をアップロードしました。', 'success')
    return redirect(url_for('analysis.analysis_detail', record_id=record.id))