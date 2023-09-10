from networkx.drawing.nx_agraph import graphviz_layout
import matplotlib.font_manager as fm
from functools import lru_cache
import matplotlib.pyplot as plt
from bs4 import BeautifulSoup
from lxml import etree as ET
from copy import deepcopy
from matplotlib import rc
import networkx as nx
import unicodedata
import string


#####################################################  Public Interface Support ####################################################

#####################################################################################################################################


#####################################################  MathML String Processing   ##################################################### 

# unnecessary attributes to remove from mathml string
REMOVE_ATTRIBUTES = ["id", "xref", "type", "cd", "encoding"]
# tags to skip
skip = {'math', 'semantics', 'annotation', 'annotation-xml'}
# operator tags - first child is operator, remaining children are operands
op = {'apply','ci', 'cn', 'cs', 'csymbol'}
# terminal tags - tags with no children (except few instances), usually represent variables in equation
term = {'ci', 'cn', 'cs', 'csymbol'}
# some latex commands won't work in matplotlib because the required package isn't installed
BAD_COMMANDS = {
    "\\cal", "\\text", "\\hbox", "\\nolimits", "\\mathop", "\\mathrmsl"
}
# replace some latex with equivalents that will render in matplotlib
REPLACE_COMMANDS = {
    "\\tfrac": "\\frac",
    "scal": "\\mathrm{scal}",
    "  ": " ",
    "'\\mathrm": "\\mathrm", # Fixing misplaced single quote
}


# veiw text contents of eree objects
def pretty_print(et, indent=4):
    et_copy = deepcopy(et)
    input_xml_str = ET.tostring(et_copy).decode('utf-8').strip()
    def pretty_recursive(elem, level=0):
        i = "\n" + level * " " * indent
        internal_indent = "\n" + (level + 1) * " " * indent
        result = i + '<' + elem.tag + '>'
        if elem.text and elem.text.strip():
            result += internal_indent + elem.text.strip()
        for child in elem:
            result += pretty_recursive(child, level + 1)
        if elem.tail and elem.tail.strip():
            result += internal_indent + elem.tail.strip()
        result += i + '</' + elem.tag + '>'
        return result
    root = ET.fromstring(input_xml_str)
    print(pretty_recursive(root))



"""
toMathMLStrings:
    Purpose:
        extract all block equations in a given html document to mathML strings
    Input: 
        html_filename (str) -  article html filename
    Output:
        list of [mathml string, latex alttext] for each "block" equation
"""
def toMathMLStrings(html_filename):
    f = open(html_filename, "r")
    xml = f.read()
    soup = BeautifulSoup(xml, features="lxml")
    mathml_strings = []
    for mms in soup.find_all("math"):
        # skip non-block equations
        # a block equation gets its own line in the article (as opposed to an "inline" equation)
        if mms["display"] == "block": 
            # remove unnecessary attributes
            for attr in REMOVE_ATTRIBUTES: 
                [s.attrs.pop(attr) for s in mms.find_all() if attr in s.attrs]
            # prettify fixes mismatched tags and formats the HTML better
            mathml_strings.append([mms.prettify(), mms["alttext"]])
    return mathml_strings




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



"""
cleanUpLatex(s):
    Purpose:
        cleans up alttext so latex title properly renders in matplotlib
    Input:
        s (str) - latext string to clean
    Output:
        latex string with non-renderable chars removed
"""
def cleanUpLatex(s):
    s = s.replace("\n", " ")
    s = s.replace("%", " ")
    for cmd in BAD_COMMANDS:
        s = s.replace(cmd, "")
    for cmd, replacement in REPLACE_COMMANDS.items():
        s = s.replace(cmd, replacement)

    s = "$" + s + "$"
    return s






####################################################################################################################################### 



#####################################################  Network X Graph Generation  ####################################################
'''
struct Node:
    value (str) - node's value
    children (list[Node]) - list of children node objects
'''
class Node:
    def __init__(self, value, children=None):
        self.value = value
        self.children = [] if children == None else children



