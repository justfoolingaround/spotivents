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
