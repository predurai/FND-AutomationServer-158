import os
import re
import sys
import csv
import time
import yaml
import json
import base64
import inspect
import pexpect
import requests
import ssl
import urllib.request
import multiprocessing
import multiprocessing.pool
import socket, struct
import paramiko, select

from ats import tcl
from ats import aetest
from ats import easypy
from ats import results
from suds.client import Client
from suds import transport
from functools import partial
from multiprocessing import Process
from datetime import date, datetime, timedelta

import logging
from ats.log.utils import banner
log = logging.getLogger(__name__)
logging.getLogger().setLevel(logging.INFO)

testbed=None
def device_reload(device_eid):
    '''
    Module to reload a device with the given eid.
    
    :param device_eid: eid of the device in testbed yaml file
    :type device_eid: str
    '''

    reboot_start_time = time.time()
    device = testbed.devices[device_eid]
    log.info('Reloading device: %s'%device)

    ''' Reloading device with ssh connection. '''
    if hasattr(device.custom, 'connection_type'):
        mgmt_ip=str(device.connections.a.ip)
        telnet_uname = device.tacacs.username
        telnet_pwd = device.passwords.line

        try:
            log.info('spawning child thread to connect to mgmt device: %s using pexpect' % mgmt_ip)
            log.info('telnet_uname: %s, telnet_pwd: %s'%(telnet_uname, telnet_pwd))
            mgmt_device = pexpect.spawn('telnet ' + mgmt_ip)
            mgmt_device.expect('.*Username:', timeout=30)
            mgmt_device.sendline(telnet_uname)
            mgmt_device.expect('.*Password:', timeout=30)
            mgmt_device.sendline(telnet_pwd)
            mgmt_device.expect(device.name + '#', timeout=30)
            mgmt_device.sendline('reload')
            log.info('Issuing a reload command.')
            try:
                reload_prompt = mgmt_device.expect('Do you want to reload the internal AP.*:', timeout=30)
                log.info('reload_prompt: %s'%reload_prompt)
                mgmt_device.sendline('no\r\n')
            except Exception as e: log.info(e)
            try:
                reload_prompt = mgmt_device.expect('System configuration has been modified.*', timeout=30)
                log.info('reload_prompt: %s'%reload_prompt)
                mgmt_device.sendline('no\r\n')
            except Exception as e: log.info(e)
            mgmt_device.expect('Proceed with reload?.*', timeout=60)
            log.info('Confirming reload.')
            mgmt_device.sendline('\r\n')
            log.info('Waiting for the device to reload.')
            time.sleep(180)
        except Exception as e:
            log.error('Error connecting and executing reload command on device: %s' % e)

        # Check if the device comes up.
        pingable = False
        timeout = time.time()+60*15
        while timeout>time.time():
            log.info('mgmt_ip: %s'%mgmt_ip)
            dev_utils = DeviceUtils()
            pingable = dev_utils.check_ping(mgmt_ip)
            if pingable:
                log.info(banner('%s CAME UP'%device_eid))
                break
            else: time.sleep(45)

        if not pingable: log.error(banner('ROUTER IS DOWN'))
    else:
        ''' Reloading device with telnet connection. '''
        try:
            from csccon import set_csccon_default
            device.set_csccon_default(destroy_wait=5)
            device.set_csccon_default(boot_timeout=900)
            device.set_csccon_default(auth_retry_timeout=300)
            device.reload()
            log.info('%s reload completed.'%device_eid)
        except Exception as e: log.info(e)

    reboot_end_time = time.time()
    reboot_time = float(reboot_end_time-reboot_start_time)/60
    log.info(banner('Time taken to Reboot: %.2f'%reboot_time))
    return '%s reload completed.'%device_eid

class HTTPSUnVerifiedCertTransport(transport.https.HttpAuthenticated):
    def __init__(self, *args, **kwargs):
        transport.https.HttpAuthenticated.__init__(self, *args, **kwargs)
    def u2handlers(self):
        handlers = []
        handlers.append(urllib.request.ProxyHandler(self.proxy))
        handlers.append(urllib.request.HTTPBasicAuthHandler(self.pm))
        # python ssl Context support - PEP 0466
        if hasattr(ssl, '_create_unverified_context'):
            ssl_context = ssl._create_unverified_context()
            handlers.append(urllib.request.HTTPSHandler(context=ssl_context))
        else:
            handlers.append(urllib.request.HTTPSHandler())
        return handlers

