# VLCKit SwiftPM Mirror 第一版计划

## 目标

将 VideoLAN 官方发布的 VLCKit 预编译包自动转换为 Swift Package
Manager 可直接依赖的二进制包。

官方源目录：

- `https://download.videolan.org/pub/cocoapods/prod/`
- `https://download.videolan.org/pub/cocoapods/unstable/`

本仓库负责：

1. 定时检查官方目录是否有新版本。
2. 下载官方归档包。
3. 解包并整理为 SwiftPM 支持的 `.xcframework` zip。
4. 计算 SwiftPM checksum。
5. 将 zip 上传到 GitHub Release 或 prerelease。
6. 自动更新 `Package.swift`、metadata、分支和 tag。
7. 让外部项目可以直接通过 tag 或 branch 依赖本仓库。

## 使用方式

稳定版使用 SemVer tag：

```swift
.package(url: "https://github.com/<owner>/VLCKit-SPM.git", from: "3.7.3")
```

指定 unstable 的某个 prerelease 版本：

```swift
.package(url: "https://github.com/<owner>/VLCKit-SPM.git", exact: "4.0.0-alpha.18")
```

跟随最新 unstable 分支：

```swift
.package(url: "https://github.com/<owner>/VLCKit-SPM.git", branch: "unstable")
```

## 仓库结构

```text
VLCKit-SPM/
  Package.swift
  README.md
  LICENSE
  PLAN.md
  scripts/
    vlckit_spm.py
  metadata/
    prod.json
    unstable.json
  .github/
    workflows/
      check-and-release.yml
```

不提交构建产物：

```text
.cache/
dist/
```

`dist/` 中的 SwiftPM zip 只作为 GitHub Release asset 发布。

## 分支和发布模型

维护两个移动分支和一组不可变 tag：

```text
master
  默认开发分支，保存脚本、workflow 和文档。

prod
  指向最新稳定版 VLCKit 包。

unstable
  指向最新 alpha、beta 或 rc 版本。

tags
  稳定版示例：3.7.3
  prerelease 示例：4.0.0-alpha.18
```

GitHub Release 规则：

- `prod` 目录里的稳定版创建普通 GitHub Release。
- `unstable` 目录里的 alpha、beta、rc 创建 GitHub prerelease。
- 每个 Release 上传一个 SwiftPM 可用的 zip asset。
- `Package.swift` 中的 binary target URL 指向对应 Release asset。
- tag 一旦创建，不自动移动。
- 第一版固定使用当前默认分支 `master`。如需迁移到 `main`，后续单独处理。

## 版本规范

SwiftPM 依赖 tag 时要求 SemVer。VideoLAN unstable 版本可能不是合法 SemVer，
例如 `4.0.0a18`，因此需要规范化。

推荐映射：

```text
3.7.3       -> 3.7.3
4.0.0a18    -> 4.0.0-alpha.18
4.0.0b2     -> 4.0.0-beta.2
4.0.0rc1    -> 4.0.0-rc.1
```

保留原始版本号和原始文件名用于追踪。

metadata 示例：

```json
{
  "kit": "VLCKit",
  "channel": "unstable",
  "upstream_version": "4.0.0a18",
  "normalized_version": "4.0.0-alpha.18",
  "tag": "4.0.0-alpha.18",
  "source_url": "https://download.videolan.org/pub/cocoapods/unstable/VLCKit-4.0.0a18-844dff57e-c833c4be0.tar.xz",
  "upstream_filename": "VLCKit-4.0.0a18-844dff57e-c833c4be0.tar.xz",
  "asset_name": "VLCKit-4.0.0-alpha.18.zip",
  "checksum": "<swiftpm-checksum>",
  "source_sha256": "<source-archive-sha256>"
}
```

## Python 脚本设计

脚本路径：

```text
scripts/vlckit_spm.py
```

第一版命令：

