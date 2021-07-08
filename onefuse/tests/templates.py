username = 'admin'
password = 'admin'
host = 'se-1f-demo-1-3.sovlabs.net'

template_properties = {
    "id": "4220",
    "hostname": "pp-atltlap101",
    "ip": "10.30.30.145",
    "mac": "00:50:56:a5:ba:a2",
    "os_build": "CentOS 7.2",
    "cpu_cnt": "1",
    "disk_size": "16",
    "mem_size": "1",
    "hw_rate": "15.0000000000",
    "sw_rate": "3.5000000000",
    "extra_rate": "0E-10",
    "total_rate": "18.5000000000",
    "notes": "Built by Mike Bombard using CloudBolt https://cb-mb-01.sovlabs.net/ on 5/31/21 [Job ID=25664, Order ID=269]",
    "add_date": "2021-05-31 11:41:45.608483",
    "environment": "OneFuse",
    "owner": "Mike Bombard",
    "status": "ACTIVE",
    "group": "piedpiper",
    "provision_engine_svr_id": "",
    "provision_engine_id": "None",
    "resource_handler_svr_id": "42258454-8794-7a93-0ae6-ffe5a27f709a",
    "resource_handler": "vCenter",
    "power_status": "POWERON",
    "os_family": "Linux -> CentOS",
    "resource_id": "None",
    "service_item": "Server",
    "OneFuse_ADPolicy": "onefuse:dev",
    "annotation": "Built by {{ server.owner }} using CloudBolt {{ portal.site_url|default_if_none:\"\" }} on {{ server.add_date|date:\"SHORT_DATE_FORMAT\" }} [Job ID={{ job.id }}, Order ID={{ order.id }}]",
    "time_zone": "US/Pacific",
    "OneFuse_DnsPolicy_Nic0": "onefuse:prod:infoblox851.sovlabs.net",
    "custom_storage_account_arm": "False",
    "OneFuse_IpamPolicy_Nic0": "onefuse:atltest",
    "sc_nic_0": "dvs_SovLabs_330_10.30.30.0_24",
    "password": "******",
    "OneFuse_NamingPolicy": "onefuse:machine",
    "OneFuse_PropertyToolkit": "onefuse:true",
    "sc_nic_0_ip": "10.30.30.145",
    "OneFuse_SPS_All_Modules": "ptk_all_modules",
    "OneFuse_SPS_App": "ptk_app_apache_ansible_tower",
    "OneFuse_SPS_Env": "ptk_env_test",
    "OneFuse_SPS_Location": "ptk_location_atl",
    "OneFuse_SPS_Size": "ptk_size_small",
    "nameApp": "ap",
    "ipamApp": "web",
    "OneFuse_SPS_OS": "ptk_os_centos7",
    "deployNameApp": "APACHE",
    "username": "root",
    "nameEnv": "t",
    "folderEnv": "TEST",
    "ipamEnv": "test",
    "ouEnv": "TST",
    "sgEnv": "test",
    "dnsPolicy": "prod",
    "adPolicy": "dev",
    "location": "por",
    "dnsSuffix": "infoblox851.sovlabs.net",
    "deployNameEnv": "Test",
    "s3NameEnv": "test",
    "nameLocation": "atl",
    "ipamLocation": "atl",
    "Global_Props": {
      "memoryGB": "1",
      "cpuCount": "1"
    },
    "vmware_disk_type": "Thin Provision",
    "memoryGB": "1",
    "cpuCount": "1",
    "familyOS": "linux",
    "nameOS": "l",
    "folderName": "VRM-BACKUPEXCLUDED/demo/PiedPiper/TEST",
    "OneFuse_SPS_GlobalProperties": "ptk_globalproperties",
    "folderGroup": "PiedPiper",
    "nameGroup": "pp",
    "ouGroup": "PiedPiper",
    "s3NameGroup": "piedpiper",
    "OneFuse_SPS_Group": "ptk_group_piedpiper",
    "OneFuse_Naming": {
      "_links": {
        "self": {
          "href": "/api/v3/onefuse/customNames/130/",
          "title": "pp-atltlap101"
        },
        "workspace": {
          "href": "/api/v3/onefuse/workspaces/2/",
          "title": "Default"
        },
        "policy": {
          "href": "/api/v3/onefuse/namingPolicies/8/",
          "title": "machine"
        },
        "jobMetadata": {
          "href": "/api/v3/onefuse/jobMetadata/726/",
          "title": "Job Metadata Record id 726"
        }
      },
      "name": "pp-atltlap101",
      "id": 130,
      "dnsSuffix": "infoblox851.sovlabs.net",
      "trackingId": "52fef98b-d19d-440a-9e8b-e05497739d9e",
      "endpoint": "onefuse"
    },
    "OneFuse_Ipam_Nic0": {
      "_links": {
        "self": {
          "href": "/api/v3/onefuse/ipamReservations/62/",
          "title": "10.30.30.145"
        },
        "workspace": {
          "href": "/api/v3/onefuse/workspaces/2/",
          "title": "Default"
        },
        "policy": {
          "href": "/api/v3/onefuse/ipamPolicies/5/",
          "title": "atltest"
        },
        "jobMetadata": {
          "href": "/api/v3/onefuse/jobMetadata/727/",
          "title": "Job Metadata Record id 727"
        }
      },
      "id": 62,
      "ipAddress": "10.30.30.145",
      "hostname": "pp-atltlap101.infoblox851.sovlabs.net",
      "ingestEvent": None,
      "primaryDns": "10.30.0.11",
      "secondaryDns": "10.30.0.12",
      "dnsSuffix": "infoblox851.sovlabs.net",
      "dnsSearchSuffixes": "infoblox851.sovlabs.net,sovlabs.net",
      "nicLabel": None,
      "subnet": "10.30.30.0/24",
      "gateway": "10.30.30.1",
      "network": "dvs_SovLabs_330_10.30.30.0_24",
      "netmask": "255.255.255.0",
      "trackingId": "52fef98b-d19d-440a-9e8b-e05497739d9e",
      "endpoint": "onefuse"
    },
    "dns_domain": "infoblox851.sovlabs.net",
    "OneFuse_AD_State": "final",
    "OneFuse_Dns_Nic0": {
      "_links": {
        "self": {
          "href": "/api/v3/onefuse/dnsReservations/54/",
          "title": "pp-atltlap101"
        },
        "workspace": {
          "href": "/api/v3/onefuse/workspaces/2/",
          "title": "Default"
        },
        "policy": {
          "href": "/api/v3/onefuse/dnsPolicies/6/",
          "title": "prod"
        },
        "jobMetadata": {
          "href": "/api/v3/onefuse/jobMetadata/730/",
          "title": "Job Metadata Record id 730"
        }
      },
      "name": "pp-atltlap101",
      "id": 54,
      "records": [
        {
          "type": "host",
          "name": "pp-atltlap101.infoblox851.sovlabs.net",
          "value": "10.30.30.145"
        }
      ],
      "trackingId": "52fef98b-d19d-440a-9e8b-e05497739d9e",
      "endpoint": "onefuse"
    },
    "OneFuse_AnsibleTowerPolicy_PostProvision_apache": "onefuse:linux_install_apache:pp-atltlap101.infoblox851.sovlabs.net:pp-atltlap101.infoblox851.sovlabs.net",
    "OneFuse_AD": {
      "_links": {
        "self": {
          "href": "/api/v3/onefuse/microsoftADComputerAccounts/55/",
          "title": "pp-atltlap101"
        },
        "workspace": {
          "href": "/api/v3/onefuse/workspaces/2/",
          "title": "Default"
        },
        "policy": {
          "href": "/api/v3/onefuse/microsoftADPolicies/2/",
          "title": "dev"
        },
        "jobMetadata": {
          "href": "/api/v3/onefuse/jobMetadata/733/",
          "title": "Job Metadata Record id 733"
        }
      },
      "name": "pp-atltlap101",
      "id": 55,
      "state": "final",
      "buildOu": "OU=PiedPiper,OU=TST,OU=build,DC=2k19ad,DC=sovlabs,DC=net",
      "finalOu": "OU=PiedPiper,OU=TST,OU=final,DC=2k19ad,DC=sovlabs,DC=net",
      "securityGroups": [
        "CN=testDemoComputers,OU=Groups,OU=SovLabs,DC=2k19ad,DC=sovlabs,DC=net"
      ],
      "trackingId": "52fef98b-d19d-440a-9e8b-e05497739d9e",
      "endpoint": "onefuse"
    },
    "domain_name_server": "10.30.0.11,10.30.0.12",
    "OneFuse_CreateProperties_Compliance": {
      "key": "OneFuse_SPS_Compliance",
      "value": ""
    },
    "OneFuse_AnsibleTower_apache": {
      "_links": {
        "self": {
          "href": "/api/v3/onefuse/ansibleTowerDeployments/4/",
          "title": "Ansible Tower Deployment id 4"
        },
        "workspace": {
          "href": "/api/v3/onefuse/workspaces/2/",
          "title": "Default"
        },
        "policy": {
          "href": "/api/v3/onefuse/ansibleTowerPolicies/2/",
          "title": "linux_install_apache"
        },
        "jobMetadata": {
          "href": "/api/v3/onefuse/jobMetadata/752/",
          "title": "Job Metadata Record id 752"
        }
      },
      "id": 4,
      "limit": "pp-atltlap101.infoblox851.sovlabs.net",
      "inventoryName": "Demo Inventory",
      "hosts": [
        "pp-atltlap101.infoblox851.sovlabs.net"
      ],
      "provisioningJobResults": [
        {
          "output": "",
          "status": "successful",
          "jobTemplateName": "install httpd"
        }
      ],
      "deprovisioningJobResults": {},
      "archived": False,
      "trackingId": "52fef98b-d19d-440a-9e8b-e05497739d9e",
      "endpoint": "onefuse",
      "OneFuse_CBHookPointString": "PostProvision",
      "OneFuse_Suffix": "apache"
    },
    "OneFuse_ServiceNowCmdbPolicy": "onefuse:linux",
    "OneFuse_CreateProperties_Domain": {
      "key": "domain",
      "value": "2k19ad.sovlabs.net"
    },
    "content_library": "('', '')",
    "domain": "2k19ad.sovlabs.net",
    "domain_username": "SOVLABS.NET\\vrasvc",
    "domain_password": "******",
    "OneFuse_Tracking_Id": "52fef98b-d19d-440a-9e8b-e05497739d9e",
    "owner_email": "mbombard@sovlabs.com",
    "OneFuse_VmNic0": {
      "mac": "00:50:56:a5:ba:a2",
      "ipAddress": "10.30.30.145",
      "nicLabel": "NIC 1",
      "assignment": "none",
      "label": "NIC 1",
      "network": "dvs_SovLabs_330_10.30.30.0_24",
      "hostname": "pp-atltlap101",
      "fqdn": "pp-atltlap101.infoblox851.sovlabs.net",
      "gateway": "10.30.30.1",
      "dnsSuffix": "infoblox851.sovlabs.net",
      "dnsServers": [
        "10.30.0.11",
        "10.30.0.12"
      ]
    },
    "OneFuse_VmHardware": {
      "cpuCount": 1,
      "memoryMB": 1024,
      "memoryGB": 1,
      "powerState": "ON",
      "platformUuid": "42258454-8794-7a93-0ae6-ffe5a27f709a",
      "totalStorageGB": 16
    },
    "hook_point": "post_provision"
  }
