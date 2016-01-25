# Crypto File Storage

Project description. Lorem ipsum dolor sit amet.

With the command-line clients, all crypto operations are performed locally. The
password is never sent to the server.

## Dependencies

 * libsodium
 * Python
 * Everything listed in requirements.txt

## Preparations

Create a new S3 bucket, and new credentials with restricted access.

Add an inline policy for the new user:

```json
    {
      "Statement": [
        {
          "Action": "s3:*",
          "Effect": "Allow",
          "Resource": [
            "arn:aws:s3:::bucket-name",
            "arn:aws:s3:::bucket-name/*"
          ]
        }
      ]
    }
```

Replace `bucket-name` with the name of your bucket.

## Deploying to Heroku

Install [Heroku Toolbelt](https://toolbelt.heroku.com/) and configure the account

TODO: Explain why a custom buildpack is needed

First, create the app with a custom buildpack

```bash
  $ heroku create my_app --buildpack https://github.com/ddollar/heroku-buildpack-multi.git
```

This will also add a new git remote in the local repository

Set environment variables

```bash
  $ heroku config:set AWS_ACCESS_KEY_ID=xxxxxxx AWS_SECRET_ACCESS_KEY=xxxxxxx
  $ heroku config:set AWS_REGION=eu-central-1
  $ heroku config:set S3_BUCKET=xxxxxxx
  $ heroku config:set APP_SECRET=super_secret_random_string
```

Push the code to Heroku

```bash
  $ git push heroku master
```

Make sure that at least one dyno is running

```bash
  $ heroku ps:scale web=1
```

## Testing locally

Create and activate virtualenv

```bash
  $ virtualenv venv
  $ source venv/bin/activate
```

Install the required dependencies

```bash
  $ pip install -r requirements.txt
```

TODO: Set environment variables (same as for Heroku, but use `export KEY=value`)

Host the Flask app locally

```bash
  $ python app.py
   * Running on http://127.0.0.1:5000/ (Press CTRL+C to quit)
```

or, for local Heroku testing,

```bash
  $ heroku local
  forego | starting web.1 on port 5000
  web.1  | [2016-01-25 17:04:42 +0000] [5059] [INFO] Starting gunicorn 19.4.5
  web.1  | [2016-01-25 17:04:42 +0000] [5059] [INFO] Listening at: http://0.0.0.0:5000 (5059)
  web.1  | [2016-01-25 17:04:42 +0000] [5059] [INFO] Using worker: sync
  web.1  | [2016-01-25 17:04:42 +0000] [5064] [INFO] Booting worker with pid: 5064
```

The web interface should now be up and running on (on port 5000 by default).

## Python Command Line Interface

Upload a file:

```bash
  $ python cli.py upload filename.ext
  Password:
  File uploaded.
  Download URL: https://server/download/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
```

The download URL can be opened in a web browser, or the ID can be used directly
with the command line client:

```bash
  $ python cli.py download xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
  Password:
  Download the file 'filename.ext'? [Y/n] y
  File saved as 'filename.ext'
```

## Go Command Line Interface

Works pretty much the same as the Python client (at least the parts that
actually work).
