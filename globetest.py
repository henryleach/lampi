#!/usr/bin/python3
"""
globetest.py Version 1.0
To test if the LEDs light up correctly using the LED board and lampi_lib.
"""

import lampi_lib as ll
import RPi.GPIO as GPIO

##pin numbers to match LED legs
##These match LED board pins.
red_pin = 19 
green_pin = 21 
blue_pin = 23

##create a light object with correct board pins
lamp = ll.light(red_pin, green_pin, blue_pin)

##Run the seven colour test pattern.
lamp.testcycle()

##Let's close all the GPIO connections correctly for our light object.
lamp.shutdown()

##Last we need to close all GPIO connections properly.
GPIO.cleanup()
