schedule:
  ceph.heartbeat:
    function: ceph.heartbeat
    seconds: 10
    returner: local
    maxrunning: 1
  iscsi.get_iscsi_data:
    function: iscsi.get_lrbd_data
    seconds: 10
    returner: local
    maxrunning: 1

