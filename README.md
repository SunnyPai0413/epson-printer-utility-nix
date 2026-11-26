# Epson Printer Utility for Nix

**NixOS-first 的 Epson 打印机维护工具与可选 CUPS USB 后端。** 首个正式公开版本为 **v1.0.0**（`VERSION` 为 `1.0.0`，Git Tag 为 `v1.0.0`）。从仓库保留的官方 **Epson Printer Utility 1.1.3 / epson-backend 1.3.1** 源码构建原生 Qt GUI、CLI、USB daemon 和 ecblp；项目版本与这两个上游版本独立管理。本项目独立维护，**非 Epson 官方项目，未获 Epson 背书**。

提供设备发现／切换、状态、设备上报墨量、进纸计数、喷嘴检查和普通清洗。USB 使用原生 ecbd；网络维护保留 EPSCommonLib 原生通路。**实机验证限于 NixOS 上的 L805 USB 设备**：2026-11-26 已完成远程 IPP 多页 PDF 打印及重启后验证。其他 Epson 机型、Epson 网络设备的发现与维护尚未实机验证，功能可用性取决于上游协议与设备。详细范围见下文验证表。

只提供上述维护入口，不提供 Power Ink Flushing、废墨计数器重置、EEPROM 修改或任意指令接口。

## 安装

包输出面向 `x86_64-linux`、`aarch64-linux`。需要安装 Nix 并启用 `nix-command`、`flakes` 特性；NixOS 可在系统配置中设置：

```nix
nix.settings.experimental-features = [ "nix-command" "flakes" ];
```

尚未启用这些特性时，也可将下文命令开头的 `nix` 替换为 `nix --extra-experimental-features 'nix-command flakes'`，临时启用后构建或运行。

应用配置后，推荐固定 **Git Tag**，并保留调用方的 `flake.lock`。以下公开引用在维护者发布 `v1.0.0` Tag 后可用：

```sh
nix build github:SunnyPai0413/epson-printer-utility-nix/v1.0.0#default
nix run github:SunnyPai0413/epson-printer-utility-nix/v1.0.0#cli -- --help
nix run github:SunnyPai0413/epson-printer-utility-nix/v1.0.0#gui
```

`nix build` 的结果位于 `./result`；`nix run` 临时运行应用。默认包包含 GUI、CLI、ecbd 和 `lib/cups/backend/ecblp`。也可分别构建 `#epson-printer-utility`（GUI／CLI）和 `#epson-backend` / `#ecblp`（同一个后端包）。构建或运行包本身不会安装系统服务、USB 权限或 CUPS 队列。

### NixOS：推荐模块安装

模块负责运行目录、维护锁、访问组和 USB 服务。将下面结构合并进现有 `flake.nix`；保留已有的 `nixpkgs` input 和系统模块，把 `your-host`、架构替换为自己的配置：

```nix
{
  inputs.epson-utility.url = "github:SunnyPai0413/epson-printer-utility-nix/v1.0.0";

  outputs = inputs@{ nixpkgs, ... }: {
    nixosConfigurations.your-host = nixpkgs.lib.nixosSystem {
      system = "x86_64-linux"; # 或 aarch64-linux
      modules = [
        ./configuration.nix
        inputs.epson-utility.nixosModules.default
      ];
    };
  };
}
```

在 `configuration.nix` 中加入 USB 配置；`your-user` 必须是已存在的普通用户：

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

从你的系统配置目录应用配置，再重新登录使组权限生效；已连接的 USB 设备可能需要重新插拔：

```sh
sudo nixos-rebuild switch --flake .#your-host
systemctl status ecbd.service
epson-printer-cli devices --connection usb --json
```

模块会安装 `epson-printer-utility` 和 `epson-printer-cli`。GUI 由桌面普通用户启动。ecbd 一次管理一台 USB 打印机；多台匹配时拒绝任取第一台，用模块的 USB 描述符序列号筛选。更换被 daemon 管理的 USB 设备需要调整筛选并重启服务，不支持在 GUI 中动态接管多台 USB 设备。CUPS 打印还需完成下文的驱动与队列配置。

### NixOS：仅网络维护（尚未实机验证）

在已导入模块的系统配置中，使用：

```nix
services.epson-printer-utility = {
  enable = true;
  users = [ "your-user" ];
  usb.enable = false;
};
```

