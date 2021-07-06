#####################################################################################
# CanBadger Simulator                                                               #
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


# simple dummy canbadger for testing various things

import socket
import struct
import threading
import time
import random
from libcanbadger import EthernetMessage, EthernetMessageType, ActionType


class SendBroadcastThread(threading.Thread):
    def __init__(self, cb_id, version='2'):
        threading.Thread.__init__(self)
        self._stopper = threading.Event()
        self.version = version
        self.id = cb_id

    def run(self):
        UDP_IP = '255.255.255.255'
        UDP_PORT = 13370

        sock = socket.socket(socket.AF_INET,  # Internet
                             socket.SOCK_DGRAM)  # UDP
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

        while not self._stopper.is_set():
            sock.sendto(b'CB|' + bytes(self.id, 'ascii') + b'|' + bytes(self.version, 'ascii'), (UDP_IP, UDP_PORT))
            time.sleep(1)

    def stop(self):
        self._stopper.set()


class SendRandomCanDataThread(threading.Thread):
    def __init__(self, sock, remote_host, remote_port):
        threading.Thread.__init__(self)
        self.sock = sock
        self.remote_host = remote_host
        self.remote_port = remote_port
        self.abort = False

    def run(self):
        now = time.time()
        cnt = 1
        while not self.abort:
            #rand_id = struct.pack('h', random.randint(1,0x7ff))
            rand_id = random.randint(0x7f0, 0x7ff)
            rand_pl = bytes([random.randint(0x00, 0xff) for i in range(0, random.randint(4,8))])
            pl_len = len(rand_pl)
            timestamp = int(time.time() - now)
            busno = random.randint(1, 2) + 20  # 20 for can standard + can not kline, as this byte encodes more info
            speed = 500000

            msg_data = struct.pack('>BI', busno, timestamp)
            msg_data += struct.pack('>I', rand_id)
            msg_data += struct.pack('>I', speed)
            msg_data += struct.pack('>B', pl_len)
            msg_data += rand_pl

            hex_rep = str()
            str_byte = lambda b: '0' + hex(b)[2] if len(hex(b)) < 4 else hex(b)[2:4]
            for byte in rand_pl:
                hex_rep += " " + str_byte(byte)

            print("{}: sending id {} pl {}".format(cnt, hex(rand_id), hex_rep))
            data_len = len(msg_data)
            msg = struct.pack('<bbI',
                              0x02,  # DATA
                              0x00,  # no action type
                              data_len,  # len
                              )
            msg += msg_data
            self.sock.sendto(msg, (self.remote_host, self.remote_port))
            cnt += 1
            #time.sleep(random.randint(10,10000) * 1e-6)
            time.sleep(random.randint(10,10000) * 1e-5)
        after = time.time()
        print(f"Sent {cnt} frames in {after - now} seconds!")


class UdsSession(object):
    def __init__(self, level):
        self.level = level

    def requestPositive(self, sid, data):
        if sid == 0x10:
            # diag session
            self.level = data[0]
            return b'\x50' + struct.pack('<B', data[0] & 0xff)

    def requestNegative(self, sid, data):
        #reason =
        pass


class Settings:
    def __init__(self):
        self.spi_speed = 2000000
        self.can1spd = 500000
        self.can2spd = 500000
        self.kl1spd = 12
        self.kl2spd = 11111
        self.settings_num = 0x100301

    def toggleBit(self, bit):
        if bit < 0 or bit > 29:
            return  # non valid bit
        swapper = 1 << bit
        self.settings_num ^= swapper

    def getBit(self, bit):
        if bit < 0 or bit > 29:
            return None  # non valid bit
        tester = self.settings_num >> bit
        return tester % 2 == 1


