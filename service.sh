#!/bin/sh
#### BEGIN INIT INFO
# From: https://www.topjavablogs.com/news/how-to-make-spring-boot-application-start-when-linux-boots
#       http://www.jcgonzalez.com/linux-java-service-wrapper-example
####
# step 1: sudo vi /etc/init.d/mytestserv
# step 2: modify the SERVICE_NAME, PATH_TO_JAR, and choose a PID_PATH_NAME 
# step 3: sudo chmod +x /etc/init.d/mytestserv
# step 4: sudo service mytestserv start/stop/restart
### END INIT INFO
SERVICE_NAME=eurekaserver
PATH_TO_JAR=/usr/local/eurekaserver/EurekaServer-0.0.1-SNAPSHOT.jar
PID_PATH_NAME=/tmp/eurekaserver-pid
#### END CONFIGURATION
case $1 in
    start)
        echo "Starting $SERVICE_NAME ..."
        if [ ! -f $PID_PATH_NAME ]; then
            nohup java -jar $PATH_TO_JAR /tmp 2>> /dev/null >> /dev/null &
                        echo $! > $PID_PATH_NAME
            echo "$SERVICE_NAME started ..."
        else
            echo "$SERVICE_NAME is already running ..."
        fi
    ;;
    stop)
        if [ -f $PID_PATH_NAME ]; then
            PID=$(cat $PID_PATH_NAME);
            echo "$SERVICE_NAME stoping ..."
            kill $PID;
            echo "$SERVICE_NAME stopped ..."
            rm $PID_PATH_NAME
        else
            echo "$SERVICE_NAME is not running ..."
        fi
    ;;
    restart)
        if [ -f $PID_PATH_NAME ]; then
            PID=$(cat $PID_PATH_NAME);
            echo "$SERVICE_NAME stopping ...";
            kill $PID;
            echo "$SERVICE_NAME stopped ...";
            rm $PID_PATH_NAME
            echo "$SERVICE_NAME starting ..."
            nohup java -jar $PATH_TO_JAR /tmp 2>> /dev/null >> /dev/null &
                        echo $! > $PID_PATH_NAME
            echo "$SERVICE_NAME started ..."
        else
            echo "$SERVICE_NAME is not running ..."
        fi
    ;;
esac 