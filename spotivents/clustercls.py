import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class SpotifyTrackMetadata:

    actions: Dict[str, Optional[str]]
    autoplay: Dict[str, Optional[str]]
    shuffle: Dict[str, Optional[str]]
    collection: Dict[str, Optional[str]]
    media: Dict[str, Optional[str]]

    context_uri: Optional[str] = None
    entity_uri: Optional[str] = None
    page_instance_id: Optional[str] = None
    track_player: Optional[str] = None
    hidden: Optional[str] = None
    iteration: Optional[str] = None

    title: Optional[str] = None

    artist_uri: Optional[str] = None
    artist_name: Optional[str] = None
    artists: List[Dict[str, str]] = field(default_factory=list)

    image_url: Optional[str] = None
    image_xlarge_url: Optional[str] = None
    image_large_url: Optional[str] = None
    image_small_url: Optional[str] = None
    album_title: Optional[str] = None
    album_uri: Optional[str] = None
    provider: Optional[str] = None

    decision_id: Optional[str] = None
    interaction_id: Optional[str] = None
    added_by_user: Optional[str] = None
    added_by_username: Optional[str] = None

    is_advertisement: Optional[str] = None
    is_explicit: Optional[str] = None
    is_promotional: Optional[str] = None

    is_queued: Optional[str] = None
    queued_by: Optional[str] = None

    keep_skip_direction: Optional[str] = None
    added_at: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Optional[Dict]):

        if not data:
            return None

        actions: Dict[str, Optional[str]] = {
            "advancing_past_track": data.pop("actions.advancing_past_track", None),
            "skipping_next_past_track": data.pop(
                "actions.skipping_next_past_track", None
            ),
            "skipping_prev_past_track": data.pop(
                "actions.skipping_prev_past_track", None
            ),
        }

        autoplay: Dict[str, Optional[str]] = {
            "is_autoplay": data.pop("autoplay.is_autoplay", None),
        }

        media: Dict[str, Optional[str]] = {
            "media_type": data.pop("media.media_type", None),
            "media_start_position": data.pop("media.start_position", None),
        }

        collection = {
            "artist": {
                "is_banned": data.pop("collection.artist.is_banned", None),
            },
            "is_banned": data.pop("collection.is_banned", None),
        }

        shuffle: Dict[str, Optional[str]] = {
            "distribution": data.pop("shuffle.distribution", None),
        }

        for key, value in tuple(data.items()):
            match = re.match(r"artist_name:(\d+)", key)

            if match is not None:

                data.setdefault("artists", []).append(
                    {
                        "name": value,
                        "index": match.group(1),
                        "uri": data.pop(f"artist_uri:{match.group(1)}", None),
                    },
                )
            data.pop(key, None)

        return cls(
            actions=actions,
            autoplay=autoplay,
            media=media,
            collection=collection,
            shuffle=shuffle,
            **data,
        )


@dataclass
class SpotifyTrack:

    uri: str
    metadata: Optional[SpotifyTrackMetadata]
    provider: str

    uid: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Optional[Dict]):
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
    def from_dict(cls, data: Optional[Dict]):
        if not data:
            return None

        return cls(**data)


@dataclass
class SpotifyPlayerStatePartialTrack:

    uri: str
    metadata: Optional[SpotifyTrackMetadata]
    provider: str
    removed: Optional[List[str]] = None
    blocked: Optional[str] = None
    uid: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Optional[Dict]):
        if not data:
            return None

        return cls(
            metadata=SpotifyTrackMetadata.from_dict(data.pop("metadata", None)),
            **data,
        )


@dataclass
class SpotifyPlaybackQuality:

    bitrate_level: str
    strategy: str
    target_bitrate_level: str
    target_bitrate_available: bool = False

    @classmethod
    def from_dict(cls, data: Optional[Dict]):
        if not data:
            return None

        return cls(**data)


@dataclass
class SpotifyPlayerState:

    context_url: str
    track: Optional[SpotifyTrack]
    playback_speed: float
    position_as_of_timestamp: str
    is_playing: bool
    is_paused: bool
    is_system_initiated: bool
    options: Optional[SpotifyPlayerStateOptions]
    page_metadata: Dict
    playback_quality: Optional[SpotifyPlaybackQuality]
    next_tracks: List[Optional[SpotifyPlayerStatePartialTrack]]
    prev_tracks: List[Optional[SpotifyPlayerStatePartialTrack]]

    context_restrictions: Optional[dict] = None
    play_origin: Optional[dict] = None
    restrictions: Optional[dict] = None
    suppressions: Optional[dict] = None
    queue_revision: Optional[str] = None

    index: Optional[dict] = None
    session_id: Optional[str] = None

    is_buffering: Optional[bool] = False
    timestamp: Optional[str] = None
    audio_stream: Optional[str] = None
    playback_id: Optional[str] = None
    duration: Optional[str] = None
    context_uri: Optional[str] = None
    context_metadata: Optional[Dict] = None

    @classmethod
    def from_dict(cls, data: Optional[Dict]):
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
                if track is not None
            ],
            prev_tracks=[
                SpotifyPlayerStatePartialTrack.from_dict(track)
                for track in data.pop("prev_tracks", [])
                if track is not None
            ],
            **data,
        )


@dataclass
class SpotifyConnectDevice:

    capabilities: Dict
    device_type: str
    device_id: str
    can_play: bool = False

    name: Optional[str] = None
    device_software_version: Optional[str] = None
    client_id: Optional[str] = None
    brand: Optional[str] = None
    model: Optional[str] = None
    license: Optional[str] = None

    volume: int = 0
    spirc_version: Optional[str] = None
    metadata_map: Optional[dict] = None
    deduplication_id: Optional[str] = None
    is_private_session: bool = False
    public_ip: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Optional[Dict]):
        if not data:
            return None

        return cls(**data)


@dataclass
class SpotifyDeviceStateChangeCluster:

    type: str

    timestamp: str
    player_state: Optional[SpotifyPlayerState]
    devices: Dict[str, Optional[SpotifyConnectDevice]]
    need_full_player_state: bool
    server_timestamp_ms: str

    not_playing_since_timestamp: Optional[str] = None
    transfer_data_timestamp: Optional[str] = None
    active_device_id: Optional[str] = None

    @classmethod
    def from_dict(cls, type: str, data: Optional[Dict]):
        if not data:
            return None

        devices = {
            device_id: SpotifyConnectDevice.from_dict(device)
            for device_id, device in data.pop("devices", {}).items()
        }

        return cls(
            type=type,
            player_state=SpotifyPlayerState.from_dict(data.pop("player_state", None)),
            devices=devices,
            **data,
        )


def iter_handled_payloads(
    payloads: List[Dict],
):
    for payload in payloads:

        if not isinstance(payload, dict):
            continue

        shallow_payload = payload.copy()
        update_reason: Optional[str] = shallow_payload.get("update_reason", None)

        if update_reason is not None and update_reason in (
            "DEVICE_STATE_CHANGED",
            "DEVICE_VOLUME_CHANGED",
            "DEVICES_DISAPPEARED",
            "DEVICE_NEW_CONNECTION",
        ):
            cluster = shallow_payload.pop("cluster", None)
            yield {
                "cluster": SpotifyDeviceStateChangeCluster.from_dict(
                    update_reason, cluster
                ),
                **shallow_payload,
            }
        else:
            if shallow_payload.get("type") == "replace_state":
                yield shallow_payload
