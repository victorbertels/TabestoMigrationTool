import streamlit as st
import json
import re
import io

# Page configuration
st.set_page_config(
    page_title="Tabesto Menu Converter",
    page_icon="🍽️",
    layout="centered"
)

st.title("🍽️ Tabesto Menu Converter")
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
                        bundle_group['Name_en'] = 'Choose your option'
                        bundle_group['Name_es'] = 'Choose your option'
                        bundle_group['Name_fr'] = 'Choose your option'
                        bundle_group['PLU'] = f"{meal_sequence['id']}-{step_index}"
                        
                        choices = item.get('choices', [])
                        subproduct_ids = [str(choice.get('reference_id', '')) for choice in choices if choice.get('reference_id')]
                        products = item.get('product_suggestion', {}).get('products', [])
                        subproduct_ids.extend([str(p.get('reference_id', '')) for p in products if p.get('reference_id')])
                        
                        bundle_group['Subproducts'] = ','.join(subproduct_ids)
                        bundle_group['Max'] = 1
                        bundle_group['Min'] = 1
                        bundle_group['Producttype'] = 'BUNDLE'
                        bundle_group['isCombo'] = ''
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
                    row['PLU'] = meal_sequence.get('id', '')
                    
                    miniature_picture_ref = None
                    for pic in meal_sequence.get('pictures', []):
                        if pic.get('type') == 'MINIATURE':
                            miniature_picture_ref = pic.get('reference_id', '')
                            break
                    
                    row['ProductImageID'] = miniature_picture_ref or ''
                    row['Price'] = meal_sequence.get('price', 0) / 100 if meal_sequence.get('price') else ''
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
                    row['Imageurl'] = get_image_url(row['ProductImageID'], image_export_data)
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
                    row['PLU'] = product.get('id', '')
                    
                    miniature_picture_ref = None
                    for pic in product.get('pictures', []):
                        if pic.get('type') == 'MINIATURE':
                            miniature_picture_ref = pic.get('reference_id', '')
                            break
                    
                    row['ProductImageID'] = miniature_picture_ref or ''
                    row['Price'] = product.get('price', 0) / 100 if product.get('price') else ''
                    row['Subproducts'] = ','.join([str(opt.get('reference_id', '')) for opt in product.get('options', []) if opt.get('reference_id')])
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
                    row['Imageurl'] = get_image_url(row['ProductImageID'], image_export_data)
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
                    row['PLU'] = choice.get('id', '')
                    row['Price'] = choice.get('price', 0) / 100 if choice.get('price') else ''
                    
                    choice_ref = None
                    for pc in product_export_data.get('reference', {}).get('product_choice', []):
                        if pc.get('id') == choice.get('id'):
                            choice_ref = pc
                            break
                    
                    row['ProductTags'] = ','.join(choice_ref.get('allergens', [])) if choice_ref else ''
                    row['Producttype'] = 'MODIFIER'
                    row['isCombo'] = 'FALSE'
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
                    row['PLU'] = option.get('id', '')
                    row['Subproducts'] = ','.join([str(c.get('reference_id', '')) for c in option.get('choices', []) if c.get('reference_id')])
                    row['Max'] = option.get('max_allowed', '')
                    row['Min'] = option.get('min_required', '')
                    row['Producttype'] = 'MODIFIER_GROUP'
                    row['isUpsell'] = 'FALSE'
                    row['isCombo'] = ''
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
                        row['PLU'] = suggestion.get('id', '')
                        row['Subproducts'] = ','.join([str(p.get('reference_id', '')) for p in suggestion.get('products', []) if p.get('reference_id')])
                        row['Max'] = 99
                        row['Min'] = 0
                        row['Producttype'] = 'MODIFIER_GROUP'
                        row['isUpsell'] = 'TRUE'
                        row['isCombo'] = ''
                        output_data.append(row)
                
                # FINAL PASS: CATEGORY POPULATION
                status_text.text("Finalizing: Adding categories...")
                progress_bar.progress(95)
                
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
                
                # GENERATE OUTPUT
                output_headers = [
                    'LocationID', 'LocationName', 'PLU', 'Name', 'Name(en)', 'Name(es)', 'Name(fr)', 
                    'Description', 'Description(en)', 'Description(es)', 'Description(fr)', 
                    'Price', 'Producttype', 'ProductImageID', 'Imageurl', 'Category', 
                    'DeliveryTax', 'TakeawayTax', 'EatInTax', 
                    'Subproducts', 'Min', 'Max', 'ProductTags', 'isCombo', 'isUpsell'
                ]
                
                header_to_key = {
                    'Name(en)': 'Name_en',
                    'Name(es)': 'Name_es',
                    'Name(fr)': 'Name_fr',
                    'Description(en)': 'Description_en',
                    'Description(es)': 'Description_es',
                    'Description(fr)': 'Description_fr',
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
                
                # Success message
                st.success(f"✅ Successfully converted {len(output_data)} rows!")
                
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
    <p>🍽️ Tabesto Menu Converter | Built with Streamlit</p>
</div>
""", unsafe_allow_html=True)