"""
toOpTree:
    Purpose:
        convert a mathml_string into an operator tree
    Input:
        mathml_string (str) - clean & readable mathML string
    Output:
        root of operator tree if string is valid, else None        
"""
def toOpTree(mathml_string, compress_subscripts = True, compress_superscripts = True, fix_derivatives=True):
    # _eTreeToOpTree(et): converts etree xml object to node based operator tree
    def _eTreeToOpTree(et, compress_subscripts = compress_subscripts, compress_superscripts = compress_superscripts,fix_derivatives=fix_derivatives ):
        # Skip Tags: skip & process children
        if et.tag in skip:
            # "semantics" tag splits presentation & content ML
            if et.tag == 'semantics':
                for child in et:
                    # content ml subtree rooted @ "annotation" 
                    if child.tag == 'annotation' or child.tag == 'annotation-xml': 
                        return _eTreeToOpTree(child)
                # error if content ml not found
                exit(-1) 
            else:
                # skip tag & generate children subtrees
                return _eTreeToOpTree(et[0]) 
            
        # Terimal Tags: nested layers of tags before text
        elif et.tag in term:
            value = et.text.strip()
            while value == "": 
                if len(list(et)) == 0:
                    value = "no text found"
                    break
                et = et[0]
                value = et.text.strip()
            return Node(value = value)

        # Operator Tags: have operators & n children    
        elif et.tag in op:
            value = ""
            children = []
            # first child of op tag is operator
            node = _eTreeToOpTree(et[0]) 
            value = node.value 

            '''
            Rulbase for subscript compression:
                Rule 0: tag1 ∈ {'ci', 'cn', 'cs'} ^ tag2 ∈ {'ci', 'cn', 'cs'} 
                        -> return Node(node1.value + '_' + node2.value)
                Rule 1: node0.value == 'subscript' and node1.value == 'superscript' and node2.children == [] and node1.children[0].children == [] 
                        -> node1.children[0].value += '_' + node2.value; return node1
                Rule 2: node0.value == 'subscript' and node1.children == [] 
                        -> return node1
            '''
            # compress subscript nodes into 1 node
            if compress_subscripts == True:
                num_children = len(et)
                compressable = {'ci', 'cn', 'cs'}
                if value=='subscript':
                    tag0, tag1 = et[0].tag, et[1].tag
                    node0, node1 = _eTreeToOpTree(et[0]), _eTreeToOpTree(et[1])
                    # Apply Compression Rules
                    if num_children == 3:
                        tag2 = et[2].tag
                        node2 = _eTreeToOpTree(et[2]) 
                        if tag1 in compressable and tag2 in compressable:
                            return Node(node1.value + '_' + node2.value)
                        elif node0.value == 'subscript' and node1.value == 'superscript' and node2.children == [] and node1.children[0].children == []:
                            node1.children[0].value += '_' + node2.value
                            return node1
                        elif node0.value == 'subscript' and node1.value == 'superscript' and node2.children !=[]:
                            return node1
                        elif node0.value == 'subscript' and node1.children == [] and tag1 in compressable and tag2 not in compressable:
                            def _IOT(node):
                                if node.children==[]:
                                    return node.value.strip()
                                if len(node.children) == 2:
                                    return _IOT(node.children[0]) + '_' + node.value + '_' + _IOT(node.children[1])
                                if len(node.children) == 1:
                                    return _IOT(node.children[0]) + '_' + node.value
                                
                            node1.value += '_' + _IOT(node2) 
                            return node1
                        elif node0.value == 'subscript' and node1.children == []:
                            return node1
                        elif tag1 not in compressable and tag2 in compressable:
                            return node1
                        elif tag1 not in compressable and tag2 not in compressable:
                            return node1

            # compress superscript nodes
            if compress_superscripts == True:
                if value == 'superscript':
                    '''
                    Rulbase for superscript compression:
                        Rule 0: test = opTree(et) w/o super-script compression 3 ^ all children are of test are leaves 
                                -> move test.child[2] to be the child of test.child[1]
                    '''
                    test_node = _eTreeToOpTree(et, compress_subscripts, False)
                    if len(test_node.children) == 3 and sum(len(child.children) for child in test_node.children) == 0:
                        operand = test_node.children[2]
                        operator = test_node.children[0]
                        power = test_node.children[1]
                        operator.children = [operand]
                        return Node(value, [operator, power])
                    


            if fix_derivatives == True:
                if value == 'times':
                    l0 = _eTreeToOpTree(et, compress_subscripts, compress_superscripts, False)
        
                    # convert d * operand to to d.child = operand
                    l1_removal = set()  
                    l1_nodes = l0.children
                    for l1_idx, l1 in enumerate(l1_nodes):
                        l1 = l1_nodes[l1_idx]
                        if l1_idx + 1 < len(l1_nodes):
                            if l1.value == '𝑑' and l1.children == []:
                                l1_child = l1_nodes[l1_idx + 1]
                                l1.children.append(l1_child)  
                                l1_removal.add(l1_idx + 1)  
                    new_l1 = []
                    for l1_idx, l1 in enumerate(l1_nodes):
                        if l1_idx not in l1_removal:
                            if l1.value == '𝑑':
                                l1.value = 'd'
                            new_l1.append(l1)


                # convert times(superscript(d,n), z) to times(superscript(d(operant),n), z) if times has more children else superscript(d(operant),n).
                    l1_removal = set()  
                    l1_nodes = l0.children
                    for l1_idx, l1 in enumerate(l1_nodes):
                        l1 = l1_nodes[l1_idx]
                        if l1.value == 'superscript':
                            l2_nodes = l1.children
                            for l2_idx, l2 in enumerate(l2_nodes):
                                if l2.value == '𝑑' and l2.children == []:
                                    l2.value = 'd'
                                    if l1_idx + 1 < len(l1_nodes):
                                        l1_operand = l1_nodes[l1_idx + 1]
                                        l1_removal.add(l1_idx + 1)  
                                        l2.children = [l1_operand]
                                                      
                    new_l1 = []
                    for l1_idx, l1 in enumerate(l1_nodes):
                        if l1_idx not in l1_removal:
                            if l1.value == '𝑑':
                                l1.value = 'd'
                            new_l1.append(l1)

                    # times operator has only 1 child after compression
                    if len(new_l1) == 1:
                        return Node(new_l1[0].value, new_l1[0].children)
                    else:
                        return Node(value, new_l1)
                
                


                        
                    
                    
                        
             

                        # if l1.value == 'superscript':
                        #     l0.children.remove(l1_idx+1)

                        # # Case 0: d*var 
                        # if l1.value == 'd' and l1.children == []:
                        #     new_children = l0



                        # if l1.value == 'superscript':
                        #     for l2_idx,l2 in enumerate(l1.children):
                        #         if l2.ch




                

      
                    
                      







                           






                        




 
            # operator's children become children of operator node
            children.extend(node.children) 
            # remaining children are operands & become children of operator node
            for i in range(1, len(list(et))): 
                children.append(_eTreeToOpTree(et[i]))
            return Node(value = value.strip(), children = children)

        # No Children Tags: return Node with value = tag
        elif len(list(et)) == 0: 
            return Node(value = et.tag)
        
        # Error Protection: create dummy node & process children for unprocessed tag
        else: 
            children = []
            for child in et:
                children.append(_eTreeToOpTree(child))
            return Node(value = et.tag, children = children)
        
    # Attempt to create operator tree
    try:        
        et = ET.fromstring(mathml_string.encode('utf-8'))
        root = _eTreeToOpTree(et)
        return root
    except ET.XMLSyntaxError as e:
        print(f"Error parsing MathML string: {mathml_string}")
        return None 
    


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



