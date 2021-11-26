#!/bin/env python3

import asyncio
import socket
import struct
from nmp.connection import ConnectionPool
from nmp.log import get_logger
from nmp.pipe import Pipe, SocketStream
from nmp.proto import ATYP_DOMAINNAME, ATYP_IP_V4, CMD_CONNECT, IMPLEMENTED_METHODS, NMP_CONNECT_OK, SOCK_V5


class SockHandler:
    def __init__(self, sock, pool: ConnectionPool):
        self.logger = get_logger(__name__)
        self.sock = sock
        self.pool = pool
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
            addr = socket.inet_ntoa(req[4:8]).encode()
            port = struct.unpack('!H', req[8:10])[0]
        elif ATYP_DOMAINNAME == atyp:
            addr_len = ord(req[4:5])
            addr = req[5:5 + addr_len]
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
        req = bytearray(struct.pack("!BH", addr_type, target_port))
        req.extend(target_host)
        self.logger.debug(req)
        wsock = await self.pool.new_connection()
        if not wsock:
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
        self.pool = ConnectionPool(config.endpoint, config.token)

    async def start_server(self):
        server = await asyncio.start_server(
            self.dispatch, self.config.host, self.config.port)
        async with server:
            await server.serve_forever()

    async def dispatch(self, r, w):
        handler = SockHandler(SocketStream(r, w), self.pool)
        try:
            await handler.handle()
        except Exception as e:
            self.logger.warning(e)
            if not handler.sock.closed:
                await handler.sock.close()


if '__main__' == __name__:
    sockv5 = SockV5Server(1234)
    asyncio.run(sockv5.start_server())
