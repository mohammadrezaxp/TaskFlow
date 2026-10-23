from django.urls import reverse


def navigation(request):
    if not request.user.is_authenticated:
        return {}
    links = [
        ("dashboard", "◈", "Dashboard"),
        ("task-list", "☑", "Tasks"),
        ("task-kanban", "▥", "Kanban"),
        ("project-list", "▣", "Projects"),
        ("organization-list", "◇", "Organizations"),
        ("calendar", "▦", "Calendar"),
        ("team-list", "♧", "Team"),
        ("messages", "✉", "Messages"),
        ("notification-list", "♢", "Notifications"),
        ("activity-list", "◷", "Activity"),
        ("analytics", "↗", "Analytics"),
        ("accounts:profile", "◉", "Profile"),
        ("settings-index", "⚙", "Settings"),
    ]
    return {
        "sidebar_items": [
            {
                "url": reverse(name),
                "label": label,
                "icon": icon,
                "active": request.path == reverse(name),
            }
            for name, icon, label in links
        ],
        "unread_count": request.user.notifications.filter(
            read_at=None, organization__memberships__user=request.user
        ).count(),
    }
