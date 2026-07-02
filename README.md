# VLCKit-SPM

Swift Package Manager mirror for official VideoLAN VLCKit prebuilt packages.

This repository converts VideoLAN archives from:

- `https://download.videolan.org/pub/cocoapods/prod/`
- `https://download.videolan.org/pub/cocoapods/unstable/`

into SwiftPM-compatible binary target zip assets hosted on GitHub Releases.

## Usage

Stable release:

```swift
.package(url: "https://github.com/MobileVLCKit-SPM/VLCKit-SPM.git", from: "3.7.3")
```

Latest unstable branch:

```swift
.package(url: "https://github.com/MobileVLCKit-SPM/VLCKit-SPM.git", branch: "unstable")
```

Exact prerelease tag:

```swift
.package(url: "https://github.com/MobileVLCKit-SPM/VLCKit-SPM.git", exact: "4.0.0-alpha.18")
```

## Automation

The conversion script is `scripts/vlckit_spm.py`.

Check latest stable package:

```bash
python3 scripts/vlckit_spm.py check --channel prod --kit VLCKit --version latest
```

Build a SwiftPM binary target zip and generate `Package.swift`:

```bash
python3 scripts/vlckit_spm.py build \
  --channel prod \
  --kit VLCKit \
  --version latest \
  --repo MobileVLCKit-SPM/VLCKit-SPM
```

GitHub Actions runs the same script, commits generated metadata, creates a tag,
and uploads the generated zip to the matching GitHub Release.
