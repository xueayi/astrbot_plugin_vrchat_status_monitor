"""将变化事件渲染为纯文本消息."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from .detector import ChangeEvent, label

# 消息中各组件的排序优先级
_TYPE_ORDER = {"status": 0, "component": 1, "incident": 2, "maintenance": 3}

_TYPE_SECTION_TITLE = {
    "status": "【VRChat 状态】",
    "component": "【VRChat 组件】",
    "incident": "【VRChat 事件】",
    "maintenance": "【VRChat 维护】",
}


def format_changes(changes: list[ChangeEvent], utc_offset: int = 8) -> str:
    """将变化列表渲染为一条纯文本消息。空列表返回空字符串。

    Args:
        changes: 变化事件列表。
        utc_offset: 消息时间戳使用的 UTC 偏移小时数。

    Returns:
        渲染后的纯文本；changes 为空时返回空字符串。
    """
    if not changes:
        return ""

    sorted_changes = sorted(changes, key=lambda e: _TYPE_ORDER.get(e.type, 99))

    sections: list[str] = []
    current_type: str | None = None

    for event in sorted_changes:
        if event.type != current_type:
            current_type = event.type
            sections.append(_TYPE_SECTION_TITLE.get(event.type, f"【{event.type}】"))
        sections.append(f"{event.title}: {event.details}")

    sections.append(
        f"更新时间：{datetime.now(timezone(timedelta(hours=utc_offset))).strftime('%Y-%m-%d %H:%M:%S')}"
        f" (UTC{utc_offset:+d})"
    )

    return "\n".join(sections)


def format_summary(summary: dict, utc_offset: int = 8) -> str:
    """将当前 summary.json 渲染为一条摘要消息。

    Args:
        summary: summary.json 解析结果。
        utc_offset: 消息时间戳使用的 UTC 偏移小时数。

    Returns:
        渲染后的纯文本摘要。
    """
    status = summary.get("status", {})
    lines = [
        "【VRChat 当前状态】",
        f"整体：{label(status.get('description', '未知'))}（{label(status.get('indicator', '未知'))}）",
    ]

    comps = summary.get("components", [])
    if comps:
        lines.append("组件：")
        for comp in comps:
            if isinstance(comp, dict):
                lines.append(
                    f"  {comp.get('name', '?')}：{label(comp.get('status', '?'))}"
                )

    incidents = summary.get("incidents", [])
    if incidents:
        lines.append("进行中事件：")
        for inc in incidents:
            if isinstance(inc, dict):
                lines.append(
                    f"  {inc.get('name', '?')}（{label(inc.get('status', '?'))}）"
                )

    maintenances = summary.get("scheduled_maintenances", [])
    if maintenances:
        lines.append("计划维护：")
        for mt in maintenances:
            if isinstance(mt, dict):
                lines.append(
                    f"  {mt.get('name', '?')}（{label(mt.get('status', '?'))}）"
                )

    lines.append(
        f"查询时间：{datetime.now(timezone(timedelta(hours=utc_offset))).strftime('%Y-%m-%d %H:%M:%S')}"
        f" (UTC{utc_offset:+d})"
    )

    return "\n".join(lines)
