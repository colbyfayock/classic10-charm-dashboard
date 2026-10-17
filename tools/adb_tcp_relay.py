#!/usr/bin/env python3
import argparse
import selectors
import socket
from typing import Optional


def relay(left: socket.socket, right: socket.socket) -> None:
    selector = selectors.DefaultSelector()
    selector.register(left, selectors.EVENT_READ, right)
    selector.register(right, selectors.EVENT_READ, left)

    try:
        while True:
            for key, _ in selector.select():
                source = key.fileobj
                destination = key.data
                try:
                    data = source.recv(65536)
                except ConnectionResetError:
                    return
                if not data:
                    return
                destination.sendall(data)
    finally:
        selector.close()


def serve(
    target_host: str,
    target_port: int,
    listen_port: int,
    *,
    max_sessions: Optional[int] = None,
) -> None:
    sessions = 0

    # Bind only to loopback so the relay never exposes ADB to another host.
    with socket.create_server(("127.0.0.1", listen_port)) as server:
        while max_sessions is None or sessions < max_sessions:
            client, _ = server.accept()
            with client:
                try:
                    with socket.create_connection(
                        (target_host, target_port), timeout=5
                    ) as target:
                        target.settimeout(None)
                        relay(client, target)
                except (ConnectionError, OSError):
                    pass
            sessions += 1


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Forward localhost TCP traffic to a frame's network ADB port."
    )
    parser.add_argument("target_host")
    parser.add_argument("--target-port", type=int, default=5555)
    parser.add_argument("--listen-port", type=int, default=15555)
    args = parser.parse_args()

    print(
        f"Relaying 127.0.0.1:{args.listen_port} to "
        f"{args.target_host}:{args.target_port}"
    )
    serve(args.target_host, args.target_port, args.listen_port)


if __name__ == "__main__":
    main()
