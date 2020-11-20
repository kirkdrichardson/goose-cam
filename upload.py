#!/usr/bin/python3

import os
import logging
import requests
import json
import sys
from datetime import datetime, timedelta
import config

"""
    A script to upload a passed file to Google Drive:

    Usage:
    >>> python3 upload.py "/home/user/Desktop/my_movie.mp3

"""


# Ensure all config variables are defined
env_vars = [var for var in dir(config) if var.startswith("ENV_")]
env_var_values = [getattr(config, item) for item in env_vars]

if None in env_var_values:
    print("All variables in 'config.py' must be defined!")
    exit(1)

# Ensure at least one cmd line argument is present
if len(sys.argv) > 1:
    print(sys.argv)

    ####################################################
    ####################################################
    #########    GET ACCESS TOKEN    ###################
    ####################################################
    ####################################################

    # Open the file that may contain an access token
    f = open(config.ENV_ACCESS_TOKEN_FILE_PATH, "r")
    contents = f.read()

    access_token = None

    # Extract token and assess expiration date if data present
    if contents is not None and len(contents.split(',')) == 2:
        content_list = contents.split(',')
        expiration_date = datetime.strptime(
            content_list[0], '%Y-%m-%d %H:%M:%S.%f')
        # If the stored access token hasn't expired, use it
        if expiration_date > datetime.now():
            print("Using existing access token...")
            access_token = content_list[1]


    # If we were unable to get a valid access token from the file, get one using the refresh token
    if access_token is None:
        print("Requesting new access token...")

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
        }

        # Define our post body using the info provided in the config
        data = {
            "client_id": config.ENV_CLIENT_ID,
            "client_secret": config.ENV_CLIENT_SECRET,
            "refresh_token": config.ENV_REFRESH_TOKEN,
            "grant_type": "refresh_token"
        }

        # Post to Google Drive oauth for new access token
        try:
            r = requests.post(
                "https://www.googleapis.com/oauth2/v4/token",
                headers=headers,
                data=data
            )
            r.raise_for_status()

            # print(r.content)

            # Set the new access token locally
            access_token = r.json()["access_token"]

            # Define the expiration date for this token
            expires = '{}'.format(datetime.now() + timedelta(minutes=55))

            # Write to file for future use
            wr = open(config.ENV_ACCESS_TOKEN_FILE_PATH, 'w')
            wr.write("{},{}".format(expires, access_token))

        except requests.exceptions.RequestException as e:
            print(e)

    ####################################################
    ####################################################
    #############    Upload Image    ###################
    ####################################################
    ####################################################
    
    headers = {"Authorization": "Bearer {}".format(access_token)}

    # Path to image
    file_path = sys.argv[1]

    file_metadata = {
        "name": file_path.split('/')[-1],
        # The unique folder ID defined by Google - if you create a folder on Google Drive, this ID is the last section of the URL
        "parents": ["1anzGb9kjCKLh_OxF1OGs7MYWObtXCLB3"]
    }

    files = {
        'data': ('metadata', json.dumps(file_metadata), 'application/json; charset=UTF-8'),
        'file': open(file_path, "rb"),
    }

    print("uploading image at '{}'...".format(file_path))

    # Configure logger
    logger = logging.getLogger('goose_cam')
    hdlr = logging.FileHandler('/var/tmp/goose_cam.log')
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    hdlr.setFormatter(formatter)
    logger.addHandler(hdlr)
    logger.setLevel(logging.WARNING)

    # Post to Google Drive
    try:
        r = requests.post(
            "https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart",
            headers=headers,
            files=files
        )
        r.raise_for_status()
        # Log the successful post
        logger.info(r)
    except requests.exceptions.RequestException as e:
        logger.error(e)

    print("Image upload successful!")
    print("Removing file...")

    # If we have posted the image successfully, delete it locally
    try:
        os.remove(file_path)
    except:
        logger.error("unable to delete local file at path %s", file_path)

    print("success!")
    # Exit without error
    exit(0)

else:
    print("Invalid arguments: {}".format(sys.argv))
    print("Usage: upload.py '/home/user/my_file.jpg'")
    exit(1)
