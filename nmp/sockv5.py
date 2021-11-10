#!/bin/env python3

import asyncio
import secrets
import socket
import ssl
import struct
import websockets
from random import randint
from nmp.log import get_logger
from nmp.pipe import Pipe, SocketStream
from nmp.proto import *


class SockHandler:
    def __init__(self, config, sock):
        self.logger = get_logger(__name__)
        self.token = config.token
        self.endpoint = config.endpoint
        self.sock = sock
        self.pipeing = False

    async def handle(self):
        r = await self.parse_ver_and_reply()
        if not r:
            await self.sock.close()
            return

        wsock = await self.connect_and_reply()
        if not wsock:
            await self.sock.close()
            return

        pipe = Pipe(self.sock, wsock)
        await pipe.pipe()

    async def parse_ver_and_reply(self):
        req = await self.sock.recv()
        ver, nmethods = struct.unpack('!BB', req[0:2])
        if SOCK_V5 != ver:
            return False

        for method in [ord(req[2 + i: 3 + i]) for i in range(nmethods)]:
            if method in IMPLEMENTED_METHODS:
                await self.sock.send(struct.pack('!BB', SOCK_V5, method))
                return True

        return False

    async def connect_and_reply(self):
        req = await self.sock.recv()
        ver, cmd, _, atyp = struct.unpack('!BBBB', req[0:4])
        if CMD_CONNECT != cmd:
            return None

        if ATYP_IP_V4 == atyp:
            addr = socket.inet_ntoa(req[4:8]).encode('ascii')
            port = struct.unpack('!H', req[8:10])[0]
        elif ATYP_DOMAINNAME == atyp:
            addr_len = ord(req[4:5])
            addr = req[5:(5 + addr_len)]
            port = struct.unpack('!H', req[5 + addr_len: 7 + addr_len])[0]
        else:
            return None

        self.logger.debug(f'connect to {addr}')
        # need fix to right host ?
        nhost = struct.unpack('!I', socket.inet_aton('127.0.0.1'))[0]
        wsock = await self.open_connection(atyp, addr, port)
        if wsock:
            reply = struct.pack("!BBBBIH", SOCK_V5, 0, 0, 1, nhost, port)
            await self.sock.send(reply)
            return wsock
        else:
            reply = struct.pack("!BBBBIH", SOCK_V5, 5, 1, 1, nhost, port)
            await self.sock.send(reply)
            return None

    async def open_connection(self, addr_type, target_host, target_port):
        req = struct.pack("!BH", addr_type, target_port) + target_host
        self.logger.debug(req)
        try:
            dummy = secrets.token_hex(randint(1, 16))
            context = ssl.create_default_context()
            context.options |= ssl.OP_NO_TLSv1
            context.options |= ssl.OP_NO_TLSv1_1
            context.options |= ssl.OP_NO_TLSv1_3
            uri = f'{self.endpoint}/{self.token}/{dummy}'
            wsock = await websockets.connect(uri, ssl=context,
                                             server_hostname=self.endpoint.split('/')[2])
        except Exception as e:
            self.logger.exception(e)
            return None

        await wsock.send(req)
        reply = await wsock.recv()
        code = struct.unpack('!B', reply[:1])[0]
        if code != NMP_CONNECT_OK:
            self.logger.warning(f'connect refused, error code {code}')
            await wsock.close()
            return None

        return wsock


class SockV5Server:
    def __init__(self, config):
        self.logger = get_logger(__name__)
        self.config = config

    async def start_server(self):
        server = await asyncio.start_server(
            self.dispatch, self.config.host, self.config.port)
        async with server:
            await server.serve_forever()

    async def dispatch(self, r, w):
        handler = SockHandler(self.config, SocketStream(r, w))
        try:
            await handler.handle()
        except Exception as e:
            self.logger.warning(e)
            if not handler.sock.closed:
                await handler.sock.close()


if '__main__' == __name__:
    sockv5 = SockV5Server(1234)
    asyncio.run(sockv5.start_server())
