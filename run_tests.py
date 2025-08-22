#!/usr/bin/env python3
"""
Test runner for the SIT Portal application.
Run specific tests or all tests for the monthly schedule creator.

Usage:
    python run_tests.py                           # Run all tests
    python run_tests.py -k test_academic_year     # Run specific test pattern
    python run_tests.py --cov                     # Run with coverage
    python run_tests.py --integration             # Run integration tests only
"""

import sys
import subprocess
from pathlib import Path


def run_tests(args=None):
    """Run tests with pytest."""
    if args is None:
        args = []
    
    # Base pytest command
    cmd = [
        sys.executable, "-m", "pytest",
        "tests/test_monthly_schedule_creator.py",
        "-v",
        "--tb=short"
    ]
    
    # Add additional arguments
    cmd.extend(args)
    
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=Path(__file__).parent)
    return result.returncode


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run tests for monthly schedule creator")
    parser.add_argument("-k", "--keyword", help="Run tests matching keyword")
    parser.add_argument("--cov", action="store_true", help="Run with coverage")
    parser.add_argument("--integration", action="store_true", help="Run integration tests only")
    parser.add_argument("--unit", action="store_true", help="Run unit tests only")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--pdb", action="store_true", help="Drop into debugger on failure")
    
    args = parser.parse_args()
    
    pytest_args = []
    
    if args.keyword:
        pytest_args.extend(["-k", args.keyword])
        
    if args.cov:
        pytest_args.extend([
            "--cov=app.tasks.monthly_schedule_creator",
            "--cov-report=html",
            "--cov-report=term-missing"
        ])
        
    if args.integration:
        pytest_args.extend(["-m", "integration"])
        
    if args.unit:
        pytest_args.extend(["-m", "unit"])
        
    if args.verbose:
        pytest_args.append("-vv")
        
    if args.pdb:
        pytest_args.append("--pdb")
    
    return run_tests(pytest_args)


if __name__ == "__main__":
    sys.exit(main())