#!/usr/bin/env python

import socket
import time

HOST = '192.168.2.1'  # Standard loopback interface address (localhost)
PORT = 8000            # Port to listen on (non-privileged ports are > 1023)

_cfg_pktsz = 1024 # 1440

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
if s is not None:
    s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((HOST, PORT))
    s.listen(1)
    conn, addr = s.accept()
    if conn is not None:
        conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        conn.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        print('Connected by', addr)
        logs, dsz, lasttm, firsttm = [], 0, 0, 0
        while True:
            data = conn.recv(_cfg_pktsz)
            tm = time.time()
            if not data:
                break
            tdif = 0
            if lasttm != 0:
                tdif = tm - lasttm
            else:
                firsttm = tm
            lasttm = tm
            dlen = len(data)
            dsz += dlen
            seqn = 0
            if dlen >= 8:
                try:
                    seqn = int(data[0:4].decode())
                except:
                    pass
            #conn.sendall(data)
            lmsg = "  dsz:%04d:%d:%d:%.3f  " % (seqn, dlen, dsz, tdif)
            print(lmsg)
            conn.send(lmsg + "\r\n")
            logs.append(lmsg)
        conn.close()
        print(logs)
        print(" total time %.3f" % (lasttm - firsttm))
    s.close()



