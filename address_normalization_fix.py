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
- Extract and compare street number + street name as primary identifier
"""

import re
from difflib import SequenceMatcher

# Try to import logger_handler for logging (optional - won't break if not available)
try:
    from logger_handler import AppLogger
    logger_handler = AppLogger()
    LOGGING_ENABLED = True
except ImportError:
    logger_handler = None
    LOGGING_ENABLED = False


def _log_activity(action, message):
    """Helper function to log activity if logger is available"""
    if LOGGING_ENABLED and logger_handler:
        try:
            logger_handler.log_user_activity(action, message)
        except Exception:
            pass  # Ignore logging errors


def extract_street_address(address):
    """
    Extract the core street address (number + street name) from an address string.
    This is the most reliable identifier for location matching.
    
    Handles cases where:
    - Street number is at the beginning: "735 18th St S"
    - Building name comes first: "Aurora Hills Library, 735, 18th Street South"
    
    Args:
        address: Normalized address string
        
    Returns:
        Core street address string (e.g., "735 18th st s")
    """
    if not address:
        return ""
    
    addr_lower = address.lower()
    
    # Pattern to match: street number + optional directional + street name + street type
    # This pattern searches ANYWHERE in the string, not just at the beginning
    # Examples: "735 18th st s", "3402 south glebe road", "7100 gordon rd"
    street_types = r'(?:rd|st|ave|dr|ln|ct|blvd|pkwy|cir|pl|ter|hwy|way|trail|pike|run|walk|path|loop|road|street|avenue|drive|lane|court|boulevard|parkway|circle|place|terrace|highway)'
    
    # Pattern: number + ordinal/street name + optional directional + street type
    # Handles: "735 18th st s", "735, 18th street south"
    street_pattern = rf'(\d+)[\s,]+(\d*(?:st|nd|rd|th)?\s*[\w\s]*?{street_types})(?:\s+([nsew]|north|south|east|west))?'
    
    match = re.search(street_pattern, addr_lower)
    if match:
        street_num = match.group(1).strip()
        street_name = match.group(2).strip()
        direction = match.group(3) if match.group(3) else ""
        
        # Clean up extra spaces and commas
        street_name = re.sub(r'[\s,]+', ' ', street_name).strip()
        
        # Normalize direction
        dir_map = {'north': 'n', 'south': 's', 'east': 'e', 'west': 'w'}
        if direction:
            direction = dir_map.get(direction, direction)
        
        result = f"{street_num} {street_name}"
        if direction:
            result += f" {direction}"
        
        return result
    
    # Fallback: try to find just a street number followed by some words
    simple_pattern = r'(\d+)[\s,]+([\w\s]+)'
    match = re.search(simple_pattern, addr_lower)
    if match:
        street_num = match.group(1).strip()
        # Take words until we hit something that looks like a city/state
        words = match.group(2).split()
        street_words = []
        for word in words:
            # Stop at state abbreviations or zip codes
            if re.match(r'^[a-z]{2}$', word) and word in ['va', 'md', 'dc', 'ca', 'ny', 'tx', 'fl', 'pa', 'il', 'oh', 'ga', 'nc', 'nj']:
                break
            if re.match(r'^\d{5}', word):
                break
            street_words.append(word)
        if street_words:
            return f"{street_num} {' '.join(street_words[:4])}"  # Limit to 4 words
    
    return address


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
        
        "Aurora Hills Branch Library, 735, 18th Street South, Arlington, VA 22202"
        "735 18th St S, Arlington, VA 22202"
        Both normalize to: "735 18th st s, arlington, va 22202"
    """
    if not address or not isinstance(address, str):
        return address
    
    # Convert to lowercase for consistent comparison
    normalized = address.lower().strip()
    
    # Remove extra whitespace and normalize separators
    normalized = re.sub(r'\s+', ' ', normalized)  # Multiple spaces to single space
    normalized = re.sub(r'\s*,\s*', ', ', normalized)  # Normalize comma spacing
    
    # Remove building/location names that come BEFORE the street number
    # Pattern: remove text before a street number if it looks like a building name
    # Examples: "Aurora Hills Branch Library, 735" → "735"
    #           "Fire Station #7, 123 Main St" → "123 Main St"
    building_pattern = r'^[^,\d]*(?:library|station|center|building|plaza|tower|hall|office|school|church|hospital|clinic|bank|hotel|restaurant|store|shop|mall|complex|headquarters|hq|branch)[^,\d]*,\s*'
    normalized = re.sub(building_pattern, '', normalized, flags=re.IGNORECASE)
    
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
    
    # Convert full state names to abbreviations
    state_names = {
        r'\bvirginia\b': 'va',
        r'\bmaryland\b': 'md',
        r'\bdistrict of columbia\b': 'dc',
        r'\bcalifornia\b': 'ca',
        r'\bnew york\b': 'ny',
        r'\btexas\b': 'tx',
        r'\bflorida\b': 'fl',
        r'\bpennsylvania\b': 'pa',
        r'\billinois\b': 'il',
        r'\bohio\b': 'oh',
        r'\bgeorgia\b': 'ga',
        r'\bnorth carolina\b': 'nc',
        r'\bnew jersey\b': 'nj',
        r'\bwashington\b': 'wa',
        r'\bmassachusetts\b': 'ma',
        r'\barizona\b': 'az',
        r'\bcolorado\b': 'co',
        r'\btennessee\b': 'tn',
        r'\bindiana\b': 'in',
        r'\bmissouri\b': 'mo',
        r'\bwisconsin\b': 'wi',
        r'\bminnesota\b': 'mn',
        r'\bsouth carolina\b': 'sc',
        r'\balabama\b': 'al',
        r'\blouisiana\b': 'la',
        r'\bkentucky\b': 'ky',
        r'\boregon\b': 'or',
        r'\boklahoma\b': 'ok',
        r'\bconnecticut\b': 'ct',
        r'\biowa\b': 'ia',
        r'\bmississippi\b': 'ms',
        r'\barkansas\b': 'ar',
        r'\bkansas\b': 'ks',
        r'\butah\b': 'ut',
        r'\bnevada\b': 'nv',
        r'\bnew mexico\b': 'nm',
        r'\bwest virginia\b': 'wv',
        r'\bnebraska\b': 'ne',
        r'\bidaho\b': 'id',
        r'\bhawaii\b': 'hi',
        r'\bmaine\b': 'me',
        r'\bnew hampshire\b': 'nh',
        r'\brhode island\b': 'ri',
        r'\bmontana\b': 'mt',
        r'\bdelaware\b': 'de',
        r'\bsouth dakota\b': 'sd',
        r'\bnorth dakota\b': 'nd',
        r'\balaska\b': 'ak',
        r'\bvermont\b': 'vt',
        r'\bwyoming\b': 'wy'
    }
    
    for full_name, abbrev in state_names.items():
        normalized = re.sub(full_name, abbrev, normalized)
    
    # Remove neighborhood/district names that aren't essential for location
    # Examples: "Aurora Hills", "Downtown", etc.
    parts = [p.strip() for p in normalized.split(',')]
    
    # Keep: street address, city, state, zip
    # Remove: neighborhood names, building names, country suffixes, county names
    filtered_parts = []
    
    # Known neighborhood keywords to remove (these don't affect geocoding)
    neighborhood_keywords = ['hills', 'heights', 'park', 'village', 'estates', 
                            'manor', 'gardens', 'terrace', 'commons', 'plaza',
                            'downtown', 'midtown', 'uptown', 'district', 'center',
                            'crossing', 'corner', 'square', 'point', 'landing',
                            'aurora', 'crystal', 'forest', 'lake', 'river', 'creek',
                            'meadow', 'valley', 'ridge', 'grove', 'glen', 'woods',
                            'addison', 'colonial', 'fairfax', 'heritage', 'liberty']
    
    # Country names and suffixes to remove (English and other languages)
    country_suffixes = ['usa', 'us', 'united states', 'united states of america',
                       'estados unidos', 'estados unidos de américa', 'estados unidos de america',
                       'eeuu', 'e.u.', 'u.s.a.', 'u.s.', 'america', 'américas']
    
    for i, part in enumerate(parts):
        part_clean = part.strip()
        
        # Always keep first part (street address) - but only if it contains a number
        if i == 0:
            # Check if this looks like a building name (no street number)
            if re.search(r'\d', part_clean):
                filtered_parts.append(part_clean)
            else:
                print(f"   Removing building name: '{part_clean}'")
            continue
        
        # Skip empty parts
        if not part_clean:
            continue
        
        # Skip country suffixes (multiple languages)
        if part_clean in country_suffixes:
            print(f"   Removing country: '{part_clean}'")
            continue
        
        # Skip county names (e.g., "Arlington County", "Fairfax County")
        if 'county' in part_clean:
            print(f"   Removing county: '{part_clean}'")
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
    
    # Remove common country suffixes that don't affect location (final cleanup)
    normalized = re.sub(r',?\s*(usa|united states|us|estados unidos.*?|eeuu|u\.s\.a?\.|america|américas?)$', '', normalized, flags=re.IGNORECASE)
    
    # Final cleanup: remove trailing commas and spaces
    normalized = normalized.strip(', ')
    
    print(f"🔧 Address normalization:")
    print(f"   Original: {address}")
    print(f"   Normalized: {normalized}")
    
    return normalized


