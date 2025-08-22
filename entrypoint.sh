#!/bin/bash

echo ~~~ Restic explorer
echo ~~~ Revision : $GIT_BRANCH - $GIT_REVISION
echo ~~~ Docker image generated : $DATE

mkdir -p /app/.secrets /app/.cache /app/params /app/setup /app/logs

if [ ! -e '/app/params/params.ini' ]; then
  cp -n /app/setup/params.ini /app/params/
fi

chmod a+x entrypoint.sh

if [ "$DEBUG" == "DEBUG" ]; then
  echo ~~~ Launching DEBUG mode ~~~
  su "$(id -un $UID)" -c "uvicorn main.py:app --reload --port 8000 --host 0.0.0.0 --reload-include='*.py' --reload-include='frontend/*'"
else
  su "$(id -un $UID)" -c "python3 main.py"
fi