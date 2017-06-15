#include <stdio.h>
#include <unistd.h>

int main() {
	printf("hello, I belong to test_exe_t, my pid is %d\n", getpid());
	while (1) {
		sleep(100);
	}
	printf("good bye!\n");
	return 0;
}
