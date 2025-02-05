# data/data_list.py
import os
import xml.etree.ElementTree as ET
import pandas as pd

MATERIAL_MAP = {
    'Al Mg 3': 'CZ',
    '1.4301': 'N',
    'By Steel': 'CZ'
}

def load_data_from_xml(folder_path):
    data = []
    xml_files = ['1.4301.xml', 'By Steel.xml', 'Al Mg 3.xml']
    for filename in xml_files:
        full_path = os.path.join(folder_path, filename)
        if os.path.exists(full_path):
            tree = ET.parse(full_path)
            root = tree.getroot()

            material_element = root.find('.//Material')
            if material_element is not None:
                original_material = material_element.attrib.get('Name', 'Unknown')
                material = MATERIAL_MAP.get(original_material, 'Unknown')
            else:
                material = 'Unknown'

            for data_table in material_element.findall('.//DataTable'):
                thickness = float(data_table.attrib.get('SheetThickness', '0'))
                v_width = float(data_table.attrib.get('DieOpeningWidth', '0'))

                dt_entries = data_table.find('.//DTEntries')
                if dt_entries is not None:
                    for dt_entry in dt_entries.findall('.//DTEntry'):
                        angle = float(dt_entry.attrib.get('BendAngle', '0'))
                        bd = float(dt_entry.attrib.get('DX', '0'))

                        data.append({
                            'Material': material,
                            'Grubosc': thickness,
                            'V': v_width,
                            'Kat': angle,
                            'BD': bd
                        })
        else:
            print(f"Plik {filename} nie istnieje w folderze {folder_path}.")
    df = pd.DataFrame(data)
    df = df.sort_values(['Grubosc', 'V', 'Kat']).reset_index(drop=True)

    df['BD'] = df.groupby(['Grubosc', 'V'])['BD'].apply(lambda group: group.interpolate()).reset_index(level=[0, 1], drop=True)

    return df
