import asyncio

import httpcore
import pytest

from app.core.network_security import (
    MAX_NETWORK_TIMEOUT,
    NetworkSecurityBackend,
)


@pytest.mark.parametrize(
    "timeout",
    [
        float("nan"),
        float("inf"),
        float("-inf"),
        -1,
        True,
        "10",
        10 ** 1000,
        1e308,
        MAX_NETWORK_TIMEOUT + 1,
    ],
)
def test_network_backend_rejects_invalid_timeout(timeout):
    async def run_test():
        backend = NetworkSecurityBackend()

        with pytest.raises(httpcore.ConnectTimeout):
            await backend.connect_tcp(
                host="93.184.216.34",
                port=443,
                timeout=timeout,
            )

    asyncio.run(run_test())


def test_network_backend_accepts_zero_timeout_as_immediate_timeout():
    async def run_test():
        backend = NetworkSecurityBackend()

        with pytest.raises(httpcore.ConnectTimeout):
            await backend.connect_tcp(
                host="93.184.216.34",
                port=443,
                timeout=0,
            )

    asyncio.run(run_test())


def test_network_backend_accepts_maximum_timeout():
    connected = []

    class RecordingBackend(NetworkSecurityBackend):
        async def _connect_to_ip(
            self,
            address,
            port,
            timeout,
            local_address,
            socket_options,
        ):
            connected.append(str(address))
            return "connected"

    async def run_test():
        backend = RecordingBackend()

        result = await backend.connect_tcp(
            host="93.184.216.34",
            port=443,
            timeout=MAX_NETWORK_TIMEOUT,
        )

        assert result == "connected"

    asyncio.run(run_test())

    assert connected == ["93.184.216.34"]