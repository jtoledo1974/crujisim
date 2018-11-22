#!/usr/bin/env python
# -*- coding:utf-8 -*-
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

"""Classes dealing with routes and waypoints"""
from __future__ import print_function
from __future__ import absolute_import
from builtins import range
from builtins import object

import logging
import re
from . import MathUtil

# Restrictions
AABV = 0  # At or above
ABLW = 1  # At or below
LVL = 3  # Cross established

# Waypoint Types
WAYPOINT = 0
FMS = 1  # FMS added to implement a IAP, for instance
TLPV = 2  # Added by the TLPV to calculate a sector entry time, for instance


def is_str(item):
    """Check for str type in a python2 / python 3 compatible way"""
    try:
        res = isinstance(item, str) or isinstance(item, unicode)
    except NameError:
        res = isinstance(item, str)
    return res


def get_waypoints(item):
    """Given a route either as a string, or a list of waypoints,
    or a list of fix strings, returns a list of waypoints"""
    if is_str(item):
        points = item.replace(",", " ").strip().split()
        return [WP(p) for p in points]
    elif isinstance(item, WP):
        return [item]
    elif isinstance(item, list):
        rlist = []
        for wp in item:
            if isinstance(wp, WP):
                rlist.append(wp)
            elif isinstance(wp, str):
                rlist.append(WP(wp))
            else:
                raise TypeError('get_waypoints: Unable to extract waypoint list from ' + str(item))
        return rlist
    else:
        raise TypeError('get_waypoints: Unable to extract waypoint list from ' + str(item))


