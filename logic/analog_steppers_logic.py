# -*- coding: utf-8 -*-

"""
A module for controlling the steppers via analog user input.

Qudi is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Qudi is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Qudi. If not, see <http://www.gnu.org/licenses/>.

Copyright (c) the Qudi Developers. See the COPYRIGHT.txt file at the
top-level directory of this distribution and at <https://github.com/Ulm-IQO/qudi/>
"""

import numpy as np

from core.module import Connector, ConfigOption, StatusVar
from core.util.mutex import Mutex
from logic.generic_logic import GenericLogic
from qtpy import QtCore
import numpy as np
import time

class AnalogSteppersLogic(GenericLogic):
    """
    Control xyz steppers via "analog input"
    """
    _modclass = 'analogstepperslogic'
    _modtype = 'logic'

    # declare connectors
    hardware = Connector(interface='SteppersInterface')
    _ui_frequency = ConfigOption('ui_frequency', 10)
    _hardware_frequency = ConfigOption('hardware_frequency', 1000)
    _hardware_voltage = ConfigOption('hardware_voltage', 40)
    _axis = ConfigOption('axis', ('x', 'y', None))

    # signals
    sigUpdate = QtCore.Signal()
    timer = None

    _last_value = [0., .0, .0]
    _enabled = False

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

        self.threadlock = Mutex()

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        self._hardware = self.hardware()

        self.timer = QtCore.QTimer()
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.loop)

        self.setup_axis()
        self.startLoop()

    def setup_axis(self):
        """ Set axis as in config file"""
        for axis in self._axis:
            if axis:
                self._hardware.frequency(axis, self._hardware_frequency)
                self._hardware.voltage(axis, self._hardware_voltage)


    def on_deactivate(self):
        """ Perform required deactivation. """
        pass


    def startLoop(self):
        self._enabled = True
        self.start_timer()


    def stopLoop(self):
        self.timer.stop()
        self._enabled = False
        self._hardware.stop()


    def loop(self):
        if self._enabled:
            self.start_timer()
            self.move()

    def start_timer(self):
        self.timer.start(int(1000 * 1 / self._ui_frequency))

    def move(self):
        for axis in self._axis:
            if axis:
                i = self._axis.index(axis)
                value = self._last_value[i]
                self._last_value[i] = 0
                self.move_axis(axis, value)

    def move_axis(self, axis, analog):
        if analog == 0.:
            return
        if analog < -1. or analog > 1:
            self.log.error('Analog value must be between -1.0 and 1.0 : {}'.format(analog))
        steps = self._hardware_frequency / self._ui_frequency * analog
        steps = np.trunc(steps)
        self._hardware.steps(axis, steps)

    # Because why not
    def hello(self):
        """ Greet humans properly """

        axis = self._axis[0]
        notes = {'c': 261, 'd': 294, 'e': 329, 'f': 349, 'g': 391, 'gS': 415, 'a': 440, 'aS': 455, 'b': 466, 'cH': 523,
                 'cSH': 554, 'dH': 587, 'dSH': 622, 'eH': 659, 'fH': 698, 'fSH': 740, 'gH': 784, 'gSH': 830, 'aH': 880}

        first_section = [('a', 500), ('a', 500), ('a', 500), ('f', 350), ('cH', 150), ('a', 500), ('f', 350),
                         ('cH', 150), ('a', 650), ('', 500), ('eH', 500), ('eH', 500), ('eH', 500), ('fH', 350),
                         ('cH', 150), ('gS', 500), ('f', 350), ('cH', 150), ('a', 650), ('', 500)]
        second_section = [('aH', 500), ('a', 300), ('a', 150), ('aH', 500), ('gSH', 325), ('fSH', 125), ('fH', 125),
                          ('fSH', 250), ('', 325), ('aS', 250), ('dSH', 500), ('dH', 325), ('cSH', 175), ('cH', 125),
                          ('b', 125), ('cH', 250), ('', 350)]
        variant_1 = [('f', 250), ('gS', 500), ('f', 350), ('a', 125), ('cH', 500), ('a', 375), ('cH', 125), ('eH', 650),
                     ('', 500)]
        variant_2 = [('f', 250), ('gS', 500), ('f', 375), ('cH', 125), ('a', 500), ('f', 375), ('cH', 125), ('a', 650),
                     ('', 650)]
        total = first_section + second_section + variant_1 + second_section + variant_2
        count = 0
        up = True
        for note, duration in total:
            if note != '':
                frequency = notes[note]
                steps = int(frequency * (float(duration)/1000.))
                self._hardware.frequency(axis, frequency)
                if not up:
                    steps = -steps
                count += steps
                self._hardware.steps(axis, steps)
            time.sleep((duration + 50)/1000)
            up = not up
        self._hardware.steps(axis, -count)  # Back to origin
