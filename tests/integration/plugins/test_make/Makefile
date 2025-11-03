CC = gcc
CFLAGS = -Wall

# Allow MESSAGE and TARGET to be set from command line
ifdef MESSAGE
CFLAGS += -DMESSAGE=\"$(MESSAGE)\"
endif

ifdef TARGET
CFLAGS += -DTARGET=\"$(TARGET)\"
endif

all: hello

hello: hello.c
	$(CC) $(CFLAGS) -o hello hello.c

install:
	mkdir -p $(DESTDIR)/bin
	cp hello $(DESTDIR)/bin/

clean:
	rm -f hello

.PHONY: all install clean
