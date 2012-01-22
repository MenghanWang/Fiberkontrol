# Major imports
import numpy as np
import serial
import re
import time
import random
import wx

# Enthought imports
from enthought.traits.api \
    import Array, Dict, Enum, HasTraits, Str, Int, Range, Button, String, \
    Bool, Callable, Float, Instance, Trait
from enthought.traits.ui.api import Item, View, Group, HGroup, spring, Handler
from enthought.pyface.timer.api import Timer

# Chaco imports
from enthought.chaco.api import ArrayPlotData, Plot
from enthought.enable.component_editor import ComponentEditor
from enthought.chaco.chaco_plot_editor import ChacoPlotEditor, \
                                                ChacoPlotItem

# Timer
from enthought.pyface.timer.api import Timer


from threading import Thread

#-----------------------------------------------------------------------------------------#

class FiberModel( HasTraits ):
    # Traits - other functions are listening for this to change

    # Public Traits
    plot_type     = Enum( "record", "demo" )
    analog_in_pin = Int( 0 )
    T             = Int( 0 ) 
    dt            = Int( 1 ) # in ms; what does this do to accuracy
    analog_in_0   = Int( 1 ) 
    analog_in_1   = Int( 1 ) 
    analog_in_2   = Int( 0 ) 
    analog_in_3   = Int( 0 ) 

    savepath = '/Users/kellyz/Documents/Data/Fiberkontrol/20120120/'
    filename = '20120120-'

    view = View(Group( 'savepath',
                       'filename',
                       orientation="vertical"),
                buttons=["OK", "Cancel"],
                width = 500, height = 200 )


    # Private Traits
    _ydata  = Array()
    _i1data = Array() #input 1 data
    _i2data = Array() #input 2 data
    _i3data = Array() #input 3 data
    _tdata  = Array() #time data
    _sdata  = Array() #shutter data

    _ydata  = np.zeros(500000)
    _i1data = np.zeros(500000) #input 1 data
    _i2data = np.zeros(500000) #input 2 data
    _i3data = np.zeros(500000) #input 3 data
    _tdata  = np.zeros(500000) #time data
    _sdata  = np.zeros(500000) #shutter data
    master_index = 0


    def __init__(self, **kwtraits):
#        self.view.edit_traits()

        super( FiberModel, self ).__init__( **kwtraits )


 
        # debugging flag
        self.debug = False

        if self.plot_type is "record":
            try:
                import u6
                self.labjack = u6.U6()
                print "---------------------------------------------------"
                print "             Labjack U6 Initialized                "
                print "---------------------------------------------------"
                if self.debug:
                    self.labjack.debug = True
            except:
                raise IOError( "No Labjack detected." )

            # setup analog channel registers
            self.AIN0_REGISTER = 0
            self.AIN1_REGISTER = 2
            self.AIN2_REGISTER = 4
            self.AIN3_REGISTER = 6

            self.num_analog_channels = self.analog_in_0 + self.analog_in_1 + self.analog_in_2 + self.analog_in_3

            #setup streaming
            print "configuring U6 stream"
            self.labjack.streamConfig(  NumChannels = 2, ChannelNumbers = [ 0, 1,], 
                                        ChannelOptions = [ 0, 0, ], SettlingFactor = 1, 
                                        ResolutionIndex = 1, ScanInterval =  6000, SamplesPerPacket = 25)

            self.prev_time = 0

            # setup frequency control

            #---Constants for PWM frequency-----
            self.TIME_CLOCK_BASE = 4000000 #in Hz
            self.FREQUENCY_CONVERSION_CONSTANT = 65536
            self.PWM_CONSTANT = 65536
            

            self.labjack.writeRegister(6002, 1) #change FI02 to output
            self.labjack.writeRegister(50501, 1) # enable one timer
            self.labjack.writeRegister(50500, 2) #change the offset (output pin) to FIO2            

            self.labjack.writeRegister(7100, 0) #for 16bit PWM output
            self.labjack.writeRegister(7000, 4) #for 4 MHz/divisor base clock
            self.labjack.writeRegister(7200, 65535) #init the  duty cycle to 0%


            #---Shutter plan settings ------------
            self.start_time = time.time()
            self.shutterChunkTime = 10 #in seconds

            self.shutterPlan = [0, 30, 0, 10, 0, 0.5, 0, 5, 0, 50,
                                0, 20, 0, 1, 0, 30, 0, 5, 0, 10, 
                                0, 0.5, 0, 20, 0, 1, 0] #in Hz

            freq = 10 #in Hz
            if(True):
                self.shutterPlan = [0, freq, 0, freq, 0, freq, 0, freq, 0,
                                    freq, 0, freq, 0, freq, 0, freq, 0, freq,
                                    0, freq, 0, freq, 0, freq, 0, freq, 0, freq,
                                    0, freq, 0, freq, 0, freq, 0, freq, 0, freq,
                                    0, freq, 0, freq, 0, freq, 0, freq, 0, freq,
                                    0, freq, 0, freq, 0, freq, 0, freq, 0, freq,
                                    0, freq, 0, freq, 0, freq, 0, freq, 0, freq]


            # set recording to be true
            self.recording = True




    def _get_current_data( self ):
        """ If currently recording, query labjack for current analog input registers """
        if self.recording is True:
