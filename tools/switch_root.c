#include <fcntl.h>
#include <stdio.h>
#include <unistd.h>

int main(int argc, char** argv) {
  chdir(argv[1]);
  chroot(".");
  int console_fd = open("/dev/console", O_RDWR);
  dup2(console_fd, 0);
  dup2(console_fd, 1);
  dup2(console_fd, 2);
  close(console_fd);
  execlp(argv[2], argv[2], NULL);
  return 0;
}
