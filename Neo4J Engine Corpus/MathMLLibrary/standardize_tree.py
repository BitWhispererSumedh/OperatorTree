import networkx as nx

# list of common constants in hex
COMMON_CONSTANTS = [
    0x03C0 # pi
]



"""
isVar:
    Purpose:
        Checks if the given name is a variable according to specific rules.
        A name is considered a variable if it's a single alphabet character
        and is not in a predefined set of common constants.
    Input:
        name (str) - The name to check if it's a variable.
    Output:
        bool - Returns True if the name is considered a variable, False otherwise.
"""
def isVar(name):
    if len(name) != 1:
        return False
    if not name.isalpha():
        return False
    if ord(name) in COMMON_CONSTANTS:
        return False
    return True



"""
standardizeOpTree:
    Purpose:
        Standardizes the variable names in a given operation tree. All the variable
        nodes are renamed sequentially using the alphabetical characters starting
        from 'a'. The operation tree's topology remains the same.
    Input:
        t (nx.Graph) - A networkX graph object representing the operation tree where
                       variable nodes have out-degree 0 and are identified by the 'data' attribute.
    Output:
        nx.Graph - A new graph object with standardized variable names.
"""
def standardizeOpTree(t):
    # collect a list of seen variable names
    var_nodes = set()
    used_names = set()
    for node in t.nodes():
        if t.out_degree(node) == 0:
            name = t.nodes[node]['data']
            if isVar(name):
                var_nodes.add(node)
                used_names.add(name)

    # replace var names with standardized substitutions
    s = t.copy()
    sorted = nx.topological_sort(t)
    substitutions = {}
    idx = ord('a')
    for node in sorted:
        if node not in var_nodes:
            continue

        name = t.nodes[node]['data']
        if name in substitutions.keys():
            s.nodes[node]['data'] = substitutions[name]
        else:
            s.nodes[node]['data'] = chr(idx)
            substitutions.update({name:chr(idx)})
            idx += 1
    
    # return standardized opTree
    return s