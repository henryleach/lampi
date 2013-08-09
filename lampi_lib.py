#!/usr/bin/python3
"""
lampi_lib.py
www.henryleach.com
This libary contains all the utility functions needed to run
a lampi and get weather data from the 'net to set the lighting
pattern.
"""
import time
import RPi.GPIO as GPIO
import math
import bisect
import json
import urllib.request
import datetime
import socket #for timeout error
import calendar #for transforming to epoch time.


##LED control object and related control functions.##

class light:
    """
    Light class. Contains three PWM GPIO objects
    to control RGB LEDs attached to the pins.
    To create pin numbers for red, green and blue
    are needed. Frequency can be optionally set, default
    is 100Hz.
    """
    def __init__(self, R_pin, G_pin, B_pin, Frequency=100):
        """Create a light object controlling an RGB LED using three GPIO pins with PWM.\n

        Pins use the GPIO.BOARD number convention. Default frequency is 100Hz.
        """
        GPIO.setmode(GPIO.BOARD)
        GPIO.setup(R_pin, GPIO.OUT)
        GPIO.setup(G_pin, GPIO.OUT)
        GPIO.setup(B_pin, GPIO.OUT)

        #setup the colours
        self.RED = GPIO.PWM(R_pin, Frequency) #(Pin, frequency)
        self.RED.start(0) #Initial duty cycle of 0, off.
        self.GREEN = GPIO.PWM(G_pin, Frequency)    
        self.GREEN.start(0)  
        self.BLUE = GPIO.PWM(B_pin, Frequency)
        self.BLUE.start(0)

    def change_freq(self, Frequency):
        """Change the frequency (in Hz) of the PWM for all three pins.\n

        """
        self.RED.ChangeFrequency(Frequency)
        self.GREEN.ChangeFrequency(Frequency)
        self.BLUE.ChangeFrequency(Frequency)

    def shutdown(self):
        """Close all the GPIO connections in a tidy manner.\n

        """
        #Stop PWM objects
        self.RED.stop()
        self.GREEN.stop()
        self.BLUE.stop()

    def colour(self, R, G, B, on_time):
        """Colour depth is 0-255. On time in seconds, after which lights are turned off.\n

        0-255 converted to 0-100% range for PWM. If input intesity is out of range,
        it is set to 128.
        """
        if R > 255 or R < 0:
            R=128

        if G > 255 or G < 0:
            G=128

        if B > 255 or B < 0:
            B=128

        ratio=100/255 #to convert to % duty cycle.
        
        self.RED.ChangeDutyCycle(R*ratio)
        self.GREEN.ChangeDutyCycle(G*ratio)
        self.BLUE.ChangeDutyCycle(B*ratio)
        time.sleep(on_time)

        #Turn all off, leaving ready for next call.
        self.RED.ChangeDutyCycle(0)
        self.GREEN.ChangeDutyCycle(0) 
        self.BLUE.ChangeDutyCycle(0)


    def colour_cont(self, R, G, B, on_time):
        """As .colour method, but leave the colour on until changed.\n

        """
        ratio=100/255 #to convert to % duty cycle.
        
        self.RED.ChangeDutyCycle(R*ratio)
        self.GREEN.ChangeDutyCycle(G*ratio)
        self.BLUE.ChangeDutyCycle(B*ratio)
        time.sleep(on_time)

    def testcycle(self):
        """
        Cycles through the seven basic binary colour combinations.\n
        
        Red, green, blue, yellow, magenta, cyan and white.
        """
        self.colour(255,0,0,1) #red
        self.colour(0,255,0,1) #green
        self.colour(0,0,255,1) #blue
        self.colour(255,255,0,1) #yellow
        self.colour(255,0,255,1) #magenta
        self.colour(0,255,255,1) #cyan
        self.colour(255,255,255,1) #white


def possinwave(amplitude, angle, frequency):
    """Input angle in degrees. Output a positive sin wave value 0 and amplitude*2.\n

    """
    return amplitude + (amplitude * math.sin(math.radians(angle)*frequency) )



