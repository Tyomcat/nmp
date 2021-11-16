#!/bin/env python3


import asyncio
from nmp.log import get_logger
from nmp.pipe import WebSockStream


class DatagramHandler:
    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)
        self.transport = None

    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data, addr):
        self.logger.info(addr)
        self.logger.info(data)
        self.logger.info(self.transport.get_extra_info('peername'))
        self.logger.info(self.transport.get_extra_info('sockname'))
        sock = self.transport.get_extra_info('socket')
        self.logger.info(sock)
        # self.transport.sendto(data, addr)

    async def forward_and_reply(self, data, addr):
        wsock = await WebSockStream.open('ws://127.0.0.1:8888', 'abc')
        if wsock:
            # connect ?
            await wsock.send(data)
            reply = await wsock.recv()
            self.logger.debug(reply)
            self.transport.sendto(reply, addr)


class DatagramServer:
    def __init__(self):
        pass

    def create_datagram_handler(self):
        return DatagramHandler()

    async def start_server(self):
        loop = asyncio.get_running_loop()
        self.transport, protocol = await loop.create_datagram_endpoint(self.create_datagram_handler,
                                                                       local_addr=('0.0.0.0', 8888))
        await asyncio.Future()

    def close(self):
        self.transport.close()


if '__main__' == __name__:
    server = DatagramServer()
    asyncio.run(server.start_server())
