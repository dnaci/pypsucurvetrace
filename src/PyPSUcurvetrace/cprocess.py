# This file is part of PyPSUcurvetrace, a toolbox for I/V curve tracing of electronic parts using programmable power supplies.
#
# PyPSUcurvetrace is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# PyPSUcurvetrace is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with PyPSUcurvetrace.  If not, see <http://www.gnu.org/licenses/>.

import argparse
from pathlib import Path
import logging

from PyPSUcurvetrace.read_datafile import read_datafile
from PyPSUcurvetrace.curvetrace_tools import say_hello


# set up logger:
logger = logging.getLogger('extracpreheat')
if not logger.handlers:
    logger.setLevel(logging.DEBUG)
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(levelname)s (%(name)s): %(message)s')
    ch.setFormatter(formatter)
    logger.addHandler(ch)


if __name__ == "__main__":
    cprocess()


def cprocess():
    ################
    # main program #
    ################

    # input arguments:
    parser = argparse.ArgumentParser(description='curveprocess is a Python program to extract and calculate parameters from from PyPSUcurvetrace data files.')
    parser.add_argument('datafiles', nargs='+', help='Names (and paths) of PyPSUcurvetrace data files, can use wildcards.')

    # Say Hello:
    say_hello('curveprocess', 'Extract and calculate parameters from PyPSUcurvetrace data')

    args = parser.parse_args()

    # determine data file(s):
    datafiles = args.datafiles

    # extract preheat data from files and print to console:
    sep = ', '
    print( 'Filename' + sep + 'Label' + sep + 'U0' + sep + 'I0' + sep + 'Uc' + sep + 'Ic' + sep + 'T')
    for i in range(len(datafiles)):
	    d, l, p, u = read_datafile(datafiles[i])
	    print( Path(d.datafile).stem + sep + l + sep + str(p.U0) + sep + str(p.I0) + sep + str(p.Uc) + sep + str(p.Ic) + sep + str(p.T))