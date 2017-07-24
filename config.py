#!/usr/bin/env python
# -*- coding: utf-8 -*-

import configparser

class Config:

    def __init__(self, config_path):
        self.config_path = config_path
        self.used_pins = None
        self.echo = None
        self.reserved_channels = None
        self.get_vars()

    def get_vars(self):
        config = configparser.ConfigParser()
        config.read(self.config_path)
        used_pins = config['temp_init']['used_pins']
        used_pins = used_pins.split(',')
        self.used_pins = {int(x.split(':')[0]):x.split(':')[1] for x in used_pins if x != ''}
        print(self.used_pins)
        reserved_channels = config['RPIO']['reserved_channels']
        reserved_channels = reserved_channels.split(',')
        self.reserved_channels = [int(x) for x in reserved_channels if x != '']
        self.echo = config['py_behavior']['echo']

    def write(self):
        config = configparser.ConfigParser()
        config.read(self.config_path)
        # Permanent variables go here
        with open(self.config_path, 'w') as file:
            config.write(file)
