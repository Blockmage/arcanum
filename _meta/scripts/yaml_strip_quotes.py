#!/usr/bin/env python3

import logging
import sys
from pathlib import Path

from ruamel.yaml import YAML
from ruamel.yaml.scalarstring import (
    FoldedScalarString,
    LiteralScalarString,
    PlainScalarString,
    ScalarString,
)

logging.basicConfig(force=True, level=logging.WARNING, stream=sys.stderr)
logger = logging.getLogger('yaml-strip-quotes')

yaml = YAML()
yaml.preserve_quotes = True
yaml.indent(mapping=2, sequence=4, offset=2)
yaml.width = 4096


def strip_unnecessary_quotes(node: object) -> object:
    """Recursively strip explicit quote wrapping, preserving block scalars."""
    if isinstance(node, dict):
        new_dict = {}
        for k, v in node.items():
            cleaned_k = strip_unnecessary_quotes(k)
            new_dict[cleaned_k] = strip_unnecessary_quotes(v)
        node.clear()
        node.update(new_dict)
        return node
    if isinstance(node, list):
        for i, item in enumerate(node):
            node[i] = strip_unnecessary_quotes(item)
        return node
    if isinstance(node, (LiteralScalarString, FoldedScalarString)):
        return node
    if isinstance(node, str) and '\n' in node:
        return node
    if isinstance(node, ScalarString):
        return PlainScalarString(node)
    return node


def format_file(file_path: Path) -> bool:
    try:
        content = yaml.load(file_path)
        if content is None:
            return True
        cleaned = strip_unnecessary_quotes(content)
        yaml.dump(cleaned, file_path)
    except Exception:
        logger.exception('Error processing file: %s', file_path)
        return False
    else:
        return True


def main() -> None:
    has_errors = False
    for arg in sys.argv[1:]:
        target = Path(arg)
        if target.is_file():
            if not format_file(target):
                has_errors = True
    if has_errors:
        sys.exit(1)


if __name__ == '__main__':
    main()
