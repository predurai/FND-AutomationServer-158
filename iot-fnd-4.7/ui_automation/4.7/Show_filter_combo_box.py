#!/bin/env python
###################################################################
# Labels.py : 
###################################################################
"""
prerequisite to run the script:-

1. Minimum 1 cgr and 1 her should be in up
2. import asset json file which has vin, hvacNumber, poleNumber and housePlate in asset properties

"""


import os
import re
import sys
import csv
import time
import yaml
import datetime
import requests
import collections
import urllib.request
from random import randint

from ats import tcl
from ats import aetest
from ats import easypy
from ats import results

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import NoAlertPresentException

import logging
from ats.log.utils import banner
log = logging.getLogger(__name__)
logging.getLogger().setLevel(logging.INFO)

sys.path.insert(0, os.getcwd() + '/lib')
import fnd_utils, ui_common_utils1

driver_utils = None
nms_ssh_client = None
test_utils = fnd_utils.TestUtils()
role = 'admin'
val = 'test'
cat_val = 'router'
her_cat_val = 'her'
eid_val = '2ED02DFFFE6E0EF1'
stat_val = 'up'
issue_val = 'Down'
issue_stat = 'OPEN'
issue_sev = 'MAJOR'
typ_val = 'cgr1000'
her_typ_val = 'asr1000'
ip_val = '10.104.188.126'
tgroup_val = 'default-cgr1000[root] [default]'
name_val = '2ED02DFFFE6E0EF1'
her_name_val = 'HER'
func_val = 'gateway'
model_var = 'CGR1120/K9'
serial_val = 'JAF1648BBCT'
firmw_val = '15.8(3)M0a'
her_name_val = 'asr'
her_int_val = 'Tunnel0'
protocol_val = 'GRE'
evnt_name = 'Time Mismatch'
event_sev = 'MAJOR'
ip_val = '10.104.188.150'
far_nam_val = 'asr'
far_int_val = 'Tunnel0'
timezne = 'IST'
attach_wo = 'yes'
wr_status = 'In Service'
today = datetime.datetime.now().strftime('%Y-%m-%d')
twoday = (datetime.datetime.now()+datetime.timedelta(days=2)).strftime('%Y-%m-%d') 
log_file = '/opt/cgms/server/cgms/log/server.log'
grep_moudle=['WebFilter',
             'NetElementServiceImpl',
             'ElementListJsonAction']

class CommonSetup(aetest.CommonSetup):

    @aetest.subsection
    def connect_to_devices(self, testbed):
        ''' 
        This section connects to the devices loaded from the testbed file and checks if connections were successful.

        param testbed: Testbed object from the topology yaml file.
        type testbed: object
        '''
        logging.basicConfig(format='%(asctime)s %(message)s')

        global driver_utils
        global nms_ssh_client
        dev_utils = fnd_utils.DeviceUtils()
        test_utils = fnd_utils.TestUtils()
        tb_devices = dev_utils.connect_testbed_devices(testbed)

        nms_server = tb_devices['nms_server']
        nms_ip = str(nms_server.connections.linux.ip)
        username = nms_server.custom.gui_uname
        password = nms_server.custom.gui_pwd
        firefox_profile_name = nms_server.custom.firefoxprofile2

        #Firefox webdriver.
        profile = webdriver.FirefoxProfile(firefox_profile_name)
        driver = webdriver.Firefox(firefox_profile=profile)
        driver.set_window_size(1920, 1080)
        driver.implicitly_wait(30)
        driver.maximize_window()

        log.info('Logging into FND.')
        driver_utils = ui_common_utils1.DriverUtils(driver)
        driver = driver_utils.log_into_fnd(nms_ip, username, password)

        nms_ssh_client = test_utils.get_remote_ssh_client(server=str(nms_server.connections.linux.ip),
                                            username=nms_server.tacacs.username,
                                            password=nms_server.passwords.linux)

        self.parent.parameters.update(driver = driver)
        self.parent.parameters.update(nms_server = nms_server)
        self.parent.parameters.update(nms_ip = nms_ip)
        self.parent.parameters.update(username = username)
        self.parent.parameters.update(password = password)
        self.parent.parameters.update(test_start_time = test_utils.get_utc_curr_time())

#1
class validate_label_from_show_filter(aetest.Testcase):
    @aetest.test
    def validate_label_from_show_filter(self, driver):

        # return True
        fail_flag = False
        last_line_number = test_utils.read_remote_logs(remote_ssh_client=nms_ssh_client, log_file=log_file, get_last_line=True)[0].rstrip()

        try:
            driver_utils.navigate_to_home()
            field_dev = ui_common_utils1.FieldDevices(driver)
            field_dev.nav_sub_menu('field_devices')
            time.sleep(1)

            item_slection_message = driver.find_element_by_xpath('//div[contains(text(), "Items selected")]')
            search_input = driver.find_element_by_xpath('//input[contains(@class, "x-form-text x-form-field x-box-item")]')
            search_input.clear()

            log.info('Searching device with "up" status.')
            search_input.send_keys('deviceCategory:router status:up')
            time.sleep(1)
            log.info('\nClicking on the Search Devices button.')
            driver.find_element_by_xpath('//table[contains(@class, "x-btn fa fa-search")]').click()
            time.sleep(2)

            log.info('Click checkbox of device with Up Status.')
            check_elem = driver.find_element_by_xpath(
                '//span[contains(@class, "icon-up")]/../../preceding-sibling::td[contains(@class, "x-grid3-td-checker")]/div/div')
            check_elem.click()
            time.sleep(2)

            log.info(banner('Checking Label.'))
            label_operation_completed = field_dev.label_operation('add', 'test_label')
            time.sleep(3)

            log.info('Added test label: %s' % label_operation_completed)
            if not label_operation_completed: raise Exception('Unable to add label')

            log.info('Verify the combo box')
            field_dev.search_devices('Label', search_value='test_label')
            time.sleep(1)

            expected_fun_value = 'label:%s'%'test_label'
            current_fun_value = driver.execute_script('function searchQuery(){\
                                        return $("#filterCtrl").find ("input:visible")[0].value} return searchQuery()')

            log.info('Clearing exiting search filter content.')
            search_box = driver.execute_script('return $("input.x-box-item:visible")[0]')
            search_box.clear()

            log.info('Clicking on Hide Filter button.')
            driver.execute_script('if($(\'a:contains("Hide Filters")\').length>0)$(\'a:contains("Hide Filters")\')[0].click()')
            time.sleep(1) 

            log.info('Expected value: %s \nCurrent value: %s' % (expected_fun_value, current_fun_value))
            if expected_fun_value == current_fun_value:
                log.info('Expected_value == Current_value : %s'%
                        str(expected_fun_value == current_fun_value))
            else:
                self.failed('expected value is not same as current value')  

        except Exception as e:
            log.error(e)
            fail_flag=True
            driver_utils.save_screenshot(scriptname='Show_filter_combo_box', classname=__class__.__name__)
            driver.refresh()
            time.sleep(5)

        finally:
            log.info('Click checkbox of device with Up Status.')
            check_elem = driver.find_element_by_xpath(
                '//span[contains(@class, "icon-up")]/../../preceding-sibling::td[contains(@class, "x-grid3-td-checker")]/div/div')
            check_elem.click()
            time.sleep(2)
            log.info('Device Selected: %s' % item_slection_message.is_displayed())

            label_operation_completed = field_dev.label_operation('remove', 'test_label')
            log.info('Removed test label: %s' % label_operation_completed)
            if not label_operation_completed: raise Exception('Unable to remove label') 

        fail_test = test_utils.forensic_test(nms_ssh_client, log_file, last_line_number, fail_flag,
                                             grep_moudle=grep_moudle)
        if fail_test: self.failed()

#2
class validate_category_in_show_filter(aetest.Testcase):
    @aetest.test
    def validate_category_in_show_filter(self, driver):

        # return True
        fail_flag = False
        last_line_number = test_utils.read_remote_logs(remote_ssh_client=nms_ssh_client, log_file=log_file, get_last_line=True)[0].rstrip()
        try:

            driver_utils.navigate_to_home()
            field_dev = ui_common_utils1.FieldDevices(driver)
            field_dev.nav_sub_menu('field_devices')
            time.sleep(1)    
            field_dev.search_devices('Category', search_value=cat_val)
            time.sleep(1)

            expected_fun_value = 'deviceCategory:%s'%cat_val
            current_fun_value = driver.execute_script('function searchQuery(){\
                                        return $("#filterCtrl").find ("input:visible")[0].value} return searchQuery()')

            log.info('Clearing exiting search filter content.')
            search_box = driver.execute_script('return $("input.x-box-item:visible")[0]')
            search_box.clear()

            log.info('Clicking on Hide Filter button.')
            driver.execute_script('if($(\'a:contains("Hide Filters")\').length>0)$(\'a:contains("Hide Filters")\')[0].click()')
            time.sleep(1)   

            log.info('Expected value: %s \nCurrent value: %s' % (expected_fun_value, current_fun_value))
            if expected_fun_value == current_fun_value:
                log.info('Expected_value == Current_value : %s'%
                        str(expected_fun_value == current_fun_value))
            else:
                self.failed('expected value is not same as current value') 

        except Exception as e:
            log.error(e)
            fail_flag=True
            driver_utils.save_screenshot(scriptname='Show_filter_combo_box', classname=__class__.__name__)
            driver.refresh()
            time.sleep(5)

        fail_test = test_utils.forensic_test(nms_ssh_client, log_file, last_line_number, fail_flag,
                                             grep_moudle=grep_moudle)
        if fail_test: self.failed() 

#3
class validate_eid_in_show_filter(aetest.Testcase):
    @aetest.test
    def validate_eid_in_show_filter(self, driver):

        # return True
        fail_flag = False
        last_line_number = test_utils.read_remote_logs(remote_ssh_client=nms_ssh_client, log_file=log_file, get_last_line=True)[0].rstrip()
        try:

            field_dev = ui_common_utils1.FieldDevices(driver) 
            field_dev.search_devices('EID', search_value=eid_val)
            time.sleep(1)

            expected_fun_value = 'eid:%s'%eid_val
            current_fun_value = driver.execute_script('function searchQuery(){\
                                        return $("#filterCtrl").find ("input:visible")[0].value} return searchQuery()')

            log.info('Clearing exiting search filter content.')
            search_box = driver.execute_script('return $("input.x-box-item:visible")[0]')
            search_box.clear()

            log.info('Clicking on Hide Filter button.')
            driver.execute_script('if($(\'a:contains("Hide Filters")\').length>0)$(\'a:contains("Hide Filters")\')[0].click()')
            time.sleep(1)  

            log.info('Expected value: %s \nCurrent value: %s' % (expected_fun_value, current_fun_value))
            if expected_fun_value == current_fun_value:
                log.info('Expected_value == Current_value : %s'%
                        str(expected_fun_value == current_fun_value))
            else:
                self.failed('expected value is not same as current value') 

        except Exception as e:
            log.error(e)
            fail_flag=True
            driver_utils.save_screenshot(scriptname='Show_filter_combo_box', classname=__class__.__name__)
            driver.refresh()
            time.sleep(5)

        fail_test = test_utils.forensic_test(nms_ssh_client, log_file, last_line_number, fail_flag,
                                             grep_moudle=grep_moudle)
        if fail_test: self.failed()  

#4
class validate_status_in_show_filter(aetest.Testcase):
    @aetest.test
    def validate_status_in_show_filter(self, driver):

        # return True
        fail_flag = False
        last_line_number = test_utils.read_remote_logs(remote_ssh_client=nms_ssh_client, log_file=log_file, get_last_line=True)[0].rstrip()

        try:
            field_dev = ui_common_utils1.FieldDevices(driver)
            field_dev.search_devices('Status', search_value=stat_val)
            time.sleep(1)

            expected_fun_value = 'status:%s'%stat_val
            current_fun_value = driver.execute_script('function searchQuery(){\
                                        return $("#filterCtrl").find ("input:visible")[0].value} return searchQuery()')

            log.info('Clearing exiting search filter content.')
            search_box = driver.execute_script('return $("input.x-box-item:visible")[0]')
            search_box.clear()

            log.info('Clicking on Hide Filter button.')
            driver.execute_script('if($(\'a:contains("Hide Filters")\').length>0)$(\'a:contains("Hide Filters")\')[0].click()')
            time.sleep(1)  

            log.info('Expected value: %s \nCurrent value: %s' % (expected_fun_value, current_fun_value))
            if expected_fun_value == current_fun_value:
                log.info('Expected_value == Current_value : %s'%
                        str(expected_fun_value == current_fun_value))
            else:
                self.failed('expected value is not same as current value') 

        except Exception as e:
            log.error(e)
            fail_flag=True
            driver_utils.save_screenshot(scriptname='Show_filter_combo_box', classname=__class__.__name__)
            driver.refresh()
            time.sleep(5)

        fail_test = test_utils.forensic_test(nms_ssh_client, log_file, last_line_number, fail_flag,
                                             grep_moudle=grep_moudle)
        if fail_test: self.failed()

#5
class validate_type_in_show_filter(aetest.Testcase):
    @aetest.test
    def validate_type_in_show_filter(self, driver):

        # return True
        fail_flag = False
        last_line_number = test_utils.read_remote_logs(remote_ssh_client=nms_ssh_client, log_file=log_file, get_last_line=True)[0].rstrip()

        try:

            field_dev = ui_common_utils1.FieldDevices(driver)
            field_dev.search_devices('Type', search_value=typ_val)
            time.sleep(1)

            expected_fun_value = 'deviceType:%s'%typ_val
            current_fun_value = driver.execute_script('function searchQuery(){\
                                        return $("#filterCtrl").find ("input:visible")[0].value} return searchQuery()')

            log.info('Clearing exiting search filter content.')
            search_box = driver.execute_script('return $("input.x-box-item:visible")[0]')
            search_box.clear()

            log.info('Clicking on Hide Filter button.')
            driver.execute_script('if($(\'a:contains("Hide Filters")\').length>0)$(\'a:contains("Hide Filters")\')[0].click()')
            time.sleep(1)  

            log.info('Expected value: %s \nCurrent value: %s' % (expected_fun_value, current_fun_value))
            if expected_fun_value == current_fun_value:
                log.info('Expected_value == Current_value : %s'%
                        str(expected_fun_value == current_fun_value))
            else:
                self.failed('expected value is not same as current value') 

        except Exception as e:
            log.error(e)
            fail_flag=True
            driver_utils.save_screenshot(scriptname='Show_filter_combo_box', classname=__class__.__name__)
            driver.refresh()
            time.sleep(5)

        fail_test = test_utils.forensic_test(nms_ssh_client, log_file, last_line_number, fail_flag,
                                             grep_moudle=grep_moudle)
        if fail_test: self.failed()

