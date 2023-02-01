from bs4 import BeautifulSoup
import re
'''
find_expressions:
    Purpose:    extract all mathML expression from an html file
    Input:      filepath (str) - path to an html file 
    Output:     (list of soup_objects) a list of mathML expressions
'''
def find_expressions(filepath):
    try:
        f = open(filepath, "r")
    except:
        print(filepath + " is an invalid file path.")
    html_data = f.read()
    soup_obj = BeautifulSoup(html_data, 'html.parser')
    expressions = soup_obj.find_all('math')
    return [str(e) for e in expressions]




'''
filter_expression:
    Purpose:    remove tag attributes, tags with no data, empty spaces, hidden empty charecters
    Input:      expr_obj (soup) - a mathML expression 
    Output:     (soup object) mathML expressions with tag attributes & unneeded tags removed
'''
def filter_expression(exp):
    soup_obj = BeautifulSoup(exp, 'html.parser')
    for tag in soup_obj.find_all():                         # Remove all tag attributes
        tag.attrs = {}

    for tag in soup_obj.find_all():                         # Remove distracting tags
        if tag.name in ['annotation', 'annotation-xml']:
            tag.decompose()
    mathml_string = re.sub(r'\s', '', str(soup_obj))        # Remove spaces
    mathml_string=mathml_string.replace('\u2062', '')       # Remove hidden HTML char

    
    blacklist = []                                          # Remove tags with no content (*does NOT remove sets of nested empty tags*)
    mathml_list = mathml_string.split('><')
    for i in range(1,len(mathml_list)):
        if mathml_list[i-1] == mathml_list[i][1:]:
            blacklist.append(i-1)
            blacklist.append(i)
    blacklist.sort(reverse=True)
    for i in blacklist:
        del mathml_list[i]
    html_string='><'.join(mathml_list)
    return html_string

###########################################################################################################################################################################################################

# Sample Use Case
# 0. Find all the math expressions in given file
raw_exp = find_expressions('test.html')
# 1. Remove distractions and clean the expressions
clean_exp = [filter_expression(e) for e in raw_exp]
# 2. View the mathML represntations
for e in clean_exp:
    print(e, '\n')