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
            url: "https://github.com/MobileVLCKit-SPM/VLCKit-SPM/releases/download/3.7.3/VLCKit-3.7.3.zip",
            checksum: "58bb12cd3a4ea9f071fef97cbcc7ea92aedfd1e014bee0af09c48d75c60a520f"
        )
    ]
)
