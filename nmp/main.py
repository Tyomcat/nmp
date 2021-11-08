#!/bin/env python3

import sys
import logging
import argparse

from nmp.server import NmpServer
from nmp.sockv5 import SockV5Server


def server_handle(args):
    nmp = NmpServer(3389)
    logging.info('start nmp server...')


def socks_handle(args):
    logging.info('start sockv5 server...')
    sockv5 = SockV5Server(1234)


def main():
    fmt = '%(asctime)s:%(levelname)s:%(funcName)s:%(lineno)d:%(message)s'
    logging.basicConfig(level=logging.INFO, format=fmt)

    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=('server', 'socks'))
    args = parser.parse_args()

    if 'server' == args.action:
        server_handle(args)
    elif 'socks' == args.action:
        socks_handle(args)
    else:
        args.print_help()


if '__main__' == __name__:
    main()
