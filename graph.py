#!/usr/bin/env python
#
# $Header$
#
#
# Copyright (C) 2002 J�rg Lehmann <joergl@users.sourceforge.net>
# Copyright (C) 2002 Andr� Wobst <wobsta@users.sourceforge.net>
#
# This file is part of PyX (http://pyx.sourceforge.net/).
#
# PyX is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# PyX is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with PyX; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

from path import *
import types, re, tex, unit, math
from math import log, exp, sqrt, pow

def _powi(x, y):
    assert type(y) == types.IntType
    assert y >= 0
    if y:
        y2 = y / 2 # integer division!
        yr = y % 2
        res = _powi(x, y2)
        if yr:
           return x * res * res
        else:
           return res * res
    else:
        return 1

class _ticklength(unit.length):

    _base      = 0.15
    _factor    = sqrt(2)

    def __init__(self, l = _base, power = 0, factor = _factor):
        self.factor = factor
        unit.length.__init__(self, l = l * pow(self.factor, power), default_type="v")

    def increment(self, power = 1):
        return pow(self.factor, power) * self


class ticklength(_ticklength):

    SHORT      = _ticklength(power = -6)
    SHORt      = _ticklength(power = -5)
    SHOrt      = _ticklength(power = -4)
    SHort      = _ticklength(power = -3)
    Short      = _ticklength(power = -2)
    short      = _ticklength(power = -1)
    normal     = _ticklength()
    long       = _ticklength(power = 1)
    Long       = _ticklength(power = 2)
    LOng       = _ticklength(power = 3)
    LONg       = _ticklength(power = 4)
    LONG       = _ticklength(power = 5)


class _Map:
    def setbasepts(self, basepts):
        """base points for convertion"""
        self.basepts = basepts
        return self

    def convert(self, Values):
        if type(Values) in (types.IntType, types.LongType, types.FloatType, ):
            return self._convert(Values)
        else:
            return map(lambda x, self = self: self._convert(x), Values)

    def invert(self, Values):
        if type(Values) in (types.IntType, types.LongType, types.FloatType, ):
            return self._invert(Values)
        else:
            return map(lambda x, self = self: self._invert(x), Values)

class _LinMap(_Map):
    def _convert(self, Value):
        return self.basepts[0][1] + ((self.basepts[1][1] - self.basepts[0][1]) /
               float(self.basepts[1][0] - self.basepts[0][0])) * (Value - self.basepts[0][0])
    def _invert(self, Value):
        return self.basepts[0][0] + ((self.basepts[1][0] - self.basepts[0][0]) /
               float(self.basepts[1][1] - self.basepts[0][1])) * (Value - self.basepts[0][1])

class _LogMap(_LinMap):
    def setbasepts(self, basepts):
        """base points for convertion"""
        self.basepts = ((log(basepts[0][0]), basepts[0][1], ),
                        (log(basepts[1][0]), basepts[1][1], ), )
        return self
    def _convert(self, Value):
        return _LinMap._convert(self, log(Value))
    def _invert(self, Value):
        return exp(_LinMap._invert(self, Value))
               


###############################################################################
# axis part

class Tick:

    def __init__(self, ValuePos, VirtualPos, Label = None, LabelRep = None, TickLevel = 0, LabelLevel = 0):
        if not LabelRep:
            LapelRep = Label
        self.ValuePos = ValuePos
        self.VirtualPos = VirtualPos
        self.Label = Label
        self.LabelRep = LabelRep
        self.TickLevel = TickLevel
        self.LabelLevel = LabelLevel


