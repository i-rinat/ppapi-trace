PLUGINNAME=ppapitrace
CC=gcc

all: pepper_proxy.c out/trace-wrappers.c
	@echo compiling plugin
	@$(CC) -Wall -O -shared -fPIC -I. -Iout/ pepper_proxy.c -o out/lib${PLUGINNAME}.so

out/trace-wrappers.c: gen.py out/prep-stamp
	$(shell mkdir out 2> /dev/null || true)
	@echo generating trace-wrappers.c
	@python gen.py > out/trace-wrappers.c
	@touch out/prep-stamp

out/prep-stamp:
	@echo preprocessing PPAPI header files
	$(shell mkdir out 2> /dev/null || true)
	$(shell sh -c 'find ppapi/ -type f -name "pp[bp]_*.h" | while read line; do bname=`basename $$line`; $(CC) -E -include no-extensions.h -include cpp-compat.h -I. $$line | grep -v ^# > out/$$bname.prep; done')

.PHONY: out/prep-stamp
