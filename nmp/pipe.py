#!/bin/env python3

import asyncio

BUFFER_SIZE = 4096


class SocketStream:
    def __init__(self, reader, writer) -> None:
       self.reader = reader
       self.writer = writer

    async def send(self, msg):
        self.writer.write(msg)
        await self.writer.drain()

    async def recv(self):
        print('recv')
        msg = await self.reader.read(BUFFER_SIZE)
        print(msg)
        return msg

    async def close(self):
        self.writer.close()
        await self.writer.wait_closed()

    @staticmethod
    async def open_connection(host, port):
       r, w = await asyncio.open_connection(host, port)
       return SocketStream(r, w)


class Pipe:
    def __init__(self, sock1, sock2) -> None:
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
            except Exception as e:
                await self.close()
                print(e)

    async def pipe(self):
        self.pipeing = True
        task1 = asyncio.create_task(self.recv_and_send(self.sock1, self.sock2))
        task2 = asyncio.create_task(self.recv_and_send(self.sock2, self.sock1))
        await task2
        await task1

    async def close(self):
        self.pipeing = False
        await self.sock1.close()
        await self.sock2.close()
