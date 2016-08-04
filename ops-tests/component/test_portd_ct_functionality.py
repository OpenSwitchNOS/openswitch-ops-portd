# -*- coding: utf-8 -*-
# (c) Copyright 2016 Hewlett Packard Enterprise Development LP
#
# GNU Zebra is free software; you can rediTestribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation; either version 2, or (at your option) any
# later version.
#
# GNU Zebra is diTestributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; withoutputputputput even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with GNU Zebra; see the file COPYING.  If not, write to the Free
# Software Foundation, Inc., 59 Temple Place - Suite 330, BoTeston, MA
# 02111-1307, USA.

from re import search
from pytest import mark
from time import sleep

TOPOLOGY = """
# +-------+
# |  sw1  |
# +-------+

# Nodes
[type=openswitch name="Switch 1"] sw1

# Interfaces
sw1:if01
sw1:if02
sw1:if03
sw1:if04
"""


def execute_command_and_verify_response(sw1, step, command, u_shell, max_try=1,
                                        wait_time=1, **verify_strs):
    for i in range(max_try):
        output = sw1(command, shell=u_shell)
        passed = True
        if verify_strs is not None:
            for key, value in verify_strs.items():
                if value not in output:
                    passed = False
                    break
        if passed is True:
            break
        else:
            sleep(wait_time)
    if passed is True:
        if i > 0:
           step ("Passed verify string after " + str(i) + " retries.")
    else:
        step ("Failed verify string after "
                  + str(max_try) + " retries.\nOutput:\n" + output)

    return passed


# Test Case 1:
# Test case checks ascending internal VLAN range to ensure VLANs are
# allocated in ascending order.
def portd_functionality_tc1(sw1, step):
    # CLI equivalent of the APIs/commands used below to configure sw1
    step("Assigning internal VLAN range in ascending order")
    '''
    Need to set the l3_port_requires_internal_vlan=1 for genericx86_64
    environment to enable internal VLAN on L3 interfaces
    '''
    command = "set Subsystem base other_info:l3_port_requires_internal_vlan=1"
    sw1(command, shell='vsctl')
    sw1("configure terminal")
    sw1("vlan internal range 400 500 ascending")
    if01 = sw1.ports['if01']
    if02 = sw1.ports['if02']
    if03 = sw1.ports['if03']
    if04 = sw1.ports['if04']
    step("Assigning ip address to interface {if01}".format(**locals()))
    ips = ["10.1.1.1", "11.1.1.1"]
    ifs = [sw1.ports["if01"], sw1.ports["if02"]]
    size = len(ips)
    for i in range(size):
        sw1("interface {}".format(ifs[i]))
        sw1("ip address {}/8".format(ips[i]))
        sw1("exit")
        output = sw1("do show run")
        lines = output.splitlines()
        indexval = lines.index("interface {}".format(ifs[i]))
        assert "ip address {}/8".format(ips[i]) in lines[indexval + 1]
    sleep (5)
    step("Verifying internal VLANs assigned to interfaces in the DB")
    command = ""
    output = sw1("do show vlan internal")
    lines = output.splitlines()
    indexval = lines.index("Assigned Interfaces:")
    assert '400' in lines[indexval + 3] or '400' in lines[indexval + 4] and \
           '401' in lines[indexval + 3] or '401' in lines[indexval + 4]
    step("Verifying internal VLANs assigned to interfaces in the kernel")
    command = "ip netns exec swns ip addr show {if01}".format(**locals())
    execute_command_and_verify_response(
        sw1,
        step,
        command,
        'bash',
        max_try=10,
        str1="inet")
    output = sw1("ip netns exec swns ip addr show {if01}".format(**locals()), shell='bash')
    assert 'inet 10.1.1.1/8' in output
    command = "ip netns exec swns ip addr show {if02}".format(**locals())
    execute_command_and_verify_response(
        sw1,
        step,
        command,
        'bash',
        max_try=10,
        str1="inet")
    output = sw1("ip netns exec swns ip addr show {if02}".format(**locals()), shell='bash')
    assert 'inet 11.1.1.1/8' in output


