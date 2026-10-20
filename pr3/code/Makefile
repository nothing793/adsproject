CC = gcc
CFLAGS = -std=c99 -O2 -Wall -Wextra -Wpedantic

.PHONY: all clean
all: fence

fence: main.c fence.c fence.h sat.c sat.h
	$(CC) $(CFLAGS) main.c fence.c sat.c -o fence

clean:
	$(RM) fence fence.exe
