from __future__ import annotations

import unittest

from llm_engine_server.wol import build_magic_packet, mask_mac_address, normalize_mac_address


class WakeOnLanTests(unittest.TestCase):
    def test_normalize_and_mask_mac_address(self) -> None:
        self.assertEqual(normalize_mac_address("AA-BB-CC-DD-EE-FF"), "aabbccddeeff")
        self.assertEqual(mask_mac_address("AA:BB:CC:DD:EE:FF"), "aa:bb:**:**:ee:ff")

    def test_build_magic_packet_size(self) -> None:
        packet = build_magic_packet("AA:BB:CC:DD:EE:FF")
        self.assertEqual(len(packet), 102)
        self.assertTrue(packet.startswith(b"\xff" * 6))


if __name__ == "__main__":
    unittest.main()

