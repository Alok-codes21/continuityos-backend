"""Bounded static source summaries. Parse text only; never import or execute repository code."""
import ast
import re
from pathlib import PurePosixPath


def extract_code(path, content, meta=None):
    from .extract import Item
    meta = meta or {}
    path = str(meta.get('path') or path)
    source = content.split('\n', 1)[1] if content.startswith('File: ') else content
    key = 'code/' + str(meta.get('repository') or 'repository').lower() + '/' + path.lower()
    lines = source.splitlines()
    first = next((l for l in lines if l.strip()), '')
    if not first:
        return []
    items = [Item('component', 'component:' + key, f'Source module {path}',
                  {'component': key, 'component_name': path, 'path': path, 'static_analysis': True}, 'evidence_backed', first)]
    suffix = PurePosixPath(path).suffix.lower()
    defs, imports = [], []
    if suffix == '.py':
        try:
            tree = ast.parse(source)
        except (SyntaxError, ValueError, RecursionError):
            return items
        for node in ast.walk(tree):
            line = lines[node.lineno-1] if hasattr(node, 'lineno') and node.lineno <= len(lines) else first
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                defs.append((node.name, 'class' if isinstance(node, ast.ClassDef) else 'function', line))
            elif isinstance(node, ast.Import):
                imports.extend((a.name, line) for a in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.append(('.'*node.level + (node.module or ''), line))
    else:
        for line in lines:
            for match in re.finditer(r'\b(?:function|class|interface|def|func)\s+([A-Za-z_$][\w$]*)|\b(?:const|let)\s+([A-Za-z_$][\w$]*)\s*=.*=>', line):
                defs.append((match.group(1) or match.group(2), 'declaration', line))
            patterns = [r'\bfrom\s+[\'"]([^\'"]+)', r'\b(?:require|import)\s*\(?\s*[\'"]([^\'"]+)',
                        r'^\s*import\s+([\w./]+)', r'^\s*(?:use|using)\s+([\w:.]+)', r'#include\s*[<"]([^>"]+)']
            for pat in patterns:
                imports.extend((m.group(1), line) for m in re.finditer(pat, line))
    for name, kind, line in defs[:150]:
        items.append(Item('code_symbol', f'symbol:{key}:{name}:{kind}', f'{path} declares {kind} {name}',
                          {'component': key, 'symbol': name, 'kind': kind, 'path': path}, 'evidence_backed', line))
    for target, line in list(dict.fromkeys(imports))[:100]:
        dep = 'import/' + target.lower()
        items.append(Item('dependency', f'dependency:{key}>{dep}', f'{path} imports {target}',
                          {'from': key, 'to': dep, 'static_import': True, 'path': path}, 'inferred', line))
    for line in lines:
        m = re.search(r'(?i)(?:#|//|\*)\s*(?:owner|maintainer)\s*:\s*@?([\w.-]+)', line)
        if m:
            items.append(Item('owner_hint', f'owner-hint:{key}:{m.group(1)}', f'{path} names {m.group(1)} as an owner hint',
                              {'component': key, 'person': m.group(1), 'path': path}, 'inferred', line))
    return items
