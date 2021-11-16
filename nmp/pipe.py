#!/bin/env python3

import asyncio
import secrets
import ssl
import websockets
from random import randint
from nmp.log import get_logger

BUFFER_SIZE = 2 ** 16


class SocketStream:
    def __init__(self, reader, writer):
        self.logger = get_logger(self.__class__.__name__)
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


class WebSockStream:
    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)

    @staticmethod
    async def open(endpoint, token):
        try:
            dummy = secrets.token_hex(randint(1, 16))
            context = ssl.create_default_context()
            context.options |= ssl.OP_NO_TLSv1
            context.options |= ssl.OP_NO_TLSv1_1
            context.options |= ssl.OP_NO_TLSv1_3
            uri = f'{endpoint}/{token}/{dummy}'
            return await websockets.connect(uri, ssl=context,
                                            server_hostname=endpoint.split('/')[2])
        except Exception as e:
            get_logger(WebSockStream.__name__).exception(e)
            return None


class Pipe:
    def __init__(self, sock1, sock2):
        self.logger = get_logger(__name__)
        self.sock1 = sock1
        self.sock2 = sock2
        self.pipeing = False

    async def recv_and_send(self, r, w):
        exceptions = (RuntimeError,
                      TimeoutError,
                      ConnectionResetError,
                      websockets.exceptions.ConnectionClosedError,
                      websockets.exceptions.ConnectionClosedOK)
        while self.pipeing:
            try:
                msg = await r.recv()
                if not len(msg):
                    await self.close()
                await w.send(msg)
            except exceptions as e:
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
