import ast
import os

def parse_python_file(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            code = f.read()
            tree = ast.parse(code)
            classes = {}
            for node in tree.body:
                if isinstance(node, ast.ClassDef):
                    class_name = node.name
                    methods = []
                    attributes = []
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef):
                            if not item.name.startswith('__'):
                                args = [a.arg for a in item.args.args if a.arg != 'self' and a.arg != 'cls']
                                methods.append(f"{item.name}({', '.join(args)})")
                        elif isinstance(item, ast.Assign):
                            for target in item.targets:
                                if isinstance(target, ast.Name):
                                    # Very basic model attribute check (e.g. id = db.Column(...))
                                    if isinstance(item.value, ast.Call) and isinstance(item.value.func, ast.Attribute) and item.value.func.attr == 'Column':
                                        attributes.append(target.id)
                    classes[class_name] = {'methods': methods, 'attributes': attributes}
            return classes
    except Exception as e:
        return {}

def extract_all():
    print("=== MODELS ===")
    models = parse_python_file('d:/kmpl/Aplikasi/be_fl_fisio/models.py')
    for cls, data in models.items():
        print(f"class {cls}:")
        for attr in data['attributes']:
            print(f"  + {attr}")
        for method in data['methods']:
            print(f"  + {method}")
            
    print("\n=== SERVICES ===")
    services_dir = 'd:/kmpl/Aplikasi/be_fl_fisio/services'
    for f in os.listdir(services_dir):
        if f.endswith('.py'):
            svcs = parse_python_file(os.path.join(services_dir, f))
            for cls, data in svcs.items():
                print(f"class {cls}:")
                for method in data['methods']:
                    print(f"  + {method}")

extract_all()