class _Axis:

    def __init__(self, min = None, max = None, reverse = 0, title = None):
        self.fixmin = (min != None)
        self.fixmax = (max != None)
        self.min = min
        self.max = max
        self.title = title
        self.reverse = reverse
        self.setrange()

    def setrange(self, min = None, max = None):
        if (not self.fixmin) and (min != None):
            self.min = min
        if (not self.fixmax) and (max != None):
            self.max = max
        if (self.min != None) and (self.max != None):
            if self.reverse:
                self.setbasepts(((self.min, 1,), (self.max, 0,)))
            else:
                self.setbasepts(((self.min, 0,), (self.max, 1,)))

    def TickValPosList(self):
        TickCount = 4
        return map(lambda x, self = self, TickCount = TickCount: self._invert(x / float(TickCount)), range(TickCount + 1))

    def ValToLab(self, x):
        return "%.3f" % x

    def TickList(self):
        return map(lambda x, self=self: Tick(x, self.convert(x), self.ValToLab(x)), self.TickValPosList())


class frac:

    def __init__(self, enum, denom):
        assert type(enum) in (types.IntType, types.LongType, )
        assert type(denom) in (types.IntType, types.LongType, )
        self.enum = enum
        self.denom = denom

    def __str__(self):
        return "%i/%i" % (self.enum, self.denom, )


epsilon = 1e-10

class frac:

    def __init__(self, enum, denom):
        assert type(enum) in (types.IntType, types.LongType, )
        assert type(denom) in (types.IntType, types.LongType, )
        assert denom != 0
        self.enum = enum
        self.denom = denom

    def __cmp__(self, other):
        if other == None:
            return 1
        return cmp(self.enum * other.denom, other.enum * self.denom)

    def __mul__(self, other):
        return frac(self.enum * other.enum, self.denom * other.denom)

    def __float__(self):
        return float(self.enum) / self.denom

    def __str__(self):
        return "%i/%i" % (self.enum, self.denom)

    def __repr__(self):
        return "frac(%s, %s)" % (repr(self.enum), repr(self.denom)) # I want to see the "L"


class tick(frac):

    def __init__(self, enum, denom, ticklevel = 0, labellevel = 0):
        # ticklevel and labellevel are allowed to be None (in order to skip ticks or labels)
        frac.__init__(self, enum, denom)
        self.ticklevel = ticklevel
        self.labellevel = labellevel

    def __repr__(self):
        return "tick(%s, %s, %s, %s)" % (repr(self.enum), repr(self.denom), self.ticklevel, self.labellevel)

    def merge(self, other):
        assert self == other
        if (self.ticklevel == None) or ((other.ticklevel != None) and (other.ticklevel < self.ticklevel)):
            self.ticklevel = other.ticklevel
        if (self.labellevel == None) or ((other.labellevel != None) and (other.labellevel < self.labellevel)):
            self.labellevel = other.labellevel


class anypart:

    def mergeticklists(self, list1, list2):
        # caution: side effects
        i = 0
        j = 0
        try:
            while 1: # we keep on going until we reach an index error
                while list2[j] < list1[i]: # insert tick
                   list1.insert(i, list2[j])
                   i = i + 1
                   j = j + 1
                if list2[j] == list1[i]: # merge tick
                   list1[i].merge(list2[j])
                   j = j + 1
                i = i + 1
        except IndexError:
            if j < len(list2):
                list1 += list2[j:]
        return list1