def ramp(lightobj, R, G, B, steps):
    """
    Ramps between off and desired colour in a linear ramp.\n
    
    Negative step value ramps down, positive up.
    The greater the number of steps, the longer the ramp is.
    50 is a good step value, which takes around 10 seconds.
    """
    R_step = R/steps
    G_step = G/steps
    B_step = B/steps

    if steps>0:
        for i in range(0, steps, 1):
            lightobj.colour_cont(i*R_step, i*G_step, i*B_step, 0.1)
    else:
        for i in range(-steps, 0, -1):
            lightobj.colour_cont(i*-R_step, i*-G_step, i*-B_step, 0.1)
 

def pulse_light(lightobj, R, G, B, pulse_freq, intensity, stop_time):
    """ Fade from input colour to white (intesity 0-255) and back again until
    stop_time (in seconds since the epoch) is reached.\n

    pulse_freq is approximatly(*) the number of times a minute the light pulses.
    stop_time is seconds since epoch. pulse_light will always complete a
    current set of pulses before stopping, therefore it will stop some
    slightly random time after stop_time.\n
    
    (*)Rounding errors and uneven code running time dependent on system
    load mean that at higher pulse_freq values (>40) you're going to start
    loosing some pulses.\n
    """
    if intensity < 0 or intensity > 255:
        #set to max
        intensity = 255
    
    
    R_diff = (intensity-R)/2
    G_diff = (intensity-G)/2
    B_diff = (intensity-B)/2

    if pulse_freq>0:
        #Approximatly how many times a minute the pulse should appear.
        #Over long run periods this is going to get seriously out of step.
        #Additional -10s for two ramps (at 50 steps each).
        #Give the time for each hold. 60 sec - 2*ramp time / number of pulses + number of holds + 1
        hold = (60-10)/(pulse_freq*2 + 1) 
        #Pulse steps slighty smaller than 1/36th to compensate for processing time.
        pulse_step = hold/37 
    else:
        hold = 1
        pulse_step = 0.1 ##This should never be used.


    while time.time() < stop_time:
        lightobj.colour_cont(R, G, B, hold) #steady colour        

        if pulse_freq>0 and time.time() < stop_time:
            for i in range(-90, 270, 10): #36 steps.
               #Pulse to white and back. 
                lightobj.colour_cont(R+possinwave(R_diff,i,1),
                       G+possinwave(G_diff,i,1),
                       B+possinwave(B_diff,i,1),
                       pulse_step)
                #print("Colours",R+possinwave(R_diff,i,1),G+possinwave(G_diff,i,1),B+possinwave(B_diff,i,1))
        else:
            pass


def one_pulse(lightobj, R, G, B):
    """One to white pulse."""
    R_diff = (255-R)/2
    G_diff = (255-G)/2
    B_diff = (255-B)/2

    for i in range(-90, 270, 10): #pulse to white and back
        lightobj.colour_cont(R+possinwave(R_diff,i,1),
               G+possinwave(G_diff,i,1),
               B+possinwave(B_diff,i,1),
               0.1)

##Weatherdata and internet functions##

def check_connection(url):
    """Quick check if your Pi is connected to the internet.\n

    Returns True or False depending on result.
    """
    try:
        urllib.request.urlopen(url, timeout=2)
        return True
    except urllib.request.URLError:
        return False

def getUWeather(apikey, location):
    """Uses a wunderground.com api key get a 10 hour forecast JSON file
    and return a dict() structure.\n

    User needs to register to get their own API key (16 digit hex).\n
    Location is a string in the format 'Country/City' outside the USA and TWO_LETTER_STATE/City inside.
    e.g. 'UK/Bristol' or 'TX/El_Paso'.\n
    Returns -1 if url doesn't exist or contents is an error message.\n
    Returns -2 if connection timesout.\n
    """
    WURL = 'http://api.wunderground.com/api/'
    url = WURL+apikey+"/hourly/q/"+location+".json"

    ##Try to download the JSON. Some error catching.
    try:
        source = urllib.request.urlopen(url, timeout=2)
        json_string = source.read()
    
        ##This returns binary data, and for json we need a string, so we need to decode:
        encoding = source.headers.get_content_charset() #find the encoding type. Almost certainly "utf-8"
        parsed_json = json.loads(json_string.decode(encoding)) #decode it and load it so it becomes a dict()

    except (urllib.error.HTTPError, urllib.error.URLError) as err:
        print(err)
        return -1
    except socket.timeout as err:
        print(err)
        return -2


    ##Some checks to see if we actually got weather data
    try:
        #Did our returned information contain an error code?
        print("Error: ",parsed_json['response']['error']['type'],
              ". Description: ",parsed_json['response']['error']['description'], sep="")
        return -1 #no data loaded, return error code
    except KeyError:
        pass #Error not found in JSON, so we're probably ok.

    print('Forecast loaded from:\n'+url)
    
    return parsed_json