#6
class validate_ip_in_show_filter(aetest.Testcase):
    @aetest.test
    def validate_ip_in_show_filter(self, driver):

        # return True
        fail_flag = False
        last_line_number = test_utils.read_remote_logs(remote_ssh_client=nms_ssh_client, log_file=log_file, get_last_line=True)[0].rstrip()

        try:

            field_dev = ui_common_utils1.FieldDevices(driver)
            field_dev.search_devices('IP', search_value=ip_val)
            time.sleep(1)

            expected_fun_value = 'ip:%s'%ip_val
            current_fun_value = driver.execute_script('function searchQuery(){\
                                        return $("#filterCtrl").find ("input:visible")[0].value} return searchQuery()')

            log.info('Clearing exiting search filter content.')
            search_box = driver.execute_script('return $("input.x-box-item:visible")[0]')
            search_box.clear()

            log.info('Clicking on Hide Filter button.')
            driver.execute_script('if($(\'a:contains("Hide Filters")\').length>0)$(\'a:contains("Hide Filters")\')[0].click()')
            time.sleep(1)  

            log.info('Expected value: %s \nCurrent value: %s' % (expected_fun_value, current_fun_value))
            if expected_fun_value == current_fun_value:
                log.info('Expected_value == Current_value : %s'%
                        str(expected_fun_value == current_fun_value))
            else:
                self.failed('expected value is not same as current value') 

        except Exception as e:
            log.error(e)
            fail_flag=True
            driver_utils.save_screenshot(scriptname='Show_filter_combo_box', classname=__class__.__name__)
            driver.refresh()
            time.sleep(5)

        fail_test = test_utils.forensic_test(nms_ssh_client, log_file, last_line_number, fail_flag,
                                             grep_moudle=grep_moudle)
        if fail_test: self.failed()  

#7
class validate_config_group_in_show_filter(aetest.Testcase):
    @aetest.test
    def validate_config_group_in_show_filter(self, driver):

        # return True
        fail_flag = False
        last_line_number = test_utils.read_remote_logs(remote_ssh_client=nms_ssh_client, log_file=log_file, get_last_line=True)[0].rstrip()

        try:

            field_dev = ui_common_utils1.FieldDevices(driver)
            field_dev.nav_sub_menu('field_devices')
            time.sleep(1)  

            log.info('Navigating to router group: CGR1000')
            field_dev.nav_router_group('CGR1000')
            time.sleep(2)    

            radioButton = driver.find_elements_by_class_name("x-grid3-row-checker")
            cgrcount = len(radioButton)
            cgroup_val = 'default-cgr1000(' + str(cgrcount) + ')  [default]'

            field_dev.search_devices('Config Group', search_value=cgroup_val)
            time.sleep(1)
            
            expected_fun_value = 'configGroup:%s'%'default-cgr1000'
            current_fun_value = driver.execute_script('function searchQuery(){\
                                        return $("#filterCtrl").find ("input:visible")[0].value} return searchQuery()')

            log.info('Clearing exiting search filter content.')
            search_box = driver.execute_script('return $("input.x-box-item:visible")[0]')
            search_box.clear()

            log.info('Clicking on Hide Filter button.')
            driver.execute_script('if($(\'a:contains("Hide Filters")\').length>0)$(\'a:contains("Hide Filters")\')[0].click()')
            time.sleep(1)  

            log.info('Expected value: %s \nCurrent value: %s' % (expected_fun_value, current_fun_value))
            if expected_fun_value == current_fun_value:
                log.info('Expected_value == Current_value : %s'%
                        str(expected_fun_value == current_fun_value))
            else:
                self.failed('expected value is not same as current value') 

        except Exception as e:
            log.error(e)
            fail_flag=True
            driver_utils.save_screenshot(scriptname='Show_filter_combo_box', classname=__class__.__name__)
            driver.refresh()
            time.sleep(5)

        fail_test = test_utils.forensic_test(nms_ssh_client, log_file, last_line_number, fail_flag,
                                             grep_moudle=grep_moudle)
        if fail_test: self.failed()  

#8
class validate_name_in_show_filter(aetest.Testcase):
    @aetest.test
    def validate_name_in_show_filter(self, driver):

        # return True
        fail_flag = False
        last_line_number = test_utils.read_remote_logs(remote_ssh_client=nms_ssh_client, log_file=log_file, get_last_line=True)[0].rstrip()

        try:

            field_dev = ui_common_utils1.FieldDevices(driver)
            field_dev.nav_sub_menu('field_devices')
            time.sleep(1)

            field_dev.search_devices('Name', search_value=name_val)
            time.sleep(1)

            expected_fun_value = 'name:%s'%name_val
            current_fun_value = driver.execute_script('function searchQuery(){\
                                        return $("#filterCtrl").find ("input:visible")[0].value} return searchQuery()')

            log.info('Clearing exiting search filter content.')
            search_box = driver.execute_script('return $("input.x-box-item:visible")[0]')
            search_box.clear()

            log.info('Clicking on Hide Filter button.')
            driver.execute_script('if($(\'a:contains("Hide Filters")\').length>0)$(\'a:contains("Hide Filters")\')[0].click()')
            time.sleep(1)

            log.info('Expected value: %s \nCurrent value: %s' % (expected_fun_value, current_fun_value))
            if expected_fun_value == current_fun_value:
                log.info('Expected_value == Current_value : %s'%
                        str(expected_fun_value == current_fun_value))
            else:
                self.failed('expected value is not same as current value') 

        except Exception as e:
            log.error(e)
            fail_flag=True
            driver_utils.save_screenshot(scriptname='Show_filter_combo_box', classname=__class__.__name__)
            driver.refresh()
            time.sleep(5)

        fail_test = test_utils.forensic_test(nms_ssh_client, log_file, last_line_number, fail_flag,
                                             grep_moudle=grep_moudle)
        if fail_test: self.failed()

#9
class validate_function_in_show_filter(aetest.Testcase):
    @aetest.test
    def validate_function_in_show_filter(self, driver):

        # return True
        fail_flag = False
        last_line_number = test_utils.read_remote_logs(remote_ssh_client=nms_ssh_client, log_file=log_file, get_last_line=True)[0].rstrip()

        try:

            field_dev = ui_common_utils1.FieldDevices(driver)
            field_dev.search_devices('Function', search_value=func_val)
            time.sleep(1)

            expected_fun_value = 'function:%s'%func_val
            current_fun_value = driver.execute_script('function searchQuery(){\
                                        return $("#filterCtrl").find ("input:visible")[0].value} return searchQuery()')

            log.info('Clearing exiting search filter content.')
            search_box = driver.execute_script('return $("input.x-box-item:visible")[0]')
            search_box.clear()

            log.info('Clicking on Hide Filter button.')
            driver.execute_script('if($(\'a:contains("Hide Filters")\').length>0)$(\'a:contains("Hide Filters")\')[0].click()')
            time.sleep(1)

            log.info('Expected value: %s \nCurrent value: %s' % (expected_fun_value, current_fun_value))
            if expected_fun_value == current_fun_value:
                log.info('Expected_value == Current_value : %s'%
                        str(expected_fun_value == current_fun_value))
            else:
                self.failed('expected value is not same as current value') 

        except Exception as e:
            log.error(e)
            fail_flag=True
            driver_utils.save_screenshot(scriptname='Show_filter_combo_box', classname=__class__.__name__)
            driver.refresh()
            time.sleep(5)

        fail_test = test_utils.forensic_test(nms_ssh_client, log_file, last_line_number, fail_flag,
                                             grep_moudle=grep_moudle)
        if fail_test: self.failed()

#10
class validate_firmware_in_show_filter(aetest.Testcase):
    @aetest.test
    def validate_firmware_in_show_filter(self, driver):

        # return True
        fail_flag = False
        last_line_number = test_utils.read_remote_logs(remote_ssh_client=nms_ssh_client, log_file=log_file, get_last_line=True)[0].rstrip()

        try:

            field_dev = ui_common_utils1.FieldDevices(driver)
            field_dev.search_devices('Firmware', search_value=firmw_val)
            time.sleep(1)

            expected_fun_value = 'runningFirmwareVersion:%s'%firmw_val
            current_fun_value = driver.execute_script('function searchQuery(){\
                                        return $("#filterCtrl").find ("input:visible")[0].value} return searchQuery()')

            log.info('Clearing exiting search filter content.')
            search_box = driver.execute_script('return $("input.x-box-item:visible")[0]')
            search_box.clear()

            log.info('Clicking on Hide Filter button.')
            driver.execute_script('if($(\'a:contains("Hide Filters")\').length>0)$(\'a:contains("Hide Filters")\')[0].click()')
            time.sleep(1)

            log.info('Expected value: %s \nCurrent value: %s' % (expected_fun_value, current_fun_value))
            if expected_fun_value == current_fun_value:
                log.info('Expected_value == Current_value : %s'%
                        str(expected_fun_value == current_fun_value))
            else:
                self.failed('expected value is not same as current value') 

        except Exception as e:
            log.error(e)
            fail_flag=True
            driver_utils.save_screenshot(scriptname='Show_filter_combo_box', classname=__class__.__name__)
            driver.refresh()
            time.sleep(5)

        fail_test = test_utils.forensic_test(nms_ssh_client, log_file, last_line_number, fail_flag,
                                             grep_moudle=grep_moudle)
        if fail_test: self.failed()

#11
class validate_firmware_group_in_show_filter(aetest.Testcase):
    @aetest.test
    def validate_firmware_group_in_show_filter(self, driver):

        # return True
        fail_flag = False
        last_line_number = test_utils.read_remote_logs(remote_ssh_client=nms_ssh_client, log_file=log_file, get_last_line=True)[0].rstrip()

        try:

            field_dev = ui_common_utils1.FieldDevices(driver)
            field_dev.nav_sub_menu('field_devices')
            time.sleep(1)

            log.info('Navigating to router group: CGR1000')
            field_dev.nav_router_group('CGR1000')
            time.sleep(2)

            log.info('Get the number of CGR1000 counts') 
            radioButton = driver.find_elements_by_class_name("x-grid3-row-checker")
            cgrcount = len(radioButton)
            fgroup_val = 'default-cgr1000(' + str(cgrcount) + ')  [default]'

            field_dev.search_devices('Firmware Group', search_value=fgroup_val)
            time.sleep(1)

            expected_fun_value = 'firmwareGroup:%s'%'default-cgr1000'
            current_fun_value = driver.execute_script('function searchQuery(){\
                                        return $("#filterCtrl").find ("input:visible")[0].value} return searchQuery()')

            log.info('Clearing exiting search filter content.')
            search_box = driver.execute_script('return $("input.x-box-item:visible")[0]')
            search_box.clear()

            log.info('Clicking on Hide Filter button.')
            driver.execute_script('if($(\'a:contains("Hide Filters")\').length>0)$(\'a:contains("Hide Filters")\')[0].click()')
            time.sleep(1)

            log.info('Expected value: %s \nCurrent value: %s' % (expected_fun_value, current_fun_value))
            if expected_fun_value == current_fun_value:
                log.info('Expected_value == Current_value : %s'%
                        str(expected_fun_value == current_fun_value))
            else:
                self.failed('expected value is not same as current value')   

        except Exception as e:
            log.error(e)
            fail_flag=True
            driver_utils.save_screenshot(scriptname='Show_filter_combo_box', classname=__class__.__name__)
            driver.refresh()
            time.sleep(5)

        fail_test = test_utils.forensic_test(nms_ssh_client, log_file, last_line_number, fail_flag,
                                             grep_moudle=grep_moudle)
        if fail_test: self.failed()  

#12
class validate_tunnel_group_in_show_filter(aetest.Testcase):
    @aetest.test
    def validate_tunnel_group_in_show_filter(self, driver):

        # return True
        fail_flag = False
        last_line_number = test_utils.read_remote_logs(remote_ssh_client=nms_ssh_client, log_file=log_file, get_last_line=True)[0].rstrip()

        try:

            field_dev = ui_common_utils1.FieldDevices(driver)
            field_dev.nav_sub_menu('field_devices')
            time.sleep(1)
            field_dev.search_devices('Tunnel Group', search_value=tgroup_val)
            time.sleep(1)
            if tgroup_val == 'default-cgr1000[root] [default]': tgrp_val = 'default-cgr1000 domain:root'
            expected_fun_value = 'tunnelGroup:%s'%tgrp_val
            current_fun_value = driver.execute_script('function searchQuery(){\
                                        return $("#filterCtrl").find ("input:visible")[0].value} return searchQuery()')

            log.info('Clearing exiting search filter content.')
            search_box = driver.execute_script('return $("input.x-box-item:visible")[0]')
            search_box.clear()

            log.info('Clicking on Hide Filter button.')
            driver.execute_script('if($(\'a:contains("Hide Filters")\').length>0)$(\'a:contains("Hide Filters")\')[0].click()')
            time.sleep(1)

            log.info('Expected value: %s \nCurrent value: %s' % (expected_fun_value, current_fun_value))
            if expected_fun_value == current_fun_value:
                log.info('Expected_value == Current_value : %s'%
                        str(expected_fun_value == current_fun_value))
            else:
                self.failed('expected value is not same as current value') 

        except Exception as e:
            log.error(e)
            fail_flag=True
            driver_utils.save_screenshot(scriptname='Show_filter_combo_box', classname=__class__.__name__)
            driver.refresh()
            time.sleep(5)

        fail_test = test_utils.forensic_test(nms_ssh_client, log_file, last_line_number, fail_flag,
                                             grep_moudle=grep_moudle)
        if fail_test: self.failed()  