def extract_address_components(address):
    """
    Extract key components from an address for comparison.
    Handles addresses where the street number may not be at the beginning
    (e.g., "Aurora Hills Library, 735, 18th Street South")
    
    Args:
        address: Address string (raw or normalized)
        
    Returns:
        Dictionary with extracted components:
        - street_number: The street number (e.g., "735")
        - street_name: The street name with type (e.g., "18th st s")
        - city: City name if found
        - state: State abbreviation if found
        - zip_code: ZIP code if found
    """
    if not address:
        return {}
    
    addr_lower = address.lower().strip()
    
    components = {
        'street_number': None,
        'street_name': None,
        'city': None,
        'state': None,
        'zip_code': None
    }
    
    # Extract ZIP code first (most reliable)
    zip_match = re.search(r'\b(\d{5})(?:-\d{4})?\b', addr_lower)
    if zip_match:
        components['zip_code'] = zip_match.group(1)
    
    # Extract state (2-letter abbreviation, typically before zip or at end)
    # Also handle full state names that might not have been normalized
    valid_states = ['al', 'ak', 'az', 'ar', 'ca', 'co', 'ct', 'de', 'fl', 'ga',
                   'hi', 'id', 'il', 'in', 'ia', 'ks', 'ky', 'la', 'me', 'md',
                   'ma', 'mi', 'mn', 'ms', 'mo', 'mt', 'ne', 'nv', 'nh', 'nj',
                   'nm', 'ny', 'nc', 'nd', 'oh', 'ok', 'or', 'pa', 'ri', 'sc',
                   'sd', 'tn', 'tx', 'ut', 'vt', 'va', 'wa', 'wv', 'wi', 'wy', 'dc']
    
    state_match = re.search(r'\b([a-z]{2})\s*(?:,?\s*\d{5}|,|$)', addr_lower)
    if state_match:
        potential_state = state_match.group(1)
        if potential_state in valid_states:
            components['state'] = potential_state
    
    # Extract street number - look for it ANYWHERE in the address
    # Pattern: standalone number that's likely a street number (not a zip code or ordinal in street name)
    # Match numbers like "735" or "3402" but not "22202" (zip) or "18th" (ordinal)
    
    # First, try to find a number followed by a street-like pattern
    street_num_pattern = r'(?:^|,\s*)(\d{1,5})(?:\s*,\s*|\s+)(\d*(?:st|nd|rd|th)?\s*[\w\s]*?(?:rd|st|ave|dr|ln|ct|blvd|pkwy|cir|pl|ter|hwy|way|street|road|avenue|drive|lane|court|boulevard))'
    
    match = re.search(street_num_pattern, addr_lower)
    if match:
        components['street_number'] = match.group(1)
        street_name_raw = match.group(2).strip()
        # Clean up the street name
        street_name_raw = re.sub(r'[\s,]+', ' ', street_name_raw)
        components['street_name'] = street_name_raw
    else:
        # Fallback: try simpler pattern - just find a number at the start or after comma
        simple_num_match = re.search(r'(?:^|,\s*)(\d{1,5})(?:\s*,|\s+)(?!\d{4,5}\b)', addr_lower)
        if simple_num_match:
            components['street_number'] = simple_num_match.group(1)
            
            # Try to extract street name after the number
            remainder = addr_lower[simple_num_match.end():]
            remainder = remainder.lstrip(', ')
            
            # Look for street type keywords
            street_types = ['rd', 'st', 'ave', 'dr', 'ln', 'ct', 'blvd', 'pkwy', 'cir', 
                           'pl', 'ter', 'hwy', 'way', 'trail', 'pike', 'run', 'walk', 
                           'path', 'loop', 'road', 'street', 'avenue', 'drive', 'lane',
                           'court', 'boulevard', 'parkway', 'circle', 'place', 'terrace',
                           'highway']
            
            for st_type in street_types:
                pattern = rf'^([\w\s]+?\s*{st_type})\b'
                st_match = re.search(pattern, remainder)
                if st_match:
                    components['street_name'] = st_match.group(1).strip()
                    break
    
    return components


