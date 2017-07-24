#!/usr/bin/env python
# -*- coding: utf-8 -*-

try:
    import RPIO
    import RPIO.PWM
    from RPIO.PWM import _PWM
except (ImportError, SystemError):
    print("Couldn't import RPIO")
import warnings
from abc import ABCMeta, abstractproperty
import utility


class ABCServo(metaclass=ABCMeta):
    '''
    Abstract base class for servos.

    Attributes:
    controller (Output Controller) -- the owning output controller.
    name (str) -- the name used to reference the servo.
    pin (int) -- the GPIO pin connected to the servo's signal lead.
    channel (RPIO.PWM.Servo) -- the channel used for managing PWM.

    Abstract Properties:
    pulse (numeric) -- the pulse width delivered to the GPIO pin.
    '''

    def __init__(self, controller, name, pin, channel):
        self.controller = controller
        self.channel = channel
        self.name = name
        self.pin = pin

    def update(self):
        '''
        Updates the signal to the GPIO pin.
        '''
        if self.pulse is not None:
            self.controller.set_servo(self.pin, self.pulse)

    @abstractproperty
    def pulse(self):
        pass


class Servo(ABCServo):
    '''
    Class describing and controlling a standard servo. Subclass of ABCServo.

    Arguments:
        controller (Output Controller) -- the owning output controller.
        name (str) -- the name used to reference the servo.
        pin (int) -- the GPIO pin connected to the servo's signal lead.
        channel (RPIO.PWM.Servo) -- the channel used for managing PWM.
        range_of_motion (int) -- the total range of motion expressed in degrees.
            defaults to 90.
        pulse (tuple) -- the minimum and maximum pulse width. 
            defaults to (1.0, 2.0)
        reverse (bool) -- True if the maximum pulse width corresponds with a 
            nominal position of 0; False if the maximum pulse width corresponds 
            with a nominal position equal to range_of_motion. 
            defaults to False.ABCMeta

    Attributes:
        controller (Output Controller) -- the owning output controller.
        name (str) -- the name used to reference the servo.
        pin (int) -- the GPIO pin connected to the servo's signal lead.
        channel (RPIO.PWM.Servo) -- the channel used for managing PWM.
        range_of_motion (numeric) -- the total range of motion expressed in 
            degrees. Defaults to 90.
        pulse (tuple) -- the minimum and maximum pulse width. 
            Defaults to (1.0, 2.0)
        reverse (bool) -- True if the maximum pulse width corresponds with a 
            nominal position of 0; False if the maximum pulse width corresponds 
            with a nominal position equal to range_of_motion. 
            Defaults to False.ABCMeta
        angle (numeric) -- the current set position (not necessarily the 
            actual current position). Defaults to 0.
    '''

    def __init__(self, controller, name, pin, channel, range_of_motion=90, 
                 pulse=(1.0, 2.0), reverse=False):
        super().__init__(controller, name, pin, channel)
        self.range = range_of_motion
        self.pulse = sorted(pulse)
        self.reverse = reverse
        self.angle = 0

    def set(self, angle):
        '''
        Sets the servo angle and updates it.

        Arguments:
            angle (numeric) -- the angle to set the servo to. Must be between
                0 and self.range.
        '''
        if not 0 < angle < self.range:
            raise ValueError('angle must be between 0 and range')
        self.angle = angle
        self.update()

    def increment(self, change):
        '''
        Moves the servo by a set amount.

        Arguments:
            change (numeric) -- the amount to adjust the servo.
        '''
        self.set(self.angle + change)

    @property
    def pulse(self):
        '''
        The pulse width for the servo.
        '''
        position_ratio = self.angle / self.range
        position_ratio *= -1 if self.reverse else 1
        pulse_range = max(self.pulse) - min(self.pulse)
        pulse_incr = _PWM.get_pulse_incr_us()
        pulse = pulse_range * position_ratio + min(self.pulse)
        pulse = pulse // pulse_incr
        pulse *= pulse_incr
        return pulse


