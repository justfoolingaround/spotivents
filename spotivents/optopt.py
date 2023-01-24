try:
    import orjson as json

    dumps_function = json.dumps

    def patched_dumps(*args, **kwargs):
        return dumps_function(*args, **kwargs).decode()

    json.dumps = patched_dumps


except ImportError:
    import json
