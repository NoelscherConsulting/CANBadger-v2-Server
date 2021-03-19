#####################################################################################
# CanBadger SD Handler                                                              #
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
from PySide2.QtWidgets import QFileDialog, QListWidgetItem, QAbstractItemView

from canbadger_messages.ethernet_message import EthernetMessage, EthernetMessageType, ActionType
from helpers import *
from models import SD_FS_Model
import struct


class SdHandler(QObject):

    upload_result = Signal(bool)

    def __init__(self, mainwindow, nodehandler):
        super(SdHandler, self).__init__()
        self.mainwindow = mainwindow
        self.nodehandler = nodehandler
        self.fileBrowser = mainwindow.sdCardTreeView  # the view displaying files and directories
        self.fileModel = SD_FS_Model(self.fileBrowser)  # the model holding directories and files
        self.fileBrowser.setModel(self.fileModel)
        self.fileBrowser.setSelectionMode(QAbstractItemView.SingleSelection)
        self.fileBrowser.setPathLineEdit(self.mainwindow.sdCardFolderLineEdit)
        self.fileBrowser.setHandler(self)
        self.transmissionData = None  # buffer to store data during download or upload
        self.busy = False  # precaution flag to ensure no commands are sent to the CB while its executing another
        self.packet_number = 0  # keeps track of numbering the packets when uploading
        self.stillDownloading = False  # flag to signal the handler is in the middle of a download
        self.monitored_filepath = None  # keeps track of the filepath and name when uploading or deleting,
                                        # so the browser can be updated on ACK

    def connect_signals(self):
        self.mainwindow.refreshSdCardBtn.clicked.connect(self.onUpdateSd)
        self.mainwindow.downloadFileBtn.clicked.connect(self.onDownloadFile)
        self.mainwindow.deleteFileBtn.clicked.connect(self.onDeleteFile)
        self.mainwindow.uploadFileBtn.clicked.connect(self.onUploadButton)
        self.mainwindow.sdCardFolderLineEdit.textEdited.connect(self.onPathEdit)

    # START ACTIONS

    # send the command to transfer sd contents to the canbadger
    @Slot()
    def onUpdateSd(self, caller=None):
        if not self.check_preconditions():
            return

        # only update the model on button press and not tab change if we already have the data
        if self.fileModel.is_filled() and caller == "tab":
            return

        # create a new model to holt the new data
        self.fileModel = SD_FS_Model(self.fileBrowser)
        self.fileBrowser.setModel(self.fileModel)
        self.fileBrowser.selectionModel().currentChanged.connect(self.onSelectionChange)

        # disconnect buttons
        gracefullyDisconnectSignal(self.mainwindow.downloadFileBtn.clicked)
        gracefullyDisconnectSignal(self.mainwindow.refreshSdCardBtn.clicked)

        connection = self.mainwindow.selectedNode["connection"]
        gracefullyDisconnectSignal(connection.newDataMessage)

        self.busy = True
        connection.newDataMessage.connect(self.onGotUpdateResponse)
        connection.sendMessage(EthernetMessage(EthernetMessageType.ACTION, ActionType.UPDATE_SD, 0, None))

    # send the filepath we want downloaded to the canbadger
    @Slot()
    def onDownloadFile(self):
        if not self.check_preconditions(command="download"):
            return

        # get the connection and check which file to download
        connection = self.mainwindow.selectedNode["connection"]
        item = self.fileBrowser.selectedIndexes()[0].internalPointer()
        if item.dir:
            return

        self.transmissionData = bytes()
        self.stillDownloading = True

        # switch signals
        gracefullyDisconnectSignal(connection.newDataMessage)
        gracefullyDisconnectSignal(connection.ackReceived)
        gracefullyDisconnectSignal(connection.nackReceived)
        connection.newDataMessage.connect(self.onNewDownloadData)
        connection.ackReceived.connect(self.onDownloadAck)
        connection.nackReceived.connect(self.onDownloadError)

        # show state on button
        self.mainwindow.downloadFileBtn.setText("Downloading")

        # set self busy and send command to canbadger
        self.busy = True
        filepath = (item.get_filepath() + '\0').encode('ascii')  # get null terminated filepath
        connection.sendMessage(EthernetMessage(EthernetMessageType.ACTION, ActionType.DOWNLOAD_FILE,
                                               len(filepath), filepath))

    # send the filepath we want deleted to the canbadger
    @Slot()
    def onDeleteFile(self):
        if not self.check_preconditions(command="delete"):
            return

        # get connection and item we want to delete
        connection = self.mainwindow.selectedNode["connection"]
        item = self.fileBrowser.selectedIndexes()[0].internalPointer()
        if item.dir:
            return

        # switch signals
        gracefullyDisconnectSignal(connection.ackReceived)
        gracefullyDisconnectSignal(connection.nackReceived)
        connection.ackReceived.connect(self.onDeleteAck)
        connection.nackReceived.connect(self.onDeleteError)

        # set self busy and send command to canbadger
        self.busy = True
        filepath = (item.get_filepath() + '\0').encode('ascii')  # get null terminated filepath
        self.monitored_filepath = item.get_filepath()
        connection.sendMessage(EthernetMessage(EthernetMessageType.ACTION, ActionType.DELETE_FILE,
                                               len(filepath), filepath))

    @Slot(str)
    def onUploadFile(self, filename: str, local_filename=None, sd_path=None):
        #######################################################################################################
        # when sd_path is None, the current selection in the SD handler file browser will determine     #
        #                             the file path on the canbadger SD                                       #
        # setting sd_path (e.g. with '/MITM') will move the uploaded file to that path on the SD        #
        #                                                                                                     #
        # local_filename will be used if the filename on the GUI machine and the desired filename on the      #
        #                             canbadger differ, the function will send the file from local_filename  #
        #                             to the canbadger and call it filename                                   #
        #######################################################################################################

        if not self.check_preconditions(command="upload"):
            return

        # get connection and check if an item is selected
        connection = self.mainwindow.selectedNode["connection"]
        filepath = b''
        # if the sd_path is none we need to check the views selection
        if sd_path is None:
            item = None
            if self.fileBrowser.selectedIndexes():
                item = self.fileBrowser.selectedIndexes()[0].internalPointer()
                if not item.dir:
                    # if a file is selected, upload to parent folder
                    item = item.parent()
            # get the filepath for the selected folder
            if item is not None:
                filepath = (item.get_filepath()).encode('ascii')

        else:  # if we have an sd path instead we use it
            filepath += sd_path.encode('ascii')

        filepath += b'/' + filename.encode('ascii') + b'\0'

        # save filepath and name for browser update on success
        self.monitored_filepath = (filepath, filename)

        # get the files content
        if not local_filename:
            local_filename = filename
        try:
            with open(local_filename, 'r') as file:
                self.transmissionData = file.read().encode('ascii')
        except EnvironmentError:
            self.onUploadError()
            return

        # set current packet number to 0
        self.packet_number = 0

        # switch signals
        gracefullyDisconnectSignal(connection.ackReceived)
        gracefullyDisconnectSignal(connection.nackReceived)
        connection.ackReceived.connect(self.onUploadAck)
        connection.nackReceived.connect(self.onUploadError)

        self.busy = True
        connection.sendMessage(EthernetMessage(EthernetMessageType.ACTION, ActionType.UPDATE_SD,
                                               len(filepath), filepath))

    @Slot()
    def onUploadButton(self):
        filename = QFileDialog.getOpenFileName(self.mainwindow, 'Select file for upload', '.')
        if filename is None or filename[0] == '':
            return

        # prepare path and name for upload function
        local_path = filename[0]
        name = local_path[local_path.rfind('/') + 1:]

        # connect upload result to feedback function
        self.upload_result.connect(self.displayUploadResult)

        # initialize upload of selected file, with fileBrowser selection determining sd filepath
        self.onUploadFile(name, local_filename=local_path)

    def sendSettingsFilename(self, name):
        connection = self.mainwindow.selectedNode["connection"]
        if connection is None:
            return
        connection.sendMessage(EthernetMessage(EthernetMessageType.ACTION, ActionType.EEPROM_WRITE, len(name),
                                               name.encode('ascii')))

    # HANDLE GUI

    # keep the path LineEdit updated with the current selection
    @Slot(QModelIndex, QModelIndex)
    def onSelectionChange(self, index, old):
        selected = index.internalPointer()
        if selected is not None:
            self.mainwindow.sdCardFolderLineEdit.setText(selected.get_filepath())

    # update the selection on path edit
    @Slot()
    def onPathEdit(self):
        path = self.mainwindow.sdCardFolderLineEdit.text()

        index = self.fileModel.index_for_path(path)

        # if we get None, current path is invalid and we dont change selection
        if index is None:
            return

        # if path is root we deselect
        if not index.isValid():
            self.fileBrowser.selectionModel().clear()
            return

        # if we get a valid index, select it
        self.fileBrowser.selectionModel().select(index, QItemSelectionModel.ClearAndSelect)




    # HANDLE RESPONSES

    # handle sd contents update
    @Slot(object)
    def onGotUpdateResponse(self, data):
        connection = self.mainwindow.selectedNode["connection"]
        delim = data.index(b'\x00')

        if delim == 0:
            # no more sd content incoming
            gracefullyDisconnectSignal(connection.newDataMessage)

            # reconnect buttons
            self.mainwindow.downloadFileBtn.clicked.connect(self.onDownloadFile)
            self.mainwindow.refreshSdCardBtn.clicked.connect(self.onUpdateSd)
            self.busy = False

            self.fileBrowser.resizeColumnToContents(0)
            return

        parent_dir = data[:delim].decode('ascii')

        # get the index to the parent dir
        add_index = self.fileModel.index_for_path(parent_dir)

        data = data[delim + 1:]

        while True:
            try:
                delim = data.index(b'\x00')
                if data[0] == 15:
                    content_type = "File"
                elif data[0] == 240:
                    content_type = "Dir"
                else:
                    raise Exception

                name = data[1:delim].decode('ascii')
                self.fileModel.add_item(add_index, name, True if content_type == "Dir" else False)
                data = data[delim + 1:]
            except ValueError:
                break

    # append new download data
    @Slot(object)
    def onNewDownloadData(self, data):
        if self.stillDownloading:
            self.transmissionData += data[6:]

    # ack while downloading means transmission is done
    @Slot()
    def onDownloadAck(self):
        # download finishedFalse
        self.stillDownloading = False
        self.busy = False

        # disconnect signals used for download
        connection = self.mainwindow.selectedNode["connection"]
        gracefullyDisconnectSignal(connection.newDataMessage)
        gracefullyDisconnectSignal(connection.ackReceived)
        gracefullyDisconnectSignal(connection.nackReceived)

        # display file chooser and save file
        self.mainwindow.downloadFileBtn.setText("Download File")
        filename = QFileDialog.getSaveFileName(self.mainwindow, 'Save file', '.', "Any files")[0]
        if len(filename) < 1:
            return
        outfile = open(filename, 'wb')
        outfile.write(self.transmissionData)
        outfile.flush()
        outfile.close()

    # nack while downloading signals an error
    @Slot()
    def onDownloadError(self):
        self.stillDownloading = False
        self.busy = False
        # disconnect signals used for download
        connection = self.mainwindow.selectedNode["connection"]
        gracefullyDisconnectSignal(connection.newDataMessage)
        gracefullyDisconnectSignal(connection.ackReceived)
        gracefullyDisconnectSignal(connection.nackReceived)
        self.mainwindow.downloadFileBtn.setText("Download File")

    # deletion successful
    @Slot()
    def onDeleteAck(self):
        # disconnect signals used for download
        connection = self.mainwindow.selectedNode["connection"]
        gracefullyDisconnectSignal(connection.ackReceived)
        gracefullyDisconnectSignal(connection.nackReceived)

        # model change (kept track of filepath in monitored_filepath)
        to_delete_index = self.fileModel.index_for_path(self.monitored_filepath)
        self.monitored_filepath = None
        self.fileModel.remove_item(to_delete_index)
        self.busy = False

    # problem with deletion
    @Slot()
    def onDeleteError(self):
        # disconnect signals used for download
        connection = self.mainwindow.selectedNode["connection"]
        gracefullyDisconnectSignal(connection.ackReceived)
        gracefullyDisconnectSignal(connection.nackReceived)
        self.busy = False

        # something must have gone wrong, load the contents new to ensure consistency
        self.mainwindow.downloadFileBtn.click()

    # receiving an ACK while uploading
    @Slot()
    def onUploadAck(self):
        connection = self.mainwindow.selectedNode["connection"]

        # check if we have data left to send
        if not self.transmissionData:
            # no data left to send, send STOP_CURRENT_ACTION, canbadger will close file handle
            connection.sendMessage(EthernetMessage(EthernetMessageType.ACTION, ActionType.STOP_CURRENT_ACTION, 0, b''))
            self.busy = False

            # signal success and disconnect signals
            self.upload_result.emit(True)
            gracefullyDisconnectSignal(connection.ackReceived)
            gracefullyDisconnectSignal(connection.nackReceived)

            # update fileBrowser with uploaded entry

            path, name = self.monitored_filepath
            self.monitored_filepath = None
            path = path[:-1].decode('ascii')

            # remove trailing filename
            path = path[:path.rfind('/')]
            if path == "":
                path = "/"

            dir_index = self.fileModel.index_for_path(path)
            self.fileModel.add_item(dir_index, name, is_dir=False)

            return

        # get the data to be sent in the next packet
        packet_data = self.transmissionData[:120]  # canbadger receiver buffer currently 135 Bytes
        self.transmissionData = self.transmissionData[120:]
        if len(self.transmissionData) == 0:
            self.transmissionData = None

        # combine message and send
        message = struct.pack('<IB', self.packet_number, len(packet_data)) + packet_data
        self.packet_number += 1
        connection.sendMessage(EthernetMessage(EthernetMessageType.ACTION, ActionType.UPDATE_SD, len(message), message))

    # received a NACK while uploading
    def onUploadError(self):
        # upload went wrong, display error
        connection = self.mainwindow.selectedNode["connection"]
        self.busy = False
        self.transmissionData = None
        gracefullyDisconnectSignal(connection.ackReceived)
        gracefullyDisconnectSignal(connection.nackReceived)
        self.upload_result.emit(False)

    # HELPER FUNCTIONS

    # check if we can send a command or should abort, moving this code here to increase readability of command functions
    def check_preconditions(self, command=None):
        # dont send new command if another one is currently executed
        if self.busy:
            return False

        # only send commands for valid connection
        if self.mainwindow.selectedNode is None or self.mainwindow.selectedNode["version"] == "socket_can":
            return False

        # check if the logger is currently running
        if self.mainwindow.selectedNode["connection"].logger_process is not None:
            return False

        if command == "download" or command == "delete":
            # check if a filesystem item is selected
            selected_index = self.fileBrowser.selectedIndexes()[0]
            if selected_index is None or not selected_index.isValid():
                # no valid selection
                return False

        # all checks passed, we can send command to canbadger
        return True

    # VISUAL FEEDBACK

    @Slot(bool)
    def displayUploadResult(self, result):
        gracefullyDisconnectSignal(self.upload_result)
        self.buttonFeedback(result, self.mainwindow.uploadFileBtn)

    # blinks a button to signal success
    def buttonFeedback(self, result, button):
        if result:
            button.setStyleSheet("background-color: green")
        else:
            button.setStyleSheet("background-color: red")

        QTimer.singleShot(300, lambda: button.setStyleSheet(""))