class DeviceUtils:
    ''' This class provides utility methods for device related operations.'''

    def __init__(self, **kwargs):
        if len(kwargs) != 0:
            global testbed
            testbed = kwargs['testbed']

    def force_close_line(self, term_ip, line_num, password):
        '''
        Forcefully closes the connection of a line from a term server.
        
        :param term_ip: IP of the term server
        :type term_ip: str
        :param line_num: line number of the device
        :type line_num: str
        :param password: password of the term server
        :type password: str
        '''
        
        log.info('Force closing line: %s on server: %s with password: %s' % (line_num, term_ip, password))
        term_server = pexpect.spawn('telnet ' + term_ip)

        try:
            term_server.expect('Password:', timeout=15)
            term_server.sendline(password)
        except Exception as e:
            log.info('No password set for term server.')

        term_server.expect('.*>', timeout=15)
        term_server.sendline('en')
        term_server.expect('.*Password:', timeout=15)
        term_server.sendline(password)
        log.info('After enable:\n term_server.before --\n%s\n term_server.after--\n%s\n' % (term_server.before, term_server.after))
        
        term_server.expect('.*#', timeout=15)
        term_server.sendline('clear line %s'%(line_num))
        log.info('Clear line:\n term_server.before --\n%s\n term_server.after--\n%s\n' % (term_server.before, term_server.after))
        
        term_server.expect('[confirm]', timeout=15)
        term_server.sendline('\n')
        log.info('Confirm clear line:\n term_server.before --\n%s\n term_server.after--\n%s\n' % (term_server.before, term_server.after))
        
        term_server.expect('.*#', timeout=30)
        esc = "echo 'e' | tr 'e' '\035'"
        term_server.sendline(esc)
        term_server.expect('telnet>')
        log.info('Exiting term server:\n term_server.before --\n%s\n term_server.after--\n%s\n' % (term_server.before, term_server.after))
        term_server.sendline('q\r')
        term_server.close()

    def connect_testbed_devices(self, testbed, **kwargs):
        '''
        This section connects to the devices loaded from the testbed file and checks if connections were successful.
        
        :param testbed: testbed object from the topology yaml file.
        :type testbed: object
        :returns: dictionary of device objects.
        '''
        log.info(banner(' os.path.isfile("/root/.ssh/known_hosts"): %s'%  os.path.isfile('/root/.ssh/known_hosts')))
        if  os.path.isfile('/root/.ssh/known_hosts'): os.remove('/root/.ssh/known_hosts')
        log.info(banner("CONNECTING TO DEVICES IN TESTBED"))
        ####### Create list and populate Testbed devices for use later in script  ######

        devices = {
            'nms_server':'',
            'db_server':'',
            'tps_server':'',
            'mesh_sim':'',
            'routerEIDs':'',
            'TestBedDevices':'',
            'ManagmentDevices':''
        }

        eids = []
        TestBedDevices = []
        ManagmentDevices = []
        force_connect = kwargs.get('force_connect', False)
        use_device = kwargs.get('use_device', [])
        use_device.append('nms_server')

        for tb_device in testbed.devices:
            device = testbed.devices[tb_device]
            log.info("Device name Before %s"%device)
            if device.custom.server not in use_device: continue
            log.info("Device name After %s"%device)
            #Update devices dictionary from testbed.yaml.
            if device.type == 'linux':
                if device.custom.server == 'nms_server': devices['nms_server'] = device
                elif device.custom.server == 'db_server': devices['db_server'] = device
                elif device.custom.server == 'tps_server': devices['tps_server'] = device
                elif device.custom.server == 'mesh_sim': devices['mesh_sim'] = device
            #These are the management devices. Can be connected only through ssh.
            elif hasattr(device.custom, 'connection_type') is True:
                ManagmentDevices.append(device)
                eids.append(device.custom.eid)
            #These are the devices that can be connected through telnet.
            else:
                TestBedDevices.append(device)
                eids.append(device.custom.eid)

            #Connect to device.
            try:
                if device.is_connected() == True: device.disconnect()
                if device.type != 'linux' and force_connect:
                    term_ip = str(device.connections.a.ip)
                    en_password = str(device.passwords.enable)
                    line_num = str(device.connections.a.port)[2:]
                    self.force_close_line(term_ip, line_num, en_password)

                tries = 0
                while tries<3:
                    try:
                        if device.type == 'linux':
                            log.info(banner('Connecting to - %s'%device.name))
                            device.connect(mit=True)
                            log.info("gggggggggggggggggggggggggggggggg")
                        else:
                            log.info(banner('Connecting to - %s, tries - %d'%(device.name, tries)))
                            if hasattr(device.custom, 'connection_type'):
                                log.info('\nConnecting with ssh')
                                device.connect(via='alt')
                                log.info("fffffffffffffffffffffffffffffffff")
                            else:
                                log.info('\nConnecting with telnet')
                                device.connect()

                        if device.is_connected(): tries = 4
                        elif device.type == 'linux' and not device.is_connected():
                            raise Exception()
                        elif device.name in routers and not device.is_connected():
                            line_num = str(device.connections.a.port)[2:]
                            self.force_close_line(term_ip, line_num, en_password)
                    except Exception as e:
                        log.error(e)
                        time.sleep(60)
                    tries = tries+1
            except Exception as e:
                log.error(e)
                log.error(banner('FAILED TO CONNECT TO DEVICES IN TESTBED'))

        devices['routerEIDs'] = eids
        devices['TestBedDevices'] = TestBedDevices
        devices['ManagmentDevices'] = ManagmentDevices
        log.info(banner("CONNECTED TO DEVICES IN TESTBED"))

        nms_server = devices['nms_server']
        nms_ip = str(nms_server.connections.linux.ip)
        product_version = str(nms_server.custom.product_version)
        automation_owner = str(nms_server.custom.automation_owner)
        log.info('nms_ip :: %s;;;'%nms_ip)
        log.info('fnd_version :: %s;;_;;%s;;_;;'%(product_version, automation_owner))

        log.info('\devices: %s\n'%devices)
        return devices

    def multiple_device_reload(self, device_eids):
        '''
        Module to reload multiple devices in parallel.
        
        :param device_eids: List of device eids to reload
        :type device_eids: list
        :returns: Result of the device reload status.
        '''
        log.info(banner('In multiple_device_reload'))
        pool = multiprocessing.Pool(processes=len(device_eids))
        log.info('devices len: %d, device_eids: %s'%(len(device_eids), device_eids))
        results = pool.map(device_reload, device_eids)
        pool.close()
        pool.join()
        log.info(results)
        return results

    def check_ping(self, hostname):
        '''
        Helper function to check if the device is pingable.
        
        :param hostname: host name of the device
        :type hostname: str
        :returns: returns if a device can be pinged.
        '''
        loss=100
        pingable=False
        found = False
        ping_cmd="ping -c 5 " + hostname
        response = os.popen(ping_cmd).read()
        log.info("ping_cmd: %s \nresponse:\n %s" % (ping_cmd, response))
        for line in response.splitlines():
            match = re.match(r'^\s*(\d+) packets transmitted, (\d+) received, (\d+(\.\d+)?)% packet loss, time (\d+)ms*$', line)
            if match:
                log.info(line)
                found = True
                num_xmit = int(match.group(1))
                num_rcv = int(match.group(2))
                loss = float(match.group(3))
                # log.info('num_xmit : ', num_xmit, 'num_rcv : ', num_rcv, 'loss : ', loss)
                log.info('num_xmit : %d, num_rcv: %d, loss : %0.2f'%(num_xmit, num_rcv, loss))
                break
        if not found:
            log.info('No packet transmitted/received/loss line found in "ping" response:\n%s' % (response))
        if loss < 100:
            log.info('"ping" had packet loss %.2f%%:\n%s' % (loss, response))
            pingable=True
        return pingable

    def enable_device(self, device):
        '''
        Helper function to enable device.
        Doing this painful excercise to get hold of device connection. CSSCON libraries are not reliable at this point of time.

        :param device: device object from testbed yaml file
        :type device: object
        :returns: True if a device is ready.
        '''
        enable_start_time = time.time()
        device_available = False
        if not device: return device_available
        timeout = time.time()+60*15
        while timeout>time.time():
            try:
                if  os.path.isfile('/root/.ssh/known_hosts'): os.remove('/root/.ssh/known_hosts')
                log.info('Performing sanity check on device: %s, connected: %s' % (device, device.is_connected()))
                device.enable()
                device.execute('sh clock')
                device_available = True
                break
            except Exception as e:
                log.error(e)
                log.info('device not ready yet!! Try again. is_connected: %s'%device.is_connected())
                time.sleep(60)
                try:
                    if device.is_connected(): device.disconnect()
                    log.info('Reconnecting to device: %s, connected: %s' % (device, device.is_connected()))
                    if hasattr(device.custom, 'connection_type'):
                        device.connect(via='alt')
                    else:
                        device.connect()
                    time.sleep(30)
                except Exception as e: log.info(e)

        enable_end_time = time.time()
        enable_time = float(enable_end_time-enable_start_time)/60
        log.info('Time taken to Enable device: %.2f, device_available: %s'%(enable_time, device_available))
        return device_available

    def device_sanity_check(self, device):
        '''
        Helper function to do a sanity check on device.
        
        :param device: device object from testbed yaml file
        :type device: object
        :returns: returns if a device is ready.
        '''
        device_available = False
        timeout = time.time()+60*3
        while timeout>time.time():
            try:
                log.info('Performing sanity check on device - device.is_connected() : %s' % device.is_connected())
                device.enable()
                log.info('Getting current time on device.')
                device.execute('sh clock')
                device_available = True
                break
            except Exception as e: log.error(e)
            time.sleep(30)

        return device_available

    def copy_flash_files(self, device, file_name, new_name):
        ''' 
        Copies the given file name on a device.

        :param device: device object from testbed yaml file
        :type device: object
        :param file_name: file name to be copied on the device
        :type file_name: str
        :param new_name: new file name to be copied on the device
        :type new_name: str
        '''
        
        log.info("copying file: %s on device: %s" % (file_name, device))
        device.enable()
        flash = device.execute('dir').split()
        backup_took = False
        ############# check if files are present which will cause a rollback of the router and remove them ############
        try:
            if device.type == 'ios':
                if file_name in flash:
                    device.transmit('copy flash:%s %s\r'%(file_name, new_name))
                    device.receive('Destination filename \[%s\]\?'%new_name)
                    device.transmit('\r')
                    try:
                        device.receive('Do you want to over write\? \[confirm\]')
                        device.transmit('\r')
                    except Exception as e:pass
                    time.sleep(5)

                    flash = device.execute('dir | inc %s'%new_name).split()
                    log.info("Confirming if given file got copied to flash: - %s \n %s" % (file_name not in flash, flash))
                    assert new_name in flash
            if device.type == 'cgos':
                if file_name in flash:    
                    device.execute('copy bootflash:%s %s'%(file_name, new_name),timeout=600)
                    bootflash = device.execute('dir | inc %s'%new_name).split()
                    log.info("Confirming if file got copied to bootflash: - %s \n %s" % (file_name not in bootflash, bootflash))
                    assert new_name in bootflash
            
            backup_took = True
        except AssertionError:
            log.error(banner('COULD NOT DELETE FILES'))
        
        return backup_took
    
    def delete_checkpoint_files(self, device):
        ''' 
        Deletes the 'before-tunnel-config' and 'before-registration-config' to skip the rollback of the device for IOS devices.
        Deletes the 'golden-config' and 'ps-start-config' to skip the rollback of the device for CGOS devices.

        :param device: device object from testbed yaml file
        :type device: object
        '''
        log.info("deleting checkpoint files for device: %s" % device)
        flash = device.execute('dir').split()
        #log.info(flash)
        ############# check if files are present which will cause a rollback of the router and remove them ############
        try:
            if device.type == 'ios':
                if 'before-tunnel-config' in flash:
                    log.info(banner('DELETING CHECKPOINT FILES'))
                    device.transmit('delete flash:before-tunnel-config\r')
                    device.receive('Delete filename \[before-tunnel-config\]\?')
                    device.transmit('\r')
                    device.receive('Delete flash:\/before-tunnel-config\? \[confirm\]')
                    device.transmit('\r')
                    time.sleep(5)
                if 'before-registration-config' in flash:
                    device.transmit('delete flash:before-registration-config\r')
                    device.receive('Delete filename \[before-registration-config\]\?')
                    device.transmit('\r')
                    device.receive('Delete flash:\/before-registration-config\? \[confirm\]')
                    device.transmit('\r')
                    time.sleep(5)

                    flash = device.execute('dir | inc before').split()
                    log.info("Confirming if before files got delted from flash: - %s \n %s" % ('before-tunnel-config' and 'before-registration-config' not in flash, flash))
                    assert 'before-tunnel-config' and 'before-registration-config' not in flash
            if device.type == 'cgos':
                if 'golden-config' and 'ps-start-config' in flash:    
                    device.execute('delete bootflash:golden-config',timeout=600)
                    device.execute('delete bootflash:ps-start-config',timeout=600)

                    bootflash = device.execute('dir | inc config').split()
                    log.info("Confirming if check point files got deleted from bootflash: - %s \n %s" % ('golden-config' and 'ps-start-config' not in bootflash, bootflash))
                    assert 'golden-config' and 'ps-start-config' not in bootflash
        except AssertionError:
            log.inof(banner('COULD NOT DELETE FILES'))
        except Exception as e: log.error(e)

    def delete_flash_files(self, device, file_name):
        ''' 
        Deletes the given file name on a device.

        :param device: device object from testbed yaml file
        :type device: object
        :param file_name: file name to be deleted on the device
        :type file_name: str
        '''
        
        device.enable()
        log.info("deleting file: %s on device: %s" % (file_name, device))
        flash = device.execute('dir | i %s'%file_name).split()
        ############# check if files are present which will cause a rollback of the router and remove them ############
        try:
            if device.type == 'ios':
                if file_name in flash:
                    device.transmit('delete flash:%s\r'%file_name)
                    device.receive('Delete filename \[%s\]\?'%file_name)
                    device.transmit('\r')
                    device.receive('Delete flash:\/%s\? \[confirm\]'%file_name)
                    device.transmit('\r')
                    time.sleep(5)

                    flash = device.execute('dir | inc %s'%file_name).split()
                    log.info("Confirming if before files got delted from flash: - %s \n %s" % (file_name not in flash, flash))
                    assert file_name not in flash
            if device.type == 'cgos':
                if file_name in flash:    
                    device.execute('delete bootflash:%s'%file_name,timeout=600)
                    bootflash = device.execute('dir | inc config').split()
                    log.info("Confirming if check point files got deleted from bootflash: - %s \n %s" % (file_name not in bootflash, bootflash))
                    assert file_name not in bootflash
        except AssertionError:
            log.inof(banner('COULD NOT DELETE FILES'))

    def delete_image_files(self, device, **kwargs):

        imgs=[]
        if len(kwargs) != 0:
            try:
                if 'img' in kwargs:
                    img = kwargs['img']
                    imgs.append(img)
                if 'hv_img' in kwargs:
                    hv_img = kwargs['hv_img']
                    imgs.append(hv_img)
                if 'univ_img' in kwargs:
                    univ_img = kwargs['univ_img']
                    imgs.append(univ_img)
            except Exception as e: log.error('No imaged file names provided.')

        self.enable_device(device)
        device.transmit('cd flash:/managed/images\r')
        device.receive('\r')

        log.info('\n\n imgs: %s \n\n'%(imgs))
        for img in imgs:
            device.transmit('delete %s\r'%img)
            device.receive('\r')
            device.transmit('\r')
            device.receive('\r')
            device.transmit('\r')
            device.receive('\r')
        curr_images = device.execute('dir').split('\r\n')
        log.info('curr_images: %s'%curr_images)
        device.transmit('end\r')

        '''
        if 'img' in kwargs:pass
        elif 'hv_img' in kwargs and 'univ_img' in kwargs:pass
        elif len(kwargs) == 0:
            curr_images = device.execute('dir').split('\r\n')
            try:
                c800_img = [s.split(' ')[-1] for s in curr_images if 'c800' in s][-1]
                imgs.append(c800_img)
            except Exception as e:log.error(e)

            try:
                log.info('')
                hv_img = [s.split(' ')[-1] for s in curr_images if 'hv.srp' in s][-1]
                univ_img = [s.split(' ')[-1] for s in curr_images if 'universalk9' in s][-1]
                imgs.append(hv_img)
                imgs.append(univ_img)
            except Exception as e:log.error(e)
        '''

