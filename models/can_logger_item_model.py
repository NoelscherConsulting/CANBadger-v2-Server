#####################################################################################
# CanBadger Can Logger Item Model                                                   #
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
from datatypes.can_item import CanItem, ItemType
from datatypes.can_frame import CanFrame
from exceptions import PointerlessIndexException


# compares two payloads to determine highlighting for the second one
def highlighting_compare(last_sent_payload: bytes, now_sent_payload: bytes) -> set:
    highlight_bytes = set()

    for i in range(len(now_sent_payload)):
        # mark all bytes in the part of the payload that is longer than the last payload
        if i >= len(last_sent_payload):
            highlight_bytes.add(i)
        # mark all bytes that differ from previously sent byte
        elif last_sent_payload[i] != now_sent_payload[i]:
            highlight_bytes.add(i)

    return highlight_bytes


class CanLoggerItemModel(QAbstractItemModel):
    resetRow = Signal(int)

    def __init__(self, parent=None, *args):
        super().__init__(parent, *args)
        self.root = CanItem(model=self)
        self.header_labels = ['#', 'ID', 'Payload', 'Interface', 'Occurrence']

        # used to keep count of frames, could use root children but we might nest more in the future!
        self.frame_count = 0

        # occurrence_dict to keep track of multiples of frames (aka count frames with same content)
        # sender_dict to track last message from each sender id
        # highlight_dict to store highlight information
        self.occurrence_dict = dict()
        self.sender_dict = dict()
        self.highlight_dict = dict()

    # return an index for the given row/column pair and the parent element
    # this index is then used by views to access data
    def index(self, row: int, column: int, parent: QModelIndex = None) -> QModelIndex:
        # get parent CanItem
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
        elif role != Qt.DisplayRole:
            return None

        # we get the desired data by calling the CanItems data() function
        # that then calls the held objects get_data function
        return index.internalPointer().data(index.column())

    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        if not index.isValid():
            return Qt.NoItemFlags

        if index.column() != 2:
            return Qt.ItemIsEnabled | Qt.ItemIsSelectable
        else:
            return Qt.ItemIsEnabled

    # returns header labeling, atm just copied from the table model
    def headerData(self, section, orientation, role: Qt.DisplayRole = None):
        if role == Qt.DisplayRole and orientation == Qt.Orientation.Horizontal:
            return self.header_labels[section]
        return QAbstractTableModel.headerData(self, section, orientation, role)

    # we wrap the frame in an item and attack it as a child to the index
    def add_frame(self, index: QModelIndex, frame: CanFrame):
        # find the parent
        if not index.isValid():
            parent_item = self.root
        else:
            parent_item = index.internalPointer()

        # save models frame counter in frame
        self.frame_count += 1
        frame.set_counter(self.frame_count)

        # create new item and add as child
        item = CanItem(model=self, parent=parent_item, frame=frame)

        # send insert signals and append child
        self.beginInsertRows(index, parent_item.child_count(), parent_item.child_count())
        parent_item.append_child(item)
        # add to hashmap
        self.hash_increase(item)
        self.endInsertRows()

    # retrieve the object stored in the items data at index ## TODO replace return with Union[CanFrame, CanMessage]
    def get_can_object(self, index: QModelIndex) -> CanFrame:
        if not index.isValid():
            return None

        return index.internalPointer().get_data()

    # get the type of object that is stored in the CanItem
    def get_can_object_type(self, index: QModelIndex) -> ItemType:
        if not index.isValid():
            return None

        return index.internalPointer().get_type()

    # add multiple frames to model
    def add_frames(self, index: QModelIndex, frames: [CanFrame]):
        for frame in frames:
            self.add_frame(index, frame)

    # get list representation of all frames
    def get_frame_list(self):
        frames = []
        for item in self.root.children:
            frames.append(item.list_representation())
        return frames

    # removes all items except for the root
    # can be used together with add_frames() to achieve the table models set_frames() functionality
    # TODO affect hashmap correctly
    def clear(self, index: QModelIndex):
        if not index.isValid():
            parent_item = self.root
        else:
            parent_item = index.internalPointer()

        parent_item.remove_children()
        self.layoutChanged.emit()

    def remove_item(self, index: QModelIndex):
        # cant remove root
        if not index.isValid():
            return

        # retrieve parameters fo signal call
        parent_item = index.internalPointer().parent()
        parent_index = self.parent(index)
        row = index.row()

        # decrease hashmap entry
        self.hash_decrease(index.internalPointer().get_compare_hash())

        # remove child from parent
        self.beginRemoveRows(parent_index, row, row)
        parent_item.remove_child(index.row())
        self.endRemoveRows()
        self.layoutChanged.emit()

    # functions that increase or decrease counts in the hashmap we use to track multiples of frames (frame occurrence)
    # and keep track of the last message from each id + use this info to get the highlighting done
    def hash_increase(self, item: CanItem):
        # handle occurrence
        item_hash = item.get_compare_hash()
        if item_hash in self.occurrence_dict:
            self.occurrence_dict[item_hash] += 1
        else:
            self.occurrence_dict[item_hash] = 1

        if item.get_type() == ItemType.CanFrame:
            # check for highlighting
            f_id = item.get_data().frame_id
            if f_id in self.sender_dict:
                last_sent_row = self.sender_dict[f_id]

                # compare payloads to decide which bytes need highlighting
                last_sent_payload = self.root.child(last_sent_row).get_data().frame_payload
                frame = item.get_data()
                now_sent_payload = frame.frame_payload
                self.highlight_dict[item.row()] = highlighting_compare(last_sent_payload, now_sent_payload)

            # set this item as the last message from the sender
            last_row = None if f_id not in self.sender_dict else self.sender_dict[f_id]
            self.sender_dict[f_id] = item.row()
            if last_row is not None:
                self.resetRow.emit(last_row)

    def hash_decrease(self, item_hash: int):
        # handle occurrence
        if item_hash in self.occurrence_dict:
            self.occurrence_dict[item_hash] -= 1
            if self.occurrence_dict[item_hash] == 0:
                del self.occurrence_dict[item_hash]

        # TODO sender handling
        # this could be nasty because we have to search for the previously last sent message
        # which could add significant overhead for big frame counts
        # currently not implemented as we remove frames, like, never

    def hash_get(self, item_hash: int) -> int:
        return self.occurrence_dict[item_hash]

    # checks in the sender dict if a given row was the last frame for a given sender id
    def is_last_from_sender(self, f_id: int, row: int) -> bool:
        if self.sender_dict[f_id] == row:
            return True
        return False

    # used to transform indices with no valid internal pointer
    def translate_index(self, invalid_index: QModelIndex) -> QModelIndex:
        if invalid_index.parent().isValid():
            return self.index(invalid_index.row(), invalid_index.column(), self.translate_index(invalid_index.parent()))
        else:
            return self.index(invalid_index.row(), invalid_index.column(), QModelIndex())
