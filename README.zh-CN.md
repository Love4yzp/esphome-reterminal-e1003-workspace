# reTerminal E1003 墨水屏智能面板(Home Assistant / ESPHome)

基于 **reTerminal E1003** 墨水屏(1872×1404、16 级灰度、IT8951)+ **Seeed XIAO
ESP32-S3** 的 ESPHome 固件模板:设计稿位图作为静态 UI,少量动态卡片单独局部刷新,
触摸热区调用 Home Assistant。

整个仓库围绕两个原则:

**设计稿是源文件,不是代码。** 屏幕几何、字体、触摸热区统一放在
[`layout/ui_layout.yaml`](layout/ui_layout.yaml),由 `tools/layout_to_h.py` 编译成
C++ 头文件。ESPHome 的 packages 里不允许出现任何一个像素数值。

**行为是配置,不是固件。** 按钮控制哪个实体、调用哪个服务、卡片显示什么内容,
全部是普通的 Home Assistant `text` 实体。换个灯 = 一次服务调用,**不用重编译、不用
OTA**。

[English README](README.md)

## 核心特性

- 单张设计稿 → 4bpp PackBits-RLE 位图(约 250 KB),启动一次 `GC16` 全刷
- 脏标记局部刷新:之后只刷变化的卡片,并用 `ui_refresh` 防抖合并突发更新
- 触摸热区是**数据表**而不是 `if` 链:加按钮只改 YAML
- 构建期校验几何:越界、字体缺失、布局引用了不存在的实体 id 都会直接报错
- 板载 SHT4x 温湿度 + PCF8563 RTC(时间由 HA 校时)
- 运行时可改的目标实体 / 服务 / 卡片文案,以及可选的 HA 转发脚本
- 可选 push / pull 通道,显示固件"从没听说过"的实体状态
- 工具链由 `uv` 管理并锁版本,Linux/macOS/Windows 一套构建脚本

## 目录结构

```
e1003-dashboard.yaml            # ← 唯一要烧录的文件(薄薄的 packages 组装)
├── layout/
│   ├── ui_layout.yaml          # ← 唯一真源:热区、卡片、字体、调色板、刷新策略
│   └── generated/              # ← 生成物:ui_layout.h / fonts.yaml / policy.yaml
├── packages/
│   ├── core.yaml               # ESP32-S3、Wi-Fi、API、OTA、启动流程
│   ├── hardware.yaml           # SPI/I2C、蜂鸣器、SHT4x、PCF8563
│   ├── display.yaml            # IT8951 面板 + 渲染 lambda
│   ├── ui-state.yaml           # 脏标记 + ui_refresh / ui_beep / ui_repaint
│   ├── touch.yaml              # GT911 + 通用热区分发
│   ├── ha-bridge.yaml          # ← 运行时(免重编译)配置层
│   └── ha-pull.yaml            # 可选:设备反向拉取 HA 的 JSON
├── src/e1003_render.h          # C++ 辅助函数(RLE 位图解码)
├── assets/                     # 设计稿 PNG + 生成的位图头文件
├── tools/                      # png_to_h.py、layout_to_h.py
├── ha/e1003_dashboard.yaml     # Home Assistant 包:转发脚本 + 示例自动化
├── docs/                       # 架构 / 配置 / 布局 / HA 集成 / 构建
└── scripts/                    # build.sh / build.bat / run_esphome.bat
```

## 快速开始

```bash
uv sync                                        # 按 uv.lock 装工具链
cp secrets.example.yaml secrets.yaml           # Wi-Fi、回退热点、API key

uv run python tools/layout_to_h.py             # 重新生成几何头文件
scripts/build.sh run                           # 编译 + 烧录 + 看日志
```

然后在 Home Assistant 里添加设备(**设置 → 设备与服务 → ESPHome**),
把卡片指向你的灯:

```yaml
action: text.set_value
target: { entity_id: text.e1003_smart_workspace_main_light_target }
data: { value: light.desk_lamp }
```

全程没有重新编译。其他可运行时修改的内容见
**[docs/configuration.md](docs/configuration.md)**。

## 哪些能改、哪些要重编译

| 想改的东西 | 免重编译 | 怎么做 |
|---|---|---|
| 按钮控制哪个实体 | ✅ | `text..._main_light_target` |
| 亮度按钮调用哪个服务 | ✅ | `text..._main_light_action` |
| 卡片显示的状态/数值 | ✅ | `text..._main_light_state` / `_value` |
| 时钟卡片文案(天气、日程) | ✅ | `text..._clock_message` |
| 所有按钮的整体逻辑 | ✅ | `zone_script_hook` → HA 脚本 |
| 按钮/卡片数量、位置、字体 | ❌ | `layout/ui_layout.yaml` + 设计稿 |
| 引脚、板型、面板型号、兜底绑定 | ❌ | `e1003-dashboard.yaml` + `-s key value` |

这条界线是刻意的:**行为运行时改,设计编译期改**。墨水屏上,设计稿本身就是固件。

## 定制指引

| 目标 | 文档 |
|------|------|
| 改控制目标、用 HA 驱动面板 | [docs/configuration.md](docs/configuration.md) |
| 挪按钮、加卡片、换设计稿 | [docs/ui-layout.md](docs/ui-layout.md) |
| 理解分层与刷新协议 | [docs/architecture.md](docs/architecture.md) |
| HA 侧配置、转发脚本、push/pull 配方 | [docs/ha-integration.md](docs/ha-integration.md) |
| 构建、烧录、救砖、工具链 | [docs/build-and-flash.md](docs/build-and-flash.md) |
| 交给 AI Agent 改造 | [CLAUDE.md](CLAUDE.md) |

## 硬件

| | |
|---|---|
| 屏幕 | reTerminal E1003,IT8951,1872×1404,16 级灰度,SPI |
| 主控 | Seeed XIAO ESP32-S3,八线 PSRAM,Arduino 框架 |
| 触摸 | GT911(I²C),LEDC 驱动蜂鸣器做反馈 |
| 传感器 | SHT4x(温湿度)、PCF8563(RTC,带电池备份) |

引脚定义在 `e1003-dashboard.yaml` 的 substitutions 里。

## 许可

MIT,见 [LICENSE](LICENSE)。