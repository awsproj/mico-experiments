#!/usr/bin/env python
# the_at_ports.py

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


_cfg_pyser_timeout = 0.3
_cfg_uart_baudrate1 = 115200 # 115200 default
_cfg_uart_baudrate2 = 921600 # could use 921600
_cfg_uart_baudrate = _cfg_uart_baudrate1 # init to default

_cfg_hw_ctsrts = False # True to set rts line and check cts line
_var_hw_cts_count_high = 0
_var_hw_cts_count_low = 0
_cfg_hw_debug_cts = False

_cfg_batch_slack = False # emw3060 True: cost 640ms.


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
            #val = readln(ser)
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
                if val.decode().startswith('OK'):
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
        retv_cmd = pyser_console_cmd("AT\r")
        if type(retv_cmd) is list and len(retv_cmd) >= 2:
            if retv_cmd[0][2].decode().find('AT') >= 0:
                if retv_cmd[1][2].decode().find('OK') >= 0:
                    cmd_ok = True
    except:
        pass
    if not cmd_ok:
        pyser_close_all()
        pyser_open(baud_rate=_cfg_uart_baudrate2)
        try:
            pyser_console_cmd("\r")
            retv_cmd = pyser_console_cmd("AT\r")
            if type(retv_cmd) is list and len(retv_cmd) >= 2:
                if retv_cmd[0][2].decode().find('AT') >= 0:
                    if retv_cmd[1][2].decode().find('OK') >= 0:
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

if cfg_use_pyserial:
    pyser_open_dual()

def test_ports_uart921600():
    print("")
    print("console command:")
    print_lines(pyser_console_cmd("AT+UART?\r"))
    #115200,8,1,NONE,NONE

    print("")
    print("console command:")
    #print_lines(pyser_console_cmd("AT+UART=921600,8,1,NONE,NONE\r"))
    if _cfg_hw_ctsrts:
        print_lines(pyser_console_cmd("AT+UART=921600,8,1,NONE,CTSRTS\r"))
    else:
        print_lines(pyser_console_cmd("AT+UART=921600,8,1,NONE,NONE\r"))
    # need to reboot to take effect
    # after CTSRTS is set it needs to reboot and raise the rts line

def test_ports_init():
    print("")
    print("console command:")
    print_lines(pyser_console_cmd("\r"))

    print("")
    print("console command:")
    print_lines(pyser_console_cmd("\r"))

    print("")
    print("console command:")
    print_lines(pyser_console_cmd("AT\r"))

    print("")
    print("console command:")
    print_lines(pyser_console_cmd("AT+FACTORY\r"))

    for i in range(15, 0, -2):
        print(" count down %d " % i)
        time.sleep(2.05)

    test_ports_uart921600()

    print("")
    print("console command:")
    print_lines(pyser_console_cmd("AT+REBOOT\r"))

    pyser_close_all()
    if cfg_use_pyserial:
        pyser_open_dual()

    print("")
    print("console command:")
    print_lines(pyser_console_cmd("AT+WJAP=TestAP\r", ))
    #OK

    for i in range(30):
        print(" count up %d " % i)
        time.sleep(1.0)
        print("")
        print("console command:")
        retv_jap = pyser_console_cmd("\r")
        #+WEVENT:STATION_UP
        print_lines(retv_jap)
        found_up = False
        for x in retv_jap:
            import re
            s = re.sub(r'\r', ' ', x[2].decode())
            u = re.sub(r'\n', ' ', s)
            if x[0] >= 0 and x[1] >= 0:
                if u.find('+WEVENT:') >= 0:
                    if u.find('STATION_UP') > 2:
                        found_up = True
        if found_up:
            print(" found_up True at count up %d " % i)
            break

            print("%s    %8.3f %6.3f \t%s" % (prefix*" ", x[0], x[1], u))

    print("")
    print("console command:")
    print_lines(pyser_console_cmd("AT\r"))

    print("")
    print("console command:")
    print_lines(pyser_console_cmd("AT+WJAPS\r"))
    #0x0d 0x0a +WJAPS:STATION_UP0x0d 0x0a OK0x0d 0x0a

    print("")
    print("console command:")
    print_lines(pyser_console_cmd("AT+WJAP?\r"))
    #0x0d 0x0a +WJAP:TestAP,341513209855,11,-740x0d 0x0a OK

    print("")
    print("console command:")
    print_lines(pyser_console_cmd("AT+WJAPIP?\r"))
    #+WJAPIP:192.168.2.22,255.255.255.0,192.168.2.1,0.0.0.0


    print("")
    print("console command:")
    print_lines(pyser_console_cmd("\r"))

    pyser_close_all()

