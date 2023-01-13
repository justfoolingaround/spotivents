import random

import yarl

SPOTIVENTS_DEVICE_ID = "spotivents_" + "".join(random.choices("abcdef1234567890", k=4))

SPOTIFY_HOSTNAME = "spotify.com"

EVENT_DEALER_WS = yarl.URL(f"wss://dealer.{SPOTIFY_HOSTNAME}/")
SPOTIFY_API_ENDPOINT = yarl.URL(f"https://api.{SPOTIFY_HOSTNAME}/v1/")

SPCLIENT_ENDPOINT = yarl.URL(f"https://gae-spclient.{SPOTIFY_HOSTNAME}/")


DEVICE_PAYLOAD = {
    "brand": "spotify",
    "capabilities": {
        "change_volume": True,
        "enable_play_token": True,
        "supports_file_media_type": True,
        "play_token_lost_behavior": "pause",
        "disable_connect": False,
        "audio_podcasts": True,
        "video_playback": True,
        "manifest_formats": [
            "file_ids_mp3",
            "file_urls_mp3",
            "manifest_ids_video",
            "file_urls_external",
            "file_ids_mp4",
            "file_ids_mp4_dual",
        ],
    },
    "device_type": "computer",
    "metadata": {},
    "model": "web_player",
    "name": "Spotivents",
    "device_id": SPOTIVENTS_DEVICE_ID,
    "platform_identifier": "web_player windows 10;desktop",
    "is_group": False,
}
