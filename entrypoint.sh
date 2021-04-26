#! /bin/bash

USER_GID=1000
USER_UID=1000
USER_NAME=appuser

CINCAN_HOME=/home/appuser/.cincan

OWNER_IDS="$(stat -c "%u:%g" "${CINCAN_HOME}")"

# Required for acquiring permissions of mounted volume
if [ "${OWNER_IDS}" != "${USER_UID}:${USER_GID}" ]; then
    if [ "${OWNER_IDS}" == "0:0" ]; then
        chown -R "${USER_UID}":"${USER_GID}" "${CINCAN_HOME}"
    else
        echo "ERROR: CINCAN default '${CINCAN_HOME}' is currently owned by $(stat -c "%U:%G" "${USER_HOME}")"
        exit 1
    fi
fi
# Initialize cron job and start it
echo "Adding cron job from $DB_UPDATE_CRON"
crontab -u appuser "/etc/cron.d/$DB_UPDATE_CRON"
echo "Starting cron..."
cron
# Output cron logs as nonroot user
exec gosu "${USER_NAME}" tail -f /var/log/cron.log
