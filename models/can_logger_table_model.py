#####################################################################################
# CanBadger Can Table Model                                                         #
# Copyright (c) 2021 Noelscher Consulting GmbH                                      #
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


class CanLoggerTableModel(QAbstractTableModel):
    def __init__(self, parent=None, *args):
        QAbstractTableModel.__init__(self, parent, *args)
        self.can_data = []
        self.header_labels = ['Frame Count', 'ID', 'Payload', 'Interface']

    def rowCount(self, parent=QModelIndex()):
        return len(self.can_data)

    def columnCount(self, parent):
        return 4

    def data(self, index, role):
        if not index.isValid():
            return None
        elif role != Qt.DisplayRole:
            return None
        if index.column() == 0:  # frame count
            return self.can_data[index.row()][0]
        elif index.column() == 1:  # id
            return hex(self.can_data[index.row()][1])
        elif index.column() == 2:  # payload
            # return self.can_data[index.row()][2].hex()
            return ''.join('{:02X} '.format(x) for x in self.can_data[index.row()][2])
        elif index.column() == 3:  # interface
            return self.can_data[index.row()][3]
        # return self.can_data[index.row()][index.column()] # TODO

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self.header_labels[section]
        return QAbstractTableModel.headerData(self, section, orientation, role)

    def addFrame(self, frame):
        self.can_data.append(frame)
        self.layoutChanged.emit()

    def getFrame(self, index):
        return self.can_data[index.row()]

    def getFrames(self):
        return self.can_data

    def setFrames(self, frames):
        self.can_data = frames
        self.layoutChanged.emit()

    def removeFrame(self, index):
        if len(self.can_data) > 0:
            self.beginRemoveRows(index, index.row(), 1)
            del self.can_data[index.row()]
            self.endRemoveRows()
            self.layoutChanged.emit()

    def updateFrame(self, index, update_values):
        frame = self.can_data[index.row()]
        for k, v in update_values.items():
            frame[self.header_labels.index(k)] = v
        self.layoutChanged.emit()

    def moveUpFrame(self, index):
        if index is None or index.row() == 0 or index.row() > len(self.can_data)-1:
            return False

        frame = self.can_data[index.row()]
        self.can_data[index.row()] = self.can_data[index.row() - 1]
        self.can_data[index.row() - 1] = frame
        self.layoutChanged.emit()
        return True

    def moveDownFrame(self, index):
        if index is None or index.row() == (len(self.can_data) - 1):
            return False

        frame = self.can_data[index.row()]
        self.can_data[index.row()] = self.can_data[index.row() + 1]
        self.can_data[index.row() + 1] = frame
        self.layoutChanged.emit()
        return True

    def supportedDragActions(self, *args, **kwargs):
        return Qt.MoveAction # todo check dis, if override works
