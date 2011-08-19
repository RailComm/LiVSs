@ECHO off
REM
REM This will build our LiVSs program into an EXE on the windows platform.
REM Dependencies:
REM    - CXFreeze (http://cx-freeze.sourceforge.net/)
REM    - Python3.2 (http://python.org/download/)

CD src
@python setup.py build -b ../build
