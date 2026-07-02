#!/usr/bin/env python3
from __future__ import annotations

import argparse
import dataclasses
import hashlib
import html.parser
import json
import os
import pathlib
import re
import shutil
import subprocess
import tarfile
import urllib.parse
import urllib.request
import zipfile


BASE_URL = "https://download.videolan.org/pub/cocoapods"
SUPPORTED_KITS = ("VLCKit", "MobileVLCKit", "TVVLCKit")
CHANNELS = ("prod", "unstable")


@dataclasses.dataclass(frozen=True)
class Archive:
    kit: str
    channel: str
    upstream_version: str
    normalized_version: str
    filename: str
    url: str
    size: int | None = None

    @property
    def tag(self) -> str:
        return self.normalized_version

    @property
    def prerelease(self) -> bool:
        return "-" in self.normalized_version

    @property
    def asset_name(self) -> str:
        return f"{self.kit}-{self.normalized_version}.zip"


class LinkParser(html.parser.HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a":
            return
        for name, value in attrs:
            if name.lower() == "href" and value:
                self.links.append(value)


def fail(message: str) -> None:
    raise SystemExit(f"error: {message}")


def read_url(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "VLCKit-SPM/1.0"})
    with urllib.request.urlopen(req, timeout=60) as response:
        return response.read()


def sha256_file(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalize_version(version: str) -> str:
    match = re.fullmatch(r"(\d+\.\d+\.\d+)(?:([ab]|rc)(\d+))?", version)
    if not match:
        fail(f"unsupported upstream version: {version}")
    base, marker, number = match.groups()
    if marker is None:
        return base
    label = {"a": "alpha", "b": "beta", "rc": "rc"}[marker]
    return f"{base}-{label}.{number}"


def version_key(version: str) -> tuple[int, int, int, int, int]:
    match = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)(?:-([A-Za-z]+)\.(\d+))?", version)
    if not match:
        fail(f"unsupported normalized version: {version}")
    major, minor, patch, label, number = match.groups()
    label_rank = {"alpha": 0, "beta": 1, "rc": 2, None: 3}.get(label)
    if label_rank is None:
        fail(f"unsupported prerelease label: {label}")
    return (int(major), int(minor), int(patch), label_rank, int(number or 0))


def parse_archive_filename(channel: str, kit: str, filename: str) -> Archive | None:
    pattern = rf"^({re.escape(kit)})-(\d+\.\d+\.\d+(?:(?:a|b|rc)\d+)?)-.+\.(tar\.xz|zip)$"
    match = re.fullmatch(pattern, filename)
    if not match:
        return None
    upstream_version = match.group(2)
    normalized = normalize_version(upstream_version)
    url = f"{BASE_URL}/{channel}/{urllib.parse.quote(filename)}"
    return Archive(
        kit=kit,
        channel=channel,
        upstream_version=upstream_version,
        normalized_version=normalized,
        filename=filename,
        url=url,
    )


def fetch_archives(channel: str, kit: str) -> list[Archive]:
    index_url = f"{BASE_URL}/{channel}/"
    parser = LinkParser()
    parser.feed(read_url(index_url).decode("utf-8", errors="replace"))
    archives: list[Archive] = []
    seen: set[str] = set()
    for link in parser.links:
        filename = pathlib.PurePosixPath(urllib.parse.unquote(link)).name
        if filename in seen:
            continue
        seen.add(filename)
        archive = parse_archive_filename(channel, kit, filename)
        if archive:
            archives.append(archive)
    return sorted(archives, key=lambda item: version_key(item.normalized_version))


def select_archive(channel: str, kit: str, version: str) -> Archive:
    archives = fetch_archives(channel, kit)
    if not archives:
        fail(f"no archives found for {kit} in {channel}")
    if version == "latest":
        return archives[-1]
    requested = normalize_version(version) if re.search(r"(?:a|b|rc)\d+$", version) else version
    for archive in archives:
        if archive.upstream_version == version or archive.normalized_version == requested:
            return archive
    fail(f"version {version} not found for {kit} in {channel}")


