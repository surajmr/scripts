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
 
 