class TestUtils:
    '''
    This class provides utility methods for automation test related operations.
    '''

    def __init__(self): pass

    def get_utc_curr_time(self):
        '''
        Helper function to convert current system time to UTC time.

        :returns: current time in UTC time zone
        '''
        log.info("Getting current UTC time.")
        sys_curr_time_sec = time.mktime(datetime.now().timetuple())
        utc_curr_time = (datetime.utcfromtimestamp(sys_curr_time_sec))
        utc_curr_time_sec = time.mktime(utc_curr_time.timetuple())

        curr_time_sys = datetime.fromtimestamp(sys_curr_time_sec).strftime('%Y-%m-%d %H:%M:%S:00')
        curr_time_utc = datetime.fromtimestamp(utc_curr_time_sec).strftime('%Y-%m-%d %H:%M:%S:00')
        log.info("curr_time_sys: %s, curr_time_utc: %s" % (curr_time_sys, curr_time_utc))
        return curr_time_utc

    def get_utc_curr_time_delta(self, time_format, time_delta_op, time_delta_key, time_delta_value):
        '''
        Helper function to convert current system time to UTC time.

        :returns: current time in UTC time zone
        '''
        # format = '%Y-%m-%dT%H:%M:%S'
        now = datetime.now()
        try:

            if time_delta_op == 'add' and time_delta_key == 'seconds':
                now_delta = now + timedelta(seconds=time_delta_value)
            elif time_delta_op == 'add' and time_delta_key == 'minutes':
                now_delta = now + timedelta(minutes=time_delta_value)
            elif time_delta_op == 'add' and time_delta_key == 'hours':
                now_delta = now + timedelta(hours=time_delta_value)
            elif time_delta_op == 'sub' and time_delta_key == 'seconds':
                now_delta = now - timedelta(seconds=time_delta_value)
            elif time_delta_op == 'sub' and time_delta_key == 'minutes':
                now_delta = now - timedelta(minutes=time_delta_value)
            elif time_delta_op == 'sub' and time_delta_key == 'hours':
                now_delta = now - timedelta(hours=time_delta_value)

            sys_curr_time_sec = time.mktime(datetime.now().timetuple())
            utc_curr_time = (datetime.utcfromtimestamp(sys_curr_time_sec))
            utc_curr_time_sec = time.mktime(utc_curr_time.timetuple())

            sys_curr_time_sec_delta = time.mktime(now_delta.timetuple())
            utc_curr_time_delta = (datetime.utcfromtimestamp(sys_curr_time_sec_delta))
            utc_curr_time_sec_delta = time.mktime(utc_curr_time_delta.timetuple())

            curr_time_sys = datetime.fromtimestamp(sys_curr_time_sec).strftime(time_format)
            curr_time_utc = datetime.fromtimestamp(utc_curr_time_sec).strftime(time_format)
            curr_time_utc_delta = datetime.fromtimestamp(utc_curr_time_sec_delta).strftime(time_format)
            log.info("curr_time_sys: %s, curr_time_utc: %s, curr_time_utc_delta: %s" % (curr_time_sys, curr_time_utc, curr_time_utc_delta))
        except Exception as e: log.error(e)

        return curr_time_utc_delta

    def get_utc_curr_time_millisec(self):
        '''
        Helper function to convert current system time to UTC time in milliseconds.

        :returns: current time in UTC time zone in milliseconds
        '''
        # curr_time_sys = datetime.now()
        # curr_time_sys_millisec = round((curr_time_sys - datetime(1970, 1, 1)).total_seconds()) * 1000
        #log.info("curr_time_sys_millisec: %s, curr_time_utc_millisec: %s" % (curr_time_sys_millisec, curr_time_utc_millisec))

        # curr_time_sys = datetime.fromtimestamp(curr_time_sys_millisec/1000).strftime('%Y-%m-%d %H:%M:%S:00')
        # curr_time_utc = datetime.fromtimestamp(curr_time_utc_millisec/1000).strftime('%Y-%m-%d %H:%M:%S:00')
        # log.info("curr_time_sys: %s, curr_time_utc: %s" % (curr_time_sys, curr_time_utc))
        curr_time_utc = datetime.utcnow()
        curr_time_utc_millisec = round((curr_time_utc - datetime(1970, 1, 1)).total_seconds()) * 1000
        return curr_time_utc_millisec

    def escape_color_code(self, output):
        '''
        Escapes the color codes from the given text.

        :returns: returns output without color code 
        '''
        ansi_escape = re.compile(r'\x1b[^m]*m')
        output = ansi_escape.sub('', output)
        ansi_escape = re.compile(r'\x1b[^K]*K')
        output = ansi_escape.sub('', output)
        output = re.sub(' +', ' ', output)
        output = re.sub('\r\n', '', output)
        return output

    def get_remote_ssh_client(self, **kwargs):

        #Creating the client for remote server access.
        remote_ssh_client = paramiko.SSHClient()
        remote_ssh_client.load_system_host_keys()
        remote_ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        timeout=kwargs['timeout'] if 'timeout' in kwargs else 60
        log.info(banner('timeout: %d'%timeout))

        #Connecitng to remote server.
        remote_ssh_client.connect(kwargs['server'],
                       username=kwargs['username'],
                       password=kwargs['password'],
                       timeout=timeout)

        return remote_ssh_client

    def tail_remote_logs(self, **kwargs):
        '''
        Utility function to tail the logs on a remote server.

        :param kwargs: dictionary object with remote server details
        :type kwargs: dict
        '''

        log.info(banner('Started Capturing Logs.'))
        def linesplit(socket):
            ''' Inner function to split the lines.'''
            buffer_string = socket.recv(4048).decode("utf-8")
            done = False
            while not done:
                if "\n" in buffer_string:
                    (line, buffer_string) = buffer_string.split("\n", 1)
                    yield line + "\n"
                else:
                    more = socket.recv(4048).decode("utf-8")
                    if not more:
                        done = True
                    else:
                        buffer_string = buffer_string + more
            if buffer_string:
                yield buffer_string

        #Initialize arguments required to log into a remote server.
        log_file = kwargs['log_file']
        log_check_list = kwargs.get('log_check_list', [])
        timeout = kwargs.get('timeout', 5)
        timeout = time.time()+ 60*timeout
        client = self.get_remote_ssh_client(server=kwargs['server'], username=kwargs['username'], password=kwargs['password'])

        #We change this value depending on the user preference - Append to list if grepped, Removed from log_check_list if found in logs.
        return_log_list = []
        tail_command = 'tail -f %s' % (log_file)
        if 'grep_filter' in kwargs:
            tail_command = tail_command + ' | grep -nr "' + kwargs['grep_filter'] + '"'

        log.info('tail_command: %s' % tail_command)
        log.info('log_file: %s, log_check_list: %s, timeout: %d'%(log_file, log_check_list, timeout-time.time()))

        transport = client.get_transport()
        channel = transport.open_session()
        channel.exec_command(tail_command)

        read_next_line=True
        while read_next_line:

            if time.time()>timeout:
                log.info('timed out!! skipping log check.')
                read_next_line = False

                if not log_check_list:
                    log.info('successfully verified all the logs.')
                else:
                    log.error('Didn\'t verified all the logs.\n log_check_list_remaining: %s'%log_check_list)
                    return_log_list = log_check_list

            try:
                rl, _, _ = select.select([channel], [], [], 0.0)
                time.sleep(1)
                if len(rl)>0:
                    for line in linesplit(channel):
                        log.info("line: %s" % line)

                        if 'grep_filter' not in kwargs:
                            matches = [log_item for log_item in log_check_list if log_item in line]
                            if matches:
                                log.info('Matched Log')
                                log.info(banner('matches:%s \n line: %s' % (matches, line)))
                                if matches[0] == log_check_list[-1]:
                                    log.info('Got the final log condition, skipping other log checks and exiting.')
                                    log.info('skipped logs: %s' % log_check_list)
                                    read_next_line = False
                                log_check_list.remove(matches[0])
                                log.info('log_check_list: %s\nmatches: %s'%(log_check_list, matches))
                                log.info('Current Checklist')
                                log.info('log_check_list: %s' % log_check_list)

                            if not log_check_list:
                                read_next_line = False
                                log.info('Conditions met. Exiting tail_remote_logs.')

                        #Capturing the matched grep logs.
                        else:
                            log.info('Appending log...')
                            return_log_list.append(line)

                        #Break the for loop of reading lines after evey check.
                        break

            except (KeyboardInterrupt, SystemExit): break

        log.info('return_log_list: %s' % return_log_list)
        return return_log_list

    def read_remote_logs(self, **kwargs):

        def linesplit(socket):
            ''' Inner function to split the lines.'''
            buffer_string = socket.recv(4048).decode("utf-8")
            #buffer_string = buffer_string.decode("utf-8")
            done = False
            while not done:
                if "\n" in buffer_string:
                    (line, buffer_string) = buffer_string.split("\n", 1)
                    yield line + "\n"
                else:
                    more = socket.recv(4048).decode("utf-8")
                    if not more:
                        done = True
                    else:
                        buffer_string = buffer_string + more
            if buffer_string:
                yield buffer_string

        log.info("lastLineNumber")
        log.info(kwargs.get('get_last_line'))
        return_log_list = []
        log_file = kwargs.get('log_file', None)
        client = kwargs.get('remote_ssh_client', None)
        if client==None or log_file==None:
            log.error('Provide all the required paramters.')
            return return_log_list
        log.info("lastLineNumber")
        log.info(kwargs.get('get_last_line'))
        line_number = int(kwargs.get('line_number', 0))
        get_last_line = kwargs.get('get_last_line', False)
        read_error_logs = kwargs.get('read_error_logs', False)
        grep_include = kwargs.get('grep_include', False)
        after_line_logs = kwargs.get('after_line_logs', False)
        custom_log = kwargs.get('custom_log', False)
        filter_logs = kwargs.get('filter_logs', [])
        grep_moudle = kwargs.get('grep_moudle', [])
        grep_filter = kwargs.get('grep_filter', '')
        read_custom_logs = True if custom_log else False

        if get_last_line:
            tail_command = 'cat %s | wc -l'%log_file
        elif grep_filter:
            tail_command = 'tail --lines=+%d %s | grep -nr "%s"'%(line_number, log_file, grep_filter)
        elif read_error_logs:
            grep_string = ''
            for i, module in enumerate(grep_moudle):
                if i==len(grep_moudle)-1: grep_string += '%s.*ERROR'%module
                else: grep_string += '%s.*ERROR|'%module

            tail_command = 'tail --lines=+%d %s | grep -E '%(line_number, log_file)
            if grep_string: tail_command+='"%s"'%grep_string
            else: tail_command+='".*ERROR"'
        elif read_custom_logs:
            tail_command = 'tail --lines=+%d %s | grep "%s"'%(line_number, log_file, custom_log)
        elif after_line_logs:
            tail_command = 'tail --lines=+%d %s'%(line_number, log_file)
        elif grep_include:
            tail_command = 'tail --lines=+%d %s | grep -i "%s"'%(line_number, log_file, grep_include)

        transport = client.get_transport()
        channel = transport.open_session()
        channel.exec_command(tail_command)

        for line in linesplit(channel):
            log.info("line: %s" % line)
            return_log_list.append(line)
        if not get_last_line:
            log.info('\ntail_command: \n%s'%tail_command)
            defaul_filter_logs = ['Please verify HSM connection', 'Unable to reconnect with HSM', 'Please verify SSM server status',
                                  'Exception in the filter chain', 'Pon message will be ignored', 'Only one device import job is allowed at a time',
                                  'Narrowing proxy to class', 'Missing type info for interface', 'Invalid Certificate Exception',
                                  'Readiness Check Failed', 'Unable to establish a NETCONF SSH session', 'Seems like Wpan HA is disabled',
                                  'User has not logged in', 'java.lang.ClassNotFoundException', 'Format error in version:',
                                  'Passwords do not match for local user', 'Exception in getTree','IlLegal Access with No token table',
                                  'rolled back device', 'ignore device', 'not able to persist tunnel uptime', 'Could not get CsmpSignatureKeyStore instance',
                                  'License file already exist', 'Method invocation failed with exception', 'License file already exist', 'Error unmarshalling xml element',
                                  'Unable to schedule a runnable to process', 'Information of the uploaded file', 'Error processing lwm2m message', 'org.hibernate.exception.SQLGrammarException',
                                  'cannot setup csmp agent', 'ElementNetconfSshSession', 'ElementHeartbeatJob', 'EventPushJob', 'LicenseAction', 'DomainDetailsAction', 'NetElementServiceImpl','CgmsAuthenticator']
            filter_logs += defaul_filter_logs
            log.info('filter_logs list:\n%s'%filter_logs)
            for line in filter_logs:
                #log.info('Filtering:\n %s'%line)
                return_log_list = list(filter(lambda error_log: line not in error_log, return_log_list))

        return list(return_log_list)

    def validate_in_parallel(self, *function_names, **kwargs):

        processes = []
        args = kwargs['args'] if 'args' in kwargs else False
        log.info('function_names: %s, kwargs%s'%(function_names, kwargs))
        from multiprocessing import Manager
        return_dict = Manager().dict()

        for function_name in function_names:
            if args: process = Process(target=function_name, args=(return_dict, args,))
            else: process = Process(target=function_name, args=(return_dict,))
            process.start()
            processes.append(process)
        for process in processes:
            process.join()

        log.info(banner('Done with the parallel execution.'))
        log.info('return_dict_values: %s'%return_dict.values())
        return return_dict

    def hex_to_ipv4(self, hex):
        try: return str(socket.inet_ntoa(struct.pack('!L', int(hex,16))))
        except Exception as e: return ''

    def get_csmp_response(self, nms_server, csmp_ip, tlv_id):

        csmp_resp = {'Ip4Addr':'', 'Ip4AddrPfxLen':''}
        try:
            log.info(banner('Getting csmp response of "%s" for TLV: %d'%(csmp_ip, tlv_id)))
            nms_server.connect()
            log.info('\n\nNavigating to /opt/cgms-tools/bin')
            nms_server.execute('cd /opt/cgms-tools/bin/\r')
            nms_server.transmit('pwd')
            nms_server.receive(r'.*>', timeout=3)
            time.sleep(2)

            log.info('\nExecuting "csmp-request" script.')
            nms_server.transmit('./csmp-request -r [%s] %d'%(csmp_ip, tlv_id))
            nms_server.receive(r'.*>', timeout=30)
            time.sleep(2)
            resp = nms_server.receive_buffer()
            resp = resp.split(']: ')[1].split('\r\n')[0]
            resp = resp.replace('\\x', '')
            csmp_resp = json.loads(resp, strict=False)
        except Exception as e:
            nms_server.disconnect()
            log.error('Unable to execute csmp request.')

        log.info('\ncsmp_resp: %s\n'%json.dumps(csmp_resp, indent=4, sort_keys=True))
        return csmp_resp

    def get_csmp_response_rfc(self, nms_server, csmp_ip, tlv_id):

        csmp_resp = {'Ip4Addr':'', 'Ip4AddrPfxLen':''}
        try:
            log.info(banner('Getting csmp response of "%s" for TLV: %d'%(csmp_ip, tlv_id)))
            nms_server.connect()
            log.info('\n\nNavigating to /opt/cgms-tools/bin')
            nms_server.execute('cd /opt/cgms-tools/bin/\r')
            nms_server.transmit('pwd')
            nms_server.receive(r'.*>', timeout=3)
            time.sleep(2)

            log.info('\nExecuting "csmp-request" script.')
            nms_server.transmit('./csmp-request -rfc -r [%s] %d'%(csmp_ip, tlv_id))
            nms_server.receive(r'.*>', timeout=30)
            time.sleep(2)
            resp = nms_server.receive_buffer()
            resp = resp.split(']: ')[1].split('\r\n')[0]
            resp = resp.replace('\\x', '')
            csmp_resp = json.loads(resp, strict=False)
        except Exception as e:
            nms_server.disconnect()
            log.error('Unable to execute csmp request.')

        log.info('\ncsmp_resp: %s\n'%json.dumps(csmp_resp, indent=4, sort_keys=True))
        return csmp_resp

    def get_csmp_response_lg(self, nms_server, csmp_ip):

        csmp_resp = {'Ip4Addr':'', 'Ip4AddrPfxLen':''}
        try:
            log.info(banner('Getting csmp response of "%s" for ALL TLV'%(csmp_ip)))
            nms_server.connect()
            log.info('\n\nNavigating to /opt/cgms-tools/bin')
            nms_server.execute('cd /opt/cgms-tools/bin/\r')
            nms_server.transmit('pwd')
            nms_server.receive(r'.*>', timeout=3)
            time.sleep(2)

            log.info('\nExecuting "csmp-request" script.')
            nms_server.transmit('./csmp-request -rfc -r [%s] 23 17 25 58 75 22 61 88 13'%(csmp_ip))
            nms_server.receive(r'.*>', timeout=30)
            time.sleep(2)
            resp = nms_server.receive_buffer()
            log.info(resp)
            resp = resp.split(']: ')[9].split('\r\n')[0]
            resp = resp.replace('\\x', '')
            csmp_resp = json.loads(resp, strict=False)
        except Exception as e:
            nms_server.disconnect()
            log.error('Unable to execute csmp request.')

        log.info('\ncsmp_resp: %s\n'%json.dumps(csmp_resp, indent=4, sort_keys=True))
        return csmp_resp

    def forensic_test(self, nms_ssh_client, log_file, last_line_number, fail_flag, **kwargs):
        try:
            fail_test = False
            filter_logs = kwargs.get('filter_logs', [])
            grep_moudle = kwargs.get('grep_moudle', [])
            filter_logs.append('User has not logged in')
            error_logs = self.read_remote_logs(
                remote_ssh_client=nms_ssh_client, log_file=log_file, filter_logs=filter_logs,
                read_error_logs=True, line_number=last_line_number, grep_moudle=grep_moudle, get_last_line=False)

            if error_logs!=[]:
                log.error('Found Error logs: \n%s'%error_logs)
                raise Exception('Should not see Error Logs')
            if fail_flag != False:
                raise Exception('Something went wrong. Check screenshots for this section')
            log.info('No ERROR logs found on FND')
        except Exception as e:
            fail_test = True
        return fail_test

