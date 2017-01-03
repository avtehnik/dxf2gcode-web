# -*- coding: utf-8 -*-

############################################################################
#
#   Copyright (C) 2011-2015
#    Christian Kohlöffel
#    Jean-Paul Schouwstra
#
#   This file is part of DXF2GCODE.
#
#   DXF2GCODE is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   DXF2GCODE is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with DXF2GCODE.  If not, see <http://www.gnu.org/licenses/>.
#
############################################################################

"""
Special purpose canvas including all required plotting function etc.

@purpose:  Plotting all
"""

from __future__ import absolute_import
from __future__ import division

import logging

from core.point import Point
from core.shape import Shape
from core.stmove import StMove

import globals.globals as g

from globals.six import text_type
import globals.constants as c

logger = logging.getLogger("DxfImport.myCanvasClass")


class MyNoGraphicsScene():
    """
    This is the Canvas used to print the graphical interface of dxf2gcode.
    The Scene is rendered into the previously defined mygraphicsView class.
    All performed plotting functions should be defined here.
    @sideeffect: None
    """
    def __init__(self):

        self.shapes = []
        self.wpzero = None
        self.routearrows = []
        self.routetext = []
        self.expprv = None
        self.expcol = None
        self.expnr = 0

        self.showDisabledPaths = False

    def plotAll(self, shapes):
        """
        Instance is called by the Main Window after the defined file is loaded.
        It generates all ploting functionality. The parameters are generally
        used to scale or offset the base geometry (by Menu in GUI).
        """
        for shape in shapes:
            shape.stmove = StMoveNoGUI(shape)
            self.shapes.append(shape)

    def addexproutest(self):
        self.expprv = Point(g.config.vars.Plane_Coordinates['axis1_start_end'],
                            g.config.vars.Plane_Coordinates['axis2_start_end'])

    def addexproute(self, exp_order, layer_nr):
        """
        This function initialises the Arrows of the export route order and its numbers.
        """
        for shape_nr in range(len(exp_order)):
            shape = self.shapes[exp_order[shape_nr]]
            en, self.expprv = shape.get_start_end_points_physical()


class ShapeNoGUI(Shape):
    def __init__(self, nr, closed, parentEntity):

        Shape.__init__(self, nr, closed, parentEntity)
        self.starrow = None
        self.enarrow = None

    def __str__(self):
        return super(ShapeNoGUI, self).__str__()

    def contains_point(self, point):

        min_distance = float(0x7fffffff)
        ref_point = Point(point.x(), point.y())
        t = 0.0
        while t < 1.0:
            per_point = self.path.pointAtPercent(t)
            spline_point = Point(per_point.x(), per_point.y())
            distance = ref_point.distance(spline_point)
            if distance < min_distance:
                min_distance = distance
            t += 0.01
        return min_distance

class StMoveNoGUI(StMove):

    def __init__(self, shape):
        # QGraphicsLineItem.__init__(self)
        StMove.__init__(self, shape)
        self.allwaysshow = False

    def make_papath(self):
        """
        To be called if a Shape shall be printed to the canvas
        @param canvas: The canvas to be printed in
        @param pospro: The color of the shape
        """
        # if len(self.geos):
        #     start = self.geos.abs_el(0).get_start_end_points(True)
        #     self.path.moveTo(start.x, -start.y)
        # drawHorLine = lambda caller, start, end: self.path.lineTo(end.x, -end.y)
        # drawVerLine = lambda caller, start: None  # Not used in 2D mode
        # self.make_path(drawHorLine, drawVerLine)

