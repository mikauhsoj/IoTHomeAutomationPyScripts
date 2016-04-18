#!/usr/bin/python

import os
import time
import sys
import RPi.GPIO as GPIO
import atexit
import json
import picamera
import subprocess
from pubnub import Pubnub
import Adafruit_DHT as dht
from dotstar import Adafruit_DotStar
from subprocess import call

## I've decided to save sensitive pubnub information in a different file.
## This allows me to add this script to github without giving my pub and sub keys.
try:
    # Open the file to read
    # If the file opens, extract the pubnub information from it
    with open('pubnub.json', 'r') as pubnubInfo:
        # Decode the json
        info = json.load(pubnubInfo); 

        # Get pubnub info and put into variables
        pubKey = info['pubKey'];
        subKey = info['subKey'];
        subChannel = info['subChannel'];
        pubChannel = info['pubChannel'];

        # Close the file
        pubnubInfo.closed; 
        
## If the file fails to open/doesn't exist, get the info from user
except IOError: 
    # Open a file to write in
    with open('pubnub.json', 'w') as pubnubInfo: 
        print("It looks like you haven't specified any pubnub information yet. Please do so now.");

        #Ask the user to provide the pubnub information
        pubKey = raw_input("Enter publish key: ");
        subKey = raw_input("Enter subscribe key: ");
        subChannel = raw_input("What channel are you subscribing to? ");
        pubChannel = raw_input("What channel will you be publishing to? ");
        json.dumps(3,pubChannel)

        # Create a json object with the info
        jinfo = {'pubKey':pubKey,
                 'subKey':subKey,
                 'subChannel':subChannel,
                 'pubChannel':pubChannel};
        # Dump the json object into a json file
        json.dump(jinfo,pubnubInfo);

        # Close the file
        pubnubInfo.closed;


## Initialize Pubnub
pubnub = Pubnub(publish_key=pubKey, subscribe_key=subKey);

## Make your pin assignments
ledPin = 4;
red_gpio = 18;
green_gpio = 23;
blue_gpio = 24;
sensor_gpio = 22;
motion_gpio = 17;
rgb_strip_datapin = 19;
rgb_strip_clockpin = 6;

## Setup GPIO Board and Pins
GPIO.setmode(GPIO.BCM) # BCM for GPIO numbering
GPIO.setup(red_gpio, GPIO.OUT);
GPIO.setup(green_gpio, GPIO.OUT);
GPIO.setup(blue_gpio, GPIO.OUT);
GPIO.setup(sensor_gpio, GPIO.OUT);
GPIO.setup(motion_gpio, GPIO.IN)
GPIO.setup(ledPin, GPIO.OUT);

## Initialize the GPIO PWMs
Freq = 100; #Hz

RED = GPIO.PWM(red_gpio, Freq);
RED.start(0);

GREEN = GPIO.PWM(green_gpio, Freq);
GREEN.start(0);

BLUE = GPIO.PWM(blue_gpio, Freq);
BLUE.start(0);

MotionMessage = {'Motion': 1}


## Main function
def main():

    #rgb()
    updateHue(0,0,0); # Light off
    #print "off"
    try:

        # This callback handles any messages received on subscribed channel
        def _callback(msg, n):
            print(msg);
            # Check to see what kind of request the phone is making
            if 'Type' not in msg:
                printMessage("No type specified");
            elif msg['Type'] == "SENS": # Request for sensor readings
                sensor();
            elif msg['Type'] == "LED":
                led(msg["Status"]);
            elif msg['Type'] == "RGB": # Request for change led color
                updateHue(msg["RED"], msg["GREEN"], msg["BLUE"]);
            elif msg['Type'] == "RGBOff":
                rgbOff();
            elif msg['Type'] == "CAM":
                camera();
            elif msg['Type'] == "MOTION":
                motion();
            elif msg['Type'] == "STRIP":
                rgbStrip(msg["RED"], msg["GREEN"], msg["BLUE"]);
            elif msg['Type'] == "STest":
                rgbStripTest();
            else: # No request specified
                doesNotCompute();
    except KeyboardInterrupt:
        print " Quit"

    def _error(m):
        print(m);

    # Subscribe to pubnub channel
    pubnub.subscribe(channels=subChannel, callback=_callback, error=_error)


## Function to update the LED with RGB values
def updateHue(R, G, B):
    rVal = (R/255.0)*100;
    gVal = (G/255.0)*100;
    bVal = (B/255.0)*100;
    print "rgb(%.2f, %.2f, %.2f)" % (rVal, gVal, bVal);
    RED.ChangeDutyCycle(rVal);
    GREEN.ChangeDutyCycle(gVal);
    BLUE.ChangeDutyCycle(bVal);

## Function to iterate through the different light colors
def rgb():
    updateHue(255,0,0);
    time.sleep(2);
    updateHue(0,255,0);
    time.sleep(2);
    updateHue(0,0,255);
    time.sleep(2);

