Ceph
=============

This project installs and configures a ceph cluster on a set of bare metal Ubuntu
ppc64le servers that will be integrated into an OpenStack cluster.  These nodes are
pre-conditioned by the cluster-genesis project which orchestrates the overall
install and configuration process.

The following scripts are invoked by cluster-genesis::

    > ./scripts/bootstrap-ceph.sh
    > ./scripts/create-cluster-ceph.sh

The script bootstrap-ceph.sh installs the tools, chiefly Ceph-ansible, that will be
used to create the storage cluster.  The cluster is actually installed and configured
by the script create-cluster-ceph.sh.

The key point to remember here when multiple projects are being invoked is that all
of the bootstrap scripts are invoked before any of the create-cluster scripts are
invoked.  Beyond that, the use of separate bootstrap and create-cluster scripts is
intended to provide a control point whereby advanced users may customize settings
on a per project basis as one size does not fit all users.

To this end, meta data is generated and placed within the project (./etc) in the
bootstrap phase before it is activated in the create-cluster phase where it is
copied to the prescribed location of the actual install tool.  Note there is no
requirement to modify any meta data.

The scripts above may be invoked manually to resolve errors, particularly network
related errors.

Related projects::

    > cluster-genesis
    > os-services
    > opsmgr

For additional information, see::

    >
