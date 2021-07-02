import sys
import random as r
from os import path

ROOT_PATH = path.dirname(path.dirname(path.dirname(path.abspath(__file__))))
sys.path.append(ROOT_PATH)

from onefuse_python.onefuse_admin import OneFuseManager
from templates import template_properties, username, password, host

policy_name = 'cloud_server'
properties_stack = {
    "env": "test",
    "app": "linux",
    "size": "small",
    "location": "atl",
    "deploymentOwner": "mbombard"
}
deployment_name = f'Python-Deployment-{r.randint(0, 9999)}'
tracking_id = ''

# Make the call to provision the name
ofm = OneFuseManager(username, password, host)
response_json = ofm.provision_vra(policy_name, properties_stack,
                                  deployment_name, tracking_id)
print(f'response: {response_json}')
name_id = response_json["id"]
print(f'id: {name_id}')
ofm.deprovision_vra(name_id)
