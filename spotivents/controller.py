import logging
from binascii import hexlify, unhexlify

import aiohttp

from .auth import SpotifyAuthenticator
from .constants import SPOTIFY_HOSTNAME
from .utils import decode_basex_to_bytes, encode_bytes_to_basex


class SpotifyAPIControllerClient:

    logger = logging.getLogger("spotivents.controller")

    def __init__(self, session, auth: SpotifyAuthenticator):
        self.session = session
        self.auth = auth

    async def get_active_device_id(self):

        self.logger.debug("Getting active device ID.")

        async with self.session.get(
            f"https://api.{SPOTIFY_HOSTNAME}/v1/me/player/devices",
            headers={
                "Authorization": f"Bearer {(await self.auth.bearer_token())['accessToken']}"
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
        bearer_token = await self.auth.bearer_token()

        if include_from_to:
            active_device = to_device or await self.get_active_device_id()
            suffix = f"/from/{from_device or bearer_token['clientId']}/to/{active_device or bearer_token['clientId']}"
        else:
            suffix = ""

        async with self.session.request(
            method,
            f"https://gae-spclient.{SPOTIFY_HOSTNAME}/connect-state/v1" + url + suffix,
            headers={
                "Authorization": f"Bearer {bearer_token['accessToken']}",
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

    async def fetch_track_lyrics(self, track_id: str, album_art=None, *args, **kwargs):

        async with self.session.request(
            "GET",
            f"https://spclient.wg.{SPOTIFY_HOSTNAME}/color-lyrics/v2/track/{track_id}"
            + (f"/image/{album_art}" if album_art else ""),
            headers={
                "Authorization": f"Bearer {(await self.auth.bearer_token())['accessToken']}",
                "app-platform": "WebPlayer",
            },
            params={
                "format": "json",
                "vocalRemoval": "false",
            },
        ) as response:
            response.raise_for_status()
            return await response.json()

    async def add_track_to_queue(self, track_uri: str, *args, **kwargs):
        return await self.connect_call(
            "POST",
            f"/player/command",
            json={
                "command": {
                    "track": {
                        "uri": track_uri,
                    },
                    "endpoint": "add_to_queue",
                }
            },
            *args,
            **kwargs,
        )

    async def add_tracks_to_queue(self, track_uris: list, *args, **kwargs):

        return await self.connect_call(
            "POST",
            f"/player/command",
            json={
                "command": {
                    "next_tracks": [{"uri": track_uri} for track_uri in track_uris],
                    "endpoint": "set_queue",
                }
            },
            *args,
            **kwargs,
        )

    @staticmethod
    def convert_spotify_id_to_hex(spotify_id: str) -> str:
        return hexlify(decode_basex_to_bytes(spotify_id)).decode()

    @staticmethod
    def convert_hex_to_spotify_id(hex_id: str) -> str:
        return encode_bytes_to_basex(unhexlify(hex_id))

    async def query_entity_metadata(
        self, entity_id: str, entity_type: str, *args, **kwargs
    ):

        assert entity_type in (
            "track",
            "album",
            "artist",
            "playlist",
            "show",
            "episode",
        )

        hex_id = self.convert_spotify_id_to_hex(entity_id)

        async with self.session.get(
            f"https://gae-spclient.{SPOTIFY_HOSTNAME}/metadata/4/{entity_type}/{hex_id}",
            headers={
                "Authorization": f"Bearer {(await self.auth.bearer_token())['accessToken']}",
                "Accept": "application/json",
            },
            *args,
            **kwargs,
        ) as response:
            response.raise_for_status()
            return await response.json()
