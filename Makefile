# Root Makefile
SHELL := /bin/zsh
.ONESHELL:
.SHELLFLAGS := -lc

# Include just the common main; it fan-outs to the rest.
include mk/00_main.mk

