#!/usr/bin/python
# -*- coding: utf-8 -*-

############################################################################
#
#   Copyright (C) 2010-2016
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

from __future__ import absolute_import
from __future__ import division

import os
import sys

from math import degrees, radians
from copy import copy, deepcopy
import logging
import argparse
import subprocess
import tempfile

from core.point import Point
from core.layercontent import LayerContent, Layers, Shapes
from core.entitycontent import EntityContent
from core.customgcode import CustomGCode
from core.linegeo import LineGeo
from core.holegeo import HoleGeo
from core.project import Project
from globals.config import MyConfig
import globals.globals as g
from globals.logger import LoggerClass

from gui.configwindow import ConfigWindow

from dxfimport.importer import ReadDXF

from postpro.postprocessor import MyPostProcessor
from postpro.tspoptimisation import TspOptimization

from globals.helperfunctions import str_encode, str_decode, qstr_encode

from globals.six import text_type

logger = logging.getLogger()

ch = logging.StreamHandler(sys.stdout)
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
# logger.addHandler(ch)

# Get folder of the main instance and write into globals
g.folder = os.path.dirname(os.path.abspath(sys.argv[0])).replace("\\", "/")
if os.path.islink(sys.argv[0]):
    g.folder = os.path.dirname(os.readlink(sys.argv[0]))


class MainWindow():

    """
    Main Class
    """

    # Define a QT signal that is emitted when the configuration changes.
    # Connect to this signal if you need to know when the configuration has
    # changed.
    # configuration_changed = QtCore.pyqtSignal()

    def __init__(self):
        """
        Initialization of the Main window. This is directly called after the
        Logger has been initialized. The Function loads the GUI, creates the
        used Classes and connects the actions to the GUI.
        """

        self.config_window = ConfigWindow(g.config.makeConfigWidgets(),
                                          g.config.var_dict,
                                          g.config.var_dict.configspec,
                                          self)

        self.canvas_scene = None
        #Load the post-processor configuration and build the post-processor configuration window
        self.MyPostProcessor = MyPostProcessor()
        # If string version_mismatch isn't empty, we popup an error and exit

        self.d2g = Project(self)


        self.filename = ""

        self.valuesDXF = None
        self.shapes = Shapes([])
        self.entityRoot = None
        self.layerContents = Layers([])
        self.newNumber = 1

        self.cont_dx = 0.0
        self.cont_dy = 0.0
        self.cont_rotate = 0.0
        self.cont_scale = 1.0

        # self.readSettings()

    def tr(self, string_to_translate):
        """
        Translate a string using the QCoreApplication translation framework
        @param: string_to_translate: a unicode string
        @return: the translated unicode string if it was possible to translate
        """
        return text_type(string_to_translate)

    def deleteG0Paths(self):
        """
        Deletes the optimisation paths from the scene.
        """
        self.canvas_scene.delete_opt_paths()
        self.canvas_scene.update()

    def exportShapes(self, status=False, save_filename=None):
        """
        This function is called by the menu "Export/Export Shapes". It may open
        a Save Dialog if used without LinuxCNC integration. Otherwise it's
        possible to select multiple postprocessor files, which are located
        in the folder.
        """

        self.MyPostProcessor.exportShapes(self.filename,save_filename,self.layerContents)
        # self.close()

    def open(self):
        """
        This function is called by the menu "File/Load File" of the main toolbar.
        It creates the file selection dialog and calls the load function to
        load the selected file.
        """

        # If there is something to load then call the load function callback
        if self.filename:
            self.cont_dx = 0.0
            self.cont_dy = 0.0
            self.cont_rotate = 0.0
            self.cont_scale = 1.0

            self.load()

    def load(self, plot=True):
        """
        Loads the file given by self.filename.  Also calls the command to
        make the plot.
        @param plot: if it should plot
        """

        (name, ext) = os.path.splitext(self.filename)

        logger.info(self.tr('Loading file: %s') % self.filename)

        self.valuesDXF = ReadDXF(self.filename)

        # Output the information in the text window
        logger.info(self.tr('Loaded layers: %s') % len(self.valuesDXF.layers))
        logger.info(self.tr('Loaded blocks: %s') % len(self.valuesDXF.blocks.Entities))
        for i in range(len(self.valuesDXF.blocks.Entities)):
            layers = self.valuesDXF.blocks.Entities[i].get_used_layers()
            logger.info(self.tr('Block %i includes %i Geometries, reduced to %i Contours, used layers: %s')
                        % (i, len(self.valuesDXF.blocks.Entities[i].geo), len(self.valuesDXF.blocks.Entities[i].cont), layers))
        layers = self.valuesDXF.entities.get_used_layers()
        insert_nr = self.valuesDXF.entities.get_insert_nr()

        logger.info(self.tr('Loaded %i entity geometries; reduced to %i contours; used layers: %s; number of inserts %i')
                    % (len(self.valuesDXF.entities.geo), len(self.valuesDXF.entities.cont), layers, insert_nr))


        self.makeShapes()
        if plot:
            self.plot()
        return True

    def plot(self):

        # Paint the canvas
        self.canvas_scene = MyNoGraphicsScene()
        self.canvas_scene.plotAll(self.shapes)

    def makeShapes(self):
        self.entityRoot = EntityContent(nr=0, name='Entities', parent=None,
                                        p0=Point(self.cont_dx, self.cont_dy), pb=Point(),
                                        sca=[self.cont_scale, self.cont_scale, self.cont_scale], rot=self.cont_rotate)
        self.layerContents = Layers([])
        self.shapes = Shapes([])

        self.makeEntityShapes(self.entityRoot)

        for layerContent in self.layerContents:
            layerContent.overrideDefaults()
        self.layerContents.sort(key=lambda x: x.nr)
        self.newNumber = len(self.shapes)

    def makeEntityShapes(self, parent, layerNr=-1):
        """
        Instance is called prior to plotting the shapes. It creates
        all shape classes which are plotted into the canvas.

        @param parent: The parent of a shape is always an Entity. It may be the root
        or, if it is a Block, this is the Block.
        """
        if parent.name == "Entities":
            entities = self.valuesDXF.entities
        else:
            ent_nr = self.valuesDXF.Get_Block_Nr(parent.name)
            entities = self.valuesDXF.blocks.Entities[ent_nr]

        # Assigning the geometries in the variables geos & contours in cont
        ent_geos = entities.geo

        # Loop for the number of contours
        for cont in entities.cont:
            # Query if it is in the contour of an insert or of a block
            if ent_geos[cont.order[0][0]].Typ == "Insert":
                ent_geo = ent_geos[cont.order[0][0]]

                # Assign the base point for the block
                new_ent_nr = self.valuesDXF.Get_Block_Nr(ent_geo.BlockName)
                new_entities = self.valuesDXF.blocks.Entities[new_ent_nr]
                pb = new_entities.basep

                # Scaling, etc. assign the block
                p0 = ent_geos[cont.order[0][0]].Point
                sca = ent_geos[cont.order[0][0]].Scale
                rot = ent_geos[cont.order[0][0]].rot

                # Creating the new Entitie Contents for the insert
                newEntityContent = EntityContent(nr=0,
                                                 name=ent_geo.BlockName,
                                                 parent=parent,
                                                 p0=p0,
                                                 pb=pb,
                                                 sca=sca,
                                                 rot=rot)

                parent.append(newEntityContent)
                self.makeEntityShapes(newEntityContent, ent_geo.Layer_Nr)

            else:
                # Loop for the number of geometries
                tmp_shape = Shape(len(self.shapes),(True if cont.closed else False), parent)

                for ent_geo_nr in range(len(cont.order)):
                    ent_geo = ent_geos[cont.order[ent_geo_nr][0]]
                    if cont.order[ent_geo_nr][1]:
                        ent_geo.geo.reverse()
                        for geo in ent_geo.geo:
                            geo = copy(geo)
                            geo.reverse()
                            self.append_geo_to_shape(tmp_shape, geo)
                        ent_geo.geo.reverse()
                    else:
                        for geo in ent_geo.geo:
                            self.append_geo_to_shape(tmp_shape, copy(geo))

                if len(tmp_shape.geos) > 0:
                    # All shapes have to be CW direction.
                    tmp_shape.AnalyseAndOptimize()

                    self.shapes.append(tmp_shape)
                    if g.config.vars.Import_Parameters['insert_at_block_layer'] and layerNr != -1:
                        self.addtoLayerContents(tmp_shape, layerNr)
                    else:
                        self.addtoLayerContents(tmp_shape, ent_geo.Layer_Nr)
                    parent.append(tmp_shape)

    def append_geo_to_shape(self, shape, geo):
        if -1e-5 <= geo.length < 1e-5:  # TODO adjust import for this
            return
        shape.append(geo)
        if isinstance(geo, HoleGeo):
            shape.type = 'Hole'
            shape.closed = True  # TODO adjust import for holes?

    def addtoLayerContents(self, shape, lay_nr):
        # Check if the layer already exists and add shape if it is.
        for LayCon in self.layerContents:
            if LayCon.nr == lay_nr:
                LayCon.shapes.append(shape)
                shape.parentLayer = LayCon
                return

        # If the Layer does not exist create a new one.
        LayerName = self.valuesDXF.layers[lay_nr].name
        self.layerContents.append(LayerContent(lay_nr, LayerName, [shape]))
        shape.parentLayer = self.layerContents[-1]


