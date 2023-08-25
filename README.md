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

    ./deploy.py

## Deploy Only To LibrePCB_Base.lplib

    ./deploy.py --apply LibrePCB_Base.lplib

## Deploy To All Libraries

    ./deploy.py --apply

## Upgrade Libraries File Format

To upgrade libraries to a new file format, you need to have Docker installed.
Then run the following command (combined with the flags documented above):

    ./deploy.py --upgrade 1.0.0-rc1

With `1.0.0-rc1` representing the tag of the `librepcb/librepcb-cli` Docker
image to be used for the upgrade.
