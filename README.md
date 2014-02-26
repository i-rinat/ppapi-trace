PPAPI trace utility
===================

Wrapping every function into another, which prints its name and then
calls original one.

It's required to disable sandbox to get trace output, which is going to stdout:
`chromium --no-sandbox --ppapi-flash-path=/path/to/libppapitrace.so`