class linpart(anypart):

    def __init__(self, min, max, tickfracs = None, labelfracs = None, extendtoticklevel = 0, extendtolabellevel = None):
        """
        zero-level labelfracs are created out of the zero-level tickfracs when labelfracs are None
        all-level tickfracs are created out of the all-level labelfracs when tickfracs are None
        get ticks but avoid labels by labelfracs = ()
        get labels but avoid ticks by tickfracs = ()

        We do not perform the adjustment of tickfracs or labelfracs within this
        constructor, but later in getticks in order to allow for a change by
        parameters of getticks. That can be used to create other partition schemes
        (which create several posibilities) by derivating this class.
        """
        self.min = min
        self.max = max
        self.tickfracs = tickfracs
        self.labelfracs = labelfracs
        self.extendtoticklevel = extendtoticklevel
        self.extendtolabellevel = extendtolabellevel

    def extendminmax(self, min, max, frac):
        return (float(frac) * math.floor(min / float(frac) + epsilon),
                float(frac) * math.ceil(max / float(frac) - epsilon))

    def getticklist(self, min, max, frac, ticklevel = None, labellevel = None):
        ticks = []
        imin = int(math.ceil(min / float(frac) - 0.5 * epsilon))
        imax = int(math.floor(max / float(frac) + 0.5 * epsilon))
        for i in range(imin, imax + 1):
            ticks.append(tick(long(i) * frac.enum, frac.denom, ticklevel = ticklevel, labellevel = labellevel))
        return ticks

    def getticks(self, tickfracs = None, labelfracs = None):
        """
        When tickfracs or labelfracs are set, they will be taken instead of the
        values provided to the constructor. It is not allowed to provide something
        to tickfracs and labelfracs here and at the constructor at the same time.
        """
        if (tickfracs == None) and (labelfracs == None):
            tickfracs = self.tickfracs
            labelfracs = self.labelfracs
        else:
            assert self.tickfracs == None
            assert self.labelfracs == None
        if tickfracs == None:
            if labelfracs == None:
                tickfracs = ()
            else:
                tickfracs = labelfracs
        if labelfracs == None:
            if len(tickfracs):
                labelfracs = (tickfracs[0], )
            else:
                labelfracs = ()

        min = self.min
        max = self.max

        if self.extendtoticklevel != None:
            (min, max, ) = self.extendminmax(min, max, tickfracs[self.extendtoticklevel])
        if self.extendtolabellevel != None:
            (min, max, ) = self.extendminmax(min, max, labelfracs[self.extendtolabellevel])

        ticks = []
        for i in range(len(tickfracs)):
            ticks = self.mergeticklists(ticks, self.getticklist(min, max, tickfracs[i], ticklevel = i))
        for i in range(len(labelfracs)):
            ticks = self.mergeticklists(ticks, self.getticklist(min, max, labelfracs[i], labellevel = i))

        return ticks

    def getparts(self):
        return [getticks(self), ]


class autolinpart(linpart):
    defaulttickfracslist = ((frac(1, 1), frac(1, 2), ),
                            (frac(2, 1), frac(1, 1), ),
                            (frac(5, 2), frac(5, 4), ),
                            (frac(5, 1), frac(5, 2), ), )

    def __init__(self, min, max, minticks = 0.5, maxticks = 25, tickfracslist = defaulttickfracslist, **args):
        linpart.__init__(self, min, max, **args)
        self.minticks = minticks
        self.maxticks = maxticks
        self.tickfracslist = tickfracslist

    def getparts(self):
        parts = []
        e = int(log(self.max - self.min) / log(10))
        for shift in range(e - 5, e + 5): # TODO: what about that 5???
            if shift > 0:
                bf = frac(_powi(10L, shift), 1)
            elif shift < 0:
                bf = frac(1, _powi(10L, -shift))
            else:
                bf = frac(1, 1)

            for tickfracs in self.tickfracslist:
                tickcount = (self.max - self.min) / float(tickfracs[0] * bf)
                if (tickcount > self.minticks) and (tickcount < self.maxticks):
                    parts.append(self.getticks(map(lambda f, bf = bf: f * bf, tickfracs)))
        return parts


class multifracs:
    pass