def load_metadata(path: pathlib.Path) -> dict[str, object]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def write_json(path: pathlib.Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def download_archive(archive: Archive, cache_dir: pathlib.Path) -> pathlib.Path:
    cache_dir.mkdir(parents=True, exist_ok=True)
    path = cache_dir / archive.filename
    if path.exists():
        return path
    tmp = path.with_suffix(path.suffix + ".tmp")
    req = urllib.request.Request(archive.url, headers={"User-Agent": "VLCKit-SPM/1.0"})
    with urllib.request.urlopen(req, timeout=600) as response, tmp.open("wb") as out:
        shutil.copyfileobj(response, out)
    tmp.replace(path)
    return path


def safe_extract_tar(archive_path: pathlib.Path, destination: pathlib.Path) -> None:
    destination = destination.resolve()
    with tarfile.open(archive_path) as tar:
        for member in tar.getmembers():
            target = (destination / member.name).resolve()
            if target != destination and not str(target).startswith(str(destination) + os.sep):
                fail(f"unsafe path in tar archive: {member.name}")
        tar.extractall(destination)


def safe_extract_zip(archive_path: pathlib.Path, destination: pathlib.Path) -> None:
    destination = destination.resolve()
    with zipfile.ZipFile(archive_path) as zf:
        for member in zf.namelist():
            target = (destination / member).resolve()
            if target != destination and not str(target).startswith(str(destination) + os.sep):
                fail(f"unsafe path in zip archive: {member}")
        zf.extractall(destination)


def extract_archive(archive_path: pathlib.Path, destination: pathlib.Path) -> None:
    if destination.exists():
        shutil.rmtree(destination)
    destination.mkdir(parents=True)
    if archive_path.name.endswith(".tar.xz"):
        safe_extract_tar(archive_path, destination)
    elif archive_path.name.endswith(".zip"):
        safe_extract_zip(archive_path, destination)
    else:
        fail(f"unsupported archive format: {archive_path}")


def find_xcframework(root: pathlib.Path, kit: str) -> pathlib.Path | None:
    candidates = sorted(root.rglob("*.xcframework"))
    if not candidates:
        return None
    for candidate in candidates:
        if candidate.name == f"{kit}.xcframework":
            return candidate
    return candidates[0]


def find_frameworks(root: pathlib.Path, kit: str) -> list[pathlib.Path]:
    exact = sorted(root.rglob(f"{kit}.framework"))
    if exact:
        return exact
    return sorted(root.rglob("*.framework"))


def create_xcframework(frameworks: list[pathlib.Path], output: pathlib.Path) -> pathlib.Path:
    xcodebuild = shutil.which("xcodebuild")
    if not xcodebuild:
        fail("no .xcframework found and xcodebuild is unavailable")
    if output.exists():
        shutil.rmtree(output)
    command = [xcodebuild, "-create-xcframework"]
    for framework in frameworks:
        command.extend(["-framework", str(framework)])
    command.extend(["-output", str(output)])
    subprocess.run(command, check=True)
    return output


def copy_xcframework(source: pathlib.Path, staging_dir: pathlib.Path, kit: str) -> pathlib.Path:
    if staging_dir.exists():
        shutil.rmtree(staging_dir)
    staging_dir.mkdir(parents=True)
    target = staging_dir / f"{kit}.xcframework"
    shutil.copytree(source, target, symlinks=True)
    return target


def zip_xcframework(staging_dir: pathlib.Path, xcframework: pathlib.Path, output: pathlib.Path) -> pathlib.Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        output.unlink()
    zip_tool = shutil.which("zip")
    if zip_tool:
        subprocess.run(
            [zip_tool, "-r", "-y", "-q", "-9", str(output.resolve()), xcframework.name],
            cwd=staging_dir,
            check=True,
        )
        return output
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for path in sorted(xcframework.rglob("*")):
            arcname = path.relative_to(staging_dir)
            if path.is_dir():
                continue
            zf.write(path, arcname.as_posix())
    return output


def compute_swiftpm_checksum(zip_path: pathlib.Path) -> str:
    swift = shutil.which("swift")
    if not swift:
        fail("swift is required to compute a SwiftPM binary target checksum")
    result = subprocess.run(
        [swift, "package", "compute-checksum", str(zip_path)],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return result.stdout.strip()


def release_asset_url(repo: str, tag: str, asset_name: str) -> str:
    return f"https://github.com/{repo}/releases/download/{tag}/{asset_name}"


def write_package(path: pathlib.Path, package_name: str, kit: str, url: str, checksum: str) -> None:
    path.write_text(
        f"""// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "{package_name}",
    platforms: [
        .iOS(.v12),
        .tvOS(.v12),
        .macOS(.v10_13)
    ],
    products: [
        .library(name: "{kit}", targets: ["{kit}"])
    ],
    targets: [
        .binaryTarget(
            name: "{kit}",
            url: "{url}",
            checksum: "{checksum}"
        )
    ]
)
""",
        encoding="utf-8",
    )


def write_github_output(values: dict[str, object]) -> None:
    output_path = os.environ.get("GITHUB_OUTPUT")
    if not output_path:
        return
    with open(output_path, "a", encoding="utf-8") as fh:
        for key, value in values.items():
            text = str(value).lower() if isinstance(value, bool) else str(value)
            fh.write(f"{key}={text}\n")


def command_check(args: argparse.Namespace) -> int:
    archive = select_archive(args.channel, args.kit, args.version)
    metadata_path = pathlib.Path(args.metadata_dir) / f"{args.channel}.json"
    metadata = load_metadata(metadata_path)
    changed = metadata.get("normalized_version") != archive.normalized_version
    payload = {
        "changed": changed,
        "kit": archive.kit,
        "channel": archive.channel,
        "upstream_version": archive.upstream_version,
        "normalized_version": archive.normalized_version,
        "tag": archive.tag,
        "source_url": archive.url,
        "upstream_filename": archive.filename,
        "asset_name": archive.asset_name,
        "prerelease": archive.prerelease,
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    write_github_output(payload)
    return 0


def build(args: argparse.Namespace) -> dict[str, object]:
    archive = select_archive(args.channel, args.kit, args.version)
    repo = args.repo or os.environ.get("GITHUB_REPOSITORY")
    if not repo:
        fail("--repo is required when GITHUB_REPOSITORY is not set")

    metadata_path = pathlib.Path(args.metadata_dir) / f"{args.channel}.json"
    metadata = load_metadata(metadata_path)
    changed = metadata.get("normalized_version") != archive.normalized_version
    if not changed and not args.force:
        payload = {
            "changed": False,
            "kit": archive.kit,
            "channel": archive.channel,
            "normalized_version": archive.normalized_version,
            "tag": archive.tag,
            "asset_name": archive.asset_name,
            "prerelease": archive.prerelease,
        }
        write_github_output(payload)
        print(json.dumps(payload, indent=2, sort_keys=True))
        return payload

    root = pathlib.Path.cwd()
    cache_dir = pathlib.Path(args.cache_dir)
    output_dir = pathlib.Path(args.output)
    work_dir = pathlib.Path(args.work_dir)
    source_archive = download_archive(archive, cache_dir)
    source_sha256 = sha256_file(source_archive)

    extract_dir = work_dir / "extract"
    extract_archive(source_archive, extract_dir)

    xcframework = find_xcframework(extract_dir, args.kit)
    if xcframework is None:
        frameworks = find_frameworks(extract_dir, args.kit)
        if not frameworks:
            fail(f"no .xcframework or .framework found in {source_archive}")
        xcframework = create_xcframework(frameworks, work_dir / f"{args.kit}.xcframework")

    staging_dir = work_dir / "staging"
    staged_xcframework = copy_xcframework(xcframework, staging_dir, args.kit)
    asset_path = zip_xcframework(staging_dir, staged_xcframework, output_dir / archive.asset_name)
    checksum = compute_swiftpm_checksum(asset_path)
    url = release_asset_url(repo, archive.tag, archive.asset_name)

    write_package(root / "Package.swift", args.package_name, args.kit, url, checksum)
    metadata_payload = {
        "kit": archive.kit,
        "channel": archive.channel,
        "upstream_version": archive.upstream_version,
        "normalized_version": archive.normalized_version,
        "tag": archive.tag,
        "source_url": archive.url,
        "upstream_filename": archive.filename,
        "asset_name": archive.asset_name,
        "asset_path": str(asset_path),
        "asset_url": url,
        "checksum": checksum,
        "source_sha256": source_sha256,
        "prerelease": archive.prerelease,
    }
    write_json(metadata_path, metadata_payload)

    release_notes = pathlib.Path(args.release_notes)
    release_notes.write_text(
        "\n".join(
            [
                f"{archive.kit} {archive.normalized_version}",
                "",
                f"- Channel: {archive.channel}",
                f"- Upstream version: {archive.upstream_version}",
                f"- Upstream archive: {archive.url}",
                f"- Source SHA256: {source_sha256}",
                f"- SwiftPM checksum: {checksum}",
                "",
            ]
        ),
        encoding="utf-8",
    )

    payload = {
        "changed": True,
        "kit": archive.kit,
        "channel": archive.channel,
        "upstream_version": archive.upstream_version,
        "normalized_version": archive.normalized_version,
        "tag": archive.tag,
        "asset_name": archive.asset_name,
        "asset_path": str(asset_path),
        "asset_url": url,
        "checksum": checksum,
        "source_url": archive.url,
        "source_sha256": source_sha256,
        "release_notes": str(release_notes),
        "prerelease": archive.prerelease,
    }
    write_github_output(payload)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return payload


def command_build(args: argparse.Namespace) -> int:
    build(args)
    return 0


def command_write_package(args: argparse.Namespace) -> int:
    write_package(pathlib.Path("Package.swift"), args.package_name, args.kit, args.url, args.checksum)
    return 0


def add_common_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--channel", choices=CHANNELS, default="prod")
    parser.add_argument("--kit", choices=SUPPORTED_KITS, default="VLCKit")
    parser.add_argument("--version", default="latest")
    parser.add_argument("--metadata-dir", default="metadata")


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Convert VideoLAN VLCKit archives to SwiftPM binary packages.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    check = subparsers.add_parser("check", help="Check the selected VideoLAN channel for a new version.")
    add_common_arguments(check)
    check.set_defaults(func=command_check)

    build_parser = subparsers.add_parser("build", help="Download, convert, package, and generate SwiftPM files.")
    add_common_arguments(build_parser)
    build_parser.add_argument("--repo")
    build_parser.add_argument("--package-name", default="VLCKit-SPM")
    build_parser.add_argument("--cache-dir", default=".cache")
    build_parser.add_argument("--work-dir", default="build")
    build_parser.add_argument("--output", default="dist")
    build_parser.add_argument("--release-notes", default="release-notes.md")
    build_parser.add_argument("--force", action="store_true")
    build_parser.set_defaults(func=command_build)

    write_package_parser = subparsers.add_parser("write-package", help="Write Package.swift for an existing asset.")
    write_package_parser.add_argument("--package-name", default="VLCKit-SPM")
    write_package_parser.add_argument("--kit", choices=SUPPORTED_KITS, default="VLCKit")
    write_package_parser.add_argument("--url", required=True)
    write_package_parser.add_argument("--checksum", required=True)
    write_package_parser.set_defaults(func=command_write_package)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = make_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
