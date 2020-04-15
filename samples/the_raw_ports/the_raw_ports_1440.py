#!/usr/bin/env python
# the_raw_ports.py

import sys

class Logger(object):
    def __init__(self):
        self.terminal = sys.stdout
        self.log = open("logfile.log", "a")

    def write(self, message):
        self.terminal.write(message)
        self.log.write(message)
        self.terminal.flush()
        self.log.flush()

    def flush(self):
        #this flush method is needed for python 3 compatibility.
        #this handles the flush command by doing nothing.
        #you might want to specify some extra behavior here.
        pass

sys.stdout = Logger()

import pprint
pp = pprint.PrettyPrinter(indent=4)


import time
import libs.conf_read_ports as ports


_cfg_pyser_timeout = 0.3  # 0.05 # 0.3
_cfg_uart_baudrate1 = 921600 # 115200 default
_cfg_uart_baudrate2 = 921600 # could use 921600
_cfg_uart_baudrate = _cfg_uart_baudrate1 # init to default

_cfg_hw_ctsrts = True # True to set rts line and check cts line
_var_hw_cts_count_high = 0
_var_hw_cts_count_low = 0
_cfg_hw_debug_cts = False

_cfg_pktsz = 1024 # 1440 # 1024 is the buffer size of emw110
_cfg_hdr_slack = True # split packet to header plus body


cfg_use_pyserial = True
pyser_console = None

if cfg_use_pyserial:
    pyser_dir = "libs/pyserial"
    import os
    if os.path.isdir(pyser_dir):
        sys.path.insert(0, pyser_dir)
    else:
        cfg_use_pyserial = False
        raise Exception("No pyser_dir as a dir")
    if cfg_use_pyserial:
        try:
            import serial as pyser_pkg
        except:
            cfg_use_pyserial = False
            raise Exception("Not able to import pyser_pkg")

def pyser_open(baud_rate=None):
    port_console = ports.get_conf_console()
    try:
        global _cfg_uart_baudrate
        baud = _cfg_uart_baudrate
        if baud_rate is not None:
            baud = baud_rate
        # pyser = pyser_pkg.Serial('COM11', 115200, timeout=1)
        #pyser_console = pyser_pkg.Serial('/dev/ttyS10', 115200, timeout=0.3)
        global pyser_console
        pyser_console = pyser_pkg.Serial(port_console, baud,
                                         timeout=_cfg_pyser_timeout)
        _cfg_uart_baudrate = baud
        print("Opened UART at baud %d " % baud)
    except:
        global cfg_use_pyserial
        cfg_use_pyserial = False
        raise Exception("Not able to open port for console : %s" % str(port_console))

def pyser_close_all():
    global pyser_console
    if cfg_use_pyserial and pyser_console and pyser_console.is_open:
        pyser_console.close()
        pyser_console = None

def _pyser_ser_cmd(ser=None, cmd="", cmd_timeout_inact=0, do_send_data=False):
    if len(cmd) == 0:
        cmd = "\r"
    if cfg_use_pyserial and ser and ser.is_open:

        if _cfg_hw_ctsrts:
            ser.setRTS(True)
            global _var_hw_cts_count_high, _var_hw_cts_count_low
            cts_val = ser.getCTS()
            if cts_val:
                _var_hw_cts_count_high += 1
            else:
                _var_hw_cts_count_low += 1
                for n in range(10):
                    if not _cfg_hw_debug_cts:
                        break
                    time.sleep(0.01)
                    cts_val = ser.getCTS()
                    if cts_val:
                        _var_hw_cts_count_high += 1
                        break

        if not _cfg_hdr_slack:
            ser.write(cmd.encode())
        elif len(cmd) > 8:
            ser.write(cmd[:8].encode())
            time.sleep(0.002) # 2ms 
            ser.write(cmd[8:].encode())

        retv = []
        tm01 = time.time()
        lastactive = tm01
        def readln(ser, partitial=""):
            aggr = partitial
            for x in range(10):
                v = ser.readline()
                aggr = aggr + v
                if len(aggr) > 0 and aggr.endswith("\r\n"):
                    break
            return aggr
        timeout_val = _cfg_pyser_timeout
        if do_send_data:
            timeout_val *= 3 # so that it won't be hit. use _inact.
        max_loop = 1000
        for i in range(max_loop):
            tm02 = time.time()
            val = ser.readline()
            tm03 = time.time()
            #if len(val) >= 0:
            retv.append([tm02-tm01, tm03-tm02, val])
            tcost = tm03-tm02
            if tcost >= (timeout_val * 0.98):
                if len(val) <= 0:
                    retv.append([-1,-1,"timeout on an empty line".encode()])
                    break # timeout on an empty line
                else:
                    dec_ok = False
                    try:
                        dec_val = val.decode()
                        dec_ok = True
                    except UnicodeDecodeError:
                        dec_val = "<dec fail>"
                    if not dec_val.endswith("\r\n"):
                        if dec_ok:
                            lmsg = "timeout on a prompt line. len %d" % len(val)
                        else:
                            lmsg = "timeout on a prompt encoded line. len %d" % len(val)
                        retv.append([-1, -1, lmsg.encode()])
                        break # timeout on an prompt line
            if cmd_timeout_inact > 0:
                if tm03-lastactive > cmd_timeout_inact:
                    retv.append([-1,-1,"timeout on idle".encode()])
                    break
            if do_send_data:
                if val.decode().find('dsz:') >= 0:
                    retv.append([-1,-1,"loop escape got OK".encode()])
                    break
                if val.decode().startswith('ERROR'):
                    retv.append([-1, -1, "loop escape got ERROR".encode()])
                    break
            if len(val) > 0:
                lastactive = tm03
            if i == max_loop - 1:
                retv.append([-1, -1, ("loop ends at max_loop %d" % max_loop).encode()])

        if _cfg_hw_ctsrts:
            if ser.getCTS():
                _var_hw_cts_count_high += 1
            else:
                _var_hw_cts_count_low += 1
                for n in range(10):
                    if not _cfg_hw_debug_cts:
                        break
                    time.sleep(0.01)
                    cts_val = ser.getCTS()
                    if cts_val:
                        _var_hw_cts_count_high += 1
                        break

        return retv
    return None

