.. meta::
   :description: Create VPC (using OpenStack API) as a prerequisite for other tests
   :keywords: vpc, network
   :revision: 1
   :applicable: regression,apimon,terraform,ansible


Workflow:

- Create router
.. rest_method:: create_router
   :name: test_router
   :description: test_router_description - seems not supported by otc
   :admin_state_up: true
   :external_gateway_info:
     network_id: ID_OF_ADMIN_EXTERNAL_NET
     enable_snat: true
   :out:
- save return info

- create network
.. rest_method::
...

- create subnet
.. sdsdsdssss#


- evaluate create_router response:
  - ensure response.description = "test_router_description - seems not supported by otc"

- delete subnet
  ......