class logpart(anypart):

    """
    This very much looks like some code duplication of linpart. However, it is
    not, because logaxis use multifracs instead of fracs all the time.
    """

    def __init__(self, min, max, tickmultifracs = None, labelmultifracs = None, extendtoticklevel = 0, extendtolabellevel = None):
        """
        zero-level labelmultifracs are created out of the zero-level tickmultifracs when labelmultifracs are None
        all-level tickmultifracs are created out of the all-level labelmultifracs when tickmultifracs are None
        get ticks but avoid labels by labelfracs = ()
        get labels but avoid ticks by tickfracs = ()

        We do not perform the adjustment of tickfracs or labelfracs within this
        constructor, but later in getticks in order to allow for a change by
        parameters of getticks. That can be used to create other partition schemes
        (which create several posibilities) by derivating this class.
        """
        self.min = min
        self.max = max
        self.tickmultifracs = tickmultifracs
        self.labelmultifracs = labelmultifracs
        self.extendtoticklevel = extendtoticklevel
        self.extendtolabellevel = extendtolabellevel

    def getticklist(self, fracs, ticklevel = None, labellevel = None):
        ticks = []
        print fracs, ticklevel, labellevel
        bf = frac(_powi(10L, 5), 1)
        print bf

#        ticks = self.mergeticklists(ticks, self.getticklist(tickmultifracs[i], ticklevel = i))
#        e = int(math.ceil(log((self.max - self.min) / self.factor) / log(self.shift)))
#        imin = int(math.ceil(self.min / float(frac) - 0.5 * epsilon))
#        imax = int(math.floor(self.max / float(frac) + 0.5 * epsilon))
#        for i in range(imin, imax + 1):
#            ticks.append(tick(long(i) * frac.enum, frac.denom, ticklevel = ticklevel, labellevel = labellevel))
        return ticks

    def getticks(self, tickmultifracs = None, labelmultifracs = None):
        """
        When tickfracs or labelfracs are set, they will be taken instead of the
        values provided to the constructor. It is not allowed to provide something
        to tickfracs and labelfracs here and at the constructor at the same time.
        """
        if (tickmultifracs == None) and (labelmultifracs == None):
            tickmultifracs = self.tickmultifracs
            labelmultifracs = self.labelmultifracs
        else:
            assert self.tickmultifracs == None
            assert self.labelmultifracs == None
        if tickmultifracs == None:
            if labelmultifracs == None:
                tickmultifracs = (())
            else:
                tickmultifracs = labelmultifracs
        if labelmultifracs == None:
            if len(tickmultifracs):
                labelmultifracs = (tickmultifracs[0], )
            else:
                labelmultifracs = ()

#       take care on self.extendtoticklevel and self.extendtolabellevel ...
        #min = min.self
        #max = max.self

        ticks = []
        #for i in range(len(tickmultifracs)):
        #    ticks = self.mergeticklists(ticks, self.getticklist(min, max, tickmultifracs[i], ticklevel = i))
        #for i in range(len(labelmultifracs)):
        #    ticks = self.mergeticklists(ticks, self.getticklist(min, max, labelmultifracs[i], labellevel = i))

        return ticks

    def getparts(self):
        return [getticks(self), ]

#print linpart(0, 1.9, (frac(1, 3), frac(1, 4), ), extendtoticklevel = None, extendtolabellevel = 0).getticks()
#print autolinpart(0, 1.9).getparts()
#print logpart(0.0232, 1.4623, ((frac(1, 10), ), (frac(2, 10), frac(3, 10), frac(4, 10), frac(5, 10), frac(6, 10), frac(7, 10), frac(8, 10), frac(9, 10), ), ), extendtoticklevel = None, extendtolabellevel = 0).getticks()

class favorautolinpart(autolinpart):
    """favorfixfrac - shift - frac - partitioning"""
    # TODO: just to be done ... throw out parts within the favor region -- or what else to do?
    degreefracs = ((frac( 15, 1), frac(  5, 1), ),
                   (frac( 30, 1), frac( 15, 1), ),
                   (frac( 45, 1), frac( 15, 1), ),
                   (frac( 60, 1), frac( 30, 1), ),
                   (frac( 90, 1), frac( 30, 1), ),
                   (frac( 90, 1), frac( 45, 1), ),
                   (frac(180, 1), frac( 45, 1), ),
                   (frac(180, 1), frac( 90, 1), ),
                   (frac(360, 1), frac( 90, 1), ),
                   (frac(360, 1), frac(180, 1), ), )
    # favouring some fixed fracs, e.g. partitioning of axis in degree
    def __init__(self, fixfracs, fixfavor = 2, **args):
        sfpart.__init__(self, **args)
        self.fixfracs = fixfracs
        self.fixfavor = fixfavor


