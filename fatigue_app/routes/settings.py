from flask import Blueprint, render_template, request, redirect, url_for, flash
from models import db, User, Setting

settings_bp = Blueprint('settings', __name__)


@settings_bp.route('/settings', methods=['GET', 'POST'])
def settings_page():
    """User settings: average sleep time, threshold values."""
    user = User.query.first()
    if not user:
        flash('ユーザーが見つかりません。', 'error')
        return redirect(url_for('main.index'))

    setting = Setting.query.filter_by(user_id=user.id).first()
    if not setting:
        setting = Setting(
            user_id=user.id,
            weekly_safe_threshold=49.0,
            weekly_warning_threshold=50.0,
            weekly_danger_threshold=80.0,
        )
        db.session.add(setting)
        db.session.commit()

    if request.method == 'POST':
        try:
            average_sleep = float(request.form.get('average_sleep', '7.5'))
            if average_sleep < 0 or average_sleep > 24:
                flash('平均睡眠時間は0〜24の間で入力してください。', 'error')
                return render_template('settings.html', user=user, setting=setting)

            safe_threshold = float(request.form.get('safe_threshold', '49.0'))
            warning_threshold = float(request.form.get('warning_threshold', '50.0'))
            danger_threshold = float(request.form.get('danger_threshold', '80.0'))

            if not (safe_threshold < warning_threshold < danger_threshold):
                flash('閾値は 安全 < 注意 < 危険 となるように設定してください。', 'error')
                return render_template('settings.html', user=user, setting=setting)

            user.average_sleep = average_sleep
            setting.weekly_safe_threshold = safe_threshold
            setting.weekly_warning_threshold = warning_threshold
            setting.weekly_danger_threshold = danger_threshold

            db.session.commit()
            flash('設定を保存しました。', 'success')
            return redirect(url_for('main.index'))

        except (ValueError, TypeError):
            flash('数値を正しく入力してください。', 'error')
            return render_template('settings.html', user=user, setting=setting)

    return render_template('settings.html', user=user, setting=setting)