"""
getTreesFromFile:
    Purpose: 
        extract a list of nx graph of operator tree for each block equation in an html file
    Input:
        filename (str) - paath to html file
    Output:
        list of nx graph objects, ready to plot
"""
def getTreesFromFile(filename):
    trees = []
    mathml_strings = toMathMLStrings(filename)
    for i, e in enumerate(mathml_strings): 
        root = toOpTree(e[0])
        G = graphTree(root)
        trees.append(G)
    return trees
######################################################################################################################################



#####################################################  Display Network X Graphs  ###################################################

# list of node colors
color_palette = [
    "FFA500",  # orange
    "EE82EE",  # violet
    "008000",  # green
    "0000FF",  # blue
    "4B0082",  # indigo
    "FFC0CB",  # pink
    "D8BFD8",  # purple
    "AFEEEE",  # turquoise
    "00FFFF",  # cyan
    "000080",  # navy
    "008080",  # teal
    "A52A2A",  # brown
    "D2B48C",  # tan
    "F5F5F5",  # beige
    "808080",  # gray
    "C0C0C0",  # silver
    "FFFF00",  # yellow
    "FFA000",  # darker orange
    "EE76EE",  # darker violet
    "007000",  # darker green
    "0000CD",  # darker blue
    "4A007C",  # darker indigo
    "F7B6C1",  # darker pink
    "D5B4A6",  # darker purple
    "AEEEEE",  # darker turquoise
    "00EEEE",  # darker cyan
    "000070",  # darker navy
    "007070",  # darker teal
    "FF6347",  # red-orange
    "DA70D6",  # pink-purple
    "8FBC8F",  # green-blue
    "40E0D0",  # cyan-blue
    "8A2BE2",  # purple-blue
    "FFE4E1",  # pink-white
    "9370DB",  # purple-blue
    "B2DF8A",  # green-yellow
    "00CED1",  # cyan-blue
    "800080",  # dark red
    "D2691E",  # orange-red
    "7FFF00",  # highlighter yellow
    "00FA9A",  # light green
    "808B8B",  # light gray
    "87CEFA",  # light blue
    "F08080",  # salmon
    "9ACD32",  # light green
    "F0F0F0",  # extra light gray
    "D3D3D3",  # light gray
    "999999",  # medium gray
    "666666",  # dark gray
    "0F0F0F",  # dark gray
    "A0522D",  # terracotta
    "9D38BD",  # plum
    "6A5ACD",  # orchid
    "BC8F8F",  # rose pink
    "F0DC82",  # goldenrod
    "40E0D0",  # cyan-blue
    "3B5998",  # medium blue
    "800080",  # dark red
    "F08080",  # salmon
    "9F79AC",  # plum
    "D5D8BD",  # light brown
    "92D050",  # light green
    "C0C090",  # light gray
    "D65D00",  # orange
    "B388FF",  # purple
    "00827D",  # teal
    "D9D9D9",  # light gray
    "BDBDBD",  # medium gray
    "999999",  # dark gray
]
"""
average_color:
    Purpose:
        calculates average color from a list of hexadecimal color codes
    Input:
        colors (List[str]) - List of hexadecimal color codes (without the # symbol) to average. 
                             Example: ["ff0000", "00ff00", "0000ff"]
    Output:
        str - A hexadecimal color code representing the average color, or None if the input list is empty. 
              Example: "#808080"
"""
def average_color(colors):
    if len(colors) == 0:
        return None
    red, green, blue = 0,0,0
    for color in colors:
        red += int(color[0:2], 16)
        green += int(color[2:4], 16)
        blue += int(color[4:6], 16)
    average_red = red // len(colors)
    average_green = green // len(colors)
    average_blue = blue // len(colors)
    return f"#{average_red:02x}{average_green:02x}{average_blue:02x}"


