#####################################################################################
# CanBadger Can Logger Table View                                                   #
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

from PySide2.QtCore import Signal, Slot
from PySide2.QtWidgets import QTreeView, QMenu


class CanLoggerTreeView(QTreeView):
    sendToReplay = Signal(list)
    createRuleForId = Signal(list)
    createRuleForPayload = Signal(list)

    def __init__(self, parent):
        super().__init__(parent)

    def contextMenuEvent(self, event):
        # get current selection
        index = self.indexAt(event.pos())
        if index.row() >= 0 and index.column() >= 0:
            menu = QMenu()
            replayAction = menu.addAction("Send to Replay")
            replayAction.triggered.connect(self.onReplayActionTriggered)
            '''
            createRuleByIdAction = menu.addAction("Create Rule for ID")
            createRuleByIdAction.triggered.connect(self.onCreateRuleByIdActionTriggered)
            createRuleByPayloadAction = menu.addAction("Create Rule for Payload")
            createRuleByPayloadAction.triggered.connect(self.onCreateRuleByPayloadActionTriggered)
            '''
            action = menu.exec_(event.globalPos())

    #  we have to convert the current CanFrame object to the old representation
    #  until we also port these functions to use CanFrame objects
    @Slot()
    def onReplayActionTriggered(self):
        invalid_index = self.currentIndex()
        index = self.model().sourceModel().translate_index(invalid_index)
        frame = self.model().sourceModel().get_can_object(index)
        self.sendToReplay.emit([frame.model_counter, frame.frame_id, frame.frame_payload, frame.interface_number])

    @Slot()
    def onCreateRuleByIdActionTriggered(self):
        # frame = self.model().sourceModel().getFrame(self.currentIndex())
        frame = self.model().sourceModel().get_can_object(self.currentIndex())
        self.createRuleForId.emit([self.currentIndex().row(), frame.get_column(0), frame.get_column(1)])

    @Slot()
    def onCreateRuleByPayloadActionTriggered(self):
        # frame = self.model().sourceModel().getFrame(self.currentIndex())
        frame = self.model().sourceModel().get_can_object(self.currentIndex())
        self.createRuleForPayload.emit([self.currentIndex().row(), frame.get_column(0), frame.get_column(1)])