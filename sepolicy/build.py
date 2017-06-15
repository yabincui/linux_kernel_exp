#!/usr/bin/python

import logging
import os
import re
import subprocess
import sys

"""
Build policy data:
    call gen_policy.py to generate policy.conf
    call checkpolicy to create policy.30
    build tools: load_policy, test.
"""

def get_script_dir():
    return os.path.dirname(os.path.realpath(__file__))

CHECKPOLICY_PATH = os.path.join(get_script_dir(), "../../selinux/obj/usr/bin/checkpolicy")
LIBRARY_PATH = os.path.join(get_script_dir(), "../../selinux/obj/lib")


def log_debug(msg):
    logging.debug(msg)

def log_fatal(msg):
    raise Exception(msg)
logging.getLogger().setLevel(logging.DEBUG)

def run_cmd(args, input="", check=True, shell=False):
    subproc = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, shell=shell)
    (stdoutdata, _) = subproc.communicate(input)
    returncode = subproc.returncode
    log_debug("cmd: %s" % args)
    log_debug("%s" % stdoutdata)
    log_debug("run cmd: %s [result %s]" % (args, returncode))
    if check and returncode != 0:
        log_fatal("cmd failed")
    return stdoutdata

def call_cmd(args):
    log_debug("cmd: %s" % args)
    subprocess.check_call(args)

def run_script(content):
    with open("_temp_script.sh", "w") as fh:
        fh.write("set -ex\n")
        fh.write(content)
    call_cmd(["sh", "_temp_script.sh"])
    call_cmd(["rm", "_temp_script.sh"])

def build_tools():
    run_script('gcc -o test test.c')
    run_script('gcc -o load_policy load_policy.c -I../obj/usr/include -L../obj/usr/lib -lselinux')


def main():
    run_script('python gen_policy.py')
    run_script("""
    export LD_LIBRARY_PATH=%s
    %s -c 30 -o policy.30 policy.conf
    """ % (LIBRARY_PATH, CHECKPOLICY_PATH))
    build_tools()

if __name__ == '__main__':
    main()
