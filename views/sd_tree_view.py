#####################################################################################
# CanBadger SD Tree View                                                            #
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

from PySide2.QtCore import Signal, Slot, QModelIndex
from PySide2.QtCore import Qt
from PySide2.QtWidgets import QTreeView, QMenu
from PySide2.QtGui import QMouseEvent


class SDTreeView(QTreeView):

    def __init__(self, parent):
        super().__init__(parent)
        self.lineedit = None
        self.handler = None

    def setPathLineEdit(self, ledit):
        self.lineedit = ledit

    def setHandler(self, handler):
        self.handler = handler

    # overwriting function to enable deselection of directories and files
    def mousePressEvent(self, event: QMouseEvent):
        # deselect directory or file on additional click
        button = event.button()
        if button == Qt.MouseButton.LeftButton:
            if self.selectedIndexes():
                click_index = self.indexAt(event.pos())
                selected_index = self.selectedIndexes()[0]
                if click_index == selected_index:
                    self.selectionModel().clear()
                    if self.lineedit is not None:
                        self.lineedit.setText("/")

                    return

        super().mousePressEvent(event)

    # adding context menu
    def contextMenuEvent(self, event):
        # get current selection
        index = self.indexAt(event.pos())

        # only allow files in the top level
        if index.internalPointer().dir or index.parent().isValid():
            return

        if index.row() >= 0 and index.column() >= 0:
            menu = QMenu()
            setSettingsAction = menu.addAction("Set as Settings")
            setSettingsAction.triggered.connect(lambda: self.placeholder(index))
            action = menu.exec_(event.globalPos())

    # send filename to cb as new setings filename
    def placeholder(self, index):
        item = index.internalPointer()
        path = item.get_filepath()
        self.handler.sendSettingsFilename(path)


