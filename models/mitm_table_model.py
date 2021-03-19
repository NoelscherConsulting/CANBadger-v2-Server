#####################################################################################
# CanBadger Can MITM Table Model                                                    #
# Copyright (c) 2020 Noelscher Consulting GmbH                                      #
#                                                                                   #
# Permission is hereby granted, free of charge, to any person obtaining a copy      #
# of this software and associated documentation files (the "Software"), to deal     #
# in the Software without restriction, including without limitation the rights      #
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell         #
# copies of the Software, and to permit persons to whom the Software is             #
# furnished to do so, subject to the following conditions:                          #
#                                                                                   #
# The above copyright notice and this permission notice shall be included in        #
# all copies or substantial portions of the Software.                               #
#                                                                                   #
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR        #
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,          #
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE       #
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER            #
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,     #
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN         #
# THE SOFTWARE.                                                                     #
#####################################################################################

from PySide2.QtCore import *
from PySide2.QtGui import *
import json


class MITMTableModel(QAbstractTableModel):
    def __init__(self, parent=None, *args):
        QAbstractTableModel.__init__(self, parent, *args)
        self.rules = []
        self.header_labels = ['Rule Type', 'Rule Condition', 'Target ID', 'Cond Value',
                              'Cond Mask', 'Argument', 'Action Mask']

    def rowCount(self, parent):
        return len(self.rules)

    def columnCount(self, parent):
        return 7

    def data(self, index, role):
        if not index.isValid():
            return None
        elif role != Qt.DisplayRole:
            return None
        return self.rules[index.row()][index.column()]

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self.header_labels[section]
        return QAbstractTableModel.headerData(self, section, orientation, role)

    def addRule(self, rule):
        self.rules.append(rule)
        self.layoutChanged.emit()

    def removeRule(self, index):
        if index.row() > len(self.rules):
            return

        self.beginRemoveRows(index, index.row(), 1)
        del self.rules[index.row()]
        self.endRemoveRows()
        self.layoutChanged.emit()

    # remove all rules
    def clear(self):
        self.beginRemoveRows(QModelIndex(), 0, self.rowCount(QModelIndex()) - 1)
        self.rules = []
        self.endRemoveRows()
        self.layoutChanged.emit()

    def getRule(self, index):
        return self.rules[index.row()]

    def getRules(self):
        return self.rules

    # expects a dict as update_values containing the new rule/ changed values
    def updateRule(self, index, update_values):
        rule = self.rules[index.row()]
        for k,v in update_values.items():
            rule[self.header_labels.index(k)] = v
        self.layoutChanged.emit()

    def isEmpty(self):
        if len(self.rules) > 0: return False
        else: return True