class timepart:
    """partitioning of times and dates"""
    # TODO: this will be a difficult subject ...
    pass


class momrate:
    """min - opt - max - rating of axes partitioning"""
    defaultrates = ((1, 25, 4, 1, ), (1, 100, 8, 0.5, ), ) # min, opt, max, ratefactor
    def __init__(self, rates = defaultrates):
        self.rates = rates

    def getrates(self, parts):
        pass

class LinAxis(_Axis, _LinMap):

    def __init__(self):#, part = sfpart(), rate = momrate(), **args):
        _Axis.__init__(self, **args)
        #self.part = part
        #self.rate = rate

        self.enclosezero = 0.25 # maximal factor allowed to extend axis to enclose zero
        self.enlargerange = 1 # should we enlarge ranges?
        self.fracfixed = ( )
        self.favorfixed = 2 # factor to favor fixed fractions
        self.fracsshift = ((frac(1, 1), frac(1, 2), ),
                           (frac(2, 1), frac(1, 1), ),
                           (frac(5, 2), frac(5, 4), ),
                           (frac(5, 1), frac(5, 2), ), )
        self.shift = 10L # need to be long !!!
        self.factor = 1 # e.g. pi
        self.tickopt = ((1, 25, 4, 1, ), (1, 100, 8, 0.5, ), ) # min, max, opt, ratefactor
        # self.getpart = getpart # make this modular
        # self.ratepart = ratepart # make this modular

    def getparts(self):

        if self.min * self.max > 0:
            if (self.min > 0) and (self.max * self.enclosezero > self.min):
                self.setrange(min = 0)
            elif (self.max < 0) and (self.min * self.enclosezero < self.max):
                self.setrange(max = 0)

        e = int(math.ceil(log((self.max - self.min) / self.factor) / log(self.shift)))

        res = [ ]

        for shift in range(e - 4, e + 1): # TODO: automatically (???) estimate this range
                                          #       lower bound is related to the maxticks
                                          #       upper bound is related to the minticks

            # bf = basefrac
            if shift > 0:
                bf = frac(_powi(self.shift, shift), 1)
            elif shift < 0:
                bf = frac(1, _powi(self.shift, -shift))
            else:
                bf = frac(1, 1)

            for fracs in self.fracsshift:
                resfrac = [ ]
                min = self.min
                max = self.max
                l = (max - min) / float(self.factor)
                first = 1
                for (_f, (minticks, maxticks, opt, ratefactor, ), ) in zip(fracs, self.tickopt):
                    f = frac(bf.enum * _f.enum, bf.denom * _f.denom)
                    scale = f.enum * float(self.factor) / f.denom
                    imin = int(math.floor(min / scale + epsilon)) # TODO: long here, epsilon?
                    imax = int(math.ceil(max / scale - epsilon))
                    if first and self.enlargerange:
                        if not self.fixmin:
                            min = imin * scale
                        if not self.fixmax:
                            max = imax * scale
                    first = 0
                    resfrac.append( (f, imin, imax, ), )
                res.append((min, max, resfrac, ))
        return res

    def rateparts(self, parts):
        rparts = [ ]
        for part in parts:
            rate = 0
            min = part[0]
            max = part[1]
            for ((f, imin, imax, ), (minticks, maxticks, opt, ratefactor, ), ) in zip(part[2], self.tickopt):
                ticks = (max - min) * f.denom / float(self.factor) / f.enum
                if (ticks < minticks + epsilon) or (ticks > maxticks - epsilon):
                    break
                else:
                    rate += ratefactor * ((opt - minticks) * log((opt - minticks) / (ticks - minticks)) +
                                          (maxticks - opt) * log((maxticks - opt) / (maxticks - ticks))) / (maxticks - minticks)
            else:
                rparts.append((rate, part, ))
        return rparts

    def getticklists(self, parts):
        ticklists = []
        for (rate, (min, max, fracs, )) in parts:
            self.setrange(min, max, )
            ticklist = [min, max, ]
            level = 0
            for (f, imin, imax, ) in fracs:
                for i in range(imin, imax + 1):
                    x = f.enum * i / float(f.denom)
                    if level == 0:
                        ticklist.append(Tick(x, self.convert(x), self.ValToLab(x)))
                    else:
                        ticklist.append(Tick(x, self.convert(x), TickLevel = level))
                level = level + 1
            ticklists.append((rate, ticklist, ))
        return ticklists

    def partitioning(self): #, rateticklists):
        parts = self.getparts()
        parts = self.rateparts(parts)
        ticklists = self.getticklists(parts)
        # ticklists = self.rateticklists(ticklists)
        (bestrate, bestticklist, ) = ticklists[0]
        for (rate, ticklist, ) in ticklists[1:]:
            if rate < bestrate:
                (bestrate, bestticklist, ) = (rate, ticklist, )
        self.setrange(bestticklist[0], bestticklist[1])
        self.ticklist = bestticklist[2:]

    def TickList(self):
        return self.ticklist

