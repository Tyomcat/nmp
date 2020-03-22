#!/bin/env python3

import struct
import random as rd
from nmp.encode import random_sequence, BYTE_MAX

DUMMY_LENGTH_MIN = 8
DUMMY_LENGTH_MAX = 128

class Dummy:
    def __init__(self):
        self.lengths = [*range(DUMMY_LENGTH_MIN, DUMMY_LENGTH_MAX)]

    def add(self):
        length = rd.choice(self.lengths)
        seq = random_sequence(length, 0, BYTE_MAX)
        return bytes([length] + seq)

    def remove(self, bf):
        dummy_len = struct.unpack('!B', bf[0:1])[0]
        return dummy_len + 1

if '__main__' == __name__:
    dummy = Dummy()
    x = dummy.add()
    print(x)
    x += b'foo'
    print(x)
    d = dummy.remove(x)
    print(d)
