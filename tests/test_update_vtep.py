import unittest
from unittest.mock import patch, Mock
import socket
import sys
import types

# Provide a stub requests module if it's not installed
try:
    import requests  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - dependency may not be present
    requests = types.SimpleNamespace(RequestException=Exception, post=None)
    sys.modules['requests'] = requests

import update_vtep


class BuildFloodCommandsTest(unittest.TestCase):
    def test_build_flood_commands(self):
        remote = ["1.1.1.1", "2.2.2.2"]
        expected = [
            "interface Vxlan1",
            "vxlan flood vtep 1.1.1.1",
            "vxlan flood vtep 2.2.2.2",
            "exit",
        ]
        self.assertEqual(update_vtep.build_flood_commands(remote), expected)


class ParseArgsTest(unittest.TestCase):
    def test_parse_args(self):
        args = update_vtep.parse_args(["-u", "admin", "--verify-ssl", "leaf1", "leaf2"])
        self.assertEqual(args.username, "admin")
        self.assertTrue(args.verify_ssl)
        self.assertEqual(args.hosts, ["leaf1", "leaf2"])


class ResolveHostsTest(unittest.TestCase):
    @patch("update_vtep.socket.gethostbyname")
    def test_resolve_hosts(self, mock_gethostbyname):
        mock_gethostbyname.side_effect = ["192.0.2.1", "192.0.2.2"]
        result = update_vtep.resolve_hosts(["leaf1", "leaf2"])
        self.assertEqual(result, ["192.0.2.1", "192.0.2.2"])

    @patch("update_vtep.socket.gethostbyname", side_effect=socket.gaierror(1, "fail"))
    def test_resolve_hosts_error(self, mock_gethostbyname):
        with self.assertRaises(SystemExit) as cm:
            update_vtep.resolve_hosts(["badhost"])
        self.assertEqual(cm.exception.code, 1)


class SendEapiCommandsTest(unittest.TestCase):
    @patch("update_vtep.requests.post")
    def test_send_eapi_commands(self, mock_post):
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"status": "ok"}
        mock_post.return_value = mock_response

        result = update_vtep.send_eapi_commands(
            host="switch1",
            username="user",
            password="pass",
            commands=["show version"],
            verify_ssl=True,
        )

        self.assertEqual(result, {"status": "ok"})
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(kwargs["auth"], ("user", "pass"))
        self.assertEqual(kwargs["verify"], True)


class MainTest(unittest.TestCase):
    def test_main_not_enough_hosts(self):
        result = update_vtep.main(["-u", "admin", "leaf1"])
        self.assertEqual(result, 1)

    @patch("builtins.print")
    @patch("update_vtep.send_eapi_commands")
    @patch("update_vtep.resolve_hosts")
    @patch("update_vtep.getpass", return_value="pass")
    def test_main_success(self, mock_getpass, mock_resolve, mock_send, mock_print):
        mock_resolve.return_value = ["192.0.2.1", "192.0.2.2"]
        mock_send.return_value = {"result": "ok"}

        result = update_vtep.main(["-u", "admin", "leaf1", "leaf2"])

        self.assertEqual(result, 0)
        self.assertEqual(mock_send.call_count, 2)
        mock_send.assert_any_call(
            host="leaf1",
            username="admin",
            password="pass",
            commands=update_vtep.build_flood_commands(["192.0.2.2"]),
            verify_ssl=False,
        )
        mock_send.assert_any_call(
            host="leaf2",
            username="admin",
            password="pass",
            commands=update_vtep.build_flood_commands(["192.0.2.1"]),
            verify_ssl=False,
        )


if __name__ == "__main__":
    unittest.main()
