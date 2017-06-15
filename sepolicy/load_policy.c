#include <sys/types.h>
#include <sys/stat.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <unistd.h>
#include <selinux/selinux.h>

char* loadFile(const char* filename, int* size) {
  struct stat st;
  int ret = stat(filename, &st);
  if (ret != 0) {
    perror("stat");
    return NULL;
  }
  int filesize = (int)st.st_size;
  char* data = (char*)malloc(filesize);
  if (data == NULL) {
    perror("malloc");
    return NULL;
  }
  FILE* fp = fopen(filename, "rb");
  if (fp == NULL) {
    perror("fopen");
    goto err_file;
  }
  if (fread(data, filesize, 1, fp) != 1) {
    perror("fread");
    goto err_read;
  }
  fclose(fp);
  *size = filesize;
  return data;

err_read:
  fclose(fp);
err_file:
  free(data);
  return NULL;
}

int main(int argc, char** argv) {
  if (argc != 2) {
    printf("load_policy policy.VER   -- load policy\n");
    return 0;
  }
  const char* file = argv[1];
  int size;
  char* data = loadFile(file, &size);
  if (data == NULL) {
    return 1;
  }
  int ret = security_load_policy(data, size);
  if (ret != 0) {
    perror("security_load_policy");
    return 1;
  }
  return 0;
}