#            current = self.labjack.readRegister( self.AIN0_REGISTER, numReg = self.num_analog_channels*2 )
#            current0 = self.labjack.readRegister( self.AIN0_REGISTER )
#            current1 = self.labjack.readRegister( self.AIN1_REGISTER )

            rgen = self.labjack.streamData()
            rdata = rgen.next()
            dataCount0 = 1
            dataCount1 = 1
            dataCount2 = 1
            dataCount3 = 1

            self.curr_time = time.time() - self.start_time
            
            if rdata is not None:
                last_v = 0 
                for v in rdata['AIN0']:
                    
                    if v < 10.1:
                        numData = len(rdata['AIN0'])
                        timeChunk = dataCount0*(self.curr_time - self.prev_time)/numData
#                        self._ydata = np.append( self._ydata, v )
                        self._ydata[self.master_index + dataCount0 -1] = v
                        last_v = v
                    else: #to account for weird blips where it saturates for one time step
#                        self._ydata = np.append( self._ydata, last_v )
                        self._ydata[self.master_index + dataCount0 -1] = last_v

                    self._tdata[self.master_index + dataCount0 -1] = self.prev_time + timeChunk
                    self._sdata[self.master_index + dataCount0 -1] = self.actual_freq
#                    self._tdata = np.append( self._tdata, 
 #                                            self.prev_time + timeChunk)
#                    self._sdata = np.append( self._sdata, self.actual_freq)
                        
                    dataCount0 += 1

                    print 'master_index', self.master_index

###CHECKKK THISSSSS!!!!!!!
                for v in rdata['AIN1']:
#                    self._i1data = np.append( self._i1data, v )
                    self._i1data[self.master_index + dataCount1 -1] = v
                    dataCount1 += 1
#                for v in rdata['AIN2']:
#                    self._i2data[self.master_index+dataCount2 -1] = v
 #                   self._i2data = np.append( self._i2data, v )
  #                 dataCount2 += 1
   #             for v in rdata['AIN3']:
#                    self._i3data[self.master_index+dataCount3 -1] = v 
   #                self._i3data = np.append( self._i3data, v )
     #               dataCount3 += 1

        
            if dataCount1 != dataCount0:
                print "ERRRRORRRRRRRR, DATACOUNTS ARE NOT THE SAME"

            self.prev_time = self.curr_time

#            print 'dataCounts', dataCount0, ';', dataCount1, ';', dataCount2, ';', dataCount3

#            self._i2data = np.append( self._i2data, current[2] )
#            self._i3data = np.append( self._i3data, current[3] )

#            self._xdata = range( 0, len( self._ydata ))
 
#            print 'time', self._tdata

#            self._ydata = self._ydata
#            self._i1data = self._i1data

            self.master_index += dataCount0 - 1

    def _set_frequency( self ):
        """ Set the frequency of the shutter, according to a pretedermined plan """
#        self.labjack
        
#        print 'frequency'
        
        currTime = time.time() - self.start_time
        index = int(currTime/self.shutterChunkTime)
#        print 'index', index

        desired_freq = self.shutterPlan[index] #in Hz
#        print 'desired_freq', desired_freq

        pin = 2 #FI02
        pulsewidth = 50 #PWM %

        if (desired_freq == 0):
            pulsewidth = 0
            self.actual_freq = 0
 #           self._sdata = np.append( self._sdata, 0)            
        else:
            divisor = int(self.TIME_CLOCK_BASE/(self.FREQUENCY_CONVERSION_CONSTANT*desired_freq))
            self.labjack.writeRegister(7002, divisor) #set the divisor
            self.actual_freq = self.TIME_CLOCK_BASE/(self.FREQUENCY_CONVERSION_CONSTANT*float(divisor))
#            self._sdata = np.append( self._sdata, actual_freq)

        self.labjack.writeRegister(7200, self.PWM_CONSTANT - (self.PWM_CONSTANT*pulsewidth/100)) #set the duty cycle


        ## To test readout of AIN1, 2, 3
        if (desired_freq == 0):
            self.labjack.writeRegister(5000, 3.7)
        else:
            self.labjack.writeRegister(5000, 0)

        
    def plot_out( self ):
        pl.plot( self.out )

    def save( self, path = None, name = None ):

        if path is not None:
            self.savepath = path
        if name is not None:
            self.filename = name

        full_save_path = self.savepath + self.filename
        print full_save_path

        full_save_path_t = full_save_path + '_t'
        full_save_path_s = full_save_path + '_s'
        full_save_path_i1= full_save_path + '_i1'
        full_save_path_i2= full_save_path + '_i2'
        full_save_path_i3= full_save_path + '_i3'

        np.savez( full_save_path, self._ydata )
        np.savez( full_save_path_t, self._tdata )
        np.savez( full_save_path_s, self._sdata )
        np.savez( full_save_path_i1, self._i1data )
        np.savez( full_save_path_i2, self._i2data )
        np.savez( full_save_path_i3, self._i3data )


        self.labjack.streamStop()
        self.labjack.close()



    def load( self, path = None, name = None ):
        if path is not None:
            self.savepath = path
        self.loaded = np.load( self.savepath + '/out.npz' )['arr_0']

