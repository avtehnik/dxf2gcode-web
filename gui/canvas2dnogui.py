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
from core.stmove import StMove

import globals.globals as g

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
            shape.stmove = StMove(shape)
            # StMove.__init__(self, shape)
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
