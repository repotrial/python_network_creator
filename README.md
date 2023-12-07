# KG generation using NeDRex-python package

## Installation
1. Create conda environment: ` conda create -n nedrex python=3.9`
2. Use created conda environment: ` conda activate nedrex`
3. Install dependencies: ` pip install -r requirements.txt`
4. Run network creation: ` python network_generation/generate_networks.py network_generation/configs/basic_network.yml`

<b>Attention! Execution will create a `downloads` and `networks` directory specified through the configs/basic_network.yml file. DO NOT PUSH THESE FOLDERS TO REPOSITORY!</b>

## Config file
Through the config file you can adjust all the important things to create networks. It has the following structure:

```yaml
# Config file for network generation

paths: # Paths and names to the files needed for network generation
  basename: # Name prefix of the network
  output_directory: # Directory where the networks will be saved
  download_directory: # Directory where the downloaded files will be saved
  
nodes: # Node filters
  <node-type>: # Node types can be found in entities.yml
    filter1: # First filter
      attribute: # Attribute to filter on; attributes per node type can be found in entities.yml
      operator: # Operator to use for filtering options are: 
                # ['eq', '=', 'equals', 'is', '==', 'ne', '!=", 'not', 'is not', '>', 'gt', '<', 'lt', '>=', 'ge', '<=', 'le', 'in', 'contains', 'nin', 'not contains', 'not in', 'startswith', 'endswith']  
      value: # Value to filter for
    filter2: # Second filter
       ...

edges: # Selected edges and filters
  <edge-type>: # Edge types can be found in entities.yml
    filter1: # First filter
       ...
```

## Open TODOS

- [x] Create config file based edge selection and node and edge based filtering
- [x] Improve output format, create folder for each network and give uid, save 'description file' for each uid, describing contents?
- [ ] Discuss output format of files