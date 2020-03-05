#!/bin/env python3

import socket
import logging
import threading
import select
import pysnooper
import struct

from encode import RandomEncoder

BUFFER = 4096
SOCK_V5 = 5
RSV = 0
ATYP_IP_V4 = 1
ATYP_DOMAINNAME = 3
CMD_CONNECT = 1
IMPLEMENTED_METHODS = (2, 0)

class Handle:
    def __init__(self, fd, addr):
        self.fd = fd
        self.addr = addr
        self.encoder = RandomEncoder()
        self.encoder.load('/tmp/nmp.json')

    # @pysnooper.snoop()
    def handle(self):
        if not self.handle_version_and_auth():
            self.close_fdsets((self.fd,))
            return False

        fd = self.handle_connect()
        if not fd:
            self.close_fdsets((self.fd,))
            return False

        self.enter_pip_loop(self.fd, fd)

    def handle_version_and_auth(self):
        bf = self.encoder.recv(self.fd, BUFFER)
        ver, nmethods = struct.unpack('!BB', bf[0:2])
        if SOCK_V5 != ver:
            return False

        for method in [ord(bf[2 + i : 3 + i]) for i in range(nmethods)]:
            if method in IMPLEMENTED_METHODS:
                self.encoder.sendall(self.fd, struct.pack('!BB', SOCK_V5, method))
                return True

        return False

    def handle_connect(self):
        bf = self.encoder.recv(self.fd, BUFFER)
        ver, cmd, _, atyp = struct.unpack('!BBBB', bf[0:4])
        if CMD_CONNECT != cmd:
            return None

        if ATYP_IP_V4 == atyp:
            addr = socket.inet_ntoa(bf[4:8])
            port = struct.unpack('!H', bf[8:10])[0]
            logging.info('connect to {}'.format(addr))
        elif ATYP_DOMAINNAME == atyp:
            addr_len = ord(bf[4:5])
            addr = socket.gethostbyname(bf[5:(5 + addr_len)])
            port = struct.unpack('!H', bf[5 + addr_len: 7 + addr_len])[0]
            logging.info('connect to {}'.format(bf[5:(5 + addr_len)]))
            logging.info('host to addr = {}'.format(addr))
        else:
            return None

        addr_num = struct.unpack('!I', socket.inet_aton(addr))[0]
        fd = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            fd.connect((addr, port))
            reply = struct.pack("!BBBBIH", SOCK_V5, 0, 0, 1, addr_num, port)
        except Exception as e:
            reply = struct.pack("!BBBBIH", SOCK_V5, 5, 1, 1, addr_num, port)
            logging.info(e)
            fd.close()
            fd = None

        self.encoder.sendall(self.fd, reply)
        return fd

    def handle_noblock(self):
        thread = threading.Thread(target=self.handle, args=())
        thread.daemon = True
        thread.start()

    def enter_pip_loop(self, fd_a, fd_b):
        self.close_loop = False
        fdsets = [fd_a, fd_b]
        while not self.close_loop:
            try:
                in_sets, out_sets, ex_sets = select.select(fdsets, [], [])
                for fd in in_sets:
                    if fd == fd_a:
                        self.recv_and_send(fd_a, fd_b)
                    elif fd == fd_b:
                        self.recv_and_send(fd_b, fd_a)
            except Exception as e:
                self.close_fdsets((fd_a, fd_b))
                self.shutdown()

    def recv_and_send(self, recv_fd, send_fd):
        # recv() is a block I/O, returns '' when remote has been closed.
        if recv_fd == self.fd:
            bf = self.encoder.recv(recv_fd, BUFFER)
            if bf == b'':
                self.close_fdsets((recv_fd, send_fd))
                self.shutdown()

            send_fd.sendall(bf)
        else:
            bf = recv_fd.recv(BUFFER)
            if bf == b'':
                self.close_fdsets((recv_fd, send_fd))
                self.shutdown()

            self.encoder.sendall(send_fd, bf)

    def close_fdsets(self, fdsets):
        try:
            for fd in fdsets:
                fd.close()
        except Exception as e:
            logging.error(e)

    def shutdown(self):
        self.close_loop = True

class SockV5Server:
    def __init__(self, port):
        self.port = port
        self.fd = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def __del__(self):
        self.fd.close()

    def bind_and_listen(self, listen_max):
        self.fd.bind(('0.0.0.0', self.port))
        self.fd.listen(listen_max)

    def accept_and_dispatch(self):
        self.shutdown = False
        while not self.shutdown:
            fd, addr = self.fd.accept();
            handle = Handle(fd, addr)
            handle.handle_noblock()

    def shutdown(self):
        self.shutdown = True

if '__main__' == __name__:
    fmt = '%(asctime)s:%(levelname)s:%(funcName)s:%(lineno)d:%(message)s'
    logging.basicConfig(level=logging.INFO, format=fmt)

    e = RandomEncoder()
    e.generate()
    e.dump('/tmp/nmp.json')

    sockv5 = SockV5Server(1080)
    sockv5.bind_and_listen(listen_max=20)
    sockv5.accept_and_dispatch()
