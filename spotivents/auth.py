import logging
import re
import time
import typing as t

from .constants import SPOTIFY_HOSTNAME
from .optopt import json

ACCESS_TOKEN_REGEX = re.compile(
    r"<script id=\"session\" data-testid=\"session\" type=\"application/json\">\s*(.+?)\s*</script>",
    re.MULTILINE | re.DOTALL,
)


class SpotifyAuthenticator:
    def __init__(self, session, cookie):

        self.logger = logging.getLogger("spotivents.authenticator")

        self.session = session
        self.cookie = cookie

        self.raw_bearer_response = {}
        self.raw_client_token_response = {}

    @staticmethod
    async def get_access_token_from_cookie_from_web(session, spotify_cookie) -> t.Dict:
        async with session.get(
            f"https://open.{SPOTIFY_HOSTNAME}/",
            headers={"Cookie": f"sp_dc={spotify_cookie}"},
        ) as response:
            content = await response.text()

        match = ACCESS_TOKEN_REGEX.search(content)

        if match is None:
            return {}

        return json.loads(match.group(1))

    @staticmethod
    async def get_access_token_from_cookie(session, spotify_cookie):

        async with session.get(
            f"https://open.{SPOTIFY_HOSTNAME}/get_access_token",
            params={
                "reason": "transport",
                "productType": "web-player",
            },
            headers={"Cookie": f"sp_dc={spotify_cookie}"},
        ) as response:

            if response.status >= 400:
                return await SpotifyAuthenticator.get_access_token_from_cookie_from_web(
                    session, spotify_cookie
                )
            return await response.json()

    async def bearer_token(self):

        if self.raw_bearer_response.get("accessTokenExpirationTimestampMs", 0) > (
            time.time() * 1000
        ):
            self.logger.debug("Cached bearer token has not expired, returning it.")
            return self.raw_bearer_response

        self.logger.debug("Fetching a bearer token and recursively returning.")
        self.raw_bearer_response = await self.get_access_token_from_cookie(
            self.session, self.cookie
        )

        return await self.bearer_token()

    async def client_token(self):

        if self.raw_client_token_response.get("expires", 0) > time.time():
            self.logger.debug("Cached client token has not expired, returning it.")
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

        self.logger.debug("Fetched a client token and recursively returning.")
        self.raw_client_token_response.update(
            expires=time.time()
            + self.raw_client_token_response["granted_token"]["expires_after_seconds"]
        )

        return await self.client_token()