#13
class validate_model_number_in_show_filter(aetest.Testcase):
    @aetest.test
    def validate_model_number_in_show_filter(self, driver):

        # return True
        fail_flag = False
        last_line_number = test_utils.read_remote_logs(remote_ssh_client=nms_ssh_client, log_file=log_file, get_last_line=True)[0].rstrip()

        try:

            field_dev = ui_common_utils1.FieldDevices(driver)
            field_dev.search_devices('Model Number', search_value=model_var)
            time.sleep(1)

            expected_fun_value = 'pid:%s'%model_var
            current_fun_value = driver.execute_script('function searchQuery(){\
                                        return $("#filterCtrl").find ("input:visible")[0].value} return searchQuery()')

            log.info('Clearing exiting search filter content.')
            search_box = driver.execute_script('return $("input.x-box-item:visible")[0]')
            search_box.clear()

            log.info('Clicking on Hide Filter button.')
            driver.execute_script('if($(\'a:contains("Hide Filters")\').length>0)$(\'a:contains("Hide Filters")\')[0].click()')
            time.sleep(1)

            log.info('Expected value: %s \nCurrent value: %s' % (expected_fun_value, current_fun_value))
            if expected_fun_value == current_fun_value:
                log.info('Expected_value == Current_value : %s'%
                        str(expected_fun_value == current_fun_value))
            else:
                self.failed('expected value is not same as current value') 

        except Exception as e:
            log.error(e)
            fail_flag=True
            driver_utils.save_screenshot(scriptname='Show_filter_combo_box', classname=__class__.__name__)
            driver.refresh()
            time.sleep(5)

        fail_test = test_utils.forensic_test(nms_ssh_client, log_file, last_line_number, fail_flag,
                                             grep_moudle=grep_moudle)
        if fail_test: self.failed()      

#14
class validate_serial_number_in_show_filter(aetest.Testcase):
    @aetest.test
    def validate_serial_number_in_show_filter(self, driver):

        # return True
        fail_flag = False
        last_line_number = test_utils.read_remote_logs(remote_ssh_client=nms_ssh_client, log_file=log_file, get_last_line=True)[0].rstrip()

        try:

            field_dev = ui_common_utils1.FieldDevices(driver)
            field_dev.search_devices('Serial Number', search_value=serial_val)
            time.sleep(1)

            expected_fun_value = 'sn:%s'%serial_val
            current_fun_value = driver.execute_script('function searchQuery(){\
                                        return $("#filterCtrl").find ("input:visible")[0].value} return searchQuery()')

            log.info('Clearing exiting search filter content.')
            search_box = driver.execute_script('return $("input.x-box-item:visible")[0]')
            search_box.clear()

            log.info('Clicking on Hide Filter button.')
            driver.execute_script('if($(\'a:contains("Hide Filters")\').length>0)$(\'a:contains("Hide Filters")\')[0].click()')
            time.sleep(1)

            log.info('Expected value: %s \nCurrent value: %s' % (expected_fun_value, current_fun_value))
            if expected_fun_value == current_fun_value:
                log.info('Expected_value == Current_value : %s'%
                        str(expected_fun_value == current_fun_value))
            else:
                self.failed('expected value is not same as current value') 

        except Exception as e:
            log.error(e)
            fail_flag=True
            driver_utils.save_screenshot(scriptname='Show_filter_combo_box', classname=__class__.__name__)
            driver.refresh()
            time.sleep(5)

        fail_test = test_utils.forensic_test(nms_ssh_client, log_file, last_line_number, fail_flag,
                                             grep_moudle=grep_moudle)
        if fail_test: self.failed()  

#15
class validate_her_model_number_in_show_filter(aetest.Testcase):
    @aetest.test
    def validate_her_model_number_in_show_filter(self, driver):

        # return True
        fail_flag = False
        last_line_number = test_utils.read_remote_logs(remote_ssh_client=nms_ssh_client, log_file=log_file, get_last_line=True)[0].rstrip()

        try:
            driver_utils.navigate_to_home()
            her_dev = ui_common_utils1.HER_Devices(driver)
            her_dev.nav_sub_menu('head_end_routers')
            her_dev.search_devices('Model Number', seach_value=model_var)
            time.sleep(1)

            expected_fun_value = 'pid:%s'%model_var
            current_fun_value = driver.execute_script('function searchQuery(){\
                                        return $("#filterCtrl").find ("input:visible")[0].value} return searchQuery()')

            log.info('Clearing exiting search filter content.')
            search_box = driver.execute_script('return $("input.x-box-item:visible")[0]')
            search_box.clear()

            log.info('Clicking on Hide Filter button.')
            driver.execute_script('if($(\'a:contains("Hide Filters")\').length>0)$(\'a:contains("Hide Filters")\')[0].click()')
            time.sleep(1)

            log.info('Expected value: %s \nCurrent value: %s' % (expected_fun_value, current_fun_value))
            if expected_fun_value == current_fun_value:
                log.info('Expected_value == Current_value : %s'%
                        str(expected_fun_value == current_fun_value))
            else:
                self.failed('expected value is not same as current value') 

        except Exception as e:
            log.error(e)
            fail_flag=True
            driver_utils.save_screenshot(scriptname='Show_filter_combo_box', classname=__class__.__name__)
            driver.refresh()
            time.sleep(5)

        fail_test = test_utils.forensic_test(nms_ssh_client, log_file, last_line_number, fail_flag,
                                             grep_moudle=grep_moudle)
        if fail_test: self.failed()  

#16
class validate_her_serial_number_in_show_filter(aetest.Testcase):
    @aetest.test
    def validate_her_serial_number_in_show_filter(self, driver):

        # return True
        fail_flag = False
        last_line_number = test_utils.read_remote_logs(remote_ssh_client=nms_ssh_client, log_file=log_file, get_last_line=True)[0].rstrip()

        try:
            her_dev = ui_common_utils1.HER_Devices(driver)
            her_dev.search_devices('Serial Number', seach_value=serial_val)
            time.sleep(1)

            expected_fun_value = 'sn:%s'%serial_val
            current_fun_value = driver.execute_script('function searchQuery(){\
                                        return $("#filterCtrl").find ("input:visible")[0].value} return searchQuery()')

            log.info('Clearing exiting search filter content.')
            search_box = driver.execute_script('return $("input.x-box-item:visible")[0]')
            search_box.clear()

            log.info('Clicking on Hide Filter button.')
            driver.execute_script('if($(\'a:contains("Hide Filters")\').length>0)$(\'a:contains("Hide Filters")\')[0].click()')
            time.sleep(1)

            log.info('Expected value: %s \nCurrent value: %s' % (expected_fun_value, current_fun_value))
            if expected_fun_value == current_fun_value:
                log.info('Expected_value == Current_value : %s'%
                        str(expected_fun_value == current_fun_value))
            else:
                self.failed('expected value is not same as current value') 

        except Exception as e:
            log.error(e)
            fail_flag=True
            driver_utils.save_screenshot(scriptname='Show_filter_combo_box', classname=__class__.__name__)
            driver.refresh()
            time.sleep(5)

        fail_test = test_utils.forensic_test(nms_ssh_client, log_file, last_line_number, fail_flag,
                                             grep_moudle=grep_moudle)
        if fail_test: self.failed()

#17
class validate_her_label_from_show_filter(aetest.Testcase):
    @aetest.test
    def validate_her_label_from_show_filter(self, driver):

        # return True
        fail_flag = False
        last_line_number = test_utils.read_remote_logs(remote_ssh_client=nms_ssh_client, log_file=log_file, get_last_line=True)[0].rstrip()

        try:

            her_dev = ui_common_utils1.HER_Devices(driver)
            her_dev.nav_sub_menu('head_end_routers')       
            time.sleep(1)
            item_slection_message = driver.find_element_by_xpath('//div[contains(text(), "Items selected")]')
            search_input = driver.find_element_by_xpath('//input[contains(@class, "x-form-text x-form-field x-box-item")]')

            search_input.clear()
            time.sleep(1)
            search_input.send_keys('deviceCategory:her status:up')
            time.sleep(1)
            log.info('\nClicking on the Search Devices button.')
            driver.find_element_by_xpath('//table[contains(@class, "x-btn fa fa-search")]').click()
            time.sleep(2)

            log.info('Click checkbox of device with Up Status.')
            check_elem = driver.find_element_by_xpath(
                '//span[contains(@class, "icon-up")]/../../preceding-sibling::td[contains(@class, "x-grid3-td-checker")]/div/div')
            check_elem.click()
            time.sleep(2)

            log.info(banner('Verifying Label.'))
            label_operation_completed = her_dev.label_operation('add', 'test_label1')
            time.sleep(3)

            log.info('Added test label: %s' % label_operation_completed)
            if not label_operation_completed: raise Exception('Unable to add label')        

            log.info('Verify the combo box')
            her_dev.search_devices('Label', seach_value='test_label1')
            time.sleep(1)

            expected_fun_value = 'label:%s'%'test_label1'
            current_fun_value = driver.execute_script('function searchQuery(){\
                                        return $("#filterCtrl").find ("input:visible")[0].value} return searchQuery()')

            log.info('Clearing exiting search filter content.')
            search_box = driver.execute_script('return $("input.x-box-item:visible")[0]')
            search_box.clear()

            log.info('Clicking on Hide Filter button.')
            driver.execute_script('if($(\'a:contains("Hide Filters")\').length>0)$(\'a:contains("Hide Filters")\')[0].click()')
            time.sleep(1)

            log.info('Expected value: %s \nCurrent value: %s' % (expected_fun_value, current_fun_value))
            if expected_fun_value == current_fun_value:
                log.info('Expected_value == Current_value : %s'%
                        str(expected_fun_value == current_fun_value))
            else:
                self.failed('expected value is not same as current value')   

        except Exception as e:
            log.error(e)
            fail_flag=True
            driver_utils.save_screenshot(scriptname='Show_filter_combo_box', classname=__class__.__name__)  
            driver.refresh()
            time.sleep(5)

        finally:
            log.info('Click checkbox of device with Up Status.')
            check_elem = driver.find_element_by_xpath(
                '//span[contains(@class, "icon-up")]/../../preceding-sibling::td[contains(@class, "x-grid3-td-checker")]/div/div')
            check_elem.click()
            time.sleep(2)
            log.info('Device Selected: %s' % item_slection_message.is_displayed())

            label_operation_completed = her_dev.label_operation('remove', 'test_label1')
            log.info('Removed test label: %s' % label_operation_completed)
            time.sleep(3)   

        fail_test = test_utils.forensic_test(nms_ssh_client, log_file, last_line_number, fail_flag,
                                             grep_moudle=grep_moudle)
        if fail_test: self.failed() 

#18
class validate_her_category_from_show_filter(aetest.Testcase):
    @aetest.test
    def validate_her_category_from_show_filter(self, driver):

        # return True
        fail_flag = False
        last_line_number = test_utils.read_remote_logs(remote_ssh_client=nms_ssh_client, log_file=log_file, get_last_line=True)[0].rstrip()

        try:
            her_dev = ui_common_utils1.HER_Devices(driver)
            her_dev.search_devices('Category', seach_value=her_cat_val)
            time.sleep(1)

            expected_fun_value = 'deviceCategory:%s'%her_cat_val
            current_fun_value = driver.execute_script('function searchQuery(){\
                                        return $("#filterCtrl").find ("input:visible")[0].value} return searchQuery()')

            log.info('Clearing exiting search filter content.')
            search_box = driver.execute_script('return $("input.x-box-item:visible")[0]')
            search_box.clear()

            log.info('Clicking on Hide Filter button.')
            driver.execute_script('if($(\'a:contains("Hide Filters")\').length>0)$(\'a:contains("Hide Filters")\')[0].click()')
            time.sleep(1)

            log.info('Expected value: %s \nCurrent value: %s' % (expected_fun_value, current_fun_value))
            if expected_fun_value == current_fun_value:
                log.info('Expected_value == Current_value : %s'%
                        str(expected_fun_value == current_fun_value))
            else:
                self.failed('expected value is not same as current value') 

        except Exception as e:
            log.error(e)
            fail_flag=True
            driver_utils.save_screenshot(scriptname='Show_filter_combo_box', classname=__class__.__name__)
            driver.refresh()
            time.sleep(5)

        fail_test = test_utils.forensic_test(nms_ssh_client, log_file, last_line_number, fail_flag,
                                             grep_moudle=grep_moudle) 
        if fail_test: self.failed() 

#19
class validate_her_eid_in_show_filter(aetest.Testcase):
    @aetest.test
    def validate_her_eid_in_show_filter(self, driver):

        # return True
        fail_flag = False
        last_line_number = test_utils.read_remote_logs(remote_ssh_client=nms_ssh_client, log_file=log_file, get_last_line=True)[0].rstrip()
        try:
            her_dev = ui_common_utils1.HER_Devices(driver)
            her_dev.search_devices('EID', seach_value=eid_val)
            time.sleep(1)

            expected_fun_value = 'eid:%s'%eid_val
            current_fun_value = driver.execute_script('function searchQuery(){\
                                        return $("#filterCtrl").find ("input:visible")[0].value} return searchQuery()')

            log.info('Clearing exiting search filter content.')
            search_box = driver.execute_script('return $("input.x-box-item:visible")[0]')
            search_box.clear()

            log.info('Clicking on Hide Filter button.')
            driver.execute_script('if($(\'a:contains("Hide Filters")\').length>0)$(\'a:contains("Hide Filters")\')[0].click()')
            time.sleep(1)

            log.info('Expected value: %s \nCurrent value: %s' % (expected_fun_value, current_fun_value))
            if expected_fun_value == current_fun_value:
                log.info('Expected_value == Current_value : %s'%
                        str(expected_fun_value == current_fun_value))
            else:
                self.failed('expected value is not same as current value') 

        except Exception as e:
            log.error(e)
            fail_flag=True
            driver_utils.save_screenshot(scriptname='Show_filter_combo_box', classname=__class__.__name__)
            driver.refresh()
            time.sleep(5)

        fail_test = test_utils.forensic_test(nms_ssh_client, log_file, last_line_number, fail_flag,
                                             grep_moudle=grep_moudle)
        if fail_test: self.failed() 