class LogAxis(_Axis, _LogMap):

    def partitioning(self):
        pass
    

###############################################################################
# graph part

class Graph:

    def __init__(self, canvas, tex, xpos, ypos):
        self.canvas = canvas
        self.tex = tex
        self.xpos = xpos
        self.ypos = ypos

class _PlotData:
    def __init__(self, Data, PlotStyle):
        self.Data = Data
        self.PlotStyle = PlotStyle

_XPattern = re.compile(r"x([2-9]|[1-9][0-9]+)?$")
_YPattern = re.compile(r"y([2-9]|[1-9][0-9]+)?$")
_DXPattern = re.compile(r"dx([2-9]|[1-9][0-9]+)?$")
_DYPattern = re.compile(r"dy([2-9]|[1-9][0-9]+)?$")

class GraphXY(Graph):

    plotdata = [ ]

    def __init__(self, canvas, tex, xpos, ypos, width, height, **Axis):
        Graph.__init__(self, canvas, tex, xpos, ypos)
        self.width = width
        self.height = height
        if "x" not in Axis.keys():
            Axis["x"] = LinAxis()
        if "y" not in Axis.keys():
            Axis["y"] = LinAxis()
        self.Axis = Axis

    def plot(self, Data, PlotStyle = None):
        if not PlotStyle:
            PlotStyle = Data.DefaultPlotStyle
        self.plotdata.append(_PlotData(Data, PlotStyle))
    
    def run(self):

        for key in self.Axis.keys():
            ranges = []
            for pd in self.plotdata:
                try:
                    ranges.append(pd.Data.GetRange(key))
                except DataRangeUndefinedException:
                    pass
            if len(ranges) == 0:
                assert 0, "range for %s-axis unknown" % key
            self.Axis[key].setrange(min( map (lambda x: x[0], ranges)),
                                    max( map (lambda x: x[1], ranges)))

        for pd in self.plotdata:
            pd.Data.SetAxis(self.Axis)

        # this should be done after axis-size calculation
        self.left = 1   # convert everything to plain numbers here already, no length !!!
        self.buttom = 1 # should we use the final postscript points already ???
        self.top = 0
        self.right = 0
        self.VirMap = (_LinMap().setbasepts(((0, self.xpos + self.left, ), (1, self.xpos + self.width - self.right, ))),
                       _LinMap().setbasepts(((0, self.ypos + self.buttom, ), (1, self.ypos + self.height - self.top, ))), )

        self.canvas.draw(rect(self.VirMap[0].convert(0),
                              self.VirMap[1].convert(0),
                              self.VirMap[0].convert(1) - self.VirMap[0].convert(0),
                              self.VirMap[1].convert(1) - self.VirMap[1].convert(0)))

        for key in self.Axis.keys():
            self.Axis[key].partitioning()

        for key in self.Axis.keys():
            if _XPattern.match(key):
                Type = 0
            elif _YPattern.match(key):
                Type = 1
            else:
                assert 0, "Axis key %s not allowed" % key
            for tick in self.Axis[key].TickList():
                xv = tick.VirtualPos
                l = tick.Label
                x = self.VirMap[Type].convert(xv)
                if Type == 0:
                    self.canvas.draw(line(x, self.VirMap[1].convert(0), x, self.VirMap[1].convert(0) + ticklength.normal))
                    #self.canvas.draw(line(x+0.1, self.VirMap[1].convert(0), x+0.1, self.VirMap[1].convert(0) + ticklength.short))
                    #self.canvas.draw(line(x+0.2, self.VirMap[1].convert(0), x+0.2, self.VirMap[1].convert(0) + ticklength.normal.increment(-2)))
                    self.tex.text(x, self.VirMap[1].convert(0)-0.5, l, tex.halign.center)
                if Type == 1:
                    self.canvas.draw(line(self.VirMap[0].convert(0), x, self.VirMap[0].convert(0) + ticklength.normal.increment(-tick.TickLevel), x))
                    if l:
                        self.tex.text(self.VirMap[0].convert(0)-0.5, x, l, tex.halign.right)

        for pd in self.plotdata:
            pd.PlotStyle.LoopOverPoints(self, pd.Data)

    def VirToPos(self, Type, List):
        return self.VirMap[Type].convert(List)

    def ValueList(self, Pattern, Type, Data):
        (key, ) = filter(lambda x, Pattern = Pattern: Pattern.match(x), Data.GetKindList())
        return self.VirToPos(Type, self.Axis[key].convert(Data.GetValues(key)))



