#!/usr/bin/env python
# upipe_ports_3.py

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
_cfg_uart_baudrate = 921600

_cfg_hw_ctsrts = True # True to set rts line and check cts line
_var_hw_cts_count_high = 0
_var_hw_cts_count_low = 0
_cfg_hw_debug_cts = False

_cfg_pktsz = 1024 # 1440 # 1024 is the buffer size of emw110
_cfg_hdr_slack = False # split packet to header plus body


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
        #pyser = pyser_pkg.Serial('COM11', 115200, timeout=1)
        #pyser_console = pyser_pkg.Serial('/dev/ttyS10', 115200, timeout=0.3)
        global pyser_console
        pyser_console = pyser_pkg.Serial(port_console, baud,
                                         timeout=_cfg_pyser_timeout)
        _cfg_uart_baudrate = baud
        print("Opened UART %s at baud %d " % (port_console, baud))
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
        else:
            ser.write(cmd.encode())

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
                if val.decode().find('usz:') >= 0:
                    retv.append([-1,-1,"loop escape got OK".encode()])
                    break
                if val.decode().startswith('ERROR'):
                    retv.append([-1, -1, "loop escape got ERROR".encode()])
                    break
            if len(val) > 0:
                lastactive = tm03
            if i == max_loop - 1:
                retv.append([-1, -1, ("loop ends at max_loop %d" % max_loop).encode()])

        if _cfg_hw_ctsrts and False:
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
        j = ""
        if x[0] < 0 and x[1] < 0:
            j = " " * 22
        print("%s    %8.3f %6.3f \t %s %s" % (prefix*" ", x[0], x[1], j, u))

def pyser_open_dual():
    pyser_open()
    cmd_ok = False
    try:
        pyser_console_cmd("\r")
        retv_cmd = pyser_console_cmd("\r")
        if type(retv_cmd) is list and len(retv_cmd) >= 2:
            if retv_cmd[0][2].decode().find('usz:') >= 0:
                cmd_ok = True
    except:
        pass
    if not cmd_ok:
        pyser_close_all()
        pyser_open(baud_rate=_cfg_uart_baudrate)
        try:
            pyser_console_cmd("\r")
            retv_cmd = pyser_console_cmd("\r")
            if type(retv_cmd) is list and len(retv_cmd) >= 2:
                if retv_cmd[0][2].decode().find('usz:') >= 0:
                    cmd_ok = True
            if not cmd_ok:
                print("Error baud2: ")
                print_lines(retv_cmd)
        except BaseException as e:
            print("Exception baud2 %s" % str(e))
        except:
            print("Exception baud2 %s" % str("Unknown"))
    if not cmd_ok:
        raise Exception("Not able to open console for a command")
        pass

if cfg_use_pyserial:
    pyser_open_dual()

def test_ports_init():
    print("")
    print("console command:")
    print_lines(pyser_console_cmd("\r"))

    pyser_close_all()

