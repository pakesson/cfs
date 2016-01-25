import os, io, time
import uuid
import hashlib, base64, hmac
import json, urllib # Import 'urllib.parse' instead for Python 3
from datetime import datetime, timedelta

from flask import Flask, request, redirect, url_for, render_template
from flask import flash, send_file, abort
from werkzeug import secure_filename

from flask_wtf import Form
from flask_wtf.file import FileRequired, FileField
from wtforms import PasswordField
from wtforms.validators import DataRequired

import nacl.secret
import nacl.utils
import boto3
import botocore
from botocore.client import Config

app = Flask(__name__)
app.secret_key = os.environ.get('APP_SECRET', 'default_secret')

AWS_REGION = os.environ.get('AWS_REGION')
AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')
S3_BUCKET = os.environ.get('S3_BUCKET')

TITLE = "CCFCSC - Cloud Crypto File Cloud Storage for the Cloud(tm)"

class UploadForm(Form):
    # TODO: Add a separate hidden field with an upload token?
    password = PasswordField('Password', validators=[DataRequired()])
    file = FileField('File', validators=[FileRequired()])

class DownloadForm(Form):
    # TODO: Add a separate hidden field with a download token?
    password = PasswordField('Password', validators=[DataRequired()])

# A GET request will show landing page with the upload form. A POST request will upload the file.
@app.route('/', methods=("GET", "POST"))
def index():
    form = UploadForm()
    if form.validate_on_submit():
        filename = secure_filename(form.file.data.filename)
        key = str(uuid.uuid4())

        password = hashlib.sha256(form.password.data).digest() # TODO: Replace or wrap. Bcrypt handles a maximum of 72 characters.
        box = nacl.secret.SecretBox(password)

        nonce = nacl.utils.random(nacl.secret.SecretBox.NONCE_SIZE)
        encrypted_filename = box.encrypt(filename, nonce)

        nonce = nacl.utils.random(nacl.secret.SecretBox.NONCE_SIZE)
        encrypted_file = box.encrypt(form.file.data.read(), nonce)

        s3 = boto3.client('s3',
                          aws_access_key_id=AWS_ACCESS_KEY_ID,
                          aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
                          region_name=AWS_REGION)
        s3.put_object(Bucket=S3_BUCKET,
                      Key=key,
                      Body=encrypted_file,
                      ACL='private', # If changed to 'public-read', it's possible to get a direct public URL to the encrypted file
                      Expires=(datetime.utcnow() + timedelta(hours=1)),
                      Metadata={'filename': base64.b64encode(encrypted_filename)})

        flash('{src} uploaded to S3 as {dst}'.format(src=filename, dst=key))
        flash('Download URL: {baseurl}download/{key}'.format(baseurl=request.url_root, key=key))
    return render_template('index.html', form=form, title=TITLE)

@app.route('/download/<key>', methods=("GET", "POST"))
def download(key):
    form = DownloadForm()

    s3 = boto3.client('s3',
                      aws_access_key_id=AWS_ACCESS_KEY_ID,
                      aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
                      region_name=AWS_REGION)
    metadata = None
    try:
        metadata = s3.head_object(Bucket=S3_BUCKET,
                                  Key=key)
    except botocore.exceptions.ClientError as e:
        error_code = int(e.response['Error']['Code'])
        if error_code == 404:
            flash("Object does not exist")
        else:
            raise
    if metadata:
        if form.validate_on_submit():
            password = hashlib.sha256(form.password.data).digest() # TODO: Replace
            box = nacl.secret.SecretBox(password)

            print("B64 filename: %s" % metadata['Metadata']['filename'])

            encrypted_filename = base64.b64decode(metadata['Metadata']['filename'])

            try:
                filename = box.decrypt(encrypted_filename)

                obj = s3.get_object(Bucket=S3_BUCKET,
                                Key=key)
                encrypted_data = obj['Body'].read()
                data = box.decrypt(encrypted_data)

                return send_file(io.BytesIO(data), as_attachment=True, attachment_filename=filename)
            except:
                flash("Incorrect password")
    else:
        flash("Got no metadata")
    return render_template('download.html', form=form, title=TITLE)

""" Return a signed S3 request so that an external client can upload a file
    directly to S3
"""
@app.route('/api/upload')
def api_upload():
    client = boto3.client('s3',
                          aws_access_key_id=AWS_ACCESS_KEY_ID,
                          aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
                          region_name=AWS_REGION,
                          config=Config(signature_version='s3v4'),
                          )

    key = str(uuid.uuid4())

    url = client.generate_presigned_url('put_object',
                                        Params = {
                                          'Bucket': S3_BUCKET,
                                          'Key': key,
                                          'ACL': 'private',
                                          #'Expires': (datetime.utcnow() + timedelta(hours=1)),
                                          'Metadata': {
                                            'filename': request.args.get('filename'),
                                          }
                                        },
                                        ExpiresIn = 3600)

    print("Presigned URL: %s" % url)

    content = json.dumps({
        'url': url,
        'key': key,
    })

    return content

""" Return a signed S3 request so that an external client can fetch
    the file directly from S3
"""
@app.route('/api/download')
def api_download():
    key = request.args.get('key')

    client = boto3.client('s3',
                          aws_access_key_id=AWS_ACCESS_KEY_ID,
                          aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
                          region_name=AWS_REGION)

    metadata = None
    try:
        metadata = client.head_object(Bucket=S3_BUCKET,
                                      Key=key)
    except botocore.exceptions.ClientError as e:
        error_code = int(e.response['Error']['Code'])
        if error_code == 404:
            flash("Object does not exist")
        else:
            raise

    if metadata:
        url = client.generate_presigned_url(
            ClientMethod = "get_object",
            ExpiresIn = 60,
            HttpMethod='GET',
            Params = {
                "Bucket": S3_BUCKET,
                "Key": key,
            })

        content = json.dumps({
            'url': url,
        })

        return content

    abort(401) # TODO: Replace with a more suitable error

@app.route('/test/')
def test():
    key = nacl.utils.random(nacl.secret.SecretBox.KEY_SIZE)
    box = nacl.secret.SecretBox(key)
    message = b"Everything is okay."
    nonce = nacl.utils.random(nacl.secret.SecretBox.NONCE_SIZE)
    encrypted = box.encrypt(message, nonce)
    plaintext = box.decrypt(encrypted)

    return plaintext

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run()
