class LinkNode:
    def __init__(self, link):
        self.link = link
        self.children = []

    def add_child(self, child_node):
        self.children.append(child_node)