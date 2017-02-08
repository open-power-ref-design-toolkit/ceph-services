ceph-services
=============

This project uses Ceph-Ansible to install and configures a Ceph cluster on a set
of Ubuntu ppc64le servers. These nodes are pre-conditioned by the
cluster-genesis project which orchestrates the overall install and configuration
process.  For more information about running cluster-genesis and deploying
recipes that use ceph-services see:
https://github.com/open-power-ref-design/openstack-recipes

Manual configuration of Ceph-Ansible parameters
----------------------------------------------------

Manual configuration of the parameters used by Ceph-Ansible to create the Ceph
cluster is not required but possible.

The device list for the OSDs and the disk journals can be modified in the config.yml
before cluster-genesis is run.

To modify the two Ceph-Ansible variables that control the Ceph cluster deployment
you modify the all and osd group variable files::

    /opt/ceph-ansible/group_vars/all
    /opt/ceph-ansible/group_vars/osd

Placement group customization
------------------------------

The Ceph cluster will be created with three pools: vms, images, and volumes. The
placement group calculations for these pools are calculated using the PG calc
algorithm from http://ceph.com/pgcalc/.  The PG calc input values used by default are::

    Target PGs per OSD:  100
    OSD count: Disk count from config.yml * number of OSD nodes
    Size: 3
    vms pool % data: 25
    images pool % data: 15
    volumes pool % data: 60

The calculation can be re-run with different parameters before the Ceph cluster creation.
To do this, run the following command after bootstrap-cluster and before create-cluster::

    ./scripts/ulysses_ceph/generate_ceph_ansible_input.py \
       --inventory /var/oprc/inventory.yml --output_directory /opt/ceph-ansible \
       --growth_factor 100 --vms_pool_percent 25 \
       --images_pool_percent 15 --volumes_pool_percent 60

See the usage statement of ./scripts/ulysses_ceph/generate_ceph_ansible_input.py
for more information.

Bug Reporting
-------------
The current list of bugs can be found on launchpad:
https://bugs.launchpad.net/open-power-ref-design

Related projects
----------------

::
    > openstack-recipes
    > cluster-genesis
    > os-services
    > opsmgr
