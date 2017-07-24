#!/usr/bin/env python
# -*- coding: utf-8 -*-

import warnings
import RPIO


def claim_pin(pin, config, io_type, comment=""):
    '''
    Claim a pin for use. This should be called before the pin is used as either
    input or output.

    Arguments:
    pin -- the pin to be claimed. Int
    config -- the config file to claim the pin in. config.Config
    comment -- a comment explaining what use the pin is claimed for.
    '''
    if pin in config.used_pins:
        raise AttributeError('pin {} already claimed'.format(pin))
    else:
        mode = RPIO.IN if io_type in ('in', 'IN', RPIO.IN) else RPIO.OUT
        RPIO.setup(pin, mode)
        config.used_pins[pin] = comment


def release_pin(pin, config):
    '''
    Release a pin
    '''
    if pin in config.used_pins:
        del config.used_pins[pin]
    else:
        if config.echo:
            warnings.warn('tried to release unclaimed pin')
