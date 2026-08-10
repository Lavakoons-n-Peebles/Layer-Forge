import json
import os

CONFIG_FILE = "docs_meta.json"
README_PATH = "../README.md"

def load_config():
    # Load the list of table configurations from the external JSON file
    if not os.path.exists(CONFIG_FILE):
        raise FileNotFoundError(f"Error: {CONFIG_FILE} not found in the current directory.")
    
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def generate_html_table(table_config):
    # Generate the HTML table string based on individual table configuration, hierarchy mode, and column widths
    mode = table_config.get("generation_mode", "hierarchical")
    items = table_config.get("items", [])
    column_widths = table_config.get("column_widths", [])
    
    # Build colgroup tags if column widths are specified in configuration
    colgroup_lines = ["  <colgroup>"]
    if column_widths:
        for width in column_widths:
            colgroup_lines.append(f'    <col style="width: {width};">')
    else:
        for _ in range(4):
            colgroup_lines.append('    <col>')
    colgroup_lines.append("  </colgroup>")

    lines = [
        "<table>",
        "\n".join(colgroup_lines),
        "  <thead>",
        "    <tr>",
        "      <th>Parameter</th>",
        "      <th>Type</th>",
        "      <th>Default</th>",
        "      <th>Description</th>",
        "    </tr>",
        "  </thead>",
        "  <tbody>"
    ]
    
    def append_row(item, is_nested=False):
        # Append a single parameter row to the table lines with an optional visual indent for nested items
        indent_style = ' style="padding-left: 20px;"' if is_nested else ''
        lines.append('    <tr>')
        lines.append(f'      <td{indent_style}><code>{item["param"]}</code></td>')
        lines.append(f'      <td>{item["type"]}</td>')
        lines.append(f'      <td><code>{item["default"]}</code></td>')
        lines.append(f'      <td>{item["desc"]}</td>')
        lines.append('    </tr>')

    for item in items:
        if item.get("is_group"):
            if mode == "hierarchical":
                lines.append('    <tr>')
                lines.append(f'      <td colspan="4"><strong>{item["type"]}</strong></td>')
                lines.append('    </tr>')
            
            for child in item.get("children", []):
                # If mode is hierarchical, apply visual indentation to child parameters
                is_nested = (mode == "hierarchical")
                append_row(child, is_nested=is_nested)
        else:
            append_row(item, is_nested=False)
            
    lines.append("  </tbody>")
    lines.append("</table>")
    return "\n".join(lines)

def update_readme():
    # Update README.md by replacing content between specific markers for each table configuration
    if not os.path.exists(README_PATH):
        print(f"Error: {README_PATH} not found in the current directory.")
        return

    with open(README_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    tables = load_config()

    for table in tables:
        marker_start = table.get("marker_start")
        marker_end = table.get("marker_end")

        if not marker_start or not marker_end:
            print("Warning: Table configuration missing markers. Skipping.")
            continue

        if marker_start not in content or marker_end not in content:
            print(f"Warning: Markers {marker_start} / {marker_end} not found in {README_PATH}. Skipping.")
            continue

        new_table_block = f"{marker_start}\n{generate_html_table(table)}\n{marker_end}"

        start_idx = content.find(marker_start)
        end_idx = content.find(marker_end) + len(marker_end)
        
        content = content[:start_idx] + new_table_block + content[end_idx:]

    with open(README_PATH, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"{README_PATH} successfully updated with all configured tables!")

if __name__ == "__main__":
    update_readme()