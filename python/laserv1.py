# Von links nach rechts
# L01:5 ; L02:6 ; L03:4 ; L04:3 ; L05:7 ; L06:8 ; L11:2 ; L12:1 ; L13:9 ; L14:10 ; L15:11 ; L16 : 12
import smbus2
import time
import RPi.GPIO as GPIO
import pygame
import json
import sys

# select the sound for the harp
SOUNDSELECT = 'pentatonic' # c2maj / pentatonic / drums

# Addresses
TCA9548_ONE_ADD = 0x70
TCA9548_TWO_ADD = 0x74
MCP4725_ADD = 0x60
ADC_ADD = 0x35
BUS = smbus2.SMBus(1)

# Settings
LASER_POWER = 3500  # Set Laser to this value
DIODE_TRIGGER_THRESHOLD = LASER_POWER * 0.1 # if detected laser-power goes down by more than  -> trigger
LASER_MAX = 3650  # Absolute Maximum for Laser Diodes
LASER_BASELINE = 1800  # Start Laser Calibration from this Value
# pairs of laser diode number and according DAC-Number
LASER_MAP = [[1, 1], [1, 0], [0, 3], [0, 2], [0, 0], [0, 1], [0, 4], [0, 5], [1, 2], [1, 3], [1, 4], [1, 5]]
# LASER_MAP = [[1,5],[1,4],[1,3],[1,2],[0,5],[0,4],[0,1],[0,0],[0,2],[0,3],[1,0],[1,1]]
PHOTO_DIODE_MAP = [11, 10, 8, 9, 6, 7, 4, 5, 0, 3, 1, 2]  # photodiodes in sequence corresponding to lasers

# Sound initialisation
pygame.init()
pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=8192)
pygame.mixer.set_num_channels(12)

# global list for keeping track of interrupted lasers
is_interrupted_list = [0] * 12

SOUNDS = []

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


def load_sounds_from_config(config_file):
    with open(config_file, 'r') as file:
        config = json.load(file)
    sounds = {
        key: [pygame.mixer.Sound(sound_file) for sound_file in value]
        for key, value in config.items()
    }
    return sounds


def set_global_variable(param):
    global SOUNDSELECT
    if param == "p":
        SOUNDSELECT = 'pentatonic'
    elif param == "c":
        SOUNDSELECT = "c2maj"
    elif param == "d":
        SOUNDSELECT = "drums"
    # Add more conditions as needed
    else:
        print(f"Unknown option '{param}'. Using default value.")


# Set up MAX11617 for Single-Ended Unipolar mode
def setup_adc():
    setup_command = 0b10000000
    BUS.write_byte(ADC_ADD, setup_command)


def read_adc(channel):
    command = 0b1100001 | (channel << 1)  # single-ended and channel selection bits
    data = BUS.read_i2c_block_data(ADC_ADD, command, 2)
    value = (data[0] << 8 | data[1]) & 0xFFF  # Convert the data to 12-bits
    return value


# Function to write a value to the MCP4725
def write_dac_value(value, tca_nr, tca9548_channel):
    if value > LASER_MAX:
        value = LASER_MAX  # Never exceed Maximum Value or Laser breaks
    if tca_nr == 0:
        GPIO.output(17, GPIO.HIGH)
        GPIO.output(27, GPIO.LOW)
        BUS.write_byte(TCA9548_ONE_ADD, 1 << tca9548_channel)
    if tca_nr == 1:
        GPIO.output(27, GPIO.HIGH)
        GPIO.output(17, GPIO.LOW)
        BUS.write_byte(TCA9548_TWO_ADD, 1 << tca9548_channel)
    value_bytes = [(value >> 4) & 0xFF, (value << 4) & 0xFF]
    BUS.write_i2c_block_data(MCP4725_ADD, 0x40, value_bytes)
    # print(f"{value} to channel {tca9548_channel} - tca_nr {tca_nr}")


def reset_laser():  # set all lasers to 0
    for i in range(6):
        write_dac_value(0, 0, i)
        write_dac_value(0, 1, i)


# feedback loop at what laser power the photo diode reads a certain value
def adjust_laser_power():
    for i in range(12):
        value = 0
        laser_temp = LASER_BASELINE
        while value < LASER_POWER and value < LASER_MAX:
            write_dac_value(laser_temp, LASER_MAP[i][0], LASER_MAP[i][1])
            value = read_adc(PHOTO_DIODE_MAP[i])
            laser_temp = laser_temp + 5
        print(f"laser {i} has value {laser_temp} with value reading {value}")


# print values for debugging
def print_adc_vals():
    for pdiode in PHOTO_DIODE_MAP:
        value = read_adc(pdiode)
        print(f"{value}")
    print("--------")

triggercount = 0

def trigger_sounds():
    global triggercount
    for i, pdiode in enumerate(PHOTO_DIODE_MAP):
        channel = pygame.mixer.Channel(i)
        pdiode_value = read_adc(pdiode)
        if pdiode_value > DIODE_TRIGGER_THRESHOLD and is_interrupted_list[i] == 1:
            channel.play(SOUNDS[i])
            is_interrupted_list[i] = 0
            triggercount=triggercount + 1
        if pdiode_value <= DIODE_TRIGGER_THRESHOLD:
            is_interrupted_list[i] = 1
            #if channel.get_busy():
                #channel.stop()


def start_harp():
    global SOUNDS
    if len(sys.argv) > 1:
        set_global_variable(sys.argv[1])
    else:
        print("No parameter given. Using default values.")

    setup_values()
    reset_laser()
    setup_adc()
    adjust_laser_power()
    sounds = load_sounds_from_config('sounds_config.json')
    SOUNDS = sounds[SOUNDSELECT]
    while 1:
        trigger_sounds()
        time.sleep(0.03)


start_harp()

