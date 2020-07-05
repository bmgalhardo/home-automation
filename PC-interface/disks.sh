#!/bin/sh
echo $(df -h | grep /dev/sd | awk '{print $5" "$6}')
