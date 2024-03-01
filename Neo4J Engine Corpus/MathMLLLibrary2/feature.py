"""
find_feature_paths:
    Purpose:
        Finds the paths in a tree that match a given sequence of features. 
    Input:
        tree (nx.Graph) - NetworkX graph object representing the tree.
        title (str, optional) - Title for reference. Default is an empty string.
        feature_list (List) - List of features to find in the tree. 
    Output:
        special_nodes (set) - set of node IDs that are part of valid paths 
                              corresponding to the given feature sequence.
"""
def find_feature_paths(tree, title="", feature_list = []):
    # return node value given node id
    val = lambda node : tree.nodes[node]['data']  
    
    # find all out and in neighbors of node
    out = lambda node : list(tree.successors(node)) +  list(tree.predecessors(node))

    f_to_id = {}                # Key = Features, Value = node_id
    f_set = set(feature_list)       # O(m)
    f_path = []                 # f_path[i] is a list of ids with value features[i] s.t. each id in 
                                # f_path[i+1] is a neighbor of at least 1 element of f_path[i]

    # O(n)
    # 0. Hash locations of all nodes_ids corresponding to each feature
    for id in tree:
        key, value = val(id), id
        if val(id) in f_set:
            if key not in f_to_id:
                f_to_id[key] = set()
            f_to_id[key].add(id)

    # 1. feature_path[i] holds a list of node_ids with value feature_list[i] such that every id in feature_path[i+1] 
    # is a neighbor of at least 1 element of feature_path[i]
    # O(n)
    if feature_list[0] not in f_to_id:
        return set()
    else:
        feature_path = [f_to_id[feature_list[0]]] 
    for idx in range(len(feature_list)-1):
        cur_f = feature_list[idx]
        next_f = feature_list[idx+1] 
        if cur_f not in f_to_id:
            break
        cur_ids = f_to_id[cur_f]

        #next_ids = neighbors of current_id whose feature = next_feature
        next_ids = set()
        for cur_id in cur_ids:
            for node_id in out(cur_id):
                if val(node_id) == next_f:
                    next_ids.add(node_id)
        feature_path.append(next_ids)

    '''
    VP(i) finds all valid paths in f_paths[i...N-1]
        General Case:
            S'pose all valid paths from i+1 were found (ie. VP(i+1))
            match all paths where where the first vetex in VP(i+1) is aneighbor of a vertex in fp(i)
    '''
    # 2. Find all valid paths after redcuing search space
    N = len(feature_path)
    def VP(i):
        if i == len(feature_path)-1:
            return [[node_id] for node_id in feature_path[i]]
        to_ret = []
        nxt_valid_paths = VP(i+1)
        for node_id in feature_path[i]:
            for path in nxt_valid_paths:
                if path!= [] and path[0] in out(node_id):
                    to_ret.append([node_id] + path)
        return to_ret
    
    # 3. Determine the set of nodes to color
    special_paths = VP(0)
    special_nodes = set()
    for sp in special_paths:
        for node in sp:
            special_nodes.add(node)
    return special_nodes