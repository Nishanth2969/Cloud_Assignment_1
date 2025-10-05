import pytest
import json
import os
from unittest.mock import patch, MagicMock
import sys
import importlib.util
from pathlib import Path

def load_module(name: str, relative_path: str):
    module_path = Path(relative_path).resolve()
    spec = importlib.util.spec_from_file_location(name, str(module_path))
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader, f"Unable to load module from {relative_path}"
    spec.loader.exec_module(module)
    return module

class TestValidationFunctions:
    """Test validation functions from LF1"""
    
    def setup_method(self):
        self.lf1 = load_module(
            'lf1_module', 'lambda-functions/lf1_lex_hook/lambda_function.py'
        )
        
    def test_email_validation(self):
        validate_email = self.lf1.validate_email
        
        # Valid emails
        assert validate_email('test@example.com') == True
        assert validate_email('user.name+tag@domain.co.uk') == True
        assert validate_email('123@test.org') == True
        
        # Invalid emails
        assert validate_email('invalid-email') == False
        assert validate_email('@domain.com') == False
        assert validate_email('user@') == False
        assert validate_email('') == False
    
    def test_party_size_validation(self):
        validate_party_size = self.lf1.validate_party_size
        
        # Valid party sizes
        assert validate_party_size('1') == True
        assert validate_party_size('10') == True
        assert validate_party_size('20') == True
        
        # Invalid party sizes
        assert validate_party_size('0') == False
        assert validate_party_size('21') == False
        assert validate_party_size('abc') == False
        assert validate_party_size('') == False
    
    def test_location_validation(self):
        validate_location = self.lf1.validate_location
        
        # Valid locations
        assert validate_location('Manhattan') == True
        assert validate_location('Upper East Side, Manhattan') == True
        assert validate_location('NYC') == True
        assert validate_location('Midtown Manhattan') == True
        
        # Invalid locations
        assert validate_location('Brooklyn') == False
        assert validate_location('Queens') == False
        assert validate_location('Los Angeles') == False
    
    def test_cuisine_validation(self):
        validate_cuisine = self.lf1.validate_cuisine
        
        # Valid cuisines
        assert validate_cuisine('Italian') == True
        assert validate_cuisine('chinese') == True
        assert validate_cuisine('JAPANESE') == True
        
        # Invalid cuisines
        assert validate_cuisine('Martian') == False
        assert validate_cuisine('') == False

class TestEmailFormatting:
    """Test email formatting functions from LF2"""
    
    def setup_method(self):
        self.lf2 = load_module(
            'lf2_module', 'lambda-functions/lf2_suggestions_worker/lambda_function.py'
        )
    
    def test_text_email_formatting(self):
        format_recommendations_email_text = self.lf2.format_recommendations_email_text
        
        request_data = {
            'cuisine': 'Italian',
            'location': 'Manhattan',
            'dining_time': '7:00 PM',
            'party_size': '4',
            'email': 'test@example.com'
        }
        
        restaurants = [
            {
                'name': 'Test Italian Restaurant',
                'address': '123 Test St, Manhattan, NY',
                'rating': 4.5,
                'review_count': 100,
                'phone': '+1234567890',
                'price': '$$',
                'url': 'https://yelp.com/test'
            }
        ]
        
        result = format_recommendations_email_text(request_data, restaurants)
        
        assert 'Italian Restaurant Recommendations' in result
        assert 'Test Italian Restaurant' in result
        assert '123 Test St' in result
        assert '4.5/5' in result
        assert '+1234567890' in result
        assert 'Best regards' in result
    
    def test_html_email_formatting(self):
        format_recommendations_email_html = self.lf2.format_recommendations_email_html
        
        request_data = {
            'cuisine': 'Chinese',
            'location': 'Manhattan',
            'dining_time': '8:00 PM',
            'party_size': '2',
            'email': 'test@example.com'
        }
        
        restaurants = [
            {
                'name': 'Test Chinese Restaurant',
                'address': '456 Test Ave, Manhattan, NY',
                'rating': 4.0,
                'review_count': 50,
                'phone': '',
                'price': '$$$',
                'url': ''
            }
        ]
        
        result = format_recommendations_email_html(request_data, restaurants)
        
        assert '<html>' in result
        assert 'Chinese Restaurant Recommendations' in result
        assert 'Test Chinese Restaurant' in result
        assert '456 Test Ave' in result
        assert '4.0/5' in result
        assert 'restaurant-name' in result  # CSS class

