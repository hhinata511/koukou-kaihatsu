from datetime import date, datetime, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash
from models import db, User, TrainingRecord, Setting
from services.score_service import (
    MENU_SCORES,
    calculate_training_score,
    calculate_sleep_score,
    calculate_subjective_fatigue_score,
    calculate_temperature_score,
    calculate_daily_fatigue_score,
)
from services.risk_service import calculate_weekly_score, get_risk_level, get_risk_style

records_bp = Blueprint('records', __name__)


@records_bp.route('/records')
def record_list():
    """Display list of all past records."""
    user = User.query.first()
    if not user:
        flash('ユーザーが見つかりません。', 'error')
        return redirect(url_for('main.index'))

    records = TrainingRecord.query.filter(
        TrainingRecord.user_id == user.id
    ).order_by(TrainingRecord.record_date.desc()).all()

    return render_template('record_list.html', records=records)


@records_bp.route('/record/new', methods=['GET', 'POST'])
def record_new():
    """Input form for a new daily record."""
    user = User.query.first()
    if not user:
        flash('ユーザーが見つかりません。', 'error')
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        record_date_str = request.form.get('record_date', '')
        menu_name = request.form.get('menu_name', '')
        menu_count_str = request.form.get('menu_count', '1')
        sleep_hours_str = request.form.get('sleep_hours', '0')
        subjective_fatigue_str = request.form.get('subjective_fatigue', '3')
        temperature_str = request.form.get('temperature', '20')
        remark = request.form.get('remark', '')

        # Validation
        errors = []
        try:
            record_date = datetime.strptime(record_date_str, '%Y-%m-%d').date()
        except (ValueError, TypeError):
            errors.append('日付を正しく入力してください。')

        if not menu_name:
            errors.append('練習メニューを選択してください。')

        try:
            menu_count = int(menu_count_str)
            if menu_count < 0:
                errors.append('本数は0以上を入力してください。')
        except (ValueError, TypeError):
            errors.append('本数は整数で入力してください。')

        try:
            sleep_hours = float(sleep_hours_str)
            if sleep_hours < 0 or sleep_hours > 24:
                errors.append('睡眠時間は0〜24の間で入力してください。')
        except (ValueError, TypeError):
            errors.append('睡眠時間を正しく入力してください。')

        try:
            subjective_fatigue = int(subjective_fatigue_str)
            if subjective_fatigue < 1 or subjective_fatigue > 5:
                errors.append('主観的疲労度は1〜5で入力してください。')
        except (ValueError, TypeError):
            errors.append('主観的疲労度を正しく入力してください。')

        try:
            temperature = float(temperature_str)
        except (ValueError, TypeError):
            temperature = 20.0

        if errors:
            for error in errors:
                flash(error, 'error')
            return render_template(
                'record_form.html',
                menu_list=MENU_SCORES,
                today=date.today(),
                form_data=request.form
            )

        # Calculate scores
        training_score = calculate_training_score(menu_name, menu_count)
        sleep_score = calculate_sleep_score(sleep_hours, user.average_sleep)
        subjective_fatigue_score = calculate_subjective_fatigue_score(subjective_fatigue)
        temperature_score = calculate_temperature_score(temperature)
        daily_score = calculate_daily_fatigue_score(
            training_score=training_score,
            sleep_score=sleep_score,
            subjective_fatigue_score=subjective_fatigue_score,
            temperature_score=temperature_score,
            running_score=0.0,  # MVP: no running score
        )

        # Save record
        record = TrainingRecord(
            user_id=user.id,
            record_date=record_date,
            menu_name=menu_name,
            menu_count=menu_count,
            training_score=training_score,
            sleep_hours=sleep_hours,
            sleep_score=sleep_score,
            subjective_fatigue=subjective_fatigue,
            fatigue_score_self=subjective_fatigue_score,
            temperature=temperature,
            temperature_score=temperature_score,
            running_score=0.0,
            daily_fatigue_score=daily_score,
            remark=remark,
        )

        db.session.add(record)
        db.session.commit()

        flash('記録を保存しました。', 'success')
        return redirect(url_for('records.record_detail', record_id=record.id))

    return render_template(
        'record_form.html',
        menu_list=MENU_SCORES,
        today=date.today(),
        form_data=None
    )


@records_bp.route('/record/<int:record_id>')
def record_detail(record_id):
    """Display detail of a specific record."""
    record = TrainingRecord.query.get_or_404(record_id)
    user = User.query.get(record.user_id)

    # Calculate weekly score at the time of this record
    seven_days_ago = record.record_date - timedelta(days=6)
    week_records = TrainingRecord.query.filter(
        TrainingRecord.user_id == record.user_id,
        TrainingRecord.record_date >= seven_days_ago,
        TrainingRecord.record_date <= record.record_date
    ).order_by(TrainingRecord.record_date.asc()).all()

    daily_scores = [r.daily_fatigue_score for r in week_records]
    weekly_score = calculate_weekly_score(daily_scores) if daily_scores else 0.0

    setting = Setting.query.filter_by(user_id=record.user_id).first()
    thresholds = None
    if setting:
        thresholds = {
            'safe': setting.weekly_safe_threshold,
            'warning': setting.weekly_warning_threshold,
            'danger': setting.weekly_danger_threshold,
        }

    risk_level = get_risk_level(weekly_score, thresholds)
    risk_style = get_risk_style(risk_level)

    return render_template(
        'record_detail.html',
        record=record,
        user=user,
        weekly_score=weekly_score,
        risk_level=risk_level,
        risk_style=risk_style,
    )