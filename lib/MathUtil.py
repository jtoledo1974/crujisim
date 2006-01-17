#!/usr/bin/python
#-*- coding:iso8859-15 -*-
# $Id$
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
"""Vector algebra functions"""
from math import *
import logging

def s(a,b):
    return (a[0]+b[0],a[1]+b[1]) # Suma de vectores
    
def r(a,b):
    return (a[0]-b[0],a[1]-b[1]) # Resta de vectores
    
def p(a,b):
    return (a[0]*b,a[1]*b) #Multiplica el vector a x b
    
def rp(a): # Rextangulares a polares
    x=a[0]
    y=a[1]
    r=sqrt(pow(x,2)+pow(y,2))
    if r>0:
        ang=degrees(acos(y/r))
    else:
        ang=0.0
    if x<0:
        ang=360-ang
    return (r,ang)
    
def pr(a):  # Polares a rectangulares
    r=a[0]
    ang=a[1]
    return(r*sin(radians(ang)),r*cos(radians(ang)))
    
def sgn(a):
    if a<>0.:
        return a/abs(a)
    else:
        return 0

def get_h_m_s(t):
    try:
        ho=int(t/60/60)
        m=int(t/60)-ho*60
        s=int(t)-60*60*ho-60*m
    except:
        ho=m=s=0
        logging.error("Unable to format time "+str(t))
    return (ho,m,s)
