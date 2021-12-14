#!/bin/bash

if [ "$#" == "0" ]; then
echo "Usage: $0 <DUT IP>"
	exit
fi

IP=$1

echo '[[[ DUT: $IP ]]]'

echo '>>> add ssh key'
cd /proj/mtk15399/dfd
ssh-keygen -f "/proj/mtk15399/.ssh/known_hosts" -R "$IP"
ssh-copy-id -i ~/.ssh/id_rsa.pub root@$IP

echo '>>> tx dfd file/fw'
scp dump_dfd root@$IP:/usr/bin/
scp dump_dfd.conf root@$IP:/etc/init/
scp image-tomato.dev.bin root@$IP:/tmp

echo '>>> print dfd file/fw path'
ssh root@$IP "sync && ls /usr/bin/dump_dfd* | grep dump_dfd && echo '--' && ls /etc/init/dump_dfd* | grep dump && echo '--' && ls /tmp/image*"

#echo '>>> flash dfd fw'
#ssh root@$IP "flashrom -p host -w /tmp/image-tomato.dev.bin"

echo '>>> reboot'
ssh root@$IP reboot
