#Von links nach rechts
#L01:5 ; L02:6 ; L03:4 ; L04:3 ; L05:7 ; L06:8 ; L11:2 ; L12:1 ; L13:9 ; L14:10 ; L15:11 ; L16 : 12
import smbus2
import time
import RPi.GPIO as GPIO

# Addresses
TCA9548_ONE_ADD = 0x70
TCA9548_TWO_ADD = 0x74
MCP4725_ADD = 0x60
ADC_ADD = 0x35
bus = smbus2.SMBus(1)

# Settings
LASER_POWER = 2000
LASER_MAX = 3200
LASER_MAP = [[1,1],[1,0],[0,3],[0,2],[0,0],[0,1],[0,4],[0,5],[1,2],[1,3],[1,4],[1,5]]
#LASER_MAP = [[1,5],[1,4],[1,3],[1,2],[0,5],[0,4],[0,1],[0,0],[0,2],[0,3],[1,0],[1,1]]
PHOTO_DIODE_MAP = [11,10,8,9,6,7,4,5,0,3,1,2]

def setup_values():
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)  # Use Broadcom pin-numbering scheme
    GPIO.setup(17, GPIO.OUT)
    GPIO.setup(27, GPIO.OUT)
    GPIO.output(17, GPIO.LOW)
    GPIO.output(27, GPIO.LOW)
    time.sleep(0.5)
    GPIO.output(17, GPIO.HIGH)
    GPIO.output(27, GPIO.HIGH)


def setup_adc():
    # Set up MAX11617 for Single-Ended Unipolar mode
    setup_command = 0b10000000
    bus.write_byte(ADC_ADD, setup_command)


def read_adc(channel):
    time.sleep(0.01)
    command = 0b1100001 | (channel << 1 )  # Example command with single-ended and channel selection bits
    data = bus.read_i2c_block_data(ADC_ADD, command, 2)
    value = (data[0] << 8 | data[1]) & 0xFFF # Convert the data to 12-bits
    return value


# Function to write a value to the MCP4725
def write_dac_value(value, TCA_NR, TCA9548_CHANNEL):
    if value > LASER_MAX :
        value = LASER_MAX # Never exceed Maximum Value or Laser breaks
    if (TCA_NR == 0):
        GPIO.output(17, GPIO.HIGH)
        GPIO.output(27, GPIO.LOW)
        bus.write_byte(TCA9548_ONE_ADD, 1 << TCA9548_CHANNEL)
    if (TCA_NR == 1):
        GPIO.output(27, GPIO.HIGH)
        GPIO.output(17, GPIO.LOW)
        bus.write_byte(TCA9548_TWO_ADD, 1 << TCA9548_CHANNEL)
    value_bytes = [(value >> 4) & 0xFF, (value << 4) & 0xFF]
    bus.write_i2c_block_data(MCP4725_ADD, 0x40, value_bytes)
    #print(f"{value} to channel {TCA9548_CHANNEL} - TCA_NR {TCA_NR}")


def read_adc_vals():
    for channel in range(12):
        value = read_adc(channel)
        print(f"{value}")
    print("--------")


def reset_laser():
    for i in range (6):
        write_dac_value(0,0,i)
        write_dac_value(0,1,i)


def adjust_laser_power():
    for i in range (12):
        value = 0
        laser_temp = 2000
        while ((value < LASER_POWER) and (value < LASER_MAX)):
            write_dac_value(laser_temp, LASER_MAP[i][0],LASER_MAP[i][1])
            value = read_adc(PHOTO_DIODE_MAP[i])
            laser_temp = laser_temp + 5
        print(f"laser {i} has value {laser_temp} with value reading {value}")


def mainfun():
    setup_values()
    reset_laser()
    setup_adc()
    #adjust_laser_power()

    time.sleep(1)

mainfun()


