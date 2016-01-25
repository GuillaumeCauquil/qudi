# -*- coding: utf-8 -*-

"""
This file contains the QuDi hardware file implementation for FastComtec p7887 .

QuDi is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

QuDi is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with QuDi. If not, see <http://www.gnu.org/licenses/>.

Copyright (C) 2015 Nikolas Tomek nikolas.tomek@uni-ulm.de
Copyright (C) 2015 Alexander Stark alexander.stark@uni-ulm.de
Copyright (C) 2015 Jochen Scheuer jochen.scheuer@uni-ulm.de
"""

#TODO: start stop works but pause does not work, i guess gui/logic problem
#TODO: What does get status do or need as return?
#TODO: Check if there are more modules which are missing, and more settings for FastComtec which need to be put, should we include voltage threshold?

#Not written modules:
#TODO: configure
#TODO: get_status

from core.base import Base
from hardware.fast_counter_interface import FastCounterInterface
import time
import os
import numpy as np
import ctypes

class InterfaceImplementationError(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

class FastComtec(Base, FastCounterInterface):
    """
    unstable: Jochen Scheuer

    Hardware Class for the FastComtec Card.
    """
    _modclass = 'fastcounterinterface'
    _modtype = 'hardware'
    # connectors
    _out = {'fastcounter': 'FastCounterInterface'}

    def __init__(self, manager, name, config, **kwargs):
        state_actions = {'onactivate': self.activation, 'ondeactivate': self.deactivation}
        Base.__init__(self, manager, name, config, state_actions, **kwargs)

        self.logMsg('The following configuration was found.', 
                    msgType='status')
                    
        # checking for the right configuration
        for key in config.keys():
            self.logMsg('{}: {}'.format(key,config[key]), 
                        msgType='status')
                        
        self.gated = False
         
        
    def activation(self, e):
        """ Initialisation performed during activation of the module.
        """
        self.dll = ctypes.windll.LoadLibrary('dp7887.dll')
        self._minimal_binwidth=0.25

        return

    def deactivation(self, e):
        """ Deinitialisation performed during deactivation of the module.
        """
        return


    def configure(self, bin_width_s, record_length_s, number_of_gates = 0):
        """
        Configuration of the fast counter.
        bin_width_s: Length of a single time bin in the time trace histogram in seconds.
        record_length_s: Total length of the timetrace/each single gate in seconds.
        number_of_gates: Number of gates in the pulse sequence. Ignore for ungated counter.
        Returns the actually set values as tuple
        """

        #self.set_binwidth(binwidth)
		#self.set_length(duration)

        return (self.get_binwidth()/1e9, 4000e-9, 0)

    def get_bitshift(self):
        """Get bitshift from Fastcomtec.

		@return int settings.bitshift: the red out bitshift 		
		"""
		
        settings = AcqSettings()
        self.dll.GetSettingData(ctypes.byref(settings), 0)
        return int(settings.bitshift)

    def get_binwidth(self):
        """The binwidth is defined as 2**bitshift*minimal_binwidth

		@return float: Red out bitshift converted to binwidth
		"""
        return self._minimal_binwidth*(2**int(self.get_bitshift()))

    def set_bitshift(self, bitshift):
        """ Sets the bitshift properly for this card.
        
          @param int bitshift
          
          @return int: asks the actual bitshift and returns the red out value
          """

        cmd='BITSHIFT=%i'%bitshift
        self.dll.RunCmd(0,bytes(cmd,'ascii'))
        return self.get_bitshift()

    def set_binwidth(self,binwidth):
        """Set defined binwidth in Card. Therefore the binwidth is converted into to 			appropiate bitshift defined as 2**bitshift*minimal_binwidth.

		@return float: Red out bitshift converted to binwidth
		"""
        bitshift=np.log2(binwidth/self._minimal_binwidth)
        new_bitshift=self.set_bitshift(bitshift)
        return self._minimal_binwidth*(2**int(new_bitshift))

#TODO: Check such that only possible lengths are set.
    def set_length(self, N):
        """Sets the length of the length of the actual measurement.
        
          @param int N: Length of the measurement  

		  @return float: Red out length of measurement     
          """
        cmd='RANGE=%i'%int(N)
        self.dll.RunCmd(0, bytes(cmd, 'ascii'))
        cmd='roimax=%i'%int(N)
        self.dll.RunCmd(0, bytes(cmd, 'ascii'))
        return self.get_length()

    def get_length(self):
        """ Get the length of the current measurement.
        
          @return int: length of the current measurement
        """
        setting = AcqSettings()
        self.dll.GetSettingData(ctypes.byref(setting), 0)
        return int(setting.range)


    def get_status(self):
        """ Receives the current status of the Fast Counter and outputs it as return value."""
        return 2

#    TODO: What should the status be it asks for something with binwidth but in the interface there is only the status of
    #card if running or halt or stopped ...
    # def get_status(self):
    #     #TODO: Find out if it is possible to get the status for other modes
    #     """
    #     Receives the current status of the Fast Counter and outputs it as return value.
    #     0 = unconfigured
    #     1 = idle
    #     2 = running
    #     3 = paused
    #     -1 = error state
    #     """
    #     status = AcqStatus()
    #     self.dll.GetStatusData(ctypes.byref(status), 0)
    #     if status.started == 0:
    #         return 0
    #     if status.started == 1:
    #         return 2
    #     else:
    #         self.logMsg('There is an unknown status from FastComtec. The status message was %s'%(str(status.started)), msgType='error')
    #         return -1

    def start_measure(self):
        """Start the measurement. """
        self.dll.Start(0)
        return 0

    def pause_measure(self):
        """Make a pause in the measurement, which can be continued. """
        self.dll.Halt(0)
        return 0
        
    def stop_measure(self):
        """Stop the measurement. """
        self.dll.Halt(0)
        return 0
    
    def continue_measure(self):
        """Continue a paused measurement. """
        self.dll.Continue(0)
        return 0

    def get_data_trace(self):
        """
        Polls the current timetrace data from the fast counter and returns it as a numpy array (dtype = int64).
        The binning specified by calling configure() must be taken care of in this hardware class.
        A possible overflow of the histogram bins must be caught here and taken care of.
        If the counter is UNgated it will return a 1D-numpy-array with returnarray[timebin_index]
        If the counter is gated it will return a 2D-numpy-array with returnarray[gate_index, timebin_index]

		  @return arrray: Time trace.
        """
        setting = AcqSettings()
        self.dll.GetSettingData(ctypes.byref(setting), 0)
        N = setting.range
        data = np.empty((N,), dtype=np.uint32)
        self.dll.LVGetDat(data.ctypes.data, 0)
        return np.int64(data)

    def get_data_testfile(self):
        ''' Load data test file '''
        data = np.loadtxt(os.path.join(self.get_main_dir(), 'tools', 'FastComTec_demo_timetrace.asc'))
        time.sleep(0.5)
        return data
        
    def is_gated(self):
        """
        Boolean return value indicates if the fast counter is a gated counter (TRUE) or not (FALSE).
        """
        return self.gated



class AcqStatus(ctypes.Structure):
    """
    Retrieving the status data from Fastcomtec

    int started;                // aquisition status: 1 if running, 0 else
    double runtime;             // running time in seconds
    double totalsum;            // total events
    double roisum;              // events within ROI
    double roirate;             // acquired ROI-events per second
    double nettosum;            // ROI sum with background subtracted
    double sweeps;              // Number of sweeps
    double stevents;            // Start Events
    unsigned long maxval;       // Maximum value in spectrum
    """
    _fields_ = [('started', ctypes.c_int),
                ('runtime', ctypes.c_double),
                ('totalsum', ctypes.c_double),
                ('roisum', ctypes.c_double),
                ('roirate', ctypes.c_double),
                ('ofls', ctypes.c_double),
                ('sweeps', ctypes.c_double),
                ('stevents', ctypes.c_double),
                ('maxval', ctypes.c_ulong), ]

class AcqSettings(ctypes.Structure):
    _fields_ = [('range',       ctypes.c_ulong),
                ('prena',       ctypes.c_long),
                ('cftfak',      ctypes.c_long),
                ('roimin',      ctypes.c_ulong),
                ('roimax',      ctypes.c_ulong),
                ('eventpreset', ctypes.c_double),
                ('timepreset',  ctypes.c_double),
                ('savedata',    ctypes.c_long),
                ('fmt',         ctypes.c_long),
                ('autoinc',     ctypes.c_long),
                ('cycles',      ctypes.c_long),
                ('sweepmode',   ctypes.c_long),
                ('syncout',     ctypes.c_long),
                ('bitshift',    ctypes.c_long),
                ('digval',      ctypes.c_long),
                ('digio',       ctypes.c_long),
                ('dac0',        ctypes.c_long),
                ('dac1',        ctypes.c_long),
                ('swpreset',    ctypes.c_double),
                ('nregions',    ctypes.c_long),
                ('caluse',      ctypes.c_long),
                ('fstchan',     ctypes.c_double),
                ('active',      ctypes.c_long),
                ('calpoints',   ctypes.c_long), ]