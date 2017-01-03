# -*- coding: utf-8 -*-

############################################################################
#
#   Copyright (C) 2015-2016
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
@purpose: build a configuration window on top of ConfigObj configfile module.

It aims to be generic and reusable for many configuration windows.

*** Basic usage ***

The my __subtitle__ is not restricted to be placed under __section_title__ it can be placed on any line and
it is also not restricted to be named like that. You can even leave it out. If you do it's replaced by a line.
If you place it on a different line (with the name:__subtitle__), this subsection does not start with horizontal bar.

3) Instanciate the config window:
config_window = ConfigWindow(config_widget_dict, var_dict, configspec, self) #See ConfigObj for var_dict & configspec
config_window.finished.connect(self.updateConfiguration) #Optional signal to know when the config has changed

*** List of graphical elements currently supported ***
 - CfgSubtitle(): subtitle - just for displaying a bar with some text
 - CfgCheckBox(): a basic (possibly tristate) checkbox
 - CfgSpinBox(): a spinbox for int values
 - CfgDoubleSpinBox(): a spinbox for float values
 - CfgLineEdit(): a text input (1 line)
 - CfgListEdit(): a text list input (1 line)
 - CfgTextEdit(): a text input (multiple lines)
 - CfgComboBox(): a drop-down menu for selecting options
 - CfgTable(): a 2D table with editable text entries
 - CfgTableCustomActions(): specific module based on CfgTable(), for storing custom GCODE
 - CfgTableToolParameters(): specific module based on CfgTable(), for storing mill tools
