#####################################################################################
# CanBadger Timing Script                                                           #
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

from socket import *
from canbadger_messages import EthernetMessage, EthernetMessageType, ActionType
import struct
import sys
import time
import matplotlib.pyplot as plt
import statistics


class BroadcastDeafSocket(socket):
    def __init__(self, family, type):
        super().__init__(family, type)
        self.cant_hear = 'CB|'.encode('ascii')

    def recvfrom(self, bufsize: int):
        while True:
            resp, add = super().recvfrom(bufsize)

            if resp[0:3] != self.cant_hear:
                return resp, add

    def recv(self, bufsize: int) -> bytes:
        while True:
            resp = super().recv(bufsize)
            if resp[0:3] != self.cant_hear:
                return resp


def print_formatted_log(data, count):
    print('\n' + f'Log Message {count}' + '\n' + '---------------')
    if data[0] == 0x15:
        print('Interface : 1\n')
    elif data[0] == 0x16:
        print('Interface : 2\n')
    else:
        print('Interface ERROR!\n')

def print_statistics(values, name, ns = None, bins = None):
    print(f"\n{name} stats:\n-----------------------")

    # print median and mean
    mean = statistics.mean(values)
    print(f"Median: {statistics.median(values)}")
    print(f"Mean: {mean}")

    # biggest buckets
    if ns is not None and bins is not None:
        biggest = [i for i, j in enumerate(ns) if j == max(ns)]
        print(f"\nBiggest bucket(s) for {name} (measured {len(values)} times):")
        for i in biggest:
            print(f"{ns[i]:.0f} in {bins[i]:.3f}-{bins[i+1]:.3f}")

    # outliers
    if ns is not None and bins is not None:
        bucket_indices = [i for i, j in enumerate(ns) if j > 0]
        leftmost = bucket_indices[0]
        rightmost = bucket_indices[-1]
        print(f"Outliers: {ns[leftmost]:.0f}  in {bins[leftmost]:.3f}-{bins[leftmost+1]:.3f} "
              f"(> {(mean - bins[leftmost+1]):.3f} from mean) || "
              f"{ns[rightmost]:.0f} in {bins[rightmost]:.3f}-{bins[rightmost+1]:.3f} "
              f"(> {(bins[rightmost] - mean):.3f} from mean)")


# script vars
canbadger_ip = '10.0.0.125'

# bind udp socket to 13370 for connection request
conn_sock = socket(AF_INET, SOCK_DGRAM)
conn_sock.bind(('', 13370))

# extra socket to send commands and receive data
comm_sock = socket(AF_INET, SOCK_DGRAM)
comm_sock.bind(('', 13372))

# connection request and answer
conn_sock.sendto(EthernetMessage(EthernetMessageType.CONNECT, ActionType.NO_TYPE, 4, struct.pack('<I', 13372)).serialize(), (canbadger_ip, 13371))
answer, address = comm_sock.recvfrom(1024)
answer = EthernetMessage.unserialize(answer)
if answer.msg_type != EthernetMessageType.ACK:
    print('Connection not accepted!')
    sys.exit(1)
print('Connected!')
time.sleep(0.5)

# get the settings
print("Timing settings requests!")
count = 0
settings_timing = []
while count < 100:
    count += 1
    comm_sock.sendto(EthernetMessage(EthernetMessageType.ACTION, ActionType.SETTINGS, 0, b'').serialize(), address)
    settings_requested = time.perf_counter()
    settings = EthernetMessage.unserialize(comm_sock.recv(1024), True).data
    settings_received = time.perf_counter()
    settings_timing.append(round(settings_received - settings_requested, 5) * 1000)
    time.sleep(0.2)


# send logging command
comm_sock.sendto(EthernetMessage(EthernetMessageType.ACTION, ActionType.LOG_RAW_CAN_TRAFFIC, 0, b'').serialize(), address)
time.sleep(0.3)

# build replay message
hex_id = 0x111
hex_payload = bytes.fromhex('aabbccdd')

interface = struct.pack('B',1)
id = struct.pack('I', hex_id)
payload = struct.pack("%ds" % len(hex_payload), hex_payload)

replay_message = interface + id + payload
replay_command = EthernetMessage(EthernetMessageType.ACTION, ActionType.START_REPLAY, len(replay_message), replay_message).serialize()

# tracking vars
count = 0
command_sent = []
replay_frame_time = []
received_frame_time = []

# send replays and track timing
while count < 500:

    comm_sock.sendto(replay_command, address)
    command_sent.append(time.perf_counter())

    answer = EthernetMessage.unserialize(comm_sock.recv(1024), True)
    replay_frame_time.append(time.perf_counter())
    count += 1
    print_formatted_log(answer.data, count)

    answer = EthernetMessage.unserialize(comm_sock.recv(1024), True)
    received_frame_time.append(time.perf_counter())
    count += 1
    print_formatted_log(answer.data, count)

    time.sleep(0.1)

# send STOP to cb
comm_sock.sendto(EthernetMessage(EthernetMessageType.ACTION, ActionType.STOP_CURRENT_ACTION, 0, b'').serialize(), address)


# calculate delays
command_delays = []
for i, x in enumerate(command_sent):
    command_delays.append(round(replay_frame_time[i] - x, 5) * 1000)

receive_delays = []
for i, x in enumerate(replay_frame_time):
    receive_delays.append(round(received_frame_time[i] - x, 5) * 1000)

plt.subplot(131)
n, bins, patches = plt.hist(settings_timing, bins=40)
plt.title('Delay settings')
print_statistics(settings_timing, "settings", ns=n, bins=bins)
plt.subplot(132)
n, bins, patches = plt.hist(receive_delays, bins=40)
plt.title('Delay interfaces')
print_statistics(receive_delays, "interface", ns=n, bins=bins)
plt.subplot(133)
n, bins, patches = plt.hist(command_delays, bins=40)
plt.title('Delay replay')
print_statistics(command_delays, "command", ns=n, bins=bins)
plt.show()

sys.exit(0)


