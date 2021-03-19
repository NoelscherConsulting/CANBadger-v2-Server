#####################################################################################
# CanBadger FileSystem_Item                                                         #
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


# class to hold directories or files from the CB SD
# so they can be easily displayed

from PySide2.QtCore import QModelIndex

class FS_Item:
    def __init__(self, name: str, is_dir=True, parent=None):
        self.name = name
        self.dir = is_dir

        self.children = []
        self.parent_item = parent

    # append a child (will only work for directories)
    def append_child(self, child):
        if self.dir:
            self.children.append(child)

    # get number of children
    def child_count(self) -> int:
        return len(self.children)

    # get the number of columns per item
    def column_count(self):
        return 2

    # returns the data for a specified column
    def data(self, column: int):
        # check for valid column
        if column < 0 or column >= self.column_count():
            return False

        if column == 0:
            return self.name
        if column == 1:
            if self.dir:
                return str(self.child_count())
            else:
                return ""

    def parent(self) -> 'FS_Item':
        return self.parent_item

    def child(self, row: int) -> 'FS_Item':
        if row < 0 or row >= len(self.children):
            return None

        return self.children[row]

    # removes all children of this item
    def remove_children(self):
        self.children = []

    # removes children in given row
    def remove_child(self, row: int):
        del self.children[row]

    # returns this items row number aka its number in the children of its parent
    def row(self) -> int:
        if self.parent_item is None:
            return 0

        return self.parent_item.children.index(self)

    # gets the full path to this item by building it from parent names
    def get_filepath(self) -> str:
        if self.parent_item is None:
            return "/"

        parent_path = self.parent_item.get_filepath()
        if len(parent_path) > 1:
            return parent_path + "/" + self.name
        else:
            return parent_path + self.name

