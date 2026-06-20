from __future__ import annotations

import asyncio
import json
import uuid
from typing import Any, ClassVar

from maibot_sdk import Field, MaiBotPlugin, PluginConfigBase, Tool
from maibot_sdk.types import ToolParameterInfo, ToolParamType


class GatewaySection(PluginConfigBase):
    __ui_label__: ClassVar[str] = "OpenClaw 网关"
    __ui_order__: ClassVar[int] = 0

    url: str = Field(
        default="ws://127.0.0.1:18789",
        description="OpenClaw Gateway WebSocket 地址",
        json_schema_extra={
            "label": "网关地址",
            "placeholder": "ws://192.168.1.100:18789",
        },
    )
    token: str = Field(
        default="",
        description="Gateway 认证令牌",
        json_schema_extra={"label": "认证令牌", "placeholder": "输入 Gateway token"},
    )
    timeout_seconds: int = Field(
        default=300,
        description="任务执行超时时间（秒）",
        json_schema_extra={"label": "任务超时", "placeholder": "300"},
    )


class SkillsSection(PluginConfigBase):
    __ui_label__: ClassVar[str] = "技能开关"
    __ui_order__: ClassVar[int] = 1

    investigate_enabled: bool = Field(default=True, description="启用调试分析技能")
    ceo_review_enabled: bool = Field(default=True, description="启用规划审查技能")
    office_hours_enabled: bool = Field(default=True, description="启用头脑风暴技能")
    retro_enabled: bool = Field(default=True, description="启用工程回顾技能")


class OpenClawPluginConfig(PluginConfigBase):
    gateway: GatewaySection = Field(default_factory=GatewaySection)
    skills: SkillsSection = Field(default_factory=SkillsSection)


SKILL_PROMPTS: dict[str, str] = {
    "investigate": (
        "你是一个系统调试专家。请根据以下信息进行根因分析，"
        "输出包含：症状描述、根因分析、修复建议、复现步骤、相关注意事项。"
    ),
    "ceo_review": (
        "你是一个 CEO 级规划审查专家。请根据以下计划进行审查，"
        "输出包含：架构评估、错误处理映射、安全威胁模型、"
        "数据流与边界情况、性能与可观测性、部署与回滚策略、测试覆盖评估。"
    ),
    "office_hours": (
        "你是一个 YC 创业导师。请根据以下产品想法进行评估，"
        "输出包含：问题理解、需求真实性验证、目标用户画像、"
        "竞品分析、最小可行方案建议、潜在风险、下一步行动。"
    ),
    "retro": (
        "你是一个工程回顾专家。请根据以下工作数据进行分析，"
        "输出包含：工作总结、做得好的方面、需要改进的方面、行动项与优先级。"
    ),
}


