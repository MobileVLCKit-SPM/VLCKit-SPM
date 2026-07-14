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
            url: "https://github.com/MobileVLCKit-SPM/VLCKit-SPM/releases/download/4.0.0-alpha.20260713.1829/VLCKit-4.0.0-alpha.20260713.1829.zip",
            checksum: "ae1011f37a21183b11d8ddc10a59b96f190b8b76927363066739fc541ba6b85a"
        )
    ]
)
