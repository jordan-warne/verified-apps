#!/usr/bin/env python3
"""Fetch Accrescent API protos and generate Python gRPC stubs into proto/ and gen/."""

from __future__ import annotations

import re
import sys
import urllib.request
from pathlib import Path

from grpc_tools import protoc
import grpc_tools

# android-bundle DeviceSpec (fetched on each cache miss).
ANDROID_BUNDLE_REF = "main"
ANDROID_BUNDLE_BASE = (
    f"https://raw.githubusercontent.com/accrescent/android-bundle/{ANDROID_BUNDLE_REF}/"
)

# Minimal appstore-api v1 messages for GetAppDownloadInfo (wire-compatible subset of
# https://github.com/accrescent/appstore-api at v1.0.3).
APPSTORE_PROTOS: dict[str, str] = {
    "accrescent/appstore/v1/get_app_download_info_request.proto": """\
syntax = "proto3";

package accrescent.appstore.v1;

import "accrescent/appstore/v1/device_attributes.proto";

option java_multiple_files = true;
option java_package = "app.accrescent.appstore.v1";

message GetAppDownloadInfoRequest {
  string app_id = 1;
  DeviceAttributes device_attributes = 2;
}
""",
    "accrescent/appstore/v1/get_app_download_info_response.proto": """\
syntax = "proto3";

package accrescent.appstore.v1;

import "accrescent/appstore/v1/app_download_info.proto";

option java_multiple_files = true;
option java_package = "app.accrescent.appstore.v1";

message GetAppDownloadInfoResponse {
  AppDownloadInfo app_download_info = 1;
}
""",
    "accrescent/appstore/v1/app_download_info.proto": """\
syntax = "proto3";

package accrescent.appstore.v1;

import "accrescent/appstore/v1/split_download_info.proto";

option java_multiple_files = true;
option java_package = "app.accrescent.appstore.v1";

message AppDownloadInfo {
  repeated SplitDownloadInfo split_download_info = 1;
}
""",
    "accrescent/appstore/v1/split_download_info.proto": """\
syntax = "proto3";

package accrescent.appstore.v1;

option java_multiple_files = true;
option java_package = "app.accrescent.appstore.v1";

message SplitDownloadInfo {
  uint32 download_size = 1;
  string url = 2;
}
""",
    "accrescent/appstore/v1/device_attributes.proto": """\
syntax = "proto3";

package accrescent.appstore.v1;

import "android/bundle/devices.proto";

option java_multiple_files = true;
option java_package = "app.accrescent.appstore.v1";

message DeviceAttributes {
  android.bundle.DeviceSpec spec = 1;
}
""",
    "accrescent/appstore/v1/app_service.proto": """\
syntax = "proto3";

package accrescent.appstore.v1;

import "accrescent/appstore/v1/get_app_download_info_request.proto";
import "accrescent/appstore/v1/get_app_download_info_response.proto";

option java_multiple_files = true;
option java_package = "app.accrescent.appstore.v1";

service AppService {
  rpc GetAppDownloadInfo(GetAppDownloadInfoRequest) returns (GetAppDownloadInfoResponse);
}
""",
}

STRIP_VALIDATE_IMPORT = re.compile(
    r'^\s*import "buf/validate/validate\.proto";\s*\n',
    re.MULTILINE,
)

def generated_stub(action_root: Path) -> Path:
    return action_root / "gen/accrescent/appstore/v1/app_service_pb2_grpc.py"


def strip_validate_options(text: str) -> str:
    text = re.sub(r"\[\(buf\.validate\.field\)[^\]]*\]", "", text)
    text = re.sub(
        r"\[\s*(?:\(buf\.validate\.field\)[^\]]*)+\s*\]",
        "",
        text,
        flags=re.DOTALL,
    )
    return text


def sanitize_proto(text: str) -> str:
    text = STRIP_VALIDATE_IMPORT.sub("", text)
    return strip_validate_options(text)


def fetch(url: str) -> str:
    with urllib.request.urlopen(url, timeout=60) as response:
        return response.read().decode("utf-8")


def write_protos(proto_root: Path) -> None:
    for rel, content in APPSTORE_PROTOS.items():
        dest = proto_root / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content, encoding="utf-8")

    devices = proto_root / "android/bundle/devices.proto"
    devices.parent.mkdir(parents=True, exist_ok=True)
    devices.write_text(
        sanitize_proto(
            fetch(ANDROID_BUNDLE_BASE + "android/bundle/devices.proto"),
        ),
        encoding="utf-8",
    )


def run_protoc(proto_root: Path, gen_root: Path) -> None:
    well_known = Path(grpc_tools.__file__).resolve().parent / "_proto"
    proto_files = sorted(proto_root.rglob("*.proto"))

    args = [
        "grpc_tools.protoc",
        f"--proto_path={well_known}",
        f"--proto_path={proto_root}",
        f"--python_out={gen_root}",
        f"--grpc_python_out={gen_root}",
    ] + [str(path.relative_to(proto_root)) for path in proto_files]

    if protoc.main(args) != 0:
        raise SystemExit("protoc failed")


def main() -> int:
    action_root = Path(__file__).resolve().parent
    proto_root = action_root / "proto"
    gen_root = action_root / "gen"

    proto_root.mkdir(parents=True, exist_ok=True)
    gen_root.mkdir(parents=True, exist_ok=True)

    write_protos(proto_root)
    run_protoc(proto_root, gen_root)

    stub = generated_stub(action_root)
    if not stub.exists():
        print(
            f"protoc did not produce expected stubs at {stub}",
            file=sys.stderr,
        )
        return 1

    print(f"Wrote protos under {proto_root} and stubs under {gen_root}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
