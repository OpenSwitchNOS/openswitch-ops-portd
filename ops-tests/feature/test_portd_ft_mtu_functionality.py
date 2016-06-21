# -*- coding: utf-8 -*-
#
# Copyright (C) 2015-2016 Hewlett Packard Enterprise Development LP
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
Author: Mahadhevan Mani - mahadevan.mani@hpe.com
test Name: "test_portd_ft_mtu_functionality.py"
test Description ("This test will verify MTU functionlaity)
"""


from __future__ import unicode_literals, absolute_import
from __future__ import print_function, division
from time import sleep
from pytest import mark


TOPOLOGY = """
# +-------+     +-------+     +-------+
# |       |     |       |     |       |
# |  ix1  <-----> ops1  <----->  ops2 |
# |       |     |       |     |       |
# +-------+     +-------+     +-------+

# Nodes
[type=openswitch name="OpenSwitch 1"] ops1
[type=openswitch name="OpenSwitch 2"] ops2

[type=ixia name="Ixia 1"] ix1

#Links
ix1:if01 -- ops1:p1
ops1:p2  -- ops2:p1
"""


# Test case Variables
TIMEOUT = '0'
IPADDR1 = '.1'
IPADDR2 = '.2'
IPADDR3 = '.3'
VLAN_DUT1 = '10'
NETMASK = '255.255.255.0'
DUT_IX_NETWORK = '172.16'
SUBNET = '24'
DURATION = float(10)
TRAFFIC_OVERFLOW_CHECK = float(0.9875)


def session_timeout(switch, timeout, step):
    step('Configure session timeout on DUTS')
    # Session timeout configuration on DUTs
    with switch.libs.vtysh.Configure() as ctx:
        ctx.session_timeout(timeout)


def vlan_add(switch1, switch2, int1, int2, int3, step):
    step('Adding vlan {} on device ops'.format(VLAN_DUT1))
    with switch1.libs.vtysh.ConfigVlan(VLAN_DUT1) as ctx:
        ctx.no_shutdown()
    with switch1.libs.vtysh.ConfigInterfaceVlan(VLAN_DUT1) as ctx:
        ctx.no_shutdown()
        ctx.ip_address('{}.{}{}/{}'.format(DUT_IX_NETWORK, VLAN_DUT1,
                       IPADDR2, SUBNET))

    with switch1.libs.vtysh.ConfigInterface(int1) as ctx:
        ctx.no_routing()
        ctx.no_shutdown()
        ctx.vlan_access(VLAN_DUT1)

    with switch1.libs.vtysh.ConfigInterface(int2) as ctx:
        ctx.no_routing()
        ctx.no_shutdown()
        ctx.mtu(9192)
        ctx.vlan_access(VLAN_DUT1)

    with switch2.libs.vtysh.ConfigVlan(VLAN_DUT1) as ctx:
        ctx.no_shutdown()
    with switch2.libs.vtysh.ConfigInterfaceVlan(VLAN_DUT1) as ctx:
        ctx.no_shutdown()
        ctx.ip_address('{}.{}{}/{}'.format(DUT_IX_NETWORK, VLAN_DUT1,
                       IPADDR3, SUBNET))

    with switch2.libs.vtysh.ConfigInterface(int3) as ctx:
        ctx.no_routing()
        ctx.no_shutdown()
        ctx.vlan_access(VLAN_DUT1)


def vlan_check(switch1, switch2, int1, int3, step):
    # Check VLAN Config on DUT1
    step("Check vlan is created and assigned to the correct ports")
    vlan_output = switch1.libs.vtysh.show_vlan()
    assert (vlan_output[VLAN_DUT1]),\
        'Error: VLAN not present in DUT'
    assert (vlan_output[VLAN_DUT1]['reason'] == "ok" and
            vlan_output[VLAN_DUT1]['status'] == "up"),\
        'Error: VLAN {} not set on DUT1'.format(VLAN_DUT1)
    assert (int1 in vlan_output
            [VLAN_DUT1]['ports']),\
        'Error : VLAN {} is not set to interface in DUT1'.format(VLAN_DUT1)

    # Check VLAN Config on DUT2
    step("Check vlan is created and assigned to the correct ports")
    vlan_output = switch2.libs.vtysh.show_vlan()
    assert (vlan_output[VLAN_DUT1]),\
        'Error: VLAN not present in DUT'
    assert (vlan_output[VLAN_DUT1]['reason'] == "ok" and
            vlan_output[VLAN_DUT1]['status'] == "up"),\
        'Error: VLAN {} not set on DUT1'.format(VLAN_DUT1)
    assert (int3 in vlan_output
            [VLAN_DUT1]['ports']),\
        'Error : VLAN {} is not set to interface in DUT1'.format(VLAN_DUT1)


def ixia_connect(ix, ixia_port, step):
    step('Connecting to IXIA')
    ix.libs.ixia.send_ixia_command('ixiaFunc::Connect',
                                   device='$::topo({})'.format(ix.alias))
    # Take ownership of IXIA Ports
    result_str = ix.libs.ixia.send_ixia_command(
        'ixiaFunc::TakePortOwnership',
        device='$::topo({})'.format(ix.alias),
        portList='{{{}}}'.format(ixia_port)
    )
    result = ix.libs.ixia.parse_result(result_str)
    assert int(result['status']) == 0,\
        'Unable to take IXIA Ownership'

    # Set IXIA Ports to Default Configuration
    result_str = ix.libs.ixia.send_ixia_command(
        'ixiaFunc::SetFactoryDefault',
        device='$::topo({})'.format(ix.alias),
        portsList='{{{}}}'.format(ixia_port)
    )
    result = ix.libs.ixia.parse_result(result_str)
    assert int(result['status']) == 0,\
        'Unable to set Ixia ports to factory defaults'

    # Clear statistics on Ixia ports
    print('Clear Ixia ports statistics')
    result_str = ix.libs.ixia.send_ixia_command(
        'ixiaFunc::ClearPortStats',
        device='$::topo({})'.format(ix.alias),
        portList='{}'.format(ixia_port)
    )
    result = ix.libs.ixia.parse_result(result_str)
    assert int(result['status']) == 0, \
        'Unable to clear Ixia ports statistics'


def ixia_create_interface(ix, port_list, ip_addr, gateway, netmask,
                          vlan=None, mac_addr=None, if_desc=None):
    print('Creating IXIA interface')
    result_str = ix.libs.ixia.send_ixia_command(
        'ixiaFunc::SimulateIpProtocol',
        device='$::topo({})'.format(ix.alias),
        portList=port_list,
        option='add',
        ipAddr=ip_addr,
        netMask=netmask,
        gateway=gateway,
        macAddr=mac_addr,
        ifDesc=if_desc
    )
    result = ix.libs.ixia.parse_result(result_str)
    assert int(result['status']) == 0, \
        'Unable to create Ixia sub-interface'


def ixia_get_port_list(ix, interface):
    interface_card = ix.ports[interface].split('/')
    return '{{{} {} {}}}'.format('1', interface_card[0], interface_card[1])


def ixia_config_stream(ix, port_list, src_ip, dst_mask, dst_ip,
                       src_mac, dst_mac, frame_size, stream_rate='1000',
                       stream_mode='streamRateModeFps', protocol_name='ipV4',
                       eth_type='ethernetII', ip_proto='ipV4ProtocolUdp',
                       stream_id='1', stream_num_frames='1',
                       stream_dma='contPacket', return_id='1'):
    res = ix.libs.ixia.send_ixia_command('ixiaFunc::ConfigStream',
                                         portList=port_list,
                                         device='$::topo({})'.
                                         format(ix.alias),
                                         protocol_name=protocol_name,
                                         protocol_ethernetType=eth_type,
                                         ip_ipProtocol=ip_proto,
                                         ip_sourceIpAddr=src_ip,
                                         ip_sourceIpMask=dst_mask,
                                         ip_destIpAddr=dst_ip,
                                         ip_destIpMask=dst_mask,
                                         stream_fpsRate=stream_rate,
                                         stream_rateMode=stream_mode,
                                         stream_streamId=stream_id,
                                         stream_numFrames=stream_num_frames,
                                         stream_dma=stream_dma,
                                         stream_sa=src_mac,
                                         stream_da=dst_mac,
                                         stream_framesize=frame_size)
    result = ix.libs.ixia.parse_result(res)
    assert int(result['status']) == 0, \
        'Unable to create stream on Ixia port'


def ixia_ping(ix, port_list, iface, dst_ip):
    for i in range(0, 5):
        res = ix.libs.ixia.send_ixia_command('ixiaFunc::PingHost',
                                             device='$::topo({})'.
                                             format(ix.alias),
                                             portList=port_list,
                                             dstIpAddr=dst_ip,
                                             ifDesc=iface)
        res = ix.libs.ixia.parse_result(res)
        if res['status'] == '0':
            return True
    return False


def get_interface_statistics(switch1, switch2, int1, int2, step):
    step('### Get the initial interfaces statistics ###')
    result = {}
    int_status_dut1 = switch1.libs.vtysh.show_interface(int1)
    int_status_dut2 = switch2.libs.vtysh.show_interface(int2)

    result['dut1'] = int_status_dut1
    result['dut2'] = int_status_dut2

    return result


def verify_interface_traffic(switch1, switch2, int2, int3, init_status, step):
    step('### Verify the UDP throughput ###')
    final_status = {}
    # Get interface statistics after Traffic flow
    int_status_dut1 = {}
    int_status_dut2 = {}
    int_status_dut1 = switch1.libs.vtysh.show_interface(int2)
    int_status_dut2 = switch2.libs.vtysh.show_interface(int3)

    final_status['dut1'] = int_status_dut1
    final_status['dut2'] = int_status_dut2

    # Verify the Traffic flow is not lost more than 1%
    received = (final_status['dut2']['rx_bytes'] -
                init_status['dut2']['rx_bytes'])
    sent = (final_status['dut1']['tx_bytes'] -
            init_status['dut1']['tx_bytes'])

    print('{:.2f}% of traffic received'.
          format(sent * 100 / received))
    assert(sent > received * 0.98), \
        'ERROR: more than 2% of the traffic is lost in the system'
    assert(received >= sent * 0.9875), \
        'ERROR: more traffic from switch is sent than received'


def set_ixia_config(ix1, switch1, switch2, int1, int2, int3, step):
    step('### Configure Ixia ports ###')
    int_status_dut2 = switch2.libs.vtysh.show_interface('1')

    ixia_connect(ix1, ixia_get_port_list(ix1, 'if01'), step)
    temp_ip_ix1 = ('{}.{}{}').format(DUT_IX_NETWORK, VLAN_DUT1, IPADDR1)
    temp_ip_ix2 = ('{}.{}{}').format(DUT_IX_NETWORK, VLAN_DUT1, IPADDR3)
    temp_mac_ix1 = ('00:00:AC:10:0A:{}').format(VLAN_DUT1)
    # IXIA connected to DUT1
    step('Creating First IXIA Interface')
    ixia_create_interface(ix1, ixia_get_port_list(ix1, 'if01'), temp_ip_ix1,
                          DUT_IX_NETWORK + '.' + VLAN_DUT1 + IPADDR1, SUBNET,
                          vlan=None, mac_addr=temp_mac_ix1,
                          if_desc='if0101')
    # Configure Stream on IXIA
    mac_dut2 = int_status_dut2['mac_address']
    step('Configuring IXIA Stream')
    step('Ping test between IXIA with frame size 4000 and Switch MTU 4000')

    with switch1.libs.vtysh.ConfigInterface(int1) as ctx:
        ctx.mtu(4000)

    with switch2.libs.vtysh.ConfigInterface(int3) as ctx:
        ctx.mtu(9192)

    ixia_config_stream(ix1, ixia_get_port_list(ix1, 'if01'), temp_ip_ix1,
                       NETMASK, temp_ip_ix2, temp_mac_ix1, mac_dut2, '4000',
                       '372000', 'streamRateModeFps', 'ipV4', 'ethernetII',
                       'ipV4ProtocolUdp', '1', '1')
    ping_test = (ixia_ping(ix1, ixia_get_port_list(ix1, 'if01'),
                 'if0101', temp_ip_ix2))
    assert ping_test, \
        'ERROR : Ping failed from {} to {}'.format(
            temp_ip_ix1, temp_ip_ix2)

    # Initial Interface statistics
    stats = get_interface_statistics(switch1, switch2, int2, int3, step)
    # Send traffic for TEST duration
    ixia_send_traffic(ix1, ixia_get_port_list(ix1, 'if01'), step)
    # Verify that all the interfaces are transmitting packets
    verify_interface_traffic(switch1, switch2, int2, int3, stats, step)

    step('Test between IXIA with frame size 4000 and Switch MTU 4500')

    with switch1.libs.vtysh.ConfigInterface(int1) as ctx:
        ctx.mtu(4500)

    ixia_config_stream(ix1, ixia_get_port_list(ix1, 'if01'), temp_ip_ix1,
                       NETMASK, temp_ip_ix2, temp_mac_ix1, mac_dut2, '4000',
                       '372000', 'streamRateModeFps', 'ipV4', 'ethernetII',
                       'ipV4ProtocolUdp', '1', '1')
    # Initial Interface statistics
    stats = get_interface_statistics(switch1, switch2, int2, int3, step)
    # Send traffic for TEST duration
    ixia_send_traffic(ix1, ixia_get_port_list(ix1, 'if01'), step)
    # Verify that all the interfaces are transmitting packets
    verify_interface_traffic(switch1, switch2, int2, int3, stats, step)

    step('Test between IXIA with frame size 9216 and Switch MTU 9192')

    with switch1.libs.vtysh.ConfigInterface(int1) as ctx:
        ctx.mtu(9192)

    ixia_config_stream(ix1, ixia_get_port_list(ix1, 'if01'), temp_ip_ix1,
                       NETMASK, temp_ip_ix2, temp_mac_ix1, mac_dut2, '9216',
                       '372000', 'streamRateModeFps', 'ipV4', 'ethernetII',
                       'ipV4ProtocolUdp', '1', '1')
    # Initial Interface statistics
    stats = get_interface_statistics(switch1, switch2, int2, int3, step)
    # Send traffic for TEST duration
    ixia_send_traffic(ix1, ixia_get_port_list(ix1, 'if01'), step)
    # Verify that all the interfaces are transmitting packets
    verify_interface_traffic(switch1, switch2, int2, int3, stats, step)

    step('Test between IXIA with frame size 6000 and Switch MTU 4500')

    with switch1.libs.vtysh.ConfigInterface(int1) as ctx:
        ctx.mtu(4500)

    ixia_config_stream(ix1, ixia_get_port_list(ix1, 'if01'), temp_ip_ix1,
                       NETMASK, temp_ip_ix2, temp_mac_ix1, mac_dut2, '6000',
                       '372000', 'streamRateModeFps', 'ipV4', 'ethernetII',
                       'ipV4ProtocolUdp', '1', '1')

    init_status = get_interface_statistics(switch1, switch2, int2, int3, step)
    ixia_send_traffic(ix1, ixia_get_port_list(ix1, 'if01'), step)
    final_status = {}
    int_status_dut1 = {}
    int_status_dut1 = switch1.libs.vtysh.show_interface(int2)
    int_status_dut = switch1.libs.vtysh.show_interface(int1)

    final_status['dut1'] = int_status_dut1

    received = (final_status['dut1']['rx_bytes'] -
                init_status['dut1']['rx_bytes'])
    sent = (final_status['dut1']['tx_bytes'] -
            init_status['dut1']['tx_bytes'])

    # Verify there wont be any  Traffic flow and only input error
    assert (int_status_dut['rx_error'] != 0 and
            received == 0 and sent == 0)

    step('IXIA frame size 6000 and Switch int 1 MTU-6000 & int 2 MTU-5000')

    with switch1.libs.vtysh.ConfigInterface(int1) as ctx:
        ctx.mtu(6000)

    with switch1.libs.vtysh.ConfigInterface(int2) as ctx:
        ctx.mtu(5000)

    int_status1 = switch1.libs.vtysh.show_interface(int1)
    int_status2 = switch1.libs.vtysh.show_interface(int2)
    ixia_send_traffic(ix1, ixia_get_port_list(ix1, 'if01'), step)
    final_status_int1 = switch1.libs.vtysh.show_interface(int1)
    final_status_int2 = switch1.libs.vtysh.show_interface(int2)

    dropped = final_status_int2['tx_dropped'] - int_status2['tx_dropped']
    received = final_status_int1['rx_packets'] - int_status1['rx_packets']

    # verify the packets sent from int 1 has been dropped in int 2
    assert (received == dropped)


def ixia_send_traffic(ix, port_list1, step, stream_type='continous'):
    step('Start sending UDP Traffic for {} seconds'.format(DURATION))
    ix.libs.ixia.send_ixia_command('ixiaFunc::StartTransmit',
                                   device='$::topo({})'.format(ix.alias),
                                   streamType=stream_type, portList=port_list1)
    step('Start sending UDP Traffic for {} seconds'.format(DURATION))
    sleep(DURATION)
    step('Stop Traffic on IXIA')
    ix.libs.ixia.send_ixia_command('ixiaFunc::StopTransmit',
                                   device='$::topo({})'.format(ix.alias),
                                   portList=port_list1)
    sleep(30)


@mark.platform_incompatible(['docker'])
@mark.timeout(3900)
def test_portd_ft_mtu_functionality(topology, step):
    ops1 = topology.get('ops1')
    ops2 = topology.get('ops2')
    ix1 = topology.get('ix1')

    assert ops1 is not None
    assert ops2 is not None
    assert ix1 is not None

    dut_1_int1 = ops1.ports['p1']
    dut_1_int2 = ops1.ports['p2']
    dut_2_int1 = ops2.ports['p1']
    # Configure session timeout on DUTs
    session_timeout(ops1, TIMEOUT, step)
    session_timeout(ops2, TIMEOUT, step)
    # Create VLAN on the DUTs
    vlan_add(ops1, ops2, dut_1_int1, dut_1_int2, dut_2_int1, step)

    # Verify vlan is configured on the DUTs
    vlan_check(ops1, ops2, dut_1_int1, dut_2_int1, step)

    # Configure IXIA Interface
    set_ixia_config(ix1, ops1, ops2, dut_1_int1, dut_1_int2, dut_2_int1, step)
