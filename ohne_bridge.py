#!/usr/bin/python3
import RPi.GPIO as GPIO
import time
import threading

# Pin-Definitionen
TRIG = 7  # GPIO Pin für TRIG des HC-SR04
ECHO = 11  # GPIO Pin für ECHO des HC-SR04

# GPIO-Modus und Pin-Konfiguration
GPIO.setmode(GPIO.BOARD)
GPIO.setup(TRIG, GPIO.OUT)
GPIO.setup(ECHO, GPIO.IN)

# Wasserstandskonfiguration
MAX_WATER_LEVEL = 30.0  # Maximaler Wasserstand in cm
CRITICAL_WATER_LEVEL = 80.0  # Kritischer Wasserstand in Prozent
SAFE_WATER_LEVEL = 50.0  # Sicherer Wasserstand in Prozent

# Funktion zur Distanzmessung mit dem HC-SR04
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

# Hauptfunktion zur Distanzmessung und Wasserstandsüberwachung
def measure_distance():
    while True:
        distance = get_distance()
        print(f"Distance: {distance:.2f} cm")
        time.sleep(1)

# Das Hauptprogramm startet den Mess-Thread und enthält eine Schleife für weitere Logik.
# Bei Beendigung des Programms werden die GPIO-Pins sauber zurückgesetzt.
try:
    # Warten bis sich der Sensor stabilisiert hat
    GPIO.output(TRIG, GPIO.LOW)
    print("Waiting for sensor to settle")
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
