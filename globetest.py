#!/usr/bin/python3
"""
globetest.py Version 1.0
To test if the lights come on correctly using the weatherglobeutils library.
"""

import weatherglobeutilsv007 as wgu

##pin numbers to match LED legs
##These match mini board pins.
red_pin = 13 
green_pin = 15 
blue_pin = 19

##Initialise light object with correct board pins
globe = wgu.light(red_pin, green_pin, blue_pin)