"""

from __future__ import absolute_import

import logging

from globals.helperfunctions import toInt, toFloat, str_encode, qstr_encode

from globals.six import text_type
import globals.constants as c


try:
    from collections import OrderedDict
except ImportError:
    from globals.ordereddict import OrderedDict

logger = logging.getLogger("Gui.ConfigWindow")


class ConfigWindow():
    # Applied = QDialog.Accepted + QDialog.Rejected + 1 #Define a result code that is different from accepted and rejected

    """Main Class"""
    def __init__(self, definition_dict, config = None, configspec = None, parent = None, title = "Configuration"):
        """
        Initialization of the Configuration window. ConfigObj must be instanciated before this one.
        @param definition_dict: the dict that describes our window
        @param config: data readed from the configfile. This dict is created by ConfigObj module.
        @param configspec: specifications of the configfile. This variable is created by ConfigObj module.
        """
        self.edition_mode = False #No editing in progress for now

        self.cfg_window_def = definition_dict #This is the dict that describes our window
        self.var_dict = config #This is the data from the configfile (dictionary created by ConfigObj class)
        self.configspec = configspec #This is the specifications for all the entries defined in the config file

        #There is no config file selector for now, so no callback either
        self.selector_change_callback = None
        self.selector_add_callback = None
        self.selector_remove_callback = None
        self.selector_duplicate_callback = None

        #Create the vars for the optional configuration's file selector
        self.cfg_file_selector = None

    def configspecParser(self, configspec, comments):
        """
        This is a really trivial parser for ConfigObj spec file. This parser aims to exctract the limits and the available options for the entries in the config file. For example:
        if a config entry is defined as "option('mm', 'in', default = 'mm')", then the parser will create a list with ['mm', 'in]
        similarly, if an entry defined as "integer(max=9)", the max value will be exctracted
        @param configspec: specifications of the configfile. This variable is created by ConfigObj module.
        @param comments: string list containing the comments for a given item
        @return The function returns a dictionary with the following fields
        - minimum : contains the minimum value or length for an entry (possibly 'None' if nothing found)
        - maximum : contains the maximum value or length for an entry (possibly 'None' if nothing found)
        - string_list : contains the list of options for an "option" field, or the column titles for a table
        - comment : a text with the comment that belongs to the parameter (possibly an empty string if nothing found)
        """
        #logger.debug('configspecParser({0}, {1})'.format(configspec, comments))
        minimum = None
        maximum = None
        string_list = []

        if isinstance(configspec, dict):
            #If the received configspec is a dictionary, we most likely have a table, so we are going to exctract sections names of this table

                #When tables are used, the "__many__" config entry is used for the definition of the configspec, so we try to excract the sections names by using this __many__ special keyword.
                #Example: 'Tool_Parameters': {[...], '__many__': {'diameter': 'float(default = 3.0)', 'speed': 'float(default = 6000)', 'start_radius': 'float(default = 3.0)'}}
                if '__many__' in configspec and isinstance(configspec['__many__'], dict):
                    string_list = configspec['__many__'].keys()
                    string_list.insert(0, '') #prepend an empty element since the first column of the table is the row name (eg a unique tool number)

        else:
            #configspec is normaly a string from which we can exctrat min / max values and possibly a list of options

            #Handle "option" config entries
            string_list = self.configspecParserExctractSections('option', configspec)
            i = 0
            while i < len(string_list): #DON'T replace this with a "for", it would silently skip some steps because we remove items inside the loop
                #remove unwanted items which are unquoted (like the "default=" parameter) and remove the quotes
                if string_list[i].startswith('"'):
                    string_list[i] = string_list[i].strip('"')
                elif string_list[i].startswith("'"):
                    string_list[i] = string_list[i].strip("'")
                else:
                    #unwanted item, it doesn't contain an element of the option()
                    del string_list[i]
                    continue

                i += 1

            #Handle "integer" and "string" config entries
            if len(string_list) <= 0:
                string_list = self.configspecParserExctractSections('integer', configspec)
                if len(string_list) <= 0:
                    string_list = self.configspecParserExctractSections('string', configspec)

                minimum, maximum = self.handle_type_config_entries(minimum, maximum, string_list, toInt)

            #Handle "float" config entries
            if len(string_list) <= 0:
                string_list = self.configspecParserExctractSections('float', configspec)

                minimum, maximum = self.handle_type_config_entries(minimum, maximum, string_list, toFloat)

        #Handle comments: comments are stored in a list and contains any chars that are in the configfile (including the hash symbol and the spaces)
        comments_string = ''
        if len(comments) > 0:
            for comment in comments:
                comments_string += comment.strip()

            comments_string = comments_string.strip(' #')
            comments_string = comments_string.replace('#', '\n')

        logger.debug('configspecParser(): exctracted option elements = {0}, min = {1}, max = {2}, comment = {3}'.format(string_list, minimum, maximum, comments_string))

        result = {}
        result['minimum'] = minimum
        result['maximum'] = maximum
        result['string_list'] = string_list
        result['comment'] = comments_string
        return result

    def handle_type_config_entries(self, minimum, maximum, string_list, type_converter):
        for element in string_list:
            if minimum is not None and maximum is not None:
                break

            value = type_converter(element)
            if value[1]:
                if minimum is None:
                    minimum = value[0]
                elif maximum is None:
                    maximum = value[0]

            if minimum is None and 'min' in element:
                # string found in a string like "min = -7"
                element = element.replace('min', '')
                element = element.strip(' =')
                value = type_converter(element)
                if value[1]:
                    minimum = value[0]

            if maximum is None and 'max' in element:
                # 'max' string found
                element = element.replace('max', '')
                element = element.strip(' =')
                value = type_converter(element)
                if value[1]:
                    maximum = value[0]

        return minimum, maximum

    def configspecParserExctractSections(self, attribute_name, string):
        """
        returns a list of item from a string. Eg the string "option('mm', 'in', default = 'mm')" will be exploded into the string list ["mm", "in", "default = 'mm'"]
        """
        string_list = []

        pos_init = string.find(attribute_name + '(')
        if pos_init >= 0:
            pos_init += len(attribute_name + '(') #skip the "option("

            pos_end = string.find(')', pos_init)
            if pos_end > pos_init:
                #print("substring found = {0}".format(string[pos_init:pos_end]))
                string_list = string[pos_init:pos_end].split(',')

        # remove empty elements and remove leading and trailing spaces
        string_list = [string.strip() for string in string_list if string]
        return string_list

    def validateConfiguration(self, window_def, result_string = '', result_bool = True):
        """
        Check the configuration (check the limits, eg min/max values, ...). These limits are set according to the configspec passed to the constructor
        @param window_def: the dict that describes our window
        @param result_string: use only for recursive call
        @param result_bool: use only for recursive call
        @return (result_bool, result_string):
         - result_bool: True if no errors were encountered, False otherwise
         - result_string: a string containing all the errors encountered during the validation
        """
        #Compute all the sections
        # for section in window_def:
        #     #skip the special section __section_title__
        #     if section == '__section_title__' or isinstance(window_def[section], CfgDummy):
        #         continue
        #
        #     if isinstance(window_def[section], dict):
        #         #Browse sublevels
        #         (result_bool, result_string) = self.validateConfiguration(window_def[section], result_string, result_bool) #Recursive call, until we find a real item (not a dictionnary with subtree)
        #     else:
        #         if isinstance(window_def[section], (QWidget, QLayout)):
        #             #check that the value is correct for each widget
        #             result = window_def[section].validateValue()
        #             if result[0] is False: result_bool = False
        #             result_string += result[1]
        #         else:
        #             #Item should be a layout or a widget
        #             logger.warning("item {0} is not a widget, can't validate it!".format(window_def[section]))
        #
        # return (result_bool, result_string)