```bash
python3 scripts/vlckit_spm.py check \
  --channel prod \
  --kit VLCKit \
  --version latest

python3 scripts/vlckit_spm.py build \
  --channel prod \
  --kit VLCKit \
  --version latest \
  --output dist

python3 scripts/vlckit_spm.py write-package \
  --kit VLCKit \
  --version 3.7.3 \
  --url https://github.com/<owner>/VLCKit-SPM/releases/download/3.7.3/VLCKit-3.7.3.zip \
  --checksum <checksum>

python3 scripts/vlckit_spm.py release \
  --channel prod \
  --kit VLCKit \
  --version latest \
  --repo <owner>/VLCKit-SPM
```

脚本职责：

1. 拉取 VideoLAN `prod` 或 `unstable` 目录索引。
2. 解析归档文件名、修改时间和大小。
3. 根据 `latest` 或指定版本选择目标包。
4. 从文件名提取 upstream version。
5. 将 upstream version 规范化为 SwiftPM 可用 SemVer。
6. 对比 `metadata/<channel>.json`，没有新版本时正常退出。
7. 下载官方归档。
8. 如果目录索引提供大小，校验下载大小。
9. 计算官方源归档 SHA256。
10. 解压 `.tar.xz` 或 `.zip`。
11. 查找 `.xcframework`。
12. 如果只存在 `.framework`，在 macOS runner 上使用
    `xcodebuild -create-xcframework` 生成 `.xcframework`。
13. 将 `.xcframework` 重新压缩成 SwiftPM binary target zip。
14. 使用 `swift package compute-checksum` 计算 checksum。
15. 生成 `Package.swift`。
16. 写入 `metadata/<channel>.json`。
17. 输出 GitHub Actions 需要的变量：version、tag、asset path、
    checksum、source URL、是否 prerelease。

SwiftPM zip 的根目录必须直接包含 `.xcframework`，不能多出 `dist/`、
临时目录或其他外层目录。推荐打包方式：

```bash
mkdir -p dist staging
cp -R build/VLCKit.xcframework staging/VLCKit.xcframework
cd staging
zip -r ../dist/VLCKit-<version>.zip VLCKit.xcframework
```

zip 内部结构应为：

```text
VLCKit.xcframework/
  Info.plist
  ...
```

第一版优先支持：

- `kit`: `VLCKit`
- `channel`: `prod`
- `version`: `latest`

随后扩展：

- `unstable`
- prerelease SemVer 规范化
- `MobileVLCKit`
- `TVVLCKit`

## Package.swift 模板

生成 remote binary target：

```swift
// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "VLCKit-SPM",
    platforms: [
        .iOS(.v12),
        .tvOS(.v12),
        .macOS(.v10_13)
    ],
    products: [
        .library(name: "VLCKit", targets: ["VLCKit"])
    ],
    targets: [
        .binaryTarget(
            name: "VLCKit",
            url: "https://github.com/<owner>/VLCKit-SPM/releases/download/3.7.3/VLCKit-3.7.3.zip",
            checksum: "<checksum>"
        )
    ]
)
```

平台版本需要在实际解包后读取 `.xcframework/Info.plist` 再确认。

## GitHub Actions 设计

workflow 路径：

```text
.github/workflows/check-and-release.yml
```

触发方式：

```yaml
name: Check and Release VLCKit

on:
  workflow_dispatch:
    inputs:
      channel:
        description: prod or unstable
        required: true
        default: prod
      kit:
        description: VLCKit, MobileVLCKit, or TVVLCKit
        required: true
        default: VLCKit
      version:
        description: latest or exact upstream version
        required: true
        default: latest
  schedule:
    - cron: "30 2 * * *"

permissions:
  contents: write
```

使用 macOS runner：

```yaml
jobs:
  check-and-release:
    runs-on: macos-15
```

主要步骤：

