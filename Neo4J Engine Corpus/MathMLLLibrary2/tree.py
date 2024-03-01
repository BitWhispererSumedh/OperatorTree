from lxml import etree as ET

'''
struct Node:
    value (str) - node's value
    children (list[Node]) - list of children node objects
'''
class Node:
    def __init__(self, value, children=None):
        self.value = value
        self.children = [] if children == None else children

######################################################################################################################################        

# tags to skip
skip = {'math', 'semantics', 'annotation', 'annotation-xml'}

# terminal tags - tags with no children (except few instances), usually represent variables in equation
term = {'ci', 'cn', 'cs', 'csymbol'}

# operator tags - first child is operator, remaining children are operands
op = {'apply','ci', 'cn', 'cs', 'csymbol'}

######################################################################################################################################

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