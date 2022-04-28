# !/bin/env python
###################################################################################
#
# Copyright (c) 2020 Cisco Systems, Inc.
#
###################################################################################
#
####################################################################################
#
#               S C R I P T  H E A D E R  I N F O R M A T I O N
#
####################################################################################
# Script Name:
#       Schedule_Switch_to_Wisun.py
#
# Topology:
#
#        +---------------------+      +---------------------+
#        |                     |      |                     |
#        |       Field         |      |       IR510         |
#        |  Network Director   |------|      in WISUN       |
#        |                     |      |      PAN ID -2      |
#        |                     |      |                     |
#        +---------------------+      +---------------------+
#                   |
#                   |
#        +---------------------+
#        |                     |
#        |     IR510, IR530    |
#        |      in CGMESH      |
#        |      PAN ID -1      |
#        |                     |
#        +---------------------+
#
# Topology Prerequisite:
#       2 IR510 and 1 IR530 need be registered in FND.
#       PAN_ID - 1 = 1 IR510 and 1 IR530
#       PAN_ID - 2 = 1 IR530
#
# Author:
#       GANESH KUMAR (ganesku2@cisco.com)
#
# Sample Usage:
#       easypy jobs/fnd_job.py --testbed jobs/yaml/testbed_ganesku5.yaml --testscript Schedule_Switch_to_Wisun -no_mail -no_upload
#
# Job File:
#       jobs/yaml/testbed_ganesku5.yaml
#
# Test cases:
# -----------
#   1. Validate "Push stack mode" for two PAN ID in a group when one of the PAN_ID  was already switched to the new stack mode
#   2. Validate "Push stack time" for two PAN ID in a group when one of the PAN_ID  was already switched to the new stack mode
#   3. Validate "Cancel stack mode/time" for two PAN ID in a group when one of the PAN_ID  was already switched to the new stack mode
#   4. Validate clicking on cancel button throws error pop-up before initiating the stack mode operation
#   5. Validate initiating  "Push stackmode time" button before "Push stackmode" within PAN ID
#   6. Validate push stack mode  successful operation for default group
#   7. Validate cancel stack mode for default group
#   8. Validate push stackmode time successful operation for default group
#   9. Validate cancel stack mode and stack mode time for default group
#   10. Validate the Success Stack Change State for push stack mode per device
#   11. Validate the Success Stack Change State for push stack mode time per device
#   12. Validate cancel stack mode and time for two different PAN ID in a group
#   13. Validate switch-to-wisun stack mode buttons are disabled for the user doesn't have Enpoint Firmware update role permission
#   14. Validate scheduling stack time for more than 49 days
#   15. Validate push stack mode  successful operation for custom group
#   16. Validate push stack mode for two different PAN ID in a group
#   17. Validate push stack mode time for two different PAN ID in a group
#   18. Validate cancel stack mode for custom group
#   19. Validate Switch stack mode is blocked for the nodes which is other than base [6.2 MR]version within a PAN ID
#   20. Validate schedule switch-to-wisun stack mode and schedule firmware reload at the same date and time
#   21. Validate cancel stack mode after schedule firmware reload
#   
# Below are covered as a part of other testcases:
# -----------------------------------------------
#   1. Validate initiating push stackmode for the PAN ID which was already switched to WISUN
#   2. Validate switch-to-wisun stack mode buttons are enabled for Enpoint Firmware update role permission
#   3. Validate the switch-to-wisun stack mode state change or Events in Audit trial and logs
#   4. Validate switch-to-wisun stack mode buttons are enabled for combination of nodes in a custom-IR5xx and CGmesh group within a PAN ID
#
#
## End of header
####################################################################################
#
####################################################################################
#
#           T E S T  S C R I P T  I N I T I A L I Z A T I O N  B L O C K
#
####################################################################################
# ===== include all the packages required =====

import os
import re
import sys
import csv
import time
import yaml
import datetime
import requests
import collections
import random
from datetime import date, timedelta
from random import randint
from selenium.webdriver.common.action_chains import ActionChains
from threading import Thread

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
import fnd_utils, ui_common_utils

driver_utils = None
nms_ssh_client = None
nms_ip = None
username = None
password = None
auto_user_ws = None
log_file = '/opt/cgms/server/cgms/log/server.log'
conf_folder = '/opt/cgms/server/cgms/conf'  
properties_file_folder = '/ws/satjonna-sjc/pyats/iot-fnd-4.5/properties_folder' 

test_utils = fnd_utils.TestUtils()
dev_utils = fnd_utils.DeviceUtils()
nbapi_utils = fnd_utils.NBAPIUtils()

###################################################################
###                  COMMON SETUP SECTION                       ###
###################################################################

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
        global nms_ip
        global nonroot_domainname
        global nonroot_username
        global username
        global password
        global auto_user_ws
        global mesh_image
        global backup_file
        global mesh_firmware_image_meter
        global mesh_delete_image_meter
        tb_devices = dev_utils.connect_testbed_devices(testbed)

        #Firefox webdriver.
        if not os.path.exists(os.getcwd()+'/downloads'):
            os.makedirs(os.getcwd()+'/downloads')

        nms_server = tb_devices['nms_server']
        profile_name = nms_server.custom.firefoxprofile2

        profile = webdriver.FirefoxProfile(profile_name)
        profile.set_preference("browser.download.folderList", 2)
        profile.set_preference("browser.download.manager.showWhenStarting", False)
        profile.set_preference("browser.download.dir", os.getcwd() + '/downloads')
        profile.set_preference("browser.helperApps.neverAsk.saveToDisk",
                               "application/x-gzip,application/download,text/txt,application/txt,text/csv,application/csv,application/json,text/html")
        driver = webdriver.Firefox(firefox_profile=profile)

        driver.implicitly_wait(10)
        #driver.maximize_window()

        nms_ip = str(nms_server.connections.linux.ip)
        username = nms_server.custom.gui_uname
        password = nms_server.custom.gui_pwd
        auto_user_ws = nms_server.custom.auto_user_ws
        ir500_eids = nms_server.custom.mesh_eids_ir500
        ir510_eids = nms_server.custom.mesh_eids_ir510
        meter_eids = nms_server.custom.mesh_eids_meter
        ir510_firmware_image = nms_server.custom.ir510_firmware_image
        ir510_fw_img_sch_tble = nms_server.custom.ir510_fw_img_sch_table
        mesh_image_path = os.getcwd() + '/image_files/mesh_firmware_images/' + str(ir510_firmware_image)
	
        driver.set_window_size(1920, 1080)
        # driver = webdriver.Firefox()
        driver.implicitly_wait(30)
        driver.maximize_window()

        cgmesh_pan_id = 7
        ver_chk_pan_id = 149
        stack_node_cnt = 2
        stack_node_cnt1 = 1
        def_fw_groupname = "default-ir500"
        cus_fw_groupname = "test-ir500"
        wisun_exp_subnet = "2111:abcd:0:0:0:0:0:0"
        wisun_exp_subnet1 = "2091:abcd:1111:2222:0:0:0:0"
        cncl_exp_str = "Cancel Wi-SUN Stack Switching?"
        stackmd_exp_str = "Once Switch to Wi-SUN Stack Schedule is initiated, movement of devices between groups are not advised. Are you sure to proceed ?"
        cancel_wisun_exp_str = "Unable to cancel stack mode operation. Reason: Nodes in the subnet %s has already been moved to Wi-SUN mode. Stack operation is not allowed" % wisun_exp_subnet
        stackmd_wisun_exp_str = "Unable to push stack mode. Reason: Nodes in the subnet %s has already been moved to Wi-SUN mode. Stack operation is not allowed" % wisun_exp_subnet
        stackmd_wisun_time_exp_str = "Unable to push stack mode switch time. Reason: Nodes in the subnet %s has already been moved to Wi-SUN mode. Stack operation is not allowed" % wisun_exp_subnet
        cancel_bfr_stk_exp_str = "Unable to cancel stack mode operation. Reason: Devices in the subnet %s. did not receive stack mode/time value. Please push stack mode/time and continue." % wisun_exp_subnet1
        stktm_bfr_stkmd_exp_str = "Unable to push stack mode switch time. Reason: Devices in the subnet %s. did not receive stack mode value. Please push stack mode and continue." % wisun_exp_subnet1
        pshstack_tme_msg_exp = "Scheduling stack mode time for subnet %s" % wisun_exp_subnet1 
        stackmd_cfm_exp_str = "Stack mode push operation initiated for PANID [\'%d\']" % cgmesh_pan_id
        stackmd_typ_exp = "Stack Mode Push"
        stktm_typ_exp = "Stack Switch Time Push"
        cncl_stkmd_typ_exp = "Stack Mode Cancel"
        pshstack_msg_exp = "Configuring stack mode for subnet %s" % wisun_exp_subnet1
        cancel_exp_str = "Successfully cancelled stack mode switch for PANID [\'%d\']"% cgmesh_pan_id
        cancel_msg_exp = "Cancelling stack mode switch for subnet %s" % wisun_exp_subnet1
        error_log_wis_nonwis = "Nodes in the subnet %s has already been moved to Wi-SUN mode. Stack operation is not allowed" % wisun_exp_subnet
        error_log_cncl_bfr_stkmd_nonwis = "Cancel stack operation not allowed for subnet %s. Please push stack mode/time to device and continue."%  wisun_exp_subnet1
        error_log_stktm_bfr_stkmd_nonwis = "Stack mode time operation not allowed for subnet %s. Please push stack mode to device and continue."%  wisun_exp_subnet1
        log_msg_stkmd = "Stack mode configuration sent to device."
        log_msg_skttm = "Stack mode time configuration sent to device."
        log_msg_cncl = "Cancelled stack mode configuration from device."
        same_dt_tm_exp_str = "Unable to push stack mode switch time. Reason: Schedule reload is already set to same date and time"
        abv_49_days_exp_str = "Unable to push stack mode switch time. Reason: Stack switch time scheduling is allowed for maximum of 49 days only. Scheduled date:"
        pshstack_ver_chk = "Unable to Switch Wi-SUN Stack. Reason: Devices in following subnets prefix: [%s] spanning across groups: [%s] need to be upgraded to the version equal to 6.2 MR" % (wisun_exp_subnet, def_fw_groupname)
        error_log_ver_chk = "Devices in following subnets prefix: [%s] spanning across groups: [%s] need to be upgraded to the version equal to 6.2 MR" % (wisun_exp_subnet, def_fw_groupname)
        fw_active_job = "Unable to push stack mode. Reason: Trying to push stack mode configuration for panid  [\'%s\'] with an already active firmware operation" % cgmesh_pan_id
        push_stack_md_active_job = "Unable to push stack mode. Reason: Exception when trying to push stack mode configuration for panid [\'%s\'] with an already active stack operation" % cgmesh_pan_id
        push_stack_tm_active_job = "Unable to push stack mode switch time. Reason: Exception when trying to set stack switch time for panid [\'%s\'] with an already active stack operation" % cgmesh_pan_id
        cancel_stack_active_job = "Unable to cancel stack mode operation. Reason: Exception when trying to cancel stack mode for panid [\'%s\'] with an already active stack operation" % cgmesh_pan_id

        driver_utils = ui_common_utils.DriverUtils(driver)
        driver = driver_utils.log_into_fnd(nms_ip, username, password)

        nms_ssh_client = test_utils.get_remote_ssh_client(server=str(nms_server.connections.linux.ip),
                                            username=nms_server.tacacs.username,
                                            password=nms_server.passwords.linux,
                                            timeout=90)

        self.parent.parameters.update(driver = driver)
        self.parent.parameters.update(nms_server = nms_server)
        self.parent.parameters.update(nms_ip = nms_ip)
        self.parent.parameters.update(username = username)
        self.parent.parameters.update(password = password)
        self.parent.parameters.update(properties_file_folder=properties_file_folder) 
        self.parent.parameters.update(test_start_time = test_utils.get_utc_curr_time())
        self.parent.parameters.update(ir500_eids = ir500_eids)
        self.parent.parameters.update(ir510_eids = ir510_eids)
        self.parent.parameters.update(meter_eids = meter_eids)
        self.parent.parameters.update(cgmesh_pan_id = cgmesh_pan_id)
        self.parent.parameters.update(cncl_exp_str = cncl_exp_str)
        self.parent.parameters.update(stackmd_exp_str = stackmd_exp_str)
        self.parent.parameters.update(cancel_wisun_exp_str = cancel_wisun_exp_str)
        self.parent.parameters.update(stackmd_wisun_exp_str = stackmd_wisun_exp_str)
        self.parent.parameters.update(stackmd_wisun_time_exp_str = stackmd_wisun_time_exp_str)
        self.parent.parameters.update(cancel_bfr_stk_exp_str = cancel_bfr_stk_exp_str)
        self.parent.parameters.update(stktm_bfr_stkmd_exp_str = stktm_bfr_stkmd_exp_str)
        self.parent.parameters.update(stack_node_cnt = stack_node_cnt)
        self.parent.parameters.update(stackmd_cfm_exp_str = stackmd_cfm_exp_str)
        self.parent.parameters.update(stackmd_typ_exp = stackmd_typ_exp)
        self.parent.parameters.update(stktm_typ_exp = stktm_typ_exp)
        self.parent.parameters.update(cncl_stkmd_typ_exp = cncl_stkmd_typ_exp)
        self.parent.parameters.update(pshstack_msg_exp = pshstack_msg_exp)
        self.parent.parameters.update(cancel_exp_str = cancel_exp_str)
        self.parent.parameters.update(cancel_msg_exp = cancel_msg_exp)
        self.parent.parameters.update(pshstack_tme_msg_exp=pshstack_tme_msg_exp)
        self.parent.parameters.update(error_log_wis_nonwis = error_log_wis_nonwis)
        self.parent.parameters.update(error_log_cncl_bfr_stkmd_nonwis = error_log_cncl_bfr_stkmd_nonwis)
        self.parent.parameters.update(error_log_stktm_bfr_stkmd_nonwis = error_log_stktm_bfr_stkmd_nonwis)
        self.parent.parameters.update(log_msg_stkmd = log_msg_stkmd)
        self.parent.parameters.update(log_msg_skttm = log_msg_skttm)
        self.parent.parameters.update(log_msg_cncl = log_msg_cncl)
        self.parent.parameters.update(mesh_image_path = mesh_image_path)
        self.parent.parameters.update(ir510_firmware_image = ir510_firmware_image)
        self.parent.parameters.update(ir510_fw_img_sch_tble = ir510_fw_img_sch_tble)
        self.parent.parameters.update(same_dt_tm_exp_str = same_dt_tm_exp_str)
        self.parent.parameters.update(abv_49_days_exp_str = abv_49_days_exp_str)
        self.parent.parameters.update(error_log_ver_chk = error_log_ver_chk)
        self.parent.parameters.update(pshstack_ver_chk = pshstack_ver_chk)
        self.parent.parameters.update(ver_chk_pan_id = ver_chk_pan_id)
        self.parent.parameters.update(stack_node_cnt1 = stack_node_cnt1)
        self.parent.parameters.update(cus_fw_groupname = cus_fw_groupname)
        self.parent.parameters.update(def_fw_groupname = def_fw_groupname)
        self.parent.parameters.update(fw_active_job = fw_active_job)
        self.parent.parameters.update(push_stack_md_active_job = push_stack_md_active_job)
        self.parent.parameters.update(push_stack_tm_active_job = push_stack_tm_active_job)
        self.parent.parameters.update(cancel_stack_active_job = cancel_stack_active_job)

###################################################################
###                  LOCAL METHODS                              ###
###################################################################

def Push_And_Verify_The_StackMode(driver, pan_id, stk_typ, lst_snt_msg, total_node, schd_stk_tm = None):
    """
    Method to Push/Cancel stack mode and verify the Stack operation status, Type, Log message sent and Scheduled stack change status
    :param stk_typ: Push stack type
    :param lst_snt_msg: Last sent message to verify
    :param total_node: Expected success node to verify
    :param schd_stk_tm: Optional Argument - Expected scheduled stack time
    :return:
    """
    stak_fin_typ = 'Stack Operation Finished'
    false_flag = True
    flag = 0
    flag1 = 0
    flag2 = 0
    stk_cnt = 0
    lst_snt_msg1 = 'Stack mode configuration sent to device.'
    log.info("##################################### \nVerify Overall \'%s\' type" % stk_typ)
    stack_status = driver.find_element_by_xpath("//div[@id='fwSubnetgrid']//div[@class='x-grid3-body']//table[@class='x-grid3-row-table']//div[@class='x-grid3-cell-inner x-grid3-col-panId' and contains(text(),\'%d\')]//parent::td//following-sibling::td[5]//div[@class='x-grid3-cell-inner x-grid3-col-stackOperationType']"% pan_id).text
    time.sleep(5)
    if stack_status in str(stk_typ):
        log.info("##### \'%s\' initiated successfully #####" % stack_status)
        if schd_stk_tm:
            log.info("Click on Refresh button")
            driver.find_element_by_xpath("//div[@id='fwSubnetListPagingToolbar']//table[@class='x-toolbar-ct']//td[@class='x-toolbar-right']"
                "//table[@class='x-toolbar-right-ct']//tr[@class='x-toolbar-right-row']//td//em/button[@type='button']").click()
            time.sleep(3)
            scheduled_dttm = driver.find_element_by_xpath("//div[@id='fwSubnetgrid']//div[@class='x-grid3-body']//table[@class='x-grid3-row-table']//div[@class='x-grid3-cell-inner x-grid3-col-panId' and contains(text(),'7')]"
                "//parent::td//following-sibling::td[7]//div[@class = 'x-grid3-cell-inner x-grid3-col-scheduledStackChange']").text
            if schd_stk_tm in scheduled_dttm:
                log.info("##### Verified: Scheduled date and time: %s is same as Scheduled stack change state: %s ##### " % (schd_stk_tm, scheduled_dttm))
            else:
                log.info("Verification Failed: Scheduled date and time: %s is not same as Scheduled stack change state: %s" % (schd_stk_tm, scheduled_dttm))
                false_flag = False
        timeout = time.time() + 60 * 5
        i = 0
        while timeout > time.time():
            i += 1
            log.info("%d - Click on Refresh button" % i)
            driver.find_element_by_xpath("//div[@id='fwSubnetListPagingToolbar']//table[@class='x-toolbar-ct']//td[@class='x-toolbar-right']"
                "//table[@class='x-toolbar-right-ct']//tr[@class='x-toolbar-right-row']//td//em/button[@type='button']").click()
            log.info("%d - Wait for 5 Seconds" % i)
            time.sleep(5)
            lst_msg = driver.find_element_by_xpath("//div[@id='fwSubnetgrid']//div[@class='x-grid3-body']//table[@class='x-grid3-row-table']//div[@class='x-grid3-cell-inner x-grid3-col-panId' and contains(text(),'7')]"
                "//parent::td//following-sibling::td[6]//div[@class = 'x-grid3-cell-inner x-grid3-col-message']").text
            psh_msg = lst_msg.split(']')
            msg = psh_msg[1]
            if lst_snt_msg in str(msg) or lst_snt_msg1 in str(msg):
                log.info("##### %s Last message verification success - %s ######" % (stk_typ, msg))
                flag = True
                break
            else:
                log.info("%d - Last message is not yet updated" % i)
                time.sleep(2)
                flag = False
                continue
        if not flag:
            log.info("\'%s\'Last message verification failed - %s\n#####################################" % (stk_typ, msg))
            false_flag = False
        else:
            timeout = time.time() + 60 * 10
            j = 0
            while timeout > time.time():
                j += 1
                log.info("%d - Click on Refresh button" % j)
                driver.find_element_by_xpath("//div[@id='fwSubnetListPagingToolbar']//table[@class='x-toolbar-ct']//td[@class='x-toolbar-right']"
                    "//table[@class='x-toolbar-right-ct']//tr[@class='x-toolbar-right-row']//td//em/button[@type='button']").click()
                log.info("%d - Wait for 5 Seconds"% j)
                time.sleep(5)
                stack_count = driver.find_element_by_xpath("//div[@id='fwSubnetgrid']//div[@class='x-grid3-body']//table[@class='x-grid3-row-table']//div[@class='x-grid3-cell-inner x-grid3-col-panId' and contains(text(),'7')]"
                    "//parent::td//following-sibling::td[4]//div[@class='x-grid3-cell-inner x-grid3-col-stackOperStatusCount']").text
                cnt = stack_count.split()
                if len(cnt) == 3:
                    stk_cnt = int(cnt[0])
                    if stk_cnt == total_node:
                        log.info("##### Overall %s success - \" Expected Nodes: \'%d\' is equal to Success Node: \'%d\' ######" % (stk_typ, total_node, stk_cnt))
                        flag1 = True
                        break
                    else:
                        time.sleep(5)
                        flag1 = False
                        continue
                else:
                    log.info("%d - Overall %s Not started" % (j, stk_typ))
                    time.sleep(2)
                    flag1 = False
                    continue
            if not flag1:
                log.info("Overall %s Failed - \" Total Node: \'%d\' is not equal to Success Node: \'%d\'\n#####################################" % (stk_typ, total_node, stk_cnt))
                false_flag = False
            else:
                timeout = time.time() + 60 * 5
                k = 0
                while timeout > time.time():
                    k += 1
                    log.info("%d - Click on Refresh button" % k)
                    driver.find_element_by_xpath("//div[@id='fwSubnetListPagingToolbar']//table[@class='x-toolbar-ct']//td[@class='x-toolbar-right']"
                        "//table[@class='x-toolbar-right-ct']//tr[@class='x-toolbar-right-row']//td//em/button[@type='button']").click()
                    log.info("%d - Wait for 5 Seconds" % k)
                    time.sleep(5)
                    log.info("Verify the overall final \'stack operation type\' state")
                    stack_status1 = driver.find_element_by_xpath("//div[@id='fwSubnetgrid']//div[@class='x-grid3-body']//table[@class='x-grid3-row-table']"
                        "//div[@class='x-grid3-cell-inner x-grid3-col-panId' and contains(text(),\'%d\')]"
                        "//parent::td//following-sibling::td[5]//div[@class='x-grid3-cell-inner x-grid3-col-stackOperationType']" % pan_id).text
                    if stack_status1 in stak_fin_typ:
                        log.info("##### Verified: Stack operation status has reached the final state - %s #####" % (stack_status1))
                        log.info("#####################################") 
                        flag2 = True
                        break
                    else:
                        log.info("%d - Overall Stack operation type %s Not finished" % (k, stk_typ))
                        time.sleep(5)
                        flag2 = False
                        continue
            if not flag2:
                log.info("Verification Failed: Stack operation status: %s is not same as Expected: %s" % (stack_status, stak_fin_typ))
                log.info("#####################################")
                false_flag = False
    else:
        log.info("Failed to initiate \'%s\'\n#####################################" % stk_typ)
        false_flag = False
    return false_flag 