class NBAPIUtils:
    ''' This class provides utility methods for nbapi soap calls.'''
    '''
    try:
        frame = inspect.stack()[1]
        module = inspect.getmodule(frame[0])
        if module:
            log.info('Called from %s' % module.__file__)
    except: log.error('Unable to get module info.')
    '''

    def __init__(self): pass

    def get_nbapi_clients(self, nms_server, *args, **kwargs):
        '''
        Creates soap clients for NBAPI calls for the requested services. Creates all services by default.

        :param nms_server: nms server object from the testbed yaml file. This has all the nms server information.
        :type nms_server: object
        :params args: variable arguments for specific services.
        :type args: list
        '''
        nms_ip = str(nms_server.connections.linux.ip)
        nms_user = kwargs.get('nms_user', str(nms_server.custom.gui_uname))
        nms_password = kwargs.get('nms_password', str(nms_server.custom.gui_pwd))
        log.info('nms_ip: %s, nms_user:%s, nms_password: %s'%(nms_ip, nms_user, nms_password))
        
        nbapi_clients = {}
        wsdl_requested = []
        wsdl_default = ['audittrail', 'device', 'event', 'groups', 'issue', 'meshDeviceOps', 'orchestration', 'reprovision', 'rules',  'search', 'workorder']

        # Using the 'args' parameters to decide what all clients to generate. Empty arguments will create all the available wsdl clients.
        if len(args) is 0:
            wsdl_requested = wsdl_default
        else:
            log.info('Requested for nbapi clients: %s' % (args,))
            for arg in args:
                wsdl_requested.append(arg)

        log.info('wsdl_requested: %s' % wsdl_requested)
        for wsdl in wsdl_requested:
            client_service = 'https://'+nms_ip+'/nbapi/' + wsdl + '?wsdl'
            log.info(wsdl+'_service: %s' % client_service)
            t = HTTPSUnVerifiedCertTransport(username=nms_user,password=nms_password)
            wsdl_client = Client(client_service, transport=t, username=nms_user, password=nms_password, timeout=10000)
            wsdl_client.set_options(location=client_service)
            wsdl_client.set_options(cache=None)
            nbapi_clients[wsdl + '_client'] = wsdl_client

        log.info('nbapi_clients:\n%s' % nbapi_clients)        
        return nbapi_clients

    def find_device_in_fnd(self, search_client, eid):
        '''
        Utility function to add devices using NBAPI and wait for the job completion.
        
        :param search_client: suds client object
        :type search_client: object
        :param eid: eid of the device form the testbed yaml file
        :type eid: str
        '''

        device_found = False
        try:
            search_response = search_client.service.searchDevices(query='eid:'+eid,count=1,offset=0)
            if hasattr(search_response, 'devices'):
                device_found = True
        except:
            log.info("Can't get search response.")

        log.info('Device with EID: %s is found: %s'%(eid, device_found))
        return device_found

    def add_devices_to_fnd(self, device_client, **kwargs):
        '''
        Utility function to add devices using NBAPI and wait for the job completion.

        :param device_client: suds client object
        :type device_client: object
        :param kwargs: device data or path to device csv file
        :type kwargs: str
        '''
        device_added = False
        add_response = ''

        # Read the file contents from 'csv_path' or  'csv_data' and convert to base64 encoded stream to send to NMS. 
        if 'csv_data' in kwargs: device_file = kwargs['csv_data']
        elif 'csv_path' in kwargs: device_file = open(kwargs['csv_path'], 'r').read().rstrip().replace('\n', '\r\n')
        
        device_data = (base64.b64encode(device_file.encode())).decode()
        log.info('device_data: %s' % device_data)

        # Create a tns:deviceFile complex_type for 'addDevices' soap method.
        file_obj = device_client.factory.create('deviceFile')
        file_obj.data = device_data
        file_obj.filename = 'nbapi_device.csv'
        file_obj.username = 'root'

        try:
            add_response = device_client.service.addDevices(file=file_obj)
            log.info('add_response: %s' % add_response)
        except Exception as e:
            log.warning('''
                We are hitting a sax.parse.exception with suds client as the server is not repling a valid xml data. Ignore this.
                Add a little hack under env_py_path/site-packages/suds/client.py to skip this error next time.
                We are basically removing the unnecessary stuff from the server response using regex.

                reply_match = re.search('<soap:Envelope>.*</soap:Envelope>', str(reply))
                reply = reply_match.group().encode()
                ''')
            log.info("Unable to add devices.\n %s"%e)

        try:
            if not add_response: raise Exception('No add_response')
            timeout = time.time()+60*2
            while timeout>time.time():
                log.info('Checking for device completion status.')
                response = device_client.service.getJob(jobId=str(add_response))
                log.info('add device status: %s' % response)

                if 'COMPLETED' in response.status:
                    device_added = True
                    break
                if 'FAILED' in response.status : break
                time.sleep(5)
        except Exception as e:
            log.error(e)

        log.info('device_added: %s'%device_added)
        return device_added

    def update_devices_in_fnd(self, device_client, **kwargs):
        '''
        Utility function to update devices using NBAPI and wait for the job completion.
        
        :param device_client: suds client object
        :type device_client: object
        :param csv_path: path to device csv file
        :type csv_path: str
        '''

        devices_updated=False
        # Read the file contents from 'device_path' and convert to base64 encoded stream to send to NMS.
        if 'csv_data' in kwargs: device_file = kwargs['csv_data']
        elif 'csv_path' in kwargs: device_file = open(kwargs['csv_path'], 'r').read().rstrip().replace('\n', '\r\n')

        device_data = (base64.b64encode(device_file.encode())).decode()
        log.info('device_data: %s' % device_data)

        # Create a tns:deviceFile complex_type for 'addDevices' soap method.
        file_obj = device_client.factory.create('deviceFile')
        file_obj.data = device_data
        file_obj.filename = 'nbapi_device.csv'
        file_obj.username = 'root'

        try:
            update_response = device_client.service.updateDevices(file=file_obj)
            log.info('update_response: %s' % update_response)
        except AssertionError as e:
            log.warning('''
                We are hitting a sax.parse.exception with suds client as the server is not repling a valid xml data. Ignore this.
                Add a little hack under $(Python environmaent path)/site-packages/suds/client.py to skip this error next time.
                We are basically removing the unnecessary stuff from the server response using regex.

                reply_match = re.search('<soap:Envelope>.*</soap:Envelope>', str(reply))
                reply = reply_match.group().encode()
                ''')
            log.error(banner("Unable to update devices.\n %s"%e))

        timeout = time.time()+60*2
        while timeout>time.time():
            log.info('Checking for device update status.')
            response = device_client.service.getJob(jobId=str(update_response))
            log.info('remove completion status: %s' % response)
            
            if 'COMPLETED' in response.status:
                devices_updated=True
                break
            if 'FAILED' in response.status : break
            time.sleep(5)

        return devices_updated

    def remove_devices_in_fnd(self, device_client, **kwargs):
        '''
        Utility function to add devices using NBAPI and wait for the job completion.
        
        :param device_client: suds client object
        :type device_client: object
        :param csv_path: path to device csv file
        :type csv_path: str
        '''

        # Read the file contents from 'device_path' and convert to base64 encoded stream to send to NMS. 
        device_removed = False
        remove_response = ''

        # Read the file contents from 'csv_path' or  'csv_data' and convert to base64 encoded stream to send to NMS.
        if 'csv_data' in kwargs: device_file = kwargs['csv_data']
        elif 'csv_path' in kwargs: device_file = open(kwargs['csv_path'], 'r').read().rstrip().replace('\n', '\r\n')

        device_data = (base64.b64encode(device_file.encode())).decode()
        log.info('device_data: %s' % device_data)

        # Create a tns:deviceFile complex_type for 'addDevices' soap method.
        file_obj = device_client.factory.create('deviceFile')
        file_obj.data = device_data
        file_obj.filename = 'nbapi_device.csv'
        file_obj.username = 'root'

        try:
            remove_response = device_client.service.removeDevices(file=file_obj)
            log.info('remove_response: %s' % remove_response)
        except:
            log.warning('''
                We are hitting a sax.parse.exception with suds client as the server is not repling a valid xml data. Ignore this.
                Add a little hack under env_py_path/site-packages/suds/client.py to skip this error next time.
                We are basically removing the unnecessary stuff from the server response using regex.

                reply_match = re.search('<soap:Envelope>.*</soap:Envelope>', str(reply))
                reply = reply_match.group().encode()
                ''')
            log.error(banner("Unable to remove devices."))

        try:
            if not remove_response: raise Exception('No remove_response')
            timeout = time.time()+60*2
            while timeout>time.time():
                log.info('Checking for device remove completion status.')
                response = device_client.service.getJob(jobId=str(remove_response))
                log.info('remove completion status: %s' % response)

                if 'COMPLETED' in response.status :
                    device_removed = True
                    break
                if 'FAILED' in response.status : break
                time.sleep(5)
        except Exception as e:
            log.error(e)

        log.info('device_removed: %s'%device_removed)
        return device_removed

    def set_devices_in_fnd(self, device_client, status, **kwargs):
        '''
        Utility function to update devices using NBAPI and wait for the job completion.
        
        :param device_client: suds client object
        :type device_client: object
        :param status: Status that needs to be set
        :type status: str
        :param kwargs: device data or path to device csv file
        :type kwargs: str
        '''

        devices_updated = False
        set_response = ''

        # Read the file contents from 'csv_path' or  'csv_data' and convert to base64 encoded stream to send to NMS.
        if 'csv_data' in kwargs: device_file = kwargs['csv_data']
        elif 'csv_path' in kwargs: device_file = open(kwargs['csv_path'], 'r').read().rstrip().replace('\n', '\r\n')

        device_data = (base64.b64encode(device_file.encode())).decode()
        log.info('device_data: %s' % device_data)

        # Create a tns:deviceFile complex_type for 'addDevices' soap method.
        file_obj = device_client.factory.create('deviceFile')
        file_obj.data = device_data
        file_obj.filename = 'nbapi_device.csv'
        file_obj.username = 'root'

        try:
            set_response = device_client.service.setDevices(file=file_obj, status=status)
            log.info('set_response: %s' % set_response)
        except AssertionError as e:
            log.warning('''
                We are hitting a sax.parse.exception with suds client as the server is not repling a valid xml data. Ignore this.
                Add a little hack under $(Python environmaent path)/site-packages/suds/client.py to skip this error next time.
                We are basically removing the unnecessary stuff from the server response using regex.

                reply_match = re.search('<soap:Envelope>.*</soap:Envelope>', str(reply))
                reply = reply_match.group().encode()
                ''')
            log.error(banner("Unable to set devices."))

        try:
            if not set_response: raise Exception('No set_response')
            timeout = time.time()+60*2
            while timeout>time.time():
                log.info('Checking for device set status.')
                response = device_client.service.getJob(jobId=str(set_response))
                log.info('remove completion status: %s' % response)
                
                if 'COMPLETED' in response.status:
                    devices_updated=True
                    break
                if 'FAILED' in response.status : break
                time.sleep(5)
        except Exception as e:
            log.error(e)

        log.info('devices_updated: %s'%devices_updated)
        return devices_updated

    def get_group_info(self, groups_client, group_name, group_type):
        log.info('Deleting group under Device Configuration.')
        group_found = False
        try:
            response = groups_client.service.getGroupInfo(groupName=group_name, groupType=group_type)                  
            log.info('response: %s \n code: %s' % (response, response.code))
            if response.code=='SUCCESS': group_found = True
        except Exception as e: log.info("Error getting router group info: %s" % e)

        return group_found

    def create_group(self, groups_client, group_name, device_category, group_type):
        log.info('Creating config group under Device Configuration.')
        config_group_created = False
        try:
            response = groups_client.service.createGroup(groupName=group_name, deviceCategory=device_category, groupType=group_type)                  
            log.info('response: %s \n code: %s, message: %s' % (response, response.code, response.message))

            if hasattr(response, 'groups'):
                groups = response.groups
                for group in groups:
                    defaultGroup=group.defaultGroup
                    deviceCategory=group.deviceCategory
                    group_id=group.id
                    group_name=group.name
                    netObjectType=group.netObjectType
                    group_type=group.type

                    log.info("\n defaultGroup: %s \n deviceCategory: %s \n group_id: %s \n group_name: %s \n netObjectType: %s \n group_type: %s" 
                            % (defaultGroup, deviceCategory, group_id, group_name, netObjectType, group_type))
                    config_group_created = True
            else: log.info('Unable to create a router group.')
        except Exception as e: log.info("Error creating router group: %s" % e)

        return config_group_created

    def rename_group(self, groups_client, group_name, group_type, new_name):
        log.info('Renaming group under Device Configuration.')
        config_group_deleted = False
        try:
            response = groups_client.service.renameGroup(groupName=group_name, groupType=group_type, newName=new_name)                  
            log.info('response: %s \n code: %s, message: %s' % (response, response.code, response.message))
            config_group_deleted = True
        except Exception as e: log.info("Error creating router group: %s" % e)

        return config_group_deleted

    def delete_group(self, groups_client, group_name, group_type):
        log.info('Deleting group under Device Configuration.')
        config_group_deleted = False
        try:
            response = groups_client.service.deleteGroup(groupName=group_name, groupType=group_type)                  
            log.info('response: %s \n code: %s, message: %s' % (response, response.code, response.message))
            config_group_deleted = True
        except Exception as e: log.info("Error creating router group: %s" % e)

        return config_group_deleted

    def get_device_details(self, search_client, **kwargs):

        device_details = None
        query = kwargs['query'] if 'query' in kwargs else ''
        deviceIds = kwargs['deviceIds'] if 'deviceIds' in kwargs else None
        queryId = kwargs['queryId'] if 'queryId' in kwargs else None
        count = kwargs['count'] if 'count' in kwargs else 1000
        offset = kwargs['offset'] if 'offset' in kwargs else 0

        try:
            if deviceIds and queryId:
                response = search_client.service.getDeviceDetails(query=query, deviceIds=deviceIds, queryId=queryId, count=count, offset=offset)
            elif deviceIds:
                response = search_client.service.getDeviceDetails(query=query, deviceIds=deviceIds, count=count, offset=offset)
            elif queryId:
                response = search_client.service.getDeviceDetails(query=query, queryId=queryId, count=count, offset=offset)
            else:
                response = search_client.service.getDeviceDetails(query=query, count=count, offset=offset) 
 
            log.info('response: %s' % (response))
            device_details = response
        except Exception as e: log.error("Error getting device details: %s" % e)

        return device_details

    def search_devices(self, search_client, **kwargs):

        devices = []
        query = kwargs.get('query', '')
        fieldNames = kwargs.get('fieldNames', '')
        queryId = kwargs.get('queryId', '')
        count = kwargs.get('count', 1000)
        offset = kwargs.get('offset', 0)

        try:
            response = search_client.service.searchDevices(query=query, fieldNames=fieldNames, queryId=queryId, count=count, offset=offset)
            log.info('response: %s'%(response))
            if response.queryStatus=='SUCCEEDED':
                for dev in response.devices:
                    devices.append(dev.eid)

        except Exception as e: log.info("Error getting device details: %s" % e)

        return devices
