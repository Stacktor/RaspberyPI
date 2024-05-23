# Importieren der erforderlichen Bibliotheken
import RPi.GPIO as GPIO
import time
import threading
from phue import Bridge
from pushover import Client

# Das Programm überwacht den Wasserstand in einem Eimer mithilfe eines Raspberry Pi 4,
# eines HC-SR04 Ultraschallsensors und einer Philips Hue Steckdose.
# Die GPIO-Pins für den Ultraschallsensor werden konfiguriert, und es wird eine Verbindung
# zur Philips Hue Bridge und zum Pushover-Dienst hergestellt, um Warnungen zu senden.

# Pin-Definitionen und Philips Hue Bridge
TRIG = 7  # GPIO Pin für TRIG des HC-SR04
ECHO = 11  # GPIO Pin für ECHO des HC-SR04
bridge_ip = '192.168.0.137'  # IP-Adresse der Philips Hue Bridge
b = Bridge(bridge_ip)
b.connect()

# Pushover-API-Schlüssel und Token
pushover_user_key = 'ua9k2jykcr83sxapyg8of9w33hzf9o'
pushover_api_token = 'a4naf84gen6td7yyw21tn7s5qn7yho'
client = Client(pushover_user_key, api_token=pushover_api_token)

# GPIO-Modus und Pin-Konfiguration
GPIO.setmode(GPIO.BOARD)
GPIO.setup(TRIG, GPIO.OUT)
GPIO.setup(ECHO, GPIO.IN)

# Wasserstandskonfiguration
MAX_WATER_LEVEL = 30.0  # Maximaler Wasserstand in cm
CRITICAL_WATER_LEVEL = 80.0  # Kritischer Wasserstand in Prozent
SAFE_WATER_LEVEL = 50.0  # Sicherer Wasserstand in Prozent

pumpe_eingeschaltet = False  # Status der Pumpe

# Die Funktion get_distance() misst die Entfernung zum Wasser, indem ein Ultraschallimpuls
# ausgesendet und die Zeit bis zur Rückkehr des Echos gemessen wird.
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

# Die control_pump()-Funktion steuert die Philips Hue Steckdose, die die Pumpe ein-
# oder ausschaltet, abhängig vom Wasserstand.
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

# Funktion zum Senden von Benachrichtigungen
def send_notification(message):
    client.send_message(message, title="Wasserstand Warnung")

# Die Hauptfunktion measure_distance() misst kontinuierlich die Entfernung und berechnet
# den Wasserstand als Prozentsatz des maximalen Wasserstands. Bei einem kritischen
# Wasserstand von 80% wird die Pumpe eingeschaltet und eine Benachrichtigung gesendet.
# Sinkt der Wasserstand unter 50%, wird die Pumpe ausgeschaltet.
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

    # Hauptprogrammschleife
    while True:
        time.sleep(10)

finally:
    GPIO.cleanup()