def test_ports_packet(disable_debug=False):

    stats = []
    stats_ok, stats_err, stats_unknown = 0, 0, 0 # about serial command
    stats_pkt_ok, stats_pkt_retried, stats_retries = 0, 0, 0 # pkt
    stats_pkt_assemble, stats_pkt_abort_retry, stats_pkt_fwd = 0, 0, 0 # pkt
    stats_pkt_max_retry = 0 # pkt
    stats_retv = {}

    debug = True
    if disable_debug:
        debug = False
    if debug:
        print("")
        print("console command: send data seq reset")
    retv_rst_cmd = pyser_console_cmd_data("00000012a123") # 0000 reset seqn
    if debug:
        print_lines(retv_rst_cmd)

    #time.sleep(0.1)

    if debug:
        print("")
        print("console command: send data")
    # data packet format: T S L G V ... -- total 1024 bytes
    #                T : 2 bytes, ascii 00 for data request
    #                                   01 for ... ... to be defined
    #                S : 2 bytes, ascii 01 to 99. special 00 for sequence reset. 
    #                L : 4 bytes, ascii number, msb first. max 1024. 
    #                G : 2 bytes, non-T
    #                V : up to L-10 bytes, user data
    while True: # scope
        pktsz = _cfg_pktsz # 1440 # 1024 is the buffer size of emw110
        batch1, batch2 = 2, 6 # emw110 ok: 2,6 with cost 422ms.
        send_data = 'j' * (pktsz - 8 - 2) # 8 for header, 2 for non-00

        tm00 = time.time()
        retv_lines = []
        cost_send, cost_recv = 0, 0


        dsz = 0
        for k in range(batch1 * batch2):
            seqn = (k % 99) + 1  # 1 .. 99
            dsz += pktsz
            sx_hdr = "00%02d%04d--" % (seqn, pktsz)
            rx_hdr = "00%02d%04d--usz:%04d" % (seqn, pktsz, pktsz)
            retry_ok = False

            retry_max = 4
            for r in range(retry_max): # retry count
                ack_ok, cmd_ok = False, False
                tm11 = time.time()
                retv_cmd = pyser_console_cmd_data(sx_hdr + send_data)
                tm12 = time.time()
                for x in retv_cmd:
                    x_str = x[2].decode()
                    if x[0] == -1:
                        if x_str.startswith("loop escape got OK"):
                            stats_ok += 1
                            cmd_ok = True
                        elif x_str.startswith("loop escape got ERROR"):
                            stats_err += 1
                        else:
                            stats_unknown += 1
                    else:
                        if x_str.startswith(rx_hdr):
                            ack_ok = True
                            segs = x_str[len(rx_hdr):].split(' ')
                            #print(" segs " + str(segs))
                            if len(segs) == 3:
                                if not segs[1].startswith("1"):
                                    stats_pkt_assemble += 1
                                if segs[2].startswith("1"):
                                    stats_pkt_fwd += 1
                            else:
                                print(" segs ERROR ")

                if cmd_ok and ack_ok:
                    retv_cmd.append([-2, -2, "OK".encode()])
                    retry_ok = True
                elif ack_ok:
                    retv_cmd.append([-2, -2, "OK-ack".encode()])
                    retry_ok = True
                elif cmd_ok:
                    retv_cmd.append([-2, -2, "Retry-cmd-ok".encode()])
                else:
                    retv_cmd.append([-2, -2, "Retry-no-cmd-ok".encode()])
                retv_lines.extend(retv_cmd)
                tm13 = time.time()
                cost_send += tm12 - tm11
                cost_recv += tm13 - tm12
                if r != 0:
                    stats_retries += 1
                if r > stats_pkt_max_retry:
                    stats_pkt_max_retry = r
                if retry_ok:
                    if r != 0: stats_pkt_retried += 1
                    break
                if r == retry_max - 1: # last loop, but not retry_ok
                    stats_pkt_abort_retry += 1
                    stats_pkt_max_retry = r + 1
            if retry_ok:
                stats_pkt_ok += 1
            else:
                print("Abort sending data at k %d" % k)
                break
        tm04 = time.time()

        if debug:
            print_lines(retv_lines)
            print(" data send cost  %.3f" % cost_send)
            print(" data recv cost  %.3f" % cost_recv)
        cost_total = cost_send + cost_recv
        duration_total = tm04 - tm00
        bytes_ps = float(dsz)/1000.0/cost_total
        lmsg = " data total cost %.3f duration %.3f rate %.3f kbyte ps" % (
                        cost_total, duration_total, bytes_ps)
        stats_retv['cost'] = cost_total
        stats_retv['duration'] = duration_total
        stats_retv['bytesps'] = bytes_ps

        if debug:
            print(lmsg)
        stats.append(lmsg)
        break # scope

    if debug:
        for x in stats: print(" stats " + x)
        print(" stats cts high-low counts %d %d" % (
            _var_hw_cts_count_high, _var_hw_cts_count_low))
        print(" stats ok err unknown counts %d %d %d" % (
            stats_ok, stats_err, stats_unknown))
        print(" stats pkt ok retried retries counts %d %d %d" % (
            stats_pkt_ok, stats_pkt_retried, stats_retries), end="  ")
        print("  pkt abort assemble fwd counts %d %d %d" % (
            stats_pkt_abort_retry, stats_pkt_assemble, stats_pkt_fwd), end="")
        print("  max retry %d" % stats_pkt_max_retry)
    stats_retv['pkt_ok'] = stats_pkt_ok
    stats_retv['pkt_retried'] = stats_pkt_retried
    stats_retv['pkt_retries'] = stats_retries
    stats_retv['pkt_abort'] = stats_pkt_abort_retry
    stats_retv['pkt_assemble'] = stats_pkt_assemble
    stats_retv['pkt_fwd'] = stats_pkt_fwd
    stats_retv['pkt_maxretry'] = stats_pkt_max_retry
    return stats_retv

