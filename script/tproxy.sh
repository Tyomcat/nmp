#!/bin/bash

iptables -t mangle -N DIVERT
iptables -t mangle -A DIVERT -j MARK --set-mark 1
iptables -t mangle -A DIVERT -j ACCEPT

iptables -t mangle -A PREROUTING -p udp -m socket -j DIVERT
iptables -t mangle -A PREROUTING -p tcp -m socket -j DIVERT
iptables -t mangle -A PREROUTING -p udp -s 192.168.101.45 -j TPROXY --on-port 1111 --tproxy-mark 0x1/0x1
iptables -t mangle -A PREROUTING -p tcp -s 192.168.101.45 -j TPROXY --on-port 2222 --tproxy-mark 0x1/0x1
