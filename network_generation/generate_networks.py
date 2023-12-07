import os, sys
import logging
import time
import yaml

from network_generation.utils.nedrex_utils import download_nodes, download_edges, list_edge_types, list_node_types, filter_nodes, filter_edges, \
    get_edge_node_keys_and_bidirection, node_is_gene, get_coll_attributes

node_store = dict()
gene_protein_map = dict()
CONFIG = dict()
DEFAULT_CONFIG = dict()


def get_node_types():
    try:
        requested_nodes = set(CONFIG.get('nodes', dict()).keys())
        existing_nodes = set(DEFAULT_CONFIG.get('nodes', {}).keys())
        unknown_nodes = requested_nodes.difference(existing_nodes)
        if len(unknown_nodes) > 0:
            logging.warning(f"Unknown node types: {', '.join(unknown_nodes)}")
        return requested_nodes.intersection(existing_nodes).union({'gene'})
    except:
        return set()


def get_edge_types():
    try:
        requested_edges = set(CONFIG.get('edges', {}).keys())
        existing_edges = set(DEFAULT_CONFIG.get('edges', {}).keys())
        unknown_edges = requested_edges.difference(existing_edges)
        if len(unknown_edges) > 0:
            logging.warning(f"Unknown edge types: {', '.join(unknown_edges)}")
        return requested_edges.intersection(existing_edges)
    except:
        return set()


def run(config_file, loglevel='INFO'):
    setup_logging(loglevel)
    start = time.time()
    logging.info("Reading config files")
    import_default_config(os.path.join(os.path.split(os.path.realpath(__file__))[0], "entities.yml"))
    import_config(config_file)
    output_dir = os.path.join(get_config_paths('output_directory', 'networks'),
                              get_config_paths('basename', 'nedrex_network') + "_" + str(int(start)))
    download_dir = get_config_paths('download_directory', 'downloads')
    logging.debug("Creating output directories")
    os.system(f"mkdir -p {output_dir}")
    logging.info(f"Output directory: {output_dir}")
    logging.debug("Creating download directory")
    if not os.path.exists(download_dir):
        os.makedirs(download_dir)
    logging.info(f"Download directory: {download_dir}")
    logging.info(f"Available node types: {', '.join(list_node_types())}")
    logging.info(f"Available edge types: {', '.join(list_edge_types())}")

    download_data(download_dir)

    import_nodes(download_dir)

    import_gene_protein_map(download_dir)

    file_prefix = os.path.join(output_dir, str(int(start)) + "_")
    create_network(download_dir, file_prefix)

    create_predict_file(download_dir, file_prefix)

    save_config_file(file_prefix)

    logging.info(f"Finished in {time.time() - start} seconds")
    return output_dir


