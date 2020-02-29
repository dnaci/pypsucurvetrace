"""
Python class to control Voltcraft PPS power supplies
(This file was forked from https://github.com/strawlab/phidgets/tree/master/VoltCraft) 
"""

import serial
import sys
import math
import warnings
import time

# The model can be identified by the maximum voltage and maximum current.
# But this is probably one of the weirdest naming-schemes I've seen... 
# It just doesn't really make sense...
# Please confirm the modelnumbers.

PPS_MODELS = { 	       (36.2,  7.0) : "PPS11360", # confirmed
		       (60.0,  2.5) : "PPS11603", # not confirmed yet
		       (18.0, 20.0) : "PPS13610", # not confirmed yet
		       (36.2, 12.0) : "PPS16005", # confirmed
		       (60.0,  5.0) : "PPS11815", # not confirmed yet
		       (18.2,  12.0): "PPS11810"  # added MB 2019-01-10
		     }

PPS_TIMEOUT = 2.0

def _pps_debug(s):
	sys.stdout.write(s)
	sys.stdout.flush()

# VOLTCRAFT:
#    .output(state)
#    .voltage(voltage)
#    .current(current)
#    .reading()
#    .VMIN
#    .VMAX
#    .IMAX
#    .VRES
#    .IRES
#    .MAXSETTLETIME
#    .SETTLEPOLLTIME
#    .MODEL


class VOLTCRAFT(object):
	"""
	Class for VOLTCRAFT power supply
	"""

	def __init__(self, port, reset=False, prom=None, debug=False, exclusiveaccess=True):
		'''
		PSU(port)
		port : serial port (string, example: port = '/dev/serial/by-id/XYZ_123_abc')
		debug: flag for debugging info (bool)
		'''

		# open and configure serial port:
		from pkg_resources import parse_version
		if parse_version(serial.__version__) >= parse_version('3.3') :
			# open port with exclusive access:
			self._Serial = serial.Serial(port, timeout=PPS_TIMEOUT, exclusive = True)

		else:
			# open port (can't ask for exclusive access):
			self._Serial = serial.Serial(port, timeout=PPS_TIMEOUT)

		self._Serial.flushInput()
		self._Serial.flushOutput()
		self._debug = bool(debug)

		try:
		    model = self.limits()
		    self.MODEL = PPS_MODELS[model]
		    self.VMAX = model[0]
		    self.IMAX = model[1]
		except serial.SerialTimeoutException:
		    raise RuntimeError("No Voltcraft PPS powersupply "
				       "connected to %s" % port)
		except KeyError:
		    raise RuntimeError("Unkown Voltcraft PPS model with "
				       "max V: %f, I: %f" % model)
		if bool(reset):
		    self.output(0)
		    self.voltage(0)
		    self.current(0)
		if not (prom is None):
		    self.use_preset(prom)

		# Determined experimentally with Voltcraft PPS-16005:
		self.VMIN = 0.9
		self.VRES = 0.12
		self.IRES = 0.02
		self.MAXSETTLETIME = 5
		self.SETTLEPOLLTIME = 0.2
		self.PMAX = math.floor(self.VMAX * self.IMAX)


	def _query(self, cmd, attempt = 0):
		"""
		tx/rx to/from PS
		"""
		attempt = attempt + 1
		if attempt > 1:
			print ('*** Retrying (attempt ' + str(attempt) + ')...')
		if attempt > 10:
			raise RuntimeError('Voltcraft PSU does not respond to ' + cmd + '. Giving up...')

		if self._debug: _pps_debug("PPS <- %s<CR>\n" % cmd)
		self._Serial.write((cmd + '\r').encode())

		b = []
		retry = False
		if self._debug: _pps_debug("PPS -> ")

		# read answer byte by byte:
		answerOK = False
		while True:
			
			b.append(self._Serial.read(1).decode('utf-8'))
			if self._debug: _pps_debug(b[-1].replace('\r', '<CR>'))

			# if there was no answer:
			if b[-1] == "":
				### raise serial.SerialTimeoutException()
				print('*** No response from Voltcraft PSU! Command: ' + cmd)
				break

			# if last three entries are OK\r, the answer is complete:
			if b[-3:] == list("OK\r"):
				answerOK = True
				break

		if self._debug: _pps_debug('\n')

		if not answerOK:
			self._Serial.flushOutput()			
			time.sleep(0.2)
			self._Serial.flushInput()
			time.sleep(0.2)			
			b = self._query(cmd,attempt)

		else:
			b = "".join(b[:-4])

		return b


	def limits(self):
		"""
		get maximum voltage and current from PS
		"""
		s = self._query("GMAX")
		self.IMULT = 100. if s == "362700" else 10.
		V = int(s[0:3]) / 10.
		I = int(s[3:6]) / self.IMULT
		return (V, I)

	def output(self, state):
		"""
		enable/disable the PS output
		"""
		state = int(not bool(state))
		self._query("SOUT%d" % state)

	def voltage(self, voltage):
		"""
		set voltage: silently saturates at VMIN and VMAX
		"""
		voltage = max(min(int(float(voltage) * 10), int(self.VMAX*10)), self.VMIN)
		self._query("VOLT%03d" % voltage)

	def current(self, current):
		"""
		set current: silently saturates at 0 and IMAX
		"""
		current = max(min(int(float(current) * self.IMULT), int(self.IMAX * self.IMULT)), 0)
		self._query("CURR%03d" % current)

	def reading(self):
		"""
		read applied output voltage and current and if PS is in "CV" or "CC" mode
		"""
		s = self._query("GETD")
		V = int(s[0:4]) / 100.
		I = int(s[4:8]) / 100.
		MODE = bool(int(s[8]))
		return (V, I, ("CV", "CC")[MODE])