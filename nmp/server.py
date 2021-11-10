#!/bin/env python3

import asyncio
import json
import os
import secrets
import string
import struct
import websockets
from random import randint, choices
from http import HTTPStatus
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

    def token_auth(self, path):
        # /token/dummy
        return self.token == path[1:].split('/')[0]

    def http_handler(self, path, headers):
        self.logger.info(path)
        if self.token_auth(path):
            return None

        self.logger.warning(
            f'auth token failed, path: {path}, headers: {headers}')
        status = [HTTPStatus.NOT_FOUND,
                  HTTPStatus.INTERNAL_SERVER_ERROR,
                  HTTPStatus.OK][randint(0, 2)]
        reply = {'data': ''.join(
            choices(string.ascii_letters + string.digits, k=32))}
        return status, {'Content-Type': 'application/json'}, json.dumps(reply).encode('utf-8')

    async def start_server(self):
        self.load_token()
        self.logger.info(f'### Token: {self.token} ###')
        async with websockets.serve(self.dispatch, self.config.host, self.config.port,
                                    process_request=self.http_handler):
            await asyncio.Future()

    async def dispatch(self, wsock, path):
        handler = WebSockHandler(wsock)
        self.logger.debug(f'connect: {path}')
        try:
            await handler.handle()
        except Exception as e:
            self.logger.warning(e)
            if not wsock.closed:
                await handler.sock.close()


if '__main__' == __name__:
    nmp = NmpServer(8888)
    asyncio.run(nmp.start_server())
