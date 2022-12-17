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


Similarly, you can control your Spotify session from this websocket. You can pause, play, skip, and even change the volume of your Spotify session.

> **Note:** Use `spotipy` or its async counterpart to query entities.

## Can I download from Spotify via this?

No, but you can use `librespot` for that. This will never be added to this project.


## Usage

- To watch over a state change:

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
        loop = asyncio.new_event_loop()
        loop.run_until_complete(main())
    ```

See more cluster change strings at [`cluster.py`](./spotivents/clustercls.py).


- To use Spotify playback controls (without running websocket):

    ```py
    import asyncio

    import aiohttp

    from spotivents.client import SpotifyClient
    from spotivents.controller import SpotifyAPIControllerClient

    SPOTIFY_COOKIE = "get your Spotify cookie named 'sp_dc' from your PC browser"


    async def main():

        async with aiohttp.ClientSession() as session:
            spotify_ws = await SpotifyClient.create(SPOTIFY_COOKIE, session=session)
            client = SpotifyAPIControllerClient(spotify_ws)

            await client.resume()


    if __name__ == "__main__":
        loop = asyncio.new_event_loop()
        loop.run_until_complete(main())
    ```

Pairing this can allow you to set up API level access to your Spotify session. Such as, setting custom volume levels for certain artists