class Route(list):

    # Methods which adapt the list object to our use

    # TODO IMPORTANT!
    # We need to add methods to make sure that inbd and outbound tracks
    # are deleted in the waypoints whenever the route is modified

    def __init__(self, inlist=[], raise_on_unknown=False, insert_on_unknown=False, check=True):
        # Whether or not an exception is raised
        # when a waypoint is added with coords unknown
        self.raise_on_unknown = raise_on_unknown
        # Whether or not a waypoint whose coordinates are unknown
        # is added to the route
        self.insert_on_unknown = insert_on_unknown
        if check:
            for wp in inlist:
                if not self.check_wp(wp):
                    inlist.remove(wp)
        list.__init__(self, inlist)

    def __getslice__(self, i, j):
        return Route(list.__getslice__(self, i, j))

    def __getitem__(self, key):
        if isinstance(key, slice):
            item = list.__getitem__(self, key)
            return Route(item, check=False)

        return list.__getitem__(self, self.index(key))

    def append(self, wp):
        if self.check_wp(wp):
            list.append(self, wp)
        prev = list.__getitem__(self, -1)
        prev.inbd_track = None
        prev.outbd_track = None
        try:
            list.__getitem__(self, -1).outbd_track = None
        except Exception:
            pass

    def insert(self, index, wp):
        if self.check_wp(wp):
            list.insert(self, index, wp)
        wp.inbd_track = None
        wp.outbd_track = None
        try:
            list.__getitem__(self, index + 1).inbd_track = None
        except Exception:
            pass
        try:
            list.__getitem__(self, index - 1).outbd_track = None
        except Exception:
            pass

    def __add__(self, other):
        for wp in other[:]:
            if not self.check_wp(wp):
                other.remove(wp)
        r = Route(list.__add__(self, other))
        r.clear_tracks()
        return r

    def __contains__(self, item):
        if is_str(item):
            return item.upper() in (wp.fix for wp in self)
        elif isinstance(item, WayPoint):
            return list.__contains__(self, item)
        else:
            raise TypeError("%s is not type str nor WayPoint" % item)

    def __repr__(self):
        return ', '.join(repr(wp) for wp in self)

    def __str__(self):
        return ', '.join((str(wp) for wp in self))

    # Methods specific to the Route object, meant to be used by external users

    def substitute_after(self, wp, list, save=None):
        """Substitutes the list of waypoints after the given waypoint
        Will not perform the substitution if the waypoint given in the save parameter is absent in the result"""
        flag = True
        # It's not appropriate to use index
        # because we are beginning the search from the back
        if save:
            save = WayPoint(save)
        for i in range(len(self) - 1, -1, -1):
            if wp == self[i] or wp.upper() == self[i].fix:
                flag = False
                after_route = Route(list)
                if save and save.fix not in [wp.fix for wp in self[:i + 1]] \
                        and save.fix not in [wp.fix for wp in after_route]:
                    logging.debug("Did not substitute %s after %s in order to save %s" % (
                        after_route, self[i].fix, save.fix))
                    break
                del self[i + 1:]
                self.extend(after_route)
                break
        if flag:
            raise "Waypoint %s not found in %s" % (str(wp), str(self))

    def substitute_before(self, wp, list, save=None):
        """Substitutes the list of waypoints before the given waypoint
        Will not perform the substitution if the waypoint given in the save parameter is absent in the result"""
        if save:
            save = WayPoint(save)
        i = self.index(wp)
        before_route = Route(list)
        if save and save.fix not in [wp.fix for wp in self[i:]] \
                and save.fix not in [wp.fix for wp in before_route]:
            logging.debug("Did not substitute %s before %s in order to save %s" % (
                before_route, self[i].fix, save.fix))
            return
        del self[:i]
        new = before_route + self
        del self[:]
        # TODO I'm sure there must be a proper way to do this.
        for wp in new:
            self.append(wp)

    def delete_from(self, wp):
        """Delete all waypoints after and including wp. Silently return if not present"""
        if type(wp) != WayPoint:
            wp = WayPoint(wp)

        for i, e in reversed(list(enumerate(self))):
            if e == wp:
                break

        for i in range(len(self) - 1, i - 1, -1):
            self.pop(i)

    def get_inbd_track(self, wp):
        """Returns the inbound track to the given waypoint"""
        i = self.index(wp)
        length = len(self)

        if i >= 0 and i < length:
            wp = self[i]
            if wp.inbd_track:
                return wp.inbd_track
        # else

        if i < 1:
            wp_to = self[1]
            wp_from = wp
        elif i > length - 1:  # When calculating the outbound track of the last point
            wp_to = self[length - 1]
            wp_from = self[length - 2]
        else:
            wp_to = wp
            wp_from = self[i - 1]

        (distance, bearing) = MathUtil.rp(
            MathUtil.r(wp_to.pos, wp_from.pos))
        wp_to.inbd_track = bearing
        return bearing

    def get_outbd_track(self, wp):
        """Returns the outbound track after the given waypoint"""
        i = self.index(wp)
        wp = self[i]
        if i >= 0 and i < len(self) and wp.outbd_track:
            return wp.outbd_track
        # else
        wp.outbd_track = ot = self.get_inbd_track(i + 1)
        return ot

    def legs(self):
        """Returns a list of each of the route legs"""
        list = []
        if len(self) < 2:
            list
        # else
        for i in range(len(self) - 1):
            list.append(self[i:i + 2])
        return list

    def reduce(self):
        """Returns a copy of itself with redundancy eliminated"""

        if len(self) < 2:
            self.clear_tracks()
            return self

        wp0, wp1 = self[0], self[1]
        if self[0] == self[1]:
            if wp1.is_geo and not wp0.is_geo:
                wp1.fix = wp0.fix
                wp1.type = wp0.type
                wp1.is_geo = False
            for attr in ('sector_entry', 'sector_exit', 'eto', 'ato'):
                if getattr(wp0, attr) and not getattr(wp1, attr):
                    setattr(wp1, attr, getattr(wp0, attr))
            wp1.inbd_track = wp0.inbd_track
            return self[1:].reduce()
        else:
            return self[:1] + self[1:].reduce()

    def copy(self):
        """Returns a copy of self using copied waypoints"""
        r = Route()
        for wp in self:
            r.append(wp.copy())
        return r

    # Helper methods, used internally within the object

    def check_wp(self, wp):
        """Checks whether a given waypoint is of the right class, and verifies
        the existence or not of wp coordinates against this route's rules"""
        try:
            wp.pos
        except AttributeError:
            raise TypeError("Element " + str(wp) + " is not WayPoint instance")
        except Exception:
            if self.raise_on_unknown:
                raise RuntimeError("Unknown coordinates for waypoint " + str(wp))
            else:
                logging.warning("Unknown coordinates for waypoint " + str(wp))
                if self.insert_on_unknown:
                    return True
                else:
                    return False
        return True

    def index(self, index):
        """Given a waypoint either as an index, a WP instance, or a fix name,
        return the route index of the first wp that matches"""

        if isinstance(index, WP):
            return list.index(self, index)

        if is_str(index):
            index = index.upper()
            for pos, item in enumerate(self):
                if index == item.fix:
                    return pos

        if isinstance(index, int):
            return index

        raise TypeError(
            "Unable to find route index for waypoint " + str(index))

    def reverse_index(self, index):
        """Given a waypoint either as an index, a WP instance, or a fix name,
        return the route index of the last wp that matches"""

        i_prime = self[::-1].index(index)
        return len(self) - 1 - i_prime

    def clear_tracks(self):
        for wp in self:
            wp.inbd_track = None
            wp.outbd_track = None


