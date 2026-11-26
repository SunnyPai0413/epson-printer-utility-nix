# 现有开发构建与 CI

[Agent 索引](../AGENTS.md) · [上游适配](UPSTREAM.md) · [验证记录](VALIDATION.md)

以下命令和检查来自原 README、现有 Flake 与 CI，仅说明已有行为，不增加必跑项或发布步骤。

## 本地入口

在仓库根目录：

```sh
nix build .#default
nix flake check .
nix flake check . --all-systems --no-build
nix develop .
```

前两条针对当前架构构建／检查；`--all-systems --no-build` 只求值，不代替另一架构的实际构建。
Git 工作区 Flake 引用过滤已忽略文件；新增构建源文件未纳入 Git 跟踪时，不会进入该引用。
NixOS 安装和缓存下载说明属于 [用户安装指南](../docs/INSTALL.md)。

## 包与构建定义

- [flake.nix](../flake.nix)：`x86_64-linux`、`aarch64-linux` 的 packages、apps、devShell 和 checks。
- [nix/packages.nix](../nix/packages.nix)：显式源码 fileset、归档解包、适配脚本、依赖及包检查。
- [CMakeLists.txt](../CMakeLists.txt)：原生程序、Qt 资源、安装项及 CTest。
- [nix/module.nix](../nix/module.nix)：独立的 NixOS 服务与权限集成，不创建队列。

`#default` 是 utility 与 backend 的 symlinkJoin；`#epson-printer-utility` 包含 GUI／CLI，`#epson-backend` 包含 ecbd／ecblp，`#ecblp` 是 backend 的别名。
应用入口有 `#gui`、`#cli`、`#ecbd`；默认 app 为 GUI。

CMake 按上游 `EPSCommonLib/Makefile.am` 的源文件清单构建，沿用 Epson 将其中 `.c` 作为 C++ 编译的方式。
主要依赖来自 Nix：Qt5、libusb1、libjpeg、Threads、CMake、pkg-config 和 Python3。
README／docs／`.agents` 不在现有包源码 fileset 中；根目录 CHANGELOG 则属于打包和安装材料。

## 已有检查覆盖

| 入口 | 已存在的覆盖 |
| --- | --- |
| Utility CTest | 公共报告、原生 USB／网络解析、修改声明、离线 CLI |
| Backend CTest | 实际 ecblp 对临时 FIFO 的传输、锁、背压、取消与读端丢失 |
| Flake checks | Utility、Backend、NixOS 模块、原始来源完整性 |

测试定义在 [tests/](../tests/)；源码与结果的版本对应关系见 [验证上下文](VALIDATION.md)。
这些检查不使用打印机硬件，成功结果不能推导机型兼容性。

## 已有 GitHub Actions 配置

两个架构各自使用原生 Runner：`ubuntu-24.04` 与 `ubuntu-24.04-arm`，不交叉编译。
入口工作流是 [x86_64](../.github/workflows/cache-x86_64-linux.yml) 和 [aarch64](../.github/workflows/cache-aarch64-linux.yml)，共用 [build-cache.yml](../.github/workflows/build-cache.yml)。
现有触发器为 `main` 推送、`v*` Tag 推送与手动触发；这里描述触发条件，不授权远程推送或移动 Tag。

现有仓库配置：

| 类型 | 名称 | 含义 |
| --- | --- | --- |
| Actions Variable | `CACHIX_CACHE_NAME` | 缓存名，不含地址前缀／后缀 |
| Actions Secret | `CACHIX_AUTH_TOKEN` | 该缓存的写入 Token |

原 README 中的缓存创建选项是 Public、Managed by Cachix；私有缓存的下载者另需只读凭据。
缺少任一 Actions 配置时，工作流在安装 Nix 和构建前报错，Token 仅从 Secret 读取。

各架构构建 default、utility、backend 三个输出，Nix 复用共享依赖；`ecblp` 别名不另建。
只有该架构全部构建成功后才启用 `cachix/cachix-action@v17`，通过 `pathsToPush` 上传限定输出及运行依赖。
`pathsToPush` 使用空格分隔，既有参数分隔修复不应被误读为换行列表。
不扫描整个 store，不额外执行 `cachix push`；一个架构失败不会取消另一个架构，也不会为失败架构上传。
此流程只发布 Nix 缓存，不创建 GitHub Release。历史成功运行链接集中在 [验证记录](VALIDATION.md#ci-与版本背景)。