def test_ports_packet():

    stats = []
    stats_ok, stats_err, stats_unknown = 0, 0, 0

    print("")
    print("console command:")
    print_lines(pyser_console_cmd("AT+CIPRECVCFG?\r")) # 0:cmd; 1:event

    print("")
    print("console command:")
    print_lines(pyser_console_cmd("AT+CIPRECVCFG=0\r")) # 0:cmd; 1:event

    print("")
    print("console command:")
    print_lines(pyser_console_cmd("AT+MEMFREE?\r")) # 0:cmd; 1:event

    print("")
    print("console command:")
    print_lines(pyser_console_cmd("AT+CIPSTART=0,tcp_client,192.168.2.1,8000\r"))

    time.sleep(1)

    print("")
    print("console command:")
    print_lines(pyser_console_cmd("AT+CIPSEND=0,4\ra123"))
    dsz_init = 4 # first send bytes

    print("")
    print("console command:")
    print_lines(pyser_console_cmd("AT+CIPRECV=0,8000,100\r"))

    print("")
    print("console command:")
    print_lines(pyser_console_cmd("AT+CIPRECV=0,8000,100\r"))

    print("")
    print("console command: send data")
    while True: # scope
        dsz, pktsz = dsz_init, 1000
        send_data = 'j' * pktsz
        tm00 = time.time()
        retv_lines = []
        cost_send = 0
        cost_recv = 0
        batch1, batch2 = 2, 6 # emw110 ok: 2,6 with cost 422ms.
        batch_slack = _cfg_batch_slack # False # emw3060 True: cost 640ms.
        batch_out, batch_last_str = [], ""
        for k in range(batch1 * batch2 + 2 - batch2):
            if dsz >= dsz_init + batch1 * batch2 * pktsz:
                print("console command done: send data")
                break
            tm11 = time.time()
            for i in range(batch2 - len(batch_out)):
                retv_cmd = pyser_console_cmd_data("AT+CIPSEND=0,1000\r" + send_data)
                retv_lines.extend(retv_cmd)
                retv_result = ""
                for x in retv_cmd:
                    if x[0] == -1:
                        x_str = x[2].decode()
                        if x_str.startswith("loop escape got ERROR"):
                            retv_result = "ERR"
                            stats_ok += 1
                        elif x_str.startswith("loop escape got OK"):
                            retv_result = "OK"
                            stats_err += 1
                        else:
                            stats_unknown += 1
                if retv_result == "OK":
                    dsz += pktsz
                    batch_out.append("dsz:%d" % dsz)
                if dsz >= dsz_init + batch1 * batch2 * pktsz:
                    batch_last_str = batch_out[-1]
                    break
                if batch_slack:
                    time.sleep(0.02) # emw3060 may need this .02 delay
            tm12 = time.time()

            wait_ack_loops = 80 # for about 0.8 seconds. actual about 2.5 sec.
            if batch_slack:
                wait_ack_loops = 40 # emw3060 longer wait between polls.
            for i in range(wait_ack_loops):
                retv_seg=pyser_console_cmd_data("AT+CIPRECV=0,8000,1200\r")
                segm1 = retv_seg[1][2].decode()
                retv_lines.extend(retv_seg)
                if segm1.startswith("+CIPRECV:"):
                    if not segm1.startswith("+CIPRECV:0"):
                        while len(batch_out) > 0:
                            tgtstr = batch_out[0]
                            if segm1.find(tgtstr) > 2:
                                #print("OK find %s in %s" % (tgtstr, segm1))
                                batch_out.pop(0)
                            else:
                                #print("Cannot find %s in %s" % (tgtstr, segm1))
                                break
                    # +CIPRECV:12,  dsz 4004
                    # +CIPRECV:90,  dsz:1004:1.007    dsz:2004:0.024    dsz:3004:0.034    dsz:4004:0.027    dsz:5004:0.026
                batch_out_limit = batch2 # recv any ack, send more
                if len(batch_last_str) > 0:
                    batch_out_limit = 1 # last packet has been sent, wait for all
                if len(batch_out) < batch_out_limit:
                    tm14 = time.time()
                    lmsg = "loops %d time %.3f" % (i, tm14 - tm12)
                    retv_lines.append([-2,-2,lmsg.encode()])
                    break
                if i == 80 - 1:
                    tm14 = time.time()
                    lmsg = "loops %d time %.3f" % (i, tm14 - tm12)
                    retv_lines.append([-2,-2,lmsg.encode()])
                tm15 = time.time()
                if tm15 - tm12 > 4: # 4.0 seconds
                    lmsg = "loops %d time %.3f" % (i, tm15 - tm12)
                    retv_lines.append([-2,-2,lmsg.encode()])
                    break
                time.sleep(0.01) # emw110.
                if batch_slack:
                    time.sleep(0.01) # emw3060 may need longer wait.
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

    print("")
    print("console command:")
    print_lines(pyser_console_cmd("AT+CIPRECV=0,8000,1200\r"))

    print("")
    print("console command:")
    print_lines(pyser_console_cmd("AT+CIPRECV=0,8000,1200\r"))

    time.sleep(1)

    print("")
    print("console command:")
    print_lines(pyser_console_cmd("AT+CIPSTOP=0\r"))

    time.sleep(1)

    print("")
    print("console command:")
    print_lines(pyser_console_cmd("AT+MEMFREE?\r")) # 0:cmd; 1:event

    print("")
    print("console command:")
    print_lines(pyser_console_cmd("AT+WJAP?\r"))

    print("")
    print("console command:")
    print_lines(pyser_console_cmd("\r"))

    for x in stats: print(" stats " + x)
    print(" stats cts high-low counts %d %d" % (
        _var_hw_cts_count_high, _var_hw_cts_count_low))
    print(" stats ok err unknown counts %d %d %d" % (
        stats_ok, stats_err, stats_unknown))


