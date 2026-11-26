# Epson Printer Utility for Nix

从仓库保留的官方 **Epson Printer Utility 1.1.3 / epson-backend 1.3.1** 构建原生 Qt GUI、CLI、USB daemon 和可选 CUPS 后端。项目版本为 **0.2.0（未发布）**，与上游版本分开管理。本项目独立维护，**非 Epson 官方项目，未获 Epson 背书**。

支持上游 Linux 工具已有的设备发现／切换、状态、设备上报墨量、进纸计数、喷嘴检查和普通清洗。网络使用 EPSCommonLib 原生网络通路；USB 使用原生 ecbd。只提供上述维护入口，不提供 Power Ink Flushing、废墨计数器重置、EEPROM 修改或任意指令接口。

## 安装

需要启用 Nix 的 `nix-command`、`flakes` 特性。发布到 GitHub 后可使用以下 Flake 引用；开发时用 `path:.` 替换它：

```sh
nix build github:SunnyPai0413/epson-printer-utility-nix
nix run github:SunnyPai0413/epson-printer-utility-nix#gui
nix run github:SunnyPai0413/epson-printer-utility-nix#cli -- --help
```

默认包包含 GUI、CLI、ecbd 和 `lib/cups/backend/ecblp`。也可分别构建 `#epson-printer-utility`（无需 USB 后端）和 `#epson-backend` / `#ecblp`。

NixOS 推荐使用模块，它负责运行目录、维护锁、访问组和 USB 服务。在调用方 Flake 中增加 input，并导入模块：

```nix
inputs.epson-utility.url = "github:SunnyPai0413/epson-printer-utility-nix";
# 在 nixosSystem.modules 中加入：
inputs.epson-utility.nixosModules.default
```

USB 配置示例：

```nix
services.epson-printer-utility = {
  enable = true;
  users = [ "your-user" ]; # 已存在的桌面用户
  usb.enable = true;      # 默认值
  # 多台 Epson USB 设备时，指定设备实际的 serial / productId：
  # device.serial = "YOUR_USB_SERIAL";
  # device.productId = "YOUR_4_HEX_DIGIT_ID";
};
```

应用你自己的 NixOS 配置后重新登录，使组权限生效；已经连接的 USB 设备可能需要重新插拔。GUI 由桌面普通用户启动。ecbd 一次管理一台 USB 打印机；多台匹配时拒绝任取第一台，用模块的序列号筛选。更换被 daemon 管理的 USB 设备需要调整筛选并重启服务，不支持在 GUI 中动态接管多台 USB 设备。

纯网络配置：

```nix
services.epson-printer-utility = {
  enable = true;
  users = [ "your-user" ];
  usb.enable = false;
};
```

这不会启用 ecbd、USB 规则或安装 USB 后端。网络发现、连接和维护直接走上游 EPSCommonLib，不需要 USB 设备，不通过 ecbd 转发，也不需要暴露其端口。发现范围和可用功能取决于上游协议、网络可达性和设备。原生网络发现通常需要等待数秒；跨网段发现未验证。

只运行网络状态查询可直接 `nix run ...#cli`，无需模块。执行维护还需要模块创建的共享锁和相应访问权限。此仓库提供 NixOS 集成，未提供其他 Linux 发行版的服务安装脚本。

## 使用

安装模块后可以直接运行 `epson-printer-cli` 和 `epson-printer-utility`：

```sh
epson-printer-cli devices --json
epson-printer-cli devices --connection usb --json
epson-printer-cli devices --connection network --json

# 复制 devices 返回的 id 或 location，避免同型号歧义：
epson-printer-cli status --device 'NATIVE_ID_FROM_DEVICES' --json
epson-printer-cli ink --device 'NATIVE_ID_FROM_DEVICES' --json
epson-printer-cli paper-count --device 'NATIVE_ID_FROM_DEVICES' --json

# USB 为当前 ecbd 选中的唯一 USB 设备：
epson-printer-cli status --device USB --json
epson-printer-cli nozzle-check --device USB          # 一份原生检查图案，先装纸
epson-printer-cli clean --device USB --confirm-clean # 一次普通清洗，消耗墨水
```

`--device` 支持原生 ID（如 `USB:序列号` 或发现得到的网络 ID）、已发现的网络地址、完整型号名和 `auto`。`auto` 或型号匹配多台时拒绝执行。没有序列号的 USB ID 为 `USB`。`--connection all|usb|network` 限定发现范围；`USB` / `USB:…` 选择器默认只查 USB。纯网络模块将 GUI／CLI 默认范围设为 `network`，仍可显式覆盖 CLI 范围。

GUI 保留原生打印机选择和维护界面，列表显示设备 ID。维护在后台执行，期间禁用重复提交；一次命令发送后最多约两分钟等待状态，失败或超时显示“未确认”，不会自动重发。关闭正在维护的窗口会等待当前工作结束，避免销毁通信库。

墨色根据设备列表逐项显示，不固定为六色，不把 photo black、matte black 等不同颜色合并。设备不允许显示、状态不可读或值无效时为“未知”／JSON `null`；不猜颜色或按档位伪造百分比。**设备上报百分比不是墨仓实际液位测量。** 没有颜色列表时显示未知，JSON 为 `[]`。