这不会启用 ecbd、USB 规则或安装 USB 后端。网络发现、连接和维护直接走上游 EPSCommonLib，不需要 USB 设备，不通过 ecbd 转发，也不需要暴露其端口。发现范围和可用功能取决于上游协议、网络可达性和设备。原生网络发现通常需要等待数秒；跨网段发现未验证。

只运行网络发现／状态查询可直接使用固定 Tag 的 `#cli`，无需模块。执行维护还需要模块创建的共享锁和相应访问权限。**CUPS 远程 IPP 打印验证不代表 Epson 原生网络维护已经验证。**

### 其他 Linux 发行版

其他 Linux 发行版可以安装 Nix，使用上述 Flake 包构建及运行 GUI／CLI；这不等同于完整的系统集成。当前没有 `.deb`、`.rpm`、原生安装器，也没有面向其他发行版的服务安装集成。USB daemon、udev 权限、运行目录／锁、CUPS ACL 和驱动接入需要自行配置；本文的模块安装与实机验证面向 NixOS。

## Cachix 二进制缓存与 CI

Cachix 是 **Nix binary cache（二进制缓存）**，不是传统安装包下载站，也不提供 `.deb`、`.rpm` 或独立安装器。Nix 根据 Flake 版本、锁定的依赖与系统架构匹配 store 路径，命中缓存时直接下载构建结果；未命中时仍会从源码构建。

两个架构分别使用 GitHub 原生 Ubuntu Runner，独立构建和上传，不使用交叉编译。2026-11-26 的发布前基线已在两个架构完成构建与 Cachix 发布，固定运行链接见 [验证记录](validation/README.md)。下列徽章显示 `main` 分支的最新状态；构建成功不代表对应架构的打印机实机验证。

