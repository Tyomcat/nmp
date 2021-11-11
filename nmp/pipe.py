#!/bin/env python3

import asyncio
import websockets
from nmp.log import get_logger

BUFFER_SIZE = 2 ** 16


class SocketStream:
    def __init__(self, reader, writer):
        self.logger = get_logger(__name__)
        self.reader = reader
        self.writer = writer
        self.closed = False

    async def send(self, msg):
        self.writer.write(msg)
        await self.writer.drain()

    async def recv(self):
        self.logger.debug('recv')
        msg = await self.reader.read(BUFFER_SIZE)
        self.logger.debug(msg)
        return msg

    async def close(self):
        self.closed = True
        self.writer.close()
        await self.writer.wait_closed()

    @staticmethod
    async def open_connection(host, port):
        try:
            r, w = await asyncio.open_connection(host, port)
            return SocketStream(r, w)
        except Exception as e:
            get_logger(__name__).exception(e)
            return None


class Pipe:
    def __init__(self, sock1, sock2):
        self.logger = get_logger(__name__)
        self.sock1 = sock1
        self.sock2 = sock2
        self.pipeing = False

    async def recv_and_send(self, r, w):
        while self.pipeing:
            try:
                msg = await r.recv()
                if not len(msg):
                    await self.close()
                await w.send(msg)
            except (websockets.exceptions.ConnectionClosed, ConnectionResetError) as e:
                await self.close()
                self.logger.debug(e)
            except Exception as e:
                await self.close()
                self.logger.exception(e)

    async def pipe(self):
        self.pipeing = True
        await asyncio.gather(asyncio.create_task(self.recv_and_send(self.sock1, self.sock2)),
                             asyncio.create_task(self.recv_and_send(self.sock2, self.sock1)))

    async def close(self):
        self.pipeing = False
        await self.sock1.close()
        await self.sock2.close()
