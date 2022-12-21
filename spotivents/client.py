import asyncio
import logging
from collections import defaultdict

import aiohttp

from .auth import SpotifyAuthenticator
from .clustercls import SpotifyDeviceStateChangeCluster, iter_handled_payloads
from .utils import get_from_cluster_getter, retain_nulled_values
from .ws import ws_connect


class SpotifyClient:

    logger = logging.getLogger("spotivents.client")

    def __init__(
        self,
        session: aiohttp.ClientSession,
        auth: "SpotifyAuthenticator",
    ):

        self.loop = asyncio.get_running_loop()
        self.auth = auth
        self.session = session
        self.ws_task = None

        self.cluster_change_handlers = defaultdict(list)
        self.cluster: "SpotifyDeviceStateChangeCluster | None" = None
        self.cluster_recieve_callbacks = list()
        self.cluster_ready_callbacks = list()

        self.replace_state_callbacks = list()

    async def event_handler(self, content):

        self.logger.debug(f"Received event payload: {content}")

        if content["type"] == "pong":
            return

        for payload in iter_handled_payloads(content["payloads"]):
            cluster = payload.get("cluster")

            if isinstance(cluster, SpotifyDeviceStateChangeCluster):
                await self.cluster_handler(cluster)

            if payload.get("type") == "replace_state":
                SpotifyClient.dispatch_event_callbacks(
                    self.loop, self.replace_state_callbacks, payload
                )

    async def cluster_handler(self, cluster):

        old_cluster, self.cluster = self.cluster, cluster
        SpotifyClient.dispatch_event_callbacks(
            self.loop, self.cluster_recieve_callbacks, cluster
        )

        if old_cluster is None:
            SpotifyClient.dispatch_event_callbacks(
                self.loop, self.cluster_ready_callbacks, cluster
            )

        for cluster_getter, handlers in self.cluster_change_handlers.items():

            old_value, new_value = get_from_cluster_getter(
                old_cluster, cluster_getter
            ), get_from_cluster_getter(cluster, cluster_getter)

            if old_value != new_value:
                SpotifyClient.dispatch_event_callbacks(
                    self.loop, handlers, self.cluster, old_value, new_value
                )

        retain_nulled_values(old_cluster, cluster)

    def on_cluster_change(self, cluster_getter):

        if not isinstance(cluster_getter, str) and not hasattr(
            cluster_getter, "__call__"
        ):
            raise TypeError("cluster_getter must be a string or a function")

        return SpotifyClient.event_handler_wrapper(
            self.cluster_change_handlers[cluster_getter]
        )

    @staticmethod
    def event_handler_wrapper(mutable_callbacks):
        def inner(func):
            if not asyncio.iscoroutinefunction(func):
                raise TypeError("Event handler must be a coroutine function")

            async def wrapper(*args, **kwargs):
                await func(*args, **kwargs)

            SpotifyClient.logger.debug(
                f"Registered event handler: {func!r} onto {mutable_callbacks!r}"
            )
            mutable_callbacks.append(func)
            return wrapper

        return inner

    @staticmethod
    def dispatch_event_callbacks(
        loop: asyncio.BaseEventLoop, mutable_callbacks: list, *args, **kwargs
    ):
        SpotifyClient.logger.debug(
            f"Dispatching event callbacks: {mutable_callbacks!r} with {(args, kwargs)})"
        )
        for callback in mutable_callbacks:
            loop.create_task(callback(*args, **kwargs))

    def on_cluster_recieve(self):
        return SpotifyClient.event_handler_wrapper(self.cluster_recieve_callbacks)

    def on_cluster_ready(self):
        return SpotifyClient.event_handler_wrapper(self.cluster_ready_callbacks)

    def on_replace_state(self):
        return SpotifyClient.event_handler_wrapper(self.replace_state_callbacks)

    async def run(self, *, is_blocking=True, invisible=True):

        cluster_future = asyncio.Future()
        cluster_future.add_done_callback(
            lambda future: self.loop.create_task(
                self.cluster_handler(
                    SpotifyDeviceStateChangeCluster.from_dict(
                        "ON_LOAD", future.result()
                    )
                )
            )
        )

        self.logger.debug("Starting websocket connection to Spotify dealer.")
        self.ws_task = self.loop.create_task(
            ws_connect(
                self.session,
                (await self.auth.bearer_token())["accessToken"],
                (await self.auth.bearer_token())["clientId"],
                self.event_handler,
                invisible=invisible,
                cluster_future=cluster_future,
            )
        )

        if is_blocking:
            await self.ws_task
