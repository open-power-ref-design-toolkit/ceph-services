#!/usr/bin/env bash
#
# Copyright 2016 IBM Corp.
#
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

if [ "$1" == "--help" ]; then
    echo "Usage: create-cluster-ceph.sh"
    exit 1
fi

if [ ! -e scripts/bootstrap-ceph.sh ]; then
    echo "This script must be run in the root directory of the project.  ie. /root/os-services/ceph or /root/ceph"
    exit 1
fi
PCLD_DIR=`pwd`

SCRIPTS_DIR=$(dirname $0)
source $SCRIPTS_DIR/process-args.sh

echo "DEPLOY_AIO=$DEPLOY_AIO"
echo "infraNodes=$infraNodes"
echo "storageNodes=$storageNodes"
echo "allNodes=$allNodes"

echo "Running ceph playbooks"

# Deploy site.yml
cd $CEPH_DIR

if [ -r "$GENESIS_INVENTORY" ]; then
    run_ansible site.yml
else
    PUBLIC_SUBNET=$(ip r | grep -o '[0-9]\{1,3\}\.[0-9]\{1,3\}\.[0-9]\{1,3\}\.[0-9]\{1,3\}/[0-9]\{1,2\}' | head -1)

    JSON_VARS="{\"public_subnet\":\"${PUBLIC_SUBNET}\"}"
    echo "JSON_VARS=$JSON_VARS"

    run_ansible -vvv --extra-vars $JSON_VARS site.yml
fi
