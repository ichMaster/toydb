def format_results(columns: list[str], rows: list[list]) -> str:
    display_rows = []
    for row in rows:
        display_rows.append([_format_value(v) for v in row])

    widths = [len(col) for col in columns]
    for row in display_rows:
        for i, val in enumerate(row):
            widths[i] = max(widths[i], len(val))

    separator = '+' + '+'.join('-' * (w + 2) for w in widths) + '+'
    header = '|' + '|'.join(f" {col:<{widths[i]}} " for i, col in enumerate(columns)) + '|'

    lines = [separator, header, separator]
    for row in display_rows:
        line = '|' + '|'.join(f" {val:<{widths[i]}} " for i, val in enumerate(row)) + '|'
        lines.append(line)
    lines.append(separator)
    lines.append(f"{len(rows)} row(s)")

    return '\n'.join(lines)


def _format_value(value) -> str:
    if value is None:
        return "NULL"
    return str(value)
