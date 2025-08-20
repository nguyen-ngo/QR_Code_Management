#!/usr/bin/env python3
"""
Employee Data Merger and Deduplication Script
============================================

This script combines employee data from multiple SQL files and removes duplicates
based on intelligent business rules while maintaining data integrity.

Features:
- Parses SQL INSERT statements from multiple files
- Intelligent duplicate detection by employee ID
- Quality-based record selection for deduplication
- Comprehensive logging of merge operations
- Generates clean combined SQL output
"""

import re
import os
from typing import List, Dict, Set, Tuple
from dataclasses import dataclass
from datetime import datetime

@dataclass
class Employee:
    """Employee record structure"""
    index: int
    id: int
    firstName: str
    lastName: str
    title: str
    contractId: int
    source: str = ""
    quality_score: float = 0.0

class EmployeeDataMerger:
    """Handles merging and deduplication of employee data from multiple sources"""
    
    def __init__(self):
        self.employees: List[Employee] = []
        self.duplicate_stats = {
            'total_duplicates': 0,
            'kept_gov': 0,
            'kept_lt': 0,
            'removed_dummy': 0,
            'quality_upgrades': 0
        }
        
    def parse_sql_file(self, filename: str, source_name: str) -> List[Employee]:
        """Parse employee data from SQL INSERT file"""
        print(f"📁 Parsing {filename} (Source: {source_name})")
        
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                content = f.read()
        except FileNotFoundError:
            print(f"❌ File {filename} not found")
            return []
        
        # Extract VALUES section from INSERT statement
        values_match = re.search(r'VALUES\s*(.*?)(?:;|$)', content, re.DOTALL)
        if not values_match:
            print(f"❌ No VALUES section found in {filename}")
            return []
        
        values_text = values_match.group(1)
        employees = []
        
        # Split records by ),( pattern
        record_pattern = r'\((\d+),\s*(\d+),\s*\'([^\']*)\',\s*\'([^\']*)\',\s*(NULL|\'[^\']*\'),\s*(\d+)\)'
        matches = re.findall(record_pattern, values_text)
        
        for match in matches:
            index, emp_id, first_name, last_name, title, contract_id = match
            
            # Clean title field
            title_clean = None if title == 'NULL' else title.strip("'")
            
            employee = Employee(
                index=int(index),
                id=int(emp_id),
                firstName=first_name.strip(),
                lastName=last_name.strip(),
                title=title_clean,
                contractId=int(contract_id),
                source=source_name
            )
            employees.append(employee)
        
        print(f"✅ Parsed {len(employees)} employees from {filename}")
        return employees
    
    def is_dummy_record(self, emp: Employee) -> bool:
        """Check if employee record appears to be dummy/test data"""
        dummy_patterns = [
            r'^(no\s*(name|id)|pending|test|unknown|n\/?a|do\s*not|enter|dummy|xxx?|zzz?)',
            r'^(incorrect|missing|wrong|employee)',
            r'^[0-9]+$',  # Only numbers
            r'^[a-z]{1,2}$',  # Single letters
            r'^(a|b|x|z)\s*(a|b|x|z)$'  # Single letter combinations
        ]
        
        full_name = f"{emp.firstName} {emp.lastName}".lower().strip()
        first_name = emp.firstName.lower().strip()
        last_name = emp.lastName.lower().strip()
        
        for pattern in dummy_patterns:
            if (re.search(pattern, full_name, re.IGNORECASE) or
                re.search(pattern, first_name, re.IGNORECASE) or
                re.search(pattern, last_name, re.IGNORECASE)):
                return True
        
        return False
    
    def calculate_quality_score(self, emp: Employee) -> float:
        """Calculate quality score for record selection"""
        score = 0.0
        
        # Major penalty for dummy records
        if self.is_dummy_record(emp):
            score -= 1000
        
        # Reward complete data
        if emp.title and emp.title.strip():
            score += 10
        
        # Prefer higher contract IDs (usually more recent)
        score += emp.contractId * 0.1
        
        # Reward longer, more descriptive names
        score += len(emp.firstName) + len(emp.lastName)
        
        # Slight preference for GOV source (appears more authoritative)
        if emp.source == 'GOV':
            score += 5
        
        # Penalty for empty or very short names
        if len(emp.firstName) <= 2 or len(emp.lastName) <= 2:
            score -= 50
        
        # Reward normal name patterns (letters, spaces, common punctuation)
        name_pattern = re.compile(r'^[A-Za-z\s\.\-\']+$')
        if name_pattern.match(emp.firstName) and name_pattern.match(emp.lastName):
            score += 20
        
        return score
    
    def deduplicate_employees(self, employees: List[Employee]) -> List[Employee]:
        """Remove duplicates based on employee ID with intelligent selection"""
        print("\n🔍 Starting deduplication process...")
        
        # Group employees by ID
        id_groups: Dict[int, List[Employee]] = {}
        for emp in employees:
            if emp.id not in id_groups:
                id_groups[emp.id] = []
            id_groups[emp.id].append(emp)
        
        # Calculate quality scores
        for emp in employees:
            emp.quality_score = self.calculate_quality_score(emp)
        
        deduplicated = []
        
        for emp_id, group in id_groups.items():
            if len(group) == 1:
                # No duplicates
                deduplicated.append(group[0])
            else:
                # Multiple records - select best one
                self.duplicate_stats['total_duplicates'] += len(group) - 1
                
                # Sort by quality score (highest first)
                group.sort(key=lambda x: x.quality_score, reverse=True)
                best_record = group[0]
                
                # Track statistics
                if best_record.source == 'GOV':
                    self.duplicate_stats['kept_gov'] += 1
                else:
                    self.duplicate_stats['kept_lt'] += 1
                
                # Count dummy records removed
                dummy_removed = sum(1 for emp in group[1:] if self.is_dummy_record(emp))
                self.duplicate_stats['removed_dummy'] += dummy_removed
                
                # Check for quality upgrades
                sources = [emp.source for emp in group]
                if len(set(sources)) > 1:
                    self.duplicate_stats['quality_upgrades'] += 1
                
                deduplicated.append(best_record)
                
                # Log decision for significant duplicates
                if len(group) > 2 or any(not self.is_dummy_record(emp) for emp in group):
                    print(f"📋 Employee ID {emp_id}:")
                    print(f"   ✅ KEPT: {best_record.source} - {best_record.firstName} {best_record.lastName} (Score: {best_record.quality_score:.1f})")
                    for removed in group[1:]:
                        status = "DUMMY" if self.is_dummy_record(removed) else "LOWER_QUALITY"
                        print(f"   ❌ {status}: {removed.source} - {removed.firstName} {removed.lastName} (Score: {removed.quality_score:.1f})")
        
        return deduplicated
    
    def generate_combined_sql(self, employees: List[Employee], output_filename: str = 'combined_employees.sql'):
        """Generate combined SQL file with deduplicated data"""
        print(f"\n📝 Generating combined SQL file: {output_filename}")
        
        # Sort employees by index for consistency
        employees.sort(key=lambda x: x.index)
        
        # Reassign consecutive indices
        for i, emp in enumerate(employees, 1):
            emp.index = i
        
        sql_content = """-- Combined and Deduplicated Employee Data
-- Generated on: {timestamp}
-- Total Records: {total}
-- Sources: Government employee data + LT employee data
-- Deduplication: Intelligent quality-based selection

CREATE TABLE IF NOT EXISTS `employee` (
  `index` bigint NOT NULL AUTO_INCREMENT,
  `id` bigint NOT NULL,
  `firstName` varchar(50) NOT NULL,
  `lastName` varchar(50) NOT NULL,
  `title` varchar(20) DEFAULT NULL,
  `contractId` bigint NOT NULL DEFAULT '1',
  UNIQUE KEY `index_2` (`index`),
  KEY `index` (`index`)
) ENGINE=MyISAM DEFAULT CHARSET=latin1;

-- Clear existing data
TRUNCATE TABLE `employee`;

-- Insert combined and deduplicated data
INSERT INTO `employee` (`index`, `id`, `firstName`, `lastName`, `title`, `contractId`) VALUES
""".format(
    timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    total=len(employees)
)
        
        # Generate VALUES entries
        values_entries = []
        for emp in employees:
            title_value = 'NULL' if emp.title is None else f"'{emp.title}'"
            values_entries.append(
                f"({emp.index}, {emp.id}, '{emp.firstName}', '{emp.lastName}', {title_value}, {emp.contractId})"
            )
        
        sql_content += ',\n'.join(values_entries) + ';\n'
        
        # Add statistics as comments
        sql_content += f"""
-- DEDUPLICATION STATISTICS
-- ========================
-- Original records processed: {self.duplicate_stats['total_duplicates'] + len(employees)}
-- Final unique records: {len(employees)}
-- Duplicates removed: {self.duplicate_stats['total_duplicates']}
-- Records kept from GOV source: {self.duplicate_stats['kept_gov']}
-- Records kept from LT source: {self.duplicate_stats['kept_lt']}
-- Dummy/test records removed: {self.duplicate_stats['removed_dummy']}
-- Quality upgrades performed: {self.duplicate_stats['quality_upgrades']}
"""
        
        # Write to file
        with open(output_filename, 'w', encoding='utf-8') as f:
            f.write(sql_content)
        
        print(f"✅ Combined SQL file generated successfully!")
        return output_filename
    
    def merge_files(self, file_configs: List[Tuple[str, str]], output_filename: str = 'combined_employees.sql'):
        """Main method to merge multiple employee data files"""
        print("🚀 Starting Employee Data Merger")
        print("=" * 50)
        
        all_employees = []
        
        # Parse all source files
        for filename, source_name in file_configs:
            employees = self.parse_sql_file(filename, source_name)
            all_employees.extend(employees)
        
        print(f"\n📊 SUMMARY BEFORE DEDUPLICATION")
        print(f"Total records loaded: {len(all_employees)}")
        
        # Perform deduplication
        deduplicated_employees = self.deduplicate_employees(all_employees)
        
        print(f"\n📊 DEDUPLICATION RESULTS")
        print("=" * 30)
        print(f"Original records: {len(all_employees)}")
        print(f"Final records: {len(deduplicated_employees)}")
        print(f"Duplicates removed: {self.duplicate_stats['total_duplicates']}")
        print(f"Kept from GOV: {self.duplicate_stats['kept_gov']}")
        print(f"Kept from LT: {self.duplicate_stats['kept_lt']}")
        print(f"Dummy records removed: {self.duplicate_stats['removed_dummy']}")
        print(f"Quality upgrades: {self.duplicate_stats['quality_upgrades']}")
        
        # Generate combined SQL
        output_file = self.generate_combined_sql(deduplicated_employees, output_filename)
        
        print(f"\n✅ MERGE COMPLETED SUCCESSFULLY!")
        print(f"📁 Output file: {output_file}")
        print(f"📈 Final record count: {len(deduplicated_employees)}")
        
        return output_file, deduplicated_employees

