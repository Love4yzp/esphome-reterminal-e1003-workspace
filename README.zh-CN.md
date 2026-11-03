# reTerminal E1003 墨水屏智能面板 (Home Assistant / ESPHome)

基于 **reTerminal E1003** 墨水屏(1872×1404、16 级灰度、IT8951)+ **Seeed XIAO
ESP32-S3** 的 ESPHome 固件模板:设计稿位图作为静态 UI,少量动态卡片单独局部刷新,
触摸热区调用 Home Assistant。

整个仓库围绕两个原则:

**设计稿是源文件,不是代码。** 屏幕几何、字体、触摸热区统一放在
[`layout/ui_layout.yaml`](layout/ui_layout.yaml),由 `tools/layout_to_h.py` 编译成
C++ 头文件。ESPHome 的 packages 里不允许出现任何一个像素数值。

**行为是配置,不是固件。** 按钮控制哪个实体、卡片显示什么内容,
全部是普通的 Home Assistant `text` 实体。换个灯 = 一次服务调用,**不用重编译、不用
OTA**。

[English README](README.md)

## 核心特性

- 单张设计稿 PNG 编译为 4bpp PackBits-RLE 位图，开机以 `GC16` 完整绘制静态 UI。
- 动态卡片按需以 `DU` 局部刷新，并通过 `ui_refresh` 防抖合并突发状态更新。
- 触摸热区采用 YAML 数据表定义，无需编写分支判断代码。
- 构建期校验热区边界、字体文件与实体 ID，提前拦截布局错误。
- 读取板载 SHT4x 温湿度传感器与 PCF8563 RTC，开机由 Home Assistant 同步校时。
- 绿色实体键只负责完整刷新与安全重启等屏幕级操作。
- 通过屏幕网络区域发起 Wi-Fi 重配，并使用二次点击确认避免误触。
- 按钮控制目标、服务动作与卡片文本通过 Home Assistant `text` 实体在运行时修改，免重新编译。
- 工具链由 `uv` 管理并锁版本,Linux/macOS/Windows 共用同一个构建入口
- 字体随仓库分发(`assets/fonts/`,SIL OFL 1.1):主机无需装字体,三平台字形一致

## 目录结构

```
e1003-dashboard.yaml            # 唯一正式固件入口
e1003-base.yaml                 # 共享 packages 组装
├── layout/
│   ├── ui_layout.yaml          # ← 唯一真源:热区、卡片、字体、调色板、刷新策略
│   └── generated/              # ← 生成物:ui_layout.h / fonts.yaml / policy.yaml
├── packages/
│   ├── core.yaml               # 身份与 ESP32 平台
│   ├── hardware.yaml           # SPI/I2C、蜂鸣器、SHT4x、PCF8563
│   ├── ui.yaml                 # 启动、脏标记、刷新和渲染
│   ├── interaction.yaml        # 运行时配置、GT911 和 HA 动作
│   ├── ha-direct-state.yaml    # 自定义构建可选的固定目标 adapter
│   └── ha-pull.yaml            # 可选:设备反向拉取 HA 的 JSON
├── src/
│   ├── e1003_render.h          # C++ 辅助函数（RLE 位图解码）
│   └── e1003_system.h          # Wi-Fi 定向重置辅助
├── assets/                     # 设计稿 PNG、生成的位图头文件、内置字体(assets/fonts/)
├── tools/                      # png_to_h.py、layout_to_h.py
├── ha/e1003_dashboard.yaml     # Home Assistant 包:转发脚本 + 示例自动化
├── docs/                       # 架构 / 配置 / 布局 / HA 集成 / 构建
└── scripts/                    # build.py(Linux / Windows / macOS 同一个入口)
```

详细固件分层与 packages 说明见 [docs/architecture.md](docs/architecture.md)。

源码构建和浏览器安装固件都不会写入 Wi-Fi 凭据、AP 密码、API key 或
Home Assistant 实体 ID。首次启动后，设备会发射开放配置热点；用户连接热点并访问
`192.168.4.1` 即可填写目标 Wi-Fi。同一份固件也保留 Improv Serial，作为额外的
USB 配网方式。

