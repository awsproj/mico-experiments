#!/usr/bin/env python
# conf_read_ports.py


import re


_conf_file = "conf_ports"

'''
console=COM11

or 

console=/dev/ttyS10
'''

def _conf_read_ports():
    retv = None
    import os
    conf_file = _conf_file
    if os.path.isfile(conf_file):
        try:
            the_console = None
            with open(conf_file, "r") as fn:
                the_lines = []
                try:
                    the_lines = fn.readlines()
                except:
                    pass
                for theline in the_lines:
                    innerline = theline.strip(u' \t\r\n')
                    coreline = re.sub(r'\s+', '', innerline)
                    if len(coreline) <= 3 or coreline.startswith('#'):
                        next
                    if coreline.startswith('console='):
                        the_console = coreline[len('console='):]
            def valid_port(x):
                return (x is not None and len(x) > 3)
            if valid_port(the_console):
                retv = [the_console]
        except:
            pass
    return retv

_ports_data = _conf_read_ports()

def get_conf_console():
    if len(_ports_data) == 1:
        return _ports_data[0]
    return None

def get_conf_ext_thermal():
    if len(_ports_data) == 3:
        return _ports_data[1]
    return None

def get_conf_env_weather():
    if len(_ports_data) == 3:
        p3 = _ports_data[2]
        if p3 is not None and len(p3) > 3:
            return p3
    return None

