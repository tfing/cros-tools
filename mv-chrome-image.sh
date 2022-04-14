#!/bin/bash

IMAGE_DIR=$HOME/cros-images
#echo '$1' $1

if [ "$1" == ""  ]; then
	echo ERROR: not specify tar file
	exit
fi

if [ ! -d "$IMAGE_DIR" ]; then
	mkdir $IMAGE_DIR
fi

echo -e ">>> mv $1 to [$IMAGE_DIR]\n"
mv $1 $IMAGE_DIR
cd $IMAGE_DIR

echo -e ">>> extract $1\n"
tar -xv --one-top-level -f $1
ls

echo -e ">>>> remove $1\n"
rm $1
