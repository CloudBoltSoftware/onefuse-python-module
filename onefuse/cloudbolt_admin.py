from infrastructure.models import CustomField, Server

if __name__ == '__main__':
    import django

    django.setup()

import re
import json
from common.methods import set_progress
from onefuse.admin import OneFuseManager
from utilities.models import ConnectionInfo
from utilities.logger import ThreadLogger
from django.db.models import Q
from onefuse.exceptions import OneFuseError


class CbOneFuseManager(OneFuseManager):
    """
    This is a context manager class available to CloudBolt Plugins that
    facilitates easy API connectivity from a CloudBolt host to a OneFuse host
    given the name of a ConnectionInfo object as a string. This class will only
    function when called from a CloudBolt Server.

    Example 1 making get calls with CbOneFuseManager:

        from onefuse.cloudbolt_admin import CbOneFuseManager
        with CbOneFuseManager("name-of-conn-info", logger=logger) as ofm:
            response = ofm.get("/namingPolicies/")

    Example 2 use builtin CbOneFuseManager methods:

        from onefuse.cloudbolt_admin import CbOneFuseManager
        ofm = CbOneFuseManager("name-of-conn-info", logger=logger):
        naming_json = onefuse.provision_naming(self, policy_name,
                                               properties_stack, tracking_id)

    Authentication, headers, and url creation is handled within this class,
    freeing the caller from having to deal with these tasks.

    A boolean parameter called verify_certs with default value of False, is
    provided in the constructor in case the caller wants to enable SSL cert
    validation.

    Installation Instructions:
    1. Create a Connection Info for onefuse. This must be labelled as 'onefuse'
    2. Execute the Configuration script.
        > python /var/opt/cloudbolt/proserv/xui/onefuse/configuration/setup.py

    OneFuse Parameter usage ('name' : 'value_format'):
        'OneFuse_AnsibleTowerPolicy_<executionstring>_<uniqueName>' : '<onefusehost>:<policyname>:<hosts>:<limit>'
        'OneFuse_DnsPolicy_Nic<#>' : '<onefusehost>:<policyname>:<dnszones>'
        'OneFuse_IpamPolicy_Nic<#>' : '<onefusehost>:<policyname>'
        'OneFuse_ADPolicy' : '<onefusehost>:<policyname>'
        'OneFuse_NamingPolicy' : '<onefusehost>:<policyname>'
        Property Toolkit properties:
            'OneFuse_PropertyToolkit' : '<onefusehost>:true'
            'OneFuse_SPS_<uniqueName>' : '<staticpropertysetname>'
            'OneFuse_CreateProperties_<uniqueName>' : '{"key":"<key>","value":"<value>"}'
        'OneFuse_ScriptingPolicy_<executionstring>_<uniqueName>' : '<onefusehost>:<policyname>'

        Valid Execution Strings for Ansible Tower and Scripting:
            HostnameOverwrite
            PreCreateResource
            PreApplication (only valid when configuration manager used)
            PostProvision

    """

    def __init__(self, conn_info_name: str, verify_certs: bool = None,
                 **kwargs):
        try:
            conn_info = ConnectionInfo.objects.get(
                name__iexact=conn_info_name,
                labels__name='onefuse'
            )
        except:
            err_str = (f'ConnectionInfo could not be found with name: '
                       f'{conn_info_name}, and label onefuse')
            raise OneFuseError(err_str)
        try:
            logger = kwargs["logger"]
        except KeyError:
            # If no logger is passed in, create default logger
            logger = ThreadLogger(__name__)
        try:
            source = kwargs["source"]
        except KeyError:
            # If no source is passed in, default to CloudBolt
            source = "CLOUDBOLT"
        if verify_certs is None:
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            verify_certs = False
        username = conn_info.username
        password = conn_info.password
        host = conn_info.ip
        protocol = conn_info.protocol
        port = conn_info.port
        super().__init__(
            username,
            password,
            host,
            source=source,
            protocol=protocol,
            port=port,
            verify_certs=verify_certs,
            logger=logger
        )

    def render_and_apply_properties(self, properties, resource,
                                    properties_stack):
        utilities = Utilities(self.logger)
        for key in properties.keys():
            rendered_key = self.render(key, properties_stack)
            overwrite_property = False
            try:
                if (properties_stack[rendered_key] and
                        properties_stack[rendered_key] !=
                        properties[rendered_key]):
                    # Property exists in current stack, but value is different
                    overwrite_property = True
            except KeyError:
                # Property Doesn't exist in current Properties stack
                overwrite_property = True
            # Only want to overwrite the property if new value is different
            # than existing
            if overwrite_property:
                if type(properties[key]) == dict:
                    props_key = json.dumps(properties[key])
                else:
                    props_key = properties[key]
                rendered_value = self.render(props_key, properties_stack)
                if (rendered_key is not None and rendered_key != "" and
                        rendered_value is not None and rendered_value != ""):
                    if rendered_key == 'os_build':
                        if type(resource) == Server:
                            from externalcontent.models import OSBuild
                            current_os_build = resource.os_build
                            if current_os_build.os_family:
                                print("test")
                            os_build = OSBuild.objects.get(name=rendered_value)
                            self.logger.debug(f'Setting OS build ID to: '
                                              f'{os_build.id}')
                            # Update OS Build
                            resource.os_build_id = os_build.id
                            resource.save()
                            self.logger.debug(f'Setting OS Family ID to: '
                                              f'{os_build.os_family.id}')
                            # Update OS Family
                            resource.os_family_id = os_build.os_family.id
                            resource.save()
                            # Update OS Credentials
                            os_build_attrs = os_build.osba_for_resource_handler(
                                resource.resource_handler)
                            resource.username = os_build_attrs.username
                            resource.password = os_build_attrs.password
                            resource.save()
                    elif rendered_key == 'environment':
                        # Not working. Environment appears to change, but when
                        # VM builds, it is set to original environment
                        from infrastructure.models import Environment
                        resource.environment = Environment.objects.filter(
                            name=rendered_value).first()
                    else:
                        try:
                            resource.set_value_for_custom_field(rendered_key,
                                                                rendered_value)
                        except:
                            # If adding param to the resource fails, try to
                            # create
                            utilities.check_or_create_cf(rendered_key)
                            resource.set_value_for_custom_field(rendered_key,
                                                                rendered_value)
                        self.logger.debug(f'Setting property: {rendered_key} '
                                          f'to: {rendered_value}')
                    properties_stack[rendered_key] = rendered_value
        resource.save()
        return properties_stack