def extractHourlyUWeather(hourlyforecastdict, foretime):
    """Take the large hourly forecast dict() from wunderground.com
    and returns a smaller dict() with most important information at that forecast time inside.\n

    Some of the less obvious codes explained:
      qpf = Quantative Precipitation Forecast. How much rain is likely to fall in 3 hours.
      (Assumed to be in cm.). Mostly seems to be unused.
      Light rain < 0.25cm/hr, 0.25 < Moderate rain < 1.0 < Heavy Rain < 5.0 < Violent Rain.
      wx = sensible weather field (??).
      uni = ultraviolet index (1 - 16. 16 is extreme)
      mslp = mean sea-level pressure. Barometric pressure reduced to sea level.
    """

    foretime=int(foretime)  #prevent addressing errors
    forecast = {'retreived_time': datetime.datetime.today()}
    forecast['forecast_time'] = datetime.datetime.fromtimestamp( int(hourlyforecastdict['hourly_forecast'][foretime]['FCTTIME']['epoch']) )

    forecast['retreived_epoch'] = calendar.timegm(forecast['retreived_time'].timetuple()) #give value in unix time.

    forecast['tempC'] = float( hourlyforecastdict['hourly_forecast'][foretime]['temp']['metric'] )
    forecast['windKPH'] = float( hourlyforecastdict['hourly_forecast'][foretime]['wspd']['metric'] )
    forecast['condition'] = hourlyforecastdict['hourly_forecast'][foretime]['condition']
    forecast['pop'] = hourlyforecastdict['hourly_forecast'][foretime]['pop']

    try:  #replace with: if forecast['QPFcm'] == '' ?
        #if zero this is often an empty string, so let's make sure that doesn't fall over.
        forecast['QPFcm'] = float( hourlyforecastdict['hourly_forecast'][foretime]['qpf']['metric'] )
    except ValueError:
        forecast['QPFcm'] = 0.0
        
    return forecast


def pulsefreq_fromrain(forecast):
    """Take forecast dict() and based on 'condition' string and Probability of Precipitation ('pop')
    percentage returns a tuple containing pulse frequency and intensity.\n
    """
    ##Descriptions of conditions:
    ##http://www.wunderground.com/weather/api/d/docs?d=resources/phrase-glossary
    ##Most conditions can be preceeded by 'Light' or 'Heavy'

    pulses = 0  #start assuming no preciptitation. As we go through the options
                #we'll build up the pulse value
    intensity = 0

    if int(forecast['pop'])==0: #no precipitation, let's skip the rest of this function.
        return (pulses, 0)
        

    ##Going to tight on definition here. Mist, Fog, Haze etc. won't result in a flashing light.
    ##These conditions are listed on the API part of wunderground.com.
    PrecipConds = [  'Drizzle',
                     'Rain',
                     'Snow',
                     'Snow Grains',
                     'Ice Crystals',
                     'Ice Pellets',
                     'Hail',
                     'Volcanic Ash',
                     'Widespread Dust',
                     'Sand',
                     'Spray',
                     'Dust Whirls',
                     'Sandstorm',
                     'Blowing Snow',
                     'Blowing Widespread Dust',
                     'Blowing Sand',
                     'Rain Mist',
                     'Rain Showers',
                     'Snow Showers',
                     'Snow Blowing Snow Mist',
                     'Ice Pellet Showers',
                     'Hail Showers',
                     'Small Hail Showers',
                     'Thunderstorm',
                     'Thunderstorms and Rain',
                     'Thunderstorms and Snow',
                     'Thunderstorms and Ice Pellets',
                     'Thunderstorms with Hail',
                     'Thunderstorms with Small Hail',
                     'Freezing Drizzle',
                     'Freezing Rain',
                     'Freezing Fog',
                     'Unknown Precipitation', #Frogs, cats, dogs etc.
                     'Small Hail']

    for i in PrecipConds:
        if forecast['condition'].find(i) != -1: #does anything match the list above?
            intensity = 200
            pulses = int(forecast['pop'])*0.4

            #now adjust for severity
            #Have also seen 'Chance of' adjective phrase, but it's not documented.
            if forecast['condition'].startswith('Heavy'):
                intensity=255
            elif forecast['condition'].startswith('Light'):
                intensity=150
            else:
                pass

    ##It is possible to have a non-precipitation condition and pop > 0. Not sure what to do then.

    return (pulses, intensity)

