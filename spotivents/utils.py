from dataclasses import is_dataclass

forgivable_errors = (AttributeError, KeyError, TypeError)


def get_from_cluster_string(cluster, attributes: frozenset) -> str:

    attr, *attributes = attributes
    content = getattr(cluster, attr, None)

    if content is None:
        return None

    if attributes:
        return get_from_cluster_string(content, attributes)

    return content


def set_from_cluster_string(cluster: str, attributes: frozenset, value: str):
    attr, *attributes = attributes

    if attributes:
        set_from_cluster_string(getattr(cluster, attr), attributes, value)
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