def test_ports_packets():
    stats_lists = []
    tm0 = time.time()
    last_tm = tm0
    for m in range(60):
        for h in range(2):
            retv = test_ports_packet(disable_debug=True)
            tmnow = time.time()
            stat = [m+1, h+1, tmnow - tm0, tmnow - last_tm, retv]
            stats_lists.append(stat)
            last_tm = tmnow
    
    sum_cnt = 0
    sum_rate = 0.0
    sum_duration = 0.0
    for x in stats_lists:
        print(" %d %d  %.3f %.3f " % ( x[0], x[1], x[2], x[3] ), end="  ")
        #pp.pprint(x[4])
        #{   'bytesps': 25.079441976707184,
        #    'cost': 0.4899630546569824,
        #    'duration': 0.4899630546569824,
        #    'pkt_abort': 0,
        #    'pkt_assemble': 0,
        #    'pkt_fwd': 12,
        #    'pkt_ok': 12,
        #    'pkt_retried': 2,
        #    'pkt_retries': 2}
        #     stats_retv['pkt_maxretry'] = stats_pkt_max_retry
        print(" Bps %.2f duration %.2f retried/s/max %d %d %d" % ( 
                x[4]['bytesps'], 
                x[4]['duration'], x[4]['pkt_retried'], x[4]['pkt_retries'], 
                x[4]['pkt_maxretry'] ))
        sum_duration += x[4]['duration']
        sum_rate += x[4]['bytesps']
        sum_cnt += 1
    
    print("  avg rate %.2f duration %.2f" % ( sum_rate/sum_cnt, sum_duration/sum_cnt ))
    def getSum(v=None, value=False):
        retv = 0
        for x in stats_lists:
            t = x[4].get(v, None)
            if t is not None:
                if not value: # occurances 
                    retv += 1 if t is not 0 else 0
                else:
                    retv += t
            else:
                retv += 1000000
        return retv
    def getPartitial(v=None):
        retv = 0
        for x in stats_lists:
            t = x[4].get(v, None)
            if t is not None:
                retv += 1 if t != 12 else 0
            else:
                retv += 1000000
        return retv
    def getMax(v=None):
        retv = 0
        for x in stats_lists:
            t = x[4].get(v, None)
            if t is not None:
                retv = t if t > retv else retv
            else:
                retv += 1000000
        return retv
    print("  abort %d assemble %d partitial %d %d retried/s/max %d %d %d" % (
            getSum(v='pkt_abort'), getSum(v='pkt_assemble'), 
            getPartitial(v='pkt_ok'), getPartitial(v='pkt_fwd'), 
            getSum(v='pkt_retried'), getSum(v='pkt_retries', value=True), 
            getMax(v='pkt_maxretry') ))


if __name__ == "__main__":
    tm0 = time.time()
    if len(sys.argv) > 1 and type(sys.argv[1]) is str:
        if sys.argv[1] == 'init':
            test_ports_init()
        elif sys.argv[1].startswith('rep'):
            test_ports_packets()
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