#20
class validate_her_status_in_show_filter(aetest.Testcase):
    @aetest.test
    def validate_her_status_in_show_filter(self, driver):

        # return True
        fail_flag = False
        last_line_number = test_utils.read_remote_logs(remote_ssh_client=nms_ssh_client, log_file=log_file, get_last_line=True)[0].rstrip()

        try:
            her_dev = ui_common_utils1.HER_Devices(driver)
            her_dev.search_devices('Status', seach_value=stat_val)
            time.sleep(1)

            expected_fun_value = 'status:%s'%stat_val
            current_fun_value = driver.execute_script('function searchQuery(){\
                                        return $("#filterCtrl").find ("input:visible")[0].value} return searchQuery()')

            log.info('Clearing exiting search filter content.')
            search_box = driver.execute_script('return $("input.x-box-item:visible")[0]')
            search_box.clear()

            log.info('Clicking on Hide Filter button.')
            driver.execute_script('if($(\'a:contains("Hide Filters")\').length>0)$(\'a:contains("Hide Filters")\')[0].click()')
            time.sleep(1)

            log.info('Expected value: %s \nCurrent value: %s' % (expected_fun_value, current_fun_value))
            if expected_fun_value == current_fun_value:
                log.info('Expected_value == Current_value : %s'%
                        str(expected_fun_value == current_fun_value))
            else:
                self.failed('expected value is not same as current value') 

        except Exception as e:
            log.error(e)
            fail_flag=True
            driver_utils.save_screenshot(scriptname='Show_filter_combo_box', classname=__class__.__name__)
            driver.refresh()
            time.sleep(5)

        fail_test = test_utils.forensic_test(nms_ssh_client, log_file, last_line_number, fail_flag,
                                             grep_moudle=grep_moudle)
        if fail_test: self.failed()  

#21
class validate_her_type_in_show_filter(aetest.Testcase):
    @aetest.test
    def validate_her_type_in_show_filter(self, driver):

        # return True
        fail_flag = False
        last_line_number = test_utils.read_remote_logs(remote_ssh_client=nms_ssh_client, log_file=log_file, get_last_line=True)[0].rstrip()

        try:

            her_dev = ui_common_utils1.HER_Devices(driver)
            her_dev.search_devices('Type', seach_value=her_typ_val)
            time.sleep(1)

            expected_fun_value = 'deviceType:%s'%her_typ_val
            current_fun_value = driver.execute_script('function searchQuery(){\
                                        return $("#filterCtrl").find ("input:visible")[0].value} return searchQuery()')

            log.info('Clearing exiting search filter content.')
            search_box = driver.execute_script('return $("input.x-box-item:visible")[0]')
            search_box.clear()

            log.info('Clicking on Hide Filter button.')
            driver.execute_script('if($(\'a:contains("Hide Filters")\').length>0)$(\'a:contains("Hide Filters")\')[0].click()')
            time.sleep(1)

            log.info('Expected value: %s \nCurrent value: %s' % (expected_fun_value, current_fun_value))
            if expected_fun_value == current_fun_value:
                log.info('Expected_value == Current_value : %s'%
                        str(expected_fun_value == current_fun_value))
            else:
                self.failed('expected value is not same as current value') 

        except Exception as e:
            log.error(e)
            fail_flag=True
            driver_utils.save_screenshot(scriptname='Show_filter_combo_box', classname=__class__.__name__)
            driver.refresh()
            time.sleep(5)

        fail_test = test_utils.forensic_test(nms_ssh_client, log_file, last_line_number, fail_flag,
                                             grep_moudle=grep_moudle)
        if fail_test: self.failed()  

#22
class validate_her_ip_in_show_filter(aetest.Testcase):
    @aetest.test
    def validate_her_ip_in_show_filter(self, driver):

        # return True
        fail_flag = False
        last_line_number = test_utils.read_remote_logs(remote_ssh_client=nms_ssh_client, log_file=log_file, get_last_line=True)[0].rstrip()

        try:
            her_dev = ui_common_utils1.HER_Devices(driver)
            her_dev.search_devices('IP', seach_value=ip_val)
            time.sleep(1)

            expected_fun_value = 'ip:%s'%ip_val
            current_fun_value = driver.execute_script('function searchQuery(){\
                                        return $("#filterCtrl").find ("input:visible")[0].value} return searchQuery()')

            log.info('Clearing exiting search filter content.')
            search_box = driver.execute_script('return $("input.x-box-item:visible")[0]')
            search_box.clear()

            log.info('Clicking on Hide Filter button.')
            driver.execute_script('if($(\'a:contains("Hide Filters")\').length>0)$(\'a:contains("Hide Filters")\')[0].click()')
            time.sleep(1)

            log.info('Expected value: %s \nCurrent value: %s' % (expected_fun_value, current_fun_value))
            if expected_fun_value == current_fun_value:
                log.info('Expected_value == Current_value : %s'%
                        str(expected_fun_value == current_fun_value))
            else:
                self.failed('expected value is not same as current value') 

        except Exception as e:
            log.error(e)
            fail_flag=True
            driver_utils.save_screenshot(scriptname='Show_filter_combo_box', classname=__class__.__name__)
            driver.refresh()
            time.sleep(5)

        fail_test = test_utils.forensic_test(nms_ssh_client, log_file, last_line_number, fail_flag,
                                             grep_moudle=grep_moudle)
        if fail_test: self.failed()       

#23
class validate_her_name_in_show_filter(aetest.Testcase):
    @aetest.test
    def validate_her_name_in_show_filter(self, driver):

        # return True
        fail_flag = False
        last_line_number = test_utils.read_remote_logs(remote_ssh_client=nms_ssh_client, log_file=log_file, get_last_line=True)[0].rstrip()

        try:

            her_dev = ui_common_utils1.HER_Devices(driver)
            her_dev.search_devices('Name', seach_value=her_name_val)
            time.sleep(1)

            expected_fun_value = 'name:%s'%her_name_val
            current_fun_value = driver.execute_script('function searchQuery(){\
                                        return $("#filterCtrl").find ("input:visible")[0].value} return searchQuery()')

            log.info('Clearing exiting search filter content.')
            search_box = driver.execute_script('return $("input.x-box-item:visible")[0]')
            search_box.clear()

            log.info('Clicking on Hide Filter button.')
            driver.execute_script('if($(\'a:contains("Hide Filters")\').length>0)$(\'a:contains("Hide Filters")\')[0].click()')
            time.sleep(1)

            log.info('Expected value: %s \nCurrent value: %s' % (expected_fun_value, current_fun_value))
            if expected_fun_value == current_fun_value:
                log.info('Expected_value == Current_value : %s'%
                        str(expected_fun_value == current_fun_value))
            else:
                self.failed('expected value is not same as current value') 

        except Exception as e:
            log.error(e)
            fail_flag=True
            driver_utils.save_screenshot(scriptname='Show_filter_combo_box', classname=__class__.__name__)
            driver.refresh()
            time.sleep(5)

        fail_test = test_utils.forensic_test(nms_ssh_client, log_file, last_line_number, fail_flag,
                                             grep_moudle=grep_moudle)
        if fail_test: self.failed() 

#24
class validate_her_function_in_show_filter(aetest.Testcase):
    @aetest.test
    def validate_her_function_in_show_filter(self, driver):

        # return True
        fail_flag = False
        last_line_number = test_utils.read_remote_logs(remote_ssh_client=nms_ssh_client, log_file=log_file, get_last_line=True)[0].rstrip()

        try:
            her_dev = ui_common_utils1.HER_Devices(driver)
            her_dev.search_devices('Function', seach_value=func_val)
            time.sleep(1)

            expected_fun_value = 'function:%s'%func_val
            current_fun_value = driver.execute_script('function searchQuery(){\
                                        return $("#filterCtrl").find ("input:visible")[0].value} return searchQuery()')

            log.info('Clearing exiting search filter content.')
            search_box = driver.execute_script('return $("input.x-box-item:visible")[0]')
            search_box.clear()

            log.info('Clicking on Hide Filter button.')
            driver.execute_script('if($(\'a:contains("Hide Filters")\').length>0)$(\'a:contains("Hide Filters")\')[0].click()')
            time.sleep(1)

            log.info('Expected value: %s \nCurrent value: %s' % (expected_fun_value, current_fun_value))
            if expected_fun_value == current_fun_value:
                log.info('Expected_value == Current_value : %s'%
                        str(expected_fun_value == current_fun_value))
            else:
                self.failed('expected value is not same as current value') 

        except Exception as e:
            log.error(e)
            fail_flag=True
            driver_utils.save_screenshot(scriptname='Show_filter_combo_box', classname=__class__.__name__)
            driver.refresh()
            time.sleep(5)

        fail_test = test_utils.forensic_test(nms_ssh_client, log_file, last_line_number, fail_flag,
                                             grep_moudle=grep_moudle)
        if fail_test: self.failed()  

#25
class validate_tunnel_admin_status_from_show_filter(aetest.Testcase):
    @aetest.test
    def validate_tunnel_admin_status_from_show_filter(self, driver):

        # return True
        fail_flag = False
        last_line_number = test_utils.read_remote_logs(remote_ssh_client=nms_ssh_client, log_file=log_file, get_last_line=True)[0].rstrip()

        try:
            driver_utils.navigate_to_home()
            tunl_dev = ui_common_utils1.TunnelStatus(driver)
            tunl_dev.nav_sub_menu('tunnel_status')
            time.sleep(1)

            tunl_dev.search_tunnels('Admin Status', stat_val)
            time.sleep(1)

            expected_fun_value = 'adminStatus:%s'%stat_val
            current_fun_value = driver.find_element_by_name('tunnelSearchQuery').get_attribute('value')

            log.info('Clearing exiting search filter content.')
            driver.find_element_by_xpath('//input[contains(@id, "tunnelSearchQuery")]').clear() 

            log.info('Clicking on Hide Filter button.')
            driver.execute_script('if($(\'a:contains("Hide Filter")\').length>0)$(\'a:contains("Hide Filter")\')[0].click()') 
            time.sleep(1)

            log.info('Expected value: %s \nCurrent_fun_value: %s' % (expected_fun_value, current_fun_value))
            if expected_fun_value == current_fun_value:
                log.info('expected_fun_value == current_fun_value : %s'%
                        str(expected_fun_value == current_fun_value))
            else:
                self.failed('expected value is not same as current value') 

        except Exception as e:
            log.error(e)
            fail_flag=True
            driver_utils.save_screenshot(scriptname='Show_filter_combo_box', classname=__class__.__name__)  
            driver.refresh()
            time.sleep(5)

        fail_test = test_utils.forensic_test(nms_ssh_client, log_file, last_line_number, fail_flag,
                                             grep_moudle=grep_moudle)
        if fail_test: self.failed()  

#26
class validate_tunnel_oper_status_from_show_filter(aetest.Testcase):
    @aetest.test
    def validate_tunnel_oper_status_from_show_filter(self, driver):

        # return True
        fail_flag = False
        last_line_number = test_utils.read_remote_logs(remote_ssh_client=nms_ssh_client, log_file=log_file, get_last_line=True)[0].rstrip()

        try:
            tunl_dev = ui_common_utils1.TunnelStatus(driver)
            tunl_dev.search_tunnels('Oper Status', stat_val)
            time.sleep(1)

            expected_fun_value = 'operStatus:%s'%stat_val
            current_fun_value = driver.find_element_by_name('tunnelSearchQuery').get_attribute('value')

            log.info('Clearing exiting search filter content.')
            driver.find_element_by_xpath('//input[contains(@id, "tunnelSearchQuery")]').clear()

            log.info('Clicking on Hide Filter button.')
            driver.execute_script('if($(\'a:contains("Hide Filter")\').length>0)$(\'a:contains("Hide Filter")\')[0].click()')
            time.sleep(1)

            log.info('Expected value: %s \nCurrent_fun_value: %s' % (expected_fun_value, current_fun_value))
            if expected_fun_value == current_fun_value:
                log.info('expected_fun_value == current_fun_value : %s'%
                        str(expected_fun_value == current_fun_value))
            else:
                self.failed('expected value is not same as current value')  

        except Exception as e:
            log.error(e)
            fail_flag=True
            driver_utils.save_screenshot(scriptname='Show_filter_combo_box', classname=__class__.__name__)
            driver.refresh()
            time.sleep(5)

        fail_test = test_utils.forensic_test(nms_ssh_client, log_file, last_line_number, fail_flag,
                                             grep_moudle=grep_moudle)                     
        if fail_test: self.failed() 

#27
class validate_tunnel_her_name_from_show_filter(aetest.Testcase):
    @aetest.test
    def validate_tunnel_her_name_from_show_filter(self, driver):

        # return True
        fail_flag = False
        last_line_number = test_utils.read_remote_logs(remote_ssh_client=nms_ssh_client, log_file=log_file, get_last_line=True)[0].rstrip()

        try:
            tunl_dev = ui_common_utils1.TunnelStatus(driver)
            tunl_dev.search_tunnels('HER Name', her_name_val)
            time.sleep(1)

            expected_fun_value = 'herName:%s'%her_name_val
            current_fun_value = driver.find_element_by_name('tunnelSearchQuery').get_attribute('value')

            log.info('Clearing exiting search filter content.')
            driver.find_element_by_xpath('//input[contains(@id, "tunnelSearchQuery")]').clear()

            log.info('Clicking on Hide Filter button.')
            driver.execute_script('if($(\'a:contains("Hide Filter")\').length>0)$(\'a:contains("Hide Filter")\')[0].click()')
            time.sleep(1)

            log.info('Expected value: %s \nCurrent_fun_value: %s' % (expected_fun_value, current_fun_value))
            if expected_fun_value == current_fun_value:
                log.info('expected_fun_value == current_fun_value : %s'%
                        str(expected_fun_value == current_fun_value))
            else:
                self.failed('expected value is not same as current value')  

        except Exception as e:
            log.error(e)
            fail_flag=True
            driver_utils.save_screenshot(scriptname='Show_filter_combo_box', classname=__class__.__name__)
            driver.refresh()
            time.sleep(5)

        fail_test = test_utils.forensic_test(nms_ssh_client, log_file, last_line_number, fail_flag,
                                             grep_moudle=grep_moudle)                     
        if fail_test: self.failed() 

