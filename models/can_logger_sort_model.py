#####################################################################################
# CanBadger Can Logger Sort Model                                                   #
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
from datatypes.can_item import CanItem, ItemType
import re


class CanLoggerSortModel(QSortFilterProxyModel):
    def __init__(self, mainwindow):
        super().__init__()

        # These filters have no checkboxes and need to check their parameters to see if they are applied
        self.filterById = True
        self.payloadFilter = True

        # These filters are enabled by GUI checkboxes
        self.filterAfterNSamples = False
        self.filteringEnabled = False
        self.compactFilter = False
        self.highlightMode = False
        self.mainwindow = mainwindow

        # fill this information when invalidating, so we dont have to get it for each item separate
        self.id_filter_input = None
        self.filter_ids = None
        self.payload_filter_input = None

        self.ids_before_n = set()

    # override to allow sorting of custom model
    # has to be able to handle all data types that can be held in a CanFrame or CanMessage
    def lessThan(self, left_index: QModelIndex, right_index: QModelIndex) -> bool:
        # extract the data we want to compare
        left_data = left_index.internalPointer().data(left_index.column())
        right_data = right_index.internalPointer().data(right_index.column())

        # check for matching type ## TODO implement sorting of different types??? idk!
        if type(left_data) != type(right_data):
            raise TypeError("Trying to sort different data types")

        if left_index.column() == 0:  # this is the counter field, need to compare ints and not Strings!
            left_data = int(left_data)
            right_data = int(right_data)

        # to ensure all types are comparable, it is required to implement a total_ordering for eg enums

        return left_data < right_data

    # returns a bool for a given row and given filter
    # as we do not filter at all atm this is TODO
    def filterAcceptsRow(self, row: int, parent: QModelIndex) -> bool:
        if not self.filteringEnabled:
            return True

        if parent.isValid():
            print("got a valid parent, weird man..")
            return False

        item = self.sourceModel().root.child(row)

        if self.compactFilter:
            if not self.filter_for_last_sent(row, item):
                return False

        if self.filterById:
            if not self.filter_for_id(item):
                return False

        if self.filterAfterNSamples:
            if not self.filter_after_n(item):
                return False

        if self.payloadFilter:
            if not self.filter_for_payload(item):
                return False

        return True

    # only returns True for rows that hold the last frame sent from a specific id
    # this is used to display the so called compact view
    def filter_for_last_sent(self, row: int, item: CanItem) -> bool:
        if item.get_type() != ItemType.CanFrame:
            return False

        f_id = item.get_data().frame_id
        # check back with the source model if the row should be shown
        return self.sourceModel().is_last_from_sender(f_id, row)

    # only returns True for rows whose id didn't already show up in the first N frames
    def filter_after_n(self, item: CanItem) -> bool:
        if item.get_type() != ItemType.CanFrame:
            return False

        f_id = item.get_data().frame_id

        if f_id not in self.ids_before_n:
            return True
        return False

    # only returns True for frames with the id specified in the filter options
    def filter_for_id(self, item: CanItem) -> bool:
        if item.get_type() != ItemType.CanFrame:
            return False

        # return true if no ids are entered (filter disabled)
        if not self.filter_ids:
            return True

        frame_id = hex(item.get_data().frame_id)[2:]
        return frame_id in self.filter_ids or frame_id.upper() in self.filter_ids

    # filters for certain payloads
    def filter_for_payload(self, item: CanItem):
        if item.get_type() != ItemType.CanFrame:
            return False

        # if the input parsing has failed, return True
        if (not self.payload_filter_input) or len(self.payload_filter_input) == 0:
            return True

        payload = self.convert_payload_to_list(item.get_data().frame_payload)

        # * is arbitrary payload before/after, _ is one Byte wildcard, everything else has to be a valid byte
        start_anywhere = self.payload_filter_input[0] == '*'
        end_anywhere = self.payload_filter_input[len(self.payload_filter_input) - 1] == '*'

        matches = self.prepare_matches(self.payload_filter_input)

        for match in matches:
            if matches.index(match) == 0:
                found, at = self.match_payload(match, payload, start_anywhere)
            else:
                found, at = self.match_payload(match, payload, True)

            if not found:
                return False

            if matches.index(match) != len(matches) -1:
                payload = payload[len(match)+at:]

        # might need to check the end again, if that byte combination already matched earlier
        if (not end_anywhere) and len(payload) > 0:
            found, _ = self.match_payload(matches[-1], payload[-len(matches[-1]):], False)
            return found

        return True

    # override to get some data useful for filtering on filter startup instead of doing the operation for every row
    def invalidateFilter(self):
        # get the list of ids recurring before N frames
        self.ids_before_n = set()
        num_frames = self.mainwindow.filterFramesAfterNSpinBox.value()
        for i in range(0, num_frames):
            item = self.sourceModel().root.child(i)
            if item.get_type() != ItemType.CanFrame:
                continue

            f_id = item.get_data().frame_id
            self.ids_before_n.add(f_id)

        # read id filter parameters
        self.id_filter_input = self.mainwindow.filterFramesByIdLineEdit.text()
        if self.id_filter_input is not None:
            self.filter_ids = list(map(str.lstrip, filter(None, self.id_filter_input.split(","))))
        else:
            self.filter_ids = None

        # prepare the payload filter
        self.payload_filter_input = self.mainwindow.payloadFilterLineEdit.text().lstrip().rstrip().split()
        for byte_descriptor in self.payload_filter_input:
            if len(byte_descriptor) == 1:
                if not (byte_descriptor == "*" or byte_descriptor == "_"):
                    self.payload_filter_input.remove(byte_descriptor)
                    break
            elif len(byte_descriptor) == 2:
                if re.compile(r'[^a-fA-F0-9.]').search(byte_descriptor):
                    # show input is invalid
                    self.mainwindow.payloadFilterLineEdit.setStyleSheet("background-color: red")
                    self.payload_filter_input = []
                    break
            else:
                # show input is invalid
                self.mainwindow.payloadFilterLineEdit.setStyleSheet("background-color: red")
                self.payload_filter_input = []
                break

        if len(self.payload_filter_input) != 0:
            self.mainwindow.payloadFilterLineEdit.setStyleSheet("")

        self.payload_filter_input = [x.upper() for x in self.payload_filter_input]

        super().invalidateFilter()

    # tries to find first payload in second payload
    def match_payload(self, check_for: [str], in_here: [str], anywhere: bool) -> (bool, int):
        if len(check_for) > len(in_here):
            return False, -1
        curr_byte = 0
        while curr_byte < len(check_for):
            if check_for[curr_byte] != in_here[curr_byte]:
                if check_for[curr_byte] == '_':
                    curr_byte += 1
                    continue  # check passes for a wildcard
                if anywhere:  # if we can match anywhere in the payload (*), we have to check the rest
                    found, at = self.match_payload(check_for, in_here[1:], anywhere)
                    if found:
                        return found, at+1
                    else:
                        return found, -1
                else:
                    return False, -1

            curr_byte += 1

        return True, 0

    # takes a payload  bytes, returns it as a list of Strings (1 String per Byte)
    def convert_payload_to_list(self, payload: bytes) -> [str]:
        payload_string = payload.hex().upper()
        return [payload_string[i:i+2] for i in range(0, len(payload_string), 2)]

    # splits a list of strings into multiple lists at '*'
    def prepare_matches(self, filter_input: [str]) -> [[str]]:
        result = list()
        sublist = list()
        if filter_input[0] != '*':
            sublist.append(filter_input[0])
        for i in range(1, len(filter_input)):
            if filter_input[i] != '*':
                sublist.append(filter_input[i])
            else:
                result.append(sublist)
                sublist = list()
        result.append(sublist)
        return list(filter(lambda x: x != [], result))