class ContinousServo(ABCServo):

    def __init__(self, controller, name, pin, channel, pulse, reverse=False):
        super().__init__(self, controller, name, pin, channel)
        self.reverse = reverse
        self.speed = 0

    def set(self, speed):
        if not -1 < speed < 1:
            raise ValueError('speed must be between -1 and 1')
        self.speed = speed

    def increment(self, change):
        self.set(self.speed + change)

    @property
    def pulse(self):
        zero_pulse = (min(self.pulse) + max(self.pulse)) / 2
        pulse_range = max(self.pulse) - min(self.pulse)
        return zero_pulse + self.speed * pulse_range / 2


class LED:

    def __init__(self, name, pin, channel):
        self.name = name
        self.pin = pin
        self.channel = channel
        self.brightness = 0

    def set(self, brightness):
        if not 0 < brightness < 100:
            raise ValueError('brightness must be between 0 and 100')
        self.brightness = brightness

    def update(self):
        subcycle_time = RPIO.PWM.get_channel_subcycle_time_us(self.channel)
        granularity = RPIO.PWM.get_pulse_incr_us()
        pulse_width = self.brightness / 100 * subcycle_time / granularity
        RPIO.PWM.clear_channel_gpio(self.channel, self.pin)
        RPIO.PWM.add_channel_pulse(self.channel, self.pin, 0, pulse_width)


class OutputController:

    def __init__(self, config):
        RPIO.setmode(RPIO.BOARD)
        # update (int): channel (int)
        self.update_channels = {}
        # channel (int): RPIO.Servo
        self.channel_servos = {}
        # name (str): Servo
        self.servos = {}
        # name (str): Actuator
        self.actuators = {}
        # name (str): LED
        self.leds = {}
        self.config = config

    def new_servo(self, name, pin, update=20000, range_of_motion=90,
                  pulse=(1.0, 2.0), reverse=False):
        channel = self.get_servo_channel(update)
        utility.claim_pin(pin, RPIO.OUT, self.config,
                          'servo {}'.format(name))
        servo = Servo(self, name, pin, channel, range_of_motion, pulse, reverse)
        self.servos['name'] = servo
        return servo

    def new_continuous_servo(self, name, pin, pulse, reverse=False):
        channel = self.get_servo_channel()
        utility.claim_pin(pin, RPIO.OUT, self.config, 
                          'continuous servo {}'.format(name))
        servo = ContinousServo(name, pin, channel, pulse, reverse)
        self.servos['name'] = servo
        return servo

    def new_led(self, name, pin):
        if self.update_channels:
            channel = self.update_channels[list(self.update_channels.keys())[0]]
        else:
            channel = self.new_dma_channel()
        utility.claim_pin(pin, RPIO.OUT, self.config, 'led {}'.format(name))
        led = LED(name, pin, channel)
        self.leds['name'] = led
        return led

    def get_servo_channel(self, update_cycle=None):
        try:
            if update_cycle is None:
                return self.channel_servos[self.update_channels[
                       list(self.update_channels.keys())[0]]]
            return self.channel_servos[self.update_channels[update_cycle]]
        except (KeyError, IndexError):
            if update_cycle not in self.channel_servos:
                return self.new_servo_channel(update_cycle)
            else:
                raise AttributeError('inconsistency between update_channels and\
                                      channel_servos with update cycle \
                                      {}'.format(update_cycle))

    def new_servo_channel(self, update_cycle, channel=None):
        channel = self.new_dma_channel(update_cycle, channel)
        new_servo_channel = RPIO.PWM.Servo(channel, update_cycle)
        self.channel_servos[channel] = new_servo_channel
        return new_servo_channel

    def new_dma_channel(self, update_cycle=None, channel=None):
        if update_cycle in self.update_channels:
            if self.config.echo:
                warnings.warn('replacing servo channel with update_cycle \
                              {}'.format(update_cycle))
        if channel is None:
            channel = self.get_dma_channel()
            if channel is None:
                raise RuntimeError('no available dma channel')
        self.update_channels[update_cycle] = channel
        return channel     

    def get_dma_channel(self):
        available = [x for x in range(15) if
                     (x not in self.config.reserved_channels and
                      x not in self.channel_servos)]
        if available:
            return available[0]
        else:
            return
