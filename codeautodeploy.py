#!/usr/bin/python
# -*- coding: utf-8 -*-
########################################################################
# Name:
# 		codeautodeploy.py  (service auto deploy script)
# Description:
# 		Periodically pull the package from the specific site and update
# Author:
# 		wuwesley
# Python:
#       2.7
# Version:
#		1.0
########################################################################

import os, time, re, logging, ConfigParser, urllib2
import subprocess,shutil,hashlib
import sys,telnetlib
import threading
# the main class for the function
class CodeAutoDeploy(object):
    #==================define the global variables ========================
    def __init__(self):
        # the url of remote package, such as: https://s3.amazonaws.com/wuwesley/flashsales/EurekaServer-0.0.1-SNAPSHOT.jar
        self.mRemotePackageUrl = ''
        # the file that contains the version info of the package. such as: https://s3.amazonaws.com/wuwesley/flashsales/EurekaServer-0.0.1-SNAPSHOT.jar.inof
        self.mRemotePackageVer = ''
        # the configuration file for the tools
        self.mConfFile = 'codeautodeploy.cfg'
        # the log file for the tools
        self.mLogFile = 'codeautodeploy.log'
        # the directory that contains the installed package
        self.mLocalInstallationPath = ''
        # the package name in local environment
        self.mLocalPackageName = ''
        # the host name of the service
        self.mServiceHost = 'localhost'
        # the port of the service
        self.mServicePort= ''
        # the current version of the running package
        self.mCurrentVersion = 0
        # the md5 digest of the new package, use this avoid the duplicated download
        self.mNewPackMD5 = 0
        # the new version no
        self.mNewVersion = 0
        # the global logger object
        self.mLogger = ''
        # the configuration section
        self.mSection = 'codeautodeploy'
        # the name of the service
        self.mServiceName =''
        # the threshold that indicate the service is unhealth
        self.mThreshold =5
        # the thread for the service update
        self.mUpdateServiceThread = None
        # timeout for the update thread , unit is seconds
        self.mThreadTimeout = 600
        # get the current time in seconds
        self.current_seconds_time = lambda: int(round(time.time()))
        # the start time of the thread
        self.mThreadStartTime = self.current_seconds_time()
        # init the config handler
        self.mConfig = ConfigParser.ConfigParser()
        self.mConfig.read(self.mConfFile)
        # start service command
        self.mStartServiceCmd = ''
        # stop service command
        self.mStopServiceCmd = ''
        # set the level of log
        self.mLogLevel = '';

        #===========the variable for the daemon process ==========#


    #==================Function Define =====================================
    # initialize the logger object
    def init_the_logger(self):
        # create logger with log file
        self.mLogger = logging.getLogger(self.mSection)
        self.mLogger.setLevel(logging.INFO)
        mLoggerFileHandler = logging.FileHandler(self.mLogFile)
        mLoggerFileHandler.setLevel(self.mLogLevel)
        # create formatter and add it to the handlers
        mLogFormatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        mLoggerFileHandler.setFormatter(mLogFormatter)
        # add the handlers to the logger
        self.mLogger.addHandler(mLoggerFileHandler)


    # update the value for the specific key
    # **keyv : AutoLogin='False'
    def change_config_by_key(self,section, **keyv):
        [self.mConfig.set(section, key, keyv[key]) for key in keyv if self.mConfig.has_option(section, key)]
        self.mConfig.write(open(self.mConfFile, 'w'))


    # read and update the global variable in memory
    def read_cofig_file_to_memory(self):
        self.mRemotePackageUrl = self.mConfig.get(self.mSection, 'RemotePackageUrl')
        self.mRemotePackageVer = self.mConfig.get(self.mSection, 'RemotePackageVer')
        self.mLocalInstallationPath = self.mConfig.get(self.mSection, 'LocalInstallationPath')
        self.mLocalPackageName = self.mConfig.get(self.mSection, 'LocalPackageName')
        self.mServiceName = self.mConfig.get(self.mSection, 'ServiceName')
        self.mServicePort = self.mConfig.get(self.mSection, 'ServicePort')
        self.mCurrentVersion = self.mConfig.get(self.mSection, 'CurrentVersion')
        self.mNewPackMD5 = self.mConfig.get(self.mSection, 'NewPackMD5')
        self.mStartServiceCmd = self.mConfig.get(self.mSection, 'StartServiceCmd')
        self.mStopServiceCmd = self.mConfig.get(self.mSection, 'StopServiceCmd')
        self.mLogLevel = self.mConfig.get(self.mSection, 'LogLevel')



    # update the version to the config file
    def uptdat_current_verion_value(self):
        if  long(self.mCurrentVersion) != 0 and long(self.mNewVersion) != 0 and long(self.mCurrentVersion) < long(self.mNewVersion):
            self.change_config_by_key(self.mSection, CurrentVersion=self.mNewVersion)
            # update the current version, keep updating
            self.mCurrentVersion = self.mNewVersion
            self.mLogger.info("Updated the CurrentVersion: %s" % self.mCurrentVersion)

    # update md5 value of the new package
    def uptdate_new_package_md5(self):
        self.mNewPackMD5 = str(os.path.getsize(self.mLocalPackageName))
        self.change_config_by_key(self.mSection, newpackmd5=self.mNewPackMD5)
        self.mLogger.info("Updated the MD5 to: %s" % self.mNewPackMD5)

    # get the latest version info from the remote package info url
    def get_latest_package_info(self):
        if self.mRemotePackageVer =='': return False
        # the retry number of the action
        mMaxRetry = 3
        # to avoid the time out error, should use retry loop to fetch the url
        for retryCount in range(mMaxRetry):
            try:
                info_fp = urllib2.urlopen(self.mRemotePackageVer, None, 30)
                break
            except:
                if retryCount < mMaxRetry - 1: continue
                else:
                    self.mLogger.warning("Failed to fetch the new version from:: %s" % self.mRemotePackageVer)
                    return False

        info = info_fp.read()
        if info and len(info) != 0:
            self.mNewVersion = info
            info_fp.close()
            self.mLogger.info("Found the new version: %s" % self.mNewVersion)
            return True
        else:
            info_fp.close()
            return False

    # check the downloaded file, avoid the duplicated download
    def check_file_is_existing(self, mTargetFile):
        # if file does not exists, return false
        if not os.path.isfile(mTargetFile): return False
        # if file does exist, should compare them
        self.mNewPackMD5 = long(self.mConfig.get(self.mSection, 'newpackmd5'))
        if long(os.path.getsize(mTargetFile)) != long(self.mNewPackMD5):
            self.mLogger.info("The file is not existing: %s" % mTargetFile)
            return False
        self.mLogger.info("The file is existing: %s, md5: %s" % (mTargetFile, self.mNewPackMD5))
        return True

    # print the message to console
    def print_progress_bar(self,message):
        sys.stdout.write(message)
        sys.stdout.flush()


    # get the latest package from the remote package  url
    def download_latest_package(self):
        # the retry number of the action
        mMaxRetry = 3
        if self.mLocalPackageName == '': self.mLocalPackageName = self.mRemotePackageUrl.split('/')[-1]
        dest_file = self.mLocalPackageName
        try:
            data_file = urllib2.urlopen(self.mRemotePackageUrl, None, 30)
            data_size = int(dict(data_file.headers).get('content-length'))
        except urllib2.HTTPError, e:
            self.mLogger.warning("Not found package for uri: %s" % self.mRemotePackageUrl)
            return False
        except urllib2.URLError, t:
            self.mLogger.warning("Time out for fetch the uri: %s" % self.mRemotePackageUrl)
            return False

        fp = open(dest_file, 'ab')

        read_unit_size = 1048576  # read at most 1M every time
        read_size = 0
        bar_length = 70  # print 70 '='
        speed_max_length = 11  # for example, 1023.99KB/s

        self.mLogger.info("Package downloading... Length: %s bytes Saving to %s" % (data_size, dest_file))
        start_time = time.time()
        while read_size < data_size:
            # to avoid the time out error, should use retry loop to fetch the url
            for retryCount in range(mMaxRetry):
                try:
                    read_data = data_file.read(read_unit_size)
                    break
                except Exception, e:
                    if retryCount < mMaxRetry - 1:
                        continue
                    else:
                        self.mLogger.warn(
                            "Time out for package downloading... Length: %s bytes of total %s bytes Saving to %s" % (
                            read_size, data_size, dest_file))
                        return False
            fp.write(read_data)
            read_size += len(read_data)
            progress_bar = '=' * int(float(read_size) / data_size * bar_length)

            download_time = int(time.time() - start_time) + 1
            download_percent = int(float(read_size) / data_size * 100)
            blank_bar = " " * (bar_length - len(progress_bar))
            read_size_str = str(read_size)

            download_speed = float(read_size) / download_time
            if download_speed >= 1024 * 1024:
                download_speed = format(download_speed / (1024 * 1024), '.2f') + 'M'  # MB/s
            elif download_speed >= 1024:
                download_speed = format(download_speed / 1024, '.2f') + 'K'  # KB/s
            else:
                download_speed = format(download_speed, '.2f')  # B/s

            speed_blanks = ' ' * (speed_max_length - len(download_speed) - len('B/s'))
            self.print_progress_bar(str(download_percent) + "% [" + progress_bar +
                               ">" + blank_bar + "] " + read_size_str + "  " + speed_blanks +
                               download_speed + "B/s\r")

        self.print_progress_bar("\n")
        # download is incomplete and should return false
        if read_size < data_size:
            self.mLogger.warn("Time out for package downloading... Length: %s bytes of total %s bytes Saving to %s" \
                              % (read_size, data_size, dest_file))
            fp.close()
            data_file.close()
            return False
        # download is success
        self.mLogger.info("Download complete. Length: %s bytes Saving to %s" % (data_size, dest_file))
        fp.close()
        data_file.close()
        # updathe the file size in config file
        self.uptdate_new_package_md5()
        return True

    #  Check whether the given host:port is accessable or not.
    def check_service_status(self):
      t = telnetlib.Telnet()
      try:
        t.open(self.mServiceHost, self.mServicePort)
      except:
        self.mLogger.info("The service: %s may be down!", self.mServiceName)
        return False
      t.close()
      self.mLogger.info("The service: %s is alive!", self.mServiceName)
      return True

    # start and stop the service
    def run_service_cmd(self, command):
          self.mLogger.info('Executing: %s' % command)
          try:
              subprocess.check_call(command, shell=False)
          except subprocess.CalledProcessError:
              self.mLogger.info('Failed to execute: %s' % command)
              pass  # handle errors in the called executable
          except OSError:
              self.mLogger.info('Failed to execute: %s' % command)
              pass  # executable not found
          time.sleep(30)


    # copy the file from src to dest, the dest should be /dir/to/file.jar
    def copyfile_from_src_to_dest(self,src, dest):
        if not os.path.exists(src):
            # Some bad symlink in the src
            self.mLogger.warn('Cannot find file %s ', src)
            return
        if os.path.exists(dest):
            self.mLogger.debug('File %s already exists', dest)
            return
        if not os.path.exists(os.path.dirname(dest)):
            self.mLogger.info('Creating parent directories for %s', os.path.dirname(dest))
            os.makedirs(os.path.dirname(dest))
        self.mLogger.info('Copied file from %s to %s', src, dest)
        shutil.copy2(src, dest)


    # make file executable
    def make_file_executable(self,fn):
        if hasattr(os, 'chmod'):
            oldmode = os.stat(fn).st_mode & 0xFFF # 0o7777
            newmode = (oldmode | 0x16D) & 0xFFF # 0o555, 0o7777
            os.chmod(fn, newmode)
            self.mLogger.info('Changed mode of %s to %s', fn, oct(newmode))

    # update the service
    def update_the_service(self):
        # log the begin of the process
        self.mLogger.info('Update is starting ...')

        # compare the current version and new version
        self.mLogger.info('Compare the version,old: %s  new: %s', self.mCurrentVersion, self.mNewVersion)
        if not self.get_latest_package_info(): return
        if long(self.mCurrentVersion) == 0 or long(self.mNewVersion) == 0 or long(self.mCurrentVersion) == long(self.mNewVersion): return

        # check whether the file is existing or not
        self.mLogger.info('Check the new package: %s', self.mLocalPackageName)
        if not self.check_file_is_existing(self.mLocalPackageName):
            # download the new package
            if not self.download_latest_package(): return

        # stop the service
        self.mLogger.info('Stop the service: %s', self.mStopServiceCmd)
        self.run_service_cmd(self.mStopServiceCmd)


        # copy downloaded file to dest path
        mDest = self.mLocalInstallationPath+'/'+self.mLocalPackageName
        self.mLogger.info('Save file from %s to %s', self.mLocalPackageName, mDest)
        if not self.check_file_is_existing(mDest):
            self.copyfile_from_src_to_dest(self.mLocalPackageName, mDest)

        # make it executable
        self.mLogger.info('Make the file executable: %s', mDest)
        self.make_file_executable(mDest)

        # start the service
        self.mLogger.info('Start the service: %s', self.mStartServiceCmd)
        self.run_service_cmd(self.mStartServiceCmd)

    # keep the service alive
    def keep_the_service_alive(self):
        mUnhealth = 0
        for mCount in range(0,self.mThreshold):
            if not self.check_service_status() : mUnhealth += 1
            else : break
            time.sleep(30)
        if mUnhealth == self.mThreshold:
            self.run_service_cmd(self.mStartServiceCmd)


    # in order to avoid to block the main  event loop, start the update task in another thread
    def start_update_service_thread(self):
        self.mThreadStartTime = self.current_seconds_time()
        self.mUpdateServiceThread = threading.Thread(target=self.update_the_service)
        self.mUpdateServiceThread.daemon = True
        self.mUpdateServiceThread.start()
        self.mLogger.info('Started the App update thread: %s', self.mUpdateServiceThread.getName())

    # define the main logic
    def run(self):

        # read the configuration
        self.read_cofig_file_to_memory()

        # initilize the logger
        self.init_the_logger()

        # log the service start
        self.mLogger.info('Start the code auto deploy service, PID: %s', str(os.getpid()))

        # enter the infinite loop
        while True:
            #  refresh the configuration
            self.read_cofig_file_to_memory()

            # keep the service alive
            self.keep_the_service_alive()

            # check the current running thread of service update
            if self.mUpdateServiceThread:
                if self.mUpdateServiceThread.isAlive():
                    if self.current_seconds_time() - self.mThreadStartTime < self.mThreadTimeout:
                        self.mLogger.info('Thread: %s is alive!', self.mUpdateServiceThread.getName())
                        # hava a sleep
                        time.sleep(5)
                        continue
                    else:
                        self.mLogger.warn('Time out for the App update thread: %s', self.mUpdateServiceThread.getName())
                        self.mUpdateServiceThread.join()

            # run the app update thread
            self.start_update_service_thread()

            # hava a sleep
            time.sleep(20)


# start the code auto deploy tool
codeAutoDeploy = CodeAutoDeploy()
codeAutoDeploy.run()
