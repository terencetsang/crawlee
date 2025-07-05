#!/usr/bin/env python3
"""
Test script to verify date validation logic
"""
from datetime import datetime, timedelta

def is_valid_past_race_date(race_date_str):
    """
    Validate that a race date is valid and is strictly in the past (completed races only).
    
    Args:
        race_date_str (str): Race date in YYYY-MM-DD format
        
    Returns:
        bool: True if the date is valid and strictly in the past, False otherwise
    """
    try:
        race_datetime = datetime.strptime(race_date_str, "%Y-%m-%d")
        today = datetime.now().date()
        
        # Only allow races that are strictly in the past (not today, not future)
        # This ensures we only extract completed race data with final odds
        return race_datetime.date() < today
        
    except (ValueError, TypeError):
        return False

def test_date_validation():
    """Test the date validation function with various dates"""
    today = datetime.now().date()
    yesterday = today - timedelta(days=1)
    tomorrow = today + timedelta(days=1)
    
    test_cases = [
        (str(yesterday), True, "Yesterday (should be valid)"),
        (str(today), False, "Today (should be invalid - not completed)"),
        (str(tomorrow), False, "Tomorrow (should be invalid - future)"),
        ("2025-07-01", True, "2025-07-01 (should be valid if in past)"),
        ("2025-07-04", False, "2025-07-04 (should be invalid if today or future)"),
        ("invalid-date", False, "Invalid date format"),
        ("2025-13-01", False, "Invalid month"),
        ("", False, "Empty string"),
    ]
    
    print("🧪 Testing Date Validation Logic")
    print("=" * 50)
    print(f"Today's date: {today}")
    print()
    
    all_passed = True
    
    for date_str, expected, description in test_cases:
        result = is_valid_past_race_date(date_str)
        status = "✅ PASS" if result == expected else "❌ FAIL"
        
        if result != expected:
            all_passed = False
            
        print(f"{status} | {description}")
        print(f"      Date: '{date_str}' -> {result} (expected: {expected})")
        print()
    
    print("=" * 50)
    if all_passed:
        print("🎉 All tests passed!")
    else:
        print("⚠️ Some tests failed!")
    
    return all_passed

if __name__ == "__main__":
    test_date_validation()
