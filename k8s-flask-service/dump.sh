#!/bin/bash
# Author: xxliala
# Version: 1.0
# Date: 2025-03-19
# Description: 实用mat 对内存的dump 进行分析，然后将指定目录下的 mat分析的压缩包解压提供浏览器访问
# usage: ./dump.sh <dump文件名>

HEAPDUMP=$1
REPORT_TYPE=$2

CURRENT_DIR=$(pwd)
TODAY=$(date +"%Y%m%d")
DATA_DIR=$CURRENT_DIR/data

OUTPUT_DIR="$DATA_DIR/$TODAY/$HEAPDUMP"

# cp $DATA_DIR/$TODAY/$HEAPDUMP/$HEAPDUMP.hprof $OUTPUT_DIR/
cd $OUTPUT_DIR/

$CURRENT_DIR/mat/ParseHeapDump.sh $OUTPUT_DIR/$HEAPDUMP.hprof org.eclipse.mat.api:overview
rm -rf $OUTPUT_DIR/*.index *.threads
ZIP_FILE=$(ls "$OUTPUT_DIR" | grep "$HEAPDUMP.*\.zip$" | head -n 1)
unzip $OUTPUT_DIR/$ZIP_FILE -d $OUTPUT_DIR/

rm -rf $OUTPUT_DIR/$ZIP_FILE
