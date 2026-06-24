"""
Risk assessment service for fatigue management.

Calculates weekly scores and determines risk levels.
"""


def calculate_weekly_score(daily_scores):
    """
    Calculate the sum of daily fatigue scores for the past 7 days.

    Args:
        daily_scores: List of daily fatigue score floats

    Returns:
        float: Sum of all scores in the list
    """
    return round(sum(daily_scores), 1)


def get_risk_level(weekly_score, thresholds=None):
    """
    Determine risk level based on weekly score and thresholds.

    Args:
        weekly_score: The accumulated weekly fatigue score
        thresholds: Optional dict with 'safe', 'warning', 'danger' keys.
                    Defaults to safe <= 49, warning = 50-79, danger >= 80

    Returns:
        str: One of '安全' (safe), '注意' (warning), '危険' (danger)
    """
    if thresholds is None:
        thresholds = {
            'safe': 49.0,
            'warning': 50.0,
            'danger': 80.0,
        }

    safe = thresholds.get('safe', 49.0)
    danger = thresholds.get('danger', 80.0)

    if weekly_score <= safe:
        return '安全'
    elif weekly_score < danger:
        return '注意'
    else:
        return '危険'


def get_risk_style(risk_level):
    """
    Return a CSS class name for the risk level.

    Args:
        risk_level: '安全', '注意', or '危険'

    Returns:
        str: CSS class name
    """
    if risk_level == '安全':
        return 'risk-safe'
    elif risk_level == '注意':
        return 'risk-warning'
    else:
        return 'risk-danger'