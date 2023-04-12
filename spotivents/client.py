import asyncio
import logging
import threading
import time
import typing as t
from collections import defaultdict

import aiohttp

from .auth import SpotifyAuthenticator
from .clustercls import SpotifyDeviceStateChangeCluster, iter_handled_payloads
from .simstate import SpotiyState
from .utils import (
    CaseInsensitiveDict,
    get_from_cluster_getter,
    retain_nulled_values,
    truncated_repl,
)
from .ws import ws_connect


class SpotifyClient:

    logger = logging.getLogger("spotivents.client")

    def __init__(
        self,
        session: aiohttp.ClientSession,
        auth: "SpotifyAuthenticator",
        *,
        playable_spotivents: bool = False,
    ):

        self.loop = asyncio.get_event_loop()
        self.auth = auth
        self.session = session
        self.ws_task = None

        self.cluster_change_handlers = defaultdict(list)
        self.cluster: "SpotifyDeviceStateChangeCluster | None" = None
        self.cluster_receive_callbacks = list()
        self.cluster_ready_callbacks = list()

        self.latency: float = float("inf")
        self.last_ping: float = 0.0

        self.replace_state_callbacks = (
            [self.accept_replace_state, self.update_replace_state]
            if playable_spotivents
            else []
        )
        self.state: SpotiyState | None = None

    async def update_replace_state(self, content: t.Dict):
        if self.state is None:
            return

        await self.state.replace(content)

    async def accept_replace_state(self, content: t.Dict):

        if self.state:
            return

        if self.cluster is None or self.cluster.player_state is None:
            return

        if content["state_ref"] is None:
            return

        state_machine_id = content["state_machine"]["state_machine_id"]

        state_id = content["state_machine"]["states"][
            content["state_ref"]["state_index"]
        ]["state_id"]

        self.state = SpotiyState(
            self,
            state_id,
            state_machine_id,
            content,
        )

        return await self.state.accept()

    async def event_handler(self, content: t.Dict):

        if content["type"] == "pong":

            self.latency = time.time() - self.last_ping
            self.logger.debug(
                f"Spotify websocket running at latency: {self.latency * 1000:.2f}ms"
            )
            if self.latency > 1000:
                self.logger.warning(
                    f"Spotify websocket latency is high: {self.latency * 1000:.2f}ms, you may receive events late!"
                )
            return

        self.logger.debug(f"Received event payload: {truncated_repl(content)}")

        headers = CaseInsensitiveDict(content.get("headers", {}))

        if headers.get("content-type") != "application/json":
            return

        for payload in iter_handled_payloads(content.get("payloads", [])):
            cluster = payload.get("cluster")

            if isinstance(cluster, SpotifyDeviceStateChangeCluster):
                await self.cluster_handler(cluster)

            if payload.get("type") == "replace_state":
                SpotifyClient.dispatch_event_callbacks(
                    self.loop, self.replace_state_callbacks, payload
                )

    async def cluster_handler(
        self, cluster: t.Optional[SpotifyDeviceStateChangeCluster]
    ):
        if cluster is None:
            return

        old_cluster, self.cluster = self.cluster, cluster
        SpotifyClient.dispatch_event_callbacks(
            self.loop, self.cluster_receive_callbacks, cluster
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

    def on_cluster_change(self, *cluster_getters: t.Union[str, t.Callable[..., t.Any]]):

        for cluster_getter in cluster_getters:
            if not isinstance(cluster_getter, str) and not hasattr(
                cluster_getter, "__call__"
            ):
                raise TypeError("cluster_getter must be a string or a function")

        return SpotifyClient.event_handler_wrapper(
            *(
                self.cluster_change_handlers[cluster_getter]
                for cluster_getter in cluster_getters
            )
        )

    @staticmethod
    def event_handler_wrapper(*mutable_callbacks):
        def inner(func):
            if not asyncio.iscoroutinefunction(func):
                raise TypeError("Event handler must be a coroutine function")

            async def wrapper(*args, **kwargs):
                await func(*args, **kwargs)

            SpotifyClient.logger.debug(
                f"Registered event handler: {func!r} onto {mutable_callbacks!r}"
            )
            for mutable_callback in mutable_callbacks:
                mutable_callback.append(func)
            return wrapper

        return inner

    @staticmethod
    def dispatch_event_callbacks(
        loop: asyncio.AbstractEventLoop, mutable_callbacks: list, *args, **kwargs
    ):

        if mutable_callbacks:
            SpotifyClient.logger.debug(
                f"Dispatching event callbacks: {mutable_callbacks!r} with {truncated_repl((args, kwargs))})"
            )

        for callback in mutable_callbacks:
            loop.create_task(callback(*args, **kwargs))

    def on_cluster_receive(self):
        return SpotifyClient.event_handler_wrapper(self.cluster_receive_callbacks)

    def on_cluster_ready(self):
        return SpotifyClient.event_handler_wrapper(self.cluster_ready_callbacks)

    def on_replace_state(self):
        return SpotifyClient.event_handler_wrapper(self.replace_state_callbacks)

    async def run(self, *, is_blocking=True, is_invisible=False):

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
                self.auth,
                self.event_handler,
                cluster_future=cluster_future,
                invisible=is_invisible,
                heartbeat_coro=self.heartbeat_task,
            )
        )

        if is_blocking:
            await self.ws_task

    async def heartbeat_task(self, ws: aiohttp.ClientWebSocketResponse, interval=30):

        main_thread = threading.main_thread()

        while not ws.closed and main_thread.is_alive():
            await ws.send_json({"type": "ping"})
            self.last_ping = time.time()
            await asyncio.sleep(interval)
