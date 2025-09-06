import os

def print_tree(startpath, prefix=""):
    for i, name in enumerate(sorted(os.listdir(startpath))):
        path = os.path.join(startpath, name)
        connector = "└── " if i == len(os.listdir(startpath)) - 1 else "├── "
        print(prefix + connector + name)
        if os.path.isdir(path):
            extension = "    " if i == len(os.listdir(startpath)) - 1 else "│   "
            print_tree(path, prefix + extension)

print_tree("/home/hi-born/MahindraMahindra/active/travel_bot")