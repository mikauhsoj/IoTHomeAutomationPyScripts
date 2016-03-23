#!/usr/bin/python

import os
import time
import sys
import RPi.GPIO as GPIO
import atexit
import json
from pubnub import Pubnub
import Adafruit_DHT as dht

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
red_gpio = 18;
green_gpio = 23;
blue_gpio = 24;
sensor_gpio = 17;

## Setup GPIO Board and Pins
GPIO.setmode(GPIO.BCM) # BCM for GPIO numbering
GPIO.setup(red_gpio, GPIO.OUT);
GPIO.setup(green_gpio, GPIO.OUT);
GPIO.setup(blue_gpio, GPIO.OUT);

## Initialize the GPIO PWMs
Freq = 100; #Hz

RED = GPIO.PWM(red_gpio, Freq);
RED.start(0);

GREEN = GPIO.PWM(green_gpio, Freq);
GREEN.start(0);

BLUE = GPIO.PWM(blue_gpio, Freq);
BLUE.start(0);

## Main function
def main():
    
    #rgb()
    updateHue(0,0,0); # Light off
    #print "off"

    # This callback handles any messages received on subscribed channel
    def _callback(msg, n):
        print(msg);
        # Check to see what kind of request the phone is making
        if 'Type' not in msg:
            doesNotCompute();
        elif msg['Type'] == "SENS": # Request for sensor readings
            sensor();
        elif msg['Type'] == "LED": # Request for change led color
            updateHue(msg["RED"], msg["GREEN"], msg["BLUE"]);
        elif msg['Type'] == "LEDOff":
            rgbOff();
        else: # No request specified
            doesNotCompute();
            

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

## Function to turn the led off
def rgbOff():
    updateHue(0,0,0);

## Function to get readings from temp/humidity sensor and publish to pubnub
def sensor():
    # Use the library to get the readings from the sensor and put them into variables
    h,t = dht.read_retry(dht.DHT22, 17);
    # Convert Celsius to Farenheit
    Tf = t * 9 / 5 + 32;
    # Display the values in the terminal
    print h,t;
    # Publish the values to pubnub
    pubnub.publish(pubChannel, {
        'columns': [
            ['Time', time.time()],
            ['Temperature', "%.2f" % Tf],
            ['Humidity', "%.2f" % h]
            ]
    });

## Function to call when something doesn't make sense.
def doesNotCompute():
    print("Does not compute!");
    pubnub.publish(pubChannel, "Does not compute!");

## Function that is called when program is ended. Cleans the GPIO ports.
@atexit.register
def goodbye():
    print("Goodbye");
    GPIO.cleanup();

## Call main function.
main();
