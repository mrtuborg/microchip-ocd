import json
import re

def process_header(line):
    headers = re.split(r'\s{2,}', line)
    if '\t' in headers[-1]:
        last_headers = headers[-1].split('\t')
        headers = headers[:-1] + last_headers
    return headers

def process_line(line, headers, custom_index):
    parts = re.split(r'\s{2,}', line)
    if '\t' in parts[-1]:
        last_parts = parts[-1].split('\t')
        parts = parts[:-1] + last_parts

    index_position = headers.index('Index')
    parts[index_position] = str(custom_index)

    tool = {headers[i]: parts[i] for i in range(len(parts))}
    return tool

def hwscan(stdout):
    tools = []
    header_processed = False
    custom_index = 0
    stdout_lines = stdout.splitlines()

    for line in stdout_lines:
        line = line.strip()
        if line in ["hwtool", "quit"] or not line:
            continue

        if not header_processed:
            headers = process_header(line)
            header_processed = True
            continue

        tool = process_line(line, headers, custom_index)
        tools.append(tool)
        custom_index += 1

    json_output = json.dumps(tools, indent=4)
    print(json_output)

