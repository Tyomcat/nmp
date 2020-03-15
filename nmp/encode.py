#!/bin/env python3

import json
import random
import pysnooper

BYTE_MAX = 256

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

    def dump(self, json_file):
        with open(json_file, 'w') as f:
            json.dump({'encode': self.encode_table, 'decode': self.decode_table}, f)

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

