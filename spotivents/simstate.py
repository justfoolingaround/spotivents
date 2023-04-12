"""
Spotivents' state simulation module.
"""

import enum
import time
import typing as t

from .constants import SPCLIENT_ENDPOINT, SPOTIVENTS_DEVICE_ID

if t.TYPE_CHECKING:
    from .client import SpotifyClient

# This file is sampled from Spotify's audio manifests.
# This is kept as a constant for future-proofing.

DEFAULT_FILE = {
    "audio_quality": "VERY_HIGH",
    "bitrate": 320000,
    "format": 11,
    "track_type": "AUDIO",
}


class DebugSource(enum.Enum):
    """
    The playback state of a device.
    """

    TRACK_DATA_FINALIZED = "track_data_finalized"

    BEFORE_TRACK_LOAD = "before_track_load"
    POSITION_CHANGED = "position_changed"
    STARTED_PLAYING = "started_playing"

    RESUME = "resume"
    PAUSE = "pause"

    PLAYER_THRESHOLD_REACHED = "player_threshold_reached"
    STATE_CLEAR = "state_clear"

    MODIFY_CURRENT_STATE = "modify_current_state"


class SpotiyState:
    def __init__(
        self,
        client: "SpotifyClient",
        state_id: str,
        state_machine_id: str,
        initial_replace_state: t.Dict,
    ) -> None:
        self.client = client

        self.state_id = state_id
        self.state_machine_id = state_machine_id

        self.replace_state = initial_replace_state

    async def send(
        self,
        debug_source: DebugSource,
        data: "t.Dict | None" = None,
        *,
        is_paused: bool = True,
        position: int | None = None,
    ):

        if self.client.cluster is None:
            raise ValueError(
                "No cluster has been loaded yet, make sure SpotifyClient is up and running."
            )

        if self.client.cluster.player_state is None:
            raise ValueError(
                "No player state has been loaded yet, make sure Spotify is actually playing something."
            )

        seq_num = int(time.time() * 1000)

        if debug_source != DebugSource.STATE_CLEAR:
            state_ref = {
                "paused": is_paused,
                "state_id": self.state_id,
                "state_machine_id": self.state_machine_id,
            }
        else:
            state_ref = None

        pos = int(self.client.cluster.player_state.position_as_of_timestamp.value())

        sub_state = {
            "audio_quality": DEFAULT_FILE["audio_quality"],
            "bitrate": DEFAULT_FILE["bitrate"],
            "duration": int(self.client.cluster.player_state.duration),
            "format": DEFAULT_FILE["format"],
            "media_type": DEFAULT_FILE["track_type"],
            "playback_speed": int(self.client.cluster.player_state.playback_speed or 1),
            "position": position or pos,
        }

        json = {
            "debug_source": debug_source.value,
            "seq_num": seq_num,
            "state_ref": state_ref,
            "sub_state": sub_state,
            "previous_position": pos,
        }

        if data is not None:
            json.update(data)

        async with self.client.session.put(
            f"{SPCLIENT_ENDPOINT}track-playback/v1/devices/{SPOTIVENTS_DEVICE_ID}/state",
            json=json,
            headers={
                "Authorization": f"Bearer {(await self.client.auth.bearer_token())['accessToken']}"
            },
        ) as response:
            return await response.json(content_type=None)

    async def trigger_before_track_load(self):
        return await self.send(DebugSource.BEFORE_TRACK_LOAD)

    async def trigger_position_changed(self, position: "int | None" = None):
        return await self.send(
            DebugSource.POSITION_CHANGED,
            position=position,
        )

    async def trigger_started_playing(self):
        return await self.send(DebugSource.STARTED_PLAYING, is_paused=False)

    async def trigger_resume(self):
        return await self.send(DebugSource.RESUME, is_paused=False)

    async def trigger_pause(self):
        return await self.send(DebugSource.PAUSE)

    async def trigger_player_threshold_reached(self):
        # NOTE: Only call after a 30 second interval of "started_playing"
        #       has passed. This is potentially bannable as this **will**
        #       report a "stream" for the song to Spotify's servers.
        return await self.send(DebugSource.PLAYER_THRESHOLD_REACHED)

    async def trigger_state_clear(self):
        return await self.send(DebugSource.STATE_CLEAR)

    async def trigger_modify_current_state(self, data: t.Dict):
        return await self.send(DebugSource.MODIFY_CURRENT_STATE, data=data)

    async def trigger_track_data_finalized(self):
        # Usually, this is used to play "next" tracks.
        raise NotImplementedError(
            "Track data requires additional information not implemented yet."
        )

    async def replace(self, data: t.Dict):

        new_pause = data.get("state_ref", {}).get("paused", True)

        if new_pause:
            await self.trigger_pause()
        else:
            await self.trigger_resume()

        if data.get("seek_to", None) is not None:
            await self.trigger_position_changed(data["seek_to"])

        self.replace_state.clear()
        self.replace_state.update(data)

    async def accept(self):
        await self.trigger_before_track_load()
        await self.trigger_resume()
        await self.trigger_started_playing()
