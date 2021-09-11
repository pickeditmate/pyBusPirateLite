#!/usr/bin/env python3
# encoding: utf-8
r"""
Adapted from i2c-test.py from Peter Huewe

Requirements: 
Bus Pirate device with drivers: https://ftdichip.com/drivers/vcp-drivers/
 (not needed on Linux)
Python3
https://github.com/tijldeneut/pyBusPirateLite and run `setup.py install`

Quick reset of the BusPirate: 
python -c "from pyBusPirateLite.I2C import I2C; i2c = I2C('COM5',115200);i2c.hw_reset();"
## 'COM5' and 115200 are optional (defaults are to detect port and default rate 115200)
"""
import sys, argparse
from pyBusPirateLite.I2C import *

def i2c_write_data(data):
    i2c.send_start_bit()
    i2c.bulk_trans(len(data),data)
    i2c.send_stop_bit()

def i2c_read_bytes(address, numbytes, ret = False):
    lstBlock = []
    i2c.send_start_bit()
    i2c.bulk_trans(len(address),address)
    while numbytes > 0:
        bByte = i2c.read_byte()
        if ret: lstBlock.append(bByte)
        else: print(bByte)
        if numbytes > 1: i2c.ack()
        numbytes-=1
    i2c.nack()
    i2c.send_stop_bit()
    if ret: return lstBlock

if __name__ == '__main__':
    parser = argparse.ArgumentParser(sys.argv[0])
    parser.add_argument('-o', '--output', metavar='OUTFILE', type=argparse.FileType('wb'), required=True, help='Required: Output file')
    parser.add_argument('-s', '--size', type=int, required=True, help='Required: total size')
    parser.add_argument('-d', '--device', default='', help='Default is to detect the serial port')
    parser.add_argument('-S', '--serial-speed', dest='speed', default=115200, type=int, help='Default is 115200bps')
    parser.add_argument('-b', '--block-size', dest='bsize', default=256, type=int, help='Default is 256bytes')

    if len(sys.argv)<2: 
        parser.print_usage()
        sys.exit()
    args = parser.parse_args(sys.argv[1:])

    i2c = I2C(portname = args.device, speed = args.speed)
    
    print('[!] Entering bitbang mode'),
    if i2c.enter_bb(): print('[+] OK')
    else: sys.exit('[-] Failed')

    print('[!] Entering raw I2C mode')
    i2c.enter()
    if i2c.mode == 'i2c': print('[+] OK')
    else: sys.exit('[-] Failed')

    print('[!] Configuring I2C (Power, Pullup, 400kHz and timeout)')
    i2c.configure(power=True, pullup=True)
    if not i2c.check_i2c: sys.exit('[-] Failed to set I2C peripherals.')
    i2c.speed = '400kHz'
    if not i2c.speed == '400kHz': sys.exit('[-] Failed to set I2C Speed.')
    i2c.timeout(0.2)
    print('[!] Dumping {} bytes out of the EEPROM'.format(args.size))
    
    # Start dumping
    for iBlock in range(0, args.size, args.bsize):
        print('[!] Reading block {}'.format((int(iBlock / args.bsize))))
        # Reset the address with the correct block offset
        i2c_write_data([0xA0 + (int(iBlock / args.bsize) << 1), 0])
        lstData = i2c_read_bytes([0xA1 + (int(iBlock / args.bsize) << 1)], args.bsize, True)
        bData = b''.join(lstData)
        args.output.write(bData)
    if args.size % 16 != 0:
        end = 16 * int(args.size / args.bsize)
        args.output.write(b''.join([chr(x) for x in i2c_read_bytes([0xA1 + (int(args.size / args.bsize) << 1)], args.size % args.bsize, True)]))
    args.output.close()

    print('[!] Reset Bus Pirate to user terminal')
    try: 
        i2c.hw_reset()
        print('[+] OK')
    except:
        print('[+] Failed')
        sys.exit()
