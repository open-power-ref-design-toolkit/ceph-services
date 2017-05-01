#!/usr/bin/env bash
#
# Copyright 2016,2017 IBM Corp.
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

# User can override the location of the cluster-genesis project.
export GENESIS_DIR=${GENESIS_DIR:-"/opt/cluster-genesis"}

SCRIPTS_DIR=$(dirname $0)
source $SCRIPTS_DIR/process-args.sh

pushd playbooks >/dev/null 2>&1
DY_INVENTORY_DIR="${GENESIS_DIR}/scripts/python"
ansible-playbook -i ${DY_INVENTORY_DIR}/inventory.py pre-deploy.yml
rc=$?
if [ $rc != 0 ]; then
    echo "playbooks/pre-deploy.yml failed, rc=$rc"
    exit 1
fi
popd >/dev/null 2>&1


echo "Running ceph playbooks"

# Deploy site.yml
cd $CEPH_DIR

run_ansible site.yml