def Push_And_Verify_The_StackMode_In_Custom_Group(driver, pan_id, stk_typ, lst_snt_msg, total_node, schd_stk_tm = None):
    """
    Method to Push/Cancel stack mode and verify the Stack operation status, Type, Log message sent and Scheduled stack change status
    :param stk_typ: Push stack type
    :param lst_snt_msg: Last sent message to verify
    :param total_node: Expected success node to verify
    :param schd_stk_tm: Optional Argument - Expected scheduled stack time
    :return:
    """
    stak_fin_typ = 'Stack Operation Finished'
    false_flag = True
    flag = 0
    flag1 = 0
    flag2 = 0
    stk_cnt = 0
    lst_snt_msg1 = 'Stack mode configuration sent to device.'
    log.info("##################################### \nVerify Overall \'%s\' type" % stk_typ)
    if schd_stk_tm:
        log.info("Click on Refresh button")
        driver.find_element_by_xpath("//div[@id='fwSubnetListPagingToolbar']//table[@class='x-toolbar-ct']//td[@class='x-toolbar-right']"
            "//table[@class='x-toolbar-right-ct']//tr[@class='x-toolbar-right-row']//td//em/button[@type='button']").click()
        time.sleep(3)
        scheduled_dttm = driver.find_element_by_xpath("//div[@id='fwSubnetgrid']//div[@class='x-grid3-body']//table[@class='x-grid3-row-table']//div[@class='x-grid3-cell-inner x-grid3-col-panId' and contains(text(),'7')]"
            "//parent::td//following-sibling::td[7]//div[@class = 'x-grid3-cell-inner x-grid3-col-scheduledStackChange']").text
        if schd_stk_tm in scheduled_dttm:
            log.info("##### Verified: Scheduled date and time: %s is same as Scheduled stack change state: %s ##### " % (schd_stk_tm, scheduled_dttm))
        else:
            log.info("Verification Failed: Scheduled date and time: %s is not same as Scheduled stack change state: %s" % (schd_stk_tm, scheduled_dttm))
            false_flag = False
    timeout = time.time() + 60 * 5
    i = 0
    while timeout > time.time():
        i += 1
        log.info("%d - Click on Refresh button" % i)
        driver.find_element_by_xpath("//div[@id='fwSubnetListPagingToolbar']//table[@class='x-toolbar-ct']//td[@class='x-toolbar-right']"
            "//table[@class='x-toolbar-right-ct']//tr[@class='x-toolbar-right-row']//td//em/button[@type='button']").click()
        log.info("%d - Wait for 5 Seconds" % i)
        time.sleep(5)
        lst_msg = driver.find_element_by_xpath("//div[@id='fwSubnetgrid']//div[@class='x-grid3-body']//table[@class='x-grid3-row-table']//div[@class='x-grid3-cell-inner x-grid3-col-panId' and contains(text(),'7')]"
            "//parent::td//following-sibling::td[6]//div[@class = 'x-grid3-cell-inner x-grid3-col-message']").text
        psh_msg = lst_msg.split(']')
        msg = psh_msg[1]
        if lst_snt_msg in str(msg) or lst_snt_msg1 in str(msg):
            log.info("##### %s Last message verification success - %s ######" % (stk_typ, msg))
            flag = True
            break
        else:
            log.info("%d - Last message is not yet updated" % i)
            time.sleep(2)
            flag = False
            continue
    if not flag:
        log.info("\'%s\'Last message verification failed - %s\n#####################################" % (stk_typ, msg))
        false_flag = False
    else:
        timeout = time.time() + 60 * 10
        j = 0
        while timeout > time.time():
            j += 1
            log.info("%d - Click on Refresh button" % j)
            driver.find_element_by_xpath("//div[@id='fwSubnetListPagingToolbar']//table[@class='x-toolbar-ct']//td[@class='x-toolbar-right']"
                "//table[@class='x-toolbar-right-ct']//tr[@class='x-toolbar-right-row']//td//em/button[@type='button']").click()
            log.info("%d - Wait for 5 Seconds"% j)
            time.sleep(5)
            stack_count = driver.find_element_by_xpath("//div[@id='fwSubnetgrid']//div[@class='x-grid3-body']//table[@class='x-grid3-row-table']//div[@class='x-grid3-cell-inner x-grid3-col-panId' and contains(text(),'7')]"
                "//parent::td//following-sibling::td[4]//div[@class='x-grid3-cell-inner x-grid3-col-stackOperStatusCount']").text
            cnt = stack_count.split()
            if len(cnt) == 3:
                stk_cnt = int(cnt[0])
                if stk_cnt == total_node:
                    log.info("##### Overall %s success - \" Expected Nodes: \'%d\' is equal to Success Node: \'%d\' ######" % (stk_typ, total_node, stk_cnt))
                    flag1 = True
                    break
                else:
                    time.sleep(5)
                    flag1 = False
                    continue
            else:
                log.info("%d - Overall %s Not started" % (j, stk_typ))
                time.sleep(2)
                flag1 = False
                continue
    if not flag1:
        log.info("Overall %s Failed - \" Total Node: \'%d\' is not equal to Success Node: \'%d\'\n#####################################" % (stk_typ, total_node, stk_cnt))
        false_flag = False
    else:
        timeout = time.time() + 60 * 5
        k = 0
        while timeout > time.time():
            k += 1
            log.info("%d - Click on Refresh button" % k)
            log.info("%d - Click on Refresh button" % k)
            driver.find_element_by_xpath("//div[@id='fwSubnetListPagingToolbar']//table[@class='x-toolbar-ct']//td[@class='x-toolbar-right']"
                "//table[@class='x-toolbar-right-ct']//tr[@class='x-toolbar-right-row']//td//em/button[@type='button']").click()
            log.info("%d - Wait for 5 Seconds" % k)
            time.sleep(5)
            log.info("Verify the overall final \'stack operation type\' state")
            stack_status1 = driver.find_element_by_xpath("//div[@id='fwSubnetgrid']//div[@class='x-grid3-body']//table[@class='x-grid3-row-table']"
                "//div[@class='x-grid3-cell-inner x-grid3-col-panId' and contains(text(),\'%d\')]"
                "//parent::td//following-sibling::td[5]//div[@class='x-grid3-cell-inner x-grid3-col-stackOperationType']" % pan_id).text
            if stack_status1 in stak_fin_typ:
                log.info("##### Verified: Stack operation status has reached the final state - %s #####" % (stack_status1))
                log.info("#####################################")
                flag2 = True
                break
            else:
                log.info("%d - Overall Stack operation type %s Not finished" % (k, stk_typ))
                time.sleep(5)
                flag2 = False
                continue
    if not flag2:
        log.info("Verification Failed: Stack operation status: %s is not same as Expected: %s" % (stack_status, stak_fin_typ))
        log.info("#####################################")
        false_flag = False
    return false_flag

def Verify_Push_Stackmode_State_Changes(driver, cur_group, eids):
    """
    Method to Verify the push stack mode - stack change status in device tab
    :param cur_group:   Firmware group name
    :param eids: Mesh Eids to verify the state
    :return: True/False
    """
    val = []
    flag = True
    log.info("##### Verify \'Push Stack Mode\' state Changes for \'%s\' Nodes #####" % eids)
    driver.find_element_by_xpath("//li[@id='fwTabs__deviceTab']//span[text()='Devices']").click()
    time.sleep(3)
    for eid in eids:
        i = 0
        timeout = time.time() + 60 * 5
        while timeout > time.time():
            i += 1
            log.info('%d - Refresh the page' % i)
            driver.find_element_by_xpath('//span[contains(text(),"%s")]' % cur_group).click()
            time.sleep(2)
            log.info("%d - Wait for 2 seconds"% i)
            stk_ch_stats = driver.find_element_by_xpath("//a[contains(text(),'%s')]//parent::div//parent::td//following-sibling::td[15]" \
                "//div[@class='x-grid3-cell-inner x-grid3-col-17']" % eid).text
            if 'Configured StackMode' in stk_ch_stats:
                log.info("##### \'%s\' Node has moved to \'Configured StackMode\' state #####" % eid)
                val.append(eid)
                break
            elif 'Configuring StackMode' in stk_ch_stats:
                time.sleep(2)
                driver.find_element_by_xpath('//span[contains(text(),"%s")]' % cur_group).click()
                log.info("%d - \'%s\' Node is in \'Configuring StackMode\' state"% (i, eid))
                time.sleep(1)
                continue
            else:
                continue
    if len(val) == len(eids):
        log.info("Verified: All the nodes are moved to \'Configured StackMode state\'")
    else:
        log.info("Failed: All the nodes failed to moved to \'Configured StackMode state\'")
        flag = False
    return flag 

def Verify_Push_Stackmode_time_State_Changes(driver, cur_group, eids, stk_typ, schd_stk_tm):
    """
    Method to Verify the push stack mode time - stack change status in device tab
    :param cur_group: Firmware group name
    :param eids: Mesh Eids to verify the state
    :param stk_typ: Push stack type
    :param schd_stk_tm: Expected scheduled stack time
    :return: True/False
    """
    val = []
    val1 = []
    flag = True
    log.info("Verify Overall \'%s\' type" % stk_typ)
    stack_status = driver.find_element_by_xpath(
        "//div[@id='fwSubnetgrid']//div[@class='x-grid3-body']//table[@class='x-grid3-row-table']//div[@class='x-grid3-cell-inner x-grid3-col-panId' and contains(text(),'7')]"
        "//parent::td//following-sibling::td[5]//div[@class='x-grid3-cell-inner x-grid3-col-stackOperationType']").text
    time.sleep(5)
    if stack_status in str(stk_typ):
        log.info("##### \'%s\' initiated successfully #####" % stack_status)
        log.info("Click on Refresh button")
        driver.find_element_by_xpath("//div[@id='fwSubnetListPagingToolbar']//table[@class='x-toolbar-ct']//td[@class='x-toolbar-right']"
                "//table[@class='x-toolbar-right-ct']//tr[@class='x-toolbar-right-row']//td//em/button[@type='button']").click()
        time.sleep(3)
        scheduled_dttm = driver.find_element_by_xpath("//div[@id='fwSubnetgrid']//div[@class='x-grid3-body']//table[@class='x-grid3-row-table']//div[@class='x-grid3-cell-inner x-grid3-col-panId' and contains(text(),'7')]"
                "//parent::td//following-sibling::td[7]//div[@class = 'x-grid3-cell-inner x-grid3-col-scheduledStackChange']").text
        log.info("Scheduled stack time - %s" % scheduled_dttm)
    else:
        log.info("Failed to initiate \'%s\'" % stk_typ)
    log.info("##### Verify the \'Scheduled Stack Time\' for \'%s\' Nodes #####" % eids)
    driver.find_element_by_xpath("//li[@id='fwTabs__deviceTab']//span[text()='Devices']").click()
    time.sleep(3)
    log.info('Refresh the page')
    driver.find_element_by_xpath('//span[contains(text(),"%s")]' % cur_group).click()
    log.info("Wait for 2 seconds")
    time.sleep(2)
    for eid in eids:
        driver.find_element_by_xpath('//span[contains(text(),"%s")]' % cur_group).click()
        time.sleep(2)
        sch_tm = driver.find_element_by_xpath("//a[contains(text(),'%s')]//parent::div//parent::td//following-sibling::td[16]"
                                          "//div[@class='x-grid3-cell-inner x-grid3-col-18']" % eid).text
        if sch_tm in scheduled_dttm:
            log.info("\'%s\' - Node has received the \'Scheduled Stack Time\' - %s "% (eid, sch_tm))
            val1.append(eid)
        else:
            log.info("\'%s\' - Node has received the \'Scheduled Stack Time\' - %s "% (eid, sch_tm))
    if len(val1) == len(eids):
        log.info("Verified: All the nodes has got the \'scheduled stack time\'")
    else:
        log.info("Failed: All the nodes failed to get the \'scheduled stack time\'")
        flag = False
    log.info("##### Verify \'Push Stack Mode Time\' state Changes #####")
    driver.find_element_by_xpath("//li[@id='fwTabs__deviceTab']//span[text()='Devices']").click()
    time.sleep(3)
    for eid in eids:
        i = 0
        timeout = time.time() + 60 * 5
        while timeout > time.time():
            i += 1
            log.info('%d - Refresh the page' % i)
            driver.find_element_by_xpath('//span[contains(text(),"%s")]' % cur_group).click()
            time.sleep(2)
            log.info("%d - Wait for 2 seconds"% i)
            stk_ch_stats = driver.find_element_by_xpath("//a[contains(text(),'%s')]//parent::div//parent::td//following-sibling::td[15]" \
                "//div[@class='x-grid3-cell-inner x-grid3-col-17']" % eid).text
            if 'Success' in stk_ch_stats:
                log.info("##### \'%s\' Node has moved to \'Success\' state #####" % eid)
                val.append(eid)
                break
            elif 'Scheduling StackModeTime' in stk_ch_stats:
                time.sleep(2)
                driver.find_element_by_xpath('//span[contains(text(),"%s")]' % cur_group).click()
                log.info("%d - \'%s\' Node is in \'Scheduling StackModeTime\' state"% (i, eid))
                time.sleep(1)
                continue
            else:
                continue
    if len(val) == len(eids):
        log.info("Verified: All the nodes are moved to \'Success\' state")
    else:
        log.info("Failed: All the nodes failed to moved to \'Success\' state")
        flag = False
    return flag

def Verify_Cancel_Stackmode_State_Changes(driver, cur_group, eids):
    """
    Method to Verify the cancel stack mode - stack change status in device tab
    :param cur_group: Firmware group name
    :param eids: Mesh Eids to verify the state
    :return: True/False
    """
    val = []
    flag = True
    log.info("##### Verify \'Cancel Stack Mode\' state Changes for \'%s\' Nodes #####" % eids)
    driver.find_element_by_xpath("//li[@id='fwTabs__deviceTab']//span[text()='Devices']").click()
    time.sleep(3)
    for eid in eids:
        i = 0
        timeout = time.time() + 60 * 5
        while timeout > time.time():
            i += 1
            log.info('%d - Refresh the page' % i)
            driver.find_element_by_xpath('//span[contains(text(),"%s")]' % cur_group).click()
            time.sleep(2)
            log.info("%d - Wait for 2 seconds"% i)
            stk_ch_stats = driver.find_element_by_xpath("//a[contains(text(),'%s')]//parent::div//parent::td//following-sibling::td[15]" \
                "//div[@class='x-grid3-cell-inner x-grid3-col-17']" % eid).text
            if 'Cancelled StackMode Switch' in stk_ch_stats:
                log.info("##### \'%s\' Node has moved to \'Cancelled StackMode Switch\' state #####" % eid)
                val.append(eid)
                break
            elif 'Cancelling StackMode Switch' in stk_ch_stats:
                time.sleep(2)
                driver.find_element_by_xpath('//span[contains(text(),"%s")]' % cur_group).click()
                log.info("%d - \'%s\' Node is in \'Cancelling StackMode Switch\' state"% (i, eid))
                time.sleep(1)
                continue
            else:
                continue
    if len(val) == len(eids):
        log.info("Verified: All the nodes are moved to \'Cancelled StackMode Switch\'")
    else:
        log.info("Failed: All the nodes failed to moved to \'Cancelled StackMode Switch\'")
        flag = False
    return flag

def Upload_image_To_Mesh_nodes(driver, def_fw_groupname, mesh_image_path, ir510_firmware_image, ir510_fw_img_sch_tble):
    try:
        flag = False
        show_result = []
        log.info('Click on Images tab')
        driver.find_element_by_xpath("//li[@id='mainPnltree__imgsTab']//span[text()='Images']").click()
        time.sleep(1)

        log.info('Click on Endpoints in the left plane')
        driver.find_element_by_xpath("//div[@id='imagesTree']//span[text()='ENDPOINT']").click()
        time.sleep(1)

        output = driver.find_elements_by_xpath(
            "//div[@id='fwImagesGrid']//div[@class='x-panel-body']//div[@class='x-grid3']//div[@class='x-grid3-scroller']//div[@class='x-grid3-body']//table[@class='x-grid3-row-table']/tbody/tr[1]/td[1]/div[@class='x-grid3-cell-inner x-grid3-col-name']")
        for i in output:
            if i.text: show_result.append(i.text)
            else: log.info('Show output is empty')
        if ir510_fw_img_sch_tble in show_result:
            log.info("Firmware image \'%s\' is already uploaded to FND" % ir510_fw_img_sch_tble)
        else:
            log.info("Firmware image \'%s\' not found in Fw image list. Uploading the image "% ir510_fw_img_sch_tble)
            log.info('Click on Add (+) button')
            driver.find_element_by_xpath("//div[@id='firmwareImages_toolsContainer']/div").click()

            log.info('Browse for Endpoint image - %s' % mesh_image_path)
            file_input = driver.find_element_by_xpath("//input[@id='formchfilefile']")
            driver.execute_script(
                'arguments[0].style = ""; arguments[0].style.display = "block"; arguments[0].style.visibility = "visible";',
                file_input)

            file_input.send_keys(mesh_image_path)
            time.sleep(2)

            log.info('Click on Add file button')
            driver.find_element_by_xpath("//button[text()='Add File']").click()
            time.sleep(2)

            timeout = time.time() + 60 * 5
            while timeout > time.time():
                try:
                    if "Adding file to IoT-FND" in driver.find_element_by_xpath(
                            "//span[text()='Adding file to IoT-FND ...']").text:
                        continue
                    else:
                        break
                except:
                    break

            log.info('Click on Ok button')
            driver.find_element_by_xpath("//button[text()='OK']").click()
            time.sleep(2)

            #driver.find_element_by_xpath("//div[@class=' x-window x-window-plain x-resizable-pinned'][contains(@style,'visibility: visible;')]//span[contains(text(),'Add Firmware Image')]/..//div[@class='x-tool x-tool-close']").click()
            #time.sleep(3)
            log.info("File added to NMS!")

        log.info('Navigate to Group tab')
        driver.find_element_by_xpath("//li[@id='mainPnltree__grpsTab']//span[text()='Groups']").click()
        time.sleep(1)

        log.info('Click on %s group in the left plane' % def_fw_groupname)
        driver.find_element_by_xpath(
            "//div[@id='leftHandTree']//span[contains(text(),'" + def_fw_groupname + "')]").click()
        time.sleep(1)
        driver_utils.ignore_flash_error()

        log.info('Navigate to Transmission Settings tab in the right plane')
        driver.find_element_by_xpath(
            "//li[@id='fwTabs__endpointTransmissionTab']//span[text()='Transmission Settings']").click()
        time.sleep(1)
        driver.find_element_by_xpath("//input[@id='settingsType']/..//img").click()
        log.info('Set the Transmission speed to Fast')
        driver.find_element_by_xpath(
            "//div[@class='x-layer x-combo-list '][contains(@style,'visibility: visible;')]//div[text()='Fast']").click()
        driver.find_element_by_xpath("//i[@class='fa fa-floppy-o']").click()
        time.sleep(3)
        log.info('Click on Ok button')
        driver.find_element_by_xpath("//button[text()='OK']").click()

        log.info('Click on %s group in the left plane' % def_fw_groupname)
        driver.find_element_by_xpath(
            "//div[@id='leftHandTree']//span[contains(text(),'" + def_fw_groupname + "')]").click()
        time.sleep(1)
        driver_utils.ignore_flash_error()

        time.sleep(3)
        log.info('Click on File Managemennt tab in the right plane')
        driver.find_element_by_xpath("//li[@id='fwTabs__mgmtTab']//span[text()='Firmware Management']").click()

        log.info("Start Uploading Image")
        time.sleep(1)
        driver.find_element_by_xpath("//table[@id='startDownloadButtona']//button[text()='Upload Image']").click()
        time.sleep(1)

        log.info("Choose the Type as RF")
        driver.find_element_by_xpath("//input[@id='comboImageType']/..//img").click()
        time.sleep(3)
        driver.find_element_by_xpath(
            "//div[@class='x-layer x-combo-list '][contains(@style,'visibility: visible;')]//div[text()='RF']").click()

        log.info("Choose the firmware image - %s" % ir510_firmware_image)
        driver.find_element_by_xpath("//input[@id='comboFI']/..//img").click()
        time.sleep(3)
        driver.find_element_by_xpath(
            "//div[@class='x-layer x-combo-list '][contains(@style,'visibility: visible;')]//div[text()='%s']" % ir510_firmware_image).click()
        driver.find_element_by_xpath("//input[@id='checkImageDiff']").click()
        time.sleep(3)
        driver.find_element_by_xpath("//div[@id='fdPanelForm']//button[text()='Upload Image']").click()
        time.sleep(2)

        log.info('Clicking on OK button')
        driver.find_element_by_xpath("//button[text()='OK']").click()
        time.sleep(2)

        log.info("Uploading Image Started")
        driver_utils.ignore_flash_error()

        timeout = time.time() + 60 * 30
        flag = False
        while timeout > time.time():
            status_text = driver.find_element_by_xpath(
                "//div[@id='firmare-details-panel']//td[text()='Current Status:']/..//td[2]").text

            if 'Finished' in status_text:
                log.info("Firmware upload completed!")
                flag = True
                break
            elif 'Image Loading' in status_text:
                log.info("Firmware upload status -" + status_text)
                time.sleep(30)
                driver.find_element_by_xpath(
                    "//div[@id='leftHandTree']//span[contains(text(),'" + def_fw_groupname + "')]").click()
                time.sleep(1)
                driver_utils.ignore_flash_error()
                time.sleep(1)
                continue
            else:
                continue

        if flag:
            time.sleep(5)
            log.info(banner('Getting the latest AuditTrails.'))
            audit_trail = ui_common_utils.AuditTrail(driver)
            audittrails = audit_trail.get_latest_audittrails()
            operation = audittrails['operations']

            log.info('operation: %s' % operation)
            if 'Firmware download started' not in operation:
                raise Exception('Did not see the "Firmware image is added to NMS" AuditTrail.')
            else:
                log.info("Test Script completed")
            log.info("Assertion Pass!")
        else:
            log.info("Stopping upload")
            time.sleep(5)
            driver.find_element_by_xpath("//div[@id='firmare-details-panel']//a[text()='Stop Upload']").click()
            driver.find_element_by_xpath("//button[text()='Yes']").click()
            driver.find_element_by_xpath("//button[text()='OK']").click()
            time.sleep(1)
            driver_utils.ignore_flash_error()
            time.sleep(1)

            timeout = time.time() + 60 * 5
            while timeout > time.time():
                status_text = driver.find_element_by_xpath(
                    "//div[@id='firmare-details-panel']//td[text()='Current Status:']/..//td[2]").text

                if 'Upload Stopped' in status_text:
                    log.info("Firmware upload Stopped!")
                    break
                elif 'Upload Stopping' in status_text:
                    log.info("Firmware upload status -" + status_text)
                    time.sleep(10)
                    driver.find_element_by_xpath(
                        "//div[@id='leftHandTree']//span[contains(text(),'" + def_fw_groupname + "')]").click()
                    time.sleep(1)
                    driver_utils.ignore_flash_error()
                    time.sleep(1)
                    continue

    except Exception as ex:
        flag = False 
        log.error(ex)
    return flag

def Schedule_Reload_To_Mesh_Nodes(driver, def_fw_groupname, ir510_firmware_image, sch_time):
     
    log.info("Clicking on \'%s\' group"% def_fw_groupname)
    driver.find_element_by_xpath(
        "//div[@id='leftHandTree']//span[contains(text(),'" + def_fw_groupname + "')]").click()
    time.sleep(2)
    driver_utils.ignore_flash_error()

    log.info('Navigate to Firmware Management tab in the right plane')
    driver.find_element_by_xpath("//li[@id='fwTabs__mgmtTab']//span[text()='Firmware Management']").click()
    time.sleep(1)

    log.info("Clicking on schedule reload button for \'%s\' image" % ir510_firmware_image)
    driver.find_element_by_xpath(
        "//div[@id='mgmtGrid']//div[@class='x-grid3-scroller']//div[@class='x-grid3-cell-inner x-grid3-col-image'and contains(text(), \'%s\')]"
        "//parent::td//following-sibling::td//div[@class='x-grid3-cell-inner x-grid3-col-10']//img[contains(@class,'sched-reload')]" % ir510_firmware_image).click()

    time.sleep(1)
    driver.find_element_by_xpath("//button[text()='Yes']").click()
    time.sleep(1)
    driver.find_element_by_xpath("//input[@id='rebootDTFtime']").clear()
    driver.find_element_by_xpath("//input[@id='rebootDTFtime']").send_keys(sch_time)
    time.sleep(2)

    #driver.find_element_by_xpath("//input[@id='rebootDTFdate']/../img").click()
    #time.sleep(1)
    #driver.find_element_by_xpath("//button[text()='Today']").click()
    #time.sleep(2)

    driver.find_element_by_xpath("//button[text()='Set Reboot Time']").click()
    time.sleep(2)
    driver.find_element_by_xpath("//button[text()='OK']").click()
    log.info("Set Reboot time!")
    time.sleep(1)
    driver_utils.ignore_flash_error()
    time.sleep(3)

    timeout = time.time() + 60 * 5
    flag = False
    while timeout > time.time():
        status_text = driver.find_element_by_xpath(
            "//div[@id='firmare-details-panel']//td[text()='Current Status:']/..//td[2]").text

        if 'Reload Scheduling Finished' in status_text:
            log.info("Reload Scheduling Finished!")
            flag = True
            break
        elif 'Install Image Scheduling' in status_text:
            log.info("Reload Scheduling  -" + status_text)
            time.sleep(10)
            driver.find_element_by_xpath(
                "//div[@id='leftHandTree']//span[contains(text(),'" + def_fw_groupname + "')]").click()
            time.sleep(1)
            driver_utils.ignore_flash_error()
            time.sleep(1)
            continue
        elif 'Scheduling Reload' in status_text:
            log.info("Reload Scheduling  -" + status_text)
            time.sleep(10)
            driver.find_element_by_xpath(
                "//div[@id='leftHandTree']//span[contains(text(),'" + def_fw_groupname + "')]").click()
            time.sleep(1)
            driver_utils.ignore_flash_error()
            time.sleep(1)
            continue
        else:
            continue
    return flag


def Cancel_Scheduled_Reload(driver, def_fw_groupname):
    log.info('Click on cancel reload button')
    driver.find_element_by_xpath("//div[@id='menu']//a[@href='#']").click()
    time.sleep(2)
    driver.find_element_by_xpath("//button[text()='Yes']").click()
    time.sleep(2)
    driver.find_element_by_xpath("//button[text()='OK']").click()
    log.info("Set Cancel Reload!")
    time.sleep(1)
    driver_utils.ignore_flash_error()
    time.sleep(3)
    timeout = time.time() + 60 * 20
    flag = False
    while timeout > time.time():
        status_text = driver.find_element_by_xpath(
            "//div[@id='firmare-details-panel']//td[text()='Current Status:']/..//td[2]").text

        if 'Cancel Install Image Finished' in status_text:
            log.info("Cancel Reload completed!")
            flag = True
            break
        elif 'Cancel Install Image Scheduling' in status_text:
            log.info("Cancel reload status -" + status_text)
            time.sleep(30)
            driver.find_element_by_xpath(
                "//div[@id='leftHandTree']//span[contains(text(),'" + def_fw_groupname + "')]").click()
            time.sleep(1)
            driver_utils.ignore_flash_error()
            time.sleep(1)
            continue
        elif 'Cancel Install Image Running' in status_text:
            log.info("Cancel reload status -" + status_text)
            time.sleep(30)
            driver.find_element_by_xpath(
                "//div[@id='leftHandTree']//span[contains(text(),'" + def_fw_groupname + "')]").click()
            time.sleep(1)
            driver_utils.ignore_flash_error()
            time.sleep(1)
            continue
        else:
            continue
    return flag

def Get_Nms_Date_And_Time(self, nms_server):
    """
    Get the FNDs date and time
    """
    log.info(banner('Get NMS Time and Date'))
    try:
        out = nms_server.execute('echo \$\(date \'+%Y-%m-%d %H:%M:%S\'\)', ignore_exit_code=[1], timeout=300)
        dttm = out.split(' ')
        cur_date = dttm[0]
        cur_time = dttm[1][:-4]
        log.info('Current FND date is \'%s\' and time is \'%s\''% (cur_date, cur_time))
    except Exception as msg:
        log.info('\t\tFailed to get date and time from command line')
    return cur_date, cur_time

##############################################################################################################################

#######################################################################
###                          TESTCASE BLOCK                         ###
#######################################################################