#28
class validate_tunnel_her_interface_from_show_filter(aetest.Testcase):
    @aetest.test
    def validate_tunnel_her_interface_from_show_filter(self, driver):

        # return True
        fail_flag = False
        last_line_number = test_utils.read_remote_logs(remote_ssh_client=nms_ssh_client, log_file=log_file, get_last_line=True)[0].rstrip()

        try:
            tunl_dev = ui_common_utils1.TunnelStatus(driver)
            tunl_dev.search_tunnels('HER Interface', her_int_val)
            time.sleep(1)

            expected_fun_value = 'herInterface:%s'%her_int_val
            current_fun_value = driver.find_element_by_name('tunnelSearchQuery').get_attribute('value')

            log.info('Clearing exiting search filter content.')
            driver.find_element_by_xpath('//input[contains(@id, "tunnelSearchQuery")]').clear()

            log.info('Clicking on Hide Filter button.')
            driver.execute_script('if($(\'a:contains("Hide Filter")\').length>0)$(\'a:contains("Hide Filter")\')[0].click()')
            time.sleep(1)

            log.info('Expected value: %s \nCurrent_fun_value: %s' % (expected_fun_value, current_fun_value))
            if expected_fun_value == current_fun_value:
                log.info('expected_fun_value == current_fun_value : %s'%
                        str(expected_fun_value == current_fun_value))
            else:
                self.failed('expected value is not same as current value') 

        except Exception as e:
            log.error(e)
            fail_flag=True
            driver_utils.save_screenshot(scriptname='Show_filter_combo_box', classname=__class__.__name__)
            driver.refresh()
            time.sleep(5)

        fail_test = test_utils.forensic_test(nms_ssh_client, log_file, last_line_number, fail_flag,
                                             grep_moudle=grep_moudle)                     
        if fail_test: self.failed()  

#29
class validate_tunnel_protocol_from_show_filter(aetest.Testcase):
    @aetest.test
    def validate_tunnel_protocol_from_show_filter(self, driver):

        # return True
        fail_flag = False
        last_line_number = test_utils.read_remote_logs(remote_ssh_client=nms_ssh_client, log_file=log_file, get_last_line=True)[0].rstrip()

        try:
            tunl_dev = ui_common_utils1.TunnelStatus(driver)
            tunl_dev.search_tunnels('Protocol', protocol_val)
            time.sleep(1)

            expected_fun_value = 'protocol:%s'%protocol_val
            current_fun_value = driver.find_element_by_name('tunnelSearchQuery').get_attribute('value')

            log.info('Clearing exiting search filter content.')
            driver.find_element_by_xpath('//input[contains(@id, "tunnelSearchQuery")]').clear()

            log.info('Clicking on Hide Filter button.')
            driver.execute_script('if($(\'a:contains("Hide Filter")\').length>0)$(\'a:contains("Hide Filter")\')[0].click()')
            time.sleep(1)

            log.info('Expected value: %s \nCurrent_fun_value: %s' % (expected_fun_value, current_fun_value))
            if expected_fun_value == current_fun_value:
                log.info('expected_fun_value == current_fun_value : %s'%
                        str(expected_fun_value == current_fun_value))
            else:
                self.failed('expected value is not same as current value')  

        except Exception as e:
            log.error(e)
            fail_flag=True
            driver_utils.save_screenshot(scriptname='Show_filter_combo_box', classname=__class__.__name__)
            driver.refresh()
            time.sleep(5)

        fail_test = test_utils.forensic_test(nms_ssh_client, log_file, last_line_number, fail_flag,
                                             grep_moudle=grep_moudle)                     
        if fail_test: self.failed()  

#30
class validate_tunnel_ip_addr_from_show_filter(aetest.Testcase):
    @aetest.test
    def validate_tunnel_ip_addr_from_show_filter(self, driver):

        # return True
        fail_flag = False
        last_line_number = test_utils.read_remote_logs(remote_ssh_client=nms_ssh_client, log_file=log_file, get_last_line=True)[0].rstrip()

        try:
            tunl_dev = ui_common_utils1.TunnelStatus(driver)
            tunl_dev.search_tunnels('IP Address', ip_val)
            time.sleep(1)

            expected_fun_value = 'ipAddress:%s'%ip_val
            current_fun_value = driver.find_element_by_name('tunnelSearchQuery').get_attribute('value')

            log.info('Clearing exiting search filter content.')
            driver.find_element_by_xpath('//input[contains(@id, "tunnelSearchQuery")]').clear()

            log.info('Clicking on Hide Filter button.')
            driver.execute_script('if($(\'a:contains("Hide Filter")\').length>0)$(\'a:contains("Hide Filter")\')[0].click()')
            time.sleep(1)

            log.info('Expected value: %s \nCurrent_fun_value: %s' % (expected_fun_value, current_fun_value))
            if expected_fun_value == current_fun_value:
                log.info('expected_fun_value == current_fun_value : %s'%
                        str(expected_fun_value == current_fun_value))
            else:
                self.failed('expected value is not same as current value')  

        except Exception as e:
            log.error(e)
            fail_flag=True
            driver_utils.save_screenshot(scriptname='Show_filter_combo_box', classname=__class__.__name__)
            driver.refresh()
            time.sleep(5)

        fail_test = test_utils.forensic_test(nms_ssh_client, log_file, last_line_number, fail_flag,
                                             grep_moudle=grep_moudle)                     
        if fail_test: self.failed()  

#31
class validate_tunnel_far_name_from_show_filter(aetest.Testcase):
    @aetest.test
    def validate_tunnel_far_name_from_show_filter(self, driver):

        # return True
        fail_flag = False
        last_line_number = test_utils.read_remote_logs(remote_ssh_client=nms_ssh_client, log_file=log_file, get_last_line=True)[0].rstrip()

        try:
            tunl_dev = ui_common_utils1.TunnelStatus(driver)
            tunl_dev.search_tunnels('FAR Name', far_nam_val)
            time.sleep(1)

            expected_fun_value = 'farName:%s'%far_nam_val
            current_fun_value = driver.find_element_by_name('tunnelSearchQuery').get_attribute('value')

            log.info('Clearing exiting search filter content.')
            driver.find_element_by_xpath('//input[contains(@id, "tunnelSearchQuery")]').clear()

            log.info('Clicking on Hide Filter button.')
            driver.execute_script('if($(\'a:contains("Hide Filter")\').length>0)$(\'a:contains("Hide Filter")\')[0].click()')
            time.sleep(1)

            log.info('Expected value: %s \nCurrent_fun_value: %s' % (expected_fun_value, current_fun_value))
            if expected_fun_value == current_fun_value:
                log.info('expected_fun_value == current_fun_value : %s'%
                        str(expected_fun_value == current_fun_value))
            else:
                self.failed('expected value is not same as current value')  

        except Exception as e:
            log.error(e)
            fail_flag=True
            driver_utils.save_screenshot(scriptname='Show_filter_combo_box', classname=__class__.__name__)
            driver.refresh()
            time.sleep(5)

        fail_test = test_utils.forensic_test(nms_ssh_client, log_file, last_line_number, fail_flag,
                                             grep_moudle=grep_moudle)
        if fail_test: self.failed()   

#32
class validate_tunnel_far_int_from_show_filter(aetest.Testcase):
    @aetest.test
    def validate_tunnel_far_int_from_show_filter(self, driver):

        # return True
        fail_flag = False
        last_line_number = test_utils.read_remote_logs(remote_ssh_client=nms_ssh_client, log_file=log_file, get_last_line=True)[0].rstrip()

        try:
            tunl_dev = ui_common_utils1.TunnelStatus(driver)
            tunl_dev.search_tunnels('FAR Interface', far_int_val)
            time.sleep(1)

            expected_fun_value = 'farInterface:%s'%far_int_val
            current_fun_value = driver.find_element_by_name('tunnelSearchQuery').get_attribute('value')

            log.info('Clearing exiting search filter content.')
            driver.find_element_by_xpath('//input[contains(@id, "tunnelSearchQuery")]').clear()

            log.info('Clicking on Hide Filter button.')
            driver.execute_script('if($(\'a:contains("Hide Filter")\').length>0)$(\'a:contains("Hide Filter")\')[0].click()')
            time.sleep(1)

            log.info('Expected value: %s \nCurrent_fun_value: %s' % (expected_fun_value, current_fun_value))
            if expected_fun_value == current_fun_value:
                log.info('expected_fun_value == current_fun_value : %s'%
                        str(expected_fun_value == current_fun_value))
            else:
                self.failed('expected value is not same as current value')  

        except Exception as e:
            log.error(e)
            fail_flag=True
            driver_utils.save_screenshot(scriptname='Show_filter_combo_box', classname=__class__.__name__)
            driver.refresh()
            time.sleep(5)

        fail_test = test_utils.forensic_test(nms_ssh_client, log_file, last_line_number, fail_flag,
                                             grep_moudle=grep_moudle)
        if fail_test: self.failed() 

#33
class validate_event_type_from_show_filter(aetest.Testcase):
    @aetest.test
    def validate_event_type_from_show_filter(self, driver):

        # return True
        fail_flag = False
        last_line_number = test_utils.read_remote_logs(remote_ssh_client=nms_ssh_client, log_file=log_file, get_last_line=True)[0].rstrip()

        try:
            driver_utils.navigate_to_home()
            events = ui_common_utils1.Events(driver)
            events.nav_sub_menu('events')
            time.sleep(1)
            bfr_expected_value = driver.find_element_by_name('eventSearchQuery').get_attribute('value')

            log.info('Searching events with Type')
            val = events.search_events('Type', search_value=typ_val)
            if val: log.info('Combo box selection is success')
            else: self.failed('Combo box selection is failed')
            time.sleep(1)

            expected_fun_value = 'deviceType:%s'%typ_val
            current_fun_value = driver.find_element_by_name('eventSearchQuery').get_attribute('value')
            expected_value = bfr_expected_value + expected_fun_value

            log.info('Expected value: %s \nCurrent value: %s' % (expected_value, current_fun_value))
            if expected_value == current_fun_value:
                log.info('expected_value == current_value : %s'%
                        str(expected_value == current_fun_value))
            else:
                self.failed('expected value is not same as current value')  

        except Exception as e:
            log.error(e)
            fail_flag=True
            driver_utils.save_screenshot(scriptname='Show_filter_combo_box', classname=__class__.__name__)
            driver.refresh()
            time.sleep(5)

        fail_test = test_utils.forensic_test(nms_ssh_client, log_file, last_line_number, fail_flag,
                                             grep_moudle=grep_moudle)
        if fail_test: self.failed()   

#34
class validate_event_category_from_show_filter(aetest.Testcase):
    @aetest.test
    def validate_event_category_from_show_filter(self, driver):

        # return True
        fail_flag = False
        last_line_number = test_utils.read_remote_logs(remote_ssh_client=nms_ssh_client, log_file=log_file, get_last_line=True)[0].rstrip()

        try:
            events = ui_common_utils1.Events(driver)
            events.nav_sub_menu('events')
            bfr_expected_value = driver.find_element_by_name('eventSearchQuery').get_attribute('value')

            log.info('Searching events with Category')
            val = events.search_events('Category', search_value=cat_val)
            if val: log.info('Combo box selection is success')
            else: self.failed('Combo box selection is failed')
            time.sleep(1)

            expected_fun_value = 'deviceCategory:%s'%cat_val
            current_fun_value = driver.find_element_by_name('eventSearchQuery').get_attribute('value')
            expected_value = bfr_expected_value + expected_fun_value

            log.info('Expected value: %s \nCurrent value: %s' % (expected_value, current_fun_value))
            if expected_value == current_fun_value:
                log.info('expected_value == current_value : %s'%
                        str(expected_value == current_fun_value))
            else:
                self.failed('expected value is not same as current value')  

        except Exception as e:
            log.error(e)
            fail_flag=True
            driver_utils.save_screenshot(scriptname='Show_filter_combo_box', classname=__class__.__name__)
            driver.refresh()
            time.sleep(5)

        fail_test = test_utils.forensic_test(nms_ssh_client, log_file, last_line_number, fail_flag,
                                             grep_moudle=grep_moudle)
        if fail_test: self.failed()   

#35
class validate_event_name_from_show_filter(aetest.Testcase):
    @aetest.test
    def validate_event_name_from_show_filter(self, driver):

        # return True
        fail_flag = False
        last_line_number = test_utils.read_remote_logs(remote_ssh_client=nms_ssh_client, log_file=log_file, get_last_line=True)[0].rstrip()

        try:
            events = ui_common_utils1.Events(driver)
            events.nav_sub_menu('events')
            bfr_expected_value = driver.find_element_by_name('eventSearchQuery').get_attribute('value')

            log.info('Searching events with name')
            val = events.search_events('Event Name', search_value=evnt_name)
            if val: log.info('Combo box selection is success')
            else: self.failed('Combo box selection is failed')
            time.sleep(1)

            if evnt_name == 'Time Mismatch': evnt_nme = 'timeMismatch'
            expected_fun_value = 'eventName:%s'%evnt_nme
            current_fun_value = driver.find_element_by_name('eventSearchQuery').get_attribute('value')
            expected_value = bfr_expected_value + expected_fun_value

            log.info('Expected value: %s \nCurrent value: %s' % (expected_value, current_fun_value))
            if expected_value == current_fun_value:
                log.info('expected_value == current_value : %s'%
                        str(expected_value == current_fun_value))
            else:
                self.failed('expected value is not same as current value')  

        except Exception as e:
            log.error(e)
            fail_flag=True
            driver_utils.save_screenshot(scriptname='Show_filter_combo_box', classname=__class__.__name__)
            driver.refresh()
            time.sleep(5)

        fail_test = test_utils.forensic_test(nms_ssh_client, log_file, last_line_number, fail_flag,
                                             grep_moudle=grep_moudle)
        if fail_test: self.failed()   

