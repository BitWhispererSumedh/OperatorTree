from neo4j import GraphDatabase
from MathMLLibrary.standardize_tree import *
from MathMLLibrary.pull_features import *
from MathMLLibrary.html_to_tree import *
import time
import os



#####################################################  Create Nodes, Relationships, Populate DB  ##################################################### 

def execute_write_query(query, params=None):
    with driver.session() as session:
        session.execute_write(lambda tx: tx.run(query, params))

# Key: DB creation operation, Value: function to execute operation
cmap = {
    "connect":  lambda uri, username, password: GraphDatabase.driver(uri, auth=(username, password)),
    "doc": lambda doc_name: execute_write_query("MERGE (doc:Doc {id: $doc_name})", {"doc_name": doc_name}),
    "eq": lambda equation_id: execute_write_query("MERGE (eq:Equation {id: $equation_id})", {"equation_id": equation_id}),
    "ftr": lambda feature_id: execute_write_query("MERGE (feat:Feature {id: $feature_id})", {"feature_id": feature_id}),
    "EQN_IN": lambda equation_id, doc_id: execute_write_query("MATCH (eq:Equation {id: $equation_id}), (doc:Doc {id: $doc_id}) MERGE (eq)-[:EQN_IN]->(doc)", {"equation_id": equation_id, "doc_id": doc_id}),
    "HAS_FTR": lambda equation_id, feature_id: execute_write_query("MATCH (eq:Equation {id: $equation_id}), (f:Feature {id: $feature_id}) MERGE (eq)-[:HAS_FTR]->(f)", {"equation_id": equation_id, "feature_id": feature_id})
}

# Populate the database with documents
def populate_db(corpus_folder):
    doc_idx = 0
    for doc in os.listdir(corpus_folder):
        file = corpus_folder + '/' + doc                                                              
        math_ml_strings, trees = toMathMLStrings(file), getTreesFromFile(file)    
        cmap["doc"](doc)                                            # create doc             
        for idx, eq in enumerate(math_ml_strings):
            cmap["eq"](eq)
            cmap["EQN_IN"](eq, doc)                              
            features = get_features(trees[idx])                     # create eq, eq in doc
            for feature in features:                                        
                cmap["ftr"](feature)
                cmap["HAS_FTR"](eq, feature)                        # create feature, eq has feature
        print(doc_idx, doc)
        doc_idx += 1



#####################################################  Query Database   ##################################################### 


# Find equations containing all features in feature_list
def eqns_with_feats(feature_list):
    with driver.session() as session:
        query = (
            f"MATCH (eq:Equation)-[r:HAS_FTR]->(f:Feature) "
            f"WHERE f.id IN $feature_list "
            f"WITH eq, collect(f.id) AS matched_features "
            f"WHERE ALL (x IN $feature_list WHERE x IN matched_features) "
            f"RETURN eq.id"
        )
        parameters = {'feature_list': feature_list}
        result = session.run(query, parameters)
        records = list(result)  # convert the result to a list immediately
    equations = [record["eq.id"] for record in records]
    return equations


# Find equations & corresp. ftrs containing S as subfeature
def eqns_with_subfeat(S):
    with driver.session() as session:
        result = session.run('''
            MATCH (e:Equation)-[:HAS_FTR]->(f:Feature)
            WHERE ALL(item IN $subsequence WHERE item IN f.id)
            WITH e.id AS equation_id, f.id AS features
            WITH equation_id, features, $subsequence AS subsequence
            WITH equation_id, features, 
                    REDUCE(
                        acc = {lastIdx: -1, indices: []},
                        item IN subsequence | 
                        {
                        lastIdx: COALESCE(
                                    [idx IN range(acc.lastIdx+1, size(features)-1) WHERE features[idx] = item][0],
                                    -1
                                    ),
                        indices: acc.indices + COALESCE(
                                    [idx IN range(acc.lastIdx+1, size(features)-1) WHERE features[idx] = item][0],
                                    -1
                                    )
                        }
                    ).indices AS operator_indices
            WHERE ALL(idx IN range(1, size(operator_indices) - 1) WHERE operator_indices[idx] > operator_indices[idx - 1])
            WITH equation_id, COLLECT(features) AS all_features, COLLECT(operator_indices) AS all_operator_indices
            RETURN equation_id, all_features
        ''', {"subsequence": S})
        return [(record['equation_id'], record['all_features']) for record in result]


# Find equations matching with some features in feature_list
def match_some_ftrs(feature_list):
    with driver.session() as session:
        query = (
            f"MATCH (eq:Equation)-[r:HAS_FTR]->(f:Feature) "
            f"WHERE f.id IN $feature_list "
            f"WITH eq, collect(f.id) AS matched_features, count(f) AS total_features "
            f"ORDER BY size(matched_features) DESC "  # order by number of matched features
            f"RETURN eq.id, size(matched_features) AS num_matched, total_features"
        )
        parameters = {'feature_list': feature_list}
        result = session.run(query, parameters)
        records = list(result)  # convert the result to a list immediately
        
    equations = [(record["eq.id"], record["num_matched"], record["total_features"]) for record in records if record["num_matched"] > 0]  # only include equations that have at least one feature matched
    return equations


