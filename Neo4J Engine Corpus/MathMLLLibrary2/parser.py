from bs4 import BeautifulSoup

# unnecessary attributes to remove from mathml string
REMOVE_ATTRIBUTES = ["id", "xref", "type", "cd", "encoding"]

######################################################################################################################################

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