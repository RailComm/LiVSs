

xlwt3
=====

**DEVELOPMENT STOPPED** - 03.01.2011

I doubt that there will ever be a stable version of xlwt3.

"xlwt3" is the Python 3 port of "xlwt" 0.7.2

"xlwt3" is 100% API compatible to "xlwt" 0.7.2 (http://pypi.python.org/pypi/xlwt)
but all module names changed to lower-case names, and formula parsing related
modules moved to the subpackage 'xlwt3.excel'.

Purpose
-------

Library to create spreadsheet files compatible with MS Excel 97/2000/XP/2003 XLS files,
on any platform, with Python 3.1+

Maintainer
----------

* xlwt  -- John Machin, Lingfo Pty Ltd <sjmachin AT lexicon.net>
* xlwt3 -- Manfred Moitzi, Python 3 port <mozman AT gmx.at>

Licence
-------

BSD-style (see licences.py)

External modules required
-------------------------

The package itself is pure Python with no dependencies on modules or packages
outside the standard Python distribution.

Quick start::

    import xlwt3 as xlwt
    from datetime import datetime

    style0 = xlwt.easyxf('font: name Times New Roman, color-index red, bold on',
	                 num_format_str='#,##0.00')
    style1 = xlwt.easyxf(num_format_str='D-MMM-YY')

    wb = xlwt.Workbook()
    ws = wb.add_sheet('A Test Sheet')

    ws.write(0, 0, 1234.56, style0)
    ws.write(1, 0, datetime.now(), style1)
    ws.write(2, 0, 1)
    ws.write(2, 1, 1)
    ws.write(2, 2, xlwt.Formula("A3+B3"))

    wb.save('example.xls')

Installation
------------

Any OS: Unzip the .zip file into a suitable directory,
chdir to that directory, then do::

    python setup.py install

or::

    pip install xlwt3

Download URLs
-------------

PyPI: http://pypi.python.org/pypi/xlwt3

Bitbucket: https://bitbucket.org/mozman/xlwt3/downloads

Documentation
-------------

http://packages.python.org/xlwt3/ - Sphinx based HTML documentation

or use the original "xlwt" 0.7.2 documention at
https://secure.simplistix.co.uk/svn/xlwt/trunk/xlwt/doc/xlwt.html
and replace every "xlwt"
with "xlwt3" or use::

  import xlwt3 as xlwt

Documentation can be found in the 'doc' directory of the xlwt3 package.
If these aren't sufficient, please consult the code in the
examples directory and the source code itself.

Problems
--------

Try the following in this order:

* Read the source
* Ask a question on http://groups.google.com/group/python-excel/
* E-mail the xlwt maintainer <sjmachin AT lexicon.net>, including
  "[xlwt]" as part of the message subject.
* E-mail the xlwt3 maintainer <mozman AT gmx.at>, including
  "[xlwt]" as part of the message subject.

Acknowledgements
----------------

* xlwt is a fork of the pyExcelerator package, which was developed by
  Roman V. Kiseliov.
* "This product includes software developed by Roman V. Kiseliov <roman AT kiseliov.ru>."
* xlwt uses ANTLR v 2.7.7 to generate its formula compiler.
* a growing list of names; see HISTORY.html: feedback, testing, test files, ...

