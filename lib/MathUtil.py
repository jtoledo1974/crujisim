#!/usr/bin/python
#-*- coding:iso8859-15 -*-
# $Id$
# (c) 2005 CrujiMaster (crujisim@crujisim.cable.nu)
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

EXIT = 'EXIT'
ENTRY = 'ENTRY'


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

def dp(a, b):
    """Dot product of vectors a and b"""
    return a[0]*b[0]+a[1]*b[1]
    
def sgn(a):
    if a<>0.:
        return a/abs(a)
    else:
        return 0
    
def get_distance(pA,pB):
    return ((pA[0]-pB[0])**2 + (pA[1]-pB[1])**2)**(0.5)

def point_within_polygon(point, pointsList):
        "Return True if point is contained in polygon (defined by given list of points.)"

        assert len(pointsList) >= 3, 'Not enough points to define a polygon (I require 3 or more.)'
        assert len(point) >= 2, 'Not enough dimensions to define a point(I require 2 or more.)'

        # If given values are ints, code will fail subtly. Force them to floats.
        x,y = float(point[0]), float(point[1])
        xp = [float(p[0]) for p in pointsList]
        yp = [float(p[1]) for p in pointsList]

        # Initialize loop
        c=False
        i=0
        npol = len(pointsList)
        j=npol-1

        while i < npol:
                if ((((yp[i]<=y) and (y<yp[j])) or
                        ((yp[j]<=y) and(y<yp[i]))) and
                        (x < (xp[j] - xp[i]) * (y - yp[i]) / (yp[j] - yp[i]) + xp[i])):
                        c = not c
                j = i
                i += 1

        return c

def pfloat(a0):
    """promotes all elements of a0 to float"""
    try:
        a = [float(elements) for elements in a0]
        return a
    except:
        return None
        

def get_line_equation(pa0,pa1):
    """calculates the line equation m,b from two points"""
    #promotes to float
    #a0 = pfloat(pa0)
    #a1 = pfloat(pa1)
    a0, a1 = pa0, pa1
    d = a1[0]-a0[0]
    try:
        m = (a1[1]-a0[1])/d
        b = a0[1]-m*a0[0]
        return (m,b)
    except:
        return (None,a0)

def get_cross_point(pa0,pa1,pb0,pb1):
    """calculates crossing point's coordinates given the coordinates of four points
    if both segments are equivalent the method returns de point on segment b closest to pa0"""
    #Promotes to float
    #a0=pfloat(pa0)
    #a1=pfloat(pa1)
    #b0=pfloat(pb0)
    #b1=pfloat(pb1)
    a0, a1, b0, b1 = pa0, pa1, pb0, pb1

    l1 = get_line_equation(a0,a1)
    l2 = get_line_equation(b0,b1)

    # Most common case first. Two non parallel, non vertical lines
    try:
        d = l1[0]-l2[0]
        x1 = (l2[1]-l1[1])/d
        y1 = (l2[1]*l1[0]-l1[1]*l2[0])/d
        return (x1,y1)
    except: pass
    
    # Didn't work, let's see the border cases
    if not l1[0] and not l2[0]:
        if l1[1] == l2[1]:
            #If both lines are the same and vertical, returns the point on segment b
            #closest to pa0
            d00 = (a0[0]-b0[0])**2+(a0[1]-b0[1])**2
            d01 = (a0[0]-b1[0])**2+(a0[1]-b1[1])**2
            if d00 <= d01: return b0
            else: return b1
        else:
            # Parallel vertical lines
            return None
    elif not l1[0]:
        # First line is vertical, second is not        
        x1 = a0[0]
        y1 = l2[0]*x1+l2[1]
        return (x1,y1)
    elif not l2[0]:
        # Second line is vertical, first is not
        x1 = b0[0]
        y1 = l1[0]*x1+l1[1]
        return (x1,y1)
    elif l1[1] == l2[1]:
        #If both lines are the same and not vertical, returns the point on segment b
        #closest to pa0
        d00 = (a0[0]-b0[0])**2+(a0[1]-b0[1])**2
        d01 = (a0[0]-b1[0])**2+(a0[1]-b1[1])**2
        if d00 < d01: return b0
        else: return b1
    else:
        # We should have covered all cases previously
        logging.error("get_cross_point: Imposible scenario")
        return None
    
