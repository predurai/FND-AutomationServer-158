#!/bin/env python
###################################################################
# ui_common_utils.py : 
###################################################################

import os
import re
import csv
import sys
import time
import json
import glob
import collections

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import NoSuchElementException, ElementNotVisibleException, StaleElementReferenceException

import logging
from ats.log.utils import banner
log = logging.getLogger(__name__)
logging.getLogger().setLevel(logging.INFO)

class DriverUtils():
    ''' This class defines all the selenium webdriver related utilities. The generic functionalities of FND are defined here. '''

    def __init__(self, driver, *arg):
        self.arg = arg
        self.driver = driver

    def wait_for_loading(self, **kwargs):
        driver = self.driver
        
        timeout = time.time() + 60*2
        while timeout>time.time():
            self.ignore_flash_error()
            log.info('Waiting for page to be loaded..')
            loading_len = int(driver.execute_script('return $("div:contains(\'Loading..\')").length'))
            log.info("Loading value is ")
            wait_len = int(driver.execute_script('return $("div:contains(\'Please wait...\')").length'))
            log.info("Waiting value")
            if loading_len==0 and wait_len==0: break
            else:
                log.info('loading_len: %d, wait_len: %s'%(loading_len, wait_len))
                time.sleep(1)
            log.info("Wait over....")

    def switch_domain(self, current_domain, switch_domain):
        driver = self.driver

        is_switched = False
        log.info('click on "cisco-logged-user".')
        driver.find_element_by_xpath('//div[contains(@class, "cisco-logged-user")]').click()
        time.sleep(2)
        try:
            if driver.find_element_by_xpath('//a[text()="Switch Domain"]').is_displayed():
                log.info('Clicking on "Switch Domain" option.')
                driver.find_element_by_xpath('//a[text()="Switch Domain"]').click()
                time.sleep(1)

                log.info('Clicking on Domain names expander.')
                driver.find_element_by_xpath("//div[@id='switchDomainTree']//span[text()='root']/../../img").click()

                current_domain_elem = driver.find_element_by_xpath("//div[@id='switchDomainTree']//span[text()='%s']/../.." % current_domain)
                current_domain_class = current_domain_elem.get_attribute('class')

                if 'disabled' in current_domain_class:
                    log.info("Current logged in domain name '%s' is disabled!" % current_domain)
                    log.info('Clicking on %s'%switch_domain)
                    driver.find_element_by_xpath("//div[@id='switchDomainTree']//span[text()='%s']/../.." % switch_domain).click()
                    time.sleep(1)
                    log.info('Clicking on Exchange button.')
                    driver.find_element_by_xpath("//i[@class='fa fa-exchange']/..").click()
                    time.sleep(2)

                    driver.find_element_by_xpath("//button[text()='Yes']").click()
                    time.sleep(3)
                    self.ignore_flash_error()

                    log.info('Verifying domain name is switched.')
                    domain_after_switching = driver.find_element_by_xpath('//div[contains(@class, "display_domain_name")]').text
                    log.info('domain_after_switching: %s'%domain_after_switching)
                    assert switch_domain in domain_after_switching
                    log.info('Domain Switched to : %s' % switch_domain)
                    is_switched = True
                else:
                    time.sleep(1)
                    log.error("Current logged in domain name '%s' is enabled!" % current_domain)
                    driver.find_element_by_xpath("//i[@class='fa fa-close']/..").click()
            else:
                log.error("Switch_Domain option is disabled!")
        except AssertionError as ae: log.error('Domain not switched')
        except Exception as e: log.error(e)

        return is_switched

    def navigate_to_home(self):

        driver = self.driver
        self.ignore_flash_error()
        self.check_error_popup()
        log.info('Clicking on header_logo.')
        driver.find_element_by_id('header_logo').click()
        time.sleep(3)

        timeout = time.time() + 60*2
        while timeout>time.time():
            try:
                self.ignore_flash_error()
                breadcrumbs_span = driver.find_element_by_class_name('breadcrumbs-span')
                if breadcrumbs_span: break
                time.sleep(2)
            except Exception as e: log.error(e)
 
        self.wait_for_loading()
        if self.check_error_popup():pass

    def log_into_fnd(self, nms_ip, user_name, password):
        '''
        Helper function to log into FND portal.

        :param nms_ip: IP of the FND portal.
        :type nms_ip: str
        :param user_name: User name of the FND.
        :type user_name: str
        :param password: Password of the FND.
        :type password: str
        '''
        driver = self.driver
        login_screen = ''
        #Check if a window is at login screen.
        #The portal might timeout sometimes and logs out. We check for this case and login again.
        try:
            #If not visitng for first time, check for login screen.
            if driver.current_url != 'about:blank':
                driver.find_element_by_xpath('//label[contains(@class, "label-text") and contains(text(), "Username")]')
                login_screen = 'Log into FND'
        except NoSuchElementException as e: login_screen = 'Logged In'
        except Exception as e: log.error('Exception while trying to login: %s'%e)

        if login_screen == 'Logged In':
            log.info('FND is already logged in.')
            #Early return as we already have logged in FND webpage.
            return driver
        elif login_screen == 'Log into FND':
            log.info('First time login/Logged out, trying to login.')
        elif driver is None:
            log.info('No active session. Creating a new session and logging in.')
            driver = webdriver.Firefox()
            driver.implicitly_wait(10)
            driver.maximize_window()

        log.info('Open FND portal.')
        driver.get('https://' + nms_ip + "/home.seam")
        time.sleep(2)

        log.info('Enter Credentials.')
        driver.find_element_by_id("login:username").clear()
        driver.find_element_by_id("login:username").send_keys(user_name)
        time.sleep(1)
        driver.find_element_by_xpath('//input[@type="password"]').clear()
        driver.find_element_by_xpath('//input[@type="password"]').send_keys(password)
        time.sleep(1)

        log.info('Click on Login button.')
        driver.find_element_by_id("login:login").click()
        time.sleep(3)

        try:
            log.info('Accepting alert')
            alert = driver.switch_to.alert
            alert.accept()
        except Exception as e: log.info('No Alert present.')

        driver.execute_script('if($(\'span:contains("Information")\').length>0){ $(\'button:contains("OK")\').click() }')
        self.ignore_flash_error()
        #Check if login is succesfull.
        return driver

    def first_time_login(self, nms_ip, user_name, password, new_password):

        driver = self.driver

        log.info('First time logging in.')
        self.log_into_fnd(nms_ip, user_name, password)

        try:
            log.info('Entering current password.')
            driver.find_element_by_xpath('//input[@id="currentPassword"]').clear()
            time.sleep(1)
            driver.find_element_by_xpath('//input[@id="currentPassword"]').send_keys(password)
            time.sleep(1)

            log.info('Changing new password.')
            driver.find_element_by_xpath('//input[@id="newPassword"]').clear()
            time.sleep(1)
            driver.find_element_by_xpath('//input[@id="newPassword"]').send_keys(new_password)
            time.sleep(1)

            log.info('Confirming new password.')
            driver.find_element_by_xpath('//input[@id="confirmPassword"]').clear()
            time.sleep(1)
            driver.find_element_by_xpath('//input[@id="confirmPassword"]').send_keys(new_password)
            time.sleep(1)

            driver.find_element_by_xpath('//button[contains(text(), "Change Password")]').click()
            time.sleep(2)
            try:
                log.info('Accepting "Change Password" alert.')
                alert = driver.switch_to.alert
                alert.accept()
                time.sleep(2)
            except Exception as e: log.error(e)
        except Exception as e:
            self.save_screenshot()

        log.info('Logging in back.')
        self.log_into_fnd(nms_ip, user_name, new_password)

        return driver

    def change_time_zone(self, time_zone):

        driver = self.driver
        log.info('click on root.')
        driver.find_element_by_xpath('//div[contains(@class, "cisco-logged-user")]').click()
        time.sleep(1)

        log.info('click on Time Zone.')
        driver.find_element_by_xpath('//a[contains(text(), "Time Zone")]').click()
        time.sleep(1)

        log.info('Waiting for page to load.')
        selected=''
        timeout = time.time() + 60*2
        while timeout>time.time():
            selected = driver.find_element_by_xpath('//div[@id="page_change_time_zone"]').get_attribute('class')
            if 'selected' in selected: break
            time.sleep(1)

        timeZoneId = driver.find_element_by_xpath('//input[@id="timeZoneId"]')
        timeZoneId.find_element_by_xpath('following-sibling::img').click()
        time.sleep(1)

        combo_list_items = driver.find_elements_by_xpath('//div[starts-with(@class, "x-combo-list-item") and contains(text(), "%s")]'%time_zone)
        for item in combo_list_items:
            if item.text == time_zone:
                item.click()
                break

        log.info('Confirming time_zone update.')
        driver.find_element_by_xpath('//button[contains(text(), "Update Time Zone")]').click()
        time.sleep(1)
        driver.find_element_by_xpath('//button[contains(text(), "OK")]').click()
        time.sleep(1)

    def change_preferences(self, **kwargs):

        show_chart = kwargs.get('show_chart', None)
        show_summary_count = kwargs.get('show_summary_count', None)
        enable_maps = kwargs.get('enable_maps', None)
        default_map_view = kwargs.get('default_map_view', None)
        show_device_type_list = kwargs.get('show_device_type_list', None)
        routers = kwargs.get('routers', None)
        endpoints = kwargs.get('endpoints', None)
        hers = kwargs.get('hers', None)
        servers = kwargs.get('servers', None)

        driver = self.driver
        log.info('click on root.')
        driver.find_element_by_xpath('//div[contains(@class, "cisco-logged-user")]').click()
        time.sleep(1)

        log.info('click on Preferences.')
        driver.find_element_by_xpath('//a[contains(text(), "Preferences")]').click()
        time.sleep(1)

        if show_chart is not None:
            time.sleep(1)
            if show_chart:
                log.info('Enabling Show Chart.')
                if not driver.find_element_by_id('showEventChart').get_attribute('checked'): driver.find_element_by_id('showEventChart').click()
            else:
                log.info('Disabling Show Chart.')
                if driver.find_element_by_id('showEventChart').get_attribute('checked'): driver.find_element_by_id('showEventChart').click()

        if show_summary_count is not None:
            time.sleep(1)
            if show_summary_count:
                log.info('Enabling Summary.')
                if not driver.find_element_by_id('showEventCount').get_attribute('checked'): driver.find_element_by_id('showEventCount').click()
            else:
                log.info('Disabling Summary.')
                if driver.find_element_by_id('showEventCount').get_attribute('checked'): driver.find_element_by_id('showEventCount').click()

        if enable_maps is not None:
            time.sleep(1)
            if enable_maps:
                log.info('Enabling Maps.')
                if not driver.find_element_by_id('showMapViews').get_attribute('checked'): driver.find_element_by_id('showMapViews').click()
            else:
                log.info('Disabling Maps')
                if driver.find_element_by_id('showMapViews').get_attribute('checked'): driver.find_element_by_id('showMapViews').click()

        if default_map_view is not None:
            time.sleep(1)
            if default_map_view:
                log.info('Enabling Deafault Map View.')
                if not driver.find_element_by_id('defaultMapView').get_attribute('checked'): driver.find_element_by_id('defaultMapView').click()
            else:
                log.info('Disabling Deafault Map View')
                if driver.find_element_by_id('defaultMapView').get_attribute('checked'): driver.find_element_by_id('defaultMapView').click()

        if show_device_type_list is not None:
            time.sleep(1)
            if show_device_type_list:
                log.info('Enabling Show device type list.')
                if not driver.find_element_by_id('showDeviceTypeList').get_attribute('checked'): driver.find_element_by_id('showDeviceTypeList').click()
            else:
                log.info('Disabling Show device type list.')
                if driver.find_element_by_id('showDeviceTypeList').get_attribute('checked'): driver.find_element_by_id('showDeviceTypeList').click()

        if routers is not None:
            time.sleep(1)
            if routers:
                log.info('Enabling Show device category router.')
                if not driver.find_element_by_id('showDeviceCategoryRouter').get_attribute('checked'): driver.find_element_by_id('showDeviceCategoryRouter').click()
            else:
                log.info('Disabling Show device category router.')
                if driver.find_element_by_id('showDeviceCategoryRouter').get_attribute('checked'): driver.find_element_by_id('showDeviceCategoryRouter').click()

        if endpoints is not None:
            time.sleep(1)
            if endpoints:
                log.info('Enabling Show device category endpoint.')
                if not driver.find_element_by_id('showDeviceCategoryEndpoint').get_attribute('checked'): driver.find_element_by_id('showDeviceCategoryEndpoint').click()
            else:
                log.info('Disabling Show device category endpoint.')
                if driver.find_element_by_id('showDeviceCategoryEndpoint').get_attribute('checked'): driver.find_element_by_id('showDeviceCategoryEndpoint').click()

        if hers is not None:
            time.sleep(1)
            if hers:
                log.info('Enabling Show device category HER.')
                if not driver.find_element_by_id('showDeviceCategoryHER').get_attribute('checked'): driver.find_element_by_id('showDeviceCategoryHER').click()
            else:
                log.info('Disabling Show device category HER.')
                if driver.find_element_by_id('showDeviceCategoryHER').get_attribute('checked'): driver.find_element_by_id('showDeviceCategoryHER').click()

        if servers is not None:
            time.sleep(1)
            if servers:
                log.info('Enabling Show device category Server.')
                if not driver.find_element_by_id('showDeviceCategoryServer').get_attribute('checked'): driver.find_element_by_id('showDeviceCategoryServer').click()
            else:
                log.info('Disabling Show device category Server.')
                if driver.find_element_by_id('showDeviceCategoryServer').get_attribute('checked'): driver.find_element_by_id('showDeviceCategoryServer').click()

        log.info('Clicking on Apply.')
        driver.find_element_by_xpath('//button[contains(text(), "Apply")]').click()
        time.sleep(1)

    def guidetour(self):
        driver = self.driver

        log.info('click on "cisco-logged-user".')
        driver.find_element_by_xpath('//div[contains(@class, "cisco-logged-user")]').click()
        time.sleep(2)
        try:
            #if driver.find_element_by_xpath('//a[text()="Guided Tour"]').is_displayed():
            log.info('Clicking on "Guided Tour" option.')
            driver.find_element_by_xpath('//a[text()="Guided Tour"]').click()
            time.sleep(1)
            #else:
             #   log.error("Guided Tour option is disabled!")

        except Exception as e:
            log.error(e)
            self.save_screenshot()

        return guidetour

    def logout(self):

        driver = self.driver
        logout = True

        try:
            logout_link = driver.find_element_by_xpath('//a[@id="logout_link"]')
            log.info('logout_link.is_displayed(): %s'%logout_link.is_displayed())
            while not logout_link.is_displayed():
                log.info('click on root.')
                driver.find_element_by_xpath('//div[contains(@class, "cisco-logged-user")]').click()
                time.sleep(2)
                logout_link = driver.find_element_by_xpath('//a[@id="logout_link"]')
                log.info('logout_link.is_displayed(): %s'%logout_link.is_displayed())

            logout_link.click()
            time.sleep(1)
        except Exception as e:
            log.error(e)
            self.save_screenshot()

        return logout

    def change_password(self, new_password):

        driver = self.driver
        log.info('Changing the new_password: %s'%new_password)

        try:
            log.info('Click on root.')
            driver.find_element_by_xpath('//div[contains(@class, "cisco-logged-user")]').click()
            time.sleep(1)

            log.info('click on Change Password.')
            driver.find_element_by_xpath('//a[contains(text(), "Change Password")]').click()
            time.sleep(1)

            log.info('Entering new password.')
            driver.find_element_by_xpath('//input[@id="newPassword"]').clear()
            time.sleep(1)
            driver.find_element_by_xpath('//input[@id="newPassword"]').send_keys(new_password)
            time.sleep(1)

            log.info('Entering confirm password.')
            driver.find_element_by_xpath('//input[@id="confirmPassword"]').clear()
            time.sleep(1)
            driver.find_element_by_xpath('//input[@id="confirmPassword"]').send_keys(new_password)
            time.sleep(1)

            log.info('click on "Change Password" button.')
            driver.find_element_by_xpath('//button[contains(text(), "Change Password")]').click()
            time.sleep(1)
        except Exception as e:
            log.error(e)
            self.save_screenshot()

    def get_visible_button_by_text(self, button_text, **args):

        driver = self.driver
        visible_button = None
        try:
            visible_button = driver.execute_script('return $("button:contains(\'%s\'):visible")[0]'%button_text)
        except AssertionError as ae: log.error('Unable to fetch the correct element.')

        return visible_button

    def get_visible_button_by_class(self, button_class, **args):

        driver = self.driver
        visible_button = None
        available_buttons = driver.find_elements_by_xpath('//button[contains(@class, "%s")]'%button_class)
        log.info('available_buttons with class: %s, length: %d'%(button_class, len(available_buttons)))

        time.sleep(1)
        available_buttons = [div for div in available_buttons if div.is_displayed()]
        time.sleep(1)
        visible_button = available_buttons[0] if available_buttons else None

        try:
            if visible_button: assert button_class in visible_button.get_attribute('class')
        except AssertionError as ae: log.error('Unable to fetch the correct element.')

        return visible_button
    
    def get_visible_tag_by_class(self, tag_name, tag_class, **args):

        driver = self.driver
        visible_tag = None
        available_tags = driver.find_elements_by_xpath('//%s[contains(@class, "%s")]'%(tag_name, tag_class))
        log.info('available_tags with class: %s, length: %d'%(tag_class, len(available_tags)))

        time.sleep(1)
        available_tags = [tag for tag in available_tags if tag.is_displayed()]
        time.sleep(1)
        visible_tag = available_tags[0] if available_tags else None

        try:
            if visible_tag: assert tag_class in visible_tag.get_attribute('class')
        except AssertionError as ae: log.error('Unable to fetch the correct element.')

        return visible_tag

    def get_visible_div_by_class(self, div_class, **args):

        driver = self.driver
        visible_div = None
        available_divs = driver.find_elements_by_xpath('//div[contains(@class, "%s")]'%div_class)
        log.info('available_divs with div_class: %s:, length: %d'%(div_class, len(available_divs)))

        time.sleep(1)
        available_divs = [div for div in available_divs if div.is_displayed()]
        time.sleep(1)
        visible_div = available_divs[0] if available_divs else None

        try:
            if visible_div: assert div_class in visible_div.get_attribute('class')
        except AssertionError as ae: log.error('Unable to fetch the correct element.')

        return visible_div

    def save_screenshot(self, **kwargs):

        driver = self.driver
        classname = kwargs.get('classname', 'default')
        scriptname = kwargs.get('scriptname', 'default')

        new_folder = scriptname+'_'+time.strftime('%b_%d_%Y')
        new_file = classname+'_'+time.strftime('%H:%M:%S') + '.png'
        folder = os.getcwd() + '/selenium_screenshots/' + new_folder
        relative_folder = '/selenium_screenshots/' + new_folder
        if not os.path.exists(folder): os.makedirs(folder)

        screenshot = folder + '/' + new_file
        relative_path = relative_folder + '/' + new_file
        driver.get_screenshot_as_file(screenshot)
        log.info('Screenshot saved at:\n%s' % screenshot)
        log.info('http://172.27.171.158'+relative_path)

    def check_error_popup(self):

        driver = self.driver
        error_popup_exists = False
        try:
            time.sleep(1)
            error_popup = driver.execute_script('return $(".x-window-header-text").text()')
            if 'Error' in error_popup:
                error_popup_exists = True
                self.save_screenshot()
                driver.execute_script('$("button:contains(\'OK\'):visible").click()')
                time.sleep(1)
                raise AssertionError('Should not see an Error.')
        except AssertionError as ae: log.error(ae)
        except Exception as e:
            driver.refresh()
            log.error(e)
        
        return error_popup_exists

    def ignore_flash_error(self):
        driver = self.driver

        time.sleep(1)
        driver.execute_script('if($(\'span:contains("No Flash Player Detected")\').length>0){\
                            $(\'button:contains("OK")\').click() }')
        time.sleep(1)

    def wait_until_element_exists(self, **kwargs):
        driver = self.driver
        foundElement = False
        driver.implicitly_wait(1)
        timeout = kwargs.get('timeout', 60)
        xpath = kwargs.get('xpath')
        for i in range(timeout):
            try:
                time.sleep(1)
                driver.find_element_by_xpath(xpath)
                foundElement = True
                log.info("Expected xpath " + xpath + " element found in " + str(i) + " seconds")
                break
            except:
                pass

        if not foundElement:
            log.info("Expected xpath " + xpath + " element not found in " + str(i) + " seconds")

        driver.implicitly_wait(10)
        return foundElement

    def wait_until_element_notexists(self, **kwargs):
        driver = self.driver
        element_disabled = False
        timeout = 60
        driver.implicitly_wait(1)
        xpath = kwargs.get('xpath')
        for i in range(timeout):
            try:
                time.sleep(1)
                if not driver.find_element_by_xpath(xpath):
                    element_disabled = True
                    break
            except:
                element_disabled = True
                break

        log.info("Expected xpath " + xpath + " element disappered in " + str(i) + " seconds")
        driver.implicitly_wait(10)
        return element_disabled

    def read_csv_data(self, start_index):
        readflag = False
        result_list = []

        list_of_files = glob.glob(os.getcwd() + '/downloads/*.csv')
        filename = max(list_of_files, key=os.path.getctime)
        log.info("Downloaded FileName : " + filename)
        with open(os.path.join(os.getcwd() + "/downloads", filename)) as csvfile:
            readCSV = csv.reader(csvfile, delimiter=',')
            for row in readCSV:
                if not row:
                    continue

                if str(start_index) in str(row):
                    readflag = True
                    continue
                elif 'No data available.' in str(row):
                    readflag = True

                if readflag:
                    log.info(row)
                    result_list.append(row)


        log.info(result_list)
        return result_list

    def start_EEM_upload(self, eid, auto_user_ws):

        try:
            driver = webdriver.Firefox()
            driver.implicitly_wait(10)
            driver.maximize_window()

            log.info("EEM Script Upload")
            conf_nav = ConfigNavigation(driver)
            conf_nav.nav_sub_menu('router_file_mgmt')
            time.sleep(1)
            driver.find_element_by_xpath(
                "//div[@id='leftHandTree']//span[text()='configuration group']/../../..//span[contains(text(),'default-cgr1000')]").click()
            self.wait_until_element_exists(xpath="//table[@id='uploadBtn']")
            driver.find_element_by_xpath("//table[@id='uploadBtn']").click()
            time.sleep(1)
            driver.find_element_by_xpath("//div[@id='fileGrid']/../..//button[text()='Add File']").click()

            file_input = driver.find_element_by_xpath("//input[@id='formchfilefile']")
            driver.execute_script(
                'arguments[0].style = ""; arguments[0].style.display = "block"; arguments[0].style.visibility = "visible";',
                file_input)
            time.sleep(1)
            file_input.send_keys("/ws/" + auto_user_ws + "/pyats/iot-fnd-4.3/device_files/eem_template.tcl")
            time.sleep(2)
            driver.find_element_by_xpath("//div[@id='firmwareImageForm-routerFile']//button[text()='Add File']").click()
            driver.find_element_by_xpath("//button[text()='OK']").click()
            time.sleep(1)
            driver.find_element_by_xpath("//div[@id='fileGrid']//a[text()='eem_template.tcl']/../../..").click()
            driver.find_element_by_xpath("//button[text()='Upload File']").click()
            time.sleep(2)

            if driver.find_element_by_xpath(
                    "//div[@id='uploadDelGrid']//thead/tr/td[1]//div[@class='x-grid3-hd-checker']").is_selected():
                driver.find_element_by_xpath(
                    "//div[@id='uploadDelGrid']//thead/tr/td[1]//div[@class='x-grid3-hd-checker']").click()
            else:
                driver.find_element_by_xpath(
                    "//div[@id='uploadDelGrid']//thead/tr/td[1]//div[@class='x-grid3-hd-checker']").click()
                time.sleep(2)
                driver.find_element_by_xpath(
                    "//div[@id='uploadDelGrid']//thead/tr/td[1]//div[@class='x-grid3-hd-checker']").click()

            driver.find_element_by_xpath(
                "//div[@id='uploadDelGrid']//div[text()='" + eid + "']/../../td[1]//div[@class='x-grid3-row-checker']").click()
            driver.find_element_by_xpath("//div[@id='uploadDeleteForm']//button[text()='Upload']").click()

            time.sleep(3)
            driver.find_element_by_xpath("//button[text()='OK']").click()

            time.sleep(1)
            driver.find_element_by_xpath(
                "//div[@id='leftHandTree']//span[text()='configuration group']/../../..//span[contains(text(),'default-cgr1000')]").click()
            time.sleep(1)

            if self.wait_until_element_exists(xpath="//div[@id='groupfileMngStatus']//td[text()='Finished']",
                                                      timeout=120):
                log.info("Upload job finished!")
            else:
                status_text = driver.find_element_by_xpath("//div[@id='groupfileMngStatus']//tr[2]/td[5]").text
                log.error("Upload job status - " + status_text)

            # cleaning tcl files
            time.sleep(2)
            self.wait_until_element_exists(xpath="//table[@id='deleteBtn']//button[text()='Delete']")
            driver.find_element_by_xpath("//table[@id='deleteBtn']//button[text()='Delete']").click()
            time.sleep(1)
            driver.find_element_by_xpath("//div[@id='delfileGrid']//div[text()='eem_template.tcl']").click()
            driver.find_element_by_xpath(
                "//div[@class=' x-window x-resizable-pinned'][contains(@style,'visibility: visible;')]//button[text()='Delete File']").click()
            time.sleep(2)
            if driver.find_element_by_xpath(
                    "//div[@id='uploadDelGrid']//thead/tr/td[1]//div[@class='x-grid3-hd-checker']").is_selected():
                driver.find_element_by_xpath(
                    "//div[@id='uploadDelGrid']//thead/tr/td[1]//div[@class='x-grid3-hd-checker']").click()
            else:
                driver.find_element_by_xpath(
                    "//div[@id='uploadDelGrid']//thead/tr/td[1]//div[@class='x-grid3-hd-checker']").click()
                time.sleep(2)
                driver.find_element_by_xpath(
                    "//div[@id='uploadDelGrid']//thead/tr/td[1]//div[@class='x-grid3-hd-checker']").click()

            driver.find_element_by_xpath(
                "//div[@id='uploadDelGrid']//div[text()='" + eid + "']/../../td[1]//div[@class='x-grid3-row-checker']").click()

            driver.find_element_by_xpath("//table[@id='uDFormDeleteBtn']//button[text()='Delete']").click()
            time.sleep(2)
            driver.find_element_by_xpath("//button[text()='OK']").click()
            time.sleep(2)

            if self.wait_until_element_exists(
                    xpath="//div[@id='groupfileMngStatus']//td[text()='Finished']", timeout=120):
                log.info("Delete job finished!")
            else:
                status_text = driver.find_element_by_xpath("//div[@id='groupfileMngStatus']//tr[2]/td[5]").text
                if 'Running' in status_text:
                    log.info("Delete job status - " + status_text)
                    self.wait_until_element_exists(
                        xpath="//div[@id='groupfileMngStatus']//td[text()='Finished']")
                else:
                    log.error("Delete job status - " + status_text)

            time.sleep(2)

            self.wait_until_element_exists(xpath="//table[@id='uploadBtn']")
            driver.find_element_by_xpath("//table[@id='uploadBtn']").click()
            time.sleep(1)
            driver.find_element_by_xpath(
                "//div[@id='fileGrid']//a[text()='eem_template.tcl']/../../..//a[text()='Delete']").click()
            driver.find_element_by_xpath("//button[text()='Yes']").click()
            driver.find_element_by_xpath("//button[text()='OK']").click()
            driver.find_element_by_xpath(
                "//div[@class=' x-window x-resizable-pinned'][contains(@style,'visibility: visible;')]//div[@class='x-tool x-tool-close']").click()

            driver.quit()

        except Exception as ex:
            log.error("Something went wrong while validating group creation", ex)

    def change_display_count(self, display_count):
        try:
            drop_down = driver.execute_script('return $(".x-form-arrow-trigger:visible")[0]')
            drop_down.click()
            time.sleep(1)

            dropdown_elements = driver.find_elements_by_xpath('//div[starts-with(@class, "x-combo-list-item")]')
            dropdown_elements = [dropdown_element for dropdown_element in dropdown_elements if dropdown_element.is_displayed()]

            for dropdown_element in dropdown_elements:
                if dropdown_element.text == str(display_count):
                    dropdown_element.click()
                    time.sleep(1)
                    log.info('Selected: %s' % str(display_count))
                    break
        except Exception as e:
            self.save_screenshot()
            log.error('Unable to change display count.')

    def capture_console_errors(self):

        error_logs=[]
        try:
            for entry in self.driver.get_log('browser'):
                if str(entry.get('level')) == 'ERROR':
                    error_logs.append(str(entry.get('message')))
        except Exception as e:
            log.error(e)
        
        return error_logs

class DevicesNavigation():
    ''' This class defines all the navigation opertaions under "Devices" page. '''

    def __init__(self, driver, *arg):
        self.arg = arg
        self.driver = driver
        self.driver_utils = DriverUtils(driver)

    def nav_sub_menu(self, sub_menu):
        '''
        Method to navigate to given submenu under Devices.

        This is how you need to call.
        
        >>> dev_nav = ui_common_utils.DevicesNavigation(driver)
        >>> dev_nav.nav_sub_menu('field_devices')

        sub_menu choices :-
            * 'field_devices': 'fan1',
            * 'head_end_routers': 'her1',
            * 'servers': 'server1'
            * 'assets': 'assets1'

        :param sub_menu: Name of the sub_menu to navigate.
        :type sub_menu: str
        '''
        log.info('Navigating to submenu: %s under Devices.'%sub_menu)

        driver = self.driver
        driver_utils = self.driver_utils
        nav_sub_menu = False

        driver_utils.ignore_flash_error()
        time.sleep(2)
        menu_class = driver.execute_script('return $("#nav1_admin").parent().attr(\'class\')')
        if 'disableMenutrue' in menu_class:
            log.error('DEVICES Menu is not active.')
            return nav_sub_menu

        log.info('Clicking "nav1_devices"')
        driver.find_element_by_id('nav1_devices').click()
        time.sleep(2)

        #Dictionary of sub_menu id tuples as per the selection.
        sub_menu_ids = {
            'field_devices': 'fan1',
            'head_end_routers': 'her1',
            'servers': 'server1',
            'assets': 'assets1'
        }

        try:
            #Determine sub_menu id's depending on the requested sub_menu.
            sub_menu_id = sub_menu_ids[sub_menu]
            submenu_class = driver.execute_script('return $("#%s").attr(\'class\')'%sub_menu_id)
            if 'disableMenutrue' in submenu_class:
                log.error('%s is not active.'%sub_menu)
                driver.find_element_by_id('nav1_devices').click()
                time.sleep(1)
                return nav_sub_menu

            log.info('Clicking "%s"'% sub_menu_id)
            # driver.execute_script('$("#%s")[0].click()'%sub_menu_id)
            driver.find_element_by_id('%s'%sub_menu_id).click()
            driver_utils.ignore_flash_error()

            #Wait unitl the clicked page is loaded completely.
            timeout = time.time() + 60*2
            while timeout>time.time():
                try:
                    driver_utils.ignore_flash_error()
                    breadcrumbs_span = driver.find_element_by_class_name('breadcrumbs-span')
                    if breadcrumbs_span: break
                except (NoSuchElementException, ElementNotVisibleException) as e: log.info('Element not found: %s' % e)
                except Exception as e: log.info(e)
            
            driver_utils.wait_for_loading()
            if driver_utils.check_error_popup():pass
            else: nav_sub_menu = True
        except AssertionError as ae: log.error(ae)
        except Exception as e:
            driver_utils.save_screenshot()
            driver.refresh()
            log.error(e)

        return nav_sub_menu

class OperationsNavigation():
    ''' This class defines all the navigation opertaions under "Operations" page. '''

    def __init__(self, driver, *arg):
        self.arg = arg
        self.driver = driver
        self.driver_utils = DriverUtils(driver)

    def nav_sub_menu(self, sub_menu):
        '''
        Method to navigate to given submenu under "Operations".

        :param sub_menu: Name of the sub_menu to navigate.
        :type sub_menu: str

        This is how you need to call.
        
        >>> oper_nav = ui_common_utils.OperationsNavigation(driver)
        >>> oper_nav.nav_sub_menu('events')

        sub_menu choices :-
            * 'events': 'events1',
            * 'issues': 'issues1',
            * 'tunnel_status': 'tunnel_status1',
            * 'trouble_ticket': 'troubleTicket1'
        '''
        log.info('Navigating to submenu: %s under Operations.'%sub_menu)
        
        driver = self.driver
        driver_utils = self.driver_utils
        nav_sub_menu = False

        driver_utils.ignore_flash_error()
        menu_class = driver.execute_script('return $("#nav1_admin").parent().attr(\'class\')')
        if 'disableMenutrue' in menu_class:
            log.error('OPERATIONS Menu is not active.')
            return nav_sub_menu

        log.info('Clicking "nav1_operations"')
        driver.find_element_by_id('nav1_operations').click()
        time.sleep(2)

        #Dictionary of sub_menu id tuples as per the selection.
        sub_menu_ids = {
            'events': 'events1',
            'issues': 'issues1',
            'tunnel_status': 'tunnel_status1',
            'trouble_ticket': 'troubleTicket1'
        }

        try:
            #Determine sub_menu id's depending on the requested sub_menu.
            sub_menu_id = sub_menu_ids[sub_menu]
            submenu_class = driver.execute_script('return $("#%s").attr(\'class\')'%sub_menu_id)
            if 'disableMenutrue' in submenu_class:
                log.error('%s is not active.'%sub_menu)
                return nav_sub_menu

            log.info('Clicking "%s"'% sub_menu_id)
            driver.find_element_by_id('%s'%sub_menu_id).click()
            driver_utils.ignore_flash_error()

            #Wait unitl the clicked page is loaded completely.
            timeout = time.time() + 60*2
            while timeout>time.time():
                try:
                    driver_utils.ignore_flash_error()
                    breadcrumbs_span = driver.find_element_by_class_name('breadcrumbs-span')
                    if breadcrumbs_span: break
                    time.sleep(2)
                except (NoSuchElementException, ElementNotVisibleException) as e: log.info('Element not found: %s' % e)
                except Exception as e: log.info(e)
            driver_utils.wait_for_loading()

            if driver_utils.check_error_popup():pass
            else: nav_sub_menu = True
        except AssertionError as ae: log.error(ae)
        except Exception as e:
            driver_utils.save_screenshot()
            driver.refresh()
            log.error(e)
        
        return nav_sub_menu

class ConfigNavigation():
    ''' This class defines all the navigation opertaions under "Config" page. '''

    def __init__(self, driver, *arg):
        self.arg = arg
        self.driver = driver
        self.driver_utils = DriverUtils(driver)

    def nav_sub_menu(self, sub_menu):
        '''
        Method to navigate to given submenu under "Config".

        :param sub_menu: Name of the sub_menu to navigate.
        :type sub_menu: str
        '''
        log.info('Navigating to submenu: %s under Config'%sub_menu)

        driver = self.driver
        driver_utils = self.driver_utils
        nav_sub_menu = False

        try:
            time.sleep(1)
            log.info('Accepting alert')
            alert = driver.switch_to.alert
            alert.accept()
        except Exception as e: log.info('No Alert present.')

        driver_utils.ignore_flash_error()
        menu_class = driver.execute_script('return $("#nav1_admin").parent().attr(\'class\')')
        if 'disableMenutrue' in menu_class:
            log.error('CONFIG Menu is not active.')
            return nav_sub_menu

        log.info('Clicking "nav1_config"')
        driver.find_element_by_id('nav1_config').click()
        time.sleep(2)

        #Dictionary of sub_menu id tuples as per the selection.
        sub_menu_ids = {
            'app_mgmt': 'appMgmt1',
            'dev_configuration': 'configuration1',
            'firmware_update': 'firmware1',
            'router_file_mgmt': 'router_files1',
            'rules': 'rules1',
            'tunnel_provisioning': 'tunnel_template1',
            'groups': 'group_management1'
        }

        try:
            #Determine sub_menu id's depending on the requested sub_menu.
            sub_menu_id = sub_menu_ids[sub_menu]
            submenu_class = driver.execute_script('return $("#%s").attr(\'class\')'%sub_menu_id)
            if 'disableMenutrue' in submenu_class:
                log.error('%s is not active.'%sub_menu)
                return nav_sub_menu

            log.info('Clicking "%s"'% sub_menu_id)
            driver.find_element_by_id('%s'%sub_menu_id).click()
            driver_utils.ignore_flash_error()

            #Wait unitl the clicked page is loaded completely.
            timeout = time.time() + 60*2
            while timeout>time.time():
                try:
                    breadcrumbs_span = driver.find_element_by_class_name('breadcrumbs-span')
                    log.info('breadcrumbs_span loaded.')
                    if breadcrumbs_span: break
                    time.sleep(2)
                except (NoSuchElementException, ElementNotVisibleException) as e: log.info('Element not found: %s' % e)
                except Exception as e: log.info(e)
            driver_utils.wait_for_loading()

            error_popup = driver.execute_script('return $(".x-window-header-text").text()')
            if driver_utils.check_error_popup(): pass
            else: nav_sub_menu = True
        except AssertionError as ae: log.error(ae)
        except Exception as e:
            driver_utils.save_screenshot()
            driver.refresh()
            log.error(e)
        
        return nav_sub_menu

class AdminNavigation():
    ''' This class defines all the navigation opertaions under "Admin" page. '''

    def __init__(self, driver, *arg):
        self.arg = arg
        self.driver = driver
        self.driver_utils = DriverUtils(driver)

    def nav_sub_menu(self, sub_menu):
        '''
        Method to navigate to given submenu under "Admin".

        :param sub_menu: Name of the sub_menu to navigate.
        :type sub_menu: str
        '''
        log.info('Navigating to submenu: %s under Admin'%sub_menu)

        driver = self.driver
        driver_utils = self.driver_utils
        nav_sub_menu = False

        driver_utils.ignore_flash_error()
        menu_class = driver.execute_script('return $("#nav1_admin").parent().attr(\'class\')')
        if 'disableMenutrue' in menu_class:
            log.error('ADMIN Menu is not active.')
            return nav_sub_menu

        log.info('Clicking "nav1_admin"')
        driver.find_element_by_id('nav1_admin').click()
        time.sleep(1)

        #Dictionary of sub_menu id tuples as per the selection.
        sub_menu_ids = {
            'domains': 'domains1',
            'password_policy': 'local_password_policy1',
            'remote_auth': 'remoteAuth1',
            'roles': 'roles1',
            'users': 'users1',

            'active_sessions': 'active_sessions1',
            'audit_trail': 'audit_trail1',
            'certificates': 'certificates1',
            'data_retention': 'pruning_job_settings1',
            'license_center': 'license_center1',
            'logging': 'logging1',
            'tunnel_settings': 'tunnel_settings1',
            'server_settings': 'server_settings1',
            'syslog': 'syslog1'
        }

        try:
            #Determine sub_menu id's depending on the requested sub_menu.
            sub_menu_id = sub_menu_ids[sub_menu]
            submenu_class = driver.execute_script('return $("#%s").attr(\'class\')'%sub_menu_id)
            if 'disableMenutrue' in submenu_class:
                log.error('%s is not active.'%sub_menu)
                return nav_sub_menu

            log.info('Clicking "%s"'% sub_menu_id)
            driver.find_element_by_id('%s'%sub_menu_id).click()
            driver_utils.ignore_flash_error()

            #Wait unitl the clicked page is loaded completely.
            timeout = time.time() + 60*2
            while timeout>time.time():
                try:
                    driver_utils.ignore_flash_error()
                    breadcrumbs_span = driver.find_element_by_class_name('breadcrumbs-span')
                    if breadcrumbs_span: break
                    time.sleep(2)
                except (NoSuchElementException, ElementNotVisibleException) as e: log.info('Element not found: %s' % e)
                except Exception as e: log.info(e)
            driver_utils.wait_for_loading()

            if driver_utils.check_error_popup():pass
            else: nav_sub_menu = True
        except AssertionError as ae: log.error(ae)
        except Exception as e:
            driver_utils.save_screenshot()
            driver.refresh()
            log.error(e)
        
        return nav_sub_menu

class Dashboard(DevicesNavigation):
    ''' '''
    def __init__(self, driver, *arg):
        self.arg = arg
        self.driver = driver
        self.driver_utils = DriverUtils(driver)

    def get_current_dashlets(self):
        
        driver = self.driver
        log.info('\nCurrent Dashlets on Dashboard..')
        current_dashlets = driver.execute_script('function dashlets(){\
                                    dashlets=[];\
                                    $.each($(".x-panel-header-text:visible"), function(i, d){dashlets.push(d.textContent)});\
                                    return dashlets;\
                                }\
                                return dashlets();')
        if 'Add Dashlets' in current_dashlets: current_dashlets.remove('Add Dashlets')
        if 'Set Refresh Interval' in current_dashlets: current_dashlets.remove('Set Refresh Interval')

        return current_dashlets
    
    def get_available_dashlets(self):

        driver = self.driver
        log.info('\nClicking on Dashlet gear.')
        driver.find_element_by_xpath('//div[contains(@class, "x-tool-gear")]').click()
        time.sleep(1)

        if not driver.find_element_by_xpath('//em[contains(text(), "Dashlets")]').is_displayed():
            log.info('Clicking on "Add Dashlets"')
            driver.find_element_by_xpath('//span[contains(text(), "Add Dashlets")]/../div').click()
            time.sleep(1)

        log.info('\nGetting dashlets available to add..')
        available_dashlets = driver.execute_script('function dashlets(){\
                                dashlets=[];\
                                $.each($("dt em:visible"), function(i, d){if(i%2==0) dashlets.push(d.textContent)});\
                                return dashlets;\
                            }\
                            return dashlets();')
        driver.find_element_by_xpath('//button[contains(text(), "Close")]').click()
        time.sleep(1)

        return available_dashlets

    def add_dashlet(self, dashlet_name):

        driver = self.driver
        dashlet_added = False
        log.info('Clicking on dashlet settings.')
        driver.find_element_by_xpath('//div[contains(@class, "x-tool-gear")]').click()
        time.sleep(1)

        if not driver.find_element_by_xpath('//em[contains(text(), "Dashlets")]').is_displayed():
            log.info('Clicking on "Add Dashlets"')
            driver.find_element_by_xpath('//span[contains(text(), "Add Dashlets")]/../div').click()
            time.sleep(1)

        log.info('Adding dashlet: %s'%dashlet_name)
        try:
            log.info('Finding requested dashlet.')
            requested_dashlet = driver.find_element_by_xpath('//em[contains(text(), "%s")]'%dashlet_name)
            requested_dashlet.click()
            time.sleep(1)
            dashlet_added = True
        except Exception as e: log.error(e)
        driver.find_element_by_xpath('//button[contains(text(), "Close")]').click()
        time.sleep(1)

        log.info('Dashlet: %s is added: %s'%(dashlet_name, dashlet_added))
        return dashlet_added

    def set_refresh_interval_dashlet(self, **kwargs):

        driver = self.driver
        refresh_interval = kwargs.get('refresh_interval','30 seconds')
        log.info('Clicking on dashlet settings.')

        driver.find_element_by_xpath('//div[contains(@class, "x-tool x-tool-gear")]').click()
        time.sleep(1)

        if not driver.find_element_by_xpath('//em[contains(text(), "Dashlets")]').is_displayed():
            driver.find_element_by_xpath('//input[@id="refreshCombo"]').click()
            time.sleep(1)
            driver.find_element_by_xpath("//div[contains(@style,'visibility: visible;')]//div[text()='" + refresh_interval + "']").click()
            #log.info('Set refresh interval to : %s'%refresh_interval)
            driver.find_element_by_xpath('//button[contains(text(), "Close")]').click()
            time.sleep(1)
            log.info('Refresh interval set to : %s' % refresh_interval)

    def add_all_dashlets(self):

        driver = self.driver
        log.info('Clicking on dashlet settings.')
        driver.find_element_by_xpath('//div[contains(@class, "x-tool-gear")]').click()
        time.sleep(1)

        if not driver.find_element_by_xpath('//em[contains(text(), "Dashlets")]').is_displayed():
            log.info('Clicking on "Add Dashlets"')
            driver.find_element_by_xpath('//span[contains(text(), "Add Dashlets")]/../div').click()
            time.sleep(1)

        available_dashlets = driver.find_elements_by_xpath('//div[contains(@class, "x-list-body")]/dl/dt/em')[0::2]
        available_dashlets_names = [dashlet.text for dashlet in available_dashlets]
        log.info('available_dashlets_names: %s'%available_dashlets_names)

        for dashlet_name in available_dashlets_names:
            log.info('Adding dashlet: %s'%dashlet_name)
            # driver.find_element_by_xpath('//div[contains(@class, "x-list-body")]/dl/dt/em[contains(text(), "%s")]'%dashlet_name).click()
            driver.execute_script('$(\'.x-list-body dl dt em:contains("%s")\').click()'%dashlet_name)
            time.sleep(2)

        log.info('Closing dashboard Settings popup.')
        driver.execute_script('$("button:contains(\'Close\')").click()')
        time.sleep(1)

    def remove_dashlet(self, dashlet_name):

        driver = self.driver
        dashlet_removed = False

        try:
            log.info('Clicking on given dashlet: "%s" close button.'%dashlet_name)
            driver.find_element_by_xpath('//span[contains(text(), "%s")]/../div[contains(@class, "x-tool-close")]'%dashlet_name).click()
            dashlet_removed = True
        except Exception as e: log.error(e)
        time.sleep(1)

        log.info('Dashlet: %s is removed: %s'%(dashlet_name, dashlet_removed))
        return dashlet_removed

    def apply_filter(self, filter_value):

        driver = self.driver
        try:
            # filteroverallTab driver.find_element_by_id('filteroverallTab')
            driver.find_element_by_id('overallTabtbContainer')
        except Exception as e: 
            log.info('Clicking on global filter button.')
            #driver.find_element_by_xpath('//div[contains(@class, "x-tool-search")]').click()
            driver.find_element_by_xpath('//div[@id="settings-gear"]//div[contains(@class, "x-tool-selected-filter")]').click()
            time.sleep(3)
        
        log.info('Clicking on the given filter: %s'%filter_value)
        driver.find_element_by_xpath('//button[contains(text(), "%s")]'%filter_value).click()
        time.sleep(1)

    def apply_filter_on_dashlet(self, dashlet_name, filter_value):

        driver = self.driver
        dashlet_frame = driver.find_element_by_xpath('//span[contains(text(), "%s")]/..'%dashlet_name)
        try:
            driver.find_element_by_id('overallTabtbContainer')
        except Exception as e: 
            log.info('Clicking on global filter button.')
            driver.find_element_by_xpath('//div[contains(@class, "x-tool-search")]').click()
            time.sleep(1)
        
        log.info('Clicking on the given filter: %s'%filter_value)
        driver.find_element_by_xpath('//button[contains(text(), "%s")]'%filter_value).click()
        time.sleep(1)

class FieldDevices(DevicesNavigation):
    ''' '''
    def __init__(self, driver, *arg):
        self.arg = arg
        self.driver = driver
        self.driver_utils = DriverUtils(driver)

    def nav_router_group(self, group_name):
        '''
        Method to navigate to Router group.

        :param group_name: Name of the group to navigate.
        :type group_name: str
        '''
        log.info('Navigating to %s' % group_name)
        driver = self.driver
        driver_utils = self.driver_utils
        nav_group_succ = False

        try:
            selected=''
            timeout = time.time() + 60*2
            while timeout>time.time():
                router_group = driver.execute_script('\
                                    return $("span")\
                                    .filter(\
                                        function(){return $(this).text().split(" (")[0].toLowerCase()==="%s".toLowerCase();}\
                                    )[0]'%group_name)
                selected = router_group.find_element_by_xpath('../..').get_attribute('class')
                log.info('router_group selected: %s'%selected)
                if 'x-tree-selected' in selected:
                    nav_group_succ = True
                    break
                time.sleep(1)
                log.info('Clicking on Group: %s'%group_name)
                router_group.click()
                time.sleep(1)

            driver_utils.wait_for_loading()
        except Exception as e:
            driver_utils.save_screenshot()
            log.error('Please provide a valid Group name.')

        return nav_group_succ

    def nav_label(self, label_name):

        driver = self.driver

        selected=''
        timeout = time.time() + 60*2
        log.info('Navigating to label_name: %s.'%label_name)
        label_group_ele = driver.find_element_by_xpath('//span[contains(text(), "%s")]'%(label_name))
        while timeout>time.time():
            selected = label_group_ele.find_element_by_xpath('../..').get_attribute('class')
            search_input = driver.execute_script('return $("input.x-box-item:visible")[0]')
            search_input_val = search_input.get_attribute('value')
            if 'x-tree-selected' in selected and label_name in search_input_val: break

            log.info('Clicking on label_name: %s to be active.'%label_name)
            label_group_ele.click()
            time.sleep(2)

    def nav_tab(self, tab_name):
        '''
        Method to navigate to Router group.
        This is how you need to call.
        
        >>> field_devices = ui_common_utils.FieldDevices(driver)
        >>> field_devices.nav_tab('cell_cdma')

        tab_name choices :-
            * 'map':'Map',
            * 'cell_cdma':'Cellular-CDMA',
            * 'cell_gsm':'Cellular-GSM', 
            * 'config':'Config', 
            * 'dhcp_config':'DHCP Config', 
            * 'default':'Default', 
            * 'ethernet_traffic':'Ethernet Traffic', 
            * 'firmware':'Firmware', 
            * 'tunnel':'Tunnel'

        :param tab_name: Name of the tab to navigate.
        :type tab_name: str
        '''
        driver = self.driver
        driver_utils = self.driver_utils
        nav_tab_success = False

        tab_dict = {
                    'fan_map':'Map',
                    'fan_default':'Inventory',
                    'map':'Map',
                    'cell_cdma':'Cellular-CDMA',
                    'cell_gsm':'Cellular-GSM', 
                    'config':'Config', 
                    'dhcp_config':'DHCP Config', 
                    'inventory':'Inventory', 
                    'ethernet_traffic':'Ethernet Traffic', 
                    'firmware':'Firmware', 
                    'tunnel':'Tunnel',
                    'default':'Default',
                    'cell_endpoints': 'Cellular Endpoints',
                    'config': 'Config',
                    'firmware_group': 'FirmwareGroup',
                    'plc_mesh': 'PLC Mesh',
                    'rf_mesh': 'RF Mesh',
                    'security': 'security',
                    'health': 'Health'
                   }
        try:
            tab = tab_dict[tab_name]
            log.info('Navigating to Tab: %s'%tab)
            tab_element = driver.execute_script('return $(".x-tab-strip-text:contains(\'%s\'):visible")[0]'%tab)
            log.info('tab_element: %s'%tab_element)

            #Waiting for maximum 2 minutes for the tab to be loaded.
            active=''
            timeout = time.time() + 60*2
            while timeout>time.time():
                tab_element.click()
                time.sleep(1)
                active = driver.execute_script('\
                        return \
                        $(".x-tab-strip-text:contains(\'%s\'):visible")\
                        .closest("li").\
                        attr("class")'%tab)
                log.info('active class: %s'%active)
                if 'active' in active:
                    nav_tab_success = True
                    break
                time.sleep(2)
        except Exception as e:
            driver_utils.save_screenshot()
            log.error(e)

        log.info('tab_name:%s Navigation:%s'%(tab_name, nav_tab_success))
        return nav_tab_success

    def nav_dev_tab(self, tab_name):

        driver = self.driver
        driver_utils = self.driver_utils
        dev_tab_navigated = False

        tab_dict = {
                    'dev_info':'elementTabs__infoTab',
                    'events':'elementTabs__eventsTab',
                    'conf_prop':'elementTabs__configPropertiesTab',
                    'run_conf':'elementTabs__configTab',
                    'mesh_routing_tree':'elementTabs__routingTab',
                    'mesh_link_traffic':'elementTabs__meshTrafficTab',
                    'App':"elementTabs__appTab",
                    'IOx':'elementTabs__SparrowIOxTab',
                    'router_files':'elementTabs__fileTab',
                    'raw_sockets':'elementTabs__rawSocketsTab',
                    'work_orders':'elementTabs__workOrderTab',
                    'assets':'elementTabs__assetTab'
                   }
        try:
            tab_element=tab_dict[tab_name]
            log.info('Clicking tab_element:%s'%(tab_element))

            active=''
            timeout = time.time() + 60*2
            while timeout>time.time():
                try:
                    driver.execute_script('$("iframe").contents().find("#%s a")[1].click()'%tab_element)
                    time.sleep(1)
                    selected = driver.execute_script('return $("iframe").contents().find("#%s").attr("class")'%tab_element)
                    if 'x-tab-strip-active' in selected:
                        dev_tab_navigated = True
                        break
                    time.sleep(1)
                except Exception as e: pass
        except Exception as e:
            log.error()
            driver_utils.save_screenshot()
        
        log.info('Naviagted to %s: %s'%(tab_name, dev_tab_navigated))
        return dev_tab_navigated

    def click_element(self, ele_name):
        '''
        Method to navigate to given element.

        :param ele_name: Name of the element to click
        :type ele_name: str
        '''
        driver = self.driver

        if ele_name == 'zoom':
            pass
        elif ele_name == 'gray_scale':
            pass
        elif ele_name == 'overlay':
            pass
        elif ele_name == 'refresh':
            pass
        elif ele_name == 'search_devices':
            pass
        elif ele_name == 'show_filters':
            pass

    def label_operation(self, opertaion, label_name):
        '''
        Method to click on 'Label' opertaion.

        :param opertaion: Name of the operation button to click
        :type opertaion: str
        '''
        driver = self.driver
        driver_utils = self.driver_utils
        label_operation_completed = False
        time.sleep(2)
        log.info('\nClicking on Label button.')
        driver.execute_script('return $("button:contains(\'Label\')")[0]').click()
        time.sleep(2)

        if opertaion == 'add':
            try:
                log.info('Clicking on btnAddLabel element.')
                driver.find_element_by_id('btnAddLabel').click()
                driver_utils.wait_for_loading()

                input_ele = driver.execute_script('return $(".x-window-bwrap input.x-form-field:visible")[0]')
                log.info('Clearing the input element.')
                input_ele.clear()
                time.sleep(2)
                log.info('\nEntering label_name: %s.'%label_name)
                input_ele.send_keys(label_name)
                time.sleep(2)
                input_ele.send_keys(Keys.ENTER)
                time.sleep(2)
                dropdown = driver.execute_script('return $(".x-form-arrow-trigger:visible")[1]')
                dropdown.click()
                time.sleep(1)
                dropdown.click()
                time.sleep(1)
                log.info('Current label name: %s'%input_ele.get_attribute('value'))
                driver.execute_script('return $(".x-window-header-text:contains(\'Add Label\')")[0]').click()
                time.sleep(2)
                log.info('Clicking on "Add Label" button.')
                add_label = driver.execute_script('return $("button:contains(\'Add Label\'):visible")[0]')
                add_label.click()
                time.sleep(2)

                driver_utils.wait_for_loading()
                log.info('Reading the popup messages.')
                popup_header = driver.execute_script('return $(".x-window-dlg .x-window-header-text:visible").text()')
                update_response = driver.execute_script('return $(".ext-mb-text:visible").text()')

                log.info('\n\npopup_header: %s,\nupdate_response: %s'%(popup_header, update_response))
                if 'ERROR' in popup_header:
                    driver_utils.save_screenshot()
                driver.find_element_by_xpath('//button[contains(text(), "OK")]').click()
                driver_utils.wait_for_loading()

                log.info('Checking the label group: %s'%label_name)
                search_input = driver.execute_script('return $("input.x-box-item:visible")[0]')
                search_input.clear()
                time.sleep(2)
                seach_string = "label:'%s'"%label_name
                log.info('Entering the search string - %s'%seach_string )
                search_input.send_keys(seach_string)
                time.sleep(2)
                log.info('Clicking on the Search Devices button.')
                driver.execute_script('return $("table.fa-search:visible")[0]').click()
                driver_utils.wait_for_loading()
                log.info('Checking for empty devices grid.')
                has_empty_grid = driver.execute_script('return $(".x-grid-empty").text()?true:false')
                log.info('has_empty_grid: %s'%has_empty_grid)
                assert has_empty_grid==False
                label_operation_completed = True
            except AssertionError: log.error('Unable to add label.')
            except Exception as e:
                driver_utils.save_screenshot()
                log.error(e)
                driver.refresh()
                time.sleep(5)

        elif opertaion == 'remove':
            try:
                log.info('Clicking on btnRemoveLabel element.')
                driver.find_element_by_id('btnRemoveLabel').click()
                driver_utils.wait_for_loading()

                input_ele = driver.find_element_by_xpath('//div[contains(@id, "cbLabelForm")]//input[starts-with(@class, "x-form-text")]')
                input_ele.find_element_by_xpath('following-sibling::img').click()
                time.sleep(1)
                dropdown_label = None

                z_index = driver.execute_script('a=[]; $(".x-combo-list").filter(function(){ a.push($(this).css("zIndex")) }); return a;')
                z_index.sort(reverse=True)
                z_index=z_index[0]
                dropdown_label = driver.execute_script('function label(){ x_combo_list=$(".x-combo-list").filter(function(){\
                    return $(this).attr("style").indexOf("%s")>0 });\
                    return x_combo_list.children().children().filter(function(){ return $(this).text()==="%s" })[0];}\
                    return label()'%(z_index, label_name))

                if dropdown_label: dropdown_label.click()
                else: raise Exception('No label found.')
                time.sleep(2)
                driver.find_element_by_xpath('//button[contains(text(),"Remove Label")]').click()
                time.sleep(3)

                driver_utils.wait_for_loading()
                log.info('Reading the popup messages.')
                popup_header = driver.execute_script('return $(".x-window-dlg .x-window-header-text:visible").text()')
                update_response = driver.execute_script('return $(".ext-mb-text:visible").text()')

                log.info('popup_header: %s, update_response: %s'%(popup_header, update_response))
                driver.find_element_by_xpath('//button[contains(text(), "OK")]').click()
                driver_utils.wait_for_loading()

                log.info('Checking the label group: %s'%label_name)
                search_input = driver.execute_script('return $("input.x-box-item:visible")[0]')
                search_input.clear()
                time.sleep(1)
                search_input.send_keys("label:'%s'"%label_name)
                time.sleep(1)
                log.info('Clicking on the Search Devices button.')
                driver.execute_script('return $("table.fa-search:visible")[0]').click()
                driver_utils.wait_for_loading()

                search_resp = driver.execute_script('return $(".x-grid-empty").text()')
                log.info('search_resp: %s'%search_resp)
                if search_resp == 'No data is available to display':
                    label_operation_completed = True
            except Exception as e:
                driver_utils.save_screenshot()
                log.error(e)
                driver.refresh()
                time.sleep(5)

        log.info('%s operation with name: %s is completed: %s'%
                    (opertaion, label_name, label_operation_completed))
        return label_operation_completed

    def bulk_operation(self, opertaion='', file_name=''):
        '''
        Method to click on 'Bulk Operation' operation.

        :param opertaion: Name of the operation button to click
        :type opertaion: str
        '''
        driver = self.driver
        driver_utils = self.driver_utils
        operation_completed = False
        driver_utils.wait_for_loading()
        log.info(banner('Performing %s with file: %s'%(opertaion, file_name)))

        log.info('Clicking on the "Bulk Operation" button.')
        driver.find_element_by_xpath('//div[@id="netElementGrid"]//button[contains(text(),"Bulk Operation")]').click()
        time.sleep(1)

        if not opertaion: return operation_completed
        if not file_name: return operation_completed
        log.info('opertaion: %s, file_name: %s'%(opertaion, file_name))

        if opertaion == 'add_label':
            driver.find_element_by_id('addLabel').click()
            brwose_id = 'addlabelformupfilefile'
            form_div = 'x-form-el-add-label-form-up-file'
        elif opertaion == 'remove_label':
            driver.find_element_by_id('removeLabel').click()
            brwose_id = 'removelabelformupfilefile'
            form_div = 'x-form-el-remove-label-form-up-file'
        elif opertaion == 'change_dev_prop':
            log.info('Selecting "Change Device Properties".')
            driver.find_element_by_id('chDeviceButton').click()
            time.sleep(2)
            try:
                file_input = driver.find_element_by_xpath('//input[@id="formchfilefile"]')
                file_input.send_keys(file_name)
                time.sleep(1)

                invalid_icon = driver.execute_script('return $("#x-form-el-form-add-file .x-form-invalid-icon").css("visibility")')
                assert invalid_icon!='visible'
                time.sleep(1)

                log.info('Clicking on "Change" button.')
                driver.find_element_by_xpath('//div[@id="chForm"]/.//button[contains(text(), "Change")]').click()
                time.sleep(2)

                change_dev_status = None
                timeout = time.time() + 60*2
                while timeout>time.time():
                    try:
                        change_dev_status = driver.find_element_by_xpath('//div[contains(text(), "Change Device Properties ")]').text
                        log.info('change_dev_status: %s'%change_dev_status)
                    except Exception as e: pass
                    if change_dev_status: break
                    time.sleep(3)

                if 'Failed' in change_dev_status:
                    driver.execute_script('$(".x-btn-text:contains(\'Close\')").click()')
                    return operation_completed

                failure_popup = driver.execute_script('return $(".x-window-dlg").css("visibility")')
                failure_message = driver.execute_script('return $(".x-window-dlg .x-window-header-text").text()')
                log.info('failure_popup: %s\nfailure_message: %s'%(failure_popup, failure_message))
                if failure_popup=='visible':
                    log.error('failure_message: %s'%failure_message)
                    driver.execute_script('$(".x-btn-text:contains(\'OK\')").click()')
                    time.sleep(1)
                    driver.execute_script('$(".x-btn-text:contains(\'Close\')").click()')
                    time.sleep(1)
                    return operation_completed

                if 'Completed' in change_dev_status: operation_completed = True
                time.sleep(1)
                log.info('Clicking on Close button.')
                driver.execute_script('$(".x-btn-text:contains(\'Close\')").click()')
                time.sleep(1)
            except AssertionError as ae:
                log.error('Please provide a valid file name.')
                driver_utils.save_screenshot()
            except Exception as e:
                driver_utils.save_screenshot()
        elif opertaion == 'rm_devices':
            driver.find_element_by_id('rmDevicesButton').click()
            time.sleep(2)

            try:
                file_input = driver.find_element_by_xpath('//input[@id="formrmfilefile"]')
                file_input.send_keys(file_name)
                time.sleep(1)

                invalid_icon = driver.execute_script('return $("#x-form-el-form-rm-file .x-form-invalid-icon").css("visibility")')
                assert invalid_icon!='visible'
                time.sleep(2)

                log.info('Clicking on Remove button.')
                driver.find_element_by_xpath('//div[@id="rmForm"]/.//button[contains(text(), "Remove")]').click()
                time.sleep(2)

                rm_dev_status = None
                timeout = time.time() + 60*10
                while timeout>time.time():
                    try:
                        rm_dev_status = driver.find_element_by_xpath('//div[contains(text(), "Remove Devices ")]').text
                        log.info('rm_dev_status: %s'%rm_dev_status)
                    except Exception as e: pass
                    if rm_dev_status: break
                    time.sleep(3)

                if 'Failed' in rm_dev_status:
                    driver.execute_script('$(".x-btn-text:contains(\'Close\')").click()')
                    return operation_completed

                failure_popup = driver.execute_script('return $(".x-window-dlg").css("visibility")')
                failure_message = driver.execute_script('return $(".x-window-dlg .x-window-header-text").text()')
                log.info('failure_popup: %s\nfailure_message: %s'%(failure_popup, failure_message))
                if failure_popup=='visible':
                    log.error('failure_message: %s'%failure_message)
                    driver.execute_script('$(".x-btn-text:contains(\'OK\')").click()')
                    time.sleep(1)
                    driver.execute_script('$(".x-btn-text:contains(\'Close\')").click()')
                    time.sleep(1)
                    return operation_completed

                if 'Completed' in rm_dev_status: operation_completed = True
                time.sleep(1)
                driver.execute_script('$(".x-btn-text:contains(\'Close\')").click()')
                time.sleep(1)
            except AssertionError as ae:
                log.error('Please provide a valid file name.')
                driver_utils.save_screenshot()
            except Exception as e:
                driver_utils.save_screenshot()

        driver_utils.wait_for_loading()
        log.info('%s for %s is : %s'%(opertaion, file_name, operation_completed))
        return operation_completed

    def add_devices(self,file_name=''):
        '''
        Method to click on 'Bulk Import' operation.

        :param opertaion: Name of the operation button to click
        :type opertaion: str
        '''
        driver = self.driver
        driver_utils = self.driver_utils
        operation_completed = False
        driver_utils.wait_for_loading()

        log.info('Selecting "Add Devices".')
        driver.find_element_by_id('addDevicesButton').click()
        time.sleep(2)

        try:
            file_input = driver.find_element_by_xpath('//input[@id="formaddfilefile"]')
            file_input.send_keys(file_name)
            time.sleep(1)

            invalid_icon = driver.execute_script(
                'return $("#x-form-el-form-add-file .x-form-invalid-icon").css("visibility")')
            assert invalid_icon != 'visible'
            time.sleep(2)

            log.info('Clicking on Add button.')
            driver.find_element_by_xpath('//div[@id="addForm"]/.//button[contains(text(), "Add")]').click()
            time.sleep(2)

            add_dev_status = None
            timeout = time.time() + 60 * 10
            while timeout > time.time():
                try:
                    add_dev_status = driver.find_element_by_xpath('//div[contains(text(), "Add Devices ")]').text
                    log.info('add_dev_status: %s' % add_dev_status)
                except Exception as e:
                    pass
                if add_dev_status: break
                time.sleep(3)

            if 'Failed' in add_dev_status:
                driver.execute_script('$(".x-btn-text:contains(\'Close\')").click()')
                return operation_completed

            failure_popup = driver.execute_script('return $(".x-window-dlg").css("visibility")')
            failure_message = driver.execute_script('return $(".x-window-dlg .x-window-header-text").text()')
            if failure_popup == 'visible':
                log.error('failure_message: %s' % failure_message)
                driver.execute_script('$(".x-btn-text:contains(\'OK\')").click()')
                time.sleep(1)
                driver.execute_script('$(".x-btn-text:contains(\'Close\')").click()')
                time.sleep(1)
                return operation_completed

            if 'Completed' in add_dev_status: operation_completed = True
            time.sleep(1)
            log.info('Clicking on Close button.')
            driver.execute_script('$(".x-btn-text:contains(\'Close\')").click()')
            time.sleep(1)
        except AssertionError as ae:
            log.error('Please provide a valid file name.')
            driver_utils.save_screenshot()
        except Exception as e:
            driver_utils.save_screenshot()


    def ping(self, device_eids=None, ping_from_far=True):

        driver = self.driver
        driver_utils = self.driver_utils
        ping_result = {}

        try:
            if not ping_from_far:
                device_eid=device_eids[0]
                eid_element = driver.find_element_by_xpath(
                    '//a[contains(@href, "javascript:cgms.mainPnl.loadIframe") and contains(text(), "%s")]'%device_eid)
                log.info('Waiting for loading device info.')
                timeout=time.time() + 60*2
                while timeout>time.time():
                    eid_element.click()
                    time.sleep(2)
                    eid_header = driver.execute_script(
                        'return $("iframe").contents().find("#device-detail-title:visible").text()')
                    if eid_header==device_eid: break

                log.info('\nClicking on Ping button.')
                driver.execute_script('$("iframe").contents().find("#ping").click()')
                time.sleep(2)

                log.info(banner('Checking ping response.'))
                break_loop = False
                timeout=time.time() + 60*2
                while timeout>time.time():
                    try:
                        time.sleep(1)
                        log.info('Waiting for resp_elems.')
                        ping_response = driver.execute_script('function ping_response(){\
                                a=[];\
                                $.each($("iframe").contents().find("#pingwindow .x-grid3-cell-inner"), function(i,e){\
                                    a.push(e.textContent);\
                                });\
                                return a;\
                                }\
                              return ping_response();')
                        if 'Running' not in ping_response:
                            for i in range(int(len(ping_response)/4)):
                                log.info(ping_response[i*4:i*4+4:])
                                far_response = ping_response[i*4:i*4+4:]
                                eid = far_response[0].split('\n')[0]
                                far_response.append(far_response[0].split('\n')[1].split('( ')[1].split(' )')[0])
                                ping_result[eid] = far_response[1:]
                            break_loop = True
                        if break_loop: break
                    except Exception as e: pass

                log.info('\nClick on close button.')
                driver.execute_script('$("iframe").contents().find("#pingwindow .x-tool-close:visible")[0].click()')
                time.sleep(1)
                log.info('\nClicking on "Back"')
                driver.execute_script('$("iframe").contents().find("a[onclick^=\'cgms.mainPnl.loadIframeBack\'").click()')
                time.sleep(1)
            else:
                check_elems = driver.find_elements_by_xpath('//td[contains(@class, "x-grid3-td-checker")]/div/div')
                log.info('Clicking checkboxes of the given devices.')
                for device_eid in device_eids:
                    her_elem = driver.find_element_by_id('netElementGrid').find_element_by_xpath('//a[contains(text(),"%s")]'%device_eid)
                    check_elem = her_elem.find_elements_by_xpath('../../../td')[0].find_element_by_xpath('div/div')
                    check_elem.click()
                    time.sleep(1)

                log.info('\nClicking on Ping button.')
                driver.find_element_by_id('btnPing').click()
                time.sleep(2)

                log.info(banner('Checking ping response.'))
                break_loop = False
                timeout=time.time() + 60*2
                while timeout>time.time():
                    try:
                        time.sleep(1)
                        log.info('Waiting for resp_elems.')
                        resp_elems = driver.find_elements_by_xpath('//div[@id="pingwindow"]//div[contains(@class, "x-grid3-cell-inner")]')
                        ping_response = [resp_elem.text for resp_elem in resp_elems if resp_elem.is_displayed()]
                        if 'Running' not in ping_response:
                            for i in range(int(len(ping_response)/4)):
                                log.info(ping_response[i*4:i*4+4:])
                                far_response = ping_response[i*4:i*4+4:]
                                eid = far_response[0].split('\n')[0]
                                far_response.append(far_response[0].split('\n')[1].split('( ')[1].split(' )')[0])
                                ping_result[eid] = far_response[1:]
                            break_loop = True
                        if break_loop: break
                    except Exception as e: pass

                log.info('Click on close button.')
                driver.execute_script('return $("#pingwindow .x-tool-close:visible")[0]').click()
                time.sleep(1)
                
                check_elems = driver.find_elements_by_xpath('//td[contains(@class, "x-grid3-td-checker")]/div/div')
                log.info('Unchecking checkboxes of the given devices.')
                for device_eid in device_eids:
                    her_elem = driver.find_element_by_id('netElementGrid').find_element_by_xpath('//a[contains(text(),"%s")]'%device_eid)
                    check_elem = her_elem.find_elements_by_xpath('../../../td')[0].find_element_by_xpath('div/div')
                    check_elem.click()
                    time.sleep(1)
        except Exception as e:
            log.error(e)
            driver_utils.save_screenshot()
            driver.refresh()

        log.info('Ping Response for %s\n%s'%(device_eids, json.dumps(ping_result, indent=4, sort_keys=True)))
        return ping_result

    def traceroute(self, device_eids=None, traceroute_from_far=True):

        driver = self.driver
        driver_utils = self.driver_utils
        trace_route_result = {}

        try:
            if not traceroute_from_far:
                device_eid=device_eids[0]
                eid_element = driver.find_element_by_xpath(
                    '//a[contains(@href, "javascript:cgms.mainPnl.loadIframe") and contains(text(), "%s")]'%device_eid)
                log.info('Waiting for loading device info.')
                timeout=time.time() + 60*2
                while timeout>time.time():
                    eid_element.click()
                    time.sleep(2)
                    eid_header = driver.execute_script(
                        'return $("iframe").contents().find("#device-detail-title:visible").text()')
                    if eid_header==device_eid: break

                log.info('\nClicking on Traceroute button.')
                driver.execute_script('$("iframe").contents().find("#trace_route").click()')
                time.sleep(2)

                log.info(banner('Checking Traceroute response.'))
                timeout=time.time() + 60*2
                while timeout>time.time():
                    try:
                        time.sleep(1)
                        log.info('Waiting for resp_elems.')
                        trace_route_response = driver.execute_script('function trace_route_response(){\
                                a=[];\
                                $.each($("iframe").contents().find("#pingTracerouteWindow .x-grid3-cell-inner"), function(i,e){\
                                    a.push(e.textContent);\
                                });\
                                return a;\
                                }\
                              return trace_route_response();')
                        if 'Running' not in trace_route_response:
                            for i in range(int(len(trace_route_response)/4)):
                                log.info(trace_route_response[i*4:i*4+4:])
                                far_response = trace_route_response[i*4:i*4+4:]
                                trace_route_result[far_response[0]] = far_response[1:]
                            break
                    except Exception as e: pass

                log.info('\nClick on close button.')
                driver.execute_script('$("iframe").contents().find("#pingTracerouteWindow .x-tool-close:visible")[0].click()')
                time.sleep(1)
                log.info('\nClicking on "Back"')
                driver.execute_script('$("iframe").contents().find("a[onclick^=\'cgms.mainPnl.loadIframeBack\'").click()')
                time.sleep(1)
            else:
                check_elems = driver.find_elements_by_xpath('//td[contains(@class, "x-grid3-td-checker")]/div/div')
                log.info('Clicking checkboxes of the given devices.')
                for device_eid in device_eids:
                    her_elem = driver.find_element_by_id('netElementGrid').find_element_by_xpath('//a[contains(text(),"%s")]'%device_eid)
                    check_elem = her_elem.find_elements_by_xpath('../../../td')[0].find_element_by_xpath('div/div')
                    check_elem.click()
                    time.sleep(1)

                log.info('\nClicking on Traceroute button.')
                driver.find_element_by_id('btnTraceroute').click()
                time.sleep(2)

                log.info(banner('Checking Traceroute response.'))
                timeout=time.time() + 60*2
                while timeout>time.time():
                    try:
                        time.sleep(1)
                        log.info('Waiting for resp_elems.')
                        resp_elems = driver.find_elements_by_xpath('//div[@id="pingTracerouteWindow"]//div[contains(@class, "x-grid3-cell-inner")]')
                        trace_route_response = [resp_elem.text for resp_elem in resp_elems if resp_elem.is_displayed()]
                        if 'Running' not in trace_route_response:
                            for i in range(int(len(trace_route_response)/4)):
                                log.info(trace_route_response[i*4:i*4+4:])
                                far_response = trace_route_response[i*4:i*4+4:]
                                trace_route_result[far_response[0]] = far_response[1:]
                            break
                    except Exception as e: pass

                log.info('Click on close button.')
                driver.execute_script('return $("#pingTracerouteWindow .x-tool-close:visible")[0]').click()
                time.sleep(1)

                check_elems = driver.find_elements_by_xpath('//td[contains(@class, "x-grid3-td-checker")]/div/div')
                log.info('Unchecking checkboxes of the given devices.')
                for device_eid in device_eids:
                    her_elem = driver.find_element_by_id('netElementGrid').find_element_by_xpath('//a[contains(text(),"%s")]'%device_eid)
                    check_elem = her_elem.find_elements_by_xpath('../../../td')[0].find_element_by_xpath('div/div')
                    check_elem.click()
                    time.sleep(1)
        except Exception as e:
            log.error(e)
            driver_utils.save_screenshot()
            driver.refresh()

        log.info('trace_route_result: %s'%json.dumps(trace_route_result, indent=4, sort_keys=True))
        return trace_route_result

    def add_devices(self, file_name=''):
        '''
        Method to click on 'Add Devices' operation.

        :param opertaion: Name of the operation button to click
        :type opertaion: str
        '''
        driver = self.driver
        driver_utils = self.driver_utils
        operation_completed = False
        log.info(banner('Performing "Add Devices" with file: %s'%(file_name)))

        try:
            log.info('Clicking "Add Devices".')
            driver.find_element_by_id('addDevicesButton').click()
            time.sleep(2)
            file_input = driver.find_element_by_xpath('//input[@id="formaddfilefile"]')
            file_input.send_keys(file_name)
            time.sleep(1)

            invalid_icon = driver.execute_script('return $("#x-form-el-form-add-file .x-form-invalid-icon").css("visibility")')
            if invalid_icon=='visible': raise Exception('Please provide a valid file name.')
            time.sleep(2)

            log.info('Clicking on Add button.')
            driver.find_element_by_xpath('//div[@id="addForm"]/.//button[contains(text(), "Add")]').click()
            time.sleep(2)

            timeout = time.time() + 60*10
            while timeout>time.time():
                add_devices_loading = driver.execute_script('return $("#add_devices_loading")[0].style.visibility=="visible"?true:false')
                log.info('add_devices_loading: %s'%add_devices_loading)
                if add_devices_loading:
                    time.sleep(3)
                    log.info('Waiting for file upload.')
                else: break

            time.sleep(1)
            failure_popup = driver.execute_script('return $(".x-window-dlg").css("visibility")')
            failure_message = driver.execute_script('return $(".x-window-dlg .x-window-header-text").text()')
            if failure_popup=='visible':
                log.error('failure_message: %s'%failure_message)
                driver.execute_script('$(".x-btn-text:contains(\'OK\')").click()')
                time.sleep(1)
                driver.execute_script('$(".x-btn-text:contains(\'Close\')").click()')
                time.sleep(1)
                return operation_completed

            add_dev_status = driver.find_element_by_xpath('//div[contains(text(), "Add Devices ")]').text
            if 'Failed' in add_dev_status:
                driver_utils.save_screenshot()
            if 'Completed' in add_dev_status:
                operation_completed = True

            time.sleep(1)
            log.info('Closing "Add Devices" popup.')
            driver.execute_script('$(".x-btn-text:contains(\'Close\')").click()')
            time.sleep(1)
        except Exception as e:
            log.error(e)
            driver_utils.save_screenshot()

        driver_utils.wait_for_loading()
        log.info('Add Operation for %s is : %s'%(file_name, operation_completed))
        return operation_completed

    def refresh_metrics(self, device_eid):

        driver = self.driver
        driver_utils = self.driver_utils
        refresh_metrics = {}

        try:
            search_input = driver.execute_script('return $("input.x-box-item:visible")[0]')
            search_input.clear()
            time.sleep(1)
            log.info('Entering the Search Query: %s'%('eid:' + device_eid))
            search_input.send_keys('eid:' + device_eid)
            time.sleep(1)
            log.info('Clicking on the Search Devices button.')
            driver.execute_script('return $("table.fa-search:visible")[0]').click()
            time.sleep(2)

            log.info('Clicking on the given device eid.')
            eid_element = driver.find_element_by_xpath('//a[contains(@href, "javascript:cgms.mainPnl.loadIframe") and contains(text(), "%s")]'%device_eid)
            log.info('Waiting for loading device info.')
            time.sleep(10)
            timeout=time.time() + 60*2
            while timeout>time.time():
                eid_element.click()
                time.sleep(2)
                eid_header = driver.execute_script('return $("iframe").contents().find("#device-detail-title:visible").text()')
                if eid_header==device_eid: break

            log.info(('Clicking on "Refresh Metrics".'))
            driver.execute_script('$("iframe").contents().find("#centerMainPanelCard").find("#refresh_metrics")[0].click()')
            time.sleep(5)

            timeout=time.time() + 60*2
            while timeout>time.time():
                status = driver.execute_script('return $("iframe").contents().find("#pingTracerouteWindow").find(".x-grid3-col-commandStatus").text()')
                if status=='Completed successfully' or status=='Failed': break
                log.info('Waiting for the metrics refresh.')
                time.sleep(3)

            started_at = driver.execute_script('return $("iframe").contents().find("#pingTracerouteWindow").find(".x-grid3-col-commandStartedAt").text()')
            device_ip = driver.execute_script('return $("iframe").contents().find("#pingTracerouteWindow").find(".x-grid3-col-ipAddress").text()')
            status = driver.execute_script('return $("iframe").contents().find("#pingTracerouteWindow").find(".x-grid3-col-commandStatus").text()')
            result = driver.execute_script('return $("iframe").contents().find("#pingTracerouteWindow").find(".x-grid3-col-response").text()')

            refresh_metrics['started_at'] = started_at
            refresh_metrics['device_ip'] = device_ip
            refresh_metrics['status'] = status
            refresh_metrics['result'] = result

            log.info('Closing popup window.')
            driver.execute_script('$.each($("iframe").contents().find("#pingTracerouteWindow").find(":button"), function(idx, button){if(button.textContent=="Close"){button.click()}})')
            time.sleep(1)
            driver.execute_script('$("iframe").contents().find("a[onclick^=\'cgms.mainPnl.loadIframeBack\'").click()')
            time.sleep(1)
        except Exception as e:
            log.error(e)

        log.info('Refresh Metrics for eid: %s\n%s'%(device_eid, json.dumps(refresh_metrics, indent=4, sort_keys=True)))
        return refresh_metrics

    def more_actions(self, opertaion):
        '''
        Method to click on 'More Actions' operation.

        :param opertaion: Name of the operation button to click
        :type opertaion: str
        '''
        driver = self.driver
        driver.find_element_by_xpath('//div[@id="netElementGrid"]//button[contains(text(),"More Actions")]')
        if opertaion == 'work_order':
            driver.find_element_by_id('btnWorkOrder').click()
        elif opertaion == 'refresh_mesh_key':
            driver.find_element_by_id('btnRefreshRouterMeshKey').click()
        elif opertaion == 'block_mesh_keys':
            driver.find_element_by_id('btnBlockMeshDevice').click()
        elif opertaion == 'remove_devices':
            driver.find_element_by_id('btnRemoveDevices').click()
        elif opertaion == 'reset_bootstrap_state':
            driver.find_element_by_id('btnResetBsState').click()

    def device_level_navigation(self, device_eid):
        '''
        Method to get Events info of a given router eid.

        :param router_eid: eid of the router to check the device info
        :type router_eid: str
        '''
        driver = self.driver
        driver_utils = self.driver_utils
        navigated_to_device = False

        try:
            search_input = driver.execute_script('return $("input.x-box-item:visible")[0]')
            search_input.clear()
            time.sleep(1)
            log.info('Entering the Search Query: %s'%('eid:' + device_eid))
            search_input.send_keys('eid:' + device_eid)
            time.sleep(1)
            log.info('Clicking on the Search Devices button.')
            driver.execute_script('return $("table.fa-search:visible")[0]').click()
            time.sleep(2)
            driver_utils.ignore_flash_error()

            log.info('Clicking on the device eid.')
            eid_element = driver.find_element_by_xpath(
                '//a[contains(@href, "javascript:cgms.mainPnl.loadIframe") and contains(text(), "%s")]'%device_eid)
            log.info('Waiting for loading device info.')

            timeout=time.time() + 60*2
            while timeout>time.time():
                eid_element.click()
                time.sleep(2)
                eid_header = driver.execute_script('return $("iframe").contents().find("#device-detail-title:visible").text()')
                if eid_header==device_eid:
                    driver_utils.wait_for_loading()
                    navigated_to_device = True
                    break
        except Exception as e:
            driver_utils.save_screenshot()
            log.error('Unable to navigate to device level.')

        return navigated_to_device

    def device_details(self, router_eid):
        '''
        Method to get device details of a given router eid.

        :param router_eid: eid of the router to check the details
        :type router_eid: str
        '''
        driver = self.driver
        driver.refresh()
        time.sleep(5)
        #router_elem = driver.find_element_by_id('netElementGrid').find_element_by_xpath('//a[contains(text(),"%s")]'%router_eid)
        #router_elem_tds = router_elem.find_elements_by_xpath('../../../td/div')
        try:
            device_detail_tds = [ele.text for ele in \
                                 driver.find_element_by_id('netElementGrid') \
                                 .find_element_by_xpath('//a[contains(text(),"%s")]'%router_eid) \
                                 .find_elements_by_xpath('../../../td/div')[2:]]
            log.info('device_detail_tds: %s'%(device_detail_tds,))

            meter_id = device_detail_tds[0]
            last_heard = device_detail_tds[2]
            category = device_detail_tds[3]
            dev_type = device_detail_tds[4]
            function = device_detail_tds[5]
            pan_id = device_detail_tds[6]
            firmware = device_detail_tds[7]
            ip = device_detail_tds[8]
            open_issues = device_detail_tds[9]
            labels = device_detail_tds[10]
            latitude = device_detail_tds[11]
            longitude = device_detail_tds[12]

            router_elem = driver.find_element_by_id('netElementGrid').find_element_by_xpath('//a[contains(text(),"%s")]'%router_eid)
            status = router_elem.find_elements_by_xpath('../../../td/div')[3].find_element_by_xpath('..').get_attribute('class')
            if 'displayicon-up' in status:
                status='device is UP'
            elif 'displayicon-down' in status:
                status='device is DOWN'

            log.info(
                ' meter_id: %s\n status: %s\n last_heard: %s\n category: %s\n dev_type: %s\n function: %s\n pan_id: %s\n firmware: %s\n ip: %s\n open_issues: %s\n labels: %s\n latitude: %s\n latitude:%s'%
                (meter_id, status, last_heard, category, dev_type, function, pan_id, firmware, ip, open_issues, labels, latitude, longitude)
                )
        except StaleElementReferenceException as e:
            log.error(e)
        except AssertionError as e:
            log.error(e)

    def config_properties(self, device_eid):
        
        driver = self.driver
        driver_utils = self.driver_utils
        config_properties = {}

        try:
            search_input = driver.execute_script('return $("input.x-box-item:visible")[0]')
            search_input.clear()
            time.sleep(1)
            log.info('Entering the Search Query: %s'%('eid:' + device_eid))
            search_input.send_keys('eid:' + device_eid)
            time.sleep(1)
            log.info('Clicking on the Search Devices button.')
            driver.execute_script('return $("table.fa-search:visible")[0]').click()
            time.sleep(2)

            log.info('Clicking on the device eid.')
            eid_element = driver.execute_script('return \
                $("a").filter(function(){return $(this).text()==="%s"})[0]'%device_eid)
            eid_element.click()
            log.info('Waiting for loading device info.')
            timeout=time.time() + 60*2
            while timeout>time.time():
                eid_header = driver.execute_script(
                    'return $("iframe").contents().find("#device-detail-title:visible").text()')
                if eid_header==device_eid: break
                time.sleep(2)

            log.info('\nNavigating to Config Properties tab')
            driver.switch_to_frame(driver.find_element_by_xpath("//iframe[@id='iframeMainPanelCardEl']"))
            driver.find_element_by_xpath("//li[@id='elementTabs__configPropertiesTab']//a[.='Config Properties']").click()
            time.sleep(2)
            driver.switch_to_default_content()
            # self.nav_dev_tab('elementTabs__configPropertiesTab')
            #
            # config_properties = driver.execute_script('\
            #                             function conf_prop(){\
            #                                 a={};\
            #                                 $.each($("iframe").contents().find(".properties:visible").find("td.key:visible"), function(i,e){\
            #                                     if(e.nextElementSibling != null)\
            #                                         a[e.textContent.trim()]=e.nextElementSibling.textContent.trim();\
            #                                 });\
            #                                 return a;\
            #                             }\
            #                             return conf_prop();')
            # log.info('\nClicking on "Back"')
            # driver.execute_script('$("iframe").contents().find("#backToList").click()')
        except Exception as e:
            log.error(e)
            driver_utils.save_screenshot()
        
        log.info('config_properties: %s'%json.dumps(config_properties, indent=4, sort_keys=True))
        return config_properties

    def device_info(self, device_eid):
        '''
        Method to get device info of a given router eid.

        :param router_eid: eid of the router to check the device info
        :type router_eid: str
        '''
        driver = self.driver
        driver_utils = self.driver_utils
        device_info={}

        try:
            search_input = driver.execute_script('return $("input.x-box-item:visible")[0]')
            search_input.clear()
            time.sleep(1)
            log.info('Entering the Search Query: %s'%('eid:' + device_eid))
            search_input.send_keys('eid:' + device_eid)
            time.sleep(1)
            log.info('Clicking on the Search Devices button.')
            driver.execute_script('return $("table.fa-search:visible")[0]').click()
            time.sleep(2)

            log.info('Clicking on the device eid.')
            eid_element = driver.find_element_by_xpath(
                '//a[contains(@href, "javascript:cgms.mainPnl.loadIframe") and contains(text(), "%s")]'%device_eid)
            log.info('Waiting for loading device info.')
            timeout=time.time() + 60*2
            while timeout>time.time():
                eid_element.click()
                time.sleep(2)
                eid_header = driver.execute_script('return $("iframe").contents().find("#device-detail-title").text()')
                log.info(eid_header)
                if eid_header==device_eid: break

            device_info = driver.execute_script('\
                                function info(){\
                                    a={};\
                                    $.each($("iframe").contents().find("td .key:visible"), function(i,e){\
                                        a[e.textContent.trim()]=[];\
                                        $.each(e.parentElement.children, function(j,f){\
                                            if(j==0) return;\
                                            a[e.textContent.trim()].push(f.textContent.trim());\
                                        });\
                                    });\
                                    return a;\
                                    }\
                                return info();')
            log.info('\nClicking on "Back"')
            driver.execute_script('$("iframe").contents().find("#backToList").click()')
            time.sleep(1)
        except Exception as e: log.error(e)

        log.info('device_info: %s'%json.dumps(device_info, indent=4, sort_keys=True))
        return device_info

    def event_info_by_time(self, device_eid, **kwargs):
        '''
        Method to get Events info of a given router eid.

        :param router_eid: eid of the router to check the device info
        :type router_eid: str
        '''
        driver = self.driver
        driver_utils = self.driver_utils
        event_info = {}

        try:
            search_input = driver.execute_script('return $("input.x-box-item:visible")[0]')
            search_input.clear()
            time.sleep(1)
            log.info('Entering the Search Query: %s' % ('eid:' + device_eid))
            search_input.send_keys('eid:' + device_eid)
            time.sleep(1)
            log.info('Clicking on the Search Devices button.')
            driver.execute_script('return $("table.fa-search:visible")[0]').click()
            time.sleep(2)

            log.info('Clicking on the device eid: %s.' % device_eid)
            eid_element = driver.find_element_by_xpath(
                '//a[contains(@href, "javascript:cgms.mainPnl.loadIframe") and contains(text(), "%s")]' % device_eid)
            log.info('Waiting for loading device info.')
            time.sleep(5)
            timeout = time.time() + 60 * 2
            while timeout > time.time():

                eid_element.click()
                time.sleep(2)
                eid_header = driver.execute_script(
                    'return $("iframe").contents().find("#device-detail-title:visible").text()')
                if eid_header == device_eid: break

            self.nav_dev_tab('events')

            driver.switch_to_frame(driver.find_element_by_xpath("//iframe[@id='iframeMainPanelCardEl']"))
            log.info('Check "Lables Combo" drop down.')
            labels_combo = driver.find_element_by_xpath('//input[@id="labelsCombo"]')
            labels_dropdown = labels_combo.find_element_by_xpath('following-sibling::img')

            labels_dropdown.click()
            time.sleep(1)
            driver.find_element_by_xpath(
                '//div[starts-with(@class, "x-combo-list-item") and contains(text(), "Last 15 minutes")]').click()
            time.sleep(3)
            curr_slection = labels_combo.get_attribute('value')
            log.info('curr_slection: %s' % (str(curr_slection)))

            sort_by = kwargs.get('sort_by', None)
            sort_order = kwargs.get('sort_order', None)

            if sort_by:
                column_dict = {
                    'time': 'x-grid3-hd-eventTime',
                    'name': 'x-grid3-hd-eventTypeName',
                    'severity': 'x-grid3-hd-severity',
                    'message': 'x-grid3-hd-eventMessage'
                }

                header_elem = column_dict[sort_by]
                old_sort_order = driver.execute_script('return \
                    $("iframe").contents().find(".%s").parent().attr("class")' % header_elem)

                if sort_order not in old_sort_order:
                    time.sleep(1)
                    driver.execute_script('return $("iframe").contents().find(".%s")[0].click()' % header_elem)
                    driver_utils.wait_for_loading()
                    time.sleep(1)

                new_sort_order = driver.execute_script('return \
                    $("iframe").contents().find(".%s").parent().attr("class")' % header_elem)
                log.info('old_sort_order: %s, new_sort_order: %s' %
                         (old_sort_order, new_sort_order))
            count = 2
            timeout = time.time() + 60 * 10
            while timeout > time.time():
                time.sleep(5)
                log.info('\nClicking on "Refresh" button.')
                refresh_button = driver_utils.get_visible_button_by_class('x-tbar-loading-blue')
                if refresh_button:
                    refresh_button.click()
                else:
                    log.error('Refresh button not visible.')
                time.sleep(10)
                #if count <= len(event_info['message']): break
                #if "Device is registering" in event_info['message']: break
                    #self.failed('Device registration Event not found in events %s' % ir530_eid)

            log.info('\nClicking on "Back"')
            driver.switch_to_default_content()
            event_data = driver.execute_script('\
                                function a(){\
                                    a=[];\
                                    $.each($("iframe").contents().find(".x-grid3-row:visible").find(".x-grid3-cell:visible"),\
                                        function(i,e){a.push(e.textContent)});\
                                    return a;\
                                }\
                                return a();\
                            ')

            event_info = {
                'time': event_data[0::4],
                'event_name': event_data[1::4],
                'severity': event_data[2::4],
                'message': event_data[3::4],
            }
            log.info("length of events %s" % len(event_info['message']))
            driver.execute_script('$("iframe").contents().find("#backToList").click()')
            time.sleep(1)
        except Exception as e:
            log.error(e)

        log.info('event_info: %s' % json.dumps(event_info, indent=4, sort_keys=True))
        return event_info

    def event_info(self, device_eid, **kwargs):
        '''
        Method to get Events info of a given router eid.

        :param router_eid: eid of the router to check the device info
        :type router_eid: str
        '''
        driver = self.driver
        driver_utils = self.driver_utils
        event_info={}

        try:
            search_input = driver.execute_script('return $("input.x-box-item:visible")[0]')
            search_input.clear()
            time.sleep(1)
            log.info('Entering the Search Query: %s'%('eid:' + device_eid))
            search_input.send_keys('eid:' + device_eid)
            time.sleep(1)
            log.info('Clicking on the Search Devices button.')
            driver.execute_script('return $("table.fa-search:visible")[0]').click()
            time.sleep(2)

            log.info('Clicking on the device eid: %s.'%device_eid)
            eid_element = driver.find_element_by_xpath(
                '//a[contains(@href, "javascript:cgms.mainPnl.loadIframe") and contains(text(), "%s")]'%device_eid)
            log.info('Waiting for loading device info.')

            timeout=time.time() + 60*2
            while timeout>time.time():
                eid_element.click()
                time.sleep(2)
                eid_header = driver.execute_script('return $("iframe").contents().find("#device-detail-title:visible").text()')
                if eid_header==device_eid: break

            self.nav_dev_tab('events')
            sort_by = kwargs.get('sort_by', None)
            sort_order = kwargs.get('sort_order', None)

            if sort_by:
                column_dict = {
                    'time': 'x-grid3-hd-eventTime',
                    'name': 'x-grid3-hd-eventTypeName',
                    'severity': 'x-grid3-hd-severity',
                    'message': 'x-grid3-hd-eventMessage'
                }
                
                header_elem = column_dict[sort_by]
                old_sort_order = driver.execute_script('return \
                    $("iframe").contents().find(".%s").parent().attr("class")'%header_elem)

                if sort_order not in old_sort_order:
                    time.sleep(1)
                    driver.execute_script('return $("iframe").contents().find(".%s")[0].click()'%header_elem)
                    driver_utils.wait_for_loading()
                    time.sleep(1)

                new_sort_order = driver.execute_script('return \
                    $("iframe").contents().find(".%s").parent().attr("class")'%header_elem)
                log.info('old_sort_order: %s, new_sort_order: %s'%
                        (old_sort_order, new_sort_order))

            event_data = driver.execute_script('\
                function a(){\
                    a=[];\
                    $.each($("iframe").contents().find(".x-grid3-row:visible").find(".x-grid3-cell:visible"),\
                        function(i,e){a.push(e.textContent)});\
                    return a;\
                }\
                return a();\
            ')

            event_info = {
                'time': event_data[0::4],
                'event_name': event_data[1::4],
                'severity': event_data[2::4],
                'message': event_data[3::4],
            }

            log.info('\nClicking on "Back"')
            driver.execute_script('$("iframe").contents().find("#backToList").click()')
            time.sleep(1)
        except Exception as e: log.error(e)

        log.info('event_info: %s'%json.dumps(event_info, indent=4, sort_keys=True))
        return event_info

    def edit_view(self, **kwargs):
        driver = self.driver
        driver_utils = self.driver_utils

        view_edited = False
        active = kwargs.get('active', False)
        column_names = kwargs.get('column_names', [])
        arrow = 'left2' if active else 'right2'
        try:
            tools_container = driver.execute_script('return $(".toolsContainer:visible")[0]')
            tools_container.click()
            time.sleep(1)

            for column in column_names:
                column_ele = driver.execute_script('return $("em:contains(\'%s\')")[0]'%column)
                column_ele.click()
                time.sleep(1)
                arrow_ele = driver.execute_script('return $.find(\'img[src$="/ext/ux/images/%s.gif"]\')[0]'%arrow)
                log.info('Clicking on the %s arrow.'%arrow)
                arrow_ele.click()
                time.sleep(1)
        
            log.info('Clicking on the Save button.')
            save_button = driver.execute_script('return $(".fa-floppy-o:visible")[0]')
            save_button.click()
            time.sleep(1)
            view_edited = True
        except Exception as e:
            log.error(e)
            driver_utils.save_screenshot()

        log.info(banner('View with column_names: %s is edited: %s'%(column_names, view_edited)))
        return view_edited

    def mesh_routing_tree(self, device_eid):
        '''
        Method to get Mesh Routing Tree info of a given router eid.

        :param router_eid: eid of the router to check the device info
        :type router_eid: str
        '''
        driver = self.driver
        driver_utils = self.driver_utils
        mesh_routing_tree_info={}

        try:
            search_input = driver.execute_script('return $("input.x-box-item:visible")[0]')
            search_input.clear()
            time.sleep(1)
            log.info('Entering the Search Query: %s'%('eid:' + device_eid))
            search_input.send_keys('eid:' + device_eid)
            time.sleep(1)
            log.info('Clicking on the Search Devices button.')
            driver.execute_script('return $("table.fa-search:visible")[0]').click()
            time.sleep(2)

            log.info('Clicking on the device eid.')
            eid_element = driver.find_element_by_xpath(
                '//a[contains(@href, "javascript:cgms.mainPnl.loadIframe") and contains(text(), "%s")]'%device_eid)
            log.info('Waiting for loading device info.')

            timeout=time.time() + 60*2
            while timeout>time.time():
                eid_element.click()
                time.sleep(2)
                eid_header = driver.execute_script('return $("iframe").contents().find("#device-detail-title:visible").text()')
                if eid_header==device_eid: break

            self.nav_dev_tab('mesh_routing_tree')
            mesh_data = driver.execute_script('\
                function a(){\
                    a=[];\
                    $.each($("iframe").contents().find(".x-treegrid-col:visible"),\
                        function(i,e){a.push(e.textContent)});\
                    return a;\
                }\
                return a();\
            ')

            mesh_routing_tree_info = {
                'eid': mesh_data[0],
                'name': mesh_data[1],
                'status': mesh_data[2],
                'type': mesh_data[3],
                'ip': mesh_data[4],
                'last_heard': mesh_data[5],
                'meter_id': mesh_data[6],
                'transmit_speed': mesh_data[7],
                'packet_drops': mesh_data[8],
                'receive_speed': mesh_data[9],
                'rpl_hops': mesh_data[10],
                'rpl_link_cost': mesh_data[11],
                'rpl_path_cost': mesh_data[12],
                'rsi': mesh_data[13],
                'reverse_rsi': mesh_data[14],
                'link_type': mesh_data[15]
            }

            log.info('\nClicking on "Back"')
            driver.execute_script('$("iframe").contents().find("#backToList").click()')
            time.sleep(1)
        except Exception as e: log.error(e)

        log.info('mesh_routing_tree_info: %s'%json.dumps(mesh_routing_tree_info, indent=4, sort_keys=True))
        return mesh_routing_tree_info

    def select_devices(self, router_eids):
        '''
        Method to select the given devices.

        :param router_eids: list of eids to select
        :type router_eids: list
        '''
        driver = self.driver
        try:
            for router_eid in router_eids:
                #Getting anchor element with router_eid under the element with id:"netElementGrid".
                router_elem = driver.find_element_by_id('netElementGrid').find_element_by_xpath('//a[contains(text(),"%s")]'%router_eid)
                log.info('Click on the device checkbox from netElementGrid')
                #Getting the first td element of this tr row.
                check_box_td = router_elem.find_element_by_xpath('../../..').find_elements_by_tag_name('td')[0]
                #Click the checkbox of the router_eid.
                check_box_td.find_element_by_xpath('div/div').click()
        except (NoSuchElementException, ElementNotVisibleException) as e:
            log.error('Unable to find the element: %s' % e)

    def access_device(self, router_eid):
        '''
        Method to access the given device.

        :param router_eid: eid of the device.
        :type router_eid: str
        '''
        driver = self.driver
        try:
            #Getting router element with router_eid under the element with id:"netElementGrid".
            router_elem = driver.find_element_by_id('netElementGrid').find_element_by_xpath('//a[contains(text(),"%s")]'%router_eid)
            log.info('Click on the device from netElementGrid')
            router_elem.click()
        except (NoSuchElementException, ElementNotVisibleException) as e:
            log.error('Unable to find the element: %s' % e)

    def search_devices(self, search_field, **kwargs):
        '''
        Allows the user to search for devices with the given fields

        :param search_field: Search Field name
        :type search_field: str
        :param search_value: Search value
        :type search_value: str

        Search Field choices :-
            * 'Label'
            * 'Config Group'
            * 'Firmware Group'
            * 'Groups'
            * 'Tunnel Groups'
            * 'Category'
            * 'EID'
            * 'Firmware'
            * 'Function'
            * 'Hardware ID'
            * 'IP'
            * 'Last Heard'
            * 'Latitude'
            * 'Longitude'
            * 'Model Number'
            * 'Name'
            * 'Serial Number'
            * 'Status'
            * 'Type'
            * 'Up time'

        Usage:

        >>> field_devices = ui_common_utils.FieldDevices(driver)
        >>> field_devices.search_devices('Type', 'cgr1000')
        '''

        driver = self.driver
        driver_utils = self.driver_utils
        log.info('Clearing exiting search filter content.')
        search_box = driver.execute_script('return $("input.x-box-item:visible")[0]')
        search_box.clear()

        log.info('Clicking on Hide Filter button if exists.')
        driver.execute_script('if($(\'a:contains("Hide Filters")\').length>0)$(\'a:contains("Hide Filters")\')[0].click()')
        time.sleep(1)

        log.info('Clicking on Show Filter button.')
        driver.find_element_by_xpath('//a[contains(text(), "Show Filter")]').click()

        try:
            log.info('Selecting search field')
            driver.find_element_by_xpath('//input[contains(@id, "labelsCombofilterCtrl")]//following-sibling::img').click()
            time.sleep(2)
            dropdown_elements = driver.find_elements_by_xpath('//div[starts-with(@class, "x-combo-list-item") and contains(text(), "%s")]'%search_field)
            for dropdown_element in dropdown_elements:
                if dropdown_element.text == search_field:
                    dropdown_element.click()
                    break
            time.sleep(2)

            log.info('Selecting search value')
            search_value = kwargs.get('search_value', '')
            log.info('Entering "%s" values'%search_field)

            if search_field in ['Groups', 'EID', 'Firmware', 'Hardware ID', 'IP', 'Model Number', 'Name', 'Serial Number']:
                driver.find_element_by_xpath('//input[contains(@id, "stringfilterCtrl")]').send_keys(search_value)
                time.sleep(2)
            
            elif search_field in ['Latitude', 'Longitude', 'Up time']:
                inputs = driver.find_elements_by_xpath('//div[contains(@class, "x-box-inner")]/input[starts-with(@class,"x-form-text")]')
                start_input = inputs[1]
                stop_input = inputs[2]

                start_value = kwargs.get('start_value', '')
                end_value = kwargs.get('end_value', '')

                start_input.clear()
                start_input.send_keys(start_value)
                time.sleep(1)
                stop_input.clear()
                stop_input.send_keys(end_value)
                time.sleep(1)
                search_box.click()

            elif search_field == ['Last Heard', 'Last GPS Heard']:
                input_dates = driver.find_elements_by_xpath('//td[contains(@class, "ux-datetime-date")]')[1:]
                start_date = input_dates[0].find_element_by_xpath('div/input')
                end_date = input_dates[1].find_element_by_xpath('div/input')
                # input_times = driver.find_elements_by_xpath('//td[contains(@class, "ux-datetime-time")]')[1:]
                # start_time = input_times[0].find_element_by_xpath('div/input')
                # end_time = input_times[1].find_element_by_xpath('div/input')
                start_date_value = kwargs.get('start_date', '')
                end_date_value = kwargs.get('end_date', '')

                start_date.clear()
                start_date.send_keys(start_date_value)
                time.sleep(1)
                end_date.clear()
                end_date.send_keys(end_date_value)
                time.sleep(1)
                search_box.click()

            else:
                driver.find_element_by_xpath('//input[contains(@id, "combofilterCtrl")]//following-sibling::img').click()
                time.sleep(2)
                driver.find_element_by_xpath('//div[starts-with(@class, "x-combo-list-item") and contains(text(), "%s")]'%search_value).click()
                time.sleep(2)

            log.info('Adding the selected filter.')
            driver.find_element_by_xpath('//i[@class="fa fa-plus"]').click()
            time.sleep(2)

            log.info('Clicking on the Search Devices button.')
            driver.execute_script('return $("table.fa-search:visible")[0]').click()
            time.sleep(2)

        except Exception as e:
            driver_utils.save_screenshot()
            log.error(e)

        try:
            searched_values = driver.find_elements_by_xpath('//div[contains(@class, "x-grid3-body")]/div[starts-with(@class,"x-grid3-row")]')
            log.info(banner('Total devices with the search criteria "%s" : %d'%(search_field+':'+search_value, len(searched_values))))
        except Exception as e: log.error(e)

    def sort_fan_devices(self, sort_by, *args):

        driver = self.driver
        log.info('Sorting Devices by: %s'%sort_by)
        
        tab_ids = {
            'name': 'x-grid3-td-1',
            'meter_id': 'x-grid3-td-2',
            'status': 'x-grid3-td-3',
            'last_heard': 'x-grid3-td-4',
            'category': 'x-grid3-td-5',
            'type': 'x-grid3-td-6',
            'function': 'x-grid3-td-7',
            'pan_id': 'x-grid3-td-8',
            'firmware': 'x-grid3-td-9',
            'ip': 'x-grid3-td-10',
            'open_issues': 'x-grid3-td-11',
            'labels': 'x-grid3-td-12',
            'latitude': 'x-grid3-td-13',
            'longitude': 'x-grid3-td-14'
        }
        tab_id = tab_ids[sort_by]

        selected=''
        timeout = time.time()+60*2
        fan_span = driver.find_element_by_xpath('//a[@class="x-tree-node-anchor"]/span[contains(text(), "All FAN Devices")]')

        while 'x-tree-selected' not in selected:
            selected = fan_span.find_element_by_xpath('../..').get_attribute('class')
            if time.time()>timeout: break
            log.info('Click on "All FAN Devices."')
            fan_span.click()
            time.sleep(2)

        log.info('Click on "Inventory" tab.')
        self.nav_tab('inventory')
        time.sleep(1)

        try:
            tab_ele = driver.find_element_by_xpath('//tr[contains(@class, "x-grid3-hd-row")]/td[contains(@class,"%s")]'%tab_id)
            curr_sort = tab_ele.get_attribute('class')
            log.info('curr_sort: %s'%curr_sort)

            log.info('Clicking on %s tab.'%sort_by)
            tab_ele.click()
            time.sleep(1)
        except Exception as e: log.error(e)

    def sort_router_devices(self, sort_by, *args):

        driver = self.driver
        log.info('Sorting Devices by: %s'%sort_by)
        
        tab_ids = {
            'name': 'x-grid3-td-1',
            'status': 'x-grid3-td-2',
            'domain': 'x-grid3-td-3',
            'last_heard': 'x-grid3-td-4',
            'mesh_count': 'x-grid3-td-5',
            'firmware': 'x-grid3-td-6',
            'ip': 'x-grid3-td-7',
            'open_issues': 'x-grid3-td-8',
            'labels': 'x-grid3-td-9',
            'lat': 'x-grid3-td-10',
            'lon': 'x-grid3-td-11',
            'cell_bw': 'x-grid3-td-12',
            'eid': 'x-grid3-td-13',
            'type': 'x-grid3-td-14',
            'ver_incr': 'x-grid3-td-15'
        }
        tab_id = tab_ids[sort_by]

        selected=''
        timeout = time.time() + 60*2
        router_span = driver.find_element_by_xpath('//span[contains(text(), "ROUTER")]')
        while 'x-tree-selected' not in selected:
            selected = router_span.find_element_by_xpath('../..').get_attribute('class')
            if time.time()>timeout: break
            log.info('Click on "ROUTER" span.')
            router_span.click()
            time.sleep(1)
        
        log.info('Click on "Inventory" tab.')
        self.nav_tab('inventory')
        time.sleep(1)

        try:
            tab_ele = driver.find_element_by_xpath('//tr[contains(@class, "x-grid3-hd-row")]/td[contains(@class,"%s")]'%tab_id)
            curr_sort = tab_ele.get_attribute('class')
            log.info('curr_sort: %s'%curr_sort)

            log.info('Clicking on %s tab.'%sort_by)
            tab_ele.click()
            time.sleep(1)
        except Exception as e: log.error(e)

    def reboot(self, device_eid):

        driver = self.driver
        driver_utils = self.driver_utils
        reboot_response={}

        try:
            search_input = driver.execute_script('return $("input.x-box-item:visible")[0]')
            search_input.clear()
            time.sleep(1)
            log.info('Entering the Search Query: %s'%('eid:' + device_eid))
            search_input.send_keys('eid:' + device_eid)
            time.sleep(1)
            log.info('Clicking on the Search Devices button.')
            driver.execute_script('return $("table.fa-search:visible")[0]').click()
            time.sleep(2)

            log.info('Clicking on the device eid.')
            eid_element = driver.find_element_by_xpath(
                '//a[contains(@href, "javascript:cgms.mainPnl.loadIframe") and contains(text(), "%s")]'%device_eid)
            log.info('Waiting for loading device info.')
            timeout=time.time() + 60*2
            while timeout>time.time():
                eid_element.click()
                time.sleep(2)
                eid_header = driver.execute_script('return $("iframe").contents().find("#device-detail-title:visible").text()')
                if eid_header==device_eid: break

            has_reboot = driver.execute_script('return $("iframe").contents().find("#reboot_device").length>0 ? true : false')
            if not has_reboot: raise Exception('No Reboot button available.')

            log.info(('Clicking on "Reboot".'))
            driver.execute_script('return $("iframe").contents().find("#reboot_device")[0].click()')
            time.sleep(5)

            log.info(('Clicking on "Yes" button.'))
            driver.execute_script('return $("iframe").contents().find("button:contains(\'Yes\')")[0].click()')

            log.info('Verifying the reboot status.')
            timeout=time.time() + 60*2
            while timeout>time.time():
                reboot_status = driver.execute_script('return $("iframe").contents().find("#pingTracerouteWindow").find(".x-grid3-col-commandStatus").text()')
                log.info('reboot_status: %s'%reboot_status)
                if reboot_status in ['Completed successfully', 'Failed']: break
                log.info('Waiting for the reboot_status refresh.')
                time.sleep(5)

            response = driver.execute_script('function response(){\
                                a=[];\
                                $.each($("iframe").contents().find("#pingTracerouteWindow").find(".x-grid3-cell-inner"), function(i,e){\
                                    a.push(e.textContent);\
                                });\
                                return a;\
                                }\
                              return response();')

            reboot_response = {
                'started_at' : response[0],
                'device' : response[1],
                'status' : response[2],
                'result' : response[3]
            }

            log.info('Closing popup window.')
            driver.execute_script('return $("iframe").contents().find(".fa-close")[0].click()')
        except Exception as e:
            log.error(e)
            driver_utils.save_screenshot()

        log.info('reboot_response: %s'%json.dumps(reboot_response, indent=4, sort_keys=True))
        return reboot_response

    def sync_config_membership(self, device_eid):
        driver = self.driver
        driver_utils = self.driver_utils
        membership_synched = False

        try:
            search_input = driver.execute_script('return $("input.x-box-item:visible")[0]')
            search_input.clear()
            time.sleep(1)
            log.info('Entering the Search Query: %s'%('eid:' + device_eid))
            search_input.send_keys('eid:' + device_eid)
            time.sleep(1)
            log.info('Clicking on the Search Devices button.')
            driver.execute_script('return $("table.fa-search:visible")[0]').click()
            time.sleep(2)

            log.info('Clicking on the device eid.')
            eid_element = driver.find_element_by_xpath(
                '//a[contains(@href, "javascript:cgms.mainPnl.loadIframe") and contains(text(), "%s")]'%device_eid)
            log.info('Waiting for loading device info.')
            timeout=time.time() + 60*2
            while timeout>time.time():
                eid_element.click()
                time.sleep(2)
                eid_header = driver.execute_script('return $("iframe").contents().find("#device-detail-title:visible").text()')
                if eid_header==device_eid: break

            has_sync_conf_button = driver.execute_script(\
            'return $("iframe").contents().find("button:contains(\'Sync Config Membership\')").length>0 ? true : false')
            if not has_sync_conf_button: raise Exception('No "Synch Config Memenership" button available.')

            log.info(('Clicking on "Synch Config Memenership".'))
            driver.execute_script('return $("iframe").contents().find("button:contains(\'Sync Config Membership\')")[0].click()')
            time.sleep(5)

            log.info(('Clicking on "Yes" button.'))
            driver.execute_script('return $("iframe").contents().find("button:contains(\'Yes\')")[0].click()')
            time.sleep(2)

            popup = False
            timeout=time.time() + 60*2
            while timeout>time.time():
                popup = driver.execute_script('\
                return $("iframe").contents().find("td.x-hide-offsets").text().indexOf("OK")>0 ? false : true')
                if popup: break
                time.sleep(1)

            log.info(('Clicking on "OK" button.'))
            driver.execute_script('return $("iframe").contents().find("button:contains(\'OK\')")[0].click()')
            time.sleep(2)

            popup_header = driver.execute_script('return $("iframe").contents().find("span.x-window-header-text").text()')
            popup_message = driver.execute_script('return $("iframe").contents().find("span.ext-mb-text").text()')
            log.info('\npopup_header: %s\npopup_message: %s'%(popup_header, popup_message))
            if popup_header=='Success': membership_synched = True
        except Exception as e:
            driver_utils.save_screenshot()
            log.error(e)

        return membership_synched

    def sync_firmware_membership(self, device_eid):
        driver = self.driver
        driver_utils = self.driver_utils
        membership_synched = False

        try:
            search_input = driver.execute_script('return $("input.x-box-item:visible")[0]')
            search_input.clear()
            time.sleep(1)
            log.info('Entering the Search Query: %s'%('eid:' + device_eid))
            search_input.send_keys('eid:' + device_eid)
            time.sleep(1)
            log.info('Clicking on the Search Devices button.')
            driver.execute_script('return $("table.fa-search:visible")[0]').click()
            time.sleep(2)

            log.info('Clicking on the device eid.')
            eid_element = driver.find_element_by_xpath(
                '//a[contains(@href, "javascript:cgms.mainPnl.loadIframe") and contains(text(), "%s")]'%device_eid)
            log.info('Waiting for loading device info.')
            timeout=time.time() + 60*2
            while timeout>time.time():
                eid_element.click()
                time.sleep(2)
                eid_header = driver.execute_script('return $("iframe").contents().find("#device-detail-title:visible").text()')
                if eid_header==device_eid: break

            has_sync_firmware_button = driver.execute_script(\
            'return $("iframe").contents().find("button:contains(\'Sync Firmware Membership\')").length>0 ? true : false')
            if not has_sync_firmware_button: raise Exception('No "Synch Firmware Memenership" button available.')

            log.info(('Clicking on "Synch Firmware Memenership".'))
            driver.execute_script('return $("iframe").contents().find("button:contains(\'Sync Firmware Membership\')")[0].click()')
            time.sleep(5)

            log.info(('Clicking on "Yes" button.'))
            driver.execute_script('return $("iframe").contents().find("button:contains(\'Yes\')")[0].click()')
            time.sleep(2)

            popup = False
            timeout=time.time() + 60*2
            while timeout>time.time():
                popup = driver.execute_script('\
                return $("iframe").contents().find("td.x-hide-offsets").text().indexOf("OK")>0 ? false : true')
                if popup: break
                time.sleep(1)

            log.info(('Clicking on "OK" button.'))
            driver.execute_script('return $("iframe").contents().find("button:contains(\'OK\')")[0].click()')
            time.sleep(2)

            popup_header = driver.execute_script('return $("iframe").contents().find("span.x-window-header-text").text()')
            popup_message = driver.execute_script('return $("iframe").contents().find("span.ext-mb-text").text()')
            log.info('\npopup_header: %s\npopup_message: %s'%(popup_header, popup_message))
            if popup_header=='Success': membership_synched = True
        except Exception as e:
            driver_utils.save_screenshot()
            log.error(e)

        return membership_synched

    def erase_node_certificates(self, device_eid):
        driver = self.driver
        driver_utils = self.driver_utils
        erase_node_certificate_response = {}
        try:
            search_input = driver.execute_script('return $("input.x-box-item:visible")[0]')
            search_input.clear()
            time.sleep(1)
            log.info('Entering the Search Query: %s'%('eid:' + device_eid))
            search_input.send_keys('eid:' + device_eid)
            time.sleep(1)
            log.info('Clicking on the Search Devices button.')
            driver.execute_script('return $("table.fa-search:visible")[0]').click()
            time.sleep(2)

            log.info('Clicking on the device eid.')
            eid_element = driver.find_element_by_xpath(
                '//a[contains(@href, "javascript:cgms.mainPnl.loadIframe") and contains(text(), "%s")]'%device_eid)
            log.info('Waiting for loading device info.')
            timeout=time.time() + 60*2
            while timeout>time.time():
                eid_element.click()
                time.sleep(2)
                eid_header = driver.execute_script('return $("iframe").contents().find("#device-detail-title:visible").text()')
                if eid_header==device_eid: break

            has_erase_node_certificates_button = driver.execute_script(\
            'return $("iframe").contents().find("button:contains(\'Erase Node Certificates\')").length>0 ? true : false')
            if not has_erase_node_certificates_button: raise Exception('No "Erase Node Certificates" button available.')

            log.info(('Clicking on "Erase Node Certificates".'))
            driver.execute_script('return $("iframe").contents().find("button:contains(\'Erase Node Certificates\')")[0].click()')
            time.sleep(5)

            log.info(('Clicking on "Yes" button.'))
            driver.execute_script('return $("iframe").contents().find("button:contains(\'Yes\')")[0].click()')
            time.sleep(2)

            timeout = time.time() + 60 * 2
            while timeout > time.time():
                reboot_status = driver.execute_script(
                    'return $("iframe").contents().find("#pingTracerouteWindow").find(".x-grid3-col-commandStatus").text()')
                log.info('reboot_status: %s' % reboot_status)
                if reboot_status in ['Completed successfully', 'Failed']: break
                log.info('Waiting for the reboot_status refresh.')
                time.sleep(5)

            response = driver.execute_script('function response(){\
                                            a=[];\
                                            $.each($("iframe").contents().find("#pingTracerouteWindow").find(".x-grid3-cell-inner"), function(i,e){\
                                                a.push(e.textContent);\
                                            });\
                                            return a;\
                                            }\
                                          return response();')

            erase_node_certificate_response = {
                'started_at': response[0],
                'device': response[1],
                'status': response[2],
                'result': response[3]
            }

            log.info('Closing popup window.')
            driver.execute_script('return $("iframe").contents().find(".fa-close")[0].click()')
        except Exception as e:
            driver_utils.save_screenshot()
            log.error(e)

        log.info('erase_node_certificate_response: %s' % json.dumps(erase_node_certificate_response, indent=4, sort_keys=True))
        return erase_node_certificate_response

    def block_mesh_devices(self, device_eid):
        driver = self.driver
        driver_utils = self.driver_utils
        mesh_devices_blocked = False

        try:
            search_input = driver.execute_script('return $("input.x-box-item:visible")[0]')
            search_input.clear()
            time.sleep(1)
            log.info('Entering the Search Query: %s'%('eid:' + device_eid))
            search_input.send_keys('eid:' + device_eid)
            time.sleep(1)
            log.info('Clicking on the Search Devices button.')
            driver.execute_script('return $("table.fa-search:visible")[0]').click()
            time.sleep(2)

            log.info('Clicking on the device eid.')
            eid_element = driver.find_element_by_xpath(
                '//a[contains(@href, "javascript:cgms.mainPnl.loadIframe") and contains(text(), "%s")]'%device_eid)
            log.info('Waiting for loading device info.')
            timeout=time.time() + 60*2
            while timeout>time.time():
                eid_element.click()
                time.sleep(2)
                eid_header = driver.execute_script('return $("iframe").contents().find("#device-detail-title:visible").text()')
                if eid_header==device_eid: break

            has_block_mesh_button = driver.execute_script(\
            'return $("iframe").contents().find("button:contains(\'Block Mesh Device\')").length>0 ? true : false')
            if not has_block_mesh_button: raise Exception('No "Block Mesh Device" button available.')

            log.info(('Clicking on "Block Mesh Device".'))
            driver.execute_script('return $("iframe").contents().find("button:contains(\'Block Mesh Device\')")[0].click()')
            time.sleep(5)

            log.info(('Clicking on "Yes" button.'))
            driver.execute_script('return $("iframe").contents().find("button:contains(\'Yes\')")[0].click()')
            time.sleep(2)

            break_loop = False
            timeout=time.time() + 60*2
            while timeout>time.time():
                try:
                    time.sleep(1)
                    log.info('Waiting for resp_elems.')
                    block_response = driver.execute_script('function block_response(){\
                            a=[];\
                            $.each($("iframe").contents().find("#pingwindow .x-grid3-cell-inner"), function(i,e){\
                                a.push(e.textContent);\
                            });\
                            return a;\
                            }\
                            return block_response();')
                    if 'Running' not in block_response:
                        for i in range(int(len(block_response)/4)):
                            log.info(block_response[i*4:i*4+4:])
                        break_loop = True
                    if break_loop: break
                    else: log.info(block_response)
                except Exception as e: pass

            log.info(('Clicking on "OK" button.'))
            driver.execute_script('return $("iframe").contents().find("button:contains(\'OK\')")[0].click()')
            time.sleep(2)

            popup_header = driver.execute_script('return $("iframe").contents().find("span.x-window-header-text").text()')
            popup_message = driver.execute_script('return $("iframe").contents().find("span.ext-mb-text").text()')
            log.info('\npopup_header: %s\npopup_message: %s'%(popup_header, popup_message))
            if popup_header=='Success': mesh_devices_blocked = True
        except Exception as e:
            driver_utils.save_screenshot()
            log.error(e)

        return mesh_devices_blocked

    def create_work_order(self, **kwargs):
        driver = self.driver
        driver_utils = self.driver_utils
        work_order_created = False

        work_order_name = kwargs.get('work_order_name', None)
        technician_username = kwargs.get('technician_username', None)
        eid = kwargs.get('eid', None)
        status = kwargs.get('status', None)
        start_date = kwargs.get('start_date', '')
        start_time = kwargs.get('start_time', None)
        end_date = kwargs.get('end_date', '')
        end_time = kwargs.get('end_time', '02:00:00')
        time_zone = kwargs.get('time_zone', None)

        try:
            if None in [work_order_name, start_date, end_date]:
                raise Exception('Should provide valid work order details.')
            search_input = driver.execute_script('return $("input.x-box-item:visible")[0]')
            search_input.clear()
            time.sleep(1)
            log.info('Entering the Search Query: %s'%('eid:' + eid))
            search_input.send_keys('eid:' + eid)
            time.sleep(1)
            log.info('Clicking on the Search Devices button.')
            driver.execute_script('return $("table.fa-search:visible")[0]').click()
            time.sleep(2)

            log.info('Clicking on the device eid.')
            eid_element = driver.find_element_by_xpath(
                '//a[contains(@href, "javascript:cgms.mainPnl.loadIframe") and contains(text(), "%s")]'%eid)
            log.info('Waiting for loading device info.')
            timeout=time.time() + 60*2
            while timeout>time.time():
                eid_element.click()
                time.sleep(2)
                eid_header = driver.execute_script('return $("iframe").contents().find("#device-detail-title:visible").text()')
                if eid_header==eid: break

            has_work_order_button = driver.execute_script(\
            'return $("iframe").contents().find("button:contains(\'Create Work Order\')").length>0 ? true : false')
            if not has_work_order_button: raise Exception('No "Create Work Order" button available.')

            log.info(('Clicking on "Create Work Order".'))
            driver.execute_script('return $("iframe").contents().find("button:contains(\'Create Work Order\')")[0].click()')
            time.sleep(5)

            log.info('Entering Work Order name: %s'%work_order_name)
            work_order_input = driver.find_element_by_id('workOrderName')
            work_order_input.clear()
            time.sleep(1)
            work_order_input.send_keys(work_order_name)
            time.sleep(1)

            if technician_username:
                log.info('Entering Technician name: %s'%technician_username)
                technician_username_input = driver.find_element_by_id('technicianUserName')
                technician_username_input.clear()
                time.sleep(1)
                technician_username_input.send_keys(technician_username)
                time.sleep(1)

            if status:
                log.info('Entering Status: %s'%status)
                status_input = driver.find_element_by_id('status')
                status_input.clear()
                time.sleep(1)
                status_input.send_keys(status)
                time.sleep(1)

            log.info('Entering Start Date: %s'%start_date)
            start_date_input = driver.find_element_by_id('startDTFdate')
            start_date_input.clear()
            time.sleep(1)
            start_date_input.send_keys(start_date)
            time.sleep(1)

            if start_time:
                log.info('Entering Start Time: %s'%start_time)
                start_time_input = driver.find_element_by_id('startDTFtime')
                start_time_input.clear()
                time.sleep(1)
                start_time_input.send_keys(start_time)
                time.sleep(1)

            log.info('Entering End date: %s'%end_date)
            end_date_input = driver.find_element_by_id('endDTFdate')
            end_date_input.clear()
            time.sleep(1)
            end_date_input.send_keys(end_date)
            time.sleep(1)

            if end_time:
                log.info('Entering End Time: %s'%end_time)
                end_time_input = driver.find_element_by_id('endDTFtime')
                end_time_input.clear()
                time.sleep(1)
                end_time_input.send_keys(end_time)
                time.sleep(1)

            if time_zone:
                log.info('Entering Time Zone: %s'%time_zone)
                time_zone_input = driver.find_element_by_id('timeZoneId')
                time_zone_input.clear()
                time.sleep(1)
                time_zone_input.send_keys(time_zone)
                time.sleep(1)

            log.info('Saving the changes.')
            time.sleep(3)
            #driver.execute_script('return $(".fa-floppy-o:visible")[0]').click()
            #time.sleep(5)
            #driver.execute_script('return $(".fa-floppy-o")[0]').click()
            #driver_utils.wait_for_loading()
            #time.sleep(5)

            #popup_header = driver.execute_script('return $(".x-window-header-text").text()')
            #popup_message = driver.execute_script('return $(".ext-mb-text").text()')
            #log.info('\npopup_header: %s\npopup_message: %s'%(popup_header, popup_message))
            #time.sleep(10)
            #log.info('Clicking on OK.')
            #ok_button = driver.execute_script('return $(".x-btn-text:contains(\'OK\'):visible")[0]')
            #if ok_button: ok_button.click()
            #else: raise Exception('Unable to get OK button.')
            #time.sleep(2)

            driver.implicitly_wait(2)
            timeout = time.time() + 60 * 2
            while timeout > time.time():
                try:
                    driver.execute_script('return $(".fa-floppy-o:visible")[0]').click()
                    time.sleep(1)
                    popup_header = driver.execute_script('return $(".x-window-header-text").text()')
                    popup_message = driver.execute_script('return $(".ext-mb-text").text()')
                    log.info('\npopup_header: %s\npopup_message: %s' % (popup_header, popup_message))
                    driver.find_element_by_xpath("//button[text()='OK']").click()
                    log.info("Save element clicked.")
                    break
                except:
                    log.info("Unable to click save button... trying again...")
                    time.sleep(1)

            #log.info('Clicking on the close button.')
            #close_button = driver.execute_script('$(".fa-close-o:visible")[0]')
            #if close_button: close_button.click()
            #else: raise Exception('Unable to get Close button.')
            #driver_utils.wait_for_loading()

            field_dev = FieldDevices(driver)
            field_dev.nav_sub_menu('field_devices')
            if popup_header=='Success': work_order_created = True
        except Exception as e:
            driver_utils.save_screenshot()
            log.error(e)

        log.info('work_order_name: %s, created: %s'%(work_order_name, work_order_created))
        return work_order_created

    def default_tab_data(self, group_name):
        driver = self.driver
        driver_utils = self.driver_utils

        default_tab_data = {}
        try:
            self.nav_router_group(group_name)
            self.nav_tab('default')
            driver_utils.wait_for_loading()

            health_data = driver.execute_script('\
                function a(){\
                    a=[];\
                    $.each($(".x-grid3-row-table .x-grid3-cell-inner:visible"),\
                        function(i,e){a.push(e.textContent)});\
                    return a;\
                }\
                return a();\
            ')

            default_data = [a.replace(u'\xa0', u' ') for a in health_data]
            log.info('len(health_data): %d'%len(health_data))

            for i in range(int(len(default_data)/18)):
                dev_data = default_data[i*18:i*18+18:]
                data={}
                data['status'] = dev_data[2]
                data['function'] = dev_data[3]
                data['last_heard'] = dev_data[4]
                data['meter_id'] = dev_data[5]
                data['phy_type'] = dev_data[6]
                data['pan_id'] = dev_data[7]
                data['hops'] = dev_data[8]
                data['mesh_parents'] = dev_data[9]
                data['mesh_children'] = dev_data[10]
                data['mesh_descendants'] = dev_data[11]
                data['firmware'] = dev_data[12]
                data['ip'] = dev_data[13]
                data['open_issues'] = dev_data[14]
                data['labels'] = dev_data[15]
                data['latitude'] = dev_data[16]
                data['longitude'] = dev_data[17]
                default_tab_data[dev_data[1]] = data
        except Exception as e:
            driver_utils.save_screenshot()
            log.error(e)

        log.info('\ndefault_tab_data for : %s\n%s\n\n'%
            (group_name, json.dumps(default_tab_data, indent=4, sort_keys=True)))
        return default_tab_data

    def health_tab_data(self, group_name):
        driver = self.driver
        driver_utils = self.driver_utils

        health_tab_data = {}
        try:
            self.nav_router_group(group_name)
            self.nav_tab('health')

            health_data = driver.execute_script('\
                function a(){\
                    a=[];\
                    $.each($(".x-grid3-row-table .x-grid3-cell-inner:visible"),\
                        function(i,e){a.push(e.textContent)});\
                    return a;\
                }\
                return a();\
            ')

            health_data = [a.replace(u'\xa0', u' ') for a in health_data]
            for i in range(int(len(health_data)/10)):
                dev_data = health_data[i*10:i*10+10:]
                data={}
                data['hops'] = dev_data[2]
                data['pasth_cost'] = dev_data[3]
                data['rssi'] = dev_data[4]
                data['mesh_parents'] = dev_data[5]
                data['mesh_descendants'] = dev_data[6]
                data['interpan_migrations'] = dev_data[7]
                data['intrapan_migrations'] = dev_data[8]
                data['missed_periodic_reads'] = dev_data[9]

                health_tab_data[dev_data[1]] = data
        except Exception as e:
            driver_utils.save_screenshot()
            log.error(e)

        log.info('\n\nhealth_tab_data for group: %s \n%s\n'%
            (group_name, json.dumps(health_tab_data, indent=4, sort_keys=True)))
        return health_tab_data

    def table_grid_styling(self):
        driver = self.driver
        driver_utils = self.driver_utils
        grid_styling = False

        try:
            log.info(banner('Verifying Grid Style for current page.'))
            grid_styling = driver.execute_script('\
                function a(){\
                    odd_even = true;\
                    $.each($(".x-grid3-row:visible"), function(i,e){\
                        if(i%2==0 && e.className.indexOf("x-grid3-row-alt")!=-1) odd_even=false;\
                        else if(i%2==1 && e.className.indexOf("x-grid3-row-alt")==0) odd_even=false;\
                    });\
                    return odd_even;\
                }\
                return a();\
            ')
        except Exception as e:
            driver_utils.save_screenshot()
            log.error(e)

        log.info('\ngrid_styling Exists: %s'%grid_styling)
        return grid_styling

    def sort_tab_data(self, **kwargs):
        driver = self.driver
        driver_utils = self.driver_utils
        data_sorted = False

        try:
            sort_column = kwargs.get('sort_column', None)
            if not sort_column: raise Exception('Provide a vaild Column name to sort.')

            log.info('Soritng by %s'%sort_column)
            before_sort = driver.execute_script('\
                                    return $(".x-grid3-hd-inner:contains(\'%s\')").parent().attr("class")'
                                    %sort_column)
            log.info('before_sort: %s'%before_sort)

            log.info('Clicking on the Column Header.')
            column_header = driver.execute_script('return $(".x-grid3-hd-inner:contains(\'%s\')")[0]'%sort_column)
            column_header.click()
            time.sleep(1)

            after_sort = driver.execute_script('\
                                    return $(".x-grid3-hd-inner:contains(\'%s\')").parent().attr("class")'
                                    %sort_column)
            log.info('after_sort: %s'%after_sort)

            empty_grid = driver.execute_script('return $(".x-grid-empty:visible").text()')
            log.info('empty_grid: %s'%empty_grid)
            if before_sort == after_sort: raise Exception('Unable to sort the headers.')
            else: data_sorted=True
        except Exception as e:
            log.error(e)
            driver_utils.save_screenshot()

        return data_sorted

    def reloadDeviceByRefreshMetrics(self, eid):
        driver = self.driver
        driver_utils = self.driver_utils

        driver_utils.wait_until_element_exists(xpath="//div[@id='netElementGrid']//div[text()='Name']")
        driver.find_element_by_xpath("//div[@id='filterCtrl']//a[text()='Show Filters']/../../input").clear()
        driver.find_element_by_xpath("//div[@id='filterCtrl']//a[text()='Show Filters']/../../input").send_keys(
            "deviceCategory:router domain:root name:" + eid + " status:up")
        driver.find_element_by_xpath(
            "//div[@id='filterCtrl']//table[contains(@class, 'x-btn fa fa-search btn-filter-serach')]").click()
        driver_utils.wait_until_element_exists(xpath="//div[@id='netElementGrid']//a[text()='" + eid + "']")
        driver.find_element_by_xpath("//div[@id='netElementGrid']//a[text()='" + eid + "']").click()

        time.sleep(1)
        # Switch to iframe
        driver.switch_to_frame(driver.find_element_by_xpath("//iframe[@id='iframeMainPanelCardEl']"))

        driver_utils.wait_until_element_exists(xpath="//button[text()='Refresh Metrics']")
        driver.find_element_by_xpath("//button[text()='Refresh Metrics']").click()
        driver_utils.wait_until_element_exists(
            xpath="//div[@id='pingTracerouteWindow']//div[text()='Completed successfully']")
        driver.find_element_by_xpath("//div[@id='pingTracerouteWindow']//i[@class='fa fa-close']").click()
        # Return to main frame
        driver.switch_to_default_content()

    def delete_all_devices(self):
        driver = self.driver
        driver_utils = self.driver_utils
        deleted_all_devices = False

        try:
            check_box = driver.execute_script('return $(".x-grid3-hd-checker:visible")[0]')
            check_box.click()
            time.sleep(1)

            more_actions = driver.execute_script('return $("button:contains(\'More Actions\')")[0]')
            more_actions.click()
            time.sleep(1)
            remove_devices = driver.execute_script('return $("#btnRemoveDevices")[0]')
            
            if 'x-unselectable' not in remove_devices.get_attribute('class'):
                remove_devices.click()
                time.sleep(1)

                driver.execute_script('return $("button:contains(\'Yes\')")[0]').click()
                time.sleep(1)
                driver.execute_script('return $("button:contains(\'OK\')")[0]').click()
                time.sleep(1)
                deleted_all_devices = True
            else:
                log.info('Remove Devices button not enabled.')
        except Exception as e:
            log.error(e)

        log.info('deleted_all_devices: %s'%deleted_all_devices)
        return deleted_all_devices

class HER_Devices(DevicesNavigation):

    def __init__(self, driver, *arg):
        self.arg = arg
        self.driver = driver
        self.driver_utils = DriverUtils(driver)

    def nav_router_group(self, group_name):
        '''
        Method to navigate to Router group.

        :param group_name: Name of the group to navigate.
        :type group_name: str
        '''
        log.info('Navigating to %s' % group_name)
        driver = self.driver
        driver_utils = self.driver_utils
        nav_group_succ = False

        try:
            selected=''
            timeout = time.time() + 60*2
            while timeout>time.time():
                router_group = driver.execute_script('\
                                    return $("span")\
                                    .filter(\
                                        function(){return $(this).text().split(" ")[0].toLowerCase()==="%s".toLowerCase();}\
                                    )[0]'%group_name)
                selected = router_group.find_element_by_xpath('../..').get_attribute('class')
                log.info('router_group selected: %s'%selected)
                if 'x-tree-selected' in selected:
                    nav_group_succ = True
                    break
                time.sleep(1)
                log.info('Clicking on Group: %s'%group_name)
                router_group.click()
                time.sleep(1)
        except Exception as e:
            driver_utils.save_screenshot()
            log.error('Please provide a valid Group name.')

        return nav_group_succ

    def nav_label(self, label_name):

        driver = self.driver

        selected=''
        timeout = time.time() + 60*2
        log.info('Navigating to label_name: %s.'%label_name)
        label_group_ele = driver.find_element_by_xpath('//span[contains(text(), "%s")]'%(label_name))

        while timeout>time.time():
            selected = label_group_ele.find_element_by_xpath('../..').get_attribute('class')
            search_input = driver.execute_script('return $("input.x-box-item:visible")[0]')
            search_input_val = search_input.get_attribute('value')
            if 'x-tree-selected' in selected and label_name in search_input_val: break

            log.info('Clicking on label_name: %s to be active.'%label_name)
            label_group_ele.click()
            time.sleep(2)

    def nav_tab(self, tab_name):
        '''
        Method to navigate to Router group.
        This is how you need to call.
        
        >>> her_devices = ui_common_utils.HER_Devices(driver)
        >>> her_devices.nav_tab('default')

        tab_name choices :-
            * 'default':'Default'
            * 'tunnel1':'Tunnel 1'
            * 'tunnel2':'Tunnel 2'

        :param tab_name: Name of the tab to navigate.
        :type tab_name: str
        '''
        driver = self.driver
        driver_utils = DriverUtils(driver)
        nav_tab_success = False
        tab_dict = {
                    'default':'Default',
                    'tunnel1':'Tunnel 1',
                    'tunnel2':'Tunnel 2'
                   }

        try:
            if tab_name not in tab_dict:
                log.error('Please provide a valid tab name.')
                return

            tab = tab_dict[tab_name]
            log.info('Navigating to Tab: %s'%tab)
            tab_element = driver.execute_script('return $(".x-tab-strip-text:contains(\'%s\'):visible")[0]'%tab)
            log.info('tab_element: %s'%tab_element)

            #Waiting for maximum 2 minutes for the tab to be loaded.
            active=''
            timeout = time.time() + 60*2
            while timeout>time.time():
                tab_element.click()
                time.sleep(1)
                active = driver.execute_script('\
                        return \
                        $(".x-tab-strip-text:contains(\'%s\'):visible")\
                        .closest("li").\
                        attr("class")'%tab)
                log.info('active class: %s'%active)
                if 'active' in active:
                    nav_tab_success = True
                    break
                time.sleep(2)
        except Exception as e:
            driver_utils.save_screenshot()
            log.error(e)

        log.info('tab_name:%s Navigation:%s'%(tab_name, nav_tab_success))
        return nav_tab_success

    def click_element(self, ele_name):
        '''
        Method to navigate to given element.

        :param ele_name: Name of the element to click
        :type ele_name: str
        '''
        driver = self.driver

        if ele_name == 'zoom':
            pass
        elif ele_name == 'gray_scale':
            pass
        elif ele_name == 'overlay':
            pass
        elif ele_name == 'refresh':
            pass
        elif ele_name == 'search_devices':
            pass
        elif ele_name == 'show_filters':
            pass

    def label_operation(self, opertaion, label_name):
        '''
        Method to click on 'Label' opertaion.

        :param opertaion: Name of the operation button to click
        :type opertaion: str
        '''
        driver = self.driver
        driver_utils = self.driver_utils
        label_operation_completed = False
        log.info('Clicking on Label button.')
        driver.execute_script('return $("button:contains(\'Label\')")[0]').click()
        time.sleep(2)

        if opertaion == 'add':
            try:
                log.info('Clicking on btnAddLabel element.')
                driver.find_element_by_id('btnAddLabel').click()
                time.sleep(2)

                input_ele = driver.execute_script('return $(".x-window-bwrap input.x-form-field:visible")[0]')
                time.sleep(2)
                log.info('Clearing the input element.')
                input_ele.clear()
                time.sleep(2)
                log.info('\nEntering label_name: %s.'%label_name)
                input_ele.send_keys(label_name)
                time.sleep(2)
                input_ele.send_keys(Keys.ENTER)
                time.sleep(2)
                dropdown = driver.execute_script('return $(".x-form-arrow-trigger:visible")[1]')
                dropdown.click()
                time.sleep(1)
                dropdown.click()
                time.sleep(1)
                log.info('Current label name: %s'%input_ele.get_attribute('value'))
                driver.execute_script('return $(".x-window-header-text:contains(\'Add Label\')")[0]').click()
                time.sleep(2)
                log.info('Clicking on "Add Label" button.')
                add_label = driver.execute_script('return $("button:contains(\'Add Label\'):visible")[0]')
                add_label.click()
                time.sleep(2)

                driver_utils.wait_for_loading()
                log.info('Reading the popup messages.')
                popup_header = driver.execute_script('return $(".x-window-dlg .x-window-header-text:visible").text()')
                update_response = driver.execute_script('return $(".ext-mb-text:visible").text()')

                log.info('\n\npopup_header: %s,\nupdate_response: %s'%(popup_header, update_response))
                if 'ERROR' in popup_header:
                    driver_utils.save_screenshot()
                driver.find_element_by_xpath('//button[contains(text(), "OK")]').click()
                driver_utils.wait_for_loading()

                log.info('Checking the label group: %s'%label_name)
                search_input = driver.execute_script('return $("input.x-box-item:visible")[0]')
                search_input.clear()
                time.sleep(2)
                seach_string = "label:'%s'"%label_name
                log.info('Entering the search string - %s'%seach_string )
                search_input.send_keys(seach_string)
                time.sleep(2)
                log.info('Clicking on the Search Devices button.')
                driver.execute_script('return $("table.fa-search:visible")[0]').click()
                driver_utils.wait_for_loading()
                log.info('Checking for empty devices grid.')
                has_empty_grid = driver.execute_script('return $(".x-grid-empty").text()?true:false')
                log.info('has_empty_grid: %s'%has_empty_grid)
                assert has_empty_grid==False
                label_operation_completed = True
            except AssertionError: log.error('Unable to add label.')
            except Exception as e:
                driver_utils.save_screenshot()
                log.error(e)
                driver.refresh()
                time.sleep(5)

        elif opertaion == 'remove':
            try:
                log.info('Clicking on btnRemoveLabel element.')
                driver.find_element_by_id('btnRemoveLabel').click()
                time.sleep(1)
                input_ele = driver.find_element_by_xpath('//div[contains(@id, "cbLabelForm")]//input[starts-with(@class, "x-form-text")]')
                input_ele.find_element_by_xpath('following-sibling::img').click()
                time.sleep(1)
                dropdown_label = None
                combo_list_items = input_ele.find_elements_by_xpath('//div[starts-with(@class, "x-combo-list-item") and contains(text(), "%s")]'%label_name)
                for item in combo_list_items:
                    if item.is_displayed() == True:
                        dropdown_label = item
                        break

                if dropdown_label: dropdown_label.click()
                else: raise Exception('No label found.')
                time.sleep(2)
                driver.find_element_by_xpath('//button[contains(text(),"Remove Label")]').click()
                time.sleep(3)

                driver_utils.wait_for_loading()
                log.info('Reading the popup messages.')
                popup_header = driver.execute_script('return $(".x-window-dlg .x-window-header-text:visible").text()')
                update_response = driver.execute_script('return $(".ext-mb-text:visible").text()')

                log.info('popup_header: %s, update_response: %s'%(popup_header, update_response))
                driver.find_element_by_xpath('//button[contains(text(), "OK")]').click()
                driver_utils.wait_for_loading()

                log.info('Checking the label group: %s'%label_name)
                search_input = driver.execute_script('return $("input.x-box-item:visible")[0]')
                search_input.clear()
                time.sleep(1)
                search_input.send_keys("label:'%s'"%label_name)
                time.sleep(1)
                log.info('Clicking on the Search Devices button.')
                driver.execute_script('return $("table.fa-search:visible")[0]').click()
                driver_utils.wait_for_loading()

                search_resp = driver.execute_script('return $(".x-grid-empty").text()')
                log.info('search_resp: %s'%search_resp)
                if search_resp == 'No data is available to display':
                    label_operation_completed = True
            except Exception as e:
                driver_utils.save_screenshot()
                log.error(e)
                driver.refresh()
                time.sleep(5)

        log.info('%s operation with name: %s is completed: %s'%
                    (opertaion, label_name, label_operation_completed))
        return label_operation_completed

    def bulk_operation(self, opertaion='', file_name=''):
        '''
        Method to click on 'Bulk Operation' operation.

        :param opertaion: Name of the operation button to click
        :type opertaion: str
        :param file_name: Name of the csv file
        :type file_name: str
        '''
        driver = self.driver
        driver_utils = self.driver_utils
        operation_completed = False

        log.info('Clicking on the "Bulk Operation" button.')
        driver.find_element_by_xpath('//div[@id="netElementGrid"]//button[contains(text(),"Bulk Operation")]').click()
        time.sleep(1)
        
        if not opertaion: return operation_completed
        if not file_name: return operation_completed
        log.info('opertaion: %s, file_name: %s'%(opertaion, file_name))

        if opertaion == 'add_label':
            driver.find_element_by_id('addLabel').click()
            brwose_id = 'addlabelformupfilefile'
            form_div = 'x-form-el-add-label-form-up-file'
        elif opertaion == 'remove_label':
            driver.find_element_by_id('removeLabel').click()
            brwose_id = 'removelabelformupfilefile'
            form_div = 'x-form-el-remove-label-form-up-file'
        elif opertaion == 'change_dev_prop':
            driver.find_element_by_id('chDeviceButton').click()
            brwose_id = 'formchfilefile'
            form_div = 'x-form-el-form-ch-file'
        elif opertaion == 'rm_devices':
            driver.find_element_by_id('rmDevicesButton').click()
            time.sleep(2)

            try:
                file_input = driver.find_element_by_xpath('//input[@id="formrmfilefile"]')
                file_input.send_keys(file_name)
                time.sleep(1)

                invalid_icon = driver.execute_script('return $("#x-form-el-form-rm-file .x-form-invalid-icon").css("visibility")')
                assert invalid_icon!='visible'
                time.sleep(2)

                log.info('Clicking on Remove button.')
                driver.find_element_by_xpath('//div[@id="rmForm"]/.//button[contains(text(), "Remove")]').click()
                time.sleep(2)

                rm_dev_status = None
                timeout = time.time() + 60*2
                while timeout>time.time():
                    try:
                        rm_dev_status = driver.find_element_by_xpath('//div[contains(text(), "Remove Devices ")]').text
                        log.info('rm_dev_status: %s'%rm_dev_status)
                    except Exception as e: pass
                    if rm_dev_status: break
                    time.sleep(3)

                if 'Failed' in rm_dev_status:
                    driver.execute_script('$(".x-btn-text:contains(\'Close\')").click()')
                    return operation_completed

                failure_popup = driver.execute_script('return $(".x-window-dlg").css("visibility")')
                failure_message = driver.execute_script('return $(".x-window-dlg .x-window-header-text").text()')
                if failure_popup=='visible':
                    log.error('failure_message: %s'%failure_message)
                    driver.execute_script('$(".x-btn-text:contains(\'OK\')").click()')
                    time.sleep(1)
                    driver.execute_script('$(".x-btn-text:contains(\'Close\')").click()')
                    time.sleep(1)
                    return operation_completed

                if 'Completed' in rm_dev_status: operation_completed = True
                time.sleep(1)
                driver.execute_script('$(".x-btn-text:contains(\'Close\')").click()')
                time.sleep(1)
            except AssertionError as ae:
                log.error('Please provide a valid file name.')
                driver_utils.save_screenshot()
            except Exception as e:
                driver_utils.save_screenshot()

        log.info(banner('opertaion: %s with file: %s is completed: %s'%(opertaion, file_name, operation_completed)))
        return operation_completed

    def ping(self, device_eids=None, ping_from_her=True):

        driver = self.driver
        driver_utils = self.driver_utils
        ping_result = {}

        try:
            if not ping_from_her:
                device_eid=device_eids[0]
                eid_element = driver.find_element_by_xpath(
                    '//a[contains(@href, "javascript:cgms.mainPnl.loadIframe") and contains(text(), "%s")]'%device_eid)
                log.info('Waiting for loading device info.')
                timeout=time.time() + 60*2
                while timeout>time.time():
                    eid_element.click()
                    time.sleep(2)
                    eid_header = driver.execute_script(
                        'return $("iframe").contents().find("#device-detail-title:visible").text()')
                    if eid_header==device_eid: break

                log.info('\nClicking on Ping button.')
                driver.execute_script('$("iframe").contents().find("#ping").click()')
                time.sleep(2)

                log.info(banner('Checking ping response.'))
                break_loop = False
                timeout=time.time() + 60*2
                while timeout>time.time():
                    try:
                        time.sleep(1)
                        log.info('Waiting for resp_elems.')
                        ping_response = driver.execute_script('function ping_response(){\
                                a=[];\
                                $.each($("iframe").contents().find("#pingwindow .x-grid3-cell-inner"), function(i,e){\
                                    a.push(e.textContent);\
                                });\
                                return a;\
                                }\
                              return ping_response();')
                        if 'Running' not in ping_response:
                            for i in range(int(len(ping_response)/4)):
                                log.info(ping_response[i*4:i*4+4:])
                                her_response = ping_response[i*4:i*4+4:]
                                eid = her_response[0].split('\n')[0]
                                her_response.append(her_response[0].split('\n')[1].split('( ')[1].split(' )')[0])
                                ping_result[eid] = her_response[1:]
                            break_loop = True
                        if break_loop: break
                    except Exception as e: pass

                log.info('\nClick on close button.')
                driver.execute_script('$("iframe").contents().find("#pingwindow .x-tool-close:visible")[0].click()')
                time.sleep(1)
                log.info('\nClicking on "Back"')
                driver.execute_script('$("iframe").contents().find("a[onclick^=\'cgms.mainPnl.loadIframeBack\'").click()')
                time.sleep(1)
            else:
                check_elems = driver.find_elements_by_xpath('//td[contains(@class, "x-grid3-td-checker")]/div/div')
                log.info('Clicking checkboxes of the given devices.')
                for device_eid in device_eids:
                    her_elem = driver.find_element_by_id('netElementGrid').find_element_by_xpath('//a[contains(text(),"%s")]'%device_eid)
                    check_elem = her_elem.find_elements_by_xpath('../../../td')[0].find_element_by_xpath('div/div')
                    check_elem.click()
                    time.sleep(1)

                log.info('\nClicking on Ping button.')
                driver.find_element_by_id('btnPing').click()
                time.sleep(2)

                log.info(banner('Checking ping response.'))
                break_loop = False
                timeout=time.time() + 60*2
                while timeout>time.time():
                    try:
                        time.sleep(1)
                        log.info('Waiting for resp_elems.')
                        resp_elems = driver.find_elements_by_xpath('//div[@id="pingwindow"]//div[contains(@class, "x-grid3-cell-inner")]')
                        ping_response = [resp_elem.text for resp_elem in resp_elems if resp_elem.is_displayed()]
                        if 'Running' not in ping_response:
                            for i in range(int(len(ping_response)/4)):
                                log.info(ping_response[i*4:i*4+4:])
                                her_response = ping_response[i*4:i*4+4:]
                                eid = her_response[0].split('\n')[0]
                                her_response.append(her_response[0].split('\n')[1].split('( ')[1].split(' )')[0])
                                ping_result[eid] = her_response[1:]
                            break_loop = True
                        if break_loop: break
                    except Exception as e: pass

                log.info('Click on close button.')
                driver.execute_script('return $("#pingwindow .x-tool-close:visible")[0]').click()
                time.sleep(1)
                
                check_elems = driver.find_elements_by_xpath('//td[contains(@class, "x-grid3-td-checker")]/div/div')
                log.info('Unchecking checkboxes of the given devices.')
                for device_eid in device_eids:
                    her_elem = driver.find_element_by_id('netElementGrid').find_element_by_xpath('//a[contains(text(),"%s")]'%device_eid)
                    check_elem = her_elem.find_elements_by_xpath('../../../td')[0].find_element_by_xpath('div/div')
                    check_elem.click()
                    time.sleep(1)
        except Exception as e:
            log.error(e)
            driver_utils.save_screenshot()
            driver.refresh()

        return ping_result

    def traceroute(self, device_eids=None, traceroute_from_her=True):

        driver = self.driver
        driver_utils = self.driver_utils
        trace_route_result = {}

        try:
            if not traceroute_from_her:
                device_eid=device_eids[0]
                eid_element = driver.find_element_by_xpath(
                    '//a[contains(@href, "javascript:cgms.mainPnl.loadIframe") and contains(text(), "%s")]'%device_eid)
                log.info('Waiting for loading device info.')
                timeout=time.time() + 60*2
                while timeout>time.time():
                    eid_element.click()
                    time.sleep(2)
                    eid_header = driver.execute_script(
                        'return $("iframe").contents().find("#device-detail-title:visible").text()')
                    if eid_header==device_eid: break

                log.info('\nClicking on Traceroute button.')
                driver.execute_script('$("iframe").contents().find("#trace_route").click()')
                time.sleep(2)

                log.info(banner('Checking Traceroute response.'))
                timeout=time.time() + 60*2
                while timeout>time.time():
                    try:
                        time.sleep(1)
                        log.info('Waiting for resp_elems.')
                        trace_route_response = driver.execute_script('function trace_route_response(){\
                                a=[];\
                                $.each($("iframe").contents().find("#pingTracerouteWindow .x-grid3-cell-inner"), function(i,e){\
                                    a.push(e.textContent);\
                                });\
                                return a;\
                                }\
                              return trace_route_response();')
                        if 'Running' not in trace_route_response:
                            for i in range(int(len(trace_route_response)/4)):
                                log.info(trace_route_response[i*4:i*4+4:])
                                her_response = trace_route_response[i*4:i*4+4:]
                                trace_route_result[her_response[0]] = her_response[1:]
                            break
                    except Exception as e: pass

                log.info('\nClick on close button.')
                driver.execute_script('$("iframe").contents().find("#pingTracerouteWindow .x-tool-close:visible")[0].click()')
                time.sleep(1)
                log.info('\nClicking on "Back"')
                driver.execute_script('$("iframe").contents().find("a[onclick^=\'cgms.mainPnl.loadIframeBack\'").click()')
                time.sleep(1)
            else:
                check_elems = driver.find_elements_by_xpath('//td[contains(@class, "x-grid3-td-checker")]/div/div')
                log.info('Clicking checkboxes of the given devices.')
                for device_eid in device_eids:
                    her_elem = driver.find_element_by_id('netElementGrid').find_element_by_xpath('//a[contains(text(),"%s")]'%device_eid)
                    check_elem = her_elem.find_elements_by_xpath('../../../td')[0].find_element_by_xpath('div/div')
                    check_elem.click()
                    time.sleep(1)

                log.info('\nClicking on Traceroute button.')
                driver.find_element_by_id('btnTraceroute').click()
                time.sleep(2)

                log.info(banner('Checking Traceroute response.'))
                timeout=time.time() + 60*2
                while timeout>time.time():
                    try:
                        time.sleep(1)
                        log.info('Waiting for resp_elems.')
                        resp_elems = driver.find_elements_by_xpath('//div[@id="pingTracerouteWindow"]//div[contains(@class, "x-grid3-cell-inner")]')
                        trace_route_response = [resp_elem.text for resp_elem in resp_elems if resp_elem.is_displayed()]
                        if 'Running' not in trace_route_response:
                            for i in range(int(len(trace_route_response)/4)):
                                log.info(trace_route_response[i*4:i*4+4:])
                                her_response = trace_route_response[i*4:i*4+4:]
                                trace_route_result[her_response[0]] = her_response[1:]
                            break
                    except Exception as e: pass

                log.info('Click on close button.')
                driver.execute_script('return $("#pingTracerouteWindow .x-tool-close:visible")[0]').click()
                time.sleep(1)

                check_elems = driver.find_elements_by_xpath('//td[contains(@class, "x-grid3-td-checker")]/div/div')
                log.info('Unchecking checkboxes of the given devices.')
                for device_eid in device_eids:
                    her_elem = driver.find_element_by_id('netElementGrid').find_element_by_xpath('//a[contains(text(),"%s")]'%device_eid)
                    check_elem = her_elem.find_elements_by_xpath('../../../td')[0].find_element_by_xpath('div/div')
                    check_elem.click()
                    time.sleep(1)
        except Exception as e:
            log.error(e)
            driver_utils.save_screenshot()
            driver.refresh()

        log.info('trace_route_result: %s'%json.dumps(trace_route_result, indent=4, sort_keys=True))
        return trace_route_result

    def add_devices(self, file_name=''):
        '''
        Method to click on 'Add Devices' operation.

        :param opertaion: Name of the operation button to click
        :type opertaion: str
        '''
        driver = self.driver
        driver_utils = self.driver_utils
        operation_completed = False
        log.info(banner('Performing "Add Devices" with file: %s'%(file_name)))

        driver.find_element_by_id('addDevicesButton').click()
        time.sleep(2)

        try:
            file_input = driver.find_element_by_xpath('//input[@id="formaddfilefile"]')
            file_input.send_keys(file_name)
            time.sleep(1)

            invalid_icon = driver.execute_script('return $("#x-form-el-form-add-file .x-form-invalid-icon").css("visibility")')
            if invalid_icon=='visible': raise Exception('Please provide a valid file name.')
            time.sleep(2)

            log.info('Clicking on Add button.')
            driver.find_element_by_xpath('//div[@id="addForm"]/.//button[contains(text(), "Add")]').click()
            time.sleep(2)

            add_dev_status = None
            timeout = time.time() + 60*2
            while timeout>time.time():
                try:
                    add_dev_status = driver.find_element_by_xpath('//div[contains(text(), "Add Devices ")]').text
                    log.info('add_dev_status: %s'%add_dev_status)
                except Exception as e: pass
                if add_dev_status: break
                time.sleep(3)

            if 'Failed' in add_dev_status:
                driver.execute_script('$(".x-btn-text:contains(\'Close\')").click()')
                return operation_completed

            failure_popup = driver.execute_script('return $(".x-window-dlg").css("visibility")')
            failure_message = driver.execute_script('return $(".x-window-dlg .x-window-header-text").text()')
            if failure_popup=='visible':
                log.error('failure_message: %s'%failure_message)
                driver.execute_script('$(".x-btn-text:contains(\'OK\')").click()')
                time.sleep(1)
                driver.execute_script('$(".x-btn-text:contains(\'Close\')").click()')
                time.sleep(1)
                return operation_completed

            if 'Completed' in add_dev_status: operation_completed = True
            time.sleep(1)
            log.info('Clicking on Close button.')
            driver.execute_script('$(".x-btn-text:contains(\'Close\')").click()')
            time.sleep(1)
        except Exception as e:
            driver_utils.save_screenshot()

        driver_utils.wait_for_loading()
        log.info('Add Operation for %s is : %s'%(file_name, operation_completed))
        return operation_completed

    def refresh_metrics(self, device_eid):

        driver = self.driver
        driver_utils = self.driver_utils
        refresh_metrics = {}

        try:
            log.info('Clicking on the given device eid.')
            eid_element = driver.find_element_by_xpath('//a[contains(@href, "javascript:cgms.mainPnl.loadIframe") and contains(text(), "%s")]'%device_eid)
            log.info('Waiting for loading device info.')
            timeout=time.time() + 60*2
            while timeout>time.time():
                eid_element.click()
                time.sleep(2)
                eid_header = driver.execute_script('return $("iframe").contents().find("#device-detail-title:visible").text()')
                if eid_header==device_eid: break

            log.info(('Clicking on "Refresh Metrics".'))
            driver.execute_script('$("iframe").contents().find("#centerMainPanelCard").find("#refresh_metrics")[0].click()')
            time.sleep(5)

            timeout=time.time() + 60*2
            while timeout>time.time():
                status = driver.execute_script('return $("iframe").contents().find("#pingTracerouteWindow").find(".x-grid3-col-commandStatus").text()')
                if status=='Completed successfully' or status=='Failed': break
                log.info('Waiting for the metrics refresh.')
                time.sleep(3)

            started_at = driver.execute_script('return $("iframe").contents().find("#pingTracerouteWindow").find(".x-grid3-col-commandStartedAt").text()')
            device_ip = driver.execute_script('return $("iframe").contents().find("#pingTracerouteWindow").find(".x-grid3-col-ipAddress").text()')
            status = driver.execute_script('return $("iframe").contents().find("#pingTracerouteWindow").find(".x-grid3-col-commandStatus").text()')
            result = driver.execute_script('return $("iframe").contents().find("#pingTracerouteWindow").find(".x-grid3-col-response").text()')

            refresh_metrics['started_at'] = started_at
            refresh_metrics['device_ip'] = device_ip
            refresh_metrics['status'] = status
            refresh_metrics['result'] = result

            log.info('Closing popup window.')
            driver.execute_script('$.each($("iframe").contents().find("#pingTracerouteWindow").find(":button"), function(idx, button){if(button.textContent=="Close"){button.click()}})')
            time.sleep(1)
            driver.execute_script('$("iframe").contents().find("a[onclick^=\'cgms.mainPnl.loadIframeBack\'").click()')
            time.sleep(1)
        except Exception as e:
            log.error(e)

        return refresh_metrics

    def more_actions(self, opertaion):
        '''
        Method to click on 'More Actions' operation.

        :param opertaion: Name of the operation button to click
        :type opertaion: str
        '''
        driver = self.driver
        driver.find_element_by_xpath('//div[@id="netElementGrid"]//button[contains(text(),"More Actions")]')
        if opertaion == 'work_order':
            driver.find_element_by_id('btnWorkOrder').click()
        elif opertaion == 'refresh_mesh_key':
            driver.find_element_by_id('btnRefreshRouterMeshKey').click()
        elif opertaion == 'block_mesh_keys':
            driver.find_element_by_id('btnBlockMeshDevice').click()
        elif opertaion == 'remove_devices':
            driver.find_element_by_id('btnRemoveDevices').click()

    def device_details(self, router_eid):
        '''
        Method to get device details of a given router eid.

        :param router_eid: eid of the router to check the details
        :type router_eid: str
        '''
        driver = self.driver
        driver.refresh()
        time.sleep(5)
        #router_elem = driver.find_element_by_id('netElementGrid').find_element_by_xpath('//a[contains(text(),"%s")]'%router_eid)
        #router_elem_tds = router_elem.find_elements_by_xpath('../../../td/div')
        try:
            device_detail_tds = [ele.text for ele in \
                                 driver.find_element_by_id('netElementGrid') \
                                 .find_element_by_xpath('//a[contains(text(),"%s")]'%router_eid) \
                                 .find_elements_by_xpath('../../../td/div')[2:]]
            log.info('device_detail_tds: %s'%(device_detail_tds,))

            meter_id = device_detail_tds[0]
            last_heard = device_detail_tds[2]
            category = device_detail_tds[3]
            dev_type = device_detail_tds[4]
            function = device_detail_tds[5]
            pan_id = device_detail_tds[6]
            firmware = device_detail_tds[7]
            ip = device_detail_tds[8]
            open_issues = device_detail_tds[9]
            labels = device_detail_tds[10]
            latitude = device_detail_tds[11]
            longitude = device_detail_tds[12]

            router_elem = driver.find_element_by_id('netElementGrid').find_element_by_xpath('//a[contains(text(),"%s")]'%router_eid)
            status = router_elem.find_elements_by_xpath('../../../td/div')[3].find_element_by_xpath('..').get_attribute('class')
            if 'displayicon-up' in status:
                status='device is UP'
            elif 'displayicon-down' in status:
                status='device is DOWN'

            log.info(
                ' meter_id: %s\n status: %s\n last_heard: %s\n category: %s\n dev_type: %s\n function: %s\n pan_id: %s\n firmware: %s\n ip: %s\n open_issues: %s\n labels: %s\n latitude: %s\n latitude:%s'%
                (meter_id, status, last_heard, category, dev_type, function, pan_id, firmware, ip, open_issues, labels, latitude, longitude)
                )
        except StaleElementReferenceException as e:
            log.error(e)
        except AssertionError as e:
            log.error(e)

    def device_info(self, device_eid):
        '''
        Method to get device info of a given router eid.

        :param router_eid: eid of the router to check the device info
        :type router_eid: str
        '''
        driver = self.driver
        driver_utils = self.driver_utils

        try:
            device_info={}
            eid_element = driver.find_element_by_xpath('//a[contains(@href, "javascript:cgms.mainPnl.loadIframe") and contains(text(), "%s")]'%device_eid)

            log.info('Waiting for loading device info.')
            timeout=time.time() + 60*2
            while timeout>time.time():
                eid_element.click()
                time.sleep(2)
                eid_header = driver.execute_script('return $("iframe").contents().find("#device-detail-title:visible").text()')
                if eid_header==device_eid: break

            device_info = driver.execute_script('function info(){\
                                        a={};\
                                        $.each($("iframe").contents().find(".key:visible"), function(i,e){\
                                            a[e.textContent.trim()]=e.nextElementSibling.textContent;\
                                        });\
                                        return a;\
                                    }\
                                    return info();')

        except Exception as e: log.error(e)

        return device_info

    def select_devices(self, router_eids):
        '''
        Method to select the given devices.

        :param router_eids: list of eids to select
        :type router_eids: list
        '''
        driver = self.driver
        try:
            for router_eid in router_eids:
                #Getting anchor element with router_eid under the element with id:"netElementGrid".
                router_elem = driver.find_element_by_id('netElementGrid').find_element_by_xpath('//a[contains(text(),"%s")]'%router_eid)
                log.info('Click on the device checkbox from netElementGrid')
                #Getting the first td element of this tr row.
                check_box_td = router_elem.find_element_by_xpath('../../..').find_elements_by_tag_name('td')[0]
                #Click the checkbox of the router_eid.
                check_box_td.find_element_by_xpath('div/div').click()

                '''
                row_checkers = driver.find_elements_by_xpath('//div[contains(@class, "x-grid3-row-checker")]')
                for row_checker in row_checkers:
                    curr_eid = row_checker.find_element_by_xpath('../../following-sibling::td/div/a').text
                    if curr_eid == router_eid:
                        row_checker.click()
                        break
                '''
        except (NoSuchElementException, ElementNotVisibleException) as e:
            log.error('Unable to find the element: %s' % e)

    def access_device(self, router_eid):
        '''
        Method to access the given device.

        :param router_eid: eid of the device.
        :type router_eid: str
        '''
        driver = self.driver
        try:
            #Getting router element with router_eid under the element with id:"netElementGrid".
            router_elem = driver.find_element_by_id('netElementGrid').find_element_by_xpath('//a[contains(text(),"%s")]'%router_eid)
            log.info('Click on the device from netElementGrid')
            router_elem.click()
        except (NoSuchElementException, ElementNotVisibleException) as e:
            log.error('Unable to find the element: %s' % e)

    def search_devices(self, search_field, **kwargs):
        '''
        Allows the user to search for devices with the given fields

        :param search_field: Search Field name
        :type search_field: str
        :param search_value: Search value
        :type search_value: str

        Search Field choices :-
            * 'Label'
            * 'Category'
            * 'EID'
            * 'Firmware'
            * 'Function'
            * 'Hardware ID'
            * 'IP'
            * 'Last Heard'
            * 'Latitude'
            * 'Longitude'
            * 'Model Number'
            * 'Name'
            * 'Serial Number'
            * 'Status'
            * 'Type'
            * 'Up time'
            * 'GRE Tunnel Source 1'
            * 'GRE Tunnel Source 2'
            * 'IPsec Tunnel Source 1'
            * 'IPsec Tunnel Source 2'
            * 'Tunnel Group'

        Usage:

        >>> her_devices = ui_common_utils.HER_Devices(driver)
        >>> her_devices.search_devices('Type', 'cgr1000')
        '''

        driver = self.driver
        log.info('Clearing exiting search filter content.')
        search_box = driver.execute_script('return $("input.x-box-item:visible")[0]')
        search_box.clear()

        log.info('Clicking on Hide Filters button if exists.')
        driver.execute_script('if($(\'a:contains("Hide Filters")\').length>0)$(\'a:contains("Hide Filters")\')[0].click()')
        time.sleep(1)

        log.info('Clicking on Show Filter button.')
        driver.find_element_by_xpath('//a[contains(text(), "Show Filter")]').click()

        log.info('Selecting search field')
        driver.find_element_by_xpath('//input[contains(@id, "labelsCombofilterCtrl")]//following-sibling::img').click()
        time.sleep(2)
        dropdown_elements = driver.find_elements_by_xpath('//div[starts-with(@class, "x-combo-list-item") and contains(text(), "%s")]'%search_field)
        for dropdown_element in dropdown_elements:
            if dropdown_element.text == search_field:
                dropdown_element.click()
                break
        time.sleep(2)

        log.info('Selecting search value')
        search_value = kwargs.get('seach_value', '')

        if search_field in ['Groups', 'EID', 'Firmware', 'Hardware ID', 'IP', 'Model Number', 'Name', 'Serial Number']:
            driver.find_element_by_xpath('//input[contains(@id, "stringfilterCtrl")]').send_keys(search_value)
            time.sleep(2)
        
        elif search_field in ['Latitude', 'Longitude', 'Up time']:
            inputs = driver.find_elements_by_xpath('//div[contains(@class, "x-box-inner")]/input[starts-with(@class,"x-form-text")]')
            start_input = inputs[1]
            stop_input = inputs[2]

            start_value = kwargs.get('start_value', '')
            end_value = kwargs.get('end_value', '')

            start_input.clear()
            start_input.send_keys(start_value)
            time.sleep(1)
            stop_input.clear()
            stop_input.send_keys(end_value)
            time.sleep(1)
            search_box.click()

        elif search_field == 'Last Heard':
            input_dates = driver.find_elements_by_xpath('//td[contains(@class, "ux-datetime-date")]')[1:]
            start_date = input_dates[0].find_element_by_xpath('div/input')
            end_date = input_dates[1].find_element_by_xpath('div/input')
            # input_times = driver.find_elements_by_xpath('//td[contains(@class, "ux-datetime-time")]')[1:]
            # start_time = input_times[0].find_element_by_xpath('div/input')
            # end_time = input_times[1].find_element_by_xpath('div/input')

            start_date_value = kwargs.get('start_date', '')
            end_date_value = kwargs.get('end_date', '')

            start_date.clear()
            start_date.send_keys(start_date_value)
            time.sleep(1)
            end_date.clear()
            end_date.send_keys(end_date_value)
            time.sleep(1)
            search_box.click()

        else:
            driver.find_element_by_xpath('//input[contains(@id, "combofilterCtrl")]//following-sibling::img').click()
            time.sleep(2)
            driver.find_element_by_xpath('//div[starts-with(@class, "x-combo-list-item") and contains(text(), "%s")]'%search_value).click()
            time.sleep(2)

        log.info('Adding the selected filter.')
        driver.find_element_by_xpath('//i[@class="fa fa-plus"]').click()
        time.sleep(2)

        log.info('Clicking on the Search Devices button.')
        driver.execute_script('return $("table.fa-search:visible")[0]').click()
        time.sleep(2)

        try:
            searched_tunnels = driver.find_elements_by_xpath('//div[contains(@class, "x-grid3-body")]/div[starts-with(@class,"x-grid3-row")]')
            log.info(banner('Total devices with the search criteria "%s" : %d'%(search_field+':'+search_value, len(searched_tunnels))))
        except Exception as e: log.error(e)

    def sort_her_devices(self, sort_by, *args):

        driver = self.driver
        log.info('Sorting Devices by: %s'%sort_by)
        
        tab_ids = {
            'name': 'x-grid3-td-1',
            'status': 'x-grid3-td-2',
            'last_heard': 'x-grid3-td-3',
            'firmware': 'x-grid3-td-4',
            'ip': 'x-grid3-td-5'
        }
        tab_id = tab_ids[sort_by]

        selected=''
        timeout = time.time() + 60*2
        router_span = driver.find_element_by_xpath('//span[contains(text(), "All HER Devices")]')
        while 'x-tree-selected' not in selected:
            selected = router_span.find_element_by_xpath('../..').get_attribute('class')
            if time.time()>timeout: break
            log.info('Click on "All HER Devices" span.')
            router_span.click()
            time.sleep(1)
        
        log.info('Click on "Inventory" tab.')
        self.nav_tab('inventory')
        time.sleep(1)

        try:
            tab_ele = driver.find_element_by_xpath('//tr[contains(@class, "x-grid3-hd-row")]/td[contains(@class,"%s")]'%tab_id)
            curr_sort = tab_ele.get_attribute('class')
            log.info('curr_sort: %s'%curr_sort)

            log.info('Clicking on %s tab.'%sort_by)
            tab_ele.click()
            time.sleep(1)
        except Exception as e: log.error(e)

class Servers(DevicesNavigation):

    def __init__(self, driver, *arg):
        self.arg = arg
        self.driver = driver
        self.driver_utils = DriverUtils(driver)

    def nav_device_group(self, group_name):
        '''
        Method to navigate to Devices group.

        :param group_name: Name of the group to navigate.
        :type group_name: str
        '''
        driver = self.driver
        log.info('Clicking on Devices Group: %s'%group_name)
        driver.find_element_by_partial_link_text(group_name).click()

    def nav_tab(self, tab_name):
        '''
        Method to navigate to Tab.
        This is how you need to call.
        
        >>> servers = ui_common_utils.Servers(driver)
        >>> servers.nav_tab('default')

        tab_name choices :-
            * 'default':'Default'

        :param tab_name: Name of the tab to navigate.
        :type tab_name: str
        '''
        driver = self.driver
        driver_utils = DriverUtils(driver)
        nav_tab_success = False
        tab_dict = {'default':'Default'}

        try:
            if tab_name not in tab_dict:
                log.error('Please provide a valid tab name.')
                return

            tab = tab_dict[tab_name]
            log.info('Navigating to Tab: %s'%tab)
            tab_element = driver.execute_script('return $(".x-tab-strip-text:contains(\'%s\'):visible")[0]'%tab)
            log.info('tab_element: %s'%tab_element)

            #Waiting for maximum 2 minutes for the tab to be loaded.
            active=''
            timeout = time.time() + 60*2
            while timeout>time.time():
                tab_element.click()
                time.sleep(1)
                active = driver.execute_script('\
                        return \
                        $(".x-tab-strip-text:contains(\'%s\'):visible")\
                        .closest("li").\
                        attr("class")'%tab)
                log.info('active class: %s'%active)
                if 'active' in active:
                    nav_tab_success = True
                    break
                time.sleep(2)
        except Exception as e:
            driver_utils.save_screenshot()
            log.error(e)

        log.info('tab_name:%s Navigation:%s'%(tab_name, nav_tab_success))
        return nav_tab_success

    def click_element(self, ele_name):
        '''
        Method to navigate to given element.

        :param ele_name: Name of the element to click
        :type ele_name: str
        '''
        driver = self.driver

        if ele_name == 'zoom':
            pass
        elif ele_name == 'gray_scale':
            pass
        elif ele_name == 'overlay':
            pass
        elif ele_name == 'refresh':
            pass
        elif ele_name == 'search_devices':
            pass
        elif ele_name == 'show_filters':
            pass

    def ping(self, device_eids=None, ping_from_far=True):

        driver = self.driver
        driver_utils = self.driver_utils
        ping_result = {}

        try:
            if not ping_from_far:
                device_eid=device_eids[0]
                eid_element = driver.find_element_by_xpath(
                    '//a[contains(@href, "javascript:cgms.mainPnl.loadIframe") and contains(text(), "%s")]'%device_eid)
                log.info('Waiting for loading device info.')
                timeout=time.time() + 60*2
                while timeout>time.time():
                    eid_element.click()
                    time.sleep(2)
                    eid_header = driver.execute_script(
                        'return $("iframe").contents().find("#device-detail-title:visible").text()')
                    if eid_header==device_eid: break

                log.info('\nClicking on Ping button.')
                driver.execute_script('$("iframe").contents().find("#ping").click()')
                time.sleep(2)

                log.info(banner('Checking ping response.'))
                break_loop = False
                timeout=time.time() + 60*2
                while timeout>time.time():
                    try:
                        time.sleep(1)
                        log.info('Waiting for resp_elems.')
                        ping_response = driver.execute_script('function ping_response(){\
                                a=[];\
                                $.each($("iframe").contents().find("#pingwindow .x-grid3-cell-inner"), function(i,e){\
                                    a.push(e.textContent);\
                                });\
                                return a;\
                                }\
                              return ping_response();')
                        if 'Running' not in ping_response:
                            for i in range(int(len(ping_response)/4)):
                                log.info(ping_response[i*4:i*4+4:])
                                far_response = ping_response[i*4:i*4+4:]
                                eid = far_response[0].split('\n')[0]
                                far_response.append(far_response[0].split('\n')[1].split('( ')[1].split(' )')[0])
                                ping_result[eid] = far_response[1:]
                            break_loop = True
                        if break_loop: break
                    except Exception as e: pass

                log.info('\nClick on close button.')
                driver.execute_script('$("iframe").contents().find("#pingwindow .x-tool-close:visible")[0].click()')
                time.sleep(1)
                log.info('\nClicking on "Back"')
                driver.execute_script('$("iframe").contents().find("a[onclick^=\'cgms.mainPnl.loadIframeBack\'").click()')
                time.sleep(1)
            else:
                check_elems = driver.find_elements_by_xpath('//td[contains(@class, "x-grid3-td-checker")]/div/div')
                log.info('Clicking checkboxes of the given devices.')
                for device_eid in device_eids:
                    her_elem = driver.find_element_by_id('netElementGrid').find_element_by_xpath('//a[contains(text(),"%s")]'%device_eid)
                    check_elem = her_elem.find_elements_by_xpath('../../../td')[0].find_element_by_xpath('div/div')
                    check_elem.click()
                    time.sleep(1)

                log.info('\nClicking on Ping button.')
                driver.find_element_by_id('btnPing').click()
                time.sleep(2)

                log.info(banner('Checking ping response.'))
                break_loop = False
                timeout=time.time() + 60*2
                while timeout>time.time():
                    try:
                        time.sleep(1)
                        log.info('Waiting for resp_elems.')
                        resp_elems = driver.find_elements_by_xpath('//div[@id="pingwindow"]//div[contains(@class, "x-grid3-cell-inner")]')
                        ping_response = [resp_elem.text for resp_elem in resp_elems if resp_elem.is_displayed()]
                        if 'Running' not in ping_response:
                            for i in range(int(len(ping_response)/4)):
                                log.info(ping_response[i*4:i*4+4:])
                                far_response = ping_response[i*4:i*4+4:]
                                eid = far_response[0].split('\n')[0]
                                far_response.append(far_response[0].split('\n')[1].split('( ')[1].split(' )')[0])
                                ping_result[eid] = far_response[1:]
                            break_loop = True
                        if break_loop: break
                    except Exception as e: pass

                log.info('Click on close button.')
                driver.execute_script('return $("#pingwindow .x-tool-close:visible")[0]').click()
                time.sleep(1)
                
                check_elems = driver.find_elements_by_xpath('//td[contains(@class, "x-grid3-td-checker")]/div/div')
                log.info('Unchecking checkboxes of the given devices.')
                for device_eid in device_eids:
                    her_elem = driver.find_element_by_id('netElementGrid').find_element_by_xpath('//a[contains(text(),"%s")]'%device_eid)
                    check_elem = her_elem.find_elements_by_xpath('../../../td')[0].find_element_by_xpath('div/div')
                    check_elem.click()
                    time.sleep(1)
        except Exception as e:
            log.error(e)
            driver_utils.save_screenshot()
            driver.refresh()

        log.info('Ping Response for %s\n%s'%(device_eids, json.dumps(ping_result, indent=4, sort_keys=True)))
        return ping_result

    def traceroute(self, device_eids=None, traceroute_from_far=True):

        driver = self.driver
        driver_utils = self.driver_utils
        trace_route_result = {}

        try:
            if not traceroute_from_far:
                device_eid=device_eids[0]
                eid_element = driver.find_element_by_xpath(
                    '//a[contains(@href, "javascript:cgms.mainPnl.loadIframe") and contains(text(), "%s")]'%device_eid)
                log.info('Waiting for loading device info.')
                timeout=time.time() + 60*2
                while timeout>time.time():
                    eid_element.click()
                    time.sleep(2)
                    eid_header = driver.execute_script(
                        'return $("iframe").contents().find("#device-detail-title:visible").text()')
                    if eid_header==device_eid: break

                log.info('\nClicking on Traceroute button.')
                driver.execute_script('$("iframe").contents().find("#trace_route").click()')
                time.sleep(2)

                log.info(banner('Checking Traceroute response.'))
                timeout=time.time() + 60*2
                while timeout>time.time():
                    try:
                        time.sleep(1)
                        log.info('Waiting for resp_elems.')
                        trace_route_response = driver.execute_script('function trace_route_response(){\
                                a=[];\
                                $.each($("iframe").contents().find("#pingTracerouteWindow .x-grid3-cell-inner"), function(i,e){\
                                    a.push(e.textContent);\
                                });\
                                return a;\
                                }\
                              return trace_route_response();')
                        if 'Running' not in trace_route_response:
                            for i in range(int(len(trace_route_response)/4)):
                                log.info(trace_route_response[i*4:i*4+4:])
                                far_response = trace_route_response[i*4:i*4+4:]
                                trace_route_result[far_response[0]] = far_response[1:]
                            break
                    except Exception as e: pass

                log.info('\nClick on close button.')
                driver.execute_script('$("iframe").contents().find("#pingTracerouteWindow .x-tool-close:visible")[0].click()')
                time.sleep(1)
                log.info('\nClicking on "Back"')
                driver.execute_script('$("iframe").contents().find("a[onclick^=\'cgms.mainPnl.loadIframeBack\'").click()')
                time.sleep(1)
            else:
                check_elems = driver.find_elements_by_xpath('//td[contains(@class, "x-grid3-td-checker")]/div/div')
                log.info('Clicking checkboxes of the given devices.')
                for device_eid in device_eids:
                    her_elem = driver.find_element_by_id('netElementGrid').find_element_by_xpath('//a[contains(text(),"%s")]'%device_eid)
                    check_elem = her_elem.find_elements_by_xpath('../../../td')[0].find_element_by_xpath('div/div')
                    check_elem.click()
                    time.sleep(1)

                log.info('\nClicking on Traceroute button.')
                driver.find_element_by_id('btnTraceroute').click()
                time.sleep(2)

                log.info(banner('Checking Traceroute response.'))
                timeout=time.time() + 60*2
                while timeout>time.time():
                    try:
                        time.sleep(1)
                        log.info('Waiting for resp_elems.')
                        resp_elems = driver.find_elements_by_xpath('//div[@id="pingTracerouteWindow"]//div[contains(@class, "x-grid3-cell-inner")]')
                        trace_route_response = [resp_elem.text for resp_elem in resp_elems if resp_elem.is_displayed()]
                        if 'Running' not in trace_route_response:
                            for i in range(int(len(trace_route_response)/4)):
                                log.info(trace_route_response[i*4:i*4+4:])
                                far_response = trace_route_response[i*4:i*4+4:]
                                trace_route_result[far_response[0]] = far_response[1:]
                            break
                    except Exception as e: pass

                log.info('Click on close button.')
                driver.execute_script('return $("#pingTracerouteWindow .x-tool-close:visible")[0]').click()
                time.sleep(1)

                check_elems = driver.find_elements_by_xpath('//td[contains(@class, "x-grid3-td-checker")]/div/div')
                log.info('Unchecking checkboxes of the given devices.')
                for device_eid in device_eids:
                    her_elem = driver.find_element_by_id('netElementGrid').find_element_by_xpath('//a[contains(text(),"%s")]'%device_eid)
                    check_elem = her_elem.find_elements_by_xpath('../../../td')[0].find_element_by_xpath('div/div')
                    check_elem.click()
                    time.sleep(1)
        except Exception as e:
            log.error(e)
            driver_utils.save_screenshot()
            driver.refresh()

        log.info('trace_route_result: %s'%json.dumps(trace_route_result, indent=4, sort_keys=True))
        return trace_route_result

    def add_devices(self, file_name=''):
        '''
        Method to click on 'Add Devices' operation.

        :param opertaion: Name of the operation button to click
        :type opertaion: str
        '''
        driver = self.driver
        driver_utils = self.driver_utils
        operation_completed = False
        log.info(banner('Performing "Add Devices" with file: %s'%(file_name)))

        try:
            log.info('Clicking "Add Devices".')
            driver.find_element_by_id('addDevicesButton').click()
            time.sleep(2)
            file_input = driver.find_element_by_xpath('//input[@id="formaddfilefile"]')
            file_input.send_keys(file_name)
            time.sleep(1)

            invalid_icon = driver.execute_script('return $("#x-form-el-form-add-file .x-form-invalid-icon").css("visibility")')
            if invalid_icon=='visible': raise Exception('Please provide a valid file name.')
            time.sleep(2)

            log.info('Clicking on Add button.')
            driver.find_element_by_xpath('//div[@id="addForm"]/.//button[contains(text(), "Add")]').click()
            time.sleep(2)

            timeout = time.time() + 60*10
            while timeout>time.time():
                add_devices_loading = driver.execute_script('return $("#add_devices_loading")[0].style.visibility=="visible"?true:false')
                log.info('add_devices_loading: %s'%add_devices_loading)
                if add_devices_loading:
                    time.sleep(3)
                    log.info('Waiting for file upload.')
                else: break

            time.sleep(1)
            failure_popup = driver.execute_script('return $(".x-window-dlg").css("visibility")')
            failure_message = driver.execute_script('return $(".x-window-dlg .x-window-header-text").text()')
            if failure_popup=='visible':
                log.error('failure_message: %s'%failure_message)
                driver.execute_script('$(".x-btn-text:contains(\'OK\')").click()')
                time.sleep(1)
                driver.execute_script('$(".x-btn-text:contains(\'Close\')").click()')
                time.sleep(1)
                return operation_completed

            add_dev_status = driver.find_element_by_xpath('//div[contains(text(), "Add Devices ")]').text
            if 'Failed' in add_dev_status:
                driver_utils.save_screenshot()
            if 'Completed' in add_dev_status:
                operation_completed = True

            time.sleep(1)
            log.info('Closing "Add Devices" popup.')
            driver.execute_script('$(".x-btn-text:contains(\'Close\')").click()')
            time.sleep(1)
        except Exception as e:
            log.error(e)
            driver_utils.save_screenshot()

        driver_utils.wait_for_loading()
        log.info('Add Operation for %s is : %s'%(file_name, operation_completed))
        return operation_completed

    def label_operation(self, opertaion, label_name):
        '''
        Method to click on 'Label' opertaion.

        :param opertaion: Name of the operation button to click
        :type opertaion: str
        '''
        driver = self.driver
        driver_utils = self.driver_utils
        label_operation_completed = False
        log.info('Clicking on Label button.')
        driver.execute_script('return $("button:contains(\'Label\')")[0]').click()
        time.sleep(2)

        if opertaion == 'add':
            try:
                log.info('Clicking on btnAddLabel element.')
                driver.find_element_by_id('btnAddLabel').click()
                time.sleep(2)

                #input_ele = driver.execute_script('return $(".x-window-bwrap input.x-form-field:visible")[0]')
                input_ele = driver.find_element_by_xpath('//div[contains(@id, "cbLabelForm")]//input[starts-with(@class, "x-form-text")]')
                log.info(input_ele)
                time.sleep(5)
                log.info('Clearing the input element.')
                input_ele.clear()
                time.sleep(2)
                log.info('\nEntering label_name: %s.'%label_name)
                input_ele.send_keys(label_name)
                time.sleep(2)
                input_ele.send_keys(Keys.ENTER)
                time.sleep(2)

                ##Fix
                log.info('Clicking Add Label button')
                driver.find_element_by_xpath('//button[contains(text(),"Add Label")]').click()
                time.sleep(1)
                log.info('Confirming OK.')
                #driver.find_element_by_xpath('//button[contains(text(), "OK")]').click()
                #time.sleep(1)

                #dropdown = driver.execute_script('return $(".x-form-arrow-trigger:visible")[1]')
                #dropdown.click()
                #time.sleep(1)
                #dropdown.click()
                #time.sleep(1)
                #log.info('Current label name: %s'%input_ele.get_attribute('value'))
                #driver.execute_script('return $(".x-window-header-text:contains(\'Add Label\')")[0]').click()
                #time.sleep(2)
                #log.info('Clicking on "Add Label" button.')
                #add_label = driver.execute_script('return $("button:contains(\'Add Label\'):visible")[0]')
                #add_label.click()
                #time.sleep(2)

                driver_utils.wait_for_loading()
                log.info('Reading the popup messages.')
                popup_header = driver.execute_script('return $(".x-window-dlg .x-window-header-text:visible").text()')
                update_response = driver.execute_script('return $(".ext-mb-text:visible").text()')

                log.info('\n\npopup_header: %s,\nupdate_response: %s'%(popup_header, update_response))
                if 'ERROR' in popup_header:
                    driver_utils.save_screenshot()
                driver.find_element_by_xpath('//button[contains(text(), "OK")]').click()
                driver_utils.wait_for_loading()

                log.info('Checking the label group: %s'%label_name)
                #search_input = driver.execute_script('return $("input.x-box-item:visible")[0]')
                #search_input.clear()
                #time.sleep(2)
                #seach_string = "label:'%s'"%label_name
                #log.info('Entering the search string - %s'%seach_string )
                #search_input.send_keys(seach_string)
                #time.sleep(2)
                #log.info('Clicking on the Search Devices button.')
                #driver.execute_script('return $("table.fa-search:visible")[0]').click()
                driver.find_element_by_xpath(
                '//a[@class="x-tree-node-anchor"]/span[contains(text(), "%s")]'%label_name).click()
                driver_utils.wait_for_loading()
                log.info('Checking for empty devices grid.')
                has_empty_grid = driver.execute_script('return $(".x-grid-empty").text()?false:true')
                log.info('has_empty_grid: %s'%has_empty_grid)
                assert has_empty_grid==False
                label_operation_completed = True
            except AssertionError: log.error('Unable to add label.')
            except Exception as e:
                driver_utils.save_screenshot()
                log.error(e)
                driver.refresh()
                time.sleep(5)

        elif opertaion == 'remove':
            try:
                log.info('Clicking on btnRemoveLabel element.')
                driver.find_element_by_id('btnRemoveLabel').click()
                time.sleep(1)
                input_ele = driver.find_element_by_xpath('//div[contains(@id, "cbLabelForm")]//input[starts-with(@class, "x-form-text")]')
                input_ele.find_element_by_xpath('following-sibling::img').click()
                time.sleep(1)
                dropdown_label = None
                combo_list_items = input_ele.find_elements_by_xpath('//div[starts-with(@class, "x-combo-list-item") and contains(text(), "%s")]'%label_name)
                for item in combo_list_items:
                    if item.is_displayed() == True:
                        dropdown_label = item
                        break

                if dropdown_label: dropdown_label.click()
                else: raise Exception('No label found.')
                time.sleep(2)
                driver.find_element_by_xpath('//button[contains(text(),"Remove Label")]').click()
                time.sleep(3)

                driver_utils.wait_for_loading()
                log.info('Reading the popup messages.')
                popup_header = driver.execute_script('return $(".x-window-dlg .x-window-header-text:visible").text()')
                update_response = driver.execute_script('return $(".ext-mb-text:visible").text()')

                log.info('popup_header: %s, update_response: %s'%(popup_header, update_response))
                driver.find_element_by_xpath('//button[contains(text(), "OK")]').click()
                driver_utils.wait_for_loading()

                #log.info('Checking the label group: %s'%label_name)
                
                #search_input = driver.execute_script('return $("input.x-box-item:visible")[0]')
                #search_input.clear()
                #time.sleep(1)
                #search_input.send_keys("label:'%s'"%label_name)
                #time.sleep(1)
                #log.info('Clicking on the Search Devices button.')
                #driver.execute_script('return $("table.fa-search:visible")[0]').click()
                #driver_utils.wait_for_loading()

                search_resp = driver.execute_script('return $(".x-grid-empty").text()')
                log.info('search_resp: %s'%search_resp)
                if search_resp == 'No data is available to display':
                    label_operation_completed = True
            except Exception as e:
                driver_utils.save_screenshot()
                log.error(e)
                driver.refresh()
                time.sleep(5)

        log.info('%s operation with name: %s is completed: %s'%
                    (opertaion, label_name, label_operation_completed))
        return label_operation_completed

    def nav_label(self, opertaion, label_name):
        '''
        Method to click on 'Label' opertaion.

        :param opertaion: Name of the operation button to click
        :type opertaion: str
        '''

        driver = self.driver
        log.info('Clicking on Label button.')
        driver.find_element_by_xpath('//div[@id="netElementGrid"]//button[contains(text(),"Label")]').click()
        
        if opertaion == 'add':
            log.info('Clicking on btnAddLabel button.')
            driver.find_element_by_id('btnAddLabel').click()
            time.sleep(1)
            input_ele = driver.find_element_by_xpath('//div[contains(@id, "cbLabelForm")]//input[starts-with(@class, "x-form-text")]')
            input_ele.clear()
            time.sleep(1)
            log.info('Entering label_name: %s'% label_name)
            input_ele.send_keys(label_name)
            time.sleep(1)
            log.info('Clicking Add Label button')
            driver.find_element_by_xpath('//button[contains(text(),"Add Label")]').click()
            time.sleep(1)
            log.info('Confirming OK.')
            driver.find_element_by_xpath('//button[contains(text(), "OK")]').click()
            time.sleep(1)
        elif opertaion == 'remove':
            log.info('Clicking on btnRemoveLabel button.')
            driver.find_element_by_id('btnRemoveLabel').click()
            time.sleep(1)
            input_ele = driver.find_element_by_xpath('//div[contains(@id, "cbLabelForm")]//input[starts-with(@class, "x-form-text")]')
            log.info('Selecting dropdown')
            input_ele.find_element_by_xpath('following-sibling::img').click()
            time.sleep(1)
            log.info('Selecting label_name: %s'%label_name)
            combo_list_items = input_ele.find_elements_by_xpath('//div[starts-with(@class, "x-combo-list-item") and contains(text(), "%s")]'%label_name)
            for item in combo_list_items:
                if item.is_displayed() == True:
                    item.click()
                    break
            time.sleep(1)
            log.info('Clicking Remove Label button')
            driver.find_element_by_xpath('//button[contains(text(),"Remove Label")]').click()
            time.sleep(1)
            log.info('Confirming OK.')
            driver.find_element_by_xpath('//button[contains(text(), "OK")]').click()
            time.sleep(1)

    def bulk_operation(self, opertaion):
        '''
        Method to click on 'Bulk Operation' operation.

        :param opertaion: Name of the operation button to click
        :type opertaion: str
        '''
        driver = self.driver
        driver.find_element_by_xpath('//div[@id="netElementGrid"]//button[contains(text(),"Bulk Operation")]').click()
        if opertaion == 'add_label':
            driver.find_element_by_id('addLabel').click()
        elif opertaion == 'remove_label':
            driver.find_element_by_id('removeLabel').click()
        elif opertaion == 'change_dev_prop':
            driver.find_element_by_id('chDeviceButton').click()
        elif opertaion == 'remove_dev':
            driver.find_element_by_id('rmDevicesButton').click()

    def more_actions(self, opertaion):
        '''
        Method to click on 'More Actions' operation.

        :param opertaion: Name of the operation button to click
        :type opertaion: str
        '''
        driver = self.driver
        driver.find_element_by_xpath('//div[@id="netElementGrid"]//button[contains(text(),"More Actions")]')
        if opertaion == 'work_order':
            driver.find_element_by_id('btnWorkOrder').click()
        elif opertaion == 'refresh_mesh_key':
            driver.find_element_by_id('btnRefreshRouterMeshKey').click()
        elif opertaion == 'block_mesh_keys':
            driver.find_element_by_id('btnBlockMeshDevice').click()
        elif opertaion == 'remove_devices':
            driver.find_element_by_id('btnRemoveDevices').click()

    def device_details(self, router_eid):
        '''
        Method to get device details of a given router eid.

        :param router_eid: eid of the router to check the details
        :type router_eid: str
        '''
        driver = self.driver
        driver.refresh()
        time.sleep(5)
        #router_elem = driver.find_element_by_id('netElementGrid').find_element_by_xpath('//a[contains(text(),"%s")]'%router_eid)
        #router_elem_tds = router_elem.find_elements_by_xpath('../../../td/div')
        try:
            device_detail_tds = [ele.text for ele in \
                                 driver.find_element_by_id('netElementGrid') \
                                 .find_element_by_xpath('//a[contains(text(),"%s")]'%router_eid) \
                                 .find_elements_by_xpath('../../../td/div')[2:]]
            log.info('device_detail_tds: %s'%(device_detail_tds,))

            meter_id = device_detail_tds[0]
            last_heard = device_detail_tds[2]
            category = device_detail_tds[3]
            dev_type = device_detail_tds[4]
            function = device_detail_tds[5]
            pan_id = device_detail_tds[6]
            firmware = device_detail_tds[7]
            ip = device_detail_tds[8]
            open_issues = device_detail_tds[9]
            labels = device_detail_tds[10]
            latitude = device_detail_tds[11]
            longitude = device_detail_tds[12]

            router_elem = driver.find_element_by_id('netElementGrid').find_element_by_xpath('//a[contains(text(),"%s")]'%router_eid)
            status = router_elem.find_elements_by_xpath('../../../td/div')[3].find_element_by_xpath('..').get_attribute('class')
            if 'displayicon-up' in status:
                status='device is UP'
            elif 'displayicon-down' in status:
                status='device is DOWN'

            log.info(
                ' meter_id: %s\n status: %s\n last_heard: %s\n category: %s\n dev_type: %s\n function: %s\n pan_id: %s\n firmware: %s\n ip: %s\n open_issues: %s\n labels: %s\n latitude: %s\n latitude:%s'%
                (meter_id, status, last_heard, category, dev_type, function, pan_id, firmware, ip, open_issues, labels, latitude, longitude)
                )
        except StaleElementReferenceException as e:
            log.error(e)
        except AssertionError as e:
            log.error(e)

    def device_info(self, router_eid):
        '''
        Method to get device info of a given router eid.

        :param router_eid: eid of the router to check the device info
        :type router_eid: str
        '''
        driver = self.driver
        pass

    def select_devices(self, router_eids):
        '''
        Method to select the given devices.

        :param router_eids: list of eids to select
        :type router_eids: list
        '''
        driver = self.driver
        try:
            for router_eid in router_eids:
                #Getting anchor element with router_eid under the element with id:"netElementGrid".
                router_elem = driver.find_element_by_id('netElementGrid').find_element_by_xpath('//a[contains(text(),"%s")]'%router_eid)
                log.info('Click on the device checkbox from netElementGrid')
                #Getting the first td element of this tr row.
                check_box_td = router_elem.find_element_by_xpath('../../..').find_elements_by_tag_name('td')[0]
                #Click the checkbox of the router_eid.
                check_box_td.find_element_by_xpath('div/div').click()
        except (NoSuchElementException, ElementNotVisibleException) as e:
            log.error('Unable to find the element: %s' % e)

    def access_device(self, router_eid):
        '''
        Method to access the given device.

        :param router_eid: eid of the device.
        :type router_eid: str
        '''
        driver = self.driver
        try:
            #Getting router element with router_eid under the element with id:"netElementGrid".
            router_elem = driver.find_element_by_id('netElementGrid').find_element_by_xpath('//a[contains(text(),"%s")]'%router_eid)
            log.info('Click on the device from netElementGrid')
            router_elem.click()
        except (NoSuchElementException, ElementNotVisibleException) as e:
            log.error('Unable to find the element: %s' % e)

    def sort_server_devices(self, sort_by, *args):

        driver = self.driver
        log.info('Sorting Devices by: %s'%sort_by)
        
        tab_ids = {
            'name': 'x-grid3-td-1',
            'status': 'x-grid3-td-2',
            'last_heard': 'x-grid3-td-3',
            'ip': 'x-grid3-td-4'
        }
        tab_id = tab_ids[sort_by]

        selected=''
        timeout = time.time() + 60*2
        router_span = driver.find_element_by_xpath('//span[contains(text(), "All SERVER Devices")]')
        while 'x-tree-selected' not in selected:
            selected = router_span.find_element_by_xpath('../..').get_attribute('class')
            if time.time()>timeout: break
            log.info('Click on "All SERVER Devices" span.')
            router_span.click()
            time.sleep(1)

        log.info('Click on "Inventory" tab.')
        self.nav_tab('inventory')
        time.sleep(1)

        try:
            tab_ele = driver.find_element_by_xpath('//tr[contains(@class, "x-grid3-hd-row")]/td[contains(@class,"%s")]'%tab_id)
            curr_sort = tab_ele.get_attribute('class')
            log.info('curr_sort: %s'%curr_sort)

            log.info('Clicking on %s tab.'%sort_by)
            tab_ele.click()
            time.sleep(1)
        except Exception as e: log.error(e)

class Assets(DevicesNavigation):

    def __init__(self, driver, *arg):
        self.arg = arg
        self.driver = driver
        self.driver_utils = DriverUtils(driver)

    def bulk_import(self, opertaion='', file_name=''):
        '''
        Method to click on 'Bulk Import' operation.

        :param opertaion: Name of the operation button to click
        :type opertaion: str
        '''
        driver = self.driver
        driver_utils = self.driver_utils
        operation_completed = False
        driver_utils.wait_for_loading()
        log.info(banner('Performing %s with file: %s'%(opertaion, file_name)))

        log.info('Clicking on the "Bulk Import" button.')
        actions_button = driver.execute_script('return $("#actions_button")[0]')
        actions_button.click()
        time.sleep(1)

        if not opertaion: return operation_completed
        if not file_name: return operation_completed
        log.info('opertaion: %s, file_name: %s'%(opertaion, file_name))

        if opertaion == 'add_assets':
            log.info('Selecting "Add Assets".')
            driver.find_element_by_id('addAssetsButton').click()
            time.sleep(2)

            try:
                file_input = driver.find_element_by_xpath('//input[@id="formaddfilefile"]')
                file_input.send_keys(file_name)
                time.sleep(1)

                invalid_icon = driver.execute_script('return $("#x-form-el-form-add-file .x-form-invalid-icon").css("visibility")')
                assert invalid_icon!='visible'
                time.sleep(2)

                log.info('Clicking on Add button.')
                driver.find_element_by_xpath('//div[@id="addForm"]/.//button[contains(text(), "Add")]').click()
                time.sleep(2)

                timeout = time.time() + 60*10
                while timeout>time.time():
                    add_devices_loading = driver.execute_script('return $("#add_devices_loading")[0].style.visibility=="visible"?true:false')
                    log.info('add_devices_loading: %s'%add_devices_loading)
                    if add_devices_loading:
                        time.sleep(3)
                        log.info('Waiting for file upload.')
                    else: break

                time.sleep(1)
                failure_popup = driver.execute_script('return $(".x-window-dlg").css("visibility")')
                failure_message = driver.execute_script('return $(".x-window-dlg .x-window-header-text").text()')
                if failure_popup=='visible':
                    log.error('failure_message: %s'%failure_message)
                    driver.execute_script('$(".x-btn-text:contains(\'OK\')").click()')
                    time.sleep(1)
                    driver.execute_script('$(".x-btn-text:contains(\'Close\')").click()')
                    time.sleep(1)
                    return operation_completed

                add_assets_status = driver.find_element_by_xpath('//div[contains(text(), "Add Assets ")]').text
                if 'Failed' in add_assets_status:
                    driver_utils.save_screenshot()
                if 'Completed' in add_assets_status:
                    operation_completed = True

                time.sleep(1)
                log.info('Closing "Add Assets" popup.')
                driver.execute_script('$(".x-btn-text:contains(\'Close\')").click()')
                time.sleep(1)
            except AssertionError as ae:
                log.error('Please provide a valid file name.')
                driver_utils.save_screenshot()
            except Exception as e:
                driver_utils.save_screenshot()
        elif opertaion == 'change_asset_property':
            log.info('Selecting "Change Asset Property".')
            driver.find_element_by_id('changeProperty').click()
            time.sleep(2)
            try:
                file_input = driver.find_element_by_xpath('//input[@id="formupdatefilefile"]')
                file_input.send_keys(file_name)
                time.sleep(1)

                invalid_icon = driver.execute_script('return $("#x-form-el-form-add-file .x-form-invalid-icon").css("visibility")')
                assert invalid_icon!='visible'
                time.sleep(1)

                log.info('Clicking on "Change" button.')
                driver.find_element_by_xpath('//div[@id="updateForm"]/.//button[contains(text(), "Update")]').click()
                time.sleep(2)

                change_dev_status = None
                timeout = time.time() + 60*2
                while timeout>time.time():
                    try:
                        change_dev_status = driver.find_element_by_xpath('//div[contains(text(), "Update Assets ")]').text
                        log.info('change_asset_status: %s'%change_dev_status)
                    except Exception as e: pass
                    if change_dev_status: break
                    time.sleep(3)

                if 'Failed' in change_dev_status:
                    driver.execute_script('$(".x-btn-text:contains(\'Close\')").click()')
                    return operation_completed

                failure_popup = driver.execute_script('return $(".x-window-dlg").css("visibility")')
                failure_message = driver.execute_script('return $(".x-window-dlg .x-window-header-text").text()')
                log.info('failure_popup: %s\nfailure_message: %s'%(failure_popup, failure_message))
                if failure_popup=='visible':
                    log.error('failure_message: %s'%failure_message)
                    driver.execute_script('$(".x-btn-text:contains(\'OK\')").click()')
                    time.sleep(1)
                    driver.execute_script('$(".x-btn-text:contains(\'Close\')").click()')
                    time.sleep(1)
                    return operation_completed

                if 'Completed' in change_dev_status: operation_completed = True
                time.sleep(1)
                log.info('Clicking on Close button.')
                driver.execute_script('$(".x-btn-text:contains(\'Close\')").click()')
                time.sleep(1)
            except AssertionError as ae:
                log.error('Please provide a valid file name.')
                driver_utils.save_screenshot()
        elif opertaion == 'remove_assets':
            driver.find_element_by_id('removeAssets').click()
            time.sleep(2)

            try:
                file_input = driver.find_element_by_xpath('//input[@id="formremovefilefile"]')
                file_input.send_keys(file_name)
                time.sleep(1)

                invalid_icon = driver.execute_script('return $("#x-form-el-form-rm-file .x-form-invalid-icon").css("visibility")')
                assert invalid_icon!='visible'
                time.sleep(2)

                log.info('Clicking on Remove button.')
                driver.find_element_by_xpath('//div[@id="removeForm"]/.//button[contains(text(), "Remove Assets")]').click()
                time.sleep(2)

                rm_dev_status = None
                timeout = time.time() + 60*10
                while timeout>time.time():
                    try:
                        rm_dev_status = driver.find_element_by_xpath('//div[contains(text(), "Remove ")]').text
                        log.info('rm_dev_status: %s'%rm_dev_status)
                    except Exception as e: pass
                    if rm_dev_status: break
                    time.sleep(3)

                if 'Failed' in rm_dev_status:
                    driver.execute_script('$(".x-btn-text:contains(\'Close\')").click()')
                    return operation_completed

                failure_popup = driver.execute_script('return $(".x-window-dlg").css("visibility")')
                failure_message = driver.execute_script('return $(".x-window-dlg .x-window-header-text").text()')
                log.info('failure_popup: %s\nfailure_message: %s'%(failure_popup, failure_message))
                if failure_popup=='visible':
                    log.error('failure_message: %s'%failure_message)
                    driver.execute_script('$(".x-btn-text:contains(\'OK\')").click()')
                    time.sleep(1)
                    driver.execute_script('$(".x-btn-text:contains(\'Close\')").click()')
                    time.sleep(1)
                    return operation_completed

                if 'Completed' in rm_dev_status: operation_completed = True
                time.sleep(1)
                driver.execute_script('$(".x-btn-text:contains(\'Close\')").click()')
                time.sleep(1)
            except AssertionError as ae:
                log.error('Please provide a valid file name.')
                driver_utils.save_screenshot()
            except Exception as e:
                driver_utils.save_screenshot()
        elif opertaion == 'add_files_to_assets':
            log.info('Selecting "Add Files to assets".')
            driver.find_element_by_id('addFilesButton').click()
            time.sleep(2)

            try:
                file_input = driver.find_element_by_xpath('//input[@id="formchfilefile"]')
                log.info('Entering file_name: %s'%file_name)
                file_input.send_keys(file_name)
                time.sleep(1)

                invalid_icon = driver.execute_script('return $("#x-form-el-form-add-file .x-form-invalid-icon").css("visibility")')
                assert invalid_icon!='visible'
                time.sleep(2)

                log.info('Clicking on Upload button.')
                driver.find_element_by_xpath('//div[@id="tarFileUploadWindow"]/.//button[contains(text(), "Upload")]').click()
                driver_utils.wait_for_loading()

                '''
                add_assets_status = driver.find_element_by_xpath('//div[contains(text(), "Add Assets ")]').text
                log.info('add_assets_status: %s'%add_assets_status)
                if 'Failed' in add_assets_status:
                    driver_utils.save_screenshot()
                if 'Completed' in add_assets_status:
                    operation_completed = True

                time.sleep(1)
                log.info('Closing "Add Assets" popup.')
                driver.execute_script('$(".x-btn-text:contains(\'Close\')").click()')
                time.sleep(1)
                '''
                failure_popup = driver.execute_script('return $(".x-window-dlg").css("visibility")')
                failure_message = driver.execute_script('return $(".x-window-dlg .x-window-header-text").text()')
                if failure_message=='ERROR':
                    log.error('failure_message: %s'%failure_message)
                    log.info('Clicking on OK')
                    driver.execute_script('return $(".x-btn-text:contains(\'OK\')")[0]').click()
                    time.sleep(1)
                    log.info('Clicking on Close')
                    driver.execute_script('return $(".x-tool-close:visible")[0]').click()
                    time.sleep(1)
                    raise Exception('Unable to upload.')

                driver.execute_script('$(".x-btn-text:contains(\'OK\')").click()')
                time.sleep(1)
                operation_completed = True
            except AssertionError as ae:
                log.error('Please provide a valid file name.')
                driver_utils.save_screenshot()
            except Exception as e:
                driver_utils.save_screenshot()

        driver_utils.wait_for_loading()
        log.info('%s for %s is : %s'%(opertaion, file_name, operation_completed))
        return operation_completed

    def delete_asset_files(self, asset_name):
        '''
        Method to click on 'Bulk Import' operation.

        :param asset_name: Name of the asset
        :type asset_name: str
        '''
        driver = self.driver
        driver_utils = self.driver_utils
        operation_completed = False
        asset_files_deleted = False

        try:
            # import pdb; pdb.set_trace()
            asset = driver.execute_script('return \
                                    $(".x-grid3-col-2:visible").\
                                    filter(function(){return $(this).text() === "%s"})[0]'
                                    %asset_name)
            asset.click()
            driver_utils.wait_for_loading()
            asset_file_delete = driver.execute_script('return \
                                    $("iframe").contents().find("#centerMainPanelCard")\
                                    .find(".asset-file-delete")[0]')
            asset_file_delete.click()
            driver.execute_script\
                ('return $("button:contains(\'Yes\')")[0]').click()
            time.sleep(1)
            driver.execute_script\
                ('return $("button:contains(\'OK\')")[0]').click()
            time.sleep(1)
            asset_files_deleted = True
            # $("iframe").contents().find("#centerMainPanelCard").find(".asset-file-delete")[0]
        except Exception as e:
            log.error(e)
            driver_utils.save_screenshot()

        log.info('Asset files under: %s is deleted: %s'%(asset_name, asset_files_deleted))
        return operation_completed

class Events(OperationsNavigation):
    ''' This class defines all the opertaions under "Events" page. '''

    def __init__(self, driver, *arg):
        self.arg = arg
        self.driver = driver
        self.driver_utils = DriverUtils(driver)

    def verifyEventTriggerred(self, user_defined_event_name):
        driver = self.driver
        driver_utils = self.driver_utils
        driver_utils.wait_until_element_exists(xpath="//div[@id='eventsGrid']//div[text()='Name']")
        driver.find_element_by_xpath("//input[@id='eventSearchQuery']").clear()
        driver.find_element_by_xpath("//input[@id='eventSearchQuery']").send_keys('eventName:' + user_defined_event_name)
        driver.find_element_by_xpath("//input[@id='eventSearchQuery']/../table").click()
        driver_utils.wait_until_element_exists(xpath="//div[@id='eventsGrid']//div[text()='" + user_defined_event_name + "']")
        driver.find_element_by_xpath("//div[@id='eventsGrid']//div[text()='" + user_defined_event_name + "']")
        log.info("Expected Event Found!")
        time.sleep(1)

    def search_events(self, search_field, **kwargs):
        '''
        Search Field choices :-
            * 'Name'
            * 'Type'
            * 'Category'
            * 'Event Name'
            * 'Event Severity'
            * 'Event Time'
            * 'Label'

        Usage:

        >>> events.search_events('Admin Status', 'up')
        '''

        driver = self.driver
        driver_utils = self.driver_utils
        search_success = False
        curr_search_query = ''

        log.info('Clearing exiting search filter content.')
        search_box = driver.find_element_by_xpath('//input[contains(@id, "eventSearchQuery")]')
        search_box.clear()

        log.info('Clicking on Hide Filter button if exists.')
        driver.execute_script('if($(\'a:contains("Hide Filter")\').length>0)$(\'a:contains("Hide Filter")\')[0].click()')
        time.sleep(1)
        log.info('Clicking on Show Filter button.')
        driver.find_element_by_xpath('//a[contains(text(), "Show Filter")]').click()
        time.sleep(2)

        try:
            log.info('Selecting search field')
            log.info('Clicking on event options.')
            driver.find_element_by_xpath('//input[contains(@id, "labelsCombortb")]//following-sibling::img').click()
            time.sleep(2)
            log.info('Clicking on %s.'%search_field)
            driver.find_element_by_xpath('//div[starts-with(@class, "x-combo-list-item") and contains(text(), "%s")]'%search_field).click()
            time.sleep(2)

            log.info('Selecting search value')
            search_value = kwargs.get('search_value', '')

            if search_field == 'Name':
                driver.find_element_by_xpath('//input[contains(@id, "stringrtb")]').send_keys(search_value)
                time.sleep(2)

            elif search_field == 'Event Time':
                input_dates = driver.find_elements_by_xpath('//td[contains(@class, "ux-datetime-date")]')[1:]
                start_date = input_dates[0].find_element_by_xpath('div/input')
                end_date = input_dates[1].find_element_by_xpath('div/input')
                # input_times = driver.find_elements_by_xpath('//td[contains(@class, "ux-datetime-time")]')[1:]
                # start_time = input_times[0].find_element_by_xpath('div/input')
                # end_time = input_times[1].find_element_by_xpath('div/input')

                start_date_value = kwargs.get('start_date', '')
                end_date_value = kwargs.get('end_date', '')

                start_date.clear()
                start_date.send_keys(start_date_value)
                time.sleep(1)
                end_date.clear()
                end_date.send_keys(end_date_value)
                time.sleep(1)

                driver.execute_script('return $("#extcomp1043time")[0]').click()
                time.sleep(1)
                driver.execute_script('return $("#extcomp1045time")[0]').click()
                time.sleep(1)
                search_box.click()

            else:
                driver.find_element_by_xpath('//input[contains(@id, "combortb")]//following-sibling::img').click()
                time.sleep(2)
                node = driver.execute_script('return \
                                    $(".x-combo-list-item:visible").\
                                    filter(function(){return $(this).text() === "%s"})[0]'
                                    %search_value)
                node.click()
                time.sleep(2)

            log.info('Adding the selected filter.')
            driver.find_element_by_xpath('//i[@class="fa fa-plus"]').click()
            time.sleep(2)

            curr_search_query = driver.execute_script('function searchQuery(){return $("#eventSearchQuery").val();} return searchQuery()')
            log.info('curr_search_query: %s'%curr_search_query)

            log.info('Clicking on the Search Events button.')
            driver.execute_script('return $("table.fa-search:visible")[0]').click()
            search_success = True

            searched_events=[]
            timeout=time.time()+60
            while timeout>time.time():
                log.info(banner('Getting events with the search criteria: %s'%curr_search_query))
                empty_grid_len = int(driver.execute_script('return $(".x-grid-empty:visible").length'))

                if empty_grid_len!=0:
                    log.info('No data with Searched Criteria')
                else:
                    searched_events = driver.execute_script('return \
                        $(".xtb-text:contains(\'Displaying\')")[0].textContent.split("of ")[1]')
                    log.info(banner('Total events with the search criteria "%s" : %d'%(search_field+':'+search_value, int(searched_events))))
                if searched_events: break
                time.sleep(5)
        except Exception as e:
            log.error(e)
            driver_utils.save_screenshot()

        return search_success

    def get_event_data(self, **kwargs):
        '''
        Method to get Events info of a given router eid.

        :param router_eid: eid of the router to check the device info
        :type router_eid: str
        '''
        driver = self.driver
        driver_utils = self.driver_utils
        event_data={}
        search_query = kwargs.get('device_eid', None)
        event_count = kwargs.get('event_count', None)
        event_data = {}

        try:
            if search_query:
                search_input = driver.execute_script('return $("input.x-box-item:visible")[0]')
                #search_input.clear()
                time.sleep(1)
                log.info('Entering the Search Query: %s'%search_query)
                search_input.send_keys(search_query)
                time.sleep(1)
                log.info('Clicking on the Search Devices button.')
                driver.execute_script('return $("table.fa-search:visible")[0]').click()
                time.sleep(2)

            data = driver.execute_script('\
                                function a(){\
                                    a=[];\
                                    $.each($(".x-grid3-row:visible").find(".x-grid3-cell:visible"),\
                                        function(i,e){ if(i%5!=0){a.push(e.textContent)} else{a.push(e.firstChild.firstChild.title)} });\
                                    return a;\
                                }\
                            return a();\
                        ')
            if event_count: data = data[:5*int(event_count)]

            time.sleep(2)
            event_data = {
                'severity': data[0::5],
                'name': data[1::5],
                'time': data[2::5],
                'event_name': data[3::5],
                'message': data[4::5],
            }
        except Exception as e: log.error(e)

        log.info('event_data: %s'%json.dumps(event_data, indent=4, sort_keys=True))
        return event_data

    def sort_events(self, sort_by, **kwargs):

        driver = self.driver
        driver_utils = self.driver_utils
        log.info('Sorting WorkOrders by: %s'%sort_by)
        
        tab_ids = {
            'severity': 'x-grid3-td-severity',
            'name': 'x-grid3-td-name',
            'eventTime': 'x-grid3-td-eventTime',
            'eventTypeName': 'x-grid3-td-eventTypeName',
            'eventMessage': 'x-grid3-td-eventMessage'
        }
        tab_id = tab_ids[sort_by]
        sort_order = kwargs.get('sort_order','desc')
        curr_sort_order = None

        try:
            tab_ele = driver.find_element_by_xpath('//tr[contains(@class, "x-grid3-hd-row")]/td[contains(@class,"%s")]'%tab_id)
            curr_sort = tab_ele.get_attribute('class')
            log.info('curr_sort: %s'%curr_sort)
            if sort_order in curr_sort:
                log.info('Already sorted')
            else:
                log.info('Clicking on %s tab.'%sort_by)
                tab_ele.click()
                driver_utils.wait_for_loading()
                tab_ele = driver.find_element_by_xpath('//tr[contains(@class, "x-grid3-hd-row")]/td[contains(@class,"%s")]'%tab_id)
                curr_sort = tab_ele.get_attribute('class')

            if 'sort-asc' in curr_sort: curr_sort_order = 'Ascending Order'
            elif 'sort-desc' in curr_sort: curr_sort_order = 'Descending Order'
        except Exception as e:
            log.error(e)
            driver_utils.save_screenshot()

        log.info('curr_sort_order: %s'%curr_sort_order)
        return curr_sort_order

    def sort_tab_data(self, **kwargs):
        driver = self.driver
        driver_utils = self.driver_utils
        data_sorted = False

        try:
            sort_column = kwargs.get('sort_column', None)
            if not sort_column: raise Exception('Provide a vaild Column name to sort.')
            time.sleep(1)
            column_header = driver.execute_script('return $(".x-grid3-hd-inner:contains(\'%s\')")[0]'%sort_column)
            column_header.click()
            time.sleep(1)
            log.info('Soritng by %s'%sort_column)
            before_sort = driver.execute_script('\
                                    return $(".x-grid3-hd-inner:contains(\'%s\')").parent().attr("class")'
                                    %sort_column)
            log.info('before_sort: %s'%before_sort)
            time.sleep(2)
            log.info('Clicking on the Column Header.')
#            column_header = driver.find_element_by_xpath('//tr[contains(@class, "x-grid3-hd-row")]/td[contains(@class,"%s")]'%sort_column)
            column_header1 = driver.execute_script('return $(".x-grid3-hd-inner:contains(\'%s\')")[0]'%sort_column)
            column_header1.click()
            time.sleep(2) 
            after_sort = driver.execute_script('\
                                    return $(".x-grid3-hd-inner:contains(\'%s\')").parent().attr("class")'
                                    %sort_column)
            log.info('after_sort: %s'%after_sort)

            empty_grid = driver.execute_script('return $(".x-grid-empty:visible").text()')
            log.info('empty_grid: %s'%empty_grid)
            if before_sort == after_sort: raise Exception('Unable to sort the headers.')
            else: data_sorted=True
        except Exception as e:
            log.error(e)
            driver_utils.save_screenshot()

        return data_sorted
    
class Issues(OperationsNavigation):
    ''' This class defines all the opertaions under "Events" page. '''

    def __init__(self, driver, *arg):
        self.arg = arg
        self.driver = driver
        self.driver_utils = DriverUtils(driver)

class TunnelStatus(OperationsNavigation):
    ''' This class defines all the opertaions under "Tunnel Status" page. '''

    def __init__(self, driver, *arg):
        self.arg = arg
        self.driver = driver
        self.driver_utils = DriverUtils(driver)

    def search_tunnels(self, search_field, search_value):
        '''

        Search Field choices :-
            * 'HER Name'
            * 'HER Interface'
            * 'FAR Name'
            * 'Admin Status'
            * 'Oper Status'
            * 'Protocol'
            * 'FAR Interface'
            * 'IP Address'

        Usage:

        >>> tunnel_status.search_tunnels('Admin Status', 'up')

        '''
        
        driver = self.driver
        log.info('Clearing exiting search filter content.')
        driver.find_element_by_xpath('//input[contains(@id, "tunnelSearchQuery")]').clear()

        log.info('Clicking on Hide Filter button if exisits.')
        driver.execute_script('if($(\'a:contains("Hide Filter")\').length>0)$(\'a:contains("Hide Filter")\')[0].click()')
        time.sleep(1)

        log.info('Clicking on Show Filter button.')
        driver.find_element_by_xpath('//a[contains(text(), "Show Filter")]').click()

        log.info('Selecting search field')
        driver.find_element_by_xpath('//input[contains(@id, "labelsCombofilterBox")]//following-sibling::img').click()
        time.sleep(2)
        driver.find_element_by_xpath('//div[starts-with(@class, "x-combo-list-item") and contains(text(), "%s")]'%search_field).click()
        time.sleep(2)

        log.info('Selecting search value')
        if search_field == 'Admin Status' or search_field == 'Oper Status':
            driver.find_element_by_xpath('//input[contains(@id, "combofilterBox")]//following-sibling::img').click()
            time.sleep(2)
            driver.find_element_by_xpath('//div[starts-with(@class, "x-combo-list-item") and contains(text(), "%s")]'%search_value).click()
            time.sleep(2)
        else:
            driver.find_element_by_xpath('//input[contains(@id, "stringfilterBox")]').send_keys(search_value)
            time.sleep(2)

        log.info('Adding the selected filter.')
        driver.find_element_by_xpath('//i[@class="fa fa-plus"]').click()
        time.sleep(2)

        log.info('Clicking on the Search Tunnels button.')
        driver.execute_script('return $("table.fa-search:visible")[0]').click()

        try:
            searched_tunnels = driver.find_elements_by_xpath('//div[contains(@class, "x-grid3-body")]/div[starts-with(@class,"x-grid3-row")]')
            log.info(banner('Total tunnels with the search criteria "%s" : %d'%(search_field+':'+search_value, len(searched_tunnels))))
        except Exception as e: log.error(e)

    def sort_tunnels(self, sort_by, *args):

        driver = self.driver
        tunnels_sorted = False
        log.info('Sorting Devices by: %s'%sort_by)
        
        tab_ids = {
            'her_name': 'x-grid3-td-0',
            'her_interface': 'x-grid3-td-1',
            'admin_status': 'x-grid3-td-2',
            'oper_status': 'x-grid3-td-3',
            'protocol': 'x-grid3-td-4'
        }
        tab_id = tab_ids[sort_by]

        try:
            tab_ele = driver.find_element_by_xpath('//tr[contains(@class, "x-grid3-hd-row")]/td[contains(@class,"%s")]'%tab_id)
            curr_sort = tab_ele.get_attribute('class')
            log.info('curr_sort: %s'%curr_sort)

            log.info('Clicking on %s tab.'%sort_by)
            tab_ele.click()
            time.sleep(1)
        except Exception as e:
            driver_utils.save_screenshot()
            driver.refresh()
            log.error(e)

        log.info('Sorted tunnels with: %s success: %s'%(sort_by, tunnels_sorted))
        return tunnels_sorted

class WorkOrders(OperationsNavigation):
    ''' This class defines all the opertaions under "Tunnel Status" page. '''

    def __init__(self, driver, *arg):
        self.arg = arg
        self.driver = driver
        self.driver_utils = DriverUtils(driver)

    def sort_work_orders(self, sort_by, *args):

        driver = self.driver
        log.info('Sorting WorkOrders by: %s'%sort_by)
        
        tab_ids = {
            'work_order_number': 'x-grid3-td-orderNumber',
            'work_order_name': 'x-grid3-td-workOrderName',
            'role': 'x-grid3-td-role',
            'device_type': 'x-grid3-td-deviceType',
            'name': 'x-grid3-td-name',
            'user_name': 'x-grid3-td-technicianUserName',
            'time_zone': 'x-grid3-td-timeZone',
            'start_date': 'x-grid3-td-startDate',
            'end_date': 'x-grid3-td-endDate',
            'last_update': 'x-grid3-td-lastUpdate',
            'status': 'x-grid3-td-status'
        }
        tab_id = tab_ids[sort_by]
        curr_sort_order = None

        try:
            tab_ele = driver.find_element_by_xpath('//tr[contains(@class, "x-grid3-hd-row")]/td[contains(@class,"%s")]'%tab_id)
            curr_sort = tab_ele.get_attribute('class')
            log.info('curr_sort: %s'%curr_sort)

            log.info('Clicking on %s tab.'%sort_by)
            tab_ele.click()
            time.sleep(1)

            tab_ele = driver.find_element_by_xpath('//tr[contains(@class, "x-grid3-hd-row")]/td[contains(@class,"%s")]'%tab_id)
            curr_sort = tab_ele.get_attribute('class')
            if 'sort-asc' in curr_sort: curr_sort_order = 'Ascending Order'
            elif 'sort-desc' in curr_sort: curr_sort_order = 'Descending Order'
        except Exception as e: log.error(e)

        log.info('curr_sort_order: %s'%curr_sort_order)
        return curr_sort_order

class AppManagementNavigation(ConfigNavigation):
    ''' This class defines all the navigation opertaions under "Device Configuration" page. '''

    def __init__(self, driver, *arg):
        self.arg = arg
        self.driver = driver
        self.driver_utils = DriverUtils(driver)

    def nav_router_group(self, group_name):
        '''
        Method to navigate to Router group.

        :param group_name: Name of the group to navigate.
        :type group_name: str
        '''
        log.info('Navigating to %s' % group_name)
        driver = self.driver
        driver_utils = self.driver_utils
        nav_group_succ = False

        try:
            selected=''
            timeout = time.time() + 60*2
            while timeout>time.time():
                router_group = driver.execute_script('\
                                    return $("span")\
                                    .filter(\
                                        function(){return $(this).text().split(" ")[0].toLowerCase()==="%s".toLowerCase();}\
                                    )[0]'%group_name)
                selected = router_group.find_element_by_xpath('../..').get_attribute('class')
                log.info('router_group selected: %s'%selected)
                if 'x-tree-selected' in selected:
                    nav_group_succ = True
                    break
                time.sleep(1)
                log.info('Clicking on Group: %s'%group_name)
                router_group.click()
                time.sleep(1)
        except Exception as e:
            driver_utils.save_screenshot()
            log.error('Please provide a valid Group name.')

        return nav_group_succ

    def nav_tab(self, tab_name):
        '''
        Method to navigate to a tab.

        :param group_name: Name of the tab to navigate.
        :type group_name: str
        '''

        driver = self.driver
        log.info('Navigating to tab_name: %s'%tab_name)
        #Dictionary of sub_menu id tuples as per the selection.
        tab_ids = {
            'activity_status': 'Activity Status',
            'upload': 'Upload',
            'deployment': 'Deployment'
        }
        #Determine tab id's depending on the requested tab_name.
        tab_id = tab_ids[tab_name]

        try:
            tab_span = driver.find_element_by_xpath('//span[contains(@class, "x-tab-strip-text") and contains(text(), "%s")]'%tab_id)

            log.info('Clicking "%s"'% tab_id)
            tab_span.click()
            time.sleep(2)

            #Wait unitl the clicked page is loaded completely.
            selected = ''
            timeout = time.time() + 2*60
            while 'x-tab-strip-active' not in selected:
                log.info('Checking for sub_menu_active_id')
                selected = tab_span.find_element_by_xpath('../../../..').get_attribute('class')
                log.info('selected: %s' % selected)
                time.sleep(1)
                log.info('Waiting for tab to be active.')
                if time.time()>timeout: break

        except (NoSuchElementException, ElementNotVisibleException) as e: log.info('Element not found: %s' % e)
        except Exception as e: log.info(e)

class DeviceConfiguration(ConfigNavigation):
    ''' This class defines all the applicable opertaions under "Device Configuration" page. '''

    def __init__(self, driver, *arg):
        self.arg = arg
        self.driver = driver
        self.driver_utils = DriverUtils(driver)

    def nav_config_tab(self, tab_name):
        '''
        Method to navigate to groups/config profiles tab for the .

        :param group_name: Name of the tab to navigate.
        :type group_name: str
        '''

        log.info('Navigating to tab_name: %s'%tab_name)
        driver = self.driver
        driver_utils = self.driver_utils

        #Dictionary of config tabs id tuples as per the selection.
        tab_ids = {
            'groups': 'mainPnltree__configGrpsTab',
            'config_profiles': 'mainPnltree__configProfileTab'
        }

        try:
            selected = ''
            tab_id = tab_ids[tab_name]
            timeout=time.time() + 60*2
            while timeout>time.time():
                selected = driver.find_element_by_id('%s'%tab_id).get_attribute('class')
                log.info('selected: %s' % selected)
                if 'x-tab-strip-active' in selected:
                    nav_tab_success = True
                    break

                log.info('Clicking "%s"'% tab_id)
                driver.find_element_by_id('%s'%tab_id).click()
                log.info('Waiting for tab to be active.')
                time.sleep(2)

            driver_utils.wait_for_loading()
        except Exception as e:
            log.error(e)
            driver_utils.save_screenshot()

    def nav_router_group(self, group_name):
        '''
        Method to navigate to a group.

        :param group_name: Name of the group to navigate.
        :type group_name: str
        '''
        log.info('Navigating to %s' % group_name)
        driver = self.driver
        driver_utils = self.driver_utils
        nav_group_succ = False

        try:
            selected=''
            timeout = time.time() + 60*2
            while timeout>time.time():
                config_group = driver.execute_script('\
                                    return $("span")\
                                    .filter(\
                                        function(){return $(this).text().split(" ")[0].toLowerCase()==="%s".toLowerCase();}\
                                    )[0]'%group_name)
                selected = config_group.find_element_by_xpath('../..').get_attribute('class')
                log.info('config_group selected: %s'%selected)
                if 'x-tree-selected' in selected:
                    nav_group_succ = True
                    break
                time.sleep(1)
                log.info('Clicking on Group: %s'%group_name)
                config_group.click()
                time.sleep(1)
        except Exception as e:
            driver_utils.save_screenshot()
            log.error('Please provide a valid Group name.')

        log.info('Navigation for group: %s is sucsess: %s'%(group_name, nav_group_succ))
        return nav_group_succ

    def nav_tab(self, tab_name):
        '''
        Method to navigate to a tab.

        :param group_name: Name of the tab to navigate.
        :type group_name: str
        '''

        driver = self.driver
        driver_utils = self.driver_utils
        nav_tab_success = False

        #Dictionary of sub_menu id tuples as per the selection.
        tab_ids = {
            'group_members': 'configTabs__devicesTab',
            'edit_config_template': 'configTabs__tempTab',
            'edit_ap_config_template': 'configTabs__apTempTab',
            'push_config': 'configTabs__statusTab',
            'transmission_settings': 'configTabs__endpointTransmissionTab'
        }

        #Determine tab id's depending on the requested tab_name.
        if tab_name=='group_properties':
            if driver.find_element_by_id('configTabs__propertyTab').is_displayed():
                tab_id = 'configTabs__propertyTab'
            elif driver.find_element_by_id('configTabs__endpointPropertyTab').is_displayed():
                tab_id = 'configTabs__endpointPropertyTab'
        else:
            tab_id = tab_ids[tab_name]

        try:
            log.info('Navigating to tab: %s'%tab_id)
            log.info('\nClicking "%s"'% tab_id)
            driver.find_element_by_id('%s'%tab_id).click()
            time.sleep(2)

            #Wait unitl the clicked page is loaded completely.
            selected = ''
            timeout=time.time() + 60*2
            while timeout>time.time():
                log.info('Checking for sub_menu_active_id')
                selected = driver.find_element_by_id('%s'%tab_id).get_attribute('class')
                log.info('selected: %s' % selected)
                if 'x-tab-strip-active' in selected:
                    nav_tab_success = True
                    break

                driver.find_element_by_id('%s'%tab_id).click()
                log.info('Waiting for tab to be active.')
                time.sleep(1)

        except (NoSuchElementException, ElementNotVisibleException) as e:
            log.info('Element not found: %s' % e)
        except Exception as e: log.info(e)

        log.info('tab_name:%s Navigation:%s'%(tab_name, nav_tab_success))
        return nav_tab_success

    def sort_devices(self, group_name, sort_by, *args):

        driver = self.driver
        log.info('Sorting Devices by: %s in group: %s'%(sort_by, group_name))
        
        tab_ids = {
            'status': 'x-grid3-td-1',
            'name': 'x-grid3-td-3',
            'ip': 'x-grid3-td-4',
            'last_heard': 'x-grid3-td-5',
            'mesh_prefix_config': 'x-grid3-td-6',
            'mesh_prefix_len_config': 'x-grid3-td-7',
            'mesh_panid__config': 'x-grid3-td-8',
            'mesh_add_config': 'x-grid3-td-9'
        }
        tab_id = tab_ids[sort_by]

        selected=''
        timeout = time.time() + 60*2
        group_span = driver.find_element_by_xpath('//span[contains(text(), "%s")]'%group_name)
        while 'x-tree-selected' not in selected:
            selected = group_span.find_element_by_xpath('../..').get_attribute('class')
            if time.time()>timeout: break
            log.info('Click on "%s" span.'%group_name)
            group_span.click()
            time.sleep(1)
        
        log.info('Click on "group_members" tab.')
        self.nav_tab('group_members')
        time.sleep(1)

        try:
            tab_ele = driver.find_element_by_xpath('//tr[contains(@class, "x-grid3-hd-row")]/td[contains(@class,"%s")]'%tab_id)
            curr_sort = tab_ele.get_attribute('class')
            log.info('curr_sort: %s'%curr_sort)

            log.info('Clicking on %s tab.'%sort_by)
            tab_ele.click()
            time.sleep(1)
        except Exception as e: log.error(e)

    def find_group(self, group_type, group_name):
        '''
        Method to find a router group in FND portal.

        :param group_name: Name of the router group
        :type group_name: str
        '''
        driver = self.driver
        group_found = False

        try:
            anchor_span_elems = driver.find_elements_by_xpath('//a[@class="x-tree-node-anchor"]//span')
            router_groups = [span_elem.text.split(' (')[0].capitalize() for span_elem in anchor_span_elems]
            log.info('Current Device Router Groups: %s' % router_groups)

            if group_name.capitalize() in router_groups:
                group_found = True
                log.info('Given "group_name: %s" found in the exisitng groups.'%group_name)
        except StaleElementReferenceException as e: log.error('StaleElementReferenceException: %s' % e)
        except Exception as e: log.info(e)

        return group_found

    def find_profile(self, profile_type, profile_name):
        '''
        Method to find a config profile in FND portal.

        :param profile_type: Name of the config profile type
        :type profile_type: str
        :param profile_name: Name of the config profile to add
        :type profile_name: str
        '''
        driver = self.driver
        profile_found = False

        try:
            self.nav_config_tab('config_profiles')
            existing_profiles = driver.execute_script('function get_dev_types(){\
                                    a=[];\
                                    $.each($("span:contains(\'%s\')").parent().parent().next().find("a span"), function(i, e){a.push(e.innerHTML)});\
                                    return a;\
                                }\
                                return get_dev_types();'%profile_type)
            log.info('existing_profiles: %s'%existing_profiles)
            if profile_name in existing_profiles:
                profile_found = True
                log.info('Given "profile_name: %s" found in the exisitng config.'%profile_name)
        except Exception as e: log.info(e)

        return profile_found

    def add_group(self, group_type, group_name):
        '''
        Method to add a router group in FND portal.

        :param group_name: Name of the router group to add
        :type group_name: str
        '''
        driver = self.driver
        driver_utils = self.driver_utils
        router_group_added = False
        group_found = self.find_group(group_type, group_name)

        if group_found:
            log.error('There is a group already exisitng with this name. Please choose a differnt name.')
            driver_utils.save_screenshot()
            return router_group_added
        else:
            try:
                log.info('Adding new group: %s' % group_name)
                time.sleep(2)
                driver.find_element_by_xpath('//div[@id="configurationGroups_toolsContainer"]//div').click()
                time.sleep(1)
                log.info('\nClearing input')
                driver.find_element_by_xpath('//input[@id="addFormGroupName"]').clear()
                time.sleep(1)
                log.info('\nEntering group name: %s'%group_name)
                driver.find_element_by_xpath('//input[@id="addFormGroupName"]').send_keys(group_name)
                time.sleep(1)
                log.info('\nClicking dropdown.')
                driver.find_element_by_xpath('//input[@id="deviceCategoryCombo"]').click()
                time.sleep(1)
                log.info('\nSelecting %s.'%group_type)
                driver.find_element_by_xpath('//div[contains(@class, "x-combo-list-item") and contains(text(), "%s")]'%group_type.capitalize()).click()
                time.sleep(1)
                log.info('\nClicking Add.')
                driver.find_element_by_id('groupAddBtn').click()
                time.sleep(3)

                add_error = driver.execute_script('return $(\'span:contains("Error")\').length>0 ? $(".ext-mb-text").text() : ""')
                if add_error:
                    log.info('add_error: %s'%add_error)
                    driver_utils.save_screenshot()
                    driver.execute_script('$(\'button:contains("OK")\').click()')

                    close_button = driver_utils.get_visible_div_by_class('x-tool-close')
                    log.info('\nClick on close button.')
                    close_button.click()
                else:
                    router_group_added = True

            except Exception as e:
                log.error('Unable to add router group.\n%s'%e)
                driver_utils.save_screenshot()
                return router_group_added

        #Waiting till new group is added.
        router_groups = []
        timeout=time.time() + 60*2
        while timeout>time.time():
            #Finding anchor tags with a class "x-tree-node-anchor". This is a list of configuration groups on the portal.
            anchor_span_elems = driver.find_elements_by_xpath('//a[@class="x-tree-node-anchor"]//span')
            router_groups = [span_elem.text.split(' (')[0].capitalize() for span_elem in anchor_span_elems]
            log.info('New device router groups: %s' % router_groups)
            if group_name.capitalize() in router_groups: break
            time.sleep(2)

        log.info('group_name: %s router_group_added: %s'%(group_name, router_group_added))
        return router_group_added

    def delete_group(self, group_type, group_name):
        '''
        Method to delete a router group in FND portal.

        :param group_name: Name of the router group to delete
        :type group_name: str
        '''

        driver = self.driver
        driver_utils = self.driver_utils
        router_group_deleted = False

        try:
            group_found = self.find_group(group_type, group_name)
            if not group_found:
                log.error('There is a no group with this name. Please choose a differnt name.')
                driver_utils.save_screenshot()
                return router_group_deleted

            span_element = driver.find_element_by_xpath('//span[contains(text(), "%s")]'%group_type.upper())
            x_tree_node = span_element.find_element_by_xpath('../../..')
            current_groups = x_tree_node.find_elements_by_xpath('ul/li/div/a/span')

            #Finding the delete button for the given group_name and click it.
            for current_group in current_groups:
                if current_group.text.split(' (')[0].capitalize() == group_name.capitalize():
                    del_button = current_group.find_element_by_xpath('following-sibling::div/div[@class="x-tool x-tool-ciscoDelete"]')
                    time.sleep(2)
                    driver.execute_script('$(arguments[0]).click();', del_button)
                    time.sleep(2)
                    break

            #Confirming the delete in popup.
            log.info('Confirming the delete.')
            driver.find_element_by_xpath('//button[contains(text(), "Yes")]').click()
            time.sleep(1)
            driver.find_element_by_xpath('//button[contains(text(), "OK")]').click()
            log.info('Given router group deleted.')

            router_group_deleted = True
        except Exception as e:
            log.error('Unable to delete router group.')
            log.info(e)

        log.info('group_name: %s router_group_deleted: %s'%(group_name, router_group_deleted))
        return router_group_deleted

    def add_profile(self, profile_type, profile_name):
        '''
        Method to add a config profile in FND portal.

        :param profile_type: Name of the config profile type
        :type profile_type: str
        :param profile_name: Name of the config profile to add
        :type profile_name: str
        '''
        driver = self.driver
        driver_utils = self.driver_utils
        profile_added = False

        try:
            profile_found = self.find_profile(profile_type, profile_name)
            if profile_found:
                log.error('There is a profile already exisitng with this name. Please choose a differnt name.')
                driver_utils.save_screenshot()
                return profile_added

            log.info('Adding new profile: %s' % profile_name)
            time.sleep(2)
            log.info('Clicking on Profile Add button.')
            driver.find_element_by_xpath('//div[contains(@class, "x-tool-ciscoProfileAdd")]').click()
            time.sleep(1)
            log.info('Clicking on Profile Selector.')
            driver.find_element_by_id('profileTypeCombo').click()
            time.sleep(1)
            log.info('Selecting Profile Type.')
            driver.execute_script('return $(".x-combo-list-item:contains(\'%s\'):visible")[0]'%profile_type).click()
            time.sleep(1)
            driver.find_element_by_id('profileName').clear()
            time.sleep(1)
            log.info('Entering the Profile Name.')
            driver.find_element_by_id('profileName').send_keys(profile_name)
            time.sleep(1)

            invalid_icon = driver.execute_script('return $("#x-form-el-form-ch-file .x-form-invalid-icon").css("visibility")')
            log.info('invalid_icon: %s'%invalid_icon)
            if invalid_icon=='visible': raise Exception('Should enter all the required fields.')
            time.sleep(2)

            log.info('Clicking on Add button.')
            driver.execute_script('return $("button:contains(\'Add\'):visible")[0]').click()
            time.sleep(1)

            add_error = driver.execute_script('return $(\'span:contains("Error")\').length>0 ? $(".ext-mb-text").text() : ""')
            if add_error:
                log.info('add_error: %s'%add_error)
                driver_utils.save_screenshot()
                log.info('Clicking on OK button.')
                driver.execute_script('return $("button:contains(\'OK\'):visible")').click()
                time.sleep(1)
                log.info('Click on close button.')
                driver.execute_script('return $(".x-tool-close:visible")').click()
                time.sleep(1)
            else:
                profile_added = True
        except Exception as e:
            log.error('Unable to add config profile.')
            driver_utils.save_screenshot()
            log.error(e)
            driver.refresh()
            time.sleep(3)
            return profile_added

        #Waiting till new profile is added.
        profile_groups = []
        timeout=time.time() + 60*2
        while timeout>time.time():
            existing_profiles = driver.execute_script('function get_dev_types(){\
                                    a=[];\
                                    $.each($("span:contains(\'%s\')").parent().parent().next().find("a span"), function(i, e){a.push(e.innerHTML)});\
                                    return a;\
                                }\
                                return get_dev_types();'%profile_type)
            log.info('New config profiles: %s' % existing_profiles)
            if profile_name in existing_profiles: break
            time.sleep(2)

        log.info('profile_name: %s under, "%s" added: %s'%(profile_name, profile_type, profile_added))
        return profile_added

    def delete_profile(self, profile_type, profile_name):
        '''
        Method to delete a config profile in FND portal.

        :param profile_type: Name of the config profile type
        :type profile_type: str
        :param profile_name: Name of the config profile to delete
        :type profile_name: str
        '''
        log.info('Deleting profile: %s under category: %s'%(profile_name, profile_type))
        driver = self.driver
        driver_utils = self.driver_utils
        profile_delted = False

        try:
            self.nav_config_tab('config_profiles')
            profile_element = driver.execute_script('function get_profile(){\
                                profile=undefined;\
                                $.each($("span:contains(\'%s\')").parent().parent().next().find("a span"), function(i, e){if(e.innerHTML==\'%s\') profile=e});\
                                return profile;\
                              }\
                              return get_profile();'%(profile_type, profile_name))

            if not profile_element: 
                log.error('Please provide a valid profile name.')
                return profile_delted
            log.info('Hovering on %s'%profile_name)
            hover = ActionChains(driver).move_to_element(profile_element)
            hover.perform()
            time.sleep(1)

            log.info('Clicking in the Delete menu.')
            driver.execute_script('return $(".x-tool-ciscoProfileDelete:visible")[0];').click()
            time.sleep(1)

            log.info('Veriying the popup header "Confirm"')
            confirm_status = driver.execute_script('return $(".x-window-dlg .x-window-header-text").text()')
            log.info('Clicking on "Yes" button.')
            driver.find_element_by_xpath('//div[contains(@class, "x-window-plain")]//button[contains(text(), "Yes")]').click()
            time.sleep(1)
            log.info('Veriying the popup header "Status"')
            popup_status = driver.execute_script('return $(".x-window-dlg .x-window-header-text").text()')
            log.info('Clicking on OK button.')
            driver.execute_script('return $(".x-window-dlg button:contains(\'OK\'):visible")[0]').click()
            time.sleep(1)

            delete_error = driver.execute_script('return $(\'span:contains("Error")\').length>0 ? $(".ext-mb-text").text() : ""')
            if delete_error:
                log.info('delete_error: %s'%delete_error)
                driver_utils.save_screenshot()
                log.info('Clicking on OK button.')
                driver.execute_script('return $(".x-window-dlg button:contains(\'OK\'):visible")[0]').click()
                time.sleep(1)
                log.info('Closing the popup.')
                driver.execute_script('return $("span:contains(\'Rename Profile\')").prev()[0]').click()
                time.sleep(1)

            log.info('confirm_status: %s'%confirm_status)
            if confirm_status!='Confirm': raise Exception('Confirm popup not shown.')
            time.sleep(1)
            log.info('popup_status: %s'%popup_status)
            if popup_status!='Status': raise Exception('Status popup not shown.')
            time.sleep(1)

        except Exception as e:
            fail_flag = True
            log.error(e)
            log.error('Unable to delete config profile.')
            driver_utils.save_screenshot()
            driver.refresh()
            time.sleep(5)

        #Waiting till profile is delted from UI.
        profile_groups = []
        timeout=time.time() + 60*2
        while timeout>time.time():
            time.sleep(2)
            existing_profiles = driver.execute_script('function get_profiles(){\
                                    a=[];\
                                    $.each($("span:contains(\'%s\')").parent().parent().next().find("a span"), function(i, e){a.push(e.innerHTML)});\
                                    return a;\
                                }\
                                return get_profiles();'%profile_type)
            log.info('existing_profiles: %s' % existing_profiles)
            if profile_name not in existing_profiles:
                profile_delted = True
                break

        log.info('profile_name: %s under, "%s" deleted: %s'%(profile_name, profile_type, profile_delted))
        return profile_delted

    def edit_profile(self, profile_type, profile_name, profile_name_new):
        '''
        Method to edit a config profile in FND portal.

        :param profile_type: Name of the config profile type
        :type profile_type: str
        :param profile_name: Name of the config profile to delete
        :type profile_name: str
        :param profile_name_new: Name of the config profile to rename
        :type profile_name_new: str
        '''
        driver = self.driver
        driver_utils = self.driver_utils
        profile_edited = False

        try:
            self.nav_config_tab('config_profiles')
            profile_element = driver.execute_script('return $("span:contains(\'%s\')").parent().parent().next().\
                        find("a span").filter(function(){return $(this).text()==="%s";})[0]'
                        %(profile_type, profile_name))

            if not profile_element: 
                log.error('Please provide a valid profile name.')
                return profile_edited

            log.info('Hovering on %s'%profile_name)
            hover = ActionChains(driver).move_to_element(profile_element)
            hover.perform()

            log.info('Clicking on edit button.')
            edit_button = driver.execute_script('return $(".x-tool-ciscoProfileEdit:visible")[0];')
            edit_button.click()
            log.info('Veriying the popup header "Rename Profile"')
            popup_status = driver.execute_script('return $(".x-window-header-text").text()')
            if 'Rename Profile' not in popup_status: raise Exception('Confirm popup not shown.')

            log.info('Clearing the exisitng profile name.')
            driver.find_element_by_id('profileRename').clear()
            time.sleep(1)
            log.info('Entering new profile name.')
            driver.find_element_by_id('profileRename').send_keys(profile_name_new)
            time.sleep(1)
            log.info('Clicking on OK button.')
            ok_buttons = driver.execute_script('function ok(){\
                                    a=[];\
                                    $.each($("button:contains(\'OK\'):visible"), function(i, e){a.push(e)});\
                                    return a;\
                                }return ok();')
            ok_button = [b for b in ok_buttons if b.is_displayed()][0]
            ok_button.click()
            time.sleep(1)

            edit_error = driver.execute_script('return $(\'span:contains("Error")\').length>0 ? $(".ext-mb-text").text() : ""')
            if edit_error:
                log.info('edit_error: %s'%edit_error)
                driver_utils.save_screenshot()
                log.info('Clicking on OK button.')
                driver.execute_script('return $(".x-window-dlg button:contains(\'OK\'):visible")[0]').click()
                time.sleep(1)
                log.info('Click on close button.')
                driver.execute_script('return $(".x-tool-close:visible")[0]').click()
                time.sleep(1)
            else:
                log.info('Veriying the popup header "Status"')
                popup_status = driver.execute_script('return \
                    $(".x-window-header-text")[$(".x-window-header-text").length-1].innerHTML')
                if popup_status!='Status': raise Exception('Status popup not shown.')
                
                edit_status = driver.execute_script('return $(".ext-mb-text:visible").text()')
                if edit_status!='Rename successful.': raise Exception('Edit Status not shown.')

                log.info('Clicking on OK button.')
                driver.execute_script('return $("button:contains(\'OK\'):visible")[1]').click()
                time.sleep(1)

        except Exception as e:
            fail_flag = True
            driver_utils.save_screenshot()
            log.error(e)
            driver.refresh()
            time.sleep(5)

        #Waiting till profile is delted from UI.
        profile_groups = []
        timeout=time.time() + 60*2
        while timeout>time.time():
            time.sleep(2)
            existing_profiles = driver.execute_script('function get_dev_types(){\
                                    a=[];\
                                    $.each($("span:contains(\'%s\')").parent().parent().next().find("a span"), function(i, e){a.push(e.innerHTML)});\
                                    return a;\
                                }\
                                return get_dev_types();'%profile_type)
            log.info('config profiles: %s' % existing_profiles)
            if profile_name_new in existing_profiles:
                profile_edited = True
                break

        return profile_edited

    def get_config_profile(self, profile_type, profile_name, **kwargs):
        '''
        Method to update a config profile.

        :param profile_type: Name of the config profile type
        :type profile_type: str
        :param profile_name: Name of the config profile to delete
        :type profile_name: str
        '''
        driver = self.driver
        driver_utils = self.driver_utils
        config_profile = {}

        try:
            self.nav_config_tab('config_profiles')
            profile_element = driver.execute_script('function get_profile(){\
                                profile=undefined;\
                                $.each($("span:contains(\'%s\')").parent().parent().next().find("a span"), function(i, e){if(e.innerHTML==\'%s\') profile=e});\
                                return profile;\
                              }\
                              return get_profile();'%(profile_type, profile_name))
            
            log.info('Clicking on the config profile.')
            if profile_element: profile_element.click()
            else: raise Exception('Given profile not found.')

            if profile_type=='MAP-T Profile':

                dmrIpv6Pfx = driver.find_element_by_id('dmrIpv6Pfx').get_attribute('value')
                dmrIpv6PfxLen = driver.find_element_by_id('dmrIpv6PfxLen').get_attribute('value')
                bmrIpv4Pfx = driver.find_element_by_id('bmrIpv4Pfx').get_attribute('value')
                bmrIpv4PfxLen = driver.find_element_by_id('bmrIpv4PfxLen').get_attribute('value')
                bmrEaBitsLen = driver.find_element_by_id('bmrEaBitsLen').get_attribute('value')

                config_profile['dmrIpv6Pfx'] = dmrIpv6Pfx
                config_profile['dmrIpv6PfxLen'] = dmrIpv6PfxLen
                config_profile['bmrIpv4Pfx'] = bmrIpv4Pfx
                config_profile['bmrIpv4PfxLen'] = bmrIpv4PfxLen
                config_profile['bmrEaBitsLen'] = bmrEaBitsLen

        except Exception as e:
            driver_utils.save_screenshot()
            log.error(e)
        
        log.info('config_profile: %s'%json.dumps(config_profile, indent=4, sort_keys=True))
        return config_profile

    def add_fmr_profile_rule(self, profile_name, **kwargs):
        '''
        Method to add a config profile in FND portal.

        :param profile_type: Name of the config profile type
        :type profile_type: str
        :param profile_name: Name of the config profile to add
        :type profile_name: str
        '''
        driver = self.driver
        driver_utils = self.driver_utils
        fmr_profile_rule_added = False

        ipv4_prefix = kwargs.get('ipv4_prefix', None)
        ipv4_prefix_len = kwargs.get('ipv4_prefix_len', None)
        ea_bits_len = kwargs.get('ea_bits_len', None)

        try:
            self.nav_config_tab('config_profiles')
            log.info('\nFinding the given profile name.')
            profile_element = driver.execute_script('function get_profile(){\
                                profile=undefined;\
                                $.each($("span:contains(\'FMR Profile\')").parent().parent().next().find("a span"),\
                                     function(i, e){if(e.innerHTML==\'%s\') profile=e});\
                                return profile;\
                              }\
                              return get_profile();'%(profile_name))
            if not profile_element: 
                log.error('Please provide a valid profile name.')
                return fmr_profile_rule_added

            log.info('Clicking on profile: %s' % profile_name)
            profile_element.click()
            time.sleep(1)

            add_rule_button = driver.execute_script('return $(".fa-plus:visible")[0]')
            if not add_rule_button:
                log.error('Add Rule not found.')
                return fmr_profile_rule_added
            log.info('Clicking on "Add Rule" button.')
            add_rule_button.click()
            time.sleep(1)

            new_ipv4_element = driver.execute_script('return $(".x-grid3-col-fmrIpv4Prefix:last")[0]')
            new_ipv4_len_element = driver.execute_script('return $(".x-grid3-col-fmrIpv4PrefixLen:last")[0]')
            ea_bit_len_element = driver.execute_script('return $(".x-grid3-col-fmrEaBitsLen:last")[0]')

            log.info('Clicking on "IPV4 Prefix" input.')
            driver.execute_script('return $(".x-grid3-col-fmrIpv4Prefix:last")[0].click()')
            time.sleep(1)
            ipv4_prefix_input = driver.execute_script('return $(".x-form-field:visible")[0]')
            log.info('Clearing the exisitng value.')
            ipv4_prefix_input.clear()
            time.sleep(1)
            log.info('Entering new value: %s'%ipv4_prefix)
            for i in ipv4_prefix.split('.'):
                time.sleep(1)
                ipv4_prefix_input.send_keys(int(i))
                ipv4_prefix_input.send_keys('.')
            ipv4_prefix_input.send_keys(Keys.BACKSPACE)
            time.sleep(1)
            ipv4_prefix_input.send_keys(Keys.ENTER)
            time.sleep(1)

            if ipv4_prefix_len:
                log.info('Clicking on "IPV4 Prefix Length" input.')
                driver.execute_script('return $(".x-grid3-col-fmrIpv4PrefixLen:last")[0].click()')
                time.sleep(1)
                ipv4_prefix_len_input = driver.execute_script('return $(".x-form-field:visible")[1]')
                log.info('Clearing the exisitng value.')
                ipv4_prefix_len_input.clear()
                time.sleep(1)
                log.info('Entering new value: %s'%ipv4_prefix_len)
                ipv4_prefix_len_input.send_keys(ipv4_prefix_len)
                time.sleep(1)
                ipv4_prefix_len_input.send_keys(Keys.ENTER)
                time.sleep(1)

            if ea_bits_len:
                log.info('Clicking on "EA Bits Length" input.')
                driver.execute_script('return $(".x-grid3-col-fmrEaBitsLen:last")[0].click()')
                time.sleep(1)
                ea_bits_len_input = driver.execute_script('return $(".x-form-field:visible")[2]')
                log.info('Clearing the exisitng value.')
                ea_bits_len_input.clear()
                time.sleep(1)
                log.info('Entering new value: %s'%ea_bits_len)
                ea_bits_len_input.send_keys(ea_bits_len)
                time.sleep(1)
                ea_bits_len_input.send_keys(Keys.ENTER)
                time.sleep(1)

            log.info('Saving the changes.')
            driver.execute_script('return $(".fa-floppy-o:visible")[0]').click()
            time.sleep(1)
            add_error = driver.execute_script('return $(\'span:contains("Error")\').length>0 ? $(".ext-mb-text").text() : ""')
            log.info('add_error: %s'%add_error)
            if add_error: driver_utils.save_screenshot()
            else: fmr_profile_rule_added = True
            driver.execute_script('return $("button:contains(\'OK\')")[0]').click()
            time.sleep(1)
        except Exception as e:
            log.error('Unable to add config profile.')
            driver_utils.save_screenshot()
            log.error(e)
            driver.refresh()
            time.sleep(3)

        log.info(banner('Profile rule with %s under %s is added: %s'%(kwargs, profile_name, fmr_profile_rule_added)))
        return fmr_profile_rule_added

    def add_dscp_profile_rule(self, profile_name, **kwargs):
        '''
        Method to add a config profile in FND portal.

        :param profile_name: Name of the config profile to add
        :type profile_name: str
        '''
        driver = self.driver
        driver_utils = self.driver_utils
        dscp_profile_rule_added = False

        source_ipv4 = kwargs.get('source_ipv4', None)
        dscp_marking = kwargs.get('dscp_marking', None)
        if source_ipv4==None or dscp_marking==None:
            log.error('Provide both source_ipv4 and dscp_marking.')
            return dscp_profile_rule_added

        try:
            self.nav_config_tab('config_profiles')
            profile_element = driver.execute_script('function get_profile(){\
                                profile=undefined;\
                                $.each($("span:contains(\'DSCP Profile\')").parent().parent().next().find("a span"),\
                                    function(i, e){if(e.innerHTML==\'%s\') profile=e});\
                                return profile;\
                              }\
                              return get_profile();'%(profile_name))
            if not profile_element: 
                log.error('Please provide a valid profile name.')
                return dscp_profile_rule_added

            log.info('Clicking on profile: %s' % profile_name)
            profile_element.click()
            time.sleep(1)

            add_rule_button = driver.execute_script('return $(".fa-plus:visible")[0]')
            if not add_rule_button:
                log.error('Add Rule not found.')
                return dscp_profile_rule_added
            log.info('Clicking on "Add Rule" button.')
            add_rule_button.click()
            time.sleep(1)

            new_ipv4_element = driver.execute_script('return $(".x-grid3-col-sourceIpAddr:last")[0]')
            dscp_marking_element = driver.execute_script('return $(".x-grid3-col-dscpMarking:last")[0]')

            actionChains = ActionChains(driver)
            log.info('Clicking on source IPV4 input.')
            actionChains.double_click(new_ipv4_element).perform()
            assigned_num = driver.execute_script('return $(".x-form-field:visible")[0]')
            log.info('Clearing the exisitng value.')
            assigned_num.clear()
            time.sleep(1)
            log.info('Entering new value: %s'%source_ipv4)
            for i in source_ipv4.split('.'):
                time.sleep(1)
                assigned_num.send_keys(int(i))
                assigned_num.send_keys('.')
            assigned_num.send_keys(Keys.BACKSPACE)

            actionChains = ActionChains(driver)
            log.info('Clicking on DSCP Marking input.')
            actionChains.click(dscp_marking_element).perform()
            driver.execute_script('return $(".x-form-arrow-trigger:visible")[0]').click()
            time.sleep(1)
            if dscp_marking == 'User Controlled':
                driver.execute_script('return $(".x-combo-list-item:contains(\'%s\'):visible")[1]'%dscp_marking).click()
            else:
                driver.execute_script('return $(".x-combo-list-item:contains(\'%s\'):visible")[0]'%dscp_marking).click()
            time.sleep(1)

            log.info('Clicking on Save button.')
            driver.find_element_by_id('saveDscpDetails').click()
            time.sleep(1)

            add_error = driver.execute_script('return $(\'span:contains("Error")\').length>0 ? $(".ext-mb-text").text() : ""')
            if add_error:
                log.info('add_error: %s'%add_error)
                driver_utils.save_screenshot()
            else: dscp_profile_rule_added = True
            log.info('Clicking on OK button.')
            driver.execute_script('return $("button:contains(\'OK\'):visible")[0]').click()
            time.sleep(1)
            log.info('Clicking on profile: %s' % profile_name)
            profile_element.click()
        except Exception as e:
            log.error('Unable to add config profile.')
            driver_utils.save_screenshot()
            log.error(e)
            driver.refresh()
            time.sleep(3)
            return dscp_profile_rule_added

        log.info(banner('Profile rule with %s under %s is added: %s'%(kwargs, profile_name, dscp_profile_rule_added)))
        return dscp_profile_rule_added

    def add_nat44_mappings(self, profile_name, **kwargs):
        driver = self.driver
        driver_utils = self.driver_utils
        mapping_ip_added = False
        mapping_ips = kwargs.get('mapping_ips', None)
        log.info(banner('Adding NAT44 Mapping entries with: %s'%mapping_ips))

        if mapping_ips==None:
            log.error('Provide ip\'s to add.')
            return mapping_ip_added

        try:
            self.nav_config_tab('config_profiles')
            profile_element = driver.execute_script('function get_profile(){\
                                profile=undefined;\
                                $.each($("span:contains(\'NAT44 Profile\')").parent().parent().next().find("a span"), function(i, e){if(e.innerHTML==\'%s\') profile=e});\
                                return profile;\
                              }\
                              return get_profile();'%(profile_name))
            if not profile_element: 
                log.error('Please provide a valid profile name.')
                return mapping_ip_added
            profile_element.click()
            time.sleep(1)

            for mapping_ip in mapping_ips:
                log.info('Click on Add IP button.')
                add_rule_button = driver.execute_script('return $(".fa-plus:visible")[0]')
                add_rule_button.click()
                time.sleep(1)

                ip_values = mapping_ips[mapping_ip]
                internal_port = ip_values[0]
                external_port = ip_values[1]
                port_incrmenet = ip_values[2]
                print(internal_port, external_port, port_incrmenet)

                log.info('Clicking on "IPV4 Address" input.')
                driver.execute_script('return $(".x-grid3-col-internalAddr:last")[0].click()')
                time.sleep(1)
                form_fields = driver.execute_script('a=[];$.each($(".x-grid3-scroller .x-form-field:visible"), \
                                                    function(i,e){a.push(e);}); return a;')
                ipv4_input = [form_field for form_field in form_fields if form_field.is_displayed()][0]
                log.info('Clearing the exisitng ipv4.')
                ipv4_input.clear()
                time.sleep(1)
                log.info('Entering new value: %s'%mapping_ip)
                ipv4_input.send_keys(mapping_ip)
                time.sleep(1)
                ipv4_input.send_keys(Keys.ENTER)
                time.sleep(1)

                if internal_port!=0:
                    driver.execute_script('return $(".x-grid3-col-internalPort:last")[0].click()')
                    time.sleep(1)
                    form_fields = driver.execute_script('a=[];$.each($(".x-grid3-scroller .x-form-field:visible"), \
                                                    function(i,e){a.push(e);}); return a;')
                    port_input = [form_field for form_field in form_fields if form_field.is_displayed()][0]
                    log.info('Clearing the exisitng internal_port.')
                    port_input.clear()
                    time.sleep(1)
                    log.info('Entering new value: %d'%internal_port)
                    port_input.send_keys(internal_port)
                    time.sleep(1)
                    port_input.send_keys(Keys.ENTER)
                    time.sleep(1)
                if external_port!=0:
                    driver.execute_script('return $(".x-grid3-col-externalPort:last")[0].click()')
                    time.sleep(1)
                    form_fields = driver.execute_script('a=[];$.each($(".x-grid3-scroller .x-form-field:visible"), \
                                                    function(i,e){a.push(e);}); return a;')
                    port_input = [form_field for form_field in form_fields if form_field.is_displayed()][0]
                    log.info('Clearing the exisitng external_port.')
                    port_input.clear()
                    time.sleep(1)
                    log.info('Entering new value: %d'%external_port)
                    port_input.send_keys(external_port)
                    time.sleep(1)
                    port_input.send_keys(Keys.ENTER)
                    time.sleep(1)
                if port_incrmenet!=1:
                    driver.execute_script('return $(".x-grid3-col-portIncrement:last")[0].click()')
                    time.sleep(1)
                    form_fields = driver.execute_script('a=[];$.each($(".x-grid3-scroller .x-form-field:visible"), \
                                                    function(i,e){a.push(e);}); return a;')
                    port_input = [form_field for form_field in form_fields if form_field.is_displayed()][0]
                    log.info('Clearing the exisitng internal_port.')
                    port_input.clear()
                    time.sleep(1)
                    log.info('Entering new value: %d'%internal_port)
                    port_input.send_keys(internal_port)
                    time.sleep(1)
                    port_input.send_keys(Keys.ENTER)
                    time.sleep(1)

            log.info('Clicking on Save button.')
            driver.execute_script('return $(".fa-floppy-o:visible")[0]').click()
            time.sleep(1)

            save_error = driver.execute_script('return $(\'span:contains("Error")\').length>0 ? $(".ext-mb-text").text() : ""')
            if save_error:
                log.info('save_error: %s'%save_error)
                driver_utils.save_screenshot()
            else: mapping_ip_added = True
            log.info('Clicking on OK button.')
            driver.execute_script('return $("button:contains(\'OK\'):visible")[0]').click()
            time.sleep(1)

        except Exception as e:
            log.error('Unable to add NAT44 Mapping IP.')
            driver_utils.save_screenshot()
            log.error(e)
            driver.refresh()
            time.sleep(3)

        log.info('NAT44 Mapping entries added: %s'%mapping_ip_added)
        return mapping_ip_added

    def add_dhcp_client_profile_rule(self, profile_name, **kwargs):
        '''
        Method to add a dhcp client profile rule in FND portal.

        :param profile_name: Name of the config profile to add
        :type profile_name: str
        '''
        driver = self.driver
        driver_utils = self.driver_utils
        dhcp_profile_rule_added = False

        client_id = kwargs.get('client_id', None)
        host_address = kwargs.get('host_address', None)
        if client_id==None or host_address==None:
            log.error('Provide both client_id and host_address.')
            return dhcp_profile_rule_added

        try:
            self.nav_config_tab('config_profiles')
            profile_element = driver.execute_script('function get_profile(){\
                                profile=undefined;\
                                $.each($("span:contains(\'DHCP Client Profile\')").parent().parent().next().find("a span"),\
                                    function(i, e){if(e.innerHTML==\'%s\') profile=e});\
                                return profile;\
                              }\
                              return get_profile();'%(profile_name))
            if not profile_element: 
                log.error('Please provide a valid profile name.')
                return dhcp_profile_rule_added

            log.info('Clicking on profile: %s' % profile_name)
            profile_element.click()
            time.sleep(1)

            add_rule_button = driver.execute_script('return $(".fa-plus:visible")[0]')
            if not add_rule_button:
                log.error('Add Rule not found.')
                return dhcp_profile_rule_added
            log.info('Clicking on "Add Rule" button.')
            add_rule_button.click()
            time.sleep(1)

            client_id_element = driver.execute_script('return $(".x-grid3-col-clientId:last")[0]')
            host_add_element = driver.execute_script('return $(".x-grid3-col-hostAddress:last")[0]')

            actionChains = ActionChains(driver)
            log.info('Clicking on Client ID input.')
            actionChains.double_click(client_id_element).perform()
            client_id_input = driver.execute_script('return $(".x-form-field:visible")[0]')
            log.info('Clearing the exisitng value.')
            client_id_input.clear()
            time.sleep(1)
            log.info('Entering new client_id value: %s'%client_id)
            client_id_input.send_keys(client_id)

            actionChains = ActionChains(driver)
            log.info('Clicking on Host Address input.')
            actionChains.click(host_add_element).perform()
            host_add_input = driver.execute_script('return $(".x-form-field:visible")[1]')
            log.info('Clearing the exisitng value.')
            host_add_input.clear()
            time.sleep(1)
            log.info('Entering new host_address value: %s'%host_address)
            host_add_input.send_keys(host_address)
            time.sleep(1)
            host_add_input.send_keys(Keys.ENTER)
            time.sleep(1)

            log.info('Clicking on Save button.')
            driver.find_element_by_id('saveDhcpClientDetails').click()
            time.sleep(1)

            add_error = driver.execute_script('return $(\'span:contains("Error")\').length>0 ? $(".ext-mb-text").text() : ""')
            if add_error:
                log.info('add_error: %s'%add_error)
                driver_utils.save_screenshot()
            else: dhcp_profile_rule_added = True
            log.info('Clicking on OK button.')
            driver.execute_script('return $("button:contains(\'OK\'):visible")[0]').click()
            time.sleep(1)
            log.info('Clicking on profile: %s' % profile_name)
            profile_element.click()
        except Exception as e:
            log.error('Unable to add dhcp client profile.')
            driver_utils.save_screenshot()
            log.error(e)
            driver.refresh()
            time.sleep(3)

        log.info('\n\nDHCP Client Profile rule with %s under %s is added: %s\n\n'
                %(kwargs, profile_name, dhcp_profile_rule_added))
        return dhcp_profile_rule_added

    def update_map_t_config_profile(self, profile_name, **kwargs):
        '''
        Method to update a config profile.

        :param profile_type: Name of the config profile type
        :type profile_type: str
        :param profile_name: Name of the config profile to delete
        :type profile_name: str
        '''
        driver = self.driver
        driver_utils = self.driver_utils
        profile_updated = False

        try:
            self.nav_config_tab('config_profiles')
            profile_element = driver.execute_script('function get_profile(){\
                                profile=undefined;\
                                $.each($("span:contains(\'MAP-T Profile\')").parent().parent().next().find("a span"), \
                                function(i, e){if(e.innerHTML==\'%s\') profile=e});\
                                    return profile;\
                              }\
                              return get_profile();'%(profile_name))
            
            log.info('Clicking on the config profile.')
            if profile_element: profile_element.click()
            else: raise Exception('Given profile not found.')

            dmrIpv6Pfx = kwargs.get('dmrIpv6Pfx', None)
            dmrIpv6PfxLen = kwargs.get('dmrIpv6PfxLen', None)
            bmrIpv4Pfx = kwargs.get('bmrIpv4Pfx', None)
            bmrIpv4PfxLen = kwargs.get('bmrIpv4PfxLen', None)
            bmrEaBitsLen = kwargs.get('bmrEaBitsLen', None)

            dmr_Ipv6Pfx = driver.find_element_by_id('dmrIpv6Pfx')
            dmr_Ipv6PfxLen = driver.find_element_by_id('dmrIpv6PfxLen')
            bmr_Ipv4Pfx = driver.find_element_by_id('bmrIpv4Pfx')
            bmr_Ipv4PfxLen = driver.find_element_by_id('bmrIpv4PfxLen')
            bmr_EaBitsLen = driver.find_element_by_id('bmrEaBitsLen')

            log.info('Clearing dmr_Ipv6Pfx: %s'%dmr_Ipv6Pfx.get_attribute('value'))
            dmr_Ipv6Pfx.clear()
            time.sleep(1)
            log.info('Entering value: %s'%str(dmrIpv6Pfx))
            dmr_Ipv6Pfx.send_keys(str(dmrIpv6Pfx))
            time.sleep(1)

            log.info('Cliking dmr_Ipv6PfxLen%s'%dmr_Ipv6PfxLen.get_attribute('value'))
            driver.find_element_by_id('dmrIpv6PfxLen').click()
            time.sleep(1)
            log.info('Entering value: %s'%str(dmrIpv6PfxLen))
            driver.execute_script('return $(".x-combo-list-item:visible").filter(function(){return $(this).text()==="%s";})[0]'%str(dmrIpv6PfxLen)).click()
            time.sleep(1)

            log.info('Clearing bmrIpv4Pfx: %s'%bmr_Ipv4Pfx.get_attribute('value'))
            bmr_Ipv4Pfx.clear()
            time.sleep(1)
            log.info('Entering value: %s'%str(bmrIpv4Pfx))
            bmr_Ipv4Pfx.send_keys(str(bmrIpv4Pfx))
            time.sleep(1)

            log.info('Clearing bmrIpv4PfxLen: %s'%bmr_Ipv4PfxLen.get_attribute('value'))
            bmr_Ipv4PfxLen.clear()
            time.sleep(1)
            log.info('Entering value: %s'%str(bmrIpv4PfxLen))
            bmr_Ipv4PfxLen.send_keys(str(bmrIpv4PfxLen))
            time.sleep(1)
            
            log.info('Clearing bmrEaBitsLen: %s'%bmr_EaBitsLen.get_attribute('value'))
            bmr_EaBitsLen.clear()
            time.sleep(1)
            log.info('Entering value: %s'%str(bmrEaBitsLen))
            bmr_EaBitsLen.send_keys(str(bmrEaBitsLen))
            time.sleep(1)

            log.info('Saving the changes.')
            driver.execute_script('$(".fa-floppy-o:visible").click()')
            time.sleep(2)
            log.info('Clicking on OK.')
            driver.find_element_by_xpath('//button[contains(text(), "OK")]').click()
            time.sleep(2)
            profile_updated = True

        except Exception as e:
            driver_utils.save_screenshot()
            log.error(e)

        log.info('Profile updated under %s : %s'%(profile_name, profile_updated))
        return profile_updated

    def update_fmr_config_profile(self, profile_name, **kwargs):
        '''
        Method to update a config profile.

        :param profile_type: Name of the config profile type
        :type profile_type: str
        :param profile_name: Name of the config profile to delete
        :type profile_name: str
        '''
        driver = self.driver
        driver_utils = self.driver_utils
        profile_updated = False

        try:
            self.nav_config_tab('config_profiles')
            profile_element = driver.execute_script('function get_profile(){\
                                profile=undefined;\
                                $.each($("span:contains(\'FMR Profile\')").parent().parent().next().find("a span"), \
                                function(i, e){if(e.innerHTML==\'%s\') profile=e});\
                                    return profile;\
                              }\
                              return get_profile();'%(profile_name))
            
            log.info('Clicking on the config profile.')
            if profile_element: profile_element.click()
            else: raise Exception('Given profile not found.')

            dmrIpv6Pfx = kwargs.get('dmrIpv6Pfx', None)
            dmrIpv6PfxLen = kwargs.get('dmrIpv6PfxLen', None)
            bmrIpv4Pfx = kwargs.get('bmrIpv4Pfx', None)

            dmr_Ipv6Pfx = driver.find_element_by_id('dmrIpv6Pfx')
            dmr_Ipv6PfxLen = driver.find_element_by_id('dmrIpv6PfxLen')
            bmr_Ipv4Pfx = driver.find_element_by_id('bmrIpv4Pfx')

        except Exception as e:
            driver_utils.save_screenshot()
            log.error(e)

        log.info('Profile updated under %s : %s'%(profile_name, profile_updated))
        return profile_updated

    def delete_fmr_profile_rule(self, profile_name, **kwargs):
        '''
        Method to delete a FMR config profile rule in FND portal.

        :param profile_name: Name of the config profile to delete rules.
        :type profile_name: str
        '''
        driver = self.driver
        driver_utils = self.driver_utils
        profile_rule_deleted = False

        rule_ips = kwargs.get('rule_ips', None)
        if rule_ips==None:
            log.error('Provide rules to delete.')
            return profile_rule_deleted

        try:
            self.nav_config_tab('config_profiles')
            profile_element = driver.execute_script('function get_profile(){\
                                profile=undefined;\
                                $.each($("span:contains(\'FMR Profile\')").parent().parent().next().find("a span"), function(i, e){if(e.innerHTML==\'%s\') profile=e});\
                                return profile;\
                              }\
                              return get_profile();'%(profile_name))
            if not profile_element: 
                log.error('Please provide a valid profile name.')
                return profile_rule_deleted
            if rule_ips[0]=='All':
                log.info('Selecting all FMR Mapping Rules.')
                driver.execute_script('return $(".x-grid3-hd-checker:visible")[0]').click()
                time.sleep(1)
            else:
                log.info('Selecting rule_ips: %s.'%rule_ips)
                for ip in rule_ips:
                    checkbox = driver.execute_script('return $(".x-grid3-td-fmrIpv4Prefix:contains(\'%s\'):visible").prev()[0]'%ip)
                    checkbox.click()
                    time.sleep(1)

            log.info('Clicking on Delete button.')
            driver.find_element_by_id('removeFMRRule').click()
            time.sleep(1)
            log.info('Clicking on Save button.')
            driver.find_element_by_id('saveFmrDetails').click()
            time.sleep(1)

            del_error = driver.execute_script('return $(\'span:contains("Error")\').length>0 ? $(".ext-mb-text").text() : ""')
            if del_error:
                log.info('del_error: %s'%del_error)
                driver_utils.save_screenshot()
            else: profile_rule_deleted = True
            log.info('Clicking on OK button.')
            driver.execute_script('return $("button:contains(\'OK\'):visible")[0]').click()
            time.sleep(1)

        except Exception as e:
            log.error('Unable to delete FMR config profile rule.')
            driver_utils.save_screenshot()
            log.error(e)
            driver.refresh()
            time.sleep(3)

        return profile_rule_deleted
    
    def delete_dscp_profile_rule(self, profile_name, **kwargs):
        '''
        Method to delete a DCSP config profile rule in FND portal.

        :param profile_name: Name of the config profile to delete rules.
        :type profile_name: str
        '''
        driver = self.driver
        driver_utils = self.driver_utils
        profile_rule_deleted = False

        rule_ips = kwargs.get('rule_ips', None)
        if rule_ips==None:
            log.error('Provide rules to delete.')
            return profile_rule_deleted

        try:
            self.nav_config_tab('config_profiles')
            profile_element = driver.execute_script('function get_profile(){\
                                profile=undefined;\
                                $.each($("span:contains(\'DSCP Profile\')").parent().parent().next().find("a span"), function(i, e){if(e.innerHTML==\'%s\') profile=e});\
                                return profile;\
                              }\
                              return get_profile();'%(profile_name))
            if not profile_element: 
                log.error('Please provide a valid profile name.')
                return profile_rule_deleted

            log.info('Clicking on profile: %s' % profile_name)
            profile_element.click()
            time.sleep(2)

            if rule_ips[0]=='All':
                log.info('Clicking on "All" checkbox.')
                checkbox = driver.execute_script('return $(".x-grid3-hd-checker:visible .x-grid3-hd-checker")[0]')
                time.sleep(1)
                checkbox.click()
                time.sleep(1)
            else:
                for ip in rule_ips:
                    log.info('Selecting %s'%ip)
                    checkbox = driver.execute_script('return $(".x-grid3-td-sourceIpAddr:contains(\'%s\'):visible")\
                                                .prev()[0].firstChild.firstChild'%ip)
                    time.sleep(1)
                    checkbox.click()
                    time.sleep(1)

            log.info('Clicking on Delete button.')
            driver.find_element_by_id('removeDSCPRule').click()
            time.sleep(1)
            log.info('Clicking on Save button.')
            driver.find_element_by_id('saveDscpDetails').click()
            time.sleep(1)

            del_error = driver.execute_script('return $(\'span:contains("Error")\').length>0 ? $(".ext-mb-text").text() : ""')
            if del_error:
                log.info('del_error: %s'%del_error)
                driver_utils.save_screenshot()
            else: profile_rule_deleted = True
            log.info('Clicking on OK button.')
            driver.execute_script('return $("button:contains(\'OK\'):visible")[0]').click()
            time.sleep(1)

        except Exception as e:
            log.error('Unable to delete DSCP config profile rule.')
            driver_utils.save_screenshot()
            log.error(e)
            driver.refresh()
            time.sleep(3)

        return profile_rule_deleted

    def delete_nat44_mappings(self, profile_name, **kwargs):
        '''
        Method to delete a FMR config profile rule in FND portal.

        :param profile_name: Name of the config profile to delete rules.
        :type profile_name: str
        '''
        driver = self.driver
        driver_utils = self.driver_utils
        mapping_ip_deleted = False
        mapping_ips = kwargs.get('mapping_ips', None)
        log.info(banner('Deleting NAT44 Mapping entries with: %s'%mapping_ips))

        if mapping_ips==None:
            log.error('Provide ip\'s to delete.')
            return mapping_ip_deleted

        try:
            self.nav_config_tab('config_profiles')
            profile_element = driver.execute_script('function get_profile(){\
                                profile=undefined;\
                                $.each($("span:contains(\'NAT44 Profile\')").parent().parent().next().find("a span"), function(i, e){if(e.innerHTML==\'%s\') profile=e});\
                                return profile;\
                              }\
                              return get_profile();'%(profile_name))
            if not profile_element: 
                log.error('Please provide a valid profile name.')
                return mapping_ip_deleted
            profile_element.click()
            time.sleep(2)
            
            if mapping_ips[0]=='All':
                log.info('Selecting all NAT44 Mapping.')
                driver.execute_script('return $(".x-grid3-hd-checker:visible")[0]').click()
                time.sleep(1)
            else:
                log.info('Selecting rule_ips: %s.'%mapping_ips)
                for ip in mapping_ips:
                    checkbox = driver.execute_script('return \
                        $(".x-grid3-col-internalAddr:contains(\'%s\'):visible").parent().prev()[0]'%ip)
                    checkbox.click()
                    time.sleep(1)

            log.info('Clicking on Delete button.')
            driver.execute_script('return $(".fa-trash:visible")[0]').click()
            time.sleep(1)
            log.info('Clicking on Save button.')
            driver.execute_script('return $(".fa-floppy-o:visible")[0]').click()
            time.sleep(1)

            del_error = driver.execute_script('return $(\'span:contains("Error")\').length>0 ? $(".ext-mb-text").text() : ""')
            if del_error:
                log.info('del_error: %s'%del_error)
                driver_utils.save_screenshot()
            else: mapping_ip_deleted = True
            log.info('Clicking on OK button.')
            driver.execute_script('return $("button:contains(\'OK\'):visible")[0]').click()
            time.sleep(1)

        except Exception as e:
            log.error('Unable to delete NAT44 Mapping IP.')
            driver_utils.save_screenshot()
            log.error(e)
            driver.refresh()
            time.sleep(3)

        log.info('NAT44 Mapping entries deleted: %s'%mapping_ip_deleted)
        return mapping_ip_deleted

    def delete_dhcp_client_profile_rule(self, profile_name, **kwargs):
        '''
        Method to delete a DHCP client profile rule in FND portal.

        :param profile_name: Name of the config profile to delete rules.
        :type profile_name: str
        '''
        driver = self.driver
        driver_utils = self.driver_utils
        client_profile_rules_delted = False
        client_ids = kwargs.get('client_ids', None)
        log.info(banner('Deleting DHCP Client profiles with: %s'%client_ids))

        if client_ids==None:
            log.error('Provide client ids to delete.')
            return client_profile_rules_delted

        try:
            self.nav_config_tab('config_profiles')
            profile_element = driver.execute_script('function get_profile(){\
                                profile=undefined;\
                                $.each($("span:contains(\'DHCP Client Profile\')").parent().parent().next().find("a span"), function(i, e){if(e.innerHTML==\'%s\') profile=e});\
                                return profile;\
                              }\
                              return get_profile();'%(profile_name))
            if not profile_element: 
                log.error('Please provide a valid profile name.')
                return client_profile_rules_delted

            log.info('Clicking on profile: %s' % profile_name)
            profile_element.click()
            time.sleep(2)

            if client_ids[0]=='All':
                log.info('Clicking on "All" checkbox.')
                checkbox = driver.execute_script('return $(".x-grid3-hd-checker:visible .x-grid3-hd-checker")[0]')
                time.sleep(1)
                checkbox.click()
                time.sleep(1)
            else:
                for client_id in client_ids:
                    log.info('Selecting %s'%client_id)
                    checkbox = driver.execute_script('return $(".x-grid3-td-clientId:contains(\'%s\'):visible")\
                                                .prev()[0].firstChild.firstChild'%client_id)
                    time.sleep(1)
                    checkbox.click()
                    time.sleep(1)

            log.info('Clicking on Delete button.')
            driver.find_element_by_id('removeDhcpClient').click()
            time.sleep(1)
            log.info('Clicking on Save button.')
            driver.find_element_by_id('saveDhcpClientDetails').click()
            time.sleep(1)

            del_error = driver.execute_script('return $(\'span:contains("Error")\').length>0 ? $(".ext-mb-text").text() : ""')
            if del_error:
                log.info('del_error: %s'%del_error)
                driver_utils.save_screenshot()
            else: client_profile_rules_delted = True
            log.info('Clicking on OK button.')
            driver.execute_script('return $("button:contains(\'OK\'):visible")[0]').click()
            time.sleep(1)

        except Exception as e:
            log.error('Unable to delete DHCP Client profiles.')
            driver_utils.save_screenshot()
            log.error(e)
            driver.refresh()
            time.sleep(3)

        log.info('DHCP client profile rules deleted: %s'%client_profile_rules_delted)
        return client_profile_rules_delted

    def change_config_group(self, curr_group, new_group, router_eids):
        '''
        Method to move device from one configuration group to other.

        :param curr_group: Current router group where the device is present.
        :type curr_group: str
        :param new_group: New router group where the device needs to be moved.
        :type new_group: str
        :param router_eids: Router eids of the test devices that needs to be changed.
        :type router_eids: list
        '''

        log.info('Changing the device configuration group from %s to %s.' % (curr_group, new_group))
        driver = self.driver

        log.info('Navigate to %s' % curr_group)
        driver.refresh()
        time.sleep(3)
        driver.find_element_by_xpath('//span[contains(text(),"%s")]'%curr_group).click()
        time.sleep(3)

        log.info('Click test device checkbox')
        try:
            for router_eid in router_eids:
                #Getting anchor element with router_eid under the element with id:"netElementGrid".
                router_elem = driver.find_element_by_id('netElementGrid').find_element_by_xpath('//a[contains(text(),"%s")]'%router_eid)
                #Getting the first td element of this tr row.
                check_box_td = router_elem.find_element_by_xpath('../../..').find_elements_by_tag_name('td')[0]
                #Click the checkbox of the router_eid.
                check_box_td.find_element_by_xpath('div/div').click()
        except (NoSuchElementException, ElementNotVisibleException) as e:
            log.error('Unable to find the element: %s' % e)

        log.info('Click on "Change Configuration Group" button.')
        driver.find_element_by_xpath('//button[contains(text(),"Change Configuration Group")]').click()
        time.sleep(2)

        log.info('Select %s from drop down and move to it.' % new_group)
        driver.find_element_by_xpath('//label[contains(text(),"Config Group:")]//following-sibling::div').find_element_by_tag_name('img').click()
        time.sleep(3)
        driver.find_element_by_xpath('//div[contains(text(),"%s")]'%new_group).click()
        time.sleep(3)
        driver.find_element_by_id('CBCommandsButton').click()
        time.sleep(3)
        driver.find_element_by_xpath('//button[contains(text(), "OK")]').click()
        time.sleep(3)
        log.info('Change config group done.')

    def edit_config_template(self, group_name, edit_position, edit_text):
        '''
        Method to edit configuration template of a given group.

        :param group_name: Current router group where template has to be edited.
        :type group_name: str
        :param edit_position: Postion string where template has to be edited.
        :type edit_position: str
        :param edit_text: Config commands that needs to be updated.
        :type edit_text: str
        '''
        driver = self.driver

        log.info('Navigate to configuration template.')
        self.nav_router_group(group_name)
        self.nav_tab('edit_config_template')

        log.info('Get current template.')
        current_template = driver.find_element_by_id('configTemplaterouter').get_attribute('value')
        idx = current_template.index(edit_position)

        log.info('Update current configuration template.')
        new_template = current_template[:idx] + edit_text + current_template[idx:]
        driver.find_element_by_id('configTemplaterouter').clear()
        driver.find_element_by_id('configTemplaterouter').send_keys(new_template)
        time.sleep(5)

        log.info('Saving the changes.')
        driver.find_element_by_xpath('//i[@class="fa fa-floppy-o"]').click()
        time.sleep(3)
        driver.find_element_by_xpath('//button[contains(text(), "OK")]').click()
        time.sleep(3)

    def edit_ep_config_template(self, **kwargs):
        '''
        Method to edit configuration template of a given group.

        :param group_name: Current router group where template has to be edited.
        :type group_name: str
        :param edit_position: Postion string where template has to be edited.
        :type edit_position: str
        :param edit_text: Config commands that needs to be updated.
        :type edit_text: str
        '''
        driver = self.driver
        driver_utils = self.driver_utils
        ep_config_template_edited = False

        group_name = kwargs.get('group_name', None)
        report_interval = kwargs.get('report_interval', None)
        bbu_settings = kwargs.get('bbu_settings', None)
        chk_enable_ethernet = kwargs.get('chk_enable_ethernet', None)
        eth_dscpmarking = kwargs.get('eth_dscpmarking', None)
        active_modulations = kwargs.get('active_modulations', None)

        if not group_name: raise Exception('Group name has to be provided.')
        nav_group_succ = self.nav_router_group(group_name)
        if not nav_group_succ: raise Exception()
        nav_tab_success = self.nav_tab('edit_config_template')
        if not nav_tab_success: raise Exception()

        try:
            layout_cells = []
            if report_interval:
                log.info('Changing Report Interval.')
                report_interval_val = driver.execute_script('return $("#configTemplateendpoint").val()')
                log.info('Current Report Interval: %s'%report_interval_val)
                report_interval_input = driver.execute_script('return $("#configTemplateendpoint")[0]')
                report_interval_input.clear()
                time.sleep(1)
                log.info('Entering new report interval: %d'%report_interval)
                report_interval_input.send_keys(report_interval)

            if bbu_settings:
                log.info('Changing BBU Settings.')
                bbu_settings_input = driver.execute_script('return $("#bbuSettings")[0]')

            if chk_enable_ethernet:
                log.info('Changing BBU Settings.')
                chk_enable_ethernet_input = driver.execute_script('return $("#chkEnableEthernet")[0]')

            if eth_dscpmarking:
                log.info('Changing BBU Settings.')
                eth_dscpmarking_input = driver.execute_script('return $("#ethdscpmarking")[0]')
            
            if active_modulations:
                layout_cells = driver.find_elements_by_class_name('x-table-layout-cell')
                active_columns = layout_cells[0].find_elements_by_xpath('.//dl')
                available_columns = layout_cells[2].find_elements_by_xpath('.//dl')
                active_columns = [str(e.text) for e in active_columns]
                available_columns = [str(e.text) for e in available_columns]
                log.info('active_columns: %s'%active_columns)
                log.info('available_columns: %s'%available_columns)

                for modulation in active_columns:
                    log.info('Moving %s from "active" to "available" section'%modulation)
                    modulation_column = driver.find_element_by_xpath('//em[text()="%s"]'%modulation)
                    available_column_click = ActionChains(driver).click(modulation_column)
                    log.info('Selecting %s'%modulation)
                    available_column_click.perform()
                    right_arrow = driver.execute_script('return $.find(\'img[src$="/ext/ux/images/right2.gif"]\')[0]')
                    log.info('Clicking on the right arrow.')
                    right_arrow.click()
                    time.sleep(1)

                time.sleep(2)
                active_columns = layout_cells[0].find_elements_by_xpath('.//dl')
                available_columns = layout_cells[2].find_elements_by_xpath('.//dl')
                active_columns = [str(e.text) for e in active_columns]
                available_columns = [str(e.text) for e in available_columns]
                log.info('active_columns: %s'%active_columns)
                log.info('available_columns: %s'%available_columns)
                time.sleep(2)

                for modulation in active_modulations:
                    log.info('\nMoving %s from "available" to "active" section'%modulation)
                    modulation_column = driver.find_element_by_xpath('//em[text()="%s"]'%modulation)
                    modulation_column_click = ActionChains(driver).click(modulation_column)
                    log.info('Selecting %s'%modulation)
                    modulation_column_click.perform()
                    left_arrow = driver.execute_script('return $.find(\'img[src$="/ext/ux/images/left2.gif"]\')[0]')
                    log.info('Clicking on the left arrow.')
                    left_arrow.click()
                    time.sleep(1)

            log.info('Clicking on the Save button.')
            save_button = driver.execute_script('return $(".fa-floppy-o:visible")[0]')
            save_button.click()
            time.sleep(1)

            popup_header = driver.execute_script('return $(".x-window-dlg .x-window-header-text:visible").text()')
            update_response = driver.execute_script('return $(".ext-mb-text:visible").text()')
            log.info('\n\npopup_header: %s,\nupdate_response: %s\n\n'%(popup_header, update_response))

            ok_button = driver.execute_script('return $("button:contains(\'OK\')")[0]')
            ok_button.click()
            time.sleep(1)

            if len(layout_cells)>=2:
                time.sleep(2)
                log.info(banner('New Phy mode settings after changes.'))
                active_columns = layout_cells[0].find_elements_by_xpath('.//dl')
                available_columns = layout_cells[2].find_elements_by_xpath('.//dl')
                active_columns = [str(e.text) for e in active_columns]
                available_columns = [str(e.text) for e in available_columns]
                log.info('active_columns: %s'%active_columns)
                log.info('available_columns: %s'%available_columns)
                time.sleep(2)

            if 'Success' not in popup_header:
                raise Exception('Unable to Save config.')
            ep_config_template_edited = True
        except Exception as e:
            log.error(e)
            driver_utils.save_screenshot()

        log.info('Endpoint Conf Template for group: %s is edited: %s'%(group_name, ep_config_template_edited))
        return ep_config_template_edited

    def edit_ep_config_template_phy_mode(self, **kwargs):
        '''
        Method to edit configuration template of a given group.

        :param group_name: Current router group where template has to be edited.
        :type group_name: str
        :param edit_position: Postion string where template has to be edited.
        :type edit_position: str
        :param edit_text: Config commands that needs to be updated.
        :type edit_text: str
        '''
        driver = self.driver
        driver_utils = self.driver_utils
        ep_config_template_edited = False

        group_name = kwargs.get('group_name', None)
        phy_mode_type = kwargs.get('phy_mode', None)
        report_interval = kwargs.get('report_interval', None)
        bbu_settings = kwargs.get('bbu_settings', None)
        chk_enable_ethernet = kwargs.get('chk_enable_ethernet', None)
        eth_dscpmarking = kwargs.get('eth_dscpmarking', None)
        active_modulations = kwargs.get('active_modulations', None)

        if not group_name: raise Exception('Group name has to be provided.')
        nav_group_succ = self.nav_router_group(group_name)
        if not nav_group_succ: raise Exception()
        nav_tab_success = self.nav_tab('edit_config_template')
        if not nav_tab_success: raise Exception()

        try:
            layout_cells = []
            if phy_mode_type:
                log.info('Choosing PHY mode type')
                if phy_mode_type == 'OFDM Option 2 Phy Modes':
                    log.info('Selecting "OFDM Option 2 Phy Modes"')
                    driver.find_element_by_xpath('//input[(@name="phyMode")and(@value="0")]').click()
                elif phy_mode_type == 'Classic, OFDM Option 1 and 3 Phy Modes':
                    log.info('Selecting "Classic, OFDM Option 1 and 3 Phy Modes"')
                    driver.find_element_by_xpath('//input[(@name="phyMode")and(@value="1")]').click()

            if report_interval:
                log.info('Changing Report Interval.')
                report_interval_val = driver.execute_script('return $("#configTemplateendpoint").val()')
                log.info('Current Report Interval: %s' % report_interval_val)
                report_interval_input = driver.execute_script('return $("#configTemplateendpoint")[0]')
                report_interval_input.clear()
                time.sleep(1)
                log.info('Entering new report interval: %d' % report_interval)
                report_interval_input.send_keys(report_interval)

            if bbu_settings:
                log.info('Changing BBU Settings.')
                bbu_settings_input = driver.execute_script('return $("#bbuSettings")[0]')

            if chk_enable_ethernet:
                log.info('Changing BBU Settings.')
                chk_enable_ethernet_input = driver.execute_script('return $("#chkEnableEthernet")[0]')

            if eth_dscpmarking:
                log.info('Changing BBU Settings.')
                eth_dscpmarking_input = driver.execute_script('return $("#ethdscpmarking")[0]')

            if active_modulations and phy_mode_type == 'OFDM Option 2 Phy Modes':
                layout_cells = driver.find_elements_by_class_name('x-table-layout-cell')
                log.info("layout_cells:%s" %(len(layout_cells)))
                active_columns = layout_cells[0].find_elements_by_xpath('.//dl')
                available_columns = layout_cells[2].find_elements_by_xpath('.//dl')
                active_columns = [str(e.text) for e in active_columns]
                available_columns = [str(e.text) for e in available_columns]
                log.info('active_columns: %s' % active_columns)
                log.info('available_columns: %s' % available_columns)

                for modulation in active_columns:
                    log.info('Moving %s from "active" to "available" section' % modulation)
                    modulation_column = driver.find_element_by_xpath('//em[text()="%s"]' % modulation)
                    available_column_click = ActionChains(driver).click(modulation_column)
                    log.info('Selecting %s' % modulation)
                    if 'FSK-150kbps-ON' in modulation:
                        driver.find_element_by_xpath('//div[@id="itemselector"]//em[text()="2FSK-150kbps-ON"]').click()
                    elif 'FSK-150kbps-OFF' in modulation:
                        driver.find_element_by_xpath('//div[@id="itemselector"]//em[text()="2FSK-150kbps-OFF"]').click()
                    else:
                        available_column_click.perform()
                    right_arrow = driver.execute_script('return $.find(\'img[src$="/ext/ux/images/right2.gif"]\')[0]')
                    log.info('Clicking on the right arrow.')
                    right_arrow.click()
                    time.sleep(1)

                time.sleep(2)
                active_columns = layout_cells[0].find_elements_by_xpath('.//dl')
                available_columns = layout_cells[2].find_elements_by_xpath('.//dl')
                active_columns = [str(e.text) for e in active_columns]
                available_columns = [str(e.text) for e in available_columns]
                log.info('active_columns: %s' % active_columns)
                log.info('available_columns: %s' % available_columns)
                time.sleep(2)

                for modulation in active_modulations:
                    log.info('\nMoving %s from "available" to "active" section' % modulation)
                    modulation_column = driver.find_element_by_xpath('//em[text()="%s"]' % modulation)
                    modulation_column_click = ActionChains(driver).click(modulation_column)
                    log.info('Selecting %s' % modulation)
                    if 'FSK-150kbps-ON' in modulation:
                        driver.find_element_by_xpath('//div[@id="itemselector"]//em[text()="2FSK-150kbps-ON"]').click()
                    elif 'FSK-150kbps-OFF' in modulation:
                        driver.find_element_by_xpath('//div[@id="itemselector"]//em[text()="2FSK-150kbps-OFF"]').click()
                    else:
                        modulation_column_click.perform()
                    left_arrow = driver.execute_script('return $.find(\'img[src$="/ext/ux/images/left2.gif"]\')[0]')
                    log.info('Clicking on the left arrow.')
                    left_arrow.click()
                    time.sleep(1)

            if active_modulations and phy_mode_type == 'Classic, OFDM Option 1 and 3 Phy Modes':
                layout_cells = driver.find_elements_by_class_name('x-table-layout-cell')
                log.info("layout_cells:%s" %(len(layout_cells)))
                active_columns = layout_cells[3].find_elements_by_xpath('.//dl')
                available_columns = layout_cells[5].find_elements_by_xpath('.//dl')
                active_columns = [str(e.text) for e in active_columns]
                available_columns = [str(e.text) for e in available_columns]
                log.info('active_columns: %s' % active_columns)
                log.info('available_columns: %s' % available_columns)

                for modulation in active_columns:
                    log.info('Moving %s from "active" to "available" section' % modulation)
                    modulation_column = driver.find_element_by_xpath('//em[text()="%s"]' % modulation)
                    available_column_click = ActionChains(driver).click(modulation_column)
                    log.info('Selecting %s' % modulation)
                    if 'FSK-150kbps-ON' in modulation:
                        driver.find_element_by_xpath('//div[@id="classicitemselector"]//em[text()="2FSK-150kbps-ON"]').click()
                    elif 'FSK-150kbps-OFF' in modulation:
                        driver.find_element_by_xpath('//div[@id="classicitemselector"]//em[text()="2FSK-150kbps-OFF"]').click()
                    else:
                        available_column_click.perform()
                    right_arrow = driver.execute_script('return $.find(\'img[src$="/ext/ux/images/right2.gif"]\')[1]')
                    log.info('Clicking on the right arrow.')
                    right_arrow.click()
                    time.sleep(1)

                time.sleep(2)
                active_columns = layout_cells[3].find_elements_by_xpath('.//dl')
                available_columns = layout_cells[5].find_elements_by_xpath('.//dl')
                active_columns = [str(e.text) for e in active_columns]
                available_columns = [str(e.text) for e in available_columns]
                log.info('active_columns: %s' % active_columns)
                log.info('available_columns: %s' % available_columns)
                time.sleep(2)

                for modulation in active_modulations:
                    log.info('\nMoving %s from "available" to "active" section' % modulation)
                    modulation_column = driver.find_element_by_xpath('//em[text()="%s"]' % modulation)
                    curr_elem = driver.find_element_by_xpath('//em[text()="%s"]/../..' % modulation)
                    class_selection = curr_elem.get_attribute('class')
                    log.info("class_selection: %s"%class_selection)
                    modulation_column_click = ActionChains(driver).click(modulation_column)
                    log.info('Selecting %s' % modulation)
                    if 'FSK-150kbps-ON' in modulation:
                        driver.find_element_by_xpath('//div[@id="classicitemselector"]//em[text()="2FSK-150kbps-ON"]').click()
                    elif 'FSK-150kbps-OFF' in modulation:
                        driver.find_element_by_xpath('//div[@id="classicitemselector"]//em[text()="2FSK-150kbps-OFF"]').click()
                    else:
                        modulation_column_click.perform()
                    left_arrow = driver.execute_script('return $.find(\'img[src$="/ext/ux/images/left2.gif"]\')[1]')
                    log.info('Clicking on the left arrow.')
                    left_arrow.click()
                    time.sleep(1)

            log.info('Clicking on the Save button.')
            save_button = driver.execute_script('return $(".fa-floppy-o:visible")[0]')
            save_button.click()
            time.sleep(1)

            popup_header = driver.execute_script('return $(".x-window-dlg .x-window-header-text:visible").text()')
            update_response = driver.execute_script('return $(".ext-mb-text:visible").text()')
            log.info('\n\npopup_header: %s,\nupdate_response: %s\n\n' % (popup_header, update_response))

            ok_button = driver.execute_script('return $("button:contains(\'OK\')")[0]')
            ok_button.click()
            time.sleep(1)

            if len(layout_cells) >= 2 and phy_mode_type == 'OFDM Option 2 Phy Modes':
                time.sleep(2)
                log.info(banner('New Phy mode settings after changes.'))
                active_columns = layout_cells[0].find_elements_by_xpath('.//dl')
                available_columns = layout_cells[2].find_elements_by_xpath('.//dl')
                active_columns = [str(e.text) for e in active_columns]
                available_columns = [str(e.text) for e in available_columns]
                log.info('active_columns: %s' % active_columns)
                log.info('available_columns: %s' % available_columns)
                time.sleep(2)

            if len(layout_cells) >= 2 and phy_mode_type == 'Classic, OFDM Option 1 and 3 Phy Modes':
                time.sleep(2)
                log.info(banner('New Phy mode settings after changes.'))
                active_columns = layout_cells[3].find_elements_by_xpath('.//dl')
                available_columns = layout_cells[5].find_elements_by_xpath('.//dl')
                active_columns = [str(e.text) for e in active_columns]
                available_columns = [str(e.text) for e in available_columns]
                log.info('active_columns: %s' % active_columns)
                log.info('available_columns: %s' % available_columns)
                time.sleep(2)

            if 'Success' not in popup_header:
                raise Exception('Unable to Save config.')
            ep_config_template_edited = True
        except Exception as e:
            log.error(e)
            driver_utils.save_screenshot()

        log.info('Endpoint Conf Template for group: %s is edited: %s' % (group_name, ep_config_template_edited))
        return ep_config_template_edited

    def replace_gw_config_template_with_text(self, group_name, edit_text):
        '''
        Method to edit configuration template of a given group.

        :param group_name: Current router group where template has to be edited.
        :type group_name: str
        :param edit_position: Postion string where template has to be edited.
        :type edit_position: str
        :param edit_text: Config commands that needs to be updated.
        :type edit_text: str
        '''
        driver = self.driver

        log.info('Navigate to configuration template.')
        self.nav_router_group(group_name)
        self.nav_tab('edit_config_template')

        log.info('Get current template.')
        current_template = driver.find_element_by_id('configTemplateiotgateway').get_attribute('value')
        # idx = current_template.index(edit_position)

        log.info('Update current configuration template.')
        new_template = edit_text
        driver.find_element_by_id('configTemplateiotgateway').clear()
        time.sleep(3)
        driver.find_element_by_id('configTemplateiotgateway').send_keys(new_template)
        time.sleep(5)

        log.info('Saving the changes.')

        save_changes = driver.find_elements_by_xpath('//i[@class="fa fa-floppy-o"]')
        save_change = [save_change for save_change in save_changes if save_change.is_displayed()][0]
        save_change.click()
        time.sleep(3)

        driver.find_element_by_xpath('//button[contains(text(), "OK")]').click()
        time.sleep(3)

    def replace_config_template_with_text(self, group_name, replace_text):
        '''
        Method to edit configuration template with the given text.

        :param group_name: Current router group where template has to be edited.
        :type group_name: str
        :param replace_text: Text that needs to be replaced.
        :type replace_text: str
        '''
        driver = self.driver
        driver_utils = self.driver_utils
        template_updated = False

        try:
            log.info('Navigate to configuration template.')
            self.nav_router_group(group_name)
            self.nav_tab('edit_config_template')

            log.info('Clearing the exisitng template.')
            driver.find_element_by_id('configTemplaterouter').clear()
            driver.find_element_by_id('configTemplaterouter').send_keys(replace_text)
            time.sleep(3)

            log.info('Saving the changes.')
            driver.find_element_by_xpath('//i[@class="fa fa-floppy-o"]').click()
            time.sleep(3)

            popup_headers = driver.find_elements_by_xpath('//span[contains(@class, "x-window-header-text")]')
            for popup_header in popup_headers:
                if popup_header.is_displayed() == True:
                    if 'Failure' not in popup_header.text: template_updated = True
                    break

            driver.find_element_by_xpath('//button[contains(text(), "OK")]').click()
            time.sleep(3)
        except Exception as e:
            driver_utils.save_screenshot()
            log.error(e)

        return template_updated

    def replace_config_template_with_file(self, group_name, replace_file_location):
        '''
        Method to edit configuration template at a given location.

        :param group_name: Current router group where template has to be edited.
        :type group_name: str
        :param replace_file_location: String position where template has to be edited.
        :type replace_file_location: int
        '''
        pass

    def push_configuration(self, group_name, config_name):
        '''
        '''

        driver = self.driver
        driver_utils = self.driver_utils
        config_pushed = False

        try:
            log.info(banner('Pushing Configuration under group: %s with config_name: %s'%(group_name, config_name)))
            nav_router_group_succ = self.nav_router_group(group_name)
            if not nav_router_group_succ:
                raise Exception('Unable to navigate to given group.')
            self.nav_tab('push_config')

            log.info('Clicking on "Select Operation" dropdown.')
            config_combo = driver.find_element_by_xpath('//input[@id="configCombo"]')
            config_combo_dropdown = config_combo.find_element_by_xpath('following-sibling::img')
            config_combo_dropdown.click()
            time.sleep(1)

            push_config_dict = {
                'router_config': 'Push ROUTER Configuration',
                'sd_card_password': 'Push SD Card Password',
                'endpoint_config': 'Push ENDPOINT Configuration',
                'gateway_config': 'Push GATEWAY Configuration'
            }
            push_config_name = push_config_dict[config_name]

            log.info('Selecting %s'%push_config_name)
            operation = driver.execute_script(
                        'return $(".x-combo-list-item").filter(function(){return $(this).text()=="%s"})[0]'\
                        %push_config_name)
            if operation: operation.click()
            else:
                raise Exception('Selected Operation is not present.')
                return config_pushed
            time.sleep(1)

            log.info('Click on Start button.')
            start_button = driver.execute_script('return $("button:contains(\'Start\'):visible")[0]')
            start_button.click()

            log.info('Click on Yes button.')
            driver.execute_script('return $("button:contains(\'Yes\'):visible")[0]').click()
            time.sleep(1)

            log.info('Click on OK button.')
            driver.execute_script('return $("button:contains(\'OK\'):visible")[0]').click()
            time.sleep(1)

            log.info('Navigating back to "Push Configuration".')
            self.nav_tab('push_config')
            device_status_tds = driver.find_elements_by_xpath('//div[@id="tblPushConfigVer"]/.//table[@class="properties"]//td')
            log.info('%s'%' '.join([td.text for td in device_status_tds]))

            resp_elems = driver.find_elements_by_xpath('//div[@id="deviceStatusGrid"]/.//div[contains(@class, "x-grid3-cell-inner")]')
            resp_elems = [e.text for e in resp_elems]
            log.info('\n\nresp_elems: %s\n\n'%resp_elems)

            config_pushed = True
        except Exception as e:
            log.error(e)
            driver_utils.save_screenshot()

        log.info('\npush_configuration for %s with %s is : %s'%(group_name, config_name, config_pushed))
        return config_pushed

    def get_adaptive_phy_mode_settings(self, **kwargs):
        '''
        '''
        driver = self.driver
        driver_utils = self.driver_utils
        adaptive_phy_mode_settings = {}

        try:
            group = kwargs.get('group', None)
            tab_name = kwargs.get('tab_name', None)
            if not group or not tab_name: raise Exception('Provide valid parameters.')

            nav_group_succ = self.nav_router_group('default-ir500')
            if not nav_group_succ: raise Exception()
            nav_tab_success = self.nav_tab('edit_config_template')
            if not nav_tab_success: raise Exception()

            layout_cells = driver.find_elements_by_class_name('x-table-layout-cell')
            active_columns = layout_cells[0].find_elements_by_xpath('.//dl')
            active_columns = [str(dl.text) for dl in active_columns]
            available_columns = layout_cells[2].find_elements_by_xpath('.//dl')
            available_columns = [str(dl.text) for dl in available_columns]

            adaptive_phy_mode_settings['active_columns'] = active_columns
            adaptive_phy_mode_settings['available_columns'] = available_columns
        except Exception as e:
            log.error(e)
            driver_utils.save_screenshot()

        log.info('%s'%(json.dumps(adaptive_phy_mode_settings, indent=4, sort_keys=True)))
        return adaptive_phy_mode_settings

class FirmwareUpdate(ConfigNavigation):
    ''' This class defines all the applicable opertaions under "Firmware Update" page. '''

    def __init__(self, driver, *arg):
        self.arg = arg
        self.driver = driver
        self.driver_utils = DriverUtils(driver)

    def nav_router_group(self, group_name):
        '''
        Method to navigate to Router group.

        :param group_name: Name of the group to navigate.
        :type group_name: str
        '''
        log.info('Navigate to %s' % group_name)
        driver = self.driver
        driver_utils = self.driver_utils
        nav_group_succ = False

        try:
            selected=''
            timeout = time.time() + 60*2
            while timeout>time.time():
                time.sleep(1)
                firmware_group = driver.execute_script('\
                                    return $("span")\
                                    .filter(\
                                        function(){return $(this).text().split(" ")[0].toLowerCase()==="%s".toLowerCase();}\
                                    )[0]'%group_name)
                log.info('Clicking on Firmware Group: %s'%group_name)
                firmware_group.click()
                time.sleep(1)
                driver_utils.ignore_flash_error()
                selected = firmware_group.find_element_by_xpath('../..').get_attribute('class')
                log.info('selected: %s'%selected)
                if 'x-tree-selected' in selected:
                    nav_group_succ = True
                    break

        except Exception as e:
            driver_utils.save_screenshot()
            log.error('Please provide a valid Group name.')

        return nav_group_succ

    def nav_tab(self, tab_name):
        '''
        Method to navigate to given tab.

        :param group_name: Name of the tab to navigate.
        :type group_name: str
        '''

        driver = self.driver
        nav_tab_succ = False
        #Dictionary of sub_menu id tuples as per the selection.
        tab_ids = {
            'firmware_upgrade': 'upgradeMigrateTabPanel__firmwareUpgradeTab',
            'migration_to_ios': 'upgradeMigrateTabPanel__migrationToIOSTab',
            'firmware_management': 'fwTabs__mgmtTab',
            'devices': 'fwTabs__deviceTab',
            'logs': 'fwTabs__logTab',
            'transmission_settings': 'fwTabs__endpointTransmissionTab'
        }
        #Determine tab id's depending on the requested tab_name.
        tab_id = tab_ids[tab_name]

        try:
            log.info('Clicking "%s"'% tab_id)
            driver.find_element_by_id('%s'%tab_id).click()
            time.sleep(2)

            #Wait unitl the clicked page is loaded completely.
            selected = ''
            timeout=time.time() + 60*2
            while timeout>time.time():
                log.info('Checking for sub_menu_active_id')
                selected = driver.find_element_by_id('%s'%tab_id).get_attribute('class')
                log.info('selected: %s' % selected)
                if 'x-tab-strip-active' in selected:
                    nav_tab_succ = True
                    break

                driver.find_element_by_id('%s'%tab_id).click()
                log.info('Waiting for tab to be active.')
                time.sleep(1)
        except (NoSuchElementException, ElementNotVisibleException) as e:
            log.error('Element not found: %s' % e)
        except Exception as e: log.error(e)

        return nav_tab_succ

    def find_group(self, group_type, group_name):
        '''
        Method to find a router group in FND portal.

        :param group_name: Name of the router group
        :type group_name: str
        '''
        driver = self.driver
        group_found = False

        try:
            anchor_span_elems = driver.find_elements_by_xpath('//a[@class="x-tree-node-anchor"]//span')
            firmware_groups = [span_elem.text.split(' (')[0].capitalize() for span_elem in anchor_span_elems]
            log.info('Current Firmware Groups: %s' % firmware_groups)

            if group_name.capitalize() in firmware_groups:
                group_found = True
                log.info('Given "group_name: %s" found in the exisitng groups.'%group_name)
        except StaleElementReferenceException as e: log.error('StaleElementReferenceException: %s' % e)
        except Exception as e: log.info(e)

        return group_found

    def add_group(self, group_type, group_name):
        '''
        Method to add a router group in FND portal.

        :param group_name: Name of the router group to add
        :type group_name: str
        '''
        driver = self.driver
        driver_utils = self.driver_utils

        group_added = False
        group_found = self.find_group(group_type, group_name)

        if group_found:
            log.error('There is a group already exisitng with this name. Please choose a differnt name.')
            return group_added
        else:
            if group_type == 'router': group = 'default-cgr1000'
            elif group_type == 'endpoint': group = 'default-cgmesh'
            elif group_type == 'gateway': group = 'default-lorawan'
            log.info('Clicking on %s group.'%group)
            driver.find_element_by_xpath('//span[contains(text(),"%s")]'%group).click()
            if group == 'default-cgmesh': driver_utils.ignore_flash_error()

            try:
                log.info('Adding new group: %s' % group_name)
                time.sleep(2)
                driver.find_element_by_xpath('//div[@id="firmwareGroups_toolsContainer"]//div').click()
                driver.find_element_by_xpath('//input[@id="addFormGroupName"]').send_keys(group_name)
                add_button = driver.execute_script('return $("#addGroupForm .x-btn-text:contains(\'Add\')")[0]')
                add_button.click()
                group_added = True
                time.sleep(3)
            except:
                log.error('Unable to add group.')
                return group_added

        #Waiting till new group is added.
        new_groups = []
        timeout=time.time() + 60*2
        while timeout>time.time():
            #Finding anchor tags with a class "x-tree-node-anchor". This is a list of configuration groups on the portal.
            anchor_span_elems = driver.find_elements_by_xpath('//a[@class="x-tree-node-anchor"]//span')
            new_groups = [span_elem.text.split(' (')[0].capitalize() for span_elem in anchor_span_elems]
            log.info('New device groups: %s' % new_groups)
            if group_name.capitalize() in new_groups: break
            time.sleep(2)

        log.info('%s under %s is added: %s'%(group_name, group_type, group_added))
        return group_added

    def rename_group(self, group_name, new_name):
        '''
        Method to rename a router group in FND portal.

        :param group_name: Name of the router group to add
        :type group_name: str
        '''
        driver = self.driver
        driver_utils = self.driver_utils
        router_group_renamed = False

        try:
            anchor_span_elems = driver.find_elements_by_xpath('//a[@class="x-tree-node-anchor"]//span')
            firmware_groups = [span_elem.text.split(' (')[0].capitalize() for span_elem in anchor_span_elems]
            log.info('Current firmware_groups: %s'%firmware_groups)

            #Finding the edit button for the given group_name and click it.
            for current_group in anchor_span_elems:
                if current_group.text.split(' (')[0].capitalize() == group_name.capitalize():
                    rename_button = current_group.find_element_by_xpath('following-sibling::div/div[@class="x-tool x-tool-ciscoEdit"]')
                    time.sleep(1)
                    current_group.click()
                    time.sleep(2)
                    driver.execute_script('$(arguments[0]).click();', rename_button)
                    time.sleep(2)
                    break

            log.info('Entering the new name.')
            driver.find_element_by_id('groupRename').clear()
            driver.find_element_by_id('groupRename').send_keys(new_name)
            time.sleep(1)
            #Confirming the edit in popup.
            log.info('Confirming the edit.')
            driver_utils.get_visible_button_by_text('OK').click()
            time.sleep(1)
            driver_utils.get_visible_button_by_text('OK').click()
            router_group_renamed = True
        except Exception as e:
            log.error('Unable to edit firmware group.\n%s'%e)
            driver.refresh()
        
        #Waiting till new group is updated.
        tunnel_groups = []
        timeout = time.time() + 60*2
        while timeout>time.time():
            anchor_span_elems = driver.find_elements_by_xpath('//a[@class="x-tree-node-anchor"]//span')
            groups = [span_elem.text.split(' (')[0].capitalize() for span_elem in anchor_span_elems]
            log.info('New tunnel groups: %s' % groups)
            log.info('Waiting for group to show up. %s'%new_name)
            log.info(new_name in groups)
            if new_name.capitalize() in groups : break
            time.sleep(1)

        return router_group_renamed

    def delete_group(self, group_type, group_name):
        '''
        Method to delete a router group in FND portal.

        :param group_name: Name of the router group to delete
        :type group_name: str
        '''

        driver = self.driver
        driver_utils = self.driver_utils
        group_deleted = False
        group_found = self.find_group(group_type, group_name)

        if not group_found:
            log.error('There is a no group with this name. Please choose a differnt name.')
            return group_deleted
        else:
            try:
                span_element = driver.find_element_by_xpath('//span[contains(text(), "%s")]'%group_type)
                x_tree_node = span_element.find_element_by_xpath('../../..')
                current_groups = x_tree_node.find_elements_by_xpath('ul/li/div/a/span')

                # current_groups = driver.find_elements_by_xpath('//a[@class="x-tree-node-anchor"]//span')
                #Finding the delete button for the given group_name and click it.
                for current_group in current_groups:
                    if current_group.text.split(' (')[0].capitalize() == group_name.capitalize():
                        del_button = current_group.find_element_by_xpath('following-sibling::div/div[@class="x-tool x-tool-ciscoDelete"]')
                        time.sleep(2)
                        driver.execute_script('$(arguments[0]).click();', del_button)
                        time.sleep(2)
                        break

                #Confirming the delete in popup.
                log.info('Confirming the delete.')
                driver.execute_script('return $("button:contains(\'Yes\'):visible")[0]').click()
                time.sleep(2)
                ok_button = driver.execute_script('return $("button:contains(\'OK\'):visible")[0]')
                if not ok_button.is_displayed():
                    ok_button = driver.execute_script('return $("button:contains(\'OK\'):visible")[1]')
                
                ok_button.click()
                time.sleep(2)
                log.info('Given group deleted.')

                group_deleted = True
            except Exception as e:
                log.error('Unable to delete group.')
                driver_utils.save_screenshot()
                log.info(e)

        return group_deleted

    def change_firmware_group(self, curr_group, new_group, router_eids, **kwargs):
        '''
        Method to move device from one configuration group to other.

        :param curr_group: Current router group where the device is present.
        :type curr_group: str
        :param new_group: New router group where the device needs to be moved.
        :type new_group: str
        :param router_eids: Router eids of the test devices that needs to be changed.
        :type router_eids: list
        '''

        log.info(banner('Changing the firmware configuration group from %s to %s.' % (curr_group, new_group)))
        driver_utils = self.driver_utils
        driver = self.driver
        time.sleep(3)

        log.info('Navigate to %s' % curr_group)
        driver.find_element_by_xpath('//span[contains(text(),"%s")]' % curr_group).click()
        time.sleep(3)

        status = kwargs.get('status', 'up')
        type = kwargs.get('type', 'router')
        if 'endpoint' in type:
            driver_utils.ignore_flash_error()
            time.sleep(1)
            driver.find_element_by_xpath("//li[@id='fwTabs__deviceTab']//span[text()='Devices']").click()
            time.sleep(3)
            driver.find_element_by_xpath("//input[@id='deviceSearchQuery']").clear()
            if len(router_eids) > 1:
                driver.find_element_by_xpath("//input[@id='deviceSearchQuery']").send_keys("status:" + status)
            else:
                for eid in router_eids:
                    driver.find_element_by_xpath("//input[@id='deviceSearchQuery']").send_keys("name:" + eid)

            driver.find_element_by_xpath(
                "//table[@class='x-btn fa fa-search btn-filter-serach x-btn-noicon x-box-item']").click()
            time.sleep(2)

        log.info('Click checkboxes of the given router_eids: %s' % router_eids)
        try:
            for router_eid in router_eids:
                log.info('Clicking router_eid: %s' % router_eid)
                # Getting anchor element with router_eid under the element with id:"netElementGrid".
                router_elem = driver.find_element_by_id('firmwareGrid').find_element_by_xpath(
                    '//a[contains(text(),"%s")]' % router_eid)
                time.sleep(2)
                # Getting the first td element of this tr row.
                check_box_td = router_elem.find_element_by_xpath('../../..').find_elements_by_tag_name('td')[0]
                # Click the checkbox of the router_eid.
                check_box_td.find_element_by_xpath('div/div').click()
        except (NoSuchElementException, ElementNotVisibleException) as e:
            log.error('Unable to find the element: %s' % e)

        log.info('Click on "Change Firmware Group" button.')
        driver.find_element_by_xpath('//button[contains(text(),"Change Firmware Group")]').click()
        time.sleep(2)

        try:
            log.info('Select %s from drop down and move to it.' % new_group)
            driver.find_element_by_xpath(
                '//label[contains(text(),"Firmware Group:")]//following-sibling::div').find_element_by_tag_name(
                'img').click()
            time.sleep(3)
            log.info('Selecting new_group: %s from dropdown.' % new_group)
            driver.find_element_by_xpath(
                "//div[@class='x-layer x-combo-list '][contains(@style,'visibility: visible;')]//div[contains(text(),'" + new_group + "')]").click()
            time.sleep(3)
            driver.find_element_by_id('CBCommandsButton').click()
            time.sleep(3)
            driver.find_element_by_xpath('//button[contains(text(), "OK")]').click()
            time.sleep(3)
            log.info('Change firmware group done.')
        except (NoSuchElementException, ElementNotVisibleException) as e:
            log.error('Unable to find the element: %s' % e)

    def upload_image_to_fnd(self, group_name, image_file_path):
        '''
        Method to Upload Image to FND.
        '''
        driver = self.driver
        driver_utils = self.driver_utils
        image_uploaded = {
            'upload_status': False,
            'upload_message': ''
        }

        try:
            log.info('Navigating to "Images" tab.')
            driver.find_element_by_id('mainPnltree__imgsTab').click()
            time.sleep(2)

            log.info('Selecting the given group: %s'%group_name)
            group = driver.execute_script(
                'return $(".x-tree-node-el").filter(function(){return $(this).text()=="%s"})[0]'%group_name)
            if not group: raise Exception('Given groupname not available.')
            group.click()
            time.sleep(1)

            log.info('Clicking on Add image button.')
            add_img_button = driver.execute_script('return $(".x-tool-ciscoAdd:visible")[0]')
            if not add_img_button: raise Exception('Add Image button is missing.')
            add_img_button.click()
            time.sleep(2)

            log.info('Entering the file: %s to Upload.'%image_file_path)
            file_input = driver.find_element_by_xpath('//input[@id="formchfilefile"]')
            file_input.send_keys(image_file_path)
            time.sleep(1)

            invalid_icon = driver.execute_script('return $("#x-form-el-form-ch-file .x-form-invalid-icon").css("visibility")')
            log.info('invalid_icon: %s'%invalid_icon)
            assert invalid_icon!='visible'
            time.sleep(2)

            log.info('Clicking on "Add File" button.')
            driver.find_element_by_xpath('//div[@id="firmwareImageForm-image"]/.//button[contains(text(), "Add File")]').click()

            log.info(banner('Checking Upload Status'))
            timeout = time.time() + 60*15
            while timeout>time.time():
                time.sleep(5)
                add_status = 1
                try: add_status = driver.execute_script('return $("span:contains(\'Adding file to IoT-FND\'):visible").length')
                except Exception as e: log.error('Unable to get add_status')
                log.info('Uploading...')
                if not add_status: break

            upload_popup = driver.execute_script('return $(".x-window-dlg").css("visibility")')
            log.info('upload_popup: %s'%upload_popup)
            if upload_popup=='visible':
                upload_succ = driver.execute_script('return $("span:contains(\'successfully uploaded\')").length')
                if upload_succ:
                    upload_succ_mess = driver.execute_script('return $("span:contains(\'successfully\')").text()')
                    log.info('upload_succ_mess: %s'%upload_succ_mess)
                    image_uploaded['upload_status'] = True
                    image_uploaded['upload_message'] = upload_succ_mess
                    log.info('Clicking on OK button.')
                    driver.execute_script('$("button:contains(\'OK\')").click()')
                    time.sleep(1)
                else:
                    upload_fail_mess = driver.execute_script('return $(".ext-mb-text").text()')
                    log.error('upload_fail_mess: %s'%upload_fail_mess)
                    image_uploaded['upload_message'] = upload_fail_mess
                    log.info('Clicking on OK button.')
                    driver.execute_script('$("button:contains(\'OK\')").click()')
                    time.sleep(1)
                    log.info('Clicking on the Close button.')
                    driver.execute_script('$("span:contains(\'Add Firmware Image to: \')").prev().click()')
        except Exception as e:
            log.error('Unable to upload image to FND.')
            driver_utils.save_screenshot()
            driver.refresh()

        log.info('Image: %s under group: %s is\n%s'%
            (image_file_path.split('/')[-1], group_name, json.dumps(image_uploaded, indent=4, sort_keys=True)))
        return image_uploaded

    def delete_image_from_fnd(self, group_name, image_name):
        '''
        Method to Upload Image to FND.
        '''
        driver = self.driver
        driver_utils = self.driver_utils
        image_deleted = False

        try:
            if not group_name or not image_name:
                log.error('Provide a valid image name.')
                return image_deleted
            log.info(banner('Deleting image: %s under group: %s'%(image_name, group_name)))
            log.info('Navigating to "Images" tab.')
            driver.find_element_by_id('mainPnltree__imgsTab').click()
            time.sleep(2)

            log.info('Clicking on Group: %s.'%group_name)
            driver.execute_script('$("span:contains(\'%s\')").click()'%group_name)
            driver_utils.wait_for_loading()

            log.info('Clicking on "Delete" for image: %s'%image_name)

            driver.find_element_by_xpath('//a[contains(@onclick, "%s")]'%image_name).click()
            time.sleep(1)

            expected_header = 'Confirm'
            expected_message = 'Image will be deleted from IoT-FND only.'

            popup_header = driver.execute_script('return $(".x-window-header-text").text()')
            confirm_message = driver.execute_script('return $(".ext-mb-text").text()')
            log.info('popup_header: %s\nconfirm_message: %s'%(popup_header, confirm_message))
            log.info('Clicking on "Yes" buttton')
            driver.execute_script('return $("button:contains(\'Yes\'):visible")[0]').click()
            time.sleep(1)
            log.info('Clicking on "OK" buttton')
            driver.execute_script('return $("button:contains(\'OK\'):visible")[0]').click()
            time.sleep(1)

            assert expected_message in confirm_message
            image_deleted = True
        except Exception as e:
            log.error('Unable to delete image from FND.')
            driver_utils.save_screenshot()
            driver.refresh()

        log.info(banner('%s under %s is deleted: %s'%(image_name, group_name, image_deleted)))
        return image_deleted

    def upload_image(self, group_name, device_type, image_name):
        '''
        Method to Upload firmware image in given router group.

        :param group_name: Group name to upload the image
        :type group_name: str
        :param device_type: Device type
        :type device_type: str
        :param image_name: Image name that needs to be uploaded.
        :type image_name: list

        device_type Options:
           * 'cgr1000': 'IOS-CGR'
           * 'ir800': 'IOS-IR800'
           * 'c800': 'IOS-C800'
        '''
        driver = self.driver
        driver_utils = self.driver_utils
        image_upload_started = False
        log.info('Uploading the image: %s in the group: %s.' % (image_name, group_name))

        #Dictionary of sub_menu id tuples as per the selection.
        type_dict = {
            'cgr1000': 'IOS-CGR',
            'ir800': 'IOS-IR800',
            'ir1100': 'IOS-XE-IR1100',
            'c800': 'IOS-C800',
            'esr': 'IOS-ESR',
            'RF': 'RF',
            'wpan_ofdm': 'IOS-WPAN-OFDM',
            'wpan_rf': 'IOS-WPAN-RF',
            'ic3000': 'IC3000',
            'cgos': 'CGOS'
        }

        try:
            #Determine sub_menu id's depending on the requested sub_menu.
            image_type = type_dict[device_type]
            log.info("rrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrr %s"%image_type)
            self.nav_router_group(group_name)
            driver_utils.ignore_flash_error()
            firmware_management = driver.execute_script('return \
                    $("#fwTabs__mgmtTab:visible").length > 0 ? true : false')
            log.info('firmware_management: %s'%firmware_management)
            if firmware_management: self.nav_tab('firmware_management')

            log.info('Click on "Upload Image" button.')
            upload_button = driver.execute_script('return \
                    $("#uploadImageButton:visible").length>0 ?\
                    $("#uploadImageButton:visible")[0] :\
                    $("#startDownloadButtona:visible")[0]')

            if not upload_button: raise Exception('"Upload Image" not visible.')
            upload_class = upload_button.get_attribute('class')
            if 'x-item-disabled' in upload_class: raise Exception('"Upload Image" is disabled.')

            upload_button.click()
            time.sleep(2)
            log.info('Select router type: %s from drop down.' % image_type)
            driver.execute_script('return $("#comboImageType").next()[0]').click()
            time.sleep(3)
            driver.execute_script('return \
                    $(".x-combo-list-item:visible").filter(function(){return $(this).text()=="%s";})[0]'
                    %image_type).click()

            log.info('Select image: %s from drop down.' % image_name)
            if not image_name: log.info('Uploading the default Image.')
            else:
                driver.execute_script('return $("#comboFI").next()[0]').click()
                time.sleep(2)
                
                image_ele = driver.execute_script('return $(".x-combo-list-item:visible").filter(function(){return $(this).text()=="%s";})[0]'%image_name)
                if image_ele is None: raise Exception('No image available with the give name.')
                image_ele.click()
                time.sleep(2)
                driver.find_element_by_xpath("//input[@id='checkImageDiff']").click()
                time.sleep(3)

            log.info('Click on "Upload Image" button to start upload.')
            driver.execute_script('return $("#fdPanelForm button:contains(\'Upload Image\'):visible")[0]').click()
            time.sleep(2)
            driver_utils.ignore_flash_error()
            time.sleep(1)
            
            log.info('Confirming - Start uploading!')
            driver.execute_script('return $("button:contains(\'OK\'):visible")[0]').click()
            time.sleep(3)
            driver_utils.ignore_flash_error()
            time.sleep(2)
            image_upload_started = True
            timeout = time.time() + 60 * 20
            flag=False
            while timeout > time.time():
                status_text = driver.find_element_by_xpath("//div[@id='firmare-details-panel']//td[text()='Current Status:']/..//td[2]").text

                if 'Finished' in status_text:
                    log.info("Firmware upload completed!")
                    flag=True
                    break
                elif 'Image Loading' in status_text:
                    log.info("Firmware upload status -" + status_text)
                    time.sleep(30)
                    driver.find_element_by_xpath("//div[@id='leftHandTree']//span[contains(text(),'" + fw_groupname + "')]").click()
                    time.sleep(1)
                    driver_utils.ignore_flash_error()
                    time.sleep(1)
                    continue
                else:
                    continue
        except Exception as e:
            log.error(e)
            driver_utils.save_screenshot()

        log.info('Image: %s under group: %s is started: %s'%(image_name, group_name, image_upload_started))
        return image_upload_started

    def install_image(self, group_name):
        '''
        Method to Install firmware image in given router group.

        :param group_name: Group name to upload the image
        :type group_name: str
        '''
        log.info('Installing the image in the group: %s.' % (group_name))
        driver = self.driver
        driver_utils = self.driver_utils
        install_image_submitted = False

        try:
            self.nav_router_group(group_name)
            install_image_button = driver.find_element_by_id('installImageButton')
            
            if 'x-item-disabled' in install_image_button.get_attribute('class'):
                raise Exception('Install Image button is in disabled state.')

            log.info('Click on "Install Image" button.')
            install_image_button.click()
            time.sleep(1)

            log.info('Confirming - Install Image!')
            driver.find_element_by_xpath('//button[contains(text(), "Yes")]').click()
            time.sleep(1)
            install_image_submitted = True
        except Exception as e:
            log.error(e)
            driver_utils.save_screenshot()

        log.info('install_image_submitted: %s for Group: %s'%(install_image_submitted, group_name))
        return install_image_submitted

    def get_firmware_update_status(self, group_name):
        '''
        Method to find the current image upload status in given router group.

        :param group_name: Group name to upload the image
        :type group_name: str
        '''
        log.info(banner('Getting Firmware Update status of the group: %s'%group_name))

        driver = self.driver
        driver_utils = self.driver_utils
        firmware_update_status = {'upload_status': '', 'device_status':[]}

        upload_status_div = driver.execute_script('return \
                    $("#statustitlepnl:visible").length>0 ?\
                    "statustitlepnl" :\
                    "firmare-details-panel"')

        try:
            time.sleep(1)
            self.nav_router_group(group_name)
            time.sleep(1)
            upload_status = driver.execute_script('function info(){\
                        a={};\
                        $.each($("#%s").find(".key:visible"), function(i,e){\
                            a[e.textContent.trim().split(":")[0]]=e.nextElementSibling.textContent;\
                        });\
                        return a;\
                    }\
                    return info();'%upload_status_div)

            time.sleep(1)
            firmware_update_status['upload_status'] = upload_status
            
            firmware_grid_visible = driver.execute_script('return $("#firmwareGrid:visible").length>0')
            if firmware_grid_visible:
                grid_tables = driver.find_elements_by_xpath('//div[@id="firmwareGrid"]/\
                            .//div[@class="x-grid3-body"]//table[@class="x-grid3-row-table"]')
                for grid_table in grid_tables:
                    time.sleep(1)
                    grid_tds = grid_table.find_elements_by_xpath('tbody//tr//td')
                    device_status = {}
                    device_status['name'] = grid_tds[3].text
                    device_status['ip'] = grid_tds[4].text
                    device_status['firmware_ver'] = grid_tds[5].text
                    device_status['activity'] = grid_tds[6].text
                    device_status['update_progress'] = grid_tds[7].text
                    device_status['last_status_heard'] = grid_tds[8].text
                    device_status['error_mess'] = grid_tds[9].text
                    firmware_update_status['device_status'].append(device_status)
                    time.sleep(1)
        except Exception as e:
                log.error(e)
        
        log.info('firmware_update_status: %s'%json.dumps(firmware_update_status, indent=4, sort_keys=True))
        return firmware_update_status

    def get_firmware_install_status(self, group_name):
        '''
        '''
        driver = self.driver
        driver_utils = self.driver_utils
        firmware_install_status = {'install_status': '', 'device_status':[]}

        try:
            time.sleep(1)
            self.nav_router_group(group_name)
            time.sleep(1)
            install_status = driver.execute_script('function info(){\
                        a={};\
                        $.each($("#statustitlepnl").find(".key:visible"), function(i,e){\
                            a[e.textContent.trim().split(":")[0]]=e.nextElementSibling.textContent;\
                        });\
                        return a;\
                    }\
                    return info();')

            time.sleep(1)
            firmware_install_status['install_status'] = install_status

            device_status_details = driver.execute_script('function info(){\
                        a=[];\
                        $.each($("#firmwareGrid .x-grid3-row-table:visible td"), function(i,e){\
                            a.push(e.textContent)\
                        });\
                        return a;\
                    }\
                    return info();')

            for i in range(int(len(device_status_details)/12)):
                grid_tds = device_status_details[i*12:i*12+12]
                device_status = {}
                device_status['name'] = grid_tds[3]
                device_status['ip'] = grid_tds[4]
                device_status['firmware_ver'] = grid_tds[5]
                device_status['activity'] = grid_tds[6]
                device_status['update_progress'] = grid_tds[7]
                device_status['last_status_heard'] = grid_tds[8]
                device_status['error_mess'] = grid_tds[9]
                firmware_install_status['device_status'].append(device_status)
                time.sleep(1)

        except Exception as e:
            log.error(e)
            driver_utils.save_screenshot()

        log.info('firmware_install_status: %s'%json.dumps(firmware_install_status, indent=4, sort_keys=True))
        return firmware_install_status

    def sort_devices(self, group_name, sort_by, *args):

        driver = self.driver
        log.info('Sorting Devices by: %s in group: %s'%(sort_by, group_name))
        
        tab_ids = {
            'status': 'x-grid3-td-1',
            'name': 'x-grid3-td-3',
            'ip': 'x-grid3-td-4',
            'firmware_ver': 'x-grid3-td-5',
            'activity': 'x-grid3-td-6',
            'update_progress': 'x-grid3-td-7',
            'last_firmware_status_heard': 'x-grid3-td-8',
            'error_message': 'x-grid3-td-firmwareErrorMessage'
        }
        tab_id = tab_ids[sort_by]

        log.info('Click on "%s" span.'%group_name)
        self.nav_router_group(group_name)
        time.sleep(1)

        try:
            tab_ele = driver.find_element_by_xpath('//tr[contains(@class, "x-grid3-hd-row")]/td[contains(@class,"%s")]'%tab_id)
            curr_sort = tab_ele.get_attribute('class')
            log.info('curr_sort: %s'%curr_sort)

            log.info('Clicking on %s tab.'%sort_by)
            tab_ele.click()
            time.sleep(1)
        except Exception as e: log.error(e)

    def get_images_available(self, group_name):
        driver = self.driver
        driver_utils = self.driver_utils
        images = {}

        try:
            log.info('Navigating to "Images" tab.')
            driver.find_element_by_id('mainPnltree__imgsTab').click()
            time.sleep(2)

            log.info('Clicking on Group: %s.'%group_name)
            driver.execute_script('$("span:contains(\'%s\')").click()'%group_name)
            driver_utils.wait_for_loading()

            image_info = driver.execute_script('\
                function a(){\
                    a=[];\
                    $.each($(".x-grid3-row:visible").find(".x-grid3-cell:visible"),\
                        function(i,e){a.push(e.textContent)});\
                    return a;\
                }\
                return a();\
            ')

            for i in range(int(len(image_info)/7)):
                images[image_info[(i*7)]] = image_info[(i*7)+1:i*7+6:]

        except Exception as e:
            log.error(e)
            driver_utils.save_screenshot()
        
        log.info('Images for group: %s\n%s'%(group_name, json.dumps(images, indent=4, sort_keys=True)))
        return images

    def get_selected_firmware_image(self, group_name):
        driver = self.driver
        driver_utils = self.driver_utils
        selected_firmware_image = ''

        try:
            selected_firmware_image = driver.execute_script(
                'return $(".key:contains(\'Selected Firmware Image\')").next().text().split(" (")[0]')
        except Exception as e:
            log.error(e)
            driver_utils.save_screenshot()

        log.info('selected_firmware_image under Group: %s is %s'%(group_name, selected_firmware_image))
        return selected_firmware_image

    def get_uploaded_images_details(self, group_name):
        driver = self.driver
        driver_utils = self.driver_utils
        images_details = {
            'header': [],
            'image_info': []
        }

        try:
            time.sleep(1)
            log.info('Navigating to "Images" tab.')
            driver.find_element_by_id('mainPnltree__imgsTab').click()
            time.sleep(2)
            self.nav_router_group(group_name)
            header = driver.execute_script('function get_header(){\
                                    a=[];\
                                    $.each($(".x-grid3-hd:visible"), function(i, e){a.push(e.textContent)});\
                                    return a;\
                                }\
                                return get_header();')
            image_info = driver.execute_script('function get_header(){\
                                    a=[];\
                                    $.each($(".x-grid3-col:visible"), function(i, e){a.push(e.textContent)});\
                                    return a;\
                                }\
                                return get_header();')

            images_details['header'] = header[:-1]
            for i in range(int(len(image_info)/7)):
                images_details['image_info'].append(image_info[(i*7):i*7+6:])
        except Exception as e:
            log.error(e)
            driver_utils.save_screenshot()

        log.info('selected_firmware_image under Group: %s is %s'
                %(group_name, json.dumps(images_details, indent=4, sort_keys=True)))
        return images_details

class DeviceFileManagement(ConfigNavigation):
    ''' This class defines all the applicable opertaions under "Device File Management" page. '''

    def __init__(self, driver, *arg):
        self.arg = arg
        self.driver = driver
        self.driver_utils = DriverUtils(driver)

    def nav_group(self, group_type, group_name):
        '''
        Method to navigate to Router group.

        :param group_name: Name of the group to navigate.
        :type group_name: str
        '''
        driver = self.driver
        nav_group_succ = False

        try:
            group_span = driver.find_element_by_xpath('//span[contains(text(), "%s")]'%group_type)
            x_tree_node = group_span.find_element_by_xpath('../../..')
            group_elems = x_tree_node.find_elements_by_xpath('ul/li/div/a/span')

            group_elem = [elem for elem in group_elems if group_name.capitalize() in elem.text][0]
        except Exception as e: log.error(e)

        selected=''
        timeout = time.time() + 60*2
        while timeout>time.time():
            selected = group_elem.find_element_by_xpath('../..').get_attribute('class')
            if 'x-tree-selected' in selected:
                nav_group_succ = True
                break
            log.info('Clicking on "%s" group.'%group_name)
            group_elem.click()
            time.sleep(1)
        
        return nav_group_succ

    def router_file_mgmtnav_tab(self, tab_name):
        '''
        Method to navigate to given tab.

        :param group_name: Name of the tab to navigate.
        :type group_name: str
        '''

        driver = self.driver
        #Dictionary of sub_menu id tuples as per the selection.
        tab_ids = {
            'actions': 'gridsContainer__statusTab',
            'managed_files': 'gridsContainer__managedFilesTab',
            'file_management': 'gridsContainer__fileMgmtTab',
            'logs': 'gridsContainer__logTab'
        }
        #Determine tab id's depending on the requested tab_name.
        tab_id = tab_ids[tab_name]

        try:
            log.info('Clicking "%s"'% tab_id)
            driver.find_element_by_id('%s'%tab_id).click()
            time.sleep(2)

            #Wait unitl the clicked page is loaded completely.
            selected = ''
            timeout=time.time() + 60*2
            while timeout>time.time():
                log.info('Checking for sub_menu_active_id')
                selected = driver.find_element_by_id('%s'%tab_id).get_attribute('class')
                log.info('selected: %s' % selected)
                if 'x-tab-strip-active' in selected: break
                
                driver.find_element_by_id('%s'%tab_id).click()
                log.info('Waiting for tab to be active.')
                time.sleep(1)
        except Exception as e: log.error(e)
    
    def upload_image(self, group_type, group_name, file_name):
        '''
        Method to Upload firmware image in given router group.

        :param group_name: Group name to upload the image
        :type group_name: str
        :param image_name: Image name that needs to be uploaded.
        :type image_name: list

        device_type Options:
           * 'cgr1000': 'IOS-CGR'
           * 'ir800': 'IOS-IR800'
           * 'c800': 'IOS-C800'
        '''
        driver = self.driver
        driver_utils = self.driver_utils
        file_upload_started = False
        # log.info('Uploading the file: %s in the group: %s.'%(file_name, group_name))

        try:
            #Determine sub_menu id's depending on the requested sub_menu.
            self.nav_group(group_type, group_name)
            driver_utils.ignore_flash_error()
            self.nav_tab('actions')
            driver_utils.ignore_flash_error()

            log.info('Click on "Upload Image" button.')
            upload_button = driver.execute_script('return $("#uploadBtn:visible")[0];')

            if not upload_button: raise Exception('"Upload Image" not visible.')
            upload_class = upload_button.get_attribute('class')
            if 'x-item-disabled' in upload_class: raise Exception('"Upload Image" is disabled.')

            upload_button.click()
            time.sleep(2)
            log.info('Selecting file %s.'%file_name)
            driver.execute_script('return $("td:contains(\'%s\')").next()[0]'%file_name).click()
            time.sleep(2)

            log.info('Click on "Upload File" button to start upload.')
            driver.execute_script('return $("button:contains(\'Upload File\'):visible")[0]').click()
            time.sleep(2)
            driver_utils.ignore_flash_error()
            time.sleep(1)
            
            log.info('Confirming - Start uploading!')
            driver.execute_script('return $("#uDFormUploadBtn:visible")[0]').click()
            time.sleep(2)
            driver_utils.ignore_flash_error()
            time.sleep(2)
            log.info('Click on "OK" button to start upload.')
            driver.execute_script('return $("button:contains(\'OK\'):visible")[0]').click()
            file_upload_started = True
        except Exception as e:
            log.error(e)
            driver_utils.save_screenshot()

        log.info('File: %s to group: %s is started: %s'%(file_name, group_name, file_upload_started))
        return file_upload_started

class Rules(ConfigNavigation):
    ''' This class defines all the applicable opertaions under "Device File Management" page. '''

    def __init__(self, driver, *arg):
        self.arg = arg
        self.driver = driver
        self.driver_utils = DriverUtils(driver)

    def add_rule(self, **kwargs):
        '''
        rules.add_rule(rule_name='txspeed',
                       activate = True
                       rule_literal='devicecategory='ROUTER' ethernettxspeed>=100 ethernettxspeed<160',
                       log_event = True,
                       log_event_name='txspeed',
                       sev_level='WARN',
                       user_defined_event_name='txspeed',
                       add_label = True,
                       add_label_name='txspeed',
                       show_label = True,
                       remove_label=False,
                       remove_label_name='')
        '''
        
        driver = self.driver
        driver_utils = self.driver_utils
        rule_added = False

        try:
            log.info('kwargs: %s'%kwargs)        
            rule_name = kwargs['rule_name']
            rule_literal = kwargs['rule_literal']

            log.info('Clicking "Add" rule button.')
            driver.find_element_by_id('ruleAddButton').click()
            time.sleep(1)

            log.info('Entering Rule Name: %s'%rule_name)
            driver.find_element_by_id('ruleName').clear()
            time.sleep(1)
            driver.find_element_by_id('ruleName').send_keys(rule_name)
            time.sleep(1)

            if 'activate' in kwargs:
                activate=kwargs['activate']
                log.info('Checking Activate Rule.')
                if activate: driver.find_element_by_id('ruleStatus').click()

            log.info('Entering Rule Literal: %s'%rule_literal)
            driver.find_element_by_xpath('//textarea[@id="ruleLiteral"]').clear()
            time.sleep(1)
            driver.find_element_by_xpath('//textarea[@id="ruleLiteral"]').send_keys(rule_literal)
            time.sleep(1)

            if 'log_event' in kwargs and kwargs['log_event']==True:
                driver.find_element_by_id('cbEvent').click()
                time.sleep(1)
                driver.find_element_by_id('eventMsg').clear()
                time.sleep(1)
                driver.find_element_by_id('eventMsg').clear()
                time.sleep(1)
                log_event_name=kwargs['log_event_name']
                driver.find_element_by_id('eventMsg').send_keys(log_event_name)
                time.sleep(1)

                sev_selector = driver.find_element_by_id('addSeverityNew')
                time.sleep(1)

                sev_selector.click()
                dropdown_elements = driver.find_elements_by_xpath('//div[starts-with(@class, "x-combo-list-item")]')
                dropdown_elements = [element for element in dropdown_elements if element.is_displayed()]
                sev_selector.click()
                sev_level = kwargs['sev_level']

                for element in dropdown_elements:
                    sev_selector.click()
                    time.sleep(1)
                    if element.text == sev_level:
                        element.click()
                        time.sleep(1)
                        break

            if 'user_defined_event_name' in kwargs:
                user_defined_event_name=kwargs['user_defined_event_name']
                log.info('Entering User-defined Event.')
                driver.find_element_by_id('eventNameNew').clear()
                time.sleep(1)
                driver.find_element_by_id('eventNameNew').send_keys(user_defined_event_name)
                time.sleep(1)

            if 'add_label' in kwargs and kwargs['add_label']==True:
                add_label_name=kwargs['add_label_name']
                
                log.info('Clicking checkbox for Add Label.')
                driver.find_element_by_id('cbAddLabel').click()
                time.sleep(1)
                driver.find_element_by_id('addLabelName').clear()
                time.sleep(1)
                driver.find_element_by_xpath('//input[contains(@id, "addLabelName")]/following-sibling::img').click()
                time.sleep(1)
                driver.find_element_by_id('addLabelName').click()
                time.sleep(1)
                driver.find_element_by_id('addLabelName').send_keys(add_label_name)
                time.sleep(2)
                driver.find_element_by_xpath('//input[contains(@id, "addLabelName")]/following-sibling::img').click()
                time.sleep(1)

            if 'show_label' in kwargs and kwargs['show_label']==True:
                driver.find_element_by_id('statusLabel').click()
                time.sleep(1)

            if 'remove_label' in kwargs and kwargs['remove_label']==True:
                remove_label_name=kwargs['remove_label_name']
                
                log.info('Clicking checkbox for Remove Label.')
                driver.find_element_by_id('cbRmLabel').click()
                time.sleep(1)
                driver.find_element_by_id('rmLabelName').clear()
                time.sleep(1)
                driver.find_element_by_xpath('//input[contains(@id, "rmLabelName")]/following-sibling::img').click()
                time.sleep(1)
                driver.find_element_by_id('rmLabelName').click()
                time.sleep(1)
                driver.find_element_by_id('rmLabelName').send_keys(remove_label_name)
                time.sleep(2)
                driver.find_element_by_xpath('//input[contains(@id, "rmLabelName")]/following-sibling::img').click()
                time.sleep(1)
                # We are doing this skip error while saving remove label.
                log.info('Unchecking cbRmLabel')
                driver.find_element_by_id('cbRmLabel').click()
                time.sleep(1)
                log.info('Checking back cbRmLabel')
                driver.find_element_by_id('cbRmLabel').click()
                time.sleep(1)

            driver.find_element_by_xpath('//i[@class="fa fa-floppy-o"]').click()
            time.sleep(1)

            headers_elems = driver.find_elements_by_xpath('//span[contains(@class, "x-window-header-text")]')
            span_text_elems = driver.find_elements_by_xpath('//span[contains(@class, "ext-mb-text")]')
            headers_elems = [elem for elem in headers_elems if elem.is_displayed()]
            span_text_elems = [elem for elem in span_text_elems if elem.is_displayed()]
            
            update = span_text_elems[0] if span_text_elems else None
            if headers_elems and len(headers_elems)>1: header = headers_elems[1]
            else: header = headers_elems[0]

            log.info('header: %s, update: %s'%(header.text, update.text))

            if header.text.lower()=='error':
                driver_utils.save_screenshot()
                driver.find_element_by_xpath('//button[contains(text(), "OK")]').click()
                time.sleep(1)
                close_button = driver_utils.get_visible_div_by_class('x-tool-close')
                log.info('Closing the popup.')
                close_button.click()
            else:
                driver.find_element_by_xpath('//button[contains(text(), "OK")]').click()
                time.sleep(1)
                rule_added = True
        except Exception as e:
            driver_utils.save_screenshot()
            log.error(e)
            driver.refresh()
            time.sleep(5)

        log.info('\n\nGiven Options: %s\n\n'%kwargs)
        log.info(banner('Rule with is added: %s'%rule_added))
        return rule_added

    def activate_rule(self, rule_name):
        
        driver = self.driver

        log.info('Click on the checkbox of the given rule.')
        rule_elem = driver.find_element_by_id('ruleGrid').find_element_by_xpath('//a[contains(text(),"%s")]'%rule_name)
        #Getting the first td element of this tr row.
        check_box_td = rule_elem.find_element_by_xpath('../../..').find_elements_by_tag_name('td')[0]
        #Click the checkbox of the rule_elem.
        check_box_td.find_element_by_xpath('div/div').click()
        time.sleep(1)

        log.info('Clicking "Activate" rule button.')
        driver.find_element_by_id('ruleActivateButton').click()
        time.sleep(1)

        log.info('Clicking "Yes" to activate.')
        driver.find_element_by_xpath('//button[contains(text(), "Yes")]').click()
        time.sleep(1)

        log.info('Checking the confirmation of activate.')
        driver.find_element_by_xpath('//button[contains(text(), "OK")]').click()
        time.sleep(1)

    def deactivate_rule(self, rule_name):
        
        driver = self.driver

        log.info('Click on the checkbox of the given rule.')
        rule_elem = driver.find_element_by_id('ruleGrid').find_element_by_xpath('//a[contains(text(),"%s")]'%rule_name)
        #Getting the first td element of this tr row.
        check_box_td = rule_elem.find_element_by_xpath('../../..').find_elements_by_tag_name('td')[0]
        #Click the checkbox of the rule_elem.
        check_box_td.find_element_by_xpath('div/div').click()
        time.sleep(1)

        log.info('Clicking "Deactivate" rule button.')
        driver.find_element_by_id('ruleDeactivateButton').click()
        time.sleep(1)

        log.info('Clicking "Yes" to deactivate.')
        driver.find_element_by_xpath('//button[contains(text(), "Yes")]').click()
        time.sleep(1)

        log.info('Checking the confirmation of deactivate.')
        driver.find_element_by_xpath('//button[contains(text(), "OK")]').click()
        time.sleep(1)

    def delete_rule(self, rule_name):
        
        driver = self.driver
        driver_utils = self.driver_utils
        rule_deleted = False

        try:
            log.info('Click on the checkbox of the given rule.')
            rule_elem = driver.find_element_by_id('ruleGrid').find_element_by_xpath('//a[contains(text(),"%s")]'%rule_name)
            #Getting the first td element of this tr row.
            check_box_td = rule_elem.find_element_by_xpath('../../..').find_elements_by_tag_name('td')[0]
            #Click the checkbox of the rule_elem.
            check_box_td.find_element_by_xpath('div/div').click()
            time.sleep(1)

            log.info('Clicking "Delete" rule button.')
            driver.find_element_by_id('ruleDeleteButton').click()
            time.sleep(1)

            log.info('Clicking "Yes" to delete.')
            driver.find_element_by_xpath('//button[contains(text(), "Yes")]').click()
            time.sleep(1)

            log.info('Checking the confirmation of delete.')
            driver.find_element_by_xpath('//button[contains(text(), "OK")]').click()
            time.sleep(1)
            rule_deleted = True
        except Exception as e:
            driver_utils.save_screenshot()
            log.error(e)
            driver.refresh()
            time.sleep(5)

        log.info(banner('Rule with name: %s is delted: %s'%(rule_name, rule_deleted)))
        return rule_deleted

    def modify_rule(self, rule_name, rule_literal):
        
        driver = self.driver
        driver_utils = self.driver_utils
        rule_modifed = False

        log.info('Click on the given rule.')
        rule = driver.find_element_by_xpath('//a[contains(text(), "%s")]'%rule_name)
        rule.click()
        time.sleep(1)

        log.info('Entering Rule Literal: %s'%rule_literal)
        driver.find_element_by_xpath('//textarea[@id="ruleLiteral"]').clear()
        time.sleep(1)
        driver.find_element_by_xpath('//textarea[@id="ruleLiteral"]').send_keys(rule_literal)
        time.sleep(1)

        log.info('Clicking on Save button.')
        driver.find_element_by_xpath('//i[@class="fa fa-floppy-o"]').click()
        time.sleep(1)

        popup_header = driver.execute_script('return $(".x-window-dlg .x-window-header-text:visible").text()')
        update_message = driver.execute_script('return $(".x-window-dlg .ext-mb-text:visible").text()')
        log.info('popup_header: %s\nupdate_message: %s'%(popup_header, update_message))

        if popup_header.lower()=='error' or popup_header.lower()=='failure':
            driver.find_element_by_xpath('//button[contains(text(), "OK")]').click()
            time.sleep(1)

            close_button = driver_utils.get_visible_div_by_class('x-tool-close')
            log.info('Click on close button.')
            close_button.click()
        else:
            driver.find_element_by_xpath('//button[contains(text(), "OK")]').click()
            time.sleep(1)
            rule_modifed = True

        return rule_modifed

class TunnelProvisioning(ConfigNavigation):
    ''' This class defines all the applicable opertaions under "Tunnel Provisioning" page. '''

    def __init__(self, driver, *arg):
        self.arg = arg
        self.driver = driver
        self.driver_utils = DriverUtils(driver)

    def nav_tunnel_group(self, group_name):
        '''
        Method to navigate to Tunnel group.

        :param group_name: Name of the group to navigate.
        :type group_name: str
        '''
        driver = self.driver
        driver_utils = self.driver_utils
        nav_group_succ = False

        try:
            log.info('Navigating to Tunnel group: %s'%group_name)
            time.sleep(1)
            group_name = group_name.lower()
            matched_groups = driver.find_elements_by_xpath('//span[contains(text(), "%s")]'%group_name)
            log.info('matched_groups: %s'%[group.text.capitalize() for group in matched_groups])

            tunnel_group = [group for group in matched_groups if group_name.capitalize() in group.text.split(' (')][0]
            selected=''
            timeout = time.time() + 60*2
            while timeout>time.time():
                selected = tunnel_group.find_element_by_xpath('../..').get_attribute('class')
                if 'x-tree-selected' in selected:
                    nav_group_succ = True
                    break
                log.info('Clicking on Router Group: %s'%group_name)
                time.sleep(1)
                tunnel_group.click()
                time.sleep(1)
        except Exception as e:
            driver_utils.save_screenshot()
            log.error('Please provide a valid Router group.')

        return nav_group_succ

    def nav_tab(self, tab_name):
        '''
        Method to navigate to a given tab.

        :param tab_name: Name of the tab to navigate.
        :type tab_name: str
        '''
        driver = self.driver
        driver_utils = self.driver_utils
        log.info('Navigating to %s'%tab_name)

        #Dictionary of tab id tuples as per the selection.
        tab_ids = {
            'group_members': 'gridsContainer__gridTab',
            'gateway_tunnel_addition': 'gridsContainer__iotGatewayTab',
            'far_tunnel_addition': 'gridsContainer__cgr1000Tab',
            'her_tunnel_addition': 'gridsContainer__asr1000Tab',
            'her_tunnel_deletion': 'gridsContainer__asr1000DeleteTab',
            'Router_BootStrap_Config':'gridsContainer__asr1000FactoryConfigTab',
            'far_factory_reprov': 'gridsContainer__asr1000FactoryConfigTab',
            'reprov_actions': 'gridsContainer__reprovisioningActionsTab',
            'policies': 'gridsContainer__policiesTab',
            'bootstrapping': 'gridsContainer__BootstrappingTab',
        }

        #Determine tab id's depending on the requested tab_name.
        tab_id = tab_ids[tab_name]

        try:
            log.info('Clicking "%s"'% tab_id)
            driver.find_element_by_id('%s'%tab_id).click()
            time.sleep(2)

            #Wait unitl the clicked page is loaded completely.
            selected = ''
            timeout=time.time() + 60*2
            while timeout>time.time():
                log.info('Checking for sub_menu_active_id')
                selected = driver.find_element_by_id('%s'%tab_id).get_attribute('class')
                log.info('selected: %s' % selected)
                if 'x-tab-strip-active' in selected: break
                
                driver.find_element_by_id('%s'%tab_id).click()
                log.info('Waiting for tab to be active.')
                time.sleep(1)
        except Exception as e:
            log.info(e)
            driver_utils.save_screenshot()

    def find_tunnel_group(self, group_name):
        '''
        Method to find a tunnel group in FND portal.

        :param group_name: Name of the tunnel group to find.
        :type group_name: str
        '''
        driver = self.driver
        group_found = False

        try:
            driver.refresh()
            anchor_span_elems = driver.find_elements_by_xpath('//a[@class="x-tree-node-anchor"]//span')
            tunnel_groups = [span_elem.text.split(' (')[0].capitalize() for span_elem in anchor_span_elems]
            log.info('Current Tunnel Groups: %s' % tunnel_groups)

            log.info('find group_name: %s'%group_name)
            if group_name.capitalize() in tunnel_groups:
                group_found = True
                log.info('Given tunnel "group_name:%s" found in the exisitng tunnel groups.'%group_name)
        except StaleElementReferenceException as e: log.error('StaleElementReferenceException: %s' % e)
        except Exception as e: log.info(e)

        return group_found

    def add_tunnel_group(self, group_name):
        '''
        Method to add a tunnel group in FND portal.

        :param group_name: Name of the tunnel group to add.
        :type group_name: str
        '''

        driver = self.driver
        tunnel_group_added = False
        group_found = self.find_tunnel_group(group_name)

        if group_found:
            log.error('There is a tunnel group already exisitng with this name. Please choose a differnt name.')
            return tunnel_group_added
        else:
            try:
                time.sleep(3)
                log.info('Adding new tunnel group: %s' % group_name)
                log.info('Clicking on add button')
                driver.find_element_by_xpath('//div[@id="tunnelGroup_toolsContainer"]//div').click()
                time.sleep(1)
                log.info('Entering group name: %s'%group_name)
                driver.find_element_by_xpath('//input[@id="groupNameTP"]').send_keys(group_name)
                time.sleep(1)
                log.info('Clicking on Add button.')
                driver.execute_script('return $("button:contains(\'Add\'):visible")[0]').click()
                tunnel_group_added = True
                time.sleep(3)
            except Exception as e:
                log.error('Unable to add tunnel group.')
                log.info(e)

        #Waiting till new group is added.
        tunnel_groups = []
        timeout = time.time()+60
        while timeout>time.time():
            #Finding anchor tags with a class "x-tree-node-anchor". This is a list of configuration groups on the portal.
            anchor_span_elems = driver.find_elements_by_xpath('//a[@class="x-tree-node-anchor"]//span')
            tunnel_groups = [span_elem.text.split(' (')[0].capitalize() for span_elem in anchor_span_elems]
            log.info('New tunnel groups: %s' % tunnel_groups)
            if group_name.capitalize() in tunnel_groups: break
            log.info('Waiting for tunnel group to show up.')
            time.sleep(3)

        return tunnel_group_added

    def delete_tunnel_group(self, group_name):
        '''
        Method to delete a tunnel group under "Tunnel Provisioning" page.

        :param group_name: Name of the tunnel group to delete.
        :type group_name: str
        '''
        driver = self.driver
        tunnel_group_deleted = False
        group_found = self.find_tunnel_group(group_name)
        log.info('group_found: %s' % group_found)

        if not group_found:
            log.error('There is a no group with this name. Please choose a differnt name.')
            return tunnel_group_deleted
        else:
            try:
                current_groups = driver.find_elements_by_xpath('//a[@class="x-tree-node-anchor"]//span')
                #Finding the delete button for the given group_name and click it.
                for current_group in current_groups:
                    if current_group.text.split(' (')[0].capitalize() == group_name.capitalize():
                        del_button = current_group.find_element_by_xpath('following-sibling::div/div[@class="x-tool x-tool-ciscoDelete"]')
                        driver.execute_script('$(arguments[0]).click();', del_button)
                        break
                #Confirming the delete in popup.
                log.info('Confirming the delete.')
                driver.find_element_by_xpath('//button[contains(text(), "Yes")]').click()
                log.info('Given tunnel group deleted.')
                tunnel_group_deleted = True
            except:
                log.error('Unable to delete tunnel group.')

        return tunnel_group_deleted

    def change_tunnel_group(self, curr_group, new_group, router_eids):
        '''
        Method to move device from one tunnel group to other.

        :param curr_group: Current tunnel group where the device is present.
        :type curr_group: str
        :param new_group: New tunnel group where the device needs to be moved.
        :type new_group: str
        :param router_eids: Router eids of the test devices that needs to be changed.
        :type router_eids: list
        '''

        log.info('Changing the device configuration group from %s to %s.' % (curr_group, new_group))
        driver = self.driver
        driver_utils = self.driver_utils
        tunnel_group_changed = False

        # driver.find_element_by_xpath('//span[contains(text(),"%s")]'%curr_group).click()
        log.info('Navigate to %s' % curr_group)
        self.nav_tunnel_group(curr_group)
        time.sleep(1)
        self.nav_tab('group_members')
        time.sleep(1)

        #Click dropdown to select 'ROUTER' device type.
        log.info('\nClicking ROUTER from device selection dropdown.')
        driver.find_element_by_xpath('//input[@id="memberSelectCombo"]//following-sibling::img').click()
        driver.find_element_by_xpath('//div[contains(text(),"ROUTER")]').click()
        device_selection = driver.find_element_by_xpath('//input[@id="memberSelectCombo"]').get_attribute('value')
        log.info('current device_selection: %s' % device_selection)
        time.sleep(3)

        try:
            log.info('Select all the test devices.')
            for router_eid in router_eids:
                #Getting anchor element with router_eid under the element with id:"netElementGrid".
                router_elem = driver.find_element_by_id('netElementGrid').find_element_by_xpath('//a[contains(text(),"%s")]'%router_eid)
                #Getting the first td element of this tr row.
                check_box_td = router_elem.find_element_by_xpath('../../..').find_elements_by_tag_name('td')[0]
                log.info('Clicking checkbox for router_eid: %s' % router_eid)
                check_box_td.find_element_by_xpath('div/div').click()
                time.sleep(2)

            log.info('\nClick on "Change Tunnel Group" button.')
            driver.find_element_by_xpath('//button[contains(text(),"Change Tunnel Group")]').click()
            time.sleep(3)

            log.info('\nSelect %s from drop down and move to it.' % new_group)
            driver.find_element_by_xpath('//label[contains(text(),"Tunnel Group:")]//following-sibling::div').find_element_by_tag_name('img').click()
            time.sleep(2)
            driver.find_element_by_xpath('//div[contains(text(),"%s")]'%new_group).click()
            time.sleep(2)
            driver.find_element_by_id('CBCommandsButton').click()
            time.sleep(2)
            driver.find_element_by_xpath('//button[contains(text(), "OK")]').click()
            time.sleep(2)
            log.info('Change tunnel group done.')
            tunnel_group_changed = True
        except (NoSuchElementException, ElementNotVisibleException) as e:
            driver_utils.save_screenshot()
            log.error('Unable to find the element: %s' % e)

        return tunnel_group_changed

    def replace_tunnel_template_with_text(self, group_name, template_name, replace_text):
        '''
        Method to edit configuration template with the given text.

        :param group_name: Current router group where template has to be edited.
        :type group_name: str
        :param replace_text: Text that needs to be replaced.
        :type replace_text: str
        '''
        driver = self.driver
        driver_utils = self.driver_utils
        template_updated = False

        log.info('Navigate to configuration template.')
        self.nav_tunnel_group(group_name)
        time.sleep(1)
        self.nav_tab(template_name)
        time.sleep(1)

        log.info('Clearing the exisitng template.')
        text_areas = driver.find_elements_by_xpath('//textarea[@name="value"]')
        text_area = [text_area for text_area in text_areas if text_area.is_displayed()][0]
        text_area.clear()
        time.sleep(3)


        replace_text_len = len(replace_text)
        chunk_size = 1000
        replace_text_chunks = [replace_text[i:i+chunk_size] for i in range(0, len(replace_text), chunk_size)]

        log.info('Replacing with new text.')
        # text_area.send_keys(replace_text)
        for i in range(len(replace_text_chunks)):
            log.info('Sending chunk : %d'%i)
            text_area.send_keys(replace_text_chunks[i])
            time.sleep(1)

        log.info('Saving the changes.')
        save_changes = driver.find_elements_by_xpath('//i[@class="fa fa-floppy-o"]')
        save_change = [save_change for save_change in save_changes if save_change.is_displayed()][0]
        save_change.click()
        time.sleep(3)

        popup_headers = driver.find_elements_by_xpath('//span[contains(@class, "x-window-header-text")]')
        for popup_header in popup_headers:
            if popup_header.is_displayed() == True:
                if 'Failure' not in popup_header.text: template_updated = True
                break

        driver.find_element_by_xpath('//button[contains(text(), "OK")]').click()
        time.sleep(3)

        return template_updated

    def reprovision_actions(self, group_name, **kwargs):

        driver = self.driver
        driver_utils = self.driver_utils
        reprovision_actions_scheduled = False

        reprov_action = kwargs.get('reprov_action', None)
        interface_name = kwargs.get('interface_name', None)
        interface_type = kwargs.get('interface_type', None)

        if None in [reprov_action, interface_name, interface_type]:
            log.error('Provide all the required fields.')
            return reprovision_actions_scheduled

        try:
            self.nav_tunnel_group(group_name)
            self.nav_tab('reprov_actions')

            action_combo = driver.find_element_by_id('actionCombo')
            interface_combo = driver.execute_script('return $("#interfaceCombo").next()[0]')
            interface_type_combo = driver.find_element_by_id('interfaceTypeCombo')

            time.sleep(1)
            action_combo.click()
            time.sleep(1)
            log.info('\nClicking on %s Action.'%reprov_action)
            driver.execute_script('return $(".x-combo-list-item:contains(\'%s\')")[0]'%reprov_action).click()

            time.sleep(1)
            interface_combo.click()
            time.sleep(1)
            log.info('\nClicking on Interface Name: %s'%interface_name)
            driver.execute_script('\
                        return $(".x-combo-list-item")\
                        .filter(\
                            function(){return $(this).text()==="%s";}\
                        )[0]'%interface_name).click()

            time.sleep(1)
            #interface_combo.click()
            interface_type_combo.click()
            time.sleep(1)
            log.info('\nClicking on Interface Type: %s'%interface_type)
            driver.execute_script('\
                        return $(".x-combo-list-item")\
                        .filter(\
                            function(){return $(this).text()==="%s";}\
                        )[0]'%interface_type).click()

            log.info(banner('Clicking on Start Reprovisioning button.'))
            driver.execute_script('$(\'button:contains("Start")\').click()')
            time.sleep(3)

            log.info('Clicking on "OK" button.')
            driver.execute_script('return $(".x-window-dlg button:contains(\'OK\'):visible")[0]').click()
            time.sleep(5)
        except Exception as e:
            log.error(e)
            driver_utils.save_screenshot()

        log.info('Reprovision Actions for group: %s is scheduled: %s'%(group_name, reprovision_actions_scheduled))
        return reprovision_actions_scheduled

class Groups(ConfigNavigation):
    ''' This class defines all the applicable opertaions under "Tunnel Provisioning" page. '''

    def __init__(self, driver, *arg):
        self.arg = arg
        self.driver = driver
        self.driver_utils = DriverUtils(driver)

    def nav_group(self, group_name):
        '''
        Method to navigate to a group.

        :param group_name: Name of the group to navigate.
        :type group_name: str
        '''
        driver = self.driver
        nav_group_succ = False
        
        # if group_name not in ['IR530', 'GATEWAY-IR500', 'EXTENDER-IR500']:group_name = group_name.lower()
        matched_groups = driver.find_elements_by_xpath('//span[contains(text(), "%s")]'%group_name)
        log.info('matched_groups: %s'%[group.text for group in matched_groups])
        try:
            selected_group = [group for group in matched_groups if group_name in group.text.split(' (')][0]
            # if group_name=='IR530':pass
            # else: selected_group = [group for group in matched_groups if group_name.capitalize() in group.text.split(' (')][0]
            selected=''
            timeout = time.time() + 60*2
            while timeout>time.time():
                selected = selected_group.find_element_by_xpath('../..').get_attribute('class')
                if 'x-tree-selected' in selected:
                    nav_group_succ = True
                    break
                log.info('Clicking on Configuration Group: %s'%group_name)
                selected_group.click()
                time.sleep(1)
        except Exception as e: log.error('Please provide a valid Router group.')

        return nav_group_succ

    def find_group(self, group_name):
        '''
        Method to find a tunnel group in FND portal.

        :param group_name: Name of the tunnel group to find.
        :type group_name: str
        '''
        driver = self.driver
        group_found = False

        try:
            driver.refresh()
            anchor_span_elems = driver.find_elements_by_xpath('//a[@class="x-tree-node-anchor"]//span')
            groups = [span_elem.text.split(' (')[0].capitalize() for span_elem in anchor_span_elems]
            log.info('groups: %s'%groups)

            log.info('group_name: %s, "group_name.capitalize() in groups": %s'
                    %(group_name, (group_name.capitalize() in groups)))

            if group_name.capitalize() in groups:
                group_found = True
                log.info('Given "group_name:%s" found in the exisitng groups.'%group_name)
        except StaleElementReferenceException as e: log.error('StaleElementReferenceException: %s' % e)
        except Exception as e: log.info(e)

        return group_found

    def add_group(self, group_name):
        '''
        Method to add a tunnel group in FND portal.

        :param group_name: Name of the tunnel group to add.
        :type group_name: str
        '''

        driver = self.driver
        tunnel_group_added = False
        group_found = self.find_group(group_name)

        if group_found:
            log.error('There is a tunnel group already exisitng with this name. Please choose a differnt name.')
            return tunnel_group_added
        else:
            try:
                log.info('Adding new tunnel group: %s' % group_name)
                time.sleep(1)
                driver.find_element_by_xpath('//div[@id="group_management_toolsContainer"]//div').click()
                driver.find_element_by_xpath('//input[@id="groupNameTP"]').send_keys(group_name)
                driver.find_element_by_xpath('//div[contains(@class, "x-window-plain")]//button[contains(text(), "Add")]').click()
                tunnel_group_added = True
                time.sleep(1)
            except Exception as e:
                log.error('Unable to add group.')
                log.info(e)

        #Waiting till new group is added.
        tunnel_groups = []
        timeout = time.time() + 60*2
        while timeout>time.time():
            #Finding anchor tags with a class "x-tree-node-anchor". This is a list of configuration groups on the portal.
            anchor_span_elems = driver.find_elements_by_xpath('//a[@class="x-tree-node-anchor"]//span')
            groups = [span_elem.text.split(' (')[0].capitalize() for span_elem in anchor_span_elems]
            log.info('New tunnel groups: %s' % groups)
            log.info('Waiting for group to show up. %s'%group_name)
            log.info(group_name in groups)
            if group_name.capitalize() in groups : break
            time.sleep(1)

        return tunnel_group_added

    def delete_group(self, group_name):
        '''
        Method to delete a tunnel group under "Tunnel Provisioning" page.

        :param group_name: Name of the tunnel group to delete.
        :type group_name: str
        '''
        driver = self.driver
        group_deleted = False
        group_found = self.find_group(group_name)
        log.info('group_found: %s' % group_found)

        if not group_found:
            log.error('There is a no group with this name. Please choose a differnt name.')
            return group_deleted
        else:
            try:
                current_groups = driver.find_elements_by_xpath('//a[@class="x-tree-node-anchor"]//span')
                #Finding the delete button for the given group_name and click it.
                for current_group in current_groups:
                    if current_group.text.split(' (')[0] == group_name.capitalize():
                        del_button = current_group.find_element_by_xpath('following-sibling::div/div[@class="x-tool x-tool-ciscoDelete"]')
                        driver.execute_script('$(arguments[0]).click();', del_button)
                        break
                #Confirming the delete in popup.
                log.info('Confirming the delete.')
                driver.execute_script('$(".x-window-footer .x-btn-text:contains(\'OK\')").click()')
                time.sleep(2)
                log.info('Clicking on OK button.')
                driver.execute_script('$(".x-window-footer .x-btn-text:contains(\'OK\')").click()')
                log.info('Given tunnel group deleted.')

                group_deleted = True
            except:
                log.error('Unable to delete tunnel group.')

        return group_deleted
    
    def rename_group(self, group_name, new_name):
        '''
        Method to add a tunnel group in FND portal.

        :param group_name: Name of the tunnel group to rename.
        :type group_name: str
        :param group_name: New name of the tunnel group.
        :type group_name: str
        '''

        driver = self.driver
        driver_utils = self.driver_utils
        group_renamed = False

        try:
            anchor_span_elems = driver.find_elements_by_xpath('//a[@class="x-tree-node-anchor"]//span')
            firmware_groups = [span_elem.text.split(' (')[0].capitalize() for span_elem in anchor_span_elems]
            log.info('Current firmware_groups: %s'%firmware_groups)

            #Finding the edit button for the given group_name and click it.
            for current_group in anchor_span_elems:
                if current_group.text.split(' (')[0].capitalize() == group_name.capitalize():
                    rename_button = current_group.find_element_by_xpath('following-sibling::div/div[@class="x-tool x-tool-ciscoEdit"]')
                    time.sleep(1)
                    current_group.click()
                    time.sleep(2)
                    driver.execute_script('$(arguments[0]).click();', rename_button)
                    time.sleep(2)
                    break

            log.info('Entering the new name.')
            driver.find_element_by_id('groupName').clear()
            driver.find_element_by_id('groupName').send_keys(new_name)
            time.sleep(1)
            #Confirming the edit in popup.
            log.info('Confirming the edit.')
            driver.execute_script('$("button:contains(\'Ok\')").click()')
            time.sleep(1)
            driver.execute_script('$("button:contains(\'OK\')").click()')
            group_renamed = True
        except Exception as e:
            log.error('Unable to edit firmware group.\n%s'%e)
            driver.refresh()

        #Waiting till new group is updated.
        tunnel_groups = []
        timeout = time.time() + 60*2
        while timeout>time.time():
            anchor_span_elems = driver.find_elements_by_xpath('//a[@class="x-tree-node-anchor"]//span')
            groups = [span_elem.text.split(' (')[0].capitalize() for span_elem in anchor_span_elems]
            log.info('New tunnel groups: %s' % groups)
            log.info('Waiting for group to show up. %s'%new_name)
            log.info(new_name in groups)
            if new_name.capitalize() in groups : break
            time.sleep(1)

        return group_renamed

    def remove_from_group(self, group_name):
        try:
            remove_from_group = False
            driver = self.driver
            driver_utils = self.driver_utils

            driver.find_element_by_xpath("//div[@id='groupsTree']//span[contains(text(),'%s')]" % group_name).click()

            driver_utils.wait_until_element_exists(
                xpath="//div[@id='gridsContainer']//thead//td[1]//div[@class='x-grid3-hd-inner x-grid3-hd-checker']")
            driver.find_element_by_xpath(
                "//div[@id='gridsContainer']//thead//td[1]//div[@class='x-grid3-hd-inner x-grid3-hd-checker']")

            # driver_utils.wait_until_element_exists(
            #    xpath="//div[@id='netElementGrid']//thead//td[1]//div[@class='x-grid3-hd-checker']")
            # driver.find_element_by_xpath(
            #    "//div[@id='netElementGrid']//thead//td[1]//div[@class='x-grid3-hd-checker']").click()
            driver.find_element_by_xpath("//table[@id='removeFromGroup']//button[text()='Remove from group']").click()
            driver.find_element_by_xpath("//button[text()='Yes']").click()
            driver.find_element_by_xpath("//button[text()='OK']").click()

            remove_from_group = True

        except Exception as e:
            log.error('Unable to remove from group.', e)

        return remove_from_group

    def change_group(self, current_group, change_group):
        try:
            group_status = False
            driver = self.driver
            driver_utils = self.driver_utils

            driver.find_element_by_xpath("//div[@id='groupsTree']//span[contains(text(),'%s')]" % current_group).click()

            driver_utils.wait_until_element_exists(
                xpath="//div[@id='netElementGrid']//thead//td[1]//div[@class='x-grid3-hd-checker']")
            driver.find_element_by_xpath(
                "//div[@id='netElementGrid']//thead//td[1]//div[@class='x-grid3-hd-checker']").click()
            driver.find_element_by_xpath("//table[@id='changeGroup']//button[text()='Change Group']").click()
            driver.find_element_by_xpath(
                "//div[@class=' x-window x-window-plain x-resizable-pinned'][contains(@style,'visibility: visible;')]//img[@class='x-form-trigger x-form-arrow-trigger']").click()
            driver.find_element_by_xpath(
                "//div[contains(@style,'visibility: visible')]//div[contains(text(),'%s')]" % change_group).click()
            driver.find_element_by_xpath("//table[@id='CBCommandsButton']//button[text()='Change Group']").click()
            driver.find_element_by_xpath("//button[text()='OK']").click()

            group_status = True


        except Exception as e:
            log.error('Unable to change group.', e)

        return group_status

    def add_device_to_group(self, group_name):
        try:
            add_group_status = False
            driver = self.driver
            driver_utils = self.driver_utils

            driver.find_element_by_xpath("//div[@id='groupsTree']//span[contains(text(),'ENDPOINT ')]").click()
            # time.sleep(1)
            #
            # driver.find_element_by_xpath("//input[@id='searchQuery']").clear()
            # driver.find_element_by_xpath("//input[@id='searchQuery']").send_keys('deviceCategory:endpoint')
            # driver.find_element_by_xpath("//input[@id='searchQuery']/../table").click()
            time.sleep(2)
            driver.find_element_by_xpath(
                "//div[@id='gridsContainer']//div[@class='x-grid3-header-offset']//td[1]//div[@class='x-grid3-hd-inner x-grid3-hd-checker']").click()
            #driver.find_element_by_xpath(
            #    "//div[@id='netElementGrid']//div[@class='x-grid3-row  x-grid3-row-first']//td[1]//div[@class='x-grid3-row-checker']").click()
            driver.find_element_by_xpath("//table[@id='addToGroup']//button[text()='Add to Group']").click()
            driver.find_element_by_xpath(
                "//div[@class=' x-window x-window-plain x-resizable-pinned'][contains(@style,'visibility: visible;')]//img[@class='x-form-trigger x-form-arrow-trigger']").click()
            driver.find_element_by_xpath(
                "//div[contains(@style,'visibility: visible')]//div[contains(text(),'%s')]" % group_name).click()
            driver.find_element_by_xpath("//table[@id='CBCommandsButton']//button[text()='Add To Group']").click()
            time.sleep(2)
            popup_header = driver.execute_script('return $(".x-window-dlg .x-window-header-text:visible").text()')
            popup_message = driver.execute_script('return $(".x-window-dlg .ext-mb-text:visible").text()')
            log.info('\npopup_header: %s\npopup_message: %s' % (popup_header, popup_message))

            if 'ERROR' in popup_header:
                driver_utils.save_screenshot()
                time.sleep(1)
                log.info('Unable to add devices to the group: %s.' % group_name)
                driver.find_element_by_xpath('//button[contains(text(), "OK")]').click()
                time.sleep(1)
                close_button = driver_utils.get_visible_div_by_class('x-tool-close')
                log.info('Click on close button.')
                close_button.click()

            if 'SUCCESS' in popup_header:
                log.info('Added devices to the group: %s' % group_name)
                log.info('Clicking on "OK" button.')
                driver.find_element_by_xpath('//button[contains(text(), "OK")]').click()
                time.sleep(1)
                add_group_status = True

            upload_response = str(driver.execute_script('return $(".ext-mb-content").text()'))
            log.info('%s' % upload_response)

        except Exception as e:
            log.error('Unable to add device to group.', e)

        return add_group_status

class Domains(AdminNavigation):

    def __init__(self, driver, *arg):
        self.arg = arg
        self.driver = driver
        self.driver_utils = DriverUtils(driver)
    
    def create_domain(self, **kwargs):
        driver = self.driver
        driver_utils = self.driver_utils

        try:
            self.nav_sub_menu('domains')
            domain_created = False
            domain_name = kwargs.get('name')
            domain_desc = kwargs.get('desc', 'domain test description')
            domain_hierarchy = kwargs.get('hierarchy', '/root')
            new_user = kwargs.get('new_user', None)
            password = kwargs.get('password', None)
            domain_user = kwargs.get('user', 'root')
            
            assigned_cgr1k = kwargs.get('cgr1k', None)
            assigned_c800 = kwargs.get('c800', None)
            assigned_ir800 = kwargs.get('ir800', None)
            assigned_lorawan = kwargs.get('lorawan', None)
            assigned_ir500 = kwargs.get('ir500', None)
            assigned_endpoint = kwargs.get('endpoint', None)
            assigned_cep = kwargs.get('cep', None)
            assigned_bep = kwargs.get('bep', None)

            log.info(banner('Creating a new Domain: %s.'%(domain_name)))
            log.info('Checking if domain is already exisitng.')
            domain_exisits = driver.execute_script('return $("a:contains(\'%s\')").length == 1'%domain_name)
            if domain_exisits:
                log.error('Domain is already existing')
                return domain_created

            log.info('Clicking on Add Domain Icon.')
            driver.execute_script('return $(".fa-plus")[0]').click()
            time.sleep(2)
            log.info('Entering all the providede values: %s'%kwargs)

            name_input = driver.find_element_by_xpath('//input[contains(@name, "domainName")]')
            desc_input = driver.find_element_by_xpath('//input[contains(@name, "domainDescription")]')
            
            log.info('Entering the Domain Name: %s'%domain_name)
            name_input.clear()
            name_input.send_keys(domain_name)
            time.sleep(1)
            log.info('Entering the Domain Description: %s'%domain_desc)
            desc_input.clear()
            desc_input.send_keys(domain_desc)
            time.sleep(1)

            domain_hierarchy_select = driver.find_element_by_xpath('//select[@name="domainHierarchy"]')
            domain_hierarchy_select.click()
            time.sleep(1)
            log.info('Clicking on the %s option'%domain_hierarchy)
            driver.find_element_by_xpath("//select[@name='domainHierarchy']//option[text()='%s']"%domain_hierarchy).click()
            time.sleep(1)

            if len(list(filter(None.__ne__, [new_user, password]))) == 0:
                log.info('Clicking on "Existing User" radio button.')
                driver.find_element_by_id('existingUser').click()
                time.sleep(1)

                log.info('Clicking on "Existing User" drop down.')
                user_listCombo = driver.find_element_by_xpath('//input[@id="userListCombo"]')
                user_listCombo.click()
                time.sleep(1)
                combo_list_items = driver.find_elements_by_xpath('//div[starts-with(@class, "x-combo-list-item")]')
                for item in combo_list_items:
                    if item.text == domain_user:
                        log.info('Selecting %s user.'%domain_user)
                        item.click()
                        time.sleep(1)
                        break
            elif len(list(filter(None.__ne__, [new_user, password]))) == 2:
                log.info('Clicking on "New User" radio button.')
                driver.find_element_by_id('newUser').click()
                time.sleep(1)
                driver.find_element_by_id('newUser').click()
                time.sleep(1)

                log.info('Entering username.')
                driver.find_element_by_id('userNameLocal').clear()
                driver.find_element_by_id('userNameLocal').send_keys(new_user)
                time.sleep(1)
                log.info('Entering password.')
                driver.find_element_by_id('passwordLocal').clear()
                driver.find_element_by_id('passwordLocal').send_keys(password)
                time.sleep(1)
            else:
                raise Exception('Please provide both username and password for New User.')

            time.sleep(3)
            log.info(banner('Entering assigned device count if provided any.'))
            for idx, assigned_item in enumerate([assigned_cgr1k,
                                            assigned_c800, 
                                            assigned_ir800, 
                                            assigned_lorawan, 
                                            assigned_ir500, 
                                            assigned_endpoint, 
                                            assigned_cep, 
                                            assigned_bep]):
                if assigned_item:
                    time.sleep(1)
                    log.info('Clicking on assigned input')
                    assigned_input = driver.find_elements_by_xpath('//div[contains(@class, "x-grid3-col-deviceAllocation")]')[idx]
                    actionChains = ActionChains(driver)
                    actionChains.double_click(assigned_input).perform()
                    assigned_num = driver.find_element_by_xpath('//input[contains(@class, "x-form-num-field")]')
                    log.info('Clearing the exisitng value.')
                    assigned_num.clear()
                    time.sleep(1)
                    log.info('Entering new value: %d'%assigned_item)
                    assigned_num.send_keys(assigned_item)
                    time.sleep(1)
                    log.info('Sending \\n')
                    assigned_num.send_keys('\n')
                    time.sleep(1)

            log.info('Clicking on the Save button')
            driver.execute_script('return $(".fa-floppy-o")[0]').click()
            driver_utils.wait_for_loading()
            time.sleep(30)
            
            # Assert the domain got created or not
            confirmDlgMsg = driver.find_element_by_xpath("//span[contains(text(),'saved successfully')]").text
            assert "Domain '%s' details saved successfully."%domain_name in confirmDlgMsg
            domain_created = True

            log.info('Clicking on the OK button')
            driver.find_element_by_xpath('//button[contains(text(), "OK")]').click()
            time.sleep(3)

        except AssertionError as ae:
            log.error('Domain success message not seen.\n%s'%ae)
            driver_utils.save_screenshot()
            log.info('Clicking on the OK button')
            driver.find_element_by_xpath('//button[contains(text(), "OK")]').click()
        except Exception as ex:
            log.error('Unexpected error occurred...\n%s'%ex)
            driver_utils.save_screenshot()

        driver.refresh()
        driver_utils.wait_for_loading()
        log.info('Domain - %s created: %s'%(domain_name, domain_created))
        return domain_created

    def delete_domain(self, **kwargs):
        driver = self.driver
        driver_utils = self.driver_utils

        domain_deleted = False
        domain_name = kwargs.get('name', None)
        log.info(banner('Deleting Domain: %s.'%(domain_name)))
        try:
            if domain_name is None:
                log.error('Provide a domain name that needs to be deleted.')
                return domain_deleted
                
            if type(domain_name) is list:
                for name in domain_name:
                    log.info('Clicking on %s checkbox'%name)
                    domain_elem = driver.find_element_by_xpath('//a[contains(@href, "javascript:editDomain") and contains(text(), "%s")]'%name)
                    domain_checkbox = domain_elem.find_element_by_xpath('../../../td//div[@class="x-grid3-row-checker"]')
                    domain_checkbox.click()
            elif type(domain_name) is str:
                log.info('Clicking on %s checkbox'%domain_name)
                domain_elem = driver.find_element_by_xpath('//a[contains(@href, "javascript:editDomain") and contains(text(), "%s")]'%domain_name)
                domain_checkbox = domain_elem.find_element_by_xpath('../../../td//div[@class="x-grid3-row-checker"]')
                domain_checkbox.click()

            log.info('Clicking on Delete button.')
            driver.find_element_by_xpath('//i[@class="fa fa-trash"]').click()

            log.info('Confirming Delete.')
            driver.find_element_by_xpath('//button[contains(text(), "Yes")]').click()
            time.sleep(1)
            update_header = driver.find_element_by_xpath('//span[@class="x-window-header-text"]').text
            log.info('Update Header: %s'%update_header)
            update_status = driver.find_element_by_xpath('//span[@class="ext-mb-text"]').text
            log.info('Update Status: %s'%update_status)

            log.info('Clicking on OK button.')
            driver.find_element_by_xpath('//button[contains(text(), "OK")]').click()
            time.sleep(1)
            domain_deleted = True
        except Exception as e:
            log.error(e)
            driver_utils.save_screenshot()
        
        log.info('Domain - %s deleted: %s'%(domain_name, domain_deleted))
        return domain_deleted

    def delete_domains(self):
        driver = self.driver
        driver_utils = self.driver_utils

        domain_deleted = False
        log.info(banner('Deleting Domains:'))
        try:
            time.sleep(3)
            log.info("Getting domains list for cleanup")
            domains = driver.find_elements_by_xpath('//a[contains(@href, "javascript:editDomain")]')
            print(len(domains))
            time.sleep(2)
            if len(domains) == 1: return "No Domains to be deleted"
            else:
                driver.find_element_by_xpath('//td/div[contains(@class, "x-grid3-hd-inner x-grid3-hd-checker")]').click()
                def check_domain(domainname):
                   domains = driver.find_elements_by_xpath('//a[contains(@href, "javascript:editDomain")]')
                   time.sleep(2)
                   for domain in domains:
                       if domain.text == domainname:
                          domain.find_element_by_xpath('../../preceding-sibling::td/div/div').click()
                          break
                check_domain('root')
                log.info('Clicking on Delete button')
                driver.find_element_by_xpath('//i[@class="fa fa-trash"]').click()

                log.info('Confirming Delete.')
                driver.find_element_by_xpath('//button[contains(text(), "Yes")]').click()
                time.sleep(1)
                update_header = driver.find_element_by_xpath('//span[@class="x-window-header-text"]').text
                log.info('Update Header: %s'%update_header)
                update_status = driver.find_element_by_xpath('//span[@class="ext-mb-text"]').text
                log.info('Update Status: %s'%update_status)

                log.info('Clicking on OK button.')
                driver.find_element_by_xpath('//button[contains(text(), "OK")]').click()
                time.sleep(1)
                domain_deleted = True
        except Exception as e:
            log.error(e)
            driver_utils.save_screenshot()

        return domain_deleted

    def get_domain_details(self, domain_name, **kwargs):
        driver = self.driver
        driver_utils = self.driver_utils
        domain_details = {}

        try:
            log.info('Clickig on the given domain: %s'%domain_name)
            domain_elem = driver.find_element_by_xpath('//a[contains(@href, "javascript:editDomain") and contains(text(), "%s")]'%domain_name)
            domain_elem.click()
            time.sleep(2)

            dev_types = driver.execute_script('function get_dev_types(){\
                                    dev_types=[];\
                                    $.each($(".x-grid3-col-deviceTypeDisplay"), function(i, e){dev_types.push(e.textContent)});\
                                    return dev_types;\
                                }\
                                return get_dev_types();')
            dev_assigned = driver.execute_script('function get_dev_assigned(){\
                                    dev_assigned=[];\
                                    $.each($(".x-grid3-col-deviceAllocation"), function(i, e){dev_assigned.push(e.textContent)});\
                                    return dev_assigned;\
                                }\
                                return get_dev_assigned();')
            dev_used = driver.execute_script('function get_dev_used(){\
                                    dev_used=[];\
                                    $.each($(".x-grid3-col-usedAllocation"), function(i, e){dev_used.push(e.textContent)});\
                                    return dev_used;\
                                }\
                                return get_dev_used();')
            available_counts = driver.execute_script('function get_available_counts(){\
                                    available=[];\
                                    $.each($(".x-grid3-col-availableAllocation"), function(i, e){available.push(e.textContent)});\
                                    return available;\
                                }\
                                return get_available_counts();')

            for idx in range(len(dev_types)):
                dev_data = {}
                dev_data['assigned'] = dev_assigned[idx]
                dev_data['used'] = dev_used[idx]
                dev_data['available'] = available_counts[idx]
                domain_details[dev_types[idx]] = dev_data

        except Exception as e:
            log.error(e)
            driver_utils.save_screenshot()
        
        log.info('domain_details: %s'%json.dumps(domain_details, indent=4, sort_keys=True))
        return domain_details

    def allocate_licenses(self, domain_name, **kwargs):
        driver = self.driver
        driver_utils = self.driver_utils
        licenses_allocated = False
        log.info('\n\nAllocating Licenses for domain: %s with values: %s\n\n'%(domain_name, kwargs))

        dev_dict = {
                'cgr1k': 'CGR1K',
                'c800': 'C800',
                'ir800': 'IR800',
                'lorawan': 'LORAWAN',
                'ir500': 'IR500',
                'endpoint': 'ENDPOINT',
                'cep': 'CELL_ENDPOINT',
                'bep': 'BATTERY_ENDPOINT'
            }

        try:
            log.info('Clickig on the given domain: %s'%domain_name)
            domain_elem = driver.find_element_by_xpath('//a[contains(@href, "javascript:editDomain") and contains(text(), "%s")]'%domain_name)
            domain_elem.click()
            time.sleep(5)

            log.info(banner('Entering assigned device count if provided any.'))
            for key in kwargs.keys():
                assigned_input = dev_dict[key]
                assigned_item = kwargs.get(key)
                log.info('Clicking on assigned input for %s with value: %s.'%(assigned_input, assigned_item))
                assigned_input = driver.execute_script('return $(".x-grid3-col-deviceTypeDisplay:contains(\'%s\')")\
                                                        .parent().siblings("td.x-grid3-td-deviceAllocation")[0]'%assigned_input)
                actionChains = ActionChains(driver)
                actionChains.double_click(assigned_input).perform()
                time.sleep(1)
                assigned_num = driver.find_element_by_xpath('//input[contains(@class, "x-form-num-field")]')
                log.info('Clearing the exisitng value.')
                assigned_num.clear()
                time.sleep(1)
                log.info('Entering new value: %d'%assigned_item)
                assigned_num.send_keys(assigned_item)
                time.sleep(1)
                assigned_num.send_keys('\n')
                time.sleep(1)

            log.info('Clicking on the Save button')
            driver.find_element_by_xpath('//i[@class="fa fa-floppy-o"]').click()
            time.sleep(6)

            popup_header = driver.execute_script('return $(".x-window-header-text").text()')
            popup_message = driver.execute_script('return $(".ext-mb-text").text()')
            confirm_message = driver.find_element_by_xpath("//span[contains(text(),'saved successfully')]").text
            log.info('\npopup_header: %s\npopup_message: %s\n:confirm_message: %s'%
                    (popup_header, popup_message, confirm_message))

            if 'ERROR' in popup_header or \
               "Domain '%s' details saved successfully."%domain_name not in confirm_message:
                raise Exception('Unable to save License allocation.')
            licenses_allocated=True
        except Exception as e:
            log.error(e)
            driver_utils.save_screenshot()
        finally:
            log.info('Clicking on the OK button')
            driver.find_element_by_xpath('//button[contains(text(), "OK")]').click()
            driver_utils.wait_for_loading()
        
        log.info('%s under %s is allocated: %s'%(kwargs, domain_name, licenses_allocated))
        return licenses_allocated

class PasswordPolicy(AdminNavigation):

    def __init__(self, driver, *arg):
        self.arg = arg
        self.driver = driver
        self.driver_utils = DriverUtils(driver)

    def change_policy_value(self, policy_name, policy_vlaue):

        driver = self.driver
        policy_changed = False
        policy_name_dict = {
            'minimum_length':'Password minimum length',
            'history_size': 'Password history size',
            'expire_interval': 'Password expire interval',
            'max_login_attempts': 'Max unsuccessful login attempts'
        }

        policy_div = policy_name_dict[policy_name]

        policy_val_div = driver.find_element_by_xpath('//div[contains(text(), "%s")]/../following-sibling::td/div'%policy_div)
        curr_val = policy_val_div.text
        log.info('curr_val: %s'%str(curr_val))

        if policy_vlaue == curr_val:
            log.info('Cant replace with existing value.')
            return policy_changed

        policy_val_div.click()
        time.sleep(1)

        input_elem = driver.find_element_by_xpath('//input[contains(@class, "x-form-num-field")]')
        input_elem.clear()
        time.sleep(1)
        log.info('Entering new value: %s.'%str(policy_vlaue))
        input_elem.send_keys(policy_vlaue)
        time.sleep(1)
        input_elem.send_keys('\n')
        time.sleep(1)

        log.info('Clicking on Save button.')
        driver.find_element_by_xpath('//i[@class="fa fa-floppy-o"]').click()
        time.sleep(1)
        log.info('Confirming Save.')
        driver.find_element_by_xpath('//button[contains(text(), "Yes")]').click()
        time.sleep(1)
        alert = driver.switch_to.alert
        alert.accept()
        policy_changed = True

        return policy_changed

class RemoteAuthentication(AdminNavigation):

    def __init__(self, driver, *arg):
        self.arg = arg
        self.driver = driver
        self.driver_utils = DriverUtils(driver)

class Roles(AdminNavigation):

    def __init__(self, driver, *arg):
        self.arg = arg
        self.driver = driver
        self.driver_utils = DriverUtils(driver)

    def add_role(self, role_name, **kwargs):

        driver = self.driver
        driver_utils = DriverUtils(driver)
        role_added = False

        try:
            log.info('Checking if a role with this name is existing already.')
            role_len = driver.execute_script('return $(\'a[href*="%s"]\').length;'%role_name)
            if role_len>0: raise Exception('Role with this name already exists.')
            log.info('No role with this name.')

            log.info('Clicking on Add button.')
            driver.execute_script('return $("button:contains(\'Add\'):visible")[0]').click()
            time.sleep(1)

            log.info('Entering role name: %s.'%role_name)
            driver.find_element_by_id('roleName').send_keys(role_name)
            time.sleep(1)

            permission_names=[]
            if len(kwargs) != 0: permission_names = kwargs['permission_names'].split(',')
            if permission_names == []:
                log.info('Clicking on Permission check box.')
                driver.find_element_by_xpath('//div[contains(@class, "x-grid3-hd-checker")]').click()
                time.sleep(1)

                curr_permissions = driver.find_elements_by_xpath('//div[contains(@class, "x-grid3-col-permissionName")]')
                log.info([permission.text for permission in curr_permissions])
            else:
                # permissions = ['Add/Modify/Delete Devices', 'Administrative Operations']
                for permission in permission_names:
                    log.info('Clicking on permission: %s'%permission)
                    checkbox = driver.find_element_by_xpath('//div[contains(text(), "%s")]/../preceding-sibling::td//div[contains(@class, "x-grid3-row-checker")]'%permission)
                    checkbox.click()
                    time.sleep(1)

            log.info('Clicking on Save button.')
            driver.find_element_by_xpath('//i[@class="fa fa-floppy-o"]').click()
            time.sleep(10)

            log.info('Clicking on No button.')
            driver.find_element_by_xpath('//button[contains(text(), "No")]').click()
            time.sleep(3)
            role_added = True
        except Exception as e:
            log.error(e)
            driver_utils.save_screenshot()

        log.info(banner('Given role: %s is added: %s'%(role_name, role_added)))
        return role_added

    def modify_role(self, role_name, **kwargs):
        driver = self.driver
        driver_utils = DriverUtils(driver)
        role_modified = False

        role = driver.find_element_by_xpath('//a[contains(@href, "editRole") and contains(text(), "%s")]'%role_name)
        role.click()
        time.sleep(2)

        permission_names=[]
        if len(kwargs) != 0 and 'permission_names' in kwargs: permission_names = kwargs['permission_names'].split(',')
        for permission in permission_names:
            try:
                log.info('Clicking on checkbox for permission: %s'%permission)
                checkbox = driver.find_element_by_xpath('//div[contains(text(), "%s")]/../preceding-sibling::td//div[contains(@class, "x-grid3-row-checker")]'%permission)
                checkbox.click()
                time.sleep(1)
            except Exception as e:
                log.info(e)
                driver_utils.save_screenshot()

        try:
            log.info('Clicking on Save button.')
            save_btn = driver.find_element_by_id('saveBtn')
            if 'x-item-disabled' in save_btn.get_attribute('class'): raise Exception('Save button should be active')
            save_btn.click()
            time.sleep(1)

            log.info('Clicking on OK button.')
            ok_btn = driver_utils.get_visible_button_by_text('OK')
            if ok_btn: ok_btn.click()
            time.sleep(3)

            role_modified = True
        except Exception as e: log.info('Unable to edit role.\n%s'%e)

        return role_modified

    def delete_role(self, role_name):
        driver = self.driver
        driver_utils = DriverUtils(driver)
        role_deleted = False

        try:
            test_check_box = driver.find_element_by_xpath('//a[contains(@href, "editRole") and contains(text(), "%s")]/../../../td/div/div'%role_name)
            test_check_box.click()
            time.sleep(2)
        except Exception as e:
            log.info(e)
            return role_deleted

        log.info('Clicking on Delete button.')
        driver_utils.get_visible_button_by_text('Delete').click()
        time.sleep(1)
        driver_utils.get_visible_button_by_text('Yes').click()
        time.sleep(1)
        driver_utils.get_visible_button_by_text('OK').click()
        time.sleep(1)
        role_deleted = True

        return role_deleted

    def delete_roles(self):
        driver = self.driver
        driver_utils = DriverUtils(driver)
        role_deleted = False
          
        log.info("Getting roles list for cleanup")
        roles = driver.find_elements_by_xpath('//a[contains(@href, "javascript:editRole")]')
        time.sleep(2)
        if len(roles) == 6: return "No Roles to be deleted"
        else:
           test_check_box = driver.find_element_by_xpath('//td/div[contains(@class, "x-grid3-hd-inner x-grid3-hd-checker")]').click()
           log.info('Clicking on Delete button.')
           driver_utils.get_visible_button_by_text('Delete').click()
           time.sleep(1)
           driver_utils.get_visible_button_by_text('Yes').click()
           time.sleep(1)
           driver_utils.get_visible_button_by_text('OK').click()
           time.sleep(1)
           role_deleted = True

           return role_deleted

    def get_role_permissions(self, role_name):
        driver = self.driver
        permission_names = []

        log.info('Clicking on the Role name: %s'%role_name)
        driver.find_element_by_xpath('//a[contains(@href, "editRole") and contains(text(), "%s")]'%role_name).click()
        time.sleep(2)

        try:
            permission_names = driver.execute_script('function get_permissions(){\
                permissions=[];\
                $.each($(".x-grid3-row-selected .x-grid3-col-permissionName"),\
                    function(i, elem){permissions.push(elem.textContent)}\
                );\
                return permissions;}\
            return get_permissions()')

            time.sleep(2)
            log.info('Clicking on "Cancel" button.')
            driver.find_element_by_xpath('//i[@class="fa fa-close"]').click()
            time.sleep(2)
        except Exception as e: log.error(e)

        return permission_names

class Users(AdminNavigation):

    def __init__(self, driver, *arg):
        self.arg = arg
        self.driver = driver
        self.driver_utils = DriverUtils(driver)

    def add_user(self, username, password, **kwargs):

        driver = self.driver
        driver_utils = self.driver_utils
        user_added = False

        try:
            domain = kwargs.get('domain', 'root')
            role = kwargs.get('role', 'Monitor Only')
            user_exists = driver.execute_script('return $(".x-grid3-col-userName:contains(\'%s\')").length>0?true:false'%username)
            if user_exists:
                raise Exception('User already exists.')
            log.info('\nCreating new user with username: %s, password: %s\n\
                under domain: %s with role: %s'%(username, password, domain, role))

            time.sleep(1)
            log.info('Clicking on Add button')
            driver.find_element_by_xpath('//i[@class="fa fa-plus"]').click()
            time.sleep(1)
            log.info('Entering User Name. %s'%username)
            driver.find_element_by_xpath('//input[@name="userName"]').send_keys(username)
            time.sleep(1)
            log.info('Entering Password. %s'%password)
            driver.find_element_by_xpath('//input[@name="userPassword"]').send_keys(password)
            time.sleep(1)
            log.info('Confirming Password.')
            driver.find_element_by_xpath('//input[@name="userConfirmPassword"]').send_keys(password)
            time.sleep(1)

            log.info('Clicking on Assign Domain button.')
            driver.find_element_by_xpath('//button[text()="Assign Domain"]').click()
            time.sleep(1)
            driver_utils.wait_until_element_exists(xpath="//span[text()='Domain Assignment']")
            log.info('Clicking on Domains dropdown.')
            driver.find_element_by_id('domainComboBoxSelector').find_element_by_xpath('following-sibling::img').click()
            time.sleep(1)
            action_combo_elements = driver.find_elements_by_xpath('//div[starts-with(@class, "x-combo-list-item")]')
            available_domains = [element.text for element in action_combo_elements if element.is_displayed()]
            log.info('available_domains: %s' % available_domains)

            domain_name = [ele for ele in action_combo_elements if ele.is_displayed() and ele.text == domain]
            domain_name = domain_name[0] if domain_name else None
            if domain_name:
                log.info('Clicking on domain name: "%s"' % domain_name.text)
                domain_name.click()
            else:
                log.error('Select a valid domain.')
                return user_added

            time.sleep(1)
            log.info("role name: "+str(role))
            check_box = driver.find_element_by_xpath('//div[contains(@class, "x-grid3-cell-inner") and contains(text(), "%s")]/../preceding-sibling::td/div/div'%role)
            check_box.click()
            time.sleep(2)
            log.info('Selected "%s" role.' % role)

            log.info('Clicking on Assign button')
            driver.execute_script('$(\'button:contains("Assign")\')[1].click()')
            time.sleep(1)

            assign_error = driver.execute_script('return $(\'span:contains("Error")\').length>0 ? $(".ext-mb-text").text() : ""')
            if assign_error:
                log.info('assign_error: %s'%assign_error)
                driver_utils.save_screenshot()
                log.info('Error while assigning domain. Clicking OK.')
                driver.execute_script('if($(\'span:contains("ERROR")\').length>0){ $(\'button:contains("OK")\').click() }')
                time.sleep(1)
                log.info('Clicking on Cancel button.')
                driver.execute_script('if($(\'button:contains("Cancel")\').length>0){ $(\'button:contains("Cancel")\').click(); }')
                time.sleep(1)
                driver.find_element_by_xpath('//i[@class="fa fa-close"]').click()
                time.sleep(1)
                return user_added

            domain_checkboxes = driver.find_elements_by_xpath('//input[contains(@class,"userDetails-checkbox-defaultDomain")]')
            for domain_checkbox in domain_checkboxes:
                domain_name = domain_checkbox.find_element_by_xpath('../../../td/div').text
                log.info('domain_name: %s'%domain_name)
                if domain_name==domain:domain_checkbox.click()

            log.info('Clicking on Save button.')
            driver.find_element_by_xpath('//i[@class="fa fa-floppy-o"]').click()
            time.sleep(2)

            header = driver.execute_script('return $(".x-window-dlg .x-window-header-text:visible").text()')
            update = driver.execute_script('return $(".x-window-dlg .ext-mb-text:visible").text()')
            if header: log.info('header: %s'%header)
            if update: log.info('update: %s'%update)

            if header.lower()=='error':
                driver_utils.save_screenshot()
                driver.find_element_by_xpath('//button[contains(text(),"OK")]').click()
                time.sleep(1)
                log.info('Clicking on Cancel button.')
                driver.execute_script('if($(\'button:contains("Cancel")\').length>0){ $(\'button:contains("Cancel")\').click(); }')
                time.sleep(1)
                raise Exception('Unable to add user.')
            else:
                driver.find_element_by_xpath('//button[contains(text(),"OK")]').click()
                time.sleep(1)
                user_added = True
        except Exception as e:
            driver_utils.save_screenshot()
            log.error(e)

        log.info('User with username: %s is added: %s'%(username, user_added))
        return user_added

    def edit_user_roles(self, **kwargs):
        role_edited = False
        driver = self.driver
        driver_utils = self.driver_utils

        username = kwargs.get('username', None)
        domain_name = kwargs.get('domain_name', None)
        role_name = kwargs.get('role_name', None)
        try:
            time.sleep(2)
            log.info('Clicking on the given user: %s'%username)
            driver.find_element_by_xpath('//a[contains(@href, "javascript:editUser") \
                                         and contains(text(), "%s")]'%username).click()
            time.sleep(2)
            log.info('Clicking on the "Edit" button.')
            #edit_button = driver.execute_script('return $(".x-grid3-cell-first").filter(function(){\
            #    return $(this).text()==="%s"}).siblings().find(("button"))[0]'%domain_name)
            edit_button = driver.find_element_by_xpath('//button[text()="Edit"]')
            edit_button.click()
            time.sleep(2)

            log.info('Selecting the given role: %s'%role_name)
            role_checkbox = driver.execute_script('return $(".x-grid3-col-1:contains(\'%s\')").\
                                   closest("tr").find(".x-grid3-row-checker")[0]'%role_name)
            # role_checkbox = driver.find_element_by_xpath('//div[contains(@class, "x-grid3-cell-inner") and contains(text(), "Endpoint Operator")]')
            # role_checkbox = driver.find_element_by_xpath('//div[contains(@class, "x-grid3-cell-inner") and contains(text(), "%s")]//../../preceding-sibling::td/div/div' % role_name)
            role_checkbox.click()
            time.sleep(1)

            log.info('Clicking on the "Assign" button.')
            driver.execute_script('$(\'button:contains("Assign")\')[1].click()')
            driver.find_element_by_xpath('//i[@class="fa fa-floppy-o"]').click()
            time.sleep(1)
            driver.find_element_by_xpath('//button[contains(text(),"OK")]').click()
            role_edited = True
        except Exception as e:
            log.error(e)
            driver_utils.save_screenshot()

        log.info('Roles edited for user: %s'%role_edited)
        return role_edited

    def delete_user(self, username):

        driver = self.driver
        driver_utils = self.driver_utils
        user_deleted = False
        log.info('Deleting user: %s'%(username))

        try:
            user_ele=''
            users = driver.find_elements_by_xpath('//div[contains(@class, "x-grid3-col-userName")]/a')

            for user in users:
                if user.text == username:
                    user_ele = user
                    break

            log.info('Selecting given username: %s'%username)
            user_ele.find_element_by_xpath('../../preceding-sibling::td/div/div').click()
            
            log.info('Clicking on Delete button')
            driver.find_element_by_xpath('//i[@class="fa fa-trash"]').click()
            driver_utils.wait_for_loading()
            try: driver.find_element_by_xpath('//button[contains(text(), "Yes")]').click()
            except Exception as e: pass
            driver_utils.wait_for_loading()
            
            header = driver.execute_script('return $(".x-window-dlg .x-window-header-text:visible").text()')
            update = driver.execute_script('return $(".x-window-dlg .ext-mb-text:visible").text()')
            if header: log.info('header: %s'%header)
            if update: log.info('update: %s'%update)

            if header.lower()=='error':
                driver_utils.save_screenshot()
                log.info('Clicking on OK')
                driver.find_element_by_xpath('//button[contains(text(),"OK")]').click()
                raise Exception('Unable to remove user.')
            else:
                log.info('Clicking on OK')
                driver.find_element_by_xpath('//button[contains(text(),"OK")]').click()
                user_deleted = True
        except Exception as e:
            log.error(e)
            driver_utils.save_screenshot()

        log.info('User with username: %s is deleted: %s'%(username, user_deleted))
        return user_deleted

    def delete_users(self):

        driver = self.driver
        driver_utils = self.driver_utils
        user_deleted = False
        log.info('Deleting users:')

        try:
            time.sleep(3)
            log.info("Getting users list for cleanup") 
            users = driver.find_elements_by_xpath('//div[contains(@class, "x-grid3-col-userName")]/a')
            time.sleep(2)
            if len(users) == 2: return "No users to be deleted"
            driver.find_element_by_xpath('//td/div[contains(@class, "x-grid3-hd-inner x-grid3-hd-checker")]').click()
            def check_user(username):
                users = driver.find_elements_by_xpath('//div[contains(@class, "x-grid3-col-userName")]/a')
                time.sleep(2)
                for user in users:
                    if user.text == username:
                       user.find_element_by_xpath('../../preceding-sibling::td/div/div').click()
                       break
            check_user('root')
            check_user('orchestration')
            log.info('Clicking on Delete button')
            driver.find_element_by_xpath('//i[@class="fa fa-trash"]').click()
            driver_utils.wait_for_loading()
            try: driver.find_element_by_xpath('//button[contains(text(), "Yes")]').click()
            except Exception as e: pass
            driver_utils.wait_for_loading()

            header = driver.execute_script('return $(".x-window-dlg .x-window-header-text:visible").text()')
            update = driver.execute_script('return $(".x-window-dlg .ext-mb-text:visible").text()')
            if header: log.info('header: %s'%header)
            if update: log.info('update: %s'%update)

            if header.lower()=='error':
                driver_utils.save_screenshot()
                log.info('Clicking on OK')
                driver.find_element_by_xpath('//button[contains(text(),"OK")]').click()
                raise Exception('Unable to remove user.')
            else:
                log.info('Clicking on OK')
                driver.find_element_by_xpath('//button[contains(text(),"OK")]').click()
                user_deleted = True
        except Exception as e:
            log.error(e)
            driver_utils.save_screenshot()
        return user_deleted

    def disable_user(self, username):

        driver = self.driver
        user_disabled = False
        log.info('Disabling user: %s'%(username))

        try:
            user_ele=''
            users = driver.find_elements_by_xpath('//div[contains(@class, "x-grid3-col-userName")]/a')

            for user in users:
                if user.text == username:
                    user_ele = user
                    break

            log.info('Selecting given username: %s'%username)
            user_ele.find_element_by_xpath('../../preceding-sibling::td/div/div').click()

            log.info('Clicking on Disable button')
            driver.find_element_by_xpath('//i[@class="fa fa-user-o"]').click()
            time.sleep(1)
            driver.find_element_by_xpath('//button[contains(text(),"Yes")]').click()
            time.sleep(1)
            disable_message = driver.find_element_by_xpath('//div[contains(@class, "ext-mb-content")]/span').text
            log.info('disable_message: %s'%disable_message)
            assert disable_message == 'User account(s) successfully disabled.'
            
            driver.find_element_by_xpath('//button[contains(text(),"OK")]').click()
            time.sleep(1)
            user_disabled = True
        except AssertionError as ae: log.error('Invalid message.')
        except Exception as e: log.error(e)

        return user_disabled

    def enable_user(self, username):

        driver = self.driver
        user_enabled = False
        log.info('Enabling user: %s'%(username))

        try:
            user_ele=''
            users = driver.find_elements_by_xpath('//div[contains(@class, "x-grid3-col-userName")]/a')

            for user in users:
                if user.text == username:
                    user_ele = user
                    break

            log.info('Selecting given username: %s'%username)
            user_ele.find_element_by_xpath('../../preceding-sibling::td/div/div').click()

            log.info('Clicking on Enable button')
            driver.find_element_by_xpath('//i[@class="fa fa-user"]').click()
            time.sleep(1)
            driver.find_element_by_xpath('//button[contains(text(),"Yes")]').click()
            time.sleep(1)
            enable_message = driver.find_element_by_xpath('//div[contains(@class, "ext-mb-content")]/span').text
            log.info('enable_message: %s'%enable_message)
            assert enable_message == 'User account(s) successfully enabled.'
            
            driver.find_element_by_xpath('//button[contains(text(),"OK")]').click()
            time.sleep(1)
            user_enabled = True

        except AssertionError as ae: log.error('Invalid message.')
        except Exception as e: log.error(e)

        return user_enabled

    def assign_domain(self, **kwargs):

        driver = self.driver
        driver_utils = self.driver_utils
        domain_assigned = False

        username = kwargs.get('username', None)
        domain = kwargs.get('domain', None)
        role = kwargs.get('role', 'Monitor Only')
        if not domain or not username:
            raise Exception('Provide all the required fields.')

        try:
            log.info('Clicking on the given user.')
            driver.find_element_by_xpath('//a[contains(@href, "javascript:editUser") \
                                         and contains(text(), "%s")]'%username).click()
            time.sleep(2)
            log.info('Clicking on Assign Domain button.')
            driver.find_element_by_xpath('//button[text()="Assign Domain"]').click()
            time.sleep(1)
            driver_utils.wait_until_element_exists(xpath="//span[text()='Domain Assignment']")
            driver.find_element_by_id('domainComboBoxSelector').find_element_by_xpath('following-sibling::img').click()
            time.sleep(1)
            action_combo_elements = driver.find_elements_by_xpath('//div[starts-with(@class, "x-combo-list-item")]')
            available_domains = [element.text for element in action_combo_elements if element.is_displayed()]
            log.info('available_domains: %s' % available_domains)

            domain_name = [ele for ele in action_combo_elements if ele.is_displayed() and ele.text == domain]
            domain_name = domain_name[0] if domain_name else None
            if domain_name:
                log.info('Clicking on domain name: "%s"' % domain_name.text)
                domain_name.click()
            else:
                log.error('Select a valid domain.')
                return domain_assigned

            time.sleep(1)
            log.info("role name: "+str(role))
            check_box = driver.find_element_by_xpath('//div[contains(@class, "x-grid3-cell-inner") and contains(text(), "%s")]/../preceding-sibling::td/div/div'%role)
            check_box.click()
            time.sleep(2)
            log.info('Selected "%s" role.' % role)

            log.info('Clicking on Assign button')
            driver.execute_script('$(\'button:contains("Assign")\')[1].click()')
            time.sleep(1)

            log.info('Saving the changes.')
            driver.execute_script('return $(".fa-floppy-o:visible")[0]').click()
            time.sleep(1)
            driver.execute_script('return $("button:contains(\'OK\')")[0]').click()
            time.sleep(1)
            domain_assigned = True
        except Exception as e:
            log.error(e)

        return domain_assigned

    def change_domain(self, username, domain_name):

        driver = self.driver
        driver_utils = self.driver_utils
        domain_changed = False

        try:
            log.info('Clicking on the given user.')
            driver.find_element_by_xpath('//a[contains(@href, "javascript:editUser") \
                                         and contains(text(), "%s")]'%username).click()
            time.sleep(2)
            log.info('Clicking on the domain checkbox.')
            domain_checkbox = driver.execute_script('return $("div").filter(function(){\
                                return $(this).text()==="%s"})[0].closest("tr").\
                                childNodes[1].childNodes[0].childNodes[0]'%domain_name)
            if domain_checkbox: domain_checkbox.click()
            else: raise Exception('Domain name doesn\'t exist.')

            log.info('Saving the changes.')
            driver.execute_script('return $(".fa-floppy-o:visible")[0]').click()
            time.sleep(1)
            driver.execute_script('return $("button:contains(\'OK\')")[0]').click()
            time.sleep(1)
            domain_changed = True
        except Exception as e:
            log.error(e)

        return domain_changed

    def update_domain_roles(self, username, domain_name, role_name):

        driver = self.driver
        driver_utils = self.driver_utils
        domain_roles_updated = False

        try:
            log.info('Clicking on the given user.')
            driver.find_element_by_xpath('//a[contains(@href, "javascript:editUser") \
                                         and contains(text(), "%s")]'%username).click()
            driver_utils.wait_until_element_exists(xpath='//h1[text()="Edit User"]')
            driver.execute_script('return \
                $(".x-grid3-cell-inner")\
                .filter(function(){return $(this).text() == "%s"})\
                .closest("tr").find(".userDetails-grid-btn-edit")[0]'%domain_name).click()
            driver_utils.wait_until_element_exists(xpath='//span[text()="Domain Assignment"]')
            driver.execute_script('return \
                $(".x-grid3-cell-inner:contains(\'%s\')")\
                .closest("tr")[0].childNodes[0].childNodes[0]'%role_name).click()
            time.sleep(2)
            driver.execute_script('$(\'button:contains("Assign")\')[1].click()')
            driver.find_element_by_xpath('//i[@class="fa fa-floppy-o"]').click()
            time.sleep(1)
            driver.find_element_by_xpath('//button[contains(text(),"OK")]').click()
        except Exception as e:
            log.error(e)
        return domain_roles_updated

class ActiveSessions(AdminNavigation):
    ''' This class defines all the applicable opertaions under "Active Sessions" page. '''

    def __init__(self, driver, *arg):
        self.arg = arg
        self.driver = driver
        self.driver_utils = DriverUtils(driver)

    def refresh(self):
        log.info('ActiveSessions Refresh...')
        driver = self.driver
        self.nav_sub_menu('active_sessions')

        log.info('Clicking on Refresh button.')
        driver.find_element_by_xpath('//button[contains(text(), "Refresh")]').click()
        time.sleep(1)
        log.info('Clicked on Refresh...')

    def logout_users(self, username):
        driver = self.driver
        users_logged_out = False
        self.nav_sub_menu('active_sessions')

        try:
            user_ele=''
            users = driver.find_elements_by_xpath('//div[contains(@class, "x-grid3-col-userName")]/a')

            for user in users:
                if user.text == username:
                    user_ele = user
                    break

            log.info('Selecting given username: %s'%username)
            user_ele.find_element_by_xpath('../../preceding-sibling::td/div/div').click()

            log.info('Clicking on "Logout Users" button.')
            driver.find_element_by_xpath('//button[contains(text(), "Logout Users")]').click()
            time.sleep(1)

            driver.find_element_by_xpath('//button[contains(text(), "Yes")]').click()
            time.sleep(1)

            if username=='root': driver.find_element_by_xpath('//button[contains(text(), "OK")]').click()
            time.sleep(2)
        except Exception as e:
            log.error(e)

        log.info('User: %s users_logged_out: %s'%(username, users_logged_out))
        return users_logged_out
 
    def clear_filter(self):
        log.info('Clearing Filter...')
        driver = self.driver
        self.nav_sub_menu('active_sessions')

        log.info('Clicking on Refresh button.')
        driver.find_element_by_xpath('//button[contains(text(), "Clear Filter")]').click()
        time.sleep(1)
        log.info('Cleared Filter...')

    def sort_columns(self, sort_by):

        driver = self.driver
        log.info('Sorting ActiveSessions by: %s'%sort_by)
        is_sorted = False

        column_ids = {
            'username': 'x-grid3-hd-userName',
            'ip': 'x-grid3-hd-userIpAddr',
            'login': 'x-grid3-hd-loginTime',
            'last_access_time': 'x-grid3-hd-lastAccessTime'
        }

        column_id = column_ids[sort_by]
        driver.find_element_by_xpath('//div[contains(@class,"%s")]'%column_id).click()
        time.sleep(1)
        col_class = driver.find_element_by_xpath('//div[contains(@class,"%s")]/..'%column_id).get_attribute('class')

        try:
            assert 'sort' in col_class
            is_sorted = True
        except AssertionError as ae: log.error('Unable to sort.\n%s'%ae)

        log.info('%s is sortable: %s'%(sort_by, is_sorted))
        return is_sorted

class AuditTrail(AdminNavigation):
    ''' This class defines all the applicable opertaions under "Audit Trail" page. '''

    def __init__(self, driver, *arg):
        self.arg = arg
        self.driver = driver
        self.driver_utils = DriverUtils(driver)

    def get_latest_audittrails(self, offset=0, count=10):
        driver = self.driver
        driver_utils = self.driver_utils
        audittrails = {
            'date': None,
            'user_name': None,
            'ip': None,
            'operations': None,
            'status': None,
            'details': None
        }

        try:
            self.nav_sub_menu('audit_trail')
            log.info(banner('Getting the latest AuditTrails.'))

            data = driver.execute_script('a=[];\
                                        $.each($(".x-grid3-col:visible"),\
                                            function(i,e){a.push(e.textContent)}\
                                        );\
                                        return a;')
            data = data[:7*int(count)]

            time.sleep(2)
            audittrails = {
                'date': data[0::7],
                'domain': data[1::7],
                'user_name': data[2::7],
                'ip': data[3::7],
                'operations': data[4::7],
                'status': data[5::7],
                'details': data[6::7]
            }
        except Exception as e: log.error(e)

        log.info('audittrails: %s'%json.dumps(audittrails, indent=4, sort_keys=True))
        return audittrails

    def verifyAuditTrailForUpdate(self, oper):
        driver = self.driver
        log.info(banner('Getting the latest AuditTrails.'))
        audits = driver.find_elements_by_xpath(
            '//div[@class="x-grid3-body"]/div/table[contains(@class, "x-grid3-row-table")]/tbody/tr')[0:15:2]
        operations = [audit.find_elements_by_xpath('td')[4].find_element_by_xpath('div').text for audit in audits]
        rule_state = operations.index(oper)

        status_arr = [audit.find_elements_by_xpath('td')[5].find_element_by_xpath('div').text for audit in audits]
        status = status_arr[rule_state]
        log.info('operations: %s, status: %s' % (operations, status))
        try:
            assert 'Success' == status
        except AssertionError as ae:
            log.error(ae)

    def verifyAuditTrail(self, oper, **kwargs):
        driver = self.driver
        exp_status = kwargs.get('status', 'Initiated')
        log.info(banner('Getting the latest AuditTrails.'))
        audits = driver.find_elements_by_xpath(
            '//div[@class="x-grid3-body"]/div/table[contains(@class, "x-grid3-row-table")]/tbody/tr')[0:15:2]
        operations = [audit.find_elements_by_xpath('td')[4].find_element_by_xpath('div').text for audit in audits]
        rule_state = operations.index(oper)

        status_arr = [audit.find_elements_by_xpath('td')[5].find_element_by_xpath('div').text for audit in audits]
        status = status_arr[rule_state]
        log.info('operations: %s, status: %s' % (operations, status))
        try:
            if exp_status == status:
                log.info("Audit trail Assertion Pass")
            else:
                log.error("Audit trail  Assertion Failed!")
        except AssertionError as ae:
            self.failed(ae)

    def sort_audits(self, sort_by):

        driver = self.driver
        log.info('Sorting AuditTrails by: %s'%sort_by)
        is_sorted = False

        column_ids = {
            'date': 'x-grid3-hd-generatedAt',
            'username': 'x-grid3-hd-userName',
            'ip': 'x-grid3-hd-ipAddrStr',
            'operation': 'x-grid3-hd-operation',
            'status': 'x-grid3-hd-status'
        }

        time.sleep(1)
        column_id = column_ids[sort_by]
        driver.find_element_by_xpath('//div[contains(@class,"%s")]'%column_id).click()
        time.sleep(1)
        col_class = driver.find_element_by_xpath('//div[contains(@class,"%s")]/..'%column_id).get_attribute('class')

        try:
            assert 'sort' in col_class
            is_sorted = True
        except AssertionError as ae: log.error('Unable to sort.\n%s'%ae)

        return is_sorted

    def filter_audits(self, filter_by, filter_name, *args):

        log.info('Filter AuditTrails by: %s'%filter_by)

        driver = self.driver
        driver_utils = self.driver_utils
        filtered_audits = False

        tab_ids = {
            'date': 'x-grid3-hd-generatedAt',
            'username': 'x-grid3-hd-userName',
            'ip': 'x-grid3-hd-ipAddrStr',
            'operation': 'x-grid3-hd-operation',
            'status': 'x-grid3-hd-status'
        }

        tab_id = tab_ids[filter_by]
        tab_ele = driver.find_element_by_xpath('//div[contains(@class,"%s")]'%tab_id)
        
        try:
            log.info('Hovering on %s'%filter_by)
            hover = ActionChains(driver).move_to_element(tab_ele)
            hover.perform()
            time.sleep(1)

            hd_btns = driver.find_elements_by_xpath('//a[@class="x-grid3-hd-btn"]')
            for btn in hd_btns:
                if btn.is_displayed():
                    log.info('Clicking on Sorting arrow element.')
                    btn.click()
                    time.sleep(1)
                    break

            log.info('Hovering to Filter input.')
            arrow_ele = driver.find_element_by_xpath('//a[contains(@class, "x-menu-item-arrow")]')
            hover = ActionChains(driver).move_to_element(arrow_ele)
            hover.perform()
            time.sleep(1)

            input_ele = driver.find_element_by_xpath('//li/input')
            time.sleep(1)

            input_ele.click()
            time.sleep(2)
            log.info('Entering : %s to filter'%filter_name)
            input_ele.send_keys(filter_name)
            time.sleep(2)
        except Exception as e:
            driver_utils.save_screenshot()
            log.error(e)

        col_id = tab_id.replace('hd', 'col')
        if filter_by=='username':
            col_values = driver.execute_script('function filterVals(){vals=[]; $(".x-grid3-col-userName a").each(function(){vals.push($(this).text())}); return vals;}; return filterVals()')
        else:
            col_values = driver.execute_script('function filterVals(){vals=[]; $(".x-grid3-col-ipAddrStr").each(function(){vals.push($(this).text())}); return vals;}; return filterVals()')

        time.sleep(2)
        col_values = list(set(col_values))
        log.info('\ncol_values: %s, \nfilter_name: %s'%(col_values, filter_name))
        has_filter_name = all([True for val in col_values if filter_name in val])

        try:
            assert has_filter_name==True
            filtered_audits = True
        except AssertionError as ae: log.info('Unable to filter.') 

        return filtered_audits

class Certificates(AdminNavigation):
    ''' This class defines all the applicable opertaions under "Audit Trail" page. '''

    def __init__(self, driver, *arg):
        self.arg = arg
        self.driver = driver
        self.driver_utils = DriverUtils(driver)

    def nav_tab(self, tab_name):
        '''
        Method to navigate to a given tab.

        :param tab_name: Name of the tab to navigate.
        :type tab_name: str
        '''
        log.info('Navigating to Certificates Tab - %s'%tab_name)
        driver = self.driver

        #Dictionary of tab id tuples as per the selection.
        tab_ids = {
            'csmp': 'cgmsCertTabs__certForCsmpTab',
            'routers': 'cgmsCertTabs__certForCgdmTab',
            'web': 'cgmsCertTabs__certForWebTab'
        }

        #Determine tab id's depending on the requested tab_name.
        tab_id = tab_ids[tab_name]

        try:
            log.info('Clicking "%s"'% tab_id)
            driver.find_element_by_id('%s'%tab_id).click()
            time.sleep(2)

            #Wait unitl the clicked page is loaded completely.
            selected = ''
            timeout=time.time() + 60*2
            while timeout>time.time():
                log.info('Checking for sub_menu_active_id')
                selected = driver.find_element_by_id('%s'%tab_id).get_attribute('class')
                log.info('selected: %s' % selected)
                if 'x-tab-strip-active' in selected: break
                
                driver.find_element_by_id('%s'%tab_id).click()
                log.info('Waiting for tab to be active.')
                time.sleep(1)

        except (NoSuchElementException, ElementNotVisibleException) as e: log.error('Element not found: %s' % e)
        except Exception as e: log.error(e)

class DataRetention(AdminNavigation):

    def __init__(self, driver, *arg):
        self.arg = arg
        self.driver = driver
        self.driver_utils = DriverUtils(driver)

    def update_data_retention_values(self, data_field, data_value):
        '''
        Updates the values of the DataRetention fields.
        '''

        driver = self.driver
        retention_data_updated = False
        data_field_dict = {
            'event_data' : 'EventPruningJob',
            'endpoint_firmware_data' : 'FirmwarePruningJob',
            'historical_dashboard_data' : 'HistoricalDailyAggrPruningJob',
            'dashboard_data' : 'HistoricalDataPruningJob',
            'closed_issues_data' : 'IssuePruningJob',
            'job_engine_data' : 'JobEnginePruningJob',
            'router_statistics_data' : 'MetricDailyAggrPruningJob',
            'device_network_statistics' : 'MetricPruningJob',
            'service_providers_down_data' : 'SPDownRoutersPruningJob'
        }
        data_field_name = data_field_dict[data_field]

        try:
            curr_value = driver.find_element_by_xpath('//input[@name="%s"]'%data_field_name).get_attribute('value')
            log.info('Current Value: %s' % str(curr_value))
            driver.find_element_by_xpath('//input[@name="EventPruningJob"]').clear()
            log.info('Entering value: %s'%data_value)
            driver.find_element_by_xpath('//input[@name="EventPruningJob"]').send_keys(data_value)
            time.sleep(1)
            log.info('Clicking Save')
            driver.find_element_by_xpath('//i[@class="fa fa-floppy-o"]').click()
            time.sleep(1)
            driver.find_element_by_xpath('//button[contains(text(), "Yes")]').click()
            time.sleep(1)
            update_status = driver.find_element_by_xpath('//span[@class="ext-mb-text"]').text
            log.info('Update Status: %s'%update_status)
            time.sleep(1)
            if update_status != '':
                driver.find_element_by_xpath('//button[contains(text(), "OK")]').click()
                time.sleep(1)
            retention_data_updated = True
        except Exception as e: log.error(e)

        return retention_data_updated

class LicenseCenter(AdminNavigation):

    def __init__(self, driver, *arg):
        self.arg = arg
        self.driver = driver
        self.driver_utils = DriverUtils(driver)

    def nav_tab(self, tab_name):
        '''
        Method to navigate to a given tab.

        :param tab_name: Name of the tab to navigate.
        :type tab_name: str
        '''
        driver = self.driver
        #Dictionary of tab id tuples as per the selection.
        tab_ids = {
            'license_summary': 'licenseTabPanel__licenseSummaryTab',
            'license_files': 'licenseTabPanel__classicLicenseTab',
            'smart_licenses': 'licenseTabPanel__smartLicenseTab'
        }

        #Determine tab id's depending on the requested tab_name.
        tab_id = tab_ids[tab_name]

        try:
            log.info('Clicking "%s"'% tab_id)
            driver.find_element_by_id('%s'%tab_id).click()
            time.sleep(2)

            #Wait unitl the clicked page is loaded completely.
            selected = ''
            timeout=time.time() + 60*2
            while timeout>time.time():
                log.info('Checking for sub_menu_active_id')
                selected = driver.find_element_by_id('%s'%tab_id).get_attribute('class')
                log.info('selected: %s' % selected)
                if 'x-tab-strip-active' in selected: break
                
                driver.find_element_by_id('%s'%tab_id).click()
                log.info('Waiting for tab to be active.')
                time.sleep(1)

        except (NoSuchElementException, ElementNotVisibleException) as e:
            log.info('Element not found: %s' % e)
        except Exception as e: log.info(e)

    def sort_licenses(self, sort_by, *args):

        log.info('Sorting Licenses by: %s'%sort_by)
        driver = self.driver
        driver_utils = self.driver_utils
        lic_sorted = False

        try:
            tab_ids = {
                'package_name': 'x-grid3-hd-1'
            }

            tab_id = tab_ids[sort_by]
            tab = driver.find_element_by_xpath('//div[contains(@class,"%s")]/..'%tab_id)
            curr_sort = tab.get_attribute('class')

            if 'sort-asc' in curr_sort: curr_sort_order = 'Ascending Order'
            elif 'sort-desc' in curr_sort: curr_sort_order = 'Descending Order'
            log.info('curr_sort: %s'%curr_sort_order)

            driver.refresh()
            driver_utils.wait_for_loading()

            tab = driver.find_element_by_xpath('//div[contains(@class,"%s")]/..'%tab_id)
            tab.click()

            after_sort = tab.get_attribute('class')
            if 'sort-asc' in after_sort: after_sort_order = 'Ascending Order'
            elif 'sort-desc' in after_sort: after_sort_order = 'Descending Order'
            log.info('after_sort: %s'%curr_sort_order)
            
            assert curr_sort!=after_sort
            lic_sorted = True
        except AssertionError as ae: log.error('Unable to sort.')
        except Exception as e: log.error(e)
    
        return lic_sorted

    def add_license(self, lic_file_path):
        
        driver = self.driver
        driver_utils = self.driver_utils
        file_uploaded = False
        
        try:
            log.info(banner('Adding License %s'%lic_file_path))
            log.info('Navigating to "License Center".')
            self.nav_sub_menu('license_center')
            log.info('Navigating to "License Files" tab.')
            self.nav_tab('license_files')
            log.info('Clicking on the Add button.')
            driver.find_element_by_xpath('//button[contains(text(), "Add")]').click()
            time.sleep(2)
            file_input = driver.find_element_by_xpath('//input[@id="formchfilefile"]')
            file_input.send_keys(lic_file_path)
            log.info('Clicking on "Upload" button.')
            driver.find_element_by_xpath('//button[contains(text(), "Upload")]').click()
            time.sleep(5)

            popup_header = driver.execute_script('return $(".x-window-header-text").text()')
            popup_message = driver.execute_script('return $(".ext-mb-text").text()')
            log.info('\npopup_header: %s\npopup_message: %s'%(popup_header, popup_message))
            if 'ERROR' in popup_header:
                driver_utils.save_screenshot()
                log.error('Unable to upload license file.')

            log.info('Clicking on "OK" button.')
            driver.find_element_by_xpath('//button[contains(text(), "OK")]').click()

            upload_response = str(driver.execute_script('return $(".ext-mb-content").text()'))
            if upload_response=='File successfully uploaded.': file_uploaded = True
            else: raise Exception('Unable to upload license file.')
            time.sleep(1)
        except Exception as e:
            driver_utils.save_screenshot()
            driver.refresh()

        return file_uploaded

    def delete_license(self, lic_file_name):
        
        driver = self.driver
        driver_utils = self.driver_utils
        file_deleted = False
        
        try:
            log.info(banner('Deleting the given license file'))
            log.info('Navigating to "License Center".')
            self.nav_sub_menu('license_center')
            log.info('Navigating to "License Files" tab.')
            self.nav_tab('license_files')
            time.sleep(1)

            log.info('Selecting %s file.'%lic_file_name)
            driver.find_element_by_xpath('//div[contains(text(), "%s")]/../../td//div[@class="x-grid3-row-checker"]'%lic_file_name).click()

            log.info('Clicking on the Delete button.')
            driver.find_element_by_xpath('//button[contains(text(), "Delete")]').click()
            time.sleep(2)
            try:
                log.info('Confirming the Delete.')
                driver.find_element_by_xpath('//button[contains(text(), "Yes")]').click()
                time.sleep(2)
                driver.find_element_by_xpath('//button[contains(text(), "Yes")]').click()
                time.sleep(10)
            except Exception as e: pass
            finally:
                driver.find_element_by_xpath('//button[contains(text(), "OK")]').click()
                time.sleep(1)
            file_deleted = True
        except Exception as e:
            driver_utils.save_screenshot()

        return file_deleted

    def delete_all_licenses(self):
        
        driver = self.driver
        driver_utils = self.driver_utils
        licenses_deleted = False

        try:
            log.info(banner('Deleting all the exisitng licenses.'))
            log.info('Navigating to "License Center".')
            self.nav_sub_menu('license_center')
            log.info('Navigating to "License Files" tab.')
            self.nav_tab('license_files')
            time.sleep(1)

            licenses_total = int(driver.execute_script('return $(".x-grid3-row-checker").length'))
            if licenses_total==0:
                log.info('No licenses available on the FND.')
                return licenses_deleted

            log.info('Clicking on check box for all license files.')
            driver.find_element_by_xpath('//tr[@class="x-grid3-hd-row"]/.//div[@class="x-grid3-hd-checker"]').click()
            time.sleep(1)

            log.info('Clicking on the Delete button.')
            driver.find_element_by_xpath('//button[contains(text(), "Delete")]').click()
            time.sleep(2)
            try:
                log.info('Confirming the Delete.')
                driver.find_element_by_xpath('//button[contains(text(), "Yes")]').click()
                time.sleep(2)
                log.info('Clicking on Yes.')
                driver.find_element_by_xpath('//button[contains(text(), "Yes")]').click()
                driver_utils.wait_for_loading()
                time.sleep(2)
            except Exception as e: pass
            finally:
                log.info('Clicking on "OK"')
                driver.find_element_by_xpath('//button[contains(text(), "OK")]').click()
                time.sleep(1)

            if driver.execute_script('return $(".x-grid-empty").text()'): licenses_deleted = True
        except Exception as e:
            driver_utils.save_screenshot()

        return licenses_deleted

    def license_summary(self):
        driver = self.driver
        driver_utils = self.driver_utils
        license_summary = {}

        try:
            package_name = driver.execute_script('\
                                function a(){\
                                    a=[];\
                                    $.each($(".x-grid3-hd-row").find(".x-grid3-hd-inner"),\
                                        function(i,e){ a.push(e.textContent)});\
                                    return a;\
                                }\
                            return a();\
                        ')
            dev_lic_info = driver.execute_script('\
                                function a(){\
                                    a=[];\
                                    $.each($(".x-grid3-row-table").find(".x-grid3-col-1:contains(\'DEVICE_LICENSE\')")\
                                    .closest(".x-grid3-row-table").find(".x-grid3-cell"),\
                                        function(i,e){ a.push(e.textContent)});\
                                    return a;\
                                }\
                            return a();\
                        ')

            package_name = package_name[2:-1]
            dev_lic_info = dev_lic_info[2:-1]

            for idx, header in enumerate(package_name):
                license_summary[header.split(' ')[0]]=dev_lic_info[idx]

        except Exception as e:
            log.error(e)
            driver_utils.save_screenshot()

        log.info('license_summary: %s'%json.dumps(license_summary, indent=4, sort_keys=True))
        return license_summary

class Logging(AdminNavigation):
    ''' This class defines all the applicable opertaions under "Logging" page. '''

    def __init__(self, driver, *arg):
        self.arg = arg
        self.driver = driver
        self.driver_utils = DriverUtils(driver)

    def nav_tab(self, tab_name):
        '''
        Method to navigate to a given tab.

        :param tab_name: Name of the tab to navigate.
        :type tab_name: str
        '''
        log.info('Navigating to Certificates Tab - %s'%tab_name)
        driver = self.driver

        #Dictionary of tab id tuples as per the selection.
        tab_ids = {
            'download_logs': 'loggingTabPanel__downloadLogsTab',
            'log_level_settings': 'loggingTabPanel__logLevelSettingsTab'
        }

        #Determine tab id's depending on the requested tab_name.
        tab_id = tab_ids[tab_name]

        try:
            log.info('Clicking "%s"'% tab_id)
            driver.find_element_by_id('%s'%tab_id).click()
            time.sleep(2)

            #Wait unitl the clicked page is loaded completely.
            selected = ''
            timeout=time.time() + 60*2
            while timeout>time.time():
                log.info('Checking for sub_menu_active_id')
                selected = driver.find_element_by_id('%s'%tab_id).get_attribute('class')
                log.info('selected: %s' % selected)
                if 'x-tab-strip-active' in selected: break
                
                driver.find_element_by_id('%s'%tab_id).click()
                log.info('Waiting for tab to be active.')
                time.sleep(1)

        except (NoSuchElementException, ElementNotVisibleException) as e: log.error('Element not found: %s' % e)
        except Exception as e: log.error(e)

    def download_logs(self):
        '''
        Method to download logs from FND portal.
        '''

        driver = self.driver
        driver.find_element_by_xpath('//button[contains(text(), "Download Logs")]')
        time.sleep(3)
        driver.refresh()

    def log_level_settings(self, log_level, **categories):
        '''
        logging = ui_common_utils.Logging(driver)
        logging.nav_sub_menu('logging')
        logging.log_level_settings('Debug', category_list=['Metrics'])
        '''
        log.info('Changing "%s" to debug level.'%categories['category_list'])

        driver = self.driver
        driver_utils = self.driver_utils
        log_level_updated = False

        try:
            self.nav_tab('log_level_settings')
            if 'All' in categories['category_list']:
                select_all = driver.execute_script('return $(".x-grid3-hd-checker")[0]')
                select_all.click()
                time.sleep(1)
            else:
                for cat_elem in categories['category_list']:
                    log.info('cat_elem: %s'%cat_elem)
                    category = driver.find_elements_by_xpath('//div[contains(text(), "%s")]/../../td'%cat_elem)[0]
                    category.find_element_by_xpath('div/div').click()
                    time.sleep(1)

            driver.find_element_by_xpath('//input[contains(@id, "logLevelCombo")]//following-sibling::img').click()
            time.sleep(2)
            log_levels =  driver.find_elements_by_class_name('x-combo-list-item')

            for log_level_ele in log_levels:
                log.info(log_level_ele.get_attribute('innerHTML'))
                time.sleep(2)
                if log_level_ele.get_attribute('innerHTML') == log_level:
                    log.info('Clicking on "%s"'%log_level)
                    log_level_ele.click()
                    break

            driver.find_element_by_xpath('//button[contains(text(),"Go")]').click()
            time.sleep(1)
            driver.find_element_by_xpath('//button[contains(text(), "Yes")]').click()
            time.sleep(1)
            log_level_updated = True
        except Exception as e:
            log.error(e)
            driver_utils.save_screenshot()
        
        log.info('Log Level Settings for the Categories: %s are updated with %s Level'%(categories['category_list'], log_level))
        return log_level_updated

    def add_eids_for_debugging(self, eids, **kwargs):
        '''
        Method to add eids in the logging page for debugging.
        :param eids: eids for adding debugging
        :type eids: list
        '''

        driver = self.driver
        eids_added_for_debugging= False

        delimiter = kwargs.get('delimiter', ',')
        clear_existing = kwargs.get('clear_existing', False)
        if isinstance(eids, list): eids = delimiter.join(eids)

        if not clear_existing:
            log.info('Getting the exisitng eid values.')
            current_eids = driver.find_element_by_id('eidListText').get_attribute('value')
            current_eids = delimiter.join(current_eids.split())
            log.info('Forming new content with exisitng eid values.')
            if current_eids != '': eids=eids+','+current_eids

        log.info('Clearing the exisitng eids.')
        driver.find_element_by_id('eidListText').clear()
        log.info('Adding the new eid content - %s.'%eids)
        driver.find_element_by_id('eidListText').send_keys(eids)
        time.sleep(2)
        log.info('Clicking on the "Save" button.')
        driver.find_element_by_xpath('//i[@class="fa fa-floppy-o"]').click()
        time.sleep(1)

        log.info('Clicking on the "Yes" button.')
        driver.find_element_by_xpath('//button[contains(text(), "Yes")]').click()
        time.sleep(1)

        headers_elems = driver.find_elements_by_xpath('//span[contains(@class, "x-window-header-text")]')
        span_text_elems = driver.find_elements_by_xpath('//span[contains(@class, "ext-mb-text")]')
        headers_elems = [elem for elem in headers_elems if elem.is_displayed()]
        span_text_elems = [elem for elem in span_text_elems if elem.is_displayed()]

        header = headers_elems[0] if headers_elems else None
        update = span_text_elems[0] if span_text_elems else None

        if header: log.info('header: %s'%header.text)
        if update: log.info('update: %s'%update.text)

        if header.text.lower()!='error' and header.text.lower()!='failure':
            eids_added_for_debugging = True
        log.info('Clicking on the "OK" button.')
        driver.find_element_by_xpath('//button[contains(text(), "OK")]').click()
        time.sleep(1)

        return eids_added_for_debugging

class ProvisioningSettings(AdminNavigation):

    def __init__(self, driver, *arg):
        self.arg = arg
        self.driver = driver
        self.driver_utils = DriverUtils(driver)

class ServerSettings(AdminNavigation):

    def __init__(self, driver, *arg):
        self.arg = arg
        self.driver = driver
        self.driver_utils = DriverUtils(driver)

    def nav_tab(self, tab_name):
        '''
        Method to navigate to a given tab.

        :param tab_name: Name of the tab to navigate.
        :type tab_name: str
        '''
        driver = self.driver
        driver_utils = self.driver_utils
        #Dictionary of tab id tuples as per the selection.
        tab_ids = {
            'download_logs': 'serverSettingsTabPanel__downloadLogsSettingsTab',
            'web_session': 'serverSettingsTabPanel__webSessionSettingsTab',
            'device_down_times': 'serverSettingsTabPanel__markDownJobSettingsTab',
            'billing_period_settings': 'serverSettingsTabPanel__billingPeriodSettingsTab',
            'rpl_tree_settings': 'serverSettingsTabPanel__rplTreePullingSettingsTab',
            'issue_settings': 'serverSettingsTabPanel__issueSetingsTab',
            'asset_property_settings': 'serverSettingsTabPanel__assetPropertySetingsTab'
        }

        #Determine tab id's depending on the requested tab_name.
        tab_id = tab_ids[tab_name]

        try:
            log.info('Clicking "%s"'% tab_id)
            driver.find_element_by_id('%s'%tab_id).click()
            time.sleep(2)

            #Wait unitl the clicked page is loaded completely.
            selected = ''
            timeout=time.time() + 60*2
            while timeout>time.time():
                log.info('Checking for sub_menu_active_id')
                selected = driver.find_element_by_id('%s'%tab_id).get_attribute('class')
                log.info('selected: %s' % selected)
                if 'x-tab-strip-active' in selected: break

                driver.find_element_by_id('%s'%tab_id).click()
                log.info('Waiting for tab to be active.')
                time.sleep(1)
        except Exception as e:
            log.error(e)
            driver_utils.save_screenshot()

    def change_device_down_timeouts(self, dev_category, down_time):
        '''
        Method to navigate to a given tab.

        :param tab_name: Name of the tab to navigate.
        :type tab_name: str
        '''
        driver = self.driver
        driver_utils = self.driver_utils

        category_dict = {
            'her': 'asrMarkDownAge',
            'router': 'routerMarkDownAge',
            'act': 'actMarkDownAge',
            'bact': 'bactMarkDownAge',
            'cam': 'camMarkDownAge',
            'cep': 'cellNodeMarkDownAge',
            'ir500': 'ir500MarkDownAge',
	    'lgnn': 'lgnnMarkDownAge',
            'lgelectric':'lgelectricMarkDownAge',
            'lgradio':'lgradioMarkDownAge',
            'mesh': 'meshMarkDownAge',
            'lora': 'loraMarkDownAge'
        }
        
        try:
            self.nav_tab('device_down_times')
            time.sleep(1)

            category_input = category_dict[dev_category]
            current_down_time = int(driver.execute_script('return $("input[name=\'%s\']").val()'%category_input))
            log.info('current_down_time: %d'%current_down_time)
            time.sleep(1)
            driver.execute_script('$("input[name=\'%s\']").val("%d")'%(category_input, down_time))
            time.sleep(1)

            log.info('Saving the changes.')
            driver.execute_script('$(".fa-floppy-o:visible").click()')
            time.sleep(2)

            popup_header = driver.execute_script('return $(".x-window-header-text").text()')
            popup_message = driver.execute_script('return $(".ext-mb-text").text()')

            assert 'INFO' in popup_header
            assert 'success' in popup_message
        except AssertionError as ae:
            log.error('Popup was not shown correctly.')
            driver_utils.save_screenshot()
        except Exception as e:
            log.error(e)
            driver_utils.save_screenshot()
        finally:
            driver.find_element_by_xpath('//button[contains(text(), "OK")]').click()
            time.sleep(1)

    def add_asset_properties(self, json_file):
        '''
        Method to add Assert Properties.

        :param json_file: location of json file.
        :type json_file: str
        '''
        driver = self.driver
        driver_utils = self.driver_utils
        asset_properties_added = False
        if not os.path.isfile(json_file):
                raise ValueError('No json file found.')

        try:
            self.nav_tab('asset_property_settings')
            driver.execute_script\
                ('return $("button:contains(\'Upload json File\')")[0]').click()

            file_input = driver.find_element_by_xpath('//input[@id="formchfilefile"]')
            file_input.send_keys(json_file)
            time.sleep(1)

            invalid_icon = driver.execute_script('return \
                $("#x-form-el-form-add-file .x-form-invalid-icon").css("visibility")')
            if invalid_icon=='visible':
                raise Exception('Invalid image.')
            time.sleep(1)

            driver.execute_script\
                ('return $(".x-toolbar-left-row button:contains(\'Upload\')")[0]').click()
            driver_utils.wait_for_loading()
            driver.execute_script\
                ('return $("button:contains(\'OK\')")[0]').click()
            time.sleep(1)
            asset_properties_added = True
        except Exception as e:
            log.error(e)
            driver_utils.save_screenshot()
        
        log.info('Assets file: %s added to FND: %s'%(json_file, asset_properties_added))
        return asset_properties_added
    
    def remove_asset_properties(self, assets=[]):
        '''
        Method to navigate to a given tab.

        :param tab_name: Name of the tab to navigate.
        :type tab_name: str
        '''
        driver = self.driver
        driver_utils = self.driver_utils
        asset_properties_removed = False
        if not assets: return asset_properties_removed

        try:
            self.nav_tab('asset_property_settings')
            for asset in assets:
                asset_checkbox = driver.execute_script('return \
                    $(".x-grid3-col-name").filter(\
                        function(){return $(this).text()==="%s"})\
                        .parent().parent().children()[0]'%asset)
                asset_checkbox.click()
                time.sleep(1)

            time.sleep(1)
            driver.execute_script\
                ('return $("button:contains(\'Delete\')")[0]').click()
            time.sleep(1)
            driver.execute_script\
                ('return $("button:contains(\'Yes\')")[0]').click()
            time.sleep(1)
            status_popup = driver.execute_script('return $(".x-window-header-text").text()')

            driver.execute_script\
                ('return $("button:contains(\'OK\')")[0]').click()
            if status_popup != 'ERROR':
                asset_properties_removed = True
        except Exception as e:
            log.error(e)
            driver_utils.save_screenshot()

        log.info('Assets: %s removed from FND: %s'%(assets, asset_properties_removed))
        return asset_properties_removed
    
    def get_assets(self):
        '''
        Method to navigate to a given tab.

        :param tab_name: Name of the tab to navigate.
        :type tab_name: str
        '''
        driver = self.driver
        driver_utils = self.driver_utils
        assets = []

        try:
            self.nav_tab('asset_property_settings')
            assets = driver.execute_script('a=[]; \
                $.each($(".x-grid3-col-name"), function(i,e){a.push(e.textContent)}); return a;')
            assets = [a for a in assets]
        except Exception as e:
            log.error(e)
            driver_utils.save_screenshot()

        log.info('Available assets: %s'%(assets))
        return assets        

class SyslogSettings(AdminNavigation):

    def __init__(self, driver, *arg):
        self.arg = arg
        self.driver = driver
        self.driver_utils = DriverUtils(driver)
