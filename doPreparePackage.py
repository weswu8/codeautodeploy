
########################################################################
# Name:
# 		dePreparePackage.py
# Description:
# 		 A aws lambad funtion, it will publish the package from the out put of aws code pipeline
# Author:
# 		wuwesley
# Python:
#       2.7
# Version:
#		1.0
########################################################################
import logging
import boto3
import os
import datetime
from botocore.client import Config
from botocore.exceptions import ClientError

LOGGER = logging.getLogger()
LOGGER.setLevel(logging.INFO)

LOGGER.info("============Loading function============")

s3r = boto3.resource('s3', region_name="us-east-1", config=Config(signature_version='s3v4'))
s3 = boto3.client('s3', region_name="us-east-1", config=Config(signature_version='s3v4'))


def log_event(event):
    """
    Logs event information for debugging
    """
    LOGGER.info("=========================================")
    LOGGER.info(event)
    LOGGER.info("=========================================")


def update_package_time(bucket, key):
    """
    update the creation time of the final package
    """
    key = key + ".info";
    utc_datetime = datetime.datetime.utcnow()
    timestamp = utc_datetime.strftime("%Y%m%d%H%M%S")
    s3r.Bucket(bucket).put_object(Key=key, Body=timestamp)
    try:
        s3r.Bucket(bucket).put_object(Key=key, Body=timestamp)
        s3.put_object_acl(ACL='public-read', Bucket=bucket, Key=key)
        LOGGER.info("The lastest update time:%s", timestamp)
        return True
    except ClientError as err:
        LOGGER.error("Failed to update the creation time of the final package!\n%s", err)
        return False


def codepipeline_success(job_id):
    """
    Puts CodePipeline Success Result
    """
    try:
        codepipeline = boto3.client('codepipeline')
        codepipeline.put_job_success_result(jobId=job_id)
        LOGGER.info("============SUCCESS============")
        return True
    except ClientError as err:
        LOGGER.error("Failed to PutJobSuccessResult for CodePipeline!\n%s", err)
        return False


def codepipeline_failure(job_id, message):
    """
    Puts CodePipeline Failure Result
    """
    try:
        codepipeline = boto3.client('codepipeline')
        codepipeline.put_job_failure_result(
            jobId=job_id,
            failureDetails={'type': 'JobFailed', 'message': message}
        )
        LOGGER.info("============FAILURE============")
        return True
    except ClientError as err:
        LOGGER.error("Failed to PutJobFailureResult for CodePipeline!\n%s", err)
        return False


def checkObjecExist(bucket, key):
    results = s3.list_objects(Bucket=bucket, Prefix=key)
    return 'Contents' in results


def doRenameAndMakepublic(event, context):
    """
    Rename the artifact and make it public
    """
    log_event(event)
    try:
        job_id = event['CodePipeline.job']['id']
    except KeyError as err:
        LOGGER.error("Could not retrieve CodePipeline Job ID!\n%s", err)
        return False

    # Get the object from the event and show its content type
    bucket = event['CodePipeline.job']['data']['inputArtifacts'][0]['location']['s3Location']['bucketName']
    key = event['CodePipeline.job']['data']['inputArtifacts'][0]['location']['s3Location']['objectKey']
    userParams = event["CodePipeline.job"]['data']['actionConfiguration']['configuration']['UserParameters']
    sourcefile = {'Bucket': bucket, 'Key': key}
    LOGGER.info("Input artifact:%s", sourcefile)
    newbucket = "wuwesley"
    newkey = 'flashsales/{0}'.format(userParams)
    LOGGER.info("New Bucket:%s, new key:%s", newbucket, newkey)
    try:
        if (checkObjecExist(bucket, newkey)):
            s3.delete_object(Bucket=bucket, Key=newkey)
            LOGGER.info("Delete existing:%s", newkey)
        s3r.Object(newbucket, newkey).copy_from(CopySource=sourcefile)
        LOGGER.info("Copied from %s to %s", bucket + '/' + key, newbucket + '/' + newkey)
        s3.put_object_acl(ACL='public-read', Bucket=newbucket, Key=newkey)
        LOGGER.info("Changed permission of %s", newkey)
        update_package_time(newbucket, newkey)
        if (codepipeline_success(job_id) == True):
            return True
        else:
            return False
    except (TypeError, KeyError) as err:
        LOGGER.error(err)
        codepipeline_failure(job_id, 'The task of rename and change permission is failed!')
        return False