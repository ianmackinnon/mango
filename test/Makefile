SHELL := /bin/bash
.PHONY : install-dependencies all test test-js-url-rewrite

all : test

install-dependencies :
	nmp install underscore jsdom


test : test-js-url-rewrite

test-js-url-rewrite :
	nodejs testUrlRewrite.js
