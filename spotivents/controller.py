import logging
from binascii import hexlify, unhexlify

from .auth import SpotifyAuthenticator
from .constants import SPOTIFY_HOSTNAME
from .optopt import json
from .utils import decode_basex_to_bytes, encode_bytes_to_basex


class SpotifyAPIControllerClient:

    logger = logging.getLogger("spotivents.controller")
    entity_types = (
        "track",
        "album",
        "artist",
        "playlist",
        "show",
        "episode",
    )

    def __init__(self, session, auth: SpotifyAuthenticator):
        self.session = session
        self.auth = auth

    async def get_headers(self, json=False, platform=None):

        headers = {
            "Authorization": f"Bearer {(await self.auth.bearer_token())['accessToken']}"
        }
        if json:
            headers["Accept"] = "application/json"

        if platform is not None:
            headers["app-platform"] = platform

        return headers

    async def get_active_device_id(self):

        self.logger.debug("Getting active device ID.")

        async with self.session.get(
            f"https://api.{SPOTIFY_HOSTNAME}/v1/me/player",
            headers=await self.get_headers(),
        ) as response:
            response.raise_for_status()
            data = await response.json()

        return data.get("device", {}).get("id")

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
            headers=await self.get_headers(platform="WebPlayer"),
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
        next_tracks = [{"uri": track_uri} for track_uri in track_uris]
        return await self.connect_call(
            "POST",
            f"/player/command",
            json={
                "command": {
                    "next_tracks": next_tracks,
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

        assert entity_type in self.entity_types

        hex_id = self.convert_spotify_id_to_hex(entity_id)

        async with self.session.get(
            f"https://gae-spclient.{SPOTIFY_HOSTNAME}/metadata/4/{entity_type}/{hex_id}",
            headers=await self.get_headers(json=True),
            *args,
            **kwargs,
        ) as response:
            response.raise_for_status()
            return await response.json()

    async def determine_entity_type(self, id: str) -> str:

        for entity_type in self.entity_types:
            async with self.session.head(
                f"https://open.spotify.com/embed/{entity_type}/{id}",
            ) as response:
                if response.status == 200:
                    return entity_type

        raise ValueError(f"Invalid entity id: {id}")

    async def presence_view_call(
        self,
        method: str,
        endpoint: str,
        *args,
        **kwargs,
    ):
        async with self.session.request(
            method,
            f"https://spclient.wg.{SPOTIFY_HOSTNAME}/presence-view/v1{endpoint}",
            headers=await self.get_headers(),
            *args,
            **kwargs,
        ) as response:
            response.raise_for_status()
            return await response.json()

    async def get_buddies(self, *args, **kwargs):
        return await self.presence_view_call("GET", "/buddylist", *args, **kwargs)

    async def get_buddy_presence(self, user_id: str, *args, **kwargs):
        return await self.presence_view_call("GET", f"/user/{user_id}", *args, **kwargs)

    async def fetch_playlist_extension(
        self,
        playlist_id: str,
        track_ids: list = None,
        artist_ids: list = None,
        track_skip_ids: list = None,
        playlist_skip_ids: list = None,
        artist_skip_ids: list = None,
        num_results: int = 50,
        condensed: bool = False,
        decoration: bool = False,
        family: str = "all",
        family_list: list = ["all"],
        *args,
        **kwargs,
    ):

        async with self.session.post(
            f"https://spclient.wg.{SPOTIFY_HOSTNAME}/playlistextender/extendp/",
            headers=await self.get_headers(),
            json={
                "playlistURI": f"spotify:playlist:{playlist_id}",
                "trackIDs": track_ids,
                "artistIDs": artist_ids,
                "trackSkipIDs": track_skip_ids,
                "playlistSkipIDs": playlist_skip_ids,
                "artistSkipIDs": artist_skip_ids,
                "numResults": num_results,
                "condensed": condensed,
                "decoration": decoration,
                "family": family,
                "familyList": family_list,
            },
            *args,
            **kwargs,
        ) as response:
            response.raise_for_status()
            return json.loads(await response.text())

    async def fetch_user(
        self,
        user_id: str,
        playlist_limit: int = 10,
        artist_limit: int = 10,
        episode_limit: int = 10,
        market: str = "from_token",
        *args,
        **kwargs,
    ):
        async with self.session.get(
            f"https://spclient.wg.{SPOTIFY_HOSTNAME}/user-profile-view/v3/profile/{user_id}",
            headers=await self.get_headers(),
            params={
                "playlist_limit": playlist_limit,
                "artist_limit": artist_limit,
                "episode_limit": episode_limit,
                "market": market,
            },
            *args,
            **kwargs,
        ) as response:
            response.raise_for_status()
            return await response.json()

    async def fetch_user_follow(
        self,
        user_id: str,
        follow_type: str = "following",
        *args,
        **kwargs,
    ):
        assert follow_type in ["following", "followers"]

        async with self.session.get(
            f"https://spclient.wg.{SPOTIFY_HOSTNAME}/user-profile-view/v3/profile/{user_id}/{follow_type}",
            headers=await self.get_headers(),
            *args,
            **kwargs,
        ) as response:
            response.raise_for_status()
            return await response.json()

    async def skip_advertisement(self):
        current_device = await self.get_active_device_id()

        await self.transfer_across_device((await self.auth.bearer_token())["clientId"])
        await self.transfer_across_device(current_device)

        return await self.resume()
