import asyncio
from collections import defaultdict

import aiohttp

from .clustercls import SpotifyDeviceStateChangeCluster, iter_handled_payloads
from .constants import SPOTIFY_HOSTNAME
from .utils import (
    get_from_cluster_string,
    retain_nulled_values,
    set_from_cluster_string,
)
from .ws import ws_connect


class SpotifyClient:
    def __init__(
        self, session: aiohttp.ClientSession, client_id: str, access_token: str
    ):

        self.loop = asyncio.get_running_loop()
        self.session = session
        self.access_token = access_token

        self.ws_task = self.loop.create_task(
            ws_connect(session, access_token, client_id, self.event_handler)
        )

        self.cluster_change_handlers = defaultdict(list)

        self.cluster = None
        self.cluster_load_callbacks = list()

    async def event_handler(self, content):

        if content["type"] == "pong":
            return print("Pong!")

        for payload in iter_handled_payloads(content["payloads"]):
            cluster = payload["cluster"]

            if isinstance(cluster, SpotifyDeviceStateChangeCluster):
                await self.cluster_change_handler(cluster)

    async def cluster_change_handler(self, cluster):

        for callback in self.cluster_load_callbacks:
            self.loop.create_task(callback(cluster))

        if self.cluster is None:
            self.cluster = cluster
            return

        for cluster_string, handlers in self.cluster_change_handlers.items():

            old_value = get_from_cluster_string(self.cluster, cluster_string)
            new_value = get_from_cluster_string(cluster, cluster_string)

            if new_value is None:
                set_from_cluster_string(self.cluster, cluster_string, old_value)
            else:
                if old_value != new_value:
                    for handler in handlers:
                        self.loop.create_task(
                            handler(self.cluster, old_value, new_value)
                        )

        retain_nulled_values(self.cluster, cluster)
        self.cluster = cluster

    def on_cluster_change(self, cluster_string: str):
        def inner(func):

            if not asyncio.iscoroutinefunction(func):
                raise TypeError("Event handler must be a coroutine function")

            async def wrapper(*args, **kwargs):
                await func(*args, **kwargs)

            self.cluster_change_handlers[tuple(cluster_string.split("."))].append(
                wrapper
            )
            return wrapper

        return inner

    def on_cluster_recieve(self):
        def inner(func):
            if not asyncio.iscoroutinefunction(func):
                raise TypeError("Event handler must be a coroutine function")

            self.cluster_load_callbacks.append(func)

            async def wrapper(cluster):
                await func(cluster)

            return wrapper

        return inner

    @classmethod
    async def create(cls, spotify_cookie, *, session=None):

        session = session or aiohttp.ClientSession()

        async with session.get(
            f"https://open.{SPOTIFY_HOSTNAME}/get_access_token",
            headers={
                "Cookie": f"sp_dc={spotify_cookie}",
            },
        ) as response:
            response.raise_for_status()
            data = await response.json()

        return cls(session, data["clientId"], data["accessToken"])

    async def run(self):
        await self.ws_task

    # TODO: Add player controls
    # TODO: Add entity querying [playlists, albums, artists, tracks]
    # TODO: Add player cluster querying
