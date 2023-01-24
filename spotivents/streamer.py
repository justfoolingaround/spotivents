import io
import typing as t

import aiohttp
from Cryptodome.Cipher import AES
from Cryptodome.Util import Counter

AUDIO_STREAMER_IV = 0x72E067FBDDCBCF77EBE8BC643F630D93
AUDIO_STREAMER_IV_INTERVAL = 0x100
AUDIO_CHUNK_SIZE = 0x20000


def decrypt_spotify_audio(audio_key: bytes, chunk: bytes, chunk_index: int):
    iv = AUDIO_STREAMER_IV + int(AUDIO_CHUNK_SIZE * chunk_index / 16)

    decrypted_chunks = bytearray()

    for size in range(0, len(chunk), 4096):

        cipher = AES.new(
            key=audio_key,
            mode=AES.MODE_CTR,
            counter=Counter.new(128, initial_value=iv),
        )
        count = min(4096, len(chunk) - size)
        decrypted_chunk = cipher.decrypt(chunk[size : size + count])

        if count != len(decrypted_chunk):
            raise RuntimeError(
                f"Couldn't process all data, actual: {len(decrypted_chunk)}, expected: {count}"
            )
        decrypted_chunks.extend(decrypted_chunk)

        iv += AUDIO_STREAMER_IV_INTERVAL
    return bytes(decrypted_chunks)


async def iter_spotify_audio_bytes(
    session: aiohttp.ClientSession,
    spotify_cdn_url: str,
    audio_key: bytes,
    *,
    chunk_index: int = 0,
    file_size: t.Optional[int] = None,
):
    """
    Iterates decrypted bytes from an encrypted Spotify track stream url.

    Use librespot to fetch the audio key.

    ```py
    from librespot.core import Session

    track_gid = ...
    file_gid = ...

    print(
        Session.Builder()
        .user_pass("example@gmail.com", "example@123")
        .create()
        .audio_key()
        .get_audio_key(
            bytes.fromhex(track_gid),
            bytes.fromhex(file_gid),
        )
    )
    ```

    Spotivents' downloading is FASTER & better.
    """
    while file_size is None or file_size > chunk_index * AUDIO_CHUNK_SIZE:

        from_chunk = chunk_index * AUDIO_CHUNK_SIZE
        to_chunk = from_chunk + AUDIO_CHUNK_SIZE - 1

        async with session.get(
            spotify_cdn_url, headers={"Range": f"bytes={from_chunk}-{to_chunk}"}
        ) as response:

            if file_size is None:
                file_size = int(response.headers["Content-Range"].split("/")[-1])

            chunk = await response.content.read()

            decrypted_chunk = decrypt_spotify_audio(audio_key, chunk, chunk_index)

            if chunk_index == 0:
                decrypted_chunk = decrypted_chunk[0xA7:]

            yield decrypted_chunk

            chunk_index += 1


def iter_spotify_audio_bytes_from_io(
    io_object: io.IOBase,
    audio_key: bytes,
    *,
    chunk_index: int = 0,
):
    chunk: bytes

    io_object.seek(chunk_index * AUDIO_CHUNK_SIZE)

    chunk = io_object.read(AUDIO_CHUNK_SIZE)

    while len(chunk) == AUDIO_CHUNK_SIZE:

        decrypted_chunk = decrypt_spotify_audio(audio_key, chunk, chunk_index)

        if chunk_index == 0:
            decrypted_chunk = decrypted_chunk[0xA7:]

        yield decrypted_chunk

        chunk_index += 1
        chunk = io_object.read(AUDIO_CHUNK_SIZE)
