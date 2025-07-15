#!/usr/bin/env python3
import os
import re
import time
import uuid
import xml.etree.ElementTree as ET
from xml.dom import minidom
import zipfile
import shutil

def generate_uuid():
    return str(uuid.uuid4()).replace('-', '')

def escape_xml(text):
    """Escape special XML characters"""
    return text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;').replace("'", '&apos;')

def parse_markdown(content):
    """Parse markdown content into a hierarchical structure"""
    lines = content.strip().split('\n')
    title = "Untitled"
    structure = []
    stack = []
    
    for line in lines:
        if not line.strip():
            continue
            
        # Check for title
        if line.startswith('Title:'):
            title = line[6:].strip()
            continue
            
        # Determine level and content
        level = 0
        content = line.strip()
        
        if line.startswith('# '):
            level = 1
            content = line[2:].strip()
        elif line.startswith('## '):
            level = 2
            content = line[3:].strip()
        elif line.startswith('### '):
            level = 3
            content = line[4:].strip()
        elif line.startswith('#### '):
            level = 4
            content = line[5:].strip()
        elif line.startswith('- '):
            # Determine level by indentation
            indent = len(line) - len(line.lstrip())
            level = (indent // 2) + 2
            content = line.strip()[2:]
        elif line.startswith('* '):
            indent = len(line) - len(line.lstrip())
            level = (indent // 2) + 3
            content = line.strip()[2:]
        else:
            continue
            
        node = {
            'id': generate_uuid(),
            'content': content,
            'level': level,
            'children': []
        }
        
        # Find parent
        while stack and stack[-1]['level'] >= level:
            stack.pop()
            
        if not stack:
            structure.append(node)
        else:
            stack[-1]['children'].append(node)
            
        stack.append(node)
    
    return title, structure

def create_topic_element(node, parent_elem):
    """Create XML topic element"""
    topic = ET.SubElement(parent_elem, 'topic', {
        'id': node['id'],
        'timestamp': str(int(time.time() * 1000))
    })
    
    title = ET.SubElement(topic, 'title')
    title.text = node['content']
    
    if node['children']:
        children = ET.SubElement(topic, 'children')
        topics = ET.SubElement(children, 'topics', {'type': 'attached'})
        
        for child in node['children']:
            create_topic_element(child, topics)
    
    return topic

def generate_xmind_xml(title, structure):
    """Generate XMind XML content"""
    # Create root element with namespaces
    root = ET.Element('xmap-content', {
        'xmlns': 'urn:xmind:xmap:xmlns:content:2.0',
        'xmlns:fo': 'http://www.w3.org/1999/XSL/Format',
        'xmlns:svg': 'http://www.w3.org/2000/svg',
        'xmlns:xhtml': 'http://www.w3.org/1999/xhtml',
        'xmlns:xlink': 'http://www.w3.org/1999/xlink',
        'version': '2.0'
    })
    
    # Create sheet
    sheet = ET.SubElement(root, 'sheet', {
        'id': generate_uuid(),
        'timestamp': str(int(time.time() * 1000))
    })
    
    # Create root topic
    root_topic = ET.SubElement(sheet, 'topic', {
        'id': generate_uuid(),
        'structure-class': 'org.xmind.ui.map.unbalanced',
        'timestamp': str(int(time.time() * 1000))
    })
    
    root_title = ET.SubElement(root_topic, 'title')
    root_title.text = title
    
    # Add children if any
    if structure:
        children = ET.SubElement(root_topic, 'children')
        topics = ET.SubElement(children, 'topics', {'type': 'attached'})
        
        for node in structure:
            create_topic_element(node, topics)
    
    # Convert to pretty XML string
    xml_str = ET.tostring(root, encoding='unicode')
    dom = minidom.parseString(xml_str)
    return dom.toprettyxml(indent='  ', encoding='UTF-8')

def create_meta_xml():
    """Create meta.xml content"""
    meta_content = '''<?xml version="1.0" encoding="UTF-8"?>
<meta xmlns="urn:xmind:xmap:xmlns:meta:2.0" version="2.0">
  <create-time>{}</create-time>
  <creator>
    <n>GitHub Action</n>
  </creator>
</meta>'''.format(time.strftime('%Y-%m-%d %H:%M:%S'))
    return meta_content.encode('utf-8')

def create_xmind_file(title, structure, output_path):
    """Create complete XMind file"""
    # Create temporary directory
    temp_dir = f"temp_{generate_uuid()}"
    os.makedirs(temp_dir, exist_ok=True)
    
    try:
        # Generate content.xml
        content_xml = generate_xmind_xml(title, structure)
        with open(os.path.join(temp_dir, 'content.xml'), 'wb') as f:
            f.write(content_xml)
        
        # Generate meta.xml
        meta_xml = create_meta_xml()
        with open(os.path.join(temp_dir, 'meta.xml'), 'wb') as f:
            f.write(meta_xml)
        
        # Create XMind file (zip)
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(temp_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, temp_dir)
                    zipf.write(file_path, arcname)
    
    finally:
        # Clean up
        shutil.rmtree(temp_dir)

def process_markdown_files():
    """Process all markdown files in the mindmaps directory"""
    input_dir = 'mindmaps'
    output_dir = 'generated'
    
    if not os.path.exists(input_dir):
        os.makedirs(input_dir)
        print(f"Created {input_dir} directory")
        return
    
    os.makedirs(output_dir, exist_ok=True)
    
    # Process each markdown file
    for filename in os.listdir(input_dir):
        if filename.endswith('.md'):
            input_path = os.path.join(input_dir, filename)
            base_name = os.path.splitext(filename)[0]
            
            # Create output directory for this mindmap
            mindmap_dir = os.path.join(output_dir, base_name)
            os.makedirs(mindmap_dir, exist_ok=True)
            
            print(f"Processing {filename}...")
            
            try:
                # Read and parse markdown
                with open(input_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                title, structure = parse_markdown(content)
                
                # Generate XML files
                content_xml = generate_xmind_xml(title, structure)
                with open(os.path.join(mindmap_dir, 'content.xml'), 'wb') as f:
                    f.write(content_xml)
                
                meta_xml = create_meta_xml()
                with open(os.path.join(mindmap_dir, 'meta.xml'), 'wb') as f:
                    f.write(meta_xml)
                
                print(f"Generated files for {base_name}")
                
            except Exception as e:
                print(f"Error processing {filename}: {e}")

if __name__ == "__main__":
    process_markdown_files()
