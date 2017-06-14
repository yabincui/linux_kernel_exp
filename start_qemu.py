#!/usr/bin/python

import logging
import os
import subprocess
import sys

DISK_IMAGE_PATH = "image/a.img"
NOGRAPHIC = False

def log_debug(msg):
    logging.debug(msg)

def log_fatal(msg):
    raise Exception(msg)
logging.getLogger().setLevel(logging.DEBUG)

def run_cmd(args, input="", check=True):
    subproc = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
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


def write_file(filename, content):
    with open(filename, "w") as fh:
        fh.write(content)

def start_qemu():
    args = ["qemu", "-hda", DISK_IMAGE_PATH]
    if NOGRAPHIC:
        args += ["-nographic"]
    call_cmd(args)

def main():
    start_qemu()

if __name__ == '__main__':
    main()
