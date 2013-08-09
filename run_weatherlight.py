#!/usr/bin/python3
"""
run_weatherlight.py Version 1.0
www.henryleach.com
Main script to collect weather data from the internet and set an
LED colour and pattern that hopefully gives and intuative impression
for the weather forecast. Frequency and intensity of(white) pulses represent
precipitation, base colour is temperature.
"""

import lampi_lib as ll
import RPi.GPIO as GPIO
import time
import argparse

##command line arguments for user, plus defaults and help details.
parser = argparse.ArgumentParser()
## -k APIKEY -l LOCATION -f foretime -r refresh_min
parser.add_argument("apikey", help="wunderground.com 16-char apikey.")
parser.add_argument("location", help="<country(or US state)>/<city>.")
parser.add_argument("-f", "--foretime", default=3, choices=range(12),
                    help="How far in advance to forecast, hours. Default 3", type=int)
parser.add_argument("-r ", "--refresh", default=30, choices=range(5,59),
                    help="Refresh time, minutes. Default 30", type=int)

args = parser.parse_args()
print("Options chosen:\n",
      "API key:", args.apikey,
      "Location:", args.location,
      "foretime:", args.foretime,
      "Refresh every",args.refresh,"min.")



##pin numbers to match LED legs
##These match GPIO board pins used by LED board.
red_pin = 19 
green_pin = 21 
blue_pin = 23
run = True #If True, main light and refresh data loop will run.

##Scale for RGB intensity combinations to give the correct
##temperature/colour scale.
temp_scale = [
                [-30,-17, -0, 12, 20, 26, 35, 50], #degress C
                [  0,  0,  0,100,255,255,255,255], #Red
                [183, 65, 94,100,224,140, 55,  0], #Green
                [  0,178,255,100,  0,  0,  0,197], #Blue
             ]
##Initialise light object with correct board pins
globe = ll.light(red_pin, green_pin, blue_pin)

##Check forecase time
if args.foretime < 0 or args.foretime > 12:
    args.foretime = 2 #set to sensible default
    print("Forecast period out of range (1-12 hours). Set to 2 hours.")
    globe.colour(255,0,255,1) #flash magenta to tell user.

##check refresh interval. We don't need to check too often, the forecast
##isn't refreshed that quickly.
if args.refresh < 5 or args.refresh > 60:
    args.refresh = 15 #set to sensible default
    print("Refresh time out of range (10-60 minutes). Set to 15 minutes.")
    globe.colour(0,255,255,1) #flash cyan to tell user.
    
##Can we connect to our website?
if ll.check_connection('http://www.wunderground.com'):
    print("Internet connection available.")
    globe.colour(0,255,0,1) #green if true
else:
    globe.colour(255,0,0,5) #red if can't connect
    print("No internet connection.")
    run = False #stop the run.

##Main loop. Program can be stopped by a keyboard interrupt (ctrl+c) at the consol.
try:
    while run:
        
        ##Get weather data
        ##Download the raw 10 hour forcast JSON and convert to a dict.      
        raw_weather_data = ll.getUWeather(args.apikey, args.location)

        if raw_weather_data == -1:
            ##There was a terminal error getting the data, so we have to stop.
            print("Stopped. Error getting weather data.")
            run = False
            break
        elif raw_weather_data == -2:
            ##Connection timeout error. This might be temporary...let's wait and try again
            ##until we get a positive response or a terminal error.
            print("Timeout, waiting 5 minutes.")
            #pulse dimly for five minutes.
            ll.pulse_light(globe, 0, 0, 0, 5, 100, time.time()+300)
        else:
            ##Extract the weather data for the forecase time we're interested in
            forecast = ll.extractHourlyUWeather(raw_weather_data, args.foretime)

            print("In ",args.foretime," hours the temperature will be: ",forecast['tempC'], "C", sep="")

            ##Set the intensities to each colour.
            r = ll.lin_interp(temp_scale, 1, forecast['tempC'])
            g = ll.lin_interp(temp_scale, 2, forecast['tempC'])
            b = ll.lin_interp(temp_scale, 3, forecast['tempC'])

            ##Work out the next time to stop and refresh.
            refresh_epoch = ll.next_refresh(args.refresh)

            print("Condition: ", forecast['condition'], " with ", forecast['pop'],"% chance.", sep="")
            
            ##Set the number of pulses based on rain forecast
            pulses, intensity = ll.pulsefreq_fromrain(forecast)
            print("Pulses: ", pulses, ", Intensity: ", intensity,"\n", sep="")

            ##Turn LED on and off smoothly. Run colour and pulsing until
            ##next refresh time.
            ll.ramp(globe, r, g, b, 50)
            ll.pulse_light(globe, r, g, b, pulses, intensity, refresh_epoch)
            ll.ramp(globe, r, g, b,-50)
            globe.colour(0,0,0,0) #make sure the LED is really off during the refresh.

except KeyboardInterrupt:
    pass


##Close the connections
globe.shutdown()

##Tidy up anything that might be left
GPIO.cleanup()
