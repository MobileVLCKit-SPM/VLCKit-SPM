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
            checksum: "9f26c3037ce72ab27758ee8e60cb38102197587fd79359a2674b141781cf8b3f"
        )
    ]
)
