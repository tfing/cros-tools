#!/bin/bash

IMAGE_FOLDER=$HOME/cros-images
BOARD_NAME=tomato
FW_IMAGE_NAME=image-$BOARD_NAME.dev.bin
EC_IMAGE_NAME=ec.bin
UPD_FW=0
UPD_EC=0
RM_PROTECT=0
ADD_SSH_KEY=0
REBOOT=0

if [ $# -eq 0 ]; then
	echo "$0 -efps -i <ip> -v <version>"
	echo "   -f: update fw"
	echo "   -e: update ec"
	echo "   -p: remove protection, implied -s"
	echo "   -r: reboot after finish update"
	exit
fi

while getopts "i:v:efprs" flag
do
	#echo [$flag] [$OPTARG]

	if [ "$flag" == "i" ]; then
		IP=$OPTARG
	elif [ "$flag" == "v" ]; then
		VER=$OPTARG
	elif [ "$flag" == "f" ]; then
		UPD_FW=1
	elif [ "$flag" == "e" ]; then
		UPD_EC=1
	elif [ "$flag" == "p" ]; then
		RM_PROTECT=1
	elif [ "$flag" == "r" ]; then
		REBOOT=1
	fi
done

if [ -z $IP ]; then
	echo "missing -p <ip>"
	exit
fi

if [ -z $VER ]; then
	echo "missing -v <version>"
	exit
fi

echo IP $IP
echo UPD_FW $UPD_FW
echo UPD_EC $UPD_EC
echo REBOOT $REBOOT

if [ $RM_PROTECT -eq 1 ]; then
	ssh root@$IP "\
	/usr/share/vboot/bin/make_dev_ssd.sh \
	--remove_rootfs_verification --partitions 2 \
	&& /usr/share/vboot/bin/make_dev_ssd.sh \
	--remove_rootfs_verification --partitions 4 \
	&& reboot"
	
	sleep 20
fi

if [ $UPD_FW -eq 1 ]; then
	FW_PATH=$(find $IMAGE_FOLDER | grep $FW_IMAGE_NAME | grep $VER)
	if [ -z $FW_PATH ]; then
		echo "ERROR: cannot find fw/ec with version [$VER]"
		exit
	fi

	echo $FW_PATH
fi

if [ $UPD_EC -eq 1 ]; then
	EC_PATH=$(find $IMAGE_FOLDER | grep $BOARD_NAME/$EC_IMAGE_NAME | grep $VER)
	if [ -z $EC_PATH ]; then
		echo "ERROR: cannot find fw/ec with version [$VER]"
		exit
	fi

	echo $EC_PATH
fi

if [ ! -z $FW_PATH ] || [ ! -z $EC_PATH ]; then
scp $FW_PATH $EC_PATH root@$IP:/tmp
fi

if [ $UPD_FW -eq 1 ]; then
ssh root@$IP "flashrom -p host -w /tmp/$FW_IMAGE_NAME"
fi

if [ $UPD_EC -eq 1 ]; then
ssh root@$IP "flashrom -p ec -w /tmp/$EC_IMAGE_NAME"
fi

if [ $REBOOT -eq 1 ]; then
ssh root@$IP reboot
fi
