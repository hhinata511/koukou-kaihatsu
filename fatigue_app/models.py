from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone

db = SQLAlchemy()


class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, default='Default User')
    average_sleep = db.Column(db.Float, nullable=False, default=7.5)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    training_records = db.relationship('TrainingRecord', backref='user', lazy=True)
    settings = db.relationship('Setting', backref='user', lazy=True)


class TrainingRecord(db.Model):
    __tablename__ = 'training_records'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    record_date = db.Column(db.Date, nullable=False)
    menu_name = db.Column(db.String(200), nullable=False)
    menu_count = db.Column(db.Integer, nullable=False, default=1)
    training_score = db.Column(db.Float, default=0.0)
    sleep_hours = db.Column(db.Float, default=0.0)
    sleep_score = db.Column(db.Float, default=0.0)
    subjective_fatigue = db.Column(db.Integer, default=3)
    fatigue_score_self = db.Column(db.Float, default=0.0)
    temperature = db.Column(db.Float, default=20.0)
    temperature_score = db.Column(db.Float, default=0.0)
    running_score = db.Column(db.Float, default=0.0)
    daily_fatigue_score = db.Column(db.Float, default=0.0)
    remark = db.Column(db.Text, default='')
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    videos = db.relationship('VideoRecord', backref='training_record', lazy=True)


class VideoRecord(db.Model):
    __tablename__ = 'video_records'

    id = db.Column(db.Integer, primary_key=True)
    training_record_id = db.Column(db.Integer, db.ForeignKey('training_records.id'), nullable=False)
    video_type = db.Column(db.String(50), default='running')
    file_path = db.Column(db.String(500), nullable=False)
    analysis_status = db.Column(db.String(50), default='未解析')
    analysis_result_json = db.Column(db.Text, default='')
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))


class Setting(db.Model):
    __tablename__ = 'settings'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    weekly_safe_threshold = db.Column(db.Float, default=49.0)
    weekly_warning_threshold = db.Column(db.Float, default=50.0)
    weekly_danger_threshold = db.Column(db.Float, default=80.0)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )