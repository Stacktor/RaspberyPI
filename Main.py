import time
import RPi.GPIO as GPIO
import PyFiglet

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

TRIG = 4
ECHO = 17

GPIO.setup(TRIG, GPIO.OUT)
GPIO.setup(ECHO, GPIO.IN)

GPIO.output(TRIG, False)
time.sleep(2)

print('[press ctrl+c to end the script]')

try:  # Main program loop
    while True:
        GPIO.output(TRIG, True)
        time.sleep(0.00001)
        GPIO.output(TRIG, False)

        while GPIO.input(ECHO) == 0:
            pulse_start = time.time()

        while GPIO.input(ECHO) == 1:
            pulse_end = time.time()

        pulse_duration = pulse_end - pulse_start
        distance = pulse_duration * 17150
        distance = round(distance, 2)

        print('Distance is {} cm'.format(distance))
        time.sleep(2)

# Scavenging work after the end of the program
except KeyboardInterrupt:
    print('Script end!')

finally:
    GPIO.cleanup()