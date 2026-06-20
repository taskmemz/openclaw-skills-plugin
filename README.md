# OpenClaw 任务桥接

让 MaiBot 把复杂任务丢给远程 OpenClaw 处理。

## 安装

```bash
git clone --filter=blob:none --sparse https://github.com/taskmemz/openclaw-skills-plugin.git /MaiMBot/plugins/openclaw-skills
cd /MaiMBot/plugins/openclaw-skills && rm -rf .git
uv pip install websockets
```

重启 MaiBot。

## 配置

在 WebUI **系统设置 → 插件 → openclaw-skills** 填入：

| 字段 | 说明 |
|---|---|
| 网关地址 | OpenClaw Gateway 地址，默认 `ws://127.0.0.1:18789` |
| 认证令牌 | token 模式用的密钥 |
| 认证密码 | password 模式用的密码，留空则使用 token 的值 |
| 任务超时 | 单次任务超时秒数，默认 300 |

## 提供 1 个工具

| 工具 | Maisaka 什么时候调用 |
|---|---|
| `openclaw_task` | 遇到自己搞不定的复杂问题时，把任务描述丢给 OpenClaw |

Maisaka 把任务原文发给 OpenClaw，OpenClaw 处理完返回结果，就这么简单。
