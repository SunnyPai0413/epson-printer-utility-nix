# Epson Printer Utility for Nix

**面向 NixOS 的 Epson 打印机维护工具与可选 CUPS USB 后端。**
从仓库保留的 Epson Printer Utility **1.1.3** 和 epson-backend **1.3.1** 源码
构建原生 Qt GUI、CLI、ecbd 和 ecblp。项目版本为 **v1.0.0**，与上游版本独立。

本项目由社区独立维护，非 Epson 官方产品，未获 Epson 背书。
当前实机证据限于 NixOS x86_64 主机连接的 **Epson L805 USB** 设备。

## 功能

| 功能 | 说明 |
| --- | --- |
| 设备发现与选择 | USB／原生网络发现，拒绝有歧义的设备选择 |
| 状态与墨量 | GUI／CLI 共用设备报告，保留警告、原始墨色 ID 和未知值 |
| 进纸计数 | 报告设备提供的原生计数，不是成功打印页数 |
| 喷嘴检查 | 发送一次原生检查图案，消耗一张纸 |
| 普通清洗 | 手动确认后执行一次，不自动重复 |
| CUPS USB 打印 | ecblp/ecbd 传输后端，普通队列另需机型驱动 |
| Windows 原厂驱动接入 | 经 IPP RAW 队列传输原厂驱动生成的数据 |
| 可选定时喷嘴检查 | 默认关闭，忙碌／离线／锁占用时跳过，不补打或自动清洗 |

本项目的维护接口只有喷嘴检查与普通清洗，不提供废墨计数器重置、EEPROM 修改或任意指令接口。
**大墨量冲洗（Power Ink Flushing）由 Windows Epson 原厂驱动提供，
不属于本项目 GUI、CLI 或定时维护接口。**

## 快速安装

支持 `x86_64-linux`、`aarch64-linux`，需要 Nix 和 `nix-command`／`flakes` 特性。
完整安装、缓存下载、仅网络模式及定时配置见 [安装指南](docs/INSTALL.md)。

### NixOS 模块

将输入和模块合并进已有系统 Flake，保留自己的 `nixpkgs`、主机名及其他模块：

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

在 `configuration.nix` 中加入以下配置，`your-user` 是已存在的普通用户：

```nix
nix.settings.experimental-features = [ "nix-command" "flakes" ];

services.epson-printer-utility = {
  enable = true;
  users = [ "your-user" ];
  usb.enable = true;
};
```

从系统配置目录应用配置，再重新登录使用户组权限生效：

```sh
sudo nixos-rebuild switch --flake .#your-host
systemctl status ecbd.service
epson-printer-cli devices --connection usb --json
```

模块安装 GUI／CLI，管理 USB 服务和访问权限。GUI 由普通桌面用户启动：

```sh
epson-printer-utility
```

ecbd 一次管理一台 USB 打印机。多台设备时，用模块的 `device.serial`／`productId`
指定设备；筛选含义和仅网络配置见安装指南。

### 只构建或临时运行

以下固定版本引用需要远端已存在 `v1.0.0` Tag；保留调用方的 `flake.lock`：

```sh
nix build github:SunnyPai0413/epson-printer-utility-nix/v1.0.0#default
nix run github:SunnyPai0413/epson-printer-utility-nix/v1.0.0#cli -- --help
nix run github:SunnyPai0413/epson-printer-utility-nix/v1.0.0#gui
```

`nix build` 输出到 `./result`；构建或临时运行不会自动安装 USB 服务、权限和打印队列。
尚未启用特性时，可将 `nix` 换成 `nix --extra-experimental-features 'nix-command flakes'`。
其他 Linux 发行版的服务集成需要手动配置，详见安装指南。

### 启用打印

在已导入模块的 NixOS 配置中，普通 L805 队列还需：

```nix
services.epson-printer-utility.cups.enable = true;
services.printing.drivers = [ pkgs.epson-escpr ];
```

`pkgs` 来自系统模块参数。模块准备后端与权限，不创建或迁移队列。
普通 ESC/P-R 队列使用 Linux 机型驱动，Windows RAW 队列由原厂驱动渲染；
二者可复用同一个 ecblp/ecbd 后端及共享锁。

队列创建、局域网 IPP 共享和 Windows 接入步骤集中在 [打印配置](docs/PRINTING.md)。
RAW 接入依赖仍支持传统后端的 CUPS 2.x，升级限制也在该指南中说明。

