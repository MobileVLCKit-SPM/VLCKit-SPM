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
            url: "https://github.com/MobileVLCKit-SPM/VLCKit-SPM/releases/download/4.0.0-alpha.19/VLCKit-4.0.0-alpha.19.zip",
            checksum: "bba8590a2f98a3c7c180e742d9ef27c660c5055b5de203c755a5d8f27404526a"
        )
    ]
)
