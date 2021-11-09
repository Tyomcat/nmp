#!/bin/env python3

import asyncio
import os
import secrets
import struct
import websockets
from random import randint
from nmp.log import get_logger
from nmp.pipe import SocketStream, Pipe
from nmp.proto import *


class WebSockHandler:
    def __init__(self, wsock):
        self.logger = get_logger(__name__)
        self.wsock = wsock

    async def parse_and_reply(self):
        req = await self.wsock.recv()
        self.logger.debug(req)
        atyp, port = struct.unpack('!BH', req[:3])
        host = req[3:].decode('ascii')
        return await SocketStream.open_connection(host, port)

    async def handle(self):
        sock = await self.parse_and_reply()
        if not sock:
            reply = struct.pack('!B', NMP_CONNECT_FAILED)
            await self.wsock.send(reply)
            await self.wsock.close()
            return

        reply = struct.pack('!B', NMP_CONNECT_OK)
        await self.wsock.send(reply)
        pipe = Pipe(self.wsock, sock)
        await pipe.pipe()


class NmpServer:
    def __init__(self, config):
        self.logger = get_logger(__name__)
        self.config = config

    def load_token(self):
        if os.path.exists(self.config.conf):
            with open(self.config.conf, 'r') as f:
                self.token = f.read()
        else:
            self.token = secrets.token_hex(randint(8, 16))
            with open(self.config.conf, 'w') as f:
                f.write(self.token)

    async def start_server(self):
        self.load_token()
        self.logger.info(f'### Token: {self.token} ###')
        async with websockets.serve(self.dispatch, self.config.host, self.config.port):
            await asyncio.Future()

    async def dispatch(self, wsock, path):
        handler = WebSockHandler(wsock)
        self.logger.debug(f'connect: {path}')
        if not self.token_auth(path):
            self.logger.warning(f'auth token failed, path: {path}')
            await wsock.close()
            return

        try:
            await handler.handle()
        except Exception as e:
            self.logger.warning(e)
            if not wsock.closed:
                await handler.sock.close()

    def token_auth(self, path):
        # /token/dummy
        return self.token == path[1:].split('/')[0]


if '__main__' == __name__:
    nmp = NmpServer(8888)
    asyncio.run(nmp.start_server())