##timing and other admin functions##

def lin_interp(indata, dimension, xvalue):
    """
    Takes nested list of floats and returns interpolated value at that dimension.\n

    The first dimension (nested list) are x-values, subsiquent dimensions are y-values.
    X-Values must be in ascending order.
    Returns interpolated y-value for given x-value.
    If x-value falls outside available range the closest in-range
    value is returned.
    """

    #check dimensions agree
    if dimension > len(indata)-1:
        raise ValueError("Dimension index exceeds available dimensions")

    #check xvalue is within range
    if xvalue >= max(indata[0]):
        #Above/at maximum, return rightmost dimension value.
        return indata[dimension][len(indata[dimension]-1)]        
    if xvalue <= min(indata[0]):
        #Below/at min value, return leftmost dimension value.
        return indata[dimension][0]
    

    floatdata=[] #create empty list
    
    #Convert the indata list to floats, prevents problems when doing maths later.
    for j in range(len(indata)):
        floatdata.append([float(i) for i in indata[j]])

    #Find the points to interpolate between
    #returns the largest element smaller than xvalue
    m = bisect.bisect_left(floatdata[0], xvalue)
    #Get the local gradient
    if m==0:
        m=1 #make sure we don't index -1

    deltax = (floatdata[0][m]-floatdata[0][m-1])
    deltay = (floatdata[dimension][m]-floatdata[dimension][m-1])

    if deltay==0:
        #Completely flat (gradient=0). Prevent div. by 0 errors.
        yvalue = floatdata[dimension][m]
    else:
        grad = deltay/deltax
        yvalue = floatdata[dimension][m-1]+(xvalue-floatdata[0][m-1])*grad

    return yvalue

def next_refresh(refresh_interval):
    """
    Returns the epoch time (in second, as float) of the next whole number of
    refresh_intervals (in min) in this hour, or the next whole hour if you're
    already in the last refresh interval.\n
    
    e.g. If refresh_interval is 10 (minutes) and it's now 16:24:15, next_refresh(10)
    will return the epoch seconds for 16:30:00.
    """

    if 60 % refresh_interval != 0:
        #Warn user that you're not going to get evenly spaced refreshes.
        print("Warning: refresh_interval is not evenly divisible into 60 minutes.")

    #Create list of each hourly fresh time.
    refreshes = list(range(0, 60, int(refresh_interval)))

    s = time.gmtime() ##get a time_struct for Now.
    #we can't edit a time_struct, so make a tuple list of it that we can:
    nfresh=list(s)
    #nfresh[3]=hour, [4]=min, [5]=sec.

    
    if nfresh[4] >= max(refreshes):
        #Are we between last refresh and next whole hour, if so:
        nfresh[4] = 0 #zero min, on the hour
        nfresh[3]+=1 #add one hour
    else:
        nfresh[4]= refreshes[bisect.bisect_right(refreshes, nfresh[4])]
        #Match the next highest next fresh (nfresh) time in nfresh
        #and return that minute value.

    ##WARNING: the above involves a dirty hack that seems to work reliably
    ##because calendar.timegm() will accept a time tuple list which 
    ##states nonsense times (dd:hh:mm:ss) like 01:27:34:23 (27 hours a day!)
    ##and convert them correctly to an epoch time. 
    ##If you convert that epoch time back to a time_struct with time.gmtime()
    ##it will correctly state 02:03:34:23.
    ##This hack saves having to deal with more complex date/time/calendar
    ##function addition to do it correctly.

    nfresh[5]=0 #make seconds zero

    #Uncomment print lines for debugging:
    print("Time now:",s.tm_hour,":",s.tm_min,":",s.tm_sec, sep="")
    print("Refresh at:",nfresh[3],":",nfresh[4],":",nfresh[5], sep="")

    return calendar.timegm(nfresh) #return epoch time for next refresh


