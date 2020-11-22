import asyncio
from contextlib import asynccontextmanager
from itertools import count
import logging
import socket

logger = logging.getLogger(__file__)


@asynccontextmanager
async def open_connection(host, port):
    for attempt_number in count():
        try:
            reader, writer = await asyncio.open_connection(host, port)
            break
        except socket.gaierror:
            logger.error(f'Can not connect to {host}')
            if attempt_number > 2:
                await asyncio.sleep(1)
    try:
        logger.debug(f'Establish a connection with {host}')
        yield reader, writer
    finally:
        writer.close()
        await writer.wait_closed()
