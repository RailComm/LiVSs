

xlrd3
=====

**DEVELOPMENT STOPPED** - 03.01.2011

I doubt that there will ever be a stable version of xlrd3.

The Python package "xlrd3" is a Python 3 port of "xlrd".

"xlrd3" is 100% API compatible to "xlrd" 0.7.1 (http://pypi.python.org/pypi/xlrd).

Purpose
-------

Provide a library for developers to use to extract data
from Microsoft Excel (tm) spreadsheet files.
It is not an end-user tool.

Maintainers
-----------

* xlrd  -- John Machin, Lingfo Pty Ltd <sjmachin@lexicon.net>
* xlrd3 -- Port to Python 3 and some tests by Manfred Moitzi <mozman@gmx.at>

Licence
-------

BSD-style (see LICENSE.txt)

Dependencies
------------

The package itself is pure Python with no dependencies on modules or packages
outside the standard Python distribution.

Versions of Excel supported
---------------------------

2004, 2003, XP, 2000, 97, 95, 5.0, 4.0, 3.0, 2.1, 2.0.

xlrd/xlrd3 will safely and reliably ignore any of these if present in the file:

* Charts, Macros, Pictures, any other embedded object. WARNING: currently
  this includes embedded worksheets.
* VBA modules
* Formulas (results of formula calculations are extracted, of course).
* Comments
* Hyperlinks

Download URLs
-------------

* http://pypi.python.org/pypi/xlrd3
* http://bitbucket.org/mozman/xlrd3/downloads

Documentation
-------------

http://packages.python.org/xlrd3/ - Sphinx generated HTML docs

or use the original "xlrd" documention at http://www.lexicon.net/sjmachin/xlrd.htm (0.6.1)

replace every "xlrd" with "xlrd3" or use::

  import xlrd3 as xlrd

Acknowledgements
----------------

This package started life as a translation from C into Python
of parts of a utility called "xlreader" developed by David Giffin.

* "This product includes software developed by David Giffin <david@giffin.org>."
* OpenOffice.org has truly excellent documentation of the Microsoft Excel file formats
  and Compound Document file format, authored by Daniel Rentz. See http://sc.openoffice.org
* over a decade of inspiration, support, and interesting decoding opportunities.
* Ksenia Marasanova: sample Macintosh and non-Latin1 files, alpha testing
* Backporting to Python 2.1 was partially funded by Journyx - provider of
  timesheet and project accounting solutions (http://journyx.com/).
* Provision of formatting information in version 0.6.1 was funded by Simplistix Ltd
  (http://www.simplistix.co.uk/)
* a growing list of names; see HISTORY.html feedback, testing, test files, ...
