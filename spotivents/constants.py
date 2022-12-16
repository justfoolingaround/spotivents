import yarl

SPOTIFY_HOSTNAME = "spotify.com"

EVENT_DEALER_WS = yarl.URL(f"wss://dealer.{SPOTIFY_HOSTNAME}/")
SPOTIFY_API_ENDPOINT = yarl.URL(f"https://api.{SPOTIFY_HOSTNAME}/v1/")

SPCLIENT_ENDPOINT = yarl.URL(f"https://gae-spclient.{SPOTIFY_HOSTNAME}/")
