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
from core.boundingbox import BoundingBox
from core.stmove import StMove
from gui.wpzero import WpZero
from gui.arrow import Arrow
from gui.routetext import RouteText
from gui.canvas import CanvasBase, MyDropDownMenu

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

        self.BB = BoundingBox()

    def setScene(self, instance):

        return
    def update(self):

        return
    def tr(self, string_to_translate):
        """
        Translate a string using the QCoreApplication translation framework
        @param string_to_translate: a unicode string
        @return: the translated unicode string if it was possible to translate
        """
        return text_type(string_to_translate)

    def plotAll(self, shapes):
        """
        Instance is called by the Main Window after the defined file is loaded.
        It generates all ploting functionality. The parameters are generally
        used to scale or offset the base geometry (by Menu in GUI).
        """
        for shape in shapes:
            self.paint_shape(shape)
            # self.addItem(shape)
            self.shapes.append(shape)
        self.draw_wp_zero()
        self.update()

    def repaint_shape(self, shape):
        # setParentItem(None) might let it crash, hence we rely on the garbage collector
        shape.stmove.hide()
        shape.starrow.hide()
        shape.enarrow.hide()
        del shape.stmove
        del shape.starrow
        del shape.enarrow
        self.paint_shape(shape)
        if not shape.isSelected():
            shape.stmove.hide()
            shape.starrow.hide()
            shape.enarrow.hide()

    def paint_shape(self, shape):
        """
        Create all plotting related parts of one shape.
        @param shape: The shape to be plotted.
        """
        start, start_ang = shape.get_start_end_points(True, True)
        # drawHorLine = lambda caller, start, end: shape.path.lineTo(end.x, -end.y)
        # drawVerLine = lambda caller, start: None  # Not used in 2D mode
        # shape.make_path(drawHorLine, drawVerLine)

        # self.BB = self.BB.joinBB(shape.BB)

        shape.stmove = self.createstmove(shape)
        # shape.starrow = self.createstarrow(shape)
        # shape.enarrow = self.createenarrow(shape)
        # shape.stmove.setParentItem(shape)
        # shape.starrow.setParentItem(shape)
        # shape.enarrow.setParentItem(shape)

    def draw_wp_zero(self):
        """
        This function is called while the drawing of all items is done. It plots
        the WPZero to the Point x=0 and y=0. This item will be enabled or
        disabled to be shown or not.
        """

    def createstmove(self, shape):
        """
        This function creates the Additional Start and End Moves in the plot
        window when the shape is selected
        @param shape: The shape for which the Move shall be created.
        """
        stmove = StMoveNoGUI(shape)
        return stmove

    def delete_opt_paths(self):
        """
        This function deletes all the plotted export routes.
        """
        # removeItem might let it crash, hence we rely on the garbage collector
        while self.routearrows:
            item = self.routearrows.pop()
            item.hide()
            del item

        while self.routetext:
            item = self.routetext.pop()
            item.hide()
            del item

    def addexproutest(self):
        self.expprv = Point(g.config.vars.Plane_Coordinates['axis1_start_end'],
                            g.config.vars.Plane_Coordinates['axis2_start_end'])
        # self.expcol = QtCore.Qt.darkRed

    def addexproute(self, exp_order, layer_nr):
        """
        This function initialises the Arrows of the export route order and its numbers.
        """
        for shape_nr in range(len(exp_order)):
            shape = self.shapes[exp_order[shape_nr]]
            st = self.expprv
            en, self.expprv = shape.get_start_end_points_physical()
            # self.routearrows.append(Arrow(startp=en,
            #                               endp=st,
            #                               color=self.expcol,
            #                               pencolor=self.expcol))


            self.routetext.append(RouteText(text=("%s,%s" % (layer_nr, shape_nr+1)),
                                            startp=en))


    def setShowDisabledPaths(self, flag):
        """
        This function is called by the Main Menu and is passed from Main to
        MyGraphicsView to the Scene. It performs the showing or hiding
        of enabled/disabled shapes.

        @param flag: This flag is true if hidden paths shall be shown
        """
        self.showDisabledPaths = flag

        for shape in self.shapes:
            if flag and shape.isDisabled():
                shape.show()
            elif not flag and shape.isDisabled():
                shape.hide()


class ShapeNoGUI(Shape):
    def __init__(self, nr, closed, parentEntity):

        Shape.__init__(self, nr, closed, parentEntity)
        self.starrow = None
        self.enarrow = None

    def __str__(self):
        return super(ShapeNoGUI, self).__str__()

    def tr(self, string_to_translate):
        return text_type(string_to_translate)

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

    def boundingRect(self):
        """
        Required method for painting. Inherited by Painterpath
        @return: Gives the Bounding Box
        """
        return self.path.boundingRect()

    # def shape(self):
    #     """
    #     Reimplemented function to select outline only.
    #     @return: Returns the Outline only
    #     """
    #     return stroke


class StMoveNoGUI(StMove):

    def __init__(self, shape):
        # QGraphicsLineItem.__init__(self)
        StMove.__init__(self, shape)

        self.allwaysshow = False

    def contains_point(self, point):
        """
        StMove cannot be selected. Return maximal distance
        """
        return float(0x7fffffff)

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

    def setSelected(self, flag=True):
        """
        Override inherited function to turn off selection of Arrows.
        @param flag: The flag to enable or disable Selection
        """
        if self.allwaysshow:
            pass
        elif flag is True:
            self.show()
        else:
            self.hide()

    def setallwaysshow(self, flag=False):
        """
        If the directions shall be allwaysshown the parameter will be set and
        all paths will be shown.
        @param flag: The flag to enable or disable Selection
        """
        self.allwaysshow = flag
        if flag is True:
            self.show()
        elif flag is True and self.isSelected():
            self.show()
        else:
            self.hide()

    def paint(self, painter, option, widget=None):
        """
        Method will be triggered with each paint event. Possible to give options
        @param painter: Reference to std. painter
        @param option: Possible options here
        @param widget: The widget which is painted on.
        """
        painter.setPen(self.pen)
        painter.drawPath(self.path)

    def boundingRect(self):
        """
        Required method for painting. Inherited by Painterpath
        @return: Gives the Bounding Box
        """
        return self.path.boundingRect()
