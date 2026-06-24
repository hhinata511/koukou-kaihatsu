"""
Score calculation service for fatigue management system.

Calculates individual score components and the daily fatigue score.
"""

# Training menu base scores (as specified in the design document)
MENU_SCORES = {
    'ジョグ': 1,
    '体操': 1,
    'ドリル': 2,
    'ランジ前後': 2,
    '股関節ストレッチ': 2,
    '反発スキップ': 2,
    'Cスキップ': 2,
    '3テンポ腿上げ': 2,
    '2テンポ腿上げ': 2,
    'ジャンプスキップ': 2,
    'スピードスキップ': 2,
    'バウンディング': 2,
    '流し×2': 1,
    '流し': 1,
    'ショートスプリント': 4,
    'ショートスプリント（30m）': 4,
    'ショートスプリント（50m）': 4,
    'ショートスプリント（70m）': 4,
    'マーカー走': 4,
    '変形ダッシュ': 5,
    '坂ダッシュ': 6,
    '坂ダッシュ・坂トレーニング': 6,
    '100m': 5,
    '120m': 6,
    '150m': 6,
    '200m': 7,
    '300m': 8,
    'タイヤ引きトレーニング': 8,
    '200m＋100m': 8,
    '300m＋100m': 9,
    '100mリレー': 6,
    '200mリレー': 7,
    'サーキットトレーニング': 8,
    'ラダートレーニング': 3,
}


def calculate_training_score(menu_name, menu_count=1):
    """
    Calculate training intensity score based on menu and count.

    Uses a base score from MENU_SCORES multiplied by a count factor.
    """
    base_score = MENU_SCORES.get(menu_name, 3)  # Default score for unknown menus
    # Count multiplier: more reps = higher fatigue contribution
    if menu_count <= 1:
        factor = 1.0
    elif menu_count <= 3:
        factor = 1.2
    elif menu_count <= 5:
        factor = 1.5
    else:
        factor = 2.0
    return round(base_score * factor, 1)


def calculate_sleep_score(sleep_hours, average_sleep=7.5):
    """
    Calculate sleep score based on the difference between actual and average sleep.

    Formula: max(0, (average_sleep - sleep_hours) * 2)
    Positive score means sleep deficit contributes to fatigue.
    """
    diff = average_sleep - sleep_hours
    return round(max(0.0, diff * 2), 1)


def calculate_subjective_fatigue_score(fatigue_value):
    """
    Calculate subjective fatigue score.
    Uses the raw input value (1-5) multiplied by 2 for emphasis.
    """
    if fatigue_value < 1:
        fatigue_value = 1
    if fatigue_value > 5:
        fatigue_value = 5
    return round(float(fatigue_value) * 2, 1)


def calculate_temperature_score(temperature, threshold=25.0):
    """
    Calculate temperature score. High temperatures increase fatigue.

    Formula: max(0, (temperature - threshold) * 0.5)
    """
    return round(max(0.0, (temperature - threshold) * 0.5), 1)


def calculate_daily_fatigue_score(
    training_score=0.0,
    sleep_score=0.0,
    subjective_fatigue_score=0.0,
    temperature_score=0.0,
    running_score=0.0
):
    """
    Aggregate all component scores into a daily fatigue score.

    fatigue_score = training_score + sleep_score + subjective_fatigue_score
                    + temperature_score + running_score
    """
    total = (
        training_score
        + sleep_score
        + subjective_fatigue_score
        + temperature_score
        + running_score
    )
    return round(total, 1)