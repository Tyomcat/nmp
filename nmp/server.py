#!/bin/env python3

import logging
import struct
import asyncio
import websockets

from nmp.pipe import SocketStream, Pipe

NMP_CONNECT_OK = 1


class WebSockHandler:
    def __init__(self, wsock) -> None:
        self.wsock = wsock
        self.sock = None

    async def parse_and_reply(self) -> None:
        req = await self.wsock.recv()
        print(req)
        atyp, port = struct.unpack('!BH', req[:3])
        host = req[3:].decode('ascii')
        reply = struct.pack('!B', NMP_CONNECT_OK)
        await self.wsock.send(reply)
        self.sock = await SocketStream.open_connection(host, port)

    async def handle(self):
        await self.parse_and_reply()
        pipe = Pipe(self.wsock, self.sock)
        await pipe.pipe()


class NmpServer:
    def __init__(self, port):
        self.port = port

    async def start_server(self):
        async with websockets.serve(self.dispatch, '0.0.0.0', self.port):
            await asyncio.Future()

    async def dispatch(self, wsock, path):
        handler = WebSockHandler(wsock)
        await handler.handle()


if '__main__' == __name__:
    fmt = '%(asctime)s:%(levelname)s:%(funcName)s:%(lineno)d:%(message)s'
    logging.basicConfig(level=logging.INFO, format=fmt)

    nmp = NmpServer(8888)
    asyncio.run(nmp.start_server())
