import os
import logging
from typing import Generator, Dict, Any, Tuple

from tqdm import tqdm
import nedrex
from nedrex.core import iter_nodes, iter_edges, get_api_key, get_edge_types, get_node_types, get_collection_attributes

nedrex.config.set_url_base("https://api.nedrex.net/licensed")
nedrex.config.set_api_key(get_api_key(accept_eula=True))


def iter_node_collection(coll_name, callback):
    logging.info(f"Downloading {coll_name} nodes")
    for node in tqdm(iter_nodes(coll_name)):
        callback(node)
    logging.info(f"Finished downloading {coll_name} nodes")


def list_node_types():
    return get_node_types()


def list_edge_types():
    return get_edge_types()


def get_coll_attributes(coll_name):
    return get_collection_attributes(coll_name)


def iter_edge_collection(coll_name, callback):
    logging.info(f"Downloading {coll_name} edges")
    for edge in tqdm(iter_edges(coll_name)):
        callback(edge)
    logging.info(f"Finished downloading {coll_name} edges")


def get_file_name(coll_name, download_directory):
    return f"{download_directory}/{coll_name}_raw.tsv"


def download_nodes(coll_name, output_dir):
    file_name = get_file_name(coll_name, output_dir)
    if os.path.exists(file_name):
        logging.info(f"Using {coll_name} nodes from cache")
        return
    with open(file_name, "w") as fh:
        iter_node_collection(coll_name, lambda node: fh.write(f"{node}\n"))


def download_edges(coll_name, output_dir):
    file_name = get_file_name(coll_name, output_dir)
    if os.path.exists(file_name):
        logging.info(f"Using {coll_name} edges from cache")
        return
    with open(file_name, "w") as fh:
        iter_edge_collection(coll_name, lambda edge: fh.write(f"{edge}\n"))


def read_nedrex_file(file_name) -> Generator[Dict[str, Any], None, None]:
    with open(file_name) as fh:
        for line in fh.readlines():
            yield eval(line)


def filter_nodes(coll_name, output_dir, filter_func) -> Generator[str, None, None]:
    file_name = get_file_name(coll_name, output_dir)
    logging.info(f"Importing {coll_name} nodes")
    for node in tqdm(read_nedrex_file(file_name)):
        if filter_func(node):
            yield node['primaryDomainId']

def filter_edges(coll_name, output_dir, filter_func, node_names, bidirectional=False) -> Generator[Tuple[str,str], None, None]:
    file_name = get_file_name(coll_name, output_dir)
    logging.info(f"Importing {coll_name} edges")
    for edge in tqdm(read_nedrex_file(file_name)):
        if filter_func(edge):
            yield edge[node_names[0]], edge[node_names[1]]
            if bidirectional:
                yield edge[node_names[1]], edge[node_names[0]]



def get_edge_node_keys_and_bidirection(edge):
    if edge in ['protein_interacts_with_protein','molecule_similarity_molecule']:
        return ('memberOne', 'memberTwo'), True
    return ('sourceDomainId', 'targetDomainId'), False

def node_is_gene(edge):
    if edge in ['gene_associated_with_disorder', 'gene_expressed_in_tissue']:
        return (True, False)
    elif edge in ['protein_encoded_by_gene','variant_affects_gene']:
        return (False, True)
    return (False, False)

