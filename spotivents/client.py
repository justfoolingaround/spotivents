import asyncio
import time
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
        self,
        session: aiohttp.ClientSession,
        spotify_cookie: str,
    ):

        self.loop = asyncio.get_running_loop()
        self.cookie = spotify_cookie

        self.session = session

        self.ws_task = None

        self.cluster_change_handlers = defaultdict(list)

        self.cluster: "SpotifyDeviceStateChangeCluster | None" = None
        self.cluster_load_callbacks = list()
        self.cluster_ready_callbacks = list()

        self.raw_bearer_response = {}
        self.raw_client_token_response = {}

    @staticmethod
    async def get_access_token_from_cookie(session, spotify_cookie):

        async with session.get(
            f"https://open.{SPOTIFY_HOSTNAME}/get_access_token",
            headers={"Cookie": f"sp_dc={spotify_cookie}"},
        ) as response:
            return await response.json()

    async def bearer_token(self):

        if self.raw_bearer_response.get("accessTokenExpirationTimestampMs", 0) > (
            time.time() * 1000
        ):
            return self.raw_bearer_response

        self.raw_bearer_response = await self.get_access_token_from_cookie(
            self.session, self.cookie
        )

        return await self.bearer_token()

    async def client_token(self):

        if self.raw_client_token_response.get("expires", 0) > time.time():
            return self.raw_client_token_response

        async with self.session.post(
            f"https://clienttoken.{SPOTIFY_HOSTNAME}/v1/clienttoken",
            json={
                "client_data": {
                    "client_id": (await self.bearer_token())["clientId"],
                    "js_sdk_data": {},
                }
            },
            headers={
                "accept": "application/json",
            },
        ) as response:
            self.raw_client_token_response = await response.json()

        self.raw_client_token_response.update(
            expires=time.time()
            + self.raw_client_token_response["granted_token"]["expires_after_seconds"]
        )

        return await self.client_token()

    async def event_handler(self, content):

        if content["type"] == "pong":
            return print("Pong!")

        for payload in iter_handled_payloads(content["payloads"]):
            cluster = payload["cluster"]

            if isinstance(cluster, SpotifyDeviceStateChangeCluster):
                await self.cluster_change_handler(cluster)

    async def cluster_change_handler(self, cluster):

        old_cluster = self.cluster
        self.cluster = cluster

        for callback in self.cluster_load_callbacks:
            self.loop.create_task(callback(cluster))

        if old_cluster is None:

            for callback in self.cluster_ready_callbacks:
                self.loop.create_task(callback(cluster))

        for cluster_string, handlers in self.cluster_change_handlers.items():

            old_value = get_from_cluster_string(old_cluster, cluster_string)
            new_value = get_from_cluster_string(cluster, cluster_string)

            if new_value is None:
                set_from_cluster_string(self.cluster, cluster_string, old_value)
            else:
                if old_value != new_value:
                    for handler in handlers:
                        self.loop.create_task(
                            handler(self.cluster, old_value, new_value)
                        )

        retain_nulled_values(old_cluster, cluster)

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

    def on_cluster_ready(self):
        def inner(func):
            if not asyncio.iscoroutinefunction(func):
                raise TypeError("Event handler must be a coroutine function")

            self.cluster_ready_callbacks.append(func)

            async def wrapper(cluster):
                await func(cluster)

            return wrapper

        return inner

    @classmethod
    async def create(cls, spotify_cookie, *, session=None):
        session = session or aiohttp.ClientSession()
        return cls(session, spotify_cookie)

    async def run(self, *, is_blocking=True):

        self.ws_task = self.loop.create_task(
            ws_connect(
                self.session,
                (await self.bearer_token())["accessToken"],
                (await self.bearer_token())["clientId"],
                self.event_handler,
            )
        )

        if is_blocking:
            await self.ws_task

    # TODO: Add entity querying [playlists, albums, artists, tracks]
    # TODO: Add player cluster querying
