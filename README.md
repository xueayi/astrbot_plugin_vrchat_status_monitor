# astrbot_plugin_vrchat_status_monitor

VRChat 官方服务状态监控插件（AstrBot）。

定期拉取 [status.vrchat.com](https://status.vrchat.com/api/v2/summary.json)（Statuspage 格式），对比上一轮快照，检测到变化（整体状态 / 组件状态 / 事件 incident / 计划维护）时推送到绑定的会话。

## 指令

| 指令 | 说明 |
| --- | --- |
| `/vrcstatus bind` | 绑定当前会话为推送目标 |
| `/vrcstatus unbind` | 解绑当前会话 |
| `/vrcstatus status` | 查询当前 VRChat 状态摘要 |
| `/vrcstatus check` | 立即执行一次变更检测（调试） |

## 配置（WebUI）

- `poll_interval_seconds`：轮询间隔，默认 300 秒（最小 60）
- `proxy`：HTTP 代理（可选）
- `utc_offset_hours`：消息时间戳的时区偏移，默认 8（UTC+8）
- `enabled`：是否启用自动轮询

## 说明

- 推送失败时会保留本轮检测结果，下一轮自动重试，不会丢失变更。
- `/vrcstatus bind` 对会话内所有成员开放（状态页是公开数据）；如需限制，可在 AstrBot 中为该指令配置权限。

## 安装

放入 AstrBot `data/plugins/` 目录（或在插件市场安装），依赖 `aiohttp`（会自动安装）。

## License

AGPL-3.0（沿用仓库模板的 LICENSE）。
