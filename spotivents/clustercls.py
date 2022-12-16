from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class SpotifyTrackMetadata:

    track_player: str
    image_xlarge_url: str
    page_instance_id: str
    image_large_url: str
    album_title: str
    interaction_id: str
    artist_uri: str
    image_small_url: str
    context_uri: str
    album_uri: str
    entity_uri: str
    image_url: str
    iteration: str
    actions: Dict[str, str]
    autoplay: Dict[str, str]
    media: Dict[str, str]
    decision_id: Optional[str] = None

    @classmethod
    def from_dict(cls, data):

        if not data:
            return None

        actions = {
            "advancing_past_track": data.pop("actions.advancing_past_track", None),
            "skipping_next_past_track": data.pop(
                "actions.skipping_next_past_track", None
            ),
            "skipping_prev_past_track": data.pop(
                "actions.skipping_prev_past_track", None
            ),
        }

        autoplay = {
            "is_autoplay": data.pop("autoplay.is_autoplay", None),
        }

        media = {
            "media_type": data.pop("media.media_type", None),
            "media_start_position": data.pop("media.start_position", None),
        }

        return cls(
            actions=actions,
            autoplay=autoplay,
            media=media,
            **data,
        )


@dataclass
class SpotifyTrack:

    uri: str
    uid: str
    metadata: SpotifyTrackMetadata
    provider: str

    @classmethod
    def from_dict(cls, data):
        if not data:
            return None

        return cls(
            metadata=SpotifyTrackMetadata.from_dict(data.pop("metadata", None)),
            **data,
        )


@dataclass
class SpotifyPlayerStateOptions:

    shuffling_context: bool
    repeating_context: bool
    repeating_track: bool

    @classmethod
    def from_dict(cls, data):
        if not data:
            return None

        return cls(**data)


@dataclass
class SpotifyPlayerStatePartialTrackMetadata:

    page_instance_id: str
    actions: Dict[str, str]
    interaction_id: str
    autoplay: Dict[str, str]

    context_uri: Optional[str] = None
    entity_uri: Optional[str] = None
    track_player: Optional[str] = None
    hidden: Optional[str] = None
    iteration: Optional[str] = None
    artist_uri: Optional[str] = None
    image_url: Optional[str] = None
    image_xlarge_url: Optional[str] = None
    image_large_url: Optional[str] = None
    image_small_url: Optional[str] = None
    album_title: Optional[str] = None
    album_uri: Optional[str] = None

    media: Dict[str, str] = None
    decision_id: Optional[str] = None

    @classmethod
    def from_dict(cls, data):

        if not data:
            return None

        actions = {
            "advancing_past_track": data.pop("actions.advancing_past_track", None),
            "skipping_next_past_track": data.pop(
                "actions.skipping_next_past_track", None
            ),
            "skipping_prev_past_track": data.pop(
                "actions.skipping_prev_past_track", None
            ),
        }

        autoplay = {
            "is_autoplay": data.pop("autoplay.is_autoplay", None),
        }

        media = {
            "media_type": data.pop("media.media_type", None),
            "media_start_position": data.pop("media.start_position", None),
        }

        return cls(
            actions=actions,
            autoplay=autoplay,
            media=media,
            **data,
        )


@dataclass
class SpotifyPlayerStatePartialTrack:

    uri: str
    uid: str
    metadata: SpotifyPlayerStatePartialTrackMetadata
    provider: str
    removed: Optional[List[str]] = None
    blocked: Optional[str] = None

    @classmethod
    def from_dict(cls, data):
        if not data:
            return None

        return cls(
            metadata=SpotifyPlayerStatePartialTrackMetadata.from_dict(
                data.pop("metadata", None)
            ),
            **data,
        )


@dataclass
class SpotifyPlaybackQuality:

    bitrate_level: str
    strategy: str
    target_bitrate_level: str
    target_bitrate_available: bool

    @classmethod
    def from_dict(cls, data):
        if not data:
            return None

        return cls(**data)


@dataclass
class SpotifyPlayerState:

    timestamp: str
    context_uri: str
    context_url: str
    context_restrictions: Dict
    play_origin: Dict
    track: Optional[SpotifyTrack]
    playback_id: str
    playback_speed: float
    position_as_of_timestamp: str
    duration: str
    is_playing: bool
    is_paused: bool
    is_system_initiated: bool
    options: Optional[SpotifyPlayerStateOptions]
    restrictions: Dict
    suppressions: Dict
    context_metadata: Dict
    page_metadata: Dict
    session_id: str
    queue_revision: str
    playback_quality: Optional[SpotifyPlaybackQuality]

    index: Optional[dict] = None
    next_tracks: Optional[List[SpotifyPlayerStatePartialTrack]] = None
    prev_tracks: Optional[List[SpotifyPlayerStatePartialTrack]] = None
    is_buffering: Optional[bool] = False

    @classmethod
    def from_dict(cls, data):
        if not data:
            return None

        return cls(
            track=SpotifyTrack.from_dict(data.pop("track", None)),
            options=SpotifyPlayerStateOptions.from_dict(data.pop("options", None)),
            playback_quality=SpotifyPlaybackQuality.from_dict(
                data.pop("playback_quality", None)
            ),
            next_tracks=[
                SpotifyPlayerStatePartialTrack.from_dict(track)
                for track in data.pop("next_tracks", [])
            ],
            prev_tracks=[
                SpotifyPlayerStatePartialTrack.from_dict(track)
                for track in data.pop("prev_tracks", [])
            ],
            **data,
        )


@dataclass
class SpotifyConnectDevice:

    can_play: bool
    volume: int
    name: str
    capabilities: Dict
    device_software_version: str
    device_type: str
    device_id: str
    client_id: str
    brand: str
    model: str
    public_ip: str
    license: str

    spirc_version: Optional[str] = None
    metadata_map: Optional[dict] = None
    deduplication_id: Optional[str] = None

    @classmethod
    def from_dict(cls, data):
        if not data:
            return None

        return cls(**data)


@dataclass
class SpotifyDeviceStateChangeCluster:

    timestamp: str
    player_state: SpotifyPlayerState
    devices: Dict[str, SpotifyConnectDevice]
    active_device_id: str
    transfer_data_timestamp: str
    need_full_player_state: bool
    server_timestamp_ms: str
    not_playing_since_timestamp: Optional[str] = None

    @classmethod
    def from_dict(cls, data):
        if not data:
            return None

        devices = {
            device_id: SpotifyConnectDevice.from_dict(device)
            for device_id, device in data.pop("devices", {}).items()
        }
        devices.update(active=devices[data["active_device_id"]])

        return cls(
            player_state=SpotifyPlayerState.from_dict(data.pop("player_state", None)),
            devices=devices,
            **data,
        )


def iter_handled_payloads(
    payloads: List[Dict],
):
    for payload in payloads:
        shallow_payload = payload.copy()

        if shallow_payload.get("update_reason") == "DEVICE_STATE_CHANGED":
            cluster = shallow_payload.pop("cluster", None)
            yield {
                "cluster": SpotifyDeviceStateChangeCluster.from_dict(cluster),
                **shallow_payload,
            }
