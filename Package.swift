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
            url: "https://github.com/MobileVLCKit-SPM/VLCKit-SPM/releases/download/4.0.0-alpha.20260720.1538/VLCKit-4.0.0-alpha.20260720.1538.zip",
            checksum: "b8bf91bcc2faaac80ed584c91dab3f9ec31a0335b41d2e9ae9995ab79d49e1a6"
        )
    ]
)