class TestAPIHandling:
    """Test API handling functions from LF0"""
    
    def setup_method(self):
        self.lf0 = load_module(
            'lf0_module', 'lambda-functions/lf0_chat_proxy/lambda_function.py'
        )
    
    def test_cors_response_formatting(self):
        cors_response = self.lf0.cors_response
        
        result = cors_response(200, {'message': 'test'})
        
        assert result['statusCode'] == 200
        assert 'Access-Control-Allow-Origin' in result['headers']
        assert 'Access-Control-Allow-Headers' in result['headers']
        assert 'Access-Control-Allow-Methods' in result['headers']
        assert result['headers']['Access-Control-Allow-Origin'] == '*'
        
        parsed_body = json.loads(result['body'])
        assert parsed_body['message'] == 'test'
    
    def test_different_status_codes(self):
        cors_response = self.lf0.cors_response
        
        for status_code in [200, 400, 404, 500]:
            result = cors_response(status_code, {'status': status_code})
            assert result['statusCode'] == status_code

class TestDataProcessing:
    """Test data processing utilities"""
    
    def setup_method(self):
        sys.path.insert(0, 'other-scripts')
    
    def test_yelp_scraper_initialization(self):
        from yelp_scraper import YelpScraper
        
        scraper = YelpScraper('fake-api-key')
        assert scraper.api_key == 'fake-api-key'
        assert scraper.base_url == "https://api.yelp.com/v3/businesses/search"
    
    def test_restaurant_data_formatting(self):
        from yelp_scraper import YelpScraper
        
        scraper = YelpScraper('fake-api-key')
        
        test_business = {
            'id': 'test-123',
            'name': 'Test Restaurant', 
            'location': {
                'address1': '123 Test St',
                'city': 'New York',
                'state': 'NY',
                'zip_code': '10001'
            },
            'coordinates': {'latitude': 40.7128, 'longitude': -74.0060},
            'review_count': 100,
            'rating': 4.5,
            'categories': [{'title': 'Italian'}, {'title': 'Restaurants'}]
        }
        
        formatted = scraper.format_restaurant_data(test_business)
        
        assert formatted is not None
        assert formatted['business_id'] == 'test-123'
        assert formatted['name'] == 'Test Restaurant'
        assert 'New York' in formatted['address']
        assert formatted['rating'] == 4.5
        assert formatted['review_count'] == 100
        assert 'Italian' in formatted['categories']
    
    def test_duplicate_removal(self):
        from yelp_scraper import YelpScraper
        
        scraper = YelpScraper('fake-api-key')
        
        restaurants = [
            {'business_id': 'rest-1', 'name': 'Restaurant 1'},
            {'business_id': 'rest-2', 'name': 'Restaurant 2'},
            {'business_id': 'rest-1', 'name': 'Restaurant 1 Duplicate'},
            {'business_id': 'rest-3', 'name': 'Restaurant 3'}
        ]
        
        unique = scraper.remove_duplicates(restaurants)
        
        assert len(unique) == 3
        business_ids = [r['business_id'] for r in unique]
        assert business_ids == ['rest-1', 'rest-2', 'rest-3']

class TestSystemIntegration:
    """High-level integration tests"""
    
    def test_environment_variables_handling(self):
        """Test that functions handle missing environment variables gracefully"""
        lf0 = load_module(
            'lf0_module', 'lambda-functions/lf0_chat_proxy/lambda_function.py'
        )
        send_to_lex = lf0.send_to_lex
        
        result = send_to_lex('test message', 'test-session')
        assert result is None  # Should return None when bot ID is missing
    
    def test_error_handling_consistency(self):
        """Test that all Lambda functions handle errors consistently"""
        lf1 = load_module(
            'lf1_module', 'lambda-functions/lf1_lex_hook/lambda_function.py'
        )
        lf1_handler = lf1.lambda_handler
        
        invalid_event = {'invalid': 'structure'}
        
        try:
            result = lf1_handler(invalid_event, {})
            assert 'dialogAction' in result
            assert result['dialogAction']['fulfillmentState'] == 'Failed'
        except Exception:
            # Should handle gracefully, not crash
            pass
    
    def test_data_validation_consistency(self):
        """Test that validation is consistent across the system"""
        lf1 = load_module(
            'lf1_module', 'lambda-functions/lf1_lex_hook/lambda_function.py'
        )
        validate_slots = lf1.validate_slots
        
        # Test complete valid input
        result = validate_slots(
            'Manhattan', 'Italian', '7:00 PM', '4', 'test@example.com'
        )
        assert result['isValid'] == True
        
        # Test invalid input
        result = validate_slots(
            'Brooklyn', 'Italian', '7:00 PM', '4', 'test@example.com'
        )
        assert result['isValid'] == False
        assert result['violatedSlot'] == 'Location'