"""
plotTree:
    Purpose:
        astehtically plots nx graphs of contentML trees
    Input:
        tree (nx) - networkX graph object
    Output:
        None - Displays Tree
"""
def plotTree(tree, title):
    title = cleanUpLatex(title)
    plt.title(title, usetex=True)
    pos = nx.nx_agraph.pygraphviz_layout(tree, prog='dot')
    labels = nx.get_node_attributes(tree, 'data') 
    nx.draw(tree, pos, labels=labels, font_size=8)
    plt.show()



"""
plotTreesFromFile:
    Purpose: 
        plot operator trees of all block equations in given test file
    Input:
        filename (str) - path to html file
    Output:
        None - 1 by 1 graphs of contentML equations
"""
def plotTreesFromFile(filename):
    mathml_strings = toMathMLStrings(filename)
    for i, e in enumerate(mathml_strings): 
        math_str, latex_str = e[0], e[1]
        root = toOpTree(math_str)
        title = cleanUpLatex(e[1])
        G = graphTree(root)
        plotTree(G, title)



'''
    plotTreeWithFeature:
        Purpose: 
            hi-light all instances of a feature in a network X tree
        Input:
            tree (nx) - content ML operator tree
            feature_list (list[str]) -  list of operators in feature path
            feature_color (str) - color to hilight features in 
        Output:
            None - displays operator tree with every occurrance of a feature
 '''       
