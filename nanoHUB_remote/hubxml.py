"""
Manipulate XML for nanoHUB tools

Benjamin P. Haley, Purdue University (bhaley@purdue.edu)

Copyright 2017 HUBzero Foundation, LLC.

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.

HUBzero is a registered trademark of Purdue University.
"""

import json
import numpy as np
import xml.etree.ElementTree as et
from api import launch_tool, get_results

# Driver template for the drivergen tool
template = """<?xml version="1.0"?>
<run>
    <input>
        <string id="toolname"><current>{0}</current></string>
        <string id="inputs"><current>{1}</current></string>
    </input>
</run>
"""

def get_driver(tool_name, inputs, headers):
    """Get the driver XML for running a nanoHUB tool with specific inputs"""
    drivergen_json = {
        'app': 'drivergen',
        'xml': template.format(tool_name, json.dumps(inputs))
    }
    session_id = launch_tool(drivergen_json, headers)
    run_xml = get_results(session_id, headers)
    xml = et.fromstring(run_xml)  # <run>
    driver_str  = '<?xml version="1.0"?>\n'
    driver_str += xml.find('./output/string/current').text
    return {'app': tool_name, 'xml': driver_str}

def extract_results(run_xml, outputs):
    """
    Parse run_xml to extract the specified output; return a dict with the
    output label as a key.  The returned values will be floats for <number>
    outputs, 2D numpy arrays for <curve> outputs, and strings      
    for all other output types.
    """

    if run_xml is None:
        print("Run not done OR results not extracted (check above!)")
        return
    
    ### For empty list, return all curve, number, text outputs
    return_all = False
    if not outputs:
        return_all = True

    results = {}
    ### Parse XML output results
    xml = et.fromstring(run_xml)
    xml_output = xml.find('output')
    ### Extract only these results (so far)
    curve = xml_output.findall('.//curve')
    num = xml_output.findall('.//number')
    log = xml_output.findall('.//log')

    ### Loop over number output
    ### Assume value in "current"
    ### Return raw string if float conversion fails
    for n in num:
        val = n.findall('.//current')[0].text
        label = n.findall('.//label')[0].text
        if return_all or label in outputs:
            try:
                results[label] = float(val)
            except:
                results[label] = val
    
    ### Loop over text output, checking all XML
    ### Cases so far: "tail" of "about" contains text
    ### Could use for this style for all types
    for l in log: 
        label = l.findall('.//label')[0].text
        if return_all or label in outputs:        
            for text in l.itertext():
                if not text.isspace() and text != label:
                    results[label] = text

    ### Loop over curve outputs, including grouped curves
    for ind, c in enumerate(curve):

        ### Curves can be separate or grouped
        cgroup = c.find('./about/group')
        clabel = c.find('./about/label')

        ### If the group/label exists, save if all results were
        ###    requested or if this was specifically requested
        if cgroup is not None and (return_all or cgroup.text in outputs):
            name = "{}: {}".format(cgroup.text, clabel.text)
            parse = True
        elif clabel is not None and (return_all or clabel.text in outputs):
            name = clabel.text
            parse = True
        else: 
            parse = False
            
        if parse:
            xy = c.findall('.//xy')[0].text

            lines = xy.split('\n')
            n = len(lines)
            val = np.zeros([n,2])
            for i in range(n):
                words = lines[i].split()
                if words:
                    val[i,:] = map(float, words)

            results[name] = val
            
    return results
