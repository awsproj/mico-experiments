#!/usr/bin/env python

import socket
import time

HOST = '192.168.2.1'   # Standard loopback interface address (localhost)
PORT = 8000            # Port to listen on (non-privileged ports are > 1023)

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
if s is not None:
    s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    s.bind((HOST, PORT))
    s.listen(1)
    conn, addr = s.accept()
    if conn is not None:
        conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        print('Connected by', addr)
        logs, dsz, lasttm, firsttm = [], 0, 0, 0
        while True:
            data = conn.recv(1024)
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
            conn.send(lmsg)
            logs.append(lmsg)
        conn.close()
        print(logs)
        print(" total time %.3f" % (lasttm - firsttm))
    s.close()



