#####################################################################################
# CanBadger FrameDelegate                                                           #
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


from PySide2.QtWidgets import QStyledItemDelegate, QStyleOptionViewItem, QStyle, QApplication
from PySide2.QtGui import *
from PySide2.QtCore import *


# custom delegate to allow for bytewise drawing of data and highlighting
class FrameDelegate(QStyledItemDelegate):
    def __init__(self, model=None, proxy=None):
        super().__init__(parent=None)
        self.model = model
        self.proxy = proxy

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex):

        # let the standard delegate handle painting the non payload columns for now
        if index.column() not in (1, 2):
            super().paint(painter, option, index)
            return

        index = self.proxy.mapToSource(index)

        # setup option
        self.initStyleOption(option, index)

        # save the painter state and get the style object
        painter.save()
        style = option.widget.style()
        qfm = painter.fontMetrics()

        if index.column() == 1:  # display sender ids in hex
            option.text = hex(int(option.text))[2:].upper()
            style.drawControl(QStyle.CE_ItemViewItem, option, painter)

        else:  # print payload with highlights
            # get the frames highlighting info
            if self.proxy.highlightMode and index.row() in self.model.highlight_dict:
                highlight_bytes = self.model.highlight_dict[index.row()]
            else:
                highlight_bytes = set()

            # get the full payload from the option, then print it bytewise
            full_payload = option.text
            payload_length = len(full_payload)
            byte_counter = 0
            painter.setBackground(QBrush(Qt.cyan))

            for i in range(0, payload_length-1, 2):
                if byte_counter in highlight_bytes:
                    painter.setBackgroundMode(Qt.OpaqueMode)
                else:
                    painter.setBackgroundMode(Qt.TransparentMode)

                option.text = full_payload[i:i+2].upper()
                style.drawControl(QStyle.CE_ItemViewItem, option, painter)
                painter.translate(qfm.horizontalAdvance("DD ", 3), 0)
                byte_counter += 1

        # restore the painter state
        painter.restore()

    def sizeHint(self, option: QStyleOptionViewItem, index: QModelIndex) -> QSize:

        if index.column() != 2:
            return super().sizeHint(option, index)

        # setup option
        # self.initStyleOption(option, index)

        return QSize(300, 10)

