"""
Copyright (c) 2025, Oracle and/or its affiliates.
Licensed under the Universal Permissive License (UPL) 1.0 as shown at https://oss.oracle.com/licenses/upl/
"""

#!/usr/bin/python3.6.8 -Es
# -*- coding: utf-8 -*-
#
"""
Usage:
    python fss_update_cmk.py [options]

Options:
    --help      Show this help message and exit
    --dr_protection_group_ocid  Standby DR Protection Group OCID where the File Systems would be created
    --config_file    Specify the OCI Config file which has the user profile for authentication

Description:
    This script updates the KMSKeyID on the File Systems created during Switchover. 
    It reads the freeform tags from the source File System and updates the KmsKeyID on Standby accordingly
    freeform tags to be added with key as "key_regioncode" - value as "key_ocid"

Examples:
    python fss_update_cmk.py --dr_protection_group_ocid ocid1.drprotectiongroup.oc1.phx.replaceme
    freeform tags to be added as below
    key as "key_iad" - value as "replace_iad_key_ocid"
    key as "key_phx" - value as "replace_phx_key_ocid"
"""

import argparse
import datetime
import json
import logging
import os
import oci


# Define a custom formatter with a separator
class CustomFormatter(logging.Formatter):
    def format(self, record):
        original = super().format(record)
        return original + "\n"  # Add double newlines as a separator


# Retrieve Region Name to Region Code Dictionary
def get_region_dict(identity_client):
    region_dict = {}
    regions_response = identity_client.list_regions()
    for region in regions_response.data:
        region_name = region.name
        region_key = region.key
        region_dict[region_name] = region_key

    # print(region_dict)
    return region_dict


# Retrieve DRPG Member Details
def get_drpg_fss_member_details(disasterrecovery_client, drpg_ocid):
    drpg_fss_members_list = []

    try:
        response = disasterrecovery_client.get_dr_protection_group(
            dr_protection_group_id=drpg_ocid
        )
        drpg_response = response.data
        # print(f"Fetch DRPG details response - [{drpg_response}]")
        if hasattr(drpg_response, "members"):
            members = drpg_response.members
            for member in members:
                if member.member_type == "FILE_SYSTEM":
                    file_system_id = member.member_id
                    drpg_fss_members_list.append(file_system_id)
    except Exception as e:
        print("Error in fetching DRPG Details: {0}".format(e.reason))
    return drpg_fss_members_list


##########################################################################
# Main
##########################################################################
# Get Command Line Parser
parser = argparse.ArgumentParser()
parser.add_argument("--dr_protection_group_ocid", required=True)
parser.add_argument("--config_file", required=False)

args = parser.parse_args()

drpg_ocid = args.dr_protection_group_ocid
config_file = args.config_file

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

handler = logging.StreamHandler()
handler.setLevel(logging.INFO)
formatter = CustomFormatter("%(asctime)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)

start_dt = datetime.datetime.now()
logger.info("Execution Start Date - [{0}]".format(start_dt))
dt_string = start_dt.strftime("%d%m%Y%H%M%S")

if config_file is None:
    signer = oci.auth.signers.InstancePrincipalsSecurityTokenSigner()
    identity_client = oci.identity.IdentityClient(config={}, signer=signer)
    dr_client = oci.disaster_recovery.DisasterRecoveryClient(config={}, signer=signer)
    file_storage_client = oci.file_storage.FileStorageClient(config={}, signer=signer)
else:
    # Load configuration from file
    config = oci.config.from_file(config_file, "DEFAULT")
    identity_client = oci.identity.IdentityClient(config)
    dr_client = oci.disaster_recovery.DisasterRecoveryClient(config)
    file_storage_client = oci.file_storage.FileStorageClient(config)

regions_dict = get_region_dict(identity_client)

restored_file_systems_list = get_drpg_fss_member_details(dr_client, drpg_ocid)

parts = drpg_ocid.split(".")
region_identifier = parts[3]
keyname = "key_" + region_identifier

if len(restored_file_systems_list) > 0:
    logger.info(
        "File Systems count in DRProtectionGroup {}".format(
            len(restored_file_systems_list)
        )
    )
    logger.info(
        "List of File Systems in DRProtectionGroup: {}".format(
            restored_file_systems_list
        )
    )
else:
    logger.info("No File Systems found in DRProtectionGroup")

for file_system_id in restored_file_systems_list:
    file_system_response = file_storage_client.get_file_system(file_system_id)
    response_dict = json.loads(str(file_system_response.data))
    file_system_name = response_dict.get("display_name", None)
    current_cmk_id = response_dict.get("kms_key_id", None)
    file_system_tags_list = response_dict.get("freeform_tags", {})
    new_cmk_id = file_system_tags_list.get(keyname, None)

    if current_cmk_id is None or current_cmk_id == "":
        if new_cmk_id is not None:
            logger.info(
                "Updating the file system [{0}] - [{1}] with the new CMK with kmsKeyId [{2}]".format(
                    file_system_name, file_system_id, new_cmk_id
                )
            )
            update_response = file_storage_client.update_file_system(
                file_system_id,
                oci.file_storage.models.UpdateFileSystemDetails(kms_key_id=new_cmk_id),
            )
            logger.info(update_response)
        else:
            logger.info(
                "Skipping Update of the file system [{0}] - [{1}] as Key not found in Freeform Tags list [{2}]".format(
                    file_system_name, file_system_id, file_system_tags_list
                )
            )
    else:
        logger.info(
            "Skipping Update of the file system [{0}] - [{1}] as CMK already exists with kmsKeyId [{2}]".format(
                file_system_name, file_system_id, current_cmk_id
            )
        )

end_dt = datetime.datetime.now()
time_taken = round((end_dt - start_dt).total_seconds(), 2)
logger.info("Execution End Date - [{0}]".format(end_dt))
logger.info("Total Execution Time - [{0}] seconds".format(time_taken))
