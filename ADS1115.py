from time import sleep_ms
from machine import Pin, I2C

#    CONVERSION DELAY (in mS)
ADS1115_CONVERSIONDELAY =8

#    POINTER REGISTER
REG_MASK        = 0x03
REG_CONVERT     = 0x00
REG_CONFIG      = 0x01
REG_LOWTHRESH   = 0x02
REG_HITHRESH    = 0x03

#    REG_CONFIG REGISTER
OS_REG_MASK      = 0x8000
OS_SINGLE    = 0x8000  # Write: Set to start a single-conversion
OS_BUSY      = 0x0000  # Read: Bit = 0 when conversion is in progress
OS_NOTBUSY   = 0x8000  # Read: Bit = 1 when device is not performing a conversion

MUX_REG_MASK     = 0x7000
MUX_DIFF_0_1 = 0x0000  # Differential P = AIN0, N = AIN1 (default)
MUX_DIFF_0_3 = 0x1000  # Differential P = AIN0, N = AIN3
MUX_DIFF_1_3 = 0x2000  # Differential P = AIN1, N = AIN3
MUX_DIFF_2_3 = 0x3000  # Differential P = AIN2, N = AIN3
MUX_SINGLE_0 = 0x4000  # Single-ended AIN0
MUX_SINGLE_1 = 0x5000  # Single-ended AIN1
MUX_SINGLE_2 = 0x6000  # Single-ended AIN2
MUX_SINGLE_3 = 0x7000  # Single-ended AIN3

PGA_REG_MASK     = 0x0E00
PGA_6_144V   = 0x0000  # +/-6.144V range = Gain 2/3
PGA_4_096V   = 0x0200  # +/-4.096V range = Gain 1
PGA_2_048V   = 0x0400  # +/-2.048V range = Gain 2 (default)
PGA_1_024V   = 0x0600  # +/-1.024V range = Gain 4
PGA_0_512V   = 0x0800  # +/-0.512V range = Gain 8
PGA_0_256V   = 0x0A00  # +/-0.256V range = Gain 16

MODE_REG_MASK    = 0x0100
MODE_CONTIN  = 0x0000  # Continuous conversion mode
MODE_SINGLE  = 0x0100  # Power-down single-shot mode (default)

DR_REG_MASK      = 0x00E0  
DR_8SPS      = 0x0000  # 8 samples per second
DR_16SPS     = 0x0020  # 16 samples per second
DR_32SPS     = 0x0040  # 32 samples per second
DR_64SPS     = 0x0060  # 64 samples per second
DR_128SPS    = 0x0080  # 128 samples per second (default)
DR_250SPS    = 0x00A0  # 250 samples per second
DR_475SPS    = 0x00C0  # 475 samples per second
DR_869SPS    = 0x00E0  # 860 samples per second

CMODE_REG_MASK   = 0x0010
CMODE_TRAD   = 0x0000  # Traditional comparator with hysteresis (default)
CMODE_WINDOW = 0x0010  # Window comparator

CPOL_REG_MASK    = 0x0008
CPOL_ACTVLOW = 0x0000  # ALERT/RDY pin is low when active (default)
CPOL_ACTVHI  = 0x0008  # ALERT/RDY pin is high when active

CLAT_REG_MASK    = 0x0004  # Determines if ALERT/RDY pin latches once asserted
CLAT_NONLAT  = 0x0000  # Non-latching comparator (default)
CLAT_LATCH   = 0x0004  # Latching comparator

CQUE_REG_MASK    = 0x0003
CQUE_1CONV   = 0x0000  # Assert ALERT/RDY after one conversions
CQUE_2CONV   = 0x0001  # Assert ALERT/RDY after two conversions
CQUE_4CONV   = 0x0002  # Assert ALERT/RDY after four conversions
CQUE_NONE    = 0x0003  # Disable the comparator and put ALERT/RDY in high state (default)


GAIN_TWOTHIRDS    = PGA_6_144V
GAIN_ONE          = PGA_4_096V
GAIN_TWO          = PGA_2_048V
GAIN_FOUR         = PGA_1_024V
GAIN_EIGHT        = PGA_0_512V
GAIN_SIXTEEN      = PGA_0_256V

DEVID = 0x48

