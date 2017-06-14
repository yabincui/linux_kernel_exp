This project is a collection of scripts used for experimenting linux kernel.

`config_for_linux_4_12` is a configuration of linux kernel for x86_64 pc.

`build_kernel_qemu.py` is used to build kernel and kernel modules.

`make_image.py` is used to create disk image for running linux kernel.

`start_qemu.py` runs qemu with the built image.

To play with these scripts, you need to download sources as below:

    linux kernel -- https://github.com/torvalds/linux.git
    grub2 -- https://git.savannah.gnu.org/git/grub.git
    busybox -- https://github.com/mirror/busybox.git

Make sure at least following libraries are installed before building the sources:

    sudo apt-get install libdevmapper-dev