class ThermalPorts():
    __ports_are_open = False
    __ports_are_closed = False

    def __init__(self):
        if not ThermalPorts.__ports_are_open and not ThermalPorts.__ports_are_closed:
            ThermalPorts.__ports_are_open = True
    def __del__(self):
        if ThermalPorts.__ports_are_open and not ThermalPorts.__ports_are_closed:
            ThermalPorts.__ports_are_closed = True
            pyser_close_all()

    def doConsoleCmd(self, msg=""):
        if ThermalPorts.__ports_are_open and not ThermalPorts.__ports_are_closed:
            return pyser_console_cmd(msg)
        else:
            return None

    def isThermalOrWeatherModeOk(self, lines): # shared between thermal and weather
        if type(lines) is not list:
            print("Mode not ok : not list")
            return False
        modeline = lines[-1]
        if type(modeline) is not list or len(modeline) < 3:
            print("Mode not ok : line not list or not enough elements")
            return False
        mode = modeline[2]
        if type(mode) is not str and type(mode) is not unicode:
            print("Mode not ok : not str or unicode")
            return False
        if mode == "DIO>" or mode == u"DIO>":
            return True
        print("Mode not ok : not DIO>")
        return False

    def setThermalMode(self):
        self.doThermalCmd('#\r')
        time.sleep(1)
        self.doThermalCmd('m\r')
        time.sleep(1)
        self.doThermalCmd('9\r')
        time.sleep(1)
        self.doThermalCmd('W\r')
        time.sleep(1)
        return self.doThermalCmd('v\r')

    def setWeatherMode(self):
        self.doWeatherCmd('#\r')
        time.sleep(1)
        self.doWeatherCmd('m\r')
        time.sleep(1)
        self.doWeatherCmd('9\r')
        time.sleep(1)
        self.doWeatherCmd('W\r')
        time.sleep(1)
        return self.doWeatherCmd('v\r')

    def printLines(self, lines, prefix=3):
        print_lines(lines, prefix=prefix)

    def parseTemperatureConsole(self, in_lines):
        retv = float(0)
        import re
        sums = 0.0
        sumn = 0
        for theline in in_lines:
            if len(theline) < 3 or len(theline[2]) < 3:
                continue # next line
            x = theline[2]
            x = x.strip(' \t\r\n')
            x = re.sub(r'\s+', ' ', x)
            m = re.match(r'(\d+\.\d+).*', x)
            if m:
                k = m.groups()
                #print("    match: k %s" % str(k))
                if len(k) == 1:
                    v = float(k[0])
                    if v >= 10.0 and v < 99.0:
                        sums += float(k[0])
                        sumn += 1
                    else:
                        print("    Error: < 10 or > 99 match: k %s" % str(k))
                else:
                    print("    Error: match: k %s" % str(k))
        if sumn > 0:
            retv = sums / sumn
        return retv

    def parseTemperatureBuspirateLm35(self, in_lines):
        retv = float(0)
        import re
        for theline in in_lines:
            if len(theline) < 3 or len(theline[2]) < 3:
                continue # next line
            x = theline[2]
            x = x.strip(' \t\r\n')
            x = re.sub(r'\s+', ' ', x)
            m = re.match(r'GND\s+(\d+\.\d+)V\s+(\d+\.\d+)V\s+(\d+\.\d+)V\s+(\d+\.\d+)V\s+[HL].*', x)
            if m:
                k = m.groups()
                #print("    match: k %s" % str(k))
                if len(k) == 4:
                    v33 = float(k[0])
                    v50 = float(k[1])
                    if v33 < 2.0 or v50 < 4.0:
                        print("    Error: v33 or v50. match: k %s" % str(k))
                    retv = float(k[2]) * 100
                else:
                    print("    Error: match: k %s" % str(k))
        return retv

    def parseUptimeLoadConsole(self, in_lines):
        '''
        ~ # uptime; mpstat
         17:25:50 up 7 min,  1 users,  load average: 4.20, 3.29, 1.59
        Linux 4.9.37 (hw44)     05/03/19        _aarch64_       (4 CPU)
        
        17:25:50     CPU    %usr   %nice    %sys %iowait    %irq   %soft  %steal  %guest   %idle
        17:25:50     all   42.92    0.00    1.79    0.28    0.00    0.64    0.00    0.00   54.38
        '''
        retv = ['up unknown', 'idle unknown'] # uptime, idle
        import re
        state = 0
        for theline in in_lines:
            if len(theline) < 3 or len(theline[2]) < 3:
                continue # next line
            x = str(theline[2])
            x = x.strip(' \t\r\n')
            x = re.sub(r'\s+', ' ', x)
            if state == 0:
                m = re.match(r'^\s*\S+\s+up\s+(\d+\S+.*),\s+\d+\s+users.*$', x)
                if m:
                    k = m.groups()
                    # print("    match: k %s" % str(k))
                    if len(k) == 1:
                        retv[0] = k[0]
                        state = 1
                    else:
                        print("    Error: match state %d: k %s" % (state, str(k)))
            elif state == 1:
                m = re.match(r'^\s*\S+\s+CPU\s+.*%idle\s*$', x)
                if m:
                    state = 2
            elif state == 2:
                m = re.match(r'^\s*\S+\s+all((\s+\d+\.\d+)+)\s*$', x)
                if m:
                    k = m.groups()
                    # matched k: <type 'tuple'>: (' 42.92 0.00 1.79 0.28 0.00 0.64 0.00 0.00 54.38', ' 54.38')
                    # print("    match: k %s" % str(k))
                    if len(k) == 2:
                        retv[1] = k[1]
                        state = 3
                    else:
                        print("    Error: match state %d: k %s" % (state, str(k)))
        return retv