class Utilities(object):
    def __init__(self, logger=None):
        if logger:
            self.logger = logger
        else:
            # If no logger is passed in, create default logger
            self.logger = ThreadLogger(__name__)

    def __enter__(self):
        return self

    def __repr__(self):
        return 'Utilities'

    def get_connection_and_policy_values(self, prefix, properties_stack):
        conn_and_policy_values = []
        pattern = re.compile(prefix)
        for key in properties_stack.keys():
            result = pattern.match(key)
            if result is not None:
                key_value = properties_stack[key]
                if len(key_value.split(":")) < 2:
                    err = (
                        f'OneFuse key was found but value is formatted wrong. '
                        f'Key: {key}, Value: {key_value}')
                    self.logger.error(err)
                    raise OneFuseError(err)
                endpoint = key_value.split(":")[0]
                policy = key_value.split(":")[1]
                try:
                    extras = key_value.split(":")[2]
                except:
                    extras = ""
                try:
                    extras2 = key_value.split(":")[3]
                except:
                    extras2 = ""
                conn_policy_value = {
                    "endpoint": endpoint,
                    "policy": policy,
                    "extras": extras,
                    "extras2": extras2
                }
                start = len(prefix)
                conn_policy_value["suffix"] = str(key[start:])
                conn_and_policy_values.append(conn_policy_value)
        return conn_and_policy_values

    def check_or_create_cf(self, cf_name, cf_type="STR"):
        # Check the existence of a custom field in CB. Create if it doesn't exist
        try:
            CustomField.objects.get(name=cf_name)
        except:
            self.logger.debug(f'Creating parameter: {cf_name}')
            cf = CustomField(
                name=cf_name,
                label=cf_name,
                type=cf_type,
                show_on_servers=True,
                description="Created by the OneFuse plugin for CloudBolt"
            )
            cf.save()
            self.logger.debug(f'Created parameter: {cf_name}')

    def get_cb_object_properties(self, resource, hook_point=None):
        # Generate a properties payload to be sent to OneFuse
        resource_values = vars(resource)
        properties_stack = {}

        # Add Resource variables to the properties stack
        for key in list(resource_values):
            if key.find("_") != 0:
                # Ignoring hidden when building the payload to pass to OneFuse
                if (
                        key.split("_")[-1] == "id"
                        and key != "id"
                        and resource_values[key] is not None
                        and resource_values[key] != ""
                ):
                    try:
                        # Get the actual object if the key is an ID key
                        f_key_name = key[0:-3]
                        key_name = f_key_name
                        key_value = getattr(resource, f_key_name)
                        if "password" in key_name.lower():
                            key_value = "******"
                    except AttributeError:
                        # If this ends up here, it failed getting the value
                        # So we will just write the ID to the payload
                        key_name = key
                        key_value = resource_values[key]
                else:
                    key_name = key
                    key_value = resource_values[key]
                properties_stack[key_name] = str(key_value)

        # Add the Custom Field (parameter) values to the properties stack
        cf_values = resource.get_cf_values_as_dict()
        cfvm = resource.get_cfv_manager()
        pwd_fields = []
        pwd_cfvs = cfvm.filter(~Q(pwd_value=None))
        for pwd_cfv in pwd_cfvs:
            pwd_fields.append(pwd_cfv.field.name)
        for key in cf_values.keys():
            key_name = key
            key_value = cf_values[key]
            if key_name in pwd_fields:
                key_value = "******"
            if type(key_value) == str:
                if (
                        (key_value.find('{') == 0 or key_value.find('[') == 0)
                        and key_value.find('{{') != 0
                ):
                    try:
                        key_value = json.loads(key_value)
                    except:
                        self.logger.warning(f'JSON parse failed, sending '
                                            f'string')
                properties_stack[key_name] = key_value
            else:
                properties_stack[key_name] = str(key_value)

        # Add additional information useful for tracking in OneFuse
        try:
            properties_stack["owner_email"] = resource.owner.user.email
        except:
            self.logger.warning("Owner email could not be determined")
        if type(resource) == Server:
            try:
                network_info = self.get_network_info(resource)
                for key in network_info.keys():
                    properties_stack[key] = network_info[key]
            except:
                self.logger.warning("Unable to determine Network Info for "
                                    "Server.")
            try:
                hardware_info = self.get_hardware_info(resource)
                for key in hardware_info.keys():
                    properties_stack[key] = hardware_info[key]
            except:
                self.logger.warning('Unable to determine Hardware Info for '
                                    'Server.')
        if hook_point is not None:
            properties_stack["hook_point"] = hook_point

        """ Commenting out until able to validate PTK
        for key in properties_stack.keys():
            if key.find("OneFuse_SPS_") == 0:
                # Replace properties with OneFuse_SPS_ with 1FPS_
                key_val = key.replace('OneFuse_SPS_', '1FPS_')
                properties_stack[key_val] = properties_stack.pop(key)
        """
        try:
            # If annotation is set, it isn't in a JSON friendly format
            properties_stack["annotation"] = ""
        except KeyError:
            pass
        return properties_stack

    def get_network_info(self, resource):
        nics = resource.nics.all()
        network_info = {}
        for nic in nics:
            index_prop = f'OneFuse_VmNic{nic.index}'
            network_info[index_prop] = {}
            try:
                network_info[index_prop]["mac"] = nic.mac
            except Exception:
                pass
            try:
                network_info[index_prop]["ipAddress"] = nic.ip
            except Exception:
                pass
            try:
                network_info[index_prop]["nicLabel"] = nic.display
            except Exception:
                pass
            try:
                network_info[index_prop]["assignment"] = nic.bootproto
            except Exception:
                pass
            try:
                network_info[index_prop]["label"] = nic.display
            except Exception:
                pass
            try:
                network_info[index_prop]["network"] = nic.network.name
            except Exception:
                pass
            try:
                network_info[index_prop]["hostname"] = resource.hostname
            except Exception:
                pass
            try:
                network_info[index_prop]["fqdn"] = (f'{resource.hostname}.'
                                                    f'{resource.dns_domain}')
                network_info[index_prop]["target"] = network_info[
                                                            index_prop]["fqdn"]
            except Exception:
                pass
            try:
                network_info[index_prop]["gateway"] = nic.network.gateway
            except Exception:
                pass
            try:
                network_info[index_prop]["dnsSuffix"] = resource.dns_domain
            except Exception:
                pass
            try:
                network_info[index_prop]["dnsServers"] = []
                if nic.network.dns1:
                    network_info[index_prop]["dnsServers"].append(
                        nic.network.dns1)
                if nic.network.dns2:
                    network_info[index_prop]["dnsServers"].append(
                        nic.network.dns2)
            except Exception:
                pass
        self.logger.debug(f'Returning network_info: {network_info}')
        return network_info

    def get_hardware_info(self, resource):
        hardware_info = {}
        index_prop = f'OneFuse_VmHardware'
        hardware_info[index_prop] = {}
        try:
            hardware_info[index_prop]["cpuCount"] = resource.cpu_cnt
        except Exception:
            pass
        try:
            hardware_info[index_prop]["memoryMB"] = resource.mem_size * 1024
        except Exception:
            pass
        try:
            hardware_info[index_prop]["memoryGB"] = resource.mem_size
        except Exception:
            pass
        try:
            power_status = resource.power_status
            if power_status.find("POWERON") > -1:
                hardware_info[index_prop]["powerState"] = "ON"
            else:
                hardware_info[index_prop]["powerState"] = "OFF"
        except Exception:
            pass
        try:
            hardware_info[index_prop][
                "platformUuid"] = resource.resource_handler_svr_id
        except Exception:
            pass
        try:
            # Once a CB server is provisioned, disk_size = total disk size for VM
            hardware_info[index_prop]["totalStorageGB"] = resource.disk_size
        except:
            pass
        self.logger.debug(f'Returning hardware_info: {hardware_info}')
        return hardware_info

    def convert_object_to_string(self, value):
        if type(value) == 'list' or type(value) == 'dict':
            self.logger.debug('Object converted to string')
            return json.dumps(value)
        return value

    def get_matching_property_names(self, prefix, properties_stack):
        matching_property_names = []
        pattern = re.compile(prefix)
        for key in properties_stack.keys():
            result = pattern.match(key)
            if result is not None:
                matching_property_names.append(key)
        self.logger.debug(f'Returning matching_property_names: '
                          f'{matching_property_names}')
        return matching_property_names

    def get_matching_properties(self, prefix, properties_stack):
        matching_properties = []
        pattern = re.compile(prefix)
        for key in properties_stack.keys():
            result = pattern.match(key)
            if result is not None:
                matching_properties.append(properties_stack[key])
        self.logger.debug(f'Returning matching_properties: '
                          f'{matching_properties}')
        return matching_properties

    def delete_output_job_results(self, managed_object, run_type):
        # Scripting and Ansible Tower can have massive response payloads, this
        # Function cleans the output to keep the MO a manageable size
        if run_type == 'ansible_tower':
            self.logger.debug(
                f'prov len: {len(managed_object["provisioningJobResults"])}')
            for i in range(len(managed_object["provisioningJobResults"])):
                managed_object["provisioningJobResults"][i]["output"] = ""
                self.logger.debug(f'AT Output deleted for provisioning.')
            self.logger.debug(
                f'de len: {len(managed_object["deprovisioningJobResults"])}')
            for i in range(len(managed_object["deprovisioningJobResults"])):
                managed_object["provisioningJobResults"][i]["output"] = ""
                self.logger.debug(f'AT Output deleted for deprovisioning.')
        elif run_type == "scripting":
            max_char_limit = 5000
            if len(json.dumps(managed_object)) > max_char_limit:
                self.logger.debug(
                    f'Object exceeds {max_char_limit} chars. Removing job '
                    f'output.')
                try:
                    managed_object["provisioningDetails"]["output"] = []
                    self.logger.debug(
                        f'Scripting Output deleted for provisioning.')
                except:
                    self.logger.debug(f'MO does not include provisioningDetails '
                                      f'to be cleaned.')
                try:
                    managed_object["deprovisioningDetails"]["output"] = []
                    self.logger.debug(
                        f'Scripting Output deleted for deprovisioning.')
                except:
                    self.logger.debug(
                        f'MO does not include deprovisioningDetails '
                        f'to be cleaned.')
        elif run_type == "pluggable_module":
            max_characters = 6000
            clean_details = len(json.dumps(managed_object)) > max_characters
            original_mo = dict(managed_object)
            safe_props = ["_links", "id", "name", "archived", "trackingId",
                          "OneFuse_PluggableModuleName", "OneFuse_Suffix",
                          "OneFuse_CBHookPointString", "endpoint",
                          "managedObjectTruncated"]
            job_results_keys = ['provisioningJobResults', 'updateJobResults',
                                'deprovisioningJobResults']

            if clean_details:
                managed_object["managedObjectTruncated"] = True
                for key in list(managed_object):
                    if key not in safe_props:
                        del managed_object[key]

                for key in job_results_keys:
                    temp_mo = dict(managed_object)
                    value_list = original_mo[key]
                    if value_list and type(value_list) == list:
                        list_length = len(value_list)
                        value = value_list[-1]
                        if type(value) == dict:
                            last_element = dict(value)
                        else:
                            last_element = value
                        last_element["originalIndexNumber"] = list_length
                        temp_mo[key] = [last_element]
                        if len(json.dumps(temp_mo)) < max_characters:
                            managed_object = dict(temp_mo)
            else:
                managed_object["managedObjectTruncated"] = False
        else:
            self.logger.debug(f'Invalid run_type: {run_type}')
        return managed_object

    def sort_deprovision_props(self, props):
        sorted_props = []
        states = [
            "PostProvision",
            "PreApplication",
            "PreCreateResource",
            "HostnameOverwrite"
        ]
        # loop through states in reverse order of provisioning
        for state in states:
            state_props = []
            for prop in props:
                if prop["OneFuse_CBHookPointString"] == state:
                    state_props.append(prop)
            # Sort state_props in reverse
            state_props.sort(key=lambda x: x["OneFuse_Suffix"], reverse=True)
            sorted_props = sorted_props + state_props
        self.logger.debug(f'Sorted deprovision properties: {sorted_props}')
        return sorted_props


if __name__ == '__main__':
    with CbOneFuseManager('onefuse') as onefuse:
        response = onefuse.get('/namingPolicies/')

    print(json.dumps(response.json(), indent=True))
