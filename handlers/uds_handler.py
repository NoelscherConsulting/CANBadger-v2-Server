#####################################################################################
# CanBadger UDS Handler                                                             #
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
from PySide2.QtWidgets import QComboBox, QPushButton, QLabel, QLineEdit
import struct
from canbadger_messages.uds_response import UdsResponse
from canbadger_messages.uds_request import UdsRequest
from uds.uds_enums import *
from uds.read_memory_by_address import ReadMemoryByAddress
from canbadger.canbadger_defines import CanbadgerInterface, CANFormat, AddressingType
from canbadger_messages.start_uds_message import StartUdsMessage
from uds.uds_response_parser import UdsResponseParser
from helpers import *
from enum import Enum

class UdsHandlerStatus(Enum):
    DISCONNECTED=0,
    CONNECTING=1,
    CONNECTED=2,
    BUSY=3


# TODO: scan valid ids
# TODO: read some info (vin etc.)
class UDSHandler(QObject):
    udsFunctions = [ 'SWITCH_SESSION', 'SCAN_FOR_AVAILABLE_SESSION_TYPES', # diag session ctrl
                     'READ_ALL_DATA', 'READ_VIN', 'READ_ECU_HW', 'READ_SUPPLIER_ECU_HW', 'READ_ECU_HW_VERSION', # read data by id
                     'READ_SUPPLIER_ECU_SW', 'READ_ECU_SW_VERSION', 'READ_CUSTOM_ID', 'READ_SCAN_FOR_SUPPORTED_IDS',
                     'SA_USE_KNOWN_ALGO', 'SA_MANUAL_AUTH', # sec access
                     'ECU_RESET_HARD', 'ECU_RESET_IGNITION_ONOFF_RESET', 'ECU_RESET_OFF', 'ECU_RESET_CUSTOM', # ecu reset
                     'READ_MEMORY_BY_ADR', 'WRITE_MEMORY_BY_ADR', 'FAST_SCAN_FOR_READABLE_OFFSETS' # memory menu
                     ]

    def __init__(self, mainwindow, nodehandler):
        super(UDSHandler, self).__init__()
        self.mainwindow = mainwindow
        self.nodehandler = nodehandler
        self.printAscii = False
        self.selected_node = None
        self.state = UdsHandlerStatus.DISCONNECTED
        self.uds_parser = UdsResponseParser()


    def connect_signals(self):
        self.mainwindow.mainInitDone.connect(self.setup_gui)
        self.mainwindow.selectedNodeChanged.connect(self.onSelectedNodeChanged)

    def writeUdsLogMsg(self, msg):
        self.mainwindow.udsLogPlainTextEdit.appendPlainText(msg)

    @Slot()
    def setup_gui(self):
        self.mainwindow.udsActionsComboBox.addItem("Diag Session Control")
        self.mainwindow.udsActionsComboBox.addItem("Read Data by ID")  #  <- somewhat important
        self.mainwindow.udsActionsComboBox.addItem("Security Access")
        self.mainwindow.udsActionsComboBox.addItem("ECU Reset")
        self.mainwindow.udsActionsComboBox.addItem("Read Memory By Address")
        self.mainwindow.udsActionsComboBox.addItem("Write Memory By Address")
        self.mainwindow.udsActionsComboBox.addItem("Terminate Session")
        self.mainwindow.udsActionsComboBox.addItem("UDS Channel Setup Scan")  # <- important
        self.mainwindow.udsActionsComboBox.currentIndexChanged.connect(self.onActionsComboBoxChange)

    def setEnableGui(self, enable):
        self.mainwindow.newUDSSessionBtn.setEnabled(enable)
        self.mainwindow.udsOwnIdLineEdit.setEnabled(enable)
        self.mainwindow.udsTargetIdLineEdit.setEnabled(enable)
        self.mainwindow.udsActionsComboBox.setEnabled(enable)
        self.mainwindow.udsLogPlainTextEdit.setEnabled(enable)
        self.onActionsComboBoxChange(0)

    @Slot(object, object)
    def onSelectedNodeChanged(self, prev_node, new_node):
        if new_node["version"] != "2":
            return

        self.setEnableGui(True)
        self.selected_node = new_node["connection"]


    @Slot(int)
    def onActionsComboBoxChange(self, index):
        # clear ui items first
        for i in reversed(range(self.mainwindow.udsActionContentsLayout.count())):
            self.mainwindow.udsActionContentsLayout.itemAt(i).widget().deleteLater()

        if index == 0:  # diag session control
            self.sessionTypesComboBox = QComboBox(self.mainwindow)
            self.sessionTypeLineEdit = QLineEdit(self.mainwindow)
            self.mainwindow.udsActionContentsLayout.addWidget(QLabel("Switch to Session:"))
            self.sessionTypeLineEdit.setPlaceholderText("Session Level (hex)")
            self.sessionTypesComboBox.addItems(["Default", "Programming", "Extended", "Custom"])
            self.mainwindow.udsActionContentsLayout.addWidget(self.sessionTypesComboBox)
            self.mainwindow.udsActionContentsLayout.addWidget(self.sessionTypeLineEdit)
        elif index == 1:  # read data by id
            self.rdbidLineEdit = QLineEdit(self.mainwindow)
            self.rdbidLineEdit.setPlaceholderText("Data ID (hex)")
            self.readDataBtn = QPushButton("Read")
            self.readDataBtn.clicked.connect(self.onReadDataById)
            self.mainwindow.udsActionContentsLayout.addWidget(self.rdbidLineEdit)
            self.mainwindow.udsActionContentsLayout.addWidget(self.readDataBtn)
        elif index == 4:  # read mem by address
            self.readMemoryBtn = QPushButton("Run")
            self.memoryAddressLineEdit = QLineEdit(self.mainwindow)
            self.memoryAddressLineEdit.setPlaceholderText("Address to Read (hex)")
            self.memoryLengthLineEdit = QLineEdit(self.mainwindow)
            self.memoryLengthLineEdit.setPlaceholderText("Size (hex)")

            gracefullyDisconnectSignal(self.readMemoryBtn.clicked)
            self.readMemoryBtn.clicked.connect(self.onReadMemByAddress)
            self.mainwindow.udsActionContentsLayout.addWidget(self.memoryAddressLineEdit)
            self.mainwindow.udsActionContentsLayout.addWidget(self.memoryLengthLineEdit)
            self.mainwindow.udsActionContentsLayout.addWidget(self.readMemoryBtn)


    @Slot()
    def onEstablishNewSession(self):
        self.selected_node = self.mainwindow.selectedNode['connection']
        own_id = int(str(self.mainwindow.udsOwnIdLineEdit.text()), 16)
        target_id = int(str(self.mainwindow.udsTargetIdLineEdit.text()), 16)
        session_level = UdsDiagnosticSessionType.DEFAULT
        if len(self.sessionTypeLineEdit.text()) > 0:
            session_level = int(self.sessionTypeLineEdit.text(), 16)
        else:
            # get value from dropdown
            session_level = self.sessionTypesComboBox.currentIndex() + 1
        #self.selected_node.ackReceived.disconnect()
        #self.selected_node.nackReceived.disconnect()
        self.mainwindow.newUDSSessionBtn.clicked.disconnect()

        #self.mainwindow.selectedNode["connection"].ackReceived.connect(self.onSuccessfullyEstablishedSession)
        #self.mainwindow.selectedNode["connection"].nackReceived.connect(self.onErrorEstablishingSession)
        gracefullyDisconnectSignal(self.selected_node.newDataMessage)
        self.selected_node.newDataMessage.connect(self.onData)

        self.mainwindow.newUDSSessionBtn.setText("Cancel")
        self.mainwindow.newUDSSessionBtn.clicked.connect(self.onCancelEstablishingSession)
        self.writeUdsLogMsg(f"Trying to establish new UDS session with tester id {hex(own_id)} and target id {hex(target_id)}, level {hex(session_level)}..")

        req = StartUdsMessage(CanbadgerInterface.INTERFACE_1, local_id=own_id, remote_id=target_id, can_format=CANFormat.STANDARD_FORMAT,
                              enable_padding=True, padding_byte=0x00, addressing_type=AddressingType.STANDARD_ADDRESSING, target_diag_session=session_level)
        self.selected_node.sendEthernetMessage(req)
        self.state = UdsHandlerStatus.CONNECTING

    @Slot()
    def onCancelEstablishingSession(self):
        self.selected_node.stopCurrentAction()
        self.onErrorEstablishingSession()

    @Slot()
    def onSuccessfullyEstablishedSession(self):
        self.state = UdsHandlerStatus.CONNECTED
        self.mainwindow.newUDSSessionBtn.clicked.disconnect()
        self.mainwindow.newUDSSessionBtn.clicked.connect(self.onCloseCurrentSession)
        self.mainwindow.newUDSSessionBtn.setText("Close Session")
        self.mainwindow.udsActionsComboBox.setEnabled(True)
        self.onActionsComboBoxChange(0)


    @Slot()
    def onErrorEstablishingSession(self):
        self.state = UdsHandlerStatus.DISCONNECTED
        self.writeUdsLogMsg("Error establishing session!")
        self.mainwindow.newUDSSessionBtn.clicked.disconnect()
        self.mainwindow.newUDSSessionBtn.clicked.connect(self.onEstablishNewSession)
        self.mainwindow.newUDSSessionBtn.setText("New Session")
        self.mainwindow.udsActionsComboBox.setEnabled(False)

    @Slot(dict)
    def onTakeOverSession(self, session):
        pass

    @Slot()
    def onCloseCurrentSession(self):
        # do stuff ..
        self.mainwindow.newUDSSessionBtn.clicked.disconnect()
        self.mainwindow.newUDSSessionBtn.clicked.connect(self.onEstablishNewSession)
        self.mainwindow.newUDSSessionBtn.setText("New Session")
        self.mainwindow.udsActionsComboBox.setEnabled(False)
        self.selected_node.stopCurrentAction()

    @Slot()
    def onReadDataById(self):
        id = int(self.rdbidLineEdit.text(), 16)
        payload = b''
        if id < 0x100:
            payload = struct.pack('>B', id)
        if id > 0xFF:
            payload = struct.pack('>H', id)

        gracefullyDisconnectSignal(self.selected_node.newDataMessage)
        self.selected_node.newDataMessage.connect(self.onData)
        self.selected_node.sendEthernetMessage(UdsRequest(UdsServiceIdentifier.READ_DATA_BY_ID, payload))


    @Slot()
    def onReadMemByAddress(self):
        self.printAscii = False
        gracefullyDisconnectSignal(self.selected_node.newDataMessage)
        self.mainwindow.selectedNode["connection"].newDataMessage.connect(self.onData)
        address = int(self.memoryAddressLineEdit.text(), 16)
        length = int(self.memoryLengthLineEdit.text(), 16)
        memReq = ReadMemoryByAddress.build_request(address, length)
        req = UdsRequest(UdsServiceIdentifier.READ_MEMORY_BY_ADDRESS, memReq)
        self.selected_node.sendEthernetMessage(req)


    @Slot(object)
    def onData(self, data):
        if self.state == UdsHandlerStatus.CONNECTING:
            # parse uds response with sid 0x10
            uds = UdsResponse(data)
            if uds.is_positive_reply:
                self.writeUdsLogMsg(f"DiagSession established with level {uds.payload[1]}")
                self.onSuccessfullyEstablishedSession()
            else:
                neg_resp = UdsResponseParser.parseNegativeResponse(uds.payload)
                self.writeUdsLogMsg(f"DiagSessionControl Request failed: Code {hex(neg_resp['code'])}, Reason: {neg_resp['reason']}")
                self.onErrorEstablishingSession()

        if self.state == UdsHandlerStatus.CONNECTED or self.state == UdsHandlerStatus.BUSY:
            # check current action
            if self.mainwindow.udsActionsComboBox.currentIndex() == 1:
                # read data by id
                uds = UdsResponse(data)
                if uds.is_positive_reply:
                    self.writeUdsLogMsg(f"ReadDataById succeeded!")
                    self.writeUdsLogMsg(uds.payload.hex())
                else:
                    neg_resp = UdsResponseParser.parseNegativeResponse(uds.payload)
                    self.writeUdsLogMsg(
                        f"ReadDataById Request failed: Code {hex(neg_resp['code'])}, Reason: {neg_resp['reason']}"
                    )
            if self.mainwindow.udsActionsComboBox.currentIndex() == 4:
                # read mem by address
                # parse uds response with sid 0x10
                uds = UdsResponse(data)
                if uds.is_positive_reply:
                    self.writeUdsLogMsg(f"ReadMemByAddress succeeded!")
                    self.writeUdsLogMsg(uds.payload.hex())
                else:
                    neg_resp = UdsResponseParser.parseNegativeResponse(uds.payload)
                    self.writeUdsLogMsg(
                        f"ReadMemByAddress Request failed: Code {hex(neg_resp['code'])}, Reason: {neg_resp['reason']}"
                    )

        #if self.printAscii:
        #    self.mainwindow.udsLogPlainTextEdit.appendPlainText(str(data))
        #else:
        #    self.mainwindow.udsLogPlainTextEdit.appendPlainText(str(QByteArray.fromRawData(data).toHex()))