## 常用命令

先列出设备，复制返回的原生 ID 或 location，再查询对应设备：

```sh
epson-printer-cli devices --json
epson-printer-cli status --device 'NATIVE_ID_FROM_DEVICES' --json
epson-printer-cli ink --device 'NATIVE_ID_FROM_DEVICES' --json
epson-printer-cli paper-count --device 'NATIVE_ID_FROM_DEVICES' --json
```

`--device` 也支持完整型号或 `auto`；匹配多台时拒绝任取一台。
没有序列号的 USB 设备 ID 为 `USB`，指当前 ecbd 选择的唯一设备：

```sh
epson-printer-cli status --device USB --json
```

`--connection all|usb|network` 限制发现范围。USB 选择器默认只查 USB；
仅网络配置默认查 network，原生网络设备尚无实机验证。

### 手动维护

先装纸并确认设备空闲，再按需执行一次：

```sh
epson-printer-cli nozzle-check --device USB
epson-printer-cli clean --device USB --confirm-clean
```

喷嘴检查消耗纸张，普通清洗消耗墨水；没有 `--confirm-clean` 不执行清洗。
忙碌、离线或操作锁被占用时跳过；失败或超时记为“未确认”，不自动重发。
GUI 维护期间禁用重复提交；关闭维护窗口会等待当前工作结束。

设备上报的墨量不是墨仓实际液位测量；不可读值为未知／JSON `null`。
原生进纸计数也不是废墨计数器，没有重置接口。

### 脚本调用

v1.0.0 使用 **JSON schema 2**。脚本应检查 `outcome`、通信结果及设备错误，
不能只凭进程退出 0 判断打印机正常或物理清洗完成。
字段、设备标识、未知值及退出码见 [JSON 接口](docs/JSON.md)。

## 兼容性与验证范围

以下结果记录于 **2026-11-26（Asia/Singapore）**；Windows 结果来自维护者实机确认。

| 范围 | 已确认 | 尚未验证 |
| --- | --- | --- |
| L805 USB 查询 | 状态、实际墨色 ID、未知墨量、原生进纸计数 | 全部错误状态与其他墨色配置 |
| 项目喷嘴检查／普通清洗 | 历史实机输出和维护记录 | 完整的新 GUI 维护交互、timer 激活 |
| 普通 CUPS／远程 IPP | 多页 PDF；重启后权限、CUPS 服务与打印作业 | 打印期间主动触发维护 |
| Windows 原厂驱动／IPP RAW | 高质量 A4 相纸打印、喷嘴检查、大墨量冲洗成功 | 实际喷墨 DPI、光盘打印、Windows 双向状态查询及其他驱动组合 |
| 原生 Epson 网络维护 | 保留发现、连接与维护实现 | 网络设备及跨网段操作 |
| 其他机型／平台 | 两架构有原生构建记录 | 其他 Epson 机型、ARM 打印机硬件、其他发行版服务集成 |

Windows 原厂驱动的“高质量”不构成实际 DPI 的测量。
原厂维护数据经 RAW 队列提交时使用 ecblp 的锁，设备长时间动作是否完成仍需实际确认。
普通队列和 RAW 队列应按指南分别选择，避免重复渲染或把普通 PDF 直接透传给设备。

CUPS 远程 IPP 成功不代表 Epson 原生网络维护已验证，构建成功也不代表全机型兼容。
本项目没有为其他发行版提供原生安装器，也没有提供 CUPS 3 迁移实现。

## 文档索引

| 文档 | 内容 |
| --- | --- |
| [安装指南](docs/INSTALL.md) | NixOS、其他 Linux、缓存、设备选择与可选定时配置 |
| [打印配置](docs/PRINTING.md) | 普通队列、IPP 共享、Windows 原厂驱动 RAW 接入与排错 |
| [JSON 接口](docs/JSON.md) | schema 2、字段语义、兼容性变化与退出码 |
| [CHANGELOG](CHANGELOG.md) | 版本变化 |
| [源码来源](upstream/SOURCE.md) | 保留的官方输入、版本及校验值 |
| [Agent 上下文入口](AGENTS.md) | 架构、上游适配、设计决策、开发构建与验证证据索引 |

新增代码采用 [GPL-2.0-or-later](LICENSE)，上游文件保留各自许可与例外。
完整的版权、第三方及源码分发声明见 [NOTICE.md](NOTICE.md) 和 [LICENSES/](LICENSES/)。
