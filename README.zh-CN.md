# reTerminal E1003 墨水屏智能面板 (Home Assistant / ESPHome)

基于 **reTerminal E1003** 电子墨水屏（1872×1404、16 级灰度、IT8951）与 **Seeed XIAO ESP32-S3** 的 ESPHome 固件模板：以整屏设计稿位图作为静态 UI，通过局部刷新更新动态卡片，触摸热区直接与 Home Assistant 交互。

[English README](README.md)

## 核心特性

- 单张设计稿 PNG 编译为 4bpp PackBits-RLE 位图，开机以 `GC16` 完整绘制静态 UI。
- 动态卡片按需以 `DU` 局部刷新，并通过 `ui_refresh` 防抖合并突发状态更新。
- 触摸热区采用 YAML 数据表定义，无需编写分支判断代码。
- 构建期校验热区边界、字体文件与实体 ID，提前拦截布局错误。
- 读取板载 SHT4x 温湿度传感器与 PCF8563 RTC，开机由 Home Assistant 同步校时。
- 按钮控制目标、服务动作与卡片文本通过 Home Assistant `text` 实体在运行时修改，免重新编译。

## 目录结构

```
e1003-dashboard.yaml            # 开发者入口，使用本地凭据
e1003-release.yaml              # 无用户凭据的 USB 配网验证版
e1003-base.yaml                 # 两个入口共享的默认值与组件组合
layout/                         # 屏幕布局、坐标尺寸、触摸热区与字体定义
packages/                       # ESPHome 组件包（硬件、显示、触摸、状态与 HA 桥接）
src/                            # C++ 辅助代码（位图解码等）
assets/                         # 设计稿 PNG 与生成的位图头文件
tools/                          # 布局编译与图片转换工具
ha/                             # Home Assistant 配置包、转发脚本与自动化示例
docs/                           # 详细文档
scripts/                        # Linux、macOS 与 Windows 构建脚本
```

详细固件分层与 packages 说明见 [docs/architecture.md](docs/architecture.md)。

参考设计使用维护者预编译的单一 USB 固件，通过 App 配置 Wi-Fi 和灯光目标，默认无需 API 密钥，加密为可选项。使用者不需要编辑 YAML 或编译固件，见[配置流程](docs/provisioning.md)。下方快速开始面向固件开发者。

## 快速开始

首先安装工具链依赖并生成配置文件副本：

```bash
uv sync
cp secrets.example.yaml secrets.yaml
```

编辑 `secrets.yaml`，填入你的 Wi-Fi 凭据、回退热点密码以及 ESPHome API 加密密钥。

然后编译并烧录固件：

```bash
scripts/build.sh run
```

`scripts/build.sh` 在编译前会自动调用 `tools/layout_to_h.py` 生成布局头文件，无需手动单独执行生成步骤。

以上命令适用于 Linux 与 macOS；Windows 环境请执行 `scripts/build.bat run`。完整的构建与烧录细节参见 [docs/build-and-flash.md](docs/build-and-flash.md)。

烧录完成后，在 Home Assistant 中添加设备（**设置 → 设备与服务 → ESPHome**），并将控制项指向目标实体：

```yaml
action: text.set_value
target:
  entity_id: text.e1003_smart_workspace_main_light_target
data:
  value: light.desk_lamp
```

配置保存后即刻生效，无需重新编译固件。所有运行时可配置项参见 [docs/configuration.md](docs/configuration.md)。

## 哪些能改、哪些要重编译

| 想改的内容 | 免重编译 | 方式 |
|---|:---:|---|
| 按钮控制哪个实体 | ✅ | `text..._main_light_target` |
| 亮度/百分比按钮调用哪个动作 | ✅ | `text..._main_light_action` |
| 卡片显示的状态或数值 | ✅ | `text..._main_light_state` / `_value` |
| 时钟/横幅文案（天气、日历） | ✅ | `text..._clock_message` |
| 所有按钮的整体逻辑 | ✅ | `zone_script_hook` → HA 脚本 |
| 按钮与卡片数量、位置、字体 | ❌ | `layout/ui_layout.yaml` + 设计稿 PNG |
| 引脚、板型、面板型号、兜底绑定 | ❌ | `e1003-dashboard.yaml` + `-s key value` |

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

引脚定义是 `e1003-dashboard.yaml` 中的 substitutions。
