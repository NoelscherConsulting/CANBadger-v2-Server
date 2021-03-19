#####################################################################################
# CanBadger SocketCanSource                                                         #
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

from multiprocessing import Process
from socket import *
import queue
import struct
import select
import time
import math


# process to receive traffic from a socketcan connection
class SocketCanSource(Process):
    def __init__(self, bound_socket, command_queue=None, message_queue=None):
        super().__init__()

        # socket should be bound and closed by calling class
        self.socket = bound_socket

        self.active = True
        self.started = None

        # queues for buffering output frames, and commands to send
        self.message_queue = message_queue
        self.command_queue = command_queue

    def run(self):
        inputs = [self.socket]
        outputs = [self.socket]

        self.started = time.time()

        # socket can standard format, 4byte id, 1byte data length, 3byte padding, up to 8 byte data
        fmt = '<IB3x8s'

        while self.active:

            # check network connections
            readable, writeable, errors = select.select(inputs, outputs, [], 1)

            for r in readable:
                message = r.recv(16)
                if message:
                    can_id, length, data = struct.unpack(fmt, message)
                    can_id &= CAN_EFF_MASK
                    data = data[:length]
                    timestamp = math.floor((time.time() - self.started) * 1000)  # gives ms timestamp
                    self.message_queue.put((can_id, timestamp, length, data))

            for e in errors:
                if e in inputs:
                    inputs.remove(e)
                if e in outputs:
                    outputs.remove(e)
                print("Something went terribly wrong!")

            while True:
                try:
                    command = self.command_queue.get_nowait()
                    if command == "kys":
                        self.active = False
                except queue.Empty:
                    break

