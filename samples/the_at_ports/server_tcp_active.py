#!/usr/bin/env python

import socket
import time

HOST = '192.168.2.1'   # Standard loopback interface address (localhost)
PORT = 8000            # Port to listen on (non-privileged ports are > 1023)

cfg_pkt_sz = 1400
cfg_pkt_num = 1250
cfg_pre_send = True

cfg_send_small = True  # send small packet. expect to receive big.

if cfg_send_small:
    cfg_pkt_sz = 4

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
if s is not None:
    s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((HOST, PORT))
    s.listen(1)
    conn, addr = s.accept()
    if conn is not None:
        conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        print('Connected by', addr)
        logs, dsz, lasttm, firsttm = [], 0, 0, 0
        data_out = b'k' * cfg_pkt_sz
        if cfg_pre_send: # send one more block first before receiving
            conn.send(data_out)
        while True:
            conn.send(data_out)
            data = conn.recv(2048)
            tm = time.time()
            if not data:
                break
            tdif = 0
            if lasttm != 0:
                tdif = tm - lasttm
            else:
                firsttm = tm
            lasttm = tm
            dsz += len(data)
            #conn.sendall(data)
            lmsg = "  dsz:%d:%.3f  " % (dsz, tdif)
            #print(lmsg)
            ##conn.send(lmsg)

            logs.append(lmsg)
            if len(logs) > cfg_pkt_num:
                break
        conn.close()
        print(logs)
        print(" total time %.3f" % (lasttm - firsttm))
    s.close()



