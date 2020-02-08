# LibrePCB Library Administration Scripts

## Create Virtualenv

    mkvirtualenv -p `which python3` librepcb-libraries-admin

## Install Requirements

    pip install -r requirements.txt

## Create Configuration

Create a file `options.json` with following content:

```json
{
  "--token": "<GitHub API Token>"
}
```

## Test Deployment

    python deploy.py

## Deploy To LibrePCB_Base.lplib

    python deploy.py --single --apply

## Deploy To All Libraries

    python deploy.py --apply
