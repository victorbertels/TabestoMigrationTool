import streamlit as st
import json
import re
import io
import os

# Page configuration
st.set_page_config(
    page_title="Tabesto Menu Converter",
    page_icon="🍽️",
    layout="centered"
)

# Counter management
COUNTER_FILE = "usage_counter.json"

def load_counter():
    """Load the usage counter from file"""
    if os.path.exists(COUNTER_FILE):
        try:
            with open(COUNTER_FILE, 'r') as f:
                data = json.load(f)
                return data.get('count', 0)
        except:
            return 0
    return 0

def increment_counter():
    """Increment and save the usage counter"""
    count = load_counter()
    count += 1
    with open(COUNTER_FILE, 'w') as f:
        json.dump({'count': count}, f)
    return count

# Display header with counter
st.title("🍽️ Tabesto Menu Converter 2.0")

# Display usage counter prominently
current_count = load_counter()
st.markdown(f"""
<div style='text-align: center; margin: 20px 0;'>
    <div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 20px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);'>
        <div style='color: rgba(255,255,255,0.9); font-size: 1em; margin-bottom: 10px; font-weight: 500;'>Built by MALI & V1C</div>
        <div style='color: white; font-size: 1.2em; margin-bottom: 5px;'>Total Conversions</div>
        <div style='color: white; font-size: 4em; font-weight: bold; font-family: monospace;'>{current_count:,}</div>
    </div>
</div>
""", unsafe_allow_html=True)

st.markdown("""
Upload your **PRODUCT IMPORT** and **IMAGE EXPORT** JSON files to convert them into a TAB_DLV import template.
""")

# File uploaders
col1, col2 = st.columns(2)

with col1:
    product_file = st.file_uploader("📄 Upload PRODUCT IMPORT.json", type=['json'])

with col2:
    image_file = st.file_uploader("🖼️ Upload IMAGE EXPORT.json", type=['json'])