###############################################################################
# draw styles -- planed are things like:
#     * chain
#         just connect points by lines
#     * mark
#         place markers at the points
#         there is a hole lot of specialized markers (derived from mark):
#             * text-mark (put a text (additional column!) there)
#             * fill/size-mark (changes filling or size of the marker by an additional column)
#             * vector-mark (puts a small vector with direction given by an additional column)
#     * bar

class _PlotStyle:

    pass

class chain(_PlotStyle):

    def LoopOverPoints(self, Graph, Data):
        p = [ ]
        for pt in zip(Graph.ValueList(_XPattern, 0, Data),
                      Graph.ValueList(_YPattern, 1, Data)):
            if p:
                p.append(lineto(pt[0],pt[1]))
            else:
                p = [moveto(pt[0],pt[1]), ]
        Graph.canvas.draw(path(p))

class mark(_PlotStyle):

    def __init__(self, size = 0.05):
        self.size = size

    def LoopOverPoints(self, Graph, Data):
        for pt in zip(Graph.ValueList(_XPattern, 0, Data),
                      Graph.ValueList(_YPattern, 1, Data)):
            Graph.canvas.draw(path([moveto(pt[0] - self.size, pt[1] - self.size),
                                    lineto(pt[0] + self.size, pt[1] + self.size),
                                    moveto(pt[0] - self.size, pt[1] + self.size),
                                    lineto(pt[0] + self.size, pt[1] - self.size), ]))

###############################################################################
# data part

from mathtree import *
import re

CommentPattern = re.compile(r"\s*(#|!)+\s*")

