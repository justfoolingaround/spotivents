from .client import SpotifyClient
from .constants import SPOTIFY_HOSTNAME


class SpotifyAPIControllerClient:
    def __init__(self, ws_client: SpotifyClient):
        self.session = ws_client.session

        self.ws_client = ws_client

    async def connect_call(
        self,
        method,
        url,
        from_device: str = None,
        to_device: str = None,
        include_from_to: bool = True,
        *args,
        **kwargs,
    ):
        bearer_token = await self.ws_client.bearer_token()

        if include_from_to:
            active_device = self.ws_client.cluster.active_device_id
            suffix = (
                f"/from/{from_device or active_device}/to/{to_device or active_device}"
            )
        else:
            suffix = ""

        async with self.session.request(
            method,
            f"https://gae-spclient.{SPOTIFY_HOSTNAME}/connect-state/v1" + url + suffix,
            headers={
                "Authorization": f"Bearer {bearer_token['accessToken']}",
                "client-token": (await self.ws_client.client_token())["granted_token"][
                    "token"
                ],
            },
            *args,
            **kwargs,
        ) as response:
            response.raise_for_status()
            return await response.text()

    async def change_connect_state(self, name, state, *args, **kwargs):

        return await self.connect_call(
            "PUT",
            f"/connect/{name}",
            json={name: state},
            *args,
            **kwargs,
        )

    async def set_volume(self, volume: int, percent: bool = True, *args, **kwargs):
        if percent:
            volume = int(volume * 65535)

        return await self.change_connect_state("volume", volume, *args, **kwargs)

    async def set_shuffle(self, shuffle: bool, *args, **kwargs):
        return await self.change_connect_state("shuffle", shuffle, *args, **kwargs)

    async def set_repeat(self, repeat: str, *args, **kwargs):
        return await self.change_connect_state("repeat", repeat, *args, **kwargs)

    async def set_playback(self, playback: str, *args, **kwargs):

        assert playback in (
            "resume",
            "pause",
            "skip_next",
            "skip_prev",
        )

        return await self.connect_call(
            "POST",
            f"/player/command",
            json={"command": {"endpoint": playback}},
            *args,
            **kwargs,
        )

    async def set_seek(self, position: int, *args, **kwargs):
        return await self.connect_call(
            "POST",
            f"/player/command",
            json={
                "command": {
                    "endpoint": "seek_to",
                    "value": position,
                }
            },
            *args,
            **kwargs,
        )

    async def set_repeat(
        self,
        track: bool = False,
        context: bool = False,
        *args,
        **kwargs,
    ):

        return await self.connect_call(
            "POST",
            f"/player/command",
            json={
                "command": {
                    "endpoint": "set_options",
                    "repeating_context": context,
                    "repeating_track": track,
                }
            },
            *args,
            **kwargs,
        )

    async def set_shuffle(self, shuffle: bool, *args, **kwargs):

        return await self.connect_call(
            "POST",
            f"/player/command",
            json={
                "command": {
                    "endpoint": "set_options",
                    "shuffling_context": shuffle,
                }
            },
            *args,
            **kwargs,
        )

    async def next_track(self, *args, **kwargs):
        return await self.set_playback("skip_next", *args, **kwargs)

    async def previous_track(self, *args, **kwargs):
        return await self.set_playback("skip_prev", *args, **kwargs)

    async def pause(self, *args, **kwargs):
        return await self.set_playback("pause", *args, **kwargs)

    async def resume(self, *args, **kwargs):
        return await self.set_playback("resume", *args, **kwargs)

    play = resume

    async def seek(self, position: int, *args, **kwargs):
        return await self.set_seek(position, *args, **kwargs)
