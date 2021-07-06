#####################################################################################
# CanBadger CanbadgerSource                                                         #
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

from multiprocessing import Process, Queue
from socket import *
import queue
import struct
import select
import random
import time
from enum import Enum
from libcanbadger import EthernetMessage, EthernetMessageType, ActionType


class ConnectionStatus(Enum):
    Unconnected = 0
    Connected = 1
    Logging = 2
    Stopping = 3


# Process to receive incoming messages from the CanBadger
class CanbadgerSource(Process):
    def __init__(self, ip, port=13371, command_queue: Queue = None,
                 signal_queue: Queue = None, message_queue: Queue = None):
        super().__init__()
        self.ip = ip
        self.port = port
        self.status = ConnectionStatus.Unconnected
        self.data_ready = False
        self.active = True

        # queues for buffering output frames, and commands to send
        self.signal_queue = signal_queue
        self.message_queue = message_queue
        self.command_queue = command_queue

    def run(self):
        print("logger running!")

        # dataSocket for listening to cb data, actionSocket to send commands
        data_socket = socket(AF_INET, SOCK_DGRAM)
        action_socket = socket(AF_INET, SOCK_DGRAM)

        data_port = random.randint(10000, 13370)
        data_socket.bind(('', data_port))

        # dict that holds  local queues for outputs and inputs
        buffer_queues = dict()
        buffer_queues[data_socket] = Queue()
        buffer_queues[action_socket] = Queue()

        inputs = [data_socket]
        outputs = [action_socket]

        # put the connection setup message into the action sockets queue
        buffer_queues[action_socket].put(b'\x04' + b'\x00' + struct.pack('<I', 4) +
                                         struct.pack('<I', data_port) + b'\x00')

        while self.active:

            # loop uses select to check for network activity and then checks the command queue for inputs
            # we cant use queues with select on windows, so we have to check separately

            # check network connections
            readable, writeable, errors = select.select(inputs, outputs, [], 1)

            for r in readable:
                message = r.recv(1024)
                if message:
                    buffer_queues[r].put(message)

            for w in writeable:
                try:
                    message = buffer_queues[w].get_nowait()
                except queue.Empty:
                    pass
                else:
                    if type(message) == EthernetMessage:
                        if self.status == ConnectionStatus.Stopping \
                                and message.getActionType() == ActionType.STOP_CURRENT_ACTION:
                            self.active = False
                        message = message.serialize()

                    action_socket.sendto(message, (self.ip, self.port))

            for e in errors:
                if e in inputs:
                    inputs.remove(e)
                if e in outputs:
                    outputs.remove(e)
                del buffer_queues[e]
                print("Something went terribly wrong!")

            # handle incoming data
            for input in inputs:
                while True:
                    try:
                        message = buffer_queues[input].get_nowait()

                        eth_msg = EthernetMessage.unserialize(message, unpack_data=True)
                        msg_type = eth_msg.getMsgType()

                        # if we receive an ACK while unconnected we are now connected
                        if self.status == ConnectionStatus.Unconnected and msg_type == EthernetMessageType.ACK:
                            self.status = ConnectionStatus.Connected

                        # while logging output data frames to queue
                        if self.status == ConnectionStatus.Logging and msg_type == EthernetMessageType.DATA:
                            self.message_queue.put(eth_msg)

                    except queue.Empty:
                        break

            # if we are connected, send the logging request
            if self.status == ConnectionStatus.Connected:
                start_logging_message = EthernetMessage(EthernetMessageType.ACTION, ActionType.LOG_RAW_CAN_TRAFFIC, 1,
                                                        struct.pack('<?', False))

                buffer_queues[action_socket].put(start_logging_message)
                self.status = ConnectionStatus.Logging

            while True:
                try:
                    command = self.command_queue.get_nowait()
                    if command == "kys":
                        self.status = ConnectionStatus.Stopping
                        stop_message = EthernetMessage(EthernetMessageType.ACTION, ActionType.STOP_CURRENT_ACTION, 0,
                                                       b'')
                        buffer_queues[action_socket].put(stop_message)

                except queue.Empty:
                    break

        time.sleep(0.001)

        # close sockets
        data_socket.close()
        action_socket.close()


if __name__ == "__main__":
    ip = "192.168.198.1"

    cq = Queue()
    sq = Queue()
    mq = Queue()

    p = CanbadgerSource(ip, command_queue=cq, signal_queue=sq, message_queue=mq)
    print("starting cbs")
    p.start()

    count = 0
    while count < 300:
        try:
            emsg = mq.get_nowait()
            print("Main thread got {}".format(emsg.data))
            count += 1
        except queue.Empty:
            pass
    cq.put("kys")
    p.join()
    print("test done!")
