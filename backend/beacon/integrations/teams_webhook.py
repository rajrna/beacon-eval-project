"""Microsoft Teams webhook integration. Best-effort — never blocks eval runs."""
from typing import Any

import httpx
import structlog

logger = structlog.get_logger(__name__)


async def send_teams_alert(
    webhook_url: str,
    title: str,
    message: str,
    severity: str = "info",  # info, warning, critical
    facts: list[dict[str, str]] | None = None,
    deep_link: str | None = None,
) -> bool:
    """Post an Adaptive Card to a Teams webhook. Returns True on success."""
    color_map = {"info": "accent", "warning": "warning", "critical": "attention"}
    color = color_map.get(severity, "accent")

    body: list[dict[str, Any]] = [
        {"type": "TextBlock", "size": "Medium", "weight": "Bolder", "text": title, "color": color},
        {"type": "TextBlock", "text": message, "wrap": True},
    ]

    if facts:
        body.append({
            "type": "FactSet",
            "facts": [{"title": f["title"], "value": f["value"]} for f in facts],
        })

    actions = []
    if deep_link:
        actions.append({
            "type": "Action.OpenUrl",
            "title": "View in Beacon",
            "url": deep_link,
        })

    payload = {
        "type": "message",
        "attachments": [{
            "contentType": "application/vnd.microsoft.card.adaptive",
            "content": {
                "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                "type": "AdaptiveCard",
                "version": "1.4",
                "body": body,
                "actions": actions,
            },
        }],
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            for attempt in range(3):
                try:
                    resp = await client.post(webhook_url, json=payload)
                    if resp.status_code < 300:
                        logger.info("teams_alert_sent", title=title, severity=severity)
                        return True
                    logger.warning(
                        "teams_alert_failed",
                        attempt=attempt + 1,
                        status=resp.status_code,
                    )
                except httpx.TimeoutException:
                    logger.warning("teams_alert_timeout", attempt=attempt + 1)
    except Exception as exc:
        logger.warning("teams_alert_error", error=str(exc))
    return False
