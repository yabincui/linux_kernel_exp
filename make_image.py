#!/usr/bin/python

import logging
import os
import re
import subprocess
import sys

IMAGE_PATH = "image/a.img"
IMAGE_MOUNT_PATH = "image/tmp"
GRUB_INSTALL_PATH = "../grub/grub-install/sbin/grub-install"
KERNEL_IMAGE_PATH = "../obj/a/arch/x86/boot/bzImage"
BUSYBOX_INSTALL_PATH = "../busybox/obj/x86-busybox/_install"
INITRAMFS_PATH = "image/initramfs.gz"
INITRAMFS_TMPDIR = "image/initramfs_tmp"
NOGRAPHIC = True

def get_script_dir():
    return os.path.dirname(os.path.realpath(__file__))

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

def write_file(filename, content):
    with open(filename, "w") as fh:
        fh.write(content)

def mount_image():
    output = run_cmd(["sudo", "kpartx", "-av", IMAGE_PATH])
    start = output.find('loop')
    end = output.find(' ', start)
    loop_str = output[start:end]
    run_cmd(["sleep", "1"])
    run_cmd(["sudo", "mount", "/dev/mapper/" + loop_str, IMAGE_MOUNT_PATH])

def unmount_image():
    if os.path.isdir(IMAGE_MOUNT_PATH):
        run_cmd(["sudo", "umount", IMAGE_MOUNT_PATH], check=False)
    if os.path.isfile(IMAGE_PATH):
        run_cmd(["sudo", "kpartx", "-d", IMAGE_PATH], check=False)

def create_image_with_partition():
    run_cmd(["dd", "if=/dev/zero", "of=" + IMAGE_PATH, "bs=1M", "count=100"])
    input="n\np\n1\n2048\n\nw\n"
    run_cmd(["fdisk", IMAGE_PATH], input=input)
    output = run_cmd(["sudo", "kpartx", "-av", IMAGE_PATH])
    start = output.find('loop')
    end = output.find(' ', start)
    loop_str = output[start:end]
    run_cmd(["sleep", "1"])
    run_cmd(["sudo", "mkfs.ext4", "/dev/mapper/" + loop_str])
    run_cmd(["mkdir", "-p", "tmp"])
    run_cmd(["sudo", "mount", "/dev/mapper/" + loop_str, IMAGE_MOUNT_PATH])
    run_cmd(["sudo", "chown", "yabinc:yabinc", IMAGE_MOUNT_PATH])
    return loop_str

def install_grub(loop_partition_name):
    m = re.search(r'loop(\d+)', loop_partition_name)
    loop_number = m.group(1)
    run_cmd(["mkdir", "-p", IMAGE_MOUNT_PATH + "/boot/grub"])
    run_cmd(["sudo", GRUB_INSTALL_PATH, "--root-directory=" + os.path.abspath(IMAGE_MOUNT_PATH),
        "/dev/loop" + loop_number])

class Rootfs(object):
    def __init__(self, rootdir):
        self.rootdir = rootdir

    def mkdir(self, dirname):
        run_cmd(["mkdir", "-p", os.path.join(self.rootdir, dirname)])

    def copyWholeDir(self, dirname):
        for item in os.listdir(dirname):
            run_cmd(["cp", "-av", os.path.join(dirname, item), self.rootdir])

    def writeFile(self, filepath, content, executable=False):
        filepath = os.path.join(self.rootdir, filepath)
        dirpath = os.path.dirname(filepath)
        if not os.path.isdir(dirpath):
            self.mkdir(dirpath)
        with open(filepath, "w") as fh:
            fh.write(content)
        if executable:
            run_cmd(["chmod", "a+x", filepath])

    def copyFile(self, src, dest):
        run_cmd(["cp", src, os.path.join(self.rootdir, dest)])

    def removeFile(self, filepath):
        filepath = os.path.join(self.rootdir, filepath)
        if os.path.isfile(filepath):
            os.unlink(filepath)

def create_initramfs():
    run_cmd(["rm", "-rf", INITRAMFS_TMPDIR])
    rootfs = Rootfs(INITRAMFS_TMPDIR)
    dirs = ["bin", "sbin", "etc", "proc", "sys", "usr/bin", "usr/sbin", "dev"]
    for dirname in dirs:
        rootfs.mkdir(dirname)
    rootfs.copyWholeDir(BUSYBOX_INSTALL_PATH)
    init_script = """#!/bin/sh
        echo "Hello, Linux!"
        export PATH=/usr/sbin:/usr/bin:/sbin:/bin
        mount -n -t devtmpfs none /dev
        mount -n -t proc proc /proc
        mount -n -t sysfs sysfs /sys
        mkdir tmp
        mount -n -t ext4 /dev/sda1 tmp
        mount -n --move /dev tmp/dev
        mount -n --move /proc tmp/proc
        mount -n --move /sys tmp/sys
        /bin/switch_root tmp /init
    """
    rootfs.writeFile("init", init_script, executable=True)
    rootfs.copyFile(os.path.join(get_script_dir(), "tools/switch_root"), "bin")
    run_script("""
        cd %s
        find . -print0 | cpio --null -ov --format=newc | gzip -9 >%s
    """ % (INITRAMFS_TMPDIR, os.path.abspath(INITRAMFS_PATH)))

