import asyncio
import threading

import aiohttp

from .constants import (
    DEVICE_PAYLOAD,
    EVENT_DEALER_WS,
    SPCLIENT_ENDPOINT,
    SPOTIVENTS_DEVICE_ID,
)
from .optopt import json

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


async def websocket_heartbeat(ws: aiohttp.ClientWebSocketResponse, interval=30):

    main_thread = threading.main_thread()

    while not ws.closed and main_thread.is_alive():
        await ws.send_json({"type": "ping"})
        await asyncio.sleep(interval)


async def ws_connect(
    session: aiohttp.ClientSession,
    auth,
    event_handler,
    invisible=True,
    cluster_future=None,
):

    access_token = (await auth.bearer_token())["accessToken"]

    async with session.ws_connect(
        EVENT_DEALER_WS, params={"access_token": access_token}
    ) as ws:

        connection_state = await ws.receive_json()
        connection_id = connection_state["headers"]["Spotify-Connection-Id"]

        if not invisible:

            async with session.post(
                SPCLIENT_ENDPOINT.with_path(f"/track-playback/v1/devices"),
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
                json={
                    "device": DEVICE_PAYLOAD,
                    "connection_id": connection_id,
                    "client_version": "harmony:4.27.1-af7f4f3",
                    "volume": (1 << 16) - 1,
                },
            ) as response:
                response.raise_for_status()

        async with session.put(
            SPCLIENT_ENDPOINT.with_path(
                f"/connect-state/v1/devices/hobs_{SPOTIVENTS_DEVICE_ID}"
            ),
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
        event_loop.create_task(websocket_heartbeat(ws, interval=15))

        async for msg in ws:
            _ = event_loop.create_task(event_handler(msg.json()))
