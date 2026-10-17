import socket
import threading
import unittest

from adb_tcp_relay import serve


def unused_port() -> int:
    with socket.create_server(("127.0.0.1", 0)) as server:
        return server.getsockname()[1]


class AdbTcpRelayTest(unittest.TestCase):
    def test_accepts_a_new_client_after_the_first_disconnects(self) -> None:
        target_port = unused_port()
        relay_port = unused_port()

        def echo_server() -> None:
            with socket.create_server(("127.0.0.1", target_port)) as server:
                for _ in range(2):
                    connection, _ = server.accept()
                    with connection:
                        connection.sendall(connection.recv(1024))

        echo_thread = threading.Thread(target=echo_server)
        echo_thread.start()

        relay_thread = threading.Thread(
            target=serve,
            args=("127.0.0.1", target_port, relay_port),
            kwargs={"max_sessions": 2},
        )
        relay_thread.start()

        for message in (b"first", b"second"):
            with socket.create_connection(
                ("127.0.0.1", relay_port), timeout=2
            ) as client:
                client.sendall(message)
                self.assertEqual(client.recv(1024), message)

        relay_thread.join(timeout=2)
        echo_thread.join(timeout=2)
        self.assertFalse(relay_thread.is_alive())
        self.assertFalse(echo_thread.is_alive())


if __name__ == "__main__":
    unittest.main()
