# CANBadger Server v2
The CANBadgers best friend!
The CANBadger project is a vehicle security platform revolving around the CANBadger hardware.
To find out more about the hard- and firmware, please head to the firmware repository.

In this repository, you'll find the code for an application that connects to the CANBadger over Ethernet.
It can also be used to interface with any SocketCan interface on Linux systems.

# Check Out The Wiki
Visit this repositories [wiki](Wiki) to learn more!

# Run from source
Required packages: pip3, python3, pyside2
Additional packages for development: pyqt-tools, qtcreator (for editing the .ui files)
Example installation in ubuntu 20.04, assuming you have already cloned the repo:
```
# optional: create virtualenv
$ cd $repo
$ virtualenv venv
$ source venv/bin/activate
# install python dependencies
$ pip3 install -r requirements.txt
# if everything worked, you can now do:
$ python3 main.py
# .. and the CANBadger Server should come up
```

## Attributions
"entypo icons" by Daniel Bruce - CC BY-SA 4.0

Currently, the CANBadger Automotive Security Platform is maintained by [Noelscher Consulting GmbH](https://noelscher.com).