def plotTreeWithFeature(tree, title="", feature_list=[], feature_color = 'green'):
        
    special_nodes = find_feature_paths(tree, title, feature_list)
    # 4. Plot graph and label nodes with apporpiate color
    try:
        plt.title(title, usetex=True)
    except:
        plt.title("Ill-Formed Latex", usetex=True)
    pos = nx.nx_agraph.pygraphviz_layout(tree, prog='dot')
    labels = nx.get_node_attributes(tree, 'data') 
    color_map = []
    for node in tree:
        if node in special_nodes:
            color_map.append(feature_color) # green color for feature nodes
        else: 
            color_map.append('red') # red color for non-feature nodes
    nx.draw(tree, pos, labels=labels, node_color=color_map, font_size=8)
    plt.show()



"""
plotTreeWithFeatures:
    Purpose:
        Plots a networkX graph object, highlighting nodes that belong to specific feature paths. 
        Computes the average color for nodes that may belong to multiple paths and displays the 
        tree with appropriate coloring and labels for features.
    Input:
        tree (nx.Graph) - NetworkX graph object representing the tree.
        title (str, optional) - Title of the plot. Default is an empty string.
        features (List[List[str]], optional) - List of features to be highlighted.
    Output:
        None - Displays the tree with specified features highlighted.
"""
def plotTreeWithFeatures(tree, title="", features=[]):
    title = cleanUpLatex(title)
    special_nodes = {}

    # find all nodes belonging to a feature path
    for idx, feature in enumerate(features):
        feature_nodes = find_feature_paths(tree, title, feature)
        for node_id in feature_nodes:
            if node_id not in special_nodes:
                special_nodes[node_id] = set()
            special_nodes[node_id].add(color_palette[idx%len(color_palette)])

    # compute average for each colored node (nodes may belong to many paths)
    for node_id in special_nodes:
        special_nodes[node_id] = average_color(special_nodes[node_id])

    # plot graph and label nodes with apporpiate color
    plt.title(title, usetex=True)

    # plot feature & corresonding node color on graph
    for i in range(len(features)):
        x = -50
        y = -50 - 30*i
        text = str(features[i])
        color = '#'+color_palette[i%len(color_palette)]
        plt.text(x,y,text, fontsize=10, color=color)

    # map nodes to appropriate colors   
    pos = nx.nx_agraph.pygraphviz_layout(tree, prog='dot')
    labels = nx.get_node_attributes(tree, 'data') 

    color_map = []
    for node in tree:
        if node in special_nodes:
            color_map.append(special_nodes[node]) 
        else: 
            color_map.append('red')
    nx.draw(tree, pos, labels=labels, node_color=color_map, font_size=10)
    plt.show()

    



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
######################################################################################################################################





