"""VRChat 官方服务状态监控插件."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from astrbot.api import AstrBotConfig, logger, star
from astrbot.api.event import AstrMessageEvent, MessageChain, filter
from astrbot.core.utils.astrbot_path import get_astrbot_plugin_data_path

from . import detector, fetcher, formatter, state_store

PLUGIN_NAME = "astrbot_plugin_vrchat_status_monitor"
KV_TARGETS_KEY = "bound_sessions"
MIN_POLL_INTERVAL = 60


class Main(star.Star):
    """VRChat 服务状态监控：轮询 status.vrchat.com，变化时推送到绑定会话。"""

    def __init__(self, context: star.Context, config: AstrBotConfig) -> None:
        super().__init__(context, config)
        self.config = config
        self.state_path = Path(get_astrbot_plugin_data_path()) / PLUGIN_NAME / "state.json"
        self._poll_task: asyncio.Task | None = None
        self._stop_event: asyncio.Event | None = None

    @filter.on_astrbot_loaded()
    async def on_loaded(self, *args, **kwargs) -> None:
        """启动轮询循环."""
        if self.config.get("enabled", True):
            self._start_polling()

    async def terminate(self) -> None:
        """停止轮询."""
        if self._stop_event:
            self._stop_event.set()
        if self._poll_task and not self._poll_task.done():
            self._poll_task.cancel()

    def _start_polling(self) -> None:
        if self._poll_task and not self._poll_task.done():
            return
        self._stop_event = asyncio.Event()
        interval = max(MIN_POLL_INTERVAL, int(self.config.get("poll_interval_seconds", 300)))
        self._poll_task = asyncio.create_task(self._poll_loop(interval))

    async def _poll_loop(self, interval: int) -> None:
        while True:
            try:
                await self.check_once()
            except Exception as e:
                logger.error(f"[{PLUGIN_NAME}] 检测循环异常: {e}")
            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=interval)
                return
            except asyncio.TimeoutError:
                pass

    async def check_once(self) -> int:
        """执行一轮检测，返回发现的变更数。首轮只保存状态不推送。"""
        old = state_store.load(self.state_path)
        new = await fetcher.fetch(self.config.get("proxy", "") or None)
        if new is None:
            return -1

        changes = detector.detect(None if old is None else old, new)
        state_store.save(self.state_path, new)

        if not changes:
            return 0

        text = formatter.format_changes(changes)
        targets = await self._targets()
        for umo in targets:
            try:
                await self.context.send_message(umo, MessageChain().message(text))
            except Exception as e:
                logger.error(f"[{PLUGIN_NAME}] 推送失败 {umo}: {e}")
        return len(changes)

    async def _targets(self) -> list[str]:
        bound = await self.get_kv_data(KV_TARGETS_KEY, [])
        if not isinstance(bound, list):
            bound = []
        return [str(t) for t in bound if str(t).strip()]

    @filter.command_group("vrcstatus")
    def vrcstatus(self):
        """VRChat 状态监控指令组。"""

    @vrcstatus.command("bind")
    async def cmd_bind(self, event: AstrMessageEvent):
        """绑定当前会话为推送目标。"""
        umo = event.unified_msg_origin
        targets = await self.get_kv_data(KV_TARGETS_KEY, [])
        if not isinstance(targets, list):
            targets = []
        if umo not in targets:
            targets.append(umo)
            await self.put_kv_data(KV_TARGETS_KEY, targets)
            yield event.plain_result("已绑定当前会话为 VRChat 状态推送目标。")
        else:
            yield event.plain_result("当前会话已绑定。")

    @vrcstatus.command("unbind")
    async def cmd_unbind(self, event: AstrMessageEvent):
        """解除当前会话绑定。"""
        umo = event.unified_msg_origin
        targets = await self.get_kv_data(KV_TARGETS_KEY, [])
        if not isinstance(targets, list):
            targets = []
        if umo in targets:
            targets.remove(umo)
            await self.put_kv_data(KV_TARGETS_KEY, targets)
            yield event.plain_result("已解除当前会话绑定。")
        else:
            yield event.plain_result("当前会话未绑定。")

    @vrcstatus.command("status")
    async def cmd_status(self, event: AstrMessageEvent):
        """查询 VRChat 当前状态摘要。"""
        summary = await fetcher.fetch(self.config.get("proxy", "") or None)
        if summary is None:
            yield event.plain_result("VRChat 状态查询失败，请稍后再试。")
            return
        yield event.plain_result(formatter.format_summary(summary))

    @vrcstatus.command("check")
    async def cmd_check(self, event: AstrMessageEvent):
        """立即执行一次变更检测（调试用）。"""
        count = await self.check_once()
        if count < 0:
            yield event.plain_result("检测失败：拉取 VRChat 状态失败。")
        elif count == 0:
            yield event.plain_result("检测完成，无状态变化。")
        else:
            yield event.plain_result(f"检测到 {count} 个变化，已推送到绑定会话。")
