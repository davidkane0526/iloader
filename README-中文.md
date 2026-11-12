# HermesEnabler Windows-only 安装器

本项目对应 [HermesEnabler Issue #54](https://github.com/pookjw/HermesEnabler/issues/54)。

## 构建说明

本仓库是一个可复现的 **patch overlay**，不是完整的 iLoader 上游镜像。
工作流自动检出 `AndreySemjonov/iloader` 提交
`2d13485ef2d7107b2bc2ec6cdb5f54ce5729ef70`，然后执行
`python apply_patch.py --root upstream`，将 `cli` 目录放入上游源码中，
最后在 `windows-2022` 上编译。不会上传或使用 Apple ID。

1. 打开仓库 Actions → **Build HermesEnabler Windows CLI**。
2. 选择 `feat/hermes-win-watch-cli` 分支运行（如果没有自动触发）。
3. 成功后下载 `iloader-cli-windows-x64` artifact，解压后得到 `iloader-cli.exe`。
4. 下载 [HermesEnabler 官方原版 IPA](https://github.com/pookjw/HermesEnabler/releases/latest)，**不要预先重签或修改 Bundle ID**。
5. Windows 安装官方 Apple Mobile Device 支持组件，iPhone 开启开发者模式并使用 USB 连接电脑、信任此电脑。Apple Watch 也需要开发者模式。
6. 在 PowerShell 中执行：

```powershell
.\iloader-cli.exe .\HermesEnabler.ipa
```

7. 在本地控制台输入 Apple ID、密码和 2FA 验证码，等待安装结果。

## 核心修复

- Windows Anisette 数据：从 `https://ani.jkcoxson.com/v3/client_info` 动态获取 `client_info`、`user_agent`；
- 同时为 Watch 应用关联 App Group，传递 `DeveloperDeviceType::Watchos`；
- 安装前验证 Watch provisioning profile 的 App Group entitlement；
- 固定签名依赖的 Git revision，以提高构建可复现性；
- 明确初始化 rustls ring crypto provider。

## 注意

- 若发生 Apple 开发证书上限错误，**默认不撤销任何证书**；只有在本地完整输入证书序列号并再次输入 `REVOKE` 才会执行撤销。撤销会影响使用旧证书签名的其他应用。
- 免费 Apple ID 开发签名通常七天有效，需要重新签名安装。
- iPhone / Watch 上安装应用成功，不等于必然有权修改 MobileGestalt，也不能保证某个 watchOS 版本兼容。
- `Backup MG` 必须确保未曾用已修改的 MobileGestalt 覆盖原始备份；升级或重装时不要盲目重复备份。
- 外部 Anisette 服务是第三方服务；不要将 Apple ID 密码、2FA 或签名私钥提交到 Issue、GitHub Secrets 或 CI 日志。
- **构建验证已通过：** [GitHub Actions #43153944527](https://github.com/davidkane0526/iloader/actions/runs/43153944527)，已生成 12,387,840 字节的 Windows x64 EXE。\n\nSHA-256：`923c7fe46b792d9f6a427165c41d1767e842b83ce274d9efa220743c6db626b1`。\n\n**实机安装仍需在 Apple Watch 上验证。**
