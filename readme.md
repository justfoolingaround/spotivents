<h1 align="center">Spotivents<sup><sup>Only uses <code>aiohttp</code></sup></sup></h1>

A fully asynchronous Spotify websocket event reciever in Python.

## Hey, what's this?

Spotify, when ran, uses a websocket to send various events across the subscribing clients. This project just uses a prominent cluster event called `DEVICE_STATE_CHANGED` to get nearly everything about your Spotify play session.

Notably, we can recieve the following information **as soon as it changes** without having to constantly send requests to the Spotify API:

- Playback state
    - Playback progress
    - Playback quality
    - Play/Pause state
    - Shuffle/Repeat state
    - Volume (across all devices)
    - Next/Previous tracks
- Device state
    - IP address
    - Name specifications

> **Note:** Use `spotipy` or its async counterpart to query entities.

## Can I change the data?

This client does not send HTTP requests to the Spotify API as of right now. However, this is a planned feature. **This client will support playback controls even on non-premium accounts in the future by using Spotify client methods.**

## Can I download from Spotify via this?

No, but you can use `librespot` for that. This will never be added to this project.


## Usage

```py
import asyncio

from spotivents.client import SpotifyClient

SPOTIFY_COOKIE = "get your Spotify cookie named 'sp_dc' from your PC browser"


async def main():

    spotify_ws = await SpotifyClient.create(SPOTIFY_COOKIE)

    @spotify_ws.on_cluster_change("player_state.is_paused")
    async def on_playback_change(cluster, before, after):
        if after:
            print("Not vibing? :(")
        else:
            print("Vibing! :)")

    await spotify_ws.run()


if __name__ == "__main__":
    asyncio.run(main())
```

See more cluster change strings at [`cluster.py`](./spotivents/clustercls.py).