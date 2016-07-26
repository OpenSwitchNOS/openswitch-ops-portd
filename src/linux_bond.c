/*
 * (c) Copyright 2016 Hewlett Packard Enterprise Development LP
 *
 * Licensed under the Apache License, Version 2.0 (the "License"); you may
 * not use this file except in compliance with the License. You may obtain
 * a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
 * WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
 * License for the specific language governing permissions and limitations
 * under the License.
 */

/***************************************************************************
 *    File               : linux_bond.c
 *    Description        : Manages (creates, deletes, configures) Linux
 *                           bonding interfaces
 ***************************************************************************/

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#include <ops-utils.h>

#include <unixctl.h>
#include <dynamic-string.h>
#include <openswitch-idl.h>
#include <openswitch-dflt.h>
#include <openvswitch/vlog.h>
#include <poll-loop.h>
#include <hash.h>
#include <shash.h>

#include "linux_bond.h"

VLOG_DEFINE_THIS_MODULE(linux_bond);

#define WRITE_UPDATE            "w+"
#define READ                    "r"

#define MAX_FILE_PATH_LEN       100
#define BONDING_MASTERS_PATH    "/sys/class/net/bonding_masters"
#define BONDING_MODE_PATH       "/sys/class/net/%s/bonding/mode"
#define BONDING_SLAVES_PATH     "/sys/class/net/%s/bonding/slaves"
#define BALANCE_XOR_MODE        "2"
#define BONDING_CONFIG_PATH     "/proc/net/bonding/%s"
#define BONDING_LINE_LEN        60
#define SLAVE_IF                "Slave Interface: %s"
#define SLAVE_IF_LEN            19

/**
 * Deletes a Linux bond interface previously created.
 *
 * @param bond_name is the name of the bond to be deleted
 * @return true if the bond was deleted, false otherwise
 *
 */
bool delete_linux_bond(char* bond_name)
{
    FILE * masters_file;

    VLOG_INFO("bond: Deleting bond %s", bond_name);

    masters_file = fopen(BONDING_MASTERS_PATH, WRITE_UPDATE);

    if(masters_file) {
        fprintf (masters_file, "-%s", bond_name);
        fclose(masters_file);
        return true;
    }
    else {
        VLOG_ERR("bond: Failed to delete bond %s in linux", bond_name);
        return false;
    }
} /* delete_linux_bond */

/**
 * Creates a Linux bond interface.
 *
 * @param bond_name is the name of the bond to be created
 * @return true if the bond was created, false otherwise
 *
 */
bool create_linux_bond(char* bond_name)
{
    char file_path[MAX_FILE_PATH_LEN];
    FILE * masters_file;

    VLOG_INFO("bond: Creating bond %s", bond_name);

    masters_file = fopen (BONDING_MASTERS_PATH, WRITE_UPDATE);

    if(masters_file) {
        fprintf (masters_file, "+%s", bond_name);
        fclose(masters_file);

        snprintf(file_path, MAX_FILE_PATH_LEN,BONDING_MODE_PATH, bond_name);
        masters_file = fopen (file_path, WRITE_UPDATE);

        if(masters_file) {
            fprintf (masters_file, BALANCE_XOR_MODE);
            fclose(masters_file);
        }
        else {
            VLOG_ERR("bond: Failed to set bonding mode in bond %s",
                     bond_name);
            return false;
        }
    }
    else {
        VLOG_ERR("bond: Failed to create bond %s in linux", bond_name);
        return false;
    }
    return true;
} /* create_linux_bond */

/**
 * Adds a slave to a Linux bond
 *
 * @param bond_name is the name of the bond.
 * @param slave_name is the name of the slave interface to
 *           be added.
 * @return true if the slave was added to the bond, false otherwise
 *
 */
bool add_slave_to_bond(char* bond_name, char* slave_name)
{
    char file_path[MAX_FILE_PATH_LEN];
    FILE * slaves_file;

    VLOG_INFO("bond: Adding bonding slave %s to bond %s",
              slave_name, bond_name);

    snprintf(file_path, MAX_FILE_PATH_LEN, BONDING_SLAVES_PATH, bond_name);

    slaves_file = fopen (file_path, WRITE_UPDATE);

    if(slaves_file) {
        fprintf (slaves_file, "+%s", slave_name);
        fclose(slaves_file);
        return true;
    }
    else {
        VLOG_ERR("bond: Failed to add interface %s to bond %s",
                 slave_name, bond_name);
        return false;
    }
} /* add_slave_to_bond */

/**
 * Checks if a slave is in a Linux bond.
 *
 * @param bond_name is the name of the bond.
 * @param slave_name is the name of the slave interface
 * @return true if the slave is in the bond, false otherwise
 *
 */
static bool check_slave_in_bond(char* bond_name, char* slave_name)
{
    FILE *fp;
    char buffer[BONDING_LINE_LEN];
    char file_path[MAX_FILE_PATH_LEN];
    bool found = false;

    snprintf(file_path, MAX_FILE_PATH_LEN, BONDING_CONFIG_PATH, bond_name);
    if((fp = fopen(file_path, READ)) == NULL) {
        VLOG_WARN("bond: Unable to open file %s", file_path);
        return false;
    }

    char slave_if[SLAVE_IF_LEN];
    snprintf(slave_if, SLAVE_IF_LEN, SLAVE_IF, slave_name);

    while(fgets(buffer, BONDING_LINE_LEN, fp) != NULL) {
        if(strstr(buffer, slave_if) != NULL) {
            found = true;
            break;
         }
    }

    if(fp) {
        fclose(fp);
    }

    return found;
} /* check_slave_in_bond */


/**
 * Removes a slave from a Linux bond.
 *
 * @param bond_name is the name of the bond.
 * @param slave_name is the name of the slave interface to
 *           be removed.
 * @return true if the slave was removed from the bond, false otherwise
 *
 */
bool remove_slave_from_bond(char* bond_name, char* slave_name)
{
    char file_path[MAX_FILE_PATH_LEN];
    FILE * slaves_file;

    VLOG_INFO("bond: Removing bonding slave %s from bond %s",
             slave_name, bond_name);

    // Don't do anything if slave is not in bond
    if(!check_slave_in_bond(bond_name, slave_name)) {
        VLOG_INFO("bond: Slave %s is not in bond %s", slave_name, bond_name);
        return false;
    }

    snprintf(file_path, MAX_FILE_PATH_LEN, BONDING_SLAVES_PATH, bond_name);

    slaves_file = fopen (file_path, WRITE_UPDATE);

    if(slaves_file) {
        fprintf (slaves_file, "-%s", slave_name);
        fclose(slaves_file);
        return true;
    }
    else {
        VLOG_ERR("bond: Failed to remove interface %s from bond %s",
                 slave_name, bond_name);
        return false;
    }
} /* remove_slave_from_bond */
