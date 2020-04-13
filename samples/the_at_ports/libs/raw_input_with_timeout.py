#!/usr/bin/env python
# raw_input_with_timeout.py


from __future__ import print_function
import __builtin__
import sys
def print(*args, **kwargs):
    retv = __builtin__.print(*args, **kwargs)
    sys.stdout.flush()
    return retv


import threading
import time
import multiprocessing


class ThreadWithTimeout(threading.Thread):

    __the_instance_lock = multiprocessing.Lock()
    __the_instances_count = 0
    __the_instance_no_one = None
    __the_instance_error_count = 0
    __the_instances_count_inits = 0
    __the_instances_count_runs = 0
    __the_instances_count_dels = 0

    def get_previous_instance(self):
        retv = None
        try:
            ThreadWithTimeout.__the_instance_lock.acquire()
            if ThreadWithTimeout.__the_instances_count == 1:
                retv = ThreadWithTimeout.__the_instance_no_one
            ThreadWithTimeout.__the_instance_lock.release()
        except:
            pass
        return retv

    def __init__(self, prompt=None, timeout=0):
        super(ThreadWithTimeout, self).__init__()
        self.__inited = False

        if prompt is None:
            return

        try:
            ThreadWithTimeout.__the_instance_lock.acquire()
            if ThreadWithTimeout.__the_instances_count < 1:
                ThreadWithTimeout.__the_instances_count += 1
                ThreadWithTimeout.__the_instance_no_one = self
                ThreadWithTimeout.__the_instances_count_inits += 1
                self.__inited = True
            ThreadWithTimeout.__the_instance_lock.release()
        except:
            pass
        self.__retv = None
        self.__prompt = prompt
        self.__time_to_wait = timeout
        self.__canceled = False

    def __del__(self):
        if self.__inited:
            ThreadWithTimeout.__the_instances_count_dels += 1

    def run(self):
        if self.__inited:
            ThreadWithTimeout.__the_instance_lock.acquire()
            ThreadWithTimeout.__the_instances_count_runs += 1
            ThreadWithTimeout.__the_instance_lock.release()

            print(" %s in %.1f seconds : " % (self.__prompt, self.__time_to_wait))
            astring = raw_input("")
            if not self.__canceled:
                self.__retv = astring

            ThreadWithTimeout.__the_instance_lock.acquire()
            if ThreadWithTimeout.__the_instances_count == 1:
                ThreadWithTimeout.__the_instances_count -= 1
                ThreadWithTimeout.__the_instance_no_one = None
            elif ThreadWithTimeout.__the_instances_count != 1:
                ThreadWithTimeout.__the_instance_error_count += 1
                print("  run __the_instance_error_count %d" % ThreadWithTimeout.__the_instance_error_count)
            ThreadWithTimeout.__the_instance_lock.release()

    def get_retv(self):
        if self.__inited and not self.__canceled:
            return self.__retv
        return None

    def get_inited(self):
        return self.__inited

    def get_instance_count(self):
        return ThreadWithTimeout.__instances_count

    def show_instances_stats(self):
        print("ThreadWithTimeout.__the_instances_count       %d" % ThreadWithTimeout.__the_instances_count)
        print("ThreadWithTimeout.__the_instance_error_count  %d" % ThreadWithTimeout.__the_instance_error_count)
        print("ThreadWithTimeout.__the_instances_count_inits %d" % ThreadWithTimeout.__the_instances_count_inits)
        print("ThreadWithTimeout.__the_instances_count_runs  %d" % ThreadWithTimeout.__the_instances_count_runs)
        print("ThreadWithTimeout.__the_instances_count_dels  %d" % ThreadWithTimeout.__the_instances_count_dels)


def raw_input_with_timeout(prompt, timeout=5.0):
    print(prompt)
    astring = None

    time_to_wait = timeout
    tm0 = time.time()

    while True: # scope
        tm1 = time.time()
        timer = ThreadWithTimeout(prompt, time_to_wait)
        if timer.get_inited(): # only one thread can be alive ...
            timer.start() # must start if it is inited
        else:
            timer = timer.get_previous_instance()
            if timer is None:
                print(" %s in %.1f seconds : %s" % (prompt, time_to_wait,
                                                    " <ignored-no-previous> "))
                break
            print(" %s in %.1f seconds %s : " % (prompt, time_to_wait,
                                                "on a previous raw_input "), end='')
        while timer.isAlive():
            time.sleep(1)
            if not timer.isAlive():
                #print(" -- not isAlive(). break. -- ")
                astring = timer.get_retv()
                break
            else:
                #print(" -- isAlive(). -- ")
                pass
            tm2 = time.time()
            tdiff = tm2 - tm1
            if tdiff > 0 and tdiff >= time_to_wait:
                #print(" -- got astring %s -- " % str(astring))
                print(" <timeout> ")
                #timer.cancel()
                break
        try:
            #print(" -- join -- ")
            timer.join(1.0)
            if timer.isAlive():
                #print(" -- timeout, not joined -- ")
                pass
            #print(" -- join done ok -- ")
        except:
            print(" -- join failed -- ")
        break # scope
    return astring


def raw_input_stats():
    ThreadWithTimeout().show_instances_stats()


if __name__ == "__main__":
    '''
    cfg_use_raw_input_w_timeout = True
    if cfg_use_raw_input_w_timeout:
        sys.path.insert(0, "./")
        try:
            import libs.raw_input_with_timeout as raw_read
        except:
            cfg_use_raw_input_w_timeout = False
            raise Exception("Not able to import libs.raw_input_with_timeout")
        del (sys.path[0])
    def get_raw_read(msg="raw_input"):
        if cfg_use_raw_input_w_timeout:
            return raw_read.raw_input_with_timeout(msg)
        else:
            return None
    
    if __name__ == "__main__":
        raw_retv = get_raw_read()
        print(" type raw_retv %s value %s " % (type(raw_retv), str(raw_retv)))
    
        raw_retv = get_raw_read()
        print(" type raw_retv %s value %s " % (type(raw_retv), str(raw_retv)))
    
        raw_read.raw_input_stats()
    '''
    print("The above is the test when this package file is placed under libs/")
