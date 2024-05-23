#!/usr/bin/python3
import RPi.GPIO as GPIO
import time
import threading
from phue import Bridge
from pushover import Client

# Pin-Definitionen und Philips Hue Bridge
TRIG = 7
ECHO = 11
bridge_ip = '192.168.0.137'
b = Bridge(bridge_ip)
b.connect()

pushover_user_key = 'ua9k2jykcr83sxapyg8of9w33hzf9o'
pushover_api_token = 'a4naf84gen6td7yyw21tn7s5qn7yho'

client = Client(pushover_user_key, api_token=pushover_api_token)

GPIO.setmode(GPIO.BOARD)
GPIO.setup(TRIG, GPIO.OUT)
GPIO.setup(ECHO, GPIO.IN)

MAX_WATER_LEVEL = 30.0  # Maximaler Wasserstand in cm
CRITICAL_WATER_LEVEL = 80.0  # Kritischer Wasserstand in Prozent
SAFE_WATER_LEVEL = 50.0  # Sicherer Wasserstand in Prozent

pumpe_eingeschaltet = False

def get_distance():
    GPIO.output(TRIG, True)
    time.sleep(0.00001)
    GPIO.output(TRIG, False)

    while GPIO.input(ECHO) == 0:
        start_time = time.time()
    
    while GPIO.input(ECHO) == 1:
        end_time = time.time()

    duration = end_time - start_time
    distance = (duration * 34300) / 2
    return distance

def control_pump(turn_on):
    global pumpe_eingeschaltet
    lights = b.get_light_objects('name')
    pump_light = lights['Pumpe']

    if turn_on and not pumpe_eingeschaltet:
        pump_light.on = True
        pumpe_eingeschaltet = True
    elif not turn_on and pumpe_eingeschaltet:
        pump_light.on = False
        pumpe_eingeschaltet = False

def send_notification(message):
    client.send_message(message, title="Wasserstand Warnung")

def measure_distance():
    global pumpe_eingeschaltet
    while True:
        distance = get_distance()
        water_level_percentage = (MAX_WATER_LEVEL - distance) / MAX_WATER_LEVEL * 100
        
        if water_level_percentage >= CRITICAL_WATER_LEVEL:
            control_pump(True)
            send_notification(f"Wasserstand kritisch: {water_level_percentage:.2f}%")
            time.sleep(5)
        elif water_level_percentage < SAFE_WATER_LEVEL and pumpe_eingeschaltet:
            control_pump(False)
        
        print(f"Water Level: {water_level_percentage:.2f}%")
        time.sleep(1)

def everythreehour():
    while True:
        send_notification("Akuteller Wasserstand: {water_level_percentage:.2f}%")
        time.sleep(10)


try:
    # Warten bis sich der Sensor stabilisiert hat
    GPIO.output(TRIG, GPIO.LOW)
    print("Waiting for sensor to settle")
    everythreehour = True
    time.sleep(2)

    # Starten des Mess-Threads
    measurement_thread = threading.Thread(target=measure_distance)
    measurement_thread.start()


    # Hauptprogramm kann hier fortgesetzt werden
    while True:
        # Hier kann weitere Logik hinzugefügt werden
        time.sleep(10)  # Beispielhafte Wartezeit

finally:
    GPIO.cleanup()
