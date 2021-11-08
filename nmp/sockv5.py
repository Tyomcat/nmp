#!/bin/env python3

import asyncio
import socket
import logging
import struct
import websockets
from nmp.pipe import Pipe, SocketStream
from nmp.server import NMP_CONNECT_OK

SOCK_V5 = 5
RSV = 0
ATYP_IP_V4 = 1
ATYP_DOMAINNAME = 3
CMD_CONNECT = 1
IMPLEMENTED_METHODS = (2, 0)


class SockHandler:
    def __init__(self, sock):
        self.host = '127.0.0.1'
        self.sock = sock
        self.wsock = None
        self.pipeing = False

    async def handle(self):
        r = await self.parse_ver_and_reply()
        if not r:
            await self.sock.close()
            return

        r = await self.connect_and_reply()
        if not r:
            await self.sock.close()
            await self.wsock.close()
            return

        pipe = Pipe(self.sock, self.wsock)
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
            return False

        if ATYP_IP_V4 == atyp:
            addr = socket.inet_ntoa(req[4:8]).encode('ascii')
            port = struct.unpack('!H', req[8:10])[0]
        elif ATYP_DOMAINNAME == atyp:
            addr_len = ord(req[4:5])
            addr = req[5:(5 + addr_len)]
            port = struct.unpack('!H', req[5 + addr_len: 7 + addr_len])[0]
        else:
            return False

        logging.info(f'connect to {addr}')
        nhost = struct.unpack('!I', socket.inet_aton(self.host))[0]
        r = await self.open_connection(atyp, addr, port)
        if r:
            reply = struct.pack("!BBBBIH", SOCK_V5, 0, 0, 1, nhost, port)
            await self.sock.send(reply)
            return True
        else:
            reply = struct.pack("!BBBBIH", SOCK_V5, 5, 1, 1, nhost, port)
            await self.sock.send(reply)
            return False

    async def open_connection(self, addr_type, target_host, target_port):
        req = struct.pack("!BH", addr_type, target_port) + target_host
        logging.info(req)
        self.wsock = await websockets.connect('ws://127.0.0.1:8888/nmp')
        await self.wsock.send(req)
        reply = await self.wsock.recv()
        code = struct.unpack('!B', reply[:1])[0]
        if code != NMP_CONNECT_OK:
            logging.error(f'connect nmp server failed, error code {code}')
        return code == NMP_CONNECT_OK


class SockV5Server:
    def __init__(self, port):
        self.port = port

    async def start_server(self):
        server = await asyncio.start_server(
            self.dispatch, '127.0.0.1', self.port)
        async with server:
            await server.serve_forever()

    async def dispatch(self, r, w):
        handler = SockHandler(SocketStream(r, w))
        await handler.handle()


if '__main__' == __name__:
    fmt = '%(asctime)s:%(levelname)s:%(funcName)s:%(lineno)d:%(message)s'
    logging.basicConfig(level=logging.INFO, format=fmt)

    sockv5 = SockV5Server(1234)
    asyncio.run(sockv5.start_server())
