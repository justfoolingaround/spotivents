<h1 align="center"><img src="https://capsule-render.vercel.app/api?type=soft&fontColor=1ed760&text=spotivents&height=150&fontSize=60&desc=Fully%20asynchronous%20Spotify%20Dealer%20and%20Connect%20Client&descAlignY=75&descAlign=60&color=00000000&animation=twinkling"></h1>

Spotify client from a web browser can generally control your playback and keep track of what is going on in **real time**. This is done via websockets and various different requests.

`spotivents` uses only one library, `aiohttp`, to communicate with the client just using a singular browser cookie. Using this project, you can:
- Receive playbacks changes as soon as they happen.
- Control Spotify playback using pretty straight-forward methods.
- Fetch track lyrics **from** Spotify.
- Query tracks, playlists, albums, artists, shows, episodes and nearly all entities' metadata using the internal API.

## Usages

### Authenticating Spotivents to your client

```py
import aiohttp

from spotivents import SpotifyAuthenticator

SPOTIFY_COOKIE = "Your Spotify sp_dc cookie here!"

session = aiohttp.ClientSession()
auth = SpotifyAuthenticator(session, SPOTIFY_COOKIE)
```

The authenticator will hold every single authentications our controllers may need.

### Controlling your playbacks

```py
import aiohttp
import asyncio

from spotivents import SpotifyAPIControllerClient, SpotifyAuthenticator

SPOTIFY_COOKIE = "Your Spotify sp_dc cookie here!"

session = aiohttp.ClientSession()
auth = SpotifyAuthenticator(session, SPOTIFY_COOKIE)

controller = SpotifyAPIControllerClient(session, auth)

async def main():
    # Resume the track playback!
    await controller.resume()

loop = asyncio.get_event_loop()
loop.run_until_complete(main())
```

The controller needs to be initalised with a session and the authentication class. The session need not be the same but it is good practice to re-use already active sessions.

> **Note**: The controller within Spotivents does not require a Premium account to control your playbacks.

> **Warning**: Controller is practically a dumb remote. This means that it does not take in account for the what is going on with the playback. The API will return an error reply when the controller tries to resume an already playing track.

> **Warning**: This example **will not** work with non-Premium accounts as there is no way of obtaining the active device without using a Premium endpoint. Pairing the controller with the websocket will be able to get you an `active_device_id` to use with the controller.

To make the controller better and an absolutely great tool, you should use it with the Spotivents websocket client.

### Getting real-time events and using the controller

```py
import asyncio

import aiohttp

from spotivents import SpotifyAPIControllerClient, SpotifyAuthenticator, SpotifyClient

SPOTIFY_COOKIE = "Your Spotify sp_dc cookie here!"

session = aiohttp.ClientSession()
auth = SpotifyAuthenticator(session, SPOTIFY_COOKIE)
ws_client = SpotifyClient(session, auth)
controller = SpotifyAPIControllerClient(session, auth)


@ws_client.on_cluster_change("player_state.track.uri")
async def on_playback_change(cluster, before, after):
    if after is None:
        return

    track_details = await controller.query_entity_metadata(after[14:], "track")

    out = f"{track_details['name']} by {', '.join(artist['name'] for artist in track_details['artist'])}"

    is_paused = cluster.player_state.is_paused

    if is_paused:
        print(f"Resuming playback for {out!r}")
        await controller.resume(to_device=cluster.active_device_id)
    else:
        print(f"You're listening to {out!r}!")


async def main():
    await ws_client.run()


loop = asyncio.get_event_loop()
loop.run_until_complete(main())
```

> **Note**: You will have to use the `to_device` keyword-argument on the playback controls if you're a regular Spotify user.

## Downloading

Downloading tracks is not impossible with `spotivents` but is definitely a challenge for most people. This can be done quite easily by using the Spotify AP endpoints. The AP endpoints can give an AES decryption key for the tracks.

```
[Bearer Authenticated] GET https://gae-spclient.spotify.com/storage-resolve/v2/files/audio/interactive/{file_type}/{file_id}
```

This will give you the necessary manifest URLs. The file `id` and the `type` will be given by `controller.query_entity_metadata` if the entity type is `track`.