#Testcase 1
class Tc1_Validate_Cancel_Stackmode_When_Panid_One_In_Wisun_Another_In_CGMesh(aetest.Testcase):
    @aetest.test
    def Tc1_Validate_Cancel_Stackmode_When_Panid_One_In_Wisun_Another_In_CGMesh(self, driver, cncl_exp_str, cancel_wisun_exp_str, error_log_cncl_bfr_stkmd_nonwis, 
                                                                                 cancel_bfr_stk_exp_str, cgmesh_pan_id, error_log_wis_nonwis):
        try:
            global driver_utils
            global auto_user_ws
            import datetime
            fw_groupname = "default-ir500"

            last_line_number = \
                test_utils.read_remote_logs(remote_ssh_client=nms_ssh_client, log_file=log_file, get_last_line=True)[
                    0].rstrip()

            driver_utils.navigate_to_home()
            fw_up = ui_common_utils.FirmwareUpdate(driver)
            fw_up.nav_sub_menu('firmware_update')
            time.sleep(2)
            driver_utils.ignore_flash_error()

            driver.find_element_by_xpath(
                "//div[@id='leftHandTree']//span[contains(text(),'" + fw_groupname + "')]").click()
            time.sleep(2)
            driver_utils.ignore_flash_error()  

            log.info('Navigate to Firmware Management tab in the right plane')
            driver.find_element_by_xpath("//li[@id='fwTabs__mgmtTab']//span[text()='Firmware Management']").click()
            time.sleep(1)      

            log.info("Clicking on \"Clear Filter\" button")
            driver.find_element_by_xpath("//div[@id='fwSubnetListPagingToolbar']/table[@class='x-toolbar-ct']"
                                         "//td[@class='x-toolbar-left']/table//tr[@class='x-toolbar-left-row']/td[1]/table//button[@type='button']").click()
            time.sleep(2)

            log.info("Select all the checkbox")
            driver.find_element_by_xpath("//div[@id='fwSubnetgrid']/div[@class='x-panel-bwrap']/div[3]/div[@class='x-grid3']"
                                         "//div[@class='x-grid3-header-inner']//tr/td[1]/div").click()
            time.sleep(2)

            log.info("Clicking on \"Cancel StackMode\" button")
            driver.find_element_by_xpath("//table[@id='cancelStackPush']//em/button[@type='button']").click()
            time.sleep(2)

            log.info("Verify the Cancel switching pop-up message")
            cn_str = driver.find_element_by_xpath("//div[@class='x-window-bwrap']//div[@class='x-window-body']//span[@class='ext-mb-text']").text
            if cncl_exp_str in str(cn_str): log.info ("Verified: \"%s\"" % cn_str)
            else: self.failed(banner("Pop-up message Verification failed - \'%s\'\nExpected: \'%s\'") % (cn_str, cncl_exp_str))
            time.sleep(1)

            log.info("Clicking on \"yes\" button")
            driver.find_element_by_xpath("//button[text()='Yes']").click()
            time.sleep(2)

            dte = datetime.datetime.utcnow().strftime('%Y-%m-%d')

            log.info("Verify if already nodes are switched to WISUN pop-up message")
            wisun_str = driver.find_element_by_xpath("//div[@class='x-window-bwrap']//div[@class='x-window-body']//span[@class='ext-mb-text']").text
            if cancel_wisun_exp_str in str(wisun_str) or cancel_bfr_stk_exp_str in str(wisun_str): log.info ("Verified: \"%s\"" % wisun_str)
            else: self.failed(banner("Pop-up message Verification failed - \'%s\'\nExpected: \'%s\' or \'%s\'") % (wisun_str, cancel_wisun_exp_str, cancel_bfr_stk_exp_str))

            log.info("Clicking on \'OK\' button")
            driver.find_element_by_xpath("//button[text()='OK']").click()
            time.sleep(2)  

            log.info('Navigate to Logs tab in the right plane')
            driver.find_element_by_xpath("//li[@id='fwTabs__logTab']//span[text()='Logs']").click()
            time.sleep(4)

            log.info("Click on Refresh button")
            driver.find_element_by_xpath("//div[@id='logPageTB']//td[@class='x-toolbar-right']//tr[@class='x-toolbar-right-row']//table[@class='x-btn x-btn-icon']//button[@type='button']").click()
            time.sleep(1)  

            log.info("Verify cancel stack when combination of wisun and non-wisun in a pan id log message")
            message_list = [element.text for element in driver.find_elements_by_xpath(
                "//div[@id='firmwareMeshLog']//div[@class='x-grid3-body']//div//td[2]//div[contains(text(),'" + dte + "')]/../..//td[6]/div")]

            log.info('Event Message: %s' % message_list)
            #if error_log_wis_nonwis not in message_list or error_log_cncl_bfr_stkmd_nonwis not in message_list: raise Exception('Did not see \'%s\' Error in Event message' % error_log_wis_nonwis)
            #else: log.info("Verified: \'%s\' Error found in Event message"% error_log_wis_nonwis)
            if error_log_wis_nonwis in message_list or error_log_cncl_bfr_stkmd_nonwis in message_list: log.info("Verified: \'%s\' or \'%s\' Error found in Event message"% (error_log_wis_nonwis, error_log_cncl_bfr_stkmd_nonwis))
            else: raise Exception('Did not see either \'%s\' or \'%s\' Error in Event message' % (error_log_wis_nonwis, error_log_cncl_bfr_stkmd_nonwis))

        except Exception as ex:
            self.failed(ex)
            driver_utils.save_screenshot(scriptname='Tc1_Validate_Cancel_Stackmode_When_Panid_One_In_Wisun_Another_In_CGMesh', classname=__class__.__name__)

            log.info("Clicking on \'OK\' button") 
            driver.find_element_by_xpath("//button[text()='OK']").click()
            time.sleep(2) 

            try:
                error_logs = test_utils.read_remote_logs(remote_ssh_client=nms_ssh_client, log_file=log_file,
                                                         read_error_logs=True, line_number=last_line_number)
                assert error_logs == []
                log.info('No ERROR logs found on FND.')
            except AssertionError as ae:
                driver_utils.save_screenshot(scriptname='Tc1_Validate_Cancel_Stackmode_When_Panid_One_In_Wisun_Another_In_CGMesh', classname=__class__.__name__)
                log.error('Should not see ERROR logs on FND.\nerror_logs: %s' % error_logs)

#Testcase 2
class Tc2_VAlidate_Push_Stackmode_When_Panid_One_In_Wisun_Another_In_CGMesh(aetest.Testcase):
    @aetest.test
    def Tc2_Validate_Push_Stackmode_When_Panid_One_In_Wisun_Another_In_CGMesh(self, driver, stackmd_exp_str, stktm_bfr_stkmd_exp_str, 
                                                                                   error_log_stktm_bfr_stkmd_nonwis, stackmd_wisun_exp_str, error_log_wis_nonwis):
        try:
            global driver_utils
            global auto_user_ws
            import datetime
            fw_groupname = "default-ir500"

            last_line_number = \
                test_utils.read_remote_logs(remote_ssh_client=nms_ssh_client, log_file=log_file, get_last_line=True)[
                    0].rstrip()

            driver_utils.navigate_to_home()
            fw_up = ui_common_utils.FirmwareUpdate(driver)
            fw_up.nav_sub_menu('firmware_update')
            time.sleep(2)
            driver_utils.ignore_flash_error()

            driver.find_element_by_xpath(
                "//div[@id='leftHandTree']//span[contains(text(),'" + fw_groupname + "')]").click()
            time.sleep(2)
            driver_utils.ignore_flash_error()

            log.info('Navigate to Firmware Management tab in the right plane')
            driver.find_element_by_xpath("//li[@id='fwTabs__mgmtTab']//span[text()='Firmware Management']").click()
            time.sleep(1)  

            log.info("Clicking on \"Clear Filter\" button")
            driver.find_element_by_xpath("//div[@id='fwSubnetListPagingToolbar']/table[@class='x-toolbar-ct']//td[@class='x-toolbar-left']"
                                         "/table//tr[@class='x-toolbar-left-row']/td[1]/table//button[@type='button']").click()
            time.sleep(2)
            
            log.info("Select all the checkbox")
            driver.find_element_by_xpath("//div[@id='fwSubnetgrid']/div[@class='x-panel-bwrap']/div[3]/div[@class='x-grid3']"
                                         "//div[@class='x-grid3-header-inner']//tr/td[1]/div").click()
            time.sleep(2)

            dte = datetime.datetime.utcnow().strftime('%Y-%m-%d')
            
            log.info("Clicking on \"Push StackMode\" button")
            driver.find_element_by_xpath("//table[@id='stackModePush']//em/button[@type='button']").click()
            time.sleep(2)
            
            log.info("Verify Push stack mode pop-up message")
            stackmd_str = driver.find_element_by_xpath("//div[@class='x-window-bwrap']//div[@class='x-window-body']//span[@class='ext-mb-text']").text
            if stackmd_exp_str in str(stackmd_str): log.info ("Verified: \"%s\"" % stackmd_str)
            else: self.failed(banner("Pop-up message Verification failed - \'%s\'\nExpected: \'%s\'") % (stackmd_str, stackmd_exp_str))
            time.sleep(1)
            
            log.info("Clicking on \"yes\" button")
            driver.find_element_by_xpath("//button[text()='Yes']").click()
            time.sleep(2)
            
            log.info("Verify if already nodes are switched to WISUN pop-up message")
            wisun_str1 = driver.find_element_by_xpath("//div[@class='x-window-bwrap']//div[@class='x-window-body']//span[@class='ext-mb-text']").text
            if stackmd_wisun_exp_str in str(wisun_str1) or stktm_bfr_stkmd_exp_str in str(wisun_str1): log.info ("Verified: \"%s\"" % wisun_str1)
            else: self.failed(banner("Pop-up message Verification failed - \'%s\'\nExpected: \'%s\' or \'%s\'") % (wisun_str1, stackmd_wisun_exp_str, stktm_bfr_stkmd_exp_str))  

            log.info("Clicking on \'OK\' button")
            driver.find_element_by_xpath("//button[text()='OK']").click()
            time.sleep(2)    

            log.info('Navigate to Logs tab in the right plane')
            driver.find_element_by_xpath("//li[@id='fwTabs__logTab']//span[text()='Logs']").click()
            time.sleep(4)

            log.info("Click on Refresh button")
            driver.find_element_by_xpath("//div[@id='logPageTB']//td[@class='x-toolbar-right']//tr[@class='x-toolbar-right-row']//table[@class='x-btn x-btn-icon']//button[@type='button']").click()
            time.sleep(1)  

            log.info("Verify stackmode push when combination of wisun and non-wisun in a pan id log message")
            message_list = [element.text for element in driver.find_elements_by_xpath(
                "//div[@id='firmwareMeshLog']//div[@class='x-grid3-body']//div//td[2]//div[contains(text(),'" + dte + "')]/../..//td[6]/div")]

            log.info('Event Message: %s' % message_list)
            #if error_log_wis_nonwis not in message_list or error_log_stktm_bfr_stkmd_nonwis not in message_list: raise Exception('Did not see \'%s\' Error in Event message' % error_log_wis_nonwis)
            #else: log.info("Verified: \'%s\' Error found in Event message"% error_log_wis_nonwis)   
            if error_log_wis_nonwis in message_list or error_log_stktm_bfr_stkmd_nonwis in message_list: log.info("Verified: \'%s\' or \'%s\' Error found in Event message"% (error_log_wis_nonwis, error_log_stktm_bfr_stkmd_nonwis))
            else: raise Exception('Did not see either \'%s\' or \'%s\' Error in Event message' % (error_log_wis_nonwis, error_log_stktm_bfr_stkmd_nonwis))

        except Exception as ex:
            self.failed(ex)
            driver_utils.save_screenshot(scriptname='Tc2_Validate_Push_Stackmode_When_Panid_One_In_Wisun_Another_In_CGMesh', classname=__class__.__name__)

            log.info("Clicking on \'OK\' button") 
            driver.find_element_by_xpath("//button[text()='OK']").click()
            time.sleep(2) 

            try:
                error_logs = test_utils.read_remote_logs(remote_ssh_client=nms_ssh_client, log_file=log_file,
                                                         read_error_logs=True, line_number=last_line_number)
                assert error_logs == []
                log.info('No ERROR logs found on FND.')
            except AssertionError as ae:
                driver_utils.save_screenshot(scriptname='Tc2_Validate_Push_Stackmode_When_Panid_One_In_Wisun_Another_In_CGMesh', classname=__class__.__name__)
                log.error('Should not see ERROR logs on FND.\nerror_logs: %s' % error_logs)   

#Testcase 3
class Tc3_Validate_Push_Stackmode_Time_When_Panid_One_In_Wisun_Another_In_CGMesh(aetest.Testcase):
    @aetest.test
    def Tc3_Validate_Push_Stackmode_Time_When_Panid_One_In_Wisun_Another_In_CGMesh(self, driver, stackmd_exp_str, stktm_bfr_stkmd_exp_str,
                                                                                    error_log_stktm_bfr_stkmd_nonwis, stackmd_wisun_time_exp_str, error_log_wis_nonwis):
        try:
            global driver_utils
            global auto_user_ws
            import datetime
            fw_groupname = "default-ir500"

            last_line_number = \
                test_utils.read_remote_logs(remote_ssh_client=nms_ssh_client, log_file=log_file, get_last_line=True)[
                    0].rstrip()

            driver_utils.navigate_to_home()
            fw_up = ui_common_utils.FirmwareUpdate(driver)
            fw_up.nav_sub_menu('firmware_update')
            time.sleep(2)
            driver_utils.ignore_flash_error()

            driver.find_element_by_xpath(
                "//div[@id='leftHandTree']//span[contains(text(),'" + fw_groupname + "')]").click()
            time.sleep(2)
            driver_utils.ignore_flash_error()

            log.info('Navigate to Firmware Management tab in the right plane')
            driver.find_element_by_xpath("//li[@id='fwTabs__mgmtTab']//span[text()='Firmware Management']").click()
            time.sleep(1)                          

            log.info("Clicking on \"Clear Filter\" button")
            driver.find_element_by_xpath("//div[@id='fwSubnetListPagingToolbar']/table[@class='x-toolbar-ct']"
                                         "//td[@class='x-toolbar-left']/table//tr[@class='x-toolbar-left-row']/td[1]/table//button[@type='button']").click()
            time.sleep(2)

            log.info("Select all the checkbox")
            driver.find_element_by_xpath("//div[@id='fwSubnetgrid']/div[@class='x-panel-bwrap']/div[3]/div[@class='x-grid3']"
                                         "//div[@class='x-grid3-header-inner']//tr/td[1]/div").click()
            time.sleep(2)

            log.info("Clicking on \"Push StackMode Time\" button")
            driver.find_element_by_xpath("//table[@id='stackModeTimePush']//em/button[@type='button']").click()
            time.sleep(2)

            log.info("Verify Push stack mode time pop-up message")
            stackmd_str = driver.find_element_by_xpath("//div[@class='x-window-bwrap']//div[@class='x-window-body']//span[@class='ext-mb-text']").text
            if stackmd_exp_str in str(stackmd_str): log.info ("Verified: \"%s\"" % stackmd_str)
            else: self.failed(banner("Pop-up message Verification failed - \'%s\'\nExpected: \'%s\'") % (stackmd_str, stackmd_exp_str))
            time.sleep(1)

            log.info("Clicking on \"yes\" button")
            driver.find_element_by_xpath("//button[text()='Yes']").click()
            time.sleep(2)

            dt = datetime.datetime.utcnow().strftime('%Y-%m-%d')
            t1 = datetime.datetime.utcnow() + datetime.timedelta(minutes=2)
            log.info("Incremented Time : "+str(t1.strftime("%H:%M")))
            driver.find_element_by_xpath("//input[@id='stackDTFtime']").clear()
            driver.find_element_by_xpath("//input[@id='stackDTFtime']").send_keys(str(t1.strftime("%H:%M")))
            time.sleep(2)

            driver.find_element_by_xpath("//button[text()='Schedule']").click()
            time.sleep(2)

            log.info("Verify if stack mode time is pushed pop-up message")
            cgmesh_str = driver.find_element_by_xpath("//div[@class='x-window-bwrap']//div[@class='x-window-body']//span[@class='ext-mb-text']").text
            if stackmd_wisun_time_exp_str in str(cgmesh_str) or stktm_bfr_stkmd_exp_str in str(cgmesh_str): log.info ("Verified: \"%s\"" % cgmesh_str)
            else: self.failed(banner("Pop-up message Verification failed - \'%s\'\nExpected: \'%s\' or \'%s\'") % (cgmesh_str, stackmd_wisun_time_exp_str, stktm_bfr_stkmd_exp_str))

            log.info("Clicking on \'OK\' button")
            driver.find_element_by_xpath("//button[text()='OK']").click()
            time.sleep(2)

            log.info("Clicking on \'Close\' button")
            driver.find_element_by_xpath("//button[text()='Close']").click()
            time.sleep(2)   

            log.info('Navigate to Logs tab in the right plane')
            driver.find_element_by_xpath("//li[@id='fwTabs__logTab']//span[text()='Logs']").click()
            time.sleep(4)

            log.info("Click on Refresh button")
            driver.find_element_by_xpath("//div[@id='logPageTB']//td[@class='x-toolbar-right']//tr[@class='x-toolbar-right-row']//table[@class='x-btn x-btn-icon']//button[@type='button']").click()
            time.sleep(1)  

            log.info("Verify stacktime push when combination of wisun and non-wisun in a pan id log message")
            message_list = [element.text for element in driver.find_elements_by_xpath(
                "//div[@id='firmwareMeshLog']//div[@class='x-grid3-body']//div//td[2]//div[contains(text(),'" + dt + "')]/../..//td[6]/div")]

            log.info('Event Message: %s' % message_list)
            #if error_log_wis_nonwis not in message_list or error_log_stktm_bfr_stkmd_nonwis not in message_list: raise Exception('Did not see \'%s\' Error in Event message' % error_log_wis_nonwis)
            #else: log.info("Verified: \'%s\' Error found in Event message"% error_log_wis_nonwis)    
            if error_log_wis_nonwis in message_list or error_log_stktm_bfr_stkmd_nonwis in message_list: log.info("Verified: \'%s\' or \'%s\' Error found in Event message"% (error_log_wis_nonwis, error_log_stktm_bfr_stkmd_nonwis))
            else: raise Exception('Did not see either \'%s\' or \'%s\' Error in Event message' % (error_log_wis_nonwis, error_log_stktm_bfr_stkmd_nonwis))

        except Exception as ex:
            self.failed(ex)
            driver_utils.save_screenshot(scriptname='Tc3_VAlidate_Push_Stackmode_Time_When_Panid_One_In_Wisun_Another_In_CGMesh', classname=__class__.__name__) 

            time.sleep(2) 
            log.info("Clicking on \'OK\' button")
            driver.find_element_by_xpath("//button[text()='OK']").click()
            time.sleep(2)

            log.info("Clicking on \'Close\' button")
            driver.find_element_by_xpath("//button[text()='Close']").click()
            time.sleep(2)  

            try:
                error_logs = test_utils.read_remote_logs(remote_ssh_client=nms_ssh_client, log_file=log_file,
                                                         read_error_logs=True, line_number=last_line_number)
                assert error_logs == []
                log.info('No ERROR logs found on FND.')
            except AssertionError as ae:
                driver_utils.save_screenshot(scriptname='Tc3_VAlidate_Push_Stackmode_Time_When_Panid_One_In_Wisun_Another_In_CGMesh', classname=__class__.__name__)
                log.error('Should not see ERROR logs on FND.\nerror_logs: %s' % error_logs)        

#Testcase 4
class Tc4_Validate_Cancel_Stackmode_Before_Stack_Mode_And_Time_Push(aetest.Testcase):
    @aetest.test
    def Tc4_Validate_Cancel_Stackmode_Before_Stack_Mode_And_Time_Push(self, driver, cgmesh_pan_id, cncl_exp_str, cancel_bfr_stk_exp_str, error_log_cncl_bfr_stkmd_nonwis):
        try:
            global driver_utils
            global auto_user_ws
            import datetime
            fw_groupname = "default-ir500"

            last_line_number = \
                test_utils.read_remote_logs(remote_ssh_client=nms_ssh_client, log_file=log_file, get_last_line=True)[
                    0].rstrip()

            driver_utils.navigate_to_home()
            fw_up = ui_common_utils.FirmwareUpdate(driver)
            fw_up.nav_sub_menu('firmware_update')
            time.sleep(2)
            driver_utils.ignore_flash_error()

            driver.find_element_by_xpath(
                "//div[@id='leftHandTree']//span[contains(text(),'" + fw_groupname + "')]").click()
            time.sleep(2)
            driver_utils.ignore_flash_error()

            log.info('Navigate to Firmware Management tab in the right plane')
            driver.find_element_by_xpath("//li[@id='fwTabs__mgmtTab']//span[text()='Firmware Management']").click()
            time.sleep(1)

            log.info("Clicking on \"Clear Filter\" button")
            driver.find_element_by_xpath(
                "//div[@id='fwSubnetListPagingToolbar']/table[@class='x-toolbar-ct']//td[@class='x-toolbar-left']/table//tr[@class='x-toolbar-left-row']/td[1]/table//button[@type='button']").click()
            time.sleep(2)

            log.info("Select the PAN ID: %d" % cgmesh_pan_id)
            driver.find_element_by_xpath(
                "//div[@id='fwSubnetgrid']//div[@class='x-grid3-body']//table[@class='x-grid3-row-table']//div[@class='x-grid3-cell-inner x-grid3-col-panId' and contains(text(),\'%d\')]"
                "//parent::td//preceding-sibling::td//div[@class='x-grid3-cell-inner x-grid3-col-checker']" % cgmesh_pan_id).click()
            time.sleep(2)
            
            log.info("Clicking on \"Cancel StackMode\" button")
            driver.find_element_by_xpath("//table[@id='cancelStackPush']//em/button[@type='button']").click()
            time.sleep(2)
            
            log.info("Verify the Cancel switching pop-up message")
            cn_str = driver.find_element_by_xpath(
                "//div[@class='x-window-bwrap']//div[@class='x-window-body']//span[@class='ext-mb-text']").text
            if cncl_exp_str in str(cn_str): log.info("Verified: \"%s\"" % cn_str)
            else: self.failed(banner("Pop-up message Verification failed - \'%s\'\nExpected: \'%s\'") % (cn_str, cncl_exp_str))
            time.sleep(1)

            dte = datetime.datetime.utcnow().strftime('%Y-%m-%d')
            
            log.info("Clicking on \"yes\" button")
            driver.find_element_by_xpath("//button[text()='Yes']").click()
            time.sleep(2)
            
            log.info("Verify Cancel reload before push stack mode/Time pop-up message")
            wisun_str = driver.find_element_by_xpath(
                "//div[@class='x-window-bwrap']//div[@class='x-window-body']//span[@class='ext-mb-text']").text
            if cancel_bfr_stk_exp_str in str(wisun_str): log.info("Verified: \"%s\"" % wisun_str)
            else: self.failed(banner("Pop-up message Verification failed - \'%s\'\nExpected: \'%s\'") % (wisun_str, cancel_bfr_stk_exp_str))

            log.info("Clicking on \'OK\' button")
            driver.find_element_by_xpath("//button[text()='OK']").click()
            time.sleep(2)    

            log.info('Navigate to Logs tab in the right plane')
            driver.find_element_by_xpath("//li[@id='fwTabs__logTab']//span[text()='Logs']").click()
            time.sleep(4)

            log.info("Click on Refresh button")
            driver.find_element_by_xpath("//div[@id='logPageTB']//td[@class='x-toolbar-right']//tr[@class='x-toolbar-right-row']//table[@class='x-btn x-btn-icon']//button[@type='button']").click()
            time.sleep(1)  

            log.info("Verify the cancel stack mode before stack push log message")
            message_list = [element.text for element in driver.find_elements_by_xpath(
                "//div[@id='firmwareMeshLog']//div[@class='x-grid3-body']//div//td[2]//div[contains(text(),'" + dte + "')]/../..//td[6]/div")]

            log.info('Event Message: %s' % message_list)
            if error_log_cncl_bfr_stkmd_nonwis not in message_list: raise Exception('Did not see \'%s\' Error in Event message' % error_log_cncl_bfr_stkmd_nonwis)
            else: log.info("Verified: \'%s\' Error found in Event message"% error_log_cncl_bfr_stkmd_nonwis)

        except Exception as ex:
            self.failed(ex)
            driver_utils.save_screenshot(scriptname='Tc4_Validate_Cancel_Stackmode_Before_Stack_Mode_And_Time_Push', classname=__class__.__name__)

            log.info("Clicking on \'OK\' button") 
            driver.find_element_by_xpath("//button[text()='OK']").click()
            time.sleep(2)   

            try:
                error_logs = test_utils.read_remote_logs(remote_ssh_client=nms_ssh_client, log_file=log_file,
                                                         read_error_logs=True, line_number=last_line_number)
                assert error_logs == []
                log.info('No ERROR logs found on FND.')
            except AssertionError as ae:
                driver_utils.save_screenshot(scriptname='Tc4_Validate_Cancel_Stackmode_Before_Stack_Mode_And_Time_Push', classname=__class__.__name__)
                log.error('Should not see ERROR logs on FND.\nerror_logs: %s' % error_logs)

