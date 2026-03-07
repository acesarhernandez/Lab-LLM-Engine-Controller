from __future__ import annotations

import unittest

from llm_engine_server.ui import render_dashboard_html
from llm_engine_server.wol import build_magic_packet, mask_mac_address, normalize_mac_address


class WakeOnLanTests(unittest.TestCase):
    def test_normalize_and_mask_mac_address(self) -> None:
        self.assertEqual(normalize_mac_address("AA-BB-CC-DD-EE-FF"), "aabbccddeeff")
        self.assertEqual(mask_mac_address("AA:BB:CC:DD:EE:FF"), "aa:bb:**:**:ee:ff")

    def test_build_magic_packet_size(self) -> None:
        packet = build_magic_packet("AA:BB:CC:DD:EE:FF")
        self.assertEqual(len(packet), 102)
        self.assertTrue(packet.startswith(b"\xff" * 6))

    def test_dashboard_html_contains_core_controls(self) -> None:
        html = render_dashboard_html()
        self.assertIn("/v1/engine/status", html)
        self.assertIn("/v1/engine/wake", html)
        self.assertIn("/v1/engine/ensure-ready", html)
        self.assertIn("LLM Engine Control", html)

    def test_dashboard_html_renders_release_version(self) -> None:
        html = render_dashboard_html("9.9.9")
        self.assertIn("Release 9.9.9 Control Surface", html)
        self.assertIn("LLM Engine Server Release 9.9.9", html)
        self.assertNotIn("__RELEASE_VERSION__", html)


if __name__ == "__main__":
    unittest.main()
