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
                            "can_be_player": False,
                            "hidden": True,
                            "needs_full_player_state": True,
                        }
                    }
                },
            },
        ) as response:
            response.raise_for_status()

        event_loop = asyncio.get_event_loop()

        async for msg in ws:
            _ = event_loop.create_task(event_handler(msg.json()))