class DataFile:

    def __init__(self, FileName, sep = None, titlesep = None):
        self.name = FileName
        File = open(FileName, "r")
        Lines = File.readlines()
        self.Columns = 0
        self.Rows = 0
        self.data = []
        for Line in Lines:
            Match = CommentPattern.match(Line)
            if not Match:
                if sep:
                    Row = Line.split(sep)
                else:
                    Row = Line.split()
                if self.Columns < len(Row):
                    for i in range(self.Columns, len(Row)):
                        # create new lists for each column in order to avoid side effects in append
                        self.data.append(reduce(lambda x,y: x + [None, ], range(self.Rows), []))
                    self.Columns = len(Row)
                for i in range(len(Row)):
                    try:
                        self.data[i].append(float(Row[i]))
                    except ValueError:
                        self.data[i].append(Row[i])
                for i in range(len(Row), self.Columns):
                    self.data[i].append(None)
                self.Rows = self.Rows + 1
            else:
                if self.Rows == 0:
                    self.titleline = Line[Match.end(): ]
                    if sep:
                        self.titles = self.titleline.split(sep)
                    else:
                        self.titles = self.titleline.split()

    def GetTitle(self, Number):
        if (Number < len(self.titles)):
            return self.titles[Number]
        else:
            return None

    def GetColumn(self, Number):
        return self.data[Number]


class DataException(Exception):
    pass

class DataKindMissingException(DataException):
    pass

class DataRangeUndefinedException(DataException):
    pass

class DataRangeAlreadySetException(DataException):
    pass

class Data:

    DefaultPlotStyle = mark()

    def __init__(self, datafile, **columns):
        self.datafile = datafile
        self.columns = columns

    def GetName(self):
        return self.datafile.name

    def GetKindList(self):
        return self.columns.keys()

    def GetTitle(self, Kind):
        return self.datafile.GetTitle(self.columns[Kind] - 1)

    def GetValues(self, Kind):
        return self.datafile.GetColumn(self.columns[Kind] - 1)
    
    def GetRange(self, Kind):
        # handle non-numeric things properly
        if Kind not in self.columns.keys():
            raise DataRangeUndefinedException
        return (min(self.GetValues(Kind)), max(self.GetValues(Kind)), )

    def SetAxis(self, Axis):
        pass


AssignPattern = re.compile(r"\s*([a-z][a-z0-9_]*)\s*=", re.IGNORECASE)

class Function:

    DefaultPlotStyle = chain()
    
    def __init__(self, Expression, Points = 100):
        self.name = Expression
        self.Points = Points
        Match = AssignPattern.match(Expression)
        if Match:
            self.ResKind = Match.group(1)
            Expression = Expression[Match.end(): ]
        else:
            self.ResKind = None
        self.MT = ParseMathTree(ParseStr(Expression))
        self.VarList = self.MT.VarList()
    

    def GetName(self):
        return self.name
    
    def GetKindList(self, DefaultResult = "y"):
        if self.ResKind:
            return self.MT.VarList() + [self.ResKind, ]
        else:
            return self.MT.VarList() + [DefaultResult, ]
    
    def GetRange(self, Kind):
        raise DataRangeUndefinedException

    def SetAxis(self, Axis, DefaultResult = "y"):
        if self.ResKind:
            self.YAxis = Axis[self.ResKind]
        else:
            self.YAxis = Axis[DefaultResult]
        self.XAxis = { }
        self.XValues = { }
        for key in self.MT.VarList():
            self.XAxis[key] = Axis[key]
            values = []
            for x in range(self.Points + 1):
                values.append(self.XAxis[key].invert(x * 1.0 / self.Points))
            self.XValues[key] = values
        # this isn't smart ... we should walk only once throu the mathtree
        self.YValues = map(lambda i, self = self: self.MT.Calc(self.XValues, i), range(self.Points + 1))

    def GetValues(self, Kind, DefaultResult = "y"):
        if (self.ResKind and (Kind == self.ResKind)) or ((not self.ResKind) and (Kind == DefaultResult)):
            return self.YValues
        return self.XValues[Kind]


class ParamFunction(Function):
    pass


###############################################################################
# key part