def create_rootfs():
    rootfs = Rootfs(IMAGE_MOUNT_PATH)
    dirs = ["bin", "sbin", "etc", "proc", "sys", "usr/bin", "usr/sbin", "dev"]
    for dirname in dirs:
        rootfs.mkdir(dirname)
    rootfs.copyWholeDir(BUSYBOX_INSTALL_PATH)
    rootfs.copyFile(KERNEL_IMAGE_PATH, "boot/bzImage")
    rootfs.copyFile(INITRAMFS_PATH, "boot/initrd.img")
    console_cmdline = " console=ttyS0" if NOGRAPHIC else ""
    rootfs.writeFile("boot/grub/grub.cfg", """
        set default="0"
        menuentry 'vita' {
            insmod ext2
            set root='hd0,msdos1'
            linux /boot/bzImage%s
            initrd /boot/initrd.img
        }
        set timeout=0
    """ % (console_cmdline))
    rootfs.writeFile("init","""#!/bin/sh
        echo "Hello, init on disk!"
        mount -t selinuxfs none /sys/fs/selinux
        exec /bin/sh
    """, executable=True)

    # load basic libraries
    rootfs.mkdir("lib64")
    rootfs.copyFile("/lib64/ld-linux-x86-64.so.2", "lib64/")
    rootfs.mkdir("lib/x86_64-linux-gnu")
    for lib in ["libc.so.6", "libpcre.so.3", "libdl.so.2", "libpthread.so.0"]:
        rootfs.copyFile("/lib/x86_64-linux-gnu/" + lib, "lib/x86_64-linux-gnu/" + lib)

    # load some utils
    rootfs.removeFile("bin/ls")
    rootfs.copyFile("/bin/ls", "bin/")
    return rootfs

def create_user_module(rootfs):
    rootfs.writeFile("etc/passwd",
"""a:x:1000:1000:Linux User,,,:/:/bin/sh
b:x:1001:1001:Linux User,,,:/:/bin/sh
""")
    rootfs.writeFile("etc/passwd-",
"""a:x:1000:1000:Linux User,,,:/:/bin/sh
""")
    rootfs.writeFile("etc/group",
"""a:x:1000:
b:x:1001:
""")
    rootfs.writeFile("etc/group-",
"""a:x:1000:
""")

def load_selinux_module(rootfs):
    SEPOLICY_PATH=os.path.join(get_script_dir(), "sepolicy/policy.30")
    LOAD_POLICY_PATH = os.path.join(get_script_dir(), "sepolicy/load_policy")
    TEST_EXE_PATH = os.path.join(get_script_dir(), "sepolicy/test")
    SELINUX_INSTALL_DIR = os.path.join(get_script_dir(), "../selinux/obj")
    SETFILES_PATH = os.path.join(get_script_dir(), "../selinux/obj/sbin/setfiles")
    FILE_CONTEXTS_PATH = os.path.join(get_script_dir(), "sepolicy/file_contexts")
    rootfs.mkdir("selinux")
    rootfs.copyFile(SEPOLICY_PATH, "selinux")
    rootfs.copyFile(LOAD_POLICY_PATH, "selinux")
    rootfs.copyFile(TEST_EXE_PATH, "selinux")
    for lib in ["libselinux.so.1"]:
        rootfs.copyFile(os.path.join(SELINUX_INSTALL_DIR, "lib", lib), "lib/x86_64-linux-gnu/" + lib)
    for filename in ["usr/sbin/setenforce", "usr/sbin/getenforce"]:
        rootfs.copyFile(os.path.join(SELINUX_INSTALL_DIR, filename), filename)
    run_script("sudo %s -F -r %s -v %s %s" % (
        SETFILES_PATH, rootfs.rootdir, FILE_CONTEXTS_PATH, rootfs.rootdir))
    run_cmd(["sleep", "1"])

def main():
    unmount_image()
    loop_partition_name = create_image_with_partition()
    install_grub(loop_partition_name)
    create_initramfs()
    rootfs = create_rootfs()
    create_user_module(rootfs)
    load_selinux_module(rootfs)
    # unmount to flush data to disk
    unmount_image()
    mount_image()

if __name__ == '__main__':
    main()