def led(status):
    if (status == 1):
        GPIO.output(ledPin,True)
    elif (status == 0):
        GPIO.output(ledPin,False)

## Function to turn the led off
def rgbOff():
    updateHue(0,0,0);

## Function to control the light color of the RGB led strip
def rgbStripTest():
    numpixels = 30; # Number of LEDs in strip

    # strip     = Adafruit_DotStar(numpixels, datapin, clockpin)
    strip   = Adafruit_DotStar(numpixels, 12000000) # SPI @ ~32 MHz

    strip.begin()           # Initialize pins for output
    strip.setBrightness(64) # Limit brightness to ~1/4 duty cycle

    # Runs 10 LEDs at a time along strip, cycling through red, green and blue.
    # This requires about 200 mA for all the 'on' pixels + 1 mA per 'off' pixel.

    head  = 0               # Index of first 'on' pixel
    tail  = -10             # Index of last 'off' pixel
    color = 0xFF0000        # 'On' color (starts red)
    repeat = 0

    while True:                              # Loop forever
        strip.setPixelColor(head, color) # Turn on 'head' pixel
        strip.setPixelColor(tail, 0)     # Turn off 'tail'
        strip.show()                     # Refresh strip
        time.sleep(1.0 / 50)             # Pause 20 milliseconds (~50 fps)

        head += 1                        # Advance head position
        if(head >= numpixels):           # Off end of strip?
            head    = 0              # Reset to start
            color >>= 8              # Red->green->blue->black
            if(color == 0): color = 0xFF0000 # If black, reset to red

        tail += 1                        # Advance tail position
        if(tail >= numpixels):
            tail = 0  # Off end? Reset
            repeat += 1

        if(repeat == 10):
            rgbStripOff(strip)
            break;

## Function to control the light color of the RGB led strip
def rgbStrip(R, G, B):
    numpixels = 30; # Number of LEDs in strip
    # strip     = Adafruit_DotStar(numpixels, rgb_strip_datapin, rgb_strip_clockpin)
    strip = Adafruit_DotStar(numpixels) # SPI @ ~32 MHz

    strip.begin()           # Initialize pins for output
    strip.setBrightness(64) # Limit brightness to ~1/4 duty cycle

    # Runs 10 LEDs at a time along strip, cycling through red, green and blue.
    # This requires about 200 mA for all the 'on' pixels + 1 mA per 'off' pixel.

    led  = 0               # Index of first 'on' pixel
    while (led != 30): # Loop for each light
        strip.setPixelColor(led, R, G, B) # Set pin color
        strip.show()                     # Refresh strip

        led += 1                        # Advance head position\
        
def rgbStripOff(strip):
    clear = 0
    while (clear != 30):
        strip.setPixelColor(clear, 0)     # Turn off 'tail'
        strip.show()
        clear += 1
    



## Function to get readings from temp/humidity sensor and publish to pubnub
def sensor():
    # Use the library to get the readings from the sensor and put them into variables
    h,t = dht.read_retry(dht.DHT22, sensor_gpio);
    # Convert Celsius to Farenheit
    Tf = t * 9 / 5 + 32;
    # Display the values in the terminal
    print h,t;
    # Publish the values to pubnub
    pubnub.publish(pubChannel, {'Time':time.time(), 'Temperature': int(Tf), 'Humidity': int(h)
    });

    # Publish the values to pubnub
    #pubnub.publish(pubChannel, {
    #    'columns': [
    #        ['Time', time.time()],
    #        ['Temperature', "%.2f" % Tf],
    #        ['Humidity', "%.2f" % h]
    #        ]
    #});

## Function to call to take 5 images from the camera
def camera():
    camera = picamera.PiCamera();

    for shot in range(0,5):
        print("Image " + str(shot) + " captured");
        camera.capture('Images/image' + str(shot) + '.jpg');
        photofile = "/home/pi/IoT/Dropbox-Uploader/dropbox_uploader.sh upload /home/pi/IoT/Images/image" + str(shot) + ".jpg image" + str(shot) + ".jpg"
        call ([photofile], shell=True)
        time.sleep(3);
        print("Images uploaded");
    camera.close();

def motion():
    try:
        GPIO.add_event_detect(motion_gpio, GPIO.RISING, callback=motionDetected)
        while 1:
            time.sleep(100)
    except KeyboardInterrupt:
        print " Quit"

def motionDetected(motion_gpio):
    print("Motion detected.");
    pubnub.publish(pubChannel, MotionMessage);

## Function to call when something doesn't make sense.
def doesNotCompute():
    print("Does not compute!");
    pubnub.publish(pubChannel, "Does not compute!");

def printMessage(message):
    print(message);
    pubnub.publish(pubChannel, message);

def test():
    print("Debug test");

## Function that is called when program is ended. Cleans the GPIO ports.
@atexit.register
def goodbye():
    print("Goodbye");
    GPIO.cleanup();

## Call main function.
main();
