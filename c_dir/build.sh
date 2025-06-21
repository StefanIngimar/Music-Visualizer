#!/bin/bash

if [[ "$CC" == "" ]]; then
  CC=gcc
fi

C_FLAGS="$(pkg-config --cflags libavformat libavcodec libavutil)"
LD_FLAGS="$(pkg-config --libs libavformat libavcodec libavutil)"
if [[ "$?" != "0" ]]; then
  echo "pkg-config not working... trying some default flags."
  FLAGS="-lavformat -lavcodec -lavutil"
fi

echo $CC -g "$1.c" -o "$1" -lm $C_FLAGS $LD_FLAGS
$CC -g "$1.c" -o "$1" -lm $C_FLAGS $LD_FLAGS
