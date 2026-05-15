"""
Test Suite for OpportunityModel
Tests: ORM model, Pydantic validation, hash generation, database operations
"""

import pytest
from datetime import datetime, timedelta
from opportunity import (
    OpportunityModel,
    OpportunityCreate,
    OpportunityUpdate,
    OpportunityResponse,
    generate_source_hash,
)


# ============================================================================
# TESTS FOR HASH GENERATION
# ============================================================================

class TestHashGeneration:
    """Test MD5 hash generation for deduplication"""
    
    def test_hash_length(self):
        """Hash should be 32 characters (MD5)"""
        hash_val = generate_source_hash(
            "Python Internship",
            "Google",
            datetime(2026, 12, 31)
        )
        assert len(hash_val) == 32
        assert hash_val.islower()
    
    def test_hash_consistency(self):
        """Same input should produce same hash"""
        title = "Python Internship"
        org = "Google"
        deadline = datetime(2026, 12, 31)
        
        hash1 = generate_source_hash(title, org, deadline)
        hash2 = generate_source_hash(title, org, deadline)
        
        assert hash1 == hash2
    
    def test_hash_uniqueness(self):
        """Different inputs should produce different hashes"""
        hash1 = generate_source_hash("Python Internship", "Google", datetime(2026, 12, 31))
        hash2 = generate_source_hash("Java Internship", "Google", datetime(2026, 12, 31))
        hash3 = generate_source_hash("Python Internship", "Microsoft", datetime(2026, 12, 31))
        hash4 = generate_source_hash("Python Internship", "Google", datetime(2027, 12, 31))
        
        assert hash1 != hash2
        assert hash1 != hash3
        assert hash1 != hash4
        assert len({hash1, hash2, hash3, hash4}) == 4
    
    def test_hash_case_insensitive(self):
        """Hash should ignore case"""
        hash1 = generate_source_hash("Python Internship", "Google", datetime(2026, 12, 31))
        hash2 = generate_source_hash("PYTHON INTERNSHIP", "GOOGLE", datetime(2026, 12, 31))
        
        assert hash1 == hash2
    
    def test_hash_whitespace_handling(self):
        """Hash should ignore extra whitespace"""
        hash1 = generate_source_hash("Python Internship", "Google", datetime(2026, 12, 31))
        hash2 = generate_source_hash("  Python Internship  ", "  Google  ", datetime(2026, 12, 31))
        
        assert hash1 == hash2


# ============================================================================
# TESTS FOR PYDANTIC MODELS (VALIDATION)
# ============================================================================

class TestOpportunityValidation:
    """Test Pydantic model validation"""
    
    def get_valid_opportunity_data(self):
        """Helper to create valid opportunity data"""
        return {
            'source': 'TCET',
            'source_url': 'https://tcetcercd.in/internship/123',
            'opportunity_type': 'internship',
            'title': 'Python Internship',
            'organization': 'Google',
            'description': 'Work on exciting projects',
            'deadline': datetime.now() + timedelta(days=30),
            'is_paid': True,
            'salary_min': 50000,
            'salary_max': 75000,
        }
    
    def test_valid_opportunity_creation(self):
        """Valid data should create OpportunityCreate successfully"""
        data = self.get_valid_opportunity_data()
        opp = OpportunityCreate(**data)
        
        assert opp.source == 'TCET'
        assert opp.title == 'Python Internship'
        assert opp.organization == 'Google'
        assert opp.opportunity_type == 'internship'
    
    def test_invalid_source(self):
        """Invalid source should raise validation error"""
        data = self.get_valid_opportunity_data()
        data['source'] = 'InvalidSource'
        
        with pytest.raises(ValueError, match='source must be one of'):
            OpportunityCreate(**data)
    
    def test_invalid_opportunity_type(self):
        """Invalid type should raise validation error"""
        data = self.get_valid_opportunity_data()
        data['opportunity_type'] = 'invalid_type'
        
        with pytest.raises(ValueError, match='opportunity_type must be one of'):
            OpportunityCreate(**data)
    
    def test_opportunity_type_case_conversion(self):
        """Opportunity type should be converted to lowercase"""
        data = self.get_valid_opportunity_data()
        data['opportunity_type'] = 'INTERNSHIP'
        
        opp = OpportunityCreate(**data)
        assert opp.opportunity_type == 'internship'
    
    def test_past_deadline_rejection(self):
        """Past deadline should raise validation error"""
        data = self.get_valid_opportunity_data()
        data['deadline'] = datetime.now() - timedelta(days=1)
        
        with pytest.raises(ValueError, match='deadline must be in the future'):
            OpportunityCreate(**data)
    
    def test_negative_salary_rejection(self):
        """Negative salary should raise validation error"""
        data = self.get_valid_opportunity_data()
        data['salary_min'] = -50000
        
        with pytest.raises(ValueError, match='salary must be positive'):
            OpportunityCreate(**data)
    
    def test_confidence_score_bounds(self):
        """Confidence score must be 0.0-1.0"""
        data = self.get_valid_opportunity_data()
        
        # Valid scores
        data['confidence_score'] = 0.0
        opp = OpportunityCreate(**data)
        assert opp.confidence_score == 0.0
        
        data['confidence_score'] = 1.0
        opp = OpportunityCreate(**data)
        assert opp.confidence_score == 1.0
        
        # Invalid: > 1.0
        data['confidence_score'] = 1.5
        with pytest.raises(ValueError):
            OpportunityCreate(**data)
        
        # Invalid: < 0.0
        data['confidence_score'] = -0.5
        with pytest.raises(ValueError):
            OpportunityCreate(**data)
    
    def test_optional_fields(self):
        """Optional fields should default to None"""
        data = self.get_valid_opportunity_data()
        # Remove optional fields
        for field in ['category', 'short_description', 'start_date', 'duration', 
                      'location', 'required_skills', 'perks']:
            data.pop(field, None)
        
        opp = OpportunityCreate(**data)
        assert opp.category is None
        assert opp.location is None
        assert opp.required_skills is None
    
    def test_default_values(self):
        """Fields with defaults should have correct defaults"""
        data = self.get_valid_opportunity_data()
        opp = OpportunityCreate(**data)
        
        assert opp.salary_currency == 'INR'
        assert opp.confidence_score == 0.7
        assert opp.is_paid == True  # Set in test data
        assert opp.is_remote == False
        assert opp.is_expired == False
        assert opp.is_active == True


