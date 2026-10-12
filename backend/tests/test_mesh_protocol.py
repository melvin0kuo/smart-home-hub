"""使用實機回傳封包驗證解析，無須連線或設備寫入。"""

import unittest

from app.integrations.mesh_protocol import parse_properties


def test_integer_command_ranges_and_rgb_byte_order():
    import pytest

    from app.integrations.mesh_protocol import integer_command

    assert integer_command(7, 3, 3, 0xFAEAD3).hex() == "0f20070000010303000450d3eafa00"
    assert integer_command(8, 2, 4, 15).hex() == "0c200800000102040001100f"
    for siid, piid, value in [(2, 4, 11), (2, 3, 7), (3, 2, 0), (3, 3, -1), (5, 1, 50), (2, 3, True)]:
        with pytest.raises(ValueError):
            integer_command(1, siid, piid, value)


def test_replay_window_accepts_out_of_order_but_rejects_duplicates():
    from app.integrations.mesh_protocol import ReplayWindow

    window = ReplayWindow()
    for counter in [1, 2, 5, 8, 6, 7]:
        window.accept(counter)
    with __import__("pytest").raises(ValueError):
        window.accept(6)
    window.accept(100)
    with __import__("pytest").raises(ValueError):
        window.accept(9)


class PropertyTests(unittest.TestCase):
    def test_unsolicited_properties_are_identified_by_their_own_ids(self):
        self.assertEqual(parse_properties(bytes.fromhex("0c2015000401020200011001")), {(2, 2): 1})
        self.assertEqual(parse_properties(bytes.fromhex("0c2016000401020300011004")), {(2, 3): 4})

    def test_session_ack_is_not_a_property_or_control_confirmation(self):
        self.assertEqual(parse_properties(bytes.fromhex("05200000f0")), {})

    def test_subscription_snapshot_has_its_own_status_field(self):
        self.assertEqual(parse_properties(bytes.fromhex("0e20010003010501000000011064")), {(5, 1): 100})

    def test_failed_property_response_is_not_a_reported_value(self):
        with self.assertRaises(ValueError):
            parse_properties(bytes.fromhex("0e20010003010501000100011064"))

    def test_truncated_packet_is_rejected(self):
        with self.assertRaises(ValueError):
            parse_properties(bytes.fromhex("0c20150004010202000110"))


if __name__ == "__main__":
    unittest.main()