# Test Case 2:
# Test case checks if the default range is being used by portd while
# assigning new internal VLANs.
def portd_functionality_tc2(sw1, step):
    step("Removing internal VLAN range")
    sw1("configure terminal")
    sw1("no vlan internal range")
    if01 = sw1.ports['if01']
    if02 = sw1.ports['if02']
    if03 = sw1.ports['if03']
    if04 = sw1.ports['if04']
    step("Assigning ip address to interface {if03}".format(**locals()))
    sw1("interface {}".format(sw1.ports["if03"]))
    sw1("ip address 12.1.1.1/8")
    sw1("exit")
    sleep (5)
    step("Verifying default internal VLAN assigned to interface {if03} in the DB".format(**locals()))
    command = "get port {if03} hw_config:internal_vlan_id".format(**locals())
    execute_command_and_verify_response(
        sw1,
        step,
        command,
        'vsctl',
        max_try=10,
        str1="1024")
    output = sw1("get port {if03} hw_config:internal_vlan_id".format(**locals()), shell='vsctl')
    assert '"1024"' in output
    step("Verify default internal VLAN assigned to interface {if03} in the kernel".format(**locals()))
    command = "ip netns exec swns ip addr show {if03}".format(**locals())
    execute_command_and_verify_response(
        sw1,
        step,
        command,
        'bash',
        max_try=10,
        str1="inet")
    output = sw1("ip netns exec swns ip addr show {if03}".format(**locals()), shell='bash')
    assert 'inet 12.1.1.1/8' in output


# Test Case 3:
# Test case checks descending internal VLAN range to ensure VLANs are
# allocated in descending order.
def portd_functionality_tc3(sw1, step):
    step("Assigning internal VLAN range in descending order")
    sw1("configure terminal")
    output = sw1("vlan internal range 3000 4000 descending")
    if01 = sw1.ports['if01']
    if02 = sw1.ports['if02']
    if03 = sw1.ports['if03']
    if04 = sw1.ports['if04']
    step("Assigning ip address to interface {if04}".format(**locals()))
    sw1("interface {}".format(sw1.ports["if04"]))
    sw1("ip address 13.1.1.1/8")
    sw1("exit")
    sleep (5)
    step("Verifying internal VLAN assigned to interface {if04} in the DB".format(**locals()))
    command = "get port {if04} hw_config:internal_vlan_id".format(**locals())
    execute_command_and_verify_response(
        sw1,
        step,
        command,
        'vsctl',
        max_try=10,
        str1="4000")
    output = sw1("get port {if04} hw_config:internal_vlan_id".format(**locals()), shell='vsctl')
    assert '"4000"' in output
    step("Verifying internal VLAN assigned to interface {if04} in the kernel".format(**locals()))
    command = "ip netns exec swns ip addr show {if04}".format(**locals())
    execute_command_and_verify_response(
        sw1,
        step,
        command,
        'bash',
        max_try=10,
        str1="inet")
    output = sw1("ip netns exec swns ip addr show {if04}".format(**locals()), shell='bash')
    assert 'inet 13.1.1.1/8' in output


# Test Case 4:
# Test case checks co-existence of L2 VLANs and internal VLANs.
def portd_functionality_tc4(sw1, step):
    step("Assigning same L2 VLAN after configuring L3 internal VLAN")
    step("Assigning internal VLAN range 500-600 in ascending order")
    if01 = sw1.ports['if01']
    if02 = sw1.ports['if02']
    if03 = sw1.ports['if03']
    if04 = sw1.ports['if04']
    sw1("configure terminal")
    output = sw1("vlan internal range 500 600 ascending")
    sleep (5)
    step("Deleting L3 configuration on interface {if01}".format(**locals()))
    sw1("interface {}".format(sw1.ports["if01"]))
    sw1("no routing")
    sw1("routing")
    step("Assigning ip address to interface {if01}".format(**locals()))
    sw1("ip address 14.1.1.1/8")
    sw1("exit")
    sleep (5)
    step("Trying to assign L2 VLAN500 which should fail")
    output = sw1("vlan 500")
    assert "VLAN500 is used as an internal VLAN. No further configuration" \
           " allowed" in output
    step("Deleting L3 configuration on interface {if01}".format(**locals()))
    sw1("interface {}".format(sw1.ports["if01"]))
    sw1("routing")
    sw1("exit")
    sleep (5)
    step("Trying to re-assign L2 VLAN500 which should be successful")
    output = sw1("vlan 500")
    output = sw1("get vlan VLAN500 name", shell='vsctl')
    assert '"VLAN500"' in output