class OpenClawSkillsPlugin(MaiBotPlugin):
    config_model: ClassVar[type[PluginConfigBase] | None] = OpenClawPluginConfig

    async def on_load(self) -> None:
        self.ctx.logger.info("OpenClaw 技能桥接插件已加载")

    async def on_unload(self) -> None:
        self.ctx.logger.info("OpenClaw 技能桥接插件已卸载")

    async def on_config_update(
        self, scope: str, config_data: dict[str, Any], version: str
    ) -> None:
        if scope == "self":
            self.ctx.logger.info("配置已更新: version=%s", version)
        del config_data
        del scope

    @Tool(
        "openclaw_investigate",
        description="将错误信息发送给远程 OpenClaw 智能体进行根因分析。"
        "当遇到难以排查的 Bug、复杂错误栈或不确定根因的问题时使用。",
        parameters=[
            ToolParameterInfo(
                name="error_description",
                param_type=ToolParamType.STRING,
                description="错误简要描述，用一句话概括发生了什么问题",
                required=True,
            ),
            ToolParameterInfo(
                name="stack_trace",
                param_type=ToolParamType.STRING,
                description="错误栈追踪或完整错误日志",
                required=False,
            ),
            ToolParameterInfo(
                name="reproduction_steps",
                param_type=ToolParamType.STRING,
                description="复现步骤，描述如何重现该问题",
                required=False,
            ),
            ToolParameterInfo(
                name="additional_context",
                param_type=ToolParamType.STRING,
                description="额外上下文信息，如环境版本、最近改动、相关文件等",
                required=False,
            ),
        ],
    )
    async def tool_investigate(
        self,
        error_description: str,
        stack_trace: str = "",
        reproduction_steps: str = "",
        additional_context: str = "",
        **kwargs: Any,
    ) -> dict[str, Any]:
        del kwargs
        if not self.config.skills.investigate_enabled:
            return {"success": False, "error": "调试分析技能已禁用"}
        return await self._execute_openclaw_task(
            skill="investigate",
            params={
                "错误描述": error_description,
                "栈追踪": stack_trace,
                "复现步骤": reproduction_steps,
                "额外上下文": additional_context,
            },
        )

    @Tool(
        "openclaw_ceo_review",
        description="将计划文档发送给远程 OpenClaw 智能体进行 CEO 级审查。"
        "当需要审查架构设计、功能规划或技术方案时使用。",
        parameters=[
            ToolParameterInfo(
                name="plan_title",
                param_type=ToolParamType.STRING,
                description="计划标题，概括审查对象",
                required=True,
            ),
            ToolParameterInfo(
                name="plan_content",
                param_type=ToolParamType.STRING,
                description="完整计划内容，包括背景、方案、技术选型等",
                required=True,
            ),
            ToolParameterInfo(
                name="review_focus",
                param_type=ToolParamType.STRING,
                description="审查重点方向，如架构、安全、性能等",
                required=False,
            ),
        ],
    )
    async def tool_ceo_review(
        self,
        plan_title: str,
        plan_content: str,
        review_focus: str = "",
        **kwargs: Any,
    ) -> dict[str, Any]:
        del kwargs
        if not self.config.skills.ceo_review_enabled:
            return {"success": False, "error": "规划审查技能已禁用"}
        return await self._execute_openclaw_task(
            skill="ceo_review",
            params={
                "计划标题": plan_title,
                "计划内容": plan_content,
                "审查重点": review_focus,
            },
        )

    @Tool(
        "openclaw_office_hours",
        description="将产品想法发送给远程 OpenClaw 智能体进行 YC 式评估。"
        "当需要验证产品想法、讨论需求或评估方向时使用。",
        parameters=[
            ToolParameterInfo(
                name="idea_title",
                param_type=ToolParamType.STRING,
                description="想法标题",
                required=True,
            ),
            ToolParameterInfo(
                name="idea_description",
                param_type=ToolParamType.STRING,
                description="想法详细描述，包括要解决的问题、目标用户、方案",
                required=True,
            ),
            ToolParameterInfo(
                name="target_users",
                param_type=ToolParamType.STRING,
                description="目标用户群体描述",
                required=False,
            ),
            ToolParameterInfo(
                name="existing_solutions",
                param_type=ToolParamType.STRING,
                description="现有替代方案或竞品",
                required=False,
            ),
        ],
    )
    async def tool_office_hours(
        self,
        idea_title: str,
        idea_description: str,
        target_users: str = "",
        existing_solutions: str = "",
        **kwargs: Any,
    ) -> dict[str, Any]:
        del kwargs
        if not self.config.skills.office_hours_enabled:
            return {"success": False, "error": "头脑风暴技能已禁用"}
        return await self._execute_openclaw_task(
            skill="office_hours",
            params={
                "想法标题": idea_title,
                "想法描述": idea_description,
                "目标用户": target_users,
                "现有方案": existing_solutions,
            },
        )

    @Tool(
        "openclaw_retro",
        description="将工作数据发送给远程 OpenClaw 智能体进行工程回顾分析。"
        "当需要分析团队工作、总结迭代经验或制定改进计划时使用。",
        parameters=[
            ToolParameterInfo(
                name="period",
                param_type=ToolParamType.STRING,
                description="回顾周期，如 '2026年6月第三周'",
                required=True,
            ),
            ToolParameterInfo(
                name="work_summary",
                param_type=ToolParamType.STRING,
                description="工作总结，包括完成的功能、修复的 Bug、合并的 PR 等",
                required=True,
            ),
            ToolParameterInfo(
                name="metrics",
                param_type=ToolParamType.STRING,
                description="量化指标，如提交数、PR 数、问题数等",
                required=False,
            ),
            ToolParameterInfo(
                name="highlights",
                param_type=ToolParamType.STRING,
                description="亮点或特别事项",
                required=False,
            ),
        ],
    )
    async def tool_retro(
        self,
        period: str,
        work_summary: str,
        metrics: str = "",
        highlights: str = "",
        **kwargs: Any,
    ) -> dict[str, Any]:
        del kwargs
        if not self.config.skills.retro_enabled:
            return {"success": False, "error": "工程回顾技能已禁用"}
        return await self._execute_openclaw_task(
            skill="retro",
            params={
                "回顾周期": period,
                "工作总结": work_summary,
                "量化指标": metrics,
                "亮点事项": highlights,
            },
        )

    async def _execute_openclaw_task(
        self, skill: str, params: dict[str, str]
    ) -> dict[str, Any]:
        cfg = self.config
        gateway_url = cfg.gateway.url
        token = cfg.gateway.token
        timeout_s = cfg.gateway.timeout_seconds

        if not gateway_url:
            return {"success": False, "error": "未配置 OpenClaw 网关地址"}
        if not token:
            return {"success": False, "error": "未配置 OpenClaw 认证令牌"}

        skill_prompt = SKILL_PROMPTS.get(skill, "")
        param_lines = "\n".join(f"{k}: {v}" for k, v in params.items() if v)
        task_message = f"{skill_prompt}\n\n## 输入数据\n\n{param_lines}"

        ws: Any = None
        try:
            import websockets

            ws = await asyncio.wait_for(
                websockets.connect(gateway_url, ping_interval=30), timeout=15
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
                    "auth": {"token": token, "password": token},
                },
            }
            await ws.send(json.dumps(connect_req))
            connect_resp = json.loads(await asyncio.wait_for(ws.recv(), timeout=10))
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
                {"title": f"maibot-{skill}-{uuid.uuid4().hex[:8]}"},
            )
            if not sess.get("ok"):
                return {"success": False, "error": f"会话创建失败: {sess}"}
            session_key = sess["payload"]["key"]

            send = await gw_call(
                "sessions.send",
                {"key": session_key, "message": task_message, "deliver": False},
            )
            if not send.get("ok"):
                return {"success": False, "error": f"任务发送失败: {send}"}

            run_id = send["payload"].get("runId", "")
            wait_params: dict[str, Any] = {
                "sessionKey": session_key,
                "timeoutMs": timeout_s * 1000,
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
                raw = await asyncio.wait_for(ws.recv(), timeout=timeout_s + 10)
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
                    return {
                        "success": True,
                        "skill": skill,
                        "response": response_text,
                    }

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
