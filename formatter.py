"""将变化事件渲染为纯文本消息."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from .detector import ChangeEvent

# 状态值中英文对照
_STATUS_LABELS: dict[str, str] = {
    "none": "正常",
    "minor": "轻微故障",
    "major": "重大故障",
    "critical": "严重故障",
    "operational": "正常运行",
    "degraded_performance": "性能下降",
    "partial_outage": "部分中断",
    "major_outage": "严重中断",
    "under_maintenance": "维护中",
    "investigating": "调查中",
    "identified": "已确认",
    "monitoring": "监控中",
    "resolved": "已解决",
    "scheduled": "已计划",
    "in_progress": "进行中",
    "completed": "已完成",
    "All Systems Operational": "所有系统正常",
    "Partial System Outage": "部分系统中断",
    "Major Service Disruption": "重大服务中断",
    "Minor Service Disruption": "轻微服务中断",
}

# 消息中各组件的排序优先级
_TYPE_ORDER = {"status": 0, "component": 1, "incident": 2, "maintenance": 3}

_TYPE_SECTION_TITLE = {
    "status": "【VRChat 状态】",
    "component": "【VRChat 组件】",
    "incident": "【VRChat 事件】",
    "maintenance": "【VRChat 维护】",
}


def _label(status: str) -> str:
    return _STATUS_LABELS.get(status, status)


def format_changes(changes: list[ChangeEvent]) -> str:
    """将变化列表渲染为一条纯文本消息。空列表返回空字符串。"""
    if not changes:
        return ""

    sorted_changes = sorted(changes, key=lambda e: _TYPE_ORDER.get(e.type, 99))

    sections: list[str] = []
    current_type: str | None = None

    for event in sorted_changes:
        if event.type != current_type:
            current_type = event.type
            sections.append(_TYPE_SECTION_TITLE.get(event.type, f"【{event.type}】"))

        # 长键优先替换，避免 major 误替 major_outage
        details_with_labels = event.details
        for eng, cn in sorted(_STATUS_LABELS.items(), key=lambda x: -len(x[0])):
            details_with_labels = details_with_labels.replace(eng, cn)
        sections.append(f"{event.title}: {details_with_labels}")

    now = datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M:%S")
    sections.append(f"更新时间：{now} (UTC+8)")

    return "\n".join(sections)


def format_summary(summary: dict) -> str:
    """将当前 summary.json 渲染为一条摘要消息。"""
    status = summary.get("status", {})
    lines = [
        "【VRChat 当前状态】",
        f"整体：{_label(status.get('description', '未知'))}（{_label(status.get('indicator', '未知'))}）",
    ]

    comps = summary.get("components", [])
    if comps:
        lines.append("组件：")
        for comp in comps:
            if isinstance(comp, dict):
                lines.append(f"  {comp.get('name', '?')}：{_label(comp.get('status', '?'))}")

    incidents = summary.get("incidents", [])
    if incidents:
        lines.append("进行中事件：")
        for inc in incidents:
            if isinstance(inc, dict):
                lines.append(f"  {inc.get('name', '?')}（{_label(inc.get('status', '?'))}）")

    maintenances = summary.get("scheduled_maintenances", [])
    if maintenances:
        lines.append("计划维护：")
        for mt in maintenances:
            if isinstance(mt, dict):
                lines.append(f"  {mt.get('name', '?')}（{_label(mt.get('status', '?'))}）")

    now = datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M:%S")
    lines.append(f"查询时间：{now} (UTC+8)")

    return "\n".join(lines)
