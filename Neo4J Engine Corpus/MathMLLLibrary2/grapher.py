import networkx as nx

"""
subMissingGlyph:
    Purpose: 
        substitute an unrenderable unicode character with an adequate renderable replacement
    Input:
        c (char) - unrenderable unicode character
    Ourput:
        renderable replacement char
"""
def subMissingGlyph(c):
    uni = ord(c)
    if uni >= 119860 and uni <= 119885:     # mathematical italic capital
        new_uni = uni - (119860 - ord('A'))
        return chr(new_uni)
    elif uni >= 119886 and uni <= 119911:   # mathematical italic small
        new_uni = uni - (119886 - ord('a'))
        return chr(new_uni)
    elif uni >= 120572 and uni <= 120596:   # Greek characters
        new_uni = uni - (120572 - 0x03B1)
        return chr(new_uni)
    elif uni >= 119834 and uni <= 119859:   # mathematical bold small
        new_uni = uni - (119834 - ord('a'))
        return chr(new_uni)
    elif uni >= 119964 and uni <= 119989:   # mathematical script capital
        new_uni = uni - (119964 - ord('A'))  
        return chr(new_uni)
    elif uni >= 119808 and uni <= 119833:   # mathematical bold capital
        new_uni = uni - (119808 - ord('A'))
        return chr(new_uni)
    else:
        return chr(uni)

######################################################################################################################################

"""
graphTree:
    Purpose:
        convert a Node* based tree to a graphable networkX object
    Input:
        root (Node*): root of contentML Tree
    Output:
        G (DiGraph) plottable by networkX
"""
def graphTree(root):
    # populates G with a Node* to the root of a content ML tree, & node's parent id
    def _graphTree(G, node, parent_id):
        if node == None:
            return
        node_id = len(G.nodes())
        if len(node.children) == 0:
            # Create a renderable label for the children node
            new_label = ""
            for char in node.value:
                new_label += subMissingGlyph(char)
            node.value = new_label
        G.add_node(node_id, data = node.value)

        if parent_id !=-1: 
            G.add_edge(parent_id, node_id)

        for child in node.children:
            _graphTree(G, child, node_id)

    # Generate Network X Tree to Plot        
    G = nx.DiGraph()
    _graphTree(G, root, -1)
    return G