from cx_Freeze import setup, Executable
  
#
# Fairly bleak setup script. 
#
# TODO: update it with the most recent information and trick it out.
#
 
includes = ["re"]
executable = Executable("livss.py")
 
setup(
    name = "LiVSs",
	author = "Alexander Dean",
    version = "0.5",
	license = "Modified BSD",
    description = "A small L10n and i18n helper",
    options = {"build_exe":{"includes":includes}},
    executables = [ executable ]
    )