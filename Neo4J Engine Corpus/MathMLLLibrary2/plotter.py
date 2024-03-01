import networkx as nx
from networkx.drawing.nx_agraph import graphviz_layout
import matplotlib.pyplot as plt

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

######################################################################################################################################

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

######################################################################################################################################

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