import os
import subprocess
import json

#This module contains functions which can be used to fetch ISCSI data from the ceph cluster
#ISCSI data could be fetched either using lrbd's lrbd.conf object or using targetcli.

# Note: do not import ceph modules at this scope, otherwise this module won't be able
# to cleanly talk to us about systems where ceph isn't installed yet.

RADOS_NAME = 'client.admin'
CLUSTER_NAME = 'ceph'
CONF_FILE = '/etc/ceph/ceph.conf'



def get_lrbdconf_data(name=RADOS_NAME, clustername=CLUSTER_NAME, conffile=CONF_FILE):
    """
    connect to the ceph cluster on the localhost using librados and iterate through all the
    pools. In each pool look for the object 'lrbd.conf' and fetch the values of it's xattrs.
    If no rados module is present, we can safely assume that ceph is not installed on this
    node. If there is an error in cluster.connect(), then we do have ceph installed but this
    node does not have client.admin key. A rados.ObjectNotFound error would mean that the
    pool in question does not have the 'lrbd.conf' object and hence it does not have an ISCSI
    deployed on any of it's RBD images.return_dict dictionary will be returned.
    """
    return_dict = {}
    try:
        import rados
    except ImportError:
        return_dict['error'] = True
        return_dict['status'] = "ceph is not installed on this node"
        return return_dict
   
    try:
        cluster_handle = rados.Rados(name=name, clustername=clustername, conffile=conffile)
        cluster_handle.connect()
    except (rados.Error):
        return_dict['error'] = True
        return_dict['status'] = "no client.admin key on this node"
        return return_dict

    pools = cluster_handle.list_pools()
    for pool in pools:
        pool_ctx = cluster_handle.open_ioctx(pool)
        #return_dict[pool]
        try:
            lrbd_attrs = pool_ctx.get_xattrs('lrbd.conf')
            return_dict[pool] = list(lrbd_attrs)
        except (rados.ObjectNotFound):
            return_dict[pool] = "No lrbd configured ISCSI target found for this pool"
            pool_ctx.close()
            continue
        finally:
            pool_ctx.close()

    cluster_handle.shutdown() 
    return return_dict
        


def get_lrbd_data():
    """
    On a node which has lrbd installed get the iscsi data for the entire cluster using
    'lrbd -o' command. Output till be a python dictionary. This will only work for nodes
    which have lrbd installed.
    :return: dictionary
    """
    lrbd_path = '/usr/sbin/lrbd'
    if not os.path.exists(lrbd_path):
        return {'status':'this node does not have lrbd installed'}

    args = ['sudo', 'lrbd' ,'-o']
    p = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = p.communicate()
    if stderr != '':
        return {'status':'lrbd -o error %s' % stderr.strip()}
    output = json.loads(stdout)

    return output


def get_rtslib_data():
    """
    On cluster nodes where targetcli/rtslib is installed, this function can be used to
    gather the ISCSI data
    :return: dictionary
    """

    return_dict = {}
    try:
        from rtslib import FabricModule, Target, TPG
    except ImportError:
        return_dict['error'] = True
        return_dict['status'] = "python-rtslib is not installed on this node"
        return return_dict
    iscsi = FabricModule("iscsi")

    if len(list(iscsi.targets)) == 0:
        return {'status':'this node has no iscsi targets configured'}

    return_dict['targets'] = []
    for i in range(len(list(iscsi.targets))):
        return_dict['targets'].insert(i, {})
        return_dict['targets'][i]['targetname'] = list(iscsi.targets)[i].wwn
        return_dict['targets'][i]['tpgs'] = []
        for t in range(len(list(list(iscsi.targets)[i].tpgs))):
            return_dict['targets'][i]['tpgs'].insert(t, {})
            return_dict['targets'][i]['tpgs'][t]['tag'] = list(list(iscsi.targets)[i].tpgs)[t].tag
            return_dict['targets'][i]['tpgs'][t]['enable'] = list(list(iscsi.targets)[i].tpgs)[t].enable
            acls = []
            for acl in list(list(list(iscsi.targets)[i].tpgs)[t].node_acls):
                acls.append(acl.node_wwn)
            return_dict['targets'][i]['tpgs'][t]['acl'] = acls
            nw_portals = []
            for nw in list(list(list(iscsi.targets)[i].tpgs)[t].network_portals):
                nw_portals.append(nw.ip_address)
            return_dict['targets'][i]['tpgs'][t]['network_portals'] = nw_portals
            luns = []
            for lun in list(list(list(iscsi.targets)[i].tpgs)[t].luns):
                luns.append(lun.storage_object.udev_path)
            return_dict['targets'][i]['tpgs'][t]['luns'] = luns

    return return_dict







