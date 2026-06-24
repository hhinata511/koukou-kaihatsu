from datetime import date, timedelta
from flask import Blueprint, render_template
from models import db, User, TrainingRecord, Setting
from services.risk_service import calculate_weekly_score, get_risk_level, get_risk_style

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    """Top page: display today's fatigue score, weekly score, and risk level."""
    user = User.query.first()
    if not user:
        return render_template('index.html', today_record=None, weekly_score=0,
                               risk_level='安全', risk_style='risk-safe',
                               latest_records=[], has_record=False)

    # Get today's record (most recent today)
    today = date.today()
    today_record = TrainingRecord.query.filter(
        TrainingRecord.user_id == user.id,
        TrainingRecord.record_date == today
    ).order_by(TrainingRecord.created_at.desc()).first()

    # Calculate weekly score from the last 7 records (or 7 days)
    seven_days_ago = today - timedelta(days=6)
    week_records = TrainingRecord.query.filter(
        TrainingRecord.user_id == user.id,
        TrainingRecord.record_date >= seven_days_ago,
        TrainingRecord.record_date <= today
    ).order_by(TrainingRecord.record_date.asc()).all()

    daily_scores = [r.daily_fatigue_score for r in week_records]
    weekly_score = calculate_weekly_score(daily_scores) if daily_scores else 0.0

    # Get thresholds from settings
    setting = Setting.query.filter_by(user_id=user.id).first()
    thresholds = None
    if setting:
        thresholds = {
            'safe': setting.weekly_safe_threshold,
            'warning': setting.weekly_warning_threshold,
            'danger': setting.weekly_danger_threshold,
        }

    risk_level = get_risk_level(weekly_score, thresholds)
    risk_style = get_risk_style(risk_level)

    # Get latest 7 records for context
    latest_records = TrainingRecord.query.filter(
        TrainingRecord.user_id == user.id
    ).order_by(TrainingRecord.record_date.desc()).limit(7).all()

    return render_template(
        'index.html',
        today_record=today_record,
        weekly_score=weekly_score,
        risk_level=risk_level,
        risk_style=risk_style,
        latest_records=latest_records,
        has_record=today_record is not None
    )