#!/bin/bash

ip rule add fwmark 1 lookup 100
ip route add local default dev lo table 100
