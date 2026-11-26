# 验证上下文与历史证据

[Agent 索引](../AGENTS.md) · [CHANGELOG](../CHANGELOG.md) · [用户兼容性摘要](../README.md#兼容性与验证范围)

日期均为 Asia/Singapore。本文集中维护原发布说明与验证 README 的证据范围；原始日志和历史检查文本仍在 [validation/](../validation/)。
已有日志中的主机名、PID 和 store hash 曾被脱敏，源码 SHA-256 保持原值。本文不是安装教程；用户配置见 [docs/](../docs/)。

## v1.0.0

首个正式公开版本为项目 1.0.0；保留的上游版本是 Utility 1.1.3／Backend 1.3.1，JSON schema 为 2。
功能变化集中于 [CHANGELOG](../CHANGELOG.md)，接口兼容性见 [JSON 文档](../docs/JSON.md)，不在这里重复安装步骤。

2026-11-26 的原始发布准备结果见 [v1.0.0-checks.txt](../validation/v1.0.0-checks.txt)：

- 本地 default、utility、backend 构建；五项 Utility CTest 和一项 Backend CTest。
- x86_64 的四项 flake checks；两架构全部输出的求值，ARM 求值不当作新 ARM 构建。
- 当时 README 的七份 Nix 示例、模块权限／ACL、用户组、队列和 timer 默认行为。
- 已安装版本、来源校验、许可证／修改声明及文档引用。

该文件是历史记录：里面的旧路径、示例数量、未提交状态及“当前 CHANGELOG”均描述当时快照，不代表本轮重新执行。

## L805 普通打印与重启

维护者于 2026-11-26 确认：ecblp 背压修复 `2cb2500` 后，远程 IPP 多页 PDF 成功出纸；持久 ACL 修复 `138ad2f` 后，重启验证通过运行权限、CUPS 服务和打印作业。

路径：`远程客户端 → IPP → NixOS CUPS → 机型驱动 → ecblp/ecbd → USB L805`。
这验证 CUPS 共享和 USB 传输，不验证 Epson 原生网络维护。
这两项是维护者提供的实机／重启确认，没有新增原始硬件 transcript；文档整理没有重复打印、清洗或重启。

## Windows IPP RAW 实机确认

维护者于 2026-11-26 确认 USB L805 的以下操作成功：

| 操作 | 发起方与证据 |
| --- | --- |
| 高质量 A4 相纸打印 | Windows Epson 原厂驱动；维护者确认实际输出成功 |
| 喷嘴检查 | Windows Epson 原厂驱动维护页；维护者确认成功 |
| 大墨量冲洗／Power Ink Flushing | Windows Epson 原厂驱动维护页；维护者确认成功 |

路径：`Windows 应用／Epson 原厂驱动 → IPP → CUPS RAW 队列 → ecblp/ecbd → USB L805`。
普通和 RAW 队列的接入教程集中在 [打印配置](../docs/PRINTING.md#windows-原厂驱动cups-ipp-raw-队列)。

大墨量冲洗由 Windows 原厂驱动提供，不是本项目 GUI、CLI 或定时维护接口；项目 `clean` 仍为普通清洗。
维护者未提供 Windows／驱动版本、具体相纸产品、实测 DPI 或新的原始硬件日志，不补造这些信息。
**实际喷墨 DPI、光盘打印和 Windows 双向状态查询尚未验证。**

共享锁串行化 ecblp 提交，但没有证明长时间 Windows 维护动作完成前的完整锁覆盖；也没有验证主动在打印中触发维护。
本次文档整理不创建队列、不修改服务或 Windows 设置，也不重复这些实机操作。

## CI 与版本背景

发布前基线 `138ad2f59c20750c66e73173aa0990a27a259335` 在 2026-11-26 的原生构建和 Cachix 上传记录：

| 系统 | Runner | 固定证据 |
| --- | --- | --- |
| x86_64-linux | ubuntu-24.04 | [run 45826063829](https://github.com/SunnyPai0413/epson-printer-utility-nix/actions/runs/45826063829) |
| aarch64-linux | ubuntu-24.04-arm | [run 45826063836](https://github.com/SunnyPai0413/epson-printer-utility-nix/actions/runs/45826063836) |

每次运行构建 default、utility、backend，包括包内 CTest，并完成 Cachix 发布及 post step；CI 不执行硬件测试，也不运行单独的模块／来源 flake checks。
这些运行早于版本号变更，只证明发布前基线；没有据此确认最终 Tag 对应的 CI 或缓存。
此次文档重排保持 VERSION=1.0.0 和已有 Tag，不创建 Release，不新增发布流程。

## 保留的 0.2.0 证据

[current-checks.txt](../validation/current-checks.txt) 记录了当时的全新本地 checkout 构建、四项 flake checks、文件修改声明跟进以及当前树和新 checkout 的包源码一致性。
原始归档、fixtures 与该时点的构建结果分别保留，不能将历史命令默认解释为本轮要求。

[current-usb.json](../validation/current-usb.json) 与 [current-gui.txt](../validation/current-gui.txt) 是内部 0.2.0 的只读硬件／桌面证据：

- NixOS x86_64 的 USB L805 枚举、原生 ID、idle／无错误／警告 0。
- 六个墨色按设备顺序报告：cyan、magenta、light-magenta、light-cyan、black、yellow；保留 ST2 type/color ID。
- 原始墨量均为 105／NOREAD，设备关闭显示，百分比为 null；没有将其解释为物理液位。
- 原生进纸计数：彩色 83,594，黑白 1,497，总计 85,091；blank 77，彩色无边距 2,177，黑白无边距 0，ADF 不可用。
- ecblp 发现共享 FIFO，没有提交任务；临时 ecbd 在只读回归后退出，CUPS 前后均保持运行。
- 新 GUI 在 ecbd 停止时于 X11／XWayland 启动，没有按维护按钮，不证明完整维护交互。

当时未验证的 CUPS 出纸、重启持久性与 ARM 构建，已由上方较晚的证据分别更新。其他硬件边界仍保留。

## 更早的 L805 维护记录

原记录日期为 2026-11-25 至 26，早于 schema 2；旧日志的固定六行墨色及按数量推断 photo black 的结果不是当前接口契约。

- [physical-confirmation.txt](../validation/physical-confirmation.txt)：最初喷嘴图案／普通清洗的人类确认；黄色图案最初不清晰。一次后续通信失败使软件结果未确认，没有自动重放。
- [clean.json](../validation/clean.json)、[第 1 轮](../validation/y-clean-round-1/)、[第 2 轮](../validation/y-clean-round-2/)、[第 3 轮](../validation/y-clean-round-3/)：最初一次普通清洗，随后三轮每轮两次清洗与一次喷嘴检查，共七次历史普通清洗调用。它们是过去逐次授权的证据，不是建议重复的流程；最后一轮实际图案质量未确认。
- `nozzle-service*`：手动启动过 oneshot，timer 始终关闭；新 timer 激活没有实机验证。
- `gui-*.txt`／`gui-*.log`：旧 GUI 的真实桌面／离线窗口证据，不能证明新的异步维护交互。
- [build-final.log](../validation/build-final.log)、[flake-check.log](../validation/flake-check.log)、[devshell.log](../validation/devshell.log)：更早的构建／检查／开发 shell 日志，名称中的 final 不表示当前最终版本。
- [result-summary.txt](../validation/result-summary.txt) 是已被后续记录取代的部分摘要；[runtime-test.sh](../validation/runtime-test.sh) 是历史开发辅助脚本，不是用户安装入口。

旧 `status*.json` 与 `ink.json` 记录设备报告；墨量未知不是实际液位测量，原生进纸计数也不是成功打印页数。

## 尚未验证

- 所有其他 Epson 机型，以及 aarch64 上的打印机硬件。
- Epson 原生网络发现、状态、维护与跨网段连接。
- 完整的新 GUI 维护交互、timer 激活、打印期间主动发起维护。
- 实际喷墨 DPI、光盘打印、Windows 双向状态查询和其他 Windows／驱动组合。
- 其他 Linux 发行版的原生安装／服务集成；CUPS 3 接入迁移。

原有 fixtures 覆盖 USB／网络解析、公共模型、设备歧义、未知值、离线 CLI、FIFO 和模块配置；通过这些检查或完成构建，不能推导硬件兼容性。

## 文档重排

原 README 的开发和维护者 CI 内容已分入其余 `.agents` 文档；原 `docs/RELEASE-NOTES.md` 与 `validation/README.md` 的重复叙述合并到本文。
`validation/` 只保留原始证据及指向这里的短索引，历史检查文件没有改写。
本轮只做文档分类、链接、示例语法和变更范围核对，不重新运行构建或实机操作，也不增加测试要求。
