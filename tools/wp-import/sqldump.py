"""Minimal parser for UpdraftPlus/mysqldump-style INSERT statements."""
import re

ESC = {'0': '\0', 'b': '\b', 'n': '\n', 'r': '\r', 't': '\t', 'Z': '\x1a'}


def columns(sql, table):
    m = re.search(r"CREATE TABLE \x60" + re.escape(table) + r"\x60 \((.*?)\n\)", sql, re.S)
    cols = []
    for line in m.group(1).split('\n'):
        mm = re.match(r"\s*\x60([^\x60]+)\x60 ", line)
        if mm:
            cols.append(mm.group(1))
    return cols


def _parse_values(sql, i):
    rows = []
    while True:
        while sql[i] in ' \n\r\t,':
            i += 1
        if sql[i] == ';':
            return rows
        assert sql[i] == '(', sql[i - 50:i + 50]
        i += 1
        row = []
        while True:
            while sql[i] in ' \n\r\t':
                i += 1
            if sql[i] == "'":
                i += 1
                buf = []
                while True:
                    c = sql[i]
                    if c == '\\':
                        buf.append(ESC.get(sql[i + 1], sql[i + 1]))
                        i += 2
                    elif c == "'":
                        if sql[i + 1] == "'":
                            buf.append("'")
                            i += 2
                        else:
                            i += 1
                            break
                    else:
                        j = i
                        while sql[j] not in "\\'":
                            j += 1
                        buf.append(sql[i:j])
                        i = j
                row.append(''.join(buf))
            else:
                j = i
                while sql[j] not in ',)':
                    j += 1
                tok = sql[i:j].strip()
                i = j
                row.append(None if tok == 'NULL' else (int(tok) if re.fullmatch(r'-?\d+', tok) else tok))
            while sql[i] in ' \n\r\t':
                i += 1
            if sql[i] == ',':
                i += 1
                continue
            if sql[i] == ')':
                i += 1
                break
        rows.append(row)


def table(sql, name):
    cols = columns(sql, name)
    out = []
    for m in re.finditer(r"INSERT INTO \x60" + re.escape(name) + r"\x60 VALUES ", sql):
        out += [dict(zip(cols, r)) for r in _parse_values(sql, m.end())]
    return out
