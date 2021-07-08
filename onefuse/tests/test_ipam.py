import sys
from os import path
ROOT_PATH = path.dirname(path.dirname(path.dirname(path.abspath(__file__))))
sys.path.append(ROOT_PATH)


from onefuse_python.onefuse_admin import OneFuseManager
from templates import template_properties, username, password, host

policy_name = 'atlprod'
hostname = 'tst-hstnm-123'
properties_stack = template_properties
properties_stack["hostname"] = hostname
tracking_id = ''

# Make the call to provision the name
ofm = OneFuseManager(username, password, host)
response_json = ofm.provision_ipam(policy_name, properties_stack, tracking_id)
print(f'response: {response_json}')
id = response_json["id"]
print(f'id to delete: {id}')
ofm.deprovision_ipam(id)
