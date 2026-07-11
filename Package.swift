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
            url: "https://github.com/MobileVLCKit-SPM/VLCKit-SPM/releases/download/4.0.0-alpha.20260706.1303/VLCKit-4.0.0-alpha.20260706.1303.zip",
            checksum: "76d1ba4216dda2290d49550d730eeb6c8d5123385feaa0771d2744ba1d5188ca"
        )
    ]
)
