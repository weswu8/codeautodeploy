Code Auto Deploy
=====
Periodically pull the package from the specific site and install it and update it.now this tool need the supervisor to manage the service。
自动安装部署工具，从指定的地址下载安装包，进行安装。并且如果有新版本发布，持续进行更新.需要使用supervisor进行服务的管理。
****
Feature
====
## Fetch package from aws s3 and other URL
## Auto insatllation and start the application
## Keep tract the installed version
## Get new version info from remote URL and compare with local record, if there is new one, download and update it

Installation
====
# Install supervisor
## step 1
    sudo easy_install supervisor
    (or) sudo pip install supervisor
    ====
## step 2
    echo_supervisord_conf > /etc/supervisord.conf
    supervisord -c /etc/supervisord.conf
    sudo vi /etc/supervisord.conf,  append below content: where myapp is your appliation name
        -----
        [program:myapp]
        directory=/usr/local/myapp
        command=nohup /usr/java/jdk1.8.0_101/bin/java -jar /usr/local/myapp/myapp.jar
        user=root
        autostart=true
        autorestart=true
        startsecs=10
        startretries=3
        stdout_logfile=/var/log/myapp-stdout.log
        stderr_logfile=/var/log/myapp-stderr.log

        [program:codeautodeploy]
        directory=/usr/local/codeautodeploy
        command=nohup /usr/bin/python /usr/local/codeautodeploy/codeautodeploy.py
        user=root
        autostart=true
        autorestart=true
        startsecs=10
        startretries=3
        stdout_logfile=/var/log/codeautodeploy-stdout.log
        stderr_logfile=/var/log/codeautodeploy-stderr.log
        -----
     supervisorctl reload
    ====
# install code auto deploy
## step 1
    git clone https://github.com/wesley1975/codeautodeploy.git
    sudo chmod a+x codeautodeploy/codeautodeploy.py
    sudo mkdir /usr/local/codeautodeploy
    sudo cp codeautodeploy/codeautodeploy.py /usr/local/codeautodeploy/
    sudo cp codeautodeploy/codeautodeploy.cfg /usr/local/codeautodeploy/
## step 2
    sudo vi /usr/local/codeautodeploy/codeautodeploy.cfg
        ----
        [codeautodeploy]
        currentversion = 0
        newpackmd5 = 0
        localpackagename = EurekaServer-0.0.1-SNAPSHOT.jar
        localinstallationpath = /usr/local/eurekaserver
        remotepackagever = https://s3.amazonaws.com/wuwesley/flashsales/EurekaServer-0.0.1-SNAPSHOT.jar.info
        remotepackageurl = https://s3.amazonaws.com/wuwesley/flashsales/EurekaServer-0.0.1-SNAPSHOT.jar
        servicename = eurekaserver
        serviceport = 8080
        startservicecmd = sudo /usr/local/bin/supervisorctl start eurekaserver
        stopservicecmd = sudo /usr/local/bin/supervisorctl stop eurekaserver
        loglevel = INFO
        ----
    sudo /usr/local/bin/supervisorctl start codeautodeploy
    sudo /usr/local/bin/supervisorctl status codeautodeploy

    sudo tail -n 10 -f /usr/local/codeautodeploy/codeautodeploy.log