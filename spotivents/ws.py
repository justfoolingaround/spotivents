import asyncio

import aiohttp

from .constants import EVENT_DEALER_WS, SPCLIENT_ENDPOINT


async def ws_connect(
    session: aiohttp.ClientSession, access_token: str, device_id: str, event_handler
):

    async with session.ws_connect(
        EVENT_DEALER_WS, params={"access_token": access_token}, heartbeat=30
    ) as ws:

        connection_state = await ws.receive_json()
        connection_id = connection_state["headers"]["Spotify-Connection-Id"]

        async with session.put(
            SPCLIENT_ENDPOINT.with_path(f"/connect-state/v1/devices/hobs_{device_id}"),
            headers={
                "Authorization": f"Bearer {access_token}",
                "x-spotify-connection-id": connection_id,
            },
            json={
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
            },
        ) as response:
            response.raise_for_status()

        event_loop = asyncio.get_event_loop()

        async for msg in ws:
            _ = event_loop.create_task(event_handler(msg.json()))
