#!/usr/bin/env python

# Copyright 2014, Rackspace US, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import optparse
import shlex
import subprocess


from maas_common import metric
from maas_common import print_output
from maas_common import status_err


def galera_check(arg):
    proc = subprocess.Popen(shlex.split(arg),
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            shell=False)

    out, err = proc.communicate()
    ret = proc.returncode
    return ret, out, err


def generate_query(host, port, output_type='status'):
    if host:
        host = ' -h %s' % host
    else:
        host = ''

    if port:
        port = ' -P %s' % port
    else:
        port = ''
    if output_type == 'status':
        return ('/usr/bin/mysql --defaults-file=/root/.my.cnf '
                '%s%s -e "SHOW GLOBAL STATUS"') % (host, port)
    elif output_type == 'variables':
        return ('/usr/bin/mysql --defaults-file=/root/.my.cnf '
                '%s%s -e "SHOW GLOBAL VARIABLES"') % (host, port)


def parse_args():
    parser = optparse.OptionParser(usage='%prog [-h] [-H hostname] [-P port]')
    parser.add_option('-H', '--host', action='store', dest='host',
                      default=None,
                      help='Host to override the defaults with')
    parser.add_option('-P', '--port', action='store', dest='port',
                      default=None,
                      help='Port to override the defauults with')
    return parser.parse_args()


def print_metrics(replica_status):

    metric('galera', 'wsrep_replicated_bytes',
           replica_status['wsrep_replicated_bytes'])
    metric('galera', 'wsrep_received_bytes',
           replica_status['wsrep_received_bytes'])
    metric('galera', 'wsrep_commit_window_size',
           replica_status['wsrep_commit_window'])
    metric('galera', 'wsrep_cluster_size_nodes',
           replica_status['wsrep_cluster_size'])
    metric('galera', 'queries_per_second',
           replica_status['Queries'])
    metric('galera', 'wsrep_cluster_state_uuid',
           replica_status['wsrep_cluster_state_uuid'])
    metric('galera', 'wsrep_cluster_status',
           replica_status['wsrep_cluster_status'])
    metric('galera', 'wsrep_local_state_uuid',
           replica_status['wsrep_local_state_uuid'])
    metric('galera', 'wsrep_local_state_comment',
           replica_status['wsrep_local_state_comment'])
    metric('galera', 'mysql_max_configured_connections',
           replica_status['max_connections'])
    metric('galera', 'mysql_current_connections',
           replica_status['Threads_connected'])
    metric('galera', 'mysql_max_seen_connections',
           replica_status['Max_used_connections'])
    metric('galera', 'num_of_open_files',
           replica_status['Open_files'])
    metric('galera', 'open_files_limit',
           replica_status['open_files_limit'])
    metric('galera', 'innodb_row_lock_time_avg',
           replica_status['Innodb_row_lock_time_avg'])
    metric('galera', 'innodb_deadlocks',
           replica_status['Innodb_deadlocks'])
    metric('galera', 'access_denied_errors',
           replica_status['Access_denied_errors'])
    metric('galera', 'aborted_clients',
           replica_status['Aborted_clients'])
    metric('galera', 'aborted_connects',
           replica_status['Aborted_connects'])


def main():
    options, _ = parse_args()

    replica_status = {}
    for output_type in ['status', 'variables']:
        retcode, output, err = galera_check(
            generate_query(options.host, options.port, output_type=output_type)
        )

        if retcode > 0:
            status_err(err)

        if not output:
            status_err('No output received from mysql. Cannot gather metrics.')

        show_list = output.split('\n')[1:-1]
        for i in show_list:
            replica_status[i.split('\t')[0]] = i.split('\t')[1]

    if replica_status['wsrep_cluster_status'] != "Primary":
        status_err("there is a partition in the cluster")

    if (replica_status['wsrep_local_state_uuid'] !=
            replica_status['wsrep_cluster_state_uuid']):
        status_err("the local node is out of sync")

    if (int(replica_status['wsrep_local_state']) == 4 and
            replica_status['wsrep_local_state_comment'] == "Synced"):
        print_metrics(replica_status)


if __name__ == '__main__':
    with print_output():
        main()
