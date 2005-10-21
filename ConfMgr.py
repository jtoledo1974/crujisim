#!/usr/bin/python
#-*- coding:iso8859-15 -*-
# $Id: $
# (c) 2005 CrujiMaster (crujisim@yahoo.com)
#
# This file is part of CrujiSim.
#
# CrujiSim is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# CrujiSim is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with CrujiSim; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
"""Management of user preferences stored in app. configuration file"""

import ConfigParser
import logging

_config_file_name="crujisim.ini"

def read_option(section, name, default_value=None):
    """Returns current value for the specified option in the specified section.
    If there is no current value for this option (either the configuration file,
    the section or the option do not exist), return the value indicated in default_value.
    """
    cp=ConfigParser.ConfigParser()
    try:
        config_fp=open(_config_file_name, "r")
        cp.readfp(config_fp)
        config_fp.close()
    except:
        logging.warning("Trying to read config value, application configuration file missing.")        
    if cp.has_option(section, name):
        return cp.get(section, name)
    else:
        return default_value

def write_option(section, name, value):
    """Set new value for the specified option in the specified section.
    If the section or the option were not present before this call, create
    them. If the configuration file is missing, create it.
    """
    cp=ConfigParser.ConfigParser()
    try:
        config_fp=open(_config_file_name, "r")
        cp.readfp(config_fp)
        config_fp.close()
    except:
        logging.warning("Application configuration file missing. Creating it.")
    if not(cp.has_section(section)):
        cp.add_section(section)
    cp.set(section, name, value)
    config_fp=open(_config_file_name, "w+")
    cp.write(config_fp)
    config_fp.close()

