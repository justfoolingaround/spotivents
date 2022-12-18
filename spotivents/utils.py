from dataclasses import is_dataclass


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

    for field in old_dataclass.__dataclass_fields__:
        old_value = getattr(old_dataclass, field)
        new_value = getattr(new_dataclass, field, None)

        if new_value is None:
            setattr(new_dataclass, field, old_value)
        else:
            if is_dataclass(new_value) and is_dataclass(old_value):
                retain_nulled_values(old_value, new_value)
