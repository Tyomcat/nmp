#!/bin/env python3

import asyncio
import argparse
import sys
import os
from pathlib import Path
from nmp.log import get_logger
from nmp.server import NmpServer
from nmp.sockv5 import SockV5Server

logger = get_logger(__name__)


class Config:
    def __init__(self):
        self.server = None
        self.host = '127.0.0.1'
        self.port = 8888
        # for sockv5
        self.endpoint = None
        self.token = None
        # for nmp server
        self.conf = os.path.join(Path.home(), '.NMP_TOKEN')

    def from_args(self):
        parser = argparse.ArgumentParser()
        parser.add_argument('--server', dest='server',
                            help='server type: nmp/sockv5')
        parser.add_argument('--host', dest='host',
                            help='bind host (default: 127.0.0.1)')
        parser.add_argument('--port', dest='port',
                            help='bind port (default: 8888)')
        parser.add_argument('--endpoint', dest='endpoint',
                            help='nmp server endpoint (wss://example.com)')
        parser.add_argument('--token', dest='token', help='nmp server token')
        args = parser.parse_args()
        if args.server:
            self.server = args.server
        if args.host:
            self.host = args.host
        if args.port:
            self.port = args.port
        if args.endpoint:
            self.endpoint = args.endpoint
        if args.token:
            self.token = args.token

        if not self.validate():
            parser.print_help()
            sys.exit(-1)

    def validate(self):
        if not self.server:
            return False
        if self.server == 'sockv5':
            return self.endpoint and self.token
        return True


def start_nmp_server(config):
    logger.info(f'start nmp server: ({config.host}:{config.port})')
    nmp = NmpServer(config)
    asyncio.run(nmp.start_server())


def start_sockv5_server(config):
    logger.info(f'start sockv5 server: ({config.host}:{config.port})')
    sockv5 = SockV5Server(config)
    asyncio.run(sockv5.start_server())


def main():
    config = Config()
    config.from_args()
    if config.server == 'sockv5':
        start_sockv5_server(config)
    else:
        start_nmp_server(config)


if '__main__' == __name__:
    main()