1. `actions/checkout`，拉取完整历史和 tag。
2. 配置 git author。
3. 运行 Python 脚本检查并构建。
4. 如果没有新版本，结束 workflow。
5. 生成 `Package.swift`、`README.md`、`metadata/<channel>.json`。
6. 提交生成文件。
7. 推送到对应 channel branch。
8. 创建并推送规范化后的 tag。
9. 基于已经存在的 tag 创建或更新 GitHub Release。
10. 上传生成的 zip asset。
11. 使用最终 Release asset URL 做一次 consumer 解析验证。
12. 对 stable 版本，可选同步到默认分支。

必须先提交并推送 tag，再创建 GitHub Release。不要让
`gh release create "$TAG"` 隐式创建 tag，否则 tag 可能指向默认分支旧提交，
而不是包含当前 `Package.swift` 和 checksum 的提交。

## GitHub Release 命令

稳定版：

```bash
gh release create "$TAG" "$ASSET" \
  --title "$TAG" \
  --notes-file release-notes.md \
  --target "$TAG"
```

unstable prerelease：

```bash
gh release create "$TAG" "$ASSET" \
  --title "$TAG" \
  --notes-file release-notes.md \
  --prerelease \
  --target "$TAG"
```

如果 Release 已存在，替换 asset：

```bash
gh release upload "$TAG" "$ASSET" --clobber
```

## 分支和 tag 行为

`prod`：

```bash
git push origin HEAD:prod
git tag 3.7.3
git push origin 3.7.3
```

`unstable`：

```bash
git push origin HEAD:unstable
git tag 4.0.0-alpha.18
git push origin 4.0.0-alpha.18
```

要求：

- 创建 tag 前必须检查远端和本地是否已存在。
- 已存在的 tag 不自动删除、不自动移动。
- channel branch 可以前进更新。
- Release asset 可用 `--clobber` 替换，但 checksum 变化必须同步更新
  `Package.swift` 和 metadata。

## 验证

发布前最小验证：

```bash
swift package compute-checksum dist/VLCKit-<version>.zip
swift package dump-package
unzip -l dist/VLCKit-<version>.zip | head
```

推荐额外验证：

1. 创建临时 SwiftPM consumer package。
2. 使用最终 GitHub Release asset URL 写入本仓库生成的 `Package.swift`。
3. 添加本仓库对应 tag 或 branch 作为依赖。
4. 如需要，创建最小 iOS/macOS sample project。
5. 使用 `xcodebuild -resolvePackageDependencies` 验证 Xcode 可解析。

第一版发布后验证必须覆盖最终远端 URL，而不是只验证本地 zip。否则
GitHub Release asset URL、权限、重定向或 zip 根目录结构问题可能在发布后才暴露。

## 第一版交付范围

第一版只做可闭环的最小版本：

- 新增 `scripts/vlckit_spm.py`。
- 支持检查 `prod` 最新 `VLCKit`。
- 支持下载、解压、定位或生成 `.xcframework`。
- 支持打包 SwiftPM zip。
- 支持计算 checksum。
- 支持生成 `Package.swift`。
- 支持写入 `metadata/prod.json`。
- 新增 GitHub Actions workflow。
- 支持将 zip 上传到 GitHub Release。
- 支持推送 `prod` 分支和稳定版 tag。

第二阶段再做：

- `unstable` 自动发布到 prerelease。
- alpha、beta、rc 版本规范化。
- `MobileVLCKit` 和 `TVVLCKit`。
- release notes 自动生成。
- 默认分支是否同步最新稳定版。

## 风险和待确认项

1. 需要确认官方归档中是否已经包含 `.xcframework`。
2. 如果只有 `.framework`，需要确认每个平台 framework 的组合方式。
3. 需要确认 `VLCKit`、`MobileVLCKit`、`TVVLCKit` 的目标命名是否统一。
4. 需要确认最低平台版本。
5. 需要确认 GitHub Release asset URL 是否使用公开仓库地址。
6. 需要决定后续是否将默认分支从 `master` 迁移到 `main`。
7. 需要决定 stable 是否先发 prerelease 人工验证，再提升为正式 release。
