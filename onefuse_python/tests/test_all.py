import sys
from os import path

ROOT_PATH = path.dirname(path.dirname(path.dirname(path.abspath(__file__))))
sys.path.append(ROOT_PATH)

from onefuse_python.onefuse_admin import OneFuseManager
from templates import template_properties, username, password, host

properties_stack = template_properties


def main():
    # Naming
    tracking_id = ''
    policy_name = 'machine'
    ofm = OneFuseManager(username, password, host)
    response_json = ofm.provision_naming(policy_name, properties_stack,
                                         tracking_id)
    hostname = response_json["name"]
    name_id = response_json["id"]
    properties_stack["hostname"] = hostname
    tracking_id = response_json["trackingId"]

    # IPAM
    policy_name = 'atlprod'
    response_json = ofm.provision_ipam(policy_name, properties_stack,
                                       tracking_id)
    ipam_id = response_json["id"]
    ip_address = response_json["ipAddress"]
    zone = response_json["dnsSuffix"]

    # DNS
    policy_name = 'prod'
    response_json = ofm.provision_dns(policy_name, properties_stack, ip_address,
                                      [zone], tracking_id)
    dns_id = response_json["id"]

    # AD
    policy_name = 'prod'
    response_json = ofm.provision_ad(policy_name, properties_stack, tracking_id)
    ad_id = response_json["id"]

    # CMDB
    policy_name = 'linux'
    response_json = ofm.provision_cmdb(policy_name, properties_stack,
                                       tracking_id)
    snow_id = response_json["id"]

    # Deprovision CMDB
    print(f'snow_id to delete: {snow_id}')
    ofm.deprovision_cmdb(snow_id)

    # Deprovision AD
    print(f'ad_id to delete: {ad_id}')
    ofm.deprovision_ad(ad_id)

    # Deprovision DNS
    print(f'dns_id to delete: {dns_id}')
    ofm.deprovision_dns(dns_id)

    # Deprovision IPAM
    print(f'ipam_id to delete: {ipam_id}')
    ofm.deprovision_ipam(ipam_id)

    # Deprovision Naming
    print(f'id: {name_id}')
    ofm.deprovision_naming(name_id)


if __name__ == "__main__":
    main()
