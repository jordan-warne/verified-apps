#!/usr/bin/env python3
import json
import sys
from pathlib import Path

import grpc

sys.path.insert(0, str(Path(__file__).resolve().parent / "gen"))

from accrescent.appstore.v1 import (  # noqa: E402
    app_service_pb2_grpc,
    device_attributes_pb2,
    get_app_download_info_request_pb2,
)
from android.bundle import devices_pb2  # noqa: E402

_HOST = "appstore-api.accrescent.app"


def main() -> None:
    app_id = sys.argv[1]
    spec = devices_pb2.DeviceSpec(
        supported_abis=["arm64-v8a", "armeabi-v7a"],
        supported_locales=["en-US"],
        screen_density=480,
        sdk_version=34,
        codename="REL",
        build_brand="generic",
        build_device="generic",
    )
    spec.device_features.append("android.hardware.touchscreen")

    request = get_app_download_info_request_pb2.GetAppDownloadInfoRequest(
        app_id=app_id,
        device_attributes=device_attributes_pb2.DeviceAttributes(spec=spec),
    )

    channel = grpc.secure_channel(
        f"{_HOST}:443",
        grpc.ssl_channel_credentials(),
    )
    response = app_service_pb2_grpc.AppServiceStub(channel).GetAppDownloadInfo(
        request,
        timeout=30,
    )

    print(
        json.dumps(
            {
                "split_download_info": [
                    {"download_size": split.download_size, "url": split.url}
                    for split in response.app_download_info.split_download_info
                ]
            }
        )
    )


if __name__ == "__main__":
    main()