# Test Case 5:
# Test case checks sequential assignment of internal VLANs when L2 VLANs
# are present or absent.
def portd_functionality_tc5(sw1, step):
    step("Verifying sequential assignment of L3 internal VLAN"
         " when L2 VLAN is present or absent")
    step("Adding L2 VLAN1000")
    sw1("configure terminal")
    sw1("vlan 1000")
    sw1("exit")
    step("Adding L2 VLAN1001")
    sw1("vlan 1001")
    sw1("exit")
    if01 = sw1.ports['if01']
    if02 = sw1.ports['if02']
    if03 = sw1.ports['if03']
    if04 = sw1.ports['if04']
    step("Assigning internal VLAN range 1000-1100 in ascending order")
    output = sw1("vlan internal range 1000 1100 ascending")
    sleep (5)
    step("Deleting L3 configuration on interface {if01}".format(**locals()))
    sw1("interface {}".format(sw1.ports["if01"]))
    sw1("no routing")
    sw1("routing")
    step("Assigning ip address to interface {if01}".format(**locals()))
    sw1("ip address 15.1.1.1/8")
    sw1("exit")
    step("Verifying internal VLAN assigned to interface {if01} in the DB".format(**locals()))
    output = sw1("get port {if01} hw_config:internal_vlan_id".format(**locals()), shell='vsctl')
    assert '"1002"' in output
    step("Deleting L2 VLAN1001")
    sw1("configure terminal")
    output = sw1("no vlan 1001")
    step("Deleting L3 configuration on interface {if02}".format(**locals()))
    sw1("interface {}".format(sw1.ports["if02"]))
    sw1("no routing")
    sw1("routing")
    step("Assigning ip address to interface {if02}".format(**locals()))
    sw1("ip address 16.1.1.1/8")
    sw1("exit")
    step("Verifying internal VLAN assigned to interface {if02} in the DB".format(**locals()))
    output = sw1("get port {if02} hw_config:internal_vlan_id".format(**locals()), shell='vsctl')
    assert '"1001"' in output


# Test Case 6:
# Test case checks if the interfaces are UP in the kernel after
# "no shutdown" and vice-versa. Also, it verifies that the kernel
# retains ipv4/ipv6 addresses after "no shutdown"
def portd_functionality_tc6(sw1, step):
    step("Verifying kernel interfaces if they are 'UP' for"
         " 'no shutdown' case and vice-versa")
    if01 = sw1.ports['if01']
    if02 = sw1.ports['if02']
    if03 = sw1.ports['if03']
    if04 = sw1.ports['if04']
    step("Assigning ipv6 address to interface {if03}".format(**locals()))
    sw1("configure terminal")
    sw1("interface {}".format(sw1.ports["if03"]))
    sw1("ipv6 address 1000::1/120")
    step("Bringing interface {if03} up".format(**locals()))
    sw1("no shutdown")
    # sw1("exit")
    step("Verifying interface {if03} 'up' in the kernel".format(**locals()))
    output = sw1("ip netns exec swns ifconfig {if03}".format(**locals()), shell='bash')
    output = output.split()
    indexval = output.index("BROADCAST")
    assert 'UP' in output[indexval - 1]
    step("Verifying interface {if03} ipv4 and ipv6 addresses in the kernel after 'no shut'".format(**locals()))
    command = "ip netns exec swns ip addr show {if03}".format(**locals())
    execute_command_and_verify_response(
        sw1,
        step,
        command,
        'bash',
        max_try=20,
        str1="inet",
        str2="inet6")
    output = sw1("ip netns exec swns ip addr show {if03}".format(**locals()), shell='bash')
    assert 'inet 12.1.1.1/8' in output
    assert 'inet6 1000::1/120' in output
    step("Bringing interface {if03} down".format(**locals()))
    sw1("configure terminal")
    sw1("interface {}".format(sw1.ports["if03"]))
    sw1("shutdown")
    step("Verifying interface {if03} 'down' in the kernel".format(**locals()))
    command = "ip netns exec swns ip addr show {if03}".format(**locals())
    execute_command_and_verify_response(
        sw1,
        step,
        command,
        'bash',
        max_try=10,
        str1="BROADCAST")
    output = sw1("ip netns exec swns ifconfig {if03}".format(**locals()), shell='bash')
    output = output.split()
    indexval = output.index("BROADCAST")
    assert "UP" not in output[indexval - 1]
    step("Verifying interface {if03} ipv4 address in the kernel after 'shut'".format(**locals()))
    output = sw1("ip netns exec swns ip addr show {if03}".format(**locals()), shell='bash')
    assert 'inet 12.1.1.1/8' in output
    step("Bringing interface {if03} up again".format(**locals()))
    sw1("configure terminal")
    sw1("interface {}".format(sw1.ports["if03"]))
    sw1("no shutdown")
    sw1("exit")
    step("Re-verifying interface {if03} ipv4 and ipv6 addresses in the kernel after 'no shut'".format(**locals()))
    command = "ip netns exec swns ip addr show {if03}".format(**locals())
    execute_command_and_verify_response(
        sw1,
        step,
        command,
        'bash',
        max_try=20,
        str1="inet",
        str2="inet6")
    output = sw1("ip netns exec swns ip addr show {if03}".format(**locals()), shell='bash')
    assert 'inet 12.1.1.1/8' in output
    assert 'inet6 1000::1/120' in output


