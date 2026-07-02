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
            url: "https://github.com/MobileVLCKit-SPM/VLCKit-SPM/releases/download/0.0.0/VLCKit-0.0.0.zip",
            checksum: "0000000000000000000000000000000000000000000000000000000000000000"
        )
    ]
)