#Testcase 5
class Tc5_Validate_Stackmode_Time_Before_Stack_Mode_Push(aetest.Testcase):
    @aetest.test
    def Tc5_Validate_Stackmode_Time_Before_Stack_Mode_Push(self, driver, cgmesh_pan_id, stackmd_exp_str, stktm_bfr_stkmd_exp_str, error_log_stktm_bfr_stkmd_nonwis):
        try:
            global driver_utils
            global auto_user_ws
            import datetime
            fw_groupname = "default-ir500"

            last_line_number = \
                test_utils.read_remote_logs(remote_ssh_client=nms_ssh_client, log_file=log_file, get_last_line=True)[
                    0].rstrip()

            driver_utils.navigate_to_home()
            fw_up = ui_common_utils.FirmwareUpdate(driver)
            fw_up.nav_sub_menu('firmware_update')
            time.sleep(2)
            driver_utils.ignore_flash_error()

            driver.find_element_by_xpath(
                "//div[@id='leftHandTree']//span[contains(text(),'" + fw_groupname + "')]").click()
            time.sleep(2)
            driver_utils.ignore_flash_error()

            log.info('Navigate to Firmware Management tab in the right plane')
            driver.find_element_by_xpath("//li[@id='fwTabs__mgmtTab']//span[text()='Firmware Management']").click()
            time.sleep(1)

            log.info("Clicking on \"Clear Filter\" button")
            driver.find_element_by_xpath(
                "//div[@id='fwSubnetListPagingToolbar']/table[@class='x-toolbar-ct']//td[@class='x-toolbar-left']/table//tr[@class='x-toolbar-left-row']/td[1]/table//button[@type='button']").click()
            time.sleep(2)

            log.info("Select the PAN ID: %d" % cgmesh_pan_id)
            driver.find_element_by_xpath(
                "//div[@id='fwSubnetgrid']//div[@class='x-grid3-body']//table[@class='x-grid3-row-table']//div[@class='x-grid3-cell-inner x-grid3-col-panId' and contains(text(),\'%d\')]"
                "//parent::td//preceding-sibling::td//div[@class='x-grid3-cell-inner x-grid3-col-checker']" % cgmesh_pan_id).click()
            time.sleep(2)

            log.info("Clicking on \"Push StackMode Time\" button")
            driver.find_element_by_xpath("//table[@id='stackModeTimePush']//em/button[@type='button']").click()
            time.sleep(2)

            log.info("Verify Push stack mode time pop-up message")
            stackmd_str = driver.find_element_by_xpath(
                "//div[@class='x-window-bwrap']//div[@class='x-window-body']//span[@class='ext-mb-text']").text
            if stackmd_exp_str in str(stackmd_str): log.info("Verified: \"%s\"" % stackmd_str)
            else: self.failed(banner("Pop-up message Verification failed - \'%s\'\nExpected: \'%s\'") % (stackmd_str, stackmd_exp_str))
            time.sleep(1)

            log.info("Clicking on \"yes\" button")
            driver.find_element_by_xpath("//button[text()='Yes']").click()
            time.sleep(2)

            dt = datetime.datetime.utcnow().strftime('%Y-%m-%d')
            t1 = datetime.datetime.utcnow() + datetime.timedelta(minutes=2)
            log.info("Incremented Time : " + str(t1.strftime("%H:%M")))
            driver.find_element_by_xpath("//input[@id='stackDTFtime']").clear()
            driver.find_element_by_xpath("//input[@id='stackDTFtime']").send_keys(str(t1.strftime("%H:%M")))
            time.sleep(2)

            log.info("Click on Schedule Button")
            driver.find_element_by_xpath("//button[text()='Schedule']").click()
            time.sleep(2)

            log.info("Verify if stack mode time is pushed pop-up message")
            cgmesh_str = driver.find_element_by_xpath(
                "//div[@class='x-window-bwrap']//div[@class='x-window-body']//span[@class='ext-mb-text']").text
            if stktm_bfr_stkmd_exp_str in str(cgmesh_str): log.info("Verified: \"%s\"" % cgmesh_str)
            else: self.failed(banner("Pop-up message Verification failed - \'%s\'\nExpected: \'%s\'") % (cgmesh_str, stktm_bfr_stkmd_exp_str))

            log.info("Clicking on \"OK\" button")
            driver.find_element_by_xpath("//button[text()='OK']").click()
            time.sleep(2)

            log.info("Clicking on \"Close\" button")
            driver.find_element_by_xpath("//button[text()='Close']").click()
            time.sleep(2)  

            log.info('Navigate to Logs tab in the right plane')
            driver.find_element_by_xpath("//li[@id='fwTabs__logTab']//span[text()='Logs']").click()
            time.sleep(4)

            log.info("Click on Refresh button")
            driver.find_element_by_xpath("//div[@id='logPageTB']//td[@class='x-toolbar-right']//tr[@class='x-toolbar-right-row']//table[@class='x-btn x-btn-icon']//button[@type='button']").click()
            time.sleep(1)  

            log.info("Verify stack mode time before stack push log message") 
            message_list = [element.text for element in driver.find_elements_by_xpath(
                "//div[@id='firmwareMeshLog']//div[@class='x-grid3-body']//div//td[2]//div[contains(text(),'" + dt + "')]/../..//td[6]/div")]

            log.info('Event Message: %s' % message_list)
            if error_log_stktm_bfr_stkmd_nonwis not in message_list: raise Exception('Did not see \'%s\' Error in Event message' % error_log_stktm_bfr_stkmd_nonwis)
            else: log.info("Verified: \'%s\' Error found in Event message"% error_log_stktm_bfr_stkmd_nonwis)

        except Exception as ex:
            self.failed(ex)
            driver_utils.save_screenshot(scriptname='Tc5_Validate_Stackmode_Time_Before_Stack_Mode_Push', classname=__class__.__name__) 

            log.info("Clicking on \"OK\" button")
            driver.find_element_by_xpath("//button[text()='OK']").click()
            time.sleep(2)

            log.info("Clicking on \"Close\" button")
            driver.find_element_by_xpath("//button[text()='Close']").click()
            time.sleep(2)     

            try:
                error_logs = test_utils.read_remote_logs(remote_ssh_client=nms_ssh_client, log_file=log_file,
                                                         read_error_logs=True, line_number=last_line_number)
                assert error_logs == []
                log.info('No ERROR logs found on FND.')
            except AssertionError as ae:
                driver_utils.save_screenshot(scriptname='Tc5_Validate_Stackmode_Time_Before_Stack_Mode_Push', classname=__class__.__name__)
                log.error('Should not see ERROR logs on FND.\nerror_logs: %s' % error_logs)

                log.error('Should not see ERROR logs on FND.\nerror_logs: %s' % error_logs)
