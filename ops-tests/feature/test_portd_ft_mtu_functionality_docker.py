# -*- coding: utf-8 -*-
#
# Copyright (C) 2016 Hewlett Packard Enterprise Development LP
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

"""
OpenSwitch Test for MTU related configurations.
"""

from __future__ import unicode_literals, absolute_import
from __future__ import print_function, division
from time import sleep


TOPOLOGY = """
# +-------+
# |       |     +--------+
# |  h1  <----->   ops1  |
# |       |     +--------+
# +-------+

# Nodes
[type=openswitch name="OpenSwitch 1"] ops1
[type=host name="Host 1"] h1

# Links
h1:1 -- ops1:5
"""

# Test case Variable
INTF_DUT = '5'
VLAN_DUT = '10'
NETMASK = '255.255.255.0'
DUT_NETWORK = '192.168'
IPADDR1 = '.1'
IPADDR2 = '.2'
SUBNET = '24'
MTU_SIZE = '600'


def test_mtu(topology, step):
    """
    Test that a mtu configuration is functional with a OpenSwitch switch.

    Build a topology of one switch and one host and connect the host to the
    switch. Setup a MTU for the ports connected to the host and ping from
    host 1 to switch with greater packet size.
    """
    ops1 = topology.get('ops1')
    h1 = topology.get('h1')

    assert ops1 is not None
    assert h1 is not None

    step('Adding vlan {} on device ops'.format(VLAN_DUT))
    with ops1.libs.vtysh.ConfigVlan(VLAN_DUT) as ctx:
        ctx.no_shutdown()
    with ops1.libs.vtysh.ConfigInterfaceVlan(VLAN_DUT) as ctx:
        ctx.no_shutdown()
        ctx.ip_address('{}.{}{}/{}'.format(DUT_NETWORK, VLAN_DUT,
                       IPADDR1, SUBNET))

    with ops1.libs.vtysh.ConfigInterface(INTF_DUT) as ctx:
        ctx.no_routing()
        ctx.no_shutdown()
        ctx.mtu(MTU_SIZE)
        ctx.vlan_access(VLAN_DUT)

    # Configure host interfaces
    h1.libs.ip.interface('1', addr='{}.{}{}/{}'.format(DUT_NETWORK,
                         VLAN_DUT, IPADDR2, SUBNET), up=True)
    sleep(30)
    # Test ping
    ping = h1.libs.ping.ping(1, '{}.{}{}'.format(DUT_NETWORK, VLAN_DUT,
                             IPADDR1))
    assert ping['transmitted'] == ping['received'] == 1

    # Test ping with more frame size
    h1('ping -s 900 -c 10 {}.{}{}'.format(DUT_NETWORK, VLAN_DUT,
       IPADDR1))
    final_status = {}
    final_status = ops1.libs.vtysh.show_interface(INTF_DUT)
    assert(final_status['rx_dropped'] != 0)
