"""Mesh 屬性封包解析；以實機捕捉的封包作測試。"""


class ReplayWindow:
    """實機的通知與查詢回覆可能交錯；允許小範圍亂序，拒絕重複及過舊封包。"""

    def __init__(self):
        self.highest = -1
        self.seen = set()

    def accept(self, counter):
        if counter in self.seen or counter <= self.highest - 64:
            raise ValueError("replayed_packet")
        self.highest = max(counter, self.highest)
        self.seen = {value for value in self.seen if value > self.highest - 64}
        self.seen.add(counter)


INTEGER_PROPERTIES = {
    (2, 3): (2, 6, 1, 1, 0x10),
    (2, 4): (10, 20, 5, 1, 0x10),
    (3, 2): (1, 100, 1, 1, 0x10),
    (3, 3): (0, 0xFFFFFF, 1, 4, 0x50),
}


def integer_command(tid, siid, piid, value):
    if (siid, piid) not in INTEGER_PROPERTIES or type(value) is not int:
        raise ValueError("unsupported_integer_control")
    low, high, step, size, kind = INTEGER_PROPERTIES[siid, piid]
    if not low <= value <= high or (value - low) % step:
        raise ValueError("invalid_integer_value")
    return bytes([11 + size, 0x20, tid & 255, tid >> 8, 0, 1, siid, piid, 0, size, kind]) + value.to_bytes(
        size, "little"
    )


def parse_properties(payload):
    if len(payload) < 5 or payload[0] != len(payload) or payload[1] != 0x20:
        raise ValueError("invalid_property_packet")
    if payload[4] not in {3, 4}:
        return {}
    if len(payload) < 6:
        raise ValueError("missing_property_count")
    position = 6
    properties = {}
    for _ in range(payload[5]):
        if position + 5 > len(payload):
            raise ValueError("truncated_property")
        siid = payload[position]
        piid = int.from_bytes(payload[position + 1 : position + 3], "little")
        position += 3
        if payload[4] == 3:
            if position + 4 > len(payload) or payload[position : position + 2] != b"\x00\x00":
                raise ValueError("property_query_failed")
            position += 2
        size, kind = payload[position : position + 2]
        position += 2
        if position + size > len(payload):
            raise ValueError("truncated_value")
        value = payload[position : position + size]
        position += size
        expected_sizes = {0x00: 1, 0x10: 1, 0x20: 1, 0x30: 2, 0x40: 2, 0x50: 4, 0x60: 4}
        if expected_sizes.get(kind) != size:
            raise ValueError("unsupported_value_type")
        properties[siid, piid] = int.from_bytes(value, "little", signed=kind in {0x20, 0x40, 0x60})
    if position != len(payload):
        raise ValueError("unexpected_property_tail")
    return properties