#36
class validate_event_severity_from_show_filter(aetest.Testcase):
    @aetest.test
    def validate_event_severity_from_show_filter(self, driver):

        # return True
        fail_flag = False
        last_line_number = test_utils.read_remote_logs(remote_ssh_client=nms_ssh_client, log_file=log_file, get_last_line=True)[0].rstrip()

        try:
            events = ui_common_utils1.Events(driver)
            events.nav_sub_menu('events')
            bfr_expected_value = driver.find_element_by_name('eventSearchQuery').get_attribute('value')

            log.info('Searching events with severity')
            events.search_events('Event Severity', search_value=event_sev)
            if val: log.info('Combo box selection is success')
            else: self.failed('Combo box selection is failed')
            time.sleep(1)

            expected_fun_value = 'eventSeverity:%s'%event_sev
            current_fun_value = driver.find_element_by_name('eventSearchQuery').get_attribute('value')
            expected_value = bfr_expected_value + expected_fun_value

            log.info('Expected value: %s \nCurrent value: %s' % (expected_value, current_fun_value))
            if expected_value == current_fun_value:
                log.info('expected_value == current_value : %s'%
                        str(expected_value == current_fun_value))
            else:
                self.failed('expected value is not same as current value')   

        except Exception as e:
            log.error(e)
            fail_flag=True
            driver_utils.save_screenshot(scriptname='Show_filter_combo_box', classname=__class__.__name__)
            driver.refresh()
            time.sleep(5)

        fail_test = test_utils.forensic_test(nms_ssh_client, log_file, last_line_number, fail_flag,
                                             grep_moudle=grep_moudle)
        if fail_test: self.failed()  

#37
class validate_event_label_from_show_filter(aetest.Testcase):
    @aetest.test
    def validate_event_label_from_show_filter(self, driver):

        # return True
        fail_flag = False
        last_line_number = test_utils.read_remote_logs(remote_ssh_client=nms_ssh_client, log_file=log_file, get_last_line=True)[0].rstrip()

        try:
            driver_utils.navigate_to_home()
            field_dev = ui_common_utils1.FieldDevices(driver)
            field_dev.nav_sub_menu('field_devices')
            time.sleep(1)

            item_slection_message = driver.find_element_by_xpath('//div[contains(text(), "Items selected")]')
            search_input = driver.find_element_by_xpath('//input[contains(@class, "x-form-text x-form-field x-box-item")]')
            search_input.clear()

            log.info('Searching device with "up" status.')
            search_input.send_keys('deviceCategory:router status:up')
            time.sleep(1)
            log.info('\nClicking on the Search Devices button.')
            driver.find_element_by_xpath('//table[contains(@class, "x-btn fa fa-search")]').click()
            time.sleep(2)

            log.info('Click checkbox of device with Up Status.')
            check_elem = driver.find_element_by_xpath(
                '//span[contains(@class, "icon-up")]/../../preceding-sibling::td[contains(@class, "x-grid3-td-checker")]/div/div')
            check_elem.click()
            time.sleep(2)

            log.info(banner('Checking Label.'))
            label_operation_completed = field_dev.label_operation('add', 'test_label3')
            time.sleep(3)

            log.info('Added test label: %s' % label_operation_completed)
            if not label_operation_completed: raise Exception('Unable to add label')

            driver_utils.navigate_to_home()
            events = ui_common_utils1.Events(driver)
            events.nav_sub_menu('events')
            time.sleep(1)      
            bfr_expected_value = driver.find_element_by_name('eventSearchQuery').get_attribute('value')

            log.info('Searching events with Label')
            events.search_events('Label', search_value='test_label3')
            if val: log.info('Combo box selection is success')
            else: self.failed('Combo box selection is failed')
            time.sleep(1)

            expected_fun_value = 'label:%s'%'test_label3'
            current_fun_value = driver.find_element_by_name('eventSearchQuery').get_attribute('value')
            expected_value = bfr_expected_value + expected_fun_value

            log.info('Expected value: %s \nCurrent value: %s' % (expected_value, current_fun_value))
            if expected_value == current_fun_value:
                log.info('expected_value == current_value : %s'%
                        str(expected_value == current_fun_value))
            else:
                self.failed('expected value is not same as current value') 

        except Exception as e:
            log.error(e)
            fail_flag=True
            driver_utils.save_screenshot(scriptname='Show_filter_combo_box', classname=__class__.__name__)
            driver.refresh()
            time.sleep(5)

        finally:
            field_dev = ui_common_utils1.FieldDevices(driver)
            field_dev.nav_sub_menu('field_devices')
            time.sleep(1)

            item_slection_message = driver.find_element_by_xpath('//div[contains(text(), "Items selected")]')
            search_input = driver.find_element_by_xpath('//input[contains(@class, "x-form-text x-form-field x-box-item")]')
            search_input.clear()

            log.info('Searching device with "up" status.')
            search_input.send_keys('deviceCategory:router status:up')
            time.sleep(1)
            log.info('\nClicking on the Search Devices button.')
            driver.find_element_by_xpath('//table[contains(@class, "x-btn fa fa-search")]').click()
            time.sleep(2)

            log.info('Click checkbox of device with Up Status.')
            check_elem = driver.find_element_by_xpath(
                '//span[contains(@class, "icon-up")]/../../preceding-sibling::td[contains(@class, "x-grid3-td-checker")]/div/div')
            check_elem.click()
            time.sleep(2)
            log.info('Device Selected: %s' % item_slection_message.is_displayed())

            label_operation_completed = field_dev.label_operation('remove', 'test_label3')
            log.info('Removed test label: %s' % label_operation_completed)
            if not label_operation_completed: raise Exception('Unable to remove label') 

        fail_test = test_utils.forensic_test(nms_ssh_client, log_file, last_line_number, fail_flag,
                                             grep_moudle=grep_moudle)
        if fail_test: self.failed() 

#38
class validate_event_device_name_from_show_filter(aetest.Testcase):
    @aetest.test
    def validate_event_device_name_from_show_filter(self, driver):

        # return True
        fail_flag = False
        last_line_number = test_utils.read_remote_logs(remote_ssh_client=nms_ssh_client, log_file=log_file, get_last_line=True)[0].rstrip()

        try:
            driver_utils.navigate_to_home()
            events = ui_common_utils1.Events(driver)
            events.nav_sub_menu('events')      
            bfr_expected_value = driver.find_element_by_name('eventSearchQuery').get_attribute('value')

            log.info('Searching events with Name')
            events.search_events('Name', search_value=her_name_val)
            if val: log.info('Combo box selection is success')
            else: self.failed('Combo box selection is failed')
            time.sleep(1)

            expected_fun_value = 'name:%s'%her_name_val
            current_fun_value = driver.find_element_by_name('eventSearchQuery').get_attribute('value')
            expected_value = bfr_expected_value + expected_fun_value

            log.info('Expected value: %s \nCurrent value: %s' % (expected_value, current_fun_value))
            if expected_value == current_fun_value:
                log.info('expected_value == current_value : %s'%
                        str(expected_value == current_fun_value))
            else:
                self.failed('expected value is not same as current value')   

        except Exception as e:
            log.error(e)
            fail_flag=True
            driver_utils.save_screenshot(scriptname='Show_filter_combo_box', classname=__class__.__name__)
            driver.refresh()
            time.sleep(5)

        fail_test = test_utils.forensic_test(nms_ssh_client, log_file, last_line_number, fail_flag,
                                             grep_moudle=grep_moudle)
        if fail_test: self.failed()   

#39
class validate_asset_name_from_show_filter(aetest.Testcase):
    @aetest.test
    def validate_asset_name_from_show_filter(self, driver):

        # return True
        fail_flag = False
        last_line_number = test_utils.read_remote_logs(remote_ssh_client=nms_ssh_client, log_file=log_file, get_last_line=True)[0].rstrip()   

        try:
            driver_utils.navigate_to_home()
            assets = ui_common_utils1.Assets(driver)
            assets.nav_sub_menu('assets')
 
            log.info('Searching assets with Name')
            assets.search_assets('Name', search_value=val)
            time.sleep(1) 

            expected_fun_value = 'assetName:%s'%val
            current_fun_value = driver.find_element_by_name('assetSearchQuery').get_attribute('value')

            log.info('Expected value: %s \nCurrent value: %s' % (expected_fun_value, current_fun_value))
            if expected_fun_value == current_fun_value:
                log.info('Expected_value == Current_value : %s'%
                        str(expected_fun_value == current_fun_value))
            else:
                self.failed('expected value is not same as current value')

        except Exception as e:
            log.error(e)
            fail_flag=True
            driver_utils.save_screenshot(scriptname='Show_filter_combo_box', classname=__class__.__name__)
            driver.refresh()
            time.sleep(5)

        fail_test = test_utils.forensic_test(nms_ssh_client, log_file, last_line_number, fail_flag,
                                             grep_moudle=grep_moudle)
        if fail_test: self.failed()  

#40
class validate_asset_devicetype_from_show_filter(aetest.Testcase):
    @aetest.test
    def validate_asset_devicetype_from_show_filter(self, driver):

        # return True
        fail_flag = False
        last_line_number = test_utils.read_remote_logs(remote_ssh_client=nms_ssh_client, log_file=log_file, get_last_line=True)[0].rstrip()

        try:
            assets = ui_common_utils1.Assets(driver)
            assets.nav_sub_menu('assets') 

            log.info('Searching assets with Type')
            assets.search_assets('Device Type', search_value=typ_val)
            time.sleep(1)

            expected_fun_value = 'assetDeviceType:%s'%typ_val
            current_fun_value = driver.find_element_by_name('assetSearchQuery').get_attribute('value')

            log.info('Expected value: %s \nCurrent value: %s' % (expected_fun_value, current_fun_value))
            if expected_fun_value == current_fun_value:
                log.info('Expected_value == Current_value : %s'%
                        str(expected_fun_value == current_fun_value))
            else:
                self.failed('expected value is not same as current value') 

        except Exception as e:
            log.error(e)
            fail_flag=True
            driver_utils.save_screenshot(scriptname='Show_filter_combo_box', classname=__class__.__name__)
            driver.refresh()
            time.sleep(5)

        fail_test = test_utils.forensic_test(nms_ssh_client, log_file, last_line_number, fail_flag,
                                             grep_moudle=grep_moudle)
        if fail_test: self.failed()   

#41
class validate_asset_eid_from_show_filter(aetest.Testcase):
    @aetest.test
    def validate_asset_eid_from_show_filter(self, driver):

        # return True
        fail_flag = False
        last_line_number = test_utils.read_remote_logs(remote_ssh_client=nms_ssh_client, log_file=log_file, get_last_line=True)[0].rstrip()

        try:
            assets = ui_common_utils1.Assets(driver)
            assets.nav_sub_menu('assets') 

            log.info('Searching assets with EID')
            assets.search_assets('Device Eid', search_value=eid_val)
            time.sleep(1)

            expected_fun_value = 'eid:%s'%eid_val
            current_fun_value = driver.find_element_by_name('assetSearchQuery').get_attribute('value')

            log.info('Expected value: %s \nCurrent value: %s' % (expected_fun_value, current_fun_value))
            if expected_fun_value == current_fun_value:
                log.info('Expected_value == Current_value : %s'%
                        str(expected_fun_value == current_fun_value))
            else:
                self.failed('expected value is not same as current value') 

        except Exception as e:
            log.error(e)
            fail_flag=True
            driver_utils.save_screenshot(scriptname='Show_filter_combo_box', classname=__class__.__name__)
            driver.refresh()
            time.sleep(5)

        fail_test = test_utils.forensic_test(nms_ssh_client, log_file, last_line_number, fail_flag,
                                             grep_moudle=grep_moudle)
        if fail_test: self.failed() 

#42
class validate_asset_device_name_from_show_filter(aetest.Testcase):
    @aetest.test
    def validate_asset_device_name_from_show_filter(self, driver):

        # return True
        fail_flag = False
        last_line_number = test_utils.read_remote_logs(remote_ssh_client=nms_ssh_client, log_file=log_file, get_last_line=True)[0].rstrip()

        try:
            assets = ui_common_utils1.Assets(driver)
            assets.nav_sub_menu('assets') 

            log.info('Searching assets with Device Name')
            assets.search_assets('Device Name', search_value=eid_val)
            time.sleep(1)

            expected_fun_value = 'name:%s'%eid_val
            current_fun_value = driver.find_element_by_name('assetSearchQuery').get_attribute('value')

            log.info('Expected value: %s \nCurrent value: %s' % (expected_fun_value, current_fun_value))
            if expected_fun_value == current_fun_value:
                log.info('Expected_value == Current_value : %s'%
                        str(expected_fun_value == current_fun_value))
            else:
                self.failed('expected value is not same as current value') 

        except Exception as e:
            log.error(e)
            fail_flag=True
            driver_utils.save_screenshot(scriptname='Show_filter_combo_box', classname=__class__.__name__)
            driver.refresh()
            time.sleep(5)

        fail_test = test_utils.forensic_test(nms_ssh_client, log_file, last_line_number, fail_flag,
                                             grep_moudle=grep_moudle)
        if fail_test: self.failed() 

#43
class validate_asset_status_from_show_filter(aetest.Testcase):
    @aetest.test
    def validate_asset_status_from_show_filter(self, driver):

        # return True
        fail_flag = False
        last_line_number = test_utils.read_remote_logs(remote_ssh_client=nms_ssh_client, log_file=log_file, get_last_line=True)[0].rstrip()

        try:
            assets = ui_common_utils1.Assets(driver)
            assets.nav_sub_menu('assets') 

            log.info('Searching assets with Status')
            assets.search_assets('Status', search_value=stat_val)
            time.sleep(1)

            expected_fun_value = 'status:%s'%stat_val
            current_fun_value = driver.find_element_by_name('assetSearchQuery').get_attribute('value')

            log.info('Expected value: %s \nCurrent value: %s' % (expected_fun_value, current_fun_value))
            if expected_fun_value == current_fun_value:
                log.info('Expected_value == Current_value : %s'%
                        str(expected_fun_value == current_fun_value))
            else:
                self.failed('expected value is not same as current value') 

        except Exception as e:
            log.error(e)
            fail_flag=True
            driver_utils.save_screenshot(scriptname='Show_filter_combo_box', classname=__class__.__name__)
            driver.refresh()
            time.sleep(5)

        fail_test = test_utils.forensic_test(nms_ssh_client, log_file, last_line_number, fail_flag,
                                             grep_moudle=grep_moudle)
        if fail_test: self.failed() 