class ADS1115(object):

	def __init__(self, i2c_devid=DEVID):
		self._addr = i2c_devid
		self.i2c = I2C(scl=Pin(5), sda=Pin(4), freq=400000) 
		self.cbuffer = bytearray(2)
		self._conversionDelay = ADS1115_CONVERSIONDELAY
		self._bitShift = 0
		self._gain = GAIN_TWOTHIRDS # +/- 6.144V range (limited to VDD +0.3V max!)

	def write_register(self, reg, value):
		"""Writes 16-bits to the specified destination register"""
		# print ('reg {0:4x}'.format(reg))
		# print ('value {0:4x}'.format(value))
		buf = bytearray(2)
		msb = value >> 8
		lsb = value & 0xFF
		buf[0] = msb
		buf[1] = lsb
		self.i2c.writeto_mem(self._addr, reg, buf) # write 2 bytes to self._addr, register		

	def read_register(self, reg):
		"""Reads 16-bits from the specified destination register"""
		self.cbuffer = self.i2c.readfrom_mem(self._addr, reg, 2) # read 2 bytes from self._addr, register
		value = (self.cbuffer[0]<<8) +self.cbuffer[1]
		return value

	def set_gain(self, gain):
		"""Sets the gain and input voltage range"""
		self._gain = gain

	def get_gain(self):
		"""Gets a gain and input voltage range"""
		return self._gain

	def read_adc(self, channel, type = 'single'):
		"""Gets a single-ended, or differential ADC reading from the specified channel"""
		if type == 'single':
			if channel > 3:
				return 0
		else:
			if channel >1:
				return 0
	  
		# Start with default values
		config  = CQUE_NONE     # Disable the comparator (default val)
		config |= CLAT_NONLAT   # Non-latching (default val)
		config |= CPOL_ACTVLOW  # Alert/Rdy active low   (default val)
		config |= CMODE_TRAD    # Traditional comparator (default val)
		config |= DR_128SPS    # 1600 samples per second (default)
		config |= MODE_SINGLE   # Single-shot mode (default)

		# Set PGA/voltage range
		config |= self._gain

		if type == 'single':
			# Set single-ended input channel
			if channel == 0:
				config |= MUX_SINGLE_0
			elif channel == 1:
				config |= MUX_SINGLE_1
			elif channel == 2:
				config |= MUX_SINGLE_2
			elif channel == 3:
				config |= MUX_SINGLE_3
		else:
			# Differential
			if channel == 0:
				config |= MUX_DIFF_0_1         # AIN0 = P, AIN1 = N
			elif channel == 1:
				config |= MUX_DIFF_2_3         # AIN2 = P, AIN3 = N

		# Set 'start single-conversion' bit
		config |= OS_SINGLE

		# Write config register to the ADC
		self.write_register(REG_CONFIG, config)

		# Wait for the conversion to complete
		sleep_ms(self._conversionDelay)

		# Read the conversion results
		return self.read_register(REG_CONVERT)

	def adc_continuous(self, channel, type = 'single'):
		"""Starts a continuous single-ended, or differential ADC reading from the specified channel"""
		if type == 'single':
			if channel > 3:
				return 0
		else:
			if channel >1:
				return 0
	  
		# Start with default values
		config  = CQUE_NONE     # Disable the comparator (default val)
		config |= CLAT_NONLAT   # Non-latching (default val)
		config |= CPOL_ACTVLOW  # Alert/Rdy active low   (default val)
		config |= CMODE_TRAD    # Traditional comparator (default val)
		config |= DR_128SPS     # 1600 samples per second (default)
		config |= MODE_CONTIN   # Continuous mode

		# Set PGA/voltage range
		config |= self._gain

		if type == 'single':
			# Set single-ended input channel
			if channel == 0:
				config |= MUX_SINGLE_0
			elif channel == 1:
				config |= MUX_SINGLE_1
			elif channel == 2:
				config |= MUX_SINGLE_2
			elif channel == 3:
				config |= MUX_SINGLE_3
		else:
			# Differential
			if channel == 0:
				config |= MUX_DIFF_0_1         # AIN0 = P, AIN1 = N
			elif channel == 1:
				config |= MUX_DIFF_2_3         # AIN2 = P, AIN3 = N

		# Write config register to the ADC
		self.write_register(REG_CONFIG, config)

	def start_comparator_single_ended(self, channel, threshold):
		"""Sets up the comparator to operate in basic mode, causing the
		ALERT/RDY pin to assert (go from high to low) when the ADC
		value exceeds the specified threshold.
		This will also set the ADC in continuous conversion mode."""
							
		# Start with default values
		config  = CQUE_1CONV    # Comparator enabled and asserts on 1 match
		config |= CLAT_LATCH    # Latching mode
		config |= CPOL_ACTVLOW  # Alert/Rdy active low   (default val)
		config |= CMODE_TRAD    # Traditional comparator (default val)
		config |= DR_128SPS     # 128 samples per second (default)
		config |= MODE_CONTIN   # Continuous conversion mode
						
		# Set PGA/voltage range
		config |= self._gain
						
		# Set single-ended input channel
		if channel == 0:
			config |= MUX_SINGLE_0
		elif channel == 1:
			config |= MUX_SINGLE_1
		elif channel == 2:
			config |= MUX_SINGLE_2
		elif channel == 3:
			config |= MUX_SINGLE_3
	  
		# Set the high threshold register
		# Shift 12-bit results left 4 bits for the ADS1015
		self.write_register(REG_HITHRESH, threshold)

		# Write config register to the ADC
		write_register(REG_CONFIG, config)

	def get_last_conversion_results(self):
		"""In order to clear the comparator, we need to read the
		conversion results.  This function reads the last conversion
		results without changing the config value."""

		# Wait for the conversion to complete
		# sleep_ms(self._conversionDelay)

		# Read the conversion results
		return self.read_register(REG_CONVERT)