def setup_logging(loglevel):
    getattr(logging, loglevel.upper())
    numeric_level = getattr(logging, loglevel.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError('Invalid log level: %s' % loglevel)
    logging.basicConfig(level=numeric_level)


def import_config(config_file):
    with open(config_file) as fh:
        CONFIG.update(yaml.load(fh, Loader=yaml.FullLoader).get('network'))


def import_default_config(default_config_file):
    with open(default_config_file) as fh:
        DEFAULT_CONFIG.update(yaml.load(fh, Loader=yaml.FullLoader))


def download_data(download_dir):
    logging.info("Downloading data")
    for node in get_node_types():
        download_nodes(node, download_dir)
    default_edges = {"protein_encoded_by_gene", "drug_has_indication"}
    for edge in set(CONFIG.get('edges', {}).keys()).union(default_edges):
        download_edges(edge, download_dir)


def get_config_paths(key, default):
    value = CONFIG.get('paths', dict()).get(key, default)
    return value


def get_filter(attribute, operator, value):
    if operator == 'eq' or operator == '=' or operator == 'equals' or operator == 'is' or operator == '==':
        return lambda node: node[attribute] == value
    if operator == 'ne' or operator == '!=' or operator == 'not' or operator == 'is not':
        return lambda node: node[attribute] != value
    if operator == '>' or operator == 'gt':
        return lambda node: node[attribute] > value
    if operator == '<' or operator == 'lt':
        return lambda node: node[attribute] < value
    if operator == '>=' or operator == 'ge':
        return lambda node: node[attribute] >= value
    if operator == '<=' or operator == 'le':
        return lambda node: node[attribute] <= value
    if operator == 'in' or operator == 'contains':
        return lambda node: value in node[attribute]
    if operator == 'nin' or operator == 'not in':
        return lambda node: value not in node[attribute]
    if operator == 'startswith':
        return lambda node: node[attribute].startswith(value)
    if operator == 'endswith':
        return lambda node: node[attribute].endswith(value)
    logging.warning(f"Unknown filter: {attribute} {operator} {value}")
    return lambda node: True


def get_filter_funct(type, collname):
    filters = CONFIG.get(type).get(collname)
    if not filters:
        return lambda node: True
    filter_list = []
    for filter in filters.values():
        try:
            filter_list.append(get_filter(filter['attribute'], filter['operator'], filter['value']))
        except:
            pass
    filter_list.append(lambda node: True)

    def f(node):
        for filter in filter_list:
            if not filter(node):
                return False
        return True

    return f


def import_gene_protein_map(download_dir):
    logging.info("Importing gene-protein map")
    filter = get_edge_filter_funct('protein_encoded_by_gene')
    for (protein, gene) in filter_edges('protein_encoded_by_gene', download_dir, filter,
                                        ('sourceDomainId', 'targetDomainId'), False):
        gene_protein_map[gene] = protein
    logging.info(f"Imported {len(gene_protein_map)} gene-protein mappings")


def get_edge_filter_funct(coll_type):
    node_types = DEFAULT_CONFIG.get('edges').get(coll_type)
    if node_types is None:
        logging.warning("Unknown edge type: {coll_type}")
        return lambda edge: True

    def filter(edge):
        for (attribute, node_type) in node_types.items():
            if node_type in node_store.keys():
                if edge[attribute] not in node_store[node_type]:
                    return False
        return True

    return lambda edge: filter(edge) and get_filter_funct('edges', coll_type)(edge)


def prepare_nodes(coll_name, download_dir):
    logging.info(f"Importing and filtering {coll_name} nodes")
    for node_id in filter_nodes(coll_name, download_dir, get_filter_funct('nodes', coll_name)):
        node_store[coll_name].add(node_id)
    logging.info(f"Stored {len(node_store[coll_name])} {coll_name} nodes")


def translate_node_ids(node1, node2, node1_is_gene, node2_is_gene):
    if node1_is_gene:
        node1 = gene_protein_map[node1]
    if node2_is_gene:
        node2 = gene_protein_map[node2]
    return (node1, node2)


def create_edges(coll_name, download_dir, output_file_writer):
    logging.debug(f"Importing, filtering and writing {coll_name} edges")
    node_keys, bidirection = get_edge_node_keys_and_bidirection(coll_name)
    (node1_is_gene, node2_is_gene) = node_is_gene(coll_name)
    filter = get_edge_filter_funct(coll_name)
    for (node1, node2) in filter_edges(coll_name, download_dir, filter, node_keys, bidirection):
        try:
            (node1, node2) = translate_node_ids(node1, node2, node1_is_gene, node2_is_gene)
            output_file_writer.write(f"{node1},{coll_name},{node2}\n")
        except:
            continue
    logging.debug(f"Written {coll_name} edges to output file.")


def import_nodes(download_dir):
    logging.info("Importing data")
    for node in get_node_types():
        node_store[node] = set()
        prepare_nodes(node, download_dir)


def create_network(download_dir, prefix):
    logging.info("Creating network")
    network_file = prefix + "train.csv"
    predict_edge = "drug_has_indication"
    with open(network_file, "w") as network_fh:
        for edge in get_edge_types().difference({predict_edge}):
            create_edges(edge, download_dir, network_fh)


def save_config_file(prefix):
    config_file = prefix + "config.yml"
    with open(config_file, "w") as fh:
        yaml.dump(CONFIG, fh)


def create_predict_file(download_dir, prefix):
    predict_edge = "drug_has_indication" # TODO move to config file
    logging.info(f"Creating truth file with {predict_edge} edges")
    network_file = prefix + 'truth.csv'
    with open(network_file, "w") as network_fh:
        create_edges(predict_edge, download_dir, network_fh)


def __main__(args):
    config_file = args[1]
    run(config_file)


if __name__ == '__main__':
    __main__(sys.argv)
