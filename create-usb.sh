#!/bin/bash


if [ -z $1 ]; then
	echo "$0 <version>"
	exit
fi

VER=$1
IMAGE_FOLDER=$HOME/cros-images


IMAGE_PATH=$(find $IMAGE_FOLDER | grep chromiumos | grep $1)
if [ -z $IMAGE_PATH ]; then
	echo "ERROR: cannot find image by version [$VER]"
	exit
fi

echo $IMAGE_PATH

$HOME/cros/chromite/bin/cros flash usb:// $IMAGE_PATH
