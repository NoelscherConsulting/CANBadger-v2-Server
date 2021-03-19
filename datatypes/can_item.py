#####################################################################################
# CanBadger CanItem                                                                 #
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

# class that holds can frames or messages as data and wraps them for use in a
# qt item model for a tree view

# used to define the types of objects we can hold
from enum import Enum

# importing the classes this item can hold
from datatypes.can_frame import CanFrame

# to implement enum ordering for sorting
from functools import total_ordering


@total_ordering
class ItemType(Enum):
    CanFrame = 0
    CanMessage = 1

    def __lt__(self, other):
        if self.__class__ is other.__class__:
            return self.value < other.value
        return NotImplemented


class CanItem:
    def __init__(self, model=None, parent=None, frame=None, message=None):
        # type will track if we wrap a can frame or a message
        # data will contain that frame or message
        if frame is not None:
            self.type = ItemType.CanFrame
            self.can_data = frame
            frame.item_container = self
        elif message is not None:
            self.type = ItemType.CanMessage
            self.can_data = message
        else:
            self.type = None
            self.can_data = None

        # children holds nested CanItems (eg frames for a message)
        # parent is the parent item (the models root item for top level items, None for the root)
        self.children = []
        self.parent_item = parent

        # the item carries a reference to the model for data requests that the model has to provide
        self.model = model

    # appends a child at the end of the list of children
    def append_child(self, child):
        self.children.append(child)

    # returns the number of children
    def child_count(self) -> int:
        return len(self.children)

    # qt retrieves data with row & column
    # we have to manually map our object attributes to columns
    # here we return how many columns we implemented for each ItemType
    def column_count(self):
        if self.type is None:
            return 5  # view is dependant on root columns
        elif self.type is ItemType.CanMessage:
            return 0
        else:  # CanFrame
            return len(CanFrame.column_representation())

    # returns the data for a given column
    # depending on itm type we map columns to different object attributes
    def data(self, column: int):
        # check for valid column
        if column < 0 or column > self.column_count():
            return False

        if type is None:
            return False
        elif type is ItemType.CanMessage:
            return 'message'
        else:
            return self.can_data.get_column(column)

    # returns the Items parent
    def parent(self) -> 'CanItem':
        return self.parent_item

    # returns this items row number aka its number in the children of its parent
    def row(self) -> int:
        if self.parent_item is None:
            return 0

        return self.parent_item.children.index(self)

    # returns the child CanItem at given row
    def child(self, row: int) -> 'CanItem':
        if row < 0 or row >= len(self.children):
            return None

        return self.children[row]

    # return the object held in data
    def get_data(self):
        return self.can_data

    # return the type of the held object
    def get_type(self) -> ItemType:
        return self.type

    # removes all children of this item
    def remove_children(self):
        self.children = []

    def remove_child(self, row: int):
        del self.children[row]

    # calls the hash function of the contained data
    def get_compare_hash(self):
        return self.can_data.get_compare_hash()

    # returns list representation of held data
    def list_representation(self):
        return self.can_data.list_representation()