#44
class validate_asset_attach_to_wo_from_show_filter(aetest.Testcase):
    @aetest.test
    def validate_asset_attach_to_wo_from_show_filter(self, driver):

        # return True
        fail_flag = False
        last_line_number = test_utils.read_remote_logs(remote_ssh_client=nms_ssh_client, log_file=log_file, get_last_line=True)[0].rstrip()

        try:
            assets = ui_common_utils1.Assets(driver)
            assets.nav_sub_menu('assets')
 
            log.info('Searching assets with Attach to WO')
            assets.search_assets('Attach to WO', search_value=attach_wo)
            time.sleep(1)
           
            if attach_wo == 'yes': atch_wo = 'true'
            expected_fun_value = 'attachToWO:%s'%atch_wo
            current_fun_value = driver.find_element_by_name('assetSearchQuery').get_attribute('value')

            log.info('Expected value: %s \nCurrent value: %s' % (expected_fun_value, current_fun_value))
            if expected_fun_value == current_fun_value:
                log.info('Expected_value == Current_value : %s'%
                        str(expected_fun_value == current_fun_value))
            else:
                self.failed('expected value is not same as current value') 

        except Exception as e:
            log.error(e)
            fail_flag=True
            driver_utils.save_screenshot(scriptname='Show_filter_combo_box', classname=__class__.__name__)
            driver.refresh()
            time.sleep(5)

        fail_test = test_utils.forensic_test(nms_ssh_client, log_file, last_line_number, fail_flag,
                                             grep_moudle=grep_moudle)
        if fail_test: self.failed() 

#45
class validate_asset_housePlate_from_show_filter(aetest.Testcase):
    @aetest.test
    def validate_asset_housePlate_from_show_filter(self, driver):

        # return True
        fail_flag = False
        last_line_number = test_utils.read_remote_logs(remote_ssh_client=nms_ssh_client, log_file=log_file, get_last_line=True)[0].rstrip()

        try:
            assets = ui_common_utils1.Assets(driver)
            assets.nav_sub_menu('assets') 

            log.info('Searching assets with housePlate')
            assets.search_assets('housePlate', search_value=val)
            time.sleep(1)

            expected_fun_value = 'housePlate:%s'%val
            current_fun_value = driver.find_element_by_name('assetSearchQuery').get_attribute('value')

            log.info('Expected value: %s \nCurrent value: %s' % (expected_fun_value, current_fun_value))
            if expected_fun_value == current_fun_value:
                log.info('Expected_value == Current_value : %s'%
                        str(expected_fun_value == current_fun_value))
            else:
                self.failed('expected value is not same as current value') 

        except Exception as e:
            log.error(e)
            fail_flag=True
            driver_utils.save_screenshot(scriptname='Show_filter_combo_box', classname=__class__.__name__)
            driver.refresh()
            time.sleep(5)

        fail_test = test_utils.forensic_test(nms_ssh_client, log_file, last_line_number, fail_flag,
                                             grep_moudle=grep_moudle)
        if fail_test: self.failed() 

#46
class validate_asset_hvacNumber_from_show_filter(aetest.Testcase):
    @aetest.test
    def validate_asset_hvacNumber_from_show_filter(self, driver):

        # return True
        fail_flag = False
        last_line_number = test_utils.read_remote_logs(remote_ssh_client=nms_ssh_client, log_file=log_file, get_last_line=True)[0].rstrip()

        try:
            assets = ui_common_utils1.Assets(driver)
            assets.nav_sub_menu('assets') 

            log.info('Searching assets with hvacNumber')
            assets.search_assets('hvacNumber', search_value=val)
            time.sleep(1)

            expected_fun_value = 'hvacNumber:%s'%val
            current_fun_value = driver.find_element_by_name('assetSearchQuery').get_attribute('value')

            log.info('Expected value: %s \nCurrent value: %s' % (expected_fun_value, current_fun_value))
            if expected_fun_value == current_fun_value:
                log.info('Expected_value == Current_value : %s'%
                        str(expected_fun_value == current_fun_value))
            else:
                self.failed('expected value is not same as current value') 

        except Exception as e:
            log.error(e)
            fail_flag=True
            driver_utils.save_screenshot(scriptname='Show_filter_combo_box', classname=__class__.__name__)
            driver.refresh()
            time.sleep(5)

        fail_test = test_utils.forensic_test(nms_ssh_client, log_file, last_line_number, fail_flag,
                                             grep_moudle=grep_moudle)
        if fail_test: self.failed() 

#47
class validate_asset_poleNumber_from_show_filter(aetest.Testcase):
    @aetest.test
    def validate_asset_poleNumber_from_show_filter(self, driver):

        # return True
        fail_flag = False
        last_line_number = test_utils.read_remote_logs(remote_ssh_client=nms_ssh_client, log_file=log_file, get_last_line=True)[0].rstrip()

        try:
            assets = ui_common_utils1.Assets(driver)
            assets.nav_sub_menu('assets') 

            log.info('Searching assets with poleNumber')
            assets.search_assets('poleNumber', search_value=val)
            time.sleep(1)

            expected_fun_value = 'poleNumber:%s'%val
            current_fun_value = driver.find_element_by_name('assetSearchQuery').get_attribute('value')

            log.info('Expected value: %s \nCurrent value: %s' % (expected_fun_value, current_fun_value))
            if expected_fun_value == current_fun_value:
                log.info('Expected_value == Current_value : %s'%
                        str(expected_fun_value == current_fun_value))
            else:
                self.failed('expected value is not same as current value') 

        except Exception as e:
            log.error(e)
            fail_flag=True
            driver_utils.save_screenshot(scriptname='Show_filter_combo_box', classname=__class__.__name__)
            driver.refresh()
            time.sleep(5)

        fail_test = test_utils.forensic_test(nms_ssh_client, log_file, last_line_number, fail_flag,
                                             grep_moudle=grep_moudle)
        if fail_test: self.failed() 

#48
class validate_asset_vin_from_show_filter(aetest.Testcase):
    @aetest.test
    def validate_asset_vin_from_show_filter(self, driver):

        # return True
        fail_flag = False
        last_line_number = test_utils.read_remote_logs(remote_ssh_client=nms_ssh_client, log_file=log_file, get_last_line=True)[0].rstrip()

        try:
            assets = ui_common_utils1.Assets(driver)
            assets.nav_sub_menu('assets') 

            log.info('Searching assets with vin')
            assets.search_assets('vin', search_value=val)
            time.sleep(1)

            expected_fun_value = 'vin:%s'%val
            current_fun_value = driver.find_element_by_name('assetSearchQuery').get_attribute('value')

            log.info('Expected value: %s \nCurrent value: %s' % (expected_fun_value, current_fun_value))
            if expected_fun_value == current_fun_value:
                log.info('Expected_value == Current_value : %s'%
                        str(expected_fun_value == current_fun_value))
            else:
                self.failed('expected value is not same as current value') 

        except Exception as e:
            log.error(e)
            fail_flag=True
            driver_utils.save_screenshot(scriptname='Show_filter_combo_box', classname=__class__.__name__)
            driver.refresh()
            time.sleep(5)

        fail_test = test_utils.forensic_test(nms_ssh_client, log_file, last_line_number, fail_flag,
                                             grep_moudle=grep_moudle)
        if fail_test: self.failed() 

#49
class validate_issue_type_from_show_filter(aetest.Testcase):
    @aetest.test
    def validate_issue_type_from_show_filter(self, driver):

        # return True
        fail_flag = False
        last_line_number = test_utils.read_remote_logs(remote_ssh_client=nms_ssh_client, log_file=log_file, get_last_line=True)[0].rstrip()

        try:

            driver_utils.navigate_to_home()
            issues = ui_common_utils1.Issues(driver)
            issues.nav_sub_menu('issues')

            log.info('Searching issue with Type')
            issues.search_issues('Type', search_value=typ_val)
            time.sleep(1)

            expected_fun_value = 'deviceType:%s'%typ_val
            current_fun_value = driver.find_element_by_name('issueSearchQuery').get_attribute('value')

            log.info('Expected value: %s \nCurrent value: %s' % (expected_fun_value, current_fun_value))
            if expected_fun_value == current_fun_value:
                log.info('Expected_value == Current_value : %s'%
                        str(expected_fun_value == current_fun_value))
            else:
                self.failed('expected value is not same as current value') 

        except Exception as e:
            log.error(e)
            fail_flag=True
            driver_utils.save_screenshot(scriptname='Show_filter_combo_box', classname=__class__.__name__)
            driver.refresh()
            time.sleep(5)

        fail_test = test_utils.forensic_test(nms_ssh_client, log_file, last_line_number, fail_flag,
                                             grep_moudle=grep_moudle) 
        if fail_test: self.failed()  

#50
class validate_issue_category_from_show_filter(aetest.Testcase):
    @aetest.test
    def validate_issue_category_from_show_filter(self, driver):

        # return True
        fail_flag = False
        last_line_number = test_utils.read_remote_logs(remote_ssh_client=nms_ssh_client, log_file=log_file, get_last_line=True)[0].rstrip()

        try:

            issues = ui_common_utils1.Issues(driver)
            issues.nav_sub_menu('issues') 

            log.info('Searching issue with Category')
            issues.search_issues('Category', search_value=cat_val)
            time.sleep(1)

            expected_fun_value = 'deviceCategory:%s'%cat_val
            current_fun_value = driver.find_element_by_name('issueSearchQuery').get_attribute('value')

            log.info('Expected value: %s \nCurrent value: %s' % (expected_fun_value, current_fun_value))
            if expected_fun_value == current_fun_value:
                log.info('Expected_value == Current_value : %s'%
                        str(expected_fun_value == current_fun_value))
            else:
                self.failed('expected value is not same as current value') 

        except Exception as e:
            log.error(e)
            fail_flag=True
            driver_utils.save_screenshot(scriptname='Show_filter_combo_box', classname=__class__.__name__)
            driver.refresh()
            time.sleep(5)

        fail_test = test_utils.forensic_test(nms_ssh_client, log_file, last_line_number, fail_flag,
                                             grep_moudle=grep_moudle) 
        if fail_test: self.failed() 

#51
class validate_issue_name_from_show_filter(aetest.Testcase):
    @aetest.test
    def validate_issue_name_from_show_filter(self, driver):

        # return True
        fail_flag = False
        last_line_number = test_utils.read_remote_logs(remote_ssh_client=nms_ssh_client, log_file=log_file, get_last_line=True)[0].rstrip()

        try:

            issues = ui_common_utils1.Issues(driver)
            issues.nav_sub_menu('issues')
            log.info('Searching issue with Name')
            issues.search_issues('Name', search_value=name_val)
            time.sleep(1)

            expected_fun_value = 'name:%s'%name_val
            current_fun_value = driver.find_element_by_name('issueSearchQuery').get_attribute('value')

            log.info('Expected value: %s \nCurrent value: %s' % (expected_fun_value, current_fun_value))
            if expected_fun_value == current_fun_value:
                log.info('Expected_value == Current_value : %s'%
                        str(expected_fun_value == current_fun_value))
            else:
                self.failed('expected value is not same as current value') 

        except Exception as e:
            log.error(e)
            fail_flag=True
            driver_utils.save_screenshot(scriptname='Show_filter_combo_box', classname=__class__.__name__)
            driver.refresh()
            time.sleep(5)

        fail_test = test_utils.forensic_test(nms_ssh_client, log_file, last_line_number, fail_flag,
                                             grep_moudle=grep_moudle)
        if fail_test: self.failed() 

#52
class validate_issue_from_show_filter(aetest.Testcase):
    @aetest.test
    def validate_issue_from_show_filter(self, driver):

        # return True
        fail_flag = False
        last_line_number = test_utils.read_remote_logs(remote_ssh_client=nms_ssh_client, log_file=log_file, get_last_line=True)[0].rstrip()

        try:

            issues = ui_common_utils1.Issues(driver)
            issues.nav_sub_menu('issues')

            log.info('Searching Issue')
            issues.search_issues('Issue', search_value=issue_val)
            time.sleep(1)
            if issue_val == 'Down': isue_val = 'down'
            expected_fun_value = 'issue:%s'%isue_val
            current_fun_value = driver.find_element_by_name('issueSearchQuery').get_attribute('value')

            log.info('Expected value: %s \nCurrent value: %s' % (expected_fun_value, current_fun_value))
            if expected_fun_value == current_fun_value:
                log.info('Expected_value == Current_value : %s'%
                        str(expected_fun_value == current_fun_value))
            else:
                self.failed('expected value is not same as current value') 

        except Exception as e:
            log.error(e)
            fail_flag=True
            driver_utils.save_screenshot(scriptname='Show_filter_combo_box', classname=__class__.__name__)
            driver.refresh()
            time.sleep(5)

        fail_test = test_utils.forensic_test(nms_ssh_client, log_file, last_line_number, fail_flag,
                                             grep_moudle=grep_moudle)
        if fail_test: self.failed() 

#53
class validate_issue_status_from_show_filter(aetest.Testcase):
    @aetest.test
    def validate_issue_status_from_show_filter(self, driver):

        # return True
        fail_flag = False
        last_line_number = test_utils.read_remote_logs(remote_ssh_client=nms_ssh_client, log_file=log_file, get_last_line=True)[0].rstrip()

        try:

            issues = ui_common_utils1.Issues(driver)
            issues.nav_sub_menu('issues')

            log.info('Searching Issue Status')
            issues.search_issues('Issue Status', search_value=issue_stat)
            time.sleep(1)
     
            expected_fun_value = 'issueStatus:%s'%issue_stat
            current_fun_value = driver.find_element_by_name('issueSearchQuery').get_attribute('value')

            log.info('Expected value: %s \nCurrent value: %s' % (expected_fun_value, current_fun_value))
            if expected_fun_value == current_fun_value:
                log.info('Expected_value == Current_value : %s'%
                        str(expected_fun_value == current_fun_value))
            else:
                self.failed('expected value is not same as current value') 

        except Exception as e:
            log.error(e)
            fail_flag=True
            driver_utils.save_screenshot(scriptname='Show_filter_combo_box', classname=__class__.__name__)
            driver.refresh()
            time.sleep(5)

        fail_test = test_utils.forensic_test(nms_ssh_client, log_file, last_line_number, fail_flag,
                                             grep_moudle=grep_moudle)
        if fail_test: self.failed() 