# Process button
if product_file and image_file:
    if st.button("🚀 Convert Files", type="primary"):
        with st.spinner("Processing your files..."):
            try:
                # Load the JSON files
                product_export_data = json.load(product_file)
                image_data = json.load(image_file)
                image_export_data = image_data.get('pictures', [])
                
                output_data = []
                
                # Helper function to find a specific language text
                def get_lang_text(data, lang):
                    if data and 'data' in data:
                        for item in data['data']:
                            if item.get('lang') == lang:
                                return item.get('text', '')
                    return ''
                
                # Helper function to find Image URL and clean it
                def get_image_url(image_ref_id, image_export_data):
                    if not image_ref_id:
                        return ''
                    for image in image_export_data:
                        if image.get('id') == image_ref_id:
                            image_url = image.get('url', '')
                            if image_url:
                                return re.sub(r'(upload/).*?(tabesto/)', r'\1\2', image_url)
                    return ''
                
                # Global constants
                common_fields = {
                    'LocationID': 'All locations',
                    'LocationName': 'All locations',
                    'DeliveryTax': 10,
                    'TakeawayTax': 10,
                    'EatInTax': 10
                }
                
                def create_base_row():
                    return common_fields.copy()
                
                # Progress bar
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                # STEP 1: CREATE BUNDLE GROUPS FOR MEAL DEALS
                status_text.text("Step 1/6: Creating bundle groups...")
                progress_bar.progress(10)
                
                bundle_groups = []
                for meal_sequence in product_export_data.get('reference', {}).get('meal_sequence', []):
                    for step_index, item in enumerate(meal_sequence.get('items', [])):
                        bundle_group = create_base_row()
                        bundle_group['Name'] = 'Choose your option'
                        bundle_group['Name_en'] = ''  # Blank for bundles
                        bundle_group['Name_es'] = ''  # Blank for bundles
                        bundle_group['Name_fr'] = ''  # Blank for bundles
                        
                        # Store original PLU (will be prefixed later based on output columns)
                        bundle_plu = f"{meal_sequence['id']}-{step_index}"
                        bundle_group['PLU'] = bundle_plu
                        bundle_group['Multiple'] = 1  # Always 1 for bundles
                        
                        # Collect subproduct IDs (original IDs, will be mapped later)
                        choices = item.get('choices', [])
                        subproduct_ids = [str(choice.get('reference_id', '')) for choice in choices if choice.get('reference_id')]
                        products = item.get('product_suggestion', {}).get('products', [])
                        subproduct_ids.extend([str(p.get('reference_id', '')) for p in products if p.get('reference_id')])
                        
                        bundle_group['Subproducts'] = ','.join(subproduct_ids)
                        bundle_group['Max'] = 1
                        bundle_group['Min'] = 1
                        bundle_group['Producttype'] = 'BUNDLE'
                        bundle_group['isCombo'] = ''
                        bundle_group['Isinternal'] = ''  # Blank for bundles
                        bundle_groups.append(bundle_group)
                
                output_data.extend(bundle_groups)
                
                # STEP 2: MEAL DEALS
                status_text.text("Step 2/6: Processing meal deals...")
                progress_bar.progress(25)
                
                for meal_sequence in product_export_data.get('reference', {}).get('meal_sequence', []):
                    row = create_base_row()
                    row['Name'] = get_lang_text(meal_sequence.get('name'), 'fr_FR')
                    row['Name_en'] = get_lang_text(meal_sequence.get('name'), 'en_GB')
                    row['Name_es'] = get_lang_text(meal_sequence.get('name'), 'es_ES')
                    row['Name_fr'] = get_lang_text(meal_sequence.get('name'), 'fr_FR')
                    
                    # Store original PLU (will be prefixed later)
                    row['PLU'] = str(meal_sequence.get('id', ''))
                    
                    miniature_picture_ref = None
                    for pic in meal_sequence.get('pictures', []):
                        if pic.get('type') == 'MINIATURE':
                            miniature_picture_ref = pic.get('reference_id', '')
                            break
                    
                    row['ProductImageID'] = miniature_picture_ref or ''
                    row['Price'] = meal_sequence.get('price', 0) / 100 if meal_sequence.get('price') else ''
                    
                    # Get matching bundle PLUs (original IDs, will be mapped later)
                    matching_bundles = [bg['PLU'] for bg in bundle_groups if bg['PLU'].startswith(f"{meal_sequence['id']}-")]
                    row['Subproducts'] = ','.join(matching_bundles)
                    
                    product_ref = None
                    for product in product_export_data.get('reference', {}).get('product', []):
                        if product.get('id') == meal_sequence.get('id'):
                            product_ref = product
                            break
                    
                    row['Description'] = get_lang_text(product_ref.get('description') if product_ref else None, 'fr_FR')
                    row['Description_en'] = get_lang_text(product_ref.get('description') if product_ref else None, 'en_GB')
                    row['Description_es'] = get_lang_text(product_ref.get('description') if product_ref else None, 'es_ES')
                    row['Description_fr'] = get_lang_text(product_ref.get('description') if product_ref else None, 'fr_FR')
                    row['ProductTags'] = ','.join(product_ref.get('allergens', [])) if product_ref else ''
                    row['Producttype'] = 'PRODUCT'
                    row['isCombo'] = 'TRUE'
                    row['Isinternal'] = 'TRUE'  # Set to TRUE when isCombo is TRUE
                    row['Imageurl'] = get_image_url(row.get('ProductImageID', ''), image_export_data)
                    row['Category'] = ''
                    output_data.append(row)
                
                # STEP 3: PRODUCTS
                status_text.text("Step 3/6: Processing products...")
                progress_bar.progress(40)
                
                for product in product_export_data.get('reference', {}).get('product', []):
                    row = create_base_row()
                    row['Name'] = get_lang_text(product.get('name'), 'fr_FR')
                    row['Name_en'] = get_lang_text(product.get('name'), 'en_GB')
                    row['Name_es'] = get_lang_text(product.get('name'), 'es_ES')
                    row['Name_fr'] = get_lang_text(product.get('name'), 'fr_FR')
                    
                    # Store original PLU (will be prefixed later)
                    row['PLU'] = str(product.get('id', ''))
                    
                    miniature_picture_ref = None
                    for pic in product.get('pictures', []):
                        if pic.get('type') == 'MINIATURE':
                            miniature_picture_ref = pic.get('reference_id', '')
                            break
                    
                    row['ProductImageID'] = miniature_picture_ref or ''
                    row['Price'] = product.get('price', 0) / 100 if product.get('price') else ''
                    
                    # Store original subproduct IDs (will be mapped later)
                    option_ids = [str(opt.get('reference_id', '')) for opt in product.get('options', []) if opt.get('reference_id')]
                    row['Subproducts'] = ','.join(option_ids)
                    
                    row['Description'] = get_lang_text(product.get('description'), 'fr_FR')
                    row['Description_en'] = get_lang_text(product.get('description'), 'en_GB')
                    row['Description_es'] = get_lang_text(product.get('description'), 'es_ES')
                    row['Description_fr'] = get_lang_text(product.get('description'), 'fr_FR')
                    
                    quantity_info = product.get('modifier_groups', {}).get('quantity_info', {}).get('quantity', {})
                    row['Max'] = quantity_info.get('max_permitted', '')
                    row['Min'] = quantity_info.get('min_permitted', '')
                    row['ProductTags'] = ','.join(product.get('allergens', []))
                    row['Producttype'] = 'PRODUCT'
                    row['isCombo'] = 'FALSE'
                    row['Isinternal'] = 'FALSE'  # FALSE for regular products
                    row['Imageurl'] = get_image_url(row.get('ProductImageID', ''), image_export_data)
                    row['Category'] = ''
                    output_data.append(row)
                
                # STEP 4: MODIFIER
                status_text.text("Step 4/6: Processing modifiers...")
                progress_bar.progress(55)
                
                for choice in product_export_data.get('reference', {}).get('product_option_choice', []):
                    row = create_base_row()
                    row['Name'] = get_lang_text(choice.get('name'), 'fr_FR')
                    row['Name_en'] = get_lang_text(choice.get('name'), 'en_GB')
                    row['Name_es'] = get_lang_text(choice.get('name'), 'es_ES')
                    row['Name_fr'] = get_lang_text(choice.get('name'), 'fr_FR')
                    
                    # Store original PLU (will be prefixed later)
                    row['PLU'] = str(choice.get('id', ''))
                    
                    # Always set to 0 if no price for MODIFIER
                    row['Price'] = choice.get('price', 0) / 100 if choice.get('price') else 0
                    
                    choice_ref = None
                    for pc in product_export_data.get('reference', {}).get('product_choice', []):
                        if pc.get('id') == choice.get('id'):
                            choice_ref = pc
                            break
                    
                    row['ProductTags'] = ','.join(choice_ref.get('allergens', [])) if choice_ref else ''
                    row['Producttype'] = 'MODIFIER'
                    row['isCombo'] = 'FALSE'
                    row['Isinternal'] = ''  # Blank for modifiers
                    output_data.append(row)
                
                # STEP 5: MODIFIER GROUP
                status_text.text("Step 5/6: Processing modifier groups...")
                progress_bar.progress(70)
                
                for option in product_export_data.get('reference', {}).get('product_option', []):
                    row = create_base_row()
                    product_ref_for_name = None
                    for product in product_export_data.get('reference', {}).get('product', []):
                        if product.get('id') == option.get('id'):
                            product_ref_for_name = product
                            break
                    
                    if product_ref_for_name:
                        row['Name'] = get_lang_text(product_ref_for_name.get('name'), 'fr_FR')
                    else:
                        row['Name'] = get_lang_text(option.get('name'), 'fr_FR')
                    
                    row['Name_en'] = get_lang_text(option.get('name'), 'en_GB')
                    row['Name_es'] = get_lang_text(option.get('name'), 'es_ES')
                    row['Name_fr'] = get_lang_text(option.get('name'), 'fr_FR')
                    
                    # Store original PLU (will be prefixed later)
                    row['PLU'] = str(option.get('id', ''))
                    
                    # Store original subproduct IDs (will be mapped later)
                    choice_ids = [str(c.get('reference_id', '')) for c in option.get('choices', []) if c.get('reference_id')]
                    row['Subproducts'] = ','.join(choice_ids)
                    
                    row['Max'] = option.get('max_allowed', '')
                    row['Min'] = option.get('min_required', '')
                    row['Producttype'] = 'MODIFIER_GROUP'
                    row['isUpsell'] = 'FALSE'
                    row['isCombo'] = ''
                    row['Isinternal'] = ''  # Blank for modifier groups
                    output_data.append(row)
                
                # STEP 6: UPSELL GROUP
                status_text.text("Step 6/6: Processing upsell groups...")
                progress_bar.progress(85)
                
                for suggestion in product_export_data.get('reference', {}).get('product_suggestion', []):
                    if suggestion.get('type') == 'ADDITIONAL':
                        row = create_base_row()
                        row['Name'] = get_lang_text(suggestion.get('name'), 'fr_FR')
                        row['Name_en'] = get_lang_text(suggestion.get('name'), 'en_GB')
                        row['Name_es'] = get_lang_text(suggestion.get('name'), 'es_ES')
                        row['Name_fr'] = get_lang_text(suggestion.get('name'), 'fr_FR')
                        
                        # Store original PLU (will be prefixed later)
                        row['PLU'] = str(suggestion.get('id', ''))
                        
                        # Store original subproduct IDs (will be mapped later)
                        product_ids = [str(p.get('reference_id', '')) for p in suggestion.get('products', []) if p.get('reference_id')]
                        row['Subproducts'] = ','.join(product_ids)
                        
                        row['Max'] = 99
                        row['Min'] = 0
                        row['Producttype'] = 'MODIFIER_GROUP'
                        row['isUpsell'] = 'TRUE'
                        row['isCombo'] = ''
                        row['Isinternal'] = ''  # Blank for upsell groups
                        output_data.append(row)
                
                # STEP 7: CATEGORY POPULATION
                status_text.text("Step 7/8: Adding categories...")
                progress_bar.progress(85)
                
                categories = {}
                for category in product_export_data.get('reference', {}).get('category', []):
                    product_ids = tuple([str(p.get('reference_id', '')) for p in category.get('products', []) if p.get('reference_id')])
                    category_name = get_lang_text(category.get('name'), 'fr_FR')
                    categories[product_ids] = category_name
                
                for row in output_data:
                    if row.get('Producttype') == 'PRODUCT' and row.get('PLU'):
                        found_category = ''
                        for product_ids, name in categories.items():
                            if str(row['PLU']) in product_ids:
                                found_category = name
                                break
                        row['Category'] = found_category
                
                # STEP 8: APPLY PLU PREFIXES BASED ON OUTPUT COLUMNS
                status_text.text("Step 8/8: Applying PLU prefixes...")
                progress_bar.progress(92)
                
                # PASS 1: Apply prefix to each row based on its OWN properties
                for row in output_data:
                    original_plu = str(row.get('PLU', ''))
                    if not original_plu:
                        continue
                    
                    producttype = row.get('Producttype', '')
                    is_combo = row.get('isCombo', '')
                    is_upsell = row.get('isUpsell', '')
                    
                    # Determine prefix based on THIS row's columns
                    if producttype == 'MODIFIER':
                        row['PLU'] = f"M{original_plu}"
                    elif producttype == 'PRODUCT' and is_combo == 'FALSE':
                        row['PLU'] = f"P{original_plu}"
                    elif producttype == 'PRODUCT' and is_combo == 'TRUE':
                        row['PLU'] = f"MD{original_plu}"
                    elif producttype == 'MODIFIER_GROUP' and is_upsell == 'FALSE':
                        row['PLU'] = f"MG{original_plu}"
                    elif producttype == 'MODIFIER_GROUP' and is_upsell == 'TRUE':
                        row['PLU'] = f"UG{original_plu}"
                    elif producttype == 'BUNDLE':
                        row['PLU'] = original_plu  # Bundles don't get prefixed
                    else:
                        row['PLU'] = original_plu  # Default: no prefix
                
                # PASS 2: Build map from original IDs to prefixed PLUs
                # For subproduct references, we need to know: given an original ID, what are ALL the possible prefixed PLUs?
                # Build reverse map: original_id -> list of prefixed PLUs
                id_to_prefixed = {}
                for row in output_data:
                    prefixed_plu = row.get('PLU', '')
                    # Extract original ID from prefixed PLU
                    original_id = prefixed_plu
                    if prefixed_plu.startswith('MD'):
                        original_id = prefixed_plu[2:]
                    elif prefixed_plu.startswith('MG') or prefixed_plu.startswith('UG'):
                        original_id = prefixed_plu[2:]
                    elif prefixed_plu.startswith('M') or prefixed_plu.startswith('P'):
                        original_id = prefixed_plu[1:]
                    
                    if original_id:
                        if original_id not in id_to_prefixed:
                            id_to_prefixed[original_id] = []
                        if prefixed_plu not in id_to_prefixed[original_id]:
                            id_to_prefixed[original_id].append(prefixed_plu)
                
                # PASS 3: Update Subproducts to use prefixed PLUs
                # Rules for which prefix to use based on parent type:
                # - BUNDLE → only P (products)
                # - PRODUCT (isCombo=FALSE) → only MG (modifier groups)
                # - PRODUCT (isCombo=TRUE) → only BUNDLE (unprefixed with '-')
                # - MODIFIER_GROUP (isUpsell=FALSE) → only M (modifiers)
                # - MODIFIER_GROUP (isUpsell=TRUE) → only P (products)
                
                for row in output_data:
                    subproducts = row.get('Subproducts', '')
                    if not subproducts:
                        continue
                    
                    producttype = row.get('Producttype', '')
                    is_combo = row.get('isCombo', '')
                    is_upsell = row.get('isUpsell', '')
                    
                    original_ids = subproducts.split(',')
                    prefixed_ids = []
                    
                    for orig_id in original_ids:
                        orig_id = orig_id.strip()
                        if orig_id in id_to_prefixed:
                            possible_plus = id_to_prefixed[orig_id]
                            
                            # Filter based on parent type
                            if producttype == 'BUNDLE':
                                # Bundles can only contain P-prefixed PLUs (products)
                                matching = [p for p in possible_plus if p.startswith('P') and not p.startswith('MD')]
                            elif producttype == 'PRODUCT' and is_combo == 'FALSE':
                                # Regular products can only contain MG-prefixed PLUs (modifier groups)
                                matching = [p for p in possible_plus if p.startswith('MG')]
                            elif producttype == 'PRODUCT' and is_combo == 'TRUE':
                                # Combo products can only contain BUNDLE PLUs (unprefixed with '-')
                                matching = [p for p in possible_plus if '-' in p and not any(p.startswith(x) for x in ['P', 'M', 'UG'])]
                            elif producttype == 'MODIFIER_GROUP' and is_upsell == 'FALSE':
                                # Modifier groups can only contain M-prefixed PLUs (modifiers)
                                matching = [p for p in possible_plus if p.startswith('M') and not p.startswith('MG') and not p.startswith('MD')]
                            elif producttype == 'MODIFIER_GROUP' and is_upsell == 'TRUE':
                                # Upsell groups can only contain P-prefixed PLUs (products)
                                matching = [p for p in possible_plus if p.startswith('P') and not p.startswith('MD')]
                            else:
                                matching = possible_plus
                            
                            if matching:
                                prefixed_ids.extend(matching)
                            else:
                                # If no match found, keep original
                                prefixed_ids.append(orig_id)
                        else:
                            # Keep original if not in map
                            prefixed_ids.append(orig_id)
                    
                    row['Subproducts'] = ','.join(prefixed_ids)
                
                # GENERATE OUTPUT with new order
                output_headers = [
                    'Name', 'Name(en)', 'Name(es)', 'Name(fr)',
                    'LocationID', 'LocationName', 'Multiple(bundles)', 'PLU',
                    'Price', 'DeliveryTax', 'TakeawayTax', 'EatInTax',
                    'Subproducts', 'Imageurl',
                    'Description', 'Description(en)', 'Description(es)', 'Description(fr)',
                    'Max', 'Min', 'Isinternal(combos)',
                    'Category', 'ProductTags', 'Producttype',
                    'isCombo', 'isUpsell'
                ]
                
                header_to_key = {
                    'Name(en)': 'Name_en',
                    'Name(es)': 'Name_es',
                    'Name(fr)': 'Name_fr',
                    'Description(en)': 'Description_en',
                    'Description(es)': 'Description_es',
                    'Description(fr)': 'Description_fr',
                    'Multiple(bundles)': 'Multiple',
                    'Isinternal(combos)': 'Isinternal',
                }
                
                final_output = '\t'.join(output_headers) + '\n'
                for row in output_data:
                    line_values = []
                    for header in output_headers:
                        key = header_to_key.get(header, header)
                        value = row.get(key, '')
                        line_values.append(str(value) if value is not None and value != '' else '')
                    final_output += '\t'.join(line_values) + '\n'
                
                progress_bar.progress(100)
                status_text.text("✅ Conversion complete!")
                
                # Increment usage counter
                new_count = increment_counter()
                
                # Success message
                st.success(f"✅ Successfully converted {len(output_data)} rows!")
                st.info(f"🎉 This is conversion #{new_count:,}!")
                
                # Display statistics
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Rows", len(output_data))
                with col2:
                    bundles = len([r for r in output_data if r.get('Producttype') == 'BUNDLE'])
                    st.metric("Bundles", bundles)
                with col3:
                    products = len([r for r in output_data if r.get('Producttype') == 'PRODUCT'])
                    st.metric("Products", products)
                
                # Download button with UTF-8 BOM
                tsv_bytes = final_output.encode('utf-8-sig')
                st.download_button(
                    label="⬇️ Download TAB_DLV_IMPORT.tsv",
                    data=tsv_bytes,
                    file_name="TAB_DLV_IMPORT_OUTPUT.tsv",
                    mime="text/tab-separated-values",
                    type="primary"
                )
                
                # Show preview
                with st.expander("📊 Preview First 10 Rows"):
                    preview_lines = final_output.split('\n')[:11]
                    st.code('\n'.join(preview_lines), language=None)
                
            except Exception as e:
                st.error(f"❌ Error processing files: {str(e)}")
                st.exception(e)

else:
    st.info("👆 Please upload both JSON files to begin conversion.")

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: gray; font-size: 0.9em;'>
    <p>🍽️ Tabesto Menu Converter | Built by MALI & V1C</p>
</div>
""", unsafe_allow_html=True)

