import sys, re
import xml.etree.ElementTree as ET
p=sys.argv[1]
ET.register_namespace('', 'http://www.w3.org/2000/svg')
t=ET.parse(p); root=t.getroot()
removed=0
for g in list(root):
    if g.tag.endswith('g') and (g.get('transform') or '').replace(' ','').startswith('translate(40,'):
        root.remove(g); removed+=1
t.write(p, encoding='utf-8', xml_declaration=False)
print('removed', removed)