class WayPoint(object):

    def __init__(self, fix, pos=None, eto=None, xfl=None, xfl_type=None, type=WAYPOINT):

        # If we get a WayPoint passed as the init parameter
        if isinstance(fix, WayPoint):
            fix = fix.fix

        self.fix          = fix.upper()
        self.pos          = pos
        self.type         = type
        self.eto          = eto       # Estimated time overhead. Datetime object.
        self.xfl          = xfl
        self.xfl_type     = xfl_type  # Use one of the restriction constants AABV, ABLW, LVL
        self.ato          = None      # Actual time over the waypoint
        self.is_geo       = False     # Whether the waypoint was created using coordinates
        self.inbd_track   = None
        self.outbd_track  = None
        self.sector_entry = None      # Sector this waypoint marks the entry to
        self.sector_exit  = None      # Sector this waypoint marks the exit of

        # If given in the appropriate format, store the position
        try:
            if fix[0].upper() == "X":
                v = re.match(
                    "X([-+]?(\d+(\.\d*)?|\d*\.\d+))Y([-+]?(\d+(\.\d*)?|\d*\.\d+))", fix.upper()).groups()
                self.pos = (float(v[0]), float(v[3]))
                self.fix = "X%.1fY%.1f" % self.pos
                self.is_geo = True
        except Exception:
            pass

        if self.pos is None:
            from . import AIS
            try:
                self.pos = AIS.points[self.fix].pos
            except KeyError:
                # TODO With AIXM this shouldn't happen
                logging.warning("Adding waypoint %s with no available position", self.fix)
                self.pos = (0, 0)

    def pos(self):
        return self.pos

    def copy(self):
        wp = WayPoint(self.fix)
        wp.__dict__ = self.__dict__.copy()
        return wp

    def __repr__(self):
        s = self.fix
        if self.ato:
            t = self.ato
        elif self.eto:
            t = self.eto
        try:
            s += "(%02d%02d)" % (t.hour, t.minute)
        except Exception:
            pass
        return s

    def __str__(self):
        return self.fix

    def __eq__(self, other):
        """Check whether two waypoints may be considered the same (within 0.1 nm)"""
        if not isinstance(other, WayPoint):
            return False
        try:
            if MathUtil.get_distance(self.pos, other.pos) < 0.1:
                return True
            else:
                return False
        except Exception:
            # The previous test may fail for unknown points
            return False

    def __ne__(self, other):
        return not self.__eq__(other)


WP = WayPoint
