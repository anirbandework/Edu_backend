# app/services/csv_processor.py
import pandas as pd
import io
from typing import List, Dict, Any, Tuple
from fastapi import UploadFile
from ..schemas.bulk_schemas import TenantBulkUpdateRow

class CSVProcessor:
    @staticmethod
    async def process_tenant_csv(file: UploadFile) -> Tuple[List[Dict], List[Dict]]:
        """
        Process CSV file with validation and error reporting
        Returns: (valid_rows, validation_errors)
        """
        try:
            # Read file content
            contents = await file.read()
            decoded_content = contents.decode('utf-8')
            
            # Use pandas for efficient CSV processing
            df = pd.read_csv(io.StringIO(decoded_content))
            
            # Clean and standardize column names
            df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_')
            
            # Validate required columns
            required_columns = ['school_code']
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                raise ValueError(f"Missing required columns: {missing_columns}")
            
            # Process rows with validation
            valid_rows = []
            validation_errors = []
            
            for index, row in df.iterrows():
                try:
                    # Convert row to dictionary and clean None values
                    row_dict = {}
                    for col, value in row.items():
                        if pd.notna(value):  # Only include non-NaN values
                            if isinstance(value, str):
                                value = value.strip()
                            if value != "":  # Skip empty strings
                                row_dict[col] = value
                    
                    # Validate using Pydantic
                    if 'school_code' in row_dict:  # Must have school_code
                        validated_row = TenantBulkUpdateRow(**row_dict)
                        valid_rows.append(validated_row.model_dump(exclude_none=True))
                    else:
                        validation_errors.append({
                            "row_number": index + 2,  # +2 for header and 0-based index
                            "data": row.to_dict(),
                            "error": "Missing required field: school_code"
                        })
                    
                except Exception as validation_error:
                    validation_errors.append({
                        "row_number": index + 2,  # +2 for header and 0-based index
                        "data": row.to_dict(),
                        "error": str(validation_error)
                    })
            
            return valid_rows, validation_errors
            
        except Exception as e:
            raise ValueError(f"Failed to process CSV: {str(e)}")
    
    @staticmethod
    def generate_csv_template() -> str:
        """Generate CSV template for bulk tenant operations"""
        template_data = {
            'school_code': ['SCH2025021', 'SCH2025022', 'SCH2025023'],
            'school_name': ['New Elementary School', 'Advanced High School', 'Creative Arts Academy'],
            'address': ['100 New School Lane, City', '200 Academic Blvd, Town', '300 Arts Street, Village'],
            'phone': ['+1-555-0100', '+1-555-0200', '+1-555-0300'],
            'email': ['admin@newelem.edu', 'info@advancedhigh.edu', 'contact@creativearts.edu'],
            'principal_name': ['Dr. Alice Johnson', 'Mr. Robert Smith', 'Ms. Creative Director'],
            'annual_tuition': [12000.00, 18000.00, 15000.00],
            'registration_fee': [400.00, 750.00, 600.00],
            'maximum_capacity': [800, 1500, 1000],
            'current_enrollment': [750, 1400, 950],
            'total_students': [750, 1400, 950],
            'total_teachers': [45, 85, 65],
            'total_staff': [20, 40, 30],
            'school_type': ['K-8', '9-12', 'K-12'],
            'established_year': [2015, 2010, 2018],
            'accreditation': ['WASC', 'NEASC', 'SACS'],
            'language_of_instruction': ['English', 'English', 'English']
        }
        
        df = pd.DataFrame(template_data)
        return df.to_csv(index=False)
