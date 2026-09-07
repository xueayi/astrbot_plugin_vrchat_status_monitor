"""对比新旧状态，检测变化."""

from __future__ import annotations

from dataclasses import dataclass

# Statuspage 状态枚举的中文标签。只对枚举字段做精确匹配，自由文本
# （如事件正文）不做任何子串替换，以免破坏原文。
STATUS_LABELS: dict[str, str] = {
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


def label(value: object) -> str:
    """返回状态枚举值的中文标签，未知值原样返回。"""
    return STATUS_LABELS.get(str(value or ""), str(value or ""))


@dataclass
class ChangeEvent:
    """状态变化事件."""

    type: str  # "status" | "component" | "incident" | "maintenance"
    title: str
    details: str


def detect(old: dict | None, new: dict) -> list[ChangeEvent]:
    """比较新旧 summary.json 数据，返回变化事件列表。首次运行时 old 为 None，返回空列表。"""
    if old is None:
        return []

    changes: list[ChangeEvent] = []

    changes.extend(_detect_status(old.get("status", {}), new.get("status", {})))
    changes.extend(
        _detect_components(old.get("components", []), new.get("components", []))
    )
    changes.extend(
        _detect_incidents(old.get("incidents", []), new.get("incidents", []))
    )
    changes.extend(
        _detect_maintenances(
            old.get("scheduled_maintenances", []),
            new.get("scheduled_maintenances", []),
        )
    )

    return changes


def _detect_status(old_status: dict, new_status: dict) -> list[ChangeEvent]:
    old_ind = old_status.get("indicator", "")
    new_ind = new_status.get("indicator", "")
    old_desc = old_status.get("description", "")
    new_desc = new_status.get("description", "")

    if old_ind != new_ind or old_desc != new_desc:
        return [
            ChangeEvent(
                type="status",
                title="整体状态变更",
                details=f"{label(old_desc)} → {label(new_desc)}",
            )
        ]
    return []


def _detect_components(old_comps: list, new_comps: list) -> list[ChangeEvent]:
    events: list[ChangeEvent] = []
    old_by_id = {c["id"]: c for c in old_comps if isinstance(c, dict) and "id" in c}

    for comp in new_comps:
        if not isinstance(comp, dict) or "id" not in comp:
            continue
        cid = comp["id"]
        old_comp = old_by_id.get(cid)
        if old_comp and old_comp.get("status") != comp.get("status"):
            events.append(
                ChangeEvent(
                    type="component",
                    title=f"组件状态变更: {comp.get('name', cid)}",
                    details=f"{label(old_comp.get('status', '?'))} → {label(comp.get('status', '?'))}",
                )
            )

    return events


def _detect_incidents(old_list: list, new_list: list) -> list[ChangeEvent]:
    events: list[ChangeEvent] = []
    old_by_id = {i["id"]: i for i in old_list if isinstance(i, dict) and "id" in i}
    new_ids = {i["id"] for i in new_list if isinstance(i, dict) and "id" in i}

    for inc in new_list:
        if not isinstance(inc, dict) or "id" not in inc:
            continue
        iid = inc["id"]
        old_inc = old_by_id.get(iid)

        if old_inc is None:
            events.append(
                ChangeEvent(
                    type="incident",
                    title="新增事件",
                    details=(
                        f"事件: {inc.get('name', iid)}\n"
                        f"状态: {label(inc.get('status', '?'))}\n"
                        f"影响: {label(inc.get('impact', '?'))}"
                    ),
                )
            )
        else:
            if old_inc.get("status") != inc.get("status"):
                events.append(
                    ChangeEvent(
                        type="incident",
                        title=f"事件状态变更: {inc.get('name', iid)}",
                        details=(
                            f"状态: {label(old_inc.get('status', '?'))} → "
                            f"{label(inc.get('status', '?'))}"
                        ),
                    )
                )

            old_updates = len(old_inc.get("incident_updates", []))
            new_updates = len(inc.get("incident_updates", []))
            if new_updates > old_updates:
                latest = inc["incident_updates"][-1]
                events.append(
                    ChangeEvent(
                        type="incident",
                        title=f"事件更新: {inc.get('name', iid)}",
                        details=(
                            f"更新: {latest.get('body', '')}\n"
                            f"状态: {label(latest.get('status', '?'))}"
                        ),
                    )
                )

    # summary.json 的 incidents 只包含未解决事件，旧快照里有而新快照没有
    # 即视为已解决。
    for iid, old_inc in old_by_id.items():
        if iid not in new_ids:
            events.append(
                ChangeEvent(
                    type="incident",
                    title=f"事件已解决: {old_inc.get('name', iid)}",
                    details=f"状态: {label(old_inc.get('status', '?'))} → 已解决",
                )
            )

    return events


def _detect_maintenances(old_list: list, new_list: list) -> list[ChangeEvent]:
    events: list[ChangeEvent] = []
    old_by_id = {m["id"]: m for m in old_list if isinstance(m, dict) and "id" in m}
    new_ids = {m["id"] for m in new_list if isinstance(m, dict) and "id" in m}

    for mt in new_list:
        if not isinstance(mt, dict) or "id" not in mt:
            continue
        mid = mt["id"]
        if mid not in old_by_id:
            events.append(
                ChangeEvent(
                    type="maintenance",
                    title="新增计划维护",
                    details=(
                        f"维护: {mt.get('name', mid)}\n"
                        f"状态: {label(mt.get('status', '?'))}\n"
                        f"影响: {label(mt.get('impact', '?'))}"
                    ),
                )
            )
        else:
            old_mt = old_by_id[mid]
            if old_mt.get("status") != mt.get("status"):
                events.append(
                    ChangeEvent(
                        type="maintenance",
                        title=f"维护状态变更: {mt.get('name', mid)}",
                        details=(
                            f"状态: {label(old_mt.get('status', '?'))} → "
                            f"{label(mt.get('status', '?'))}"
                        ),
                    )
                )

    # 计划维护完成或取消后会从 scheduled_maintenances 中移除。
    for mid, old_mt in old_by_id.items():
        if mid not in new_ids:
            events.append(
                ChangeEvent(
                    type="maintenance",
                    title=f"计划维护已结束: {old_mt.get('name', mid)}",
                    details=f"状态: {label(old_mt.get('status', '?'))} → 已结束",
                )
            )

    return events
