#!/usr/bin/python

import logging
import os
import re
import subprocess
import sys

TOP_DIR = os.path.join(os.getcwd(), "..")
LINUX_SRC_DIR = TOP_DIR + "/linux"
LINUX_BUILD_DIR = TOP_DIR + "/obj/a"
LINUX_MODULE_INSTALL_DIR = TOP_DIR + "/obj/a_modules"
CONFIG_FILE = "config_for_linux_4_12"

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

def write_file(filename, content):
    with open(filename, "w") as fh:
        fh.write(content)

def change_to_abs_path():
    global TOP_DIR, LINUX_SRC_DIR, LINUX_BUILD_DIR, CONFIG_FILE
    TOP_DIR = os.path.abspath(TOP_DIR)
    LINUX_SRC_DIR = os.path.abspath(LINUX_SRC_DIR)
    LINUX_BUILD_DIR = os.path.abspath(LINUX_BUILD_DIR)
    CONFIG_FILE = os.path.abspath(CONFIG_FILE)

def main():
    change_to_abs_path()
    is_cleanbuild = False
    for i in range(len(sys.argv)):
        if sys.argv[i] == 'clean':
            is_cleanbuild = True
    if not os.path.isdir(LINUX_BUILD_DIR) or is_cleanbuild:
        call_cmd(["rm", "-rf", LINUX_BUILD_DIR])
        call_cmd(["mkdir", "-p", LINUX_BUILD_DIR])
        call_cmd(["cp", CONFIG_FILE, os.path.join(LINUX_BUILD_DIR, ".config")])
    os.chdir(LINUX_SRC_DIR)
    call_cmd(["make", "O=" + LINUX_BUILD_DIR, "KCONFIG_CONFIG=%s/.config" % LINUX_BUILD_DIR, "-j20"])
    call_cmd(["make", "O=" + LINUX_BUILD_DIR, "KCONFIG_CONFIG=%s/.config" % LINUX_BUILD_DIR,
        "modules", "-j20"])
    call_cmd(["make", "O=" + LINUX_BUILD_DIR, "KCONFIG_CONFIG=%s/.config" % LINUX_BUILD_DIR,
        "INSTALL_MOD_PATH=%s" % LINUX_MODULE_INSTALL_DIR, "modules_install", "-j20"])

if __name__ == '__main__':
    main()
