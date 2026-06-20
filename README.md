# OpenClaw Skills Plugin

将 MaiBot 无法处理的复杂任务委托给远程 OpenClaw 智能体执行。

## 安装

将本目录复制到 MaiBot 的 `plugins/` 目录下：

```bash
git clone --filter=blob:none --sparse https://github.com/taskmemz/openclaw-skills-plugin.git /tmp/oc-skills
cd /tmp/oc-skills
sparse-checkout set .  # 或直接 cp -r
cp -r * /MaiMBot/plugins/openclaw-skills/
cd / && rm -rf /tmp/oc-skills
```

或通过 MaiBot 的插件市场安装（如果已收录）。

然后安装依赖并重启：

```bash
cd /MaiMBot
uv pip install websockets
```

## 配置

在 WebUI **系统设置 → 插件 → openclaw-skills** 中填入：

| 字段 | 说明 |
|---|---|
| 网关地址 | `ws://你的OpenClaw地址:18789` |
| 认证令牌 | 你的 OpenClaw Gateway 密钥 |
| 任务超时 | 单次任务超时秒数（默认 300） |

或在 `config.toml` 中直接编辑：

```toml
[gateway]
url = "ws://127.0.0.1:18789"
token = "你的密钥"
timeout_seconds = 300
```

## 技能

| 工具 | 触发场景 |
|---|---|
| `openclaw_investigate` | 遇到难排查的 Bug、复杂错误栈时，OpenClaw 进行根因分析 |
| `openclaw_ceo_review` | 需要审查架构设计或技术方案时，OpenClaw 进行 CEO 级审查 |
| `openclaw_office_hours` | 需要验证产品想法时，OpenClaw 进行 YC 式评估 |
| `openclaw_retro` | 需要做工程回顾时，OpenClaw 进行回顾分析 |

## 前提条件

- OpenClaw Gateway 运行中且可通过 WebSocket 访问
- OpenClaw 已安装对应的 `maibot` skill（见 [maibot-openclaw-bridge](https://github.com/taskmemz/maibot-openclaw-bridge) 的 `openclaw-skill/` 目录）
