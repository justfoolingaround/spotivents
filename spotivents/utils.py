import time
import typing as t
import webbrowser
from dataclasses import is_dataclass

forgivable_errors = (AttributeError, KeyError, TypeError)


def get_from_cluster_string(cluster, attributes: frozenset) -> t.Optional[str]:

    attr, *attrs = attributes
    content = getattr(cluster, attr, None)

    if content is None:
        return None

    if attrs:
        return get_from_cluster_string(content, frozenset(attrs))

    return content


def set_from_cluster_string(cluster: str, attributes: frozenset, value: str):
    attr, *attrs = attributes

    if attrs:
        set_from_cluster_string(getattr(cluster, attr), frozenset(attrs), value)
    else:
        setattr(cluster, attr, value)


def retain_nulled_values(old_dataclass, new_dataclass):

    if not is_dataclass(old_dataclass):
        return

    for field in old_dataclass.__dataclass_fields__:
        old_value = getattr(old_dataclass, field)
        new_value = getattr(new_dataclass, field, None)

        if new_value is None and old_value is not None:
            if isinstance(old_value, bool) and old_value:
                setattr(new_dataclass, field, False)
            else:
                setattr(new_dataclass, field, old_value)
        else:
            if is_dataclass(new_value):
                retain_nulled_values(old_value, new_value)


def get_from_cluster_getter(
    cluster, cluster_getter, *, forgivable_errors=forgivable_errors
):
    if hasattr(cluster_getter, "__call__"):
        try:
            return cluster_getter(cluster)
        except forgivable_errors as _:
            return None
    else:
        return get_from_cluster_string(cluster, cluster_getter.split("."))


B62_CHARSET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
B62_INVERTED_CHARSET = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"


def decode_basex_to_bytes(value: str, charset=B62_INVERTED_CHARSET):
    base = len(charset)

    decoded = 0
    for str_at in value:
        decoded = (decoded * base) + charset.index(str_at)

    buf = bytearray()

    while decoded > 0:
        buf.append(decoded & 0xFF)
        decoded >>= 8
    buf.reverse()

    return bytes(buf)


def encode_bytes_to_basex(
    value: bytes,
    charset=B62_INVERTED_CHARSET,
):
    base = len(charset)

    encoded = 0
    for b in value:
        encoded = (encoded << 8) | b

    result = ""
    while encoded > 0:
        result += charset[encoded % base]
        encoded //= base
    return result[::-1]


def get_mosaic_image_url(
    image_1,
    image_2,
    image_3,
    image_4,
    size=640,
):
    assert size in (640, 300), "Mosaic image size must be 640 or 300"
    return "https://mosaic.scdn.co/" f"{size}/{image_1}{image_2}{image_3}{image_4}"


def run_spotify_protocol(
    content_id: str,
    content_type: str,
    autoraise: bool = False,
):
    """
    Opens up a closed Spotify client.
    """
    return webbrowser.open(
        f"spotify://spotify:{content_type}:{content_id}", autoraise=autoraise
    )


def truncated_repl(object, *, maxlen: int = 50):
    """
    Change <xyz object at 0x000000000000> to <xyz…> for eye bleaching.
    """
    out = repr(object)

    suffix = out[-1]

    if suffix in ">'\")}]":
        suffix = "…" + suffix

    if len(out) > maxlen:
        return out[: maxlen - len(suffix)] + suffix

    return out


class CaseInsensitiveDict(dict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__normalise_keys()

    def __setitem__(self, key, value):
        super().__setitem__(key.lower(), value)

    def __getitem__(self, key):
        return super().__getitem__(key.lower())

    def __delitem__(self, key):
        return super().__delitem__(key.lower())

    def __contains__(self, key):
        return super().__contains__(key.lower())

    def __normalise_keys(self):
        for key in list(self.keys()):
            self[key.lower()] = self.pop(key)

    def update(self, *args, **kwargs):
        super().update(*args, **kwargs)
        self.__normalise_keys()

    def copy(self):
        return CaseInsensitiveDict(self)

    def __copy__(self):
        return self.copy()

    def __deepcopy__(self, memo):
        import copy

        return CaseInsensitiveDict(copy.deepcopy(dict(self), memo))

    def __repr__(self):
        return f"{self.__class__.__name__}({super().__repr__()})"

    def __str__(self):
        return f"{self.__class__.__name__}({super().__str__()})"

    def get(self, key, default=None):
        return super().get(key.lower(), default)

    def pop(self, key, default=None):
        return super().pop(key.lower(), default)

    def setdefault(self, key, default=None):
        return super().setdefault(key.lower(), default)

    def has_key(self, k):
        return k.lower() in self

    def __eq__(self, other):
        return dict(self.items()) == dict(other.items())


class TimePosition:
    def __init__(self, is_moving: bool, position: int) -> None:
        self.is_moving = is_moving
        self.position = position

        self.time = time.time()

    def value(self):
        if self.is_moving:
            return self.position + (time.time() - self.time) * 1000
        else:
            return self.position