#54
class validate_issue_severity_from_show_filter(aetest.Testcase):
    @aetest.test
    def validate_issue_severity_from_show_filter(self, driver):

        # return True
        fail_flag = False
        last_line_number = test_utils.read_remote_logs(remote_ssh_client=nms_ssh_client, log_file=log_file, get_last_line=True)[0].rstrip()

        try:

            issues = ui_common_utils1.Issues(driver)
            issues.nav_sub_menu('issues')

            log.info('Searching Issue Severity')
            issues.search_issues('Issue Severity', search_value=issue_sev)
            time.sleep(1)

            expected_fun_value = 'issueSeverity:%s'%issue_sev
            current_fun_value = driver.find_element_by_name('issueSearchQuery').get_attribute('value')

            log.info('Expected value: %s \nCurrent value: %s' % (expected_fun_value, current_fun_value))
            if expected_fun_value == current_fun_value:
                log.info('Expected_value == Current_value : %s'%
                        str(expected_fun_value == current_fun_value))
            else:
                self.failed('expected value is not same as current value') 

        except Exception as e:
            log.error(e)
            fail_flag=True
            driver_utils.save_screenshot(scriptname='Show_filter_combo_box', classname=__class__.__name__)
            driver.refresh()
            time.sleep(5)

        fail_test = test_utils.forensic_test(nms_ssh_client, log_file, last_line_number, fail_flag,
                                             grep_moudle=grep_moudle)
        if fail_test: self.failed() 

#55
class validate_wo_device_number_from_show_filter(aetest.Testcase):
    @aetest.test
    def validate_wo_device_number_from_show_filter(self, driver):

        # return True
        fail_flag = False
        last_line_number = test_utils.read_remote_logs(remote_ssh_client=nms_ssh_client, log_file=log_file, get_last_line=True)[0].rstrip()

        try:
            driver_utils.navigate_to_home()
            wo = ui_common_utils1.WorkOrders(driver)
            wo.nav_sub_menu('trouble_ticket')

            log.info('Searching WO device number')
            wo.search_workorder('Work Order Number', search_value=val)
            time.sleep(1)

            expected_fun_value = 'workOrderNumber:%s'%val
            current_fun_value = driver.find_element_by_name('workOrderSearchQuery').get_attribute('value')

            log.info('Expected value: %s \nCurrent value: %s' % (expected_fun_value, current_fun_value))
            if expected_fun_value == current_fun_value:
                log.info('Expected_value == Current_value : %s'%
                        str(expected_fun_value == current_fun_value))
            else:
                self.failed('expected value is not same as current value') 

        except Exception as e:
            log.error(e)
            fail_flag=True
            driver_utils.save_screenshot(scriptname='Show_filter_combo_box', classname=__class__.__name__)
            driver.refresh()
            time.sleep(5)

        fail_test = test_utils.forensic_test(nms_ssh_client, log_file, last_line_number, fail_flag,
                                             grep_moudle=grep_moudle)
        if fail_test: self.failed()   

#56
class validate_wo_name_from_show_filter(aetest.Testcase):
    @aetest.test
    def validate_wo_name_from_show_filter(self, driver):

        # return True
        fail_flag = False
        last_line_number = test_utils.read_remote_logs(remote_ssh_client=nms_ssh_client, log_file=log_file, get_last_line=True)[0].rstrip()

        try:
            wo = ui_common_utils1.WorkOrders(driver)
            log.info('Searching WO Name')
            wo.nav_sub_menu('trouble_ticket')
            wo.search_workorder('Work Order Name', search_value=val)
            time.sleep(1)

            expected_fun_value = 'workOrderName:%s'%val
            current_fun_value = driver.find_element_by_name('workOrderSearchQuery').get_attribute('value')

            log.info('Expected value: %s \nCurrent value: %s' % (expected_fun_value, current_fun_value))
            if expected_fun_value == current_fun_value:
                log.info('Expected_value == Current_value : %s'%
                        str(expected_fun_value == current_fun_value))
            else:
                self.failed('expected value is not same as current value') 

        except Exception as e:
            log.error(e)
            fail_flag=True
            driver_utils.save_screenshot(scriptname='Show_filter_combo_box', classname=__class__.__name__)
            driver.refresh()
            time.sleep(5)

        fail_test = test_utils.forensic_test(nms_ssh_client, log_file, last_line_number, fail_flag,
                                             grep_moudle=grep_moudle)
        if fail_test: self.failed()

#57
class validate_wo_device_type_from_show_filter(aetest.Testcase):
    @aetest.test
    def validate_wo_device_type_from_show_filter(self, driver):

        # return True
        fail_flag = False
        last_line_number = test_utils.read_remote_logs(remote_ssh_client=nms_ssh_client, log_file=log_file, get_last_line=True)[0].rstrip()

        try:
            wo = ui_common_utils1.WorkOrders(driver)
            log.info('Searching WO device Type')
            wo.nav_sub_menu('trouble_ticket')
            wo.search_workorder('Work Order Device Type', search_value=typ_val)
            time.sleep(1)   

            expected_fun_value = 'workOrderDeviceType:%s'%typ_val
            current_fun_value = driver.find_element_by_name('workOrderSearchQuery').get_attribute('value')

            log.info('Expected value: %s \nCurrent value: %s' % (expected_fun_value, current_fun_value))
            if expected_fun_value == current_fun_value:
                log.info('Expected_value == Current_value : %s'%
                        str(expected_fun_value == current_fun_value))
            else:
                self.failed('expected value is not same as current value') 

        except Exception as e:
            log.error(e)
            fail_flag=True
            driver_utils.save_screenshot(scriptname='Show_filter_combo_box', classname=__class__.__name__)
            driver.refresh()
            time.sleep(5)

        fail_test = test_utils.forensic_test(nms_ssh_client, log_file, last_line_number, fail_flag,
                                             grep_moudle=grep_moudle)
        if fail_test: self.failed()  

#58
class validate_wo_far_name_eid_from_show_filter(aetest.Testcase):
    @aetest.test
    def validate_wo_far_name_eid_from_show_filter(self, driver):

        # return True
        fail_flag = False
        last_line_number = test_utils.read_remote_logs(remote_ssh_client=nms_ssh_client, log_file=log_file, get_last_line=True)[0].rstrip()

        try:
            wo = ui_common_utils1.WorkOrders(driver)
            log.info('Searching WO Name and EID')
            wo.nav_sub_menu('trouble_ticket')
            wo.search_workorder('FAR NAME/EID', search_value=eid_val)
            time.sleep(1)

            expected_fun_value = 'eid:%s'%eid_val
            current_fun_value = driver.find_element_by_name('workOrderSearchQuery').get_attribute('value')

            log.info('Expected value: %s \nCurrent value: %s' % (expected_fun_value, current_fun_value))
            if expected_fun_value == current_fun_value:
                log.info('Expected_value == Current_value : %s'%
                        str(expected_fun_value == current_fun_value))
            else:
                self.failed('expected value is not same as current value') 

        except Exception as e:
            log.error(e)
            fail_flag=True
            driver_utils.save_screenshot(scriptname='Show_filter_combo_box', classname=__class__.__name__)
            driver.refresh()
            time.sleep(5)

        fail_test = test_utils.forensic_test(nms_ssh_client, log_file, last_line_number, fail_flag,
                                             grep_moudle=grep_moudle)
        if fail_test: self.failed()

#59
class validate_wo_role_from_show_filter(aetest.Testcase):
    @aetest.test
    def validate_wo_role_from_show_filter(self, driver):

        # return True
        fail_flag = False
        last_line_number = test_utils.read_remote_logs(remote_ssh_client=nms_ssh_client, log_file=log_file, get_last_line=True)[0].rstrip()

        try:
            wo = ui_common_utils1.WorkOrders(driver)
            log.info('Searching WO Role')
            wo.nav_sub_menu('trouble_ticket')
            wo.search_workorder('Role', search_value=role)
            time.sleep(1)

            expected_fun_value = 'role:%s'%role
            current_fun_value = driver.find_element_by_name('workOrderSearchQuery').get_attribute('value')

            log.info('Expected value: %s \nCurrent value: %s' % (expected_fun_value, current_fun_value))
            if expected_fun_value == current_fun_value:
                log.info('Expected_value == Current_value : %s'%
                        str(expected_fun_value == current_fun_value))
            else:
                self.failed('expected value is not same as current value') 

        except Exception as e:
            log.error(e)
            fail_flag=True
            driver_utils.save_screenshot(scriptname='Show_filter_combo_box', classname=__class__.__name__)
            driver.refresh()
            time.sleep(5)

        fail_test = test_utils.forensic_test(nms_ssh_client, log_file, last_line_number, fail_flag,
                                             grep_moudle=grep_moudle)
        if fail_test: self.failed()

#60
class validate_wo_technician_user_name_from_show_filter(aetest.Testcase):
    @aetest.test
    def validate_wo_technician_user_name_from_show_filter(self, driver, username):

        # return True
        fail_flag = False
        last_line_number = test_utils.read_remote_logs(remote_ssh_client=nms_ssh_client, log_file=log_file, get_last_line=True)[0].rstrip()

        try:
            wo = ui_common_utils1.WorkOrders(driver)
            log.info('Searching WO Technician User Name')
            wo.nav_sub_menu('trouble_ticket')
            wo.search_workorder('Technician User Name', search_value=username)
            time.sleep(1)

            expected_fun_value = 'technicianUserName:%s'%username
            current_fun_value = driver.find_element_by_name('workOrderSearchQuery').get_attribute('value')

            log.info('Expected value: %s \nCurrent value: %s' % (expected_fun_value, current_fun_value))
            if expected_fun_value == current_fun_value:
                log.info('Expected_value == Current_value : %s'%
                        str(expected_fun_value == current_fun_value))
            else:
                self.failed('expected value is not same as current value') 

        except Exception as e:
            log.error(e)
            fail_flag=True
            driver_utils.save_screenshot(scriptname='Show_filter_combo_box', classname=__class__.__name__)
            driver.refresh()
            time.sleep(5)

        fail_test = test_utils.forensic_test(nms_ssh_client, log_file, last_line_number, fail_flag,
                                             grep_moudle=grep_moudle)
        if fail_test: self.failed()

#61
class validate_wo_status_from_show_filter(aetest.Testcase):
    @aetest.test
    def validate_wo_status_from_show_filter(self, driver):

        # return True
        fail_flag = False
        last_line_number = test_utils.read_remote_logs(remote_ssh_client=nms_ssh_client, log_file=log_file, get_last_line=True)[0].rstrip()

        try:
            wo = ui_common_utils1.WorkOrders(driver)
            log.info('Searching WO Status')
            wo.nav_sub_menu('trouble_ticket')
            wo.search_workorder('Status', search_value=wr_status)
            time.sleep(1)
            if wr_status == 'In Service': wr_stus = 'InService'
            expected_fun_value = 'workOrderStatus:%s'%wr_stus
            current_fun_value = driver.find_element_by_name('workOrderSearchQuery').get_attribute('value')

            log.info('Expected value: %s \nCurrent value: %s' % (expected_fun_value, current_fun_value))
            if expected_fun_value == current_fun_value:
                log.info('Expected_value == Current_value : %s'%
                        str(expected_fun_value == current_fun_value))
            else:
                self.failed('expected value is not same as current value') 

        except Exception as e:
            log.error(e)
            fail_flag=True
            driver_utils.save_screenshot(scriptname='Show_filter_combo_box', classname=__class__.__name__)
            driver.refresh()
            time.sleep(5)

        fail_test = test_utils.forensic_test(nms_ssh_client, log_file, last_line_number, fail_flag,
                                             grep_moudle=grep_moudle)
        if fail_test: self.failed()

#62
class validate_bill_period_setting_combo_box(aetest.Testcase):
    @aetest.test
    def validate_bill_period_setting_combo_box(self, driver):

        # return True
        fail_flag = False
        last_line_number = test_utils.read_remote_logs(remote_ssh_client=nms_ssh_client, log_file=log_file, get_last_line=True)[0].rstrip()

        try:
            log.info('\nNavigating to "Server Settings".')
            server_settings = ui_common_utils1.ServerSettings(driver)
            server_settings.nav_sub_menu('server_settings')
            server_settings.nav_tab('billing_period_settings')

            time_zoneId = driver.find_element_by_name('timeZoneId')
            time_zoneId.clear()
            log.info('Search timezone dropdown button')
            driver.find_element_by_xpath('//input[contains(@id, "timeZoneId")]//following-sibling::img').click()
            for val in timezne:
                time_zoneId.send_keys(val)
            time.sleep(5)
            time_zoneId.click()
            time.sleep(1)
            log.info('Clicking on %s.'%timezne)
            driver.find_element_by_xpath('//div[starts-with(@class, "x-combo-list-item") and contains(text(), "%s")]'%timezne).click()
            time.sleep(2)

            expected_fun_value = timezne
            current_fun_value = driver.find_element_by_name('timeZoneId').get_attribute('value')

            log.info('Expected value: %s \nCurrent value: %s' % (expected_fun_value, current_fun_value))
            if expected_fun_value == current_fun_value:
                log.info('Expected_value == Current_value : %s'%
                        str(expected_fun_value == current_fun_value))
            else:
                self.failed('expected value is not same as current value') 

        except Exception as e:
            log.error(e)
            fail_flag=True
            driver_utils.save_screenshot(scriptname='Show_filter_combo_box', classname=__class__.__name__)
            driver.refresh()
            time.sleep(5)

        fail_test = test_utils.forensic_test(nms_ssh_client, log_file, last_line_number, fail_flag,
                                             grep_moudle=grep_moudle)
        if fail_test: self.failed() 

class CommonCleanup(aetest.CommonCleanup):

    @aetest.subsection
    def disconnect_from_devices(self, driver, nms_server):
        log.info(banner('DISCONNECTING FROM DEVICES IN TESTBED'))
        try:
            log.info('Closing NMS ssh client.')
            nms_ssh_client.close()

            log.info(banner('Quitting webdriver.'))
            driver_utils = ui_common_utils1.DriverUtils(driver)
            driver_utils.logout()
            driver.quit()

            nms_server.disconnect()
            if nms_server.is_connected():
                raise Exception('COULD NOT DISCONNECT FROM DEVICE')
        except Exception as e: self.failed(e)

if __name__ == '__main__':
    import argparse
    from ats import topology
    parser = argparse.ArgumentParser(description='standalone parser')
    parser.add_argument("--testbed", type = topology.loader.load)

    args, unknwon = parser.parse_known_args()
    aetest.main(**vars(args))