def calculates_intersection(pA0,pA1,pB0,pB1,use_given_coordinates = True):
    """calculates intersection between line defined by pA0,pA1 and line defined by pB0,pB1"""
    ###returns a point which name is pA0's name + "#" + pA1's name + "@" + pB0's name + "#" + pB1's name
    xP = ["A",[0.0,0,0]]
    if use_given_coordinates:
        #Tuples of points' names and coordinates are passed
        try:
            xP[0]= pA0[0]+"#"+pA1[0]+"@"+pB0[0]+"#"+pB1[0]
            xP[1] = get_cross_point(pA0[1],pA1[1],pB0[1],pB1[1])
            return xP
        except:
            return None
    else:
        #In this case, only points' names are passed
        try:
            xP[0]= pA0+"#"+pA1+"@"+pB0+"#"+pB1
            pList = [pA0, pA1,pB0,pB1]
            pListC = [get_point_coordinates(elements) for elements in pList]
            xP[1] = get_cross_point(pListC[0],pListC[1],pListC[2],pListC[3])
            return xP
        except:
            return None
        
#def point_within_segment(pA,sA0,sA1):
#    """Returns true if pA lies within the segment sA0-sA1. Coordinates Tuples are passed
#        if pA == sA0 or sA1 also returns true"""
#    if sA0[0] == sA1[0]:
#        # vertical segment, check y coordinates.
#        min_sA_Y = min(sA0[1],sA1[1])
#        max_sA_Y = max(sA0[1],sA1[1])
#        if (pA[1] >= min_sA_Y) and (pA[1] <= max_sA_Y):
#            return True
#        else:
#            return False
#    else:
#        # horizontal segment or generic segment, check x coordinates.
#        min_sA_X = min(sA0[0],sA1[0])
#        max_sA_X = max(sA0[0],sA1[0])
#        if (pA[0] >= min_sA_X) and (pA[0] <= max_sA_X):
#            return True
#        else:
#            return False

def point_within_segment(pA,sA0,sA1):
    """Returns true if pA lies within the segment sA0-sA1. Points Tuples are passed
        if pA == sA0 or pA == sA1 also returns true"""
    (px,py),(s0x,s0y),(s1x,s1y)=pA,sA0,sA1    
    outside = (px>s0x and px>s1x) or (px<s0x and px<s1x) or \
              (py>s0y and py>s1y) or (py<s0y and py<s1y)
    return not outside
    
def get_entry_exit_points(pA0,pA1,poly):
    """Returns a list with entry and exit points of the path defined
    by segment pA0 -> pA1 when crosses polygon poly, method uses coordinates points
    WARNING: For efficiency reasons we are assuming that all inputs are floats.
    There WILL be problems if they are not, but it's too expensive to promote them
    to floats here. Make sure your data is correct.
    """
    
    pA0_in = point_within_polygon(pA0,poly)
    pA1_in = point_within_polygon(pA1,poly)
    N = len(poly)
    x_points=[]
    #Find all intersectings points
    for i in range(0,N-1):
        pA_x_poly = get_cross_point(pA0,pA1,poly[i],poly[i+1])
        if pA_x_poly != None:
            #There is a crossing point, check if it is within segment poly[i]->poli[i+1] and
            # between pA0 -> pA1
            test1 = point_within_segment(pA_x_poly,poly[i],poly[i+1])
            test2 = point_within_segment(pA_x_poly,pA0,pA1)
            if test1 and test2:
                x_points.append(["Unknown",pA_x_poly,get_distance(pA0,pA_x_poly)])
    
    #Now we sort the points by distance to pA0
    if len(x_points) == 0:
        return []
    else:
        if len(x_points) > 1: x_points.sort(lambda p,q: cmp(p[2],q[2]))
        type = ENTRY
        if pA0_in: type = EXIT   #pA0 is inside the poly, so the first point is an exit point
        for element in x_points:
            element[0] = type
            type = not type
        return x_points
    
if __name__=='__main__':
    print r((10,10),(0,10))
    assert point_within_polygon((0.1,0.1),((0,0),(0,1),(1,0))) == True
    assert point_within_polygon((0,0),((0,0),(0,1),(1,0))) == True
    assert point_within_polygon((1,1),((0,0),(0,1),(1,0))) == False
