@ECHO off
REM
REM Generates the documentation for LiVSs. If you are familiar with 
REM JavaDocs, the pydocs generated will be easy to read.
REM
REM Dependencies:
REM   - PyDoc (should come with the Python3.2 install)
REM

REM SET UP DOCUMENTATION DIR
MD "doc\pydoc"

REM CLEAN DOCUMENTATION DIR
cd doc\pydoc
ECHO Y | DEL *.html
CD ..\..

REM MAKE LSLIB DOCUMENTATION
CD .\src
@python C:\Python32\Lib\pydoc.py -w .\
MOVE .\*.html ..\doc\pydoc\.