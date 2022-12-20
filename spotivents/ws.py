import asyncio

try:
    import orjson as json
except ImportError:
    import json

import aiohttp

from .constants import EVENT_DEALER_WS, SPCLIENT_ENDPOINT

WS_CONNECT_STATE_PAYLOAD = {
    "member_type": "CONNECT_STATE",
    "device": {
        "device_info": {
            "capabilities": {
                "can_be_player": True,
                "gaia_eq_connect_id": True,
                "supports_logout": True,
                "is_observable": True,
                "supported_types": [
                    "audio/track",
                    "audio/episode",
                    "video/episode",
                    "mixed/episode",
                ],
                "command_acks": True,
                "is_controllable": True,
                "supports_external_episodes": True,
                "supports_command_request": True,
                "supports_set_options_command": True,
                "supports_hifi": {
                    "device_supported": True,
                },
                "needs_full_player_state": True,
                "hidden": True,
            }
        },
    },
}

DEVICE_CONNECT_PAYLOAD = {
    "device": {
        "brand": "spotify",
        "capabilities": {
            "change_volume": True,
            "enable_play_token": True,
            "supports_file_media_type": True,
            "play_token_lost_behavior": "pause",
            "disable_connect": False,
            "audio_podcasts": True,
            "video_playback": True,
            "manifest_formats": [
                "file_ids_mp3",
                "file_urls_mp3",
                "manifest_ids_video",
                "file_urls_external",
                "file_ids_mp4",
                "file_ids_mp4_dual",
            ],
        },
        "device_type": "computer",
        "metadata": {},
        "model": "web_player",
        "name": "Spotivents",
        "platform_identifier": "web_player windows 10;chrome 108.0.0.0;desktop",
        "is_group": False,
    },
    "client_version": "harmony:4.27.1-af7f4f3",
    "volume": 65535,
}


async def ws_connect(
    session: aiohttp.ClientSession,
    access_token: str,
    device_id: str,
    event_handler,
    invisible=True,
    cluster_future=None,
):

    async with session.ws_connect(
        EVENT_DEALER_WS, params={"access_token": access_token}, heartbeat=30
    ) as ws:

        connection_state = await ws.receive_json()
        connection_id = connection_state["headers"]["Spotify-Connection-Id"]

        if not invisible:

            payload = DEVICE_CONNECT_PAYLOAD.copy()
            device = DEVICE_CONNECT_PAYLOAD["device"].copy()

            device["device_id"] = device_id
            payload["device"] = device
            payload["connection_id"] = connection_id

            async with session.post(
                SPCLIENT_ENDPOINT.with_path(f"/track-playback/v1/devices"),
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
                json=payload,
            ) as response:
                response.raise_for_status()

        async with session.put(
            SPCLIENT_ENDPOINT.with_path(f"/connect-state/v1/devices/hobs_{device_id}"),
            headers={
                "Authorization": f"Bearer {access_token}",
                "x-spotify-connection-id": connection_id,
            },
            json=WS_CONNECT_STATE_PAYLOAD,
        ) as response:
            response.raise_for_status()
            if cluster_future:
                cluster_future.set_result(json.loads(await response.text()))

        event_loop = asyncio.get_event_loop()

        async for msg in ws:
            _ = event_loop.create_task(event_handler(msg.json()))
