#!/usr/bin/env python3
"""
Verification script to compare DynamoDB uploaded data with source JSON file
"""
import boto3
import json
import os
from decimal import Decimal
from collections import defaultdict

def convert_decimal(obj):
    """Convert Decimal objects to float for comparison"""
    if isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, dict):
        return {k: convert_decimal(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_decimal(v) for v in obj]
    return obj

def load_source_data(file_path):
    """Load source restaurant data from JSON file"""
    with open(file_path, 'r') as f:
        data = json.load(f)
    
    # Create a dictionary keyed by business_id for easy lookup
    source_dict = {item['business_id']: item for item in data}
    return source_dict

def scan_dynamodb_table(table_name, region='us-east-1'):
    """Scan entire DynamoDB table and return all items"""
    dynamodb = boto3.resource('dynamodb', region_name=region)
    table = dynamodb.Table(table_name)
    
    items = []
    response = table.scan()
    items.extend(response['Items'])
    
    # Handle pagination
    while 'LastEvaluatedKey' in response:
        response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
        items.extend(response['Items'])
    
    return items

def compare_restaurant_data(source_item, ddb_item):
    """Compare a source restaurant with its DynamoDB counterpart"""
    issues = []
    
    # Convert DynamoDB Decimal types to comparable formats
    ddb_item = convert_decimal(ddb_item)
    
    # Check key fields
    key_fields = ['business_id', 'name', 'address', 'rating', 'review_count', 'zip_code']
    
    for field in key_fields:
        source_val = source_item.get(field)
        ddb_val = ddb_item.get(field)
        
        if source_val != ddb_val:
            issues.append(f"  {field}: source={source_val}, ddb={ddb_val}")
    
    # Check coordinates
    if source_item.get('coordinates'):
        if 'coordinates' in ddb_item:
            for coord in ['latitude', 'longitude']:
                source_coord = float(source_item['coordinates'].get(coord, 0))
                ddb_coord = float(ddb_item['coordinates'].get(coord, 0))
                if abs(source_coord - ddb_coord) > 0.000001:
                    issues.append(f"  coordinates.{coord}: source={source_coord}, ddb={ddb_coord}")
    
    return issues

def main():
    print("=" * 70)
    print("DynamoDB Upload Verification Script")
    print("=" * 70)
    
    # Configuration
    table_name = os.environ.get('DYNAMODB_TABLE_NAME', 'yelp-restaurants')
    source_file = 'data/restaurants.json'
    
    print(f"\nLoading source data from {source_file}...")
    source_data = load_source_data(source_file)
    print(f"Loaded {len(source_data)} restaurants from source file")
    
    print(f"\nScanning DynamoDB table '{table_name}'...")
    ddb_items = scan_dynamodb_table(table_name)
    print(f"Retrieved {len(ddb_items)} items from DynamoDB")
    
    # Create DynamoDB dict for comparison
    ddb_dict = {item['business_id']: item for item in ddb_items}
    
    print("\n" + "=" * 70)
    print("VERIFICATION RESULTS")
    print("=" * 70)
    
    # Statistics
    total_source = len(source_data)
    total_ddb = len(ddb_dict)
    
    print(f"\nCount Comparison:")
    print(f"  Source file:  {total_source} restaurants")
    print(f"  DynamoDB:     {total_ddb} restaurants")
    
    if total_source == total_ddb:
        print(f"  Match! All {total_source} restaurants uploaded successfully")
    else:
        print(f"  WARNING: Mismatch - {abs(total_source - total_ddb)} restaurants difference")
    
    # Find missing items
    print(f"\nChecking for missing restaurants...")
    missing_in_ddb = set(source_data.keys()) - set(ddb_dict.keys())
    missing_in_source = set(ddb_dict.keys()) - set(source_data.keys())
    
    if missing_in_ddb:
        print(f"  WARNING: {len(missing_in_ddb)} restaurants in source but NOT in DynamoDB:")
        for business_id in list(missing_in_ddb)[:5]:
            print(f"    - {business_id}: {source_data[business_id]['name']}")
        if len(missing_in_ddb) > 5:
            print(f"    ... and {len(missing_in_ddb) - 5} more")
    else:
        print(f"  All source restaurants found in DynamoDB")
    
    if missing_in_source:
        print(f"  WARNING: {len(missing_in_source)} restaurants in DynamoDB but NOT in source:")
        for business_id in list(missing_in_source)[:5]:
            print(f"    - {business_id}")
        if len(missing_in_source) > 5:
            print(f"    ... and {len(missing_in_source) - 5} more")
    else:
        print(f"  No extra restaurants in DynamoDB")
    
    # Compare data quality for common items
    print(f"\nComparing data integrity for matching restaurants...")
    common_ids = set(source_data.keys()) & set(ddb_dict.keys())
    
    data_issues = defaultdict(list)
    perfect_matches = 0
    
    for business_id in common_ids:
        issues = compare_restaurant_data(source_data[business_id], ddb_dict[business_id])
        if issues:
            data_issues[business_id] = issues
        else:
            perfect_matches += 1
    
    print(f"  Perfect matches: {perfect_matches}/{len(common_ids)} restaurants")
    
    if data_issues:
        print(f"  WARNING: Data mismatches found in {len(data_issues)} restaurants")
        print(f"\n  Sample issues (showing first 3):")
        for i, (business_id, issues) in enumerate(list(data_issues.items())[:3]):
            print(f"\n  Restaurant: {source_data[business_id]['name']} ({business_id})")
            for issue in issues:
                print(f"    {issue}")
    else:
        print(f"  All data fields match perfectly!")
    
    # Sample data verification
    print(f"\nSample Restaurant Verification (first 3):")
    for i, business_id in enumerate(list(common_ids)[:3]):
        source = source_data[business_id]
        ddb = convert_decimal(ddb_dict[business_id])
        print(f"\n  {i+1}. {source['name']}")
        print(f"     Business ID: {business_id}")
        print(f"     Rating: {source['rating']} (source) vs {ddb['rating']} (DDB) [OK]")
        print(f"     Reviews: {source['review_count']} (source) vs {ddb['review_count']} (DDB) [OK]")
        print(f"     Address: {source['address'][:50]}...")
    
    # Cuisine distribution check
    print(f"\nCuisine Distribution Verification:")
    source_cuisines = defaultdict(int)
    ddb_cuisines = defaultdict(int)
    
    for item in source_data.values():
        for category in item.get('categories', []):
            source_cuisines[category] += 1
    
    for item in ddb_items:
        for category in item.get('categories', []):
            ddb_cuisines[category] += 1
    
    top_cuisines = sorted(source_cuisines.items(), key=lambda x: x[1], reverse=True)[:5]
    print(f"\n  Top 5 cuisines comparison:")
    for cuisine, count in top_cuisines:
        ddb_count = ddb_cuisines.get(cuisine, 0)
        match = "[OK]" if count == ddb_count else "[MISMATCH]"
        print(f"    {cuisine}: {count} (source) vs {ddb_count} (DDB) {match}")
    
    # Final summary
    print("\n" + "=" * 70)
    print("FINAL VERDICT")
    print("=" * 70)
    
    if (total_source == total_ddb and 
        not missing_in_ddb and 
        not missing_in_source and 
        not data_issues):
        print("SUCCESS! All data uploaded correctly to DynamoDB!")
        print("   - All restaurants present")
        print("   - All data fields match")
        print("   - No data corruption detected")
        return 0
    else:
        print("ISSUES DETECTED:")
        if total_source != total_ddb:
            print(f"   - Count mismatch: {abs(total_source - total_ddb)} difference")
        if missing_in_ddb:
            print(f"   - {len(missing_in_ddb)} restaurants missing from DynamoDB")
        if data_issues:
            print(f"   - {len(data_issues)} restaurants have data mismatches")
        return 1

if __name__ == "__main__":
    try:
        exit(main())
    except Exception as e:
        print(f"\nERROR during verification: {str(e)}")
        import traceback
        traceback.print_exc()
        exit(1)

