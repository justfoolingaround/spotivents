from .constants import SPOTIFY_HOSTNAME


class SpotifyAPIControllerClient:
    def __init__(self, ws_client):
        self.session = ws_client.session
        self.ws_client = ws_client

    async def get_active_device_id(self):

        if self.ws_client.cluster is not None:
            return self.ws_client.cluster.active_device_id

        async with self.session.get(
            f"https://api.{SPOTIFY_HOSTNAME}/v1/me/player/devices",
            headers={
                "Authorization": f"Bearer {(await self.ws_client.bearer_token())['accessToken']}"
            },
        ) as response:
            response.raise_for_status()
            data = await response.json()

        for device in data["devices"]:
            if device["is_active"]:
                return device["id"]

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
            active_device = (
                await self.get_active_device_id() or bearer_token["clientId"]
            )
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

    async def seek(self, position: int, *args, **kwargs):
        return await self.set_seek(position, *args, **kwargs)

    async def play(
        self, entity_uri: str, skip_to_track_uri: str = None, *args, **kwargs
    ):
        # FOR LIKED SONGS, USE "spotify:user:...:collection"
        # FOR YOUR EPISODES, USE "spotify:user:...:collection:your-episodes"

        command = {
            "endpoint": "play",
            "context": {
                "uri": entity_uri,
                "url": f"context://{entity_uri}",
            },
        }

        if skip_to_track_uri is not None:
            command.update(
                {
                    "options": {
                        "skip_to": {
                            "track_uri": skip_to_track_uri,
                        }
                    }
                }
            )

        return await self.connect_call(
            "POST",
            f"/player/command",
            json={"command": command},
            *args,
            **kwargs,
        )

    async def transfer_across_device(
        self, to_device: str, restore_paused="restore", *args, **kwargs
    ):
        return await self.connect_call(
            "POST",
            f"/connect/transfer",
            json={
                "transfer_options": {"restore_paused": restore_paused},
            },
            to_device=to_device,
            *args,
            **kwargs,
        )

    async def fetch_track_lyrics(self, track_uri: str, album_art=None, *args, **kwargs):

        async with self.session.request(
            "GET",
            f"https://spclient.wg.{SPOTIFY_HOSTNAME}/color-lyrics/v2/track/{track_uri}"
            + f"/image/{album_art}"
            if album_art
            else "",
            headers={
                "Authorization": f"Bearer {(await self.ws_client.bearer_token())['accessToken']}",
                "app-platform": "WebPlayer",
            },
            params={
                "format": "json",
                "hasVocalRemoval": "false",
            },
        ) as response:
            response.raise_for_status()
            return await response.json()