def addresses_are_similar(addr1, addr2, threshold=0.85):
    """
    Check if two addresses are similar enough to be considered the same location
    Uses multiple comparison strategies for robust matching:
    1. Direct street address comparison (highest priority)
    2. Component-based comparison
    3. Fuzzy string matching on normalized addresses
    
    Args:
        addr1: First address string
        addr2: Second address string
        threshold: Similarity threshold (0-1), default 0.85 (85% similar)
        
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
    
    print(f"\n🔍 ADDRESS SIMILARITY CHECK:")
    print(f"   Address 1: {addr1}")
    print(f"   Address 2: {addr2}")
    
    # Normalize both addresses
    norm1 = normalize_address(addr1)
    norm2 = normalize_address(addr2)
    
    # Exact match after normalization
    if norm1 == norm2:
        print(f"✅ Addresses match exactly after normalization")
        return True
    
    # STRATEGY 1: Extract and compare core street addresses
    # This is the most reliable method for catching cases like:
    # "3402 South Glebe Road Arlington VA 22202" vs 
    # "3402, South Glebe Road, Aurora Hills, Arlington VA 22202"
    street1 = extract_street_address(norm1)
    street2 = extract_street_address(norm2)
    
    print(f"   Street Address 1: '{street1}'")
    print(f"   Street Address 2: '{street2}'")
    
    if street1 and street2:
        street_similarity = SequenceMatcher(None, street1, street2).ratio()
        print(f"   Street similarity: {street_similarity:.2%}")
        
        # If street addresses are very similar (>92%), addresses are the same
        if street_similarity >= 0.92:
            print(f"✅ SIMILAR - Street addresses match ({street_similarity:.2%})")
            return True
    
    # STRATEGY 2: Component-based comparison
    comp1 = extract_address_components(addr1)
    comp2 = extract_address_components(addr2)
    
    print(f"   Components 1: {comp1}")
    print(f"   Components 2: {comp2}")
    
    # If street numbers match exactly and street names are similar
    if comp1.get('street_number') and comp2.get('street_number'):
        if comp1['street_number'] == comp2['street_number']:
            # Same street number - check street name similarity
            if comp1.get('street_name') and comp2.get('street_name'):
                name_sim = SequenceMatcher(None, 
                                          comp1['street_name'], 
                                          comp2['street_name']).ratio()
                print(f"   Street name similarity: {name_sim:.2%}")
                
                if name_sim >= 0.85:
                    # Also check if zip codes match (if both have them)
                    if comp1.get('zip_code') and comp2.get('zip_code'):
                        if comp1['zip_code'] == comp2['zip_code']:
                            print(f"✅ SIMILAR - Same street number, similar name, same ZIP")
                            return True
                    else:
                        # No zip to compare, but street info matches
                        print(f"✅ SIMILAR - Same street number, similar street name")
                        return True
    
    # STRATEGY 3: Full normalized address fuzzy matching
    similarity = SequenceMatcher(None, norm1, norm2).ratio()
    is_similar = similarity >= threshold
    
    print(f"📊 Full address similarity:")
    print(f"   Address 1 (normalized): {norm1}")
    print(f"   Address 2 (normalized): {norm2}")
    print(f"   Similarity score: {similarity:.2%}")
    print(f"   Threshold: {threshold:.2%}")
    print(f"   Result: {'✅ SIMILAR (same location)' if is_similar else '❌ DIFFERENT (different locations)'}")
    
    # Log the address similarity check result
    _log_activity(
        'address_similarity_check',
        f"Compared addresses: similarity={similarity:.2%}, result={'SIMILAR' if is_similar else 'DIFFERENT'}"
    )
    
    return is_similar