class FiberView( HasTraits ):

    timer         = Instance( Timer )
    model         =  FiberModel()

# Pop up the save window
    model.edit_traits()

    plot_data     = Instance( ArrayPlotData )
    plot          = Instance( Plot )
    record        = Button()
    stop          = Button()
    load_data     = Button()
    save_data     = Button()
    save_plot     = Button()

    # Default TraitsUI view
    traits_view = View(
        Item('plot', editor=ComponentEditor(), show_label=False),
        # Items
        HGroup( spring,
                Item( "record",    show_label = False ), spring,
                Item( "stop",      show_label = False ), spring,
                Item( "load_data", show_label = False ), spring,
                Item( "save_data", show_label = False ), spring,
                Item( "save_plot", show_label = False ), spring,
                Item( "plot_type" ),                     spring,
                Item( "analog_in_pin" ),                 spring,
                Item( "dt" ),                            spring ),

        Item( "T" ),
        # GUI window
        resizable = True,
        width     = 1000, 
        height    = 700 ,
        kind      = 'live' )

    def __init__(self, **kwtraits):
        super( FiberView, self ).__init__( **kwtraits )

        self.plot_data = ArrayPlotData( x = self.model._tdata, y = self.model._ydata )
#        self.plot_data = ArrayPlotData( x = self.model._tdata, y = self.model._i1data )
        

        self.plot = Plot( self.plot_data )
        renderer  = self.plot.plot(("x", "y"), type="line", color="green")[0]

        # Start the timer!

        self.timer = Timer(self.model.dt, self.time_update) # update every 1 ms

    def run( self ):
        self.model.start_time = time.time()
        self.model.prev_time = 0
        
        self.model.labjack.streamStart()

        self._plot_update()
        self.model._get_current_data()

    def time_update( self ):
        """ Callback that gets called on a timer to get the next data point over the labjack """
        if self.recording is True:
            time1 = time.time()-self.model.start_time
            self.model._set_frequency()
            time2 = time.time()-self.model.start_time
#            print 'set_freq:', time2-time1
            self.model._get_current_data()     
            time3 = time.time()-self.model.start_time
 #           print 'get_current_data', time3-time2
            self._plot_update()
            time4 = time.time()-self.model.start_time
  #          print 'plot_update', time4-time3

    def _plot_update( self ):

        if len(self.model._ydata) > 10000:
            self.plot_data.set_data("y", self.model._ydata[-10000:])
            self.plot_data.set_data( "x", self.model._tdata[-10000:] )
        else:        
            self.plot_data.set_data( "y", self.model._ydata ) 
        #        self.plot_data.set_data( "y", self.model._i1data ) 
            self.plot_data.set_data( "x", self.model._tdata )
            self.plot = Plot( self.plot_data )
        self.plot.plot(("x", "y"), type="line", color="green")[0]
        self.plot.request_redraw()

    # Note: These should be moved to a proper handler (ModelViewController)

    def _record_fired( self ):
        self.recording = True
        self.run()
            

    def _stop_fired( self ):
        self.recording = False

    def _load_data_fired( self ):
        pass

    def _save_data_fired( self ):
        self.model.save( path = self.model.savepath, name = self.model.filename )
        print 'time',self.model._tdata


    def _save_plot_fired( self ):
        pass


#-----------------------------------------------------------------------------------------

class Save( HasTraits ):
    """ Save object """

    savepath  = Str( '/Users/kellyz/Documents/Data/Fiberkontrol/Data/20111208/',
                     desc="Location to save data file",
                     label="Save location:", )

    outname   = Str( '',
                     desc="Filename",
                     label="Save file as:", )

#------------------------------------------------------------------------------------------

class TextDisplay(HasTraits):
    string = String()

    view= View( Item('string', show_label = False, springy = True, style = 'custom' ) )

#------------------------------------------------------------------------------------------

class SaveDialog(HasTraits):
#    save = Instance( Save )
#    display = Instance( TextDisplay )

    view = View(
                Item('save', style='custom', show_label=False, ),
                Item('display', style='custom', show_label=False, ),
            )

#------------------------------------------------------------------------------------------

if __name__ == "__main__":
    F = FiberView()
    F.recording = False
    F.configure_traits()
