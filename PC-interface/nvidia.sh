#!/bin/sh
echo $(#!/bin/sh
 -q -d POWER,TEMPERATURE,MEMORY | grep -A3 'FB Memory Usage\|Temperature\|Power Readings' | awk -F ':' '{print $2}' | awk '{print $1}')
