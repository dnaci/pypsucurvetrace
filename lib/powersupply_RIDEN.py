"""
Python class to control RIDEN (RUIDEN) RDxxxx power supplies
"""

# Useful information about RIDEN Modbus registers and other details: https://github.com/ShayBox/Riden

### import serial
### import sys
import time
import minimalmodbus
import logging

# set up logger:
logger = logging.getLogger('powersupply_RIDEN')
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(levelname)s (%(name)s): %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)


# Python dictionary of known KORAD (RND) power supply models (Vmin,Vmax,Imax,Pmax,Vresolution,Iresolution,VoffsetMax,IoffsetMax,MaxSettleTime)

RIDEN_SPECS = {
		"RD6006":	( 0.0, 60.0,  6.0,  360,  0.001,  0.001,  0.0, 0.0, 0.5 ) , # not confirmed
		"RD6006P":	( 0.0, 60.0,  6.0,  360,  0.001,  0.0001, 0.0, 0.0, 0.5 ) , # not confirmed, currently testing
		"RD6012":	( 0.0, 60.0, 12.0,  720,  0.001,  0.001,  0.0, 0.0, 0.5 ) , # not confirmed
		"RD6012P":	( 0.0, 60.0, 12.0,  720,  0.001,  -1,     0.0, 0.0, 0.5 ) , # not confirmed -- IRES is not constant!
}

RIDEN_TIMEOUT = 1.0

MAX_COMM_ATTEMPTS = 10

def _RIDEN_debug(s):
	sys.stdout.write(s)
	sys.stdout.flush()

# RIDEN:
#    .output(state)
#    .voltage(voltage)
#    .current(current)
#    .reading()
#    .VMIN
#    .VMAX
#    .IMAX
#    .VRESSET
#    .IRESSET
#    .VRESREAD
#    .IRESREAD
#    .VOFFSETMAX
#    .VOFFSETMAX
#    .IOFFSETMAX
#    .MAXSETTLETIME
#    .READIDLETIME
#    .MODEL

class RIDEN(object):
	"""
	Class for RIDEN (RUIDEN) power supply
	"""

	def __init__(self, port, baud=115200, debug=False):
		'''
		PSU(port)
		port : serial port (string, example: port = '/dev/serial/by-id/XYZ_123_abc')
		baud : baud rate of serial port (check the settings at the RD PSU unit)
		debug: flag for debugging info (bool)
		'''
		
		self._debug = bool(debug)
		
		# open and configure ModBus/serial port:
		try:
		    self._instrument = minimalmodbus.Instrument(port=port, slaveaddress=1)
		    self._instrument.serial.baudrate = baud
		    self._instrument.serial.timeout = 1.0
		    time.sleep(0.2) # wait a bit unit the port is really ready
		except:
		    raise RuntimeError('Could not connect to RIDEN powersupply at ' + port)


		# determine model / type:
		try:
		    mdl = self._get_register(0)
		    if 60060 <= mdl <= 60064:
		        # RD6006
		        self.MODEL = 'RD6006'
                
		    elif mdl == 60065:
		        # RD6006P
		        self.MODEL = 'RD6006P'
                
		    elif 60120 <= self.id <= 60124:
		        # RD6012
		        self.MODEL = 'RD6012'
            
		    elif 60125 <= self.id <= 60129:
		        # RD6012P
		        self.MODEL = 'RD6012P'
		        # IRES is not constant!
		        logger.warning ( 'RIDEN ' + self.MODEL + ' may have variable IRES or VRES -- this is untested and may not work!' ) # see https://github.com/ShayBox/Riden
                
		    elif 60180 <= self.id <= 60189:
		        # RD6018
		        self.MODEL = 'RD6018'
            
		    else:
		        # unknown RD model:
		        logger.warning ( 'Unknown RIDEN model ID: ' + mdl )
		        self.MODEL = '?????'

		    self.VMIN          = RIDEN_SPECS[self.MODEL][0]
		    self.VMAX          = RIDEN_SPECS[self.MODEL][1]
		    self.IMAX          = RIDEN_SPECS[self.MODEL][2]
		    self.PMAX          = RIDEN_SPECS[self.MODEL][3]
		    self._VRES         = RIDEN_SPECS[self.MODEL][4]
		    self._IRES         = RIDEN_SPECS[self.MODEL][5]
		    self.VRESSET       = self._VRES
		    self.VRESREAD      = self._VRES
		    self.IRESSET       = self._IRES
		    self.IRESREAD      = self._IRES
		    self.VOFFSETMAX    = RIDEN_SPECS[self.MODEL][6]
		    self.IOFFSETMAX    = RIDEN_SPECS[self.MODEL][7]
		    self.MAXSETTLETIME = RIDEN_SPECS[self.MODEL][8]
		    self.READIDLETIME  = self.MAXSETTLETIME/50

		except KeyError:
		    raise RuntimeError('Unknown RIDEN powersupply type/model ' + self.MODEL)
		except:
		    raise RuntimeError('Could not determine RIDEN powersupply type/model')


	def _set_register(self, register, value):
	    k = 1
	    while k <= MAX_COMM_ATTEMPTS:
	        try:
        	    self._instrument.write_register(register, int(value))
        	    break # break from the loop if communication was successful
        	except:
        	    k += 1
        	    pass # keep trying
	    if k > MAX_COMM_ATTEMPTS:
	        raise RuntimeError('Communication with RIDEN ' + self.MODEL + ' at ' + self._instrument.serial.port + ' failed.')
            

	def _get_register(self, register):
	    value = None
	    k = 1
	    while k <= MAX_COMM_ATTEMPTS:
	        try:
        	    value = self._instrument.read_register(register)
        	    break # break from the loop if communication was successful
	        except:
        	    k += 1
        	    pass # keep trying
	    if k > MAX_COMM_ATTEMPTS:
	        raise RuntimeError('Communication with RIDEN ' + self.MODEL + ' at ' + self._instrument.serial.port + ' failed.')
 
	    return value


	def output(self, state):
		"""
		enable/disable the PS output
		"""
		state = int(bool(state))
		self._set_register(18, state)


	def voltage(self, voltage):
		"""
		set voltage: silently saturates at VMIN and VMAX
		"""
		if voltage > self.VMAX:
			voltage = self.VMAX
		if voltage < self.VMIN:
			voltage = self.VMIN
		self._set_register(8, round(voltage/self._VRES))
		

	def current(self, current):
		"""
		set current: silently saturates at IMIN and IMAX
		"""
		if current > self.IMAX:
			current = self.IMAX
		if current < 0.0:
			current = 0.0
		self._set_register(9, round(current/self._IRES))


	def reading(self):
		"""
		read applied output voltage and current and if PS is in "CV" or "CC" mode
		"""
		
		# read voltage:
		V = self._get_register(10) * self._VRES

		# read current:
		I = self._get_register(11) * self._IRES

		# read CV/CC:
		if self._get_register(17) == 0:
		    S = 'CV'
		else:
		    S = 'CC'

		return (V, I, S)
