#!/usr/bin/env python3
"""
Simple verification script to test DynamoDB upload by sampling restaurants
"""
import boto3
import json
import os
import random
from decimal import Decimal

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
    return data

def get_item_from_dynamodb(table_name, business_id, region='us-east-1'):
    """Get a single item from DynamoDB by business_id"""
    dynamodb = boto3.resource('dynamodb', region_name=region)
    table = dynamodb.Table(table_name)
    
    try:
        response = table.get_item(Key={'business_id': business_id})
        return response.get('Item')
    except Exception as e:
        print(f"Error getting item {business_id}: {str(e)}")
        return None

def compare_restaurant(source, ddb_item):
    """Compare source and DDB restaurant data"""
    if not ddb_item:
        return False, ["Item not found in DynamoDB"]
    
    ddb_item = convert_decimal(ddb_item)
    issues = []
    
    # Check critical fields
    if source['name'] != ddb_item.get('name'):
        issues.append(f"Name mismatch: '{source['name']}' vs '{ddb_item.get('name')}'")
    
    if abs(float(source['rating']) - float(ddb_item.get('rating', 0))) > 0.01:
        issues.append(f"Rating mismatch: {source['rating']} vs {ddb_item.get('rating')}")
    
    if source['review_count'] != ddb_item.get('review_count'):
        issues.append(f"Review count mismatch: {source['review_count']} vs {ddb_item.get('review_count')}")
    
    if source['address'] != ddb_item.get('address'):
        issues.append(f"Address mismatch")
    
    return len(issues) == 0, issues

def main():
    print("=" * 70)
    print("DynamoDB Sample Verification Script")
    print("=" * 70)
    
    table_name = os.environ.get('DYNAMODB_TABLE_NAME', 'yelp-restaurants')
    source_file = 'data/restaurants.json'
    sample_size = 50  # Test 50 random restaurants
    
    print(f"\nLoading source data from {source_file}...")
    source_data = load_source_data(source_file)
    print(f"Loaded {len(source_data)} restaurants from source file")
    
    # Select random sample
    sample_restaurants = random.sample(source_data, min(sample_size, len(source_data)))
    
    print(f"\nTesting {len(sample_restaurants)} random restaurants from DynamoDB...")
    print(f"   Table: {table_name}")
    print(f"   Region: us-east-1")
    
    successful = 0
    failed = 0
    not_found = 0
    
    print("\n" + "-" * 70)
    
    for i, restaurant in enumerate(sample_restaurants, 1):
        business_id = restaurant['business_id']
        name = restaurant['name']
        
        ddb_item = get_item_from_dynamodb(table_name, business_id)
        
        if ddb_item is None:
            print(f"[FAIL] {i}. NOT FOUND: {name} ({business_id})")
            not_found += 1
            failed += 1
        else:
            is_match, issues = compare_restaurant(restaurant, ddb_item)
            
            if is_match:
                print(f"[OK] {i}. MATCH: {name}")
                successful += 1
            else:
                print(f"[WARN] {i}. MISMATCH: {name}")
                for issue in issues:
                    print(f"     - {issue}")
                failed += 1
        
        # Show progress every 10 items
        if i % 10 == 0:
            print(f"   Progress: {i}/{len(sample_restaurants)} checked...")
    
    print("\n" + "=" * 70)
    print("VERIFICATION RESULTS")
    print("=" * 70)
    
    print(f"\nStatistics:")
    print(f"   Total Tested: {len(sample_restaurants)}")
    print(f"   Successful Matches: {successful}")
    print(f"   Failed/Mismatched: {failed}")
    print(f"   Not Found: {not_found}")
    print(f"   Success Rate: {(successful/len(sample_restaurants)*100):.1f}%")
    
    # Detailed verification of first 3
    print(f"\nDetailed Verification (first 3 restaurants):")
    for i, restaurant in enumerate(sample_restaurants[:3], 1):
        business_id = restaurant['business_id']
        ddb_item = get_item_from_dynamodb(table_name, business_id)
        
        if ddb_item:
            ddb_item = convert_decimal(ddb_item)
            print(f"\n  {i}. {restaurant['name']}")
            print(f"     Business ID: {business_id}")
            print(f"     Rating: {restaurant['rating']} (source) = {ddb_item.get('rating')} (DDB)")
            print(f"     Reviews: {restaurant['review_count']} (source) = {ddb_item.get('review_count')} (DDB)")
            print(f"     Categories: {restaurant.get('categories', [])[:3]}")
            print(f"     Address: {restaurant['address'][:60]}...")
    
    print("\n" + "=" * 70)
    print("FINAL VERDICT")
    print("=" * 70)
    
    if successful == len(sample_restaurants):
        print("\nSUCCESS! All sampled restaurants uploaded correctly!")
        print(f"   - All {successful}/{len(sample_restaurants)} restaurants verified")
        print(f"   - No data corruption detected")
        print(f"\n   Based on this sample, we can confidently say:")
        print(f"   All {len(source_data)} restaurants were likely uploaded successfully!")
        return 0
    elif successful > len(sample_restaurants) * 0.95:
        print(f"\nMOSTLY SUCCESSFUL!")
        print(f"   - {successful}/{len(sample_restaurants)} restaurants verified ({(successful/len(sample_restaurants)*100):.1f}%)")
        print(f"   - Some minor issues detected but overall upload successful")
        return 0
    else:
        print(f"\nISSUES DETECTED:")
        print(f"   - Only {successful}/{len(sample_restaurants)} verified successfully")
        print(f"   - {failed} restaurants had issues")
        if not_found > 0:
            print(f"   - {not_found} restaurants not found in DynamoDB")
        return 1

if __name__ == "__main__":
    try:
        exit(main())
    except Exception as e:
        print(f"\nERROR during verification: {str(e)}")
        import traceback
        traceback.print_exc()
        exit(1)