def main():
    """Main execution function"""
    merger = EmployeeDataMerger()
    
    # Configure source files
    file_configs = [
        ('gov_employee.sql', 'GOV'),  # Government employee data
        ('lt_employee.sql', 'LT')     # LT employee data
    ]
    
    # Verify files exist
    missing_files = [f for f, _ in file_configs if not os.path.exists(f)]
    if missing_files:
        print(f"❌ Missing files: {missing_files}")
        print("Please ensure all SQL files are in the current directory.")
        return
    
    # Perform merge
    try:
        output_file, final_employees = merger.merge_files(file_configs, 'combined_employees.sql')
        
        # Additional validation
        print(f"\n🔍 VALIDATION CHECKS")
        print("=" * 20)
        
        # Check for remaining duplicates
        ids = [emp.id for emp in final_employees]
        duplicate_ids = set([id for id in ids if ids.count(id) > 1])
        
        if duplicate_ids:
            print(f"⚠️  Warning: {len(duplicate_ids)} employee IDs still have duplicates: {duplicate_ids}")
        else:
            print("✅ No duplicate employee IDs found")
        
        # Check data quality
        dummy_count = sum(1 for emp in final_employees if merger.is_dummy_record(emp))
        print(f"📊 Data quality: {len(final_employees) - dummy_count}/{len(final_employees)} real records ({dummy_count} dummy records remaining)")
        
        # Contract ID distribution
        contract_distribution = {}
        for emp in final_employees:
            contract_distribution[emp.contractId] = contract_distribution.get(emp.contractId, 0) + 1
        
        print(f"📋 Contract ID distribution:")
        for contract_id, count in sorted(contract_distribution.items()):
            print(f"   Contract {contract_id}: {count} employees")
        
        print(f"\n🎉 Employee data merge completed successfully!")
        print(f"📁 Use {output_file} for your employee synchronization script.")
        
    except Exception as e:
        print(f"❌ Error during merge: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()