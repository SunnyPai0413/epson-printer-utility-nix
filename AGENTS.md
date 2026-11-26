# AI Agent 开发上下文

本项目将 Epson Printer Utility 1.1.3 和 epson-backend 1.3.1 原生打包为 Nix Flake，
以 NixOS 集成为主。项目版本见 [VERSION](VERSION)，与两个上游版本独立。

## 项目边界

- 不要未经允许直接向远程推送变更。
- 保留原始源码归档、校验值及各文件许可证；来源见 [upstream/SOURCE.md](upstream/SOURCE.md)，许可见 [NOTICE.md](NOTICE.md)。
- 项目维护入口限于喷嘴检查和普通清洗；Windows 原厂驱动的大墨量冲洗不属于本项目 GUI、CLI 或定时接口。
- ecblp 是传输后端，机型渲染由 Linux ESC/P-R 或 Windows 原厂驱动承担；不要据高质量选项推定实际喷墨 DPI。
- 现有实机证据限于 USB L805；构建、解析 fixtures 与远程 IPP 成功均不能推导全机型或 Epson 原生网络维护兼容性。

## 按需阅读

| 要了解的内容 | 文档 |
| --- | --- |
| 组件、USB／网络／CUPS 数据路径与共享资源 | [.agents/ARCHITECTURE.md](.agents/ARCHITECTURE.md) |
| 保留的上游输入、适配点和许可处理 | [.agents/UPSTREAM.md](.agents/UPSTREAM.md) |
| 已有设计选择及其理由 | [.agents/DECISIONS.md](.agents/DECISIONS.md) |
| 现有构建命令、包输出、CI 与 Cachix 配置 | [.agents/DEVELOPMENT.md](.agents/DEVELOPMENT.md) |
| 版本背景、实机确认、历史检查和未验证项 | [.agents/VALIDATION.md](.agents/VALIDATION.md) |

用户入口为 [README](README.md)，详细指南仅放在 [docs/](docs/)。
以上是现有实现与证据的索引，不新增开发流程或测试要求。
