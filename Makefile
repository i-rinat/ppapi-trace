PLUGINNAME=ppapitrace
CC=gcc

all: pepper_proxy.c build/trace-wrappers.c
	@echo compiling plugin
	@$(CC) -Wall -O -shared -fPIC -I. -Ibuild/ pepper_proxy.c -o build/lib${PLUGINNAME}.so

build/trace-wrappers.c: gen.py build/prep-stamp
	$(shell mkdir build 2> /dev/null || true)
	@echo generating trace-wrappers.c
	@python gen.py > build/trace-wrappers.c
	@touch build/prep-stamp

build/prep-stamp:
	@echo preprocessing PPAPI header files
	$(shell mkdir build 2> /dev/null || true)
	$(shell sh -c 'find ppapi/ -type f -name "pp[bp]_*.h" | while read line; do bname=`basename $$line`; $(CC) -E -include no-extensions.h -include cpp-compat.h -I. $$line | grep -v ^# > build/$$bname.prep; done')

.PHONY: build/prep-stamp
