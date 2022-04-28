import os, sys
from ats import topology
from ats.easypy import run

import argparse
import logging
from ats.log.utils import banner
log = logging.getLogger(__name__)
logging.getLogger().setLevel(logging.INFO)

parser = argparse.ArgumentParser(description = "user input")
parser.add_argument("--testbed", type = topology.loader.load, help = "testbed")
parser.add_argument("--testscript", help = "testscript")

def main():

    args = parser.parse_known_args()[0]
    job_path = os.path.dirname(os.path.abspath(__file__))
    log.info("job_path : %s" % job_path)
    
    #Find the base directory where the test scripts exists
    test_path = job_path.replace('jobs', '')
    log.info("test_path : %s" % test_path)
    
    testscript = False
    try: testscript = args.testscript
    except: pass

    testscript_suite = []

    log.info('testscript_suite %s' % testscript_suite)
    #The suite execution starts here if any testscripts are passed as a part of this execution.
    if testscript: testscripts = testscript.split(',')
    #The suite execution starts here if the whole suite needs to be run.
    else: testscripts = testscript_suite
        
    log.info('testscripts: %s'%testscripts)
    for testscript in testscripts:
        log.info('Selected testscript: %s' % testscript)
        log.info(test_path)
        for root, dirs, files in os.walk(test_path):
            for file_name in files:
                if file_name.endswith((testscript+'.py')):
                    testscript = os.path.join(root, file_name)
                    log.info('file_name: %s - %s' % (file_name, testscript))
                    continue_suite = run(testscript=testscript, testbed=args.testbed)
                    log.info(banner('Run result of %s is : %s' % (testscript, continue_suite)))
