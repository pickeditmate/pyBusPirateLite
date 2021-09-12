#!/usr/bin/env python3
# encoding: utf-8
r'''
Created by Sean Nelson on 2009-10-14.
Copyright 2009 Sean Nelson <audiohacked@gmail.com>
This file is part of pyBusPirate.
pyBusPirate is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
pyBusPirate is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.
You should have received a copy of the GNU General Public License
along with pyBusPirate.  If not, see <http://www.gnu.org/licenses/>.

Updated for Python3 by Tijl "Photubias" Deneut <tijl.deneut@howest.be>
 on 2021-09-12

Quick reset of the BusPirate: 
python -c "from pyBusPirateLite.SPI import SPI; oSPI = SPI('COM5',115200);oSPI.hw_reset();"
## 'COM5' and 115200 are optional (defaults are to detect port and default rate 115200)
sudo python3 -c "from pyBusPirateLite.SPI import SPI; oSPI = SPI();oSPI.hw_reset());"
'''
from serial.serialutil import SerialException
import sys, optparse
from pyBusPirateLite.SPI import SPI

def read_list_data(iSize):
    lstData = []
    ## 0xFF is also used to erase the chip, feel free to change here
    for i in range(iSize + 1): lstData.append(0xBB)
    return lstData

def bytes_to_list(bData):
    lstData = []
    for i in range(len(bData)): lstData.append(bData[i])
    return lstData

def parse_prog_args():
    parser = optparse.OptionParser(usage='%prog [options] filename', version='%prog 1.5')
    
    parser.set_defaults(command='read')
    parser.add_option('-r', '--read', default='', help='Perform read operation to file, default == STDOUT')
    parser.add_option('-w', '--write', help='Perform write operation from file')
    parser.add_option('-e', '--erase', action='store_true', default=False, help='Erase the chip (0xff over the provided flash_size)')
    parser.add_option('-i', '--id', action='store_true', default=False, help='Print Register Status')
    parser.add_option('-s', '--size', dest='flash_size', default=16, help='Size of dump in bytes, default 16', type='int')
    parser.add_option('-d', '--device', dest='device', default='', help='The device to connect to, performs autodetect', type='string')
    parser.add_option('-v', '--verbose', action='store_true', default=False, help='Print data to stdout')
    
    (options, args) = parser.parse_args()

    if options.read == '': options.verbose = True
    return (options, args)
    
if __name__ == '__main__':
    (opt, args)  = parse_prog_args()

    sCommand = 'read'

    if not opt.read == '': 
        oFile = open(opt.read, 'wb')
        opt.read = True
    elif opt.write: 
        oFile = open(opt.write, 'rb')
        sCommand = 'write'
    elif opt.erase:
        sCommand = 'erase'
    elif opt.id: sCommand = 'id'

    try:
        spi = SPI(opt.device, 115200)
    except SerialException as ex:
        print(ex)
        sys.exit()

    print('[!] Entering bitbang mode')
    if spi.enter_bb(): print('[+] OK')
    else: sys.exit('[-] Failed')
    
    print('[!] Entering raw SPI mode')
    spi.enter()
    if spi.mode == 'spi': print('[+] OK')
    else: sys.exit('[-] Failed')

    print('[!] Configuring SPI peripherals')
    spi.pins = SPI.PIN_POWER | SPI.PIN_CS | SPI.PIN_AUX
    ## Depending on the Bus Pirate version, the limit might be 1MHz (should go from 30kHz up to 8MHz)
    print('[!] Configuring SPI speed')
    spi.speed = '1MHz'
    ## Settings confirmed to work with 25LC640A
    print('[!] Configuring SPI configuration')
    spi.config = SPI.CFG_OUT_TYPE | SPI.CFG_IDLE
    spi.cs = True
    spi.timeout(0.2)
    
    if sCommand == 'read':
        print('[!] Reading EEPROM ({} bytes)'.format(opt.flash_size))
        spi.bulk_trans(3, [0x3, 0, 0])
        for i in range((int(opt.flash_size/16))):
            bData = spi.bulk_trans(16, read_list_data(16))
            if opt.verbose: print(bData)
            if opt.read: oFile.write(bData)
        if opt.flash_size % 16 != 0:
            bData = spi.bulk_trans(int(opt.flash_size % 16), read_list_data(int(opt.flash_size % 16)))
            if opt.verbose: print(bData)
            if opt.read: oFile.write(bData)
        if opt.read: oFile.close()

    elif sCommand == 'write':
        bData = oFile.read()
        opt.flash_size = len(bData)
        sAnsw = input('[?] Are you sure to overwrite the first {} bytes of the chip? [y/N]: '.format(opt.flash_size))
        if sAnsw.lower() == 'y': 
            print('[!] Writing EEPROM ({} bytes)'.format(opt.flash_size))
            for i in range((int(opt.flash_size/16))):
                spi.bulk_trans(1, [0x6])
                spi.cs = False
                spi.cs = True
                spi.bulk_trans(3, [0x2, int(i/16), (i % 16)*16])
                spi.bulk_trans(16, bytes_to_list(bData[16*i:(16*i)+16]))
                spi.cs = False
                spi.cs = True
        else: print('[!] Ok, not doing anything')

    elif sCommand == 'erase':
        print('[!] Erasing EEPROM')
        sAnsw = input('[?] Are you sure to clear the first {} bytes of the chip? [y/N]: '.format(opt.flash_size))
        if sAnsw.lower() == 'y': 
            print('[+] Erasing now ...')
            for i in range((int(opt.flash_size/16))): 
                spi.bulk_trans(1, [0x6])
                spi.cs = False
                spi.cs = True
                iMod = i % 16
                iDiv = int(i/16)
                spi.bulk_trans(3, [0x2, iDiv, iMod*16])
                spi.bulk_trans(16, read_list_data(16))
                spi.cs = False
                spi.cs = True
        else: print('[!] Ok, not doing anything')

    elif sCommand == 'id':
        print('Reading Chip ID')
        ## Read Status Register, Instruction 0b101
        bData = spi.bulk_trans(2, [0x5, 0])
        print(bData.hex())

    spi.cs = False
    print('[!] Reset Bus Pirate to user terminal')
    try: 
        spi.hw_reset()
        print('[+] OK')
    except:
        print('[+] Failed')
        sys.exit()
