# -*- coding: utf-8 -*-

############################################################################
#
#   Copyright (C) 2012-2015
#    Xavier Izard
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
This class is intended to deal with the drawing (.dxf) structure.
It has the following functions:
- populate the entities treeView and the layers treeView
- allow selection of shapes from any treeView and show the
  selection on the graphic view
- allow to enable/disable shapes from any treeView
- reflects into the treeView the changes that occurs on the graphic view
- set export order using drag & drop

@purpose: display tree structure of the .dxf file, select,
          enable and set export order of the shapes
"""

from __future__ import absolute_import

from math import degrees
import logging

import globals.globals as g

from core.shape import Shape
from core.entitycontent import EntityContent
from core.customgcode import CustomGCode
from gui.treeview import MyStandardItemModel

from globals.helperfunctions import toInt, toFloat

from globals.six import text_type
import globals.constants as c
if c.PYQT5notPYQT4:
    from PyQt5.QtWidgets import QAction, QMenu, QWidget, QAbstractItemView, QTreeView
    from PyQt5.QtCore import QItemSelectionModel, QItemSelection
    from PyQt5.QtGui import QStandardItem, QIcon, QPixmap, QStandardItemModel, QPalette
    from PyQt5 import QtCore
    isValid = lambda data: data
    toPyObject = lambda data: data
else:
    from PyQt4.QtGui import QAction, QMenu, QWidget, QAbstractItemView, QStandardItem, QIcon, QPixmap, \
        QTreeView, QStandardItemModel, QItemSelectionModel, QItemSelection, QPalette
    from PyQt4 import QtCore
    isValid = lambda data: data.isValid()
    toPyObject = lambda data: data.toPyObject()


class QVariantShape(QtCore.QVariant):
    """
    Wrapper is needed for PyQt5 since this version does not accept to add a QGraphisItem
     directly to a QStandardItem
    """
    def __init__(self, shapeobj):
        self.shapeobj = shapeobj


logger = logging.getLogger("Gui.TreeHandling")

# defines some arbitrary types for the objects stored into the treeView.
# These types will eg help us to find which kind of data is stored
# in the element received from a click() event
ENTITY_OBJECT = QtCore.Qt.UserRole + 1  # For storing refs to the entities elements (entities_list)
LAYER_OBJECT = QtCore.Qt.UserRole + 2  # For storing refs to the layers elements (layers_list)
SHAPE_OBJECT = QtCore.Qt.UserRole + 3  # For storing refs to the shape elements (entities_list & layers_list)
CUSTOM_GCODE_OBJECT = QtCore.Qt.UserRole + 4  # For storing refs to the custom gcode elements (layers_list)

PATH_OPTIMISATION_COL = 3  # Column that corresponds to TSP enable checkbox

class TreeHandlerNoQui():
    """
    Class to handle both QTreeView :  entitiesTreeView (for blocks, and the tree of blocks) and layersShapesTreeView (for layers and shapes)
    """

    def __init__(self, ui):
        """
        Standard method to initialize the class
        @param ui: the GUI
        """
        self.ui = ui
        self.layer_item_model = None
        self.layers_list = None
        self.auto_update_export_order = False
        self.entity_item_model = None
        self.entities_list = None

    def buildLayerTree(self, layers_list):
        """
        This method populates the Layers QTreeView with all the elements contained into the layers_list
        Method must be called each time a new .dxf file is loaded.
        options
        @param layers_list: list of the layers and shapes (created in the main)
        """
        self.layers_list = layers_list
        if self.layer_item_model:
            self.layer_item_model.clear()  # Remove any existing item_model
        self.layer_item_model = MyStandardItemModel()  # This is the container for the data (QStandardItemModel)
        if not c.PYQT5notPYQT4:
            self.layer_item_model.setSupportedDragActions(QtCore.Qt.MoveAction)
        self.layer_item_model.setHorizontalHeaderItem(0, QStandardItem("[en]"))
        self.layer_item_model.setHorizontalHeaderItem(1, QStandardItem("Name"))
        self.layer_item_model.setHorizontalHeaderItem(2, QStandardItem("Nr"))
        self.layer_item_model.setHorizontalHeaderItem(3, QStandardItem("Optimal path"))
        modele_root_element = self.layer_item_model.invisibleRootItem()  # Root element of our tree

        for layer in layers_list:
            icon = QIcon()
            icon.addPixmap(QPixmap(":/images/layer.png"))
            checkbox_element = QStandardItem(icon, "")
            checkbox_element.setData(QtCore.QVariant(layer), LAYER_OBJECT)  # store a ref in our treeView element
            modele_element = QStandardItem(layer.name)
            nbr_element = QStandardItem()
            optimise_element = QStandardItem()
            modele_root_element.appendRow([checkbox_element, modele_element, nbr_element, optimise_element])

            parent_item = modele_root_element.child(modele_root_element.rowCount() - 1, 0)
            containsChecked = False
            containsUnchecked = False
            for shape in layer.shapes:
                if isinstance(shape, CustomGCode):
                    # self.AddCustomGCodeRowLayer(shape, parent_item)
                    print 1
                else:
                    self.AddShapeRowLayer(shape, parent_item)


    def AddShapeRowLayer(self, shape, parent_item):
        icon = QIcon()
        icon.addPixmap(QPixmap(":/images/shape.png"))
        item_col_0 = QStandardItem(icon, "")
        item_col_0.setData(QVariantShape(shape), SHAPE_OBJECT)  # store a ref in our treeView element
        item_col_1 = QStandardItem(shape.type)
        item_col_2 = QStandardItem(str(shape.nr))
        item_col_3 = QStandardItem()
        parent_item.appendRow([item_col_0, item_col_1, item_col_2, item_col_3])

        # Deal with the checkboxes (shape enabled or disabled / send shape to TSP optimizer)
        item_col_0.setCheckState(QtCore.Qt.Unchecked if shape.isDisabled() else QtCore.Qt.Checked)
        item_col_3.setCheckState(QtCore.Qt.Checked if shape.isToolPathOptimized() else QtCore.Qt.Unchecked)

        flags = QtCore.Qt.ItemIsDragEnabled | QtCore.Qt.ItemIsSelectable
        if shape.allowedToChange:
            flags |= QtCore.Qt.ItemIsEnabled
        item_col_0.setFlags(flags | QtCore.Qt.ItemIsUserCheckable)
        item_col_1.setFlags(flags)
        item_col_2.setFlags(flags)
        item_col_3.setFlags(flags | QtCore.Qt.ItemIsUserCheckable)

    def buildEntitiesTree(self, entities_list):
        """
        This method populates the Entities (blocks) QTreeView with
        all the elements contained in the entities_list
        Method must be called each time a new .dxf file is loaded.
        options
        @param entities_list: list of the layers and shapes (created in the main)
        """

        self.entities_list = entities_list
        if self.entity_item_model:
            self.entity_item_model.clear()  # Remove any existing item_model
        self.entity_item_model = QStandardItemModel()
        self.entity_item_model.setHorizontalHeaderItem(0, QStandardItem("[en]"))
        self.entity_item_model.setHorizontalHeaderItem(1, QStandardItem("Name"))
        self.entity_item_model.setHorizontalHeaderItem(2, QStandardItem("Nr"))
        self.entity_item_model.setHorizontalHeaderItem(3, QStandardItem("Type"))
        self.entity_item_model.setHorizontalHeaderItem(4, QStandardItem("Base point"))
        self.entity_item_model.setHorizontalHeaderItem(5, QStandardItem("Scale"))
        self.entity_item_model.setHorizontalHeaderItem(6, QStandardItem("Rotation"))

        # Signal to get events when a checkbox state changes (enable or disable shapes)

        self.ui.entitiesTreeView.setModel(self.entity_item_model)
        self.ui.entitiesTreeView.expandToDepth(0)

        for i in range(6):
            self.ui.entitiesTreeView.resizeColumnToContents(i)

    def updateExportOrder(self, includeDisableds=False):
        """
        Update the layers_list order to reflect the TreeView order.
        This function must be called before generating the GCode
        (export function). Export will be performed in the order of the
        structure self.LayerContents of the main. Each layer contains
        some shapes, and the export order of the shapes is set by
        populating the exp_order[] list with the shapes reference number
        for each layer (eg exp_order = [5, 3, 2, 4, 0, 1] for layer 0,
        exp_order = [5, 3, 7] for layer 1, ...)
        options
        """

        i = self.layer_item_model.rowCount(QtCore.QModelIndex())
        while i > 0:
            i -= 1
            layer_item_index = self.layer_item_model.index(i, 0)

            if isValid(layer_item_index.data(LAYER_OBJECT)):
                real_layer = toPyObject(layer_item_index.data(LAYER_OBJECT))
                self.layers_list.remove(real_layer)  # Remove the layer from its original position
                self.layers_list.insert(0, real_layer)  # and insert it at the beginning of the layer's list

                real_layer.exp_order = []  # Clear the current export order
                real_layer.exp_order_complete = []  # Clear the current export order

                # Assign the export order for the shapes of the layer "real_layer"
                for j in range(self.layer_item_model.rowCount(layer_item_index)):
                    shape_item_index = self.layer_item_model.index(j, 0, layer_item_index)

                    real_shape = None
                    if isValid(shape_item_index.data(SHAPE_OBJECT)):
                        real_shape = toPyObject(shape_item_index.data(SHAPE_OBJECT)).shapeobj
                        if not real_shape.isDisabled() or includeDisableds:
                            real_layer.exp_order.append(real_shape.nr)  # Create the export order list with the real and unique shapes numbers (eg [25, 22, 30, 4, 1, 5])

                    if isValid(shape_item_index.data(CUSTOM_GCODE_OBJECT)):
                        real_shape = toPyObject(shape_item_index.data(CUSTOM_GCODE_OBJECT))

                    if real_shape and (not real_shape.isDisabled() or includeDisableds):
                        real_layer.exp_order_complete.append(real_layer.shapes.index(real_shape))  # Create the export order list with the shapes & custom gcode numbers (eg [5, 3, 2, 4, 0, 1])

