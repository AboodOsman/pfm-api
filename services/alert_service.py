from repositories.alert_repository import (
    get_all_alerts,
    get_alerts_by_user,
    get_alerts_by_type,
)

def list_all_alerts():
    return get_all_alerts()

def list_alerts_for_user(user_id: int, only_unread: bool = False):
    return get_alerts_by_user(user_id, only_unread=only_unread)

def list_alerts_by_type(alert_type: str):
    return get_alerts_by_type(alert_type)