def pyser_console_cmd(cmd=""):
    return _pyser_ser_cmd(ser=pyser_console, cmd=cmd)

def pyser_console_cmd_data(cmd=""):
    return _pyser_ser_cmd(ser=pyser_console, cmd=cmd,
                          cmd_timeout_inact=_cfg_pyser_timeout*3,
                          #cmd_timeout_inact=0.050,
                          do_send_data=True)

def print_lines(lines, prefix=0):
    for x in lines:
        import re
        try:
            x2_dec = x[2].decode()
        except:
            x2_dec = "Uunable to decode" # todo: fix this
        s = re.sub(r'\r', ' ', x2_dec)
        u = re.sub(r'\n', ' ', s)
        print("%s    %8.3f %6.3f \t%s" % (prefix*" ", x[0], x[1], u))

def pyser_open_dual():
    pyser_open()
    cmd_ok = False
    try:
        pyser_console_cmd("\r")
        retv_cmd = pyser_console_cmd("\r")
        if type(retv_cmd) is list and len(retv_cmd) >= 2:
            if retv_cmd[0][2].decode().find('dsz:') >= 0:
                cmd_ok = True
    except:
        pass
    if not cmd_ok:
        pyser_close_all()
        pyser_open(baud_rate=_cfg_uart_baudrate2)
        try:
            pyser_console_cmd("\r")
            retv_cmd = pyser_console_cmd("\r")
            if type(retv_cmd) is list and len(retv_cmd) >= 2:
                if retv_cmd[0][2].decode().find('dsz:') >= 0:
                    cmd_ok = True
            if not cmd_ok:
                print("Error baud2: ")
                print_lines(retv_cmd)
        except BaseException as e:
            print("Exception baud2 %s" % str(e))
        except:
            print("Exception baud2 %s" % str("Unknown"))
    if not cmd_ok:
        #raise Exception("Not able to open console for a command")
        pass

if cfg_use_pyserial:
    pyser_open_dual()

def test_ports_uart921600():
    print("")
    print("console command:")
    print_lines(pyser_console_cmd("\r"))

def test_ports_init():
    print("")
    print("console command:")
    print_lines(pyser_console_cmd("\r"))

    pyser_close_all()

def test_ports_packet():

    stats = []
    stats_ok, stats_err, stats_unknown = 0, 0, 0

    print("")
    print("console command:")
    print_lines(pyser_console_cmd("0004a123"))

    time.sleep(0.6)

    print("")
    print("console command: send data")
    while True: # scope
        pktsz = _cfg_pktsz # 1440 # 1024 is the buffer size of emw110
        batch1, batch2 = 2, 6 # emw110 ok: 2,6 with cost 422ms.
        send_data = 'j' * (pktsz - 8) # 8 for header
        tm00 = time.time()
        retv_lines = []
        cost_send, cost_recv = 0, 0

        dsz = 0
        for k in range(batch1 * batch2):
            tm11 = time.time()
            retv_cmd = pyser_console_cmd_data("%04d%04d" % (k + 1, pktsz) + send_data)
            dsz += pktsz
            retv_lines.extend(retv_cmd)
            for x in retv_cmd:
                if x[0] == -1:
                    x_str = x[2].decode()
                    if x_str.startswith("loop escape got OK"):
                        stats_ok += 1
                    elif x_str.startswith("loop escape got ERROR"):
                        stats_err += 1
                    else:
                        stats_unknown += 1
            tm12 = time.time()

            tm13 = time.time()
            cost_send += tm12 - tm11
            cost_recv += tm13 - tm12
        tm04 = time.time()

        print_lines(retv_lines)
        print(" data send cost  %.3f" % cost_send)
        print(" data recv cost  %.3f" % cost_recv)
        cost_total = cost_send + cost_recv
        lmsg = " data total cost %.3f duration %.3f rate %.3f kbps" % (
                        cost_total, tm04 - tm00, float(dsz)/1000.0/cost_total)
        print(lmsg)
        stats.append(lmsg)
        break # scope

    for x in stats: print(" stats " + x)
    print(" stats cts high-low counts %d %d" % (
        _var_hw_cts_count_high, _var_hw_cts_count_low))
    print(" stats ok err unknown counts %d %d %d" % (
        stats_ok, stats_err, stats_unknown))


if __name__ == "__main__":
    tm0 = time.time()
    if len(sys.argv) > 1 and type(sys.argv[1]) is str:
        if sys.argv[1] == 'mon':
            pass # test_mon()
        elif sys.argv[1] == 'mon300':
            pass # test_mon(duration=300)
        elif sys.argv[1] == 'init':
            test_ports_init()
        else:
            print("")
            print("Available command line arguments: ")
            print("      mon      -- monitor the temperature sensors on the shell and in the environment")
            print("Without command line arguments, it shows temperatures in one shot")
    else:
        test_ports_packet()
    tmnow = time.time()
    print("total time: %.2f" % (tmnow - tm0))

'''
'''

