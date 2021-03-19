#####################################################################################
# CanBadger SD FileSystem Model                                                     #
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
from PySide2.QtWidgets import QFileIconProvider

from datatypes import FS_Item

class SD_FS_Model(QAbstractItemModel):
    def __init__(self, parent=None, *args):
        super().__init__(parent, *args)
        self.root = FS_Item("/")
        self.header_labels = ['Name', 'Children']
        self.icon_provider = QFileIconProvider()

    # return an index for the given row/column pair and the parent element
    # this index is then used by views to access data
    def index(self, row: int, column: int, parent: QModelIndex = None) -> QModelIndex:
        if not parent or not parent.isValid():
            parent_item = self.root
        else:
            parent_item = parent.internalPointer()

        # check if row is valid
        if row >= parent_item.child_count():
            return QModelIndex()

        child_item = parent_item.child(row)

        # check if column is valid for child
        if column >= child_item.column_count():
            return QModelIndex()

        # return the valid index for the childs column
        return self.createIndex(row, column, child_item)

    def parent(self, index: QModelIndex = None) -> QModelIndex:
        if not index.isValid():
            return QModelIndex()

        child_item = index.internalPointer()
        parent_item = child_item.parent()

        # return invalid index if we hit root
        if parent_item == self.root:
            return QModelIndex()

        return self.createIndex(parent_item.row(), 0, parent_item)

    # returns the amount of nested rows aka children for the parent item the index identifies
    def rowCount(self, parent: QModelIndex = None) -> int:
        # if the column count is nonzero we return
        # indices that identify a node/row and not a value/field have column=0 by convention
        if parent is not None and parent.column() > 0:
            return 0

        if not parent or not parent.isValid():
            parent_item = self.root
        else:
            parent_item = parent.internalPointer()

        return parent_item.child_count()

    # returns the number of columns available for an index
    def columnCount(self, index: QModelIndex = None) -> int:
        # for now, we accept indices with column>0, as there is no drawback
        if index is not None and index.isValid():
            return index.internalPointer().column_count()
        return self.root.column_count()

    # returns the value of the data attribute mapped to the column
    # column mapping is done in the respective class the CanItem holds
    # via the column_representation classmethod
    def data(self, index: QModelIndex, role: int = None):
        # we return None for root data or roles we dont serve
        if not index.isValid():
            return None
        if role == Qt.DecorationRole and index.column() == 0:
            if index.internalPointer().dir:
                return self.icon_provider.icon(QFileIconProvider.Folder)
            else:
                return self.icon_provider.icon(QFileIconProvider.File)
        elif role == Qt.DisplayRole:
            # we get the desired data by calling the CanItems data() function
            # that then calls the held objects get_data function
            return index.internalPointer().data(index.column())

        return None

    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        if not index.isValid():
            return Qt.NoItemFlags
        return Qt.ItemIsEnabled | Qt.ItemIsSelectable

    # returns header labeling, atm just copied from the table model
    def headerData(self, section, orientation, role: Qt.DisplayRole = None):
        if role == Qt.DisplayRole and orientation == Qt.Orientation.Horizontal:
            return self.header_labels[section]
        return QAbstractTableModel.headerData(self, section, orientation, role)

    def add_item(self, index: QModelIndex, name: str, is_dir: bool):
        # find the parent
        if index is None or not index.isValid():
            parent_item = self.root
        else:
            parent_item = index.internalPointer()

        item = FS_Item(name, is_dir=is_dir, parent=parent_item)

        # send insert signals and append child
        self.beginInsertRows(index, parent_item.child_count(), parent_item.child_count())
        parent_item.append_child(item)
        self.endInsertRows()

    def remove_item(self, index: QModelIndex):
        # cant remove root
        if index is None or not index.isValid():
            return

        # retrieve parameters fo signal call
        parent_item = index.internalPointer().parent()
        parent_index = self.parent(index)
        row = index.row()

        # remove child from parent
        self.beginRemoveRows(parent_index, row, row)
        parent_item.remove_child(row)
        self.endRemoveRows()

    def child_index_by_name(self, parent_index: QModelIndex, name: str) -> QModelIndex:
        if not parent_index.isValid():
            parent = self.root
        else:
            parent = parent_index.internalPointer()

        for child in parent.children:
            if child.name == name:
                return self.createIndex(child.row(), 0, child)
        # no child has the name -> return invalid Index
        return QModelIndex()

    # search through the items according to the given directory path and return index to end of path
    def index_for_path(self, path: str) -> QModelIndex:
        # return an invalid index for the root
        if path == "/":
            return QModelIndex()

        slash1 = 0
        slash2 = path.find("/", slash1+1)

        if slash2 == -1:
            directory = path[slash1+1:]
        else:
            directory = path[slash1+1:slash2]

        path_end_index = self.child_index_by_name(QModelIndex(), directory)

        while True:
            if not path_end_index.isValid():
                # subdirectory not found, return None
                return None

            # go deeper if we have a longer path
            if slash2 != -1:
                slash1 = slash2
                slash2 = path.find("/", slash1+1)
            else:
                return path_end_index

            if slash2 == -1:
                directory = path[slash1 + 1:]
            else:
                directory = path[slash1 + 1:slash2]

            path_end_index = self.child_index_by_name(path_end_index, directory)

    def is_filled(self) -> bool:
        return self.root.child_count() > 0




