import networkx as nx
"""
extractFeatures:
    Purpose:
        Extracts the features from a given tree structure, represented as an oriented graph. 
        Specifically, it identifies pairs of variable nodes and the corresponding operator paths between them.
    Input:
        t (nx.DiGraph) - NetworkX directed graph object representing the tree. Each node should 
        have an associated 'data' attribute that can be an operator or variable.
    Output:
        features (List[Tuple]) - A list of features. Each feature is represented as a tuple where the 
        first element is a pair of variables (at the leaves of the tree), and the second element is a 
        list of operators (forming a path between the variables in the tree).
"""
def extractFeatures(t):
    # find root of tree
    root = None
    for node in t.nodes:
        if t.in_degree(node) == 0:
            root = node
            break

    # extract a list of leaf nodes
    sorted = nx.topological_sort(t)
    var_nodes = []
    for node in sorted:
        if t.out_degree(node) == 0:
            var_nodes.append(node)

    features = []
    # for every pair of possible leaf nodes
    for i in range(len(var_nodes)):
        for j in range(i+1, len(var_nodes)):
            
            # find shortest path between each leaf & root
            path_a = nx.shortest_path(t, root, var_nodes[i])
            path_b = nx.shortest_path(t, root, var_nodes[j])

            # find shortest operator path between leaves
            full_path = []
            for node in reversed(path_a):
                full_path.append(node)
            last_repeat_node = None
            for node in path_b:
                if node in full_path: 
                    last_repeat_node = node
                    full_path.remove(node)
                else:
                    if last_repeat_node != None:
                        full_path.append(last_repeat_node)
                        last_repeat_node = None
                    full_path.append(node)
            full_path.pop(0)
            full_path.pop(-1)

            # extract the operator data from path nodes
            operators = []
            for node in full_path:
                operators.append(t.nodes[node]['data'])

            # list[0] = (var1, var2), list[1] = operators
            vars = (t.nodes[var_nodes[i]]['data'], t.nodes[var_nodes[j]]['data'])
            features.append([vars, operators])
    return features

# disregard variable node names, only return the corresponding operator paths between children
get_features = lambda tree : [tuple(feature_path) for children, feature_path in extractFeatures(tree)]


"""
printFeatures:
    Purpose:
        Prints the features in a human-readable format.     
    Input:
        features (List[Tuple]) - A list of features, where each feature is a tuple. 
        (pair of variables, list of operators)
    Output:
        None - Outputs the features to the console.
"""
def printFeatures(features):
    for f in features:
        var_s = "(" + str(f[0][0]) + "," + str(f[0][1]) + ")"
        op_s = "["
        for op in f[1]:
            op_s += op + ", "
        op_s = op_s[:-2]
        op_s += "]"
        print(var_s + " : " + op_s)



"""
get_feature_subsets:
    Purpose:
        Generates all possible subsets of the given feature, including the empty set.
    Input:
        feature (list) - A list of elements for which all subsets are to be generated.
    Output:
        list - A list containing all possible subsets of the input feature, including
               the empty set. Each subset is represented as a list.
"""
def get_feature_subsets(feature):
    # S(i) generates all subsets of feature[i...N]
    N = len(feature) 
    def S(i):
        if i==N-1:
            return [[feature[N-1]], []]
        to_ret = []
        for subset in S(i+1):
            include = [feature[i]] +  subset
            exclude = subset
            to_ret.append(include)
            to_ret.append(exclude)
        return to_ret
    return(S(0))




"""
is_subsequence:
    Purpose:
        Determines if the list `S` exists as a subsequence within the list `F`.
    Input:
        S (list) - Sequence to be verified as a subsequence.
        F (list) - Reference sequence against which the check is performed.
    Output:
        bool - True if `S` exists as a subsequence within `F`; otherwise, False.
"""
def is_subsequence(S, F):
    N = len(S)
    M = len(F)
    def _is_subsequence(i, j):
        if i == N:
            return True
        if j == M:
            return False
        if S[i] == F[j]:
            return _is_subsequence(i+1, j+1)
        if  S[i] != F[j]:
            return _is_subsequence(i, j+1)
    return _is_subsequence(0, 0)