class CanbadgerSimulator:
    def __init__(self):
        self.remote_host = ""
        self.remote_port = None

    def send_ack(self, sock):
        sock.sendto(b'\x00\x00\x00\x00\x00\x00', (self.remote_host, self.remote_port))

    def send_nack(self, sock):
        sock.sendto(b'\x01\x00\x00\x00\x00\x00', (self.remote_host, self.remote_port))

    def impostor(self):
        # output for xprocess to match
        print("Canbadger Simulator is running!")

        UDP_IP = "0.0.0.0"
        UDP_PORT = 13371

        # SETTINGS -- some values that represent the canbadgers internal settings
        canbadger_id = 'cb_sim'
        settings = Settings()


        sock = socket.socket(socket.AF_INET, # Internet
                             socket.SOCK_DGRAM) # UDP
        sock.bind((UDP_IP, UDP_PORT))

        current_mode = -1

        bc_thread = SendBroadcastThread(canbadger_id)
        bc_thread.start()

        cl_thread = SendRandomCanDataThread(sock, self.remote_host, self.remote_port)
        uds_session = None

        while True:
            data, addr = sock.recvfrom(1024) # buffer size is 1024 bytes
            print("received message:", data)
            if data[0] == 0x04: # connect
                self.remote_host = addr[0]
                self.remote_port = struct.unpack('<I', data[6:10])[0]
                print("Connect received from {} with port {}".format(self.remote_host, self.remote_port))
                self.send_ack(sock)
            elif self.remote_port is None:
                print("got non-connect packet before being connected! ignoring!")
                continue
            elif data[0] == 0x03:
                # ACTION packet
                if data[1] == 0x03:
                    # start can logging
                    print('starting CAN Logger')
                    current_mode = 1
                    cl_thread = SendRandomCanDataThread(sock, self.remote_host, self.remote_port)
                    cl_thread.abort = False
                    cl_thread.start()
                if data[1] == 0x05:
                    print("GOT STOP_CURRENT_ACTION")
                    current_mode = -1
                    if cl_thread and not cl_thread.abort:
                        cl_thread.abort = True
                if data[1] == 0x13:
                    # enter replay mode
                    current_mode = 2
                    self.send_ack(sock)
                    print("entering REPLAY mode..")
                if data[1] == 2 and current_mode == 2:
                        print("sending can frame {}".format(data[6:]))
                        self.send_ack(sock)
                if data[1] == 0x05:
                    # stop current action
                    current_mode = -1
                    if not cl_thread.abort:
                        cl_thread.abort = True
                if data[1] == ActionType.START_UDS:
                    self.send_nack(sock)
                    '''
                    print("Starting UDS session..")
                    req = StartUdsMessage.unpack(data[6:])
                    uds_session = UdsSession(req.target_diag_session)

                    response = uds_session.requestPositive(0x10, struct.pack('<B', uds_session.level))
                    msg = UdsResponse.make_response(0x10, True, response)
                    sock.sendto(msg, (self.remote_host, self.remote_port))
                    '''
                if data[1] == ActionType.UDS:
                    pass
                if data[1] == ActionType.SETTINGS:
                    dataLength = struct.unpack('<I', data[2:6])[0]
                    if dataLength == 0:
                        # send current settings (DATA with ACTION SETTINGS, full length of payload and id length)
                        msg = struct.pack('<BBIB', 0x02, 0x01, 1 + len(canbadger_id) + 6*4, len(canbadger_id))
                        # add cb id, the settigns and the speeds
                        msg += bytes(canbadger_id, 'ascii')
                        msg += struct.pack('<IIIIII', settings.settings_num, settings.spi_speed,
                                           settings.can1spd, settings.can2spd, settings.kl1spd, settings.kl2spd)
                        sock.sendto(msg, (self.remote_host, self.remote_port))
                    else:
                        # handle update
                        id_length = data[6]
                        if id_length < 0 or id_length > 18:
                            return  # invalid length
                        canbadger_id = data[7:id_length + 7].decode('ascii')

                        bc_thread.stop()
                        bc_thread.join()

                        if len(data[id_length + 7:]) != 6 * 4:
                            return  # rest of the message is wrong length
                        settings.settings_num, settings.spi_speed, settings.can1spd, settings.can2spd,\
                        settings.kl1spd, settings.kl2spd = struct.unpack('<IIIIII', data[id_length + 7:])

                        bc_thread = SendBroadcastThread(canbadger_id)
                        bc_thread.start()

            else:
                print(data)
                self.send_nack(sock)

        sock.close()


if __name__ == '__main__':
    cbs = CanbadgerSimulator()
    cbs.impostor()
