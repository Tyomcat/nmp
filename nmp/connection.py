#!/bin/env python3

import secrets
import ssl
import struct
import websockets
from collections import deque
from random import randint
from nmp.log import get_logger
from nmp.proto import NMP_UDP_PIPE_IP

MAX_MSG_BUF_SIZE = 2 ** 16
MAX_IDLE_CONNECTION = 2 ** 10


class ConnectionPool:
    def __init__(self, endpoint, token) -> None:
        self.logger = get_logger(__name__)
        self.endpoint = endpoint
        self.token = token
        self.queue = deque(maxlen=MAX_IDLE_CONNECTION)

    async def open_connection(self):
        if len(self.queue) > 0:
            return self.queue.popleft()
        wsock = await self.new_connection()
        await wsock.send(struct.pack('!B', NMP_UDP_PIPE_IP))
        return wsock

    async def close_connection(self, connection):
        if len(self.queue) >= MAX_IDLE_CONNECTION:
            await connection.close()
            return
        self.queue.append(connection)

    async def new_connection(self):
        try:
            dummy = secrets.token_hex(randint(1, 16))
            context = ssl.create_default_context()
            context.options |= ssl.OP_NO_TLSv1
            context.options |= ssl.OP_NO_TLSv1_1
            context.options |= ssl.OP_NO_TLSv1_3
            uri = f'{self.endpoint}/{self.token}/{dummy}'
            if self.endpoint.startswith('wss://'):
                return await websockets.connect(uri, ssl=context,
                                                server_hostname=self.endpoint.split('/')[2])
            else:
                return await websockets.connect(uri)
        except Exception as e:
            self.logger.exception(e)
            return None
