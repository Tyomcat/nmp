#!/bin/env python3

import asyncio
import socket
import struct
from nmp.connection import ConnectionPool
from nmp.log import get_logger
from nmp.proto import NMP_CONNECT_OK

MAX_MSG_BUF_SIZE = 2 ** 16
MAX_IDLE_CONNECTION = 2 ** 10


class DatagramHandler:
    def __init__(self, sock, pool: ConnectionPool):
        self.logger = get_logger(self.__class__.__name__)
        self.sock = sock
        self.pool = pool

    @staticmethod
    def new(sock, pool: ConnectionPool):
        return DatagramHandler(sock, pool)

    async def received(self, data, from_addr, to_addr):
        self.logger.debug(from_addr)
        self.logger.debug(to_addr)
        self.logger.debug(data)
        reply = await self.forward_and_recv(data, to_addr)
        if reply:
            await self.reply(reply, to_addr, from_addr)

    async def forward_and_recv(self, data, addr):
        wsock = await self.pool.open_connection()
        if not wsock:
            return
        self.logger.debug(addr)
        msg = bytearray(socket.inet_aton(addr[0]))
        msg.extend(struct.pack('!H', addr[1]))
        msg.extend(data)
        self.logger.debug(msg)
        await wsock.send(msg)
        reply = await wsock.recv()
        await self.pool.close_connection(wsock)
        statu = struct.unpack('!B', reply[:1])[0]
        if statu != NMP_CONNECT_OK:
            self.logger.warning(f'forward message failed, {addr}')
            return None

        return reply[1:]

    async def reply(self, data, from_addr, to_addr):
        # sock = socket.socket(socket.family, socket.SOCK_DGRAM)
        # sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # sock.setsockopt(socket.SOL_IP, IP_TRANSPARENT, 1)
        # sock.bind(from_addr)
        # sock.sendto(data, to_addr)
        # sock.close()
        self.sock.sendto(data, to_addr)


class TransparentServer:
    def __init__(self):
        self.datagram_sock = None
        self.pool = ConnectionPool(
            'ws://127.0.0.1:8888', '44f25ba0957c61def8b1')

    def datagram_handler(self):
        data, anc, flags, from_addr = self.datagram_sock.recvmsg(
            MAX_MSG_BUF_SIZE)
        asyncio.create_task(DatagramHandler
                            .new(self.datagram_sock, self.pool)
                            .received(data, from_addr, ('8.8.8.8', 53)))

    async def start_datagram_server(self):
        self.datagram_sock = self.new_datagram_endpoint()
        loop = asyncio.get_running_loop()
        loop.add_reader(self.datagram_sock, self.datagram_handler)
        await asyncio.Future()

    def new_datagram_endpoint(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind(('0.0.0.0', 8888))
        return sock

    def close(self):
        if self.datagram_sock:
            self.datagram_sock.close()


if '__main__' == __name__:
    server = TransparentServer()
    asyncio.run(server.start_datagram_server())
