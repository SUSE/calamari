__author__ = 'kapil'
import datetime
from pytz import utc
from cthulhu.log import log
from calamari_common.salt_wrapper import condition_kwarg, LocalClient, SaltEventSource
from cthulhu.manager import config, salt_config
from cluster_monitor import ClusterMonitor
from cthulhu.gevent_util import nosleep, nosleep_mgr
from calamari_common.types import SYNC_OBJECT_TYPES




class ISCSIMonitor(ClusterMonitor):
    """
    Monitoring of ISCSI data of the ceph cluster from the
    ceph/cluster/{0}/iscsi'.format(fsid) event tag
    """
    def _run(self):
        self._plugin_monitor.start()

        self._ready.set()
        log.debug("ISCSIMonitor._run: ready")

        event = SaltEventSource(log, salt_config)

        while not self._complete.is_set():
            # No salt tag filtering: https://github.com/saltstack/salt/issues/11582
            ev = event.get_event(full=True)

            if ev is not None:
                data = ev['data']
                tag = ev['tag']
                log.debug("_run.ev: %s/tag=%s" % (data['id'] if 'id' in data else None, tag))

                # I am interested in the following tags:
                # - ceph/cluster/<fsid>/iscsi where fsid is my fsid

                try:
                    if tag.startswith("ceph/cluster/{0}/iscsi".format(self.fsid)):
                        # A iscsi_data beacon
                        self.on_heartbeat(data['id'], data['data'])
                except:
                    # Because this is our main event handling loop, swallow exceptions
                    # instead of letting them end the world.
                    log.exception("Exception handling message with tag %s" % tag)
                    log.debug("Message content: %s" % data)
        log.info("%s complete" % self.__class__.__name__)
        self._plugin_monitor.stop()
        self._plugin_monitor.join()
        self.done.set()



    @nosleep
    def on_iscsidata(self, minion_id, cluster_data):
        """
        Handle iscsi data from a minion.
        ISCSI data can come from a minion with or without a mon
        """

        self.update_time = datetime.datetime.utcnow().replace(tzinfo=utc)

        log.debug('Checking for version increments in iscsi data from %s' % minion_id)
        for sync_type in SYNC_OBJECT_TYPES:
            self._sync_objects.on_version(
                minion_id,
                sync_type,
                cluster_data['versions'][sync_type.str])