from __future__ import annotations

import asyncio
import json
import uuid
from typing import Any, ClassVar

from maibot_sdk import Field, MaiBotPlugin, PluginConfigBase, Tool
from maibot_sdk.types import ToolParameterInfo, ToolParamType


class GatewayConfig(PluginConfigBase):
    url: str = Field(
        default="ws://127.0.0.1:18789",
        description="OpenClaw Gateway WebSocket 地址",
        json_schema_extra={"label": "网关地址"},
    )
    token: str = Field(
        default="",
        description="Gateway 认证令牌",
        json_schema_extra={"label": "认证令牌"},
    )
    timeout_seconds: int = Field(
        default=300,
        description="任务执行超时时间（秒）",
        json_schema_extra={"label": "任务超时"},
    )


class OpenClawPluginConfig(PluginConfigBase):
    gateway: GatewayConfig = Field(default_factory=GatewayConfig)


class OpenClawSkillsPlugin(MaiBotPlugin):
    config_model: ClassVar[type[PluginConfigBase] | None] = OpenClawPluginConfig

    async def on_load(self) -> None:
        self.ctx.logger.info("OpenClaw 插件已加载")

    async def on_unload(self) -> None:
        self.ctx.logger.info("OpenClaw 插件已卸载")

    async def on_config_update(self, scope: str, config_data: dict, version: str) -> None:
        if scope == "self":
            self.ctx.logger.info("配置已更新: version=%s", version)

    @Tool(
        "openclaw_task",
        description="将复杂任务发送给远程 OpenClaw 智能体处理。"
        "当你遇到自己难以处理的问题（需要深入分析、长上下文推理、多步操作等）时使用。",
        parameters=[
            ToolParameterInfo(
                name="task_description",
                param_type=ToolParamType.STRING,
                description="描述你要 OpenClaw 帮你做什么，说清楚背景和要求即可",
                required=True,
            ),
        ],
    )
    async def tool_task(
        self, task_description: str, **kwargs: Any
    ) -> dict[str, Any]:
        del kwargs
        return await self._execute_openclaw_task(task_description)

    async def _execute_openclaw_task(self, task: str) -> dict[str, Any]:
        gw = self.config.gateway
        if not gw.url:
            return {"success": False, "error": "未配置 OpenClaw 网关地址"}
        if not gw.token:
            return {"success": False, "error": "未配置 OpenClaw 认证令牌"}

        ws: Any = None
        try:
            import websockets

            ws = await asyncio.wait_for(
                websockets.connect(gw.url, ping_interval=30), timeout=15
            )

            await asyncio.wait_for(ws.recv(), timeout=10)

            connect_req = {
                "type": "req",
                "id": uuid.uuid4().hex[:12],
                "method": "connect",
                "params": {
                    "minProtocol": 4,
                    "maxProtocol": 4,
                    "client": {
                        "id": "maibot-plugin",
                        "version": "1.0.0",
                        "platform": "node",
                        "mode": "operator",
                    },
                    "role": "operator",
                    "scopes": ["operator.read", "operator.write"],
                    "auth": {"token": gw.token, "password": gw.token},
                },
            }
            await ws.send(json.dumps(connect_req))
            connect_resp = json.loads(
                await asyncio.wait_for(ws.recv(), timeout=10)
            )
            if not connect_resp.get("ok"):
                return {
                    "success": False,
                    "error": "OpenClaw 网关认证失败，请检查 token",
                }

            async def gw_call(
                method: str, params: dict, timeout: float = 30
            ) -> dict:
                req = {
                    "type": "req",
                    "id": uuid.uuid4().hex[:12],
                    "method": method,
                    "params": params,
                }
                await ws.send(json.dumps(req))
                raw = await asyncio.wait_for(ws.recv(), timeout=timeout)
                return json.loads(raw)

            sess = await gw_call(
                "sessions.create",
                {"title": f"maibot-task-{uuid.uuid4().hex[:8]}"},
            )
            if not sess.get("ok"):
                return {"success": False, "error": f"会话创建失败: {sess}"}
            session_key = sess["payload"]["key"]

            send = await gw_call(
                "sessions.send",
                {
                    "key": session_key,
                    "message": task,
                    "deliver": False,
                },
            )
            if not send.get("ok"):
                return {"success": False, "error": f"任务发送失败: {send}"}

            run_id = send["payload"].get("runId", "")
            wait_params: dict[str, Any] = {
                "sessionKey": session_key,
                "timeoutMs": gw.timeout_seconds * 1000,
            }
            if run_id:
                wait_params["runId"] = run_id

            wait_req = {
                "type": "req",
                "id": uuid.uuid4().hex[:12],
                "method": "agent.wait",
                "params": wait_params,
            }
            await ws.send(json.dumps(wait_req))

            while True:
                raw = await asyncio.wait_for(
                    ws.recv(), timeout=gw.timeout_seconds + 10
                )
                msg = json.loads(raw)
                if msg.get("type") == "res" and msg.get("id") == wait_req["id"]:
                    if not msg.get("ok"):
                        return {
                            "success": False,
                            "error": f"任务执行失败: {msg}",
                        }
                    payload = msg.get("payload", {})
                    response_text = (
                        payload.get("response")
                        or payload.get("text")
                        or payload.get("content")
                        or str(payload)
                    )
                    return {"success": True, "response": response_text}

        except ImportError:
            return {
                "success": False,
                "error": "缺少 websockets 库，请运行: uv pip install websockets",
            }
        except asyncio.TimeoutError:
            return {"success": False, "error": "连接 OpenClaw 网关超时"}
        except Exception as exc:
            self.ctx.logger.error(
                "OpenClaw 任务执行异常: %s", exc, exc_info=True
            )
            return {"success": False, "error": f"执行异常: {exc}"}
        finally:
            if ws is not None:
                try:
                    await ws.close()
                except Exception:
                    pass


def create_plugin() -> OpenClawSkillsPlugin:
    return OpenClawSkillsPlugin()
