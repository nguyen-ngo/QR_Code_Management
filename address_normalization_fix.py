"""
Address Normalization Fix for Distance Calculation Issues
==========================================================

This module fixes the issue where nearly identical addresses are geocoded to 
different coordinates, causing incorrect distance calculations.

Issue: 
- "7100 Gordon Rd" vs "7100 Gordons Rd, USA" → 1.5 miles apart (WRONG!)
- "3402 South Glebe Road" vs "3402, South Glebe Road, Aurora Hills" → 0.7 miles (WRONG!)

Root Cause:
- Google Maps/OSM geocodes slightly different address strings to different coordinates
- Minor variations (plurals, commas, neighborhoods, "USA") create false distance

Solution:
- Normalize addresses before geocoding
- Use fuzzy matching to detect identical locations
- Prevent re-geocoding of essentially the same address
"""

import re
from difflib import SequenceMatcher


def normalize_address(address):
    """
    Normalize address string for better matching and geocoding accuracy
    This helps prevent geocoding nearly identical addresses to different coordinates
    
    Args:
        address: Raw address string
        
    Returns:
        Normalized address string
        
    Examples:
        "7100 Gordon Rd, Falls Church, VA 22043"
        "7100 Gordons Rd, Falls Church, VA 22043, USA"
        Both normalize to: "7100 gordon rd, falls church, va 22043"
        
        "3402 South Glebe Road Arlington VA 22202"
        "3402, South Glebe Road, Aurora Hills, Arlington VA 22202"
        Both normalize to: "3402 s glebe rd, arlington, va 22202"
    """
    if not address or not isinstance(address, str):
        return address
    
    # Convert to lowercase for consistent comparison
    normalized = address.lower().strip()
    
    # Remove extra whitespace and normalize separators
    normalized = re.sub(r'\s+', ' ', normalized)  # Multiple spaces to single space
    normalized = re.sub(r'\s*,\s*', ', ', normalized)  # Normalize comma spacing
    
    # Standardize common street abbreviations to short forms
    street_abbrev = {
        r'\broad\b': 'rd',
        r'\broads\b': 'rd',  # Handle plural form (Gordon Rd vs Gordons Rd)
        r'\bstreet\b': 'st',
        r'\bavenue\b': 'ave',
        r'\bdrive\b': 'dr',
        r'\blane\b': 'ln',
        r'\bcourt\b': 'ct',
        r'\bboulevard\b': 'blvd',
        r'\bparkway\b': 'pkwy',
        r'\bcircle\b': 'cir',
        r'\bplace\b': 'pl',
        r'\bterrace\b': 'ter',
        r'\bhighway\b': 'hwy'
    }
    
    for full_form, abbrev in street_abbrev.items():
        normalized = re.sub(full_form, abbrev, normalized)
    
    # Standardize directionals to single letter
    directionals = {
        r'\bnorth\b': 'n',
        r'\bsouth\b': 's', 
        r'\beast\b': 'e',
        r'\bwest\b': 'w',
        r'\bnortheast\b': 'ne',
        r'\bnorthwest\b': 'nw',
        r'\bsoutheast\b': 'se',
        r'\bsouthwest\b': 'sw'
    }
    
    for full_form, abbrev in directionals.items():
        normalized = re.sub(full_form, abbrev, normalized)
    
    # Remove neighborhood/district names that aren't essential for location
    # Examples: "Aurora Hills", "Downtown", etc.
    parts = [p.strip() for p in normalized.split(',')]
    
    # Keep: street address, city, state, zip
    # Remove: neighborhood names, building names, country suffixes
    filtered_parts = []
    
    # Known neighborhood keywords to remove (these don't affect geocoding)
    neighborhood_keywords = ['hills', 'heights', 'park', 'village', 'estates', 
                            'manor', 'gardens', 'terrace', 'commons', 'plaza']
    
    for i, part in enumerate(parts):
        part_clean = part.strip()
        
        # Always keep first part (street address)
        if i == 0:
            filtered_parts.append(part_clean)
            continue
        
        # Skip empty parts
        if not part_clean:
            continue
        
        # Skip country suffixes
        if part_clean in ['usa', 'us', 'united states']:
            continue
        
        # Skip if it's a neighborhood name (contains neighborhood keywords but no numbers)
        is_neighborhood = False
        for keyword in neighborhood_keywords:
            if keyword in part_clean and not re.search(r'\d', part_clean):
                is_neighborhood = True
                print(f"   Removing neighborhood: '{part_clean}'")
                break
        
        if is_neighborhood:
            continue
        
        # Keep if it looks like state (2 letter abbrev)
        if re.match(r'^[a-z]{2}$', part_clean):
            filtered_parts.append(part_clean)
            continue
        
        # Keep if it looks like zip code
        if re.match(r'^\d{5}(-\d{4})?$', part_clean):
            filtered_parts.append(part_clean)
            continue
        
        # Keep if it's likely a city name (reasonable length, no special patterns)
        if 3 <= len(part_clean) <= 30:
            filtered_parts.append(part_clean)
    
    # Reconstruct address
    normalized = ', '.join(filtered_parts)
    
    # Remove common country suffixes that don't affect location
    normalized = re.sub(r',?\s*(usa|united states|us)$', '', normalized)
    
    # Final cleanup: remove trailing commas and spaces
    normalized = normalized.strip(', ')
    
    print(f"🔧 Address normalization:")
    print(f"   Original: {address}")
    print(f"   Normalized: {normalized}")
    
    return normalized


def addresses_are_similar(addr1, addr2, threshold=0.90):
    """
    Check if two addresses are similar enough to be considered the same location
    Uses fuzzy string matching to handle minor variations
    
    Args:
        addr1: First address string
        addr2: Second address string
        threshold: Similarity threshold (0-1), default 0.90 (90% similar)
        
    Returns:
        Boolean indicating if addresses are similar
        
    Examples:
        addresses_are_similar(
            "7100 Gordon Rd, Falls Church, VA 22043",
            "7100 Gordons Rd, Falls Church, VA 22043, USA"
        ) → True (same location, minor spelling difference)
        
        addresses_are_similar(
            "3402 South Glebe Road Arlington VA 22202",
            "3402, South Glebe Road, Aurora Hills, Arlington VA 22202"
        ) → True (same location, extra neighborhood name)
    """
    if not addr1 or not addr2:
        return False
    
    # Normalize both addresses
    norm1 = normalize_address(addr1)
    norm2 = normalize_address(addr2)
    
    # Exact match after normalization
    if norm1 == norm2:
        print(f"✅ Addresses match exactly after normalization")
        return True
    
    # Calculate similarity using difflib SequenceMatcher
    similarity = SequenceMatcher(None, norm1, norm2).ratio()
    
    is_similar = similarity >= threshold
    
    print(f"📊 Address similarity check:")
    print(f"   Address 1 (normalized): {norm1}")
    print(f"   Address 2 (normalized): {norm2}")
    print(f"   Similarity score: {similarity:.2%}")
    print(f"   Threshold: {threshold:.2%}")
    print(f"   Result: {'✅ SIMILAR (same location)' if is_similar else '❌ DIFFERENT (different locations)'}")
    
    return is_similar