## 开发者快速开始

安装工具链依赖：

```bash
uv sync
```

然后直接编译并烧录零凭据默认固件：

```bash
uv run python scripts/build.py run
```

构建入口会在编译前自动生成布局文件，并在 Linux、Windows 与 macOS 上使用
同一套命令。完整的构建与烧录细节参见 [docs/build-and-flash.md](docs/build-and-flash.md)。

烧录完成后，连接名称以 `reterminal-e1003-` 开头的开放热点，访问
`192.168.4.1` 填写目标 Wi-Fi。随后在 Home Assistant 中添加设备
（**设置 → 设备与服务 → ESPHome**），
并将控制项指向目标实体：

```yaml
action: text.set_value
target:
  entity_id: text.e1003_smart_workspace_main_light_target
data:
  value: light.desk_lamp
```

配置保存后即刻生效，无需重新编译固件。所有运行时可配置项参见 [docs/configuration.md](docs/configuration.md)。

## 现成固件

不想自己编译?每个 tag 的 Release 都带现成固件,GitHub Pages 上还有一个浏览器刷机页
——插上 USB-C 就能在网页里直接烧录。见
[公共首次安装固件](docs/build-and-flash.md#public-first-install-image)。

然后在 Home Assistant 里添加设备,导入
`ha/blueprints/automation/e1003_light_sync.yaml`,选择面板的 target/state/value
实体和要控制的灯。全程没有重新编译。其他可运行时修改的内容见
**[docs/configuration.md](docs/configuration.md)**。

## 哪些能改、哪些要重编译

| 想改的内容 | 免重编译 | 方式 |
|---|:---:|---|
| 按钮控制哪个实体 | ✅ | `text..._main_light_target` |
| 卡片显示的状态/数值 | ✅ | `text..._main_light_state` / `_value` |
| 灯光按钮的自定义路由 | ✅ | `zone_script_hook` → HA 脚本 |
| Reachy 场景动作 | ✅ | `reachy_script_hook` → HA 脚本 |
| 按钮/卡片数量、位置、字体 | ❌ | `layout/ui_layout.yaml` + 设计稿 |
| 引脚、板型、面板型号、编译期默认目标 | ❌ | `packages/defaults.yaml` + `-s key value` |

## 文档指引

| 目标 | 参考文档 |
|---|---|
| 修改控制目标、通过 HA 驱动面板 | [docs/configuration.md](docs/configuration.md) |
| 移动按钮、添加卡片、更换设计稿 | [docs/ui-layout.md](docs/ui-layout.md) |
| 固件分层、脏标记机制与刷新协议 | [docs/architecture.md](docs/architecture.md) |
| Home Assistant 配置、路由脚本与 push/pull 方案 | [docs/ha-integration.md](docs/ha-integration.md) |
| 编译、烧录、排错与工具链说明 | [docs/build-and-flash.md](docs/build-and-flash.md) |
| Agent 工作指南与仓库规范 | [AGENTS.md](AGENTS.md) |

## 硬件

| 组件 | 规格 |
|---|---|
| 屏幕 | reTerminal E1003, IT8951, 1872×1404, 16 级灰度, SPI |
| 主控 | Seeed XIAO ESP32-S3, octal PSRAM, Arduino 框架 |
| 触摸 | GT911 (I²C), LEDC 驱动蜂鸣器反馈 |
| 传感器 | SHT4x (温湿度), PCF8563 (RTC + 电池备份) |

引脚定义在 `packages/defaults.yaml` 的 substitutions 里。

### 实体按键

| 按键 | 手势 | 功能 |
|---|---|---|
| 绿色键 | 单击 | 完整刷新 Dashboard |
| 绿色键 | 长按 3 秒 | 安全重启设备 |

## 许可

MIT,见 [LICENSE](LICENSE)。