# Find equations matching with some subfeatures in subfeatures_list
def match_some_subfeats_ordered(subfeatures_list):
    with driver.session() as session:
        result = session.run('''
            UNWIND $subsequences as subsequence
            MATCH (e:Equation)-[:HAS_FTR]->(f:Feature)
            WHERE ALL(item IN subsequence WHERE item IN f.id)
            WITH e.id AS equation_id, count(DISTINCT f.id) AS matched_subfeature_count
            MATCH (e:Equation {id: equation_id})-[:HAS_FTR]->(all_f:Feature)
            WITH equation_id, matched_subfeature_count, count(all_f) AS total_features
            RETURN DISTINCT equation_id, matched_subfeature_count, total_features
            ORDER BY matched_subfeature_count DESC, total_features DESC
        ''', {"subsequences": subfeatures_list})

        return [(record['equation_id'], record['matched_subfeature_count'], record['total_features']) for record in result]



def ranked_results(feature_list):
    exact_matches = match_some_ftrs(feature_list)
    subftr_matches = match_some_subfeats_ordered(feature_list)
    eq_to_rank = {}

    # Exact Matches
    for eq_id, num_matched, num_ftrs in exact_matches:
        key = tuple(eq_id)
        val = int(num_matched)
        denom = max(int(num_ftrs), len(feature_list))
        if key not in eq_to_rank:
            eq_to_rank[key] = 0
        eq_to_rank[key] += 0.5 * (val/denom)
 

    # Subfeature Matches
    seen_keys = set()
    for eq_id, cnt, num_ftrs in subftr_matches: 
        key = tuple(eq_id)
        val = int(cnt)
        denom = max(int(num_ftrs), len(feature_list))
        if key not in eq_to_rank:
            eq_to_rank[key] = 0
        eq_to_rank[key] += 0.5*(val/denom)

    # Group results by rank
    rank_to_eq = {}
    for eq_id in eq_to_rank:
        rank = eq_to_rank[eq_id]
        print(rank)
        if rank not in rank_to_eq:
            rank_to_eq[rank] = set()
        rank_to_eq[rank].add(eq_id)

    ranks = set()
    for rank in rank_to_eq:
        ranks.add(rank)
    
    ranks = list(ranks) 
    ranks.sort()
    ranks.reverse()

    for r in ranks:
        for eq in rank_to_eq[r]:
            eq = list(eq)
            math_str, latex_str = eq[0], eq[1]
            G = graphTree(toOpTree(math_str))
            plotTreeWithFeatures(G, latex_str, feature_list)




    



    
            
            


    
    

    





         























##################################################### Search Functionality ##################################################### 

def process_user_query(file_path):
    formatted = toMathMLStrings(file_path)[0]
    math_ml_string, latex_title = formatted[0], formatted[1]
    root = toOpTree(math_ml_string)
    tree = graphTree(root)
    return tree, latex_title


def f_exact_match(filepath):
    tree, title =  process_user_query(filepath)
    input_features = get_features(tree)
    matches = eqns_with_feats(input_features)
    for match in matches:
        mathML_str, title = match[0], match[1]
        root = toOpTree(mathML_str)
        G = graphTree(root)
        plotTree(G, title)

def f_eqns_with_subftr(subsequence):
    matches = eqns_with_subfeat(subsequence)
    for match in matches:
        eq, features = match
        math_str, latex_str = eq[0], eq[1]
        G = graphTree(toOpTree(math_str))
        plotTreeWithFeatures(G, latex_str, features)

def f_eqns_with_feats(features):
    matches = eqns_with_feats(features)
    for match in matches:
        eq = match
        math_str, latex_str = eq[0], eq[1]
        G = graphTree(toOpTree(math_str))
        plotTreeWithFeatures(G, latex_str, features)



#####################################################  Test Cases  ##################################################### 

test_map = {
    # tests f_exact_match 
    "test_exact_match_1" : lambda : f_exact_match('/Users/sumedh/Development/MathSearchEngine/Neo4J Engine/corpus1.txt'),
    "test_exact_match_2"  : lambda :f_exact_match('/Users/sumedh/Development/MathSearchEngine/Neo4J Engine/corpus2.txt'),

    # test equations containing a subfeature
    "test_eqns_with_subftr_1" : lambda : f_eqns_with_subftr(["¨"]),
    "test_eqns_with_subftr_2" : lambda : f_eqns_with_subftr(["times", "plus", "times"]),
    "test_eqns_with_subftr_3" : lambda : f_eqns_with_subftr(["superscript", "times", "divide", "times", "superscript"]),
    "test_eqns_with_subftr_4" : lambda : f_eqns_with_subftr(['vector', 'times', 'abs', 'superscript', 'eq', 'times', 'superscript', 'divide', 'times', 'superscript']),
        
    # test f_eqns_with_feats
    "test_eqns_with_feats_simple" : lambda : f_eqns_with_feats([["divide", "times", "superscript"]]),
    "test_eqns_with_feats_complex" :  lambda : f_eqns_with_feats([["times", "plus", "times", "superscript", "∇"], ["times", "plus", "times", "superscript"], ["times", "plus", "times"]]),

    # test f_eqns_with_most_feats
    "test_eqns_with_most_ftrs_simple" :  lambda : f_eqns_with_feats([["times", "plus", "times"]]),
    "test_eqns_with_most_ftrs_complex" :  lambda : f_eqns_with_feats([["times", "plus", "times", "superscript", "∇"], ["times", "plus", "times", "superscript"], ["times", "plus", "times"]]),

    # test ranking
    "test_ranking_fn" : lambda : ranked_results([["superscript", "times", "superscript"],["times", "plus", "times"]]),




}
if __name__ == "__main__":
    global driver
    driver = cmap["connect"]("bolt://localhost:7687", "neo4j", "password")
    # test_map["test_eqns_with_subftr_1"]()
    # test_map["test_eqns_with_most_ftrs_simple"]()
    # test_map["test_eqns_with_subftr_2"]()
    test_map["test_ranking_fn"]()



   
  





















    # Test
















 



    



