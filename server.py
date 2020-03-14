#!/bin/env python3

import socket
import logging
import threading
import select
import pysnooper
import struct

from encode import RandomEncoder

BUFFER = 4096

class Handle:
    def __init__(self, fd, addr):
        self.fd = fd
        self.addr = addr
        self.encoder = RandomEncoder()
        self.encoder.load('/tmp/nmp.json')

    # @pysnooper.snoop()
    def handle(self):
        fd = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.handle_connect(fd)
        except Exception as e:
            logging.info(e)
            self.close_fdsets((self.fd, fd))
            return

        self.enter_pip_loop(self.fd, fd)

    # conenct
    # dummy_len | dummy | atyp | port | host_len | host
    # reply
    # dummp_len | dummy | status
    # @pysnooper.snoop()
    def handle_connect(self, fd):
        bf = self.fd.recv(BUFFER)
        dummy_len = struct.unpack('!B', bf[0:1])[0]
        idx = dummy_len + 1
        atyp, port = struct.unpack('!BH', bf[idx:idx + 3])
        host = (bf[idx + 3:]).decode('ascii')
        fd.connect((host, port))

        dummy = b'barrrrrrrrrr'
        sendbf = struct.pack('!B', len(dummy)) + dummy + struct.pack('!B', 0)
        self.fd.sendall(sendbf)

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
            bf = recv_fd.recv(BUFFER)
            if bf == b'':
                self.close_fdsets((recv_fd, send_fd))
                self.shutdown()

            self.encoder.sendall(send_fd, bf)
        else:
            bf = self.encoder.recv(recv_fd, BUFFER)
            if bf == b'':
                self.close_fdsets((recv_fd, send_fd))
                self.shutdown()

            send_fd.sendall(bf)

    def close_fdsets(self, fdsets):
        try:
            for fd in fdsets:
                fd.close()
        except Exception as e:
            logging.error(e)

    def shutdown(self):
        self.close_loop = True

class NmpServer:
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

    # e = RandomEncoder()
    # e.generate()
    # e.dump('/tmp/nmp.json')

    nmp = NmpServer(1080)
    nmp.bind_and_listen(listen_max=20)
    nmp.accept_and_dispatch()