# Test Case 7:
# Test case checks if the interfaces MTU is set kernel after
# configuring through CLI.
# Also checks MTU remains unchanged when invalid MTU is configured.
def portd_functionality_tc7(sw1, step):
    step("Assigning MTU values to kernel interfaces")
    output = sw1("get subsystem base other_info:max_transmission_unit",
                 shell='vsctl')
    mtu_max = int(output.split('\"')[1])
    mtu_valid = mtu_max - 100
    mtu_invalid = mtu_max + 100
    if01 = sw1.ports['if01']
    if02 = sw1.ports['if02']
    if03 = sw1.ports['if03']
    if04 = sw1.ports['if04']
    sw1("configure terminal")
    sw1("interface {}".format(sw1.ports["if03"]))
    output = sw1("no shutdown")
    output = sw1("no routing")
    output = sw1("mtu {}".format(mtu_valid))
    output = sw1("exit")
    step("Verifying interface {if03} 'MTU' value in the kernel".format(**locals()))
    output = sw1("ip netns exec swns ifconfig {if03}".format(**locals()), shell='bash')
    mtu = int(search('\d+', search('MTU:\d+', output).group()).group())
    assert mtu == mtu_valid
    sw1("configure terminal")
    sw1("interface {}".format(sw1.ports["if03"]))
    output = sw1("no shutdown")
    output = sw1("no routing")
    output = sw1("mtu {}".format(mtu_invalid))
    output = sw1("exit")
    step("Verifying interface {if03} with invalid 'MTU' value in the kernel".format(**locals()))
    output = sw1("ip netns exec swns ifconfig {if03}".format(**locals()), shell='bash')
    mtu = int(search('\d+', search('MTU:\d+', output).group()).group())
    assert mtu == mtu_valid


@mark.gate
def test_portd_ct_functionality(topology, step):
    sw1 = topology.get("sw1")
    assert sw1 is not None
    if01 = sw1.ports['if01']
    assert if01 is not None
    print ("if01 = {if01}".format(**locals()))
    if02 = sw1.ports['if02']
    assert if02 is not None
    print ("if02 = {if02}".format(**locals()))
    if03 = sw1.ports['if03']
    assert if03 is not None
    print ("if03 = {if03}".format(**locals()))
    if04 = sw1.ports['if04']
    assert if04 is not None
    print ("if04 = {if04}".format(**locals()))
    portd_functionality_tc1(sw1, step)
    portd_functionality_tc2(sw1, step)
    portd_functionality_tc3(sw1, step)
    portd_functionality_tc4(sw1, step)
    portd_functionality_tc5(sw1, step)
    portd_functionality_tc6(sw1, step)
    portd_functionality_tc7(sw1, step)