| 架构 | 原生 Runner | 构建与缓存发布状态 |
| --- | --- | --- |
| `x86_64-linux` | `ubuntu-24.04` | [![x86_64-linux](https://github.com/SunnyPai0413/epson-printer-utility-nix/actions/workflows/cache-x86_64-linux.yml/badge.svg?branch=main)](https://github.com/SunnyPai0413/epson-printer-utility-nix/actions/workflows/cache-x86_64-linux.yml) |
| `aarch64-linux` | `ubuntu-24.04-arm` | [![aarch64-linux](https://github.com/SunnyPai0413/epson-printer-utility-nix/actions/workflows/cache-aarch64-linux.yml/badge.svg?branch=main)](https://github.com/SunnyPai0413/epson-printer-utility-nix/actions/workflows/cache-aarch64-linux.yml) |

### 维护者配置

先在 [Cachix](https://app.cachix.org/) 创建缓存。供所有用户下载时选择 **Public**，签名选择 **Managed by Cachix**，并创建具有该缓存写入权限的 Token。在 GitHub 仓库 **Settings → Secrets and variables → Actions** 中配置：

| 类型 | 名称 | 内容 |
| --- | --- | --- |
| Repository variable（Variables） | `CACHIX_CACHE_NAME` | 实际缓存名称，不含 `https://` 或 `.cachix.org` |
| Repository secret（Secrets） | `CACHIX_AUTH_TOKEN` | 具有该缓存写入权限的 Cachix Token |

缺少任一配置时，工作流会在安装 Nix 和构建前明确报错；Token 只从 Secret 读取。仓库需要启用 GitHub Actions，并允许工作流使用上述 Runner 和所引用的 Actions。

推送到 `main`、推送 `v*` Tag 或在 Actions 页面手动运行对应架构工作流时，都会调用共用的 [构建工作流](.github/workflows/build-cache.yml)，构建 `packages.<system>.default`、`epson-printer-utility` 和 `epson-backend`。`ecblp` 与 `epson-backend` 是同一产物，无需另建；Nix 会复用默认包与子包之间的共享依赖。

每个架构的三个目标全部成功后，才启用 [`cachix/cachix-action@v17`](https://github.com/cachix/cachix-action/tree/v17) 的自动上传，通过 `pathsToPush` 限定为这些输出及其运行依赖，不扫描整个 Nix store，也不额外执行 `cachix push`。ARM 失败不会取消或影响 x86 的结果；失败架构不会启用上传，成功架构独立发布。此流程只发布 Nix 缓存，不创建 GitHub Release。

### 使用缓存

将下例 `YOUR-CACHE-NAME` 替换为维护者配置的 `CACHIX_CACHE_NAME` 实际值；本地不会自动读取 GitHub Actions Variable：

```sh
CACHIX_CACHE_NAME='YOUR-CACHE-NAME'
nix run nixpkgs#cachix -- use "$CACHIX_CACHE_NAME"
nix build github:SunnyPai0413/epson-printer-utility-nix/v1.0.0#default
```

按 `cachix use` 输出的提示完成 Nix 配置。NixOS 用户将实际缓存地址与公钥加入 `nix.settings.extra-substituters`、`nix.settings.extra-trusted-public-keys` 后应用系统配置；公钥可从该缓存的 Cachix 页面获取。公共缓存下载无需写入 Token。若选择私有缓存，下载者还需配置自己的只读凭据，见 [Cachix 使用说明](https://docs.cachix.org/using-a-cache)。

缓存按实际 store 路径匹配。建议固定 `v1.0.0` Tag，并确认该 Tag 对应的 CI 已成功，保持锁文件与架构一致；`#epson-printer-utility`、`#epson-backend`、`#ecblp` 以及 NixOS 模块安装也使用同一套 Nix 缓存机制。项目版本号变化会产生新的 store 路径，发布前基线的缓存不保证命中 v1.0.0 产物。

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

v1.0.0 使用 **JSON schema 2**，与本地早期版本相比含兼容性变化；`project_version` 为 `1.0.0`，两个上游版本仍分别为 `1.1.3` / `1.3.1`。脚本接入或升级前请阅读 [JSON 字段与退出码](docs/JSON.md)。

## 可选 CUPS 接入

### USB L805：后端、驱动与队列

在上面的 USB 模块配置基础上启用 CUPS，并在接受 `pkgs` 参数的系统模块（如 `configuration.nix`）中加入机型驱动。L805 示例：

```nix
services.epson-printer-utility.cups.enable = true;
services.printing.drivers = [ pkgs.epson-escpr ];
```

模块会启用 CUPS（若未配置），自动把 ecblp 所在的 `backendPackage` 加入 `services.printing.drivers`，并通过用户组和 tmpfiles ACL 授予 CUPS 后端使用的 `lp` 组 FIFO／锁访问权限；目录的默认 ACL 覆盖服务重建文件的情况，重启后会重新应用。仅将 `#epson-backend` 放入驱动列表不足以完成这些服务与权限配置。

ecblp 是 USB **传输后端**，不包含机型 PPD 或渲染过滤器；`pkgs.epson-escpr` 在此提供 L805 的渲染驱动。其他机型需自行核实驱动与上游支持，尚未实机验证。应用 NixOS 配置后，先查询后端与实际可用的 L805 型号标识：

```sh
lpinfo -v
lpinfo -m | grep -i L805
```

ecbd 就绪后应能发现 URI：

```text
ecblp:/run/epson-printer-utility/ecblp0
```

将 `lpinfo -m` 输出中匹配 L805 的**第一列**替换下例的 `MODEL_FROM_LPINFO`，手动创建名为 `Epson_L805` 的队列（也可在 `http://localhost:631` 中选择同一 URI 和机型驱动）：

```sh
sudo lpadmin -p Epson_L805 -E \
  -v 'ecblp:/run/epson-printer-utility/ecblp0' \
  -m 'MODEL_FROM_LPINFO'
lpstat -v Epson_L805
```

装纸后可主动提交一份自己的 PDF，并检查任务：

```sh
lp -d Epson_L805 /path/to/test.pdf
lpstat -W not-completed -o Epson_L805
```

任务完成状态仍需结合实际出纸确认。模块不会创建、迁移或修改任何打印队列。已有队列可由用户在 CUPS 中修改 URI 和驱动；ecbd 管理的 USB 设备应通过 ecblp 打印，其他直接抢占同一 USB 接口的队列无法与它共享连接。直接连接网络打印机的队列继续使用自身的网络传输，无需 ecblp。

ecblp 和维护工具共用 `/run/epson-printer-utility` 下的 FIFO、写入锁和操作锁，避免 USB 打印数据与维护命令交错；维护前重新检查设备是否空闲。发往本机 CUPS 的远程 IPP 作业也经 ecblp 使用这些锁；其他主机直接向网络打印机发送的作业不受本机维护锁控制。ecbd 仅监听 `127.0.0.1:35587`，不开放防火墙；上游本地 TCP 接口无用户认证。正常打印所需的取消、复位和特定继续打印通路仅保留在后端内部，CLI 没有对应维护入口。

v1.0.0 包含 ecblp 的 FIFO 背压修复：读端存活但消费较慢时继续等待，同时保留 CUPS 取消能力；读端消失或 I/O 失败时明确失败，不自动重放打印数据。2026-11-26 已验证 L805 远程 IPP 多页 PDF 输出，重启后 ACL、CUPS 服务及打印任务验证通过。

### 可选：让局域网客户端通过 IPP 打印

路径为 **客户端 → IPP → NixOS CUPS → 机型驱动 → ecblp/ecbd → USB L805**。Epson 原生网络发现／维护是另一条通路，尚未实机验证。

默认模块只提供本机接入。若需要共享，按实际受信局域网设置 CUPS 监听与允许范围；替换下面的主机地址和网段，然后应用配置：

```nix
services.printing = {
  listenAddresses = [ "localhost:631" "192.168.1.10:631" ];
  allowFrom = [ "localhost" "192.168.1.0/24" ];
  openFirewall = true;
};
```

在打印主机上共享刚创建的队列：

```sh
sudo lpadmin -p Epson_L805 -o printer-is-shared=true
```

客户端可添加 `ipp://PRINT_SERVER_IP:631/printers/Epson_L805`。有 CUPS 客户端命令时，可直接向打印主机提交多页 PDF；将 `PRINT_SERVER_IP` 替换为实际地址：

```sh
lp -h PRINT_SERVER_IP:631 -d Epson_L805 /path/to/multipage.pdf
lpstat -h PRINT_SERVER_IP:631 -W not-completed -o Epson_L805
```

这里共享的是 CUPS 的 631 端口；ecbd 的 35587 端口保持本机监听。若任务失败，先检查 `journalctl -u cups.service -u ecbd.service`；权限问题可用 `getfacl /run/epson-printer-utility{,/ecblp0,/fifo.lock,/operation.lock}` 核对 `lp` 组 ACL，再检查队列 URI、驱动及实际出纸情况。

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
| L805 USB 状态、墨量、进纸计数 | GUI／CLI 共用，解析与离线回归 | L805 枚举、状态、实际墨色 ID、未知墨量与原生计数 | 全部错误状态、其他墨色配置 |
| L805 喷嘴检查、普通清洗 | 原生命令、共享维护锁 | 历史实机喷嘴／清洗及 oneshot 记录 | 发布准备未重复清洗；新 GUI 完整维护交互、timer 激活 |
| L805 CUPS USB／远程 IPP 打印 | ecblp、FIFO 背压修复、CUPS 集成 | 2026-11-26 远程 IPP 多页 PDF；重启后 ACL、CUPS 服务与打印任务通过 | 打印过程中主动触发维护的完整实机交互 |
| Epson 网络发现、连接、状态与维护 | EPSCommonLib 原生通路，解析／离线检查 | 无网络设备实机验证 | 网络维护、跨网段连接 |
| 其他 Epson 机型 | 保留上游协议与机型选择能力 | 无 | 全部其他机型的打印与维护兼容性 |
| 构建与缓存 | `x86_64-linux`、`aarch64-linux` 原生 CI | 两架构发布前基线构建与 Cachix 发布成功；硬件验证在 NixOS x86_64 | aarch64 打印机硬件验证、其他发行版原生安装集成 |

详细证据与本轮结果在 [validation/README.md](validation/README.md)。个人维护过程只作为历史证据，不是使用教程，不据此宣称全机型兼容。

## 构建与贡献

```sh
nix build .#default
nix flake check .
nix flake check . --all-systems --no-build
nix develop .
```

前两条在当前架构构建与检查；`--all-systems --no-build` 只求值全部架构，不能代替另一架构的实际构建。Git 工作区引用会过滤已忽略的本地构建产物；新增构建源文件需纳入 Git 跟踪后才能被此引用读取。

构建在沙箱中解包保留的 tarball，再应用 `patches/adapt.py`；不下载其他上游版本，不使用预编译 Epson 二进制、Wine 或 FHS 容器。检查覆盖来源校验、原生 USB／网络解析、公共模型、离线 CLI、CUPS FIFO 和模块配置。[源码来源与校验值](upstream/SOURCE.md)、[许可证说明](NOTICE.md)、[changelog](CHANGELOG.md) 和 [v1.0.0 发布说明](docs/RELEASE-NOTES.md) 随仓库保留。新增代码采用 GPL-2.0-or-later，上游文件保留各自许可。
