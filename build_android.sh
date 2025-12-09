#!/bin/bash
export JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
source venv/bin/activate
buildozer android debug
