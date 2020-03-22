#!/bin/env python3

import json
import random
import logging
import requests
import pysnooper
from collections import deque

BYTE_MAX = 256
ENCODER_MAX = 3

def random_sequence(n, l, r):
    seq = [*range(l, r)]
    random.shuffle(seq)
    return seq[:n]

class Encoder:
    def encode(self, bf):
        pass

    def decode(self, bf):
        pass

class RandomEncoder(Encoder):
    def load(self, json_file):
        with open(json_file) as f:
            tables = json.load(f)

        self.encode_table = tables['encode']
        self.decode_table = tables['decode']

    def loads(self, s):
        tables = json.loads(s)
        self.encode_table = tables['encode']
        self.decode_table = tables['decode']

    def dump(self, json_file):
        with open(json_file, 'w') as f:
            json.dump({'encode': self.encode_table, 'decode': self.decode_table}, f)

    def dumps(self):
        return json.dumps({'encode': self.encode_table, 'decode': self.decode_table})

    def generate(self):
        self.encode_table = random_sequence(BYTE_MAX, 0, BYTE_MAX)
        self.decode_table = [*range(0, BYTE_MAX)]
        for i, ch in enumerate(self.encode_table):
            self.decode_table[ch] = i

    # @pysnooper.snoop()
    def encode(self, bf):
        arr = bytearray(bf)
        for i in range(0, len(arr)):
            arr[i] = self.encode_table[arr[i]]

        return bytes(arr)

    # @pysnooper.snoop()
    def decode(self, bf):
        arr = bytearray(bf)
        for i in range(0, len(arr)):
            arr[i] = self.decode_table[arr[i]]

        return bytes(arr)

    # @pysnooper.snoop()
    def recv(self, fd, size):
        return self.decode(fd.recv(size))

    def send(self, fd, bf):
        return fd.send(self.encode(bf))

    # @pysnooper.snoop()
    def sendall(self, fd, bf):
        fd.sendall(self.encode(bf))

class EncoderPool:
    def __init__(self, prefix):
        self.prefix = prefix

    def generate(self, count=ENCODER_MAX, lazy=False):
        self.tokens = deque(range(0, count))
        self.encoders = {}
        if not lazy:
            for token in self.tokens:
                r = RandomEncoder()
                r.generate()
                self.encoders[token] = r

    def dynamic_alloc(self, n):
        encoders = {}
        for i in range(0, n):
            if not len(self.tokens):
                return encoders
            r = RandomEncoder()
            r.generate()
            token = self.tokens.popleft()
            encoders[token] = r

        return encoders

    def alloc_from_apiserver(self, n):
        self.encoders = {}
        self.tokens = deque()
        uri = '{}/connect?uuid={}&n={}'.format(self.prefix, 'foo', n)
        r = requests.post(uri)
        if 200 != r.status_code:
            logging.error('fail to alloc, status_code={}'.format(r.status_code))
            return
        data = r.json()['data']
        if not data['status']:
            logging.error(data)
            return

        encoders = json.loads(data['data'])
        for token, s in encoders.items():
            r = RandomEncoder()
            r.loads(s)
            self.tokens.append(token)
            self.encoders[token] = r

    def dealloc_to_apiserver(self):
        uri = '{}/disconnect?uuid={}&tokens={}'.format(self.prefix, 'foo',
                                                       json.dumps([*self.tokens]))
        r = requests.delete(uri)
        if 200 != r.status_code:
            logging.error('fail to alloc, status_code={}'.format(r.status_code))
            return

    def alloc(self, n):
        encoders = {}
        for i in range(0, n):
            token = self.tokens.popleft()
            if not len(self.tokens):
                return encoders
            encoders[token] = self.encoders[token]
        return encoders

    def dealloc(self, seq):
        for token in seq:
            self.tokens.append(token)


if '__main__' == __name__:
    encoder = RandomEncoder()
    encoder.generate()
    bf = b'abc'
    message = encoder.encode(bf)
    print(message)
    print(encoder.decode(message))

    f = '/tmp/nmp.json'
    encoder.dump(f)
    e = RandomEncoder()
    e.load(f)
    print(e.decode(message))
    print(e.encode(bf))
    print(e.encode_table)
    print(e.decode_table)

    pool = EncoderPool(prefix='127.0.0.1:3306/v1')
    pool.generate()
    print(pool.tokens)
    print(pool.encoders)
    x = pool.alloc(2)
    print(x)
    print(pool.tokens)
    print(pool.encoders)
    pool.dealloc([0, 1])
    print(pool.tokens)
    print(pool.encoders)
    print(pool.encoders[2].dumps())
    x = pool.dynamic_alloc(1)
    print(x, x[2].dumps())
    print(pool.tokens)
    print(pool.encoders)