`paper-count` 沿用原生计数接口，逐项保留未知值；总数只在彩色和黑白计数都有效时相加。它表示设备进纸计数，**不是成功打印页数**，也不是可重置的废墨计数器。设备不支持或未上报时明确不可用。

原有四个 CLI 命令和 `--json` 保留；新增 `devices`、`paper-count`。**JSON schema 2 含兼容性变化**，脚本升级前请阅读 [JSON 字段与退出码](docs/JSON.md)。

## 可选 CUPS 接入

```nix
services.epson-printer-utility.cups.enable = true;
```

这会启用 CUPS（若未配置），把 `backendPackage` 加入 `services.printing.drivers`，授予 CUPS 用户 FIFO／锁访问权限，并保留 CUPS 运行。也可直接把此 Flake 的 `packages.<system>.epson-backend` 放入 `services.printing.drivers`；仍需启用 USB 模块，并将 CUPS 用户加入 `epson-maintenance` 组以访问共享运行目录和锁。

ecblp 是 USB **传输后端**，不包含机型 PPD 或渲染过滤器；还需要适合机型的打印驱动。ecbd 就绪后，`lpinfo -v` 应能列出：

```text
ecblp:/run/epson-printer-utility/ecblp0
```

由用户在打印机设置中为目标设备选择此后端。模块不会创建、迁移或修改任何打印队列。ecbd 管理的 USB 设备应通过 ecblp 打印；其他直接抢占同一 USB 接口的队列无法与它共享连接。网络打印机继续使用已有的网络打印队列，无需 ecblp。

ecblp 和维护工具共用 `/run/epson-printer-utility` 下的 FIFO、写入锁和操作锁，避免 USB 打印数据与维护命令交错；维护前重新检查设备是否空闲。网络上其他主机提交的作业不受本地锁控制。ecbd 仅监听 `127.0.0.1:35587`，不开放防火墙；上游本地 TCP 接口无用户认证。正常打印所需的取消、复位和特定继续打印通路仅保留在后端内部，CLI 没有对应维护入口。

## 可选定时喷嘴检查

默认关闭。只在明确需要自动消耗纸张打印原生图案时开启，并设置唯一设备：

```nix
services.epson-printer-utility = {
  device.selector = "NATIVE_ID_FROM_DEVICES";
  automaticNozzleCheck = {
    enable = true;
    onCalendar = "Sun *-*-* 10:00:00";
  };
};
```

日历按主机时区解释，也可在表达式中指定时区。离线、忙碌、设备错误或锁被占用时记录原因并跳过；`Persistent=false`、`Restart=no`，不积压补打，不自动清洗。任务日志：

```sh
journalctl -u epson-nozzle-check.service
```

未开启 timer 时也有对应 oneshot service；手动启动它会实际打印一份图案。

## 完成情况与验证边界

| 范围 | 已实现 | 已实机验证 | 未验证 |
| --- | --- | --- | --- |
| USB 状态、墨量、喷嘴检查、普通清洗 | 是 | 新版 L805 枚举／状态／墨量只读回归；历史喷嘴／清洗记录 | 其他机型；新版本维护动作未重复执行 |
| 网络发现、连接、状态、墨量、进纸计数和两项维护 | 原生通路已恢复 | 无网络设备验证 | 网络实机和跨网段连接 |
| 错误／警告、墨色 ID、未知值、进纸计数解析 | GUI／CLI 共用，夹具回归 | 新版 L805 状态／墨量／进纸计数，详见验证记录 | 全部错误状态、其他墨色配置 |
| CUPS ecblp 与维护共存 | 已构建安装、FIFO／锁／失败路径检查 | L805 ecblp 发现，CUPS 保持运行 | 实际 CUPS 打印、打印中维护和完整模块激活 |
| 定时任务、GUI 后台维护 | 已实现、模块／离线检查 | 历史 L805 oneshot；新版桌面 GUI 启动 | 新版完整 GUI 维护交互 |
| 平台 | 提供 x86_64-linux、aarch64-linux | x86_64-linux 构建与检查 | aarch64-linux 构建／硬件 |

详细证据与本轮结果在 [validation/README.md](validation/README.md)。个人维护过程只作为历史证据，不是使用教程，不据此宣称全机型兼容。

## 构建与贡献

```sh
nix build path:.
nix flake check path:.
nix develop path:.
```

构建在沙箱中解包保留的 tarball，再应用 `patches/adapt.py`；不下载其他上游版本，不使用预编译 Epson 二进制、Wine 或 FHS 容器。检查覆盖来源校验、原生 USB／网络解析、公共模型、离线 CLI、CUPS FIFO 和模块配置。[源码来源与校验值](upstream/SOURCE.md)、[许可证说明](NOTICE.md)、[changelog](CHANGELOG.md) 和 [发布说明草稿](docs/RELEASE-NOTES.md) 随仓库保留。新增代码采用 GPL-2.0-or-later，上游文件保留各自许可。
