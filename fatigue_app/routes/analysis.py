import os
import json
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from models import db, TrainingRecord, VideoRecord
from services.video_service import save_video, analyze_video, allowed_file
from services.score_service import (
    calculate_daily_fatigue_score,
)

analysis_bp = Blueprint('analysis', __name__)


@analysis_bp.route('/analysis/<int:record_id>')
def analysis_detail(record_id):
    """Display analysis results for a specific record."""
    record = TrainingRecord.query.get_or_404(record_id)
    videos = VideoRecord.query.filter_by(training_record_id=record_id).all()

    # Parse JSON for each video
    parsed_videos = []
    for v in videos:
        video_data = {
            'id': v.id,
            'video_type': v.video_type,
            'file_path': v.file_path,
            'analysis_status': v.analysis_status,
        }
        if v.analysis_result_json:
            try:
                video_data['analysis'] = json.loads(v.analysis_result_json)
            except (json.JSONDecodeError, TypeError):
                video_data['analysis'] = {}
        else:
            video_data['analysis'] = {}
        parsed_videos.append(video_data)

    return render_template('analysis.html', record=record, videos=parsed_videos)


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

    flash('動画をアップロードしました。「解析実行」ボタンから解析を開始できます。', 'success')
    return redirect(url_for('analysis.analysis_detail', record_id=record.id))


@analysis_bp.route('/video/<int:video_id>/analyze', methods=['POST'])
def video_analyze(video_id):
    """Run motion analysis on an uploaded video."""
    video = VideoRecord.query.get_or_404(video_id)

    # Build absolute file path
    file_path = os.path.join(current_app.config['UPLOAD_FOLDER'],
                             os.path.basename(video.file_path))

    if not os.path.exists(file_path):
        flash('動画ファイルが見つかりません。', 'error')
        return redirect(url_for('analysis.analysis_detail',
                                record_id=video.training_record_id))

    # Run analysis
    video.analysis_status = '解析中'
    db.session.commit()

    try:
        result = analyze_video(file_path)

        if result.get('status') == '解析済み':
            video.analysis_status = '解析済み'
        elif result.get('status') == 'failed':
            video.analysis_status = '失敗'
        else:
            video.analysis_status = '未解析'

        video.analysis_result_json = json.dumps(result, ensure_ascii=False)
        db.session.commit()

        # If running_score was calculated, update the training record
        if result.get('running_score', 0) > 0:
            record = TrainingRecord.query.get(video.training_record_id)
            if record:
                record.running_score = result['running_score']
                # Recalculate daily fatigue score with new running score
                record.daily_fatigue_score = calculate_daily_fatigue_score(
                    training_score=record.training_score,
                    sleep_score=record.sleep_score,
                    subjective_fatigue_score=record.fatigue_score_self,
                    temperature_score=record.temperature_score,
                    running_score=record.running_score,
                )
                db.session.commit()

        if video.analysis_status == '解析済み':
            flash('動画解析が完了しました。', 'success')
        elif video.analysis_status == '失敗':
            flash(f'解析中にエラーが発生しました: {result.get("error", "不明なエラー")}', 'error')
        else:
            flash('解析を実行しましたが、結果が不完全です。', 'warning')

    except Exception as e:
        video.analysis_status = '失敗'
        video.analysis_result_json = json.dumps({
            'status': 'failed',
            'error': str(e),
            'running_score': 0.0,
        }, ensure_ascii=False)
        db.session.commit()
        flash(f'解析中にエラーが発生しました: {str(e)}', 'error')

    return redirect(url_for('analysis.analysis_detail',
                            record_id=video.training_record_id))