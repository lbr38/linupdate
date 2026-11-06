#!/usr/bin/env bash
#
# Start a container running systemd as PID 1 (systemd is not running in the CI job
# containers), with the current directory mounted on /src (read only).
#
# Usage: start-systemd-container.sh <image> <container name>

set -e

IMAGE="$1"
NAME="$2"

# Install systemd, then replace the shell by systemd
docker run -d --name "$NAME" --privileged --cgroupns=private -v "${PWD}:/src:ro" "$IMAGE" bash -c '
    if command -v apt-get > /dev/null; then
        apt-get update -y && DEBIAN_FRONTEND=noninteractive apt-get install -y systemd systemd-sysv
    else
        dnf install -y systemd
    fi
    exec /sbin/init'

# Wait for systemd to be started ('degraded' if some units are failing, common in containers)
for _ in $(seq 1 150); do
    state=$(docker exec "$NAME" systemctl is-system-running 2> /dev/null || true)

    if [ "$state" = "running" ] || [ "$state" = "degraded" ]; then
        echo "systemd is ${state} in container ${NAME}"
        exit 0
    fi

    sleep 2
done

docker logs "$NAME" 2>&1 | tail -n 50
echo "systemd did not start in container ${NAME}"
exit 1