# ============================================================================
# TESTS FOR TO_DICT METHOD
# ============================================================================

class TestOpportunityModelMethods:
    """Test OpportunityModel methods"""
    
    def test_repr(self):
        """__repr__ should show key information"""
        opp = OpportunityModel(
            id=1,
            title='Python Internship',
            source='TCET',
            organization='Google',
            source_url='https://example.com',
            opportunity_type='internship',
            description='Test',
            deadline=datetime(2026, 12, 31),
            source_hash='abc123def456',
        )
        
        repr_str = repr(opp)
        assert 'Opportunity' in repr_str
        assert '1' in repr_str or 'id=1' in repr_str
        assert 'Python Internship' in repr_str or 'title=' in repr_str


# ============================================================================
# TESTS FOR EDGE CASES
# ============================================================================

class TestEdgeCases:
    """Test edge cases and boundary conditions"""
    
    def test_very_long_title(self):
        """Should handle very long titles"""
        data = {
            'source': 'TCET',
            'source_url': 'https://example.com',
            'opportunity_type': 'internship',
            'title': 'A' * 255,  # Max length
            'organization': 'Google',
            'description': 'Test',
            'deadline': datetime.now() + timedelta(days=30),
        }
        opp = OpportunityCreate(**data)
        assert len(opp.title) == 255
    
    def test_unicode_content(self):
        """Should handle unicode characters"""
        data = {
            'source': 'TCET',
            'source_url': 'https://example.com',
            'opportunity_type': 'internship',
            'title': 'Python इंटर्नशिप 🐍',
            'organization': 'गूगल',
            'description': 'काम करो',
            'deadline': datetime.now() + timedelta(days=30),
        }
        opp = OpportunityCreate(**data)
        assert '🐍' in opp.title
        assert 'गूगल' in opp.organization
    
    def test_null_optional_fields(self):
        """Should handle None for optional fields"""
        data = {
            'source': 'TCET',
            'source_url': 'https://example.com',
            'opportunity_type': 'internship',
            'title': 'Test',
            'organization': 'Google',
            'description': 'Test',
            'deadline': datetime.now() + timedelta(days=30),
            'salary_min': None,
            'salary_max': None,
            'location': None,
            'required_skills': None,
        }
        opp = OpportunityCreate(**data)
        assert opp.salary_min is None
        assert opp.location is None


# ============================================================================
# RUN TESTS
# ============================================================================

if __name__ == "__main__":
    print("\n" + "="*60)
    print("OPPORTUNITYMODEL TEST SUITE")
    print("="*60)
    
    # Run with pytest: python -m pytest test_opportunity.py -v
    pytest.main([__file__, '-v', '--tb=short'])