def test_mon(duration=30, interval=5): # in minutes

    report_file = "log_report.csv"
    report_file_opened = False
    try:
        fh = open(report_file, "a+")
        report_file_opened = True
        def csv_write(msg):
            fh.write(msg)
            fh.flush()
        csv_write("thermal_ports test_mon  duration %d  interval %d\n" % (
            duration, interval))
        csv_write("seq,time_sec,time_date,shell_temperature,environment_temperature\n")
    except:
        print("Error: not able to open the report file \"%s\". ignored." % (report_file))
        def csv_write(*args, **kwargs):
            pass

    from datetime import datetime as dates

    thermal = ThermalPorts()
    _debug_thermal = False
    _debug_weather = False

    cycle_prompt = "MON"
    tm1 = time.time()
    loopcnt = 0
    while True:
        loopcnt += 1

        # modes
        heat = thermal.doThermalCmd("v\r")
        if not thermal.isThermalOrWeatherModeOk(heat):
            print("CYCLE %s -- set thermal mode  dates %s" % (cycle_prompt, dates.now()))
            if _debug_thermal:
                print("HEAT:       ")
                thermal.printLines(heat)
                print("HEAT: done. ")
            thermal.setThermalMode()
        heat = thermal.doWeatherCmd("v\r")
        if not thermal.isThermalOrWeatherModeOk(heat):
            print("CYCLE %s -- set weather mode  dates %s" % (cycle_prompt, dates.now()))
            if _debug_weather:
                print("HEAT: env   ")
                thermal.printLines(heat)
                print("HEAT: done. ")
            thermal.setWeatherMode()

        print("CYCLE %s -- %d begin  dates %s" % (cycle_prompt, loopcnt, dates.now()))

        # ext thermal
        heat = thermal.doThermalCmd("v\r")
        if _debug_thermal:
            print("HEAT:       ")
            thermal.printLines(heat)
            print("HEAT: done. ")
        shell_tempr = thermal.parseTemperatureBuspirateLm35(heat)
        print(" TEMPERATURE SHELL %s: " % cycle_prompt, "%.2f" % shell_tempr)

        # env thermal
        heat = thermal.doWeatherCmd("v\r")
        if _debug_weather:
            print("HEAT: env   ")
            thermal.printLines(heat)
            print("HEAT: done. ")
        env_tempr = thermal.parseTemperatureBuspirateLm35(heat)
        print(" TEMPERATURE ENV   %s: " % cycle_prompt, "%.2f" % env_tempr)

        # report in csv
        tmnow = time.time()
        #csv: "seq,time_sec,time_date,shell_temperature,environment_temperature"
        csv_write("%d,%d,%s,%.2f,%.2f\n" % (loopcnt, tmnow-tm1,
                                            dates.now(), shell_tempr, env_tempr ))

        # loop delay
        if tmnow - tm1 > duration * 60:
            break
        tmtgt = loopcnt * interval * 60 + tm1
        loop_delay = 10
        if tmtgt > tmnow + 5:
            loop_delay = tmtgt - tmnow
        print("CYCLE %s -- %d delay %.2f  dates %s" % (cycle_prompt, loopcnt, loop_delay, dates.now()))
        time.sleep(loop_delay)

    if report_file_opened:
        fh.close()


if __name__ == "__main__":
    tm0 = time.time()
    if len(sys.argv) > 1 and type(sys.argv[1]) is str:
        if sys.argv[1] == 'mon':
            test_mon()
        elif sys.argv[1] == 'mon300':
            test_mon(duration=300)
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

