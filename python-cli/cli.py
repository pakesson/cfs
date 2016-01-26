#!/usr/bin/env python

import requests, urllib
import base64
import os, time, getpass

import hashlib
import nacl.secret
import nacl.utils

import argparse

BASE_URL = 'http://localhost:5000'
#BASE_URL = 'https://xxxx.herokuapp.com/'

from utils import query_yes_no

def upload(filename, password):
    data = args.file.read()

    password = hashlib.sha256(password).digest()
    box = nacl.secret.SecretBox(password)

    nonce = nacl.utils.random(nacl.secret.SecretBox.NONCE_SIZE)
    encrypted_filename = box.encrypt(filename, nonce)

    nonce = nacl.utils.random(nacl.secret.SecretBox.NONCE_SIZE)
    encrypted_data = box.encrypt(data, nonce)

    r = requests.get('{baseurl}/api/upload?filename={filename}'.format(baseurl=BASE_URL, filename=urllib.quote_plus(base64.b64encode(encrypted_filename))))
    json_data = r.json()

    url = json_data['url']

    headers = {
        'x-amz-acl': 'private',
        'x-amz-meta-filename': base64.b64encode(encrypted_filename),
        #'expires': int(time.time()+60*60),
    }

    r = requests.put(url=url, data=encrypted_data, headers=headers)

    if r.status_code == 200:
        print('File uploaded.')
        print('Download URL: {baseurl}/download/{key}'.format(baseurl=BASE_URL, key=json_data['key']))

def download(key, password):
    r = requests.get('{baseurl}/api/download?key={key}'.format(baseurl=BASE_URL, key=key))

    if r.status_code == 200:
        json_data = r.json()

        url = json_data['url']
        r = requests.get(url)

        metadata = r.headers['x-amz-meta-filename']

        password = hashlib.sha256(password).digest()
        box = nacl.secret.SecretBox(password)

        filename = box.decrypt(base64.b64decode(urllib.unquote_plus(metadata)))

        if query_yes_no("Download the file '{file}'?".format(file=filename)):
            encrypted_data = r.content
            data = box.decrypt(encrypted_data)

            with open(filename, 'wb') as f:
                f.write(data)
    else:
        print("Download failed.")
        print("File saved as '{file}'".format(file=filename))

if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    subparsers = parser.add_subparsers(dest='subparser_name', help='commands')
    upload_parser = subparsers.add_parser('upload', help='Upload a file')
    upload_parser.add_argument('file', action='store', type=argparse.FileType('rb'), help='File to upload')
    download_parser = subparsers.add_parser('download', help='Download a file')
    download_parser.add_argument('key', action='store', help='File to download')

    try:
        args = parser.parse_args()
    except IOError, msg:
        parser.error(str(msg))

    password = getpass.getpass()

    if args.subparser_name == 'upload':
        filename = os.path.basename(args.file.name)
        upload(filename, password)
    elif args.subparser_name == 'download':
        key = args.key
        download(key, password)