'''
# Testcase 6
class Tc6_Validate_Overall_Stackmode_Mode_Push_And_Active_Running_Job(aetest.Testcase):
    @aetest.test
    def Tc6_Validate_Overall_Stackmode_Mode_Push_And_Active_Running_Job(self, driver, cgmesh_pan_id, stackmd_exp_str, stack_node_cnt,
                                                 stackmd_cfm_exp_str, stackmd_typ_exp, pshstack_msg_exp, log_msg_stkmd, push_stack_md_active_job):
        try:
            global driver_utils
            global auto_user_ws
            import datetime
            fw_groupname = "default-ir500"

            last_line_number = \
                test_utils.read_remote_logs(remote_ssh_client=nms_ssh_client, log_file=log_file, get_last_line=True)[
                    0].rstrip()

            driver_utils.navigate_to_home()
            fw_up = ui_common_utils.FirmwareUpdate(driver)
            fw_up.nav_sub_menu('firmware_update')
            time.sleep(2)
            driver_utils.ignore_flash_error()

            driver.find_element_by_xpath(
                "//div[@id='leftHandTree']//span[contains(text(),'" + fw_groupname + "')]").click()
            time.sleep(2)
            driver_utils.ignore_flash_error()

            log.info('Navigate to Firmware Management tab in the right plane')
            driver.find_element_by_xpath("//li[@id='fwTabs__mgmtTab']//span[text()='Firmware Management']").click()
            time.sleep(1)

            log.info("Clicking on \"Clear Filter\" button")
            driver.find_element_by_xpath(
                "//div[@id='fwSubnetListPagingToolbar']/table[@class='x-toolbar-ct']//td[@class='x-toolbar-left']/table"
                "//tr[@class='x-toolbar-left-row']/td[1]/table//button[@type='button']").click()
            time.sleep(2)

            log.info("Select the PAN ID: %d" % cgmesh_pan_id)
            driver.find_element_by_xpath(
                "//div[@id='fwSubnetgrid']//div[@class='x-grid3-body']//table[@class='x-grid3-row-table']"
                "//div[@class='x-grid3-cell-inner x-grid3-col-panId' and contains(text(),\'%d\')]"
                "//parent::td//preceding-sibling::td//div[@class='x-grid3-cell-inner x-grid3-col-checker']" % cgmesh_pan_id).click()
            time.sleep(2)

            dte = datetime.datetime.utcnow().strftime('%Y-%m-%d')

            log.info("Clicking on \"Push StackMode\" button")
            driver.find_element_by_xpath("//table[@id='stackModePush']//em/button[@type='button']").click()
            time.sleep(2)

            log.info("Verify the Push stack mode pop-up message")
            stackmd_str = driver.find_element_by_xpath(
                "//div[@class='x-window-bwrap']//div[@class='x-window-body']//span[@class='ext-mb-text']").text
            if stackmd_exp_str in str(stackmd_str):
                log.info("Verified: \"%s\"" % stackmd_str)
            else:
                self.failed(banner("Pop-up message Verification failed - \'%s\'\nExpected: \'%s\'") % (
                stackmd_str, stackmd_exp_str))
            time.sleep(1)

            log.info("Clicking on \"yes\" button")
            driver.find_element_by_xpath("//button[text()='Yes']").click()
            time.sleep(2)

            log.info("Verify conformation pop-up message")
            stackmd_cfm_str = driver.find_element_by_xpath(
                "//div[@class='x-window-bwrap']//div[@class='x-window-body']//span[@class='ext-mb-text']").text
            if stackmd_cfm_exp_str in str(stackmd_cfm_str):
                log.info("Verified: \"%s\"" % stackmd_cfm_str)
            else:
                self.failed(banner("Pop-up message Verification failed - \'%s\'\nExpected: \'%s\'") % (
                stackmd_cfm_str, stackmd_cfm_exp_str))
            time.sleep(1)

            log.info("Clicking on \"OK\" button")
            driver.find_element_by_xpath("//button[text()='OK']").click()
            time.sleep(5)

            log.info("Clicking on \"Push StackMode\" button again")
            driver.find_element_by_xpath("//table[@id='stackModePush']//em/button[@type='button']").click()
            time.sleep(2)

            log.info("Verify the Push stack mode pop-up message")
            stackmd_str = driver.find_element_by_xpath(
                "//div[@class='x-window-bwrap']//div[@class='x-window-body']//span[@class='ext-mb-text']").text
            if stackmd_exp_str in str(stackmd_str):
                log.info("Verified: \"%s\"" % stackmd_str)
            else:
                self.failed(banner("Pop-up message Verification failed - \'%s\'\nExpected: \'%s\'") % (
                stackmd_str, stackmd_exp_str))
            time.sleep(1)

            log.info("Clicking on \"yes\" button")
            driver.find_element_by_xpath("//button[text()='Yes']").click()
            time.sleep(2)

            log.info("Verify Push stack mode existing Active job pop-up message")
            stackmd_cfm_str = driver.find_element_by_xpath(
                "//div[@class='x-window-bwrap']//div[@class='x-window-body']//span[@class='ext-mb-text']").text
            if push_stack_md_active_job in str(stackmd_cfm_str):
                log.info("Verified: \"%s\"" % stackmd_cfm_str)
            else:
                self.failed(banner("Pop-up message Verification failed - \'%s\'\nExpected: \'%s\'") % (
                stackmd_cfm_str, push_stack_md_active_job))
            time.sleep(1)

            log.info("Clicking on \"OK\" button")
            driver.find_element_by_xpath("//button[text()='OK']").click()

            log.info("Wait for 15 Seconds")
            time.sleep(15)

            log.info("Click on Refresh button")
            driver.find_element_by_xpath(
                "//div[@id='fwSubnetListPagingToolbar']//table[@class='x-toolbar-ct']//td[@class='x-toolbar-right']"
                "//table[@class='x-toolbar-right-ct']//tr[@class='x-toolbar-right-row']//td//em/button[@type='button']").click()

            log.info("Wait for 5 Seconds")
            time.sleep(5)         

            temp = Push_And_Verify_The_StackMode(driver, cgmesh_pan_id, stackmd_typ_exp, pshstack_msg_exp, stack_node_cnt)
            if temp: log.info("Overall stack mode push verified successfully")
            else: self.failed(banner("Overall stack mode push Failed"))

            log.info('Navigate to Logs tab in the right plane')
            driver.find_element_by_xpath("//li[@id='fwTabs__logTab']//span[text()='Logs']").click()
            time.sleep(4)

            log.info("Click on Refresh button")
            driver.find_element_by_xpath("//div[@id='logPageTB']//td[@class='x-toolbar-right']//tr[@class='x-toolbar-right-row']//table[@class='x-btn x-btn-icon']//button[@type='button']").click()
            time.sleep(1)  

            log.info("Verify the stackmode push log message")
            message_list = [element.text for element in driver.find_elements_by_xpath(
                "//div[@id='firmwareMeshLog']//div[@class='x-grid3-body']//div//td[2]//div[contains(text(),'" + dte + "')]/../..//td[6]/div")]

            log.info('Event Message: %s' % message_list)
            if log_msg_stkmd not in message_list: raise Exception('Did not see the \"%s\" in Event message'% log_msg_stkmd)
            else: log.info("\'%s\' found in Event message"% log_msg_stkmd)

            log.info("Wait for 5 Seconds")
            time.sleep(5)         

            log.info(banner('Getting the latest AuditTrails'))
            audit_trail = ui_common_utils.AuditTrail(driver)
            audittrails = audit_trail.get_latest_audittrails()
            operation = audittrails['operations']

            log.info('operation: %s' % operation)
            if 'Stack Mode Push' not in operation: raise Exception('Did not see the "Stack Mode Push" Audit Trail')
            else: log.info("Stack mode push found in Audit trials")

        except Exception as ex:
            self.failed(ex)
            driver_utils.save_screenshot(scriptname='Tc6_Validate_Overall_Stackmode_Mode_Push_And_Active_Running_Job',
                                         classname=__class__.__name__)

            try:
                error_logs = test_utils.read_remote_logs(remote_ssh_client=nms_ssh_client, log_file=log_file,
                                                         read_error_logs=True, line_number=last_line_number)
                assert error_logs == []
                log.info('No ERROR logs found on FND.')
            except AssertionError as ae:
                driver_utils.save_screenshot(scriptname='Tc6_Validate_Overall_Stackmode_Mode_Push_And_Active_Running_Job',
                                             classname=__class__.__name__)
                log.error('Should not see ERROR logs on FND.\nerror_logs: %s' % error_logs)

#Testcase 7
class Tc7_Validate_Overall_Stackmode_Cancel(aetest.Testcase):
    @aetest.test
    def Tc7_Validate_Overall_Stackmode_Cancel(self, driver, cgmesh_pan_id, cncl_exp_str, cancel_exp_str, stack_node_cnt, cncl_stkmd_typ_exp, cancel_msg_exp, log_msg_cncl):
        try:
            global driver_utils
            global auto_user_ws
            import datetime
            fw_groupname = "default-ir500"

            last_line_number = \
                test_utils.read_remote_logs(remote_ssh_client=nms_ssh_client, log_file=log_file, get_last_line=True)[
                    0].rstrip()

            driver_utils.navigate_to_home()
            fw_up = ui_common_utils.FirmwareUpdate(driver)
            fw_up.nav_sub_menu('firmware_update')
            time.sleep(2)
            driver_utils.ignore_flash_error()

            driver.find_element_by_xpath(
                "//div[@id='leftHandTree']//span[contains(text(),'" + fw_groupname + "')]").click()
            time.sleep(2)
            driver_utils.ignore_flash_error()

            log.info('Navigate to Firmware Management tab in the right plane')
            driver.find_element_by_xpath("//li[@id='fwTabs__mgmtTab']//span[text()='Firmware Management']").click()
            time.sleep(1)

            log.info("Clicking on \"Clear Filter\" button")
            driver.find_element_by_xpath("//div[@id='fwSubnetListPagingToolbar']/table[@class='x-toolbar-ct']//td[@class='x-toolbar-left']/table//tr[@class='x-toolbar-left-row']/td[1]/table//button[@type='button']").click()
            time.sleep(2)

            log.info("Select the PAN ID: %d" % cgmesh_pan_id)
            driver.find_element_by_xpath("//div[@id='fwSubnetgrid']//div[@class='x-grid3-body']//table[@class='x-grid3-row-table']//div[@class='x-grid3-cell-inner x-grid3-col-panId' and contains(text(),\'%d\')]//parent::td//preceding-sibling::td//div[@class='x-grid3-cell-inner x-grid3-col-checker']" % cgmesh_pan_id).click()
            time.sleep(2)

            log.info("Clicking on \"Cancel StackMode\" button")
            driver.find_element_by_xpath("//table[@id='cancelStackPush']//em/button[@type='button']").click()
            time.sleep(2)

            log.info("Verify the Cancel switching pop-up message")
            cn_str = driver.find_element_by_xpath("//div[@class='x-window-bwrap']//div[@class='x-window-body']//span[@class='ext-mb-text']").text
            if cncl_exp_str in str(cn_str): log.info ("Verified: \"%s\"" % cn_str)
            else: self.failed(banner("Pop-up message Verification failed - \'%s\'\nExpected: \'%s\'") % (cn_str, cncl_exp_str))
            time.sleep(1)

            log.info("Clicking on \"yes\" button")
            driver.find_element_by_xpath("//button[text()='Yes']").click()
            time.sleep(2)

            log.info("Verify Cancel stack mode pop-up message")
            cancel_str = driver.find_element_by_xpath("//div[@class='x-window-bwrap']//div[@class='x-window-body']//span[@class='ext-mb-text']").text
            if cancel_exp_str in str(cancel_str): log.info ("Verified: \"%s\"" % cancel_str)
            else: self.failed(banner("Pop-up message Verification failed - \'%s\'\nExpected: \'%s\'") % (cancel_str, cancel_exp_str))

            dte = datetime.datetime.utcnow().strftime('%Y-%m-%d')

            log.info("Clicking on \"OK\" button")
            driver.find_element_by_xpath("//button[text()='OK']").click()
            time.sleep(1)

            log.info("Click on Refresh button")
            driver.find_element_by_xpath("//div[@id='fwSubnetListPagingToolbar']//table[@class='x-toolbar-ct']//td[@class='x-toolbar-right']"
                                         "//table[@class='x-toolbar-right-ct']//tr[@class='x-toolbar-right-row']//td//em/button[@type='button']").click()
            time.sleep(1) 

            temp = Push_And_Verify_The_StackMode(driver, cgmesh_pan_id, cncl_stkmd_typ_exp, cancel_msg_exp, stack_node_cnt)
            if temp: log.info("Overall stack mode cancel verified successfully")
            else: self.failed(banner("Overall stack mode cancel Failed"))

            log.info("Wait for 5 Seconds")  
            time.sleep(5)

            log.info('Navigate to Logs tab in the right plane')
            driver.find_element_by_xpath("//li[@id='fwTabs__logTab']//span[text()='Logs']").click()
            time.sleep(4)

            log.info("Click on Refresh button")
            driver.find_element_by_xpath("//div[@id='logPageTB']//td[@class='x-toolbar-right']//tr[@class='x-toolbar-right-row']//table[@class='x-btn x-btn-icon']//button[@type='button']").click()
            time.sleep(1)  

            log.info("Verify the Cancel stack log message")
            message_list = [element.text for element in driver.find_elements_by_xpath(
                "//div[@id='firmwareMeshLog']//div[@class='x-grid3-body']//div//td[2]//div[contains(text(),'" + dte + "')]/../..//td[6]/div")]

            log.info('Event Message: %s' % message_list)
            if log_msg_cncl not in message_list: raise Exception('Did not see \'%s\' Error in Event message' % log_msg_cncl)
            else: log.info("Verified: \'%s\' Error found in Event message"% log_msg_cncl)

            log.info(banner('Getting the latest AuditTrails'))
            audit_trail = ui_common_utils.AuditTrail(driver)
            audittrails = audit_trail.get_latest_audittrails()
            operation = audittrails['operations']

            log.info('operation: %s' % operation)
            if 'Cancel Stack' not in operation: raise Exception('Did not see the "Cancel stack" Audit Trail')
            else: log.info("Cancel stack found in Audit trials")

        except Exception as ex:
            self.failed(ex)
            driver_utils.save_screenshot(scriptname='Tc7_Validate_Overall_Stackmode_Cancel', classname=__class__.__name__)

            try:
                error_logs = test_utils.read_remote_logs(remote_ssh_client=nms_ssh_client, log_file=log_file,
                                                         read_error_logs=True, line_number=last_line_number)
                assert error_logs == []
                log.info('No ERROR logs found on FND.')
            except AssertionError as ae:
                driver_utils.save_screenshot(scriptname='Tc7_Validate_Overall_Stackmode_Cancel', classname=__class__.__name__)
                log.error('Should not see ERROR logs on FND.\nerror_logs: %s' % error_logs)

# Testcase 8
class Tc8_Validate_Overall_Stacktime_Push_And_Active_Running_Job(aetest.Testcase):
    @aetest.test
    def Tc8_Validate_Overall_Stacktime_Push_And_Active_Running_Job(self, driver, nms_server, ir500_eids, cgmesh_pan_id, stackmd_exp_str, stack_node_cnt, push_stack_tm_active_job,
                                                 stackmd_cfm_exp_str, stackmd_typ_exp, stktm_typ_exp, pshstack_msg_exp, pshstack_tme_msg_exp, log_msg_skttm):
        try:
            global driver_utils
            global auto_user_ws
            import datetime
            fw_groupname = "default-ir500"

            last_line_number = \
                test_utils.read_remote_logs(remote_ssh_client=nms_ssh_client, log_file=log_file, get_last_line=True)[
                    0].rstrip()

            driver_utils.navigate_to_home()
            fw_up = ui_common_utils.FirmwareUpdate(driver)
            fw_up.nav_sub_menu('firmware_update')
            time.sleep(2)
            driver_utils.ignore_flash_error()

            driver.find_element_by_xpath(
                "//div[@id='leftHandTree']//span[contains(text(),'" + fw_groupname + "')]").click()
            time.sleep(2)
            driver_utils.ignore_flash_error()

            log.info('Navigate to Firmware Management tab in the right plane')
            driver.find_element_by_xpath("//li[@id='fwTabs__mgmtTab']//span[text()='Firmware Management']").click()
            time.sleep(1)

            log.info("Clicking on \"Clear Filter\" button")
            driver.find_element_by_xpath(
                "//div[@id='fwSubnetListPagingToolbar']/table[@class='x-toolbar-ct']//td[@class='x-toolbar-left']/table"
                "//tr[@class='x-toolbar-left-row']/td[1]/table//button[@type='button']").click()
            time.sleep(2)

            log.info("Select the PAN ID: %d" % cgmesh_pan_id)
            driver.find_element_by_xpath(
                "//div[@id='fwSubnetgrid']//div[@class='x-grid3-body']//table[@class='x-grid3-row-table']"
                "//div[@class='x-grid3-cell-inner x-grid3-col-panId' and contains(text(),\'%d\')]"
                "//parent::td//preceding-sibling::td//div[@class='x-grid3-cell-inner x-grid3-col-checker']" % cgmesh_pan_id).click()
            time.sleep(2)

            log.info("Clicking on \"Push StackMode\" button")
            driver.find_element_by_xpath("//table[@id='stackModePush']//em/button[@type='button']").click()
            time.sleep(2)

            log.info("Verify the Push stack mode pop-up message")
            stackmd_str = driver.find_element_by_xpath(
                "//div[@class='x-window-bwrap']//div[@class='x-window-body']//span[@class='ext-mb-text']").text
            if stackmd_exp_str in str(stackmd_str):
                log.info("Verified: \"%s\"" % stackmd_str)
            else:
                self.failed(banner("Pop-up message Verification failed - \'%s\'\nExpected: \'%s\'") % (
                    stackmd_str, stackmd_exp_str))
            time.sleep(1)

            log.info("Clicking on \"yes\" button")
            driver.find_element_by_xpath("//button[text()='Yes']").click()
            time.sleep(2)

            log.info("Verify conformation pop-up message")
            stackmd_cfm_str = driver.find_element_by_xpath(
                "//div[@class='x-window-bwrap']//div[@class='x-window-body']//span[@class='ext-mb-text']").text
            if stackmd_cfm_exp_str in str(stackmd_cfm_str):
                log.info("Verified: \"%s\"" % stackmd_cfm_str)
            else:
                self.failed(banner("Pop-up message Verification failed - \'%s\'\nExpected: \'%s\'") % (
                    stackmd_cfm_str, stackmd_cfm_exp_str))
            time.sleep(1)

            log.info("Clicking on \"OK\" button")
            driver.find_element_by_xpath("//button[text()='OK']").click()

            log.info("Wait for 15 Seconds")
            time.sleep(15)

            log.info("Click on Refresh button")
            driver.find_element_by_xpath(
                "//div[@id='fwSubnetListPagingToolbar']//table[@class='x-toolbar-ct']//td[@class='x-toolbar-right']"
                "//table[@class='x-toolbar-right-ct']//tr[@class='x-toolbar-right-row']//td//em/button[@type='button']").click()
            time.sleep(5)
            log.info("Wait for 5 Seconds")

            temp = Push_And_Verify_The_StackMode(driver, cgmesh_pan_id, stackmd_typ_exp, pshstack_msg_exp, stack_node_cnt)
            if temp:
                log.info("Overall stack mode push verified successfully")
            else:
                log.info("Overall stack mode push Failed")
            time.sleep(2)

            log.info("Clicking on \"Push StackMode Time\" button")
            driver.find_element_by_xpath("//table[@id='stackModeTimePush']//em/button[@type='button']").click()
            time.sleep(2)

            log.info("Verify Push stack mode time pop-up message")
            stackmd_str = driver.find_element_by_xpath(
                "//div[@class='x-window-bwrap']//div[@class='x-window-body']//span[@class='ext-mb-text']").text
            if stackmd_exp_str in str(stackmd_str):
                log.info("Verified: \"%s\"" % stackmd_str)
            else:
                self.failed(banner("Pop-up message Verification failed - \'%s\'\nExpected: \'%s\'") % (
                    stackmd_str, stackmd_exp_str))
            time.sleep(1)

            log.info("Clicking on \"yes\" button")
            driver.find_element_by_xpath("//button[text()='Yes']").click()
            time.sleep(2)

            log.info("Current Date: " + datetime.datetime.utcnow().strftime('%Y-%m-%d'))
            log.info("Current Time: " + datetime.datetime.utcnow().strftime("%H:%M"))
            dt = datetime.datetime.utcnow().strftime('%Y-%m-%d')
            t1 = datetime.datetime.utcnow() + datetime.timedelta(minutes=300)
            inc_tm = str(t1.strftime("%H:%M"))
            #sch_tm = inc_tm + ":00.0"
            sch_tm = inc_tm + ":00"
            config_dt_tm = dt + " " + sch_tm
            log.info("Incremented Time: " + inc_tm)
            driver.find_element_by_xpath("//input[@id='stackDTFtime']").clear()
            driver.find_element_by_xpath("//input[@id='stackDTFtime']").send_keys(inc_tm)
            #driver.find_element_by_xpath("//input[@id='stackDTFdate']/../img").click()
            time.sleep(1)

            dt1, t11 = Get_Nms_Date_And_Time(self, nms_server)
            log.info("Current FND Date: %s" % dt1)
            log.info("Current FND Time: %s" % t11)   

            #log.info("Clicking on \"Today\" button")
            #driver.find_element_by_xpath("//button[text()='Today']").click()
            #time.sleep(2)

            log.info("Clicking on \"Schedule\" button")
            driver.find_element_by_xpath("//button[text()='Schedule']").click()
            time.sleep(2)

            log.info("Clicking on \"OK\" button")
            driver.find_element_by_xpath("//button[text()='OK']").click()
            time.sleep(2)

            log.info("Clicking on \"Push StackMode Time\" button again")
            driver.find_element_by_xpath("//table[@id='stackModeTimePush']//em/button[@type='button']").click()
            time.sleep(2)

            log.info("Verify Push stack mode time pop-up message")
            stackmd_str = driver.find_element_by_xpath(
                "//div[@class='x-window-bwrap']//div[@class='x-window-body']//span[@class='ext-mb-text']").text
            if stackmd_exp_str in str(stackmd_str): log.info("Verified: \"%s\"" % stackmd_str)
            else: self.failed(banner("Pop-up message Verification failed - \'%s\'\nExpected: \'%s\'") % (stackmd_str, stackmd_exp_str))
            time.sleep(1)

            log.info("Clicking on \"yes\" button")
            driver.find_element_by_xpath("//button[text()='Yes']").click()
            time.sleep(2)

            log.info("Schedule stack time again")
            driver.find_element_by_xpath("//input[@id='stackDTFtime']").clear()
            driver.find_element_by_xpath("//input[@id='stackDTFtime']").send_keys(inc_tm)
            #driver.find_element_by_xpath("//input[@id='stackDTFdate']/../img").click()
            time.sleep(1)

            log.info("Clicking on \"Schedule\" button")
            driver.find_element_by_xpath("//button[text()='Schedule']").click()
            time.sleep(2)

            log.info("Verify Push stack time existing Active job pop-up message")
            stackmd_str = driver.find_element_by_xpath(
                "//div[@class='x-window-bwrap']//div[@class='x-window-body']//span[@class='ext-mb-text']").text
            if push_stack_tm_active_job in str(stackmd_str): log.info("Verified: \"%s\"" % stackmd_str)
            else: self.failed(banner("Pop-up message Verification failed - \'%s\'\nExpected: \'%s\'") % (stackmd_str, push_stack_tm_active_job))
            time.sleep(1)

            log.info("Clicking on \"OK\" button")
            driver.find_element_by_xpath("//button[text()='OK']").click()
            time.sleep(1)

            log.info("Clicking on \"Close\" button")
            driver.find_element_by_xpath("//button[text()='Close']").click()   

            log.info("Wait for 15 Seconds")
            time.sleep(15)

            log.info("Click on Refresh button")
            driver.find_element_by_xpath(
                "//div[@id='fwSubnetListPagingToolbar']//table[@class='x-toolbar-ct']//td[@class='x-toolbar-right']"
                "//table[@class='x-toolbar-right-ct']//tr[@class='x-toolbar-right-row']//td//em/button[@type='button']").click()
            time.sleep(2)
            log.info("Wait for 5 Seconds")

            log.info("Click on Refresh button")
            driver.find_element_by_xpath(
                "//div[@id='fwSubnetListPagingToolbar']//table[@class='x-toolbar-ct']//td[@class='x-toolbar-right']"
                "//table[@class='x-toolbar-right-ct']//tr[@class='x-toolbar-right-row']//td//em/button[@type='button']").click()

            log.info("Wait for 2 Seconds")
            time.sleep(2) 

            #temp = Push_And_Verify_The_StackMode(driver, cgmesh_pan_id, stktm_typ_exp, pshstack_tme_msg_exp, stack_node_cnt, config_dt_tm)
            temp = Push_And_Verify_The_StackMode(driver, cgmesh_pan_id, stktm_typ_exp, pshstack_tme_msg_exp, stack_node_cnt)
            if temp: log.info("Overall Scheduled Stack mode time is Successfull")
            else: self.failed(banner("Overall Scheduled Stack mode time Failed"))

            log.info('Navigate to Logs tab in the right plane')
            driver.find_element_by_xpath("//li[@id='fwTabs__logTab']//span[text()='Logs']").click()
            time.sleep(4)

            log.info("Click on Refresh button")
            driver.find_element_by_xpath("//div[@id='logPageTB']//td[@class='x-toolbar-right']//tr[@class='x-toolbar-right-row']//table[@class='x-btn x-btn-icon']//button[@type='button']").click()
            time.sleep(1)  

            log.info("Verify the Push stack time log message")
            message_list = [element.text for element in driver.find_elements_by_xpath(
                "//div[@id='firmwareMeshLog']//div[@class='x-grid3-body']//div//td[2]//div[contains(text(),'" + dt1 + "')]/../..//td[6]/div")]

            log.info('Event Message: %s' % message_list)
            if log_msg_skttm not in message_list: raise Exception('Did not see \'%s\' Error in Event message' % log_msg_skttm)
            else: log.info("Verified: \'%s\' Error found in Event message"% log_msg_skttm)

            log.info("Wait for 5 Seconds")
            time.sleep(5)

            log.info(banner('Getting the latest AuditTrails'))
            audit_trail = ui_common_utils.AuditTrail(driver)
            audittrails = audit_trail.get_latest_audittrails()
            operation = audittrails['operations']

            log.info('operation: %s' % operation)
            if 'Scheduled Stack Switch Time' not in operation: raise Exception('Did not see the "Scheduled Stack Switch Time" Audit Trail')
            else: log.info("Scheduled Stack Switch Time found in Audit trials")

        except Exception as ex:
            self.failed(ex)
            driver_utils.save_screenshot(scriptname='Tc8_Validate_Overall_Stacktime_Push_And_Active_Running_Job',
                                         classname=__class__.__name__)

            try:
                error_logs = test_utils.read_remote_logs(remote_ssh_client=nms_ssh_client, log_file=log_file,
                                                         read_error_logs=True, line_number=last_line_number)
                assert error_logs == []
                log.info('No ERROR logs found on FND.')
            except AssertionError as ae:
                driver_utils.save_screenshot(scriptname='Tc8_Validate_Overall_Stacktime_Push_And_Active_Running_Job',
                                             classname=__class__.__name__)
                log.error('Should not see ERROR logs on FND.\nerror_logs: %s' % error_logs)

# Testcase 9
class Tc9_Validate_Overall_StackMode_And_Stacktime_Cancel_And_Active_Running_Job(aetest.Testcase):
    @aetest.test
    def Tc9_Validate_Overall_StackMode_And_Stacktime_Cancel_And_Active_Running_Job(self, driver, cgmesh_pan_id, cncl_exp_str,
                                                   cancel_exp_str, stack_node_cnt, cncl_stkmd_typ_exp,
                                                   cancel_msg_exp, log_msg_cncl, cancel_stack_active_job):
        try:
            global driver_utils
            global auto_user_ws
            import datetime
            fw_groupname = "default-ir500"

            last_line_number = \
                test_utils.read_remote_logs(remote_ssh_client=nms_ssh_client, log_file=log_file,
                                            get_last_line=True)[
                    0].rstrip()

            driver_utils.navigate_to_home()
            fw_up = ui_common_utils.FirmwareUpdate(driver)
            fw_up.nav_sub_menu('firmware_update')
            time.sleep(2)
            driver_utils.ignore_flash_error()

            driver.find_element_by_xpath(
                "//div[@id='leftHandTree']//span[contains(text(),'" + fw_groupname + "')]").click()
            time.sleep(2)
            driver_utils.ignore_flash_error()

            log.info('Navigate to Firmware Management tab in the right plane')
            driver.find_element_by_xpath(
                "//li[@id='fwTabs__mgmtTab']//span[text()='Firmware Management']").click()
            time.sleep(1)

            log.info("Clicking on \"Clear Filter\" button")
            driver.find_element_by_xpath(
                "//div[@id='fwSubnetListPagingToolbar']/table[@class='x-toolbar-ct']//td[@class='x-toolbar-left']/table//tr[@class='x-toolbar-left-row']/td[1]/table//button[@type='button']").click()
            time.sleep(2)

            log.info("Select the PAN ID: %d" % cgmesh_pan_id)
            driver.find_element_by_xpath(
                "//div[@id='fwSubnetgrid']//div[@class='x-grid3-body']//table[@class='x-grid3-row-table']//div[@class='x-grid3-cell-inner x-grid3-col-panId' and contains(text(),\'%d\')]//parent::td//preceding-sibling::td//div[@class='x-grid3-cell-inner x-grid3-col-checker']" % cgmesh_pan_id).click()
            time.sleep(2)

            log.info("Clicking on \"Cancel StackMode\" button")
            driver.find_element_by_xpath(
                "//table[@id='cancelStackPush']//em/button[@type='button']").click()
            time.sleep(2)

            log.info("Verify the Cancel switching pop-up message")
            cn_str = driver.find_element_by_xpath(
                "//div[@class='x-window-bwrap']//div[@class='x-window-body']//span[@class='ext-mb-text']").text
            if cncl_exp_str in str(cn_str): log.info("Verified: \"%s\"" % cn_str)
            else:
                self.failed(banner("Pop-up message Verification failed - \'%s\'\nExpected: \'%s\'") % (
                cn_str, cncl_exp_str))
            time.sleep(1)

            log.info("Clicking on \"yes\" button")
            driver.find_element_by_xpath("//button[text()='Yes']").click()
            time.sleep(2)

            log.info("Verify Cancel stack mode pop-up message")
            cancel_str = driver.find_element_by_xpath(
                "//div[@class='x-window-bwrap']//div[@class='x-window-body']//span[@class='ext-mb-text']").text
            if cancel_exp_str in str(cancel_str):
                log.info("Verified: \"%s\"" % cancel_str)
            else:
                self.failed(banner("Pop-up message Verification failed - \'%s\'\nExpected: \'%s\'") % (
                cancel_str, cancel_exp_str))

            dte = datetime.datetime.utcnow().strftime('%Y-%m-%d')

            log.info("Clicking on \"OK\" button")
            driver.find_element_by_xpath("//button[text()='OK']").click()
            time.sleep(2)

            log.info("Clicking on \"Cancel StackMode\" button again")
            driver.find_element_by_xpath("//table[@id='cancelStackPush']//em/button[@type='button']").click()
            time.sleep(2)

            log.info("Verify the Cancel switching pop-up message")
            cn_str = driver.find_element_by_xpath(
                "//div[@class='x-window-bwrap']//div[@class='x-window-body']//span[@class='ext-mb-text']").text
            if cncl_exp_str in str(cn_str): log.info("Verified: \"%s\"" % cn_str)
            else: self.failed(banner("Pop-up message Verification failed - \'%s\'\nExpected: \'%s\'") % (cn_str, cncl_exp_str))
            time.sleep(1)

            log.info("Clicking on \"yes\" button")
            driver.find_element_by_xpath("//button[text()='Yes']").click()
            time.sleep(2)

            log.info("Verify Cancel stack mode Active job pop-up message")
            cancel_str = driver.find_element_by_xpath(
                "//div[@class='x-window-bwrap']//div[@class='x-window-body']//span[@class='ext-mb-text']").text
            if cancel_stack_active_job in str(cancel_str): log.info("Verified: \"%s\"" % cancel_str)
            else: self.failed(banner("Pop-up message Verification failed - \'%s\'\nExpected: \'%s\'") % (cancel_str, cancel_stack_active_job))

            log.info("Clicking on \"OK\" button")
            driver.find_element_by_xpath("//button[text()='OK']").click()
            time.sleep(2)

            log.info("Click on Refresh button")
            driver.find_element_by_xpath(
                "//div[@id='fwSubnetListPagingToolbar']//table[@class='x-toolbar-ct']//td[@class='x-toolbar-right']"
                "//table[@class='x-toolbar-right-ct']//tr[@class='x-toolbar-right-row']//td//em/button[@type='button']").click()
            time.sleep(1)

            temp = Push_And_Verify_The_StackMode(driver, cgmesh_pan_id, cncl_stkmd_typ_exp, cancel_msg_exp,
                                                 stack_node_cnt)
            if temp: log.info("Overall stack mode cancel verified successfully")
            else: self.failed(banner("Overall stack mode cancel Failed"))

            log.info('Navigate to Logs tab in the right plane')
            driver.find_element_by_xpath("//li[@id='fwTabs__logTab']//span[text()='Logs']").click()
            time.sleep(4)

            log.info("Click on Refresh button")
            driver.find_element_by_xpath("//div[@id='logPageTB']//td[@class='x-toolbar-right']//tr[@class='x-toolbar-right-row']//table[@class='x-btn x-btn-icon']//button[@type='button']").click()
            time.sleep(1)  

            log.info("Verify the Cancel stack mode and time log message")
            message_list = [element.text for element in driver.find_elements_by_xpath(
                "//div[@id='firmwareMeshLog']//div[@class='x-grid3-body']//div//td[2]//div[contains(text(),'" + dte + "')]/../..//td[6]/div")]

            log.info('Event Message: %s' % message_list)
            if log_msg_cncl not in message_list: raise Exception('Did not see \'%s\' Error in Event message' % log_msg_cncl)
            else: log.info("Verified: \'%s\' Error found in Event message"% log_msg_cncl)

            log.info("Wait for 5 Seconds")
            time.sleep(5)

            log.info(banner('Getting the latest AuditTrails'))
            audit_trail = ui_common_utils.AuditTrail(driver)
            audittrails = audit_trail.get_latest_audittrails()
            operation = audittrails['operations']

            log.info('operation: %s' % operation)
            if 'Cancel Stack' not in operation: raise Exception('Did not see the "Cancel stack" Audit Trail')
            else: log.info("Cancel stack found in Audit trials")

        except Exception as ex:
            self.failed(ex)
            driver_utils.save_screenshot(scriptname='Tc9_Validate_Overall_StackMode_And_Stacktime_Cancel_And_Active_Running_Job',
                                         classname=__class__.__name__)

            try:
                error_logs = test_utils.read_remote_logs(remote_ssh_client=nms_ssh_client,
                                                         log_file=log_file,
                                                         read_error_logs=True, line_number=last_line_number)
                assert error_logs == []
                log.info('No ERROR logs found on FND.')
            except AssertionError as ae:
                driver_utils.save_screenshot(scriptname='Tc9_Validate_Overall_StackMode_And_Stacktime_Cancel_And_Active_Running_Job',
                                             classname=__class__.__name__)
                log.error('Should not see ERROR logs on FND.\nerror_logs: %s' % error_logs)

# Testcase 10
class Tc10_Validate_Per_Device_Stackmode_State_Changes(aetest.Testcase):
    @aetest.test
    def Tc10_Validate_Per_Device_Stackmode_State_Changes(self, driver, ir500_eids, cgmesh_pan_id, stackmd_exp_str, stackmd_cfm_exp_str, log_msg_stkmd):
        try:
            global driver_utils
            global auto_user_ws
            import datetime
            fw_groupname = "default-ir500"

            last_line_number = \
                test_utils.read_remote_logs(remote_ssh_client=nms_ssh_client, log_file=log_file, get_last_line=True)[
                    0].rstrip()

            driver_utils.navigate_to_home()
            fw_up = ui_common_utils.FirmwareUpdate(driver)
            fw_up.nav_sub_menu('firmware_update')
            time.sleep(2)
            driver_utils.ignore_flash_error()
            driver.find_element_by_xpath(
                "//div[@id='leftHandTree']//span[contains(text(),'" + fw_groupname + "')]").click()
            time.sleep(2)
            driver_utils.ignore_flash_error()

            log.info('Navigate to Firmware Management tab in the right plane')
            driver.find_element_by_xpath("//li[@id='fwTabs__mgmtTab']//span[text()='Firmware Management']").click()
            time.sleep(1)

            log.info("Clicking on \"Clear Filter\" button")
            driver.find_element_by_xpath("//div[@id='fwSubnetListPagingToolbar']/table[@class='x-toolbar-ct']//td[@class='x-toolbar-left']/table//tr[@class='x-toolbar-left-row']/td[1]/table//button[@type='button']").click()
            time.sleep(2)

            log.info("Select the PAN ID: %d" % cgmesh_pan_id)
            driver.find_element_by_xpath("//div[@id='fwSubnetgrid']//div[@class='x-grid3-body']//table[@class='x-grid3-row-table']//div[@class='x-grid3-cell-inner x-grid3-col-panId' and contains(text(),\'%d\')]//parent::td//preceding-sibling::td//div[@class='x-grid3-cell-inner x-grid3-col-checker']" % cgmesh_pan_id).click()
            time.sleep(2)

            log.info("Clicking on \"Push StackMode\" button")
            driver.find_element_by_xpath("//table[@id='stackModePush']//em/button[@type='button']").click()
            time.sleep(2)

            log.info("Verify the Push stack mode pop-up message")
            stackmd_str = driver.find_element_by_xpath("//div[@class='x-window-bwrap']//div[@class='x-window-body']//span[@class='ext-mb-text']").text
            if stackmd_exp_str in str(stackmd_str): log.info ("Verified: \"%s\"" % stackmd_str)
            else: self.failed(banner("Pop-up message Verification failed - \'%s\'\nExpected: \'%s\'") % (stackmd_str, stackmd_exp_str))
            time.sleep(1)

            log.info("Clicking on \"yes\" button")
            driver.find_element_by_xpath("//button[text()='Yes']").click()
            time.sleep(2)

            log.info("Verify conformation pop-up message")
            stackmd_cfm_str = driver.find_element_by_xpath("//div[@class='x-window-bwrap']//div[@class='x-window-body']//span[@class='ext-mb-text']").text
            if stackmd_cfm_exp_str in str(stackmd_cfm_str): log.info ("Verified: \"%s\"" % stackmd_cfm_str)
            else: self.failed(banner("Pop-up message Verification failed - \'%s\'\nExpected: \'%s\'") % (stackmd_cfm_str, stackmd_cfm_exp_str))

            dte = datetime.datetime.utcnow().strftime('%Y-%m-%d')

            log.info("Clicking on \"OK\" button")
            driver.find_element_by_xpath("//button[text()='OK']").click()
            time.sleep(1)

            temp = Verify_Push_Stackmode_State_Changes(driver, fw_groupname, ir500_eids)
            if temp: log.info("Push stack mode Stack change status in device tab is Successfull")
            else: self.failed(banner("Push stack mode Stack change status in device tab is Failed"))

            log.info('Navigate to Logs tab in the right plane')
            driver.find_element_by_xpath("//li[@id='fwTabs__logTab']//span[text()='Logs']").click()
            time.sleep(4)

            log.info("Click on Refresh button")
            driver.find_element_by_xpath("//div[@id='logPageTB']//td[@class='x-toolbar-right']//tr[@class='x-toolbar-right-row']//table[@class='x-btn x-btn-icon']//button[@type='button']").click()
            time.sleep(1)  

            log.info("Verify push stack mode and time log message")
            message_list = [element.text for element in driver.find_elements_by_xpath(
                "//div[@id='firmwareMeshLog']//div[@class='x-grid3-body']//div//td[2]//div[contains(text(),'" + dte + "')]/../..//td[6]/div")]

            log.info('Event Message: %s' % message_list)
            if log_msg_stkmd not in message_list: raise Exception('Did not see \'%s\' Error in Event message' % log_msg_stkmd)
            else: log.info("Verified: \'%s\' Error found in Event message"% log_msg_stkmd)

            log.info("Wait for 5 Seconds")
            time.sleep(5)

            log.info(banner('Getting the latest AuditTrails'))
            audit_trail = ui_common_utils.AuditTrail(driver)
            audittrails = audit_trail.get_latest_audittrails()
            operation = audittrails['operations']

            log.info('operation: %s' % operation)
            if 'Stack Mode Push' not in operation: raise Exception('Did not see the "Stack Mode Push" Audit Trail')
            else: log.info("Stack mode push found in Audit trials")

        except Exception as ex:
            self.failed(ex)
            driver_utils.save_screenshot(scriptname='Tc10_Validate_Per_Device_Stackmode_State_Changes',
                                         classname=__class__.__name__)

            try:
                error_logs = test_utils.read_remote_logs(remote_ssh_client=nms_ssh_client, log_file=log_file,
                                                         read_error_logs=True, line_number=last_line_number)
                assert error_logs == []
                log.info('No ERROR logs found on FND.')
            except AssertionError as ae:
                driver_utils.save_screenshot(scriptname='Tc10_Validate_Per_Device_Stackmode_State_Changes',
                                             classname=__class__.__name__)
                log.error('Should not see ERROR logs on FND.\nerror_logs: %s' % error_logs)

# Testcase 11
class Tc11_Validate_Per_Device_Stacktime_State_Changes(aetest.Testcase):
    @aetest.test
    def Tc11_Validate_Per_Device_Stacktime_State_Changes(self, driver, ir500_eids, cgmesh_pan_id, stackmd_exp_str, stktm_typ_exp, log_msg_skttm):
        try:
            global driver_utils
            global auto_user_ws
            import datetime
            fw_groupname = "default-ir500"

            last_line_number = \
                test_utils.read_remote_logs(remote_ssh_client=nms_ssh_client, log_file=log_file,
                                            get_last_line=True)[
                    0].rstrip()

            driver_utils.navigate_to_home()
            fw_up = ui_common_utils.FirmwareUpdate(driver)
            fw_up.nav_sub_menu('firmware_update')
            time.sleep(2)
            driver_utils.ignore_flash_error()
            driver.find_element_by_xpath(
                "//div[@id='leftHandTree']//span[contains(text(),'" + fw_groupname + "')]").click()
            time.sleep(2)
            driver_utils.ignore_flash_error()

            log.info('Navigate to Firmware Management tab in the right plane')
            driver.find_element_by_xpath(
                "//li[@id='fwTabs__mgmtTab']//span[text()='Firmware Management']").click()
            time.sleep(1) 

            log.info("Clicking on \"Clear Filter\" button")
            driver.find_element_by_xpath("//div[@id='fwSubnetListPagingToolbar']/table[@class='x-toolbar-ct']//td[@class='x-toolbar-left']/table//tr[@class='x-toolbar-left-row']/td[1]/table//button[@type='button']").click()
            time.sleep(2)

            log.info("Select the PAN ID: %d" % cgmesh_pan_id)
            driver.find_element_by_xpath("//div[@id='fwSubnetgrid']//div[@class='x-grid3-body']//table[@class='x-grid3-row-table']//div[@class='x-grid3-cell-inner x-grid3-col-panId' and contains(text(),\'%d\')]//parent::td//preceding-sibling::td//div[@class='x-grid3-cell-inner x-grid3-col-checker']" % cgmesh_pan_id).click()
            time.sleep(2)

            log.info("Clicking on \"Push StackMode Time\" button")
            driver.find_element_by_xpath("//table[@id='stackModeTimePush']//em/button[@type='button']").click()
            time.sleep(2)

            log.info("Verify Push stack mode time pop-up message")
            stackmd_str = driver.find_element_by_xpath("//div[@class='x-window-bwrap']//div[@class='x-window-body']//span[@class='ext-mb-text']").text
            if stackmd_exp_str in str(stackmd_str): log.info ("Verified: \"%s\"" % stackmd_str)
            else: self.failed(banner("Pop-up message Verification failed - \'%s\'\nExpected: \'%s\'") % (stackmd_str, stackmd_exp_str))
            time.sleep(1)

            log.info("Clicking on \"yes\" button")
            driver.find_element_by_xpath("//button[text()='Yes']").click()
            time.sleep(2)

            log.info("Current Date: " + datetime.datetime.utcnow().strftime('%Y-%m-%d'))
            log.info("Current Time: " + datetime.datetime.utcnow().strftime("%H:%M"))
            dt = datetime.datetime.utcnow().strftime('%Y-%m-%d')
            t1 = datetime.datetime.utcnow() + datetime.timedelta(minutes=300)
            inc_tm = str(t1.strftime("%H:%M"))
            #sch_tm = inc_tm + ":00.0"
            sch_tm = inc_tm + ":00.0"
            config_dt_tm = dt + " " + sch_tm
            log.info("Incremented Time: " + inc_tm)
            driver.find_element_by_xpath("//input[@id='stackDTFtime']").clear()
            driver.find_element_by_xpath("//input[@id='stackDTFtime']").send_keys(inc_tm)
            driver.find_element_by_xpath("//input[@id='stackDTFdate']/../img").click()
            time.sleep(1)

            log.info("Clicking on \"Today\" button")
            driver.find_element_by_xpath("//button[text()='Today']").click()
            time.sleep(2)

            log.info("Clicking on \"Schedule\" button")
            driver.find_element_by_xpath("//button[text()='Schedule']").click()
            time.sleep(2)

            log.info("Clicking on \"OK\" button")
            driver.find_element_by_xpath("//button[text()='OK']").click()
            
            log.info("Wait for 15 Seconds")
            time.sleep(15)

            log.info("Click on Refresh button")
            driver.find_element_by_xpath("//div[@id='fwSubnetListPagingToolbar']//table[@class='x-toolbar-ct']//td[@class='x-toolbar-right']"
                                         "//table[@class='x-toolbar-right-ct']//tr[@class='x-toolbar-right-row']//td//em/button[@type='button']").click()

            log.info("Wait for 2 Seconds")
            time.sleep(2) 
            
            temp = Verify_Push_Stackmode_time_State_Changes(driver, fw_groupname, ir500_eids, stktm_typ_exp, config_dt_tm)
            if temp: log.info("Push stack time Stack change status in device tab is Successfull")
            else: self.failed(banner("Push time mode Stack change status in device tab is Failed"))    

            log.info('Navigate to Logs tab in the right plane')
            driver.find_element_by_xpath("//li[@id='fwTabs__logTab']//span[text()='Logs']").click()
            time.sleep(4)

            log.info("Click on Refresh button")
            driver.find_element_by_xpath("//div[@id='logPageTB']//td[@class='x-toolbar-right']//tr[@class='x-toolbar-right-row']//table[@class='x-btn x-btn-icon']//button[@type='button']").click()
            time.sleep(1)  

            log.info("Verify the Push stack time log message")
            message_list = [element.text for element in driver.find_elements_by_xpath(
                "//div[@id='firmwareMeshLog']//div[@class='x-grid3-body']//div//td[2]//div[contains(text(),'" + dt + "')]/../..//td[6]/div")]

            log.info('Event Message: %s' % message_list)
            if log_msg_skttm not in message_list: raise Exception('Did not see \'%s\' Error in Event message' % log_msg_skttm)
            else: log.info("Verified: \'%s\' Error found in Event message"% log_msg_skttm) 

            log.info("Wait for 5 Seconds")
            time.sleep(5)

            log.info(banner('Getting the latest AuditTrails'))
            audit_trail = ui_common_utils.AuditTrail(driver)
            audittrails = audit_trail.get_latest_audittrails()
            operation = audittrails['operations']

            log.info('operation: %s' % operation)
            if 'Scheduled Stack Switch Time' not in operation: raise Exception('Did not see the "Scheduled Stack Switch Time" Audit Trail')
            else: log.info("Scheduled Stack Switch Time found in Audit trials")

        except Exception as ex:
            self.failed(ex)
            driver_utils.save_screenshot(scriptname='Tc11_Validate_Per_Device_Stacktime_State_Changes',
                                         classname=__class__.__name__)

            try:
                error_logs = test_utils.read_remote_logs(remote_ssh_client=nms_ssh_client,
                                                         log_file=log_file,
                                                         read_error_logs=True, line_number=last_line_number)
                assert error_logs == []
                log.info('No ERROR logs found on FND.')
            except AssertionError as ae:
                driver_utils.save_screenshot(scriptname='Tc11_Validate_Per_Device_Stacktime_State_Changes',
                                             classname=__class__.__name__)
                log.error('Should not see ERROR logs on FND.\nerror_logs: %s' % error_logs)

#Testcase 12
class Tc12_Validate_Per_Device_Cancel_Stack_State_Changes(aetest.Testcase):
    @aetest.test
    def Tc12_Validate_Per_Device_Cancel_Stack_State_Changes(self, driver, ir500_eids, cgmesh_pan_id, cncl_exp_str, cancel_exp_str, log_msg_cncl):
        try:
            global driver_utils
            global auto_user_ws
            import datetime
            fw_groupname = "default-ir500"

            last_line_number = \
                test_utils.read_remote_logs(remote_ssh_client=nms_ssh_client, log_file=log_file, get_last_line=True)[
                    0].rstrip()

            driver_utils.navigate_to_home()
            fw_up = ui_common_utils.FirmwareUpdate(driver)
            fw_up.nav_sub_menu('firmware_update')
            time.sleep(2)
            driver_utils.ignore_flash_error()

            driver.find_element_by_xpath(
                "//div[@id='leftHandTree']//span[contains(text(),'" + fw_groupname + "')]").click()
            time.sleep(2)
            driver_utils.ignore_flash_error()

            log.info('Navigate to Firmware Management tab in the right plane')
            driver.find_element_by_xpath("//li[@id='fwTabs__mgmtTab']//span[text()='Firmware Management']").click()
            time.sleep(1)       

            log.info("Clicking on \"Clear Filter\" button")
            driver.find_element_by_xpath("//div[@id='fwSubnetListPagingToolbar']/table[@class='x-toolbar-ct']//td[@class='x-toolbar-left']/table//tr[@class='x-toolbar-left-row']/td[1]/table//button[@type='button']").click()
            time.sleep(2)
            log.info("Select the PAN ID: %d" % cgmesh_pan_id)
            driver.find_element_by_xpath("//div[@id='fwSubnetgrid']//div[@class='x-grid3-body']//table[@class='x-grid3-row-table']//div[@class='x-grid3-cell-inner x-grid3-col-panId' and contains(text(),\'%d\')]"
                                         "//parent::td//preceding-sibling::td//div[@class='x-grid3-cell-inner x-grid3-col-checker']" % cgmesh_pan_id).click()
            time.sleep(2)
            log.info("Clicking on \"Cancel StackMode\" button")
            driver.find_element_by_xpath("//table[@id='cancelStackPush']//em/button[@type='button']").click()
            time.sleep(2)

            log.info("Verify the Cancel switching pop-up message")
            cn_str = driver.find_element_by_xpath("//div[@class='x-window-bwrap']//div[@class='x-window-body']//span[@class='ext-mb-text']").text
            if cncl_exp_str in str(cn_str): log.info("Verified: \"%s\"" % cn_str)
            else: self.failed(banner("Pop-up message Verification failed - \'%s\'\nExpected: \'%s\'") % (cn_str, cncl_exp_str))
            time.sleep(1)

            log.info("Clicking on \"yes\" button")
            driver.find_element_by_xpath("//button[text()='Yes']").click()
            time.sleep(2)

            log.info("Verify Cancel stack mode pop-up message")
            cancel_str = driver.find_element_by_xpath("//div[@class='x-window-bwrap']//div[@class='x-window-body']//span[@class='ext-mb-text']").text
            if cancel_exp_str in str(cancel_str): log.info("Verified: \"%s\"" % cancel_str)
            else: self.failed(banner("Pop-up message Verification failed - \'%s\'\nExpected: \'%s\'") % (cancel_str, cancel_exp_str))
            time.sleep(1)

            dte = datetime.datetime.utcnow().strftime('%Y-%m-%d')

            log.info("Clicking on \"OK\" button")
            driver.find_element_by_xpath("//button[text()='OK']").click()
            time.sleep(2)
            
            temp = Verify_Cancel_Stackmode_State_Changes(driver, fw_groupname, ir500_eids)
            if temp: log.info("Cancel Stack change status in device tab is Successfull")
            else: self.failed(banner("Cancel Stack change status in device tab is Successfull"))  

            log.info('Navigate to Logs tab in the right plane')
            driver.find_element_by_xpath("//li[@id='fwTabs__logTab']//span[text()='Logs']").click()
            time.sleep(4)

            log.info("Click on Refresh button")
            driver.find_element_by_xpath("//div[@id='logPageTB']//td[@class='x-toolbar-right']//tr[@class='x-toolbar-right-row']//table[@class='x-btn x-btn-icon']//button[@type='button']").click()
            time.sleep(1)

            log.info("Verify the Cancel stack mode and time log message")
            message_list = [element.text for element in driver.find_elements_by_xpath(
                "//div[@id='firmwareMeshLog']//div[@class='x-grid3-body']//div//td[2]//div[contains(text(),'" + dte + "')]/../..//td[6]/div")]

            log.info('Event Message: %s' % message_list)
            if log_msg_cncl not in message_list: raise Exception('Did not see \'%s\' Error in Event message' % log_msg_cncl)
            else: log.info("Verified: \'%s\' Error found in Event message"% log_msg_cncl)  

            log.info("Wait for 5 Seconds")
            time.sleep(5)

            log.info(banner('Getting the latest AuditTrails'))
            audit_trail = ui_common_utils.AuditTrail(driver)
            audittrails = audit_trail.get_latest_audittrails()
            operation = audittrails['operations']

            log.info('operation: %s' % operation)
            if 'Cancel Stack' not in operation: raise Exception('Did not see the "Cancel stack" Audit Trail')
            else: log.info("Cancel stack found in Audit trials")

        except Exception as ex:
            self.failed(ex)
            driver_utils.save_screenshot(scriptname='Tc12_Validate_Per_Device_Cancel_Stack_State_Changes',
                                         classname=__class__.__name__)

            try:
                error_logs = test_utils.read_remote_logs(remote_ssh_client=nms_ssh_client,
                                                         log_file=log_file,
                                                         read_error_logs=True, line_number=last_line_number)
                assert error_logs == []
                log.info('No ERROR logs found on FND.')
            except AssertionError as ae:
                driver_utils.save_screenshot(scriptname='Tc12_Validate_Per_Device_Cancel_Stack_State_Changes',
                                             classname=__class__.__name__)
                log.error('Should not see ERROR logs on FND.\nerror_logs: %s' % error_logs)


#Testcase 13
class TC13_Validate_Switch_To_Wisun_Buttons_When_RBAC_Without_Endpoint_Permission(aetest.Testcase):
    @aetest.test
    def TC13_Validate_Switch_To_Wisun_Buttons_When_RBAC_Without_Endpoint_Permission(self, driver, nms_ip):
        # return True
        fail_flag = False
        last_line_number = test_utils.read_remote_logs(remote_ssh_client=nms_ssh_client, log_file=log_file, get_last_line=True)[0].rstrip()
        driver_utils.navigate_to_home()
        fw_groupname = "default-ir500"  

        try:
            users = ui_common_utils.Users(driver)
            users.nav_sub_menu('users')
            log.info(banner('Creating monitor_user'))
            user_added = users.add_user('monitor_user', 'Sgbu1234!')

            monitor_user_driver = webdriver.Firefox()
            monitor_user_driver.implicitly_wait(10)
            monitor_user_driver.maximize_window()

            log.info(banner('Logging and changing password for monitor_user.'))
            monitor_user_driver_utils = ui_common_utils.DriverUtils(monitor_user_driver)
            monitor_user_driver = monitor_user_driver_utils.first_time_login(
                                    nms_ip, 'monitor_user', 'Sgbu1234!', 'Sgbu123!')


            fw_up = ui_common_utils.FirmwareUpdate(monitor_user_driver)
            fw_up.nav_sub_menu('firmware_update')
            time.sleep(2)
            monitor_user_driver_utils.ignore_flash_error()

            log.info("Clicking on \'%s\' group" % fw_groupname)
            monitor_user_driver.find_element_by_xpath(
                "//div[@id='leftHandTree']//span[contains(text(),'" + fw_groupname + "')]").click()
            time.sleep(2)
            monitor_user_driver_utils.ignore_flash_error()

            log.info('Navigate to \'Firmware Management\' tab in the right plane')
            monitor_user_driver.find_element_by_xpath("//li[@id='fwTabs__mgmtTab']//span[text()='Firmware Management']").click()
            time.sleep(1) 

            try:
                log.info("Search for \'Push StackMode\' Button")
                stkmd_val = monitor_user_driver.find_element_by_xpath(
                    "//table[@id='stackModeTimePush']//em/button[@type='button']").text
                if not stkmd_val: log.info("Verified: \'Push StackMode\' Button is removed")
                else: self.failed(banner("Failed to remove \'Push StackMode\' Button"))
                time.sleep(1)

                log.info("Search for \'Push Stack Time\' Button")
                stktm_val = monitor_user_driver.find_element_by_xpath(
                    "//table[@id='stackModeTimePush']//em/button[@type='button']").text
                if not stktm_val: log.info("Verified: \'Push Stack Time\' Button is removed")
                else: self.failed(banner("Failed to remove \'Push Stack Time\' Button"))
                time.sleep(1)

                log.info("Search for \'Cancel Stack\' Button")
                cncl_val = monitor_user_driver.find_element_by_xpath(
                    "//table[@id='cancelStackPush']//em/button[@type='button']").text
                if not cncl_val: log.info("Verified: \'Cancel Stack\' Button is removed")
                else: self.failed(banner("Failed to remove \'Cancel Stack\' Button"))
                time.sleep(1)
                
            except Exception as ex:
                log.error(e)

            monitor_user_driver_utils.logout()
            monitor_user_driver.quit()

        except Exception as ex:
            fail_flag = True
            self.failed(ex)
            driver_utils.save_screenshot(scriptname='TC13_Validate_Switch_To_Wisun_Buttons_When_RBAC_Without_Endpoint_Permission',
                                         classname=__class__.__name__)
            log.error(e)
            driver.refresh()
            time.sleep(5)
            monitor_user_driver_utils.logout()
            monitor_user_driver.quit()

        finally:
            log.info('Delete test_user.')
            user_deleted = users.delete_user('monitor_user')

        try:
            error_logs = test_utils.read_remote_logs(remote_ssh_client=nms_ssh_client,
                                                     log_file=log_file,
                                                     read_error_logs=True, line_number=last_line_number)
            assert error_logs == []
            log.info('No ERROR logs found on FND.')

        except AssertionError as ae:
            driver_utils.save_screenshot(scriptname='TC13_Validate_Switch_To_Wisun_Buttons_When_RBAC_Without_Endpoint_Permission',
                                         classname=__class__.__name__)
            log.error('Should not see ERROR logs on FND.\nerror_logs: %s' % error_logs)

        try: assert fail_flag == False
        except AssertionError as ae: self.failed('Something went wrong. Check screenshots for this section')

# Testcase 14
class Tc14_Validate_Scheduling_More_than_49_days_stacktime(aetest.Testcase):
    @aetest.test
    def Tc14_Validate_Scheduling_More_than_49_days_stacktime(self, driver, cgmesh_pan_id, stackmd_exp_str, abv_49_days_exp_str):
        try:
            global driver_utils
            global auto_user_ws
            import datetime
            fw_groupname = "default-ir500"
            tm = "00:00"

            last_line_number = \
                test_utils.read_remote_logs(remote_ssh_client=nms_ssh_client, log_file=log_file, get_last_line=True)[
                    0].rstrip()

            driver_utils.navigate_to_home()
            fw_up = ui_common_utils.FirmwareUpdate(driver)
            fw_up.nav_sub_menu('firmware_update')
            time.sleep(2)
            driver_utils.ignore_flash_error()

            driver.find_element_by_xpath(
                "//div[@id='leftHandTree']//span[contains(text(),'" + fw_groupname + "')]").click()
            time.sleep(2)
            driver_utils.ignore_flash_error()

            log.info('Navigate to Firmware Management tab in the right plane')
            driver.find_element_by_xpath("//li[@id='fwTabs__mgmtTab']//span[text()='Firmware Management']").click()
            time.sleep(1)

            log.info("Clicking on \"Clear Filter\" button")
            driver.find_element_by_xpath(
                "//div[@id='fwSubnetListPagingToolbar']/table[@class='x-toolbar-ct']//td[@class='x-toolbar-left']/table//tr[@class='x-toolbar-left-row']/td[1]/table//button[@type='button']").click()
            time.sleep(2)

            log.info("Select the PAN ID: %d" % cgmesh_pan_id)
            driver.find_element_by_xpath(
                "//div[@id='fwSubnetgrid']//div[@class='x-grid3-body']//table[@class='x-grid3-row-table']//div[@class='x-grid3-cell-inner x-grid3-col-panId' and contains(text(),\'%d\')]"
                "//parent::td//preceding-sibling::td//div[@class='x-grid3-cell-inner x-grid3-col-checker']" % cgmesh_pan_id).click()
            time.sleep(2)

            log.info("Clicking on \"Push StackMode Time\" button")
            driver.find_element_by_xpath("//table[@id='stackModeTimePush']//em/button[@type='button']").click()
            time.sleep(2)

            log.info("Verify Push stack mode time pop-up message")
            stackmd_str = driver.find_element_by_xpath(
                "//div[@class='x-window-bwrap']//div[@class='x-window-body']//span[@class='ext-mb-text']").text
            if stackmd_exp_str in str(stackmd_str):
                log.info("Verified: \"%s\"" % stackmd_str)
            else:
                self.failed(banner("Pop-up message Verification failed - \'%s\'\nExpected: \'%s\'") % (
                    stackmd_str, stackmd_exp_str))
            time.sleep(1)

            log.info("Clicking on \"yes\" button")
            driver.find_element_by_xpath("//button[text()='Yes']").click()
            time.sleep(2)

            log.info("Entering the past time : %s" % tm)
            driver.find_element_by_xpath("//input[@id='stackDTFtime']").clear()
            driver.find_element_by_xpath("//input[@id='stackDTFtime']").send_keys(tm)
            driver.find_element_by_xpath("//input[@id='stackDTFdate']/../img").click()
            time.sleep(1)

            log.info("Double click on \'Next\' button and select the date \'28\'")
            driver.find_element_by_xpath("//ul[@class='x-menu-list']//div[@class='x-date-picker x-unselectable']//table//a[@title='Next Month (Control+Right)']").click()
            time.sleep(1)
            driver.find_element_by_xpath("//ul[@class='x-menu-list']//div[@class='x-date-picker x-unselectable']//table//a[@title='Next Month (Control+Right)']").click()
            time.sleep(1)
            driver.find_element_by_xpath("//ul[@class='x-menu-list']//div[@class='x-date-picker x-unselectable']//table//table[@class='x-date-inner']//span[.='28']").click()
            time.sleep(1)

            dte = datetime.datetime.utcnow().strftime('%Y-%m-%d')

            log.info("Clicking on \"Schedule\" button")
            driver.find_element_by_xpath("//button[text()='Schedule']").click()
            time.sleep(2)

            log.info("Verify if scheduling stack time is not allowed for past date/time")
            cgmesh_str = driver.find_element_by_xpath(
                "//div[@class='x-window-bwrap']//div[@class='x-window-body']//span[@class='ext-mb-text']").text
            if cgmesh_str.startswith(abv_49_days_exp_str):
                log.info("Verified: \"%s\"" % cgmesh_str)
            else:
                self.failed(banner("Pop-up message Verification failed - \'%s\'\nExpected: \'%s\'") % (
                    cgmesh_str, abv_49_days_exp_str))

            log.info("Clicking on \"OK\" button")
            driver.find_element_by_xpath("//button[text()='OK']").click()
            time.sleep(2)

            log.info("Clicking on \"Close\" button")
            driver.find_element_by_xpath("//button[text()='Close']").click()
            time.sleep(2)

        except Exception as ex:
            self.failed(ex)
            driver_utils.save_screenshot(scriptname='Tc14_Validate_Scheduling_More_than_49_days_stacktime',
                                         classname=__class__.__name__)

            try:
                error_logs = test_utils.read_remote_logs(remote_ssh_client=nms_ssh_client, log_file=log_file,
                                                         read_error_logs=True, line_number=last_line_number)
                assert error_logs == []
                log.info('No ERROR logs found on FND.')
            except AssertionError as ae:
                driver_utils.save_screenshot(scriptname='Tc14_Validate_Scheduling_More_than_49_days_stacktime',
                                             classname=__class__.__name__)
                log.error('Should not see ERROR logs on FND.\nerror_logs: %s' % error_logs)


# Testcase 15
class Tc15_Validate_Overall_Stack_Mode_Push_From_Custom_Group(aetest.Testcase):
    @aetest.test
    def Tc15_Validate_Overall_Stack_Mode_Push_From_Custom_Group(self, driver, ir510_eids ,cgmesh_pan_id, stackmd_exp_str, cus_fw_groupname,
                                                 def_fw_groupname, stack_node_cnt1, stackmd_cfm_exp_str, stackmd_typ_exp, pshstack_msg_exp, log_msg_stkmd):
        try:
            global driver_utils
            global auto_user_ws
            import datetime

            last_line_number = \
                test_utils.read_remote_logs(remote_ssh_client=nms_ssh_client, log_file=log_file, get_last_line=True)[
                    0].rstrip()

            driver_utils.navigate_to_home()
            fw_up = ui_common_utils.FirmwareUpdate(driver)
            fw_up.nav_sub_menu('firmware_update')
            time.sleep(2)
            driver_utils.ignore_flash_error()

            time.sleep(1)
            log.info('Add new firmware group - %s'% cus_fw_groupname)
            fw_up.add_group('endpoint', cus_fw_groupname)
            time.sleep(2)
            log.info('Move %s Nodes to %s group from \'default-cgmesh\' group' % (ir510_eids, cus_fw_groupname))
            fw_up.change_firmware_group('default-ir500', cus_fw_groupname, ir510_eids, type='endpoint')
            time.sleep(3)

            log.info('Clicking on \'%s\' group' % cus_fw_groupname)
            driver.find_element_by_xpath(
                "//div[@id='leftHandTree']//span[contains(text(),'" + cus_fw_groupname + "')]").click()
            time.sleep(2)
            driver_utils.ignore_flash_error()

            log.info('Navigate to Firmware Management tab in the right plane')
            driver.find_element_by_xpath("//li[@id='fwTabs__mgmtTab']//span[text()='Firmware Management']").click()
            time.sleep(1)

            log.info("Clicking on \"Clear Filter\" button")
            driver.find_element_by_xpath(
                "//div[@id='fwSubnetListPagingToolbar']/table[@class='x-toolbar-ct']//td[@class='x-toolbar-left']/table"
                "//tr[@class='x-toolbar-left-row']/td[1]/table//button[@type='button']").click()
            time.sleep(2)

            log.info("Select the PAN ID: %d" % cgmesh_pan_id)
            driver.find_element_by_xpath(
                "//div[@id='fwSubnetgrid']//div[@class='x-grid3-body']//table[@class='x-grid3-row-table']"
                "//div[@class='x-grid3-cell-inner x-grid3-col-panId' and contains(text(),\'%d\')]"
                "//parent::td//preceding-sibling::td//div[@class='x-grid3-cell-inner x-grid3-col-checker']" % cgmesh_pan_id).click()
            time.sleep(2)

            dte = datetime.datetime.utcnow().strftime('%Y-%m-%d')

            log.info("Clicking on \"Push StackMode\" button")
            driver.find_element_by_xpath("//table[@id='stackModePush']//em/button[@type='button']").click()
            time.sleep(2)

            log.info("Verify the Push stack mode pop-up message")
            stackmd_str = driver.find_element_by_xpath(
                "//div[@class='x-window-bwrap']//div[@class='x-window-body']//span[@class='ext-mb-text']").text
            if stackmd_exp_str in str(stackmd_str):
                log.info("Verified: \"%s\"" % stackmd_str)
            else:
                self.failed(banner("Pop-up message Verification failed - \'%s\'\nExpected: \'%s\'") % (
                    stackmd_str, stackmd_exp_str))
            time.sleep(1)

            log.info("Clicking on \"yes\" button")
            driver.find_element_by_xpath("//button[text()='Yes']").click()
            time.sleep(2)

            log.info("Verify conformation pop-up message")
            stackmd_cfm_str = driver.find_element_by_xpath(
                "//div[@class='x-window-bwrap']//div[@class='x-window-body']//span[@class='ext-mb-text']").text
            if stackmd_cfm_exp_str in str(stackmd_cfm_str):
                log.info("Verified: \"%s\"" % stackmd_cfm_str)
            else:
                self.failed(banner("Pop-up message Verification failed - \'%s\'\nExpected: \'%s\'") % (
                    stackmd_cfm_str, stackmd_cfm_exp_str))
            time.sleep(1)

            log.info("Clicking on \"OK\" button")
            driver.find_element_by_xpath("//button[text()='OK']").click()

            log.info("Wait for 15 Seconds")
            time.sleep(15)

            log.info("Click on Refresh button")
            driver.find_element_by_xpath(
                "//div[@id='fwSubnetListPagingToolbar']//table[@class='x-toolbar-ct']//td[@class='x-toolbar-right']"
                "//table[@class='x-toolbar-right-ct']//tr[@class='x-toolbar-right-row']//td//em/button[@type='button']").click()

            log.info("Wait for 5 Seconds")
            time.sleep(5)

            log.info("Verify Push stack mode time in \'%s\' group" % cus_fw_groupname)
            temp = Push_And_Verify_The_StackMode(driver, cgmesh_pan_id, stackmd_typ_exp, pshstack_msg_exp, stack_node_cnt1)
            if temp:
                log.info("Overall Scheduled Stack mode time is Successfull in \'%s\'" % cus_fw_groupname)
            else:
                self.failed(banner("Overall Scheduled Stack mode time Failed in \'%s\'" % cus_fw_groupname))
            time.sleep(2)

            log.info('Navigate to Logs tab in the right plane')
            driver.find_element_by_xpath("//li[@id='fwTabs__logTab']//span[text()='Logs']").click()
            time.sleep(4)

            log.info("Click on Refresh button")
            driver.find_element_by_xpath(
                "//div[@id='logPageTB']//td[@class='x-toolbar-right']//tr[@class='x-toolbar-right-row']//table[@class='x-btn x-btn-icon']//button[@type='button']").click()
            time.sleep(1)

            log.info("Verify the stack mode push log message")
            message_list = [element.text for element in driver.find_elements_by_xpath(
                "//div[@id='firmwareMeshLog']//div[@class='x-grid3-body']//div//td[2]//div[contains(text(),'" + dte + "')]/../..//td[6]/div")]

            log.info('Event Message: %s' % message_list)
            if log_msg_stkmd not in message_list:
                raise Exception('Did not see the \"%s\" in Event message' % log_msg_stkmd)
            else:
                log.info("\'%s\' found in Event message" % log_msg_stkmd)

            log.info('Clicking on \'%s\' group' % def_fw_groupname)
            driver.find_element_by_xpath(
                "//div[@id='leftHandTree']//span[contains(text(),'" + def_fw_groupname + "')]").click()
            time.sleep(2)
            driver_utils.ignore_flash_error()

            log.info('Navigate to Firmware Management tab in the right plane')
            driver.find_element_by_xpath("//li[@id='fwTabs__mgmtTab']//span[text()='Firmware Management']").click()
            time.sleep(1)

            log.info("Click on Refresh button")
            driver.find_element_by_xpath(
                "//div[@id='fwSubnetListPagingToolbar']//table[@class='x-toolbar-ct']//td[@class='x-toolbar-right']"
                "//table[@class='x-toolbar-right-ct']//tr[@class='x-toolbar-right-row']//td//em/button[@type='button']").click()

            log.info("Wait for 2 Seconds")
            time.sleep(2)

            log.info("Verify Push stack mode time in \'%s\' group" % def_fw_groupname)
            temp = Push_And_Verify_The_StackMode_In_Custom_Group(driver, cgmesh_pan_id, stackmd_typ_exp, pshstack_msg_exp, stack_node_cnt1)
            if temp:
                log.info("Overall Scheduled Stack mode time is Successfull in \'%s\'" % def_fw_groupname)
            else:
                self.failed(banner("Overall Scheduled Stack mode time Failed in \'%s\'" % def_fw_groupname))

            log.info("Wait for 5 Seconds")
            time.sleep(5)

            log.info(banner('Getting the latest AuditTrails'))
            audit_trail = ui_common_utils.AuditTrail(driver)
            audittrails = audit_trail.get_latest_audittrails()
            operation = audittrails['operations']

            log.info('operation: %s' % operation)
            if 'Stack Mode Push' not in operation:
                raise Exception('Did not see the "Stack Mode Push" Audit Trail')
            else:
                log.info("Stack mode push found in Audit trials")

        except Exception as ex:
            self.failed(ex)
            driver_utils.save_screenshot(scriptname='Tc15_Validate_Overall_Stack_Mode_Push_From_Custom_Group',
                                         classname=__class__.__name__)

        finally:
            fw_up.nav_sub_menu('firmware_update')
            time.sleep(2)
            driver_utils.ignore_flash_error()
            time.sleep(1)
            log.info('Delete the firmware group - %s' % (cus_fw_groupname))
            fw_up.change_firmware_group(cus_fw_groupname, 'default-ir500', ir510_eids, type='endpoint')
            time.sleep(2)
            fw_up.delete_group('endpoint', cus_fw_groupname)
            time.sleep(2)

        try:
                error_logs = test_utils.read_remote_logs(remote_ssh_client=nms_ssh_client, log_file=log_file,
                                                         read_error_logs=True, line_number=last_line_number)
                assert error_logs == []
                log.info('No ERROR logs found on FND.')
        except AssertionError as ae:
                driver_utils.save_screenshot(scriptname='Tc15_Validate_Overall_Stack_Mode_Push_From_Custom_Group',
                                             classname=__class__.__name__)
                log.error('Should not see ERROR logs on FND.\nerror_logs: %s' % error_logs)

# Testcase 16
class Tc16_Validate_Overall_Stack_Time_Push_From_Custom_Group(aetest.Testcase):
    @aetest.test
    def Tc16_Validate_Overall_Stack_Time_Push_From_Custom_Group(self, driver, nms_server, ir510_eids, cus_fw_groupname, def_fw_groupname,
                                                                      cgmesh_pan_id, stackmd_exp_str, stack_node_cnt1,
                                                                      stktm_typ_exp, pshstack_tme_msg_exp, log_msg_skttm):
        try:
            global driver_utils
            global auto_user_ws
            import datetime

            last_line_number = \
                test_utils.read_remote_logs(remote_ssh_client=nms_ssh_client, log_file=log_file, get_last_line=True)[
                    0].rstrip()

            driver_utils.navigate_to_home()
            fw_up = ui_common_utils.FirmwareUpdate(driver)
            fw_up.nav_sub_menu('firmware_update')
            time.sleep(2)
            driver_utils.ignore_flash_error()

            time.sleep(1)
            log.info('Add new firmware group - %s'% cus_fw_groupname)
            fw_up.add_group('endpoint', cus_fw_groupname)
            time.sleep(2)
            log.info('Move %s Nodes to %s group from \'default-cgmesh\' group' % (ir510_eids, cus_fw_groupname))
            fw_up.change_firmware_group('default-ir500', cus_fw_groupname, ir510_eids, type='endpoint')
            time.sleep(3)

            log.info('Clicking on \'%s\' group' % cus_fw_groupname)
            driver.find_element_by_xpath(
                "//div[@id='leftHandTree']//span[contains(text(),'" + cus_fw_groupname + "')]").click()
            time.sleep(2)
            driver_utils.ignore_flash_error()

            log.info('Navigate to Firmware Management tab in the right plane')
            driver.find_element_by_xpath("//li[@id='fwTabs__mgmtTab']//span[text()='Firmware Management']").click()
            time.sleep(1)

            log.info("Clicking on \"Clear Filter\" button")
            driver.find_element_by_xpath(
                "//div[@id='fwSubnetListPagingToolbar']/table[@class='x-toolbar-ct']//td[@class='x-toolbar-left']/table"
                "//tr[@class='x-toolbar-left-row']/td[1]/table//button[@type='button']").click()
            time.sleep(2)

            log.info("Select the PAN ID: %d" % cgmesh_pan_id)
            driver.find_element_by_xpath(
                "//div[@id='fwSubnetgrid']//div[@class='x-grid3-body']//table[@class='x-grid3-row-table']"
                "//div[@class='x-grid3-cell-inner x-grid3-col-panId' and contains(text(),\'%d\')]"
                "//parent::td//preceding-sibling::td//div[@class='x-grid3-cell-inner x-grid3-col-checker']" % cgmesh_pan_id).click()
            time.sleep(2)

            log.info("Clicking on \"Push StackMode Time\" button")
            driver.find_element_by_xpath("//table[@id='stackModeTimePush']//em/button[@type='button']").click()
            time.sleep(2)

            log.info("Verify Push stack mode time pop-up message")
            stackmd_str = driver.find_element_by_xpath(
                "//div[@class='x-window-bwrap']//div[@class='x-window-body']//span[@class='ext-mb-text']").text
            if stackmd_exp_str in str(stackmd_str):
                log.info("Verified: \"%s\"" % stackmd_str)
            else:
                self.failed(banner("Pop-up message Verification failed - \'%s\'\nExpected: \'%s\'") % (
                    stackmd_str, stackmd_exp_str))
            time.sleep(1)

            log.info("Clicking on \"yes\" button")
            driver.find_element_by_xpath("//button[text()='Yes']").click()
            time.sleep(2)

            log.info("Current Date: " + datetime.datetime.utcnow().strftime('%Y-%m-%d'))
            log.info("Current Time: " + datetime.datetime.utcnow().strftime("%H:%M"))
            dt = datetime.datetime.utcnow().strftime('%Y-%m-%d')
            t1 = datetime.datetime.utcnow() + datetime.timedelta(minutes=300)
            inc_tm = str(t1.strftime("%H:%M"))
            # sch_tm = inc_tm + ":00.0"
            sch_tm = inc_tm + ":00"
            config_dt_tm = dt + " " + sch_tm
            log.info("Incremented Time: " + inc_tm)
            driver.find_element_by_xpath("//input[@id='stackDTFtime']").clear()
            driver.find_element_by_xpath("//input[@id='stackDTFtime']").send_keys(inc_tm)
            # driver.find_element_by_xpath("//input[@id='stackDTFdate']/../img").click()
            time.sleep(1)

            dt1, t11 = Get_Nms_Date_And_Time(self, nms_server)
            log.info("Current FND Date: %s" % dt1)
            log.info("Current FND Time: %s" % t11)

            # log.info("Clicking on \"Today\" button")
            # driver.find_element_by_xpath("//button[text()='Today']").click()
            # time.sleep(2)

            log.info("Clicking on \"Schedule\" button")
            driver.find_element_by_xpath("//button[text()='Schedule']").click()
            time.sleep(2)

            log.info("Clicking on \"OK\" button")
            driver.find_element_by_xpath("//button[text()='OK']").click()

            log.info("Wait for 15 Seconds")
            time.sleep(15)

            log.info("Click on Refresh button")
            driver.find_element_by_xpath(
                "//div[@id='fwSubnetListPagingToolbar']//table[@class='x-toolbar-ct']//td[@class='x-toolbar-right']"
                "//table[@class='x-toolbar-right-ct']//tr[@class='x-toolbar-right-row']//td//em/button[@type='button']").click()
            time.sleep(2)
            log.info("Wait for 5 Seconds")

            log.info("Click on Refresh button")
            driver.find_element_by_xpath(
                "//div[@id='fwSubnetListPagingToolbar']//table[@class='x-toolbar-ct']//td[@class='x-toolbar-right']"
                "//table[@class='x-toolbar-right-ct']//tr[@class='x-toolbar-right-row']//td//em/button[@type='button']").click()

            log.info("Wait for 2 Seconds")
            time.sleep(2)

            log.info("Verify Push stack mode time in \'%s\' group" % cus_fw_groupname)
            # temp = Push_And_Verify_The_StackMode(driver, cgmesh_pan_id, stktm_typ_exp, pshstack_tme_msg_exp, stack_node_cnt1, config_dt_tm)
            temp = Push_And_Verify_The_StackMode(driver, cgmesh_pan_id, stktm_typ_exp, pshstack_tme_msg_exp, stack_node_cnt1)
            if temp:
                log.info("Overall Scheduled Stack mode time is Successfull in \'%s\'" % cus_fw_groupname)
            else:
                self.failed(banner("Overall Scheduled Stack mode time Failed in \'%s\'" % cus_fw_groupname))
            time.sleep(2)

            log.info('Navigate to Logs tab in the right plane')
            driver.find_element_by_xpath("//li[@id='fwTabs__logTab']//span[text()='Logs']").click()
            time.sleep(4)

            log.info("Click on Refresh button")
            driver.find_element_by_xpath(
                "//div[@id='logPageTB']//td[@class='x-toolbar-right']//tr[@class='x-toolbar-right-row']//table[@class='x-btn x-btn-icon']//button[@type='button']").click()
            time.sleep(1)

            log.info("Verify the Push stack time log message")
            message_list = [element.text for element in driver.find_elements_by_xpath(
                "//div[@id='firmwareMeshLog']//div[@class='x-grid3-body']//div//td[2]//div[contains(text(),'" + dt1 + "')]/../..//td[6]/div")]

            log.info('Event Message: %s' % message_list)
            if log_msg_skttm not in message_list:
                raise Exception('Did not see \'%s\' Error in Event message' % log_msg_skttm)
            else:
                log.info("Verified: \'%s\' Error found in Event message" % log_msg_skttm)

            log.info('Clicking on \'%s\' group' % def_fw_groupname)
            driver.find_element_by_xpath(
                "//div[@id='leftHandTree']//span[contains(text(),'" + def_fw_groupname + "')]").click()
            time.sleep(2)
            driver_utils.ignore_flash_error()

            log.info('Navigate to Firmware Management tab in the right plane')
            driver.find_element_by_xpath("//li[@id='fwTabs__mgmtTab']//span[text()='Firmware Management']").click()
            time.sleep(1)   

            log.info("Click on Refresh button")
            driver.find_element_by_xpath(
                "//div[@id='fwSubnetListPagingToolbar']//table[@class='x-toolbar-ct']//td[@class='x-toolbar-right']"
                "//table[@class='x-toolbar-right-ct']//tr[@class='x-toolbar-right-row']//td//em/button[@type='button']").click()

            log.info("Wait for 2 Seconds")
            time.sleep(2)

            log.info("Verify Push stack mode time in \'%s\' group" % def_fw_groupname)
            temp = Push_And_Verify_The_StackMode_In_Custom_Group(driver, cgmesh_pan_id, stktm_typ_exp, pshstack_tme_msg_exp,
                                                 stack_node_cnt1)
            if temp:
                log.info("Overall Scheduled Stack mode time is Successfull in \'%s\'" % def_fw_groupname)
            else:
                self.failed(banner("Overall Scheduled Stack mode time Failed in \'%s\'" % def_fw_groupname))

            log.info("Wait for 5 Seconds")
            time.sleep(5)

            log.info(banner('Getting the latest AuditTrails'))
            audit_trail = ui_common_utils.AuditTrail(driver)
            audittrails = audit_trail.get_latest_audittrails()
            operation = audittrails['operations']

            log.info('operation: %s' % operation)
            if 'Scheduled Stack Switch Time' not in operation: raise Exception('Did not see the "Scheduled Stack Switch Time" Audit Trail')
            else: log.info("Scheduled Stack Switch Time found in Audit trials")

        except Exception as ex:
            self.failed(ex)
            driver_utils.save_screenshot(scriptname='Tc16_Validate_Overall_Stack_Time_Push_From_Custom_Group',
                                         classname=__class__.__name__)

        finally:
            fw_up.nav_sub_menu('firmware_update')
            time.sleep(2)
            driver_utils.ignore_flash_error()
            time.sleep(1)
            log.info('Delete the firmware group - %s' % (cus_fw_groupname))
            fw_up.change_firmware_group(cus_fw_groupname, 'default-ir500', ir510_eids, type='endpoint')
            time.sleep(2)
            fw_up.delete_group('endpoint', cus_fw_groupname)
            time.sleep(2)
            try:
                error_logs = test_utils.read_remote_logs(remote_ssh_client=nms_ssh_client,
                                                         log_file=log_file,
                                                         read_error_logs=True, line_number=last_line_number)
                assert error_logs == []
                log.info('No ERROR logs found on FND.')
            except AssertionError as ae:
                driver_utils.save_screenshot(scriptname='Tc16_Validate_Overall_Stack_Time_Push_From_Custom_Group',
                                             classname=__class__.__name__)
                log.error('Should not see ERROR logs on FND.\nerror_logs: %s' % error_logs)  


# Testcase 17
class Tc17_Validate_Overall_Stackmode_Time_Cancel_From_Custom_Group(aetest.Testcase):
    @aetest.test
    def Tc17_Validate_Overall_Stackmode_Time_Cancel_From_Custom_Group(self, driver, ir510_eids, cus_fw_groupname, def_fw_groupname,
                                                   cgmesh_pan_id, cncl_exp_str, cancel_exp_str, stack_node_cnt1, cncl_stkmd_typ_exp,
                                                   cancel_msg_exp, log_msg_cncl):
        try:
            global driver_utils
            global auto_user_ws
            import datetime

            last_line_number = \
                test_utils.read_remote_logs(remote_ssh_client=nms_ssh_client, log_file=log_file,
                                            get_last_line=True)[0].rstrip()

            driver_utils.navigate_to_home()
            fw_up = ui_common_utils.FirmwareUpdate(driver)
            fw_up.nav_sub_menu('firmware_update')
            time.sleep(2)
            driver_utils.ignore_flash_error()

            time.sleep(1)
            log.info('Add new firmware group - %s'% cus_fw_groupname)
            fw_up.add_group('endpoint', cus_fw_groupname)
            time.sleep(2)
            log.info('Move %s Nodes to %s group from \'default-cgmesh\' group' % (ir510_eids, cus_fw_groupname))
            fw_up.change_firmware_group('default-ir500', cus_fw_groupname, ir510_eids, type='endpoint')
            time.sleep(3)

            log.info('Clicking on \'%s\' group' % cus_fw_groupname)
            driver.find_element_by_xpath(
                "//div[@id='leftHandTree']//span[contains(text(),'" + cus_fw_groupname + "')]").click()
            time.sleep(2)
            driver_utils.ignore_flash_error()

            log.info('Navigate to Firmware Management tab in the right plane')
            driver.find_element_by_xpath(
                "//li[@id='fwTabs__mgmtTab']//span[text()='Firmware Management']").click()
            time.sleep(1)

            log.info("Clicking on \"Clear Filter\" button")
            driver.find_element_by_xpath(
                "//div[@id='fwSubnetListPagingToolbar']/table[@class='x-toolbar-ct']//td[@class='x-toolbar-left']/table//tr[@class='x-toolbar-left-row']/td[1]/table//button[@type='button']").click()
            time.sleep(2)

            log.info("Select the PAN ID: %d" % cgmesh_pan_id)
            driver.find_element_by_xpath(
                "//div[@id='fwSubnetgrid']//div[@class='x-grid3-body']//table[@class='x-grid3-row-table']//div[@class='x-grid3-cell-inner x-grid3-col-panId' and contains(text(),\'%d\')]//parent::td//preceding-sibling::td//div[@class='x-grid3-cell-inner x-grid3-col-checker']" % cgmesh_pan_id).click()
            time.sleep(2)

            log.info("Clicking on \"Cancel StackMode\" button")
            driver.find_element_by_xpath(
                "//table[@id='cancelStackPush']//em/button[@type='button']").click()
            time.sleep(2)

            log.info("Verify the Cancel switching pop-up message")
            cn_str = driver.find_element_by_xpath(
                "//div[@class='x-window-bwrap']//div[@class='x-window-body']//span[@class='ext-mb-text']").text
            if cncl_exp_str in str(cn_str): log.info("Verified: \"%s\"" % cn_str)
            else:
                self.failed(banner("Pop-up message Verification failed - \'%s\'\nExpected: \'%s\'") % (
                cn_str, cncl_exp_str))
            time.sleep(1)

            log.info("Clicking on \"yes\" button")
            driver.find_element_by_xpath("//button[text()='Yes']").click()
            time.sleep(2)

            log.info("Verify Cancel stack mode pop-up message")
            cancel_str = driver.find_element_by_xpath(
                "//div[@class='x-window-bwrap']//div[@class='x-window-body']//span[@class='ext-mb-text']").text
            if cancel_exp_str in str(cancel_str):
                log.info("Verified: \"%s\"" % cancel_str)
            else:
                self.failed(banner("Pop-up message Verification failed - \'%s\'\nExpected: \'%s\'") % (
                cancel_str, cancel_exp_str))

            dte = datetime.datetime.utcnow().strftime('%Y-%m-%d')

            log.info("Clicking on \"OK\" button")
            driver.find_element_by_xpath("//button[text()='OK']").click()
            time.sleep(2)

            log.info("Click on Refresh button")
            driver.find_element_by_xpath(
                "//div[@id='fwSubnetListPagingToolbar']//table[@class='x-toolbar-ct']//td[@class='x-toolbar-right']"
                "//table[@class='x-toolbar-right-ct']//tr[@class='x-toolbar-right-row']//td//em/button[@type='button']").click()
            time.sleep(1)

            log.info("Verify Push stack mode time in \'%s\' group" % cus_fw_groupname)
            temp = Push_And_Verify_The_StackMode(driver, cgmesh_pan_id, cncl_stkmd_typ_exp, cancel_msg_exp, stack_node_cnt1)
            if temp: log.info("Overall Scheduled Stack mode time is Successfull in \'%s\'" % cus_fw_groupname)
            else: self.failed(banner("Overall Scheduled Stack mode time Failed in \'%s\'" % cus_fw_groupname))
            time.sleep(2)

            log.info('Navigate to Logs tab in the right plane')
            driver.find_element_by_xpath("//li[@id='fwTabs__logTab']//span[text()='Logs']").click()
            time.sleep(4)

            log.info("Click on Refresh button")
            driver.find_element_by_xpath("//div[@id='logPageTB']//td[@class='x-toolbar-right']//tr[@class='x-toolbar-right-row']//table[@class='x-btn x-btn-icon']//button[@type='button']").click()
            time.sleep(1)

            log.info("Verify the Cancel stack mode and time log message")
            message_list = [element.text for element in driver.find_elements_by_xpath(
                "//div[@id='firmwareMeshLog']//div[@class='x-grid3-body']//div//td[2]//div[contains(text(),'" + dte + "')]/../..//td[6]/div")]

            log.info('Event Message: %s' % message_list)
            if log_msg_cncl not in message_list: raise Exception('Did not see \'%s\' Error in Event message' % log_msg_cncl)
            else: log.info("Verified: \'%s\' Error found in Event message"% log_msg_cncl)

            log.info('Clicking on \'%s\' group' % def_fw_groupname)
            driver.find_element_by_xpath(
                "//div[@id='leftHandTree']//span[contains(text(),'" + def_fw_groupname + "')]").click()
            time.sleep(2)
            driver_utils.ignore_flash_error()

            log.info('Navigate to Firmware Management tab in the right plane')
            driver.find_element_by_xpath("//li[@id='fwTabs__mgmtTab']//span[text()='Firmware Management']").click()
            time.sleep(1)

            log.info("Click on Refresh button")
            driver.find_element_by_xpath(
                "//div[@id='fwSubnetListPagingToolbar']//table[@class='x-toolbar-ct']//td[@class='x-toolbar-right']"
                "//table[@class='x-toolbar-right-ct']//tr[@class='x-toolbar-right-row']//td//em/button[@type='button']").click()

            log.info("Wait for 2 Seconds")
            time.sleep(2)

            log.info("Verify Push stack mode time in \'%s\' group" % def_fw_groupname)
            temp = Push_And_Verify_The_StackMode_In_Custom_Group(driver, cgmesh_pan_id, cncl_stkmd_typ_exp, cancel_msg_exp, stack_node_cnt1)
            if temp: log.info("Overall Scheduled Stack mode time is Successfull in \'%s\'" % def_fw_groupname)
            else: self.failed(banner("Overall Scheduled Stack mode time Failed in \'%s\'" % def_fw_groupname))

            log.info("Wait for 5 Seconds")
            time.sleep(5)

            log.info(banner('Getting the latest AuditTrails'))
            audit_trail = ui_common_utils.AuditTrail(driver)
            audittrails = audit_trail.get_latest_audittrails()
            operation = audittrails['operations']

            log.info('operation: %s' % operation)
            if 'Cancel Stack' not in operation: raise Exception('Did not see the "Cancel stack" Audit Trail')
            else: log.info("Cancel stack found in Audit trials")

        except Exception as ex:
            self.failed(ex)
            driver_utils.save_screenshot(scriptname='Tc17_Validate_Overall_Stackmode_Time_Cancel_From_Custom_Group',
                                         classname=__class__.__name__)
        finally:
            fw_up.nav_sub_menu('firmware_update')
            time.sleep(2)
            driver_utils.ignore_flash_error()
            time.sleep(1)
            log.info('Delete the firmware group - %s' % (cus_fw_groupname))
            fw_up.change_firmware_group(cus_fw_groupname, 'default-ir500', ir510_eids, type='endpoint')
            time.sleep(2)
            fw_up.delete_group('endpoint', cus_fw_groupname)
            time.sleep(2)
            try:
                error_logs = test_utils.read_remote_logs(remote_ssh_client=nms_ssh_client,
                                                         log_file=log_file,
                                                         read_error_logs=True, line_number=last_line_number)
                assert error_logs == []
                log.info('No ERROR logs found on FND.')
            except AssertionError as ae:
                driver_utils.save_screenshot(scriptname='Tc17_Validate_Overall_Stackmode_Time_Cancel_From_Custom_Group',
                                             classname=__class__.__name__)
                log.error('Should not see ERROR logs on FND.\nerror_logs: %s' % error_logs)

# Testcase 18
class Tc18_Validate_Scheduling_Past_stacktime(aetest.Testcase):
    @aetest.test
    def Tc18_Validate_Scheduling_Past_stacktime(self, driver, cgmesh_pan_id, stackmd_exp_str):
        try:
            global driver_utils
            global auto_user_ws
            import datetime
            fw_groupname = "default-ir500"
            past_time_exp_str = "requested for group %s is in the past." % fw_groupname
            tm = "00:00"

            last_line_number = \
                test_utils.read_remote_logs(remote_ssh_client=nms_ssh_client, log_file=log_file, get_last_line=True)[
                    0].rstrip()

            driver_utils.navigate_to_home()
            fw_up = ui_common_utils.FirmwareUpdate(driver)
            fw_up.nav_sub_menu('firmware_update')
            time.sleep(2)
            driver_utils.ignore_flash_error()

            driver.find_element_by_xpath(
                "//div[@id='leftHandTree']//span[contains(text(),'" + fw_groupname + "')]").click()
            time.sleep(2)
            driver_utils.ignore_flash_error()

            log.info('Navigate to Firmware Management tab in the right plane')
            driver.find_element_by_xpath("//li[@id='fwTabs__mgmtTab']//span[text()='Firmware Management']").click()
            time.sleep(1)

            log.info("Clicking on \"Clear Filter\" button")
            driver.find_element_by_xpath(
                "//div[@id='fwSubnetListPagingToolbar']/table[@class='x-toolbar-ct']//td[@class='x-toolbar-left']/table//tr[@class='x-toolbar-left-row']/td[1]/table//button[@type='button']").click()
            time.sleep(2)

            log.info("Select the PAN ID: %d" % cgmesh_pan_id)
            driver.find_element_by_xpath(
                "//div[@id='fwSubnetgrid']//div[@class='x-grid3-body']//table[@class='x-grid3-row-table']//div[@class='x-grid3-cell-inner x-grid3-col-panId' and contains(text(),\'%d\')]"
                "//parent::td//preceding-sibling::td//div[@class='x-grid3-cell-inner x-grid3-col-checker']" % cgmesh_pan_id).click()
            time.sleep(2)

            log.info("Clicking on \"Push StackMode Time\" button")
            driver.find_element_by_xpath("//table[@id='stackModeTimePush']//em/button[@type='button']").click()
            time.sleep(2)

            log.info("Verify Push stack mode time pop-up message")
            stackmd_str = driver.find_element_by_xpath(
                "//div[@class='x-window-bwrap']//div[@class='x-window-body']//span[@class='ext-mb-text']").text
            if stackmd_exp_str in str(stackmd_str):
                log.info("Verified: \"%s\"" % stackmd_str)
            else:
                self.failed(banner("Pop-up message Verification failed - \'%s\'\nExpected: \'%s\'") % (
                stackmd_str, stackmd_exp_str))
            time.sleep(1)

            log.info("Clicking on \"yes\" button")
            driver.find_element_by_xpath("//button[text()='Yes']").click()
            time.sleep(2)

            log.info("Entering the past time : %s" % tm)
            driver.find_element_by_xpath("//input[@id='stackDTFtime']").clear()
            driver.find_element_by_xpath("//input[@id='stackDTFtime']").send_keys(tm)
            driver.find_element_by_xpath("//input[@id='stackDTFdate']/../img").click()
            time.sleep(1)

            log.info("Clicking on \"Today\" button") 
            driver.find_element_by_xpath("//button[text()='Today']").click()
            time.sleep(2)

            dte = datetime.datetime.utcnow().strftime('%Y-%m-%d')

            log.info("Clicking on \"Schedule\" button") 
            driver.find_element_by_xpath("//button[text()='Schedule']").click()
            time.sleep(2)

            log.info("Verify if scheduling stack time is not allowed for past date/time")
            cgmesh_str = driver.find_element_by_xpath(
                "//div[@class='x-window-bwrap']//div[@class='x-window-body']//span[@class='ext-mb-text']").text
            if cgmesh_str.endswith(past_time_exp_str):
                log.info("Verified: \"%s\"" % cgmesh_str)
            else:
                self.failed(banner("Pop-up message Verification failed - \'%s\'\nExpected: \'%s\'") % (
                cgmesh_str, past_time_exp_str))

            log.info("Clicking on \"OK\" button")
            driver.find_element_by_xpath("//button[text()='OK']").click()
            time.sleep(2)

            log.info("Clicking on \"Close\" button")
            driver.find_element_by_xpath("//button[text()='Close']").click()
            time.sleep(2)

            log.info('Navigate to Logs tab in the right plane')
            driver.find_element_by_xpath("//li[@id='fwTabs__logTab']//span[text()='Logs']").click()
            time.sleep(4)

            log.info("Click on Refresh button")
            driver.find_element_by_xpath("//div[@id='logPageTB']//td[@class='x-toolbar-right']//tr[@class='x-toolbar-right-row']//table[@class='x-btn x-btn-icon']//button[@type='button']").click()
            time.sleep(1)  

            log.info("Verify the stackmode push past time log message")
            message_list = [element.text for element in driver.find_elements_by_xpath(
                "//div[@id='firmwareMeshLog']//div[@class='x-grid3-body']//div//td[2]//div[contains(text(),'" + dte + "')]/../..//td[6]/div")]

            log.info('Event Message: %s' % message_list)

        except Exception as ex:
            self.failed(ex)
            driver_utils.save_screenshot(scriptname='Tc18_Validate_Scheduling_Past_stacktime',
                                         classname=__class__.__name__)

            log.info("Clicking on \"OK\" button")
            driver.find_element_by_xpath("//button[text()='OK']").click()
            time.sleep(2)

            log.info("Clicking on \"Close\" button")
            driver.find_element_by_xpath("//button[text()='Close']").click()
            time.sleep(2)  

            try:
                error_logs = test_utils.read_remote_logs(remote_ssh_client=nms_ssh_client, log_file=log_file,
                                                         read_error_logs=True, line_number=last_line_number)
                assert error_logs == []
                log.info('No ERROR logs found on FND.')
            except AssertionError as ae:
                driver_utils.save_screenshot(scriptname='Tc18_Validate_Scheduling_Past_stacktime',
                                             classname=__class__.__name__)
                log.error('Should not see ERROR logs on FND.\nerror_logs: %s' % error_logs)

# Testcase 19
class Tc19_Validate_Push_Stackmode_Firmware_Version_Check(aetest.Testcase):
    @aetest.test
    def Tc19_Validate_Push_Stackmode_Firmware_Version_Check(self, driver, ver_chk_pan_id, stackmd_exp_str, pshstack_ver_chk, error_log_ver_chk):
        try:
            global driver_utils
            global auto_user_ws
            import datetime
            fw_groupname = "default-ir500"

            last_line_number = \
                test_utils.read_remote_logs(remote_ssh_client=nms_ssh_client, log_file=log_file, get_last_line=True)[
                    0].rstrip()

            driver_utils.navigate_to_home()
            fw_up = ui_common_utils.FirmwareUpdate(driver)
            fw_up.nav_sub_menu('firmware_update')
            time.sleep(2)
            driver_utils.ignore_flash_error()

            driver.find_element_by_xpath(
                "//div[@id='leftHandTree']//span[contains(text(),'" + fw_groupname + "')]").click()
            time.sleep(2)
            driver_utils.ignore_flash_error()

            log.info('Navigate to Firmware Management tab in the right plane')
            driver.find_element_by_xpath("//li[@id='fwTabs__mgmtTab']//span[text()='Firmware Management']").click()
            time.sleep(1)

            log.info("Clicking on \"Clear Filter\" button")
            driver.find_element_by_xpath("//div[@id='fwSubnetListPagingToolbar']/table[@class='x-toolbar-ct']//td[@class='x-toolbar-left']"
                                         "/table//tr[@class='x-toolbar-left-row']/td[1]/table//button[@type='button']").click()
            time.sleep(2)

            log.info("Select the PAN ID: %d" % ver_chk_pan_id)
            driver.find_element_by_xpath(
                "//div[@id='fwSubnetgrid']//div[@class='x-grid3-body']//table[@class='x-grid3-row-table']//div[@class='x-grid3-cell-inner x-grid3-col-panId' and contains(text(),\'%d\')]"
                "//parent::td//preceding-sibling::td//div[@class='x-grid3-cell-inner x-grid3-col-checker']" % ver_chk_pan_id).click()
            time.sleep(2)

            dte = datetime.datetime.utcnow().strftime('%Y-%m-%d')

            log.info("Clicking on \"Push StackMode\" button")
            driver.find_element_by_xpath("//table[@id='stackModePush']//em/button[@type='button']").click()
            time.sleep(2)

            log.info("Verify Push stack mode pop-up message")
            stackmd_str = driver.find_element_by_xpath(
                "//div[@class='x-window-bwrap']//div[@class='x-window-body']//span[@class='ext-mb-text']").text
            if stackmd_exp_str in str(stackmd_str):
                log.info("Verified: \"%s\"" % stackmd_str)
            else:
                self.failed(banner("Pop-up message Verification failed - \'%s\'\nExpected: \'%s\'") % (
                stackmd_str, stackmd_exp_str))
            time.sleep(1)

            log.info("Clicking on \"yes\" button")
            driver.find_element_by_xpath("//button[text()='Yes']").click()
            time.sleep(2)

            log.info("Verify the base version for switch-to-wisun pop-up message")
            wisun_str1 = driver.find_element_by_xpath(
                "//div[@class='x-window-bwrap']//div[@class='x-window-body']//span[@class='ext-mb-text']").text
            if pshstack_ver_chk in str(wisun_str1):
                log.info("Verified: \"%s\"" % wisun_str1)
            else:
                self.failed(banner("Pop-up message Verification failed - \'%s\'\nExpected: \'%s\'") % (
                wisun_str1, pshstack_ver_chk))

            log.info("Clicking on \'OK\' button")
            driver.find_element_by_xpath("//button[text()='OK']").click()
            time.sleep(2)

            log.info('Navigate to Logs tab in the right plane')
            driver.find_element_by_xpath("//li[@id='fwTabs__logTab']//span[text()='Logs']").click()
            time.sleep(4)

            log.info("Click on Refresh button")
            driver.find_element_by_xpath(
                "//div[@id='logPageTB']//td[@class='x-toolbar-right']//tr[@class='x-toolbar-right-row']//table[@class='x-btn x-btn-icon']//button[@type='button']").click()
            time.sleep(1)

            log.info("Verify stackmode push when combination of wisun and non-wisun in a pan id log message")
            message_list = [element.text for element in driver.find_elements_by_xpath(
                "//div[@id='firmwareMeshLog']//div[@class='x-grid3-body']//div//td[2]//div[contains(text(),'" + dte + "')]/../..//td[6]/div")]

            log.info('Event Message: %s' % message_list)
            if error_log_ver_chk not in message_list:
                raise Exception('Did not see \'%s\' Error in Event message' % error_log_ver_chk)
            else:
                log.info("Verified: \'%s\' Error found in Event message" % error_log_ver_chk)

        except Exception as ex:
            self.failed(ex)
            driver_utils.save_screenshot(scriptname='Tc19_Validate_Push_Stackmode_Firmware_Version_Check', classname=__class__.__name__)

            log.info("Clicking on \'OK\' button")
            driver.find_element_by_xpath("//button[text()='OK']").click()
            time.sleep(2)

            try:
                error_logs = test_utils.read_remote_logs(remote_ssh_client=nms_ssh_client, log_file=log_file,
                                                         read_error_logs=True, line_number=last_line_number)
                assert error_logs == []
                log.info('No ERROR logs found on FND.')
            except AssertionError as ae:
                driver_utils.save_screenshot(scriptname='Tc19_Validate_Push_Stackmode_Firmware_Version_Check', classname=__class__.__name__)
                log.error('Should not see ERROR logs on FND.\nerror_logs: %s' % error_logs)


#Testcase 20
class Tc20_Validate_Schedule_Reload_And_Switch_stack_time_At_The_Same_Time(aetest.Testcase):
    @aetest.test
    def Tc20_Validate_Schedule_Reload_And_Switch_stack_time_At_The_Same_Time(self, driver, cgmesh_pan_id, stackmd_exp_str,
                                                                             stackmd_cfm_exp_str, stackmd_typ_exp, pshstack_msg_exp,
                                                                             stack_node_cnt, stktm_typ_exp, pshstack_tme_msg_exp, ir510_eids, mesh_image_path,
                                                                             ir510_firmware_image, ir510_fw_img_sch_tble, same_dt_tm_exp_str):
        try:
            global driver_utils
            global auto_user_ws

            def_fw_groupname = 'default-ir500'

            last_line_number = \
                test_utils.read_remote_logs(remote_ssh_client=nms_ssh_client, log_file=log_file, get_last_line=True)[
                    0].rstrip()
            driver_utils.navigate_to_home()

            log.info('Navigate to Firmware update')
            fw_up = ui_common_utils.FirmwareUpdate(driver)
            fw_up.nav_sub_menu('firmware_update')
            time.sleep(2)
            driver_utils.ignore_flash_error()
            time.sleep(1)

            #################################################################################################### 
            log.info("Upload image to \'%s\' Nodes in \'%s\' group" % (ir510_eids, def_fw_groupname))
            upload_stats = Upload_image_To_Mesh_nodes(driver, def_fw_groupname, mesh_image_path, ir510_firmware_image, ir510_fw_img_sch_tble)
            if upload_stats: log.info("Upload image to \'%s\' Nodes in \'%s\' group is success" % (ir510_eids, def_fw_groupname))
            else: self.failed(banner("Upload image to \'%s\' Nodes in \'%s\' group failed" % (ir510_eids, def_fw_groupname)))
            time.sleep(1)
            #################################################################################################### 

            log.info('Navigate to Firmware update')  
            fw_up.nav_sub_menu('firmware_update')
            time.sleep(2)
            driver_utils.ignore_flash_error()   

            log.info("Current Date : " + datetime.datetime.utcnow().strftime('%Y-%m-%d'))
            log.info("Current Time : " + datetime.datetime.utcnow().strftime("%H:%M"))
            dt = datetime.datetime.utcnow().strftime('%Y-%m-%d')
            t1 = datetime.datetime.utcnow() + datetime.timedelta(minutes=100)
            sch_time = str(t1.strftime("%H:%M"))
            log.info("Incremented Time : " + sch_time)
            sec_tm = sch_time + ":00.0"
            config_dt_tm = dt + " " + sec_tm

            ####################################################################################################
            log.info("Initiate scheduled reload for \'%s\' in \'%s\'" % (ir510_eids, def_fw_groupname))
            schrd_stats = Schedule_Reload_To_Mesh_Nodes(driver, def_fw_groupname, ir510_fw_img_sch_tble, sch_time)
            if schrd_stats: log.info("Scheduled reload is successfull for \'%s\' in \'%s\' group" % (ir510_eids, def_fw_groupname))
            else: self.failed(banner("Scheduled reload failed for \'%s\' in \'%s\' group" % (ir510_eids, def_fw_groupname))) 
            #################################################################################################### 

            log.info("Clicking on \"Clear Filter\" button")
            driver.find_element_by_xpath(
                "//div[@id='fwSubnetListPagingToolbar']/table[@class='x-toolbar-ct']//td[@class='x-toolbar-left']/table//tr[@class='x-toolbar-left-row']/td[1]/table//button[@type='button']").click()
            time.sleep(2)

            log.info("Select the PAN ID: %d" % cgmesh_pan_id)
            driver.find_element_by_xpath(
                "//div[@id='fwSubnetgrid']//div[@class='x-grid3-body']//table[@class='x-grid3-row-table']//div[@class='x-grid3-cell-inner x-grid3-col-panId' and contains(text(),\'%d\')]"
                "//parent::td//preceding-sibling::td//div[@class='x-grid3-cell-inner x-grid3-col-checker']" % cgmesh_pan_id).click()
            time.sleep(2)

            log.info("Clicking on \"Push StackMode\" button")
            driver.find_element_by_xpath("//table[@id='stackModePush']//em/button[@type='button']").click()
            time.sleep(2)

            log.info("Verify the Push stack mode pop-up message")
            stackmd_str = driver.find_element_by_xpath(
                "//div[@class='x-window-bwrap']//div[@class='x-window-body']//span[@class='ext-mb-text']").text
            if stackmd_exp_str in str(stackmd_str):
                log.info("Verified: \"%s\"" % stackmd_str)
            else:
                self.failed(banner("Pop-up message Verification failed - \'%s\'\nExpected: \'%s\'") % (
                    stackmd_str, stackmd_exp_str))
            time.sleep(1)

            log.info("Clicking on \"yes\" button")
            driver.find_element_by_xpath("//button[text()='Yes']").click()
            time.sleep(2)

            log.info("Verify conformation pop-up message")
            stackmd_cfm_str = driver.find_element_by_xpath(
                "//div[@class='x-window-bwrap']//div[@class='x-window-body']//span[@class='ext-mb-text']").text
            if stackmd_cfm_exp_str in str(stackmd_cfm_str):
                log.info("Verified: \"%s\"" % stackmd_cfm_str)
            else:
                self.failed(banner("Pop-up message Verification failed - \'%s\'\nExpected: \'%s\'") % (
                    stackmd_cfm_str, stackmd_cfm_exp_str))
            time.sleep(1)

            log.info("Clicking on \"OK\" button")
            driver.find_element_by_xpath("//button[text()='OK']").click()

            log.info("Wait for 15 Seconds")
            time.sleep(15)

            log.info("Click on Refresh button")
            driver.find_element_by_xpath(
                "//div[@id='fwSubnetListPagingToolbar']//table[@class='x-toolbar-ct']//td[@class='x-toolbar-right']"
                "//table[@class='x-toolbar-right-ct']//tr[@class='x-toolbar-right-row']//td//em/button[@type='button']").click()
            time.sleep(5)
            log.info("Wait for 5 Seconds")

            #################################################################################################### 
            temp = Push_And_Verify_The_StackMode(driver, cgmesh_pan_id, stackmd_typ_exp, pshstack_msg_exp, stack_node_cnt)
            if temp:
                log.info("Overall stack mode push verified successfully")
            else:
                log.info("Overall stack mode push Failed")
            time.sleep(2)
            #################################################################################################### 

            log.info("Clicking on \"Push StackMode Time\" button")
            driver.find_element_by_xpath("//table[@id='stackModeTimePush']//em/button[@type='button']").click()
            time.sleep(2)

            log.info("Verify Push stack mode time pop-up message")
            stackmd_str = driver.find_element_by_xpath(
                "//div[@class='x-window-bwrap']//div[@class='x-window-body']//span[@class='ext-mb-text']").text
            if stackmd_exp_str in str(stackmd_str):
                log.info("Verified: \"%s\"" % stackmd_str)
            else:
                self.failed(banner("Pop-up message Verification failed - \'%s\'\nExpected: \'%s\'") % (
                    stackmd_str, stackmd_exp_str))
            time.sleep(1)

            log.info("Clicking on \"yes\" button")
            driver.find_element_by_xpath("//button[text()='Yes']").click()
            time.sleep(2)

            log.info("Entering the stack-switch-time same as scheduled reload time : %s" % sch_time)
            driver.find_element_by_xpath("//input[@id='stackDTFtime']").clear()
            driver.find_element_by_xpath("//input[@id='stackDTFtime']").send_keys(sch_time)
            time.sleep(1)

            #driver.find_element_by_xpath("//input[@id='stackDTFdate']/../img").click()
            #time.sleep(2)
            #log.info("Clicking on \"Today\" button")
            #driver.find_element_by_xpath("//button[text()='Today']").click()
            #time.sleep(2)

            log.info("Clicking on \"Schedule\" button")
            driver.find_element_by_xpath("//button[text()='Schedule']").click()
            time.sleep(2)

            ####################################################################################################
            log.info("Verify if stack-switch-time and scheduled reload time is not allowed at the same time")
            cgmesh_str = driver.find_element_by_xpath(
                "//div[@class='x-window-bwrap']//div[@class='x-window-body']//span[@class='ext-mb-text']").text
            if cgmesh_str.startswith(same_dt_tm_exp_str):
                log.info("Verified: \"%s\"" % cgmesh_str)
            else:
                log.info("Stackmode time pop-up message verification failed - \'%s\' Expected: \'%s\'" % (
                    cgmesh_str, same_dt_tm_exp_str))    
            ####################################################################################################

        except Exception as ex:
            self.failed(ex)
            driver_utils.save_screenshot(scriptname='Tc20_Validate_Schedule_Reload_And_Switch_stack_time_At_The_Same_Time',
                                         classname=__class__.__name__)
            log.error(e)

        finally:

            log.info("Clicking on \"OK\" button")
            driver.find_element_by_xpath("//button[text()='OK']").click()

            log.info("Clicking on \"Close\" button")
            driver.find_element_by_xpath("//button[text()='Close']").click()
            time.sleep(2)  

            try:
                error_logs = test_utils.read_remote_logs(remote_ssh_client=nms_ssh_client,
                                                         log_file=log_file,
                                                         read_error_logs=True, line_number=last_line_number)
                assert error_logs == []
                log.info('No ERROR logs found on FND.')
            except AssertionError as ae:
                driver_utils.save_screenshot(scriptname='Tc20_Validate_Schedule_Reload_And_Switch_stack_time_At_The_Same_Time',
                                             classname=__class__.__name__)
                log.error('Should not see ERROR logs on FND.\nerror_logs: %s' % error_logs)

#Testcase 21
class Tc21_Validate_Cancel_Reload_Stackmode(aetest.Testcase):
    @aetest.test
    def Tc21_Validate_Cancel_Reload__Stackmode(self, driver, ir510_eids, cgmesh_pan_id, cncl_exp_str, cancel_exp_str, stack_node_cnt, cncl_stkmd_typ_exp, cancel_msg_exp, log_msg_cncl):
        try:
            global driver_utils
            global auto_user_ws
            import datetime
            fw_groupname = 'default-ir500' 

            last_line_number = \
                test_utils.read_remote_logs(remote_ssh_client=nms_ssh_client, log_file=log_file, get_last_line=True)[
                    0].rstrip()

            driver_utils.navigate_to_home()
            fw_up = ui_common_utils.FirmwareUpdate(driver)
            fw_up.nav_sub_menu('firmware_update')
            time.sleep(2)
            driver_utils.ignore_flash_error()

            driver.find_element_by_xpath(
                "//div[@id='leftHandTree']//span[contains(text(),'" + fw_groupname + "')]").click()
            time.sleep(2)
            driver_utils.ignore_flash_error()

            log.info('Navigate to Firmware Management tab in the right plane')
            driver.find_element_by_xpath("//li[@id='fwTabs__mgmtTab']//span[text()='Firmware Management']").click()
            time.sleep(1)

            log.info("Initiate cancel reload for \'%s\' in \'%s\'" % (ir510_eids, fw_groupname))
            cncl_sch_stats = Cancel_Scheduled_Reload(driver, fw_groupname)
            if cncl_sch_stats:
                log.info("Cancel reload is successfull for \'%s\' in \'%s\' group" % (ir510_eids, fw_groupname))
            else:
                self.failed(banner("Cancel reload failed for \'%s\' in \'%s\' group" % (ir510_eids, fw_groupname)))

            log.info("Clicking on \"Clear Filter\" button")
            driver.find_element_by_xpath("//div[@id='fwSubnetListPagingToolbar']/table[@class='x-toolbar-ct']//td[@class='x-toolbar-left']/table//tr[@class='x-toolbar-left-row']/td[1]/table//button[@type='button']").click()
            time.sleep(2)

            log.info("Select the PAN ID: %d" % cgmesh_pan_id)
            driver.find_element_by_xpath("//div[@id='fwSubnetgrid']//div[@class='x-grid3-body']//table[@class='x-grid3-row-table']//div[@class='x-grid3-cell-inner x-grid3-col-panId' and contains(text(),\'%d\')]//parent::td//preceding-sibling::td//div[@class='x-grid3-cell-inner x-grid3-col-checker']" % cgmesh_pan_id).click()
            time.sleep(2)

            log.info("Clicking on \"Cancel StackMode\" button")
            driver.find_element_by_xpath("//table[@id='cancelStackPush']//em/button[@type='button']").click()
            time.sleep(2)

            log.info("Verify the Cancel switching pop-up message")
            cn_str = driver.find_element_by_xpath(
                "//div[@class='x-window-bwrap']//div[@class='x-window-body']//span[@class='ext-mb-text']").text
            if cncl_exp_str in str(cn_str):
                log.info("Verified: \"%s\"" % cn_str)
            else:
                self.failed(
                    banner("Pop-up message Verification failed - \'%s\'\nExpected: \'%s\'") % (cn_str, cncl_exp_str))
            time.sleep(1)

            log.info("Clicking on \"yes\" button")
            driver.find_element_by_xpath("//button[text()='Yes']").click()
            time.sleep(2)

            log.info("Verify Cancel stack mode pop-up message")
            cancel_str = driver.find_element_by_xpath(
                "//div[@class='x-window-bwrap']//div[@class='x-window-body']//span[@class='ext-mb-text']").text
            if cancel_exp_str in str(cancel_str):
                log.info("Verified: \"%s\"" % cancel_str)
            else:
                self.failed(
                    banner("Pop-up message Verification failed - \'%s\'\nExpected: \'%s\'") % (cancel_str, cancel_exp_str))

            dte = datetime.datetime.utcnow().strftime('%Y-%m-%d')

            log.info("Clicking on \"OK\" button")
            driver.find_element_by_xpath("//button[text()='OK']").click()
            time.sleep(2)

            log.info("Wait for 15 Seconds")
            time.sleep(15)
            log.info("Click on Refresh button")
            driver.find_element_by_xpath(
                "//div[@id='fwSubnetListPagingToolbar']//table[@class='x-toolbar-ct']//td[@class='x-toolbar-right']"
                "//table[@class='x-toolbar-right-ct']//tr[@class='x-toolbar-right-row']//td//em/button[@type='button']").click()

            log.info("Wait for 5 Seconds")
            time.sleep(5)

            temp = Push_And_Verify_The_StackMode(driver, cgmesh_pan_id, cncl_stkmd_typ_exp, cancel_msg_exp, stack_node_cnt)
            if temp:
                log.info("Overall stack mode cancel verified successfully")
            else:
                self.failed(banner("Overall stack mode cancel Failed"))

            log.info("Wait for 5 Seconds")
            time.sleep(5)

            log.info('Navigate to Logs tab in the right plane')
            driver.find_element_by_xpath("//li[@id='fwTabs__logTab']//span[text()='Logs']").click()
            time.sleep(4)

            log.info("Click on Refresh button")
            driver.find_element_by_xpath(
                "//div[@id='logPageTB']//td[@class='x-toolbar-right']//tr[@class='x-toolbar-right-row']//table[@class='x-btn x-btn-icon']//button[@type='button']").click()
            time.sleep(1)

            log.info("Verify the Cancel stack log message")
            message_list = [element.text for element in driver.find_elements_by_xpath(
                "//div[@id='firmwareMeshLog']//div[@class='x-grid3-body']//div//td[2]//div[contains(text(),'" + dte + "')]/../..//td[6]/div")]

            log.info('Event Message: %s' % message_list)
            if log_msg_cncl not in message_list: raise Exception('Did not see \'%s\' Error in Event message' % log_msg_cncl)
            else: log.info("Verified: \'%s\' Error found in Event message"% log_msg_cncl)

            log.info(banner('Getting the latest AuditTrails'))
            audit_trail = ui_common_utils.AuditTrail(driver)
            audittrails = audit_trail.get_latest_audittrails()
            operation = audittrails['operations']

            log.info('operation: %s' % operation)
            if 'Cancel Stack' not in operation: raise Exception('Did not see the "Cancel stack" Audit Trail')
            else: log.info("Cancel stack found in Audit trials")

        except Exception as ex:
            self.failed(ex)
            driver_utils.save_screenshot(scriptname='Tc21_Validate_Cancel_Reload__Stackmode', classname=__class__.__name__)

            try:
                error_logs = test_utils.read_remote_logs(remote_ssh_client=nms_ssh_client, log_file=log_file,
                                                         read_error_logs=True, line_number=last_line_number)
                assert error_logs == []
                log.info('No ERROR logs found on FND.')
            except AssertionError as ae:
                driver_utils.save_screenshot(scriptname='Tc21_Validate_Cancel_Reload__Stackmode', classname=__class__.__name__)
                log.error('Should not see ERROR logs on FND.\nerror_logs: %s' % error_logs)

                log.error('Should not see ERROR logs on FND.\nerror_logs: %s' % error_logs)
'''


########################################################################
####                       COMMON CLEANUP SECTION                    ###
########################################################################

class CommonCleanup(aetest.CommonCleanup):
    ######################################################################
    #                                                                    #
    # This section disconnects from devices in the testbed and cleans up #
    #                                                                    #
    ######################################################################

    @aetest.subsection
    def tearDown(self, driver):

        try:
            log.info(banner('Quitting webdriver.'))
            time.sleep(1)
            driver_utils.logout()
            driver.quit()
            log.info('Closing NMS ssh client.')
            nms_ssh_client.close()
        except Exception as ex:
            driver.quit()

    @aetest.subsection
    def disconnect_from_devices(self, nms_server):
        try:
            nms_server.disconnect()
            assert nms_server.is_connected() == False
        except AssertionError:
            self.failed('COULD NOT DISCONNECT FROM DEVICE')


if __name__ == '__main__':
    import argparse
    from ats import topology
    parser = argparse.ArgumentParser(description='standalone parser')
    parser.add_argument("--testbed", type = topology.loader.load)

    args, unknwon = parser.parse_known_args()
    aetest.main(**vars(args))
