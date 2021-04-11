import json

def build_ast(ast):
    root = to_ast_tree(ast["root"], parent=None)
    return root

def build_ast_from_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        ast = json.load(f)
    root = to_ast_tree(ast["root"], parent=None)
    return root

def to_ast_tree(node, parent=None, left_brother=None):
    type = node["type"]
    pos = node["pos"]
    end = pos + node["length"]
    line = node["length"]

    if "label" in node:
        # has label
        label = node["label"]
    else:
        label = None

    ast_node = AST_Node(type, pos, end, line, label=label, parent=parent, left_brother=left_brother)

    left_brother = None
    for child in node["children"]:
        child = to_ast_tree(child, parent=ast_node, left_brother=left_brother)
        ast_node.add_child(child)
        left_brother = child

    return ast_node

def extract_Variable(ast):
    for node in ast.parse():
        node.extract_Variable()
    return ast
    
class AST_Node(object):
    def __init__(self, type, pos, end, line, label=None, parent=None, left_brother=None):
        self.type = type
        self.pos = pos
        self.end = end
        self.label = label
        self.line = line
        self.has_label = True if self.label else False
        self.children = []
        self.root = parent.root if parent else self
        self.variable = dict()
        self.parent = parent
        self.left_brother = left_brother

    def to_string(self):
        if self.has_label:
            node_str = '{}: {} [{},{}]'.format(self.type, self.label, self.pos, self.end)
        else:
            node_str = '{} [{},{}]'.format(self.type, self.pos, self.end)

        return node_str
    
    def add_child(self, child):
        self.children.append(child)

    def get_v_type(self):
        assert "Type" in self.type
        type_name = []
        for node in self.parse():
            if node.type == 'SimpleName':
                type_name.append(node.label)
        
        return ' '.join(type_name)

    def get_variable(self):
        assert self.type == 'VariableDeclarationFragment'
        if self.children[0].type == 'SimpleName':
            v = self.children[0].label

        if len(self.children) > 1 and self.children[1].type == 'SimpleName':
            v = self.children[1].label
        
        t = v
        if self.left_brother and "Type" in self.left_brother.type:
            t = self.left_brother.get_v_type()
        
        return v, t

    def extract_Variable(self):
        if self.type == 'VariableDeclarationFragment':
            v, t = self.get_variable()
            self.root.variable[v] = t

    def child_have(self, type):
        for child in self.parse():
            if child.type == type:
                return 1
        return 0

    def parse(self):
        ast = [self]
        for child in self.children:
            ast.extend(child.parse())
        
        return ast

    def dfs_print(self, pref=''):
        if self.has_label:
            node_str = '{}: {} [{},{}]'.format(self.type, self.label, self.pos, self.end)
        else:
            node_str = '{} [{},{}]'.format(self.type, self.pos, self.end)
        ast = pref + node_str + '\n'
        for child in self.children:
            ast += child.dfs_print(pref+'    ')
        
        return ast


class Cache():
    def __init__(self, size=10):
        self.memory = {}
        self.size = size
    
    def check_in(self, id):
        if id in self.memory:
            return True
        return False

    def get(self, id):
        if self.check_in(id):
            return self.memory[id]
        return None
    
    def add(self, id, value):
        if self.check_in(id):
            self.memory[id] = value
        else:
            if len(self.memory.keys()) >= self.size:
                self.memory.popitem()
            self.memory[id] = value

if __name__ == "__main__":
    
    import json
    file_path = "/home/zander/JIT-DP/Data_Extraction/git_base/datasets/tomcat/code/f23b99755bd5b1f1766cc9d6992b06a1aeb463c0/code-ast/java^org^apache^catalina^connector^CometEventImpl.java"
    with open(file_path, 'r', encoding='utf-8') as f:
        ast = json.load(f)
        ast = build_ast(ast)

    # ast.extract_Assignment()
    # ast.extract_Variable()
    # print(ast.extract_IF())
    