if __name__ == "__main__":
    """
    The main function which is executed after program start.
    """
    Log = LoggerClass(logger)

    g.config = MyConfig()
    Log.set_console_handler_loglevel()
    Log.add_file_logger()

    # app = QApplication(sys.argv)

    # Get local language and install if available.
    # locale = QtCore.QLocale.system().name()
    # logger.debug("locale: %s" % locale)
    # translator = QtCore.QTranslator()
    # if translator.load("dxf2gcode_" + locale, "./i18n"):
    #     app.installTranslator(translator)

    # If string version_mismatch isn't empty, we popup an error and exit
    # if g.config.version_mismatch:
        # error_message = QMessageBox(QMessageBox.Critical, 'Configuration error', g.config.version_mismatch)
        # sys.exit(error_message.exec_())


    from gui.canvas2dnogui import MyNoGraphicsScene
    # from gui.canvas2dnogui import ShapeNoGUI as Shape
    from core.shape import Shape

    window = MainWindow()
    g.window = window

    # command line options
    parser = argparse.ArgumentParser()

    parser.add_argument("filename", nargs="?")

#    parser.add_argument("-f", "--file", dest = "filename",
#                        help = "read data from FILENAME")
    parser.add_argument("-e", "--export", dest="export_filename",
                        help="export data to FILENAME")
    parser.add_argument("-q", "--quiet", action="store_true",
                        dest="quiet", help="no GUI")
    options = parser.parse_args()

    # (options, args) = parser.parse_args()
    logger.debug("Started with following options:\n%s" % parser)


    if options.filename is not None:
        window.filename = str_decode(options.filename)
        window.load()

    if options.export_filename is not None:
        window.exportShapes(None, options.export_filename)

    if not options.quiet:
        # It's exec_ because exec is a reserved word in Python
        sys.exit(app.exec_())
