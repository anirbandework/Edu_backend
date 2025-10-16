-- Create tenants table
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE IF NOT EXISTS tenants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    school_code VARCHAR(50) UNIQUE NOT NULL,
    school_name VARCHAR(200) NOT NULL,
    address TEXT NOT NULL,
    phone VARCHAR(20) NOT NULL,
    email VARCHAR(100) NOT NULL,
    principal_name VARCHAR(100) NOT NULL,
    is_active BOOLEAN DEFAULT true,
    annual_tuition DECIMAL(10,2) NOT NULL,
    registration_fee DECIMAL(10,2) NOT NULL,
    total_students INTEGER DEFAULT 0,
    total_teachers INTEGER DEFAULT 0,
    total_staff INTEGER DEFAULT 0,
    student_teacher_ratio DECIMAL(4,1),
    maximum_capacity INTEGER DEFAULT 1000,
    current_enrollment INTEGER DEFAULT 0,
    school_type VARCHAR(20) DEFAULT 'K-12',
    grade_levels TEXT[] NOT NULL,
    academic_year_start TIMESTAMP WITH TIME ZONE NOT NULL,
    academic_year_end TIMESTAMP WITH TIME ZONE NOT NULL,
    established_year INTEGER NOT NULL,
    accreditation VARCHAR(100),
    language_of_instruction VARCHAR(50) DEFAULT 'English',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_tenants_school_code ON tenants(school_code);
CREATE INDEX IF NOT EXISTS idx_tenants_active ON tenants(is_active);
